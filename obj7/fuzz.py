#!/usr/bin/env python3
"""
Core fuzzing logic and infrastructure.
"""
import subprocess
import time
import random
import string
import os
import mmap
from pathlib import Path

from seedPool import  Pool
from mutator import Mutator

SIZE = 4096

class Fuzzer:
    def __init__(self, target_path, max_length=10, timeout=3600):
        """Initialize the fuzzer."""
        self.target_path = target_path
        self.max_length = max_length
        self.timeout = timeout
        
        # Statistics
        self.runs = 0
        self.test_cases_generated = 0
        self.crashes_found = []
        self.start_time = None
        self.end_time = None

        # Tools
        self.pool:Pool
        self.mutator:Mutator

        # File Access
        self.file = None
        self.mm = None
        
    def setup(self):
        """Setup the fuzzer before running."""
        print("[*] Setting up fuzzer...")
        self.start_time = time.time()
        #create file for later MMIO interactions
        with open("input.txt", "wb") as f:
            f.truncate(SIZE)

        self.file = open("input.txt", "r+b")
        # Step 3: mmap once
        self.mm = mmap.mmap(self.file.fileno(), SIZE, access=mmap.ACCESS_WRITE)

    def load_seeds(self, seeds_dir: str = "seeds"):
    
        for path in Path(seeds_dir).iterdir():
            if path.is_file():
                test_case = path.read_bytes()
                self.write_input(test_case)
                # Execute target
                result = self.execute_target()
                # Analyze result | assume seeds don't crash
                self.analyze_result(test_case ,result)
        
    def generate_test_case(self):
        """
        Generate a random test case of specified length.
        
        Args:
            length: Length of the test case to generate
            
        Returns:
            bytes: Random byte string
        """
        length = 3
        random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=length))
        return random_string
    
    def execute_target(self):
        """
        Execute the target binary with the given test case.
        
        Args:
            test_case: Bytes to pass to the target
            
        Returns:
            dict: Execution results with keys 'crashed', 'duration', 'returncode'
        """
        start = time.time()
        
        try:
            argv = [self.target_path, "input.txt"]
            env = os.environ.copy()

            pid = os.posix_spawn(self.target_path, argv, env)
            _, status = os.waitpid(pid, 0)
            # Decode exit status
            if os.WIFSIGNALED(status):
                returncode = -os.WTERMSIG(status)
            elif os.WIFEXITED(status):
                returncode = os.WEXITSTATUS(status)
            else:
                returncode = None  # shouldn't really happen

            duration = time.time() - start
            crashed = returncode < 0 or returncode == 139 
            result = {
                'crashed': crashed,
                'duration': duration,
                'returncode': returncode,
            }
            
        except subprocess.TimeoutExpired:
            # Timeout - treat as non-crash for now
            print(f"Exception = Timout")
            duration = time.time() - start
            result = {
                'crashed': False,
                'duration': duration,
                'returncode': -1,
            }
        except Exception as e:
            print(f"Exception {e}")
            # Other errors
            duration = time.time() - start
            result = {
                'crashed': False,
                'duration': duration,
                'returncode': -999,
            }
        
        return result
    
    def analyze_result(self, test_case, exec_result):
        """
        Analyze execution result and handle crashes.
        
        Args:
            test_case: The test case that was executed
            exec_result: Result dictionary from execute_target
            
        Returns:
            bool: True if crash was found
        """
        if exec_result['crashed']:
            print(f"\n[!] CRASH FOUND!")
            print(f"[!] Test case: {test_case}")
            
            self.crashes_found.append({
                'test_case': test_case,
                'iteration': self.test_cases_generated,
                'time': time.time() - self.start_time
            })
            return True
        
        # Check bit map if new edge found
        self.pool.filter("coverage.bin", test_case)
        return False
    
    def write_input(self, input):
        self.mm.seek(0)
        self.mm.write(input)
        #terminate with empty / don't really need but doesn't hurt
        self.mm.write(b"\x00" * (SIZE - len(input)))

    
    def run(self):
        """
        Main fuzzing loop.
        
        Returns:
            dict: Summary of fuzzing results
        """
        self.setup()
        self.pool = Pool()
        self.mutator = Mutator()
        self.load_seeds()

        while time.time() - self.start_time < self.timeout:
            self.runs += 1

            # Generate test case
            seed = self.pool.get_seed()
            test_case = self.mutator.mutate(seed)
            self.write_input(test_case)
            self.test_cases_generated += 1
            # Execute target
            result = self.execute_target()
            # Analyze result
            crash_found = self.analyze_result(test_case, result)
            
            if crash_found:
                # For now, stop on first crash
                print("Early Exit")
                break

            # Progress indicator every 1000000 iterations
            if self.runs % 10000 == 0:
                elapsed = time.time() - self.start_time
                rate = self.runs / elapsed if elapsed > 0 else 0
                print(f"[*] Iterations: {self.runs} | "
                      f"Rate: {rate:.2f}/sec | "
                      f"Time: {elapsed:.2f}s")
            
        self.end_time = time.time()

        #Close files
        self.mm.close()
        self.file.close()

        return self.get_summary()
    
    def get_summary(self):
        """
        Get summary of fuzzing results.
        
        Returns:
            dict: Summary statistics
        """
        total_time = self.end_time - self.start_time if self.end_time else 0
        
        summary = {
            'runs': self.runs,
            'crashes_found': len(self.crashes_found),
            'total_time': total_time,
            'crash_details': self.crashes_found
        }
        
        return summary
    
    def save_results(self, output_file):
        """
        Save fuzzing results to a file.
        
        Args:
            output_file: Path to output file
        """
        summary = self.get_summary()
        
        with open(output_file, 'w') as f:
            f.write("=== Fuzzing Results ===\n\n")
            f.write(f"Number of test cases: {summary['runs']}\n")
            f.write(f"Wall clock time: {summary['total_time']:.2f} seconds\n")
            f.write(f"Crashes found: {summary['crashes_found']}\n\n")
            
            if summary['crash_details']:
                f.write("=== Crash Details ===\n")
                for crash in summary['crash_details']:
                    f.write(f"\nCrash-inducing test case: {crash['test_case']}\n")
                    f.write(f"Found at iteration: {crash['iteration']}\n")
                    f.write(f"Time to find: {crash['time']:.2f} seconds\n")
        
        print(f"\n=== Summary ===")
        print(f"Test cases generated: {summary['runs']}")
        print(f"Total time: {summary['total_time']:.2f} seconds")
        print(f"Crashes found: {summary['crashes_found']}")
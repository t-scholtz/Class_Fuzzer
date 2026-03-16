#!/usr/bin/env python3
"""
fuzz.py
Core fuzzing logic and infrastructure.
"""
import subprocess
import time
import shutil
import os
import mmap
from pathlib import Path
import posix_ipc
import mmap

from seedPool import  Pool
from mutator import Mutator

SIZE = 1000000 #Max input size - change as needed

FUZZER_TO_FORK_FD = 100
FORK_TO_FUZZER_FD = 101

class Fuzzer:
    def __init__(self, target_path, timeout=3600):
        """Initialize the fuzzer."""
        self.target_path = target_path
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
        self.shared_mem = None
        
    def setup(self):
        """Setup the fuzzer before running."""
        print("[*] Setting up fuzzer...")
        self.start_time = time.time()
        # Clean and recreate output directories
        for dir_name in ["output", "interesting"]:
            if os.path.exists(dir_name):
                shutil.rmtree(dir_name)
            os.makedirs(dir_name)

        # Create file for later mmap interactions
        with open("input.txt", "wb") as f:
            f.truncate(SIZE)

        self.file = open("input.txt", "r+b")
        self.mm = mmap.mmap(self.file.fileno(), SIZE, access=mmap.ACCESS_WRITE)


    def load_seeds(self, seeds_dir: str = "seeds"):
        print("[*] Loading Seeds")
        for path in Path(seeds_dir).iterdir():
            if path.is_file():
                # Read file contents as bytes
                data = path.read_bytes()
                # Copy file contents into mmap
                self.write_input(data)
                # Execute target
                result = self.execute_target()
                # Analyze result | assume seeds don't crash
                self.analyze_result(data, result)
        print(f"\t\t- Coverage score after loading seeds is {self.pool.get_coverage():.2f}%")

    def setup_fork_server(self):
        try:
            self.pipe_to_fork_r,   self.pipe_to_fork_w   = os.pipe() #Fuzzer to fork 
            self.pipe_from_fork_r, self.pipe_from_fork_w = os.pipe() #Fork to fuzzer

            self.fork_proc = subprocess.Popen(
                [
                    self.target_path,
                    "input.txt",
                    "/dev/null",
                    str(self.pipe_to_fork_r),    # argv[3]: forkserver reads from this
                    str(self.pipe_from_fork_w)   # argv[4]: forkserver writes to this
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                pass_fds=(self.pipe_to_fork_r, self.pipe_from_fork_w)
            )

            # Close child ends in parent — parent only needs its own ends
            os.close(self.pipe_to_fork_r)
            os.close(self.pipe_from_fork_w)

            import time
            time.sleep(0.2)
            poll = self.fork_proc.poll()
            if poll is not None:
                print(f"[-] Forkserver died immediately with exit code: {poll}")
                return False
            
            print(f"[+] Forkserver running with pid: {self.fork_proc.pid}")

        except Exception as e:
            print(f"[*] Failed to start fork server: {e}")
            return False
        return True
        
    def execute_target(self):
        ## returns true if target crahese
        os.write(self.pipe_to_fork_w, b'\x01')    # send go
        result = os.read(self.pipe_from_fork_r, 1)  # wait for result

        return result == b'\x01'
    
    def analyze_result(self, test_case, crash: bool):
        """
        Analyze execution result and handle crashes.
        
        Args:
            test_case: The test case that was executed
            exec_result: Result dictionary from execute_target
            
        Returns:
            bool: True if crash was found
        """
        if crash:
            print(f"\n[!] CRASH FOUND!")
            print(f"[!] Test case: {test_case}")
            
            self.crashes_found.append({
                'test_case': test_case,
                'iteration': self.test_cases_generated,
                'time': time.time() - self.start_time
            })
            return True
        
        # Check bit map if new edge found
        self.pool.filter(test_case)
        return False
    
    def write_input(self, input):
        self.mm.seek(0)
        data = input[:SIZE]
        self.mm.write(data)
        #terminate with empty / don't really need but doesn't hurt
        self.mm.write(b"\x00" * (SIZE - len(input)))

    def run(self):
        """
        Main fuzzing loop.
        
        Returns:
            dict: Summary of fuzzing results
        """
        self.setup()
        try:
            posix_ipc.unlink_shared_memory("/fuzz_coverage")
        except posix_ipc.ExistentialError:
            pass
        
        if not self.setup_fork_server():
            return None
    
        # Bootstrap run to discover edge count (uses file fallback in harness)
        self.execute_target()
        edge_count = os.path.getsize("coverage.bin")
        print(f"\t\t- Number of edges in application: {edge_count}")

        self.fork_proc.terminate()
        self.fork_proc.wait()
        os.close(self.pipe_to_fork_w)
        os.close(self.pipe_from_fork_r)

        # Set up shared memory for all subsequent runs
        shm = posix_ipc.SharedMemory(
            "/fuzz_coverage",
            flags=posix_ipc.O_CREAT,
            mode=0o666,
            size=edge_count
        )

        self.shared_mem = mmap.mmap(shm.fd, edge_count, access=mmap.ACCESS_READ)
        shm.close_fd() 

        if not self.setup_fork_server():
            return None
        print("[*] Production forkserver started with shared memory")

        self.pool = Pool(self.shared_mem, edge_count)

        self.mutator = Mutator(SIZE)
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

        self.shared_mem.close()
        try:
            posix_ipc.unlink_shared_memory("/fuzz_coverage")
        except posix_ipc.ExistentialError:
            pass

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
            'crash_details': self.crashes_found,
            'coverage': f"{self.pool.get_coverage():.2f}",
            'edge_count': f"{self.pool.get_edges_found()}"
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
            f.write(f"Crashes found: {summary['crashes_found']}\n")
            f.write(f"Edges found: {summary['edge_count']}\n")
            f.write(f"Coverage: {summary['coverage']}%\n\n")
            
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
        print(f"Edges found: {summary['edge_count']}")
        print(f"Coverage: {summary['coverage']}%")

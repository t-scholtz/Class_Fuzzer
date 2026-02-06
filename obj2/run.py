#!/usr/bin/env python3
"""
Main entry point for the fuzzer.
Provides a simple CLI interface.
"""

import argparse
import sys
from fuzz import Fuzzer

def main():
    parser = argparse.ArgumentParser(description='Basic black-box fuzzer')
    parser.add_argument('target', help='Path to the target binary')
    parser.add_argument('--max-len', type=int, default=20, 
                        help='Maximum length of test cases (default: 10)')
    parser.add_argument('--timeout', type=int, default=3600,
                        help='Fuzzing timeout in seconds (default: 3600)')
    parser.add_argument('--output', default='results.txt',
                        help='Output file for results (default: results.txt)')
    
    args = parser.parse_args()
    
    print(f"[*] Starting fuzzer...")
    print(f"[*] Target: {args.target}")
    print(f"[*] Max input length: {args.max_len}")
    print(f"[*] Timeout: {args.timeout} seconds")
    print()
    
    # Initialize and run fuzzer
    fuzzer = Fuzzer(
        target_path=args.target,
        max_length=args.max_len,
        timeout=args.timeout
    )
    
    results = fuzzer.run()
    
    # Save results
    fuzzer.save_results(args.output)
    
    print(f"\n[*] Results saved to {args.output}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
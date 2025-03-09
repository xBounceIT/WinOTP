#!/usr/bin/env python
"""
Main entry point to run all WinOTP tests.
Run this from the project root directory.
"""
import os
import sys
import subprocess

if __name__ == "__main__":
    # Run the tests module
    print("Running WinOTP tests...")
    result = subprocess.call([sys.executable, os.path.join("tests", "run_tests.py")])
    sys.exit(result) 
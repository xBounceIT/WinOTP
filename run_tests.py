#!/usr/bin/env python3
"""
Test runner for WinOTP
Run this script to execute all tests with coverage reporting
"""

import sys
import pytest

if __name__ == "__main__":
    # Add command line arguments
    args = [
        "-v",                      # Verbose output
        "--cov=.",                 # Coverage for all modules
        "--cov-report=term-missing", # Show missing lines in coverage report
    ]
    
    # Add any additional arguments from the command line
    args.extend(sys.argv[1:])
    
    # Run pytest with the arguments
    sys.exit(pytest.main(args)) 
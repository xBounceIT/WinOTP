#!/usr/bin/env python
"""
Run only the core non-UI tests that don't require mocking of tkinter.
Use this if you're having issues with the GUI mocking.

Note: For running QR scanner tests, you might need to install additional dependencies:
    pip install -r requirements_dev.txt
"""
import unittest
import sys
import os

# Add the parent directory to sys.path so we can import the app modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Import only the tests that don't use tkinter
from tests.test_token import TestToken
from tests.test_file_io import TestFileIO
from tests.test_qr_scanner import TestQRScanner

def run_core_tests():
    """Run only the core non-UI WinOTP tests."""
    # Create a test suite containing only non-UI tests
    test_suite = unittest.TestSuite()
    
    # Add test cases to the suite
    test_suite.addTest(unittest.makeSuite(TestToken))
    test_suite.addTest(unittest.makeSuite(TestFileIO))
    test_suite.addTest(unittest.makeSuite(TestQRScanner))
    
    # Run the tests
    print("\n===== Running WinOTP Core Tests (Non-UI) =====\n")
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    
    # Print summary
    print("\n===== Test Summary =====")
    print(f"Tests run: {result.testsRun}")
    print(f"Errors: {len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Skipped: {len(result.skipped)}")
    
    # Return 0 if all tests passed, 1 otherwise
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(run_core_tests()) 
#!/usr/bin/env python
import unittest
import sys
import os

# Add the parent directory to sys.path so we can import the app modules
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

# Note: Make sure to initialize our mock modules before importing test modules
# First import the mockable UI test to validate our mocking approach
from tests.test_mock_ui import TestMockUI
from tests.test_token import TestToken
from tests.test_file_io import TestFileIO
from tests.test_qr_scanner import TestQRScanner
from tests.test_app import TestWinOTPApp

def run_tests():
    """Run all WinOTP tests and print a summary."""
    # Create a test suite containing all tests
    test_suite = unittest.TestSuite()
    
    # Add test cases to the suite
    test_suite.addTest(unittest.makeSuite(TestMockUI))  # Start with the mock UI test
    test_suite.addTest(unittest.makeSuite(TestToken))
    test_suite.addTest(unittest.makeSuite(TestFileIO))
    test_suite.addTest(unittest.makeSuite(TestQRScanner))
    test_suite.addTest(unittest.makeSuite(TestWinOTPApp))
    
    # Run the tests
    print("\n===== Running WinOTP Tests =====\n")
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
    sys.exit(run_tests()) 
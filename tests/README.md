# WinOTP Test Suite

This directory contains unit tests for the WinOTP application. The tests are organized by component and functionality.

## Test Files

- `test_token.py`: Tests for the Token model, including code generation and validation
- `test_file_io.py`: Tests for file I/O operations
- `test_ntp_sync.py`: Tests for NTP synchronization functionality
- `test_qr_scanner.py`: Tests for QR code scanning functionality
- `test_api.py`: Tests for the API class that handles application logic

## Running Tests

You can run the tests using pytest. From the project root directory:

```bash
# Run all tests
pytest

# Run tests with coverage report
pytest --cov=. --cov-report=term-missing

# Run a specific test file
pytest tests/test_token.py

# Run a specific test
pytest tests/test_token.py::TestToken::test_get_code
```

## Test Configuration

The test configuration is defined in `pytest.ini` in the project root. It includes:
- Test discovery patterns
- Coverage reporting options
- Verbosity settings

## Adding New Tests

When adding new tests:
1. Create a new test file following the naming convention `test_*.py`
2. Create test classes with the prefix `Test*`
3. Create test methods with the prefix `test_*`
4. Use pytest fixtures for setup and teardown
5. Use mocks for external dependencies

## Test Data

Some tests require test data. Test data is generated within the tests or stored in the `tests/data` directory. 
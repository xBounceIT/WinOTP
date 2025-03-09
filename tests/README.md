# WinOTP Tests

This directory contains tests for the WinOTP application.

## Running Tests

There are multiple ways to run the tests:

### 1. Run all tests from the project root

```
python run_tests.py
```

This will run all tests, including UI tests with mocked tkinter modules.

### 2. Run only core non-UI tests

If you're having issues with the UI mocking, you can run just the core functionality tests:

```
python tests/run_core_tests.py
```

These tests don't rely on tkinter mocking and should run without issues.

### 3. Run individual test modules

You can also run individual test modules:

```
python tests/test_token.py
python tests/test_file_io.py
python tests/test_qr_scanner.py
python tests/test_mock_ui.py
python tests/test_app.py
```

### 4. Run with pytest

You can use pytest to run the tests with additional features like coverage reports:

```
pytest
```

## Test Module Overview

- **test_token.py**: Tests for the Token model, including OTP code generation
- **test_file_io.py**: Tests for JSON file I/O utilities
- **test_qr_scanner.py**: Tests for QR code scanning functionality
- **test_mock_ui.py**: Simple tests to validate our UI mocking strategy
- **test_app.py**: Tests for the main WinOTP application functionality

## Troubleshooting

### ImportError with tkinter

If you see errors like:
```
ModuleNotFoundError: No module named 'tkinter.font'; 'tkinter' is not a package
```

Try running the core non-UI tests instead:
```
python tests/run_core_tests.py
```

### Install Test Dependencies

Make sure you have all the required test dependencies installed:
```
pip install -r requirements_dev.txt
```

### Mock Objects

The UI tests use extensive mocking of tkinter and other UI-related modules. If you encounter issues with the mocking mechanism, try updating the mock objects in test_app.py or test_mock_ui.py. 
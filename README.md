# WinOTP

A secure and user-friendly Windows desktop application for managing Two-Factor Authentication (2FA) tokens.

## Features

- Desktop-based OTP token management
- QR code scanning support
- Secure token storage with encryption
- Modern and intuitive user interface
- Automatic time synchronization
- System tray integration

## Prerequisites

- Windows 10 or later
- Python 3.8+
- Camera (optional, for QR code scanning)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/xBounceIT/WinOTP.git
cd WinOTP
```

2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure

- `/api` - API endpoints and interfaces
- `/core` - Core application logic
- `/models` - Data models and schemas
- `/static` - Static assets and resources
- `/tests` - Test suite
- `/ui` - User interface components
- `/utils` - Utility functions and helpers

## Configuration

The application uses several configuration files:

- `auth_config.json` - Authentication configuration
- `app_settings.json` - Application settings
- `tokens.json` - Encrypted token storage (do not edit manually)

## Development

### Running Tests

```bash
python run_tests.py
```

Test coverage reports can be found in the `.coverage` file.

### Development Environment

The project includes configuration files for VS Code in the `.vscode` directory.

## Security

- All tokens are encrypted at rest using strong cryptography
- No cloud storage or network transmission of tokens
- Local-only storage with secure encryption

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file. Please refer to the LICENSE file for detailed licensing information and terms of use.

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed list of changes. 
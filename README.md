# WinOTP

A modern, secure, and feature-rich TOTP authenticator designed specifically for Windows, offering a user-friendly interface and robust security features.

![background](https://github.com/user-attachments/assets/6412eacd-5b58-4255-837c-9070fb922981)

## Features

- Generate TOTP codes for two-factor authentication
- Scan QR codes to add tokens easily
- Manual entry and management of token details
- NTP time synchronization for accurate code generation
- Multiple authentication options:
    - PIN protection 
    - Password protection
- Token management features:
    - Import/Export tokens as JSON
    - Customizable token sorting
    - Token editing and deletion
- System integration:
    - Minimize to system tray option
    - Encrypted token storage

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

By default, the application stores its configuration and data files in the user's Documents folder:
`%USERPROFILE%\Documents\WinOTP`

The main files are:

- `auth_config.json` - Authentication configuration (PIN/password hashes, timeout settings).
- `app_settings.json` - Application settings (e.g., minimize to tray).
- `tokens.json` - Token storage. Encrypted if app protection is enabled. **Do not edit this file manually.**

**Note:** When running in debug mode (using the `--debug` or `-d` flag), the application will instead use local files named `tokens.json.dev`, `app_settings.json.dev`, and `auth_config.json.dev` located in the application's root directory.

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

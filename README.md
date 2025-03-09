# WinOTP

A Windows TOTP Authenticator application built with Python and ttkbootstrap.

## Features

- Add TOTP tokens manually or by scanning QR codes
- Copy TOTP codes to clipboard with a single click
- Search and sort tokens
- Dark mode UI
- Import/export tokens

## Project Structure

The project has been refactored into a modular structure:

```
WinOTP/
├── main.py                 # Entry point
├── app.py                  # Main application window
├── models/                 # Data models
│   ├── __init__.py
│   └── token.py            # Token model with validation
├── ui/                     # UI components
│   ├── __init__.py
│   ├── totp_frame.py       # Individual token display
│   └── search_bar.py       # Search and toolbar
├── utils/                  # Utility functions
│   ├── __init__.py
│   ├── file_io.py          # File operations
│   └── qr_scanner.py       # QR code scanning
└── icons/                  # Application icons
```

## Requirements

- Python 3.6+
- ttkbootstrap
- pyotp
- Pillow
- pyzbar

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install ttkbootstrap pyotp pillow pyzbar
   ```
3. Run the application:
   ```
   python main.py
   ```

## Development Mode

Run the application in debug mode to use a separate tokens file:

```
python main.py --debug
```

This will use `tokens.json.dev` instead of `tokens.json` for storing tokens.

## License

[MIT License](LICENSE)
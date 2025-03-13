# WinOTP

A Windows TOTP Authenticator application built with Python and PyWebView.

## Features

- Add TOTP tokens manually or by scanning QR codes
- Copy TOTP codes to clipboard with a single click
- Search and sort tokens
- Dark mode UI
- Import/export tokens
- NTP time synchronization for accurate TOTP codes

## Project Structure

The project has a modular structure:

```
WinOTP/
├── main.py                 # Entry point and API implementation
├── ui/                     # UI files
│   └── index.html          # Main HTML interface
├── models/                 # Data models
│   └── token.py            # Token model
├── utils/                  # Utility functions
│   ├── asset_manager.py    # Asset management
│   ├── file_io.py          # File I/O operations
│   ├── ntp_sync.py         # NTP time synchronization
│   └── qr_scanner.py       # QR code scanning
├── tokens.json             # Token storage (production)
└── tokens.json.dev         # Token storage (development)
```

## How It Works

This application uses PyWebView to create a desktop application with a web-based UI:

1. Python backend handles token management, TOTP generation, and file operations
2. HTML/CSS/JavaScript frontend provides the user interface
3. PyWebView bridges the gap between the two, allowing JavaScript to call Python functions directly

## Installation

1. Clone the repository
2. Install the required packages: `pip install -r requirements.txt`
3. Run the application: `python main.py`

## Development

To run the application in debug mode:

```
python main.py --debug
```

This will use the development token file (`tokens.json.dev`) and enable debug logging.

## License

[MIT License](LICENSE)
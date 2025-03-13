# WinOTP

A Windows TOTP Authenticator application built with Python and ttkbootstrap.

## Features

- Add TOTP tokens manually or by scanning QR codes
- Copy TOTP codes to clipboard with a single click
- Search and sort tokens
- Dark mode UI
- Import/export tokens
- HTTP/3 support for faster requests (optional)

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

## HTTP/3 Support

WinOTP now supports HTTP/3 for faster requests. There are several ways to enable HTTP/3:

### Option 1: HTTP/3 with fallback (recommended for most users)

```
python main.py --http3
```

This will attempt to use HTTP/3, but will automatically fall back to HTTP/1.1 if HTTP/3 cannot be initialized. This is the safest option.

### Option 2: HTTP/3 only mode with webview

```
python main.py --http3-only
```

This runs the server with HTTP/3 support directly in the main thread and launches the webview in a separate process. This provides true HTTP/3 support but will not fall back to HTTP/1.1 if there's an issue.

### Option 3: HTTP/3 only mode with browser

```
python main.py --http3-only --no-webview
```

This runs the server with HTTP/3 support and opens your default web browser instead of using a webview window. This is the most compatible option for HTTP/3 support.

All options require the `hypercorn[h3]` package to be installed. HTTP/3 uses QUIC protocol which provides:

- Faster connection establishment
- Improved congestion control
- Reduced latency
- Better performance on unreliable networks

When HTTP/3 is enabled, the application will use HTTPS with self-signed certificates.

## License

[MIT License](LICENSE)
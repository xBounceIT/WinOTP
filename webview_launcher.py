import webview
import sys
import time
import os

# Wait a moment for the server to start (reduced from 2 seconds to 0.5 seconds)
time.sleep(0.5)

# Create and run the webview window
window = webview.create_window("WinOTP", f"https://localhost:5000", width=500, height=600, resizable=False)

# Start the webview
webview.start()

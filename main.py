import sys
import webview
import threading
import time
from app import start_flask, set_tokens_path

def check_server_ready(port=5000, max_attempts=10):
    """Check if the Flask server is ready to accept connections"""
    import socket
    for attempt in range(max_attempts):
        try:
            # Try to connect to the server
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                s.connect(('127.0.0.1', port))
                print(f"Server is ready after {attempt+1} attempts")
                return True
        except (socket.error, socket.timeout):
            # Wait a bit before trying again
            time.sleep(0.1)
    
    print(f"Server not ready after {max_attempts} attempts, continuing anyway")
    return False

if __name__ == "__main__":
    # Check if debug mode is enabled via command line arguments
    debug_mode = "--debug" in sys.argv or "-d" in sys.argv
    
    # Select the appropriate tokens file
    if debug_mode:
        tokens_path = "tokens.json.dev"
        print("Running in DEBUG mode with tokens.json.dev")
    else:
        tokens_path = "tokens.json"
        print("Running in PRODUCTION mode with tokens.json")
    
    # Set the tokens path in the app
    set_tokens_path(tokens_path)
    
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=start_flask, kwargs={'debug': debug_mode, 'port': 5000})
    flask_thread.daemon = True
    flask_thread.start()
    
    # Wait for the server to be ready (with a timeout)
    check_server_ready(port=5000, max_attempts=20)
    
    # Create and run the webview window
    webview.create_window("WinOTP", "http://localhost:5000", width=500, height=600, resizable=False)
    webview.start() 
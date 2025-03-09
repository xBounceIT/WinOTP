import sys
from app import WinOTP

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
    
    app = WinOTP(tokens_path)
    app.mainloop() 
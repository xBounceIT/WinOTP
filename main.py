import webview
import json
import os
import sys
import uuid
import pyotp
import threading
import time
from datetime import datetime
import base64
from PIL import Image
import io
import gzip

# Import utilities
from utils.file_io import read_json, write_json
from utils.qr_scanner import scan_qr_image
from utils.ntp_sync import start_ntp_sync, get_accurate_time, get_accurate_timestamp_30s, get_sync_status, calculate_offset
from utils.asset_manager import initialize_assets
from models.token import Token

# Global variables
tokens_path = "tokens.json"  # Default path
tokens = {}  # Store tokens data
sort_ascending = True  # Default sort order
last_tokens_update = 0  # Track when tokens were last updated from disk
file_write_lock = threading.Lock()  # Lock for thread-safe file operations

class Api:
    def __init__(self):
        self.window = None
        # Initialize assets in the background
        initialize_assets()
        # Start NTP sync in the background
        start_ntp_sync()
        # Load tokens
        self.load_tokens()
    
    def __eq__(self, other):
        # Implement equality method to fix Rectangle.op_Equality error
        if isinstance(other, Api):
            return id(self) == id(other)
        return False
    
    def __hash__(self):
        # Implement hash method to complement __eq__
        return hash(id(self))
    
    def set_window(self, window):
        self.window = window
    
    def load_tokens(self):
        """Load tokens from the tokens file"""
        global tokens, last_tokens_update
        try:
            tokens_data = read_json(tokens_path)
            if tokens_data:
                tokens = tokens_data
                last_tokens_update = time.time()
                print(f"Successfully loaded {len(tokens)} tokens from {tokens_path}")
                return {"status": "success", "message": f"Loaded {len(tokens)} tokens"}
            print(f"No tokens found or empty file: {tokens_path}")
            return {"status": "warning", "message": "No tokens found or empty file"}
        except Exception as e:
            print(f"Failed to load tokens: {str(e)}")
            return {"status": "error", "message": f"Failed to load tokens: {str(e)}"}
    
    def save_tokens(self):
        """Save tokens to the tokens file"""
        global tokens, last_tokens_update
        try:
            with file_write_lock:
                write_json(tokens_path, tokens)
                last_tokens_update = time.time()
            return {"status": "success", "message": "Tokens saved successfully"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to save tokens: {str(e)}"}
    
    def get_tokens(self):
        """Get all tokens with their current codes"""
        global tokens
        result = []
        
        # Check if we need to reload tokens from disk
        self.check_reload_tokens()
        
        # Get current time for TOTP generation
        current_time = get_accurate_time()
        
        for token_id, token_data in tokens.items():
            try:
                # Create Token object
                token_obj = Token(
                    token_data.get("issuer", "Unknown"),
                    token_data.get("secret", ""),
                    token_data.get("name", "Unknown")
                )
                
                # Generate code and get time remaining
                code = token_obj.get_code()
                time_remaining = token_obj.get_time_remaining()
                
                # Add token to result
                result.append({
                    "id": token_id,
                    "issuer": token_data.get("issuer", "Unknown"),
                    "name": token_data.get("name", "Unknown"),
                    "code": code,
                    "timeRemaining": time_remaining,
                    "created": token_data.get("created", ""),
                    "lastUsed": token_data.get("lastUsed", "")
                })
            except Exception as e:
                # Add error token
                result.append({
                    "id": token_id,
                    "issuer": token_data.get("issuer", "Unknown"),
                    "name": token_data.get("name", "Unknown"),
                    "code": "ERROR",
                    "timeRemaining": 30,
                    "error": str(e),
                    "created": token_data.get("created", ""),
                    "lastUsed": token_data.get("lastUsed", "")
                })
        
        # Sort tokens
        if sort_ascending:
            result.sort(key=lambda x: (x.get("issuer", "").lower(), x.get("name", "").lower()))
        else:
            result.sort(key=lambda x: (x.get("issuer", "").lower(), x.get("name", "").lower()), reverse=True)
        
        return result
    
    def check_reload_tokens(self):
        """Check if tokens need to be reloaded from disk"""
        global tokens, last_tokens_update
        try:
            # Check if file has been modified since last load
            if os.path.exists(tokens_path):
                file_mtime = os.path.getmtime(tokens_path)
                if file_mtime > last_tokens_update:
                    self.load_tokens()
        except Exception:
            # Ignore errors, will try again next time
            pass
    
    def add_token(self, token_data):
        """Add a new token"""
        global tokens
        try:
            # Validate token data
            if not token_data.get("secret"):
                return {"status": "error", "message": "Secret is required"}
            
            # Generate token ID
            token_id = str(uuid.uuid4())
            
            # Add created timestamp
            token_data["created"] = datetime.now().isoformat()
            
            # Add token to tokens
            tokens[token_id] = token_data
            
            # Save tokens
            save_result = self.save_tokens()
            if save_result["status"] != "success":
                return save_result
            
            return {"status": "success", "message": "Token added successfully", "id": token_id}
        except Exception as e:
            return {"status": "error", "message": f"Failed to add token: {str(e)}"}
    
    def update_token(self, token_id, token_data):
        """Update an existing token"""
        global tokens
        try:
            # Check if token exists
            if token_id not in tokens:
                return {"status": "error", "message": "Token not found"}
            
            # Update token data
            tokens[token_id].update(token_data)
            
            # Save tokens
            save_result = self.save_tokens()
            if save_result["status"] != "success":
                return save_result
            
            return {"status": "success", "message": "Token updated successfully"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to update token: {str(e)}"}
    
    def delete_token(self, token_id):
        """Delete a token"""
        global tokens
        try:
            # Check if token exists
            if token_id not in tokens:
                return {"status": "error", "message": "Token not found"}
            
            # Delete token
            del tokens[token_id]
            
            # Save tokens
            save_result = self.save_tokens()
            if save_result["status"] != "success":
                return save_result
            
            return {"status": "success", "message": "Token deleted successfully"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to delete token: {str(e)}"}
    
    def scan_qr_code(self, image_data):
        """Scan a QR code from image data"""
        try:
            # Decode base64 image
            image_data = base64.b64decode(image_data.split(',')[1])
            image = Image.open(io.BytesIO(image_data))
            
            # Scan QR code
            result = scan_qr_image(image)
            
            if not result:
                return {"status": "error", "message": "No QR code found"}
            
            return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": f"Failed to scan QR code: {str(e)}"}
    
    def get_ntp_status(self):
        """Get NTP synchronization status"""
        try:
            status = get_sync_status()
            return {"status": "success", "data": status}
        except Exception as e:
            return {"status": "error", "message": f"Failed to get NTP status: {str(e)}"}
    
    def toggle_sort_order(self):
        """Toggle token sort order"""
        global sort_ascending
        sort_ascending = not sort_ascending
        return {"status": "success", "ascending": sort_ascending}

def set_tokens_path(path):
    """Set the path to the tokens file"""
    global tokens_path
    tokens_path = path

def main():
    # Check if debug mode is enabled via command line arguments
    debug_mode = "--debug" in sys.argv or "-d" in sys.argv
    
    # Select the appropriate tokens file
    if debug_mode:
        tokens_path = "tokens.json.dev"
        print("Running in DEBUG mode with tokens.json.dev")
    else:
        tokens_path = "tokens.json"
        print("Running in PRODUCTION mode with tokens.json")
    
    # Set the tokens path
    set_tokens_path(tokens_path)
    
    # Create API instance
    api = Api()
    
    # Create window with HTML file
    window = webview.create_window(
        "WinOTP", 
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "index.html"),
        width=500, 
        height=600, 
        resizable=False,
        js_api=api
    )
    
    # Set window reference in API
    api.set_window(window)
    
    # Start webview
    webview.start(debug=debug_mode)

if __name__ == "__main__":
    main() 
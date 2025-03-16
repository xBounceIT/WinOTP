import webview
import json
import os
import sys
import uuid
import threading
import time
from datetime import datetime
import base64
import io
import pystray
from PIL import Image

# Import utilities
from utils.file_io import read_json, write_json
from utils.asset_manager import initialize_assets
from utils.ntp_sync import start_ntp_sync, get_accurate_time, get_sync_status
from utils.auth import (
    set_pin, set_password, clear_auth, verify_pin, verify_password, 
    is_auth_enabled, get_auth_type, hash_password, set_timeout,
    get_timeout, check_timeout
)
from utils.crypto import encrypt_tokens_file, decrypt_tokens_file
from models.token import Token  # Import Token class directly

# Global variables
tokens_path = "tokens.json"  # Default path
AUTH_CONFIG_PATH = "auth_config.json"  # Auth config file path
tokens = {}  # Store tokens data
sort_ascending = True  # Default sort order
last_tokens_update = 0  # Track when tokens were last updated from disk
file_write_lock = threading.Lock()  # Lock for thread-safe file operations
settings_path = "app_settings.json"  # Settings file path
tray_icon = None  # Global tray icon instance

def load_settings():
    """Load application settings"""
    try:
        if os.path.exists(settings_path):
            return read_json(settings_path)
        return {"minimize_to_tray": False}
    except Exception as e:
        print(f"Error loading settings: {e}")
        return {"minimize_to_tray": False}

def save_settings(settings):
    """Save application settings"""
    try:
        write_json(settings_path, settings)
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False

def create_tray_icon(window):
    """Create system tray icon"""
    try:
        # Load the icon image
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "icons", "app.png")
        image = Image.open(icon_path)

        def show_window():
            window.show()
            window.restore()

        def quit_app():
            window.destroy()
            tray_icon.stop()

        # Create the tray icon
        menu = (
            pystray.MenuItem("Show", show_window),
            pystray.MenuItem("Quit", quit_app)
        )
        icon = pystray.Icon("WinOTP", image, "WinOTP", menu)
        return icon
    except Exception as e:
        print(f"Error creating tray icon: {e}")
        return None

# Lazy imports for modules not needed at startup
def import_lazy_modules():
    global pyotp, gzip, Image, scan_qr_image, calculate_offset, get_accurate_timestamp_30s
    
    import pyotp
    import gzip
    from PIL import Image
    from utils.qr_scanner import scan_qr_image
    from utils.ntp_sync import calculate_offset, get_accurate_timestamp_30s
    
    print("Lazy modules imported successfully")

# Start lazy import in background
lazy_import_thread = None

class Api:
    def __init__(self):
        self._window = None
        self._settings = load_settings()
        # Initialize assets in the background
        initialize_assets()
        # Start NTP sync in the background with delayed initialization
        start_ntp_sync()
        # Load tokens
        self.load_tokens()
        
        # Check authentication status
        auth_enabled = is_auth_enabled()
        auth_type = get_auth_type()
        print(f"Authentication enabled: {auth_enabled}, type: {auth_type}")
        
        # Authentication state - initially not authenticated if auth is enabled
        self.is_authenticated = False
        self.last_auth_time = None
        print(f"Initial authentication state: {self.is_authenticated}")
        
        # Start lazy import in background
        global lazy_import_thread
        lazy_import_thread = threading.Thread(target=import_lazy_modules, daemon=True)
        lazy_import_thread.start()
        
        self._tokens_lock = threading.Lock()
    
    def __eq__(self, other):
        # Completely rewritten equality method to avoid Rectangle.op_Equality error
        if other is self:
            return True
        if not hasattr(other, '__class__'):
            return False
        return False
    
    def __hash__(self):
        # Implement hash method to complement __eq__
        return id(self)
    
    def set_window(self, window):
        # Store window reference
        self._window = window
        
        # Create tray icon if minimize to tray is enabled
        if self._settings.get("minimize_to_tray", False):
            global tray_icon
            tray_icon = create_tray_icon(window)
            if tray_icon:
                threading.Thread(target=tray_icon.run, daemon=True).start()
    
    def load_tokens(self):
        """Load tokens from the tokens file"""
        global tokens, last_tokens_update
        try:
            # Get current auth type and credentials
            auth_type = get_auth_type()
            config = read_json(AUTH_CONFIG_PATH) or {}
            
            # Try to decrypt tokens if auth is enabled
            if auth_type == "pin":
                tokens_data = decrypt_tokens_file(tokens_path, config.get("pin_hash", ""))
            elif auth_type == "password":
                tokens_data = decrypt_tokens_file(tokens_path, config.get("password_hash", ""))
            else:
                tokens_data = read_json(tokens_path)
            
            # Validate tokens data
            if isinstance(tokens_data, dict):
                # Verify each token has the required structure
                valid_tokens = {}
                for token_id, token_data in tokens_data.items():
                    if isinstance(token_data, dict) and "secret" in token_data:
                        valid_tokens[token_id] = {
                            "issuer": token_data.get("issuer", "Unknown"),
                            "name": token_data.get("name", "Unknown"),
                            "secret": token_data["secret"],
                            "created": token_data.get("created", datetime.now().isoformat())
                        }
                
                tokens = valid_tokens
                last_tokens_update = time.time()
                print(f"Successfully loaded {len(tokens)} tokens from {tokens_path}")
                return {"status": "success", "message": f"Loaded {len(tokens)} tokens"}
            
            print(f"No valid tokens found in file: {tokens_path}")
            tokens = {}  # Reset to empty dict if invalid data
            return {"status": "warning", "message": "No valid tokens found"}
        except Exception as e:
            print(f"Failed to load tokens: {str(e)}")
            tokens = {}  # Reset to empty dict on error
            return {"status": "error", "message": f"Failed to load tokens: {str(e)}"}
    
    def save_tokens(self):
        """Save tokens to the tokens file"""
        global tokens, last_tokens_update
        try:
            with file_write_lock:
                # Get current auth type and credentials
                auth_type = get_auth_type()
                config = read_json(AUTH_CONFIG_PATH) or {}
                
                # First write tokens to file without encryption
                write_json(tokens_path, tokens)
                
                # Then encrypt if auth is enabled
                if auth_type == "pin":
                    success = encrypt_tokens_file(tokens_path, config.get("pin_hash", ""))
                elif auth_type == "password":
                    success = encrypt_tokens_file(tokens_path, config.get("password_hash", ""))
                else:
                    success = True
                
                if success:
                    last_tokens_update = time.time()
                    return {"status": "success", "message": "Tokens saved successfully"}
                else:
                    return {"status": "error", "message": "Failed to save tokens"}
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
                
                # Get the current code and time remaining
                code = token_obj.get_code()
                time_remaining = token_obj.get_time_remaining()
                
                # Add to result
                result.append({
                    "id": token_id,
                    "issuer": token_data.get("issuer", "Unknown"),
                    "name": token_data.get("name", "Unknown"),
                    "code": code,
                    "timeRemaining": time_remaining,
                    "icon": token_data.get("icon", None)
                })
            except Exception as e:
                print(f"Error generating code for token {token_id}: {str(e)}")
                result.append({
                    "id": token_id,
                    "issuer": token_data.get("issuer", "Unknown"),
                    "name": token_data.get("name", "Unknown"),
                    "code": "ERROR",
                    "timeRemaining": 30,
                    "icon": token_data.get("icon", None),
                    "error": str(e)
                })
        
        # Sort tokens by issuer and name
        if sort_ascending:
            result.sort(key=lambda x: (x["issuer"].lower(), x["name"].lower()))
        else:
            result.sort(key=lambda x: (x["issuer"].lower(), x["name"].lower()), reverse=True)
            
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
    
    def update_token(self, token_id, data):
        """Update token details"""
        global tokens
        try:
            # Check if token exists
            if token_id not in tokens:
                return {"status": "error", "message": "Token not found"}
            
            # Update token details
            tokens[token_id]["issuer"] = data.get("issuer", tokens[token_id]["issuer"])
            tokens[token_id]["name"] = data.get("name", tokens[token_id]["name"])
            
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
            # Ensure PIL.Image is imported
            if 'Image' not in globals():
                from PIL import Image
                print("Imported PIL.Image directly for QR scanning")
                
            # Ensure scan_qr_image is imported
            if 'scan_qr_image' not in globals():
                from utils.qr_scanner import scan_qr_image
                print("Imported scan_qr_image directly for QR scanning")
                
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
        """Toggle the sort order of tokens"""
        global sort_ascending
        sort_ascending = not sort_ascending
        return {"status": "success", "ascending": sort_ascending}
    
    def add_token_from_uri(self, uri):
        """Add a new token from an otpauth URI"""
        global tokens
        try:
            # Validate URI format
            if not uri.startswith('otpauth://'):
                return {"status": "error", "message": "Invalid OTP Auth URI format"}
            
            # Ensure pyotp is imported synchronously
            if 'pyotp' not in globals():
                try:
                    global pyotp
                    import pyotp
                    print("Imported pyotp synchronously for URI parsing")
                except ImportError as e:
                    return {"status": "error", "message": f"Failed to import pyotp: {str(e)}"}
                
            # Parse the URI using pyotp
            try:
                totp = pyotp.parse_uri(uri)
                
                # Validate that the secret is a valid base32 string
                if not Token.validate_base32_secret(totp.secret):
                    return {"status": "error", "message": "Invalid secret: Not a valid base32 string"}
                
                # Extract token data
                token_data = {
                    "issuer": totp.issuer or "Unknown",
                    "name": totp.name or "Unknown",
                    "secret": totp.secret
                }
                
                # Add the token using the existing method
                return self.add_token(token_data)
            except Exception as e:
                return {"status": "error", "message": f"Failed to parse URI: {str(e)}"}
            
        except Exception as e:
            return {"status": "error", "message": f"Failed to add token from URI: {str(e)}"}
    
    def import_tokens_from_json(self, json_str):
        """Import tokens from a JSON string (typically from another WinOTP instance)"""
        try:
            # Parse JSON data
            import_data = json.loads(json_str)
            
            # Validate import data format
            if not isinstance(import_data, dict):
                return {"status": "error", "message": "Invalid import format: Expected a JSON object"}
            
            # Count successful and failed imports
            successful = 0
            failed = 0
            
            # Process each token
            for token_id, token_data in import_data.items():
                try:
                    # Validate token data
                    if not token_data.get("secret"):
                        failed += 1
                        continue
                    
                    # Validate that the secret is a valid base32 string
                    if not Token.validate_base32_secret(token_data.get("secret")):
                        failed += 1
                        continue
                    
                    # Add each token with a new ID (using existing add_token method)
                    result = self.add_token({
                        "issuer": token_data.get("issuer", "Unknown"),
                        "name": token_data.get("name", "Unknown"),
                        "secret": token_data.get("secret")
                    })
                    
                    if result.get("status") == "success":
                        successful += 1
                    else:
                        failed += 1
                except Exception:
                    failed += 1
            
            if successful > 0:
                return {
                    "status": "success", 
                    "message": f"Successfully imported {successful} tokens" + 
                              (f", {failed} failed" if failed > 0 else "")
                }
            elif failed > 0:
                return {"status": "error", "message": f"Failed to import {failed} tokens"}
            else:
                return {"status": "warning", "message": "No tokens found in the import file"}
        except json.JSONDecodeError:
            return {"status": "error", "message": "Invalid JSON format"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to import tokens: {str(e)}"}
    
    def get_icon_base64(self, icon_name):
        """Get base64 encoded icon data"""
        try:
            # Define the path to the icon
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "icons", icon_name)
            print(f"Looking for icon at: {icon_path}")
            
            # Check if the file exists
            if not os.path.exists(icon_path):
                print(f"Icon not found: {icon_path}")
                return {"status": "error", "message": f"Icon not found: {icon_name}"}
            
            # Read the file and encode as base64
            with open(icon_path, "rb") as f:
                icon_data = base64.b64encode(f.read()).decode("utf-8")
            
            print(f"Successfully loaded icon: {icon_name}")
            return {"status": "success", "data": icon_data}
        except Exception as e:
            print(f"Error loading icon {icon_name}: {str(e)}")
            return {"status": "error", "message": f"Failed to load icon: {str(e)}"}

    def show_confirmation_dialog(self, message, title="Confirm"):
        """Show a confirmation dialog to the user"""
        return self._window.create_confirmation_dialog(title, message)

    def set_pin_protection(self, pin):
        """Set a PIN for app protection"""
        if not pin or len(pin) < 4:
            return {"status": "error", "message": "PIN must be at least 4 digits"}
        
        # Validate PIN format (numbers only)
        if not pin.isdigit():
            return {"status": "error", "message": "PIN must contain only digits"}
            
        # Set the PIN
        if set_pin(pin):
            # Encrypt the tokens file with the new PIN
            if encrypt_tokens_file(tokens_path, hash_password(pin)):
                return {"status": "success", "message": "PIN protection enabled"}
            else:
                # If encryption fails, clear the PIN
                clear_auth()
                return {"status": "error", "message": "Failed to encrypt tokens with PIN"}
        else:
            return {"status": "error", "message": "Failed to set PIN protection"}
    
    def set_password_protection(self, password):
        """Set a password for app protection"""
        if not password or len(password) < 6:
            return {"status": "error", "message": "Password must be at least 6 characters"}
            
        # Set the password
        if set_password(password):
            # Encrypt the tokens file with the new password
            if encrypt_tokens_file(tokens_path, hash_password(password)):
                return {"status": "success", "message": "Password protection enabled"}
            else:
                # If encryption fails, clear the password
                clear_auth()
                return {"status": "error", "message": "Failed to encrypt tokens with password"}
        else:
            return {"status": "error", "message": "Failed to set password protection"}
    
    def disable_protection(self):
        """Disable PIN/password protection"""
        # Load the current tokens before disabling protection
        auth_type = get_auth_type()
        config = read_json(AUTH_CONFIG_PATH) or {}
        
        if auth_type == "pin":
            current_tokens = decrypt_tokens_file(tokens_path, config.get("pin_hash", ""))
        elif auth_type == "password":
            current_tokens = decrypt_tokens_file(tokens_path, config.get("password_hash", ""))
        else:
            current_tokens = read_json(tokens_path)
        
        # Clear the protection
        if clear_auth():
            # Set timeout to 0 (never) when disabling protection
            set_timeout(0)
            
            # Save the tokens without encryption
            try:
                write_json(tokens_path, current_tokens)
                return {"status": "success", "message": "Protection disabled"}
            except Exception as e:
                return {"status": "error", "message": f"Failed to save unencrypted tokens: {str(e)}"}
        else:
            return {"status": "error", "message": "Failed to disable protection"}
    
    def verify_authentication(self, credential):
        """Verify PIN or password"""
        auth_type = get_auth_type()
        
        if auth_type == "pin":
            if verify_pin(credential):
                self.is_authenticated = True
                self.last_auth_time = time.time()
                return {"status": "success", "message": "Authentication successful"}
            else:
                return {"status": "error", "message": "Incorrect PIN"}
        elif auth_type == "password":
            if verify_password(credential):
                self.is_authenticated = True
                self.last_auth_time = time.time()
                return {"status": "success", "message": "Authentication successful"}
            else:
                return {"status": "error", "message": "Incorrect password"}
        else:
            self.is_authenticated = True
            self.last_auth_time = time.time()
            return {"status": "success", "message": "No authentication required"}
    
    def get_auth_status(self):
        """Get current authentication status"""
        auth_enabled = is_auth_enabled()
        auth_type = get_auth_type()
        
        # Check if authentication has timed out
        if auth_enabled and self.is_authenticated and self.last_auth_time:
            if check_timeout(self.last_auth_time):
                self.is_authenticated = False
                self.last_auth_time = None
        
        return {
            "is_enabled": auth_enabled,
            "auth_type": auth_type,
            "is_authenticated": self.is_authenticated,
            "timeout_minutes": get_timeout()
        }

    def export_tokens_to_json(self):
        """Export tokens to a JSON string"""
        try:
            # Convert tokens to JSON string with pretty printing
            json_str = json.dumps(tokens, indent=4)
            
            # Get current date for default filename
            default_filename = f"winotp_backup_{datetime.now().strftime('%Y-%m-%d')}.json"
            
            # Show save file dialog
            file_path = self._window.create_file_dialog(
                webview.SAVE_DIALOG,
                directory='~',
                save_filename=default_filename,
                file_types=('JSON Files (*.json)',)
            )
            
            if file_path:
                # Ensure file has .json extension
                if not file_path.lower().endswith('.json'):
                    file_path += '.json'
                    
                # Write the file
                with open(file_path, 'w') as f:
                    f.write(json_str)
                return {"status": "success", "message": "Tokens exported successfully"}
            else:
                return {"status": "cancelled", "message": "Export cancelled"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to export tokens: {str(e)}"}

    def get_minimize_to_tray(self):
        """Get minimize to tray setting"""
        try:
            return {"status": "success", "enabled": self._settings.get("minimize_to_tray", False)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def set_minimize_to_tray(self, enabled):
        """Set minimize to tray setting"""
        try:
            self._settings["minimize_to_tray"] = enabled
            if save_settings(self._settings):
                # Create or destroy tray icon based on setting
                global tray_icon
                if enabled and not tray_icon and self._window:
                    tray_icon = create_tray_icon(self._window)
                    if tray_icon:
                        threading.Thread(target=tray_icon.run, daemon=True).start()
                elif not enabled and tray_icon:
                    tray_icon.stop()
                    tray_icon = None
                return {"status": "success", "message": "Setting updated successfully"}
            return {"status": "error", "message": "Failed to save setting"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def set_protection_timeout(self, timeout_minutes):
        """Set the protection timeout duration"""
        try:
            timeout_minutes = int(timeout_minutes)
            if timeout_minutes < 0:
                return {"status": "error", "message": "Timeout cannot be negative"}
                
            if set_timeout(timeout_minutes):
                return {"status": "success", "message": "Protection timeout updated"}
            else:
                return {"status": "error", "message": "Failed to update protection timeout"}
        except ValueError:
            return {"status": "error", "message": "Invalid timeout value"}

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
        js_api=api,
        on_top=False,
        minimized=False
    )
    
    # Set window reference in API
    api.set_window(window)

    # Set up closing event handler
    def on_closing():
        minimize_to_tray = api._settings.get("minimize_to_tray", False)
        if minimize_to_tray and tray_icon:
            window.hide()
            return False  # Prevent window from closing
        return True  # Allow window to close
    
    window.events.closing += on_closing
    
    # Start webview
    webview.start(debug=debug_mode)

if __name__ == "__main__":
    main() 
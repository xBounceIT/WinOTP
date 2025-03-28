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
from utils.ntp_sync import start_ntp_sync, get_accurate_time, get_sync_status
from utils.auth import (
    set_pin, set_password, clear_auth, verify_pin, verify_password, 
    is_auth_enabled, get_auth_type, hash_password, set_timeout,
    get_timeout, check_timeout, set_auth_path
)
from utils.crypto import encrypt_tokens_file, decrypt_tokens_file
from models.token import Token  # Import Token class directly
from utils import asset_manager # Import asset_manager
from utils.importers.winotp_importer import parse_winotp_json # <-- New import
from utils.importers.twofas_importer import parse_2fas_json # <-- New import

# --- Define Application Data Directory ---
# Get user's Documents folder
documents_path = os.path.join(os.path.expanduser("~"), "Documents")
# Define the application-specific directory within Documents
winotp_data_dir = os.path.join(documents_path, "WinOTP")

# --- Global variables ---
tokens_path = os.path.join(winotp_data_dir, "tokens.json")  # Default path
AUTH_CONFIG_PATH = os.path.join(winotp_data_dir, "auth_config.json")  # Auth config file path
settings_path = os.path.join(winotp_data_dir, "app_settings.json")  # Settings file path

tokens = {}  # Store tokens data
sort_ascending = True  # Default sort order
last_tokens_update = 0  # Track when tokens were last updated from disk
file_write_lock = threading.Lock()  # Lock for thread-safe file operations
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
        print(f"--- Enter load_tokens --- ")
        print(f"    Current tokens_path: {tokens_path}")
        print(f"    Current settings_path: {settings_path}")
        print(f"    Current AUTH_CONFIG_PATH: {AUTH_CONFIG_PATH}")
        
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
                print(f"Successfully processed {len(tokens)} tokens loaded from {tokens_path}")
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
        global tokens
        try:
            # Parse JSON data using the importer
            parse_result = parse_winotp_json(json_str)

            if parse_result["status"] == "error":
                return {"status": "error", "message": parse_result["message"]}
            if parse_result["status"] == "warning" or not parse_result["valid_tokens"]:
                return {"status": "warning", "message": parse_result["message"]} # Return warning if no valid tokens found

            valid_tokens_data = parse_result["valid_tokens"]
            successful_adds = 0
            failed_adds = 0

            # Add valid tokens using the existing lock and save mechanism
            try:
                with self._tokens_lock:
                    for token_data in valid_tokens_data:
                        # Add each token with a new ID and created timestamp
                        token_id = str(uuid.uuid4())
                        token_data["created"] = datetime.now().isoformat()
                        tokens[token_id] = token_data
                        successful_adds += 1 # Assume add is successful for now

                    # Save all added tokens at once
                    save_status = self.save_tokens()
                    if save_status["status"] != "success":
                        # If saving failed, treat all adds as failed
                        failed_adds = successful_adds
                        successful_adds = 0
                        return {"status": "error", "message": f"Import failed during save: {save_status.get('message', 'Unknown')}"}

            except Exception as add_save_e:
                 # Critical error during adding/saving phase
                 failed_adds = len(valid_tokens_data) # All parsed tokens failed to be added/saved
                 successful_adds = 0
                 return {"status": "error", "message": f"Critical error adding/saving imported tokens: {add_save_e}"}


            # Construct final message based on adding results
            message_parts = []
            if successful_adds > 0:
                message_parts.append(f"Successfully imported {successful_adds} tokens")
            if failed_adds > 0: # This should only happen if save fails currently
                message_parts.append(f"{failed_adds} failed to save")

            final_message = ", ".join(message_parts) + "." if message_parts else "No tokens were imported."
            final_status = "success" if successful_adds > 0 else "error"

            return {"status": final_status, "message": final_message}

        except Exception as e:
            # Catch potential errors before parsing starts
            return {"status": "error", "message": f"Failed to import tokens: {str(e)}"}


    def import_tokens_from_2fas(self, file_content):
        """Import tokens from a 2FAS backup JSON string with progress reporting"""
        global tokens # Need access to the global tokens dict

        def progress_callback(current, total):
            """Callback function to send progress updates to the frontend."""
            if self._window:
                try:
                    progress_percent = int(((current) / total) * 100)
                    self._window.evaluate_js(f'updateImportProgress({current}, {total}, {progress_percent})')
                except Exception as eval_e:
                    print(f"Error sending progress update to frontend: {eval_e}")

        try:
            # Parse the 2FAS JSON using the importer, passing the callback
            parse_result = parse_2fas_json(file_content, progress_callback)

            # Extract results from parsing
            valid_tokens_data = parse_result.get("valid_tokens", [])
            skipped = parse_result.get("skipped", 0)
            failed_validation = parse_result.get("failed_validation", 0)
            parse_status = parse_result["status"]
            parse_message = parse_result["message"] # Initial message from parser

            # Handle parsing errors immediately
            if parse_status == "error":
                 if self._window: # Try to hide progress UI on error
                      try: self._window.evaluate_js('hideImportProgressOnError()')
                      except Exception: pass
                 return {"status": "error", "message": parse_message}

            # --- Add valid tokens and save ---
            successful_adds = 0
            failed_adds = 0 # Tokens that were valid but failed during add/save
            save_status = {"status": "success"} # Default

            if valid_tokens_data: # Only proceed if there are tokens to add
                try:
                    with self._tokens_lock:
                        for token_data in valid_tokens_data:
                            token_id = str(uuid.uuid4())
                            token_data["created"] = datetime.now().isoformat()
                            tokens[token_id] = token_data
                            # successful_adds count will be finalized after save

                        # Save all new tokens at once
                        save_status = self.save_tokens()
                        if save_status["status"] == "success":
                            successful_adds = len(valid_tokens_data)
                        else:
                            failed_adds = len(valid_tokens_data) # All parsed tokens failed to save
                            print(f"Save operation failed after processing 2FAS tokens: {save_status.get('message')}")

                except Exception as save_e:
                    failed_adds = len(valid_tokens_data) # All parsed tokens failed if exception during save
                    save_status = {"status": "error", "message": f"Critical error during final save: {save_e}"}
                    print(f"Critical error during final 2FAS token save: {save_e}")

            # --- Construct final summary message ---
            message_parts = []
            final_status = "warning" # Default to warning

            if successful_adds > 0:
                message_parts.append(f"Successfully imported {successful_adds} tokens")
                final_status = "success"
            # Combine validation failures and save failures into "failed"
            total_failed = failed_validation + failed_adds
            if total_failed > 0:
                 message_parts.append(f"{total_failed} failed (validation or save)")
                 # If there were successes before save failed, status might be success.
                 # If save failed, overall status MUST be error.
                 if save_status["status"] != "success":
                     final_status = "error"
                 # If only validation failed, but some succeeded, it's still success overall
                 # If only validation failed and none succeeded, it's error
                 elif successful_adds == 0:
                      final_status = "error"

            if skipped > 0:
                 message_parts.append(f"{skipped} skipped (format)")
                 if final_status == "warning" and successful_adds == 0 and total_failed == 0:
                     final_status = "warning" # Only skipped means warning


            if message_parts:
                 final_message = ", ".join(message_parts) + "."
                 # Append save error message specifically if save failed
                 if save_status["status"] != "success":
                     final_message += f" Save Error: {save_status.get('message', 'Unknown')}"
            elif save_status["status"] != "success": # Handle case where save failed but no tokens parsed
                 final_status = "error"
                 final_message = f"Import failed during save: {save_status.get('message', 'Unknown')}"
            elif skipped == 0 and failed_validation == 0 and successful_adds == 0:
                 final_message = "No valid tokens found in the 2FAS file to import." # Original warning message
                 final_status = "warning"
            else: # Should cover the case where only skipped happened
                 final_message = ", ".join(message_parts) + "."


            # Ensure progress UI is hidden if it was shown
            if self._window:
                 try:
                      self._window.evaluate_js('hideImportProgressOnCompletion()')
                 except Exception as eval_e:
                      print(f"Error hiding progress UI on completion: {eval_e}")


            return {"status": final_status, "message": final_message}

        except Exception as e:
            # General exception catcher
            if self._window:
                try: self._window.evaluate_js('hideImportProgressOnError()')
                except Exception: pass
            print(f"Unexpected error during 2FAS import process: {str(e)}")
            return {"status": "error", "message": f"Failed to import tokens from 2FAS: {str(e)}"}

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
        """Verify PIN or password and check for updates on success."""
        auth_type = get_auth_type()
        authenticated = False
        message = ""

        if auth_type == "pin":
            if verify_pin(credential):
                authenticated = True
                message = "Authentication successful"
            else:
                message = "Incorrect PIN"
        elif auth_type == "password":
            if verify_password(credential):
                authenticated = True
                message = "Authentication successful"
            else:
                message = "Incorrect password"
        else: # No auth enabled
            authenticated = True
            message = "No authentication required"

        if authenticated:
            self.is_authenticated = True
            self.last_auth_time = time.time()
            print("Authentication successful. Checking for updates...")
            
            # Check for updates after successful authentication
            update_status = asset_manager.get_update_status()
            if update_status.get("available"):
                print("Update available, including status in auth response.")
            else:
                print("No update available or already up-to-date.")
                
            # Return success message AND update status
            return {"status": "success", "message": message, "update_info": update_status}
        else:
            return {"status": "error", "message": message}
    
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

    def get_setting(self, key):
        """Get a specific application setting"""
        print(f"Getting setting: {key}")
        self._settings = load_settings() # Ensure latest settings are loaded
        return self._settings.get(key)

    def get_current_version(self):
        """Get the current application version"""
        return asset_manager.CURRENT_VERSION

    def set_minimize_to_tray(self, enabled):
        """Set the minimize to tray setting"""
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
    # --- Ensure Application Data Directory Exists (for production mode) ---
    try:
        os.makedirs(winotp_data_dir, exist_ok=True)
        print(f"Production data directory: {winotp_data_dir}")
    except OSError as e:
        print(f"Error creating data directory {winotp_data_dir}: {e}")
        # Potentially critical error if not in debug mode
        pass # Or sys.exit(1)

    # Check if debug mode is enabled via command line arguments
    debug_mode = "--debug" in sys.argv or "-d" in sys.argv

    # Select the appropriate file paths based on mode
    global tokens_path, settings_path, AUTH_CONFIG_PATH # Declare globals to modify them
    if debug_mode:
        # Use local .dev files for debug mode
        tokens_path = "tokens.json.dev"
        settings_path = "app_settings.json.dev"
        AUTH_CONFIG_PATH = "auth_config.json.dev"
        print(f"DEBUG MODE: Using local development files:")
        print(f"  - Tokens: {os.path.abspath(tokens_path)}")
        print(f"  - Settings: {os.path.abspath(settings_path)}")
        print(f"  - Auth Config: {os.path.abspath(AUTH_CONFIG_PATH)}")
    else:
        # Use data directory paths for production mode (paths are already set globally)
        print(f"PRODUCTION MODE: Using files in {winotp_data_dir}:")
        print(f"  - Tokens: {tokens_path}")
        print(f"  - Settings: {settings_path}")
        print(f"  - Auth Config: {AUTH_CONFIG_PATH}")

    # --- Set the authentication file path for the auth utility module ---
    set_auth_path(AUTH_CONFIG_PATH) 

    # Start update check in a background thread
    print("Starting background update check...")
    update_thread = threading.Thread(target=asset_manager.check_for_updates, daemon=True)
    update_thread.start()

    # Create API instance (which will load settings and tokens based on the set paths)
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
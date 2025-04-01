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
import logging
import urllib.request
import re
import winreg

# Import utilities
from utils.file_io import read_json, write_json, clear_cache
from utils.ntp_sync import start_ntp_sync, get_accurate_time, get_sync_status
from utils.auth import (
    set_pin, set_password, clear_auth, verify_pin, verify_password, 
    is_auth_enabled, get_auth_type, hash_password, set_timeout,
    get_timeout, check_timeout, set_auth_path
)
from utils.crypto import encrypt_tokens_file, decrypt_tokens_file
from models.token import Token  # Import Token class directly
from utils import asset_manager # Import asset_manager
from utils.importers.winotp_importer import parse_winotp_json
from utils.importers.twofas_importer import parse_2fas_json
from utils.importers.authenticator_plugin import parse_authenticator_plugin_export
from app import startup # Import the startup module

# Globals for on-demand imports
pyotp = None
pyzbar = None
Image = None

# Path to the user's app data directory
winotp_data_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'WinOTP')

# Global file paths with default values for app data directory
tokens_path = os.path.join(winotp_data_dir, 'tokens.json')
settings_path = os.path.join(winotp_data_dir, 'app_settings.json')
AUTH_CONFIG_PATH = os.path.join(winotp_data_dir, 'auth_config.json')

# Lock for file operations
file_write_lock = threading.Lock()

tokens = {}  # Store tokens data
sort_ascending = True  # Default sort order
last_tokens_update = 0  # Track when tokens were last updated from disk
tray_icon = None  # Global tray icon instance

def load_settings():
    """Load application settings"""
    try:
        default_settings = {
            "minimize_to_tray": False,
            "update_check_enabled": True,
            "run_at_startup": False,
            "next_code_preview_enabled": False
        }
        
        if os.path.exists(settings_path):
            current_settings = read_json(settings_path)
            # Ensure all default settings exist
            for key, value in default_settings.items():
                if key not in current_settings:
                    current_settings[key] = value
            # Save if any defaults were added
            if len(current_settings) > len(read_json(settings_path)):
                write_json(settings_path, current_settings)
            return current_settings
        
        # If file doesn't exist, create it with default settings
        write_json(settings_path, default_settings)
        return default_settings
    except Exception as e:
        print(f"Error loading settings: {e}")
        return default_settings

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
        # Load the icon image container
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "static", "icons", "app.ico")
        image_container = Image.open(icon_path)
        
        # Print original container size (usually largest frame)
        print(f"Pillow loaded ICO container, largest frame size: {image_container.size}")

        # --- Explicitly extract the 32x32 frame --- 
        icon_32 = None
        try:
            # Get the specific 32x32 image frame from the ICO container
            icon_32 = image_container.ico.getimage((32, 32))
            print(f"Successfully extracted 32x32 frame. Size: {icon_32.size}")
        except KeyError:
            print("Warning: 32x32 frame not found in ICO. Falling back to largest and resizing.")
            # Fallback: Resize the largest image if 32x32 is missing
            target_size = (32, 32)
            icon_32 = image_container.resize(target_size, Image.Resampling.LANCZOS)
            print(f"Resized largest frame to: {icon_32.size}")
        except Exception as e_extract:
             print(f"Error extracting 32x32 frame: {e_extract}. Falling back to largest and resizing.")
             target_size = (32, 32)
             icon_32 = image_container.resize(target_size, Image.Resampling.LANCZOS)
             print(f"Resized largest frame to: {icon_32.size}")
        # --- End frame extraction ---

        if not icon_32:
             print("Error: Could not obtain a 32x32 icon image.")
             return None

        def show_window():
            window.show()
            window.restore()

        def quit_app():
            # Use the global tray_icon reference if available
            global tray_icon
            window.destroy()
            if tray_icon:
                tray_icon.stop()

        # Create the tray icon using the 32x32 image
        menu = (
            pystray.MenuItem("Show", show_window),
            pystray.MenuItem("Quit", quit_app)
        )
        icon = pystray.Icon("WinOTP", icon_32, "WinOTP", menu) # Use the extracted/resized 32x32 image
        return icon
    except Exception as e:
        print(f"Error creating tray icon: {e}")
        return None

# Lazy imports for modules not needed at startup
def import_lazy_modules():
    global pyotp, gzip, Image, scan_qr_image, calculate_offset, get_accurate_timestamp_30s
    
    try:
        import pyotp
        import gzip
        from PIL import Image
        from utils.qr_scanner import scan_qr_image
        from utils.ntp_sync import calculate_offset, get_accurate_timestamp_30s
        
        print("Lazy modules imported successfully")
    except Exception as e:
        print(f"Error in lazy module import: {str(e)}")

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
        self._settings_lock = threading.Lock()  # Add lock for thread-safe settings access

        # Sync startup setting with registry on initialization
        self._sync_startup_setting()
    
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
        """Scan a QR code from an image data URL"""
        try:
            # Ensure required modules are imported
            global Image
            if 'Image' not in globals() or Image is None:
                from PIL import Image
                print("Imported PIL.Image directly for QR scanning")
                
            # Ensure scan_qr_image is imported
            from utils.qr_scanner import scan_qr_image
            print("Imported scan_qr_image directly for QR scanning")
            
            # Decode base64 image
            image_data = base64.b64decode(image_data.split(',')[1])
            image = Image.open(io.BytesIO(image_data))
            
            # Scan QR code
            result = scan_qr_image(image)
            
            if not result:
                return {"status": "error", "message": "No QR code found"}
            
            # Check if the result is a string (Google Auth migration QR) or a tuple (regular TOTP QR)
            if isinstance(result, str):
                # For Google Auth migration QR, return the raw string
                return {"status": "success", "data": result}
            else:
                # For regular TOTP QR, return the tuple
                return {"status": "success", "data": result}
                
        except Exception as e:
            return {"status": "error", "message": f"Failed to scan QR code: {str(e)}"}

    def scan_qr_from_file(self, file_path):
        """Scan a QR code from a file"""
        try:
            # Ensure required modules are imported
            global Image
            if 'Image' not in globals() or Image is None:
                from PIL import Image
                print("Imported PIL.Image directly for QR scanning")
                
            # Ensure scan_qr_image is imported
            from utils.qr_scanner import scan_qr_image
            print("Imported scan_qr_image directly for QR scanning")
            
            # Scan QR code
            result = scan_qr_image(file_path)
            
            if not result:
                return {"status": "error", "message": "No QR code found"}
            
            # Check if the result is a string (Google Auth migration QR) or a tuple (regular TOTP QR)
            if isinstance(result, str):
                # For Google Auth migration QR, return the raw string
                return {"status": "success", "data": result}
            else:
                # For regular TOTP QR, return the tuple
                return {"status": "success", "data": result}
        except Exception as e:
            return {"status": "error", "message": f"Failed to scan QR code: {str(e)}"}

    def start_camera_scan(self):
        """Start camera-based QR code scanning"""
        try:
            # Import required modules
            import cv2
            from utils.qr_scanner import scan_qr_image
            from PIL import Image
            import io
            import numpy as np
            import threading
            
            def scan_camera():
                # Initialize camera
                cap = cv2.VideoCapture(0)
                if not cap.isOpened():
                    return {"status": "error", "message": "Failed to open camera"}
                
                try:
                    while True:
                        # Read frame from camera
                        ret, frame = cap.read()
                        if not ret:
                            break
                        
                        # Convert frame to PIL Image
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        pil_image = Image.fromarray(frame_rgb)
                        
                        # Scan for QR code
                        result = scan_qr_image(pil_image)
                        if result:
                            # Found a QR code, process it
                            issuer, secret, name = result
                            # Add token
                            add_result = self.add_token({
                                'issuer': issuer,
                                'name': name,
                                'secret': secret
                            })
                            
                            if add_result["status"] == "success":
                                # Show success notification
                                if self._window:
                                    self._window.evaluate_js(f'showNotification("{add_result["message"]}", "success")')
                                    self._window.evaluate_js('showMainPage()')
                            else:
                                # Show error notification
                                if self._window:
                                    self._window.evaluate_js(f'showNotification("{add_result["message"]}", "error")')
                            break
                        
                        # Show preview window
                        cv2.imshow('QR Code Scanner', frame)
                        
                        # Check for exit key (ESC)
                        if cv2.waitKey(1) & 0xFF == 27:
                            break
                
                finally:
                    # Clean up
                    cap.release()
                    cv2.destroyAllWindows()
            
            # Start scanning in a separate thread
            thread = threading.Thread(target=scan_camera)
            thread.daemon = True
            thread.start()
            
            return {"status": "success", "message": "Camera started"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to start camera: {str(e)}"}
    
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

    def import_tokens_from_authenticator_plugin(self, file_content):
        """Import tokens from an Authenticator Browser Plugin export file"""
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
            # Parse the Authenticator Plugin export using the importer, passing the callback
            parse_result = parse_authenticator_plugin_export(file_content, progress_callback)

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
                            print(f"Save operation failed after processing Authenticator Plugin tokens: {save_status.get('message')}")

                except Exception as save_e:
                    failed_adds = len(valid_tokens_data) # All parsed tokens failed if exception during save
                    save_status = {"status": "error", "message": f"Critical error during final save: {save_e}"}
                    print(f"Critical error during final Authenticator Plugin token save: {save_e}")

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
                 final_message = "No valid tokens found in the Authenticator Plugin export file to import." # Original warning message
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
            print(f"Unexpected error during Authenticator Plugin import process: {str(e)}")
            return {"status": "error", "message": f"Failed to import tokens from Authenticator Plugin: {str(e)}"}

    def get_icon_base64(self, icon_name):
        """Get base64 encoded icon data"""
        try:
            # First try to find the icon in the ui/static/icons directory
            base_dir = os.path.dirname(os.path.abspath(__file__))
            icon_paths = [
                os.path.join(base_dir, "ui", "static", "icons", icon_name),  # First try ui/static/icons
                os.path.join(base_dir, "static", "icons", icon_name)         # Fall back to static/icons
            ]
            
            # Try each path until we find the icon
            for icon_path in icon_paths:
                print(f"Looking for icon at: {icon_path}")
                
                # Check if the file exists
                if os.path.exists(icon_path):
                    # Read the file and encode as base64
                    with open(icon_path, "rb") as f:
                        icon_data = base64.b64encode(f.read()).decode("utf-8")
                    
                    print(f"Successfully loaded icon: {icon_name} from {icon_path}")
                    return {"status": "success", "data": icon_data}
                else:
                    print(f"Icon not found at: {icon_path}")
            
            # If we reach here, the icon was not found in any location
            return {"status": "error", "message": f"Icon not found: {icon_name}"}
            
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
        with self._settings_lock:
            # Define default values for known settings
            default_values = {
                "update_check_enabled": True,
                "minimize_to_tray": False,
                "run_at_startup": False,
                "next_code_preview_enabled": False
            }
            
            # If the key is not in settings but has a default value, add it
            if key in default_values and key not in self._settings:
                self._settings[key] = default_values[key]
                # Save the updated settings to file
                self._save_settings()
            
            # Special handling for run_at_startup to ensure registry sync
            if key == "run_at_startup":
                registry_state = startup.is_in_startup()
                if key not in self._settings or self._settings[key] != registry_state:
                    self._settings[key] = registry_state
                    self._save_settings()
                return registry_state
            
            return self._settings.get(key, default_values.get(key))

    def _save_settings(self):
        """Internal method to save settings and handle errors"""
        try:
            if save_settings(self._settings):
                return True
            return False
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False

    def get_current_version(self):
        """Get the current application version"""
        return asset_manager.CURRENT_VERSION

    def set_minimize_to_tray(self, enabled):
        """Set the minimize to tray setting"""
        try:
            with self._settings_lock:
                self._settings["minimize_to_tray"] = enabled
                if self._save_settings():
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

    def set_update_check_enabled(self, enabled):
        """Set the update check enabled setting"""
        try:
            with self._settings_lock:
                self._settings["update_check_enabled"] = enabled
                if self._save_settings():
                    return {"status": "success", "message": "Setting updated successfully"}
                return {"status": "error", "message": "Failed to save setting"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def set_next_code_preview(self, enabled):
        """Set the next code preview setting"""
        try:
            with self._settings_lock:
                self._settings["next_code_preview_enabled"] = enabled
                if self._save_settings():
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
            
            print(f"API: Setting protection timeout to {timeout_minutes}")
            
            # Rely *only* on the set_timeout function from utils.auth
            if set_timeout(timeout_minutes):
                print(f"Successfully set timeout to {timeout_minutes} using utils.auth.set_timeout")
                return {"status": "success", "message": "Protection timeout updated"}
            else:
                # If set_timeout failed, report the error directly
                print(f"Failed to set timeout using utils.auth.set_timeout")
                return {"status": "error", "message": "Failed to update protection timeout in auth config"}
                
        except ValueError:
            return {"status": "error", "message": "Invalid timeout value"}
        except Exception as e:
            # Catch any other unexpected errors from set_timeout or int conversion
            print(f"Error in API set_protection_timeout: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}

    def check_for_updates(self):
        """Get the current update status from asset_manager"""
        return asset_manager.get_update_status()
        
    def open_url(self, url):
        """Open a URL in the default web browser"""
        try:
            import webbrowser
            webbrowser.open(url)
            return {"status": "success", "message": "URL opened successfully"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to open URL: {str(e)}"}

    def download_update_file(self, url):
        """Download update file from GitHub release to the user's Downloads folder
        
        Args:
            url (str): URL of the file to download
            
        Returns:
            dict: Status and message, and download_path if successful
        """
        try:
            # Get the actual Downloads folder path from Windows Registry
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders') as key:
                    downloads_folder = winreg.QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')[0]
                print(f"Found Downloads folder in registry: {downloads_folder}")
            except Exception as e:
                print(f"Failed to get Downloads folder from registry: {e}")
                # Fallback to user profile Downloads folder
                downloads_folder = os.path.join(os.path.expanduser("~"), "Downloads")
                print(f"Using fallback Downloads folder: {downloads_folder}")
            
            # Check if the URL is an actual file or a release page
            if url.endswith('.exe'):
                # Direct file URL
                filename = url.split("/")[-1]
                is_direct_file = True
            else:
                # Release page URL - we need to extract the version to create a meaningful filename
                # Example: https://github.com/xBounceIT/WinOTP/releases/tag/v0.5.2
                version_match = re.search(r'tag/(v\d+\.\d+(?:\.\d+)?)', url)
                if version_match:
                    version = version_match.group(1)
                    filename = f"WinOTP_{version}_portable.exe"
                else:
                    filename = f"WinOTP_update.exe"
                is_direct_file = False
            
            # Add a timestamp to avoid overwriting existing files
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename_parts = filename.split(".")
            if len(filename_parts) > 1:
                # Insert timestamp before the extension
                filename = f"{'.'.join(filename_parts[:-1])}_{timestamp}.{filename_parts[-1]}"
            else:
                # No extension, just append timestamp
                filename = f"{filename}_{timestamp}"
            
            # Full path to save the file
            download_path = os.path.join(downloads_folder, filename)
            
            # Ensure the Downloads directory exists
            os.makedirs(downloads_folder, exist_ok=True)
            
            if is_direct_file:
                print(f"Downloading update from {url} to {download_path}")
                # Download the file
                urllib.request.urlretrieve(url, download_path)
                
                return {
                    "status": "success", 
                    "message": f"Update downloaded successfully to {download_path}",
                    "download_path": download_path
                }
            else:
                # If it's a release page URL, we should inform the user that they need to download manually
                print(f"Received release page URL instead of direct file URL: {url}")
                return {
                    "status": "error",
                    "message": "Direct download link not available. Please visit the releases page to download manually.",
                    "is_release_page": True,
                    "url": url
                }
        except Exception as e:
            print(f"Error downloading update: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": f"Failed to download update: {str(e)}"}

    def get_next_code(self, token_id):
        """Get the next TOTP code for a token"""
        global tokens
        try:
            if token_id not in tokens:
                return {"status": "error", "message": "Token not found"}

            token_data = tokens[token_id]
            token_obj = Token(
                token_data.get("issuer", "Unknown"),
                token_data.get("secret", ""),
                token_data.get("name", "Unknown")
            )

            # Get the current time and calculate the next interval
            current_time = get_accurate_time()
            next_interval = current_time + (30 - (current_time % 30))

            # Get the next code
            next_code = token_obj.totp.at(next_interval)

            return {"status": "success", "code": next_code}
        except Exception as e:
            print(f"Error getting next code for token {token_id}: {str(e)}")
            return {"status": "error", "message": str(e)}

    def import_tokens_from_google_auth_qr(self, qr_data):
        """Import tokens from Google Authenticator QR code"""
        try:
            # Use the dedicated module for Google Auth QR processing
            from utils.google_auth_qr import decode_migration_payload
            
            # Process the QR code data
            success, result = decode_migration_payload(qr_data)
            
            if not success:
                return {"status": "error", "message": result}
            
            # Got valid migration payload, now import the tokens
            migration_payload = result
            tokens_added = 0
            
            # Ensure pyotp is imported
            global pyotp
            if 'pyotp' not in globals() or pyotp is None:
                import pyotp
                print("Imported pyotp directly for Google Auth import")
                
            # Import base64 module if not already imported
            import base64
            
            # Add each token
            for otp_param in migration_payload.otp_parameters:
                try:
                    # Convert secret from bytes to base32 string
                    secret = base64.b32encode(otp_param.secret).decode('utf-8').rstrip('=')
                    
                    # Create TOTP object to validate secret
                    totp = pyotp.TOTP(secret)
                    
                    # Add token to database
                    self.add_token({
                        'issuer': otp_param.issuer or 'Unknown',
                        'name': otp_param.name or 'Unknown',
                        'secret': secret
                    })
                    tokens_added += 1
                    print(f"Added token for {otp_param.issuer or 'Unknown'} - {otp_param.name or 'Unknown'}")
                except Exception as e:
                    print(f"Error adding token: {str(e)}")
                    continue

            if tokens_added > 0:
                return {"status": "success", "message": f"Successfully imported {tokens_added} tokens", "tokens_count": tokens_added}
            else:
                return {"status": "error", "message": "No valid tokens found in QR code"}

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Failed to import tokens: {str(e)}")
            return {"status": "error", "message": f"Failed to import tokens: {str(e)}"}
            
    def initialize_google_auth_qr_scanner(self):
        """Initialize Google Authenticator QR scanner"""
        try:
            print("Initializing Google Authenticator QR scanner")
            # This is mainly a placeholder that just confirms the API call works
            # Actual processing will happen when scan_google_auth_qr is called
            return {"status": "success", "message": "QR scanner initialized"}
        except Exception as e:
            print(f"Error initializing Google Auth QR scanner: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def scan_google_auth_qr(self, file_path):
        """Scan a Google Authenticator QR code from a file"""
        try:
            print(f"Scanning Google Auth QR code from file: {file_path}")
            
            # Use the dedicated module for Google Auth QR scanning
            from utils.google_auth_qr import scan_google_auth_qr_from_file, decode_migration_payload
            
            # Scan the QR code
            scan_result = scan_google_auth_qr_from_file(file_path)
            
            if scan_result["status"] == "error":
                return scan_result
            
            # If scan successful, process the data
            qr_data = scan_result["data"]
            print(f"Successfully scanned QR code with data: {qr_data[:50]}...")
            
            # Process the QR code data
            success, result = decode_migration_payload(qr_data)
            
            if not success:
                return {"status": "error", "message": result}
            
            # Got valid migration payload, now import the tokens
            migration_payload = result
            tokens_added = 0
            
            # Ensure pyotp is imported
            global pyotp
            if 'pyotp' not in globals() or pyotp is None:
                import pyotp
                print("Imported pyotp directly for Google Auth import")
                
            # Import base64 module if not already imported
            import base64
            
            # Add each token
            for otp_param in migration_payload.otp_parameters:
                try:
                    # Convert secret from bytes to base32 string
                    secret = base64.b32encode(otp_param.secret).decode('utf-8').rstrip('=')
                    
                    # Create TOTP object to validate secret
                    totp = pyotp.TOTP(secret)
                    
                    # Add token to database
                    self.add_token({
                        'issuer': otp_param.issuer or 'Unknown',
                        'name': otp_param.name or 'Unknown',
                        'secret': secret
                    })
                    tokens_added += 1
                    print(f"Added token for {otp_param.issuer or 'Unknown'} - {otp_param.name or 'Unknown'}")
                except Exception as e:
                    print(f"Error adding token: {str(e)}")
                    continue

            if tokens_added > 0:
                return {"status": "success", "message": f"Successfully imported {tokens_added} tokens", "tokens_count": tokens_added}
            else:
                return {"status": "error", "message": "No valid tokens found in QR code"}
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error scanning Google Auth QR: {str(e)}")
            return {"status": "error", "message": f"Error scanning QR code: {str(e)}"}
            
    def finish_google_auth_import(self):
        """Finish Google Authenticator import process"""
        try:
            # Save tokens
            self.save_tokens()
            
            return {"status": "success", "message": "Google Authenticator import completed successfully"}
        except Exception as e:
            return {"status": "error", "message": f"Error completing import: {str(e)}"}

    def _sync_startup_setting(self):
        """Synchronizes the registry startup state with the saved setting."""
        try:
            with self._settings_lock:
                # Ensure the setting exists in the JSON file
                if "run_at_startup" not in self._settings:
                    self._settings["run_at_startup"] = startup.is_in_startup()
                    self._save_settings()
                
                should_run_at_startup = self._settings["run_at_startup"]
                is_currently_in_startup = startup.is_in_startup()

                logging.info(f"Startup sync: Saved setting={should_run_at_startup}, Registry state={is_currently_in_startup}")

                if should_run_at_startup and not is_currently_in_startup:
                    logging.info("Adding app to startup based on saved setting.")
                    if not startup.add_to_startup():
                        logging.error("Failed to add app to startup during sync.")
                elif not should_run_at_startup and is_currently_in_startup:
                    logging.info("Removing app from startup based on saved setting.")
                    if not startup.remove_from_startup():
                        logging.error("Failed to remove app from startup during sync.")
        except Exception as e:
            logging.error(f"Error during startup setting sync: {e}")

    def set_run_at_startup(self, enabled):
        """Sets the application's run at startup behavior."""
        try:
            with self._settings_lock:
                # First try to modify the startup shortcut
                if enabled:
                    operation_success = startup.add_to_startup()
                    message = "Added shortcut to startup folder." if operation_success else "Failed to add shortcut to startup folder."
                else:
                    operation_success = startup.remove_from_startup()
                    message = "Removed shortcut from startup folder." if operation_success else "Failed to remove shortcut from startup folder."

                if operation_success:
                    # Only update and save settings if shortcut operation was successful
                    self._settings["run_at_startup"] = enabled
                    save_success = self._save_settings()
                    
                    if save_success:
                        return {"status": "success", "message": message}
                    else:
                        # If settings save failed, try to revert shortcut change
                        if enabled:
                            startup.remove_from_startup()
                        else:
                            startup.add_to_startup()
                        return {"status": "error", "message": "Failed to save setting to file"}
                else:
                    # Include specific error message from startup functions if possible
                    # (Currently the startup functions log errors but return bool)
                    return {"status": "error", "message": message}

        except Exception as e:
            logging.error(f"Error in set_run_at_startup: {e}")
            return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}

    def clear_cache(self):
        """Clear the file cache"""
        try:
            clear_cache()
            return {"status": "success", "message": "Cache cleared"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to clear cache: {str(e)}"}

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
        tokens_path = os.path.abspath("tokens.json.dev")
        settings_path = os.path.abspath("app_settings.json.dev")
        AUTH_CONFIG_PATH = os.path.abspath("auth_config.json.dev")
        print(f"DEBUG MODE: Using local development files:")
        print(f"  - Tokens: {tokens_path}")
        print(f"  - Settings: {settings_path}")
        print(f"  - Auth Config: {AUTH_CONFIG_PATH}")
    else:
        # Use data directory paths for production mode (paths are already set globally)
        # Ensure these are absolute paths
        tokens_path = os.path.abspath(tokens_path)
        settings_path = os.path.abspath(settings_path)
        AUTH_CONFIG_PATH = os.path.abspath(AUTH_CONFIG_PATH)
        print(f"PRODUCTION MODE: Using files in {winotp_data_dir}:")
        print(f"  - Tokens: {tokens_path}")
        print(f"  - Settings: {settings_path}")
        print(f"  - Auth Config: {AUTH_CONFIG_PATH}")

    # --- Set the authentication file path for the auth utility module ---
    set_auth_path(AUTH_CONFIG_PATH) 

    # Verify if files exist, create them if they don't
    for path, default_content in [
        (tokens_path, {}),
        (settings_path, {"minimize_to_tray": False, "update_check_enabled": True, "run_at_startup": False}),
        (AUTH_CONFIG_PATH, {"timeout_minutes": 0})
    ]:
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"Created directory: {directory}")
            except OSError as e:
                print(f"Error creating directory {directory}: {e}")
                
        if not os.path.exists(path):
            try:
                with open(path, 'w') as f:
                    json.dump(default_content, f, indent=4)
                print(f"Created default file: {path}")
            except Exception as e:
                print(f"Error creating file {path}: {e}")

    # Start update check in a background thread
    print("Starting background update check...")
    update_thread = threading.Thread(target=asset_manager.check_for_updates, daemon=True)
    update_thread.start()

    # Create API instance (which will load settings and tokens based on the set paths)
    api = Api()

    # Copy static files to ui directory if they don't exist - this ensures the web server can find them
    ui_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "static")
    static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
    
    # Ensure ui/static directories exist
    os.makedirs(os.path.join(ui_static_dir, "js"), exist_ok=True)
    os.makedirs(os.path.join(ui_static_dir, "css"), exist_ok=True)
    os.makedirs(os.path.join(ui_static_dir, "icons"), exist_ok=True)
    
    # List of files to copy if they don't exist in ui/static
    files_to_copy = [
        ("js", "bootstrap.bundle.min.js"),
        ("js", "jquery-3.6.0.min.js"),
        ("css", "bootstrap.min.css"),
    ]
    
    # Copy each file if it doesn't exist in ui/static
    for subdir, filename in files_to_copy:
        src = os.path.join(static_dir, subdir, filename)
        dst = os.path.join(ui_static_dir, subdir, filename)
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                import shutil
                shutil.copy2(src, dst)
                print(f"Copied {src} to {dst}")
            except Exception as e:
                print(f"Error copying {src} to {dst}: {e}")
    
    # Also copy all icon files
    icon_src_dir = os.path.join(static_dir, "icons")
    icon_dst_dir = os.path.join(ui_static_dir, "icons")
    if os.path.exists(icon_src_dir):
        for icon_file in os.listdir(icon_src_dir):
            src = os.path.join(icon_src_dir, icon_file)
            dst = os.path.join(icon_dst_dir, icon_file)
            if os.path.isfile(src) and not os.path.exists(dst):
                try:
                    import shutil
                    shutil.copy2(src, dst)
                    print(f"Copied icon {src} to {dst}")
                except Exception as e:
                    print(f"Error copying icon {src} to {dst}: {e}")
    
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
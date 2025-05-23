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
from utils.single_instance import is_already_running, activate_existing_window

# Globals for on-demand imports
pyotp = None
pyzbar = None
Image = None

# Path to the user's app data directory (new location in AppData)
winotp_data_dir = os.path.join(os.path.expandvars('%APPDATA%'), 'WinOTP')

# Path to the old data directory (in Documents)
old_winotp_data_dir = os.path.join(os.path.expanduser('~'), 'Documents', 'WinOTP')

# Global file paths with default values for app data directory
tokens_path = os.path.join(winotp_data_dir, 'tokens.json')
settings_path = os.path.join(winotp_data_dir, 'app_settings.json')
AUTH_CONFIG_PATH = os.path.join(winotp_data_dir, 'auth_config.json')

# Lock for file operations
file_write_lock = threading.Lock()

sort_ascending = True  # Default sort order
tray_icon = None

# Define a custom Icon class for Windows that handles double-click
if sys.platform == 'win32':
    class Win32PystrayIcon(pystray.Icon):
        # Windows message constants
        WM_LBUTTONDBLCLK = 0x0203
        
        def _on_notify(self, wparam, lparam):
            # Call the parent method to handle standard events
            super()._on_notify(wparam, lparam)
            
            # Check if the event is a double-click
            if lparam == self.WM_LBUTTONDBLCLK:
                # Show and restore the window (same as "Show" menu item)
                if hasattr(self, '_window'):
                    self._window.show()
                    self._window.restore()
    
    # Replace the default pystray.Icon with our custom class
    CustomIcon = Win32PystrayIcon
else:
    # On other platforms, use the standard Icon class
    CustomIcon = pystray.Icon

def load_settings():
    """Load application settings"""
    try:
        default_settings = {
            "minimize_to_tray": False,
            "update_check_enabled": True,
            "run_at_startup": False,
            "next_code_preview_enabled": False,
            "backup_to_google_drive": False,
            "last_backup_date_google_drive": "",
            "backup_to_onedrive": False,
            "last_backup_date_onedrive": ""
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
    print("=== Entered save_settings ===")
    try:
        # Get old settings to compare
        old_settings = {}
        if os.path.exists(settings_path):
            old_settings = load_settings()
        
        # Save the new settings
        write_json(settings_path, settings)
        
        # Debug: print current and old settings before checking OneDrive backup condition
        print(f"DEBUG: settings = {settings}")
        print(f"DEBUG: old_settings = {old_settings}")
        # Always check if OneDrive backup is enabled and if backup has not been executed today on OneDrive
        if settings.get('backup_to_onedrive', False):
            print("DEBUG: Checking OneDrive for today's backup file...")
            try:
                from utils.onedrive_backup import check_backup_exists, upload_tokens_json_to_onedrive
                backup_exists = check_backup_exists()
                print(f"DEBUG: check_backup_exists returned {backup_exists}")
                if not backup_exists:
                    print("OneDrive backup enabled and not yet run today (no file found), triggering backup...")
                    backup_success = upload_tokens_json_to_onedrive(local_file_path=tokens_path)
                    if backup_success:
                        from datetime import datetime
                        today_str = datetime.now().strftime('%Y-%m-%d')
                        settings['last_backup_date_onedrive'] = today_str
                        write_json(settings_path, settings)
                        print("OneDrive backup completed and last_backup_date_onedrive updated.")
                    else:
                        print("OneDrive backup failed: Backup was not uploaded to OneDrive. last_backup_date_onedrive NOT updated.")
                else:
                    print("OneDrive backup already exists for today; skipping.")
            except Exception as backup_exc:
                print(f"Error during OneDrive backup: {backup_exc}")
                import traceback
                traceback.print_exc()
                import traceback
                print("Error during immediate OneDrive backup.")
                traceback.print_exc()
    except Exception as e:
        print(f"Error saving settings (outer except): {e}")
        import traceback
        traceback.print_exc()
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
            # Force application exit
            os._exit(0)

        # Create the tray icon using the 32x32 image
        menu = (
            pystray.MenuItem("Show", show_window),
            pystray.MenuItem("Quit", quit_app)
        )
        
        # Create the icon using our custom class
        icon = CustomIcon("WinOTP", icon_32, "WinOTP", menu) # Use the extracted/resized 32x32 image
        
        # Store a reference to the window for the double-click handler
        if sys.platform == 'win32':
            icon._window = window
            
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
        
        # Initialize tokens as None - will load on first request
        self._tokens_loaded = False
        self.tokens = {}
        self.last_tokens_update = 0
        
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
        
        # Expose all required API methods to the webview
        window.expose(
            self.get_icon_base64,
            self.get_auth_status,
            self.get_tokens,
            self.verify_authentication,
            self.add_token,
            self.update_token,
            self.delete_token,
            self.scan_qr_code,
            self.scan_qr_from_file,
            self.capture_screen_for_qr,
            self.get_ntp_status,
            self.toggle_sort_order,
            self.add_token_from_uri,
            self.import_tokens_from_json,
            self.import_tokens_from_2fas,
            self.import_tokens_from_authenticator_plugin,
            self.export_tokens_to_json,
            self.get_minimize_to_tray,
            self.get_setting,
            self.set_setting,
            self.set_minimize_to_tray,
            self.set_update_check_enabled,
            self.set_next_code_preview,
            self.set_protection_timeout,
            self.set_pin_protection,
            self.set_password_protection,
            self.disable_protection,
            self.check_for_updates,
            self.open_url,
            self.download_update_file,
            self.get_next_code,
            self.import_tokens_from_google_auth_qr,
            self.scan_google_auth_qr,
            self.finish_google_auth_import,
            self.set_run_at_startup,
            self.clear_cache,
            self.get_fresh_token_code,
            self.batch_get_token_codes
        )
    
    def load_tokens(self):
        """Load tokens from the tokens file"""
        print(f"--- Enter load_tokens --- ")
        print(f"    Current tokens_path: {tokens_path}")
        print(f"    Current settings_path: {settings_path}")
        print(f"    Current AUTH_CONFIG_PATH: {AUTH_CONFIG_PATH}")
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
                
                self.tokens = valid_tokens
                self.last_tokens_update = time.time()
                print(f"Successfully processed {len(self.tokens)} tokens loaded from {tokens_path}")
                return {"status": "success", "message": f"Loaded {len(self.tokens)} tokens"}
            
            print(f"No valid tokens found in file: {tokens_path}")
            self.tokens = {}  # Reset to empty dict if invalid data
            return {"status": "warning", "message": "No valid tokens found"}
        except Exception as e:
            print(f"Failed to load tokens: {str(e)}")
            self.tokens = {}  # Reset to empty dict on error
            return {"status": "error", "message": f"Failed to load tokens: {str(e)}"}
    
    def save_tokens(self):
        """Save tokens to the tokens file"""
        try:
            with file_write_lock:
                # Get current auth type and credentials
                auth_type = get_auth_type()
                config = read_json(AUTH_CONFIG_PATH) or {}
                
                # First write tokens to file without encryption
                write_json(tokens_path, self.tokens)
                
                # Then encrypt if auth is enabled
                if auth_type == "pin":
                    success = encrypt_tokens_file(tokens_path, config.get("pin_hash", ""))
                elif auth_type == "password":
                    success = encrypt_tokens_file(tokens_path, config.get("password_hash", ""))
                else:
                    success = True
                
                if success:
                    self.last_tokens_update = time.time()
                    return {"status": "success", "message": "Tokens saved successfully"}
                else:
                    return {"status": "error", "message": "Failed to save tokens"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to save tokens: {str(e)}"}
    
    def get_tokens(self):
        """Get all tokens with their current codes"""
        result = []
        
        # Load tokens if not already loaded
        if not self._tokens_loaded:
            self.load_tokens()
            
        # Check if we need to reload tokens from disk
        self.check_reload_tokens()
        
        # Get current time for TOTP generation
        current_time = get_accurate_time()
        
        for token_id, token_data in self.tokens.items():
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
        try:
            # Check if file has been modified since last load
            if os.path.exists(tokens_path):
                file_mtime = os.path.getmtime(tokens_path)
                if file_mtime > self.last_tokens_update:
                    self.load_tokens()
        except Exception:
            # Ignore errors, will try again next time
            pass
    
    def add_token(self, token_data):
        """Add a new token"""
        try:
            # Validate token data
            if not token_data.get("secret"):
                return {"status": "error", "message": "Secret is required"}
            
            # Generate token ID
            token_id = str(uuid.uuid4())
            
            # Add created timestamp
            token_data["created"] = datetime.now().isoformat()
            
            # Add token to tokens
            self.tokens[token_id] = token_data
            
            # Save tokens
            save_result = self.save_tokens()
            if save_result["status"] != "success":
                return save_result
            
            return {"status": "success", "message": "Token added successfully", "id": token_id}
        except Exception as e:
            return {"status": "error", "message": f"Failed to add token: {str(e)}"}
    
    def update_token(self, token_id, data):
        """Update token details"""
        try:
            # Check if token exists
            if token_id not in self.tokens:
                return {"status": "error", "message": "Token not found"}
            
            # Update token details
            self.tokens[token_id]["issuer"] = data.get("issuer", self.tokens[token_id]["issuer"])
            self.tokens[token_id]["name"] = data.get("name", self.tokens[token_id]["name"])
            
            # Save tokens
            save_result = self.save_tokens()
            if save_result["status"] != "success":
                return save_result
            
            return {"status": "success", "message": "Token updated successfully"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to update token: {str(e)}"}
    
    def delete_token(self, token_id):
        """Delete a token"""
        try:
            # Check if token exists
            if token_id not in self.tokens:
                return {"status": "error", "message": "Token not found"}
            
            # Delete token
            del self.tokens[token_id]
            
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

    def capture_screen_for_qr(self):
        """Capture a screen region and scan for QR codes"""
        try:
            # Import required modules
            from utils.screen_selector import select_screen_region
            from utils.screen_capture import capture_screen_region, process_captured_image
            from utils.qr_scanner import scan_qr_image

            # First, prompt the user to select a region
            print("Prompting user to select screen region...")
            region_result = select_screen_region()
            
            if region_result["status"] != "success":
                logging.warning(f"Screen region selection cancelled or failed: {region_result['message']}")
                return region_result  # Return the error or cancellation
            
            # Capture the selected region
            region = region_result["region"]
            print(f"Capturing screen region: {region}")
            capture_result = capture_screen_region(region)
            
            if capture_result["status"] != "success":
                logging.error(f"Screen capture failed: {capture_result['message']}")
                return capture_result  # Return the error
            
            # Process the captured image
            screenshot = capture_result["image"]
            process_result = process_captured_image(screenshot)
            
            if process_result["status"] != "success":
                logging.error(f"Image processing failed: {process_result['message']}")
                return process_result  # Return the error
            
            # Scan the processed image for QR codes
            processed_image = process_result["image"]
            print("Scanning captured image for QR codes...")
            qr_result = scan_qr_image(processed_image)
            
            if not qr_result:
                logging.warning("No QR code found in the captured image")
                return {"status": "error", "message": "No QR code found in the captured region"}
            
            # Check if the result is a string (Google Auth migration QR) or a tuple (regular TOTP QR)
            if isinstance(qr_result, str):
                # For Google Auth migration QR, return the raw string
                return {"status": "success", "data": qr_result}
            else:
                # For regular TOTP QR, convert the tuple to a dictionary
                # The tuple format is (issuer, secret, name)
                issuer, secret, name = qr_result
                token_data = {
                    "issuer": issuer,
                    "secret": secret,
                    "name": name
                }
                return {"status": "success", "data": token_data}
                
        except Exception as e:
            import traceback
            logging.error(f"Error in screen capture QR scanning: {e}")
            logging.error(traceback.format_exc())
            return {"status": "error", "message": f"Failed to scan QR code from screen: {str(e)}"}

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
                        self.tokens[token_id] = token_data
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
                            self.tokens[token_id] = token_data
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
                            self.tokens[token_id] = token_data
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

                
                # Check if the file exists
                if os.path.exists(icon_path):
                    # Read the file and encode as base64
                    with open(icon_path, "rb") as f:
                        icon_data = base64.b64encode(f.read()).decode("utf-8")
                    

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
            # Encrypt the tokens file with the new PIN (use the raw pin, not the hash)
            if encrypt_tokens_file(tokens_path, pin):
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
            # Encrypt the tokens file with the new password (use the raw password, not the hash)
            if encrypt_tokens_file(tokens_path, password):
                return {"status": "success", "message": "Password protection enabled"}
            else:
                # If encryption fails, clear the password
                clear_auth()
                return {"status": "error", "message": "Failed to encrypt tokens with password"}
        else:
            return {"status": "error", "message": "Failed to set password protection"}
    
    def disable_protection(self, credential):
        """Disable PIN/password protection after verifying the current credential"""
        auth_type = get_auth_type()
        config = read_json(AUTH_CONFIG_PATH) or {}
        
        # Verify the provided credential first
        if auth_type == "pin":
            if not verify_pin(credential):
                return {"status": "error", "message": "Incorrect PIN provided"}
        elif auth_type == "password":
            if not verify_password(credential):
                return {"status": "error", "message": "Incorrect password provided"}
        else:
            # No protection enabled, nothing to disable (should ideally not be called)
            return {"status": "warning", "message": "Protection is already disabled"}

        # If verification passed, proceed with decryption using the raw credential
        print(f"Verification successful for disabling {auth_type} protection.")
        
        try:
            if auth_type == "pin":
                # Decrypt using the verified raw PIN
                current_tokens = decrypt_tokens_file(tokens_path, credential) 
            elif auth_type == "password":
                # Decrypt using the verified raw password
                current_tokens = decrypt_tokens_file(tokens_path, credential)
            # No 'else' needed here because we handled 'None' auth_type earlier

            if current_tokens is None:
                # Decryption failed even after verification, which is unexpected
                print("Error: Decryption failed after successful verification.")
                return {"status": "error", "message": "Failed to decrypt tokens even with correct credential. Please report this issue."}

            # Clear the authentication settings in the config file
            if clear_auth():
                # Set timeout to 0 (never) when disabling protection
                set_timeout(0)
                
                # Save the decrypted tokens without encryption
                try:
                    write_json(tokens_path, current_tokens)
                    # Reset authentication state in the API instance
                    self.is_authenticated = False 
                    self.last_auth_time = None
                    print("Protection successfully disabled.")
                    return {"status": "success", "message": "Protection disabled"}
                except Exception as e:
                    # Attempt to re-enable auth if saving decrypted tokens failed
                    print(f"Error saving unencrypted tokens: {e}. Attempting to restore protection...")
                    if auth_type == "pin": set_pin(credential) 
                    if auth_type == "password": set_password(credential)
                    # Re-encrypt the file (best effort)
                    encrypt_tokens_file(tokens_path, credential) 
                    return {"status": "error", "message": f"Failed to save unencrypted tokens: {str(e)}. Protection may not be fully disabled."}
            else:
                print("Error: Failed to clear authentication settings.")
                return {"status": "error", "message": "Failed to clear authentication settings in config."}
        except Exception as e:
             print(f"Unexpected error during decryption/saving in disable_protection: {e}")
             import traceback
             traceback.print_exc()
             return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}
    
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
            json_str = json.dumps(self.tokens, indent=4)
            
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
                "next_code_preview_enabled": False,
                "backup_to_google_drive": False
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
            
    def set_setting(self, key, value):
        """Set a specific application setting"""
        with self._settings_lock:
            # Special handling for OneDrive backup - don't save setting until after authentication
            if key == "backup_to_onedrive" and value == True:
                try:
                    # Trigger OneDrive authentication immediately
                    from utils.onedrive_backup import get_auth_token
                    token_result = get_auth_token()
                    
                    # Check if authentication was cancelled or failed
                    if token_result is None:
                        print("OneDrive authentication was cancelled by user")
                        return {"status": "cancelled", "message": "OneDrive authentication was cancelled"}
                    if "access_token" not in token_result:
                        print("OneDrive authentication failed")
                        return {"status": "error", "message": "Failed to authenticate with OneDrive"}
                    
                    # Only save the setting after successful authentication
                    self._settings[key] = value
                    success = self._save_settings()
                    if success:
                        # Trigger immediate backup after enabling
                        try:
                            from utils.onedrive_backup import upload_tokens_json_to_onedrive
                            # Run backup in a separate thread to avoid blocking
                            import threading
                            backup_thread = threading.Thread(target=upload_tokens_json_to_onedrive, args=('tokens.json',))
                            backup_thread.daemon = True
                            backup_thread.start()
                            return {"status": "success", "message": "OneDrive backup enabled and authenticated. Initial backup started."}
                        except Exception as e:
                            print(f"Error starting initial OneDrive backup: {e}")
                            # Don't fail if just the initial backup fails
                            return {"status": "success", "message": "OneDrive backup enabled and authenticated, but initial backup failed."} 
                    else:
                        return {"status": "error", "message": "Failed to save settings after authentication"}
                except Exception as e:
                    print(f"Error authenticating with OneDrive: {e}")
                    return {"status": "error", "message": f"Failed to authenticate with OneDrive: {str(e)}"}
            
            # Special handling for Google Drive backup
            elif key == "backup_to_google_drive" and value == True:
                try:
                    # Trigger Google Drive authentication immediately (don't save setting until successful)
                    from utils.drive_backup import authenticate_google_drive
                    service = authenticate_google_drive()
                    
                    # Check if authentication was cancelled or failed
                    if service is None:
                        print("Google Drive authentication was cancelled or failed")
                        return {"status": "cancelled", "message": "Google Drive authentication was cancelled"}
                    
                    # Only save the setting after successful authentication
                    self._settings[key] = value
                    success = self._save_settings()
                    if success:
                        # Trigger immediate backup after enabling
                        try:
                            from utils.drive_backup import upload_tokens_json_to_drive
                            # Run backup in a separate thread to avoid blocking
                            import threading
                            backup_thread = threading.Thread(target=upload_tokens_json_to_drive, args=('tokens.json',))
                            backup_thread.daemon = True
                            backup_thread.start()
                            return {"status": "success", "message": "Google Drive backup enabled and authenticated. Initial backup started."}
                        except Exception as e:
                            print(f"Error starting initial Google Drive backup: {e}")
                            # Don't fail if just the initial backup fails
                            return {"status": "success", "message": "Google Drive backup enabled and authenticated, but initial backup failed."}
                    else:
                        return {"status": "error", "message": "Failed to save settings after authentication"}
                except Exception as e:
                    print(f"Error authenticating with Google Drive: {e}")
                    return {"status": "error", "message": f"Failed to authenticate with Google Drive: {str(e)}"}
            
            # For all other settings, just save normally
            else:
                self._settings[key] = value
                success = self._save_settings()
                
                if success:
                    return {"status": "success", "message": f"Setting '{key}' updated successfully"}
                else:
                    return {"status": "error", "message": f"Failed to update setting '{key}'"}

    def _save_settings(self):
        """Internal method to save settings and handle errors"""
        try:
            logging.info(f"Attempting to save settings: {self._settings}")
            print(f"Attempting to save settings: {self._settings}")
            
            # Get file path for logging
            logging.info(f"Settings path: {settings_path}")
            print(f"Settings path: {settings_path}")
            
            # First verify we have write permissions
            try:
                if os.path.exists(settings_path):
                    # Try a quick test write to check permissions
                    with open(settings_path, 'a') as f:
                        pass
                    logging.info("Write permission check passed")
                    print("Write permission check passed")
                else:
                    directory = os.path.dirname(settings_path)
                    if not os.path.exists(directory):
                        os.makedirs(directory, exist_ok=True)
                        logging.info(f"Created directory: {directory}")
                        print(f"Created directory: {directory}")
            except Exception as e:
                logging.error(f"Permission or path error: {e}")
                print(f"Permission or path error: {e}")
                return False
            
            # Now try to save
            if save_settings(self._settings):
                logging.info("Settings saved successfully")
                print("Settings saved successfully")
                
                # Verify the save actually worked
                try:
                    saved_settings = read_json(settings_path)
                    if saved_settings.get("run_at_startup") == self._settings.get("run_at_startup"):
                        logging.info("Settings verification passed")
                        print("Settings verification passed")
                    else:
                        logging.warning(f"Settings verification failed. Expected: {self._settings}, got: {saved_settings}")
                        print(f"Settings verification failed. Expected: {self._settings}, got: {saved_settings}")
                except Exception as e:
                    logging.error(f"Settings verification error: {e}")
                    print(f"Settings verification error: {e}")
                
                return True
            
            logging.error("Failed to save settings using save_settings function")
            print("Failed to save settings using save_settings function")
            
            # Try direct file writing as fallback
            try:
                with open(settings_path, 'w') as f:
                    json.dump(self._settings, f, indent=4)
                    logging.info("Settings saved via direct file writing")
                    print("Settings saved via direct file writing")
                return True
            except Exception as e:
                logging.error(f"Direct file writing failed: {e}")
                print(f"Direct file writing failed: {e}")
                return False
        except Exception as e:
            logging.error(f"Error in _save_settings: {e}")
            print(f"Error in _save_settings: {e}")
            import traceback
            traceback.print_exc()
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
        try:
            if token_id not in self.tokens:
                return {"status": "error", "message": "Token not found"}

            token_data = self.tokens[token_id]
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

                # First check if shortcut path needs updating (if app was moved)
                if is_currently_in_startup:
                    startup.check_and_update_startup_shortcut()

                # Then handle adding/removing from startup based on settings
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
            logging.info(f"Setting run_at_startup to {enabled}")
            print(f"Setting run_at_startup to {enabled}")
            
            with self._settings_lock:
                # Check current settings before modification
                logging.info(f"Current settings before modification: {self._settings}")
                print(f"Current settings before modification: {self._settings}")
                
                # First try to modify the startup shortcut
                if enabled:
                    operation_success = startup.add_to_startup()
                    message = "Added shortcut to startup folder." if operation_success else "Failed to add shortcut to startup folder."
                else:
                    operation_success = startup.remove_from_startup()
                    message = "Removed shortcut from startup folder." if operation_success else "Failed to remove shortcut from startup folder."

                logging.info(f"Startup operation success: {operation_success}, message: {message}")
                print(f"Startup operation success: {operation_success}, message: {message}")

                if operation_success:
                    # Only update and save settings if shortcut operation was successful
                    self._settings["run_at_startup"] = enabled
                    logging.info(f"Updated in-memory settings: {self._settings}")
                    print(f"Updated in-memory settings: {self._settings}")
                    
                    # Try multiple approaches to ensure the setting is saved
                    
                    # 1. First try using the write_json function directly
                    try:
                        write_json(settings_path, self._settings)
                        logging.info(f"Settings saved directly using write_json to {settings_path}")
                        print(f"Settings saved directly using write_json to {settings_path}")
                    except Exception as e:
                        logging.error(f"Direct write_json failed: {e}")
                        print(f"Direct write_json failed: {e}")
                    
                    # 2. Then try the save_settings function
                    save_success = save_settings(self._settings)
                    logging.info(f"Settings save result (save_settings): {save_success}")
                    print(f"Settings save result (save_settings): {save_success}")
                    
                    # 3. Then try the internal method as fallback
                    if not save_success:
                        save_success = self._save_settings()
                        logging.info(f"Fallback settings save result (_save_settings): {save_success}")
                        print(f"Fallback settings save result (_save_settings): {save_success}")
                    
                    # 4. Final fallback: direct file writing
                    if not save_success:
                        try:
                            with open(settings_path, 'w') as f:
                                json.dump(self._settings, f, indent=4)
                                f.flush()
                                os.fsync(f.fileno())
                            logging.info(f"Final fallback: Direct file writing to {settings_path} completed")
                            print(f"Final fallback: Direct file writing to {settings_path} completed")
                            save_success = True
                        except Exception as e:
                            logging.error(f"All save attempts failed, final error: {e}")
                            print(f"All save attempts failed, final error: {e}")
                    
                    # Verify settings were saved
                    try:
                        with open(settings_path, 'r') as f:
                            current_settings = json.load(f)
                        logging.info(f"Verification - settings read from file: {current_settings}")
                        print(f"Verification - settings read from file: {current_settings}")
                        
                        # Check if the run_at_startup value matches what we expect
                        if current_settings.get("run_at_startup") == enabled:
                            logging.info(f"Verification SUCCESS: run_at_startup is correctly set to {enabled}")
                            print(f"Verification SUCCESS: run_at_startup is correctly set to {enabled}")
                        else:
                            logging.error(f"Verification FAILED: run_at_startup should be {enabled} but is {current_settings.get('run_at_startup')}")
                            print(f"Verification FAILED: run_at_startup should be {enabled} but is {current_settings.get('run_at_startup')}")
                    except Exception as e:
                        logging.error(f"Error during verification read: {e}")
                        print(f"Error during verification read: {e}")
                    
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
            print(f"Error in set_run_at_startup: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": f"An unexpected error occurred: {str(e)}"}

    def clear_cache(self):
        """Clear the file cache"""
        try:
            clear_cache()
            return {"status": "success", "message": "Cache cleared"}
        except Exception as e:
            return {"status": "error", "message": f"Failed to clear cache: {str(e)}"}

    def start_qr_scanning(self):
        """
        [DEPRECATED] Start QR scanning - now redirects to screen capture method
        
        This method is maintained for backward compatibility and redirects to the
        new screen capture based QR scanning method.
        """
        import logging
        logging.warning("start_qr_scanning is deprecated, using capture_screen_for_qr instead")
        print("Camera scanning is deprecated, using screen capture instead")
        
        # Call the new screen capture method
        return self.capture_screen_for_qr()
    
    def stop_qr_scanning(self):
        """
        [DEPRECATED] Stop QR scanning
        
        This method is maintained for backward compatibility but does nothing
        as the screen capture QR scanning doesn't need to be stopped.
        """
        import logging
        logging.warning("stop_qr_scanning is deprecated and does nothing")
        return {"status": "success", "message": "Screen capture QR scanning doesn't need to be stopped"}
    
    def get_qr_scan_result(self):
        """
        [DEPRECATED] Get QR scan result
        
        This method is maintained for backward compatibility but always returns
        no result as the screen capture QR scanning delivers results immediately.
        """
        import logging
        logging.warning("get_qr_scan_result is deprecated and always returns no result")
        return {"status": "success", "data": None}
    
    def check_camera_permission(self):
        """
        [DEPRECATED] Check camera permission
        
        This method is maintained for backward compatibility but always returns
        permission denied as camera scanning is no longer used.
        """
        import logging
        logging.warning("check_camera_permission is deprecated and always returns denied")
        return {"status": "success", "granted": False, "message": "Camera scanning is deprecated, using screen capture instead"}
    
    def request_camera_permission(self):
        """
        [DEPRECATED] Request camera permission
        
        This method is maintained for backward compatibility but always returns
        permission denied as camera scanning is no longer used.
        """
        import logging
        logging.warning("request_camera_permission is deprecated and always returns denied")
        return {"status": "success", "granted": False, "message": "Camera scanning is deprecated, using screen capture instead"}

    def get_fresh_token_code(self, token_id):
        """Get a fresh token code for a specific token ID without reloading all tokens"""
        try:
            # Check if token exists in memory
            if token_id not in self.tokens:
                return {"status": "error", "message": "Token not found"}
            
            token_data = self.tokens[token_id]
            
            # Create Token object
            token_obj = Token(
                token_data.get("issuer", "Unknown"),
                token_data.get("secret", ""),
                token_data.get("name", "Unknown")
            )
            
            # Get the current code and time remaining
            code = token_obj.get_code()
            time_remaining = token_obj.get_time_remaining()
            
            return {
                "status": "success",
                "id": token_id,
                "code": code,
                "timeRemaining": time_remaining
            }
        except Exception as e:
            return {"status": "error", "message": f"Error generating code: {str(e)}"}
            
    def batch_get_token_codes(self, token_ids):
        """Get fresh token codes for multiple token IDs in a single batch operation"""
        try:
            results = {}
            
            # Process only tokens that exist in memory
            for token_id in token_ids:
                if token_id not in self.tokens:
                    results[token_id] = {
                        "status": "error", 
                        "message": "Token not found"
                    }
                    continue
                
                token_data = self.tokens[token_id]
                
                # Create Token object
                token_obj = Token(
                    token_data.get("issuer", "Unknown"),
                    token_data.get("secret", ""),
                    token_data.get("name", "Unknown")
                )
                
                # Get the current code and time remaining
                code = token_obj.get_code()
                time_remaining = token_obj.get_time_remaining()
                
                # Store in results
                results[token_id] = {
                    "status": "success",
                    "id": token_id,
                    "code": code,
                    "timeRemaining": time_remaining,
                    "nextCode": token_obj.totp.at(get_accurate_time() + (30 - time_remaining))
                }
            
            return {
                "status": "success",
                "results": results
            }
        except Exception as e:
            return {"status": "error", "message": f"Error generating codes in batch: {str(e)}"}

def set_tokens_path(path):
    """Set the path to the tokens file"""
    global tokens_path
    tokens_path = path

def start_sync_startup_setting(api):
    """Background thread function to sync startup setting"""
    time.sleep(2)  # Give webview time to initialize
    api._sync_startup_setting()

def migrate_data_from_old_location():
    """Migrate data from old Documents location to new AppData location if needed.
    After successful migration, delete the old data directory."""
    import shutil
    if not os.path.exists(old_winotp_data_dir):
        print(f"No old data directory found at {old_winotp_data_dir}")
        return False

    print(f"Found old data directory at {old_winotp_data_dir}, migrating data...")

    # Make sure the new directory exists
    os.makedirs(winotp_data_dir, exist_ok=True)

    # List of files to migrate
    files_to_migrate = ['tokens.json', 'app_settings.json', 'auth_config.json']
    migrated_files = []

    for filename in files_to_migrate:
        old_path = os.path.join(old_winotp_data_dir, filename)
        new_path = os.path.join(winotp_data_dir, filename)

        # Only migrate if the old file exists and the new one doesn't
        if os.path.exists(old_path) and not os.path.exists(new_path):
            try:
                shutil.copy2(old_path, new_path)
                migrated_files.append(filename)
                print(f"Migrated {filename} from Documents to AppData")
            except Exception as e:
                print(f"Error migrating {filename}: {e}")

    # After migration, delete the old directory if any files were migrated
    if migrated_files:
        try:
            shutil.rmtree(old_winotp_data_dir)
            print(f"Old data directory {old_winotp_data_dir} deleted after migration.")
        except Exception as e:
            print(f"Error deleting old data directory {old_winotp_data_dir}: {e}")

    return len(migrated_files) > 0

def main():
    # Check if debug mode is enabled via command line arguments
    debug_mode = "--debug" in sys.argv or "-d" in sys.argv

    # Select the appropriate file paths based on mode
    global tokens_path, settings_path, AUTH_CONFIG_PATH # Declare globals to modify them
    if debug_mode:
        # Use local .dev files for debug mode
        tokens_path = os.path.abspath("tokens.json.dev")
        settings_path = os.path.abspath("app_settings.json.dev")
        AUTH_CONFIG_PATH = os.path.abspath("auth_config.json.dev")
        # Set Google Drive and OneDrive token paths to utils folder in debug mode
        utils_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'utils')
        DRIVE_PICKLE_PATH = os.path.join(utils_dir, 'token_drive.pickle')
        ONEDRIVE_TOKEN_PATH = os.path.join(utils_dir, 'token_onedrive.json')
        # Patch the token path globals in the backup modules
        import utils.drive_backup as drive_backup
        import utils.onedrive_backup as onedrive_backup
        drive_backup.TOKEN_PATH = DRIVE_PICKLE_PATH
        onedrive_backup.TOKEN_PATH = ONEDRIVE_TOKEN_PATH
        print(f"DEBUG MODE: Using local development files:")
        print(f"  - Tokens: {tokens_path}")
        print(f"  - Settings: {settings_path}")
        print(f"  - Auth Config: {AUTH_CONFIG_PATH}")
        print(f"  - Google Drive pickle: {DRIVE_PICKLE_PATH}")
        print(f"  - OneDrive token: {ONEDRIVE_TOKEN_PATH}")

    # --- Check if instance is already running ---
    already_running, existing_hwnd = is_already_running()
    if already_running:
        print("WinOTP is already running. Activating existing window...")
        if existing_hwnd:
            activate_existing_window(existing_hwnd)
        else:
            print("Could not find existing window to activate.")
        return  # Exit this instance

    # --- Ensure Application Data Directory Exists (for production mode) ---
    try:
        os.makedirs(winotp_data_dir, exist_ok=True)
        print(f"Production data directory: {winotp_data_dir}")
        
        # --- Cloud backup logic ---
        from datetime import datetime
        settings = load_settings()
        today_str = datetime.now().date().isoformat()
        
        # --- Google Drive backup logic ---
        if settings.get("backup_to_google_drive", False):
            from utils.drive_backup import upload_tokens_json_to_drive, check_backup_exists
            # Check if we need to perform a backup (either no backup today or backup file doesn't exist)
            backup_exists = False
            if settings.get("last_backup_date_google_drive", "") == today_str:
                # If we've backed up today, verify the file actually exists on Google Drive
                try:
                    backup_exists = check_backup_exists()
                    if not backup_exists:
                        print("Today's backup file not found on Google Drive. Will create a new backup.")
                except Exception as e:
                    print(f"Error checking if backup exists: {e}")
                    # If we can't check, assume it doesn't exist to be safe
                    backup_exists = False
            
            # Perform backup if needed
            if not backup_exists:
                try:
                    # Use the global tokens_path variable directly
                    upload_tokens_json_to_drive(local_file_path=tokens_path)
                    settings["last_backup_date_google_drive"] = today_str
                    save_settings(settings)
                    print("Google Drive backup completed and date updated.")
                except Exception as e:
                    print(f"Google Drive backup failed: {e}")
        
        # --- OneDrive backup logic ---
        if settings.get("backup_to_onedrive", False):
            from utils.onedrive_backup import upload_tokens_json_to_onedrive, check_backup_exists as check_onedrive_backup_exists
            # Check if we need to perform a backup (either no backup today or backup file doesn't exist)
            backup_exists = False
            if settings.get("last_backup_date_onedrive", "") == today_str:
                # If we've backed up today, verify the file actually exists on OneDrive
                try:
                    backup_exists = check_onedrive_backup_exists()
                    if not backup_exists:
                        print("Today's backup file not found on OneDrive. Will create a new backup.")
                except Exception as e:
                    print(f"Error checking if OneDrive backup exists: {e}")
                    # If we can't check, assume it doesn't exist to be safe
                    backup_exists = False
            
            # Perform backup if needed
            if not backup_exists:
                try:
                    # Use the global tokens_path variable directly
                    upload_tokens_json_to_onedrive(local_file_path=tokens_path)
                    settings["last_backup_date_onedrive"] = today_str
                    save_settings(settings)
                    print("OneDrive backup completed and date updated.")
                except Exception as e:
                    print(f"OneDrive backup failed: {e}")
    
        # Check if we need to migrate data from old location
        migrate_data_from_old_location()
    except OSError as e:
        print(f"Error creating data directory {winotp_data_dir}: {e}")
        # Potentially critical error if not in debug mode
        pass # Or sys.exit(1)

    # Already set the file paths at the beginning of the function
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
        else:
            # If we're not minimizing to tray, ensure the application exits
            # We need to delay the exit to allow the window to close properly
            threading.Timer(0.5, lambda: os._exit(0)).start()
        return True  # Allow window to close
    
    window.events.closing += on_closing
    
    # Start webview
    webview.start(debug=debug_mode)
    
    # Start background thread for startup setting sync
    sync_thread = threading.Thread(target=start_sync_startup_setting, args=(api,), daemon=True)
    sync_thread.start()

if __name__ == "__main__":
    main()

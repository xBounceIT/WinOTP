import os
import json
import hashlib
from .file_io import read_json, write_json
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

# Path to the auth configuration file - This will be set by main.py
# AUTH_CONFIG_PATH = "auth_config.json" # REMOVED
_current_auth_path = None
_password_hasher = PasswordHasher()

def set_auth_path(path):
    """Sets the path for the authentication configuration file.
    This should be called by the main application entry point.
    """
    global _current_auth_path
    _current_auth_path = path
    print(f"Auth module path set to: {_current_auth_path}") # Debug print

def _get_auth_path():
    """Helper to get the auth path, ensuring it's set."""
    if _current_auth_path is None:
        print("Error: Authentication configuration path has not been set.")
        raise RuntimeError("Authentication configuration path has not been set.")
    print(f"Getting auth path: {_current_auth_path}")
    print(f"Absolute path: {os.path.abspath(_current_auth_path)}")
    print(f"Path exists: {os.path.exists(_current_auth_path)}")
    return _current_auth_path

def hash_password(password):
    """
    Hash a password using Argon2.
    
    Args:
        password (str): The password to hash
        
    Returns:
        str: The Argon2 hash string
    """
    return _password_hasher.hash(password)

def verify_password_hash(password_hash, password):
    """
    Verify a password against an Argon2 hash.
    
    Args:
        password_hash (str): The stored Argon2 hash
        password (str): The password to verify
        
    Returns:
        bool: True if the password matches the hash, False otherwise.
    """
    try:
        _password_hasher.verify(password_hash, password)
        return True
    except VerifyMismatchError:
        return False
    except Exception as e:
        print(f"Error during password verification: {e}")
        return False

def set_pin(pin):
    """
    Set a PIN for app protection
    
    Args:
        pin (str): The PIN to set
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        auth_path = _get_auth_path()
        # Hash the PIN
        hashed_pin = hash_password(pin)
        
        # Read existing config or create new one
        config = read_json(auth_path) or {}
        
        # Update the config
        config["pin_hash"] = hashed_pin
        config["auth_type"] = "pin"
        
        # Write the config
        write_json(auth_path, config)
        return True
    except Exception as e:
        print(f"Error setting PIN: {e}")
        return False

def set_password(password):
    """
    Set a password for app protection
    
    Args:
        password (str): The password to set
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        auth_path = _get_auth_path()
        # Hash the password
        hashed_password = hash_password(password)
        
        # Read existing config or create new one
        config = read_json(auth_path) or {}
        
        # Update the config
        config["password_hash"] = hashed_password
        config["auth_type"] = "password"
        
        # Write the config
        write_json(auth_path, config)
        return True
    except Exception as e:
        print(f"Error setting password: {e}")
        return False

def clear_auth():
    """
    Clear authentication settings
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        auth_path = _get_auth_path()
        # Read existing config
        config = read_json(auth_path) or {}
        
        # Remove auth settings
        if "pin_hash" in config:
            del config["pin_hash"]
        if "password_hash" in config:
            del config["password_hash"]
        if "auth_type" in config:
            del config["auth_type"]
        
        # Write the config
        write_json(auth_path, config)
        return True
    except Exception as e:
        print(f"Error clearing authentication: {e}")
        return False

def verify_pin(pin):
    """
    Verify a PIN against the stored hash
    
    Args:
        pin (str): The PIN to verify
        
    Returns:
        bool: True if PIN is correct, False otherwise
    """
    try:
        auth_path = _get_auth_path()
        # Read config
        config = read_json(auth_path) or {}
        
        # Check if PIN is set
        if "pin_hash" not in config or config.get("auth_type") != "pin":
            return True  # No PIN set, so verification passes
        
        # Verify against stored hash
        stored_hash = config.get("pin_hash")
        if not stored_hash:
            print("Error: PIN hash not found in config during verification.")
            return False # Should not happen if auth_type is pin, but good practice
        
        return verify_password_hash(stored_hash, pin)
    except Exception as e:
        print(f"Error verifying PIN: {e}")
        return False

def verify_password(password):
    """
    Verify a password against the stored hash
    
    Args:
        password (str): The password to verify
        
    Returns:
        bool: True if password is correct, False otherwise
    """
    try:
        auth_path = _get_auth_path()
        # Read config
        config = read_json(auth_path) or {}
        
        # Check if password is set
        if "password_hash" not in config or config.get("auth_type") != "password":
            return True  # No password set, so verification passes
        
        # Verify against stored hash
        stored_hash = config.get("password_hash")
        if not stored_hash:
            print("Error: Password hash not found in config during verification.")
            return False # Should not happen if auth_type is password
        
        return verify_password_hash(stored_hash, password)
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False

def is_auth_enabled():
    """
    Check if authentication is enabled
    
    Returns:
        bool: True if authentication is enabled, False otherwise
    """
    try:
        auth_path = _get_auth_path()
        # Read config
        config = read_json(auth_path) or {}
        
        # Check if auth is enabled
        has_auth = "auth_type" in config and (
            ("pin_hash" in config and config["auth_type"] == "pin") or
            ("password_hash" in config and config["auth_type"] == "password")
        )
        
        print(f"Auth enabled check (using {_current_auth_path}): {has_auth}, config: {config}") # Updated log
        return has_auth
    except Exception as e:
        print(f"Error checking auth status: {e}")
        return False

def get_auth_type():
    """
    Get the current authentication type
    
    Returns:
        str: "pin", "password", or None if not set
    """
    try:
        auth_path = _get_auth_path()
        # Read config
        config = read_json(auth_path) or {}
        
        # Return auth type
        return config.get("auth_type")
    except Exception as e:
        print(f"Error getting auth type: {e}")
        return None

def set_timeout(timeout_minutes):
    """
    Set the authentication timeout duration
    
    Args:
        timeout_minutes (int): Number of minutes until re-authentication is required, 0 for never
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print(f"------- BEGIN SET TIMEOUT -------")
        print(f"Setting timeout to {timeout_minutes} minutes")
        
        # Get and validate the auth path
        auth_path = _get_auth_path()
        print(f"Using auth path: {auth_path}")
        print(f"Absolute path: {os.path.abspath(auth_path)}")
        print(f"Path exists: {os.path.exists(auth_path)}")
        
        # Create directory if it doesn't exist
        directory = os.path.dirname(auth_path)
        if directory and not os.path.exists(directory):
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"Created directory: {directory}")
            except Exception as e:
                print(f"Error creating directory {directory}: {e}")
        
        # Read existing config
        config = read_json(auth_path) or {}
        print(f"Current config before update: {config}")
        
        # Create an empty file if it doesn't exist
        if not os.path.exists(auth_path):
            try:
                with open(auth_path, 'w') as f:
                    json.dump({"timeout_minutes": timeout_minutes}, f, indent=4)
                print(f"Created new auth config file with timeout {timeout_minutes}")
                
                # Clear the file cache to ensure fresh reads
                from .file_io import clear_cache
                clear_cache()
                
                return True
            except Exception as e:
                print(f"Error creating auth config file: {e}")
                return False
        
        # Update the config
        old_timeout = config.get("timeout_minutes", 0)
        config["timeout_minutes"] = timeout_minutes
        print(f"Updated config: {config}")
        print(f"Changed timeout from {old_timeout} to {timeout_minutes}")
        
        # Try regular file writing first
        success = False
        try:
            # Write the config using write_json
            print("Attempting to write config using write_json...")
            success = write_json(auth_path, config)
            if success:
                print("Successfully wrote config using write_json")
            else:
                print("Failed to write config file using write_json")
        except Exception as e:
            print(f"Error during write_json: {e}")
            success = False
        
        # If regular file writing failed, try specialized auth file operations
        if not success:
            try:
                print("Trying specialized auth file operations...")
                from .auth_file_ops import write_auth_config
                success = write_auth_config(auth_path, config)
                if success:
                    print("Successfully wrote config using specialized auth file ops")
                else:
                    print("Failed to write config using specialized auth file ops")
            except ImportError:
                print("Specialized auth file operations module not available")
            except Exception as e:
                print(f"Error during specialized auth file ops: {e}")
                success = False
        
        # If both methods failed, try direct file writing
        if not success:
            try:
                # Try direct file writing
                print("Attempting direct file writing as last resort...")
                with open(auth_path, 'w') as f:
                    json.dump(config, f, indent=4)
                    f.flush()
                    os.fsync(f.fileno())
                print("Direct file writing completed")
                success = True
            except Exception as e:
                print(f"Error during direct file writing: {e}")
                return False
        
        # Clear the file cache to ensure fresh reads
        from .file_io import clear_cache
        clear_cache()
        print("File cache cleared")
        
        # Verify the write by reading it back
        try:
            new_config = read_json(auth_path)
            print(f"Config after write: {new_config}")
            
            new_timeout = new_config.get("timeout_minutes")
            if new_timeout != timeout_minutes:
                print(f"Verification failed: timeout value mismatch. Got {new_timeout}, expected {timeout_minutes}")
                return False
        except Exception as e:
            print(f"Error during verification: {e}")
            return False
            
        print(f"Timeout successfully updated to {timeout_minutes}")
        print(f"------- END SET TIMEOUT -------")
        return True
    except Exception as e:
        print(f"Error setting timeout: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_timeout():
    """
    Get the current authentication timeout duration
    
    Returns:
        int: Number of minutes until re-authentication is required, 0 for never
    """
    try:
        auth_path = _get_auth_path()
        # Read config
        config = read_json(auth_path) or {}
        
        # Return timeout setting
        return config.get("timeout_minutes", 0)
    except Exception as e:
        print(f"Error getting timeout: {e}")
        return 0

def check_timeout(last_auth_time):
    """
    Check if the authentication has timed out
    
    Args:
        last_auth_time (float): Timestamp of the last successful authentication
        
    Returns:
        bool: True if authentication has timed out, False otherwise
    """
    try:
        # If protection is disabled, never timeout
        if not is_auth_enabled():
            return False
            
        timeout_minutes = get_timeout()
        
        # If timeout is 0, authentication never expires
        if timeout_minutes == 0:
            return False
            
        # Check if enough time has passed
        import time
        elapsed_minutes = (time.time() - last_auth_time) / 60
        return elapsed_minutes >= timeout_minutes
    except Exception as e:
        print(f"Error checking timeout: {e}")
        return True  # Default to requiring re-authentication on error 
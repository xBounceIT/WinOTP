import os
import json
import hashlib
from .file_io import read_json, write_json

# Path to the auth configuration file
AUTH_CONFIG_PATH = "auth_config.json"

def hash_password(password):
    """
    Hash a password using SHA-256
    
    Args:
        password (str): The password to hash
        
    Returns:
        str: The hashed password
    """
    return hashlib.sha256(password.encode()).hexdigest()

def set_pin(pin):
    """
    Set a PIN for app protection
    
    Args:
        pin (str): The PIN to set
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Hash the PIN
        hashed_pin = hash_password(pin)
        
        # Read existing config or create new one
        config = read_json(AUTH_CONFIG_PATH) or {}
        
        # Update the config
        config["pin_hash"] = hashed_pin
        config["auth_type"] = "pin"
        
        # Write the config
        write_json(AUTH_CONFIG_PATH, config)
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
        # Hash the password
        hashed_password = hash_password(password)
        
        # Read existing config or create new one
        config = read_json(AUTH_CONFIG_PATH) or {}
        
        # Update the config
        config["password_hash"] = hashed_password
        config["auth_type"] = "password"
        
        # Write the config
        write_json(AUTH_CONFIG_PATH, config)
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
        # Read existing config
        config = read_json(AUTH_CONFIG_PATH) or {}
        
        # Remove auth settings
        if "pin_hash" in config:
            del config["pin_hash"]
        if "password_hash" in config:
            del config["password_hash"]
        if "auth_type" in config:
            del config["auth_type"]
        
        # Write the config
        write_json(AUTH_CONFIG_PATH, config)
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
        # Read config
        config = read_json(AUTH_CONFIG_PATH) or {}
        
        # Check if PIN is set
        if "pin_hash" not in config or config.get("auth_type") != "pin":
            return True  # No PIN set, so verification passes
        
        # Hash the provided PIN
        hashed_pin = hash_password(pin)
        
        # Compare with stored hash
        return hashed_pin == config["pin_hash"]
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
        # Read config
        config = read_json(AUTH_CONFIG_PATH) or {}
        
        # Check if password is set
        if "password_hash" not in config or config.get("auth_type") != "password":
            return True  # No password set, so verification passes
        
        # Hash the provided password
        hashed_password = hash_password(password)
        
        # Compare with stored hash
        return hashed_password == config["password_hash"]
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
        # Read config
        config = read_json(AUTH_CONFIG_PATH) or {}
        
        # Check if auth is enabled
        has_auth = "auth_type" in config and (
            ("pin_hash" in config and config["auth_type"] == "pin") or
            ("password_hash" in config and config["auth_type"] == "password")
        )
        
        print(f"Auth enabled check: {has_auth}, config: {config}")
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
        # Read config
        config = read_json(AUTH_CONFIG_PATH) or {}
        
        # Return auth type
        return config.get("auth_type")
    except Exception as e:
        print(f"Error getting auth type: {e}")
        return None 
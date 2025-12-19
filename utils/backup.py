import os
import json
import shutil
import logging
from datetime import datetime
from pathlib import Path

# Import file I/O utilities
from .file_io import read_json, write_json

def create_backup(tokens_path, backup_folder=None, settings_path=None, tokens_data=None):
    """
    Create a backup of the tokens file
    
    Args:
        tokens_path (str): Path to the tokens.json file
        backup_folder (str, optional): Custom backup folder path
        settings_path (str, optional): Path to app_settings.json for reading/writing backup info
        tokens_data (dict, optional): Pre-loaded tokens data (decrypted). If None, will load from tokens_path.
        
    Returns:
        dict: Status and message
    """
    try:
        # Get backup folder from settings if available
        if settings_path and os.path.exists(settings_path):
            settings = read_json(settings_path) or {}
            settings_backup_folder = settings.get("backup_folder")
            if settings_backup_folder:
                backup_folder = settings_backup_folder
        
        # Get default backup folder if none provided
        if not backup_folder:
            # Use AppData directory for backups
            appdata_dir = os.path.expandvars('%APPDATA%')
            backup_folder = os.path.join(appdata_dir, 'WinOTP', 'backups')
        
        # Ensure backup folder exists
        os.makedirs(backup_folder, exist_ok=True)
        
        # Generate timestamped filename
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        backup_filename = f'winotp_backup_{timestamp}.json'
        backup_path = os.path.join(backup_folder, backup_filename)
        
        # Check if tokens file exists
        if not os.path.exists(tokens_path):
            return {
                "status": "error",
                "message": f"Tokens file not found: {tokens_path}"
            }
        
        # If tokens_data is provided, use it directly (already decrypted)
        # Otherwise, load from file and handle encryption
        if tokens_data is None:
            # Read tokens data from file
            raw_data = read_json(tokens_path)
            
            # Check if the file is encrypted
            if isinstance(raw_data, dict) and raw_data.get("encrypted", False):
                # File is encrypted, need to decrypt it
                # Import auth utilities to get credentials
                from utils.auth import get_auth_type, is_auth_enabled
                from utils.crypto import decrypt_tokens_file
                
                auth_type = get_auth_type()
                if auth_type == "pin":
                    # Get PIN hash from auth config
                    from utils.file_io import read_json as read_json_file
                    auth_config_path = os.path.join(os.path.dirname(tokens_path), 'auth_config.json')
                    if os.path.exists(auth_config_path):
                        config = read_json_file(auth_config_path) or {}
                        tokens_data = decrypt_tokens_file(tokens_path, config.get("pin_hash", ""))
                    else:
                        return {
                            "status": "error",
                            "message": "Cannot backup encrypted tokens without authentication config"
                        }
                elif auth_type == "password":
                    # Get password hash from auth config
                    from utils.file_io import read_json as read_json_file
                    auth_config_path = os.path.join(os.path.dirname(tokens_path), 'auth_config.json')
                    if os.path.exists(auth_config_path):
                        config = read_json_file(auth_config_path) or {}
                        tokens_data = decrypt_tokens_file(tokens_path, config.get("password_hash", ""))
                    else:
                        return {
                            "status": "error",
                            "message": "Cannot backup encrypted tokens without authentication config"
                        }
                else:
                    return {
                        "status": "error",
                        "message": "Encrypted tokens found but no authentication method configured"
                    }
                
                if tokens_data is None:
                    return {
                        "status": "error",
                        "message": "Failed to decrypt tokens for backup"
                    }
            else:
                # File is not encrypted, use directly
                tokens_data = raw_data
        
        # Use the same format as export functionality (pretty-printed JSON)
        # This ensures backup and export produce identical file formats
        tokens_json = json.dumps(tokens_data, indent=4, ensure_ascii=False)
        
        # Write backup file using the same format as export
        # This creates a clean JSON file that matches export functionality
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(tokens_json)
        
        # Update last backup date in settings if provided
        if settings_path:
            try:
                settings = read_json(settings_path) or {}
                settings["last_backup_date"] = datetime.now().strftime('%Y-%m-%d')
                write_json(settings_path, settings)
            except Exception as e:
                logging.warning(f"Failed to update last backup date in settings: {e}")
        
        logging.info(f"Backup created successfully: {backup_path}")
        return {
            "status": "success",
            "message": f"Backup created successfully: {backup_path}",
            "backup_path": backup_path
        }
        
    except PermissionError as e:
        logging.error(f"Permission error during backup: {e}")
        return {
            "status": "error",
            "message": f"Permission denied. Cannot create backup in {backup_folder}"
        }
    except Exception as e:
        logging.error(f"Error creating backup: {e}")
        return {
            "status": "error",
            "message": f"Failed to create backup: {str(e)}"
        }

def should_create_backup(settings_path, backup_folder=None):
    """
    Check if a backup should be created based on the last backup date
    and whether a backup file actually exists
    
    Args:
        settings_path (str): Path to app_settings.json
        backup_folder (str, optional): Custom backup folder path
        
    Returns:
        bool: True if backup should be created, False otherwise
    """
    try:
        # Get default backup folder if none provided
        if not backup_folder:
            appdata_dir = os.path.expandvars('%APPDATA%')
            backup_folder = os.path.join(appdata_dir, 'WinOTP', 'backups')
        
        # Check if backup is enabled
        settings = read_json(settings_path) or {}
        if not settings.get("backup_enabled", False):
            return False
        
        # Get last backup date
        last_backup_date = settings.get("last_backup_date")
        current_date = datetime.now().strftime('%Y-%m-%d')
        
        # Check if backup file exists for today
        backup_pattern = f"winotp_backup_{current_date}_*.json"
        backup_files = []
        
        try:
            if os.path.exists(backup_folder):
                backup_files = [f for f in os.listdir(backup_folder) 
                               if f.startswith(f"winotp_backup_{current_date}_") and f.endswith('.json')]
        except Exception as e:
            logging.warning(f"Could not check backup folder: {e}")
            # If we can't access the folder, assume we need to create a backup
            return True
        
        # If no previous backup date, create backup
        if not last_backup_date:
            return True
        
        # If date has changed, create backup
        if last_backup_date != current_date:
            return True
        
        # If date is current but no backup file exists, create backup
        if last_backup_date == current_date and len(backup_files) == 0:
            logging.warning(f"Backup date is {last_backup_date} but no backup file found. Creating new backup.")
            return True
        
        # If we have a backup file for today, don't create another
        return False
        
    except Exception as e:
        logging.error(f"Error checking backup schedule: {e}")
        return False

def get_backup_status(settings_path):
    """
    Get current backup configuration status
    
    Args:
        settings_path (str): Path to app_settings.json
        
    Returns:
        dict: Backup status information
    """
    try:
        settings = read_json(settings_path) or {}
        
        return {
            "enabled": settings.get("backup_enabled", False),
            "backup_folder": settings.get("backup_folder", ""),
            "last_backup_date": settings.get("last_backup_date", ""),
            "default_folder": os.path.join(os.path.expandvars('%APPDATA%'), 'WinOTP', 'backups')
        }
    except Exception as e:
        logging.error(f"Error getting backup status: {e}")
        return {
            "enabled": False,
            "backup_folder": "",
            "last_backup_date": "",
            "default_folder": os.path.join(os.path.expandvars('%APPDATA%'), 'WinOTP', 'backups')
        }

def enable_backup(settings_path, enabled=True, backup_folder=None):
    """
    Enable or disable backup functionality
    
    Args:
        settings_path (str): Path to app_settings.json
        enabled (bool): Whether to enable backup
        backup_folder (str, optional): Custom backup folder path
        
    Returns:
        dict: Status and message
    """
    try:
        settings = read_json(settings_path) or {}
        
        # Set backup enabled status
        settings["backup_enabled"] = enabled
        
        # Set backup folder if provided
        if backup_folder:
            settings["backup_folder"] = backup_folder
        elif not settings.get("backup_folder"):
            # Use default folder if none set
            settings["backup_folder"] = os.path.join(os.path.expandvars('%APPDATA%'), 'WinOTP', 'backups')
        
        # Save settings
        write_json(settings_path, settings)
        
        return {
            "status": "success",
            "message": f"Backup {'enabled' if enabled else 'disabled'} successfully"
        }
        
    except Exception as e:
        logging.error(f"Error updating backup settings: {e}")
        return {
            "status": "error",
            "message": f"Failed to update backup settings: {str(e)}"
        }

def set_backup_folder(settings_path, backup_folder):
    """
    Set custom backup folder
    
    Args:
        settings_path (str): Path to app_settings.json
        backup_folder (str): Custom backup folder path
        
    Returns:
        dict: Status and message
    """
    try:
        settings = read_json(settings_path) or {}
        
        # Validate backup folder path
        if not backup_folder or not isinstance(backup_folder, str):
            return {
                "status": "error",
                "message": "Invalid backup folder path"
            }
        
        # Ensure backup folder exists
        try:
            os.makedirs(backup_folder, exist_ok=True)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Cannot create backup folder: {str(e)}"
            }
        
        # Update settings
        settings["backup_folder"] = backup_folder
        write_json(settings_path, settings)
        
        return {
            "status": "success",
            "message": f"Backup folder set to: {backup_folder}"
        }
        
    except Exception as e:
        logging.error(f"Error setting backup folder: {e}")
        return {
            "status": "error",
            "message": f"Failed to set backup folder: {str(e)}"
        }

def list_backups(backup_folder=None):
    """
    List all backup files in the backup folder
    
    Args:
        backup_folder (str, optional): Custom backup folder path
        
    Returns:
        list: List of backup file information
    """
    try:
        # Get default backup folder if none provided
        if not backup_folder:
            appdata_dir = os.path.expandvars('%APPDATA%')
            backup_folder = os.path.join(appdata_dir, 'WinOTP', 'backups')
        
        # Check if backup folder exists
        if not os.path.exists(backup_folder):
            return []
        
        backups = []
        for filename in os.listdir(backup_folder):
            if filename.startswith('winotp_backup_') and filename.endswith('.json'):
                filepath = os.path.join(backup_folder, filename)
                try:
                    # Get file creation time
                    creation_time = datetime.fromtimestamp(os.path.getctime(filepath))
                    
                    # Try to read backup metadata
                    backup_data = read_json(filepath)
                    # Check if it's the new export format or old backup format
                    if "backup_info" in backup_data:
                        backup_type = backup_data.get("backup_info", {}).get("backup_type", "unknown")
                    else:
                        backup_type = "export_format"
                    
                    backups.append({
                        "filename": filename,
                        "filepath": filepath,
                        "created_at": creation_time.strftime('%Y-%m-%d %H:%M:%S'),
                        "backup_type": backup_type
                    })
                except Exception:
                    # If we can't read the file, just include basic info
                    creation_time = datetime.fromtimestamp(os.path.getctime(filepath))
                    backups.append({
                        "filename": filename,
                        "filepath": filepath,
                        "created_at": creation_time.strftime('%Y-%m-%d %H:%M:%S'),
                        "backup_type": "unknown"
                    })
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x["created_at"], reverse=True)
        return backups
        
    except Exception as e:
        logging.error(f"Error listing backups: {e}")
        return []

def restore_from_backup(backup_path, tokens_path):
    """
    Restore tokens from a backup file
    
    Args:
        backup_path (str): Path to the backup file
        tokens_path (str): Path to the tokens.json file
        
    Returns:
        dict: Status and message
    """
    try:
        # Check if backup file exists
        if not os.path.exists(backup_path):
            return {
                "status": "error",
                "message": f"Backup file not found: {backup_path}"
            }
        
        # Read backup data
        backup_data = read_json(backup_path)
        
        # Handle both old backup format and new export format
        if "tokens" in backup_data:
            # Old backup format with metadata
            tokens_data = backup_data["tokens"]
        elif "backup_info" in backup_data:
            # Should have tokens, but check anyway
            tokens_data = backup_data.get("tokens", {})
        else:
            # New export format - just the tokens directly
            tokens_data = backup_data
        
        # Write to tokens file
        write_json(tokens_path, tokens_data)
        
        return {
            "status": "success",
            "message": f"Tokens restored from backup: {backup_path}"
        }
        
    except Exception as e:
        logging.error(f"Error restoring from backup: {e}")
        return {
            "status": "error",
            "message": f"Failed to restore from backup: {str(e)}"
        }

import winreg
import sys
import os
import logging

# Use a consistent name for the registry entry
APP_NAME = "WinOTP"
# Construct the path to the executable
APP_PATH = os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else sys.argv[0])

# Ensure the path points to the .exe in a frozen app (PyInstaller)
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    # When frozen, sys.executable points to the bootloader.
    # Assume the .exe has the same name as APP_NAME and is nearby.
    # This path logic might need adjustment based on the PyInstaller setup (one-file vs one-dir)
    potential_exe_path = os.path.join(os.path.dirname(sys.executable), f"{APP_NAME}.exe")
    if os.path.exists(potential_exe_path):
        APP_PATH = potential_exe_path
    else:
        # If bundled as one-file, sys.executable *is* the exe path usually
        if os.path.basename(sys.executable).lower() == f"{APP_NAME}.exe".lower():
             APP_PATH = sys.executable # Already correct
        else:
            # Fallback if structure is unexpected
            logging.warning(f"Could not reliably determine packaged .exe path. Using sys.executable: {sys.executable}")
            APP_PATH = sys.executable # Use bootloader path as fallback
elif not getattr(sys, 'frozen', False):
    # In development (not frozen), sys.executable is often python.exe.
    # sys.argv[0] usually points to the script (e.g., main.py)
    script_path = os.path.abspath(sys.argv[0])
    # Best guess for dev is that the script itself should be run via python
    # Or maybe a built exe exists for testing? Let's default to running the script via python.
    # However, for the startup entry, we *need* the final .exe path.
    # This implies startup functionality might only work correctly when run from the built .exe
    # Let's try finding a built exe relative to the script
    script_dir = os.path.dirname(script_path)
    dist_exe_path = os.path.join(script_dir, 'dist', APP_NAME, f"{APP_NAME}.exe") # Common PyInstaller dist path

    if os.path.exists(dist_exe_path):
        APP_PATH = dist_exe_path
        logging.info(f"Found potential built exe for dev startup: {APP_PATH}")
    else:
        # If no built exe found, we cannot reliably add to startup in dev mode
        # We'll use the python executable and the script path, but log a clear warning.
        python_exe = sys.executable
        APP_PATH = f'"{python_exe}" "{script_path}"' # Run script with python
        logging.warning(f"Running in dev mode. Adding startup entry to run script via Python: {APP_PATH}. "
                        f"This might differ from the final packaged app.")


logging.info(f"Using application path for startup registry: {APP_PATH}")

REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

def add_to_startup():
    """Adds the application to the Windows startup registry."""
    # Ensure path is quoted if it contains spaces and isn't already quoted
    path_to_register = APP_PATH
    if ' ' in path_to_register and not (path_to_register.startswith('"') and path_to_register.endswith('"')):
         # Check if it looks like we already added quotes for python + script
         if not (path_to_register.startswith('"') and path_to_register.count('"') >= 2):
              path_to_register = f'"{path_to_register}"'


    try:
        logging.info(f"Attempting to add to startup: {APP_NAME} with path {path_to_register}")
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, path_to_register)
        winreg.CloseKey(key)
        logging.info(f"Successfully added {APP_NAME} to startup.")
        return True
    except FileNotFoundError:
        logging.error(f"Startup registry path not found: {REG_PATH}. Cannot add to startup.")
        return False
    except PermissionError:
        logging.error(f"Permission denied when trying to write to registry path: {REG_PATH}")
        return False
    except OSError as e:
        logging.error(f"OS error adding to startup: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error adding {APP_NAME} to startup: {e}")
        return False

def remove_from_startup():
    """Removes the application from the Windows startup registry."""
    try:
        logging.info(f"Attempting to remove '{APP_NAME}' from startup.")
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE)
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        logging.info(f"Successfully removed '{APP_NAME}' from startup.")
        return True
    except FileNotFoundError:
        # If the key or value doesn't exist, it's already removed (or wasn't added)
        logging.info(f"App '{APP_NAME}' not found in startup registry for removal. Considered successful.")
        return True # Goal is removal, so this is success
    except PermissionError:
        logging.error(f"Permission denied when trying to delete '{APP_NAME}' from registry path: {REG_PATH}")
        return False
    except OSError as e:
        logging.error(f"OS error removing '{APP_NAME}' from startup: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error removing '{APP_NAME}' from startup: {e}")
        return False

def is_in_startup():
    """Checks if the application is currently in the Windows startup registry."""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        registered_path, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)

        # Normalize paths for comparison (lower case, strip quotes)
        # Normalize expected path (APP_PATH might be quoted python + script path)
        expected_path_norm = APP_PATH.lower().strip('"')
        if APP_PATH.startswith('"') and APP_PATH.count('"') >= 2: # Handle quoted python + script case
             parts = APP_PATH.strip('"').split('" "', 1)
             expected_path_norm = f'"{parts[0].lower()}" "{parts[1].lower()}"' if len(parts) == 2 else APP_PATH.lower().strip('"')


        registered_path_norm = registered_path.lower().strip('"')
        # Also handle if registered path has quotes around python + script
        if registered_path.startswith('"') and registered_path.count('"') >= 2:
             parts = registered_path.strip('"').split('" "', 1)
             registered_path_norm = f'"{parts[0].lower()}" "{parts[1].lower()}"' if len(parts) == 2 else registered_path.lower().strip('"')


        # Direct comparison might be sufficient if SetValueEx handles quoting consistently
        is_set = registered_path_norm == expected_path_norm

        logging.debug(f"Checking startup status: Name='{APP_NAME}', Expected='{expected_path_norm}', Found='{registered_path_norm}', Match={is_set}")
        return is_set
    except FileNotFoundError:
        logging.debug(f"App '{APP_NAME}' not found in startup registry.")
        return False # Key or value doesn't exist
    except Exception as e:
        logging.error(f"Failed to check startup status for '{APP_NAME}': {e}")
        return False # Return False on error to be safe 
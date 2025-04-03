import sys
import os
import logging
import winshell  # Requires pywin32
from win32com.client import Dispatch # Requires pywin32
import pythoncom # Requires pywin32

# Use a consistent name for the app and shortcut
APP_NAME = "WinOTP"
SHORTCUT_NAME = f"{APP_NAME}.lnk"

# --- Determine Application Path ---
# Initialize APP_PATH and a flag indicating if it's a runnable executable
APP_PATH = None
IS_EXECUTABLE_PATH = False

if getattr(sys, 'frozen', False):
    # --- Packaged App (PyInstaller) ---
    # sys.executable is the path to the bundled .exe
    APP_PATH = sys.executable
    IS_EXECUTABLE_PATH = True
    logging.info(f"Running packaged app. Startup target: {APP_PATH}")
else:
    # --- Development Mode ---
    script_path = os.path.abspath(sys.argv[0])
    script_dir = os.path.dirname(script_path)
    
    # Check for a pre-built executable in a common location (e.g., dist/)
    dist_exe_path = os.path.join(script_dir, 'dist', APP_NAME, f"{APP_NAME}.exe") # Common PyInstaller dist path
    
    if os.path.exists(dist_exe_path):
        # Found a potential built .exe, use it for startup shortcut
        APP_PATH = dist_exe_path
        IS_EXECUTABLE_PATH = True
        logging.info(f"Running in dev mode, but found built exe for startup: {APP_PATH}")
    else:
        # No built exe found, cannot reliably create startup item in dev mode
        APP_PATH = script_path # Store script path for logging, but won't use for shortcut
        IS_EXECUTABLE_PATH = False
        logging.warning(f"Running in dev mode (Script: {APP_PATH}). 'Run at Startup' requires a built executable (.exe).")

# --- Determine Startup Folder and Shortcut Path ---
STARTUP_FOLDER = winshell.startup()
if STARTUP_FOLDER is None:
    logging.error("Could not determine user's Startup folder.")
    # Set a dummy path to prevent crashes later, though functions will fail
    SHORTCUT_PATH = "" 
else:
    SHORTCUT_PATH = os.path.join(STARTUP_FOLDER, SHORTCUT_NAME)
    logging.info(f"Using Startup folder: {STARTUP_FOLDER}")
    logging.info(f"Startup shortcut path: {SHORTCUT_PATH}")

# --- Startup Management Functions ---

def add_to_startup():
    """Adds the application shortcut to the Windows Startup folder."""
    logging.info(f"Attempting to add '{SHORTCUT_NAME}' to startup.")
    
    if not IS_EXECUTABLE_PATH:
        logging.error(f"Cannot add to startup: Application path '{APP_PATH}' is not a valid executable.")
        return False
        
    if not STARTUP_FOLDER or not SHORTCUT_PATH:
        logging.error("Cannot add to startup: Startup folder path is not available.")
        return False

    try:
        # Initialize COM library (required for Dispatch in some contexts/threads)
        pythoncom.CoInitialize() 
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(SHORTCUT_PATH)
        shortcut.Targetpath = APP_PATH
        # Set working directory to the executable's directory for relative paths
        shortcut.WorkingDirectory = os.path.dirname(APP_PATH) 
        shortcut.Description = f"Start {APP_NAME}"
        # shortcut.IconLocation = APP_PATH # Optional: Set icon
        shortcut.save()
        
        # Uninitialize COM library
        pythoncom.CoUninitialize()
        
        logging.info(f"Successfully created startup shortcut: {SHORTCUT_PATH}")
        return True
    except pythoncom.com_error as e:
        logging.error(f"COM error creating startup shortcut: {e}")
        pythoncom.CoUninitialize() # Ensure uninitialization on error
        return False
    except Exception as e:
        logging.error(f"Unexpected error creating startup shortcut: {e}")
        # Attempt uninitialization even on unexpected errors
        try:
            pythoncom.CoUninitialize()
        except pythoncom.com_error:
            pass # Ignore if already uninitialized or other COM issue
        return False

def remove_from_startup():
    """Removes the application shortcut from the Windows Startup folder."""
    logging.info(f"Attempting to remove '{SHORTCUT_NAME}' from startup.")
    
    if not STARTUP_FOLDER or not SHORTCUT_PATH:
        logging.error("Cannot remove from startup: Startup folder path is not available.")
        return False

    try:
        if os.path.exists(SHORTCUT_PATH):
            os.remove(SHORTCUT_PATH)
            logging.info(f"Successfully removed startup shortcut: {SHORTCUT_PATH}")
            # Verify removal
            if os.path.exists(SHORTCUT_PATH):
                 logging.warning(f"Shortcut file still exists after attempting removal: {SHORTCUT_PATH}")
                 return False
            return True
        else:
            logging.info(f"Startup shortcut not found (already removed): {SHORTCUT_PATH}")
            return True # Goal is removal, so this is success
    except PermissionError:
        logging.error(f"Permission denied when trying to remove shortcut: {SHORTCUT_PATH}")
        return False
    except OSError as e:
        logging.error(f"OS error removing shortcut: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error removing startup shortcut: {e}")
        return False

def is_in_startup():
    """Checks if the application shortcut exists in the Windows Startup folder."""
    if not STARTUP_FOLDER or not SHORTCUT_PATH:
        logging.warning("Cannot check startup status: Startup folder path is not available.")
        return False
        
    exists = os.path.exists(SHORTCUT_PATH)
    logging.debug(f"Checking startup status: Shortcut '{SHORTCUT_PATH}' exists = {exists}")
    return exists

def check_and_update_startup_shortcut():
    """
    Checks if the current application path matches the shortcut target.
    If the app has been moved, updates the shortcut to point to the new location.
    """
    if not IS_EXECUTABLE_PATH:
        logging.warning("Not running as executable, skipping startup shortcut verification.")
        return False
        
    if not os.path.exists(SHORTCUT_PATH):
        logging.debug("Startup shortcut does not exist, no need to update.")
        return False
        
    try:
        # Initialize COM library
        pythoncom.CoInitialize()
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(SHORTCUT_PATH)
        current_target = shortcut.Targetpath
        
        # Compare current app path with shortcut target
        if current_target != APP_PATH:
            logging.info(f"App location changed. Updating startup shortcut from {current_target} to {APP_PATH}")
            
            # Update shortcut properties
            shortcut.Targetpath = APP_PATH
            shortcut.WorkingDirectory = os.path.dirname(APP_PATH)
            shortcut.save()
            
            # Uninitialize COM library
            pythoncom.CoUninitialize()
            logging.info("Startup shortcut updated successfully.")
            return True
        else:
            logging.debug("Startup shortcut target is already correct.")
            # Uninitialize COM library
            pythoncom.CoUninitialize()
            return True
            
    except pythoncom.com_error as e:
        logging.error(f"COM error updating startup shortcut: {e}")
        try:
            pythoncom.CoUninitialize()
        except:
            pass
        return False
    except Exception as e:
        logging.error(f"Unexpected error updating startup shortcut: {e}")
        try:
            pythoncom.CoUninitialize()
        except:
            pass
        return False 
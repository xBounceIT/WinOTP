import os
import sys
import ctypes
from ctypes import wintypes
import win32api
import win32con
import win32gui
import win32process

# Windows API constants
ERROR_ALREADY_EXISTS = 0xB7
ERROR_ACCESS_DENIED = 0x5

# App identifier - using a unique name
APP_ID = "WinOTP-{67812F19-BF0A-493A-8C21-29DE51A4184B}"

def is_already_running():
    """
    Check if the application is already running.
    
    Returns:
        tuple: (is_running, hwnd) where is_running is a boolean indicating if
               another instance is running, and hwnd is the window handle of 
               the existing instance (or None if not running)
    """
    print(f"Checking if application is already running using mutex '{APP_ID}'...")
    
    # Try to create a mutex with our unique name
    mutex = ctypes.windll.kernel32.CreateMutexW(
        None,  # Default security attributes
        False,  # We don't want to own the mutex initially
        APP_ID  # Our unique application ID
    )
    
    # If the mutex already exists or we can't access it, another instance is running
    last_error = ctypes.windll.kernel32.GetLastError()
    is_running = (last_error == ERROR_ALREADY_EXISTS or 
                  last_error == ERROR_ACCESS_DENIED)
    
    print(f"CreateMutex result: {mutex}, last error: {last_error}")
    print(f"Is another instance running: {is_running}")
    
    # Find the window handle of the existing instance if it's running
    hwnd = None
    if is_running:
        hwnd = find_existing_window()
        print(f"Found existing window handle: {hwnd}")
    
    return is_running, hwnd


def find_existing_window():
    """
    Find the window handle of the existing application instance.
    
    Returns:
        int: Window handle of the existing instance, or None if not found
    """
    result = [None]
    found_windows = []
    
    def enum_windows_callback(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return True  # Skip non-visible windows
            
        window_text = win32gui.GetWindowText(hwnd)
        
        # Store all windows with WinOTP in their title for debugging
        if "WinOTP" in window_text:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            is_top_level = not win32gui.GetParent(hwnd)
            found_windows.append({
                "hwnd": hwnd,
                "title": window_text,
                "pid": pid,
                "is_top_level": is_top_level
            })
            
            # If this is a top-level window, this is our target
            if is_top_level:
                result[0] = hwnd
                return False  # Stop enumerating
        
        return True  # Continue enumerating
    
    win32gui.EnumWindows(enum_windows_callback, None)
    
    # Print found windows for debugging
    if found_windows:
        print(f"Found {len(found_windows)} windows containing 'WinOTP':")
        for i, window in enumerate(found_windows, 1):
            print(f"  Window {i}: hwnd={window['hwnd']}, pid={window['pid']}, "
                  f"title='{window['title']}', top-level={window['is_top_level']}")
    else:
        print("No windows containing 'WinOTP' found.")
        
    return result[0]


def activate_existing_window(hwnd):
    """
    Bring the existing application window to the foreground and restore it if minimized.
    
    Args:
        hwnd (int): Window handle of the existing instance
    
    Returns:
        bool: True if successful, False otherwise
    """
    if not hwnd:
        return False
    
    try:
        # If the window is minimized, restore it
        is_iconic = win32gui.IsIconic(hwnd)
        print(f"Window is minimized: {is_iconic}")
        
        if is_iconic:
            print("Restoring window...")
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        
        # Bring the window to the foreground
        print("Setting window to foreground...")
        result = win32gui.SetForegroundWindow(hwnd)
        print(f"SetForegroundWindow result: {result}")
        
        return True
    except Exception as e:
        print(f"Error activating existing window: {e}")
        return False 
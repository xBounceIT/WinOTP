import time
import threading
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ntp_sync")

# Global variables
_time_offset = 0.0  # Offset is always 0 when using local time
_last_sync = 0  # Last sync timestamp (for compatibility)
_sync_interval = 900  # Sync interval (kept for compatibility, but not used)
_sync_lock = threading.Lock()
_sync_thread = None  # Sync thread reference
_is_running = False  # Sync thread running flag
_sync_initialized = False  # Flag to track if sync has been initialized
_last_request_time = 0  # Last time get_accurate_time was called
_request_count = 0  # Counter for get_accurate_time requests

def get_ntp_time(server=None):
    """
    Get the current time from an NTP server.
    DEPRECATED: Returns local system time for compatibility.
    
    Args:
        server (str, optional): NTP server to use (ignored, kept for compatibility)
    
    Returns:
        float: Local system time timestamp
    """
    logger.warning("get_ntp_time() is deprecated and returns local time")
    return time.time()

def calculate_offset():
    """
    Calculate the offset between system time and NTP time.
    MODIFIED: Now returns 0 since we use local time.
    
    Returns:
        float: Time offset (always 0 for local time)
    """
    global _time_offset, _last_sync
    
    # For local time, offset is always 0
    with _sync_lock:
        _time_offset = 0.0
        _last_sync = time.time()
    
    logger.info("Using local system time (offset = 0)")
    return 0.0

def get_accurate_time():
    """
    Get the current time using host local time.
    MODIFIED: Returns local system time directly.
    
    Returns:
        float: Current local time in seconds since epoch
    """
    global _last_request_time, _request_count, _sync_initialized, _last_sync
    
    # Ensure sync is initialized
    if not _sync_initialized:
        # Initialize on first call
        with _sync_lock:
            _last_sync = time.time()
            _sync_initialized = True
        logger.info("Local time sync initialized")
        
    with _sync_lock:
        current_time = time.time()
        
        # Track request frequency (for compatibility with existing logic)
        if current_time - _last_request_time < 1.0:  # Within 1 second
            _request_count += 1
        else:
            # Reset counter if more than 1 second has passed
            _last_request_time = current_time
            _request_count = 1
        
        # For local time, we don't need periodic syncs, but we update last_sync periodically
        # to maintain compatibility with status reporting
        if current_time - _last_sync > _sync_interval:
            _last_sync = current_time
        
        # Return local time directly (no offset adjustment needed)
        return current_time

def get_accurate_timestamp_30s():
    """
    Get the current 30-second timestamp using local time.
    MODIFIED: Uses local time for TOTP intervals.
    
    Returns:
        int: Current 30-second timestamp
    """
    return int(get_accurate_time() // 30)

def format_time(timestamp=None):
    """
    Format a timestamp as a human-readable string.
    
    Args:
        timestamp (float, optional): Timestamp to format. Defaults to current local time.
    
    Returns:
        str: Formatted time string
    """
    if timestamp is None:
        timestamp = get_accurate_time()
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

def _sync_thread_func():
    """Thread function for periodic sync updates (compatibility only)"""
    global _is_running
    
    # This thread now just updates the last_sync timestamp periodically
    # to maintain compatibility with status reporting
    while _is_running:
        try:
            with _sync_lock:
                _last_sync = time.time()
        except Exception as e:
            logger.error(f"Error in sync thread: {e}")
        
        time.sleep(_sync_interval)

def start_ntp_sync(interval=900):
    """
    Start the sync thread (for compatibility).
    MODIFIED: Uses local time, no NTP servers.
    
    Args:
        interval (int, optional): Update interval in seconds. Defaults to 900 (15 minutes).
    """
    global _sync_thread, _is_running, _sync_interval, _sync_initialized
    
    # Don't start if already running
    if _is_running:
        return
    
    _sync_interval = interval
    _is_running = True
    
    # Start the sync in a background thread to avoid blocking the UI
    def delayed_start():
        global _sync_initialized
        # Wait a short time before first sync to allow app to start up
        time.sleep(1)
        
        # Perform initial sync
        calculate_offset()
        _sync_initialized = True
        
        # Start the periodic sync thread (for compatibility)
        _sync_thread = threading.Thread(target=_sync_thread_func, daemon=True)
        _sync_thread.start()
        logger.info(f"Local time sync started with interval {interval} seconds")
    
    # Start the delayed initialization
    init_thread = threading.Thread(target=delayed_start, daemon=True)
    init_thread.start()

def stop_ntp_sync():
    """
    Stop the sync thread.
    """
    global _is_running
    
    _is_running = False
    logger.info("Local time sync thread stopping")

def get_sync_status():
    """
    Get the current sync status.
    MODIFIED: Reports local time usage.
    
    Returns:
        dict: Status information
    """
    with _sync_lock:
        current_time = time.time()
        time_since_sync = current_time - _last_sync if _last_sync > 0 else float('inf')
        
        # For local time, we're always "synced" if initialized
        synced = _sync_initialized
        syncing = False  # Never syncing with local time
        
        # Offset is always 0 for local time
        offset_ms = 0.0
        
        return {
            "offset": 0.0,
            "offset_ms": offset_ms,
            "last_sync": _last_sync,
            "last_sync_formatted": format_time(_last_sync) if _last_sync > 0 else "Never",
            "sync_interval": _sync_interval,
            "is_running": _is_running and (_sync_thread is not None and _sync_thread.is_alive()),
            "synced": synced,
            "syncing": syncing,
            "mode": "local"  # Add mode indicator
        }

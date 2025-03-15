import ntplib
import time
import threading
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ntp_sync")

# Global variables
_time_offset = 0.0  # Offset between system time and NTP time in seconds
_last_sync = 0  # Last successful sync timestamp
_sync_interval = 300  # Reduced from 3600 to 300 seconds (5 minutes) for more frequent updates
_ntp_servers = [
    "pool.ntp.org",
    "time.google.com",
    "time.windows.com",
    "time.nist.gov"
]
_sync_lock = threading.Lock()
_sync_thread = None
_is_running = False
_last_server_index = 0  # Track which server we last used successfully
_sync_initialized = False  # Flag to track if sync has been initialized

def get_ntp_time(server=None):
    """
    Get the current time from an NTP server.
    
    Args:
        server (str, optional): NTP server to use. Defaults to None, which uses the first server in _ntp_servers.
    
    Returns:
        float: NTP timestamp or None if failed
    """
    global _last_server_index
    
    if server is None:
        # Start with the last successful server
        servers = _ntp_servers[_last_server_index:] + _ntp_servers[:_last_server_index]
    else:
        servers = [server]
    
    client = ntplib.NTPClient()
    
    for idx, srv in enumerate(servers):
        try:
            # Reduced timeout from 2 to 1 second for faster failure detection
            response = client.request(srv, timeout=1)
            if server is None:
                _last_server_index = (_last_server_index + idx) % len(_ntp_servers)
            return response.tx_time
        except (ntplib.NTPException, Exception) as e:
            logger.warning(f"Failed to get time from NTP server {srv}: {e}")
            continue
    
    return None

def calculate_offset():
    """
    Calculate the offset between system time and NTP time.
    
    Returns:
        float: Time offset in seconds or 0 if sync failed
    """
    global _time_offset, _last_sync
    
    # Try each NTP server until one succeeds
    ntp_time = get_ntp_time()
    if ntp_time is not None:
        system_time = time.time()
        offset = ntp_time - system_time
        
        with _sync_lock:
            # Use a weighted average to smooth out changes
            if _last_sync > 0:
                # Weight: 70% new offset, 30% old offset
                _time_offset = 0.7 * offset + 0.3 * _time_offset
            else:
                _time_offset = offset
            _last_sync = system_time
        
        logger.info(f"NTP sync successful. New offset: {_time_offset:.6f} seconds")
        return _time_offset
    
    logger.error("Failed to sync with any NTP server")
    return 0.0

def get_accurate_time():
    """
    Get the current time adjusted by the NTP offset.
    
    Returns:
        float: Adjusted current time in seconds since epoch
    """
    # Ensure NTP sync is initialized
    if not _sync_initialized:
        # Just use system time on first call
        return time.time()
        
    with _sync_lock:
        current_time = time.time()
        # Force a sync if too much time has passed since last sync
        if _last_sync > 0 and current_time - _last_sync > _sync_interval:
            threading.Thread(target=calculate_offset, daemon=True).start()
        
        return current_time + _time_offset

def get_accurate_timestamp_30s():
    """
    Get the current 30-second timestamp adjusted by the NTP offset.
    This is specifically for TOTP which uses 30-second intervals.
    
    Returns:
        int: Current 30-second timestamp
    """
    return int(get_accurate_time() // 30)

def format_time(timestamp=None):
    """
    Format a timestamp as a human-readable string.
    
    Args:
        timestamp (float, optional): Timestamp to format. Defaults to current accurate time.
    
    Returns:
        str: Formatted time string
    """
    if timestamp is None:
        timestamp = get_accurate_time()
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

def _sync_thread_func():
    """Thread function for periodic NTP synchronization"""
    global _is_running
    
    while _is_running:
        try:
            calculate_offset()
        except Exception as e:
            logger.error(f"Error in NTP sync thread: {e}")
        
        # Sleep until next sync interval
        time.sleep(_sync_interval)

def start_ntp_sync(interval=300):  # Default to 5 minutes instead of 1 hour
    """
    Start the NTP synchronization thread.
    
    Args:
        interval (int, optional): Sync interval in seconds. Defaults to 300 (5 minutes).
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
        
        # Start the periodic sync thread
        _sync_thread = threading.Thread(target=_sync_thread_func, daemon=True)
        _sync_thread.start()
        logger.info(f"NTP sync started with interval {interval} seconds")
    
    # Start the delayed initialization
    init_thread = threading.Thread(target=delayed_start, daemon=True)
    init_thread.start()

def stop_ntp_sync():
    """
    Stop the NTP synchronization thread.
    """
    global _is_running
    
    _is_running = False
    logger.info("NTP sync thread stopping")

def get_sync_status():
    """
    Get the current NTP synchronization status.
    
    Returns:
        dict: Status information including offset, last sync time, and sync interval
    """
    with _sync_lock:
        # Calculate time since last sync
        current_time = time.time()
        time_since_sync = current_time - _last_sync if _last_sync > 0 else float('inf')
        
        # Determine if we're synced (had a successful sync in the last sync interval)
        synced = _last_sync > 0 and time_since_sync < _sync_interval
        
        # Determine if we're currently syncing (thread is running but not yet synced)
        syncing = _is_running and (_sync_thread is not None and _sync_thread.is_alive()) and not synced
        
        # Convert offset from seconds to milliseconds for UI display
        offset_ms = _time_offset * 1000
        
        return {
            "offset": _time_offset,
            "offset_ms": offset_ms,  # Add milliseconds version for UI
            "last_sync": _last_sync,
            "last_sync_formatted": format_time(_last_sync) if _last_sync > 0 else "Never",
            "sync_interval": _sync_interval,
            "is_running": _is_running and (_sync_thread is not None and _sync_thread.is_alive()),
            "synced": synced,  # Add synced flag for UI
            "syncing": syncing  # Add syncing flag for UI
        } 
import json
import os
import threading

# Cache for file contents
_file_cache = {}
_cache_lock = threading.Lock()
_cache_enabled = True

def enable_cache(enabled=True):
    """Enable or disable the file cache
    
    Args:
        enabled (bool): Whether to enable the cache
    """
    global _cache_enabled
    _cache_enabled = enabled

def clear_cache():
    """Clear the file cache"""
    global _file_cache
    with _cache_lock:
        _file_cache.clear()

def read_json(file_path):
    """Read and parse a JSON file
    
    Args:
        file_path (str): Path to the JSON file
        
    Returns:
        dict: The parsed JSON data or an empty dict if file not found or invalid
    """
    global _file_cache, _cache_enabled
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}, creating empty token storage")
        return {}
    
    # Check cache first if enabled
    if _cache_enabled:
        with _cache_lock:
            cache_key = f"{file_path}:{os.path.getmtime(file_path)}"
            if cache_key in _file_cache:
                print(f"Using cached data for {file_path}")
                return _file_cache[cache_key]
    
    try:
        with open(file_path, 'r') as file:
            data = json.load(file)
            
            # Cache the result if enabled
            if _cache_enabled:
                with _cache_lock:
                    cache_key = f"{file_path}:{os.path.getmtime(file_path)}"
                    _file_cache[cache_key] = data
            
            print(f"Successfully loaded {len(data)} tokens from {file_path}")
            return data
    except FileNotFoundError:
        print(f"File not found: {file_path}, creating empty token storage")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from {file_path}: {e}")
        return {}

def write_json(file_path, data):
    """Write data to a JSON file
    
    Args:
        file_path (str): Path to the JSON file
        data (dict): Data to write to the file
    """
    # Create directory if it doesn't exist
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)
    
    # Update cache if enabled
    if _cache_enabled:
        with _cache_lock:
            cache_key = f"{file_path}:{os.path.getmtime(file_path)}"
            _file_cache[cache_key] = data 
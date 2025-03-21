import os
import urllib.request
import threading
import time

# Create directories if they don't exist
def ensure_directories():
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    os.makedirs('static/icons', exist_ok=True)

# Files to download
files_to_download = [
    ('https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css', 'static/css/bootstrap.min.css'),
    ('https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js', 'static/js/bootstrap.bundle.min.js'),
    ('https://code.jquery.com/jquery-3.6.0.min.js', 'static/js/jquery-3.6.0.min.js'),
]

# Flag to track if assets have been initialized
_assets_initialized = False

def download_file(url, path):
    """Download a file from URL to path"""
    # Skip if file already exists
    if os.path.exists(path):
        return
    
    try:
        urllib.request.urlretrieve(url, path)
        print(f"Downloaded {path}")
    except Exception as e:
        print(f"Error downloading {url}: {e}")

def download_assets_background():
    """Download all assets in the background"""
    ensure_directories()
    
    # Download files
    for url, path in files_to_download:
        download_file(url, path)
    
    print("Asset download completed")

def initialize_assets():
    """Initialize assets - create essential ones immediately and download others in background"""
    global _assets_initialized
    
    # Only run initialization once
    if _assets_initialized:
        return
    
    ensure_directories()
    
    # Check if all files already exist
    all_files_exist = all(os.path.exists(path) for _, path in files_to_download)
    
    if all_files_exist:
        print("All assets already exist, skipping download")
        _assets_initialized = True
        return
    
    # Start background thread to download remaining assets
    thread = threading.Thread(target=download_assets_background, daemon=True)
    thread.start()
    _assets_initialized = True 
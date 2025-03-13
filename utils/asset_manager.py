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

# Icons to create
icons = [
    'search.png',
    'sort_asc.png',
    'sort_desc.png',
    'settings.png',
    'plus.png',
    'back_arrow.png',
    'copy.png',
    'copy_confirm.png',
    'delete.png',
    'app.png',
    'question.png',
    'warning.png',
    'download.png',
    'upload.png',
    'edit.png',
    'qr-code.png',
]

# Transparent pixel data for placeholder icons
transparent_pixel = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x00\x00\x02\x00\x01\xe5\'\xde\xfc\x00\x00\x00\x00IEND\xaeB`\x82'

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

def create_placeholder_icon(icon_path):
    """Create a placeholder icon if it doesn't exist"""
    # Skip if icon already exists
    if os.path.exists(icon_path):
        return
    
    try:
        with open(icon_path, 'wb') as f:
            f.write(transparent_pixel)
        print(f"Created {icon_path}")
    except Exception as e:
        print(f"Error creating {icon_path}: {e}")

def ensure_essential_assets():
    """Ensure essential assets exist (create placeholders if needed)"""
    ensure_directories()
    
    # Create placeholder icons for essential UI elements
    essential_icons = ['search.png', 'sort_asc.png', 'sort_desc.png', 'plus.png']
    for icon in essential_icons:
        icon_path = os.path.join('static/icons', icon)
        create_placeholder_icon(icon_path)

def download_assets_background():
    """Download all assets in the background"""
    ensure_directories()
    
    # Download files
    for url, path in files_to_download:
        download_file(url, path)
    
    # Create placeholder icons
    for icon in icons:
        icon_path = os.path.join('static/icons', icon)
        create_placeholder_icon(icon_path)
    
    print("Asset download completed")

def initialize_assets():
    """Initialize assets - create essential ones immediately and download others in background"""
    # Ensure essential assets exist immediately
    ensure_essential_assets()
    
    # Start background thread to download remaining assets
    thread = threading.Thread(target=download_assets_background, daemon=True)
    thread.start() 
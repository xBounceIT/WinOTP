from flask import Flask, render_template, request, jsonify, redirect, url_for, session, Response, send_from_directory
import json
import os
import sys
import uuid
import pyotp
from datetime import datetime
import base64
from PIL import Image
import io
import threading
import time
from functools import lru_cache
import gzip

from utils.file_io import read_json, write_json
from utils.qr_scanner import scan_qr_image
from utils.ntp_sync import start_ntp_sync, get_accurate_time, get_accurate_timestamp_30s, get_sync_status, calculate_offset
from utils.asset_manager import initialize_assets
from models.token import Token

# Initialize assets in the background
initialize_assets()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Global variables
tokens_path = "tokens.json"  # Default path, will be updated in main.py
tokens = {}  # Store tokens data
sort_ascending = True  # Default sort order
last_tokens_update = 0  # Track when tokens were last updated from disk
tokens_cache = {}  # Cache for generated TOTP codes
response_cache = {}  # Cache for API responses
last_file_write = 0  # Track when tokens were last written to disk
file_write_pending = False  # Flag to track if a file write is pending
file_write_lock = threading.Lock()  # Lock for thread-safe file operations

# Performance optimization: Increase cache size and TTL
CACHE_TTL = 2  # Reduced from 30 to 2 seconds for more real-time updates
CACHE_SIZE = 512  # Increased from 256 to 512 for better caching

# Cache control constants
STATIC_CACHE_MAX_AGE = 3600 * 24 * 7  # 7 days for static resources
HTML_CACHE_MAX_AGE = 3600  # 1 hour for HTML templates
API_CACHE_MAX_AGE = 30  # 30 seconds for API responses (except tokens)

# Override static file serving to add cache headers
@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files with proper cache headers"""
    response = send_from_directory('static', filename)
    
    # Add cache control headers for static resources
    response.headers['Cache-Control'] = f'public, max-age={STATIC_CACHE_MAX_AGE}'
    response.headers['Expires'] = datetime.utcfromtimestamp(time.time() + STATIC_CACHE_MAX_AGE).strftime('%a, %d %b %Y %H:%M:%S GMT')
    
    return response

# Enable gzip compression for responses, but only for API endpoints
@app.after_request
def after_request(response):
    # Add cache control headers based on content type and path
    if request.path.startswith('/static/'):
        # Static files already handled by serve_static
        pass
    elif request.path.startswith('/api/'):
        if request.path == '/api/tokens' or 'time_remaining' in str(response.data):
            # No caching for real-time data
            response.headers['Cache-Control'] = 'no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        else:
            # Short cache for other API responses
            response.headers['Cache-Control'] = f'private, max-age={API_CACHE_MAX_AGE}'
    else:
        # HTML templates - use a moderate cache time
        response.headers['Cache-Control'] = f'private, max-age={HTML_CACHE_MAX_AGE}'
        response.headers['Varies'] = 'Accept-Encoding'
    
    # Only compress JSON API responses, not static files or HTML
    if not request.path.startswith('/api/'):
        return response
        
    # Check if client accepts gzip compression
    if 'gzip' not in request.headers.get('Accept-Encoding', ''):
        return response
    
    # Don't compress small responses
    if int(response.headers.get('Content-Length', '0')) < 500:
        return response
    
    # Don't compress already compressed responses
    if response.headers.get('Content-Encoding') is not None:
        return response
    
    # Compress the response
    gzip_buffer = io.BytesIO()
    with gzip.GzipFile(mode='wb', fileobj=gzip_buffer) as gzip_file:
        gzip_file.write(response.data)
    
    # Update the response with the compressed data
    response.data = gzip_buffer.getvalue()
    response.headers['Content-Encoding'] = 'gzip'
    response.headers['Content-Length'] = len(response.data)
    response.headers['Vary'] = 'Accept-Encoding'
    
    return response

@app.route('/')
def index():
    """Main page with token list"""
    global tokens
    
    # Check if we need to reload tokens from disk
    load_tokens_if_needed()
    
    # Render the template with the tokens data
    return render_template('index.html', 
                          has_tokens=len(tokens) > 0,
                          sort_ascending=sort_ascending,
                          cache_buster=int(time.time() / HTML_CACHE_MAX_AGE))  # Cache buster that changes hourly

@app.route('/add_token')
def add_token_page():
    """Page for adding a new token"""
    return render_template('add_token.html', cache_buster=int(time.time() / HTML_CACHE_MAX_AGE))

@app.route('/manual_entry')
def manual_entry():
    """Page for manually entering token details"""
    return render_template('manual_entry.html', cache_buster=int(time.time() / HTML_CACHE_MAX_AGE))

@app.route('/qr_scan')
def qr_scan():
    """Page for scanning QR codes"""
    return render_template('qr_scan.html', cache_buster=int(time.time() / HTML_CACHE_MAX_AGE))

@app.route('/settings')
def settings():
    """Settings page"""
    return render_template('settings.html', cache_buster=int(time.time() / HTML_CACHE_MAX_AGE))

@app.route('/about')
def about():
    """About page"""
    return render_template('about.html', cache_buster=int(time.time() / HTML_CACHE_MAX_AGE))

@app.route('/service-worker.js')
def service_worker():
    """Serve the service worker from the root path for better scope"""
    response = send_from_directory('static/js', 'service-worker.js')
    # No caching for service worker
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

# Performance optimization: Increased cache size
@lru_cache(maxsize=CACHE_SIZE)
def generate_totp(secret, timestamp_30s):
    """Generate a TOTP code for a given secret and timestamp."""
    totp = pyotp.TOTP(secret)
    return totp.at(timestamp_30s * 30)

# Performance optimization: Load tokens only when needed
def load_tokens_if_needed():
    """Load tokens from disk if they've been modified since last load."""
    global tokens, last_tokens_update
    
    try:
        # Check if the file exists and has been modified
        if os.path.exists(tokens_path):
            file_mtime = os.path.getmtime(tokens_path)
            
            # Only reload if the file has been modified
            if file_mtime > last_tokens_update:
                with file_write_lock:
                    tokens = read_json(tokens_path)
                    last_tokens_update = file_mtime
    except Exception as e:
        print(f"Error loading tokens: {e}")

@app.route('/api/tokens', methods=['GET'])
def get_tokens():
    """API endpoint to get all tokens"""
    global tokens, tokens_cache, response_cache
    
    # Get accurate time once for the entire request to ensure consistency
    accurate_time = get_accurate_time()
    timestamp_30s = int(accurate_time // 30)
    current_period_start = timestamp_30s * 30
    next_period_start = current_period_start + 30
    time_remaining = round(next_period_start - accurate_time, 1)  # Round to 1 decimal place
    
    # Check if we have a cached response that's still valid
    cache_key = f"tokens_{sort_ascending}"
    
    # Load tokens if needed
    load_tokens_if_needed()
    
    # Check if we can use cached token codes but with updated time_remaining
    # Only use cache if we're not close to the period boundary (within 1 second)
    if cache_key in response_cache and time_remaining > 1 and time_remaining < 29:
        cache_entry = response_cache[cache_key]
        # Only reuse cached codes if we're still in the same 30-second window
        if timestamp_30s == int(cache_entry['timestamp'] // 30):
            # Get the cached data but update the time_remaining and server_time
            response_data = cache_entry['data']
            # Update time_remaining for each token
            for token in response_data:
                token['time_remaining'] = time_remaining
            return jsonify({
                'tokens': response_data,
                'server_time': accurate_time,
                'current_period_start': current_period_start,
                'next_period_start': next_period_start,
                'time_remaining': time_remaining
            })
    
    # Prepare the response data
    response_data = []
    
    for token_id, token_data in tokens.items():
        # Get the token secret
        secret = token_data.get('secret', '')
        
        # Check if we have a cached code for this token and timestamp
        cache_key_token = f"{secret}_{timestamp_30s}"
        
        if cache_key_token in tokens_cache:
            code = tokens_cache[cache_key_token]
        else:
            # Generate a new code
            code = generate_totp(secret, timestamp_30s)
            # Cache the code
            tokens_cache[cache_key_token] = code
        
        # Add the token data to the response
        response_data.append({
            'id': token_id,
            'issuer': token_data.get('issuer', 'Unknown'),
            'name': token_data.get('name', ''),
            'code': code,
            'time_remaining': time_remaining  # Add time_remaining to each token
        })
    
    # Cache the response only if we're not close to the period boundary
    if time_remaining > 1 and time_remaining < 29:
        response_cache[cache_key] = {
            'timestamp': accurate_time,
            'data': response_data
        }
    
    # Clean up old cache entries
    clean_cache()
    
    # Add Cache-Control header for real-time updates
    response = jsonify({
        'tokens': response_data,
        'server_time': accurate_time,
        'current_period_start': current_period_start,
        'next_period_start': next_period_start,
        'time_remaining': time_remaining
    })
    
    # Ensure TOTP codes are never cached by the browser
    response.headers['Cache-Control'] = 'no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    
    return response

# Performance optimization: Clean up old cache entries
def clean_cache():
    """Remove old entries from the cache."""
    global tokens_cache, response_cache
    
    # Get the current timestamp using accurate time
    accurate_time = get_accurate_time()
    current_timestamp_30s = int(accurate_time // 30)
    
    # Clean up tokens cache (keep only entries for the current timestamp)
    # This ensures we don't accumulate stale codes
    tokens_cache = {k: v for k, v in tokens_cache.items() 
                   if k.endswith(f"_{current_timestamp_30s}")}
    
    # Clean up response cache more aggressively (keep only very recent entries)
    response_cache = {k: v for k, v in response_cache.items() 
                     if accurate_time - v['timestamp'] < CACHE_TTL}

# Function to write tokens to file in a separate thread
def delayed_write_tokens():
    """Write tokens to disk after a delay to batch multiple changes."""
    global tokens, file_write_pending, last_file_write
    
    # Set the flag to indicate a write is pending
    file_write_pending = True
    
    # Wait a short time to batch multiple changes
    time.sleep(0.5)
    
    # Acquire the lock to ensure thread safety
    with file_write_lock:
        # Check if another thread has already written the file
        if not file_write_pending:
            return
        
        try:
            # Write the tokens to disk
            write_json(tokens_path, tokens)
            
            # Update the last write time
            last_file_write = time.time()
            
            # Reset the flag
            file_write_pending = False
        except Exception as e:
            print(f"Error writing tokens: {e}")
            file_write_pending = False

@app.route('/api/add_token', methods=['POST'])
def add_token():
    """API endpoint to add a new token"""
    global tokens
    
    # Get the token data from the request
    data = request.json
    
    # Validate the token data
    if not data or 'secret' not in data:
        return jsonify({'success': False, 'error': 'Invalid token data'})
    
    # Generate a unique ID for the token
    token_id = str(uuid.uuid4())
    
    # Create a new token object
    new_token = {
        'secret': data['secret'],
        'issuer': data.get('issuer', 'Unknown'),
        'name': data.get('name', ''),
        'type': data.get('type', 'totp'),
        'algorithm': data.get('algorithm', 'SHA1'),
        'digits': data.get('digits', 6),
        'period': data.get('period', 30)
    }
    
    # Add the token to the tokens dictionary
    with file_write_lock:
        tokens[token_id] = new_token
    
    # Write the tokens to disk in a separate thread
    threading.Thread(target=delayed_write_tokens).start()
    
    return jsonify({'success': True})

@app.route('/api/delete_token/<token_id>', methods=['DELETE'])
def delete_token(token_id):
    """API endpoint to delete a token"""
    global tokens
    
    # Check if the token exists
    if token_id not in tokens:
        return jsonify({'success': False, 'error': 'Token not found'})
    
    # Remove the token from the tokens dictionary
    with file_write_lock:
        del tokens[token_id]
    
    # Write the tokens to disk in a separate thread
    threading.Thread(target=delayed_write_tokens).start()
    
    return jsonify({'success': True})

@app.route('/api/sort_tokens', methods=['POST'])
def sort_tokens():
    """API endpoint to toggle token sorting"""
    global sort_ascending
    
    # Get the sort order from the request
    data = request.json
    
    # Update the sort order
    sort_ascending = data.get('sort_ascending', not sort_ascending)
    
    # Only clear the tokens cache entries in the response cache
    # This preserves other cached responses while ensuring tokens are re-sorted
    keys_to_remove = [k for k in response_cache.keys() if k.startswith('tokens_')]
    for key in keys_to_remove:
        if key in response_cache:
            del response_cache[key]
    
    return jsonify({'success': True, 'sort_ascending': sort_ascending})

@app.route('/api/search_tokens', methods=['POST'])
def search_tokens():
    """API endpoint to search tokens"""
    global tokens
    
    # Get accurate time once for the entire request to ensure consistency
    accurate_time = get_accurate_time()
    timestamp_30s = int(accurate_time // 30)
    time_remaining = 30 - (int(accurate_time) % 30)
    
    # Get the search query from the request
    data = request.json
    query = data.get('query', '').lower()
    
    # Load tokens if needed
    load_tokens_if_needed()
    
    # Filter the tokens based on the query
    filtered_tokens = {}
    
    for token_id, token_data in tokens.items():
        issuer = token_data.get('issuer', '').lower()
        name = token_data.get('name', '').lower()
        
        if query in issuer or query in name:
            filtered_tokens[token_id] = token_data
    
    # Prepare the response data
    response_data = []
    
    for token_id, token_data in filtered_tokens.items():
        # Get the token secret
        secret = token_data.get('secret', '')
        
        # Check if we have a cached code for this token and timestamp
        cache_key_token = f"{secret}_{timestamp_30s}"
        
        if cache_key_token in tokens_cache:
            code = tokens_cache[cache_key_token]
        else:
            # Generate a new code
            code = generate_totp(secret, timestamp_30s)
            # Cache the code
            tokens_cache[cache_key_token] = code
        
        # Add the token data to the response
        response_data.append({
            'id': token_id,
            'issuer': token_data.get('issuer', 'Unknown'),
            'name': token_data.get('name', ''),
            'code': code,
            'time_remaining': time_remaining
        })
    
    return jsonify({'success': True, 'tokens': response_data})

@app.route('/api/process_qr', methods=['POST'])
def process_qr():
    """API endpoint to process a QR code image"""
    if 'image' not in request.files:
        return jsonify({'success': False, 'error': 'No image provided'})
    
    image_file = request.files['image']
    
    try:
        # Read the image data
        image_data = image_file.read()
        
        # Convert the image data to a PIL Image
        image = Image.open(io.BytesIO(image_data))
        
        # Scan the QR code
        qr_data = scan_qr_image(image)
        
        if not qr_data:
            return jsonify({'success': False, 'error': 'No QR code found'})
        
        # Parse the QR code data
        if qr_data.startswith('otpauth://'):
            # Parse the OTP auth URI
            try:
                # Extract the type (totp or hotp)
                if 'totp' in qr_data:
                    token_type = 'totp'
                elif 'hotp' in qr_data:
                    token_type = 'hotp'
                else:
                    return jsonify({'success': False, 'error': 'Unsupported OTP type'})
                
                # Extract the issuer and name
                parts = qr_data.split('/')
                if len(parts) < 4:
                    return jsonify({'success': False, 'error': 'Invalid OTP URI'})
                
                label = parts[3].split('?')[0]
                
                # The label can be in the format "issuer:name" or just "name"
                if ':' in label:
                    issuer, name = label.split(':', 1)
                else:
                    issuer = 'Unknown'
                    name = label
                
                # URL decode the issuer and name
                import urllib.parse
                issuer = urllib.parse.unquote(issuer)
                name = urllib.parse.unquote(name)
                
                # Extract the secret and other parameters
                import urllib.parse
                params = dict(urllib.parse.parse_qsl(qr_data.split('?', 1)[1]))
                
                secret = params.get('secret', '')
                
                # Extract the issuer from the parameters if available
                if 'issuer' in params:
                    issuer = params['issuer']
                
                # Extract other parameters
                algorithm = params.get('algorithm', 'SHA1')
                digits = int(params.get('digits', '6'))
                period = int(params.get('period', '30'))
                
                # Create a token object
                token = {
                    'type': token_type,
                    'issuer': issuer,
                    'name': name,
                    'secret': secret,
                    'algorithm': algorithm,
                    'digits': digits,
                    'period': period
                }
                
                return jsonify({'success': True, 'token': token})
            except Exception as e:
                return jsonify({'success': False, 'error': f'Error parsing OTP URI: {str(e)}'})
        else:
            return jsonify({'success': False, 'error': 'Not an OTP auth URI'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error processing image: {str(e)}'})

@app.route('/api/bulk_import', methods=['POST'])
def bulk_import():
    """API endpoint to import tokens in bulk"""
    global tokens
    
    # Get the import data from the request
    data = request.json
    
    if not data or 'tokens' not in data:
        return jsonify({'success': False, 'error': 'Invalid import data'})
    
    import_tokens = data['tokens']
    
    if not isinstance(import_tokens, list):
        return jsonify({'success': False, 'error': 'Import data must be a list'})
    
    # Count of successfully imported tokens
    imported_count = 0
    
    # Process each token
    with file_write_lock:
        for token_data in import_tokens:
            # Validate the token data
            if not isinstance(token_data, dict) or 'secret' not in token_data:
                continue
            
            # Generate a unique ID for the token
            token_id = str(uuid.uuid4())
            
            # Create a new token object
            new_token = {
                'secret': token_data['secret'],
                'issuer': token_data.get('issuer', 'Unknown'),
                'name': token_data.get('name', ''),
                'type': token_data.get('type', 'totp'),
                'algorithm': token_data.get('algorithm', 'SHA1'),
                'digits': token_data.get('digits', 6),
                'period': token_data.get('period', 30)
            }
            
            # Add the token to the tokens dictionary
            tokens[token_id] = new_token
            imported_count += 1
    
    # Write the tokens to disk in a separate thread
    threading.Thread(target=delayed_write_tokens).start()
    
    return jsonify({'success': True, 'imported': imported_count})

@app.route('/api/ntp_status', methods=['GET'])
def ntp_status():
    """API endpoint to get NTP synchronization status"""
    status = get_sync_status()
    return jsonify({'success': True, 'status': status})

@app.route('/api/ntp_sync', methods=['POST'])
def ntp_sync():
    """API endpoint to manually trigger NTP synchronization"""
    # Trigger a manual NTP synchronization
    offset = calculate_offset()
    
    # Get the updated status
    status = get_sync_status()
    
    return jsonify({
        'success': True, 
        'offset': offset,
        'status': status
    })

def set_tokens_path(path):
    """Set the path to the tokens file."""
    global tokens_path, tokens, last_tokens_update
    
    # Set the tokens path
    tokens_path = path
    
    # Load the tokens from the file if it exists
    if os.path.exists(tokens_path):
        try:
            tokens = read_json(tokens_path)
            last_tokens_update = os.path.getmtime(tokens_path)
        except Exception as e:
            print(f"Error loading tokens: {e}")
            tokens = {}
    else:
        # Create an empty tokens file
        tokens = {}
        write_json(tokens_path, tokens)
        last_tokens_update = os.path.getmtime(tokens_path)

def start_flask(debug=False, port=5000):
    """Start the Flask application"""
    global app
    
    # Start NTP synchronization with a 1-hour interval in a separate thread
    # to avoid blocking startup
    threading.Thread(target=start_ntp_sync, args=(3600,), daemon=True).start()
    
    # Start the Flask application
    if debug:
        # In debug mode, we need to disable the reloader when running in a thread
        # to avoid the signal handler error
        app.run(host='127.0.0.1', port=port, debug=True, use_reloader=False, threaded=True)
    else:
        app.run(host='127.0.0.1', port=port, debug=False, threaded=True)

# This class is maintained for compatibility with the old code
class WinOTP:
    def __init__(self, tokens_path_arg):
        # Set the tokens path
        set_tokens_path(tokens_path_arg)
        
    def mainloop(self):
        # This method is kept for compatibility but does nothing
        pass
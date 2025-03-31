"""
Google Authenticator QR code processing utility

This module handles the scanning and parsing of Google Authenticator QR codes.
"""

import base64
from urllib.parse import unquote, parse_qs, urlparse
from PIL import Image, ImageEnhance
from pyzbar import pyzbar
import io

def scan_google_auth_qr_from_image(image):
    """
    Scan a Google Authenticator QR code from a PIL Image
    
    Args:
        image: PIL Image object containing the QR code
        
    Returns:
        dict: A dictionary containing the scan result information
    """
    # Try multiple image processing techniques to extract QR code
    decoded_objects = _scan_with_preprocessing(image)
    
    if not decoded_objects:
        return {"status": "error", "message": "No QR code found in the image"}
    
    # Process each decoded object
    for obj in decoded_objects:
        try:
            # Convert QR data to string
            if isinstance(obj.data, bytes):
                data = obj.data.decode('utf-8')
            elif isinstance(obj.data, str):
                data = obj.data
            else:
                # Try string conversion as last resort
                data = str(obj.data)
            
            # Debug output
            print(f"QR data: {data[:100]}...")
            
            # Check if it's a Google Authenticator QR code
            if data.startswith('otpauth-migration://offline?data='):
                return {
                    "status": "success", 
                    "data": data,
                    "type": "google_auth_migration"
                }
        except Exception as e:
            print(f"Error processing QR data: {str(e)}")
            continue
    
    return {"status": "error", "message": "No valid Google Authenticator QR code found"}

def _scan_with_preprocessing(image):
    """
    Apply various preprocessing techniques to improve QR code detection
    
    Args:
        image: PIL Image object
        
    Returns:
        list: Decoded QR code objects
    """
    # Try original image first
    decoded_objects = pyzbar.decode(image)
    if decoded_objects:
        return decoded_objects
    
    # Try grayscale conversion
    image_gray = image.convert('L')
    decoded_objects = pyzbar.decode(image_gray)
    if decoded_objects:
        return decoded_objects
    
    # Try resizing
    width, height = image.size
    # First try enlarging
    new_size = (width * 2, height * 2)
    image_resized = image.resize(new_size, Image.LANCZOS)
    decoded_objects = pyzbar.decode(image_resized)
    if decoded_objects:
        return decoded_objects
    
    # Try contrast enhancement
    enhancer = ImageEnhance.Contrast(image)
    image_enhanced = enhancer.enhance(2.0)
    decoded_objects = pyzbar.decode(image_enhanced)
    if decoded_objects:
        return decoded_objects
    
    # Try brightness adjustment
    enhancer = ImageEnhance.Brightness(image)
    image_enhanced = enhancer.enhance(1.5)
    decoded_objects = pyzbar.decode(image_enhanced)
    
    return decoded_objects

def decode_migration_payload(qr_data):
    """
    Decode the migration payload from Google Authenticator QR code
    
    Args:
        qr_data (str): The raw QR code data string
        
    Returns:
        tuple: (status, result) where status is a boolean success flag
               and result is either the decoded payload or an error message
    """
    from utils.google_auth_pb2 import MigrationPayload
    
    try:
        # Extract the base64 data
        if not qr_data.startswith('otpauth-migration://offline?data='):
            return (False, "Invalid Google Authenticator QR code format")
        
        # First try the standard URL parsing approach
        try:
            # Parse the URL to handle the data parameter correctly
            parsed_url = urlparse(qr_data)
            query_params = parse_qs(parsed_url.query)
            
            if 'data' in query_params and query_params['data']:
                # Get the data parameter
                data = query_params['data'][0]
            else:
                # Try alternative extraction if URL parsing fails
                data = extract_migration_data_alternative(qr_data)
                
                if not data:
                    # Final fallback: direct replacement
                    data = qr_data.replace('otpauth-migration://offline?data=', '')
        except Exception as e:
            print(f"URL parsing failed: {str(e)}, trying alternative extraction")
            data = extract_migration_data_alternative(qr_data)
            
            if not data:
                # Final fallback
                data = qr_data.replace('otpauth-migration://offline?data=', '')
        
        # Clean and pad the data
        data = clean_and_pad_base64(data)
        print(f"Prepared base64 data for decoding: {data[:30]}...")
        
        # Decode the base64 data
        try:
            decoded_data = base64.b64decode(data)
            print(f"Successfully decoded {len(decoded_data)} bytes of data")
        except Exception as e:
            print(f"Base64 decoding error: {str(e)}")
            # Try one more approach - replace special characters
            data = data.replace('-', '+').replace('_', '/')
            try:
                # Try again with modified data
                decoded_data = base64.b64decode(data)
                print(f"Successfully decoded {len(decoded_data)} bytes after character replacement")
            except Exception as e:
                return (False, f"Failed to decode base64 data: {str(e)}")
        
        # Parse the protobuf data
        try:
            migration_payload = MigrationPayload()
            migration_payload.ParseFromString(decoded_data)
            print(f"Successfully parsed protobuf data with {len(migration_payload.otp_parameters)} OTP parameters")
            return (True, migration_payload)
        except Exception as e:
            print(f"Protobuf parsing error: {str(e)}")
            return (False, f"Failed to parse QR code data: {str(e)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        return (False, f"Error decoding migration payload: {str(e)}")

def scan_google_auth_qr_from_file(file_path):
    """
    Scan a Google Authenticator QR code from a file
    
    Args:
        file_path (str): Path to the image file or base64 data URL
        
    Returns:
        dict: A dictionary containing the scan result information
    """
    import re
    
    try:
        # Check if file_path is valid
        if not file_path:
            return {"status": "error", "message": "No file provided"}
            
        # Is it a base64 data URL?
        if isinstance(file_path, str) and re.match(r'^data:image\/(jpeg|png|gif|bmp);base64,', file_path):
            # It's a base64 data URL
            try:
                # Strip the prefix and decode
                base64_data = file_path.split(',', 1)[1]
                image_data = base64.b64decode(base64_data)
                image = Image.open(io.BytesIO(image_data))
            except Exception as e:
                return {"status": "error", "message": f"Invalid image data: {str(e)}"}
        else:
            # Try to open as a file path
            try:
                image = Image.open(file_path)
            except Exception as e:
                return {"status": "error", "message": f"Could not open image file: {str(e)}"}
        
        # Scan the image
        return scan_google_auth_qr_from_image(image)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"status": "error", "message": f"Error scanning QR code: {str(e)}"}

def extract_migration_data_alternative(qr_data):
    """
    Alternative method to extract data from Google Authenticator QR code
    when the standard parsing fails
    
    Args:
        qr_data (str): The raw QR code data string
        
    Returns:
        str: Extracted data part, or None if extraction fails
    """
    import re
    
    if not qr_data.startswith('otpauth-migration://offline?data='):
        return None
    
    # Try different regex patterns to extract the data
    patterns = [
        r'otpauth-migration://offline\?data=([^&]+)',  # Standard format
        r'data=([^&]+)',                              # Just extract data parameter
        r'offline\?data=(.+)$'                        # Everything after data=
    ]
    
    for pattern in patterns:
        match = re.search(pattern, qr_data)
        if match:
            data = match.group(1)
            print(f"Successfully extracted data using pattern: {pattern}")
            return data
    
    # If all regex approaches fail, try direct string manipulation
    try:
        data = qr_data.split('data=', 1)[1]
        # Check if there are other parameters
        if '&' in data:
            data = data.split('&', 1)[0]
        print(f"Extracted data using string split")
        return data
    except Exception:
        return None
    
def clean_and_pad_base64(data):
    """
    Clean and pad a base64 string to ensure it can be decoded correctly
    
    Args:
        data (str): The base64 data string
        
    Returns:
        str: Cleaned and padded base64 string
    """
    from urllib.parse import unquote
    
    # URL decode
    data = unquote(data)
    
    # Replace URL-safe base64 characters with standard ones
    data = data.replace('-', '+').replace('_', '/')
    
    # Remove any non-base64 characters
    data = ''.join(c for c in data if c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=')
    
    # Add padding if necessary
    padding_needed = len(data) % 4
    if padding_needed:
        data += '=' * (4 - padding_needed)
        
    return data 
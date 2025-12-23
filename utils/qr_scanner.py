from PIL import Image
from pyzbar.pyzbar import decode
import re
from urllib.parse import unquote, urlparse, parse_qs

def scan_qr_image(image_input):
    """Scan a QR code image and extract TOTP information
    
    Args:
        image_input (str or PIL.Image): Path to the QR code image or a PIL Image object
        
    Returns:
        tuple: (issuer, secret, name) or the raw QR data string for Google Auth migration QR codes
    """
    try:
        # Handle both file path and PIL Image input
        if isinstance(image_input, str):
            # Open the image from file path
            img = Image.open(image_input)
        elif isinstance(image_input, Image.Image):
            # Use the provided PIL Image directly
            img = image_input
        else:
            print(f"Invalid image input type: {type(image_input)}")
            return None
        
        # Decode QR code
        decoded_objects = decode(img)
        
        if not decoded_objects:
            return None
            
        # Get the data from the first QR code
        qr_data = decoded_objects[0].data.decode('utf-8')
        print(f"QR code decoded successfully, data: {qr_data[:100]}...")
        
        # Check if it's a Google Authenticator migration QR code
        if qr_data.startswith('otpauth-migration://offline?data='):
            # Return the raw data for Google Auth migration QR codes
            return qr_data
        
        # Check if it's an otpauth URL
        if not qr_data.startswith('otpauth://totp/'):
            print(f"Not a TOTP otpauth URL: {qr_data[:50]}")
            return None
        
        # Parse the otpauth URL using urllib for robustness
        try:
            parsed = urlparse(qr_data)
            
            # Extract the path (account/label info)
            # Path format can be: /ACCOUNT, /ISSUER:ACCOUNT, or /ACCOUNT with issuer in params
            path = unquote(parsed.path.lstrip('/'))
            
            # Parse query parameters
            params = parse_qs(parsed.query)
            
            # Extract secret (required)
            secret = params.get('secret', [None])[0]
            if not secret:
                print("No secret found in QR code")
                return None
            
            # Extract issuer from params if available
            issuer_param = params.get('issuer', [None])[0]
            if issuer_param:
                issuer_param = unquote(issuer_param)
            
            # Parse the path for issuer:account format
            if ':' in path:
                # Format: ISSUER:ACCOUNT
                issuer_from_path, name = path.split(':', 1)
            else:
                # Format: just ACCOUNT
                issuer_from_path = None
                name = path
            
            # Use issuer from parameter if available, otherwise from path
            issuer = issuer_param or issuer_from_path or "Unknown"
            
            print(f"Parsed TOTP: issuer={issuer}, name={name}, secret={secret[:4]}...")
            return (issuer, secret, name)
            
        except Exception as parse_error:
            print(f"Error parsing otpauth URL: {parse_error}")
            return None
        
    except Exception as e:
        print(f"Error scanning QR code: {e}")
        return None

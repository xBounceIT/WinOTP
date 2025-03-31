from PIL import Image
from pyzbar.pyzbar import decode
import re
from urllib.parse import unquote

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
        
        # Check if it's a Google Authenticator migration QR code
        if qr_data.startswith('otpauth-migration://offline?data='):
            # Return the raw data for Google Auth migration QR codes
            return qr_data
        
        # Parse the otpauth URL
        # Format: otpauth://totp/ISSUER:ACCOUNT?secret=SECRET&issuer=ISSUER
        match = re.match(r'otpauth://totp/([^:]+):([^?]+)\?secret=([^&]+)(&.*)?', qr_data)
        
        if match:
            issuer = unquote(match.group(1))
            name = unquote(match.group(2))
            secret = match.group(3)
            return (issuer, secret, name)
            
        # Alternative format: otpauth://totp/ACCOUNT?secret=SECRET&issuer=ISSUER
        match = re.match(r'otpauth://totp/([^?]+)\?secret=([^&]+)&issuer=([^&]+)(.*)?', qr_data)
        
        if match:
            name = unquote(match.group(1))
            secret = match.group(2)
            issuer = unquote(match.group(3))
            return (issuer, secret, name)
            
        return None
        
    except Exception as e:
        print(f"Error scanning QR code: {e}")
        return None 
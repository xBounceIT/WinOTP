from PIL import Image
from pyzbar.pyzbar import decode
import re
from urllib.parse import unquote

def scan_qr_image(image_path):
    """Scan a QR code image and extract TOTP information
    
    Args:
        image_path (str): Path to the QR code image
        
    Returns:
        tuple: (issuer, secret, name) or None if invalid
    """
    try:
        # Open the image
        img = Image.open(image_path)
        
        # Decode QR code
        decoded_objects = decode(img)
        
        if not decoded_objects:
            return None
            
        # Get the data from the first QR code
        qr_data = decoded_objects[0].data.decode('utf-8')
        
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
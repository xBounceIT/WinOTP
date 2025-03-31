"""
Utility script to extract QR code from base64 data and save to file
"""

import base64
import sys
from PIL import Image
import io

def save_base64_image(base64_data, output_file):
    """
    Save base64 image data to a file
    
    Args:
        base64_data (str): Base64 encoded image data
        output_file (str): Output file path
    """
    try:
        # If the data starts with a prefix, strip it
        if ',' in base64_data:
            base64_data = base64_data.split(',', 1)[1]
        
        # Decode the base64 data
        image_data = base64.b64decode(base64_data)
        
        # Create a PIL Image from the binary data
        image = Image.open(io.BytesIO(image_data))
        
        # Save the image to file
        image.save(output_file)
        print(f"Image saved to {output_file}")
        return True
    except Exception as e:
        print(f"Error saving image: {str(e)}")
        return False

if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) != 3:
        print("Usage: python extract_qr.py <base64_data_file> <output_image_file>")
        sys.exit(1)
    
    # Get the base64 data from file
    base64_file = sys.argv[1]
    output_file = sys.argv[2]
    
    try:
        with open(base64_file, 'r') as f:
            base64_data = f.read().strip()
        
        success = save_base64_image(base64_data, output_file)
        
        if success:
            print("QR code extracted successfully")
            sys.exit(0)
        else:
            print("Failed to extract QR code")
            sys.exit(1)
    except Exception as e:
        print(f"Error reading base64 data file: {str(e)}")
        sys.exit(1) 
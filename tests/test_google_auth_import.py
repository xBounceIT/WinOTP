"""
Test script for Google Authenticator QR code import functionality.

Run this script with:
python test_google_auth_import.py <path_to_qr_image>
"""

import sys
import os
from utils.google_auth_qr import scan_google_auth_qr_from_file, decode_migration_payload

def test_google_auth_qr_import(image_path):
    """Test Google Authenticator QR code import with a given image file"""
    print(f"Testing Google Auth QR code import with image: {image_path}")
    
    # Check if file exists
    if not os.path.exists(image_path):
        print(f"Error: File does not exist: {image_path}")
        return False
    
    # Scan the QR code
    print("Scanning QR code...")
    scan_result = scan_google_auth_qr_from_file(image_path)
    
    if scan_result["status"] == "error":
        print(f"Error scanning QR code: {scan_result['message']}")
        return False
    
    print("Successfully scanned QR code")
    qr_data = scan_result["data"]
    print(f"QR data (first 50 chars): {qr_data[:50]}...")
    
    # Decode the migration payload
    print("Decoding migration payload...")
    success, result = decode_migration_payload(qr_data)
    
    if not success:
        print(f"Error decoding migration payload: {result}")
        return False
    
    # Got valid migration payload
    migration_payload = result
    print(f"Successfully decoded migration payload")
    print(f"Found {len(migration_payload.otp_parameters)} OTP parameters")
    
    # Print details about each token (without revealing secrets)
    for i, otp_param in enumerate(migration_payload.otp_parameters):
        print(f"Token {i+1}:")
        print(f"  Issuer: {otp_param.issuer or 'Unknown'}")
        print(f"  Name: {otp_param.name or 'Unknown'}")
        print(f"  Secret: {'*' * 10} (hidden for security)")
    
    return True

if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) != 2:
        print("Usage: python test_google_auth_import.py <path_to_qr_image>")
        sys.exit(1)
    
    image_path = sys.argv[1]
    success = test_google_auth_qr_import(image_path)
    
    if success:
        print("\nTest completed successfully!")
        sys.exit(0)
    else:
        print("\nTest failed!")
        sys.exit(1) 
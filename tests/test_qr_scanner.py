import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
from PIL import Image, ImageDraw
import qrcode
from utils.qr_scanner import scan_qr_image

class TestQRScanner(unittest.TestCase):
    """Test cases for QR code scanning functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create test QR code images
        self.create_test_qr_codes()
        
    def tearDown(self):
        """Tear down test fixtures"""
        try:
            # Remove test files
            for filename in os.listdir(self.test_dir):
                try:
                    os.remove(os.path.join(self.test_dir, filename))
                except (PermissionError, OSError):
                    # Skip files that can't be removed
                    pass
            os.rmdir(self.test_dir)
        except (PermissionError, OSError):
            # If we can't remove the directory, just log it
            print(f"Warning: Could not remove temporary directory {self.test_dir}")
        
    def create_test_qr_codes(self):
        """Create test QR code images"""
        # Standard format: otpauth://totp/ISSUER:ACCOUNT?secret=SECRET&issuer=ISSUER
        standard_data = "otpauth://totp/Test%20Issuer:test%40example.com?secret=JBSWY3DPEHPK3PXP&issuer=Test%20Issuer"
        self.standard_qr_path = os.path.join(self.test_dir, "standard_qr.png")
        self.create_qr_code(standard_data, self.standard_qr_path)
        
        # Alternative format: otpauth://totp/ACCOUNT?secret=SECRET&issuer=ISSUER
        alt_data = "otpauth://totp/test%40example.com?secret=JBSWY3DPEHPK3PXP&issuer=Test%20Issuer"
        self.alt_qr_path = os.path.join(self.test_dir, "alt_qr.png")
        self.create_qr_code(alt_data, self.alt_qr_path)
        
        # Invalid format
        invalid_data = "https://example.com"
        self.invalid_qr_path = os.path.join(self.test_dir, "invalid_qr.png")
        self.create_qr_code(invalid_data, self.invalid_qr_path)
        
        # Create a non-QR image
        self.non_qr_path = os.path.join(self.test_dir, "non_qr.png")
        img = Image.new('RGB', (100, 100), color='white')
        d = ImageDraw.Draw(img)
        d.rectangle([(20, 20), (80, 80)], fill='black')
        img.save(self.non_qr_path)
        
    def create_qr_code(self, data, path):
        """Create a QR code image with the given data"""
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(path)
        
    def test_scan_standard_format(self):
        """Test scanning a QR code with standard format"""
        result = scan_qr_image(self.standard_qr_path)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)
        
        issuer, secret, name = result
        self.assertEqual(issuer, "Test Issuer")
        self.assertEqual(secret, "JBSWY3DPEHPK3PXP")
        self.assertEqual(name, "test@example.com")
        
    def test_scan_alternative_format(self):
        """Test scanning a QR code with alternative format"""
        result = scan_qr_image(self.alt_qr_path)
        
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)
        
        issuer, secret, name = result
        self.assertEqual(issuer, "Test Issuer")
        self.assertEqual(secret, "JBSWY3DPEHPK3PXP")
        self.assertEqual(name, "test@example.com")
        
    def test_scan_invalid_format(self):
        """Test scanning a QR code with invalid format"""
        result = scan_qr_image(self.invalid_qr_path)
        
        self.assertIsNone(result)
        
    def test_scan_non_qr_image(self):
        """Test scanning an image that is not a QR code"""
        result = scan_qr_image(self.non_qr_path)
        
        self.assertIsNone(result)
        
    def test_scan_nonexistent_file(self):
        """Test scanning a file that doesn't exist"""
        result = scan_qr_image(os.path.join(self.test_dir, "nonexistent.png"))
        
        self.assertIsNone(result)
        
    @patch('utils.qr_scanner.decode')
    def test_decode_error(self, mock_decode):
        """Test handling of decode errors"""
        # Mock decode to raise an exception
        mock_decode.side_effect = Exception("Decode error")
        
        # Use a path that doesn't require file access
        result = scan_qr_image("nonexistent_file.png")
        
        self.assertIsNone(result)

if __name__ == '__main__':
    unittest.main() 
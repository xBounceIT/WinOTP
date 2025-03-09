import unittest
import sys
import os
import tempfile
from PIL import Image, ImageDraw
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path so we can import the app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.qr_scanner import scan_qr_image

class TestQRScanner(unittest.TestCase):
    """Test cases for QR scanner utilities."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Remove all test files
        for file in os.listdir(self.test_dir):
            os.remove(os.path.join(self.test_dir, file))
        os.rmdir(self.test_dir)
    
    def create_dummy_image(self, filename):
        """Helper to create a dummy image for testing."""
        img = Image.new('RGB', (100, 100), color='white')
        d = ImageDraw.Draw(img)
        d.rectangle([(20, 20), (80, 80)], fill="black")
        
        img_path = os.path.join(self.test_dir, filename)
        img.save(img_path)
        return img_path
    
    @patch('utils.qr_scanner.decode')
    def test_scan_valid_qr_code_format1(self, mock_decode):
        """Test scanning a valid QR code with format: otpauth://totp/ISSUER:ACCOUNT?secret=SECRET."""
        # Create test data
        issuer = "Test Issuer"
        account = "test@example.com"
        secret = "JBSWY3DPEHPK3PXP"
        
        # Create a dummy image path
        img_path = self.create_dummy_image("test_qr1.png")
        
        # Mock the decode function to return data in the first format
        mock_decoded_obj = MagicMock()
        mock_decoded_obj.data.decode.return_value = f"otpauth://totp/{issuer}:{account}?secret={secret}&issuer={issuer}"
        mock_decode.return_value = [mock_decoded_obj]
        
        # Scan the QR code
        result = scan_qr_image(img_path)
        
        # Check results
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], issuer)  # issuer
        self.assertEqual(result[1], secret)  # secret
        self.assertEqual(result[2], account)  # name/account
    
    @patch('utils.qr_scanner.decode')
    def test_scan_valid_qr_code_format2(self, mock_decode):
        """Test scanning a valid QR code with format: otpauth://totp/ACCOUNT?secret=SECRET&issuer=ISSUER."""
        # Create test data
        issuer = "Test Issuer"
        account = "test@example.com"
        secret = "JBSWY3DPEHPK3PXP"
        
        # Create a dummy image path
        img_path = self.create_dummy_image("test_qr2.png")
        
        # Mock the decode function to return data in the second format
        mock_decoded_obj = MagicMock()
        mock_decoded_obj.data.decode.return_value = f"otpauth://totp/{account}?secret={secret}&issuer={issuer}"
        mock_decode.return_value = [mock_decoded_obj]
        
        # Scan the QR code
        result = scan_qr_image(img_path)
        
        # Check results
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0], issuer)  # issuer
        self.assertEqual(result[1], secret)  # secret
        self.assertEqual(result[2], account)  # name/account
    
    @patch('utils.qr_scanner.decode')
    def test_scan_invalid_qr_code(self, mock_decode):
        """Test scanning an invalid QR code that doesn't contain otpauth URL."""
        # Create a dummy image path
        img_path = self.create_dummy_image("invalid_qr.png")
        
        # Mock the decode function to return invalid data
        mock_decoded_obj = MagicMock()
        mock_decoded_obj.data.decode.return_value = "This is not an otpauth URL"
        mock_decode.return_value = [mock_decoded_obj]
        
        # Scan the QR code
        result = scan_qr_image(img_path)
        
        # Should return None for invalid data
        self.assertIsNone(result)
    
    @patch('utils.qr_scanner.decode')
    def test_scan_non_qr_image(self, mock_decode):
        """Test scanning an image that doesn't contain a QR code."""
        # Create a dummy image
        img_path = self.create_dummy_image("non_qr.png")
        
        # Mock the decode function to return empty list (no QR codes found)
        mock_decode.return_value = []
        
        # Scan the non-QR image
        result = scan_qr_image(img_path)
        
        # Should return None for non-QR image
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main() 
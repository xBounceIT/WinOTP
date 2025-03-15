import unittest
from unittest.mock import patch, MagicMock
import pyotp
import re
from models.token import Token

class TestToken(unittest.TestCase):
    """Test cases for the Token class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Valid base32 secret for testing
        self.valid_secret = "JBSWY3DPEHPK3PXP"
        self.issuer = "Test Issuer"
        self.name = "Test Account"
        
    def test_init(self):
        """Test Token initialization"""
        token = Token(self.issuer, self.valid_secret, self.name)
        
        self.assertEqual(token.issuer, self.issuer)
        self.assertEqual(token.secret, self.valid_secret)
        self.assertEqual(token.name, self.name)
        self.assertIsInstance(token.totp, pyotp.TOTP)
        
    @patch('models.token.get_accurate_time')
    def test_get_code(self, mock_get_accurate_time):
        """Test code generation with mocked time"""
        # Mock the time to get a predictable code
        mock_get_accurate_time.return_value = 0
        
        token = Token(self.issuer, self.valid_secret, self.name)
        
        # Calculate expected code manually
        expected_code = pyotp.TOTP(self.valid_secret).at(0)
        
        # Get the actual code
        actual_code = token.get_code()
        
        # Verify the code
        self.assertEqual(actual_code, expected_code)
        self.assertTrue(len(actual_code) == 6)
        self.assertTrue(re.match(r'^\d{6}$', actual_code))
        
    @patch('models.token.get_accurate_time')
    def test_get_time_remaining(self, mock_get_accurate_time):
        """Test time remaining calculation with mocked time"""
        # Mock the time to get a predictable result
        mock_get_accurate_time.return_value = 10  # 10 seconds into the period
        
        token = Token(self.issuer, self.valid_secret, self.name)
        
        # Default TOTP interval is 30 seconds
        expected_remaining = 20  # 30 - 10 = 20
        
        # Get the actual time remaining
        actual_remaining = token.get_time_remaining()
        
        # Verify the time remaining
        self.assertEqual(actual_remaining, expected_remaining)
        
    def test_validate_base32_secret_valid(self):
        """Test validation of valid base32 secrets"""
        # Test valid secrets
        valid_secrets = [
            "JBSWY3DPEHPK3PXP",  # Standard secret
            "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP",  # Longer secret
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"  # All valid chars
        ]
        
        for secret in valid_secrets:
            self.assertTrue(Token.validate_base32_secret(secret))
            
    def test_validate_base32_secret_invalid(self):
        """Test validation of invalid base32 secrets"""
        # Test invalid secrets
        invalid_secrets = [
            "",  # Empty
            "12345",  # Too short
            "INVALID!",  # Invalid characters
            "jbswy3dpehpk3pxp"  # Lowercase (base32 is uppercase)
        ]
        
        for secret in invalid_secrets:
            self.assertFalse(Token.validate_base32_secret(secret))
            
    @patch('models.token.get_accurate_time')
    def test_code_changes_with_time(self, mock_get_accurate_time):
        """Test that the code changes when the time period changes"""
        # Set initial time
        mock_get_accurate_time.return_value = 0
        
        token = Token(self.issuer, self.valid_secret, self.name)
        code1 = token.get_code()
        
        # Move to next time period
        mock_get_accurate_time.return_value = 30
        
        code2 = token.get_code()
        
        # Codes should be different
        self.assertNotEqual(code1, code2)

if __name__ == '__main__':
    unittest.main() 
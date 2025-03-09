import unittest
import sys
import os
from datetime import datetime
import time

# Add the parent directory to sys.path so we can import the app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.token import Token

class TestToken(unittest.TestCase):
    """Test cases for the Token model."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use a standard test secret for testing (from Google Authenticator docs)
        self.test_issuer = "TestIssuer"
        self.test_secret = "JBSWY3DPEHPK3PXP"  # This is a valid base32 secret
        self.test_name = "TestAccount"
        self.token = Token(self.test_issuer, self.test_secret, self.test_name)
    
    def test_token_initialization(self):
        """Test that a token is properly initialized with the right attributes."""
        self.assertEqual(self.token.issuer, self.test_issuer)
        self.assertEqual(self.token.secret, self.test_secret)
        self.assertEqual(self.token.name, self.test_name)
        self.assertIsNotNone(self.token.totp)
    
    def test_get_code(self):
        """Test that get_code() returns a 6-digit code."""
        code = self.token.get_code()
        self.assertIsNotNone(code)
        self.assertTrue(code.isdigit())
        self.assertEqual(len(code), 6)
    
    def test_get_time_remaining(self):
        """Test that get_time_remaining() returns a value between 0 and 30."""
        time_remaining = self.token.get_time_remaining()
        self.assertIsInstance(time_remaining, int)
        self.assertTrue(0 <= time_remaining <= 30)
        
        # Test that time decreases if we wait
        time.sleep(1)
        new_time_remaining = self.token.get_time_remaining()
        self.assertTrue(new_time_remaining <= time_remaining)
    
    def test_validate_base32_secret_valid(self):
        """Test that valid base32 secrets pass validation."""
        # Valid secrets
        self.assertTrue(Token.validate_base32_secret("JBSWY3DPEHPK3PXP"))
        self.assertTrue(Token.validate_base32_secret("A" * 16))
        self.assertTrue(Token.validate_base32_secret("234567ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    
    def test_validate_base32_secret_invalid(self):
        """Test that invalid base32 secrets fail validation."""
        # Invalid secrets (too short)
        self.assertFalse(Token.validate_base32_secret("ABC"))
        
        # Invalid characters
        self.assertFalse(Token.validate_base32_secret("JBSWY3DPEHPK3PXP1"))  # Contains '1'
        self.assertFalse(Token.validate_base32_secret("JBSWY3DPEHPK3PXP!"))  # Contains '!'
        self.assertFalse(Token.validate_base32_secret("jbswy3dpehpk3pxp"))  # Lowercase letters

if __name__ == "__main__":
    unittest.main() 
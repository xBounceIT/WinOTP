import re
import pyotp
from datetime import datetime

class Token:
    def __init__(self, issuer, secret, name):
        self.issuer = issuer
        self.secret = secret
        self.name = name
        self.totp = pyotp.TOTP(self.secret)
    
    def get_code(self):
        """Generate the current TOTP code"""
        return self.totp.now()
    
    def get_time_remaining(self):
        """Calculate the time remaining until the next code refresh"""
        return int(self.totp.interval - datetime.now().timestamp() % self.totp.interval)
    
    @staticmethod
    def validate_base32_secret(secret):
        """Validate if the provided string is a valid base32 secret"""
        # Base32 alphabet: A-Z and 2-7
        
        # Remove any padding characters
        secret = secret.rstrip("=")
        
        # Check if the string only contains valid base32 characters
        if not re.match(r'^[A-Z2-7]+$', secret):
            return False
            
        # Base32 encoded data should have a length that's a multiple of 8
        # But for TOTP secrets, we're slightly more lenient
        return len(secret) >= 16  # Most TOTP secrets are at least 16 chars 
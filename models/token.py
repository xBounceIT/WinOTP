import re
import pyotp
from datetime import datetime
from utils.ntp_sync import get_accurate_time

# Cache for TOTP objects
_totp_cache = {}

class Token:
    def __init__(self, issuer, secret, name):
        self.issuer = issuer
        self.secret = secret
        self.name = name
        
        # Use cached TOTP object if available
        cache_key = self.secret
        if cache_key in _totp_cache:
            self.totp = _totp_cache[cache_key]
        else:
            self.totp = pyotp.TOTP(self.secret)
            _totp_cache[cache_key] = self.totp
    
    def get_code(self):
        """Generate the current TOTP code using NTP-synchronized time"""
        # Use the accurate time from NTP synchronization
        return self.totp.at(get_accurate_time())
    
    def get_time_remaining(self):
        """Calculate the time remaining until the next code refresh using NTP-synchronized time"""
        return int(self.totp.interval - get_accurate_time() % self.totp.interval)
    
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
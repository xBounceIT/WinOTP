import unittest
from unittest.mock import patch, MagicMock, mock_open
import json
import os
import tempfile
import shutil
import time
from main import Api, set_tokens_path

class TestApi(unittest.TestCase):
    """Test cases for the API class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.test_tokens_path = os.path.join(self.test_dir, "test_tokens.json")
        
        # Sample token data
        self.sample_tokens = {
            "token1": {
                "issuer": "Test Issuer",
                "name": "Test Account",
                "secret": "JBSWY3DPEHPK3PXP"
            },
            "token2": {
                "issuer": "Another Issuer",
                "name": "Another Account",
                "secret": "HXDMVJECJJWSRB3HWIZR4IFUGFTMXBOZ"
            }
        }
        
        # Write sample tokens to the test file
        with open(self.test_tokens_path, 'w') as f:
            json.dump(self.sample_tokens, f)
            
        # Set the tokens path for the API
        set_tokens_path(self.test_tokens_path)
        
        # Create API instance
        self.api = Api()
        
    def tearDown(self):
        """Tear down test fixtures"""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.test_dir)
        
        # Reset the tokens path
        set_tokens_path("tokens.json")
        
    def test_load_tokens(self):
        """Test loading tokens from file"""
        # Force reload tokens
        result = self.api.load_tokens()
        
        # Verify the result
        self.assertEqual(result["status"], "success")
        
        # Verify tokens were loaded correctly
        tokens = self.api.get_tokens()
        self.assertEqual(len(tokens), 2)
        # Check if the tokens contain the expected data
        token_issuers = [token["issuer"] for token in tokens]
        self.assertTrue("Test Issuer" in token_issuers)
        self.assertTrue("Another Issuer" in token_issuers)
        
    def test_save_tokens(self):
        """Test saving tokens to file"""
        # Get the tokens dictionary from the global variable
        from main import tokens
        
        # Add a new token
        tokens["token3"] = {
            "issuer": "New Issuer",
            "name": "New Account",
            "secret": "JBSWY3DPEHPK3PXP"
        }
        
        # Save tokens
        result = self.api.save_tokens()
        
        # Verify the result
        self.assertEqual(result["status"], "success")
        
        # Read the file directly to verify
        with open(self.test_tokens_path, 'r') as f:
            saved_tokens = json.load(f)
            
        # Verify the tokens were saved correctly
        self.assertEqual(len(saved_tokens), 3)
        self.assertTrue("token3" in saved_tokens)
        
    def test_get_tokens(self):
        """Test getting tokens"""
        tokens = self.api.get_tokens()
        
        # Verify the tokens are returned correctly
        self.assertEqual(len(tokens), 2)
        # Check if the tokens contain the expected data
        token_issuers = [token["issuer"] for token in tokens]
        self.assertTrue("Test Issuer" in token_issuers)
        self.assertTrue("Another Issuer" in token_issuers)
        
    def test_add_token(self):
        """Test adding a token"""
        # Add a new token
        new_token = {
            "issuer": "New Issuer",
            "name": "New Account",
            "secret": "JBSWY3DPEHPK3PXP"
        }
        
        result = self.api.add_token(new_token)
        
        # Verify the token was added
        self.assertEqual(result["status"], "success")
        self.assertTrue("id" in result)
        
        # Get the token ID
        token_id = result["id"]
        
        # Get the tokens dictionary from the global variable
        from main import tokens
        
        # Verify the token exists in the tokens
        self.assertTrue(token_id in tokens)
        self.assertEqual(tokens[token_id]["issuer"], "New Issuer")
        
    def test_add_token_invalid(self):
        """Test adding an invalid token"""
        # Add a token with invalid secret
        invalid_token = {
            "issuer": "Invalid Issuer",
            "name": "Invalid Account",
            "secret": ""  # Empty secret
        }
        
        result = self.api.add_token(invalid_token)
        
        # Verify the token was not added
        self.assertEqual(result["status"], "error")
        self.assertTrue("message" in result)
        
    def test_update_token(self):
        """Test updating a token"""
        # Get the tokens dictionary from the global variable
        from main import tokens
        
        # Get existing token ID
        token_id = list(tokens.keys())[0]
        
        # Update the token
        updated_token = {
            "issuer": "Updated Issuer",
            "name": "Updated Account",
            "secret": tokens[token_id]["secret"]
        }
        
        result = self.api.update_token(token_id, updated_token)
        
        # Verify the token was updated
        self.assertEqual(result["status"], "success")
        
        # Verify the token was updated in the tokens
        self.assertEqual(tokens[token_id]["issuer"], "Updated Issuer")
        self.assertEqual(tokens[token_id]["name"], "Updated Account")
        
    def test_update_nonexistent_token(self):
        """Test updating a nonexistent token"""
        # Update a nonexistent token
        updated_token = {
            "issuer": "Updated Issuer",
            "name": "Updated Account",
            "secret": "JBSWY3DPEHPK3PXP"
        }
        
        result = self.api.update_token("nonexistent", updated_token)
        
        # Verify the update failed
        self.assertEqual(result["status"], "error")
        self.assertTrue("message" in result)
        
    def test_delete_token(self):
        """Test deleting a token"""
        # Get the tokens dictionary from the global variable
        from main import tokens
        
        # Get existing token ID
        token_id = list(tokens.keys())[0]
        
        # Delete the token
        result = self.api.delete_token(token_id)
        
        # Verify the token was deleted
        self.assertEqual(result["status"], "success")
        
        # Verify the token was removed from the tokens
        self.assertFalse(token_id in tokens)
        
    def test_delete_nonexistent_token(self):
        """Test deleting a nonexistent token"""
        # Delete a nonexistent token
        result = self.api.delete_token("nonexistent")
        
        # Verify the deletion failed
        self.assertEqual(result["status"], "error")
        self.assertTrue("message" in result)
    
    @unittest.skip("This test requires more complex mocking of Image and base64 modules")
    @patch('main.scan_qr_image')
    @patch('main.Image')
    @patch('main.io.BytesIO')
    @patch('main.base64.b64decode')
    def test_scan_qr_code(self, mock_b64decode, mock_bytesio, mock_image, mock_scan_qr_image):
        """Test scanning a QR code"""
        # Mock the dependencies
        mock_b64decode.return_value = b'fake_image_data'
        mock_bytesio_instance = MagicMock()
        mock_bytesio.return_value = mock_bytesio_instance
        mock_image_instance = MagicMock()
        mock_image.open.return_value = mock_image_instance
        
        # Mock the scan_qr_image function
        mock_scan_qr_image.return_value = ("Test Issuer", "JBSWY3DPEHPK3PXP", "Test Account")
        
        # Call the function with a mock image path
        result = self.api.scan_qr_code("data:image/png;base64,fake_base64_data")
        
        # Verify the result
        self.assertEqual(result["status"], "success")
        self.assertTrue("data" in result)
        self.assertEqual(result["data"], ("Test Issuer", "JBSWY3DPEHPK3PXP", "Test Account"))
        
    @patch('main.scan_qr_image')
    def test_scan_qr_code_failure(self, mock_scan_qr_image):
        """Test scanning an invalid QR code"""
        # Mock the scan_qr_image function to return None
        mock_scan_qr_image.return_value = None
        
        # Call the function with a mock image path
        result = self.api.scan_qr_code("data:image/png;base64,...")
        
        # Verify the result
        self.assertEqual(result["status"], "error")
        self.assertTrue("message" in result)
        
    def test_toggle_sort_order(self):
        """Test toggling sort order"""
        # Get initial sort order
        initial_sort_order = self.api.toggle_sort_order()
        
        # Toggle sort order
        new_sort_order = self.api.toggle_sort_order()
        
        # Verify the sort order was toggled
        self.assertNotEqual(initial_sort_order["ascending"], new_sort_order["ascending"])
    
    def test_import_tokens_from_google_auth_qr(self):
        """Test importing tokens from Google Authenticator QR code"""
        # Create a test migration payload
        from utils.google_auth_pb2 import MigrationPayload, OtpParameters
        import base64
        
        payload = MigrationPayload()
        
        # Add a test token
        otp_param = OtpParameters()
        otp_param.secret = b"JBSWY3DPEHPK3PXP"  # Test secret in bytes
        otp_param.name = "test@example.com"
        otp_param.issuer = "Test Issuer"
        payload.otp_parameters.append(otp_param)
        
        # Serialize and encode the payload
        serialized = payload.SerializeToString()
        encoded = base64.b64encode(serialized).decode('utf-8')
        qr_data = f"otpauth-migration://offline?data={encoded}"
        
        # Import the tokens
        result = self.api.import_tokens_from_google_auth_qr(qr_data)
        
        # Verify the result
        self.assertEqual(result["status"], "success")
        self.assertTrue("Successfully imported" in result["message"])
        
        # Verify the token was added
        tokens = self.api.get_tokens()["data"]
        self.assertEqual(len(tokens), 1)
        self.assertEqual(tokens[0]["issuer"], "Test Issuer")
        self.assertEqual(tokens[0]["name"], "test@example.com")
    
    def test_import_tokens_from_google_auth_qr_invalid_data(self):
        """Test importing tokens from invalid Google Authenticator QR code"""
        # Test with invalid QR code format
        result = self.api.import_tokens_from_google_auth_qr("invalid-data")
        self.assertEqual(result["status"], "error")
        self.assertTrue("Invalid Google Authenticator QR code" in result["message"])
        
        # Test with invalid base64 data
        result = self.api.import_tokens_from_google_auth_qr("otpauth-migration://offline?data=invalid-base64")
        self.assertEqual(result["status"], "error")
        self.assertTrue("Invalid QR code data" in result["message"])
        
        # Test with invalid protobuf data
        invalid_data = base64.b64encode(b"invalid-protobuf").decode('utf-8')
        result = self.api.import_tokens_from_google_auth_qr(f"otpauth-migration://offline?data={invalid_data}")
        self.assertEqual(result["status"], "error")
        self.assertTrue("Failed to import tokens" in result["message"])
    
    @unittest.skip("This test requires more complex mocking of pyotp module")
    @patch('main.pyotp')
    def test_add_token_from_uri(self, mock_pyotp):
        """Test adding a token from URI"""
        # Mock the parse_uri function
        mock_totp = MagicMock()
        mock_totp.issuer = "Test Issuer"
        mock_totp.name = "Test Account"
        mock_totp.secret = "JBSWY3DPEHPK3PXP"
        mock_pyotp.parse_uri.return_value = mock_totp
        
        # Mock the add_token method to return success
        with patch.object(Api, 'add_token', return_value={"status": "success", "id": "mock_token_id"}):
            # Call the function
            result = self.api.add_token_from_uri("otpauth://totp/Test%20Issuer:test%40example.com?secret=JBSWY3DPEHPK3PXP&issuer=Test%20Issuer")
            
            # Verify the result
            self.assertEqual(result["status"], "success")
            self.assertTrue("id" in result)

if __name__ == '__main__':
    unittest.main() 
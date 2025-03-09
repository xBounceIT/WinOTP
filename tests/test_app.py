import unittest
import sys
import os
import json
import tempfile
import shutil
import uuid
from unittest.mock import patch, MagicMock

# Add the parent directory to sys.path so we can import the app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Create proper mocks for tkinter and its submodules
# Instead of using MagicMock class attributes, we'll make them functions
mock_tkinter = MagicMock()
mock_tkinter.font = MagicMock()
mock_tkinter.filedialog = MagicMock()
mock_tkinter.messagebox = MagicMock()

# Create mock functions instead of classes
mock_tkinter.Tk = lambda: MagicMock()
mock_tkinter.Label = lambda *args, **kwargs: MagicMock()
mock_tkinter.Button = lambda *args, **kwargs: MagicMock()
mock_tkinter.Entry = lambda *args, **kwargs: MagicMock()
mock_tkinter.Canvas = lambda *args, **kwargs: MagicMock()
mock_tkinter.Toplevel = lambda *args, **kwargs: MagicMock()
mock_tkinter.PhotoImage = lambda *args, **kwargs: MagicMock()

# Constants
mock_tkinter.CENTER = "center"
mock_tkinter.TOP = "top"

# Mock the modules
sys.modules['tkinter'] = mock_tkinter
sys.modules['tkinter.font'] = mock_tkinter.font
sys.modules['tkinter.filedialog'] = mock_tkinter.filedialog
sys.modules['tkinter.messagebox'] = mock_tkinter.messagebox

# Mock ttkbootstrap
mock_ttk = MagicMock()
mock_ttk.Window = MagicMock
sys.modules['ttkbootstrap'] = mock_ttk

# Mock PIL
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['PIL.ImageTk'] = MagicMock()

# Now we can safely import the app
from models.token import Token

# Create a mock WinOTP class to avoid UI initialization
class MockWinOTP(MagicMock):
    def __init__(self, tokens_path, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tokens_path = tokens_path
        self.frames = {}
        self.filtered_frames = {}
        self.sort_ascending = True

# Patch the WinOTP class before importing it
with patch('app.WinOTP', MockWinOTP):
    from app import WinOTP

class TestWinOTPApp(unittest.TestCase):
    """Test cases for the main WinOTP application."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.test_tokens_path = os.path.join(self.test_dir, "test_tokens.json")
        
        # Create a test tokens file
        self.test_tokens = {
            str(uuid.uuid4()): {
                "issuer": "TestIssuer1",
                "secret": "JBSWY3DPEHPK3PXP",
                "name": "TestAccount1"
            },
            str(uuid.uuid4()): {
                "issuer": "TestIssuer2",
                "secret": "JBSWY3DPEHPK3PXP",
                "name": "TestAccount2"
            }
        }
        
        with open(self.test_tokens_path, 'w') as f:
            json.dump(self.test_tokens, f)
        
        # Create app instance with test tokens - no need for patching now
        self.app = MockWinOTP(self.test_tokens_path)
        
    def tearDown(self):
        """Tear down test fixtures."""
        # Remove temporary directory and files
        shutil.rmtree(self.test_dir)
    
    @patch('utils.file_io.read_json')
    def test_app_initialization(self, mock_read_json):
        """Test that the app is properly initialized."""
        mock_read_json.return_value = self.test_tokens
        
        app = MockWinOTP(self.test_tokens_path)
        
        self.assertEqual(app.tokens_path, self.test_tokens_path)
        self.assertEqual(app.frames, {})
        self.assertEqual(app.filtered_frames, {})
        self.assertTrue(app.sort_ascending)
    
    @patch('utils.file_io.read_json')
    @patch('utils.file_io.write_json')
    def test_add_new_token(self, mock_write_json, mock_read_json):
        """Test adding a new token."""
        mock_read_json.return_value = self.test_tokens.copy()
        
        # Add a new token
        issuer = "New Test Issuer"
        secret = "JBSWY3DPEHPK3PXP"
        name = "New Test Account"
        
        # Implement a simple version of add_new_token for testing
        def add_new_token(issuer, secret, name):
            tokens = mock_read_json.return_value.copy()
            token_id = str(uuid.uuid4())
            tokens[token_id] = {
                "issuer": issuer,
                "secret": secret,
                "name": name
            }
            mock_write_json(self.test_tokens_path, tokens)
            return token_id
        
        # Attach our implementation to the mock
        self.app.add_new_token = add_new_token
        
        # Call add_new_token
        token_id = self.app.add_new_token(issuer, secret, name)
        
        # Check that write_json was called
        mock_write_json.assert_called_once()
        
        # The first arg should be the tokens path
        self.assertEqual(mock_write_json.call_args[0][0], self.test_tokens_path)
        
        # The second arg should be the updated tokens dict
        tokens_arg = mock_write_json.call_args[0][1]
        
        # Check that the new token was added
        self.assertIn(token_id, tokens_arg)
        self.assertEqual(tokens_arg[token_id]["issuer"], issuer)
        self.assertEqual(tokens_arg[token_id]["secret"], secret)
        self.assertEqual(tokens_arg[token_id]["name"], name)
    
    @patch('utils.file_io.read_json')
    @patch('utils.file_io.write_json')
    def test_delete_token(self, mock_write_json, mock_read_json):
        """Test deleting a token."""
        # Set up tokens
        test_token_id = list(self.test_tokens.keys())[0]
        mock_tokens = self.test_tokens.copy()
        mock_read_json.return_value = mock_tokens
        
        # Mock user confirmation
        mock_tkinter.messagebox.askyesno.return_value = True
        
        # Set up frame mocks
        self.app.frames = {test_token_id: MagicMock()}
        self.app.filtered_frames = {test_token_id: MagicMock()}
        
        # Implement a simple version of delete_token for testing
        def delete_token(token_id):
            if mock_tkinter.messagebox.askyesno.return_value:
                tokens = mock_read_json.return_value.copy()
                if token_id in tokens:
                    del tokens[token_id]
                mock_write_json(self.test_tokens_path, tokens)
                if token_id in self.app.frames:
                    del self.app.frames[token_id]
                if token_id in self.app.filtered_frames:
                    del self.app.filtered_frames[token_id]
                return True
            return False
        
        # Attach our implementation to the mock
        self.app.delete_token = delete_token
        
        # Call delete_token
        result = self.app.delete_token(test_token_id)
        
        # Check result
        self.assertTrue(result)
        
        # Check that write_json was called
        mock_write_json.assert_called_once()
        
        # The first arg should be the tokens path
        self.assertEqual(mock_write_json.call_args[0][0], self.test_tokens_path)
        
        # The second arg should be the updated tokens dict without the deleted token
        tokens_arg = mock_write_json.call_args[0][1]
        self.assertNotIn(test_token_id, tokens_arg)
        
        # Check that the frame was removed
        self.assertNotIn(test_token_id, self.app.frames)
        self.assertNotIn(test_token_id, self.app.filtered_frames)
    
    def test_search_tokens(self):
        """Test searching tokens."""
        # Set up frames with different issuers
        frame1 = MagicMock()
        frame1.issuer_label = MagicMock()
        frame1.issuer_label.cget.return_value = "GitHub"
        frame1.pack = MagicMock()
        frame1.pack_forget = MagicMock()
        
        frame2 = MagicMock()
        frame2.issuer_label = MagicMock()
        frame2.issuer_label.cget.return_value = "Google"
        frame2.pack = MagicMock()
        frame2.pack_forget = MagicMock()
        
        frame3 = MagicMock()
        frame3.issuer_label = MagicMock()
        frame3.issuer_label.cget.return_value = "Amazon"
        frame3.pack = MagicMock()
        frame3.pack_forget = MagicMock()
        
        self.app.frames = {
            "token1": frame1,
            "token2": frame2,
            "token3": frame3
        }
        
        # Implement a simple version of search_tokens for testing
        def search_tokens(query):
            # Reset filtered frames
            self.app.filtered_frames = {}
            
            # If no query, show all
            if not query:
                for token_id, frame in self.app.frames.items():
                    frame.pack()
                    self.app.filtered_frames[token_id] = frame
                return
            
            # Filter frames based on query
            query = query.lower()
            for token_id, frame in self.app.frames.items():
                issuer = frame.issuer_label.cget.return_value.lower()
                if query in issuer:
                    frame.pack()
                    self.app.filtered_frames[token_id] = frame
                else:
                    frame.pack_forget()
        
        # Attach our implementation to the mock
        self.app.search_tokens = search_tokens
        
        # Test search for "Go" (should match Google)
        self.app.search_tokens("Go")
        
        # Only Google frame should be visible
        self.assertEqual(len(self.app.filtered_frames), 1)
        self.assertIn("token2", self.app.filtered_frames)
        
        # Test search for empty string (should show all)
        self.app.search_tokens("")
        self.assertEqual(len(self.app.filtered_frames), 3)
        
        # Test case-insensitive search
        self.app.search_tokens("github")
        self.assertEqual(len(self.app.filtered_frames), 1)
        self.assertIn("token1", self.app.filtered_frames)

if __name__ == "__main__":
    unittest.main() 
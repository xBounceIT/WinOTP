import unittest
import sys
import os
import json
import tempfile
import shutil

# Add the parent directory to sys.path so we can import the app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.file_io import read_json, write_json

class TestFileIO(unittest.TestCase):
    """Test cases for file I/O utilities."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test_tokens.json")
        self.test_data = {
            "token1": {
                "issuer": "TestIssuer1",
                "secret": "TESTSECRET1",
                "name": "TestAccount1"
            },
            "token2": {
                "issuer": "TestIssuer2",
                "secret": "TESTSECRET2",
                "name": "TestAccount2"
            }
        }
    
    def tearDown(self):
        """Tear down test fixtures."""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.test_dir)
    
    def test_write_json(self):
        """Test that data is correctly written to a JSON file."""
        write_json(self.test_file, self.test_data)
        self.assertTrue(os.path.exists(self.test_file))
        
        # Verify the file contains the expected data
        with open(self.test_file, 'r') as f:
            written_data = json.load(f)
        
        self.assertEqual(written_data, self.test_data)
    
    def test_read_json_valid(self):
        """Test that JSON data is correctly read from a file."""
        # First write the test data
        with open(self.test_file, 'w') as f:
            json.dump(self.test_data, f)
        
        # Then read it back
        read_data = read_json(self.test_file)
        
        self.assertEqual(read_data, self.test_data)
    
    def test_read_json_file_not_found(self):
        """Test that read_json returns an empty dict when file is not found."""
        non_existent_file = os.path.join(self.test_dir, "non_existent.json")
        read_data = read_json(non_existent_file)
        
        self.assertEqual(read_data, {})
    
    def test_read_json_invalid(self):
        """Test that read_json returns an empty dict for invalid JSON."""
        # Create a file with invalid JSON
        with open(self.test_file, 'w') as f:
            f.write("{invalid json}")
        
        read_data = read_json(self.test_file)
        
        self.assertEqual(read_data, {})

if __name__ == "__main__":
    unittest.main() 
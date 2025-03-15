import unittest
import os
import json
import tempfile
import shutil
from utils.file_io import read_json, write_json, enable_cache, clear_cache

class TestFileIO(unittest.TestCase):
    """Test cases for file I/O operations"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test.json")
        
        # Sample data for testing
        self.test_data = {
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
        
        # Ensure cache is enabled for testing
        enable_cache(True)
        clear_cache()
        
    def tearDown(self):
        """Tear down test fixtures"""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.test_dir)
        
        # Clear the cache
        clear_cache()
        
    def test_write_json(self):
        """Test writing JSON data to a file"""
        # Write test data to the file
        write_json(self.test_file, self.test_data)
        
        # Verify the file exists
        self.assertTrue(os.path.exists(self.test_file))
        
        # Read the file directly to verify contents
        with open(self.test_file, 'r') as file:
            file_data = json.load(file)
            
        # Verify the data was written correctly
        self.assertEqual(file_data, self.test_data)
        
    def test_read_json(self):
        """Test reading JSON data from a file"""
        # Write test data to the file directly
        with open(self.test_file, 'w') as file:
            json.dump(self.test_data, file)
            
        # Read the data using the function
        read_data = read_json(self.test_file)
        
        # Verify the data was read correctly
        self.assertEqual(read_data, self.test_data)
        
    def test_read_json_nonexistent_file(self):
        """Test reading from a nonexistent file"""
        # Try to read from a file that doesn't exist
        nonexistent_file = os.path.join(self.test_dir, "nonexistent.json")
        read_data = read_json(nonexistent_file)
        
        # Should return an empty dict
        self.assertEqual(read_data, {})
        
    def test_read_json_invalid_json(self):
        """Test reading from a file with invalid JSON"""
        # Create a file with invalid JSON
        with open(self.test_file, 'w') as file:
            file.write("This is not valid JSON")
            
        # Try to read the file
        read_data = read_json(self.test_file)
        
        # Should return an empty dict
        self.assertEqual(read_data, {})
        
    def test_cache_functionality(self):
        """Test that the cache works correctly"""
        # Write test data to the file
        write_json(self.test_file, self.test_data)
        
        # Read the data to cache it
        first_read = read_json(self.test_file)
        
        # Get the file modification time
        original_mtime = os.path.getmtime(self.test_file)
        
        # Modify the file directly (bypassing the write_json function)
        modified_data = {"modified": True}
        with open(self.test_file, 'w') as file:
            json.dump(modified_data, file)
            
        # Ensure the modification time is different
        os.utime(self.test_file, (original_mtime, original_mtime))
            
        # Read again with cache enabled - should get cached data
        second_read = read_json(self.test_file)
        
        # Since we didn't change the modification time, it should use the cache
        self.assertEqual(second_read, self.test_data)
        
        # Now update the modification time
        new_mtime = original_mtime + 10
        os.utime(self.test_file, (new_mtime, new_mtime))
        
        # Read again - should get new data because mtime changed
        third_read = read_json(self.test_file)
        self.assertEqual(third_read, modified_data)
        
        # Disable cache
        enable_cache(False)
        
        # Read again with cache disabled - should get new data
        fourth_read = read_json(self.test_file)
        self.assertEqual(fourth_read, modified_data)
        
        # Re-enable cache for other tests
        enable_cache(True)
        
    def test_clear_cache(self):
        """Test clearing the cache"""
        # Write test data to the file
        write_json(self.test_file, self.test_data)
        
        # Read the data to cache it
        first_read = read_json(self.test_file)
        
        # Modify the file directly
        modified_data = {"modified": True}
        with open(self.test_file, 'w') as file:
            json.dump(modified_data, file)
            
        # Clear the cache
        clear_cache()
        
        # Read again - should get new data even with cache enabled
        second_read = read_json(self.test_file)
        self.assertEqual(second_read, modified_data)

if __name__ == '__main__':
    unittest.main() 
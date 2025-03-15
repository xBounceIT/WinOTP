import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
import shutil
from utils.asset_manager import (
    ensure_directories, download_file, download_assets_background,
    initialize_assets
)

class TestAssetManager(unittest.TestCase):
    """Test cases for asset manager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Save the original working directory
        self.original_cwd = os.getcwd()
        
        # Change to the test directory
        os.chdir(self.test_dir)
        
        # Reset the _assets_initialized flag
        import utils.asset_manager
        utils.asset_manager._assets_initialized = False
        
    def tearDown(self):
        """Tear down test fixtures"""
        # Change back to the original directory
        os.chdir(self.original_cwd)
        
        # Remove the temporary directory and its contents
        shutil.rmtree(self.test_dir)
        
    def test_ensure_directories(self):
        """Test ensuring directories exist"""
        # Call the function
        ensure_directories()
        
        # Verify the directories were created
        self.assertTrue(os.path.exists('static/css'))
        self.assertTrue(os.path.exists('static/js'))
        self.assertTrue(os.path.exists('static/icons'))
        
    @patch('utils.asset_manager.urllib.request.urlretrieve')
    def test_download_file(self, mock_urlretrieve):
        """Test downloading a file"""
        # Ensure the directory exists
        os.makedirs('static/css', exist_ok=True)
        
        # Call the function
        download_file('https://example.com/test.css', 'static/css/test.css')
        
        # Verify the urlretrieve function was called
        mock_urlretrieve.assert_called_once_with('https://example.com/test.css', 'static/css/test.css')
        
    @patch('utils.asset_manager.urllib.request.urlretrieve')
    def test_download_file_existing(self, mock_urlretrieve):
        """Test downloading a file that already exists"""
        # Ensure the directory exists
        os.makedirs('static/css', exist_ok=True)
        
        # Create the file
        with open('static/css/test.css', 'w') as f:
            f.write('/* Test CSS */')
            
        # Call the function
        download_file('https://example.com/test.css', 'static/css/test.css')
        
        # Verify the urlretrieve function was not called
        mock_urlretrieve.assert_not_called()
        
    @patch('utils.asset_manager.urllib.request.urlretrieve')
    def test_download_file_error(self, mock_urlretrieve):
        """Test handling of download errors"""
        # Ensure the directory exists
        os.makedirs('static/css', exist_ok=True)
        
        # Make the urlretrieve function raise an exception
        mock_urlretrieve.side_effect = Exception("Download error")
        
        # Call the function
        download_file('https://example.com/test.css', 'static/css/test.css')
        
        # Verify the urlretrieve function was called
        mock_urlretrieve.assert_called_once_with('https://example.com/test.css', 'static/css/test.css')
        
        # Verify the file doesn't exist
        self.assertFalse(os.path.exists('static/css/test.css'))
        
    @patch('utils.asset_manager.download_file')
    def test_download_assets_background(self, mock_download_file):
        """Test downloading assets in the background"""
        # Call the function
        download_assets_background()
        
        # Verify the download_file function was called for each file
        self.assertEqual(mock_download_file.call_count, 3)
        
    @patch('utils.asset_manager.threading.Thread')
    @patch('utils.asset_manager.os.path.exists')
    def test_initialize_assets(self, mock_exists, mock_thread):
        """Test initializing assets"""
        # Mock the thread
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        # Mock exists to return False for at least one file
        mock_exists.return_value = False
        
        # Call the function
        initialize_assets()
        
        # Verify the thread was started
        mock_thread_instance.start.assert_called_once()
        
        # Call the function again
        initialize_assets()
        
        # Verify the thread was not started again
        self.assertEqual(mock_thread_instance.start.call_count, 1)
        
    @patch('utils.asset_manager.threading.Thread')
    def test_initialize_assets_all_exist(self, mock_thread):
        """Test initializing assets when all files exist"""
        # Create all the necessary directories and files
        ensure_directories()
        
        # Create all the files that would be downloaded
        from utils.asset_manager import files_to_download
        for _, path in files_to_download:
            with open(path, 'w') as f:
                f.write('/* Test file */')
        
        # Call the function
        initialize_assets()
        
        # Verify the thread was not started
        mock_thread.assert_not_called()

if __name__ == '__main__':
    unittest.main() 
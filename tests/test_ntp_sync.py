import unittest
from unittest.mock import patch, MagicMock
import time
from utils.ntp_sync import (
    get_ntp_time, calculate_offset, get_accurate_time,
    get_accurate_timestamp_30s, start_ntp_sync, stop_ntp_sync,
    get_sync_status
)

class TestLocalTimeSync(unittest.TestCase):
    """Test cases for local time synchronization functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Stop any running sync thread to avoid interference
        stop_ntp_sync()
        
    def tearDown(self):
        """Tear down test fixtures"""
        # Stop any running sync thread
        stop_ntp_sync()
        
    def test_get_ntp_time_deprecated(self):
        """Test that get_ntp_time returns local time (deprecated function)"""
        # Call the function
        result = get_ntp_time("test.ntp.server")
        
        # Verify it returns current local time
        current_time = time.time()
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, current_time, delta=1.0)
        
    def test_calculate_offset_local_time(self):
        """Test that calculate_offset returns 0 for local time"""
        # Call the function
        offset = calculate_offset()
        
        # Verify the offset is always 0 for local time
        self.assertEqual(offset, 0.0)
        
    def test_get_accurate_time_local(self):
        """Test getting accurate time using local time"""
        # Call the function multiple times
        time1 = get_accurate_time()
        time.sleep(0.1)
        time2 = get_accurate_time()
        
        # Verify times are increasing and close to system time
        self.assertGreater(time2, time1)
        self.assertAlmostEqual(time1, time.time(), delta=1.0)
        self.assertAlmostEqual(time2, time.time(), delta=1.0)
        
    def test_get_accurate_timestamp_30s_local(self):
        """Test getting accurate timestamp rounded to 30 seconds using local time"""
        # Mock time.time to get predictable results
        with patch('utils.ntp_sync.time.time') as mock_time:
            mock_time.return_value = 1000.0
            
            # Call the function
            timestamp_30s = get_accurate_timestamp_30s()
            
            # Verify the timestamp is rounded to 30 seconds
            # 1000 / 30 = 33.33, floor to 33
            self.assertEqual(timestamp_30s, 33)
            
            # Test with different time
            mock_time.return_value = 1015.0
            timestamp_30s = get_accurate_timestamp_30s()
            # 1015 / 30 = 33.83, floor to 33
            self.assertEqual(timestamp_30s, 33)
            
            mock_time.return_value = 1030.0
            timestamp_30s = get_accurate_timestamp_30s()
            # 1030 / 30 = 34.33, floor to 34
            self.assertEqual(timestamp_30s, 34)
        
    @patch('utils.ntp_sync.threading.Thread')
    def test_start_ntp_sync(self, mock_thread):
        """Test starting local time sync thread"""
        # Mock the thread
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance
        
        # Call the function
        start_ntp_sync()
        
        # Verify the thread was started
        mock_thread_instance.start.assert_called_once()
        
    @patch('utils.ntp_sync._is_running', True)
    def test_stop_ntp_sync(self):
        """Test stopping local time sync thread"""
        # Call the function
        stop_ntp_sync()
        
        # Verify the running flag was set to False
        from utils.ntp_sync import _is_running
        self.assertFalse(_is_running)
        
    def test_get_sync_status_local(self):
        """Test getting sync status for local time"""
        # Initialize the sync first
        start_ntp_sync()
        time.sleep(0.1)  # Let it initialize
        
        # Get status
        status = get_sync_status()
        
        # Verify status contains expected keys
        self.assertIn('offset', status)
        self.assertIn('offset_ms', status)
        self.assertIn('last_sync', status)
        self.assertIn('synced', status)
        self.assertIn('mode', status)
        
        # Verify local time specific values
        self.assertEqual(status['offset'], 0.0)
        self.assertEqual(status['offset_ms'], 0.0)
        self.assertEqual(status['mode'], 'local')
        self.assertTrue(status['synced'])  # Should be synced with local time
        
        # Stop sync
        stop_ntp_sync()
        
    def test_get_accurate_time_initialization(self):
        """Test that get_accurate_time initializes on first call"""
        # Ensure sync is not initialized
        from utils.ntp_sync import _sync_initialized
        original_state = _sync_initialized
        
        # Reset for test
        import utils.ntp_sync
        utils.ntp_sync._sync_initialized = False
        
        try:
            # First call should initialize
            time1 = get_accurate_time()
            
            # Verify initialization happened
            self.assertTrue(utils.ntp_sync._sync_initialized)
            
            # Second call should work normally
            time2 = get_accurate_time()
            self.assertGreater(time2, time1)
        finally:
            # Restore original state
            utils.ntp_sync._sync_initialized = original_state

if __name__ == '__main__':
    unittest.main()

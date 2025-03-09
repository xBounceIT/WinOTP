import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# Add the parent directory to sys.path
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
sys.modules['ttkbootstrap'] = MagicMock()
sys.modules['PIL'] = MagicMock()
sys.modules['PIL.Image'] = MagicMock()
sys.modules['PIL.ImageTk'] = MagicMock()

# A simple UI class to test our mocking approach
class MockUI:
    def __init__(self):
        self.root = mock_tkinter.Tk()
        self.label = mock_tkinter.Label(self.root, text="Test")
        self.button = mock_tkinter.Button(self.root, text="Click")
        
    def show_message(self):
        mock_tkinter.messagebox.showinfo("Title", "Message")
        
    def select_file(self):
        return mock_tkinter.filedialog.askopenfilename()

class TestMockUI(unittest.TestCase):
    """Test cases for validating our UI mocking approach."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.ui = MockUI()
    
    def test_ui_initialization(self):
        """Test that UI elements can be created with mocks."""
        self.assertIsNotNone(self.ui.root)
        self.assertIsNotNone(self.ui.label)
        self.assertIsNotNone(self.ui.button)
    
    def test_messagebox(self):
        """Test that messagebox can be called."""
        self.ui.show_message()
        mock_tkinter.messagebox.showinfo.assert_called_once_with("Title", "Message")
    
    def test_filedialog(self):
        """Test that filedialog can be called."""
        mock_tkinter.filedialog.askopenfilename.return_value = "test.txt"
        result = self.ui.select_file()
        self.assertEqual(result, "test.txt")
        mock_tkinter.filedialog.askopenfilename.assert_called_once()

if __name__ == "__main__":
    unittest.main() 
"""
Screen region selector utility for Windows

This module provides a way for users to select a region of the screen
to capture for QR code scanning.
"""

import tkinter as tk
import logging
import traceback
from screeninfo import get_monitors

class ScreenRegionSelector:
    """Class for selecting a region of the screen"""
    
    def __init__(self):
        self.root = None
        self.canvas = None
        self.selected_region = None
        self.start_x = None
        self.start_y = None
        self.current_rectangle = None
        self.overlay_alpha = 128  # Semi-transparent overlay
        
        # Calculate multi-monitor boundaries
        self.monitors = get_monitors()
        self.full_width = 0
        self.full_height = 0
        self.offset_x = 0
        self.offset_y = 0
        self._calculate_virtual_screen_size()
        
    def _calculate_virtual_screen_size(self):
        """Calculate the full dimensions of the virtual screen across all monitors"""
        if not self.monitors:
            # Fallback to primary screen dimensions if monitor detection fails
            self.full_width = tk.Tk().winfo_screenwidth()
            self.full_height = tk.Tk().winfo_screenheight()
            logging.info(f"Using primary monitor dimensions: {self.full_width}x{self.full_height}")
            return
            
        # Find the leftmost and topmost coordinates (can be negative)
        min_x = min(monitor.x for monitor in self.monitors)
        min_y = min(monitor.y for monitor in self.monitors)
        max_x = max(monitor.x + monitor.width for monitor in self.monitors)
        max_y = max(monitor.y + monitor.height for monitor in self.monitors)
        
        # Calculate full dimensions and offset
        self.full_width = max_x - min_x
        self.full_height = max_y - min_y
        self.offset_x = min_x
        self.offset_y = min_y
        
        logging.info(f"Virtual screen dimensions: {self.full_width}x{self.full_height}")
        logging.info(f"Virtual screen offset: {self.offset_x},{self.offset_y}")
        logging.info(f"Detected monitors: {len(self.monitors)}")
        for i, m in enumerate(self.monitors):
            logging.info(f"Monitor {i+1}: {m.width}x{m.height}+{m.x}+{m.y}")
        
    def get_region(self):
        """
        Prompt the user to select a region of the screen
        
        Returns:
            tuple: (left, top, right, bottom) coordinates of the selected region,
                  or None if selection was cancelled
        """
        try:
            # Create a full-screen transparent window
            self.root = tk.Tk()
            self.root.attributes("-alpha", 0.3)  # Semi-transparent
            
            # Set window to cover the entire virtual screen
            self.root.geometry(f"{self.full_width}x{self.full_height}+{self.offset_x}+{self.offset_y}")
            self.root.attributes("-fullscreen", True)
            self.root.attributes("-topmost", True)  # Keep on top
            
            # Set window title and hint text
            self.root.title("Select QR Code Region")
            
            # Create canvas for drawing selection rectangle
            self.canvas = tk.Canvas(self.root, cursor="crosshair")
            self.canvas.pack(fill=tk.BOTH, expand=True)
            
            # Add instructions text
            self.canvas.create_text(
                self.full_width // 2,
                50,
                text="Click and drag to select the region with the QR code\nPress ESC to cancel",
                fill="white",
                font=("Arial", 16, "bold")
            )
            
            # Bind events
            self.canvas.bind("<ButtonPress-1>", self._on_press)
            self.canvas.bind("<B1-Motion>", self._on_drag)
            self.canvas.bind("<ButtonRelease-1>", self._on_release)
            self.root.bind("<Escape>", self._on_cancel)
            
            # Start the main loop
            self.root.mainloop()
            
            # Apply the offset to coordinates if we have a selection
            if self.selected_region:
                left, top, right, bottom = self.selected_region
                # Adjust coordinates to account for the virtual screen offset
                real_left = left + self.offset_x
                real_top = top + self.offset_y
                real_right = right + self.offset_x
                real_bottom = bottom + self.offset_y
                return (real_left, real_top, real_right, real_bottom)
            
            return None
        
        except Exception as e:
            logging.error(f"Error in screen region selector: {e}")
            logging.error(traceback.format_exc())
            if self.root:
                self.root.destroy()
            return None
    
    def _on_press(self, event):
        """Handle mouse press event"""
        self.start_x = event.x
        self.start_y = event.y
        
        # Create a new rectangle if it doesn't exist
        if self.current_rectangle:
            self.canvas.delete(self.current_rectangle)
        
        self.current_rectangle = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline="red", width=2
        )
    
    def _on_drag(self, event):
        """Handle mouse drag event"""
        if self.current_rectangle:
            # Update the rectangle as the mouse is dragged
            self.canvas.coords(
                self.current_rectangle,
                self.start_x, self.start_y, event.x, event.y
            )
    
    def _on_release(self, event):
        """Handle mouse release event"""
        if self.start_x is None or self.start_y is None:
            return
            
        end_x, end_y = event.x, event.y
        
        # Ensure coordinates are ordered properly (left, top, right, bottom)
        left = min(self.start_x, end_x)
        top = min(self.start_y, end_y)
        right = max(self.start_x, end_x)
        bottom = max(self.start_y, end_y)
        
        # Store the selected region (without offsets - those are applied in get_region)
        self.selected_region = (left, top, right, bottom)
        
        # Close the window
        self.root.destroy()
    
    def _on_cancel(self, event):
        """Handle cancel event (ESC key)"""
        self.selected_region = None
        self.root.destroy()

def select_screen_region():
    """
    Prompt the user to select a region of the screen
    
    Returns:
        dict: A dictionary containing the result of the selection
    """
    try:
        selector = ScreenRegionSelector()
        region = selector.get_region()
        
        if region:
            return {
                "status": "success",
                "message": "Region selected successfully",
                "region": region
            }
        else:
            return {
                "status": "cancelled",
                "message": "Region selection was cancelled"
            }
    except Exception as e:
        logging.error(f"Error selecting screen region: {e}")
        logging.error(traceback.format_exc())
        return {
            "status": "error",
            "message": f"Failed to select screen region: {str(e)}"
        } 
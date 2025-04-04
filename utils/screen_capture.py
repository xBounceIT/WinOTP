"""
Screen capture utility for Windows

This module provides functionality to capture a region of the screen
and process it for QR code scanning.
"""

import io
import logging
from PIL import Image, ImageGrab
from datetime import datetime
import traceback

def capture_screen_region(region=None):
    """
    Capture a region of the screen or prompt user to select a region.
    
    Args:
        region (tuple, optional): Region to capture (left, top, right, bottom).
                                 If None, the entire screen is captured.
    
    Returns:
        dict: A dictionary containing the status and captured image data
    """
    try:
        logging.info(f"Capturing screen region: {region}")
        
        # Capture the specified region or full screen
        try:
            # For multi-monitor setups, ImageGrab.grab can take bbox coordinates
            # that span across different monitors
            screenshot = ImageGrab.grab(bbox=region, all_screens=True)
            
            # Log capture details
            if region:
                width = region[2] - region[0]
                height = region[3] - region[1]
                logging.info(f"Captured region: {width}x{height} at position {region[0]},{region[1]}")
            else:
                logging.info(f"Captured full screen: {screenshot.width}x{screenshot.height}")
        except TypeError as e:
            # Handle the case where all_screens parameter is not supported (older Pillow versions)
            logging.warning(f"Multi-monitor parameter not supported: {e}")
            logging.warning("Attempting capture without all_screens parameter")
            screenshot = ImageGrab.grab(bbox=region)
        
        # Convert to bytes for processing
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        # Generate a timestamp for logging
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return {
            "status": "success",
            "message": "Screen region captured successfully",
            "image": screenshot,
            "timestamp": timestamp
        }
    except Exception as e:
        logging.error(f"Error capturing screen region: {e}")
        logging.error(traceback.format_exc())
        return {
            "status": "error",
            "message": f"Failed to capture screen region: {str(e)}"
        }

def process_captured_image(image):
    """
    Process a captured image for QR code scanning
    
    Args:
        image: PIL Image object of the screen capture
        
    Returns:
        dict: A dictionary containing the processed image
    """
    try:
        # Apply basic image enhancements to improve QR code detection
        # Convert to grayscale
        image_processed = image.convert('L')
        
        # Log processing details
        logging.info(f"Processed image dimensions: {image_processed.width}x{image_processed.height}")
        
        return {
            "status": "success",
            "message": "Image processed successfully",
            "image": image_processed
        }
    except Exception as e:
        logging.error(f"Error processing captured image: {e}")
        logging.error(traceback.format_exc())
        return {
            "status": "error",
            "message": f"Failed to process image: {str(e)}"
        } 
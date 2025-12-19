"""
Screen capture utility for Windows

This module provides functionality to capture a region of the screen
and process it for QR code scanning.
"""

import io
import logging
import traceback
from datetime import datetime
from PIL import Image, ImageGrab, ImageOps, ImageEnhance, ImageFilter

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
        # Apply a series of enhancements to improve QR code detection reliability.
        image_processed = image.convert('L')  # grayscale gives pyzbar stable input
        image_processed = ImageOps.autocontrast(image_processed)
        image_processed = ImageEnhance.Contrast(image_processed).enhance(1.8)
        image_processed = ImageEnhance.Sharpness(image_processed).enhance(2.0)
        image_processed = image_processed.filter(ImageFilter.UnsharpMask(radius=1, percent=150))

        # Upscale small captures so the QR modules remain legible after preprocessing.
        min_dimension = min(image_processed.width, image_processed.height)
        if min_dimension < 320:
            scale_factor = max(2, int(320 / min_dimension))
            new_size = (
                image_processed.width * scale_factor,
                image_processed.height * scale_factor
            )
            image_processed = image_processed.resize(new_size, Image.LANCZOS)
            logging.info(
                "Upscaled processed image to %sx%s using factor %s",
                image_processed.width,
                image_processed.height,
                scale_factor
            )

        logging.info(
            "Processed image dimensions: %sx%s (original %sx%s)",
            image_processed.width,
            image_processed.height,
            image.width,
            image.height
        )

        return {
            "status": "success",
            "message": "Image processed successfully",
            "image": image_processed,
            "original": image
        }
    except Exception as e:
        logging.error(f"Error processing captured image: {e}")
        logging.error(traceback.format_exc())
        return {
            "status": "error",
            "message": f"Failed to process image: {str(e)}"
        } 

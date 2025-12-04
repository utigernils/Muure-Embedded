import os
import logging
import time
from PIL import Image
from waveshare_epd import epd7in5_V2

class EInkDisplay:
    def __init__(self):
        self.epd = epd7in5_V2.EPD()
        self.logger = logging.getLogger(__name__)

    def init_display(self):
        """Initialize and clear the display."""
        try:
            self.logger.info("Initializing and clearing display")
            self.epd.init()
            self.epd.Clear()
        except Exception as e:
            self.logger.error(f"Failed to initialize display: {e}")
            raise

    def display_image(self, image_path: str):
        """Display a 4-gray image on the screen."""
        if not os.path.exists(image_path):
            self.logger.error(f"Image file not found: {image_path}")
            return

        try:
            self.logger.info("Initializing 4Gray display mode")
            self.epd.init_4Gray()
            
            self.logger.info(f"Loading image from {image_path}")
            image = Image.open(image_path)
            
            self.logger.info("Displaying image")
            self.epd.display_4Gray(self.epd.getbuffer_4Gray(image))
        except Exception as e:
            self.logger.error(f"Failed to display image: {e}")
            raise

    def sleep(self):
        """Put the display to sleep."""
        try:
            self.logger.info("Display going to sleep...")
            self.epd.sleep()
        except Exception as e:
            self.logger.error(f"Failed to sleep display: {e}")

    def clear(self):
        """Clear the display."""
        try:
            self.logger.info("Clearing display...")
            self.epd.init()
            self.epd.Clear()
        except Exception as e:
            self.logger.error(f"Failed to clear display: {e}")

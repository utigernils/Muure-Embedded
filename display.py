import os
import logging
import time
from config import Config
from PIL import Image

config = Config()

if config.get("DISPLAY_ENVIRONMENT") == "development":
    from waveshare_epd import emulator
else:
    from waveshare_epd import epd7in5_V2

class EInkDisplay:
    def __init__(self):
        if config.get("DISPLAY_ENVIRONMENT") == "development":
            self.epd = emulator.EPD()
        else:
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

    def update(self, bmp_path):
        """Full update using 4-gray mode.
        - Clears first
        - Displays the provided image in 4-gray mode
        - Puts display to sleep when done
        """
        if not os.path.exists(bmp_path):
            self.logger.error(f"Image file not found: {bmp_path}")
            return

        try:
            # Clear display first as requested
            self.logger.info("Clearing then initializing 4Gray display mode")
            self.epd.init()
            self.epd.Clear()
            self.epd.init_4Gray()

            # Load and fit to panel
            self.logger.info(f"Loading image from {bmp_path}")
            image = Image.open(bmp_path)
            target_size = (getattr(self.epd, 'width', image.width), getattr(self.epd, 'height', image.height))
            if image.size == target_size:
                fitted = image
            elif image.size == (target_size[1], target_size[0]):
                fitted = image.rotate(90, expand=True)
            else:
                self.logger.info(f"Resizing image from {image.size} to {target_size}")
                fitted = image.resize(target_size)

            self.logger.info("Displaying 4Gray image")
            self.epd.display_4Gray(self.epd.getbuffer_4Gray(fitted))
        except Exception as e:
            self.logger.error(f"Failed to perform full update: {e}")
            raise
        finally:
            try:
                self.sleep()
            except Exception:
                pass
    
    def partial_update(self, bmp_path, regions):
        """Partial update using panel partial mode.
        - Uses regions from ImageDifference (x, y, w, h) in pixels
        - Thresholds to 1-bit since partial refresh is monochrome
        - Puts display to sleep when done
        """
        if not os.path.exists(bmp_path):
            self.logger.error(f"Image file not found: {bmp_path}")
            return

        if not regions:
            self.logger.info("No regions provided for partial update; skipping")
            return

        try:
            # Initialize partial mode
            self.logger.info("Initializing partial update mode")
            self.epd.init_part()

            # Load source image once
            src = Image.open(bmp_path)
            # Ensure orientation matches panel
            panel_w = getattr(self.epd, 'width', src.width)
            panel_h = getattr(self.epd, 'height', src.height)
            if src.size == (panel_w, panel_h):
                base = src
            elif src.size == (panel_h, panel_w):
                base = src.rotate(90, expand=True)
            else:
                self.logger.info(f"Resizing image from {src.size} to {(panel_w, panel_h)} for partials")
                base = src.resize((panel_w, panel_h))

            # Convert once to grayscale for thresholding per region
            base_gray = base.convert("L")

            def align_to_bytes(x0, x1):
                ax0 = (x0 // 8) * 8
                ax1 = ((x1 + 7) // 8) * 8
                return ax0, ax1

            for idx, region in enumerate(regions, start=1):
                if not isinstance(region, tuple) or len(region) != 4:
                    self.logger.warning(f"Skipping invalid region #{idx}: {region}")
                    continue
                x, y, w, h = region
                if w <= 0 or h <= 0:
                    continue

                # Clamp to panel bounds
                x0 = max(0, min(x, panel_w))
                y0 = max(0, min(y, panel_h))
                x1 = max(0, min(x + w, panel_w))
                y1 = max(0, min(y + h, panel_h))
                if x0 >= x1 or y0 >= y1:
                    continue

                # Align to 8-pixel boundary horizontally as required by the driver
                ax0, ax1 = align_to_bytes(x0, x1)
                if ax0 >= ax1:
                    continue

                crop = base_gray.crop((ax0, y0, ax1, y1))
                bw = crop.point(lambda p: 255 if p > 127 else 0, mode="1")

                # Ensure width is byte-aligned so raw bytes are contiguous
                region_w_bytes = (ax1 - ax0) // 8
                region_h = (y1 - y0)
                raw = bytearray(bw.tobytes('raw'))
                # Invert bits to match e-paper expectations (0=white,1=black)
                for i in range(len(raw)):
                    raw[i] ^= 0xFF

                self.logger.info(
                    f"Partial region #{idx}: x={ax0}, y={y0}, w={ax1-ax0}, h={region_h}, bytes={region_w_bytes*region_h}"
                )

                # Call driver partial update; handle emulator signature differences
                try:
                    self.epd.display_Partial(raw, ax0, y0, ax1, y1)
                except TypeError:
                    # Emulator fallback (no coords supported)
                    self.epd.display_Partial(raw)

        except Exception as e:
            self.logger.error(f"Failed partial update: {e}")
            raise
        finally:
            try:
                self.sleep()
            except Exception:
                pass

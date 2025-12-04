import logging
from PIL import Image

class FourToneConverter:
    LEVELS = [255, 192, 128, 0]

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def convert(self, input_path: str, output_path: str):
        try:
            self.logger.info(f"Converting {input_path} to 4-tone BMP")
            img = Image.open(input_path).convert("L")

            pixels = img.load()
            width, height = img.size

            for y in range(height):
                for x in range(width):
                    original = pixels[x, y]

                    if original > 190:
                        tone = 255
                    elif original > 128:
                        tone = 192
                    elif original > 64:
                        tone = 128
                    else:
                        tone = 0

                    pixels[x, y] = tone

            if not output_path.lower().endswith(".bmp"):
                output_path += ".bmp"

            img.save(output_path, format="BMP")
            self.logger.info(f"Image saved to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to convert image: {e}")
            raise

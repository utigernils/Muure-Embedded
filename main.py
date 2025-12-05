import asyncio
import logging
import os
import sys
from config import Config
from render import Renderer
from convert import FourToneConverter
from display import EInkDisplay

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("Main")

async def main():
    config = Config()
    renderer = Renderer()
    converter = FourToneConverter()
    display = EInkDisplay()

    if config.get("DISPLAY_ENVIRONMENT") == "development":
        logger.info("The display is being emulated in development mode.")

    # Ensure directories exist
    os.makedirs("renders", exist_ok=True)

    png_path = os.path.abspath("renders/output.png")
    bmp_path = os.path.abspath("renders/output.bmp")

    # Initial clear
    display.init_display()

    try:
        while True:
            logger.info("Starting display cycle...")
            
            # 1. Render
            logger.info("Step 1: Rendering page...")
            try:
                await renderer.render_to_png(png_path)
            except Exception as e:
                logger.error(f"Rendering failed: {e}")
                await asyncio.sleep(10)
                continue
            
            # 2. Convert
            logger.info("Step 2: Converting image...")
            try:
                converter.convert(png_path, bmp_path)
            except Exception as e:
                logger.error(f"Conversion failed: {e}")
                await asyncio.sleep(10)
                continue
            
            # 3. Display
            logger.info("Step 3: Displaying image...")
            try:
                display.display_image(bmp_path)
                display.sleep()
            except Exception as e:
                logger.error(f"Display failed: {e}")
            
            logger.info("Cycle complete. Waiting for 60 seconds...")
            await asyncio.sleep(60)

    except KeyboardInterrupt:
        logger.info("Exiting...")
        display.clear()
        display.sleep()
    except Exception as e:
        logger.error(f"An unhandled error occurred: {e}")
        display.sleep()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

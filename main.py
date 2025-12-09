import asyncio
import logging
import os
import sys
import threading
from config import Config
from render import Renderer
from convert import FourToneConverter
from display import EInkDisplay
from buttons import ButtonHandler
from leds import LEDController

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("Main")

class DisplayManager:
    """Manages the display cycle with button interrupt capability."""
    
    def __init__(self):
        self.config = Config()
        self.renderer = Renderer()
        self.converter = FourToneConverter()
        self.display = EInkDisplay()
        self.led_controller = LEDController(self.config)
        
        # Event to signal immediate refresh
        self.refresh_event = asyncio.Event()
        self.refresh_lock = asyncio.Lock()
        self.loop = None  # Will store the asyncio loop reference
        
        # Button handler with refresh callback
        self.button_handler = ButtonHandler(refresh_callback=self.trigger_refresh)
        
        # Paths
        self.png_path = os.path.abspath("renders/output.png")
        self.bmp_path = os.path.abspath("renders/output.bmp")
    
    def trigger_refresh(self):
        """Callback function for button handler to trigger immediate refresh."""
        logger.info("Button press detected - triggering immediate display refresh")
        # Use call_soon_threadsafe since this is called from button thread
        if self.loop and not self.loop.is_closed():
            self.loop.call_soon_threadsafe(self.refresh_event.set)
        else:
            logger.error("Cannot trigger refresh - asyncio loop not available")
    
    async def perform_display_cycle(self):
        """Perform one complete display cycle (render, convert, display)."""
        async with self.refresh_lock:
            logger.info("Starting display cycle...")
            
            # Start loading animation
            self.led_controller.loading()
            
            try:
                # 1. Render
                logger.info("Step 1: Rendering page...")
                try:
                    await self.renderer.render_to_png(self.png_path)
                except Exception as e:
                    logger.error(f"Rendering failed: {e}")
                    self.led_controller.fault()
                    raise
                
                # 2. Convert
                logger.info("Step 2: Converting image...")
                try:
                    self.converter.convert(self.png_path, self.bmp_path)
                except Exception as e:
                    logger.error(f"Conversion failed: {e}")
                    self.led_controller.fault()
                    raise
                
                # 3. Display
                logger.info("Step 3: Displaying image...")
                try:
                    self.display.display_image(self.bmp_path)
                    self.display.sleep()
                except Exception as e:
                    logger.error(f"Display failed: {e}")
                    self.led_controller.fault()
                    raise
                
                logger.info("Display cycle complete")
                # Show success animation
                self.led_controller.success()
                
            except Exception:
                # Keep the fault animation running and re-raise
                raise
    
    async def wait_with_interrupt(self, duration: int):
        """Wait for specified duration or until refresh event is triggered."""
        logger.info(f"Waiting for {duration} seconds (or until button press)...")
        
        try:
            await asyncio.wait_for(self.refresh_event.wait(), timeout=duration)
            logger.info("Wait interrupted by button press")
        except asyncio.TimeoutError:
            logger.info("Wait completed normally")
        finally:
            # Clear the event for next cycle
            self.refresh_event.clear()
    
    async def run(self):
        """Main display loop with button interrupt support."""
        # Store the asyncio loop reference for thread-safe event setting
        self.loop = asyncio.get_running_loop()
        
        if self.config.get("DISPLAY_ENVIRONMENT") == "development":
            logger.info("The display is being emulated in development mode.")

        # Ensure directories exist
        os.makedirs("renders", exist_ok=True)

        # Initial clear
        self.display.init_display()

        # Start button handler
        self.button_handler.start()

        try:
            while True:
                # Perform display cycle
                try:
                    await self.perform_display_cycle()
                except Exception as e:
                    logger.error(f"Display cycle failed: {e}")
                    # Fault animation is already triggered in perform_display_cycle
                    # Wait before retrying
                    await asyncio.sleep(10)
                    continue
                
                # Wait for next cycle or button interrupt
                refresh_interval = int(self.config.get("DISPLAY_REFRESH_INTERVAL", 60))
                await self.wait_with_interrupt(refresh_interval)

        except KeyboardInterrupt:
            logger.info("Exiting...")
        except Exception as e:
            logger.error(f"An unhandled error occurred: {e}")
        finally:
            # Cleanup
            self.button_handler.stop()
            try:
                self.display.clear()
                self.display.sleep()
            except:
                pass
            # Turn off LEDs and cleanup
            try:
                self.led_controller.cleanup()
            except:
                pass

async def main():
    display_manager = DisplayManager()
    await display_manager.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass

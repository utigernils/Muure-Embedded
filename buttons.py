import asyncio
import logging
import threading
import time
from typing import Callable, Optional
import aiohttp
from config import Config

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

logger = logging.getLogger(__name__)

class ButtonHandler:
    """
    Handles button presses for the e-ink display.
    
    Supports both hardware GPIO buttons (on Raspberry Pi) and keyboard simulation
    for development environment.
    """
    
    def __init__(self, refresh_callback: Optional[Callable] = None):
        self.config = Config()
        self.refresh_callback = refresh_callback
        self.running = False
        self.thread = None
        
        # Button GPIO pins (adjust these based on your hardware setup)
        self.BUTTON_LEFT_PIN = int(self.config.get("BUTTON_LEFT_PIN", "3"))
        self.BUTTON_RIGHT_PIN = int(self.config.get("BUTTON_RIGHT_PIN", "4"))
        
        # API endpoints
        self.API_BASE = self.config.get("MUURE_SERVER", "http://localhost:8000")
        self.LEFT_WIDGET_ENDPOINT = f"{self.API_BASE}api/widgets/left/next"
        self.RIGHT_WIDGET_ENDPOINT = f"{self.API_BASE}api/widgets/right/next"
        
        # Debounce settings
        self.DEBOUNCE_TIME = float(self.config.get("BUTTON_DEBOUNCE_TIME", "0.2"))
        self.last_press_time = {"left": 0, "right": 0}
        
        self._setup_buttons()
    
    def _setup_buttons(self):
        """Setup button GPIO or keyboard input based on environment."""
        if self.config.get("DISPLAY_ENVIRONMENT") == "development":
            logger.info("Button handler initialized for development (keyboard input)")
        elif GPIO_AVAILABLE:
            try:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.BUTTON_LEFT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                GPIO.setup(self.BUTTON_RIGHT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                logger.info(f"GPIO buttons initialized on pins {self.BUTTON_LEFT_PIN} and {self.BUTTON_RIGHT_PIN}")
            except Exception as e:
                logger.error(f"Failed to setup GPIO: {e}")
                raise
        else:
            logger.warning("GPIO not available, button functionality disabled")
    
    def _is_debounced(self, button: str) -> bool:
        """Check if enough time has passed since last button press."""
        current_time = time.time()
        if current_time - self.last_press_time[button] > self.DEBOUNCE_TIME:
            self.last_press_time[button] = current_time
            return True
        return False
    
    async def _make_api_request(self, endpoint: str, button_name: str):
        """Make POST request to widget API."""
        try:
            timeout = aiohttp.ClientTimeout(total=5.0)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(endpoint) as response:
                    if response.status == 200:
                        logger.info(f"Successfully switched {button_name} widget")
                    else:
                        logger.warning(f"API request failed with status {response.status}")
        except asyncio.TimeoutError:
            logger.error(f"API request to {endpoint} timed out")
        except Exception as e:
            logger.error(f"Failed to make API request to {endpoint}: {e}")
    
    async def _handle_button_press(self, button: str):
        """Handle a button press event."""
        if not self._is_debounced(button):
            return
        
        logger.info(f"{button.capitalize()} button pressed")
        
        # Make API request
        if button == "left":
            await self._make_api_request(self.LEFT_WIDGET_ENDPOINT, "left")
        elif button == "right":
            await self._make_api_request(self.RIGHT_WIDGET_ENDPOINT, "right")
        
        # Trigger display refresh
        if self.refresh_callback:
            self.refresh_callback()
    
    def _gpio_button_loop(self):
        """GPIO button monitoring loop (runs in thread)."""
        logger.info("Starting GPIO button monitoring loop")
        
        while self.running:
            try:
                # Check left button (active low with pull-up)
                if not GPIO.input(self.BUTTON_LEFT_PIN) == GPIO.LOW:
                    asyncio.run(self._handle_button_press("left"))
                
                # Check right button (active low with pull-up)
                if not GPIO.input(self.BUTTON_RIGHT_PIN) == GPIO.LOW:
                    asyncio.run(self._handle_button_press("right"))
                
                time.sleep(0.05)  # 50ms polling interval
                
            except Exception as e:
                logger.error(f"Error in GPIO button loop: {e}")
                time.sleep(1)
    
    def _keyboard_button_loop(self):
        """Keyboard button simulation loop for development."""
        logger.info("Starting keyboard button simulation")
        logger.info("Press 'a' for left button, 'd' for right button, 'q' to quit")
        
        try:
            import sys
            import tty
            import termios
            
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())
            
            while self.running:
                try:
                    char = sys.stdin.read(1)
                    if char.lower() == 'a':
                        asyncio.run(self._handle_button_press("left"))
                    elif char.lower() == 'd':
                        asyncio.run(self._handle_button_press("right"))
                    elif char.lower() == 'q':
                        logger.info("Quit requested via keyboard")
                        break
                    time.sleep(0.1)
                except KeyboardInterrupt:
                    break
            
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
            
        except ImportError:
            logger.warning("Termios not available, keyboard simulation disabled")
            while self.running:
                time.sleep(1)
    
    def start(self):
        """Start the button monitoring thread."""
        if self.running:
            logger.warning("Button handler already running")
            return
        
        self.running = True
        
        if self.config.get("DISPLAY_ENVIRONMENT") == "development":
            self.thread = threading.Thread(target=self._keyboard_button_loop, daemon=True)
        elif GPIO_AVAILABLE:
            self.thread = threading.Thread(target=self._gpio_button_loop, daemon=True)
        else:
            logger.error("No button input method available")
            return
        
        self.thread.start()
        logger.info("Button handler started")
    
    def stop(self):
        """Stop the button monitoring thread."""
        if not self.running:
            return
        
        logger.info("Stopping button handler")
        self.running = False
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        
        if GPIO_AVAILABLE and self.config.get("DISPLAY_ENVIRONMENT") != "development":
            try:
                GPIO.cleanup()
            except:
                pass
        
        logger.info("Button handler stopped")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
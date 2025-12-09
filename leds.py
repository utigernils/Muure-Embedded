import time
from datetime import datetime, time as dt_time
from typing import Tuple, Optional
import threading
import board
import neopixel
from config import Config


class LEDController:
    """
    LED controller using NeoPixel library with various light effects.
    Supports time-based blocking to prevent lights during specified hours.
    """
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize the LED controller with configuration."""
        if config is None:
            config = Config()
        
        self.config = config
        self.num_pixels = int(self.config.get("LED_NUM_PIXELS", "4"))
        self.brightness = float(self.config.get("LED_BRIGHTNESS", "0.3"))
        self.pin_name = self.config.get("LED_PIN", "D18")
        
        # Time blocking configuration (24-hour format)
        self.block_start_hour = int(self.config.get("LED_BLOCK_START_HOUR", "22"))
        self.block_end_hour = int(self.config.get("LED_BLOCK_END_HOUR", "7"))
        
        # Initialize NeoPixel strip
        try:
            pin = getattr(board, self.pin_name)
            self.pixels = neopixel.NeoPixel(
                pin, 
                self.num_pixels, 
                brightness=self.brightness,
                auto_write=False
            )
        except AttributeError:
            raise ValueError(f"Invalid pin name: {self.pin_name}")
        
        # Thread control for animations
        self._animation_thread: Optional[threading.Thread] = None
        self._stop_animation = threading.Event()
        
        # Color definitions
        self.colors = {
            "red": (255, 0, 0),
            "green": (0, 255, 0),
            "blue": (0, 100, 255),
            "yellow": (255, 255, 0),
            "purple": (128, 0, 128),
            "white": (255, 255, 255),
            "orange": (255, 165, 0),
            "off": (0, 0, 0)
        }
    
    def _is_blocked_time(self) -> bool:
        """Check if current time falls within the blocked hours."""
        current_time = datetime.now().time()
        current_hour = current_time.hour
        
        # Handle case where block period crosses midnight
        if self.block_start_hour > self.block_end_hour:
            return current_hour >= self.block_start_hour or current_hour < self.block_end_hour
        else:
            return self.block_start_hour <= current_hour < self.block_end_hour
    
    def _stop_current_animation(self):
        """Stop any currently running animation."""
        if self._animation_thread and self._animation_thread.is_alive():
            self._stop_animation.set()
            self._animation_thread.join(timeout=2.0)
        self._stop_animation.clear()
    
    def _set_all_pixels(self, color: Tuple[int, int, int]):
        """Set all pixels to the same color."""
        if self._is_blocked_time():
            return
        
        for i in range(self.num_pixels):
            self.pixels[i] = color
        self.pixels.show()
    
    def _fade_effect(self, color: Tuple[int, int, int], duration: float = 2.0, steps: int = 50):
        """Create a fade in/out effect."""
        if self._is_blocked_time():
            return
        
        step_delay = duration / (steps * 2)  # *2 for fade in and fade out
        
        # Fade in
        for step in range(steps):
            if self._stop_animation.is_set():
                return
            
            fade_factor = step / steps
            faded_color = (
                int(color[0] * fade_factor),
                int(color[1] * fade_factor),
                int(color[2] * fade_factor)
            )
            self._set_all_pixels(faded_color)
            time.sleep(step_delay)
        
        # Fade out
        for step in range(steps, -1, -1):
            if self._stop_animation.is_set():
                return
            
            fade_factor = step / steps
            faded_color = (
                int(color[0] * fade_factor),
                int(color[1] * fade_factor),
                int(color[2] * fade_factor)
            )
            self._set_all_pixels(faded_color)
            time.sleep(step_delay)
    
    def _pulse_effect(self, color: Tuple[int, int, int], pulses: int = 3, pulse_duration: float = 0.5):
        """Create a pulsing effect."""
        if self._is_blocked_time():
            return
        
        for _ in range(pulses):
            if self._stop_animation.is_set():
                return
            
            self._set_all_pixels(color)
            time.sleep(pulse_duration)
            self._set_all_pixels(self.colors["off"])
            time.sleep(pulse_duration * 0.5)
    
    def _loading_animation(self):
        """Animated loading effect with rotating light."""
        if self._is_blocked_time():
            return
        
        while not self._stop_animation.is_set():
            for i in range(self.num_pixels):
                if self._stop_animation.is_set():
                    return
                
                # Clear all pixels
                for j in range(self.num_pixels):
                    self.pixels[j] = self.colors["off"]
                
                # Light up current pixel
                self.pixels[i] = self.colors["blue"]
                self.pixels.show()
                time.sleep(0.1)
    
    def fault(self):
        """Display fault indication with red pulsing effect."""
        self._stop_current_animation()
        
        def fault_animation():
            for _ in range(5):  # Pulse 5 times
                if self._stop_animation.is_set():
                    return
                self._pulse_effect(self.colors["red"], pulses=1, pulse_duration=0.3)
        
        self._animation_thread = threading.Thread(target=fault_animation, daemon=True)
        self._animation_thread.start()
    
    def success(self):
        """Display success indication with green fade effect."""
        self._stop_current_animation()
        
        def success_animation():
            self._fade_effect(self.colors["green"], duration=1.5)
            time.sleep(0.5)
            self._set_all_pixels(self.colors["off"])
        
        self._animation_thread = threading.Thread(target=success_animation, daemon=True)
        self._animation_thread.start()
    
    def loading(self):
        """Display loading indication with rotating blue light."""
        self._stop_current_animation()
        self._animation_thread = threading.Thread(target=self._loading_animation, daemon=True)
        self._animation_thread.start()
    
    def notification(self):
        """Display notification with yellow/orange pulse."""
        self._stop_current_animation()
        
        def notification_animation():
            self._pulse_effect(self.colors["orange"], pulses=3, pulse_duration=0.4)
            time.sleep(0.5)
            self._set_all_pixels(self.colors["off"])
        
        self._animation_thread = threading.Thread(target=notification_animation, daemon=True)
        self._animation_thread.start()
    
    def off(self):
        """Turn off all LEDs and stop any running animations."""
        self._stop_current_animation()
        self._set_all_pixels(self.colors["off"])
    
    def cleanup(self):
        """Clean up resources and turn off LEDs."""
        self.off()
        if hasattr(self, 'pixels'):
            self.pixels.deinit()


# Convenience function for easy usage
def create_led_controller(config: Optional[Config] = None) -> LEDController:
    """Create and return an LED controller instance."""
    return LEDController(config)


__all__ = ["LEDController", "create_led_controller"]
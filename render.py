"""
Renderer service for capturing browser screenshots.
Manages headless browser automation to render the frontend as PNG.
"""
import asyncio
import logging
from playwright.async_api import async_playwright
from pathlib import Path


class Renderer:
    """Handles headless browser rendering to PNG."""
    
    def __init__(self):
        self.url = "http://localhost:8000/"
        self.width = 800
        self.height = 480
        self.logger = logging.getLogger(__name__)
    
    async def render_to_png(self, output_path: str = "./renders/output.png", max_retries: int = 5) -> Path:
        """
        Open headless browser, wait for page load, and capture screenshot.
        
        Args:
            output_path: Path where the PNG should be saved
            max_retries: Number of times to retry if page fails to load
            
        Returns:
            Path object pointing to the saved PNG file
        """
        for attempt in range(max_retries):
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True)
                    
                    page = await browser.new_page(
                        viewport={"width": self.width, "height": self.height}
                    )
                    
                    self.logger.info(f"Attempting to load {self.url} (attempt {attempt + 1}/{max_retries})...")
                    await page.goto(self.url, wait_until="domcontentloaded", timeout=30000)
                    
                    self.logger.info("Page loaded, waiting for content to render...")
                    await asyncio.sleep(3)
                    
                    output_file = Path(output_path)
                    await page.screenshot(path=str(output_file), full_page=False)
                    self.logger.info(f"Screenshot saved successfully to {output_file}")
                    
                    await browser.close()
                    
                    return output_file
            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 5
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(f"Failed to render after {max_retries} attempts: {e}")
                    raise Exception(f"Failed to render after {max_retries} attempts: {e}")

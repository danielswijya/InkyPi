from plugins.base_plugin.base_plugin import BasePlugin
from utils.image_utils import take_screenshot
import logging

logger = logging.getLogger(__name__)

class BentoGrid(BasePlugin):
    def generate_image(self, settings, device_config):
        """Screenshot the bento grid dashboard and display it."""
        
        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]
        
        # Screenshot the main dashboard page
        url = "http://localhost:8080/"
        logger.info(f"Taking screenshot of bento dashboard: {url}")
        
        image = take_screenshot(url, dimensions, timeout_ms=10000)
        
        if not image:
            raise RuntimeError("Failed to screenshot bento dashboard, please check logs.")
        
        return image

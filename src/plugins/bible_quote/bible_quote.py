from plugins.base_plugin.base_plugin import BasePlugin
from PIL import Image, ImageDraw, ImageFont, ImageColor
import logging

logger = logging.getLogger(__name__)

class BibleQuote(BasePlugin):
    def _fetch_verse(self, settings, device_config):
        """Return verse data for the web interface."""
        return {
            'text': 'Commit your works to the Lord, and your plans will be established.',
            'reference': 'Proverbs 16:3',
            'version': 'ESV'
        }
    
    def generate_image(self, settings, device_config):
        """Generate the Bible verse image for the display using HTML/CSS rendering"""
        # Hardcoded verse - you can change this to any verse you like
        verse_text = "Commit your works to the Lord, and your plans will be established."
        verse_reference = "Proverbs 16:3"
        verse_version = "ESV"
        
        # Get dimensions from device config
        dimensions = device_config.get_resolution()
        if device_config.get_config("orientation") == "vertical":
            dimensions = dimensions[::-1]
        
        # Template parameters
        template_params = {
            'verse_text': verse_text,
            'verse_reference': verse_reference,
            'verse_version': verse_version,
            'show_reference': True,
            'show_version': True
        }
        
        # Render using the HTML template and CSS
        return self.render_image(dimensions, 'bible_quote.html', 'bible_quote.css', template_params)
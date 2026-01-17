import logging
from datetime import datetime
import pytz
import requests

logger = logging.getLogger(__name__)

def get_weather_data_for_dashboard(device_config, latitude=None, longitude=None, units='metric'):
    """
    Extract weather data without generating an image for display in the bento dashboard.
    Uses the free OpenWeatherMap Current Weather API.
    
    Args:
        device_config: The Config instance with device settings
        latitude: Optional latitude (defaults to config or hardcoded value)
        longitude: Optional longitude (defaults to config or hardcoded value)
        units: 'imperial', 'metric', or 'standard'
    
    Returns:
        Dictionary with weather data or None if error occurs
    """
    try:
        # Get API key from environment
        api_key = device_config.load_env_key("OPEN_WEATHER_MAP_SECRET")
        if not api_key:
            logger.warning("OpenWeatherMap API key not found")
            return None
        
        # Use provided coordinates or defaults
        lat = latitude if latitude else 42.3611  # Default: Boston
        lon = longitude if longitude else -71.058
        
        # Use the free Current Weather API endpoint
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units={units}&appid={api_key}"
        
        # Fetch weather data
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        weather_data = response.json()
        
        if not weather_data or weather_data.get('cod') != 200:
            logger.error(f"Invalid weather data received: {weather_data}")
            return None
        
        # Get timezone for last updated time
        timezone_str = device_config.get_config("timezone", default="UTC")
        tz = pytz.timezone(timezone_str)
        dt = datetime.fromtimestamp(weather_data.get('dt'), tz=tz)
        
        # Extract just the data needed for the bento box
        return {
            'temp': round(weather_data.get('main', {}).get('temp', 0)),
            'feels_like': round(weather_data.get('main', {}).get('feels_like', 0)),
            'condition': weather_data.get('weather', [{}])[0].get('description', 'N/A').title(),
            'icon': weather_data.get('weather', [{}])[0].get('icon', '01d'),
            'humidity': weather_data.get('main', {}).get('humidity', 0),
            'wind_speed': round(weather_data.get('wind', {}).get('speed', 0)),
            'units': 'metric',
            'last_updated': dt.strftime('%I:%M %p'),
            'icon_url': f"http://openweathermap.org/img/wn/{weather_data.get('weather', [{}])[0].get('icon', '01d')}@2x.png"
        }
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weather data from API: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing weather data: {e}")
        return None
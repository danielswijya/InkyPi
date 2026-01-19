from flask import Blueprint, request, jsonify, current_app, render_template, send_file
import os
from datetime import datetime
import pytz
import logging
from plugins.football_fixtures.football_fixtures import FootballFixtures

logger = logging.getLogger(__name__)
main_bp = Blueprint("main", __name__)

def get_weather_from_plugin(device_config):
    """Get weather data using the weather plugin configuration but 2.5 API."""
    try:
        # Find the weather plugin in the configured plugins
        plugins = device_config.get_plugins()
        weather_plugin_config = None
        
        for plugin in plugins:
            if plugin.get('id') == 'weather' and not plugin.get('disabled', False):
                weather_plugin_config = plugin
                break
        
        if not weather_plugin_config:
            logger.info("Weather plugin not configured, using defaults")
            return get_simple_weather_data(device_config)
        
        # Get settings from the plugin config
        settings = weather_plugin_config.get('settings', {})
        lat = float(settings.get('latitude', 42.3611))
        lon = float(settings.get('longitude', -71.058))
        units = settings.get('units', 'metric')
        
        # Get API key
        api_key = device_config.load_env_key("OPEN_WEATHER_MAP_SECRET")
        if not api_key:
            logger.warning("OpenWeatherMap API key not found")
            return None
        
        # Use 2.5 API (free tier)
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units={units}&appid={api_key}"
        
        import requests
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('cod') != 200:
            logger.error(f"Invalid weather data: {data}")
            return None
        
        return {
            'temp': round(data.get('main', {}).get('temp', 0)),
            'feels_like': round(data.get('main', {}).get('feels_like', 0)),
            'condition': data.get('weather', [{}])[0].get('description', 'N/A').title(),
            'icon': data.get('weather', [{}])[0].get('icon', '01d'),
            'humidity': data.get('main', {}).get('humidity', 0),
            'wind_speed': round(data.get('wind', {}).get('speed', 0)),
            'units': units,
            'icon_url': f"http://openweathermap.org/img/wn/{data.get('weather', [{}])[0].get('icon', '01d')}@2x.png"
        }
        
    except Exception as e:
        logger.error(f"Error fetching weather data: {e}")
        return None

def get_simple_weather_data(device_config):
    """Fallback: Get weather using simple Current Weather API (free tier)."""
    try:
        import requests
        
        api_key = device_config.load_env_key("OPEN_WEATHER_MAP_SECRET")
        if not api_key:
            logger.warning("OpenWeatherMap API key not found")
            return None
        
        # Default coordinates (Boston)
        lat = 42.3611
        lon = -71.058
        units = 'metric'
        
        # Use the free Current Weather API endpoint
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&units={units}&appid={api_key}"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get('cod') != 200:
            logger.error(f"Invalid weather data: {data}")
            return None
        
        return {
            'temp': round(data.get('main', {}).get('temp', 0)),
            'feels_like': round(data.get('main', {}).get('feels_like', 0)),
            'condition': data.get('weather', [{}])[0].get('description', 'N/A').title(),
            'icon': data.get('weather', [{}])[0].get('icon', '01d'),
            'humidity': data.get('main', {}).get('humidity', 0),
            'wind_speed': round(data.get('wind', {}).get('speed', 0)),
            'units': units,
            'icon_url': f"http://openweathermap.org/img/wn/{data.get('weather', [{}])[0].get('icon', '01d')}@2x.png"
        }
        
    except Exception as e:
        logger.error(f"Error in simple weather fetch: {e}")
        return None

def get_bible_from_plugin(device_config):
    """Get Bible verse data using the bible_quote plugin."""
    try:
        # Find the bible_quote plugin in the configured plugins
        plugins = device_config.get_plugins()
        bible_plugin_config = None
        
        for plugin in plugins:
            if plugin.get('id') == 'bible_quote' and not plugin.get('disabled', False):
                bible_plugin_config = plugin
                break
        
        if not bible_plugin_config:
            logger.info("Bible quote plugin not configured")
            return None
        
        # Import the bible_quote plugin
        from plugins.bible_quote.bible_quote import BibleQuote
        bible_plugin = BibleQuote(bible_plugin_config)
        
        # Get settings from the plugin config
        settings = bible_plugin_config.get('settings', {})
        
        # Fetch verse data using the plugin's method
        verse_data = bible_plugin._fetch_verse(settings, device_config)
        
        return verse_data
        
    except Exception as e:
        logger.error(f"Error fetching Bible verse from plugin: {e}")
        return None

@main_bp.route('/')
def main_page():
    device_config = current_app.config['DEVICE_CONFIG']
    # Get current time based on your InkyPi settings
    tz_str = device_config.get_config("timezone", default="UTC")
    now = datetime.now(pytz.timezone(tz_str))
    
    # Format: THU JAN 15 2026 (Clear Japanese-style uppercase)
    formatted_time = now.strftime("%a %b %d %Y").upper()
    
    # Fetch weather data from the weather plugin
    weather_data = get_weather_from_plugin(device_config)
    
    # Fetch Bible verse from the bible_quote plugin
    bible_data = get_bible_from_plugin(device_config)
    
    # TODO: Add live sports scores
    # sports_data = get_live_sports_scores()
    
    return render_template('inky.html',
                         config=device_config.get_config(),
                         plugins=device_config.get_plugins(),
                         current_time_date=formatted_time,
                         weather=weather_data,
                         bible=bible_data)
                         # sports=sports_data  # Add when ready

@main_bp.route('/api/current_image')
def get_current_image():
    """Serve current_image.png with conditional request support (If-Modified-Since)."""
    image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'images', 'current_image.png')
    
    if not os.path.exists(image_path):
        return jsonify({"error": "Image not found"}), 404
    
    # Get the file's last modified time (truncate to seconds to match HTTP header precision)
    file_mtime = int(os.path.getmtime(image_path))
    last_modified = datetime.fromtimestamp(file_mtime)
    
    # Check If-Modified-Since header
    if_modified_since = request.headers.get('If-Modified-Since')
    if if_modified_since:
        try:
            # Parse the If-Modified-Since header
            client_mtime = datetime.strptime(if_modified_since, '%a, %d %b %Y %H:%M:%S %Z')
            client_mtime_seconds = int(client_mtime.timestamp())
            
            # Compare (both now in seconds, no sub-second precision)
            if file_mtime <= client_mtime_seconds:
                return '', 304
        except (ValueError, AttributeError):
            pass
    
    # Send the file with Last-Modified header
    response = send_file(image_path, mimetype='image/png')
    response.headers['Last-Modified'] = last_modified.strftime('%a, %d %b %Y %H:%M:%S GMT')
    response.headers['Cache-Control'] = 'no-cache'
    return response

@main_bp.route("/api/football/fixture")
def get_football_fixture():
    """API endpoint to get current/next Chelsea fixture from ESPN."""
    try:
        logger.info("Football fixture endpoint called")
        device_config = current_app.config['DEVICE_CONFIG']
        
        # Get timezone from config
        tz = device_config.get_config("timezone", default="America/New_York")
        
        # No API key needed for ESPN!
        football = FootballFixtures(timezone=tz)
        fixture = football.get_next_or_live_fixture()
        
        if fixture:
            logger.info(f"Fixture found: {fixture}")
            return jsonify(fixture)
        
        logger.warning("No fixtures found")
        return jsonify({"error": "No fixtures found"}), 404
        
    except Exception as e:
        logger.error(f"Error in football fixture endpoint: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


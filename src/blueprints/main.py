from flask import Blueprint, request, jsonify, current_app, render_template, send_file
import os
from datetime import datetime
import pytz

main_bp = Blueprint("main", __name__)

@main_bp.route('/')
def main_page():
    device_config = current_app.config['DEVICE_CONFIG']
    # Get current time based on your InkyPi settings
    tz_str = device_config.get_config("timezone", default="UTC")
    now = datetime.now(pytz.timezone(tz_str))
    
    # Format: THU JAN 15 2026 (Clear Japanese-style uppercase)
    formatted_time = now.strftime("%a %b %d %Y").upper()
    
    return render_template('inky.html',config=device_config.get_config(),plugins=device_config.get_plugins(),current_time_date=formatted_time) # Passing the time variable

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
# web_server.py

import json
import logging
import os
import socket

from twisted.internet import reactor
from twisted.web import resource, server
from twisted.web.static import File

import shared_state  # To access race data
from race_timer import RaceTimer # For formatting time

logger = logging.getLogger('rfid_race_timer')

# Module-level variable to hold the Twisted listening port object
_listening_port = None
_server_port = 8000 # Default port

# This resource handles the dynamic JSON data requests
class RaceDataResource(resource.Resource):
    isLeaf = True

    def render_GET(self, request):
        """Handle GET requests for /api/race-data."""
        request.setHeader(b"Content-Type", b"application/json")
        request.setHeader(b'Access-Control-Allow-Origin', b'*') # For CORS

        # This logic should be similar to your original data preparation
        # For simplicity, we directly access shared_state here.
        # This is safe because Twisted calls this method from the reactor thread.
        racers_list = sorted(
            [r for r in shared_state.racers_data.values() if r.get('lap_times')],
            key=lambda x: (-x['laps'], x['finish_time'] if x['finish_time'] > 0 else float('inf'))
        )
        
        elapsed_time = reactor.seconds() - shared_state.race_start_time if shared_state.race_active else 0

        race_data = {
            "active": shared_state.race_active,
            "elapsed_formatted": RaceTimer.format_time(elapsed_time),
            "racers": racers_list,
        }

        return json.dumps(race_data, default=str).encode('utf-8')

# --- Main Functions to be Called by the GUI ---

def _start_web_server():
    """Internal function to start the server, called by the reactor."""
    global _listening_port
    if _listening_port is not None:
        logger.warning("Web server already running.")
        return

    try:
        web_dir_path = os.path.join(os.path.dirname(__file__), 'web')
        if not os.path.exists(web_dir_path):
            os.makedirs(web_dir_path)
            logger.info(f"Created web directory at: {web_dir_path}")

        # The root resource serves static files (index.html, etc.)
        root = File(web_dir_path.encode("utf-8"))
        
        # Create a resource for the /api endpoint
        api_resource = resource.Resource()
        root.putChild(b"api", api_resource)
        
        # Add the /api/race-data endpoint
        api_resource.putChild(b"race-data", RaceDataResource())

        site = server.Site(root)
        _listening_port = reactor.listenTCP(_server_port, site)
        logger.info(f"Web server started and listening on port {_server_port}")
    except Exception as e:
        logger.error(f"Failed to start web server: {e}", exc_info=True)


def _stop_web_server():
    """Internal function to stop the server, called by the reactor."""
    global _listening_port
    if _listening_port:
        d = _listening_port.stopListening()
        _listening_port = None
        logger.info("Web server stopped.")
        return d
    return None

def start_server():
    """
    Schedules the web server to start on the reactor thread.
    This is safe to call from the main GUI thread.
    """
    reactor.callFromThread(_start_web_server)
    return True

def stop_server():
    """
    Schedules the web server to stop on the reactor thread.
    This is safe to call from the main GUI thread.
    """
    if _listening_port:
        reactor.callFromThread(_stop_web_server)
    return True

def get_server_url():
    """Get the URL for the web server."""
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return f"http://{local_ip}:{_server_port}"
    except Exception:
        return f"http://127.0.0.1:{_server_port}"

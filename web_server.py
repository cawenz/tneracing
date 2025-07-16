# web_server.py
import http.server
import socketserver
import json
import threading
import os
import logging
from pathlib import Path
import time
import shared_state
from race_timer import RaceTimer

logger = logging.getLogger('rfid_race_timer')

# Global reference to server for shutdown
_server = None
_server_thread = None
_server_port = 8000
_web_dir = None

# Cache for race data to prevent excessive processing
_race_data_cache = {}
_cache_lock = threading.Lock()
_last_update_time = 0
_cache_ttl = 0.2  # Cache lifetime in seconds

def update_race_data_cache():
    """Update the cached race data - called from main thread"""
    global _race_data_cache, _last_update_time
    
    try:
        # Don't update cache too frequently
        current_time = time.time()
        if current_time - _last_update_time < _cache_ttl:
            return
            
        # Create a thread-safe copy of race data
        with _cache_lock:
            elapsed = current_time - shared_state.race_start_time if shared_state.race_active else 0
            
            race_data = {
                "active": shared_state.race_active,
                "elapsed": elapsed,
                "elapsed_formatted": RaceTimer.format_time(elapsed),
                "target_laps": shared_state.num_laps,
                "race_mode": shared_state.race_mode,  # NEW
                "race_mode_display": "Start Line Race" if shared_state.race_mode == shared_state.RACE_MODE_START_LINE else "Rolling Start",  # NEW
                "racers": [],
                "lap_times": []
            }
            
            # Copy racer data (avoid direct shared_state access in handler thread)
            racers_list = []
            for racer_id, racer in shared_state.racers_data.items():
                racers_list.append({
                    "id": racer_id,
                    "name": racer.get("name", "Unknown"),
                    "laps": racer.get("laps", 0),
                    "position": racer.get("position", 0),
                    "lap_times_raw": racer.get("lap_times", []),
                    "calculated_gap": racer.get("calculated_gap", "-"),
                    "best_lap_raw": racer.get("best_lap", 0),
                    "last_lap_raw": racer.get("last_lap", 0)
                })
            
            # Sort racers by position for consistent display
            racers_list.sort(key=lambda x: x["position"] if x["position"] > 0 else float('inf'))
            
            # Process each racer for display
            for racer in racers_list:
                # Calculate racer's actual total race time based on mode
                racer_total_time = "-"
                if shared_state.race_mode == shared_state.RACE_MODE_ROLLING and racer.get("rolling_start_time") is not None and racer["lap_times_raw"]:
                    total_seconds = racer["lap_times_raw"][-1] - racer["rolling_start_time"]
                    racer_total_time = RaceTimer.format_total_time(total_seconds)
                elif shared_state.race_mode == shared_state.RACE_MODE_START_LINE and racer.get("start_time") is not None and racer["lap_times_raw"]:
                    total_seconds = racer["lap_times_raw"][-1] - racer["start_time"]
                    racer_total_time = RaceTimer.format_total_time(total_seconds)
                
                # Format the gap (use the calculated gap from main app)
                gap_display = racer["calculated_gap"]
                
                # Format best lap time (3 decimal places)
                if racer["best_lap_raw"] > 0:
                    best_lap_display = f"{racer['best_lap_raw']:.3f}"
                else:
                    best_lap_display = "-"
                
                # Format last lap time (3 decimal places)
                if racer["last_lap_raw"] > 0:
                    last_lap_display = f"{racer['last_lap_raw']:.3f}"
                else:
                    last_lap_display = "-"
                
                # Format total time (use the last lap time if available)
                if racer["lap_times_raw"]:
                    total_time_raw = racer["lap_times_raw"][-1]
                    total_time_display = RaceTimer.format_total_time(total_time_raw)
                else:
                    total_time_display = "-"
                
                race_data["racers"].append({
                    "id": racer["id"],
                    "name": racer["name"],
                    "laps": racer["laps"],
                    "position": racer["position"],
                    "finished": racer.get("finished", False),
                    "target_laps": shared_state.num_laps,
                    "gap": gap_display,
                    "best_lap": best_lap_display,
                    "last_lap": last_lap_display,
                    "total_time": total_time_display,
                    "racer_total_time": racer_total_time,  # NEW - actual race time
                    "finish_time_formatted": total_time_display
                })

            # Copy lap times data with race mode support
                lap_times = racer["lap_times_raw"]
                for i, lap_time in enumerate(lap_times):
                    lap_num = i + 1
                    
                    # Calculate individual lap time based on race mode
                    if i == 0:
                        if shared_state.race_mode == shared_state.RACE_MODE_START_LINE and racer.get("start_time") is not None:
                            individual_lap = lap_time - racer["start_time"]
                        elif shared_state.race_mode == shared_state.RACE_MODE_ROLLING and racer.get("rolling_start_time") is not None:
                            individual_lap = lap_time - racer["rolling_start_time"]
                        else:
                            individual_lap = lap_time
                    else:
                        individual_lap = lap_time - lap_times[i-1]
                    
                    race_data["lap_times"].append({
                        "racer_name": racer["name"],
                        "lap_number": lap_num,
                        "lap_time": individual_lap,
                        "lap_time_formatted": f"{individual_lap:.3f}",
                        "total_time": lap_time,
                        "total_time_formatted": f"{lap_time:.3f}"
                    })
            
            # Sort lap times (most recent first, then fastest)
            race_data["lap_times"].sort(key=lambda x: (-x["lap_number"], x["lap_time"]))
            
            # Update the cache
            _race_data_cache = race_data
            _last_update_time = current_time
            
    except Exception as e:
        logger.error(f"Error updating race data cache: {e}", exc_info=True)

class RaceDataHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler for race data"""
    
    def __init__(self, *args, **kwargs):
        # Store web_dir for path translation
        self.web_dir = _web_dir
        super().__init__(*args, **kwargs)
    
    def log_message(self, format, *args):
        """Override to use our logger instead of stderr"""
        logger.debug(f"{self.address_string()} - {format % args}")
    
    def do_GET(self):
        """Handle GET requests"""
        # Handle API requests
        if self.path == '/api/race-data':
            self.send_race_data()
            return
            
        # Default to index.html for root path
        if self.path == '/':
            self.path = '/index.html'
            
        # Try to serve the file from the web directory
        try:
            file_path = os.path.join(self.web_dir, self.path.lstrip('/'))
            
            # Security check to prevent directory traversal
            if os.path.commonprefix([os.path.abspath(file_path), self.web_dir]) != self.web_dir:
                self.send_error(403, "Forbidden")
                return
                
            # If file exists, serve it
            if os.path.isfile(file_path):
                # Determine content type
                content_type = self.guess_type(file_path)
                
                # Read file content
                with open(file_path, 'rb') as file:
                    content = file.read()
                    
                # Send response
                self.send_response(200)
                self.send_header('Content-Type', content_type)
                self.send_header('Content-Length', len(content))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "File not found")
        except Exception as e:
            logger.error(f"Error serving {self.path}: {e}", exc_info=True)
            self.send_error(500, f"Server error: {str(e)}")
    
    def send_race_data(self):
        """Send current race data as JSON"""
        try:
            # Use the cached race data instead of processing it here
            with _cache_lock:
                race_data = _race_data_cache.copy()
                
            # Send JSON response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')  # For CORS
            self.end_headers()
            self.wfile.write(json.dumps(race_data).encode())
            
        except Exception as e:
            logger.error(f"Error sending race data: {e}", exc_info=True)
            self.send_error(500, f"Error sending race data: {str(e)}")

def create_web_files():
    """Create necessary web files if they don't exist"""
    global _web_dir
    
    _web_dir = os.path.join(os.path.dirname(__file__), 'web')
    os.makedirs(_web_dir, exist_ok=True)
    
    # Define the web files to create/update
    # Define the web files to create/update
    web_files = {
        "index.html": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RFID Race Timer - Live Results</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Live Race Results</h1>
            <div class="race-status">
                <div id="status-indicator" class="status-indicator"></div>
                <div id="race-status">Waiting for race to start</div>
            </div>
            <div id="race-timer" class="race-timer">0:00:00.000</div>
        </header>
        <div class="tabs">
            <button class="tab-button active" data-tab="standings">Current Standings</button>
            <button class="tab-button" data-tab="lap-times">Lap Times</button>
        </div>
        <main>
            <div id="standings" class="tab-content active">
                <table class="results-table">
                    <thead>
                        <tr>
                            <th>Position</th>
                            <th>Racer</th>
                            <th>Laps</th>
                            <th>Gap</th>
                            <th>Best Lap</th>
                            <th>Last Lap</th>
                            <th>Total Time</th>
                        </tr>
                    </thead>
                    <tbody id="standings-body">
                        <tr>
                            <td colspan="7">Waiting for race data...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div id="lap-times" class="tab-content">
                <h2>Lap Times</h2>
                <table>
                    <thead>
                        <tr>
                            <th>Racer Name</th>
                            <th>Lap Number</th>
                            <th>Lap Time</th> <!-- This will be individual lap time -->
                            <th>Total Time</th> <!-- This will be cumulative time at lap completion -->
                        </tr>
                    </thead>
                    <tbody id="lap-times-body">
                        <!-- Lap time rows will be populated by script.js -->
                    </tbody>
                </table>
            </div>
        </main>
    </div>
    <script src="script.js"></script>
</body>
</html>
""",
        "styles.css": """/* Your CSS styles here */
        
""",
        "script.js": """/* Your JavaScript code here */
document.addEventListener('DOMContentLoaded', function() {
const statusIndicator = document.getElementById('status-indicator');
const raceStatus = document.getElementById('race-status');
const raceTimer = document.getElementById('race-timer');
const standingsBody = document.getElementById('standings-body');
const lapTimesBody = document.getElementById('lap-times-body');
const tabButtons = document.querySelectorAll('.tab-button');
const tabContents = document.querySelectorAll('.tab-content');

// Function to switch tabs
function switchTab(tabId) {
    tabButtons.forEach(button => button.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));
    document.querySelector(`.tab-button[data-tab="${tabId}"]`).classList.add('active');
    document.getElementById(tabId).classList.add('active');
}

tabButtons.forEach(button => {
    button.addEventListener('click', () => switchTab(button.dataset.tab));
});

function updateStatus(active) {
    statusIndicator.classList.toggle('active', active);
    raceStatus.textContent = active ? 'Race in progress' : 'Waiting for race to start';
}

function updateTimer(elapsedFormatted) {
    raceTimer.textContent = elapsedFormatted;
}

function updateStandings(racers) {
    standingsBody.innerHTML = '';
    if (!racers || racers.length === 0) {
        standingsBody.innerHTML = '<tr><td colspan="7">No racers in the race.</td></tr>';
        return;
    }
    
    // Add each racer to the table
    racers.forEach(racer => {
        const row = document.createElement('tr');
        
        // Extract position (could be a number or a string)
        const position = racer.position > 0 ? racer.position : '-';
        
         // Format times with 3 decimal places
        //const gap = racer.gap || '-';
        const bestLap = racer.best_lap !== '-' ? racer.best_lap : '-';
        const lastLap = racer.last_lap !== '-' ? racer.last_lap : '-';
        const totalTime = racer.total_time !== '-' ? racer.total_time : '-';
        
          row.innerHTML = `
            <td>${racer.position > 0 ? racer.position : '-'}</td>
            <td>${racer.name}</td>
            <td>${racer.laps}</td>
            <td>${racer.gap || '-'}</td>
            <td>${racer.best_lap || '-'}</td>
            <td>${racer.last_lap || '-'}</td>
            <td>${racer.finish_time_formatted || '-'}</td>
        `;
        
        standingsBody.appendChild(row);
    });
}
function updateLapTimes(data) {
    lapTimesBody.innerHTML = '';
    let hasLapData = false;
    
    // First check if we have the new dedicated lap_times array
    if (data.lap_times && data.lap_times.length > 0) {
        hasLapData = true;
        
        // Sort lap times: most recent laps first, then by elapsed time
        const sortedLapTimes = [...data.lap_times].sort((a, b) => {
            if (a.lap_number !== b.lap_number) {
                return b.lap_number - a.lap_number; // Most recent laps first
            }
            return a.total_time - b.total_time; // Faster times first for same lap
        });
        
        // Display the lap times with formatted values
        sortedLapTimes.forEach(lap => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${lap.racer_name}</td>
                <td>${lap.lap_number}</td>
                <td>${lap.lap_time_formatted}</td>
                <td>${lap.total_time_formatted}</td>
            `;
            lapTimesBody.appendChild(row);
        });
    }
    // Fall back to the original method if lap_times array isn't available
    else if (data.racers && data.racers.length > 0) {
        let allLapEvents = [];
        data.racers.forEach(racer => {
            if (racer.lap_times && racer.lap_times.length > 0) {
                hasLapData = true;
                let previousTime = 0; // Track previous lap's cumulative time
                racer.lap_times.forEach((lap, index) => {
                    // Handle both old and new data structures
                    const lapRaw = typeof lap === 'object' ? lap.raw : lap;
                    const lapFormatted = typeof lap === 'object' ? lap.formatted : formatTimeNoHours(lap);
                    
                    allLapEvents.push({
                        racerName: racer.name || 'N/A',
                        lapNumber: index + 1,
                        cumulativeTimeRaw: lapRaw, // Make sure this is a number
                        cumulativeTimeFormatted: lapFormatted,
                        previousCumulativeTimeRaw: previousTime
                    });
                    previousTime = lapRaw; // Update previous time for next lap
                });
            }
        });
        
        // Sort all lap events by lap number (descending) then by cumulative time (ascending)
        allLapEvents.sort((a, b) => {
            if (a.lapNumber !== b.lapNumber) {
                return b.lapNumber - a.lapNumber; // Higher lap numbers first
            }
            return a.cumulativeTimeRaw - b.cumulativeTimeRaw; // Faster times first for same lap
        });
        
        allLapEvents.forEach(event => {
            const individualLapTime = event.cumulativeTimeRaw - event.previousCumulativeTimeRaw;
            const row = document.createElement('tr');
            
            // Format the times with 3 decimal places
            const formattedIndividualLap = formatLapTime(individualLapTime);
            const formattedCumulativeTime = formatTimeNoHours(event.cumulativeTimeRaw);
            
            row.innerHTML = `
                <td>${event.racerName}</td>
                <td>${event.lapNumber}</td>
                <td>${formattedIndividualLap}</td>
                <td>${formattedCumulativeTime}</td>
            `;
            lapTimesBody.appendChild(row);
        });
    }
    
    // Display "No lap times" message if no data was found
    if (!hasLapData) {
        lapTimesBody.innerHTML = '<tr><td colspan="4">No lap times recorded yet.</td></tr>';
    }
    
    // Log lap data for debugging
    console.log("Lap data available:", hasLapData);
    if (data.lap_times) console.log("Dedicated lap_times array length:", data.lap_times.length);
    if (data.racers) console.log("Racers array length:", data.racers.length);
}
// Format time with hours for the main race timer
function formatTime(seconds) {
    if (typeof seconds !== 'number' || seconds < 0) return '0:00:00.000';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours}:${String(minutes).padStart(2, '0')}:${String(secs.toFixed(3)).padStart(6, '0')}`;
}

// Format time without hours for finish times and total times
function formatTimeNoHours(seconds) {
    if (typeof seconds !== 'number' || seconds < 0) return '00:00.000';
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(minutes).padStart(2, '0')}:${String(secs.toFixed(3)).padStart(6, '0')}`;
}

// Format time for lap times (just seconds with three decimal places)
function formatLapTime(seconds) {
    if (typeof seconds !== 'number' || seconds < 0) return '0.000';
    return seconds.toFixed(3);
}

function formatTotalTime(seconds) {
    if (typeof seconds !== 'number' || seconds <= 0) return '-';
    const minutes = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(minutes).padStart(2, '0')}:${secs.toFixed(3).padStart(6, '0')}`;
}

/*function fetchRaceData() {
    fetch('/api/race-data')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            updateStatus(data.active);
            updateTimer(data.elapsed_formatted);
            updateStandings(data.racers); // Ensure racers are sorted by position
            updateLapTimes(data);
        })
        .catch(error => {
            console.error('Error fetching race data:', error);
            raceStatus.textContent = 'Error fetching data. Check console.';
        });
}*/

// Add this to your script.js for debugging
function fetchRaceData() {
    console.log("Fetching race data...");
    fetch('/api/race-data')
        .then(response => {
            console.log("Response received:", response.status);
            return response.json();
        })
        .then(data => {
            console.log("Data received:", data);
            
            // Debug racer information
            if (data.racers && data.racers.length > 0) {
                console.log("First racer:", data.racers[0]);
                console.log("Gap:", data.racers[0].gap);
                console.log("Best lap:", data.racers[0].best_lap);
                console.log("Last lap:", data.racers[0].last_lap);
            }
            
            // Debug lap times information
            console.log("Number of lap times:", data.lap_times ? data.lap_times.length : 0);
            if (data.lap_times && data.lap_times.length > 0) {
                console.log("First lap time entry:", data.lap_times[0]);
            } else {
                console.log("No lap times data found in response");
            }
            
            // Update the UI components
            updateStatus(data.active);
            updateTimer(data.elapsed_formatted);
            updateStandings(data.racers);
            
            // Pass the complete data object to updateLapTimes
            updateLapTimes(data);
        })
        .catch(error => {
            console.error("Error fetching race data:", error);
            
            // Try to provide more detailed error information
            if (error instanceof SyntaxError) {
                console.error("Invalid JSON response from server. Check server logs for errors.");
            } else if (error instanceof TypeError) {
                console.error("Network error or server unreachable.");
            }
        });
}

// Initial fetch and set interval
fetchRaceData();
setInterval(fetchRaceData, 1000); // Fetch every 1 second
});
"""
    }
    
    # Write/update all web files
    for filename, content in web_files.items():
        file_path = os.path.join(_web_dir, filename)
        try:
            # Only write if file doesn't exist
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Created web file: {filename}")
        except Exception as e:
            logger.error(f"Error creating web file {filename}: {e}")

def start_server(port=8000):
    """Start the web server on the specified port"""
    global _server, _server_thread, _server_port, _web_dir
    
    if _server_thread and _server_thread.is_alive():
        logger.warning("Web server is already running")
        return False
    
    # Create web files if they don't exist
    create_web_files()
    
    # Set up server
    _server_port = port
    
    try:
        # Ensure web directory is properly set
        if not _web_dir:
            _web_dir = os.path.join(os.path.dirname(__file__), 'web')
            os.makedirs(_web_dir, exist_ok=True)
            
        # Initialize race data cache
        update_race_data_cache()
        
        # Set handler directory
        handler = RaceDataHandler
        handler.web_dir = _web_dir
        
        # Create server
        _server = socketserver.ThreadingTCPServer(("", port), handler)
        _server.daemon_threads = True
        
        # Start server in a separate thread
        _server_thread = threading.Thread(target=_server.serve_forever, daemon=True)
        _server_thread.start()
        
        logger.info(f"Web server started on port {port}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to start web server: {e}", exc_info=True)
        return False

def stop_server():
    """Stop the web server"""
    global _server, _server_thread
    
    if not _server:
        logger.warning("Web server is not running")
        return False
    
    try:
        _server.shutdown()
        _server.server_close()
        _server = None
        _server_thread = None
        logger.info("Web server stopped")
        return True
    except Exception as e:
        logger.error(f"Error stopping web server: {e}")
        return False

def get_server_url():
    """Get the URL for the web server"""
    import socket
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return f"http://{local_ip}:{_server_port}"
    except Exception as e:
        logger.error(f"Error getting server URL: {e}")
        return f"http://localhost:{_server_port}"
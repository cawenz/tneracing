# web_server.py
import http.server
import socketserver
import json
import threading
import os
import logging
from pathlib import Path
import time
import shared_state  # Access shared race data
from race_timer import RaceTimer  # For time formatting

logger = logging.getLogger('rfid_race_timer')

# Global reference to server for shutdown
_server = None
_server_thread = None
_server_port = 8000

class RaceDataHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler for race data"""
    
    # Format time for display using RaceTimer's static method
    @staticmethod
    def format_time(seconds):
        return RaceTimer.format_time(seconds)
    
    def log_message(self, format, *args):
        """Override to use our logger instead of stderr"""
        logger.debug(f"{self.address_string()} - {format%args}")
    
    def do_GET(self):
        """Handle GET requests"""
        # API endpoint for race data
        # In web_server.py (Source 2), inside the RaceDataHandler class

# Find the do_GET method and modify the /api/race-data section like this:

        if self.path == '/api/race-data':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            
            # --- NEW LOGIC START: Live sorting for the web API ---
            
            # Prepare the list of racers for sorting
            all_racers = list(shared_state.racers_data.values())
            
            racers_in_progress = [r for r in all_racers if r.get("laps", 0) > 0]
            racers_not_started = [r for r in all_racers if r.get("laps", 0) == 0]

            # Sort racers in progress by laps (desc) and then by time (asc)
            racers_in_progress.sort(key=lambda r: (-r['laps'], r['lap_times'][-1]))
            
            # Combine the sorted lists
            sorted_racers = racers_in_progress + racers_not_started

            # Build the JSON response with live positions
            race_data = {
                'active': shared_state.race_active,
                'elapsed': time.time() - shared_state.race_start_time if shared_state.race_active else 0,
                'elapsed_formatted': self.format_time(time.time() - shared_state.race_start_time if shared_state.race_active else 0),
                'racers': []
            }

            for i, racer in enumerate(sorted_racers):
                # Calculate live position for racers in progress
                live_position = i + 1 if racer in racers_in_progress else "-"
                
                # Format lap times
                formatted_lap_times = []
                for lap_time in racer.get('lap_times', []):
                    formatted_lap_times.append({
                        'raw': lap_time,
                        'formatted': self.format_time(lap_time)
                    })
                
                # Add racer to response with the live position
                race_data['racers'].append({
                    'id': racer.get('tag'), # Assuming tag is the ID for the web view
                    'name': racer.get('name', 'Unknown'),
                    'laps': racer.get('laps', 0),
                    'position': live_position,  # <-- Using the new live position
                    'finished': racer.get('finished', False),
                    'finish_time': racer.get('finish_time', 0),
                    'finish_time_formatted': self.format_time(racer.get('finish_time', 0)),
                    'lap_times': formatted_lap_times
                })
            
            # Send JSON response
            self.wfile.write(json.dumps(race_data).encode())
        
        # For any other path, serve static files from web directory
        else:
            # Default to index.html if root is requested
            if self.path == '/':
                self.path = '/index.html'
            
            # Get web directory path
            web_dir = os.path.join(os.path.dirname(__file__), 'web')
            file_path = os.path.join(web_dir, self.path.lstrip('/'))
            
            try:
                # Make sure the file exists and is in the web directory
                if not os.path.isfile(file_path) or not os.path.abspath(file_path).startswith(os.path.abspath(web_dir)):
                    self.send_error(404, 'File not found')
                    return
                
                # Serve the file
                self.send_response(200)
                if self.path.endswith('.html'):
                    self.send_header('Content-Type', 'text/html')
                elif self.path.endswith('.js'):
                    self.send_header('Content-Type', 'application/javascript')
                elif self.path.endswith('.css'):
                    self.send_header('Content-Type', 'text/css')
                elif self.path.endswith('.json'):
                    self.send_header('Content-Type', 'application/json')
                elif self.path.endswith('.svg'):
                    self.send_header('Content-Type', 'image/svg+xml')
                self.end_headers()
                
                with open(file_path, 'rb') as file:
                    self.wfile.write(file.read())
            
            except Exception as e:
                logger.error(f"Error serving {self.path}: {e}")
                self.send_error(500, f"Server error: {str(e)}")

def create_web_files():
    """Create the necessary web files if they don't exist"""
    web_dir = os.path.join(os.path.dirname(__file__), 'web')
    os.makedirs(web_dir, exist_ok=True)
    
    # Create index.html
    index_path = os.path.join(web_dir, 'index.html')
    if not os.path.exists(index_path):
        with open(index_path, 'w') as f:
            f.write("""<!DOCTYPE html>
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

        <div id="standings" class="tab-content active">
            <table class="results-table">
                <thead>
                    <tr>
                        <th>Position</th>
                        <th>Racer</th>
                        <th>Laps</th>
                        <th>Time</th>
                    </tr>
                </thead>
                <tbody id="standings-body">
                    <tr>
                        <td colspan="4">Waiting for race data...</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div id="lap-times" class="tab-content">
            <table class="results-table">
                <thead>
                    <tr>
                        <th>Racer</th>
                        <th>Lap</th>
                        <th>Lap Time</th>
                        <th>Total Time</th>
                    </tr>
                </thead>
                <tbody id="lap-times-body">
                    <tr>
                        <td colspan="4">Waiting for race data...</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <footer>
        <div>RFID Race Timer</div>
        <div id="refresh-status">Refreshing...</div>
    </footer>

    <script src="script.js"></script>
</body>
</html>""")
    
    # Create styles.css
    css_path = os.path.join(web_dir, 'styles.css')
    if not os.path.exists(css_path):
        with open(css_path, 'w') as f:
            f.write("""
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f4f4f4;
    padding: 20px;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    background-color: #fff;
    border-radius: 8px;
    box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
    overflow: hidden;
}

header {
    background-color: #2c3e50;
    color: #fff;
    padding: 20px;
    text-align: center;
}

h1 {
    margin-bottom: 20px;
}

.race-timer {
    font-size: 3rem;
    font-weight: bold;
    margin: 10px 0;
    font-family: monospace;
}

.race-status {
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 10px 0;
}

.status-indicator {
    width: 15px;
    height: 15px;
    border-radius: 50%;
    background-color: #e74c3c; /* Red for inactive */
    margin-right: 10px;
}

.status-indicator.active {
    background-color: #2ecc71; /* Green for active */
}

.tabs {
    display: flex;
    background-color: #34495e;
}

.tab-button {
    background-color: transparent;
    border: none;
    color: #fff;
    padding: 15px 20px;
    cursor: pointer;
    flex: 1;
    font-size: 1rem;
    transition: background-color 0.3s;
}

.tab-button:hover {
    background-color: #2c3e50;
}

.tab-button.active {
    background-color: #2c3e50;
    border-bottom: 3px solid #3498db;
}

.tab-content {
    display: none;
    padding: 20px;
}

.tab-content.active {
    display: block;
}

.results-table {
    width: 100%;
    border-collapse: collapse;
}

.results-table th,
.results-table td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}

.results-table th {
    background-color: #f2f2f2;
    font-weight: bold;
}

.results-table tbody tr:hover {
    background-color: #f5f5f5;
}

footer {
    display: flex;
    justify-content: space-between;
    padding: 10px 20px;
    background-color: #2c3e50;
    color: #fff;
    font-size: 0.8rem;
}

#refresh-status {
    font-style: italic;
}
/* Updated table style*/
/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */
table {
    width: 100%;              /* Make table use full container width */
    border-collapse: separate; /* Allow spacing between cells */
    border-spacing: 8px;      /* Add space between columns */
    margin: 20px 0;           /* Add some margin around the table */
}

th, td {
    padding: 12px 16px;       /* Add padding inside cells */
    font-size: 1.1rem;        /* Increase text size */
}

th {
    font-size: 1.2rem;        /* Larger text for headers */
    font-weight: 700;         /* Make headers bold */
    background-color: #34495e; /* Match the blue theme */
    color: white;             /* White text for headers */
}

/* Add alternating row colors */
tr:nth-child(even) {
    background-color: #f5f7fa; /* Light grey for even rows */
}

/* Add hover effect for better interaction */
tbody tr:hover {
    background-color: #edf2f7;
}

/* Ensure text alignment */
td, th {
    text-align: left;
    vertical-align: middle;
}
/* ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ */


/* Responsive design */
@media (max-width: 768px) {
    .race-timer {
        font-size: 2rem;
    }
    
    .results-table th,
    .results-table td {
        padding: 8px;
    }
}""")
    
    # Create script.js
    js_path = os.path.join(web_dir, 'script.js')
    if not os.path.exists(js_path):
        with open(js_path, 'w') as f:
            f.write("""// Global variables
let refreshInterval;
let currentData = null;

// DOM elements
const tabButtons = document.querySelectorAll('.tab-button');
const tabContents = document.querySelectorAll('.tab-content');
const raceTimer = document.getElementById('race-timer');
const raceStatus = document.getElementById('race-status');
const statusIndicator = document.getElementById('status-indicator');
const standingsBody = document.getElementById('standings-body');
const lapTimesBody = document.getElementById('lap-times-body');
const refreshStatus = document.getElementById('refresh-status');

// Initialize page
document.addEventListener('DOMContentLoaded', () => {
    // Setup tab switching
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabName = button.getAttribute('data-tab');
            switchTab(tabName);
        });
    });

    // Start data refresh
    startRefreshing();
});

// Function to switch tabs
function switchTab(tabName) {
    tabButtons.forEach(btn => {
        if (btn.getAttribute('data-tab') === tabName) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });

    tabContents.forEach(content => {
        if (content.id === tabName) {
            content.classList.add('active');
        } else {
            content.classList.remove('active');
        }
    });
}

// Function to start refreshing data
function startRefreshing() {
    // Immediate fetch
    fetchRaceData();
    
    // Then set interval for regular updates
    refreshInterval = setInterval(fetchRaceData, 1000);
}

// Function to fetch race data from server
function fetchRaceData() {
    refreshStatus.textContent = 'Refreshing...';
    
    fetch('/api/race-data')
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            currentData = data;
            updateDisplay(data);
            refreshStatus.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
        })
        .catch(error => {
            console.error('Error fetching race data:', error);
            refreshStatus.textContent = `Error: ${error.message}`;
        });
}

// Function to update the display with new data
function updateDisplay(data) {
    // Update race status
    if (data.active) {
        raceStatus.textContent = 'Race in progress';
        statusIndicator.classList.add('active');
    } else {
        raceStatus.textContent = data.elapsed > 0 ? 'Race finished' : 'Waiting for race to start';
        statusIndicator.classList.remove('active');
    }
    
    // Update timer
    raceTimer.textContent = data.elapsed_formatted;
    
    // Update standings
    updateStandings(data);
    
    // Update lap times
    updateLapTimes(data);
}

// Function to update the standings table
function updateStandings(data) {
    // Clear the table
    standingsBody.innerHTML = '';
    
    if (!data.racers || data.racers.length === 0) {
        standingsBody.innerHTML = '<tr><td colspan="4">No racers registered</td></tr>';
        return;
    }
    
    // Sort racers by position, then by laps (descending)
    const sortedRacers = [...data.racers].sort((a, b) => {
        if (a.position > 0 && b.position > 0) {
            return a.position - b.position;
        }
        if (a.position > 0) return -1;
        if (b.position > 0) return 1;
        if (a.laps !== b.laps) return b.laps - a.laps;
        return a.finish_time - b.finish_time;
    });
    
    // Add each racer to the table
    sortedRacers.forEach(racer => {
        const row = document.createElement('tr');
        
        const positionCell = document.createElement('td');
        positionCell.textContent = racer.position > 0 ? racer.position : '-';
        
        const nameCell = document.createElement('td');
        nameCell.textContent = racer.name;
        
        const lapsCell = document.createElement('td');
        lapsCell.textContent = racer.laps;
        
        const timeCell = document.createElement('td');
        timeCell.textContent = racer.finished ? racer.finish_time_formatted : '-';
        
        row.appendChild(positionCell);
        row.appendChild(nameCell);
        row.appendChild(lapsCell);
        row.appendChild(timeCell);
        
        standingsBody.appendChild(row);
    });
}

// Function to update the lap times table
function updateLapTimes(data) {
    // Clear the table
    lapTimesBody.innerHTML = '';
    
    if (!data.racers || data.racers.length === 0) {
        lapTimesBody.innerHTML = '<tr><td colspan="4">No lap times recorded</td></tr>';
        return;
    }
    
    // Create rows for each lap time
    let hasLaps = false;
    
    data.racers.forEach(racer => {
        if (racer.lap_times && racer.lap_times.length > 0) {
            hasLaps = true;
            
            racer.lap_times.forEach((lap, index) => {
                const row = document.createElement('tr');
                
                const nameCell = document.createElement('td');
                nameCell.textContent = racer.name;
                
                const lapNumberCell = document.createElement('td');
                lapNumberCell.textContent = index + 1;
                
                const lapTimeCell = document.createElement('td');
                lapTimeCell.textContent = lap.formatted;
                
                // Calculate total time (sum of all laps up to this one)
                const totalTime = racer.lap_times
                    .slice(0, index + 1)
                    .reduce((sum, curr) => sum + curr.raw, 0);
                
                const totalTimeCell = document.createElement('td');
                totalTimeCell.textContent = formatTime(totalTime);
                
                row.appendChild(nameCell);
                row.appendChild(lapNumberCell);
                row.appendChild(lapTimeCell);
                row.appendChild(totalTimeCell);
                
                lapTimesBody.appendChild(row);
            });
        }
    });
    
    if (!hasLaps) {
        lapTimesBody.innerHTML = '<tr><td colspan="4">No lap times recorded yet</td></tr>';
    }
}

// Helper function to format time (fallback if server format fails)
function formatTime(seconds) {
    if (!seconds || seconds <= 0) return '0:00:00.000';
    
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    return `${hours}:${String(minutes).padStart(2, '0')}:${secs.toFixed(3).padStart(6, '0')}`;
}""")

def start_server(port=8000):
    """Start the web server on the specified port"""
    global _server, _server_thread, _server_port
    
    if _server_thread and _server_thread.is_alive():
        logger.warning("Web server is already running")
        return False
    
    # Create web files if they don't exist
    create_web_files()
    
    # Set up server
    _server_port = port
    handler = RaceDataHandler
    
    try:
        # Create a directory to serve files from
        web_dir = os.path.join(os.path.dirname(__file__), 'web')
        
        # Need to change the working directory to serve files correctly
        original_dir = os.getcwd()
        os.chdir(web_dir)
        
        # Create server
        _server = socketserver.TCPServer(("", port), handler)
        
        # Start server in a separate thread
        _server_thread = threading.Thread(target=_server.serve_forever, daemon=True)
        _server_thread.start()
        
        # Change back to original directory
        os.chdir(original_dir)
        
        logger.info(f"Web server started on port {port}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to start web server: {e}")
        return False

def stop_server():
    """Stop the web server"""
    global _server, _server_thread
    
    if _server:
        try:
            _server.shutdown()
            _server.server_close()
            logger.info("Web server stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping web server: {e}")
    
    return False

def get_server_url():
    """Get the URL for the web server"""
    global _server_port
    
    # Try to get the actual IP address for the machine
    import socket
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return f"http://{ip}:{_server_port}"
    except:
        # Fallback
        return f"http://localhost:{_server_port}"
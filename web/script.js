// script.js
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
        standingsBody.innerHTML = '<tr><td colspan="8">No racers in the race.</td></tr>';
        return;
    }
    
    // Debug: Check the first racer's data structure
    if (racers.length > 0) {
        console.log("First racer in standings:", racers[0]);
    }
    
    // Add each racer to the table
    racers.forEach(racer => {
        const row = document.createElement('tr');
        
        // Use the formatted values from the server
        const position = racer.position > 0 ? racer.position : '-';
        const gap = racer.gap || '-';
        const bestLap = racer.best_lap || '-';
        const lastLap = racer.last_lap || '-';
        const totalTime = racer.total_time || racer.finish_time_formatted || '-';
        
        // Determine racer status and create status indicator
        let statusIndicator = '';
        let statusClass = '';
        
        if (racer.laps === 0) {
            statusClass = 'not-started';
            statusIndicator = '<div class="racer-status not-started" title="Not Started"></div>';
        } else if (racer.finished || (racer.laps >= racer.target_laps)) {
            statusClass = 'finished';
            statusIndicator = '<div class="racer-status finished" title="Finished"></div>';
        } else {
            statusClass = 'racing';
            statusIndicator = '<div class="racer-status racing" title="Racing"></div>';
        }
        
        row.innerHTML = `
            <td>${statusIndicator}</td>    
            <td>${position}</td>
            <td>${racer.name}</td>
            <td>${racer.laps}</td>
            <td>${gap}</td>
            <td>${bestLap}</td>
            <td>${lastLap}</td>
            <td>${totalTime}</td>
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

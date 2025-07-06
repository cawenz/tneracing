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
        standingsBody.innerHTML = '<tr><td colspan="4">No racers in the race.</td></tr>';
        return;
    }
    // Sort racers by position, handling cases where position might be 0 or undefined
    racers.sort((a, b) => {
        const posA = a.position > 0 ? a.position : Infinity;
        const posB = b.position > 0 ? b.position : Infinity;
        if (posA === posB) { // If positions are same, sort by laps (more laps is better)
            return (b.laps || 0) - (a.laps || 0);
        }
        return posA - posB;
    });

racers.forEach(racer => {
    const row = document.createElement('tr');
    row.innerHTML = `
        <td>${racer.position > 0 ? racer.position : '-'}</td>
        <td>${racer.name || 'N/A'}</td>
        <td>${racer.laps || 0}</td>
        <td>${racer.finish_time && racer.finish_time > 0 ? 
            formatTimeNoHours(racer.finish_time) : 
            (racer.laps > 0 && raceTimer.textContent !== '0:00:00.000' ? 'Running' : '-')}</td>
    `;
    standingsBody.appendChild(row);
});
}

function updateLapTimes(data) {
    lapTimesBody.innerHTML = '';
    let hasLapData = false;

    if (data.racers && data.racers.length > 0) {
        let allLapEvents = [];
        data.racers.forEach(racer => {
            if (racer.lap_times && racer.lap_times.length > 0) {
                hasLapData = true;
                let previousTime = 0; // Track previous lap's cumulative time
                racer.lap_times.forEach((lap, index) => {
                    allLapEvents.push({
                        racerName: racer.name || 'N/A',
                        lapNumber: index + 1,
                        cumulativeTimeRaw: lap.raw, // Make sure this is a number
                        cumulativeTimeFormatted: lap.formatted,
                        previousCumulativeTimeRaw: previousTime
                    });
                    previousTime = lap.raw; // Update previous time for next lap
                });
            }
        });

        // Sort all lap events by cumulative time
        allLapEvents.sort((a, b) => b.cumulativeTimeRaw - a.cumulativeTimeRaw);

        allLapEvents.forEach(event => {
            const individualLapTime = event.cumulativeTimeRaw - event.previousCumulativeTimeRaw;
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${event.racerName}</td>
                <td>${event.lapNumber}</td>
                <td>${formatLapTime(individualLapTime)}</td>
                <td>${formatTimeNoHours(event.cumulativeTimeRaw)}</td>
            `;
            lapTimesBody.appendChild(row);
        });
    }

    if (!hasLapData) {
        lapTimesBody.innerHTML = '<tr><td colspan="4">No lap times recorded yet.</td></tr>';
    }
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

function fetchRaceData() {
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
}

// Initial fetch and set interval
fetchRaceData();
setInterval(fetchRaceData, 1000); // Fetch every 1 second

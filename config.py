import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('rfid_race_timer')

# RFID Reader Configuration
READER_IP = '192.168.8.200' # Replace with the reader's correct IP address
READER_PORT = 5084 
DELAY_SECONDS = 5 # Minimum time between readings of the same tag
DEFAULT_NUM_LAPS = 10 # Default number of laps

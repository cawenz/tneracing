import threading
from config import DEFAULT_NUM_LAPS, READER_IP # Import constants

# Global variables related to shared application state
ALLOWED_TAGS = [] # Will be populated with selected racer tags [1, 3, 4]
last_read_times = {} # Track when each tag was last read [1, 8, 9]
stop_event = threading.Event() # Event to signal reader thread to stop [1, 10-12]
race_active = False 
race_start_time = 0
racers_data = {} # Store lap times, race position etc.
num_laps = DEFAULT_NUM_LAPS # From config 
reader_connected = False 
reader_client = None # Instance of LLRPReaderClient [1] (can be managed locally within rfid_reader.py too)
DELAY_SECONDS = 5
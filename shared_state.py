import threading
from datetime import datetime
import random
from config import DEFAULT_NUM_LAPS, READER_IP # Import constants

# Global variables related to shared application state
ALLOWED_TAGS = [] # Will be populated with selected racer tags
last_read_times = {} # Track when each tag was last read
stop_event = threading.Event() # Event to signal reader thread to stop
race_active = False 
race_start_time = 0
race_start_datetime = None  # NEW: Store the actual datetime when race started
race_name = None  # NEW: Store the race name
racers_data = {} # Store lap times, race position etc.
num_laps = DEFAULT_NUM_LAPS # From config 
reader_connected = False 
reader_client = None
DELAY_SECONDS = 5

# Race mode settings
RACE_MODE_START_LINE = "start_line"
RACE_MODE_ROLLING = "rolling"
race_mode = RACE_MODE_START_LINE  # Default to start line race mode

# UPDATE shared_state.py - Replace the generate_random_race_name function

def generate_random_race_name():
    """Generate a random race name if none is set"""
    # Speed-related adjectives
    adjectives = [
        "Blazing", "Lightning", "Speeding", "Racing", "Dashing", "Rushing", 
        "Zooming", "Bolting", "Sprinting", "Flying", "Streaking", "Whizzing",
        "Rocketing", "Zipping", "Darting", "Charging", "Hurling", "Careening",
        "Swooping", "Surging", "Blitzing", "Flashing", "Shooting", "Bombing"
    ]
    
    # Interesting but recognizable animals
    animals = [
        "Pangolin", "Quokka", "Axolotl", "Tapir", "Numbat", "Binturong",
        "Aardvark", "Okapi", "Capybara", "Narwhal", "Platypus", "Wombat",
        "Fennec", "Jerboa", "Tenrec", "Dugong", "Meerkat", "Mongoose",
        "Lemur", "Wallaby", "Ocelot", "Serval", "Margay", "Caracal",
        "Chinchilla", "Vicuna", "Alpaca", "Llama", "Pika", "Quetzal",
        "Toucan", "Hornbill", "Kookaburra", "Cassowary", "Shoebill", "Fossa",
        "Civet", "Genet", "Coati", "Kinkajou", "Olingo", "Potto"
    ]
    
    # Random number between 1 and 999
    number = random.randint(1, 999)
    
    # Format: adjective_animal_number
    return f"{random.choice(adjectives)}_{random.choice(animals)}_{number}"
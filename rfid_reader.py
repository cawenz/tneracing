# rfid_reader.py - New sllurp (LLRPReaderClient) Version
import time
import threading
from config import READER_IP, READER_PORT, DELAY_SECONDS, logger
import shared_state

# Import the new sllurp (no Twisted) - CORRECTED IMPORT
try:
    from sllurp import llrp
    SLLURP_AVAILABLE = True
    LLRPReaderClient = llrp.LLRPReaderClient
    LLRPReaderConfig = llrp.LLRPReaderConfig
    logger.info("Successfully imported sllurp with LLRPReaderClient")
except ImportError as e:
    logger.error(f"New sllurp not available: {e}")
    SLLURP_AVAILABLE = False
    class LLRPReaderClient:  # Dummy class to prevent crashes
        def __init__(self, *args, **kwargs): pass
    class LLRPReaderConfig:  # Dummy class to prevent crashes
        def __init__(self, *args, **kwargs): pass

# Internal module-level references
_monitor_ref = None
_reader_client = None

def set_monitor_reference(monitor_instance):
    """Sets the reference to the main monitor GUI for callbacks."""
    global _monitor_ref
    _monitor_ref = monitor_instance

def process_tag_data(tag_data):
    """Process tag data from the reader"""
    try:
        # Extract EPC from tag data (new sllurp format)
        epc = tag_data.get('EPC', None)
        if not epc:
            logger.warning("No EPC data in tag")
            return
        
        logger.info(f"Raw EPC data: {epc} (type: {type(epc)})")  # DEBUG
        
        # Convert to consistent hex string format
        if isinstance(epc, bytes):
            # Raw bytes - try to decode as ASCII first, then fall back to hex
            try:
                # Try to decode as ASCII (this is what we want for your tags)
                tag_id = epc.decode('ascii').lower()
                logger.info(f"Decoded bytes as ASCII: {tag_id}")  # DEBUG
            except UnicodeDecodeError:
                # If ASCII decode fails, convert to hex
                tag_id = epc.hex().lower()
                logger.info(f"Converted bytes to hex: {tag_id}")  # DEBUG
        else:
            # String data - check if it's ASCII-encoded hex
            epc_str = str(epc).lower()
            logger.info(f"EPC as string: {epc_str} (length: {len(epc_str)})")  # DEBUG
            
            # Check if this looks like ASCII-encoded hex (double the expected length)
            if len(epc_str) == 48 and all(c in '0123456789abcdef' for c in epc_str):
                logger.info("EPC matches ASCII-encoded hex criteria, converting...")  # DEBUG
                try:
                    # This is ASCII-encoded hex - convert it back
                    decoded_bytes = bytes.fromhex(epc_str)
                    logger.info(f"Decoded bytes: {decoded_bytes}")  # DEBUG
                    # Decode the bytes as ASCII to get the original hex string
                    tag_id = decoded_bytes.decode('ascii').lower()
                    logger.info(f"Converted ASCII-encoded hex: {epc_str} -> {tag_id}")  # DEBUG
                except Exception as e:
                    logger.warning(f"Failed to convert ASCII-encoded hex: {e}")
                    tag_id = epc_str
            else:
                logger.info("EPC does not match ASCII-encoded hex criteria, using as-is")  # DEBUG
                # Normal hex string (or other format)
                tag_id = epc_str
        
        logger.info(f"Final tag_id: {tag_id}")  # DEBUG
        logger.info(f"Read tag: {tag_id} (converted), race_active: {shared_state.race_active}, in allowed tags: {tag_id in shared_state.ALLOWED_TAGS}")
        logger.info(f"Current ALLOWED_TAGS: {shared_state.ALLOWED_TAGS}")  # DEBUG
        
        # Only process if race is active and tag is allowed
        if not shared_state.race_active:
            logger.debug(f"Ignoring tag: {tag_id} (race not active)")
            return
            
        if shared_state.ALLOWED_TAGS and tag_id not in shared_state.ALLOWED_TAGS:
            logger.debug(f"Ignoring tag: {tag_id} (not in allowed list)")
            logger.debug(f"Allowed tags are: {shared_state.ALLOWED_TAGS}")
            return
            
        # Check timing to prevent duplicate reads
        current_time = time.time()
        if tag_id in shared_state.last_read_times:
            if (current_time - shared_state.last_read_times[tag_id] < shared_state.DELAY_SECONDS):
                logger.debug(f"Ignoring tag: {tag_id} (too soon since last read)")
                return
        
        shared_state.last_read_times[tag_id] = current_time
        
        # Process the tag for the race
        if tag_id in shared_state.racers_data:
            racer = shared_state.racers_data[tag_id]
            
            # Check if racer has already finished
            if racer.get("finished", False):
                logger.debug(f"Ignoring tag read for finished racer {racer['name']} (ID: {tag_id})")
                return
            
            lap_time = current_time - shared_state.race_start_time
            
            # Handle different race modes
            if shared_state.race_mode == shared_state.RACE_MODE_START_LINE:
                # Start Line Race Mode Logic
                if not racer["has_started"]:
                    # First read - record start time but don't count as lap
                    racer["start_time"] = lap_time
                    racer["has_started"] = True
                    logger.info(f"Racer {racer['name']} crossed start line at {lap_time:.2f}s")
                    return
                
                # Check delay since last read
                last_time = racer["lap_times"][-1] if racer["lap_times"] else racer["start_time"]
                if lap_time - last_time < shared_state.DELAY_SECONDS:
                    logger.debug(f"Ignoring too fast lap for {racer['name']} (ID: {tag_id})")
                    return
                    
                # This is a legitimate lap completion
                racer["laps"] += 1
                racer["lap_times"].append(lap_time)
                
            else:
                # Rolling Start Mode Logic
                if not racer["has_started"]:
                    # First read - this is the START of lap 1
                    racer["rolling_start_time"] = lap_time
                    racer["has_started"] = True
                    logger.info(f"Racer {racer['name']} started lap 1 at {lap_time:.2f}s (rolling start)")
                    return
                
                # Check delay since last read
                last_time = racer["lap_times"][-1] if racer["lap_times"] else racer["rolling_start_time"]
                if lap_time - last_time < shared_state.DELAY_SECONDS:
                    logger.debug(f"Ignoring too fast lap for {racer['name']} (ID: {tag_id})")
                    return
                
                # This is a lap completion
                racer["laps"] += 1
                racer["lap_times"].append(lap_time)

            logger.info(f"Racer {racer['name']} completed lap {racer['laps']} at {lap_time:.2f}s")
            
            # Check if racer finished the race
            if racer["laps"] >= shared_state.num_laps and not racer["finished"]:
                racer["finished"] = True
                
                # Calculate finish time based on race mode
                if shared_state.race_mode == shared_state.RACE_MODE_ROLLING:
                    racer["finish_time"] = lap_time - racer["rolling_start_time"]
                else:
                    racer["finish_time"] = lap_time - racer["start_time"]
                
                # Calculate position
                position = 1
                for r in shared_state.racers_data.values():
                    if r["finished"] and r != racer:
                        position += 1
                racer["position"] = position
                logger.info(f"Racer {racer['name']} finished in position {position} with total time {racer['finish_time']:.2f}s")
            
            # Check for race ending
            if not any(not r.get("has_started", False) for r in shared_state.racers_data.values()):
                if all(r.get("finished", False) for r in shared_state.racers_data.values()) and shared_state.race_active:
                    logger.info("All racers have finished the race - ending race")
                    if _monitor_ref and hasattr(_monitor_ref, 'root'):
                        try:
                            _monitor_ref.root.after(0, _monitor_ref.stop_race)
                        except Exception as e:
                            logger.error(f"Could not stop race: {e}")
                            
    except Exception as e:
        logger.error(f"Error processing tag data: {e}", exc_info=True)

def tag_report_callback(reader, tags):
    """Callback function for tag reports - new sllurp format"""
    if tags:
        logger.info(f"Received {len(tags)} tags in report")
        for tag in tags:
            process_tag_data(tag)
    else:
        logger.debug("Received empty tag report")

def connection_callback(reader, success):
    """Callback for connection events"""
    global _monitor_ref
    if success:
        logger.info("Successfully connected to RFID reader")
        if _monitor_ref:
            _monitor_ref.root.after(0, _monitor_ref.set_connected)
            _monitor_ref.root.after(0, lambda: _monitor_ref.update_status("Connected to reader. Ready to start race."))
    else:
        logger.error("Failed to connect to RFID reader")
        if _monitor_ref:
            _monitor_ref.root.after(0, lambda: _monitor_ref.update_status("Connection failed", is_error=True))
            _monitor_ref.root.after(3000, _monitor_ref.reset_connection_ui)

def start_rfid_reader():
    """Start the RFID reader connection using new sllurp"""
    global _reader_client
    
    if not SLLURP_AVAILABLE:
        error_msg = "sllurp library not available"
        logger.error(error_msg)
        if _monitor_ref:
            _monitor_ref.root.after(0, lambda: _monitor_ref.update_status(error_msg, is_error=True))
        return
    
    # Clear events
    shared_state.stop_event.clear()
    
    if _monitor_ref:
        _monitor_ref.root.after(0, lambda: _monitor_ref.update_status("Connecting to RFID reader..."))
    
    try:
        logger.info(f"Connecting to reader at {shared_state.READER_IP}")
        
        # Create reader configuration
        config = LLRPReaderConfig()
        config.reset_on_connect = True
        config.start_inventory = True
        config.antennas = [1, 2, 3, 4]
        config.tx_power = {1: 30, 2: 30, 3: 30, 4: 30}  # Full power
        config.session = 2
        config.mode_identifier = 2
        config.tag_population = 4
        config.report_every_n_tags = 1
        config.tag_content_selector = {
            'EnableAntennaID': True,
            'EnablePeakRSSI': True,
            'EnableTagSeenCount': True
        }
        
        # Create and configure reader client
        _reader_client = LLRPReaderClient(shared_state.READER_IP, READER_PORT, config)
        
        # Add callbacks
        _reader_client.add_tag_report_callback(tag_report_callback)
        
        # Connect to the reader
        _reader_client.connect()
        
        # Notify successful connection
        if _monitor_ref:
            _monitor_ref.root.after(0, _monitor_ref.set_connected)
            _monitor_ref.root.after(0, lambda: _monitor_ref.update_status("Connected to reader. Ready to start race."))
        
        logger.info("RFID reader connected successfully")
        
    except Exception as e:
        error_msg = f"Error connecting to reader: {e}"
        logger.error(error_msg, exc_info=True)
        if _monitor_ref:
            _monitor_ref.root.after(0, lambda: _monitor_ref.update_status(error_msg, is_error=True))
            _monitor_ref.root.after(3000, _monitor_ref.reset_connection_ui)

def disconnect_rfid_reader():
    """Disconnect from the RFID reader"""
    global _reader_client
    
    logger.info("Disconnecting from RFID reader...")
    
    # Signal stop
    shared_state.stop_event.set()
    
    # Disconnect the reader client
    if _reader_client:
        try:
            if _reader_client.is_alive():
                logger.info("Stopping reader client...")
                _reader_client.disconnect()
                
                # Wait for clean disconnection
                _reader_client.join(timeout=3.0)
                
                if _reader_client.is_alive():
                    logger.warning("Reader client did not stop within timeout")
                else:
                    logger.info("Reader client stopped successfully")
            
            _reader_client = None
            logger.info("Reader client cleaned up")
            
        except Exception as e:
            logger.error(f"Error disconnecting reader: {e}")
            _reader_client = None
    
    # Update UI
    if _monitor_ref:
        _monitor_ref.root.after(0, _monitor_ref.reset_connection_ui)
    
    logger.info("RFID reader disconnected")

def force_reader_reset():
    """Force a reader reset using external command"""
    import subprocess
    
    try:
        logger.info("Attempting to reset reader using sllurp command")
        result = subprocess.run(
            ['sllurp', 'reset', shared_state.READER_IP],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info("Successfully reset reader")
            return True
        else:
            logger.warning(f"Reader reset failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        logger.warning("Reader reset command timed out")
    except FileNotFoundError:
        logger.warning("sllurp command not found")
    except Exception as e:
        logger.error(f"Error resetting reader: {e}")
    
    return False
# rfid_reader.py
import threading
import time
from twisted.internet import reactor # Required for sllurp [2, 11, 51]
from sllurp.llrp import LLRPReaderConfig, LLRPReaderClient # Specific sllurp imports [48, 50]
from config import READER_IP, READER_PORT, DELAY_SECONDS, logger # Import constants and logger [2, 8, 49]
import shared_state # Import shared_state to access/modify global race data [8, 9, 11, 45]

# Internal module-level reference to the main RFIDTagMonitor for UI updates
_monitor_ref = None

def set_monitor_reference(monitor_instance):
    """Sets the reference to the main monitor GUI for callbacks."""
    global _monitor_ref
    _monitor_ref = monitor_instance

def process_tag_data(tag_data):
    try:
        epc_data = tag_data.get('EPC', None)
        if not epc_data:
            logger.warning("No EPC data in tag")
            return
        
        if isinstance(epc_data, bytes):
            tag_id_hex = epc_data.hex().lower()
            try:
                tag_id = ''.join(chr(b) for b in epc_data if 32 <= b < 127)
                if not tag_id or len(tag_id) < len(tag_id_hex) / 2:
                    tag_id = tag_id_hex
            except Exception as e:
                logger.warning(f"Failed to convert ASCII hex: {e}, using raw hex")
                tag_id = tag_id_hex
        else:
            tag_id = str(epc_data).lower()
        
        logger.info(f"Extracted tag_id: {tag_id}, race_active: {shared_state.race_active}, in allowed tags: {tag_id in shared_state.ALLOWED_TAGS}")
        
        if shared_state.race_active and (not shared_state.ALLOWED_TAGS or tag_id in shared_state.ALLOWED_TAGS):
            current_time = time.time()
            if tag_id in shared_state.last_read_times and \
               (current_time - shared_state.last_read_times[tag_id] < shared_state.DELAY_SECONDS):
                logger.debug(f"Ignoring tag: {tag_id} (too soon since last read)")
                return
            
            shared_state.last_read_times[tag_id] = current_time
            antenna = tag_data.get('AntennaID', 0)
            rssi = tag_data.get('PeakRSSI', 0)
            logger.info(f"Read tag: {tag_id} on antenna {antenna} with RSSI {rssi}")
            
            if tag_id in shared_state.racers_data:
                racer = shared_state.racers_data[tag_id]
                lap_time = current_time - shared_state.race_start_time
                
                # Handle different race modes
                if shared_state.race_mode == shared_state.RACE_MODE_START_LINE:
                    # Start Line Race Mode Logic
                    if not racer["has_started"]:
                        # First read - record start time but don't count as lap
                        racer["start_time"] = lap_time
                        racer["has_started"] = True
                        logger.info(f"Racer {racer['name']} crossed start line at {lap_time:.2f}s")
                        return  # Don't process further for start line crossing
                    
                    # Check delay since last read (start time or last lap)
                    last_time = racer["lap_times"][-1] if racer["lap_times"] else racer["start_time"]
                    if lap_time - last_time < shared_state.DELAY_SECONDS:
                        logger.debug(f"Ignoring too fast lap for {racer['name']} (ID: {tag_id})")
                        return
                        
                    # This is a legitimate lap completion
                    racer["laps"] += 1
                    racer["lap_times"].append(lap_time)
                    
                else:
                    # Rolling Start Mode Logic - CORRECTED
                    if not racer["has_started"]:
                        # First read - this is the START of lap 1
                        racer["rolling_start_time"] = lap_time
                        racer["has_started"] = True
                        logger.info(f"Racer {racer['name']} started lap 1 at {lap_time:.2f}s (rolling start)")
                        return  # Don't count this as a completed lap yet
                    
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
                        # For rolling start, total time is from first tag read to last lap completion
                        racer["finish_time"] = lap_time - racer["rolling_start_time"]
                    else:
                        # For start line, total time is from start line to last lap completion
                        racer["finish_time"] = lap_time - racer["start_time"]
                    
                    # Calculate position
                    position = 1
                    for r in shared_state.racers_data.values():
                        if r["finished"] and r != racer:
                            position += 1
                    racer["position"] = position
                    logger.info(f"Racer {racer['name']} finished in position {position} with total time {racer['finish_time']:.2f}s")
                
                # Check for race ending - only if all racers have started
                if not any(not r.get("has_started", False) for r in shared_state.racers_data.values()):
                    # All racers have started, check if all have finished
                    if all(r.get("laps", 0) >= shared_state.num_laps for r in shared_state.racers_data.values()) and shared_state.race_active:
                        logger.info("All racers have completed all required laps - ending race")
                        if _monitor_ref and hasattr(_monitor_ref, 'root'):
                            try:
                                _monitor_ref.root.after(0, _monitor_ref.stop_race)
                            except Exception as e:
                                logger.error(f"Could not stop race: {e}")
        else:
            logger.debug(f"Ignoring tag: {tag_id} (not in allowed list or race not active)")
    except Exception as e:
        logger.error(f"Error processing tag data: {e}", exc_info=True)


def tag_seen_callback(reader, tags):
    """Callback function for tag reports - will be called by the reader client"""
    if tags:
        logger.info(f"Received {len(tags)} tags in report")
        for tag in tags:
            process_tag_data(tag) # Call the local function
    else:
        logger.debug("Received empty tag report")

def handle_event(reader_client, event):
    """Handle events from the reader including connection events"""
    global _monitor_ref # Access _monitor_ref
    if 'ConnectionAttemptEvent' in event:
        connection_event = event['ConnectionAttemptEvent'] 
        logger.info(f"Connection Event: {connection_event}") 
        if connection_event.get('Status') == 'Success': 
            if _monitor_ref:
                _monitor_ref.root.after(0, _monitor_ref.set_connected) 
                _monitor_ref.root.after(0, lambda: _monitor_ref.update_status("Connected to reader. Ready to start race.")) 
        else: 
            if _monitor_ref:
                _monitor_ref.root.after(0, lambda: _monitor_ref.update_status(f"Connection failed: {connection_event.get('Status')}", is_error=True))
    elif 'ReaderEventNotificationData' in event: 
        logger.info("Reader notification received") 
        if _monitor_ref:
            _monitor_ref.root.after(0, lambda: _monitor_ref.update_status("Reader event received")) 
    else:
        logger.info(f"Received event: {event}")

# Keep _reader_client_instance within this module as it's the specific LLRP client
_reader_client_instance = None

def start_rfid_reader():
    """Start the RFID reader - using the correct sllurp 2.0.1 API"""
    global _reader_client_instance, _monitor_ref # Use internal module global

    if _monitor_ref:
        _monitor_ref.root.after(0, lambda: _monitor_ref.update_status("Initializing RFID reader connection..."))

    try:
        logger.info(f"Connecting to reader at {shared_state.READER_IP}") # Use constant from config
        if _monitor_ref:
            _monitor_ref.root.after(0, lambda: _monitor_ref.update_status(f"Connecting to reader at {shared_state.READER_IP}..."))

        config = LLRPReaderConfig() 
        config.reset_on_connect = True 
        config.start_inventory = True 
        config.antennas = [1, 2, 3, 4]
        config.tx_power = {1: 30, 2: 30, 3: 30, 4: 30}
        config.session = 2 
        config.mode_identifier = 2 # Miller-4 [50]
        config.tag_population = 4 
        config.report_every_n_tags = 1 
        config.tag_content_selector = { 
            'EnableAntennaID': True, 'EnablePeakRSSI': True, 'EnableTagSeenCount': True
        }

        _reader_client_instance = LLRPReaderClient(shared_state.READER_IP, READER_PORT, config) # Create instance [50]
        _reader_client_instance.add_tag_report_callback(tag_seen_callback) 
        _reader_client_instance.add_event_callback(handle_event)

        if _monitor_ref:
            _monitor_ref.root.after(0, lambda: _monitor_ref.update_status("Connecting to reader..."))

        _reader_client_instance.connect()

        def check_stop():
            if shared_state.stop_event.is_set(): # Use shared_state
                try:
                    if _reader_client_instance and _reader_client_instance.is_alive():
                        logger.info("Stopping inventory and disconnecting...")
                        _reader_client_instance.disconnect()
                except Exception as e:
                    logger.error(f"Error during disconnect: {e}")
                if reactor.running:
                    reactor.stop()
            else:
                reactor.callLater(0.5, check_stop)
        reactor.callLater(0.5, check_stop) 
        reactor.run(installSignalHandlers=0) # This blocks until reactor stops

    except Exception as e:
        error_msg = f"Error initializing RFID reader: {e}"
        logger.error(error_msg, exc_info=True)
        if _monitor_ref: 
            _monitor_ref.root.after(0, lambda: _monitor_ref.update_status(error_msg, is_error=True))
            # Reset the connection UI so user can try again
            _monitor_ref.root.after(3000, _monitor_ref.reset_connection_ui)

def disconnect_rfid_reader():
    """Function to be called from main app to initiate disconnection."""
    # This simply sets the stop_event, the actual disconnect happens in the reader thread
    shared_state.stop_event.set()
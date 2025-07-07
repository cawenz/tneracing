import sys
import os

print("--- PYTHON ENVIRONMENT DIAGNOSTICS ---")
print(f"Running from: {sys.executable}")
print("--- END DIAGNOSTICS ---\n")

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time

from config import logger, READER_IP, DEFAULT_NUM_LAPS # Import constants and logger from config [2, 52, 56]
import shared_state # Import shared_state to access/modify global race data [5-7, 10, 12-19, 44]
from race_timer import RaceTimer # Import RaceTimer class  
from racer_manager import RacerManager # Import RacerManager class [1]
from rfid_reader import start_rfid_reader, disconnect_rfid_reader, set_monitor_reference # Import reader functions [10, 62]
from data_exporter import RaceResultsExporter # Import RaceResultsExporter class  
from web_server import start_server, stop_server, get_server_url



class RFIDTagMonitor:
    def __init__(self, root):
        self.root = root
        self.race_timer = RaceTimer(self) # Pass 'self' (RFIDTagMonitor instance) to RaceTimer  
        # Pass references to shared_state and self to RacerManager
        self.racer_manager = RacerManager(root, self) 
        # Pass references to shared_state and self.race_timer to RaceResultsExporter
        self.results_exporter = RaceResultsExporter(shared_state, self.race_timer) # New line for exporter
        # Set the reference to this monitor instance for the RFID reader module
        set_monitor_reference(self)
        self.web_server_running = False
        self.update_results_interval = 1000  # Update every 1 second
        self.update_results()

        # Setup the user interface
        self.setup_ui()
        self.update_status("Application started. Please connect to reader and set up the race...")
        # Handle window close 
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_ui(self):
        # Setup the user interface without redundant Race Results boxes"""
        self.root.title("RFID Race Timer")  
        self.root.geometry("800x600")
    
        main_frame = ttk.Frame(self.root, padding=10)  
        main_frame.pack(fill=tk.BOTH, expand=True)  
    
        # Status label
        self.status_label = ttk.Label(main_frame, text="Starting application...", font=("Arial", 12))
        self.status_label.pack(anchor=tk.W, pady=10)  
    
        # RFID Reader Connection frame
        connection_frame = ttk.LabelFrame(main_frame, text="RFID Reader Connection")  
        connection_frame.pack(fill=tk.X, pady=5)  
    
        ip_frame = ttk.Frame(connection_frame)  
        ip_frame.pack(side=tk.LEFT, padx=10, pady=5)  
    
        ttk.Label(ip_frame, text="Reader IP:").pack(side=tk.LEFT, padx=5)  
        self.ip_var = tk.StringVar(value=READER_IP)
        ttk.Entry(ip_frame, textvariable=self.ip_var, width=15).pack(side=tk.LEFT)  
    
        # Connection buttons
        button_frame = ttk.Frame(connection_frame)  
        button_frame.pack(side=tk.LEFT, padx=10, pady=5)  
    
        self.connect_btn = ttk.Button(button_frame, text="Connect", command=self.connect_reader)  
        self.connect_btn.pack(side=tk.LEFT, padx=5)  
    
        self.disconnect_btn = ttk.Button(button_frame, text="Disconnect", 
                                     command=self.disconnect_reader, state=tk.DISABLED)  
        self.disconnect_btn.pack(side=tk.LEFT, padx=5)  
    
        # Connection status
        self.connection_status = ttk.Label(connection_frame, text="Not connected", foreground="red")
        self.connection_status.pack(side=tk.LEFT, padx=10)  
    
        # Race Timer display
        timer_frame = ttk.LabelFrame(main_frame, text="Race Timer")  
        timer_frame.pack(fill=tk.X, pady=5)  
    
        self.timer_display = ttk.Label(timer_frame, text="0:00:00.000", font=("Arial", 24, "bold"))  
        self.timer_display.pack(pady=10)  
    
        # Race control buttons
        control_frame = ttk.Frame(timer_frame)  
        control_frame.pack(pady=5)  
    
        self.start_button = ttk.Button(control_frame, text="Start Race", 
                                  command=self.start_race, state=tk.DISABLED)  
        self.start_button.pack(side=tk.LEFT, padx=5)  
    
        self.stop_button = ttk.Button(control_frame, text="Stop Race", 
                                 command=self.stop_race, state=tk.DISABLED)  
        self.stop_button.pack(side=tk.LEFT, padx=5)  
    
        # Race setup frame
        setup_frame = ttk.LabelFrame(main_frame, text="Race Setup")  
        setup_frame.pack(fill=tk.X, pady=5)  
    
        # Racer management button
        self.racer_mgr_button = ttk.Button(setup_frame, text="Manage Racers", 
                                     command=self.open_racer_manager)  
        self.racer_mgr_button.pack(side=tk.LEFT, padx=5, pady=5)  
    
        # Number of laps
        lap_frame = ttk.Frame(setup_frame)  
        lap_frame.pack(side=tk.LEFT, padx=5, pady=5)  
    
        ttk.Label(lap_frame, text="Number of Laps:").pack(side=tk.LEFT)  
        self.lap_var = tk.StringVar(value=str(DEFAULT_NUM_LAPS))
        ttk.Spinbox(lap_frame, from_=1, to=100, textvariable=self.lap_var, width=5).pack(side=tk.LEFT, padx=5)
    
        # Race info label
        self.race_info_label = ttk.Label(setup_frame, text="No racers selected")
        self.race_info_label.pack(side=tk.LEFT, padx=20)
    
        # Web server frame
        web_server_frame = ttk.LabelFrame(main_frame, text="Web Display")
        web_server_frame.pack(fill=tk.X, pady=5)
    
        self.web_server_btn = ttk.Button(
            web_server_frame,
            text="Start Web Display",
            command=self.toggle_web_server
        )
        self.web_server_btn.pack(side=tk.LEFT, padx=5, pady=5)
    
        self.web_url_label = ttk.Label(web_server_frame, text="")
        self.web_url_label.pack(side=tk.LEFT, padx=10)
    
        # Race Results frame - this is the single, correct implementation
        results_frame = ttk.LabelFrame(main_frame, text="Race Results")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
    
        # Results notebook
        self.results_notebook = ttk.Notebook(results_frame)
        self.results_notebook.pack(fill=tk.BOTH, expand=True)
    
        # Standings tab
        standings_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(standings_frame, text="Standings")

        self.standings_tree = ttk.Treeview(standings_frame, 
                                   columns=("position", "racer", "laps", "time"), 
                                   show="headings")
        self.standings_tree.heading("position", text="Position")
        self.standings_tree.heading("racer", text="Racer")
        self.standings_tree.heading("laps", text="Laps")
        self.standings_tree.heading("time", text="Time") # This now shows last lap's total time

        self.standings_tree.column("position", width=80)
        self.standings_tree.column("racer", width=250)
        self.standings_tree.column("laps", width=80)
        self.standings_tree.column("time", width=120)

# ... (rest of the setup)
    
        results_scrollbar = ttk.Scrollbar(standings_frame, orient="vertical", command=self.standings_tree.yview)
        self.standings_tree.configure(yscrollcommand=results_scrollbar.set)
    
        self.standings_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        results_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
        # Lap Times tab
        lap_times_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(lap_times_frame, text="Lap Times")
    
        self.lap_times_tree = ttk.Treeview(lap_times_frame, 
                                      columns=("racer", "lap", "lap_time", "total_time"), 
                                      show="headings")
        self.lap_times_tree.heading("racer", text="Racer")
        self.lap_times_tree.heading("lap", text="Lap")
        self.lap_times_tree.heading("lap_time", text="Lap Time")
        self.lap_times_tree.heading("total_time", text="Total Time")
    
        self.lap_times_tree.column("racer", width=200)
        self.lap_times_tree.column("lap", width=50)
        self.lap_times_tree.column("lap_time", width=100)
        self.lap_times_tree.column("total_time", width=100)
    
        lap_times_scrollbar = ttk.Scrollbar(lap_times_frame, orient="vertical", command=self.lap_times_tree.yview)
        self.lap_times_tree.configure(yscrollcommand=lap_times_scrollbar.set)
    
        self.lap_times_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lap_times_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Section above and below are related to web sockets

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def toggle_web_server(self):
        if not self.web_server_running:
        # Try to start the server
            if start_server():
                self.web_server_running = True
                self.web_server_btn.config(text="Stop Web Display")
            
            # Get and display the URL
                url = get_server_url()
                self.web_url_label.config(
                    text=f"Web display running at: {url}",
                    foreground="blue"
            )
            
            # Show a message to the user
                messagebox.showinfo(
                    "Web Display Started",
                    f"Web display has been started!\n\nSpectators can view race results at:\n{url}"
                )
                self.update_status(f"Web display started at {url}")
            else:
             messagebox.showerror(
                "Web Display Error",
                "Failed to start web display. See log for details."
            )
        else:
        # Try to stop the server
            if stop_server():
                self.web_server_running = False
                self.web_server_btn.config(text="Start Web Display")
                self.web_url_label.config(
                    text="Web display not running",
                    foreground="gray"
                )
                self.update_status("Web display stopped")
            else:
                messagebox.showerror(
                "Web Display Error",
                "Failed to stop web display. See log for details."
            )
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    def connect_reader(self):
        """Connect to the RFID reader"""
        shared_state.READER_IP = self.ip_var.get().strip() # Update shared state's READER_IP  
        if not shared_state.READER_IP:  
            messagebox.showerror("Invalid IP", "Please enter a valid IP address")
            return
        self.update_status(f"Connecting to reader at {shared_state.READER_IP}...")  
        self.connect_btn.config(state=tk.DISABLED)  

        reader_thread = threading.Thread(
            target=start_rfid_reader, # Call function from rfid_reader module  
            daemon=True
        )
        reader_thread.start()  

    def disconnect_reader(self):
        """Disconnect from the RFID reader"""
        if shared_state.race_active:   # Use shared_state
            if not messagebox.askyesno("Warning", "A race is in progress. Are you sure you want to disconnect?"):  
                return
            self.stop_race()   # Stop race before disconnecting
        self.update_status("Disconnecting from reader...")  
        disconnect_rfid_reader() # Call function from rfid_reader module  
        self.root.after(1000, self.reset_connection_ui)  

    def reset_connection_ui(self):
        """Reset the UI after disconnection"""
        shared_state.reader_connected = False   # Update shared_state
        self.connection_status.config(text="Not connected", foreground="red")  
        self.connect_btn.config(state=tk.NORMAL)  
        self.disconnect_btn.config(state=tk.DISABLED)  
        self.start_button.config(state=tk.DISABLED)  
        self.update_status("Disconnected from reader")  
        shared_state.stop_event.clear()   # Reset shared_state's stop event

    def set_connected(self):
        """Set UI elements for connected state"""
        shared_state.reader_connected = True   # Update shared_state
        self.connection_status.config(text="Connected", foreground="green")  
        self.connect_btn.config(state=tk.DISABLED)  
        self.disconnect_btn.config(state=tk.NORMAL)  
        if shared_state.ALLOWED_TAGS:   # Use shared_state
            self.start_button.config(state=tk.NORMAL)  

    def open_racer_manager(self):
        """Open the racer manager window"""
        self.racer_manager.show()  

    # In your RFIDTagMonitor class (Source 6)

    # ... (other methods like open_racer_manager) ...

    def update_selected_racers(self, selected_racers_list):
        """
        Receives the list of selected racers from the RacerManager,
        updates the shared state, and refreshes the race setup UI.
        """
        logger.info(f"Applying {len(selected_racers_list)} racers to the race.")
        
        # Clear previous race data
        shared_state.ALLOWED_TAGS = []
        shared_state.racers_data = {}

        # Populate the shared state with the new selection
        for racer in selected_racers_list:
            # Normalize the tag for consistency
            tag = str(racer.get('tag', '')).strip().lower()
            if not tag:
                continue

            shared_state.ALLOWED_TAGS.append(tag)
            
            # Initialize the racer's data for the upcoming race
            shared_state.racers_data[tag] = {
                "name": f"{racer.get('first_name', '')} {racer.get('last_name', '')}",
                "laps": 0,
                "lap_times": [],
                "finished": False,
                "position": 0,
                "finish_time": 0
            }
        
        # Update the main UI label to reflect the selection
        self.update_race_setup(len(shared_state.ALLOWED_TAGS))
        
        messagebox.showinfo("Racers Applied", 
                            f"{len(shared_state.ALLOWED_TAGS)} racers have been applied to the race.")

    # ... (other methods like update_race_setup) ...





    def update_race_setup(self, num_racers):
        """Update the race setup display"""
        try:
            shared_state.num_laps = int(self.lap_var.get())   # Update shared_state
        except ValueError:
            shared_state.num_laps = DEFAULT_NUM_LAPS # Default if invalid, use config constant  
        self.lap_var.set(str(shared_state.num_laps))  
        self.race_info_label.config(text=f"{num_racers} racers selected, {shared_state.num_laps} laps")  
        if shared_state.reader_connected:   # Use shared_state
            self.start_button.config(state=tk.NORMAL)

    def start_race(self):
        """Start the race"""
        shared_state.race_active = True   # Update shared_state
        shared_state.race_start_time = time.time()   # Update shared_state
        
        if not shared_state.ALLOWED_TAGS:   # Use shared_state
            messagebox.showerror("No Racers", "Please select racers for the race first")
            return
        try:
            shared_state.num_laps = int(self.lap_var.get())   # Update shared_state
        except ValueError:
            messagebox.showerror("Invalid Input", "Number of laps must be a number")
            return

        # Clear the results trees
        for item in self.standings_tree.get_children():  
            self.standings_tree.delete(item)
        for item in self.lap_times_tree.get_children():  
            self.lap_times_tree.delete(item)

        for tag in shared_state.racers_data:   # Use shared_state
            shared_state.racers_data[tag]["laps"] = 0
            shared_state.racers_data[tag]["lap_times"] = []
            shared_state.racers_data[tag]["finished"] = False
            shared_state.racers_data[tag]["position"] = 0
            shared_state.racers_data[tag]["finish_time"] = 0  

        self.start_button.config(state=tk.DISABLED)  
        self.stop_button.config(state=tk.NORMAL)  
        self.racer_mgr_button.config(state=tk.DISABLED)  
        self.update_status(f"Race started! {len(shared_state.ALLOWED_TAGS)} racers, {shared_state.num_laps} laps")  
        self.race_timer.start()  

    def stop_race(self):
        """Stop the race"""
        shared_state.race_active = False   # Update shared_state
        self.race_timer.stop()  
        self.start_button.config(state=tk.NORMAL)  
        self.stop_button.config(state=tk.DISABLED)  
        self.racer_mgr_button.config(state=tk.NORMAL)  
        self.update_status("Race stopped")  
        self.show_race_results()  
        self.results_exporter.prompt_export_results() # Call method from the exporter instance  

    def show_race_results(self):
        """Display race results"""
        sorted_racers = []  
        for tag, data in shared_state.racers_data.items():   # Use shared_state
            sorted_racers.append(data)

        sorted_racers.sort(key=lambda x: (-x["laps"], x["finish_time"] if x["finish_time"] > 0 else float('inf')))  

        position = 1  
        for racer in sorted_racers:  
            if racer["position"] == 0 and racer["laps"] > 0:
                racer["position"] = position
                position += 1

        for item in self.standings_tree.get_children():  
            self.standings_tree.delete(item)
        for racer in sorted_racers:  
            position_str = racer["position"] if racer["position"] > 0 else "-"  
            time_str = self.race_timer.format_time(racer["finish_time"]) if racer["finish_time"] > 0 else "-"  
            self.standings_tree.insert("", tk.END, values=(
                position_str, racer["name"], racer["laps"], time_str
            ))  

    def process_tag_reading(self, tag_id, antenna, rssi, timestamp):
    # Skip processing if race is not active
        if not shared_state.race_active:
            logger.debug(f"Tag read but race not active: {tag_id}")
            return
        
        # Debug output
        logger.info(f"Processing tag reading: {tag_id}")

    # Check if tag belongs to a racer in current race
        if tag_id in shared_state.ALLOWED_TAGS:
        # Get racer data or initialize if first reading
            if tag_id not in shared_state.racers_data:
                logger.warning(f"Tag {tag_id} is allowed but not in racers_data, initializing")
                racer_name = "Unknown"
                for racer in self.racer_manager.racers:
                    if racer["tag"] == tag_id:
                        racer_name = f"{racer['first_name']} {racer['last_name']}"
                        break
                shared_state.racers_data[tag_id] = {
                    "name": racer_name,
                    "laps": 0,
                    "lap_times": [],
                    "position": 0,
                    "finish_time": 0,
                    "finished": False
                }

            racer = shared_state.racers_data[tag_id]
        
            # Calculate time since race start
            lap_time = timestamp - shared_state.race_start_time
        
            # Calculate individual lap time if not the first lap
            if racer["lap_times"]:
                individual_lap_time = lap_time - racer["lap_times"][-1]
            else:
                individual_lap_time = lap_time

        # Debug info
            print(f"Processing tag: {tag_id}, racer: {racer['name']}, current laps: {racer['laps']}")
        
        # Logic for counting new laps based on time delay
            if racer["laps"] > 0 or racer["lap_times"]:
            # Check if enough time has passed since last lap
                if not racer["lap_times"] or (lap_time - racer["lap_times"][-1] > shared_state.DELAY_SECONDS):
                    racer["laps"] += 1
                    racer["lap_times"].append(lap_time)
                
                # Update lap times display
                self.lap_times_tree.insert("", 0, values=(
                    racer["name"], 
                    racer["laps"],
                    self.race_timer.format_time(individual_lap_time),
                    self.race_timer.format_time(lap_time)
                ))
                
                logger.info(f"Racer {racer['name']} completed lap {racer['laps']} in {individual_lap_time:.2f}s (total: {lap_time:.2f}s)")
                
                # Check if racer finished the race
                if racer["laps"] >= shared_state.num_laps and not racer["finished"]:
                    racer["finished"] = True
                    racer["finish_time"] = lap_time
                    # Find the next position
                    position = 1
                    for r in shared_state.racers_data.values():
                        if r["finished"] and r != racer:
                            position += 1
                    racer["position"] = position
                    logger.info(f"Racer {racer['name']} finished in position {position} with time {lap_time:.2f}s")
                    self.show_race_results()
                    # Update results tree
                    self.update_results()
            else:
                logger.debug(f"Ignoring too fast lap for {racer['name']} (ID: {tag_id})")
        else:
            # First reading for this racer
            racer["lap_times"].append(lap_time)
            racer["laps"] = 1
            self.lap_times_tree.insert("", 0, values=(
                racer["name"], 
                1, 
                self.race_timer.format_time(lap_time), 
                self.race_timer.format_time(lap_time)
            ))
            logger.info(f"Racer {racer['name']} started race, lap 1: {lap_time:.2f}s")

    def update_status(self, message, is_error=False):
        """Update the status message"""
        if is_error:  
            self.status_label.config(text=message, foreground="red")
        else:
            self.status_label.config(text=message, foreground="black")
        self.root.update_idletasks()  

    def update_timer_display(self, time_str):
        """Update the race timer display"""
        self.timer_display.config(text=time_str)  

    def on_close(self):
        """Handle window close event"""
        logger.info("Window close requested, shutting down...")  
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        if self.web_server_running:
            stop_server()
        # ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
        shared_state.stop_event.set()   # Signal the reader thread to stop via shared_state
        self.root.destroy()  
        # Try to stop the Twisted reactor if it's still running (it runs in reader thread)  
        try:
            from twisted.internet import reactor # Import here to avoid circular dependency
            if reactor.running:  
                reactor.stop()
        except:
            pass

    # In your RFIDTagMonitor class (likely from Source 6)

    def update_results(self):
        if not shared_state.race_active or not shared_state.racers_data:
            return
        try:
            # Clear existing entries in the standings tree
            for item in self.standings_tree.get_children():
                self.standings_tree.delete(item)

            # Clear existing entries in the lap times tree
            for item in self.lap_times_tree.get_children():
                self.lap_times_tree.delete(item)

            # Separate racers who have started from those who haven't.
            # This prevents errors and makes sorting easier.
            racers_in_progress = []
            racers_not_started = []
            for tag, racer in shared_state.racers_data.items():
                if racer.get("laps", 0) > 0:
                    racers_in_progress.append(racer)
                else:
                    racers_not_started.append(racer)

            # --- THIS IS THE NEW SORTING LOGIC FOR LIVE STANDINGS ---
            # 1. Sort by number of laps in DESCENDING order (more laps is better).
            # 2. For racers with the same number of laps, sort by their last lap's
            #    total time in ASCENDING order (the racer who got there first is ahead).
            racers_in_progress.sort(key=lambda r: (-r['laps'], r['lap_times'][-1]))

            logger.info("Updating results with the following racers:")
            logger.info(racers_in_progress)

            # --- Populate the Standings Tree with Live Positions ---
            
            # Add the currently ranked racers
            for i, racer in enumerate(racers_in_progress):
                current_position = i + 1
                
                # The time displayed is the total elapsed time of their last completed lap
                last_lap_time = racer['lap_times'][-1]
                time_str = self.race_timer.format_time(last_lap_time)

                self.standings_tree.insert("", tk.END, values=(
                    current_position,
                    racer["name"],
                    racer["laps"],
                    time_str
                ))
            
            # Add the racers who haven't started yet at the bottom of the list
            for racer in racers_not_started:
                self.standings_tree.insert("", tk.END, values=(
                    "-",
                    racer["name"],
                    0,
                    "-"
                ))
                
            # --- Populate the Lap Times Tree with Lap Times ---
            
            # Add lap times for each racer
            for racer in racers_in_progress:
                for i, lap_time in enumerate(racer['lap_times']):
                    lap_num = i + 1
                    
                    # Calculate individual lap duration
                    if i == 0:
                        individual_lap_duration = lap_time
                    else:
                        individual_lap_duration = lap_time - racer['lap_times'][i-1]
                    
                    # Format times for output
                    formatted_lap_duration = self.race_timer.format_time(individual_lap_duration)
                    formatted_total_elapsed_time = self.race_timer.format_time(lap_time)

                    self.lap_times_tree.insert("", tk.END, values=(
                        racer["name"],
                        lap_num,
                        formatted_lap_duration,
                        formatted_total_elapsed_time
                    ))

        except Exception as e:
            logger.error(f"Failed to update results display: {e}", exc_info=True)

        finally:
            self.root.after(1000, self.update_results)

            # If we have a web server running, update it with latest data
            if hasattr(self, 'web_server_running') and self.web_server_running:
                    self.update_web_data()

if __name__ == "__main__":
    try:
        # Create the main tkinter window
        root = tk.Tk()
        # Create the monitor (which builds the UI and orchestrates other components)
        monitor_app = RFIDTagMonitor(root)
        # Run the tkinter main loop
        root.mainloop()
    except KeyboardInterrupt:  
        logger.info("Application terminated by user")
    except Exception as e:  
        logger.error(f"Error in main thread: {e}", exc_info=True)
    finally:
        # Ensure stop_event is set on application exit  
        shared_state.stop_event.set()
        logger.info("Shutting down...")
        try:
            from twisted.internet import reactor
            if reactor.running:
                reactor.stop()
        except:
            pass

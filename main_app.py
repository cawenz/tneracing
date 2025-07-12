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
        # Pass references to shared_state and self.race_timer to RaceResultsExporter
        self.results_exporter = RaceResultsExporter(shared_state, self.race_timer) # New line for exporter
        # Set the reference to this monitor instance for the RFID reader module
        set_monitor_reference(self)
        self.web_server_running = False

        # Setup the user interface FIRST
        self.setup_ui()

        # THEN create the racer manager after UI is set up
        self.racer_manager = RacerManager(root, self) 
        
        # NOW we can safely refresh the racer list
        self.refresh_racer_list()
        
        self.update_status("Application started. Please connect to reader and set up the race...")
        # Handle window close 
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.update_results()

    def setup_ui(self):
        """Setup the user interface with unified background and improved styling"""
        self.root.title("RFID Race Timer")  
        self.root.geometry("1100x700")
        
        # Define unified color scheme
        UNIFIED_BG = "#f8f9fa"  # Light gray background for all frames
        HEADING_FONT = ("Segoe UI", 14, "bold")  # Modern font for headings
        
        # Configure root background
        self.root.configure(bg=UNIFIED_BG)
        
        main_frame = ttk.Frame(self.root, padding="5 10 10 10")
        main_frame.pack(fill=tk.BOTH, expand=True)  
        
        # Create main horizontal layout
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # LEFT HALF - Setup and Connection
        left_frame = ttk.Frame(content_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # RIGHT HALF - Timer and Results  
        right_frame = ttk.Frame(content_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # === LEFT HALF CONTENT ===
        
        # Status/Message Center
        status_outer = tk.Frame(left_frame, bg=UNIFIED_BG, relief="solid", bd=1)
        status_outer.pack(fill=tk.X, pady=(0, 10))
        
        status_header_frame = tk.Frame(status_outer, bg=UNIFIED_BG)
        status_header_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        tk.Label(status_header_frame, text="📢", font=HEADING_FONT, bg=UNIFIED_BG, fg="#1e88e5").pack(side=tk.LEFT)
        tk.Label(status_header_frame, text="  Message Center", font=HEADING_FONT, bg=UNIFIED_BG, fg="black").pack(side=tk.LEFT)
                
        self.status_label = tk.Label(status_outer, text="Starting application...", 
                                font=("Arial", 11), fg="#2c3e50", bg=UNIFIED_BG, anchor="w")
        self.status_label.pack(fill=tk.X, padx=15, pady=(0, 15))

        # RFID Reader Connection
        connection_outer = tk.Frame(left_frame, bg=UNIFIED_BG, relief="solid", bd=1)
        connection_outer.pack(fill=tk.X, pady=5)
        
        conn_header_frame = tk.Frame(connection_outer, bg=UNIFIED_BG)
        conn_header_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        tk.Label(conn_header_frame, text="🔗", font=HEADING_FONT, bg=UNIFIED_BG, fg="#7b1fa2").pack(side=tk.LEFT)
        tk.Label(conn_header_frame, text="  RFID Reader Connection", font=HEADING_FONT, bg=UNIFIED_BG, fg="black").pack(side=tk.LEFT)
                
        conn_content = tk.Frame(connection_outer, bg=UNIFIED_BG)
        conn_content.pack(fill=tk.X, padx=15, pady=(5, 15))

        ip_frame = tk.Frame(conn_content, bg=UNIFIED_BG)
        ip_frame.pack(side=tk.LEFT, pady=5)

        tk.Label(ip_frame, text="Reader IP:", bg=UNIFIED_BG, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.ip_var = tk.StringVar(value=READER_IP)
        ttk.Entry(ip_frame, textvariable=self.ip_var, width=15).pack(side=tk.LEFT)

        # Connection buttons
        button_frame = tk.Frame(conn_content, bg=UNIFIED_BG)
        button_frame.pack(side=tk.LEFT, padx=10, pady=5)

        self.connect_btn = ttk.Button(button_frame, text="Connect", command=self.connect_reader)
        self.connect_btn.pack(side=tk.LEFT, padx=5)

        self.disconnect_btn = ttk.Button(button_frame, text="Disconnect", 
                                    command=self.disconnect_reader, state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT, padx=5)

        # Connection status
        self.connection_status = tk.Label(conn_content, text="Not connected", 
                                        foreground="red", bg=UNIFIED_BG, font=("Arial", 10, "bold"))
        self.connection_status.pack(side=tk.LEFT, padx=10)

        # Race Setup Section
        setup_outer = tk.Frame(left_frame, bg=UNIFIED_BG, relief="solid", bd=1)
        setup_outer.pack(fill=tk.BOTH, expand=True, pady=5)
        
        setup_header_frame = tk.Frame(setup_outer, bg=UNIFIED_BG)
        setup_header_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        tk.Label(setup_header_frame, text="🔧", font=HEADING_FONT, bg=UNIFIED_BG, fg="#4b3e30").pack(side=tk.LEFT)
        tk.Label(setup_header_frame, text="  Race Setup", font=HEADING_FONT, bg=UNIFIED_BG, fg="black").pack(side=tk.LEFT)
                
        setup_content = tk.Frame(setup_outer, bg=UNIFIED_BG)
        setup_content.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 15))

        # Top row - Database management and lap configuration
        top_controls_frame = tk.Frame(setup_content, bg=UNIFIED_BG)
        top_controls_frame.pack(fill=tk.X, pady=5)
        
        # Racer management button
        self.racer_mgr_button = ttk.Button(top_controls_frame, text="Manage Racer Database", 
                                        command=self.open_racer_manager)
        self.racer_mgr_button.pack(side=tk.LEFT, padx=(0, 20))

        # Number of laps section
        lap_frame = tk.Frame(top_controls_frame, bg=UNIFIED_BG)
        lap_frame.pack(side=tk.LEFT)
        
        tk.Label(lap_frame, text="Laps:", bg=UNIFIED_BG, font=("Arial", 10)).pack(side=tk.LEFT, padx=(0, 5))
        self.lap_var = tk.StringVar(value=str(DEFAULT_NUM_LAPS))
        self.lap_spinbox = ttk.Spinbox(lap_frame, from_=1, to=100, textvariable=self.lap_var, width=5)
        self.lap_spinbox.pack(side=tk.LEFT, padx=(0, 5))
        
        self.set_laps_btn = ttk.Button(lap_frame, text="Set Laps", command=self.set_laps)
        self.set_laps_btn.pack(side=tk.LEFT, padx=5)

        # Racer selection section
        racer_selection_frame = tk.Frame(setup_content, bg=UNIFIED_BG)
        racer_selection_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 5))

        # Left sub-frame - Available racers
        available_frame = ttk.LabelFrame(racer_selection_frame, text="Available Racers")
        available_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Search for available racers
        search_frame = ttk.Frame(available_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.racer_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.racer_search_var, width=20)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.racer_search_var.trace_add("write", self.filter_available_racers)

        # Available racers list
        available_tree_frame = ttk.Frame(available_frame)
        available_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        
        self.available_racers_tree = ttk.Treeview(available_tree_frame, 
                                                columns=("name",), 
                                                show="headings", 
                                                selectmode="browse",
                                                height=6)
        self.available_racers_tree.heading("name", text="Name")
        self.available_racers_tree.column("name", width=220)

        available_scrollbar = ttk.Scrollbar(available_tree_frame, orient="vertical", command=self.available_racers_tree.yview)
        self.available_racers_tree.configure(yscrollcommand=available_scrollbar.set)
        
        self.available_racers_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        available_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add button
        add_button_frame = ttk.Frame(available_frame)
        add_button_frame.pack(fill=tk.X, padx=5, pady=5)
        self.add_racer_btn = ttk.Button(add_button_frame, text="Add to Race →", command=self.add_racer_to_race)
        self.add_racer_btn.pack()

        # Right sub-frame - Race roster
        roster_frame = ttk.LabelFrame(racer_selection_frame, text="Race Roster")
        roster_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # Race roster list
        roster_tree_frame = ttk.Frame(roster_frame)
        roster_tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.race_roster_tree = ttk.Treeview(roster_tree_frame, 
                                        columns=("name",), 
                                        show="headings", 
                                        selectmode="browse",
                                        height=6)
        self.race_roster_tree.heading("name", text="Name")
        self.race_roster_tree.column("name", width=220)

        roster_scrollbar = ttk.Scrollbar(roster_tree_frame, orient="vertical", command=self.race_roster_tree.yview)
        self.race_roster_tree.configure(yscrollcommand=roster_scrollbar.set)
        
        self.race_roster_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        roster_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Remove button
        remove_button_frame = ttk.Frame(roster_frame)
        remove_button_frame.pack(fill=tk.X, padx=5, pady=5)
        self.remove_racer_btn = ttk.Button(remove_button_frame, text="← Remove from Race", command=self.remove_racer_from_race)
        self.remove_racer_btn.pack()

        # === RIGHT HALF CONTENT ===

        # Race Timer Section
        timer_outer = tk.Frame(right_frame, bg=UNIFIED_BG, relief="solid", bd=1)
        timer_outer.pack(fill=tk.X, pady=(0, 5))
        
        timer_header_frame = tk.Frame(timer_outer, bg=UNIFIED_BG)
        timer_header_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        tk.Label(timer_header_frame, text="⏰", font=HEADING_FONT, bg=UNIFIED_BG, fg="#2e7d32").pack(side=tk.LEFT)
        tk.Label(timer_header_frame, text="  Race Timer", font=HEADING_FONT, bg=UNIFIED_BG, fg="black").pack(side=tk.LEFT)
                
        timer_content_frame = tk.Frame(timer_outer, bg=UNIFIED_BG)
        timer_content_frame.pack(fill=tk.X, padx=15, pady=(5, 15))

        # Configure grid weights to make 3 equal columns
        timer_content_frame.grid_columnconfigure(0, weight=1)
        timer_content_frame.grid_columnconfigure(1, weight=1) 

        # LEFT THIRD - Timer display and race info
        timer_display_frame = tk.Frame(timer_content_frame, bg=UNIFIED_BG)
        timer_display_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Race status indicator and timer in same row
        timer_row_frame = tk.Frame(timer_display_frame, bg=UNIFIED_BG)
        timer_row_frame.pack(anchor=tk.W, fill=tk.X)

        # Race status indicator
        self.race_status_frame = tk.Frame(timer_row_frame, bg=UNIFIED_BG)
        self.race_status_frame.pack(side=tk.LEFT, padx=(0, 15))

        self.race_status_indicator = tk.Canvas(self.race_status_frame, width=20, height=20, 
                                            highlightthickness=0, bg=UNIFIED_BG)
        self.race_status_indicator.pack()

        # Create the status circle (red = stopped, green = racing)
        self.status_circle = self.race_status_indicator.create_oval(2, 2, 18, 18, 
                                                                fill="#e74c3c", outline="#c0392b", width=2)

        # Large timer display
        self.timer_display = tk.Label(timer_row_frame, text="00:00.00", 
                                    font=("Consolas", 28, "bold"), bg=UNIFIED_BG, fg="#2c3e50")
        self.timer_display.pack(side=tk.LEFT, anchor=tk.W)

        # Race info
        self.race_info_label = tk.Label(timer_display_frame, text="0 racers, 3 laps", 
                                    font=("Arial", 12, "bold"), fg="#2c3e50", bg=UNIFIED_BG)
        self.race_info_label.pack(anchor=tk.W, pady=(5, 0))

        # MIDDLE THIRD - Race control buttons
        control_frame = tk.Frame(timer_content_frame, bg=UNIFIED_BG)
        control_frame.grid(row=0, column=1, sticky="nsew", padx=(10,0))

        tk.Label(control_frame, text="Race Controls", font=("Arial", 11, "bold"), 
            bg=UNIFIED_BG, fg="#2c3e50").pack(pady=(0, 10))

        # Start button
        self.start_button = tk.Button(control_frame, 
                            text="▶ Start Race", 
                            command=self.start_race, 
                            state=tk.DISABLED,
                            width=12,
                            font=("Arial", 10, "bold"),
                            bg="#27ae60", fg="white",
                            activebackground="#2ecc71", activeforeground="white",
                            relief="raised", bd=2)
        self.start_button.pack(pady=2)

        # Stop button
        self.stop_button = tk.Button(control_frame, 
                        text="⏹ Stop Race", 
                        command=self.stop_race, 
                        state=tk.DISABLED,
                        width=12,
                        font=("Arial", 10, "bold"),
                        bg="#e74c3c", fg="white",
                        activebackground="#c0392b", activeforeground="white",
                        relief="raised", bd=2)
        self.stop_button.pack(pady=2)

        # Reset button
        self.reset_button = tk.Button(control_frame, 
                        text="🔄 Reset", 
                        command=self.reset_race, 
                        width=12,
                        font=("Arial", 10, "bold"),
                        bg="#95a5a6", fg="white",
                        activebackground="#7f8c8d", activeforeground="white",
                        relief="raised", bd=2)
        self.reset_button.pack(pady=2)

        # Race Results
        results_outer = tk.Frame(right_frame, bg=UNIFIED_BG, relief="solid", bd=1)
        results_outer.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        results_header_frame = tk.Frame(results_outer, bg=UNIFIED_BG)
        results_header_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        tk.Label(results_header_frame, text="🏆", font=HEADING_FONT, bg=UNIFIED_BG, fg="#c29b0c").pack(side=tk.LEFT)
        tk.Label(results_header_frame, text="  Race Results", font=HEADING_FONT, bg=UNIFIED_BG, fg="black").pack(side=tk.LEFT)

        # Results notebook
            # Web server controls row
        web_controls_frame = tk.Frame(results_outer, bg=UNIFIED_BG)
        web_controls_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

        self.web_server_btn = ttk.Button(web_controls_frame, text="Start Web Display", 
                                    command=self.toggle_web_server)
        self.web_server_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.copy_url_btn = ttk.Button(web_controls_frame, text="📋 Copy URL", 
                                    command=self.copy_web_url, state=tk.DISABLED)
        self.copy_url_btn.pack(side=tk.LEFT, padx=(0, 10))

        self.web_url_label = tk.Label(web_controls_frame, text="Web display not running", 
                                    font=("Arial", 9), fg="gray", bg=UNIFIED_BG)
        self.web_url_label.pack(side=tk.LEFT, padx=(10, 0))

        # Results notebook
        self.results_notebook = ttk.Notebook(results_outer)
        self.results_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 15))

        # Standings tab
        standings_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(standings_frame, text="Standings")

        self.standings_tree = ttk.Treeview(standings_frame, 
                                columns=("position", "racer", "laps", "gap", "best_lap_time", "last_lap_time", "total_time"), 
                                show="headings")
        self.standings_tree["columns"] = ("position", "racer", "laps", "gap", "best_lap_time", "last_lap_time", "total_time")
        self.standings_tree.column("#0", width=0, stretch=tk.NO)
        for column in self.standings_tree["columns"]:
            self.standings_tree.column(column, anchor=tk.W, width=100)
            self.standings_tree.heading(column, text=column.capitalize().replace("_", " "))
        self.standings_tree.heading("position", text="Position")
        self.standings_tree.heading("racer", text="Racer")
        self.standings_tree.heading("laps", text="Total Laps Recorded")
        self.standings_tree.heading("gap", text="Gap")
        self.standings_tree.heading("best_lap_time", text="Best Lap Time")
        self.standings_tree.heading("last_lap_time", text="Last Lap Time")
        self.standings_tree.heading("total_time", text="Total Time")

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
    def update_race_status_indicator(self, racing=False):
        """Update the race status indicator color"""
        if racing:
            # Green for active race
            self.race_status_indicator.itemconfig(self.status_circle, 
                                                fill="#2ecc71", outline="#27ae60")
        else:
            # Red for stopped
            self.race_status_indicator.itemconfig(self.status_circle, 
                                                fill="#e74c3c", outline="#c0392b")

    def update_button_states(self, race_active=False):
        """Update button states and colors based on race status"""
        if race_active:
            # During race: disable start, enable stop
            self.start_button.config(state=tk.DISABLED, bg="#95a5a6")  # Gray when disabled
            self.stop_button.config(state=tk.NORMAL, bg="#e74c3c")     # Red when enabled
        else:
            # Race stopped: enable start (if conditions met), disable stop
            if shared_state.reader_connected and shared_state.ALLOWED_TAGS:
                self.start_button.config(state=tk.NORMAL, bg="#27ae60")  # Green when enabled
            else:
                self.start_button.config(state=tk.DISABLED, bg="#95a5a6")  # Gray when disabled
            self.stop_button.config(state=tk.DISABLED, bg="#95a5a6")

    def filter_available_racers(self, *args):
        """Filter available racers based on search"""
        self.refresh_racer_list()

    def add_racer_to_race(self):
        """Add selected racer to the race"""
        selected_items = self.available_racers_tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select a racer to add to the race.")
            return
            
        # Get selected racer info
        item = selected_items[0]
        name, tag = self.available_racers_tree.item(item, 'values')
        
        # Find the full racer data
        all_racers = self.racer_manager.get_all_racers()
        selected_racer = None
        for racer in all_racers:
            if racer.get('tag', '').strip().lower() == tag.strip().lower():
                selected_racer = racer
                break
                
        if not selected_racer:
            messagebox.showerror("Error", "Could not find racer data.")
            return
            
        # Add to race
        tag_normalized = str(selected_racer.get('tag', '')).strip().lower()
        if tag_normalized not in shared_state.ALLOWED_TAGS:
            shared_state.ALLOWED_TAGS.append(tag_normalized)
            
            # Initialize racer data
            shared_state.racers_data[tag_normalized] = {
                "name": f"{selected_racer.get('first_name', '')} {selected_racer.get('last_name', '')}",
                "laps": 0,
                "lap_times": [],
                "finished": False,
                "position": 0,
                "finish_time": 0
            }
            
            # Update UI
            self.refresh_race_roster()
            self.refresh_racer_list()
            self.update_race_info()
            
            # Update start button state
            if shared_state.reader_connected and shared_state.ALLOWED_TAGS:
                self.start_button.config(state=tk.NORMAL)

    def remove_racer_from_race(self):
        """Remove selected racer from the race"""
        selected_items = self.race_roster_tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select a racer to remove from the race.")
            return
            
        # Get selected racer info
        item = selected_items[0]
        name, tag = self.race_roster_tree.item(item, 'values')
        
        # Remove from race
        tag_normalized = tag.strip().lower()
        if tag_normalized in shared_state.ALLOWED_TAGS:
            shared_state.ALLOWED_TAGS.remove(tag_normalized)
            
        if tag_normalized in shared_state.racers_data:
            del shared_state.racers_data[tag_normalized]
            
        # Update UI
        self.refresh_race_roster()
        self.refresh_racer_list()
        self.update_race_info()
        
        # Update start button state
        if not shared_state.ALLOWED_TAGS:
            self.start_button.config(state=tk.DISABLED)

    def refresh_race_roster(self):
        """Refresh the race roster display"""
        # Clear the race roster tree
        for item in self.race_roster_tree.get_children():
            self.race_roster_tree.delete(item)
            
        # Add current race participants
        for tag in shared_state.ALLOWED_TAGS:
            if tag in shared_state.racers_data:
                racer = shared_state.racers_data[tag]
                self.race_roster_tree.insert("", tk.END, values=(racer["name"], tag))

    def update_race_info(self):
        """Update the race info label"""
        try:
            shared_state.num_laps = int(self.lap_var.get())
        except ValueError:
            shared_state.num_laps = DEFAULT_NUM_LAPS
            self.lap_var.set(str(shared_state.num_laps))
            
        num_racers = len(shared_state.ALLOWED_TAGS)
        self.race_info_label.config(text=f"{num_racers} racers, {shared_state.num_laps} laps")

    def update_selected_racers(self, selected_racers_list):
        """Legacy method - no longer used with new UI"""
        pass  # This method is kept for compatibility but does nothing

    def update_race_setup(self, num_racers):
        """Legacy method - replaced by update_race_info"""
        self.update_race_info()(column, text=column.capitalize().replace("_", " "))
        self.standings_tree.heading("position", text="Position")
        self.standings_tree.heading("racer", text="Racer")
        self.standings_tree.heading("laps", text="Total Laps Recorded")
        self.standings_tree.heading

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
                self.copy_url_btn.config(state=tk.NORMAL)
                
            
            # Show a message to the user
                
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
                self.copy_url_btn.config(state=tk.DISABLED)
                self.update_status("Web display stopped")
            else:
                messagebox.showerror(
                "Web Display Error",
                "Failed to stop web display. See log for details."
            )

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
        # Only enable start button if we have racers in the race
        if shared_state.ALLOWED_TAGS:   # Use shared_state
            self.start_button.config(state=tk.NORMAL)
            self.start_button.config(state=tk.NORMAL)
            self.start_button.config(state=tk.NORMAL)  

    def open_racer_manager(self):
        """Open the racer manager window"""
        self.racer_manager.show()  

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

    def update_race_info(self):
        """Update the race info label"""
        num_racers = len(shared_state.ALLOWED_TAGS)
        self.race_info_label.config(text=f"{num_racers} racers, {shared_state.num_laps} laps")

    def start_race(self):
        """Start the race"""
        if not shared_state.ALLOWED_TAGS:   # Use shared_state
            messagebox.showerror("No Racers", "Please add racers to the race first")
            return
            
        try:
            shared_state.num_laps = int(self.lap_var.get())   # Update shared_state
        except ValueError:
            messagebox.showerror("Invalid Input", "Number of laps must be a number")
            return

        shared_state.race_active = True   # Update shared_state
        shared_state.race_start_time = time.time()   # Update shared_state

        # Clear the results trees
        for item in self.standings_tree.get_children():  
            self.standings_tree.delete(item)
        for item in self.lap_times_tree.get_children():  
            self.lap_times_tree.delete(item)

        # Reset all racer data
        for tag in shared_state.racers_data:   # Use shared_state
            shared_state.racers_data[tag]["laps"] = 0
            shared_state.racers_data[tag]["lap_times"] = []
            shared_state.racers_data[tag]["finished"] = False
            shared_state.racers_data[tag]["position"] = 0
            shared_state.racers_data[tag]["finish_time"] = 0  

        # Update UI state
        self.start_button.config(state=tk.DISABLED)  
        self.stop_button.config(state=tk.NORMAL)  
        self.racer_mgr_button.config(state=tk.DISABLED)
        
        # Disable race setup during race
        self.add_racer_btn.config(state=tk.DISABLED)
        self.remove_racer_btn.config(state=tk.DISABLED)
        
        self.update_status(f"Race started! {len(shared_state.ALLOWED_TAGS)} racers, {shared_state.num_laps} laps")  
        self.race_timer.start()  
        
        # IMPORTANT: Start the update_results timer here
        self.update_results()

    def stop_race(self):
        """Stop the race"""
        # Force one final update to show the final results BEFORE stopping the race
        self.update_results()
        # Update web server cache one more time
        if hasattr(self, 'web_server_running') and self.web_server_running:
            try:
                self.update_web_data()
            except Exception as e:
                logger.error(f"Error updating web data during race stop: {e}", exc_info=True)
        
        shared_state.race_active = False   # Update shared_state
        self.race_timer.stop()  
        self.start_button.config(state=tk.NORMAL if shared_state.reader_connected and shared_state.ALLOWED_TAGS else tk.DISABLED)  
        self.stop_button.config(state=tk.DISABLED)  
        self.racer_mgr_button.config(state=tk.NORMAL)
        
        # Re-enable race setup after race
        self.add_racer_btn.config(state=tk.NORMAL)
        self.remove_racer_btn.config(state=tk.NORMAL)
        
        self.update_status("Race stopped")  
        
        # Prompt to export results
        self.results_exporter.prompt_export_results()

    def process_tag_reading(self, tag_id, antenna, rssi, timestamp):
    # Skip processing if race is not active
        if not shared_state.race_active:
            logger.debug(f"Tag read but race not active: {tag_id}")
            return
    
        # Debug output
        logger.info(f"Processing tag reading: {tag_id}")
    
        # Check if the tag belongs to a racer
        if tag_id not in shared_state.racers_data:
            logger.warning(f"Tag {tag_id} not found in racers_data")
            return
    
        # Get the racer data
        racer = shared_state.racers_data[tag_id]
    
        # Calculate the lap time
        lap_time = time.time() - shared_state.race_start_time
    
        # Calculate individual lap duration
        if not racer["lap_times"]:
            individual_lap_time = lap_time  # First lap
        else:
            individual_lap_time = lap_time - racer["lap_times"][-1]
    
        logger.debug(f"Processing tag: {tag_id}, racer: {racer['name']}, current laps: {racer['laps']}")
    
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
                    f"{individual_lap_time:.3f}",
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
                
                # Show race results if appropriate
                    if all(r.get("finished", False) or r.get("laps", 0) == 0 for r in shared_state.racers_data.values()):
                        self.show_race_results()
            
                # Always update results after a new lap
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
            f"{lap_time:.3f}", 
            self.race_timer.format_time(lap_time)
        ))
        logger.info(f"Racer {racer['name']} started race, lap 1: {lap_time:.2f}s")
        # Update results after first lap
        self.update_results()

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

    def update_results(self):
        """Update the race results display"""
        try:
            # Always schedule the next update first to ensure continuity
            self.root.after(1000, self.update_results)
            
            # Skip if race is not active or no racers
            if not shared_state.race_active or not shared_state.racers_data:
                return
            
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
                # Store the tag in the racer data for reference
                racer["tag_id"] = tag
                if racer.get("laps", 0) > 0:
                    racers_in_progress.append(racer)
                else:
                    racers_not_started.append(racer)
                    
            # Sort racers by position: more laps first, then by fastest time for same lap count
            racers_in_progress.sort(key=lambda r: (-r['laps'], r['lap_times'][-1] if r['lap_times'] else 0))
            
            # If no racers have started, just show the waiting racers
            if not racers_in_progress:
                for racer in racers_not_started:
                    self.standings_tree.insert("", tk.END, values=(
                        "-",
                        racer["name"],
                        0,
                        "-",
                        "-",
                        "-",
                        "-"
                    ))
                return
                    
            # Determine the leader to calculate gaps
            leader = racers_in_progress[0] if racers_in_progress else None
            leader_laps = leader["laps"] if leader else 0
            leader_time = leader["lap_times"][-1] if leader and leader["lap_times"] else 0
                
            # Populate the Standings Tree with Live Positions
            for i, racer in enumerate(racers_in_progress):
                current_position = i + 1
                    
                # The time displayed is the total elapsed time of their last completed lap
                last_lap_time = racer['lap_times'][-1] if racer['lap_times'] else 0
                total_time = self.race_timer.format_total_time(last_lap_time)
                    
                # Calculate gap from leader
                gap = "Leader"
                if racer != leader and racer["lap_times"]:
                    if racer["laps"] == leader_laps:
                        # Same lap, calculate time gap
                        gap_value = racer['lap_times'][-1] - leader_time
                        gap = f"+{gap_value:.3f}"
                    else:
                        # Different lap, show lap gap
                        lap_gap = leader_laps - racer["laps"]
                        gap = f"+{lap_gap} lap{'s' if lap_gap > 1 else ''}"
                    
                # Calculate best lap time
                best_lap_time = "N/A"
                best_lap_value = 0
                if len(racer["lap_times"]) > 1:
                    lap_durations = []
                    for j in range(len(racer["lap_times"])):
                        if j == 0:
                            lap_durations.append(racer["lap_times"][0])
                        else:
                            lap_durations.append(racer["lap_times"][j] - racer["lap_times"][j-1])
                            
                    best_lap_value = min(lap_durations)
                    best_lap_time = f"{best_lap_value:.3f}"
                elif racer["lap_times"]:
                    best_lap_value = racer['lap_times'][0]
                    best_lap_time = f"{best_lap_value:.3f}"
                    
                # Calculate last lap time
                last_lap_time_value = 0
                if len(racer["lap_times"]) > 1:
                    last_lap_time_value = racer["lap_times"][-1] - racer["lap_times"][-2]
                    last_lap_time = f"{last_lap_time_value:.3f}"
                elif racer["lap_times"]:
                    last_lap_time_value = racer['lap_times'][0]
                    last_lap_time = f"{last_lap_time_value:.3f}"
                else:
                    last_lap_time = "N/A"
                    
                # Store these calculated values in shared_state for web server
                tag_id = racer.get("tag_id")
                if tag_id:
                    shared_state.racers_data[tag_id]["calculated_gap"] = gap
                    shared_state.racers_data[tag_id]["best_lap"] = best_lap_value
                    shared_state.racers_data[tag_id]["last_lap"] = last_lap_time_value
                    shared_state.racers_data[tag_id]["position"] = current_position
                    
                # Update the UI
                self.standings_tree.insert("", tk.END, values=(
                    current_position,
                    racer["name"],
                    racer["laps"],
                    gap,
                    best_lap_time,
                    last_lap_time,
                    total_time
                ))
                
            # Add the racers who haven't started yet at the bottom of the list
            for racer in racers_not_started:
                self.standings_tree.insert("", tk.END, values=(
                    "-",
                    racer["name"],
                    0,
                    "-",
                    "-",
                    "-",
                    "-"
                ))
                
            # Populate the Lap Times Tree with Lap Times
            for racer in racers_in_progress:
                for i, lap_time in enumerate(racer['lap_times']):
                    lap_num = i + 1
                    
                    # Calculate individual lap duration
                    if i == 0:
                        individual_lap_duration = lap_time
                    else:
                        individual_lap_duration = lap_time - racer['lap_times'][i-1]
                        
                    # Format times for output
                    formatted_lap_duration = f"{individual_lap_duration:.3f}"
                    formatted_total_elapsed_time = self.race_timer.format_total_time(lap_time)
                        
                    self.lap_times_tree.insert("", tk.END, values=(
                        racer["name"],
                        lap_num,
                        formatted_lap_duration,
                        formatted_total_elapsed_time
                    ))
        
        except Exception as e:
            logger.error(f"Failed to update results display: {e}", exc_info=True)
            import traceback
            logger.error(traceback.format_exc())
        
        finally:
            # If we have a web server running, update it with latest data
            if hasattr(self, 'web_server_running') and self.web_server_running:
                try:
                    self.update_web_data()
                except Exception as e:
                    logger.error(f"Error updating web data: {e}", exc_info=True)

    def update_web_data(self):
        """Update shared_state with latest race data for the web server"""
        try:
            # Skip if race timer isn't initialized
            if not hasattr(self, 'race_timer'):
                return
                
            # Just update the race data cache in the web server module
            # Don't modify shared_state here as it's already being updated by the RFID reader
            from web_server import update_race_data_cache
            update_race_data_cache()
            
        except Exception as e:
            logger.error(f"Error updating web data: {e}", exc_info=True)

    def set_laps(self):
        """Set the number of laps and update the display"""
        try:
            new_laps = int(self.lap_var.get())
            if new_laps < 1 or new_laps > 100:
                raise ValueError("Laps must be between 1 and 100")
            shared_state.num_laps = new_laps
            self.update_race_info()
            logger.info(f"Number of laps set to {new_laps}")
        except ValueError as e:
            if "invalid literal" in str(e):
                messagebox.showerror("Invalid Input", "Number of laps must be a valid number")
            else:
                messagebox.showerror("Invalid Input", str(e))
            # Reset to current value
            self.lap_var.set(str(shared_state.num_laps))

    def refresh_racer_list(self):
        """Refresh the available racers list"""
        # Check if racer_manager exists yet (it won't during initial setup)
        if not hasattr(self, 'racer_manager'):
            return
            
        # Clear the available racers tree
        for item in self.available_racers_tree.get_children():
            self.available_racers_tree.delete(item)
        
        # Get all racers from the racer manager
        all_racers = self.racer_manager.get_all_racers()
        
        # Filter based on search term
        search_term = self.racer_search_var.get().lower()
        
        for racer in all_racers:
            # Skip racers already in the race
            tag = str(racer.get('tag', '')).strip().lower()
            if tag in shared_state.ALLOWED_TAGS:
                continue
                
            name = f"{racer.get('first_name', '')} {racer.get('last_name', '')}"
            
            # Apply search filter
            if search_term and search_term not in name.lower() and search_term not in tag:
                continue
                
            self.available_racers_tree.insert("", tk.END, values=(name, racer.get('tag', '')))

    def show_race_ended(self):
        """Show visual indicators that the race has ended"""
        # Update message center
        self.update_status("🏁 Race Finished! All racers have completed the race.", is_error=False)
    
        # Update timer display to show "RACE FINISHED"
        self.timer_display.config(text="RACE FINISHED", fg="#e74c3c", font=("Consolas", 20, "bold"))
    
        # Change status indicator to yellow/gold for finished
        self.race_status_indicator.itemconfig(self.status_circle, 
                                        fill="#f39c12", outline="#e67e22")

    def reset_race(self):
        """Reset everything to default state"""
    # Stop race if running
        if shared_state.race_active:
            self.stop_race()
    
    # Clear race data
        shared_state.ALLOWED_TAGS = []
        shared_state.racers_data = {}
        shared_state.num_laps = DEFAULT_NUM_LAPS
        
        # Reset UI elements
        self.lap_var.set(str(DEFAULT_NUM_LAPS))
        self.timer_display.config(text="00:00.00", fg="#2c3e50", font=("Consolas", 28, "bold"))
        self.update_race_status_indicator(racing=False)
        
        # Clear results trees
        for item in self.standings_tree.get_children():
            self.standings_tree.delete(item)
        for item in self.lap_times_tree.get_children():
            self.lap_times_tree.delete(item)
        
        # Refresh UI
        self.refresh_race_roster()
        self.refresh_racer_list()
        self.update_race_info()
        self.update_status("Race data reset. Ready to set up a new race.")

    def copy_web_url(self):
        """Copy the web server URL to clipboard"""
        if self.web_server_running:
            from web_server import get_server_url
            url = get_server_url()
            self.root.clipboard_clear()
            self.root.clipboard_append(url)
            self.update_status(f"URL copied to clipboard: {url}")


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

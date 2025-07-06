import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
from config import logger # Use logger from config
import shared_state # Import shared_state to access/modify global race data

class RacerManager:
    def __init__(self, parent, monitor=None):
        self.parent = parent
        self.monitor=monitor
        self.racers = []  # List to store racer data
        self.load_racers()  # Load saved racers if available
        
        # Create a new window for racer management
        self.window = tk.Toplevel(parent)
        self.window.title("Racer Management")
        self.window.geometry("600x500")
        self.window.protocol("WM_DELETE_WINDOW", self.hide)  # Hide instead of destroy
        
        # Main frame
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side - Racer list
        list_frame = ttk.LabelFrame(main_frame, text="Registered Racers")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # Racer list with scrollbar
        self.racer_tree = ttk.Treeview(list_frame, columns=("id", "name", "tag"), show="headings")
        self.racer_tree.heading("id", text="ID")
        self.racer_tree.heading("name", text="Name")
        self.racer_tree.heading("tag", text="RFID Tag")
        
        # Column widths
        self.racer_tree.column("id", width=50)
        self.racer_tree.column("name", width=150)
        self.racer_tree.column("tag", width=150)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.racer_tree.yview)
        self.racer_tree.configure(yscroll=scrollbar.set)
        
        # Pack list and scrollbar
        self.racer_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right side - Add/Edit racer form
        form_frame = ttk.LabelFrame(main_frame, text="Add/Edit Racer")
        form_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        # Form fields
        ttk.Label(form_frame, text="First Name:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.first_name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.first_name_var).grid(row=0, column=1, sticky=tk.EW, pady=5)
        
        ttk.Label(form_frame, text="Last Name:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.last_name_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.last_name_var).grid(row=1, column=1, sticky=tk.EW, pady=5)
        
        ttk.Label(form_frame, text="Racer ID:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.racer_id_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.racer_id_var).grid(row=2, column=1, sticky=tk.EW, pady=5)
        
        ttk.Label(form_frame, text="RFID Tag:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.tag_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.tag_var).grid(row=3, column=1, sticky=tk.EW, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Add Racer", command=self.add_racer).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Update Selected", command=self.update_racer).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete Selected", command=self.delete_racer).pack(side=tk.LEFT, padx=5)
        
        # Bottom frame - Race selection
        bottom_frame = ttk.LabelFrame(self.window, text="Race Setup")
        bottom_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Selected racers for race
        ttk.Label(bottom_frame, text="Select racers for the race:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Buttons for race selection
        selection_frame = ttk.Frame(bottom_frame)
        selection_frame.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        ttk.Button(selection_frame, text="Add to Race", command=self.add_to_race).pack(side=tk.LEFT, padx=5)
        ttk.Button(selection_frame, text="Remove from Race", command=self.remove_from_race).pack(side=tk.LEFT, padx=5)
        ttk.Button(selection_frame, text="Apply Selection", command=self.apply_selection).pack(side=tk.LEFT, padx=5)
        
        # Selected racers list
        selected_frame = ttk.LabelFrame(bottom_frame, text="Selected Racers")
        selected_frame.grid(row=2, column=0, sticky=tk.EW, pady=5)
        
        self.selected_tree = ttk.Treeview(selected_frame, columns=("id", "name", "tag"), show="headings", height=5)
        self.selected_tree.heading("id", text="ID")
        self.selected_tree.heading("name", text="Name")
        self.selected_tree.heading("tag", text="RFID Tag")
        
        # Column widths for selected racers
        self.selected_tree.column("id", width=50)
        self.selected_tree.column("name", width=150)
        self.selected_tree.column("tag", width=150)
        
        self.selected_tree.pack(fill=tk.X)
        
        # Bind selection event
        self.racer_tree.bind("<<TreeviewSelect>>", self.on_racer_select)
        
        # Initially hide the window
        self.window.withdraw()
        
        # Load existing racers into the treeview
        self.refresh_racer_list()
    
    def show(self):
        self.window.deiconify()
        self.window.lift()
    
    def hide(self):
        self.window.withdraw()
    
    def load_racers(self):
        """Load racers from file if available"""
        try:
            if os.path.exists("racers.json"):
                with open("racers.json", "r") as f:
                    self.racers = json.load(f)
        except Exception as e:
            logger.error(f"Error loading racers: {e}")
            self.racers = []
    
    def save_racers(self):
        """Save racers to file"""
        try:
            with open("racers.json", "w") as f:
                json.dump(self.racers, f)
        except Exception as e:
            logger.error(f"Error saving racers: {e}")
    
    def refresh_racer_list(self):
        """Update the racer list in the treeview"""
        # Clear current list
        for item in self.racer_tree.get_children():
            self.racer_tree.delete(item)
        
        # Add all racers
        for racer in self.racers:
            name = f"{racer['first_name']} {racer['last_name']}"
            self.racer_tree.insert("", tk.END, values=(racer["id"], name, racer["tag"]))
    
    def add_racer(self):
        """Add a new racer"""
        first_name = self.first_name_var.get().strip()
        last_name = self.last_name_var.get().strip()
        racer_id = self.racer_id_var.get().strip()
        tag = self.tag_var.get().strip()
        
        if not first_name or not last_name or not racer_id or not tag:
            messagebox.showerror("Input Error", "All fields are required")
            return
        
        # Check for duplicate ID
        if any(r["id"] == racer_id for r in self.racers):
            messagebox.showerror("Duplicate ID", "A racer with this ID already exists")
            return
        
        # Check for duplicate tag
        if any(r["tag"].lower() == tag.lower() for r in self.racers):
            messagebox.showerror("Duplicate Tag", "A racer with this RFID tag already exists")
            return
        
        # Add new racer
        self.racers.append({
            "id": racer_id,
            "first_name": first_name,
            "last_name": last_name,
            "tag": tag
        })
        
        # Save and refresh
        self.save_racers()
        self.refresh_racer_list()
        self.clear_form()
    
    def update_racer(self):
        """Update selected racer"""
        selected = self.racer_tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Select a racer to update")
            return
        
        first_name = self.first_name_var.get().strip()
        last_name = self.last_name_var.get().strip()
        racer_id = self.racer_id_var.get().strip()
        tag = self.tag_var.get().strip()
        
        if not first_name or not last_name or not racer_id or not tag:
            messagebox.showerror("Input Error", "All fields are required")
            return
        
        # Get the current racer ID from the tree
        current_id = self.racer_tree.item(selected[0])['values'][0]
        
        # Check if ID is being changed to an existing ID
        if racer_id != current_id and any(r["id"] == racer_id for r in self.racers):
            messagebox.showerror("Duplicate ID", "A racer with this ID already exists")
            return
        
        # Find the racer
        for i, racer in enumerate(self.racers):
            if racer["id"] == current_id:
                # Update racer
                self.racers[i] = {
                    "id": racer_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "tag": tag
                }
                break
        
        # Save and refresh
        self.save_racers()
        self.refresh_racer_list()
        self.clear_form()
    
    def delete_racer(self):
        """Delete selected racer"""
        selected = self.racer_tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Select a racer to delete")
            return
        
        racer_id = self.racer_tree.item(selected[0])['values'][0]
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this racer?"):
            # Remove racer
            #*8888self.racers = [r for r in self.racers if r["id"] != racer_id]
            self.racers = [r for r in self.racers if str(r["id"]) != racer_id]
            # Save and refresh
            self.save_racers()
            self.refresh_racer_list()
            self.clear_form()
    
    def on_racer_select(self, event):
        """Handle selection of a racer in the list"""
        selected = self.racer_tree.selection()
        if not selected:
            return
        
        racer_id = self.racer_tree.item(selected[0])['values'][0]
        
        # Find the racer
        for racer in self.racers:
            if racer["id"] == racer_id:
                # Fill the form
                self.first_name_var.set(racer["first_name"])
                self.last_name_var.set(racer["last_name"])
                self.racer_id_var.set(racer["id"])
                self.tag_var.set(racer["tag"])
                break
    
    def clear_form(self):
        """Clear the form fields"""
        self.first_name_var.set("")
        self.last_name_var.set("")
        self.racer_id_var.set("")
        self.tag_var.set("")
    
    def add_to_race(self):
        """Add selected racer to the race"""
        selected = self.racer_tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Select a racer to add to the race")
            return
        
        # Check if already in the race
        for item in self.selected_tree.get_children():
            if self.selected_tree.item(item)['values'][0] == self.racer_tree.item(selected[0])['values'][0]:
                messagebox.showinfo("Already Added", "This racer is already added to the race")
                return
        
        # Copy the selected racer to the race list
        values = self.racer_tree.item(selected[0])['values']
        self.selected_tree.insert("", tk.END, values=values)
    
    def remove_from_race(self):
        """Remove selected racer from the race"""
        selected = self.selected_tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Select a racer to remove from the race")
            return
        
        self.selected_tree.delete(selected[0])

    def apply_selection(self):
    # Clear previous selections
        shared_state.ALLOWED_TAGS = []
    
    # Get all selected racers
        for item in self.selected_tree.get_children():
            values = self.selected_tree.item(item)['values']
            racer_id = values[0]
            name = values[1]
            tag = values[2]
        
    # Ensure tag is properly formatted (lowercase, stripped)
            tag = str(tag).strip().lower()
            shared_state.ALLOWED_TAGS.append(tag)

    # Also store racer information - this is what's missing!
            shared_state.racers_data[tag] = {
                "id": racer_id,
                "name": name,
                "tag": tag,
                "laps": 0,
                "lap_times": [],
                "finish_time": 0,
                "position": 0,
                "finished": False
        }
        logger.info(f"Selected tags: {shared_state.ALLOWED_TAGS}")
        logger.info(f"Racer data initialized: {shared_state.racers_data}")

    
        if not shared_state.ALLOWED_TAGS:
            messagebox.showinfo("No Racers Selected", "Please add racers to the race before applying")
            return
    
        # Update main UI
        num_racers = len(shared_state.ALLOWED_TAGS)
    
    # Call update_race_setup on the monitor to update UI
    # Change 'monitor' to 'self.monitor'
        if hasattr(self, 'monitor') and self.monitor is not None:
            self.monitor.update_race_setup(num_racers)
        else:
            messagebox.showinfo("Selection Complete", f"{num_racers} racers selected for the race")
    
        self.hide()  # Hide racer manager window
    
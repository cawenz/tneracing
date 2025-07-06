# racer_manager.py

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import random
from datetime import datetime
from config import logger
from desktop_scanner_utils import scan_single_rfid_tag

# --- Helper functions from desktopScanner.py (Reference 3) ---
def is_valid_dob_format(date_string):
    """Checks if the date string is in YYYY-MM-DD format."""
    if not date_string:
        return True # An empty date is valid as it's optional
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False

class RacerManager:
    def __init__(self, parent, monitor=None):
        self.parent = parent
        self.monitor = monitor
        self.racers = []
        self.current_editing_id = None
        
        self.window = tk.Toplevel(parent)
        self.window.title("Racer Management")
        self.window.geometry("800x550") # Made window a bit larger for new fields
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        self.window.transient(parent)
        self.window.grab_set()

        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Left Side: Racer List ---
        list_frame = ttk.LabelFrame(main_frame, text="Registered Racers")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # TASK 1: Enable multi-select with "extended" mode
        self.racer_tree = ttk.Treeview(list_frame, columns=("id", "name", "tag"), show="headings", selectmode="extended")
        self.racer_tree.heading("id", text="ID")
        self.racer_tree.heading("name", text="Name")
        self.racer_tree.heading("tag", text="RFID Tag")
        self.racer_tree.column("id", width=60)
        self.racer_tree.column("name", width=180)
        self.racer_tree.column("tag", width=180)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.racer_tree.yview)
        self.racer_tree.configure(yscroll=scrollbar.set)
        self.racer_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # --- ADD THIS DEBUGGING CODE ---
        print("--- Treeview Bindings ---")
        print(self.racer_tree.bind())
        print("--- Ttk.Treeview Class Bindings ---")
        print(self.racer_tree.bind_class('TtkTreeview'))
        print("--- ALL Bindings ---")
        print(self.racer_tree.bind_all())
        print("------------------------")
        # --- END DEBUGGING CODE ---

        #self.racer_tree.bind('<<TreeviewSelect>>', self.on_racer_select)

        # --- Right Side: Add/Edit Form ---
        form_frame = ttk.LabelFrame(main_frame, text="Add / Edit Racer Details")
        form_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        form_frame.columnconfigure(1, weight=1)

        # Form StringVars
        self.first_name_var = tk.StringVar()
        self.last_name_var = tk.StringVar()
        self.racer_id_var = tk.StringVar()
        self.tag_var = tk.StringVar()
        self.tag_label_var = tk.StringVar()
        self.birthdate_var = tk.StringVar()

        # Row counter for easier layout
        row_idx = 0
        
        # TASK 2: ID is now system-generated and read-only
        ttk.Label(form_frame, text="Racer ID:").grid(row=row_idx, column=0, sticky=tk.W, padx=5, pady=5)
        self.id_entry = ttk.Entry(form_frame, textvariable=self.racer_id_var, state='readonly')
        self.id_entry.grid(row=row_idx, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5); row_idx += 1

        ttk.Label(form_frame, text="First Name:").grid(row=row_idx, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.first_name_var).grid(row=row_idx, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5); row_idx += 1
        
        ttk.Label(form_frame, text="Last Name:").grid(row=row_idx, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.last_name_var).grid(row=row_idx, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5); row_idx += 1
        
        ttk.Label(form_frame, text="RFID Tag:").grid(row=row_idx, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.tag_var).grid(row=row_idx, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(form_frame, text="Scan", command=self.scan_for_tag).grid(row=row_idx, column=2, sticky=tk.W, padx=5, pady=5); row_idx += 1

        # TASK 3: New data columns for Tag Label and Birthdate
        ttk.Label(form_frame, text="Tag Label:").grid(row=row_idx, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.tag_label_var).grid(row=row_idx, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5); row_idx += 1
        
        ttk.Label(form_frame, text="Birthdate (YYYY-MM-DD):").grid(row=row_idx, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.birthdate_var).grid(row=row_idx, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5); row_idx += 1

        # --- Form Buttons ---
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=row_idx, column=0, columnspan=3, pady=20)
        ttk.Button(button_frame, text="Save Racer", command=self.save_racer).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Clear Form / New", command=self.clear_form).pack(side=tk.LEFT, padx=10)
        
        # --- Bottom Buttons ---
        bottom_frame = ttk.Frame(self.window, padding=(10,0))
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        ttk.Button(bottom_frame, text="Add to race", command=self.apply_selection).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="Delete selected racer", command=self.delete_racer).pack(side=tk.RIGHT, padx=5)
        
        self.load_racers()
        self.clear_form()

    # --- NEW: Function to generate racer IDs from Ref 3 ---
    def generate_new_user_id(self):
        """Generates a unique 5-digit user ID."""
        existing_ids = {r.get('id') for r in self.racers}
        for i in range(10000, 20000):
            potential_id = str(i)
            if potential_id not in existing_ids: return potential_id
        # Fallback for when the primary range is exhausted
        while True:
            potential_id = "1" + "".join(random.choices("0123456789", k=4))
            if potential_id not in existing_ids:
                 messagebox.showwarning("ID Generation", "Standard ID range exhausted, using random ID.", parent=self.window)
                 return potential_id

    def on_racer_select(self, event=None):
        selected_items = self.racer_tree.selection()
        # Only act if one item is selected to avoid form confusion
        if len(selected_items) != 1:
            self.clear_form()
            return

        selected_id = self.racer_tree.item(selected_items[0], 'values')[0]
        for racer in self.racers:
            if str(racer['id']) == str(selected_id):
                self.racer_id_var.set(racer.get('id', ''))
                self.first_name_var.set(racer.get('first_name', ''))
                self.last_name_var.set(racer.get('last_name', ''))
                self.tag_var.set(racer.get('tag', ''))
                # Populate new optional fields
                self.tag_label_var.set(racer.get('tag_label', ''))
                self.birthdate_var.set(racer.get('birthdate', ''))
                self.current_editing_id = racer['id']
                return

    def clear_form(self):
        self.racer_id_var.set("(New Racer)")
        self.first_name_var.set("")
        self.last_name_var.set("")
        self.tag_var.set("")
        self.tag_label_var.set("")
        self.birthdate_var.set("")
        self.current_editing_id = None
        if self.racer_tree.selection(): self.racer_tree.selection_remove(self.racer_tree.selection())

    def save_racer(self):
        first_name = self.first_name_var.get().strip()
        last_name = self.last_name_var.get().strip()
        tag = self.tag_var.get().strip()
        tag_label = self.tag_label_var.get().strip()
        birthdate = self.birthdate_var.get().strip()
        
        # TASK 4 & 5: Validate required fields and birthdate format
        if not all([first_name, last_name, tag]):
            messagebox.showerror("Input Error", "First Name, Last Name, and RFID Tag are required.", parent=self.window)
            return
            
        if not is_valid_dob_format(birthdate):
            messagebox.showerror("Validation Error", "Birthdate must be in YYYY-MM-DD format.", parent=self.window)
            return
        
        # Check for duplicate tag (but ignore the racer we are editing)
        for r in self.racers:
            if r['tag'].lower() == tag.lower() and str(r.get('id')) != str(self.current_editing_id):
                messagebox.showerror("Duplicate Tag", f"This RFID tag is assigned to {r['first_name']} {r['last_name']}.", parent=self.window)
                return

        if self.current_editing_id:
            # UPDATE mode
            racer_id_to_save = self.current_editing_id
            action = "updated"
        else:
            # ADD mode - TASK 2: Generate new ID
            racer_id_to_save = self.generate_new_user_id()
            action = "added"

        new_racer_data = {
            "id": racer_id_to_save, 
            "first_name": first_name, 
            "last_name": last_name, 
            "tag": tag,
            "tag_label": tag_label,
            "birthdate": birthdate
        }

        if action == "updated":
            for i, r in enumerate(self.racers):
                if str(r.get('id')) == str(self.current_editing_id):
                    self.racers[i] = new_racer_data; break
        else:
            self.racers.append(new_racer_data)
        
        self.save_racers_to_file()
        self.refresh_racer_list()
        self.clear_form()
        messagebox.showinfo("Success", f"Racer '{first_name} {last_name}' has been {action}.", parent=self.window)

    def delete_racer(self):
        selected_items = self.racer_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Required", "Please select a racer from the list to delete.", parent=self.window)
            return
        
        racer_name_to_delete = self.racer_tree.item(selected_items[0], 'values')[1]
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete racer '{racer_name_to_delete}'?", parent=self.window):
            return
        
        racer_id_to_delete = self.racer_tree.item(selected_items[0], 'values')[0]
        self.racers = [r for r in self.racers if str(r.get('id')) != str(racer_id_to_delete)]
        self.save_racers_to_file()
        self.refresh_racer_list()
        if str(self.current_editing_id) == str(racer_id_to_delete): self.clear_form()

    def apply_selection(self):
        # TASK 1: Handle multiple selections
        selected_items = self.racer_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Required", "Please select one or more racers to apply.", parent=self.window)
            return
        
        selected_racers = []
        for item in selected_items:
            racer_id = self.racer_tree.item(item, 'values')[0]
            # Find the full racer data
            racer_data = next((r for r in self.racers if str(r.get('id')) == str(racer_id)), None)
            if racer_data: selected_racers.append(racer_data)
        
        if self.monitor: self.monitor.update_selected_racers(selected_racers)
        self.hide()

    def scan_for_tag(self):
        self.window.config(cursor="watch"); self.window.update()
        tag_id = scan_single_rfid_tag()
        self.window.config(cursor="")
        if tag_id: self.tag_var.set(tag_id)

    def refresh_racer_list(self):
        self.racers.sort(key=lambda r: (r.get('last_name', '').lower(), r.get('first_name', '').lower()))
        for item in self.racer_tree.get_children(): self.racer_tree.delete(item)
        for racer in self.racers:
            name = f"{racer.get('first_name', '')} {racer.get('last_name', '')}"
            self.racer_tree.insert("", tk.END, values=(racer.get("id"), name, racer.get("tag")))

    def load_racers(self):
        try:
            if os.path.exists("racers.json"):
                with open("racers.json", "r") as f: self.racers = json.load(f)
            else: self.racers = []
        except Exception as e:
            logger.error(f"Error loading racers: {e}"); self.racers = []
        self.refresh_racer_list()

    def save_racers_to_file(self):
        try:
            with open("racers.json", "w") as f: json.dump(self.racers, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving racers: {e}")
            messagebox.showerror("Save Error", f"Could not save racers to file: {e}", parent=self.window)

    def show(self):
        self.load_racers()
        self.window.deiconify(); self.window.grab_set()

    def hide(self):
        self.parent.grab_set(); self.window.withdraw()
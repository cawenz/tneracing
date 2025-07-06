# racer_manager.py

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
from config import logger
from desktop_scanner_utils import scan_single_rfid_tag

class RacerManager:
    def __init__(self, parent, monitor=None):
        self.parent = parent
        self.monitor = monitor
        self.racers = []
        
        # This variable tracks the racer loaded into the form for editing.
        # It's used by 'Save' and reset by 'Clear' or 'Select'.
        self.current_editing_id = None
        
        self.window = tk.Toplevel(parent)
        self.window.title("Racer Management")
        self.window.geometry("750x500")
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        self.window.transient(parent)
        self.window.grab_set()

        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Left Side: Racer List ---
        list_frame = ttk.LabelFrame(main_frame, text="Registered Racers")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        self.racer_tree = ttk.Treeview(list_frame, columns=("id", "name", "tag"), show="headings", selectmode="extended")
        self.racer_tree.heading("id", text="ID")
        self.racer_tree.heading("name", text="Name")
        self.racer_tree.heading("tag", text="RFID Tag")
        self.racer_tree.column("id", width=60, anchor=tk.W)
        self.racer_tree.column("name", width=150, anchor=tk.W)
        self.racer_tree.column("tag", width=180, anchor=tk.W)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.racer_tree.yview)
        self.racer_tree.configure(yscroll=scrollbar.set)
        
        self.racer_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.racer_tree.bind('<<TreeviewSelect>>', self.on_racer_select)

        # --- Right Side: Add/Edit Form ---
        form_frame = ttk.LabelFrame(main_frame, text="Add / Edit Racer Details")
        form_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        form_frame.columnconfigure(1, weight=1)

        self.first_name_var = tk.StringVar()
        self.last_name_var = tk.StringVar()
        self.racer_id_var = tk.StringVar()
        self.tag_var = tk.StringVar()

        ttk.Label(form_frame, text="First Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.first_name_var).grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(form_frame, text="Last Name:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.last_name_var).grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(form_frame, text="Racer ID:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.racer_id_var).grid(row=2, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(form_frame, text="RFID Tag:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.tag_var).grid(row=3, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(form_frame, text="Scan", command=self.scan_for_tag).grid(row=3, column=2, sticky=tk.W, padx=5, pady=5)

        # --- Form Buttons ---
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=20)
        
        ttk.Button(button_frame, text="Save Racer", command=self.save_racer).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Clear Form / New", command=self.clear_form).pack(side=tk.LEFT, padx=10)
        # The Delete button is moved to the bottom for clarity
        
        # --- Bottom Buttons ---
        bottom_frame = ttk.Frame(self.window, padding=(10,0))
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        
        # This button is for applying racers to the race, not for managing the database
        ttk.Button(bottom_frame, text="Apply Racers to Race", command=self.apply_selection).pack(side=tk.RIGHT, padx=5)
        
        # The delete button correctly placed to act on the selection in the list
        ttk.Button(bottom_frame, text="Delete Selected Racer", command=self.delete_racer).pack(side=tk.RIGHT, padx=5)
        
        self.load_racers()
        self.clear_form()

    def on_racer_select(self, event=None):
        selected_items = self.racer_tree.selection()
        if not selected_items: return

        selected_id = self.racer_tree.item(selected_items[0], 'values')[0]
        for racer in self.racers:
            if str(racer['id']) == str(selected_id):
                self.first_name_var.set(racer.get('first_name', ''))
                self.last_name_var.set(racer.get('last_name', ''))
                self.racer_id_var.set(racer.get('id', ''))
                self.tag_var.set(racer.get('tag', ''))
                self.current_editing_id = racer['id']
                return

    def clear_form(self):
        self.first_name_var.set("")
        self.last_name_var.set("")
        self.racer_id_var.set("")
        self.tag_var.set("")
        self.current_editing_id = None
        if self.racer_tree.selection(): self.racer_tree.selection_remove(self.racer_tree.selection()[0])

    def save_racer(self):
        first_name = self.first_name_var.get().strip()
        last_name = self.last_name_var.get().strip()
        racer_id = self.racer_id_var.get().strip()
        tag = self.tag_var.get().strip()
        
        if not all([first_name, last_name, racer_id, tag]):
            messagebox.showerror("Input Error", "All fields are required.", parent=self.window)
            return
        
        for r in self.racers:
            if str(r['id']) == racer_id and str(r['id']) != str(self.current_editing_id):
                messagebox.showerror("Duplicate ID", f"A racer with ID '{racer_id}' already exists.", parent=self.window)
                return
            if r['tag'].lower() == tag.lower() and str(r['id']) != str(self.current_editing_id):
                messagebox.showerror("Duplicate Tag", f"This RFID tag is assigned to {r['first_name']} {r['last_name']}.", parent=self.window)
                return

        new_racer_data = {"id": racer_id, "first_name": first_name, "last_name": last_name, "tag": tag}

        if self.current_editing_id is not None:
            for i, r in enumerate(self.racers):
                if str(r['id']) == str(self.current_editing_id):
                    self.racers[i] = new_racer_data
                    break
        else:
            self.racers.append(new_racer_data)
        
        self.save_racers_to_file()
        self.refresh_racer_list()
        self.clear_form()

    def delete_racer(self):
        """Deletes the racer currently selected in the list, using the reliable method from Ref 3."""
        # 1. Get the current selection directly from the Treeview widget.
        selected_items = self.racer_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Required", "Please select a racer from the list to delete.", parent=self.window)
            return

        # 2. Extract the racer's info from the selected item's values.
        item_data = self.racer_tree.item(selected_items[0], 'values')
        racer_id_to_delete = item_data[0]
        racer_name_to_delete = item_data[1]

        # 3. Confirm with the user.
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete racer '{racer_name_to_delete}'?", parent=self.window):
            return
        
        # 4. Filter the list, save, and refresh the UI.
        self.racers = [r for r in self.racers if str(r.get('id')) != str(racer_id_to_delete)]
        self.save_racers_to_file()
        self.refresh_racer_list()
        
        # If the deleted racer was in the form, clear the form.
        if str(self.current_editing_id) == str(racer_id_to_delete):
            self.clear_form()
            
        messagebox.showinfo("Success", f"Racer '{racer_name_to_delete}' has been deleted.", parent=self.window)

    def scan_for_tag(self):
        self.window.config(cursor="watch"); self.window.update()
        tag_id = scan_single_rfid_tag()
        self.window.config(cursor="")
        if tag_id: self.tag_var.set(tag_id)

    def refresh_racer_list(self):
        self.racers.sort(key=lambda r: (r.get('last_name', ''), r.get('first_name', '')))
        for item in self.racer_tree.get_children(): self.racer_tree.delete(item)
        for racer in self.racers:
            name = f"{racer.get('first_name', '')} {racer.get('last_name', '')}"
            self.racer_tree.insert("", tk.END, values=(racer["id"], name, racer["tag"]))

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

    # In racer_manager.py, replace the apply_selection function

    def apply_selection(self):
        selected_items = self.racer_tree.selection()
        if not selected_items:
            messagebox.showwarning("Selection Required", 
                               "Please select one or more racers from the list to apply.", 
                               parent=self.window)
            return

        selected_racers_data = []
        # Get the full data dictionary for each selected racer
        for item_id in selected_items:
            racer_id = self.racer_tree.item(item_id, 'values')[0]
        # Find the matching racer in our master list
            racer_data = next((r for r in self.racers if str(r.get('id')) == str(racer_id)), None)
            if racer_data:
                selected_racers_data.append(racer_data)

    # Call the newly created function on the monitor instance
        if self.monitor:
            self.monitor.update_selected_racers(selected_racers_data)
    
        self.hide()

    def show(self):
        self.load_racers()
        self.window.deiconify(); self.window.grab_set()

    def hide(self):
        self.parent.grab_set(); self.window.withdraw()
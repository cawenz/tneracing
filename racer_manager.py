# racer_manager.py

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import random
from datetime import datetime
from config import logger
from desktop_scanner_utils import scan_single_rfid_tag

def is_valid_dob_format(date_string):
    if not date_string: return True
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
        self.window.geometry("1000x600")
        self.window.protocol("WM_DELETE_WINDOW", self.hide)
        self.window.transient(parent)
        self.window.grab_set()

        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        list_frame = ttk.LabelFrame(main_frame, text="Registered Racers")
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        search_frame = ttk.Frame(list_frame)
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(fill=tk.X, expand=True)
        self.search_var.trace_add("write", self.filter_racer_list)

        tree_container = ttk.Frame(list_frame)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        self.racer_tree = ttk.Treeview(tree_container, columns=("id", "name", "tag"), show="headings", selectmode="extended")
        self.racer_tree.heading("id", text="ID"); self.racer_tree.heading("name", text="Name"); self.racer_tree.heading("tag", text="RFID Tag")
        self.racer_tree.column("id", width=60); self.racer_tree.column("name", width=180); self.racer_tree.column("tag", width=180)
        
        scrollbar = ttk.Scrollbar(tree_container, orient=tk.VERTICAL, command=self.racer_tree.yview)
        self.racer_tree.configure(yscroll=scrollbar.set)
        
        self.racer_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # This now binds to our new, lightweight function that does NOT interfere with multi-select
        self.racer_tree.bind('<<TreeviewSelect>>', self.on_selection_change)

        center_frame = ttk.Frame(main_frame)
        center_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        self.edit_btn = ttk.Button(center_frame, text="Edit Selected →", command=self.populate_form_for_edit, state=tk.DISABLED)
        self.edit_btn.pack(pady=20, anchor=tk.N)

        form_frame = ttk.LabelFrame(main_frame, text="Add / Edit Racer Details")
        form_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        form_frame.columnconfigure(1, weight=1)

        self.first_name_var = tk.StringVar(); self.last_name_var = tk.StringVar(); self.racer_id_var = tk.StringVar()
        self.tag_var = tk.StringVar(); self.tag_label_var = tk.StringVar(); self.birthdate_var = tk.StringVar()
        row_idx = 0
        ttk.Label(form_frame, text="Racer ID:").grid(row=row_idx, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.racer_id_var, state='readonly').grid(row=row_idx, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5); row_idx += 1
        ttk.Label(form_frame, text="First Name:").grid(row=row_idx, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.first_name_var).grid(row=row_idx, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5); row_idx += 1
        ttk.Label(form_frame, text="Last Name:").grid(row=row_idx, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.last_name_var).grid(row=row_idx, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5); row_idx += 1
        ttk.Label(form_frame, text="RFID Tag:").grid(row=row_idx, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.tag_var).grid(row=row_idx, column=1, sticky=tk.EW, padx=5, pady=5)
        ttk.Button(form_frame, text="Scan", command=self.scan_for_tag).grid(row=row_idx, column=2, sticky=tk.W, padx=5, pady=5); row_idx += 1
        ttk.Label(form_frame, text="Tag Label:").grid(row=row_idx, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.tag_label_var).grid(row=row_idx, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5); row_idx += 1
        ttk.Label(form_frame, text="Birthdate (YYYY-MM-DD):").grid(row=row_idx, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(form_frame, textvariable=self.birthdate_var).grid(row=row_idx, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5); row_idx += 1
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=row_idx, column=0, columnspan=3, pady=20)
        ttk.Button(button_frame, text="Save Racer", command=self.save_racer).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Clear Form / New", command=self.clear_form).pack(side=tk.LEFT, padx=10)
        bottom_frame = ttk.Frame(self.window, padding=(10,0))
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10)
        ttk.Button(bottom_frame, text="Apply Racers to Race", command=self.apply_selection).pack(side=tk.RIGHT, padx=5)
        ttk.Button(bottom_frame, text="Delete Selected Racer", command=self.delete_racer).pack(side=tk.RIGHT, padx=5)
        
        self.load_racers()
        self.clear_form()

    def on_selection_change(self, event=None):
        """
        This function's ONLY responsibility is to update the state of the
        'Edit Selected' button. It has no other side effects, which prevents 
        conflicts with the Treeview's native multi-select behavior.
        """
        selected_items = self.racer_tree.selection()
        if len(selected_items) == 1:
            self.edit_btn.config(state="normal")
        else:
            self.edit_btn.config(state="disabled")

    def populate_form_for_edit(self):
        """The action for the 'Edit Selected' button. Populates the form."""
        selected_items = self.racer_tree.selection()
        if len(selected_items) != 1: return

        selected_id = self.racer_tree.item(selected_items[0], 'values')[0]
        for racer in self.racers:
            if str(racer['id']) == str(selected_id):
                self.racer_id_var.set(racer.get('id', ''))
                self.first_name_var.set(racer.get('first_name', ''))
                self.last_name_var.set(racer.get('last_name', ''))
                self.tag_var.set(racer.get('tag', ''))
                self.tag_label_var.set(racer.get('tag_label', ''))
                self.birthdate_var.set(racer.get('birthdate', ''))
                self.current_editing_id = racer['id']
                return
    
    def clear_form(self):
        """Clears the form and also resets the selection and edit button state."""
        self.racer_id_var.set("(New Racer)")
        self.first_name_var.set(""); self.last_name_var.set(""); self.tag_var.set("")
        self.tag_label_var.set(""); self.birthdate_var.set("")
        self.current_editing_id = None
        # Clearing the form should also deselect items in the list
        if self.racer_tree.selection():
            self.racer_tree.selection_remove(self.racer_tree.selection())
        # The on_selection_change event will fire and disable the button automatically
    
    def filter_racer_list(self, *args):
        search_term = self.search_var.get().lower()
        for item in self.racer_tree.get_children(): self.racer_tree.delete(item)
        for racer in self.racers:
            name = f"{racer.get('first_name', '')} {racer.get('last_name', '')}".lower()
            racer_id = str(racer.get('id', '')).lower()
            tag = str(racer.get('tag', '')).lower()
            if search_term in name or search_term in racer_id or search_term in tag:
                self.racer_tree.insert("", tk.END, values=(racer.get("id"), f"{racer.get('first_name', '')} {racer.get('last_name', '')}", racer.get("tag")))

    def refresh_racer_list(self):
        self.racers.sort(key=lambda r: (r.get('last_name', '').lower(), r.get('first_name', '').lower()))
        self.filter_racer_list()

    def generate_new_user_id(self):
        existing_ids = {r.get('id') for r in self.racers}; i = 10000
        while str(i) in existing_ids: i += 1
        return str(i)

    def save_racer(self):
        first_name = self.first_name_var.get().strip(); last_name = self.last_name_var.get().strip()
        tag = self.tag_var.get().strip(); tag_label = self.tag_label_var.get().strip()
        birthdate = self.birthdate_var.get().strip()
        if not all([first_name, last_name, tag]):
            messagebox.showerror("Input Error", "First Name, Last Name, and RFID Tag are required.", parent=self.window); return
        if not is_valid_dob_format(birthdate):
            messagebox.showerror("Validation Error", "Birthdate must be in YYYY-MM-DD format.", parent=self.window); return
        for r in self.racers:
            if r['tag'].lower() == tag.lower() and str(r.get('id')) != str(self.current_editing_id):
                messagebox.showerror("Duplicate Tag", f"This RFID tag is assigned to {r['first_name']} {r['last_name']}.", parent=self.window); return
        action = "updated" if self.current_editing_id else "added"
        racer_id_to_save = self.current_editing_id if self.current_editing_id else self.generate_new_user_id()
        new_racer_data = {"id": racer_id_to_save, "first_name": first_name, "last_name": last_name, "tag": tag, "tag_label": tag_label, "birthdate": birthdate}
        if action == "updated":
            for i, r in enumerate(self.racers):
                if str(r.get('id')) == str(self.current_editing_id): self.racers[i] = new_racer_data; break
        else: self.racers.append(new_racer_data)
        self.save_racers_to_file(); self.refresh_racer_list(); self.clear_form()
        messagebox.showinfo("Success", f"Racer '{first_name} {last_name}' has been {action}.", parent=self.window)

    def delete_racer(self):
        selected_items = self.racer_tree.selection()
        if not selected_items: messagebox.showwarning("Selection Required", "Please select a racer from the list to delete.", parent=self.window); return
        # Deleting multiple racers at once is a good feature
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {len(selected_items)} selected racer(s)?", parent=self.window): return
        
        ids_to_delete = {self.racer_tree.item(item, 'values')[0] for item in selected_items}
        self.racers = [r for r in self.racers if str(r.get('id')) not in ids_to_delete]
        self.save_racers_to_file(); self.refresh_racer_list()
        # If the racer being edited was among those deleted, clear the form
        if self.current_editing_id and str(self.current_editing_id) in ids_to_delete: self.clear_form()

    def apply_selection(self):
        selected_items = self.racer_tree.selection()
        if not selected_items: messagebox.showwarning("Selection Required", "Please select one or more racers to apply.", parent=self.window); return
        selected_racers = []
        for item in selected_items:
            racer_id = self.racer_tree.item(item, 'values')[0]
            racer_data = next((r for r in self.racers if str(r.get('id')) == str(racer_id)), None)
            if racer_data: selected_racers.append(racer_data)
        if self.monitor: self.monitor.update_selected_racers(selected_racers)
        self.hide()

    def scan_for_tag(self):
        self.window.config(cursor="watch"); self.window.update(); tag_id = scan_single_rfid_tag(); self.window.config(cursor="")
        if tag_id: self.tag_var.set(tag_id)

    def load_racers(self):
        try:
            if os.path.exists("racers.json"):
                with open("racers.json", "r") as f: self.racers = json.load(f)
            else: self.racers = []
        except Exception as e: logger.error(f"Error loading racers: {e}"); self.racers = []
        self.refresh_racer_list()

    def save_racers_to_file(self):
        try:
            with open("racers.json", "w") as f: json.dump(self.racers, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving racers: {e}")
            messagebox.showerror("Save Error", f"Could not save racers to file: {e}", parent=self.window)

    def show(self): self.load_racers(); self.window.deiconify(); self.window.grab_set()
    def hide(self): self.parent.grab_set(); self.window.withdraw()
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import threading
import time

import config
import app_detector

# Define a file to save and load configurations
CONFIG_FILE = "gesture_mappings.json"

class UIController:
    def __init__(self, master, start_callback, stop_callback, update_mappings_callback):
        self.master = master
        self.master.title("HandBridge")
        self.master.geometry("800x600")

        self.start_callback = start_callback
        self.stop_callback = stop_callback
        self.update_mappings_callback = update_mappings_callback

        self.running = False
        self.gesture_mappings = self._load_mappings()

        self._create_widgets()
        self._populate_mappings()

        # Update the action_controller with the loaded mappings
        self.update_mappings_callback(self.gesture_mappings)


    def _load_mappings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                messagebox.showerror("Error", "Could not load gesture mappings file. Using default.")
                return config.CUSTOM_APP_GESTURE_MAPPINGS
        return config.CUSTOM_APP_GESTURE_MAPPINGS

    def _save_mappings(self):
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.gesture_mappings, f, indent=4)
        messagebox.showinfo("Saved", "Gesture mappings saved successfully!")

    def _create_widgets(self):
        # Control Frame (Start/Stop/Save)
        control_frame = ttk.LabelFrame(self.master, text="Control")
        control_frame.pack(padx=10, pady=10, fill="x")

        self.start_button = ttk.Button(control_frame, text="Start Gesture Control", command=self._start_control)
        self.start_button.pack(side="left", padx=5, pady=5)

        self.stop_button = ttk.Button(control_frame, text="Stop Gesture Control", command=self._stop_control, state="disabled")
        self.stop_button.pack(side="left", padx=5, pady=5)

        self.save_button = ttk.Button(control_frame, text="Save Mappings", command=self._save_mappings)
        self.save_button.pack(side="right", padx=5, pady=5)

        # Profile Selection
        profile_frame = ttk.LabelFrame(self.master, text="Select Application Profile")
        profile_frame.pack(padx=10, pady=5, fill="x")

        self.selected_profile = tk.StringVar()
        self.profile_dropdown = ttk.Combobox(profile_frame, textvariable=self.selected_profile,
                                             values=list(app_detector.SUPPORTED_PROFILES.keys()))
        self.profile_dropdown.pack(padx=5, pady=5)
        self.profile_dropdown.set(list(app_detector.SUPPORTED_PROFILES.keys())[0]) # Set default
        self.profile_dropdown.bind("<<ComboboxSelected>>", self._on_profile_selected)

        # Mappings Display Frame
        self.mappings_frame = ttk.LabelFrame(self.master, text="Gesture Mappings")
        self.mappings_frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.canvas = tk.Canvas(self.mappings_frame)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.scrollbar = ttk.Scrollbar(self.mappings_frame, orient="vertical", command=self.canvas.yview)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind('<Configure>', lambda e: self.canvas.configure(scrollregion = self.canvas.bbox("all")))

        self.inner_mappings_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.inner_mappings_frame, anchor="nw")


        self.gesture_vars = {} # Stores StringVar for each gesture's selected action

    def _populate_mappings(self):
        # Clear existing widgets
        for widget in self.inner_mappings_frame.winfo_children():
            widget.destroy()

        current_profile_name = self.selected_profile.get()
        current_profile_mappings = self.gesture_mappings.get(current_profile_name, {})

        row = 0
        for gesture_name in config.CUSTOM_APP_GESTURE_MAPPINGS["default"].keys(): # Use default keys for consistent order
            if gesture_name == config.GESTURE_MOUSE_MOVING or gesture_name == config.GESTURE_DRAGGING:
                # These gestures' actions are fixed and not user-configurable in this UI
                ttk.Label(self.inner_mappings_frame, text=f"{gesture_name}:").grid(row=row, column=0, padx=5, pady=2, sticky="w")
                ttk.Label(self.inner_mappings_frame, text=f"{current_profile_mappings.get(gesture_name, 'N/A')} (Fixed)").grid(row=row, column=1, padx=5, pady=2, sticky="w")
                row += 1
                continue


            ttk.Label(self.inner_mappings_frame, text=f"{gesture_name}:").grid(row=row, column=0, padx=5, pady=2, sticky="w")

            var = tk.StringVar()
            # Set current value or default if not found
            var.set(current_profile_mappings.get(gesture_name, "do_nothing"))
            self.gesture_vars[gesture_name] = var

            dropdown = ttk.Combobox(self.inner_mappings_frame, textvariable=var, values=config.AVAILABLE_ACTIONS)
            dropdown.grid(row=row, column=1, padx=5, pady=2, sticky="ew")
            dropdown.bind("<<ComboboxSelected>>", lambda event, g=gesture_name, p=current_profile_name: self._on_mapping_changed(g, p))
            row += 1

        self.inner_mappings_frame.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))


    def _on_profile_selected(self, event=None):
        self._populate_mappings()

    def _on_mapping_changed(self, gesture, profile):
        new_action = self.gesture_vars[gesture].get()
        if profile not in self.gesture_mappings:
            self.gesture_mappings[profile] = {}
        self.gesture_mappings[profile][gesture] = new_action
        self.update_mappings_callback(self.gesture_mappings)
        # print(f"Mapping updated: Profile={profile}, Gesture={gesture}, Action={new_action}")

    def _start_control(self):
        if not self.running:
            self.running = True
            self.start_button.config(state="disabled")
            self.stop_button.config(state="normal")
            # Start the main gesture control logic in a separate thread
            self.control_thread = threading.Thread(target=self.start_callback, daemon=True)
            self.control_thread.start()
            print("Gesture control started.")

    def _stop_control(self):
        if self.running:
            self.running = False
            self.stop_callback() # Signal the main loop to stop
            # Give a moment for the thread to actually stop
            if self.control_thread.is_alive():
                self.control_thread.join(timeout=2)
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
            print("Gesture control stopped.")


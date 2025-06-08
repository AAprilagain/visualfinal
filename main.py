import tkinter as tk
import threading
import time # Import time for potential short sleeps

import multithread_main
import ui_controller
import config # To access CUSTOM_APP_GESTURE_MAPPINGS

# Global variable to hold the ActionController instance
global_action_controller = None

def start_gesture_control():
    """
    Function to be called by the UI to start the gesture control logic.
    Runs multithread_main.main_threaded in a separate thread.
    """
    global global_action_controller
    print("Attempting to start gesture control from main_threaded_wrapper...")
    # Initialize ActionController here if not already initialized
    if global_action_controller is None:
        global_action_controller = multithread_main.get_action_controller() # Get the instance
        if global_action_controller is None:
            # Fallback if get_action_controller fails or returns None unexpectedly
            global_action_controller = multithread_main.ActionController(initial_mappings=config.CUSTOM_APP_GESTURE_MAPPINGS)
            multithread_main.set_action_controller(global_action_controller)


    multithread_main.main_threaded_wrapper() # This will internally set stop_event and start threads

def stop_gesture_control():
    """
    Function to be called by the UI to stop the gesture control logic.
    Signals the main thread to stop.
    """
    print("Attempting to stop gesture control from main_threaded_wrapper...")
    multithread_main.stop_event.set() # Signal the stop event

def update_action_controller_mappings(new_mappings):
    """
    Callback function from UI to update the ActionController's mappings.
    """
    global global_action_controller
    if global_action_controller:
        global_action_controller.update_gesture_mappings(new_mappings)
        print("ActionController mappings updated from UI.")
    else:
        print("Warning: ActionController not yet initialized, cannot update mappings.")

def main():
    # Initialize ActionController instance before passing to UIController
    # This allows UIController to immediately access the mappings for display.
    global global_action_controller
    global_action_controller = multithread_main.ActionController(initial_mappings=config.CUSTOM_APP_GESTURE_MAPPINGS)
    multithread_main.set_action_controller(global_action_controller) # Pass the instance to multithread_main

    root = tk.Tk()
    app = ui_controller.UIController(root, start_gesture_control, stop_gesture_control, update_action_controller_mappings)
    root.protocol("WM_DELETE_WINDOW", lambda: on_closing(root)) # Handle window close event
    root.mainloop()

def on_closing(root):
    """Handles proper shutdown when the Tkinter window is closed."""
    print("Closing UI window. Signaling gesture control to stop.")
    multithread_main.stop_event.set() # Ensure all threads are signaled to stop
    # Give threads a moment to finish, then destroy the window
    threading.Thread(target=lambda: _delayed_destroy(root), daemon=True).start()

def _delayed_destroy(root):
    """Helper to ensure main thread has a moment to process stop event before GUI is destroyed."""
    # It's better to let the threads in multithread_main manage their own join/cleanup.
    # The stop_event should be sufficient for clean shutdown.
    time.sleep(0.5) # Give a small buffer
    if root.winfo_exists(): # Check if window still exists before destroying
        root.destroy()
    print("UI window destroyed.")


if __name__ == '__main__':
    print(f"Starting {__name__}...")
    main()
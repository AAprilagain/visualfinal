# action_controller.py

import pyautogui
import time
import config
import app_detector # To get the current application profile

# --- Define Base Actions ---
# These are lambda functions that will be called by pyautogui
# They can take arguments like coordinates or scroll amount.
BASE_ACTIONS = {
    "do_nothing": lambda **kwargs: None,
    "mouse_move": lambda x, y, **kwargs: pyautogui.moveTo(x, y, duration=config.PYAUTOGUI_MOVE_DURATION_MOUSE),
    "mouse_drag": lambda x, y, **kwargs: pyautogui.moveTo(x, y, duration=config.PYAUTOGUI_MOVE_DURATION_DRAG),
    "left_click": lambda **kwargs: pyautogui.click(),
    "double_click": lambda **kwargs: pyautogui.doubleClick(),
    "mouse_down_left": lambda **kwargs: pyautogui.mouseDown(button='left'),
    "mouse_up_left": lambda **kwargs: pyautogui.mouseUp(button='left'),
    "scroll": lambda amount, **kwargs: pyautogui.scroll(amount),
    "hotkey_left": lambda **kwargs: pyautogui.hotkey('left'),
    "hotkey_right": lambda **kwargs: pyautogui.hotkey('right'),
    "hotkey_up": lambda **kwargs: pyautogui.hotkey('up'),
    "hotkey_down": lambda **kwargs: pyautogui.hotkey('down'),
    "hotkey_alt_left": lambda **kwargs: pyautogui.hotkey('alt', 'left'), # Example for browser back
    "hotkey_alt_right": lambda **kwargs: pyautogui.hotkey('alt', 'right'),# Example for browser forward
}

# --- Define Gesture Mappings for Different Application Profiles ---
# Each profile maps a GESTURE_NAME from config.py to an ACTION_KEY from BASE_ACTIONS.
APP_GESTURE_MAPPINGS = {
    "default": {
        config.GESTURE_MOUSE_MOVING: "mouse_move",
        config.GESTURE_LEFT_CLICK: "left_click",
        config.GESTURE_DOUBLE_CLICK: "double_click",
        config.GESTURE_DRAG_START: "mouse_down_left",
        config.GESTURE_DRAGGING: "mouse_drag", # Data (x,y) will be passed
        config.GESTURE_DRAG_DROP: "mouse_up_left",
        config.GESTURE_SCROLL_UP: "scroll",    # Data (amount) will be passed
        config.GESTURE_SCROLL_DOWN: "scroll",  # Data (amount, will be negative)
        config.GESTURE_SWIPE_LEFT: "hotkey_left",
        config.GESTURE_SWIPE_RIGHT: "hotkey_right",
        config.GESTURE_SWIPE_UP: "hotkey_up",
        config.GESTURE_SWIPE_DOWN: "hotkey_down",
        # config.GESTURE_NONE: "do_nothing", # Optional
        # config.GESTURE_SCROLL_MODE_ENGAGED: "do_nothing", # Usually just for display
    },
    "browser": { # Example: Web Browser
        config.GESTURE_MOUSE_MOVING: "mouse_move",
        config.GESTURE_LEFT_CLICK: "left_click",
        config.GESTURE_DOUBLE_CLICK: "double_click",
        config.GESTURE_DRAG_START: "mouse_down_left",
        config.GESTURE_DRAGGING: "mouse_drag",
        config.GESTURE_DRAG_DROP: "mouse_up_left",
        config.GESTURE_SCROLL_UP: "scroll",
        config.GESTURE_SCROLL_DOWN: "scroll",
        config.GESTURE_SWIPE_LEFT: "hotkey_alt_left",  # Browser Back
        config.GESTURE_SWIPE_RIGHT: "hotkey_alt_right", # Browser Forward
        config.GESTURE_SWIPE_UP: "hotkey_up",       # Page Up (or custom)
        config.GESTURE_SWIPE_DOWN: "hotkey_down",   # Page Down (or custom)
    },
    "designer": { # Example: Design Tool (e.g., Photoshop, Illustrator)
        config.GESTURE_MOUSE_MOVING: "mouse_move",
        config.GESTURE_LEFT_CLICK: "left_click",
        config.GESTURE_DOUBLE_CLICK: "double_click", # May not be used often
        config.GESTURE_DRAG_START: "mouse_down_left",
        config.GESTURE_DRAGGING: "mouse_drag",
        config.GESTURE_DRAG_DROP: "mouse_up_left",
        config.GESTURE_SCROLL_UP: "scroll", # Zoom in (often Ctrl+Scroll or Alt+Scroll)
        config.GESTURE_SCROLL_DOWN: "scroll",# Zoom out
        # Potentially map swipes to tool changes or undo/redo
        config.GESTURE_SWIPE_LEFT: "hotkey_ctrl_z", # Example: Undo (Ctrl+Z)
        config.GESTURE_SWIPE_RIGHT: "hotkey_ctrl_shift_z", # Example: Redo (Ctrl+Shift+Z)
        # You would add more custom BASE_ACTIONS for complex hotkeys
    }
}
# Add more complex hotkeys to BASE_ACTIONS if needed:
BASE_ACTIONS["hotkey_ctrl_z"] = lambda **kwargs: pyautogui.hotkey('ctrl', 'z')
BASE_ACTIONS["hotkey_ctrl_shift_z"] = lambda **kwargs: pyautogui.hotkey('ctrl', 'shift', 'z')


class ActionController:
    def __init__(self):
        pyautogui.FAILSAFE = config.PYAUTOGUI_FAILSAFE
        self.active_profile_name = app_detector.get_active_application_profile()
        self.current_gesture_map = APP_GESTURE_MAPPINGS.get(self.active_profile_name, APP_GESTURE_MAPPINGS["default"])
        print(f"ActionController initialized with profile: {self.active_profile_name}")

    def update_profile(self):
        new_profile_name = app_detector.get_active_application_profile()
        if new_profile_name != self.active_profile_name:
            self.active_profile_name = new_profile_name
            self.current_gesture_map = APP_GESTURE_MAPPINGS.get(self.active_profile_name, APP_GESTURE_MAPPINGS["default"])
            print(f"ActionController switched to profile: {self.active_profile_name}")


    def execute_action(self, gesture_name, gesture_data=None):
        """
        Executes a pyautogui action based on the recognized gesture and current app profile.
        Args:
            gesture_name (str): The name of the gesture from config.py (e.g., config.GESTURE_LEFT_CLICK).
            gesture_data (dict, optional): Data associated with the gesture (e.g., {'x':100, 'y':100} for move,
                                           {'amount': 5} for scroll).
        """
        if gesture_data is None:
            gesture_data = {}

        self.update_profile() # Check if profile changed

        action_key = self.current_gesture_map.get(gesture_name)

        if action_key and action_key in BASE_ACTIONS:
            action_function = BASE_ACTIONS[action_key]
            try:
                # Pass relevant data to the action function
                # The lambda functions in BASE_ACTIONS use **kwargs to accept these
                action_function(**gesture_data)

                # Special handling for swipe delays
                if gesture_name in [config.GESTURE_SWIPE_LEFT, config.GESTURE_SWIPE_RIGHT,
                                    config.GESTURE_SWIPE_UP, config.GESTURE_SWIPE_DOWN]:
                    time.sleep(config.SWIPE_ACTION_DELAY)

            except Exception as e:
                print(f"Error executing action '{action_key}' for gesture '{gesture_name}': {e}")
        # else:
            # No action mapped for this gesture in the current profile, or action key is invalid
            # print(f"No action mapped for gesture '{gesture_name}' in profile '{self.active_profile_name}'")
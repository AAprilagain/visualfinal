import pyautogui
import time
import config
import app_detector # To get the current application profile

# --- Define Base Actions ---
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
    "hotkey_ctrl_z": lambda **kwargs: pyautogui.hotkey('ctrl', 'z'),
    "hotkey_ctrl_shift_z": lambda **kwargs: pyautogui.hotkey('ctrl', 'shift', 'z'),
    # New keyboard actions
    "press_x": lambda **kwargs: pyautogui.press('x'),
    "press_z": lambda **kwargs: pyautogui.press('z'),
    "press_space": lambda **kwargs: pyautogui.press('space'),
}

# --- Define Gesture Mappings for Different Application Profiles ---
APP_GESTURE_MAPPINGS = {
    "default": {
        config.GESTURE_MOUSE_MOVING: "mouse_move",
        config.GESTURE_LEFT_CLICK: "left_click",
        config.GESTURE_DOUBLE_CLICK: "double_click",
        config.GESTURE_DRAG_START: "mouse_down_left",
        config.GESTURE_DRAGGING: "mouse_drag",
        config.GESTURE_DRAG_DROP: "mouse_up_left",
        config.GESTURE_SCROLL_UP: "scroll",
        config.GESTURE_SCROLL_DOWN: "scroll",
        config.GESTURE_SWIPE_LEFT: "hotkey_left",
        config.GESTURE_SWIPE_RIGHT: "hotkey_right",
        config.GESTURE_SWIPE_UP: "hotkey_up",
        config.GESTURE_SWIPE_DOWN: "hotkey_down",
    },
    "browser": {
        config.GESTURE_MOUSE_MOVING: "mouse_move",
        config.GESTURE_LEFT_CLICK: "left_click",
        config.GESTURE_DOUBLE_CLICK: "double_click",
        config.GESTURE_DRAG_START: "mouse_down_left",
        config.GESTURE_DRAGGING: "mouse_drag",
        config.GESTURE_DRAG_DROP: "mouse_up_left",
        config.GESTURE_SCROLL_UP: "scroll",
        config.GESTURE_SCROLL_DOWN: "scroll",
        config.GESTURE_SWIPE_LEFT: "hotkey_alt_left",
        config.GESTURE_SWIPE_RIGHT: "hotkey_alt_right",
        config.GESTURE_SWIPE_UP: "hotkey_up",
        config.GESTURE_SWIPE_DOWN: "hotkey_down",
    },
    "douyin": { # New Profile for Douyin/TikTok
        config.GESTURE_MOUSE_MOVING: "mouse_move",
        config.GESTURE_LEFT_CLICK: "do_nothing",       # Left click disabled
        config.GESTURE_DOUBLE_CLICK: "do_nothing",     # Optionally disable double click too or map to other action
        config.GESTURE_DRAG_START: "do_nothing",       # Disable dragging by default or map if needed
        config.GESTURE_DRAGGING: "do_nothing",
        config.GESTURE_DRAG_DROP: "do_nothing",
        config.GESTURE_SCROLL_UP: "press_space",            # Scroll up maps to 'space' (e.g., play/pause)
        config.GESTURE_SCROLL_DOWN: "press_x",            # Scroll down maps to 'x' (e.g., next video)
        config.GESTURE_SWIPE_LEFT: "do_nothing",          # Swipe Left disabled
        config.GESTURE_SWIPE_RIGHT: "do_nothing",         # Swipe Right disabled
        config.GESTURE_SWIPE_UP: "hotkey_up",        # Swipe Up (e.g., like)
        config.GESTURE_SWIPE_DOWN: "hotkey_down",      # Swipe Down (e.g., previous video)
        # Map other gestures as needed, or they will default to "do_nothing" if not in BASE_ACTIONS
    }
}


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
            gesture_data (dict, optional): Data associated with the gesture.
        """
        if gesture_data is None:
            gesture_data = {}

        self.update_profile() # Check if profile changed

        action_key = self.current_gesture_map.get(gesture_name)

        if action_key and action_key in BASE_ACTIONS:
            action_function = BASE_ACTIONS[action_key]
            try:
                action_function(**gesture_data)
                # Only apply swipe action delay if an actual swipe action was performed
                if gesture_name in [config.GESTURE_SWIPE_LEFT, config.GESTURE_SWIPE_RIGHT,
                                    config.GESTURE_SWIPE_UP, config.GESTURE_SWIPE_DOWN]:
                    time.sleep(config.SWIPE_ACTION_DELAY)
            except Exception as e:
                print(f"Error executing action '{action_key}' for gesture '{gesture_name}': {e}")
        # else:
        #     print(f"No action mapped for gesture '{gesture_name}' in profile '{self.active_profile_name}' or default, or action_key not in BASE_ACTIONS.")
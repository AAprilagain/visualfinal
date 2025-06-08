# action_controller.py

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
    "press_f": lambda **kwargs: pyautogui.press('f'),
    "press_h": lambda **kwargs: pyautogui.press('h'),
    "press_esc": lambda **kwargs: pyautogui.press('esc'),


}


class ActionController:
    def __init__(self, initial_mappings=None):
        pyautogui.FAILSAFE = config.PYAUTOGUI_FAILSAFE
        self.active_profile_name = app_detector.get_active_application_profile()
        # Initialize with provided mappings or default from config
        self.all_app_gesture_mappings = initial_mappings if initial_mappings is not None else config.CUSTOM_APP_GESTURE_MAPPINGS
        self.current_gesture_map = self.all_app_gesture_mappings.get(self.active_profile_name, self.all_app_gesture_mappings["default"])
        print(f"ActionController initialized with profile: {self.active_profile_name}")

        self.cooldown_until = 0.0

    def update_profile(self):
        new_profile_name = app_detector.get_active_application_profile()
        if new_profile_name != self.active_profile_name:
            self.active_profile_name = new_profile_name
            self.current_gesture_map = self.all_app_gesture_mappings.get(self.active_profile_name, self.all_app_gesture_mappings["default"])
            print(f"ActionController switched to profile: {self.active_profile_name}")

    def update_gesture_mappings(self, new_mappings):
        """
        Updates the internal gesture mappings with new ones from the UI.
        """
        self.all_app_gesture_mappings = new_mappings
        # Re-apply the current profile's map based on the new mappings
        self.current_gesture_map = self.all_app_gesture_mappings.get(self.active_profile_name, self.all_app_gesture_mappings["default"])
        print("ActionController mappings updated.")

    def execute_action(self, gesture_name, gesture_data=None):
        major_gestures = [
            config.GESTURE_SWIPE_LEFT, config.GESTURE_SWIPE_RIGHT,
            config.GESTURE_SWIPE_UP, config.GESTURE_SWIPE_DOWN,
            config.GESTURE_FIST_TO_OPEN, config.GESTURE_OPEN_TO_FIST
        ]

        if time.time() < self.cooldown_until and gesture_name in major_gestures:
            return

        if gesture_data is None:
            gesture_data = {}

        self.update_profile()

        action_key = self.current_gesture_map.get(gesture_name)

        if action_key and action_key in BASE_ACTIONS:
            action_function = BASE_ACTIONS[action_key]

            try:
                if action_key in ["mouse_move", "mouse_drag"]:
                    x, y = gesture_data.get('x'), gesture_data.get('y')
                    # print(f"DEBUG: Executing {action_key} to screen coordinates: X={x}, Y={y}")

                action_function(**gesture_data)

                if gesture_name in [config.GESTURE_SWIPE_LEFT, config.GESTURE_SWIPE_RIGHT,
                                    config.GESTURE_SWIPE_UP, config.GESTURE_SWIPE_DOWN,
                                    config.GESTURE_FIST_TO_OPEN, config.GESTURE_OPEN_TO_FIST]:
                    self.cooldown_until = time.time() + config.SWIPE_ACTION_DELAY

            except Exception as e:
                print(f"Error executing action '{action_key}' for gesture '{gesture_name}': {e}")
# action_controller.py
import pyautogui
import time
import config
import app_detector  # To get the current application profile

# --- Define Base Actions ---
BASE_ACTIONS = {
    "do_nothing": lambda **kwargs: None,
    "mouse_move": lambda x, y, **kwargs: pyautogui.moveTo(x, y, duration=config.PYAUTOGUI_MOVE_DURATION_MOUSE),
    "mouse_drag": lambda x, y, **kwargs: pyautogui.moveTo(x, y, duration=config.PYAUTOGUI_MOVE_DURATION_DRAG),
    # 注意：原代码这里是 moveTo，通常拖拽是 dragTo，但PyAutoGUI没有dragTo，而是mouseDown/moveTo/mouseUp序列
    "left_click": lambda **kwargs: pyautogui.click(),
    "double_click": lambda **kwargs: pyautogui.doubleClick(),
    "mouse_down_left": lambda **kwargs: pyautogui.mouseDown(button='left'),
    "mouse_up_left": lambda **kwargs: pyautogui.mouseUp(button='left'),
    "scroll": lambda amount, **kwargs: pyautogui.scroll(amount),
    "hotkey_left": lambda **kwargs: pyautogui.hotkey('left'),
    "hotkey_right": lambda **kwargs: pyautogui.hotkey('right'),
    "hotkey_up": lambda **kwargs: pyautogui.hotkey('up'),
    "hotkey_down": lambda **kwargs: pyautogui.hotkey('down'),
    "hotkey_alt_left": lambda **kwargs: pyautogui.hotkey('alt', 'left'),
    "hotkey_alt_right": lambda **kwargs: pyautogui.hotkey('alt', 'right'),
    "hotkey_ctrl_z": lambda **kwargs: pyautogui.hotkey('ctrl', 'z'),
    "hotkey_ctrl_shift_z": lambda **kwargs: pyautogui.hotkey('ctrl', 'shift', 'z'),
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
        # PyAutoGUI moveTo during drag is correct if mouse button is already down
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
    "douyin": {
        config.GESTURE_MOUSE_MOVING: "mouse_move",
        config.GESTURE_LEFT_CLICK: "do_nothing",
        config.GESTURE_DOUBLE_CLICK: "do_nothing",
        config.GESTURE_DRAG_START: "do_nothing",
        config.GESTURE_DRAGGING: "do_nothing",
        config.GESTURE_DRAG_DROP: "do_nothing",
        config.GESTURE_SCROLL_UP: "press_space",
        config.GESTURE_SCROLL_DOWN: "press_x",
        config.GESTURE_SWIPE_LEFT: "do_nothing",
        config.GESTURE_SWIPE_RIGHT: "do_nothing",
        config.GESTURE_SWIPE_UP: "hotkey_up",
        config.GESTURE_SWIPE_DOWN: "hotkey_down",
    }
}


class ActionController:
    def __init__(self):
        pyautogui.FAILSAFE = config.PYAUTOGUI_FAILSAFE
        self.active_profile_name = app_detector.get_active_application_profile()  #
        self.current_gesture_map = APP_GESTURE_MAPPINGS.get(self.active_profile_name,
                                                            APP_GESTURE_MAPPINGS["default"])  #
        print(f"ActionController initialized with profile: {self.active_profile_name}")  #
        self.last_swipe_action_time = 0  # 用于滑动动作的冷却时间

    def update_profile(self):
        new_profile_name = app_detector.get_active_application_profile()  #
        if new_profile_name != self.active_profile_name:  #
            self.active_profile_name = new_profile_name  #
            self.current_gesture_map = APP_GESTURE_MAPPINGS.get(self.active_profile_name,
                                                                APP_GESTURE_MAPPINGS["default"])  #
            print(f"ActionController switched to profile: {self.active_profile_name}")  #

    def execute_action(self, gesture_name, gesture_data=None):
        """
        Executes a pyautogui action based on the recognized gesture and current app profile.
        Args:
            gesture_name (str): The name of the gesture from config.py (e.g., config.GESTURE_LEFT_CLICK).
            gesture_data (dict, optional): Data associated with the gesture.
        """
        if gesture_data is None:
            gesture_data = {}

        self.update_profile()  # Check if profile changed

        action_key = self.current_gesture_map.get(gesture_name)  #

        if action_key and action_key in BASE_ACTIONS:  #
            action_function = BASE_ACTIONS[action_key]  #
            try:
                # --- 非阻塞滑动冷却逻辑 ---
                is_swipe_gesture = gesture_name in [config.GESTURE_SWIPE_LEFT, config.GESTURE_SWIPE_RIGHT,  #
                                                    config.GESTURE_SWIPE_UP, config.GESTURE_SWIPE_DOWN]  #

                if is_swipe_gesture:
                    current_time = time.time()
                    if current_time - self.last_swipe_action_time < config.SWIPE_ACTION_DELAY:
                        # print(f"Swipe action for {gesture_name} skipped due to cooldown.")
                        return  # 因为在冷却时间内，所以跳过此滑动动作
                    self.last_swipe_action_time = current_time  # 更新最后一次滑动动作的时间

                # 执行动作
                action_function(**gesture_data)  #

                # 原来的 time.sleep(config.SWIPE_ACTION_DELAY) 已被移除
                # 现在的冷却逻辑是防止连续快速触发，而不是在每次滑动后暂停

            except Exception as e:
                print(f"Error executing action '{action_key}' for gesture '{gesture_name}': {e}")  #
        # else:
        # print(f"No action mapped for gesture '{gesture_name}' in profile '{self.active_profile_name}' or default, or action_key not in BASE_ACTIONS.")
import pyautogui
import time
import config
import app_detector  # To get the current application profile
import utils

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
    "hotkey_alt_left": lambda **kwargs: pyautogui.hotkey('alt', 'left'),  # Example for browser back
    "hotkey_alt_right": lambda **kwargs: pyautogui.hotkey('alt', 'right'),  # Example for browser forward
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
        config.GESTURE_LEFT_CLICK: "left_click",  #
        config.GESTURE_DOUBLE_CLICK: "double_click",
        config.GESTURE_DRAG_START: "mouse_down_left",
        config.GESTURE_DRAGGING: "mouse_drag",
        config.GESTURE_DRAG_DROP: "mouse_up_left",
        config.GESTURE_SCROLL_UP: "scroll",
        config.GESTURE_SCROLL_DOWN: "scroll",
        config.GESTURE_SWIPE_LEFT: "hotkey_left",  #
        config.GESTURE_SWIPE_RIGHT: "hotkey_right",  #
        config.GESTURE_SWIPE_UP: "hotkey_up",  #
        config.GESTURE_SWIPE_DOWN: "hotkey_down",  #
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
    "douyin": {  # New Profile for Douyin/TikTok
        config.GESTURE_MOUSE_MOVING: "mouse_move",
        config.GESTURE_LEFT_CLICK: "do_nothing",  # Left click disabled
        config.GESTURE_DOUBLE_CLICK: "double_click",  # Optionally disable double click too or map to other action
        config.GESTURE_DRAG_START: "do_nothing",  # Disable dragging by default or map if needed
        config.GESTURE_DRAGGING: "do_nothing",
        config.GESTURE_DRAG_DROP: "do_nothing",
        config.GESTURE_SCROLL_UP: "press_space",  # Keep scroll for feed navigation
        config.GESTURE_SCROLL_DOWN: "press_x",
        config.GESTURE_SWIPE_LEFT: "do_nothing",  # Swipe Left maps to 'x' key
        config.GESTURE_SWIPE_RIGHT: "do_nothing",  # Swipe Right maps to 'z' key
        config.GESTURE_SWIPE_UP: "hotkey_up",  # Swipe Up maps to 'space' key (e.g., for 'like' or 'play/pause')
        config.GESTURE_SWIPE_DOWN: "hotkey_down",  # Swipe Down could be page down or another action
        # Map other gestures as needed, or they will default to "do_nothing" if not in BASE_ACTIONS
    }
}


class ActionController:
    def __init__(self):
        pyautogui.FAILSAFE = config.PYAUTOGUI_FAILSAFE  #
        self.active_profile_name = app_detector.get_active_application_profile()  #
        self.current_gesture_map = APP_GESTURE_MAPPINGS.get(self.active_profile_name, APP_GESTURE_MAPPINGS["default"])
        print(f"ActionController initialized with profile: {self.active_profile_name}")

        # 新增平滑处理相关参数
        self.mouse_filter_window = 2  # 滤波窗口大小（2-5帧平衡延迟与平滑）
        self.mouse_position_history = []  # 坐标历史缓存
        self.last_smoothed_pos = (0, 0)  # 上一次处理后的坐标
        self.drag_filter_factor = 0.3  # 拖拽状态滤波系数（0=完全跟随原始坐标，1=完全保持旧值）

    def update_profile(self):
        new_profile_name = app_detector.get_active_application_profile()  #
        if new_profile_name != self.active_profile_name:
            self.active_profile_name = new_profile_name
            self.current_gesture_map = APP_GESTURE_MAPPINGS.get(self.active_profile_name,
                                                                APP_GESTURE_MAPPINGS["default"])
            print(f"ActionController switched to profile: {self.active_profile_name}")

    def _smooth_mouse_position(self, new_x, new_y, is_dragging=False):
        """应用移动平滑算法"""
        # 去抖：忽略微小移动
        if utils.calculate_distance_2d((new_x, new_y), self.last_smoothed_pos) < config.MIN_MOVE_DISTANCE:
            return self.last_smoothed_pos

        # 动态窗口调整：拖拽时使用更小延迟的滤波
        window_size = self.mouse_filter_window if not is_dragging else max(2, self.mouse_filter_window - 1)

        # 使用加权移动平均滤波
        self.mouse_position_history.append((new_x, new_y))
        if len(self.mouse_position_history) > window_size:
            self.mouse_position_history.pop(0)

        # 计算加权平均值（最近点权重更高）
        total_weight = 0.0
        weighted_x, weighted_y = 0.0, 0.0
        for i, (x, y) in enumerate(self.mouse_position_history):
            weight = (i + 1) / len(self.mouse_position_history)  # 线性权重
            weighted_x += x * weight
            weighted_y += y * weight
            total_weight += weight

        smoothed_x = weighted_x / total_weight
        smoothed_y = weighted_y / total_weight

        # 拖拽状态额外应用惯性滤波
        if is_dragging:
            smoothed_x = self.drag_filter_factor * self.last_smoothed_pos[0] + (
                    1 - self.drag_filter_factor) * smoothed_x
            smoothed_y = self.drag_filter_factor * self.last_smoothed_pos[1] + (
                    1 - self.drag_filter_factor) * smoothed_y

        self.last_smoothed_pos = (smoothed_x, smoothed_y)
        return self.last_smoothed_pos

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

        action_key = self.current_gesture_map.get(gesture_name)

        if action_key and action_key in BASE_ACTIONS:
            if action_key in ["mouse_move", "mouse_drag"] and "x" in gesture_data and "y" in gesture_data:
                raw_x, raw_y = gesture_data["x"], gesture_data["y"]
                # 应用平滑处理（拖拽状态使用不同参数）
                smoothed_x, smoothed_y = self._smooth_mouse_position(
                    raw_x, raw_y,
                    is_dragging=(gesture_name == config.GESTURE_DRAGGING)
                )
                gesture_data.update({"x": smoothed_x, "y": smoothed_y})
            action_function = BASE_ACTIONS[action_key]
            try:
                action_function(**gesture_data)
                if gesture_name in [config.GESTURE_SWIPE_LEFT, config.GESTURE_SWIPE_RIGHT,  #
                                    config.GESTURE_SWIPE_UP, config.GESTURE_SWIPE_DOWN]:  #
                    time.sleep(config.SWIPE_ACTION_DELAY)  #
            except Exception as e:
                print(f"Error executing action '{action_key}' for gesture '{gesture_name}': {e}")
        # else: # This part can be un-commented for debugging missing mappings
        # action_in_default = APP_GESTURE_MAPPINGS["default"].get(gesture_name)
        # if action_in_default and action_in_default in BASE_ACTIONS and self.active_profile_name != "default":
        #     # Fallback to default profile's action if not specifically mapped in current profile
        #     # and the action is not "do_nothing" (or handle "do_nothing" explicitly if needed)
        #     # print(f"Gesture '{gesture_name}' not in profile '{self.active_profile_name}', trying default.")
        #     # BASE_ACTIONS[action_in_default](**gesture_data)
        # else:
        #     print(f"No action mapped for gesture '{gesture_name}' in profile '{self.active_profile_name}' or default.")

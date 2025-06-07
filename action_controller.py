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

# --- Define Gesture Mappings for Different Application Profiles ---
APP_GESTURE_MAPPINGS = {
    "default": {
        config.GESTURE_MOUSE_MOVING: "mouse_move",
        config.GESTURE_LEFT_CLICK: "left_click",
        config.GESTURE_DOUBLE_CLICK: "double_click",
        config.GESTURE_DRAG_START: "left_click",
        config.GESTURE_DRAGGING: "do_nothing",
        config.GESTURE_DRAG_DROP: "do_nothing",
        config.GESTURE_SCROLL_UP: "scroll",
        config.GESTURE_SCROLL_DOWN: "scroll",
        config.GESTURE_SWIPE_LEFT: "hotkey_left",
        config.GESTURE_SWIPE_RIGHT: "hotkey_right",
        config.GESTURE_SWIPE_UP: "hotkey_up",
        config.GESTURE_SWIPE_DOWN: "hotkey_down",
        config.GESTURE_FIST_TO_OPEN: "press_f", 
        config.GESTURE_OPEN_TO_FIST: "press_esc", 
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
        config.GESTURE_FIST_TO_OPEN: "do_nothing",
        config.GESTURE_OPEN_TO_FIST: "do_nothing",
    },
    "douyin": {
        config.GESTURE_MOUSE_MOVING: "mouse_move",
        config.GESTURE_LEFT_CLICK: "left_click",
        config.GESTURE_DOUBLE_CLICK: "double_click",
        config.GESTURE_DRAG_START: "do_nothing",
        config.GESTURE_DRAGGING: "do_nothing",
        config.GESTURE_DRAG_DROP: "hotkey_up",
        config.GESTURE_SCROLL_UP: "scroll",
        config.GESTURE_SCROLL_DOWN: "scroll",
        config.GESTURE_SWIPE_LEFT: "hotkey_down",
        config.GESTURE_SWIPE_RIGHT: "hotkey_down",
        config.GESTURE_SWIPE_UP: "hotkey_down",
        config.GESTURE_SWIPE_DOWN: "hotkey_down",
        config.GESTURE_FIST_TO_OPEN: "press_h",
        config.GESTURE_OPEN_TO_FIST: "press_esc",
    },
    "bilibili": {
            config.GESTURE_MOUSE_MOVING: "mouse_move",
            config.GESTURE_LEFT_CLICK: "left_click",
            config.GESTURE_DOUBLE_CLICK: "do_nothing",
            config.GESTURE_DRAG_START: "do_nothing",
            config.GESTURE_DRAGGING: "do_nothing",
            config.GESTURE_DRAG_DROP: "do_nothing",
            config.GESTURE_SCROLL_UP: "scroll",
            config.GESTURE_SCROLL_DOWN: "scroll",
            config.GESTURE_SWIPE_LEFT: "hotkey_left",
            config.GESTURE_SWIPE_RIGHT: "hotkey_right",
            config.GESTURE_SWIPE_UP: "hotkey_up",
            config.GESTURE_SWIPE_DOWN: "hotkey_down",
            config.GESTURE_FIST_TO_OPEN: "press_f",
            config.GESTURE_OPEN_TO_FIST: "press_esc",
        }
}


class ActionController:
    def __init__(self):
        pyautogui.FAILSAFE = config.PYAUTOGUI_FAILSAFE
        self.active_profile_name = app_detector.get_active_application_profile()
        self.current_gesture_map = APP_GESTURE_MAPPINGS.get(self.active_profile_name, APP_GESTURE_MAPPINGS["default"])
        print(f"ActionController initialized with profile: {self.active_profile_name}")

        # --- 新增代码 ---
        # 用于记录冷却截止的时间戳，初始化为0.0表示没有冷却
        self.cooldown_until = 0.0

    def update_profile(self):
        new_profile_name = app_detector.get_active_application_profile()
        if new_profile_name != self.active_profile_name:
            self.active_profile_name = new_profile_name
            self.current_gesture_map = APP_GESTURE_MAPPINGS.get(self.active_profile_name, APP_GESTURE_MAPPINGS["default"])
            print(f"ActionController switched to profile: {self.active_profile_name}")


    def execute_action(self, gesture_name, gesture_data=None):
        # --- 新增代码：非阻塞冷却检查 ---
        # 1. 定义哪些是需要被冷却的“大动作”
        major_gestures = [
            config.GESTURE_SWIPE_LEFT, config.GESTURE_SWIPE_RIGHT,
            config.GESTURE_SWIPE_UP, config.GESTURE_SWIPE_DOWN,
            config.GESTURE_FIST_TO_OPEN, config.GESTURE_OPEN_TO_FIST
        ]

        # 2. 修改判断条件：仅当“处于冷却期”并且“当前手势是大动作”时，才屏蔽它
        if time.time() < self.cooldown_until and gesture_name in major_gestures:
            return  # 屏蔽连续的大动作

        # 如果是捏合/拖拽/移动等小动作，则会跳过上面的if判断，继续执行
        if gesture_data is None:
            gesture_data = {}

        self.update_profile()

        action_key = self.current_gesture_map.get(gesture_name)

        if action_key and action_key in BASE_ACTIONS:
            action_function = BASE_ACTIONS[action_key]

            try:
                # --- 在此添加调试打印 ---
                if action_key in ["mouse_move", "mouse_drag"]:
                    x, y = gesture_data.get('x'), gesture_data.get('y')
                    print(f"DEBUG: Executing {action_key} to screen coordinates: X={x}, Y={y}")
                # --- 调试代码结束 ---
                
                action_function(**gesture_data)

                # --- 修改代码：用设置冷却时间戳替换 time.sleep() ---
                if gesture_name in [config.GESTURE_SWIPE_LEFT, config.GESTURE_SWIPE_RIGHT,
                                    config.GESTURE_SWIPE_UP, config.GESTURE_SWIPE_DOWN,
                                    config.GESTURE_FIST_TO_OPEN, config.GESTURE_OPEN_TO_FIST]:
                    # 不再使用 time.sleep()，而是更新冷却截止时间
                    self.cooldown_until = time.time() + config.SWIPE_ACTION_DELAY
                    
            except Exception as e:
                print(f"Error executing action '{action_key}' for gesture '{gesture_name}': {e}")
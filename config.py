import pyautogui
import mediapipe as mp

mp_hands = mp.solutions.hands
# Screen Dimensions (initialize once)
SCREEN_W, SCREEN_H = pyautogui.size()

# 在一次手势状态重置后，需要一个短暂的冷却时间，以防止旧手势的结尾被误判为新手势的开始
GESTURE_DEBOUNCE_DELAY = 0.3  # seconds

# MediaPipe Hands Configuration
MAX_NUM_HANDS = 1
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.5

# Gesture Parameters
# PINCH_THRESHOLD_CLOSE = 0.05          # Normalized distance for pinch
# PINCH_THRESHOLD_OPEN = 0.10           # Normalized distance for pinch release (new)
DOUBLE_CLICK_INTERVAL = 0.3             # Seconds
DRAG_CONFIRM_DURATION = 1               # Seconds to hold pinch before drag  # Reduced for responsiveness
# DRAG_CONFIRM_MOVEMENT_THRESHOLD = 20  # Pixels moved while pinched to confirm drag (reduced)

# 定义捏合关闭的阈值：当指尖距离小于手掌参考尺寸的 15% 时，视为捏合
PINCH_CLOSE_RATIO = 0.15
# 定义捏合张开的阈值：当指尖距离大于手掌参考尺寸的 25% 时，视为张开
PINCH_OPEN_RATIO = 0.25

# Scroll Control Parameters
SCROLL_MOVEMENT_THRESHOLD_Y = 0.005     # Min normalized vertical wrist movement for scroll (Adjusted for finger)
SCROLL_SENSITIVITY_FACTOR = 2000        # Multiplier for scroll amount
SCROLL_ENGAGE_HOLD_TIME = 0.8           # 触发scroll的最小维持时间

# Swipe Gesture Parameters
SWIPE_THRESHOLD_SPEED = 0.1             # Normalized units/second for swipe
SWIPE_ACTION_DELAY = 1                  # Seconds to wait after a swipe action
SWIPE_MIN_DISTANCE_NORM = 0.01          # Minimum normalized distance for a swipe to be considered valid
SWIPE_MIN_DISTANCE = 0.1                # 归一化距离，挥手需要的最小距离 (0.15约为屏幕宽度的15%)
SWIPE_MAX_DURATION = 0.4                # 秒，完成挥手所需的最大时间
SWIPE_VELOCITY_THRESHOLD = 0.025
SWIPE_COOLDOWN = 0.2                    # 张手握拳0.2秒后才判断挥手

# New: Fist/Open Hand Gesture Parameters
FIST_CLOSED_THRESHOLD = 0.15            # Adjusted: Increased to be more tolerant for 'closed' state
HAND_OPEN_THRESHOLD = 0.2               # Adjusted: Increased to be more tolerant for 'open' state
FINGER_CURL_TOLERANCE = 0.03            # New: Add a small tolerance for finger curl check
GESTURE_TRANSITION_TIME = 0.1           # Time in seconds for a hand state transition to be considered a gesture

# Mouse Movement Mapping
MOUSE_MAP_X_MIN = 0.25                   # Normalized hand x-coordinate to map to screen left
MOUSE_MAP_X_MAX = 0.75                   # Normalized hand x-coordinate to map to screen right
MOUSE_MAP_Y_MIN = 0.05                   # Normalized hand y-coordinate to map to screen top
MOUSE_MAP_Y_MAX = 0.55                   # Normalized hand y-coordinate to map to screen bottom
MOUSE_SMOOTHING_FACTOR = 0.25           # Lower is smoother but more 'laggy', higher is more responsive but less smooth. 0.2 is a good start.

# PyAutoGUI Settings
PYAUTOGUI_FAILSAFE = False
PYAUTOGUI_MOVE_DURATION_MOUSE = 0.01
PYAUTOGUI_MOVE_DURATION_DRAG = 0.01
pyautogui.PAUSE = 0.01
pyautogui.MINIMUM_DURATION = 0.01

# Frame rate assumption (for speed calculation if time delta isn't precise)
ASSUMED_FPS = 60

# --- Gesture Names (Used for recognition and mapping) ---
GESTURE_NONE = "No Gesture"
GESTURE_MOUSE_MOVING = "Mouse Moving"

GESTURE_LEFT_CLICK = "Left Click"
GESTURE_DOUBLE_CLICK = "Double Click"

GESTURE_DRAG_START = "Drag Start"
GESTURE_DRAGGING = "Dragging"
GESTURE_DRAG_DROP = "Drag Drop"

GESTURE_SCROLL_MODE_ENGAGED = "Scroll Mode Engaged"
GESTURE_SCROLL_UP = "Scroll Up"
GESTURE_SCROLL_DOWN = "Scroll Down"

GESTURE_SWIPE_LEFT = "Swipe Left"
GESTURE_SWIPE_RIGHT = "Swipe Right"
GESTURE_SWIPE_UP = "Swipe Up"
GESTURE_SWIPE_DOWN = "Swipe Down"

# New Gestures
GESTURE_FIST_TO_OPEN = "Fist to Open"
GESTURE_OPEN_TO_FIST = "Open to Fist"
GESTURE_PRESS_ESC = "Press ESC"


# --- New: State Definitions for Gesture Recognition State Machine ---
STATE_IDLE = "IDLE"
STATE_MOUSE_MOVING = "MOUSE_MOVING"
STATE_PINCH_DETECTED = "PINCH_DETECTED"
STATE_POSSIBLE_DOUBLE_CLICK = "POSSIBLE_DOUBLE_CLICK"
STATE_DRAGGING = "DRAGGING"
STATE_SCROLL_MODE = "SCROLL_MODE"
STATE_SWIPE_PENDING = "SWIPE_PENDING"
STATE_HAND_CLOSED_STEADY = "HAND_CLOSED_STEADY"
STATE_HAND_OPEN_STEADY = "HAND_OPEN_STEADY"

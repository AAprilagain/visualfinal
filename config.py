import pyautogui
import mediapipe as mp

mp_hands = mp.solutions.hands
# Screen Dimensions (initialize once)
SCREEN_W, SCREEN_H = pyautogui.size()

# MediaPipe Hands Configuration
MAX_NUM_HANDS = 1
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.5

# Gesture Parameters
PINCH_THRESHOLD_CLOSE = 0.08  # Adjusted for pinch-drag only
PINCH_THRESHOLD_OPEN = 0.09 # Adjusted for pinch-drag only

# DOUBLE_CLICK_INTERVAL remains relevant for the new swing-based double click
DOUBLE_CLICK_INTERVAL = 0.4  # Seconds between the completion of two swings for a double click

# Drag parameters (were previously mixed with pinch-click)
DRAG_CONFIRM_DURATION = 0.15 # Seconds to hold pinch before drag can start
DRAG_CONFIRM_MOVEMENT_THRESHOLD = 20 # Pixels moved while pinched to confirm drag

CLICK_EVALUATION_PERIOD = 0.4

# Scroll Control Parameters
SCROLL_MOVEMENT_THRESHOLD_Y = 0.005
SCROLL_SENSITIVITY_FACTOR = 150
# SCROLL_ENGAGE_THRESHOLD = 0.1 # This might need review if thumb state is critical
SCROLL_MODE_CONFIRM_DELAY = 0.3 # Reduced delay for scroll confirmation

# Swipe Gesture Parameters
SWIPE_THRESHOLD_SPEED = 0.1
SWIPE_ACTION_DELAY = 1
SWIPE_MIN_DISTANCE_NORM = 0.05

# --- New Click/Double Click Gesture Parameters ---
# For index + middle finger closed, downward swing click
CLICK_FINGERS_CLOSED_Y_OFFSET = 0.005 # Tip Y must be > PIP Y - offset (larger Y is lower on screen)
CLICK_ARM_MAX_DURATION = 0.4       # Max time to hold fingers closed *before* initiating a swing
CLICK_SWING_MIN_Y_DISPLACEMENT_NORM = 0.025 # Min normalized Y movement of finger base for a swing
CLICK_SWING_MAX_DURATION = 0.35    # Max duration for one swing action to complete after starting

# Mouse Movement Mapping (remains the same)
MOUSE_MAP_X_MIN = 0.2
MOUSE_MAP_X_MAX = 0.8
MOUSE_MAP_Y_MIN = 0.2
MOUSE_MAP_Y_MAX = 0.8

# PyAutoGUI Settings (remains the same)
PYAUTOGUI_FAILSAFE = False
PYAUTOGUI_MOVE_DURATION_MOUSE = 0.01
PYAUTOGUI_MOVE_DURATION_DRAG = 0.01
pyautogui.PAUSE = 0.01  # 将每次调用后的默认暂停时间从0.1秒改为0秒
pyautogui.MINIMUM_DURATION = 0.01 # 将鼠标移动的最小持续时间从0.1秒改为0秒（允许非常快速的移动）

ASSUMED_FPS = 60

# --- Gesture Names ---
# GESTURE_LEFT_CLICK and GESTURE_DOUBLE_CLICK will now refer to the new swing gesture
GESTURE_NONE = "No Gesture"
GESTURE_MOUSE_MOVING = "Mouse Moving"
GESTURE_LEFT_CLICK = "Left Click (Swing)"
GESTURE_DOUBLE_CLICK = "Double Click (Swing)"
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

# --- State Definitions ---
STATE_IDLE = "IDLE"
STATE_PINCH_DETECTED = "PINCH_DETECTED" # Now primarily for drag
# STATE_POSSIBLE_DOUBLE_CLICK removed as new click logic handles it differently
STATE_DRAGGING = "DRAGGING"
STATE_SCROLL_MODE = "SCROLL_MODE"
STATE_SWIPE_PENDING = "SWIPE_PENDING"
STATE_SCROLL_MODE_PENDING = "SCROLL_PENDING"

# New states for the swing click mechanism
STATE_CLICK_ARMED = "CLICK_ARMED" # Index and Middle fingers are closed, waiting for swing
STATE_AWAITING_SECOND_SWING = "AWAITING_SECOND_SWING" # First swing done, waiting for second or timeout

# --- Application Profiles ---
# Example:
# APP_PROFILE_DEFAULT = "default"
# APP_PROFILE_BROWSER = "browser"
# CURRENT_APP_PROFILE = APP_PROFILE_DEFAULT # Can be changed dynamically


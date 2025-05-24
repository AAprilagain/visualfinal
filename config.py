import pyautogui

# Screen Dimensions (initialize once)
SCREEN_W, SCREEN_H = pyautogui.size()

# MediaPipe Hands Configuration
MAX_NUM_HANDS = 1
MIN_DETECTION_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.5

# Gesture Parameters
PINCH_THRESHOLD_CLOSE = 0.05  # Normalized distance for pinch
# PINCH_THRESHOLD_OPEN = 0.07 # (If needed for release)

DOUBLE_CLICK_INTERVAL = 0.4  # Seconds
DRAG_CONFIRM_DURATION = 0.20 # Seconds to hold pinch before drag
DRAG_CONFIRM_MOVEMENT = 25   # Pixels moved while pinched to confirm drag

# Scroll Control Parameters
SCROLL_MOVEMENT_THRESHOLD_Y = 0.010  # Min normalized vertical wrist movement for scroll
SCROLL_SENSITIVITY_FACTOR = 150     # Multiplier for scroll amount

# Swipe Gesture Parameters
SWIPE_THRESHOLD_SPEED = 0.2  # Normalized units/second for swipe
SWIPE_ACTION_DELAY = 0.5     # Seconds to wait after a swipe action

# Mouse Movement Mapping
MOUSE_MAP_X_MIN = 0.2  # Normalized hand x-coordinate to map to screen left
MOUSE_MAP_X_MAX = 0.8  # Normalized hand x-coordinate to map to screen right
MOUSE_MAP_Y_MIN = 0.2  # Normalized hand y-coordinate to map to screen top
MOUSE_MAP_Y_MAX = 0.8  # Normalized hand y-coordinate to map to screen bottom

# PyAutoGUI Settings
PYAUTOGUI_FAILSAFE = False
PYAUTOGUI_MOVE_DURATION_MOUSE = 0.1  # Duration for general mouse movements
PYAUTOGUI_MOVE_DURATION_DRAG = 0.05 # Duration for mouse movements during drag

# Frame rate assumption (for speed calculation if time delta isn't precise)
ASSUMED_FPS = 30

# --- Gesture Names (Used for recognition and mapping) ---
# These can be expanded or modified as needed.
GESTURE_NONE = "No Gesture"
GESTURE_MOUSE_MOVING = "Mouse Moving"

GESTURE_PINCH_START = "Pinch Start" # Internal state, might not map directly to action
GESTURE_LEFT_CLICK = "Left Click"
GESTURE_DOUBLE_CLICK = "Double Click"

GESTURE_DRAG_START = "Drag Start"
GESTURE_DRAGGING = "Dragging"
GESTURE_DRAG_DROP = "Drag Drop"

GESTURE_SCROLL_MODE_ENGAGED = "Scroll Mode (Thumbs Up)"
GESTURE_SCROLL_UP = "Scroll Up"
GESTURE_SCROLL_DOWN = "Scroll Down"

GESTURE_SWIPE_LEFT = "Swipe Left"
GESTURE_SWIPE_RIGHT = "Swipe Right"
GESTURE_SWIPE_UP = "Swipe Up"
GESTURE_SWIPE_DOWN = "Swipe Down"

# --- Application Profiles ---
# Example:
# APP_PROFILE_DEFAULT = "default"
# APP_PROFILE_BROWSER = "browser"
# CURRENT_APP_PROFILE = APP_PROFILE_DEFAULT # Can be changed dynamically
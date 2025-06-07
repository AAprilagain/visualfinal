# Placeholder for active application detection
# For a real implementation, you would use OS-specific libraries
# like pywin32 (Windows), AppKit (macOS), or python-xlib (Linux).
# Using pygetwindow for a cross-platform attempt.
import pygetwindow as gw

_current_app_profile_name = "default" # Default profile

SUPPORTED_PROFILES = {
    "default": "Default Profile",
    "browser": "Web Browser Profile",
    "douyin": "Douyin Profile",
    "bilibili": "bilibili Profile"  # Added Douyin profile
}
_profile_keys = list(SUPPORTED_PROFILES.keys())
_current_profile_index = 0 # Ensure this starts at 'default' if 'default' is the first key

# Initialize _current_app_profile_name to the first key in _profile_keys
if _profile_keys:
    _current_app_profile_name = _profile_keys[0]
    _current_profile_index = 0


def get_active_application_profile():
    """
    Returns the name of the current application profile.
    Attempts to detect the active window's application.
    """
    global _current_app_profile_name # Ensure we are modifying the global variable

    if gw:
        try:
            active_window = gw.getActiveWindow()
            if active_window:
                window_title = active_window.title.lower()
                # print(f"Active window: {window_title}") # For debugging
                if "抖音" in window_title:
                    return "douyin"
                elif "chrome" in window_title or "firefox" in window_title or "edge" in window_title:
                    return "browser"
                elif "哔哩哔哩" in window_title:
                    return "bilibili"
                # Add other application detection logic here
        except Exception as e:
            # print(f"Error detecting active window: {e}") # Might be too noisy
            # Fallback to the manually cycled profile if detection fails
            return _current_app_profile_name
    # Fallback to the manually cycled profile if pygetwindow is not available or fails
    return _current_app_profile_name

def cycle_app_profile():
    """
    Cycles through available application profiles.
    This is a manual override.
    """
    global _current_app_profile_name, _current_profile_index
    _current_profile_index = (_current_profile_index + 1) % len(_profile_keys)
    _current_app_profile_name = _profile_keys[_current_profile_index]
    print(f"Manually switched to profile: {SUPPORTED_PROFILES[_current_app_profile_name]}")
    return _current_app_profile_name

def get_current_profile_display_name():
    # Use the result of the detection, not the manually cycled one directly,
    # unless manual cycling is the only source of truth.
    # For this setup, get_active_application_profile now incorporates detection.
    detected_profile = get_active_application_profile()
    return SUPPORTED_PROFILES.get(detected_profile, "Unknown Profile")
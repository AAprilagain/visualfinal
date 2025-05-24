# Placeholder for active application detection
# For a real implementation, you would use OS-specific libraries
# like pywin32 (Windows), AppKit (macOS), or python-xlib (Linux).

_current_app_profile_name = "default" # Default profile

SUPPORTED_PROFILES = {
    "default": "Default Profile",
    "browser": "Web Browser Profile",
    "designer": "Design Tool Profile"
    # Add more profiles as needed
}
_profile_keys = list(SUPPORTED_PROFILES.keys())
_current_profile_index = 0

def get_active_application_profile():
    """
    Returns the name of the current application profile.
    In a real scenario, this would detect the active window's application
    and return a corresponding profile name (e.g., "chrome", "photoshop", "default").
    """
    global _current_app_profile_name
    return _current_app__profile_name

def cycle_app_profile():
    """
    Cycles through available application profiles.
    This is a manual override for demonstration.
    """
    global _current_app_profile_name, _current_profile_index
    _current_profile_index = (_current_profile_index + 1) % len(_profile_keys)
    _current_app_profile_name = _profile_keys[_current_profile_index]
    print(f"Switched to profile: {SUPPORTED_PROFILES[_current_app_profile_name]}")
    return _current_app_profile_name

def get_current_profile_display_name():
    return SUPPORTED_PROFILES.get(get_active_application_profile(), "Unknown Profile")
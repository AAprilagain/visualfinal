import numpy as np
from math import hypot
import config

def calculate_distance_3d(lm1, lm2):
    """Calculates the 3D Euclidean distance between two landmark points."""
    return hypot(lm1.x - lm2.x, lm1.y - lm2.y, lm1.z - lm2.z)

def calculate_distance_2d(p1, p2):
    """Calculates the 2D Euclidean distance between two screen points."""
    return hypot(p1[0] - p2[0], p1[1] - p2[1])

def calculate_movement_2d_normalized(lm1, lm2):
    """Calculates the 2D movement (dx, dy) between two normalized landmark points."""
    dx = lm2.x - lm1.x
    dy = lm2.y - lm1.y
    return dx, dy

def get_finger_extended_states(landmarks):
    """
    Checks if fingers are extended.
    Returns: list[bool]: [Index, Middle, Ring, Pinky]
    """
    states = []
    # Index, Middle, Ring, Pinky
    # Using more robust check: tip should be significantly higher (lower y) than both DIP and PIP
    for tip_idx, dip_idx, pip_idx in [(8, 6, 5), (12, 10, 9), (16, 14, 13), (20, 18, 17)]:
        # Finger is extended if tip is above DIP and PIP joints
        # (assuming hand is upright, lower y means higher up)
        states.append(landmarks[tip_idx].y < landmarks[dip_idx].y and \
                      landmarks[dip_idx].y < landmarks[pip_idx].y)
    return states

def is_thumb_extended(landmarks):
    """Checks if the thumb is extended (tip higher than knuckle)."""
    # Thumb is extended if tip (4) is above MCP joint (2)
    # Adding a small threshold to avoid minor fluctuations
    return landmarks[4].y < landmarks[3].y and landmarks[3].y < landmarks[2].y


def map_to_screen(x_normalized, y_normalized):
    """Maps normalized hand coordinates to actual screen coordinates."""
    screen_x = np.interp(x_normalized,
                         [config.MOUSE_MAP_X_MIN, config.MOUSE_MAP_X_MAX],
                         [0, config.SCREEN_W])
    screen_y = np.interp(y_normalized,
                         [config.MOUSE_MAP_Y_MIN, config.MOUSE_MAP_Y_MAX],
                         [0, config.SCREEN_H])
    return int(screen_x), int(screen_y)

def get_pinch_midpoint_normalized(thumb_tip, index_tip):
    """Calculates the normalized midpoint between thumb and index finger tips."""
    mid_x = (thumb_tip.x + index_tip.x) / 2
    mid_y = (thumb_tip.y + index_tip.y) / 2
    return mid_x, mid_y
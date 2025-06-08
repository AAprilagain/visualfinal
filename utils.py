import numpy as np
from math import hypot
import config
import mediapipe as mp

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

def calculate_landmark_distance_2d(lm1, lm2):
    """仅使用X, Y坐标计算两个landmark之间的2D欧几里得距离。"""
    return hypot(lm1.x - lm2.x, lm1.y - lm2.y)


def get_finger_extended_states(landmarks):
    """
    Checks if fingers are extended.
    Returns: list[bool]: [Index, Middle, Ring, Pinky]
    """
    states = []
    # Using more robust check: tip should be significantly higher (lower y) than both DIP and PIP
    # For each finger (index, middle, ring, pinky)
    # Check if tip is above (lower y) than DIP, and DIP is above PIP.
    # This assumes an upright hand posture.
    for tip_idx, dip_idx, pip_idx in [(8, 6, 5), (12, 10, 9), (16, 14, 13), (20, 18, 17)]:
        # Apply FINGER_CURL_TOLERANCE for more robust detection of curled state
        is_extended = (landmarks[tip_idx].y < landmarks[dip_idx].y - config.FINGER_CURL_TOLERANCE and
                       landmarks[dip_idx].y < landmarks[pip_idx].y - config.FINGER_CURL_TOLERANCE)
        states.append(is_extended)
    return states

# 用下面的新函数替换旧的 is_thumb_extended
def is_thumb_extended(landmarks):
    """
    使用可靠的“腕部距离法”检查大拇指的伸展状态。
    如果指尖离手腕的2D距离大于其中间关节(IP)离手腕的距离，则视为伸展。
    """
    try:
        wrist_lm = landmarks[mp.solutions.hands.HandLandmark.WRIST]
        thumb_tip_lm = landmarks[mp.solutions.hands.HandLandmark.THUMB_TIP]
        thumb_ip_lm = landmarks[mp.solutions.hands.HandLandmark.THUMB_IP] # 大拇指的中间关节
        
        dist_wrist_to_tip = calculate_landmark_distance_2d(wrist_lm, thumb_tip_lm)
        dist_wrist_to_ip = calculate_landmark_distance_2d(wrist_lm, thumb_ip_lm)

        return dist_wrist_to_tip > dist_wrist_to_ip
        
    except Exception as e:
        return False


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


def is_hand_fully_open(landmarks):
    """
    通过检查四根主手指是否都处于伸展状态来判断手是否完全张开。
    为了与 is_fist 函数的逻辑对称并提高稳健性，此版本忽略大拇指的状态。
    伸展的定义是：指尖到手腕的距离 > 指关节(PIP)到手腕的距离。
    """
    try:
        wrist_lm = landmarks[mp.solutions.hands.HandLandmark.WRIST]
        
        # 遍历检查四根主手指（食指到小指）
        for tip_idx, pip_idx in [(8, 6), (12, 10), (16, 14), (20, 18)]:
            tip_lm = landmarks[tip_idx]
            pip_lm = landmarks[pip_idx]
            
            dist_wrist_to_tip = calculate_distance_3d(wrist_lm, tip_lm)
            dist_wrist_to_pip = calculate_distance_3d(wrist_lm, pip_lm)
            
            # 如果有任何一根主手指是弯曲的，则判定“非张开”
            if dist_wrist_to_tip < dist_wrist_to_pip:
                return False

        # --- 以下是对大拇指的检查，我们将其注释掉或删除 ---
        # thumb_tip_lm = landmarks[mp.solutions.hands.HandLandmark.THUMB_TIP]
        # thumb_mcp_lm = landmarks[mp.solutions.hands.HandLandmark.THUMB_MCP]
        # dist_wrist_to_thumb_tip = calculate_distance_3d(wrist_lm, thumb_tip_lm)
        # dist_wrist_to_thumb_mcp = calculate_distance_3d(wrist_lm, thumb_mcp_lm)
        # if dist_wrist_to_thumb_tip < dist_wrist_to_thumb_mcp:
        #     return False

    except Exception as e:
        return False

    # 只要四根主手指满足伸展条件，我们就认为手已完全张开
    return True

def is_hand_closed_to_fist(landmarks):
    """
    Checks if the hand is in a fist-like (closed) position by checking if finger tips
    are close to the middle finger's MCP joint (a proxy for palm center).
    """
    # Define finger tip landmarks
    finger_tips = [
        landmarks[mp.solutions.hands.HandLandmark.THUMB_TIP],
        landmarks[mp.solutions.hands.HandLandmark.INDEX_FINGER_TIP],
        landmarks[mp.solutions.hands.HandLandmark.MIDDLE_FINGER_TIP],
        landmarks[mp.solutions.hands.HandLandmark.RING_FINGER_TIP],
        landmarks[mp.solutions.hands.HandLandmark.PINKY_TIP]
    ]

    # Define the "palm center" as the middle finger's MCP joint
    palm_center_lm = landmarks[mp.solutions.hands.HandLandmark.MIDDLE_FINGER_MCP]

    # Check if all finger tips are "close" to the palm center
    for tip in finger_tips:
        dist_to_palm_center = calculate_distance_3d(tip, palm_center_lm)
        # Use FIST_CLOSED_THRESHOLD from config
        if dist_to_palm_center > config.FIST_CLOSED_THRESHOLD:
            return False

    return True

# def is_hand_closed_to_fist(landmarks):
#     """
#     通过检查四根主手指（食指到小指）是否都处于卷曲状态来判断是否为握拳。
#     这个版本更宽容，因为它忽略了位置多变的大拇指。
#     卷曲的定义是：指尖到手腕的距离 < 指关节(PIP)到手腕的距离。
#     """
#     try:
#         wrist_lm = landmarks[mp.solutions.hands.HandLandmark.WRIST]
#         
#         # 遍历四根主手指
#         for tip_idx, pip_idx in [
#             (mp.solutions.hands.HandLandmark.INDEX_FINGER_TIP, mp.solutions.hands.HandLandmark.INDEX_FINGER_PIP),
#             (mp.solutions.hands.HandLandmark.MIDDLE_FINGER_TIP, mp.solutions.hands.HandLandmark.MIDDLE_FINGER_PIP),
#             (mp.solutions.hands.HandLandmark.RING_FINGER_TIP, mp.solutions.hands.HandLandmark.RING_FINGER_PIP),
#             (mp.solutions.hands.HandLandmark.PINKY_TIP, mp.solutions.hands.HandLandmark.PINKY_PIP)
#         ]:
#             tip_lm = landmarks[tip_idx]
#             pip_lm = landmarks[pip_idx]
#             
#             dist_wrist_to_tip = calculate_distance_3d(wrist_lm, tip_lm)
#             dist_wrist_to_pip = calculate_distance_3d(wrist_lm, pip_lm)
#             
#             # 核心判断：如果任何一根手指的指尖比其指关节更远离手腕，则说明该手指是伸展的
#             if dist_wrist_to_tip > dist_wrist_to_pip:
#                 # 如果需要调试，可以取消下面这行代码的注释，它会告诉你哪根手指没握紧
#                 # print(f"DEBUG: Fist check failed on finger {tip_idx.name}")
#                 return False
# 
#     except Exception as e:
#         # print(f"Error in is_hand_closed_to_fist: {e}")
#         return False
# 
#     # 如果循环顺利完成，说明四根主手指均已卷曲，我们判定为握拳成功！
#     return True

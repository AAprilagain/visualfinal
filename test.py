import cv2
import mediapipe as mp
import pyautogui
import numpy as np
from math import dist, hypot  # dist 在 Python 3.8+ 中可用，hypot 用于计算多维距离
from collections import deque
import time
import platform  # 用于获取操作系统信息以执行特定命令

# 初始化 MediaPipe Hands 模型
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,  # 检测手的最大数量
    min_detection_confidence=0.7,  # 手部检测模型的最小置信度值
    min_tracking_confidence=0.5)  # 手部跟踪模型的最小置信度值
mp_draw = mp.solutions.drawing_utils  # MediaPipe 绘图工具

# 获取屏幕尺寸
screen_w, screen_h = pyautogui.size()

# 手势参数配置
PINCH_THRESHOLD_CLOSE = 0.05  # 用于捏合检测的归一化闭合距离阈值
# PINCH_THRESHOLD_OPEN = 0.07 # (如果需要，可以为释放设置不同阈值)
DOUBLE_CLICK_INTERVAL = 0.4  # 判断为双击的两次单击之间的最大时间间隔（秒）
SCROLL_SENSITIVITY = 100  # 每单位手部垂直移动滚动的像素量
SWIPE_THRESHOLD_SPEED = 0.2  # 滑动手势的速度阈值 (归一化单位/秒) <--- 这个阈值现在将用于X和Y方向
# New Scroll Control Parameters
SCROLL_MOVEMENT_THRESHOLD_Y = 0.010  # Min vertical wrist movement (normalized) to trigger scroll
SCROLL_SENSITIVITY_FACTOR = 150     # Adjusts how much scroll happens per unit of hand movement. Tune this.

# 新增：拖拽确认参数
DRAG_CONFIRM_DURATION = 0.20  # 捏合持续超过这个时间（秒），并且有移动，才判断为拖拽
DRAG_CONFIRM_MOVEMENT = 25  # 捏合状态下，在屏幕上移动超过这个像素数，才判断为拖拽

# 状态追踪器
prev_landmarks = None  # 上一帧的手部关键点

# 修改后的捏合/点击/拖拽状态变量
was_pinching_last_frame = False  # 上一帧是否物理捏合
is_dragging = False  # 当前是否处于拖拽操作状态
pinch_start_time = 0.0  # 当前捏合动作的开始时间
last_click_action_time = 0.0  # 上一次单击或双击动作*完成*的时间
pending_single_click = False  # 是否有一个“待定”的单击事件
pinch_start_screen_pos = (0, 0)  # 捏合开始时的屏幕坐标 (用于计算拖拽移动量)


# --- 辅助函数 (与之前版本相同) ---
def calculate_distance(lm1, lm2):
    """计算两个3D地标点之间的欧几里得距离。"""
    return hypot(lm1.x - lm2.x, lm1.y - lm2.y, lm1.z - lm2.z)


def get_finger_extended_states(landmarks):
    """
    检查手指是否伸展。返回一个布尔值列表: [食指, 中指, 无名指, 小指]
    True 表示伸展, False 表示弯曲。
    """
    states = []
    for tip_idx, dip_idx, pip_idx in [(8, 6, 5), (12, 10, 9), (16, 14, 13), (20, 18, 17)]:
        states.append(landmarks[tip_idx].y < landmarks[dip_idx].y and \
                      landmarks[dip_idx].y < landmarks[pip_idx].y)
    return states


def is_thumb_extended(landmarks):
    """检查拇指是否伸展（指尖高于掌指关节）。"""
    return landmarks[4].y < landmarks[3].y and landmarks[3].y < landmarks[2].y


def map_to_screen(x, y):
    """将归一化的坐标映射到屏幕实际坐标。"""
    screen_x = np.interp(x, [0.2, 0.8], [0, screen_w])
    screen_y = np.interp(y, [0.2, 0.8], [0, screen_h])
    return int(screen_x), int(screen_y)


# --- 主循环 ---
cap = cv2.VideoCapture(0)
pyautogui.FAILSAFE = False

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        print("忽略空的摄像头帧。")
        continue

    frame = cv2.flip(frame, 1)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(rgb_frame)

    current_gesture = "No Gesture"
    action_performed_this_frame = False

    if results.multi_hand_landmarks:
        hand_landmarks = results.multi_hand_landmarks[0]
        landmarks = hand_landmarks.landmark
        mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

        finger_ext_states = get_finger_extended_states(landmarks)
        thumb_ext_state = is_thumb_extended(landmarks)

        thumb_tip = landmarks[4]  # 为了鼠标移动和截图等其他手势逻辑，提前获取
        index_tip = landmarks[8]

        # --- 1. 捏合物理状态检测 ---
        pinch_dist = calculate_distance(thumb_tip, index_tip)
        current_pinch_is_physically_active = pinch_dist < PINCH_THRESHOLD_CLOSE

        pinch_just_started = current_pinch_is_physically_active and not was_pinching_last_frame
        pinch_just_released = not current_pinch_is_physically_active and was_pinching_last_frame

        # --- 2. 捏合相关的动作处理 (单击、双击、拖拽) ---
        pinch_related_action_taken = False
        if pinch_just_started:
            pinch_start_time = time.time()
            pinch_mid_x_normalized = (thumb_tip.x + index_tip.x) / 2
            pinch_mid_y_normalized = (thumb_tip.y + index_tip.y) / 2
            pinch_start_screen_pos = map_to_screen(pinch_mid_x_normalized, pinch_mid_y_normalized)
            current_time = time.time()
            if current_time - last_click_action_time < DOUBLE_CLICK_INTERVAL and last_click_action_time != 0:
                pyautogui.doubleClick()
                current_gesture = "Double Click"
                last_click_action_time = 0
                pending_single_click = False
            else:
                pending_single_click = True
            pinch_related_action_taken = True
        elif current_pinch_is_physically_active:
            if not is_dragging:
                pinch_duration = time.time() - pinch_start_time
                pinch_current_mid_x_normalized = (thumb_tip.x + index_tip.x) / 2
                pinch_current_mid_y_normalized = (thumb_tip.y + index_tip.y) / 2
                current_pinch_screen_pos = map_to_screen(pinch_current_mid_x_normalized, pinch_current_mid_y_normalized)
                movement_since_pinch_start = dist(pinch_start_screen_pos, current_pinch_screen_pos)
                if pinch_duration > DRAG_CONFIRM_DURATION and movement_since_pinch_start > DRAG_CONFIRM_MOVEMENT:
                    is_dragging = True
                    pyautogui.mouseDown(button='left')
                    current_gesture = "Drag Start"
                    pending_single_click = False
                    pinch_related_action_taken = True
            if is_dragging:
                pinch_current_mid_x_normalized = (thumb_tip.x + index_tip.x) / 2
                pinch_current_mid_y_normalized = (thumb_tip.y + index_tip.y) / 2
                target_x, target_y = map_to_screen(pinch_current_mid_x_normalized, pinch_current_mid_y_normalized)
                pyautogui.moveTo(target_x, target_y, duration=0.05)
                current_gesture = "Dragging"
                pinch_related_action_taken = True
        elif pinch_just_released:
            if is_dragging:
                pyautogui.mouseUp(button='left')
                is_dragging = False
                current_gesture = "Drag Drop"
            elif pending_single_click:
                pyautogui.click()
                current_gesture = "Left Click"
                last_click_action_time = time.time()
            pending_single_click = False
            pinch_related_action_taken = True
        if pinch_related_action_taken:
            action_performed_this_frame = True

        # --- 3. 其他手势 (仅当捏合相关动作未执行时才考虑) ---
        if not action_performed_this_frame:

            is_scroll_base_gesture = (
                    thumb_ext_state and
                    not finger_ext_states[0] and not finger_ext_states[1] and
                    not finger_ext_states[2] and not finger_ext_states[3]
            )
            # --- 鼠标移动 (食指伸出指向) ---
            if finger_ext_states[0] and not any(finger_ext_states[1:]) and \
                    not is_dragging and not current_pinch_is_physically_active:
                target_x, target_y = map_to_screen(index_tip.x, index_tip.y)
                pyautogui.moveTo(target_x, target_y, duration=0.1)
                current_gesture = "Mouse Moving"
                action_performed_this_frame = True

            elif is_scroll_base_gesture:
                current_gesture_before_scroll = "Scroll Mode (Thumbs Up)"
                scrolled_this_frame = False

                if prev_landmarks:
                    curr_wrist_y = landmarks[0].y  # Using wrist landmark (0) for scroll detection
                    prev_wrist_y = prev_landmarks[0].y

                    dy_wrist = curr_wrist_y - prev_wrist_y  # Positive dy_wrist = hand moved down

                    if abs(dy_wrist) > SCROLL_MOVEMENT_THRESHOLD_Y:
                        # Calculate scroll amount.
                        # Negative dy_wrist (hand moves up) should result in positive scroll (scroll up/content moves down).
                        # Positive dy_wrist (hand moves down) should result in negative scroll (scroll down/content moves up).
                        scroll_amount_calculated = int(-1 * dy_wrist * SCROLL_SENSITIVITY_FACTOR)

                        if scroll_amount_calculated != 0:
                            pyautogui.scroll(scroll_amount_calculated)
                            if scroll_amount_calculated > 0:
                                current_gesture = "Scroll Up"
                            else:
                                current_gesture = "Scroll Down"
                            scrolled_this_frame = True
                            action_performed_this_frame = True
                if not scrolled_this_frame:
                    current_gesture = current_gesture_before_scroll


            # --- 四向滑动手势 (基于手腕的移动) ---
            # (注意：这个 elif 确保了它在其他更具体的手势之后被检查)
            elif prev_landmarks:  # 确保 prev_landmarks 存在才进行滑动检测
                palm_center_x_prev = prev_landmarks[0].x  # 使用手腕点 landmark[0] 作为手掌中心
                palm_center_y_prev = prev_landmarks[0].y
                palm_center_x_curr = landmarks[0].x
                palm_center_y_curr = landmarks[0].y

                dx = palm_center_x_curr - palm_center_x_prev
                dy = palm_center_y_curr - palm_center_y_prev  # 注意：图像坐标系中，Y轴向下为正

                # 帧间隔时间 (假设约30FPS，与之前代码一致)
                frame_interval = (1 / 30 if (1 / 30) > 0 else 0.033)

                speed_x = abs(dx) / frame_interval
                speed_y = abs(dy) / frame_interval

                # 首先检查是否有任一方向的速度超过阈值
                if speed_x > SWIPE_THRESHOLD_SPEED or speed_y > SWIPE_THRESHOLD_SPEED:
                    # 然后判断主导方向
                    if speed_x > speed_y:  # 水平滑动为主
                        if dx > 0:
                            pyautogui.hotkey('right')
                            current_gesture = "Swipe Right"
                        else:
                            pyautogui.hotkey('left')
                            current_gesture = "Swipe Left"
                        action_performed_this_frame = True
                        time.sleep(0.5)  # 滑动后延时
                    elif speed_y > speed_x:  # 垂直滑动为主
                        if dy > 0:  # Y值增大，表示手向下移动
                            pyautogui.hotkey('down')
                            current_gesture = "Swipe Down"
                        else:  # Y值减小，表示手向上移动
                            pyautogui.hotkey('up')
                            current_gesture = "Swipe Up"
                        action_performed_this_frame = True
                        time.sleep(0.5)  # 滑动后延时
                    # 如果 speed_x == speed_y (且都大于阈值), 则根据上面的逻辑不会触发任何操作。
                    # 这可以避免在纯对角线滑动时产生歧义。如果需要，可以修改比较条件来处理这种情况。

        prev_landmarks = landmarks
        was_pinching_last_frame = current_pinch_is_physically_active
    else:
        prev_landmarks = None
        was_pinching_last_frame = False
        if is_dragging:
            pyautogui.mouseUp(button='left')
            is_dragging = False
        pending_single_click = False

    cv2.putText(frame, current_gesture, (20, 50),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)
    cv2.imshow('Gesture Control HCI', frame)
    if cv2.waitKey(5) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
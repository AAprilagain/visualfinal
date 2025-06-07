import time
import config
import utils
from collections import deque

class GestureRecognizer:
    def __init__(self):
        # --- State Definitions ---
        self.STATE_IDLE = "IDLE"
        self.STATE_PINCH_DETECTED = "PINCH_DETECTED"
        self.STATE_POSSIBLE_DOUBLE_CLICK = "POSSIBLE_DOUBLE_CLICK"
        self.STATE_DRAGGING = "DRAGGING"
        # NEW: Renamed states for clarity and purpose
        self.STATE_FIST_STEADY = "FIST_STEADY" # Waiting in a fist posture
        self.STATE_OPEN_HAND_STEADY = "OPEN_HAND_STEADY" # Waiting in an open hand posture
        self.STATE_MOUSE_MOVING = "MOUSE_MOVING"
        self.STATE_SCROLL_MODE = "SCROLL_MODE"
        self.STATE_THUMBS_UP_SCROLL = "THUMBS_UP_SCROLL"
        
        self.current_state = self.STATE_IDLE

        # --- Timers & Counters ---
        self.state_start_time = 0.0
        self.last_click_time = 0.0
        self.scroll_posture_start_time = 0.0
        self.last_reset_time = 0.0

        # --- Positions & Data ---
        self.smoothed_mouse_pos_normalized = (0, 0)
        self.is_new_movement_gesture = True
        self.prev_landmarks = None
        self.prev_scroll_y = None
        self.wrist_velocity_tracker = deque(maxlen=5) # For swipe detection

    def _reset_all_states(self):
        # Reset all state variables to their initial values
        self.current_state = self.STATE_IDLE
        self.state_start_time = 0.0
        self.last_click_time = 0.0
        self.scroll_posture_start_time = 0.0
        self.is_new_movement_gesture = True
        self.prev_scroll_y = None
        self.wrist_velocity_tracker.clear()
        self.last_reset_time = time.time()
        
    def _enter_state(self, state):
        # Helper function to transition to a new state and reset the timer
        self.current_state = state
        self.state_start_time = time.time()

    def _apply_smoothing(self, raw_pos):
        # Applies exponential moving average to smooth mouse movements
        if self.is_new_movement_gesture:
            self.smoothed_mouse_pos_normalized = raw_pos
            self.is_new_movement_gesture = False
        else:
            prev_smooth_x, prev_smooth_y = self.smoothed_mouse_pos_normalized
            smooth_x = prev_smooth_x + config.MOUSE_SMOOTHING_FACTOR * (raw_pos[0] - prev_smooth_x)
            smooth_y = prev_smooth_y + config.MOUSE_SMOOTHING_FACTOR * (raw_pos[1] - prev_smooth_y)
            self.smoothed_mouse_pos_normalized = (smooth_x, smooth_y)
        return self.smoothed_mouse_pos_normalized

    def recognize(self, hand_landmark_obj):

        current_time = time.time()
        recognized_gesture = config.GESTURE_NONE
        gesture_data = {}

        # If hand is lost, handle drag drop and reset state
        if not hand_landmark_obj:
            if self.current_state == self.STATE_DRAGGING:
                recognized_gesture, gesture_data['performed_action'] = config.GESTURE_DRAG_DROP, True
            self._reset_all_states()
            return recognized_gesture, gesture_data

        # --- Landmark & Posture Calculation ---
        actual_landmarks = hand_landmark_obj.landmark
        thumb_tip = actual_landmarks[config.mp_hands.HandLandmark.THUMB_TIP]
        index_tip = actual_landmarks[config.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        middle_tip = actual_landmarks[config.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
        wrist = actual_landmarks[config.mp_hands.HandLandmark.WRIST]
        index_mcp = actual_landmarks[config.mp_hands.HandLandmark.INDEX_FINGER_MCP]

        # 1. 计算一个稳定的“手掌视觉大小”作为参考基准
        # 我们使用手腕到中指根部指关节的2D距离作为参考
        wrist_lm = actual_landmarks[config.mp_hands.HandLandmark.WRIST]
        mcp_lm = actual_landmarks[config.mp_hands.HandLandmark.MIDDLE_FINGER_MCP]
        hand_scale = utils.calculate_landmark_distance_2d(wrist_lm, mcp_lm)

        # 2. 根据参考基准和config中的比例，动态计算当前的阈值
        dynamic_pinch_close_threshold = hand_scale * config.PINCH_CLOSE_RATIO
        dynamic_pinch_open_threshold = hand_scale * config.PINCH_OPEN_RATIO
        
        # --- 使用新的动态阈值和2D距离进行判断 ---
        
        # 计算拇指和食指指尖的2D距离
        pinch_distance_2d = utils.calculate_landmark_distance_2d(thumb_tip, index_tip)

        # Use robust, orientation-independent posture detection from utils
        is_fist = utils.is_hand_closed_to_fist(actual_landmarks)
        is_open_hand = utils.is_hand_fully_open(actual_landmarks)
        
        # Keep original finger extension checks for other gestures
        finger_ext_states = utils.get_finger_extended_states(actual_landmarks)
        is_thumb_extended = utils.is_thumb_extended(actual_landmarks)
        is_mouse_move_posture = finger_ext_states[0] and not any(finger_ext_states[1:])
        is_middle_finger_scroll_posture = finger_ext_states[1] and not any([finger_ext_states[0], finger_ext_states[2], finger_ext_states[3]])

        finger_ext_states = utils.get_finger_extended_states(actual_landmarks)
        is_thumb_extended = utils.is_thumb_extended(actual_landmarks)
        all_four_fingers_curled = not any(finger_ext_states)

        # Pinch detection remains the same
        current_pinch_is_physically_closed = pinch_distance_2d < dynamic_pinch_close_threshold
        current_pinch_is_physically_open = pinch_distance_2d > dynamic_pinch_open_threshold
        
        is_basic_thumbs_up = is_thumb_extended and all_four_fingers_curled
        is_thumbs_up_posture = False # 默认为False

        if is_basic_thumbs_up:
            # 额外几何判断：大拇指指尖必须高于食指的指关节，才是真正的“赞”
            # 在图像坐标系中，y值越小代表位置越高
            if thumb_tip.y < index_mcp.y:
                is_thumbs_up_posture = True
                
        # if hand_landmark_obj: print(f"is_fist: {utils.is_hand_closed_to_fist(actual_landmarks)}, is_open: {utils.is_hand_fully_open(actual_landmarks)}")
        
        # --- Primary State Machine Logic ---
        if self.current_state == self.STATE_IDLE:
            # if current_pinch_is_physically_closed: print("current_pinch_is_physically_closed")
            # Priority: Check for stable, broad gestures first to avoid misinterpretation.
            if is_thumbs_up_posture:
                if self.scroll_posture_start_time == 0.0:
                    self.scroll_posture_start_time = current_time
                elif (current_time - self.scroll_posture_start_time) > config.SCROLL_ENGAGE_HOLD_TIME:
                    self._enter_state(self.STATE_SCROLL_MODE if is_middle_finger_scroll_posture else self.STATE_THUMBS_UP_SCROLL)
                    self.prev_scroll_y = middle_tip.y if is_middle_finger_scroll_posture else wrist.y
            elif is_fist and current_pinch_is_physically_open:
                self._enter_state(self.STATE_FIST_STEADY)
            elif is_open_hand and current_pinch_is_physically_open:
                self._enter_state(self.STATE_OPEN_HAND_STEADY)
            elif (current_time - self.last_reset_time) > config.GESTURE_DEBOUNCE_DELAY:
                if current_pinch_is_physically_closed:
                    self._enter_state(self.STATE_PINCH_DETECTED)
                elif is_mouse_move_posture:
                    self._enter_state(self.STATE_MOUSE_MOVING)
                    self.is_new_movement_gesture = True
                else:
                    self.scroll_posture_start_time = 0.0
            # 握拳时大拇指放在拳头外侧，拇指高度应不高于近端食指关节！！！！

        # --- Fist/Open Gesture Logic ---
        elif self.current_state == self.STATE_FIST_STEADY:
            # 当前是稳定的“握拳”状态，等待向“张手”转换
            # 优先检查是否成功转换到了“张手”
            if is_open_hand:
                # 如果成功转换，再检查“握拳”姿态的持续时间是否足够长
                time_held_open = current_time - self.state_start_time

                if time_held_open > config.GESTURE_TRANSITION_TIME:
                    recognized_gesture, gesture_data['performed_action'] = config.GESTURE_FIST_TO_OPEN, True
                else:
                    print(f"DEBUG: 时间检查失败。保持时间需要超过 {config.GESTURE_TRANSITION_TIME} 秒。")
                
                # 无论持续时间是否足够，状态已经改变，必须重置
                self._reset_all_states()

            # 如果手没有变成“张手”，但也不再是“握拳”状态，说明手势乱了，安全重置
            elif not is_fist:
                self._reset_all_states()
                
        elif self.current_state == self.STATE_OPEN_HAND_STEADY:
            # 当前是稳定的“张手”状态。计时器(self.state_start_time)已启动。
            # 目标：检测是否转换到了“握拳”状态。
            # --- 检查1: 手势是否成功变成了“握拳”？
            if is_fist:
                # print("DEBUG: 检测到'握拳'。准备检查计时器...")
                
                # 计算“张手”姿态已经保持了多久
                time_held_open = current_time - self.state_start_time
                # print(f"DEBUG: '张手'状态已保持 {time_held_open:.2f} 秒。")

                # 只有当“张手”保持时间 > 设定的阈值时，才认为是有效手势
                if time_held_open > config.GESTURE_TRANSITION_TIME:
                    # print("DEBUG: 时间检查通过！识别为 GESTURE_OPEN_TO_FIST。")
                    recognized_gesture, gesture_data['performed_action'] = config.GESTURE_OPEN_TO_FIST, True
                else:
                    print(f"DEBUG: 时间检查失败。保持时间需要超过 {config.GESTURE_TRANSITION_TIME} 秒。")

                # 重要：因为手势已经从“张开”变为“握拳”，当前状态必须结束，所以重置。
                self._reset_all_states()

            # --- 检查2: 如果没变成“握拳”，那是否变成了“非张开”的混乱状态？
            elif not is_open_hand:
                # print("DEBUG: 手不再是'张开'，但也不是'握拳'。判定为混乱状态，重置。")
                # 安全重置，防止因中间状态导致程序卡住
                self._reset_all_states()

            # --- 检查3: 如果以上都不是，说明手势仍保持在“张开”状态
            else:
                # Swipe detection logic (can only happen from a steady open hand)
                if (current_time - self.state_start_time) > config.SWIPE_COOLDOWN:
                    if self.prev_landmarks:
                        dx, dy = utils.calculate_movement_2d_normalized(self.prev_landmarks.landmark[config.mp_hands.HandLandmark.WRIST], wrist)
                        self.wrist_velocity_tracker.append((dx, dy))

                        if len(self.wrist_velocity_tracker) == self.wrist_velocity_tracker.maxlen:
                            avg_dx = sum(v[0] for v in self.wrist_velocity_tracker)
                            avg_dy = sum(v[1] for v in self.wrist_velocity_tracker)

                            if abs(avg_dx) > config.SWIPE_VELOCITY_THRESHOLD or abs(avg_dy) > config.SWIPE_VELOCITY_THRESHOLD:
                                if abs(avg_dx) > abs(avg_dy): # 水平挥手
                                    recognized_gesture = config.GESTURE_SWIPE_RIGHT if avg_dx > 0 else config.GESTURE_SWIPE_LEFT
                                else: # 垂直挥手
                                    recognized_gesture = config.GESTURE_SWIPE_DOWN if dy > 0 else config.GESTURE_SWIPE_UP
                                self._reset_all_states()

        elif self.current_state == self.STATE_MOUSE_MOVING:
            if not is_mouse_move_posture:
                self._reset_all_states()
            else:
                target_x, target_y = utils.map_to_screen(*self._apply_smoothing((index_tip.x, index_tip.y)))
                recognized_gesture, gesture_data = config.GESTURE_MOUSE_MOVING, {'x': target_x, 'y': target_y, 'performed_action': True}
                self.prev_landmarks = hand_landmark_obj
                return recognized_gesture, gesture_data

        elif self.current_state == self.STATE_PINCH_DETECTED:
            # print(current_pinch_is_physically_open)
            if (current_time - self.state_start_time) > config.DRAG_CONFIRM_DURATION:
                self._enter_state(self.STATE_DRAGGING)
                self.is_new_movement_gesture = True
                recognized_gesture, gesture_data['performed_action'] = config.GESTURE_DRAG_START, True
            elif current_pinch_is_physically_open:
                self._enter_state(self.STATE_POSSIBLE_DOUBLE_CLICK)
                self.last_click_time = current_time
        
        elif self.current_state == self.STATE_POSSIBLE_DOUBLE_CLICK:
            if current_pinch_is_physically_closed:
                recognized_gesture, gesture_data['performed_action'] = config.GESTURE_DOUBLE_CLICK, True
                self.last_click_time = 0
                self._reset_all_states()
            elif (current_time - self.last_click_time) > config.DOUBLE_CLICK_INTERVAL:
                recognized_gesture, gesture_data['performed_action'] = config.GESTURE_LEFT_CLICK, True
                self._reset_all_states()

        elif self.current_state == self.STATE_DRAGGING:
            if current_pinch_is_physically_open:
                recognized_gesture, gesture_data['performed_action'] = config.GESTURE_DRAG_DROP, True
                self._reset_all_states()
            else:
                target_x, target_y = utils.map_to_screen(*self._apply_smoothing(utils.get_pinch_midpoint_normalized(thumb_tip, index_tip)))
                recognized_gesture, gesture_data = config.GESTURE_DRAGGING, {'x': target_x, 'y': target_y, 'performed_action': True}

        elif self.current_state == self.STATE_SCROLL_MODE:
            if not is_middle_finger_scroll_posture: self._reset_all_states()
            else:
                if self.prev_scroll_y is not None:
                    dy = middle_tip.y - self.prev_scroll_y
                    if abs(dy) > config.SCROLL_MOVEMENT_THRESHOLD_Y:
                        scroll_amount = int(-1 * dy * config.SCROLL_SENSITIVITY_FACTOR)
                        recognized_gesture, gesture_data = (config.GESTURE_SCROLL_UP if scroll_amount > 0 else config.GESTURE_SCROLL_DOWN), {'amount': scroll_amount, 'performed_action': True}
                self.prev_scroll_y = middle_tip.y
        
        elif self.current_state == self.STATE_THUMBS_UP_SCROLL:
            if not is_thumbs_up_posture: self._reset_all_states()
            else:
                if self.prev_scroll_y is not None:
                    dy = wrist.y - self.prev_scroll_y
                    if abs(dy) > config.SCROLL_MOVEMENT_THRESHOLD_Y:
                        scroll_amount = int(-1 * dy * config.SCROLL_SENSITIVITY_FACTOR)
                        recognized_gesture, gesture_data = (config.GESTURE_SCROLL_UP if scroll_amount > 0 else config.GESTURE_SCROLL_DOWN), {'amount': scroll_amount, 'performed_action': True}
                self.prev_scroll_y = wrist.y

        if recognized_gesture not in [config.GESTURE_NONE, config.GESTURE_MOUSE_MOVING]:
            print(f"State: {self.current_state}, Recognized Gesture: {recognized_gesture}, Actionable: {gesture_data.get('performed_action', False)}")

        self.prev_landmarks = hand_landmark_obj # Update previous landmarks at the end of every frame
        return recognized_gesture, gesture_data
# gesture_recognizer.py

import time
import config
import utils


class GestureRecognizer:
    def __init__(self):
        self.current_state = config.STATE_IDLE  # 当前手势状态

        self.pinch_start_time = 0.0  # 捏合开始时间戳
        self.last_click_time = 0.0  # 上次点击时间戳（用于双击检测）
        self.pinch_start_screen_pos = (0, 0)  # 捏合起始屏幕坐标
        self.scroll_pending_start_time = 0.0  # 滚动模式待定状态起始时间（用于 STATE_SCROLL_MODE_PENDING）
        self.last_mouse_pos_normalized = (0, 0)  # For mouse movement smoothing

        # Scroll related states
        self.scroll_mode_engaged_time = 0.0

        # Swipe related states
        self.swipe_start_time = 0.0
        self.swipe_start_wrist_pos = None  # Stores NormalizedLandmark object
        self.last_gesture_time = 0.0

        # Landmark history for speed/movement calculation
        self.prev_landmarks = None  # Stores the entire NormalizedLandmarkList object

    def _reset_all_states(self):
        """重置所有内部状态到空闲(IDLE)状态，清除所有计时器/位置数据"""
        self.current_state = config.STATE_IDLE
        self.pinch_start_time = 0.0
        self.last_click_time = 0.0
        self.pinch_start_screen_pos = (0, 0)
        self.scroll_mode_engaged_time = 0.0  # 滚动模式激活时间
        self.swipe_start_time = 0.0  # 滑动手势开始时间
        self.swipe_start_wrist_pos = None  # 滑动手腕起始位置
        self.prev_landmarks = None  # 上一帧的手部关键点
        self.scroll_pending_start_time = 0.0  # 确保滚动待定状态时间重置

    def recognize(self, hand_landmark_obj):
        """核心手势识别方法
        Args:
            hand_landmark_obj: 包含当前帧手部关键点的对象

        Returns:
            recognized_gesture: 识别到的手势类型
            gesture_data: 手势相关数据（如坐标、滚动量等）
        """
        current_time = time.time()
        recognized_gesture = config.GESTURE_NONE  # 默认无手势
        gesture_data = {}  # 手势数据字典

        # 如果没有检测到手部，重置状态并处理可能的拖放结束
        if not hand_landmark_obj:
            if self.current_state == config.STATE_DRAGGING:
                recognized_gesture = config.GESTURE_DRAG_DROP
            self._reset_all_states()
            return recognized_gesture, gesture_data

        # 获取关键点坐标
        actual_landmarks = hand_landmark_obj.landmark
        thumb_tip = actual_landmarks[config.mp_hands.HandLandmark.THUMB_TIP]  # 拇指指尖
        index_tip = actual_landmarks[config.mp_hands.HandLandmark.INDEX_FINGER_TIP]  # 食指指尖
        wrist = actual_landmarks[config.mp_hands.HandLandmark.WRIST]  # 手腕

        # 计算捏合距离并判断状态
        pinch_dist = utils.calculate_distance_3d(thumb_tip, index_tip)
        current_pinch_is_physically_closed = pinch_dist < config.PINCH_THRESHOLD_CLOSE  # 捏合是否闭合
        current_pinch_is_physically_open = pinch_dist > config.PINCH_THRESHOLD_OPEN  # 捏合是否张开

        # 获取手指伸展状态
        finger_ext_states = utils.get_finger_extended_states(actual_landmarks)
        thumb_ext_state = utils.is_thumb_extended(actual_landmarks)  # 拇指是否伸展

        # ===== 状态机核心逻辑 =====

        # 状态1: 空闲状态 (IDLE)
        if self.current_state == config.STATE_IDLE:
            # 检测到捏合闭合 -> 进入捏合检测状态
            if current_pinch_is_physically_closed:
                self.current_state = config.STATE_PINCH_DETECTED
                self.pinch_start_time = current_time
                # 计算并存储捏合中心点的屏幕坐标
                pinch_mid_x_norm, pinch_mid_y_norm = utils.get_pinch_midpoint_normalized(thumb_tip, index_tip)
                self.pinch_start_screen_pos = utils.map_to_screen(pinch_mid_x_norm, pinch_mid_y_norm)
                recognized_gesture = config.GESTURE_NONE

            # 检测到"竖起拇指"手势 -> 进入滚动待定状态
            elif thumb_ext_state and not any(finger_ext_states):
                self.current_state = config.STATE_SCROLL_MODE_PENDING
                self.scroll_pending_start_time = current_time
                recognized_gesture = config.GESTURE_NONE

            # 检测到食指指向 -> 鼠标移动
            elif finger_ext_states[0] and not any(finger_ext_states[1:]):
                target_x, target_y = utils.map_to_screen(index_tip.x, index_tip.y)
                recognized_gesture = config.GESTURE_MOUSE_MOVING
                gesture_data = {'x': target_x, 'y': target_y}

            # 滑动手势逻辑
            elif self.prev_landmarks and (current_time - self.last_gesture_time > config.SWIPE_ACTION_DELAY):
                # Check for swipe gesture
                prev_wrist_lm = self.prev_landmarks.landmark[config.mp_hands.HandLandmark.WRIST]
                dx, dy = utils.calculate_movement_2d_normalized(prev_wrist_lm, wrist)
                frame_interval = 1 / config.ASSUMED_FPS
                speed_x = abs(dx) / frame_interval if frame_interval > 0 else 0
                speed_y = abs(dy) / frame_interval if frame_interval > 0 else 0

                total_dist = utils.calculate_distance_2d((prev_wrist_lm.x, prev_wrist_lm.y), (wrist.x, wrist.y))

                if (speed_x > config.SWIPE_THRESHOLD_SPEED or speed_y > config.SWIPE_THRESHOLD_SPEED) and \
                        total_dist > config.SWIPE_MIN_DISTANCE_NORM:
                    self.current_state = config.STATE_SWIPE_PENDING  # Consider this a pending swipe
                    self.swipe_start_time = current_time
                    self.swipe_start_wrist_pos = wrist  # Store current wrist position
                    # We'll determine direction and recognize the gesture in the next frame if swipe continues
                    recognized_gesture = config.GESTURE_NONE  # Not yet, prevent immediate action

        # 状态2: 滚动待定状态 (SCROLL_MODE_PENDING)
        elif self.current_state == config.STATE_SCROLL_MODE_PENDING:
            # 优先级: 捏合手势中断滚动检测
            if current_pinch_is_physically_closed:
                self.current_state = config.STATE_PINCH_DETECTED
                self.pinch_start_time = current_time
                pinch_mid_x_norm, pinch_mid_y_norm = utils.get_pinch_midpoint_normalized(thumb_tip, index_tip)
                self.pinch_start_screen_pos = utils.map_to_screen(pinch_mid_x_norm, pinch_mid_y_norm)
                recognized_gesture = config.GESTURE_NONE

            # "竖起拇指"手势中断 -> 返回空闲状态
            elif not (thumb_ext_state and not any(finger_ext_states)):
                self._reset_all_states()

            # 超过确认延迟时间 -> 进入滚动模式
            elif current_time - self.scroll_pending_start_time > config.SCROLL_MODE_CONFIRM_DELAY:
                self.current_state = config.STATE_SCROLL_MODE
                self.scroll_mode_engaged_time = current_time
                recognized_gesture = config.GESTURE_SCROLL_MODE_ENGAGED

            # 仍在等待确认中
            else:
                recognized_gesture = config.GESTURE_NONE

        # 状态3: 捏合检测状态 (PINCH_DETECTED)
        elif self.current_state == config.STATE_PINCH_DETECTED:
            pinch_duration = current_time - self.pinch_start_time  # 当前捏合持续时间

            # 捏合释放处理 (手指张开)
            if not current_pinch_is_physically_closed and current_pinch_is_physically_open:
                # 在点击评估期内释放 -> 点击/双击
                if pinch_duration < config.CLICK_EVALUATION_PERIOD:
                    # 检查双击时间间隔
                    if current_time - self.last_click_time < config.DOUBLE_CLICK_INTERVAL:
                        recognized_gesture = config.GESTURE_DOUBLE_CLICK
                        self.last_click_time = 0  # 重置双击计时
                    else:
                        recognized_gesture = config.GESTURE_LEFT_CLICK
                        self.last_click_time = current_time
                    # 重置状态（无论是否识别到点击）
                self._reset_all_states()

            # 持续捏合处理
            elif current_pinch_is_physically_closed:
                # 超过点击评估期 -> 可能进入拖拽
                if pinch_duration > config.CLICK_EVALUATION_PERIOD:
                    pinch_mid_x_norm, pinch_mid_y_norm = utils.get_pinch_midpoint_normalized(thumb_tip, index_tip)
                    current_pinch_screen_pos = utils.map_to_screen(pinch_mid_x_norm, pinch_mid_y_norm)
                    # 计算从起始位置的移动距离
                    movement_since_pinch_start = utils.calculate_distance_2d(
                        self.pinch_start_screen_pos, current_pinch_screen_pos
                    )

                    # 超过拖拽确认阈值 -> 进入拖拽状态
                    if movement_since_pinch_start > config.DRAG_CONFIRM_MOVEMENT_THRESHOLD:
                        self.current_state = config.STATE_DRAGGING
                        recognized_gesture = config.GESTURE_DRAG_START
                        gesture_data = {'x': current_pinch_screen_pos[0], 'y': current_pinch_screen_pos[1]}

        # 状态4: 拖拽状态 (DRAGGING)
        elif self.current_state == config.STATE_DRAGGING:
            # 持续捏合 -> 更新拖拽位置
            if current_pinch_is_physically_closed:
                pinch_current_mid_x_norm, pinch_current_mid_y_norm = utils.get_pinch_midpoint_normalized(thumb_tip,
                                                                                                         index_tip)
                current_pinch_screen_pos = utils.map_to_screen(pinch_current_mid_x_norm, pinch_current_mid_y_norm)
                recognized_gesture = config.GESTURE_DRAGGING
                gesture_data = {'x': current_pinch_screen_pos[0], 'y': current_pinch_screen_pos[1]}
            # 捏合释放 -> 拖拽结束
            else:
                recognized_gesture = config.GESTURE_DRAG_DROP
                self._reset_all_states()

        # 状态5: 滚动模式 (SCROLL_MODE)
        elif self.current_state == config.STATE_SCROLL_MODE:
            # 捏合手势中断滚动
            if current_pinch_is_physically_closed:
                self.current_state = config.STATE_PINCH_DETECTED
                self.pinch_start_time = current_time
                pinch_mid_x_norm, pinch_mid_y_norm = utils.get_pinch_midpoint_normalized(thumb_tip, index_tip)
                self.pinch_start_screen_pos = utils.map_to_screen(pinch_mid_x_norm, pinch_mid_y_norm)

            # "竖起拇指"手势中断 -> 退出滚动模式
            elif not (thumb_ext_state and not any(finger_ext_states)):
                self._reset_all_states()

            # 有上一帧数据 -> 计算滚动量
            elif self.prev_landmarks:
                curr_wrist_y = wrist.y
                prev_wrist_y = self.prev_landmarks.landmark[config.mp_hands.HandLandmark.WRIST].y
                dy_wrist = curr_wrist_y - prev_wrist_y  # 手腕Y轴变化量

                # 超过滚动阈值 -> 触发滚动
                if abs(dy_wrist) > config.SCROLL_MOVEMENT_THRESHOLD_Y:
                    scroll_amount = int(-1 * dy_wrist * config.SCROLL_SENSITIVITY_FACTOR)
                    if scroll_amount != 0:
                        # 根据方向判断上滚/下滚
                        recognized_gesture = config.GESTURE_SCROLL_UP if scroll_amount > 0 else config.GESTURE_SCROLL_DOWN
                        gesture_data = {'amount': scroll_amount}
                    else:
                        # 无实际滚动，保持滚动模式激活状态
                        recognized_gesture = config.GESTURE_SCROLL_MODE_ENGAGED
                else:
                    recognized_gesture = config.GESTURE_SCROLL_MODE_ENGAGED
            # 无上一帧数据（刚进入状态）
            else:
                recognized_gesture = config.GESTURE_SCROLL_MODE_ENGAGED

        # 状态6: 滑动待定状态 (SWIPE_PENDING - 保持原有逻辑)
        elif self.current_state == config.STATE_SWIPE_PENDING:
            if current_time - self.swipe_start_time > config.SWIPE_ACTION_DELAY:
                self._reset_all_states()
            elif self.swipe_start_wrist_pos:
                dx, dy = utils.calculate_movement_2d_normalized(self.swipe_start_wrist_pos, wrist)
                total_dist = utils.calculate_distance_2d(
                    (self.swipe_start_wrist_pos.x, self.swipe_start_wrist_pos.y),
                    (wrist.x, wrist.y)
                )

                if total_dist > config.SWIPE_MIN_DISTANCE_NORM:
                    if abs(dx) > abs(dy):
                        recognized_gesture = config.GESTURE_SWIPE_RIGHT if dx > 0 else config.GESTURE_SWIPE_LEFT
                    else:
                        recognized_gesture = config.GESTURE_SWIPE_DOWN if dy > 0 else config.GESTURE_SWIPE_UP
                    self.last_gesture_time = current_time
                    self._reset_all_states()

        # ===== 状态更新 =====
        # 保存当前帧数据供下一帧使用
        self.prev_landmarks = hand_landmark_obj

        # 标记已执行动作（滚动模式激活除外）
        if recognized_gesture != config.GESTURE_NONE and recognized_gesture != config.GESTURE_SCROLL_MODE_ENGAGED:
            gesture_data['performed_action'] = True
        print(
            f"Time: {current_time:.2f}, State: {self.current_state}, Recognized Gesture: {recognized_gesture}, Actionable: {gesture_data.get('performed_action', False)}")
        return recognized_gesture, gesture_data
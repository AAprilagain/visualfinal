import time
import config
import utils

class GestureRecognizer:
    def __init__(self):
        self.current_state = config.STATE_IDLE

        self.pinch_start_time = 0.0
        self.last_click_time = 0.0
        self.pinch_start_screen_pos = (0, 0)
        self.last_mouse_pos_normalized = (0, 0) # For mouse movement smoothing

        self.scroll_mode_engaged_time = 0.0
        self.prev_middle_finger_tip_y = None

        self.swipe_start_time = 0.0
        self.swipe_start_wrist_pos = None
        self.last_gesture_time = 0.0

        self.last_hand_open_detected_time = 0.0
        self.last_hand_closed_detected_time = 0.0

        self.prev_landmarks = None

        self.mouse_move_start_time = 0.0
        self.mouse_move_hold_threshold = 0.1


    def _reset_all_states(self):
        """Resets all internal states to IDLE and clears all timers/positions."""
        self.current_state = config.STATE_IDLE
        self.pinch_start_time = 0.0
        self.last_click_time = 0.0
        self.pinch_start_screen_pos = (0, 0)
        self.scroll_mode_engaged_time = 0.0
        self.prev_middle_finger_tip_y = None
        self.swipe_start_time = 0.0
        self.swipe_start_wrist_pos = None
        self.prev_landmarks = None # Keep this reset for clean state after no hand/action
        self.last_hand_open_detected_time = 0.0
        self.last_hand_closed_detected_time = 0.0
        self.mouse_move_start_time = 0.0


    def _reset_all_states_except_mouse_pos(self):
        """Resets most internal states, but preserves last_mouse_pos_normalized for smoother mouse control."""
        # Note: prev_landmarks will still be reset here, which is usually fine for mode changes
        self.pinch_start_time = 0.0
        self.last_click_time = 0.0
        self.pinch_start_screen_pos = (0, 0)
        self.scroll_mode_engaged_time = 0.0
        self.prev_middle_finger_tip_y = None
        self.swipe_start_time = 0.0
        self.swipe_start_wrist_pos = None
        self.prev_landmarks = None
        self.last_hand_open_detected_time = 0.0
        self.last_hand_closed_detected_time = 0.0
        self.mouse_move_start_time = 0.0

    def recognize(self, hand_landmark_obj):
        current_time = time.time()
        recognized_gesture = config.GESTURE_NONE
        gesture_data = {}

        if not hand_landmark_obj:
            if self.current_state == config.STATE_MOUSE_MOVING:
                recognized_gesture = config.GESTURE_MOUSE_MOVING
                gesture_data = {'x': utils.map_to_screen(self.last_mouse_pos_normalized[0], self.last_mouse_pos_normalized[1])[0],
                                'y': utils.map_to_screen(self.last_mouse_pos_normalized[0], self.last_mouse_pos_normalized[1])[1],
                                'performed_action': True}
                self._reset_all_states() # Reset to IDLE after sending one last mouse move and hand lost
            elif self.current_state == config.STATE_DRAGGING:
                recognized_gesture = config.GESTURE_DRAG_DROP
                gesture_data = {'performed_action': True}
                self._reset_all_states()
            else:
                self._reset_all_states()
            return recognized_gesture, gesture_data

        actual_landmarks = hand_landmark_obj.landmark
        thumb_tip = actual_landmarks[config.mp_hands.HandLandmark.THUMB_TIP]
        index_tip = actual_landmarks[config.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        middle_tip = actual_landmarks[config.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
        wrist = actual_landmarks[config.mp_hands.HandLandmark.WRIST]

        pinch_dist = utils.calculate_distance_3d(thumb_tip, index_tip)
        current_pinch_is_physically_closed = pinch_dist < config.PINCH_THRESHOLD_CLOSE
        current_pinch_is_physically_open = pinch_dist > config.PINCH_THRESHOLD_OPEN

        finger_ext_states = utils.get_finger_extended_states(actual_landmarks)
        is_thumb_extended = utils.is_thumb_extended(actual_landmarks)

        is_hand_fully_open_posture = all(finger_ext_states) and is_thumb_extended
        is_hand_closed_posture = utils.is_hand_closed_to_fist(actual_landmarks)

        is_middle_finger_extended = finger_ext_states[1]
        other_fingers_curled_for_scroll = (not finger_ext_states[0] and
                                           not finger_ext_states[2] and
                                           not finger_ext_states[3] and
                                           not is_thumb_extended)

        is_index_finger_extended = finger_ext_states[0]
        other_fingers_curled_for_mouse_move = (not finger_ext_states[1] and
                                               not finger_ext_states[2] and
                                               not finger_ext_states[3] and
                                               not is_thumb_extended)

        # --- Hand Open/Closed State Machine (Priority 1) ---
        # These transitions reset other states and return immediately as they are high-priority mode changes.
        if is_hand_fully_open_posture:
            if self.current_state == config.STATE_HAND_CLOSED_STEADY and \
               (current_time - self.last_hand_closed_detected_time < config.GESTURE_TRANSITION_TIME):
                recognized_gesture = config.GESTURE_FIST_TO_OPEN
                self._reset_all_states_except_mouse_pos()
                self.current_state = config.STATE_HAND_OPEN_STEADY
                self.last_hand_open_detected_time = current_time
                self.last_hand_closed_detected_time = 0.0
                gesture_data['performed_action'] = True
                print(f"Time: {current_time:.2f}, State: {self.current_state}, Recognized Gesture: {recognized_gesture}, Actionable: {gesture_data.get('performed_action', False)}")
                # Before returning, update prev_landmarks for subsequent frame
                self.prev_landmarks = hand_landmark_obj
                self.last_mouse_pos_normalized = (index_tip.x, index_tip.y)
                return recognized_gesture, gesture_data

            elif self.current_state != config.STATE_HAND_OPEN_STEADY:
                self.current_state = config.STATE_HAND_OPEN_STEADY
            self.last_hand_open_detected_time = current_time
            self.last_hand_closed_detected_time = 0.0

        elif is_hand_closed_posture:
            if self.current_state == config.STATE_HAND_OPEN_STEADY and \
               (current_time - self.last_hand_open_detected_time < config.GESTURE_TRANSITION_TIME):
                recognized_gesture = config.GESTURE_OPEN_TO_FIST
                self._reset_all_states_except_mouse_pos()
                self.current_state = config.STATE_HAND_CLOSED_STEADY
                self.last_hand_closed_detected_time = current_time
                self.last_hand_open_detected_time = 0.0
                gesture_data['performed_action'] = True
                print(f"Time: {current_time:.2f}, State: {self.current_state}, Recognized Gesture: {recognized_gesture}, Actionable: {gesture_data.get('performed_action', False)}")
                # Before returning, update prev_landmarks for subsequent frame
                self.prev_landmarks = hand_landmark_obj
                self.last_mouse_pos_normalized = (index_tip.x, index_tip.y)
                return recognized_gesture, gesture_data
            elif self.current_state != config.STATE_HAND_CLOSED_STEADY:
                self.current_state = config.STATE_HAND_CLOSED_STEADY
            self.last_hand_closed_detected_time = current_time
            self.last_hand_open_detected_time = 0.0
        else:
            if self.current_state == config.STATE_HAND_OPEN_STEADY or \
               self.current_state == config.STATE_HAND_CLOSED_STEADY:
                self.current_state = config.STATE_IDLE
            self.last_hand_open_detected_time = 0.0
            self.last_hand_closed_detected_time = 0.0

        # --- Swipe Gesture (New Position: Before Mouse Moving) ---
        # Swipe should be checked here, before continuous mouse moving,
        # especially if it can interrupt mouse moving.
        # Ensure prev_landmarks is available for calculation
        if self.prev_landmarks and (current_time - self.last_gesture_time > config.SWIPE_ACTION_DELAY) and is_hand_fully_open_posture:
            prev_wrist_lm = self.prev_landmarks.landmark[config.mp_hands.HandLandmark.WRIST]
            dx, dy = utils.calculate_movement_2d_normalized(prev_wrist_lm, wrist)
            frame_interval = 1 / config.ASSUMED_FPS
            speed_x = abs(dx) / frame_interval if frame_interval > 0 else 0
            speed_y = abs(dy) / frame_interval if frame_interval > 0 else 0

            total_dist = utils.calculate_distance_2d((prev_wrist_lm.x, prev_wrist_lm.y), (wrist.x, wrist.y))

            if (speed_x > config.SWIPE_THRESHOLD_SPEED or speed_y > config.SWIPE_THRESHOLD_SPEED) and \
               total_dist > config.SWIPE_MIN_DISTANCE_NORM:
                # Swipe detected! Reset all states to ensure clean transition
                # and prevent mouse moving from immediately taking over.
                recognized_gesture = config.GESTURE_NONE # Temporarily set to NONE while determining direction
                if abs(dx) > abs(dy): # Horizontal swipe
                    if dx > 0: recognized_gesture = config.GESTURE_SWIPE_RIGHT
                    else: recognized_gesture = config.GESTURE_SWIPE_LEFT
                else: # Vertical swipe
                    if dy > 0: recognized_gesture = config.GESTURE_SWIPE_DOWN
                    else: recognized_gesture = config.GESTURE_SWIPE_UP

                # If a swipe was truly recognized, process it and return.
                if recognized_gesture != config.GESTURE_NONE:
                    gesture_data['performed_action'] = True
                    self.last_gesture_time = current_time
                    self._reset_all_states() # Full reset after swipe
                    print(f"Time: {current_time:.2f}, State: {self.current_state}, Recognized Gesture: {recognized_gesture}, Actionable: {gesture_data.get('performed_action', False)}")
                    # Before returning, update prev_landmarks for subsequent frame
                    self.prev_landmarks = hand_landmark_obj
                    self.last_mouse_pos_normalized = (index_tip.x, index_tip.y)
                    return recognized_gesture, gesture_data
                # If conditions met for swipe but not a clear direction, let it pass to other logic
                else:
                    self.current_state = config.STATE_SWIPE_PENDING # Still pending if no clear direction yet
                    self.swipe_start_time = current_time
                    self.swipe_start_wrist_pos = wrist
                    recognized_gesture = config.GESTURE_NONE


        # --- Mouse Moving Gesture State Management ---
        # Prioritize mouse moving if the conditions are met OR if we are already in STATE_MOUSE_MOVING
        if is_index_finger_extended and other_fingers_curled_for_mouse_move:
            if self.current_state != config.STATE_MOUSE_MOVING:
                if self.mouse_move_start_time == 0.0:
                    self.mouse_move_start_time = current_time
                if current_time - self.mouse_move_start_time > self.mouse_move_hold_threshold:
                    self.current_state = config.STATE_MOUSE_MOVING
            if self.current_state == config.STATE_MOUSE_MOVING:
                target_x, target_y = utils.map_to_screen(index_tip.x, index_tip.y)
                recognized_gesture = config.GESTURE_MOUSE_MOVING
                gesture_data = {'x': target_x, 'y': target_y, 'performed_action': True}
                self.last_mouse_pos_normalized = (index_tip.x, index_tip.y)
                self.prev_landmarks = hand_landmark_obj
                print(f"Time: {current_time:.2f}, State: {self.current_state}, Recognized Gesture: {recognized_gesture}, Actionable: {gesture_data.get('performed_action', False)}")
                return recognized_gesture, gesture_data
        else:
            self.mouse_move_start_time = 0.0
            if self.current_state == config.STATE_MOUSE_MOVING:
                self.current_state = config.STATE_IDLE


        # --- Other Gesture State Machine (Normal Priority, only if not mouse moving or swipe) ---
        # This block will only be reached if STATE_MOUSE_MOVING is not active and not identified in this frame,
        # and no FIST_TO_OPEN/OPEN_TO_FIST/Swipe was recognized.
        if self.current_state == config.STATE_IDLE:
            if current_pinch_is_physically_closed:
                self.current_state = config.STATE_PINCH_DETECTED
                self.pinch_start_time = current_time
                self.last_click_time = current_time
                pinch_mid_x_norm, pinch_mid_y_norm = utils.get_pinch_midpoint_normalized(thumb_tip, index_tip)
                self.pinch_start_screen_pos = utils.map_to_screen(pinch_mid_x_norm, pinch_mid_y_norm)
                recognized_gesture = config.GESTURE_NONE
            elif is_middle_finger_extended and other_fingers_curled_for_scroll:
                self.current_state = config.STATE_SCROLL_MODE
                self.scroll_mode_engaged_time = current_time
                self.prev_middle_finger_tip_y = middle_tip.y
                recognized_gesture = config.GESTURE_SCROLL_MODE_ENGAGED
            # Note: Swipe logic moved above. SWIPE_PENDING state is handled within the new swipe block if it's not immediately a full swipe.

        elif self.current_state == config.STATE_PINCH_DETECTED:
            if not current_pinch_is_physically_closed and current_pinch_is_physically_open:
                if current_time - self.pinch_start_time < config.DRAG_CONFIRM_DURATION:
                    if current_time - self.last_click_time < config.DOUBLE_CLICK_INTERVAL:
                        recognized_gesture = config.GESTURE_DOUBLE_CLICK
                        self.last_click_time = 0
                    else:
                        recognized_gesture = config.GESTURE_LEFT_CLICK
                        self.last_click_time = current_time
                    gesture_data['performed_action'] = True
                self.current_state = config.STATE_IDLE
            elif current_pinch_is_physically_closed:
                pinch_duration = current_time - self.pinch_start_time
                pinch_mid_x_norm, pinch_mid_y_norm = utils.get_pinch_midpoint_normalized(thumb_tip, index_tip)
                current_pinch_screen_pos = utils.map_to_screen(pinch_mid_x_norm, pinch_mid_y_norm)
                movement_since_pinch_start = utils.calculate_distance_2d(self.pinch_start_screen_pos, current_pinch_screen_pos)

                if pinch_duration > config.DRAG_CONFIRM_DURATION and \
                   movement_since_pinch_start > config.DRAG_CONFIRM_MOVEMENT_THRESHOLD:
                    self.current_state = config.STATE_DRAGGING
                    recognized_gesture = config.GESTURE_DRAG_START
                    gesture_data = {'x': current_pinch_screen_pos[0], 'y': current_pinch_screen_pos[1], 'performed_action': True}

        elif self.current_state == config.STATE_DRAGGING:
            if current_pinch_is_physically_closed:
                pinch_current_mid_x_norm, pinch_current_mid_y_norm = utils.get_pinch_midpoint_normalized(thumb_tip, index_tip)
                current_pinch_screen_pos = utils.map_to_screen(pinch_current_mid_x_norm, pinch_current_mid_y_norm)
                recognized_gesture = config.GESTURE_DRAGGING
                gesture_data = {'x': current_pinch_screen_pos[0], 'y': current_pinch_screen_pos[1], 'performed_action': True}
            else:
                recognized_gesture = config.GESTURE_DRAG_DROP
                gesture_data['performed_action'] = True
                self._reset_all_states()

        elif self.current_state == config.STATE_SCROLL_MODE:
            if not (is_middle_finger_extended and other_fingers_curled_for_scroll):
                self._reset_all_states()
                recognized_gesture = config.GESTURE_NONE
            elif self.prev_middle_finger_tip_y is not None:
                curr_middle_finger_tip_y = middle_tip.y
                dy_middle_finger = curr_middle_finger_tip_y - self.prev_middle_finger_tip_y

                if abs(dy_middle_finger) > config.SCROLL_MOVEMENT_THRESHOLD_Y:
                    scroll_amount = int(-1 * dy_middle_finger * config.SCROLL_SENSITIVITY_FACTOR)
                    if scroll_amount > 0:
                        recognized_gesture = config.GESTURE_SCROLL_UP
                    else:
                        recognized_gesture = config.GESTURE_SCROLL_DOWN
                    gesture_data = {'amount': scroll_amount, 'performed_action': True}
                else:
                    recognized_gesture = config.GESTURE_SCROLL_MODE_ENGAGED
                self.prev_middle_finger_tip_y = curr_middle_finger_tip_y
            else:
                 recognized_gesture = config.GESTURE_SCROLL_MODE_ENGAGED


        elif self.current_state == config.STATE_SWIPE_PENDING:
            # If in swipe pending, check for completion or timeout
            if current_time - self.swipe_start_time > config.SWIPE_ACTION_DELAY or not is_hand_fully_open_posture:
                self._reset_all_states()
                recognized_gesture = config.GESTURE_NONE
            elif self.swipe_start_wrist_pos:
                dx, dy = utils.calculate_movement_2d_normalized(self.swipe_start_wrist_pos, wrist)
                total_dist = utils.calculate_distance_2d((self.swipe_start_wrist_pos.x, self.swipe_start_wrist_pos.y), (wrist.x, wrist.y))

                if total_dist > config.SWIPE_MIN_DISTANCE_NORM:
                    if abs(dx) > abs(dy):
                        if dx > 0: recognized_gesture = config.GESTURE_SWIPE_RIGHT
                        else: recognized_gesture = config.GESTURE_SWIPE_LEFT
                    else:
                        if dy > 0: recognized_gesture = config.GESTURE_SWIPE_DOWN
                        else: recognized_gesture = config.GESTURE_SWIPE_UP
                    gesture_data['performed_action'] = True
                    self.last_gesture_time = current_time
                    self._reset_all_states()
                else:
                    recognized_gesture = config.GESTURE_NONE


        # Always update prev_landmarks for the next frame's calculations if a hand is detected
        # This line was originally after mouse moving logic, now it's important to be here or inside blocks that return.
        # Ensure it's updated for all paths that might lead to a return.
        self.prev_landmarks = hand_landmark_obj
        self.last_mouse_pos_normalized = (index_tip.x, index_tip.y) # Always update, even if not mouse moving, for smoother re-entry


        if recognized_gesture not in [config.GESTURE_NONE, config.GESTURE_SCROLL_MODE_ENGAGED] and \
           'performed_action' not in gesture_data:
            gesture_data['performed_action'] = True

        print(f"Time: {current_time:.2f}, State: {self.current_state}, Recognized Gesture: {recognized_gesture}, Actionable: {gesture_data.get('performed_action', False)}")
        return recognized_gesture, gesture_data
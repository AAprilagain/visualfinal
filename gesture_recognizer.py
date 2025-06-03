# gesture_recognizer.py

import time
import config
import utils

class GestureRecognizer:
    def __init__(self):
        # State machine current state
        self.current_state = config.STATE_IDLE

        # Pinch/Click/Drag related states and timers
        self.pinch_start_time = 0.0
        self.last_click_time = 0.0
        self.pinch_start_screen_pos = (0, 0)
        self.last_mouse_pos_normalized = (0, 0) # For mouse movement smoothing

        # Scroll related states
        self.scroll_mode_engaged_time = 0.0

        # Swipe related states
        self.swipe_start_time = 0.0
        self.swipe_start_wrist_pos = None # Stores NormalizedLandmark object
        self.last_gesture_time = 0.0

        # Landmark history for speed/movement calculation
        self.prev_landmarks = None # Stores the entire NormalizedLandmarkList object

    def _reset_all_states(self):
        """Resets all internal states to IDLE and clears all timers/positions."""
        self.current_state = config.STATE_IDLE
        self.pinch_start_time = 0.0
        self.last_click_time = 0.0
        self.pinch_start_screen_pos = (0, 0)
        self.scroll_mode_engaged_time = 0.0
        self.swipe_start_time = 0.0
        self.swipe_start_wrist_pos = None
        self.prev_landmarks = None

    def recognize(self, hand_landmark_obj):
        """
        Recognizes a gesture from the given hand landmarks object using a state machine.
        Args:
            hand_landmark_obj: The MediaPipe NormalizedLandmarkList object for the detected hand.
        Returns:
            A tuple (gesture_name, data_dict) or (None, None) if no specific gesture.
            gesture_name: A string from config.GESTURE_*
            data_dict: Contains relevant data for the gesture (e.g., coordinates, scroll amount)
        """
        current_time = time.time()
        recognized_gesture = config.GESTURE_NONE
        gesture_data = {}

        if not hand_landmark_obj:
            # If no hand detected, transition to IDLE and reset if not already
            if self.current_state != config.STATE_IDLE:
                # If we were dragging, dropping should be the last action
                if self.current_state == config.STATE_DRAGGING:
                    recognized_gesture = config.GESTURE_DRAG_DROP
                    gesture_data = {}
                self._reset_all_states()
            return recognized_gesture, gesture_data

        actual_landmarks = hand_landmark_obj.landmark
        thumb_tip = actual_landmarks[config.mp_hands.HandLandmark.THUMB_TIP]
        index_tip = actual_landmarks[config.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        wrist = actual_landmarks[config.mp_hands.HandLandmark.WRIST]

        pinch_dist = utils.calculate_distance_3d(thumb_tip, index_tip)
        current_pinch_is_physically_closed = pinch_dist < config.PINCH_THRESHOLD_CLOSE
        current_pinch_is_physically_open = pinch_dist > config.PINCH_THRESHOLD_OPEN

        # Get finger extension states (for scroll mode and mouse movement)
        finger_ext_states = utils.get_finger_extended_states(actual_landmarks)
        thumb_ext_state = utils.is_thumb_extended(actual_landmarks)

        # --- State Machine Logic ---
        if self.current_state == config.STATE_IDLE:
            if current_pinch_is_physically_closed:
                self.current_state = config.STATE_PINCH_DETECTED
                self.pinch_start_time = current_time
                self.last_click_time = current_time # Assume this pinch might be a click
                pinch_mid_x_norm, pinch_mid_y_norm = utils.get_pinch_midpoint_normalized(thumb_tip, index_tip)
                self.pinch_start_screen_pos = utils.map_to_screen(pinch_mid_x_norm, pinch_mid_y_norm)
                recognized_gesture = config.GESTURE_NONE # No action yet, just state change
            elif thumb_ext_state and not any(finger_ext_states): # Thumbs up gesture
                self.current_state = config.STATE_SCROLL_MODE
                self.scroll_mode_engaged_time = current_time
                recognized_gesture = config.GESTURE_SCROLL_MODE_ENGAGED # Informational
            elif finger_ext_states[0] and not any(finger_ext_states[1:]): # Index finger extended
                target_x, target_y = utils.map_to_screen(index_tip.x, index_tip.y)
                recognized_gesture = config.GESTURE_MOUSE_MOVING
                gesture_data = {'x': target_x, 'y': target_y}
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
                    self.current_state = config.STATE_SWIPE_PENDING # Consider this a pending swipe
                    self.swipe_start_time = current_time
                    self.swipe_start_wrist_pos = wrist # Store current wrist position
                    # We'll determine direction and recognize the gesture in the next frame if swipe continues
                    recognized_gesture = config.GESTURE_NONE # Not yet, prevent immediate action

        elif self.current_state == config.STATE_PINCH_DETECTED:
            if not current_pinch_is_physically_closed and current_pinch_is_physically_open:
                # Pinch released, determine if click or double click
                if current_time - self.pinch_start_time < config.DRAG_CONFIRM_DURATION:
                    # It was a short pinch, consider it a potential click
                    if current_time - self.last_click_time < config.DOUBLE_CLICK_INTERVAL:
                        recognized_gesture = config.GESTURE_DOUBLE_CLICK
                        self.last_click_time = 0 # Reset for next click sequence
                    else:
                        recognized_gesture = config.GESTURE_LEFT_CLICK
                        self.last_click_time = current_time
                self.current_state = config.STATE_IDLE # Back to idle
            elif current_pinch_is_physically_closed:
                pinch_duration = current_time - self.pinch_start_time
                pinch_mid_x_norm, pinch_mid_y_norm = utils.get_pinch_midpoint_normalized(thumb_tip, index_tip)
                current_pinch_screen_pos = utils.map_to_screen(pinch_mid_x_norm, pinch_mid_y_norm)
                movement_since_pinch_start = utils.calculate_distance_2d(self.pinch_start_screen_pos, current_pinch_screen_pos)

                if pinch_duration > config.DRAG_CONFIRM_DURATION and \
                   movement_since_pinch_start > config.DRAG_CONFIRM_MOVEMENT_THRESHOLD:
                    self.current_state = config.STATE_DRAGGING
                    recognized_gesture = config.GESTURE_DRAG_START
                    gesture_data = {'x': current_pinch_screen_pos[0], 'y': current_pinch_screen_pos[1]}
            # If still pinching but not dragging yet, remain in STATE_PINCH_DETECTED


        elif self.current_state == config.STATE_DRAGGING:
            if current_pinch_is_physically_closed:
                # 确保在这里重新计算 pinch_current_mid_x_norm 和 pinch_current_mid_y_norm
                pinch_current_mid_x_norm, pinch_current_mid_y_norm = utils.get_pinch_midpoint_normalized(thumb_tip, index_tip)  #
                current_pinch_screen_pos = utils.map_to_screen(pinch_current_mid_x_norm, pinch_current_mid_y_norm)  #
                recognized_gesture = config.GESTURE_DRAGGING  #
                gesture_data = {'x': current_pinch_screen_pos[0], 'y': current_pinch_screen_pos[1]}  #
            else:  # Pinch released, end drag
                recognized_gesture = config.GESTURE_DRAG_DROP  #
                self._reset_all_states()  # Back to idle #

        elif self.current_state == config.STATE_SCROLL_MODE:
            if not (thumb_ext_state and not any(finger_ext_states)): # If thumbs up is no longer active
                self._reset_all_states() # Exit scroll mode
                recognized_gesture = config.GESTURE_NONE # Or a "Scroll Mode Ended" gesture if desired
            elif self.prev_landmarks:
                curr_wrist_y = wrist.y
                prev_wrist_y = self.prev_landmarks.landmark[config.mp_hands.HandLandmark.WRIST].y
                dy_wrist = curr_wrist_y - prev_wrist_y

                if abs(dy_wrist) > config.SCROLL_MOVEMENT_THRESHOLD_Y:
                    scroll_amount = int(-1 * dy_wrist * config.SCROLL_SENSITIVITY_FACTOR)
                    if scroll_amount > 0:
                        recognized_gesture = config.GESTURE_SCROLL_UP
                    else:
                        recognized_gesture = config.GESTURE_SCROLL_DOWN
                    gesture_data = {'amount': scroll_amount}
                else:
                    recognized_gesture = config.GESTURE_SCROLL_MODE_ENGAGED # Still in scroll mode, but no action

        elif self.current_state == config.STATE_SWIPE_PENDING:
            if current_time - self.swipe_start_time > config.SWIPE_ACTION_DELAY:
                # If too much time has passed, reset
                self._reset_all_states()
                recognized_gesture = config.GESTURE_NONE
            elif self.swipe_start_wrist_pos:
                dx, dy = utils.calculate_movement_2d_normalized(self.swipe_start_wrist_pos, wrist)
                total_dist = utils.calculate_distance_2d((self.swipe_start_wrist_pos.x, self.swipe_start_wrist_pos.y), (wrist.x, wrist.y))

                if total_dist > config.SWIPE_MIN_DISTANCE_NORM: # Confirm enough movement
                    if abs(dx) > abs(dy): # Horizontal swipe
                        if dx > 0: recognized_gesture = config.GESTURE_SWIPE_RIGHT
                        else: recognized_gesture = config.GESTURE_SWIPE_LEFT
                    else: # Vertical swipe
                        if dy > 0: recognized_gesture = config.GESTURE_SWIPE_DOWN
                        else: recognized_gesture = config.GESTURE_SWIPE_UP
                    self.last_gesture_time = current_time # Update last gesture time to prevent rapid firing
                    self._reset_all_states() # Swipe recognized, back to IDLE state

        # Update previous landmarks for next frame's calculations
        self.prev_landmarks = hand_landmark_obj
        self.last_mouse_pos_normalized = (index_tip.x, index_tip.y) # Store for smoothing if needed elsewhere

        if recognized_gesture != config.GESTURE_NONE and recognized_gesture != config.GESTURE_SCROLL_MODE_ENGAGED:
            gesture_data['performed_action'] = True # Flag indicates an actionable gesture

        print(f"Time: {current_time:.2f}, State: {self.current_state}, Recognized Gesture: {recognized_gesture}, Actionable: {gesture_data.get('performed_action', False)}")
        return recognized_gesture, gesture_data
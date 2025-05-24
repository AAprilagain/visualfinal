# gesture_recognizer.py

import time
import config
import utils

class GestureRecognizer:
    def __init__(self):
        # Pinch/Click/Drag states
        self.was_pinching_last_frame = False
        self.is_dragging_state = False # Internal state of physical drag
        self.pinch_start_time = 0.0
        self.last_click_action_time = 0.0
        self.pending_single_click = False
        self.pinch_start_screen_pos = (0, 0)

        # Landmark history for speed/movement calculation
        # self.prev_landmarks will store the entire NormalizedLandmarkList object from the previous frame
        self.prev_landmarks = None
        self.last_gesture_time = 0 # To prevent rapid firing of some gestures like swipe

    def _reset_pinch_states(self):
        self.was_pinching_last_frame = False
        self.is_dragging_state = False
        self.pending_single_click = False

    def recognize(self, hand_landmark_obj): # Parameter renamed for clarity
        """
        Recognizes a gesture from the given hand landmarks object.
        Args:
            hand_landmark_obj: The MediaPipe NormalizedLandmarkList object for the detected hand.
        Returns:
            A tuple (gesture_name, data_dict) or (None, None) if no specific gesture.
            gesture_name: A string from config.GESTURE_*
            data_dict: Contains relevant data for the gesture (e.g., coordinates, scroll amount)
        """
        if not hand_landmark_obj:
            if self.is_dragging_state:
                self._reset_pinch_states()
                return config.GESTURE_DRAG_DROP, {}
            self._reset_pinch_states()
            self.prev_landmarks = None
            return config.GESTURE_NONE, {}

        # Access the actual list of landmark points
        actual_landmarks = hand_landmark_obj.landmark

        current_time = time.time()
        recognized_gesture = config.GESTURE_NONE
        gesture_data = {}
        action_performed_this_frame = False

        # Use actual_landmarks for subscripting
        thumb_tip = actual_landmarks[config.mp_hands.HandLandmark.THUMB_TIP] # Using MediaPipe enums for clarity
        index_tip = actual_landmarks[config.mp_hands.HandLandmark.INDEX_FINGER_TIP]
        wrist = actual_landmarks[config.mp_hands.HandLandmark.WRIST]

        # --- 1. Pinch Physical State Detection ---
        # utils.calculate_distance_3d expects landmark objects (like thumb_tip, index_tip), which is correct
        pinch_dist = utils.calculate_distance_3d(thumb_tip, index_tip)
        current_pinch_is_physically_active = pinch_dist < config.PINCH_THRESHOLD_CLOSE

        pinch_just_started = current_pinch_is_physically_active and not self.was_pinching_last_frame
        pinch_just_released = not current_pinch_is_physically_active and self.was_pinching_last_frame

        # --- 2. Pinch-related Actions (Click, Double Click, Drag) ---
        if pinch_just_started:
            self.pinch_start_time = current_time
            pinch_mid_x_norm, pinch_mid_y_norm = utils.get_pinch_midpoint_normalized(thumb_tip, index_tip)
            self.pinch_start_screen_pos = utils.map_to_screen(pinch_mid_x_norm, pinch_mid_y_norm)

            if current_time - self.last_click_action_time < config.DOUBLE_CLICK_INTERVAL and self.last_click_action_time != 0:
                recognized_gesture = config.GESTURE_DOUBLE_CLICK
                self.last_click_action_time = 0
                self.pending_single_click = False
            else:
                self.pending_single_click = True
            action_performed_this_frame = True

        elif current_pinch_is_physically_active:
            pinch_current_mid_x_norm, pinch_current_mid_y_norm = utils.get_pinch_midpoint_normalized(thumb_tip, index_tip)
            current_pinch_screen_pos = utils.map_to_screen(pinch_current_mid_x_norm, pinch_current_mid_y_norm)

            if not self.is_dragging_state:
                pinch_duration = current_time - self.pinch_start_time
                movement_since_pinch_start = utils.calculate_distance_2d(self.pinch_start_screen_pos, current_pinch_screen_pos)

                if pinch_duration > config.DRAG_CONFIRM_DURATION and \
                   movement_since_pinch_start > config.DRAG_CONFIRM_MOVEMENT:
                    self.is_dragging_state = True
                    self.pending_single_click = False
                    recognized_gesture = config.GESTURE_DRAG_START
                    gesture_data = {'x': current_pinch_screen_pos[0], 'y': current_pinch_screen_pos[1]}

            if self.is_dragging_state: # This condition should likely be part of the above if, or ensure it's mutually exclusive
                recognized_gesture = config.GESTURE_DRAGGING
                gesture_data = {'x': current_pinch_screen_pos[0], 'y': current_pinch_screen_pos[1]}
            action_performed_this_frame = True # This should be set if any action in this block is taken

        elif pinch_just_released:
            if self.is_dragging_state:
                recognized_gesture = config.GESTURE_DRAG_DROP
                self.is_dragging_state = False
            elif self.pending_single_click:
                recognized_gesture = config.GESTURE_LEFT_CLICK
                self.last_click_action_time = current_time
            self.pending_single_click = False
            action_performed_this_frame = True

        # --- 3. Other Gestures (if no pinch action was definitive) ---
        if not action_performed_this_frame:
            # Pass the list of landmark points (actual_landmarks) to utility functions
            finger_ext_states = utils.get_finger_extended_states(actual_landmarks)
            thumb_ext_state = utils.is_thumb_extended(actual_landmarks)

            if finger_ext_states[0] and not any(finger_ext_states[1:]) and \
               not current_pinch_is_physically_active and not self.is_dragging_state:
                target_x, target_y = utils.map_to_screen(index_tip.x, index_tip.y)
                recognized_gesture = config.GESTURE_MOUSE_MOVING
                gesture_data = {'x': target_x, 'y': target_y}
                action_performed_this_frame = True

            elif thumb_ext_state and not any(finger_ext_states):
                recognized_gesture = config.GESTURE_SCROLL_MODE_ENGAGED
                if self.prev_landmarks: # self.prev_landmarks is the NormalizedLandmarkList object
                    curr_wrist_y = wrist.y # wrist is actual_landmarks[config.mp_hands.HandLandmark.WRIST]
                    prev_wrist_y = self.prev_landmarks.landmark[config.mp_hands.HandLandmark.WRIST].y # Access .landmark here
                    dy_wrist = curr_wrist_y - prev_wrist_y

                    if abs(dy_wrist) > config.SCROLL_MOVEMENT_THRESHOLD_Y:
                        scroll_amount = int(-1 * dy_wrist * config.SCROLL_SENSITIVITY_FACTOR)
                        if scroll_amount > 0:
                            recognized_gesture = config.GESTURE_SCROLL_UP
                        else:
                            recognized_gesture = config.GESTURE_SCROLL_DOWN
                        gesture_data = {'amount': scroll_amount}
                        action_performed_this_frame = True

            elif self.prev_landmarks and (current_time - self.last_gesture_time > config.SWIPE_ACTION_DELAY):
                # self.prev_landmarks is the NormalizedLandmarkList object
                prev_wrist_lm = self.prev_landmarks.landmark[config.mp_hands.HandLandmark.WRIST] # Access .landmark
                palm_center_x_prev = prev_wrist_lm.x
                palm_center_y_prev = prev_wrist_lm.y
                palm_center_x_curr = wrist.x # wrist is actual_landmarks[config.mp_hands.HandLandmark.WRIST]
                palm_center_y_curr = wrist.y

                dx = palm_center_x_curr - palm_center_x_prev
                dy = palm_center_y_curr - palm_center_y_prev
                frame_interval = 1 / config.ASSUMED_FPS

                speed_x = abs(dx) / frame_interval if frame_interval > 0 else 0
                speed_y = abs(dy) / frame_interval if frame_interval > 0 else 0

                if speed_x > config.SWIPE_THRESHOLD_SPEED or speed_y > config.SWIPE_THRESHOLD_SPEED:
                    if speed_x > speed_y:
                        if dx > 0: recognized_gesture = config.GESTURE_SWIPE_RIGHT
                        else: recognized_gesture = config.GESTURE_SWIPE_LEFT
                    else:
                        if dy > 0: recognized_gesture = config.GESTURE_SWIPE_DOWN
                        else: recognized_gesture = config.GESTURE_SWIPE_UP
                    action_performed_this_frame = True
                    self.last_gesture_time = current_time

        self.was_pinching_last_frame = current_pinch_is_physically_active
        # Store the entire NormalizedLandmarkList object for the next frame
        self.prev_landmarks = hand_landmark_obj

        if recognized_gesture != config.GESTURE_NONE and recognized_gesture != config.GESTURE_SCROLL_MODE_ENGAGED:
            gesture_data['performed_action'] = True

        return recognized_gesture, gesture_data
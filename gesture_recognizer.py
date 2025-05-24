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
        self.prev_landmarks = None
        self.last_gesture_time = 0 # To prevent rapid firing of some gestures like swipe

    def _reset_pinch_states(self):
        self.was_pinching_last_frame = False
        self.is_dragging_state = False
        self.pending_single_click = False
        # self.pinch_start_time = 0.0 # Keep for duration check on release
        # self.last_click_action_time = 0.0 # Keep for double click interval

    def recognize(self, landmarks):
        """
        Recognizes a gesture from the given hand landmarks.
        Returns:
            A tuple (gesture_name, data_dict) or (None, None) if no specific gesture.
            gesture_name: A string from config.GESTURE_*
            data_dict: Contains relevant data for the gesture (e.g., coordinates, scroll amount)
        """
        if not landmarks:
            if self.is_dragging_state: # If hand disappears during drag, consider it a drop
                self._reset_pinch_states()
                return config.GESTURE_DRAG_DROP, {}
            self._reset_pinch_states()
            self.prev_landmarks = None
            return config.GESTURE_NONE, {}

        current_time = time.time()
        recognized_gesture = config.GESTURE_NONE
        gesture_data = {}
        action_performed_this_frame = False # To prioritize gestures

        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        wrist = landmarks[0]

        # --- 1. Pinch Physical State Detection ---
        pinch_dist = utils.calculate_distance_3d(thumb_tip, index_tip)
        current_pinch_is_physically_active = pinch_dist < config.PINCH_THRESHOLD_CLOSE

        pinch_just_started = current_pinch_is_physically_active and not self.was_pinching_last_frame
        pinch_just_released = not current_pinch_is_physically_active and self.was_pinching_last_frame

        # --- 2. Pinch-related Actions (Click, Double Click, Drag) ---
        if pinch_just_started:
            self.pinch_start_time = current_time
            pinch_mid_x_norm, pinch_mid_y_norm = utils.get_pinch_midpoint_normalized(thumb_tip, index_tip)
            self.pinch_start_screen_pos = utils.map_to_screen(pinch_mid_x_norm, pinch_mid_y_norm)

            # Check for Double Click
            if current_time - self.last_click_action_time < config.DOUBLE_CLICK_INTERVAL and self.last_click_action_time != 0:
                recognized_gesture = config.GESTURE_DOUBLE_CLICK
                self.last_click_action_time = 0  # Reset to prevent triple clicks
                self.pending_single_click = False
            else:
                self.pending_single_click = True # Potential single click
            action_performed_this_frame = True
            # recognized_gesture = config.GESTURE_PINCH_START # Could be an event too

        elif current_pinch_is_physically_active: # Pinch is being held
            pinch_current_mid_x_norm, pinch_current_mid_y_norm = utils.get_pinch_midpoint_normalized(thumb_tip, index_tip)
            current_pinch_screen_pos = utils.map_to_screen(pinch_current_mid_x_norm, pinch_current_mid_y_norm)

            if not self.is_dragging_state: # Not yet dragging, check if drag should start
                pinch_duration = current_time - self.pinch_start_time
                movement_since_pinch_start = utils.calculate_distance_2d(self.pinch_start_screen_pos, current_pinch_screen_pos)

                if pinch_duration > config.DRAG_CONFIRM_DURATION and \
                   movement_since_pinch_start > config.DRAG_CONFIRM_MOVEMENT:
                    self.is_dragging_state = True
                    self.pending_single_click = False # Drag overrides pending click
                    recognized_gesture = config.GESTURE_DRAG_START
                    # The actual mouse down will be handled by action_controller
                    # Dragging will involve continuous MOUSE_MOVE updates
                    gesture_data = {'x': current_pinch_screen_pos[0], 'y': current_pinch_screen_pos[1]}

            if self.is_dragging_state:
                recognized_gesture = config.GESTURE_DRAGGING
                gesture_data = {'x': current_pinch_screen_pos[0], 'y': current_pinch_screen_pos[1]}
            action_performed_this_frame = True

        elif pinch_just_released:
            if self.is_dragging_state:
                recognized_gesture = config.GESTURE_DRAG_DROP
                self.is_dragging_state = False
            elif self.pending_single_click:
                # Check if it was a very short pinch (tap) vs a hold then release without drag
                # This simple model assumes any non-drag release after pending is a click
                recognized_gesture = config.GESTURE_LEFT_CLICK
                self.last_click_action_time = current_time # Record time for double click
            self.pending_single_click = False
            action_performed_this_frame = True

        # --- 3. Other Gestures (if no pinch action was definitive) ---
        if not action_performed_this_frame:
            finger_ext_states = utils.get_finger_extended_states(landmarks)
            thumb_ext_state = utils.is_thumb_extended(landmarks)

            # --- Mouse Moving (Index finger pointing) ---
            if finger_ext_states[0] and not any(finger_ext_states[1:]) and \
               not current_pinch_is_physically_active and not self.is_dragging_state: # Ensure not pinching/dragging
                target_x, target_y = utils.map_to_screen(index_tip.x, index_tip.y)
                recognized_gesture = config.GESTURE_MOUSE_MOVING
                gesture_data = {'x': target_x, 'y': target_y}
                action_performed_this_frame = True

            # --- Scroll Gesture (Thumbs up, then vertical wrist movement) ---
            elif thumb_ext_state and not any(finger_ext_states): # Thumbs up pose
                recognized_gesture = config.GESTURE_SCROLL_MODE_ENGAGED # Inform user
                if self.prev_landmarks:
                    curr_wrist_y = wrist.y
                    prev_wrist_y = self.prev_landmarks[0].y # Wrist landmark is 0
                    dy_wrist = curr_wrist_y - prev_wrist_y

                    if abs(dy_wrist) > config.SCROLL_MOVEMENT_THRESHOLD_Y:
                        scroll_amount = int(-1 * dy_wrist * config.SCROLL_SENSITIVITY_FACTOR)
                        if scroll_amount > 0:
                            recognized_gesture = config.GESTURE_SCROLL_UP
                        else:
                            recognized_gesture = config.GESTURE_SCROLL_DOWN
                        gesture_data = {'amount': scroll_amount}
                        action_performed_this_frame = True
                # If no scroll movement, it's just "scroll mode engaged"

            # --- Swipe Gestures (Based on wrist movement if no other specific gesture) ---
            # Ensure enough time has passed since the last swipe to prevent multiple triggers
            elif self.prev_landmarks and (current_time - self.last_gesture_time > config.SWIPE_ACTION_DELAY):
                palm_center_x_prev = self.prev_landmarks[0].x
                palm_center_y_prev = self.prev_landmarks[0].y
                palm_center_x_curr = wrist.x
                palm_center_y_curr = wrist.y

                dx = palm_center_x_curr - palm_center_x_prev
                dy = palm_center_y_curr - palm_center_y_prev

                # Estimate frame interval (can be made more precise if needed)
                frame_interval = 1 / config.ASSUMED_FPS # A more robust solution would measure actual time delta

                speed_x = abs(dx) / frame_interval if frame_interval > 0 else 0
                speed_y = abs(dy) / frame_interval if frame_interval > 0 else 0

                if speed_x > config.SWIPE_THRESHOLD_SPEED or speed_y > config.SWIPE_THRESHOLD_SPEED:
                    if speed_x > speed_y: # Horizontal swipe
                        if dx > 0: recognized_gesture = config.GESTURE_SWIPE_RIGHT
                        else: recognized_gesture = config.GESTURE_SWIPE_LEFT
                    else: # Vertical swipe
                        if dy > 0: recognized_gesture = config.GESTURE_SWIPE_DOWN # Y increases downwards
                        else: recognized_gesture = config.GESTURE_SWIPE_UP
                    action_performed_this_frame = True
                    self.last_gesture_time = current_time # Update time of last swipe

        # Update states for next frame
        self.was_pinching_last_frame = current_pinch_is_physically_active
        self.prev_landmarks = landmarks

        # If a gesture was performed, clear pending single click unless it was the click itself
        if action_performed_this_frame and recognized_gesture not in [config.GESTURE_LEFT_CLICK, config.GESTURE_PINCH_START]:
             if recognized_gesture != config.GESTURE_NONE and self.pending_single_click and not current_pinch_is_physically_active:
                # If a different action happened while a click was pending AND pinch was released, cancel click
                # This logic needs to be robust. E.g. if swipe happens while pinch held, click might still be valid on release.
                # For now, any other action clears it if not actively pinching.
                pass # This area can be tricky, current logic tries to make click happen on release if nothing else interceded.

        if recognized_gesture != config.GESTURE_NONE and recognized_gesture != config.GESTURE_SCROLL_MODE_ENGAGED:
             gesture_data['performed_action'] = True # Flag that an action was taken

        return recognized_gesture, gesture_data
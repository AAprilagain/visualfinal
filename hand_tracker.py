import cv2
import mediapipe as mp
import config

class HandTracker:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            model_complexity=1,
            max_num_hands=config.MAX_NUM_HANDS,
            min_detection_confidence=config.MIN_DETECTION_CONFIDENCE,
            min_tracking_confidence=config.MIN_TRACKING_CONFIDENCE
        )
        self.mp_draw = mp.solutions.drawing_utils

    def process_frame(self, frame):
        """
        Processes a video frame to detect hand landmarks.
        Args:
            frame: The BGR video frame.
        Returns:
            A tuple (processed_frame, hand_landmarks).
            processed_frame: The frame with landmarks drawn (if any).
            hand_landmarks: MediaPipe landmarks object for the first detected hand, or None.
        """
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(rgb_frame)

        hand_landmarks_data = None
        if results.multi_hand_landmarks:
            # For simplicity, using the first detected hand
            hand_landmarks_data = results.multi_hand_landmarks[0]
            self.mp_draw.draw_landmarks(
                frame,
                hand_landmarks_data,
                self.mp_hands.HAND_CONNECTIONS
            )
        return frame, hand_landmarks_data

    def close(self):
        self.hands.close()
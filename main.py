import cv2
import config
from hand_tracker import HandTracker
from gesture_recognizer import GestureRecognizer
from action_controller import ActionController
import app_detector # For manually cycling profiles in this example

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Cannot open camera.")
        return

    hand_tracker = HandTracker()
    gesture_recognizer = GestureRecognizer()
    action_controller = ActionController()

    current_display_gesture = config.GESTURE_NONE
    last_actionable_gesture = config.GESTURE_NONE # To keep displaying the last *action*

    print("Gesture Control HCI Started.")
    print("Press 'q' to quit.")
    print("Press 'p' to cycle through application profiles.")

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("Ignoring empty camera frame.")
            continue

        frame = cv2.flip(frame, 1) # Flip horizontally for intuitive movement

        # Process frame for hand landmarks
        processed_frame, landmarks = hand_tracker.process_frame(frame)

        # Recognize gesture
        recognized_gesture_name, gesture_data = gesture_recognizer.recognize(landmarks)

        # Update display gesture
        # Only update current_display_gesture if it's not GESTURE_NONE or if it's an actionable gesture
        if recognized_gesture_name != config.GESTURE_NONE:
            current_display_gesture = recognized_gesture_name
            # If the gesture was actionable, store it as the last actionable one
            if gesture_data.get('performed_action', False):
                 last_actionable_gesture = recognized_gesture_name
        # else: # Removed this else block to maintain display of continuous gestures like MOUSE_MOVING
        #     current_display_gesture = config.GESTURE_NONE


        # Execute action based on gesture
        # We only execute if a specific action was recognized AND it's not purely informational (like SCROLL_MODE_ENGAGED)
        if recognized_gesture_name != config.GESTURE_NONE and \
           recognized_gesture_name != config.GESTURE_SCROLL_MODE_ENGAGED and \
           gesture_data.get('performed_action', False): # Ensure it's an actionable gesture from the recognizer
            action_controller.execute_action(recognized_gesture_name, gesture_data)


        # Display information on frame
        # Display current active profile
        profile_text = f"Profile: {app_detector.get_current_profile_display_name()}"
        cv2.putText(processed_frame, profile_text, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

        # Display the most relevant gesture
        display_text = current_display_gesture
        # Prioritize showing scroll mode if active, or mouse moving if active
        if recognized_gesture_name == config.GESTURE_SCROLL_MODE_ENGAGED:
            display_text = config.GESTURE_SCROLL_MODE_ENGAGED
        elif recognized_gesture_name == config.GESTURE_MOUSE_MOVING:
            display_text = config.GESTURE_MOUSE_MOVING
        elif current_display_gesture == config.GESTURE_NONE and last_actionable_gesture != config.GESTURE_NONE:
            display_text = f"Last Action: {last_actionable_gesture}" # Show last action if current is none


        cv2.putText(processed_frame, display_text, (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

        cv2.imshow('Gesture Control HCI', processed_frame)

        key = cv2.waitKey(5) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('p'): # Manual profile cycling for demo
            app_detector.cycle_app_profile()
            action_controller.update_profile() # Ensure controller knows
            last_actionable_gesture = config.GESTURE_NONE # Reset last action display

    cap.release()
    cv2.destroyAllWindows()
    hand_tracker.close()
    print("Gesture Control HCI Stopped.")

if __name__ == '__main__':
    main()
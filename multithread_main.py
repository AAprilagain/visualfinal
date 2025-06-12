import cv2
import time
import numpy as np
import sys
import ctypes
import queue
import threading

import cProfile
import pstats

import utils
import config
from hand_tracker import HandTracker
from gesture_recognizer import GestureRecognizer
from action_controller import ActionController # Import ActionController
import app_detector

frame_queue = queue.Queue(maxsize=2)
result_queue = queue.Queue(maxsize=2)
stop_event = threading.Event() # This will be managed by the UI

# Global variable to hold the ActionController instance
_global_action_controller_instance = None

if sys.platform == "win32":
    # These handles will be set once the main_threaded_wrapper is called and the window is created
    hwnd = None
    HWND_TOPMOST = -1
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOACTIVATE = 0x0010
    FLAGS = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE

def set_action_controller(controller_instance):
    """Setter for the global ActionController instance."""
    global _global_action_controller_instance
    _global_action_controller_instance = controller_instance

def get_action_controller():
    """Getter for the global ActionController instance."""
    return _global_action_controller_instance

def camera_worker(cap, frame_q, stop_ev):
    print("Camera worker started")
    while not stop_ev.is_set():
        if frame_q.full():
            time.sleep(0.001)
            continue
        success, frame = cap.read()
        if success:
            frame = cv2.flip(frame, 1)
            try:
                frame_q.put(frame, block=False)
            except queue.Full:
                pass
        else:
            time.sleep(0.01)
    print("Camera worker stopped")

def processing_worker(hand_tracker, gesture_recognizer, frame_q, result_q, stop_ev):
    print("Processing worker started")
    while not stop_ev.is_set():
        try:
            _get_start_time = time.perf_counter()
            frame = frame_q.get(block=True, timeout=0.1)
            _get_duration_ms = (time.perf_counter() - _get_start_time) * 1000
            if _get_duration_ms > 90:
                # print(f"DEBUG: frame_q.get() took {_get_duration_ms:.2f} ms (close to timeout)")
                pass # Suppress frequent timeout messages unless truly debugging
        except queue.Empty:
            # print("DEBUG: frame_q.get() TIMED OUT (queue.Empty was raised)")
            continue

        processed_frame_display, landmarks = hand_tracker.process_frame(frame)
        recognized_gesture, gesture_data = gesture_recognizer.recognize(landmarks)

        try:
            result_q.put((recognized_gesture, gesture_data, processed_frame_display), block=False)
        except queue.Full:
            pass
        frame_q.task_done()
    print("Processing worker stopped")


def main_threaded_wrapper():
    """
    Wrapper function to encapsulate the gesture control main loop,
    allowing it to be started and stopped by the UI.
    """
    global hwnd # Use global hwnd

    # Reset the stop event in case it was set from a previous run
    stop_event.clear()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Cannot open camera.")
        return

    hand_tracker = HandTracker()
    gesture_recognizer = GestureRecognizer()
    # Get the shared ActionController instance
    action_controller = get_action_controller()
    if action_controller is None:
        print("Error: ActionController instance not set before starting main_threaded_wrapper.")
        cap.release()
        return

    cam_thread = threading.Thread(target=camera_worker, args=(cap, frame_queue, stop_event))
    proc_thread = threading.Thread(target=processing_worker,
                                   args=(hand_tracker, gesture_recognizer, frame_queue, result_queue, stop_event))

    cam_thread.start()
    proc_thread.start()

    current_display_gesture = config.GESTURE_NONE
    last_actionable_gesture = config.GESTURE_NONE
    prev_time_main = time.time()

    try:
        while not stop_event.is_set():
            try:
                recognized_gesture_name, gesture_data, display_frame = result_queue.get(block=True, timeout=0.03)
            except queue.Empty:
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    stop_event.set()
                    break
                continue

            # --- Action Execution ---
            if recognized_gesture_name != config.GESTURE_NONE and \
                    recognized_gesture_name != config.GESTURE_SCROLL_MODE_ENGAGED and \
                    gesture_data.get('performed_action', False):
                action_controller.execute_action(recognized_gesture_name, gesture_data)

            # --- Update Display Text and Show Frame ---
            if recognized_gesture_name != config.GESTURE_NONE:
                current_display_gesture = recognized_gesture_name
                if gesture_data.get('performed_action', False):
                    last_actionable_gesture = recognized_gesture_name
            else:
                current_display_gesture = config.GESTURE_NONE

            profile_text = f"Profile: {app_detector.get_current_profile_display_name()}"
            cv2.putText(display_frame, profile_text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

            display_text = current_display_gesture
            if current_display_gesture == config.GESTURE_NONE and last_actionable_gesture != config.GESTURE_NONE:
                display_text = f"Last Action: {last_actionable_gesture}"
            elif current_display_gesture == config.GESTURE_SCROLL_MODE_ENGAGED:
                display_text = config.GESTURE_SCROLL_MODE_ENGAGED
            cv2.putText(display_frame, display_text, (10, 70),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

            # --- FPS Calculation for main loop---
            curr_time_main = time.time()
            fps_main = 1.0 / (curr_time_main - prev_time_main) if (curr_time_main - prev_time_main) > 0 else 0
            prev_time_main = curr_time_main
            fps_text_main = f"Display FPS: {fps_main:.1f}"
            cv2.putText(display_frame, fps_text_main, (10, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)

            cv2.imshow('HandBridge', display_frame)
            result_queue.task_done()

            if sys.platform == "win32":
                if hwnd is None:
                    hwnd = ctypes.windll.user32.FindWindowW(None, "Gesture Control HCI")
                if hwnd:
                    ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, FLAGS)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                stop_event.set()
                break
            elif key == ord('p'):
                app_detector.cycle_app_profile()
                action_controller.update_profile()
                last_actionable_gesture = config.GESTURE_NONE

    finally:
        print("Stopping threads in multithread_main...")
        stop_event.set() # Ensure all threads are signaled to stop

        if cam_thread.is_alive(): cam_thread.join(timeout=1)
        if proc_thread.is_alive(): proc_thread.join(timeout=1)

        if 'cap' in locals() and cap.isOpened(): cap.release()
        cv2.destroyAllWindows()
        hand_tracker.close()
        print("Gesture Control HCI loop finished.")

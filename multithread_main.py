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
from action_controller import ActionController
import app_detector 

frame_queue = queue.Queue(maxsize=2)  # 限制队列大小，防止处理过多旧帧
result_queue = queue.Queue(maxsize=2)
stop_event = threading.Event()

if sys.platform == "win32":
    hwnd = ctypes.windll.user32.FindWindowW(None, "Gesture Control HCI")
    HWND_TOPMOST = -1
    SWP_NOMOVE = 0x0002
    SWP_NOSIZE = 0x0001
    SWP_NOACTIVATE = 0x0010
    FLAGS = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE


def camera_worker(cap, frame_q, stop_ev):
    print("Camera worker started")
    while not stop_ev.is_set():
        if frame_q.full():
            time.sleep(0.001)  # 队列满则稍等，避免CPU空转
            continue
        success, frame = cap.read()
        if success:
            frame = cv2.flip(frame, 1)
            try:
                frame_q.put(frame, block=False)  # 非阻塞放入
            except queue.Full:
                pass  # 帧丢失
        else:
            time.sleep(0.01)  # 读取失败稍等
    print("Camera worker stopped")


def processing_worker(hand_tracker, gesture_recognizer, frame_q, result_q, stop_ev):
    print("Processing worker started")
    while not stop_ev.is_set():
        try:
            try:
                _get_start_time = time.perf_counter()
                frame = frame_q.get(block=True, timeout=0.1)  # 假设timeout是0.1秒
                _get_duration_ms = (time.perf_counter() - _get_start_time) * 1000
                if _get_duration_ms > 90:  # 如果获取时间接近超时时间
                    print(f"DEBUG: frame_q.get() took {_get_duration_ms:.2f} ms (close to timeout)")
            except queue.Empty:
                print("DEBUG: frame_q.get() TIMED OUT (queue.Empty was raised)")
                continue  # 如果超时，则跳过后续处理，直接开始下一次循环

        except queue.Empty:
            continue

        processed_frame_display, landmarks = hand_tracker.process_frame(frame)
        recognized_gesture, gesture_data = gesture_recognizer.recognize(landmarks)

        try:
            result_q.put((recognized_gesture, gesture_data, processed_frame_display), block=False)
        except queue.Full:
            pass  # 结果丢失
        frame_q.task_done()
    print("Processing worker stopped")


def main_threaded():  # 重命名原来的 main
    # ... 初始化 cap, hand_tracker.py, gesture_recognizer, action_controller ...
    # 确保 action_controller 使用了非阻塞的滑动延时
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Cannot open camera.")
        return

    hand_tracker = HandTracker()
    gesture_recognizer = GestureRecognizer()
    action_controller = ActionController()

    cam_thread = threading.Thread(target=camera_worker, args=(cap, frame_queue, stop_event))
    proc_thread = threading.Thread(target=processing_worker,
                                   args=(hand_tracker, gesture_recognizer, frame_queue, result_queue, stop_event))

    cam_thread.start()
    proc_thread.start()

    current_display_gesture = config.GESTURE_NONE 
    last_actionable_gesture = config.GESTURE_NONE 
    hwnd = None
    prev_time_main = time.time()

    try:
        while not stop_event.is_set():  # 主循环检查 stop_event
            try:
                recognized_gesture_name, gesture_data, display_frame = result_queue.get(block=True,
                                                                                        timeout=0.03)  # 假设超时是0.03秒
            except queue.Empty:
                # 如果队列为空，仍然可以处理键盘输入和更新窗口置顶
                key = cv2.waitKey(1) & 0xFF  # 保持UI响应
                if key == ord('q'):
                    stop_event.set()
                    break
                continue  # 没有新结果则继续循环

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
            # print(fps_text_main)
            cv2.putText(display_frame, fps_text_main, (10, 110),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)  

            cv2.imshow('Gesture Control HCI', display_frame)  
            result_queue.task_done()

            if sys.platform == "win32":
                if hwnd is None:
                    # Find the window handle ONLY ONCE after it has been created
                    hwnd = ctypes.windll.user32.FindWindowW(None, "Gesture Control HCI")
                if hwnd:
                    # Set the window to be topmost in every loop iteration
                    ctypes.windll.user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, FLAGS)

            key = cv2.waitKey(1) & 0xFF  # 保持UI响应
            if key == ord('q'):
                stop_event.set()
                break
            elif key == ord('p'):  
                app_detector.cycle_app_profile()  
                action_controller.update_profile()  
                last_actionable_gesture = config.GESTURE_NONE  


    finally:
        print("Stopping threads...")
        stop_event.set()
        if cam_thread.is_alive(): cam_thread.join(timeout=1)
        if proc_thread.is_alive(): proc_thread.join(timeout=1)

        if 'cap' in locals() and cap.isOpened(): cap.release()  
        cv2.destroyAllWindows()  
        if 'hand_tracker.py' in locals(): hand_tracker.close()  
        print("Gesture Control HCI Stopped.")


if __name__ == '__main__':
    # hwnd 等全局变量初始化需要考虑
    main_threaded()
"""
sit_and_reach.py
Real-time Sit-and-Reach measurement using MediaPipe Pose + OpenCV.

Controls:
 - 'c' : enter calibration mode (click two points on a known-length object on the displayed window)
 - 'r' : reset recorded max
 - 'q' : quit

Outputs:
 - on-screen: current reach (cm if calibrated), max reach
 - CSV: "sit_and_reach_results.csv" (timestamp, reach_px, reach_cm)
"""

import cv2
import mediapipe as mp
import numpy as np
import time
import csv
import webbrowser
import requests

# ---------- USER SETTINGS ----------
SMOOTH_ALPHA = 0.6          # smoothing factor (0..1). Higher = more responsive, lower = smoother
MIN_VISIBILITY = 0.20      # threshold for considering a keypoint "
OUTPUT_CSV = "sit_and_reach_results.csv"
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
# -----------------------------------

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# Globals used by mouse callback and main loop
pixels_per_cm = None
calibrating = False
calib_points = []
calib_frame = None
counter_opened = False  # Add this at the top

def mouse_callback(event, x, y, flags, param):
    """
    Mouse callback used in calibration mode. User clicks two points on a known-length object.
    After two clicks we ask for the real-world length (cm) in the console and compute pixels/cm.
    """
    global calib_points, calib_frame, pixels_per_cm, calibrating
    if not calibrating:
        return
    if event == cv2.EVENT_LBUTTONDOWN:
        calib_points.append((x, y))
        print(f"Calibration click {len(calib_points)}: {x},{y}")
        if len(calib_points) == 2:
            # Draw the line on the frozen frame so the user sees what they clicked
            frame_copy = calib_frame.copy()
            cv2.line(frame_copy, calib_points[0], calib_points[1], (0,255,0), 2)
            cv2.circle(frame_copy, calib_points[0], 5, (0,255,0), -1)
            cv2.circle(frame_copy, calib_points[1], 5, (0,255,0), -1)
            cv2.imshow(WINDOW_NAME, frame_copy)
            # prompt for real-world length
            while True:
                try:
                    val = float(input("Enter the real-world distance between the two clicked points (in cm): "))
                    if val <= 0:
                        print("Enter a positive number.")
                        continue
                    break
                except Exception as e:
                    print("Invalid input. Please enter a number (e.g. 20.0).")
            px = np.linalg.norm(np.array(calib_points[0]) - np.array(calib_points[1]))
            pixels_per_cm = px / val
            print(f"Calibration complete: {pixels_per_cm:.3f} pixels/cm")
            calibrating = False
            calib_points = []

def landmark_to_pixel(landmark, w, h):
    """Convert MediaPipe normalized landmark to pixel coords (x,y)."""
    return int(landmark.x * w), int(landmark.y * h)

def find_best_toe(landmarks):
    """Return the pixel coords of the best visible toe/foot reference (foot index, heel, ankle)."""
    candidates = [
        mp_pose.PoseLandmark.LEFT_FOOT_INDEX,
        mp_pose.PoseLandmark.RIGHT_FOOT_INDEX,
        mp_pose.PoseLandmark.LEFT_HEEL,
        mp_pose.PoseLandmark.RIGHT_HEEL,
        mp_pose.PoseLandmark.LEFT_ANKLE,
        mp_pose.PoseLandmark.RIGHT_ANKLE,
    ]
    for c in candidates:
        lm = landmarks[c.value]
        if lm.visibility > MIN_VISIBILITY:
            return lm
    return None

def main():
    global WINDOW_NAME, calib_frame, calibrating, pixels_per_cm

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Camera could not be opened.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    WINDOW_NAME = "Sit-and-Reach (press 'c' to calibrate, 'q' to quit)"
    cv2.namedWindow(WINDOW_NAME)
    cv2.setMouseCallback(WINDOW_NAME, mouse_callback)

    # CSV writer
    csvfile = open(OUTPUT_CSV, "w", newline="")
    csvw = csv.writer(csvfile)
    csvw.writerow(["timestamp", "reach_px_smoothed", "reach_cm"])

    reach_cm = 0.0
    max_reach_cm = -999.0
    smoothed_reach_px = None

    # Constraint parameters
    KNEE_LOCK_ANGLE = 165      # degrees, threshold for straight leg
    ANKLE_DIST_THRESHOLD = 0.05  # normalized, threshold for feet not sliding
    HIP_Y_THRESHOLD = 0.05     # normalized, threshold for hip lift
    WRIST_Y_DIFF_THRESHOLD = 0.05  # normalized, hands aligned
    HOLD_DURATION = 30         # frames (~1 sec at 30fps)

    # State for hold detection
    hold_frames = 0
    last_valid_reach = None

    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Camera read failed. Exiting.")
                break

            h, w = frame.shape[:2]
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(frame_rgb)
            vis_frame = frame.copy()

            # Draw landmarks for user feedback
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(vis_frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

                lm = results.pose_landmarks.landmark

                # compute hip center x for forward direction guess
                left_hip = lm[mp_pose.PoseLandmark.LEFT_HIP.value]
                right_hip = lm[mp_pose.PoseLandmark.RIGHT_HIP.value]
                hip_center_x = ((left_hip.x + right_hip.x) / 2.0) * w

                # toe reference
                toe_lm = find_best_toe(lm)

                # fingertip candidates (index finger tips)
                left_index = lm[mp_pose.PoseLandmark.LEFT_INDEX.value]
                right_index = lm[mp_pose.PoseLandmark.RIGHT_INDEX.value]

                if toe_lm is not None and (left_index.visibility > MIN_VISIBILITY or right_index.visibility > MIN_VISIBILITY):
                    toe_px = landmark_to_pixel(toe_lm, w, h)
                    left_px = landmark_to_pixel(left_index, w, h)
                    right_px = landmark_to_pixel(right_index, w, h)

                    # choose the hand that is further horizontally from the toe (likely the reaching hand)
                    dist_left = abs(left_px[0] - toe_px[0]) if left_index.visibility > MIN_VISIBILITY else -1
                    dist_right = abs(right_px[0] - toe_px[0]) if right_index.visibility > MIN_VISIBILITY else -1

                    if dist_left >= dist_right:
                        hand_px = left_px
                        hand_vis = left_index.visibility
                    else:
                        hand_px = right_px
                        hand_vis = right_index.visibility

                    # Determine "forward" direction relative to hip->toe: if toe is to the right of hips, forward is +x
                    forward_sign = 1 if toe_px[0] > int(hip_center_x) else -1

                    # raw reach in pixels (positive = fingertip beyond toes in forward direction)
                    reach_px = (hand_px[0] - toe_px[0]) * forward_sign

                    # smooth
                    if smoothed_reach_px is None:
                        smoothed_reach_px = reach_px
                    else:
                        smoothed_reach_px = SMOOTH_ALPHA * reach_px + (1.0 - SMOOTH_ALPHA) * smoothed_reach_px

                    # convert to cm if calibrated
                    reach_cm = None
                    if pixels_per_cm is not None:
                        reach_cm = smoothed_reach_px / pixels_per_cm
                        if reach_cm > max_reach_cm:
                            max_reach_cm = reach_cm
                            # Notify Flask server to increment counter
                            try:
                                requests.post("http://127.0.0.1:5000/increment")
                            except Exception as e:
                                print("Could not update counter:", e)

                # (a) Legs straight and flat
                left_knee = lm[mp_pose.PoseLandmark.LEFT_KNEE.value]
                right_knee = lm[mp_pose.PoseLandmark.RIGHT_KNEE.value]
                left_ankle = lm[mp_pose.PoseLandmark.LEFT_ANKLE.value]
                right_ankle = lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value]
                left_hip = lm[mp_pose.PoseLandmark.LEFT_HIP.value]
                right_hip = lm[mp_pose.PoseLandmark.RIGHT_HIP.value]

                def angle(a, b, c):
                    # Returns angle at point b (in degrees)
                    ba = np.array([a.x - b.x, a.y - b.y])
                    bc = np.array([c.x - b.x, c.y - b.y])
                    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
                    return np.degrees(np.arccos(np.clip(cosine_angle, -1.0, 1.0)))

                left_leg_angle = angle(left_hip, left_knee, left_ankle)
                right_leg_angle = angle(right_hip, right_knee, right_ankle)

                legs_straight = left_leg_angle > KNEE_LOCK_ANGLE and right_leg_angle > KNEE_LOCK_ANGLE

                # (b) Feet placement
                ankle_dist = abs(left_ankle.x - right_ankle.x)
                feet_stable = ankle_dist < ANKLE_DIST_THRESHOLD

                # (c) Hip position
                hip_y = (left_hip.y + right_hip.y) / 2
                ankle_y = (left_ankle.y + right_ankle.y) / 2
                hip_down = abs(hip_y - ankle_y) < HIP_Y_THRESHOLD

                # (d) Hands aligned
                left_wrist = lm[mp_pose.PoseLandmark.LEFT_WRIST.value]
                right_wrist = lm[mp_pose.PoseLandmark.RIGHT_WRIST.value]
                hands_aligned = abs(left_wrist.y - right_wrist.y) < WRIST_Y_DIFF_THRESHOLD

                # (e) Reach forward
                # Use the wrist further from the ankle (horizontal distance)
                left_reach = abs(left_wrist.x - left_ankle.x)
                right_reach = abs(right_wrist.x - right_ankle.x)
                reach_px = max(left_reach, right_reach) * w  # convert normalized to pixels

                # (f) Hold duration
                valid_pose = legs_straight and feet_stable and hip_down and hands_aligned

                if valid_pose:
                    if last_valid_reach is not None and abs(reach_px - last_valid_reach) < 10:
                        hold_frames += 1
                    else:
                        hold_frames = 1
                        last_valid_reach = reach_px
                else:
                    hold_frames = 0
                    last_valid_reach = None

                # Only count if held for required duration
                if hold_frames >= HOLD_DURATION:
                    # Only increment if new max
                    if pixels_per_cm is not None:
                        reach_cm = reach_px / pixels_per_cm
                        if reach_cm > max_reach_cm:
                            max_reach_cm = reach_cm
                            try:
                                requests.post("http://127.0.0.1:5000/increment")
                            except Exception as e:
                                print("Could not update counter:", e)
                    hold_frames = 0  # reset after counting

            # Show the current frame with annotations
            cv2.putText(vis_frame, f"Max Reach: {max_reach_cm:.1f} cm", (30,60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,255,0), 2, cv2.LINE_AA)
            if pixels_per_cm is not None:
                cv2.putText(vis_frame, f"Current Reach: {reach_cm:.1f} cm", (30,100),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255,255,255), 2, cv2.LINE_AA)
            cv2.imshow(WINDOW_NAME, vis_frame)

            # Update reach values on server
            safe_reach_cm = reach_cm if isinstance(reach_cm, (int, float)) and reach_cm is not None else 0.0
            safe_max_reach_cm = max_reach_cm if isinstance(max_reach_cm, (int, float)) and max_reach_cm is not None else -999.0
            try:
                requests.post(
                    "http://127.0.0.1:5000/update_reach",
                    json={"current_reach": float(safe_reach_cm), "max_reach": float(safe_max_reach_cm)}
                )
            except Exception as e:
                print("Could not update reach values:", e)

            key = cv2.waitKey(5)
            if key == ord('q'):
                break
            elif key == ord('c'):
                calibrating = True
                calib_frame = frame.copy()
                cv2.putText(calib_frame, "Calibration mode: Click two points", (50,50),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2, cv2.LINE_AA)
                cv2.imshow(WINDOW_NAME, calib_frame)
            elif key == ord('r'):
                max_reach_cm = -999.0
                with open(OUTPUT_CSV, "w", newline="") as csvfile:
                    csvw = csv.writer(csvfile)
                    csvw.writerow(["timestamp", "reach_px_smoothed", "reach_cm"])
                print("Recorded max reset.")

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()

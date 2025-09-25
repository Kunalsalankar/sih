import cv2
import mediapipe as mp
import numpy as np
import math
import time
import requests

FRAME_WIDTH = 1280
FRAME_HEIGHT = 720
FPS = 30  # set to your camera FPS
PIXELS_PER_CM = 44.0  # calibration factor

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

def calculate_metrics(release, land, pixels_per_cm, fps):
    # Flight time (s)
    flight_time = (land['frame'] - release['frame']) / fps

    # Range in cm
    D_cm = abs(land['x'] - release['x']) / pixels_per_cm

    # Speeds (cm/s) using frame-based Δt
    dt = flight_time if flight_time > 0 else 1e-6
    vx = (land['x'] - release['x']) / pixels_per_cm / dt
    vy = (land['y'] - release['y']) / pixels_per_cm / dt
    v = math.sqrt(vx**2 + vy**2)

    # Release angle (deg)
    theta = math.degrees(math.atan2(vy, vx))

    # Score (rounding rule)
    if D_cm < 100:   # less than 1 m
        score = round(D_cm / 10) * 10
    else:            # 1 m or more
        score = round(D_cm / 50) * 50

    return {
        "flight_time": flight_time,
        "range_cm": D_cm,
        "vx": vx,
        "vy": vy,
        "v": v,
        "angle_deg": theta,
        "score": score
    }

def main():
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    WINDOW_NAME = "Medicine Ball Throw (press 'q' to quit, 'r' to reset)"
    cv2.namedWindow(WINDOW_NAME)

    release = None
    land = None
    throw_detected = False
    frame_count = 0

    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(frame_rgb)
            vis_frame = frame.copy()
            h, w = frame.shape[:2]

            if results.pose_landmarks:
                lm = results.pose_landmarks.landmark
                wrist = lm[mp_pose.PoseLandmark.RIGHT_WRIST.value]
                wrist_x = wrist.x * w
                wrist_y = wrist.y * h

                # Release detection
                if not throw_detected and wrist_x > w * 0.7:
                    release = {
                        "frame": frame_count,
                        "x": wrist_x,
                        "y": wrist_y,
                    }
                    throw_detected = True
                    print("Release detected!")

                # Landing detection
                if throw_detected and wrist_x < w * 0.3:
                    land = {
                        "frame": frame_count,
                        "x": wrist_x,
                        "y": wrist_y,
                    }
                    print("Landing detected!")

            # Calculate metrics once per throw
            if release and land:
                metrics = calculate_metrics(release, land, PIXELS_PER_CM, FPS)

                # Send to Flask API
                try:
                    requests.post("http://127.0.0.1:5000/increment", json=metrics)
                except:
                    print("⚠ Could not connect to Flask server.")

                # Display on screen
                y0 = 60
                for k, v in metrics.items():
                    cv2.putText(vis_frame, f"{k}: {v:.2f}", (30, y0),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
                    y0 += 40

                # Reset after one throw
                release, land = None, None
                throw_detected = False

            cv2.imshow(WINDOW_NAME, vis_frame)
            key = cv2.waitKey(5)
            if key == ord('q'):
                break
            elif key == ord('r'):
                release, land = None, None
                throw_detected = False

            frame_count += 1

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
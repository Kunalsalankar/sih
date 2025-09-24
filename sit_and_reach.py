import cv2
import mediapipe as mp
import numpy as np
import csv
import requests

OUTPUT_CSV = "broad_jump_results.csv"
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

PIXELS_PER_CM = 44.0  # Set from calibration

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Camera could not be opened.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    WINDOW_NAME = "Broad Jump Counter (press 'q' to quit, 'r' to reset, 's' to set take-off)"
    cv2.namedWindow(WINDOW_NAME)

    csvfile = open(OUTPUT_CSV, "w", newline="")
    csvw = csv.writer(csvfile)
    csvw.writerow(["timestamp", "jump_distance_cm"])

    takeoff_x = None
    landing_x = None
    jump_distance_cm = 0.0
    jump_count = 0
    in_air = False

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

            if results.pose_landmarks:
                mp_drawing.draw_landmarks(vis_frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
                lm = results.pose_landmarks.landmark

                # Use left and right ankles for measurement
                left_ankle = lm[mp_pose.PoseLandmark.LEFT_ANKLE.value]
                right_ankle = lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value]
                ankles_x = [left_ankle.x * w, right_ankle.x * w]

                # 1. Set take-off line (when standing still, press 's')
                if takeoff_x is None:
                    cv2.putText(vis_frame, "Stand at take-off line and press 's'", (30,100),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 2, cv2.LINE_AA)
                else:
                    # 2. Detect landing (ankles move forward, then stop)
                    if not in_air and min(ankles_x) > takeoff_x + 30:
                        in_air = True
                        landing_x = min(ankles_x)
                    elif in_air and min(ankles_x) <= landing_x:
                        # Landed and stopped moving forward
                        jump_distance_px = landing_x - takeoff_x
                        jump_distance_cm = jump_distance_px / PIXELS_PER_CM
                        jump_count += 1
                        print(f"Jump {jump_count}: {jump_distance_cm:.2f} cm")
                        try:
                            requests.post("http://127.0.0.1:5000/increment", json={"jump_height": jump_distance_cm})
                        except Exception as e:
                            print("Could not update counter:", e)
                        in_air = False
                        takeoff_x = None  # Reset for next jump

            # Show info
            cv2.putText(vis_frame, f"Jumps: {jump_count}", (30,60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,255,0), 2, cv2.LINE_AA)
            cv2.putText(vis_frame, f"Last Jump Distance: {jump_distance_cm:.2f} cm", (30,120),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2, cv2.LINE_AA)
            cv2.imshow(WINDOW_NAME, vis_frame)

            key = cv2.waitKey(5)
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Set take-off line
                if results.pose_landmarks:
                    left_ankle = lm[mp_pose.PoseLandmark.LEFT_ANKLE.value]
                    right_ankle = lm[mp_pose.PoseLandmark.RIGHT_ANKLE.value]
                    takeoff_x = min(left_ankle.x * w, right_ankle.x * w)
                    print(f"Take-off line set at x={takeoff_x:.2f} px")
            elif key == ord('r'):
                jump_count = 0
                jump_distance_cm = 0.0
                takeoff_x = None

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
import cv2
import mediapipe as mp
import numpy as np
import csv
import requests

OUTPUT_CSV = "jump_results.csv"
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Camera could not be opened.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    WINDOW_NAME = "Vertical Jump Counter (press 'q' to quit, 'r' to reset)"
    cv2.namedWindow(WINDOW_NAME)

    csvfile = open(OUTPUT_CSV, "w", newline="")
    csvw = csv.writer(csvfile)
    csvw.writerow(["timestamp", "jump_height_cm"])

    # Calibration: pixels_per_cm (set this after calibration, e.g. using wall marks)
    pixels_per_cm = 44.0  # <-- Set this from your calibration step

    standing_reach_y = None
    peak_jump_y = None
    jump_height_cm = 0.0
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

                # Use right wrist for fingertip height (can use left or average)
                wrist = lm[mp_pose.PoseLandmark.RIGHT_WRIST.value]
                wrist_y_px = wrist.y * h

                # 1. Set standing reach (when user is standing still)
                if standing_reach_y is None:
                    cv2.putText(vis_frame, "Stand still and press 's' to set reach", (30,100),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,0,255), 2, cv2.LINE_AA)

                # 2. Detect jump (wrist rises above threshold)
                if standing_reach_y is not None:
                    if wrist_y_px < standing_reach_y - 30:  # Jump detected (hand goes up)
                        if not in_air:
                            in_air = True
                            peak_jump_y = wrist_y_px
                        else:
                            peak_jump_y = min(peak_jump_y, wrist_y_px)
                    else:
                        if in_air:
                            # Jump finished, calculate height
                            jump_height_px = standing_reach_y - peak_jump_y
                            jump_height_cm = jump_height_px / pixels_per_cm
                            jump_count += 1
                            print(f"Jump {jump_count}: {jump_height_cm:.2f} cm")
                            try:
                                requests.post("http://127.0.0.1:5000/increment", json={"jump_height": jump_height_cm})
                            except Exception as e:
                                print("Could not update counter:", e)
                            in_air = False

            # Show info
            cv2.putText(vis_frame, f"Jumps: {jump_count}", (30,60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,255,0), 2, cv2.LINE_AA)
            cv2.putText(vis_frame, f"Last Jump Height: {jump_height_cm:.2f} cm", (30,120),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0,255,0), 2, cv2.LINE_AA)
            cv2.imshow(WINDOW_NAME, vis_frame)

            key = cv2.waitKey(5)
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Set standing reach
                if results.pose_landmarks:
                    wrist = lm[mp_pose.PoseLandmark.RIGHT_WRIST.value]
                    standing_reach_y = wrist.y * h
                    print(f"Standing reach set at y={standing_reach_y:.2f} px")
            elif key == ord('r'):
                jump_count = 0
                jump_height_cm = 0.0

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
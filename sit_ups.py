import cv2
import mediapipe as mp
import numpy as np
import csv
import requests

OUTPUT_CSV = "situp_results.csv"
FRAME_WIDTH = 1280
FRAME_HEIGHT = 720

mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

def angle(a, b, c):
    ba = np.array([a.x - b.x, a.y - b.y])
    bc = np.array([c.x - b.x, c.y - b.y])
    cosine_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    return np.degrees(np.arccos(np.clip(cosine_angle, -1.0, 1.0)))

def main():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Camera could not be opened.")
        return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)

    WINDOW_NAME = "Sit-up Counter (press 'q' to quit)"
    cv2.namedWindow(WINDOW_NAME)

    csvfile = open(OUTPUT_CSV, "w", newline="")
    csvw = csv.writer(csvfile)
    csvw.writerow(["timestamp", "rep_count"])

    rep_count = 0
    phase = "down"

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

                left_shoulder = lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value]
                left_hip = lm[mp_pose.PoseLandmark.LEFT_HIP.value]
                left_knee = lm[mp_pose.PoseLandmark.LEFT_KNEE.value]

                # Sit-up logic:
                # Down phase: shoulder near ground, angle ~180°
                # Up phase: shoulder rises, angle ≤ 100°
                sh_hip_knee_angle = angle(left_shoulder, left_hip, left_knee)
                shoulder_y = left_shoulder.y

                DOWN_ANGLE = 160
                UP_ANGLE = 100
                SHOULDER_GROUND_Y = 0.85  # Adjust based on camera setup
                SHOULDER_UP_Y = 0.6       # Adjust based on camera setup

                if phase == "down":
                    if sh_hip_knee_angle < UP_ANGLE and shoulder_y < SHOULDER_UP_Y:
                        phase = "up"
                elif phase == "up":
                    if sh_hip_knee_angle > DOWN_ANGLE and shoulder_y > SHOULDER_GROUND_Y:
                        rep_count += 1
                        phase = "down"
                        print(f"Sit-up rep counted! Total: {rep_count}")
                        try:
                            requests.post("http://127.0.0.1:5000/increment")
                        except Exception as e:
                            print("Could not update counter:", e)

            cv2.putText(vis_frame, f"Sit-ups: {rep_count}", (30,60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0,255,0), 2, cv2.LINE_AA)
            cv2.imshow(WINDOW_NAME, vis_frame)

            key = cv2.waitKey(5)
            if key == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
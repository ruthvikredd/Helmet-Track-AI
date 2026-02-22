from ultralytics import YOLO
import cv2
import time
import numpy as np
from db_connection import get_connection
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Load both models
pb_model = YOLO("yolov8n.pt")  # person + bike detection
helmet_model = YOLO(
    os.path.join(BASE_DIR, "..", "yolov8", "best.pt")
)  # helmet detection

VIOLATION_FOLDER = os.path.join(BASE_DIR, "..", "static", "violations")
os.makedirs(VIOLATION_FOLDER, exist_ok=True)


def _xyxy_from_box(box):
    try:
        coords = box.xyxy[0].cpu().numpy()
    except Exception:
        coords = box.xyxy[0].numpy()
    return [float(c) for c in coords]


def run_camera_detection():
    cap = cv2.VideoCapture(0)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Person + Bike detection
        pb_results = pb_model(frame)
        # Helmet detection
        helmet_results = helmet_model(frame)

        persons = []
        bikes = []
        no_helmets = []

        # ================================
        # PERSON + BIKE DETECTION (yolov8n)
        # ================================
        for box in pb_results[0].boxes:
            cls = int(box.cls[0])
            label = pb_model.names[cls].lower()
            conf = float(box.conf[0])
            xyxy = _xyxy_from_box(box)
            x1, y1, x2, y2 = [int(v) for v in xyxy]

            if "person" in label:
                persons.append({"xy": (x1, y1, x2, y2), "conf": conf})
            elif any(
                k in label for k in ("motorbike", "motorcycle", "bicycle", "bike")
            ):
                bikes.append({"xy": (x1, y1, x2, y2), "conf": conf})

        # ================================
        # HELMET DETECTION (best.pt)
        # ================================
        for box in helmet_results[0].boxes:
            cls = int(box.cls[0])
            label = helmet_model.names[cls].lower()
            conf = float(box.conf[0])
            xyxy = _xyxy_from_box(box)
            x1, y1, x2, y2 = [int(v) for v in xyxy]

            if "without helmet" in label or "no helmet" in label:
                no_helmets.append({"xy": (x1, y1, x2, y2), "conf": conf})

        # Draw bikes (red)
        for b in bikes:
            bx1, by1, bx2, by2 = b["xy"]
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), (0, 0, 255), 2)
            cv2.putText(
                frame,
                "BIKE",
                (bx1, by1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 0, 255),
                2,
            )

        # Draw persons (cyan)
        for p in persons:
            px1, py1, px2, py2 = p["xy"]
            cv2.rectangle(frame, (px1, py1), (px2, py2), (255, 255, 0), 2)
            cv2.putText(
                frame,
                "PERSON",
                (px1, py1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 0),
                2,
            )

        # Draw no-helmet detections (red)
        for nh in no_helmets:
            nhx1, nhy1, nhx2, nhy2 = nh["xy"]
            cv2.rectangle(frame, (nhx1, nhy1), (nhx2, nhy2), (0, 0, 255), 3)
            cv2.putText(
                frame,
                "NO HELMET",
                (nhx1, nhy1 - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )
            nh_cx = (nhx1 + nhx2) // 2
            nh_cy = (nhy1 + nhy2) // 2

            # Check if no-helmet person is in a bike
            for p in persons:
                px1, py1, px2, py2 = p["xy"]
                person_cx = (px1 + px2) // 2
                person_cy = (py1 + py2) // 2

                # Check if person overlaps with no-helmet detection
                if px1 <= nh_cx <= px2 and py1 <= nh_cy <= py2:
                    # Check if person is riding a bike
                    riding = False
                    for b in bikes:
                        bx1, by1, bx2, by2 = b["xy"]
                        if bx1 <= person_cx <= bx2 and by1 <= person_cy <= by2:
                            riding = True
                            break

                    # HELMET VIOLATION: Person riding bike without helmet
                    if riding and p["conf"] > 0.5:
                        from notification_email import send_violation_email
                        from datetime import datetime

                        # Draw violation label on the frame
                        cv2.putText(
                            frame,
                            "VIOLATION DETECTED",
                            (50, 50),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            1.5,
                            (0, 0, 255),
                            3,
                        )

                        timestamp = int(time.time())
                        violation_filename = f"violation_{timestamp}.jpg"
                        path = os.path.join(VIOLATION_FOLDER, violation_filename)
                        cv2.imwrite(path, frame)
                        try:
                            conn = get_connection()
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO no_helmet_records (image_name, original_image, violation_image, fine_amount, timestamp) VALUES (%s, %s, %s, %s, NOW())",
                                (
                                    violation_filename,
                                    violation_filename,
                                    violation_filename,
                                    500,
                                ),
                            )
                            conn.commit()

                            # Send email notification
                            admin_email = os.environ.get(
                                "ADMIN_EMAIL", "22r91a1235@tkrec.ac.in"
                            )
                            violation_details = {
                                "timestamp": datetime.now().strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                "fine_amount": 500,
                                "image": violation_filename,
                            }
                            send_violation_email(admin_email, violation_details)
                        except Exception as e:
                            print("DB insert error in realtime detection:", e)
                        finally:
                            try:
                                cursor.close()
                            except:
                                pass
                            try:
                                conn.close()
                            except:
                                pass
                        pass
                    try:
                        conn.close()
                    except:
                        pass

        cv2.imshow("Helmet & Bike Detection", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

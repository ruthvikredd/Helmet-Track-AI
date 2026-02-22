from flask import Flask, render_template, request, redirect, session
from db_connection import get_connection
from detection.realtime import run_camera_detection
from detection.video_detect import detect_video
from notification import validate_phone_number
from notification_email import send_violation_email
from ultralytics import YOLO
import os
import cv2
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = "helmettrack_secret"

# -------------------------
# ADMIN EMAIL CONFIGURATION
# -------------------------
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "22r91a1235@tkrec.ac.in")
SEND_EMAIL_ENABLED = os.environ.get("SEND_EMAIL_ENABLED", "True").lower() == "true"

# -------------------------
# DIRECTORIES
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
VIOLATION_FOLDER = os.path.join(BASE_DIR, "static", "violations")

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(VIOLATION_FOLDER, exist_ok=True)

# -------------------------
# ROUTES
# -------------------------


@app.route("/")
def login_page():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM admin WHERE username=%s AND password=%s", (username, password)
    )
    admin = cursor.fetchone()

    if admin:
        session["admin"] = username
        return redirect("/dashboard")
    return "Invalid Credentials"


@app.route("/dashboard")
def dashboard():
    if "admin" not in session:
        return redirect("/")
    return render_template("dashboard.html")


# -------------------------
# ADD USER
# -------------------------
@app.route("/add_user", methods=["GET", "POST"])
def add_user():
    if "admin" not in session:
        return redirect("/")

    if request.method == "POST":
        name = request.form["name"]
        aadhar = request.form["aadhar"]
        phone_number = request.form.get("phone_number", "").strip()
        photo = request.files["photo"]

        # Validate phone number
        is_valid, formatted_phone = validate_phone_number(phone_number)
        if not is_valid:
            return (
                "Invalid phone number format. Please enter a valid Indian phone number.",
                400,
            )

        photo_name = photo.filename
        photo_path = os.path.join(UPLOAD_FOLDER, photo_name)
        photo.save(photo_path)

        conn = get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "INSERT INTO users (name, photo, aadhar_no, phone_number) VALUES (%s, %s, %s, %s)",
                (name, photo_name, aadhar, formatted_phone),
            )
            conn.commit()
            return redirect("/view_users")
        except Exception as e:
            conn.rollback()
            print(f"Database error: {e}")
            return f"Error adding user: {str(e)}", 500
        finally:
            cursor.close()
            conn.close()

    return render_template("add_user.html")


@app.route("/view_users")
def view_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()
    return render_template("view_users.html", users=users)


# -------------------------
# UPLOAD VIDEO
# -------------------------
@app.route("/upload_video", methods=["GET", "POST"])
def upload_video():
    if request.method == "GET":
        return render_template("upload_video.html")

    # POST: process video
    video = request.files["video"]
    save_path = os.path.join(UPLOAD_FOLDER, video.filename)
    video.save(save_path)

    detect_video(save_path)
    return "Video processed successfully!"


# -------------------------
# VIEW VIOLATIONS
# -------------------------
@app.route("/no_helmet_records")
def violations():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        "SELECT id, timestamp, image_name, original_image, violation_image, fine_amount "
        "FROM no_helmet_records ORDER BY timestamp DESC"
    )
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template("no_helmet_records.html", records=data)


# -------------------------
# PREDICTION PAGE
# -------------------------
@app.route("/run_prediction")
def prediction_page():
    return render_template("run_prediction.html")


@app.route("/predict_image", methods=["POST"])
def predict_image():

    img = request.files["image"]
    save_path = os.path.join(UPLOAD_FOLDER, img.filename)
    img.save(save_path)

    # Load models
    pb_model = YOLO("yolov8n.pt")  # person + bike
    helmet_model = YOLO("yolov8/best.pt")  # helmet

    image = cv2.imread(save_path)

    pb_results = pb_model(image)
    helmet_results = helmet_model(image)

    persons = []
    bikes = []
    no_helmets = []

    # -------------------------
    # PERSON + BIKE DETECTION
    # -------------------------
    for box in pb_results[0].boxes:
        cls = int(box.cls[0])
        label = pb_model.names[cls]
        x1, y1, x2, y2 = map(int, box.xyxy[0])

        if label == "person":
            persons.append((x1, y1, x2, y2))
        elif label in ["motorcycle", "bicycle"]:
            bikes.append((x1, y1, x2, y2))

    # -------------------------
    # NO HELMET DETECTION
    # -------------------------
    for box in helmet_results[0].boxes:
        cls = int(box.cls[0])
        label = helmet_model.names[cls].lower()
        conf = float(box.conf[0])

        if "without helmet" in label:
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            no_helmets.append((x1, y1, x2, y2, conf))

    # -------------------------
    # VIOLATION LOGIC
    # -------------------------
    for nhx1, nhy1, nhx2, nhy2, conf in no_helmets:
        nh_cx = (nhx1 + nhx2) // 2
        nh_cy = (nhy1 + nhy2) // 2

        for px1, py1, px2, py2 in persons:
            if px1 <= nh_cx <= px2 and py1 <= nh_cy <= py2:

                person_cx = (px1 + px2) // 2
                person_cy = (py1 + py2) // 2

                for bx1, by1, bx2, by2 in bikes:
                    if bx1 <= person_cx <= bx2 and by1 <= person_cy <= by2:

                        # 🚨 VIOLATION CONFIRMED
                        cv2.rectangle(image, (px1, py1), (px2, py2), (0, 0, 255), 3)
                        cv2.putText(
                            image,
                            "NO HELMET",
                            (px1, py1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.8,
                            (0, 0, 255),
                            2,
                        )

                        viol_name = (
                            f"viol_{datetime.now().strftime('%Y%m%d%H%M%S%f')}.jpg"
                        )
                        viol_path = os.path.join(VIOLATION_FOLDER, viol_name)
                        cv2.imwrite(viol_path, image)

                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO no_helmet_records "
                            "(image_name, original_image, violation_image, fine_amount, timestamp) "
                            "VALUES (%s, %s, %s, %s, NOW())",
                            (img.filename, img.filename, viol_name, 500),
                        )
                        conn.commit()
                        cursor.close()
                        conn.close()

                        # Send email notification
                        violation_details = {
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "fine_amount": 500,
                            "image": viol_name,
                        }
                        send_violation_email(ADMIN_EMAIL, violation_details)

    output_path = os.path.join(UPLOAD_FOLDER, "output.jpg")
    cv2.imwrite(output_path, image)

    return render_template("show_result.html", image="output.jpg")


# -------------------------
# RUN CAMERA
# -------------------------
@app.route("/start_camera")
def start_camera():
    run_camera_detection()
    return "Camera closed"


# -------------------------
# LOGOUT
# -------------------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# -------------------------
# RUN APP
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)

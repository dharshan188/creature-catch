from threading import Lock, Thread
import os
import time
from datetime import datetime

import cv2
from flask import Flask, Response, jsonify, request
import requests
from dotenv import load_dotenv

try:
    from ultralytics import YOLO
    from twilio.rest import Client
    from twilio.twiml.voice_response import VoiceResponse, Gather
except ImportError as exc:
    raise ImportError(
        "Install dependencies with: pip install flask ultralytics opencv-python python-dotenv requests twilio"
    ) from exc


load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
print("BOT_TOKEN:", BOT_TOKEN)
print("CHAT_ID:", CHAT_ID)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
USER_PHONE_NUMBER = os.getenv("USER_PHONE_NUMBER")
SERVER_URL = os.getenv("SERVER_URL", "http://localhost:5000")
print("TWILIO_ACCOUNT_SID:", TWILIO_ACCOUNT_SID)
print("USER_PHONE_NUMBER:", USER_PHONE_NUMBER)

ALERTS_DIR = "alerts"
os.makedirs(ALERTS_DIR, exist_ok=True)
STABLE_DETECTION_SECONDS = 3
NO_DETECTION_RESET_SECONDS = 2
MODEL_INPUT_SIZE = (640, 480)


app = Flask(__name__)

WATCH_CLASSES = {"person", "elephant", "bear", "giraffe"}
STATUS_BY_CLASS = {
    "person": "Human Detected",
    "elephant": "Elephant Detected",
    "bear": "Bear Detected",
    "giraffe": "Giraffe Detected",
}
ALERT_LABEL_BY_CLASS = {
    "person": "HUMAN",
    "elephant": "ELEPHANT",
    "bear": "BEAR",
    "giraffe": "GIRAFFE",
}

current_status = "Nothing Detected"
status_lock = Lock()
alert_lock = Lock()
tracking_lock = Lock()
current_label = None
first_seen_time = None
last_confirmed_label = None
last_detection_time = 0.0

model = YOLO("yolov8n.pt")
camera = cv2.VideoCapture(0, cv2.CAP_V4L2)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)


def send_telegram_alert(image_path, label, conf):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram error:", "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    caption = f"🚨 Intrusion Detected!\nType: {label.upper()}\nConfidence: {conf:.2f}"
    print("📤 API CALL START")
    print("Token:", BOT_TOKEN)
    print("Chat ID:", CHAT_ID)

    try:
        with open(image_path, "rb") as image_file:
            response = requests.post(
                url,
                files={"photo": image_file},
                data={"chat_id": CHAT_ID, "caption": caption},
                timeout=10,
            )
        print("Response:", response.status_code, response.text)
        response.raise_for_status()
        return True
    except Exception as exc:
        print("Telegram error:", exc)
        return False


def make_call():
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER or not USER_PHONE_NUMBER:
        print("Twilio error: Missing Twilio credentials")
        return False

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        call = client.calls.create(
            to=USER_PHONE_NUMBER,
            from_=TWILIO_PHONE_NUMBER,
            url=f"{SERVER_URL}/voice",
        )
        print("📞 CALL INITIATED:", call.sid)
        return True
    except Exception as exc:
        print("Twilio error:", exc)
        return False


def delayed_call():
    time.sleep(10)
    print("⏰ INITIATING VOICE CALL AFTER 10 SECONDS")
    make_call()


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    return response


def generate_frames():
    global current_status, current_label, first_seen_time, last_confirmed_label, last_detection_time

    if not camera.isOpened():
        raise RuntimeError("Cannot open camera 0")

    while True:
        ok, frame = camera.read()
        if not ok:
            continue

        frame = cv2.resize(frame, MODEL_INPUT_SIZE)
        results = model(frame, conf=0.5, iou=0.5, verbose=False)[0]
        frame_status = "Nothing Detected"
        now = time.time()

        detected_label = None
        detected_confidence = 0.0
        detected_box = None

        for box in results.boxes:
            class_name = model.names[int(box.cls[0])]
            if class_name not in WATCH_CLASSES:
                continue

            confidence = float(box.conf[0])
            if confidence > detected_confidence:
                detected_label = class_name
                detected_confidence = confidence
                detected_box = tuple(map(int, box.xyxy[0]))

        confirmed_label = None
        stable_for = 0.0

        with tracking_lock:
            if detected_label is not None:
                last_detection_time = now

                if detected_label != current_label:
                    current_label = detected_label
                    first_seen_time = now

                stable_for = now - first_seen_time if first_seen_time is not None else 0.0
                if stable_for >= STABLE_DETECTION_SECONDS:
                    confirmed_label = current_label
            else:
                if (
                    current_label is not None
                    and now - last_detection_time > NO_DETECTION_RESET_SECONDS
                ):
                    current_label = None
                    first_seen_time = None

        print("Tracking:", current_label)
        print("Stable for:", stable_for)
        print("Confirmed:", confirmed_label)

        if detected_label is not None and detected_box is not None:
            print("DETECTED:", detected_label, detected_confidence)

            x1, y1, x2, y2 = detected_box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 190, 255), 2)
            cv2.putText(
                frame,
                f"{detected_label.upper()} {detected_confidence * 100:.0f}%",
                (x1, max(y1 - 8, 16)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 190, 255),
                2,
            )

        if confirmed_label is not None:
            frame_status = STATUS_BY_CLASS[confirmed_label]
        elif current_label is not None:
            frame_status = f"Tracking {current_label.upper()}"

        candidate_alert_label = None
        with alert_lock:
            if confirmed_label is not None and confirmed_label != last_confirmed_label:
                candidate_alert_label = confirmed_label

        if candidate_alert_label is not None:
            mapped_label = ALERT_LABEL_BY_CLASS.get(candidate_alert_label, candidate_alert_label.upper())
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{ALERTS_DIR}/{mapped_label}_{timestamp}.jpg"

            try:
                print("🔥 ALERT TRIGGERED")
                print("📸 Saving image:", filename)
                saved = cv2.imwrite(filename, frame)
                if not saved:
                    print("Failed to save alert image:", filename)
                else:
                    print("Sending to Telegram:", filename)
                    sent_ok = send_telegram_alert(filename, mapped_label, detected_confidence)
                    if sent_ok:
                        with alert_lock:
                            last_confirmed_label = candidate_alert_label
                        print("📞 SPAWNING DELAYED CALL THREAD")
                        call_thread = Thread(target=delayed_call, daemon=True)
                        call_thread.start()
            except Exception as exc:
                print("Alert processing failed:", exc)

        with status_lock:
            current_status = frame_status

        encoded_ok, buffer = cv2.imencode(".jpg", frame)
        if not encoded_ok:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
        )


@app.route("/video_feed")
def video_feed():
    return Response(generate_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/status")
def status():
    with status_lock:
        return jsonify({"status": current_status})


@app.route("/voice", methods=["GET", "POST"])
def voice():
    response = VoiceResponse()
    gather = Gather(num_digits=1, action="/handle-key")
    gather.say(
        "Intrusion detected at your location. We have sent a picture to your phone. "
        "If the situation seems suspicious and you would like to escalate this alert, press 4."
    )
    response.append(gather)
    print("🎙️ VOICE ROUTE CALLED - PLAYING MESSAGE")
    return str(response)


@app.route("/handle-key", methods=["POST"])
def handle_key():
    digit = request.form.get("Digits")
    print("🎛️ USER PRESSED KEY:", digit)
    if digit == "4":
        print("🚨 USER CONFIRMED INTRUSION - ESCALATING ALERT!")
    return "OK"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
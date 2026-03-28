import cv2
import time
import argparse
from datetime import datetime

try:
    from ultralytics import YOLO
except ImportError:
    print("ERROR: Run this first ->  pip install ultralytics opencv-python")
    exit(1)

# ── Configuration ─────────────────────────────────────────────
CONF_THRESHOLD = 0.5
CAMERA_INDEX   = 2

# 🔥 UPDATED CLASSES
WATCH_CLASSES = {"person", "elephant", "bear", "giraffe"}

# 🎨 UPDATED STYLE
CLASS_STYLE = {
    "person":   {"color": (30,  40, 220), "tag": "HUMAN"},
    "elephant": {"color": (0,  145, 255), "tag": "ELEPHANT"},
    "bear":     {"color": (80,  70, 180), "tag": "BEAR"},
    "giraffe":  {"color": (0,  200, 200), "tag": "GIRAFFE"},
}
DEFAULT_STYLE = {"color": (200, 200, 0), "tag": "UNKNOWN"}

# ── Args ─────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="FarmGuard detection test")
parser.add_argument("--model",  default="yolov8n.pt")
parser.add_argument("--conf",   type=float, default=CONF_THRESHOLD)
parser.add_argument("--camera", type=int,   default=CAMERA_INDEX)
args = parser.parse_args()

# ── Load model ───────────────────────────────────────────────
print(f"\n[INFO] Loading model : {args.model}")
model = YOLO(args.model)
print(f"[INFO] Watching for  : {WATCH_CLASSES}")
print("[INFO] Press Q to quit\n")

# ── Open webcam ──────────────────────────────────────────────
cap = cv2.VideoCapture(args.camera)

if not cap.isOpened():
    print(f"ERROR: Cannot open camera {args.camera}")
    exit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

fps_time    = time.time()
fps         = 0.0
frame_count = 0

# ── Main loop ────────────────────────────────────────────────
while True:
    ret, frame = cap.read()
    if not ret:
        time.sleep(0.05)
        continue

    # 🔥 IMPROVED INFERENCE (LESS DUPLICATES)
    results    = model(frame, conf=0.5, iou=0.5, verbose=False)[0]
    detections = []

    for box in results.boxes:
        conf  = float(box.conf[0])
        label = model.names[int(box.cls[0])]

        if label not in WATCH_CLASSES:
            continue

        x1, y1, x2, y2 = map(int, box.xyxy[0])
        detections.append((label, conf, x1, y1, x2, y2))

    # ── Draw boxes ───────────────────────────────────────────
    for label, conf, x1, y1, x2, y2 in detections:
        style = CLASS_STYLE.get(label, DEFAULT_STYLE)
        color = style["color"]
        tag   = style["tag"]

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

        text = f"{tag} {conf*100:.0f}%"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.65, 2)
        cv2.rectangle(frame, (x1, y1 - th - 12), (x1 + tw + 8, y1), color, -1)
        cv2.putText(frame, text, (x1 + 4, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)

        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {tag:<10} conf={conf:.2f}")

    # ── HUD ─────────────────────────────────────────────────
    frame_count += 1
    if frame_count % 15 == 0:
        fps      = 15 / (time.time() - fps_time + 1e-9)
        fps_time = time.time()

    if detections:
        names        = ", ".join(sorted(set(d[0].upper() for d in detections)))
        status_text  = f"ALERT: {names}"
        status_color = (0, 0, 255)
    else:
        status_text  = "Monitoring..."
        status_color = (0, 180, 60)

    cv2.rectangle(frame, (0, 0), (640, 36), (10, 10, 10), -1)
    cv2.putText(frame, f"FarmGuard | {status_text}",
                (8, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.65, status_color, 2)

    cv2.putText(frame, f"FPS:{fps:.1f}",
                (450, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (130, 130, 130), 1)

    # ── Display ─────────────────────────────────────────────
    cv2.imshow("FarmGuard Detection (Q to quit)", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

# ── Cleanup ─────────────────────────────────────────────────
cap.release()
cv2.destroyAllWindows()

print("\n[INFO] Detector stopped.")
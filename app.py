from threading import Lock, Thread
import threading
import os
import time
import json
import csv
from datetime import datetime
import smtplib
from email.message import EmailMessage

import cv2
from flask import Flask, Response, abort, jsonify, request, send_file
import requests
from dotenv import load_dotenv
from news_fetcher import fetch_news
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus
from urllib.request import urlopen

try:
    from ultralytics import YOLO
    from twilio.rest import Client
    from twilio.twiml.voice_response import VoiceResponse, Gather
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
except ImportError as exc:
    raise ImportError(
        "Install dependencies with: pip install flask ultralytics opencv-python python-dotenv requests twilio reportlab"
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
BASE_URL = os.getenv("BASE_URL")
if BASE_URL:
    BASE_URL = BASE_URL.rstrip("/")
if not BASE_URL or "localhost" in BASE_URL or not BASE_URL.startswith("https://"):
    raise ValueError("BASE_URL must be a public ngrok HTTPS URL")
FOREST_OFFICER_NUMBER = os.getenv("FOREST_OFFICER_NUMBER")

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")
print("TWILIO_ACCOUNT_SID:", TWILIO_ACCOUNT_SID)
print("USER_PHONE_NUMBER:", USER_PHONE_NUMBER)
print("EMAIL:", EMAIL_SENDER)
print("EMAIL_SENDER:", EMAIL_SENDER)
print("EMAIL_PASSWORD:", EMAIL_PASSWORD)
print("EMAIL_RECEIVER:", EMAIL_RECEIVER)
print("FOREST:", FOREST_OFFICER_NUMBER)
print("Using BASE_URL:", BASE_URL)

ALERTS_DIR = "alerts"
os.makedirs(ALERTS_DIR, exist_ok=True)
REPORTS_DIR = "reports"
EVENTS_JSON_PATH = os.path.join(REPORTS_DIR, "events.json")
EVENTS_CSV_PATH = os.path.join(REPORTS_DIR, "events.csv")
DATA_DIR = "data"
NEWS_JSON_PATH = os.path.join(DATA_DIR, "news.json")
NEWS_CONFIG_PATH = os.path.join(DATA_DIR, "news_config.json")
LOCATION_NAME = "Nelambur"
DEFAULT_NEWS_CITY = os.getenv("NEWS_CITY", LOCATION_NAME)
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
reports_lock = Lock()
news_lock = Lock()
news_refresh_lock = Lock()
news_refreshing_cities = set()
sent_alert_titles = set()
current_label = None
first_seen_time = None
last_confirmed_label = None
last_detection_time = 0.0
last_image_path = None
last_label = None
last_event_id = None

model = YOLO("yolov8n.pt")
camera = cv2.VideoCapture(2, cv2.CAP_V4L2)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)


def ensure_report_storage():
    os.makedirs(REPORTS_DIR, exist_ok=True)

    if not os.path.exists(EVENTS_JSON_PATH):
        try:
            with open(EVENTS_JSON_PATH, "w", encoding="utf-8") as events_file:
                json.dump([], events_file, indent=2)
        except OSError as exc:
            print("Report storage error:", exc)


def ensure_news_storage():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(NEWS_JSON_PATH):
        try:
            with open(NEWS_JSON_PATH, "w", encoding="utf-8") as news_file:
                json.dump([], news_file, indent=2)
        except OSError as exc:
            print("News storage error:", exc)

    if not os.path.exists(NEWS_CONFIG_PATH):
        try:
            with open(NEWS_CONFIG_PATH, "w", encoding="utf-8") as config_file:
                json.dump({"city": DEFAULT_NEWS_CITY}, config_file, indent=2)
        except OSError as exc:
            print("News config storage error:", exc)


def fetch_intrusion_news(city: str) -> list[dict[str, str]]:
    """
    Fetch intrusion-related news from Google News RSS with strict filtering.
    Apply multi-level keyword filters to remove noise and keep only real intrusion events.
    """
    city_clean = (city or "").strip()
    if not city_clean:
        return []

    animal_keywords = ["elephant", "leopard", "tiger"]
    strong_action_keywords = ["spotted", "roaming", "entered", "strayed", "seen"]
    place_keywords = ["village", "road", "area", "near"]
    medium_action_keywords = ["attack", "injured", "killed", "enters", "menace"]

    # Negative context keywords (remove articles with any of these)
    negative_context = [
        "election", "boycott", "policy", "scheme", "analysis", "report", "victim", "compensation"
    ]

    query = f"{city_clean} wildlife OR elephant OR leopard OR tiger OR intrusion"
    rss_url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-IN&gl=IN&ceid=IN:en"

    strong = []
    medium = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        response = urlopen(rss_url, timeout=5)
        rss_data = response.read()
        root = ET.fromstring(rss_data)

        for item in root.findall(".//item")[:15]:
            title_elem = item.find("title")
            link_elem = item.find("link")
            title = title_elem.text if title_elem is not None else ""
            link = link_elem.text if link_elem is not None else ""

            if not title or not link:
                continue

            t = title.lower()

            # ❌ Reject: Negative context (political, generic, etc.)
            if any(word in t for word in negative_context):
                continue

            # ✅ Strong intrusion detection: animal + action + place
            has_animal = any(animal in t for animal in animal_keywords)
            has_action = any(action in t for action in strong_action_keywords)
            has_place = any(place in t for place in place_keywords)

            if has_animal and has_action and has_place:
                strong.append(
                    {
                        "title": title,
                        "link": link,
                        "city": city_clean,
                        "time": now,
                    }
                )
                continue

            # ✅ Medium intrusion detection: incident terms + place context, excluding opinion/debate noise
            if (
                has_animal
                and any(k in t for k in medium_action_keywords)
                and any(context in t for context in [
                    "village", "area", "near", "forest", "district", "campus"
                ])
                and not any(bad in t for bad in [
                    "call to", "demand", "discussion", "debate", "rename", "nickname"
                ])
            ):
                medium.append(
                    {
                        "title": title,
                        "link": link,
                        "city": city_clean,
                        "time": now,
                    }
                )

    except Exception as exc:
        print(f"❌ RSS fetch error for {city_clean}: {exc}")

    alerts = strong[:3] if strong else medium[:3]
    print(f"📰 Filtered intrusion alerts for {city_clean}: {len(alerts)} found")

    return alerts


def send_telegram_intrusion_alert(alert: dict[str, str]) -> bool:
    """
    Send intrusion alert via Telegram.
    """
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram error: Missing BOT_TOKEN or CHAT_ID")
        return False

    title = alert.get("title", "Unknown Alert")
    city = alert.get("city", "Unknown Location")
    link = alert.get("link", "#")

    message = f"""🚨 Intrusion Alert!
📍 Location: {city}
📰 {title}
🔗 {link}"""

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}

    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
        print(f"✅ Telegram alert sent for {city}")
        return True
    except Exception as exc:
        print(f"❌ Telegram error: {exc}")
        return False


def write_events_csv(events):
    csv_headers = [
        "event_id",
        "timestamp",
        "type",
        "confidence",
        "image_path",
        "location",
        "telegram_sent",
        "call_made",
        "user_response",
        "email_sent",
        "forest_notified",
        "report_file",
    ]

    try:
        with open(EVENTS_CSV_PATH, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=csv_headers)
            writer.writeheader()
            for event in events:
                writer.writerow({key: event.get(key, "") for key in csv_headers})
    except OSError as exc:
        print("CSV write error:", exc)


def load_events():
    ensure_report_storage()
    with reports_lock:
        try:
            with open(EVENTS_JSON_PATH, "r", encoding="utf-8") as events_file:
                events = json.load(events_file)
            if isinstance(events, list):
                return events
            print("Report data warning: events.json did not contain a list. Resetting.")
            return []
        except (OSError, json.JSONDecodeError) as exc:
            print("Report load error:", exc)
            return []


def load_news_city():
    ensure_news_storage()
    with news_lock:
        try:
            with open(NEWS_CONFIG_PATH, "r", encoding="utf-8") as config_file:
                config = json.load(config_file)
            if isinstance(config, dict) and config.get("city"):
                return str(config.get("city"))
        except (OSError, json.JSONDecodeError):
            pass
    return DEFAULT_NEWS_CITY


def save_news_city(city):
    city_name = (city or "").strip()
    if not city_name:
        return False

    ensure_news_storage()
    with news_lock:
        try:
            with open(NEWS_CONFIG_PATH, "w", encoding="utf-8") as config_file:
                json.dump({"city": city_name}, config_file, indent=2)
            return True
        except OSError as exc:
            print("News config save error:", exc)
            return False


def load_news(city=None):
    ensure_news_storage()
    target_city = (city or "").strip().lower()

    with news_lock:
        try:
            with open(NEWS_JSON_PATH, "r", encoding="utf-8") as news_file:
                records = json.load(news_file)
        except (OSError, json.JSONDecodeError) as exc:
            print("News load error:", exc)
            records = []

    if not isinstance(records, list):
        return []

    if not target_city:
        return records

    return [record for record in records if str(record.get("city", "")).strip().lower() == target_city]


def save_news(article):
    ensure_news_storage()
    if not isinstance(article, dict):
        return False

    normalized_article = {
        "city": str(article.get("city", "")).strip(),
        "title": str(article.get("title", "")).strip(),
        "link": str(article.get("link", "")).strip(),
        "time": str(article.get("time", current_time_string())).strip(),
        "published_time": str(article.get("published_time", "")).strip(),
    }

    if not normalized_article["city"] or not normalized_article["title"] or not normalized_article["link"]:
        return False

    with news_lock:
        try:
            with open(NEWS_JSON_PATH, "r", encoding="utf-8") as news_file:
                records = json.load(news_file)
                if not isinstance(records, list):
                    records = []
        except (OSError, json.JSONDecodeError):
            records = []

        exists = any(
            str(item.get("link", "")).strip() == normalized_article["link"]
            and str(item.get("city", "")).strip().lower() == normalized_article["city"].lower()
            for item in records
            if isinstance(item, dict)
        )
        if exists:
            return False

        records.append(normalized_article)
        records.sort(key=lambda item: item.get("time", ""), reverse=True)

        try:
            with open(NEWS_JSON_PATH, "w", encoding="utf-8") as news_file:
                json.dump(records, news_file, indent=2)
            return True
        except OSError as exc:
            print("News save error:", exc)
            return False


def current_time_string():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def generate_report(event):
    timestamp_text = event.get("timestamp", current_time_string())
    filename = event.get("report_file")
    if not filename:
        safe_stamp = str(timestamp_text).replace(":", "-").replace(" ", "_")
        filename = os.path.join(REPORTS_DIR, f"report_{safe_stamp}.pdf")

    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    content = []

    content.append(Paragraph("WILDLIFE INTRUSION REPORT", styles["Title"]))
    content.append(Spacer(1, 12))

    content.append(Paragraph(f"Location: {event.get('location', LOCATION_NAME)}", styles["Normal"]))
    content.append(Paragraph(f"Date & Time: {timestamp_text}", styles["Normal"]))
    content.append(Spacer(1, 10))

    content.append(Paragraph("Detection Details:", styles["Heading2"]))
    content.append(Paragraph(f"Type: {event.get('type', 'UNKNOWN')}", styles["Normal"]))
    content.append(Paragraph(f"Confidence: {event.get('confidence', 0.0)}", styles["Normal"]))
    content.append(Spacer(1, 10))

    try:
        content.append(Paragraph("Image Evidence:", styles["Heading2"]))
        img = Image(event.get("image_path", ""), width=4 * inch, height=3 * inch)
        content.append(img)
    except Exception:
        content.append(Paragraph("Image not available", styles["Normal"]))

    content.append(Spacer(1, 12))

    content.append(Paragraph("Timeline of Events:", styles["Heading2"]))
    timeline = event.get("timeline", {}) or {}
    for key, value in timeline.items():
        timestamp_value = value if value else "Not recorded"
        content.append(Paragraph(f"{timestamp_value} → {key}", styles["Normal"]))

    content.append(Spacer(1, 12))
    content.append(Paragraph("Summary:", styles["Heading2"]))

    authority_status = "Authorities were notified successfully." if event.get("forest_notified") else "Authorities notification is pending."
    summary_text = (
        f"Intrusion of type {event.get('type', 'UNKNOWN')} was detected and processed.<br/>"
        f"User response: {event.get('user_response', 'Pending')}.<br/>"
        f"{authority_status}"
    )
    content.append(Paragraph(summary_text, styles["Normal"]))

    doc.build(content)
    print("📄 Advanced PDF generated:", filename)
    return filename


def write_report_file(event):
    ensure_report_storage()
    report_path = event.get("report_file")
    if not report_path:
        event_timestamp = event.get("timestamp", current_time_string())
        safe_timestamp = str(event_timestamp).replace(":", "-").replace(" ", "_")
        report_path = os.path.join(REPORTS_DIR, f"report_{safe_timestamp}.pdf")
        event["report_file"] = report_path

    try:
        generated_path = generate_report(event)
        print("📄 Report generated:", generated_path)
        return generated_path
    except Exception as exc:
        print("Report write error:", exc)
        return None


def save_event(event_data):
    ensure_report_storage()

    event = {
        "event_id": event_data.get("event_id") or f"EVT-{int(time.time() * 1000)}",
        "timestamp": event_data.get("timestamp", current_time_string()),
        "type": event_data.get("type", "UNKNOWN"),
        "confidence": event_data.get("confidence", 0.0),
        "image_path": event_data.get("image_path", ""),
        "location": event_data.get("location", LOCATION_NAME),
        "telegram_sent": bool(event_data.get("telegram_sent", False)),
        "call_made": bool(event_data.get("call_made", False)),
        "user_response": event_data.get("user_response", "Pending"),
        "email_sent": bool(event_data.get("email_sent", False)),
        "forest_notified": bool(event_data.get("forest_notified", False)),
        "timeline": event_data.get("timeline")
        or {
            "detected": event_data.get("timestamp", current_time_string()),
            "telegram": "",
            "call": "",
            "user_response": "",
            "email": "",
            "forest": "",
        },
        "report_file": event_data.get("report_file"),
    }

    with reports_lock:
        events = []
        try:
            with open(EVENTS_JSON_PATH, "r", encoding="utf-8") as events_file:
                loaded_events = json.load(events_file)
                if isinstance(loaded_events, list):
                    events = loaded_events
        except (OSError, json.JSONDecodeError):
            events = []

        if not event.get("report_file"):
            event_timestamp = event.get("timestamp", current_time_string())
            safe_timestamp = str(event_timestamp).replace(":", "-").replace(" ", "_")
            event["report_file"] = os.path.join(REPORTS_DIR, f"report_{safe_timestamp}.pdf")

        events.append(event)

        try:
            with open(EVENTS_JSON_PATH, "w", encoding="utf-8") as events_file:
                json.dump(events, events_file, indent=2)
        except OSError as exc:
            print("Event save error:", exc)
            return None

        write_events_csv(events)

    write_report_file(event)
    print("📄 Event logged")
    return event


def update_event(event_id, field, value):
    if not event_id:
        return False

    ensure_report_storage()
    updated_event = None

    with reports_lock:
        try:
            with open(EVENTS_JSON_PATH, "r", encoding="utf-8") as events_file:
                events = json.load(events_file)
                if not isinstance(events, list):
                    events = []
        except (OSError, json.JSONDecodeError):
            events = []

        for event in events:
            if event.get("event_id") == event_id:
                event[field] = value
                updated_event = event
                break

        if updated_event is None:
            return False

        try:
            with open(EVENTS_JSON_PATH, "w", encoding="utf-8") as events_file:
                json.dump(events, events_file, indent=2)
        except OSError as exc:
            print("Event update error:", exc)
            return False

        write_events_csv(events)

    write_report_file(updated_event)
    return True


def update_event_timeline(event_id, timeline_field, timestamp_value=None):
    if not event_id:
        return False

    ensure_report_storage()
    updated_event = None

    with reports_lock:
        try:
            with open(EVENTS_JSON_PATH, "r", encoding="utf-8") as events_file:
                events = json.load(events_file)
                if not isinstance(events, list):
                    events = []
        except (OSError, json.JSONDecodeError):
            events = []

        for event in events:
            if event.get("event_id") == event_id:
                timeline = event.get("timeline") or {}
                timeline[timeline_field] = timestamp_value or current_time_string()
                event["timeline"] = timeline
                updated_event = event
                break

        if updated_event is None:
            return False

        try:
            with open(EVENTS_JSON_PATH, "w", encoding="utf-8") as events_file:
                json.dump(events, events_file, indent=2)
        except OSError as exc:
            print("Timeline update error:", exc)
            return False

        write_events_csv(events)

    write_report_file(updated_event)
    return True


def find_latest_pending_event_id():
    events = load_events()
    for event in reversed(events):
        if event.get("user_response") == "Pending":
            return event.get("event_id")
    return None


def build_public_url(path, event_id=None):
    base_url = BASE_URL or ""
    if base_url:
        full_url = f"{base_url.rstrip('/')}{path}"
    else:
        full_url = path

    if event_id:
        separator = "&" if "?" in full_url else "?"
        full_url = f"{full_url}{separator}event_id={event_id}"

    return full_url


ensure_report_storage()
ensure_news_storage()


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


def make_call(event_id=None):
    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER or not USER_PHONE_NUMBER:
        print("Twilio error: Missing Twilio credentials")
        return False

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        if not BASE_URL:
            print("Twilio error: Missing BASE_URL")
            return False

        voice_url = build_public_url("/voice", event_id)
        call = client.calls.create(
            to=USER_PHONE_NUMBER,
            from_=TWILIO_PHONE_NUMBER,
            url=voice_url,
            method="GET",
        )
        print("📞 CALL INITIATED:", call.sid)
        if event_id:
            update_event(event_id, "call_made", True)
            update_event_timeline(event_id, "call", current_time_string())
        return True
    except Exception as exc:
        print("Twilio error:", exc)
        return False


def delayed_call(event_id=None):
    time.sleep(10)
    print("⏰ INITIATING VOICE CALL AFTER 10 SECONDS")
    make_call(event_id)


def send_email(image_path, label, event_id=None):
    try:
        print("📧 Sending email...")
        print("To:", EMAIL_RECEIVER)

        if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECEIVER:
            print("❌ EMAIL ERROR: Missing EMAIL_SENDER, EMAIL_PASSWORD, or EMAIL_RECEIVER")
            return False

        if not image_path or not os.path.exists(image_path):
            print("❌ EMAIL ERROR: Missing or invalid image_path", image_path)
            return False

        msg = EmailMessage()
        msg["Subject"] = "🚨 Wildlife Intrusion Alert"
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER

        msg.set_content(f"Intrusion detected in Nelambur. Type: {label}")

        with open(image_path, "rb") as image_file:
            msg.add_attachment(
                image_file.read(),
                maintype="image",
                subtype="jpeg",
                filename="intrusion.jpg",
            )

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)

        print("✅ Email sent successfully")
        if event_id:
            update_event(event_id, "email_sent", True)
            update_event_timeline(event_id, "email", current_time_string())
        return True
    except Exception as e:
        print("❌ EMAIL ERROR:", e)
        return False


def send_email_simple(subject, body):
    if not EMAIL_SENDER or not EMAIL_PASSWORD or not EMAIL_RECEIVER:
        print("❌ EMAIL ERROR: Missing EMAIL_SENDER, EMAIL_PASSWORD, or EMAIL_RECEIVER")
        return False

    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = EMAIL_RECEIVER
        msg.set_content(body)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
            smtp.send_message(msg)

        print("✅ Plain email sent successfully")
        return True
    except Exception as exc:
        print("❌ PLAIN EMAIL ERROR:", exc)
        return False


def send_news_email(article):
    subject = "⚠️ Nearby Intrusion Alert"
    body = f"""
News Alert Detected!

Title: {article.get('title', 'Unknown')}
Location: {article.get('city', DEFAULT_NEWS_CITY)}
Link: {article.get('link', '')}

Check immediately.
"""
    return send_email_simple(subject, body)


def fetch_and_store_news(city):
    city_name = (city or "").strip()
    if not city_name:
        return []

    try:
        articles = fetch_news(city_name)
    except Exception as exc:
        print("News fetch error:", exc)
        return []

    newly_saved = []
    for article in articles:
        if save_news(article):
            newly_saved.append(article)
            send_news_email(article)

    return newly_saved


def news_scheduler():
    while True:
        try:
            city_name = load_news_city()
            print(f"📰 Checking news for {city_name}...")
            fetch_and_store_news(city_name)
        except Exception as exc:
            print("News scheduler error:", exc)

        time.sleep(86400)


def trigger_news_refresh(city):
    city_name = (city or "").strip()
    if not city_name:
        return False

    with news_refresh_lock:
        if city_name.lower() in news_refreshing_cities:
            return False
        news_refreshing_cities.add(city_name.lower())

    def _run_refresh():
        try:
            fetch_and_store_news(city_name)
        finally:
            with news_refresh_lock:
                news_refreshing_cities.discard(city_name.lower())

    Thread(target=_run_refresh, daemon=True).start()
    return True


def call_forest_officer(event_id=None):
    print("📞 Calling forest officer...")

    if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER or not FOREST_OFFICER_NUMBER:
        print("Twilio error: Missing credentials or FOREST_OFFICER_NUMBER for escalation call")
        return False

    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        call = client.calls.create(
            to=FOREST_OFFICER_NUMBER,
            from_=TWILIO_PHONE_NUMBER,
            twiml="""
            <Response>
                <Say>Emergency alert. Wildlife intrusion detected in Nelambur. Immediate attention required.</Say>
            </Response>
            """,
        )
        print("✅ Forest officer call placed")
        print("📞 FOREST OFFICER CALL SID:", call.sid)
        if event_id:
            update_event(event_id, "forest_notified", True)
            update_event_timeline(event_id, "forest", current_time_string())
        return True
    except Exception as exc:
        print("Forest officer call error:", exc)
        return False


def trigger_escalation(event_id=None):
    print("🚀 ESCALATION STARTED")
    try:
        print("Image:", last_image_path)
        print("Label:", last_label)

        target_event_id = event_id or last_event_id

        if not last_image_path or not last_label:
            print("⚠️ No detection data available")
            return False

        email_ok = send_email(last_image_path, last_label, target_event_id)
        print("Email status:", email_ok)
        call_ok = call_forest_officer(target_event_id)
        print("Forest call status:", call_ok)

        print("✅ Escalation complete")
        return email_ok and call_ok
    except Exception as e:
        print("❌ ESCALATION ERROR:", e)
        return False


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return response


def generate_frames():
    global current_status, current_label, first_seen_time, last_confirmed_label, last_detection_time
    global last_image_path, last_label, last_event_id

    if not camera.isOpened():
        raise RuntimeError("Cannot open camera 1")

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
                    last_image_path = filename
                    last_label = mapped_label.upper()
                    event_record = save_event(
                        {
                            "timestamp": current_time_string(),
                            "type": mapped_label.upper(),
                            "confidence": round(float(detected_confidence), 2),
                            "image_path": filename,
                            "location": LOCATION_NAME,
                            "telegram_sent": False,
                            "call_made": False,
                            "user_response": "Pending",
                            "email_sent": False,
                            "forest_notified": False,
                            "timeline": {
                                "detected": current_time_string(),
                                "telegram": "",
                                "call": "",
                                "user_response": "",
                                "email": "",
                                "forest": "",
                            },
                        }
                    )
                    event_id = event_record.get("event_id") if event_record else None
                    last_event_id = event_id
                    print("Sending to Telegram:", filename)
                    sent_ok = send_telegram_alert(filename, mapped_label, detected_confidence)
                    if sent_ok and event_id:
                        update_event(event_id, "telegram_sent", True)
                        update_event_timeline(event_id, "telegram", current_time_string())
                    if sent_ok:
                        with alert_lock:
                            last_confirmed_label = candidate_alert_label
                        print("📞 SPAWNING DELAYED CALL THREAD")
                        call_thread = Thread(target=delayed_call, args=(event_id,), daemon=True)
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


@app.route("/reports", methods=["GET"])
def get_reports():
    events = load_events()
    report_items = []

    for event in events:
        report_path = event.get("report_file")
        if not report_path:
            continue

        report_items.append(
            {
                "timestamp": event.get("timestamp"),
                "type": event.get("type"),
                "confidence": float(event.get("confidence", 0.0)),
                "user_response": event.get("user_response", "Pending"),
                "report_path": report_path,
            }
        )

    return jsonify(report_items)


@app.route("/news", methods=["GET"])
def get_news():
    city = request.args.get("city", "").strip()
    target_city = city or load_news_city()

    alerts = fetch_intrusion_news(target_city)

    for alert in alerts:
        title = alert.get("title", "")
        if title and title not in sent_alert_titles:
            send_telegram_intrusion_alert(alert)
            sent_alert_titles.add(title)

    return jsonify({"city": target_city, "alerts": alerts, "lastUpdated": datetime.now().isoformat()})


@app.route("/news/city", methods=["POST"])
def set_news_city():
    payload = request.get_json(silent=True) or {}
    city = str(payload.get("city", "")).strip()
    if not city:
        return jsonify({"error": "city is required"}), 400

    saved = save_news_city(city)
    if not saved:
        return jsonify({"error": "failed to save city"}), 500

    return jsonify({"city": city})


@app.route("/download/<path:report_path>", methods=["GET"])
def download_report(report_path):
    normalized_path = os.path.normpath(report_path).lstrip(os.sep)
    full_path = os.path.abspath(os.path.join(os.getcwd(), normalized_path))
    reports_root = os.path.abspath(REPORTS_DIR)

    if not full_path.startswith(reports_root + os.sep):
        abort(403, description="Forbidden report path")

    if not os.path.exists(full_path):
        abort(404, description="Report not found")

    return send_file(
        full_path,
        as_attachment=True,
        download_name=os.path.basename(full_path),
        mimetype="application/pdf",
    )


@app.route("/voice", methods=["GET", "POST"])
def voice():
    from twilio.twiml.voice_response import VoiceResponse, Gather

    print("VOICE ROUTE HIT")
    event_id = request.args.get("event_id")
    action_url = build_public_url("/handle-key", event_id)

    response = VoiceResponse()
    try:
        gather = Gather(
            input="dtmf",
            num_digits=1,
            action=action_url,
            method="POST",
            timeout=7,
        )
        gather.say(
            "Intrusion detected. We have sent a picture. If it seems suspicious, press 4.",
            voice="alice",
            language="en-US",
        )
        response.append(gather)
        response.say("No input received. Goodbye.", voice="alice", language="en-US")
        response.hangup()
    except Exception as exc:
        print("Voice route error:", exc)
        response.say("System is temporarily unavailable. Goodbye.", voice="alice", language="en-US")
        response.hangup()

    return str(response)


@app.route("/handle-key", methods=["POST"])
def handle_key():
    from flask import request
    from twilio.twiml.voice_response import VoiceResponse

    event_id = request.args.get("event_id") or find_latest_pending_event_id()
    digit = request.form.get("Digits")
    print("HANDLE KEY HIT:", digit)

    response = VoiceResponse()
    try:
        if digit == "4":
            if event_id:
                update_event(event_id, "user_response", "Confirmed")
                update_event_timeline(event_id, "user_response", current_time_string())
            response.say(
                "Intrusion confirmed. Authorities are being notified.",
                voice="alice",
                language="en-US",
            )
            escalation_thread = threading.Thread(target=trigger_escalation, args=(event_id,), daemon=True)
            escalation_thread.start()
            print("Escalation thread started")
        else:
            if event_id:
                update_event(event_id, "user_response", "Ignored")
                update_event_timeline(event_id, "user_response", current_time_string())
            response.say("No action taken.", voice="alice", language="en-US")
    except Exception as exc:
        print("Handle-key route error:", exc)
        response.say("Could not process your input. Goodbye.", voice="alice", language="en-US")

    response.hangup()
    return str(response)


if __name__ == "__main__":
    threading.Thread(target=news_scheduler, daemon=True).start()
    app.run(host="0.0.0.0", port=5000, debug=False)
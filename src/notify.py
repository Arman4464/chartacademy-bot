"""
Discord Notification Module for ChartAcademy Bot
Supports sending rich, trader-aesthetic Discord alerts via Webhook:
- Clean completion summary with visual progress bar, streak counter, and goal projections
- Immediate alert on session issues with visual screenshot attachments
- 1-time missed/failed session alerts
"""

import os
import sys
import json
import uuid
import urllib.request
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("ChartAcademyBot")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")
POINTS_LOG_FILE = os.path.join(PROJECT_ROOT, "data", "points_tracker.json")


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[Notify] Error reading config.json: {e}")
    return {}


def make_progress_bar(pct: float, length: int = 12) -> str:
    """Creates a clean ASCII block progress bar."""
    filled = int(round((pct / 100.0) * length))
    filled = max(0, min(length, filled))
    return f"`[{'█' * filled}{'░' * (length - filled)}]` **{pct:.1f}%**"


def calculate_streak_and_projection(points_record: dict) -> dict:
    """Calculates active streak and estimated goal completion date."""
    streak = 1
    avg_gain = 50.0  # Default assumption
    est_date_str = "Calculating..."
    days_left = 0

    if os.path.exists(POINTS_LOG_FILE):
        try:
            with open(POINTS_LOG_FILE, "r", encoding="utf-8-sig") as f:
                history = json.load(f)
                if isinstance(history, list) and history:
                    # Calculate streak based on dates
                    dates = sorted([h.get("date") for h in history if h.get("date")])
                    if dates:
                        streak = 1
                        for i in range(len(dates) - 1, 0, -1):
                            d2 = datetime.strptime(dates[i], "%Y-%m-%d")
                            d1 = datetime.strptime(dates[i-1], "%Y-%m-%d")
                            if (d2 - d1).days == 1:
                                streak += 1
                            else:
                                break

                    # Calculate average gain from sessions that had positive gain
                    gains = [h.get("daily_gain", 0) for h in history if h.get("daily_gain", 0) > 0]
                    if gains:
                        avg_gain = sum(gains) / len(gains)

        except Exception as e:
            logger.warning(f"[Notify] Calculation note: {e}")

    rem = points_record.get("remaining", 0)
    if avg_gain > 0 and rem > 0:
        days_left = int(round(rem / avg_gain))
        est_target = datetime.now() + timedelta(days=days_left)
        est_date_str = f"{est_target.strftime('%b %d, %Y')} (~{days_left} days left)"
    elif rem == 0:
        est_date_str = "Goal Achieved! 🏆"

    return {
        "streak": streak,
        "avg_gain": round(avg_gain, 1),
        "days_left": days_left,
        "est_date_str": est_date_str
    }


def send_discord_webhook(content: str = None, embeds: list = None, image_path: str = None) -> bool:
    """Sends payload (and optional image attachment) to Discord."""
    config = load_config()
    webhook_url = config.get("discord_webhook_url", "").strip()

    if not webhook_url:
        logger.info("[Notify] No Discord webhook URL configured. Skipping Discord message.")
        return False

    payload = {"username": "ChartAcademy Bot"}
    if content:
        payload["content"] = content
    if embeds:
        payload["embeds"] = embeds

    try:
        if image_path and os.path.exists(image_path):
            filename = os.path.basename(image_path)
            boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
            body = bytearray()

            # 1. payload_json
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(b'Content-Disposition: form-data; name="payload_json"\r\n')
            body.extend(b"Content-Type: application/json\r\n\r\n")
            body.extend(json.dumps(payload).encode("utf-8"))
            body.extend(b"\r\n")

            # 2. file part
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="files[0]"; filename="{filename}"\r\n'.encode("utf-8"))
            content_type = b"Content-Type: image/jpeg\r\n\r\n" if filename.lower().endswith((".jpg", ".jpeg")) else b"Content-Type: image/png\r\n\r\n"
            body.extend(content_type)
            with open(image_path, "rb") as f:
                body.extend(f.read())
            body.extend(b"\r\n")

            body.extend(f"--{boundary}--\r\n".encode("utf-8"))

            req = urllib.request.Request(
                webhook_url,
                data=bytes(body),
                headers={
                    "Content-Type": f"multipart/form-data; boundary={boundary}",
                    "User-Agent": "ChartAcademyBot/1.0"
                }
            )
        else:
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=data,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "ChartAcademyBot/1.0"
                }
            )

        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status in [200, 204]:
                logger.info("[Notify] Discord notification sent successfully!")
                return True

    except Exception as e:
        logger.warning(f"[Notify] Failed to send Discord webhook: {e}")

    return False


def notify_session_success(class_title: str, pure_video_seconds: float, points_record: dict, screenshot_path: str = None):
    """Sends a trader-aesthetic completion embed with stats, progress bar, streak, and screenshot."""
    mins = int(pure_video_seconds // 60)
    secs = int(pure_video_seconds % 60)

    pts = points_record.get("points", 0)
    goal = points_record.get("goal", 1750)
    rem = points_record.get("remaining", 0)
    gain = points_record.get("daily_gain", 0)
    pct = points_record.get("progress_pct", (pts / goal * 100.0) if goal > 0 else 100.0)

    proj = calculate_streak_and_projection(points_record)
    prog_bar = make_progress_bar(pct)

    embed = {
        "title": "🎓  ChartAcademy Session Completed",
        "description": f"**Masterclass:** *{class_title}*\n**Playback:** `{mins}m {secs}s` pure video time (Reward Verified ✅)",
        "color": 0x10b981,  # Emerald Green
        "fields": [
            {
                "name": "📊 Academy Points",
                "value": f"**{pts:,}** / {goal:,} pts  (+{gain:,} today)",
                "inline": True
            },
            {
                "name": "🔥 Active Streak",
                "value": f"**{proj['streak']}** Day{'s' if proj['streak'] != 1 else ''}",
                "inline": True
            },
            {
                "name": "🎯 Goal Pace & Projection",
                "value": f"**{proj['est_date_str']}**\n*({rem:,} pts remaining)*",
                "inline": False
            },
            {
                "name": "📈 Goal Progress",
                "value": prog_bar,
                "inline": False
            }
        ],
        "footer": {"text": f"Daily Automation • {datetime.now().strftime('%b %d, %Y • %I:%M %p')}"}
    }

    if screenshot_path and os.path.exists(screenshot_path):
        filename = os.path.basename(screenshot_path)
        embed["image"] = {"url": f"attachment://{filename}"}

    send_discord_webhook(embeds=[embed], image_path=screenshot_path)


def notify_session_warning(screenshot_path: str = None):
    """Sends a discreet alert embed with screenshot when an issue occurs."""
    embed = {
        "title": "⚠️  ChartAcademy Alert",
        "description": "An issue or unexpected state occurred during today's session. Attached is the browser view at the exact moment of the alert.",
        "color": 0xf59e0b,  # Amber
        "footer": {"text": f"ChartAcademy Daily Watcher • {datetime.now().strftime('%b %d, %Y • %I:%M %p')}"}
    }

    if screenshot_path and os.path.exists(screenshot_path):
        filename = os.path.basename(screenshot_path)
        embed["image"] = {"url": f"attachment://{filename}"}

    send_discord_webhook(embeds=[embed], image_path=screenshot_path)


def notify_missed_run(reason: str = "No internet connection or scheduled trigger missed"):
    """Sends a 1-time notification when a run never starts or fails to connect."""
    embed = {
        "title": "⚠️  ChartAcademy Run Missed / Delayed",
        "description": f"Today's scheduled session could not start automatically.\n**Reason:** *{reason}*\n\n👉 A prompt has been opened on your desktop to start the session now.",
        "color": 0xef4444,  # Red
        "footer": {"text": f"ChartAcademy Watcher • {datetime.now().strftime('%b %d, %Y • %I:%M %p')}"}
    }
    send_discord_webhook(embeds=[embed])


if __name__ == "__main__":
    print("Testing upgraded Discord embeds...")
    avatar_path = os.path.join(PROJECT_ROOT, "data", "bot_avatar.jpg")
    notify_session_success(
        "Institutional Volume & Liquidity Concepts",
        1825,
        {"points": 470, "goal": 1750, "remaining": 1280, "daily_gain": 50, "progress_pct": 26.9},
        screenshot_path=avatar_path if os.path.exists(avatar_path) else None
    )

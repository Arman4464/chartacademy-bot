"""
ChartAcademy Leaderboard & Points Tracker
Navigates to https://app.chartacademy.com/leaderboard, extracts Academy Points,
tracks daily progress towards the goal of 1750, and persists history in data/points_tracker.json.
Displays a sleek trader-aesthetic desktop summary card.
"""

import os
import sys
import json
import re
import tkinter as tk
from datetime import datetime, timedelta

# Enable High-DPI scaling on Windows
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
POINTS_LOG_FILE = os.path.join(DATA_DIR, "points_tracker.json")


def load_points_history() -> list:
    if os.path.exists(POINTS_LOG_FILE):
        try:
            with open(POINTS_LOG_FILE, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception as e:
            print(f"[PointsTracker] Warning reading points log: {e}")
    return []


def save_points_history(history: list):
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        with open(POINTS_LOG_FILE, "w", encoding="utf-8-sig") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"[PointsTracker] Warning saving points log: {e}")


def calculate_metrics(record: dict) -> dict:
    history = load_points_history()
    streak = 1
    avg_gain = 50.0

    if history:
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

        gains = [h.get("daily_gain", 0) for h in history if h.get("daily_gain", 0) > 0]
        if gains:
            avg_gain = sum(gains) / len(gains)

    rem = record.get("remaining", 0)
    days_left = int(round(rem / avg_gain)) if avg_gain > 0 and rem > 0 else 0
    return {
        "streak": streak,
        "avg_gain": round(avg_gain, 1),
        "days_left": days_left
    }


def show_points_popup(record: dict):
    """Shows a professional trader-aesthetic floating card with live progress bar."""
    try:
        root = tk.Tk()
        root.title("Academy Points")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.configure(bg="#0d1117")

        width = 410
        height = 190
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        pos_x = sw - width - 24
        pos_y = sh - height - 60
        root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

        container = tk.Frame(root, bg="#0d1117", highlightbackground="#238636", highlightthickness=1)
        container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Header
        header = tk.Frame(container, bg="#0d1117")
        header.pack(fill=tk.X, padx=16, pady=(12, 4))

        tk.Label(header, text="🎯  Academy Points Logged", font=("Segoe UI", 11, "bold"), fg="#10b981", bg="#0d1117").pack(side=tk.LEFT)
        tk.Label(header, text=datetime.now().strftime("%I:%M %p"), font=("Segoe UI", 9), fg="#8b949e", bg="#0d1117").pack(side=tk.RIGHT)

        pts = record.get("points", 0)
        goal = record.get("goal", 1750)
        rem = record.get("remaining", 0)
        pct = record.get("progress_pct", 0)
        gain = record.get("daily_gain", 0)

        metrics = calculate_metrics(record)
        gain_str = f" (+{gain} today)" if gain > 0 else ""

        # Main points line
        stats_frame = tk.Frame(container, bg="#0d1117")
        stats_frame.pack(fill=tk.X, padx=16, pady=(4, 6))

        tk.Label(
            stats_frame,
            text=f"{pts:,} / {goal:,} pts{gain_str}",
            font=("Segoe UI", 13, "bold"),
            fg="#f0f6fc",
            bg="#0d1117"
        ).pack(side=tk.LEFT)

        tk.Label(
            stats_frame,
            text=f"{pct:.1f}%",
            font=("Segoe UI", 12, "bold"),
            fg="#10b981",
            bg="#0d1117"
        ).pack(side=tk.RIGHT)

        # Canvas progress bar
        bar_canvas = tk.Canvas(container, height=7, bg="#161b22", highlightthickness=0)
        bar_canvas.pack(fill=tk.X, padx=16, pady=(0, 10))

        def draw_bar():
            w = bar_canvas.winfo_width()
            if w <= 1:
                w = width - 32
            fill_w = max(0, int(w * (pct / 100.0)))
            bar_canvas.create_rectangle(0, 0, fill_w, 7, fill="#10b981", width=0)

        root.after(50, draw_bar)

        # Details line
        details_text = f"🔥 {metrics['streak']}-Day Streak  •  {rem:,} pts remaining (~{metrics['days_left']} days left)"
        tk.Label(
            container,
            text=details_text,
            font=("Segoe UI", 9),
            fg="#8b949e",
            bg="#0d1117"
        ).pack(anchor="w", padx=16, pady=(0, 10))

        # Bottom dismiss button
        btn_frame = tk.Frame(container, bg="#0d1117")
        btn_frame.pack(fill=tk.X, padx=16, pady=(0, 10))

        tk.Button(
            btn_frame,
            text="Dismiss",
            font=("Segoe UI", 9),
            bg="#21262d",
            fg="#c9d1d9",
            activebackground="#30363d",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=12,
            pady=3,
            cursor="hand2",
            command=root.destroy
        ).pack(side=tk.RIGHT)

        # Auto-dismiss after 12 seconds
        root.after(12000, root.destroy)
        root.mainloop()
    except Exception:
        pass


def scrape_and_update_points(page, goal: int = 1750) -> dict:
    """
    Extracts Academy Points from https://app.chartacademy.com/leaderboard.
    Updates data/points_tracker.json and displays a visual summary.
    """
    print("\n" + "=" * 60)
    print(" [PointsTracker] Navigating to https://app.chartacademy.com/leaderboard...")
    print("=" * 60)

    try:
        page.goto("https://app.chartacademy.com/leaderboard", wait_until="networkidle", timeout=30000)
    except Exception as e:
        print(f"[PointsTracker] Note on navigation: {e}. Checking loaded DOM...")

    page.wait_for_timeout(3000)

    points_val = None
    try:
        label_elem = page.locator("text='Academy Points'").first
        label_elem.wait_for(state="visible", timeout=15000)

        parent = label_elem.locator("..")
        text = parent.inner_text()
        print(f"[PointsTracker] Found Leaderboard Card Text: {repr(text)}")

        numbers = re.findall(r"[\d,]+", text)
        for num_str in numbers:
            clean = num_str.replace(",", "").strip()
            if clean.isdigit() and int(clean) > 0:
                points_val = int(clean)
                break

        if points_val is None:
            headings = parent.locator("h1, h2, h3, h4, h5, h6, span, p").all()
            for h in headings:
                t = h.inner_text().strip().replace(",", "")
                if t.isdigit() and int(t) > 0:
                    points_val = int(t)
                    break
    except Exception as e:
        print(f"[PointsTracker] Error locating 'Academy Points': {e}")

    if points_val is None:
        print("[PointsTracker] Could not parse Academy Points number.")
        return {"error": "Could not extract points"}

    today_str = datetime.now().strftime("%Y-%m-%d")
    now_iso = datetime.now().isoformat()

    history = load_points_history()
    prev_points = history[-1]["points"] if history else None
    daily_gain = (points_val - prev_points) if prev_points is not None else 0

    record = {
        "date": today_str,
        "timestamp": now_iso,
        "points": points_val,
        "daily_gain": daily_gain,
        "goal": goal,
        "remaining": max(0, goal - points_val),
        "progress_pct": round((points_val / goal) * 100.0, 1) if goal > 0 else 100.0
    }

    if history and history[-1].get("date") == today_str:
        history[-1] = record
    else:
        history.append(record)

    save_points_history(history)

    print("\n" + "=" * 60)
    print(" 🎯 ACADEMY POINTS LOGGED SUCCESSFULLY")
    print("-" * 60)
    print(f" Current Points : {record['points']:,} pts")
    print(f" Today's Gain   : +{record['daily_gain']:,} pts")
    print(f" Goal Target    : {record['goal']:,} pts")
    print(f" Goal Progress  : {record['progress_pct']}%")
    print(f" Remaining      : {record['remaining']:,} pts to reach 1,750 goal")
    print("=" * 60 + "\n")

    show_points_popup(record)
    return record


if __name__ == "__main__":
    test_record = {"points": 470, "goal": 1750, "remaining": 1280, "progress_pct": 26.9, "daily_gain": 50}
    show_points_popup(test_record)

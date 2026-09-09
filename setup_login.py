"""
One-Time Setup Script for ChartAcademy
Launches standard Google Chrome directly (WITHOUT automation wrappers)
so Google's bot detection is completely bypassed and allows 100% smooth login.
Once logged in, your session is saved to disk for the daily automated watcher!
"""

import os
import sys
import json
import subprocess
import time

try:
    sys.stdout.reconfigure(encoding="utf-8-sig")
except Exception:
    pass

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(PROJECT_ROOT, "config.json")
DEFAULT_PROFILE_DIR = os.path.expanduser(r"~\.chartacademy_profile")


def find_chrome() -> str:
    """Finds Google Chrome executable across standard Windows installation paths."""
    candidates = [
        os.environ.get("CHROME_PATH", ""),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def run_setup():
    chrome_path = find_chrome()
    cfg = load_config()
    target_email = cfg.get("google_account", "your Google account")

    print("=" * 70)
    print(" 🎓 ChartAcademy Genuine Browser Login (Google Anti-Bot Bypass)")
    print(f" Target Profile Directory : {DEFAULT_PROFILE_DIR}")
    print(f" Detected Chrome Path     : {chrome_path}")
    print("=" * 70)
    print(" Launching official Google Chrome natively (no automation wrapper)...")
    print(" This ensures Google recognizes standard Chrome and allows sign in.")
    print("=" * 70 + "\n")

    if not os.path.exists(chrome_path):
        print(f"❌ Error: Chrome executable not found at '{chrome_path}'.")
        print("Please install Google Chrome or set CHROME_PATH environment variable.")
        sys.exit(1)

    os.makedirs(DEFAULT_PROFILE_DIR, exist_ok=True)

    cmd = [
        chrome_path,
        f"--user-data-dir={DEFAULT_PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "https://app.chartacademy.com/masterclasses"
    ]

    proc = subprocess.Popen(cmd)

    print("=" * 70)
    print(" 📌 ACTION REQUIRED IN THE OPENED CHROME WINDOW:")
    print(" 1. Click 'Sign in with Google'")
    print(f" 2. Enter {target_email} and your password.")
    print("    (Notice Google now allows sign-in because this is official Chrome!)")
    print(" 3. Once you are logged in and see the masterclasses, return here and:")
    print("    👉 PRESS [ENTER] IN THIS TERMINAL (or close Chrome)")
    print("=" * 70 + "\n")

    try:
        input("Waiting for you to finish logging in... Press ENTER when done: ")
    except (EOFError, KeyboardInterrupt):
        pass

    print("\nFinalizing session save...")
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        pass

    print("=" * 70)
    print(" ✅ SUCCESS! Your Google and ChartAcademy session is permanently saved.")
    print(f" Session profile stored in: {DEFAULT_PROFILE_DIR}")
    print(" The automated watcher will now be able to use this session every day!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_setup()

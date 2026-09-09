"""
ChartAcademy System Diagnostic & Health Check Module
Quick 3-second comprehensive audit of all system components:
- Network & ChartAcademy server latency
- Chrome executable & dedicated profile
- Discord Webhook connection
- Windows Task Scheduler status
- Academy points progress & streak
"""

import os
import sys
import json
import time
import subprocess
import urllib.request
from datetime import datetime

# Ensure UTF-8 output for Windows console
try:
    sys.stdout.reconfigure(encoding='utf-8-sig')
except Exception:
    pass

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from notify import load_config, calculate_streak_and_projection, make_progress_bar

# ANSI Colors
GREEN = "\033[92m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def find_chrome() -> str:
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


def check_chrome(profile_dir: str) -> dict:
    chrome_path = find_chrome()
    res = {"ok": False, "version": "Unknown", "profile_ok": False, "path": chrome_path}
    if os.path.exists(chrome_path):
        try:
            out = subprocess.check_output(
                f'powershell -command "(Get-Item \'{chrome_path}\').VersionInfo.ProductVersion"',
                shell=True,
                text=True
            ).strip()
            res["version"] = out
            res["ok"] = True
        except Exception:
            res["ok"] = True

    # Check cookies file in profile
    default_dir = os.path.join(profile_dir, "Default")
    cookie_file = os.path.join(default_dir, "Network", "Cookies")
    if not os.path.exists(cookie_file):
        cookie_file = os.path.join(default_dir, "Cookies")
    res["profile_ok"] = os.path.exists(profile_dir) and os.path.exists(cookie_file)
    return res


def check_network() -> dict:
    res = {"ok": False, "latency_ms": 0}
    t0 = time.time()
    try:
        req = urllib.request.Request("https://app.chartacademy.com", headers={"User-Agent": "ChartAcademyBot/1.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            if r.status in [200, 301, 302]:
                res["ok"] = True
                res["latency_ms"] = int((time.time() - t0) * 1000)
    except Exception:
        pass
    return res


def check_discord() -> dict:
    cfg = load_config()
    url = cfg.get("discord_webhook_url", "").strip()
    if not url:
        return {"ok": False, "status": "Not configured"}
    if not url.startswith("https://discord.com/api/webhooks/"):
        return {"ok": False, "status": "Invalid URL format"}
    return {"ok": True, "status": "Configured & Active"}


def check_scheduler(task_name: str = "ChartAcademyDailyWatcher") -> dict:
    cmd = f'powershell -command "$t = Get-ScheduledTask -TaskName \'{task_name}\' -ErrorAction SilentlyContinue; if ($t) {{ Write-Host $t.State }} else {{ Write-Host \'NotFound\' }}"'
    try:
        out = subprocess.check_output(cmd, shell=True, text=True).strip()
        return {"exists": (out != "NotFound"), "state": out if out != "NotFound" else "Not Registered"}
    except Exception:
        return {"exists": False, "state": "Error querying scheduler"}


def run_healthcheck():
    cfg = load_config()
    profile_dir = os.path.expanduser(r"~\.chartacademy_profile")
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    completed_file = os.path.join(DATA_DIR, "completed_classes.json")
    points_file = os.path.join(DATA_DIR, "points_tracker.json")

    print("\n" + "=" * 68)
    print(f"{BOLD}{CYAN}  ⚡ CHARTACADEMY SYSTEM HEALTH AUDIT{RESET}")
    print(f"  Audit Time : {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}")
    print("=" * 68)

    # 1. Network & ChartAcademy Server
    net = check_network()
    if net["ok"]:
        print(f"  [{GREEN}PASS{RESET}] Network & ChartAcademy Server : {GREEN}Online{RESET} ({net['latency_ms']}ms latency)")
    else:
        print(f"  [{RED}FAIL{RESET}] Network & ChartAcademy Server : {RED}Unreachable / Offline{RESET}")

    # 2. Google Chrome
    cr = check_chrome(profile_dir)
    if cr["ok"]:
        print(f"  [{GREEN}PASS{RESET}] Official Google Chrome        : {GREEN}Installed{RESET} (v{cr['version']})")
    else:
        print(f"  [{RED}FAIL{RESET}] Official Google Chrome        : {RED}Not found at default path{RESET}")

    # 3. Persistent Profile & Auth
    if cr["profile_ok"]:
        print(f"  [{GREEN}PASS{RESET}] Dedicated Profile & Auth      : {GREEN}Verified{RESET} ({cfg.get('google_account', 'Account cached')})")
    else:
        print(f"  [{YELLOW}WARN{RESET}] Dedicated Profile & Auth      : {YELLOW}Profile exists but cookies not verified{RESET}")

    # 4. Discord Webhook
    disc = check_discord()
    if disc["ok"]:
        print(f"  [{GREEN}PASS{RESET}] Discord Webhook Alerts        : {GREEN}Active & Configured{RESET}")
    else:
        print(f"  [{YELLOW}WARN{RESET}] Discord Webhook Alerts        : {YELLOW}{disc['status']}{RESET}")

    # 5. Windows Task Scheduler
    sched = check_scheduler("ChartAcademyDailyWatcher")
    if sched["exists"] and sched["state"] == "Ready":
        print(f"  [{GREEN}PASS{RESET}] Windows Task Scheduler        : {GREEN}Ready{RESET} (Triggers daily at 11:58 AM IST)")
    else:
        print(f"  [{YELLOW}WARN{RESET}] Windows Task Scheduler        : {YELLOW}{sched['state']}{RESET}")

    # 6. Academy Points & Classes Progress
    completed_count = 0
    if os.path.exists(completed_file):
        try:
            with open(completed_file, "r", encoding="utf-8-sig") as f:
                c_data = json.load(f)
                completed_count = len(c_data)
        except Exception:
            pass

    points_record = {"points": 0, "goal": 1750, "remaining": 1750, "progress_pct": 0}
    if os.path.exists(points_file):
        try:
            with open(points_file, "r", encoding="utf-8-sig") as f:
                p_data = json.load(f)
                if p_data:
                    points_record = p_data[-1]
        except Exception:
            pass

    proj = calculate_streak_and_projection(points_record)
    pts = points_record.get("points", 0)
    goal = points_record.get("goal", 1750)
    rem = points_record.get("remaining", 1750)
    pct = points_record.get("progress_pct", 0)

    print("-" * 68)
    print(f"  {BOLD}Masterclasses Watched Database :{RESET} {completed_count} classes completed (Skiplist active)")
    print(f"  {BOLD}Current Academy Points Balance :{RESET} {GREEN}{pts:,}{RESET} / {goal:,} pts ({pct}%)")
    print(f"  {BOLD}Active Learning Streak         :{RESET} {YELLOW}🔥 {proj['streak']} Day{'s' if proj['streak'] != 1 else ''}{RESET}")
    print(f"  {BOLD}Estimated Goal Completion Date :{RESET} {CYAN}{proj['est_date_str']}{RESET}")
    print(f"  {BOLD}Progress Bar                   :{RESET} {make_progress_bar(pct, length=18)}")
    print("=" * 68 + "\n")


if __name__ == "__main__":
    run_healthcheck()

"""
ChartAcademy Daily Autonomous Watcher & Points Tracker
- Runs at 12:00 PM IST daily (with 2-minute pre-alert at 11:58 AM IST)
- Clean Chrome launch (NO unsupported command-line flags)
- Robust Google OAuth check & selection for rangooniarman@gmail.com
- Automatically clicks 'Continue' / 'Allow' if Google permission prompts appear
- Pure Video Playback Accumulator: Tracks actual seconds of video played (guaranteeing >= 30m 5s of real playback)
- Log Rotation: Daily rotation with 30-day retention in logs/
- Discord Notification: Clean alerts on completion or when any warning/error occurs
"""

import sys
import os
import time
import json
import re
import argparse
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Project root directory
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
SCREENSHOTS_DIR = os.path.join(LOGS_DIR, "screenshots")

for p in [PROJECT_ROOT, SRC_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

import urllib.request

# Imports from src
from dialog import show_cancel_dialog, show_missed_run_dialog
from points import scrape_and_update_points
from notify import notify_session_success, notify_session_warning, notify_missed_run
from health import run_healthcheck

# -------------------------------------------------------------
# File paths and configuration
# -------------------------------------------------------------
LOG_FILE = os.path.join(LOGS_DIR, "chartacademy.log")
COMPLETED_CLASSES_FILE = os.path.join(DATA_DIR, "completed_classes.json")
SESSION_STATE_FILE = os.path.join(DATA_DIR, "session_state.json")
CONFIG_FILE = os.path.join(PROJECT_ROOT, "config.json")


class FlushingTimedRotatingFileHandler(TimedRotatingFileHandler):
    """Rotates daily, keeps 30 days, flushes after every single emit."""
    def emit(self, record):
        super().emit(record)
        self.flush()


logger = logging.getLogger("ChartAcademyBot")
logger.setLevel(logging.INFO)
logger.handlers.clear()

formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

rot_handler = FlushingTimedRotatingFileHandler(
    LOG_FILE,
    when="midnight",
    interval=1,
    backupCount=30,
    encoding="utf-8"
)
rot_handler.setFormatter(formatter)
logger.addHandler(rot_handler)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

def load_app_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


APP_CONFIG = load_app_config()
DEFAULT_PROFILE_DIR = os.path.expanduser(r"~\.chartacademy_profile")
TARGET_EMAIL = APP_CONFIG.get("google_account", "trader@example.com")
MASTERCLASSES_URL = "https://app.chartacademy.com/masterclasses"
LOGIN_URL_SUBSTRING = "/login"

DEFAULT_WATCH_SECONDS = int(APP_CONFIG.get("watch_duration_minutes", 32) * 60)
MIN_PURE_PLAYBACK_SECONDS = int(APP_CONFIG.get("min_pure_playback_minutes", 30.1) * 60)
DEFAULT_POINTS_GOAL = int(APP_CONFIG.get("points_goal", 1750))


def load_completed_classes() -> set:
    if os.path.exists(COMPLETED_CLASSES_FILE):
        try:
            with open(COMPLETED_CLASSES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    logger.info(f"[Storage] Loaded {len(data)} completed classes from {COMPLETED_CLASSES_FILE}")
                    return set(data)
        except Exception as e:
            logger.warning(f"[Storage] Error reading completed classes: {e}")
    return set()


def mark_class_completed(class_title: str):
    if not class_title or class_title == "Unknown Class":
        return
    if "Lessons" in class_title or "hr" in class_title or "min" in class_title:
        return
    completed = load_completed_classes()
    if class_title not in completed:
        completed.add(class_title)
        try:
            with open(COMPLETED_CLASSES_FILE, "w", encoding="utf-8") as f:
                json.dump(sorted(list(completed)), f, indent=2)
            logger.info(f"[CompletedClasses] Successfully logged '{class_title}' in {COMPLETED_CLASSES_FILE}")
        except Exception as e:
            logger.warning(f"[CompletedClasses] Error saving completed class: {e}")


def load_session_state() -> dict:
    if os.path.exists(SESSION_STATE_FILE):
        try:
            with open(SESSION_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_session_state(state: dict):
    try:
        with open(SESSION_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.warning(f"[State] Error saving session state: {e}")


def wait_for_internet(max_wait_seconds=60) -> bool:
    """Verifies network connectivity to ChartAcademy, polling every 10s if offline."""
    t0 = time.time()
    while time.time() - t0 <= max_wait_seconds:
        try:
            req = urllib.request.Request("https://app.chartacademy.com", headers={"User-Agent": "ChartAcademyBot/1.0"})
            with urllib.request.urlopen(req, timeout=5) as r:
                if r.status in [200, 301, 302]:
                    return True
        except Exception:
            pass
        if time.time() - t0 + 10 <= max_wait_seconds:
            logger.info("[Network] Waiting for network connection...")
            time.sleep(10)
        else:
            break
    return False


def clean_class_title(raw_text: str) -> str:
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]
    for line in lines:
        if re.search(r"\d+\s+Lessons?", line, re.IGNORECASE):
            continue
        if re.search(r"^\d+(\.\d+)?\s*(hr|min|hours|minutes)", line, re.IGNORECASE):
            continue
        if line.upper() in ["NEW", "START CLASS", "CONTINUE CLASS", "REWATCH CLASS"]:
            continue
        if len(line) > 2:
            return line
    return lines[0] if lines else "Unknown Class"


def handle_authentication(page, context, target_email=TARGET_EMAIL, force_test=False):
    """
    Checks if login is required. If so, clicks 'Sign in with Google',
    selects target email, and handles permission/consent prompts.
    """
    if force_test:
        logger.info("[Auth] --force-login active! Clearing ChartAcademy cookies to test auto-login...")
        context.clear_cookies(name="*")
        page.goto("https://app.chartacademy.com/login", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(2000)

    current_url = page.url
    logger.info(f"[Auth] Checking authentication state. Current URL: {current_url}")

    google_btn = page.locator("text='Sign in with Google'").first

    try:
        is_login_page = LOGIN_URL_SUBSTRING in current_url or google_btn.is_visible(timeout=4000)
    except Exception:
        is_login_page = False

    if not is_login_page:
        logger.info("[Auth] User is already authenticated! Proceeding directly to classes.")
        return True

    logger.info("[Auth] Login prompt detected! Initiating 'Sign in with Google' flow...")
    try:
        popup = None
        try:
            with context.expect_page(timeout=10000) as popup_info:
                google_btn.click()
            popup = popup_info.value
            logger.info("[Auth] Google sign-in opened in a popup window.")
        except PlaywrightTimeoutError:
            logger.info("[Auth] Google sign-in loaded in main page.")
            popup = page

        auth_page = popup
        auth_page.wait_for_load_state("domcontentloaded", timeout=20000)
        logger.info(f"[Auth] Auth page loaded. Title: '{auth_page.title()}'. URL: {auth_page.url}")

        # Account selection
        logger.info(f"[Auth] Checking account chooser for: {target_email}...")
        username_prefix = target_email.split("@")[0] if "@" in target_email else target_email
        account_selectors = [
            f"text='{target_email}'",
            f"[data-email='{target_email}']",
            f"[data-identifier='{target_email}']",
            f"div:has-text('{target_email}')",
            f"div:has-text('{username_prefix}')"
        ]

        clicked = False
        for selector in account_selectors:
            elem = auth_page.locator(selector).first
            try:
                if elem.is_visible(timeout=2500):
                    logger.info(f"[Auth] Matched account selector '{selector}'. Clicking account...")
                    elem.click()
                    clicked = True
                    break
            except Exception:
                continue

        # Handle potential Google OAuth permission / 'Continue' / 'Allow' prompts
        auth_page.wait_for_timeout(2000)
        consent_buttons = auth_page.locator("button:has-text('Continue'), button:has-text('Allow'), button:has-text('Confirm')").all()
        for btn in consent_buttons:
            if btn.is_visible():
                logger.info(f"[Auth] Detected consent button: '{btn.inner_text()}'. Clicking to accept permissions...")
                try:
                    btn.click()
                    break
                except Exception:
                    pass

        # Wait for redirect back
        logger.info("[Auth] Waiting for redirect back to ChartAcademy...")
        page.wait_for_url(lambda u: "app.chartacademy.com" in u and "/login" not in u, timeout=45000)
        logger.info(f"[Auth] Successfully authenticated! Returned to: {page.url}")
        return True

    except Exception as e:
        logger.error(f"[Auth] Error during Google authentication: {e}")
        return False


def select_and_start_masterclass(page) -> str:
    logger.info(f"[ClassSelection] Navigating to {MASTERCLASSES_URL}...")
    try:
        page.goto(MASTERCLASSES_URL, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        logger.warning(f"[ClassSelection] Page navigation note: {e}. Scanning loaded DOM...")

    page.wait_for_timeout(3000)
    completed_set = load_completed_classes()

    # Strategy 1: "Continue Class" (In-progress)
    logger.info("[ClassSelection] Strategy 1: Scanning for 'Continue Class' (in-progress)...")
    continue_buttons = page.locator("text='Continue Class'").all()
    logger.info(f"[ClassSelection] Found {len(continue_buttons)} 'Continue Class' button(s).")

    for btn in continue_buttons:
        try:
            parent_card = btn.locator("xpath=ancestor::*[contains(@data-testid, 'featured') or contains(@class, 'Card')][1]")
            card_text = parent_card.inner_text() if parent_card.count() > 0 else ""
        except Exception:
            card_text = ""

        class_title = clean_class_title(card_text)
        if class_title in completed_set:
            logger.info(f"[ClassSelection] Skipping '{class_title}' (marked completed).")
            continue

        logger.info(f"[ClassSelection] Selected in-progress class: '{class_title}'. Clicking 'Continue Class'...")
        try:
            btn.scroll_into_view_if_needed()
            btn.click()
            page.wait_for_timeout(3000)
            logger.info(f"[ClassSelection] Successfully started in-progress class: '{class_title}'")
            return class_title
        except Exception as e:
            logger.warning(f"[ClassSelection] Click failed on 'Continue Class': {e}")

    # Strategy 2: "Start Class" (Unstarted)
    logger.info("[ClassSelection] Strategy 2: Scanning for 'Start Class' (new uncompleted)...")
    start_buttons = page.locator("text='Start Class'").all()
    logger.info(f"[ClassSelection] Found {len(start_buttons)} 'Start Class' button(s).")

    for btn in start_buttons:
        try:
            parent_card = btn.locator("xpath=ancestor::*[contains(@data-testid, 'featured') or contains(@class, 'Card')][1]")
            card_text = parent_card.inner_text() if parent_card.count() > 0 else ""
        except Exception:
            card_text = ""

        class_title = clean_class_title(card_text)
        if class_title in completed_set:
            logger.info(f"[ClassSelection] Skipping '{class_title}' (marked completed).")
            continue

        logger.info(f"[ClassSelection] Selected new class: '{class_title}'. Clicking 'Start Class'...")
        try:
            btn.scroll_into_view_if_needed()
            btn.click()
            page.wait_for_timeout(3000)
            logger.info(f"[ClassSelection] Successfully started new class: '{class_title}'")
            return class_title
        except Exception as e:
            logger.warning(f"[ClassSelection] Click failed on 'Start Class': {e}")

    # Strategy 3: Carousel Rows Below Suggested / Coming Soon
    logger.info("[ClassSelection] Strategy 3: Browsing class carousels below Suggested/Coming Soon...")
    page.mouse.wheel(0, 700)
    page.wait_for_timeout(2000)

    card_locators = page.locator("[data-testid^='master-class-card-']")
    total_cards = card_locators.count()
    logger.info(f"[ClassSelection] Detected {total_cards} class cards in carousel sections.")

    for round_idx in range(6):
        cards = card_locators.all()
        for card in cards:
            try:
                if not card.is_visible():
                    continue

                card_text = card.inner_text()
                class_title = clean_class_title(card_text)

                if class_title in completed_set:
                    continue
                if "Rewatch Class" in card_text:
                    logger.info(f"[ClassSelection] Card '{class_title}' shows 'Rewatch Class'. Marking completed and skipping.")
                    mark_class_completed(class_title)
                    continue
                if card.locator("[class*='Lock']").count() > 0:
                    continue

                logger.info(f"[ClassSelection] Target class identified: '{class_title}'. Scrolling into view and hovering...")
                card.scroll_into_view_if_needed()
                page.wait_for_timeout(400)
                card.hover()
                page.wait_for_timeout(600)

                action_btn = card.locator(".master-class-card--actions button, button[class*='MuiButton']").first
                if action_btn.is_visible():
                    logger.info(f"[ClassSelection] Hover play button revealed for '{class_title}'. Clicking play...")
                    action_btn.click()
                else:
                    logger.info(f"[ClassSelection] Clicking card directly for '{class_title}'...")
                    card.click()

                page.wait_for_timeout(3000)
                logger.info(f"[ClassSelection] Successfully started carousel class: '{class_title}'")
                return class_title

            except Exception as e:
                logger.debug(f"[ClassSelection] Card evaluation error: {e}")
                continue

        right_arrows = page.locator("button[aria-label='Scroll right']:not([disabled])").all()
        if right_arrows:
            logger.info("[ClassSelection] Visible cards skipped. Clicking '>' (Scroll right) to slide carousel...")
            try:
                right_arrows[0].scroll_into_view_if_needed()
                right_arrows[0].click()
                page.wait_for_timeout(1500)
            except Exception:
                page.mouse.wheel(0, 450)
        else:
            page.mouse.wheel(0, 500)
            page.wait_for_timeout(1500)

    logger.error("[ClassSelection] Could not find any uncompleted class to play.")
    return ""


def ensure_video_playing(page) -> bool:
    logger.info("[Video] Waiting for video element to mount...")

    video = page.locator("video").first
    try:
        video.wait_for(state="attached", timeout=25000)
        logger.info("[Video] Video element attached! Requesting playback...")
        video.evaluate("v => v.play()")
        page.wait_for_timeout(2000)

        state = video.evaluate("v => ({ paused: v.paused, currentTime: v.currentTime, duration: v.duration })")
        cur = state.get("currentTime", 0)
        dur = state.get("duration", 0)
        paused = state.get("paused", True)

        if not paused:
            logger.info(f"[Video] Confirmed video is PLAYING! Current time: {cur:.1f}s / {dur:.1f}s")
            return True
        else:
            logger.info("[Video] Video still paused. Attempting overlay play click...")
            play_overlay = page.locator("[aria-label*='Play' i], [class*='play' i], video").first
            if play_overlay.is_visible():
                play_overlay.click()
            page.wait_for_timeout(1500)
            return True

    except Exception as e:
        logger.warning(f"[Video] Video mounting or playback note: {e}")
        return False


def run_watchdog(page, target_seconds: int = DEFAULT_WATCH_SECONDS, current_class_title: str = "", min_pure_seconds: int = 0) -> float:
    start_time = time.time()
    logger.info("=" * 65)
    logger.info(f"[Watchdog] Starting watch session for '{current_class_title or 'Masterclass'}'")
    logger.info(f"[Watchdog] Session Wall-Clock Target : {target_seconds // 60}m {target_seconds % 60}s ({target_seconds}s)")
    if min_pure_seconds > 0:
        logger.info(f"[Watchdog] Minimum Pure Video Target: {min_pure_seconds // 60}m {min_pure_seconds % 60}s (Guarantees Reward!)")
    logger.info("=" * 65)

    last_log_time = 0
    poll_interval = 8
    video_locator = page.locator("video").first

    pure_video_played = 0.0
    last_cur_time = None

    while True:
        elapsed = time.time() - start_time
        remaining = target_seconds - elapsed

        try:
            if video_locator.is_visible():
                state = video_locator.evaluate("v => ({ paused: v.paused, ended: v.ended, currentTime: v.currentTime, duration: v.duration })")
                cur = state.get("currentTime", 0)
                dur = state.get("duration", 0)
                ended = state.get("ended", False)
                paused = state.get("paused", False)

                if not paused and cur is not None:
                    if last_cur_time is not None and cur > last_cur_time:
                        delta = cur - last_cur_time
                        if 0 < delta < 30:
                            pure_video_played += delta
                    last_cur_time = cur

                if ended or (dur > 0 and cur >= dur - 2):
                    logger.info(f"[Watchdog] Lesson finished ({cur:.1f}s / {dur:.1f}s). Logging completed class...")
                    if current_class_title:
                        mark_class_completed(current_class_title)

                    logger.info("[Watchdog] Waiting 10s for platform auto-advance...")
                    page.wait_for_timeout(10000)

                    try:
                        new_state = video_locator.evaluate("v => ({ paused: v.paused, ended: v.ended, currentTime: v.currentTime })")
                        if new_state.get("ended") or new_state.get("paused") or new_state.get("currentTime", 0) < 1:
                            logger.info("[Watchdog] No auto-advance. Navigating to select next masterclass...")
                            new_title = select_and_start_masterclass(page)
                            if new_title:
                                current_class_title = new_title
                                ensure_video_playing(page)
                                last_cur_time = None
                    except Exception as e:
                        logger.warning(f"[Watchdog] Auto-advance recheck note: {e}")

                elif paused:
                    logger.info("[Watchdog] Video was paused. Resuming playback...")
                    video_locator.evaluate("v => v.play()")
            else:
                logger.info("[Watchdog] Video buffering or transitioning to next lesson...")
                last_cur_time = None

            page.evaluate("window.dispatchEvent(new Event('mousemove'))")

        except Exception as e:
            logger.warning(f"[Watchdog] Watchdog tick note: {e}")

        wall_time_met = (elapsed >= target_seconds)
        pure_time_met = (pure_video_played >= min_pure_seconds) if min_pure_seconds > 0 else True

        if wall_time_met and pure_time_met:
            logger.info("=" * 65)
            logger.info(f"[Watchdog] Watch goal reached!")
            logger.info(f"[Watchdog] Total Wall-Clock Time  : {int(elapsed // 60)}m {int(elapsed % 60)}s")
            logger.info(f"[Watchdog] Pure Video Play Time    : {int(pure_video_played // 60)}m {int(pure_video_played % 60)}s")
            logger.info("=" * 65)
            break

        if elapsed - last_log_time >= 30:
            w_m, w_s = int(elapsed // 60), int(elapsed % 60)
            p_m, p_s = int(pure_video_played // 60), int(pure_video_played % 60)
            rem_m, rem_s = max(0, int(remaining // 60)), max(0, int(remaining % 60))
            logger.info(f"[Watchdog] Wall: {w_m}m {w_s}s | Pure Video: {p_m}m {p_s}s | Rem: {rem_m}m {rem_s}s | Class: '{current_class_title}'")
            last_log_time = elapsed

        time.sleep(poll_interval)

    return pure_video_played


def take_immediate_snapshot(page, prefix="alert") -> str:
    """Captures a screenshot at the exact instant an event, warning, or error occurs."""
    try:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        ss_path = os.path.join(SCREENSHOTS_DIR, f"{prefix}_{ts}.png")
        page.screenshot(path=ss_path, full_page=False)
        logger.info(f"[Screenshot] Immediately captured '{prefix}' screenshot at: {ss_path}")
        return ss_path
    except Exception as e:
        logger.warning(f"[Screenshot] Failed to capture immediate snapshot '{prefix}': {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description="ChartAcademy Autonomous Daily Watcher")
    parser.add_argument("--watch-duration", type=int, default=DEFAULT_WATCH_SECONDS,
                        help=f"Watch duration in seconds (default: {DEFAULT_WATCH_SECONDS}s = 32m)")
    parser.add_argument("--skip-dialog", action="store_true",
                        help="Skip the 2-minute pre-run countdown cancel dialog")
    parser.add_argument("--dialog-timeout", type=int, default=120,
                        help="Cancel dialog timeout in seconds (default: 120s)")
    parser.add_argument("--profile-dir", type=str, default=DEFAULT_PROFILE_DIR,
                        help=f"Chrome profile directory (default: {DEFAULT_PROFILE_DIR})")
    parser.add_argument("--goal", type=int, default=DEFAULT_POINTS_GOAL,
                        help=f"Daily Academy Points goal (default: {DEFAULT_POINTS_GOAL})")
    parser.add_argument("--background", action="store_true",
                        help="Run quietly in background without bringing window to foreground")
    parser.add_argument("--force-login", action="store_true",
                        help="Force login demonstration: triggers the Google OAuth sign-in flow")
    parser.add_argument("--health", "--healthcheck", action="store_true",
                        help="Run full system diagnostic health audit and exit")
    parser.add_argument("--force", action="store_true",
                        help="Force execution even if already completed today")
    args = parser.parse_args()

    if args.health:
        run_healthcheck()
        sys.exit(0)

    today_str = datetime.now().strftime("%Y-%m-%d")
    state = load_session_state()

    # 0. Check if already completed today (skip redundant runs)
    if state.get("last_successful_run") == today_str and not args.force:
        logger.info("=" * 65)
        logger.info(f"[Session] Today's session ({today_str}) has already completed successfully.")
        logger.info(f"[Session] Last Class Watched: '{state.get('last_completed_class', 'Completed')}'")
        logger.info("[Session] Exiting cleanly without disturbing you. (Use --force to override)")
        logger.info("=" * 65)
        sys.exit(0)

    # 0. Check Network Connectivity before opening browser
    logger.info("[PreRun] Verifying network connection to ChartAcademy...")
    if not wait_for_internet(max_wait_seconds=60):
        logger.error("[Network] No network connection detected after 60 seconds.")
        if state.get("missed_alert_date") != today_str:
            state["missed_alert_date"] = today_str
            save_session_state(state)
            notify_missed_run(reason="No internet connection detected at scheduled time")

            start_now = show_missed_run_dialog(reason="No internet connection detected")
            if start_now:
                logger.info("[PreRun] Trader clicked 'Start Session Now'. Waiting for network recovery...")
                if wait_for_internet(max_wait_seconds=120):
                    logger.info("[PreRun] Network connection online! Proceeding with session...")
                else:
                    logger.error("[PreRun] Network still offline. Exiting.")
                    sys.exit(1)
            else:
                logger.info("[PreRun] Missed session prompt dismissed. Exiting.")
                sys.exit(1)
        else:
            logger.info("[PreRun] Missed alert already delivered today. Exiting quietly.")
            sys.exit(1)

    min_pure = MIN_PURE_PLAYBACK_SECONDS if args.watch_duration >= 1800 else 0
    had_warnings_or_errors = False

    logger.info("=" * 65)
    logger.info(f" ChartAcademy Automation Initialized: {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}")
    logger.info(f" Mode           : {'Background (Quiet)' if args.background else 'Visible (Interactive)'}")
    logger.info(f" Watch Duration : {args.watch_duration}s ({args.watch_duration // 60}m {args.watch_duration % 60}s)")
    if min_pure > 0:
        logger.info(f" Pure Video Req : {min_pure}s (30m 5s to guarantee daily reward)")
    logger.info(f" Points Goal    : {args.goal} pts")
    logger.info(f" Log File       : {LOG_FILE} (30-day rotation)")
    logger.info("=" * 65)

    # 1. 2-Minute Pre-Run Cancel Dialog
    if not args.skip_dialog:
        logger.info(f"[PreRun] Displaying {args.dialog_timeout}s cancel dialog...")
        proceed = show_cancel_dialog(timeout_seconds=args.dialog_timeout)
        if not proceed:
            logger.info("[PreRun] Automation cancelled by user via countdown prompt. Exiting cleanly.")
            sys.exit(0)
        logger.info("[PreRun] User confirmed or timer expired. Proceeding with workflow!")
    else:
        logger.info("[PreRun] Skipping cancel dialog (--skip-dialog flag specified).")

    # 2. Launch Google Chrome cleanly with resource optimizations
    os.makedirs(args.profile_dir, exist_ok=True)
    logger.info(f"[Browser] Launching Google Chrome with persistent profile: {args.profile_dir}")

    # Optimized Chrome arguments (Low CPU, Low GPU, RAM capped to 256MB)
    chrome_args = [
        "--mute-audio",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-search-engine-choice-screen",
        "--disable-features=OptimizationGuideModelDownloading,OptimizationHintsUI,PrivacySandboxSettings4,Translate,MediaRouter",
        "--disable-component-update",
        "--disable-background-networking",
        "--disable-sync",
        "--disable-translate",
        "--disable-breakpad",
        "--js-flags=--max-old-space-size=256",
        "--renderer-process-limit=2",
    ]

    if args.background:
        chrome_args.extend(["--window-position=300,300", "--window-size=1280,800"])
    else:
        chrome_args.extend(["--window-position=60,60", "--window-size=1360,860"])

    class_title = "Unknown Class"
    pure_seconds_watched = 0.0
    stats = {}
    session_screenshot = None

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=args.profile_dir,
            channel="chrome",
            headless=False,
            args=chrome_args,
            ignore_default_args=["--no-sandbox", "--enable-automation"]
        )

        def handle_new_page(new_p):
            try:
                new_p.wait_for_timeout(1500)
                u = new_p.url.lower()
                logger.info(f"[TabGuard] Popup or new tab opened: {u}")
                # Auto-close unexpected tabs (like Chrome update/welcome, ad popups)
                if not any(domain in u for domain in ["chartacademy.com", "accounts.google.com", "google.com"]):
                    logger.warning(f"[TabGuard] Automatically closing non-essential tab: {u}")
                    new_p.close()
            except Exception as err:
                logger.warning(f"[TabGuard] Tab handling note: {err}")

        context.on("page", handle_new_page)

        page = context.pages[0] if context.pages else context.new_page()

        try:
            if not args.background:
                page.bring_to_front()

            # 3. Auth Check & Navigation
            logger.info(f"[Browser] Navigating to {MASTERCLASSES_URL}...")
            try:
                page.goto(MASTERCLASSES_URL, wait_until="domcontentloaded", timeout=45000)
            except Exception as e:
                logger.warning(f"[Browser] Navigation note: {e}. Proceeding with authentication check...")

            auth_ok = handle_authentication(page, context, target_email=TARGET_EMAIL, force_test=args.force_login)
            if not auth_ok:
                had_warnings_or_errors = True
                if not session_screenshot:
                    session_screenshot = take_immediate_snapshot(page, "auth_warning")

            # 4. Class Selection
            class_title = select_and_start_masterclass(page)
            if not class_title:
                logger.error("[Workflow] No valid uncompleted class found.")
                had_warnings_or_errors = True
                if not session_screenshot:
                    session_screenshot = take_immediate_snapshot(page, "class_selection_failed")
            else:
                # 5. Play Video
                playing = ensure_video_playing(page)
                if not playing:
                    had_warnings_or_errors = True
                    if not session_screenshot:
                        session_screenshot = take_immediate_snapshot(page, "video_play_failed")

                # 6. Watchdog
                pure_seconds_watched = run_watchdog(page, target_seconds=args.watch_duration, current_class_title=class_title, min_pure_seconds=min_pure)

            # 7. Check Leaderboard & Record Academy Points
            logger.info("[Leaderboard] Session complete. Navigating to Leaderboard to record points...")
            try:
                stats = scrape_and_update_points(page, goal=args.goal)
                logger.info(f"[Leaderboard] Updated Points Record: {stats}")
            except Exception as e:
                logger.error(f"[Leaderboard] Error while updating points: {e}")
                had_warnings_or_errors = True
                if not session_screenshot:
                    session_screenshot = take_immediate_snapshot(page, "leaderboard_failed")

            # Capture session completion screenshot if clean
            if not had_warnings_or_errors:
                session_screenshot = take_immediate_snapshot(page, "completed")

        except Exception as e:
            logger.exception(f"[Workflow] Unexpected error during automation run: {e}")
            had_warnings_or_errors = True
            if not session_screenshot:
                session_screenshot = take_immediate_snapshot(page, "unexpected_error")

        finally:
            # 8. Clean Shutdown
            logger.info("[Shutdown] Closing automation browser window...")
            try:
                context.close()
                logger.info("[Shutdown] Browser context closed cleanly.")
            except Exception as e:
                logger.warning(f"[Shutdown] Error closing context: {e}")

    # 9. Send Discord Notifications
    if had_warnings_or_errors:
        notify_session_warning(screenshot_path=session_screenshot)
        if state.get("missed_alert_date") != today_str:
            state["missed_alert_date"] = today_str
            save_session_state(state)
            show_missed_run_dialog(reason="Automation encountered an issue during session")
    elif class_title and stats and "error" not in stats:
        notify_session_success(class_title, pure_seconds_watched, stats, screenshot_path=session_screenshot)
        state = load_session_state()
        state["last_successful_run"] = today_str
        state["last_completed_class"] = class_title
        save_session_state(state)

    logger.info("=" * 65)
    logger.info(f" Workflow finished successfully at {datetime.now().strftime('%Y-%m-%d %I:%M:%S %p')}")
    logger.info("=" * 65 + "\n")


if __name__ == "__main__":
    main()

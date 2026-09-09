<div align="center">

# 🎓 ChartAcademy Bot

**Autonomous Daily Masterclass Watcher & Leaderboard Points Tracker**  
*Guarantees daily rewards with zero interference, pure playback accounting, and rich Discord reporting.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white)](https://microsoft.com)
[![Playwright](https://img.shields.io/badge/Engine-Playwright%20Chromium-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

<img src="data/bot_avatar.jpg" width="180" alt="ChartAcademy Bot Avatar" style="border-radius: 50%;" />

</div>

---

## 🌟 Key Features

- 🛡️ **Google Anti-Bot Bypass**: Authenticates via official Chrome native profiles. Google recognizes the browser as genuine and never blocks OAuth sign-ins.
- ⏱️ **Pure Video Playback Guarantee**: Tracks actual video delta seconds played (>= 30m 5s) instead of raw wall-clock time, ensuring buffering, network hiccups, or class switches never cost you rewards.
- 🎯 **Smart Class Selection & Auto-Advance**:
  - Automatically resumes in-progress classes (`"Continue Class"`).
  - Starts uncompleted classes while strictly skipping completed ones (`"Rewatch Class"`).
  - Automatically switches to the next masterclass when a video ends.
- 🔕 **True Background Execution**: Runs behind other windows with tab-level muting (`--mute-audio`). Video player remains unmuted to register full analytics. Zero mouse/keyboard interference.
- ⚡ **Resource Optimized**: JavaScript heap capped to 256MB, renderer process limits enforced, and GPU hardware acceleration utilized for `< 1%` CPU usage.
- 📊 **Leaderboard Scraper & Streak Tracker**: Daily scrapes Academy Points, logs progress against your 1,750-point goal, and calculates learning streaks and estimated completion dates.
- 🔔 **Trader-Aesthetic Discord Reporting**: Sends rich embeds with ASCII progress bars, active streak counters, goal projections, and attached screenshots of the completed session or alert states.
- 🎨 **High-DPI Desktop UI**: Crisp 120-second pre-run countdown cancel card and post-session points popup with real-time canvas progress bars.
- 🩺 **3-Second Health Audit**: Built-in CLI diagnostic tool to verify network, Chrome, authentication, Task Scheduler, and database integrity in seconds.

---

## 📁 Project Structure

```text
chartacademy-bot/
├── run.py                 # Primary runner (supports --health, --background, --force)
├── setup_login.py         # One-time official Chrome launcher for Google OAuth
├── schedule_task.ps1      # Windows Task Scheduler installer (11:58 AM IST daily)
├── config.example.json    # Example configuration template
├── config.json            # Active configuration (ignored by git)
├── requirements.txt       # Python dependencies (playwright)
├── SETUP.md               # Step-by-step setup and deployment guide
├── README.md              # Project documentation
├── LICENSE                # MIT License
├── src/
│   ├── bot.py             # Core automation engine & pure playback watchdog
│   ├── dialog.py          # High-DPI countdown cancel card & missed session prompt
│   ├── health.py          # 3-second system health diagnostic audit
│   ├── notify.py          # Discord notifications, progress bars, streaks & projections
│   └── points.py          # Leaderboard scraper & floating desktop summary card
├── data/
│   ├── bot_avatar.jpg     # Bot profile picture asset
│   ├── completed_classes.json   # Watched masterclasses database
│   └── points_tracker.json      # Daily points history vs 1,750 goal
└── logs/
    └── .gitkeep           # Daily rotated logs directory (30-day retention)
```

---

## 🚀 Quick Start

For detailed step-by-step instructions, see the **[Complete Setup Guide (SETUP.md)](SETUP.md)**.

### 1. Install Dependencies
```powershell
pip install -r requirements.txt
playwright install chromium
```

### 2. One-Time Google Authentication
```powershell
python setup_login.py
```
*Sign in to Google in the opened official Chrome window, then press `[ENTER]`.*

### 3. Configure
```powershell
Copy-Item config.example.json config.json
```
*Edit `config.json` with your Discord webhook URL and Google email.*

### 4. Run Diagnostic Health Audit
```powershell
python run.py --health
```

### 5. Test Run
```powershell
python run.py --skip-dialog --watch-duration 30
```

### 6. Schedule Daily Autonomous Runs
```powershell
powershell -ExecutionPolicy Bypass -File .\schedule_task.ps1
```

---

## 🎮 CLI Command Reference

| Command | Description |
|---|---|
| `python run.py --health` | Runs 3-second system diagnostic audit and displays status dashboard |
| `python run.py` | Normal interactive run with 120-second pre-run cancel prompt |
| `python run.py --background` | Runs quietly in background (used by Windows Task Scheduler) |
| `python run.py --skip-dialog` | Bypasses the 120s countdown card and starts immediately |
| `python run.py --watch-duration 30` | Runs a quick test session for 30 seconds |
| `python run.py --force` | Runs session even if already completed earlier today |
| `python setup_login.py` | Launches official Chrome to test or refresh your saved profile |

---

## 🛡️ Anti-Bot & Detection Philosophy

Standard automation frameworks fail against modern Google OAuth because of automation flags like `navigator.webdriver = true` and `--enable-automation`.

ChartAcademy Bot circumvents this entirely:
1. **Official Chrome**: Launches genuine `chrome.exe` natively using your user data directory.
2. **Flag Stripping**: Explicitly strips `--enable-automation` and `--no-sandbox`.
3. **Hardware Acceleration**: Preserves real GPU acceleration and browser fingerprinting.
4. **Natural Cadence**: Watches at standard 1.0x speed with 10-second polling intervals matching human interaction.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

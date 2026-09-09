# 🚀 ChartAcademy Bot — Complete Setup & Deployment Guide

This guide walks you step-by-step through setting up, configuring, and scheduling **ChartAcademy Bot** on Windows.

---

## 📋 Prerequisites

1. **Operating System**: Windows 10 or Windows 11 (64-bit)
2. **Python**: Python 3.10 or higher ([Download Python](https://www.python.org/downloads/))  
   *(Make sure to check "Add Python to PATH" during installation)*
3. **Google Chrome**: Official Google Chrome installed on your machine.
4. **Discord Account** *(Optional)*: For webhook status notifications.

---

## 🛠️ Step 1: Install Dependencies

Open **PowerShell** or **Command Prompt** in the project root directory and run:

```powershell
# 1. Install required Python packages
pip install -r requirements.txt

# 2. Install Playwright browser dependencies
playwright install chromium
```

---

## 🔑 Step 2: One-Time Google Authentication

Because Google blocks automated browsers ("This browser or app may not be secure"), we use our **Native Anti-Bot Bypass**:

1. Run the setup script:
   ```powershell
   python setup_login.py
   ```
2. A genuine official Google Chrome window will open.
3. Click **"Sign in with Google"** and enter your Google credentials.
4. Once you are signed in and can see your ChartAcademy masterclasses, return to your terminal and press **`[ENTER]`** (or close the browser).
5. Your session tokens, device trust, and cookies are now permanently saved in:  
   `%USERPROFILE%\.chartacademy_profile`

> [!NOTE]
> You only need to do this **once**. The bot will reuse this trusted profile for all subsequent autonomous runs.

---

## ⚙️ Step 3: Configure Settings

1. Copy the example configuration file:
   ```powershell
   Copy-Item config.example.json config.json
   ```
2. Open `config.json` in your favorite editor:
   ```json
   {
     "discord_webhook_url": "https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN",
     "google_account": "your_email@gmail.com",
     "points_goal": 1750,
     "watch_duration_minutes": 32,
     "min_pure_playback_minutes": 30.1,
     "log_retention_days": 30
   }
   ```
3. **Configuration Options**:
   - `discord_webhook_url`: Your Discord channel webhook URL. *(Leave empty `""` to disable Discord alerts)*.
   - `google_account`: Your Google email address (used by the auto-login selector).
   - `points_goal`: Target Academy Points (default: `1750`).
   - `watch_duration_minutes`: Total session duration (default: `32`).
   - `min_pure_playback_minutes`: Minimum pure video playback threshold required to earn rewards (default: `30.1`).
   - `log_retention_days`: Number of daily logs to retain before rotating out (default: `30`).

---

## 🩺 Step 4: Run System Health Check

Verify your setup with the built-in diagnostic tool:

```powershell
python run.py --health
```

You should see a clean report with `[PASS]` on:
- ChartAcademy server connection & latency
- Google Chrome installation & version
- Persistent profile cookies & authentication
- Discord webhook connectivity
- Windows Task Scheduler status

---

## 🧪 Step 5: Test Run (Dry-Run)

Test the full video playback and leaderboard scraping workflow with a quick 30-second test:

```powershell
python run.py --skip-dialog --watch-duration 30
```

- Watch Chrome launch cleanly behind your windows.
- Confirm video playback begins automatically.
- Confirm points are extracted from the leaderboard and logged.

---

## ⏰ Step 6: Register Windows Task Scheduler (Daily Runs)

To automate the bot so it runs autonomously every day at **12:00 PM IST** (with a 2-minute pre-run cancel card at **11:58 AM IST**):

Right-click PowerShell and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\schedule_task.ps1
```

### What This Configures:
- **Trigger**: Every day at **11:58 AM**.
- **Pre-Run Alert**: A 120-second floating dark card appears at 11:58 AM with a *"Cancel Today"* button. If untouched, automation starts at 12:00 PM.
- **Background Mode**: Chrome runs in background mode without stealing mouse or keyboard focus.
- **Start When Available**: If your PC was turned off at 11:58 AM, Windows automatically runs the missed session as soon as you boot.
- **Power Management**: Configured to run on battery or AC power and wake computer if sleeping.

---

## 🔔 Setting Up Discord Alerts (Optional)

1. In Discord, go to **Server Settings** (or right-click a channel ➔ **Edit Channel**).
2. Navigate to **Integrations** ➔ **Webhooks** ➔ **New Webhook**.
3. Name it **ChartAcademy Bot**.
4. *(Optional)* Click the avatar circle and upload `data/bot_avatar.jpg`.
5. Click **Copy Webhook URL** and paste it into `config.json`.

---

## ❓ Troubleshooting

- **Google asks for 2FA again?**  
  Run `python setup_login.py` to refresh your profile. Google only asks for 2FA if the profile directory was deleted or cleared.
- **Want to test manual profile access?**  
  Launch official Chrome directly with your saved profile:
  ```powershell
  & "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="$env:USERPROFILE\.chartacademy_profile" "https://app.chartacademy.com/masterclasses"
  ```
- **Task Scheduler didn't trigger?**  
  Open `taskschd.msc`, click **Task Scheduler Library**, right-click **ChartAcademyDailyWatcher**, and click **Run** to test.

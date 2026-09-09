#!/usr/bin/env python
"""
ChartAcademy Bot - Master Runner Entrypoint
Run this script to start the ChartAcademy automation.
All command-line flags are forwarded to src/bot.py.

Usage:
  python run.py                   # Normal interactive run (with 120s pre-run prompt)
  python run.py --background      # Quiet background run (used by Windows Task Scheduler)
  python run.py --skip-dialog     # Skip the 120s countdown card and start immediately
"""

import os
import sys

# Ensure src/ is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(PROJECT_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from bot import main

if __name__ == "__main__":
    main()

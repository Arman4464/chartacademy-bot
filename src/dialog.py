"""
ChartAcademy Desktop Dialogs Module
Trader-aesthetic dark mode floating prompts for:
1. 120-second pre-run countdown cancel card
2. Missed / Delayed run interactive prompt ("Start Now" or "Dismiss")
"""

import sys
import tkinter as tk
from datetime import datetime

# Enable High-DPI scaling on Windows for ultra-crisp rendering
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


def show_cancel_dialog(timeout_seconds=120, title="ChartAcademy Daily Watcher") -> bool:
    """
    Displays a sleek, modern countdown prompt in the bottom-right corner.
    Gives the trader 120 seconds to cancel or immediately start the automated watch.
    """
    proceed = True

    root = tk.Tk()
    root.title(title)
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="#0d1117")

    width = 400
    height = 160
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    pos_x = sw - width - 24
    pos_y = sh - height - 60
    root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

    # Container with crisp border
    container = tk.Frame(root, bg="#0d1117", highlightbackground="#30363d", highlightthickness=1)
    container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    # Header
    header_frame = tk.Frame(container, bg="#0d1117")
    header_frame.pack(fill=tk.X, padx=16, pady=(12, 4))

    icon_label = tk.Label(header_frame, text="⚡  ChartAcademy Automation", font=("Segoe UI", 11, "bold"), fg="#f0f6fc", bg="#0d1117")
    icon_label.pack(side=tk.LEFT)

    time_now = datetime.now().strftime("%I:%M %p")
    time_label = tk.Label(header_frame, text=time_now, font=("Segoe UI", 9), fg="#8b949e", bg="#0d1117")
    time_label.pack(side=tk.RIGHT)

    # Status text
    status_label = tk.Label(
        container,
        text=f"Session begins in {timeout_seconds}s  •  Goal: 1750 pts",
        font=("Segoe UI", 9),
        fg="#c9d1d9",
        bg="#0d1117"
    )
    status_label.pack(anchor="w", padx=16, pady=(0, 8))

    # Canvas Progress Bar
    bar_canvas = tk.Canvas(container, height=6, bg="#161b22", highlightthickness=0)
    bar_canvas.pack(fill=tk.X, padx=16, pady=(0, 14))

    total_time = timeout_seconds
    remaining = timeout_seconds

    def update_bar():
        bar_canvas.delete("all")
        canv_w = bar_canvas.winfo_width()
        if canv_w <= 1:
            canv_w = width - 32
        pct = remaining / total_time
        fill_w = max(0, int(canv_w * pct))
        bar_canvas.create_rectangle(0, 0, fill_w, 6, fill="#10b981", width=0)

    # Buttons frame
    btn_frame = tk.Frame(container, bg="#0d1117")
    btn_frame.pack(fill=tk.X, padx=16, pady=(0, 12))

    def on_cancel():
        nonlocal proceed
        proceed = False
        root.destroy()

    def on_start_now():
        nonlocal proceed
        proceed = True
        root.destroy()

    cancel_btn = tk.Button(
        btn_frame,
        text="✕  Cancel Today",
        font=("Segoe UI", 9, "bold"),
        bg="#da3633",
        fg="#ffffff",
        activebackground="#b62324",
        activeforeground="#ffffff",
        relief=tk.FLAT,
        padx=14,
        pady=5,
        cursor="hand2",
        command=on_cancel
    )
    cancel_btn.pack(side=tk.LEFT)

    start_btn = tk.Button(
        btn_frame,
        text="▶  Start Now",
        font=("Segoe UI", 9, "bold"),
        bg="#238636",
        fg="#ffffff",
        activebackground="#2ea043",
        activeforeground="#ffffff",
        relief=tk.FLAT,
        padx=16,
        pady=5,
        cursor="hand2",
        command=on_start_now
    )
    start_btn.pack(side=tk.RIGHT)

    def tick():
        nonlocal remaining
        if remaining <= 0:
            root.destroy()
            return
        remaining -= 1
        mins = remaining // 60
        secs = remaining % 60
        time_str = f"{mins}m {secs}s" if mins > 0 else f"{secs}s"
        status_label.config(text=f"Session begins in {time_str}  •  Goal: 1750 pts")
        update_bar()
        root.after(1000, tick)

    root.after(50, update_bar)
    root.after(1000, tick)
    root.mainloop()
    return proceed


def show_missed_run_dialog(reason: str = "Network offline or PC scheduled trigger delayed") -> bool:
    """
    Displays an interactive notification if a scheduled run never started or failed.
    Asks the trader: Start Session Now or Dismiss?
    Returns True if user clicks 'Start Session Now', False otherwise.
    Auto-dismisses after 60s without taking action.
    """
    start_now = False

    root = tk.Tk()
    root.title("ChartAcademy Missed Session")
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.configure(bg="#0d1117")

    width = 420
    height = 165
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    pos_x = sw - width - 24
    pos_y = sh - height - 60
    root.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

    container = tk.Frame(root, bg="#0d1117", highlightbackground="#f0883e", highlightthickness=1)
    container.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    # Header
    header_frame = tk.Frame(container, bg="#0d1117")
    header_frame.pack(fill=tk.X, padx=16, pady=(12, 4))

    icon_label = tk.Label(header_frame, text="⚠️  ChartAcademy: Missed Session", font=("Segoe UI", 11, "bold"), fg="#f0883e", bg="#0d1117")
    icon_label.pack(side=tk.LEFT)

    time_now = datetime.now().strftime("%I:%M %p")
    time_label = tk.Label(header_frame, text=time_now, font=("Segoe UI", 9), fg="#8b949e", bg="#0d1117")
    time_label.pack(side=tk.RIGHT)

    # Reason and prompt
    body_label = tk.Label(
        container,
        text=f"Today's scheduled run was delayed ({reason}).\nWould you like to begin your 32-minute session now?",
        font=("Segoe UI", 9),
        fg="#c9d1d9",
        bg="#0d1117",
        justify=tk.LEFT
    )
    body_label.pack(anchor="w", padx=16, pady=(2, 12))

    btn_frame = tk.Frame(container, bg="#0d1117")
    btn_frame.pack(fill=tk.X, padx=16, pady=(0, 10))

    def on_dismiss():
        nonlocal start_now
        start_now = False
        root.destroy()

    def on_confirm():
        nonlocal start_now
        start_now = True
        root.destroy()

    dismiss_btn = tk.Button(
        btn_frame,
        text="Dismiss",
        font=("Segoe UI", 9),
        bg="#21262d",
        fg="#8b949e",
        activebackground="#30363d",
        activeforeground="#c9d1d9",
        relief=tk.FLAT,
        padx=14,
        pady=5,
        cursor="hand2",
        command=on_dismiss
    )
    dismiss_btn.pack(side=tk.LEFT)

    confirm_btn = tk.Button(
        btn_frame,
        text="▶  Start Session Now",
        font=("Segoe UI", 9, "bold"),
        bg="#238636",
        fg="#ffffff",
        activebackground="#2ea043",
        activeforeground="#ffffff",
        relief=tk.FLAT,
        padx=16,
        pady=5,
        cursor="hand2",
        command=on_confirm
    )
    confirm_btn.pack(side=tk.RIGHT)

    # Auto-dismiss after 60s
    root.after(60000, root.destroy)
    root.mainloop()
    return start_now


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "cancel"
    if action == "missed":
        ans = show_missed_run_dialog("Network connection was offline")
        print("User answer:", ans)
    else:
        p = show_cancel_dialog(10)
        print("Proceed:", p)

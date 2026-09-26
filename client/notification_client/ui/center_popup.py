import sys
import threading
import json
import logging
import tkinter as tk
from typing import Optional, Dict, Any
from ..config import config

logger = logging.getLogger("notification_client.center_popup")

class CenterScreenAlert:
    """Displays a sleek, high-visibility notification banner in the center of the laptop screen."""
    
    @classmethod
    def show(
        cls,
        title: str,
        message: str,
        priority: str = "normal",
        source: str = "system",
        data: Optional[Dict[str, Any]] = None,
        duration: Optional[int] = None
    ):
        """Spawns center popup in a background daemon thread."""
        thread = threading.Thread(
            target=cls._create_and_run,
            args=(title, message, priority, source, data, duration),
            daemon=True
        )
        thread.start()

    @staticmethod
    def _create_and_run(
        title: str,
        message: str,
        priority: str,
        source: str,
        data: Optional[Dict[str, Any]],
        duration: Optional[int]
    ):
        try:
            root = tk.Tk()
            root.title("Notification Alert")
            root.overrideredirect(True)      # Frameless overlay
            root.attributes("-topmost", True) # Always on top of all windows

            # Color scheme tailored by priority
            priority_styles = {
                "critical": {"border": "#ef4444", "badge_bg": "#450a0a", "badge_fg": "#fca5a5", "icon": "⚠️ CRITICAL"},
                "high":     {"border": "#f59e0b", "badge_bg": "#451a03", "badge_fg": "#fcd34d", "icon": "🔔 HIGH PRIORITY"},
                "normal":   {"border": "#3b82f6", "badge_bg": "#172554", "badge_fg": "#93c5fd", "icon": "ℹ️ ALERT"},
                "low":      {"border": "#64748b", "badge_bg": "#1e293b", "badge_fg": "#cbd5e1", "icon": "📌 INFO"}
            }
            style = priority_styles.get(priority.lower(), priority_styles["normal"])

            # Outer glow / border container
            border_frame = tk.Frame(root, bg=style["border"], padx=2, pady=2)
            border_frame.pack(fill="both", expand=True)

            # Main content container
            content_frame = tk.Frame(border_frame, bg="#0f172a", padx=20, pady=16)
            content_frame.pack(fill="both", expand=True)

            # 1. Header Row: Source & Priority Badge
            header_frame = tk.Frame(content_frame, bg="#0f172a")
            header_frame.pack(fill="x", pady=(0, 10))

            src_label = tk.Label(
                header_frame,
                text=f"[{source.upper()}]",
                font=("Segoe UI", 9, "bold"),
                fg="#94a3b8",
                bg="#0f172a"
            )
            src_label.pack(side="left")

            badge_label = tk.Label(
                header_frame,
                text=f" {style['icon']} ",
                font=("Segoe UI", 8, "bold"),
                fg=style["badge_fg"],
                bg=style["badge_bg"],
                padx=8,
                pady=2
            )
            badge_label.pack(side="right")

            # 2. Title
            title_label = tk.Label(
                content_frame,
                text=title,
                font=("Segoe UI", 13, "bold"),
                fg="#f8fafc",
                bg="#0f172a",
                wraplength=480,
                justify="left",
                anchor="w"
            )
            title_label.pack(fill="x", pady=(0, 6))

            # 3. Message Body
            msg_label = tk.Label(
                content_frame,
                text=message,
                font=("Segoe UI", 10),
                fg="#cbd5e1",
                bg="#0f172a",
                wraplength=480,
                justify="left",
                anchor="w"
            )
            msg_label.pack(fill="x", pady=(0, 10))

            # 4. Optional Custom Data Preview (e.g. order details / metrics)
            if data and isinstance(data, dict) and len(data) > 0:
                data_box = tk.Frame(content_frame, bg="#090d16", padx=10, pady=8)
                data_box.pack(fill="x", pady=(0, 12))
                
                data_str = "\n".join([f"{k}: {v}" for k, v in list(data.items())[:4]])
                data_label = tk.Label(
                    data_box,
                    text=data_str,
                    font=("Consolas", 8),
                    fg="#38bdf8",
                    bg="#090d16",
                    justify="left",
                    anchor="w"
                )
                data_label.pack(fill="x")

            # 5. Footer: Dismiss Button & Auto-Close Timer
            footer_frame = tk.Frame(content_frame, bg="#0f172a")
            footer_frame.pack(fill="x", pady=(6, 0))

            timeout = duration or config.duration_seconds
            timer_text = tk.StringVar(value=f"Closing in {timeout}s...")

            timer_label = tk.Label(
                footer_frame,
                textvariable=timer_text,
                font=("Segoe UI", 8),
                fg="#64748b",
                bg="#0f172a"
            )
            timer_label.pack(side="left")

            dismiss_btn = tk.Button(
                footer_frame,
                text="Dismiss (Esc)",
                font=("Segoe UI", 9, "bold"),
                fg="#f8fafc",
                bg="#334155",
                activebackground="#475569",
                activeforeground="#ffffff",
                relief="flat",
                padx=14,
                pady=4,
                cursor="hand2",
                command=root.destroy
            )
            dismiss_btn.pack(side="right")

            # Geometry & Positioning: Center of screen
            root.update_idletasks()
            w = max(520, root.winfo_reqwidth())
            h = root.winfo_reqheight()
            
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            x = (sw - w) // 2
            y = (sh - h) // 2
            root.geometry(f"{w}x{h}+{x}+{y}")

            # Keyboard and click bindings to dismiss
            root.bind("<Escape>", lambda e: root.destroy())
            root.bind("<Return>", lambda e: root.destroy())
            root.bind("<space>", lambda e: root.destroy())
            content_frame.bind("<Button-1>", lambda e: root.destroy())

            # Countdown timer
            remaining = [timeout]
            def countdown():
                if remaining[0] <= 1:
                    try: root.destroy()
                    except: pass
                else:
                    remaining[0] -= 1
                    timer_text.set(f"Closing in {remaining[0]}s...")
                    root.after(1000, countdown)

            root.after(1000, countdown)
            root.mainloop()

        except Exception as e:
            logger.error(f"Error displaying center screen alert: {e}")

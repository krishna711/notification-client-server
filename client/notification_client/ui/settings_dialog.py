import threading
import logging
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from ..config import config

logger = logging.getLogger("notification_client.settings")

class SettingsDialog:
    """Settings GUI to configure Gateway Server URL, auth credentials, and notification styles."""

    @classmethod
    def open(cls, on_save_callback: Optional[Callable[[], None]] = None):
        """Open settings dialog in a background thread."""
        t = threading.Thread(target=cls._run_dialog, args=(on_save_callback,), daemon=True)
        t.start()

    @staticmethod
    def _run_dialog(on_save_callback: Optional[Callable[[], None]]):
        root = tk.Tk()
        root.title("Notification Client - Settings")
        root.geometry("540x520")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg="#0f172a")

        # Styling
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure styles
        style.configure("TLabel", background="#0f172a", foreground="#f8fafc", font=("Segoe UI", 9))
        style.configure("Header.TLabel", font=("Segoe UI", 12, "bold"), foreground="#38bdf8")
        style.configure("Sub.TLabel", font=("Segoe UI", 8), foreground="#94a3b8")
        style.configure("TRadiobutton", background="#0f172a", foreground="#e2e8f0", font=("Segoe UI", 9))
        style.configure("TCheckbutton", background="#0f172a", foreground="#e2e8f0", font=("Segoe UI", 9))

        main_frame = tk.Frame(root, bg="#0f172a", padx=24, pady=20)
        main_frame.pack(fill="both", expand=True)

        # Header
        tk.Label(
            main_frame,
            text="⚙ Notification Gateway Settings",
            font=("Segoe UI", 14, "bold"),
            fg="#f8fafc",
            bg="#0f172a"
        ).pack(anchor="w", pady=(0, 2))

        tk.Label(
            main_frame,
            text="Configure server endpoint and desktop alert behavior.",
            font=("Segoe UI", 8),
            fg="#94a3b8",
            bg="#0f172a"
        ).pack(anchor="w", pady=(0, 16))

        # 1. Gateway Server URL
        tk.Label(
            main_frame,
            text="GATEWAY SERVER URL (LOCAL OR PRODUCTION)",
            font=("Segoe UI", 8, "bold"),
            fg="#94a3b8",
            bg="#0f172a"
        ).pack(anchor="w", pady=(4, 2))

        url_var = tk.StringVar(value=config.server_url)
        url_entry = tk.Entry(
            main_frame,
            textvariable=url_var,
            font=("Segoe UI", 10),
            bg="#1e293b",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#334155",
            highlightcolor="#3b82f6"
        )
        url_entry.pack(fill="x", ipady=6, pady=(0, 4))
        
        tk.Label(
            main_frame,
            text="e.g. http://localhost:8000 (Local) or https://notify.yourdomain.com (Production)",
            font=("Segoe UI", 7),
            fg="#64748b",
            bg="#0f172a"
        ).pack(anchor="w", pady=(0, 12))

        # 2. Device Auth Token
        tk.Label(
            main_frame,
            text="DEVICE AUTH TOKEN / SECRET",
            font=("Segoe UI", 8, "bold"),
            fg="#94a3b8",
            bg="#0f172a"
        ).pack(anchor="w", pady=(4, 2))

        token_var = tk.StringVar(value=config.device_token)
        token_entry = tk.Entry(
            main_frame,
            textvariable=token_var,
            font=("Segoe UI", 10),
            bg="#1e293b",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#334155",
            highlightcolor="#3b82f6"
        )
        token_entry.pack(fill="x", ipady=6, pady=(0, 12))

        # 3. Notification Display Style
        tk.Label(
            main_frame,
            text="NOTIFICATION DISPLAY STYLE",
            font=("Segoe UI", 8, "bold"),
            fg="#94a3b8",
            bg="#0f172a"
        ).pack(anchor="w", pady=(4, 4))

        style_var = tk.StringVar(value=config.notification_style)
        
        style_frame = tk.Frame(main_frame, bg="#1e293b", padx=12, pady=10, highlightthickness=1, highlightbackground="#334155")
        style_frame.pack(fill="x", pady=(0, 14))

        r1 = tk.Radiobutton(
            style_frame,
            text="🎯 Center Screen Banner (High Focus Overlay)",
            variable=style_var,
            value="center",
            bg="#1e293b",
            fg="#f8fafc",
            selectcolor="#0f172a",
            activebackground="#1e293b",
            activeforeground="#38bdf8",
            font=("Segoe UI", 9)
        )
        r1.pack(anchor="w", pady=2)

        r2 = tk.Radiobutton(
            style_frame,
            text="🪟 Windows Toast (Bottom-Right Corner)",
            variable=style_var,
            value="toast",
            bg="#1e293b",
            fg="#f8fafc",
            selectcolor="#0f172a",
            activebackground="#1e293b",
            activeforeground="#38bdf8",
            font=("Segoe UI", 9)
        )
        r2.pack(anchor="w", pady=2)

        r3 = tk.Radiobutton(
            style_frame,
            text="🔀 Both (Center Screen Banner + Windows Toast)",
            variable=style_var,
            value="both",
            bg="#1e293b",
            fg="#f8fafc",
            selectcolor="#0f172a",
            activebackground="#1e293b",
            activeforeground="#38bdf8",
            font=("Segoe UI", 9)
        )
        r3.pack(anchor="w", pady=2)

        # 4. Duration & Sound Options
        opts_frame = tk.Frame(main_frame, bg="#0f172a")
        opts_frame.pack(fill="x", pady=(0, 16))

        sound_var = tk.BooleanVar(value=config.enable_sound)
        sound_chk = tk.Checkbutton(
            opts_frame,
            text="🔊 Play Notification Sound",
            variable=sound_var,
            bg="#0f172a",
            fg="#f8fafc",
            selectcolor="#1e293b",
            activebackground="#0f172a",
            activeforeground="#38bdf8",
            font=("Segoe UI", 9)
        )
        sound_chk.pack(side="left")

        duration_frame = tk.Frame(opts_frame, bg="#0f172a")
        duration_frame.pack(side="right")
        tk.Label(duration_frame, text="Duration: ", font=("Segoe UI", 9), fg="#94a3b8", bg="#0f172a").pack(side="left")
        
        duration_var = tk.IntVar(value=config.duration_seconds)
        duration_spin = tk.Spinbox(
            duration_frame,
            from_=3,
            to=30,
            textvariable=duration_var,
            width=4,
            bg="#1e293b",
            fg="#ffffff",
            buttonbackground="#334155"
        )
        duration_spin.pack(side="left")
        tk.Label(duration_frame, text=" sec", font=("Segoe UI", 9), fg="#94a3b8", bg="#0f172a").pack(side="left")

        # 5. Buttons
        btn_frame = tk.Frame(main_frame, bg="#0f172a")
        btn_frame.pack(fill="x", pady=(8, 0))

        def save_and_close():
            new_url = url_var.get().strip()
            new_token = token_var.get().strip()
            new_style = style_var.get()
            new_sound = sound_var.get()
            try:
                new_dur = int(duration_var.get())
            except ValueError:
                new_dur = 7

            config.update(
                server_url=new_url,
                device_token=new_token,
                notification_style=new_style,
                enable_sound=new_sound,
                duration_seconds=new_dur
            )

            root.destroy()
            if on_save_callback:
                on_save_callback()

        save_btn = tk.Button(
            btn_frame,
            text="💾 Save & Reconnect",
            font=("Segoe UI", 10, "bold"),
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            activeforeground="#ffffff",
            relief="flat",
            padx=18,
            pady=7,
            cursor="hand2",
            command=save_and_close
        )
        save_btn.pack(side="right")

        cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            font=("Segoe UI", 10),
            bg="#334155",
            fg="#cbd5e1",
            activebackground="#475569",
            activeforeground="#ffffff",
            relief="flat",
            padx=14,
            pady=7,
            cursor="hand2",
            command=root.destroy
        )
        cancel_btn.pack(side="right", padx=(0, 10))

        # Center dialog window on screen
        root.update_idletasks()
        w = root.winfo_reqwidth()
        h = root.winfo_reqheight()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        root.geometry(f"{w}x{h}+{x}+{y}")

        root.mainloop()

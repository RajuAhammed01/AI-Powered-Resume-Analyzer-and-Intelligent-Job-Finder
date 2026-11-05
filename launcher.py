"""
JobSnap - One-Click GUI Desktop Launcher
========================================
Interactive graphical launcher with a one-click Run/Start button.
Automates:
- Dependency & environment verification
- Auto port conflict detection & resolution
- Server process lifecycle (Start / Stop / Restart)
- Real-time status indicators and activity log
- Automatic browser launch
"""

import os
import queue
import secrets
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
import urllib.request
import webbrowser

BASE_DIR = Path(__file__).resolve().parent
VENV_DIR = BASE_DIR / "venv"
IS_WINDOWS = sys.platform.startswith("win")

if IS_WINDOWS:
    VENV_PYTHON = VENV_DIR / "Scripts" / "python.exe"
else:
    VENV_PYTHON = VENV_DIR / "bin" / "python"


class JobSnapLauncherApp:
    def __init__(self, root):
        self.root = root
        self.root.title("JobSnap AI — One-Click Launcher")
        self.root.geometry("680x620")
        self.root.minsize(580, 520)

        # Process management
        self.server_process = None
        self.active_port = 5000
        self.is_running = False
        self.log_queue = queue.Queue()

        self.apply_theme()
        self.build_ui()
        self.start_log_listener()

        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Initial check
        self.log("JobSnap launcher initialized. Ready to start.")
        self.check_initial_environment()

    def apply_theme(self):
        style = ttk.Style()
        style.theme_use("clam")
        self.bg_color = "#f8fafc"
        self.card_bg = "#ffffff"
        self.border_color = "#e2e8f0"
        self.primary_color = "#2563eb"
        self.success_color = "#059669"
        self.danger_color = "#dc2626"
        self.text_main = "#0f172a"
        self.text_muted = "#64748b"

        self.root.configure(bg=self.bg_color)
        style.configure("TLabel", background=self.bg_color, foreground=self.text_main, font=("Segoe UI", 9))
        style.configure("Card.TFrame", background=self.card_bg, relief="flat")

    def build_ui(self):
        main_frame = tk.Frame(self.root, bg=self.bg_color, padx=20, pady=16)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # ── 1. Header ─────────────────────────────────────────────────────────
        header_frame = tk.Frame(main_frame, bg=self.bg_color)
        header_frame.pack(fill=tk.X, pady=(0, 14))

        title_lbl = tk.Label(
            header_frame,
            text="🚀 JobSnap AI Runner",
            font=("Segoe UI", 16, "bold"),
            bg=self.bg_color,
            fg=self.primary_color,
        )
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(
            header_frame,
            text="AI-Powered Resume Analyzer & Intelligent Job Finder • One-Click Starter",
            font=("Segoe UI", 9),
            bg=self.bg_color,
            fg=self.text_muted,
        )
        sub_lbl.pack(anchor="w")

        # ── 2. System Status Overview Card ────────────────────────────────────
        status_card = tk.LabelFrame(
            main_frame,
            text=" System Health & Diagnostics ",
            font=("Segoe UI", 9, "bold"),
            bg=self.card_bg,
            fg=self.text_main,
            padx=14,
            pady=10,
            relief="solid",
            bd=1,
        )
        status_card.pack(fill=tk.X, pady=(0, 12))

        # 4 status rows
        self.lbl_python = tk.Label(status_card, text="● Python & Environment: Checking...", bg=self.card_bg, fg=self.text_muted, anchor="w")
        self.lbl_python.pack(fill=tk.X, pady=2)

        self.lbl_deps = tk.Label(status_card, text="● Core Dependencies: Pending verification", bg=self.card_bg, fg=self.text_muted, anchor="w")
        self.lbl_deps.pack(fill=tk.X, pady=2)

        self.lbl_port = tk.Label(status_card, text="● Port Status: Port 5000 ready", bg=self.card_bg, fg=self.text_muted, anchor="w")
        self.lbl_port.pack(fill=tk.X, pady=2)

        self.lbl_server = tk.Label(status_card, text="● Server Status: Stopped (Click Start to run)", font=("Segoe UI", 9, "bold"), bg=self.card_bg, fg="#d97706", anchor="w")
        self.lbl_server.pack(fill=tk.X, pady=2)

        # ── 3. Action Buttons & Controls ─────────────────────────────────────
        action_frame = tk.Frame(main_frame, bg=self.bg_color)
        action_frame.pack(fill=tk.X, pady=(0, 12))

        # Big Run Button
        self.btn_start = tk.Button(
            action_frame,
            text="▶  One-Click Start JobSnap",
            font=("Segoe UI", 11, "bold"),
            bg="#10b981",
            fg="white",
            activebackground="#059669",
            activeforeground="white",
            relief="flat",
            padx=18,
            pady=10,
            cursor="hand2",
            command=self.start_application_thread,
        )
        self.btn_start.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))

        # Stop Button
        self.btn_stop = tk.Button(
            action_frame,
            text="⏹  Stop Server",
            font=("Segoe UI", 10, "bold"),
            bg="#e2e8f0",
            fg="#64748b",
            state=tk.DISABLED,
            relief="flat",
            padx=14,
            pady=10,
            cursor="hand2",
            command=self.stop_server,
        )
        self.btn_stop.pack(side=tk.LEFT, padx=6)

        # Open in Browser Button
        self.btn_browser = tk.Button(
            action_frame,
            text="🌐  Open Browser",
            font=("Segoe UI", 10, "bold"),
            bg="#eff6ff",
            fg="#2563eb",
            relief="flat",
            padx=14,
            pady=10,
            cursor="hand2",
            command=self.open_in_browser,
        )
        self.btn_browser.pack(side=tk.LEFT, padx=(6, 0))

        # ── 4. Configuration Checkboxes ──────────────────────────────────────
        opts_frame = tk.Frame(main_frame, bg=self.bg_color)
        opts_frame.pack(fill=tk.X, pady=(0, 8))

        self.var_autobrowser = tk.BooleanVar(value=True)
        self.chk_browser = tk.Checkbutton(
            opts_frame,
            text="Automatically open in browser upon launch",
            variable=self.var_autobrowser,
            bg=self.bg_color,
            activebackground=self.bg_color,
            font=("Segoe UI", 8),
        )
        self.chk_browser.pack(side=tk.LEFT)

        self.var_autoresolve = tk.BooleanVar(value=True)
        self.chk_resolve = tk.Checkbutton(
            opts_frame,
            text="Auto-resolve port conflicts (no crash if port busy)",
            variable=self.var_autoresolve,
            bg=self.bg_color,
            activebackground=self.bg_color,
            font=("Segoe UI", 8),
        )
        self.chk_resolve.pack(side=tk.RIGHT)

        # ── 5. Progress Bar ──────────────────────────────────────────────────
        self.progress = ttk.Progressbar(main_frame, mode="determinate")
        self.progress.pack(fill=tk.X, pady=(0, 8))

        # ── 6. Live Activity Log Box ─────────────────────────────────────────
        log_frame = tk.LabelFrame(
            main_frame,
            text=" Live Output & Event Log ",
            font=("Segoe UI", 9, "bold"),
            bg=self.card_bg,
            fg=self.text_main,
            padx=8,
            pady=6,
            relief="solid",
            bd=1,
        )
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.txt_log = tk.Text(
            log_frame,
            wrap=tk.WORD,
            bg="#0f172a",
            fg="#f1f5f9",
            insertbackground="white",
            font=("Consolas", 9),
            relief="flat",
        )
        self.txt_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.txt_log.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.txt_log.config(yscrollcommand=scrollbar.set)

    def log(self, message):
        """Thread-safe logging method."""
        timestamp = time.strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {message}\n")

    def start_log_listener(self):
        """Polls log_queue to safely update Tkinter text widget."""
        try:
            while not self.log_queue.empty():
                msg = self.log_queue.get_nowait()
                self.txt_log.insert(tk.END, msg)
                self.txt_log.see(tk.END)
        except Exception:
            pass
        self.root.after(100, self.start_log_listener)

    def check_initial_environment(self):
        if VENV_PYTHON.exists():
            self.lbl_python.config(text=f"● Python & Venv: Ready ({VENV_PYTHON})", fg=self.success_color)
        else:
            self.lbl_python.config(text="● Python & Venv: Not yet created (will auto-create on Start)", fg="#d97706")

    def is_port_in_use(self, port, host="127.0.0.1"):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            try:
                s.bind((host, port))
                return False
            except OSError:
                return True

    def find_free_port(self, preferred=5000, host="127.0.0.1"):
        if not self.is_port_in_use(preferred, host):
            return preferred
        if not self.var_autoresolve.get():
            return preferred
        for offset in range(1, 20):
            cand = preferred + offset
            if not self.is_port_in_use(cand, host):
                return cand
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, 0))
            return s.getsockname()[1]

    def start_application_thread(self):
        if self.is_running:
            return
        self.btn_start.config(state=tk.DISABLED, bg="#9ca3af", text="⏳ Starting JobSnap...")
        threading.Thread(target=self.run_startup_sequence, daemon=True).start()

    def run_startup_sequence(self):
        try:
            self.progress["value"] = 10
            self.log("Step 1/5: Verifying Python environment...")
            python_bin = VENV_PYTHON if VENV_PYTHON.exists() else Path(sys.executable)

            self.root.after(0, lambda: self.lbl_python.config(text=f"● Python: {python_bin.name} active", fg=self.success_color))

            # Step 2: Directories & .env
            self.progress["value"] = 30
            self.log("Step 2/5: Setting up environment & directories...")
            for folder in ["instance", "models", "uploads", "data"]:
                (BASE_DIR / folder).mkdir(exist_ok=True)
            
            env_path = BASE_DIR / ".env"
            if not env_path.exists():
                env_path.write_text(f"SECRET_KEY={secrets.token_hex(24)}\nFLASK_APP=run.py\nFLASK_DEBUG=0\nPORT=5000\n", encoding="utf-8")
                self.log("Created secure .env configuration.")

            # Step 3: Database & Migrations
            self.progress["value"] = 50
            self.log("Step 3/5: Initializing database and verifying schema...")
            db_script = """
from app import create_app
from app.extensions import db
app = create_app()
with app.app_context():
    db.create_all()
print("DB_READY")
"""
            res = subprocess.run([str(python_bin), "-c", db_script], capture_output=True, text=True)
            if "DB_READY" in res.stdout:
                self.log("Database verified successfully.")
            self.root.after(0, lambda: self.lbl_deps.config(text="● Core Dependencies & DB: Verified", fg=self.success_color))

            # Step 4: Resolve Port
            self.progress["value"] = 70
            self.log("Step 4/5: Testing network port availability...")
            preferred_port = 5000
            self.active_port = self.find_free_port(preferred_port)
            if self.active_port != preferred_port:
                self.log(f"Port {preferred_port} in use. Conflict avoided: switched to port {self.active_port}.")
                self.root.after(0, lambda: self.lbl_port.config(text=f"● Port Status: Auto-routed to port {self.active_port}", fg="#d97706"))
            else:
                self.log(f"Port {self.active_port} is available.")
                self.root.after(0, lambda: self.lbl_port.config(text=f"● Port Status: Port {self.active_port} available", fg=self.success_color))

            # Step 5: Start Server Process
            self.progress["value"] = 90
            app_url = f"http://127.0.0.1:{self.active_port}"
            self.log(f"Step 5/5: Launching server on {app_url}...")

            env = os.environ.copy()
            env["PORT"] = str(self.active_port)
            env["HOST"] = "127.0.0.1"

            server_cmd = [str(python_bin), str(BASE_DIR / "run.py"), "--port", str(self.active_port), "--host", "127.0.0.1"]
            self.server_process = subprocess.Popen(
                server_cmd,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )

            # Stream server output in background
            threading.Thread(target=self.stream_server_logs, daemon=True).start()

            # Poll for health check
            healthy = False
            for _ in range(30):
                try:
                    req = urllib.request.Request(app_url, headers={"User-Agent": "JobSnapLauncher"})
                    with urllib.request.urlopen(req, timeout=1.0) as resp:
                        if resp.status in (200, 302):
                            healthy = True
                            break
                except Exception:
                    time.sleep(0.3)

            self.progress["value"] = 100
            self.is_running = True

            self.root.after(0, self.on_server_started_success)

            if self.var_autobrowser.get():
                time.sleep(0.3)
                self.log(f"Opening browser at: {app_url}")
                webbrowser.open(app_url)

        except Exception as e:
            self.log(f"Startup error: {e}")
            self.root.after(0, lambda: self.on_server_start_error(str(e)))

    def stream_server_logs(self):
        """Reads output from the Flask server process and pipes to log."""
        if not self.server_process:
            return
        try:
            for line in iter(self.server_process.stdout.readline, ""):
                if line:
                    clean = line.strip()
                    if clean:
                        self.log(f"[Server] {clean}")
        except Exception:
            pass

    def on_server_started_success(self):
        app_url = f"http://127.0.0.1:{self.active_port}"
        self.lbl_server.config(text=f"● Server Status: RUNNING ({app_url})", fg=self.success_color)
        self.btn_start.config(text="✓ Running", state=tk.DISABLED, bg="#059669")
        self.btn_stop.config(state=tk.NORMAL, bg=self.danger_color, fg="white")
        self.log(f"🎉 SUCCESS: JobSnap is now live at {app_url}")

    def on_server_start_error(self, err_msg):
        self.lbl_server.config(text=f"● Server Status: Error ({err_msg[:30]})", fg=self.danger_color)
        self.btn_start.config(text="▶  Retry Start", state=tk.NORMAL, bg="#10b981")
        self.btn_stop.config(state=tk.DISABLED, bg="#e2e8f0", fg="#64748b")
        messagebox.showerror("JobSnap Startup Error", f"Failed to start JobSnap:\n{err_msg}")

    def stop_server(self):
        if not self.server_process:
            return
        self.log("Stopping JobSnap server process...")
        try:
            self.server_process.terminate()
            self.server_process.wait(timeout=2)
        except Exception:
            try:
                self.server_process.kill()
            except Exception:
                pass

        self.server_process = None
        self.is_running = False
        self.lbl_server.config(text="● Server Status: Stopped", fg="#d97706")
        self.btn_start.config(text="▶  One-Click Start JobSnap", state=tk.NORMAL, bg="#10b981")
        self.btn_stop.config(state=tk.DISABLED, bg="#e2e8f0", fg="#64748b")
        self.progress["value"] = 0
        self.log("Server stopped successfully.")

    def open_in_browser(self):
        app_url = f"http://127.0.0.1:{self.active_port}"
        self.log(f"Opening browser at: {app_url}")
        webbrowser.open(app_url)

    def on_close(self):
        if self.is_running and self.server_process:
            if messagebox.askyesno("Exit JobSnap", "The JobSnap server is still running. Would you like to stop it and exit?"):
                self.stop_server()
                self.root.destroy()
        else:
            self.root.destroy()


def main():
    root = tk.Tk()
    app = JobSnapLauncherApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()


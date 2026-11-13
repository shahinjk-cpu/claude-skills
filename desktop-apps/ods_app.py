import os
import sys
import threading
import queue
import time
import subprocess
import webbrowser
from dotenv import load_dotenv

# Try to load any local environment variables
ENV_PATH = r"C:\Users\sahin\.gemini\antigravity\scratch\repos\ODS\ods\.env"
if os.path.isfile(ENV_PATH):
    load_dotenv(ENV_PATH)

import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ODSApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🌌 Osmantic ODS V3 — Sovereign Private AI Server")
        self.geometry("1020x740")
        self.minsize(880, 620)

        self.worker_thread = None
        self.is_running = False
        self.log_queue = queue.Queue()

        # Ports
        self.dashboard_port = os.environ.get("DASHBOARD_PORT", "3021")
        self.webui_port = os.environ.get("WEBUI_PORT", "3000")
        self.litellm_port = os.environ.get("LITELLM_PORT", "4000")

        self.setup_ui()
        self.check_log_queue()
        
        # Initial status check in background
        self.run_command_async("ods status", "Sistem statusu yoxlanılır...")

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header Frame
        header = ctk.CTkFrame(self, height=65, corner_radius=0, fg_color="#13161c")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        header.grid_columnconfigure(0, weight=1)

        title_box = ctk.CTkFrame(header, fg_color="transparent")
        title_box.grid(row=0, column=0, sticky="w", padx=20, pady=10)

        ctk.CTkLabel(
            title_box,
            text="🌌 OSMANTIC ODS V3",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#f59e0b"
        ).pack(side="left")

        ctk.CTkLabel(
            title_box,
            text=" | Sovereign AI Homelab",
            font=ctk.CTkFont(size=14),
            text_color="#94a3b8"
        ).pack(side="left", padx=(5, 0))

        # Right status badge in header
        status_box = ctk.CTkFrame(header, fg_color="transparent")
        status_box.grid(row=0, column=1, sticky="e", padx=20, pady=10)

        self.status_badge = ctk.CTkLabel(
            status_box,
            text="🟢 WSL2 & Docker Aktiv",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#10b981"
        )
        self.status_badge.pack(side="right")

        # Left Sidebar (Controls & Navigation)
        sidebar = ctk.CTkFrame(self, width=320, corner_radius=10, fg_color="#1a1e27")
        sidebar.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        sidebar.grid_columnconfigure(0, weight=1)

        # Quick Links Section
        ctk.CTkLabel(
            sidebar,
            text="🌐 Portallar & Veb İnterfeyslər",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#e2e8f0"
        ).pack(padx=15, pady=(15, 8), anchor="w")

        btn_portal = ctk.CTkButton(
            sidebar,
            text="🚀 Pixel Agent Portalı",
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            font=ctk.CTkFont(weight="bold"),
            command=self.open_portal
        )
        btn_portal.pack(padx=15, pady=4, fill="x")

        btn_dashboard = ctk.CTkButton(
            sidebar,
            text="🖥️ ODS Homelab Dashboard",
            fg_color="#3b82f6",
            hover_color="#2563eb",
            font=ctk.CTkFont(weight="bold"),
            command=self.open_dashboard
        )
        btn_dashboard.pack(padx=15, pady=4, fill="x")

        btn_webui = ctk.CTkButton(
            sidebar,
            text="💬 Open WebUI (Çat)",
            fg_color="#06b6d4",
            hover_color="#0891b2",
            font=ctk.CTkFont(weight="bold"),
            command=self.open_webui
        )
        btn_webui.pack(padx=15, pady=4, fill="x")

        # Server Control Section
        ctk.CTkLabel(
            sidebar,
            text="⚙️ Server Əməliyyatları",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#e2e8f0"
        ).pack(padx=15, pady=(20, 8), anchor="w")

        btn_start = ctk.CTkButton(
            sidebar,
            text="▶️ ODS Stack Başlat",
            fg_color="#10b981",
            hover_color="#059669",
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self.run_command_async("ods start", "ODS xidmətləri başladılır...")
        )
        btn_start.pack(padx=15, pady=4, fill="x")

        btn_stop = ctk.CTkButton(
            sidebar,
            text="⏹️ ODS Stack Dayandır",
            fg_color="#ef4444",
            hover_color="#dc2626",
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self.run_command_async("ods stop", "ODS xidmətləri dayandırılır...")
        )
        btn_stop.pack(padx=15, pady=4, fill="x")

        btn_restart = ctk.CTkButton(
            sidebar,
            text="🔄 Stack Yenidən Başlat",
            fg_color="#f59e0b",
            hover_color="#d97706",
            font=ctk.CTkFont(weight="bold"),
            command=lambda: self.run_command_async("ods restart", "ODS xidmətləri yenidən başladılır...")
        )
        btn_restart.pack(padx=15, pady=4, fill="x")

        btn_status = ctk.CTkButton(
            sidebar,
            text="📊 Status & Telemetriya",
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self.run_command_async("ods status", "Xidmətlərin vəziyyəti oxunur...")
        )
        btn_status.pack(padx=15, pady=4, fill="x")

        btn_doctor = ctk.CTkButton(
            sidebar,
            text="🩺 ODS Doctor Diaqnostika",
            fg_color="#334155",
            hover_color="#475569",
            command=lambda: self.run_command_async("ods doctor", "Sistem diaqnostikası aparılır...")
        )
        btn_doctor.pack(padx=15, pady=4, fill="x")

        # System Hardware Info Card
        info_card = ctk.CTkFrame(sidebar, fg_color="#11141b", corner_radius=8)
        info_card.pack(padx=15, pady=(20, 10), fill="x")

        ctk.CTkLabel(info_card, text="💻 Avadanlıq Profili", font=ctk.CTkFont(size=12, weight="bold"), text_color="#94a3b8").pack(padx=10, pady=(8, 2), anchor="w")
        ctk.CTkLabel(info_card, text="CPU: Intel Core Ultra 7 155H", font=ctk.CTkFont(size=11), text_color="#cbd5e1").pack(padx=10, pady=1, anchor="w")
        ctk.CTkLabel(info_card, text="RAM: 16 GB | NPU: Intel AI Boost", font=ctk.CTkFont(size=11), text_color="#cbd5e1").pack(padx=10, pady=1, anchor="w")
        ctk.CTkLabel(info_card, text="OS: Windows 11 + WSL2 Ubuntu", font=ctk.CTkFont(size=11), text_color="#cbd5e1").pack(padx=10, pady=(1, 8), anchor="w")

        # Right Main Panel (Console & Execution)
        main_panel = ctk.CTkFrame(self, corner_radius=10, fg_color="#1e232d")
        main_panel.grid(row=1, column=1, sticky="nsew", padx=(0, 15), pady=15)
        main_panel.grid_columnconfigure(0, weight=1)
        main_panel.grid_rowconfigure(1, weight=1)

        # Console Header
        console_hdr = ctk.CTkFrame(main_panel, fg_color="transparent")
        console_hdr.grid(row=0, column=0, sticky="ew", padx=15, pady=(12, 6))
        console_hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            console_hdr,
            text="📜 Canlı Konsol & ODS Terminalı",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="#e2e8f0"
        ).grid(row=0, column=0, sticky="w")

        btn_clear = ctk.CTkButton(
            console_hdr,
            text="Təmizlə",
            width=80,
            height=28,
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.clear_console
        )
        btn_clear.grid(row=0, column=1, sticky="e")

        # Console Output Box
        self.console = ctk.CTkTextbox(
            main_panel,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#0d1117",
            text_color="#58a6ff"
        )
        self.console.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 10))

        # Command Input Bar
        cmd_bar = ctk.CTkFrame(main_panel, fg_color="transparent")
        cmd_bar.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 15))
        cmd_bar.grid_columnconfigure(0, weight=1)

        self.cmd_entry = ctk.CTkEntry(
            cmd_bar,
            placeholder_text="ODS və ya Docker əmri daxil edin (məs: ods status, ods logs -n 20, docker ps)...",
            font=ctk.CTkFont(family="Consolas", size=13),
            height=38
        )
        self.cmd_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.cmd_entry.bind("<Return>", lambda event: self.execute_custom_cmd())

        self.btn_exec = ctk.CTkButton(
            cmd_bar,
            text="İcra Et",
            width=100,
            height=38,
            fg_color="#3b82f6",
            hover_color="#2563eb",
            font=ctk.CTkFont(weight="bold"),
            command=self.execute_custom_cmd
        )
        self.btn_exec.grid(row=0, column=1)

    def log(self, message):
        self.log_queue.put(message)

    def check_log_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.console.insert("end", msg + "\n")
            self.console.see("end")
        self.after(100, self.check_log_queue)

    def clear_console(self):
        self.console.delete("1.0", "end")

    def open_portal(self):
        url = f"http://localhost:{self.dashboard_port}/pixel"
        self.log(f"[Browser] Açılır: {url}")
        webbrowser.open(url)

    def open_dashboard(self):
        url = f"http://localhost:{self.dashboard_port}"
        self.log(f"[Browser] Açılır: {url}")
        webbrowser.open(url)

    def open_webui(self):
        url = f"http://localhost:{self.webui_port}"
        self.log(f"[Browser] Açılır: {url}")
        webbrowser.open(url)

    def execute_custom_cmd(self):
        cmd = self.cmd_entry.get().strip()
        if not cmd:
            return
        self.cmd_entry.delete(0, "end")
        self.run_command_async(cmd, f"Əmr icra edilir: {cmd}")

    def run_command_async(self, cmd, banner=""):
        if self.is_running:
            self.log("[Xəbərdarlıq] Başqa bir əmr hazırda icra olunur, zəhmət olmasa gözləyin...")
            return

        def task():
            self.is_running = True
            if banner:
                self.log(f"\n=======================================================")
                self.log(f"▶ {banner}")
                self.log(f"=======================================================\n")
            try:
                # Wrap command with wsl -d Ubuntu
                if not cmd.startswith("wsl"):
                    full_cmd = f'wsl -d Ubuntu -e bash -l -c "PATH=$HOME/ods:$PATH {cmd}"'
                else:
                    full_cmd = cmd

                proc = subprocess.Popen(
                    full_cmd,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                for line in iter(proc.stdout.readline, ''):
                    if line:
                        self.log(line.rstrip())

                proc.stdout.close()
                proc.wait()
                self.log(f"\n[Tamamlandı] Çıxış kodu: {proc.returncode}")
            except Exception as e:
                self.log(f"[Xəta] {str(e)}")
            finally:
                self.is_running = False

        self.worker_thread = threading.Thread(target=task, daemon=True)
        self.worker_thread.start()

if __name__ == "__main__":
    app = ODSApp()
    app.mainloop()

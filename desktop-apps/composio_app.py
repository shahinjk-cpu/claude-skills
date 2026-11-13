import os
import sys
import threading
import subprocess
import queue
from dotenv import load_dotenv

COMP_DIR = r"C:\Users\sahin\.gemini\antigravity\scratch\repos\composio"
ENV_PATH = os.path.join(COMP_DIR, ".env")
if os.path.isfile(ENV_PATH):
    load_dotenv(ENV_PATH)

import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

class ComposioDesktopApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🔌 Composio Desktop Hub — 1000+ App Toolkits & Agent İnteqrasiyası")
        self.geometry("980x720")
        self.minsize(860, 600)

        self.is_running = False
        self.log_queue = queue.Queue()

        self.setup_ui()
        self.check_log_queue()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header Frame
        header = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="#17201c")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        header.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(
            header,
            text="🔌 COMPOSIO DESKTOP HUB",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#34d399"
        )
        title_lbl.grid(row=0, column=0, sticky="w", padx=20, pady=12)

        gemini_key = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
        status_text = "🟢 Google Gemini Qoşuludur" if gemini_key else "🔴 API Açar Yoxdur"
        status_color = "#34d399" if gemini_key else "#f87171"

        key_lbl = ctk.CTkLabel(
            header,
            text=status_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=status_color
        )
        key_lbl.grid(row=0, column=1, sticky="e", padx=20, pady=12)

        # Left Sidebar (Apps & Quick Actions)
        sidebar = ctk.CTkFrame(self, width=280, corner_radius=10, fg_color="#1c2622")
        sidebar.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        sidebar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(sidebar, text="⚡ Əsas Alət Paketləri", font=ctk.CTkFont(size=14, weight="bold"), text_color="#cbd5e1").pack(padx=15, pady=(15, 10), anchor="w")

        apps = [
            ("🐙 GitHub İnteqrasiyası", "github"),
            ("✉️ Gmail & Email Alətləri", "gmail"),
            ("💬 Slack Mesajlaşma", "slack"),
            ("📅 Google Calendar", "googlecalendar"),
            ("📝 Notion Sənədlər", "notion"),
            ("🎯 Linear / Jira Məsələləri", "linear"),
            ("🐦 Twitter / X Alətləri", "twitter"),
            ("🤖 Discord Bot Alətləri", "discord")
        ]

        for label, app_slug in apps:
            btn = ctk.CTkButton(
                sidebar,
                text=label,
                fg_color="#24332c",
                hover_color="#31453b",
                text_color="#e2e8f0",
                anchor="w",
                command=lambda s=app_slug: self.select_app(s)
            )
            btn.pack(padx=15, pady=3, fill="x")

        ctk.CTkLabel(sidebar, text="🔧 Hesab & Sistem İdarəsi", font=ctk.CTkFont(size=14, weight="bold"), text_color="#cbd5e1").pack(padx=15, pady=(20, 8), anchor="w")

        ctk.CTkButton(
            sidebar,
            text="🔑 Hesaba Giriş (composio login)",
            fg_color="#059669",
            hover_color="#047857",
            command=self.run_login
        ).pack(padx=15, pady=4, fill="x")

        ctk.CTkButton(
            sidebar,
            text="📋 Bağlı Hesablar (connections)",
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.run_connections
        ).pack(padx=15, pady=4, fill="x")

        ctk.CTkButton(
            sidebar,
            text="⚡ Tool Server Başlat (serve)",
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.run_serve
        ).pack(padx=15, pady=4, fill="x")

        # Main Workspace
        main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#17201c")
        main_frame.grid(row=1, column=1, sticky="nsew", padx=(0, 15), pady=15)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(3, weight=1)

        prompt_hdr = ctk.CTkLabel(main_frame, text="🔍 Tətbiq və ya Alət Axtarışı / İcra Əmri:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#e2e8f0")
        prompt_hdr.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        self.query_entry = ctk.CTkTextbox(main_frame, height=80, font=ctk.CTkFont(size=13), fg_color="#202c26", border_width=1, border_color="#374151")
        self.query_entry.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        self.query_entry.insert("1.0", "github")

        # Action Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))

        self.run_btn = ctk.CTkButton(
            btn_frame,
            text="🚀 Alət Məlumatlarını Gətir",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=38,
            command=self.search_tool
        )
        self.run_btn.pack(side="left", padx=(0, 10))

        list_apps_btn = ctk.CTkButton(
            btn_frame,
            text="📦 Bütün 1000+ Tətbiqi Göstər",
            font=ctk.CTkFont(size=13),
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=38,
            command=self.list_all_apps
        )
        list_apps_btn.pack(side="left", padx=(0, 10))

        clear_btn = ctk.CTkButton(
            btn_frame,
            text="🧹 Təmizlə",
            fg_color="#4b5563",
            hover_color="#374151",
            height=38,
            command=self.clear_console
        )
        clear_btn.pack(side="left")

        # Console Log
        console_frame = ctk.CTkFrame(main_frame, fg_color="#0e1411", corner_radius=8)
        console_frame.grid(row=3, column=0, sticky="nsew", padx=15, pady=(0, 15))
        console_frame.grid_columnconfigure(0, weight=1)
        console_frame.grid_rowconfigure(1, weight=1)

        c_header = ctk.CTkLabel(console_frame, text="🖥️ Composio Alət & Nəticə Paneli", font=ctk.CTkFont(size=12, weight="bold"), text_color="#94a3b8")
        c_header.grid(row=0, column=0, sticky="w", padx=12, pady=(8, 4))

        self.console_box = ctk.CTkTextbox(
            console_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#090d0b",
            text_color="#e2e8f0",
            border_width=0
        )
        self.console_box.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.log("[SİSTEM] Composio Desktop Hub hazırdır.\n[İNTEQRASİYA] Google Gemini Provayderi aktivdir.\n")

    def select_app(self, app_slug):
        self.query_entry.delete("1.0", "end")
        self.query_entry.insert("1.0", app_slug)
        self.search_tool()

    def log(self, text):
        self.log_queue.put(text)

    def check_log_queue(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.console_box.insert("end", msg + "\n")
            self.console_box.see("end")
        self.after(100, self.check_log_queue)

    def clear_console(self):
        self.console_box.delete("1.0", "end")

    def run_cmd_async(self, cmd_args, banner_text):
        def worker():
            self.log(f"\n{'='*55}\n{banner_text}\n{'='*55}")
            try:
                proc = subprocess.Popen(
                    cmd_args,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace"
                )
                for line in iter(proc.stdout.readline, ''):
                    l = line.strip()
                    if l:
                        self.log(l)
                proc.stdout.close()
                proc.wait()
            except Exception as e:
                self.log(f"[XƏTA]: {e}")
            finally:
                self.log("[BAŞA ÇATDI]\n")

        threading.Thread(target=worker, daemon=True).start()

    def search_tool(self):
        query = self.query_entry.get("1.0", "end").strip()
        if not query:
            return
        self.run_cmd_async(
            [sys.executable, "-m", "composio.cli", "apps"],
            f"[Axtarış]: '{query}' tətbiq alətləri sorğulanır..."
        )

    def list_all_apps(self):
        self.run_cmd_async(
            [sys.executable, "-m", "composio.cli", "apps"],
            "[Bütün Tətbiqlər]: Composio tərəfindən dəstəklənən inteqrasiyalar:"
        )

    def run_login(self):
        self.run_cmd_async(
            [sys.executable, "-m", "composio.cli", "login"],
            "[GİRİŞ]: Composio brauzer identifikasiya pəncərəsi başladılır..."
        )

    def run_connections(self):
        self.run_cmd_async(
            [sys.executable, "-m", "composio.cli", "connections"],
            "[BAĞLANTILAR]: Hazırda bağlı olan hesablar yoxlanılır..."
        )

    def run_serve(self):
        self.run_cmd_async(
            [sys.executable, "-m", "composio.cli", "serve"],
            "[SERVER]: Composio alət serveri başladılır..."
        )

if __name__ == "__main__":
    app = ComposioDesktopApp()
    app.mainloop()

import os
import sys
import threading
import subprocess
import queue
import time
from dotenv import load_dotenv

UFO_DIR = r"C:\Users\sahin\.gemini\antigravity\scratch\repos\UFO"
ENV_PATH = os.path.join(UFO_DIR, ".env")
if os.path.isfile(ENV_PATH):
    load_dotenv(ENV_PATH)

import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class UFODesktopApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🛸 Microsoft UFO — Windows OS Desktop AgentOS")
        self.geometry("1000x740")
        self.minsize(880, 620)

        self.process = None
        self.is_running = False
        self.log_queue = queue.Queue()

        self.setup_ui()
        self.check_log_queue()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header Frame
        header = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="#181e29")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        header.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(
            header,
            text="🛸 MICROSOFT UFO — DESKTOP AGENTOS",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#38bdf8"
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

        # Left Sidebar (Config & Presets)
        sidebar = ctk.CTkFrame(self, width=290, corner_radius=10, fg_color="#1f2430")
        sidebar.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        sidebar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(sidebar, text="⚙️ UFO Rejim Parametrləri", font=ctk.CTkFont(size=14, weight="bold"), text_color="#cbd5e1").pack(padx=15, pady=(15, 10), anchor="w")

        ctk.CTkLabel(sidebar, text="Tapşırıq Qovluğu Adı:", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(padx=15, pady=(5, 2), anchor="w")
        self.task_name_entry = ctk.CTkEntry(sidebar, font=ctk.CTkFont(size=12))
        self.task_name_entry.insert(0, "desktop_task_1")
        self.task_name_entry.pack(padx=15, pady=(0, 10), fill="x")

        ctk.CTkLabel(sidebar, text="İcra Rejimi (Mode):", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(padx=15, pady=(5, 2), anchor="w")
        self.mode_var = ctk.StringVar(value="normal")
        mode_dropdown = ctk.CTkOptionMenu(
            sidebar,
            values=["normal", "batch_normal", "follower"],
            variable=self.mode_var,
            fg_color="#0284c7",
            button_color="#0369a1"
        )
        mode_dropdown.pack(padx=15, pady=(0, 10), fill="x")

        self.visual_var = ctk.BooleanVar(value=True)
        visual_chk = ctk.CTkCheckBox(
            sidebar,
            text="Görüntü Analizi (Visual Mode)",
            variable=self.visual_var,
            fg_color="#0284c7"
        )
        visual_chk.pack(padx=15, pady=(5, 15), anchor="w")

        # Presets
        ctk.CTkLabel(sidebar, text="⚡ Hazır Windows Tapşırıqları", font=ctk.CTkFont(size=14, weight="bold"), text_color="#cbd5e1").pack(padx=15, pady=(10, 8), anchor="w")

        presets = [
            ("📝 Notepad-da Qeyd Yaz", "Notepad (Qeyd Dəftəri) proqramını aç, 'Google Antigravity və Microsoft UFO aktivdir!' yaz."),
            ("⚙️ Sistem Parametrlərini Yoxla", "Windows Settings (Parametrlər) tətbiqini aç, Sistem bölməsinə keç və ekran rezolyusiyasını yoxla."),
            ("📁 Fayl Bələdçisində Qovluq Aç", "File Explorer (Fayl Bələdçisi) pəncərəsini aç və 'Yüklənənlər' (Downloads) qovluğuna keç."),
            ("📄 Word Sənədi Hazırla", "Word proqramını aç, yeni sənəd yarat, 'Süni İntellekt Hesabatı' başlığını 24pt şriftlə yaz."),
            ("📊 Excel Cədvəli Yarat", "Excel proqramını aç, yeni iş vərəqi yarat və ilk sətrə 'Ad', 'Say', 'Qiymət' başlıqlarını daxil et.")
        ]

        for title, prompt_text in presets:
            btn = ctk.CTkButton(
                sidebar,
                text=title,
                fg_color="#2b3245",
                hover_color="#3e4863",
                text_color="#e2e8f0",
                anchor="w",
                command=lambda p=prompt_text: self.load_preset(p)
            )
            btn.pack(padx=15, pady=4, fill="x")

        # Open logs folder button
        ctk.CTkButton(
            sidebar,
            text="📂 UFO Jurnallarını və Şəkilləri Aç",
            fg_color="#374151",
            hover_color="#4b5563",
            command=self.open_logs_dir
        ).pack(padx=15, pady=(20, 10), fill="x", side="bottom")

        # Main Workspace
        main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#181e29")
        main_frame.grid(row=1, column=1, sticky="nsew", padx=(0, 15), pady=15)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(3, weight=1)

        prompt_hdr = ctk.CTkLabel(main_frame, text="🎯 Windows Əməliyyat Sistemi Tapşırığı:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#e2e8f0")
        prompt_hdr.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        self.prompt_entry = ctk.CTkTextbox(main_frame, height=90, font=ctk.CTkFont(size=13), fg_color="#242b3a", border_width=1, border_color="#374151")
        self.prompt_entry.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        self.prompt_entry.insert("1.0", "Notepad (Qeyd Dəftəri) proqramını aç, 'Google Antigravity və Microsoft UFO aktivdir!' yaz.")

        # Action Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))

        self.run_btn = ctk.CTkButton(
            btn_frame,
            text="🚀 Windows Tapşırığını İcra Et",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=38,
            command=self.start_ufo_task
        )
        self.run_btn.pack(side="left", padx=(0, 10))

        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="⏹ Dayandır",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#ef4444",
            hover_color="#dc2626",
            height=38,
            state="disabled",
            command=self.stop_ufo_task
        )
        self.stop_btn.pack(side="left", padx=(0, 10))

        clear_btn = ctk.CTkButton(
            btn_frame,
            text="🧹 Konsolu Təmizlə",
            fg_color="#4b5563",
            hover_color="#374151",
            height=38,
            command=self.clear_console
        )
        clear_btn.pack(side="left")

        # Console Log
        console_frame = ctk.CTkFrame(main_frame, fg_color="#0f131a", corner_radius=8)
        console_frame.grid(row=3, column=0, sticky="nsew", padx=15, pady=(0, 15))
        console_frame.grid_columnconfigure(0, weight=1)
        console_frame.grid_rowconfigure(1, weight=1)

        c_header = ctk.CTkLabel(console_frame, text="🖥️ UFO HostAgent & AppAgent Canlı İcra Konsolu", font=ctk.CTkFont(size=12, weight="bold"), text_color="#94a3b8")
        c_header.grid(row=0, column=0, sticky="w", padx=12, pady=(8, 4))

        self.console_box = ctk.CTkTextbox(
            console_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#0a0c10",
            text_color="#e2e8f0",
            border_width=0
        )
        self.console_box.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.log("[SİSTEM] Microsoft UFO Desktop AgentOS hazırdır.\n[MODEL] Google Gemini 2.5 Flash qoşuldu.\n")

    def load_preset(self, text):
        self.prompt_entry.delete("1.0", "end")
        self.prompt_entry.insert("1.0", text)

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

    def open_logs_dir(self):
        logs_dir = os.path.join(UFO_DIR, "ufo", "logs")
        os.makedirs(logs_dir, exist_ok=True)
        os.startfile(logs_dir)

    def start_ufo_task(self):
        prompt = self.prompt_entry.get("1.0", "end").strip()
        task_name = self.task_name_entry.get().strip() or "ufo_task"
        if not prompt:
            self.log("[XƏTA] Zəhmət olmasa icra ediləcək tapşırıq mətni daxil edin!")
            return

        self.is_running = True
        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.log(f"\n{'='*60}\n[UFO BAŞLADI] Tapşırıq: {task_name}\nİstək: {prompt}\n{'='*60}")

        threading.Thread(target=self.run_ufo_worker, args=(task_name, prompt), daemon=True).start()

    def stop_ufo_task(self):
        self.is_running = False
        if self.process:
            try:
                self.process.terminate()
            except Exception:
                pass
        self.log("[SİSTEM] UFO dayandırıldı.")
        self.run_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def run_ufo_worker(self, task_name, prompt):
        try:
            cmd = [
                sys.executable,
                "-u",
                "-m",
                "ufo",
                "--task",
                task_name,
                "-r",
                prompt
            ]

            self.process = subprocess.Popen(
                cmd,
                cwd=UFO_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1
            )

            for line in iter(self.process.stdout.readline, ''):
                if not self.is_running:
                    self.process.terminate()
                    break
                l = line.strip()
                if l:
                    self.log(l)

            self.process.stdout.close()
            self.process.wait()
            self.log(f"[UFO TAMAMLANDI] {task_name} başa çatdı. Nəticələr və skrinşotlar ufo/logs qovluğuna qeyd edildi.")
        except Exception as e:
            self.log(f"[XƏTA]: {e}")
        finally:
            self.is_running = False
            self.run_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")

if __name__ == "__main__":
    app = UFODesktopApp()
    app.mainloop()

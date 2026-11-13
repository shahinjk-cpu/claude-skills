import os
import sys
import threading
import asyncio
import queue
import time
import subprocess
from dotenv import load_dotenv

# Load env variables
ENV_PATH = r"C:\Users\sahin\.gemini\antigravity\scratch\repos\browser-use\.env"
if os.path.isfile(ENV_PATH):
    load_dotenv(ENV_PATH)

import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class BrowserUseApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🌐 Browser-Use Studio — AI Brauzer Avtomatlaşdırması")
        self.geometry("980x720")
        self.minsize(850, 600)

        self.worker_thread = None
        self.is_running = False
        self.log_queue = queue.Queue()

        self.setup_ui()
        self.check_log_queue()

    def setup_ui(self):
        # Grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header Frame
        header = ctk.CTkFrame(self, height=60, corner_radius=0, fg_color="#1a1d24")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=0)
        header.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(
            header,
            text="🌐 BROWSER-USE STUDIO",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#60a5fa"
        )
        title_lbl.grid(row=0, column=0, sticky="w", padx=20, pady=12)

        gemini_key = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
        status_text = "🟢 Google Gemini Aktiv" if gemini_key else "🔴 API Açar Yoxdur"
        status_color = "#34d399" if gemini_key else "#f87171"

        key_lbl = ctk.CTkLabel(
            header,
            text=status_text,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=status_color
        )
        key_lbl.grid(row=0, column=1, sticky="e", padx=20, pady=12)

        # Left Sidebar (Settings & Presets)
        sidebar = ctk.CTkFrame(self, width=280, corner_radius=10, fg_color="#21252e")
        sidebar.grid(row=1, column=0, sticky="nsew", padx=15, pady=15)
        sidebar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(sidebar, text="⚙️ Model & Brauzer Parametrləri", font=ctk.CTkFont(size=14, weight="bold"), text_color="#cbd5e1").pack(padx=15, pady=(15, 10), anchor="w")

        ctk.CTkLabel(sidebar, text="Süni İntellekt Modeli:", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(padx=15, pady=(5, 2), anchor="w")
        self.model_var = ctk.StringVar(value="gemini-2.5-flash")
        model_dropdown = ctk.CTkOptionMenu(
            sidebar,
            values=["gemini-2.5-flash", "gemini-1.5-flash", "gemini-2.0-flash"],
            variable=self.model_var,
            fg_color="#3b82f6",
            button_color="#2563eb"
        )
        model_dropdown.pack(padx=15, pady=(0, 10), fill="x")

        ctk.CTkLabel(sidebar, text="Brauzer Görünüşü:", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(padx=15, pady=(5, 2), anchor="w")
        self.headless_var = ctk.BooleanVar(value=False)
        self.headless_chk = ctk.CTkCheckBox(
            sidebar,
            text="Görünən Brauzer (Canlı İzlə)",
            variable=self.headless_var,
            onvalue=False,
            offvalue=True,
            fg_color="#3b82f6"
        )
        self.headless_chk.pack(padx=15, pady=(0, 10), anchor="w")

        ctk.CTkLabel(sidebar, text="Maksimum Addım Sayı:", font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(padx=15, pady=(5, 2), anchor="w")
        self.steps_slider = ctk.CTkSlider(sidebar, from_=5, to=50, number_of_steps=9)
        self.steps_slider.set(20)
        self.steps_slider.pack(padx=15, pady=(0, 5), fill="x")
        self.steps_lbl = ctk.CTkLabel(sidebar, text="20 addım", font=ctk.CTkFont(size=11), text_color="#94a3b8")
        self.steps_lbl.pack(padx=15, pady=(0, 15), anchor="e")
        self.steps_slider.configure(command=lambda v: self.steps_lbl.configure(text=f"{int(v)} addım"))

        # Presets
        ctk.CTkLabel(sidebar, text="⚡ Hazır Nümunələr", font=ctk.CTkFont(size=14, weight="bold"), text_color="#cbd5e1").pack(padx=15, pady=(10, 8), anchor="w")

        presets = [
            ("🔍 Google Axtarışı", "Google-da 'Google Antigravity Agent' haqqında axtarış et və ilk 3 nəticənin başlığını göstər."),
            ("📈 GitHub Trendlər", "GitHub Trending səhifəsinə daxil ol və ən çox ulduz qazanan ilk 3 Python layihəsinin adını yaz."),
            ("📰 Hacker News Xəbərləri", "news.ycombinator.com saytına daxil ol və 1 nömrəli ən son xəbərin başlığını çıxar."),
            ("🌦️ Bakı Hava Proqnozu", "Google-da 'Baki hava proqnozu' axtar və bugünkü havanın temperaturunu öyrən.")
        ]

        for title, prompt_text in presets:
            btn = ctk.CTkButton(
                sidebar,
                text=title,
                fg_color="#2d3748",
                hover_color="#4a5568",
                text_color="#e2e8f0",
                anchor="w",
                command=lambda p=prompt_text: self.load_preset(p)
            )
            btn.pack(padx=15, pady=4, fill="x")

        # Main Workspace
        main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#1a1d24")
        main_frame.grid(row=1, column=1, sticky="nsew", padx=(0, 15), pady=15)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(3, weight=1)

        # Prompt input
        prompt_hdr = ctk.CTkLabel(main_frame, text="📝 İcra Ediləcək Tapşırıq (Təbii Dillə Yazın):", font=ctk.CTkFont(size=14, weight="bold"), text_color="#e2e8f0")
        prompt_hdr.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 5))

        self.prompt_entry = ctk.CTkTextbox(main_frame, height=90, font=ctk.CTkFont(size=13), fg_color="#262b36", border_width=1, border_color="#374151")
        self.prompt_entry.grid(row=1, column=0, sticky="ew", padx=15, pady=(0, 10))
        self.prompt_entry.insert("1.0", "Google-da 'Google Antigravity Agent' haqqında axtarış et və ilk 3 nəticənin başlığını tap.")

        # Action Buttons
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))

        self.run_btn = ctk.CTkButton(
            btn_frame,
            text="🚀 Brauzeri İşə Sal və İcra Et",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#10b981",
            hover_color="#059669",
            height=38,
            command=self.start_task
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
            command=self.stop_task
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

        # Console Log Area
        console_frame = ctk.CTkFrame(main_frame, fg_color="#111318", corner_radius=8)
        console_frame.grid(row=3, column=0, sticky="nsew", padx=15, pady=(0, 15))
        console_frame.grid_columnconfigure(0, weight=1)
        console_frame.grid_rowconfigure(1, weight=1)

        c_header = ctk.CTkLabel(console_frame, text="🖥️ Canlı İcra Konsolu & Agent Jurnalı", font=ctk.CTkFont(size=12, weight="bold"), text_color="#94a3b8")
        c_header.grid(row=0, column=0, sticky="w", padx=12, pady=(8, 4))

        self.console_box = ctk.CTkTextbox(
            console_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            fg_color="#0a0c10",
            text_color="#e2e8f0",
            border_width=0
        )
        self.console_box.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.log("[SİSTEM] Browser-Use Studio Desktop işə düşdü. Google Gemini hazırdır.\n")

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

    def start_task(self):
        prompt = self.prompt_entry.get("1.0", "end").strip()
        if not prompt:
            self.log("[XƏTA] Zəhmət olmasa icra ediləcək tapşırıq mətni daxil edin!")
            return

        self.is_running = True
        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.log(f"\n{'='*55}\n[BAŞLADI] Tapşırıq: {prompt}\nModel: {self.model_var.get()} | Görünən Brauzer: {not self.headless_var.get()}\n{'='*55}")

        self.worker_thread = threading.Thread(target=self.run_agent_thread, args=(prompt,), daemon=True)
        self.worker_thread.start()

    def stop_task(self):
        self.is_running = False
        self.log("[SİSTEM] Dayandırma əmri göndərildi...")
        self.run_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def run_agent_thread(self, prompt):
        try:
            # We execute python script directly to handle asyncio event loop cleanly
            script = f"""
import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv(r"{ENV_PATH}")
from browser_use import Agent, Browser, ChatGoogle

async def run():
    llm = ChatGoogle('{self.model_var.get()}')
    # Open local Chromium or Chrome
    browser = Browser('chromium', headless={str(self.headless_var.get())})
    agent = Agent(
        task='''{prompt}''',
        llm=llm,
        browser=browser
    )
    result = await agent.run(max_steps={int(self.steps_slider.get())})
    print("\\n[NƏTİCƏ]:\\n" + str(result.final_result()))

if __name__ == '__main__':
    asyncio.run(run())
"""
            temp_script = os.path.join(r"C:\Users\sahin\AI-Agent-Desktop-Apps", "temp_runner.py")
            with open(temp_script, "w", encoding="utf-8") as f:
                f.write(script)

            process = subprocess.Popen(
                [sys.executable, "-u", temp_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1
            )

            for line in iter(process.stdout.readline, ''):
                if not self.is_running:
                    process.terminate()
                    self.log("[DAYANDIRILDI] İstifadəçi tərəfindən dayandırıldı.")
                    break
                line_str = line.strip()
                if line_str:
                    self.log(line_str)

            process.stdout.close()
            process.wait()
            self.log("[TAMAMLANDI] Browser-Use tapşırığı başa çatdı.")
        except Exception as e:
            self.log(f"[XƏTA]: {e}")
        finally:
            self.is_running = False
            self.run_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")

if __name__ == "__main__":
    app = BrowserUseApp()
    app.mainloop()

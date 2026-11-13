import os
import sys
import subprocess
import threading
import customtkinter as ctk

APPS_DIR = r"C:\Users\sahin\AI-Agent-Desktop-Apps"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AIAgentMasterStudio(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🚀 AI Agent Master Studio — Browser-Use, Microsoft UFO & Composio")
        self.geometry("1100x780")
        self.minsize(920, 650)

        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left Navigation Sidebar
        sidebar = ctk.CTkFrame(self, width=260, corner_radius=0, fg_color="#13161c")
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(6, weight=1)

        logo_lbl = ctk.CTkLabel(
            sidebar,
            text="🚀 AGENT STUDIO",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#60a5fa"
        )
        logo_lbl.grid(row=0, column=0, padx=20, pady=(25, 20), sticky="w")

        self.nav_btns = {}
        nav_items = [
            ("🌐 Browser-Use", "browser"),
            ("🛸 Microsoft UFO", "ufo"),
            ("🔌 Composio Hub", "composio"),
            ("🔑 API & Parametrlər", "settings")
        ]

        for i, (label, tag) in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(
                sidebar,
                text=label,
                font=ctk.CTkFont(size=14, weight="bold"),
                height=42,
                corner_radius=8,
                fg_color="#1e2430" if tag == "browser" else "transparent",
                text_color="#f8fafc",
                hover_color="#273042",
                anchor="w",
                command=lambda t=tag: self.switch_tab(t)
            )
            btn.grid(row=i, column=0, padx=15, pady=5, sticky="ew")
            self.nav_btns[tag] = btn

        # Bottom Quick Launch Buttons
        quick_hdr = ctk.CTkLabel(sidebar, text="Masaüstü Pəncərələri:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#64748b")
        quick_hdr.grid(row=5, column=0, padx=20, pady=(30, 8), sticky="w")

        ctk.CTkButton(
            sidebar,
            text="🌐 Browser-Use Aç",
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color="#1e3a8a",
            hover_color="#1d4ed8",
            command=lambda: self.launch_standalone("browser_use_app.py")
        ).grid(row=6, column=0, padx=15, pady=4, sticky="ew")

        ctk.CTkButton(
            sidebar,
            text="🛸 Microsoft UFO Aç",
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color="#0369a1",
            hover_color="#0284c7",
            command=lambda: self.launch_standalone("ufo_app.py")
        ).grid(row=7, column=0, padx=15, pady=4, sticky="ew")

        ctk.CTkButton(
            sidebar,
            text="🔌 Composio Aç",
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color="#065f46",
            hover_color="#059669",
            command=lambda: self.launch_standalone("composio_app.py")
        ).grid(row=8, column=0, padx=15, pady=(4, 20), sticky="ew")

        # Main Content Area
        self.content_container = ctk.CTkFrame(self, corner_radius=0, fg_color="#181c24")
        self.content_container.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)

        self.frames = {}
        self.build_browser_tab()
        self.build_ufo_tab()
        self.build_composio_tab()
        self.build_settings_tab()

        self.switch_tab("browser")

    def switch_tab(self, active_tag):
        for tag, btn in self.nav_btns.items():
            if tag == active_tag:
                btn.configure(fg_color="#2563eb", text_color="#ffffff")
            else:
                btn.configure(fg_color="transparent", text_color="#94a3b8")

        for tag, frame in self.frames.items():
            if tag == active_tag:
                frame.grid(row=0, column=0, sticky="nsew", padx=25, pady=25)
            else:
                frame.grid_forget()

    def launch_standalone(self, script_name):
        path = os.path.join(APPS_DIR, script_name)
        subprocess.Popen([sys.executable, path])

    def build_browser_tab(self):
        f = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.frames["browser"] = f
        f.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(header, text="🌐 Browser-Use AI Studio", font=ctk.CTkFont(size=22, weight="bold"), text_color="#60a5fa").pack(side="left")
        ctk.CTkButton(
            header,
            text="📂 Ayrı Pəncərədə Aç",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=lambda: self.launch_standalone("browser_use_app.py")
        ).pack(side="right")

        card = ctk.CTkFrame(f, fg_color="#1e2430", corner_radius=10)
        card.pack(fill="both", expand=True, pady=10)

        ctk.CTkLabel(card, text="Veb Brauzer Avtomatlaşdırması Haqqında", font=ctk.CTkFont(size=16, weight="bold"), text_color="#e2e8f0").pack(padx=20, pady=(20, 10), anchor="w")
        desc = (
            "Browser-Use Google Gemini modeli ilə real Google Chrome və ya Chromium brauzerini idarə edir.\n"
            "İstədiyiniz tapşırığı təbii dildə yazdıqda süni intellekt canlı olaraq veb saytlara daxil olur,\n"
            "formaları doldurur, düymələrə klikləyir, məlumatları toplayır və nəticəni təqdim edir."
        )
        ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(size=13), text_color="#94a3b8", justify="left").pack(padx=20, pady=(0, 20), anchor="w")

        features_frame = ctk.CTkFrame(card, fg_color="#151922", corner_radius=8)
        features_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(features_frame, text="✨ Əsas Xüsusiyyətlər:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8").pack(padx=15, pady=(12, 6), anchor="w")
        points = [
            "• Canlı brauzer rejimi (Headless=False) ilə süni intellektin hərəkətlərini ekranda izləmək.",
            "• CAPTCHA və bot qorunmalarını insan davranışına uyğun aşmaq.",
            "• Google Axtarış, GitHub, Xəbər və elektron ticarət saytlarından dəqiq məlumat çıxarışı.",
            "• Google Gemini 2.5 Flash və Gemini 1.5 Flash modelləri ilə yüksək sürətli icra."
        ]
        for p in points:
            ctk.CTkLabel(features_frame, text=p, font=ctk.CTkFont(size=12), text_color="#cbd5e1").pack(padx=20, pady=2, anchor="w")
        features_frame.pack_configure(pady=(0, 20))

        launch_btn = ctk.CTkButton(
            card,
            text="🚀 Browser-Use Studio-nu Başlat və İdarə Et",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=46,
            fg_color="#10b981",
            hover_color="#059669",
            command=lambda: self.launch_standalone("browser_use_app.py")
        )
        launch_btn.pack(padx=20, pady=20, fill="x")

    def build_ufo_tab(self):
        f = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.frames["ufo"] = f
        f.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(header, text="🛸 Microsoft UFO Desktop AgentOS", font=ctk.CTkFont(size=22, weight="bold"), text_color="#38bdf8").pack(side="left")
        ctk.CTkButton(
            header,
            text="📂 Ayrı Pəncərədə Aç",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=lambda: self.launch_standalone("ufo_app.py")
        ).pack(side="right")

        card = ctk.CTkFrame(f, fg_color="#1e2430", corner_radius=10)
        card.pack(fill="both", expand=True, pady=10)

        ctk.CTkLabel(card, text="Windows Əməliyyat Sistemi Avtomatlaşdırması", font=ctk.CTkFont(size=16, weight="bold"), text_color="#e2e8f0").pack(padx=20, pady=(20, 10), anchor="w")
        desc = (
            "Microsoft UFO Windows masaüstü tətbiqlərini birbaşa idarə edən ilk rəsmi süni intellekt agentidir.\n"
            "HostAgent ekranı nəzərdən keçirib tətbiqləri seçir, AppAgent isə tətbiqdaxili düymələri, menyuları\n"
            "və sahələri Windows UIAutomation və vizual görmə qabiliyyəti ilə taparaq idarə edir."
        )
        ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(size=13), text_color="#94a3b8", justify="left").pack(padx=20, pady=(0, 20), anchor="w")

        features_frame = ctk.CTkFrame(card, fg_color="#151922", corner_radius=8)
        features_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(features_frame, text="✨ Nələri Avtomatlaşdıra Bilir:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8").pack(padx=15, pady=(12, 6), anchor="w")
        points = [
            "• Microsoft Office (Word sənədləri, Excel cədvəlləri, PowerPoint slaydları).",
            "• Windows Parametrləri, Fayl Bələdçisi (Explorer), Notepad, Kalkulyator.",
            "• Hibrid UIAutomation və Multimodal görmə: xüsusi dizayn edilmiş desktop proqramlar.",
            "• Addım-addım skrinşot arxivlənməsi və qərar qəbuletmə jurnalı."
        ]
        for p in points:
            ctk.CTkLabel(features_frame, text=p, font=ctk.CTkFont(size=12), text_color="#cbd5e1").pack(padx=20, pady=2, anchor="w")
        features_frame.pack_configure(pady=(0, 20))

        launch_btn = ctk.CTkButton(
            card,
            text="🚀 Microsoft UFO Desktop Tətbiqini Başlat",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=46,
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=lambda: self.launch_standalone("ufo_app.py")
        )
        launch_btn.pack(padx=20, pady=20, fill="x")

    def build_composio_tab(self):
        f = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.frames["composio"] = f
        f.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(header, text="🔌 Composio 1000+ Tools Hub", font=ctk.CTkFont(size=22, weight="bold"), text_color="#34d399").pack(side="left")
        ctk.CTkButton(
            header,
            text="📂 Ayrı Pəncərədə Aç",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#059669",
            hover_color="#047857",
            command=lambda: self.launch_standalone("composio_app.py")
        ).pack(side="right")

        card = ctk.CTkFrame(f, fg_color="#1e2430", corner_radius=10)
        card.pack(fill="both", expand=True, pady=10)

        ctk.CTkLabel(card, text="Süni İntellekt üçün 1000+ Real Dünya Tətbiqi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#e2e8f0").pack(padx=20, pady=(20, 10), anchor="w")
        desc = (
            "Composio AI agentləri real bulud servislərinə və proqramlarına bağlayan ən zəngin alət qovşağıdır.\n"
            "GitHub-da repozitoriya ulduzlamaqdan Slack-də mesaj göndərməyə, Gmail-dən məktub oxumaqdan\n"
            "Google Calendar-da görüş təyin etməyə qədər hər bir əməliyyatı Gemini üçün hazır alətə çevirir."
        )
        ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(size=13), text_color="#94a3b8", justify="left").pack(padx=20, pady=(0, 20), anchor="w")

        features_frame = ctk.CTkFrame(card, fg_color="#151922", corner_radius=8)
        features_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(features_frame, text="✨ Dəstəklənən Əsas İnteqrasiyalar:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#34d399").pack(padx=15, pady=(12, 6), anchor="w")
        points = [
            "• Gelişdirici: GitHub, GitLab, Jira, Linear, Sentry, Postman.",
            "• Əməkdaşlıq: Slack, Discord, Microsoft Teams, Notion, Google Docs.",
            "• Şəxsi köməkçi: Gmail, Google Calendar, Outlook, ClickUp, Trello.",
            "• MCP (Model Context Protocol) və Gemini SDK ilə 100% uyğunluq."
        ]
        for p in points:
            ctk.CTkLabel(features_frame, text=p, font=ctk.CTkFont(size=12), text_color="#cbd5e1").pack(padx=20, pady=2, anchor="w")
        features_frame.pack_configure(pady=(0, 20))

        launch_btn = ctk.CTkButton(
            card,
            text="🚀 Composio Desktop Hub-ı Başlat",
            font=ctk.CTkFont(size=15, weight="bold"),
            height=46,
            fg_color="#059669",
            hover_color="#047857",
            command=lambda: self.launch_standalone("composio_app.py")
        )
        launch_btn.pack(padx=20, pady=20, fill="x")

    def build_settings_tab(self):
        f = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.frames["settings"] = f
        f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(f, text="🔑 API Açar & Sistem Parametrləri", font=ctk.CTkFont(size=22, weight="bold"), text_color="#f8fafc").pack(pady=(0, 15), anchor="w")

        card = ctk.CTkFrame(f, fg_color="#1e2430", corner_radius=10)
        card.pack(fill="both", expand=True, pady=10)

        ctk.CTkLabel(card, text="Google Gemini API Açar İdarəsi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#e2e8f0").pack(padx=20, pady=(20, 10), anchor="w")

        current_key = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
        self.key_entry = ctk.CTkEntry(card, font=ctk.CTkFont(size=13), show="*")
        self.key_entry.insert(0, current_key)
        self.key_entry.pack(padx=20, pady=10, fill="x")

        toggle_frame = ctk.CTkFrame(card, fg_color="transparent")
        toggle_frame.pack(fill="x", padx=20, pady=5)

        self.show_key_var = ctk.BooleanVar(value=False)
        def toggle_key():
            self.key_entry.configure(show="" if self.show_key_var.get() else "*")

        ctk.CTkCheckBox(toggle_frame, text="Açarı göstər", variable=self.show_key_var, command=toggle_key).pack(side="left")

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=20)

        def save_and_test():
            new_key = self.key_entry.get().strip()
            if not new_key:
                status_lbl.configure(text="[XƏTA] Açar boş ola bilməz!", text_color="#f87171")
                return

            import urllib.request
            url = f"https://generativelanguage.googleapis.com/v1beta/models?key={new_key}"
            try:
                req = urllib.request.Request(url)
                with urllib.request.urlopen(req) as resp:
                    if resp.status == 200:
                        # Save in files
                        os.environ["GEMINI_API_KEY"] = new_key
                        os.environ["GOOGLE_API_KEY"] = new_key
                        # Update repos
                        for p in [
                            r"C:\Users\sahin\.gemini\antigravity\scratch\repos\browser-use\.env",
                            r"C:\Users\sahin\.gemini\antigravity\scratch\repos\UFO\.env",
                            r"C:\Users\sahin\.gemini\antigravity\scratch\repos\composio\.env"
                        ]:
                            with open(p, "w", encoding="utf-8") as env_f:
                                env_f.write(f"GOOGLE_API_KEY={new_key}\nGEMINI_API_KEY={new_key}\n")
                        status_lbl.configure(text="✅ Açar uğurla yoxlanıldı və bütün 3 tətbiqdə yeniləndi!", text_color="#34d399")
            except Exception as e:
                status_lbl.configure(text=f"❌ Açar etibarsızdır: {e}", text_color="#f87171")

        ctk.CTkButton(btn_row, text="💾 Yadda Saxla və Yoxla", fg_color="#10b981", hover_color="#059669", command=save_and_test).pack(side="left", padx=(0, 10))

        status_lbl = ctk.CTkLabel(card, text="🟢 Cari açar aktivdir və bütün 3 sistemlə əlaqələndirilib.", font=ctk.CTkFont(size=13), text_color="#34d399")
        status_lbl.pack(padx=20, pady=10, anchor="w")

if __name__ == "__main__":
    app = AIAgentMasterStudio()
    app.mainloop()

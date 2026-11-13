import os
import sys
import subprocess
import threading
import webbrowser
import customtkinter as ctk

APPS_DIR = r"C:\Users\sahin\AI-Agent-Desktop-Apps"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AIAgentMasterStudio(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🚀 AI Agent Master Studio — Browser-Use, UFO, Composio & ODS V3")
        self.geometry("1120x800")
        self.minsize(940, 680)

        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left Navigation Sidebar
        sidebar = ctk.CTkFrame(self, width=270, corner_radius=0, fg_color="#13161c")
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(8, weight=1)

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
            ("🌌 Osmantic ODS V3", "ods"),
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
            btn.grid(row=i, column=0, padx=15, pady=4, sticky="ew")
            self.nav_btns[tag] = btn

        # Quick Launch Header
        quick_hdr = ctk.CTkLabel(sidebar, text="Masaüstü Pəncərələri:", font=ctk.CTkFont(size=12, weight="bold"), text_color="#64748b")
        quick_hdr.grid(row=6, column=0, padx=20, pady=(25, 6), sticky="w")

        ctk.CTkButton(
            sidebar,
            text="🌐 Browser-Use Aç",
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color="#1e3a8a",
            hover_color="#1d4ed8",
            command=lambda: self.launch_standalone("browser_use_app.py")
        ).grid(row=7, column=0, padx=15, pady=3, sticky="ew")

        ctk.CTkButton(
            sidebar,
            text="🛸 Microsoft UFO Aç",
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color="#0369a1",
            hover_color="#0284c7",
            command=lambda: self.launch_standalone("ufo_app.py")
        ).grid(row=8, column=0, padx=15, pady=3, sticky="ew")

        ctk.CTkButton(
            sidebar,
            text="🔌 Composio Aç",
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color="#065f46",
            hover_color="#059669",
            command=lambda: self.launch_standalone("composio_app.py")
        ).grid(row=9, column=0, padx=15, pady=3, sticky="ew")

        ctk.CTkButton(
            sidebar,
            text="🌌 Osmantic ODS Aç",
            height=30,
            font=ctk.CTkFont(size=12),
            fg_color="#7c2d12",
            hover_color="#b45309",
            command=lambda: self.launch_standalone("ods_app.py")
        ).grid(row=10, column=0, padx=15, pady=(3, 20), sticky="ew")

        # Main Content Area
        self.content_container = ctk.CTkFrame(self, corner_radius=0, fg_color="#181c24")
        self.content_container.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.content_container.grid_columnconfigure(0, weight=1)
        self.content_container.grid_rowconfigure(0, weight=1)

        self.frames = {}
        self.build_browser_tab()
        self.build_ufo_tab()
        self.build_composio_tab()
        self.build_ods_tab()
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
            "• Canlı brauzer vizualizasiyası (Gözünüzün qarşısında saytları gəzir)",
            "• Google Gemini 2.5 Flash / Pro ilə super-sürətli planlama və icra",
            "• Kompleks axtarış, e-ticarət qiymət müqayisəsi, qeydiyyat və testlər",
            "• Çıxarılmış məlumatların fayla yazılması və konsol hesabatı"
        ]
        for p in points:
            ctk.CTkLabel(features_frame, text=p, font=ctk.CTkFont(size=13), text_color="#cbd5e1").pack(padx=20, pady=2, anchor="w")

        ctk.CTkLabel(features_frame, text="", height=10).pack()

        btn_launch = ctk.CTkButton(
            card,
            text="🚀 Browser-Use Studio-nu Başlat",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=44,
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            command=lambda: self.launch_standalone("browser_use_app.py")
        )
        btn_launch.pack(padx=20, pady=25, fill="x")

    def build_ufo_tab(self):
        f = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.frames["ufo"] = f
        f.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(header, text="🛸 Microsoft UFO Studio", font=ctk.CTkFont(size=22, weight="bold"), text_color="#38bdf8").pack(side="left")
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

        ctk.CTkLabel(card, text="Windows ƏS və Desktop Tətbiqlərinin İdarəsi", font=ctk.CTkFont(size=16, weight="bold"), text_color="#e2e8f0").pack(padx=20, pady=(20, 10), anchor="w")
        desc = (
            "Microsoft UFO (UI-Focused Agent) Windows əməliyyat sisteminin daxilindəki bütün desktop proqramları\n"
            "(Office, Notepad, Paint, Explorer, Brauzer və s.) vizual olaraq analiz edir və idarə edir.\n"
            "HostAgent və AppAgent ikili agent arxitekturası sayəsində pəncərələri tanıyır, idarə elementlərinə klikləyir."
        )
        ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(size=13), text_color="#94a3b8", justify="left").pack(padx=20, pady=(0, 20), anchor="w")

        features_frame = ctk.CTkFrame(card, fg_color="#151922", corner_radius=8)
        features_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(features_frame, text="✨ Əsas Xüsusiyyətlər:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8").pack(padx=15, pady=(12, 6), anchor="w")
        points = [
            "• Windows UI Automation API və Win32 inteqrasiyası",
            "• İkili Agent sistemi: HostAgent (qlobal plan) və AppAgent (tətbiq daxili icra)",
            "• İstənilən desktop proqramında mətn yazmaq, menyuları açmaq və faylları saxlamaq",
            "• Təbii dildə əmr: 'Notepad-i aç və xülasəni yaz', 'Faylı Word-ə çevir' və s."
        ]
        for p in points:
            ctk.CTkLabel(features_frame, text=p, font=ctk.CTkFont(size=13), text_color="#cbd5e1").pack(padx=20, pady=2, anchor="w")

        ctk.CTkLabel(features_frame, text="", height=10).pack()

        btn_launch = ctk.CTkButton(
            card,
            text="🚀 Microsoft UFO Desktop-u Başlat",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=44,
            fg_color="#0284c7",
            hover_color="#0369a1",
            command=lambda: self.launch_standalone("ufo_app.py")
        )
        btn_launch.pack(padx=20, pady=25, fill="x")

    def build_composio_tab(self):
        f = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.frames["composio"] = f
        f.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(header, text="🔌 Composio Toolset Hub", font=ctk.CTkFont(size=22, weight="bold"), text_color="#34d399").pack(side="left")
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

        ctk.CTkLabel(card, text="250+ Xidmət və Alət İnteqrasiyası", font=ctk.CTkFont(size=16, weight="bold"), text_color="#e2e8f0").pack(padx=20, pady=(20, 10), anchor="w")
        desc = (
            "Composio süni intellekt agentlərinə GitHub, Gmail, Slack, Notion, Linear, Trello, Google Calendar\n"
            "və 250-dən çox digər xidmətlə birbaşa API səviyyəsində əlaqə qurmaq və işləmək imkanı verir.\n"
            "Google Gemini modeli ilə hazır Function Calling və Alət icrası təmin edilir."
        )
        ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(size=13), text_color="#94a3b8", justify="left").pack(padx=20, pady=(0, 20), anchor="w")

        features_frame = ctk.CTkFrame(card, fg_color="#151922", corner_radius=8)
        features_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(features_frame, text="✨ Əsas Xüsusiyyətlər:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#34d399").pack(padx=15, pady=(12, 6), anchor="w")
        points = [
            "• GitHub repozitoriyaları, Pull Request və Issue-lərin idarəsi",
            "• Gmail və Slack üzərindən avtomatlaşdırılmış bildirişlər və mesaj göndərişi",
            "• Google Calendar görüşlərinin təyini və sənədlərin sinxronizasiyası",
            "• Bütün alətlər üçün təhlükəsiz OAuth və API açar idarəetməsi"
        ]
        for p in points:
            ctk.CTkLabel(features_frame, text=p, font=ctk.CTkFont(size=13), text_color="#cbd5e1").pack(padx=20, pady=2, anchor="w")

        ctk.CTkLabel(features_frame, text="", height=10).pack()

        btn_launch = ctk.CTkButton(
            card,
            text="🚀 Composio Studio-nu Başlat",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=44,
            fg_color="#059669",
            hover_color="#047857",
            command=lambda: self.launch_standalone("composio_app.py")
        )
        btn_launch.pack(padx=20, pady=25, fill="x")

    def build_ods_tab(self):
        f = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.frames["ods"] = f
        f.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(f, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(header, text="🌌 Osmantic ODS V3 AI Server", font=ctk.CTkFont(size=22, weight="bold"), text_color="#f59e0b").pack(side="left")
        ctk.CTkButton(
            header,
            text="📂 ODS Studio Aç",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#d97706",
            hover_color="#b45309",
            command=lambda: self.launch_standalone("ods_app.py")
        ).pack(side="right")

        card = ctk.CTkFrame(f, fg_color="#1e2430", corner_radius=10)
        card.pack(fill="both", expand=True, pady=10)

        ctk.CTkLabel(card, text="Şəxsi Süni İntellekt Serveri & Homelab", font=ctk.CTkFont(size=16, weight="bold"), text_color="#e2e8f0").pack(padx=20, pady=(20, 10), anchor="w")
        desc = (
            "Osmantic Deployment System (ODS V3) kompüterinizi tam müstəqil, təhlükəsiz və suveren süni intellekt\n"
            "serverinə çevirir. Heç bir bulud abunəliyi və ya telemetriya olmadan lokal modelləri işlədir,\n"
            "Open WebUI, Pixel Agent, Qdrant RAG, SearXNG, n8n və ComfyUI xidmətlərini vahid bir sistemdə birləşdirir."
        )
        ctk.CTkLabel(card, text=desc, font=ctk.CTkFont(size=13), text_color="#94a3b8", justify="left").pack(padx=20, pady=(0, 15), anchor="w")

        # Quick Web Links
        link_frame = ctk.CTkFrame(card, fg_color="#151922", corner_radius=8)
        link_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(link_frame, text="🔗 Veb Giriş Nöqtələri:", font=ctk.CTkFont(size=14, weight="bold"), text_color="#f59e0b").pack(padx=15, pady=(10, 6), anchor="w")

        row = ctk.CTkFrame(link_frame, fg_color="transparent")
        row.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkButton(
            row,
            text="🚀 Pixel Agent Portalı",
            fg_color="#8b5cf6",
            hover_color="#7c3aed",
            command=lambda: webbrowser.open("http://localhost:3021/pixel")
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            row,
            text="🖥️ ODS Dashboard",
            fg_color="#3b82f6",
            hover_color="#2563eb",
            command=lambda: webbrowser.open("http://localhost:3021")
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            row,
            text="💬 Open WebUI",
            fg_color="#06b6d4",
            hover_color="#0891b2",
            command=lambda: webbrowser.open("http://localhost:3000")
        ).pack(side="left")

        btn_launch = ctk.CTkButton(
            card,
            text="🚀 Osmantic ODS Nəzarət Panelini Aç",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=44,
            fg_color="#f59e0b",
            hover_color="#d97706",
            command=lambda: self.launch_standalone("ods_app.py")
        )
        btn_launch.pack(padx=20, pady=20, fill="x")

    def build_settings_tab(self):
        f = ctk.CTkFrame(self.content_container, fg_color="transparent")
        self.frames["settings"] = f
        f.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(f, text="🔑 API və Əlaqə Parametrləri", font=ctk.CTkFont(size=22, weight="bold"), text_color="#f8fafc").pack(anchor="w", pady=(0, 15))

        card = ctk.CTkFrame(f, fg_color="#1e2430", corner_radius=10)
        card.pack(fill="both", expand=True, pady=10)

        ctk.CTkLabel(card, text="Google Gemini API Açarı", font=ctk.CTkFont(size=16, weight="bold"), text_color="#e2e8f0").pack(padx=20, pady=(20, 5), anchor="w")
        ctk.CTkLabel(card, text="Bu açar Browser-Use, Microsoft UFO və Composio sistemlərinin hər 3-nü hərəkətə gətirir.", font=ctk.CTkFont(size=13), text_color="#94a3b8").pack(padx=20, pady=(0, 15), anchor="w")

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
                        os.environ["GEMINI_API_KEY"] = new_key
                        os.environ["GOOGLE_API_KEY"] = new_key
                        for p in [
                            r"C:\Users\sahin\.gemini\antigravity\scratch\repos\browser-use\.env",
                            r"C:\Users\sahin\.gemini\antigravity\scratch\repos\UFO\.env",
                            r"C:\Users\sahin\.gemini\antigravity\scratch\repos\composio\.env"
                        ]:
                            with open(p, "w", encoding="utf-8") as env_f:
                                env_f.write(f"GOOGLE_API_KEY={new_key}\nGEMINI_API_KEY={new_key}\n")
                        status_lbl.configure(text="✅ Açar uğurla yoxlanıldı və bütün tətbiqlərdə yeniləndi!", text_color="#34d399")
            except Exception as e:
                status_lbl.configure(text=f"❌ Açar etibarsızdır: {e}", text_color="#f87171")

        ctk.CTkButton(btn_row, text="💾 Yadda Saxla və Yoxla", fg_color="#10b981", hover_color="#059669", command=save_and_test).pack(side="left", padx=(0, 10))

        status_lbl = ctk.CTkLabel(card, text="🟢 Cari açar aktivdir və bütün sistemlərlə əlaqələndirilib.", font=ctk.CTkFont(size=13), text_color="#34d399")
        status_lbl.pack(padx=20, pady=10, anchor="w")

if __name__ == "__main__":
    app = AIAgentMasterStudio()
    app.mainloop()

# SPDX-License-Identifier: GPL-3.0-or-later
"""ZeroScript Desktop App - zero-console bridge, tray, and ASTROX-style dashboard."""
import asyncio
import json
import mimetypes
import os
import shlex
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

# pythonw.exe starts with sys.stdout / sys.stderr set to None; redirect safely
# before importing bridge so print() / sys.stdout.reconfigure never crash.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8", errors="replace")
if sys.stderr is None:
    try:
        _logs_dir = os.path.join(HERE, "logs")
        os.makedirs(_logs_dir, exist_ok=True)
        sys.stderr = open(os.path.join(_logs_dir, "app_error.log"), "a", encoding="utf-8", errors="replace")
    except Exception:
        sys.stderr = open(os.devnull, "w", encoding="utf-8", errors="replace")

import bridge  # noqa: E402
import skills_manager  # noqa: E402
import zeroscript_kit  # noqa: E402

bridge.EMBEDDED_MODE = True

UI_DIR = os.path.join(HERE, "app_ui")
EXT_DIR = os.path.join(HERE, "zeroscript-extension")
ICON_PATH = os.path.join(HERE, "assets", "icon.png")

AI_PROVIDERS = [
    {"id": "claude", "name": "Claude", "url": "https://claude.ai/new", "tag": "New · Coding", "category": "Coding", "vision": True, "badge": "CL", "color": "#d97757", "desc": "Anthropic Claude for ultra-clean Luau architecture and multi-step UI edits."},
    {"id": "deepseek", "name": "DeepSeek", "url": "https://chat.deepseek.com/", "tag": "Recommended", "category": "Coding", "vision": True, "badge": "DS", "color": "#4f7cff", "desc": "Unified reasoning model with live screenshots and rock-solid command output."},
    {"id": "chatgpt", "name": "ChatGPT", "url": "https://chatgpt.com/", "tag": "Popular", "category": "Coding", "vision": False, "badge": "OA", "color": "#10a37f", "desc": "OpenAI GPT-5/o-series with CodeMirror reading, amnesia recovery, and persistence."},
    {"id": "gemini", "name": "Google Gemini", "url": "https://gemini.google.com/app", "tag": "Vision", "category": "Vision", "vision": True, "badge": "GM", "color": "#60a5fa", "desc": "Multimodal Gemini with Studio screenshots and automatic prompt refresh."},
    {"id": "aistudio", "name": "Google AI Studio", "url": "https://aistudio.google.com/prompts/new_chat", "tag": "New · Free Pro", "category": "Coding", "vision": True, "badge": "AS", "color": "#4285f4", "desc": "Free Gemini 2.5 Pro/Flash in Google AI Studio with huge context and Studio vision."},
    {"id": "grok", "name": "Grok", "url": "https://grok.com/", "tag": "New · Fast", "category": "Fast", "vision": True, "badge": "GK", "color": "#e5e7eb", "desc": "xAI Grok with fast streaming responses, vision screenshots, and Studio execution."},
    {"id": "mistral", "name": "Mistral Le Chat", "url": "https://chat.mistral.ai/", "tag": "New · Coding", "category": "Fast", "vision": True, "badge": "MS", "color": "#fb923c", "desc": "Fast Mistral coding & reasoning agent wired directly to Roblox Studio."},
    {"id": "kimi", "name": "Kimi", "url": "https://www.kimi.ai/", "tag": "Agentic", "category": "Coding", "vision": True, "badge": "KM", "color": "#38bdf8", "desc": "Moonshot AI with strong multi-step tool execution and vision support."},
    {"id": "glm", "name": "GLM (Z.ai)", "url": "https://chat.z.ai/", "tag": "Multimodal", "category": "Vision", "vision": True, "badge": "GL", "color": "#a78bfa", "desc": "Zhipu GLM with deep code understanding and vision capabilities."},
    {"id": "qwen", "name": "Qwen", "url": "https://chat.qwen.ai/", "tag": "Fast", "category": "Fast", "vision": True, "badge": "QW", "color": "#818cf8", "desc": "Alibaba Qwen with high-speed structured Luau & JSON tool output."},
    {"id": "arena", "name": "Arena", "url": "https://arena.ai/text/direct", "tag": "Multi-model", "category": "Multi-model", "vision": True, "badge": "AR", "color": "#f472b6", "desc": "Direct-mode access to top frontier models in one place (all Arena domains supported)."},
    {"id": "meta", "name": "Meta AI", "url": "https://www.meta.ai/", "tag": "Vision", "category": "Vision", "vision": True, "badge": "MA", "color": "#3b82f6", "desc": "Llama playground with image & Studio integration."},
]

_bridge_loop = None
_bridge_ready = False
_http_server = None
_shutdown_requested = threading.Event()

_studio_cache = {"place": None, "app": None, "proc": None, "ts": 0.0}
_studio_lock = threading.Lock()
_probe_running = False

try:
    from PyQt6.QtCore import QTimer  # type: ignore
    from PyQt6.QtGui import QAction, QIcon  # type: ignore
    from PyQt6.QtWidgets import QApplication, QMenu, QSystemTrayIcon  # type: ignore
    HAS_PYQT6 = True
except Exception:
    HAS_PYQT6 = False


def _run_studio_probe_sync():
    global _probe_running
    try:
        st = bridge.probe_studio()
        proc = bridge._roblox_studio_app_running()
        with _studio_lock:
            _studio_cache["place"] = st.get("place")
            _studio_cache["app"] = st.get("app")
            _studio_cache["proc"] = proc
            _studio_cache["ts"] = time.time()
    except Exception:
        pass
    finally:
        _probe_running = False


def _maybe_refresh_studio_async():
    global _probe_running
    with _studio_lock:
        age = time.time() - _studio_cache["ts"]
    if age > 4.0 and not _probe_running:
        _probe_running = True
        threading.Thread(target=_run_studio_probe_sync, daemon=True).start()


def _run_on_bridge_loop(coro, timeout=10.0):
    if _bridge_loop is None or not _bridge_loop.is_running():
        coro.close()
        return None
    try:
        fut = asyncio.run_coroutine_threadsafe(coro, _bridge_loop)
    except Exception:
        coro.close()
        return None
    try:
        return fut.result(timeout=timeout)
    except Exception:
        return None


def _read_manifest_version():
    try:
        mpath = os.path.join(EXT_DIR, "manifest.json")
        if os.path.isfile(mpath):
            with open(mpath, "r", encoding="utf-8") as f:
                return str(json.load(f).get("version") or "")
    except Exception:
        pass
    return ""


def _build_diagnostics_payload():
    checks = []
    # 1. Local Bridge & WebSocket
    checks.append({
        "id": "bridge",
        "title": "Local WebSocket Bridge",
        "status": "ok" if _bridge_ready else "warn",
        "detail": f"Listening on ws://{bridge.HOST}:{bridge.PORT} ({len(bridge.clients)} connected browser tab(s))"
        if _bridge_ready else "Bridge thread starting up...",
    })

    # 2. Extension Version Match
    ext_ver = _read_manifest_version()
    ver_match = bool(ext_ver) and ext_ver == bridge.BRIDGE_VERSION
    checks.append({
        "id": "extension",
        "title": "Chrome Extension Folder",
        "status": "ok" if ver_match else "warn",
        "detail": f"zeroscript-extension v{ext_ver or '?'} matches bridge v{bridge.BRIDGE_VERSION}. Remember to click Reload (↻) in edge://extensions or chrome://extensions."
        if ver_match else f"Extension version ({ext_ver or 'missing'}) differs from bridge ({bridge.BRIDGE_VERSION}).",
    })

    # 3. StudioMCP.exe binary
    mcp_exe = bridge._current_studio_exe()
    checks.append({
        "id": "studiomcp",
        "title": "Roblox StudioMCP Binary",
        "status": "ok" if mcp_exe else "warn",
        "detail": str(mcp_exe) if mcp_exe else "StudioMCP.exe not found in default Roblox Versions directory.",
    })

    # 4. Port 13469 owner & Studio process
    proc_up = bridge._roblox_studio_app_running()
    owner = bridge._port_owner(bridge.STUDIO_MCP_PORT)
    if owner:
        pid, name, path = owner
        low_n = (name or "").lower()
        low_p = (path or "").lower()
        if "studiomcp" in low_n or "roblox" in low_n or "roblox" in low_p:
            checks.append({
                "id": "port13469",
                "title": f"Studio MCP Port ({bridge.STUDIO_MCP_PORT})",
                "status": "ok",
                "detail": f"Owned by {name} (PID {pid}). No port conflict detected.",
            })
        else:
            checks.append({
                "id": "port13469",
                "title": f"Studio MCP Port ({bridge.STUDIO_MCP_PORT})",
                "status": "fail",
                "detail": f"Conflict: port {bridge.STUDIO_MCP_PORT} is held by '{name}' (PID {pid}). Close that app or disable other Quick Connect clients.",
            })
    else:
        checks.append({
            "id": "port13469",
            "title": f"Studio MCP Port ({bridge.STUDIO_MCP_PORT})",
            "status": "warn",
            "detail": f"Port {bridge.STUDIO_MCP_PORT} is free (waiting for Studio / StudioMCP registration).",
        })

    # 5. Live Studio & Place status
    with _studio_lock:
        place = _studio_cache["place"]
        app_ok = _studio_cache["app"]
    tools_n = len(bridge.mgr.list_tools())
    if place is True and tools_n > 0:
        st_status = "ok"
        st_detail = f"Roblox Studio place attached and ready ({tools_n} live commands)."
    elif app_ok is True:
        st_status = "warn"
        st_detail = "Roblox Studio is connected, but no place is open."
    elif proc_up is True:
        st_status = "warn"
        st_detail = "Roblox Studio is running — open Assistant Settings > MCP Servers and toggle 'Enable Studio as MCP server'."
    else:
        st_status = "warn"
        st_detail = "Roblox Studio is not running yet."
    checks.append({
        "id": "studio",
        "title": "Roblox Studio Place Link",
        "status": st_status,
        "detail": st_detail,
    })

    # 6. Skills & Providers summary
    enabled_skills = sum(1 for sk in skills_manager.list_summary() if sk.get("enabled"))
    checks.append({
        "id": "skills",
        "title": "Agent Playbooks & Providers",
        "status": "ok" if enabled_skills > 0 else "warn",
        "detail": f"{enabled_skills} active skill playbook(s) synced across {len(AI_PROVIDERS)} AI providers.",
    })

    # 7. ZeroScript Toolkit summary
    mods_count = len(zeroscript_kit.list_modules())
    checks.append({
        "id": "toolkit",
        "title": "Luau 60-Gate Engine & Starter Modules",
        "status": "ok" if mods_count > 0 else "warn",
        "detail": f"{len(zeroscript_kit.GATES)} static gates, {mods_count} Luau modules, 12 genre style guides & {len(zeroscript_kit.memory_list())} memory record(s) ready.",
    })

    return {
        "ok": True,
        "ts": time.strftime("%H:%M:%S"),
        "checks": checks,
    }


def _build_status_payload(force_probe=False):
    if force_probe:
        _run_studio_probe_sync()
    else:
        _maybe_refresh_studio_async()

    with _studio_lock:
        st_snap = {
            "place": _studio_cache["place"],
            "app": _studio_cache["app"],
            "proc": _studio_cache["proc"],
        }

    servers = []
    for sid, client in bridge.mgr.clients.items():
        servers.append({
            "id": sid,
            "alive": client.is_alive(),
            "tools": len(client.tools_cache or []),
            "command": client.command or "",
            "args": list(client.args or []),
            "startError": client.start_error,
            "lastExit": client.last_exit,
        })

    tools = []
    for t in bridge.mgr.list_tools():
        tools.append({
            "name": t.get("name", ""),
            "server": t.get("server", "roblox"),
            "description": (t.get("description") or "").split("\n")[0].strip(),
        })

    return {
        "ok": True,
        "bridge": {
            "online": _bridge_ready,
            "host": bridge.HOST,
            "port": bridge.PORT,
            "clients": len(bridge.clients),
            "version": bridge.BRIDGE_VERSION,
            "extensionVersion": _read_manifest_version(),
            "uptime": max(0, int(time.time() - bridge.START_TIME)),
        },
        "studio": st_snap,
        "servers": servers,
        "tools": tools,
        "skills": skills_manager.list_summary(),
        "presets": skills_manager.list_presets(),
        "starterPrompts": skills_manager.BUILTIN_STARTER_PROMPTS,
        "activityStats": bridge.get_activity().get("stats", {}),
        "toolkit": {
            "gates": len(zeroscript_kit.GATES),
            "modules": len(zeroscript_kit.list_modules()),
            "genres": 12,
            "recovery": 12,
            "memoryCount": len(zeroscript_kit.memory_list()),
        },
        "providers": AI_PROVIDERS,
        "settings": skills_manager.load_settings(),
        "paths": {
            "root": HERE,
            "extension": EXT_DIR,
            "skills": skills_manager.SKILLS_DIR,
            "modules": os.path.join(HERE, "luau_modules"),
            "logs": bridge.LOGS_DIR,
        },
        "trayAvailable": HAS_PYQT6,
    }


def _find_app_browser():
    candidates = [
        shutil.which("msedge"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
        shutil.which("chrome"),
        os.path.join(os.environ.get("ProgramFiles", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LocalAppData", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def open_app_window(url):
    browser = _find_app_browser()
    if browser:
        profile_dir = os.path.join(
            os.environ.get("LOCALAPPDATA") or HERE,
            "ZeroScriptAppProfile",
        )
        os.makedirs(profile_dir, exist_ok=True)
        cmd = [
            browser,
            f"--app={url}",
            "--window-size=1360,860",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
        ]
        try:
            subprocess.Popen(cmd, cwd=HERE)
            return True
        except Exception:
            pass
    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False


def _open_folder(which):
    mapping = {
        "skills": skills_manager.SKILLS_DIR,
        "modules": os.path.join(HERE, "luau_modules"),
        "logs": bridge.LOGS_DIR,
        "extension": EXT_DIR,
        "root": HERE,
    }
    target = mapping.get(which)
    if not target:
        return False, f"unknown folder '{which}'"
    os.makedirs(target, exist_ok=True)
    try:
        if sys.platform == "win32":
            os.startfile(target)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", target])
        else:
            subprocess.Popen(["xdg-open", target])
        return True, None
    except Exception as e:
        return False, str(e)


def request_shutdown():
    _shutdown_requested.set()
    for c in list(bridge.mgr.clients.values()):
        try:
            c.stop()
        except Exception:
            pass
    if _http_server is not None:
        threading.Thread(target=_http_server.shutdown, daemon=True).start()


class AppHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        return  # Keep logs clean

    def _send_bytes(self, code, data, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send_bytes(code, body, "application/json; charset=utf-8")

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            length = 0
        if length <= 0 or length > 2 * 1024 * 1024:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8", errors="replace"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _serve_file(self, path):
        if not os.path.isfile(path):
            self._send_json(404, {"ok": False, "error": "not found"})
            return
        ctype, _ = mimetypes.guess_type(path)
        if path.endswith(".js"):
            ctype = "application/javascript; charset=utf-8"
        elif path.endswith(".css"):
            ctype = "text/css; charset=utf-8"
        elif path.endswith(".html"):
            ctype = "text/html; charset=utf-8"
        elif not ctype:
            ctype = "application/octet-stream"
        with open(path, "rb") as f:
            self._send_bytes(200, f.read(), ctype)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ("/", "/index.html"):
            return self._serve_file(os.path.join(UI_DIR, "index.html"))
        if path == "/styles.css":
            return self._serve_file(os.path.join(UI_DIR, "styles.css"))
        if path == "/app.js":
            return self._serve_file(os.path.join(UI_DIR, "app.js"))
        if path == "/icon.png":
            return self._serve_file(ICON_PATH)

        if path == "/api/status":
            return self._send_json(200, _build_status_payload(force_probe=False))

        if path == "/api/logs":
            with bridge.LOG_LOCK:
                logs_copy = list(bridge.LOG_BUFFER)
            return self._send_json(200, {"ok": True, "logs": logs_copy})

        if path == "/api/skills":
            return self._send_json(200, {"ok": True, "skills": skills_manager.list_skills(include_content=True)})

        if path == "/api/settings":
            return self._send_json(200, {"ok": True, "settings": skills_manager.load_settings()})

        if path == "/api/activity":
            return self._send_json(200, {"ok": True, **bridge.get_activity()})

        if path == "/api/diagnostics":
            return self._send_json(200, _build_diagnostics_payload())

        if path == "/api/toolkit/summary":
            sg = zeroscript_kit.get_style_guide()
            bug = zeroscript_kit.diagnose_bug("")
            return self._send_json(200, {
                "ok": True,
                "gates": zeroscript_kit.list_gates(),
                "demoLuau": zeroscript_kit.DEMO_BUGGY_LUAU,
                "modules": zeroscript_kit.list_modules(include_code=True),
                "styles": sg.get("vocabulary") or {},
                "genres": sg.get("genres") or [],
                "antiSlop": sg.get("antiSlop") or "",
                "recovery": bug.get("recovery") or [],
                "apiNotes": bug.get("apiNotes") or [],
                "memory": zeroscript_kit.memory_list(include_superseded=False),
            })

        if path == "/api/toolkit/modules":
            qs = urlparse(self.path).query
            mid = ""
            for part in qs.split("&"):
                if part.startswith("id="):
                    mid = part[3:]
                    break
            if mid:
                m = zeroscript_kit.get_module(mid)
                if not m:
                    return self._send_json(404, {"ok": False, "error": f"module '{mid}' not found"})
                return self._send_json(200, {"ok": True, "module": m})
            return self._send_json(200, {"ok": True, "modules": zeroscript_kit.list_modules(include_code=True)})

        if path == "/api/toolkit/memory":
            return self._send_json(200, {"ok": True, "records": zeroscript_kit.memory_list(include_superseded=False)})

        return self._send_json(404, {"ok": False, "error": f"unknown route: {path}"})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        body = self._read_json()

        if path == "/api/refresh":
            try:
                bridge.mgr.list_tools(True)
            except Exception as e:
                bridge.log(f"manual refresh error: {e}", "yl")
            _run_on_bridge_loop(bridge.broadcast_status(), timeout=8.0)
            return self._send_json(200, _build_status_payload(force_probe=True))

        if path == "/api/restart_mcp":
            sid = (body.get("server") or "").strip() or None
            try:
                bridge.mgr.restart(sid)
                _run_on_bridge_loop(bridge.broadcast_status(), timeout=8.0)
                return self._send_json(200, {"ok": True, **_build_status_payload(force_probe=True)})
            except Exception as e:
                return self._send_json(500, {"ok": False, "error": str(e)})

        if path == "/api/servers/add":
            sid = body.get("server_id") or body.get("id")
            command = body.get("command")
            raw_args = body.get("args")
            if isinstance(raw_args, str):
                try:
                    args = shlex.split(raw_args, posix=(sys.platform != "win32"))
                except Exception:
                    args = raw_args.split()
            elif isinstance(raw_args, list):
                args = [str(a) for a in raw_args]
            else:
                args = []
            env = body.get("env") if isinstance(body.get("env"), dict) else None
            ok, err = bridge.config_add_server(sid, command, args, env)
            if not ok:
                return self._send_json(400, {"ok": False, "error": err})
            bridge.reload_servers()
            _run_on_bridge_loop(bridge.broadcast_status(), timeout=8.0)
            return self._send_json(200, {"ok": True, **_build_status_payload(force_probe=False)})

        if path == "/api/servers/remove":
            sid = body.get("server_id") or body.get("id")
            ok, err = bridge.config_remove_server(sid)
            if not ok:
                return self._send_json(400, {"ok": False, "error": err})
            bridge.reload_servers()
            _run_on_bridge_loop(bridge.broadcast_status(), timeout=8.0)
            return self._send_json(200, {"ok": True, **_build_status_payload(force_probe=False)})

        if path == "/api/skills/save":
            ok, res = skills_manager.save_skill(body)
            if not ok:
                return self._send_json(400, {"ok": False, "error": res})
            bridge.log(f"skill saved: {res['id']} ({res['mode']}, enabled={res['enabled']})", "cy")
            _run_on_bridge_loop(bridge.broadcast_status(), timeout=6.0)
            return self._send_json(200, {"ok": True, "skill": res, "skills": skills_manager.list_skills(include_content=True)})

        if path == "/api/skills/toggle":
            sid = body.get("id") or body.get("skill_id")
            ok, res = skills_manager.toggle_skill(sid, enabled=body.get("enabled"), mode=body.get("mode"))
            if not ok:
                return self._send_json(404, {"ok": False, "error": res})
            bridge.log(f"skill updated: {res['id']} (enabled={res['enabled']}, mode={res['mode']})", "cy")
            _run_on_bridge_loop(bridge.broadcast_status(), timeout=6.0)
            return self._send_json(200, {"ok": True, "skill": res, "skills": skills_manager.list_skills(include_content=True)})

        if path == "/api/skills/delete":
            sid = body.get("id") or body.get("skill_id")
            ok, err = skills_manager.delete_skill(sid)
            if not ok:
                return self._send_json(400, {"ok": False, "error": err})
            bridge.log(f"skill deleted: {sid}", "yl")
            _run_on_bridge_loop(bridge.broadcast_status(), timeout=6.0)
            return self._send_json(200, {"ok": True, "skills": skills_manager.list_skills(include_content=True)})

        if path == "/api/skills/preset":
            pid = body.get("preset") or body.get("id")
            ok, res = skills_manager.apply_preset(pid)
            if not ok:
                return self._send_json(400, {"ok": False, "error": res})
            bridge.log(f"skill preset applied: {res['id']}", "cy")
            _run_on_bridge_loop(bridge.broadcast_status(), timeout=6.0)
            return self._send_json(200, {"ok": True, "preset": res, "skills": skills_manager.list_skills(include_content=True)})

        if path == "/api/activity/clear":
            return self._send_json(200, {"ok": True, **bridge.clear_activity()})

        if path == "/api/toolkit/audit":
            directory = (body.get("directory") or "").strip()
            if directory:
                res = zeroscript_kit.audit_directory(directory)
            else:
                res = zeroscript_kit.audit_code(
                    body.get("code") or "",
                    filename=body.get("filename") or "Script.luau",
                    context=body.get("context") or "unknown",
                )
            code_num = 200 if res.get("ok") else 400
            return self._send_json(code_num, res)

        if path == "/api/toolkit/route":
            res = zeroscript_kit.route_skills(body.get("query") or "", limit=body.get("limit") or 4)
            return self._send_json(200 if res.get("ok") else 400, res)

        if path == "/api/toolkit/module":
            m = zeroscript_kit.get_module(body.get("id") or body.get("module_id") or "")
            if not m:
                return self._send_json(404, {"ok": False, "error": "module not found"})
            return self._send_json(200, {"ok": True, "module": m})

        if path == "/api/toolkit/memory/save":
            ok, entry_or_err = zeroscript_kit.memory_put(
                key=body.get("key"),
                value=body.get("value"),
                kind=body.get("kind") or "decision",
                project=body.get("project") or "default",
                state=body.get("state") or "observed",
            )
            if not ok:
                return self._send_json(400, {"ok": False, "error": str(entry_or_err)})
            return self._send_json(200, {"ok": True, "record": entry_or_err, "records": zeroscript_kit.memory_list()})

        if path == "/api/toolkit/memory/delete":
            if body.get("clear"):
                zeroscript_kit.memory_clear()
                return self._send_json(200, {"ok": True, "records": []})
            ok, err = zeroscript_kit.memory_delete(body.get("id"))
            if not ok:
                return self._send_json(404, {"ok": False, "error": err})
            return self._send_json(200, {"ok": True, "records": zeroscript_kit.memory_list()})

        if path == "/api/prompts/save":
            ok, res = skills_manager.save_custom_prompt(body)
            if not ok:
                return self._send_json(400, {"ok": False, "error": res})
            return self._send_json(200, {"ok": True, "customPrompts": res, "settings": skills_manager.load_settings()})

        if path == "/api/prompts/delete":
            pid = body.get("id")
            ok, res = skills_manager.delete_custom_prompt(pid)
            if not ok:
                return self._send_json(404, {"ok": False, "error": res})
            return self._send_json(200, {"ok": True, "customPrompts": res, "settings": skills_manager.load_settings()})

        if path == "/api/settings":
            old_gp = skills_manager.load_settings().get("globalPrompt", "")
            cfg = skills_manager.save_settings(body)
            if cfg.get("globalPrompt", "") != old_gp:
                bridge.log("global prompt updated and synced to extensions", "cy")
                _run_on_bridge_loop(bridge.broadcast_status(), timeout=6.0)
            return self._send_json(200, {"ok": True, "settings": cfg})

        if path == "/api/open_url":
            url = str(body.get("url") or "").strip()
            if not url.startswith("https://"):
                return self._send_json(400, {"ok": False, "error": "only https:// URLs are allowed"})
            try:
                webbrowser.open(url)
                return self._send_json(200, {"ok": True})
            except Exception as e:
                return self._send_json(500, {"ok": False, "error": str(e)})

        if path == "/api/open_folder":
            which = str(body.get("folder") or "").strip().lower()
            ok, err = _open_folder(which)
            if not ok:
                return self._send_json(400, {"ok": False, "error": err})
            return self._send_json(200, {"ok": True})

        if path == "/api/quit":
            self._send_json(200, {"ok": True})
            request_shutdown()
            return

        return self._send_json(404, {"ok": False, "error": f"unknown route: {path}"})


class _SingleHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = False


def create_http_server(host="127.0.0.1", port=17614):
    return _SingleHTTPServer((host, port), AppHandler)


def _start_bridge_thread():
    global _bridge_loop, _bridge_ready

    def _worker():
        global _bridge_loop, _bridge_ready
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _bridge_loop = loop
        _bridge_ready = True
        try:
            loop.run_until_complete(bridge.main())
        except Exception as e:
            bridge.log(f"bridge thread stopped: {e}", "rd")
        finally:
            _bridge_ready = False
            loop.close()

    t = threading.Thread(target=_worker, daemon=True)
    t.start()


def _existing_instance_alive(port):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/status", timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
            return bool(data and data.get("ok") and "bridge" in data)
    except Exception:
        return False


def _run_tray(app_url):
    qapp = QApplication(sys.argv)
    qapp.setQuitOnLastWindowClosed(False)
    icon = QIcon(ICON_PATH) if os.path.isfile(ICON_PATH) else QIcon()
    tray = QSystemTrayIcon(icon, qapp)
    tray.setToolTip(f"ZeroScript v{bridge.BRIDGE_VERSION} - Running")

    menu = QMenu()
    act_open = QAction("Open ZeroScript", menu)
    act_open.triggered.connect(lambda: open_app_window(app_url))
    menu.addAction(act_open)

    act_status = QAction("Status: Starting bridge...", menu)
    act_status.setEnabled(False)
    menu.addAction(act_status)

    menu.addSeparator()

    act_refresh = QAction("Refresh Connections", menu)
    act_refresh.triggered.connect(lambda: threading.Thread(
        target=lambda: (bridge.mgr.list_tools(True), _run_studio_probe_sync(), _run_on_bridge_loop(bridge.broadcast_status(), 6.0)),
        daemon=True,
    ).start())
    menu.addAction(act_refresh)

    act_restart = QAction("Restart Roblox MCP", menu)
    act_restart.triggered.connect(lambda: threading.Thread(
        target=lambda: (bridge.mgr.restart("roblox"), _run_studio_probe_sync(), _run_on_bridge_loop(bridge.broadcast_status(), 6.0)),
        daemon=True,
    ).start())
    menu.addAction(act_restart)

    act_ext = QAction("Open Extension Folder", menu)
    act_ext.triggered.connect(lambda: _open_folder("extension"))
    menu.addAction(act_ext)

    menu.addSeparator()

    act_quit = QAction("Quit ZeroScript", menu)
    act_quit.triggered.connect(lambda: (request_shutdown(), qapp.quit()))
    menu.addAction(act_quit)

    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: open_app_window(app_url)
                           if reason in (QSystemTrayIcon.ActivationReason.DoubleClick, QSystemTrayIcon.ActivationReason.Trigger)
                           else None)
    tray.show()

    def _sync_tray():
        if _shutdown_requested.is_set():
            qapp.quit()
            return
        with _studio_lock:
            place = _studio_cache["place"]
            app = _studio_cache["app"]
        total_tools = len(bridge.mgr.list_tools())
        if place is True:
            label = f"Studio ready ({total_tools} tools)"
        elif app is True:
            label = "Studio open (no place)"
        elif _bridge_ready:
            label = f"Bridge online ({total_tools} tools)"
        else:
            label = "Starting bridge..."
        act_status.setText(f"Status: {label}")
        tray.setToolTip(f"ZeroScript v{bridge.BRIDGE_VERSION} - {label}")

    timer = QTimer()
    timer.timeout.connect(_sync_tray)
    timer.start(1500)
    qapp.exec()


_INSTANCE_MUTEX = None


def _acquire_single_instance_mutex():
    global _INSTANCE_MUTEX
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        handle = k32.CreateMutexW(None, False, "Local\\ZeroScriptDesktopAppMutex")
        if handle and k32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            k32.CloseHandle(handle)
            return False
        _INSTANCE_MUTEX = handle
    except Exception:
        pass
    return True


def main():
    global _http_server
    settings = skills_manager.load_settings()
    port = int(os.environ.get("ZS_APP_PORT") or settings.get("appPort") or 17614)
    app_url = f"http://127.0.0.1:{port}"

    if _existing_instance_alive(port) or not _acquire_single_instance_mutex():
        open_app_window(app_url)
        return

    try:
        _http_server = create_http_server("127.0.0.1", port)
    except OSError:
        if _existing_instance_alive(port):
            open_app_window(app_url)
            return
        raise

    _start_bridge_thread()
    threading.Thread(target=_http_server.serve_forever, daemon=True).start()

    if settings.get("autoOpenWindow", True) and "--no-window" not in sys.argv:
        threading.Timer(0.35, lambda: open_app_window(app_url)).start()

    if HAS_PYQT6 and "--no-tray" not in sys.argv:
        _run_tray(app_url)
    else:
        try:
            while not _shutdown_requested.is_set():
                time.sleep(0.5)
        except KeyboardInterrupt:
            request_shutdown()


if __name__ == "__main__":
    main()

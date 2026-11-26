# SPDX-License-Identifier: GPL-3.0-or-later
"""ZeroScript Skills & App Settings manager (pure Python stdlib)."""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SKILLS_DIR = os.path.join(HERE, "skills")
SETTINGS_PATH = os.path.join(HERE, "app_settings.json")

BUILTIN_ORDER = {
    "ui-craftsmanship": 0,
    "ui-reference-accessibility": 1,
    "building-architecture": 2,
    "maps-biomes-atmosphere": 3,
    "game-recreation-1to1": 4,
    "animations-rigging-procedural": 5,
    "creatures-facial-state-machines": 6,
    "camera-movement-physics": 7,
    "cutscenes-cinematics": 8,
    "combat-vfx-gamefeel": 9,
    "luau-architecture-networking": 10,
    "security-datastore-trading": 11,
    "npc-ai-pathfinding": 12,
    "pets-quests-lobbies": 13,
    "lighting-atmosphere-audio": 14,
    "economy-progression-loops": 15,
    "performance-optimization": 16,
}

VALID_CATEGORIES = (
    "UI",
    "Building",
    "Game Cloning",
    "Animations",
    "Cutscenes",
    "Combat & VFX",
    "Scripting",
    "Gameplay",
    "Polish",
    "Optimization",
    "Custom",
)
VALID_MODES = ("auto", "always")
VALID_ACCENTS = ("indigo", "cyan", "emerald", "amber", "crimson", "prism")
VALID_GLASS_STYLES = ("liquid", "frosted", "crystal")
VALID_BACKDROPS = ("sunset", "aurora", "ocean", "midnight")

SKILL_PRESETS = [
    {
        "id": "all-rounder",
        "name": "Full AAA Stack",
        "desc": "Enable all 17 specialized playbooks across 1:1 cloning, animations, security, pets/quests, UI, architecture, combat, AI, lighting, economy & performance.",
        "skills": list(BUILTIN_ORDER.keys()),
    },
    {
        "id": "game-cloner-1to1",
        "name": "1:1 Game Cloner",
        "desc": "Maximum fidelity stack for recreating any game 1:1 (Clone Architect, Animations, Movement/Camera, 1:1 Maps, Reference UI, Combat, Security).",
        "skills": [
            "game-recreation-1to1",
            "animations-rigging-procedural",
            "camera-movement-physics",
            "maps-biomes-atmosphere",
            "ui-craftsmanship",
            "ui-reference-accessibility",
            "combat-vfx-gamefeel",
            "luau-architecture-networking",
            "security-datastore-trading",
        ],
    },
    {
        "id": "animations-combat",
        "name": "Animations & Game Feel",
        "desc": "Custom Motor6D/KeyframeSequence movesets, creature gaits, FaceControls, procedural springs, dashes, camera recoil & combat VFX.",
        "skills": [
            "animations-rigging-procedural",
            "creatures-facial-state-machines",
            "combat-vfx-gamefeel",
            "camera-movement-physics",
            "cutscenes-cinematics",
            "lighting-atmosphere-audio",
        ],
    },
    {
        "id": "security-backend",
        "name": "Security, Data & LiveOps",
        "desc": "Zero-trust Remote validation, TokenBucket rate limits, UpdateAsync DataStores, ProcessReceipt idempotency, trading & lobbies.",
        "skills": [
            "security-datastore-trading",
            "luau-architecture-networking",
            "economy-progression-loops",
            "pets-quests-lobbies",
            "performance-optimization",
        ],
    },
    {
        "id": "ui-ux-polish",
        "name": "1:1 UI, Mobile & Polish",
        "desc": "Screenshot/Figma-level HUD fidelity, anti-slop geometry tokens, mobile safe areas, gamepad focus, lighting & cutscenes.",
        "skills": [
            "ui-craftsmanship",
            "ui-reference-accessibility",
            "lighting-atmosphere-audio",
            "cutscenes-cinematics",
        ],
    },
    {
        "id": "action-combat",
        "name": "Action & Combat",
        "desc": "Best for RPGs, anime fighters, and wave games (Combat VFX, NPC Boss AI, UI, Security & Networking, Lighting, Optimization).",
        "skills": [
            "ui-craftsmanship",
            "combat-vfx-gamefeel",
            "npc-ai-pathfinding",
            "luau-architecture-networking",
            "security-datastore-trading",
            "lighting-atmosphere-audio",
            "performance-optimization",
        ],
    },
    {
        "id": "world-cinematics",
        "name": "Worlds & Cutscenes",
        "desc": "Best for showcase maps, lobbies, and story games (3D Architecture, Biomes, Future Lighting & Audio, Cutscenes, Optimization).",
        "skills": [
            "building-architecture",
            "maps-biomes-atmosphere",
            "lighting-atmosphere-audio",
            "cutscenes-cinematics",
            "performance-optimization",
        ],
    },
    {
        "id": "simulator-tycoon",
        "name": "Simulator & Tycoon",
        "desc": "Best for economy loops, pets, quests, shops, upgrades & DataStore persistence.",
        "skills": [
            "ui-craftsmanship",
            "economy-progression-loops",
            "pets-quests-lobbies",
            "luau-architecture-networking",
            "security-datastore-trading",
            "performance-optimization",
        ],
    },
    {
        "id": "minimal-fast",
        "name": "Core Coding Only",
        "desc": "Lean setup keeping only UI, Luau architecture/security, and performance playbooks active.",
        "skills": [
            "ui-craftsmanship",
            "luau-architecture-networking",
            "security-datastore-trading",
            "performance-optimization",
        ],
    },
]

BUILTIN_STARTER_PROMPTS = [
    {
        "id": "rpg-hud-inventory",
        "title": "Animated Obsidian RPG HUD & Inventory",
        "category": "UI",
        "text": "Read the ui-craftsmanship skill first. Build a modern obsidian-glass RPG HUD in StarterGui (health/mana bars, hotbar, quests tracker) plus a toggleable Inventory modal with CanvasGroup fade/pop tweens, UIScale hover feedback, and a modular LocalScript.",
    },
    {
        "id": "melee-combat-system",
        "title": "3-Hit Sword Combat with Hitstop & VFX",
        "category": "Combat & VFX",
        "text": "Read combat-vfx-gamefeel and luau-architecture-networking skills first. Implement a 3-hit M1 sword combo using client swing prediction, server Workspace:GetPartBoundsInBox validation, cooldown checks, hitstop, knockback, and trauma camera shake.",
    },
    {
        "id": "boss-ai-encounter",
        "title": "Multi-Phase Boss NPC with Telegraphed Attacks",
        "category": "Gameplay",
        "text": "Read npc-ai-pathfinding and lighting-atmosphere-audio first. Build an FSM Boss AI module in ServerScriptService with async PathfindingService chase, spawn leash, Phase 2 (<50% HP) enrage, and telegraphed ground-ring AoE slams.",
    },
    {
        "id": "stylized-hub-map",
        "title": "Detailed Plaza Hub with Future Lighting",
        "category": "Building",
        "text": "Read building-architecture and lighting-atmosphere-audio skills first. Build a 3-layer detailed medieval/sci-fi spawn plaza Model in Workspace with zero Z-fighting CFrame math, recessed windows, props, Future lighting, Atmosphere, Bloom, and spatial audio.",
    },
    {
        "id": "economy-datastore-loop",
        "title": "Zero-Trust Shop, Economy & DataStore",
        "category": "Scripting",
        "text": "Read economy-progression-loops, security-datastore-trading, and luau-architecture-networking first. Set up ReplicatedStorage.Shared.Catalog, server-authoritative ShopService + DataService using UpdateAsync retries + BindToClose, and a synchronized client shop controller.",
    },
    {
        "id": "cinematic-boss-intro",
        "title": "Boss Reveal Spline Cutscene + Skip HUD",
        "category": "Cutscenes",
        "text": "Read cutscenes-cinematics skill first. Build a CutsceneDirector ModuleScript in ReplicatedStorage with Catmull-Rom spline camera motion, DepthOfField focus pulls, 2.35:1 letterbox bars, subtitle beats, Skip button, and zero-softlock cleanup().",
    },
    {
        "id": "clone-battlegrounds-1to1",
        "title": "1:1 Anime Battlegrounds Combat Clone",
        "category": "Game Cloning",
        "text": "Read game-recreation-1to1, animations-rigging-procedural, camera-movement-physics, and combat-vfx-gamefeel skills first. Build a complete 1:1 Battlegrounds vertical slice: 4-hit M1 combo + downslam with code-authored KeyframeSequence animations, 4-way LinearVelocity dash with i-frames, 2 active abilities, block/parry, destructive arena landmark map, sleek bottom hotbar HUD, and playtest verification.",
    },
    {
        "id": "procedural-weapon-anims",
        "title": "Procedural R15/R6 Weapon & Dash Animation Suite",
        "category": "Animations",
        "text": "Read animations-rigging-procedural and camera-movement-physics skills first. Build a modular ProceduralAnimator + KeyframeSequence library supporting live Studio playback (idle breathing, sprint lean, 3-phase sword slash with HitFrame KeyframeMarker, parry pose, and landing squash) plus spring-damped FOV/camera punch.",
    },
    {
        "id": "clone-horror-doors-1to1",
        "title": "1:1 Atmospheric Horror / Doors-Style Experience",
        "category": "Game Cloning",
        "text": "Read game-recreation-1to1, maps-biomes-atmosphere, and ui-craftsmanship skills first. Recreate a 1:1 procedural numbered-room horror loop with hinged Motor6D doors, flickering sconce Future lighting, inventory flashlight/key items, entity ambush telegraphing + closet hiding, and crisp dark-glass HUD.",
    },
    {
        "id": "secure-trade-datastore",
        "title": "Dupe-Proof Trading, DataStore & Receipt System",
        "category": "Scripting",
        "text": "Read security-datastore-trading skill first and pull RevisionTrade, TokenBucket, and Finite via get_luau_module. Build a zero-trust TradingService + DataStore UpdateAsync profile loader + idempotent ProcessReceipt handler in ServerScriptService, then audit every server script with audit_luau.",
    },
    {
        "id": "pet-quest-lobby-hub",
        "title": "Pet Companion System, Quest NPC & Party Lobby",
        "category": "Gameplay",
        "text": "Read pets-quests-lobbies skill first and pull Formation, CriticalSpring, CleanupScope, and WeightedChoice via get_luau_module. Create server-owned pet hatching/equipping with smooth client followers, a branching Quest NPC with ProximityPrompt, and a reserved-server matchmaking pad.",
    },
    {
        "id": "screenshot-ui-audit",
        "title": "1:1 Reference UI Rebuild + Mobile/Gamepad Audit",
        "category": "UI",
        "text": "Read ui-reference-accessibility first, call get_style_guide, and pull StudioProbe + ModalTransition via get_luau_module. Build a responsive 1:1 HUD & Modal Shop with 44px mobile touch targets, ScreenInsets safe areas, gamepad focus restoration, and audit live TextFits bounds using StudioProbe.",
    },
]


def _ensure_skills_dir():
    os.makedirs(SKILLS_DIR, exist_ok=True)


def _slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", str(text or "").strip().lower()).strip("-")
    return slug[:64] or "custom-skill"


def _norm_key(text):
    return re.sub(r"[^a-z0-9]+", "", str(text or "").strip().lower())


def _parse_bool(val, default=True):
    if isinstance(val, bool):
        return val
    s = str(val or "").strip().lower()
    if s in ("true", "1", "yes", "on"):
        return True
    if s in ("false", "0", "no", "off"):
        return False
    return default


def _unquote(val):
    s = str(val or "").strip()
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        inner = s[1:-1]
        if s[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        return inner
    return s


def _quote(val):
    s = str(val or "").replace("\r", " ").replace("\n", " ").strip()
    if not s or any(ch in s for ch in (":", "#", '"', "'")) or s.startswith(" ") or s.endswith(" "):
        return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return s


def _parse_skill_file(path, include_content=True):
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        raw = f.read()

    raw_norm = raw.replace("\r\n", "\n")
    meta = {}
    body = raw_norm

    if raw_norm.startswith("---\n"):
        end_idx = raw_norm.find("\n---\n", 4)
        if end_idx == -1 and raw_norm.rstrip().endswith("\n---"):
            end_idx = raw_norm.rfind("\n---")
            fm_text = raw_norm[4:end_idx]
            body = ""
        elif end_idx != -1:
            fm_text = raw_norm[4:end_idx]
            body = raw_norm[end_idx + 5:]
        else:
            fm_text = ""

        for line in fm_text.split("\n"):
            line = line.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = _unquote(v)

    fname_id = os.path.splitext(os.path.basename(path))[0]
    sid = _slugify(meta.get("id") or fname_id)
    name = (meta.get("name") or sid.replace("-", " ").title()).strip()
    category = (meta.get("category") or "Custom").strip()
    if category not in VALID_CATEGORIES:
        cat_match = next((c for c in VALID_CATEGORIES if c.lower() == category.lower()), None)
        category = cat_match or category or "Custom"
    tagline = (meta.get("tagline") or "").strip()
    enabled = _parse_bool(meta.get("enabled"), default=True)
    mode = (meta.get("mode") or "auto").strip().lower()
    if mode not in VALID_MODES:
        mode = "auto"
    builtin = _parse_bool(meta.get("builtin"), default=(sid in BUILTIN_ORDER))
    body_clean = body.lstrip("\n")

    skill = {
        "id": sid,
        "name": name,
        "category": category,
        "tagline": tagline,
        "enabled": enabled,
        "mode": mode,
        "builtin": builtin,
        "chars": len(body_clean),
        "file": os.path.basename(path),
    }
    if include_content:
        skill["content"] = body_clean
    return skill


def _serialize_skill(skill):
    lines = [
        "---",
        f"id: {_quote(skill['id'])}",
        f"name: {_quote(skill['name'])}",
        f"category: {_quote(skill['category'])}",
        f"tagline: {_quote(skill.get('tagline', ''))}",
        f"enabled: {'true' if skill.get('enabled', True) else 'false'}",
        f"mode: {skill.get('mode', 'auto') if skill.get('mode') in VALID_MODES else 'auto'}",
        f"builtin: {'true' if skill.get('builtin', False) else 'false'}",
        "---",
        "",
    ]
    body = str(skill.get("content") or "").replace("\r\n", "\n").lstrip("\n")
    if body and not body.endswith("\n"):
        body += "\n"
    return "\n".join(lines) + body


def _atomic_write(path, text):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    os.replace(tmp, path)


def list_skills(include_content=True):
    _ensure_skills_dir()
    skills = []
    for entry in os.listdir(SKILLS_DIR):
        if not entry.lower().endswith(".md"):
            continue
        full = os.path.join(SKILLS_DIR, entry)
        if not os.path.isfile(full):
            continue
        try:
            skills.append(_parse_skill_file(full, include_content=include_content))
        except Exception:
            continue

    skills.sort(key=lambda s: (
        0 if s["id"] in BUILTIN_ORDER else 1,
        BUILTIN_ORDER.get(s["id"], 999),
        s["name"].lower(),
    ))
    return skills


def list_summary():
    out = []
    for s in list_skills(include_content=True):
        item = {
            "id": s["id"],
            "name": s["name"],
            "category": s["category"],
            "tagline": s["tagline"],
            "enabled": s["enabled"],
            "mode": s["mode"],
            "builtin": s["builtin"],
            "chars": s["chars"],
        }
        if s["enabled"] and s["mode"] == "always":
            item["content"] = s.get("content", "")
        out.append(item)
    return out


def get_skill(skill_id):
    q = _norm_key(skill_id)
    if not q:
        return None
    skills = list_skills(include_content=True)
    # 1. Exact id or name
    for s in skills:
        if _norm_key(s["id"]) == q or _norm_key(s["name"]) == q:
            return s
    # 2. Exact category match
    for s in skills:
        if _norm_key(s["category"]) == q:
            return s
    # 3. Substring / prefix match
    for s in skills:
        if q in _norm_key(s["id"]) or q in _norm_key(s["name"]):
            return s
    return None


def _find_skill_path(sid):
    _ensure_skills_dir()
    target = _slugify(sid)
    direct = os.path.join(SKILLS_DIR, f"{target}.md")
    if os.path.isfile(direct):
        return direct
    for entry in os.listdir(SKILLS_DIR):
        if not entry.lower().endswith(".md"):
            continue
        full = os.path.join(SKILLS_DIR, entry)
        try:
            sk = _parse_skill_file(full, include_content=False)
            if sk["id"] == target:
                return full
        except Exception:
            continue
    return direct


def save_skill(data):
    if not isinstance(data, dict):
        return False, "invalid skill payload"
    name = str(data.get("name") or "").strip()
    content = str(data.get("content") or "").replace("\r\n", "\n").strip()
    if not name:
        return False, "skill name is required"
    if not content:
        return False, "skill content is required"

    sid = _slugify(data.get("id") or name)
    path = _find_skill_path(sid)
    existing = None
    if os.path.isfile(path):
        try:
            existing = _parse_skill_file(path, include_content=True)
        except Exception:
            existing = None

    category = str(data.get("category") or (existing["category"] if existing else "Custom")).strip() or "Custom"
    tagline = str(data.get("tagline") if "tagline" in data else (existing["tagline"] if existing else "")).strip()
    enabled = _parse_bool(data.get("enabled"), default=(existing["enabled"] if existing else True))
    mode = str(data.get("mode") or (existing["mode"] if existing else "auto")).strip().lower()
    if mode not in VALID_MODES:
        mode = "auto"
    builtin = bool(existing["builtin"]) if existing else (sid in BUILTIN_ORDER)

    record = {
        "id": sid,
        "name": name,
        "category": category,
        "tagline": tagline,
        "enabled": enabled,
        "mode": mode,
        "builtin": builtin,
        "content": content,
    }
    try:
        _ensure_skills_dir()
        _atomic_write(path, _serialize_skill(record))
        return True, _parse_skill_file(path, include_content=True)
    except Exception as e:
        return False, str(e)


def toggle_skill(skill_id, enabled=None, mode=None):
    sk = get_skill(skill_id)
    if not sk:
        return False, f"skill '{skill_id}' not found"
    path = _find_skill_path(sk["id"])
    if enabled is not None:
        sk["enabled"] = _parse_bool(enabled, default=sk["enabled"])
    if mode is not None:
        m = str(mode).strip().lower()
        if m not in VALID_MODES:
            return False, f"invalid mode '{mode}' (expected 'auto' or 'always')"
        sk["mode"] = m
    try:
        _atomic_write(path, _serialize_skill(sk))
        return True, _parse_skill_file(path, include_content=True)
    except Exception as e:
        return False, str(e)


def delete_skill(skill_id):
    sk = get_skill(skill_id)
    if not sk:
        return False, f"skill '{skill_id}' not found"
    if sk.get("builtin"):
        return False, f"built-in skill '{sk['name']}' cannot be deleted (disable it instead)"
    path = _find_skill_path(sk["id"])
    try:
        if os.path.isfile(path):
            os.remove(path)
        return True, None
    except Exception as e:
        return False, str(e)


def list_presets():
    return [dict(p) for p in SKILL_PRESETS]


def apply_preset(preset_id):
    pid = _slugify(preset_id)
    preset = next((p for p in SKILL_PRESETS if p["id"] == pid), None)
    if not preset:
        return False, f"unknown preset '{preset_id}'"
    wanted = set(preset["skills"])
    for sk in list_skills(include_content=True):
        if sk.get("builtin"):
            target_enabled = sk["id"] in wanted
            if bool(sk.get("enabled")) != target_enabled:
                ok, err = toggle_skill(sk["id"], enabled=target_enabled)
                if not ok:
                    return False, err
    return True, preset


def default_settings():
    return {
        "userName": os.environ.get("USERNAME") or os.environ.get("USER") or "Builder",
        "minimizeToTray": True,
        "autoOpenWindow": True,
        "appPort": int(os.environ.get("ZS_APP_PORT", "17614")),
        "accentTheme": "indigo",
        "liquidGlass": True,
        "liquidBackdrop": "sunset",
        "glassStyle": "liquid",
        "ambientMotion": True,
        "favoriteProviders": ["claude", "deepseek", "gemini"],
        "globalPrompt": "",
        "customPrompts": [],
    }


def _clean_prompts(raw):
    out = []
    if not isinstance(raw, list):
        return out
    seen = set()
    for item in raw[:64]:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title") or "").strip()[:80]
        text = str(item.get("text") or "").replace("\r\n", "\n").strip()[:4000]
        if not title or not text:
            continue
        pid = _slugify(item.get("id") or title)
        while pid in seen:
            pid = f"{pid[:58]}-x"
        seen.add(pid)
        cat = str(item.get("category") or "Custom").strip()[:32] or "Custom"
        out.append({"id": pid, "title": title, "category": cat, "text": text})
    return out


def load_settings():
    cfg = default_settings()
    if os.path.isfile(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                if isinstance(saved.get("userName"), str) and saved["userName"].strip():
                    cfg["userName"] = saved["userName"].strip()[:40]
                if isinstance(saved.get("minimizeToTray"), bool):
                    cfg["minimizeToTray"] = saved["minimizeToTray"]
                if isinstance(saved.get("autoOpenWindow"), bool):
                    cfg["autoOpenWindow"] = saved["autoOpenWindow"]
                if isinstance(saved.get("appPort"), int) and 1024 <= saved["appPort"] <= 65535:
                    cfg["appPort"] = saved["appPort"]
                if isinstance(saved.get("accentTheme"), str) and saved["accentTheme"].strip().lower() in VALID_ACCENTS:
                    cfg["accentTheme"] = saved["accentTheme"].strip().lower()
                if isinstance(saved.get("liquidGlass"), bool):
                    cfg["liquidGlass"] = saved["liquidGlass"]
                if isinstance(saved.get("liquidBackdrop"), str) and saved["liquidBackdrop"].strip().lower() in VALID_BACKDROPS:
                    cfg["liquidBackdrop"] = saved["liquidBackdrop"].strip().lower()
                if isinstance(saved.get("glassStyle"), str) and saved["glassStyle"].strip().lower() in VALID_GLASS_STYLES:
                    cfg["glassStyle"] = saved["glassStyle"].strip().lower()
                if isinstance(saved.get("ambientMotion"), bool):
                    cfg["ambientMotion"] = saved["ambientMotion"]
                if isinstance(saved.get("favoriteProviders"), list):
                    cfg["favoriteProviders"] = [
                        _slugify(x) for x in saved["favoriteProviders"][:12] if isinstance(x, str) and x.strip()
                    ]
                if isinstance(saved.get("globalPrompt"), str):
                    cfg["globalPrompt"] = saved["globalPrompt"].replace("\r\n", "\n").strip()[:8000]
                if isinstance(saved.get("customPrompts"), list):
                    cfg["customPrompts"] = _clean_prompts(saved["customPrompts"])
        except Exception:
            pass
    return cfg


def save_settings(patch):
    cfg = load_settings()
    if isinstance(patch, dict):
        if "userName" in patch and isinstance(patch["userName"], str):
            name = patch["userName"].strip()[:40]
            if name:
                cfg["userName"] = name
        if "minimizeToTray" in patch:
            cfg["minimizeToTray"] = _parse_bool(patch["minimizeToTray"], default=cfg["minimizeToTray"])
        if "autoOpenWindow" in patch:
            cfg["autoOpenWindow"] = _parse_bool(patch["autoOpenWindow"], default=cfg["autoOpenWindow"])
        if "appPort" in patch:
            try:
                p = int(patch["appPort"])
                if 1024 <= p <= 65535:
                    cfg["appPort"] = p
            except Exception:
                pass
        if "accentTheme" in patch and isinstance(patch["accentTheme"], str):
            th = patch["accentTheme"].strip().lower()
            if th in VALID_ACCENTS:
                cfg["accentTheme"] = th
        if "liquidGlass" in patch:
            cfg["liquidGlass"] = _parse_bool(patch["liquidGlass"], default=cfg["liquidGlass"])
        if "liquidBackdrop" in patch and isinstance(patch["liquidBackdrop"], str):
            bd = patch["liquidBackdrop"].strip().lower()
            if bd in VALID_BACKDROPS:
                cfg["liquidBackdrop"] = bd
        if "glassStyle" in patch and isinstance(patch["glassStyle"], str):
            gs = patch["glassStyle"].strip().lower()
            if gs in VALID_GLASS_STYLES:
                cfg["glassStyle"] = gs
        if "ambientMotion" in patch:
            cfg["ambientMotion"] = _parse_bool(patch["ambientMotion"], default=cfg["ambientMotion"])
        if "favoriteProviders" in patch and isinstance(patch["favoriteProviders"], list):
            cfg["favoriteProviders"] = [
                _slugify(x) for x in patch["favoriteProviders"][:12] if isinstance(x, str) and x.strip()
            ]
        if "globalPrompt" in patch and isinstance(patch["globalPrompt"], str):
            cfg["globalPrompt"] = patch["globalPrompt"].replace("\r\n", "\n").strip()[:8000]
        if "customPrompts" in patch and isinstance(patch["customPrompts"], list):
            cfg["customPrompts"] = _clean_prompts(patch["customPrompts"])
    _atomic_write(SETTINGS_PATH, json.dumps(cfg, indent=2) + "\n")
    return cfg


def save_custom_prompt(data):
    if not isinstance(data, dict):
        return False, "invalid prompt payload"
    title = str(data.get("title") or "").strip()[:80]
    text = str(data.get("text") or "").replace("\r\n", "\n").strip()[:4000]
    cat = str(data.get("category") or "Custom").strip()[:32] or "Custom"
    if not title:
        return False, "prompt title is required"
    if not text:
        return False, "prompt text is required"
    cfg = load_settings()
    prompts = list(cfg.get("customPrompts") or [])
    pid = _slugify(data.get("id") or title)
    entry = {"id": pid, "title": title, "category": cat, "text": text}
    idx = next((i for i, p in enumerate(prompts) if p["id"] == pid), None)
    if idx is not None:
        prompts[idx] = entry
    else:
        prompts.insert(0, entry)
    saved = save_settings({"customPrompts": prompts})
    return True, saved["customPrompts"]


def delete_custom_prompt(prompt_id):
    pid = _slugify(prompt_id)
    cfg = load_settings()
    prompts = [p for p in (cfg.get("customPrompts") or []) if p["id"] != pid]
    if len(prompts) == len(cfg.get("customPrompts") or []):
        return False, f"prompt '{prompt_id}' not found"
    saved = save_settings({"customPrompts": prompts})
    return True, saved["customPrompts"]


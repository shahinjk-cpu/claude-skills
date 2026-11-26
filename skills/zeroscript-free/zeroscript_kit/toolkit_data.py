# SPDX-License-Identifier: GPL-3.0-or-later
"""ZeroScript Toolkit Data: 19 Luau Modules, 12-Genre Style Vocab, Bug Recovery, Skill Router & Project Memory."""
from datetime import datetime, timezone
import json
import os
import re
import threading

import skills_manager

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODULES_DIR = os.path.join(HERE, "luau_modules")
INTEL_DIR = os.path.join(HERE, "intelligence_data")
MEMORY_PATH = os.path.join(HERE, "project_memory.json")
_MEMORY_LOCK = threading.Lock()

VALID_MEMORY_KINDS = ("project", "style", "asset", "decision", "failure", "progress")
VALID_MEMORY_STATES = ("observed", "proposed", "superseded")
SECRET_PATTERN = re.compile(
    r"(?i)(api[_ -]?key|password|authorization:\s*bearer|\.ROBLOSECURITY|private[_ -]?key)"
)

MODULE_META = {
    "TokenBucket": {
        "category": "Server Security",
        "context": "Server",
        "summary": "Per-player rate limiter preventing RemoteEvent spam and burst exploits.",
        "example": "local bucket = TokenBucket.new(5, 2)\nif not bucket.allow(player.UserId) then return end\n-- Clean up in Players.PlayerRemoving: bucket.remove(player.UserId)",
    },
    "AttackWindow": {
        "category": "Server Security",
        "context": "Server",
        "summary": "Authoritative server windup/active/recover melee timing validator independent of client markers.",
        "example": "local win = AttackWindow.new(os.clock(), 0.18, 0.32, 0.68)\nif win.tryHit(targetUserId, os.clock()) then applyDamage() end",
    },
    "RevisionGate": {
        "category": "Server Security",
        "context": "Server",
        "summary": "Monotonic revision & confirmation token gate preventing stale or replayed state mutations.",
        "example": "if not gate.commit(expectedRev) then return false, 'stale_revision' end",
    },
    "RevisionTrade": {
        "category": "Server Security",
        "context": "Server",
        "summary": "Lock-step 2-player trading state machine that resets confirmations on every offer edit.",
        "example": "trade.setOffer(player.UserId, items) -- bumps revision & clears confirmations",
    },
    "RequestEpoch": {
        "category": "Server Security",
        "context": "Server / Shared",
        "summary": "Monotonic epoch guard that discards out-of-order async UI/network responses.",
        "example": "local token = epoch.next()\n-- after yield: if not epoch.current(token) then return end",
    },
    "ScopedRay": {
        "category": "Server Security",
        "context": "Server / Shared",
        "summary": "Zero-leak RaycastParams helper enforcing filter lists and safe bounded distances.",
        "example": "local result = ScopedRay.cast(origin, dir, ignoreList, 250)",
    },
    "Finite": {
        "category": "Server Security",
        "context": "Server / Shared",
        "summary": "NaN, Inf, and finite-bounds validator for untrusted numbers and Vector3 coordinates.",
        "example": "if not Finite.number(amount, 0, 10000) then return end",
    },
    "CriticalSpring": {
        "category": "Client UI & Feel",
        "context": "Client / Shared",
        "summary": "Unconditionally stable critically damped spring solver for camera recoil, viewmodels & UI.",
        "example": "x, v = CriticalSpring.step(x, v, target, omega, dt)",
    },
    "ModalTransition": {
        "category": "Client UI & Feel",
        "context": "Client",
        "summary": "Clean CanvasGroup fade/slide/pop modal controller with reduced-motion fallback & cancel cleanup.",
        "example": "local modal = ModalTransition.new(canvasGroup)\nmodal:set(true, 0.18, reducedMotion)",
    },
    "HealthBinding": {
        "category": "Client UI & Feel",
        "context": "Client",
        "summary": "Safe LocalPlayer Humanoid health observer that handles respawns and returns a teardown cleanup.",
        "example": "local unbind = HealthBinding.attach(Players.LocalPlayer, function(ratio, hp, maxHp) ... end)",
    },
    "ViewportFit": {
        "category": "Client UI & Feel",
        "context": "Client",
        "summary": "Automatically frames any Model cleanly inside a ViewportFrame camera with orbit bounds.",
        "example": "local cleanup = ViewportFit.mount(viewportFrame, itemModel)",
    },
    "BoundedPool": {
        "category": "Client UI & Feel",
        "context": "Client / Shared",
        "summary": "Fixed-capacity VFX/part object pool that recycles active instances without GC spikes.",
        "example": "local pool = BoundedPool.new(32, createImpactPart, resetPart)",
    },
    "Formation": {
        "category": "Client UI & Feel",
        "context": "Client / Shared",
        "summary": "Grid/arc follower slot offsets relative to character root for pets, minions & squads.",
        "example": "local offset = Formation.slotOffset(index, totalPets, 4.5)",
    },
    "StableSelection": {
        "category": "Client UI & Feel",
        "context": "Client",
        "summary": "Preserves selected item ID and gamepad/list focus across inventory sorting & updates.",
        "example": "local nextId = StableSelection.resolve(visibleIds, prevSelectedId)",
    },
    "CleanupScope": {
        "category": "General Utility",
        "context": "Shared",
        "summary": "Lightweight Janitor/Maid scope for tracks, RBXScriptConnections, instances, and callbacks.",
        "example": "local scope = CleanupScope.new()\nscope:add(part.Touched:Connect(...))\nscope:destroy()",
    },
    "WeightedChoice": {
        "category": "General Utility",
        "context": "Server / Shared",
        "summary": "Deterministic or RNG weighted table roller with clean cumulative distribution validation.",
        "example": "local drop = WeightedChoice.pick(lootTable, math.random)",
    },
    "RigMap": {
        "category": "General Utility",
        "context": "Shared",
        "summary": "R6/R15/custom creature bone & Motor6D resolver so animation code never hardcodes fragile paths.",
        "example": "local joints = RigMap.collect(character)",
    },
    "MaterialBinding": {
        "category": "General Utility",
        "context": "Client / Shared",
        "summary": "Clean visual state / highlight / material swapper with deterministic restore on unequip.",
        "example": "local restore = MaterialBinding.apply(model, Enum.Material.ForceField, color)",
    },
    "StudioProbe": {
        "category": "Diagnostics",
        "context": "Studio Edit/Play",
        "summary": "Bounded read-only subtree inspector returning GuiObject AbsoluteSize, TextFits, RunContext & joints.",
        "example": "local snap = StudioProbe.capture(Players.LocalPlayer.PlayerGui.HUD, 500)\nreturn snap",
    },
}

MODULE_ORDER = [
    "TokenBucket",
    "AttackWindow",
    "RevisionGate",
    "RevisionTrade",
    "Finite",
    "RequestEpoch",
    "ScopedRay",
    "CriticalSpring",
    "ModalTransition",
    "HealthBinding",
    "ViewportFit",
    "BoundedPool",
    "Formation",
    "StableSelection",
    "CleanupScope",
    "WeightedChoice",
    "RigMap",
    "MaterialBinding",
    "StudioProbe",
]

SKILL_KEYWORD_BOOSTS = {
    "game-recreation-1to1": {"clone", "1:1", "recreate", "battlegrounds", "doors", "brookhaven", "bedwars", "vertical", "slice", "copy"},
    "animations-rigging-procedural": {"animation", "animate", "motor6d", "keyframesequence", "pose", "viewmodel", "ik", "procedural", "spring", "swing", "dash", "reload"},
    "creatures-facial-state-machines": {"creature", "quadruped", "wing", "tail", "monster", "gait", "facial", "facecontrols", "expression", "blink", "state", "machine", "blend"},
    "camera-movement-physics": {"camera", "fov", "movement", "parkour", "dash", "slide", "vault", "wall", "coyote", "lock", "recoil", "shake", "momentum"},
    "combat-vfx-gamefeel": {"combat", "sword", "melee", "combo", "hitbox", "hitstop", "knockback", "parry", "block", "vfx", "particle", "slash", "projectile", "telegraph"},
    "security-datastore-trading": {"security", "exploit", "remote", "ratelimit", "rate", "datastore", "save", "profile", "session", "receipt", "processreceipt", "trade", "trading", "escrow", "dupe", "anti"},
    "pets-quests-lobbies": {"pet", "pets", "hatch", "egg", "follow", "quest", "dialogue", "npc", "lobby", "matchmaking", "party", "queue", "teleport", "reserved"},
    "ui-craftsmanship": {"ui", "gui", "hud", "inventory", "shop", "hotbar", "minimap", "canvasgroup", "uiscale", "tween"},
    "ui-reference-accessibility": {"figma", "reference", "screenshot", "mobile", "phone", "touch", "gamepad", "controller", "accessibility", "textfits", "clipping", "navigation", "focus", "safe", "area"},
    "building-architecture": {"building", "architecture", "house", "plaza", "castle", "tower", "interior", "prop", "pillar", "arch", "door", "roof", "cframe"},
    "maps-biomes-atmosphere": {"map", "biome", "terrain", "forest", "desert", "cyberpunk", "horror", "landmark", "route", "lobby", "arena", "world"},
    "lighting-atmosphere-audio": {"lighting", "future", "atmosphere", "bloom", "fog", "sunrays", "sky", "audio", "sound", "sfx", "ambient", "horror"},
    "cutscenes-cinematics": {"cutscene", "cinematic", "spline", "boss", "intro", "letterbox", "subtitle", "skip", "depthoffield"},
    "luau-architecture-networking": {"architecture", "module", "modulescript", "knit", "service", "controller", "strict", "network", "remoteevent"},
    "npc-ai-pathfinding": {"npc", "enemy", "boss", "ai", "pathfinding", "path", "aggro", "patrol", "leash", "fsm"},
    "economy-progression-loops": {"economy", "shop", "xp", "level", "rebirth", "currency", "upgrade", "tycoon", "simulator", "daily", "reward"},
    "performance-optimization": {"performance", "lag", "fps", "memory", "leak", "streaming", "pool", "microprofiler", "optimize", "network"},
}

BUG_SIGNAL_WORDS = {"bug", "fix", "broken", "error", "fail", "invisible", "clip", "clipped", "slide", "sliding", "lag", "jitter", "dupe", "duplicate", "lost", "stall", "offscreen", "noisy"}


def _tokens(text):
    return set(re.findall(r"[a-z0-9]+", str(text or "").lower()))


def _read_json_file(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _norm_key(s):
    return re.sub(r"[^a-z0-9]+", "", str(s or "").strip().lower())


def list_modules(category=None, include_code=False):
    """List the 19 extracted standalone Luau starter modules."""
    out = []
    cat_filter = (category or "").strip().lower()
    if cat_filter in ("all", ""):
        cat_filter = ""

    names = list(MODULE_ORDER)
    if os.path.isdir(MODULES_DIR):
        for fn in sorted(os.listdir(MODULES_DIR)):
            if fn.endswith(".luau"):
                mid = fn[:-5]
                if mid not in names:
                    names.append(mid)

    for mid in names:
        fp = os.path.join(MODULES_DIR, f"{mid}.luau")
        if not os.path.isfile(fp):
            continue
        meta = MODULE_META.get(mid, {})
        cat = meta.get("category", "General Utility")
        if cat_filter and cat.lower() != cat_filter:
            continue
        try:
            with open(fp, "r", encoding="utf-8", errors="replace") as f:
                code = f.read()
        except Exception:
            code = ""
        row = {
            "id": mid,
            "name": mid,
            "file": f"{mid}.luau",
            "category": cat,
            "context": meta.get("context", "Shared"),
            "summary": meta.get("summary", "Standalone Luau starter module."),
            "example": meta.get("example", ""),
            "lines": code.count("\n") + (1 if code else 0),
            "chars": len(code),
        }
        if include_code:
            row["code"] = code
        out.append(row)
    return out


def get_module(module_id):
    """Fetch a single Luau starter module with its full source code."""
    q = _norm_key(module_id)
    if not q:
        return None
    mods = list_modules(include_code=True)
    for m in mods:
        if _norm_key(m["id"]) == q:
            return m
    for m in mods:
        if q in _norm_key(m["id"]):
            return m
    return None


def get_style_guide(genre=None):
    """Return 12-genre Roblox style vocabulary and the anti-slop rubric."""
    vocab = _read_json_file(os.path.join(INTEL_DIR, "style_vocabulary.json"), {})
    antislop_path = os.path.join(INTEL_DIR, "anti_slop.md")
    antislop = ""
    if os.path.isfile(antislop_path):
        try:
            with open(antislop_path, "r", encoding="utf-8", errors="replace") as f:
                antislop = f.read().strip()
        except Exception:
            antislop = ""

    if genre:
        g = _norm_key(genre)
        matched = next((k for k in vocab if _norm_key(k) == g), None)
        if not matched:
            matched = next((k for k in vocab if g in _norm_key(k)), None)
        if not matched:
            return {"ok": False, "error": f"Unknown style genre '{genre}'. Available: {', '.join(sorted(vocab.keys()))}"}
        return {
            "ok": True,
            "genre": matched,
            "tokens": vocab[matched],
            "antiSlop": antislop,
        }

    return {
        "ok": True,
        "genres": list(vocab.keys()),
        "vocabulary": vocab,
        "antiSlop": antislop,
    }


def diagnose_bug(query=""):
    """Search the 12 bug-recovery recipes and 53 API gotchas."""
    recipes = _read_json_file(os.path.join(INTEL_DIR, "recovery.json"), [])
    api_seed = _read_json_file(os.path.join(INTEL_DIR, "api_seed.json"), [])
    qtoks = _tokens(query)

    if not qtoks:
        return {
            "ok": True,
            "query": "",
            "recovery": recipes,
            "apiNotes": api_seed[:15],
            "totalApiNotes": len(api_seed),
        }

    scored_rec = []
    for r in recipes:
        blob = f"{r.get('symptom','')} {r.get('probe','')} {r.get('repair','')} {r.get('retest','')}"
        score = len(qtoks & _tokens(blob))
        if score:
            scored_rec.append((score, r))
    scored_rec.sort(key=lambda x: -x[0])

    scored_api = []
    for row in api_seed:
        if isinstance(row, list) and len(row) >= 5:
            item = {
                "service": row[0],
                "member": row[1],
                "kind": row[2],
                "context": row[3],
                "note": row[4],
            }
            score = len(qtoks & _tokens(" ".join(str(x) for x in row)))
            if score:
                scored_api.append((score, item))
    scored_api.sort(key=lambda x: -x[0])

    return {
        "ok": True,
        "query": query,
        "recovery": [r for _, r in scored_rec[:5]] if scored_rec else recipes[:3],
        "apiNotes": [a for _, a in scored_api[:8]],
        "matchedRecovery": len(scored_rec),
        "totalApiNotes": len(api_seed),
    }


def route_skills(query, limit=4):
    """Recommend the top matching playbooks, style genres, Luau modules, and bug leads for a prompt."""
    q = str(query or "").strip()
    if not q:
        return {"ok": False, "error": "query is required"}
    lim = max(1, min(8, int(limit or 4)))
    qtoks = _tokens(q)

    enabled_skills = [s for s in skills_manager.list_summary() if s.get("enabled", True)]
    ranked_skills = []
    for sk in enabled_skills:
        sid = sk["id"]
        boost_words = SKILL_KEYWORD_BOOSTS.get(sid, set())
        meta_toks = _tokens(f"{sid} {sk.get('name','')} {sk.get('category','')} {sk.get('tagline','')}")
        boost_hits = sorted(qtoks & boost_words)
        meta_hits = sorted(qtoks & meta_toks)
        score = len(boost_hits) * 3 + len(meta_hits)
        if score > 0:
            ranked_skills.append({
                "id": sid,
                "name": sk["name"],
                "category": sk.get("category", "Skill"),
                "tagline": sk.get("tagline", ""),
                "score": score,
                "matched": sorted(set(boost_hits) | set(meta_hits))[:6],
            })
    ranked_skills.sort(key=lambda x: (-x["score"], x["name"]))
    top_skills = ranked_skills[:lim]
    if not top_skills and enabled_skills:
        top_skills = [
            {
                "id": sk["id"],
                "name": sk["name"],
                "category": sk.get("category", "Skill"),
                "tagline": sk.get("tagline", ""),
                "score": 1,
                "matched": ["default"],
            }
            for sk in enabled_skills[:min(2, lim)]
        ]

    # Style genres
    vocab = _read_json_file(os.path.join(INTEL_DIR, "style_vocabulary.json"), {})
    style_hits = []
    for gname, tokens in vocab.items():
        g_toks = _tokens(gname) | _tokens(json.dumps(tokens))
        overlap = len(qtoks & g_toks)
        if _norm_key(gname) in _norm_key(q):
            overlap += 5
        if overlap > 0:
            style_hits.append((overlap, gname))
    style_hits.sort(key=lambda x: -x[0])

    # Luau modules
    mod_hits = []
    for m in list_modules(include_code=False):
        mtoks = _tokens(f"{m['id']} {m['category']} {m['summary']}")
        overlap = len(qtoks & mtoks)
        if overlap > 0:
            mod_hits.append((overlap, m))
    mod_hits.sort(key=lambda x: (-x[0], x[1]["id"]))

    # Bug leads if query looks diagnostic
    recovery_hits = []
    if qtoks & BUG_SIGNAL_WORDS:
        recovery_hits = diagnose_bug(q).get("recovery", [])[:3]

    return {
        "ok": True,
        "query": q,
        "skills": top_skills,
        "styles": [g for _, g in style_hits[:3]],
        "modules": [
            {"id": m["id"], "category": m["category"], "context": m["context"], "summary": m["summary"]}
            for _, m in mod_hits[:4]
        ],
        "recovery": recovery_hits,
    }


def _load_memory_raw():
    if os.path.isfile(MEMORY_PATH):
        try:
            with open(MEMORY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and isinstance(data.get("records"), list):
                data.setdefault("schema", 1)
                data.setdefault("revision", 0)
                return data
        except Exception:
            pass
    return {"schema": 1, "revision": 0, "records": []}


def _save_memory_raw(data):
    tmp = MEMORY_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, MEMORY_PATH)


def memory_list(project=None, include_superseded=False):
    """List local project memory ledger entries."""
    with _MEMORY_LOCK:
        data = _load_memory_raw()
        proj_filter = (project or "").strip().lower()
        rows = []
        for r in data["records"]:
            if not include_superseded and r.get("state") == "superseded":
                continue
            if proj_filter and str(r.get("project") or "default").lower() != proj_filter:
                continue
            rows.append(r)
        rows.sort(key=lambda x: -int(x.get("revision", 0)))
        return rows


def memory_search(query="", project=None, limit=12):
    """Search local project memory entries by keyword."""
    rows = memory_list(project=project, include_superseded=False)
    qtoks = _tokens(query)
    if not qtoks:
        return rows[:max(1, min(50, int(limit or 12)))]
    scored = []
    for r in rows:
        blob = f"{r.get('project','')} {r.get('kind','')} {r.get('key','')} {r.get('value','')}"
        score = len(qtoks & _tokens(blob))
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: (-x[0], -int(x[1].get("revision", 0))))
    return [r for _, r in scored[:max(1, min(50, int(limit or 12)))]]


def memory_put(key, value, kind="decision", project="default", state="observed"):
    """Add or update a project memory entry with secret filtering and revision tracking."""
    k = re.sub(r"[^a-zA-Z0-9_.-]+", "-", str(key or "").strip()).strip("-")[:80]
    if not k:
        return False, "memory key is required (letters, numbers, '.', '_', '-')"
    val = str(value or "").strip()
    if not val or len(val) > 3000:
        return False, "memory value must be 1 to 3000 characters"
    if SECRET_PATTERN.search(val):
        return False, "refused potential secret/token in memory value; store only architecture/design facts"
    kd = str(kind or "decision").strip().lower()
    if kd not in VALID_MEMORY_KINDS:
        return False, f"invalid kind '{kd}'; expected one of {', '.join(VALID_MEMORY_KINDS)}"
    st = str(state or "observed").strip().lower()
    if st not in ("observed", "proposed"):
        st = "observed"
    proj = str(project or "default").strip()[:60] or "default"

    with _MEMORY_LOCK:
        data = _load_memory_raw()
        rev = int(data.get("revision", 0)) + 1
        data["revision"] = rev
        for r in data["records"]:
            if (
                str(r.get("project") or "default").lower() == proj.lower()
                and r.get("kind") == kd
                and r.get("key") == k
                and r.get("state") != "superseded"
            ):
                r["state"] = "superseded"
        entry = {
            "id": f"mem-{rev}",
            "project": proj,
            "kind": kd,
            "key": k,
            "value": val,
            "state": st,
            "revision": rev,
            "utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        }
        data["records"].append(entry)
        _save_memory_raw(data)
        return True, entry


def memory_delete(entry_id):
    """Delete a memory entry by id."""
    eid = str(entry_id or "").strip()
    if not eid:
        return False, "entry id is required"
    with _MEMORY_LOCK:
        data = _load_memory_raw()
        before = len(data["records"])
        data["records"] = [r for r in data["records"] if r.get("id") != eid]
        if len(data["records"]) == before:
            return False, f"memory entry '{eid}' not found"
        _save_memory_raw(data)
        return True, None


def memory_clear():
    """Clear all local project memory records."""
    with _MEMORY_LOCK:
        _save_memory_raw({"schema": 1, "revision": 0, "records": []})
    return True


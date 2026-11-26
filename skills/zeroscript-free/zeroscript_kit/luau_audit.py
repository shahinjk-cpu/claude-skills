# SPDX-License-Identifier: GPL-3.0-or-later
"""ZeroScript 60-Gate Pure-Python Luau Static Auditor."""
import os
from pathlib import Path

from . import luau_roblox, luau_rules, luau_semantic

GATES = {**luau_rules.GATES, **luau_semantic.GATES}

MAX_CODE_BYTES = 512 * 1024
SKIP_DIRS = {".git", "node_modules", "__pycache__", "venv", ".venv", ".mypy_cache", "dist", "build"}
PRIO_ORDER = {"high": 0, "medium": 1, "low": 2}
VALID_CONTEXTS = ("server", "client", "shared", "unknown")

DEMO_BUGGY_LUAU = """-- Example CombatHandler.server.luau with intentional bugs for 60-Gate Audit
local ReplicatedStorage = game:GetService("ReplicatedStorage")
local Players = game:GetService("Players")

local HitRemote = ReplicatedStorage:WaitForChild("HitRemote")
local DAMAGE = 25
local DAMAGE = 30

local function computeScale(divisor)
    local players = Players:GetPlayers()
    return DAMAGE / 0
end

HitRemote.OnServerEvent:Connect(function(player, targetChar, dmg)
    targetChar.Humanoid:TakeDamage(dmg)
    local hum = Players.LocalPlayer
    task.wait(0.2)
    workspace.Arena.Pad.Touched:Connect(function(hit)
        print(hit.Name)
    end)
end)
"""


def list_gates():
    """Return sorted list of all 60 Luau static audit gates."""
    return [
        {"id": gid, "name": GATES[gid][0], "description": GATES[gid][1]}
        for gid in sorted(GATES.keys())
    ]


def _infer_context(path_str):
    low = (path_str or "").replace("\\", "/").lower()
    if (
        low.endswith(".server.luau")
        or low.endswith(".server.lua")
        or "/serverscriptservice/" in low
        or "/serverstorage/" in low
        or "server" in os.path.basename(low)
    ):
        return "server"
    if (
        low.endswith(".client.luau")
        or low.endswith(".client.lua")
        or "/starterplayer/" in low
        or "/startergui/" in low
        or "/starterpack/" in low
        or "client" in os.path.basename(low)
    ):
        return "client"
    if "/replicatedstorage/" in low or "/replicatedfirst/" in low or "/shared/" in low:
        return "shared"
    return "unknown"


def _normalize_finding(raw, filename):
    gate = str(raw.get("gate") or "G06")
    g_info = GATES.get(gate, ("review", "Static review finding"))
    prio = str(raw.get("priority") or "medium").lower()
    if prio not in PRIO_ORDER:
        prio = "medium"
    return {
        "gate": gate,
        "gate_name": g_info[0],
        "path": str(raw.get("path") or filename),
        "line": int(raw.get("line") or 1),
        "code": str(raw.get("code") or raw.get("kind") or "review"),
        "message": str(raw.get("message") or raw.get("advice") or g_info[1]),
        "priority": prio,
    }


def _collect_findings(code, filename, context):
    findings = []
    seen = set()

    def push(item):
        norm = _normalize_finding(item, filename)
        key = (norm["gate"], norm["line"], norm["code"])
        if key not in seen:
            seen.add(key)
            findings.append(norm)

    rev = luau_roblox.review_text(code, context=context)
    for row in rev.get("findings", []):
        gid = luau_rules.legacy_gate(row.get("kind", ""))
        push({
            "gate": gid,
            "path": filename,
            "line": row.get("line", 1),
            "code": row.get("kind", "review"),
            "message": row.get("advice", ""),
            "priority": row.get("priority", "medium"),
        })

    ins_rows, _ins_stats, _receipts = luau_rules.inspect_source(filename, code, context=context)
    for row in ins_rows:
        push(row)

    sem_rows, sem_cov = luau_semantic.inspect(filename, code)
    for row in sem_rows:
        push(row)

    findings.sort(key=lambda f: (PRIO_ORDER.get(f["priority"], 9), f["line"], f["gate"]))
    return findings, rev, sem_cov


def audit_code(code, filename="Script.luau", context="unknown"):
    """Run all 60 static gates on a Luau script string."""
    if not isinstance(code, str):
        return {"ok": False, "error": "code must be a string"}
    if len(code.encode("utf-8", errors="replace")) > MAX_CODE_BYTES:
        return {"ok": False, "error": f"code exceeds {MAX_CODE_BYTES // 1024}KB audit limit"}
    ctx = str(context or "unknown").strip().lower()
    if ctx not in VALID_CONTEXTS:
        ctx = "unknown"
    fname = str(filename or "Script.luau").strip() or "Script.luau"

    try:
        findings, rev, sem_cov = _collect_findings(code, fname, ctx)
    except Exception as e:
        return {"ok": False, "error": f"audit failed: {e}"}

    high = sum(1 for f in findings if f["priority"] == "high")
    medium = sum(1 for f in findings if f["priority"] == "medium")
    low = sum(1 for f in findings if f["priority"] == "low")
    gates_triggered = sorted({f["gate"] for f in findings})
    status = "FAIL" if high > 0 else ("REVIEW" if findings else "PASS")

    return {
        "ok": True,
        "filename": fname,
        "context": ctx,
        "gateCount": len(GATES),
        "summary": {
            "status": status,
            "total": len(findings),
            "high": high,
            "medium": medium,
            "low": low,
            "lines": code.count("\n") + (1 if code else 0),
            "mode": rev.get("type_mode", "default"),
            "gates_triggered": gates_triggered,
            "coverage": sem_cov,
        },
        "findings": findings,
    }


def audit_directory(root_dir, max_files=120):
    """Audit all .lua/.luau files in a local folder + check require() cycles and context leaks."""
    if not isinstance(root_dir, str) or not root_dir.strip():
        return {"ok": False, "error": "directory path is required"}
    try:
        root = Path(root_dir.strip()).resolve(strict=True)
    except Exception as e:
        return {"ok": False, "error": f"invalid directory: {e}"}
    if not root.is_dir():
        return {"ok": False, "error": f"not a directory: {root}"}

    limit = max(1, min(500, int(max_files or 120)))
    files = []
    for base, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(names):
            if name.lower().endswith((".luau", ".lua")):
                files.append(Path(base) / name)
                if len(files) >= limit:
                    break
        if len(files) >= limit:
            break

    if not files:
        return {"ok": False, "error": f"no .luau/.lua files found under {root}"}

    all_findings = []
    graph_rows = []
    contexts = {}
    all_rel = set()
    total_lines = 0

    for fp in files:
        rel = fp.relative_to(root).as_posix()
        all_rel.add(rel)
        ctx = _infer_context(rel)
        contexts[rel] = ctx
        try:
            if fp.stat().st_size > MAX_CODE_BYTES:
                continue
            code = fp.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        total_lines += code.count("\n") + (1 if code else 0)
        try:
            findings, rev, _ = _collect_findings(code, rel, ctx)
            all_findings.extend(findings)
            graph_rows.append({
                "path": rel,
                "literal_requires": rev.get("literal_requires", []),
                "instance_requires": rev.get("instance_requires", []),
                "unknown_require_calls": rev.get("unknown_require_calls", 0),
            })
        except Exception:
            continue

    # Cross-file dependency cycles (G08) and client/shared -> server edges (G11)
    try:
        rg = luau_roblox.relative_graph(graph_rows, root, all_rel)
        scc = luau_rules.strongly_connected(rg.get("edges", {}))
        for cyc in scc.get("cycles", []):
            all_findings.append(_normalize_finding({
                "gate": "G08",
                "path": cyc[0],
                "line": 1,
                "code": "dependency_cycle",
                "message": f"Circular require cycle detected: {' -> '.join(cyc)}",
                "priority": "high",
            }, cyc[0]))
        for src, dsts in rg.get("edges", {}).items():
            sctx = contexts.get(src, "unknown")
            for dst in dsts:
                dctx = contexts.get(dst, "unknown")
                if sctx in ("client", "shared") and dctx == "server":
                    all_findings.append(_normalize_finding({
                        "gate": "G11",
                        "path": src,
                        "line": 1,
                        "code": "server_boundary_leak",
                        "message": f"{sctx} script requires server module '{dst}'.",
                        "priority": "high",
                    }, src))
    except Exception:
        pass

    all_findings.sort(key=lambda f: (PRIO_ORDER.get(f["priority"], 9), f["path"], f["line"], f["gate"]))
    truncated = len(all_findings) > 500
    capped = all_findings[:500]
    high = sum(1 for f in capped if f["priority"] == "high")
    medium = sum(1 for f in capped if f["priority"] == "medium")
    low = sum(1 for f in capped if f["priority"] == "low")
    status = "FAIL" if high > 0 else ("REVIEW" if capped else "PASS")

    return {
        "ok": True,
        "filename": str(root),
        "context": "project",
        "gateCount": len(GATES),
        "filesScanned": len(graph_rows),
        "truncated": truncated,
        "summary": {
            "status": status,
            "total": len(all_findings),
            "high": high,
            "medium": medium,
            "low": low,
            "lines": total_lines,
            "mode": "project",
            "gates_triggered": sorted({f["gate"] for f in capped}),
        },
        "findings": capped,
    }


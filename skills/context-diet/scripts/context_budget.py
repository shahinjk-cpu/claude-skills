#!/usr/bin/env python3
"""Audit the per-session / per-turn context budget of Claude Code config.

Read-only report. Enumerates and estimates the token cost of the artifacts
that ride the system prompt: global rules (full text), CLAUDE.md (full text),
the home-project MEMORY.md (full text), every skill's frontmatter name +
description (per-turn cost), agent definition files, and a count of commands.

Token estimate is a rough chars/4 heuristic (CJK chars counted as 1 char, so
CJK token cost is under-estimated vs a real tokenizer). Paths are resolved
from Path.home(), never Path.cwd() — the number must not drift with the
working directory (audit.py has that bug).
"""

import json
import sys
from pathlib import Path

HOME = Path.home()
CLAUDE_DIR = HOME / ".claude"
# ponytail: home-project MEMORY.md only; other projects' memory not audited,
#           add a --project flag if per-repo budgets ever matter.
MEMORY_MD = (
    CLAUDE_DIR / "projects" / str(HOME).replace("/", "-") / "memory" / "MEMORY.md"
)
HOT_SKILLS_JSON = CLAUDE_DIR / "data" / "skill-index" / "hot-skills.json"
AGENT_DOC = "AGENT-SKILL-MAP.md"  # documentation, not an agent definition


def estimate_tokens(text: str) -> int:
    """Rough token estimate: chars / 4 (CJK counted as 1 char — under-counts CJK)."""
    return round(len(text) / 4)


def read_text(path: Path) -> str:
    """Read a file as UTF-8, empty string on any error (read-only, never raises)."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _unquote(value: str) -> str:
    """Strip a single pair of surrounding matching quotes."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> dict:
    """Extract top-level scalar fields from YAML frontmatter without a YAML lib.

    Handles inline scalars (``key: value`` / quoted) and folded/literal block
    scalars (``key: >-`` followed by indented continuation lines).
    # ponytail: line-based parse, sufficient for name/description; swap in
    #           PyYAML if nested block fields ever need reading.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    body = []
    for ln in lines[1:]:
        if ln.strip() == "---":
            break
        body.append(ln)

    fields = {}
    i = 0
    while i < len(body):
        ln = body[i]
        if not ln or ln[0].isspace() or ":" not in ln:
            i += 1
            continue
        key, _, rest = ln.partition(":")
        key = key.strip()
        val = rest.strip()
        if val in ("", ">", ">-", ">+", "|", "|-", "|+"):
            collected = []
            j = i + 1
            while j < len(body):
                nxt = body[j]
                if nxt.strip() == "":
                    j += 1
                    continue
                if nxt[0].isspace():
                    collected.append(nxt.strip())
                    j += 1
                else:
                    break
            fields[key] = " ".join(collected)
            i = j
        else:
            fields[key] = _unquote(val)
            i += 1
    return fields


def load_hot_skills() -> set | None:
    """Return the hot-skill whitelist, or None if the index is unreadable."""
    try:
        return set(json.loads(HOT_SKILLS_JSON.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        return None


def collect_full_text(paths: list[Path], category: str) -> list[dict]:
    """Build items whose cost is their full text."""
    items = []
    for p in paths:
        text = read_text(p)
        items.append(
            {
                "category": category,
                "name": p.name,
                "path": str(p),
                "chars": len(text),
                "tokens": estimate_tokens(text),
            }
        )
    return items


def collect_skills(hot: set | None) -> list[dict]:
    """One item per skill = frontmatter name + description (the per-turn cost)."""
    skills_dir = CLAUDE_DIR / "skills"
    items = []
    for d in sorted(skills_dir.iterdir()):
        if not d.is_dir() or d.name == ".backups":
            continue
        skill_md = d / "SKILL.md"
        if not skill_md.exists():
            continue
        fm = parse_frontmatter(read_text(skill_md))
        name = fm.get("name") or d.name
        desc = fm.get("description", "")
        billed = f"{name} {desc}".strip()
        if d.name.startswith("_"):
            state = "ref"  # _ref-* skills skipped by apply_cold — never managed
        elif hot is None:
            state = "unknown"
        elif d.name in hot:
            state = "hot"
        else:
            state = "cold"
        items.append(
            {
                "category": "skills_frontmatter",
                "name": d.name,
                "path": str(skill_md),
                "chars": len(billed),
                "tokens": estimate_tokens(billed),
                "state": state,
            }
        )
    return items


def count_commands() -> dict:
    """Commands are assumed zero-cost until invoked — count only."""
    cmd_dir = CLAUDE_DIR / "commands"
    active = sorted(cmd_dir.glob("*.md"))
    archived = sorted((cmd_dir / ".archived").rglob("*.md"))
    return {
        "count": len(active) + len(archived),
        "active": len(active),
        "archived": len(archived),
        "tokens": 0,
    }


def build_report() -> dict:
    hot = load_hot_skills()

    rules = collect_full_text(sorted((CLAUDE_DIR / "rules").glob("*.md")), "rules")
    claude_md = collect_full_text([CLAUDE_DIR / "CLAUDE.md"], "claude_md")
    memory_md = collect_full_text([MEMORY_MD], "memory_md")
    agents = collect_full_text(
        [
            p
            for p in sorted((CLAUDE_DIR / "agents").glob("*.md"))
            if p.name != AGENT_DOC
        ],
        "agents",
    )
    skills = collect_skills(hot)
    commands = count_commands()

    estimated = rules + claude_md + memory_md + skills  # agents verified cold 2026-07-19, excluded

    skill_states = {"hot": 0, "cold": 0, "ref": 0, "unknown": 0}
    skill_state_tokens = {"hot": 0, "cold": 0, "ref": 0, "unknown": 0}
    for s in skills:
        skill_states[s["state"]] += 1
        skill_state_tokens[s["state"]] += s["tokens"]

    def cat(items: list[dict]) -> dict:
        return {"items": len(items), "tokens": sum(i["tokens"] for i in items)}

    categories = {
        "rules": cat(rules),
        "claude_md": cat(claude_md),
        "memory_md": cat(memory_md),
        "skills_frontmatter": {
            **cat(skills),
            "by_state": {k: skill_states[k] for k in skill_states if skill_states[k]},
            "tokens_by_state": {
                k: skill_state_tokens[k] for k in skill_states if skill_states[k]
            },
        },
        "agents": cat(agents),
        "commands": {"items": commands["count"], "tokens": 0, "detail": commands},
    }

    notes = [
        "Token estimate is chars/4 (rough). CJK counted as 1 char, so CJK token "
        "cost is UNDER-estimated vs a real tokenizer.",
        "agents: VERIFIED COLD 2026-07-19 — only frontmatter description enters main loop (one line per agent); bodies load on spawn (like "
        "skills). Counted here so the block is visible; may over-state real cost.",
        "commands: assumed zero-cost until invoked (count only). Note %d command "
        "entries currently surface in the Skill-tool list this session — whether "
        "that costs main-prompt tokens is UNVERIFIED." % commands["count"],
        "skills_frontmatter: cold skills carry Method-C compressed keyword lists "
        "(cheap); hot skills carry full-sentence descriptions (expensive).",
    ]
    if hot is None:
        notes.append(
            "hot-skills.json unreadable — every skill marked 'unknown'; skill "
            "frontmatter tokens reflect current SKILL.md as-is (upper bound if "
            "compression state cannot be confirmed)."
        )

    total_tokens = sum(i["tokens"] for i in estimated)
    all_items = sorted(estimated, key=lambda x: -x["tokens"])

    return {
        "summary": {
            "heuristic": "chars/4 (rough; CJK counted as 1 char)",
            "total_tokens_estimated": total_tokens,
            "categories": categories,
        },
        "top_offenders": all_items[:15],
        "items": all_items,
        "notes": notes,
    }


def print_human(report: dict) -> None:
    s = report["summary"]
    cats = s["categories"]
    print("=== Context Budget Audit (read-only) ===")
    print(f"Heuristic: {s['heuristic']} — CJK token cost under-estimated")
    print()

    rows = [
        ("rules (full text)", cats["rules"]),
        ("CLAUDE.md (full text)", cats["claude_md"]),
        ("MEMORY.md (full text)", cats["memory_md"]),
        ("skills frontmatter (per turn)", cats["skills_frontmatter"]),
        ("agents (COLD, excluded)*", cats["agents"]),
    ]
    print(f"{'Category':<32}{'Items':>7}{'Tokens':>11}")
    print("-" * 50)
    for label, c in rows:
        print(f"{label:<32}{c['items']:>7}{c['tokens']:>11,}")
        if label.startswith("skills") and "by_state" in c:
            by = c["by_state"]
            tb = c["tokens_by_state"]
            detail = "  ".join(f"{k} {by[k]}/{tb[k]:,}t" for k in by)
            print(f"{'  └ ' + detail:<50}")
    print("-" * 50)
    print(f"{'TOTAL (estimated cost)':<32}{'':>7}{s['total_tokens_estimated']:>11,}")
    cm = cats["commands"]["detail"]
    print(
        f"{'commands (count only, ~0 cost)':<32}{cm['count']:>7}{0:>11}"
        f"   (active {cm['active']} / archived {cm['archived']})"
    )
    print("* agents verified COLD 2026-07-19: desc-only in main loop, bodies load on spawn — excluded from TOTAL.")

    print()
    print("=== Top 15 single-item offenders (tokens desc) ===")
    for i, it in enumerate(report["top_offenders"], 1):
        tag = it.get("state", "")
        tag = f" [{tag}]" if tag else ""
        print(f"{i:>2}. {it['name']:<40}{it['category']:<20}{it['tokens']:>7,}{tag}")

    print()
    print("=== Notes ===")
    for n in report["notes"]:
        print(f"- {n}")


def main() -> None:
    report = build_report()
    if "--json" in sys.argv:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print_human(report)


if __name__ == "__main__":
    main()

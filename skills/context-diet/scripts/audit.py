#!/usr/bin/env python3
"""Audit Claude Code memory files for token cost, CJK%, and overlap."""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
# Common domain keywords for overlap detection
DOMAIN_KEYWORDS = {
    "security": [
        "auth",
        "permission",
        "rbac",
        "csrf",
        "ssrf",
        "session",
        "cookie",
        "password",
        "encrypt",
    ],
    "agent": [
        "sub-agent",
        "subagent",
        "agent",
        "delegate",
        "boundary",
        "capability",
        "evaluator",
        "isolation",
    ],
    "context": ["context", "token", "compact", "compress", "cache", "memory", "handoff"],
    "config": ["config", "claude.md", "rules", "memory.md", "layering", "version control"],
    "mcp": ["mcp", "playwright", "browser", "proxy", "mcpproxy"],
    "git": ["git", "worktree", "branch", "commit", "merge"],
    "llm": ["llm", "model", "ollama", "omlx", "embedding", "inference"],
    "skill": ["skill", "io:", "mime", "pipeline", "trigger", "invocation"],
    "sandbox": ["sandbox", "execute", "batch"],
}


def estimate_tokens(text: str) -> int:
    """Estimate token count: English ~4 chars/token, CJK ~1.5 chars/token."""
    cjk_chars = len(CJK_RE.findall(text))
    ascii_chars = len(text) - cjk_chars
    return int(ascii_chars / 4 + cjk_chars / 1.5)


def analyze_file(path: Path) -> dict:
    """Analyze a single file for metrics."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    lines = content.count("\n") + 1
    chars = len(content)
    cjk_count = len(CJK_RE.findall(content))
    cjk_pct = round(cjk_count * 100 / max(chars, 1), 1)
    tokens = estimate_tokens(content)

    # Extract headings for structure analysis
    headings = re.findall(r"^#{1,3}\s+(.+)$", content, re.MULTILINE)

    # Domain keyword matching
    content_lower = content.lower()
    domains = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        hits = sum(1 for k in keywords if k in content_lower)
        if hits >= 2:
            domains.append((domain, hits))
    domains.sort(key=lambda x: -x[1])

    return {
        "path": str(path),
        "name": path.name,
        "lines": lines,
        "chars": chars,
        "tokens": tokens,
        "cjk_count": cjk_count,
        "cjk_pct": cjk_pct,
        "headings": headings[:10],
        "domains": [d[0] for d in domains[:3]],
    }


def find_memory_files() -> list[Path]:
    """Find all files that Claude Code loads at startup."""
    home = Path.home()
    files = []

    # Global CLAUDE.md
    g = home / ".claude" / "CLAUDE.md"
    if g.exists():
        files.append(g)

    # Global rules
    rules_dir = home / ".claude" / "rules"
    if rules_dir.exists():
        files.extend(sorted(rules_dir.glob("*.md")))

    # Find project CLAUDE.md and rules by walking up from cwd
    cwd = Path.cwd()
    for p in [cwd, *cwd.parents]:
        proj_claude = p / "CLAUDE.md"
        if proj_claude.exists() and proj_claude != g:
            files.append(proj_claude)
        proj_rules = p / ".claude" / "rules"
        if proj_rules.exists():
            files.extend(sorted(proj_rules.glob("*.md")))
        if (p / ".git").exists():
            break

    # Project memory (MEMORY.md only, not topic files)
    cwd_key = str(cwd).replace("/", "-")
    mem_dir = home / ".claude" / "projects" / cwd_key / "memory"
    if mem_dir.exists():
        mem_file = mem_dir / "MEMORY.md"
        if mem_file.exists():
            files.append(mem_file)

    return files


def detect_overlaps(analyses: list[dict]) -> list[dict]:
    """Detect domain overlaps between files."""
    domain_files = defaultdict(list)
    for a in analyses:
        for d in a["domains"]:
            domain_files[d].append(a["name"])

    overlaps = []
    for domain, fnames in domain_files.items():
        if len(fnames) >= 2:
            overlaps.append({"domain": domain, "files": fnames})
    return overlaps


def main():
    files = find_memory_files()
    if not files:
        print(json.dumps({"error": "No memory files found"}))
        return

    analyses = []
    for f in files:
        result = analyze_file(f)
        if result:
            analyses.append(result)

    overlaps = detect_overlaps(analyses)
    total_tokens = sum(a["tokens"] for a in analyses)
    total_cjk = sum(a["cjk_count"] for a in analyses)
    total_chars = sum(a["chars"] for a in analyses)
    files_with_cjk = [a["name"] for a in analyses if a["cjk_pct"] > 2]

    report = {
        "summary": {
            "file_count": len(analyses),
            "total_tokens": total_tokens,
            "total_chars": total_chars,
            "total_cjk_chars": total_cjk,
            "cjk_pct": round(total_cjk * 100 / max(total_chars, 1), 1),
            "files_with_cjk": files_with_cjk,
        },
        "files": sorted(analyses, key=lambda x: -x["tokens"]),
        "overlaps": overlaps,
    }

    if "--json" in sys.argv:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        # Human-readable output
        s = report["summary"]
        print("=== Context Diet Audit ===")
        print(
            f"Files: {s['file_count']}  |  Tokens: ~{s['total_tokens']:,}  |  CJK: {s['cjk_pct']}%"
        )
        if s["files_with_cjk"]:
            print(f"⚠️  CJK >2%: {', '.join(s['files_with_cjk'])}")
        print()
        print(f"{'File':<40} {'Tokens':>7} {'Lines':>6} {'CJK%':>5}  Domains")
        print("-" * 85)
        for a in report["files"]:
            cjk_flag = "⚠️" if a["cjk_pct"] > 2 else "  "
            domains = ", ".join(a["domains"][:2]) if a["domains"] else "-"
            print(
                f"{a['name']:<40} {a['tokens']:>7} {a['lines']:>6} {a['cjk_pct']:>4}% {cjk_flag} {domains}"
            )
        if overlaps:
            print()
            print("=== Domain Overlaps (merge candidates) ===")
            for o in overlaps:
                print(f"  {o['domain']}: {' + '.join(o['files'])}")


if __name__ == "__main__":
    main()

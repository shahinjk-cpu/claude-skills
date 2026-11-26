#!/usr/bin/env python3
"""
anchor-check - verify that recorded decisions still match the code.

A decision record carries *anchors*: verifiable handles into the repo (a file, a
symbol, a migration, a config key) plus the date it was last verified. This tool
resolves every anchor and reports which decisions can no longer be trusted, so a
returning session re-derives only what actually drifted.

Works in any repository. No third-party dependencies - stdlib only, Python 3.8+.

    anchor-check                      # discover and check every DECISIONS.md
    anchor-check docs/DECISIONS.md    # one file
    anchor-check TICKET-42            # a directory (by name or path)
    anchor-check --init               # scaffold a DECISIONS.md here
    anchor-check --new "Use Postgres advisory locks"
    anchor-check --max-age 60 --quiet
    anchor-check --json
    anchor-check FEATURE_MAP.md       # check a feature map's paths and selectors
    anchor-check --decisions-only     # skip feature maps (alias: --no-feature-map)
    anchor-check --feature-map-only   # skip decisions

A FEATURE_MAP.md (the feature-map skill's format) is checked too: every entry's
code location must exist, and every `[attr="value"]` selector must still appear
as a string literal in the code.

Optional per-repo config, `.anchors.json` at the repo root:

    {
      "paths":        ["tickets/*/DECISIONS.md"],  // where records live
      "feature_maps": ["FEATURE_MAP.md"],          // where feature maps live
      "feature_map":  true,                        // false = skip feature maps
      "exclude":      ["archive/**"],              // globs to skip
      "anchor_base":  ".",                         // anchors resolve from here
      "max_age":      90                           // days before a check expires
    }

Exit codes:  0 = everything verifiable is current
             1 = at least one STALE / EXPIRED / BROKEN / MALFORMED finding
             2 = usage or parse error
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import date, datetime, timedelta
from pathlib import Path

__version__ = "1.2.0"

CONFIG_NAME = ".anchors.json"
RECORD_NAME = "DECISIONS.md"
MAP_NAME = "FEATURE_MAP.md"

# directories never worth walking into when discovering records
PRUNE = {".git", ".hg", ".svn", "node_modules", "target", "build", "dist", "out",
         "vendor", ".venv", "venv", "__pycache__", ".idea", ".vscode", ".gradle",
         ".mvn", ".tox", ".next", ".cache", "coverage",
         # agent tooling - a skill's own templates are not this repo's decisions
         ".claude", ".agents", ".cursor", ".aider"}


# --------------------------------------------------------------------------
# Repo layout - all of this is convention-free
# --------------------------------------------------------------------------

def find_root(start: Path, explicit: str | None) -> tuple[Path, dict]:
    """Root = --root, else nearest .anchors.json, else nearest .git, else cwd."""
    if explicit:
        root = Path(explicit).resolve()
        return root, load_config(root / CONFIG_NAME)

    # Nearest marker wins, whichever kind it is: an independent repo nested under a
    # configured workspace is its own root, not part of the parent's record set.
    cur = start.resolve()
    for cand in [cur, *cur.parents]:
        cfg_file = cand / CONFIG_NAME
        if cfg_file.is_file():
            return cand, load_config(cfg_file)
        if (cand / ".git").exists():
            return cand, {}
    return cur, {}


def load_config(path: Path) -> dict:
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}


def nearest_git_repo(path: Path) -> Path | None:
    """Monorepos and submodule trees hold many repos; find the owning one."""
    for cand in [path if path.is_dir() else path.parent, *path.parents]:
        if (cand / ".git").exists():
            return cand
    return None


def git_last_change(path: Path) -> date | None:
    repo = nearest_git_repo(path)
    if repo is None:
        return None
    try:
        rel = path.relative_to(repo)
        out = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%cI", "--", str(rel)],
                             capture_output=True, text=True, timeout=20)
    except (subprocess.SubprocessError, ValueError, OSError):
        return None
    stamp = out.stdout.strip()
    if not stamp:
        return None
    try:
        return datetime.fromisoformat(stamp).date()
    except ValueError:
        return None


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

STATUSES = {"ACTIVE", "PROPOSED", "SUPERSEDED", "REVERTED"}

HEAD_RE = re.compile(r"^##\s+(?P<id>[A-Z]{1,4}-\d+)\s*[-–—]\s*(?P<title>.+?)\s*$")
FIELD_RE = re.compile(r"^\s*[-*]\s*(?P<key>[A-Za-z][A-Za-z-]*)\s*:\s*(?P<val>.*?)\s*$")
ANCHOR_RE = re.compile(r"^\s{2,}[-*]\s*(?P<kind>[a-z]+)\s*:\s*(?P<val>.+?)\s*$")
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


@dataclass
class Finding:
    level: str            # OK | MANUAL | EXPIRED | STALE | BROKEN | MALFORMED
    anchor: str
    detail: str


@dataclass
class Decision:
    id: str
    title: str
    file: str
    line: int
    status: str = ""
    decided: str = ""
    verified: str = ""
    supersedes: str = ""
    superseded_by: str = ""
    anchors: list = field(default_factory=list)
    findings: list = field(default_factory=list)

    @property
    def verdict(self) -> str:
        levels = {f.level for f in self.findings}
        for lvl in ["BROKEN", "STALE", "EXPIRED", "MALFORMED", "MANUAL", "OK"]:
            if lvl in levels:
                return lvl
        return "OK"


def parse_decisions(path: Path) -> list:
    decisions, cur, in_anchors, in_comment = [], None, False, False
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.rstrip()

        # commented-out records are documentation, not live claims
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if "<!--" in line and "-->" not in line:
            in_comment = True
            continue

        head = HEAD_RE.match(line)
        if head:
            cur = Decision(id=head.group("id"), title=head.group("title"),
                           file=str(path), line=n)
            decisions.append(cur)
            in_anchors = False
            continue
        if cur is None:
            continue
        if line.startswith("## ") or line.startswith("# "):
            cur, in_anchors = None, False
            continue

        if in_anchors:
            anchor = ANCHOR_RE.match(line)
            if anchor:
                cur.anchors.append((anchor.group("kind"), anchor.group("val")))
                continue

        fld = FIELD_RE.match(line)
        if fld:
            key, val = fld.group("key").lower(), fld.group("val")
            in_anchors = key == "anchors"
            if key == "status":
                cur.status = val.split("#")[0].strip().upper()
            elif key == "decided":
                cur.decided = val
            elif key == "verified":
                cur.verified = val
            elif key == "supersedes":
                cur.supersedes = val
            elif key in ("superseded-by", "supersededby"):
                cur.superseded_by = val
        elif line and not line.startswith(" "):
            in_anchors = False
    return decisions


def parse_date(text: str):
    m = DATE_RE.search(text or "")
    return date.fromisoformat(m.group(1)) if m else None


# --------------------------------------------------------------------------
# Anchor verification
# --------------------------------------------------------------------------

DERIVABLE = {"code", "test", "sql", "config", "file", "doc"}      # resolved against the tree
MANUAL = {"pr", "issue", "jira", "ticket", "url", "env", "data", "ship", "release", "person"}


def split_target(value: str):
    if "#" in value:
        p, _, sym = value.partition("#")
        return p.strip(), sym.strip()
    return value.strip(), None


def resolve(rel: str, bases: list):
    """Anchors may be written relative to the repo root or to their own file."""
    for base in bases:
        cand = (base / rel)
        if cand.exists():
            return cand.resolve()
    return None


def check_anchor(kind: str, value: str, bases: list, verified, max_age: int) -> Finding:
    label = f"{kind}: {value}"

    if kind in DERIVABLE:
        rel, symbol = split_target(value)
        target = resolve(rel, bases)
        if target is None:
            return Finding("BROKEN", label, f"path does not exist: {rel}")
        if symbol:
            try:
                text = target.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                return Finding("BROKEN", label, f"unreadable: {exc}")
            if not re.search(r"\b" + re.escape(symbol) + r"\b", text):
                return Finding("BROKEN", label,
                               f"'{symbol}' not found in {rel} - renamed or removed")
        changed = git_last_change(target)
        if changed and verified and changed > verified:
            return Finding("STALE", label,
                           f"file changed {changed}, decision last verified {verified}")
        if changed:
            return Finding("OK", label, f"present, unchanged since {changed}")
        return Finding("OK", label, "present (not tracked by git)")

    if kind in MANUAL:
        when = parse_date(value) or verified
        if when and (date.today() - when) > timedelta(days=max_age):
            age = (date.today() - when).days
            return Finding("EXPIRED", label,
                           f"last confirmed {when} ({age}d ago) - re-confirm by hand")
        return Finding("MANUAL", label, "not machine-checkable - confirm by hand")

    return Finding("MALFORMED", label, f"unknown anchor kind '{kind}'")


def check_decision(d: Decision, bases: list, max_age: int) -> Decision:
    verified = parse_date(d.verified)

    if not d.status:
        d.findings.append(Finding("MALFORMED", "Status", "missing Status field"))
    elif d.status not in STATUSES:
        d.findings.append(Finding("MALFORMED", "Status", f"unknown status '{d.status}'"))
    if d.status == "ACTIVE" and d.superseded_by.strip(" -—–"):
        d.findings.append(Finding("MALFORMED", "Status",
                                  f"ACTIVE but Superseded-by: {d.superseded_by}"))
    if d.status in ("ACTIVE", "PROPOSED") and not verified:
        d.findings.append(Finding("MALFORMED", "Verified", "missing or unparsable Verified date"))
    elif verified and (date.today() - verified) > timedelta(days=max_age):
        age = (date.today() - verified).days
        d.findings.append(Finding("EXPIRED", "Verified",
                                  f"last verified {verified} ({age}d ago, limit {max_age}d)"))

    if d.status in ("SUPERSEDED", "REVERTED"):
        return d                      # history, not a live claim

    if not d.anchors:
        d.findings.append(Finding("MALFORMED", "Anchors", "no anchors - decision is unverifiable"))
    for kind, value in d.anchors:
        d.findings.append(check_anchor(kind, value, bases, verified, max_age))
    return d


# --------------------------------------------------------------------------
# Feature maps (FEATURE_MAP.md, as written by the feature-map skill)
# --------------------------------------------------------------------------

MAP_HEAD_RE = re.compile(r"^##\s+(?P<title>.+?)\s*$")
MAP_FIELD_RE = re.compile(r"^(?P<indent>\s*)[-*]\s*\*\*(?P<label>[^*]+?)\*\*\s*:?\s*(?P<val>.*)$")
MAP_SUB_RE = re.compile(r"^\s{2,}[-*]\s*(?P<val>.*)$")
TICK_RE = re.compile(r"`([^`]+)`")
ATTR_RE = re.compile(r"\[\s*[\w:-]+\s*[*^$|~]?=\s*[\"']([^\"']+)[\"']\s*\]")
PLACEHOLDERS = {"...", "…", ""}
MAX_SCAN_BYTES = 2_000_000


def is_placeholder(value: str) -> bool:
    v = value.strip()
    return v in PLACEHOLDERS or v.startswith("<") or "..." in v or "…" in v


def parse_feature_map(path: Path) -> list:
    """Entries are `## Name` sections; only the location and selector fields are read."""
    entries, cur, in_sel, in_fence, in_comment = [], None, False, False, False
    for n, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.rstrip()
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if in_comment:
            in_comment = "-->" not in line
            continue
        if "<!--" in line and "-->" not in line:
            in_comment = True
            continue

        head = MAP_HEAD_RE.match(line)
        if head:
            cur = {"title": head.group("title"), "line": n, "locations": [], "selectors": []}
            entries.append(cur)
            in_sel = False
            continue
        if cur is None:
            continue
        if line.startswith("# "):
            cur, in_sel = None, False
            continue

        fld = MAP_FIELD_RE.match(line)
        if fld and not (in_sel and len(fld.group("indent")) >= 2):
            label = fld.group("label").strip().rstrip(":").lower()
            ticks = TICK_RE.findall(fld.group("val"))
            in_sel = "selector" in label
            if "ubicaci" in label or "location" in label:
                cur["locations"].extend(ticks)
            elif in_sel:
                cur["selectors"].extend(ticks)
            continue
        sub = MAP_SUB_RE.match(line)
        if sub and in_sel:
            cur["selectors"].extend(TICK_RE.findall(sub.group("val")))
        elif line and not line.startswith(" "):
            in_sel = False
    return entries


_TEXT_CACHE: dict = {}


def code_files(base: Path):
    """Source files under a path, skipping docs, binaries and pruned directories."""
    if base.is_file():
        yield base
        return
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in PRUNE]
        for name in filenames:
            if not name.endswith(".md"):
                yield Path(dirpath) / name


def read_code(path: Path) -> str:
    if path not in _TEXT_CACHE:
        text = ""
        try:
            if path.stat().st_size <= MAX_SCAN_BYTES:
                data = path.read_bytes()
                if b"\0" not in data[:1024]:
                    text = data.decode("utf-8", errors="replace")
        except OSError:
            pass
        _TEXT_CACHE[path] = text
    return _TEXT_CACHE[path]


def shown(path: Path, root: Path):
    try:
        return path.relative_to(root)
    except ValueError:
        return path


def find_literal(value: str, scopes: list):
    """First file under the scopes containing value as a quoted string literal."""
    pattern = re.compile(r"[\"'`]" + re.escape(value) + r"[\"'`]")
    for scope in scopes:
        for f in code_files(scope):
            if pattern.search(read_code(f)):
                return f
    return None


def check_map_entry(e: dict, path: Path, bases: list, root: Path) -> Decision:
    d = Decision(id="MAP", title=e["title"], file=str(path), line=e["line"], status="MAP")
    located = []
    if not e["locations"]:
        d.findings.append(Finding("MALFORMED", "Location",
                                  "no code location in backticks - entry is unverifiable"))
    for rel in e["locations"]:
        label = f"location: {rel}"
        if is_placeholder(rel):
            d.findings.append(Finding("MALFORMED", label, "placeholder, not a real path"))
            continue
        target = resolve(rel, bases)
        if target is None:
            d.findings.append(Finding("BROKEN", label, f"path does not exist: {rel}"))
        else:
            located.append(target)
            d.findings.append(Finding("OK", label, "present"))

    for sel in e["selectors"]:
        label = f"selector: {sel}"
        values = ATTR_RE.findall(sel)
        if not values:
            d.findings.append(Finding("MANUAL", label,
                                      "no [attr=\"value\"] part - confirm in the running app"))
            continue
        for value in values:
            if is_placeholder(value):
                d.findings.append(Finding("MALFORMED", label, "placeholder, not a real selector"))
                continue
            hit = find_literal(value, located)
            if hit:
                d.findings.append(Finding("OK", label, f"'{value}' found in {shown(hit, root)}"))
                continue
            hit = find_literal(value, [root])
            if hit:
                d.findings.append(Finding("OK", label, f"'{value}' found outside the code "
                                                       f"location, in {shown(hit, root)}"))
            else:
                d.findings.append(Finding("BROKEN", label,
                                          f"'{value}' not found in the code - renamed or removed"))
    return d


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------

def discover(root: Path, cfg: dict, maps: bool = True, decisions: bool = True) -> list:
    """Configured globs where given, else a walk for the default file names."""
    excl = cfg.get("exclude", [])
    found, walk_for = [], set()
    for key, name, wanted in (("paths", RECORD_NAME, decisions),
                              ("feature_maps", MAP_NAME, maps)):
        if not wanted:
            continue
        if cfg.get(key):
            for pattern in cfg[key]:
                found.extend(root.glob(pattern))
        else:
            walk_for.add(name)
    if walk_for:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in PRUNE and not d.startswith("_")]
            found.extend(Path(dirpath) / n for n in walk_for if n in filenames)
    out = []
    for f in sorted(set(found)):
        try:
            rel = str(f.relative_to(root))        # 3.8-safe (no is_relative_to)
        except ValueError:
            rel = str(f)
        if any(f.match(p) or Path(rel).match(p) for p in excl):
            continue
        out.append(f)
    return out


def collect(target: str | None, root: Path, cfg: dict, maps: bool = True,
            decisions: bool = True) -> list:
    if not target:
        return discover(root, cfg, maps, decisions)
    names = ([RECORD_NAME] if decisions else []) + ([MAP_NAME] if maps else [])
    for cand in (Path(target), root / target):
        if cand.is_file():
            return [cand]
        if cand.is_dir():
            direct = sorted(p for n in names for p in cand.glob(n))
            return direct or sorted(p for n in names for p in cand.glob(f"**/{n}"))
    # a bare name like "TICKET-42" anywhere under the root
    hits = [p for p in discover(root, cfg, maps, decisions) if p.parent.name == target]
    if hits:
        return hits
    print(f"anchor-check: no {' or '.join(names)} found for '{target}'", file=sys.stderr)
    sys.exit(2)


# --------------------------------------------------------------------------
# Scaffolding
# --------------------------------------------------------------------------

TEMPLATE = """# DECISIONS

> One record per decision, added **when the choice is made**. Every record carries anchors
> (verifiable handles into this repo) and the date it was last checked, so `anchor-check` can
> report which decisions still hold without anyone re-reading the whole history.
>
> Decisions are append-only: when one stops being true, add a record that supersedes it and set
> the old one to SUPERSEDED. The rejected alternative is the part no commit records.

Anchor kinds - `code` `test` `sql` `config` `file` `doc` are checked against the tree (add
`#symbol` to pin a function, class or key); `pr` `issue` `jira` `url` `env` `data` `ship` need a
human and expire after 90 days, so give them their own date (`env: prod@2026-01-30 - ...`).

---

## D-01 - <the decision, stated as a rule>
- Status: PROPOSED
- Decided: {today}
- Verified: {today} (code-only)
- Supersedes: -
- Superseded-by: -
- Owner: <who made the call>
- Anchors:
  - code: <path/to/file.ext>#<symbol>

**Why:** <the reason that cannot be reconstructed from the diff>

**Why not:** <the alternative that was rejected, and what ruled it out>

**Still-true test:** <the cheapest command that proves this still holds>
"""

RECORD = """
---

## {id} - {title}
- Status: PROPOSED
- Decided: {today}
- Verified: {today} (code-only)
- Supersedes: -
- Superseded-by: -
- Owner: {owner}
- Anchors:

**Why:** 

**Why not:** 

**Still-true test:** 
"""


def do_init(target: Path) -> int:
    path = target / RECORD_NAME if target.is_dir() else target
    if path.exists():
        print(f"anchor-check: {path} already exists - not overwriting", file=sys.stderr)
        return 2
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(TEMPLATE.format(today=date.today().isoformat()), encoding="utf-8")
    print(f"created {path}\nFill in the D-01 record, then run: anchor-check {path}")
    return 0


def do_new(title: str, target: Path, owner: str) -> int:
    path = target / RECORD_NAME if target.is_dir() else target
    if not path.exists():
        print(f"anchor-check: {path} does not exist - run --init first", file=sys.stderr)
        return 2
    existing = parse_decisions(path)
    prefixes = [d.id.rsplit("-", 1)[0] for d in existing] or ["D"]
    prefix = prefixes[-1]
    nums = [int(d.id.rsplit("-", 1)[1]) for d in existing if d.id.startswith(prefix + "-")]
    new_id = f"{prefix}-{max(nums) + 1:02d}" if nums else f"{prefix}-01"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(RECORD.format(id=new_id, title=title, today=date.today().isoformat(), owner=owner))
    print(f"added {new_id} to {path} - add at least one anchor and the why-not")
    return 0


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------

ICON = {"OK": "ok  ", "MANUAL": "man ", "EXPIRED": "EXP ", "STALE": "STALE",
        "BROKEN": "BROK", "MALFORMED": "MALF"}
FAIL = {"STALE", "BROKEN", "EXPIRED", "MALFORMED"}


def report(decisions: list, root: Path, quiet: bool) -> int:
    by_file = {}
    for d in decisions:
        by_file.setdefault(d.file, []).append(d)

    for fname, group in by_file.items():
        problems = [d for d in group if d.verdict in FAIL]
        if quiet and not problems:
            continue
        try:
            shown = Path(fname).relative_to(root)
        except ValueError:
            shown = Path(fname)
        print(f"\n{shown}")
        for d in group:
            if quiet and d.verdict not in FAIL:
                continue
            print(f"  [{ICON.get(d.verdict, d.verdict)}] {d.id} - {d.title}   "
                  f"({d.status or 'NO STATUS'}{', verified ' + d.verified if d.verified else ''})")
            for f in d.findings:
                if quiet and f.level in ("OK", "MANUAL"):
                    continue
                print(f"          {ICON.get(f.level, f.level)}  {f.anchor}")
                print(f"                 -> {f.detail}")

    total = len(decisions)
    bad = [d for d in decisions if d.verdict in FAIL]
    manual = [d for d in decisions if d.verdict == "MANUAL"]
    n_map = sum(1 for d in decisions if d.status == "MAP")
    what = (f"{total} decision(s)" if not n_map else
            f"{total} record(s) ({total - n_map} decisions, {n_map} feature-map entries)")
    print(f"\n{what}: {total - len(bad)} current, {len(bad)} needing attention, "
          f"{len(manual)} manual-only")
    if bad:
        print(f"Re-verify the flagged {'records' if n_map else 'decisions'} "
              f"before building on them.")
    return 1 if bad else 0


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(
        prog="anchor-check", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version=f"anchor-check {__version__}")
    ap.add_argument("target", nargs="?", help=f"{RECORD_NAME} path, a directory, or a folder name")
    ap.add_argument("--init", action="store_true", help=f"scaffold a {RECORD_NAME}")
    ap.add_argument("--new", metavar="TITLE", help="append a new record skeleton")
    ap.add_argument("--owner", default=os.environ.get("USER", "unknown"),
                    help="owner recorded by --new")
    ap.add_argument("--max-age", type=int, help="days before a verification expires (default 90)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--quiet", action="store_true", help="print only decisions needing attention")
    ap.add_argument("--root", help="repo root (default: .anchors.json, else .git, else cwd)")
    only = ap.add_mutually_exclusive_group()
    only.add_argument("--decisions-only", "--no-feature-map", dest="decisions_only",
                      action="store_true", help=f"check only {RECORD_NAME} files")
    only.add_argument("--feature-map-only", action="store_true",
                      help=f"check only {MAP_NAME} files")
    args = ap.parse_args()

    root, cfg = find_root(Path.cwd(), args.root)
    max_age = args.max_age or cfg.get("max_age", 90)
    bases = [root / cfg.get("anchor_base", ".")]

    if args.init:
        return do_init(Path(args.target).resolve() if args.target else Path.cwd())
    if args.new:
        return do_new(args.new, Path(args.target).resolve() if args.target else Path.cwd(),
                      args.owner)

    # an explicit --feature-map-only wins over "feature_map": false in the config
    maps = args.feature_map_only or (not args.decisions_only
                                     and cfg.get("feature_map", True) is not False)
    decisions_wanted = not args.feature_map_only
    files = collect(args.target, root, cfg, maps, decisions_wanted)
    if not files:
        if decisions_wanted:
            print(f"anchor-check: no {RECORD_NAME} found under {root} - "
                  f"run 'anchor-check --init' to start one", file=sys.stderr)
        else:
            print(f"anchor-check: no {MAP_NAME} found under {root}", file=sys.stderr)
        return 0

    decisions = []
    for f in files:
        try:
            local_bases = bases + [f.parent]
            if f.name == MAP_NAME:
                decisions.extend(check_map_entry(e, f, local_bases, root)
                                 for e in parse_feature_map(f))
                continue
            decisions.extend(check_decision(d, local_bases, max_age) for d in parse_decisions(f))
        except OSError as exc:
            print(f"anchor-check: cannot read {f}: {exc}", file=sys.stderr)
            return 2

    if args.json:
        print(json.dumps({"root": str(root), "checked": [str(f) for f in files],
                          "decisions": [{**asdict(d), "verdict": d.verdict} for d in decisions]},
                         indent=2, default=str))
        return 1 if any(d.verdict in FAIL for d in decisions) else 0

    return report(decisions, root, args.quiet)


if __name__ == "__main__":
    sys.exit(main())

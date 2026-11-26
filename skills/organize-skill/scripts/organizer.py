#!/usr/bin/env python3
"""organize — safety script for the /organize Claude Code skill.

Does every filesystem operation for the skill, journals each one so it can be
undone, and never deletes anything except via `empty-trash --yes-really`.
Works on macOS, Linux (freedesktop Trash) and Windows (Recycle Bin).
Python 3.8+, standard library only.

Commands:
  info                      platform, user folders, trash backend
  scan [paths...]           JSON inventory of top-level items (default: Desktop, Downloads, Documents)
  check-project <path>      virtualenvs and scheduled jobs that depend on a folder's path
  apply <plan.json>         run a list of actions (mkdir / move / rename / trash)
  undo [run-id]             reverse a run (default: the last one)
  runs                      list past runs
  trash-list                JSON list of what's in the Trash
  empty-trash --yes-really  permanently empty the Trash
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import quote, unquote

HASH_LIMIT = 50 * 1024 * 1024
SIZE_WALK_LIMIT = 20000
CODE_MARKERS = {
    ".git", "pyproject.toml", "requirements.txt", "setup.py", "package.json",
    "venv", ".venv", "Cargo.toml", "go.mod", "pom.xml", "build.gradle",
    "Gemfile", "Makefile", "CMakeLists.txt", "Package.swift", "docker-compose.yml",
    "compose.yaml", "composer.json", "*.sln", "*.csproj",
}
INSTALLER_EXT = {".dmg", ".pkg", ".mpkg", ".exe", ".msi", ".deb", ".rpm", ".appimage", ".flatpakref"}
ARCHIVE_EXT = {".zip", ".tar", ".gz", ".tgz", ".rar", ".7z", ".xz", ".bz2"}
TEMP_EXT = {".crdownload", ".part", ".download", ".tmp", ".partial"}
SCREENSHOT_RE = re.compile(
    r"^(Screenshot|Screen Shot|Screen Recording|Schermata|Registrazione schermo|"
    r"Capture d.écran|Bildschirmfoto|Captura de pantalla)[ _\-]",
    re.I,
)
SKIP_NAMES = {".DS_Store", ".localized", "desktop.ini", "Thumbs.db", ".directory"}
WIN_FOLDER_KEYS = {
    "desktop": "Desktop",
    "downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
    "documents": "Personal",
}

_run = subprocess.run  # patched in tests


# ---------- platform & paths ----------

def platform_name() -> str:
    forced = os.environ.get("ORGANIZE_PLATFORM")
    if forced:
        return forced
    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    return "linux"


def test_mode() -> bool:
    return bool(os.environ.get("ORGANIZE_HOME"))


def home() -> Path:
    return Path(os.environ.get("ORGANIZE_HOME") or Path.home())


def _xdg_user_dirs() -> dict:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    cfg = Path(xdg) if xdg and not test_mode() else home() / ".config"
    out = {}
    f = cfg / "user-dirs.dirs"
    if not f.exists():
        return out
    keys = {"XDG_DESKTOP_DIR": "desktop", "XDG_DOWNLOAD_DIR": "downloads", "XDG_DOCUMENTS_DIR": "documents"}
    for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r'\s*(XDG_\w+_DIR)\s*=\s*"?(.*?)"?\s*$', line)
        if m and m.group(1) in keys:
            val = m.group(2).replace("$HOME", str(home()))
            out[keys[m.group(1)]] = Path(val)
    return out


def _windows_user_dirs() -> dict:
    out = {}
    try:
        import winreg  # type: ignore
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                           r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders")
        for name, reg in WIN_FOLDER_KEYS.items():
            try:
                val, _ = winreg.QueryValueEx(k, reg)
                out[name] = Path(os.path.expandvars(val))
            except OSError:
                pass
    except Exception:
        pass
    return out


def user_folders() -> dict:
    """Real Desktop / Downloads / Documents for this OS (handles XDG and OneDrive redirects)."""
    defaults = {"desktop": home() / "Desktop", "downloads": home() / "Downloads", "documents": home() / "Documents"}
    plat = platform_name()
    if plat == "linux":
        found = _xdg_user_dirs()
    elif plat == "windows" and not test_mode():
        found = _windows_user_dirs()
    else:
        found = {}
    return {k: found.get(k, v) for k, v in defaults.items()}


RUN_ID_RE = re.compile(r"^\d{8}-\d{6}(-\d+)?$")
CLOUD_ROOT_RE =re.compile(r"^(iCloud Drive|OneDrive.*|Dropbox.*|Google Drive.*|My Drive|Box|pCloud Drive|MEGA)$", re.I)


def _abs(p: Path) -> Path:
    """Absolute path WITHOUT following a symlink at the last component (parents are resolved)."""
    p = Path(os.path.abspath(str(p.expanduser())))
    return p.parent.resolve() / p.name


def skill_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def _key(p: Path) -> str:
    """Comparable form of a path. macOS and Windows filesystems are case-insensitive and
    normalize Unicode, so compare case-folded NFC there; Linux compares exactly."""
    s = str(p).rstrip("/\\") or str(p)
    if platform_name() in ("macos", "windows"):
        s = unicodedata.normalize("NFC", s).casefold()
    return s


def _inside(child: Path, parent: Path) -> bool:
    """True if child is parent or anywhere below it."""
    c, p = _key(child), _key(parent)
    return c == p or c.startswith(p.rstrip("/\\") + os.sep) or c.startswith(p.rstrip("/\\") + "/")


def check_path(p: Path, role: str) -> Optional[str]:
    """Enforce the safety rules in code, whatever the plan says.

    Returns an error message, or None when the path is allowed. Allowed: items strictly
    inside the user's Desktop / Downloads / Documents, not hidden, not a cloud-sync root,
    not this tool, not ~/.claude.
    """
    a = _abs(p)
    roots = [_abs(r).resolve() for r in user_folders().values()]
    root = next((r for r in roots if _inside(a, r) and _key(a) != _key(r)), None)
    if root is None:
        return f"{role} must be inside Desktop, Downloads or Documents"
    rel = a.parts[len(root.parts):]
    if any(part.startswith(".") for part in rel):
        return f"{role} is (inside) a hidden item"
    if CLOUD_ROOT_RE.match(rel[0]) and len(rel) == 1:
        return f"{role} is a cloud-sync folder"
    for protected in (skill_dir(), _abs(home()).resolve() / ".claude"):
        if _inside(protected, a) or _inside(a, protected):
            return f"{role} contains or is inside a protected folder ({protected.name})"
    try:
        for link in (_abs(home()).resolve() / ".claude" / "skills").iterdir():
            if link.is_symlink():
                target = link.resolve()
                if role == "source" and (_inside(target, a) or _inside(a, target)):
                    return f"{role} holds an installed skill ({link.name})"
    except OSError:
        pass
    return None


def journal_dir() -> Path:
    d = home() / ".organize" / "journal"
    d.mkdir(parents=True, exist_ok=True)
    return d


def unique_dest(dest: Path, taken=lambda p: False) -> Path:
    def used(p: Path) -> bool:
        return p.exists() or p.is_symlink() or taken(p)

    if not used(dest):
        return dest
    is_dir = dest.is_dir()
    stem, suffix = (dest.name, "") if is_dir or not dest.suffix else (dest.stem, dest.suffix)
    n = 2
    while True:
        cand = dest.with_name(f"{stem} ({n}){suffix}")
        if not used(cand):
            return cand
        n += 1


# ---------- trash backends ----------

class TrashAccessError(Exception):
    pass


class MacTrash:
    name = "macos"

    def dir(self) -> Path:
        return home() / ".Trash"

    def put(self, src: Path) -> dict:
        d = self.dir()
        d.mkdir(exist_ok=True)
        final = unique_dest(d / src.name)
        shutil.move(str(src), str(final))
        return {"dst": str(final)}

    def restore(self, entry: dict) -> Tuple[str, str]:
        return _move_back(Path(entry["dst"]), Path(entry["src"]))

    def list(self) -> list:
        try:
            names = os.listdir(self.dir())
        except PermissionError as e:
            raise TrashAccessError(str(e))
        return [_describe(self.dir() / n) for n in sorted(names) if n not in SKIP_NAMES]

    def empty(self) -> Optional[int]:
        try:
            return _clear_dir(self.dir())
        except PermissionError:
            if test_mode():
                raise TrashAccessError("no access")
            _run(["osascript", "-e", 'tell application "Finder" to empty trash'], check=True,
                 capture_output=True)
            return None


class LinuxTrash:
    """freedesktop.org Trash spec (home trash): files/ + info/<name>.trashinfo."""
    name = "freedesktop"

    def base(self) -> Path:
        xdg = os.environ.get("XDG_DATA_HOME")
        root = Path(xdg) if xdg and not test_mode() else home() / ".local" / "share"
        return root / "Trash"

    def put(self, src: Path) -> dict:
        files, info = self.base() / "files", self.base() / "info"
        files.mkdir(parents=True, exist_ok=True)
        info.mkdir(parents=True, exist_ok=True)
        final = unique_dest(files / src.name, taken=lambda p: (info / f"{p.name}.trashinfo").exists())
        info_file = info / f"{final.name}.trashinfo"
        info_file.write_text(
            "[Trash Info]\n"
            f"Path={quote(str(_abs(src)), safe='/')}\n"
            f"DeletionDate={datetime.now().strftime('%Y-%m-%dT%H:%M:%S')}\n",
            encoding="utf-8",
        )
        try:
            shutil.move(str(src), str(final))
        except Exception:
            info_file.unlink()
            raise
        return {"dst": str(final), "info": str(info_file)}

    def restore(self, entry: dict) -> Tuple[str, str]:
        status, msg = _move_back(Path(entry["dst"]), Path(entry["src"]))
        if status == "ok":
            # Derive the .trashinfo path; never trust a path from the journal for deletion.
            (self.base() / "info" / f"{Path(entry['dst']).name}.trashinfo").unlink(missing_ok=True)
        return status, msg

    def list(self) -> list:
        files = self.base() / "files"
        if not files.exists():
            return []
        out = []
        for n in sorted(os.listdir(files)):
            item = _describe(files / n)
            info = self.base() / "info" / f"{n}.trashinfo"
            if info.exists():
                m = re.search(r"^Path=(.*)$", info.read_text(encoding="utf-8", errors="replace"), re.M)
                if m:
                    item["original_path"] = unquote(m.group(1))
            out.append(item)
        return out

    def empty(self) -> Optional[int]:
        n = _clear_dir(self.base() / "files") if (self.base() / "files").exists() else 0
        for sub in ("info", "expunged"):
            if (self.base() / sub).exists():
                _clear_dir(self.base() / sub)
        return n


class WindowsTrash:
    """Recycle Bin via PowerShell (Microsoft.VisualBasic.FileIO / Shell.Application)."""
    name = "windows"

    def _ps(self, script: str, target: Optional[str] = None) -> str:
        env = dict(os.environ)
        if target is not None:
            env["ORGANIZE_TARGET"] = target
        r = _run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                 capture_output=True, text=True, env=env)
        if r.returncode != 0:
            raise OSError((r.stderr or r.stdout or "powershell failed").strip())
        return r.stdout or ""

    def put(self, src: Path) -> dict:
        if src.is_symlink() or _is_junction(src):
            # Never let the Recycle Bin follow a link into its target: remove only the link
            # (no data lost) and remember its target so undo can recreate it.
            target = os.readlink(str(src))
            is_dir = src.is_dir()
            if is_dir and _is_junction(src):
                os.rmdir(str(src))
            else:
                os.unlink(str(src))
            return {"dst": None, "link_target": target, "link_is_dir": is_dir}
        fn = "DeleteDirectory" if src.is_dir() else "DeleteFile"
        self._ps(
            "Add-Type -AssemblyName Microsoft.VisualBasic; "
            f"[Microsoft.VisualBasic.FileIO.FileSystem]::{fn}($env:ORGANIZE_TARGET, "
            "'OnlyErrorDialogs', 'SendToRecycleBin')",
            target=str(_abs(src)),
        )
        return {"dst": None}

    def restore(self, entry: dict) -> Tuple[str, str]:
        if entry.get("link_target"):
            link = Path(entry["src"])
            if link.exists() or link.is_symlink():
                return "skipped", "the original location is taken"
            os.symlink(entry["link_target"], str(link), target_is_directory=bool(entry.get("link_is_dir")))
            return "ok", "link recreated"
        return "skipped", "in the Recycle Bin: right-click it there and choose Restore"

    def list(self) -> list:
        out = self._ps(
            "$s = New-Object -ComObject Shell.Application; "
            "@($s.Namespace(10).Items() | ForEach-Object { [pscustomobject]@{ "
            "name = $_.Name; path = $_.Path; is_dir = $_.IsFolder; size = $_.Size } }) "
            "| ConvertTo-Json -Compress"
        ).strip()
        if not out:
            return []
        data = json.loads(out)
        return data if isinstance(data, list) else [data]

    def empty(self) -> Optional[int]:
        self._ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue")
        return None


def _is_junction(p: Path) -> bool:
    try:
        return bool(getattr(os.path, "isjunction", lambda _: False)(str(p)))
    except OSError:
        return False


def trash_backend():
    return {"macos": MacTrash, "linux": LinuxTrash, "windows": WindowsTrash}[platform_name()]()


def _backend_by_name(name: Optional[str]):
    return {"macos": MacTrash, "freedesktop": LinuxTrash, "windows": WindowsTrash}.get(name or "", MacTrash)()


def _trash_files_dir(backend: Optional[str]) -> Optional[Path]:
    """Folder where a backend keeps trashed files (None for the Windows Recycle Bin)."""
    if backend == "macos":
        return MacTrash().dir()
    if backend == "freedesktop":
        return LinuxTrash().base() / "files"
    return None


def _clear_dir(d: Path) -> int:
    n = 0
    for name in os.listdir(d):
        p = d / name
        if p.is_dir() and not p.is_symlink():
            shutil.rmtree(p)
        else:
            p.unlink()
        n += 1
    return n


def _move_back(now: Path, orig: Path) -> Tuple[str, str]:
    if not now.exists() and not now.is_symlink():
        return "skipped", "it was moved or deleted since"
    if orig.exists():
        return "skipped", "the original location is taken"
    orig.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(now), str(orig))
    return "ok", ""


def _describe(p: Path) -> dict:
    try:
        st = p.lstat()
    except OSError:
        return {"name": p.name, "path": str(p)}
    is_dir = p.is_dir() and not p.is_symlink()
    return {"name": p.name, "path": str(p), "is_dir": is_dir,
            "size": _dir_size(p)[0] if is_dir else st.st_size,
            "modified": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")}


# ---------- apply / undo ----------

def _new_run_id() -> str:
    base = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id, n = base, 2
    while (journal_dir() / f"{run_id}.jsonl").exists() or (journal_dir() / f"{run_id}.undone").exists():
        run_id, n = f"{base}-{n}", n + 1
    return run_id


def _mkdirs(path: Path, log) -> None:
    missing = []
    p = path
    while not p.exists():
        missing.append(p)
        p = p.parent
    for d in reversed(missing):
        d.mkdir()
        log({"op": "mkdir", "dst": str(d)})


def _is_inside(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def apply_plan(actions: List[dict]) -> Tuple[str, List[dict]]:
    run_id = _new_run_id()
    jpath = journal_dir() / f"{run_id}.jsonl"
    results: List[dict] = []
    trash = trash_backend()

    with jpath.open("a", encoding="utf-8") as jf:
        def log(entry: dict) -> None:
            jf.write(json.dumps(entry, ensure_ascii=False) + "\n")
            jf.flush()

        for a in actions:
            op = a.get("op")
            src = _abs(Path(a["src"])) if a.get("src") else None
            dst = _abs(Path(a["dst"])) if a.get("dst") else None
            res = {"op": op, "src": a.get("src"), "dst": a.get("dst"), "status": "ok", "msg": ""}
            denied = None
            if src is not None and op in ("move", "rename", "trash"):
                denied = check_path(src, "source")
            if not denied and dst is not None and op in ("move", "rename", "mkdir"):
                denied = check_path(dst, "destination")
            if denied:
                res["status"], res["msg"] = "error", f"refused: {denied}"
                results.append(res)
                continue
            try:
                if op == "mkdir":
                    if dst.exists():
                        res["status"], res["msg"] = "skipped", "already exists"
                    else:
                        _mkdirs(dst, log)
                elif src is None:
                    res["status"], res["msg"] = "error", "missing src"
                elif not src.exists() and not src.is_symlink():
                    res["status"], res["msg"] = "skipped", "source no longer exists"
                elif op == "trash":
                    info = trash.put(src)
                    log({"op": "trash", "backend": trash.name, "src": str(src), **info})
                    res["dst"] = info.get("dst")
                elif op in ("move", "rename"):
                    if dst is None:
                        res["status"], res["msg"] = "error", "missing dst"
                    elif src.is_dir() and _is_inside(dst.parent, src):
                        res["status"], res["msg"] = "error", "cannot move a folder into itself"
                    else:
                        _mkdirs(dst.parent, log)
                        final = unique_dest(dst)
                        shutil.move(str(src), str(final))
                        log({"op": "move", "src": str(src), "dst": str(final)})
                        res["dst"] = str(final)
                        if final != dst:
                            res["msg"] = f"name taken, saved as {final.name}"
                else:
                    res["status"], res["msg"] = "error", f"unknown op {op!r}"
            except Exception as e:  # report and keep going
                res["status"], res["msg"] = "error", str(e)
            results.append(res)

    return run_id, results


def list_runs() -> List[str]:
    return sorted(p.stem for p in journal_dir().glob("*.jsonl"))


def undo(run_id: Optional[str] = None) -> List[dict]:
    runs = list_runs()
    if not runs:
        return []
    run_id = run_id or runs[-1]
    if not RUN_ID_RE.match(run_id) or run_id not in runs:
        raise ValueError(f"unknown run id {run_id!r} (see `runs`)")
    jpath = journal_dir() / f"{run_id}.jsonl"
    entries = [json.loads(l) for l in jpath.read_text(encoding="utf-8").splitlines() if l.strip()]
    results = []
    for e in reversed(entries):
        res = {"op": f"undo-{e.get('op')}", "src": e.get("dst"), "dst": e.get("src"), "status": "ok", "msg": ""}
        # The journal is a file on disk: re-check every path it names before acting on it.
        if e.get("op") == "mkdir":
            denied = check_path(Path(e["dst"]), "folder")
        elif e.get("op") == "move":
            denied = check_path(Path(e["src"]), "destination") or check_path(Path(e["dst"]), "source")
        elif e.get("op") == "trash":
            denied = check_path(Path(e["src"]), "destination")
            if not denied and e.get("dst"):
                tdir = _trash_files_dir(e.get("backend"))
                if tdir is None or not _inside(_abs(Path(e["dst"])), _abs(tdir).resolve()):
                    denied = "trashed item is not in the Trash"
        else:
            denied = f"unknown journal op {e.get('op')!r}"
        if denied:
            res["status"], res["msg"] = "error", f"refused: {denied}"
            results.append(res)
            continue
        try:
            if e["op"] == "mkdir":
                d = Path(e["dst"])
                if d.exists() and not [n for n in os.listdir(d) if n not in SKIP_NAMES]:
                    for n in os.listdir(d):
                        (d / n).unlink()
                    d.rmdir()
                else:
                    res["status"], res["msg"] = "skipped", "folder not empty or gone"
            elif e["op"] == "trash":
                res["status"], res["msg"] = _backend_by_name(e.get("backend")).restore(e)
            else:
                res["status"], res["msg"] = _move_back(Path(e["dst"]), Path(e["src"]))
        except Exception as ex:
            res["status"], res["msg"] = "error", str(ex)
        results.append(res)
    jpath.rename(jpath.with_suffix(".undone"))
    return results


# ---------- scan ----------

def _sha1(path: Path) -> Optional[str]:
    try:
        if path.stat().st_size > HASH_LIMIT:
            return None
        h = hashlib.sha1()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _dir_size(path: Path) -> Tuple[int, bool]:
    total, count = 0, 0
    for root, dirs, files in os.walk(path):
        for f in files:
            count += 1
            if count > SIZE_WALK_LIMIT:
                return total, True
            try:
                total += os.lstat(os.path.join(root, f)).st_size
            except OSError:
                pass
    return total, False


def _mdls(path: Path) -> Tuple[Optional[str], List[str]]:
    try:
        out = _run(["mdls", "-name", "kMDItemKind", "-name", "kMDItemWhereFroms", str(path)],
                   capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return None, []
    kind = None
    m = re.search(r'kMDItemKind\s*=\s*"([^"]*)"', out)
    if m:
        kind = m.group(1)
    froms = []
    m = re.search(r"kMDItemWhereFroms\s*=\s*\((.*?)\)", out, re.S)
    if m:
        froms = re.findall(r'"([^"]*)"', m.group(1))
    return kind, froms


def _windows_zone_url(path: Path) -> List[str]:
    """Download URL from the Zone.Identifier alternate data stream (Windows)."""
    try:
        with open(str(path) + ":Zone.Identifier", encoding="utf-8", errors="replace") as f:
            txt = f.read()
        return re.findall(r"^(?:HostUrl|ReferrerUrl)=(.*)$", txt, re.M)
    except OSError:
        return []


def _is_code_project(path: Path) -> bool:
    try:
        names = set(os.listdir(path))
    except OSError:
        return False
    if names & CODE_MARKERS:
        return True
    return any(n.endswith((".xcodeproj", ".sln", ".csproj")) for n in names)


def _is_hidden(p: Path) -> bool:
    if p.name.startswith(".") or p.name in SKIP_NAMES:
        return True
    if platform_name() == "windows" and not test_mode():
        try:
            import stat
            return bool(p.stat().st_file_attributes & (stat.FILE_ATTRIBUTE_HIDDEN | stat.FILE_ATTRIBUTE_SYSTEM))
        except (AttributeError, OSError):
            return False
    return False


def scan(paths: List[Path], metadata: bool = True) -> List[dict]:
    items: List[dict] = []
    plat = platform_name()
    for base in paths:
        if not base.exists():
            continue
        try:
            entries = sorted(base.iterdir(), key=lambda p: p.name.lower())
        except PermissionError:
            items.append({"path": str(base), "error": "no_access"})
            continue
        sibling_names = {p.name for p in entries}
        for p in entries:
            if _is_hidden(p):
                continue
            try:
                st = p.lstat()
            except OSError:
                continue
            is_dir = p.is_dir() and not p.is_symlink()
            flags: List[str] = []
            item = {
                "path": str(p), "name": p.name, "location": base.name, "is_dir": is_dir,
                "ext": "" if is_dir else p.suffix.lower(),
                "modified": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                "size": st.st_size, "sha1": None, "kind": None, "where_from": [],
                "flags": flags, "duplicate_of": None,
            }
            if is_dir:
                item["size"], truncated = _dir_size(p)
                if truncated:
                    item["size_truncated"] = True
                if _is_code_project(p):
                    flags.append("code_project")
                try:
                    if not [n for n in os.listdir(p) if n not in SKIP_NAMES]:
                        flags.append("empty_dir")
                except OSError:
                    pass
            else:
                if p.name.startswith("~$") or item["ext"] in TEMP_EXT:
                    flags.append("temp")
                else:
                    item["sha1"] = _sha1(p)
                if item["ext"] in INSTALLER_EXT:
                    flags.append("installer")
                if item["ext"] in ARCHIVE_EXT:
                    stem = p.name[: -len(p.suffix)]
                    if stem in sibling_names and (base / stem).is_dir():
                        flags.append("archive_extracted")
            if SCREENSHOT_RE.match(p.name):
                flags.append("screenshot")
            if metadata and not test_mode():
                if plat == "macos":
                    item["kind"], item["where_from"] = _mdls(p)
                elif plat == "windows" and not is_dir:
                    item["where_from"] = _windows_zone_url(p)
            items.append(item)

    # identical files: keep the copy that already lives in Documents (or the first seen)
    by_hash: dict = {}
    for it in items:
        if it.get("sha1"):
            by_hash.setdefault(it["sha1"], []).append(it)
    for group in by_hash.values():
        if len(group) < 2:
            continue
        keeper = next((g for g in group if g["location"] == user_folders()["documents"].name), group[0])
        for g in group:
            if g is not keeper:
                g["flags"].append("duplicate")
                g["duplicate_of"] = keeper["path"]
    return items


# ---------- project safety ----------

def check_project(path: Path) -> dict:
    """What breaks if this folder moves: virtualenvs (absolute paths) and scheduled jobs pointing at it."""
    path = path.expanduser()
    venvs = []
    for root, dirs, files in os.walk(path):
        if Path(root).relative_to(path).parts.__len__() >= 3:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".git")]
        if "pyvenv.cfg" in files:
            venvs.append(root)
    needle = str(path.resolve())
    jobs = []
    plat = platform_name()
    if plat == "macos":
        la = home() / "Library" / "LaunchAgents"
        if la.exists():
            for f in la.glob("*.plist"):
                try:
                    if needle in f.read_text(encoding="utf-8", errors="replace"):
                        jobs.append(f"launchd: {f}")
                except OSError:
                    pass
    elif plat == "linux":
        sd = home() / ".config" / "systemd" / "user"
        if sd.exists():
            for f in sd.iterdir():
                if f.is_file() and needle in f.read_text(encoding="utf-8", errors="replace"):
                    jobs.append(f"systemd: {f}")
    if not test_mode():
        try:
            if plat in ("macos", "linux") and shutil.which("crontab"):
                out = _run(["crontab", "-l"], capture_output=True, text=True, timeout=10).stdout
                jobs += [f"crontab: {l}" for l in out.splitlines() if needle in l]
            elif plat == "windows":
                out = _run(["schtasks", "/query", "/fo", "LIST", "/v"], capture_output=True, text=True,
                           timeout=30).stdout
                current = ""
                for l in out.splitlines():
                    if l.lower().startswith("taskname:"):
                        current = l.split(":", 1)[1].strip()
                    if needle.lower() in l.lower() and current:
                        jobs.append(f"task scheduler: {current}")
        except Exception:
            pass
    return {"path": str(path), "venvs": venvs, "scheduled_jobs": sorted(set(jobs)),
            "safe_to_move": not venvs and not jobs}


# ---------- CLI ----------

NO_ACCESS_HINT = {
    "macos": "Grant Full Disk Access: System Settings > Privacy & Security > Full Disk Access, "
             "enable the app running Claude Code (Terminal / iTerm / VS Code), then restart it.",
    "linux": "Check the permissions of ~/.local/share/Trash.",
    "windows": "PowerShell could not read the Recycle Bin.",
}


def _print(obj) -> None:
    sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
    print(json.dumps(obj, indent=1, ensure_ascii=False))


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("info")
    s = sub.add_parser("scan")
    s.add_argument("paths", nargs="*")
    s.add_argument("--no-metadata", action="store_true")
    c = sub.add_parser("check-project")
    c.add_argument("path")
    a = sub.add_parser("apply")
    a.add_argument("plan")
    u = sub.add_parser("undo")
    u.add_argument("run_id", nargs="?")
    sub.add_parser("runs")
    sub.add_parser("trash-list")
    e = sub.add_parser("empty-trash")
    e.add_argument("--yes-really", action="store_true")
    args = ap.parse_args(argv)
    plat = platform_name()

    if args.cmd == "info":
        trash = trash_backend()
        try:
            trash.list()
            access = True
        except Exception:
            access = False
        _print({"platform": plat, "home": str(home()),
                "folders": {k: str(v) for k, v in user_folders().items()},
                "trash_backend": trash.name, "trash_readable": access,
                "journal": str(journal_dir())})
    elif args.cmd == "scan":
        f = user_folders()
        paths = [Path(p).expanduser() for p in args.paths] or [f["desktop"], f["downloads"], f["documents"]]
        _print(scan(paths, metadata=not args.no_metadata))
    elif args.cmd == "check-project":
        _print(check_project(Path(args.path)))
    elif args.cmd == "apply":
        plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
        actions = plan["actions"] if isinstance(plan, dict) else plan
        run_id, results = apply_plan(actions)
        _print({"run_id": run_id, "results": results})
    elif args.cmd == "undo":
        try:
            _print(undo(args.run_id))
        except ValueError as ex:
            _print({"error": str(ex)})
            return 1
    elif args.cmd == "runs":
        _print(list_runs())
    elif args.cmd == "trash-list":
        try:
            _print(trash_backend().list())
        except (TrashAccessError, OSError):
            _print({"error": "no_access", "hint": NO_ACCESS_HINT[plat]})
            return 2
    elif args.cmd == "empty-trash":
        if not args.yes_really:
            print("Refusing: emptying the Trash is permanent. Re-run with --yes-really.", file=sys.stderr)
            return 1
        try:
            _print({"emptied": True, "removed": trash_backend().empty()})
        except (TrashAccessError, OSError) as ex:
            _print({"error": "no_access", "hint": NO_ACCESS_HINT[plat], "detail": str(ex)})
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

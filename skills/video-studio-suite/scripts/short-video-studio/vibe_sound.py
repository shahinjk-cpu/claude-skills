#!/usr/bin/env python3
"""
[Vibe Sound CC0 声学资产集成与清洗工具]
基于 vibe-motion/sound 规范集成 Freesound CC0 检索与清洗，
全面使用基于 ASSETS_DIR 的相对路径（跨机零失效），并按六大流派母版覆盖全部 24 套风格。
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import (
    ASSETS_DIR,
    find_bin,
    get_wav_duration_sec,
    load_style_spectrum_entry,
    maybe_reexec_in_venv,
    write_json,
)

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) short-video-studio-vibe-sound"}
CACHE_DIR = Path.home() / ".cache" / "sfx-sources"
INDEX_PATH = CACHE_DIR / "index.json"
SOUND_VIBE_DIR = ASSETS_DIR / "sound_vibe"
FS_LICENSE = {"cc0": '"Creative Commons 0"', "by": '("Attribution" OR "Creative Commons 0")', "any": None}
FS_LIC_SHORT = {
    "Creative Commons 0": "CC0",
    "Attribution": "BY",
    "Attribution NonCommercial": "BY-NC",
    "Sampling+": "Sampling+",
}
FS_SORT = {
    "downloads": "Downloads (most first)",
    "rating": "Rating (highest first)",
    "relevance": "Automatic by relevance",
    "short": "Duration (shortest first)",
}

# 六大流派母版到 7 套内置 CC0 真实物理音库的兜底映射，覆盖全库 style_01 ~ style_24
ARCHETYPE_TO_VIBE_STYLE: Dict[str, str] = {
    "arch_01_tech_ui_console": "style_15",
    "arch_02_high_contrast_story": "style_03",
    "arch_03_editorial_matte_depth": "style_12",
    "arch_04_punch_talking_head": "style_14",
    "arch_05_cinema_slow_space": "style_06",
    "arch_06_paper_stopmotion": "style_05",
}

STYLE_SOUND_MAP: Dict[str, Dict[str, Any]] = {
    "style_14": {
        "bgm": {"src": "fs_680113_Pop-Guitar-Loop-Thing.mp3", "start": 0.60, "end": 65.50, "bpm": 120.0},
        "sfx": {
            "transition": ("fs_585257_swoosh-1-mp3.mp3", 0.10, 0.36, -1.5),
            "accent": ("fs_704935_Wooden-Tap.mp3", 0.82, 1.05, 0.0),
            "ui": ("fs_411462_Bubble-Pop.mp3", 0.14, 0.34, -2.0),
        },
        "sfx_min_gap_sec": 7.5,
        "sfx_gain_db": -10.0,
        "bgm_base_db": -12.0,
        "duck_depth_db": -10.0,
    },
    "style_02": {
        "bgm": {"src": "fs_69195_Mix05_90BPM-mp3.mp3", "start": 0.02, "end": 21.30, "bpm": 90.0},
        "sfx": {
            "transition": ("fs_585257_swoosh-1-mp3.mp3", 0.12, 0.34, 0.0),
            "accent": ("fs_512389_Bass-Impact-Ki_01-mp3.mp3", 0.04, 0.48, -2.0),
            "ui": ("fs_878248_UI-Hover-Micro-Swish.mp3", 0.01, 0.18, -1.5),
        },
        "sfx_min_gap_sec": 6.0,
        "sfx_gain_db": -9.0,
        "bgm_base_db": -11.5,
        "duck_depth_db": -10.5,
    },
    "style_03": {
        "bgm": {"src": "fs_713517_Perspire-Loop-Corporate-style-background.mp3", "start": 0.02, "end": 59.80, "bpm": 110.0},
        "sfx": {
            "transition": ("fs_623709_soft_swoosh_with_noisy_ambience-wav.mp3", 0.04, 0.36, -2.0),
            "accent": ("fs_369710_Wood-Knock.mp3", 0.00, 0.22, -1.0),
            "ui": ("fs_704935_Wooden-Tap.mp3", 0.82, 1.06, -1.0),
        },
        "sfx_min_gap_sec": 6.5,
        "sfx_gain_db": -10.0,
        "bgm_base_db": -12.5,
        "duck_depth_db": -10.0,
    },
    "style_12": {
        "bgm": {"src": "fs_629153_Dusty-Lofi-Melody-Loop-75-BPM-wav.mp3", "start": 0.02, "end": 49.50, "bpm": 75.0},
        "sfx": {
            "transition": ("fs_878248_UI-Hover-Micro-Swish.mp3", 0.01, 0.18, -2.0),
            "accent": ("fs_411462_Bubble-Pop.mp3", 0.15, 0.32, -2.0),
            "ui": ("fs_528561_Soft-UI-Button-Click.mp3", 0.00, 0.14, -1.0),
        },
        "sfx_min_gap_sec": 7.5,
        "sfx_gain_db": -11.0,
        "bgm_base_db": -13.0,
        "duck_depth_db": -9.5,
    },
    "style_06": {
        "bgm": {"src": "fs_668907_Free-Cinematic-Emotional-Piano-92bpm-D-M.mp3", "start": 0.02, "end": 41.40, "bpm": 92.0},
        "sfx": {
            "transition": ("fs_623709_soft_swoosh_with_noisy_ambience-wav.mp3", 0.04, 0.42, -3.0),
            "accent": ("fs_676375_Film-Camera-Click-Shutter.mp3", 0.96, 1.28, -1.0),
            "ui": ("fs_676375_Film-Camera-Click-Shutter.mp3", 0.20, 0.48, -2.0),
        },
        "sfx_min_gap_sec": 11.0,
        "sfx_gain_db": -13.5,
        "bgm_base_db": -11.5,
        "duck_depth_db": -11.0,
    },
    "style_05": {
        "bgm": {"src": "fs_347815_Warm-Breeze-mp3.mp3", "start": 0.88, "end": 22.30, "bpm": 104.0},
        "sfx": {
            "transition": ("fs_82379_paper-flip-3-wav.mp3", 0.05, 0.34, 0.0),
            "accent": ("fs_82379_paper-flip-3-wav.mp3", 0.05, 0.28, 0.0),
            "ui": ("fs_369710_Wood-Knock.mp3", 0.00, 0.20, -1.5),
        },
        "sfx_min_gap_sec": 6.5,
        "sfx_gain_db": -9.5,
        "bgm_base_db": -12.5,
        "duck_depth_db": -10.0,
    },
    "style_15": {
        "bgm": {"src": "fs_531463_Waterfall-synth-loop-wav.mp3", "start": 0.02, "end": 34.10, "bpm": 120.0},
        "sfx": {
            "transition": ("fs_878248_UI-Hover-Micro-Swish.mp3", 0.01, 0.19, -1.0),
            "accent": ("fs_378085_mechanical-key-hard-wav.mp3", 0.08, 0.25, 0.0),
            "ui": ("fs_528561_Soft-UI-Button-Click.mp3", 0.00, 0.15, -1.0),
            "receipt": ("fs_217181_Old-Till-Printer-Feeding-Receipt-Paper-w.mp3", 4.95, 5.55, -1.0),
        },
        "sfx_min_gap_sec": 6.5,
        "sfx_gain_db": -10.0,
        "bgm_base_db": -12.5,
        "duck_depth_db": -10.0,
    },
}


def _to_asset_rel(path_or_str: str | Path) -> str:
    """将任意路径规范化为相对 ASSETS_DIR 的 POSIX 路径，防止写入本机绝对路径。"""
    s = str(path_or_str)
    p = Path(s)
    if p.is_absolute():
        try:
            return p.resolve().relative_to(ASSETS_DIR.resolve()).as_posix()
        except Exception:
            if "assets/" in s:
                return s.split("assets/", 1)[1].lstrip("/")
    return s.replace("\\", "/").lstrip("/")


def _resolve_asset_path(rel_or_abs: str) -> str:
    rel = _to_asset_rel(rel_or_abs)
    return str((ASSETS_DIR / rel).resolve())


def _build_beat_grid(dur_sec: float, bpm: float) -> Tuple[List[float], List[float]]:
    beat_sec = 60.0 / max(40.0, min(220.0, float(bpm)))
    beats: List[float] = []
    downs: List[float] = []
    t = 0.0
    idx = 0
    while t < max(0.5, dur_sec) - 0.03:
        beats.append(round(t, 4))
        if idx % 4 == 0:
            downs.append(round(t, 4))
        t += beat_sec
        idx += 1
    return beats, downs


def _fetch(url: str, timeout: int = 60, tries: int = 3) -> bytes:
    for n in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read()
        except Exception as e:
            if n == tries - 1:
                raise e if isinstance(e, OSError) else OSError(repr(e))
            time.sleep(1 + n)
    return b""


def search_freesound(query: str, license_mode: str = "cc0", limit: int = 8, pages: int = 2) -> List[Dict[str, Any]]:
    q = {"q": query, "s": FS_SORT["relevance"]}
    if FS_LICENSE[license_mode]:
        q["f"] = "license:" + FS_LICENSE[license_mode]
    with ThreadPoolExecutor(max(1, pages)) as ex:
        htmls = list(ex.map(lambda n: _fetch("https://freesound.org/search/?" + urllib.parse.urlencode({**q, "page": n})).decode(), range(1, pages + 1)))
    rows: List[Dict[str, Any]] = []
    for blk in (b for h in htmls for b in h.split('class="bw-search__result"')[1:]):
        g = lambda k: (re.search(rf'data-{k}="([^"]*)"', blk) or [None, ""])[1]
        lic = re.search(r'title="License: ([^"]+)"', blk)
        rt = re.search(r'aria-label="Average rating of ([\d.]+)"', blk)
        rn = re.search(r'bw-rating__count[^>]*>\((\d+)\)', blk)
        desc = re.search(r'<div class="max-h-60px[^"]*"\s*>\s*(.*?)\s*</div>', blk, re.S)
        sid, user, dl = g("sound-id"), g("username"), int(g("num-downloads") or 0)
        rows.append({
            "key": f"fs:{sid}",
            "title": html.unescape(g("title")),
            "dur": f"{float(g('duration') or 0):.1f}s",
            "author": user,
            "license": FS_LIC_SHORT.get(lic.group(1), lic.group(1)) if lic else "?",
            "preview": g("mp3").replace("-lq.mp3", "-hq.mp3"),
            "url": g("mp3").replace("-lq.mp3", "-hq.mp3"),
            "downloads": dl,
            "stats": f"↓{dl} ★{rt[1]}({rn[1]})" if rt and rn else f"↓{dl} ★-",
            "desc": html.unescape(re.sub(r"<[^>]+>|\s+", " ", desc[1])).strip()[:90] if desc else "",
        })
    rows.sort(key=lambda r: -r["downloads"])
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    idx = json.loads(INDEX_PATH.read_text(encoding="utf-8")) if INDEX_PATH.exists() else {}
    idx.update({r["key"]: r for r in rows})
    INDEX_PATH.write_text(json.dumps(idx, ensure_ascii=False), encoding="utf-8")
    return rows[:limit]


SFX_DEDUP_ALIAS: Dict[str, str] = {
    "sound_vibe/sfx/style_02_transition.wav": "sound_vibe/sfx/style_14_transition.wav",
    "sound_vibe/sfx/style_12_transition.wav": "sound_vibe/sfx/style_02_ui.wav",
    "sound_vibe/sfx/style_15_transition.wav": "sound_vibe/sfx/style_02_ui.wav",
    "sound_vibe/sfx/style_12_accent.wav": "sound_vibe/sfx/style_14_ui.wav",
    "sound_vibe/sfx/style_15_ui.wav": "sound_vibe/sfx/style_12_ui.wav",
    "sound_vibe/sfx/style_03_ui.wav": "sound_vibe/sfx/style_14_accent.wav",
    "sound_vibe/sfx/style_05_ui.wav": "sound_vibe/sfx/style_03_accent.wav",
    "sound_vibe/sfx/style_06_transition.wav": "sound_vibe/sfx/style_03_transition.wav",
    "sound_vibe/sfx/style_05_accent.wav": "sound_vibe/sfx/style_05_transition.wav",
}


def rebuild_relative_manifest_and_beats(out_dir: Path | None = None) -> Dict[str, Any]:
    """基于已清洗 BGM (.m4a/.wav) 与去重 SFX 重建相对路径 manifest 并补全节拍时间轴。"""
    out_dir = out_dir or SOUND_VIBE_DIR
    bgm_dir = out_dir / "bgm"
    sfx_dir = out_dir / "sfx"
    manifest: Dict[str, Any] = {"styles": {}, "archetype_fallback": ARCHETYPE_TO_VIBE_STYLE}

    for sid, cfg in STYLE_SOUND_MAP.items():
        b = cfg["bgm"]
        dst_m4a = bgm_dir / f"{sid}_bgm.m4a"
        dst_wav = bgm_dir / f"{sid}_bgm.wav"
        dst_b = dst_m4a if dst_m4a.exists() else dst_wav
        if not dst_b.exists():
            continue
        dur_b = round(get_wav_duration_sec(dst_b), 4)
        beats, downs = _build_beat_grid(dur_b, float(b["bpm"]))
        write_json(bgm_dir / f"{sid}_bgm.json", {
            "style_id": sid,
            "bpm": float(b["bpm"]),
            "duration_sec": dur_b,
            "beat_times_sec": beats,
            "downbeat_times_sec": downs,
            "source": b["src"],
            "license": "CC0",
        })
        sfx_entry: Dict[str, str] = {}
        for role in cfg["sfx"]:
            raw_rel = f"sound_vibe/sfx/{sid}_{role}.wav"
            canonical_rel = SFX_DEDUP_ALIAS.get(raw_rel, raw_rel)
            if (ASSETS_DIR / canonical_rel).exists():
                sfx_entry[role] = canonical_rel
            elif (ASSETS_DIR / raw_rel).exists():
                sfx_entry[role] = raw_rel

        manifest["styles"][sid] = {
            "bgm_wav": _to_asset_rel(dst_b),
            "bpm": float(b["bpm"]),
            "sfx": sfx_entry,
            "sfx_min_gap_sec": cfg["sfx_min_gap_sec"],
            "sfx_gain_db": cfg["sfx_gain_db"],
            "bgm_base_db": cfg["bgm_base_db"],
            "duck_depth_db": cfg["duck_depth_db"],
        }

    write_json(out_dir / "vibe_sound_manifest.json", manifest)
    return manifest


def clean_all_vibe_assets(raw_dir: Path | None = None, out_dir: Path | None = None) -> Dict[str, Any]:
    """将 raw 目录中的 CC0 Freesound 录音清洗为 48kHz stereo 标准化 BGM 与 SFX，写出全相对路径清单。"""
    out_dir = out_dir or SOUND_VIBE_DIR
    raw_dir = raw_dir or (out_dir / "raw")
    if not raw_dir.exists():
        # 若原始下载目录已被瘦身清理，直接基于现有已清洗 WAV 重建相对路径 manifest 与节拍 JSON
        mf = rebuild_relative_manifest_and_beats(out_dir)
        print(f"[vibe_sound] raw 目录已瘦身，已直接刷新相对路径与节拍网格 -> {out_dir / 'vibe_sound_manifest.json'}")
        return mf

    ffmpeg = find_bin("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("需要 ffmpeg 执行声学清洗。")
    bgm_dir = out_dir / "bgm"
    sfx_dir = out_dir / "sfx"
    bgm_dir.mkdir(parents=True, exist_ok=True)
    sfx_dir.mkdir(parents=True, exist_ok=True)

    for sid, cfg in STYLE_SOUND_MAP.items():
        b = cfg["bgm"]
        src_b = raw_dir / b["src"]
        dst_b = bgm_dir / f"{sid}_bgm.m4a"
        dur_b = max(2.0, float(b["end"]) - float(b["start"]))
        fade_out_t = max(0.0, dur_b - 0.18)
        if src_b.exists():
            subprocess.run([
                ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-ss", f"{float(b['start']):.3f}", "-t", f"{dur_b:.3f}",
                "-i", str(src_b),
                "-af", f"afade=t=in:st=0:d=0.12,afade=t=out:st={fade_out_t:.3f}:d=0.18,loudnorm=I=-20:TP=-2.0:LRA=8",
                "-ar", "48000", "-ac", "2", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
                str(dst_b),
            ], check=True)
        for role, (fn, s0, s1, trim_gain_db) in cfg["sfx"].items():
            raw_rel = f"sound_vibe/sfx/{sid}_{role}.wav"
            if raw_rel in SFX_DEDUP_ALIAS:
                continue
            src_s = raw_dir / fn
            dst_s = sfx_dir / f"{sid}_{role}.wav"
            d_s = max(0.08, s1 - s0)
            f_out_d = min(0.06, d_s * 0.35)
            f_out_st = max(0.0, d_s - f_out_d)
            if src_s.exists():
                subprocess.run([
                    ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                    "-ss", f"{s0:.3f}", "-t", f"{d_s:.3f}",
                    "-i", str(src_s),
                    "-af", (
                        f"highpass=f=60,afade=t=in:st=0:d=0.005,afade=t=out:st={f_out_st:.3f}:d={f_out_d:.3f},"
                        f"loudnorm=I=-22:TP=-6.0:LRA=6,volume={trim_gain_db:.1f}dB"
                    ),
                    "-ar", "48000", "-ac", "2", "-acodec", "pcm_s16le",
                    str(dst_s),
                ], check=True)

    mf = rebuild_relative_manifest_and_beats(out_dir)
    print(f"[vibe_sound] 已生成 {len(mf['styles'])} 套相对路径 CC0 音库 -> {out_dir / 'vibe_sound_manifest.json'}")
    return mf


def get_style_sound_profile(style_id: str) -> Optional[Dict[str, Any]]:
    """
    获取任意 style_01 ~ style_24 对应的真实 CC0 音色包：
    1. 精确命中 STYLE_SOUND_MAP / manifest；
    2. 未单独建包者按其 archetype_id 自动映射至同流派真实 CC0 音色包；
    3. 全部路径基于当前主机 ASSETS_DIR 动态拼装，彻底杜绝绝对路径失效。
    """
    mf_path = SOUND_VIBE_DIR / "vibe_sound_manifest.json"
    if not mf_path.exists():
        return None
    mf = json.loads(mf_path.read_text(encoding="utf-8"))
    styles = mf.get("styles", {})
    target_sid = style_id
    if target_sid not in styles:
        entry = load_style_spectrum_entry(style_id)
        arch_id = entry.get("archetype_id") if entry else None
        fb_map = {**(mf.get("archetype_fallback") or {}), **ARCHETYPE_TO_VIBE_STYLE}
        if arch_id and arch_id in fb_map and fb_map[arch_id] in styles:
            target_sid = fb_map[arch_id]
        else:
            return None

    raw_prof = dict(styles[target_sid])
    if raw_prof.get("bgm_wav"):
        raw_prof["bgm_wav"] = _resolve_asset_path(raw_prof["bgm_wav"])
    resolved_sfx: Dict[str, str] = {}
    for role, sp in (raw_prof.get("sfx") or {}).items():
        resolved_sfx[role] = _resolve_asset_path(sp)
    raw_prof["sfx"] = resolved_sfx
    raw_prof["mapped_from_style_id"] = target_sid
    return raw_prof


def get_default_sound_profile(track: str = "store") -> Optional[Dict[str, Any]]:
    """当未指定 style_id 时按轨道返回默认 CC0 真录音库（门店轨 style_14 / 博主轨 style_12）。"""
    return get_style_sound_profile("style_14" if track == "store" else "style_12")


def main() -> None:
    maybe_reexec_in_venv()
    ap = argparse.ArgumentParser(description="Vibe Sound CC0 真实音效检索与清洗")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p_s = sp.add_parser("search")
    p_s.add_argument("query")
    p_s.add_argument("--license", default="cc0", choices=list(FS_LICENSE))
    p_s.add_argument("-n", type=int, default=8)
    sp.add_parser("clean")
    a = ap.parse_args()
    if a.cmd == "search":
        for r in search_freesound(a.query, license_mode=a.license, limit=a.n):
            print(f"{r['key']}\t{r['title']}\t{r['dur']}\t{r['stats']}\t{r['desc']}")
    elif a.cmd == "clean":
        clean_all_vibe_assets()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
[Step 7: 真实肤色矢量掩膜校色 + 切段中点测光 + 24 风格动态适配 + LUT 肤色回测闭环]
1. 按 EDL 实际切片区间 [source_in_sec, source_out_sec] 中点测光（不拿片头 3s 乱调第 20s 画面）。
2. 利用 Step 1 映射后的裁切人脸 ROI + BT.709 肤色像素掩膜剔除背景/眼镜/眉毛后测定真实 Cb/Cr。
3. 肤色矫正作用于中间调 Midtones (rm/bm)，彻底告别用暗部 rs/bs 调肤色；
   从 style_spectrum_library.json 动态派生全部 24 套风格参数。
4. 闭环回测：生成 blended LUT 后对 Hero 帧抽样复核套色后肤色是否偏移 common.SKIN_YCBCR_RANGE，若偏移则自动降强度重编。
输出：pipeline/07_color_plan.json (+ pipeline/07_blended_lut.cube)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from common import (
    SKIN_YCBCR_RANGE,
    find_bin,
    load_style_applied,
    load_style_spectrum_entry,
    maybe_reexec_in_venv,
    parse_manifest_faces,
    read_json,
    resolve_lut_path,
    run_cmd,
    write_cube_lut,
    write_json,
)

if __name__ == "__main__":
    maybe_reexec_in_venv()

import numpy as np


STYLE_GRADE_PROFILES: Dict[str, Dict[str, float]] = {
    "style_01": {"b_off": -0.026, "contrast": 1.15, "sat": 0.94, "rm_off": -0.018, "bm_off": 0.028},
    "style_02": {"b_off": -0.012, "contrast": 1.12, "sat": 1.04, "rm_off": 0.010, "bm_off": -0.008},
    "style_03": {"b_off": -0.028, "contrast": 1.14, "sat": 1.08, "rm_off": 0.022, "bm_off": -0.020},
    "style_04": {"b_off": 0.032, "contrast": 1.04, "sat": 0.88, "rm_off": -0.014, "bm_off": 0.018},
    "style_05": {"b_off": 0.024, "contrast": 1.04, "sat": 0.80, "rm_off": 0.018, "bm_off": -0.018},
    "style_06": {"b_off": -0.032, "contrast": 1.14, "sat": 0.84, "rm_off": 0.006, "bm_off": -0.004},
    "style_07": {"b_off": 0.008, "contrast": 1.08, "sat": 1.02, "rm_off": 0.014, "bm_off": -0.012},
    "style_08": {"b_off": 0.014, "contrast": 1.06, "sat": 1.02, "rm_off": 0.018, "bm_off": -0.016},
    "style_09": {"b_off": -0.035, "contrast": 1.16, "sat": 0.90, "rm_off": 0.004, "bm_off": 0.006},
    "style_10": {"b_off": 0.020, "contrast": 1.08, "sat": 0.94, "rm_off": -0.004, "bm_off": 0.006},
    "style_11": {"b_off": 0.026, "contrast": 1.06, "sat": 0.95, "rm_off": 0.006, "bm_off": -0.004},
    "style_12": {"b_off": 0.030, "contrast": 1.05, "sat": 0.90, "rm_off": -0.006, "bm_off": 0.010},
    "style_13": {"b_off": 0.018, "contrast": 1.06, "sat": 0.88, "rm_off": 0.010, "bm_off": -0.008},
    "style_14": {"b_off": 0.012, "contrast": 1.05, "sat": 1.06, "rm_off": 0.016, "bm_off": -0.014},
    "style_15": {"b_off": -0.014, "contrast": 1.12, "sat": 1.04, "rm_off": 0.016, "bm_off": -0.014},
    "style_16": {"b_off": -0.036, "contrast": 1.16, "sat": 0.92, "rm_off": 0.008, "bm_off": -0.004},
    "style_17": {"b_off": -0.006, "contrast": 1.12, "sat": 1.12, "rm_off": 0.026, "bm_off": -0.024},
    "style_18": {"b_off": 0.012, "contrast": 1.08, "sat": 0.94, "rm_off": 0.006, "bm_off": -0.004},
    "style_19": {"b_off": 0.006, "contrast": 1.10, "sat": 0.96, "rm_off": -0.014, "bm_off": 0.018},
    "style_20": {"b_off": -0.008, "contrast": 1.10, "sat": 1.14, "rm_off": 0.028, "bm_off": -0.026},
    "style_21": {"b_off": 0.010, "contrast": 1.09, "sat": 1.07, "rm_off": 0.018, "bm_off": -0.014},
    "style_22": {"b_off": 0.024, "contrast": 1.05, "sat": 0.94, "rm_off": -0.004, "bm_off": 0.008},
    "style_23": {"b_off": -0.020, "contrast": 1.12, "sat": 0.88, "rm_off": 0.008, "bm_off": 0.010},
    "style_24": {"b_off": -0.016, "contrast": 1.14, "sat": 1.08, "rm_off": 0.018, "bm_off": -0.016},
}


def _resolve_style_grade_profile(style_id: Optional[str]) -> Dict[str, float]:
    """覆盖全 24 套风格：先查调优表，否则从 style_spectrum_library.json 的 color_and_lut & archetype 动态派生。"""
    if not style_id:
        return {}
    if style_id in STYLE_GRADE_PROFILES:
        return STYLE_GRADE_PROFILES[style_id]
    entry = load_style_spectrum_entry(style_id)
    if not entry:
        return {}
    arch = str(entry.get("archetype_id", ""))
    cl = entry.get("color_and_lut", {}) or {}
    warm_raw = float(cl.get("warmth_index", cl.get("warm_cool_score", 0.0)))
    # analyze_style_spectrum 输出的 warmth_index 为 0..255 尺度 (常见 -30..+70)，归一化到 [-1, 1] 防止瞬间打满
    warm = max(-1.0, min(1.0, warm_raw / 60.0)) if abs(warm_raw) > 1.5 else max(-1.0, min(1.0, warm_raw))
    if arch == "arch_01_tech_ui_console":
        return {"b_off": -0.025, "contrast": 1.15, "sat": 0.94, "rm_off": -0.018, "bm_off": 0.028}
    if arch == "arch_02_high_contrast_story":
        return {"b_off": 0.0, "contrast": 1.12, "sat": 1.08, "rm_off": 0.020, "bm_off": -0.018}
    if arch == "arch_03_editorial_matte_depth":
        return {"b_off": 0.028, "contrast": 1.04, "sat": 0.90, "rm_off": -0.006, "bm_off": 0.010}
    if arch == "arch_05_cinema_slow_space":
        return {"b_off": -0.035, "contrast": 1.15, "sat": 0.84, "rm_off": -0.016, "bm_off": 0.026}
    if arch == "arch_06_paper_stopmotion":
        return {"b_off": 0.025, "contrast": 1.04, "sat": 0.80, "rm_off": 0.018, "bm_off": -0.018}
    # arch_04 默认暖人声高饱和口播
    return {
        "b_off": 0.010,
        "contrast": 1.07,
        "sat": 1.04,
        "rm_off": round(max(-0.025, min(0.025, warm * 0.02)), 3),
        "bm_off": round(max(-0.025, min(0.025, -warm * 0.02)), 3),
    }


def _escape_lut_filter_path(p: Path) -> str:
    return str(p.resolve()).replace("\\", "/").replace("'", "\\'").replace(":", "\\:")


def probe_clip_color_stats(
    media_path: Path,
    start_sec: float = 0.0,
    dur_sec: float = 3.0,
) -> Dict[str, float]:
    """针对 EDL 实际切片区间 [start_sec, start_sec + dur_sec] 的中点窗口抽样测光。"""
    ffmpeg = find_bin("ffmpeg")
    if not ffmpeg or not media_path.exists():
        return {"yavg": 125.0, "uavg": 128.0, "vavg": 128.0}
    c_dur = max(0.3, float(dur_sec))
    win_dur = min(4.0, c_dur)
    win_start = max(0.0, float(start_sec) + max(0.0, (c_dur - win_dur) * 0.5))
    cmd = [
        ffmpeg, "-v", "info",
        "-ss", f"{win_start:.3f}", "-t", f"{win_dur:.3f}",
        "-i", str(media_path),
        "-vf", "select='not(mod(n,12))',scale=in_color_matrix=bt709:out_color_matrix=bt709,format=yuv420p,signalstats,metadata=print",
        "-an", "-f", "null", "-",
    ]
    res = run_cmd(cmd, check=False)

    def avg_val(key: str, default: float = 128.0) -> float:
        vals = [float(m) for m in re.findall(rf"lavfi\.signalstats\.{key}=([0-9.]+)", res.stderr or "")]
        return round(sum(vals) / len(vals), 2) if vals else default

    return {
        "yavg": avg_val("YAVG", 125.0),
        "uavg": avg_val("UAVG", 128.0),
        "vavg": avg_val("VAVG", 128.0),
    }


def _compute_masked_skin_ycbcr_from_rgb(
    arr_rgb: np.ndarray,
    face_bbox: Dict[str, float],
) -> Optional[Dict[str, float]]:
    """使用 BT.709 矩阵 + 皮肤色度粗掩膜提取人脸真实肤色画素（剔除眼镜/眉毛/胡须/背景）。"""
    h_s, w_s, _ = arr_rgb.shape
    fx, fy, fw, fh = float(face_bbox["x"]), float(face_bbox["y"]), float(face_bbox["w"]), float(face_bbox["h"])
    if max(fx, fy, fw, fh) > 1.01:
        fx, fy, fw, fh = fx / 1080.0, fy / 1920.0, fw / 1080.0, fh / 1920.0
    x0 = max(0, int((fx + fw * 0.22) * w_s))
    x1 = min(w_s, max(x0 + 4, int((fx + fw * 0.78) * w_s)))
    y0 = max(0, int((fy + fh * 0.22) * h_s))
    y1 = min(h_s, max(y0 + 4, int((fy + fh * 0.76) * h_s)))
    roi = arr_rgb[y0:y1, x0:x1].astype(np.float32)
    if roi.size < 12:
        return None

    r, g, b = roi[:, :, 0], roi[:, :, 1], roi[:, :, 2]
    # BT.709 矩阵系数转换
    y_val = 16.0 + (0.2126 * r + 0.7152 * g + 0.0722 * b) * (219.0 / 255.0)
    cb = 128.0 + (-0.114572 * r - 0.385428 * g + 0.5 * b) * (224.0 / 255.0)
    cr = 128.0 + (0.5 * r - 0.454153 * g - 0.045847 * b) * (224.0 / 255.0)

    skin_mask = (cb >= 77.0) & (cb <= 136.0) & (cr >= 125.0) & (cr <= 178.0) & (y_val >= 35.0) & (y_val <= 235.0)
    if int(np.sum(skin_mask)) >= 8:
        return {
            "skin_y": round(float(np.median(y_val[skin_mask])), 1),
            "skin_cb": round(float(np.median(cb[skin_mask])), 1),
            "skin_cr": round(float(np.median(cr[skin_mask])), 1),
            "mask_ratio": round(float(np.mean(skin_mask)), 3),
        }
    return {
        "skin_y": round(float(np.median(y_val)), 1),
        "skin_cb": round(float(np.median(cb)), 1),
        "skin_cr": round(float(np.median(cr)), 1),
        "mask_ratio": 0.0,
    }


def probe_face_skin_ycbcr(
    media_path: Path,
    face_bbox: Dict[str, float],
    at_sec: float = 0.2,
    extra_vf: Optional[str] = None,
) -> Optional[Dict[str, float]]:
    ffmpeg = find_bin("ffmpeg")
    if not ffmpeg or not media_path.exists():
        return None
    w_s, h_s = 270, 480
    scale_bt709 = f"scale={w_s}:{h_s}:in_color_matrix=bt709:out_color_matrix=bt709,format=rgb24"
    vf_arg = f"{extra_vf},{scale_bt709}" if extra_vf else scale_bt709
    res = subprocess.run(
        [
            ffmpeg, "-hide_banner", "-loglevel", "error",
            "-ss", f"{max(0.0, at_sec):.2f}", "-i", str(media_path),
            "-frames:v", "1", "-vf", vf_arg,
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if len(res.stdout) < w_s * h_s * 3:
        return None
    arr = np.frombuffer(res.stdout[: w_s * h_s * 3], dtype=np.uint8).reshape((h_s, w_s, 3))
    return _compute_masked_skin_ycbcr_from_rgb(arr, face_bbox)


def compute_hero_and_shot_correction(
    stats: Dict[str, float],
    hero_stats: Dict[str, float],
    is_hero: bool,
    skin_ycbcr: Optional[Dict[str, float]],
    style_id: Optional[str] = None,
) -> Dict[str, Any]:
    """基于 Hero 锚定与中间调皮肤矢量保护计算校色参数（仅作用于 rm/bm 中间调，同时护航含人脸副镜头）。"""
    prof = _resolve_style_grade_profile(style_id)
    y, u, v = stats["yavg"], stats["uavg"], stats["vavg"]

    skin_bm, skin_rm = 0.0, 0.0
    if skin_ycbcr:
        cb, cr = skin_ycbcr["skin_cb"], skin_ycbcr["skin_cr"]
        if cb > SKIN_YCBCR_RANGE["cb_max"] - 6.0:
            skin_bm = -(cb - 118.0) / 360.0
        elif cb < SKIN_YCBCR_RANGE["cb_min"] + 6.0:
            skin_bm = (100.0 - cb) / 360.0
        if cr < SKIN_YCBCR_RANGE["cr_min"] + 6.0:
            skin_rm = (142.0 - cr) / 360.0
        elif cr > SKIN_YCBCR_RANGE["cr_max"] - 6.0:
            skin_rm = -(cr - 160.0) / 360.0

    if is_hero:
        y_corr = 0.0
        if y < 85.0:
            y_corr = (95.0 - y) / 480.0
        elif y > 175.0:
            y_corr = (165.0 - y) / 480.0
        brightness = round(max(-0.14, min(0.14, y_corr + float(prof.get("b_off", 0.0)))), 3)
        bm_shift = round(max(-0.08, min(0.08, skin_bm + float(prof.get("bm_off", 0.0)))), 3)
        rm_shift = round(max(-0.08, min(0.08, skin_rm + float(prof.get("rm_off", 0.0)))), 3)
    else:
        y_diff = hero_stats["yavg"] - y
        u_diff = hero_stats["uavg"] - u
        v_diff = hero_stats["vavg"] - v
        brightness = round(max(-0.12, min(0.12, (y_diff * 0.45) / 380.0 + float(prof.get("b_off", 0.0)))), 3)
        bm_base = (u_diff * 0.30) / 420.0
        rm_base = (v_diff * 0.30) / 420.0
        if skin_ycbcr:
            bm_base = bm_base * 0.5 + skin_bm * 0.7
            rm_base = rm_base * 0.5 + skin_rm * 0.7
        bm_shift = round(max(-0.07, min(0.07, bm_base + float(prof.get("bm_off", 0.0)))), 3)
        rm_shift = round(max(-0.07, min(0.07, rm_base + float(prof.get("rm_off", 0.0)))), 3)

    return {
        "brightness": brightness,
        "contrast": round(float(prof.get("contrast", 1.05)), 3),
        "saturation": round(float(prof.get("sat", 1.04)), 3),
        "rm": rm_shift,
        "bm": bm_shift,
    }


def build_blended_cube_lut(lut_path: Path, strength: float, out_path: Path) -> tuple[Path, float]:
    """将源 3D .cube LUT 与恒等映射线性混合；通过 common.write_cube_lut 写出并如实返回有效强度。"""
    strength = max(0.0, min(1.0, strength))
    if strength >= 0.99 or not lut_path.exists():
        return lut_path, 1.0 if lut_path.exists() else 0.0

    lines = lut_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    size = 33
    triplets: List[List[float]] = []
    title = f"Blended_{lut_path.stem}_{int(round(strength*100))}pct"

    for ln in lines:
        s = ln.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("LUT_3D_SIZE"):
            size = int(s.split()[1])
            continue
        if s.startswith(("TITLE", "DOMAIN_MIN", "DOMAIN_MAX")):
            continue
        parts = s.split()
        if len(parts) == 3:
            try:
                triplets.append([float(parts[0]), float(parts[1]), float(parts[2])])
            except ValueError:
                continue

    if len(triplets) != size ** 3:
        return lut_path, 1.0

    lut_arr = np.array(triplets, dtype=np.float32)
    grid = np.linspace(0.0, 1.0, size, dtype=np.float32)
    bb, gg, rr = np.meshgrid(grid, grid, grid, indexing="ij")
    identity = np.stack([rr, gg, bb], axis=-1).reshape(-1, 3)

    blended = np.clip(identity * (1.0 - strength) + lut_arr * strength, 0.0, 1.0)
    write_cube_lut(out_path, blended, size, title)
    return out_path, strength


def _build_vf_for_corr(corr: Dict[str, Any], lut_path: Optional[Path], lut_strength: float = 1.0) -> str:
    base = (
        f"eq=brightness={corr['brightness']}:contrast={corr['contrast']}:saturation={corr['saturation']},"
        f"colorbalance=rm={corr['rm']}:bm={corr['bm']}"
    )
    if float(lut_strength) <= 0.01 or lut_path is None or not Path(lut_path).is_file():
        return base
    lut_escaped = _escape_lut_filter_path(Path(lut_path))
    return (
        f"{base},"
        f"scale=in_color_matrix=bt709:out_color_matrix=bt709,format=rgb24,"
        f"lut3d='{lut_escaped}',"
        f"scale=in_color_matrix=bt709:out_color_matrix=bt709,format=yuv420p"
    )


def run_step7(
    pipeline_dir: Path,
    track: str = "store",
    lut_name: Optional[str] = None,
    style_id: Optional[str] = None,
    lut_strength: Optional[float] = None,
) -> Dict[str, Any]:
    edl = read_json(pipeline_dir / "04_edl.json")
    manifest = read_json(pipeline_dir / "01_manifest.json") if (pipeline_dir / "01_manifest.json").exists() else {"items": []}

    if not style_id:
        style_id = edl.get("style_id") or load_style_applied(pipeline_dir)
    if not lut_name:
        lut_name = f"{style_id}.cube" if style_id else ("warm_store.cube" if track == "store" else "clean_creator.cube")
    lut_path = resolve_lut_path(lut_name, style_id=style_id)

    style_entry = load_style_spectrum_entry(style_id) if style_id else None
    if lut_strength is None:
        cfg_str = (style_entry or {}).get("color_and_lut", {}).get("lut_strength")
        if cfg_str is not None:
            lut_strength = max(0.0, min(1.0, float(cfg_str)))
        else:
            lut_strength = 0.72 if style_id in ("style_06", "style_08", "style_13") else 0.60

    blended_out_path = pipeline_dir / "07_blended_lut.cube"
    blended_lut, eff_strength = build_blended_cube_lut(lut_path, lut_strength, blended_out_path)

    manifest_by_mp4 = {it.get("normalized_mp4"): it for it in manifest.get("items", [])}
    clip_stats_cache: Dict[str, Dict[str, float]] = {}
    clip_skin_cache: Dict[str, Optional[Dict[str, float]]] = {}

    def _get_clip_stats(mp_s: str, s_in: float, s_dur: float) -> Dict[str, float]:
        ck = f"{mp_s}@{s_in:.2f}@{s_dur:.2f}"
        if ck not in clip_stats_cache:
            clip_stats_cache[ck] = probe_clip_color_stats(Path(mp_s), s_in, s_dur)
        return clip_stats_cache[ck]

    def _get_clip_skin(mp_s: str, fb_dict: Dict[str, float], at_s: float) -> Optional[Dict[str, float]]:
        sk = f"{mp_s}@{at_s:.2f}"
        if sk not in clip_skin_cache:
            clip_skin_cache[sk] = probe_face_skin_ycbcr(Path(mp_s), fb_dict, at_sec=at_s)
        return clip_skin_cache[sk]

    hero_clip = next((c for c in edl["clips"] if c["track_role"] == "a_roll"), None)
    if not hero_clip:
        hero_clip = next(
            (
                c for c in edl["clips"]
                if c["track_role"] != "code_broll"
                and not (manifest_by_mp4.get(c.get("media_path")) or {}).get("source_is_code_scene")
            ),
            None,
        )

    hero_mp = hero_clip["media_path"] if hero_clip else ""
    hero_in = float(hero_clip.get("source_in_sec", 0.0)) if hero_clip else 0.0
    hero_dur = float(hero_clip.get("duration_sec", 2.0)) if hero_clip else 2.0
    hero_stats = _get_clip_stats(hero_mp, hero_in, hero_dur) if hero_mp else {"yavg": 125.0, "uavg": 128.0, "vavg": 128.0}

    skin_ycbcr: Optional[Dict[str, float]] = None
    hero_face_bbox: Optional[Dict[str, float]] = None
    hero_at_sec = round(hero_in + min(1.5, hero_dur * 0.5), 2)
    if hero_mp and hero_mp in manifest_by_mp4:
        faces_px = parse_manifest_faces(manifest_by_mp4[hero_mp])
        if faces_px:
            hero_face_bbox = faces_px[0]
            skin_ycbcr = _get_clip_skin(hero_mp, hero_face_bbox, hero_at_sec)

    # 收集所有含人脸镜头的抽样检验点（不仅 Hero 1 帧，副镜头人脸一并纳入 LUT 肤色保护回测）
    face_verify_targets: List[Tuple[Path, Dict[str, float], float, Dict[str, float], bool]] = []
    if hero_mp and hero_face_bbox and skin_ycbcr:
        face_verify_targets.append((Path(hero_mp), hero_face_bbox, hero_at_sec, hero_stats, True))
    seen_verify_mps = {hero_mp}
    for c_tmp in edl["clips"]:
        mp_t = str(c_tmp.get("media_path") or "")
        if not mp_t or mp_t in seen_verify_mps or mp_t not in manifest_by_mp4:
            continue
        f_list = parse_manifest_faces(manifest_by_mp4[mp_t])
        if not f_list:
            continue
        seen_verify_mps.add(mp_t)
        c_in_t = float(c_tmp.get("source_in_sec", 0.0))
        c_dur_t = float(c_tmp.get("duration_sec", 2.0))
        at_t = round(c_in_t + min(1.5, c_dur_t * 0.5), 2)
        st_t = _get_clip_stats(mp_t, c_in_t, c_dur_t)
        face_verify_targets.append((Path(mp_t), f_list[0], at_t, st_t, False))
        if len(face_verify_targets) >= 4:
            break

    # 闭环 LUT 肤色保护验证：套用建议滤镜回测 Hero 及副镜头人脸肤色是否跌出健康扇区，仅沿严格不增强度阶梯下探
    skin_post_grade: Optional[Dict[str, float]] = None
    if face_verify_targets and eff_strength > 0.01:
        raw_cands = [eff_strength, min(eff_strength, 0.45), min(eff_strength, 0.30), 0.15]
        cand_strengths: List[float] = []
        for cs in raw_cands:
            cs_r = round(float(cs), 2)
            if cs_r <= eff_strength + 1e-6 and cs_r not in cand_strengths:
                cand_strengths.append(cs_r)
        min_cand = min(cand_strengths) if cand_strengths else 0.15
        for cand_str in cand_strengths:
            if abs(cand_str - eff_strength) < 1e-6 and blended_lut.is_file():
                cand_lut, cand_eff = blended_lut, eff_strength
            else:
                cand_lut, cand_eff = build_blended_cube_lut(lut_path, cand_str, blended_out_path)
            blended_lut, eff_strength = cand_lut, cand_eff
            all_in_sector = True
            for vp, v_fb, v_at, v_st, v_is_hero in face_verify_targets:
                v_skin = skin_ycbcr if v_is_hero else _get_clip_skin(str(vp), v_fb, v_at)
                v_corr = compute_hero_and_shot_correction(v_st, hero_stats, v_is_hero, v_skin, style_id=style_id)
                test_vf = _build_vf_for_corr(v_corr, cand_lut, lut_strength=cand_eff)
                pg = probe_face_skin_ycbcr(vp, v_fb, at_sec=v_at, extra_vf=test_vf)
                if v_is_hero:
                    skin_post_grade = pg
                if pg and not (
                    SKIN_YCBCR_RANGE["cb_min"] <= pg["skin_cb"] <= SKIN_YCBCR_RANGE["cb_max"]
                    and SKIN_YCBCR_RANGE["cr_min"] <= pg["skin_cr"] <= SKIN_YCBCR_RANGE["cr_max"]
                ):
                    all_in_sector = False
                    break
            if all_in_sector or cand_str <= min_cand:
                break

    clip_plans: List[Dict[str, Any]] = []

    for clip in edl["clips"]:
        mp = clip["media_path"]
        is_code = (clip["track_role"] == "code_broll") or bool((manifest_by_mp4.get(mp) or {}).get("source_is_code_scene"))
        if is_code:
            clip_plans.append({
                "clip_id": clip["clip_id"],
                "track_role": clip["track_role"],
                "apply_color_grade": False,
                "reason": "代码生成UI图表保留原色",
                "vf_filter": None,
            })
            continue

        c_in = float(clip.get("source_in_sec", 0.0))
        c_dur = float(clip.get("duration_sec", 2.0))
        stats = _get_clip_stats(mp, c_in, c_dur)
        is_hero = (mp == hero_mp and abs(c_in - hero_in) < 0.5)

        shot_skin: Optional[Dict[str, float]] = skin_ycbcr if is_hero else None
        if not is_hero and mp in manifest_by_mp4:
            clip_faces = parse_manifest_faces(manifest_by_mp4[mp])
            if clip_faces:
                c_at = round(c_in + min(1.5, c_dur * 0.5), 2)
                shot_skin = _get_clip_skin(mp, clip_faces[0], c_at)

        corr = compute_hero_and_shot_correction(
            stats,
            hero_stats=hero_stats,
            is_hero=is_hero,
            skin_ycbcr=shot_skin,
            style_id=style_id,
        )
        vf_str = _build_vf_for_corr(corr, blended_lut, lut_strength=eff_strength)
        clip_plans.append({
            "clip_id": clip["clip_id"],
            "track_role": clip["track_role"],
            "is_hero_ref": is_hero,
            "apply_color_grade": True,
            "measured_stats": stats,
            "base_correction": corr,
            "lut_file": str(blended_lut.resolve()) if eff_strength > 0.01 else None,
            "vf_filter": vf_str,
        })

    plan = {
        "step": "07_color_grade",
        "style_id": style_id,
        "lut_name": lut_path.name,
        "source_lut_path": str(lut_path.resolve()),
        "lut_strength": round(eff_strength, 2),
        "lut_path": str(blended_lut.resolve()),
        "hero_media": hero_mp,
        "hero_stats": hero_stats,
        "skin_tone_measured": skin_ycbcr,
        "skin_tone_post_grade": skin_post_grade,
        "clip_plans": clip_plans,
    }
    write_json(pipeline_dir / "07_color_plan.json", plan)
    graded_cnt = sum(1 for c in clip_plans if c["apply_color_grade"])
    print(
        f"[step7] 肤色保护调色方案生成完成：{graded_cnt} 个实拍镜头（Hero锚定 + 强度{eff_strength:.0%}混合 `{lut_path.name}`）-> 07_color_plan.json"
    )
    return plan


def main() -> None:
    maybe_reexec_in_venv()
    parser = argparse.ArgumentParser(description="Step 7: 肤色保护基准校色与可控强度 LUT 规划")
    parser.add_argument("--pipeline-dir", required=True)
    parser.add_argument("--track", choices=["store", "creator"], default="store")
    parser.add_argument("--style-id", help="绑定风格谱 ID")
    parser.add_argument("--lut", help="LUT 文件名")
    parser.add_argument("--lut-strength", type=float, default=None, help="LUT 混合强度 0.0~1.0")
    args = parser.parse_args()
    run_step7(
        Path(args.pipeline_dir),
        track=args.track,
        lut_name=args.lut,
        style_id=args.style_id,
        lut_strength=args.lut_strength,
    )


if __name__ == "__main__":
    main()

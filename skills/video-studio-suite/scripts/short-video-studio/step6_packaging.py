#!/usr/bin/env python3
"""
[Step 6: 包装对齐与预算控制]
1. 修复限幅符号写反 Bug：采用上限 min(-3.0, ...) 确保真实流派音量梯度生效，06_packaging.json 与 WAV 实感完全一致。
2. Freesound CC0 真实物理材质音效排在数学合成兜底之前，同族轮换防疲劳。
3. 视觉包装严格遵守预算上限 max(3, ceil(duration_sec / 3.5))，并写入 style_id 与基于 01_manifest 裁切人脸的权威避脸 final_bbox。
输出：pipeline/06_packaging.json 与 pipeline/06_sfx_track.wav
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from common import (
    ASSETS_DIR,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    DEFAULT_FPS,
    SAFE_ZONE,
    SUBTITLE_CENTER_X,
    SUBTITLE_SYMMETRIC_MAX_W,
    bbox_iou,
    check_bbox_in_safe_zone,
    contrast_ratio,
    estimate_read_hold_sec,
    find_commercial_font,
    fit_text_line,
    frames_to_sec,
    hex_to_rgba,
    load_animation_sfx_pairs,
    load_sfx_intent_taxonomy,
    load_style_applied,
    load_style_spectrum_entry,
    maybe_reexec_in_venv,
    parse_manifest_faces,
    read_json,
    write_json,
)

if __name__ == "__main__":
    maybe_reexec_in_venv()

import numpy as np
from step3_lock_audio import SR, load_stereo_wav_np, save_stereo_wav_np


def _default_cc0_sfx(role: str) -> Path:
    """全仓统一 CC0 真录物理音效兜底（彻底淘汰正弦波合成电子音）。"""
    vibe_sfx = ASSETS_DIR / "sound_vibe" / "sfx"
    role_map = {
        "transition": vibe_sfx / "style_14_transition.wav",
        "accent": vibe_sfx / "style_14_accent.wav",
        "ui": vibe_sfx / "style_14_ui.wav",
        "receipt": vibe_sfx / "style_15_receipt.wav",
    }
    cand = role_map.get(role, vibe_sfx / "style_14_ui.wav")
    if cand.is_file():
        return cand
    any_wav = next(iter(sorted(vibe_sfx.glob("*.wav"))), None) if vibe_sfx.is_dir() else None
    return any_wav or cand


def rotate_sfx(candidates: List[Path], last_used_name: Optional[str]) -> Path:
    """同族/候选音效自动轮换，避免连续两次重复同一音色引起听觉疲劳。"""
    valid = [p for p in candidates if p and p.is_file()]
    if not valid:
        return _default_cc0_sfx("ui")
    if len(valid) == 1 or not last_used_name:
        return valid[0]
    for p in valid:
        if p.name != last_used_name:
            return p
    return valid[0]


def _enhance_sfx_presence(arr: np.ndarray, sr: int = SR) -> np.ndarray:
    """保持 CC0 原生频谱波形不变，对 2–8kHz 过闷暖调 SFX 施加温和广播级自身带通临场补偿。"""
    if len(arr) < 128:
        return arr
    try:
        from scipy import signal as sp_sig
        mono = arr.mean(axis=1).astype(np.float64)
        full_rms = float(np.sqrt(np.mean(mono ** 2) + 1e-12))
        sos = sp_sig.butter(4, [2000.0, 8000.0], btype="bandpass", fs=float(sr), output="sos")
        hf_mono = sp_sig.sosfiltfilt(sos, mono)
        hf_rms = float(np.sqrt(np.mean(hf_mono ** 2) + 1e-12))
        hf_ratio = hf_rms / max(1e-5, full_rms)
        if hf_ratio >= 0.28 or hf_rms < 1e-5:
            return arr
        # 仅按比例混合原 SFX 自身的 2–8kHz 分量，使其清晰度达到 hf_ratio≈0.35（绝不混入人工噪波）
        target_hf = max(hf_rms, full_rms * 0.35)
        alpha = min(6.0, max(0.0, (target_hf - hf_rms) / hf_rms))
        out = arr.astype(np.float64).copy()
        out[:, 0] += alpha * sp_sig.sosfiltfilt(sos, out[:, 0])
        out[:, 1] += alpha * sp_sig.sosfiltfilt(sos, out[:, 1])
        pk = float(np.max(np.abs(out)))
        if pk > 0.85:
            out *= (0.85 / pk)
        return out.astype(np.float32)
    except Exception:
        return arr


def _measure_sfx_peak_offset_sec(arr: np.ndarray, sr: int = SR) -> float:
    if len(arr) < 128:
        return 0.0
    mono = np.abs(arr.mean(axis=1))
    win = max(1, int(0.020 * sr))
    env = np.convolve(mono, np.ones(win, dtype=np.float32) / win, mode="same")
    peak_idx = int(np.argmax(env))
    return round(peak_idx / float(sr), 4)


def _avoid_faces_for_pkg(bbox: Dict[str, int], faces_px: List[Dict[str, Any]]) -> Dict[str, int]:
    """在 Step 6 源头一次性将花字胶囊避开裁切后人脸五官，保持安全区且不侵入字幕带。"""
    cand = dict(bbox)
    if not faces_px:
        return cand
    cur_iou = max(bbox_iou(cand, fb) for fb in faces_px)
    if cur_iou <= 0.01:
        return cand
    best = cand
    best_iou = cur_iou
    for try_y in (176, 224, 280, 340, 460, 820, 920, 1020):
        if try_y + cand["h"] > 1165:
            continue
        alt = {"x": cand["x"], "y": int(try_y), "w": cand["w"], "h": cand["h"]}
        ok, _ = check_bbox_in_safe_zone(alt)
        if not ok:
            continue
        iou_v = max(bbox_iou(alt, fb) for fb in faces_px)
        if iou_v <= 0.01:
            return alt
        if iou_v < best_iou:
            best_iou = iou_v
            best = alt
    return best


def _measure_pkg_badge_width(text: str, font_path: Optional[str], max_pkg_w: int, target_fs: int = 40, min_w: int = 240) -> int:
    try:
        from PIL import Image, ImageDraw
        draw = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        fnt, _ = fit_text_line(draw, text, font_path, max_width=max_pkg_w - 64, max_size=target_fs, min_size=24)
        if fnt is not None:
            bb = draw.textbbox((0, 0), text, font=fnt)
            return int(min(max_pkg_w, max(min_w, (bb[2] - bb[0]) + 72)))
    except Exception:
        pass
    return int(min(max_pkg_w, max(min_w, len(text) * target_fs + 68)))


def run_step6(
    pipeline_dir: Path,
    fps: int = DEFAULT_FPS,
    style_id: str | None = None,
) -> Dict[str, Any]:
    audio_events = read_json(pipeline_dir / "03_audio_events.json")
    edl = read_json(pipeline_dir / "04_edl.json")
    man_p = pipeline_dir / "01_manifest.json"
    manifest = read_json(man_p) if man_p.exists() else {"items": []}

    faces_by_mp4: Dict[str, List[Dict[str, int]]] = {}
    for it in manifest.get("items", []):
        mp = str(it.get("normalized_mp4", ""))
        fl = parse_manifest_faces(it)
        if mp and fl:
            faces_by_mp4[mp] = fl

    if not style_id:
        style_id = edl.get("style_id") or load_style_applied(pipeline_dir)
    style_id = str(style_id or "style_14")

    vibe_prof = None
    try:
        from vibe_sound import get_style_sound_profile
        vibe_prof = get_style_sound_profile(style_id)
    except Exception:
        vibe_prof = None

    style_entry_pre = load_style_spectrum_entry(style_id) or {}
    broll_target = float(style_entry_pre.get("broll_overlay_ratio_target", 0.5))
    sfx_per_min_tgt = float((style_entry_pre.get("audio_and_sfx") or {}).get("sfx_per_min_target") or 24.0)
    total_dur = float(audio_events["locked_duration_sec"])
    total_samples = int(round(total_dur * SR))
    max_visual_budget = max(2, math.ceil(total_dur / 5.5)) if broll_target >= 0.85 else max(3, math.ceil(total_dur / 3.5))
    dyn_sfx_budget = max(5, int(math.ceil(total_dur * max(15.0, min(48.0, sfx_per_min_tgt)) / 60.0)))
    max_sfx_budget = max(8, dyn_sfx_budget) if style_id == "style_06" else dyn_sfx_budget

    sentences_map = {s["id"]: s for s in audio_events["sentences"]}
    events = audio_events["events"]
    code_ranges = [
        (int(c["timeline_in_frame"]), int(c["timeline_out_frame"]))
        for c in edl.get("clips", [])
        if c.get("track_role") == "code_broll"
    ]

    def overlaps_code(sf_f: int, ef_f: int) -> bool:
        return any(sf_f < ce and ef_f > cs for cs, ce in code_ranges)

    sfx_cues: List[Dict[str, Any]] = []
    dyn_gap_sec = max(1.5, min(4.8, (60.0 / max(12.0, sfx_per_min_tgt)) * 0.68))
    if vibe_prof and vibe_prof.get("sfx"):
        v_sfx = {k: Path(v) for k, v in vibe_prof["sfx"].items() if Path(v).exists()}
        # 尊重流派真实 sfx_gain_db（仅允许上限到 -3.5dB，避免风格全被拉爆成统一响度）
        base_gain_db = max(-14.0, min(-3.5, float(vibe_prof.get("sfx_gain_db", -9.5)) + 3.0))
        prof_gap = float(vibe_prof.get("sfx_min_gap_sec", dyn_gap_sec))
        min_sfx_gap = int(min(prof_gap, dyn_gap_sec) * fps)
    else:
        v_sfx = {}
        base_gain_db = -8.5
        min_sfx_gap = int(dyn_gap_sec * fps)

    sfx_files = {
        "hook": v_sfx.get("accent") or _default_cc0_sfx("accent"),
        "info": v_sfx.get("ui") or v_sfx.get("accent") or _default_cc0_sfx("ui"),
        "twist": v_sfx.get("accent") or _default_cc0_sfx("accent"),
        "detail": v_sfx.get("ui") or _default_cc0_sfx("ui"),
        "persona": v_sfx.get("ui") or v_sfx.get("transition") or _default_cc0_sfx("ui"),
        "cta": v_sfx.get("receipt") or v_sfx.get("ui") or _default_cc0_sfx("ui"),
        "cut": v_sfx.get("transition") or _default_cc0_sfx("transition"),
    }

    # 接入动画×音效字典与叙事意图分类表
    anim_sfx_dict = load_animation_sfx_pairs()
    sfx_taxonomy = load_sfx_intent_taxonomy()
    emotion_routing = sfx_taxonomy.get("pipeline_emotion_routing") or {}
    for emo_key, rel_list in emotion_routing.items():
        if emo_key not in sfx_files or not rel_list:
            continue
        for rel_p in rel_list:
            cand_p = ASSETS_DIR / rel_p
            if cand_p.is_file():
                # 保护流派专属 receipt 收尾音效不被泛用 cta 覆盖；仅填充尚未显式设定的角色
                if emo_key in ("persona", "twist") or (emo_key == "cta" and "receipt" not in v_sfx):
                    sfx_files[emo_key] = cand_p
                break

    used_frames: List[int] = []
    last_sfx_name: Optional[str] = None

    def can_place_sfx(frame: int) -> bool:
        return len(sfx_cues) < max_sfx_budget and all(abs(frame - f) >= min_sfx_gap for f in used_frames)

    # 100% 使用 Freesound CC0 真实物理材质 SFX（彻底剔除塑料电子合成音）
    for clip in edl["clips"][1:]:
        role = clip.get("track_role", "b_roll")
        ev_frame = int(clip.get("timeline_in_frame", clip["cut_event_frame"])) if role == "code_broll" else int(clip["cut_event_frame"])
        is_end_receipt = (clip is edl["clips"][-1]) and ("receipt" in v_sfx)
        if role != "code_broll" and not is_end_receipt:
            continue
        if not can_place_sfx(ev_frame):
            continue
        cand_list = [v_sfx["receipt"]] if is_end_receipt else [
            sfx_files["info"],
            sfx_files["cut"],
            sfx_files["hook"],
        ]
        sf = rotate_sfx(cand_list, last_sfx_name)
        last_sfx_name = sf.name
        cue_gain = round(max(-14.0, min(-3.5, base_gain_db + 1.5)), 1)
        sfx_cues.append({
            "id": f"sfx_{len(sfx_cues)+1:03d}",
            "file": str(sf.resolve()),
            "sfx_name": sf.name,
            "time_sec": frames_to_sec(ev_frame, fps),
            "frame": ev_frame,
            "gain_db": cue_gain,
            "event_id": clip["cut_event_id"],
            "reason": f"{style_id} 账单小票收尾提示" if is_end_receipt else f"{style_id} 信息卡片物理提示",
        })
        used_frames.append(ev_frame)

    # 100% CC0 真实物理录音轮换池
    cut_palette = [
        sfx_files["cut"],
        sfx_files["info"],
        sfx_files["hook"],
        _default_cc0_sfx("transition"),
        _default_cc0_sfx("ui"),
    ]
    cut_rot = 0
    # 优先选在句首/停顿缝隙切点安放 SFX，确保听感清爽且避免被重读浊音完全掩蔽，第二遍再补足其余切点
    prioritized_clips = [
        c for c in edl["clips"][1:]
        if str(c.get("cut_event_type", "")) in ("sentence_start", "pause_start", "pause_end", "bgm_downbeat")
    ] + [
        c for c in edl["clips"][1:]
        if str(c.get("cut_event_type", "")) not in ("sentence_start", "pause_start", "pause_end", "bgm_downbeat")
    ]
    for clip in prioritized_clips:
        ev_frame = int(clip["cut_event_frame"])
        if not can_place_sfx(ev_frame):
            continue
        rotated_pool = cut_palette[cut_rot % len(cut_palette):] + cut_palette[:cut_rot % len(cut_palette)]
        sf = rotate_sfx(rotated_pool, last_sfx_name)
        last_sfx_name = sf.name
        cut_rot += 1
        cue_gain = round(max(-14.0, min(-4.0, base_gain_db + 0.5)), 1)
        sfx_cues.append({
            "id": f"sfx_{len(sfx_cues)+1:03d}",
            "file": str(sf.resolve()),
            "sfx_name": sf.name,
            "time_sec": frames_to_sec(ev_frame, fps),
            "frame": ev_frame,
            "gain_db": cue_gain,
            "event_id": clip["cut_event_id"],
            "reason": f"{style_id} 流派物理材质转场",
        })
        used_frames.append(ev_frame)

    for ev in events:
        if ev["type"] == "sentence_start" and can_place_sfx(ev["frame"]):
            sent = sentences_map.get(ev.get("sentence_id", ""), {})
            emo = sent.get("emotion_or_info", "info")
            if emo not in ("hook", "twist", "persona", "cta"):
                continue
            sf = rotate_sfx([sfx_files.get(emo, sfx_files["info"]), sfx_files["cut"]], last_sfx_name)
            last_sfx_name = sf.name
            cue_gain = round(max(-15.0, min(-4.5, base_gain_db - 1.2)), 1)
            sfx_cues.append({
                "id": f"sfx_{len(sfx_cues)+1:03d}",
                "file": str(sf.resolve()),
                "sfx_name": sf.name,
                "time_sec": ev["time_sec"],
                "frame": ev["frame"],
                "gain_db": cue_gain,
                "event_id": ev["id"],
                "reason": f"{emo} 句首节点轻量提示",
            })
            used_frames.append(ev["frame"])

    sfx_cues.sort(key=lambda x: x["frame"])
    for idx_cue, cue in enumerate(sfx_cues, start=1):
        cue["id"] = f"sfx_{idx_cue:03d}"

    sfx_track = np.zeros((total_samples, 2), dtype=np.float32)
    sfx_cache: Dict[str, np.ndarray] = {}
    for cue in sfx_cues:
        fp = cue["file"]
        if fp not in sfx_cache:
            arr, _ = load_stereo_wav_np(Path(fp))
            m_abs = np.abs(arr.mean(axis=1))
            active_m = m_abs[m_abs >= max(1e-4, float(np.max(m_abs)) * 0.15)]
            core_rms = float(np.sqrt(np.mean(active_m ** 2) + 1e-10)) if len(active_m) > 0 else 0.01
            # 保持原生 CC0 物理频谱不注水：仅做温和活性核心增益归一化与防削波峰值钳位
            norm_gain = min(10.0, 0.25 / max(1e-4, core_rms))
            peak_cap = 0.85 / max(1e-4, float(np.max(np.abs(arr))))
            arr = (arr * min(norm_gain, peak_cap)).astype(np.float32)
            arr = _enhance_sfx_presence(arr, SR)
            sfx_cache[fp] = arr
        arr = sfx_cache[fp]
        peak_off = _measure_sfx_peak_offset_sec(arr, SR)
        # 峰值对齐切点：提前 peak_off 起播，使听觉峰值精准落在切点 time_sec
        onset_sec = max(0.0, float(cue["time_sec"]) - peak_off)
        cue["onset_time_sec"] = round(onset_sec, 4)
        cue["peak_time_sec"] = round(onset_sec + peak_off, 4)
        gain = 10.0 ** (min(-3.0, float(cue["gain_db"])) / 20.0)
        start_idx = max(0, int(round(onset_sec * SR)))
        end_idx = min(total_samples, start_idx + len(arr))
        if end_idx > start_idx:
            sfx_track[start_idx:end_idx] += arr[: end_idx - start_idx] * gain

    sfx_wav_path = pipeline_dir / "06_sfx_track.wav"
    save_stereo_wav_np(sfx_wav_path, sfx_track, SR)

    pkg_font_path = find_commercial_font()
    style_entry = load_style_spectrum_entry(style_id) or {}
    flower_spec = style_entry.get("multi_zone_flower_spec") or (style_entry.get("transition_and_packaging") or {}).get("multi_zone_flower_spec") or {}
    pkg_tech = style_entry.get("packaging_techniques") or {}
    is_borderless_flower = bool(flower_spec.get("borderless", False))
    use_top_bar = bool(pkg_tech.get("persistent_top_bar") or flower_spec.get("persistent_top_bar"))
    use_quote_card = bool(pkg_tech.get("quote_citation_card") or flower_spec.get("quote_citation_card"))

    anim_lookup = anim_sfx_dict.get("animation_lookup") or {}
    anim_cn_alias = {
        "hard_cut": "干脆切换",
        "smooth_pop_or_fade": "轻快渐显",
        "渐显": "渐显",
        "渐隐": "渐隐",
        "水墨晕开": "晕开",
        "弹幕滚动": "向右集合",
        "日出": "随机上升",
        "向下滑动": "向下露出",
        "向右露出": "向右缓入",
    }
    raw_anim_str = str((style_entry.get("subtitle_spec") or {}).get("measured_animation_raw") or "in:渐显")
    raw_anim_tokens = [
        p.replace("in:", "").replace("loop:", "").replace("out:", "").strip()
        for p in raw_anim_str.split("/")
        if p.strip()
    ] or ["渐显"]
    default_jy_anim = ""
    matched_pair = None
    for tok in raw_anim_tokens:
        mapped = anim_cn_alias.get(tok, tok)
        if tok in anim_lookup:
            default_jy_anim = tok
            matched_pair = anim_lookup[tok]
            break
        if mapped in anim_lookup:
            default_jy_anim = mapped
            matched_pair = anim_lookup[mapped]
            break
    if not default_jy_anim:
        first_tok = raw_anim_tokens[0]
        default_jy_anim = anim_cn_alias.get(first_tok, "渐显" if first_tok.isascii() else first_tok)
    if matched_pair is None:
        matched_pair = next(iter(anim_lookup.values()), {
            "jianying_anim_name": "渐显",
            "anim_duration_ms": 400,
            "jianying_sfx_name": "“呼”的转场音效",
        })

    def _safe_readable_fg(cand_hex: Optional[str], fallback_hex: str = "#FFE28A") -> str:
        c_str = str(cand_hex or fallback_hex)
        rgb = hex_to_rgba(c_str, 255)[:3]
        # 防止暗红/深色直接用于深底或花字时低于 4.5:1 无障碍对比度
        if contrast_ratio(rgb, (16, 20, 28)) < 4.5:
            return fallback_hex
        return c_str

    visual_elements: List[Dict[str, Any]] = []
    giant_spec = style_entry.get("giant_text_spec") or {}
    giant_mode = str(giant_spec.get("mode") or "giant_smash_single")
    giant_fs = int(giant_spec.get("font_size_px") or 140)
    giant_tag = str(giant_spec.get("tag_label") or "核心重点")
    giant_fg = _safe_readable_fg(giant_spec.get("fg_hex") or flower_spec.get("center_burst_color"), "#FFE28A")
    giant_accent = _safe_readable_fg(giant_spec.get("accent_hex") or flower_spec.get("flank_color"), "#FFF589")
    giant_stroke = str(giant_spec.get("stroke_hex") or flower_spec.get("stroke_color") or "#000000")
    giant_count_target = int(pkg_tech.get("giant_impact_count") or 2)
    use_multi_tag = bool(pkg_tech.get("multi_tag_burst") or flower_spec.get("multi_tag_burst"))

    first_sent = audio_events["sentences"][0] if audio_events["sentences"] else {"text": "必看重点", "keywords": []}
    hook_badge_text = first_sent["keywords"][0] if first_sent.get("keywords") else first_sent["text"][:6]
    top_ef = min(int(min(4.2, total_dur * 0.45) * fps), int(total_dur * fps))
    hook_ef = min(int(2.2 * fps), int(total_dur * fps))

    # 1. 若风格启用「顶部常驻标题栏」(如 style_01 / 03 / 06 / 08 / 22 / 24)，严格落在安全区 y=162 (>= SAFE_ZONE.y_min=160)
    if use_top_bar and total_dur >= 3.2 and not overlaps_code(0, top_ef):
        top_label = f"本期主题 · {hook_badge_text[:8]}"
        top_w = _measure_pkg_badge_width(top_label, pkg_font_path, SUBTITLE_SYMMETRIC_MAX_W, target_fs=34, min_w=280)
        top_bb = {"x": SUBTITLE_CENTER_X - top_w // 2, "y": 162, "w": top_w, "h": 58}
        ok_top, _ = check_bbox_in_safe_zone(top_bb)
        visual_elements.append({
            "id": f"pkg_{len(visual_elements)+1:03d}",
            "kind": "persistent_top_bar",
            "overlay_mode": "top_bar",
            "fg_hex": _safe_readable_fg(flower_spec.get("center_burst_color"), "#FFF589"),
            "stroke_hex": "#000000",
            "text_or_asset": top_label,
            "start_frame": 0,
            "end_frame": top_ef,
            "read_hold_sec": round(top_ef / float(fps), 2),
            "aligned_sfx_or_accent_frame": 0,
            "alignment_error_frames": 0,
            "bbox": top_bb,
            "final_bbox": top_bb,
            "safe_zone_ok": ok_top,
            "jianying_anim_name": default_jy_anim,
            "anim_duration_ms": int(matched_pair.get("anim_duration_ms", 400)),
            "paired_jianying_sfx": str(matched_pair.get("jianying_sfx_name", "提示音")),
            "reason": f"{style_id} 顶部常驻主题标语栏",
        })

    # 2. 开场真·巨字冲击（与顶部常驻标题栏可同屏共存，解除互斥锁！）
    can_place_opening_giant = (
        len(visual_elements) < max_visual_budget
        and (giant_count_target > 0 or is_borderless_flower or not use_top_bar)
        and not overlaps_code(0, hook_ef)
        and (hook_ef / float(fps) >= 1.35)
    )
    if can_place_opening_giant:
        hook_label = hook_badge_text[:6]
        hook_w = min(SUBTITLE_SYMMETRIC_MAX_W, max(360, _measure_pkg_badge_width(hook_label, pkg_font_path, SUBTITLE_SYMMETRIC_MAX_W, target_fs=96, min_w=360)))
        hook_x = SUBTITLE_CENTER_X - hook_w // 2
        hook_h = 152 if giant_mode in ("giant_dual_clash", "giant_numeric_trio") else 142
        init_giant_y = 224 if use_top_bar else 178
        active_faces_0 = []
        for c in edl.get("clips", []):
            if int(c["timeline_in_frame"]) < hook_ef and int(c["timeline_out_frame"]) > 0:
                active_faces_0.extend(faces_by_mp4.get(str(c.get("media_path", "")), []))
        hook_bbox = _avoid_faces_for_pkg({"x": hook_x, "y": init_giant_y, "w": hook_w, "h": hook_h}, active_faces_0)
        if use_top_bar and hook_bbox["y"] < 218:
            hook_bbox["y"] = 222
        safe_ok, _ = check_bbox_in_safe_zone(hook_bbox)
        sec_kw = (first_sent.get("keywords") or [None, None])[1] if len(first_sent.get("keywords") or []) >= 2 else ""
        visual_elements.append({
            "id": f"pkg_{len(visual_elements)+1:03d}",
            "kind": "center_burst_title",
            "giant_mode": giant_mode,
            "font_size_px": giant_fs,
            "tag_label": giant_tag,
            "accent_hex": giant_accent,
            "subtext": str(sec_kw or giant_tag),
            "overlay_mode": "borderless",
            "fg_hex": giant_fg,
            "stroke_hex": giant_stroke,
            "text_or_asset": hook_label,
            "start_frame": 0,
            "end_frame": hook_ef,
            "read_hold_sec": round(hook_ef / float(fps), 2),
            "aligned_sfx_or_accent_frame": 0,
            "alignment_error_frames": 0,
            "bbox": hook_bbox,
            "final_bbox": hook_bbox,
            "safe_zone_ok": safe_ok,
            "jianying_anim_name": default_jy_anim,
            "anim_duration_ms": int(matched_pair.get("anim_duration_ms", 400)),
            "paired_jianying_sfx": str(matched_pair.get("jianying_sfx_name", "“呼”的转场音效")),
            "reason": f"{style_id} 开场 {giant_fs}px 砸屏巨字冲击 ({giant_mode})",
        })
    max_pkg_w = SUBTITLE_SYMMETRIC_MAX_W

    raw_intel_p = pipeline_dir / "00_raw_intel.json"
    raw_pain_kws = [str(k) for k in ((read_json(raw_intel_p).get("pain_keywords") or []) if raw_intel_p.is_file() else []) if str(k).strip()]

    last_vis_end = hook_ef + int(2.2 * fps)
    last_sent = audio_events["sentences"][-1] if audio_events["sentences"] else None
    stamp_zone_ys = (280, 860, 230, 930)
    stamp_seq = 0
    has_end_cta = False
    for cue in sfx_cues:
        if len(visual_elements) >= max_visual_budget:
            break
        sf = int(cue["frame"])
        if sf < last_vis_end or sf > int((total_dur - 1.35) * fps):
            continue
        sent = next((s for s in audio_events["sentences"] if s["start_frame"] <= sf <= s["end_frame"] + 15), first_sent)
        if sent.get("emotion_or_info") not in ("hook", "info", "twist", "persona", "cta"):
            continue

        # 优先采用与本句重合的客户真实痛点词做花字，否则用句子重点词
        sent_txt = str(sent.get("text") or "")
        matched_pain = next((pk for pk in raw_pain_kws if pk in sent_txt), None)
        kw_label = matched_pain or (sent["keywords"][0] if sent.get("keywords") else sent_txt[:8])
        est_hold = estimate_read_hold_sec(kw_label, min_sec=2.0, max_sec=3.0)
        ef = min(int(total_dur * fps), sf + int(math.ceil(est_hold * fps)))
        if (ef - sf) / float(fps) < 1.35 or overlaps_code(sf, ef):
            continue
        is_end_cta = bool(is_borderless_flower and last_sent and sent.get("id") == last_sent.get("id"))
        is_quote_item = bool(use_quote_card and not is_end_cta and stamp_seq == 0)
        use_centered_box = True
        box_max_w = SUBTITLE_SYMMETRIC_MAX_W
        target_fs = 64 if is_quote_item else (68 if is_borderless_flower else 48)
        box_w = min(box_max_w, max(320 if is_quote_item else 260, _measure_pkg_badge_width(kw_label, pkg_font_path, box_max_w, target_fs=target_fs, min_w=320 if is_quote_item else 260)))
        box_x = SUBTITLE_CENTER_X - box_w // 2
        box_h = 136 if is_end_cta else (132 if is_quote_item else (112 if is_borderless_flower else 96))
        init_y = 920 if is_end_cta else (840 if is_quote_item else stamp_zone_ys[stamp_seq % len(stamp_zone_ys)])
        active_faces = []
        for c in edl.get("clips", []):
            if int(c["timeline_in_frame"]) < ef and int(c["timeline_out_frame"]) > sf:
                active_faces.extend(faces_by_mp4.get(str(c.get("media_path", "")), []))
        final_bbox = _avoid_faces_for_pkg({"x": box_x, "y": init_y, "w": box_w, "h": box_h}, active_faces)
        ok, _ = check_bbox_in_safe_zone(final_bbox)
        elem_kind = (
            "end_card_cta" if is_end_cta else
            ("quote_citation_card" if is_quote_item else
             ("stamp_tag" if is_borderless_flower else "flower_text"))
        )
        fg_key = "end_card_color" if is_end_cta else ("flank_color" if is_quote_item else "stamp_color")
        fg_default = "#FFE28A" if (is_end_cta or is_quote_item) else "#FFF589"
        burst_tags = [str(k)[:5] for k in (sent.get("keywords") or []) if str(k).strip()][:3] if use_multi_tag else []
        elem_obj: Dict[str, Any] = {
            "id": f"pkg_{len(visual_elements)+1:03d}",
            "kind": elem_kind,
            "overlay_mode": "borderless" if is_borderless_flower else ("focus_blur" if sent.get("emotion_or_info") == "twist" else "corner"),
            "fg_hex": _safe_readable_fg(flower_spec.get(fg_key), fg_default),
            "accent_hex": giant_accent,
            "stroke_hex": str(flower_spec.get("stroke_color") or "#000000"),
            "text_or_asset": f"“{kw_label}”" if is_quote_item and not kw_label.startswith("“") else kw_label,
            "subtext": f"—— {giant_tag} · 核心实证" if is_quote_item else "",
            "burst_tags": burst_tags,
            "start_frame": sf,
            "end_frame": ef,
            "read_hold_sec": round((ef - sf) / float(fps), 2),
            "aligned_sfx_or_accent_frame": sf,
            "alignment_error_frames": 0,
            "bbox": final_bbox,
            "final_bbox": final_bbox,
            "safe_zone_ok": ok,
            "jianying_anim_name": default_jy_anim,
            "anim_duration_ms": int(matched_pair.get("anim_duration_ms", 400)),
            "paired_jianying_sfx": str(matched_pair.get("jianying_sfx_name", "“呼”的转场音效")),
            "reason": cue["reason"],
        }
        if is_end_cta:
            elem_obj["subtext"] = "评论区聊聊你的看法"
            has_end_cta = True
        else:
            stamp_seq += 1
        visual_elements.append(elem_obj)
        last_vis_end = ef + int(2.5 * fps)

    # 保障片尾互动大字在无框风格下不会因末句缺少独立 SFX cue 而丢失
    if is_borderless_flower and not has_end_cta and last_sent and len(visual_elements) < max_visual_budget:
        ls_sf = int(last_sent.get("start_frame", 0))
        ls_ef = min(int(total_dur * fps), max(ls_sf + int(1.45 * fps), int(last_sent.get("end_frame", ls_sf))))
        if ls_sf >= last_vis_end and (ls_ef - ls_sf) / float(fps) >= 1.40 and not overlaps_code(ls_sf, ls_ef):
            cta_label = (last_sent["keywords"][0] if last_sent.get("keywords") else str(last_sent.get("text", ""))[:8]) or "欢迎评论聊聊"
            bw = _measure_pkg_badge_width(cta_label, pkg_font_path, max_pkg_w, target_fs=54, min_w=240)
            bx = SUBTITLE_CENTER_X - bw // 2
            active_f = []
            for c in edl.get("clips", []):
                if int(c["timeline_in_frame"]) < ls_ef and int(c["timeline_out_frame"]) > ls_sf:
                    active_f.extend(faces_by_mp4.get(str(c.get("media_path", "")), []))
            cta_bb = _avoid_faces_for_pkg({"x": bx, "y": 920, "w": bw, "h": 128}, active_f)
            ok_cta, _ = check_bbox_in_safe_zone(cta_bb)
            visual_elements.append({
                "id": f"pkg_{len(visual_elements)+1:03d}",
                "kind": "end_card_cta",
                "overlay_mode": "borderless",
                "fg_hex": str(flower_spec.get("end_card_color") or "#FFE28A"),
                "stroke_hex": str(flower_spec.get("stroke_color") or "#000000"),
                "text_or_asset": cta_label,
                "subtext": "评论区聊聊你的看法",
                "start_frame": ls_sf,
                "end_frame": ls_ef,
                "read_hold_sec": round((ls_ef - ls_sf) / float(fps), 2),
                "aligned_sfx_or_accent_frame": ls_sf,
                "alignment_error_frames": 0,
                "bbox": cta_bb,
                "final_bbox": cta_bb,
                "safe_zone_ok": ok_cta,
                "jianying_anim_name": default_jy_anim,
                "anim_duration_ms": int(matched_pair.get("anim_duration_ms", 400)),
                "paired_jianying_sfx": str(matched_pair.get("jianying_sfx_name", "“呼”的转场音效")),
                "reason": "片尾收束互动召唤大字（绑定末句起声帧）",
            })

    packaging = {
        "step": "06_packaging",
        "style_id": style_id,
        "sfx_track_wav": str(sfx_wav_path.resolve()),
        "budget": {
            "max_visual_elements": max_visual_budget,
            "used_visual_elements": len(visual_elements),
            "max_sfx_cues": max_sfx_budget,
            "used_sfx_cues": len(sfx_cues),
        },
        "sfx_cues": sfx_cues,
        "visual_elements": visual_elements,
    }
    write_json(pipeline_dir / "06_packaging.json", packaging)
    print(
        f"[step6] 包装完成：音效 {len(sfx_cues)}/{max_sfx_budget} 个，"
        f"视觉包装 {len(visual_elements)}/{max_visual_budget} 个（±0 帧对齐）-> 06_packaging.json"
    )
    return packaging


def main() -> None:
    maybe_reexec_in_venv()
    parser = argparse.ArgumentParser(description="Step 6: 音效先行与±1帧对齐视觉包装")
    parser.add_argument("--pipeline-dir", required=True)
    parser.add_argument("--style-id", help="绑定风格谱 ID")
    args = parser.parse_args()
    run_step6(Path(args.pipeline_dir), style_id=args.style_id)


if __name__ == "__main__":
    main()

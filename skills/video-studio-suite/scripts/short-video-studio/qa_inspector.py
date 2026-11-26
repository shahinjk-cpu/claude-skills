#!/usr/bin/env python3
"""
[Step 10: 全套白盒硬红线自检 + 独立黑盒外部裁判 + 独立盲审取证包]
自动核查（白盒 #1–#11 + 黑盒 #12–#22 + 可选同步/来源门禁，统一三态 PASS | FAIL | SKIPPED_UNAVAILABLE）：
1–11. 响度(-14 LUFS ±1.5)、黑帧、静音、音画差(<=1帧)、字幕与03_audio_events真实偏差、切点对齐、
      平台UI安全区/540px水平居中/[220,860]对称带/<=3字残句/包装预算、镜头分布/零倒带/A-Roll占比、前3秒切换、句界严锁、禁词防露馅。
12–22. 调用 independent_verifier.py 执行单遍解码黑盒校验。
输出：pipeline/10_qa_report.json、pipeline/10_qa_report.md 与 pipeline/10_blind_review_pack.md
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    DEFAULT_FPS,
    EDIT_PROFILES,
    EXPORT_CHOICES,
    export_selection,
    LEAK_REGEX_PATTERNS,
    LOUDNESS_TOLERANCE_LUFS,
    SAFE_ZONE,
    SUBTITLE_CENTER_X,
    SUBTITLE_SAFE_ZONE,
    SUBTITLE_SYMMETRIC_ZONE,
    TARGET_LUFS,
    check_bbox_in_safe_zone,
    ffprobe_media,
    find_bin,
    maybe_reexec_in_venv,
    read_json,
    review_checks,
    run_cmd,
    sha256_file,
    write_json,
)

if __name__ == "__main__":
    maybe_reexec_in_venv()


META_LEAK_RE = re.compile("|".join(LEAK_REGEX_PATTERNS), re.IGNORECASE)


def _mk_check(
    cid: str,
    name: str,
    status: str,
    measured: str,
    threshold: str,
) -> Dict[str, Any]:
    st = status if status in ("PASS", "FAIL", "SKIPPED_UNAVAILABLE", "NOT_REQUESTED") else "FAIL"
    return {
        "id": cid,
        "name": name,
        "status": st,
        "passed": (st == "PASS"),
        "measured": measured,
        "threshold": threshold,
    }


def _strip_punct_for_len(text: str) -> str:
    return re.sub(r"[\s，。！？；：、,.!?;:\"'“”‘’()（）\[\]【】—\-]+", "", str(text or ""))


def _check_bbox_in_bounds(bbox: Any, bounds: Dict[str, int], label: str) -> tuple[bool, str]:
    if not isinstance(bbox, dict) or not {"x", "y", "w", "h"}.issubset(bbox.keys()):
        return False, f"{label}: 缺少完整 bbox"
    x, y, w, h = int(bbox["x"]), int(bbox["y"]), int(bbox["w"]), int(bbox["h"])
    if x < bounds["x_min"] or (x + w) > bounds["x_max"] or y < bounds["y_min"] or (y + h) > bounds["y_max"]:
        return False, f"{label} ({x},{y},{x+w},{y+h}) 越出 ({bounds['x_min']},{bounds['y_min']},{bounds['x_max']},{bounds['y_max']})"
    return True, "ok"


def compare_with_benchmark(video_path: Path, benchmark_path: Path, edl: Dict[str, Any]) -> Dict[str, Any]:
    """与用户提供的对标参考视频做结构/节奏对比（只读对比）。"""
    ffmpeg = find_bin("ffmpeg")
    b_probe = ffprobe_media(benchmark_path)
    b_dur = float(b_probe.get("format", {}).get("duration") or 10.0)
    b_cuts = 1
    if ffmpeg:
        res = run_cmd([
            ffmpeg, "-hide_banner", "-i", str(benchmark_path),
            "-vf", "select='gt(scene,0.28)',showinfo", "-f", "null", "-",
        ], check=False)
        b_cuts = max(1, len(re.findall(r"pts_time:([0-9.]+)", res.stderr or "")))

    v_dur = float(edl.get("total_duration_sec") or 1.0)
    v_cuts = max(1, len(edl.get("clips") or []))
    b_asl = round(b_dur / b_cuts, 2)
    v_asl = round(v_dur / v_cuts, 2)
    return {
        "benchmark_file": str(benchmark_path.resolve()),
        "benchmark_duration_sec": round(b_dur, 2),
        "benchmark_estimated_asl_sec": b_asl,
        "our_duration_sec": round(v_dur, 2),
        "our_asl_sec": v_asl,
        "rhythm_delta_sec": round(v_asl - b_asl, 2),
        "our_video_path": str(video_path.resolve()),
    }


def detect_black_intervals(video_path: Path) -> tuple[str, List[str]]:
    ffmpeg = find_bin("ffmpeg")
    if not ffmpeg:
        return "SKIPPED_UNAVAILABLE", []
    result = run_cmd([
        ffmpeg, "-hide_banner", "-nostats", "-i", str(video_path),
        "-vf", "blackdetect=d=0:pix_th=0.07", "-an", "-f", "null", "-",
    ], check=False)
    if result.returncode:
        return "FAIL", []
    hits = re.findall(r"black_start:([0-9.]+)", result.stderr or "")
    return ("FAIL" if hits else "PASS"), hits


def measure_sync_marker(video_path: Path, start: float, end: float, fps: int) -> Dict[str, Any]:
    """Measure the onset offset of a bright slate flash and a paired test tone."""
    import numpy as np

    ffmpeg = find_bin("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("需要 FFmpeg 测量同步测试信号")
    if not (0 <= start < end and end - start <= 10):
        raise ValueError("同步测试窗须位于成片内且长度不超过 10 秒")
    seek = [ffmpeg, "-v", "error", "-ss", str(start), "-i", str(video_path), "-t", str(end - start)]
    visual = subprocess.check_output([
        *seek, "-an", "-vf", f"fps={fps},scale=16:16,format=gray", "-f", "rawvideo", "-",
    ])
    audio = subprocess.check_output([*seek, "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"])
    image_levels = np.frombuffer(visual, dtype=np.uint8).reshape(-1, 256).mean(axis=1)
    samples = np.frombuffer(audio, dtype="<i2").astype(float)
    levels = np.sqrt(np.mean(samples[: len(samples) // 80 * 80].reshape(-1, 80) ** 2, axis=1))
    if len(image_levels) < 3 or len(levels) < 3:
        raise ValueError("同步测试窗内的信号不足")
    background = float(np.percentile(image_levels, 20))
    flash = np.flatnonzero(image_levels > background + 40)
    beep = np.flatnonzero(levels > max(500, np.max(levels) * 0.35))
    if flash.size == 0 or beep.size == 0:
        raise ValueError("未同时测到测试闪帧与声音")
    video_on = start + int(flash[0]) / fps
    audio_on = start + int(beep[0]) / 100
    return {"video_sec": video_on, "audio_sec": audio_on, "offset_sec": audio_on - video_on}


def inspect_video(
    pipeline_dir: Path,
    video_path: Optional[Path] = None,
    benchmark_path: Optional[Path] = None,
    dialect: str = "mandarin",
    store_anchor: Optional[str] = None,
    strict_asr: bool = False,
    export_mode: str = "auto",
    sync_window: Optional[List[float]] = None,
) -> Dict[str, Any]:
    from workflow_guard import compute_plan_digest, package_digest
    from source_review import source_review_status

    if video_path is None:
        video_path = pipeline_dir / "output_final.mp4"
    if not video_path.exists():
        raise FileNotFoundError(f"待检成片不存在: {video_path}")

    plan_sha256 = compute_plan_digest(pipeline_dir)
    video_sha256 = sha256_file(video_path)
    audio_events = read_json(pipeline_dir / "03_audio_events.json")
    edl = read_json(pipeline_dir / "04_edl.json")
    subs = read_json(pipeline_dir / "05_subtitles.json")
    pkg = read_json(pipeline_dir / "06_packaging.json")

    fps = int(edl.get("fps", DEFAULT_FPS))
    pacing = EDIT_PROFILES.get(edl.get("edit_profile"), EDIT_PROFILES["talking"])
    frame_dur = 1.0 / fps
    checks: List[Dict[str, Any]] = []

    from independent_verifier import extract_audio_context_once, run_blackbox_verification

    with tempfile.TemporaryDirectory(prefix="svs_qa_audio_") as td:
        audio_ctx = extract_audio_context_once(video_path, Path(td))
        r128 = audio_ctx["r128"]
        long_sil = audio_ctx["long_silences"]

        # 1. 响度检查 (-14 LUFS ± LOUDNESS_TOLERANCE_LUFS，与黑盒 #12 同源)
        lufs = float(r128["integrated_lufs"])
        lufs_ok = abs(lufs - TARGET_LUFS) <= LOUDNESS_TOLERANCE_LUFS
        checks.append(_mk_check(
            "loudness",
            f"综合响度 ({TARGET_LUFS:.0f} LUFS)",
            "PASS" if lufs_ok else "FAIL",
            f"{lufs:.2f} LUFS (TP={r128['true_peak_dbtp']} dBTP)",
            f"{TARGET_LUFS - LOUDNESS_TOLERANCE_LUFS:.1f} ~ {TARGET_LUFS + LOUDNESS_TOLERANCE_LUFS:.1f} LUFS",
        ))

        # 2. 黑帧检测
        black_status, black_hits = detect_black_intervals(video_path)
        checks.append(_mk_check(
            "black_frames", "黑帧检测", black_status,
            ", ".join(black_hits[:5]) if black_hits else "未检出" if black_status == "PASS" else "解码失败",
            "0 处非预期黑帧",
        ))

        # 3. 超过 0.8s 静音段检测（复用单次音频抽取结果）
        checks.append(_mk_check(
            "long_silence",
            "超过 0.8s 的静音段",
            "PASS" if len(long_sil) == 0 else "FAIL",
            f"{len(long_sil)} 段" + (f" (最长 {max(long_sil):.2f}s)" if long_sil else ""),
            "0 段 > 0.8s",
        ))

        # 4. 音画同步与总时长差 <= 1 帧
        probe = ffprobe_media(video_path)
        streams = probe.get("streams", [])
        v_s = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_s = next((s for s in streams if s.get("codec_type") == "audio"), None)
        v_dur = float(v_s.get("duration") or probe.get("format", {}).get("duration") or 0.0) if v_s else 0.0
        a_dur = float(a_s.get("duration") or probe.get("format", {}).get("duration") or 0.0) if a_s else 0.0
        dur_diff_sec = abs(v_dur - a_dur)
        dur_diff_frames = dur_diff_sec / frame_dur
        aroll_sync_ok = all(bool(c.get("audio_locked", True)) for c in edl["clips"] if c.get("track_role") == "a_roll")
        start_delta = abs(float((v_s or {}).get("start_time") or 0) - float((a_s or {}).get("start_time") or 0))
        sync_ok = (v_s is not None and a_s is not None and max(dur_diff_sec, start_delta) <= frame_dur + 1e-6 and aroll_sync_ok)
        checks.append(_mk_check(
            "av_sync",
            "音视频流起点与时长 (≤1帧)",
            "PASS" if sync_ok else "FAIL",
            f"起点差 {start_delta*1000:.1f}ms，时长差 {dur_diff_sec*1000:.1f}ms ({dur_diff_frames:.2f} 帧), 同期声锁定={'是' if aroll_sync_ok else '否'}",
            f"≤ 1.0 帧 ({frame_dur*1000:.1f}ms)",
        ))
        if sync_window:
            try:
                marker = measure_sync_marker(video_path, *sync_window, fps)
                offset = marker["offset_sec"]
                status = "PASS" if abs(offset) <= frame_dur + 0.005 else "FAIL"
                detail = f"声音相对闪帧偏移 {offset * 1000:+.1f}ms"
            except (ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
                status, detail = "FAIL", str(exc)
            checks.append(_mk_check("sync_marker", "闪帧与测试音同步", status, detail, "≤1 帧，计入 5ms 测量误差"))

        # 5. 字幕与 03_audio_events 真实锁定语音时间戳交叉偏差（禁止与自身 words 相减作假）
        sents_all = audio_events.get("sentences", [])
        sents_by_id = {s["id"]: s for s in sents_all if s.get("id")}
        max_sub_err_sec = 0.0
        sub_sync_violations: List[str] = []
        active_subs = [e for e in subs.get("entries", []) if not e.get("suppressed")]
        for sub in active_subs:
            sid = sub.get("sentence_id")
            st_sub = float(sub.get("start_sec", 0.0))
            en_sub = float(sub.get("end_sec", 0.0))
            ref_sent = sents_by_id.get(sid)
            if not ref_sent:
                sub_sync_violations.append(f"{sub.get('id')}: 未关联有效 03_audio_events 句子 {sid}")
                continue
            s_st = float(ref_sent.get("start_sec", 0.0))
            s_en = float(ref_sent.get("end_sec", 0.0))
            if st_sub < s_st - 0.08 or en_sub > s_en + 0.12:
                overrun = max(s_st - st_sub, en_sub - s_en, 0.0)
                max_sub_err_sec = max(max_sub_err_sec, overrun)
                sub_sync_violations.append(f"{sub.get('id')}: 超出所属锁定句窗 [{s_st:.2f},{s_en:.2f}]")

            ref_words = ref_sent.get("words") or []
            sub_words = sub.get("words") or []
            if ref_words and sub_words:
                rw_starts = [float(w["start_sec"]) for w in ref_words if "start_sec" in w]
                rw_ends = [float(w["end_sec"]) for w in ref_words if "end_sec" in w]
                if rw_starts and "start_sec" in sub_words[0]:
                    first_w_t = float(sub_words[0]["start_sec"])
                    nearest_s = min(abs(first_w_t - ts) for ts in rw_starts)
                    max_sub_err_sec = max(max_sub_err_sec, nearest_s)
                    err_self = abs(st_sub - first_w_t)
                    max_sub_err_sec = max(max_sub_err_sec, err_self)
                if rw_ends and "end_sec" in sub_words[-1]:
                    last_w_t = float(sub_words[-1]["end_sec"])
                    nearest_e = min(abs(last_w_t - te) for te in rw_ends)
                    max_sub_err_sec = max(max_sub_err_sec, nearest_e)
                    err_self_e = abs(en_sub - last_w_t)
                    max_sub_err_sec = max(max_sub_err_sec, err_self_e)

        sub_err_frames = max_sub_err_sec / frame_dur
        all_subs_entries = subs.get("entries", [])
        all_suppressed_b9 = (
            len(all_subs_entries) > 0
            and len(active_subs) == 0
            and int(subs.get("suppressed_count", 0)) >= len(all_subs_entries)
        )
        sub_sync_ok = (len(active_subs) > 0 or len(sents_all) == 0 or all_suppressed_b9) and len(sub_sync_violations) == 0 and sub_err_frames <= 1.5
        checks.append(_mk_check(
            "subtitle_sync",
            "字幕与 03_audio_events 语音时间戳交叉对齐",
            "PASS" if sub_sync_ok else "FAIL",
            f"最大交叉偏差 {max_sub_err_sec*1000:.1f}ms ({sub_err_frames:.2f} 帧), 越窗 {len(sub_sync_violations)} 处",
            "≤ 1.5 帧且 0 越出锁定句时间窗",
        ))

        # 6. 切点对齐音频事件 (含 J-cut)
        events_by_id = {e["id"]: e for e in audio_events.get("events", [])}
        max_cut_err_frames = 0
        jcut_valid = True
        for clip in edl.get("clips", [])[1:]:
            ev = events_by_id.get(clip.get("cut_event_id", ""))
            j_lead = int(clip.get("j_cut_lead_frames", 0))
            if not (-6 <= j_lead <= 4):
                jcut_valid = False
            if not ev:
                max_cut_err_frames = 999
            else:
                err = abs((int(clip["timeline_in_frame"]) - j_lead) - int(ev["frame"]))
                max_cut_err_frames = max(max_cut_err_frames, err)
        cut_ok = jcut_valid and max_cut_err_frames <= 1
        checks.append(_mk_check(
            "cut_on_audio_event",
            "切点对齐音频事件 (含J-cut)",
            "PASS" if cut_ok else "FAIL",
            f"最大对齐偏差 {max_cut_err_frames} 帧, J-cut合规={'是' if jcut_valid else '否'}",
            "≤ 1 帧",
        ))

        # 7. UI 安全区 / 540px 真居中对称带 / <=3 字残句 / B9 互斥 / 包装预算
        ui_violations: List[str] = []
        short_subs = 0
        code_ranges = [
            (int(c["timeline_in_frame"]), int(c["timeline_out_frame"]))
            for c in edl.get("clips", [])
            if c.get("track_role") == "code_broll"
        ]
        code_collisions = 0
        for sub in subs.get("entries", []):
            if sub.get("suppressed"):
                continue
            bbox = sub.get("final_bbox") or sub.get("bbox")
            ok1, msg1 = check_bbox_in_safe_zone(bbox) if bbox else (False, "缺少bbox")
            ok2, msg2 = _check_bbox_in_bounds(bbox, SUBTITLE_SAFE_ZONE, sub.get("id", "sub"))
            if not ok1 or not ok2:
                ui_violations.append(f"{sub['id']}: {msg1 if not ok1 else msg2}")
            elif isinstance(bbox, dict):
                bx = float(bbox["x"])
                bw = float(bbox["w"])
                cx = bx + bw / 2.0
                if abs(cx - float(SUBTITLE_CENTER_X)) > 4.0:
                    ui_violations.append(
                        f"{sub['id']}: 字幕未水平居中 (中心 X={cx:.1f}px，目标 {SUBTITLE_CENTER_X}±4px)"
                    )
                if bx < SUBTITLE_SYMMETRIC_ZONE["x_min"] or (bx + bw) > SUBTITLE_SYMMETRIC_ZONE["x_max"]:
                    ui_violations.append(
                        f"{sub['id']}: 字幕横越居中对称带 [{SUBTITLE_SYMMETRIC_ZONE['x_min']},{SUBTITLE_SYMMETRIC_ZONE['x_max']}] (实测 [{bx:.0f},{bx+bw:.0f}])"
                    )
            clean_txt = _strip_punct_for_len(sub.get("text", ""))
            ref_sent_txt = _strip_punct_for_len(sents_by_id.get(sub.get("sentence_id", ""), {}).get("text", ""))
            if len(clean_txt) <= 3 and len(ref_sent_txt) >= 5:
                short_subs += 1
                ui_violations.append(f"{sub['id']}: <=3字残句 '{sub.get('text', '')}'")
            sf_sub = int(round(float(sub.get("start_sec", 0.0)) * fps))
            ef_sub = int(round(float(sub.get("end_sec", 0.0)) * fps))
            for cs, ce in code_ranges:
                ov = max(0, min(ef_sub, ce) - max(sf_sub, cs))
                if ef_sub > sf_sub and ov / float(ef_sub - sf_sub) >= 0.60:
                    code_collisions += 1
                    ui_violations.append(f"{sub['id']}: 未触发 B9 让位与代码卡重叠")

        total_edl_dur = max(0.1, float(edl.get("total_duration_sec", 1.0)))
        max_visual_budget = max(3, math.ceil(total_edl_dur / 3.5))
        vis_elems = pkg.get("visual_elements", [])
        if len(vis_elems) > max_visual_budget:
            ui_violations.append(f"视觉包装超预算 {len(vis_elems)} > {max_visual_budget}")
        short_holds = 0
        for elem in vis_elems:
            ebbox = elem.get("final_bbox") or elem.get("bbox")
            ok, msg = _check_bbox_in_bounds(ebbox, SAFE_ZONE, elem.get("id", "pkg"))
            if not ok:
                ui_violations.append(f"{elem['id']}: {msg}")
            sf_e, ef_e = int(elem["start_frame"]), int(elem["end_frame"])
            elem_txt = str(elem.get("text_or_asset") or "")
            hold_sec = (ef_e - sf_e) / float(fps)
            if elem_txt and hold_sec < 1.35:
                short_holds += 1
                ui_violations.append(f"{elem['id']}: 卡片停留过短 {hold_sec:.2f}s (<1.35s)")
            if any(sf_e < ce and ef_e > cs for cs, ce in code_ranges):
                code_collisions += 1
                ui_violations.append(f"{elem['id']}: 与代码补镜卡重叠")
        pkg_sync_err = max(
            [abs(int(e["start_frame"]) - int(e.get("aligned_sfx_or_accent_frame", e["start_frame"]))) for e in vis_elems]
            or [0]
        )
        ui_ok = len(ui_violations) == 0 and pkg_sync_err <= 1
        checks.append(_mk_check(
            "ui_safe_zone",
            "平台 UI 安全区 / 代码卡互斥 / 零 <=3 残句 / 阅读停留",
            "PASS" if ui_ok else "FAIL",
            f"违规 {len(ui_violations)} 处 (碰撞={code_collisions}, <=3残句={short_subs}, 短停留={short_holds}, 包装={len(vis_elems)}/{max_visual_budget}), 误差 {pkg_sync_err} 帧",
            "0违规/0碰撞/0残句, 卡片停留≥1.35s, 包装<=ceil(dur/3.5), 误差<=1帧",
        ))

        # 8. 镜头时长分布 + 零同源倒带 + A-Roll 占比
        durs = [float(c["duration_sec"]) for c in edl["clips"]]
        min_d, max_d = min(durs), max(durs)
        med_d = statistics.median(durs)
        rewind_count = 0
        clips_list = edl.get("clips", [])
        last_src_out_by_mp: Dict[str, float] = {}
        for c_cur in clips_list:
            mp = str(c_cur.get("media_path") or "")
            if not mp:
                continue
            if c_cur.get("track_role") == "code_broll":
                continue
            cin_s = float(c_cur.get("source_in_sec", 0.0))
            cout_s = float(c_cur.get("source_out_sec", cin_s))
            if mp in last_src_out_by_mp and cin_s < last_src_out_by_mp[mp] - 0.08:
                rewind_count += 1
            last_src_out_by_mp[mp] = max(last_src_out_by_mp.get(mp, 0.0), cout_s)
        aroll_clips = [c for c in clips_list if c.get("track_role") == "a_roll"]
        masked_voice_clips = [c for c in clips_list if c.get("audio_only_masked")]
        aroll_ratio = (
            (sum(float(c["duration_sec"]) for c in aroll_clips) + sum(float(c["duration_sec"]) for c in masked_voice_clips))
            / total_edl_dur
            if (aroll_clips or masked_voice_clips)
            else 0.0
        )
        broll_tgt = float(edl.get("broll_ratio_target") if edl.get("broll_ratio_target") is not None else 0.53)
        if edl.get("style_id") and edl.get("broll_ratio_target") is None:
            from common import load_style_spectrum_entry
            st_ent = load_style_spectrum_entry(str(edl["style_id"]))
            if st_ent and st_ent.get("broll_overlay_ratio_target") is not None:
                broll_tgt = float(st_ent["broll_overlay_ratio_target"])
        if broll_tgt >= 0.995:
            aroll_ok = True
        elif broll_tgt >= 0.85:
            min_aroll_floor = max(0.0, (1.0 - broll_tgt) * 0.40)
            aroll_ok = (aroll_ratio >= min_aroll_floor) if aroll_clips else True
        else:
            aroll_tail_ok = True if not aroll_clips else any(float(c["timeline_out_sec"]) >= total_edl_dur - 10.0 for c in aroll_clips)
            aroll_ok = (aroll_ratio >= 0.18 and aroll_tail_ok) if aroll_clips else True
        dist_ok = (min_d >= 0.30 and max_d <= pacing["max_shot_sec"] and rewind_count == 0 and aroll_ok)
        checks.append(_mk_check(
            "shot_duration_dist",
            "镜头分布 / 零同源倒带 / A-Roll 占比",
            "PASS" if dist_ok else "FAIL",
            f"共{len(durs)}镜 | min={min_d:.2f}s, med={med_d:.2f}s, max={max_d:.2f}s | 倒带={rewind_count}, A-roll={aroll_ratio*100:.1f}%",
            f"0.30s≤单镜≤{pacing['max_shot_sec']:.1f}s, 0非预期倒带",
        ))

        # 9. 前 3 秒画面变化次数
        first_3s_cuts = [c for c in edl["clips"][1:] if int(c["timeline_in_frame"]) < 3 * fps]
        all_on_events = all(c.get("cut_event_id") in events_by_id for c in first_3s_cuts)
        first3_ok = len(first_3s_cuts) >= pacing["opening_cuts"] and all_on_events
        checks.append(_mk_check(
            "first_3s_changes",
            "前 3 秒画面变化次数",
            "PASS" if first3_ok else "FAIL",
            f"{len(first_3s_cuts)} 次变化 (对齐事件: {'全部' if all_on_events else '部分缺失'})",
            f"≥ {pacing['opening_cuts']} 次且切点对齐音频事件",
        ))

        # 10. A-Roll 句界严锁（兼容正常 J/L-cut 声画错位延续）
        aroll_boundary_violations: List[str] = []
        max_overrun_sec = 0.0
        max_late_in_sec = 0.0
        for ci, c in enumerate(aroll_clips):
            c_in, c_out = float(c["timeline_in_sec"]), float(c["timeline_out_sec"])
            overlapping = [s for s in sents_all if min(c_out, float(s["end_sec"])) - max(c_in, float(s["start_sec"])) > 0.04]
            if not overlapping and c.get("sentence_id") in sents_by_id:
                overlapping = [sents_by_id[c["sentence_id"]]]
            if not overlapping:
                continue
            first_s, last_s = overlapping[0], overlapping[-1]
            base_end = float(last_s["end_sec"]) + 0.08
            src_locked_ok = float(c.get("source_out_sec", 0.0)) <= float(last_s.get("source_out_sec", 99999.0)) + 0.06
            dyn_end = float(last_s["end_sec"]) + float(last_s.get("pause_after_sec", 0.08)) + 0.04 if src_locked_ok else base_end
            # 允许相邻 B-roll L-cut 跨界延申 (<= 0.25s)
            l_lead_allowance = 0.0
            clip_pos = clips_list.index(c)
            if clip_pos + 1 < len(clips_list):
                nxt_j = int(clips_list[clip_pos + 1].get("j_cut_lead_frames", 0))
                if nxt_j < 0:
                    l_lead_allowance = abs(nxt_j) / float(fps) + 0.04
            cut_end_limit = max(base_end, dyn_end) + l_lead_allowance
            if last_s["id"] == sents_all[-1]["id"] and c is clips_list[-1]:
                cut_end_limit = max(cut_end_limit, total_edl_dur)
            overrun = c_out - cut_end_limit
            max_overrun_sec = max(max_overrun_sec, max(0.0, overrun))
            if overrun > 0.04:
                aroll_boundary_violations.append(f"{c['clip_id']} ({last_s['id']}): +{overrun:.2f}s")
            late_in = c_in - float(first_s["start_sec"])
            max_late_in_sec = max(max_late_in_sec, max(0.0, late_in))
            if late_in > 1.20:
                aroll_boundary_violations.append(f"{c['clip_id']} ({first_s['id']}): 晚入 +{late_in:.2f}s")
        checks.append(_mk_check(
            "aroll_sentence_lock",
            "同期声句界契约",
            "PASS" if len(aroll_boundary_violations) == 0 else "FAIL",
            f"违规 {len(aroll_boundary_violations)} 处 (超界 {max_overrun_sec:.2f}s, 晚入 {max_late_in_sec:.2f}s)",
            "0 违规 (超界≤0.04s, 晚入≤1.20s)",
        ))

        # 11. 统一使用 common.LEAK_REGEX_PATTERNS 的零开发词与风格名称露馅审计
        meta_leaks: List[str] = []

        def _scan_text(src_tag: str, txt: Any) -> None:
            s = str(txt or "").strip()
            if not s:
                return
            m = META_LEAK_RE.search(s)
            if m:
                meta_leaks.append(f"{src_tag}: 命中 '{m.group(0)}' ({s[:24]})")

        for sub in subs.get("entries", []):
            _scan_text(sub.get("id", "sub"), sub.get("text"))
        for elem in pkg.get("visual_elements", []):
            _scan_text(elem.get("id", "pkg"), elem.get("text_or_asset"))
        cover_json_p = pipeline_dir / "09_title_cover.json"
        if cover_json_p.exists():
            cj = read_json(cover_json_p)
            for k in ("cover_main", "cover_sub", "hashtags"):
                _scan_text(f"09_cover.{k}", cj.get(k))
            for ti, tline in enumerate(cj.get("titles") or []):
                _scan_text(f"09_cover.titles[{ti}]", tline)
        copy_pack_p = pipeline_dir / "09_publish_copy_pack.json"
        if copy_pack_p.exists():
            pj = read_json(copy_pack_p)
            for plat_k, plat_v in (pj.get("platforms") or {}).items():
                if not isinstance(plat_v, dict):
                    continue
                for ti, tline in enumerate(plat_v.get("titles") or []):
                    _scan_text(f"09_copy.{plat_k}.titles[{ti}]", tline)
                _scan_text(f"09_copy.{plat_k}.body", plat_v.get("body"))

        checks.append(_mk_check(
            "forbidden_meta_text",
            "零开发词与风格名称露馅审计",
            "PASS" if len(meta_leaks) == 0 else "FAIL",
            f"检出 {len(meta_leaks)} 处" + (f" ({meta_leaks[0]})" if meta_leaks else ""),
            "0 处元数据/风格代号露馅",
        ))

        # 11b. 10 秒滑窗残留重说与半截起句复查（正式接入 scan_residual_repeats）
        sent_list = audio_events.get("sentences") or []
        rep_scan = scan_residual_repeats(sent_list, window_sec=10.0)
        rep_ok = bool(rep_scan.get("clean", True))
        dup_hits = rep_scan.get("duplicate_phrases") or []
        orph_hits = rep_scan.get("orphan_starts") or []
        checks.append(_mk_check(
            "residual_repeat_scan",
            "成片口播残留重说与半截起句复查",
            "PASS" if rep_ok else "FAIL",
            f"残留重复 {len(dup_hits)} 处 / 孤立半截起句 {len(orph_hits)} 处",
            "10 秒内 0 处意外重复短语、0 处半截起句残留",
        ))

        # 12–22. 独立黑盒外部验收（复用 audio_ctx，严格 Fail-Closed 三态）
        bb_res = run_blackbox_verification(
            video_path,
            pipeline_dir=pipeline_dir,
            dialect=dialect,
            store_anchor=store_anchor,
            strict_asr=strict_asr,
            precomputed_audio=audio_ctx,
            export_mode=export_mode,
        )

    for bchk in bb_res["checks"]:
        checks.append(_mk_check(
            bchk["id"],
            bchk["name"],
            bchk["status"],
            bchk["measured"],
            bchk["threshold"],
        ))

    provenance_path = pipeline_dir / "04_source_review.json"
    provenance = source_review_status(read_json(provenance_path)) if provenance_path.is_file() else "NOT_REQUESTED"
    if provenance == "FAIL":
        checks.append(_mk_check("source_claims", "主张来源", "FAIL", "存在缺失或变更的来源或台词", "逐条可回查"))
    requested_exports, export_required = export_selection(export_mode)
    export_check = next((c for c in bb_res["checks"] if c["id"] == "bb_export_contracts"), {})
    export_results = export_check.get("detail", {}).get("targets", {})
    required_package_hashes = {
        name: package_digest(pipeline_dir / f"{name}_draft") for name in requested_exports
        if export_required and export_results.get(name, {}).get("status") == "PASS"
    }
    manual_checks = []
    if export_required and "jianying" in requested_exports:
        manual_checks.append("jianying_import")
    if provenance == "PENDING_REVIEW":
        manual_checks.append("source_claims")
    if (pipeline_dir / "00_code_spec.json").is_file():
        manual_checks.append("code_visual_review")
    commercial = next((c["detail"] for c in bb_res["checks"]
                       if c["id"] == "bb_compliance_and_license"), {})
    if commercial.get("unacked_warn_count"):
        manual_checks.append("compliance_context")
    if commercial.get("external_documents"):
        manual_checks.append("authorization_documents")
    blocking, unavailable = review_checks(checks, export_mode, strict_asr)
    manual_checks.extend(unavailable)
    all_passed = not blocking

    if plan_sha256 != compute_plan_digest(pipeline_dir) or video_sha256 != sha256_file(video_path):
        raise RuntimeError("质检期间方案或成片已变更，请重新质检。")

    approval_status = "REJECTED"
    if all_passed:
        approval_status = "REVIEW_REQUIRED" if manual_checks else "MACHINE_PASS_PENDING_HUMAN"
        lock_p = pipeline_dir / "approval_lock.json"
        if lock_p.is_file():
            try:
                lock = read_json(lock_p)
                if (
                    lock.get("human_approved") is True
                    and lock.get("plan_sha256") == plan_sha256
                    and lock.get("output_final_sha256") == video_sha256
                    and lock.get("export_mode", "auto") == export_mode
                    and lock.get("required_package_hashes", {}) == required_package_hashes
                    and set(manual_checks) <= set(lock.get("reviewed_checks", []))
                ):
                    approval_status = "APPROVED"
            except Exception:
                pass

    pass_cnt = sum(1 for c in checks if c["status"] == "PASS")
    fail_cnt = sum(1 for c in checks if c["status"] == "FAIL")
    skip_cnt = sum(1 for c in checks if c["status"] == "SKIPPED_UNAVAILABLE")

    report: Dict[str, Any] = {
        "step": "10_qa_inspector",
        "video_path": str(video_path.resolve()),
        "plan_sha256": plan_sha256,
        "output_final_sha256": video_sha256,
        "all_passed": all_passed,
        "machine_passed": all_passed and not manual_checks,
        "blocking_checks": blocking,
        "pending_manual_checks": manual_checks if approval_status != "APPROVED" else [],
        "required_manual_checks": manual_checks,
        "export_mode": export_mode,
        "required_package_hashes": required_package_hashes,
        "sync_window": sync_window,
        "deliverables": {"mp4": {"status": "FAIL" if any(c != "bb_export_contracts" for c in blocking) else
                                  "PENDING_REVIEW" if any(c != "jianying_import" for c in manual_checks) else "PASS"},
                         **export_results},
        "approval_status": approval_status,
        "strict_asr": strict_asr,
        "pass_count": pass_cnt,
        "fail_count": fail_cnt,
        "skipped_count": skip_cnt,
        "total_checks": len(checks),
        "checks": checks,
        "blackbox_details": bb_res,
    }
    if benchmark_path and benchmark_path.exists():
        report["benchmark_comparison"] = compare_with_benchmark(video_path, benchmark_path, edl)

    write_json(pipeline_dir / "10_qa_report.json", report)

    status_banner = (
        "✅ **全部自动检查与人工终审已通过**"
        if approval_status == "APPROVED"
        else (
            "🟡 **自动检查已过，待您最后看一眼确认**"
            if all_passed
            else "❌ **有硬性问题未通过，请先修改再发**"
        )
    )
    plain_verdict = (
        "成片声音清晰、字幕居中没被按钮遮挡、画面切换干脆，所有硬性检查都过了，您确认一眼就能发。"
        if all_passed
        else f"还有 {fail_cnt} 项硬性问题没过（见下表标有「未通过」的行），建议先修好再发，避免发出后被限流或观感打折。"
    )
    _status_cn = {
        "PASS": "✅ 通过",
        "FAIL": "❌ 未通过",
        "SKIPPED_UNAVAILABLE": "⏭️ 环境未装跳过",
        "NOT_REQUESTED": "➖ 本次未要求",
    }
    _manual_cn = {
        "jianying_import": "剪映工程导入抽查",
        "source_claims": "原始报价或证明材料核对",
        "code_visual_review": "动态图解画面人眼核查",
        "compliance_context": "需凭证表述核验确认",
        "authorization_documents": "外置素材授权原件核对",
        "bb_ocr_av_loop": "画面字幕居中与同步人工抽查",
        "bb_pixel_readability": "字幕与人像遮挡及清晰度抽查",
        "bb_meta_leak_ocr": "画面零异常水印/开发词抽查",
        "bb_color_scope": "人物肤色与曝光自然度抽查",
        "bb_blind_asr_proxy": "整片盲听复核",
        "bb_cut_spot_verify": "镜头切换顺畅度抽查",
    }
    _check_plain_cn = {
        "loudness": "整片声音大小适中、不破音",
        "black_frames": "全程没有突然黑屏",
        "long_silence": "说话之间没有冷场大空白",
        "av_sync": "画面和声音严格对齐不脱节",
        "subtitle_sync": "字幕出现时间紧贴说话节奏",
        "cut_alignment": "切画面踩在说话和音乐节拍上",
        "ui_safe_zone": "字幕居中好看、不撞点赞按钮、不留碎字",
        "shot_rhythm": "镜头长短有起伏、不重复倒播",
        "first_3s_hook": "开头前 3 秒画面节奏抓人",
        "sentence_integrity": "没有把话说一半硬切断",
        "forbidden_meta_text": "画面和文案没有多余乱码或模板字样",
        "residual_repeat_scan": "没有漏剪的口误重说和半截话",
        "bb_audio_master": "成品声音饱满清晰、无爆音无穿帮",
        "bb_ocr_av_loop": "成片字幕实测正中对齐、字句准确",
        "bb_pixel_readability": "字幕不挡脸且对比清晰好认",
        "bb_color_scope": "人物肤色自然、不过曝不发灰",
        "bb_export_contracts": "可编辑工程包完整不缺素材",
        "bb_meta_leak_ocr": "成片画面干干净净无异常水印",
        "bb_freeze_frame": "没有卡顿定格死画面",
        "bb_cut_spot_verify": "每次切镜画面都有真实变化",
        "bb_sfx_onset_align": "提示音和画面动作严丝合缝",
        "bb_blind_asr_proxy": "脱离字幕盲听还原台词清晰准确",
        "bb_compliance_and_license": "台词文案合规、字体音乐全部可商用",
    }
    md_lines = [
        f"# 成片与交付工程体检报告（共 {len(checks)} 项）",
        "",
        f"- **一句话大白话结论**：{plain_verdict}",
        f"- **成片文件**：`{video_path.name}`",
        f"- **质量状态**：{status_banner}",
        f"- **统计**：共 {len(checks)} 项 · 通过 `{pass_cnt}` 项 · 未通过 `{fail_cnt}` 项 · 跳过 `{skip_cnt}` 项",
        "",
        "## 一、 大白话体验体检表",
        "",
        "| 序号 | 体检项目 | 结果 |",
        "| :---: | :--- | :---: |",
    ]
    for i, c in enumerate(checks, start=1):
        st_label = _status_cn.get(c["status"], c["status"])
        plain_title = _check_plain_cn.get(c["id"], c["name"])
        md_lines.append(f"| {i} | {plain_title} | {st_label} |")
    if manual_checks:
        manual_readable = "、".join(_manual_cn.get(m, m) for m in manual_checks)
        md_lines.extend(["", f"- **建议您最后一眼确认**：{manual_readable}"])
    for target, result in export_results.items():
        md_lines.extend(f"- {target}：{error}" for error in result.get("errors", []))

    md_lines.extend([
        "",
        "<details>",
        "<summary>展开查看专业工程实测明细（供技术复核）</summary>",
        "",
        "| # | 检查项 | 状态 | 实测结果 | 门槛 |",
        "|:-:|:---|:---:|:---|:---|",
    ])
    for i, c in enumerate(checks, start=1):
        measured = c["measured"].replace("|", "｜")
        st_label = _status_cn.get(c["status"], c["status"])
        md_lines.append(f"| {i} | {c['name']} | {st_label} | {measured} | {c['threshold']} |")
    md_lines.append("</details>")

    if "benchmark_comparison" in report:
        bc = report["benchmark_comparison"]
        md_lines.extend([
            "",
            "## 对标参考节奏对比",
            f"- 参考片 `{Path(bc['benchmark_file']).name}` 平均单镜时长：`{bc['benchmark_estimated_asl_sec']}s`；本片平均单镜时长：`{bc['our_asl_sec']}s`（差值 `{bc['rhythm_delta_sec']:+.2f}s`）",
        ])

    (pipeline_dir / "10_qa_report.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    _write_blind_review_pack(pipeline_dir, video_path, report, edl, subs, audio_events)
    print(f"[qa] {len(checks)} 项质检：{pass_cnt} PASS / {fail_cnt} FAIL / {skip_cnt} SKIP -> 10_qa_report.md")
    return report


def _write_blind_review_pack(
    pipeline_dir: Path,
    video_path: Path,
    report: Dict[str, Any],
    edl: Dict[str, Any],
    subs: Dict[str, Any],
    audio_events: Dict[str, Any],
) -> Path:
    """生成《独立盲审取证包》(10_blind_review_pack.md)：零内部代号，30 秒人眼/外审一页通关。"""
    bb_checks = {c["id"]: c for c in (report.get("blackbox_details", {}).get("checks") or [])}
    asr_detail = bb_checks.get("bb_blind_asr_proxy", {}).get("detail", {}) or {}
    asr_text = str(asr_detail.get("recognized_text") or "").strip()
    ocr_detail = bb_checks.get("bb_ocr_av_loop", {}).get("detail", {}) or {}
    cover_p = pipeline_dir / "09_title_cover.json"
    cover_meta = read_json(cover_p) if cover_p.is_file() else {}

    strip_p = pipeline_dir / "10_action_strips.jpg"
    cover_3x4 = pipeline_dir / "09_cover_3x4.jpg"
    cover_full = pipeline_dir / "09_cover.jpg"
    ui_prev = pipeline_dir / "09_ui_safe_preview.jpg"
    feed_prev = pipeline_dir / "09_cover_360px_feed.jpg"

    cover_files_list = [f"`{p.name}`" for p in (cover_full, cover_3x4, ui_prev, feed_prev) if p.is_file()]
    lines = [
        "# 成片出厂盲审取证包（不看内部制作过程，直接当普通观众验片）",
        "",
        "这份清单把成片的开头、关键切镜、手机小图封面和盲听还原的台词摊平在一页里，方便你或朋友 30 秒一眼验收：",
        "",
        "## 1. 取证材料一览",
        f"- **最终成片**：`{video_path.name}`（总时长 {float(edl.get('total_duration_sec', 0.0)):.1f} 秒，共 {len(edl.get('clips') or [])} 个镜头）",
        f"- **开头 3 秒与关键切点连拍长图**：`{strip_p.name}`" + ("（已生成）" if strip_p.is_file() else "（本次未生成，请直接播放成片前 3 秒核对）"),
        f"- **封面与手机信息流模拟预览**：{' / '.join(cover_files_list) if cover_files_list else '（本次未生成封面图）'}",
    ]
    if cover_meta:
        lines.append(
            f"- **封面实测清晰度（缩小到手机双列小图尺寸）**：对比度 `{cover_meta.get('thumb_180_contrast_ratio', '-')}:1`（越高越醒目，最低底线 3.8:1，推荐 ≥ 4.5:1），"
            f"人物前景压字：`{'已启用' if cover_meta.get('person_cutout_applied') else '标准排版'}`"
        )

    lines.extend([
        "",
        "## 2. 脱离字幕直接盲听还原的台词",
        (f"> {asr_text}" if asr_text else "> （本次未启用独立听写或视频无口播，请直接打开成片外放试听。）"),
        "",
        "## 3. 镜头画面与当下台词对照抽样（检查有没有文不对图）",
        "",
        "| 时间段 | 画面内容 | 这一刻嘴里正在说什么 |",
        "| :---: | :--- | :--- |",
    ])
    sents = audio_events.get("sentences") or []
    clips = edl.get("clips") or []
    step_stride = max(1, len(clips) // 8)
    for c in clips[::step_stride][:8]:
        c_in = float(c.get("timeline_in_sec", 0.0))
        c_out = float(c.get("timeline_out_sec", 0.0))
        spoken = [
            str(s.get("text") or "").strip()
            for s in sents
            if min(c_out, float(s.get("end_sec", 0.0))) - max(c_in, float(s.get("start_sec", 0.0))) > 0.15
        ]
        spoken_str = " / ".join(spoken[:2]) or "（画面过渡/停顿）"
        role_zh = (
            "真人出镜说话" if c.get("track_role") == "a_roll"
            else ("图解动画卡片" if c.get("track_role") == "code_broll" else "实拍特写/空镜")
        )
        purp = str(c.get("purpose") or role_zh).replace("|", "｜")
        lines.append(f"| {c_in:.1f}s–{c_out:.1f}s | {role_zh}：{purp} | {spoken_str.replace('|', '｜')} |")

    center_dev = ocr_detail.get("max_subtitle_center_dev_px")
    hook_check_src = "看连拍长图前 3 秒" if strip_p.is_file() else "静音播放成片前 3 秒"
    lines.extend([
        "",
        "## 4. 盲审人眼 5 问（全勾即可直接发布）",
        f"- [ ] **静音盲看前 3 秒**：{hook_check_src}，关掉声音的情况下，能不能一眼看懂在讲什么并想停下来？",
        "- [ ] **闭眼盲听顺不顺**：不看画面听一遍，有没有吞字、重说残句或音乐盖过说话声？",
        "- [ ] **画面对不对嘴**：看上面对照表，每段特写和字幕说的事是不是一回事？",
        f"- [ ] **字幕和按钮打不打架**：字幕都在正中间靠下清晰可读吗？（自动实测居中偏差：`{center_dev if center_dev is not None else '未测得'}px`）",
        "- [ ] **手机小图清不清楚**：看 `09_cover_360px_feed.jpg`（缩小成手机信息流真实宽度），主标题能不能 1 秒看清、没被裁切？",
    ])
    out_p = pipeline_dir / "10_blind_review_pack.md"
    out_p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_p


def scan_residual_repeats(
    segments: List[Dict[str, Any]],
    reference_text: Optional[str] = None,
    window_sec: float = 10.0,
) -> Dict[str, Any]:
    """
    成片转写残留重说扫描：
    1. 10 秒滑窗内同一 5 字片段重复出现（排除参考稿中本就有意重复 >=2 次的排比）；
    2. 1–6 字短孤立段且其前 2 字正是下一段开头（典型漏剪残留起句，如“地图……地图上其实”）。
    """
    clean_segs: List[Tuple[float, str]] = []
    for seg in (segments or []):
        t0 = float(seg.get("start_sec", seg.get("start", 0.0)))
        txt = _strip_punct_for_len(str(seg.get("text") or ""))
        if txt:
            clean_segs.append((t0, txt))

    ref_clean = _strip_punct_for_len(reference_text or "")
    dup_phrases: set[str] = set()
    for i, (t0, s0) in enumerate(clean_segs):
        for j in range(i, len(clean_segs)):
            t1, s1 = clean_segs[j]
            if (t1 - t0) > window_sec:
                break
            for k in range(max(0, len(s0) - 4)):
                gram = s0[k : k + 5]
                if len(gram) < 5:
                    continue
                pos = s1.find(gram, k + 5 if i == j else 0)
                if pos >= 0:
                    if not ref_clean or ref_clean.count(gram) < 2:
                        dup_phrases.add(gram)

    orphan_starts: List[str] = []
    for (t0, s0), (t1, s1) in zip(clean_segs, clean_segs[1:]):
        if 1 <= len(s0) <= 6 and len(s1) >= 2 and s1.startswith(s0[:2]):
            if (t1 - t0) <= 4.0:
                orphan_starts.append(f"{t0:.2f}s 「{s0}」→「{s1[:10]}」")

    return {
        "duplicate_phrases": sorted(dup_phrases),
        "orphan_starts": orphan_starts,
        "clean": (len(dup_phrases) == 0 and len(orphan_starts) == 0),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Step 10: 全套白盒硬红线与独立黑盒质检报告生成")
    parser.add_argument("--pipeline-dir", required=True)
    parser.add_argument("--video", help="指定待检 MP4（默认 output_final.mp4）")
    parser.add_argument("--benchmark", help="可选：对标视频路径")
    parser.add_argument("--dialect", default="mandarin", help="语言模式 (mandarin / cantonese / dialect)")
    parser.add_argument("--store-anchor", help="门店名/核心听觉锚点")
    parser.add_argument("--exports", choices=EXPORT_CHOICES, default=None)
    parser.add_argument("--sync-window", type=float, nargs=2, metavar=("START", "END"))
    parser.add_argument("--strict-asr", action=argparse.BooleanOptionalAction, default=None, help="要求可用的独立 ASR")
    args = parser.parse_args()
    previous = Path(args.pipeline_dir) / "10_qa_report.json"
    saved_report = read_json(previous) if previous.is_file() else {}

    res = inspect_video(
        Path(args.pipeline_dir),
        video_path=Path(args.video) if args.video else None,
        benchmark_path=Path(args.benchmark) if args.benchmark else None,
        dialect=args.dialect,
        store_anchor=args.store_anchor,
        strict_asr=args.strict_asr if args.strict_asr is not None else bool(saved_report.get("strict_asr")),
        export_mode=args.exports or saved_report.get("export_mode", "auto"),
        sync_window=args.sync_window or saved_report.get("sync_window"),
    )
    if not res["all_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()

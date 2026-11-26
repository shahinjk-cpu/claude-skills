#!/usr/bin/env python3
"""
[入口 2：带素材进来] 深度素材盘点、分镜日志 (00_shot_log) 与多模态视觉索引融合脚本
v5 增强：
1. 单遍 4fps 像素流同时测算 BT.709 YAVG、1%/99% 极值分位、等面积归一化拉普拉斯锐度与 2D FFT 二阶稳度；
   修复 skip=True 甩镜/硬切帧奖励成 best_in_sec 与 TV-range Y=16 导致 ng 死分支的 Bug。
2. 直接解析双声道原生 PCM（detect L/R 无线麦单边失效、0dBFS 削波率、动态范围 p95-p10），防止嘈杂空镜误判 A-roll。
3. 复用 common.detect_vfr_hdr 与 common.get_cached_font；支持多时间点抽帧跑 Vision 防止首帧漏脸/漏物体。
"""

from __future__ import annotations

import argparse
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import (
    MEDIA_EXTS,
    compute_bt709_luma,
    detect_vfr_hdr,
    ffprobe_media,
    find_bin,
    find_commercial_font,
    get_cached_font,
    maybe_reexec_in_venv,
    parse_video_stream_geometry,
    read_json,
    rescue_stereo_channels,
    run_cmd,
    write_json,
)

if __name__ == "__main__":
    maybe_reexec_in_venv()

import numpy as np
from PIL import Image, ImageDraw, ImageOps
from vision_inspector import compute_laplacian_sharpness, inspect_images

TABOO_KEYWORD_MAP: Dict[str, Tuple[str, ...]] = {
    "raw_meat": ("生肉", "血水", "宰杀", "内脏", "冻肉", "解冻", "raw_meat", "rawmeat", "blood"),
    "kitchen_trash": ("垃圾", "泔水", "厨余", "脏乱", "油污", "苍蝇", "kitchen_trash", "trash", "dirty"),
    "construction_trash": ("废料", "拆迁", "瓦砾", "工地垃圾", "施工废料", "construction_trash", "debris"),
    "crew_leak": ("穿帮", "场记", "打板", "摄影师", "工作人员", "三脚架", "反光板", "补光灯", "crew_leak", "crew"),
}


def estimate_phase_shift(
    prev_gray: np.ndarray,
    cur_gray: np.ndarray,
    win: Optional[np.ndarray] = None,
) -> Tuple[float, float, bool]:
    """用 2D FFT 相位相关估算两帧全局像素位移 (dx, dy)；纹理缺失或甩镜/硬切时返回 skip=True。"""
    if float(np.std(prev_gray)) < 2.5 or float(np.std(cur_gray)) < 2.5:
        return 0.0, 0.0, True
    mad = float(np.mean(np.abs(cur_gray - prev_gray))) / 255.0
    if mad > 0.28:
        return 0.0, 0.0, True
    h, w = prev_gray.shape
    if win is None or win.shape != (h, w):
        win = np.outer(np.hanning(h), np.hanning(w)).astype(np.float32)
    a = (prev_gray - float(np.mean(prev_gray))) * win
    b = (cur_gray - float(np.mean(cur_gray))) * win
    fa = np.fft.fft2(a)
    fb = np.fft.fft2(b)
    r = fa * np.conj(fb)
    r /= np.maximum(np.abs(r), 1e-8)
    cc = np.fft.fftshift(np.abs(np.fft.ifft2(r)))
    py, px = np.unravel_index(int(np.argmax(cc)), cc.shape)
    sub_y, sub_x = 0.0, 0.0
    if 0 < py < h - 1:
        denom_y = float(cc[py - 1, px] - 2.0 * cc[py, px] + cc[py + 1, px])
        if abs(denom_y) > 1e-8:
            sub_y = max(-0.5, min(0.5, 0.5 * float(cc[py - 1, px] - cc[py + 1, px]) / denom_y))
    if 0 < px < w - 1:
        denom_x = float(cc[py, px - 1] - 2.0 * cc[py, px] + cc[py, px + 1])
        if abs(denom_x) > 1e-8:
            sub_x = max(-0.5, min(0.5, 0.5 * float(cc[py, px - 1] - cc[py, px + 1]) / denom_x))
    return float(px + sub_x - (w // 2)), float(py + sub_y - (h // 2)), False


def _analyze_audio_raw(ffmpeg: str, path: Path, has_audio: bool, duration: float) -> Dict[str, Any]:
    """直接解析原始双声道 16k PCM：检测静音占比、动态范围、0dBFS 削波率与无线麦单边失效。"""
    if not has_audio or duration <= 0.1:
        return {"silence_ratio": 1.0, "dyn_range_db": 0.0, "clipping_ratio": 0.0, "stereo_diag": "silent"}
    try:
        res = subprocess.run(
            [
                ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-t", f"{min(duration, 45.0):.2f}", "-i", str(path),
                "-vn", "-f", "s16le", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "2", "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        aligned_n = (len(res.stdout) // 4) * 4
        if aligned_n < 4:
            return {"silence_ratio": 1.0, "dyn_range_db": 0.0, "clipping_ratio": 0.0, "stereo_diag": "silent"}
        pcm = np.frombuffer(res.stdout[:aligned_n], dtype=np.int16).astype(np.float32) / 32768.0
        if len(pcm) < 3200:
            return {"silence_ratio": 1.0, "dyn_range_db": 0.0, "clipping_ratio": 0.0, "stereo_diag": "silent"}
        arr = pcm.reshape(-1, 2)
        arr_fixed, st_diag = rescue_stereo_channels(arr, imbalance_db=8.0)
        mono = arr_fixed.mean(axis=1)
        clip_ratio = float(np.mean(np.abs(mono) >= 0.992))
        hop = 320  # 20ms @ 16k
        n_hops = len(mono) // hop
        if n_hops < 2:
            return {"silence_ratio": 1.0, "dyn_range_db": 0.0, "clipping_ratio": clip_ratio, "stereo_diag": st_diag}
        blocks = mono[: n_hops * hop].reshape(n_hops, hop)
        rms = np.sqrt(np.mean(blocks ** 2, axis=1) + 1e-12)
        db = 20.0 * np.log10(np.maximum(1e-6, rms))
        p10, p95 = float(np.percentile(db, 10)), float(np.percentile(db, 95))
        dyn_range = max(0.0, p95 - p10)
        sil_ratio = float(np.mean(db < -42.0))
        return {
            "silence_ratio": round(sil_ratio, 2),
            "dyn_range_db": round(dyn_range, 1),
            "clipping_ratio": round(clip_ratio, 5),
            "stereo_diag": st_diag,
        }
    except Exception:
        return {"silence_ratio": 1.0, "dyn_range_db": 0.0, "clipping_ratio": 0.0, "stereo_diag": "error"}


def analyze_video_quality(
    path: Path,
    duration: float,
    display_w: int,
    display_h: int,
    has_audio: bool = True,
) -> Dict[str, Any]:
    """单遍视频流 + 双声道 PCM 质检（BT.709 曝光分位、等面积锐度、FFT 稳度、最佳入点与双声道诊断）。"""
    ffmpeg = find_bin("ffmpeg")
    if not ffmpeg or duration <= 0.1:
        return {
            "exposure": "unknown",
            "avg_luma": None,
            "luma_p1": None,
            "luma_p99": None,
            "silence_ratio": 1.0,
            "dyn_range_db": 0.0,
            "clipping_ratio": 0.0,
            "stereo_diag": "silent",
            "sharpness_score": 0.0,
            "stability_score": 1.0,
            "motion_speed_px": 0.0,
            "accel_jitter_px": 0.0,
            "best_in_sec": 0.0,
            "issues": [],
        }

    issues: List[str] = []
    aud = _analyze_audio_raw(ffmpeg, path, has_audio, duration)
    sil_ratio = aud["silence_ratio"]
    if aud["stereo_diag"] not in ("ok", "silent", "error"):
        issues.append("检测到无线麦有一侧没录上声音，后期会自动用正常那一侧修复")
    elif aud["stereo_diag"] == "error":
        issues.append("音频读取异常，建议只用画面不取这条的原声")
    if aud["clipping_ratio"] > 0.005:
        issues.append(f"原声太大有破音（占比 {aud['clipping_ratio']*100:.2f}%）")
    if has_audio and sil_ratio > 0.6:
        issues.append(f"说话声音较少（安静占比 {int(sil_ratio*100)}%），适合当特写或环境补拍画面")

    # 等面积缩放 (等效 sqrt(W*H) ≈ 320)，彻底消除横屏与竖屏锐度双标
    dw = max(1, display_w)
    dh = max(1, display_h)
    target_px = 320.0 * 320.0
    scale_s = math.sqrt(target_px / float(dw * dh))
    w_s = max(120, int(round(dw * scale_s)) // 2 * 2)
    h_s = max(120, int(round(dh * scale_s)) // 2 * 2)
    frame_bytes = w_s * h_s * 3
    sample_fps = 4.0
    max_scan = min(duration, 30.0)
    proc = subprocess.Popen(
        [
            ffmpeg, "-hide_banner", "-loglevel", "error",
            "-t", f"{max_scan:.2f}", "-i", str(path),
            "-vf", f"fps={sample_fps},scale={w_s}:{h_s}",
            "-an", "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    assert proc.stdout is not None
    sharps: List[float] = []
    lumas_tv: List[float] = []
    p1s: List[float] = []
    p99s: List[float] = []
    shifts: List[Tuple[float, float, bool]] = []
    prev_gray: Optional[np.ndarray] = None
    while True:
        raw = proc.stdout.read(frame_bytes)
        if len(raw) < frame_bytes:
            break
        arr = np.frombuffer(raw, dtype=np.uint8).reshape((h_s, w_s, 3))
        # 复用全仓唯一权威 BT.709 亮度公式 -> 全范围灰度 & TV-range Y (16..235)
        y_full = compute_bt709_luma(arr.astype(np.float32))
        y_tv = 16.0 + (219.0 / 255.0) * y_full
        lumas_tv.append(float(np.mean(y_tv)))
        if len(p1s) < 60:
            p1s.append(float(np.percentile(y_tv, 1)))
            p99s.append(float(np.percentile(y_tv, 99)))
        sharps.append(compute_laplacian_sharpness(y_full))
        if prev_gray is not None:
            if hanning_win is None or hanning_win.shape != y_full.shape:
                hanning_win = np.outer(np.hanning(y_full.shape[0]), np.hanning(y_full.shape[1])).astype(np.float32)
            shifts.append(estimate_phase_shift(prev_gray, y_full, win=hanning_win))
        else:
            hanning_win = None
            shifts.append((0.0, 0.0, True))
        prev_gray = y_full
    proc.wait()

    avg_luma = round(float(np.mean(lumas_tv)), 1) if lumas_tv else 128.0
    luma_p1 = round(float(np.mean(p1s)), 1) if p1s else 16.0
    luma_p99 = round(float(np.mean(p99s)), 1) if p99s else 230.0
    if avg_luma < 55:
        exposure = "underexposed"
        issues.append("画面整体偏暗，后期调色会自动提亮")
    elif avg_luma > 205 or (luma_p99 > 233 and avg_luma > 180):
        exposure = "overexposed"
        issues.append("画面亮部有点过曝发白，后期调色会自动压回细节")
    elif luma_p1 <= 20 and luma_p99 >= 230 and avg_luma < 90:
        exposure = "high_contrast_backlit"
        issues.append("画面逆光明暗反差大，后期会自动优先保亮人脸")
    else:
        exposure = "normal"

    speeds: List[float] = [0.0] * len(sharps)
    accels: List[float] = [0.0] * len(sharps)
    valid_speeds: List[float] = []
    valid_accels: List[float] = []
    valid_dxs: List[float] = []
    valid_dys: List[float] = []
    for i in range(1, len(shifts)):
        dx1, dy1, skip1 = shifts[i]
        dx0, dy0, skip0 = shifts[i - 1]
        if skip1:
            # 甩镜或硬切跳过帧惩罚高加速度，绝不伪装成 0.0 稳定帧奖励入点！
            accels[i] = 15.0
            continue
        sp = math.hypot(dx1, dy1)
        speeds[i] = sp
        valid_speeds.append(sp)
        valid_dxs.append(dx1)
        valid_dys.append(dy1)
        if not skip0 and i >= 2:
            acc = math.hypot(dx1 - dx0, dy1 - dy0)
            accels[i] = acc
            valid_accels.append(acc)

    camera_motion = "static"
    if valid_dxs:
        med_dx = float(np.median(valid_dxs))
        med_dy = float(np.median(valid_dys))
        if abs(med_dx) >= max(2.2, abs(med_dy) * 1.4):
            camera_motion = "pan_right" if med_dx < 0 else "pan_left"
        elif abs(med_dy) >= max(2.2, abs(med_dx) * 1.4):
            camera_motion = "tilt_down" if med_dy < 0 else "tilt_up"
    action_apex_sec = round(int(np.argmax(speeds)) / sample_fps, 2) if valid_speeds and max(speeds) >= 2.0 else 0.0

    sharpness_score = round(float(np.mean(sharps)), 1) if sharps else 0.0
    med_speed = round(float(np.median(valid_speeds)) if valid_speeds else 0.0, 2)
    med_accel = round(float(np.median(valid_accels)) if valid_accels else 0.0, 2)
    stability_score = round(max(0.0, min(1.0, 1.0 - (max(0.0, med_accel - 0.6) / 10.0))), 3)

    best_in_sec = 0.0
    if len(sharps) >= 6 and duration > 2.2:
        s_np = np.array(sharps, dtype=np.float32)
        a_np = np.array(accels, dtype=np.float32)
        s_norm = (s_np - np.min(s_np)) / max(1e-5, float(np.max(s_np) - np.min(s_np)))
        a_norm = a_np / max(2.0, float(np.max(a_np)))
        skip_idx = min(len(sharps) - 4, max(1, int(round(0.40 * sample_fps))))
        max_idx = max(skip_idx + 1, len(sharps) - 4)
        best_score = -1e9
        best_idx = skip_idx
        for idx in range(skip_idx, max_idx):
            win_sharp = float(np.mean(s_norm[idx : idx + 4]))
            win_acc = float(np.mean(a_norm[idx : idx + 4]))
            sc = win_sharp - 0.75 * win_acc
            if sc > best_score:
                best_score = sc
                best_idx = idx
        best_in_sec = round(best_idx / sample_fps, 2)

    if sharpness_score > 0 and sharpness_score < 22.0:
        issues.append("画面有点虚焦发糊，会优先选用更清楚的片段")
    if stability_score < 0.55:
        issues.append(f"手持晃动较明显，已自动避开晃动段从 {best_in_sec} 秒稳态起剪")

    return {
        "exposure": exposure,
        "avg_luma": avg_luma,
        "luma_p1": luma_p1,
        "camera_motion": camera_motion,
        "action_apex_sec": action_apex_sec,
        "luma_p99": luma_p99,
        "silence_ratio": sil_ratio,
        "dyn_range_db": aud["dyn_range_db"],
        "clipping_ratio": aud["clipping_ratio"],
        "stereo_diag": aud["stereo_diag"],
        "sharpness_score": sharpness_score,
        "stability_score": stability_score,
        "motion_speed_px": med_speed,
        "accel_jitter_px": med_accel,
        "best_in_sec": best_in_sec,
        "issues": issues,
    }


def classify_clip(
    filename: str,
    a_stream: Optional[Dict[str, Any]],
    quality: Dict[str, Any],
    duration: float,
    v_idx_entry: Optional[Dict[str, Any]] = None,
) -> str:
    low = filename.lower()
    if v_idx_entry and v_idx_entry.get("role") in ("a_roll_candidate", "b_roll_candidate"):
        return str(v_idx_entry["role"])
    if "broll" in low or "b_roll" in low:
        return "b_roll_candidate"
    if "aroll" in low or "a_roll" in low or "talk" in low:
        return "a_roll_candidate"
    # 不仅看 silence_ratio，还需具备语音动态范围 >= 7dB（防止嘈杂环境空镜持续底噪误判成口播 A-roll）
    if (
        a_stream
        and quality["silence_ratio"] < 0.55
        and float(quality.get("dyn_range_db", 0.0)) >= 7.0
        and duration >= 2.0
    ):
        return "a_roll_candidate"
    return "b_roll_candidate"


def _infer_semantic_tags(
    filename: str,
    vision_res: Dict[str, Any],
    avg_luma: Optional[float],
    v_idx_entry: Optional[Dict[str, Any]] = None,
) -> List[str]:
    tags: List[str] = []
    if v_idx_entry:
        for tg in v_idx_entry.get("semantic_tags", []) or []:
            if str(tg).strip():
                tags.append(str(tg).strip())
        if v_idx_entry.get("shot_type"):
            tags.append(str(v_idx_entry["shot_type"]).strip())
        if v_idx_entry.get("action"):
            tags.append(str(v_idx_entry["action"]).strip())

    stem = Path(filename).stem
    for tok in re.findall(r"[\u4e00-\u9fff]{2,6}|[a-zA-Z]{3,12}", stem):
        low = tok.lower()
        if low not in ("norm", "aroll", "broll", "roll", "clip", "vid", "img", "mov", "mp4"):
            tags.append(tok)
    if vision_res.get("faces"):
        tags.append("真人出镜")
    else:
        tags.append("空镜特写")
    for t in vision_res.get("texts", []):
        txt = str(t.get("text", "")).strip()
        if len(txt) >= 2:
            tags.append(txt[:10])
    if avg_luma is not None:
        if avg_luma < 85:
            tags.append("暗调质感")
        elif avg_luma > 165:
            tags.append("明亮环境")
    seen = set()
    uniq: List[str] = []
    for tg in tags:
        if tg and tg not in seen:
            seen.add(tg)
            uniq.append(tg)
    return uniq[:16]


def _infer_taboo_tags(
    filename: str,
    ocr_texts: List[str],
    v_idx_entry: Optional[Dict[str, Any]] = None,
) -> List[str]:
    tags: List[str] = []
    if v_idx_entry:
        tags.extend(str(x).strip() for x in (v_idx_entry.get("taboo_tags") or []) if str(x).strip())
    blob = (filename + " " + " ".join(ocr_texts)).lower()
    for tag, kws in TABOO_KEYWORD_MAP.items():
        if any(k.lower() in blob for k in kws) and tag not in tags:
            tags.append(tag)
    return tags


def _has_foreground_teleprompter(faces: List[Dict[str, Any]], per_frame_boxes: List[List[Dict[str, Any]]]) -> bool:
    """按单帧独立判定前景手持提词稿（消除多帧叠加误把背景招牌翻倍），并校验文字位置相对人脸尺度。"""
    if not faces or not per_frame_boxes:
        return False
    face_y_min = min(float((f.get("bbox") or {}).get("y", 0.25)) for f in faces)
    face_area = max(0.01, max(float((f.get("bbox") or {}).get("w", 0.1)) * float((f.get("bbox") or {}).get("h", 0.1)) for f in faces))
    for frame_boxes in per_frame_boxes:
        fg_boxes = [
            b for b in frame_boxes
            if max(0.22, face_y_min - 0.05) <= float(b.get("y", 0.0)) <= 0.88
            and 0.12 <= float(b.get("x", 0.0)) <= 0.85
            and len(str(b.get("text", "")).strip()) >= 3
        ]
        fg_chars = sum(len(str(b.get("text", "")).strip()) for b in fg_boxes)
        fg_area = sum(float(b.get("w", 0.0)) * float(b.get("h", 0.0)) for b in fg_boxes)
        if ((len(fg_boxes) >= 4 and fg_chars >= 28) or fg_chars >= 40) and fg_area >= max(0.025, face_area * 0.25):
            return True
    return False


def _assess_av_grades(
    filename: str,
    has_audio: bool,
    quality: Dict[str, Any],
    faces: List[Dict[str, Any]],
    per_frame_boxes: List[List[Dict[str, Any]]],
    role: str,
    v_idx_entry: Optional[Dict[str, Any]] = None,
) -> Tuple[str, str, List[str]]:
    """A2 声画分离双评级 (audio_grade × video_grade: usable | audio_only | ng)，修正 TV-range 黑帧判断。"""
    reasons: List[str] = []
    sil = float(quality.get("silence_ratio", 0.0))
    dyn = float(quality.get("dyn_range_db", 12.0))
    sharp = float(quality.get("sharpness_score", 0.0))
    luma = float(quality.get("avg_luma") or 128.0)
    luma_span = float(quality.get("luma_p99") or 200.0) - float(quality.get("luma_p1") or 20.0)

    if not has_audio or sil >= 0.85:
        audio_grade = "silent"
    elif sil >= 0.72 or (dyn > 0.0 and dyn < 6.5):
        audio_grade = "noisy"
    else:
        audio_grade = "usable"

    if v_idx_entry and v_idx_entry.get("video_grade") in ("usable", "audio_only", "ng"):
        vg = str(v_idx_entry["video_grade"])
        if v_idx_entry.get("grade_reason"):
            reasons.append(str(v_idx_entry["grade_reason"]))
        return audio_grade, vg, reasons

    fname_low = filename.lower()
    face_severed = any(
        float((f.get("bbox") or {}).get("y", 0.2)) < 0.01
        or float((f.get("bbox") or {}).get("y", 0.2)) + float((f.get("bbox") or {}).get("h", 0.2)) > 0.99
        for f in faces
    )

    is_dead_frame = (luma <= 22.0 and sharp < 10.0) or (luma_span <= 10.0 and sharp < 6.0)
    if is_dead_frame and audio_grade != "usable":
        video_grade = "ng"
        reasons.append("画面黑屏或纯色且没有可用人声，已自动跳过")
    elif "audio_only" in fname_low:
        video_grade = "audio_only"
        reasons.append("已标记只留原声、画面用特写镜头盖住")
    elif audio_grade == "usable" and role == "a_roll_candidate":
        bad = []
        if 0 < sharp < 16.0:
            bad.append("对焦太糊")
        if face_severed:
            bad.append("人像切头构图不全")
        if _has_foreground_teleprompter(faces, per_frame_boxes):
            bad.append("镜头前露出大面积提词稿")
        if (faces and luma < 32.0) or luma > 242.0:
            bad.append("光线太暗或严重发白")
        if bad:
            video_grade = "audio_only"
            reasons.append("声音能用但画面有问题（" + "、".join(bad) + "），自动留声换画面")
        else:
            video_grade = "usable"
    elif is_dead_frame:
        video_grade = "ng"
        reasons.append("画面黑屏或纯色废片，已自动跳过")
    else:
        video_grade = "usable"

    return audio_grade, video_grade, reasons


def recommend_angle(
    clips: List[Dict[str, Any]],
    track: str,
    raw_intel: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """结合素材盘点与一手客户原材 00_raw_intel.json，反推最稳妥的选题结构建议。"""
    has_aroll = any(c["suggested_role"] == "a_roll_candidate" and c.get("video_grade") != "ng" for c in clips)
    total_dur = round(sum(c["duration_sec"] for c in clips), 2)
    broll_count = sum(1 for c in clips if c["suggested_role"] == "b_roll_candidate" and c.get("video_grade") != "ng")

    pain_kws = (raw_intel or {}).get("pain_keywords", [])
    questions = (raw_intel or {}).get("customer_questions", [])
    proof_cnt = len((raw_intel or {}).get("proof_assets", []))

    if track == "store":
        if has_aroll:
            formula = "晒真实产品和凭据细节 → 亮出老板脾气和做事底线 → 让人信你愿意进店"
            hook = f"开头直接回应客人最担心的事「{questions[0][:22]}」" if questions else "开头先说一句反常识真话，或直接点破客人最怕踩的坑（例如：干这行这么多年，只守一条底线…）"
            a_level = "建信任（让人记住你靠谱）/ 打消顾虑（促人咨询进店）"
            script_type = "给进店理由 / 晒干活过程"
            viral_element = "算钱对比 / 揭秘内幕"
        else:
            formula = "借同城或行业大家关心的话题拉人 → 配高质感细节画面和实景 → 配音讲透门道 → 结尾亮出老板底线"
            hook = "第一眼给最带劲的真实特写画面，配一句让人意外的行业真话"
            a_level = "拉新（让更多同城路人刷到认识你）"
            script_type = "晒干活过程 / 聊本地同城"
            viral_element = "前后反差 / 稀奇内幕"
    else:
        if has_aroll:
            formula = "用大家最关心的话题把人拉住 → 讲具体事件和细节筛出对口观众 → 顺带立住个人观点 → 抛问题让评论区聊起来"
            hook = f"直接拿评论区大家追问最多的问题「{questions[0][:22]}」反着讲" if questions else "开头用「别再……」反常识句式，直接打掉外行常想错的误区"
            a_level = "拉新（让更多人认识你）/ 建信任（记住你的观点）"
            script_type = "聊行业看法 / 教实用知识"
            viral_element = "前后反差 / 揭秘内幕"
        else:
            formula = "开头先留悬念或抛狠数字 → 跟着配音节奏切画面和数据图 → 结尾给一句能带走的大白话总结"
            hook = "把最狠的数字或付出代价才明白的事直接放第一句"
            a_level = "拉新（让更多人刷到认识你）"
            script_type = "教实用知识 / 晒干活过程"
            viral_element = "算钱对比 / 吐槽踩坑"

    missing_alert = []
    if broll_count < 2:
        missing_alert.append("可用的细节特写和环境补拍画面偏少，后续剪辑会自动补上文字和数据图表画面，确保开头 3 秒有节奏变化")
    if not has_aroll:
        missing_alert.append("缺少清晰真人说话素材，后续会自动用文案配音或引导补录人声")
    if proof_cnt == 0 and track == "store":
        missing_alert.append("还没放进货单、称重或前后对比等实拍凭据，补拍几张会让客人更信你")

    return {
        "track": track,
        "total_raw_duration_sec": total_dur,
        "has_usable_aroll": has_aroll,
        "recommended_5a_level": a_level,
        "recommended_script_type": script_type,
        "recommended_viral_element": viral_element,
        "recommended_formula": formula,
        "recommended_hook": hook,
        "raw_pain_keywords_used": pain_kws[:6],
        "proof_assets_count": proof_cnt,
        "gaps_and_remedy": missing_alert,
    }


def _build_contact_sheet(
    clips: List[Dict[str, Any]],
    frame_paths: Dict[int, Path],
    out_jpg: Path,
) -> Optional[Path]:
    """生成 4 列等比保持宽高比的素材接触表 00_contact_sheet.jpg，方便人/VLM 一眼审片。"""
    if not clips or not frame_paths:
        return None
    cols = min(4, max(1, len(clips)))
    rows = math.ceil(len(clips) / cols)
    tw, th = 270, 480
    hdr_h = 48
    cell_h = th + hdr_h
    pad = 12
    canvas = Image.new("RGB", (cols * (tw + pad) + pad, rows * (cell_h + pad) + pad), (18, 20, 26))
    draw = ImageDraw.Draw(canvas)
    f_path = find_commercial_font(verified_only=True)
    fnt = get_cached_font(f_path, 14)

    for idx, c in enumerate(clips):
        r, col = divmod(idx, cols)
        x0 = pad + col * (tw + pad)
        y0 = pad + r * (cell_h + pad)
        draw.rectangle([x0, y0, x0 + tw, y0 + cell_h], fill=(28, 32, 42), outline=(65, 74, 92), width=1)
        fp = frame_paths.get(idx)
        if fp and fp.is_file():
            try:
                with Image.open(fp) as im:
                    im_rgb = ImageOps.exif_transpose(im).convert("RGB")
                    thumb = ImageOps.pad(im_rgb, (tw, th), method=Image.Resampling.LANCZOS, color=(14, 16, 22))
                canvas.paste(thumb, (x0, y0 + hdr_h))
            except Exception:
                pass
        vg = c.get("video_grade", "usable")
        vg_cn = {"usable": "可用", "audio_only": "仅用声音", "ng": "建议跳过"}.get(vg, vg)
        tab = ",".join(c.get("taboo_tags") or [])
        line1 = f"#{idx+1} {c['filename'][:15]} ({c['duration_sec']:.1f}s)"
        line2 = f"清晰:{c['sharpness_score']:.0f} 稳:{c['stability_score']:.2f} {vg_cn}" + (f" [{tab}]" if tab else "")
        badge_col = (250, 204, 21) if vg == "audio_only" else ((248, 113, 113) if (vg == "ng" or tab) else (226, 232, 240))
        draw.text((x0 + 6, y0 + 4), line1, font=fnt, fill=(248, 250, 252))
        draw.text((x0 + 6, y0 + 24), line2, font=fnt, fill=badge_col)

    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_jpg, quality=88)
    return out_jpg


def _load_visual_index_map(visual_index_path: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    if not visual_index_path or not visual_index_path.exists():
        return {}
    raw = read_json(visual_index_path)
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(raw, dict):
        items = raw.get("clips") or raw.get("shots") or raw
        if isinstance(items, dict):
            for k, v in items.items():
                if isinstance(v, dict):
                    out[str(k)] = v
        elif isinstance(items, list):
            for v in items:
                if isinstance(v, dict) and v.get("filename"):
                    out[str(v["filename"])] = v
    elif isinstance(raw, list):
        for v in raw:
            if isinstance(v, dict) and v.get("filename"):
                out[str(v["filename"])] = v
    return out


def build_shot_log_dict(inv: Dict[str, Any]) -> Dict[str, Any]:
    """统一构造 00_shot_log.json 数据结构（消除 inventory_media 与 run_pipeline 重复代码）。"""
    return {
        "step": "00_shot_log",
        "input_dir": inv["input_dir"],
        "shots": [
            {
                "filename": c["filename"],
                "path": c["path"],
                "role": c["suggested_role"],
                "duration_sec": c["duration_sec"],
                "width": c["width"],
                "height": c["height"],
                "rotation_deg": c.get("rotation_deg", 0),
                "orientation": c.get("orientation", "portrait"),
                "best_in_sec": c["best_in_sec"],
                "sharpness_score": c["sharpness_score"],
                "stability_score": c["stability_score"],
                "motion_speed_px": c.get("motion_speed_px", 0.0),
                "accel_jitter_px": c.get("accel_jitter_px", 0.0),
                "camera_motion": c.get("camera_motion", "static"),
                "shot_size": c.get("shot_size", "medium"),
                "action_apex_sec": c.get("action_apex_sec", 0.0),
                "usable": c.get("usable", True),
                "visual_indexed": c.get("visual_indexed", False),
                "audio_grade": c.get("audio_grade", "usable"),
                "video_grade": c.get("video_grade", "usable"),
                "taboo_tags": c.get("taboo_tags", []),
                "color_meta": c["color_meta"],
                "faces": c["faces"],
                "eye_anchor": c["eye_anchor"],
                "saliency_bbox": c["saliency_bbox"],
                "semantic_tags": c["semantic_tags"],
                "manual_tags": c["manual_tags"],
                "scene_group": c["scene_group"],
            }
            for c in inv["clips"]
        ],
    }


def inventory_directory(
    input_dir: Path,
    track: str,
    raw_intel: Optional[Dict[str, Any]] = None,
    contact_sheet_path: Optional[Path] = None,
    visual_index_path: Optional[Path] = None,
) -> Dict[str, Any]:
    files = sorted([
        p for p in input_dir.iterdir()
        if p.is_file() and p.suffix.lower() in MEDIA_EXTS and "benchmark" not in p.name.lower()
    ])
    v_index = _load_visual_index_map(visual_index_path)
    clips: List[Dict[str, Any]] = []
    ffmpeg = find_bin("ffmpeg")

    with tempfile.TemporaryDirectory(prefix="svs_inv_vis_") as td:
        td_path = Path(td)
        rep_frames: List[Path] = []
        idx_to_frames: Dict[int, List[Path]] = {}
        idx_to_frame_boxes: Dict[int, List[List[Dict[str, Any]]]] = {}

        for f in files:
            meta = ffprobe_media(f)
            streams = meta.get("streams", [])
            v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
            a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
            if not v_stream:
                continue

            dur = float(meta.get("format", {}).get("duration") or v_stream.get("duration") or 0.0)
            geom = parse_video_stream_geometry(v_stream)
            dw, dh = geom["display_width"], geom["display_height"]
            vh = detect_vfr_hdr(meta)
            r_fps, avg_fps, is_vfr = vh["r_fps"], vh["avg_fps"], vh["is_vfr"]
            color_transfer = vh["color_transfer"] or "unknown"
            color_primaries = vh["color_primaries"] or "unknown"
            color_space = vh["color_space"] or "unknown"
            pix_fmt = vh["pix_fmt"] or "unknown"
            is_hdr = vh["was_hdr"]
            is_10bit = any(k in pix_fmt for k in ("10le", "10be", "p010"))

            v_idx_entry = v_index.get(f.name) or v_index.get(f.stem)
            quality = analyze_video_quality(f, dur, dw, dh, has_audio=(a_stream is not None))
            if v_idx_entry and isinstance(v_idx_entry.get("best_in_sec"), (int, float)):
                quality["best_in_sec"] = round(max(0.0, min(max(0.0, dur - 0.5), float(v_idx_entry["best_in_sec"]))), 2)

            issues = list(quality["issues"])
            if geom["rotation_deg"] != 0:
                issues.append(f"原片带旋转角度（{geom['rotation_deg']}°），会自动扶正")
            if is_hdr:
                issues.append("手机拍的高动态高光素材，剪辑前会自动还原自然色彩不发灰")
            if is_vfr:
                issues.append("手机原片帧率有波动，会自动统一成稳定 30 帧防止音画错位")
            if dw > dh:
                issues.append(f"横屏画面（{dw}x{dh}），会自动锁定主角居中裁成竖屏")
            if min(dw, dh) < 720 or max(dw, dh) < 1080:
                issues.append(f"清晰度偏低（{dw}x{dh}），建议少用或当辅助小画面")

            role = classify_clip(f.name, a_stream, quality, dur, v_idx_entry=v_idx_entry)
            tags_meta = meta.get("format", {}).get("tags", {}) or v_stream.get("tags", {}) or {}
            ctime = str(tags_meta.get("creation_time", ""))[:10]
            luma_band = "dark" if (quality.get("avg_luma") or 128) < 85 else ("bright" if (quality.get("avg_luma") or 128) > 165 else "mid")
            scene_group = f"shoot_{ctime or 'default'}_{geom['orientation']}_{luma_band}"

            clip_idx = len(clips)
            clips.append({
                "filename": f.name,
                "path": str(f.resolve()),
                "duration_sec": round(dur, 2),
                "width": dw,
                "height": dh,
                "coded_width": geom["coded_width"],
                "coded_height": geom["coded_height"],
                "rotation_deg": geom["rotation_deg"],
                "orientation": geom["orientation"],
                "r_fps": round(r_fps, 2),
                "avg_fps": round(avg_fps, 2),
                "is_vfr": is_vfr,
                "has_audio": a_stream is not None,
                "color_meta": {
                    "color_transfer": color_transfer,
                    "color_primaries": color_primaries,
                    "color_space": color_space,
                    "pix_fmt": pix_fmt,
                    "is_hdr": is_hdr,
                    "is_10bit": is_10bit,
                },
                "quality": quality,
                "best_in_sec": quality["best_in_sec"],
                "sharpness_score": quality["sharpness_score"],
                "stability_score": quality["stability_score"],
                "motion_speed_px": quality.get("motion_speed_px", 0.0),
                "accel_jitter_px": quality.get("accel_jitter_px", 0.0),
                "camera_motion": str((v_idx_entry or {}).get("camera_motion") or quality.get("camera_motion") or "static"),
                "shot_size": str((v_idx_entry or {}).get("shot_size") or "medium"),
                "action_apex_sec": float((v_idx_entry or {}).get("action_apex_sec") or quality.get("action_apex_sec") or 0.0),
                "issues": issues,
                "suggested_role": role,
                "usable": dur >= 0.8,
                "audio_grade": "usable",
                "video_grade": "usable",
                "taboo_tags": [],
                "scene_group": scene_group,
                "faces": [],
                "eye_anchor": None,
                "saliency_bbox": None,
                "ocr_texts": [],
                "semantic_tags": [],
                "manual_tags": list((v_idx_entry or {}).get("manual_tags", [])),
                "visual_indexed": bool(v_idx_entry),
                "_v_idx_entry": v_idx_entry,
            })

            if ffmpeg and dur > 0.1:
                sample_ts = [quality["best_in_sec"]]
                if dur >= 4.0:
                    mid_ts = round(min(dur - 0.3, max(quality["best_in_sec"] + 1.2, dur * 0.55)), 2)
                    if abs(mid_ts - sample_ts[0]) >= 0.8:
                        sample_ts.append(mid_ts)
                for s_i, ts in enumerate(sample_ts):
                    rep_jpg = td_path / f"rep_{clip_idx:03d}_{s_i}.jpg"
                    run_cmd([
                        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                        "-ss", f"{ts:.2f}", "-i", str(f),
                        "-frames:v", "1", "-q:v", "3", str(rep_jpg),
                    ], check=False)
                    if rep_jpg.exists():
                        rep_frames.append(rep_jpg)
                        idx_to_frames.setdefault(clip_idx, []).append(rep_jpg)

        vis_map = inspect_images(rep_frames)
        for c_idx in range(len(clips)):
            f_list = idx_to_frames.get(c_idx, [])
            best_vr: Dict[str, Any] = {}
            frame_boxes_list: List[List[Dict[str, Any]]] = []
            seen_ocr_texts: List[str] = []
            for fp in f_list:
                vr = vis_map.get(str(fp), {})
                t_boxes = list(vr.get("texts", []) or [])
                frame_boxes_list.append(t_boxes)
                for tb in t_boxes:
                    txt_s = str(tb.get("text", "")).strip()
                    if txt_s and txt_s not in seen_ocr_texts:
                        seen_ocr_texts.append(txt_s)
                if not best_vr or (vr.get("faces") and not best_vr.get("faces")):
                    best_vr = vr
            faces = best_vr.get("faces", [])
            clips[c_idx]["faces"] = faces
            ve = clips[c_idx].get("_v_idx_entry")
            if not (ve and ve.get("shot_size")):
                if faces and isinstance(faces[0].get("bbox"), dict):
                    f_h = float(faces[0]["bbox"].get("h", 0.0))
                    clips[c_idx]["shot_size"] = "closeup" if f_h >= 0.24 else ("medium" if f_h >= 0.11 else "wide")
                else:
                    sal = best_vr.get("saliency")
                    s_area = float(sal.get("w", 0.0)) * float(sal.get("h", 0.0)) if isinstance(sal, dict) else 0.2
                    clips[c_idx]["shot_size"] = "closeup" if s_area >= 0.35 else ("medium" if s_area >= 0.12 else "wide")
            if faces:
                f0 = faces[0]
                clips[c_idx]["eye_anchor"] = {
                    "cx": round(float(f0.get("eye_cx", 0.5)), 4),
                    "cy": round(float(f0.get("eye_cy", 0.36)), 4),
                    "eye_open_ratio": round(float(f0.get("eye_open_ratio", 0.25)), 4),
                }
            clips[c_idx]["saliency_bbox"] = best_vr.get("saliency")
            idx_to_frame_boxes[c_idx] = frame_boxes_list
            clips[c_idx]["ocr_texts"] = seen_ocr_texts
            clips[c_idx]["semantic_tags"] = _infer_semantic_tags(
                clips[c_idx]["filename"], best_vr, clips[c_idx]["quality"].get("avg_luma"), v_idx_entry=ve
            )
            clips[c_idx]["taboo_tags"] = _infer_taboo_tags(clips[c_idx]["filename"], seen_ocr_texts, v_idx_entry=ve)

        primary_frames = {ci: fl[0] for ci, fl in idx_to_frames.items() if fl}
        for c_idx, c in enumerate(clips):
            ve = c.pop("_v_idx_entry", None)
            ag, vg, grade_reasons = _assess_av_grades(
                c["filename"],
                c["has_audio"],
                c["quality"],
                c["faces"],
                idx_to_frame_boxes.get(c_idx, []),
                c["suggested_role"],
                v_idx_entry=ve,
            )
            c["audio_grade"] = ag
            c["video_grade"] = vg
            c["issues"].extend(grade_reasons)
            if vg == "ng":
                c["usable"] = False

        if contact_sheet_path is not None:
            _build_contact_sheet(clips, primary_frames, contact_sheet_path)

    recommendation = recommend_angle(clips, track, raw_intel=raw_intel)
    return {
        "input_dir": str(input_dir.resolve()),
        "clip_count": len(clips),
        "clips": clips,
        "contact_sheet": str(contact_sheet_path.resolve()) if contact_sheet_path and contact_sheet_path.exists() else None,
        "visual_index_used": bool(v_index),
        "recommendation": recommendation,
    }


def render_markdown_summary(data: Dict[str, Any]) -> str:
    rec = data["recommendation"]
    lines = [
        "# 素材盘点与选题思路建议（大白话版）",
        "",
        f"- **盘点素材总数**：{data['clip_count']} 条（累计原始时长 {rec['total_raw_duration_sec']} 秒）",
        f"- **适用方向**：{'帮实体店拉本地客人（同城获客）' if rec['track']=='store' else '帮个人账号涨粉引流'}",
        f"- **这条片子适合干嘛用**：{rec['recommended_5a_level']}",
        f"- **建议怎么拍的类型**：{rec.get('recommended_script_type', '晒干活过程 / 聊行业看法')}",
        f"- **建议靠什么吸引人**：{rec.get('recommended_viral_element', '算钱对比 / 前后反差')}",
        f"- **整条串起来怎么讲**：{rec['recommended_formula']}",
        f"- **开头 3 秒抓人建议**：{rec['recommended_hook']}",
        "",
        "## 素材明细与画面体检表",
        "",
        "| 文件名 | 尺寸/旋转 | 时长 | 色彩/帧率 | 最佳起剪点 | 清晰度/稳度 | 画面里有什么 | 建议当什么用 | 体检提示 |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :--- | :--- |",
    ]
    for c in data["clips"]:
        diag = "；".join(c["issues"]) if c["issues"] else "正常可用"
        hdr_tag = "高动态(自动还原)" if c["color_meta"]["is_hdr"] else "标准"
        vfr_tag = "变帧(需统一)" if c["is_vfr"] else "稳帧"
        tags_str = ",".join(c["semantic_tags"][:4]) or "-"
        face_str = f"{len(c['faces'])}人出镜" if c["faces"] else "无人物正脸"
        dim_str = f"{c['width']}x{c['height']}" + (f"({c.get('rotation_deg',0)}°)" if c.get("rotation_deg") else "")
        lines.append(
            f"| `{c['filename']}` | {dim_str} | {c['duration_sec']}s | {hdr_tag}/{vfr_tag} | "
            f"{c['best_in_sec']:.2f}s | {c['sharpness_score']:.0f}/{c['stability_score']:.2f} | "
            f"{face_str}({tags_str}) | "
            f"{'真人出镜说话' if c['suggested_role']=='a_roll_candidate' else '细节特写/环境补拍'} | {diag} |"
        )
    if rec["gaps_and_remedy"]:
        lines += ["", "## 素材缺口与自动补救建议"] + [f"- {g}" for g in rec["gaps_and_remedy"]]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="深度素材盘点、分镜日志与多模态视觉索引融合")
    parser.add_argument("--input-dir", required=True, help="原始素材文件夹路径")
    parser.add_argument("--output", required=True, help="输出 00_inventory.json 路径")
    parser.add_argument("--track", choices=["store", "creator"], default="store", help="门店轨或博主轨")
    parser.add_argument("--raw-intel", help="可选：00_raw_intel.json 路径")
    parser.add_argument("--visual-index", help="可选：00_visual_index.json 路径（多模态看图真实语义/禁忌标注）")
    args = parser.parse_args()

    out_json = Path(args.output)
    raw_intel = None
    intel_path = Path(args.raw_intel) if args.raw_intel else (out_json.parent / "00_raw_intel.json")
    if intel_path.exists():
        raw_intel = read_json(intel_path)

    vis_idx_path = Path(args.visual_index) if args.visual_index else (out_json.parent / "00_visual_index.json")
    contact_sheet = out_json.parent / "00_contact_sheet.jpg"
    inv = inventory_directory(
        Path(args.input_dir),
        args.track,
        raw_intel=raw_intel,
        contact_sheet_path=contact_sheet,
        visual_index_path=vis_idx_path if vis_idx_path.exists() else None,
    )
    write_json(out_json, inv)

    shot_log = build_shot_log_dict(inv)
    shot_log_path = out_json.parent / "00_shot_log.json"
    write_json(shot_log_path, shot_log)

    out_md = out_json.with_suffix(".md")
    out_md.write_text(render_markdown_summary(inv), encoding="utf-8")
    print(f"[inventory] 已盘点 {inv['clip_count']} 条素材 -> {out_json} & {shot_log_path}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
[协作闸门、风格复刻洁净室与完工自动清理守卫]
四合一高内聚模块，严守 KISS 不碎拆：
1. record-stop / audit-stops : 3 必停点打扰审计账本 (stop1_script / stop2_blind_audio / stop3_final，预算=3)
2. lock / verify / approve-final : 方案指纹哈希锁 (approval_lock.json) + 双态人工签字 (MACHINE_PASS_PENDING_HUMAN -> APPROVED)
3. replication-diff : 风格复刻洁净室 (DCT pHash <= 6 禁画面复用 + 12字OCR禁文案照搬) + 7 维客观偏差 + 乱序 A/B/C 盲测页
4. tidy : 完工后一键同步成品至 out/ 并彻底清理全部无用过程临时文件（确保自包含导出工程零断链）
"""

from __future__ import annotations

import argparse
import hashlib
import html
import math
import re
import secrets
import shutil
import statistics
import subprocess
import sys
import tempfile
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from common import (
    DEFAULT_FPS,
    SCENE_CUT_THRESHOLD,
    SUBTITLE_DEFAULT_Y_CENTER,
    compute_bt709_luma,
    ffprobe_media,
    find_bin,
    find_commercial_font,
    maybe_reexec_in_venv,
    parse_fps,
    read_json,
    run_cmd,
    sha256_file,
    write_json,
)

if __name__ == "__main__":
    maybe_reexec_in_venv()

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from step2_transcribe import _clean_zh_text
from step3_lock_audio import detect_bgm_beats
from vision_inspector import inspect_images

STOP_TYPES = ("stop1_script", "stop2_blind_audio", "stop3_final")
USER_TYPES = (
    "store_from_zero",
    "creator_talking",
    "footage_organizer",
    "faceless_visual",
    "post_review",
)
BUDGET = 3
LOCK_FILENAME = "approval_lock.json"

TEMP_SUBDIRS = (
    "_render_final",
    "_render_preview",
    "01_normalized",
    "01_code_scenes",
    "02_tts_segments",
    "__pycache__",
)

TEMP_PROCESS_FILES = (
    "02_tts_voice.wav",
    "08_voice_denoised.wav",
    "08_premix_raw.wav",
    "08_premix_nosfx_raw.wav",
    "08_mixed_master_adj.wav",
    "output_preview.mp4",
)

DEEP_CLEAN_SUBDIRS = ("04_generated_broll",)
DEEP_CLEAN_FILES = (
    "03_locked_voice.wav",
    "03_locked_bgm.wav",
    "06_sfx_track.wav",
    "08_stem_nosfx.wav",
    "08_voice_master.wav",
    "08_bgm_ducked.wav",
    "08_sfx_master.wav",
    "08_mixed_master.wav",
)

DELIVERABLE_SYNC_FILES = (
    "output_final.mp4",
    "09_cover.jpg",
    "09_cover_3x4.jpg",
    "09_ui_safe_preview.jpg",
    "09_cover_360px_feed.jpg",
    "09_cover_land_4k.png",
    "09_cover_port_4k.png",
    "09_cover_v1.jpg",
    "09_cover_v2.jpg",
    "09_cover_v3.jpg",
    "09_hook_v1.mp4",
    "09_hook_v2.mp4",
    "09_hook_v3.mp4",
    "09_title_cover.md",
    "09_title_cover.json",
    "09_publish_copy_pack.md",
    "09_publish_copy_pack.json",
    "09_hook_variants.json",
    "05_subtitles.srt",
    "05_subtitle_check.txt",
    "03_blind_audio.m4a",
    "00_contact_sheet.jpg",
    "00_script_lint.md",
    "00_口播纯享稿.txt",
    "00_拍摄执行方案.md",
    "00_compliance_report.md",
    "00_compliance_report.json",
    "asset_license_manifest.json",
    "04_edl.json",
    "04_source_review.json",
    "08_locked_audio_receipt.json",
    "render_profile.json",
    "10_qa_report.md",
    "10_qa_report.json",
    "10_animation_audit.json",
    "10_blind_review_pack.md",
    "10_action_strips.jpg",
    "10_code_verify_evidence.json",
    "00_code_spec.json",
    "SPEC.md",
    "STRUCTURE.md",
    "VERIFY.md",
    "decisions_made.md",
    "11_delivery_summary.md",
    "00_progress_card.json",
    "00_进度看板.md",
    "review_player.html",
)


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _load_lock_state(pipeline_dir: Path) -> Dict[str, Any]:
    p = pipeline_dir / LOCK_FILENAME
    if p.is_file():
        try:
            return read_json(p)
        except Exception:
            pass
    return {
        "version": 1,
        "created_at": _now_iso(),
        "interruptions": [],
        "plan_sha256": None,
        "locked_at": None,
        "human_approved": False,
        "approved_at": None,
        "approval_note": "",
    }


def compute_plan_digest(pipeline_dir: Path) -> str:
    """对已定版的 03~08（及纯代码模式下的 00_code_spec.json）全核心流水线决策工件计算组合 SHA-256 指纹。"""
    h = hashlib.sha256()
    if (pipeline_dir / "00_code_spec.json").is_file():
        h.update(b"00_code_spec.json")
        h.update((pipeline_dir / "00_code_spec.json").read_bytes())
    for name in (
        "03_audio_events.json",
        "04_edl.json",
        "05_subtitles.json",
        "06_packaging.json",
        "07_color_plan.json",
        "08_mix_metrics.json",
        "04_source_review.json",
        "asset_license_manifest.json",
    ):
        p = pipeline_dir / name
        h.update(name.encode("utf-8"))
        if p.is_file():
            h.update(p.read_bytes())
    return h.hexdigest()


def package_digest(directory: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != ".DS_Store":
            digest.update(path.relative_to(directory).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def record_stop(pipeline_dir: Path, stop_type: str, summary: str = "", rehearsal: bool = False) -> Dict[str, Any]:
    if stop_type not in STOP_TYPES:
        raise ValueError(f"stop_type 必须为 {STOP_TYPES} 之一")
    st = _load_lock_state(pipeline_dir)
    st.setdefault("interruptions", []).append({
        "type": stop_type,
        "summary": summary,
        "at": _now_iso(),
        "rehearsal": bool(rehearsal),
        "source": "human_interaction",
    })
    write_json(pipeline_dir / LOCK_FILENAME, st)
    return st


def record_milestone(pipeline_dir: Path, step: str, summary: str) -> None:
    path = pipeline_dir / "pipeline_progress.json"
    progress = read_json(path) if path.is_file() else {}
    progress[step] = {"status": summary, "at": _now_iso()}
    write_json(path, progress)


def audit_stops(pipeline_dir: Path, require_all: bool = False) -> Dict[str, Any]:
    st = _load_lock_state(pipeline_dir)
    items = [item for item in st.get("interruptions", [])
             if item.get("source") == "human_interaction" and not item.get("rehearsal")]
    types = [i.get("type") for i in items]
    over = len(items) > BUDGET
    dup = len(types) != len(set(types))
    missing = [t for t in STOP_TYPES if t not in types] if require_all else []
    passed = (not over) and (not dup) and (not missing)
    return {
        "passed": passed,
        "count": len(items),
        "budget": BUDGET,
        "types": types,
        "over_budget": over,
        "duplicate_stops": dup,
        "missing_stops": missing,
    }


def lock_plan(pipeline_dir: Path, note: str = "用户拍板锁定方案") -> Dict[str, Any]:
    st = _load_lock_state(pipeline_dir)
    digest = compute_plan_digest(pipeline_dir)
    edl = read_json(pipeline_dir / "04_edl.json") if (pipeline_dir / "04_edl.json").is_file() else {}
    final_mp4 = pipeline_dir / "output_final.mp4"
    st["plan_sha256"] = digest
    st["output_final_sha256"] = sha256_file(final_mp4) if final_mp4.is_file() else None
    st["locked_at"] = _now_iso()
    st["clip_count"] = int(edl.get("clip_count", 0))
    st["duration_sec"] = float(edl.get("total_duration_sec", 0.0))
    st["lock_note"] = note
    st["human_approved"] = False
    st["approved_at"] = None
    write_json(pipeline_dir / LOCK_FILENAME, st)
    return st


def verify_lock(pipeline_dir: Path) -> Tuple[int, str, Dict[str, Any]]:
    st = _load_lock_state(pipeline_dir)
    saved = st.get("plan_sha256")
    if not saved:
        return 2, "尚未执行方案指纹锁（未落 approval_lock.json）", st
    cur = compute_plan_digest(pipeline_dir)
    if cur != saved:
        return 1, f"方案在拍板锁定后已被改动：锁={saved[:12]} != 当前={cur[:12]}，请重新预览并拍板", st
    saved_mp4_sha = st.get("output_final_sha256")
    final_mp4 = pipeline_dir / "output_final.mp4"
    if saved_mp4_sha and final_mp4.is_file():
        cur_mp4_sha = sha256_file(final_mp4)
        if cur_mp4_sha != saved_mp4_sha:
            return 1, f"成片 output_final.mp4 在锁版后被替换/篡改（{cur_mp4_sha[:12]} != {saved_mp4_sha[:12]}）", st
    return 0, f"方案锁有效 (sha={cur[:12]}, 锁定于 {st.get('locked_at')})", st


def approve_final(
    pipeline_dir: Path,
    note: str = "",
    reviewed_checks: tuple[str, ...] = (),
    out_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    qa_p = pipeline_dir / "10_qa_report.json"
    if not qa_p.is_file():
        raise FileNotFoundError("未找到 10_qa_report.json，请先运行自动+黑盒质检。")
    qa = read_json(qa_p)
    if not qa.get("all_passed", qa.get("machine_passed")):
        raise RuntimeError("必检项尚未通过，禁止人工终审签字。")
    required = set(qa.get("required_manual_checks", []))
    if not required <= set(reviewed_checks) or (required and not note.strip()):
        raise RuntimeError(f"请完成并记录人工审查后签字：{', '.join(sorted(required))}")

    final_mp4 = pipeline_dir / "output_final.mp4"
    if not final_mp4.is_file():
        raise FileNotFoundError("缺少 output_final.mp4，无法签字。")

    st = _load_lock_state(pipeline_dir)
    cur_digest = compute_plan_digest(pipeline_dir)
    cur_mp4_sha = sha256_file(final_mp4)
    if qa.get("plan_sha256") != cur_digest or qa.get("output_final_sha256") != cur_mp4_sha:
        raise RuntimeError("质检报告与当前方案或成片指纹不匹配，请重新质检再签字。")
    for target, expected in qa.get("required_package_hashes", {}).items():
        package = pipeline_dir / f"{target}_draft"
        if not package.is_dir() or package_digest(package) != expected:
            raise RuntimeError(f"{target} 工程与质检版本不一致，请重新质检再签字。")
    from source_review import source_review_status
    provenance_path = pipeline_dir / "04_source_review.json"
    if provenance_path.is_file() and source_review_status(read_json(provenance_path)) == "FAIL":
        raise RuntimeError("主张来源已缺失或变更，请更新来源并重新质检。")
    if (pipeline_dir / "asset_license_manifest.json").is_file():
        from independent_verifier import verify_compliance_and_license_blackbox
        if not verify_compliance_and_license_blackbox(pipeline_dir)["passed"]:
            raise RuntimeError("授权原件或实际资产已变更，请重新质检。")
    if st.get("plan_sha256") and st["plan_sha256"] != cur_digest:
        raise RuntimeError(f"当前 EDL/字幕/包装/音色方案已被修改 (sha={cur_digest[:12]} != 锁={st['plan_sha256'][:12]})，请先重新渲染并质检。")
    if st.get("output_final_sha256") and st["output_final_sha256"] != cur_mp4_sha:
        raise RuntimeError("output_final.mp4 与锁定指纹不一致，禁止人工签字。")
    if not st.get("plan_sha256"):
        st["plan_sha256"] = cur_digest
        st["locked_at"] = _now_iso()
    st["output_final_sha256"] = cur_mp4_sha

    st["human_approved"] = True
    st["approved_at"] = _now_iso()
    st["approval_note"] = note
    st["reviewed_checks"] = sorted(set(reviewed_checks))
    st["export_mode"] = qa.get("export_mode", "auto")
    st["required_package_hashes"] = qa.get("required_package_hashes", {})
    write_json(pipeline_dir / LOCK_FILENAME, st)

    qa["approval_status"] = "APPROVED"
    qa["pending_manual_checks"] = []
    if qa.get("deliverables", {}).get("mp4", {}).get("status") == "PENDING_REVIEW":
        qa["deliverables"]["mp4"]["status"] = "PASS"
    if "jianying_import" in reviewed_checks and "jianying" in qa.get("deliverables", {}):
        qa["deliverables"]["jianying"]["host_import"] = "USER_VERIFIED"
    qa["human_approved_at"] = st["approved_at"]
    qa["human_approval_note"] = note
    write_json(qa_p, qa)

    md_p = pipeline_dir / "10_qa_report.md"
    if md_p.is_file():
        txt = md_p.read_text(encoding="utf-8")
        for state in ("MACHINE_PASS_PENDING_HUMAN", "REVIEW_REQUIRED"):
            txt = txt.replace(f"🟡 **待人工终审确认 ({state})**", "✅ **全部自动检查与人工终审已通过**")
        txt = txt.replace("MACHINE_PASS_PENDING_HUMAN", "已通过全部检查")
        txt = txt.replace("REVIEW_REQUIRED", "已人工复核")
        for pend_banner in (
            "🟡 **全部必检通过，待人工终审确认 (APPROVED)**",
            "🟡 **全部必检通过，待人工终审确认**",
            "🟡 **全部机检通过，待人工三项终审签字 (APPROVED)**",
            "🟡 **全部机检通过，待人工三项终审签字**",
            "🟡 **自动检查已过，待您最后看一眼确认**",
            "✅ **机检与人工终审全部通过 (APPROVED)**",
            "✅ **机检与人工终审完成 (APPROVED)**",
        ):
            txt = txt.replace(pend_banner, "✅ **全部自动检查与人工终审已通过**")
        md_p.write_text(txt, encoding="utf-8")

    # 同步刷新大白话实时进度看板为「已全部完成，随时可发布」
    if (pipeline_dir / "00_progress_card.json").is_file() or (pipeline_dir / "04_edl.json").is_file():
        render_progress_card(pipeline_dir, write_files=True)

    # 同步最新审批结果至 out/ 目录，并在 tidy 已先执行时同步刷新归档清单哈希
    target_out = out_dir or (pipeline_dir.parent / "out")
    archived_mp4 = target_out / final_mp4.name
    if archived_mp4.is_file() and sha256_file(archived_mp4) == cur_mp4_sha:
        shutil.copy2(qa_p, target_out / "10_qa_report.json")
        if md_p.is_file():
            shutil.copy2(md_p, target_out / "10_qa_report.md")
        updated_out_docs: List[str] = []
        for prog_fn in ("00_progress_card.json", "00_进度看板.md"):
            prog_src = pipeline_dir / prog_fn
            if prog_src.is_file():
                shutil.copy2(prog_src, target_out / prog_fn)
                updated_out_docs.append(prog_fn)
        pending_phrases = (
            "待人工终审确认",
            "自动检查全过，等你确认一眼",
            "自动检查全过，等你核对人工项",
            "自动检查全部通过，等你确认一眼即可发布",
            "自动检查通过，请核对人工复查项后确认",
        )
        for doc_name in ("11_delivery_summary.md", "decisions_made.md"):
            for doc_p in (pipeline_dir / doc_name, target_out / doc_name):
                if doc_p.is_file():
                    dtxt = doc_p.read_text(encoding="utf-8")
                    for phrase in pending_phrases:
                        dtxt = dtxt.replace(phrase, "已通过全部检查并人工确认")
                    dtxt = re.sub(r"\bMACHINE_PASS_PENDING_HUMAN\b", "已通过全部检查", dtxt)
                    dtxt = re.sub(r"\bREVIEW_REQUIRED\b", "已人工复核", dtxt)
                    dtxt = re.sub(r"\bAPPROVED\b", "已通过全部检查并人工确认", dtxt)
                    doc_p.write_text(dtxt, encoding="utf-8")
                    if doc_p.parent == target_out:
                        updated_out_docs.append(doc_name)
        receipt_p = target_out / "archive_receipt.json"
        if receipt_p.is_file():
            receipt = read_json(receipt_p)
            files_map = receipt.setdefault("files", {})
            for doc_name in updated_out_docs:
                out_doc_p = target_out / doc_name
                if out_doc_p.is_file() and doc_name in files_map:
                    files_map[doc_name] = sha256_file(out_doc_p)
            write_json(receipt_p, receipt)
    return st


def verify_archive(out_dir: Path) -> dict[str, Any]:
    receipt = read_json(out_dir / "archive_receipt.json")
    missing, changed = [], []
    for name, expected in receipt["files"].items():
        path = out_dir / name
        if not path.is_file():
            missing.append(name)
        elif sha256_file(path) != expected:
            changed.append(name)
    qa_file = out_dir / "10_qa_report.json"
    if qa_file.is_file():
        qa = read_json(qa_file)
        if (qa.get("output_final_sha256") != receipt["files"].get("output_final.mp4")
                or qa.get("plan_sha256") != receipt["plan_sha256"]):
            changed.append(qa_file.name)
    return {"passed": "output_final.mp4" in receipt["files"] and not missing and not changed,
            "missing": missing, "changed": changed, "files": len(receipt["files"])}


# ------------------------------------------------------------------
# 风格复刻洁净室 + 7 维客观偏差 + 乱序盲测页
# ------------------------------------------------------------------

def _frame_phash_64(gray_32: np.ndarray) -> int:
    try:
        from scipy.fft import dctn
        dct = dctn(gray_32.astype(np.float32), norm="ortho")
    except Exception:
        # 纯 numpy 1D DCT 分离回退
        n = 32
        k = np.arange(n)[:, None]
        x = np.arange(n)[None, :]
        c = np.cos(np.pi * (2 * x + 1) * k / (2 * n))
        c[0, :] *= 1.0 / math.sqrt(n)
        c[1:, :] *= math.sqrt(2.0 / n)
        dct = c @ gray_32.astype(np.float32) @ c.T
    ac_coeffs = dct[:8, :8].ravel()[1:]
    med = float(np.median(ac_coeffs))
    bits = 0
    for b in (dct[:8, :8].ravel() > med):
        bits = (bits << 1) | int(bool(b))
    return bits


def _hamming_dist(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def _rgb_to_lab_mean(rgb: np.ndarray) -> Tuple[float, float, float]:
    arr = rgb.astype(np.float32) / 255.0
    lin = np.where(arr <= 0.04045, arr / 12.92, ((arr + 0.055) / 1.055) ** 2.4)
    r, g, b = lin[:, 0], lin[:, 1], lin[:, 2]
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = (0.2126 * r + 0.7152 * g + 0.0722 * b) / 1.00000
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    eps = 0.008856
    fx = np.where(x > eps, np.cbrt(x), 7.787 * x + 16 / 116)
    fy = np.where(y > eps, np.cbrt(y), 7.787 * y + 16 / 116)
    fz = np.where(z > eps, np.cbrt(z), 7.787 * z + 16 / 116)
    L = float(np.mean(116 * fy - 16))
    a = float(np.mean(500 * (fx - fy)))
    bv = float(np.mean(200 * (fy - fz)))
    return L, a, bv


def _analyze_video_profile(video_path: Path, tmp_dir: Path, tag: str) -> Dict[str, Any]:
    ffmpeg = find_bin("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("需要 ffmpeg 执行风格复刻对比分析。")

    frames_dir = tmp_dir / f"frames_{tag}"
    frames_dir.mkdir(parents=True, exist_ok=True)
    run_cmd([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(video_path),
        "-vf", "fps=1,scale=540:960:force_original_aspect_ratio=increase,crop=540:960",
        "-q:v", "3", str(frames_dir / "f_%04d.jpg"),
    ])
    frame_files = sorted(frames_dir.glob("f_*.jpg"))

    phashes: List[int] = []
    lumas: List[float] = []
    sats: List[float] = []
    text_labs: List[Tuple[float, float, float]] = []
    vis_map = inspect_images(frame_files)
    ocr_ys: List[float] = []
    ocr_stream: List[str] = []

    for fp in frame_files:
        with Image.open(fp) as im:
            g32 = np.asarray(im.convert("L").resize((32, 32), Image.Resampling.BILINEAR))
            rgb = np.asarray(im.convert("RGB"), dtype=np.float32)
            hsv = np.asarray(im.convert("HSV"), dtype=np.float32)
        phashes.append(_frame_phash_64(g32))
        luma = compute_bt709_luma(rgb)
        lumas.append(float(np.mean(luma)))
        sats.append(float(np.mean(hsv[:, :, 1])))

        vr = vis_map.get(str(fp), {})
        for t in vr.get("texts") or []:
            txt = _clean_zh_text(str(t.get("text", "")))
            if txt:
                ocr_stream.append(txt)
            ty = float(t.get("y", 0.0))
            if ty >= 0.48:
                ocr_ys.append(ty * 1920.0)
                x0 = max(0, int(float(t["x"]) * 540))
                x1 = min(540, max(x0 + 4, int((float(t["x"]) + float(t["w"])) * 540)))
                y0 = max(0, int(float(t["y"]) * 960))
                y1 = min(960, max(y0 + 4, int((float(t["y"]) + float(t["h"])) * 960)))
                roi_arr = rgb[y0:y1, x0:x1]
                roi = roi_arr.reshape(-1, 3)
                if len(roi) > 8 and roi_arr.shape[0] >= 3 and roi_arr.shape[1] >= 3:
                    roi_l_2d = compute_bt709_luma(roi_arr)
                    border_l = np.concatenate([roi_l_2d[0, :], roi_l_2d[-1, :], roi_l_2d[:, 0], roi_l_2d[:, -1]])
                    bg_l = float(np.mean(border_l))
                    roi_l = roi_l_2d.ravel()
                    # 根据边缘背景明暗自适应采样：亮底采深色字（25%低分位），暗底采亮色字（75%高分位）
                    if bg_l >= 135.0:
                        fg_px = roi[roi_l <= np.percentile(roi_l, 25)]
                    else:
                        fg_px = roi[roi_l >= np.percentile(roi_l, 75)]
                    if len(fg_px) > 0:
                        text_labs.append(_rgb_to_lab_mean(fg_px))

    # 切镜检测计算中位镜长 & 前 3 秒切镜数
    sc_res = run_cmd([
        ffmpeg, "-hide_banner", "-i", str(video_path),
        "-vf", f"select='gt(scene,{SCENE_CUT_THRESHOLD})',showinfo", "-f", "null", "-",
    ], check=False)
    cut_times = sorted(set(float(m) for m in re.findall(r"pts_time:([0-9.]+)", sc_res.stderr)))
    probe = ffprobe_media(video_path)
    dur = float(probe.get("format", {}).get("duration") or max(1.0, len(frame_files)))
    all_bounds = [0.0] + [t for t in cut_times if 0.25 < t < dur - 0.25] + [dur]
    shot_durs = [b - a for a, b in zip(all_bounds, all_bounds[1:]) if b - a >= 0.2]
    med_shot = round(statistics.median(shot_durs) if shot_durs else dur, 2)
    cuts_3s = sum(1 for t in cut_times if 0.1 <= t <= 3.1)

    wav_p = tmp_dir / f"{tag}.wav"
    run_cmd([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(video_path), "-vn", "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "2",
        str(wav_p),
    ], check=False)
    bpm = 120.0
    if wav_p.is_file() and wav_p.stat().st_size > 2048:
        bpm = float(detect_bgm_beats(wav_p).get("bpm", 120.0))

    avg_lab = (
        tuple(round(sum(x[k] for x in text_labs) / len(text_labs), 1) for k in range(3))
        if text_labs else (95.0, 0.0, 0.0)
    )
    return {
        "video": str(video_path.resolve()),
        "duration_sec": round(dur, 2),
        "phashes": phashes,
        "ocr_joined": "".join(ocr_stream),
        "median_shot_sec": med_shot,
        "first_3s_cuts": cuts_3s,
        "sub_y_px": round(statistics.median(ocr_ys), 1) if ocr_ys else float(SUBTITLE_DEFAULT_Y_CENTER),
        "mean_luma": round(statistics.mean(lumas), 1) if lumas else 128.0,
        "mean_sat": round(statistics.mean(sats), 1) if sats else 64.0,
        "bpm": round(bpm, 1),
        "sub_lab": avg_lab,
    }


def run_replication_diff(
    ref_mp4: Path,
    out_mp4: Path,
    out_dir: Path,
    contrast_mp4: Optional[Path] = None,
) -> Dict[str, Any]:
    """执行风格复刻洁净室防抄袭门禁 (pHash/OCR) + 7 维客观复刻偏差 + 乱序盲测页。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="svs_repdiff_") as td:
        td_p = Path(td)
        ref = _analyze_video_profile(ref_mp4, td_p, "ref")
        out = _analyze_video_profile(out_mp4, td_p, "out")

    # 1. Clean-Room 洁净室防抄袭门禁
    min_hamming = 64
    for ph_r in ref["phashes"]:
        for ph_o in out["phashes"]:
            d = _hamming_dist(ph_r, ph_o)
            if d < min_hamming:
                min_hamming = d

    ref_s = ref["ocr_joined"]
    out_s = out["ocr_joined"]
    ocr_12_hits: List[str] = []
    if len(ref_s) >= 12 and len(out_s) >= 12:
        for i in range(0, len(ref_s) - 11):
            win = ref_s[i : i + 12]
            if win in out_s:
                ocr_12_hits.append(win)
                break

    phash_block = bool(ref["phashes"] and out["phashes"] and min_hamming <= 6)
    ocr_block = len(ocr_12_hits) > 0
    clean_room_block = phash_block or ocr_block

    # 2. 7 维客观复刻偏差表（JSON 保持兼容字段，Markdown 报告用大白话表达）
    de = math.sqrt(sum((a - b) ** 2 for a, b in zip(ref["sub_lab"], out["sub_lab"])))
    dims = [
        {"dim": "中位镜长 (s)", "display_dim": "单个画面平均停留秒数", "ref": ref["median_shot_sec"], "out": out["median_shot_sec"],
         "ok": abs(out["median_shot_sec"] - ref["median_shot_sec"]) <= max(0.5, ref["median_shot_sec"] * 0.20), "tol": "±20%"},
        {"dim": "前 3s 切镜次数", "display_dim": "前 3 秒换画面次数", "ref": ref["first_3s_cuts"], "out": out["first_3s_cuts"],
         "ok": abs(out["first_3s_cuts"] - ref["first_3s_cuts"]) <= 1, "tol": "±1 次"},
        {"dim": "字幕重心 Y (px)", "display_dim": "字幕上下高度位置", "ref": ref["sub_y_px"], "out": out["sub_y_px"],
         "ok": abs(out["sub_y_px"] - ref["sub_y_px"]) <= 40.0, "tol": "±40 像素"},
        {"dim": "音频节奏 BPM", "display_dim": "背景音乐节拍速度", "ref": ref["bpm"], "out": out["bpm"],
         "ok": abs(out["bpm"] - ref["bpm"]) <= max(8.0, ref["bpm"] * 0.10), "tol": "±10%"},
        {"dim": "画面平均亮度", "display_dim": "画面整体明暗度", "ref": ref["mean_luma"], "out": out["mean_luma"],
         "ok": abs(out["mean_luma"] - ref["mean_luma"]) <= 18.0, "tol": "±18"},
        {"dim": "画面饱和度均值", "display_dim": "画面色彩鲜艳度", "ref": ref["mean_sat"], "out": out["mean_sat"],
         "ok": abs(out["mean_sat"] - ref["mean_sat"]) <= 24.0, "tol": "±24"},
        {"dim": "字幕字色 ΔE", "display_dim": "字幕颜色接近度", "ref": "参考字幕主色", "out": f"色差={de:.1f}",
         "ok": de <= 15.0, "tol": "偏差 ≤ 15"},
    ]

    report = {
        "step": "replication_diff",
        "clean_room_passed": not clean_room_block,
        "clean_room_block": clean_room_block,
        "min_phash_hamming": min_hamming,
        "phash_block": phash_block,
        "ocr_12char_overlap_hits": ocr_12_hits,
        "ocr_block": ocr_block,
        "dimensions_matched": sum(1 for d in dims if d["ok"]),
        "dimensions_total": len(dims),
        "dimensions": dims,
    }
    write_json(out_dir / "replication_diff.json", report)

    md_lines = [
        "# 风格参考防抄袭与 7 项视觉节奏对照报告",
        "",
        f"- **原创防抄袭检查**：{'❌ 未通过（存在画面雷同或连续 12 字台词重合风险）' if clean_room_block else '✅ 通过（原创画面与文案）'}（最小画面差异值=`{min_hamming}`，连续 12 字重合处=`{len(ocr_12_hits)}`处）",
        f"- **风格接近度**：7 项关键指标里有 {report['dimensions_matched']}/{report['dimensions_total']} 项落在合理接近范围内",
        "",
        "| 对比项目 | 参考原片 | 我方成片 | 允许误差范围 | 是否达标 |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]
    for d in dims:
        md_lines.append(f"| {d['display_dim']} | {d['ref']} | {d['out']} | {d['tol']} | {'✅' if d['ok'] else '⚠️'} |")
    (out_dir / "replication_diff.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    # 3. 乱序 A/B/C 风格盲测 HTML 页（使用真随机洗牌并将答案分离存至独立 answer_key JSON，绝不内嵌剧透）
    samples = [("参考风格原片 (Reference)", ref_mp4), ("我方复刻成片 (Ours)", out_mp4)]
    if contrast_mp4 and contrast_mp4.is_file():
        samples.append(("异风格对照组 (Contrast)", contrast_mp4))
    secrets.SystemRandom().shuffle(samples)

    cards_html = []
    answer_mapping: Dict[str, Dict[str, str]] = {}
    for label_char, (role_name, vp) in zip(("A", "B", "C"), samples):
        cards_html.append(
            f'<div class="card"><h3>样片 {label_char}</h3>'
            f'<video controls playsinline src="{html.escape(vp.resolve().as_uri())}"></video>'
            f'<label>风格相似度 (1-5)：<input type="range" class="blind-score" data-label="{label_char}" min="1" max="5" value="4" '
            f'oninput="this.nextElementSibling.textContent=this.value"><span>4</span></label></div>'
        )
        answer_mapping[label_char] = {"role": role_name, "filename": vp.name}

    write_json(out_dir / "blind_test_answer_key.json", {
        "created_at": _now_iso(),
        "mapping": answer_mapping,
    })

    blind_html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>风格复刻乱序盲测页 (Blind A/B/C Test)</title>
<style>
  body {{ font-family: -apple-system, sans-serif; background: #0f172a; color: #f8fafc; margin: 24px; }}
  .grid {{ display: flex; gap: 20px; flex-wrap: wrap; }}
  .card {{ background: #1e293b; padding: 16px; border-radius: 14px; width: 300px; border: 1px solid #334155; }}
  video {{ width: 100%; border-radius: 10px; background: #000; }}
  button {{ margin-top: 16px; background: #38bdf8; color: #0f172a; border: none; padding: 10px 16px; border-radius: 8px; font-weight: 700; cursor: pointer; }}
  .hint {{ margin-top: 16px; color: #94a3b8; font-size: 13px; }}
</style>
</head>
<body>
  <h2>风格复刻乱序盲测 (请凭直觉判断哪两条气质同源)</h2>
  <div class="grid">{''.join(cards_html)}</div>
  <button type="button" onclick="exportBlindJson()">导出盲测结果 JSON</button>
  <p class="hint">注：为保证双盲客观性，本页不含任何标签剧透。完成打分并导出 JSON 后，可打开同目录 <code>blind_test_answer_key.json</code> 核对真相。</p>
  <script>
    function exportBlindJson() {{
      const scores = Array.from(document.querySelectorAll('.blind-score')).map(el => ({{
        sample: el.dataset.label,
        similarity_score: Number(el.value)
      }}));
      const payload = {{ exported_at: new Date().toISOString(), scores }};
      const blob = new Blob([JSON.stringify(payload, null, 2)], {{ type: 'application/json' }});
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = 'blind_test_results.json';
      a.click();
    }}
  </script>
</body>
</html>
"""
    (out_dir / "replication_blind_test.html").write_text(blind_html, encoding="utf-8")
    return report


def generate_action_strips(
    video_path: Path,
    edl_path: Optional[Path],
    out_jpg: Path,
) -> Optional[Path]:
    """生成动态帧带拼图（10_action_strips.jpg）：0–3s 每 0.20s 抽帧 + 至多 4 个关键切点 ±0.30s 验证动作跳变。"""
    if not video_path.is_file():
        return None
    ffmpeg = find_bin("ffmpeg")
    if not ffmpeg:
        return None

    try:
        info = ffprobe_media(video_path)
        streams = info.get("streams") or []
        vs = next((s for s in streams if s.get("codec_type") == "video"), None)
        dur = float(info.get("format", {}).get("duration") or (vs or {}).get("duration") or 0.0)
    except Exception:
        return None
    if dur <= 0.05:
        return None

    max_t = max(0.02, dur - 0.05)
    sample_map: Dict[float, str] = {}

    open_end = min(3.0, max_t)
    cur_t = 0.0
    while cur_t <= open_end + 1e-4:
        k = round(min(max_t, cur_t), 2)
        sample_map.setdefault(k, "OPEN")
        cur_t += 0.20

    if edl_path and edl_path.is_file():
        try:
            edl = read_json(edl_path)
            cand_cuts = [float(c.get("timeline_in_sec", 0.0)) for c in (edl.get("clips") or [])[1:]]
            selected_cuts: List[float] = []
            for tc in cand_cuts:
                if tc < 3.1 or tc > max_t - 0.1:
                    continue
                if all(abs(tc - prev_tc) >= 1.0 for prev_tc in selected_cuts):
                    selected_cuts.append(tc)
                if len(selected_cuts) >= 4:
                    break
            for tc in selected_cuts:
                for off in (-0.30, -0.15, 0.0, 0.15, 0.30):
                    t_samp = round(max(0.0, min(max_t, tc + off)), 2)
                    sample_map.setdefault(t_samp, "CUT")
        except Exception:
            pass

    samples = sorted(sample_map.items(), key=lambda x: x[0])[:40]
    if not samples:
        return None

    # 计算实际帧率以支持单遍 FFmpeg select='eq(n,...)' 极速抽帧（40 进程 -> 1 进程）
    r_str = str((vs or {}).get("avg_frame_rate") or (vs or {}).get("r_frame_rate") or f"{DEFAULT_FPS}/1")
    fps_val = max(1.0, float(parse_fps(r_str) or DEFAULT_FPS))

    max_frame_idx = max(0, int(dur * fps_val) - 1)
    dedup_targets: List[Tuple[int, float, str]] = []
    seen_fn: Set[int] = set()
    for t_val, tag in samples:
        fn = min(max_frame_idx, max(0, int(round(t_val * fps_val))))
        if fn in seen_fn:
            continue
        seen_fn.add(fn)
        dedup_targets.append((fn, t_val, tag))

    def _grab_one(item: Tuple[int, float, str], tmp_dir: Path) -> Optional[Tuple[int, float, str, Path]]:
        idx_i, t_val, tag = item
        dst = tmp_dir / f"fb_{idx_i:03d}.jpg"
        proc = subprocess.run(
            [
                ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-ss", f"{t_val:.3f}",
                "-i", str(video_path),
                "-frames:v", "1",
                "-vf", "scale=240:-2",
                "-q:v", "4",
                str(dst),
            ],
            capture_output=True,
        )
        if proc.returncode == 0 and dst.is_file() and dst.stat().st_size > 0:
            return (idx_i, t_val, tag, dst)
        return None

    with tempfile.TemporaryDirectory(prefix="svs_strips_") as td:
        td_path = Path(td)
        frames: List[Tuple[int, float, str, Path]] = []
        if dedup_targets:
            select_expr = "+".join(f"eq(n,{fn})" for fn, _, _ in dedup_targets)
            max_end_t = min(dur + 0.1, dedup_targets[-1][1] + 0.35)
            single_proc = subprocess.run(
                [
                    ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                    "-i", str(video_path),
                    "-t", f"{max_end_t:.3f}",
                    "-vf", f"select='{select_expr}',scale=240:-2",
                    "-fps_mode", "passthrough",
                    "-q:v", "4",
                    str(td_path / "strip_%03d.jpg"),
                ],
                capture_output=True,
            )
            extracted = sorted(td_path.glob("strip_*.jpg"))
            if single_proc.returncode == 0 and len(extracted) == len(dedup_targets):
                for idx_i, ((_, t_val, tag), fp) in enumerate(zip(dedup_targets, extracted)):
                    frames.append((idx_i, t_val, tag, fp))
            else:
                with ThreadPoolExecutor(max_workers=4) as pool:
                    raw_res = list(pool.map(
                        lambda it: _grab_one((it[0], it[1][1], it[1][2]), td_path),
                        enumerate(dedup_targets),
                    ))
                frames = [r for r in raw_res if r is not None]
        if not frames:
            return None

        frames.sort(key=lambda x: x[0])
        with Image.open(frames[0][3]) as im0:
            fw, fh = im0.size

        hdr_h = 28
        pad = 6
        cols = min(8, max(1, len(frames)))
        rows = math.ceil(len(frames) / cols)
        tile_w = fw + pad * 2
        tile_h = fh + hdr_h + pad * 2
        sheet = Image.new("RGB", (cols * tile_w, rows * tile_h), (12, 16, 26))
        draw = ImageDraw.Draw(sheet)

        font_p = find_commercial_font()
        try:
            font_badge = ImageFont.truetype(font_p, 16) if font_p else ImageFont.load_default()
        except Exception:
            font_badge = ImageFont.load_default()

        for slot_idx, (_, t_val, tag, fpath) in enumerate(frames):
            r = slot_idx // cols
            c = slot_idx % cols
            x0 = c * tile_w + pad
            y0 = r * tile_h + pad
            badge_bg = (30, 41, 59) if tag == "OPEN" else (69, 26, 3)
            draw.rectangle([x0, y0, x0 + fw, y0 + hdr_h], fill=badge_bg)
            draw.text((x0 + 8, y0 + 5), f"{tag} {t_val:.2f}s", fill=(250, 204, 21), font=font_badge)
            with Image.open(fpath) as tile_im:
                sheet.paste(tile_im.convert("RGB"), (x0, y0 + hdr_h))

        out_jpg.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(out_jpg, format="JPEG", quality=88)
        return out_jpg


# ------------------------------------------------------------------
# 完工同步成品 & 安全清理无用过程文件 (tidy)
# ------------------------------------------------------------------

def _collect_protected_paths(pipeline_dir: Path) -> Set[Path]:
    """扫描已导出工程中的实际文件引用，绝不删除仍在被引用的路径。"""
    protected: Set[Path] = set()
    jy_dir = pipeline_dir / "jianying_draft"
    if jy_dir.is_dir():
        for xp in jy_dir.glob("*.fcpxml"):
            try:
                root = ET.parse(xp).getroot()
                for mr in root.iter("media-rep"):
                    src = mr.attrib.get("src", "")
                    if src.startswith("file://"):
                        protected.add(Path(urllib.parse.unquote(urllib.parse.urlparse(src).path)).resolve())
                    elif src:
                        protected.add((xp.parent / urllib.parse.unquote(src)).resolve())
            except Exception:
                pass
    hf_dir = pipeline_dir / "hyperframes_draft"
    if hf_dir.is_dir():
        hf = hf_dir / "index.html"
        if hf.is_file():
            txt = hf.read_text(encoding="utf-8", errors="ignore")
            for rel in re.findall(r'(?:data-src|src)=["\']([^"\']+)["\']', txt):
                if rel.startswith(("http://", "https://", "data:")):
                    continue
                protected.add((hf_dir / rel).resolve())
    return protected


def _dir_size(p: Path) -> int:
    if not p.exists():
        return 0
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def tidy_workspace(
    pipeline_dir: Path,
    out_dir: Optional[Path] = None,
    keep_temp: bool = False,
    deep_clean: bool = False,
) -> Dict[str, Any]:
    """
    1. 将全部最终交付物同步归档至 <project_dir>/out/
    2. 除非 --keep-temp，清理大体积过程临时帧/冗余中间音轨（默认保留锁轨音频与代码补镜以支撑 tidy 后二次精修；deep_clean 才彻底清库）
    """
    target_out = out_dir or (pipeline_dir.parent / "out")
    target_out.mkdir(parents=True, exist_ok=True)
    synced: List[str] = []
    for fname in DELIVERABLE_SYNC_FILES:
        src = pipeline_dir / fname
        if src.is_file():
            shutil.copy2(src, target_out / fname)
            synced.append(fname)
    rp_src = pipeline_dir / "review_pack"
    if rp_src.is_dir():
        rp_dst = target_out / "review_pack"
        if rp_dst.exists():
            shutil.rmtree(rp_dst, ignore_errors=True)
        shutil.copytree(rp_src, rp_dst)
        synced.append("review_pack/")
    write_json(target_out / "archive_receipt.json", {
        "plan_sha256": compute_plan_digest(pipeline_dir),
        "files": {name: sha256_file(target_out / name) for name in synced
                  if not name.endswith("/") and name not in ("10_qa_report.json", "10_qa_report.md") and (target_out / name).is_file()},
    })

    if keep_temp:
        rep = {
            "step": "tidy_workspace",
            "skipped_keep_temp": True,
            "removed_count": 0,
            "freed_bytes": 0,
            "freed_mb": 0.0,
            "synced_out_files": synced,
            "removed_paths": [],
        }
        write_json(pipeline_dir / "tidy_report.json", rep)
        return rep

    protected = _collect_protected_paths(pipeline_dir)
    # 若 04_edl.json 仍存在，默认保护其引用的 code_broll 与锁轨文件，支持 post-tidy 的 reedit-visuals / render-locked
    if not deep_clean:
        edl_p = pipeline_dir / "04_edl.json"
        if edl_p.is_file():
            try:
                edl = read_json(edl_p)
                for c in (edl.get("clips") or []):
                    mp = str(c.get("media_path") or "")
                    if mp and "04_generated_broll" in mp and Path(mp).exists():
                        protected.add(Path(mp).resolve())
            except Exception:
                pass

    target_subdirs = TEMP_SUBDIRS + (DEEP_CLEAN_SUBDIRS if deep_clean else ())
    target_files = TEMP_PROCESS_FILES + (DEEP_CLEAN_FILES if deep_clean else ())

    removed_paths: List[str] = []
    freed_bytes = 0

    for dname in target_subdirs:
        dp = pipeline_dir / dname
        if not dp.is_dir():
            continue
        dp_res = dp.resolve()
        has_prot = any(dp_res == pr or dp_res in pr.parents for pr in protected)
        if has_prot:
            continue
        freed_bytes += _dir_size(dp)
        shutil.rmtree(dp, ignore_errors=True)
        removed_paths.append(dname + "/")

    for fname in target_files:
        fp = pipeline_dir / fname
        if not fp.is_file():
            continue
        if fp.resolve() in protected:
            continue
        freed_bytes += fp.stat().st_size
        fp.unlink(missing_ok=True)
        removed_paths.append(fname)

    # 清理 _bb_tmp* 等临时检测残留目录
    for tmp_cand in pipeline_dir.glob("_bb_tmp*"):
        if tmp_cand.is_dir():
            freed_bytes += _dir_size(tmp_cand)
            shutil.rmtree(tmp_cand, ignore_errors=True)
            removed_paths.append(tmp_cand.name + "/")

    freed_mb = round(freed_bytes / (1024.0 * 1024.0), 2)
    rep = {
        "step": "tidy_workspace",
        "skipped_keep_temp": False,
        "removed_count": len(removed_paths),
        "freed_bytes": freed_bytes,
        "freed_mb": freed_mb,
        "synced_out_files": synced,
        "removed_paths": removed_paths,
    }
    write_json(pipeline_dir / "tidy_report.json", rep)
    write_json(target_out / "tidy_report.json", rep)
    print(f"[tidy] 完工清理完成：删除 {len(removed_paths)} 项过程文件/目录，释放 {freed_mb:.2f} MB；交付物已归档至 {target_out}")
    return rep


def render_progress_card(
    pipeline_dir: Path,
    user_type: Optional[str] = None,
    track: Optional[str] = None,
    write_files: bool = True,
) -> Dict[str, Any]:
    """根据当前项目目录真实落盘进度，生成面向零基础用户的【四要素掌控感进度卡】（100% 大白话、零专业黑话）。"""
    pipeline_dir.mkdir(parents=True, exist_ok=True)
    prev_card_p = pipeline_dir / "00_progress_card.json"
    prev_card = read_json(prev_card_p) if prev_card_p.is_file() else {}

    edl_p = pipeline_dir / "04_edl.json"
    edl = read_json(edl_p) if edl_p.is_file() else {}
    ae_p = pipeline_dir / "03_audio_events.json"
    ae = read_json(ae_p) if ae_p.is_file() else {}
    mf_p = pipeline_dir / "01_manifest.json"
    mf = read_json(mf_p) if mf_p.is_file() else {}
    inv_p = pipeline_dir / "00_inventory.json"
    inv = read_json(inv_p) if inv_p.is_file() else {}
    qa_p = pipeline_dir / "10_qa_report.json"
    qa = read_json(qa_p) if qa_p.is_file() else {}
    anim_aud_p = pipeline_dir / "10_animation_audit.json"
    anim_aud = read_json(anim_aud_p) if anim_aud_p.is_file() else {}
    lock_st = _load_lock_state(pipeline_dir)

    eff_track = str(track or prev_card.get("track") or ("store" if edl.get("style_id") in ("style_04", "style_05", "style_07", "style_13", "style_14", "style_17", "style_18", "style_20", "style_21", "style_23") else "creator"))
    if user_type and user_type in USER_TYPES:
        u_type = user_type
    elif prev_card.get("user_type") in USER_TYPES:
        u_type = str(prev_card["user_type"])
    elif anim_aud_p.is_file() or (pipeline_dir / "00_code_spec.json").is_file() or float(edl.get("broll_ratio_target") or 0.0) >= 0.85:
        u_type = "faceless_visual"
    elif inv_p.is_file() and not (pipeline_dir / "shot_card.md").is_file() and not (pipeline_dir.parent / "shot_card.md").is_file():
        u_type = "footage_organizer"
    else:
        u_type = "store_from_zero" if eff_track == "store" else "creator_talking"

    user_type_names = {
        "store_from_zero": "实体店从零拍",
        "creator_talking": "个人博主口播提质感",
        "footage_organizer": "手机存货一键挑剪",
        "faceless_visual": "社恐不露脸 / 纯图解动画",
        "post_review": "发片后复盘调优",
    }
    routes = {
        "store_from_zero": [
            "定话题写说话词",
            "照手机清单开拍",
            "听声音定节奏",
            "看粗剪画面",
            "拿成品与封面",
        ],
        "creator_talking": [
            "定台词或收素材",
            "听声音定节奏",
            "选画面样式看粗剪",
            "拿成品与封面",
        ],
        "footage_organizer": [
            "自动筛废片排顺序",
            "听声音看粗剪",
            "拿成品与封面",
        ],
        "faceless_visual": [
            "定台词与配音",
            "配全屏特写或动态图表",
            "看粗剪确认",
            "拿成品与封面",
        ],
        "post_review": [
            "看数据找卡点",
            "存下改进配方",
        ],
    }
    steps_list = routes[u_type]
    total_steps = len(steps_list)

    has_script = any((pipeline_dir / fn).is_file() for fn in ("00_raw_intel.json", "00_script_lint.md", "00_code_spec.json"))
    has_shot_card = (pipeline_dir / "shot_card.md").is_file() or (pipeline_dir.parent / "shot_card.md").is_file()
    has_media = mf_p.is_file() or inv_p.is_file()
    has_audio = ae_p.is_file() or (pipeline_dir / "03_blind_audio.m4a").is_file()
    has_preview = edl_p.is_file()
    has_final = (pipeline_dir / "output_final.mp4").is_file() or (pipeline_dir.parent / "out" / "output_final.mp4").is_file()
    is_approved = bool(lock_st.get("human_approved"))

    media_items = mf.get("items") or inv.get("items") or []
    usable_cnt = sum(1 for it in media_items if it.get("video_grade", "usable") != "ng")
    dur_sec = float(
        edl.get("total_duration_sec")
        or ae.get("locked_duration_sec")
        or anim_aud.get("duration_sec")
        or 0.0
    )
    clip_cnt = len(edl.get("clips") or [])
    is_anim_mode = bool(anim_aud)
    has_jy_draft = (pipeline_dir / "jianying_draft").is_dir() or (pipeline_dir.parent / "out" / "jianying_draft").is_dir()
    has_4k_covers = (pipeline_dir / "09_cover_land_4k.png").is_file() or (pipeline_dir / "09_cover_port_4k.png").is_file()
    has_copy_pack = (pipeline_dir / "09_publish_copy_pack.md").is_file()
    aspect_label = (
        "横屏"
        if is_anim_mode and int(anim_aud.get("width", 1920)) > int(anim_aud.get("height", 1080))
        else "竖屏"
    )
    gaps = edl.get("deictic_gaps") or []

    missing_items: List[str] = []
    if gaps:
        cue_name = str(gaps[0].get("matched_cue") or "对应特写")
        missing_items.append(f"台词提到了「{cue_name}」，可回 A 让我自动画一张对比图卡补上，或回 B 补拍一段 3 秒特写")

    if u_type == "post_review":
        if is_approved or has_final:
            cur_step = 2
            ai_status = "已经对照你的画面节奏找出了观众划走的位置，并把改进配方存进了你的账号偏好。"
            user_action = "看看这份复盘建议合不合心意："
            choices = [
                "回 A：说得很准，下一条直接按这个新节奏做",
                "回 B：我还想补充几个后台看到的评论或私信情况",
                "回 C：直接开始策划下一条新视频",
            ]
            remaining = "改进配方已存好，随时可以直接开启下一条视频。"
        else:
            cur_step = 1
            ai_status = "正在等你发来视频发布两天后的后台表现数字。"
            user_action = "把后台看到的播放量、前几秒留下的人数比例、看完的比例和点赞评论数发给我："
            choices = [
                "回 A：直接打字发这几个数字",
                "回 B：把后台数据页面截图发给我",
                "回 C：还没发满两天，先帮我剪一条新片子",
            ]
            remaining = "拿到数字后 → 帮你用大白话找出卡点并存下改进配方。"
            missing_items.append("需要提供发布后的播放、留存、点赞或私信数字")
    elif has_final and is_approved:
        cur_step = total_steps
        seg_desc = f"，共 {clip_cnt} 个画面段落" if clip_cnt > 0 else ""
        pack_parts = ["封面图"]
        if has_copy_pack:
            pack_parts.append("分平台发布文案")
        if has_jy_draft:
            pack_parts.append("可编辑草稿包")
        ai_status = f"成片（全长 {dur_sec:.1f} 秒{seg_desc}）、{'与'.join(pack_parts)}已全部打包归档，原素材完好未动。"
        user_action = "全部工序已圆满完工！你可以直接拿去发布，或者告诉我还想做什么："
        choices = [
            "回 A：直接去发片，两天后拿数据回来找你复盘",
            "回 B：用同一套样式再做下一条新视频",
            "回 C：帮我把封面标题再多备选两个不同说法",
        ]
        remaining = "全部完成（0 项待办，随时可发片）。"
    elif has_final:
        cur_step = total_steps
        qa_pass = bool(qa.get("all_passed", False)) if qa else False
        deliverable_bits = [f"{dur_sec:.1f} 秒高清{aspect_label}成片"]
        if has_4k_covers:
            deliverable_bits.append("横竖双比例超清封面")
        else:
            deliverable_bits.append("主页大图封面")
        if has_copy_pack:
            deliverable_bits.append("分平台发布文案")
        if has_jy_draft:
            deliverable_bits.append("剪映草稿包")
        qa_tail = (
            "并完成了声音、画面与字幕自动检查（全部通过）。"
            if qa_pass
            else ("并附上了自动体检提醒，建议先看一眼红色提醒项。" if qa else "请先打开成片核对画面与声音。")
        )
        ai_status = f"已经为你合成好{'、'.join(deliverable_bits)}，" + qa_tail
        user_action = "请最后看一眼成品视频和封面，直接回个字母就能收工："
        choices = [
            "回 A：看过了很满意，确认收工拿片",
            "回 B：声音不动，我想换一套小窗口或超大字画面样式",
            "回 C：想改一两句文字或换个封面标题",
        ]
        remaining = "只差你最后点头确认一眼，确认后立即归档收工。"
    elif has_preview:
        cur_step = max(2, total_steps - 1)
        ai_status = f"已经按你的说话节奏排好了 {clip_cnt} 个画面段落（全长 {dur_sec:.1f} 秒），配好了居中字幕、醒目大字与小窗口粗剪预览。"
        user_action = "先看一眼粗剪画面的切换节奏和样式，回个字母告诉我怎么往下走："
        choices = [
            "回 A：粗剪节奏和画面样式满意，直接出正式高清成片和封面",
            "回 B：声音不动，帮我换另一款画面样式（比如虚化小窗款 / 黑底双格证据款 / 不露脸快切款）",
            "回 C：把开头前 3 秒换个更抓人的画面或把重点大字再放大",
        ]
        remaining = "确认粗剪后 → 正式导出高清成品视频、主页封面与剪映草稿包。"
    elif has_audio:
        cur_step = 3 if u_type == "store_from_zero" else 2
        ai_status = f"已经把你说话里的停顿、冷场修顺，并配好了背景音乐（声音全长 {dur_sec:.1f} 秒，原视频完好未动）。"
        user_action = "先花几十秒听一下这份修好的声音小样，回个字母就行："
        choices = [
            "回 A：声音和语速听着很顺，继续往下配画面和醒目大字",
            "回 B：有句话想删掉或改一下说法（告诉我哪一句）",
            "回 C：背景音乐换一首更轻松或更有节奏感的",
        ]
        remaining = "确认声音后 → 挑选顺眼的画面样式看粗剪 → 导出成品视频与封面。"
    elif has_media:
        cur_step = 1 if u_type == "footage_organizer" else 2
        ai_status = f"已经帮你翻看完文件夹里的 {len(media_items)} 段素材，挑出了 {usable_cnt} 段清晰稳定的可用好镜头（原文件一根头发没动）。"
        user_action = "素材已经挑好，接下来怎么推进最合你心意："
        choices = [
            "回 A：直接帮我修顺说话声音、排好画面出粗剪预览",
            "回 B：我先选一款喜欢的画面样式（比如门店招牌款 / 热点虚化小窗款 / 全程不露脸快切款）",
            "回 C：我还想再往文件夹里补几段刚拍的特写",
        ]
        remaining = "修顺声音并排好粗剪画面 → 导出高清成品视频与主页封面。"
    elif has_shot_card or has_script:
        cur_step = 2 if (u_type == "store_from_zero" and has_shot_card) else 1
        ai_status = "已经为你整理好接地气的说话台词" + ("与手机拍摄清单（标明了每段拍几秒、怎么拿手机）。" if has_shot_card else "，并避开了容易被平台限流的夸大词。")
        user_action = "看看这份台词" + ("和拍摄单" if has_shot_card else "") + "顺不顺口，回个字母即可："
        choices = [
            "回 A：台词很顺口，我拍好后把视频文件夹发给你（或直接用现有素材开剪）",
            "回 B：有几句不太像我平时说话的口气，帮我改得更口语一点",
            "回 C：我不想自己出镜拍了，直接帮我做成全程不露脸的图解/特写短片",
        ]
        remaining = "收到素材或配音后 → 修顺声音 → 排好粗剪画面 → 导出成品视频与封面。"
        missing_items.append("等待放入拍好的视频文件夹，或确认改走不露脸图解路线")
    else:
        cur_step = 1
        ai_status = f"已为你开启「{user_type_names[u_type]}」专属工作区，正在等你告诉我这次想拍的话题或素材位置。"
        user_action = "只需要随口告诉我下面任意一样，咱们就能立刻开干："
        choices = [
            "回 A：告诉我你是做什么行业的、这次想聊什么话题（我先帮你写说话词）",
            "回 B：直接把拍好的视频文件夹路径发给我（我先帮你挑好镜头）",
            "回 C：我不想露脸，把几句文字或数据发给我（我直接帮你画动态图表短片）",
        ]
        remaining = "沿着专属步骤走完 → 拿到成品视频、3:4 主页封面与可微调草稿包。"
        missing_items.append("需要一句话话题描述，或已拍好的视频文件夹位置")

    cur_step = max(1, min(total_steps, cur_step))
    step_name = steps_list[cur_step - 1]
    filled = "■" * cur_step
    empty = "□" * max(0, total_steps - cur_step)
    prog_bar = f"[{filled}{empty}]"

    choices_md = "\n".join(f"   - **{c.split('：')[0]}**：{c.split('：', 1)[1]}" if "：" in c else f"   - {c}" for c in choices)
    missing_suffix = f"（温馨提示：{missing_items[0]}）" if missing_items else ""
    md_card = "\n".join([
        "---",
        f"📍 **当前进度**：第 {cur_step} 步 / 共 {total_steps} 步（{step_name}）  `{prog_bar}`",
        f"🤖 **我刚做了 / 正在做**：{ai_status}",
        f"👉 **现在轮到你**：{user_action}",
        choices_md,
        f"⏳ **离能发还差**：{remaining}{missing_suffix}",
        "---",
    ])

    card = {
        "updated_at": _now_iso(),
        "user_type": u_type,
        "user_type_cn": user_type_names[u_type],
        "track": eff_track,
        "current_step": cur_step,
        "total_steps": total_steps,
        "step_name_cn": step_name,
        "progress_bar": prog_bar,
        "steps_route_cn": steps_list,
        "ai_status_cn": ai_status,
        "user_action_cn": user_action,
        "quick_choices": choices,
        "remaining_cn": remaining,
        "missing_items_cn": missing_items,
        "human_approved": is_approved,
        "markdown_card": md_card,
    }
    if write_files:
        write_json(pipeline_dir / "00_progress_card.json", card)
        (pipeline_dir / "00_进度看板.md").write_text(
            f"# 短视频制作实时进度看板（{user_type_names[u_type]}）\n\n{md_card}\n",
            encoding="utf-8",
        )
    return card


def main() -> None:
    parser = argparse.ArgumentParser(description="协作闸门锁、复刻洁净室与完工自动清理守卫")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_rs = sub.add_parser("record-stop")
    p_rs.add_argument("--pipeline-dir", required=True)
    p_rs.add_argument("--type", required=True, choices=STOP_TYPES)
    p_rs.add_argument("--summary", default="")
    p_rs.add_argument("--rehearsal", action="store_true")

    p_as = sub.add_parser("audit-stops")
    p_as.add_argument("--pipeline-dir", required=True)
    p_as.add_argument("--require-all", action="store_true")

    p_lk = sub.add_parser("lock")
    p_lk.add_argument("--pipeline-dir", required=True)
    p_lk.add_argument("--note", default="方案拍板锁定")

    p_vf = sub.add_parser("verify")
    p_vf.add_argument("--pipeline-dir", required=True)

    p_ap = sub.add_parser("approve-final")
    p_ap.add_argument("--pipeline-dir", required=True)
    p_ap.add_argument("--out-dir", help="可选：自定义归档 out 目录路径")
    p_ap.add_argument("--note", default="", help="记录实际复核结果。剪映导入请写明版本和检查到的轨道")
    p_ap.add_argument("--reviewed", action="append", default=[], help="已完成的人工检查 ID，可重复传参")

    p_rd = sub.add_parser("replication-diff")
    p_rd.add_argument("--reference", required=True)
    p_rd.add_argument("--output", required=True)
    p_rd.add_argument("--contrast")
    p_rd.add_argument("--out-dir", required=True)

    p_td = sub.add_parser("tidy")
    p_td.add_argument("--pipeline-dir", required=True)
    p_td.add_argument("--out-dir")
    p_td.add_argument("--keep-temp", action="store_true")
    p_td.add_argument("--deep-clean", action="store_true")
    p_arch = sub.add_parser("verify-out")
    p_arch.add_argument("--out-dir", required=True, type=Path)

    p_st = sub.add_parser("status")
    p_st.add_argument("--pipeline-dir", required=True, type=Path)
    p_st.add_argument("--user-type", choices=USER_TYPES, help="可选：显式指定 5 类用户路线")
    p_st.add_argument("--track", choices=("store", "creator"), help="可选：门店或个人账号方向")

    args = parser.parse_args()
    if args.cmd == "record-stop":
        st = record_stop(Path(args.pipeline_dir), args.type, args.summary, args.rehearsal)
        print(f"[workflow] 已记录停点 {args.type} ({len(st['interruptions'])}/{BUDGET})")
    elif args.cmd == "audit-stops":
        res = audit_stops(Path(args.pipeline_dir), require_all=args.require_all)
        print(f"[workflow] 打扰审计: {res['count']}/{res['budget']} {res['types']} passed={res['passed']}")
        if not res["passed"]:
            raise SystemExit(1)
    elif args.cmd == "lock":
        st = lock_plan(Path(args.pipeline_dir), note=args.note)
        print(f"[workflow] 方案已上锁 sha={st['plan_sha256'][:12]} ({st['clip_count']}镜, {st['duration_sec']}s)")
    elif args.cmd == "verify":
        code, msg, _ = verify_lock(Path(args.pipeline_dir))
        print(("[PASS] " if code == 0 else "[BLOCK] ") + msg)
        raise SystemExit(code)
    elif args.cmd == "approve-final":
        st = approve_final(
            Path(args.pipeline_dir),
            note=args.note,
            reviewed_checks=tuple(args.reviewed),
            out_dir=Path(args.out_dir) if args.out_dir else None,
        )
        print(f"[workflow] 人工终审签字完成 -> APPROVED (at={st['approved_at']})")
    elif args.cmd == "verify-out":
        result = verify_archive(args.out_dir)
        print(result)
        raise SystemExit(0 if result["passed"] else 2)
    elif args.cmd == "replication-diff":
        rep = run_replication_diff(
            Path(args.reference),
            Path(args.output),
            Path(args.out_dir),
            contrast_mp4=Path(args.contrast) if args.contrast else None,
        )
        print(
            f"[replication] 洁净室={'PASS' if rep['clean_room_passed'] else 'BLOCK'}, "
            f"min_phash={rep['min_phash_hamming']}, ocr12={len(rep['ocr_12char_overlap_hits'])}, "
            f"匹配维度={rep['dimensions_matched']}/{rep['dimensions_total']}"
        )
        if rep["clean_room_block"]:
            raise SystemExit(2)
    elif args.cmd == "tidy":
        tidy_workspace(
            Path(args.pipeline_dir),
            out_dir=Path(args.out_dir) if args.out_dir else None,
            keep_temp=args.keep_temp,
            deep_clean=args.deep_clean,
        )
    elif args.cmd == "status":
        card = render_progress_card(args.pipeline_dir, user_type=args.user_type, track=args.track, write_files=True)
        print(card["markdown_card"])


if __name__ == "__main__":
    main()

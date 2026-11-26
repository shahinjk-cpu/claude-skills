#!/usr/bin/env python3
"""
[Step 1: 素材规整 + HDR 色彩空间还原 + 智能重构图 + 物理几何仿射映射]
v5 升级：
1. 基于 inventory 的 faces / saliency_bbox 智能计算横转竖重构图重心 (crop_x_frac / crop_y_frac)，彻底避免三分法人物裁出画面。
2. 音频流强制 `-af aresample=async=1:first_pts=0` 对齐 PTS 并自动拯救单边故障无线麦，杜绝 VFR/非零偏移引起的声画漂移。
3. 修复无 zscale 时 HDR 回退滤镜链路，准确统计 hdr_tonemapped_count，尊重 00_shot_log/00_visual_index 角色。
4. 并发调用 ffmpeg 规整，复用 common.detect_vfr_hdr。
"""

from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import (
    BT709_FFMPEG_ARGS,
    BT709_VF_SUFFIX,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    DEFAULT_FPS,
    MEDIA_EXTS,
    compute_centered_crop_frac,
    compute_crop_transform,
    detect_vfr_hdr,
    ffmpeg_has_filter,
    ffprobe_media,
    find_bin,
    map_eye_anchor_to_crop,
    map_norm_bbox_to_crop,
    maybe_reexec_in_venv,
    parse_video_stream_geometry,
    read_json,
    read_wav_as_48k_stereo,
    rescue_stereo_channels,
    run_cmd,
    write_json,
    write_wav_48k_stereo,
)


def _build_hdr_prefix() -> str:
    if ffmpeg_has_filter("zscale"):
        return "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,"
    return "colorspace=all=bt709:iall=bt2020:fast=1,"


def _smart_crop_fractions(shot_meta: Optional[Dict[str, Any]], disp_w: int, disp_h: int) -> Tuple[float, float]:
    """根据旋转前人脸/显著性中心计算智能重构图裁切比例，确保横转竖后主体真正落在 540px 正中。"""
    if not shot_meta or disp_w <= 0 or disp_h <= 0:
        return 0.5, 0.5
    faces = shot_meta.get("faces") or []
    cx, cy = 0.5, 0.5
    is_face = False
    found = False
    if faces and isinstance(faces[0], dict):
        bb = faces[0].get("bbox")
        if isinstance(bb, dict) and bb.get("w", 0) > 0:
            cx = float(bb.get("x", 0.5)) + float(bb.get("w", 0.0)) * 0.5
            cy = float(bb.get("y", 0.5)) + float(bb.get("h", 0.0)) * 0.5
            is_face = True
            found = True
    if not found:
        sal = shot_meta.get("saliency_bbox")
        if isinstance(sal, dict) and sal.get("w", 0) > 0:
            cx = float(sal.get("x", 0.5)) + float(sal.get("w", 0.0)) * 0.5
            cy = float(sal.get("y", 0.5)) + float(sal.get("h", 0.0)) * 0.5
            found = True
    if not found:
        return 0.5, 0.5
    base_tx = compute_crop_transform(disp_w, disp_h, CANVAS_WIDTH, CANVAS_HEIGHT, 0.5, 0.5)
    fx = compute_centered_crop_frac(cx, base_tx["scaled_w"], CANVAS_WIDTH, target_norm_pos=0.5)
    fy = compute_centered_crop_frac(cy, base_tx["scaled_h"], CANVAS_HEIGHT, target_norm_pos=0.40 if is_face else 0.5)
    return fx, fy


def normalize_single_media(
    src: Path,
    out_dir: Path,
    idx: int,
    role_hint: str = "auto",
    shot_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    ffmpeg = find_bin("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("未找到 ffmpeg。")

    meta = ffprobe_media(src)
    streams = meta.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not v_stream:
        raise ValueError(f"文件不含视频流: {src}")

    geom = parse_video_stream_geometry(v_stream)
    disp_w = geom["display_width"] or CANVAS_WIDTH
    disp_h = geom["display_height"] or CANVAS_HEIGHT
    cx_frac, cy_frac = _smart_crop_fractions(shot_meta, disp_w, disp_h)
    crop_tx = compute_crop_transform(
        disp_w, disp_h, CANVAS_WIDTH, CANVAS_HEIGHT,
        crop_x_frac=cx_frac, crop_y_frac=cy_frac,
    )

    vh = detect_vfr_hdr(meta)
    r_fps, is_vfr, was_hdr = vh["r_fps"], vh["is_vfr"], vh["was_hdr"]
    log_profile = vh.get("log_profile")
    color_transfer = vh["color_transfer"] or "unknown"
    color_primaries = vh["color_primaries"] or "unknown"

    stem = f"norm_{idx:02d}_{src.stem}"
    out_mp4 = out_dir / f"{stem}.mp4"
    out_wav = out_dir / f"{stem}.wav"
    has_audio = a_stream is not None

    hdr_prefix = _build_hdr_prefix() if was_hdr else ("eq=contrast=1.18:saturation=1.22:gamma=0.92," if log_profile else "")
    bt709_tail = ",".join(BT709_VF_SUFFIX)
    vf_chain = (
        f"{hdr_prefix}"
        f"scale={crop_tx['scaled_w']}:{crop_tx['scaled_h']}:flags=lanczos,"
        f"crop={CANVAS_WIDTH}:{CANVAS_HEIGHT}:{crop_tx['crop_x']}:{crop_tx['crop_y']},"
        f"fps={DEFAULT_FPS},{bt709_tail}"
    )

    def _build_norm_cmd(vf_str: str, include_wav: bool) -> List[str]:
        cmd = [
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(src),
            "-map", "0:v:0",
            "-vf", vf_str,
            "-an",
            "-fps_mode", "cfr",
            "-r", str(DEFAULT_FPS),
            "-c:v", "libx264", *BT709_FFMPEG_ARGS, "-preset", "fast", "-crf", "18",
            str(out_mp4),
        ]
        if include_wav:
            cmd.extend([
                "-map", "0:a:0",
                "-vn", "-af", "aresample=async=1:first_pts=0",
                "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "2",
                str(out_wav),
            ])
        return cmd

    hdr_tonemapped = bool(was_hdr and ffmpeg_has_filter("zscale"))
    res = run_cmd(_build_norm_cmd(vf_chain, has_audio), check=False)
    if res.returncode != 0 and was_hdr:
        plain_vf = (
            f"scale={crop_tx['scaled_w']}:{crop_tx['scaled_h']}:flags=lanczos,"
            f"crop={CANVAS_WIDTH}:{CANVAS_HEIGHT}:{crop_tx['crop_x']}:{crop_tx['crop_y']},"
            f"fps={DEFAULT_FPS},{bt709_tail}"
        )
        hdr_tonemapped = False
        fb_res = None
        if ffmpeg_has_filter("zscale"):
            fallback_vf = (
                f"colorspace=all=bt709:iall=bt2020:fast=1,"
                f"{plain_vf}"
            )
            fb_res = run_cmd(_build_norm_cmd(fallback_vf, has_audio), check=False)
        if fb_res is None or fb_res.returncode != 0:
            run_cmd(_build_norm_cmd(plain_vf, has_audio), check=True)
    elif res.returncode != 0:
        raise RuntimeError(f"素材规整失败 ({src.name}): {(res.stderr or '')[-800:]}")

    stereo_diag = "ok"
    if has_audio and out_wav.is_file():
        # 若无线麦单边明显失效，直接用完好单声道修复归整 WAV
        try:
            arr_w, _ = read_wav_as_48k_stereo(out_wav, target_sr=48000)
            arr_fixed, stereo_diag = rescue_stereo_channels(arr_w, imbalance_db=8.0)
            if stereo_diag != "ok":
                write_wav_48k_stereo(out_wav, arr_fixed, sr=48000)
        except Exception:
            pass

    norm_meta = ffprobe_media(out_mp4)
    nv = next(s for s in norm_meta["streams"] if s["codec_type"] == "video")
    norm_dur = float(norm_meta.get("format", {}).get("duration") or nv.get("duration") or 0.0)

    # 判定素材角色（与 inventory_media 保持一致）：纯代码保护 > 显式传入 > 人工 visual_index > 无音频 > 音频缺陷/文件名 > 建议角色
    name_low = src.name.lower()
    is_code_scene = (src.parent.name == "01_code_scenes") or name_low.startswith("code_scene_")
    shot_role = (shot_meta or {}).get("role")
    shot_ag = (shot_meta or {}).get("audio_grade")
    vis_indexed = bool((shot_meta or {}).get("visual_indexed"))
    if role_hint != "auto":
        role = role_hint
    elif is_code_scene:
        role = "b_roll"
    elif "code_broll" in name_low:
        role = "code_broll"
    elif vis_indexed and shot_role in ("a_roll_candidate", "b_roll_candidate"):
        role = "a_roll" if (shot_role == "a_roll_candidate" and has_audio) else "b_roll"
    elif not has_audio or shot_ag in ("silent", "noisy"):
        role = "b_roll"
    elif "broll" in name_low or "b_roll" in name_low:
        role = "b_roll"
    elif "aroll" in name_low or "a_roll" in name_low or "talk" in name_low or "main" in name_low:
        role = "a_roll"
    elif shot_role == "b_roll_candidate":
        role = "b_roll"
    elif shot_role == "a_roll_candidate":
        role = "a_roll"
    else:
        role = "a_roll" if has_audio else "b_roll"

    item: Dict[str, Any] = {
        "id": f"media_{idx:02d}",
        "source_path": str(src.resolve()),
        "normalized_mp4": str(out_mp4.resolve()),
        "normalized_wav": str(out_wav.resolve()) if has_audio else None,
        "role": role,
        "source_is_code_scene": is_code_scene,
        "original_size": f"{disp_w}x{disp_h}",
        "coded_size": f"{geom['coded_width']}x{geom['coded_height']}",
        "rotation_deg": geom["rotation_deg"],
        "crop_transform": crop_tx,
        "was_vfr": is_vfr,
        "was_hdr": was_hdr,
        "hdr_tonemapped": hdr_tonemapped,
        "source_log_profile": log_profile,
        "stereo_diag": stereo_diag,
        "source_color_transfer": color_transfer,
        "source_color_primaries": color_primaries,
        "original_r_fps": round(r_fps, 2),
        "normalized_fps": DEFAULT_FPS,
        "duration_sec": round(norm_dur, 4),
        "has_audio": has_audio,
    }
    if shot_meta:
        for k in (
            "best_in_sec", "sharpness_score", "stability_score",
            "motion_speed_px", "accel_jitter_px", "camera_motion", "shot_size", "action_apex_sec",
            "audio_grade", "video_grade", "taboo_tags", "usable", "visual_indexed",
            "semantic_tags", "manual_tags", "scene_group",
        ):
            if k in shot_meta:
                item[k] = shot_meta[k]
        if shot_meta.get("usable") is False and item.get("video_grade", "usable") == "usable":
            item["video_grade"] = "ng"

        mapped_faces: List[Dict[str, Any]] = []
        for f_obj in shot_meta.get("faces") or []:
            nb = map_norm_bbox_to_crop(f_obj.get("bbox"), crop_tx)
            if nb is None:
                continue
            nf = dict(f_obj)
            nf["bbox"] = nb
            ea_tmp = map_eye_anchor_to_crop({"eye_cx": f_obj.get("eye_cx", 0.5), "eye_cy": f_obj.get("eye_cy", 0.35)}, crop_tx)
            if ea_tmp:
                nf["eye_cx"] = ea_tmp["eye_cx"]
                nf["eye_cy"] = ea_tmp["eye_cy"]
            mapped_faces.append(nf)
        item["faces"] = mapped_faces

        ea = shot_meta.get("eye_anchor")
        if isinstance(ea, dict):
            mapped_ea = map_eye_anchor_to_crop(
                {"eye_cx": ea.get("cx", ea.get("eye_cx", 0.5)), "eye_cy": ea.get("cy", ea.get("eye_cy", 0.36)), **{k: v for k, v in ea.items()}},
                crop_tx,
            )
            if mapped_ea:
                mapped_ea["cx"] = mapped_ea["eye_cx"]
                mapped_ea["cy"] = mapped_ea["eye_cy"]
            item["eye_anchor"] = mapped_ea
        else:
            item["eye_anchor"] = None

        item["saliency_bbox"] = map_norm_bbox_to_crop(shot_meta.get("saliency_bbox"), crop_tx)
    return item


def run_step1(input_paths: List[Path], pipeline_dir: Path) -> Dict[str, Any]:
    norm_dir = pipeline_dir / "01_normalized"
    norm_dir.mkdir(parents=True, exist_ok=True)

    shot_by_path: Dict[str, Dict[str, Any]] = {}
    shot_by_name: Dict[str, Dict[str, Any]] = {}
    shot_log_p = pipeline_dir / "00_shot_log.json"
    if shot_log_p.exists():
        sl = read_json(shot_log_p)
        for s in sl.get("shots", []):
            if s.get("path"):
                shot_by_path[str(Path(s["path"]).resolve())] = s
            if s.get("filename"):
                shot_by_name[str(s["filename"])] = s

    scene_meta_by_name: Dict[str, Dict[str, Any]] = {}
    media_files: List[Path] = []
    for p in input_paths:
        if p.is_dir():
            sm_file = p / "scene_meta.json"
            if sm_file.is_file():
                try:
                    sm_raw = read_json(sm_file)
                    if isinstance(sm_raw, dict):
                        for fn, m_obj in sm_raw.items():
                            if isinstance(m_obj, dict):
                                scene_meta_by_name[str(fn)] = m_obj
                except Exception:
                    pass
            for child in sorted(p.iterdir()):
                if child.is_file() and child.suffix.lower() in MEDIA_EXTS and "benchmark" not in child.name.lower():
                    media_files.append(child)
        elif p.is_file() and p.suffix.lower() in MEDIA_EXTS and "benchmark" not in p.name.lower():
            media_files.append(p)

    if not media_files:
        raise FileNotFoundError("未找到任何可用的原始视频素材文件。")

    def _merge_shot_meta(f: Path) -> Optional[Dict[str, Any]]:
        base = dict(shot_by_path.get(str(f.resolve())) or shot_by_name.get(f.name) or {})
        extra = scene_meta_by_name.get(f.name)
        if extra:
            base.update(extra)
        return base or None

    tasks = [
        (f, idx, _merge_shot_meta(f))
        for idx, f in enumerate(media_files, start=1)
    ]
    if len(tasks) > 1:
        with ThreadPoolExecutor(max_workers=min(4, len(tasks))) as pool:
            items = list(pool.map(lambda args: normalize_single_media(args[0], norm_dir, args[1], shot_meta=args[2]), tasks))
    else:
        items = [normalize_single_media(tasks[0][0], norm_dir, tasks[0][1], shot_meta=tasks[0][2])]

    hdr_cnt = sum(1 for it in items if it.get("hdr_tonemapped"))
    manifest = {
        "step": "01_normalize",
        "fps": DEFAULT_FPS,
        "resolution": f"{CANVAS_WIDTH}x{CANVAS_HEIGHT}",
        "sample_rate": 48000,
        "media_count": len(items),
        "hdr_tonemapped_count": hdr_cnt,
        "items": items,
    }
    write_json(pipeline_dir / "01_manifest.json", manifest)
    print(f"[step1] 素材规整完成：{len(items)} 条素材已统一为 {DEFAULT_FPS}fps CFR (HDR还原 {hdr_cnt} 条) -> 01_manifest.json")
    return manifest


def main() -> None:
    maybe_reexec_in_venv()
    parser = argparse.ArgumentParser(description="Step 1: 素材规整 (旋转解算 + 智能重构图 + 仿射映射 + HDR + CFR)")
    parser.add_argument("--input", required=True, nargs="+", help="原始素材目录或视频文件路径列表")
    parser.add_argument("--pipeline-dir", required=True, help="pipeline 输出目录")
    args = parser.parse_args()
    run_step1([Path(x) for x in args.input], Path(args.pipeline_dir))


if __name__ == "__main__":
    main()

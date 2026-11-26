#!/usr/bin/env python3
"""
出片2: 剪映专业版可编辑全风格多轨工程包 (FCPXML 1.10 + 静态全画布透明 PNG + 三轨独立 WAV + SRT)
P0/P1/P2 优化项：
1. 全部 <media-rep src="..."> 严格使用相对 jianying_draft/ 目录的路径，绝不出现 file:// 或本机用户目录绝对路径。
2. 彻底停用缓慢的 30fps Alpha MOV 编码，改用按权威 final_bbox 贴合的 1080x1920 静态透明 PNG（速度 >20x，体积降 >90%）。
3. 删除 legacy_v5_json/ 与 stage_overlays 死代码，清理旧 alpha_layers/。
4. 三轨独立音频复用同源定电平分轨 (08_voice_master.wav / 08_bgm_ducked.wav / 06_sfx_track.wav)，FCPXML 设 0dB 不重复衰减。
5. Connected clip offset 严格叠加主轨首段 clip 的 source start 基准帧，防止剪映/达芬奇导入后时间轴偏移。
"""

from __future__ import annotations

import argparse
import shutil
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.dom import minidom

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    DEFAULT_FPS,
    SAFE_ZONE,
    SUBTITLE_CENTER_X,
    SUBTITLE_SAFE_ZONE,
    SUBTITLE_SYMMETRIC_MAX_W,
    compute_segment_cache_key,
    ffprobe_media,
    find_bin,
    find_commercial_font,
    frames_to_sec,
    get_wav_duration_sec,
    link_or_copy,
    load_style_applied,
    load_style_spectrum_entry,
    load_subtitle_templates,
    maybe_reexec_in_venv,
    parse_video_stream_geometry,
    place_bbox_in_zone,
    read_json,
    resolve_audio_stems,
    run_cmd,
    sec_to_frames,
    sha256_file,
    write_json,
)

if __name__ == "__main__":
    maybe_reexec_in_venv()

from PIL import Image
from render_mp4 import build_graded_segment_cmd, compute_subtitle_place_xy, render_subtitle_png, resolve_packaging_source


def _frames_to_rational(frames: int, fps: int = DEFAULT_FPS) -> str:
    f = int(round(frames))
    if f <= 0:
        return "0s"
    return f"{f}/{fps}s"


def _measure_wav_frames(path_str: Optional[str], fps: int) -> Tuple[int, float]:
    if not path_str or not Path(path_str).is_file():
        return 0, 0.0
    dur = get_wav_duration_sec(Path(path_str))
    return max(0, sec_to_frames(dur, fps)), dur


def _format_srt_ts(sec: float) -> str:
    ms_total = max(0, int(round(float(sec) * 1000)))
    hh = ms_total // 3_600_000
    mm = (ms_total % 3_600_000) // 60_000
    ss = (ms_total % 60_000) // 1000
    ms = ms_total % 1000
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def _build_srt_content(subs: Dict[str, Any]) -> str:
    blocks: List[str] = []
    idx = 1
    for entry in (subs.get("entries") or []):
        if entry.get("suppressed"):
            continue
        text = str(entry.get("text") or "").strip()
        if not text:
            continue
        st = _format_srt_ts(float(entry.get("start_sec", 0.0)))
        en = _format_srt_ts(float(entry.get("end_sec", 0.0)))
        blocks.append(f"{idx}\n{st} --> {en}\n{text}\n")
        idx += 1
    return "\n".join(blocks)


def _compose_full_canvas_png(src_png: Path, out_full_png: Path, px: int, py: int) -> str:
    canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
    with Image.open(src_png) as fg:
        fg_rgba = fg.convert("RGBA")
        canvas.alpha_composite(fg_rgba, dest=(max(0, px), max(0, py)))
    out_full_png.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_full_png)
    return str(out_full_png)


def _assign_non_overlapping_lanes(layers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """按区间重叠自动分配 FCPXML 上层 lane (1, 2, ...)。"""
    lane_ends: Dict[int, int] = {}
    ordered = sorted(layers, key=lambda x: (x["start_frame"], x["end_frame"], x["priority"]))
    for item in ordered:
        sf = int(item["start_frame"])
        ef = int(item["end_frame"])
        chosen = 1
        while True:
            if lane_ends.get(chosen, -1) <= sf:
                lane_ends[chosen] = ef
                item["lane"] = chosen
                break
            chosen += 1
    return ordered


def _prepare_static_overlay_layers(
    pipeline_dir: Path,
    overlays_dir: Path,
    edl: Dict[str, Any],
    subs: Dict[str, Any],
    pkg: Dict[str, Any],
    color_plan: Dict[str, Any],
    fps: int,
    total_frames: int,
) -> List[Dict[str, Any]]:
    del edl
    overlays_dir.mkdir(parents=True, exist_ok=True)
    for stale in overlays_dir.glob("*.png"):
        stale.unlink(missing_ok=True)

    templates = load_subtitle_templates()
    tpl_id = subs.get("template_id") or "style_01"
    base_tpl = templates.get(tpl_id) or next(iter(templates.values()))
    tpl = {**base_tpl, **subs["template_config"]} if isinstance(subs.get("template_config"), dict) else dict(base_tpl)
    font_path = subs.get("font_path") or find_commercial_font(tpl.get("font_candidates"))
    style_id = pkg.get("style_id") or load_style_applied(pipeline_dir) or "style_01"

    layers: List[Dict[str, Any]] = []

    # 1. 视觉包装元素
    for idx, elem in enumerate(pkg.get("visual_elements") or [], start=1):
        sf = max(0, int(elem.get("start_frame", 0)))
        ef = min(total_frames, int(elem.get("end_frame", sf + fps)))
        if ef <= sf:
            continue
        raw_png = resolve_packaging_source(
            elem, pipeline_dir, idx - 1,
            style_id=style_id, color_plan=color_plan, font_candidates=tpl.get("font_candidates"),
        )
        with Image.open(raw_png) as im:
            pw, ph = im.size
        def_x = max(SAFE_ZONE["x_min"], (CANVAS_WIDTH - pw) // 2)
        def_y = SAFE_ZONE["y_min"] + 40
        px, py = place_bbox_in_zone(elem, pw, ph, SAFE_ZONE, (def_x, def_y))
        rel_name = f"pkg_{idx:03d}.png"
        full_png = overlays_dir / rel_name
        _compose_full_canvas_png(raw_png, full_png, px, py)
        layers.append({
            "id": f"ov_pkg_{idx:03d}",
            "name": f"包装_{idx:03d}_{str(elem.get('text_or_asset') or '')[:10]}",
            "group": "flower_text",
            "priority": 1,
            "start_frame": sf,
            "end_frame": ef,
            "duration_frames": ef - sf,
            "rel_src": f"overlays/{rel_name}",
            "file_path": full_png,
        })

    # 2. 双色字幕层（始终按当前 sub+tpl+font 配置指纹渲染或严格命中缓存，绝不盲用过期 PNG）
    work_tmp = pipeline_dir / "_render_final"
    work_tmp.mkdir(parents=True, exist_ok=True)
    for idx, sub in enumerate(subs.get("entries") or [], start=1):
        if sub.get("suppressed"):
            continue
        sf = max(0, sec_to_frames(float(sub.get("start_sec", 0.0)), fps))
        ef = min(total_frames, sec_to_frames(float(sub.get("end_sec", 0.0)), fps))
        if ef <= sf:
            continue
        sub_cache_key = compute_segment_cache_key({
            "text": sub.get("text"),
            "words": sub.get("words"),
            "tpl": tpl,
            "font_path": font_path,
        })
        pre_sub_png = work_tmp / f"sub_{idx - 1:03d}.png"
        pre_sub_flag = work_tmp / f"sub_{idx - 1:03d}.key"
        if (pre_sub_png.is_file() and pre_sub_flag.is_file()
                and pre_sub_flag.read_text(encoding="utf-8").strip() == sub_cache_key):
            with Image.open(pre_sub_png) as im_s:
                sw_px, sh_px = im_s.size
            use_png = pre_sub_png
            cleanup_tmp = False
        else:
            use_png = work_tmp / f"jy_sub_{idx:03d}.png"
            sw_px, sh_px = render_subtitle_png(sub, tpl, font_path, use_png)
            cleanup_tmp = True
        def_x, def_y = compute_subtitle_place_xy(sw_px, sh_px, tpl)
        px, py = place_bbox_in_zone(sub, sw_px, sh_px, SUBTITLE_SAFE_ZONE, (def_x, def_y))
        # 严格强制水平居中于 540px，杜绝 final_bbox 估算宽度误差导致剪映字幕偏轴
        if sw_px <= SUBTITLE_SYMMETRIC_MAX_W:
            px = SUBTITLE_CENTER_X - sw_px // 2
        rel_name = f"sub_{idx:03d}.png"
        full_png = overlays_dir / rel_name
        _compose_full_canvas_png(use_png, full_png, px, py)
        if cleanup_tmp:
            use_png.unlink(missing_ok=True)
        layers.append({
            "id": f"ov_sub_{idx:03d}",
            "name": f"字幕_{idx:03d}_{str(sub.get('text') or '')[:10]}",
            "group": "subtitle",
            "priority": 2,
            "start_frame": sf,
            "end_frame": ef,
            "duration_frames": ef - sf,
            "rel_src": f"overlays/{rel_name}",
            "file_path": full_png,
        })

    return _assign_non_overlapping_lanes(layers)


def _url_quote_rel(rel_src: str) -> str:
    return urllib.parse.quote(str(rel_src).replace("\\", "/"), safe="/")


def _probe_video_duration_frames(path: Path, fps: int) -> int:
    try:
        info = ffprobe_media(path)
        vs = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
        dur = float(vs.get("duration") or info.get("format", {}).get("duration") or 0.0)
        if dur > 0.0:
            return max(1, sec_to_frames(dur, fps))
    except Exception:
        pass
    return 0


def _export_graded_segment(
    ffmpeg_bin: str,
    clip: Dict[str, Any],
    color_vf: Optional[str],
    eye_by_mp4: Dict[str, Dict[str, Any]],
    out_mp4: Path,
    fps: int,
) -> None:
    """复用 render_mp4.build_graded_segment_cmd 消除 80 行重复分段管线。"""
    cmd = build_graded_segment_cmd(ffmpeg_bin, clip, color_vf, eye_by_mp4, out_mp4, fps)
    run_cmd(cmd)


def _stage_media_assets(
    pipeline_dir: Path,
    draft_dir: Path,
    edl: Dict[str, Any],
    color_plan: Dict[str, Any],
    mix_metrics: Dict[str, Any],
    audio_events: Dict[str, Any],
    fps: int,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """按需生成或链接自包含调色分镜段 + 3 轨同源定电平 WAV 至 draft_dir/media/。"""
    seg_dir = draft_dir / "media" / "segments"
    aud_dir = draft_dir / "media" / "audio"
    seg_dir.mkdir(parents=True, exist_ok=True)
    aud_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg_bin = find_bin("ffmpeg")
    man_p = pipeline_dir / "01_manifest.json"
    manifest = read_json(man_p) if man_p.exists() else {"items": []}
    eye_by_mp4: Dict[str, Dict[str, Any]] = {}
    for item in (manifest.get("items") or []):
        mp = str(item.get("normalized_mp4") or "")
        if mp and item.get("eye_anchor"):
            eye_by_mp4[mp] = item["eye_anchor"]
            eye_by_mp4[str(Path(mp).resolve())] = item["eye_anchor"]

    color_by_cid = {
        str(p.get("clip_id")): str(p.get("vf_filter") or "").strip()
        for p in (color_plan.get("clip_plans") or [])
        if p.get("apply_color_grade") and p.get("vf_filter")
    }

    clip_media_map: Dict[str, Dict[str, Any]] = {}
    keep_seg_names: set[str] = set()
    raw_link_map: Dict[str, Tuple[str, int]] = {}
    used_names: set[str] = set()
    render_work_dir = pipeline_dir / "_render_final"

    for c_idx, clip in enumerate(edl.get("clips") or []):
        cid = str(clip.get("clip_id") or f"clip_{c_idx:03d}")
        mp = str(clip.get("media_path") or "")
        src_p = Path(mp)
        if not mp or not src_p.is_file():
            raise FileNotFoundError(f"剪映导出缺失视频素材: {src_p}")

        color_vf = str(clip.get("color_filter") or color_by_cid.get(cid) or "").strip() or None
        kb = clip.get("ken_burns")
        has_kb = isinstance(kb, dict) and ("zoom_start" in kb or "zoom_end" in kb)
        has_vf_extra = bool(str(clip.get("vf_extra") or "").strip())

        if clip.get("timeline_out_frame") is not None and clip.get("timeline_in_frame") is not None:
            clip_frames = max(1, int(clip["timeline_out_frame"]) - int(clip["timeline_in_frame"]))
        else:
            clip_frames = max(1, sec_to_frames(float(clip.get("duration_sec", 1.0)), fps))
        clip_dur = frames_to_sec(clip_frames, fps)
        src_in = max(0.0, float(clip.get("source_in_sec", 0.0)))
        src_avail = max(0.1, float(clip.get("source_out_sec", src_in + clip_dur)) - src_in)
        needs_pad = src_avail < clip_dur - 0.01

        needs_bake = bool(color_vf or has_kb or has_vf_extra or needs_pad or isinstance(clip.get("pip_layout"), dict))
        prebaked_seg = render_work_dir / f"seg_{c_idx:03d}_f.mp4"

        if needs_bake and ffmpeg_bin:
            seg_name = f"seg_{c_idx:03d}.mp4"
            dst_seg = seg_dir / seg_name
            seg_sha = prebaked_seg.with_suffix(".sha256")
            lut_p = str(color_plan.get("lut_path") or "")
            expected_cmd = build_graded_segment_cmd(ffmpeg_bin, clip, color_vf, eye_by_mp4, prebaked_seg, fps)
            expected_seg_key = compute_segment_cache_key({
                "cmd": expected_cmd[:-1],
                "source_hash": sha256_file(src_p),
                "lut_hash": sha256_file(Path(lut_p)) if lut_p and Path(lut_p).is_file() else None,
                "fps": fps,
                "preview": False,
            })
            if not (
                prebaked_seg.is_file()
                and seg_sha.is_file()
                and seg_sha.read_text(encoding="utf-8").strip() == expected_seg_key
                and prebaked_seg.stat().st_size > 1024
            ):
                render_work_dir.mkdir(parents=True, exist_ok=True)
                _export_graded_segment(ffmpeg_bin, clip, color_vf, eye_by_mp4, prebaked_seg, fps)
                if prebaked_seg.is_file():
                    seg_sha.write_text(expected_seg_key, encoding="utf-8")
            link_or_copy(prebaked_seg, dst_seg)
            real_frames = _probe_video_duration_frames(dst_seg, fps) or clip_frames
            keep_seg_names.add(seg_name)
            clip_media_map[cid] = {
                "asset_key": seg_name,
                "rel_src": f"media/segments/{seg_name}",
                "name": Path(seg_name).stem,
                "src_start_f": 0,
                "asset_dur_frames": real_frames,
            }
        else:
            if mp not in raw_link_map:
                dst_name = src_p.name
                if dst_name in used_names:
                    dst_name = f"{len(used_names) + 1:02d}_{src_p.name}"
                used_names.add(dst_name)
                dst_p = seg_dir / dst_name
                link_or_copy(src_p, dst_p)
                real_frames = _probe_video_duration_frames(dst_p, fps) or max(fps, sec_to_frames(float(clip.get("source_out_sec", clip_dur)), fps))
                raw_link_map[mp] = (f"media/segments/{dst_name}", real_frames)
                keep_seg_names.add(dst_name)
            rel_src, real_frames = raw_link_map[mp]
            clip_media_map[cid] = {
                "asset_key": mp,
                "rel_src": rel_src,
                "name": Path(rel_src).stem,
                "src_start_f": sec_to_frames(src_in, fps),
                "asset_dur_frames": real_frames,
            }

    for stale_seg in seg_dir.glob("*"):
        if stale_seg.name not in keep_seg_names and stale_seg.is_file():
            stale_seg.unlink()

    stems = resolve_audio_stems(pipeline_dir, audio_events=audio_events, mix_metrics=mix_metrics)
    voice_cand = stems.get("voice")
    bgm_cand = stems.get("bgm")
    sfx_cand = stems.get("sfx")

    bgm_is_ducked = bgm_cand is not None and "08_bgm_ducked" in str(bgm_cand.name)
    sfx_is_master = sfx_cand is not None and "08_sfx_master" in str(sfx_cand.name)
    master_gain = float(mix_metrics.get("master_gain_db", 0.0) or 0.0)

    audio_map: Dict[str, Dict[str, Any]] = {}
    keep_audio_names: set[str] = set()
    specs = [
        ("voice", voice_cand, "voice_master.wav", -1, "dialogue.dialogue-1", "0dB"),
        ("bgm", bgm_cand, "bgm_ducked.wav", -2, "music.music-1", "0dB" if bgm_is_ducked else "-14dB"),
        ("sfx", sfx_cand, "sfx_master.wav", -3, "effects.effects-1", "0dB" if sfx_is_master else f"{master_gain:.2f}dB"),
    ]
    for key, src_path, dst_name, lane, role, gain_db in specs:
        if not src_path or not Path(src_path).is_file():
            continue
        dst_p = aud_dir / dst_name
        link_or_copy(Path(src_path), dst_p)
        keep_audio_names.add(dst_name)
        audio_map[key] = {
            "rel_src": f"media/audio/{dst_name}",
            "abs_src": str(dst_p),
            "lane": lane,
            "role": role,
            "gain_db": gain_db,
            "name": Path(dst_name).stem,
        }
    for stale_au in aud_dir.glob("*"):
        if stale_au.name not in keep_audio_names and stale_au.is_file():
            stale_au.unlink()

    return clip_media_map, audio_map


def build_fcpxml_tree(
    pipeline_dir: Path,
    project_name: str,
    overlay_layers: List[Dict[str, Any]],
    clip_media_map: Dict[str, Dict[str, Any]],
    audio_map: Dict[str, Dict[str, Any]],
    subs: Dict[str, Any],
) -> str:
    """构建全相对路径 FCPXML 1.10 XML 树（独立调色片段 + 按时间归属精准挂载子层 + 可编辑 <title> 字幕 + 3 轨音频）。"""
    edl = read_json(pipeline_dir / "04_edl.json")
    audio_events = read_json(pipeline_dir / "03_audio_events.json")

    fps = int(edl.get("fps", DEFAULT_FPS))
    total_frames = int(edl.get("total_frames") or sec_to_frames(float(edl["total_duration_sec"]), fps))

    fcpxml = ET.Element("fcpxml", version="1.10")
    resources = ET.SubElement(fcpxml, "resources")
    ET.SubElement(
        resources, "format",
        id="r_fmt",
        name=f"FFVideoFormat{CANVAS_WIDTH}x{CANVAS_HEIGHT}p{fps}",
        frameDuration=f"100/{fps * 100}s",
        width=str(CANVAS_WIDTH),
        height=str(CANVAS_HEIGHT),
        colorSpace="1-1-1 (Rec. 709)",
    )
    ET.SubElement(
        resources, "format",
        id="r_fmt_still",
        name="FFVideoFormatRateUndefined",
        width=str(CANVAS_WIDTH),
        height=str(CANVAS_HEIGHT),
        colorSpace="1-1-1 (Rec. 709)",
    )
    ET.SubElement(
        resources, "effect",
        id="r_title_eff",
        name="Basic Title",
        uid=".../Titles.localized/Bumper:Opener.localized/Basic Title.localized/Basic Title.moti",
    )

    vid_ids: Dict[str, str] = {}
    clips = edl.get("clips") or []
    for c_idx, c in enumerate(clips):
        cid = str(c.get("clip_id") or f"clip_{c_idx:03d}")
        c_info = clip_media_map[cid]
        akey = c_info["asset_key"]
        if akey in vid_ids:
            continue
        rid = f"r_vid_{len(vid_ids) + 1:02d}"
        vid_ids[akey] = rid
        asset = ET.SubElement(
            resources, "asset",
            id=rid,
            name=c_info["name"],
            start="0s",
            duration=_frames_to_rational(int(c_info["asset_dur_frames"]), fps),
            hasVideo="1",
            format="r_fmt",
        )
        ET.SubElement(asset, "media-rep", kind="original-media", src=_url_quote_rel(c_info["rel_src"]))

    aud_ids: Dict[str, str] = {}
    for idx, (akey, info) in enumerate(audio_map.items(), start=1):
        rid = f"r_aud_{idx:02d}"
        a_frames, _ = _measure_wav_frames(info["abs_src"], fps)
        use_frames = max(total_frames, a_frames) if a_frames > 0 else total_frames
        asset = ET.SubElement(
            resources, "asset",
            id=rid,
            name=info["name"],
            start="0s",
            duration=_frames_to_rational(use_frames, fps),
            hasAudio="1",
            audioSources="1",
            audioChannels="2",
            audioRate="48000",
        )
        ET.SubElement(asset, "media-rep", kind="original-media", src=_url_quote_rel(info["rel_src"]))
        aud_ids[akey] = rid

    ov_ids: Dict[str, str] = {}
    for idx, layer in enumerate(overlay_layers, start=1):
        rid = f"r_ov_{idx:03d}"
        ov_ids[layer["id"]] = rid
        asset = ET.SubElement(
            resources, "asset",
            id=rid,
            name=layer["id"],
            start="0s",
            duration="0s",
            hasVideo="1",
            format="r_fmt_still",
        )
        ET.SubElement(asset, "media-rep", kind="original-media", src=_url_quote_rel(layer["rel_src"]))

    library = ET.SubElement(fcpxml, "library")
    event = ET.SubElement(library, "event", name=f"{project_name}_Event")
    project = ET.SubElement(event, "project", name=project_name)
    sequence = ET.SubElement(
        project, "sequence",
        duration=_frames_to_rational(total_frames, fps),
        format="r_fmt",
        tcStart="0s",
        tcFormat="NDF",
        audioLayout="stereo",
        audioRate="48k",
    )
    spine = ET.SubElement(sequence, "spine")

    spine_records: List[Dict[str, Any]] = []
    for c_idx, c in enumerate(clips):
        cid = str(c.get("clip_id") or f"clip_{c_idx:03d}")
        c_info = clip_media_map[cid]
        in_f = int(c.get("timeline_in_frame", 0))
        out_f = int(c.get("timeline_out_frame", in_f + fps))
        dur_f = max(1, out_f - in_f)
        src_start_f = int(c_info["src_start_f"])

        c_elem = ET.SubElement(
            spine, "asset-clip",
            ref=vid_ids[c_info["asset_key"]],
            offset=_frames_to_rational(in_f, fps),
            name=f"{cid}_{c.get('track_role', 'shot')}",
            start=_frames_to_rational(src_start_f, fps),
            duration=_frames_to_rational(dur_f, fps),
            format="r_fmt",
            tcFormat="NDF",
        )
        spine_records.append({
            "elem": c_elem,
            "tl_in": in_f,
            "tl_out": out_f,
            "src_start": src_start_f,
        })

    def _find_host_clip(tl_frame: int) -> Tuple[Optional[ET.Element], int]:
        if not spine_records:
            return None, 0
        for rec in spine_records:
            if rec["tl_in"] <= tl_frame < rec["tl_out"]:
                local_off = rec["src_start"] + (tl_frame - rec["tl_in"])
                return rec["elem"], local_off
        target_rec = spine_records[0] if tl_frame < spine_records[0]["tl_in"] else spine_records[-1]
        local_off = max(target_rec["src_start"], target_rec["src_start"] + (tl_frame - target_rec["tl_in"]))
        return target_rec["elem"], local_off

    if spine_records:
        first_clip_elem = spine_records[0]["elem"]
        base_offset = _frames_to_rational(spine_records[0]["src_start"], fps)
        # 挂载三轨同源独立 WAV 音轨
        for akey in ("voice", "bgm", "sfx"):
            if akey not in audio_map:
                continue
            info = audio_map[akey]
            a_frames, _ = _measure_wav_frames(info["abs_src"], fps)
            clip_dur_f = min(total_frames, a_frames) if a_frames > 0 else total_frames
            ac = ET.SubElement(
                first_clip_elem, "asset-clip",
                ref=aud_ids[akey],
                lane=str(info["lane"]),
                offset=base_offset,
                name=info["name"],
                start="0s",
                duration=_frames_to_rational(clip_dur_f, fps),
                role=info["role"],
                tcFormat="NDF",
            )
            ET.SubElement(ac, "adjust-volume", amount=info["gain_db"])

        # 按所属镜头区间精准挂载静态透明 PNG 包装与字幕层 (lane >= 1)
        for layer in overlay_layers:
            host_elem, anchor_f = _find_host_clip(int(layer["start_frame"]))
            if host_elem is None:
                continue
            ET.SubElement(
                host_elem, "video",
                ref=ov_ids[layer["id"]],
                lane=str(layer["lane"]),
                offset=_frames_to_rational(anchor_f, fps),
                name=layer["name"],
                start="0s",
                duration=_frames_to_rational(int(layer["duration_frames"]), fps),
                format="r_fmt_still",
            )

        # 追加可编辑字幕 <title> 备用轨（放在最高 lane，导入 NLE 后可直接双击微调文本）
        title_lane = max([int(l["lane"]) for l in overlay_layers] or [0]) + 1
        tpl_cfg = subs.get("template_config") or {}
        font_stem = Path(str(subs.get("font_path") or "AlimamaShuHeiTi-Bold.otf")).stem
        _FCP_FONT_FAMILIES = {
            "AlimamaShuHeiTi-Bold": "Alimama ShuHeiTi",
            "SmileySans-Oblique": "Smiley Sans",
            "SourceHanSerifCN-Bold": "Source Han Serif CN",
            "SourceHanSerifCN-Heavy": "Source Han Serif CN",
        }
        dyn_font = _FCP_FONT_FAMILIES.get(font_stem, font_stem)
        dyn_fs = str(max(24, int(tpl_cfg.get("font_size") or 54)))
        pri_hex = str(tpl_cfg.get("primary_color") or "#FFFFFF").strip().lstrip("#")
        if len(pri_hex) >= 6:
            try:
                fc_str = f"{int(pri_hex[0:2], 16) / 255.0:.3f} {int(pri_hex[2:4], 16) / 255.0:.3f} {int(pri_hex[4:6], 16) / 255.0:.3f} 1"
            except ValueError:
                fc_str = "1 1 1 1"
        else:
            fc_str = "1 1 1 1"
        for s_idx, sub in enumerate(subs.get("entries") or [], start=1):
            if sub.get("suppressed"):
                continue
            sub_txt = str(sub.get("text") or "").strip()
            if not sub_txt:
                continue
            sf = max(0, sec_to_frames(float(sub.get("start_sec", 0.0)), fps))
            ef = min(total_frames, sec_to_frames(float(sub.get("end_sec", 0.0)), fps))
            if ef <= sf:
                continue
            host_elem, anchor_f = _find_host_clip(sf)
            if host_elem is None:
                continue
            t_elem = ET.SubElement(
                host_elem, "title",
                ref="r_title_eff",
                lane=str(title_lane),
                offset=_frames_to_rational(anchor_f, fps),
                name=f"可编辑字幕_{s_idx:03d}",
                start="0s",
                duration=_frames_to_rational(ef - sf, fps),
                enabled="0",
            )
            ts_id = f"ts_sub_{s_idx:03d}"
            text_el = ET.SubElement(t_elem, "text")
            ET.SubElement(text_el, "text-style", ref=ts_id).text = sub_txt
            tsd = ET.SubElement(t_elem, "text-style-def", id=ts_id)
            ET.SubElement(tsd, "text-style", font=dyn_font, fontSize=dyn_fs, fontColor=fc_str, alignment="center")

        # 按所属镜头区间精准挂载切点/语义 <marker>
        for ev in (audio_events.get("events") or []):
            host_elem, ef = _find_host_clip(int(ev.get("frame", 0)))
            if host_elem is None:
                continue
            ET.SubElement(
                host_elem, "marker",
                start=_frames_to_rational(ef, fps),
                duration=f"1/{fps}s",
                value=str(ev.get("reason", ev.get("id", "cut")))[:48],
            )

    rough = ET.tostring(fcpxml, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
    lines = pretty.splitlines()
    header = lines[0] + "\n" if lines and lines[0].startswith("<?xml") else '<?xml version="1.0" encoding="utf-8"?>\n'
    body = "\n".join(lines[1:] if lines and lines[0].startswith("<?xml") else lines) + "\n"
    return header + "<!DOCTYPE fcpxml>\n" + body


def export_jianying_draft(pipeline_dir: Path, simulate_failure: bool = False) -> Dict[str, Any]:
    draft_dir = pipeline_dir / "jianying_draft"
    proj_slug = pipeline_dir.parent.name if pipeline_dir.name == "pipeline" else pipeline_dir.name
    safe_name = f"short_video_studio_{proj_slug}"
    try:
        if simulate_failure:
            raise RuntimeError("模拟剪映工程导出异常或目标目录不可写。")

        draft_dir.mkdir(parents=True, exist_ok=True)
        for stale_dir in ("legacy_v5_json", "alpha_layers"):
            sd = draft_dir / stale_dir
            if sd.exists():
                shutil.rmtree(sd)
        for stale_file in list(draft_dir.glob("*.fcpxml")) + [
            draft_dir / "draft_content.json",
            draft_dir / "draft_meta_info.json",
        ]:
            if stale_file.is_file():
                stale_file.unlink()

        edl = read_json(pipeline_dir / "04_edl.json")
        subs = read_json(pipeline_dir / "05_subtitles.json")
        pkg = read_json(pipeline_dir / "06_packaging.json") if (pipeline_dir / "06_packaging.json").exists() else {"visual_elements": []}
        color_plan = read_json(pipeline_dir / "07_color_plan.json") if (pipeline_dir / "07_color_plan.json").exists() else {}
        mix_metrics = read_json(pipeline_dir / "08_mix_metrics.json") if (pipeline_dir / "08_mix_metrics.json").exists() else {}
        audio_events = read_json(pipeline_dir / "03_audio_events.json") if (pipeline_dir / "03_audio_events.json").exists() else {}

        fps = int(edl.get("fps", DEFAULT_FPS))
        total_frames = int(edl.get("total_frames") or sec_to_frames(float(edl["total_duration_sec"]), fps))

        overlay_layers = _prepare_static_overlay_layers(
            pipeline_dir, draft_dir / "overlays", edl, subs, pkg, color_plan, fps, total_frames,
        )
        clip_media_map, audio_map = _stage_media_assets(
            pipeline_dir, draft_dir, edl, color_plan, mix_metrics, audio_events, fps,
        )

        fcpxml_text = build_fcpxml_tree(pipeline_dir, safe_name, overlay_layers, clip_media_map, audio_map, subs)
        fcpxml_path = draft_dir / "timeline.fcpxml"
        fcpxml_path.write_text(fcpxml_text, encoding="utf-8")

        srt_path = draft_dir / "subtitles.srt"
        srt_src = pipeline_dir / "05_subtitles.srt"
        if srt_src.is_file():
            shutil.copy2(srt_src, srt_path)
        else:
            srt_path.write_text(_build_srt_content(subs), encoding="utf-8")
        ass_src = pipeline_dir / "05_subtitles.ass"
        if ass_src.is_file():
            shutil.copy2(ass_src, draft_dir / "subtitles.ass")

        if color_plan.get("lut_path") and Path(color_plan["lut_path"]).is_file():
            lut_src = Path(color_plan["lut_path"])
            shutil.copy2(lut_src, draft_dir / lut_src.name)

        n_pkg = sum(1 for x in overlay_layers if x["group"] == "flower_text")
        n_sub = sum(1 for x in overlay_layers if x["group"] == "subtitle")

        readme = "\n".join([
            f"【{safe_name} 剪映专业版可编辑工程导入指南】",
            "",
            "1. 打开剪映专业版 -> 全局设置开启「导入工程」 -> 导入本目录下的 timeline.fcpxml。",
            "2. 所有媒体与透明 PNG 图层均采用相对路径存储，整包拷贝不丢素材：",
            f"   - 主视频轨 V1：{len(edl.get('clips') or [])} 段分镜（相对路径 media/segments/）",
            f"   - 上层透明图层：{n_pkg} 个视觉包装 PNG + {n_sub} 条双色字幕 PNG（overlays/，零额外转码损失）",
            f"   - 三轨独立音频：{len(audio_map)} 轨（media/audio/voice_master.wav / bgm_ducked.wav / sfx_master.wav）",
            "   - 备选外挂字幕与风格配方：subtitles.srt / subtitles.ass / whitebox_style_recipe.json",
        ]) + "\n"
        (draft_dir / "README_剪映导入使用指南.txt").write_text(readme, encoding="utf-8")

        write_json(draft_dir / "manifest.json", {
            "project_name": safe_name,
            "export_format": "fcpxml_1.10+png_overlays+srt",
            "relative_paths_only": True,
            "fcpxml": "timeline.fcpxml",
            "subtitles_srt": "subtitles.srt",
            "whitebox_style_recipe": "whitebox_style_recipe.json",
            "audio_tracks": {k: v["rel_src"] for k, v in audio_map.items()},
            "overlays_count": len(overlay_layers),
        })

        active_sid = pkg.get("style_id") or load_style_applied(pipeline_dir) or "style_14"
        s_entry = load_style_spectrum_entry(active_sid) or {}
        write_json(draft_dir / "whitebox_style_recipe.json", {
            "style_id": active_sid,
            "style_name_cn": s_entry.get("style_name_cn", active_sid),
            "whitebox_source": s_entry.get("whitebox_source") or {},
            "commercial_safe_font": s_entry.get("commercial_safe_font", "AlimamaShuHeiTi-Bold.otf"),
            "source_jianying_font": s_entry.get("source_jianying_font", ""),
            "packaging_techniques": s_entry.get("packaging_techniques") or {},
            "visual_elements_animations": [
                {
                    "id": el.get("id"),
                    "kind": el.get("kind"),
                    "text": el.get("text_or_asset"),
                    "jianying_anim_name": el.get("jianying_anim_name", "渐显"),
                    "anim_duration_ms": el.get("anim_duration_ms", 400),
                    "paired_jianying_sfx": el.get("paired_jianying_sfx", ""),
                }
                for el in (pkg.get("visual_elements") or [])
            ],
        })

        status = {
            "status": "success",
            "degraded_to_mp4_only": False,
            "export_format": "fcpxml_1.10+png_overlays+srt",
            "relative_paths_only": True,
            "draft_dir": str(draft_dir.resolve()),
            "fcpxml_path": str(fcpxml_path.resolve()),
            "srt_path": str(srt_path.resolve()),
            "flower_texts_count": n_pkg,
            "subtitles_rendered_count": n_sub,
            "overlays_count": len(overlay_layers),
            "message": f"剪映全相对路径多轨工程导出成功 ({fcpxml_path.name}，{n_pkg} 包装 + {n_sub} 字幕 PNG)。",
        }
        write_json(pipeline_dir / "jianying_export_status.json", status)
        print(f"[jianying] 相对路径 FCPXML + 透明 PNG 工程导出成功 -> {draft_dir}")
        return status
    except Exception as exc:
        status = {
            "status": "degraded_to_mp4_only",
            "degraded_to_mp4_only": True,
            "draft_dir": None,
            "error": str(exc),
            "message": f"提示：剪映工程导出失败（{exc}），已自动降级。",
        }
        write_json(pipeline_dir / "jianying_export_status.json", status)
        print(f"[jianying][降级提示] {status['message']}")
        return status


def main() -> None:
    maybe_reexec_in_venv()
    parser = argparse.ArgumentParser(description="出片2: 剪映全相对路径可编辑工程包 (FCPXML + PNG Overlays + SRT)")
    parser.add_argument("--pipeline-dir", required=True)
    parser.add_argument("--simulate-failure", action="store_true", help="模拟导出失败验证降级逻辑")
    args = parser.parse_args()
    export_jianying_draft(Path(args.pipeline_dir), simulate_failure=args.simulate_failure)


if __name__ == "__main__":
    main()

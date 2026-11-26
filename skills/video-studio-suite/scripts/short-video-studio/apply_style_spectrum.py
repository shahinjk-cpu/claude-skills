#!/usr/bin/env python3
"""
「风格谱 (Style Spectrum)」运行时应用与 HyperFrames 样板导出器
1. resolve_style_runtime_config(style_id): 供 run_pipeline.py 等脚本读取风格对应的模板、LUT、J-cut 与节奏配置。
2. --apply-pipeline: 将 style_spectrum_applied.json 落盘至流水线目录，绝不污染全局 assets/luts/。
3. --export-hyperframes: 导出无 STYLE-XX 徽标泄漏、零外部 CDN 的 HyperFrames 风格样板 HTML。
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    ASSETS_DIR,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    DEFAULT_FPS,
    maybe_reexec_in_venv,
    read_json,
    resolve_lut_path,
    write_json,
)

if __name__ == "__main__":
    maybe_reexec_in_venv()

from export_hyperframes import attach_hyperframes_launchers

STYLE_DIR = ASSETS_DIR / "style_spectrum"
LIB_PATH = STYLE_DIR / "style_spectrum_library.json"


def load_library() -> Dict[str, Any]:
    if not LIB_PATH.is_file():
        raise FileNotFoundError(f"风格谱主库不存在: {LIB_PATH}")
    return read_json(LIB_PATH)


def get_style_entry(lib: Dict[str, Any], style_id: str) -> Dict[str, Any]:
    for s in lib.get("styles", []):
        if s.get("style_id") == style_id:
            return s
    raise KeyError(f"未找到风格 ID: {style_id}")


def resolve_style_runtime_config(style_id: str) -> Dict[str, Any]:
    """返回指定风格的完整运行时配置（供 run_pipeline.py / Step 4 / Step 7 共享）。"""
    lib = load_library()
    entry = get_style_entry(lib, style_id)
    color = entry.get("color_and_lut") or {}
    beat = entry.get("beat_alignment") or {}
    meta = entry.get("meta") or {}
    lut_file = color.get("lut_file") or f"{style_id}.cube"
    lut_path = resolve_lut_path(lut_file, style_id=style_id)
    j_cut_rec = beat.get("recommended_j_cut_frames")
    j_cut = int(j_cut_rec) if j_cut_rec is not None else 3
    return {
        "style_id": style_id,
        "style_name_cn": entry.get("style_name_cn", style_id),
        "archetype_id": entry.get("archetype_id", "arch_01"),
        "recommended_track": entry.get("recommended_track", "store"),
        "subtitle_template": style_id,
        "lut_file": lut_file,
        "lut_path": str(lut_path) if lut_path.exists() else "",
        "j_cut_frames": j_cut,
        "target_fps": int(round(float(meta.get("fps") or DEFAULT_FPS))),
        "beat_bpm": float(beat.get("estimated_bpm") or 110.0),
        "opening_structure": entry.get("opening_structure") or {},
        "title_cover_layout": entry.get("title_cover_layout") or {},
        "transition_and_packaging": entry.get("transition_and_packaging") or {},
        "packaging_techniques": entry.get("packaging_techniques") or {},
        "pip_composition_spec": entry.get("pip_composition_spec") or {},
        "giant_text_spec": entry.get("giant_text_spec") or {},
        "audio_and_sfx": entry.get("audio_and_sfx") or {},
        "shot_distribution": entry.get("shot_distribution") or {},
        "beat_alignment": beat,
        "commercial_safe_font": entry.get("commercial_safe_font") or "AlimamaShuHeiTi-Bold.otf",
        "source_jianying_font": entry.get("source_jianying_font") or "",
        "plain_cn_pitch": entry.get("plain_cn_pitch") or "",
        "whitebox_source": entry.get("whitebox_source") or {},
    }


def list_styles(lib: Dict[str, Any]) -> None:
    print(f"{'ID':<10} {'名称':<26} {'轨道':<8} {'中位镜长':<9} {'BPM':<7} {'字幕模板'}")
    print("-" * 76)
    for s in lib.get("styles", []):
        sid = s["style_id"]
        name = str(s.get("style_name_cn", ""))[:24]
        track = s.get("recommended_track", "creator")
        med = s.get("shot_distribution", {}).get("median_sec", 0.0)
        bpm = s.get("beat_alignment", {}).get("estimated_bpm", 0.0)
        print(f"{sid:<10} {name:<26} {track:<8} {med:<9.2f} {bpm:<7.1f} {sid}")


def export_hyperframes_html(
    lib: Dict[str, Any],
    style_id: str,
    out_html: Path,
    duration_sec: float = 15.0,
    title: str = "核心视觉样板",
) -> Path:
    """生成零外链 CDN、零可见 STYLE-XX 徽标的 HyperFrames 风格样板 HTML。"""
    entry = get_style_entry(lib, style_id)
    sub = entry.get("subtitle_spec") or {}
    color = entry.get("color_and_lut") or {}
    palette = color.get("top5_palette_hex") or ["#111827", "#38BDF8", "#FFFFFF"]
    bg_hex = palette[0] if palette else "#111827"
    accent_hex = palette[1] if len(palette) > 1 else "#FACC15"

    dur = max(1.0, float(duration_sec))
    if out_html.suffix.lower() != ".html":
        out_html = out_html / "index.html"
    out_html.parent.mkdir(parents=True, exist_ok=True)
    safe_title = html.escape(str(title or "核心视觉样板"))

    y_px = min(1400, max(980, int(sub.get("safe_y_px_1080x1920") or 1320)))
    font_sz = max(36, int(sub.get("font_size_1080p_px") or 58))
    pri_col = str(sub.get("primary_color") or "#FFFFFF")
    kw_col = str(sub.get("keyword_color") or accent_hex)
    stroke_col = str(sub.get("stroke_color") or "#0D1117")
    stroke_w = int(sub.get("stroke_width") or 0)
    stroke_css = "0px" if stroke_w <= 0 else f"{max(1, stroke_w * 2)}px {stroke_col}"

    html_doc = "\n".join([
        "<!DOCTYPE html>",
        '<html lang="zh-CN">',
        "<head>",
        '  <meta charset="utf-8" />',
        f"  <title>{safe_title}</title>",
        "  <style>",
        f"    html, body {{ margin:0; padding:0; width:{CANVAS_WIDTH}px; height:{CANVAS_HEIGHT}px; overflow:hidden; background:{bg_hex}; }}",
        f"    #main {{ position:relative; width:{CANVAS_WIDTH}px; height:{CANVAS_HEIGHT}px; font-family:sans-serif; }}",
        f"    .headline {{ position:absolute; left:96px; right:200px; top:220px; font-size:68px; font-weight:800; color:{pri_col}; line-height:1.2; }}",
        f"    .accent-bar {{ display:block; width:88px; height:10px; border-radius:5px; background:{accent_hex}; margin-bottom:24px; }}",
        f"    .sub-line {{ position:absolute; left:220px; right:220px; top:{y_px}px; text-align:center; font-size:{font_sz}px; font-weight:800; color:{pri_col}; -webkit-text-stroke:{stroke_css}; paint-order:stroke fill; }}",
        f"    .kw {{ color:{kw_col}; }}",
        "  </style>",
        "</head>",
        "<body>",
        f'  <div id="main" data-composition-id="main" data-no-timeline data-start="0" data-duration="{dur:.4f}" data-fps="{DEFAULT_FPS}" data-width="{CANVAS_WIDTH}" data-height="{CANVAS_HEIGHT}">',
        '    <div id="sample-headline" class="clip headline" data-start="0" data-duration="{0:.4f}" data-track-index="1">'.format(min(dur, 3.0)),
        '      <span class="accent-bar"></span>',
        f"      <span>{safe_title}</span>",
        "    </div>",
        f'    <div id="sample-caption" class="clip sub-line" data-start="0" data-duration="{dur:.4f}" data-track-index="2">核心<span class="kw">关键信息</span>直观呈现</div>',
        "  </div>",
        "</body>",
        "</html>",
    ]) + "\n"
    out_html.write_text(html_doc, encoding="utf-8")
    if out_html.name == "index.html":
        config = out_html.parent / "hyperframes.json"
        if not config.exists():
            write_json(config, {"media": {"autoProxy": True}})
        attach_hyperframes_launchers(out_html.parent)
    print(f"[apply-style] HyperFrames 样板 HTML 已导出 -> {out_html}")
    return out_html


def apply_to_pipeline(lib: Dict[str, Any], style_id: str, pipeline_dir: Path) -> Path:
    """将风格参数写入 pipeline_dir/style_spectrum_applied.json，绝不修改全局 assets/。"""
    entry = get_style_entry(lib, style_id)
    rt = resolve_style_runtime_config(style_id)
    pipeline_dir.mkdir(parents=True, exist_ok=True)
    out = pipeline_dir / "style_spectrum_applied.json"
    write_json(out, {
        "style_id": style_id,
        "style_name_cn": entry.get("style_name_cn"),
        "archetype_id": entry.get("archetype_id"),
        "recommended_track": rt["recommended_track"],
        "subtitle_template": rt["subtitle_template"],
        "lut_file": rt["lut_file"],
        "lut_path": rt["lut_path"],
        "j_cut_frames": rt["j_cut_frames"],
        "target_fps": rt["target_fps"],
        "beat_bpm": rt["beat_bpm"],
        "color_and_lut": entry.get("color_and_lut"),
        "subtitle_spec": entry.get("subtitle_spec"),
        "transition_and_packaging": entry.get("transition_and_packaging"),
        "opening_structure": entry.get("opening_structure"),
        "title_cover_layout": rt["title_cover_layout"],
        "subtitle_symmetry_lock": entry.get("subtitle_symmetry_lock"),
        "broll_overlay_ratio_target": entry.get("broll_overlay_ratio_target"),
        "broll_ambient_sound_policy": entry.get("broll_ambient_sound_policy"),
        "dual_bgm_structure": entry.get("dual_bgm_structure"),
        "multi_zone_flower_spec": entry.get("multi_zone_flower_spec"),
        "packaging_techniques": entry.get("packaging_techniques"),
        "pip_composition_spec": entry.get("pip_composition_spec"),
        "giant_text_spec": entry.get("giant_text_spec"),
        "audio_and_sfx": entry.get("audio_and_sfx"),
        "shot_distribution": entry.get("shot_distribution"),
        "beat_alignment": entry.get("beat_alignment"),
        "commercial_safe_font": entry.get("commercial_safe_font"),
        "source_jianying_font": entry.get("source_jianying_font"),
        "plain_cn_pitch": entry.get("plain_cn_pitch"),
        "whitebox_source": entry.get("whitebox_source"),
    })
    print(f"[apply-style] 已应用 {style_id} ({entry.get('style_name_cn')}) -> {out}")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="应用「风格谱」至流水线或导出 HyperFrames 样板")
    parser.add_argument("--list", action="store_true", help="列出全部风格谱")
    parser.add_argument("--style-id", help="风格 ID（如 style_02）")
    parser.add_argument("--apply-pipeline", help="目标流水线目录")
    parser.add_argument("--export-hyperframes", help="导出 HyperFrames HTML 目录或文件路径")
    parser.add_argument("--duration", type=float, default=15.0, help="样板时长（秒）")
    parser.add_argument("--title", default="核心视觉样板", help="样板标题")
    parser.add_argument("--print-config", action="store_true", help="打印运行时 JSON 配置")
    args = parser.parse_args()

    lib = load_library()
    if args.list:
        list_styles(lib)
        return
    if not args.style_id:
        parser.error("请指定 --style-id 或使用 --list")

    if args.print_config:
        print(json.dumps(resolve_style_runtime_config(args.style_id), ensure_ascii=False, indent=2))
    if args.apply_pipeline:
        apply_to_pipeline(lib, args.style_id, Path(args.apply_pipeline))
    if args.export_hyperframes:
        export_hyperframes_html(
            lib, args.style_id, Path(args.export_hyperframes),
            duration_sec=args.duration, title=args.title,
        )


if __name__ == "__main__":
    main()

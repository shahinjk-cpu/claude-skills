#!/usr/bin/env python3
"""
成片渲染器：合成 1080x1920 30fps BT.709 竖屏成片 MP4 (output_preview.mp4 / output_final.mp4)。
严格对齐流水线权威 Schema：
- 01_manifest.json: items[*], normalized_mp4, faces[*].bbox ([x1,y1,x2,y2] 0..1 归一化), eye_anchor
- 04_edl.json: clips[*], timeline_in_frame/timeline_out_frame, vf_extra, ken_burns ({zoom_start, zoom_end})
- 05_subtitles.json: entries[*], final_bbox/bbox, suppressed
- 06_packaging.json: visual_elements[*], kind, text_or_asset, start_frame/end_frame, final_bbox/bbox
- 07_color_plan.json: clip_plans[*], apply_color_grade, vf_filter (完整 eq+colorbalance+lut3d)
- 08_mix_metrics.json: master_wav (08_mixed_master.wav)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    BT709_FFMPEG_ARGS,
    BT709_VF_SUFFIX,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    DEFAULT_FPS,
    SAFE_ZONE,
    SUBTITLE_CENTER_X,
    SUBTITLE_SAFE_ZONE,
    SUBTITLE_SYMMETRIC_MAX_W,
    compute_centered_crop_frac,
    compute_crop_transform,
    compute_segment_cache_key,
    contrast_ratio,
    ffprobe_media,
    find_bin,
    find_commercial_font,
    fit_text_line,
    frames_to_sec,
    get_cached_font,
    get_wav_duration_sec,
    hex_to_rgba,
    load_style_applied,
    load_style_spectrum_entry,
    load_subtitle_templates,
    maybe_reexec_in_venv,
    parse_manifest_faces,
    parse_video_stream_geometry,
    read_json,
    run_cmd,
    sec_to_frames,
    sha256_file,
    write_json,
)

if __name__ == "__main__":
    maybe_reexec_in_venv()

from generate_code_broll import resolve_style_palette

from PIL import Image, ImageDraw, ImageFilter


def parse_hex_rgba(hex_str: str, default_alpha: int = 255) -> Tuple[int, int, int, int]:
    return hex_to_rgba(hex_str, default=(255, 255, 255, int(default_alpha)), default_alpha=int(default_alpha))


@lru_cache(maxsize=256)
def _render_glyph_bytes(font_path_key: str, font_size: int, ch: str) -> bytes:
    fnt = get_cached_font(None if font_path_key == "__default__" else font_path_key, font_size)
    img = Image.new("L", (48, 48), 0)
    ImageDraw.Draw(img).text((4, 4), ch, font=fnt, fill=255)
    return img.tobytes()


@lru_cache(maxsize=2048)
def _char_is_tofu(font_key: str, font_size: int, ch: str) -> bool:
    if ch.isspace():
        return False
    if ch in ("\ufffe", "\ufffd"):
        return True
    ch_bytes = _render_glyph_bytes(font_key, font_size, ch)
    if not any(ch_bytes):
        return True
    tofu_sig = _render_glyph_bytes(font_key, font_size, "\ufffe")
    return ch_bytes == tofu_sig


def compute_subtitle_place_xy(img_w: int, img_h: int, tpl: Dict[str, Any]) -> Tuple[int, int]:
    """按画布绝对水平正中 x=540px 居中放置字幕（对称安全带 [220, 860]），垂直默认对齐黄金水位 1310px。"""
    y_center = int(tpl.get("safe_y_center", tpl.get("y_center", 1310)))
    px = SUBTITLE_CENTER_X - img_w // 2
    if img_w > SUBTITLE_SYMMETRIC_MAX_W:
        px = max(SUBTITLE_SAFE_ZONE["x_min"], min(px, SUBTITLE_SAFE_ZONE["x_max"] - img_w))
    py = max(SUBTITLE_SAFE_ZONE["y_min"], min(y_center - img_h // 2, SUBTITLE_SAFE_ZONE["y_max"] - img_h))
    return int(px), int(py)


def render_subtitle_png(
    entry: Dict[str, Any],
    tpl: Dict[str, Any],
    font_path: Optional[str],
    out_png: Path,
) -> Tuple[int, int]:
    """按模板样式与字词高亮信息渲染透明字幕 PNG：整行按真实墨迹包围盒严格几何居中，且宽度严格 <=640px 保绝对居中。"""
    words = entry.get("words") or []
    raw_text = str(entry.get("text") or "").strip()
    if not raw_text and words:
        raw_text = "".join(str(w.get("word", "")) for w in words)

    orig_fs = max(24, int(tpl.get("font_size", 62)))
    orig_stroke_w = int(tpl.get("stroke_width", 4))
    kw_scale = float(tpl.get("keyword_scale", 1.133))

    bg_hex = str(tpl.get("bg_box_color") or tpl.get("bg_box") or "none").strip()
    bg_rgba = parse_hex_rgba(bg_hex, 210) if (bg_hex and bg_hex.lower() != "none") else (0, 0, 0, 0)
    has_bg = bool(bg_hex and bg_hex.lower() != "none" and bg_rgba[3] > 0)
    bg_radius = int(tpl.get("bg_radius", 18))
    pad_x = 28 if has_bg else 14
    pad_y = 18 if has_bg else 12

    max_line_w = SUBTITLE_SYMMETRIC_MAX_W - pad_x * 2
    lines_text = raw_text.splitlines() if "\n" in raw_text else [raw_text]
    if not lines_text:
        lines_text = [""]

    base_sz = orig_fs
    probe_img = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    probe_draw = ImageDraw.Draw(probe_img)
    while base_sz > 28:
        fnt_probe = get_cached_font(font_path, int(round(base_sz * max(1.0, (1.0 + kw_scale) * 0.5))))
        sw_p = 0 if orig_stroke_w <= 0 else max(1, int(round(orig_stroke_w * max(0.75, base_sz / float(orig_fs)))))
        widest = max(
            (probe_draw.textbbox((0, 0), ln, font=fnt_probe, stroke_width=sw_p)[2]
             - probe_draw.textbbox((0, 0), ln, font=fnt_probe, stroke_width=sw_p)[0]
             + max(0, len(ln) - 1) * max(1, sw_p // 2))
            for ln in lines_text
        )
        if widest <= max_line_w:
            break
        base_sz -= 2

    stroke_w = 0 if orig_stroke_w <= 0 else max(1, int(round(orig_stroke_w * max(0.75, base_sz / float(orig_fs)))))
    primary_rgba = parse_hex_rgba(tpl.get("primary_color", "#FFFFFF"))
    kw_rgba = parse_hex_rgba(tpl.get("keyword_color", "#FFE28A"))
    stroke_rgba = parse_hex_rgba(tpl.get("stroke_color", "#000000"))
    shadow_rgba = parse_hex_rgba(tpl.get("shadow_color", "#000000C8"), 200)

    fallback_font = None
    if tpl.get("font_fallback"):
        fallback_font = find_commercial_font(tpl.get("font_fallback"), verified_only=True)
    if not fallback_font:
        fallback_font = find_commercial_font(verified_only=True)

    kw_set = set(str(k) for k in (entry.get("keywords") or []))

    tokens: List[Tuple[str, bool, bool]] = []
    if words and "".join(str(w.get("word", "")) for w in words).replace("\n", "") == raw_text.replace("\n", ""):
        raw_idx = 0
        for w_obj in words:
            w_str = str(w_obj.get("word", ""))
            is_kw = bool(w_obj.get("is_keyword", False)) or (w_str in kw_set)
            for ch in w_str:
                while raw_idx < len(raw_text) and raw_text[raw_idx] == "\n":
                    tokens.append(("\n", False, True))
                    raw_idx += 1
                tokens.append((ch, is_kw, False))
                raw_idx += 1
        while raw_idx < len(raw_text):
            if raw_text[raw_idx] == "\n":
                tokens.append(("\n", False, True))
            else:
                tokens.append((raw_text[raw_idx], False, False))
            raw_idx += 1
    else:
        kw_flags = [False] * len(raw_text)
        for kw in kw_set:
            if not kw:
                continue
            start = 0
            while True:
                idx = raw_text.find(kw, start)
                if idx < 0:
                    break
                for j in range(idx, idx + len(kw)):
                    kw_flags[j] = True
                start = idx + len(kw)
        for ch, flag in zip(raw_text, kw_flags):
            tokens.append((ch, flag, ch == "\n"))

    # 逐行收集字符排版元信息
    lines: List[List[Tuple[str, Any, Tuple[int, int, int, int], int, int, int]]] = [[]]
    line_max_ascents: List[int] = [0]
    fk = font_path or "__default__"
    inter_pad = max(1, stroke_w // 2) if stroke_w > 0 else 0
    for ch, is_kw, is_nl in tokens:
        if is_nl:
            lines.append([])
            line_max_ascents.append(0)
            continue
        ch_sz = int(round(base_sz * (kw_scale if is_kw else 1.0)))
        fnt = get_cached_font(font_path, ch_sz)
        if _char_is_tofu(fk, ch_sz, ch) and fallback_font and fallback_font != font_path:
            fnt = get_cached_font(fallback_font, ch_sz)
        bb = probe_draw.textbbox((0, 0), ch, font=fnt, stroke_width=stroke_w)
        try:
            adv_w = max(4, int(round(fnt.getlength(ch))) + inter_pad)
        except Exception:
            adv_w = max(4, (bb[2] - bb[0]) + 2)
        try:
            ascent, _descent = fnt.getmetrics()
        except Exception:
            ascent = ch_sz
        rgba = kw_rgba if is_kw else primary_rgba
        lines[-1].append((ch, fnt, rgba, adv_w, ch_sz, int(ascent)))
        line_max_ascents[-1] = max(line_max_ascents[-1], int(ascent))

    use_shadow = bool(tpl.get("shadow", True))
    sh_off = tpl.get("shadow_offset") or [2, 3]
    sh_dx = int(sh_off[0]) if len(sh_off) >= 1 else 2
    sh_dy = int(sh_off[1]) if len(sh_off) >= 2 else 3

    # 先将每行单独渲染至临时透明层并精确裁出真实墨迹包围盒，消除字形左轴承/末字尾距造成的不对称偏移
    rendered_lines: List[Image.Image] = []
    for ln_idx, ln in enumerate(lines):
        if not ln:
            rendered_lines.append(Image.new("RGBA", (40, max(36, base_sz)), (0, 0, 0, 0)))
            continue
        est_ln_w = sum(item[3] for item in ln) + max(80, stroke_w * 4 + abs(sh_dx) * 4 + base_sz * 2)
        max_asc = max(base_sz // 2, line_max_ascents[ln_idx])
        est_ln_h = int(max_asc * 2.2) + stroke_w * 4 + abs(sh_dy) * 4 + 40
        tmp_ln = Image.new("RGBA", (est_ln_w, est_ln_h), (0, 0, 0, 0))
        tdraw = ImageDraw.Draw(tmp_ln)
        cur_x = 40 + stroke_w * 2
        base_top = 24 + stroke_w * 2
        for ch, fnt, rgba, adv_w, _ch_sz, asc in ln:
            y_off = base_top + max(0, max_asc - asc)
            if use_shadow:
                tdraw.text(
                    (cur_x + sh_dx, y_off + sh_dy),
                    ch,
                    font=fnt,
                    fill=shadow_rgba,
                    stroke_width=stroke_w,
                    stroke_fill=shadow_rgba if stroke_w > 0 else None,
                )
            tdraw.text(
                (cur_x, y_off),
                ch,
                font=fnt,
                fill=rgba,
                stroke_width=stroke_w,
                stroke_fill=stroke_rgba if stroke_w > 0 else None,
            )
            cur_x += adv_w
        ink_bb = tmp_ln.getbbox()
        if ink_bb is not None:
            cropped = tmp_ln.crop(ink_bb)
        else:
            cropped = Image.new("RGBA", (40, max(36, base_sz)), (0, 0, 0, 0))
        if cropped.width > max_line_w:
            ratio = max_line_w / float(cropped.width)
            cropped = cropped.resize(
                (max_line_w, max(24, int(round(cropped.height * ratio)))),
                Image.Resampling.LANCZOS,
            )
        rendered_lines.append(cropped)

    line_gap = 10 if len(rendered_lines) > 1 else 0
    max_ink_w = max((im.width for im in rendered_lines), default=60)
    total_w = max(80, min(SUBTITLE_SYMMETRIC_MAX_W, max_ink_w + pad_x * 2))
    # 保证偶数宽以便 (CANVAS_WIDTH - total_w) // 2 精准对称无 0.5px 抖动
    if total_w % 2 == 1 and total_w < SUBTITLE_SYMMETRIC_MAX_W:
        total_w += 1
    total_h = max(48, sum(im.height for im in rendered_lines) + line_gap * max(0, len(rendered_lines) - 1) + pad_y * 2)

    canvas = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    if has_bg:
        draw.rounded_rectangle([(0, 0), (total_w - 1, total_h - 1)], radius=bg_radius, fill=bg_rgba)

    cur_y = pad_y
    for im_ln in rendered_lines:
        paste_x = (total_w - im_ln.width) // 2
        canvas.alpha_composite(im_ln, dest=(paste_x, cur_y))
        cur_y += im_ln.height + line_gap

    out_png.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_png)
    return total_w, total_h


def _resolve_packaging_palette(style_id: str, track: str = "store") -> Dict[str, Tuple[int, int, int, int]]:
    pal = resolve_style_palette(style_id, track=track)
    bg_rgba = parse_hex_rgba(pal.get("card_bg_hex") or pal.get("bg_hex", "#12151E"), 232)
    accent_rgba = parse_hex_rgba(pal.get("accent_hex", "#FFD54F"), 255)
    text_rgba = parse_hex_rgba(pal.get("title_hex", "#F8FAFC"), 255)
    border_rgba = parse_hex_rgba(pal.get("border_hex") or pal.get("accent_hex", "#FFD54F"), 220)
    if contrast_ratio(text_rgba[:3], bg_rgba[:3]) < 4.5:
        text_rgba = (17, 24, 39, 255) if pal.get("is_light") else (255, 255, 255, 255)
    return {
        "bg": bg_rgba,
        "accent": accent_rgba,
        "text": text_rgba,
        "border": border_rgba,
    }


def _fit_line(draw: Any, text: str, font_path: Optional[str], max_w: int, start_sz: int, min_sz: int = 24) -> Tuple[Any, str]:
    return fit_text_line(draw, str(text or ""), font_path, max_width=max_w, max_size=start_sz, min_size=min_sz)


def render_packaging_png(
    elem: Dict[str, Any],
    style_id: str = "style_01",
    color_plan: Optional[Dict[str, Any]] = None,
    font_candidates: Optional[List[str]] = None,
) -> Image.Image:
    """渲染视觉包装 PNG（兼容 06_packaging.json: kind/text_or_asset 及通用字段）。"""
    del color_plan
    pal = _resolve_packaging_palette(style_id)
    font_path = find_commercial_font(font_candidates)
    elem_kind = str(elem.get("kind") or elem.get("type") or "flower_text")
    main_text = str(elem.get("text_or_asset") or elem.get("text") or "").strip()
    max_safe_w = SAFE_ZONE["x_max"] - SAFE_ZONE["x_min"]

    if elem_kind == "persistent_top_bar":
        # 顶部常驻主题标语栏（强对比保护 >= 4.5）
        text = main_text or "核心重点"
        fg_rgba = parse_hex_rgba(elem.get("fg_hex") or "#FFF589")
        pill_bg = (18, 22, 28)
        if contrast_ratio(fg_rgba[:3], pill_bg) < 4.5:
            fg_rgba = (255, 245, 137, 255)
        probe = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
        pdraw = ImageDraw.Draw(probe)
        fnt, fitted = _fit_line(pdraw, text, font_path, SUBTITLE_SYMMETRIC_MAX_W - 48, 34, 22)
        bb = pdraw.textbbox((0, 0), fitted, font=fnt)
        tw, th = max(40, bb[2] - bb[0]), max(22, bb[3] - bb[1])
        w = min(SUBTITLE_SYMMETRIC_MAX_W, tw + 56)
        h = max(56, th + 24)
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([(0, 0), (w - 1, h - 1)], radius=h // 2, fill=(16, 20, 28, 228), outline=fg_rgba, width=3)
        draw.text((w // 2, h // 2), fitted, font=fnt, fill=fg_rgba, anchor="mm")
        return img

    if elem_kind == "quote_citation_card":
        # 模版级大引号毛玻璃金句引语卡（适用于 style_08 / style_09 / style_16 等）
        raw_quote = (main_text or "“核心实证观点”").strip().strip("“”\"'")
        sub_txt = str(elem.get("subtext") or "—— 核心观点实证").strip()
        fg_rgba = parse_hex_rgba(elem.get("fg_hex") or "#FFF589")
        acc_rgba = parse_hex_rgba(elem.get("accent_hex") or "#FF4D4F")
        card_bg = (14, 18, 26, 232)
        if contrast_ratio(fg_rgba[:3], card_bg[:3]) < 4.5:
            fg_rgba = (255, 245, 137, 255)
        w = min(SUBTITLE_SYMMETRIC_MAX_W, 608)
        h = 136
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle([(2, 4), (w - 3, h - 2)], radius=20, fill=card_bg, outline=fg_rgba, width=3)
        draw.rounded_rectangle([(14, 18), (24, h - 18)], radius=5, fill=acc_rgba)
        q_fnt = get_cached_font(font_path, 58)
        draw.text((34, 6), "“", font=q_fnt, fill=acc_rgba, stroke_width=2, stroke_fill=(0, 0, 0, 240))
        draw.text((w - 58, h - 68), "”", font=q_fnt, fill=acc_rgba, stroke_width=2, stroke_fill=(0, 0, 0, 240))
        main_fnt, fitted_q = _fit_line(draw, raw_quote, font_path, w - 124, 46, 26)
        draw.text((w // 2 + 6, 52), fitted_q, font=main_fnt, fill=fg_rgba, anchor="mm", stroke_width=4, stroke_fill=(0, 0, 0, 245))
        sub_fnt, fitted_sub = _fit_line(draw, sub_txt, font_path, w - 140, 24, 18)
        draw.line([(48, 92), (w - 64, 92)], fill=(255, 245, 137, 110), width=1)
        draw.text((w // 2 + 6, 112), fitted_sub, font=sub_fnt, fill=(240, 244, 250, 245), anchor="mm", stroke_width=2, stroke_fill=(0, 0, 0, 220))
        return img

    burst_tags = [str(t).strip() for t in (elem.get("burst_tags") or []) if str(t).strip()]
    if elem_kind in ("stamp_tag", "flower_text") and len(burst_tags) >= 2:
        # 三连弹卡 / 三阶复利词条（适用于 style_08 / style_09 / style_16 等）
        tags = burst_tags[:3]
        fg_rgba = parse_hex_rgba(elem.get("fg_hex") or "#FFF589")
        acc_rgba = parse_hex_rgba(elem.get("accent_hex") or "#FF1837")
        w = min(SUBTITLE_SYMMETRIC_MAX_W, 616)
        h = 98
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        n_t = len(tags)
        gap = 12
        cell_w = (w - gap * (n_t - 1)) // n_t
        for ti, tg in enumerate(tags):
            cx0 = ti * (cell_w + gap)
            cx1 = cx0 + cell_w - 1
            is_hi = (ti == n_t - 1)
            bg_c = (180, 24, 38, 238) if is_hi else (18, 22, 30, 232)
            bd_c = fg_rgba if is_hi else acc_rgba
            tx_c = (255, 245, 137, 255) if is_hi else (255, 255, 255, 255)
            draw.rounded_rectangle([(cx0, 8), (cx1, h - 8)], radius=16, fill=bg_c, outline=bd_c, width=3)
            tfnt, tfit = _fit_line(draw, tg[:5], font_path, cell_w - 22, 38, 22)
            draw.text(((cx0 + cx1) // 2, h // 2), tfit, font=tfnt, fill=tx_c, anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0, 240))
        return img

    if elem_kind == "center_burst_title":
        # 真·巨字冲击引擎（126px–164px 四大剪映爆款巨字排版）
        giant_mode = str(elem.get("giant_mode") or "giant_smash_single")
        req_fs = max(112, min(168, int(elem.get("font_size_px") or 140)))
        fg_rgba = parse_hex_rgba(elem.get("fg_hex") or "#FFE28A")
        acc_rgba = parse_hex_rgba(elem.get("accent_hex") or "#FF2438")
        st_rgba = parse_hex_rgba(elem.get("stroke_hex") or "#000000")
        if contrast_ratio(fg_rgba[:3], (12, 16, 22)) < 4.5:
            fg_rgba = (255, 245, 137, 255)
        if contrast_ratio(acc_rgba[:3], (12, 16, 22)) < 3.8:
            acc_rgba = (255, 77, 79, 255)
        tag_label = str(elem.get("tag_label") or "核心重点").strip()[:6]
        raw_txt = (main_text or "核心重点").strip().strip("“”\"'")[:6]
        max_w_cap = SUBTITLE_SYMMETRIC_MAX_W  # 640px

        if giant_mode == "giant_numeric_trio":
            # style_16, 11, 22：三格巨型数字/核心字连跳砸屏 (138px–164px)
            chars = list(raw_txt[:3]) if len(raw_txt) >= 3 else list((raw_txt + "100")[:3])
            w, h = max_w_cap, 164
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            # 顶部导语横签
            tag_fnt = get_cached_font(font_path, 22)
            draw.rounded_rectangle([(w // 2 - 96, 2), (w // 2 + 96, 32)], radius=14, fill=(18, 22, 30, 235), outline=fg_rgba, width=2)
            draw.text((w // 2, 17), f"★ {tag_label} ★", font=tag_fnt, fill=fg_rgba, anchor="mm")
            cell_w = 178
            gap = 18
            total_cw = cell_w * 3 + gap * 2
            x_start = (w - total_cw) // 2
            c_fnt = get_cached_font(font_path, min(104, req_fs - 36))
            for ci, ch in enumerate(chars):
                cx0 = x_start + ci * (cell_w + gap)
                cx1 = cx0 + cell_w
                c_bg = (178, 24, 36, 236) if ci == 0 else (20, 24, 34, 232)
                c_bd = fg_rgba if ci == 0 else acc_rgba
                c_fg = (255, 245, 137, 255) if ci > 0 else (255, 255, 255, 255)
                draw.rounded_rectangle([(cx0, 38), (cx1, h - 10)], radius=20, fill=c_bg, outline=c_bd, width=4)
                draw.text(((cx0 + cx1) // 2 + 3, 98 + 4), ch, font=c_fnt, fill=(0, 0, 0, 230), anchor="mm", stroke_width=8, stroke_fill=(0, 0, 0, 230))
                draw.text(((cx0 + cx1) // 2, 98), ch, font=c_fnt, fill=c_fg, anchor="mm", stroke_width=8, stroke_fill=st_rgba)
            return img

        if giant_mode == "giant_dual_clash":
            # style_02, 08, 09, 17, 19：左右/上下双色对撞巨字 (124px–144px)
            mid = max(1, len(raw_txt) // 2) if len(raw_txt) >= 2 else 1
            left_t = raw_txt[:mid]
            right_t = raw_txt[mid:] or tag_label[:2]
            w, h = max_w_cap, 158
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            # 背板斜切警示撞色条
            draw.rounded_rectangle([(18, 22), (w - 18, h - 14)], radius=22, fill=(14, 18, 26, 216), outline=fg_rgba, width=3)
            draw.polygon([(w // 2 + 10, 24), (w - 22, 24), (w - 22, h - 16), (w // 2 - 18, h - 16)], fill=(185, 22, 36, 228))
            f_left, l_fit = _fit_line(draw, left_t, font_path, w // 2 - 36, min(112, req_fs - 24), 48)
            f_right, r_fit = _fit_line(draw, right_t, font_path, w // 2 - 36, min(112, req_fs - 24), 48)
            lx, ly = w // 4 + 6, h // 2 - 2
            rx, ry = (w * 3) // 4 - 4, h // 2 + 6
            draw.text((lx + 4, ly + 5), l_fit, font=f_left, fill=(0, 0, 0, 235), anchor="mm", stroke_width=9, stroke_fill=(0, 0, 0, 235))
            draw.text((lx, ly), l_fit, font=f_left, fill=(255, 255, 255, 255), anchor="mm", stroke_width=9, stroke_fill=st_rgba)
            draw.text((rx + 4, ry + 5), r_fit, font=f_right, fill=(0, 0, 0, 235), anchor="mm", stroke_width=9, stroke_fill=(0, 0, 0, 235))
            draw.text((rx, ry), r_fit, font=f_right, fill=fg_rgba, anchor="mm", stroke_width=9, stroke_fill=st_rgba)
            # 顶部角标
            t_fnt = get_cached_font(font_path, 20)
            draw.rounded_rectangle([(28, 4), (176, 32)], radius=10, fill=fg_rgba, outline=(0, 0, 0, 255), width=2)
            draw.text((102, 18), tag_label[:4], font=t_fnt, fill=(12, 16, 22, 255), anchor="mm")
            return img

        if giant_mode == "giant_vertical_seal":
            # style_04, 06, 13, 20, 23：130px–148px 粗宋大字 + 朱红古风方印章
            w, h = max_w_cap, 154
            img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            f_main, m_fit = _fit_line(draw, raw_txt, font_path, w - 148, min(118, req_fs - 18), 54)
            mx = (w - 76) // 2
            my = h // 2 + 4
            draw.text((mx + 4, my + 5), m_fit, font=f_main, fill=(0, 0, 0, 230), anchor="mm", stroke_width=9, stroke_fill=(0, 0, 0, 230))
            draw.text((mx, my), m_fit, font=f_main, fill=fg_rgba, anchor="mm", stroke_width=9, stroke_fill=st_rgba)
            # 右侧朱红印章签
            sx0, sy0, sx1, sy1 = w - 122, 22, w - 30, h - 22
            draw.rounded_rectangle([(sx0, sy0), (sx1, sy1)], radius=12, fill=(184, 28, 34, 242), outline=(255, 232, 168, 255), width=3)
            s_fnt = get_cached_font(font_path, 24)
            seal_t = tag_label[:4] if len(tag_label) >= 4 else (tag_label + "精选")[:4]
            draw.text(((sx0 + sx1) // 2, sy0 + 32), seal_t[:2], font=s_fnt, fill=(255, 248, 230, 255), anchor="mm")
            draw.text(((sx0 + sx1) // 2, sy0 + 72), seal_t[2:4], font=s_fnt, fill=(255, 248, 230, 255), anchor="mm")
            return img

        # 默认 giant_smash_single：130px–156px 超粗重描边砸屏巨字 + 顶部微导语签
        w, h = max_w_cap, 156
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        t_fnt = get_cached_font(font_path, 22)
        draw.rounded_rectangle([(w // 2 - 104, 2), (w // 2 + 104, 34)], radius=14, fill=(185, 24, 38, 238), outline=fg_rgba, width=2)
        draw.text((w // 2, 18), f"⚡ {tag_label} ⚡", font=t_fnt, fill=(255, 255, 255, 255), anchor="mm")
        f_main, m_fit = _fit_line(draw, raw_txt, font_path, w - 36, min(122, req_fs - 18), 56)
        mx, my = w // 2, 96
        draw.text((mx + 5, my + 6), m_fit, font=f_main, fill=(0, 0, 0, 235), anchor="mm", stroke_width=10, stroke_fill=(0, 0, 0, 235))
        draw.text((mx, my), m_fit, font=f_main, fill=fg_rgba, anchor="mm", stroke_width=10, stroke_fill=st_rgba)
        return img

    if elem_kind in ("stamp_tag", "end_card_cta"):
        # 原生无底框高冲击描边花字与片尾召唤卡
        fg_rgba = parse_hex_rgba(elem.get("fg_hex") or "#FFE28A")
        st_rgba = parse_hex_rgba(elem.get("stroke_hex") or "#000000")
        sh_rgba = (0, 0, 0, 210)
        max_w_cap = SUBTITLE_SYMMETRIC_MAX_W
        target_fs = 64 if elem_kind == "end_card_cta" else 62
        sw_draw = 6
        text = main_text or "核心重点"
        sub_txt = str(elem.get("subtext") or "").strip() if elem_kind == "end_card_cta" else ""

        tmp = Image.new("RGBA", (max_w_cap + 120, 260), (0, 0, 0, 0))
        td = ImageDraw.Draw(tmp)
        f1, t1 = _fit_line(td, text, font_path, max_w_cap - 36, target_fs, 32)
        bb1 = td.textbbox((0, 0), t1, font=f1, stroke_width=sw_draw)
        w1 = max(40, bb1[2] - bb1[0])
        h1 = max(36, bb1[3] - bb1[1])
        x1 = (tmp.width - w1) // 2 - bb1[0]
        y1 = 24 - bb1[1]
        td.text((x1 + 3, y1 + 4), t1, font=f1, fill=sh_rgba, stroke_width=sw_draw, stroke_fill=sh_rgba)
        td.text((x1, y1), t1, font=f1, fill=fg_rgba, stroke_width=sw_draw, stroke_fill=st_rgba)

        if sub_txt:
            f2, t2 = _fit_line(td, sub_txt, font_path, max_w_cap - 48, 34, 22)
            bb2 = td.textbbox((0, 0), t2, font=f2, stroke_width=3)
            w2 = max(40, bb2[2] - bb2[0])
            x2 = (tmp.width - w2) // 2 - bb2[0]
            y2 = 24 + h1 + 14 - bb2[1]
            td.text((x2 + 2, y2 + 3), t2, font=f2, fill=sh_rgba, stroke_width=3, stroke_fill=sh_rgba)
            td.text((x2, y2), t2, font=f2, fill=(255, 255, 255, 255), stroke_width=3, stroke_fill=st_rgba)

        ink = tmp.getbbox()
        if ink is not None:
            crop = tmp.crop(ink)
            pad = 12
            ow = min(max_w_cap, crop.width + pad * 2)
            oh = crop.height + pad * 2
            out_img = Image.new("RGBA", (ow, oh), (0, 0, 0, 0))
            if crop.width > ow - pad * 2:
                ratio = (ow - pad * 2) / float(crop.width)
                crop = crop.resize((ow - pad * 2, max(24, int(round(crop.height * ratio)))), Image.Resampling.LANCZOS)
            out_img.alpha_composite(crop, dest=((ow - crop.width) // 2, (oh - crop.height) // 2))
            return out_img
        return Image.new("RGBA", (240, 84), (0, 0, 0, 0))

    text = main_text or "重点"
    probe = Image.new("RGBA", (8, 8), (0, 0, 0, 0))
    pdraw = ImageDraw.Draw(probe)
    fnt, fitted = _fit_line(pdraw, text, font_path, max_safe_w - 64, 42, 24)
    bb = pdraw.textbbox((0, 0), fitted, font=fnt)
    tw, th = max(40, bb[2] - bb[0]), max(28, bb[3] - bb[1])
    w = min(max_safe_w, tw + 68)
    h = max(72, th + 32)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([(0, 0), (w - 1, h - 1)], radius=18, fill=pal["bg"], outline=pal["border"], width=2)
    draw.rounded_rectangle([(12, 16), (22, h - 16)], radius=5, fill=pal["accent"])
    draw.text((38, (h - th) // 2 - 2), fitted, font=fnt, fill=pal["text"])
    return img


def resolve_packaging_source(
    elem: Dict[str, Any],
    pipeline_dir: Path,
    idx: int,
    style_id: str = "style_01",
    color_plan: Optional[Dict[str, Any]] = None,
    font_candidates: Optional[List[str]] = None,
) -> Path:
    out_png = pipeline_dir / "_render_final" / f"pkg_{idx:03d}.png"
    out_png.parent.mkdir(parents=True, exist_ok=True)
    img = render_packaging_png(elem, style_id=style_id, color_plan=color_plan, font_candidates=font_candidates)
    img.save(out_png)
    return out_png


def _ensure_circle_mask_png(cache_dir: Path, radius_px: int) -> Path:
    """预烘焙抗锯齿圆形灰度蒙版 PNG（替代逐像素 geq 解释器，提速 50x+）。"""
    r = max(16, int(radius_px))
    diam = r * 2
    cache_dir.mkdir(parents=True, exist_ok=True)
    mask_p = cache_dir / f"_pip_circle_mask_{diam}.png"
    if not mask_p.is_file():
        mask = Image.new("L", (diam, diam), 0)
        ImageDraw.Draw(mask).ellipse([(2, 2), (diam - 3, diam - 3)], fill=255)
        mask.save(mask_p)
    return mask_p


def _ensure_circle_ring_png(cache_dir: Path, radius_px: int, border_hex: str = "#FFF589") -> Path:
    """预烘焙平滑圆环人像的发光装饰外环 PNG。"""
    r = max(16, int(radius_px))
    pad = 14
    size = r * 2 + pad * 2
    safe_hex = re.sub(r"[^0-9A-Fa-f]", "", str(border_hex or "FFF589"))[:6] or "FFF589"
    cache_dir.mkdir(parents=True, exist_ok=True)
    ring_p = cache_dir / f"_pip_circle_ring_{r}_{safe_hex}.png"
    if not ring_p.is_file():
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        col = parse_hex_rgba(f"#{safe_hex}")
        d.ellipse([(pad, pad), (size - pad - 1, size - pad - 1)], outline=(236, 227, 207, 240), width=4)
        d.ellipse([(pad - 5, pad - 5), (size - pad + 4, size - pad + 4)], outline=col, width=3)
        d.arc([(pad - 10, pad - 10), (size - pad + 9, size - pad + 9)], start=25, end=115, fill=col, width=4)
        d.arc([(pad - 10, pad - 10), (size - pad + 9, size - pad + 9)], start=205, end=270, fill=(236, 227, 207, 170), width=2)
        img.save(ring_p)
    return ring_p


def _rects_overlap(a: Tuple[int, int, int, int], b: Tuple[int, int, int, int]) -> bool:
    return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])


def _avoid_face_boxes(
    px: int,
    py: int,
    pw: int,
    ph: int,
    faces: List[Dict[str, int]],
    y_min: int,
    y_max: int,
) -> Tuple[int, int]:
    if not faces:
        return px, max(y_min, min(py, y_max - ph))
    face_rects = [(f["x"], f["y"], f["x"] + f["w"], f["y"] + f["h"]) for f in faces]
    step_y = 60
    candidates = [py]
    for d in range(1, 12):
        candidates.append(py + d * step_y)
        candidates.append(py - d * step_y)
    for cy in candidates:
        cy = max(y_min, min(cy, y_max - ph))
        cand_rect = (px, cy, px + pw, cy + ph)
        if not any(_rects_overlap(cand_rect, fr) for fr in face_rects):
            return px, cy
    return px, max(y_min, min(py, y_max - ph))


def _place_from_final_bbox(
    entry: Dict[str, Any],
    pw: int,
    ph: int,
    zone: Dict[str, int],
    default_xy: Tuple[int, int],
    faces: List[Dict[str, int]],
) -> Tuple[int, int]:
    fb = entry.get("final_bbox") or entry.get("bbox")
    if isinstance(fb, dict) and {"x", "y", "w", "h"}.issubset(fb.keys()):
        bx = int(fb["x"]) + (int(fb["w"]) - pw) // 2
        by = int(fb["y"]) + (int(fb["h"]) - ph) // 2
        px = max(zone["x_min"], min(bx, zone["x_max"] - pw))
        py = max(zone["y_min"], min(by, zone["y_max"] - ph))
        return int(px), int(py)
    return _avoid_face_boxes(default_xy[0], default_xy[1], pw, ph, faces, zone["y_min"], zone["y_max"])


def _build_color_filter_for_clip(clip: Dict[str, Any], color_plan: Dict[str, Any]) -> Optional[str]:
    cf_str = str(clip.get("color_filter") or "").strip()
    if cf_str:
        return cf_str
    cid = clip.get("clip_id")
    for item in (color_plan.get("clip_plans") or []):
        if item.get("clip_id") == cid:
            if not item.get("apply_color_grade"):
                return None
            vf = str(item.get("vf_filter") or "").strip()
            return vf or None
    return None


def _resolve_master_wav(pipeline_dir: Path) -> Tuple[Path, Dict[str, Any]]:
    mix_p = pipeline_dir / "08_mix_metrics.json"
    if mix_p.exists():
        mix_metrics = read_json(mix_p)
        cand = Path(mix_metrics.get("master_wav") or (pipeline_dir / "08_mixed_master.wav"))
        if cand.exists():
            return cand, mix_metrics
    fallback = pipeline_dir / "08_mixed_master.wav"
    if not fallback.exists():
        raise FileNotFoundError(f"混音母带不存在: {fallback}")
    return fallback, {}


def _manifest_lookups(manifest: Dict[str, Any]) -> Tuple[Dict[str, List[Dict[str, int]]], Dict[str, Dict[str, Any]]]:
    faces_by_mp4: Dict[str, List[Dict[str, int]]] = {}
    eye_by_mp4: Dict[str, Dict[str, Any]] = {}
    for item in (manifest.get("items") or []):
        mp = str(item.get("normalized_mp4") or "")
        if not mp:
            continue
        norm_faces = parse_manifest_faces(item)
        for key in {mp, str(Path(mp).resolve())}:
            faces_by_mp4[key] = norm_faces
            if item.get("eye_anchor"):
                eye_by_mp4[key] = item["eye_anchor"]
    return faces_by_mp4, eye_by_mp4


def _compute_base_cache_key(
    edl: Dict[str, Any],
    color_plan: Dict[str, Any],
    target_frames: int,
    preview: bool,
    source_hashes: Dict[str, str],
    eye_by_mp4: Dict[str, Any],
) -> str:
    payload = {
        "version": 2,
        "edl": edl,
        "color_plan": color_plan,
        "sources": source_hashes,
        "eyes": eye_by_mp4,
        "target_frames": target_frames,
        "preview": preview,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _build_ffmpeg_pip_vf(pip_layout: Optional[Dict[str, Any]], tw: int = CANVAS_WIDTH, th: int = CANVAS_HEIGHT) -> Optional[str]:
    """生成 30fps 单源动态画中画 FFmpeg 滤镜链（双源场景由 build_graded_segment_cmd 升级为双输入 filter_complex）。"""
    if not isinstance(pip_layout, dict) or tw != CANVAS_WIDTH or th != CANVAS_HEIGHT:
        return None
    mode = str(pip_layout.get("mode") or "")
    bd_hex = str(pip_layout.get("border_hex") or "#FFF589")
    if not bd_hex.startswith("#") or len(bd_hex) not in (7, 9):
        bd_hex = "#FFF589"
    bd_hex = bd_hex[:7]

    if mode == "smooth_orbit_pip":
        corner = str(pip_layout.get("corner") or "tr").lower()
        r_pip = int(pip_layout.get("radius_px") or 146)
        diam = r_pip * 2
        cx_p = (CANVAS_WIDTH - 200) if corner != "tl" else 200
        cy_p = int(pip_layout.get("center_y") or 360)
        ox, oy = cx_p - r_pip, cy_p - r_pip
        return (
            f"split=2[pip_bg][pip_av];"
            f"[pip_av]crop=min(iw\\,ih):min(iw\\,ih):(iw-min(iw\\,ih))/2:(ih-min(iw\\,ih))*0.28,"
            f"scale={diam}:{diam},pad={diam + 8}:{diam + 8}:4:4:color={bd_hex}[pip_circ];"
            f"[pip_bg][pip_circ]overlay=x={ox}:y={oy}:shortest=1"
        )

    if mode == "blur_bg_center_card_pip":
        return (
            f"split=2[pip_bg][pip_fg];"
            f"[pip_bg]boxblur=16:2,eq=brightness=-0.10[pip_bg_b];"
            f"[pip_fg]scale=764:802,pad=772:810:4:4:color={bd_hex}[pip_fg_p];"
            f"[pip_bg_b][pip_fg_p]overlay=x=154:y=386"
        )
    if mode == "black_polaroid_frame_pip":
        return (
            f"split=2[pip_bg][pip_fg];"
            f"[pip_bg]drawbox=x=0:y=0:w=iw:h=ih:color=#141720:t=fill[pip_bg_b];"
            f"[pip_fg]scale=924:1128,pad=932:1136:4:4:color={bd_hex}[pip_fg_p];"
            f"[pip_bg_b][pip_fg_p]overlay=x=74:y=352"
        )
    if mode == "dark_doc_circle_avatar_pip":
        av_x = int((pip_layout.get("avatar_circle_bbox") or {}).get("x", 112))
        return (
            f"split=3[pip_bg][pip_ev][pip_av];"
            f"[pip_bg]boxblur=18:2,eq=brightness=-0.20[pip_bg_b];"
            f"[pip_ev]crop=iw:ih*0.46:0:ih*0.18,scale=924:392,pad=932:400:4:4:color={bd_hex}[pip_ev_p];"
            f"[pip_av]crop=iw*0.62:iw*0.62:iw*0.19:ih*0.16,scale=328:328,pad=336:336:4:4:color={bd_hex}[pip_av_p];"
            f"[pip_bg_b][pip_ev_p]overlay=x=74:y=344[pip_m1];"
            f"[pip_m1][pip_av_p]overlay=x={av_x}:y=804"
        )
    if mode == "linear_split_feather_pip":
        return (
            f"split=2[pip_bg][pip_fg];"
            f"[pip_fg]crop=iw*0.86:ih*0.32:iw*0.07:ih*0.20,scale=804:256,pad=812:264:4:4:color={bd_hex}[pip_fg_p];"
            f"[pip_bg][pip_fg_p]overlay=x=134:y=346"
        )
    if mode in ("corner_circle_evidence_pip", "white_outline_cutout_pip", "dual_rect_grid_pip"):
        pad_c = "#FFFFFF" if mode == "white_outline_cutout_pip" else bd_hex
        pad_w = 8 if mode == "white_outline_cutout_pip" else 4
        in_w = 296 - pad_w * 2
        in_h = 340 - pad_w * 2
        return (
            f"split=2[pip_bg][pip_fg];"
            f"[pip_fg]crop=iw*0.64:ih*0.44:iw*0.18:ih*0.20,scale={in_w}:{in_h},pad=296:340:{pad_w}:{pad_w}:color={pad_c}[pip_fg_p];"
            f"[pip_bg][pip_fg_p]overlay=x=692:y=356"
        )
    return None


def _build_dual_pip_cmd(
    ffmpeg_bin: str,
    media_path: str,
    src_in: float,
    src_avail: float,
    base_vf_chain: str,
    pip_layout: Dict[str, Any],
    sec_media: str,
    sec_in: float,
    clip_dur: float,
    clip_frames: int,
    fps: int,
    out_mp4: Path,
) -> Optional[List[str]]:
    """真双源画中画（主镜头 + 独立副镜头）高速合成器：使用预烘焙圆形 Alpha 蒙版与平滑入场缩放，彻底消灭自己叠自己与慢速 geq。"""
    mode = str(pip_layout.get("mode") or "")
    bd_hex = str(pip_layout.get("border_hex") or "#FFF589")
    if not bd_hex.startswith("#") or len(bd_hex) not in (7, 9):
        bd_hex = "#FFF589"
    bd_hex = bd_hex[:7]
    tail_str = ",".join(BT709_VF_SUFFIX)
    sec_trim = f"fps=fps={fps},trim=duration={clip_dur:.4f},setpts=PTS-STARTPTS"

    if mode == "smooth_orbit_pip":
        corner = str(pip_layout.get("corner") or "tr").lower()
        r_pip = int(pip_layout.get("radius_px") or 146)
        diam = r_pip * 2
        cx_p = (CANVAS_WIDTH - 200) if corner != "tl" else 200
        cy_p = int(pip_layout.get("center_y") or 360)
        ox, oy = cx_p - r_pip, cy_p - r_pip
        mask_p = _ensure_circle_mask_png(out_mp4.parent, r_pip)
        ring_p = _ensure_circle_ring_png(out_mp4.parent, r_pip, bd_hex)
        # 前 0.32s 从画面中心顺滑滑向安全角，末尾 0.28s 顺滑回中（纯表达式零重算开销）
        cx0, cy0 = (CANVAS_WIDTH - diam) // 2, (CANVAS_HEIGHT - diam) // 2
        t_out = max(0.45, clip_dur - 0.30)
        x_expr = f"if(lt(t,0.32),{cx0}+({ox}-{cx0})*sin(t/0.32*PI/2),if(gt(t,{t_out:.3f}),{ox}+({cx0}-{ox})*sin(min(1,(t-{t_out:.3f})/0.30)*PI/2),{ox}))"
        y_expr = f"if(lt(t,0.32),{cy0}+({oy}-{cy0})*sin(t/0.32*PI/2),if(gt(t,{t_out:.3f}),{oy}+({cy0}-{oy})*sin(min(1,(t-{t_out:.3f})/0.30)*PI/2),{oy}))"
        fc = (
            f"[0:v]{base_vf_chain}[p_main];"
            f"[1:v]{sec_trim},crop=min(iw\\,ih):min(iw\\,ih):(iw-min(iw\\,ih))/2:(ih-min(iw\\,ih))*0.24,"
            f"scale={diam}:{diam},format=rgba[p_av_raw];"
            f"[2:v]format=gray[p_mask];"
            f"[p_av_raw][p_mask]alphamerge[p_av_circ];"
            f"[p_main][p_av_circ]overlay=x='{x_expr}':y='{y_expr}':shortest=1[p_m1];"
            f"[p_m1][3:v]overlay=x='({x_expr})-14':y='({y_expr})-14':shortest=1,{tail_str}[vout]"
        )
        return [
            ffmpeg_bin, "-y",
            "-ss", f"{src_in:.4f}", "-t", f"{src_avail + 0.1:.4f}", "-i", media_path,
            "-ss", f"{sec_in:.4f}", "-t", f"{clip_dur + 0.2:.4f}", "-i", sec_media,
            "-loop", "1", "-framerate", str(fps), "-i", str(mask_p),
            "-loop", "1", "-framerate", str(fps), "-i", str(ring_p),
            "-an", "-filter_complex", fc, "-map", "[vout]",
            "-frames:v", str(clip_frames), "-c:v", "libx264", "-preset", "medium", "-crf", "15",
            "-pix_fmt", "yuv420p", *BT709_FFMPEG_ARGS, str(out_mp4),
        ]

    if mode == "dark_doc_circle_avatar_pip":
        av_x = int((pip_layout.get("avatar_circle_bbox") or {}).get("x", 112))
        mask_p = _ensure_circle_mask_png(out_mp4.parent, 168)
        fc = (
            f"[0:v]{base_vf_chain},split=2[p_bg_src][p_av_src];"
            f"[p_bg_src]boxblur=18:2,eq=brightness=-0.20[p_bg];"
            f"[1:v]{sec_trim},scale=924:392:force_original_aspect_ratio=increase,crop=924:392,"
            f"pad=932:400:4:4:color={bd_hex}[p_ev];"
            f"[p_av_src]crop=min(iw\\,ih):min(iw\\,ih):(iw-min(iw\\,ih))/2:(ih-min(iw\\,ih))*0.22,"
            f"scale=336:336,format=rgba[p_av_raw];"
            f"[2:v]format=gray[p_mask];"
            f"[p_av_raw][p_mask]alphamerge[p_av];"
            f"[p_bg][p_ev]overlay=x=74:y=344:shortest=1[p_m1];"
            f"[p_m1][p_av]overlay=x={av_x}:y=804:shortest=1,{tail_str}[vout]"
        )
        return [
            ffmpeg_bin, "-y",
            "-ss", f"{src_in:.4f}", "-t", f"{src_avail + 0.1:.4f}", "-i", media_path,
            "-ss", f"{sec_in:.4f}", "-t", f"{clip_dur + 0.2:.4f}", "-i", sec_media,
            "-loop", "1", "-framerate", str(fps), "-i", str(mask_p),
            "-an", "-filter_complex", fc, "-map", "[vout]",
            "-frames:v", str(clip_frames), "-c:v", "libx264", "-preset", "medium", "-crf", "15",
            "-pix_fmt", "yuv420p", *BT709_FFMPEG_ARGS, str(out_mp4),
        ]

    if mode in ("corner_circle_evidence_pip", "white_outline_cutout_pip", "dual_rect_grid_pip", "linear_split_feather_pip"):
        if mode == "linear_split_feather_pip":
            box_w, box_h, px, py, pad_w, pad_c = 812, 264, 134, 346, 4, bd_hex
        else:
            pad_c = "#FFFFFF" if mode == "white_outline_cutout_pip" else bd_hex
            pad_w = 8 if mode == "white_outline_cutout_pip" else 4
            box_w, box_h, px, py = 296, 340, 692, 356
        in_w, in_h = box_w - pad_w * 2, box_h - pad_w * 2
        fc = (
            f"[0:v]{base_vf_chain}[p_main];"
            f"[1:v]{sec_trim},scale={in_w}:{in_h}:force_original_aspect_ratio=increase,crop={in_w}:{in_h},"
            f"pad={box_w}:{box_h}:{pad_w}:{pad_w}:color={pad_c}[p_sub];"
            f"[p_main][p_sub]overlay=x={px}:y={py}:shortest=1,{tail_str}[vout]"
        )
        return [
            ffmpeg_bin, "-y",
            "-ss", f"{src_in:.4f}", "-t", f"{src_avail + 0.1:.4f}", "-i", media_path,
            "-ss", f"{sec_in:.4f}", "-t", f"{clip_dur + 0.2:.4f}", "-i", sec_media,
            "-an", "-filter_complex", fc, "-map", "[vout]",
            "-frames:v", str(clip_frames), "-c:v", "libx264", "-preset", "medium", "-crf", "15",
            "-pix_fmt", "yuv420p", *BT709_FFMPEG_ARGS, str(out_mp4),
        ]
    return None


def build_graded_segment_cmd(
    ffmpeg_bin: str,
    clip: Dict[str, Any],
    color_vf: Optional[str],
    eye_by_mp4: Dict[str, Dict[str, Any]],
    out_mp4: Path,
    fps: int,
    tw: int = CANVAS_WIDTH,
    th: int = CANVAS_HEIGHT,
    preview: bool = False,
    geom_cache: Optional[Dict[str, Tuple[int, int]]] = None,
) -> List[str]:
    """全仓唯一权威的单分镜裁切 + 锁眼 Ken Burns + 调色 + BT.709 命令构造器（供 render_mp4 / export_jianying / export_hyperframes 共享，消灭 80 行双写）。"""
    media_path = str(clip.get("media_path") or "")
    src_in = max(0.0, float(clip.get("source_in_sec", 0.0)))
    if clip.get("timeline_out_frame") is not None and clip.get("timeline_in_frame") is not None:
        clip_frames = max(1, int(clip["timeline_out_frame"]) - int(clip["timeline_in_frame"]))
    else:
        clip_frames = max(1, sec_to_frames(float(clip.get("duration_sec", 1.0)), fps))
    clip_dur = frames_to_sec(clip_frames, fps)
    src_out = float(clip.get("source_out_sec", src_in + clip_dur))
    src_avail = max(0.1, src_out - src_in)

    if geom_cache is not None and media_path in geom_cache:
        sw, sh = geom_cache[media_path]
    else:
        probe = ffprobe_media(Path(media_path))
        v_s = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), {})
        g = parse_video_stream_geometry(v_s)
        sw, sh = g["display_width"], g["display_height"]
        if geom_cache is not None:
            geom_cache[media_path] = (sw, sh)

    eye = clip.get("eye_anchor") or eye_by_mp4.get(media_path) or eye_by_mp4.get(str(Path(media_path).resolve())) or {}
    fx_raw = float(eye.get("cx", eye.get("eye_cx", 0.50)))
    fy_raw = float(eye.get("cy", eye.get("eye_cy", 0.36)))
    base_tx = compute_crop_transform(sw, sh, tw, th, 0.5, 0.5)
    cx_frac = compute_centered_crop_frac(fx_raw, base_tx["scaled_w"], tw, target_norm_pos=0.5)
    cy_frac = compute_centered_crop_frac(fy_raw, base_tx["scaled_h"], th, target_norm_pos=0.38)
    tx = compute_crop_transform(sw, sh, tw, th, cx_frac, cy_frac)
    fx, fy = fx_raw, fy_raw

    trim_dur = min(src_avail, clip_dur) if src_avail >= clip_dur - 0.01 else src_avail
    vf_parts: List[str] = [f"fps=fps={fps}", f"trim=duration={trim_dur:.4f},setpts=PTS-STARTPTS"]

    vf_extra = str(clip.get("vf_extra") or "").strip()
    kb = clip.get("ken_burns")
    has_kb = isinstance(kb, dict) and ("zoom_start" in kb or "zoom_end" in kb)
    if has_kb and not preview and not vf_extra:
        z0 = max(1.0, float(kb.get("zoom_start", 1.0)))
        z1 = max(1.0, float(kb.get("zoom_end", 1.06)))
        pan_x = float(kb.get("pan_x", 0.0))
        pan_y = float(kb.get("pan_y", 0.0))
        if abs(z1 - z0) > 1e-4 or abs(pan_x) > 1e-4 or abs(pan_y) > 1e-4:
            prog = f"min(t/{clip_dur:.4f},1)"
            z_expr = f"({z0:.4f}+({z1 - z0:.4f})*{prog})"
            vf_parts.append(
                f"scale=w='trunc({tx['scaled_w']}*{z_expr}/2)*2':h='trunc({tx['scaled_h']}*{z_expr}/2)*2':eval=frame:flags=bicubic"
            )
            focal_px_x = float(tx["crop_x"]) + fx * tw
            focal_px_y = float(tx["crop_y"]) + fy * th
            x_off = f"{z_expr}*{focal_px_x:.2f}-{fx * tw:.2f}+({pan_x:.4f}*iw*{prog})"
            y_off = f"{z_expr}*{focal_px_y:.2f}-{fy * th:.2f}+({pan_y:.4f}*ih*{prog})"
            vf_parts.append(f"crop={tw}:{th}:x='max(0,min(iw-{tw},{x_off}))':y='max(0,min(ih-{th},{y_off}))'")
        elif sw != tw or sh != th:
            vf_parts.append(f"scale={tx['scaled_w']}:{tx['scaled_h']}:flags=bicubic")
            vf_parts.append(f"crop={tw}:{th}:{tx['crop_x']}:{tx['crop_y']}")
    else:
        if sw != tw or sh != th:
            vf_parts.append(f"scale={tx['scaled_w']}:{tx['scaled_h']}:flags=bicubic")
            vf_parts.append(f"crop={tw}:{th}:{tx['crop_x']}:{tx['crop_y']}")
        if vf_extra and not preview:
            vf_parts.append(vf_extra)

    if color_vf and not preview:
        vf_parts.append(color_vf)
    if src_avail < clip_dur - 0.01:
        pad_sec = (clip_dur - src_avail) + 0.3
        vf_parts.append(f"tpad=stop_mode=clone:stop_duration={pad_sec:.4f}")

    pip_cfg = clip.get("pip_layout") if (not preview and tw == CANVAS_WIDTH and th == CANVAS_HEIGHT) else None
    if isinstance(pip_cfg, dict):
        sec_media = str(pip_cfg.get("secondary_media_path") or "")
        sec_in = max(0.0, float(pip_cfg.get("secondary_in_sec", 0.0)))
        if sec_media and Path(sec_media).is_file() and str(Path(sec_media).resolve()) != str(Path(media_path).resolve()):
            dual_cmd = _build_dual_pip_cmd(
                ffmpeg_bin=ffmpeg_bin,
                media_path=media_path,
                src_in=src_in,
                src_avail=src_avail,
                base_vf_chain=",".join(vf_parts),
                pip_layout=pip_cfg,
                sec_media=sec_media,
                sec_in=sec_in,
                clip_dur=clip_dur,
                clip_frames=clip_frames,
                fps=fps,
                out_mp4=out_mp4,
            )
            if dual_cmd:
                return dual_cmd
        pip_vf = _build_ffmpeg_pip_vf(pip_cfg, tw=tw, th=th)
        if pip_vf:
            vf_parts.append(pip_vf)

    if preview:
        vf_parts.extend(["setsar=1", "format=yuv420p"])
    else:
        vf_parts.extend(BT709_VF_SUFFIX)

    # 正式中间分镜采用 CRF 15 极低损编码，大幅削减三代 H.264 压损
    return [
        ffmpeg_bin, "-y",
        "-ss", f"{src_in:.4f}",
        "-t", f"{src_avail + 0.1:.4f}",
        "-i", media_path,
        "-an",
        "-vf", ",".join(vf_parts),
        "-frames:v", str(clip_frames),
        "-c:v", "libx264",
        "-preset", "ultrafast" if preview else "medium",
        "-crf", "26" if preview else "15",
        "-pix_fmt", "yuv420p",
        *([] if preview else BT709_FFMPEG_ARGS),
        str(out_mp4),
    ]


def build_base_video_track(
    pipeline_dir: Path,
    edl: Dict[str, Any],
    color_plan: Dict[str, Any],
    master_wav: Path,
    manifest: Optional[Dict[str, Any]] = None,
    preview: bool = False,
) -> Path:
    """按 EDL 分镜精确裁切、单次高质量 Ken Burns / 锁眼推拉 + 调色 + 严防尾帧泄漏地拼接底轨。"""
    started = perf_counter()
    ffmpeg_bin = find_bin("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError("未找到 ffmpeg，无法渲染底轨视频。")
    work_dir = pipeline_dir / "_render_final"
    work_dir.mkdir(parents=True, exist_ok=True)
    base_mp4 = work_dir / ("base_preview.mp4" if preview else "base_video.mp4")
    cache_flag = work_dir / ("base_preview.hash" if preview else "base_video.hash")

    fps = int(edl.get("fps") or DEFAULT_FPS)
    master_dur = get_wav_duration_sec(master_wav)
    target_frames = max(1, round(master_dur * fps))
    clips = edl.get("clips") or []
    _, eye_by_mp4 = _manifest_lookups(manifest or {"items": []})
    paths = {str(clip["media_path"]) for clip in clips}
    lut_path = str(color_plan.get("lut_path") or "")
    if not preview and lut_path and Path(lut_path).is_file():
        paths.add(lut_path)
    source_hashes = {path: sha256_file(Path(path)) for path in sorted(paths)}
    cache_key = _compute_base_cache_key(edl, color_plan, target_frames, preview, source_hashes, eye_by_mp4)
    suffix = "p" if preview else "f"
    expected_segments = [work_dir / f"seg_{index:03d}_{suffix}.mp4" for index in range(len(clips))]

    def profile(base_hit: bool, reused: int) -> None:
        write_json(pipeline_dir / "render_profile.json", {
            "preview": preview, "base_cache_hit": base_hit, "segments_reused": reused,
            "segments_rendered": len(clips) - reused, "base_elapsed_sec": round(perf_counter() - started, 4),
        })

    if (base_mp4.is_file() and cache_flag.is_file()
            and cache_flag.read_text(encoding="utf-8").strip() == cache_key
            and all(seg.is_file() for seg in expected_segments)):
        profile(True, len(clips))
        return base_mp4

    tw = 540 if preview else CANVAS_WIDTH
    th = 960 if preview else CANVAS_HEIGHT
    seg_files: List[Path] = []
    geom_cache: Dict[str, Tuple[int, int]] = {}
    reused = 0
    render_jobs: List[Tuple[List[str], Path, Path, Path, str]] = []

    for idx, clip in enumerate(clips):
        seg_out = expected_segments[idx]
        media_path = str(clip.get("media_path") or "")
        if not media_path or not Path(media_path).exists():
            raise FileNotFoundError(f"EDL 镜头素材不存在: {media_path}")
        cf = _build_color_filter_for_clip(clip, color_plan)
        staged_seg = seg_out.with_suffix(".part.mp4")
        cmd = build_graded_segment_cmd(
            ffmpeg_bin, clip, cf, eye_by_mp4, staged_seg, fps,
            tw=tw, th=th, preview=preview, geom_cache=geom_cache,
        )
        sec_p = str((clip.get("pip_layout") or {}).get("secondary_media_path") or "")
        sec_hash = sha256_file(Path(sec_p)) if sec_p and Path(sec_p).is_file() else ""
        seg_key = compute_segment_cache_key({
            "cmd": cmd[:-1],
            "source_hash": source_hashes[media_path],
            "sec_hash": sec_hash,
            "lut_hash": source_hashes.get(lut_path),
            "fps": fps,
            "preview": preview,
        })
        seg_flag = seg_out.with_suffix(".sha256")
        if seg_out.is_file() and seg_flag.is_file() and seg_flag.read_text(encoding="utf-8") == seg_key:
            reused += 1
        else:
            render_jobs.append((cmd, staged_seg, seg_out, seg_flag, seg_key))
        seg_files.append(seg_out)

    if render_jobs:
        def _exec_seg(job: Tuple[List[str], Path, Path, Path, str]) -> None:
            j_cmd, j_staged, j_out, j_flag, j_key = job
            try:
                run_cmd(j_cmd)
                j_staged.replace(j_out)
            finally:
                j_staged.unlink(missing_ok=True)
            j_flag.write_text(j_key, encoding="utf-8")

        if len(render_jobs) == 1:
            _exec_seg(render_jobs[0])
        else:
            with ThreadPoolExecutor(max_workers=min(2, len(render_jobs))) as pool:
                list(pool.map(_exec_seg, render_jobs))

    concat_txt = work_dir / f"concat_{'p' if preview else 'f'}.txt"
    def _ff_concat_line(p: Path) -> str:
        escaped = p.resolve().as_posix().replace("'", r"'\''")
        return f"file '{escaped}'"
    concat_txt.write_text(
        "\n".join(_ff_concat_line(p) for p in seg_files) + "\n",
        encoding="utf-8",
    )
    exact_dur = frames_to_sec(target_frames, fps)
    run_cmd([
        ffmpeg_bin, "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_txt),
        "-c", "copy",
        "-t", f"{exact_dur:.4f}",
        str(base_mp4),
    ])
    cache_flag.write_text(cache_key, encoding="utf-8")
    profile(False, reused)
    return base_mp4


def render_mp4(pipeline_dir: Path, preview: bool = False) -> Path:
    ffmpeg_bin = find_bin("ffmpeg")
    if not ffmpeg_bin:
        raise RuntimeError("未找到 ffmpeg，无法合成成片 MP4。")
    edl = read_json(pipeline_dir / "04_edl.json")
    subs_data = read_json(pipeline_dir / "05_subtitles.json")
    pkg_data = read_json(pipeline_dir / "06_packaging.json")
    color_plan = read_json(pipeline_dir / "07_color_plan.json")
    manifest = read_json(pipeline_dir / "01_manifest.json")

    master_wav, _ = _resolve_master_wav(pipeline_dir)
    base_mp4 = build_base_video_track(pipeline_dir, edl, color_plan, master_wav, manifest=manifest, preview=preview)
    out_mp4 = pipeline_dir / ("output_preview.mp4" if preview else "output_final.mp4")

    work_dir = pipeline_dir / "_render_final"
    work_dir.mkdir(parents=True, exist_ok=True)
    for stale in list(work_dir.glob("pkg_*.png")) + list(work_dir.glob("sub_*.png")):
        stale.unlink(missing_ok=True)

    fps = int(edl.get("fps") or DEFAULT_FPS)
    master_dur = get_wav_duration_sec(master_wav)
    target_frames = max(1, round(master_dur * fps))
    exact_dur = frames_to_sec(target_frames, fps)

    if preview:
        run_cmd([
            ffmpeg_bin, "-y",
            "-i", str(base_mp4),
            "-i", str(master_wav),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "128k",
            "-t", f"{exact_dur:.4f}",
            "-movflags", "+faststart",
            str(out_mp4),
        ])
        return out_mp4

    faces_by_mp4, _ = _manifest_lookups(manifest)

    def _faces_at_time(t: float) -> List[Dict[str, int]]:
        for c in edl.get("clips") or []:
            if float(c.get("timeline_in_sec", 0.0)) <= t < float(c.get("timeline_out_sec", 0.0)):
                mp = str(c.get("media_path") or "")
                return faces_by_mp4.get(mp) or faces_by_mp4.get(str(Path(mp).resolve())) or []
        return []

    templates = load_subtitle_templates()
    tpl_id = subs_data.get("template_id") or "style_01"
    base_tpl = templates.get(tpl_id) or next(iter(templates.values()))
    tpl = {**base_tpl, **subs_data["template_config"]} if isinstance(subs_data.get("template_config"), dict) else dict(base_tpl)
    font_path = subs_data.get("font_path") or find_commercial_font(tpl.get("font_candidates"))
    style_id = pkg_data.get("style_id") or load_style_applied(pipeline_dir) or "style_01"

    overlays: List[Tuple[Path, int, int, float, float, Optional[Tuple[int, int, int, int]], bool]] = []

    for idx, elem in enumerate(pkg_data.get("visual_elements") or []):
        s_t = max(0.0, frames_to_sec(int(elem.get("start_frame", 0)), fps))
        e_t = min(exact_dur, frames_to_sec(int(elem.get("end_frame", 0)), fps))
        if e_t <= s_t:
            continue
        png_path = resolve_packaging_source(
            elem, pipeline_dir, idx,
            style_id=style_id, color_plan=color_plan, font_candidates=tpl.get("font_candidates"),
        )
        with Image.open(png_path) as im:
            pw, ph = im.size
        def_x = max(SAFE_ZONE["x_min"], (CANVAS_WIDTH - pw) // 2)
        def_y = SAFE_ZONE["y_min"] + 40
        px, py = _place_from_final_bbox(elem, pw, ph, SAFE_ZONE, (def_x, def_y), _faces_at_time(s_t))
        blur_rect = (px, py, pw, ph) if elem.get("overlay_mode") == "focus_blur" else None
        fade_in = bool(int(elem.get("start_frame", 0)) > 0)
        overlays.append((png_path, px, py, s_t, e_t, blur_rect, fade_in))

    for idx, sub in enumerate(subs_data.get("entries") or []):
        if sub.get("suppressed"):
            continue
        s_t = max(0.0, float(sub.get("start_sec", 0.0)))
        e_t = min(exact_dur, float(sub.get("end_sec", s_t + 0.5)))
        if e_t <= s_t:
            continue
        sub_png = work_dir / f"sub_{idx:03d}.png"
        sw_px, sh_px = render_subtitle_png(sub, tpl, font_path, sub_png)
        # 同步写入 .key 指纹，供 export_jianying.py 零重复渲染直接命中字幕 PNG 缓存
        sub_cache_key = compute_segment_cache_key({
            "text": sub.get("text"),
            "words": sub.get("words"),
            "tpl": tpl,
            "font_path": font_path,
        })
        (work_dir / f"sub_{idx:03d}.key").write_text(sub_cache_key, encoding="utf-8")
        def_x, def_y = compute_subtitle_place_xy(sw_px, sh_px, tpl)
        px, py = _place_from_final_bbox(sub, sw_px, sh_px, SUBTITLE_SAFE_ZONE, (def_x, def_y), _faces_at_time(s_t))
        if sw_px <= SUBTITLE_SYMMETRIC_MAX_W:
            px = SUBTITLE_CENTER_X - sw_px // 2
        overlays.append((sub_png, px, py, s_t, e_t, None, False))

    if not overlays:
        run_cmd([
            ffmpeg_bin, "-y",
            "-i", str(base_mp4),
            "-i", str(master_wav),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            "-t", f"{exact_dur:.4f}",
            "-movflags", "+faststart",
            str(out_mp4),
        ])
        return out_mp4

    cmd = [ffmpeg_bin, "-y", "-i", str(base_mp4), "-i", str(master_wav)]
    for png_p, _px, _py, s_t, e_t, _blur_rect, fade_in in overlays:
        if fade_in:
            cmd.extend(["-loop", "1", "-framerate", str(fps), "-t", f"{max(0.1, e_t - s_t + 0.05):.4f}", "-i", str(png_p)])
        else:
            cmd.extend(["-i", str(png_p)])

    filter_chains: List[str] = []
    cur_label = "[0:v]"
    step_idx = 0
    for i, (_, px, py, s_t, e_t, blur_rect, fade_in) in enumerate(overlays):
        in_idx = i + 2
        if blur_rect is not None:
            bx, by, bw, bh = blur_rect
            bw = max(40, min(CANVAS_WIDTH, int(bw)))
            bh = max(40, min(CANVAS_HEIGHT, int(bh)))
            bx = max(0, min(CANVAS_WIDTH - bw, int(bx)))
            by = max(0, min(CANVAS_HEIGHT - bh, int(by)))
            blur_rad = max(2, min(10, min(bw, bh) // 4 - 1))
            base_copy = f"[bc_{step_idx}]"
            blur_crop_in = f"[bi_{step_idx}]"
            blur_crop_out = f"[bo_{step_idx}]"
            blur_merged = f"[bm_{step_idx}]"
            filter_chains.append(f"{cur_label}split=2{base_copy}{blur_crop_in}")
            filter_chains.append(f"{blur_crop_in}crop={bw}:{bh}:{bx}:{by},boxblur={blur_rad}:2:enable='between(t,{s_t:.4f},{e_t:.4f})'{blur_crop_out}")
            filter_chains.append(
                f"{base_copy}{blur_crop_out}overlay=x={bx}:y={by}:enable='between(t,{s_t:.4f},{e_t:.4f})'{blur_merged}"
            )
            cur_label = blur_merged

        if fade_in:
            prep_lbl = f"[ovf_{step_idx}]"
            filter_chains.append(
                f"[{in_idx}:v]format=rgba,fade=t=in:st=0:d=0.133:alpha=1,setpts=PTS+{s_t:.4f}/TB{prep_lbl}"
            )
            ov_in = prep_lbl
            eof_mode = "pass"
        else:
            ov_in = f"[{in_idx}:v]"
            eof_mode = "repeat"

        out_label = "[vout]" if i == len(overlays) - 1 else f"[v{i}]"
        filter_chains.append(
            f"{cur_label}{ov_in}overlay=x={px}:y={py}:eof_action={eof_mode}:enable='between(t,{s_t:.4f},{e_t:.4f})'{out_label}"
        )
        cur_label = out_label
        step_idx += 1

    filter_str = ";\n".join(filter_chains)
    filter_script = work_dir / "overlay_filter.txt"
    filter_script.write_text(filter_str, encoding="utf-8")

    if len(filter_str) < 32768:
        fc_args = ["-filter_complex", filter_str]
    else:
        help_txt = run_cmd([ffmpeg_bin, "-hide_banner", "-h", "long"], check=False).stdout or ""
        fc_flag = "-filter_complex_script" if "filter_complex_script" in help_txt else "-/filter_complex"
        fc_args = [fc_flag, str(filter_script)]

    cmd.extend([
        *fc_args,
        "-map", "[vout]",
        "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "medium", "-crf", "17",
        *BT709_FFMPEG_ARGS,
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-t", f"{exact_dur:.4f}",
        "-movflags", "+faststart",
        str(out_mp4),
    ])
    run_cmd(cmd)
    return out_mp4


def main() -> None:
    maybe_reexec_in_venv()
    parser = argparse.ArgumentParser(description="成片渲染器（支持粗剪预览与终稿 BT.709 导出）")
    parser.add_argument("--pipeline-dir", required=True)
    parser.add_argument("--preview", action="store_true", help="输出低清快速粗剪预览 (540x960)")
    args = parser.parse_args()
    out = render_mp4(Path(args.pipeline_dir), preview=args.preview)
    print(f"[render_mp4] 渲染完成: {out}")


if __name__ == "__main__":
    main()

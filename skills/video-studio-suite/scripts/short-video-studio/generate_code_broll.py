#!/usr/bin/env python3
"""
[素材获取：风格谱同步代码叙事补镜引擎]
当实拍镜头不足时，通过 Pillow 矢量绘图 + FFmpeg rawvideo pipe:0 直推流 + 尾帧 bytes 复用，
高速输出 1080x1920 @ 30fps CFR (BT.709/TV) 的风格化叙事视频片段：
- kinetic_text / data_chart / flow_diagram / proportion / day_night / chips / versus
特性：
1. 自动加载风格谱色板与语域保护 (warm_food / craft_paper / dark_tech)。
2. 全部主副标题由 Pillow textbbox 动态缩字与限制宽度，100% 保证不冲出 SAFE_ZONE["x_max"]。
3. data_chart 按输入数值或 unit 字段按实标单位（拒绝把金额硬拼成 %）。
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from common import (
    BT709_FFMPEG_ARGS,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    DEFAULT_FPS,
    SAFE_ZONE,
    SCRIPTS_DIR,
    contrast_ratio,
    detect_browser_renderer,
    find_bin,
    find_commercial_font,
    fit_text_line,
    get_cached_font,
    hex_to_rgba,
    load_style_spectrum_entry,
    maybe_reexec_in_venv,
    write_json,
)


def ease_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0 - t) ** 3


def damped_spring(t: float, t0: float = 0.0, freq: float = 2.2, zeta: float = 0.58) -> float:
    """确定性闭式阻尼弹簧（纯时间函数，zeta<1 时带微过冲后自然收敛到 1.0）。"""
    x = float(t) - float(t0)
    if x <= 0.0:
        return 0.0
    if x > 2.5:
        return 1.0
    w = 2.0 * math.pi * float(freq)
    z = max(0.05, min(0.99, float(zeta)))
    wd = w * math.sqrt(max(1e-6, 1.0 - z * z))
    return 1.0 - math.exp(-z * w * x) * (math.cos(wd * x) + (z * w / wd) * math.sin(wd * x))


def stagger_progress(
    t: float,
    idx: int,
    base_t0: float = 0.12,
    step_sec: float = 0.10,
    freq: float = 2.2,
    zeta: float = 0.58,
) -> float:
    """多元素 2–5 帧交错阻尼弹簧进度。"""
    return damped_spring(t, t0=base_t0 + max(0, idx) * step_sec, freq=freq, zeta=zeta)


def check_chinese_read_hold(title: str, items: List[Dict[str, Any]], duration_sec: float) -> Dict[str, Any]:
    """校验视觉文字停顿时长是否满足中文 chars/4.5 + 1.5s 最低可读底线。"""
    chunks = [str(title or "")]
    for it in items[:4]:
        chunks.append(str(it.get("label") or ""))
    joined = "".join(chunks)
    cjk_n = sum(1 for c in joined if "\u4e00" <= c <= "\u9fff")
    other_n = sum(1 for c in joined if c.isalnum() and not ("\u4e00" <= c <= "\u9fff"))
    est_req = round(max(2.0, min(8.0, (cjk_n / 4.5) + (other_n / 15.0) + 1.2)), 2)
    ok = float(duration_sec) >= min(est_req, max(2.2, est_req * 0.72))
    return {"duration_sec": round(float(duration_sec), 2), "recommended_sec": est_req, "ok": ok}


def extract_clip_sequence(
    video_path: Path,
    out_dir: Path,
    start_sec: float = 0.0,
    duration_sec: float = 3.0,
    fps: int = DEFAULT_FPS,
    width: int = 720,
    height: int = 1280,
) -> List[Path]:
    """内嵌视频预抽 JPG 帧序列（禁在 HTML 无头抓帧时直接 seek <video>），确保毫秒精确逐帧绘制。"""
    ffmpeg = find_bin("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("需要 ffmpeg 预抽视频帧序列。")
    src = Path(video_path).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"视频资产不存在: {src}")
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.jpg"):
        old.unlink(missing_ok=True)
    subprocess.run([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{max(0.0, float(start_sec)):.4f}",
        "-t", f"{max(0.1, float(duration_sec)):.4f}",
        "-i", str(src),
        "-vf", f"fps={int(fps)},scale={int(width)}:{int(height)}:flags=lanczos",
        "-q:v", "3",
        str(out_dir / "%04d.jpg"),
    ], check=True)
    return sorted(out_dir.glob("*.jpg"))


def resolve_style_palette(
    style_id: Optional[str],
    track: str = "store",
    register: Optional[str] = None,
) -> Dict[str, Any]:
    """根据视觉语域 (B6) / 风格谱 ID / 轨道返回专属排版色板与字体候选。"""
    if register == "warm_food":
        return {
            "archetype_id": "register_warm_food",
            "bg_hex": "#FAF4E8",
            "card_bg_hex": "#FFFFFF",
            "grid_hex": "#EDE2CE",
            "title_hex": "#2B1E16",
            "sub_hex": "#6B4F3A",
            "accent_hex": "#C2571A",
            "badge_text_hex": "#FFFFFF",
            "border_hex": "#DFCBB2",
            "font_candidates": None,
            "is_light": True,
        }
    if register == "craft_paper":
        return {
            "archetype_id": "register_craft_paper",
            "bg_hex": "#F4EFE6",
            "card_bg_hex": "#FAF7F2",
            "grid_hex": "#E6DEC8",
            "title_hex": "#1C1917",
            "sub_hex": "#57534E",
            "accent_hex": "#B91C1C",
            "badge_text_hex": "#FFFFFF",
            "border_hex": "#D6CFC2",
            "font_candidates": None,
            "is_light": True,
        }
    if register == "dark_tech":
        return {
            "archetype_id": "register_dark_tech",
            "bg_hex": "#0B0F17",
            "card_bg_hex": "#121926",
            "grid_hex": "#1A2333",
            "title_hex": "#F8FAFC",
            "sub_hex": "#94A3B8",
            "accent_hex": "#38BDF8",
            "badge_text_hex": "#0B0F17",
            "border_hex": "#25344D",
            "font_candidates": None,
            "is_light": False,
        }

    default_acc = "#FFD54F" if track == "store" else "#38BDF8"
    base = {
        "archetype_id": "default",
        "bg_hex": "#12151E",
        "card_bg_hex": "#1B2030",
        "grid_hex": "#1F2638",
        "title_hex": "#F8FAFC",
        "sub_hex": "#94A3B8",
        "accent_hex": default_acc,
        "badge_text_hex": "#0F172A",
        "border_hex": "#2D364D",
        "font_candidates": None,
        "is_light": False,
    }
    if not style_id:
        return base

    entry = load_style_spectrum_entry(style_id)
    if not entry:
        return base

    arch = str(entry.get("archetype_id", ""))
    sb = entry.get("subtitle_spec", {}) or {}
    cl = entry.get("color_and_lut", {}) or {}
    top5 = [str(x) for x in (cl.get("top5_palette_hex") or []) if isinstance(x, str) and x.strip()]
    kw_col = str(sb.get("keyword_color") or default_acc)
    f_cands = sb.get("font_candidates")

    def _luma_255(hex_c: str) -> float:
        r, g, b, _ = hex_to_rgba(hex_c, (24, 24, 28, 255))
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    def _pick_badge_fg(acc_h: str) -> str:
        rgb = hex_to_rgba(acc_h, (255, 213, 79, 255))[:3]
        return "#FFFFFF" if contrast_ratio((255, 255, 255), rgb) >= contrast_ratio((15, 23, 42), rgb) else "#0F172A"

    # 数据驱动判定亮底/暗底：优先读色板测量均值 y_mean_255 或主背景亮度 (>= 165)，并结合流派兜底
    bg_y_meas = cl.get("bg_y_mean_255")
    if bg_y_meas is not None:
        is_light_style = float(bg_y_meas) >= 165.0
    elif top5:
        is_light_style = _luma_255(top5[0]) >= 165.0
    else:
        is_light_style = (arch == "arch_06_paper_stopmotion") or (style_id in ("style_05", "style_12", "style_18"))

    if arch == "arch_06_paper_stopmotion" or style_id == "style_05":
        acc_h = "#B91C1C" if contrast_ratio((185, 28, 28), (244, 239, 230)) >= 4.5 else "#DC2626"
        return {
            "archetype_id": arch,
            "bg_hex": "#F4EFE6",
            "card_bg_hex": "#FAF7F2",
            "grid_hex": "#E6DEC8",
            "title_hex": "#1C1917",
            "sub_hex": "#57534E",
            "accent_hex": acc_h,
            "badge_text_hex": _pick_badge_fg(acc_h),
            "border_hex": "#D6CFC2",
            "font_candidates": f_cands,
            "is_light": True,
        }
    if is_light_style:
        cand_acc = kw_col if contrast_ratio(hex_to_rgba(kw_col, 255)[:3], (246, 245, 240)) >= 3.2 else "#111827"
        return {
            "archetype_id": arch,
            "bg_hex": "#F6F5F0",
            "card_bg_hex": "#FFFFFF",
            "grid_hex": "#E7E5DF",
            "title_hex": "#111827",
            "sub_hex": "#4B5563",
            "accent_hex": cand_acc,
            "badge_text_hex": _pick_badge_fg(cand_acc),
            "border_hex": "#D1D5DB",
            "font_candidates": f_cands,
            "is_light": True,
        }
    if arch == "arch_05_cinema_slow_space":
        acc_h = kw_col if (kw_col.upper() != "#FFFFFF" and contrast_ratio(hex_to_rgba(kw_col, 255)[:3], (17, 17, 19)) >= 4.5) else "#E6C67A"
        return {
            "archetype_id": arch,
            "bg_hex": "#111113",
            "card_bg_hex": "#19191D",
            "grid_hex": "#222228",
            "title_hex": "#FAF4E4",
            "sub_hex": "#A8A29E",
            "accent_hex": acc_h,
            "badge_text_hex": _pick_badge_fg(acc_h),
            "border_hex": "#343028",
            "font_candidates": f_cands or ["SourceHanSerifCN-Bold.otf"],
            "is_light": False,
        }
    if arch == "arch_01_tech_ui_console":
        acc_h = "#38BDF8" if kw_col.upper() == "#FFFFFF" else kw_col
        if contrast_ratio(hex_to_rgba(acc_h, 255)[:3], (11, 15, 23)) < 4.0:
            acc_h = "#38BDF8"
        return {
            "archetype_id": arch,
            "bg_hex": "#0B0F17",
            "card_bg_hex": "#121926",
            "grid_hex": "#1A2333",
            "title_hex": "#F8FAFC",
            "sub_hex": "#94A3B8",
            "accent_hex": acc_h,
            "badge_text_hex": _pick_badge_fg(acc_h),
            "border_hex": "#25344D",
            "font_candidates": f_cands,
            "is_light": False,
        }
    bg_h = "#141210" if track == "store" else "#12151E"
    acc_h = kw_col if kw_col.upper() != "#FFFFFF" else default_acc
    if contrast_ratio(hex_to_rgba(acc_h, 255)[:3], hex_to_rgba(bg_h, 255)[:3]) < 4.0:
        acc_h = default_acc
    return {
        "archetype_id": arch,
        "bg_hex": bg_h,
        "card_bg_hex": "#1E1B18" if track == "store" else "#1B2030",
        "grid_hex": "#28231E" if track == "store" else "#1F2638",
        "title_hex": "#FAF8F5",
        "sub_hex": "#A8A29E",
        "accent_hex": acc_h,
        "badge_text_hex": _pick_badge_fg(acc_h),
        "border_hex": "#3A332C",
        "font_candidates": f_cands,
        "is_light": False,
    }


def _fit_single_line(draw: Any, text: str, font_path: Optional[str], start_size: int, max_width: int, min_size: int = 22) -> Tuple[Any, str]:
    """委托给 common.fit_text_line 与缓存字体加载，防止文本溢出 SAFE_ZONE 与每帧重复读字体。"""
    return fit_text_line(draw, str(text or ""), font_path, max_width=max_width, max_size=start_size, min_size=min_size)


def _format_chart_value(val: float, ratio_p: float, unit: str) -> str:
    cur = val * ratio_p
    if abs(val - round(val)) < 1e-4:
        num_str = str(int(round(cur)))
    else:
        num_str = f"{cur:.1f}"
    return f"{num_str}{unit}"


def render_broll_clip_pillow(
    output_mp4: Path,
    mode: str,
    title: str,
    items: List[Dict[str, Any]],
    duration_sec: float = 3.0,
    fps: int = DEFAULT_FPS,
    accent_hex: Optional[str] = None,
    bg_hex: Optional[str] = None,
    style_id: Optional[str] = None,
    track: str = "store",
    register: Optional[str] = None,
    anchor_delay_sec: float = 0.15,
) -> Path:
    """用 Pillow 绘制矢量缓动卡片，通过 rawvideo pipe:0 直推 FFmpeg 并复用背景图与尾帧 bytes，提速 10×。"""
    from PIL import Image, ImageDraw, ImageFont

    ffmpeg = find_bin("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("需要 ffmpeg 编码补镜视频。")

    duration_sec = max(2.6, float(duration_sec))
    pal = resolve_style_palette(style_id, track=track, register=register)
    use_bg = bg_hex or pal["bg_hex"]
    use_accent = accent_hex or pal["accent_hex"]
    card_bg = pal["card_bg_hex"]
    grid_col = pal["grid_hex"]
    title_col = pal["title_hex"]
    sub_col = pal["sub_hex"]
    border_col = pal["border_hex"]
    badge_txt_col = pal["badge_text_hex"]

    font_path = find_commercial_font(pal.get("font_candidates"))
    f_badge = get_cached_font(font_path, 26) or ImageFont.load_default()
    f_num_big = get_cached_font(font_path, 52) or ImageFont.load_default()

    total_frames = max(int(round(2.6 * fps)), int(round(duration_sec * fps)))
    anchor_frames = max(4, int(round(anchor_delay_sec * fps)))
    max_anim_end_frame = min(total_frames - 1, anchor_frames + int(round(1.6 * fps)))
    hold_check = check_chinese_read_hold(title, items, duration_sec)
    if not hold_check["ok"]:
        print(f"[code_broll] [WARN] 图卡 '{title[:10]}' 停留 {hold_check['duration_sec']}s 略短（建议 ≥{hold_check['recommended_sec']}s）")
    output_mp4.parent.mkdir(parents=True, exist_ok=True)

    mode_tags = {
        "kinetic_text": "核心观点",
        "data_chart": "数据拆解",
        "flow_diagram": "标准流程",
        "proportion": "比例拆解",
        "day_night": "全天接力",
        "chips": "招牌清单",
        "versus": "真假对照",
    }

    safe_right = SAFE_ZONE["x_max"] - 24  # 856px 严格留边
    max_title_w = safe_right - 88         # 768px

    # 预渲染静态背景+网格图层，避免每帧重绘
    base_bg = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), use_bg)
    bg_draw = ImageDraw.Draw(base_bg)
    for gx in range(88, 860, 130):
        bg_draw.line([(gx, 190), (gx, 1440)], fill=grid_col, width=1)
    for gy in range(210, 1440, 130):
        bg_draw.line([(72, gy), (safe_right, gy)], fill=grid_col, width=1)
    mode_tag = mode_tags.get(mode, "重点提示")
    bg_draw.rounded_rectangle([88, 224, 290, 276], radius=12, fill=use_accent)
    bg_draw.text((189, 250), mode_tag, fill=badge_txt_col, font=f_badge, anchor="mm")

    f_title, fit_title = _fit_single_line(bg_draw, title, font_path, 60, max_title_w, min_size=34)

    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{CANVAS_WIDTH}x{CANVAS_HEIGHT}",
        "-r", str(fps),
        "-i", "pipe:0",
        "-c:v", "libx264", *BT709_FFMPEG_ARGS, "-preset", "fast", "-crf", "17",
        "-r", str(fps), "-fps_mode", "cfr",
        str(output_mp4),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None

    cached_tail_bytes: Optional[bytes] = None
    try:
        for fi in range(total_frames):
            if cached_tail_bytes is not None:
                proc.stdin.write(cached_tail_bytes)
                continue

            img = base_bg.copy()
            draw = ImageDraw.Draw(img)

            t_sec = fi / float(fps)
            tp = 0.35 + 0.65 * damped_spring(t_sec, t0=0.0, freq=2.4, zeta=0.62)
            tp_clamped = max(0.0, min(1.0, tp))
            ty = int(340 + (1.0 - tp) * 26)
            draw.text((88, ty), fit_title, fill=title_col, font=f_title)
            draw.rectangle([88, ty + 84, 88 + int(min(max_title_w, 620) * tp_clamped), ty + 90], fill=use_accent)

            if mode == "proportion":
                raw_vals = [max(1.0, float(it.get("value") or 1.0)) for it in items[:4]]
                tot_v = max(1e-5, sum(raw_vals))
                pcts = [v * 100.0 / tot_v for v in raw_vals]
                p_bar = max(0.0, min(1.0, damped_spring(t_sec, t0=anchor_delay_sec, freq=2.0, zeta=0.65)))
                bar_x0, bar_x1, bar_y0, bar_y1 = 88, safe_right, 480, 566
                draw.rounded_rectangle([bar_x0, bar_y0, bar_x1, bar_y1], radius=18, fill=card_bg, outline=border_col, width=2)
                seg_colors = ["#B45309", "#1D4ED8", "#047857", "#6D28D9"] if pal.get("is_light") else [use_accent, "#38BDF8", "#34D399", "#E879F9"]
                cur_x = bar_x0 + 8
                avail_w = max(24, int((bar_x1 - bar_x0 - 16) * max(0.08, p_bar)))
                n_seg = len(pcts)
                gap_w = 4
                usable_w = max(16, avail_w - gap_w * max(0, n_seg - 1))
                seg_ws = [max(12, int(usable_w * pct / 100.0)) for pct in pcts]
                overflow = sum(seg_ws) - usable_w
                if overflow > 0 and n_seg > 0:
                    total_sw = max(1, sum(seg_ws))
                    seg_ws = [max(8, int(sw - overflow * (sw / total_sw))) for sw in seg_ws]
                for si, seg_w in enumerate(seg_ws):
                    ex = min(bar_x1 - 8, cur_x + seg_w)
                    if ex > cur_x + 2:
                        draw.rounded_rectangle([cur_x, bar_y0 + 10, ex, bar_y1 - 10], radius=12, fill=seg_colors[si % len(seg_colors)])
                    cur_x = ex + gap_w

                for idx, (it, pct) in enumerate(zip(items[:3], pcts[:3])):
                    p_c = max(0.0, min(1.0, stagger_progress(t_sec, idx, base_t0=anchor_delay_sec, step_sec=0.12)))
                    if p_c <= 0.02:
                        continue
                    cy = 600 + idx * 172
                    draw.rounded_rectangle([88, cy, safe_right, cy + 148], radius=16, fill=card_bg, outline=border_col, width=2)
                    draw.rounded_rectangle([104, cy + 28, 120, cy + 120], radius=6, fill=seg_colors[idx % len(seg_colors)])
                    fl, tl = _fit_single_line(draw, str(it.get("label", "")), font_path, 38, safe_right - 300)
                    draw.text((142, cy + 36), tl, fill=title_col, font=fl)
                    if it.get("subtitle"):
                        fs, ts_txt = _fit_single_line(draw, str(it["subtitle"]), font_path, 28, safe_right - 300)
                        draw.text((142, cy + 92), ts_txt, fill=sub_col, font=fs)
                    draw.text((safe_right - 32, cy + 74), f"{int(round(pct * p_c))}%", fill=seg_colors[idx % len(seg_colors)], font=f_num_big, anchor="rm")

            elif mode == "day_night":
                for idx, it in enumerate(items[:2]):
                    delay = anchor_frames + idx * 10
                    p_c = ease_out_cubic((fi - delay) / 10.0)
                    if p_c <= 0.02:
                        continue
                    cy = 490 + idx * 340
                    tag_bg = "#D97706" if idx == 0 else "#1E3A8A"
                    tag_lbl = str(it.get("tag") or ("昼 · 日间档" if idx == 0 else "夜 · 晚市档"))[:10]
                    draw.rounded_rectangle([88, cy, safe_right, cy + 240], radius=22, fill=card_bg, outline=border_col, width=2)
                    draw.rounded_rectangle([116, cy + 26, 310, cy + 74], radius=12, fill=tag_bg)
                    draw.text((213, cy + 50), tag_lbl, fill="#FFFFFF", font=f_badge, anchor="mm")
                    fl, tl = _fit_single_line(draw, str(it.get("label", "")), font_path, 38, safe_right - 148)
                    draw.text((116, cy + 104), tl, fill=title_col, font=fl)
                    if it.get("subtitle"):
                        fs, ts_txt = _fit_single_line(draw, str(it["subtitle"]), font_path, 28, safe_right - 148)
                        draw.text((116, cy + 166), ts_txt, fill=sub_col, font=fs)
                    if idx == 0 and len(items) >= 2:
                        draw.line([(472, cy + 248), (472, cy + 324)], fill=use_accent, width=6)
                        draw.polygon([(454, cy + 308), (490, cy + 308), (472, cy + 332)], fill=use_accent)

            elif mode == "chips":
                static_chip_text_w = safe_right - 236
                for idx, it in enumerate(items[:4]):
                    delay = anchor_frames + idx * 6
                    p_c = ease_out_cubic((fi - delay) / 8.0)
                    if p_c <= 0.02:
                        continue
                    cy = 500 + idx * 175
                    ox = int((1.0 - p_c) * 48)
                    draw.rounded_rectangle([88 + ox, cy, safe_right, cy + 136], radius=68, fill=card_bg, outline=use_accent, width=3)
                    draw.ellipse([120 + ox, cy + 38, 180 + ox, cy + 98], fill=use_accent)
                    f_chk, _ = _fit_single_line(draw, "✓", font_path, 38, 60)
                    draw.text((150 + ox, cy + 68), "✓", fill=badge_txt_col, font=f_chk, anchor="mm")
                    fl, tl = _fit_single_line(draw, str(it.get("label", "")), font_path, 38, static_chip_text_w)
                    draw.text((208 + ox, cy + 68), tl, fill=title_col, font=fl, anchor="lm")

            elif mode == "versus":
                for idx, it in enumerate(items[:3]):
                    delay = anchor_frames + idx * 6
                    p_c = ease_out_cubic((fi - delay) / 9.0)
                    if p_c <= 0.02:
                        continue
                    cy = 480 + idx * 210
                    is_good = bool(it.get("positive", idx % 2 == 1))
                    side_col = "#16A34A" if is_good else "#DC2626"
                    mark = "✓" if is_good else "✗"
                    draw.rounded_rectangle([88, cy, safe_right, cy + 172], radius=18, fill=card_bg, outline=side_col, width=3)
                    draw.ellipse([116, cy + 48, 180, cy + 112], fill=side_col)
                    f_mk, _ = _fit_single_line(draw, mark, font_path, 38, 60)
                    draw.text((148, cy + 80), mark, fill="#FFFFFF", font=f_mk, anchor="mm")
                    fl, tl = _fit_single_line(draw, str(it.get("label", "")), font_path, 38, safe_right - 234)
                    draw.text((206, cy + 40), tl, fill=title_col, font=fl)
                    if it.get("subtitle"):
                        fs, ts_txt = _fit_single_line(draw, str(it["subtitle"]), font_path, 28, safe_right - 234)
                        draw.text((206, cy + 104), ts_txt, fill=sub_col, font=fs)

            else:
                base_y = 480
                card_h = 196 if mode != "flow_diagram" else 188
                max_val = max([float(it["value"]) for it in items[:3] if isinstance(it.get("value"), (int, float))] + [100.0])
                static_flow_w = (safe_right - 24) - (88 + 128)
                static_card_w = (safe_right - 28) - (88 + 44)
                static_bar_max = max(120, (safe_right - 88) - 230)
                for idx, item in enumerate(items[:3]):
                    p = stagger_progress(t_sec, idx, base_t0=anchor_delay_sec, step_sec=0.12, freq=2.3, zeta=0.58)
                    if p <= 0.01:
                        continue
                    p_val = max(0.0, min(1.0, p))
                    cy = base_y + idx * (card_h + 24)
                    offset_x = max(-8, int((1.0 - p) * 64))
                    x1, x2 = 88 + offset_x, safe_right
                    draw.rounded_rectangle([x1, cy, x2, cy + card_h], radius=18, fill=card_bg, outline=border_col, width=2)
                    draw.rounded_rectangle([x1 + 14, cy + 28, x1 + 22, cy + card_h - 28], radius=4, fill=use_accent)

                    raw_lbl = str(item.get("label", ""))
                    raw_sub = str(item.get("subtitle", ""))
                    val = item.get("value")

                    if mode == "flow_diagram":
                        draw.ellipse([x1 + 42, cy + 32, x1 + 104, cy + 94], fill=use_accent)
                        f_idx, _ = _fit_single_line(draw, str(idx + 1), font_path, 36, 54)
                        draw.text((x1 + 73, cy + 63), str(idx + 1), fill=badge_txt_col, font=f_idx, anchor="mm")
                        fl, tl = _fit_single_line(draw, raw_lbl, font_path, 36, static_flow_w)
                        draw.text((x1 + 128, cy + 38), tl, fill=title_col, font=fl)
                        if raw_sub:
                            fs, ts_txt = _fit_single_line(draw, raw_sub, font_path, 28, static_flow_w)
                            draw.text((x1 + 128, cy + 104), ts_txt, fill=sub_col, font=fs)
                        if idx < len(items[:3]) - 1:
                            draw.line([(x1 + 73, cy + card_h), (x1 + 73, cy + card_h + 28)], fill=use_accent, width=4)
                    else:
                        fl, tl = _fit_single_line(draw, raw_lbl, font_path, 38, static_card_w)
                        draw.text((x1 + 44, cy + 28), tl, fill=title_col, font=fl)
                        if mode == "data_chart" and isinstance(val, (int, float)):
                            unit = str(item.get("unit") if item.get("unit") is not None else ("%" if "%" in raw_lbl else ""))
                            ratio = max(0.05, min(1.0, float(val) / max(1e-5, max_val))) * p_val
                            draw.rounded_rectangle([x1 + 44, cy + 108, x1 + 44 + static_bar_max, cy + 142], radius=14, fill=grid_col)
                            draw.rounded_rectangle(
                                [x1 + 44, cy + 108, x1 + 44 + max(24, int(static_bar_max * ratio)), cy + 142],
                                radius=14,
                                fill=use_accent,
                            )
                            val_txt = _format_chart_value(float(val), p_val, unit)
                            fv, tv = _fit_single_line(draw, val_txt, font_path, 36, 150)
                            draw.text((x2 - 30, cy + 125), tv, fill=use_accent, font=fv, anchor="rm")
                        elif raw_sub:
                            fs, ts_txt = _fit_single_line(draw, raw_sub, font_path, 28, static_card_w)
                            draw.text((x1 + 44, cy + 108), ts_txt, fill=sub_col, font=fs)

            raw_bytes = img.tobytes()
            proc.stdin.write(raw_bytes)
            if fi >= max_anim_end_frame and tp >= 0.999:
                cached_tail_bytes = raw_bytes

        proc.stdin.close()
        err = (proc.stderr.read() if proc.stderr else b"").decode("utf-8", errors="replace")
        rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"代码补镜视频编码失败 ({rc}): {err[-600:]}")
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        raise
    return output_mp4


def _build_broll_html_page(
    mode: str,
    title: str,
    items: List[Dict[str, Any]],
    duration_sec: float,
    pal: Dict[str, Any],
    font_rel_url: Optional[str],
    anchor_delay_sec: float = 0.15,
    frame_seq_rels: Optional[List[str]] = None,
    fps: int = DEFAULT_FPS,
) -> str:
    mode_tags = {
        "kinetic_text": "核心观点",
        "data_chart": "数据拆解",
        "flow_diagram": "标准流程",
        "proportion": "比例拆解",
        "day_night": "全天接力",
        "chips": "招牌清单",
        "versus": "真假对照",
    }
    mode_tag = mode_tags.get(mode, "重点提示")
    safe_right = SAFE_ZONE["x_max"] - 24
    panel_w = safe_right - 88
    items_json = json.dumps(items[:4], ensure_ascii=False)
    seq_json = json.dumps(list(frame_seq_rels or []), ensure_ascii=False)
    font_face_css = ""
    if font_rel_url:
        fmt = "opentype" if font_rel_url.lower().endswith(".otf") else "truetype"
        font_face_css = (
            "@font-face { font-family: 'SVSCodeFont'; "
            f"src: url('{html.escape(font_rel_url)}') format('{fmt}'); font-display: block; }}"
        )
    ff_name = "'SVSCodeFont', 'PingFang SC', sans-serif" if font_rel_url else "'PingFang SC', sans-serif"
    card_shadow = "0 12px 32px rgba(0,0,0,0.28)" if not pal.get("is_light") else "0 10px 26px rgba(40,30,20,0.08)"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <style>
    {font_face_css}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html, body {{
      width: {CANVAS_WIDTH}px;
      height: {CANVAS_HEIGHT}px;
      overflow: hidden;
      background: {pal['bg_hex']};
      font-family: {ff_name};
      color: {pal['title_hex']};
    }}
    .canvas-stage {{
      position: relative;
      width: {CANVAS_WIDTH}px;
      height: {CANVAS_HEIGHT}px;
      overflow: hidden;
    }}
    .camera-rig {{
      position: absolute;
      inset: 0;
      transform-origin: 490px 660px;
      will-change: transform;
    }}
    .bg-grid {{
      position: absolute;
      inset: 190px {CANVAS_WIDTH - safe_right}px 740px 72px;
      background-image:
        linear-gradient(to right, {pal['grid_hex']} 1px, transparent 1px),
        linear-gradient(to bottom, {pal['grid_hex']} 1px, transparent 1px);
      background-size: 130px 130px;
      opacity: 0.72;
    }}
    .glow-orb {{
      position: absolute;
      width: 520px;
      height: 520px;
      border-radius: 50%;
      background: radial-gradient(circle, {pal['accent_hex']}28 0%, transparent 72%);
      pointer-events: none;
    }}
    .mode-badge {{
      position: absolute;
      left: 88px;
      top: 222px;
      padding: 10px 26px;
      border-radius: 12px;
      background: {pal['accent_hex']};
      color: {pal['badge_text_hex']};
      font-size: 28px;
      font-weight: 800;
      letter-spacing: 0.04em;
    }}
    .title-wrap {{
      position: absolute;
      left: 88px;
      top: 316px;
      width: {panel_w}px;
    }}
    .main-title {{
      font-size: 56px;
      line-height: 1.18;
      font-weight: 800;
      color: {pal['title_hex']};
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    .title-bar {{
      margin-top: 14px;
      height: 6px;
      border-radius: 4px;
      background: {pal['accent_hex']};
      transform-origin: left center;
    }}
    .cards-area {{
      position: absolute;
      left: 88px;
      top: 446px;
      width: {panel_w}px;
      height: 690px;
      overflow: hidden;
    }}
    .pip-frame-box {{
      position: relative;
      width: 100%;
      height: 220px;
      border-radius: 18px;
      border: 2px solid {pal['accent_hex']};
      overflow: hidden;
      margin-bottom: 16px;
      background: #000;
      box-shadow: {card_shadow};
    }}
    .pip-frame-box img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: block;
    }}
    .flow-svg-rail {{
      position: absolute;
      left: 0;
      top: 0;
      width: 44px;
      height: 640px;
      pointer-events: none;
      z-index: 2;
    }}
    .card {{
      position: relative;
      background: {pal['card_bg_hex']};
      border: 2px solid {pal['border_hex']};
      border-radius: 20px;
      padding: 18px 24px 18px 32px;
      margin-bottom: 16px;
      box-shadow: {card_shadow};
      overflow: hidden;
    }}
    .card.flow-mode {{
      margin-left: 48px;
    }}
    .card.day-slot {{
      border-color: #F59E0B;
    }}
    .card.night-slot {{
      border-color: #38BDF8;
    }}
    .card-accent-strip {{
      position: absolute;
      left: 14px;
      top: 22px;
      bottom: 22px;
      width: 8px;
      border-radius: 4px;
      background: {pal['accent_hex']};
    }}
    .card-lbl {{
      font-size: 36px;
      font-weight: 700;
      color: {pal['title_hex']};
      line-height: 1.25;
      padding-right: 120px;
    }}
    .card-sub {{
      margin-top: 10px;
      font-size: 28px;
      color: {pal['sub_hex']};
      line-height: 1.3;
    }}
    .bar-track {{
      margin-top: 16px;
      height: 28px;
      border-radius: 14px;
      background: {pal['grid_hex']};
      overflow: hidden;
      position: relative;
    }}
    .bar-benchmark {{
      position: absolute;
      top: 0;
      bottom: 0;
      left: 50%;
      width: 2px;
      background: {pal['sub_hex']};
      opacity: 0.45;
      z-index: 2;
    }}
    .bar-fill {{
      height: 100%;
      border-radius: 14px;
      background: linear-gradient(90deg, {pal['accent_hex']}, {pal['accent_hex']}CC);
    }}
    .val-readout {{
      position: absolute;
      right: 26px;
      top: 20px;
      font-size: 38px;
      font-weight: 800;
      color: {pal['accent_hex']};
    }}
    .prop-hero-row {{
      display: flex;
      align-items: center;
      gap: 22px;
      margin-bottom: 18px;
      padding: 12px 18px;
      background: {pal['card_bg_hex']};
      border: 2px solid {pal['border_hex']};
      border-radius: 20px;
    }}
    .donut-svg {{
      width: 132px;
      height: 132px;
      flex-shrink: 0;
    }}
    .prop-track {{
      flex: 1;
      display: flex;
      gap: 6px;
      padding: 8px;
      height: 68px;
      background: {pal['bg_hex']};
      border: 2px solid {pal['border_hex']};
      border-radius: 16px;
    }}
    .prop-seg {{
      height: 100%;
      border-radius: 10px;
    }}
    .motion-rail {{
      position: absolute;
      left: 88px;
      top: 1142px;
      width: {panel_w}px;
      height: 6px;
      border-radius: 3px;
      background: {pal['grid_hex']};
      overflow: hidden;
    }}
    .motion-dot {{
      height: 100%;
      border-radius: 3px;
      background: {pal['accent_hex']};
    }}
  </style>
</head>
<body>
  <div class="canvas-stage" id="stage">
    <div class="camera-rig" id="camera-rig">
      <div class="bg-grid" id="bg-grid"></div>
      <div class="glow-orb" id="orb"></div>
      <div class="mode-badge" id="badge">{html.escape(mode_tag)}</div>
      <div class="title-wrap" id="title-wrap">
        <div class="main-title" id="main-title">{html.escape(title)}</div>
        <div class="title-bar" id="title-bar"></div>
      </div>
      <div class="cards-area" id="cards-area"></div>
      <div class="motion-rail"><div class="motion-dot" id="motion-dot"></div></div>
    </div>
  </div>
  <script>
    (function () {{
      var MODE = {json.dumps(mode)};
      var ITEMS = {items_json};
      var FRAME_SEQ = {seq_json};
      var FPS = {int(fps)};
      var DUR = {duration_sec:.4f};
      var ANCHOR_T = {anchor_delay_sec:.4f};
      var ACCENT = {json.dumps(pal['accent_hex'])};
      var IS_LIGHT = {json.dumps(bool(pal.get('is_light')))};
      var SEG_COLORS = IS_LIGHT
        ? ['#B45309', '#1D4ED8', '#047857', '#6D28D9']
        : [ACCENT, '#38BDF8', '#34D399', '#E879F9'];
      var TITLE_COL = {json.dumps(pal['title_hex'])};
      var CARD_BG = {json.dumps(pal['card_bg_hex'])};
      function _hexLum(h) {{
        var m = /^#?([0-9a-f]{{6}})$/i.exec(String(h || '').trim());
        if (!m) return null;
        var n = parseInt(m[1], 16);
        var vals = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map(function (c) {{
          var s = c / 255;
          return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
        }});
        return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2];
      }}
      function _safeFg(fgHex, bgHex) {{
        var l1 = _hexLum(fgHex), l2 = _hexLum(bgHex);
        if (l1 === null || l2 === null) return TITLE_COL;
        var cr = (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
        return cr >= 4.8 ? fgHex : TITLE_COL;
      }}
      window.DUR = DUR;
      window.READY = false;

      function clamp(v, lo, hi) {{ return Math.max(lo, Math.min(hi, v)); }}
      function dampedSpring(t, t0, freq, zeta) {{
        var x = t - t0;
        if (x <= 0) return 0;
        if (x > 2.5) return 1;
        var w = 2 * Math.PI * (freq || 2.2);
        var z = clamp(zeta || 0.58, 0.05, 0.99);
        var wd = w * Math.sqrt(Math.max(1e-6, 1 - z * z));
        return 1 - Math.exp(-z * w * x) * (Math.cos(wd * x) + (z * w / wd) * Math.sin(wd * x));
      }}

      var cardsEl = document.getElementById('cards-area');
      var pipImgEl = null;
      if (FRAME_SEQ && FRAME_SEQ.length > 0) {{
        var pipBox = document.createElement('div');
        pipBox.className = 'pip-frame-box';
        pipImgEl = document.createElement('img');
        pipImgEl.src = FRAME_SEQ[0];
        pipBox.appendChild(pipImgEl);
        cardsEl.appendChild(pipBox);
      }}

      var propSegs = [];
      var donutCircle = null;
      var flowPath = null;
      var flowPathLen = 480;
      var cardNodes = [];
      var vals = ITEMS.map(function (it) {{ return typeof it.value === 'number' ? it.value : 0; }});
      var maxVal = Math.max.apply(null, vals.concat([100]));
      var totalVal = Math.max(1e-5, vals.reduce(function (a, b) {{ return a + Math.max(1, b); }}, 0));

      if (MODE === 'proportion' && ITEMS.length) {{
        var heroRow = document.createElement('div');
        heroRow.className = 'prop-hero-row';
        var svgNS = 'http://www.w3.org/2000/svg';
        var dSvg = document.createElementNS(svgNS, 'svg');
        dSvg.setAttribute('viewBox', '0 0 120 120');
        dSvg.setAttribute('class', 'donut-svg');
        var bgC = document.createElementNS(svgNS, 'circle');
        bgC.setAttribute('cx', '60'); bgC.setAttribute('cy', '60'); bgC.setAttribute('r', '44');
        bgC.setAttribute('fill', 'none'); bgC.setAttribute('stroke', '#334155'); bgC.setAttribute('stroke-width', '14');
        dSvg.appendChild(bgC);
        donutCircle = document.createElementNS(svgNS, 'circle');
        donutCircle.setAttribute('cx', '60'); donutCircle.setAttribute('cy', '60'); donutCircle.setAttribute('r', '44');
        donutCircle.setAttribute('fill', 'none'); donutCircle.setAttribute('stroke', SEG_COLORS[0]);
        donutCircle.setAttribute('stroke-width', '14'); donutCircle.setAttribute('stroke-linecap', 'round');
        donutCircle.setAttribute('transform', 'rotate(-90 60 60)');
        donutCircle.setAttribute('stroke-dasharray', '276.46');
        donutCircle.setAttribute('stroke-dashoffset', '276.46');
        dSvg.appendChild(donutCircle);
        heroRow.appendChild(dSvg);

        var pTrack = document.createElement('div');
        pTrack.className = 'prop-track';
        ITEMS.forEach(function (it, i) {{
          var s = document.createElement('div');
          s.className = 'prop-seg';
          s.style.background = SEG_COLORS[i % SEG_COLORS.length];
          pTrack.appendChild(s);
          propSegs.push({{ el: s, pct: (Math.max(1, it.value || 1) * 100) / totalVal }});
        }});
        heroRow.appendChild(pTrack);
        cardsEl.appendChild(heroRow);
      }}

      if (MODE === 'flow_diagram' && ITEMS.length > 1) {{
        var svgNS2 = 'http://www.w3.org/2000/svg';
        var fSvg = document.createElementNS(svgNS2, 'svg');
        fSvg.setAttribute('viewBox', '0 0 44 640');
        fSvg.setAttribute('class', 'flow-svg-rail');
        flowPath = document.createElementNS(svgNS2, 'path');
        flowPath.setAttribute('d', 'M 22 42 C 36 160, 8 280, 22 440');
        flowPath.setAttribute('fill', 'none');
        flowPath.setAttribute('stroke', ACCENT);
        flowPath.setAttribute('stroke-width', '5');
        flowPath.setAttribute('stroke-linecap', 'round');
        flowPath.setAttribute('stroke-dasharray', String(flowPathLen));
        flowPath.setAttribute('stroke-dashoffset', String(flowPathLen));
        fSvg.appendChild(flowPath);
        cardsEl.appendChild(fSvg);
      }}

      var maxItems = (FRAME_SEQ && FRAME_SEQ.length > 0) ? 2 : 3;
      ITEMS.slice(0, maxItems).forEach(function (it, idx) {{
        var c = document.createElement('div');
        c.className = 'card' + (MODE === 'flow_diagram' ? ' flow-mode' : '');
        var strip = document.createElement('div');
        strip.className = 'card-accent-strip';
        if (MODE === 'proportion') strip.style.background = SEG_COLORS[idx % SEG_COLORS.length];
        if (MODE === 'versus') {{
          var good = (typeof it.positive === 'boolean') ? it.positive : (idx % 2 === 1);
          strip.style.background = good ? '#16A34A' : '#DC2626';
          c.style.borderColor = strip.style.background;
        }}
        if (MODE === 'day_night') {{
          var isDay = (idx % 2 === 0);
          c.className += isDay ? ' day-slot' : ' night-slot';
          strip.style.background = isDay ? '#F59E0B' : '#38BDF8';
        }}
        c.appendChild(strip);

        var lbl = document.createElement('div');
        lbl.className = 'card-lbl';
        var prefix = '';
        if (MODE === 'flow_diagram') prefix = (idx + 1) + '. ';
        else if (MODE === 'chips') prefix = '✓ ';
        else if (MODE === 'day_night') prefix = (idx % 2 === 0) ? '☀ 白昼 · ' : '☾ 夜间 · ';
        lbl.textContent = prefix + String(it.label || '');
        c.appendChild(lbl);

        var readoutEl = null, fillEl = null;
        if (MODE === 'data_chart' && typeof it.value === 'number') {{
          readoutEl = document.createElement('div');
          readoutEl.className = 'val-readout';
          readoutEl.style.color = _safeFg(ACCENT, CARD_BG);
          c.appendChild(readoutEl);
          var bt = document.createElement('div');
          bt.className = 'bar-track';
          var bm = document.createElement('div');
          bm.className = 'bar-benchmark';
          bt.appendChild(bm);
          fillEl = document.createElement('div');
          fillEl.className = 'bar-fill';
          bt.appendChild(fillEl);
          c.appendChild(bt);
        }} else if (MODE === 'proportion') {{
          readoutEl = document.createElement('div');
          readoutEl.className = 'val-readout';
          readoutEl.style.color = _safeFg(SEG_COLORS[idx % SEG_COLORS.length], CARD_BG);
          c.appendChild(readoutEl);
          if (it.subtitle) {{
            var sub1 = document.createElement('div');
            sub1.className = 'card-sub';
            sub1.textContent = String(it.subtitle);
            c.appendChild(sub1);
          }}
        }} else if (it.subtitle) {{
          var sub2 = document.createElement('div');
          sub2.className = 'card-sub';
          sub2.textContent = String(it.subtitle);
          c.appendChild(sub2);
        }}
        cardsEl.appendChild(c);
        cardNodes.push({{ el: c, item: it, readoutEl: readoutEl, fillEl: fillEl }});
      }});

      window.seek = function (t) {{
        var curT = clamp(Number(t) || 0, 0, DUR);
        var camP = dampedSpring(curT, 0.0, 1.9, 0.68);
        var camScale = 1.0 + (1.0 - clamp(camP, 0, 1)) * 0.022 + Math.sin(curT * 0.85) * 0.006;
        var camY = (1.0 - clamp(camP, 0, 1)) * 14.0;
        document.getElementById('camera-rig').style.transform =
          'translateY(' + camY.toFixed(2) + 'px) scale(' + camScale.toFixed(4) + ')';

        if (pipImgEl && FRAME_SEQ.length > 0) {{
          var fIdx = clamp(Math.floor(curT * FPS), 0, FRAME_SEQ.length - 1);
          pipImgEl.src = FRAME_SEQ[fIdx];
        }}

        var orb = document.getElementById('orb');
        orb.style.left = (220 + Math.sin(curT * 1.4) * 160) + 'px';
        orb.style.top = (280 + Math.cos(curT * 1.1) * 110) + 'px';

        var bg = document.getElementById('bg-grid');
        bg.style.transform = 'translateY(' + (Math.sin(curT * 0.9) * 10).toFixed(2) + 'px)';

        var tp = 0.35 + 0.65 * dampedSpring(curT, 0.0, 2.4, 0.62);
        var tw = document.getElementById('title-wrap');
        tw.style.transform = 'translateY(' + ((1 - tp) * 26).toFixed(2) + 'px)';
        document.getElementById('title-bar').style.width = (clamp(tp, 0, 1) * 620).toFixed(1) + 'px';

        var barP = clamp(dampedSpring(curT, ANCHOR_T, 2.0, 0.65), 0, 1);
        propSegs.forEach(function (ps) {{
          ps.el.style.width = Math.max(4, ps.pct * barP).toFixed(2) + '%';
        }});
        if (donutCircle && propSegs.length > 0) {{
          var leadRatio = clamp((propSegs[0].pct / 100.0) * barP, 0.05, 0.96);
          donutCircle.setAttribute('stroke-dashoffset', (276.46 * (1.0 - leadRatio)).toFixed(2));
        }}
        if (flowPath) {{
          var fpP = clamp(dampedSpring(curT, ANCHOR_T, 1.6, 0.72), 0, 1);
          flowPath.setAttribute('stroke-dashoffset', (flowPathLen * (1.0 - fpP)).toFixed(2));
        }}

        cardNodes.forEach(function (cn, i) {{
          var p = dampedSpring(curT, ANCHOR_T + i * 0.11, 2.3, 0.58);
          var pc = clamp(p, 0, 1);
          cn.el.style.opacity = clamp(p * 1.35, 0, 1).toFixed(3);
          cn.el.style.transform = 'translateX(' + ((1 - p) * 58).toFixed(2) + 'px) scale(' + (0.96 + 0.04 * p).toFixed(4) + ')';
          if (cn.fillEl && typeof cn.item.value === 'number') {{
            var targetPct = clamp((cn.item.value / maxVal) * 100, 6, 100) * pc;
            cn.fillEl.style.width = targetPct.toFixed(2) + '%';
            var unit = (cn.item.unit !== undefined && cn.item.unit !== null) ? String(cn.item.unit) : (String(cn.item.label || '').indexOf('%') >= 0 ? '%' : '');
            var vNow = cn.item.value * pc;
            cn.readoutEl.textContent = (Math.abs(cn.item.value - Math.round(cn.item.value)) < 1e-4 ? Math.round(vNow) : vNow.toFixed(1)) + unit;
          }} else if (MODE === 'proportion' && cn.readoutEl) {{
            var pctVal = (Math.max(1, cn.item.value || 1) * 100) / totalVal;
            cn.readoutEl.textContent = Math.round(pctVal * pc) + '%';
          }}
        }});

        var prog = clamp(curT / Math.max(0.1, DUR), 0, 1);
        document.getElementById('motion-dot').style.width = (prog * 100).toFixed(2) + '%';
      }};

      var fontProm = (document.fonts && document.fonts.ready) ? document.fonts.ready : Promise.resolve();
      var imgProms = (FRAME_SEQ || []).map(function (u) {{
        return new Promise(function (resolve) {{
          var im = new Image();
          im.onload = im.onerror = resolve;
          im.src = u;
        }});
      }});
      Promise.all([fontProm].concat(imgProms)).then(function () {{
        window.seek(0);
        window.READY = true;
      }});
    }})();
  </script>
</body>
</html>
"""


def _prepare_html_scene_dir(
    tdp: Path,
    mode: str,
    title: str,
    items: List[Dict[str, Any]],
    duration_sec: float,
    pal: Dict[str, Any],
    font_path: Optional[str],
    anchor_delay_sec: float = 0.15,
    clip_asset: Optional[str] = None,
    fps: int = DEFAULT_FPS,
) -> None:
    tdp.mkdir(parents=True, exist_ok=True)
    font_rel: Optional[str] = None
    if font_path and Path(font_path).is_file():
        f_dir = tdp / "fonts"
        f_dir.mkdir(parents=True, exist_ok=True)
        dst_f = f_dir / Path(font_path).name
        if not dst_f.exists():
            shutil.copy2(font_path, dst_f)
        font_rel = f"fonts/{dst_f.name}"

    frame_seq_rels: List[str] = []
    seq_fps = fps
    if clip_asset and Path(clip_asset).is_file():
        ca_p = Path(clip_asset)
        f_seq_dir = tdp / "frames"
        f_seq_dir.mkdir(parents=True, exist_ok=True)
        if ca_p.suffix.lower() in (".mp4", ".mov", ".mkv", ".m4v"):
            seq_fps = min(15, fps)
            extracted = extract_clip_sequence(
                ca_p, f_seq_dir, start_sec=0.0, duration_sec=min(4.0, duration_sec), fps=seq_fps, width=640, height=360
            )
            frame_seq_rels = [f"frames/{p.name}" for p in extracted]
        elif ca_p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            dst_img = f_seq_dir / f"0001{ca_p.suffix.lower()}"
            shutil.copy2(ca_p, dst_img)
            frame_seq_rels = [f"frames/{dst_img.name}"]

    html_src = _build_broll_html_page(
        mode, title, items, duration_sec, pal, font_rel,
        anchor_delay_sec=anchor_delay_sec, frame_seq_rels=frame_seq_rels, fps=seq_fps,
    )
    (tdp / "index.html").write_text(html_src, encoding="utf-8")


def render_broll_clip_html(
    output_mp4: Path,
    mode: str,
    title: str,
    items: List[Dict[str, Any]],
    duration_sec: float = 3.0,
    fps: int = DEFAULT_FPS,
    accent_hex: Optional[str] = None,
    bg_hex: Optional[str] = None,
    style_id: Optional[str] = None,
    track: str = "store",
    register: Optional[str] = None,
    anchor_delay_sec: float = 0.15,
    clip_asset: Optional[str] = None,
) -> Path:
    """使用无头 Chrome + capture_html_video.mjs 渲染确定性 HTML/Canvas/SVG 弹簧动效补镜 MP4。"""
    br = detect_browser_renderer()
    if not br.get("available"):
        raise RuntimeError("HTML 浏览器渲染桥不可用（需 node + playwright-core + Chrome）")

    duration_sec = max(2.6, float(duration_sec))
    pal = dict(resolve_style_palette(style_id, track=track, register=register))
    if bg_hex:
        pal["bg_hex"] = bg_hex
    if accent_hex:
        pal["accent_hex"] = accent_hex

    font_path = find_commercial_font(pal.get("font_candidates"))
    output_mp4.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="svs_html_broll_") as td:
        tdp = Path(td)
        _prepare_html_scene_dir(
            tdp, mode, title, items, duration_sec, pal, font_path,
            anchor_delay_sec=anchor_delay_sec, clip_asset=clip_asset, fps=fps,
        )
        smoke_p = tdp / "smoke.json"
        cap_env = dict(os.environ)
        cap_env["FFMPEG_BIN"] = find_bin("ffmpeg")
        res = subprocess.run([
            str(br["node_bin"]),
            str(SCRIPTS_DIR / "capture_html_video.mjs"),
            str(tdp),
            "--page", "index.html",
            "--fps", str(int(fps)),
            "--dur", f"{duration_sec:.4f}",
            "--size", f"{CANVAS_WIDTH}x{CANVAS_HEIGHT}",
            "--jpeg",
            "--out", str(output_mp4.resolve()),
            "--smoke-json", str(smoke_p),
        ], capture_output=True, text=True, env=cap_env)
        if res.returncode != 0 or not output_mp4.is_file() or output_mp4.stat().st_size < 4096:
            raise RuntimeError(f"HTML 动效渲染失败 ({res.returncode}): {(res.stderr or res.stdout)[-400:]}")
    return output_mp4


def render_code_clip(
    output_mp4: Path,
    mode: str,
    title: str,
    items: List[Dict[str, Any]],
    duration_sec: float = 3.0,
    fps: int = DEFAULT_FPS,
    accent_hex: Optional[str] = None,
    bg_hex: Optional[str] = None,
    style_id: Optional[str] = None,
    track: str = "store",
    register: Optional[str] = None,
    anchor_delay_sec: float = 0.15,
    backend: str = "auto",
    clip_asset: Optional[str] = None,
) -> Path:
    """统一代码视频渲染入口：html（确定性无头 Chrome） / pillow（纯 Python） / auto（优先 HTML，缺浏览器无缝回退）。"""
    b_norm = str(backend or "auto").lower()
    if b_norm in ("html", "auto"):
        if detect_browser_renderer().get("available"):
            try:
                return render_broll_clip_html(
                    output_mp4, mode, title, items,
                    duration_sec=duration_sec, fps=fps,
                    accent_hex=accent_hex, bg_hex=bg_hex,
                    style_id=style_id, track=track, register=register,
                    anchor_delay_sec=anchor_delay_sec, clip_asset=clip_asset,
                )
            except Exception as exc:
                if b_norm == "html":
                    raise
                print(f"[code_broll] [WARN] HTML 后端异常已自动回退 Pillow: {exc}")
        elif b_norm == "html":
            raise RuntimeError("指定 --backend html 但未检测到可用 Chrome/playwright-core")

    return render_broll_clip_pillow(
        output_mp4, mode, title, items,
        duration_sec=duration_sec, fps=fps,
        accent_hex=accent_hex, bg_hex=bg_hex,
        style_id=style_id, track=track, register=register,
        anchor_delay_sec=anchor_delay_sec,
    )


def render_spec_scene_html(
    scene_cfg: Dict[str, Any],
    style_id: Optional[str],
    track: str,
    out_mp4: Path,
    backend: str = "auto",
) -> Path:
    """按 00_code_spec.json 单幕配置渲染独立高阶动效场景 MP4（保留底部字幕洁净带）。"""
    mode = str(scene_cfg.get("mode") or "kinetic_text")
    title = str(scene_cfg.get("on_screen_text") or scene_cfg.get("title") or scene_cfg.get("name") or "核心重点")
    items = scene_cfg.get("items") or [
        {"label": title, "subtitle": str(scene_cfg.get("visual_state") or "程序确定性渲染")}
    ]
    dur = max(2.6, float(scene_cfg.get("duration_sec", 3.5)))
    return render_code_clip(
        out_mp4,
        mode=mode,
        title=title,
        items=items,
        duration_sec=dur,
        style_id=style_id,
        track=track,
        register=scene_cfg.get("register"),
        accent_hex=scene_cfg.get("accent_hex"),
        bg_hex=scene_cfg.get("bg_hex"),
        backend=backend,
        clip_asset=scene_cfg.get("clip_asset"),
    )


def render_spec_scenes_batch(
    scene_tasks: List[Tuple[Dict[str, Any], Path]],
    style_id: Optional[str],
    track: str,
    backend: str = "auto",
    fps: int = DEFAULT_FPS,
) -> List[Path]:
    """单 Chrome 实例多幕批处理渲染：一次启动浏览器连续/并发渲染全部场景，大幅降低冷启动开销。"""
    if not scene_tasks:
        return []
    b_norm = str(backend or "auto").lower()
    br = detect_browser_renderer()
    if b_norm in ("html", "auto") and br.get("available"):
        try:
            with tempfile.TemporaryDirectory(prefix="svs_html_batch_") as td:
                tdp = Path(td)
                batch_items: List[Dict[str, Any]] = []
                for idx, (sc_cfg, out_mp4) in enumerate(scene_tasks, start=1):
                    out_mp4.parent.mkdir(parents=True, exist_ok=True)
                    mode = str(sc_cfg.get("mode") or "kinetic_text")
                    title = str(sc_cfg.get("on_screen_text") or sc_cfg.get("title") or sc_cfg.get("name") or "核心重点")
                    items = sc_cfg.get("items") or [
                        {"label": title, "subtitle": str(sc_cfg.get("visual_state") or "程序确定性渲染")}
                    ]
                    dur = max(2.6, float(sc_cfg.get("duration_sec", 3.5)))
                    pal = dict(resolve_style_palette(style_id, track=track, register=sc_cfg.get("register")))
                    if sc_cfg.get("bg_hex"):
                        pal["bg_hex"] = sc_cfg["bg_hex"]
                    if sc_cfg.get("accent_hex"):
                        pal["accent_hex"] = sc_cfg["accent_hex"]
                    font_path = find_commercial_font(pal.get("font_candidates"))
                    sub_dir = tdp / f"scene_{idx:02d}"
                    _prepare_html_scene_dir(
                        sub_dir, mode, title, items, dur, pal, font_path,
                        anchor_delay_sec=float(sc_cfg.get("anchor_delay_sec", 0.15)),
                        clip_asset=sc_cfg.get("clip_asset"),
                        fps=fps,
                    )
                    batch_items.append({
                        "projectDir": str(sub_dir),
                        "page": "index.html",
                        "fps": int(fps),
                        "dur": round(dur, 4),
                        "size": f"{CANVAS_WIDTH}x{CANVAS_HEIGHT}",
                        "jpeg": True,
                        "out": str(out_mp4.resolve()),
                    })
                batch_json_p = tdp / "batch_manifest.json"
                write_json(batch_json_p, {"tasks": batch_items})
                cap_env = dict(os.environ)
                cap_env["FFMPEG_BIN"] = find_bin("ffmpeg")
                res = subprocess.run([
                    str(br["node_bin"]),
                    str(SCRIPTS_DIR / "capture_html_video.mjs"),
                    "--batch-json",
                    str(batch_json_p),
                ], capture_output=True, text=True, env=cap_env)
                if res.returncode == 0 and all(p.is_file() and p.stat().st_size >= 4096 for _, p in scene_tasks):
                    return [p for _, p in scene_tasks]
                if b_norm == "html":
                    raise RuntimeError(f"批量 HTML 渲染失败 ({res.returncode}): {(res.stderr or res.stdout)[-400:]}")
                print(f"[code_broll] [WARN] 批量 HTML 渲染异常，回退逐条 Pillow: {(res.stderr or res.stdout)[-200:]}")
        except Exception as exc:
            if b_norm == "html":
                raise
            print(f"[code_broll] [WARN] 批量 HTML 异常回退 Pillow: {exc}")
    elif b_norm == "html":
        raise RuntimeError("指定 --backend html 但未检测到可用 Chrome/playwright-core")

    return [
        render_spec_scene_html(sc_cfg, style_id=style_id, track=track, out_mp4=out_mp4, backend="pillow")
        for sc_cfg, out_mp4 in scene_tasks
    ]


def generate_demo_media_pack(output_dir: Path, style_id: Optional[str] = None) -> Dict[str, Any]:
    """生成一套完整可用于演示/测试的模拟实拍素材 + 风格化代码补镜 + 对标参考视频。"""
    from PIL import Image, ImageDraw, ImageFont

    ffmpeg = find_bin("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("需要 ffmpeg 生成演示素材。")
    output_dir.mkdir(parents=True, exist_ok=True)
    font_path = find_commercial_font()
    f_big = ImageFont.truetype(font_path, 68) if font_path else ImageFont.load_default()
    f_sub = ImageFont.truetype(font_path, 40) if font_path else ImageFont.load_default()

    broll_data = output_dir / "code_broll_cost_chart.mp4"
    render_broll_clip_pillow(
        broll_data,
        mode="data_chart",
        title="400元烤羊排成本真相",
        items=[
            {"label": "鲜羊排原料成本", "value": 68, "unit": "%"},
            {"label": "腌制与3小时炭火人工", "value": 24, "unit": "%"},
            {"label": "实际门店净利润", "value": 8, "unit": "%"},
        ],
        duration_sec=3.0,
        style_id=style_id,
    )

    broll_flow = output_dir / "code_broll_process.mp4"
    render_broll_clip_pillow(
        broll_flow,
        mode="flow_diagram",
        title="老赵烧烤三条死规矩",
        items=[
            {"label": "只买清晨现宰鲜羊排", "subtitle": "绝不用冻货充数"},
            {"label": "老师傅腌制2小时+烤3小时", "subtitle": "现点现上保证外焦里嫩"},
            {"label": "不满意现场直接退换", "subtitle": "八年老店底线"},
        ],
        duration_sec=3.2,
        style_id=style_id,
    )

    broll_food = output_dir / "broll_lamb_closeup.mp4"
    proc = subprocess.Popen([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{CANVAS_WIDTH}x{CANVAS_HEIGHT}", "-r", "30",
        "-i", "pipe:0", "-c:v", "libx264", *BT709_FFMPEG_ARGS, str(broll_food),
    ], stdin=subprocess.PIPE)
    assert proc.stdin is not None
    for fi in range(150):
        img = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), (54, 34, 24))
        d = ImageDraw.Draw(img)
        shift = int(math.sin(fi / 14.0) * 52)
        d.ellipse([180 + shift, 440, 860 + shift, 1020], fill=(92, 34, 12), outline=(251, 191, 36), width=8)
        d.text((520 + shift, 730), "鲜切烤羊排特写", fill=(255, 255, 255), font=f_big, anchor="mm")
        proc.stdin.write(img.tobytes())
    proc.stdin.close()
    proc.wait()

    broll_grill = output_dir / "broll_charcoal_fire.mp4"
    proc2 = subprocess.Popen([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{CANVAS_WIDTH}x{CANVAS_HEIGHT}", "-r", "30",
        "-i", "pipe:0", "-c:v", "libx264", *BT709_FFMPEG_ARGS, str(broll_grill),
    ], stdin=subprocess.PIPE)
    assert proc2.stdin is not None
    for fi in range(150):
        img = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), (34, 52, 68))
        d = ImageDraw.Draw(img)
        shift_y = int(math.cos(fi / 12.0) * 44)
        d.rounded_rectangle([140, 420 + shift_y, 820, 960 + shift_y], radius=36, fill=(18, 28, 42), outline=(56, 189, 248), width=6)
        d.text((480, 690 + shift_y), "明档现秤实拍", fill=(255, 255, 255), font=f_big, anchor="mm")
        proc2.stdin.write(img.tobytes())
    proc2.stdin.close()
    proc2.wait()

    bench = output_dir / "benchmark_sample.mp4"
    subprocess.run([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-f", "lavfi", "-i", "color=c=#1E293B:s=1080x1920:r=30:d=15",
        "-f", "lavfi", "-i", "sine=frequency=330:duration=15",
        "-c:v", "libx264", *BT709_FFMPEG_ARGS, "-c:a", "aac", "-shortest", str(bench),
    ], check=True)

    return {
        "code_broll_cost_chart": str(broll_data),
        "code_broll_process": str(broll_flow),
        "broll_lamb_closeup": str(broll_food),
        "benchmark_sample": str(bench),
    }


def main() -> None:
    maybe_reexec_in_venv()
    parser = argparse.ArgumentParser(description="生成风格谱同步代码驱动叙事补镜视频")
    parser.add_argument("--output-dir", help="生成整套演示补镜素材到指定目录")
    parser.add_argument("--output", help="单条补镜 MP4 输出路径")
    parser.add_argument(
        "--mode",
        choices=["kinetic_text", "data_chart", "flow_diagram", "proportion", "day_night", "chips", "versus"],
        default="kinetic_text",
    )
    parser.add_argument("--title", default="核心重点")
    parser.add_argument("--items-json", help="JSON 字符串形式的条目列表")
    parser.add_argument("--duration", type=float, default=3.0)
    parser.add_argument("--style-id", help="绑定风格谱 ID (style_01 ~ style_24)")
    parser.add_argument("--track", choices=["store", "creator"], default="store")
    parser.add_argument("--register", choices=["warm_food", "craft_paper", "dark_tech"], help="视觉语域保护 (B6)")
    parser.add_argument("--backend", choices=["auto", "pillow", "html"], default="auto", help="渲染引擎")
    parser.add_argument("--extract-clip", help="预抽视频帧源路径（禁在 HTML 内播 <video>）")
    parser.add_argument("--extract-start", type=float, default=0.0)
    args = parser.parse_args()

    if args.extract_clip:
        out_d = Path(args.output or args.output_dir or "clip_frames")
        frames = extract_clip_sequence(Path(args.extract_clip), out_d, start_sec=args.extract_start, duration_sec=args.duration)
        print(f"[code_broll] 已预抽帧 {len(frames)} 张 -> {out_d}")
        return

    if args.output_dir:
        res = generate_demo_media_pack(Path(args.output_dir), style_id=args.style_id)
        print(f"[code_broll] 已生成代码补镜与演示素材: {json.dumps(res, ensure_ascii=False)}")
        return

    if args.output:
        items = json.loads(args.items_json) if args.items_json else [{"label": args.title, "subtitle": "代码生成补镜"}]
        out = render_code_clip(
            Path(args.output),
            args.mode,
            args.title,
            items,
            duration_sec=args.duration,
            style_id=args.style_id,
            track=args.track,
            register=args.register,
            backend=args.backend,
        )
        print(f"[code_broll] 已生成风格化补镜 -> {out}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()

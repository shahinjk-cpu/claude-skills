#!/usr/bin/env python3
"""
[Step 9: 黄金封面帧优选 + 已调色风格同步封套 + 像素测宽防破框 + 去套话标题]
1. 单次批抽策略减少子进程开销，优先对选出帧施加 Step 7 调色滤镜保持封面/成片影调一致。
2. 彻底清除“深蓝底+5px粗黄框”模板味，按 style_id 同步 resolve_style_palette 色板。
3. 使用 Pillow textbbox 动态缩字控制副标签胶囊与主大字宽度，100% 保证落入 SAFE_ZONE 与 3:4 窗内。
4. 避开 CTA 词摘取有效关键短语，防止拼接出“只做【评论区】？”等病句。
输出：pipeline/09_title_cover.md, pipeline/09_title_cover.json, pipeline/09_cover.jpg, pipeline/09_cover_3x4.jpg
"""

from __future__ import annotations

import argparse
import json
import os
import re
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
    ASSETS_DIR,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    SAFE_ZONE,
    SCRIPTS_DIR,
    bbox_iou,
    contrast_ratio,
    detect_browser_renderer,
    find_bin,
    find_commercial_font,
    fit_text_line,
    hex_to_rgba,
    load_style_applied,
    load_style_spectrum_entry,
    load_typography_cover_rules,
    maybe_reexec_in_venv,
    read_json,
    run_cmd,
    write_json,
)

if __name__ == "__main__":
    maybe_reexec_in_venv()

from generate_code_broll import resolve_style_palette

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from vision_inspector import compute_laplacian_sharpness, inspect_images, segment_person_mask

_CTA_STOP_KWS = {"评论区", "点赞", "关注", "私信", "门店地址", "戳链接", "收藏"}


def _fit_text(draw: Any, text: str, font_path: Optional[str], start_size: int, max_width: int, min_size: int = 24) -> Tuple[Any, str]:
    return fit_text_line(draw, str(text or ""), font_path, max_width=max_width, max_size=start_size, min_size=min_size)


def pick_best_cover_frame(
    edl: Dict[str, Any],
    pipeline_dir: Path,
    work_dir: Path,
    color_plan: Optional[Dict[str, Any]] = None,
    audio_events: Optional[Dict[str, Any]] = None,
) -> Tuple[Optional[Path], Dict[str, Any]]:
    """结合全片情绪峰值句 + 开篇实拍镜头抽帧最多 12 张，以人脸眼部局部对焦锐度 + 自然睁眼优选黄金封面帧，并同步 Step 7 调色。"""
    ffmpeg = find_bin("ffmpeg")
    clips = edl.get("clips", [])
    if not ffmpeg or not clips:
        return None, {"score": 0.0, "face_bbox": None, "reason": "no_media"}

    real_clips = [c for c in clips if c.get("track_role") != "code_broll" and Path(c["media_path"]).exists()]
    pool = real_clips or [c for c in clips if Path(c["media_path"]).exists()]
    if not pool:
        return None, {"score": 0.0, "face_bbox": None, "reason": "no_existing_file"}

    # 结合 03_audio_events 定位全片高情绪/爆点句所在镜头加入封面候选（不再局限于前 4 段）
    selected_clips: List[Dict[str, Any]] = list(pool[:4])
    seen_cids = {c["clip_id"] for c in selected_clips}
    if audio_events:
        high_sents = [
            s for s in (audio_events.get("sentences") or [])
            if s.get("emotion_or_info") in ("hook", "twist", "persona") or (s.get("keywords") and len(s.get("keywords", [])) >= 2)
        ]
        for hs in high_sents[:4]:
            hs_t = float(hs.get("start_sec", 0.0))
            hit_c = next((c for c in pool if float(c.get("timeline_in_sec", 0.0)) <= hs_t <= float(c.get("timeline_out_sec", 0.0))), None)
            if hit_c and hit_c["clip_id"] not in seen_cids:
                selected_clips.append(hit_c)
                seen_cids.add(hit_c["clip_id"])
            if len(selected_clips) >= 7:
                break

    vf_by_cid = {p["clip_id"]: p.get("vf_filter") for p in (color_plan or {}).get("clip_plans", []) if p.get("apply_color_grade")}
    candidates: List[Tuple[Path, float, str, Optional[str], float]] = []

    for c_idx, c in enumerate(selected_clips):
        c_in = float(c.get("source_in_sec", 0.0))
        c_out = float(c.get("source_out_sec", c_in + 1.0))
        span = max(0.1, c_out - c_in)
        offsets = [0.08, span * 0.45, span * 0.80] if c_idx == 0 else [span * 0.35, span * 0.65]
        for off in offsets:
            if len(candidates) >= 12:
                break
            ts = min(max(0.0, c_out - 0.03), max(0.0, c_in + off))
            out_png = work_dir / f"cand_{len(candidates):02d}.png"
            run_cmd([
                ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-ss", f"{ts:.3f}", "-i", c["media_path"],
                "-frames:v", "1",
                "-vf", f"scale={CANVAS_WIDTH}:{CANVAS_HEIGHT}:force_original_aspect_ratio=increase,crop={CANVAS_WIDTH}:{CANVAS_HEIGHT}",
                str(out_png),
            ], check=False)
            if out_png.exists():
                candidates.append((out_png, round(float(c.get("timeline_in_sec", 0.0)) + off, 2), c["clip_id"], c["media_path"], ts))
        if len(candidates) >= 12:
            break

    if not candidates:
        return None, {"score": 0.0, "face_bbox": None, "reason": "extract_failed"}

    man_p = pipeline_dir / "01_manifest.json"
    saliency_by_mp: Dict[str, Dict[str, Any]] = {}
    if man_p.is_file():
        try:
            for it in read_json(man_p).get("items") or []:
                if it.get("normalized_mp4") and isinstance(it.get("saliency_bbox"), dict):
                    saliency_by_mp[str(it["normalized_mp4"])] = it["saliency_bbox"]
        except Exception:
            pass

    def _filter_primary_faces(face_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        kept: List[Dict[str, Any]] = []
        for f in face_list or []:
            bb = f.get("bbox") if isinstance(f, dict) else None
            if not isinstance(bb, dict):
                continue
            bw = float(bb.get("w", 0.0))
            bh = float(bb.get("h", 0.0))
            norm_area = (bw * bh) if max(bw, bh, float(bb.get("x", 0.0)), float(bb.get("y", 0.0))) <= 1.05 else ((bw * bh) / float(CANVAS_WIDTH * CANVAS_HEIGHT))
            if norm_area >= 0.015:
                kept.append(f)
        return kept

    vis_map = inspect_images([p for p, _, _, _, _ in candidates])
    sharps = []
    for p, _, _, _, _ in candidates:
        vr = vis_map.get(str(p), {})
        faces_c = _filter_primary_faces(vr.get("faces") or [])
        with Image.open(p) as im:
            rgb_arr = np.asarray(im.convert("RGB"))
        full_sh = compute_laplacian_sharpness(rgb_arr)
        if faces_c:
            fb = faces_c[0]["bbox"]
            h_i, w_i = rgb_arr.shape[:2]
            x0 = max(0, int(float(fb["x"]) * w_i))
            y0 = max(0, int(float(fb["y"]) * h_i))
            x1 = min(w_i, max(x0 + 16, int((float(fb["x"]) + float(fb["w"])) * w_i)))
            y1 = min(h_i, max(y0 + 16, int((float(fb["y"]) + float(fb["h"])) * h_i)))
            face_sh = compute_laplacian_sharpness(rgb_arr[y0:y1, x0:x1])
            sharps.append(round(face_sh * 0.70 + full_sh * 0.30, 2))
        else:
            sharps.append(full_sh)
    s_min, s_max = min(sharps), max(sharps)

    best_idx = 0
    best_score = -1.0
    best_face: Optional[Dict[str, float]] = None
    best_detail = ""

    for idx, ((p, tl_sec, cid, mp_s, _), sh) in enumerate(zip(candidates, sharps)):
        s_norm = (sh - s_min) / max(1e-4, s_max - s_min) if s_max > s_min else 0.7
        vr = vis_map.get(str(p), {})
        faces = _filter_primary_faces(vr.get("faces") or [])
        f_bb = None
        if faces:
            f0 = faces[0]
            f_bb = f0.get("bbox")
            eye_r = float(f0.get("eye_open_ratio", 0.24))
            mouth_r = float(f0.get("mouth_open_ratio", 0.15))
            if eye_r < 0.13:
                face_score = 0.15
            elif mouth_r > 0.42:
                face_score = 0.45
            else:
                face_score = min(1.0, 0.72 + (eye_r - 0.13) * 2.0)
        else:
            f_bb = saliency_by_mp.get(str(mp_s or ""))
            face_score = 0.55

        comp_score = 0.85
        if f_bb:
            fy_c = float(f_bb["y"]) + float(f_bb["h"]) * 0.5
            if fy_c > 1.0:
                fy_c /= float(CANVAS_HEIGHT)
            comp_score = 1.0 if 0.22 <= fy_c <= 0.65 else 0.55

        total = 0.45 * s_norm + 0.40 * face_score + 0.15 * comp_score
        if total > best_score:
            best_score = total
            best_idx = idx
            best_face = f_bb
            best_detail = f"clip={cid}@{tl_sec}s sharp={sh:.0f} face={face_score:.2f}"

    chosen_path, chosen_t, chosen_cid, chosen_mp, chosen_src_ts = candidates[best_idx]
    vf_grade = vf_by_cid.get(chosen_cid)
    if vf_grade:
        graded_png = work_dir / "best_graded.png"
        run_cmd([
            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
            "-ss", f"{chosen_src_ts:.3f}", "-i", chosen_mp,
            "-frames:v", "1",
            "-vf", f"{vf_grade},scale={CANVAS_WIDTH}:{CANVAS_HEIGHT}:force_original_aspect_ratio=increase,crop={CANVAS_WIDTH}:{CANVAS_HEIGHT}",
            str(graded_png),
        ], check=False)
        if graded_png.exists():
            chosen_path = graded_png

    return chosen_path, {
        "score": round(best_score, 3),
        "best_frame_sec": chosen_t,
        "best_clip_id": chosen_cid,
        "face_bbox": best_face,
        "graded_matched": bool(vf_grade),
        "detail": best_detail,
    }


def _choose_cover_card_y(face_bbox: Optional[Dict[str, float]], card_h: int = 340) -> int:
    """在 9:16 SAFE_ZONE 与 3:4 窗 [240, 1680] 内选与人脸重叠最小的 Y 坐标。"""
    cand_ys = [280, 980, 340, 880, 1080, 240]
    if not face_bbox:
        return 300
    fx, fy, fw, fh = float(face_bbox["x"]), float(face_bbox["y"]), float(face_bbox["w"]), float(face_bbox["h"])
    if max(fx, fy, fw, fh) <= 1.01:
        f_px = {"x": fx * CANVAS_WIDTH, "y": fy * CANVAS_HEIGHT, "w": fw * CANVAS_WIDTH, "h": fh * CANVAS_HEIGHT}
    else:
        f_px = {"x": fx, "y": fy, "w": fw, "h": fh}
    best_y = cand_ys[0]
    best_iou = 999.0
    for cy in cand_ys:
        c_box = {"x": 80.0, "y": float(cy), "w": 780.0, "h": float(card_h)}
        iou = bbox_iou(c_box, f_px)
        if iou < best_iou:
            best_iou = iou
            best_y = cy
        if iou == 0.0:
            break
    return best_y


def _render_ui_safe_preview(composed: Image.Image, out_path: Path) -> None:
    """生成叠加抖音/小红书平台交互区半透明红区与安全区绿框的验收预览图。"""
    ov = Image.new("RGBA", composed.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    # 顶部搜索与返回区 y < 160
    d.rectangle([0, 0, CANVAS_WIDTH, SAFE_ZONE["y_min"]], fill=(239, 68, 68, 80))
    # 右侧互动按钮区 x > 880
    d.rectangle([SAFE_ZONE["x_max"], SAFE_ZONE["y_min"], CANVAS_WIDTH, SAFE_ZONE["y_max"]], fill=(239, 68, 68, 90))
    # 底部文案与进度条区 y > 1480
    d.rectangle([0, SAFE_ZONE["y_max"], CANVAS_WIDTH, CANVAS_HEIGHT], fill=(239, 68, 68, 105))
    # 合法安全区绿线框
    d.rectangle([SAFE_ZONE["x_min"], SAFE_ZONE["y_min"], SAFE_ZONE["x_max"], SAFE_ZONE["y_max"]], outline=(34, 197, 94, 230), width=4)
    Image.alpha_composite(composed.convert("RGBA"), ov).convert("RGB").save(out_path, quality=88)


def build_publish_copy_pack(
    pipeline_dir: Path,
    title_seed: str,
    hook_text: str,
    sentences: List[Dict[str, Any]],
    keywords: List[str],
    track: str = "store",
    cover_main: str = "",
    cover_sub: str = "",
    has_4k_covers: bool = False,
) -> Dict[str, Any]:
    """
    生成分平台差异化发布文案交付包（09_publish_copy_pack.md/.json）：
    同一份素材按不同平台消费场景重写标题钩子、正文节奏与互动引导，绝不一键群发同质文案。
    """
    clean_hook = re.sub(r"[。！？!?]+$", "", str(hook_text or title_seed or "真实拆解")).strip()
    top_kw = keywords[0] if keywords else clean_hook[:6]
    sec_kw = keywords[1] if len(keywords) > 1 else top_kw
    summary_pts = [
        re.sub(r"[。！？!?]+$", "", str(s.get("text") or "").strip())
        for s in (sentences or [])[:4]
        if str(s.get("text") or "").strip()
    ]
    core_line = summary_pts[1] if len(summary_pts) > 1 else clean_hook

    clean_seed = re.sub(r"[。！？!?]+$", "", str(title_seed or "")).strip()
    primary_dy = (clean_seed or clean_hook)[:28]
    dy_titles = [
        primary_dy,
        f"别猜了，把「{top_kw[:6]}」和「{sec_kw[:6]}」摆在一起看"[:28],
        f"为什么大家总在「{top_kw[:6]}」上吃亏？看完就明白"[:28],
    ]
    xhs_titles = [
        f"收藏备用｜{top_kw[:8]}一次看懂"[:20],
        f"关于{top_kw[:6]}，没人告诉你这步"[:20],
        f"{clean_hook[:18]}（附核对清单）"[:20],
    ]
    bili_titles = [
        f"【深度拆解】{clean_hook[:26]}？从原理到真实细节讲透"[:40],
        f"为什么「{top_kw[:8]}」和直觉相反？用可核验的细节还原真相"[:40],
        f"{title_seed[:24]}：完整过程、关键对比与常见误区"[:40],
    ]

    dy_body = f"{clean_hook[:38]}。{core_line[:44]}。你平时遇到过类似情况吗？评论区聊聊。"[:100]
    xhs_paragraphs = [
        f"很多人问过「{top_kw}」到底怎么判断，今天直接把最关键的细节拆开讲清楚。",
        f"1️⃣ 先看核心现象：{clean_hook}。",
        f"2️⃣ 再看容易忽略的细节：{core_line}。",
        "建议先收藏，下次真用到的时候照着核对一遍，不容易走弯路。",
    ]
    bili_desc = (
        f"{clean_hook}。本期视频按真实细节逐层拆解「{top_kw}」与「{sec_kw}」背后的关键差别，"
        f"并附上可直接核对的实操要点。如果你有不同看法或补充案例，欢迎在评论区讨论。"
    )
    bili_pinned = f"置顶互动：你对「{top_kw}」最在意哪一点？在评论区告诉我，下期优先拆解。"

    tags_dy = "#真实记录 #实用干货 #细节拆解 #日常避坑" if track == "creator" else "#同城探店 #实体店日常 #本地生活 #真实记录"
    tags_xhs = "#涨知识 #实用经验 #生活技巧 #避坑指南 #干货收藏" if track == "creator" else "#本地好店 #同城推荐 #实体店实拍 #门店日常 #真实测评"
    tags_bili = f"#{top_kw} #知识科普 #深度拆解 #实用技巧 #真实体验 #逻辑思维 #避坑指南 #细节控"

    pack = {
        "preferred_title": dy_titles[0],
        "preferred_reason": "第一句直接抛出反常识或具体问题，不绕弯子，信息密度最高且正文可直接兑现。",
        "platforms": {
            "douyin_shipinhao": {"titles": dy_titles, "copy": dy_body, "hashtags": tags_dy, "limit_note": "标题 <=28字，正文 <=100字"},
            "xiaohongshu": {"titles": xhs_titles, "paragraphs": xhs_paragraphs, "hashtags": tags_xhs, "limit_note": "标题 <=20字，分段易收藏"},
            "bilibili": {
                "titles": bili_titles,
                "description": bili_desc,
                "pinned_comment": bili_pinned,
                "category_hint": "知识 / 生活实录" if track == "creator" else "生活 / 探店纪实",
                "hashtags": tags_bili,
                "limit_note": "标题 <=40字，信息+悬念完整兑现",
            },
        },
        "cover_summary": {
            "main_text": cover_main.replace("\n", " / "),
            "sub_text": cover_sub,
            "has_dual_4k_code_covers": has_4k_covers,
        },
        "fact_checklist": [
            "标题、封面字与视频正文承诺完全一致，没有夸大或标题党",
            "片中出现的数字、价格、时间、出处均已核对准确",
            "示意图或类比已照实说明，未冒充实测结论",
            "已清除其他平台残留词（如小红书不带小黄车口令）",
        ],
    }

    md_lines = [
        f"# 分平台发布文案与封面交付包",
        "",
        f"> **首选推荐标题**：`{pack['preferred_title']}`",
        f"> **推荐理由**：{pack['preferred_reason']}",
        "",
        "## 一、分平台备选标题（按字数上限与场景差异化定制）",
        "",
        "| 平台 | 备选标题 | 规则提示 |",
        "| :--- | :--- | :--- |",
        *[f"| 抖音 / 视频号 | {i}. {t} | ≤28 字，口语直接 |" for i, t in enumerate(dy_titles, 1)],
        *[f"| 小红书 | {i}. {t} | ≤20 字，强调收藏实用 |" for i, t in enumerate(xhs_titles, 1)],
        *[f"| B 站 | {i}. {t} | ≤40 字，信息 + 悬念 |" for i, t in enumerate(bili_titles, 1)],
        "",
        "## 二、各平台可直接复制的发布正文",
        "",
        "### 1. 抖音 / 视频号",
        dy_body,
        "",
        f"**话题**：{tags_dy}",
        "",
        "### 2. 小红书",
        "\n\n".join(xhs_paragraphs),
        "",
        f"**话题**：{tags_xhs}",
        "",
        "### 3. B 站",
        f"**简介**：{bili_desc}",
        "",
        f"**标签**：{tags_bili}",
        f"**建议分区**：{pack['platforms']['bilibili']['category_hint']}",
        f"**置顶评论**：{bili_pinned}",
        "",
        "## 三、封面说明与发布前事实核对",
        f"- **封面主大字**：`{pack['cover_summary']['main_text']}` | **副标签**：`{cover_sub}`",
        (
            "- **4K 代码封面**：`09_cover_land_4k.png`（3840×2160 横版，核心锁中央 4:3）& `09_cover_port_4k.png`（2160×2880 竖版 3:4）"
            if has_4k_covers
            else "- **标准封面**：`09_cover.jpg`（9:16 首帧）& `09_cover_3x4.jpg`（3:4 主页卡片）"
        ),
        "",
        *[f"- [ ] {chk}" for chk in pack["fact_checklist"]],
        "",
    ]
    (pipeline_dir / "09_publish_copy_pack.md").write_text("\n".join(md_lines), encoding="utf-8")
    write_json(pipeline_dir / "09_publish_copy_pack.json", pack)
    return pack


def render_dual_4k_code_covers(
    out_dir: Path,
    kicker: str,
    hero_lines: List[str],
    title: str,
    palette: Optional[Dict[str, str]] = None,
    font_mode: str = "serif",
    with_guides: bool = True,
) -> Dict[str, Any]:
    """用单源码 cover_4k.html + 无头浏览器 2x 缩放渲染横版 4K (3840×2160，核心锁中央 4:3) + 竖版 4K (2160×2880)。"""
    br = detect_browser_renderer()
    runtime_dir = ASSETS_DIR / "canvas_runtime"
    if not br.get("available") or not (runtime_dir / "cover_4k.html").is_file():
        return {"ok": False, "reason": "browser_or_runtime_unavailable", "outputs": []}

    out_dir.mkdir(parents=True, exist_ok=True)
    check_dir = out_dir / "work_checks"
    with tempfile.TemporaryDirectory(prefix="svs_cover4k_") as td:
        tdp = Path(td)
        for fn in ("stage_clock.js", "visual_kit.js", "cover_4k.html"):
            shutil.copy2(runtime_dir / fn, tdp / fn)
        cov_data = {
            "kicker": str(kicker or "")[:16],
            "hero_lines": [str(x)[:8] for x in (hero_lines or [title[:6]])[:2]],
            "title": str(title or "")[:14],
            "font_mode": font_mode,
            "palette": palette or {
                "bg": "#040711",
                "ink": "#f1f5f9",
                "sub": "#94a3b8",
                "accent": "#5ce1e6",
                "accent2": "#f59e0b",
                "alert": "#ff6b57",
            },
        }
        (tdp / "cover_data.js").write_text(
            "window.SVS_COVER_DATA = " + json.dumps(cov_data, ensure_ascii=False, indent=2) + ";\n",
            encoding="utf-8",
        )
        try:
            from knowledge_animator import inject_stage_commercial_fonts
            inject_stage_commercial_fonts(
                tdp,
                extra_text=f"{cov_data['kicker']}{''.join(cov_data['hero_lines'])}{cov_data['title']}",
                html_files=("cover_4k.html",),
            )
        except Exception:
            pass
        cmd = [
            str(br["node_bin"]),
            str(SCRIPTS_DIR / "capture_html_video.mjs"),
            str(tdp),
            "--cover-4k",
            "--page", "cover_4k.html",
            "--out-dir", str(out_dir.resolve()),
            "--name", "09_cover",
            "--check-dir", str(check_dir.resolve()),
        ]
        if with_guides:
            cmd.append("--guides")
        cap_env = dict(os.environ)
        ff = find_bin("ffmpeg")
        if ff:
            cap_env["FFMPEG_BIN"] = ff
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", env=cap_env)
        if proc.returncode != 0:
            return {"ok": False, "reason": (proc.stderr or proc.stdout)[-300:], "outputs": []}
        try:
            return json.loads(proc.stdout)
        except Exception:
            return {
                "ok": (out_dir / "09_cover_land_4k.png").is_file() and (out_dir / "09_cover_port_4k.png").is_file(),
                "outputs": [
                    str((out_dir / "09_cover_land_4k.png").resolve()),
                    str((out_dir / "09_cover_port_4k.png").resolve()),
                ],
            }


def run_step9(
    pipeline_dir: Path,
    track: str = "store",
    style_id: Optional[str] = None,
    code_cover_4k: bool = False,
) -> Dict[str, Any]:
    audio_events = read_json(pipeline_dir / "03_audio_events.json")
    edl = read_json(pipeline_dir / "04_edl.json")
    color_p = pipeline_dir / "07_color_plan.json"
    color_plan = read_json(color_p) if color_p.exists() else None
    raw_intel_p = pipeline_dir / "00_raw_intel.json"
    raw_intel = read_json(raw_intel_p) if raw_intel_p.exists() else {}

    eff_style = style_id or edl.get("style_id") or load_style_applied(pipeline_dir)
    pal = resolve_style_palette(eff_style, track=track)

    sentences = audio_events["sentences"]
    hook_text = sentences[0]["text"] if sentences else "先看真实对比再决定"
    keywords: List[str] = []
    for s in sentences[:4]:
        for kw in s.get("keywords", []):
            if str(kw).strip() and str(kw).strip() not in _CTA_STOP_KWS and kw not in keywords:
                keywords.append(str(kw).strip())
    top_kw = keywords[0] if keywords else hook_text[:6]
    sec_kw = keywords[1] if len(keywords) > 1 else (top_kw if len(sentences) <= 1 else "")

    hook_clean = hook_text.rstrip("。！？，；")
    if len(hook_clean) > 22:
        parts = [p for p in hook_clean.split("，") if p]
        hook_clean = "，".join(parts[:2]) if len("，".join(parts[:2])) <= 24 else parts[0]

    sent2_clean = (sentences[1]["text"].rstrip("。！？，；") if len(sentences) > 1 else "")
    hook_parts = [p.strip() for p in hook_text.replace("？", "，").replace("！", "，").split("，") if p.strip()]
    alt_line2 = sec_kw or (hook_parts[1][:8] if len(hook_parts) > 1 else (sent2_clean[:8] or hook_clean[-8:]))

    raw_qs = raw_intel.get("customer_questions", [])
    raw_pains = raw_intel.get("pain_keywords", [])
    pain_phrase = ""
    if raw_pains:
        p0 = str(raw_pains[0]).strip()
        pain_phrase = f"{p0}讲透" if p0.endswith("问题") else f"{p0}问题讲透"

    if track == "store":
        q_lead = f"被问最多的问题：{raw_qs[0][:20]}" if raw_qs else hook_clean
        titles = [
            q_lead,
            f"把「{top_kw}」真实成本摊开算一遍，同城老客自己判断",
            f"做这行最在意「{sec_kw or top_kw}」，直接把一线标准讲透",
        ]
        cover_main_l1 = top_kw[:8] if len(top_kw) >= 2 else hook_clean[:8]
        cover_main_l2 = alt_line2[:8] if alt_line2[:8] != cover_main_l1 else (hook_clean[-8:] or "实地真算账")
        cover_sub = f"门店实拍 · {pain_phrase}" if pain_phrase else f"实拍纪实 · {(sec_kw or top_kw)[:8]}"
        hashtags = "#同城探店 #实体店日常 #本地生活 #真实记录 #一线实拍"
    else:
        q_lead = f"评论区都在问：{raw_qs[0][:20]}" if raw_qs else hook_clean
        titles = [
            q_lead,
            f"把「{top_kw}」和「{sec_kw or top_kw}」放在一起看，差别在哪很清楚",
            f"少走弯路的一条实操细节：{hook_clean[:18]}",
        ]
        cover_main_l1 = top_kw[:8] if len(top_kw) >= 2 else hook_clean[:8]
        cover_main_l2 = alt_line2[:8] if alt_line2[:8] != cover_main_l1 else (hook_clean[-8:] or "核心对照看")
        cover_sub = f"实操复盘 · {(sec_kw or top_kw)[:8]}"
        hashtags = "#短视频实操 #创作复盘 #内容拆解 #经验分享 #干货"

    titles = [str(t).rstrip("。") for t in titles]
    cover_main = f"{cover_main_l1}\n{cover_main_l2}"
    cover_path = pipeline_dir / "09_cover.jpg"
    cover_3x4_path = pipeline_dir / "09_cover_3x4.jpg"
    ui_preview_path = pipeline_dir / "09_ui_safe_preview.jpg"

    person_cutout_applied = False
    person_mask_img: Optional[Image.Image] = None
    with tempfile.TemporaryDirectory(prefix="svs_cover_") as td:
        td_p = Path(td)
        best_frame_p, best_meta = pick_best_cover_frame(
            edl, pipeline_dir, td_p, color_plan=color_plan, audio_events=audio_events
        )
        if best_frame_p and best_frame_p.exists():
            base_img = Image.open(best_frame_p).convert("RGBA")
            # 决策 2A：若存在人脸主体且本机支持 macOS 原生 Apple Vision 前景人像分割，预提取人物前景蒙版用于主体压字纵深海报
            if best_meta.get("face_bbox"):
                mask_p = td_p / "person_mask.png"
                if segment_person_mask(best_frame_p, mask_p):
                    try:
                        with Image.open(mask_p) as m_im:
                            m_l = m_im.convert("L").resize((CANVAS_WIDTH, CANVAS_HEIGHT), Image.Resampling.BILINEAR)
                            m_arr = np.asarray(m_l, dtype=np.float32)
                            cov = float(np.mean(m_arr >= 128.0))
                            if 0.08 <= cov <= 0.65:
                                person_mask_img = m_l
                    except Exception:
                        person_mask_img = None
        else:
            base_img = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), hex_to_rgba(pal["bg_hex"], 255))

    cover_rules = load_typography_cover_rules()
    layouts_cfg = cover_rules.get("cover_3x4_layouts") or {}
    style_entry = load_style_spectrum_entry(eff_style) if eff_style else None
    cover_layout_id = str(((style_entry or {}).get("title_cover_layout") or {}).get("layout_id") or "")
    use_jianying_poster = (cover_layout_id == "jianying_poster_4zone")
    sub_spec = (style_entry or {}).get("subtitle_spec") or {}
    style_font_cands = sub_spec.get("font_candidates") or pal.get("font_candidates")
    kw_hex_style = str(sub_spec.get("keyword_color") or pal.get("accent_hex") or "#FFBF17")

    card_x1, card_x2 = 80, SAFE_ZONE["x_max"] - 20  # [80, 860] -> w=780
    card_h = 340
    card_y = _choose_cover_card_y(best_meta.get("face_bbox"), card_h=card_h)

    scrim_layer = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
    overlay = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
    mid_layer = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    scrim_draw = ImageDraw.Draw(scrim_layer)
    font_path = find_commercial_font(style_font_cands)

    if use_jianying_poster:
        # 四区高低错落无闷框爆款封面（底图压暗渐变留在主体图层下方，保人物清晰）
        for gy in range(0, 560, 4):
            a = int(125 * (1.0 - gy / 560.0))
            scrim_draw.rectangle([0, gy, CANVAS_WIDTH, gy + 4], fill=(10, 12, 16, a))
        for gy in range(1060, CANVAS_HEIGHT, 4):
            a = int(145 * min(1.0, (gy - 1060) / 520.0))
            scrim_draw.rectangle([0, gy, CANVAS_WIDTH, gy + 4], fill=(10, 12, 16, a))

        safe_w = SAFE_ZONE["x_max"] - 80  # 800px，严格在 [80, 880] 内不触碰右侧栏
        # 起始 y=262，严格落在 3:4 主页封面裁切 [240, 1680] 内部，绝不齐头切字！
        lead_small = "门店真实记录" if track == "store" else "实操真相拆解"
        f_lead, fit_lead = _fit_text(draw, lead_small, font_path, 46, 420, min_size=28)
        draw.text((88, 262), fit_lead, fill=(255, 255, 255, 255), font=f_lead, stroke_width=5, stroke_fill=(0, 0, 0, 255))

        f_l1, fit_l1 = _fit_text(draw, cover_main_l1, font_path, 106, safe_w - 20, min_size=54)
        draw.text((84 + 4, 326 + 6), fit_l1, fill=(0, 0, 0, 220), font=f_l1, stroke_width=7, stroke_fill=(0, 0, 0, 220))
        draw.text((84, 326), fit_l1, fill=(255, 42, 36, 255), font=f_l1, stroke_width=7, stroke_fill=(0, 0, 0, 255))

        # 中左区：微倾斜明黄黑边贴纸字（cover_main_l2），严格转换归一化 face_bbox 到像素坐标并钳制右边界 <= 868
        f_l2, fit_l2 = _fit_text(draw, cover_main_l2, font_path, 80, safe_w - 80, min_size=42)
        l2_tmp = Image.new("RGBA", (safe_w + 80, 180), (0, 0, 0, 0))
        l2_d = ImageDraw.Draw(l2_tmp)
        l2_d.text((28 + 3, 42 + 4), fit_l2, fill=(0, 0, 0, 220), font=f_l2, stroke_width=6, stroke_fill=(0, 0, 0, 220))
        l2_d.text((28, 42), fit_l2, fill=(255, 226, 52, 255), font=f_l2, stroke_width=6, stroke_fill=(0, 0, 0, 220))
        l2_rot = l2_tmp.rotate(4.5, resample=Image.Resampling.BICUBIC, expand=True)
        l2_bb = l2_rot.getbbox()
        if l2_bb:
            l2_rot = l2_rot.crop(l2_bb)
        max_rot_w = SAFE_ZONE["x_max"] - 84 - 12
        if l2_rot.width > max_rot_w:
            sc_r = max_rot_w / float(l2_rot.width)
            l2_rot = l2_rot.resize((max(1, int(l2_rot.width * sc_r)), max(1, int(l2_rot.height * sc_r))), Image.Resampling.LANCZOS)
        fb_raw = best_meta.get("face_bbox")
        face_y_px = 9999.0
        face_bottom_px = 0.0
        if isinstance(fb_raw, dict):
            raw_fy = float(fb_raw.get("y", 0.5))
            raw_fh = float(fb_raw.get("h", 0.16))
            face_y_px = raw_fy * CANVAS_HEIGHT if max(raw_fy, raw_fh) <= 1.01 else raw_fy
            face_bottom_px = face_y_px + (raw_fh * CANVAS_HEIGHT if max(raw_fy, raw_fh) <= 1.01 else raw_fh)
        l2_y = 1010 if face_y_px < 860.0 else 760
        if face_bottom_px > 0:
            l2_y = max(l2_y, int(face_bottom_px) + 28)
        l2_y = max(500, min(1210 - l2_rot.height, l2_y))

        l2_put_front = False
        if person_mask_img is not None:
            lx1 = max(0, min(CANVAS_WIDTH - 1, 84))
            ly1 = max(0, min(CANVAS_HEIGHT - 1, int(l2_y)))
            lx2 = max(lx1 + 1, min(CANVAS_WIDTH, 84 + l2_rot.width))
            ly2 = max(ly1 + 1, min(CANVAS_HEIGHT, int(l2_y) + l2_rot.height))
            l2_mask_roi = np.asarray(person_mask_img, dtype=np.float32)[ly1:ly2, lx1:lx2]
            if l2_mask_roi.size > 0 and float(np.mean(l2_mask_roi >= 128.0)) > 0.15:
                l2_put_front = True
        if l2_put_front:
            overlay.alpha_composite(l2_rot, dest=(84, l2_y))
            draw = ImageDraw.Draw(overlay)
        else:
            mid_layer.alpha_composite(l2_rot, dest=(84, l2_y))

        # 下方转化区：白字黑边副标 + 红白双色大字（严格落在 y <= 1460 安全区内）
        f_sub, fit_sub = _fit_text(draw, cover_sub, font_path, 44, safe_w - 20, min_size=26)
        draw.text((88 + 2, 1228 + 3), fit_sub, fill=(0, 0, 0, 220), font=f_sub, stroke_width=4, stroke_fill=(0, 0, 0, 220))
        draw.text((88, 1228), fit_sub, fill=(255, 255, 255, 255), font=f_sub, stroke_width=4, stroke_fill=(0, 0, 0, 255))

        cta_punch = (top_kw[:4] + "实测") if len(top_kw) >= 2 else "一线实拍"
        f_cta, fit_cta = _fit_text(draw, cta_punch, font_path, 86, safe_w - 20, min_size=46)
        split_at = max(1, len(fit_cta) // 2)
        p_left, p_right = fit_cta[:split_at], fit_cta[split_at:]
        draw.text((86 + 3, 1296 + 5), p_left, fill=(0, 0, 0, 225), font=f_cta, stroke_width=6, stroke_fill=(0, 0, 0, 225))
        draw.text((86, 1296), p_left, fill=(255, 36, 56, 255), font=f_cta, stroke_width=6, stroke_fill=(0, 0, 0, 255))
        lw = int(draw.textbbox((0, 0), p_left, font=f_cta, stroke_width=6)[2])
        if p_right:
            draw.text((86 + lw + 3, 1296 + 5), p_right, fill=(0, 0, 0, 225), font=f_cta, stroke_width=6, stroke_fill=(0, 0, 0, 225))
            draw.text((86 + lw, 1296), p_right, fill=(255, 255, 255, 255), font=f_cta, stroke_width=6, stroke_fill=(0, 0, 0, 255))

        card_y = 262
        l1_w = int(draw.textbbox((0, 0), fit_l1, font=f_l1, stroke_width=7)[2])
        thumb_eval_box = (80, 256, min(860, max(380, 88 + l1_w + 24)), 460)
    elif cover_layout_id == "top_giant_bottom_sub":
        # 顶部胶囊标签 + 顶部大号主标题 + 底部双行副标构图
        grad = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grad)
        for gy in range(200, 620, 4):
            a = int(185 * (1.0 - abs(gy - 360) / 260.0))
            gd.rectangle([0, gy, CANVAS_WIDTH, gy + 4], fill=(10, 12, 18, max(0, a)))
        for gy in range(1180, 1520, 4):
            a = int(185 * (1.0 - abs(gy - 1340) / 180.0))
            gd.rectangle([0, gy, CANVAS_WIDTH, gy + 4], fill=(10, 12, 18, max(0, a)))
        overlay = Image.alpha_composite(overlay, grad)
        draw = ImageDraw.Draw(overlay)

        safe_w = SAFE_ZONE["x_max"] - 80
        kw_rgba = hex_to_rgba(kw_hex_style, 255)
        if contrast_ratio(kw_rgba[:3], (10, 12, 18)) < 5.5:
            kw_rgba = (255, 214, 55, 255)
        f_sub, fit_sub = _fit_text(draw, cover_sub, font_path, 36, safe_w - 80, min_size=22)
        sub_bb = draw.textbbox((0, 0), fit_sub, font=f_sub)
        cap_w = min(safe_w, max(240, int(sub_bb[2] - sub_bb[0]) + 56))
        cap_x = 84
        draw.rounded_rectangle([cap_x, 262, cap_x + cap_w, 322], radius=16, fill=(183, 28, 28, 240))
        draw.text((cap_x + cap_w // 2, 292), fit_sub, fill=(255, 255, 255, 255), font=f_sub, anchor="mm")

        f_l1, fit_l1 = _fit_text(draw, cover_main_l1, font_path, 104, safe_w - 20, min_size=52)
        draw.text((84 + 4, 344 + 5), fit_l1, fill=(0, 0, 0, 235), font=f_l1, stroke_width=7, stroke_fill=(0, 0, 0, 235))
        draw.text((84, 344), fit_l1, fill=kw_rgba, font=f_l1, stroke_width=7, stroke_fill=(0, 0, 0, 255))

        f_l2, fit_l2 = _fit_text(draw, cover_main_l2, font_path, 78, safe_w - 20, min_size=42)
        draw.text((84 + 3, 1280 + 4), fit_l2, fill=(0, 0, 0, 235), font=f_l2, stroke_width=5, stroke_fill=(0, 0, 0, 235))
        draw.text((84, 1280), fit_l2, fill=(255, 255, 255, 255), font=f_l2, stroke_width=5, stroke_fill=(0, 0, 0, 255))
        card_y = 262
        l1_w = int(draw.textbbox((0, 0), fit_l1, font=f_l1, stroke_width=7)[2])
        thumb_eval_box = (80, 258, min(860, max(380, 88 + max(cap_w, l1_w) + 24)), 475)
    elif cover_layout_id == "four_corner_editorial":
        # 四角留白 / 黑底画框高定构图封面
        grad = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
        gd = ImageDraw.Draw(grad)
        gd.rectangle([0, 0, CANVAS_WIDTH, 475], fill=(8, 10, 14, 215))
        gd.rectangle([0, 1210, CANVAS_WIDTH, CANVAS_HEIGHT], fill=(8, 10, 14, 220))
        gd.rectangle([68, 252, SAFE_ZONE["x_max"] - 12, 1456], outline=(255, 245, 137, 200), width=3)
        overlay = Image.alpha_composite(overlay, grad)
        draw = ImageDraw.Draw(overlay)

        safe_w = SAFE_ZONE["x_max"] - 110
        f_l1, fit_l1 = _fit_text(draw, cover_main_l1, font_path, 96, safe_w, min_size=48)
        draw.text((96 + 3, 286 + 4), fit_l1, fill=(0, 0, 0, 235), font=f_l1, stroke_width=6, stroke_fill=(0, 0, 0, 235))
        draw.text((96, 286), fit_l1, fill=(255, 245, 137, 255), font=f_l1, stroke_width=6, stroke_fill=(0, 0, 0, 255))
        f_l2, fit_l2 = _fit_text(draw, cover_main_l2, font_path, 68, safe_w, min_size=36)
        draw.text((96, 1252), fit_l2, fill=(255, 255, 255, 255), font=f_l2, stroke_width=5, stroke_fill=(0, 0, 0, 245))
        f_sub, fit_sub = _fit_text(draw, cover_sub, font_path, 36, safe_w, min_size=22)
        draw.text((96, 1348), fit_sub, fill=(255, 245, 137, 240), font=f_sub, stroke_width=3, stroke_fill=(0, 0, 0, 230))
        card_y = 276
        l1_w = int(draw.textbbox((0, 0), fit_l1, font=f_l1, stroke_width=6)[2])
        thumb_eval_box = (84, 268, min(860, max(380, 96 + l1_w + 28)), 445)
    elif cover_layout_id == "left_right_split":
        lr_zones = (layouts_cfg.get("left_right_split") or {}).get("zones") or {}
        hl_z = lr_zones.get("left_headline_col") or {"x": 80, "y": 330, "max_w": 520, "size": 88, "color": "#FFBF17"}
        aux_z = lr_zones.get("left_aux_points") or {"x": 84, "y": 540, "max_w": 480, "size": 36, "color": "#FFFFFF"}
        ban_z = lr_zones.get("bottom_banner") or {"x": 80, "y": 1270, "max_w": 760, "size": 68, "color": "#FFFFFF"}

        for gx in range(0, 620, 6):
            a = int(190 * (1.0 - gx / 620.0))
            scrim_draw.rectangle([gx, 210, gx + 6, 1140], fill=(10, 12, 18, max(0, a)))
        for gy in range(1140, 1490, 4):
            scrim_draw.rectangle([0, gy, CANVAS_WIDTH, gy + 4], fill=(10, 12, 18, 180))

        # 归一化 face_bbox -> 含额头上方安全余量的像素避让框，防止副标胶囊压中眉眼
        padded_face: Optional[Dict[str, float]] = None
        fb_raw = best_meta.get("face_bbox")
        if isinstance(fb_raw, dict):
            fx = float(fb_raw.get("x", 0.0))
            fy = float(fb_raw.get("y", 0.0))
            fw = float(fb_raw.get("w", 0.0))
            fh = float(fb_raw.get("h", 0.0))
            if max(fx, fy, fw, fh) <= 1.01:
                fx, fy, fw, fh = fx * CANVAS_WIDTH, fy * CANVAS_HEIGHT, fw * CANVAS_WIDTH, fh * CANVAS_HEIGHT
            if fw > 10 and fh > 10:
                head_pad_top = max(60.0, fh * 0.36)
                padded_face = {
                    "x": fx - 24.0,
                    "y": fy - head_pad_top,
                    "w": fw + 48.0,
                    "h": fh + head_pad_top + 24.0,
                }

        hl_col = hex_to_rgba(str(hl_z.get("color") or kw_hex_style), 255)
        if contrast_ratio(hl_col[:3], (10, 12, 18)) < 5.0:
            hl_col = (255, 214, 55, 255)
        hx = int(hl_z.get("x", 80))
        hy = int(hl_z.get("y", 330))
        hw = min(int(hl_z.get("max_w", 520)), SAFE_ZONE["x_max"] - hx - 20)
        f_l1, fit_l1 = _fit_text(draw, cover_main_l1, font_path, int(hl_z.get("size", 88)), hw, min_size=42)
        l1_bb_pre = draw.textbbox((hx, hy), fit_l1, font=f_l1, stroke_width=6)
        l1_h_pre = max(60, int(l1_bb_pre[3] - l1_bb_pre[1]))
        l1_box_pre = {"x": float(hx), "y": float(hy), "w": float(max(120, l1_bb_pre[2] - l1_bb_pre[0])), "h": float(l1_h_pre)}
        if padded_face and bbox_iou(l1_box_pre, padded_face) > 0.0:
            hy = max(258, min(hy, int(padded_face["y"] - l1_h_pre - 12)))
        draw.text((hx + 3, hy + 4), fit_l1, fill=(0, 0, 0, 235), font=f_l1, stroke_width=6, stroke_fill=(0, 0, 0, 235))
        draw.text((hx, hy), fit_l1, fill=hl_col, font=f_l1, stroke_width=6, stroke_fill=(0, 0, 0, 255))

        bx = int(ban_z.get("x", 80))
        by = int(ban_z.get("y", 1270))
        ax = int(aux_z.get("x", 84))
        ay = int(aux_z.get("y", 540))
        aw = min(int(aux_z.get("max_w", 480)), SAFE_ZONE["x_max"] - ax - 20)
        f_sub, fit_sub = _fit_text(draw, cover_sub, font_path, int(aux_z.get("size", 36)), aw - 32, min_size=22)
        sub_bb = draw.textbbox((0, 0), fit_sub, font=f_sub)
        cap_w = min(aw, max(200, int(sub_bb[2] - sub_bb[0]) + 40))
        if padded_face and bbox_iou({"x": float(ax), "y": float(ay), "w": float(cap_w), "h": 58.0}, padded_face) > 0.0:
            left_gap = int(padded_face["x"]) - 12 - ax
            if left_gap >= 280:
                aw = min(aw, left_gap)
                f_sub, fit_sub = _fit_text(draw, cover_sub, font_path, int(aux_z.get("size", 36)), aw - 32, min_size=20)
                sub_bb = draw.textbbox((0, 0), fit_sub, font=f_sub)
                cap_w = min(aw, max(200, int(sub_bb[2] - sub_bb[0]) + 40))
            else:
                # 居中大头像：自动让位至下方暗角横幅正上方，绝不压脸/眉眼
                ax = bx
                ay = max(int(padded_face["y"] + padded_face["h"] + 24), by - 78)
                aw = min(int(ban_z.get("max_w", 760)), SAFE_ZONE["x_max"] - ax - 20)
                f_sub, fit_sub = _fit_text(draw, cover_sub, font_path, int(aux_z.get("size", 36)), aw - 32, min_size=22)
                sub_bb = draw.textbbox((0, 0), fit_sub, font=f_sub)
                cap_w = min(aw, max(200, int(sub_bb[2] - sub_bb[0]) + 40))

        draw.rounded_rectangle([ax, ay, ax + cap_w, ay + 58], radius=12, fill=(22, 26, 36, 230), outline=hl_col, width=2)
        draw.text((ax + cap_w // 2, ay + 29), fit_sub, fill=(255, 255, 255, 255), font=f_sub, anchor="mm")

        bw_max = min(int(ban_z.get("max_w", 760)), SAFE_ZONE["x_max"] - bx - 12)
        f_l2, fit_l2 = _fit_text(draw, cover_main_l2, font_path, int(ban_z.get("size", 68)), bw_max, min_size=36)
        draw.text((bx + 3, by + 4), fit_l2, fill=(0, 0, 0, 235), font=f_l2, stroke_width=5, stroke_fill=(0, 0, 0, 235))
        draw.text((bx, by), fit_l2, fill=(255, 255, 255, 255), font=f_l2, stroke_width=5, stroke_fill=(0, 0, 0, 255))
        card_y = hy
        l1_bb = draw.textbbox((hx, hy), fit_l1, font=f_l1, stroke_width=6)
        thumb_eval_box = (
            max(0, min(hx, int(l1_bb[0]))),
            max(0, min(hy, int(l1_bb[1]))),
            min(860, max(380, int(l1_bb[2]) + 24)),
            min(SAFE_ZONE["y_max"], max(hy + 140, int(l1_bb[3]) + 24)),
        )
    else:
        # 通用杂志卡片封套
        card_fill = hex_to_rgba(pal["card_bg_hex"], 224 if pal.get("is_light") else 212)
        border_col = hex_to_rgba(pal["border_hex"], 230)
        accent_col = hex_to_rgba(pal["accent_hex"], 255)
        badge_txt_col = hex_to_rgba(pal["badge_text_hex"], 255)
        main_txt_col = hex_to_rgba(pal["title_hex"], 255)

        if contrast_ratio(main_txt_col[:3], card_fill[:3]) < 4.5:
            main_txt_col = (17, 24, 39, 255) if pal.get("is_light") else (255, 255, 255, 255)
        l2_col = accent_col if contrast_ratio(accent_col[:3], card_fill[:3]) >= 3.2 else main_txt_col

        draw.rounded_rectangle([card_x1, card_y, card_x2, card_y + card_h], radius=22, fill=card_fill, outline=border_col, width=2)
        draw.rounded_rectangle([card_x1, card_y + 24, card_x1 + 8, card_y + card_h - 24], radius=4, fill=accent_col)

        inner_x = card_x1 + 32
        max_inner_w = (card_x2 - 28) - inner_x
        f_sub, fit_sub = _fit_text(draw, cover_sub, font_path, 34, max_inner_w - 44, min_size=22)
        sub_bb = draw.textbbox((0, 0), fit_sub, font=f_sub)
        cap_w = min(max_inner_w, max(220, int(sub_bb[2] - sub_bb[0]) + 44))
        draw.rounded_rectangle([inner_x, card_y + 28, inner_x + cap_w, card_y + 84], radius=12, fill=accent_col)
        draw.text((inner_x + cap_w // 2, card_y + 56), fit_sub, fill=badge_txt_col, font=f_sub, anchor="mm")

        f_l1, fit_l1 = _fit_text(draw, cover_main_l1, font_path, 78, max_inner_w, min_size=40)
        f_l2, fit_l2 = _fit_text(draw, cover_main_l2, font_path, 72, max_inner_w, min_size=36)
        draw.text((inner_x, card_y + 114), fit_l1, fill=main_txt_col, font=f_l1)
        draw.text((inner_x, card_y + 216), fit_l2, fill=l2_col, font=f_l2)
        l1_w = int(draw.textbbox((0, 0), fit_l1, font=f_l1)[2])
        l2_w = int(draw.textbbox((0, 0), fit_l2, font=f_l2)[2])
        thumb_eval_box = (card_x1, card_y, min(card_x2, max(card_x1 + 320, inner_x + max(cap_w, l1_w, l2_w) + 28)), card_y + card_h)

    stage_bg = Image.alpha_composite(base_img, scrim_layer)
    if use_jianying_poster:
        # 纵深合成：压暗底图 -> 中景贴纸字 -> (可选)前景人像边缘主体压字(重叠<=35%) -> 顶/底主标题清晰保底
        stage = Image.alpha_composite(stage_bg, mid_layer)
        if person_mask_img is not None:
            tx1, ty1, tx2, ty2 = (
                max(0, min(CANVAS_WIDTH - 1, int(thumb_eval_box[0]))),
                max(0, min(CANVAS_HEIGHT - 1, int(thumb_eval_box[1]))),
                max(1, min(CANVAS_WIDTH, int(thumb_eval_box[2]))),
                max(1, min(CANVAS_HEIGHT, int(thumb_eval_box[3]))),
            )
            title_region_mask = np.asarray(person_mask_img, dtype=np.float32)[ty1:ty2, tx1:tx2]
            fg_overlap = float(np.mean(title_region_mask >= 128.0)) if title_region_mask.size > 0 else 0.0
            if fg_overlap <= 0.35:
                fg_person = base_img.copy()
                fg_person.putalpha(person_mask_img)
                stage = Image.alpha_composite(stage, fg_person)
                person_cutout_applied = True
        composed = Image.alpha_composite(stage, overlay).convert("RGB")
    else:
        composed = Image.alpha_composite(stage_bg, overlay).convert("RGB")
    composed.save(cover_path, quality=92)

    crop_3x4 = composed.crop((0, 240, CANVAS_WIDTH, 1680))
    crop_3x4.save(cover_3x4_path, quality=92)

    _render_ui_safe_preview(composed, ui_preview_path)

    # 360px 手机信息流真实缩略对照图（左侧单列流 360px 首帧 + 右侧双列瀑布流 176px 主页封面，一眼看清手机上字清不清）
    feed_preview_path = pipeline_dir / "09_cover_360px_feed.jpg"
    try:
        feed_canvas = Image.new("RGB", (600, 720), (18, 20, 26))
        fd = ImageDraw.Draw(feed_canvas)
        f_lbl = get_cached_font(font_path, 20)
        card_916 = composed.resize((320, 568), Image.Resampling.LANCZOS)
        card_34 = composed.crop((0, 240, CANVAS_WIDTH, 1680)).resize((180, 240), Image.Resampling.LANCZOS)
        feed_canvas.paste(card_916, (24, 56))
        feed_canvas.paste(card_34, (382, 56))
        fd.text((24, 22), "手机单列全屏预览 (320px)", fill=(226, 232, 240), font=f_lbl)
        fd.text((382, 22), "双列瀑布流预览 (180px)", fill=(250, 204, 21), font=f_lbl)
        fd.text((382, 316), "一眼辨字检查：", fill=(226, 232, 240), font=f_lbl)
        fd.text((382, 348), "不放大能看清大字吗？", fill=(148, 163, 184), font=f_lbl)
        fd.text((382, 380), "主体有没有被切掉？", fill=(148, 163, 184), font=f_lbl)
        feed_canvas.save(feed_preview_path, quality=92)
    except Exception:
        pass

    # 180px 缩略图真实像素对比度与清晰度验收（直接从最终合成像素采样，消灭硬编码黑白 21:1 假检）
    thumb_180 = composed.resize((180, 320))
    tx0 = max(0, min(176, int(thumb_eval_box[0] * 180 / CANVAS_WIDTH)))
    ty0 = max(0, min(316, int(thumb_eval_box[1] * 320 / CANVAS_HEIGHT)))
    tx1_t = max(tx0 + 4, min(180, int(thumb_eval_box[2] * 180 / CANVAS_WIDTH)))
    ty1_t = max(ty0 + 4, min(320, int(thumb_eval_box[3] * 320 / CANVAS_HEIGHT)))
    thumb_box = (tx0, ty0, tx1_t, ty1_t)
    thumb_patch = np.asarray(thumb_180.crop(thumb_box), dtype=np.float32)
    thumb_luma = 0.2126 * thumb_patch[:, :, 0] + 0.7152 * thumb_patch[:, :, 1] + 0.0722 * thumb_patch[:, :, 2]
    thumb_luma_std = float(np.std(thumb_luma))
    # 实测文字墨迹区域前后景相对亮度极端对比 (p96 vs p08)
    lin_l = np.clip(thumb_luma / 255.0, 0.0, 1.0)
    lin_l = np.where(lin_l <= 0.03928, lin_l / 12.92, ((lin_l + 0.055) / 1.055) ** 2.4)
    measured_cover_wcag = round(float((np.percentile(lin_l, 96) + 0.05) / (np.percentile(lin_l, 8) + 0.05)), 2)
    thumb_180_legible_ok = bool(measured_cover_wcag >= 3.8 and thumb_luma_std >= 18.0)

    md_content = "\n".join([
        "# 标题与黄金封面交付方案",
        "",
        f"- **轨道策略**：{'门店轨（强信任与评论咨询转化）' if track=='store' else '博主轨（强好奇与完播留存）'}",
        f"- **黄金封面选帧**：{best_meta.get('detail', '首帧回退')} (综合分 `{best_meta.get('score', 0)}` | 卡片Y={card_y} | 调色同步={'是' if best_meta.get('graded_matched') else '否'} | 180px缩略图={'通过' if thumb_180_legible_ok else '偏低'})",
        f"- **封面主大字**：`{cover_main.replace(chr(10), ' / ')}`",
        f"- **封面副标签**：`{fit_sub}`",
        f"- **双构图封面**：`{cover_path.name}` (9:16 首帧) & `{cover_3x4_path.name}` (3:4 主页网格) & `{ui_preview_path.name}` (平台UI遮罩预览)",
        "",
        "## 备选发布标题（3 选 1，已去 AI 套话）",
        *[f"{i}. {t}" for i, t in enumerate(titles, start=1)],
        "",
        "## 推荐话题标签",
        hashtags,
        "",
    ])
    (pipeline_dir / "09_title_cover.md").write_text(md_content, encoding="utf-8")
    dual_4k_res: Optional[Dict[str, Any]] = None
    if code_cover_4k:
        dual_4k_res = render_dual_4k_code_covers(
            pipeline_dir,
            kicker=fit_sub,
            hero_lines=[cover_main_l1, cover_main_l2],
            title=titles[0][:12] if titles else cover_main_l1,
            palette={
                "bg": "#05070d",
                "ink": "#f1f5f9",
                "sub": "#94a3b8",
                "accent": pal.get("accent_hex", "#5ce1e6"),
                "accent2": "#f59e0b",
                "alert": "#ff6b57",
            },
        )
    has_4k = bool(dual_4k_res and dual_4k_res.get("ok"))
    copy_pack = build_publish_copy_pack(
        pipeline_dir,
        title_seed=titles[0] if titles else hook_clean,
        hook_text=hook_clean,
        sentences=sentences,
        keywords=keywords,
        track=track,
        cover_main=cover_main,
        cover_sub=fit_sub,
        has_4k_covers=has_4k,
    )

    out = {
        "step": "09_title_cover",
        "titles": titles,
        "cover_main": cover_main,
        "cover_sub": fit_sub,
        "hashtags": hashtags,
        "best_frame_meta": best_meta,
        "card_y": card_y,
        "thumb_180_legible_ok": thumb_180_legible_ok,
        "measured_cover_wcag": measured_cover_wcag,
        "thumb_180_contrast_ratio": measured_cover_wcag,
        "person_cutout_applied": person_cutout_applied,
        "cover_jpg": str(cover_path.resolve()),
        "cover_3x4_jpg": str(cover_3x4_path.resolve()),
        "ui_safe_preview_jpg": str(ui_preview_path.resolve()),
        "feed_360px_preview_jpg": str(feed_preview_path.resolve()) if feed_preview_path.is_file() else None,
        "publish_copy_pack_md": str((pipeline_dir / "09_publish_copy_pack.md").resolve()),
        "publish_copy_pack_json": str((pipeline_dir / "09_publish_copy_pack.json").resolve()),
        "dual_4k_covers": dual_4k_res,
        "preferred_title": copy_pack["preferred_title"],
    }
    write_json(pipeline_dir / "09_title_cover.json", out)
    print(f"[step9] 黄金封面(9:16+3:4)与分平台文案包已生成 (选帧分 {best_meta.get('score', 0)}) -> 09_cover.jpg")
    return out


def main() -> None:
    maybe_reexec_in_venv()
    parser = argparse.ArgumentParser(description="Step 9: 黄金封面帧优选与去套话标题")
    parser.add_argument("--pipeline-dir", required=True)
    parser.add_argument("--track", choices=["store", "creator"], default="store")
    parser.add_argument("--style-id", help="绑定风格谱 ID")
    parser.add_argument("--code-cover-4k", action="store_true", help="同时用代码绘制横版 16:9 + 竖版 3:4 双比例 4K 封面")
    args = parser.parse_args()
    run_step9(Path(args.pipeline_dir), track=args.track, style_id=args.style_id, code_cover_4k=args.code_cover_4k)


if __name__ == "__main__":
    main()

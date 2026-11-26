#!/usr/bin/env python3
"""
short-video-studio 专业制片流水线编排器
支持 7 种工作模式：
1. full                : 跑通 Step 1 -> Step 9 -> 渲染成片 -> 导出剪映/HyperFrames -> 22+项白盒+黑盒质检 -> 完工清理
2. lock-preview        : 停在打断#3，输出锁定音轨与低清粗剪预览 (output_preview.mp4)
3. reedit-visuals      : [打断#3 分支A] 严格保持 Step 3 锁定音轨不变（如 01_normalized 已被 tidy 自动按需重建），重排 Step 4-9 + 出片 + 质检
4. relock-voice        : [打断#3 分支B] 回到 Step 2/3 重新锁定音轨，再重排 Step 4-9 + 出片 + 质检
5. render-locked       : 校验 approval_lock 指纹锁后直接按锁定方案终稿渲染、导出与质检
6. code-video          : [入口 3 纯代码制片] 00_code_spec 规约 -> Step 2/3 音轨先锁 -> Chrome HTML/Pillow 渲染分幕 -> Step 1/4-9 -> VERIFY.md
7. knowledge-animation : [入口 3 零实拍知识讲解动画] 单源时间轴 -> 商业字体注入 -> 无头逐帧渲染 -> BGM+拟音/配音混音封装 -> 4K 双比例封面与多平台文案包 -> 归档
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    DEFAULT_FPS,
    EDIT_PROFILES,
    sha256_file,
    EXPORT_CHOICES,
    export_selection,
    SAFE_ZONE,
    SUBTITLE_CENTER_X,
    detect_browser_renderer,
    find_bin,
    fit_text_line,
    load_style_applied,
    load_style_spectrum_entry,
    maybe_reexec_in_venv,
    read_json,
    resolve_workspace_paths,
    run_cmd,
    write_json,
)

if __name__ == "__main__":
    maybe_reexec_in_venv()

from PIL import Image, ImageDraw
from apply_style_spectrum import apply_to_pipeline, load_library, resolve_style_runtime_config
from code_video_spec import generate_verify_template, init_code_spec, validate_code_spec
from compliance_guard import audit_script_compliance, build_asset_license_manifest
from export_hyperframes import export_hyperframes_draft
from export_jianying import export_jianying_draft
from generate_code_broll import (
    generate_demo_media_pack,
    render_spec_scenes_batch,
    resolve_style_palette,
)
from inventory_media import (
    MEDIA_EXTS,
    build_shot_log_dict,
    inventory_directory,
    render_markdown_summary,
)
from knowledge_animator import audit_animation_video, build_review_pack, init_animation_project, mix_animation_audio
from qa_inspector import inspect_video
from raw_intel_ingest import lint_script, render_lint_markdown
from render_mp4 import render_mp4
from source_review import import_sources, write_source_review
from step1_normalize import run_step1
from step2_transcribe import run_step2
from step3_lock_audio import run_step3
from step4_build_edl import run_step4
from step5_subtitles import run_step5
from step6_packaging import run_step6
from step7_color_grade import run_step7
from step8_mix_audio import run_step8
from step9_title_cover import build_publish_copy_pack, render_dual_4k_code_covers, run_step9
from workflow_guard import compute_plan_digest, generate_action_strips, record_milestone, render_progress_card, tidy_workspace, verify_lock


def _run_script_prelint(
    script_path: Path,
    pipeline_dir: Path,
    raw_intel: Optional[Dict[str, Any]] = None,
) -> None:
    raw = read_json(script_path)
    items = raw.get("sentences") or raw.get("segments") or [] if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return
    intel = raw_intel or {"utterance_count": 0, "verified_by_real_users": False, "pain_keywords": [], "proof_assets": []}
    lint_res = lint_script(items, raw_intel=intel)
    (pipeline_dir / "00_script_lint.md").write_text(render_lint_markdown(lint_res, intel), encoding="utf-8")
    if lint_res["error_count"] > 0 or lint_res["warn_count"] > 0:
        print(
            f"[pre-lint] 口语脚本体检提示: Error={lint_res['error_count']}, "
            f"Warn={lint_res['warn_count']} -> {pipeline_dir / '00_script_lint.md'}"
        )


def _generate_hook_variants(pipeline_dir: Path, count: int) -> Optional[Path]:
    """根据已生成的标题与成片，产出多版本真 3 秒开篇视频钩子变体（零模板词污染、全对齐安全区）。"""
    n_var = max(2, min(3, int(count)))
    cov_p = pipeline_dir / "09_title_cover.json"
    if not cov_p.is_file():
        return None
    cov = read_json(cov_p)
    titles = [str(t).strip() for t in (cov.get("titles") or []) if str(t).strip()]
    base_jpg = Path(cov.get("cover_jpg") or (pipeline_dir / "09_cover.jpg"))
    subs = read_json(pipeline_dir / "05_subtitles.json") if (pipeline_dir / "05_subtitles.json").exists() else {}
    font_path = subs.get("font_path")
    final_mp4 = pipeline_dir / "output_final.mp4"
    ffmpeg = find_bin("ffmpeg")

    titles = list(dict.fromkeys(title[:18] for title in titles)) or [str(cov.get("cover_main") or "")[:18]]
    sub_tpl_style = (subs.get("template_config") or subs.get("template") or {}) if isinstance(subs, dict) else {}
    bg_val = str(sub_tpl_style.get("bg_box_color") or sub_tpl_style.get("bg_box") or "").strip().lower()
    use_borderless = bg_val in ("", "none", "false", "transparent") or bg_val.endswith("00")
    variants: List[Dict[str, Any]] = []
    for idx, raw_t in enumerate(titles[:n_var]):
        clean_headline = raw_t.replace("\n", " ").strip()[:18]
        out_img = pipeline_dir / f"09_cover_v{idx + 1}.jpg"
        out_vid = pipeline_dir / f"09_hook_v{idx + 1}.mp4"

        if base_jpg.is_file():
            with Image.open(base_jpg) as im:
                canvas = im.convert("RGBA")
                draw = ImageDraw.Draw(canvas)
                card_y = int(cov.get("card_y", 260))
                badge_y0 = max(SAFE_ZONE["y_min"] + 16, card_y - 72 if card_y > 320 else card_y + 348)
                badge_y1 = min(1140, badge_y0 + 62)
                max_w = min(640, SAFE_ZONE["x_max"] - SAFE_ZONE["x_min"] - 40)
                fnt, fitted = fit_text_line(draw, clean_headline, font_path, max_width=max_w - 40, max_size=34 if use_borderless else 30, min_size=22)
                if use_borderless:
                    cy_t = (badge_y0 + badge_y1) // 2
                    draw.text((SUBTITLE_CENTER_X, cy_t), fitted, font=fnt, fill=(255, 224, 51, 255), anchor="mm", stroke_width=5, stroke_fill=(12, 12, 12, 245))
                else:
                    bb = draw.textbbox((0, 0), fitted, font=fnt)
                    bw = min(max_w, max(240, int(bb[2] - bb[0]) + 44))
                    bx0 = max(SAFE_ZONE["x_min"] + 10, SUBTITLE_CENTER_X - bw // 2)
                    draw.rounded_rectangle([(bx0, badge_y0), (bx0 + bw, badge_y1)], radius=14, fill=(18, 24, 38, 224), outline=(250, 204, 21, 220), width=2)
                    draw.text((bx0 + bw // 2, (badge_y0 + badge_y1) // 2), fitted, font=fnt, fill=(255, 255, 255, 255), anchor="mm")
                canvas.convert("RGB").save(out_img, quality=92)

        # 生成真实可播放的 3 秒开篇标题对比 MP4
        vid_ok = False
        if ffmpeg and final_mp4.is_file():
            ov_png = pipeline_dir / f"_tmp_hook_v{idx + 1}.png"
            ov_im = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (0, 0, 0, 0))
            ov_d = ImageDraw.Draw(ov_im)
            max_w = min(640, SAFE_ZONE["x_max"] - SAFE_ZONE["x_min"] - 40)
            fnt, fitted = fit_text_line(ov_d, clean_headline, font_path, max_width=max_w - 40, max_size=42 if use_borderless else 34, min_size=22)
            by0, by1 = SAFE_ZONE["y_min"] + 20, SAFE_ZONE["y_min"] + 96
            if use_borderless:
                ov_d.text((SUBTITLE_CENTER_X, (by0 + by1) // 2), fitted, font=fnt, fill=(255, 224, 51, 255), anchor="mm", stroke_width=6, stroke_fill=(12, 12, 12, 250))
            else:
                bb = ov_d.textbbox((0, 0), fitted, font=fnt)
                bw = min(max_w, max(260, int(bb[2] - bb[0]) + 48))
                bx0 = max(SAFE_ZONE["x_min"] + 10, SUBTITLE_CENTER_X - bw // 2)
                ov_d.rounded_rectangle([(bx0, by0), (bx0 + bw, by1)], radius=16, fill=(15, 23, 42, 226), outline=(250, 204, 21, 230), width=2)
                ov_d.text((bx0 + bw // 2, (by0 + by1) // 2), fitted, font=fnt, fill=(250, 204, 21, 255), anchor="mm")
            ov_im.save(ov_png)
            try:
                result = run_cmd([
                    ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                    "-t", "3.0", "-i", str(final_mp4),
                    "-i", str(ov_png),
                    "-filter_complex", "[0:v][1:v]overlay=0:0:enable='between(t,0,3.0)'[v]",
                    "-map", "[v]", "-map", "0:a?",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "19", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "128k", "-t", "3.0",
                    str(out_vid),
                ], check=False)
                vid_ok = result.returncode == 0 and out_vid.is_file() and out_vid.stat().st_size > 0
            finally:
                ov_png.unlink(missing_ok=True)

        variants.append({
            "variant_id": f"hook_v{idx + 1}",
            "changed_variable": "opening_title_overlay",
            "headline": raw_t,
            "cover_jpg": str(out_img.resolve()) if out_img.is_file() else None,
            "video_mp4": str(out_vid.resolve()) if vid_ok else None,
            "duration_sec": 3.0 if vid_ok else 0.0,
        })

    out_json = pipeline_dir / "09_hook_variants.json"
    src_sha = sha256_file(final_mp4) if final_mp4.is_file() else ""
    write_json(out_json, {"kind": "opening_title_overlay_preview", "source_video_sha256": src_sha, "count": len(variants), "variants": variants})
    return out_json


def write_decisions_made(pipeline_dir: Path, track: str) -> Path:
    """生成《我替你做的决定》（100% 大白话、零专业黑话，方便一句话直接修改）。"""
    mf = read_json(pipeline_dir / "01_manifest.json") if (pipeline_dir / "01_manifest.json").exists() else {}
    ae = read_json(pipeline_dir / "03_audio_events.json")
    edl = read_json(pipeline_dir / "04_edl.json")
    sub = read_json(pipeline_dir / "05_subtitles.json")
    pkg = read_json(pipeline_dir / "06_packaging.json")
    col = read_json(pipeline_dir / "07_color_plan.json")
    cov = read_json(pipeline_dir / "09_title_cover.json") if (pipeline_dir / "09_title_cover.json").exists() else {}
    qa = read_json(pipeline_dir / "10_qa_report.json") if (pipeline_dir / "10_qa_report.json").exists() else {}
    jy = qa.get("deliverables", {}).get("jianying", {})
    hf = qa.get("deliverables", {}).get("hyperframes", {})

    hdr_cnt = int(mf.get("hdr_tonemapped_count", 0))
    rt_src = "从原片里提取的真实环境底声" if ae.get("room_tone_source") == "extracted_real" else "轻微柔和的环境垫底声"
    p_range = ae.get("pause_range_sec", [ae.get("pause_duration_sec", 0.2), ae.get("pause_duration_sec", 0.2)])
    best_cov = cov.get("best_frame_meta", {})
    dual_bgm_note = "（开场 4 秒用一段情绪铺垫，正文自动丝滑切入主旋律）" if ae.get("dual_bgm_used") else ""

    def _status_zh(st: str) -> str:
        mp = {
            "PASS": "已生成且检查通过",
            "APPROVED": "已通过全部检查并人工确认",
            "MACHINE_PASS_PENDING_HUMAN": "自动检查全过，等你确认一眼",
            "REVIEW_REQUIRED": "自动检查全过，等你核对人工项",
            "NOT_REQUESTED": "本次未要求导出",
            "SKIPPED_UNAVAILABLE": "环境缺依赖已跳过",
            "FAIL": "检查未通过（详见体检表）",
            "REJECTED": "有项未通过，建议改完再发",
        }
        return mp.get(str(st or ""), "待核对")

    lines = [
        "# 我替你做的决定（全程大白话说明 + 一句话修改指南）",
        "",
        "为了少打扰你，除了开头定选题、选素材和听一遍声音节奏外，剩下的画面、字幕、配乐、调色细节都已按成熟门店/账号成片标准帮你配齐：",
        "",
        "| 环节 | 我替你做的安排 | 想改的话直接对我说 |",
        "| :--- | :--- | :--- |",
        f"| **视频定位** | {'帮实体店拉本地客人（同城获客）' if track == 'store' else '帮个人账号涨粉引流'} | “改按同城门店风格 / 个人博主风格重出” |",
        f"| **手机高动态色彩还原** | 自动把 `{hdr_cnt}` 条偏灰或过亮的手机素材调回自然耐看的颜色 | “画面再通透一点 / 柔和一点” |",
        f"| **背景音乐与踩点** | 配乐 `{Path(ae['bgm']['file']).name}`{dual_bgm_note}，开头第一句话正好落在重拍上 | “换一首更轻快 / 更舒缓的背景音乐” |",
        f"| **气口停顿与不生硬衔接** | 句子之间留出 `{p_range[0]}秒–{p_range[1]}秒` 自然呼吸停顿，垫入{rt_src}，听不出硬剪痕迹 | “说话节奏再紧凑一点 / 慢一点” |",
        f"| **声画顺滑切换与景别变化** | 做了 `{edl.get('j_cut_applied_count', 0)}` 处“先听到声音再切画面”的顺滑转场，并在 `{edl.get('punch_in_count', 0)}` 处重点话时轻轻推近镜头 | “切镜头再干脆一点”或“关闭镜头轻轻推近” |",
        f"| **居中字幕与避让脸部** | 用了 `{sub['template_name']}` 样式，免费商用字体 `{Path(sub['font_path']).name if sub.get('font_path') else '默认字体'}`，所有字幕正中对齐、自动躲开人脸和点赞按钮 | “换一种字幕颜色 / 大小” |",
        f"| **花字提示与音效节奏** | 加了 {pkg['budget']['used_sfx_cues']} 处点睛小音效、{pkg['budget']['used_visual_elements']} 处重点花字提醒（克制不吵眼） | “花字再少一点 / 再活泼一点” |",
        f"| **人物肤色保护调色** | 统一了不同镜头的亮度颜色，并护住人物自然气色（调色浓度 `{int(round(col.get('lut_strength', 0.62)*100))}%`） | “颜色再鲜亮一点 / 清淡一点” |",
        f"| **人声清晰与自动压低音乐** | 人声响度已调到平台最舒服的标准，说话时背景音乐自动变小让位，人声清晰不费耳 | “背景音乐再小声一点 / 大声一点” |",
        f"| **封面挑帧与主页适配** | 自动挑了最清晰、表情自然的一帧做封面（综合分 `{best_cov.get('score', 0)}`），同时配好竖版首帧和 3:4 主页小图 | “换一个画面做封面 / 改封面大字” |",
        f"| **出厂全套自动检查** | 通过 `{qa.get('pass_count', 0)}/{qa.get('total_checks', 0)}` 项（当前状态：{_status_zh(qa.get('approval_status', ''))}） | 打开 `10_qa_report.md` 或 `10_blind_review_pack.md` 查看 |",
        f"| **可二次编辑工程** | 高清成片 `output_final.mp4` + 剪映工程（{_status_zh(jy.get('status', ''))}） + 网页时间线工程（{_status_zh(hf.get('status', ''))}） | “帮我导出剪映工程 / 调整某一段” |",
        "",
    ]
    out_md = pipeline_dir / "decisions_made.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")
    return out_md


def write_review_player_html(pipeline_dir: Path) -> Path:
    """生成纯静态零后端离线时间线打点审片器 review_player.html（纯 DOM 操作防 XSS，读取真实 fps）。"""
    edl = read_json(pipeline_dir / "04_edl.json") if (pipeline_dir / "04_edl.json").exists() else {}
    fps = int(edl.get("fps") or DEFAULT_FPS)
    html_str = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>离线时间线打点审片器 · short-video-studio</title>
<style>
  body {{ font-family: -apple-system, sans-serif; background: #0b0f17; color: #f8fafc; margin: 20px; display: flex; gap: 24px; flex-wrap: wrap; }}
  video {{ width: 340px; border-radius: 14px; border: 1px solid #334155; background: #000; }}
  .panel {{ flex: 1; min-width: 300px; background: #121926; padding: 18px; border-radius: 14px; border: 1px solid #25344d; }}
  button {{ background: #facc15; color: #0f172a; border: none; padding: 8px 14px; border-radius: 8px; font-weight: 700; cursor: pointer; margin-right: 8px; }}
  input {{ width: 70%; padding: 8px; border-radius: 8px; border: 1px solid #334155; background: #0b0f17; color: #fff; }}
  ul {{ list-style: none; padding: 0; margin-top: 14px; }}
  li {{ padding: 8px 10px; background: #1e293b; border-radius: 8px; margin-bottom: 6px; cursor: pointer; }}
</style>
</head>
<body>
  <video id="v" controls playsinline src="output_final.mp4"></video>
  <div class="panel">
    <h3>成片离线时间线批注（按 M 键抓取秒数 · {fps}fps）</h3>
    <div>
      <input id="note" placeholder="输入修改意见，如：第4秒字幕挡脸 / 这句再快一点" />
      <button type="button" onclick="addMark()">+ 在当前帧打点</button>
      <button type="button" onclick="exportJson()" style="background:#38bdf8;">导出 annotations.json</button>
    </div>
    <ul id="list"></ul>
  </div>
<script>
  const FPS = {fps};
  const v = document.getElementById('v');
  const marks = [];
  function render() {{
    const ul = document.getElementById('list');
    ul.textContent = '';
    marks.forEach((m) => {{
      const li = document.createElement('li');
      li.addEventListener('click', () => {{ v.currentTime = m.time_sec; }});
      const b = document.createElement('b');
      b.textContent = '@' + m.time_sec.toFixed(2) + 's (f' + m.frame + ')';
      li.appendChild(b);
      li.appendChild(document.createTextNode(' — ' + m.note));
      ul.appendChild(li);
    }});
  }}
  function addMark() {{
    const t = Number((v.currentTime || 0).toFixed(2));
    const el = document.getElementById('note');
    const note = el.value.trim() || '此处需要微调';
    marks.push({{ time_sec: t, frame: Math.round(t * FPS), note }});
    marks.sort((a, b) => a.time_sec - b.time_sec);
    el.value = '';
    render();
  }}
  function exportJson() {{
    const blob = new Blob([JSON.stringify(marks, null, 2)], {{ type: 'application/json' }});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'annotations.json';
    a.click();
  }}
  window.addEventListener('keydown', (e) => {{
    if ((e.key === 'm' || e.key === 'M') && document.activeElement.tagName !== 'INPUT') {{
      document.getElementById('note').focus();
    }}
  }});
</script>
</body>
</html>
"""
    p = pipeline_dir / "review_player.html"
    p.write_text(html_str, encoding="utf-8")
    return p


def write_delivery_summary(
    pipeline_dir: Path,
    ws: Dict[str, Any],
    track: str,
    qa_report: Dict[str, Any],
) -> Path:
    """输出 11_delivery_summary.md（复用 09_title_cover.json 真实标题，绝不再造另一套）。"""
    cov = read_json(pipeline_dir / "09_title_cover.json") if (pipeline_dir / "09_title_cover.json").exists() else {}
    titles = list(cov.get("titles") or [])
    if not titles:
        ae = read_json(pipeline_dir / "03_audio_events.json") if (pipeline_dir / "03_audio_events.json").exists() else {}
        sents = ae.get("sentences") or []
        core = str(sents[0].get("text", "核心分享"))[:16] if sents else "核心分享"
        titles = [core]

    hv_p = pipeline_dir / "09_hook_variants.json"
    hv_note = ""
    if hv_p.is_file():
        hv = read_json(hv_p)
        hv_note = f"\n- **多版本开头标题预览**：已生成 {hv.get('count', 0)} 版开篇样片（`09_hook_variants.json` / `09_cover_v1..jpg`）"

    pend_manual = list(qa_report.get("required_manual_checks") or [])
    rev_flags = " ".join(f"--reviewed {m}" for m in pend_manual)
    approve_cmd = (
        f"python3 scripts/workflow_guard.py approve-final --pipeline-dir \"{pipeline_dir}\" "
        + (f"{rev_flags} " if rev_flags else "")
        + "--note \"已核对成片与人工检查项，同意发布\""
    )
    status_label = {
        "APPROVED": "已通过全部检查并人工确认",
        "MACHINE_PASS_PENDING_HUMAN": "自动检查全部通过，等你确认一眼即可发布",
        "REVIEW_REQUIRED": "自动检查通过，请核对人工复查项后确认",
        "REJECTED": "存在未通过检查项，建议修完再发",
    }.get(str(qa_report.get("approval_status", "")), "待确认")

    _deliv_st_cn = {
        "PASS": "已导出并校验通过",
        "FAIL": "导出或校验未通过",
        "NOT_REQUESTED": "本次未选择导出",
        "SKIPPED_UNAVAILABLE": "环境未就绪已跳过",
        "PENDING_REVIEW": "待人工导入看一眼",
        "PENDING_VERIFICATION": "待在剪映里打开确认",
    }
    _target_cn = {"jianying": "剪映可编辑工程", "hyperframes": "网页可编辑工程 (HyperFrames)"}

    lines = [
        f"# 成品交付清单 · 账号 `{ws.get('account_slug', 'default')}` · 项目 `{ws.get('project_id', pipeline_dir.parent.name)}`",
        "",
        f"- **隔离加工目录**：`{ws.get('project_dir', pipeline_dir.parent)}`（你的原素材目录 `{ws.get('raw_dir', '')}` 全程只读未改动）",
        f"- **出厂自动检查**：通过 `{qa_report.get('pass_count', 0)}/{qa_report.get('total_checks', 0)}` 项 · 状态：{status_label}{hv_note}",
        "",
        "## 一、 最终交付文件（已同步整理到 `out/` 目录）",
        "- 高清成片：`out/output_final.mp4`",
        "- 竖版、主页封面与手机小图预览：`out/09_cover.jpg` / `out/09_cover_3x4.jpg` / `out/09_cover_360px_feed.jpg`",
        *(["- 分平台发布文案包：`out/09_publish_copy_pack.md`（含抖音/视频号/小红书/B站独立标题与正文）"] if (pipeline_dir / "09_publish_copy_pack.md").is_file() else []),
        *(["- 纯净外挂字幕与节奏自检：`out/05_subtitles.srt` · `out/05_subtitle_check.txt`"] if (pipeline_dir / "05_subtitles.srt").is_file() else []),
        "- 一页盲审取证包：`out/10_blind_review_pack.md`（30 秒快速验片用）",
        "- 开头与切点连拍图：`out/10_action_strips.jpg`",
        "- 纯声音盲听版：`out/03_blind_audio.m4a`",
        "- 素材缩略总览图：`out/00_contact_sheet.jpg`",
        "- 项目进度看板：`out/00_进度看板.md`",
        "- 广告法合规与商用授权清单：`out/00_compliance_report.md` · `out/asset_license_manifest.json`",
        "- 浏览器离线打点审片页：`out/review_player.html`",
        *[
            f"- {_target_cn.get(target, target)}：{_deliv_st_cn.get(str(result.get('status', '')), str(result.get('status', '')))}" +
            (f"（{_deliv_st_cn.get(str(result.get('host_import', '')), str(result.get('host_import', '')))}）" if "host_import" in result else "")
            for target, result in qa_report["deliverables"].items() if target != "mp4"
        ],
        *(
            ["- 图解动画规约与核验单：`out/00_code_spec.json` · `out/SPEC.md` · `out/STRUCTURE.md` · `out/VERIFY.md`"]
            if (pipeline_dir / "00_code_spec.json").is_file()
            else []
        ),
        "",
        "## 二、 推荐发布标题（与封面方案完全同步）",
        *[f"{i}. {t}" for i, t in enumerate(titles, start=1)],
        "",
        "## 三、 人工看片确认签字",
        "- 详细配置说明与修改口令见 `decisions_made.md`。",
        f"  `{approve_cmd}`",
        "",
        "## 四、 发完 48 小时回来复盘",
        "- 把后台看到的播放量、3 秒留住人数、看完人数和私信/咨询数发给我即可自动入库（或直接传 JSON 快照给 `content_log_review.py`）。",
        "",
    ]
    out_md = pipeline_dir / "11_delivery_summary.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")
    return out_md


def _ensure_reedit_dependencies(
    pipeline_dir: Path,
    track: str = "store",
    bgm_p: Optional[Path] = None,
    pause_sec: float = 0.20,
    account_profile: Optional[Dict[str, Any]] = None,
    preserve_locked_audio: bool = False,
) -> None:
    """在 tidy 清理过临时文件后若需二次改画或重渲染，自动检查并无损重建缺失依赖。"""
    man_p = pipeline_dir / "01_manifest.json"
    if man_p.is_file():
        man = read_json(man_p)
        items = man.get("items") or []
        missing = [it for it in items if it.get("normalized_mp4") and not Path(it["normalized_mp4"]).is_file()]
        if missing:
            src_paths: List[Path] = []
            seen: set[str] = set()
            for it in items:
                sp = str(it.get("source_path") or "")
                if sp and sp not in seen and Path(sp).is_file():
                    seen.add(sp)
                    src_paths.append(Path(sp))
            if not src_paths:
                is_code_proj = (pipeline_dir / "00_code_spec.json").is_file() or any(
                    bool(it.get("source_is_code_scene")) for it in items
                )
                if is_code_proj:
                    print("[pipeline] 检测到纯代码项目 01_code_scenes 已清理，正按 00_code_spec 与锁定音轨自愈重渲代码分幕...")
                    re_scenes_dir = _render_code_scenes_from_spec(
                        pipeline_dir=pipeline_dir,
                        track=track,
                        active_style_id=load_style_applied(pipeline_dir),
                        code_html_p=None,
                        code_backend="auto",
                    )
                    src_paths = [re_scenes_dir]
                else:
                    raise FileNotFoundError("01_normalized 已被清理且找不到原始 source_path 源文件，无法重建。")
            print(f"[pipeline] 检测到 {len(missing)} 条已清理的 01_normalized，正从源素材按需重建...")
            run_step1(src_paths, pipeline_dir)

    ae_p = pipeline_dir / "03_audio_events.json"
    if ae_p.is_file():
        ae = read_json(ae_p)
        lv = Path(str(ae.get("locked_voice_wav") or (pipeline_dir / "03_locked_voice.wav")))
        lb = Path(str(ae.get("locked_bgm_wav") or (pipeline_dir / "03_locked_bgm.wav")))
        if not lv.is_file() or not lb.is_file():
            if preserve_locked_audio:
                raise FileNotFoundError("锁定分轨缺失。请恢复锁轨文件或明确选择 relock-voice。")
            print("[pipeline] 检测到锁定音轨 WAV 缺失，正按 02_transcript 自动重建 Step 3 锁轨...")
            bgm_cand = bgm_p
            if bgm_cand is None and ae.get("bgm", {}).get("file") and Path(ae["bgm"]["file"]).is_file():
                bgm_cand = Path(ae["bgm"]["file"])
            run_step3(
                pipeline_dir,
                track=track,
                bgm_path=bgm_cand,
                pause_sec=float(ae.get("pause_duration_sec", pause_sec)),
                account_profile=account_profile,
            )


def _compact_code_title(raw_t: str, limit: int = 12) -> str:
    import re
    s = re.sub(r"[，。！？、；：“”‘’（）().,!?;:\s]+", "", str(raw_t or "")).strip()
    return (s[:limit] or "核心真相").strip()


def _render_code_scenes_from_spec(
    pipeline_dir: Path,
    track: str = "store",
    active_style_id: Optional[str] = None,
    code_html_p: Optional[Path] = None,
    code_backend: str = "auto",
) -> Path:
    """根据已落盘的 00_code_spec.json 与锁定音轨批量渲染 01_code_scenes（支持自定义 sections 保留与 tidy 后自愈重渲）。"""
    import re
    import subprocess

    spec_p = pipeline_dir / "00_code_spec.json"
    spec = read_json(spec_p) if spec_p.is_file() else {}
    ae_p = pipeline_dir / "03_audio_events.json"
    tr_p = pipeline_dir / "02_transcript.json"
    ae = read_json(ae_p) if ae_p.is_file() else {}
    tr = read_json(tr_p) if tr_p.is_file() else {}

    eff_style = active_style_id or str(spec.get("style_id") or ("style_14" if track == "store" else "style_11"))
    locked_dur = max(3.0, float(ae.get("total_duration_sec", ae.get("locked_duration_sec", (spec.get("format") or {}).get("target_duration_sec", 12.0)))))
    sentences = ae.get("sentences") or tr.get("segments") or tr.get("sentences") or []
    sections = spec.get("sections") or []
    has_custom_sections = bool(spec.get("_user_custom_sections"))

    valid_assets = [str(a.get("path")) for a in (spec.get("assets") or []) if a.get("exists") and a.get("path")]

    scenes_dir = pipeline_dir / "01_code_scenes"
    if scenes_dir.exists():
        shutil.rmtree(scenes_dir, ignore_errors=True)
    scenes_dir.mkdir(parents=True, exist_ok=True)
    scene_meta: Dict[str, Any] = {}
    modes_cycle = ["kinetic_text", "data_chart", "flow_diagram", "versus", "proportion", "day_night", "chips"]

    if not code_html_p and spec.get("code_html_path"):
        cand_ch = Path(str(spec["code_html_path"]))
        if cand_ch.exists():
            code_html_p = cand_ch

    if code_html_p and code_html_p.exists():
        html_dir = code_html_p.parent if code_html_p.is_file() else code_html_p
        entry_page = code_html_p.name if code_html_p.is_file() else "index.html"
        br = detect_browser_renderer()
        if not br.get("available"):
            raise RuntimeError("传入 --code-html 但当前未就绪无头浏览器桥接，请先运行 check_and_setup.py --init-browser")
        ffmpeg = find_bin("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("需要 ffmpeg 切分 --code-html 渲染结果")
        master_mp4 = scenes_dir / "_master_code.mp4"
        cap_fps = int((spec.get("format") or {}).get("fps", DEFAULT_FPS))
        master_dur = round(locked_dur + 1.0, 2)
        frames_tot = max(30, int(round(master_dur * cap_fps)))
        cap_env = dict(os.environ)
        cap_env["FFMPEG_BIN"] = ffmpeg
        res_cap = subprocess.run([
            str(br["node_bin"]),
            str(Path(__file__).resolve().parent / "capture_html_video.mjs"),
            str(html_dir),
            "--page", entry_page,
            "--fps", str(cap_fps),
            "--frames", str(frames_tot),
            "--size", f"{CANVAS_WIDTH}x{CANVAS_HEIGHT}",
            "--jpeg",
            "--out", str(master_mp4),
        ], capture_output=True, text=True, env=cap_env)
        if res_cap.returncode != 0 or not master_mp4.is_file():
            raise RuntimeError(f"--code-html 确定性捕获失败: {(res_cap.stderr or res_cap.stdout)[:300]}")

        n_slices = max(4, min(8, len(sentences) or 4))
        slice_span = master_dur / float(n_slices)
        for si in range(n_slices):
            t0 = round(max(0.0, si * slice_span), 3)
            seg_len = max(3.2, slice_span + 0.9)
            t_clip = min(t0, max(0.0, master_dur - seg_len))
            fn = f"code_scene_{si+1:02d}.mp4"
            out_s = scenes_dir / fn
            run_cmd([
                ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-ss", f"{t_clip:.3f}", "-i", str(master_mp4),
                "-t", f"{seg_len:.3f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an",
                str(out_s),
            ])
            s_ref = sentences[min(si, len(sentences) - 1)] if sentences else {}
            scene_meta[fn] = {
                "role": "b_roll",
                "semantic_tags": list(s_ref.get("keywords") or []) + [str(spec.get("title") or "主题")],
                "scene_group": f"code_html_sec_{si+1:02d}",
                "sharpness_score": 85.0,
                "stability_score": 1.0,
            }
        master_mp4.unlink(missing_ok=True)
    else:
        unit_srcs: List[Dict[str, Any]] = []
        if has_custom_sections and sections:
            # 严格保留用户 --code-spec 中自定义的每一幕 items / mode / register / accent_hex / bg_hex / clip_asset
            for si, sec in enumerate(sections[:8]):
                s_ref = sentences[min(si, len(sentences) - 1)] if sentences else {}
                st_txt = _compact_code_title(sec.get("on_screen_text") or sec.get("title") or sec.get("name") or spec.get("title") or "", 12)
                kws = list(sec.get("keywords") or s_ref.get("keywords") or []) + [st_txt]
                unit_srcs.append({
                    "mode": str(sec.get("mode") or modes_cycle[si % len(modes_cycle)]),
                    "on_screen_text": st_txt,
                    "items": sec.get("items") or [{"label": st_txt, "subtitle": str(sec.get("visual_state") or "程序确定性渲染")[:20]}],
                    "duration_sec": max(3.6, float(sec.get("duration_sec", 3.2)) + 1.2),
                    "keywords": kws,
                    "register": sec.get("register"),
                    "accent_hex": sec.get("accent_hex"),
                    "bg_hex": sec.get("bg_hex"),
                    "clip_asset": sec.get("clip_asset") or (valid_assets[si] if si < len(valid_assets) else None),
                    "bg_shift": (si % 2 == 1) and not sec.get("bg_hex"),
                })
            # 若用户自定义少于 4 幕，在不破坏原自定义幕的前提下追加衍生子幕以保障前 3s 快切与切点跳变
            while len(unit_srcs) < 4:
                idx_extra = len(unit_srcs)
                base_u = dict(unit_srcs[idx_extra % len(sections)])
                s_ref = sentences[min(idx_extra, len(sentences) - 1)] if sentences else {}
                base_u["mode"] = modes_cycle[idx_extra % len(modes_cycle)]
                if s_ref.get("text"):
                    base_u["on_screen_text"] = _compact_code_title(s_ref.get("text"), 10)
                    base_u["keywords"] = list(s_ref.get("keywords") or []) + [base_u["on_screen_text"]]
                base_u["bg_shift"] = (idx_extra % 2 == 1)
                unit_srcs.append(base_u)
        elif len(sentences) >= 4:
            for si, sent in enumerate(sentences[:8]):
                sec_ref = sections[min(si * len(sections) // max(1, len(sentences[:8])), len(sections) - 1)] if sections else {}
                st_txt = _compact_code_title(sent.get("show") or sent.get("text") or sec_ref.get("on_screen_text") or spec.get("title") or "", 10)
                nums = [int(n) for n in re.findall(r"\b\d{1,3}\b", str(sent.get("text") or ""))][:3]
                kws = [str(k) for k in (sent.get("keywords") or [])]
                mode_pick = str(sec_ref.get("mode") or modes_cycle[si % len(modes_cycle)]) if si < len(sections) else modes_cycle[si % len(modes_cycle)]
                if mode_pick in ("data_chart", "proportion") and not nums:
                    nums = [68 - (si % 3) * 12, 32 + (si % 3) * 12]
                if mode_pick in ("data_chart", "proportion"):
                    items_s = [{"label": kws[k] if k < len(kws) else f"核心指标{k+1}", "value": nums[k % len(nums)]} for k in range(max(2, min(3, len(nums))))]
                elif mode_pick == "versus":
                    items_s = [{"label": kws[0] if kws else st_txt[:6], "subtitle": "真实实测对比", "positive": True}, {"label": "常规误区", "subtitle": "信息不透明", "positive": False}]
                elif mode_pick == "day_night":
                    items_s = [{"label": kws[0] if kws else "白昼现切备料", "subtitle": str(sent.get("text") or "")[:18]}, {"label": kws[1] if len(kws) > 1 else "夜间炭火出炉", "subtitle": "全时段品质如一"}]
                else:
                    items_s = [{"label": st_txt, "subtitle": str(sent.get("text") or "")[:18]}, {"label": kws[0] if kws else "关键要点", "subtitle": str(sec_ref.get("visual_state") or "高清数据拆解")[:18]}]
                sent_d = max(2.0, float(sent.get("end_sec", 0.0)) - float(sent.get("start_sec", 0.0)))
                unit_srcs.append({
                    "mode": mode_pick,
                    "on_screen_text": st_txt,
                    "items": items_s,
                    "duration_sec": max(3.6, sent_d + 1.4),
                    "keywords": kws + [st_txt],
                    "clip_asset": valid_assets[si] if si < len(valid_assets) else None,
                    "bg_shift": si % 2 == 1,
                })
        else:
            src_secs = list(sections)
            while len(src_secs) < 4:
                base_s = dict(src_secs[len(src_secs) % max(1, len(sections))] if sections else {"mode": "kinetic_text", "on_screen_text": spec.get("title", "要点"), "duration_sec": 3.5})
                base_s["mode"] = modes_cycle[len(src_secs) % len(modes_cycle)]
                src_secs.append(base_s)
            for si, sec in enumerate(src_secs[:8]):
                st_txt = _compact_code_title(sec.get("on_screen_text") or sec.get("name") or spec.get("title") or "", 10)
                unit_srcs.append({
                    "mode": str(sec.get("mode") or modes_cycle[si % len(modes_cycle)]),
                    "on_screen_text": st_txt,
                    "items": sec.get("items") or [{"label": st_txt, "subtitle": str(sec.get("visual_state") or "")[:18]}],
                    "duration_sec": max(3.6, float(sec.get("duration_sec", 3.2)) + 1.2),
                    "keywords": [st_txt, str(spec.get("title") or "")],
                    "clip_asset": sec.get("clip_asset") or (valid_assets[si] if si < len(valid_assets) else None),
                    "bg_shift": si % 2 == 1,
                })

        per_net = lambda u: max(0.0, float(u["duration_sec"]) - 0.80)
        tot_net = sum(per_net(u) for u in unit_srcs)
        if tot_net < locked_dur * 1.28:
            add_each = (locked_dur * 1.32 - tot_net) / max(1, len(unit_srcs))
            for u in unit_srcs:
                u["duration_sec"] = round(u["duration_sec"] + add_each, 2)

        pal_base = resolve_style_palette(eff_style, track=track)
        batch_tasks: List[Tuple[Dict[str, Any], Path]] = []
        for si, u in enumerate(unit_srcs):
            fn = f"code_scene_{si+1:02d}.mp4"
            out_mp4 = scenes_dir / fn
            scene_cfg = dict(u)
            if u.get("bg_shift") and not scene_cfg.get("bg_hex"):
                if pal_base.get("is_light"):
                    scene_cfg["bg_hex"] = str(pal_base.get("grid_hex") or "#ECE6DC")
                else:
                    scene_cfg["bg_hex"] = "#162032" if str(pal_base.get("bg_hex", "")).lower().startswith("#0") else "#1E293B"
            batch_tasks.append((scene_cfg, out_mp4))
            scene_meta[fn] = {
                "role": "b_roll",
                "semantic_tags": u.get("keywords") or [str(spec.get("title") or "")],
                "scene_group": f"code_sec_{si+1:02d}",
                "sharpness_score": 85.0,
                "stability_score": 1.0,
            }

        render_spec_scenes_batch(batch_tasks, style_id=eff_style, track=track, backend=code_backend)

    write_json(scenes_dir / "scene_meta.json", scene_meta)
    # 同步生成 00_contact_sheet.jpg，确保三入口交付物一致闭合
    contact_jpg = pipeline_dir / "00_contact_sheet.jpg"
    if not contact_jpg.is_file():
        try:
            inv = inventory_directory(scenes_dir, track, contact_sheet_path=contact_jpg)
            write_json(pipeline_dir / "00_inventory.json", inv)
            write_json(pipeline_dir / "00_shot_log.json", build_shot_log_dict(inv))
        except Exception:
            pass
    print(f"[code-video] 已批量渲染 {len(scene_meta)} 幕程序场景 ({code_backend}) -> {scenes_dir}")
    return scenes_dir


def _run_code_video_branch(
    pipeline_dir: Path,
    track: str,
    script_p: Optional[Path],
    code_spec_p: Optional[Path],
    code_html_p: Optional[Path],
    code_backend: str,
    active_style_id: Optional[str],
    bgm_p: Optional[Path],
    pause_sec: Optional[float],
    account_profile: Optional[Dict[str, Any]],
    whitelist_path: Optional[Path],
    store_anchor: Optional[str],
    dialect: str = "mandarin",
    whisper_model: Optional[str] = None,
) -> Path:
    """入口 3 纯代码制片工作流：00_code_spec 规约 -> 音轨先锁 -> 比例对齐与校验 -> 单浏览器批量渲染分场。"""
    eff_style = active_style_id or ("style_14" if track == "store" else "style_11")

    seed_items: List[Dict[str, Any]] = []
    if script_p and script_p.exists():
        raw_scr = read_json(script_p)
        seed_items = raw_scr.get("sentences") or raw_scr.get("segments") or [] if isinstance(raw_scr, dict) else list(raw_scr)

    # 1. 准备初始 00_code_spec.json（如果传入 --code-spec 则保留用户全部自定义顶层字段）
    spec_out = pipeline_dir / "00_code_spec.json"
    user_custom_sections = False
    user_extra_fields: Dict[str, Any] = {}
    if code_spec_p and code_spec_p.exists():
        spec = read_json(code_spec_p)
        user_custom_sections = bool(spec.get("sections"))
        known_spec_keys = {
            "version", "title", "one_idea", "format", "style_id", "track", "palette",
            "sections", "exact_copy", "facts", "assets", "risks", "must_haves",
        }
        user_extra_fields = {k: v for k, v in spec.items() if k not in known_spec_keys}
        spec["_user_custom_sections"] = user_custom_sections
        write_json(spec_out, spec)
        if not (pipeline_dir / "SPEC.md").is_file() or not (pipeline_dir / "STRUCTURE.md").is_file():
            fmt = spec.get("format") or {}
            init_code_spec(
                title=str(spec.get("title") or store_anchor or "核心拆解"),
                one_idea=str(spec.get("one_idea") or "一句看懂核心对比真相"),
                out_dir=pipeline_dir,
                duration_sec=float(fmt.get("target_duration_sec", 15.0)),
                width=int(fmt.get("width", CANVAS_WIDTH)),
                height=int(fmt.get("height", CANVAS_HEIGHT)),
                fps=int(fmt.get("fps", DEFAULT_FPS)),
                style_id=str(spec.get("style_id") or eff_style),
                track=str(spec.get("track") or track),
                sections=spec.get("sections"),
                exact_copy=spec.get("exact_copy"),
                facts=spec.get("facts"),
                asset_paths=[Path(a["path"]) for a in spec.get("assets", []) if a.get("path")],
                risks=spec.get("risks"),
                must_haves=spec.get("must_haves"),
            )
    else:
        t_seed = _compact_code_title(store_anchor or (seed_items[0].get("show") or seed_items[0].get("text") if seed_items else "重点拆解"), 14)
        idea_parts = [str(it.get("show") or it.get("text") or "").strip() for it in seed_items[:2] if str(it.get("show") or it.get("text") or "").strip()]
        one_idea = " ".join(idea_parts)[:42] if idea_parts else f"{t_seed}核心原理与实测对比"
        copy_seed = [t_seed] + [str(it.get("show") or it.get("text") or "")[:24] for it in seed_items if str(it.get("show") or it.get("text") or "").strip()]
        init_code_spec(
            title=t_seed,
            one_idea=one_idea,
            out_dir=pipeline_dir,
            duration_sec=15.0,
            style_id=eff_style,
            track=track,
            exact_copy=copy_seed,
        )
        spec = read_json(spec_out)

    # 2. 先音后画：无 01_manifest 直接触发 TTS + WordBoundary 与 Step 3 音轨锁
    run_step2(
        pipeline_dir,
        track=track,
        script_json_path=script_p,
        force_tts=True,
        whisper_model=whisper_model,
        whitelist_path=whitelist_path,
        dialect=dialect,
        store_anchor=store_anchor,
    )
    record_milestone(pipeline_dir, "stop1_script", "Code2Video 脚本转写与语音对齐完成")
    run_step3(
        pipeline_dir,
        track=track,
        bgm_path=bgm_p,
        pause_sec=pause_sec,
        account_profile=account_profile,
    )
    record_milestone(pipeline_dir, "stop2_blind_audio", "Code2Video 音轨节拍与边界锁定完成")

    # 3. 用真实锁定音长校正并强校验 00_code_spec.json
    ae = read_json(pipeline_dir / "03_audio_events.json")
    locked_dur = max(3.0, float(ae.get("total_duration_sec", ae.get("locked_duration_sec", 12.0))))

    sections = spec.get("sections") or []
    if sections:
        raw_sum = sum(max(0.5, float(s.get("duration_sec", 1.0))) for s in sections)
        scale = locked_dur / max(0.5, raw_sum)
        cur_t = 0.0
        for si, sec in enumerate(sections):
            if si == len(sections) - 1:
                sd = round(max(1.5, locked_dur - cur_t), 3)
            else:
                sd = round(max(1.5, float(sec.get("duration_sec", 2.0)) * scale), 3)
            sec["start_sec"] = round(cur_t, 3)
            sec["end_sec"] = round(cur_t + sd, 3)
            sec["duration_sec"] = sd
            sec["hold_sec"] = sd
            cur_t += sd

    spec.setdefault("format", {})
    spec["format"]["target_duration_sec"] = round(locked_dur, 3)
    spec["format"]["frame_count"] = int(round(locked_dur * int(spec["format"].get("fps", DEFAULT_FPS))))
    init_code_spec(
        title=str(spec.get("title") or "核心拆解"),
        one_idea=str(spec.get("one_idea") or "一句话看清核心事实"),
        out_dir=pipeline_dir,
        duration_sec=locked_dur,
        width=int(spec["format"].get("width", CANVAS_WIDTH)),
        height=int(spec["format"].get("height", CANVAS_HEIGHT)),
        fps=int(spec["format"].get("fps", DEFAULT_FPS)),
        style_id=str(spec.get("style_id") or eff_style),
        track=str(spec.get("track") or track),
        sections=sections,
        exact_copy=spec.get("exact_copy"),
        facts=spec.get("facts"),
        asset_paths=[Path(a["path"]) for a in spec.get("assets", []) if a.get("path")],
        risks=spec.get("risks"),
        must_haves=spec.get("must_haves"),
    )
    spec = read_json(spec_out)
    if user_extra_fields or user_custom_sections or (code_html_p and code_html_p.exists()):
        for k_ex, v_ex in user_extra_fields.items():
            spec.setdefault(k_ex, v_ex)
        if user_custom_sections:
            spec["_user_custom_sections"] = True
        if code_html_p and code_html_p.exists():
            spec["code_html_path"] = str(code_html_p.resolve())
        write_json(spec_out, spec)
    val = validate_code_spec(spec)
    if not val.get("passed"):
        raise RuntimeError(f"00_code_spec 校验失败，已阻断渲染: {'; '.join(val.get('errors', []))}")

    return _render_code_scenes_from_spec(
        pipeline_dir=pipeline_dir,
        track=track,
        active_style_id=eff_style,
        code_html_p=code_html_p,
        code_backend=code_backend,
    )


def _render_and_verify_only(
    pipeline_dir: Path,
    track: str,
    benchmark: Optional[Path],
    simulate_jy_fail: bool,
    simulate_hf_fail: bool,
    dialect: str,
    store_anchor: Optional[str],
    require_lock: bool,
    strict_asr: bool,
    hook_variants: int,
    ws: Optional[Dict[str, Any]],
    export_mode: str = "auto",
    sync_window: Optional[List[float]] = None,
) -> Dict[str, Any]:
    if require_lock:
        code, msg, _ = verify_lock(pipeline_dir)
        if code != 0:
            raise RuntimeError(f"哈希锁校验失败，阻断正式渲染：{msg}")

    final_mp4 = render_mp4(pipeline_dir, preview=False)
    if hook_variants > 1:
        _generate_hook_variants(pipeline_dir, hook_variants)
    generate_action_strips(final_mp4, pipeline_dir / "04_edl.json", pipeline_dir / "10_action_strips.jpg")
    targets, _ = export_selection(export_mode)
    jy_status = (export_jianying_draft(pipeline_dir, simulate_failure=simulate_jy_fail)
                 if "jianying" in targets else {"status": "not_requested"})
    hf_status = (export_hyperframes_draft(pipeline_dir, simulate_failure=simulate_hf_fail, prepared_segments=True)
                 if "hyperframes" in targets else {"status": "not_requested"})

    qa_report = inspect_video(
        pipeline_dir,
        video_path=final_mp4,
        benchmark_path=benchmark,
        dialect=dialect,
        store_anchor=store_anchor,
        strict_asr=strict_asr,
        export_mode=export_mode,
        sync_window=sync_window,
    )
    if (pipeline_dir / "00_code_spec.json").is_file():
        generate_verify_template(
            pipeline_dir,
            spec_path=pipeline_dir / "00_code_spec.json",
            video_path=final_mp4,
        )
    decisions_md = write_decisions_made(pipeline_dir, track)
    write_review_player_html(pipeline_dir)
    delivery_md = write_delivery_summary(pipeline_dir, ws or {}, track, qa_report)

    return {
        "final_mp4": str(final_mp4),
        "jianying": jy_status,
        "hyperframes": hf_status,
        "qa_report": qa_report,
        "decisions_made_md": str(decisions_md),
        "delivery_summary_md": str(delivery_md),
    }


def run_visual_to_delivery(
    pipeline_dir: Path,
    track: str,
    j_cut_frames: int,
    subtitle_template: Optional[str],
    lut_name: Optional[str],
    prefer_broll_only: bool,
    benchmark: Optional[Path],
    simulate_jy_fail: bool,
    simulate_hf_fail: bool = False,
    preview_only: bool = False,
    style_id: Optional[str] = None,
    account_profile: Optional[Dict[str, Any]] = None,
    dialect: str = "mandarin",
    store_anchor: Optional[str] = None,
    require_lock: bool = False,
    strict_asr: bool = False,
    licenses_path: Optional[Path] = None,
    hook_variants: int = 1,
    ws: Optional[Dict[str, Any]] = None,
    export_mode: str = "auto",
    edit_profile: str = "talking",
    sync_window: Optional[List[float]] = None,
) -> Dict[str, Any]:
    run_step4(
        pipeline_dir,
        track=track,
        j_cut_frames=j_cut_frames,
        prefer_broll_only=prefer_broll_only,
        style_id=style_id,
        account_profile=account_profile,
        edit_profile=edit_profile,
    )
    run_step5(pipeline_dir, track=track, template_id=subtitle_template)
    run_step6(pipeline_dir, style_id=style_id)
    write_source_review(pipeline_dir)
    run_step7(pipeline_dir, track=track, lut_name=lut_name, style_id=style_id)
    run_step8(
        pipeline_dir,
        licenses_path=licenses_path,
        out_dir=(ws or {}).get("out_dir"),
    )
    run_step9(pipeline_dir, track=track, style_id=style_id)

    if preview_only:
        preview_mp4 = render_mp4(pipeline_dir, preview=True)
        return {"preview_mp4": str(preview_mp4)}

    return _render_and_verify_only(
        pipeline_dir=pipeline_dir,
        track=track,
        benchmark=benchmark,
        simulate_jy_fail=simulate_jy_fail,
        simulate_hf_fail=simulate_hf_fail,
        dialect=dialect,
        store_anchor=store_anchor,
        require_lock=require_lock,
        strict_asr=strict_asr,
        export_mode=export_mode,
        hook_variants=hook_variants,
        ws=ws,
        sync_window=sync_window,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="short-video-studio 专业端到端流水线编排器 (支持多账号与专属工作区隔离)")
    parser.add_argument("--project-dir", help="可选：自定义加工项目目录（未传时自动落在 --workspace-root 下隔离目录）")
    parser.add_argument("--raw-dir", help="原始素材目录（严格只读，绝不向此目录写入任何加工文件）")
    parser.add_argument("--account", help="账号标识，自动隔离该账号参数基因/合规白名单/复盘日志/项目目录")
    parser.add_argument("--project-id", help="项目标识")
    parser.add_argument("--workspace-root", help="专属加工工作区根目录")
    parser.add_argument("--track", choices=["store", "creator"], default="store")
    parser.add_argument(
        "--mode",
        choices=["full", "lock-preview", "reedit-visuals", "relock-voice", "render-locked", "code-video", "knowledge-animation"],
        default="full",
        help="执行模式",
    )
    parser.add_argument("--anim-title", default="知识讲解动画", help="knowledge-animation 模式：片名")
    parser.add_argument("--anim-idea", default="用直观画面看穿一个反常识规律", help="knowledge-animation 模式：核心命题")
    parser.add_argument("--anim-ratio", choices=["16x9", "9x16", "1x1", "3x4"], default="16x9", help="knowledge-animation 模式：画幅")
    parser.add_argument("--anim-font-mode", choices=["sans", "serif"], default="sans", help="knowledge-animation 模式：字幕与封面字体气质")
    parser.add_argument("--anim-blur", type=int, default=1, help="knowledge-animation 模式：运动模糊子帧数 (1=关闭, 8=电影级模糊)")
    parser.add_argument("--anim-lines-json", help="knowledge-animation 模式：可选自定义 lines.json（含分句与金句标记）")
    parser.add_argument("--anim-audio", help="knowledge-animation 模式：可选配音 WAV/M4A（自动同步音轨并压低 BGM）")
    parser.add_argument("--code-spec", help="入口 3 (code-video)：已有 00_code_spec.json 路径")
    parser.add_argument("--code-html", help="入口 3 (code-video)：自定义程序动画 HTML 目录或入口 HTML 文件路径")
    parser.add_argument(
        "--code-backend",
        choices=["auto", "html", "pillow"],
        default="auto",
        help="入口 3 / 代码补镜渲染后端",
    )
    parser.add_argument("--script-json", help="口播或配音台词 JSON 文件")
    parser.add_argument("--force-tts", action="store_true", help="强制使用文案生成 TTS 配音")
    parser.add_argument("--bgm", help="自定义 BGM 文件路径")
    parser.add_argument("--pause-sec", type=float, help="基准句间停顿，显式值覆盖账号配置 (0.14-0.32s)")
    parser.add_argument("--j-cut-frames", type=int, default=None, help="句间 J-cut 声先入帧数 (默认 3，或由 --style-id 决定)")
    parser.add_argument("--style-id", help="可选：套用风格谱模板 ID (style_01 ~ style_24)")
    parser.add_argument("--subtitle-template", help="字幕模板 ID")
    parser.add_argument("--lut", help="调色 LUT 文件名")
    parser.add_argument("--prefer-broll-only", action="store_true", help="改画模式：尽量切换为纯 B-roll/代码补镜")
    parser.add_argument("--benchmark", help="可选：对标视频路径")
    parser.add_argument("--sources-json", help="主张与原始材料对应表")
    parser.add_argument("--edit-profile", choices=["auto", *EDIT_PROFILES], default="auto")
    parser.add_argument("--raw-intel", help="可选：一手原材萃取 00_raw_intel.json 路径")
    parser.add_argument("--visual-index", help="可选：外部高精度镜头语义索引 00_visual_index.json 路径")
    parser.add_argument("--platform", help="制作目标平台，用于选择已启用的实验参数")
    parser.add_argument("--account-profile", help="可选：账号参数基因 account_profile.json 路径")
    parser.add_argument("--whitelist", help="可选：账号合规白名单 compliance_whitelist.json 路径")
    parser.add_argument("--licenses-json", help="可选：外部资产商用授权清单 licenses.json 路径")
    parser.add_argument("--opening-title-previews", "--hook-variants", dest="hook_variants", type=int, default=1, help="生成片头标题条对比预览")
    parser.add_argument("--dialect", choices=["mandarin", "cantonese", "dialect"], default="mandarin", help="口播语种，用于转写与盲听复核")
    parser.add_argument("--store-anchor", help="门店听觉锚点（如门店名），用于热词与盲听核验")
    parser.add_argument("--multi-speaker", action="store_true", help="多人访谈/双人对话模式（禁止抑制第二人声音）")
    parser.add_argument("--whisper-model", help="可选：显式指定本地 faster-whisper 模型名称")
    parser.add_argument("--sync-window", type=float, nargs=2, metavar=("START", "END"), help="可选：实测闪帧/测试音同步检测窗")
    parser.add_argument("--require-lock", action="store_true", help="正式渲染前强制校验 approval_lock.json 指纹锁")
    parser.add_argument("--exports", choices=EXPORT_CHOICES, help="auto 尝试两种工程并允许 MP4 降级，显式选择的工程进入必检")
    parser.add_argument("--strict-asr", action="store_true", help="无本地 Whisper 模型时阻止 #21 通过")
    parser.add_argument("--keep-temp", action="store_true", help="调试用：完工后保留大体积中间临时文件")
    parser.add_argument("--simulate-jy-fail", action="store_true", help="测试剪映草稿失效降级保护")
    parser.add_argument("--simulate-hf-fail", action="store_true", help="测试 HyperFrames 草稿失效降级保护")
    args = parser.parse_args()

    ws = resolve_workspace_paths(
        account=args.account,
        project_id=args.project_id,
        project_dir=Path(args.project_dir) if args.project_dir else None,
        raw_dir=Path(args.raw_dir) if args.raw_dir else None,
        workspace_root=Path(args.workspace_root) if args.workspace_root else None,
    )
    project_dir = ws["project_dir"]
    raw_dir = ws["raw_dir"]
    pipeline_dir = ws["pipeline_dir"]
    pipeline_dir.mkdir(parents=True, exist_ok=True)
    previous_qa = pipeline_dir / "10_qa_report.json"
    previous_delivery = read_json(previous_qa) if previous_qa.is_file() else {}
    if args.exports is None:
        args.exports = previous_delivery.get("export_mode", "auto")
    if ws["redirected_from_raw"]:
        print(f"[workspace] 检测到加工目录与原素材目录重叠，已强制隔离至专属工作区 -> {project_dir}")
    else:
        print(f"[workspace] 账号={ws['account_slug']} | 加工目录={project_dir} | 原素材只读源={raw_dir}")

    account_profile: Optional[Dict[str, Any]] = None
    track_profile = ws["content_log_dir"] / f"account_profile_{args.track}.json"
    prof_path = Path(args.account_profile) if args.account_profile else (
        track_profile if track_profile.is_file() else ws["account_profile_path"]
    )
    if prof_path.exists():
        profile = read_json(prof_path)
        scope_matches = (
            not profile.get("platform")
            or args.platform is None
            or str(profile["platform"]).casefold() == str(args.platform).casefold()
        )
        if args.account_profile or (profile.get("track", "store") == args.track and scope_matches):
            account_profile = profile
            print(f"[pipeline] 已载入账号参数 ({ws['account_slug']}/{args.track}) -> {prof_path.name}")
    if args.pause_sec is None:
        args.pause_sec = 0.20
    elif account_profile:
        account_profile = {key: value for key, value in account_profile.items() if key != "pause_sec"}

    if args.sources_json:
        import_sources(Path(args.sources_json), pipeline_dir)
    previous_edl = pipeline_dir / "04_edl.json"
    edit_profile = args.edit_profile
    if edit_profile == "auto":
        edit_profile = ("explainer" if args.mode == "code-video" else
                        read_json(previous_edl).get("edit_profile", "talking") if
                        args.mode in ("reedit-visuals", "relock-voice") and previous_edl.is_file() else "talking")
    lock_files = []
    locked_before = []
    if args.mode == "reedit-visuals":
        ae_check_p = pipeline_dir / "03_audio_events.json"
        if not ae_check_p.is_file():
            raise FileNotFoundError("reedit-visuals 模式要求 03_audio_events.json 已锁定存在。")
        audio_events = read_json(ae_check_p)
        lock_files = [Path(audio_events[key]) if audio_events.get(key) else pipeline_dir / fallback
                      for key, fallback in (("locked_voice_wav", "03_locked_voice.wav"), ("locked_bgm_wav", "03_locked_bgm.wav"))]
        missing_lf = [str(p) for p in lock_files if not p.is_file()]
        if missing_lf:
            raise FileNotFoundError(f"只改画面模式缺少已锁定音轨文件：{', '.join(missing_lf)}")
        locked_before = [sha256_file(path) for path in lock_files]

    whitelist_path = Path(args.whitelist) if args.whitelist else ws["compliance_whitelist_path"]
    licenses_path = Path(args.licenses_json) if args.licenses_json else None
    visual_index_path = Path(args.visual_index) if args.visual_index else None

    raw_intel_obj: Optional[Dict[str, Any]] = None
    if args.raw_intel and Path(args.raw_intel).exists():
        dst_intel = pipeline_dir / "00_raw_intel.json"
        if Path(args.raw_intel).resolve() != dst_intel.resolve():
            shutil.copy2(args.raw_intel, dst_intel)
        raw_intel_obj = read_json(dst_intel)

    prof_pref_style = (
        account_profile.get("preferred_style_id")
        if (account_profile and account_profile.get("sample_sufficient") is True)
        else None
    )
    active_style_id = (
        args.style_id
        or load_style_applied(pipeline_dir)
        or prof_pref_style
        or ("style_14" if args.track == "store" else "style_11")
    )
    j_cut_frames = 3 if args.j_cut_frames is None else int(args.j_cut_frames)
    subtitle_template = args.subtitle_template
    lut_name = args.lut
    bgm_p = Path(args.bgm) if args.bgm else None
    active_style_entry: Optional[Dict[str, Any]] = None

    if active_style_id and args.mode != "knowledge-animation":
        lib_once = load_library()
        rt_cfg = resolve_style_runtime_config(active_style_id)
        active_style_entry = load_style_spectrum_entry(active_style_id)
        if not subtitle_template:
            subtitle_template = rt_cfg["subtitle_template"]
        if not lut_name:
            lut_name = rt_cfg["lut_file"]
        if args.j_cut_frames is None:
            j_cut_frames = int(rt_cfg["j_cut_frames"])  # 严格保留 0 帧直切，禁止 `or 3` 吞掉
        if args.mode != "render-locked":
            applied_p = apply_to_pipeline(lib_once, active_style_id, pipeline_dir)
            if args.j_cut_frames is not None or args.subtitle_template or args.lut:
                applied_obj = read_json(applied_p)
                applied_obj["subtitle_template"] = subtitle_template
                applied_obj["lut_file"] = lut_name
                applied_obj["j_cut_frames"] = j_cut_frames
                write_json(applied_p, applied_obj)
        if bgm_p is None:
            try:
                from vibe_sound import get_style_sound_profile
                v_prof = get_style_sound_profile(active_style_id)
                if v_prof and v_prof.get("bgm_wav") and Path(v_prof["bgm_wav"]).exists():
                    bgm_p = Path(v_prof["bgm_wav"])
            except Exception:
                pass
        print(
            f"[pipeline] 已挂载风格 {active_style_id} ({rt_cfg['style_name_cn']}) -> "
            f"字幕={subtitle_template}, 调色={lut_name}, 声画错切={j_cut_frames}帧"
        )

    if args.edit_profile == "auto" and args.mode in ("full", "lock-preview") and active_style_entry:
        med_sec = float((active_style_entry.get("shot_distribution") or {}).get("median_sec") or 1.5)
        b_tgt = float(active_style_entry.get("broll_overlay_ratio_target") or 0.5)
        if med_sec >= 2.2 or b_tgt >= 0.90:
            edit_profile = "documentary"
    eff_prefer_broll_only = bool(
        args.prefer_broll_only
        or float((active_style_entry or {}).get("broll_overlay_ratio_target") or 0.5) >= 0.995
    )

    script_p = Path(args.script_json) if args.script_json else None
    if script_p and script_p.exists():
        _run_script_prelint(script_p, pipeline_dir, raw_intel=raw_intel_obj)
    bench_p = Path(args.benchmark) if args.benchmark else None

    def _ensure_effective_raw_dir() -> Path:
        has_media = raw_dir.is_dir() and any(
            p.is_file() and p.suffix.lower() in MEDIA_EXTS for p in raw_dir.iterdir()
        )
        if has_media:
            return raw_dir
        if args.raw_dir:
            raise FileNotFoundError(f"指定的原素材目录没有可用视频：{raw_dir}")
        demo_dir = project_dir / "_demo_raw_media"
        if not (demo_dir.is_dir() and any(p.is_file() and p.suffix.lower() in MEDIA_EXTS for p in demo_dir.iterdir())):
            print("[pipeline] 未检测到原始素材，正在专属工作区内生成演示素材包（零写入原目录）...")
            generate_demo_media_pack(demo_dir, style_id=active_style_id)
        return demo_dir

    def _run_inventory_if_needed(src_raw: Path) -> None:
        raw_intel_p = pipeline_dir / "00_raw_intel.json"
        raw_intel = read_json(raw_intel_p) if raw_intel_p.is_file() else None
        contact_jpg = pipeline_dir / "00_contact_sheet.jpg"
        inv = inventory_directory(
            src_raw, args.track,
            raw_intel=raw_intel,
            contact_sheet_path=contact_jpg,
            visual_index_path=visual_index_path,
        )
        write_json(pipeline_dir / "00_inventory.json", inv)
        write_json(pipeline_dir / "00_shot_log.json", build_shot_log_dict(inv))
        (pipeline_dir / "00_inventory.md").write_text(render_markdown_summary(inv), encoding="utf-8")

    if args.mode == "render-locked":
        code_lk, msg_lk, _ = verify_lock(pipeline_dir)
        if code_lk != 0:
            raise RuntimeError(f"哈希锁校验失败，阻断正式渲染：{msg_lk}")
        _ensure_reedit_dependencies(pipeline_dir, track=args.track, bgm_p=bgm_p, pause_sec=args.pause_sec, account_profile=account_profile, preserve_locked_audio=True)
        res = _render_and_verify_only(
            pipeline_dir=pipeline_dir,
            track=args.track,
            benchmark=bench_p,
            simulate_jy_fail=args.simulate_jy_fail,
            simulate_hf_fail=args.simulate_hf_fail,
            dialect=args.dialect,
            store_anchor=args.store_anchor,
            require_lock=True,
            strict_asr=args.strict_asr,
            export_mode=args.exports,
            hook_variants=args.hook_variants,
            ws=ws,
            sync_window=args.sync_window,
        )
    elif args.mode == "knowledge-animation":
        anim_dir = project_dir / "animation"
        lines_override: Optional[List[Dict[str, Any]]] = None
        if args.anim_lines_json and Path(args.anim_lines_json).is_file():
            raw_al = read_json(Path(args.anim_lines_json))
            lines_override = list(raw_al.get("lines") if isinstance(raw_al, dict) else raw_al)
        elif script_p and script_p.is_file():
            raw_sc = read_json(script_p)
            sc_items = list(raw_sc.get("sentences") or raw_sc.get("segments") or [] if isinstance(raw_sc, dict) else raw_sc)
            lines_override = []
            for s_i, s_it in enumerate(sc_items):
                if s_it.get("is_filler"):
                    continue
                s_txt = str(s_it.get("show") or s_it.get("text") or "").strip()
                if not s_txt:
                    continue
                if s_i == 2:
                    lines_override.append({"id": "title_card", "text": args.anim_title, "card": True, "hold": 3.0})
                lines_override.append({
                    "id": str(s_it.get("id") or f"l{s_i + 1:02d}"),
                    "text": s_txt,
                    "hook": bool(s_it.get("hook") or s_i < 2),
                    "scene": bool(s_it.get("scene") or s_i >= 2),
                })
            if not any(x.get("card") for x in lines_override):
                lines_override.insert(min(2, len(lines_override)), {"id": "title_card", "text": args.anim_title, "card": True, "hold": 3.0})

        init_res = init_animation_project(
            anim_dir,
            title=args.anim_title,
            one_idea=args.anim_idea,
            ratio=args.anim_ratio,
            font_mode=args.anim_font_mode,
            lines_override=lines_override,
        )
        br = detect_browser_renderer()
        if not br.get("available"):
            raise RuntimeError("knowledge-animation 模式需要可用 Chrome/playwright-core，请先运行 check_and_setup.py --init-browser。")
        dim_map = {"16x9": "1920x1080", "9x16": "1080x1920", "1x1": "1080x1080", "3x4": "1080x1440"}
        size_arg = dim_map.get(args.anim_ratio, "1920x1080")
        stage_dir = Path(init_res["stage_dir"])
        silent_mp4 = anim_dir / "work" / "anim_video_silent.mp4"
        out_mp4 = pipeline_dir / "output_final.mp4"
        cap_script = Path(__file__).resolve().parent / "capture_html_video.mjs"
        cap_env = dict(os.environ)
        ff_bin = find_bin("ffmpeg")
        if ff_bin:
            cap_env["FFMPEG_BIN"] = ff_bin

        subprocess.run([
            str(br["node_bin"]), str(cap_script), str(stage_dir),
            "--verify", "--page", "anim_starter.html", "--size", size_arg, "--query", f"ratio={args.anim_ratio}",
        ], check=True, env=cap_env)
        subprocess.run([
            str(br["node_bin"]), str(cap_script), str(stage_dir),
            "--page", "anim_starter.html", "--size", size_arg, "--fps", "30",
            "--blur", str(max(1, int(args.anim_blur))), "--query", f"ratio={args.anim_ratio}",
            "--out", str(silent_mp4.resolve()),
        ], check=True, env=cap_env)

        # 真正合成 BGM + 15 种程序化动效拟音 (+ 可选配音) 并规范化响度封装进 output_final.mp4
        audio_mix = mix_animation_audio(
            video_in=silent_mp4,
            video_out=out_mp4,
            compiled_timing=init_res["compiled_timing"],
            work_dir=anim_dir / "work",
            bgm_path=bgm_p,
            voice_wav=Path(args.anim_audio) if args.anim_audio else None,
        )

        audit_res = audit_animation_video(out_mp4)
        audit_res["audio_mix"] = audio_mix
        audit_res["fonts"] = init_res.get("fonts")
        write_json(pipeline_dir / "10_animation_audit.json", audit_res)
        rp_res = build_review_pack(
            out_mp4,
            pipeline_dir / "review_pack",
            timing_js=Path(init_res["timing_js"]),
            storyboard_md=anim_dir / "work" / "storyboard.md",
        )
        cov_4k = render_dual_4k_code_covers(
            pipeline_dir,
            kicker=args.anim_idea[:18],
            hero_lines=[args.anim_title[:4], args.anim_title[4:8] or "真相拆解"],
            title=args.anim_title,
            font_mode=args.anim_font_mode,
        )
        lines_cfg = read_json(Path(init_res["lines_json"]))
        spoken_sents = [{"id": l.get("id", f"l{i+1}"), "text": l["text"]} for i, l in enumerate(lines_cfg.get("lines", [])) if not l.get("card")]
        copy_pack = build_publish_copy_pack(
            pipeline_dir,
            title_seed=args.anim_title,
            hook_text=args.anim_idea,
            sentences=spoken_sents,
            keywords=[args.anim_title[:6]],
            track=args.track,
            cover_main=args.anim_title,
            cover_sub=args.anim_idea[:12],
            has_4k_covers=bool(cov_4k.get("ok")),
        )
        # 合规与商业授权核验
        comp_sents = list(spoken_sents)
        for plat_k, plat_v in (copy_pack.get("platforms") or {}).items():
            for ti, tt in enumerate(plat_v.get("titles") or [], 1):
                comp_sents.append({"id": f"copy_{plat_k}_t{ti}", "text": str(tt)})
            if plat_v.get("body"):
                comp_sents.append({"id": f"copy_{plat_k}_body", "text": str(plat_v["body"])})
        comp_rep = audit_script_compliance(
            comp_sents,
            source_type="script",
            pipeline_dir=pipeline_dir,
            whitelist_path=whitelist_path,
            auto_action=False,
        )
        lic_rep = build_asset_license_manifest(pipeline_dir, out_dir=ws["out_dir"], licenses_path=licenses_path)

        lufs_v = audio_mix.get("integrated_lufs")
        tp_v = audio_mix.get("true_peak_dbtp")
        audio_ok = bool(audio_mix.get("has_audio") and (lufs_v is None or abs(float(lufs_v) - (-14.0)) <= 2.5) and (tp_v is None or float(tp_v) <= -0.8))
        fonts_ok = bool((init_res.get("fonts") or {}).get("injected"))
        anim_checks = [
            {"id": "anim_pixel_audit", "name": "6x6死区/闪帧/暗底亮度指纹", "status": "PASS" if audit_res.get("passed") else "FAIL", "passed": bool(audit_res.get("passed")), "measured": f"死区={len(audit_res.get('dead_zones',[]))}, 闪帧={len(audit_res.get('flash_frames',[]))}, p99={audit_res.get('luminance_fingerprint',{}).get('p99')}", "threshold": "0死区, 0闪帧, 亮度指纹达标"},
            {"id": "anim_audio_mux", "name": "BGM+动效拟音/配音混音封装", "status": "PASS" if audio_ok else "FAIL", "passed": audio_ok, "measured": f"LUFS={lufs_v}, TP={tp_v} dBTP, 拟音={audio_mix.get('sfx_cue_count')}个", "threshold": "含立体声音轨, -14 LUFS 附近不削波"},
            {"id": "anim_commercial_fonts", "name": "随仓开源商用字体注入", "status": "PASS" if fonts_ok else "FAIL", "passed": fonts_ok, "measured": f"已注入 {len((init_res.get('fonts') or {}).get('injected', []))} 款字体", "threshold": ">=1 款已核验开源商用字体"},
            {"id": "anim_dual_4k_covers", "name": "横竖双比例4K代码封面", "status": "PASS" if cov_4k.get("ok") else "FAIL", "passed": bool(cov_4k.get("ok")), "measured": f"生成 {len(cov_4k.get('outputs', []))} 张", "threshold": "横版16:9 + 竖版3:4均达标"},
            {"id": "anim_compliance", "name": "台词与多平台发布文案合规审查", "status": "PASS" if comp_rep.get("passed") else "FAIL", "passed": bool(comp_rep.get("passed")), "measured": f"红线={comp_rep.get('must_sentence_count',0)}, 提醒={comp_rep.get('warn_hit_count',0)}", "threshold": "0 条禁止红线"},
        ]
        all_ok = all(c["passed"] for c in anim_checks)
        pass_cnt = sum(1 for c in anim_checks if c["passed"])
        fail_cnt = len(anim_checks) - pass_cnt
        qa_payload = {
            "step": "10_qa_inspector",
            "mode": "knowledge-animation",
            "video_path": str(out_mp4.resolve()),
            "plan_sha256": compute_plan_digest(pipeline_dir),
            "output_final_sha256": sha256_file(out_mp4),
            "all_passed": all_ok,
            "machine_passed": all_ok,
            "approval_status": "MACHINE_PASS_PENDING_HUMAN" if all_ok else "REJECTED",
            "export_mode": "mp4",
            "required_package_hashes": {},
            "required_manual_checks": [],
            "pending_manual_checks": [],
            "pass_count": pass_cnt,
            "fail_count": fail_cnt,
            "skipped_count": 0,
            "total_checks": len(anim_checks),
            "checks": anim_checks,
            "deliverables": {"mp4": {"status": "PASS" if all_ok else "FAIL"}},
            "animation_audit": audit_res,
            "review_pack": rp_res,
            "dual_4k_covers": cov_4k,
            "publish_copy_pack": copy_pack["preferred_title"],
            "license_passed": lic_rep.get("passed"),
        }
        write_json(pipeline_dir / "10_qa_report.json", qa_payload)
        (pipeline_dir / "10_qa_report.md").write_text(
            f"# 知识讲解动画体检报告（共 {len(anim_checks)} 项）\n\n"
            f"- **结论**：{'✅ 全部自动检查通过，请看审片包确认一眼即可发布' if all_ok else '❌ 存在未通过项，请先修复再发'}\n"
            f"- **声音混音**：{audio_mix['voice_mode']}（响度 {lufs_v} LUFS，峰值 {tp_v} dBTP，动效拟音 {audio_mix['sfx_cue_count']} 处）\n"
            f"- **审片包**：`review_pack/01_contact_2s.png` · `review_pack/02_keyframes.png` · `review_pack/blind_review_guide.md`\n"
            f"- **封面与文案**：`09_cover_land_4k.png` · `09_cover_port_4k.png` · `09_publish_copy_pack.md`\n",
            encoding="utf-8",
        )
        record_milestone(pipeline_dir, "stop3_final", f"知识讲解动画出片完成({args.anim_ratio}, {audit_res.get('duration_sec')}s)")
        prog_card = render_progress_card(pipeline_dir, user_type="faceless_visual", track=args.track, write_files=True)
        tidy_workspace(pipeline_dir, out_dir=ws["out_dir"], keep_temp=args.keep_temp)
        print(f"[knowledge-animation] 完成 -> {ws['out_dir'] / 'output_final.mp4'}")
        print("\n" + prog_card["markdown_card"])
        if not all_ok:
            sys.exit(2)
        return
    elif args.mode == "code-video":
        scenes_dir = _run_code_video_branch(
            pipeline_dir=pipeline_dir,
            track=args.track,
            script_p=script_p,
            code_spec_p=Path(args.code_spec) if args.code_spec else None,
            code_html_p=Path(args.code_html) if args.code_html else None,
            code_backend=args.code_backend,
            active_style_id=active_style_id,
            bgm_p=bgm_p,
            pause_sec=args.pause_sec,
            account_profile=account_profile,
            whitelist_path=whitelist_path,
            store_anchor=args.store_anchor,
            dialect=args.dialect,
            whisper_model=args.whisper_model,
        )
        run_step1([scenes_dir], pipeline_dir)
        res = run_visual_to_delivery(
            pipeline_dir=pipeline_dir,
            track=args.track,
            j_cut_frames=j_cut_frames,
            subtitle_template=subtitle_template,
            lut_name=lut_name,
            prefer_broll_only=True,
            benchmark=bench_p,
            simulate_jy_fail=args.simulate_jy_fail,
            simulate_hf_fail=args.simulate_hf_fail,
            preview_only=False,
            style_id=active_style_id,
            account_profile=account_profile,
            dialect=args.dialect,
            store_anchor=args.store_anchor,
            require_lock=args.require_lock,
            strict_asr=args.strict_asr,
            export_mode=args.exports,
            edit_profile=edit_profile,
            licenses_path=licenses_path,
            hook_variants=args.hook_variants,
            ws=ws,
            sync_window=args.sync_window,
        )
    else:
        if args.mode in ("full", "lock-preview"):
            eff_raw = _ensure_effective_raw_dir()
            _run_inventory_if_needed(eff_raw)
            run_step1([eff_raw], pipeline_dir)
            run_step2(
                pipeline_dir,
                track=args.track,
                script_json_path=script_p,
                force_tts=args.force_tts,
                whisper_model=args.whisper_model,
                whitelist_path=whitelist_path,
                dialect=args.dialect,
                store_anchor=args.store_anchor,
                multi_speaker=args.multi_speaker,
            )
            record_milestone(pipeline_dir, "stop1_script", "Step 2 脚本转写与合规门禁完成")
            run_step3(
                pipeline_dir,
                track=args.track,
                bgm_path=bgm_p,
                pause_sec=args.pause_sec,
                account_profile=account_profile,
            )
            record_milestone(pipeline_dir, "stop2_blind_audio", "Step 3 盲听锁定音轨完成")
        elif args.mode == "relock-voice":
            if not (pipeline_dir / "01_manifest.json").exists():
                eff_raw = _ensure_effective_raw_dir()
                _run_inventory_if_needed(eff_raw)
                run_step1([eff_raw], pipeline_dir)
            else:
                _ensure_reedit_dependencies(pipeline_dir, track=args.track, bgm_p=bgm_p, pause_sec=args.pause_sec, account_profile=account_profile)
            run_step2(
                pipeline_dir,
                track=args.track,
                script_json_path=script_p,
                force_tts=True if script_p else args.force_tts,
                whisper_model=args.whisper_model,
                whitelist_path=whitelist_path,
                dialect=args.dialect,
                store_anchor=args.store_anchor,
                multi_speaker=args.multi_speaker,
            )
            record_milestone(pipeline_dir, "stop1_script", "relock-voice 脚本重建完成")
            run_step3(
                pipeline_dir,
                track=args.track,
                bgm_path=bgm_p,
                pause_sec=args.pause_sec,
                account_profile=account_profile,
            )
            record_milestone(pipeline_dir, "stop2_blind_audio", "relock-voice 音轨重新锁定完成")
        elif args.mode == "reedit-visuals":
            if not (pipeline_dir / "03_audio_events.json").exists():
                raise FileNotFoundError("reedit-visuals 模式要求 03_audio_events.json 已锁定存在。")
            _ensure_reedit_dependencies(pipeline_dir, track=args.track, bgm_p=bgm_p, pause_sec=args.pause_sec, account_profile=account_profile, preserve_locked_audio=True)
            print("[pipeline] 只改画面模式：Step 1–3 已锁定音轨保持原封不动，仅按音轨事件重排画面。")

        res = run_visual_to_delivery(
            pipeline_dir=pipeline_dir,
            track=args.track,
            j_cut_frames=j_cut_frames,
            subtitle_template=subtitle_template,
            lut_name=lut_name,
            prefer_broll_only=eff_prefer_broll_only,
            benchmark=bench_p,
            simulate_jy_fail=args.simulate_jy_fail,
            simulate_hf_fail=args.simulate_hf_fail,
            preview_only=(args.mode == "lock-preview"),
            style_id=active_style_id,
            account_profile=account_profile,
            dialect=args.dialect,
            store_anchor=args.store_anchor,
            require_lock=args.require_lock,
            strict_asr=args.strict_asr,
            export_mode=args.exports,
            edit_profile=edit_profile,
            licenses_path=licenses_path,
            hook_variants=args.hook_variants,
            ws=ws,
            sync_window=args.sync_window,
        )

    if lock_files:
        locked_after = [sha256_file(path) for path in lock_files]
        if locked_before != locked_after:
            raise RuntimeError("只改画面过程中锁定分轨指纹发生变化，已阻止归档。")
        write_json(pipeline_dir / "08_locked_audio_receipt.json", {
            "mode": args.mode,
            "tracks": [{"path": str(path), "before_sha256": digest, "after_sha256": digest}
                       for path, digest in zip(lock_files, locked_after)],
        })
    if args.mode != "lock-preview" and not res["qa_report"]["all_passed"]:
        print(f"[ERROR] 必检失败：{res['qa_report']['blocking_checks']}，详见 10_qa_report.md")
        sys.exit(2)

    if args.mode != "lock-preview":
        record_milestone(pipeline_dir, "stop3_final", res["qa_report"]["approval_status"])
    prog_card = render_progress_card(pipeline_dir, track=args.track, write_files=True)
    if args.mode != "lock-preview":
        tidy_workspace(pipeline_dir, out_dir=ws["out_dir"], keep_temp=args.keep_temp)

    print("\n[OK] 流水线执行完毕。")
    print("\n" + prog_card["markdown_card"])


if __name__ == "__main__":
    main()

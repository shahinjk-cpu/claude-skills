#!/usr/bin/env python3
"""Export the edited timeline as native, independently editable HyperFrames clips."""

from __future__ import annotations

import argparse
import html
import re
import shutil
import tempfile
from html.parser import HTMLParser
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    ASSETS_DIR,
    HYPERFRAMES_VERSION,
    sha256_file,
    DEFAULT_FPS,
    SAFE_ZONE,
    SUBTITLE_CENTER_X,
    SUBTITLE_SAFE_ZONE,
    SUBTITLE_SYMMETRIC_MAX_W,
    compute_segment_cache_key,
    contrast_ratio,
    find_bin,
    find_commercial_font,
    frames_to_sec,
    get_wav_duration_sec,
    hex_to_rgba,
    is_verified_commercial_font,
    link_or_copy,
    load_style_applied,
    load_subtitle_templates,
    maybe_reexec_in_venv,
    place_bbox_in_zone,
    read_json,
    resolve_audio_stems,
    sec_to_frames,
    write_json,
)

if __name__ == "__main__":
    maybe_reexec_in_venv()

from export_jianying import _export_graded_segment
from render_mp4 import build_graded_segment_cmd, compute_subtitle_place_xy, _resolve_packaging_palette


def _clamp_window(start_sec: float, end_sec: float, max_sec: float) -> Tuple[float, float]:
    s = max(0.0, round(float(start_sec), 4))
    e = min(max_sec, round(float(end_sec), 4))
    return s, e


def _safe_id(raw: str, prefix: str = "item") -> str:
    cleaned = "".join(ch if (ch.isalnum() or ch in ("-", "_")) else "_" for ch in str(raw or ""))
    return f"{prefix}_{cleaned}" if not cleaned or cleaned[0].isdigit() else cleaned


def _measure_wav_sec(path_str: Optional[str]) -> float:
    if not path_str or not Path(path_str).is_file():
        return 0.0
    return get_wav_duration_sec(Path(path_str))


def attach_hyperframes_launchers(out_dir: Path, entry: str = "index.html") -> None:
    """Launch the official Studio editor from the project directory."""
    if entry != "index.html":
        return
    command = "\n".join([
        "#!/usr/bin/env bash", "set -euo pipefail",
        'export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"',
        'cd "$(dirname "$0")"',
        'if ! command -v npx >/dev/null 2>&1; then',
        '  echo "启动 HyperFrames Studio 需要 Node.js 22+。" >&2', '  exit 1', 'fi',
        'test -f index.html || { echo "工程缺少 index.html" >&2; exit 1; }',
        'if [ -n "${SVS_HYPERFRAMES_CLI:-}" ]; then',
        '  exec "$SVS_HYPERFRAMES_CLI" preview . "$@"',
        'fi',
        'for pkg in "${npm_config_cache:-$HOME/.npm}"/_npx/*/node_modules/hyperframes/package.json; do',
        '  [ -f "$pkg" ] || continue',
        f'  if [ "$(node -p \'require(process.argv[1]).version\' "$pkg")" = "{HYPERFRAMES_VERSION}" ]; then',
        '    exec node "${pkg%/*}/bin/hyperframes.mjs" preview . "$@"',
        '  fi',
        'done',
        f'exec npx --yes --prefer-offline hyperframes@{HYPERFRAMES_VERSION} preview . "$@"',
        "",
    ])
    mac = out_dir / "启动HyperFrames工程.command"
    mac.write_text(command, encoding="utf-8")
    mac.chmod(0o755)
    bat = "\r\n".join([
        "@echo off", "chcp 65001 >nul", 'cd /d "%~dp0"',
        'if not exist index.html (echo 工程缺少 index.html & exit /b 1)',
        'if defined SVS_HYPERFRAMES_CLI (',
        '  call "%SVS_HYPERFRAMES_CLI%" preview . %*',
        ') else (',
        '  where npx >nul 2>nul || (echo 启动 HyperFrames Studio 需要 Node.js 22+. & exit /b 1)',
        f'  call npx --yes --prefer-offline hyperframes@{HYPERFRAMES_VERSION} preview . %*',
        ')',
        'exit /b %errorlevel%', '',
    ])
    (out_dir / "启动HyperFrames工程.bat").write_bytes(bat.encode("utf-8"))


class StudioMarkup(HTMLParser):
    def __init__(self, path: Path):
        super().__init__(convert_charrefs=True)
        self.nodes: list[tuple[str, dict[str, str]]] = []
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))


def _archived_clips(draft: Path) -> dict[str, dict[str, str]]:
    result = {}
    for file in (draft / "index.html", draft / "compositions" / "video_track.html"):
        if file.is_file():
            for tag, attrs in StudioMarkup(file).nodes:
                if tag != "video" or not attrs.get("id") or not attrs.get("src"):
                    continue
                source = (file.parent / attrs["src"]).resolve()
                if source.is_relative_to(draft.resolve()) and source.is_file():
                    result[attrs["id"]] = {**attrs, "src": str(source)}
    return result


def _attrs(**values) -> str:
    return " ".join(f'{name.rstrip("_").replace("_", "-")}="{html.escape(str(value), quote=True)}"' for name, value in values.items())


def _asset_url(path: Path, root: Path) -> str:
    # Exported filenames use ASCII aliases so browsers and Studio resolve the same URL.
    return path.relative_to(root).as_posix()


def _asset_inventory(root: Path) -> dict[str, str]:
    return {file.relative_to(root).as_posix(): sha256_file(file) for file in sorted(root.rglob("*"))
            if file.is_file() and file.name not in ("studio_export.json", ".DS_Store")}


def _stage_font(font_path: Optional[str], fonts_dir: Path) -> Optional[Tuple[str, str]]:
    """仅 staging 经 common.is_verified_commercial_font 校验通过的网页可用字体 (.otf/.ttf/.woff2)。"""
    cand = font_path
    if not cand or not Path(cand).is_file() or Path(cand).suffix.lower() not in (".otf", ".ttf", ".woff2") or not is_verified_commercial_font(cand):
        cand = find_commercial_font(verified_only=True)
    if not cand or not Path(cand).is_file():
        return None
    src = Path(cand)
    ext = src.suffix.lower()
    if ext not in (".otf", ".ttf", ".woff2") or not is_verified_commercial_font(src):
        return None
    dst = fonts_dir / src.name
    link_or_copy(src, dst)
    fmt = "opentype" if ext == ".otf" else ("woff2" if ext == ".woff2" else "truetype")
    return f"media/fonts/{src.name}", fmt


def _build_video_clips(pipeline: Path, draft: Path, edl: dict, fps: int, total: float,
                       prepared_segments: bool) -> tuple[list[str], list[dict]]:
    clips = []
    items = []
    color_path = pipeline / "07_color_plan.json"
    color = read_json(color_path) if color_path.is_file() else {}
    by_clip = {plan["clip_id"]: plan.get("vf_filter") for plan in color.get("clip_plans", [])
               if plan.get("apply_color_grade")}
    manifest_path = pipeline / "01_manifest.json"
    media = read_json(manifest_path).get("items", []) if manifest_path.is_file() else []
    media_by_norm = {item["normalized_mp4"]: item for item in media}
    eyes = {item["normalized_mp4"]: item.get("eye_anchor") or {} for item in media}
    old = _archived_clips(pipeline / "hyperframes_draft")
    old_manifest = pipeline / "hyperframes_draft" / "studio_export.json"
    old_sources = {}
    if old_manifest.is_file():
        old_sources = {item["id"]: item for item in read_json(old_manifest).get("video", [])}
    sources: dict[str, str] = {}
    ffmpeg = find_bin("ffmpeg")

    for index, shot in enumerate(edl.get("clips", []), 1):
        cid = str(shot.get("clip_id") or f"seg_{index:03d}")
        stable_id = f"track-video-{_safe_id(cid)}"
        media_path = str(shot.get("media_path") or "")
        source = Path(media_path)
        start, end = _clamp_window(shot["timeline_in_sec"], shot["timeline_out_sec"], total)
        length = round(end - start, 4)
        if length <= 0:
            raise ValueError(f"分镜 {cid} 的时间范围为空")
        trim = max(0.0, float(shot.get("source_in_sec", 0)))
        source_length = float(shot.get("source_out_sec", trim + length)) - trim
        vf = shot.get("color_filter") or by_clip.get(cid)
        pip_cfg = shot.get("pip_layout") if isinstance(shot.get("pip_layout"), dict) else None
        needs_bake = bool(vf or shot.get("ken_burns") or shot.get("vf_extra") or pip_cfg or source_length < length - 0.01)
        original_url = sources.get(media_path)
        if not original_url and source.is_file():
            original = draft / "media" / "sources" / f"source_{len(sources) + 1:03d}{source.suffix.lower()}"
            link_or_copy(source, original)
            original_url = sources[media_path] = _asset_url(original, draft)
        if not original_url:
            old_source = old_sources.get(stable_id, {}).get("original_src")
            original = pipeline / "hyperframes_draft" / str(old_source or "")
            if old_source and original.resolve().is_relative_to((pipeline / "hyperframes_draft").resolve()) and original.is_file():
                destination = draft / old_source
                link_or_copy(original, destination)
                original_url = _asset_url(destination, draft)
            else:
                # A previously cleaned export may still have the camera source for replacing the baked shot.
                raw = Path(media_by_norm.get(media_path, {}).get("source_path") or "")
                if raw.is_file():
                    destination = draft / "media" / "sources" / f"source_{len(sources) + 1:03d}{raw.suffix.lower()}"
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(raw, destination)
                    original_url = _asset_url(destination, draft)
            if original_url:
                sources[media_path] = original_url

        if not source.is_file():
            archived = old.get(stable_id)
            if not archived or abs(float(archived["data-start"]) - start) > 0.001 or abs(float(archived["data-duration"]) - length) > 0.001:
                raise FileNotFoundError(f"分镜 {cid} 缺可用源片，且旧包没有同时间范围的媒体")
            destination = draft / "media" / "segments" / f"edit_{index:03d}{Path(archived['src']).suffix.lower()}"
            link_or_copy(Path(archived["src"]), destination)
            active = _asset_url(destination, draft)
            media_start = float(archived.get("data-media-start", "0"))
        elif needs_bake:
            destination = draft / "media" / "segments" / f"edit_{index:03d}.mp4"
            destination.parent.mkdir(parents=True, exist_ok=True)
            prepared = pipeline / "_render_final" / f"seg_{index - 1:03d}_f.mp4"
            lut_p = str(color.get("lut_path") or "")
            seg_flag = prepared.with_suffix(".sha256")
            cache_valid = False
            if prepared_segments and ffmpeg and prepared.is_file() and seg_flag.is_file():
                expected_cmd = build_graded_segment_cmd(ffmpeg, shot, vf, eyes, prepared, fps)
                expected_key = compute_segment_cache_key({
                    "cmd": expected_cmd[:-1],
                    "source_hash": sha256_file(source),
                    "lut_hash": sha256_file(Path(lut_p)) if lut_p and Path(lut_p).is_file() else None,
                    "fps": fps,
                    "preview": False,
                })
                cache_valid = seg_flag.read_text(encoding="utf-8").strip() == expected_key
            if cache_valid:
                link_or_copy(prepared, destination)
            elif ffmpeg:
                _export_graded_segment(ffmpeg, shot, vf, eyes, destination, fps)
            else:
                raise RuntimeError("保留分镜调色和推近效果需要 FFmpeg")
            active, media_start = _asset_url(destination, draft), 0.0
        else:
            active, media_start = original_url, trim

        label = f"分镜 {index:02d}"
        pip_mode_str = str((pip_cfg or {}).get("mode") or "none")
        attrs = _attrs(id=stable_id, class_="clip picture", src=active, data_start=f"{start:.4f}",
                       data_duration=f"{length:.4f}", data_media_start=f"{media_start:.4f}",
                       data_track_index=0, data_label=label, data_pip_mode=pip_mode_str)
        clips.append(f"    <video {attrs} muted playsinline preload=\"metadata\"></video>")
        items.append({"id": stable_id, "label": label, "src": active, "original_src": original_url,
                      "original_in_sec": trim, "original_out_sec": shot.get("source_out_sec"),
                      "start_sec": start, "duration_sec": length, "baked_picture": needs_bake,
                      "pip_mode": pip_mode_str})
    if not clips:
        raise ValueError("HyperFrames 工程没有视频分镜")
    return clips, items


def _position(bbox: dict, zone: dict, fallback: tuple[int, int], width: int, height: int) -> str:
    x, y = place_bbox_in_zone({"final_bbox": bbox}, width, height, zone, fallback)
    return f"left:{x}px;top:{y}px;width:{width}px;height:{height}px;"


def _build_graphics(draft: Path, package: dict, fps: int, total: float, style_id: str) -> tuple[list[str], int]:
    elems = list(package.get("visual_elements") or [])
    pal = _resolve_packaging_palette(style_id)
    def color(name: str) -> str:
        return "#" + "".join(f"{part:02x}" for part in pal[name])
    built = []
    native_text = 0
    for index, elem in enumerate(elems, 1):
        start, end = _clamp_window(frames_to_sec(int(elem["start_frame"]), fps),
                                   frames_to_sec(int(elem["end_frame"]), fps), total)
        if end <= start:
            continue
        text = str(elem.get("text_or_asset") or elem.get("text") or "").strip()
        raw_img_ref = elem.get("custom_png")
        image = Path(str(raw_img_ref)) if raw_img_ref else Path(text)
        bbox = elem.get("final_bbox") or elem.get("bbox") or {}
        width = max(1, min(SAFE_ZONE["x_max"] - SAFE_ZONE["x_min"], int(bbox.get("w") or 400)))
        height = max(1, min(SAFE_ZONE["y_max"] - SAFE_ZONE["y_min"], int(bbox.get("h") or 100)))
        pos = _position(bbox, SAFE_ZONE, (88, 210), width, height)
        cid = f"graphics-{index:03d}-{_safe_id(str(elem.get('id') or 'item'))}"
        attrs = _attrs(id=cid, data_start=f"{start:.4f}", data_duration=f"{end-start:.4f}",
                       data_track_index=1, data_track_kind="graphics", data_label=f"包装 {index:02d}")
        is_image_asset = bool(
            raw_img_ref
            or (image.suffix.lower() in {".svg", ".png", ".jpg", ".jpeg", ".webp"} and image.is_file())
        )
        if is_image_asset:
            if not image.is_file():
                raise FileNotFoundError(f"缺少包装素材 {image}")
            out = draft / "media" / "overlays" / f"graphic_{index:03d}{image.suffix.lower()}"
            link_or_copy(image, out)
            built.append(f'    <img {attrs} class="clip graphic-image" style="{pos}" src="{_asset_url(out, draft)}" alt="">')
            continue
        if not text:
            continue
        kind = elem.get("kind") or elem.get("type")
        if kind == "persistent_top_bar":
            fg_col = str(elem.get("fg_hex") or "#FFF589")
            pill_bg = (18, 22, 28)
            if contrast_ratio(hex_to_rgba(fg_col, 255)[:3], pill_bg) < 4.5:
                fg_col = "#FFF589"
            word_size = max(24, min(36, int((width - 36) / max(1, len(text)))))
            paint = (
                f"font-size:{word_size}px;color:{fg_col};"
                f"background:rgba(18,22,28,0.86);border:2px solid {fg_col};border-radius:999px;"
                "padding:8px 24px;"
            )
            built.append(f'    <div {attrs} class="clip graphic-text" style="{html.escape(pos + paint, quote=True)}">'
                         f'<span id="{cid}-text">{html.escape(text)}</span></div>')
            native_text += 1
            continue
        bare = kind in ("center_burst_title", "stamp_tag", "end_card_cta", "quote_citation_card") or elem.get("overlay_mode") == "borderless"
        req_giant_fs = int(elem.get("font_size_px") or 136) if kind == "center_burst_title" else 66
        target_sz = min(148, max(88, req_giant_fs)) if kind == "center_burst_title" else (62 if kind in ("end_card_cta", "quote_citation_card") else (54 if bare else 42))
        word_size = max(24, min(target_sz, int((width - 20) / max(1, min(6, len(text))))))
        raw_fg = str(elem.get("fg_hex") or color("text"))
        if not bare and contrast_ratio(hex_to_rgba(raw_fg, 255)[:3], pal["bg"][:3]) < 4.5:
            raw_fg = color("text")
        elif bare and contrast_ratio(hex_to_rgba(raw_fg, 255)[:3], (16, 20, 28)) < 4.5:
            raw_fg = "#FFE28A"
        stroke_css_w = (16 if kind == "center_burst_title" else 12) if bare else 0
        paint = (f"font-size:{word_size}px;color:{raw_fg};"
                 f"paint-order:stroke fill;-webkit-text-stroke:{stroke_css_w}px {elem.get('stroke_hex') or '#000'};"
                 + ("text-shadow:4px 5px 10px rgba(0,0,0,0.88);" if bare else ""))
        fill = ""
        if kind == "quote_citation_card":
            fill = f"background:rgba(14,18,26,0.90);border:3px solid {raw_fg};border-left:10px solid {elem.get('accent_hex') or '#FF4D4F'};border-radius:20px;padding:10px 22px;"
        elif not bare:
            fill = f"background:{color('bg')};border:2px solid {color('border')};border-left:9px solid {color('accent')};border-radius:18px;"
            if elem.get("overlay_mode") == "focus_blur":
                fill += "backdrop-filter:blur(10px);"
        sub = _escape_subtext(elem.get("subtext"))
        g_mode = str(elem.get("giant_mode") or "")
        extra_attrs = f' data-giant-mode="{html.escape(g_mode)}"' if g_mode else ""
        if g_mode == "giant_numeric_trio":
            chars = list(text.replace(" ", "")[:3])
            inner_html = "".join(
                f'<span style="display:inline-block;padding:6px 14px;margin:0 4px;background:rgba(16,20,28,0.92);'
                f'border:3px solid {raw_fg};border-radius:14px;">{html.escape(ch)}</span>'
                for ch in chars
            )
        elif g_mode == "giant_dual_clash":
            fill += "transform:rotate(-2.5deg);background:rgba(16,20,28,0.88);padding:8px 20px;border-radius:16px;"
            inner_html = f'<span id="{cid}-text">{html.escape(text)}</span>'
        elif g_mode == "giant_vertical_seal":
            fill += f"background:rgba(180,28,28,0.92);border:3px solid #FFF589;border-radius:14px;padding:12px 18px;"
            inner_html = f'<span id="{cid}-text">{html.escape(text)}</span>'
        else:
            inner_html = f'<span id="{cid}-text">{html.escape(text)}</span>'
        burst_tags = [str(t).strip() for t in (elem.get("burst_tags") or []) if str(t).strip()]
        tags_html = ""
        if burst_tags:
            tags_html = '<div style="margin-top:8px;display:flex;gap:8px;justify-content:center;">' + "".join(
                f'<span style="font-size:24px;padding:4px 12px;border-radius:999px;background:rgba(18,22,28,0.9);'
                f'border:2px solid {raw_fg};color:#fff;-webkit-text-stroke:0px;">{html.escape(tg)}</span>'
                for tg in burst_tags[:3]
            ) + "</div>"
        built.append(f'    <div {attrs}{extra_attrs} class="clip graphic-text" style="{html.escape(pos + paint + fill, quote=True)}">'
                     f'{inner_html}{sub}{tags_html}</div>')
        native_text += 1
    return built, native_text


def _escape_subtext(value: Any) -> str:
    return f'<span class="graphic-subtext">{html.escape(str(value))}</span>' if value else ""


def _hex_has_alpha(hex_str: str) -> bool:
    s = str(hex_str or "").strip().lower()
    return bool(s and s != "none" and not (len(s.lstrip("#")) == 8 and s.lstrip("#").endswith("00")))


def _build_captions_track_html(
    subs: Dict[str, Any],
    templates: Dict[str, Any],
    track_index: int,
    font_info: Optional[Tuple[str, str]],
    total_dur: float,
) -> Tuple[str, List[str]]:
    tpl_id = subs.get("template_id") or "style_01"
    base_tpl = templates.get(tpl_id) or next(iter(templates.values()))
    tpl = {**base_tpl, **subs["template_config"]} if isinstance(subs.get("template_config"), dict) else dict(base_tpl)

    c_primary = str(tpl.get("primary_color", "#FFFFFF"))
    c_kw = str(tpl.get("keyword_color", "#FFE066"))
    c_stroke = str(tpl.get("stroke_color", "#0D1117"))
    orig_stroke_w = int(tpl.get("stroke_width", 4))
    font_sz = max(24, int(tpl.get("font_size", 58)))
    kw_scale = float(tpl.get("keyword_scale", 1.15))
    bg_hex = str(tpl.get("bg_box_color") or tpl.get("bg_box") or "none")
    bg_radius = int(tpl.get("bg_radius", 16))
    bg_css = f"background: {bg_hex}; padding: 12px 24px; border-radius: {bg_radius}px;" if _hex_has_alpha(bg_hex) else ""

    font_css = ""
    font_stack = "sans-serif"
    if font_info:
        f_url, f_fmt = font_info
        font_css = (
            "      @font-face {\n"
            '        font-family: "CustomStudioFont";\n'
            f'        src: url("{f_url}") format("{f_fmt}");\n'
            "        font-display: swap;\n"
            "      }\n"
        )
        font_stack = f'"CustomStudioFont", {font_stack}'

    stroke_css = "0px" if orig_stroke_w <= 0 else f"{max(1, orig_stroke_w * 2)}px {c_stroke}"
    shadow_css = "text-shadow: 2px 3px 6px rgba(0,0,0,0.68);" if tpl.get("shadow", True) else ""

    css = "\n".join([
        font_css,
        "      .cap-clip { position: absolute; display: flex; align-items: center; justify-content: center; text-align: center; overflow: visible; }",
        f"      .cap-box {{ display: inline-flex; flex-wrap: wrap; align-items: baseline; justify-content: center; max-width: {SUBTITLE_SYMMETRIC_MAX_W}px; "
        f"font-family: {font_stack}; font-size: {font_sz}px; font-weight: 800; line-height: 1.18; "
        f"color: {c_primary}; paint-order: stroke fill; -webkit-text-stroke: {stroke_css}; {shadow_css} {bg_css} }}",
        f"      .cap-kw {{ color: {c_kw}; font-size: {int(round(font_sz * kw_scale))}px; }}",
    ])

    body_lines: List[str] = []
    max_sub_w = SUBTITLE_SYMMETRIC_MAX_W  # 640px ([220, 860]，绝对正中 540px)

    for idx, sub in enumerate(subs.get("entries") or [], start=1):
        if sub.get("suppressed"):
            continue
        st_s, en_s = _clamp_window(float(sub.get("start_sec", 0.0)), float(sub.get("end_sec", 0.0)), total_dur)
        dur_s = round(max(0.04, en_s - st_s), 4)

        fb = sub.get("final_bbox") or sub.get("bbox")
        if isinstance(fb, dict) and {"x", "y", "w", "h"}.issubset(fb.keys()):
            bw = min(max_sub_w, max(160, int(fb["w"])))
            bx = SUBTITLE_CENTER_X - bw // 2
            bh = min(SUBTITLE_SAFE_ZONE["y_max"] - SUBTITLE_SAFE_ZONE["y_min"], max(48, int(fb["h"])))
            by = max(SUBTITLE_SAFE_ZONE["y_min"], min(int(fb["y"]), SUBTITLE_SAFE_ZONE["y_max"] - bh))
        else:
            bw, bh = max_sub_w, 84
            bx, by = compute_subtitle_place_xy(bw, bh, tpl)
            by = max(SUBTITLE_SAFE_ZONE["y_min"], min(by, SUBTITLE_SAFE_ZONE["y_max"] - bh))

        text = str(sub.get("text") or "")
        sub_words = sub.get("words") or []
        words_joined = "".join(str(w.get("word") or "") for w in sub_words)
        if sub_words and re.sub(r"\s+", "", words_joined) == re.sub(r"\s+", "", text):
            span_parts: List[str] = []
            for w in sub_words:
                wt = str(w.get("word") or "")
                if not wt:
                    continue
                if w.get("is_keyword"):
                    span_parts.append(f'<span class="cap-kw">{html.escape(wt)}</span>')
                else:
                    span_parts.append(html.escape(wt))
            spans = "".join(span_parts)
        else:
            multi_kws = {str(v) for v in sub.get("keywords") or [] if v and (len(str(v)) >= 2 or str(v).isdigit())}
            if multi_kws:
                pattern = "(" + "|".join(re.escape(k) for k in sorted(multi_kws, key=lambda k: (-len(k), k))) + ")"
                spans = "".join(
                    f'<span class="cap-kw">{html.escape(part)}</span>' if part in multi_kws else html.escape(part)
                    for part in re.split(pattern, text)
                )
            else:
                spans = html.escape(text)

        sid = _safe_id(str(sub.get("id") or f"sub_{idx:03d}"), "sub")
        body_lines.append(
            f'      <div class="clip cap-clip" id="track-captions-{sid}" data-track-kind="captions" data-label="字幕 {idx:02d}" '
            f'style="left:{bx}px;top:{by}px;width:{bw}px;min-height:{bh}px;height:auto;" '
            f'data-start="{st_s:.4f}" data-duration="{dur_s:.4f}" data-track-index="{track_index}">'
            f'<span class="cap-box">{spans}</span></div>'
        )

    return css, body_lines


def _build_audio_clips(pipeline: Path, draft: Path, audio: dict, package: dict, mix: dict, total: float) -> tuple[list[str], list[dict]]:
    stems = resolve_audio_stems(pipeline, audio_events=audio, mix_metrics=mix)
    clips, inventory = [], []
    for track, role, label in ((3, "voice", "人声"), (4, "bgm", "背景音乐"), (5, "sfx", "音效")):
        source = stems.get(role)
        if not source:
            continue
        dst = draft / "media" / "audio" / f"{role}{source.suffix.lower()}"
        link_or_copy(source, dst)
        active_length = min(total, _measure_wav_sec(str(source)))
        if active_length <= 0:
            raise ValueError(f"{label}分轨为空")
        windows = []
        if role == "voice":
            # Preserve the processed speech and gaps, while making each sentence a separate clip.
            last = 0.0
            for index, sentence in enumerate(audio.get("sentences", []), 1):
                start = min(active_length, max(last, float(sentence["start_sec"])))
                end = min(active_length, max(start, float(sentence["end_sec"])))
                if start - last >= 0.001:
                    windows.append((last, start, f"间隔 {index:02d}"))
                if end - start >= 0.001:
                    windows.append((start, end, f"人声 {index:02d}"))
                last = end
            if windows and active_length - last >= 0.001:
                windows.append((last, active_length, "人声尾音"))
        if role == "sfx":
            cues = sorted(package.get("sfx_cues") or [], key=lambda cue: cue.get("onset_time_sec", cue.get("time_sec", 0)))
            starts = [max(0.0, float(cue.get("onset_time_sec", cue.get("time_sec", 0)))) for cue in cues]
            for index, (start, cue) in enumerate(zip(starts, cues)):
                cue_duration = _measure_wav_sec(cue.get("file"))
                boundary = starts[index + 1] if index + 1 < len(starts) else active_length
                end = min(active_length, boundary, start + cue_duration if cue_duration else boundary)
                if end - start >= 0.001:
                    windows.append((start, end, f"音效 {index + 1:02d}"))
        if not windows:
            windows = [(0.0, active_length, label)]
        volume = 0.2 if role == "bgm" and "08_bgm_ducked" not in source.name else 1.0
        for index, (start, end, item_label) in enumerate(windows, 1):
            clip_id = f"audio-{role}-{index:03d}"
            uri = _asset_url(dst, draft)
            attrs = _attrs(id=clip_id, data_label=item_label, src=uri, data_track_index=track,
                           data_start=f"{start:.4f}", data_duration=f"{end - start:.4f}",
                           data_media_start=f"{start:.4f}", data_volume=volume)
            clips.append(f"    <audio {attrs}></audio>")
            inventory.append({"id": clip_id, "role": role, "src": uri})
    if not {item["role"] for item in inventory} >= {"voice", "bgm"}:
        raise FileNotFoundError("缺少人声或背景音乐分轨")
    if package.get("sfx_cues") and not any(item["role"] == "sfx" for item in inventory):
        raise FileNotFoundError("有音效计划但缺少音效分轨")
    return clips, inventory


def _build_root_index_html(proj_slug: str, total: float, fps: int, clips: list[str], captions_css: str) -> str:
    body = "\n".join(clips)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width={CANVAS_WIDTH}, height={CANVAS_HEIGHT}">
  <title>{html.escape(proj_slug)} · HyperFrames</title>
  <style>
    * {{ box-sizing:border-box; }}
    html, body {{ margin:0; width:{CANVAS_WIDTH}px; height:{CANVAS_HEIGHT}px; overflow:hidden; background:#000; }}
    #main {{ position:relative; width:100%; height:100%; overflow:hidden; font-family:CustomStudioFont,sans-serif; }}
    .clip {{ position:absolute; }}
    .picture {{ inset:0; width:100%; height:100%; object-fit:cover; z-index:1; }}
    .graphic-image {{ object-fit:contain; z-index:30; }}
    .graphic-text {{ display:flex; flex-direction:column; align-items:center; justify-content:center; text-align:center;
                     padding:4px 8px; font-weight:800; line-height:1.08; paint-order:stroke fill; z-index:30; }}
    .graphic-subtext {{ font-size:0.52em; margin-top:4px; color:#fff; }}
    .cap-clip {{ z-index:40; }}
{captions_css}
  </style>
</head>
<body>
  <div id="main" data-composition-id="main" data-no-timeline data-start="0" data-duration="{total:.4f}" data-fps="{fps}"
       data-width="{CANVAS_WIDTH}" data-height="{CANVAS_HEIGHT}">
{body}
  </div>
</body>
</html>
"""


def _write_project(pipeline: Path, draft: Path, prepared_segments: bool) -> dict:
    def load(name: str) -> dict:
        path = pipeline / name
        return read_json(path) if path.is_file() else {}

    edl = read_json(pipeline / "04_edl.json")
    fps = int(edl.get("fps") or DEFAULT_FPS)
    duration = frames_to_sec(edl.get("total_frames") or sec_to_frames(edl["total_duration_sec"], fps), fps)
    subtitles, package = load("05_subtitles.json"), load("06_packaging.json")
    default_font = ASSETS_DIR / "fonts" / "AlimamaShuHeiTi-Bold.otf"
    font = _stage_font(subtitles.get("font_path") or str(default_font), draft / "media" / "fonts")
    if not font:
        raise FileNotFoundError("工程缺少可打包的本地字体")
    templates = load_subtitle_templates()
    caption_css, captions = _build_captions_track_html(subtitles, templates, 2, font, duration)
    style = package.get("style_id") or load_style_applied(pipeline) or "style_01"
    graphics, graphic_texts = _build_graphics(draft, package, fps, duration, style)
    video, shots = _build_video_clips(pipeline, draft, edl, fps, duration, prepared_segments)
    audios, audio_items = _build_audio_clips(
        pipeline, draft, load("03_audio_events.json"), package, load("08_mix_metrics.json"), duration
    )

    name = pipeline.parent.name if pipeline.name == "pipeline" else pipeline.name
    entry = draft / "index.html"
    entry.write_text(_build_root_index_html(name, duration, fps, video + graphics + captions + audios, caption_css), encoding="utf-8")
    write_json(draft / "hyperframes.json", {
        "$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
        "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "media"},
        "media": {"autoProxy": True},
    })
    attach_hyperframes_launchers(draft)
    counts = {"video": len(shots), "graphics": len(graphics), "graphic_text": graphic_texts,
              "captions": len(captions), "audio": len(audio_items)}
    receipt = {
        "format": "svs-hyperframes-studio-v2", "cli_version": HYPERFRAMES_VERSION,
        "entry_sha256": sha256_file(entry), "duration_sec": duration, "fps": fps, "counts": counts,
        "video": shots, "audio": audio_items,
    }
    (draft / "README_HyperFrames使用说明.txt").write_text(
        f"{name} · HyperFrames Studio\n\n"
        "双击工程启动器，或在本目录运行 npx hyperframes preview .。\n"
        "时间线中的分镜、字幕、人声片段、背景音乐与音效可以分别选择和调整。\n"
        "生成的标题和花字可以在画布上改字。导入图片可以移动、缩放和替换。\n"
        "已做调色或推近的分镜使用切好的画面。media/sources 保留可取得的完整素材，"
        "studio_export.json 记录它与分镜的对应关系。\n",
        encoding="utf-8",
    )
    receipt["files_sha256"] = _asset_inventory(draft)
    write_json(draft / "studio_export.json", receipt)
    return receipt


def export_hyperframes_draft(pipeline_dir: Path, simulate_failure: bool = False,
                             prepared_segments: bool = False) -> Dict[str, Any]:
    draft_dir = pipeline_dir / "hyperframes_draft"
    try:
        if simulate_failure:
            raise RuntimeError("模拟 HyperFrames 工程导出失败")
        with tempfile.TemporaryDirectory(prefix=".hf-export-", dir=pipeline_dir) as tmp:
            staged = Path(tmp) / "project"
            staged.mkdir()
            receipt = _write_project(pipeline_dir, staged, prepared_segments)
            previous = None
            backup_path = None
            if draft_dir.exists():
                prior_receipt = draft_dir / "studio_export.json"
                existing_entry = draft_dir / "index.html"
                managed = (prior_receipt.is_file() and existing_entry.is_file() and
                           read_json(prior_receipt).get("files_sha256") == _asset_inventory(draft_dir))
                if managed:
                    previous = Path(tmp) / "previous"
                else:
                    backup_path = Path(tempfile.mkdtemp(prefix="hyperframes_backup-", dir=pipeline_dir))
                    previous = backup_path / "project"
                draft_dir.rename(previous)
            try:
                staged.rename(draft_dir)
            except OSError:
                if previous:
                    previous.rename(draft_dir)
                raise

        counts = receipt["counts"]
        status = {
            "status": "success", "degraded_to_mp4_only": False, "offline_zero_cdn": True,
            "format": receipt["format"], "draft_dir": str(draft_dir.resolve()),
            "index_html": str((draft_dir / "index.html").resolve()),
            "segments_count": counts["video"], "captions_count": counts["captions"],
            "flower_texts_count": counts["graphic_text"], "audio_tracks_count": len({item["role"] for item in receipt["audio"]}),
            "audio_clips_count": counts["audio"], "previous_backup": str(backup_path) if backup_path else None,
            "message": f"已导出 Studio 工程，含 {counts['video']} 段画面、{counts['captions']} 条字幕和 {counts['audio']} 段音频。",
        }
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        status = {"status": "degraded_to_mp4_only", "degraded_to_mp4_only": True, "draft_dir": None,
                  "error": str(exc), "message": f"HyperFrames 工程导出失败：{exc}"}
    write_json(pipeline_dir / "hyperframes_export_status.json", status)
    print(f"[hyperframes] {status['message']}")
    return status


def main() -> None:
    maybe_reexec_in_venv()
    parser = argparse.ArgumentParser(description="导出原生 HyperFrames Studio 工程")
    parser.add_argument("--pipeline-dir", required=True, type=Path)
    parser.add_argument("--simulate-failure", action="store_true")
    args = parser.parse_args()
    result = export_hyperframes_draft(args.pipeline_dir, simulate_failure=args.simulate_failure)
    if result["status"] != "success":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
short-video-studio 公共工具模块
集中管理唯一权威常量、多账号隔离工作区、FFmpeg/FFprobe 调用、商用字体合规校验、
抗混叠多速率音频读写、双声道单边故障拯救、SFX 同窗审计、3D LUT/Style 解析与几何仿射映射。
"""

from __future__ import annotations

import functools
import hashlib
import importlib.util
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = SKILL_ROOT / "assets"
SCRIPTS_DIR = SKILL_ROOT / "scripts"
VENV_DIR = Path.home() / ".short-video-studio" / "venv"
NODE_TOOLS_DIR = Path.home() / ".short-video-studio" / "node_tools"
DEFAULT_WORKSPACE_ROOT = Path(
    os.environ.get("SVS_WORKSPACE_ROOT") or (Path.home() / ".short-video-studio" / "workspaces")
)

# 标准成片画布与安全区常量（1080x1920 @ 30fps，全仓唯一权威真相源）
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
DEFAULT_FPS = 30
TARGET_LUFS = -14.0
LOUDNESS_TOLERANCE_LUFS = 1.5
SCENE_CUT_THRESHOLD = 0.16
HYPERFRAMES_VERSION = "0.9.72"
EDITABLE_EXPORTS = ("jianying", "hyperframes")
EXPORT_CHOICES = ("auto", "mp4", "jianying", "hyperframes", "both")
EDIT_PROFILES = {
    "talking": {"opening_cuts": 2, "max_shot_sec": 8.0, "static_sec": 3.0, "hero_height_ratio": 0.33, "sentence_cut_gap": 0.85},
    "documentary": {"opening_cuts": 0, "max_shot_sec": 20.0, "static_sec": 12.0, "hero_height_ratio": 0.20, "sentence_cut_gap": 3.2},
    "explainer": {"opening_cuts": 1, "max_shot_sec": 14.0, "static_sec": 8.0, "hero_height_ratio": 0.28, "sentence_cut_gap": 1.8},
}


def export_selection(selection: str) -> Tuple[Tuple[str, ...], bool]:
    if selection == "mp4":
        return (), False
    if selection in ("auto", "both"):
        return EDITABLE_EXPORTS, selection == "both"
    if selection not in EDITABLE_EXPORTS:
        raise ValueError(f"未知交付格式：{selection}")
    return (selection,), True


def review_checks(checks: List[Dict[str, Any]], export_mode: str, strict_asr: bool) -> Tuple[List[str], List[str]]:
    _, exports_required = export_selection(export_mode)
    reviewable = {"bb_ocr_av_loop", "bb_pixel_readability", "bb_meta_leak_ocr"}
    if not strict_asr:
        reviewable.add("bb_blind_asr_proxy")
    blocking, manual = [], []
    for check in checks:
        cid, status = check["id"], check["status"]
        if status == "PASS" or (cid == "bb_export_contracts" and not exports_required):
            continue
        if status == "SKIPPED_UNAVAILABLE" and cid in reviewable:
            manual.append(cid)
        else:
            blocking.append(cid)
    return blocking, manual

# 平台 UI 遮挡区边界（任何关键文字/贴纸不得侵入）
SAFE_ZONE = {
    "x_min": 60,
    "x_max": 880,   # 避开右侧互动栏 (880, 1080]
    "y_min": 160,   # 避开顶部状态/搜索栏 [0, 160)
    "y_max": 1480,  # 避开底部文案/POI/进度条 (1480, 1920]
}

SUBTITLE_SAFE_ZONE = {
    "x_min": 80,
    "x_max": 860,
    "y_min": 1180,
    "y_max": 1468,
}

# 字幕绝对水平居中对称安全带：轴心恒定 540px，右不越 860px（避开右侧互动栏），对称区 [220, 860] 宽 640px
SUBTITLE_CENTER_X = CANVAS_WIDTH // 2
SUBTITLE_DEFAULT_Y_CENTER = 1310
SUBTITLE_SYMMETRIC_HALF_W = min(
    SUBTITLE_CENTER_X - SUBTITLE_SAFE_ZONE["x_min"],
    SUBTITLE_SAFE_ZONE["x_max"] - SUBTITLE_CENTER_X,
)
SUBTITLE_SYMMETRIC_MAX_W = SUBTITLE_SYMMETRIC_HALF_W * 2
SUBTITLE_SYMMETRIC_ZONE = {
    "x_min": SUBTITLE_CENTER_X - SUBTITLE_SYMMETRIC_HALF_W,
    "x_max": SUBTITLE_CENTER_X + SUBTITLE_SYMMETRIC_HALF_W,
    "y_min": SUBTITLE_SAFE_ZONE["y_min"],
    "y_max": SUBTITLE_SAFE_ZONE["y_max"],
}

# #20 SFX 2-8kHz 同窗净抬升审计唯一权威窗边界
SFX_AUDIT_PRE_SEC = 0.04
SFX_AUDIT_POST_SEC = 0.16

MEDIA_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm"}

BT709_FFMPEG_ARGS = [
    "-pix_fmt", "yuv420p",
    "-color_range", "tv",
    "-colorspace", "bt709",
    "-color_primaries", "bt709",
    "-color_trc", "bt709",
]

BT709_VF_SUFFIX = [
    "setsar=1",
    "scale=out_color_matrix=bt709:out_range=tv",
    "format=yuv420p",
    "setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709",
]

# 全仓统一的 BT.709 健康肤色矢量扇区（用于 Step 7 掩膜校色与 #15 黑盒示波器校验）
SKIN_YCBCR_RANGE = {
    "cb_min": 86.0,
    "cb_max": 132.0,
    "cr_min": 128.0,
    "cr_max": 174.0,
}

# 全仓统一的制作元数据与开发词防露馅禁用正则集（#11 与 #17 共享）
LEAK_REGEX_PATTERNS = [
    r"\bDJI_\d+",
    r"\bIMG_\d+",
    r"\bMVI_\d+",
    r"\bDSC_\d+",
    r"第\d+遍",
    r"口述稿?",
    r"提词器?",
    r"(?:STYLE|style)[_-]?\d+",
    r"暗黑科技",
    r"强反差财经",
    r"高级感杂志",
    r"高密口播",
    r"电影感空间",
    r"纸张拼贴",
    r"流派模板",
    r"风格谱",
    r"颠覆对比钩子",
    r"数字痛点钩子",
    r"悬念反问钩子",
]

# 经核验的免费/OFL 可商用中文字体文件名白名单前缀（绝不包含 STHeiti/PingFang/微软雅黑）
VERIFIED_COMMERCIAL_FONT_STEMS = (
    "alimamashuheiti",
    "sourcehansans",
    "sourcehanserif",
    "notosanssc",
    "notosanscjk",
    "notoserifsc",
    "notoserifcjk",
    "smileysans",
    "qingsongshouxieti",
    "lxgw",
    "opposans",
    "harmonyos",
)

_FONT_CACHE: Dict[Tuple[str, ...], Optional[str]] = {}


def get_preferred_python() -> str:
    """若当前不在专用 venv 且专用 venv 存在，返回其解释器路径。"""
    candidates = [
        VENV_DIR / "bin" / "python",
        VENV_DIR / "Scripts" / "python.exe",
    ]
    for p in candidates:
        if p.exists():
            return str(p)
    return sys.executable


def maybe_reexec_in_venv(extra_modules: Tuple[str, ...] = ()) -> None:
    """若核心渲染/声学包或指定扩展包缺失且专用 venv 可用，自动切换至专用 venv 执行。"""
    required = ("PIL", "numpy", "scipy", "edge_tts", *extra_modules)
    missing = any(importlib.util.find_spec(m) is None for m in required)
    if not missing:
        return

    preferred = get_preferred_python()
    if os.path.abspath(preferred) != os.path.abspath(sys.executable) and os.environ.get("SVS_IN_VENV") != "1":
        env = os.environ.copy()
        env["SVS_IN_VENV"] = "1"
        os.execvpe(preferred, [preferred, *sys.argv], env)


def find_bin(name: str) -> Optional[str]:
    """查找二进制可执行文件（ffmpeg / ffprobe / node / npm / uv 等）。"""
    return shutil.which(name)


def run_cmd(cmd: List[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
    """统一 UTF-8 子进程执行封装，失败时提供清晰命令上下文。"""
    res = subprocess.run(
        cmd,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if check and res.returncode != 0:
        err_tail = (res.stderr or "")[-1200:]
        raise RuntimeError(f"命令执行失败 ({res.returncode}): {' '.join(cmd)}\n{err_tail}")
    return res


@functools.lru_cache(maxsize=1)
def _ffmpeg_filter_set() -> frozenset[str]:
    ffmpeg = find_bin("ffmpeg")
    if not ffmpeg:
        return frozenset()
    res = subprocess.run(
        [ffmpeg, "-hide_banner", "-filters"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    filters = set()
    for line in (res.stdout or "").splitlines():
        parts = line.split()
        if len(parts) >= 2:
            filters.add(parts[1])
    return frozenset(filters)


def ffmpeg_has_filter(filter_name: str) -> bool:
    """带缓存检测当前 ffmpeg 是否编译了指定滤镜（如 subtitles / drawtext / lut3d / zscale）。"""
    return filter_name in _ffmpeg_filter_set()


def ffprobe_media(media_path: Path) -> Dict[str, Any]:
    """调用 ffprobe 获取视频/音频流的详细元数据（含 side_data_list 旋转矩阵）。"""
    path = media_path.resolve()
    stat = path.stat()
    return json.loads(_probe_media_json(str(path), stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns))


@functools.lru_cache(maxsize=256)
def _probe_media_json(path: str, inode: int, size: int, modified_ns: int, changed_ns: int) -> str:
    ffprobe = find_bin("ffprobe")
    if not ffprobe:
        raise RuntimeError("未找到 ffprobe，请先运行 check_and_setup.py 安装 ffmpeg。")
    cmd = [
        ffprobe, "-v", "quiet",
        "-print_format", "json",
        "-show_format", "-show_streams",
        path,
    ]
    res = run_cmd(cmd)
    return res.stdout or "{}"


def parse_fps(rate_str: str) -> float:
    """把 '30000/1001' 或 '30/1' 转换为浮点数帧率，非法字符串安全返回 0.0。"""
    s = str(rate_str or "").strip()
    if not s or s == "0/0":
        return 0.0
    try:
        if "/" in s:
            num, den = s.split("/", 1)
            den_f = float(den)
            return float(num) / den_f if den_f else 0.0
        return float(s)
    except ValueError:
        return 0.0


def detect_vfr_hdr(probe_data: Dict[str, Any]) -> Dict[str, Any]:
    """统一从 ffprobe 数据解算 VFR 与 HDR 元数据（消除 inventory 与 step1 重复逻辑）。"""
    v_stream = next((s for s in probe_data.get("streams", []) if s.get("codec_type") == "video"), {})
    avg_fps = parse_fps(str(v_stream.get("avg_frame_rate") or "0/1"))
    r_fps = parse_fps(str(v_stream.get("r_frame_rate") or "0/1"))
    is_vfr = abs(avg_fps - r_fps) > 1.0 or (r_fps > 120.0 and avg_fps > 0.0)
    trc = str(v_stream.get("color_transfer") or "").lower()
    primaries = str(v_stream.get("color_primaries") or "").lower()
    pix_fmt = str(v_stream.get("pix_fmt") or "").lower()
    c_space = str(v_stream.get("color_space") or "").lower()
    was_hdr = any(k in trc for k in ("arib-std-b67", "smpte2084", "hlg")) or ("bt2020" in primaries)
    tags_blob = " ".join(
        f"{k}:{v}" for d in (probe_data.get("format", {}).get("tags") or {}, v_stream.get("tags") or {})
        for k, v in d.items()
    ).lower() + f" {trc} {primaries} {c_space}"
    log_profile: Optional[str] = None
    if "apple" in tags_blob and "log" in tags_blob:
        log_profile = "apple_log"
    elif "slog" in tags_blob or "s-log" in tags_blob:
        log_profile = "slog3"
    elif "dlog" in tags_blob or "d-log" in tags_blob:
        log_profile = "dlog"
    elif "clog" in tags_blob or "c-log" in tags_blob:
        log_profile = "clog"
    return {
        "v_stream": v_stream,
        "avg_fps": avg_fps,
        "r_fps": r_fps,
        "is_vfr": is_vfr,
        "was_hdr": was_hdr,
        "log_profile": log_profile,
        "pix_fmt": pix_fmt,
        "color_transfer": trc,
        "color_primaries": primaries,
        "color_space": c_space,
    }


def parse_video_stream_geometry(v_stream: Dict[str, Any]) -> Dict[str, Any]:
    """
    从 ffprobe 视频流读取 coded_w/coded_h 与 side_data_list/tags 中的旋转角度，
    输出旋转矫正后的真实展示宽高 (display_w, display_h) 与方向判定。
    """
    coded_w = int(v_stream.get("width") or 0)
    coded_h = int(v_stream.get("height") or 0)
    rotation = 0
    for sd in v_stream.get("side_data_list", []) or []:
        if isinstance(sd, dict) and sd.get("rotation") is not None:
            try:
                rotation = int(round(float(sd["rotation"])))
                break
            except Exception:
                pass
    if rotation == 0:
        tag_rot = (v_stream.get("tags") or {}).get("rotate")
        if tag_rot is not None:
            try:
                rotation = int(round(float(tag_rot)))
            except Exception:
                rotation = 0
    rot_norm = abs(rotation) % 360
    if rot_norm in (90, 270):
        display_w, display_h = coded_h, coded_w
    else:
        display_w, display_h = coded_w, coded_h
    orientation = "portrait" if display_h >= display_w else "landscape"
    return {
        "coded_width": coded_w,
        "coded_height": coded_h,
        "rotation_deg": rotation,
        "display_width": display_w,
        "display_height": display_h,
        "orientation": orientation,
    }


def compute_centered_crop_frac(
    norm_subject_pos: float,
    scaled_dim: int,
    dst_dim: int,
    target_norm_pos: float = 0.5,
) -> float:
    """将源图归一化主体位置精确映射到裁切窗比例，使主体真正落在目标画布的 target_norm_pos 处（修复恒等失效 Bug）。"""
    max_shift = max(0, int(scaled_dim) - int(dst_dim))
    if max_shift <= 0:
        return 0.5
    desired_crop = float(norm_subject_pos) * float(scaled_dim) - float(target_norm_pos) * float(dst_dim)
    return max(0.0, min(1.0, desired_crop / float(max_shift)))


def compute_crop_transform(
    display_w: int,
    display_h: int,
    dst_w: int = CANVAS_WIDTH,
    dst_h: int = CANVAS_HEIGHT,
    crop_x_frac: float = 0.5,
    crop_y_frac: float = 0.5,
) -> Dict[str, Any]:
    """计算 scale(increase) + crop 到目标画布的确定性仿射变换参数。"""
    dw = max(1, int(display_w or dst_w))
    dh = max(1, int(display_h or dst_h))
    scale = max(float(dst_w) / float(dw), float(dst_h) / float(dh))
    scaled_w = max(dst_w, int(round(dw * scale)))
    scaled_h = max(dst_h, int(round(dh * scale)))
    if scaled_w % 2 == 1:
        scaled_w += 1
    if scaled_h % 2 == 1:
        scaled_h += 1
    max_cx = max(0, scaled_w - dst_w)
    max_cy = max(0, scaled_h - dst_h)
    crop_x = int(round(max_cx * max(0.0, min(1.0, crop_x_frac))))
    crop_y = int(round(max_cy * max(0.0, min(1.0, crop_y_frac))))
    return {
        "src_w": dw,
        "src_h": dh,
        "scaled_w": scaled_w,
        "scaled_h": scaled_h,
        "crop_x": crop_x,
        "crop_y": crop_y,
        "dst_w": int(dst_w),
        "dst_h": int(dst_h),
    }


def map_norm_bbox_to_crop(
    bbox: Optional[Dict[str, float]],
    crop_tx: Dict[str, Any],
) -> Optional[Dict[str, float]]:
    """将裁切前显示画幅的归一化 {x, y, w, h} 精确仿射映射到目标 1080x1920 归一化坐标。"""
    if not isinstance(bbox, dict) or not crop_tx:
        return bbox
    sw = float(crop_tx["scaled_w"])
    sh = float(crop_tx["scaled_h"])
    cx = float(crop_tx["crop_x"])
    cy = float(crop_tx["crop_y"])
    dw = float(crop_tx["dst_w"])
    dh = float(crop_tx["dst_h"])
    x1 = (float(bbox.get("x", 0.0)) * sw - cx) / dw
    y1 = (float(bbox.get("y", 0.0)) * sh - cy) / dh
    x2 = ((float(bbox.get("x", 0.0)) + float(bbox.get("w", 0.0))) * sw - cx) / dw
    y2 = ((float(bbox.get("y", 0.0)) + float(bbox.get("h", 0.0))) * sh - cy) / dh
    cx1, cy1 = max(0.0, min(1.0, x1)), max(0.0, min(1.0, y1))
    cx2, cy2 = max(0.0, min(1.0, x2)), max(0.0, min(1.0, y2))
    if cx2 - cx1 < 0.015 or cy2 - cy1 < 0.015:
        return None
    return {
        "x": round(cx1, 4),
        "y": round(cy1, 4),
        "w": round(cx2 - cx1, 4),
        "h": round(cy2 - cy1, 4),
    }


def map_eye_anchor_to_crop(
    eye_anchor: Optional[Dict[str, Any]],
    crop_tx: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """将裁切前归一化双眼锚点映射至目标 1080x1920 画布，若被裁出画面外则返回 None。"""
    if not isinstance(eye_anchor, dict) or not crop_tx:
        return eye_anchor
    sw = float(crop_tx["scaled_w"])
    sh = float(crop_tx["scaled_h"])
    cx = float(crop_tx["crop_x"])
    cy = float(crop_tx["crop_y"])
    dw = float(crop_tx["dst_w"])
    dh = float(crop_tx["dst_h"])
    nx = (float(eye_anchor.get("eye_cx", eye_anchor.get("cx", 0.5))) * sw - cx) / dw
    ny = (float(eye_anchor.get("eye_cy", eye_anchor.get("cy", 0.35))) * sh - cy) / dh
    if not (0.02 <= nx <= 0.98 and 0.02 <= ny <= 0.98):
        return None
    out = dict(eye_anchor)
    out["eye_cx"] = round(nx, 4)
    out["eye_cy"] = round(ny, 4)
    out["cx"] = out["eye_cx"]
    out["cy"] = out["eye_cy"]
    return out


def parse_manifest_faces(
    item: Dict[str, Any],
    canvas_w: int = CANVAS_WIDTH,
    canvas_h: int = CANVAS_HEIGHT,
) -> List[Dict[str, int]]:
    """统一将 01_manifest.json 中的人脸框（支持归一化 dict/list 与像素坐标）转换为像素 {x, y, w, h}。"""
    out: List[Dict[str, int]] = []
    for f in item.get("faces", []) or []:
        bb = f.get("bbox") if isinstance(f, dict) and "bbox" in f else f
        if isinstance(bb, dict):
            vals = [float(bb.get("x", 0.0)), float(bb.get("y", 0.0)), float(bb.get("w", 0.0)), float(bb.get("h", 0.0))]
            if max(vals) <= 1.5:
                rx = int(round(vals[0] * canvas_w))
                ry = int(round(vals[1] * canvas_h))
                rw = int(round(vals[2] * canvas_w))
                rh = int(round(vals[3] * canvas_h))
            else:
                rx, ry, rw, rh = (int(round(v)) for v in vals)
        elif isinstance(bb, (list, tuple)) and len(bb) == 4:
            v = [float(x) for x in bb]
            if max(v) <= 1.5:
                x1, y1, x2, y2 = v[0] * canvas_w, v[1] * canvas_h, v[2] * canvas_w, v[3] * canvas_h
            else:
                x1, y1, x2, y2 = v
            rx = int(round(min(x1, x2)))
            ry = int(round(min(y1, y2)))
            rw = int(round(abs(x2 - x1)))
            rh = int(round(abs(y2 - y1)))
        else:
            continue
        x1 = max(0, min(int(canvas_w), rx))
        y1 = max(0, min(int(canvas_h), ry))
        x2 = max(0, min(int(canvas_w), rx + rw))
        y2 = max(0, min(int(canvas_h), ry + rh))
        nw, nh = x2 - x1, y2 - y1
        if nw > 4 and nh > 4:
            out.append({"x": x1, "y": y1, "w": nw, "h": nh})
    return out


def bbox_iou(b1: Dict[str, Any], b2: Dict[str, Any]) -> float:
    """全仓唯一共享的轴对齐包围盒交并比计算。"""
    if not b1 or not b2:
        return 0.0
    x1 = max(float(b1["x"]), float(b2["x"]))
    y1 = max(float(b1["y"]), float(b2["y"]))
    x2 = min(float(b1["x"]) + float(b1["w"]), float(b2["x"]) + float(b2["w"]))
    y2 = min(float(b1["y"]) + float(b1["h"]), float(b2["y"]) + float(b2["h"]))
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter <= 0.0:
        return 0.0
    area1 = max(1e-9, float(b1["w"]) * float(b1["h"]))
    area2 = max(1e-9, float(b2["w"]) * float(b2["h"]))
    return inter / max(1e-9, area1 + area2 - inter)


def place_bbox_in_zone(
    entry: Dict[str, Any],
    pw: int,
    ph: int,
    zone: Dict[str, int],
    default_xy: Tuple[int, int],
) -> Tuple[int, int]:
    """按 entry 的权威 final_bbox/bbox 居中贴合并严格钳制在目标安全区 zone 内。"""
    fb = entry.get("final_bbox") or entry.get("bbox")
    if isinstance(fb, dict) and {"x", "y", "w", "h"}.issubset(fb.keys()):
        bx = int(fb["x"]) + (int(fb["w"]) - pw) // 2
        by = int(fb["y"]) + (int(fb["h"]) - ph) // 2
        px = max(zone["x_min"], min(bx, zone["x_max"] - pw))
        py = max(zone["y_min"], min(by, zone["y_max"] - ph))
        return int(px), int(py)
    px = max(zone["x_min"], min(default_xy[0], zone["x_max"] - pw))
    py = max(zone["y_min"], min(default_xy[1], zone["y_max"] - ph))
    return int(px), int(py)


def hex_to_rgba(
    hex_str: Optional[str],
    default: Any = (255, 255, 255, 255),
    default_alpha: Optional[int] = None,
) -> Tuple[int, int, int, int]:
    """统一解析 #RGB / #RRGGBB / #RRGGBBAA 为 RGBA 元组（兼容传入 alpha int 或 default RGBA tuple）。"""
    if isinstance(default, int):
        eff_alpha = max(0, min(255, default))
        fallback: Tuple[int, int, int, int] = (255, 255, 255, eff_alpha)
    else:
        fb_raw = tuple(int(v) for v in default)
        eff_alpha = max(0, min(255, int(default_alpha))) if default_alpha is not None else (fb_raw[3] if len(fb_raw) >= 4 else 255)
        fallback = (
            fb_raw[0] if len(fb_raw) >= 1 else 255,
            fb_raw[1] if len(fb_raw) >= 2 else 255,
            fb_raw[2] if len(fb_raw) >= 3 else 255,
            eff_alpha,
        )
    if not hex_str:
        return fallback
    h = str(hex_str).strip().lstrip("#")
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    try:
        if len(h) == 6:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), eff_alpha)
        if len(h) == 8:
            return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), int(h[6:8], 16))
    except ValueError:
        pass
    return fallback


def contrast_ratio(c1: Tuple[int, int, int], c2: Tuple[int, int, int]) -> float:
    """计算两 RGB 颜色的 WCAG 2.1 相对亮度对比度 (1.0 ~ 21.0)。"""
    def _rel_lum(rgb: Tuple[int, int, int]) -> float:
        vals = []
        for ch in rgb[:3]:
            s = max(0.0, min(1.0, float(ch) / 255.0))
            vals.append(s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4)
        return 0.2126 * vals[0] + 0.7152 * vals[1] + 0.0722 * vals[2]
    l1 = _rel_lum(c1)
    l2 = _rel_lum(c2)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


@functools.lru_cache(maxsize=256)
def get_cached_font(font_path: Optional[str], size: int) -> Any:
    """进程级缓存的 Pillow FreeType 字体加载器，消除逐帧重复读取 OTF/TTF 磁盘 I/O。"""
    from PIL import ImageFont

    sz = max(12, int(size))
    if font_path and Path(font_path).is_file():
        try:
            return ImageFont.truetype(str(font_path), sz)
        except Exception:
            pass
    fallback = find_commercial_font(verified_only=True)
    if fallback:
        try:
            return ImageFont.truetype(fallback, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def fit_text_line(
    draw: Any,
    text: str,
    font_path: Optional[str],
    max_width: int,
    max_size: int,
    min_size: int = 18,
) -> Tuple[Any, str]:
    """统一下采样自适应单行文字宽度；极窄时智能加省略号，绝不溢出安全框。"""
    txt = str(text or "")
    eff_max_w = max(16, int(max_width))
    eff_min = max(8, int(min_size))
    eff_max = max(eff_min, int(max_size))
    for sz in range(eff_max, eff_min - 1, -2):
        fnt = get_cached_font(font_path, sz)
        w = draw.textlength(txt, font=fnt) if hasattr(draw, "textlength") else (draw.textbbox((0, 0), txt, font=fnt)[2] - draw.textbbox((0, 0), txt, font=fnt)[0])
        if w <= eff_max_w:
            return fnt, txt
    fnt = get_cached_font(font_path, eff_min)
    while len(txt) > 2:
        cand = txt[:-1] + "…"
        w = draw.textlength(cand, font=fnt) if hasattr(draw, "textlength") else (draw.textbbox((0, 0), cand, font=fnt)[2] - draw.textbbox((0, 0), cand, font=fnt)[0])
        if w <= eff_max_w:
            return fnt, cand
        txt = txt[:-1]
    return fnt, txt


def is_verified_commercial_font(font_path: Optional[Path | str]) -> bool:
    """严格判断字体文件是否属于已验证的开源/免费商用白名单（绝不把 PingFang/STHeiti/微软雅黑标为可商用）。"""
    if not font_path:
        return False
    p = Path(font_path)
    low = p.stem.lower().replace("-", "").replace("_", "").replace(" ", "")
    return any(stem in low for stem in VERIFIED_COMMERCIAL_FONT_STEMS)


def _font_search_dirs() -> List[Path]:
    dirs: List[Path] = [ASSETS_DIR / "fonts"]
    sys_name = platform.system()
    if sys_name == "Darwin":
        dirs += [
            Path.home() / "Library" / "Fonts",
            Path("/Library/Fonts"),
            Path("/System/Library/Fonts"),
            Path("/System/Library/Fonts/Supplemental"),
        ]
    elif sys_name == "Windows":
        win_dir = Path(os.environ.get("WINDIR", "C:\\Windows"))
        dirs += [
            win_dir / "Fonts",
            Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Fonts",
        ]
    else:
        dirs += [
            Path.home() / ".local" / "share" / "fonts",
            Path("/usr/share/fonts"),
            Path("/usr/local/share/fonts"),
        ]
    return dirs


def find_commercial_font(
    candidates: Optional[List[str]] = None,
    verified_only: bool = True,
    allow_fallback: bool = True,
) -> Optional[str]:
    """
    跨平台查找中文字体（带结果缓存）：
    默认 verified_only=True，严格优先随仓与本地开源/免费商用字体，杜绝误用系统私有版权字体。
    传 allow_fallback=False 时仅检查 candidates 中明确指定的字体，不拼接默认兜底池。
    """
    default_verified = [
        "AlimamaShuHeiTi-Bold.otf",
        "SmileySans-Oblique.ttf",
        "SourceHanSerifCN-Heavy.otf",
        "SourceHanSerifCN-Bold.otf",
        "SourceHanSansCN-Bold.otf",
        "SourceHanSansCN-Medium.otf",
        "SourceHanSansCN-Regular.otf",
        "QingSongShouXieTi1.ttf",
        "QingSongShouXieTi2.ttf",
        "NotoSansCJKsc-Bold.otf",
        "NotoSansCJKsc-Regular.otf",
        "NotoSansSC-Bold.ttf",
        "NotoSansSC-Medium.ttf",
        "NotoSansSC-Regular.ttf",
    ]
    fallback_system = [
        "PingFang.ttc",
        "STHeiti Medium.ttc",
        "msyhbd.ttc",
        "msyh.ttc",
        "simhei.ttf",
    ]
    if allow_fallback or not candidates:
        pool = list(default_verified) if verified_only else (list(default_verified) + fallback_system)
        names = list(candidates or []) + [c for c in pool if not candidates or c not in candidates]
    else:
        names = list(candidates)
    if verified_only:
        names = [n for n in names if is_verified_commercial_font(n)]
        if allow_fallback and "AlimamaShuHeiTi-Bold.otf" not in names:
            names.append("AlimamaShuHeiTi-Bold.otf")

    cache_key = (str(verified_only), str(allow_fallback), *names)
    if cache_key in _FONT_CACHE:
        return _FONT_CACHE[cache_key]

    search_dirs = _font_search_dirs()
    for font_name in names:
        cand_path = Path(str(font_name)).expanduser()
        if cand_path.is_file() and (not verified_only or is_verified_commercial_font(cand_path)):
            _FONT_CACHE[cache_key] = str(cand_path)
            return _FONT_CACHE[cache_key]
        for d in search_dirs:
            if not d.exists():
                continue
            direct = d / font_name
            if direct.is_file():
                _FONT_CACHE[cache_key] = str(direct)
                return _FONT_CACHE[cache_key]
            for sub in d.glob(f"**/{font_name}"):
                if sub.is_file():
                    _FONT_CACHE[cache_key] = str(sub)
                    return _FONT_CACHE[cache_key]
    return None


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(data, ensure_ascii=False, indent=2)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        pending = Path(handle.name)
        try:
            handle.write(encoded)
            handle.flush()
        except OSError:
            handle.close()
            pending.unlink(missing_ok=True)
            raise
    try:
        pending.replace(path)
    finally:
        pending.unlink(missing_ok=True)
    return path


def load_subtitle_templates() -> Dict[str, Any]:
    tpl_path = ASSETS_DIR / "subtitle_templates" / "templates.json"
    raw = read_json(tpl_path).get("templates", {})
    return {k: v for k, v in raw.items() if isinstance(v, dict)}


def load_style_applied(pipeline_dir: Path) -> Optional[str]:
    """统一读取已绑定的 style_spectrum_applied.json 中的 style_id。"""
    spec_p = pipeline_dir / "style_spectrum_applied.json"
    if spec_p.exists():
        try:
            sid = read_json(spec_p).get("style_id")
            return str(sid) if sid else None
        except Exception:
            return None
    return None


def load_style_spectrum_entry(style_id: str) -> Optional[Dict[str, Any]]:
    """统一查询 style_spectrum_library.json 中的风格条目。"""
    lib_p = ASSETS_DIR / "style_spectrum" / "style_spectrum_library.json"
    if not lib_p.exists():
        return None
    try:
        lib = read_json(lib_p)
        for s in lib.get("styles", []):
            if s.get("style_id") == style_id:
                return s
    except Exception:
        return None
    return None


def load_animation_sfx_pairs() -> Dict[str, Any]:
    """读取内置 83 组 0ms 动画×音效配对字典。"""
    p = ASSETS_DIR / "style_spectrum" / "animation_sfx_pairs.json"
    return read_json(p) if p.is_file() else {"animation_lookup": {}, "pairs": []}


def load_sfx_intent_taxonomy() -> Dict[str, Any]:
    """读取内置 29 场景×92 音效叙事意图分类表。"""
    p = ASSETS_DIR / "style_spectrum" / "sfx_intent_taxonomy.json"
    return read_json(p) if p.is_file() else {"pipeline_emotion_routing": {}, "scene_taxonomy": {}}


def load_typography_cover_rules() -> Dict[str, Any]:
    """读取内置四色高亮与 3:4 封面四构图排版规则。"""
    p = ASSETS_DIR / "style_spectrum" / "typography_cover_rules.json"
    return read_json(p) if p.is_file() else {"golden_highlight_palette": {}, "cover_3x4_layouts": {}}


def resolve_lut_path(lut_name: Optional[str], style_id: Optional[str] = None) -> Path:
    """单源 LUT 解析：优先从 style_spectrum/luts 解析 24 套风格 LUT，次选内置通用 LUT。"""
    if style_id:
        sp = ASSETS_DIR / "style_spectrum" / "luts" / f"{style_id}.cube"
        if sp.exists():
            return sp
        print(f"[WARN] 未找到风格 LUT {sp}，尝试回退通用 LUT", file=sys.stderr)
    if lut_name:
        cand1 = ASSETS_DIR / "style_spectrum" / "luts" / lut_name
        if cand1.exists():
            return cand1
        cand2 = ASSETS_DIR / "luts" / lut_name
        if cand2.exists():
            return cand2
        print(f"[WARN] 未找到指定 LUT {lut_name}，回退 clean_creator.cube", file=sys.stderr)
    return ASSETS_DIR / "luts" / "clean_creator.cube"


def write_cube_lut(out_path: Path, lut_arr: Any, size: int, title: str) -> Path:
    """统一写出 3D .cube LUT 文件。"""
    import numpy as np

    arr = np.clip(np.asarray(lut_arr, dtype=np.float32).reshape(-1, 3), 0.0, 1.0)
    header = [
        f'TITLE "{title}"',
        f"LUT_3D_SIZE {int(size)}",
        "DOMAIN_MIN 0.0 0.0 0.0",
        "DOMAIN_MAX 1.0 1.0 1.0",
    ]
    body = [f"{r:.6f} {g:.6f} {b:.6f}" for r, g, b in arr]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(header + body) + "\n", encoding="utf-8")
    return out_path


def link_or_copy(src: Path, dst: Path) -> Path:
    """跨文件统一的同卷硬链接、失败退化拷贝辅助函数。"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    try:
        os.link(src.resolve(), dst)
    except OSError:
        shutil.copy2(src.resolve(), dst)
    return dst


def resolve_audio_stems(
    pipeline_dir: Path,
    audio_events: Optional[Dict[str, Any]] = None,
    mix_metrics: Optional[Dict[str, Any]] = None,
) -> Dict[str, Optional[Path]]:
    """
    三端同源解析分轨路径：优先使用均乘同一 master_gain_db 的 08 分轨（含 08_sfx_master.wav），
    缺失时才兼容回退上游原始分轨。
    """
    mix = mix_metrics if mix_metrics is not None else (
        read_json(pipeline_dir / "08_mix_metrics.json") if (pipeline_dir / "08_mix_metrics.json").exists() else {}
    )
    ae = audio_events if audio_events is not None else (
        read_json(pipeline_dir / "03_audio_events.json") if (pipeline_dir / "03_audio_events.json").exists() else {}
    )

    def _pick(*cands: Optional[str | Path]) -> Optional[Path]:
        for c in cands:
            if not c:
                continue
            p = Path(c)
            if p.is_file() and p.stat().st_size > 44:
                return p
        return None

    voice = _pick(mix.get("voice_master_wav"), pipeline_dir / "08_voice_master.wav", ae.get("locked_voice_wav"), pipeline_dir / "03_locked_voice.wav")
    bgm = _pick(mix.get("bgm_ducked_wav"), pipeline_dir / "08_bgm_ducked.wav", ae.get("locked_bgm_wav"), pipeline_dir / "03_locked_bgm.wav")
    sfx = _pick(mix.get("sfx_master_wav"), pipeline_dir / "08_sfx_master.wav", pipeline_dir / "06_sfx_track.wav")
    return {"voice": voice, "bgm": bgm, "sfx": sfx}


def compute_sfx_band_windows(
    cues: List[Dict[str, Any]],
    nosfx_mono: Any,
    sr: int,
) -> List[Dict[str, Any]]:
    """
    全仓唯一的 #20 SFX 2-8kHz 同窗基准计算器（Step 8 落盘与黑盒裁判 #20 共用，消除口径撕裂）：
    全量 cues + 统一窗口 [t_ref - 0.04, t_ref + 0.16] + 同一 4 阶零相位 2-8kHz 带通。
    """
    import numpy as np

    if not cues or len(nosfx_mono) < 128 or importlib.util.find_spec("scipy") is None:
        return []
    try:
        from scipy.signal import butter, sosfiltfilt
        hi_hz = min(8000.0, float(sr) * 0.48)
        lo_hz = min(2000.0, hi_hz * 0.5)
        sos = butter(4, [lo_hz, hi_hz], btype="bandpass", fs=sr, output="sos")
        hb_base = sosfiltfilt(sos, np.asarray(nosfx_mono, dtype=np.float64))
    except Exception:
        return []

    rows: List[Dict[str, Any]] = []
    n_len = len(hb_base)
    for idx, cue in enumerate(cues):
        t_ref = float(cue.get("peak_time_sec") or cue.get("time_sec") or 0.0)
        i0 = max(0, int(round((t_ref - SFX_AUDIT_PRE_SEC) * sr)))
        i1 = min(n_len, int(round((t_ref + SFX_AUDIT_POST_SEC) * sr)))
        if i1 - i0 < 64:
            continue
        r_no = float(np.sqrt(np.mean(hb_base[i0:i1] ** 2) + 1e-12))
        rows.append({
            "sfx_id": cue.get("id") or f"sfx_{idx + 1:03d}",
            "sfx_name": cue.get("sfx_name"),
            "win_start_sec": round(i0 / float(sr), 4),
            "win_end_sec": round(i1 / float(sr), 4),
            "nosfx_2_8k_rms": round(r_no, 10),
        })
    return rows


def rescue_stereo_channels(arr: Any, imbalance_db: float = 8.0) -> Tuple[Any, str]:
    """
    检测口播双声道 L/R 是否存在无线麦单边失效/极度衰减/纯杂音故障：
    若单侧高于另一侧 >= imbalance_db 且较强侧具有真实语音能量（>-42dBFS），
    自动复制完好单声道至双声道，防止 `.mean(axis=1)` 被坏道拉低或污染。
    """
    import numpy as np

    a = np.asarray(arr, dtype=np.float32)
    if a.ndim != 2 or a.shape[1] < 2 or len(a) < 256:
        return a, "ok"
    rms_l = float(np.sqrt(np.mean(a[:, 0] ** 2) + 1e-12))
    rms_r = float(np.sqrt(np.mean(a[:, 1] ** 2) + 1e-12))
    db_l = 20.0 * math.log10(max(1e-7, rms_l))
    db_r = 20.0 * math.log10(max(1e-7, rms_r))
    if db_l - db_r >= imbalance_db and db_l > -42.0:
        return np.column_stack([a[:, 0], a[:, 0]]).astype(np.float32), "left_rescued"
    if db_r - db_l >= imbalance_db and db_r > -42.0:
        return np.column_stack([a[:, 1], a[:, 1]]).astype(np.float32), "right_rescued"
    return a, "ok"


def get_wav_duration_sec(audio_path: Path) -> float:
    """准确获取音频时长（支持 .wav/.m4a/.mp3，异常或压缩容器自动交由 ffprobe）。"""
    if not audio_path.exists():
        return 0.0
    if audio_path.suffix.lower() == ".wav":
        try:
            with wave.open(str(audio_path), "rb") as wf:
                n_frames = wf.getnframes()
                sr = wf.getframerate()
                return n_frames / float(sr) if sr > 0 else 0.0
        except Exception:
            pass
    try:
        info = ffprobe_media(audio_path)
        return float(info.get("format", {}).get("duration") or 0.0)
    except Exception:
        return 0.0


def read_wav_as_48k_stereo(audio_path: Path, target_sr: int = 48000) -> Tuple[Any, int]:
    """
    通吃 .wav / .m4a / .mp3 / .aac 等任意采样率/位深/声道数的音频，
    统一抗混叠重采样为 float32 [-1, 1] 的双声道 target_sr 数组 (N, 2)。
    """
    import numpy as np

    arr: Optional[np.ndarray] = None
    src_sr = 0
    if audio_path.suffix.lower() == ".wav":
        try:
            with wave.open(str(audio_path), "rb") as wf:
                ch = wf.getnchannels()
                sw = wf.getsampwidth()
                src_sr = wf.getframerate()
                comptype = wf.getcomptype()
                raw = wf.readframes(wf.getnframes())
            if comptype == "NONE" and sw in (1, 2, 3, 4) and src_sr > 0:
                if sw == 1:
                    a = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
                elif sw == 2:
                    a = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                elif sw == 3:
                    b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
                    i32 = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
                    i32 = np.where(i32 & 0x800000, i32 - 0x1000000, i32)
                    a = i32.astype(np.float32) / 8388608.0
                else:
                    a = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
                a = a.reshape(-1, ch)
                if ch == 1:
                    arr = np.column_stack([a[:, 0], a[:, 0]])
                elif ch >= 2:
                    arr = a[:, :2]
        except Exception:
            arr = None

    if arr is not None and src_sr != target_sr and len(arr) > 0:
        g = math.gcd(int(src_sr), int(target_sr))
        up = int(target_sr) // g
        down = int(src_sr) // g
        if importlib.util.find_spec("scipy") is None or max(up, down) > 200:
            arr = None
        else:
            from scipy.signal import resample_poly
            arr = resample_poly(arr, up, down, axis=0).astype(np.float32)

    if arr is None:
        ffmpeg = find_bin("ffmpeg")
        if not ffmpeg:
            raise RuntimeError(f"无法读取音频且缺少 ffmpeg: {audio_path}")
        res = subprocess.run(
            [
                ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(audio_path),
                "-f", "s16le", "-acodec", "pcm_s16le", "-ar", str(target_sr), "-ac", "2",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        usable = (len(res.stdout) // 4) * 4
        pcm = np.frombuffer(res.stdout[:usable], dtype=np.int16).astype(np.float32) / 32768.0
        return pcm.reshape(-1, 2), target_sr

    return np.ascontiguousarray(arr, dtype=np.float32), int(target_sr)


def write_wav_48k_stereo(
    wav_path: Path,
    arr: Any,
    sr: int = 48000,
    clip_limit: float = 0.985,
) -> Path:
    """全仓唯一权威 16-bit PCM 立体声 WAV 写盘器（自动扩充单声道、统一防削波硬限幅）。"""
    import numpy as np

    a = np.asarray(arr, dtype=np.float32)
    if a.ndim == 1:
        a = np.column_stack([a, a])
    elif a.ndim == 2 and a.shape[1] == 1:
        a = np.repeat(a, 2, axis=1)
    elif a.ndim == 2 and a.shape[1] > 2:
        a = a[:, :2]
    clipped = np.clip(a, -float(clip_limit), float(clip_limit))
    pcm = (clipped * 32767.0).astype(np.int16)
    wav_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(int(sr))
        wf.writeframes(pcm.tobytes())
    return wav_path


def measure_lufs_ebur128(media_path: Path, raise_on_error: bool = True) -> Dict[str, float]:
    """统一使用 ffmpeg ebur128 测量综合响度(I)、响度范围(LRA)与真峰值(TP)，绝不静默伪造假数值。"""
    ffmpeg = find_bin("ffmpeg")
    if not ffmpeg:
        if raise_on_error:
            raise RuntimeError("未找到 ffmpeg，无法测量 EBU R128 响度。")
        return {"integrated_lufs": -99.0, "lra_lu": 0.0, "true_peak_dbtp": -99.0, "valid": False}

    res = subprocess.run(
        [ffmpeg, "-hide_banner", "-nostats", "-vn", "-i", str(media_path), "-af", "ebur128=peak=true", "-f", "null", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    txt = res.stderr or ""
    summary_idx = txt.rfind("Summary:")
    scope = txt[summary_idx:] if summary_idx >= 0 else txt
    m_i = re.findall(r"I:\s*(-?[\d.]+|-inf)\s*LUFS", scope)
    m_lra = re.findall(r"LRA:\s*([\d.]+|-inf)\s*LU", scope)
    m_tp = re.findall(r"Peak:\s*(-?[\d.]+|-inf)\s*dBFS", scope)
    if not m_i:
        if raise_on_error:
            raise RuntimeError(f"ebur128 响度解析失败: {media_path}\n{txt[-400:]}")
        return {"integrated_lufs": -99.0, "lra_lu": 0.0, "true_peak_dbtp": -99.0, "valid": False}

    def _to_db(token: str, default_val: float) -> float:
        t = token.strip().lower()
        return default_val if t == "-inf" else float(t)

    return {
        "integrated_lufs": _to_db(m_i[-1], -99.0),
        "lra_lu": 0.0 if (not m_lra or m_lra[-1].strip().lower() == "-inf") else float(m_lra[-1]),
        "true_peak_dbtp": _to_db(m_tp[-1], -99.0) if m_tp else -1.5,
        "valid": True,
    }


def check_bbox_in_safe_zone(bbox: Dict[str, int]) -> Tuple[bool, str]:
    """按全仓唯一权威 SAFE_ZONE 校验元素包围盒是否进入平台 UI 遮挡区。"""
    x1 = int(bbox["x"])
    y1 = int(bbox["y"])
    x2 = x1 + int(bbox["w"])
    y2 = y1 + int(bbox["h"])

    if y1 < SAFE_ZONE["y_min"]:
        return False, f"顶部越界: y1={y1} < {SAFE_ZONE['y_min']}"
    if y2 > SAFE_ZONE["y_max"]:
        return False, f"底部越界进入文案/进度条区: y2={y2} > {SAFE_ZONE['y_max']}"
    if x1 < SAFE_ZONE["x_min"]:
        return False, f"左侧越界: x1={x1} < {SAFE_ZONE['x_min']}"
    if x2 > SAFE_ZONE["x_max"]:
        return False, f"右侧越界进入互动按钮区: x2={x2} > {SAFE_ZONE['x_max']}"
    return True, "OK"


def sec_to_frames(sec: float, fps: int = DEFAULT_FPS) -> int:
    return int(round(sec * fps))


def frames_to_sec(frames: int, fps: int = DEFAULT_FPS) -> float:
    return round(frames / float(fps), 4)


def sanitize_slug(name: Optional[str], default: str = "default") -> str:
    """将账号名/项目名清洗为安全目录名，保留中文/字母/数字/下划线/短横线，禁止路径穿越。"""
    raw = str(name or "").strip()
    cleaned = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", raw).strip("._-")
    if not cleaned or cleaned in (".", ".."):
        return default
    return cleaned[:64]


def resolve_workspace_paths(
    account: Optional[str] = None,
    project_id: Optional[str] = None,
    project_dir: Optional[Path] = None,
    raw_dir: Optional[Path] = None,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    解析多账号物理隔离工作区与专属加工目录，并严格防止向用户原素材目录写入任何加工文件。
    目录结构：<workspace_root>/accounts/<account_slug>/{content-log/account_profile.json,compliance_whitelist.json,projects/<project_id>}
    """
    ws_root = (workspace_root or DEFAULT_WORKSPACE_ROOT).expanduser().resolve()
    acc_slug = sanitize_slug(account, default="default")
    account_dir = ws_root / "accounts" / acc_slug
    content_log_dir = account_dir / "content-log"

    raw_res = raw_dir.expanduser().resolve() if raw_dir else None
    if project_id:
        proj_slug = sanitize_slug(project_id, default="project")
    elif project_dir:
        proj_slug = sanitize_slug(project_dir.expanduser().resolve().name, default="project")
    elif raw_res:
        proj_slug = sanitize_slug(raw_res.name, default="project")
    else:
        proj_slug = "default_project"

    redirected = False
    if project_dir is not None:
        pd_res = project_dir.expanduser().resolve()
        if raw_res is not None and (pd_res == raw_res or raw_res in pd_res.parents):
            redirected = True
            eff_proj_dir = account_dir / "projects" / proj_slug
        else:
            eff_proj_dir = pd_res
    else:
        eff_proj_dir = account_dir / "projects" / proj_slug

    eff_raw_dir = raw_res if raw_res is not None else (eff_proj_dir / "raw_media")
    pipeline_dir = eff_proj_dir / "pipeline"
    if raw_res is not None and (pipeline_dir == raw_res or raw_res in pipeline_dir.parents):
        redirected = True
        eff_proj_dir = account_dir / "projects" / proj_slug
        pipeline_dir = eff_proj_dir / "pipeline"

    out_dir = eff_proj_dir / "out"
    if raw_res is not None:
        write_dirs = (pipeline_dir, out_dir, eff_proj_dir / "_demo_raw_media")
        for write_dir in write_dirs:
            resolved_dir = write_dir.resolve()
            if resolved_dir.is_relative_to(raw_res) or raw_res.is_relative_to(resolved_dir):
                raise ValueError(f"加工目录与原素材目录重叠：{resolved_dir}。请指定独立的加工目录。")

    account_profile_path = content_log_dir / "account_profile.json"
    legacy_prof = eff_proj_dir / "content-log" / "account_profile.json"
    if not account and not account_profile_path.exists() and legacy_prof.exists():
        account_profile_path = legacy_prof

    return {
        "workspace_root": ws_root,
        "account_slug": acc_slug,
        "account_dir": account_dir,
        "content_log_dir": content_log_dir,
        "account_profile_path": account_profile_path,
        "compliance_whitelist_path": account_dir / "compliance_whitelist.json",
        "project_id": proj_slug,
        "project_dir": eff_proj_dir,
        "pipeline_dir": pipeline_dir,
        "out_dir": out_dir,
        "raw_dir": eff_raw_dir,
        "redirected_from_raw": redirected,
    }


def compute_bt709_luma(rgb_arr: Any) -> Any:
    """全仓唯一权威 BT.709 亮度计算 (0.2126R + 0.7152G + 0.0722B)，杜绝 BT.601/709 系数混拼。"""
    return 0.2126 * rgb_arr[..., 0] + 0.7152 * rgb_arr[..., 1] + 0.0722 * rgb_arr[..., 2]


def estimate_read_hold_sec(text: str, min_sec: float = 1.5, max_sec: float = 8.0) -> float:
    """全仓唯一权威阅读停留时长估算（中文 4.5 字/秒 + 英文数字 15 字符/秒 + 1.35s 视觉落眼缓冲）。"""
    s = str(text or "")
    cjk_n = sum(1 for ch in s if "\u4e00" <= ch <= "\u9fff")
    other_n = sum(1 for ch in s if ch.isascii() and ch.isalnum())
    return round(max(min_sec, min(max_sec, cjk_n / 4.5 + other_n / 15.0 + 1.35)), 2)


@functools.lru_cache(maxsize=512)
def _sha256_file_cached(path_str: str, inode: int, size: int, mtime_ns: int, ctime_ns: int) -> str:
    h = hashlib.sha256()
    with open(path_str, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    p = path.resolve()
    st = p.stat()
    if st.st_size >= 1048576:
        return _sha256_file_cached(str(p), st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


_WHISPER_MODEL_CACHE: Dict[Tuple[str, str, str, bool], Any] = {}


def get_cached_whisper_model(
    model_size: str,
    device: str = "cpu",
    compute_type: str = "int8",
    local_files_only: bool = False,
) -> Any:
    """进程级单例缓存 faster-whisper 模型，消除同进程 Step 2 与 Step 10 重复冷加载。"""
    key = (str(model_size), str(device), str(compute_type), bool(local_files_only))
    if key not in _WHISPER_MODEL_CACHE:
        from faster_whisper import WhisperModel
        _WHISPER_MODEL_CACHE[key] = WhisperModel(
            model_size, device=device, compute_type=compute_type, local_files_only=local_files_only
        )
    return _WHISPER_MODEL_CACHE[key]


def _find_playwright_chromium_bin() -> Optional[str]:
    """扫描 Playwright 缓存目录中通过 `playwright-core install chromium` 下载的浏览器可执行文件。"""
    cache_roots: List[Path] = []
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        cache_roots.append(Path(os.environ["PLAYWRIGHT_BROWSERS_PATH"]).expanduser())
    cache_roots.extend([
        Path.home() / "Library" / "Caches" / "ms-playwright",
        Path.home() / ".cache" / "ms-playwright",
    ])
    if os.environ.get("LOCALAPPDATA"):
        cache_roots.append(Path(os.environ["LOCALAPPDATA"]) / "ms-playwright")

    patterns = (
        "chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium",
        "chromium-*/chrome-mac*/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing",
        "chromium_headless_shell-*/chrome-mac*/chrome-headless-shell",
        "chromium-*/chrome-linux*/chrome",
        "chromium_headless_shell-*/chrome-linux*/chrome-headless-shell",
        "chromium-*/chrome-win*/chrome.exe",
    )
    for root in cache_roots:
        if not root.is_dir():
            continue
        for pat in patterns:
            matches = sorted(root.glob(pat), reverse=True)
            for m in matches:
                if m.is_file():
                    return str(m)
    return None


def detect_browser_renderer() -> Dict[str, Any]:
    """只读探测 Node + playwright-core + 本机 Chrome/Chromium（含 Playwright 缓存与 Windows 路径）。"""
    node_bin = find_bin("node")
    pw_cands = [
        NODE_TOOLS_DIR / "node_modules" / "playwright-core",
        NODE_TOOLS_DIR / "node_modules" / "playwright",
    ]
    pw_path = next((str(p) for p in pw_cands if p.is_dir()), None)

    chrome_env = os.environ.get("SVS_CHROME_PATH")
    chrome_cands: List[str] = [
        *([chrome_env] if chrome_env else []),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    ]
    for env_key in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        base_d = os.environ.get(env_key)
        if base_d:
            chrome_cands.extend([
                str(Path(base_d) / "Google" / "Chrome" / "Application" / "chrome.exe"),
                str(Path(base_d) / "Microsoft" / "Edge" / "Application" / "msedge.exe"),
            ])
    chrome_bin = next((c for c in chrome_cands if c and Path(c).is_file()), None) or _find_playwright_chromium_bin()
    bridge = SCRIPTS_DIR / "capture_html_video.mjs"
    available = bool(node_bin and pw_path and chrome_bin and bridge.is_file())
    return {
        "available": available,
        "node_bin": node_bin,
        "playwright_core": pw_path,
        "chrome_bin": chrome_bin,
        "bridge_script": str(bridge) if bridge.is_file() else None,
    }


def get_huggingface_hub_dir() -> Path:
    """统一解析本地 HuggingFace Hub 缓存目录。"""
    if os.environ.get("HF_HUB_CACHE"):
        return Path(os.environ["HF_HUB_CACHE"]).expanduser()
    if os.environ.get("HF_HOME"):
        return Path(os.environ["HF_HOME"]).expanduser() / "hub"
    return Path.home() / ".cache" / "huggingface" / "hub"


def find_cached_whisper_model(hf_hub: Optional[Path] = None) -> Optional[str]:
    """按精度优先级探测本地已缓存的 faster-whisper 模型名。"""
    hub = hf_hub or get_huggingface_hub_dir()
    for cand in ("large-v3", "large-v3-turbo", "medium", "small", "base", "tiny"):
        d = hub / f"models--Systran--faster-whisper-{cand}"
        if (d / "snapshots").is_dir() and any((d / "snapshots").iterdir()):
            return cand
    return None


def compute_segment_cache_key(payload: Dict[str, Any]) -> str:
    """全仓共享的渲染与贴片缓存 SHA256 指纹生成器，杜绝参数变更后误复用过期缓存。"""
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:24]

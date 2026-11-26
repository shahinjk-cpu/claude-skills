#!/usr/bin/env python3
"""
[字体按用字子集化工具]
扫描工程源码/文案中实际出现的字符，结合常用标点与数字，调用 fontTools.subset (desubroutinize=True)
将大体积中文 OTF/TTF 压缩为几十 KB 的轻量项目内嵌字体，彻底规避无头 Chrome CFF 校验失败导致的静默字体回退。
若环境未安装 fontTools，则自动安全回退为复制原字体并给出提示。
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

BASE_KEEP_CHARS = (
    "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    " !?.,:;+-*/=%()[]{}<>\"'—…·"
    "，。！？、；：“”‘’（）《》【】—·％℃倍年天月日时分秒元块万亿"
)

SCAN_EXTS = {".html", ".htm", ".js", ".mjs", ".ts", ".tsx", ".json", ".md", ".txt", ".ass", ".srt"}


def collect_project_chars(scan_roots: Iterable[Path], extra_text: str = "") -> str:
    chars: Set[str] = set(BASE_KEEP_CHARS) | set(str(extra_text or ""))
    for root in scan_roots:
        p = Path(root)
        if not p.exists():
            continue
        files = [p] if p.is_file() else [f for f in p.rglob("*") if f.is_file()]
        for fp in files:
            if fp.suffix.lower() not in SCAN_EXTS or fp.name == "stage_clock.js":
                continue
            try:
                chars.update(fp.read_text(encoding="utf-8", errors="ignore"))
            except Exception:
                continue
    return "".join(sorted(ch for ch in chars if ord(ch) >= 32))


def subset_font_file(
    font_in: Path,
    font_out: Path,
    text_chars: str,
) -> Dict[str, Any]:
    src = Path(font_in).expanduser().resolve()
    dst = Path(font_out).expanduser().resolve()
    if not src.is_file():
        raise FileNotFoundError(f"字体文件不存在: {src}")
    dst.parent.mkdir(parents=True, exist_ok=True)
    orig_bytes = src.stat().st_size

    try:
        from fontTools import subset as ft_subset
        from fontTools.ttLib import TTFont

        options = ft_subset.Options()
        options.desubroutinize = True
        options.layout_features = ["*"]
        options.name_IDs = ["*"]
        options.hinting = False

        font = TTFont(str(src))
        subsetter = ft_subset.Subsetter(options=options)
        subsetter.populate(text=text_chars)
        subsetter.subset(font)
        font.save(str(dst))
        font.close()
        new_bytes = dst.stat().st_size
        return {
            "status": "subsetted",
            "source": str(src),
            "output": str(dst),
            "char_count": len(set(text_chars)),
            "original_bytes": orig_bytes,
            "subset_bytes": new_bytes,
            "saved_pct": round((1.0 - new_bytes / max(1, orig_bytes)) * 100.0, 2),
        }
    except ImportError:
        shutil.copy2(src, dst)
        return {
            "status": "copied_fallback_no_fonttools",
            "source": str(src),
            "output": str(dst),
            "char_count": len(set(text_chars)),
            "original_bytes": orig_bytes,
            "subset_bytes": dst.stat().st_size,
            "hint": "未安装 fonttools，已完整拷贝原字体；如需子集化压缩可执行 pip install fonttools",
        }


def main() -> None:
    ap = argparse.ArgumentParser(description="按项目实际用字子集化字体（防无头浏览器字体解析失败）")
    ap.add_argument("--font", required=True, help="原始 TTF/OTF 字体路径")
    ap.add_argument("--out", required=True, help="输出子集字体路径")
    ap.add_argument("--scan", nargs="*", default=[], help="扫描提取用字的目录或文件")
    ap.add_argument("--extra", default="", help="额外强制保留的字符串")
    args = ap.parse_args()

    chars = collect_project_chars([Path(p) for p in args.scan], extra_text=args.extra)
    res = subset_font_file(Path(args.font), Path(args.out), chars)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

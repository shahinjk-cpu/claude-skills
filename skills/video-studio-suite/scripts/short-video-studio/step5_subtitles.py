#!/usr/bin/env python3
"""
[Step 5: 字幕生成与统一权威布局]
1. 读取锁定音轨 03_audio_events.json 的逐字时间戳，结合 terms.txt 保护词与词边界动态规划（DP）切分清爽单行短句。
2. 修复数字旁中文标点残留（仅保住夹在数字间的小数点 . 与时间冒号 : 以及数字后 %），尊重模板 punct_stripped 配置。
3. 基于唯一权威 SUBTITLE_SAFE_ZONE 与 01_manifest.json 裁切后精确人脸框一次性完成像素测宽与避脸位移，
   写出权威 final_bbox（同步写入 bbox），供 render / jianying / hyperframes / qa 四端同源消费。
4. 双通道防重复：code_broll 在场覆盖 >=60% 时标记 suppressed=True 并跳过上屏（仅普通无画中画图解）。
输出：pipeline/05_subtitles.json、05_subtitles.ass、05_subtitles.srt 与 05_subtitle_check.txt
"""

from __future__ import annotations

import argparse
import difflib
import math
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
    BT709_FFMPEG_ARGS,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    SUBTITLE_CENTER_X,
    SUBTITLE_DEFAULT_Y_CENTER,
    SUBTITLE_SAFE_ZONE,
    SUBTITLE_SYMMETRIC_MAX_W,
    bbox_iou,
    check_bbox_in_safe_zone,
    find_bin,
    find_commercial_font,
    get_cached_font,
    load_subtitle_templates,
    maybe_reexec_in_venv,
    parse_manifest_faces,
    read_json,
    write_json,
)

# 仅保留夹在数字间的小数点/冒号(如 3.5 / 18:30)以及数字后的%，彻底清掉紧贴数字的中文逗号句号！
_NON_CORE_PUNCT_RE = re.compile(r"(?<!\d)[.:：](?!\d)|(?<!\d)[.:：](?=\d)|(?<=\d)[.:：](?!\d)|[，。、；！？,!?;“”‘’\"'（）()]+")

_DP_NO_LEAD_CHARS = set("的了呢吗吧啊着过么嘛上里中下后前")
_DP_NO_TAIL_CHARS = set("的把被从跟比在对向给让和与及是将用为")
_DP_UNIT_AFTER_NUM = set("倍度年多万亿%％岁个次米元块斤克天月时分秒件家店条步项位层种")
_DP_HARD_SPLIT_RE = re.compile(r"([。！？!?]+)")
_DP_SOFT_PUNCT = set("，、；：,;: ")
_COMMON_TWO_CHAR_WORDS = {
    "因为", "所以", "但是", "其实", "如果", "而且", "虽然", "不过", "然后", "或者",
    "为什么", "怎么样", "多少钱", "不会", "不能", "不是", "没有", "已经", "可以", "需要",
    "自己", "大家", "我们", "你们", "他们", "这个", "那个", "这样", "那样", "这里", "那里",
    "放大", "缩小", "面积", "真实", "成本", "利润", "价格", "时间", "方法", "步骤", "结果",
    "对比", "发现", "问题", "答案", "原因", "标准", "细节", "效果", "数据", "视频", "画面",
    "字幕", "镜头", "声音", "节奏", "烧烤", "羊排", "门店", "顾客", "老板", "新人", "完播",
}


def load_protected_terms(terms_path: Optional[Path] = None, extra_terms: Optional[List[str]] = None) -> List[str]:
    terms: List[str] = []
    if terms_path and Path(terms_path).is_file():
        for ln in Path(terms_path).read_text(encoding="utf-8").splitlines():
            t = ln.strip()
            if t and not t.startswith("#") and t not in terms:
                terms.append(t)
    for t in (extra_terms or []):
        ts = str(t or "").strip()
        if len(ts) >= 2 and ts not in terms:
            terms.append(ts)
    terms.sort(key=len, reverse=True)
    return terms


def tokenize_semantic_words(sentence: str, terms: Optional[List[str]] = None) -> List[str]:
    """
    词边界切分器：优先调用 jieba（若已安装），否则使用零依赖中文语义边界与保护词/数字量词合并分词器。
    严格保护 terms 中的专有名词、成语与“数字+单位”不被切碎。
    """
    s = str(sentence or "")
    if not s:
        return []
    prot = sorted([t for t in (terms or []) if t], key=len, reverse=True)
    raw_toks: List[str] = []

    try:
        import jieba  # type: ignore
        jieba.setLogLevel(60)
        for tm in prot:
            jieba.add_word(tm, freq=2_000_000)
        raw_toks = [t for t in jieba.cut(s, HMM=False) if t]
    except Exception:
        # 零依赖高质量分词兜底：先整块匹配保护词/数字+单位/英文词，再按虚词与常见词切分
        i, n = 0, len(s)
        num_unit_re = re.compile(r"[0-9]+(?:[.:][0-9]+)?[%％倍度年多万亿岁个次米元块斤克天月时分秒件家店条步项位层种]*")
        ascii_re = re.compile(r"[A-Za-z][A-Za-z0-9_\-]*")
        while i < n:
            matched_prot = None
            for tm in prot:
                if s.startswith(tm, i):
                    matched_prot = tm
                    break
            if matched_prot:
                raw_toks.append(matched_prot)
                i += len(matched_prot)
                continue
            m_num = num_unit_re.match(s, i)
            if m_num:
                raw_toks.append(m_num.group(0))
                i = m_num.end()
                continue
            m_asc = ascii_re.match(s, i)
            if m_asc:
                raw_toks.append(m_asc.group(0))
                i = m_asc.end()
                continue
            ch = s[i]
            if ch in _DP_SOFT_PUNCT or ch in "。！？!?":
                raw_toks.append(ch)
                i += 1
                continue
            if i + 3 <= n and s[i : i + 3] in _COMMON_TWO_CHAR_WORDS:
                raw_toks.append(s[i : i + 3])
                i += 3
                continue
            if i + 2 <= n and s[i : i + 2] in _COMMON_TWO_CHAR_WORDS:
                raw_toks.append(s[i : i + 2])
                i += 2
                continue
            if ch in _DP_NO_LEAD_CHARS or ch in _DP_NO_TAIL_CHARS:
                raw_toks.append(ch)
                i += 1
                continue
            # 其余普通汉字尽量组成 2 字自然语义节拍，遇到标点/数字/虚词提前停
            if i + 1 < n and ("\u4e00" <= s[i + 1] <= "\u9fff") and s[i + 1] not in _DP_NO_LEAD_CHARS and s[i + 1] not in _DP_NO_TAIL_CHARS:
                if not any(s.startswith(tm, i + 1) for tm in prot):
                    raw_toks.append(s[i : i + 2])
                    i += 2
                    continue
            raw_toks.append(ch)
            i += 1

    # 后处理：强制合并跨 token 的“数字 + 单位/小数”
    merged: List[str] = []
    for tok in raw_toks:
        if (
            merged
            and re.search(r"[0-9]$", merged[-1])
            and tok
            and (tok[0] in _DP_UNIT_AFTER_NUM or tok[0] in "0123456789.:")
        ):
            merged[-1] += tok
        else:
            merged.append(tok)
    return merged


def dp_segment_short_lines(
    sentence: str,
    max_width_px: int,
    font_path: Optional[str] = None,
    font_size: int = 62,
    terms: Optional[List[str]] = None,
    max_chars: int = 12,
    strip_punct: bool = True,
) -> List[Tuple[int, int, str]]:
    """
    词边界动态规划（DP）最优短句切分：
    返回 [(start_char_idx, end_char_idx, display_text), ...]。
    """
    raw = str(sentence or "")
    if not raw.strip():
        return []
    prot = [t for t in (terms or []) if len(t) >= 2]
    toks = tokenize_semantic_words(raw, terms=prot)
    bounds = [0]
    for tk in toks:
        bounds.append(bounds[-1] + len(tk))
    nb = len(bounds)
    if nb <= 1:
        return []

    def _disp(a: int, b: int) -> str:
        sub = raw[a:b].strip()
        if strip_punct:
            sub = re.sub(r"[，、；：,;:]+", " ", sub)
            sub = strip_display_punctuation(sub)
            sub = re.sub(r"\s+", " ", sub).strip()
        return sub

    # 预计算保护词区间，避免 DP 内层每次重复 re.finditer
    prot_spans: List[Tuple[int, int]] = []
    for tm in prot:
        for m in re.finditer(re.escape(tm), raw):
            prot_spans.append((m.start(), m.end()))

    def _break_cost(pos: int) -> float:
        if pos <= 0 or pos >= len(raw):
            return 0.0
        left = raw[:pos]
        right = raw[pos:]
        if left and left[-1] in _DP_SOFT_PUNCT:
            return 0.0
        cost = 4.0
        r_trim = right.lstrip("，、；：,;: 。！？!?")
        l_trim = left.rstrip("，、；：,;: 。！？!?")
        r0 = r_trim[:1]
        l_last = l_trim[-1:]
        if r0 in _DP_NO_LEAD_CHARS:
            cost += 30.0
        if l_last in _DP_NO_TAIL_CHARS:
            cost += 15.0
        if r0.isdigit():
            cost += 25.0
        for ps, pe in prot_spans:
            if ps < pos < pe:
                cost += 1000.0
        return cost

    inf = float("inf")
    best = [inf] * nb
    prev = [-1] * nb
    best[0] = 0.0
    max_len_hard = max(6, int(max_chars) + 1)

    for j in range(1, nb):
        for i in range(j):
            if best[i] == inf:
                continue
            txt = _disp(bounds[i], bounds[j])
            if not txt:
                if best[i] < best[j]:
                    best[j] = best[i]
                    prev[j] = i
                continue
            compact_len = len(txt.replace(" ", ""))
            pw, _ = _measure_text_px(txt, font_path, font_size)
            if pw > max_width_px or compact_len > max_len_hard:
                continue
            short_pen = max(0, 5 - compact_len) * 2.5 if j < nb - 1 or i > 0 else 0.0
            if compact_len <= 3 and (i > 0 or j < nb - 1):
                short_pen += 12.0
            cand = best[i] + _break_cost(bounds[j]) + short_pen + 1.0
            if cand < best[j]:
                best[j] = cand
                prev[j] = i

    if best[nb - 1] == inf:
        # 极端长保护词或超窄画布兜底：按原样返回整段
        return [(0, len(raw), _disp(0, len(raw)) or raw.strip())]

    out: List[Tuple[int, int, str]] = []
    cur = nb - 1
    while cur > 0:
        p = prev[cur]
        disp_t = _disp(bounds[p], bounds[cur])
        if disp_t:
            out.append((bounds[p], bounds[cur], disp_t))
        cur = p
    out.reverse()
    return out


def align_corrected_text_to_words(
    corrected_text: str,
    asr_words: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], float]:
    """用 difflib.SequenceMatcher 将人工校对后的纯文本字符级对齐到逐字时间戳，保留数字间小数点/冒号，未匹配字平滑插值。"""
    norm_corr = strip_display_punctuation(re.sub(r"\s+", "", str(corrected_text or "")))
    clean_chars = [ch for ch in norm_corr if ch.strip()]
    asr_flat: List[Tuple[str, float, float]] = []
    for w in asr_words:
        wt = strip_display_punctuation(re.sub(r"\s+", "", str(w.get("word") or "")))
        if not wt:
            continue
        ws = float(w.get("start_sec", 0.0))
        we = float(w.get("end_sec", ws + 0.08))
        n = len(wt)
        for k, ch in enumerate(wt):
            asr_flat.append((ch, ws + (we - ws) * k / n, ws + (we - ws) * (k + 1) / n))

    if not clean_chars or not asr_flat:
        return [], 0.0
    sm = difflib.SequenceMatcher(None, clean_chars, [c for c, _, _ in asr_flat], autojunk=False)
    times: List[Optional[Tuple[float, float]]] = [None] * len(clean_chars)
    matched = 0
    for blk in sm.get_matching_blocks():
        matched += blk.size
        for k in range(blk.size):
            _, s, e = asr_flat[blk.b + k]
            times[blk.a + k] = (s, e)

    first_asr_t = float(asr_flat[0][1])
    n = len(times)
    i = 0
    while i < n:
        if times[i] is None:
            j = i
            while j < n and times[j] is None:
                j += 1
            gap_n = max(1, j - i)
            if i == 0 and j < n and times[j] is not None:
                # 句首未匹配字：严格落在第一个已匹配字 times[j][0] 之前，彻底避免时间轴倒挂重叠
                t1 = float(times[j][0])
                t0 = max(0.0, min(first_asr_t, t1 - 0.12 * gap_n))
                if t1 <= t0 + 0.01:
                    t0 = max(0.0, t1 - 0.04 * gap_n)
                span = max(0.015, (t1 - t0) / gap_n)
                for k in range(i, j):
                    s_k = max(0.0, t1 - span * (j - k))
                    e_k = max(s_k + 0.01, t1 - span * (j - k - 1))
                    times[k] = (s_k, e_k)
            else:
                t0 = float(times[i - 1][1]) if i > 0 and times[i - 1] else first_asr_t
                t1 = float(times[j][0]) if j < n and times[j] else (t0 + 0.16 * gap_n)
                span = max(0.02 * gap_n, t1 - t0) / gap_n
                for k in range(i, j):
                    times[k] = (t0 + span * (k - i), t0 + span * (k - i + 1))
            i = j
        else:
            i += 1

    aligned = [
        {"word": ch, "start_sec": round(float(t[0]), 4), "end_sec": round(float(t[1]), 4)}
        for ch, t in zip(clean_chars, times)
        if t is not None
    ]
    return aligned, round(matched / max(1, len(clean_chars)), 4)


def fmt_srt_time(sec: float) -> str:
    ms = int(round(max(0.0, float(sec)) * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms_r = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms_r:03d}"


def burn_ass_safely(
    video_in: Path,
    ass_path: Path,
    video_out: Path,
    font_path: Optional[Path] = None,
    expected_font_hint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    安全烧录 ASS 字幕：把 ASS 和单个字体复制到纯 ASCII 临时目录规避中文/冒号转义坑，
    并从 libass verbose 日志确认实际命中的字体，防止静默回退系统默认字体。
    """
    ffmpeg = find_bin("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("需要 ffmpeg 烧录 ASS 字幕。")
    with tempfile.TemporaryDirectory(prefix="svs_ass_") as td:
        tdp = Path(td)
        tmp_ass = tdp / "sub.ass"
        shutil.copy2(ass_path, tmp_ass)
        fonts_dir = tdp / "fonts"
        fonts_dir.mkdir(exist_ok=True)
        if font_path and Path(font_path).is_file():
            # 保留原始商用字体文件名（替换非 ASCII 字符），便于 libass fontselect 精准核对命中
            safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(font_path).stem) or "commercial_font"
            shutil.copy2(font_path, fonts_dir / f"{safe_stem}{Path(font_path).suffix.lower()}")
        ass_esc = str(tmp_ass).replace("\\", "/").replace(":", "\\:")
        fd_esc = str(fonts_dir).replace("\\", "/").replace(":", "\\:")
        vf = f"ass='{ass_esc}':fontsdir='{fd_esc}'"
        proc = subprocess.run(
            [
                ffmpeg, "-y", "-hide_banner", "-loglevel", "verbose",
                "-i", str(video_in), "-vf", vf,
                "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
                *BT709_FFMPEG_ARGS,
                "-c:a", "copy", "-movflags", "+faststart", str(video_out),
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        font_hits = re.findall(r"fontselect:\s*\(([^)]+)\)\s*->\s*(.+)", proc.stderr or "")
        if proc.returncode != 0:
            matched_ok = False
        elif expected_font_hint:
            matched_ok = bool(font_hits) and any(
                expected_font_hint.lower() in f"{a} {b}".lower() for a, b in font_hits
            )
        else:
            matched_ok = bool(font_hits)
        return {
            "returncode": proc.returncode,
            "font_select_hits": [f"{a} -> {b.strip()}" for a, b in font_hits[:6]],
            "font_matched_expected": matched_ok,
        }


def strip_display_punctuation(text: str) -> str:
    raw = str(text or "")
    # 先将夹在数字间的全角冒号归一化为半角冒号
    raw = re.sub(r"(?<=\d)：(?=\d)", ":", raw)
    return _NON_CORE_PUNCT_RE.sub("", raw)


def _clean_word_tokens(raw_words: List[Dict[str, Any]], strip_punct: bool) -> List[Dict[str, Any]]:
    """逐词清洗标点，并保护跨 token 拆分的数字小数点/时间冒号(如 '18:' + '30')不被误杀。"""
    if not strip_punct:
        out: List[Dict[str, Any]] = []
        for w in raw_words:
            t = str(w.get("word", "")).strip()
            if t:
                cw = dict(w)
                cw["word"] = t
                out.append(cw)
        return out

    out = []
    n = len(raw_words)
    for idx, w in enumerate(raw_words):
        orig = str(w.get("word", ""))
        prev_txt = str(raw_words[idx - 1].get("word", "")) if idx > 0 else ""
        next_txt = str(raw_words[idx + 1].get("word", "")) if idx + 1 < n else ""
        # 如果当前词以 .:： 结尾且下一词以数字开头，或以 .:： 开头且上一词以数字结尾，暂时用占位符保护
        lead_protected = bool(orig and orig[0] in ".:：" and prev_txt and prev_txt[-1].isdigit())
        trail_protected = bool(orig and orig[-1] in ".:：" and next_txt and next_txt[0].isdigit())
        tmp = orig
        if lead_protected:
            tmp = "9" + tmp
        if trail_protected:
            tmp = tmp + "9"
        cleaned = strip_display_punctuation(tmp)
        if lead_protected and cleaned.startswith("9"):
            cleaned = cleaned[1:]
        if trail_protected and cleaned.endswith("9"):
            cleaned = cleaned[:-1]
        cleaned = cleaned.strip()
        if not cleaned:
            continue
        cw = dict(w)
        cw["word"] = cleaned
        out.append(cw)
    return out


def fmt_ass_time(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _escape_ass_text(txt: str) -> str:
    return str(txt or "").replace("\r\n", r"\N").replace("\n", r"\N").replace("{", r"\{").replace("}", r"\}")


def _measure_text_px(text: str, font_path: Optional[str], font_size: int) -> Tuple[int, int]:
    fnt = get_cached_font(font_path, font_size)
    if fnt is not None:
        try:
            bb = fnt.getbbox(text)
            return int(max(40, (bb[2] - bb[0]) + max(8, len(text) * 3))), int(max(font_size + 16, (bb[3] - bb[1]) + 28))
        except Exception:
            pass
    return int(len(text) * font_size * 1.04), int(font_size * 1.35 + 24)


def _compute_authoritative_subtitle_bbox(
    text: str,
    tpl: Dict[str, Any],
    font_path: Optional[str],
    face_boxes_px: List[Dict[str, Any]],
) -> Dict[str, int]:
    """按画布绝对正中 x=540 对称安全带 [220, 860] 计算尺寸并仅在垂直方向避开人脸五官，产出四端统一 final_bbox。"""
    base_fs = int(tpl.get("font_size", 62))
    kw_scale = float(tpl.get("keyword_scale", 1.133))
    eff_fs = int(round(base_fs * min(1.20, max(1.0, (1.0 + kw_scale) * 0.5))))
    safe_w_cap = SUBTITLE_SYMMETRIC_MAX_W  # 640px ([220, 860]，中心严格锁定 540px)
    center_x = SUBTITLE_CENTER_X  # 540px

    est_w, est_h = _measure_text_px(text, font_path, eff_fs)
    box_w = min(safe_w_cap, max(160, est_w + 32))
    box_h = min(220, max(84, est_h + 16))
    # 水平中心 100% 锁定画布正中央 540px，且 box_w <= 640 保证永不触发右侧 860px 单侧推偏
    box_x = center_x - box_w // 2

    # 钳位 safe_y_center，默认对齐黄金水位 SUBTITLE_DEFAULT_Y_CENTER (1310px)
    safe_yc = int(tpl.get("safe_y_center", SUBTITLE_DEFAULT_Y_CENTER))
    box_y = max(SUBTITLE_SAFE_ZONE["y_min"], min(SUBTITLE_SAFE_ZONE["y_max"] - box_h, safe_yc - box_h // 2))
    cand = {"x": int(box_x), "y": int(box_y), "w": int(box_w), "h": int(box_h)}

    if face_boxes_px:
        cur_iou = max(bbox_iou(cand, fb) for fb in face_boxes_px)
        if cur_iou > 0.01:
            y_lo = SUBTITLE_SAFE_ZONE["y_min"]
            y_hi = SUBTITLE_SAFE_ZONE["y_max"] - box_h
            try_ys = [
                y_hi,
                y_lo,
                max(y_lo, box_y - 110),
                min(y_hi, box_y + 110),
                max(y_lo, y_lo + 60),
                min(y_hi, y_hi - 60),
                (y_lo + y_hi) // 2,
            ]
            best_cand = cand
            best_iou = cur_iou
            for ty in try_ys:
                ty_c = max(y_lo, min(y_hi, int(ty)))
                alt = dict(cand, y=ty_c)
                iou_v = max(bbox_iou(alt, fb) for fb in face_boxes_px)
                if iou_v <= 0.01:
                    best_cand = alt
                    break
                if iou_v < best_iou:
                    best_iou = iou_v
                    best_cand = alt
            cand = best_cand
    return cand


def split_sentence_into_chunks(
    sent: Dict[str, Any],
    max_chars: int = 10,
    font_path: Optional[str] = None,
    font_size: int = 62,
    max_safe_px: int = SUBTITLE_SYMMETRIC_MAX_W - 32,
    strip_punct: bool = True,
    protected_terms: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    把长句按真静音 (>=0.30s) 呼吸组 + 词边界动态规划（DP）拆分为无残句、不破词、不拆保护词的短句字幕块。
    """
    clean_fn = strip_display_punctuation if strip_punct else (lambda s: str(s or "").strip())
    words = _clean_word_tokens(list(sent.get("words") or []), strip_punct=strip_punct)
    sent_kws = list(sent.get("keywords") or [])
    eff_terms = load_protected_terms(extra_terms=list(protected_terms or []) + [str(k) for k in sent_kws])

    if not words:
        raw_t = str(sent.get("text", "")).strip()
        dp_segs = dp_segment_short_lines(
            raw_t,
            max_width_px=max_safe_px,
            font_path=font_path,
            font_size=font_size,
            terms=eff_terms,
            max_chars=max_chars,
            strip_punct=strip_punct,
        )
        if not dp_segs:
            clean_txt = clean_fn(raw_t).strip()
            return [{
                "text": clean_txt or raw_t,
                "start_sec": sent["start_sec"],
                "end_sec": sent["end_sec"],
                "words": [],
                "keywords": sent_kws,
            }]
        total_chars = max(1, sum(len(t.replace(" ", "")) for _, _, t in dp_segs))
        t0, t1 = float(sent["start_sec"]), float(sent["end_sec"])
        span = max(0.2, t1 - t0)
        cursor_t = t0
        out_no_words: List[Dict[str, Any]] = []
        for _, _, seg_t in dp_segs:
            seg_dur = span * (max(1, len(seg_t.replace(" ", ""))) / total_chars)
            out_no_words.append({
                "text": seg_t,
                "start_sec": round(cursor_t, 4),
                "end_sec": round(min(t1, cursor_t + seg_dur), 4),
                "words": [],
                "keywords": sent_kws,
            })
            cursor_t += seg_dur
        return out_no_words

    breath_groups: List[List[Dict[str, Any]]] = []
    cur_grp: List[Dict[str, Any]] = [words[0]]
    for prev_w, cur_w in zip(words, words[1:]):
        gap = float(cur_w["start_sec"]) - float(prev_w["end_sec"])
        if gap >= 0.30 and len(cur_grp) >= 4:
            breath_groups.append(cur_grp)
            cur_grp = [cur_w]
        else:
            cur_grp.append(cur_w)
    if cur_grp:
        if breath_groups and len(cur_grp) <= 3:
            breath_groups[-1].extend(cur_grp)
        else:
            breath_groups.append(cur_grp)

    chunks: List[Dict[str, Any]] = []
    for grp in breath_groups:
        txt = "".join(str(x["word"]) for x in grp)
        px_w, _ = _measure_text_px(txt, font_path, font_size)
        if len(txt) <= max_chars + 1 and px_w <= max_safe_px:
            chunks.append({
                "text": txt,
                "start_sec": grp[0]["start_sec"],
                "end_sec": grp[-1]["end_sec"],
                "words": list(grp),
                "keywords": sent_kws,
            })
            continue

        # 构造字符偏移到 word token 索引的精确映射，保证 DP 按语义词边界切片不丢逐字时间戳
        char_to_wi: List[int] = []
        for wi, w_item in enumerate(grp):
            for _ in str(w_item["word"]):
                char_to_wi.append(wi)

        dp_segs = dp_segment_short_lines(
            txt,
            max_width_px=max_safe_px,
            font_path=font_path,
            font_size=font_size,
            terms=eff_terms,
            max_chars=max_chars,
            strip_punct=strip_punct,
        )
        used_end_wi = 0
        for s_ch, e_ch, _ in dp_segs:
            if s_ch >= len(char_to_wi):
                continue
            w_start = max(used_end_wi, char_to_wi[s_ch])
            w_end = char_to_wi[min(len(char_to_wi) - 1, max(s_ch, e_ch - 1))] + 1
            if w_end <= w_start:
                continue
            sl = grp[w_start:w_end]
            used_end_wi = w_end
            if sl:
                chunks.append({
                    "text": "".join(str(x["word"]) for x in sl),
                    "start_sec": sl[0]["start_sec"],
                    "end_sec": sl[-1]["end_sec"],
                    "words": list(sl),
                    "keywords": sent_kws,
                })
        if used_end_wi < len(grp):
            tail_sl = grp[used_end_wi:]
            if chunks and len(tail_sl) <= 3:
                chunks[-1]["words"].extend(tail_sl)
                chunks[-1]["text"] += "".join(str(x["word"]) for x in tail_sl)
                chunks[-1]["end_sec"] = tail_sl[-1]["end_sec"]
            elif tail_sl:
                chunks.append({
                    "text": "".join(str(x["word"]) for x in tail_sl),
                    "start_sec": tail_sl[0]["start_sec"],
                    "end_sec": tail_sl[-1]["end_sec"],
                    "words": list(tail_sl),
                    "keywords": sent_kws,
                })
    return chunks


def _build_safe_ass_style(raw_ass_style: str, font_path: Optional[str]) -> str:
    """动态对齐 ASS Style 中的商用字体名、对称左右边距 (MarginL=MarginR=220 保正中 540px) 与 MarginV >= 452。"""
    parts = [p.strip() for p in str(raw_ass_style or "").split(",")]
    if len(parts) < 23:
        return str(raw_ass_style or "")
    if font_path:
        stem = Path(font_path).stem
        low_stem = stem.lower()
        if "alimama" in low_stem:
            parts[1] = "Alimama ShuHeiTi"
        elif "smileysans" in low_stem:
            parts[1] = "Smiley Sans"
        elif "sourcehanserifcn-heavy" in low_stem:
            parts[1] = "Source Han Serif CN Heavy"
        elif "sourcehanserif" in low_stem:
            parts[1] = "Source Han Serif CN"
        elif "sourcehansans" in low_stem:
            parts[1] = "Source Han Sans CN"
        elif "notoserifsc" in low_stem:
            parts[1] = "Noto Serif CJK SC"
        elif "notosans" in low_stem:
            parts[1] = "Noto Sans CJK SC"
        elif "pingfang" not in low_stem and "stheiti" not in low_stem:
            parts[1] = stem
    sym_margin_x = str(CANVAS_WIDTH - SUBTITLE_SAFE_ZONE["x_max"])  # 220 -> [220, 860] 轴心 540px
    parts[19] = sym_margin_x
    parts[20] = sym_margin_x
    min_margin_v = CANVAS_HEIGHT - SUBTITLE_SAFE_ZONE["y_max"]  # 452
    try:
        cur_mv = int(float(parts[21]))
    except Exception:
        cur_mv = min_margin_v
    if cur_mv < min_margin_v:
        parts[21] = str(min_margin_v)
    return ",".join(parts)


def run_step5(
    pipeline_dir: Path,
    track: str = "store",
    template_id: Optional[str] = None,
) -> Dict[str, Any]:
    audio_events = read_json(pipeline_dir / "03_audio_events.json")
    edl_p = pipeline_dir / "04_edl.json"
    edl = read_json(edl_p) if edl_p.exists() else {"clips": []}
    man_p = pipeline_dir / "01_manifest.json"
    manifest = read_json(man_p) if man_p.exists() else {"items": []}

    # 获取每段规范素材在 1080x1920 裁切后画布的精确像素人脸框（兼容归一化与像素坐标系）
    faces_by_mp4: Dict[str, List[Dict[str, int]]] = {}
    for it in manifest.get("items", []):
        mp = str(it.get("normalized_mp4", ""))
        f_list = parse_manifest_faces(it)
        if mp and f_list:
            faces_by_mp4[mp] = f_list

    code_ranges: List[Tuple[float, float, str]] = [
        (float(c["timeline_in_sec"]), float(c["timeline_out_sec"]), str(c["clip_id"]))
        for c in edl.get("clips", [])
        if c.get("track_role") == "code_broll"
    ]
    templates = load_subtitle_templates()
    if not template_id or template_id not in templates:
        template_id = "store_bold_yellow" if track == "store" else "creator_clean_white"
    tpl = templates[template_id]
    font_path = find_commercial_font(tpl.get("font_candidates"), verified_only=True) or find_commercial_font()
    strip_punct = bool(tpl.get("punct_stripped", True))

    entries: List[Dict[str, Any]] = []
    ass_dialogues: List[str] = []
    kw_hex_bgr = tpl["keyword_color"].lstrip("#")
    ass_kw_color = f"&H00{kw_hex_bgr[4:6]}{kw_hex_bgr[2:4]}{kw_hex_bgr[0:2]}&"

    raw_intel_p = pipeline_dir / "00_raw_intel.json"
    raw_pain_kws = set(str(k) for k in ((read_json(raw_intel_p).get("pain_keywords") or []) if raw_intel_p.is_file() else []) if str(k).strip())

    # 切分前即加载 terms.txt 与原材关键词作为 DP 保护词，从源头禁止把专有名词/品牌词切碎
    terms_p = pipeline_dir / "terms.txt"
    prot_terms = load_protected_terms(terms_p if terms_p.is_file() else None, extra_terms=list(raw_pain_kws))

    idx = 1
    suppressed_count = 0
    tpl_max_chars = max(6, min(14, int(tpl.get("max_chars_per_line", 10))))
    base_fs = int(tpl.get("font_size", 62))
    kw_scale_f = float(tpl.get("keyword_scale", 1.133))
    eff_measure_fs = int(round(base_fs * max(1.0, (1.0 + kw_scale_f) * 0.5)))

    for sent in audio_events["sentences"]:
        sent_eff = dict(sent)
        if raw_pain_kws:
            s_kws = list(sent_eff.get("keywords") or [])
            s_txt_full = str(sent_eff.get("text") or "")
            for pk in raw_pain_kws:
                if pk in s_txt_full and pk not in s_kws:
                    s_kws.append(pk)
            sent_eff["keywords"] = s_kws
            if sent_eff.get("words"):
                matched_pks = [pk for pk in raw_pain_kws if pk and pk in s_txt_full]
                if matched_pks:
                    words_src = sent_eff["words"]
                    new_ws = [dict(w) for w in words_src]
                    # 精确拼接连续字词定位完整关键短语区间，杜绝单字包含误染
                    buf_tokens: List[Tuple[int, int, int]] = []
                    cur_pos = 0
                    joined_w = []
                    for wi, w_item in enumerate(new_ws):
                        wt = re.sub(r"\s+", "", str(w_item.get("word") or ""))
                        if not wt:
                            continue
                        joined_w.append(wt)
                        buf_tokens.append((cur_pos, cur_pos + len(wt), wi))
                        cur_pos += len(wt)
                    joined_str = "".join(joined_w)
                    for pk in matched_pks:
                        pk_clean = re.sub(r"\s+", "", pk)
                        if not pk_clean:
                            continue
                        search_i = 0
                        while True:
                            hit_at = joined_str.find(pk_clean, search_i)
                            if hit_at < 0:
                                break
                            hit_end = hit_at + len(pk_clean)
                            for cs, ce, wi in buf_tokens:
                                if cs < hit_end and ce > hit_at:
                                    new_ws[wi]["is_keyword"] = True
                            search_i = hit_end
                    sent_eff["words"] = new_ws
        sent_prot = load_protected_terms(None, extra_terms=[*prot_terms, *(sent_eff.get("keywords") or [])])
        for ch in split_sentence_into_chunks(
            sent_eff,
            max_chars=tpl_max_chars,
            font_path=font_path,
            font_size=eff_measure_fs,
            strip_punct=strip_punct,
            protected_terms=sent_prot,
        ):
            st_sec = round(float(ch["start_sec"]), 4)
            en_sec = round(float(ch["end_sec"]), 4)
            sub_dur = max(0.05, en_sec - st_sec)

            # 收集该字幕在时间线上重叠镜头的精确人脸框以执行源头避脸
            active_faces: List[Dict[str, Any]] = []
            for c in edl.get("clips", []):
                if float(c["timeline_in_sec"]) < en_sec and float(c["timeline_out_sec"]) > st_sec:
                    active_faces.extend(faces_by_mp4.get(str(c.get("media_path", "")), []))

            final_bbox = _compute_authoritative_subtitle_bbox(ch["text"], tpl, font_path, active_faces)
            safe_ok, safe_msg = check_bbox_in_safe_zone(final_bbox)

            suppressed = False
            suppressed_by = None
            for cs, ce, cid in code_ranges:
                ov = max(0.0, min(en_sec, ce) - max(st_sec, cs))
                if ov / sub_dur >= 0.60:
                    suppressed = True
                    suppressed_by = cid
                    suppressed_count += 1
                    break

            entry_obj: Dict[str, Any] = {
                "id": f"sub_{idx:03d}",
                "sentence_id": sent["id"],
                "text": ch["text"],
                "start_sec": st_sec,
                "end_sec": en_sec,
                "keywords": ch.get("keywords", sent.get("keywords", [])),
                "words": ch["words"],
                "bbox": final_bbox,
                "final_bbox": final_bbox,
                "safe_zone_ok": safe_ok,
                "safe_msg": safe_msg,
                "suppressed": suppressed,
            }
            if suppressed:
                entry_obj["suppressed_by"] = suppressed_by
                entry_obj["suppress_reason"] = "B9_code_broll_dual_channel_dedup"

            entries.append(entry_obj)

            if not suppressed:
                ass_text = ""
                for w in ch["words"]:
                    w_txt = _escape_ass_text(str(w["word"]))
                    if not w_txt:
                        continue
                    if w.get("is_keyword"):
                        ass_text += f"{{\\c{ass_kw_color}\\b1}}{w_txt}{{\\r}}"
                    else:
                        ass_text += w_txt
                if not ass_text:
                    ass_text = _escape_ass_text(ch["text"])
                plain_ass = _escape_ass_text(ch["text"])
                # 双层柔和模糊阴影（Layer 0 柔黑阴影 + Layer 1 清晰主层，禁用自动换行 \q2）
                ass_cx = SUBTITLE_CENTER_X
                ass_cy = int(final_bbox["y"]) + int(final_bbox["h"]) // 2
                ass_dialogues.append(
                    f"Dialogue: 0,{fmt_ass_time(st_sec)},{fmt_ass_time(en_sec)},Default,,0,0,0,,"
                    f"{{\\q2\\an5\\pos({ass_cx + 4},{ass_cy + 5})\\1c&H000000&\\1a&HB0&\\3c&H000000&\\3a&HB0&\\shad0\\blur4}}{plain_ass}"
                )
                ass_dialogues.append(
                    f"Dialogue: 1,{fmt_ass_time(st_sec)},{fmt_ass_time(en_sec)},Default,,0,0,0,,"
                    f"{{\\q2\\an5\\pos({ass_cx},{ass_cy})}}{ass_text}"
                )
            idx += 1

    safe_ass_style = _build_safe_ass_style(tpl["ass_style"], font_path)
    ass_content = "\n".join([
        "[Script Info]",
        "ScriptType: v4.00+",
        f"PlayResX: {CANVAS_WIDTH}",
        f"PlayResY: {CANVAS_HEIGHT}",
        "WrapStyle: 2",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        safe_ass_style,
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
        *ass_dialogues,
    ]) + "\n"

    (pipeline_dir / "05_subtitles.ass").write_text(ass_content, encoding="utf-8")

    # 同步导出纯净单行 SRT 与逐行断句检查报告（含字/秒节奏与保护词防拆核验）
    srt_lines: List[str] = []
    check_lines: List[str] = [f"字幕模板：{template_id} | 总条数：{len(entries)} | 让位挂起：{suppressed_count}", ""]
    active_entries = [e for e in entries if not e.get("suppressed")]
    for s_idx, ent in enumerate(active_entries, start=1):
        srt_lines.append(f"{s_idx}\n{fmt_srt_time(ent['start_sec'])} --> {fmt_srt_time(ent['end_sec'])}\n{ent['text']}\n")
        dur_e = max(0.05, float(ent["end_sec"]) - float(ent["start_sec"]))
        cps_e = len(str(ent["text"]).replace(" ", "")) / dur_e
        flag = "  <- 偏快 (>9字/秒)" if cps_e > 9.0 else ""
        check_lines.append(f"{s_idx:02d} [{ent['start_sec']:6.2f}-{ent['end_sec']:6.2f}] {dur_e:4.2f}s {cps_e:4.1f}字/秒 | {ent['text']}{flag}")

    broken_terms: List[str] = []
    for a, b in zip(active_entries, active_entries[1:]):
        ta = str(a["text"]).replace(" ", "")
        tb = str(b["text"]).replace(" ", "")
        joint = ta[-4:] + "|" + tb[:4]
        cut_i = joint.index("|")
        joined_plain = joint.replace("|", "")
        for tm in prot_terms:
            for m in re.finditer(re.escape(tm), joined_plain):
                if m.start() < cut_i < m.end():
                    broken_terms.append(f"{a['id']}/{b['id']} 拆开了「{tm}」")
    check_lines.append("\n保护词防拆检查：" + ("通过" if not broken_terms else "；".join(broken_terms)))
    (pipeline_dir / "05_subtitles.srt").write_text("\n".join(srt_lines), encoding="utf-8")
    (pipeline_dir / "05_subtitle_check.txt").write_text("\n".join(check_lines) + "\n", encoding="utf-8")

    out_json = {
        "step": "05_subtitles",
        "template_id": template_id,
        "template_name": tpl["name"],
        "font_path": font_path,
        "font_license": tpl["license"],
        "template_config": tpl,
        "count": len(entries),
        "suppressed_count": suppressed_count,
        "srt_path": str((pipeline_dir / "05_subtitles.srt").resolve()),
        "check_report_path": str((pipeline_dir / "05_subtitle_check.txt").resolve()),
        "broken_protected_terms": broken_terms,
        "entries": entries,
    }
    write_json(pipeline_dir / "05_subtitles.json", out_json)
    print(
        f"[step5] 字幕生成完成：{len(entries)} 条（图解画面自动让位 {suppressed_count} 条，"
        f"模板 `{template_id}`, 字体 `{Path(font_path).name if font_path else 'default'}`）-> 05_subtitles.json"
    )
    return out_json


def main() -> None:
    maybe_reexec_in_venv()
    parser = argparse.ArgumentParser(description="Step 5: 逐字时间戳字幕与统一避脸布局生成")
    parser.add_argument("--pipeline-dir", required=True)
    parser.add_argument("--track", choices=["store", "creator"], default="store")
    parser.add_argument("--template", help="字幕模板ID")
    parser.add_argument("--corrected-text", help="可选：人工校对后的纯文本文件，字符级回填逐字时间戳后重排字幕")
    args = parser.parse_args()
    pdir = Path(args.pipeline_dir)
    if args.corrected_text and Path(args.corrected_text).is_file():
        ae_p = pdir / "03_audio_events.json"
        if ae_p.is_file():
            ae = read_json(ae_p)
            corr_lines = [ln.strip() for ln in Path(args.corrected_text).read_text(encoding="utf-8").splitlines() if ln.strip()]
            for sent, corr in zip(ae.get("sentences") or [], corr_lines):
                aligned, ratio = align_corrected_text_to_words(corr, sent.get("words") or [])
                if aligned and ratio >= 0.35:
                    sent["text"] = corr
                    sent["words"] = aligned
            write_json(ae_p, ae)
    run_step5(pdir, track=args.track, template_id=args.template)


if __name__ == "__main__":
    main()

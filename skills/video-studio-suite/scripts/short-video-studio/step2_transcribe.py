#!/usr/bin/env python3
"""
[Step 2: 语音转写、真实声学强制对齐、向量化 STFT 画外声剥离 & 多条 NG 择优]
v5 升级：
1. --script-json 同时兼容 {"sentences": [...]}, {"segments": [...]} 与 list；内嵌示范文案符合 <=16 字呼吸红线。
2. extract_auto_keywords 基于虚词/标点边界切分完整实词短语（禁止 4 字硬切残词）；Whisper 词表精准按词边界标 keyword。
3. 修正流水线次序：TTS 先过合规与语义校对、刷新 keywords 再合音（音字严密一致）；实拍先收紧静音边界再重算韵律/提词。
4. 按 source_audio 分组计算主讲 RMS 防止多机位误杀；双声道自动拯救无线麦单边；向量化 STFT 计算声学指纹。
"""

from __future__ import annotations

import argparse
import asyncio
import difflib
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import (
    find_bin,
    find_cached_whisper_model,
    get_cached_whisper_model,
    get_wav_duration_sec,
    maybe_reexec_in_venv,
    read_json,
    read_wav_as_48k_stereo,
    rescue_stereo_channels,
    run_cmd,
    write_json,
    write_wav_48k_stereo,
)
from compliance_guard import audit_script_compliance, write_compliance_report_files

if __name__ == "__main__":
    maybe_reexec_in_venv(("faster_whisper",))

import numpy as np

FILLER_WORDS = {"呃", "嗯", "那个", "就是说", "然后呢", "啊", "这个", "哎呀"}
DIRECTOR_CUE_EXACT = {
    "ok", "好", "对", "来", "开始", "重来", "三二一", "321", "action",
    "等一下", "再讲一遍", "再说一遍", "再试一次", "准备", "可以", "卡", "过", "中间",
}

DEFAULT_STORE_SCRIPT = [
    {"text": "价格越高的菜，利润反而越低。", "keywords": ["价格越高", "利润"], "is_filler": False, "emotion": "hook"},
    {"text": "呃那个我先说一下，", "keywords": [], "is_filler": True, "emotion": "filler"},
    {"text": "清晨市场带回的鲜羊排，成本花了三千块。", "keywords": ["鲜羊排", "三千块"], "is_filler": False, "emotion": "info"},
    {"text": "看起来卖四百能赚一百多，", "keywords": ["卖四百"], "is_filler": False, "emotion": "info"},
    {"text": "其实要腌两小时，炭火再烤三小时。", "keywords": ["两小时", "三小时"], "is_filler": False, "emotion": "detail"},
    {"text": "开了八年烧烤店，绝不用冻肉糊弄人。", "keywords": ["八年", "绝不用冻肉"], "is_filler": False, "emotion": "persona"},
    {"text": "想吃鲜嫩烤羊排，评论区发你门店地址。", "keywords": ["评论区", "门店地址"], "is_filler": False, "emotion": "cta"},
]

DEFAULT_CREATOR_SCRIPT = [
    {"text": "做短视频，懂越多反而越做不好。", "keywords": ["短视频", "越做不好"], "is_filler": False, "emotion": "hook"},
    {"text": "呃就是说，", "keywords": [], "is_filler": True, "emotion": "filler"},
    {"text": "八成新人把时间全耗在了学转场上。", "keywords": ["八成新人", "学转场"], "is_filler": False, "emotion": "info"},
    {"text": "决定完播率的，其实只有画面密度和节奏。", "keywords": ["完播率", "画面密度"], "is_filler": False, "emotion": "twist"},
    {"text": "先锁死声音，再贴上镜头，记住这条铁律。", "keywords": ["声音", "铁律"], "is_filler": False, "emotion": "persona"},
    {"text": "写文案还是剪片子最难？评论区聊聊。", "keywords": ["评论区"], "is_filler": False, "emotion": "cta"},
]

_ASR_STOP_WORDS = {
    "我们", "你们", "他们", "这个", "那个", "就是", "其实", "然后", "因为", "所以",
    "可以", "大家", "什么", "怎么", "一个", "没有", "还是", "觉得", "如果", "自己", "为什么",
}
_PUNCT_STRIP_SET = set(" \t\r\n，。！？、；：“”‘’（）().,!?;:\"'《》【】[]")


def _clean_zh_text(text: str) -> str:
    return re.sub(r"[\s，。！？、；：“”‘’（）().,!?;:\"'《》【】\[\]]+", "", text).lower()


def is_filler_or_director_cue(text: str) -> bool:
    cleaned = _clean_zh_text(text)
    if not cleaned:
        return True
    if cleaned in DIRECTOR_CUE_EXACT:
        return True
    return any(fw == cleaned or (len(cleaned) <= 5 and fw in cleaned) for fw in FILLER_WORDS)


def extract_auto_keywords(text: str) -> List[str]:
    """按标点/虚词边界与数字量词模式提取完整中文实词短语，绝不 4 字贪婪盲切半截词。"""
    kws: List[str] = []
    # 1. 优先捕获带单位的数字或时间词
    for m in re.finditer(r"([0-9一二三四五六七八九十百千万两半\.]+[元块万千百十个年天月日%倍次度件斤克米小时分钟秒]+)", text):
        tok = m.group(1)
        if tok not in kws:
            kws.append(tok)
    # 2. 按虚词、连接词及标点分割语义块，从连续块尾提取 2–4 字完整名动词
    clauses = re.split(r"[，。！？、；：“”‘’（）().,!?;:\s]+|[的了吗呢吧啊呀就把被给从向用凭靠为和与跟而却才都还很太更最]+", text)
    for cl in clauses:
        sub = "".join(ch for ch in cl if "\u4e00" <= ch <= "\u9fff")
        if len(sub) < 2:
            continue
        tok = sub if len(sub) <= 4 else sub[-4:]
        if tok not in _ASR_STOP_WORDS and tok not in kws and all(tok not in existing for existing in kws):
            kws.append(tok)
    return kws[:3]


def _is_content_char_at(text: str, idx: int) -> bool:
    ch = text[idx]
    if ch.isspace():
        return False
    if ch in ".:：" and 0 < idx < len(text) - 1 and text[idx - 1].isdigit() and text[idx + 1].isdigit():
        return True
    return ch not in _PUNCT_STRIP_SET


def _extract_clean_chars(text: str) -> List[str]:
    """抽取正文字符流：剔除常规标点，但保留数字间的 `.` / `:`。"""
    out: List[str] = []
    for idx_c, ch in enumerate(text):
        if not _is_content_char_at(text, idx_c):
            continue
        out.append(":" if (ch == "：" and 0 < idx_c < len(text) - 1 and text[idx_c - 1].isdigit() and text[idx_c + 1].isdigit()) else ch)
    return out


def _word_content_spans(words: List[Dict[str, Any]]) -> Tuple[List[str], List[int]]:
    """按整句拼合边界计算每个 word 的有效字符与有效长度（兼容跨 token 的 18:30）。"""
    raw_strs = [str(w.get("word", "")) for w in words]
    joined = "".join(raw_strs)
    tokens: List[str] = []
    lengths: List[int] = []
    off = 0
    for rs in raw_strs:
        buf: List[str] = []
        for k in range(len(rs)):
            gi = off + k
            if _is_content_char_at(joined, gi):
                ch = joined[gi]
                buf.append(":" if ch == "：" and 0 < gi < len(joined) - 1 and joined[gi - 1].isdigit() and joined[gi + 1].isdigit() else ch)
        tok = "".join(buf)
        tokens.append(tok)
        lengths.append(len(tok))
        off += len(rs)
    return tokens, lengths


def _mark_word_keywords(words: List[Dict[str, Any]], keywords: List[str]) -> None:
    """严格按跨词拼合位置精确标记 is_keyword，彻底杜绝单字巧合命中全局变黄。"""
    if not words or not keywords:
        return
    clean_tokens, _ = _word_content_spans(words)
    spans: List[Tuple[int, int]] = []
    pos = 0
    for w, wt_c in zip(words, clean_tokens):
        spans.append((pos, pos + len(wt_c)))
        pos += len(wt_c)
        w["is_keyword"] = False

    joined = "".join(clean_tokens)
    for kw in keywords:
        kw_c = "".join(_extract_clean_chars(str(kw)))
        if len(kw_c) < 2:
            continue
        start_p = joined.find(kw_c)
        while start_p != -1:
            end_p = start_p + len(kw_c)
            for idx, (s_i, e_i) in enumerate(spans):
                if e_i > s_i and s_i < end_p and e_i > start_p:
                    words[idx]["is_keyword"] = True
            start_p = joined.find(kw_c, start_p + 1)
    for w in words:
        if w.get("is_keyword"):
            w["is_accent"] = True


def load_wav_16k_mono(wav_path: Path) -> Tuple[np.ndarray, int]:
    """统一复用 common.read_wav_as_48k_stereo(target_sr=16000) 并自动拯救单边无线麦故障。"""
    arr, sr = read_wav_as_48k_stereo(wav_path, target_sr=16000)
    if len(arr) > 0:
        arr_fixed, _ = rescue_stereo_channels(arr, imbalance_db=8.0)
        mono = arr_fixed.mean(axis=1).astype(np.float32)
    else:
        mono = np.zeros(0, dtype=np.float32)
    return mono, sr


def compute_10ms_rms(y16: np.ndarray, sr: int = 16000) -> np.ndarray:
    hop = int(sr * 0.010)
    n_hops = max(1, len(y16) // hop)
    trimmed = y16[: n_hops * hop].reshape(n_hops, hop)
    return np.sqrt(np.mean(trimmed ** 2, axis=1) + 1e-10)


def split_chars_energy_aligned(
    text: str,
    start_sec: float,
    end_sec: float,
    keywords: List[str],
    rms_10ms: Optional[np.ndarray] = None,
) -> List[Dict[str, Any]]:
    """基于 10ms 能量包络累积分布将字符映射至声学活动区间，保留数字间小数点/冒号。"""
    clean_chars = _extract_clean_chars(text)

    if not clean_chars:
        return []
    n_c = len(clean_chars)
    total_dur = max(0.03 * n_c, end_sec - start_sec)
    eff_end = start_sec + total_dur if end_sec < start_sec + 0.02 * n_c else end_sec

    if rms_10ms is not None and len(rms_10ms) >= 4:
        i0 = max(0, int(round(start_sec * 100)))
        i1 = min(len(rms_10ms), max(i0 + 2, int(round(eff_end * 100))))
        seg_env = rms_10ms[i0:i1]
        if len(seg_env) >= 2 and float(np.max(seg_env)) > 1e-4:
            weights = seg_env + 0.18 * float(np.mean(seg_env) + 1e-5)
            cdf = np.concatenate([[0.0], np.cumsum(weights)])
            cdf /= max(1e-8, float(cdf[-1]))
            t_grid = np.linspace(start_sec, eff_end, len(cdf))
            q_pts = np.linspace(0.0, 1.0, n_c + 1)
            bounds = np.interp(q_pts, cdf, t_grid)
        else:
            bounds = np.linspace(start_sec, eff_end, n_c + 1)
    else:
        bounds = np.linspace(start_sec, eff_end, n_c + 1)

    min_step = min(0.02, (eff_end - start_sec) / max(1, n_c))
    for i in range(1, len(bounds)):
        bounds[i] = max(bounds[i], bounds[i - 1] + min_step)
    if bounds[-1] > eff_end:
        span_cur = max(1e-6, bounds[-1] - bounds[0])
        bounds = bounds[0] + (bounds - bounds[0]) * ((eff_end - bounds[0]) / span_cur)

    words: List[Dict[str, Any]] = []
    for i, ch in enumerate(clean_chars):
        ws = round(float(bounds[i]), 4)
        we = round(float(bounds[i + 1]), 4)
        if we <= ws:
            we = round(ws + 0.005, 4)
        words.append({
            "word": ch,
            "start_sec": ws,
            "end_sec": we,
            "is_keyword": False,
            "is_accent": False,
            "energy": 0.75,
        })
    _mark_word_keywords(words, keywords)
    return words


def compute_prosody_for_segments(
    wav_path: Path,
    segments: List[Dict[str, Any]],
    audio_pair: Optional[Tuple[np.ndarray, int]] = None,
) -> None:
    """基于收紧后有效语音段计算 RMS 与 YIN F0 声学重音（只对有效段算 F0 提速并精准）。"""
    active_segs = [s for s in segments if not s.get("is_filler") and (s.get("words") or [])]
    if not active_segs:
        return
    if audio_pair is None:
        if not wav_path.exists():
            return
        y16, sr = load_wav_16k_mono(wav_path)
    else:
        y16, sr = audio_pair
    if len(y16) < 400:
        return
    rms_10ms = compute_10ms_rms(y16, sr)

    try:
        import librosa
        has_librosa = True
    except Exception:
        has_librosa = False

    for seg in active_segs:
        words = seg.get("words") or []
        s0 = max(0, int(round(float(seg["start_sec"]) * 100)))
        s1 = min(len(rms_10ms), max(s0 + 1, int(round(float(seg["end_sec"]) * 100))))
        seg_rms = rms_10ms[s0:s1]
        med_rms = float(np.median(seg_rms[seg_rms > 0.005])) if np.any(seg_rms > 0.005) else float(np.mean(seg_rms) + 1e-5)

        seg_f0_arr: Optional[np.ndarray] = None
        seg_f0_med = 0.0
        a0 = max(0, int(round(float(seg["start_sec"]) * sr)))
        a1 = min(len(y16), int(round(float(seg["end_sec"]) * sr)))
        if has_librosa and a1 - a0 >= 1024:
            try:
                f0 = librosa.yin(y16[a0:a1].astype(np.float64), fmin=70.0, fmax=420.0, sr=sr, frame_length=1024, hop_length=160)
                f0 = np.where((f0 >= 75.0) & (f0 <= 390.0), f0, 0.0)
                seg_f0_arr = f0.astype(np.float32)
                vf0 = seg_f0_arr[seg_f0_arr > 0]
                if len(vf0) >= 3:
                    seg_f0_med = float(np.median(vf0))
            except Exception:
                seg_f0_arr = None

        for w in words:
            w0 = min(len(rms_10ms) - 1, max(0, int(round(float(w["start_sec"]) * 100))))
            w1 = min(len(rms_10ms), max(w0 + 1, int(round(float(w["end_sec"]) * 100))))
            w_rms = float(np.percentile(rms_10ms[w0:w1], 80))
            rms_ratio_db = 20.0 * math.log10(max(1e-5, w_rms) / max(1e-5, med_rms))
            rms_score = max(0.15, min(1.0, 0.62 + rms_ratio_db / 14.0))

            f0_score = 0.5
            w_f0 = 0.0
            if seg_f0_arr is not None:
                lw0 = max(0, w0 - s0)
                lw1 = min(len(seg_f0_arr), max(lw0 + 1, w1 - s0))
                wf = seg_f0_arr[lw0:lw1]
                wf = wf[wf > 0]
                if len(wf) > 0 and seg_f0_med > 0:
                    w_f0 = float(np.median(wf))
                    f0_lift = (w_f0 - seg_f0_med) / max(1.0, seg_f0_med)
                    f0_score = max(0.2, min(1.0, 0.55 + f0_lift * 1.4))

            prosody_e = max(0.2, min(1.0, 0.68 * rms_score + 0.32 * f0_score))
            w["energy"] = round(prosody_e, 3)
            if w_f0 > 0:
                w["f0_hz"] = round(w_f0, 1)
            w["is_accent"] = bool(prosody_e >= 0.78 or w.get("is_keyword", False))
        seg["energy_score"] = round(
            sum(float(w.get("energy", 0.5)) for w in words) / float(max(1, len(words))),
            3,
        )


def vad_speech_intervals(y16: np.ndarray, sr: int = 16000) -> List[Tuple[float, float]]:
    """基于 20ms RMS 的纯物理语音活动区间检测 (VAD)。"""
    hop = int(sr * 0.020)
    n_hops = max(1, len(y16) // hop)
    rms = np.sqrt(np.mean(y16[: n_hops * hop].reshape(n_hops, hop) ** 2, axis=1) + 1e-10)
    noise_floor = float(np.percentile(rms, 20))
    thresh = max(0.008, noise_floor * 2.4)
    active = rms >= thresh

    raw_spans: List[Tuple[float, float]] = []
    in_seg = False
    st = 0
    for i, act in enumerate(active):
        if act and not in_seg:
            in_seg = True
            st = i
        elif not act and in_seg:
            in_seg = False
            raw_spans.append((st * 0.020, i * 0.020))
    if in_seg:
        raw_spans.append((st * 0.020, n_hops * 0.020))

    merged: List[Tuple[float, float]] = []
    for s, e in raw_spans:
        if merged and s - merged[-1][1] < 0.18:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    return [(round(s, 4), round(e, 4)) for s, e in merged if e - s >= 0.16]


def _get_whisper_model(model_name: str) -> Any:
    return get_cached_whisper_model(model_name, device="cpu", compute_type="int8", local_files_only=True)


def try_faster_whisper(
    wav_path: Path,
    model_name: Optional[str] = None,
    y16_cached: Optional[np.ndarray] = None,
    dialect: str = "mandarin",
    store_anchor: Optional[str] = None,
) -> Optional[List[Dict[str, Any]]]:
    """使用进程级单例 Faster-Whisper 提取词级时间戳；直接喂入内存 16k 音频避免二次解码，接入方言与店名热词提示。"""
    try:
        y16 = y16_cached if y16_cached is not None else load_wav_16k_mono(wav_path)[0]
        global_rms = float(np.sqrt(np.mean(y16 ** 2) + 1e-12)) if len(y16) else 0.0
        if global_rms < 0.002 or not vad_speech_intervals(y16, 16000):
            return []
        chosen = model_name or find_cached_whisper_model()
        if not chosen:
            return None
        model = _get_whisper_model(chosen)
        lang_code = "yue" if str(dialect or "").lower() == "cantonese" else "zh"
        anchor_hint = f"相关品牌或门店关键词：{store_anchor}。" if store_anchor else ""
        prompt = (
            f"以下为粤语真实口播内容，请保留准确口语词。{anchor_hint}"
            if lang_code == "yue"
            else f"以下是简体中文真实口播内容，请准确识别数字、价格与专有名词。{anchor_hint}"
        )
        segments, _ = model.transcribe(
            y16.astype(np.float32, copy=False),
            language=lang_code,
            initial_prompt=prompt,
            word_timestamps=True,
            vad_filter=True,
        )
        rms_10ms = compute_10ms_rms(y16)
        out = []
        for idx, seg in enumerate(segments, start=1):
            text = seg.text.strip()
            if not text:
                continue
            is_filler = is_filler_or_director_cue(text)
            kws = [] if is_filler else extract_auto_keywords(text)
            words = []
            for w in getattr(seg, "words", []) or []:
                wt = w.word.strip()
                if not wt:
                    continue
                words.append({
                    "word": wt,
                    "start_sec": round(float(w.start), 4),
                    "end_sec": round(float(w.end), 4),
                    "is_keyword": False,
                    "is_accent": False,
                    "energy": 0.75,
                })
            if words:
                _mark_word_keywords(words, kws)
            else:
                words = split_chars_energy_aligned(text, float(seg.start), float(seg.end), kws, rms_10ms=rms_10ms)
            out.append({
                "id": f"seg_{idx:03d}",
                "text": text,
                "start_sec": round(float(seg.start), 4),
                "end_sec": round(float(seg.end), 4),
                "is_filler": is_filler,
                "emotion": "filler" if is_filler else "info",
                "keywords": kws,
                "words": words,
            })
        return out if out else None
    except Exception:
        return None


def align_script_to_existing_wav(
    wav_path: Path,
    script_items: List[Dict[str, Any]],
    source_media: str,
    model_name: Optional[str] = None,
    audio_pair: Optional[Tuple[np.ndarray, int]] = None,
    dialect: str = "mandarin",
    store_anchor: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], str]:
    """将已知台词对齐到现有 WAV：优先使用 Whisper 句界+文本相似度核验，退化才用字符配比或 VAD。"""
    y16, sr = audio_pair if audio_pair is not None else load_wav_16k_mono(wav_path)
    rms_10ms = compute_10ms_rms(y16, sr)
    total_dur = len(y16) / float(sr) if sr > 0 else 0.0

    asr_segs = try_faster_whisper(
        wav_path, model_name=model_name, y16_cached=y16, dialect=dialect, store_anchor=store_anchor
    )
    if asr_segs:
        core_asr = [s for s in asr_segs if not is_filler_or_director_cue(s["text"])] or asr_segs
        if len(core_asr) == len(script_items):
            sims = [
                difflib.SequenceMatcher(None, _clean_zh_text(it["text"]), _clean_zh_text(aseg["text"])).ratio()
                for it, aseg in zip(script_items, core_asr)
            ]
            avg_sim = (sum(sims) / len(sims)) if sims else 0.0
            if avg_sim >= 0.35:
                segments: List[Dict[str, Any]] = []
                for idx, (item, aseg) in enumerate(zip(script_items, core_asr), start=1):
                    s_sec, e_sec = float(aseg["start_sec"]), float(aseg["end_sec"])
                    kws = item.get("keywords", []) or extract_auto_keywords(item["text"])
                    is_f = bool(item.get("is_filler", False)) or is_filler_or_director_cue(item["text"])
                    if aseg.get("words") and _clean_zh_text("".join(w["word"] for w in aseg["words"])) == _clean_zh_text(item["text"]):
                        w_list = [dict(w) for w in aseg["words"]]
                        _mark_word_keywords(w_list, kws)
                    else:
                        w_list = split_chars_energy_aligned(item["text"], s_sec, e_sec, kws, rms_10ms=rms_10ms)
                    segments.append({
                        "id": f"seg_{idx:03d}",
                        "text": item["text"],
                        "start_sec": round(s_sec, 4),
                        "end_sec": round(e_sec, 4),
                        "source_media": source_media,
                        "source_audio": str(wav_path.resolve()),
                        "is_filler": is_f,
                        "emotion": "filler" if is_f else item.get("emotion", "info"),
                        "keywords": kws,
                        "words": w_list,
                    })
                return segments, "asr_script_forced"
        # 句数略有差异时保留 Whisper 整体活动区间 [(s,e)...] 做字符配比，比纯能量 VAD 更精准！
        vad_spans = [(float(s["start_sec"]), float(s["end_sec"])) for s in core_asr if float(s["end_sec"]) > float(s["start_sec"])]
        mode_tag = "asr_char_mapped"
    else:
        vad_spans = vad_speech_intervals(y16, sr)
        mode_tag = "vad_energy_aligned"

    if not vad_spans:
        vad_spans = [(0.0, total_dur)]

    active_total = sum(e - s for s, e in vad_spans)
    char_counts = [max(2, len(_clean_zh_text(it["text"]))) for it in script_items]
    total_chars = max(1, sum(char_counts))

    cum_virt = [0.0]
    for s, e in vad_spans:
        cum_virt.append(cum_virt[-1] + (e - s))

    def virt_to_real(vt: float) -> float:
        vt = max(0.0, min(active_total, vt))
        for idx, (s, e) in enumerate(vad_spans):
            if vt <= cum_virt[idx + 1] + 1e-6:
                return round(s + (vt - cum_virt[idx]), 4)
        return round(vad_spans[-1][1], 4)

    segments = []
    v_cursor = 0.0
    for idx, (item, cc) in enumerate(zip(script_items, char_counts), start=1):
        v_dur = active_total * (cc / float(total_chars))
        s_sec = virt_to_real(v_cursor)
        e_sec = virt_to_real(min(active_total, v_cursor + v_dur))
        v_cursor += v_dur
        if e_sec <= s_sec:
            e_sec = round(min(total_dur, s_sec + 0.25), 4)
        kws = item.get("keywords", []) or extract_auto_keywords(item["text"])
        is_f = bool(item.get("is_filler", False)) or is_filler_or_director_cue(item["text"])
        segments.append({
            "id": f"seg_{idx:03d}",
            "text": item["text"],
            "start_sec": s_sec,
            "end_sec": e_sec,
            "source_media": source_media,
            "source_audio": str(wav_path.resolve()),
            "is_filler": is_f,
            "emotion": "filler" if is_f else item.get("emotion", "info"),
            "keywords": kws,
            "words": split_chars_energy_aligned(item["text"], s_sec, e_sec, kws, rms_10ms=rms_10ms),
        })
    return segments, mode_tag


def _extract_segment_acoustic_sig(y16: np.ndarray, sr: int, s_sec: float, e_sec: float) -> Dict[str, Any]:
    """向量化 STFT 计算整句有效发声帧的 8 频段对数能量轮廓、质心与句内卡壳停顿。"""
    i0 = max(0, int(round(s_sec * sr)))
    i1 = min(len(y16), max(i0 + 400, int(round(e_sec * sr))))
    seg = y16[i0:i1]
    if len(seg) < 400:
        return {"rms_db": -60.0, "centroid": 0.0, "bands": np.zeros(8, dtype=np.float32), "internal_pauses": 0}

    frame_len = min(400, len(seg))
    hop = 160
    n_frames = 1 + (len(seg) - frame_len) // hop
    if n_frames <= 0:
        return {"rms_db": -60.0, "centroid": 0.0, "bands": np.zeros(8, dtype=np.float32), "internal_pauses": 0}

    strides = seg.strides[0]
    frames = np.lib.stride_tricks.as_strided(seg, shape=(n_frames, frame_len), strides=(hop * strides, strides))
    rms_arr = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
    win = np.hanning(frame_len).astype(np.float32)
    spec = np.abs(np.fft.rfft(frames * win, axis=1))
    freqs = np.fft.rfftfreq(frame_len, 1.0 / sr)
    tot_e = np.sum(spec, axis=1, keepdims=True) + 1e-8
    cent_arr = np.sum(spec * freqs[None, :], axis=1) / tot_e[:, 0]

    band_edges = [80, 220, 450, 850, 1400, 2200, 3500, 5200, 7600]
    b_cols = []
    for bi in range(len(band_edges) - 1):
        m = (freqs >= band_edges[bi]) & (freqs < band_edges[bi + 1])
        b_cols.append(np.sum(spec[:, m], axis=1) / tot_e[:, 0])
    bands_mat = np.stack(b_cols, axis=1)  # (n_frames, 8)
    bands_log = np.log1p(bands_mat * 30.0)
    bands_log /= np.maximum(1e-6, np.linalg.norm(bands_log, axis=1, keepdims=True))

    peak_r = float(np.max(rms_arr))
    active_mask = rms_arr >= max(0.004, peak_r * 0.18)
    if not np.any(active_mask):
        active_mask = np.ones_like(rms_arr, dtype=bool)

    eff_rms = float(np.median(rms_arr[active_mask]))
    rms_db = 20.0 * math.log10(max(1e-6, eff_rms))
    bands_mean = np.mean(bands_log[active_mask], axis=0)
    centroid = float(np.median(cent_arr[active_mask]))

    sil_gaps = 0
    in_gap = False
    gap_len = 0
    sil_thr = max(0.003, eff_rms * 0.25)
    for r in rms_arr[::2]:
        if r < sil_thr:
            gap_len = gap_len + 1 if in_gap else 1
            in_gap = True
        else:
            if in_gap and gap_len >= 7:
                sil_gaps += 1
            in_gap = False
            gap_len = 0

    return {
        "rms_db": round(rms_db, 2),
        "centroid": round(centroid, 1),
        "bands": bands_mean.astype(np.float32),
        "internal_pauses": sil_gaps,
    }


def filter_offcamera_and_retakes(
    segments: List[Dict[str, Any]],
    audio_cache: Optional[Dict[str, Tuple[np.ndarray, int]]] = None,
    multi_speaker: bool = False,
) -> Dict[str, int]:
    """按 source_audio 各自独立分组剥离画外远场导演声（multi_speaker=True 时保护双人对话），并严谨收敛 NG 重复重录择优。"""
    cache = audio_cache if audio_cache is not None else {}
    sigs: List[Optional[Dict[str, Any]]] = []
    by_source: Dict[str, List[int]] = {}
    seg_source_keys: List[str] = []

    for idx, seg in enumerate(segments):
        sa = seg.get("source_audio")
        if sa and Path(sa).exists():
            sa_key = str(Path(sa).resolve())
            if sa_key not in cache:
                cache[sa_key] = load_wav_16k_mono(Path(sa))
            y16, sr = cache[sa_key]
            sigs.append(_extract_segment_acoustic_sig(y16, sr, float(seg["start_sec"]), float(seg["end_sec"])))
            by_source.setdefault(sa_key, []).append(idx)
            seg_source_keys.append(sa_key)
        else:
            sigs.append(None)
            seg_source_keys.append("")

    offcam_dropped = 0
    primary_rms_by_source: Dict[str, float] = {}
    for sa_key, idx_list in by_source.items():
        valid_rms = sorted([sigs[i]["rms_db"] for i in idx_list if sigs[i] and not segments[i].get("is_filler")], reverse=True)
        if len(valid_rms) < 3:
            if valid_rms:
                primary_rms_by_source[sa_key] = valid_rms[0]
            continue
        top_n = max(2, int(math.ceil(len(valid_rms) * 0.65)))
        primary_rms = float(np.median(valid_rms[:top_n]))
        primary_rms_by_source[sa_key] = primary_rms
        core_bands = [
            sigs[i]["bands"] for i in idx_list
            if sigs[i] and not segments[i].get("is_filler") and sigs[i]["rms_db"] >= primary_rms - 6.0
        ]
        primary_band = np.mean(core_bands, axis=0) if core_bands else None

        for i in idx_list:
            seg, sg = segments[i], sigs[i]
            if seg.get("is_filler") or not sg:
                continue
            seg["acoustic_rms_db"] = sg["rms_db"]
            if multi_speaker:
                continue
            db_drop = primary_rms - sg["rms_db"]
            spec_dist = float(np.linalg.norm(sg["bands"] - primary_band)) if primary_band is not None else 0.0
            if (db_drop >= 9.0 and spec_dist >= 0.14) or db_drop >= 12.0:
                seg["is_filler"] = True
                seg["emotion"] = "filler"
                seg["drop_reason"] = f"offcamera_speaker (rms_drop={db_drop:.1f}dB, spec_dist={spec_dist:.2f})"
                offcam_dropped += 1

    active_indices = [i for i, s in enumerate(segments) if not s.get("is_filler")]
    retake_dropped = 0
    for pos_a in range(len(active_indices)):
        i = active_indices[pos_a]
        if segments[i].get("is_filler"):
            continue
        ci = _clean_zh_text(segments[i]["text"])
        if len(ci) < 4:
            continue

        group = [i]
        for pos_b in range(pos_a + 1, min(len(active_indices), pos_a + 5)):
            j = active_indices[pos_b]
            if segments[j].get("is_filler"):
                continue
            cj = _clean_zh_text(segments[j]["text"])
            if len(cj) < 4:
                continue
            sim = difflib.SequenceMatcher(None, ci, cj).ratio()
            common_pref = 0
            for a_c, b_c in zip(ci, cj):
                if a_c == b_c:
                    common_pref += 1
                else:
                    break
            # 防排比句误杀：需整句高相似 >=0.76，或前缀重合>=5字且后句明显覆盖前句
            if sim >= 0.76 or (common_pref >= 5 and len(cj) > len(ci)):
                group.append(j)

        if len(group) > 1:
            best_idx = group[0]
            best_score = -1e9
            for order_k, gi in enumerate(group):
                sg = sigs[gi]
                txt_c = _clean_zh_text(segments[gi]["text"])
                internal_pauses = sg["internal_pauses"] if sg else 0
                ref_rms = primary_rms_by_source.get(seg_source_keys[gi], -20.0)
                rms_db = sg["rms_db"] if sg else ref_rms
                fluency_bonus = 8.0 if txt_c[-1:] not in ("呃", "啊", "那", "这") else -6.0
                energy_pen = max(0.0, (ref_rms - rms_db) * 1.5)
                sc = len(txt_c) * 1.4 + fluency_bonus - (internal_pauses * 5.0) - energy_pen + (order_k * 1.2)
                if sc > best_score:
                    best_score = sc
                    best_idx = gi

            for gi in group:
                if gi != best_idx:
                    segments[gi]["is_filler"] = True
                    segments[gi]["emotion"] = "filler"
                    segments[gi]["drop_reason"] = f"ng_retake (superseded_by={segments[best_idx]['id']})"
                    retake_dropped += 1

    return {"offcamera_dropped": offcam_dropped, "retake_dropped": retake_dropped}


NEGATION_CHARS = set("不没别非无莫唔冇")
PARTICLE_STRIP_RE = re.compile(r"[的了啊呢吗吧就也都还很太着过把被给]+")
LIST_ENUM_RE = re.compile(r"^(?:第[一二三四五六七八九十123456789]|[一二三四五六七八九十][是点个种步条]|首先|其次|最后)")
ANOMALY_QTY_RE = re.compile(r"([十百千万亿\d]+(?:\.\d+)?)\s*(万米|亿米|亿块|万吨|万元一[碗串份]|千度|万度)")


def refine_word_boundaries_with_energy(
    segments: List[Dict[str, Any]],
    audio_cache: Optional[Dict[str, Tuple[np.ndarray, int]]] = None,
) -> int:
    """用 10ms 真实语音能量包络收紧句首前导与句尾长静音，防止字幕或切点漂移。"""
    cache_rms: Dict[str, np.ndarray] = {}
    if audio_cache:
        for k, (y16, sr16) in audio_cache.items():
            cache_rms[k] = compute_10ms_rms(y16, sr16)
    adjusted = 0
    for seg in segments:
        if seg.get("is_filler"):
            continue
        sa = seg.get("source_audio")
        if not sa or not Path(sa).is_file():
            continue
        sa_key = str(Path(sa).resolve())
        if sa_key not in cache_rms:
            y16, sr16 = load_wav_16k_mono(Path(sa))
            cache_rms[sa_key] = compute_10ms_rms(y16, sr16)
        rms_10ms = cache_rms[sa_key]
        if len(rms_10ms) < 5:
            continue

        words = seg.get("words") or []
        s0 = max(0, int(round(float(seg["start_sec"]) * 100)))
        s1 = min(len(rms_10ms), max(s0 + 2, int(round(float(seg["end_sec"]) * 100))))
        seg_env = rms_10ms[s0:s1]
        if len(seg_env) < 5:
            continue
        nonzero = seg_env[seg_env > 0.004]
        p75 = float(np.percentile(nonzero, 75)) if len(nonzero) >= 3 else float(np.max(seg_env))
        thr = max(0.008, p75 * 0.16)

        # 收紧句首前导长静音 (> 150ms)，同步单调顺推防止制造负时长字
        seg_act = np.where(seg_env >= thr)[0]
        if len(seg_act) > 0 and int(seg_act[0]) >= 15:
            lead_hop = max(0, int(seg_act[0]) - 3)
            new_seg_start = round(float(seg["start_sec"]) + lead_hop * 0.010, 4)
            if words and new_seg_start < float(words[-1]["end_sec"]) - 0.15:
                seg["start_sec"] = new_seg_start
                cur_floor = new_seg_start
                seg_end_cap = float(seg["end_sec"])
                for w_fix in words:
                    ws = max(float(w_fix["start_sec"]), cur_floor)
                    we = max(float(w_fix["end_sec"]), min(seg_end_cap, ws + 0.03))
                    if we < ws:
                        we = ws
                    w_fix["start_sec"] = round(ws, 4)
                    w_fix["end_sec"] = round(we, 4)
                    cur_floor = we
                adjusted += 1

        for w in words:
            w0 = max(0, int(round(float(w["start_sec"]) * 100)))
            w1 = min(len(rms_10ms), int(round(float(w["end_sec"]) * 100)))
            if w1 - w0 >= 28:
                w_env = rms_10ms[w0:w1]
                active_idx = np.where(w_env >= thr)[0]
                if len(active_idx) > 0:
                    last_act = int(active_idx[-1])
                    tail_sil_hops = (len(w_env) - 1) - last_act
                    if tail_sil_hops >= 25:
                        new_end = round(float(w["start_sec"]) + (last_act + 4) * 0.010, 4)
                        new_end = max(float(w["start_sec"]) + 0.06, min(float(w["end_sec"]), new_end))
                        if new_end < float(w["end_sec"]) - 0.10:
                            w["end_sec"] = new_end
                            adjusted += 1

        if words:
            last_w_end = float(words[-1]["end_sec"])
            if float(seg["end_sec"]) - last_w_end >= 0.25:
                seg["end_sec"] = round(max(float(seg["start_sec"]) + 0.15, last_w_end + 0.05), 4)
    return adjusted


def detect_prompt_stumbles(segments: List[Dict[str, Any]]) -> int:
    """A1 提词半截词精准识别：仅在同一段原始音频内对比相邻有效句间隔。"""
    active = [i for i, s in enumerate(segments) if not s.get("is_filler")]
    dropped = 0
    for k in range(len(active) - 1):
        i_prev = active[k]
        i_next = active[k + 1]
        prev_s = segments[i_prev]
        next_s = segments[i_next]
        sa_prev = prev_s.get("source_audio")
        sa_next = next_s.get("source_audio")
        if sa_prev and sa_next and str(sa_prev) != str(sa_next):
            continue
        gap = float(next_s["start_sec"]) - float(prev_s["end_sec"])
        if gap < 0.90:
            continue
        p_raw = _clean_zh_text(prev_s["text"])
        n_raw = _clean_zh_text(next_s["text"])
        if not (2 <= len(p_raw) <= 7):
            continue
        if LIST_ENUM_RE.match(p_raw) or LIST_ENUM_RE.match(n_raw):
            continue
        p_core = PARTICLE_STRIP_RE.sub("", p_raw)
        n_core = PARTICLE_STRIP_RE.sub("", n_raw)
        if len(p_core) < 2 or len(n_core) < 2:
            continue
        if p_core[:2] == n_core[:2] or (len(p_core) >= 3 and p_core[:3] in n_core[:6]):
            prev_s["is_filler"] = True
            prev_s["emotion"] = "filler"
            prev_s["drop_reason"] = f"prompt_stumble (gap={gap:.2f}s, superseded_by={next_s['id']})"
            dropped += 1
    return dropped


def _sync_words_with_clean_text(words: List[Dict[str, Any]], clean_new: List[str]) -> None:
    """等长替换后同步更新 words，保留数字间 `:` / `.` 并跳过纯标点占位 token 防错位。"""
    if not words:
        return
    clean_norm = _extract_clean_chars("".join(clean_new))
    _, wt_lens = _word_content_spans(words)
    non_punct_indices = [idx for idx, wt_len in enumerate(wt_lens) if wt_len > 0]
    if len(clean_norm) == len(non_punct_indices):
        for idx, ch in zip(non_punct_indices, clean_norm):
            words[idx]["word"] = ch
        return
    cursor = 0
    total = len(clean_norm)
    for pos_k, idx in enumerate(non_punct_indices):
        w = words[idx]
        wt_len = wt_lens[idx]
        if wt_len == 0:
            continue
        if pos_k == len(non_punct_indices) - 1:
            w["word"] = "".join(clean_norm[cursor:]) if cursor < total else w["word"]
        else:
            w["word"] = "".join(clean_norm[cursor : min(total, cursor + wt_len)]) or w["word"]
            cursor = min(total, cursor + wt_len)


def apply_semantic_sanity_check(
    segments: List[Dict[str, Any]],
    replacements: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    """A5 上屏前语义常识校对（等长替换同步词组时间戳 + 否定词守卫 + 数量级预警）。"""
    warnings: List[Dict[str, Any]] = []
    rep_map = dict(replacements or {})

    for seg in segments:
        if seg.get("is_filler"):
            continue
        txt = str(seg.get("text") or "")
        for m in ANOMALY_QTY_RE.finditer(txt):
            warnings.append({
                "sentence_id": seg.get("id"),
                "type": "anomaly_quantity",
                "term": m.group(0),
                "text": txt,
                "needs_confirm": True,
                "reason": "检测到疑似 ASR 听错引起的反常数量级，请人工复核",
            })

        for old, new in rep_map.items():
            if old not in txt:
                continue
            if any(ch in NEGATION_CHARS for ch in (old + new)):
                warnings.append({
                    "sentence_id": seg.get("id"),
                    "type": "negation_guard_blocked",
                    "old": old,
                    "new": new,
                    "text": txt,
                    "needs_confirm": True,
                    "reason": "涉及否定词语义反转，禁止静默自动替换",
                })
                continue
            if len(old) != len(new):
                warnings.append({
                    "sentence_id": seg.get("id"),
                    "type": "non_equal_length_blocked",
                    "old": old,
                    "new": new,
                    "text": txt,
                    "needs_confirm": True,
                    "reason": "替换词不等长会导致逐字时间戳漂移，已阻断自动替换",
                })
                continue
            pos = txt.find(old)
            while pos != -1:
                txt = txt[:pos] + new + txt[pos + len(old):]
                pos = txt.find(old, pos + len(new))
            seg["text"] = txt
            clean_new = _extract_clean_chars(txt)
            _sync_words_with_clean_text(seg.get("words") or [], clean_new)
    return warnings


def _measure_wav_speech_extent(wav_path: Path, sr_target: int = 16000) -> Tuple[float, float, float]:
    """实测合成 WAV 10ms RMS 真实语流起止点 (db > peak_db - 38dB)，并返回 (dur, onset_sec, offset_sec)。"""
    dur = get_wav_duration_sec(wav_path)
    try:
        y16, sr = load_wav_16k_mono(wav_path)
        hop = max(1, int(0.010 * sr))
        n_fr = len(y16) // hop
        if n_fr <= 0:
            return dur, 0.0, dur
        fr = y16[: n_fr * hop].reshape(n_fr, hop)
        rms = np.sqrt(np.mean(fr ** 2, axis=1) + 1e-10)
        db = 20.0 * np.log10(rms + 1e-9)
        on = np.flatnonzero(db > (float(np.max(db)) - 38.0))
        if len(on) > 0:
            onset_sec = round(float(on[0]) * 0.010, 4)
            offset_sec = round(min(dur, float(on[-1] + 1) * 0.010), 4)
            return dur, onset_sec, max(onset_sec + 0.05, offset_sec)
    except Exception:
        pass
    return dur, 0.0, dur


def synthesize_tts_segment_detailed(
    speak_text: str,
    out_wav: Path,
    voice: str = "zh-CN-YunxiNeural",
    rate: str = "+8%",
    cache_dir: Optional[Path] = None,
) -> Tuple[bool, float, List[Dict[str, Any]], float, float]:
    """
    合成单句 48kHz 立体声 WAV 并采集精准 WordBoundary + 10ms RMS 起音修正：
    - 句级隔离缓存（默认 ~/.short-video-studio/cache/tts）避免重复请求；
    - edge-tts 流式采集 WordBoundary，自带 3 次重试并将 word offset 平移对齐至真实声波 onset（纠偏 ~40–55ms 提前量）；
    - 返回 (ok, duration_sec, shifted_words, measured_onset_sec, measured_offset_sec)。
    """
    ffmpeg = find_bin("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("需要 ffmpeg 转换 TTS 音频格式。")

    eff_cache = cache_dir if cache_dir is not None else (Path.home() / ".short-video-studio" / "cache" / "tts")
    cache_key = hashlib.sha256(f"{speak_text}|{voice}|{rate}".encode("utf-8")).hexdigest()[:20]
    c_wav = eff_cache / f"{cache_key}.wav"
    c_meta = eff_cache / f"{cache_key}.json"

    if c_wav.is_file() and c_meta.is_file() and c_wav.stat().st_size > 1000:
        try:
            if get_wav_duration_sec(c_wav) > 0.1:
                meta = read_json(c_meta)
                out_wav.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(c_wav, out_wav)
                return (
                    True,
                    float(meta.get("duration", get_wav_duration_sec(out_wav))),
                    list(meta.get("words") or []),
                    float(meta.get("onset_sec", 0.0)),
                    float(meta.get("offset_sec", get_wav_duration_sec(out_wav))),
                )
        except Exception:
            pass

    tmp_raw = out_wav.with_suffix(".raw.mp3")
    raw_words: List[Dict[str, Any]] = []
    try:
        import edge_tts

        async def _run_edge() -> List[Dict[str, Any]]:
            comm = edge_tts.Communicate(speak_text, voice=voice, rate=rate, boundary="WordBoundary")
            w_list: List[Dict[str, Any]] = []
            with open(tmp_raw, "wb") as f_mp3:
                async for ch in comm.stream():
                    ctype = ch.get("type")
                    if ctype == "audio":
                        f_mp3.write(ch["data"])
                    elif ctype == "WordBoundary":
                        t0 = float(ch.get("offset", 0.0)) / 1e7
                        dt = float(ch.get("duration", 0.0)) / 1e7
                        wt = str(ch.get("text") or "").strip()
                        if wt:
                            w_list.append({
                                "word": wt,
                                "start_sec": round(t0, 4),
                                "end_sec": round(max(t0 + 0.02, t0 + dt), 4),
                            })
            return w_list

        for attempt in range(3):
            try:
                raw_words = asyncio.run(_run_edge())
                if tmp_raw.exists() and tmp_raw.stat().st_size > 500:
                    break
            except Exception:
                tmp_raw.unlink(missing_ok=True)
                if attempt == 2:
                    raise

        if tmp_raw.exists() and tmp_raw.stat().st_size > 500:
            run_cmd([
                ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(tmp_raw), "-ar", "48000", "-ac", "2", "-acodec", "pcm_s16le",
                str(out_wav),
            ])
            tmp_raw.unlink(missing_ok=True)
            dur, onset_sec, offset_sec = _measure_wav_speech_extent(out_wav)
            if dur > 0.1:
                if raw_words:
                    shift = onset_sec - float(raw_words[0]["start_sec"])
                    shifted = []
                    for w in raw_words:
                        ws = max(0.0, min(dur - 0.02, float(w["start_sec"]) + shift))
                        we = max(ws + 0.02, min(dur, float(w["end_sec"]) + shift))
                        shifted.append({"word": w["word"], "start_sec": round(ws, 4), "end_sec": round(we, 4)})
                    raw_words = shifted
                try:
                    eff_cache.mkdir(parents=True, exist_ok=True)
                    with tempfile.NamedTemporaryFile(dir=eff_cache, suffix=".wav", delete=False) as tf:
                        pending_wav = Path(tf.name)
                    shutil.copy2(out_wav, pending_wav)
                    os.replace(pending_wav, c_wav)
                    write_json(c_meta, {
                        "speak_text": speak_text, "voice": voice, "rate": rate,
                        "duration": dur, "onset_sec": onset_sec, "offset_sec": offset_sec, "words": raw_words,
                    })
                except Exception:
                    pass
                return True, dur, raw_words, onset_sec, offset_sec
    except Exception:
        tmp_raw.unlink(missing_ok=True)

    say_bin = find_bin("say")
    if say_bin:
        print(f"[step2] [WARN] edge-tts 不可用，降级使用系统 say 合成：{speak_text[:20]}")
        tmp_aiff = out_wav.with_suffix(".aiff")
        try:
            run_cmd([say_bin, "-r", "215", "-o", str(tmp_aiff), speak_text])
            if tmp_aiff.exists() and tmp_aiff.stat().st_size > 500:
                run_cmd([
                    ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                    "-i", str(tmp_aiff), "-ar", "48000", "-ac", "2", "-acodec", "pcm_s16le",
                    str(out_wav),
                ])
                tmp_aiff.unlink(missing_ok=True)
                dur, onset_sec, offset_sec = _measure_wav_speech_extent(out_wav)
                if dur > 0.1:
                    return True, dur, [], onset_sec, offset_sec
        except Exception:
            tmp_aiff.unlink(missing_ok=True)

    raise RuntimeError(f"TTS 配音合成失败（edge-tts 与系统 say 均不可用），拒绝输出电子合成假语音：{speak_text[:24]}")


_ZH_DIGIT_MAP = {
    "0": "零", "1": "一", "2": "二", "3": "三", "4": "四",
    "5": "五", "6": "六", "7": "七", "8": "八", "9": "九",
    ".": "点", ":": "比", "%": "百分之", "¥": "元", "$": "美元",
}


def _int_to_zh_spoken(num_str: str) -> str:
    """将阿拉伯整数串转为标准中文读法（如 '280' -> '二百八十', '68' -> '六十八'）用于跨通道发音锚点对齐。"""
    if not num_str.isdigit():
        return "".join(_ZH_DIGIT_MAP.get(c, c) for c in num_str)
    n = int(num_str)
    if n == 0:
        return "零"
    if n >= 10000 or (len(num_str) == 4 and num_str.startswith(("19", "20"))):
        return "".join(_ZH_DIGIT_MAP.get(c, c) for c in num_str)
    units = ["", "十", "百", "千"]
    digits = list(num_str)
    L = len(digits)
    res: List[str] = []
    zero_pending = False
    for i, d_ch in enumerate(digits):
        d = int(d_ch)
        pos = L - 1 - i
        if d == 0:
            zero_pending = True
        else:
            if zero_pending and res:
                res.append("零")
            zero_pending = False
            if not (d == 1 and pos == 1 and not res):
                res.append(_ZH_DIGIT_MAP[d_ch])
            if units[pos]:
                res.append(units[pos])
    return "".join(res) or "零"


def _char_to_phonetic_key(ch: str) -> str:
    c = ch.lower()
    if c == "两":
        return "二"
    return _ZH_DIGIT_MAP.get(c, c)


def _expand_word_boundaries_for_subtitles(
    wb_words: List[Dict[str, Any]],
    s_offset_sec: float,
    keywords: List[str],
    rms_10ms: Optional[np.ndarray],
) -> List[Dict[str, Any]]:
    """将 WordBoundary 词段转为字幕友好字符/数字单元并标注关键词。"""
    expanded: List[Dict[str, Any]] = []
    for w in wb_words:
        tok = str(w.get("word") or "").strip()
        if not tok:
            continue
        t0 = float(w["start_sec"]) + s_offset_sec
        t1 = max(t0 + 0.02, float(w["end_sec"]) + s_offset_sec)
        if re.fullmatch(r"[0-9A-Za-z.:/%+\-]+", tok):
            pieces = [tok]
        else:
            pieces = _extract_clean_chars(tok) or [tok]
        n_p = len(pieces)
        dt = (t1 - t0) / float(max(1, n_p))
        for k, pch in enumerate(pieces):
            pt0 = t0 + k * dt
            pt1 = max(pt0 + 0.02, t0 + (k + 1) * dt)
            e_val = 0.72
            if rms_10ms is not None and len(rms_10ms) >= 4:
                i0 = min(len(rms_10ms) - 1, max(0, int(round(pt0 * 100))))
                i1 = min(len(rms_10ms), max(i0 + 1, int(round(pt1 * 100))))
                e_val = float(np.mean(rms_10ms[i0:i1]))
            expanded.append({
                "word": pch,
                "start_sec": round(pt0, 4),
                "end_sec": round(pt1, 4),
                "energy": round(min(1.0, e_val * 5.0), 3),
                "is_keyword": False,
            })
    _mark_word_keywords(expanded, keywords)
    return expanded


def _project_say_words_to_show(
    wb_words: List[Dict[str, Any]],
    show_text: str,
    s_offset_sec: float,
    e_sec: float,
    keywords: List[str],
    rms_10ms: Optional[np.ndarray],
    m_on: float = 0.0,
    m_off: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    跨通道发音->视觉词边界单调投射：
    即使口播 say（如 '二百八十元，占百分之六十八'）与上屏 show（如 '280元占68%'）不同，
    依然通过数字读音展开 + 单调 LCS 锚点插值将 edge-tts 真实 WordBoundary 投射到 show 的每个字符上。
    """
    show_chars = _extract_clean_chars(show_text)
    if not show_chars:
        return []
    if not wb_words:
        eff_s = min(e_sec - 0.1, s_offset_sec + m_on)
        eff_e = max(eff_s + 0.1, min(e_sec, s_offset_sec + (m_off if m_off > m_on else (e_sec - s_offset_sec))))
        return split_chars_energy_aligned(show_text, eff_s, eff_e, keywords, rms_10ms=rms_10ms)

    say_stream: List[Tuple[str, float, float]] = []
    for w in wb_words:
        tok = str(w.get("word") or "").strip()
        if not tok:
            continue
        t0 = float(w["start_sec"]) + s_offset_sec
        t1 = max(t0 + 0.015, float(w["end_sec"]) + s_offset_sec)
        if tok.isdigit():
            p_chars = list(_int_to_zh_spoken(tok))
        elif re.fullmatch(r"\d+(?:\.\d+)?%", tok):
            num_part = tok[:-1]
            spoken = _int_to_zh_spoken(num_part) if num_part.isdigit() else num_part.replace(".", "点")
            p_chars = list("百分之" + spoken)
        elif re.search(r"\d+", tok):
            p_chars = []
            for part in re.findall(r"\d+|[^\d]+", tok):
                if part.isdigit():
                    p_chars.extend(list(_int_to_zh_spoken(part)))
                else:
                    p_chars.extend(_char_to_phonetic_key(c) for c in (_extract_clean_chars(part) or list(part)))
        else:
            raw_c = _extract_clean_chars(tok) or list(tok)
            p_chars = [_char_to_phonetic_key(c) for c in raw_c]
        n_c = max(1, len(p_chars))
        dt = (t1 - t0) / float(n_c)
        for k, pc in enumerate(p_chars):
            say_stream.append((pc, t0 + k * dt, t0 + (k + 1) * dt))

    if not say_stream:
        return _expand_word_boundaries_for_subtitles(wb_words, s_offset_sec, keywords, rms_10ms)

    show_keys = [_char_to_phonetic_key(c) for c in show_chars]
    say_keys = [sc[0] for sc in say_stream]

    matcher = difflib.SequenceMatcher(None, show_keys, say_keys, autojunk=False)
    anchors: Dict[int, Tuple[float, float]] = {}
    for blk in matcher.get_matching_blocks():
        for off in range(blk.size):
            si = blk.a + off
            ti = blk.b + off
            anchors[si] = (say_stream[ti][1], say_stream[ti][2])

    n_show = len(show_chars)
    span_start = say_stream[0][1]
    span_end = max(span_start + 0.05, say_stream[-1][2])
    times: List[Tuple[float, float]] = [(0.0, 0.0)] * n_show

    anchor_indices = sorted(anchors.keys())
    if not anchor_indices:
        dt_all = (span_end - span_start) / float(n_show)
        for i in range(n_show):
            times[i] = (span_start + i * dt_all, span_start + (i + 1) * dt_all)
    else:
        for ai in anchor_indices:
            times[ai] = anchors[ai]
        first_a = anchor_indices[0]
        if first_a > 0:
            h_end = max(span_start + 0.02 * first_a, anchors[first_a][0])
            h_start = min(span_start, h_end - 0.02 * first_a)
            dt_h = (h_end - h_start) / float(first_a)
            for i in range(first_a):
                times[i] = (h_start + i * dt_h, h_start + (i + 1) * dt_h)
        for k_a in range(len(anchor_indices) - 1):
            a_prev = anchor_indices[k_a]
            a_next = anchor_indices[k_a + 1]
            gap_n = a_next - a_prev - 1
            if gap_n > 0:
                g_start = anchors[a_prev][1]
                g_end = max(g_start + 0.015 * gap_n, anchors[a_next][0])
                dt_g = (g_end - g_start) / float(gap_n)
                for step_i, idx_s in enumerate(range(a_prev + 1, a_next)):
                    times[idx_s] = (g_start + step_i * dt_g, g_start + (step_i + 1) * dt_g)
        last_a = anchor_indices[-1]
        if last_a < n_show - 1:
            tail_n = n_show - 1 - last_a
            t_start = anchors[last_a][1]
            t_end = max(t_start + 0.02 * tail_n, span_end)
            dt_t = (t_end - t_start) / float(tail_n)
            for step_i, idx_s in enumerate(range(last_a + 1, n_show)):
                times[idx_s] = (t_start + step_i * dt_t, t_start + (step_i + 1) * dt_t)

    projected: List[Dict[str, Any]] = []
    prev_end = s_offset_sec
    for idx_ch, (ch, (pt0, pt1)) in enumerate(zip(show_chars, times)):
        rem = max(1, len(show_chars) - idx_ch)
        pt0_safe = max(prev_end, min(e_sec - 0.015 * rem, pt0))
        pt1_safe = max(pt0_safe + 0.015, min(e_sec - 0.015 * (rem - 1), pt1))
        prev_end = pt1_safe
        e_val = 0.72
        if rms_10ms is not None and len(rms_10ms) >= 4:
            i0 = max(0, int(round(pt0_safe * 100)))
            i1 = min(len(rms_10ms), max(i0 + 1, int(round(pt1_safe * 100))))
            e_val = float(np.mean(rms_10ms[i0:i1]))
        projected.append({
            "word": ch,
            "start_sec": round(pt0_safe, 4),
            "end_sec": round(pt1_safe, 4),
            "energy": round(min(1.0, e_val * 5.0), 3),
            "is_keyword": False,
        })
    _mark_word_keywords(projected, keywords)
    return projected


def concat_wavs_with_gaps(seg_wavs: List[Path], gap_sec: float, out_wav: Path) -> List[Tuple[float, float]]:
    sr = 48000
    gap_frames = int(round(gap_sec * sr))
    silence_bytes = b"\x00\x00\x00\x00" * gap_frames
    all_pcm = bytearray()
    spans: List[Tuple[float, float]] = []
    cursor_frames = 0

    for idx, wp in enumerate(seg_wavs):
        with wave.open(str(wp), "rb") as wf:
            pcm = wf.readframes(wf.getnframes())
            n_frames = wf.getnframes()
        s_sec = round(cursor_frames / sr, 4)
        e_sec = round((cursor_frames + n_frames) / sr, 4)
        spans.append((s_sec, e_sec))
        all_pcm += pcm
        cursor_frames += n_frames
        if idx < len(seg_wavs) - 1 and gap_frames > 0:
            all_pcm += silence_bytes
            cursor_frames += gap_frames

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_wav), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(bytes(all_pcm))
    return spans


def _build_paper_edit_suggestions(segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """纸面精剪（Paper Edit）建议：从全片扫描强数字/强冲突/高能量金句，提示是否值得倒叙提前到开头。"""
    active = [s for s in segments if not s.get("is_filler") and str(s.get("text", "")).strip()]
    if len(active) < 4:
        return []
    punch_cues = ("真相", "其实", "千万别", "亏", "坑", "翻倍", "凭啥", "实话", "底线", "免费", "直接")
    scored: List[Tuple[float, int, Dict[str, Any]]] = []
    for idx, s in enumerate(active):
        txt = str(s.get("text", ""))
        sc = 0.0
        if re.search(r"\d+", txt):
            sc += 2.2
        if any(c in txt for c in punch_cues):
            sc += 2.0
        if "？" in txt or "?" in txt or "！" in txt or "!" in txt:
            sc += 1.2
        if 6 <= len(_clean_zh_text(txt)) <= 14:
            sc += 1.0
        sc += float(s.get("energy_score", 0.5)) * 1.5
        scored.append((sc, idx, s))
    first_sc = scored[0][0]
    best = max(scored[2:], key=lambda x: x[0])
    out: List[Dict[str, Any]] = []
    if best[0] >= first_sc + 1.8:
        out.append({
            "type": "flash_forward_opening_candidate",
            "segment_id": best[2]["id"],
            "original_position": best[1] + 1,
            "text": best[2]["text"],
            "reason": "中后段存在信息冲击力明显强于首句的金句，纸面精剪可考虑抽到第 0 秒做倒叙开场",
        })
    return out


def run_step2(
    pipeline_dir: Path,
    track: str = "store",
    script_json_path: Optional[Path] = None,
    force_tts: bool = False,
    whisper_model: Optional[str] = None,
    whitelist_path: Optional[Path] = None,
    sanity_replacements: Optional[Dict[str, str]] = None,
    dialect: str = "mandarin",
    store_anchor: Optional[str] = None,
    multi_speaker: bool = False,
) -> Dict[str, Any]:
    from compliance_guard import audit_script_compliance

    mf_path = pipeline_dir / "01_manifest.json"
    if mf_path.exists():
        manifest = read_json(mf_path)
    elif force_tts:
        manifest = {"items": []}
    else:
        raise FileNotFoundError(f"缺少 01_manifest.json: {mf_path}")
    arolls = [it for it in manifest["items"] if it["role"] == "a_roll" and it.get("normalized_wav")]
    vgrade_by_mp4 = {
        str(it.get("normalized_mp4")): str(it.get("video_grade", "usable"))
        for it in manifest.get("items", [])
        if it.get("normalized_mp4")
    }

    has_user_script = bool(script_json_path and script_json_path.exists())
    if has_user_script:
        raw_scr = read_json(script_json_path)  # type: ignore[arg-type]
        if isinstance(raw_scr, dict):
            script_items = raw_scr.get("sentences") or raw_scr.get("segments") or []
        else:
            script_items = raw_scr
    else:
        script_items = DEFAULT_STORE_SCRIPT if track == "store" else DEFAULT_CREATOR_SCRIPT

    if force_tts or not arolls:
        if not has_user_script:
            print("[step2] [WARN] 无口播原声且未传 --script-json，正在使用内置示例台词生成演示 TTS。")
        tts_dir = pipeline_dir / "02_tts_segments"
        tts_dir.mkdir(parents=True, exist_ok=True)
        seg_wavs: List[Path] = []
        pre_items = []
        for i, it in enumerate(script_items, start=1):
            show_txt = str(it.get("show") or it.get("text") or "")
            say_txt = str(it.get("say") or show_txt)
            has_distinct_say = bool(it.get("say") and say_txt.strip() != show_txt.strip())
            pre_items.append(dict(it, id=f"seg_{i:03d}", text=show_txt, show=show_txt, say=say_txt, has_distinct_say=has_distinct_say))

        pre_comp = audit_script_compliance(
            pre_items,
            source_type="tts",
            pipeline_dir=pipeline_dir,
            whitelist_path=whitelist_path,
            auto_action=True,
        )
        rewritten_by_idx = {
            f["sentence_id"]: f["suggested_text"]
            for f in pre_comp.get("findings", [])
            if f.get("action") == "auto_rewrite_or_block" and f.get("suggested_text")
        }
        effective_items = []
        for idx, it_base in enumerate(pre_items, start=1):
            it_copy = dict(it_base)
            if it_copy["id"] in rewritten_by_idx:
                it_copy.setdefault("original_text_before_compliance", it_copy["text"])
                it_copy["text"] = rewritten_by_idx[it_copy["id"]]
                it_copy["show"] = it_copy["text"]
                if not it_copy.get("has_distinct_say"):
                    it_copy["say"] = it_copy["text"]
                # 合规改写后同步刷新 keywords，严防违禁原词穿透到花字与封面
                it_copy["keywords"] = extract_auto_keywords(it_copy["text"])
            effective_items.append(it_copy)

        # 先做 TTS 前文本常识校对，确保音频与最终文字 100% 一致（独立保护用户自定义 say）
        sanity_warnings = apply_semantic_sanity_check(effective_items, replacements=sanity_replacements)
        for item in effective_items:
            if item.get("text") != item.get("show"):
                item["show"] = item["text"]
                if not item.get("has_distinct_say"):
                    item["say"] = item["text"]
            if item.get("has_distinct_say") and item.get("say"):
                say_dummy = [{"id": item["id"], "text": str(item["say"])}]
                apply_semantic_sanity_check(say_dummy, replacements=sanity_replacements)
                item["say"] = say_dummy[0]["text"]
            if not item.get("keywords") or item.get("original_text_before_compliance"):
                item["keywords"] = extract_auto_keywords(item["text"])

        tts_jobs: List[Tuple[int, Dict[str, Any], Path, str, str, str]] = []
        tts_meta_per_seg: List[Optional[Tuple[List[Dict[str, Any]], float, float]]] = [None] * len(effective_items)
        for idx, item in enumerate(effective_items, start=1):
            sp = tts_dir / f"seg_{idx:03d}.wav"
            speak_str = str(item.get("say") or item["text"])
            if speak_str != item["text"]:
                say_comp = audit_script_compliance(
                    [{"id": item["id"], "text": speak_str}],
                    source_type="tts",
                    pipeline_dir=None,
                    whitelist_path=whitelist_path,
                    auto_action=True,
                )
                say_findings = list(say_comp.get("findings") or [])
                if say_findings:
                    for sf in say_findings:
                        sf["field"] = "say"
                    pre_comp.setdefault("findings", []).extend(say_findings)
                    pre_comp["must_sentence_count"] = int(pre_comp.get("must_sentence_count", 0)) + int(say_comp.get("must_sentence_count", 0))
                    pre_comp["warn_hit_count"] = int(pre_comp.get("warn_hit_count", 0)) + int(say_comp.get("warn_hit_count", 0))
                    pre_comp["unacked_warn_count"] = int(pre_comp.get("unacked_warn_count", 0)) + int(say_comp.get("unacked_warn_count", 0))
                    pre_comp["auto_rewritten_count"] = int(pre_comp.get("auto_rewritten_count", 0)) + int(say_comp.get("auto_rewritten_count", 0))
                rw_say = next(
                    (f.get("suggested_text") for f in say_findings if f.get("action") == "auto_rewrite_or_block" and f.get("suggested_text")),
                    None,
                )
                if rw_say:
                    speak_str = str(rw_say)
                    item["say"] = speak_str
                elif not say_comp.get("passed", True):
                    pre_comp["passed"] = False
            v_name = str(item.get("voice") or "zh-CN-YunxiNeural")
            v_rate = str(item.get("rate") or "+8%")
            if item.get("voice_file"):
                if script_json_path is None:
                    raise ValueError(f"{item['id']} 指定了 voice_file 但未传入 script_json_path。")
                original = script_items[idx - 1]
                original_text = str(original.get("show") or original.get("text") or "")
                orig_shown_before = item.get("original_text_before_compliance")
                if speak_str != str(original.get("say") or original_text) or (item["text"] != original_text or orig_shown_before is not None):
                    raise ValueError(f"{item['id']} 的台词已调整，需提供匹配的新录音。")
                voice_source = (script_json_path.resolve().parent / item["voice_file"]).resolve()
                ffmpeg = find_bin("ffmpeg")
                if not ffmpeg:
                    raise RuntimeError("导入原始配音需要 FFmpeg")
                run_cmd([ffmpeg, "-y", "-v", "error", "-i", str(voice_source), "-vn",
                         "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(sp)])
                arr_v, _ = read_wav_as_48k_stereo(sp, target_sr=48000)
                arr_fixed, st_diag = rescue_stereo_channels(arr_v, imbalance_db=8.0)
                if st_diag != "ok":
                    write_wav_48k_stereo(sp, arr_fixed, sr=48000)
                duration, m_on, m_off = _measure_wav_speech_extent(sp)
                if duration <= 0.1 or m_off <= m_on:
                    raise ValueError(f"原始配音为空或过短：{voice_source}")
                item["voice_source"] = str(voice_source)
                tts_meta_per_seg[idx - 1] = ([], m_on, m_off)
            else:
                tts_jobs.append((idx - 1, item, sp, speak_str, v_name, v_rate))
            seg_wavs.append(sp)

        if tts_jobs:
            def _synth_one(job: Tuple[int, Dict[str, Any], Path, str, str, str]) -> Tuple[int, List[Dict[str, Any]], float, float]:
                j_idx, _it, sp_p, s_txt, vn, vr = job
                _, _, wbs, mo, mf = synthesize_tts_segment_detailed(s_txt, sp_p, voice=vn, rate=vr)
                return j_idx, wbs, mo, mf

            with ThreadPoolExecutor(max_workers=min(4, len(tts_jobs))) as pool:
                for j_idx, wbs, mo, mf in pool.map(_synth_one, tts_jobs):
                    tts_meta_per_seg[j_idx] = (wbs, mo, mf)

        master_tts_wav = pipeline_dir / "02_tts_voice.wav"
        spans = concat_wavs_with_gaps(seg_wavs, gap_sec=0.38, out_wav=master_tts_wav)
        total_dur = get_wav_duration_sec(master_tts_wav)
        y16, sr16 = load_wav_16k_mono(master_tts_wav)
        rms_10ms = compute_10ms_rms(y16, sr16)

        segments: List[Dict[str, Any]] = []
        for idx, (item, (s_sec, e_sec), (wb_words, m_on, m_off)) in enumerate(zip(effective_items, spans, tts_meta_per_seg), start=1):
            display_txt = str(item.get("show") or item["text"])
            speak_txt = str(item.get("say") or display_txt)
            kws = item.get("keywords", []) or extract_auto_keywords(display_txt)
            wb_joined = "".join(w["word"] for w in wb_words)
            if wb_words and speak_txt == display_txt and _clean_zh_text(wb_joined) == _clean_zh_text(display_txt):
                seg_words = _expand_word_boundaries_for_subtitles(wb_words, s_sec, kws, rms_10ms)
            elif wb_words:
                seg_words = _project_say_words_to_show(wb_words, display_txt, s_sec, e_sec, kws, rms_10ms, m_on=m_on, m_off=m_off)
            else:
                eff_s = min(e_sec - 0.1, s_sec + m_on)
                eff_e = max(eff_s + 0.1, min(e_sec, s_sec + m_off))
                seg_words = split_chars_energy_aligned(display_txt, eff_s, eff_e, kws, rms_10ms=rms_10ms)
            segments.append({
                "id": f"seg_{idx:03d}",
                "text": display_txt,
                "say_text": speak_txt,
                "start_sec": s_sec,
                "end_sec": e_sec,
                "source_media": None,
                "source_video_grade": "usable",
                "source_audio": str(master_tts_wav.resolve()),
                "voice_source": item.get("voice_source"),
                "voice_source_offset_sec": s_sec,
                "is_filler": bool(item.get("is_filler", False)),
                "emotion": item.get("emotion", "info"),
                "keywords": kws,
                "words": seg_words,
            })
        compute_prosody_for_segments(master_tts_wav, segments, audio_pair=(y16, sr16))
        source_type = "tts"
        primary_audio = str(master_tts_wav.resolve())
        filter_stats = {"offcamera_dropped": 0, "retake_dropped": 0, "stumbles_dropped": 0, "silence_retimed": 0}
        compliance_report = pre_comp
        write_compliance_report_files(pipeline_dir, compliance_report)
        speech_islands_map: Dict[str, List[Dict[str, Any]]] = {}
    else:
        segments = []
        source_types: List[str] = []
        total_dur = 0.0
        audio_cache: Dict[str, Tuple[np.ndarray, int]] = {}
        for ar in arolls:
            wav_path = Path(ar["normalized_wav"])
            wav_key = str(wav_path.resolve())
            dur_ar = get_wav_duration_sec(wav_path)
            total_dur += dur_ar
            if wav_key not in audio_cache:
                audio_cache[wav_key] = load_wav_16k_mono(wav_path)
            y16_ar, sr16_ar = audio_cache[wav_key]

            if has_user_script and len(arolls) == 1:
                ar_segs, stype = align_script_to_existing_wav(
                    wav_path, script_items, ar["normalized_mp4"], model_name=whisper_model,
                    audio_pair=(y16_ar, sr16_ar), dialect=dialect, store_anchor=store_anchor,
                )
            else:
                asr_segs = try_faster_whisper(
                    wav_path, model_name=whisper_model, y16_cached=y16_ar,
                    dialect=dialect, store_anchor=store_anchor,
                )
                if asr_segs is not None and len(asr_segs) > 0:
                    for seg in asr_segs:
                        seg["source_media"] = ar["normalized_mp4"]
                        seg["source_audio"] = wav_key
                    ar_segs = asr_segs
                    stype = "asr_whisper"
                elif has_user_script:
                    raise RuntimeError(
                        f"存在 {len(arolls)} 段实拍口播且 faster-whisper 转写{'为空' if asr_segs is not None else '失败'}，无法安全分配单份脚本至多段原声。"
                    )
                else:
                    raise RuntimeError(
                        f"检测到实拍口播原声 ({Path(ar['normalized_mp4']).name})，但 faster-whisper {'未识别到有效语音' if asr_segs is not None else '不可用'}且未传 --script-json。"
                        "已拒绝静默套用内置示范台词，请补充 --script-json 或运行 check_and_setup.py --install-ml。"
                    )

            for seg in ar_segs:
                seg["source_video_grade"] = vgrade_by_mp4.get(str(ar["normalized_mp4"]), "usable")
            segments.extend(ar_segs)
            source_types.append(stype)

        for gi, seg in enumerate(segments, start=1):
            seg["id"] = f"seg_{gi:03d}"

        # 正确顺序：先收紧句首/句尾静音 -> 再重算韵律 F0/RMS -> 分组剥离画外音 -> 再排查提词半截 -> 合规与同音校对
        retimed_cnt = refine_word_boundaries_with_energy(segments, audio_cache=audio_cache)
        for ar in arolls:
            wk = str(Path(ar["normalized_wav"]).resolve())
            ar_slice = [s for s in segments if s.get("source_audio") == wk]
            compute_prosody_for_segments(Path(ar["normalized_wav"]), ar_slice, audio_pair=audio_cache.get(wk))
        filter_stats = filter_offcamera_and_retakes(segments, audio_cache=audio_cache, multi_speaker=multi_speaker)
        stumble_cnt = detect_prompt_stumbles(segments)
        filter_stats["stumbles_dropped"] = stumble_cnt
        filter_stats["silence_retimed"] = retimed_cnt
        source_type = source_types[0] if len(set(source_types)) == 1 else "multi_aroll_mixed"
        primary_audio = str(Path(arolls[0]["normalized_wav"]).resolve())
        compliance_report = audit_script_compliance(
            segments,
            source_type="real_voice",
            pipeline_dir=pipeline_dir,
            whitelist_path=whitelist_path,
            auto_action=True,
        )
        if not compliance_report.get("passed", True):
            dropped = compliance_report.get("dropped_real_voice_ids", [])
            raise RuntimeError(f"实拍口播合规拦截阻断：违规词已淘汰 {len(dropped)} 句，导致有效原声不足。")

        sanity_warnings = apply_semantic_sanity_check(segments, replacements=sanity_replacements)
        for seg in segments:
            if not seg.get("is_filler") and sanity_replacements:
                seg["keywords"] = extract_auto_keywords(seg["text"])
                _mark_word_keywords(seg.get("words") or [], seg["keywords"])

        # 实拍口播接入 10ms 语音能量岛检测，输出物理发声边界供 Step 3 切点对齐与孤立残句排查
        speech_islands_map = {}
        short_orphan_cnt = 0
        for wk, (y16_a, sr16_a) in audio_cache.items():
            islands = detect_speech_islands(y16_a, sr=sr16_a)
            speech_islands_map[wk] = islands
            short_orphan_cnt += sum(1 for isl in islands if isl.get("is_short_orphan_candidate"))
        filter_stats["short_island_candidates"] = short_orphan_cnt

    transcript = {
        "step": "02_transcribe",
        "source_type": source_type,
        "uses_synthetic_voice": source_type == "tts" and any(not seg.get("voice_source") for seg in segments),
        "language": "zh",
        "primary_audio": primary_audio,
        "duration_sec": round(total_dur, 4),
        "filter_stats": filter_stats,
        "compliance_passed": compliance_report.get("passed", True),
        "compliance_report": str((pipeline_dir / "00_compliance_report.json").resolve()),
        "sanity_warnings": sanity_warnings,
        "speech_islands": speech_islands_map,
        "paper_edit_suggestions": _build_paper_edit_suggestions(segments),
        "segments": segments,
    }
    write_json(pipeline_dir / "02_transcript.json", transcript)
    active_cnt = sum(1 for s in segments if not s.get("is_filler"))
    print(
        f"[step2] 转写与声学对齐完成 ({source_type}, 有效 {active_cnt}/{len(segments)} 句, "
        f"画外声={filter_stats['offcamera_dropped']}, NG择优={filter_stats['retake_dropped']}, "
        f"提词半截={filter_stats['stumbles_dropped']}, 静音重计时={filter_stats['silence_retimed']}, "
        f"实拍合规弃用={len(compliance_report.get('dropped_real_voice_ids', []))}) -> 02_transcript.json"
    )
    return transcript


def detect_speech_islands(
    y16: np.ndarray,
    sr: int = 16000,
    thr_db: float = -40.0,
    min_sil_sec: float = 0.18,
    hop_sec: float = 0.010,
    min_island_sec: float = 0.06,
) -> List[Dict[str, Any]]:
    """
    10ms 语音能量岛检测：定位每段真实发声物理边界，用于精剪口播、防止误切轻声尾字，
    并精准标出 0.20–0.65s 孤立短岛（2–4 字残留起句候选）。
    """
    if len(y16) == 0:
        return []
    hop_n = max(1, int(round(hop_sec * sr)))
    n_frames = len(y16) // hop_n
    if n_frames <= 0:
        return []
    trimmed = y16[: n_frames * hop_n].reshape(n_frames, hop_n)
    rms = np.sqrt(np.mean(trimmed ** 2, axis=1) + 1e-12)
    db = 20.0 * np.log10(rms)
    active = db > float(thr_db)

    islands: List[Dict[str, float]] = []
    start_t: Optional[float] = None
    last_on_t: Optional[float] = None
    for idx, is_on in enumerate(active):
        t = idx * hop_sec
        if is_on:
            if start_t is None:
                start_t = t
            last_on_t = t
        elif start_t is not None and last_on_t is not None and (t - last_on_t) > min_sil_sec:
            dur = (last_on_t + hop_sec) - start_t
            if dur >= min_island_sec:
                islands.append({
                    "start_sec": round(start_t, 4),
                    "end_sec": round(last_on_t + hop_sec, 4),
                    "duration_sec": round(dur, 4),
                    "is_short_orphan_candidate": 0.20 <= dur <= 0.65,
                })
            start_t = None
            last_on_t = None
    if start_t is not None and last_on_t is not None:
        dur = (last_on_t + hop_sec) - start_t
        if dur >= min_island_sec:
            islands.append({
                "start_sec": round(start_t, 4),
                "end_sec": round(last_on_t + hop_sec, 4),
                "duration_sec": round(dur, 4),
                "is_short_orphan_candidate": 0.20 <= dur <= 0.65,
            })
    return islands


def probe_overlap_windows(
    wav_path: Path,
    win_sec: float = 5.0,
    hop_sec: float = 2.5,
    whisper_model: Optional[str] = None,
    dialect: str = "mandarin",
) -> List[Dict[str, Any]]:
    """
    重叠短窗口复核转写（真正不带文案 prompt、禁用前文条件依赖、纯离线缓存优先）：
    专门暴露长句整段转写中容易被语言模型“顺滑合并吞掉”的重复起句与半截重说。
    """
    y16, sr = load_wav_16k_mono(wav_path)
    total_sec = len(y16) / float(sr) if sr > 0 else 0.0
    if total_sec < 0.4:
        return []
    eff_model = whisper_model or find_cached_whisper_model()
    if not eff_model:
        return []
    try:
        model = get_cached_whisper_model(eff_model, local_files_only=True)
    except Exception:
        return []
    if model is None:
        return []

    lang_arg = "yue" if str(dialect or "").lower() in ("cantonese", "yue") else "zh"
    rows: List[Dict[str, Any]] = []
    t = 0.0
    while t < total_sec:
        s0 = int(t * sr)
        s1 = int(min(t + win_sec, total_sec) * sr)
        if s1 - s0 < int(sr * 0.4):
            break
        seg_audio = y16[s0:s1].astype(np.float32)
        segs, _ = model.transcribe(
            seg_audio,
            language=lang_arg,
            condition_on_previous_text=False,
            temperature=0.0,
            word_timestamps=False,
        )
        txt = "".join(str(sg.text or "").strip() for sg in segs).strip()
        rows.append({
            "win_start_sec": round(t, 2),
            "win_end_sec": round(min(t + win_sec, total_sec), 2),
            "text": txt,
        })
        t += max(0.5, float(hop_sec))
    return rows


def main() -> None:
    maybe_reexec_in_venv(("faster_whisper",))
    parser = argparse.ArgumentParser(description="Step 2: 语音转写、声学强制对齐、向量化指纹去画外音与 NG 择优")
    parser.add_argument("--pipeline-dir", required=True)
    parser.add_argument("--track", choices=["store", "creator"], default="store")
    parser.add_argument("--script-json", help="可选：自定义文案句列表 JSON")
    parser.add_argument("--force-tts", action="store_true", help="强制用文案生成 TTS 配音")
    parser.add_argument("--whisper-model", help="指定 faster-whisper 模型名")
    parser.add_argument("--whitelist", help="可选：compliance_whitelist.json 路径")
    parser.add_argument("--sanity-replacements", help="可选：同音纠偏等长替换字典 JSON 文件或 JSON 字符串")
    parser.add_argument("--dialect", default="mandarin", help="语言/方言提示 (mandarin|cantonese|dialect)")
    parser.add_argument("--store-anchor", help="门店/品牌热词提示")
    parser.add_argument("--multi-speaker", action="store_true", help="多人对话保护模式（不按音量差删除副说话人）")
    args = parser.parse_args()

    reps: Optional[Dict[str, str]] = None
    if args.sanity_replacements:
        p_rep = Path(args.sanity_replacements)
        reps = read_json(p_rep) if p_rep.exists() else json.loads(args.sanity_replacements)

    run_step2(
        Path(args.pipeline_dir),
        track=args.track,
        script_json_path=Path(args.script_json) if args.script_json else None,
        force_tts=args.force_tts,
        whisper_model=args.whisper_model,
        whitelist_path=Path(args.whitelist) if args.whitelist else None,
        sanity_replacements=reps,
        dialect=args.dialect,
        store_anchor=args.store_anchor,
        multi_speaker=args.multi_speaker,
    )


if __name__ == "__main__":
    main()

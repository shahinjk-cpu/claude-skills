#!/usr/bin/env python3
"""
[程序化无版权动效拟音合成与峰值对齐混音器]
离线合成 15 种 48kHz 立体声动效拟音（峰值 -3 dBFS），
专用于口播动态讲解画面（B-roll）、平滑圆环画中画缩放与知识讲解动画关键事件卡点：
- whoosh_in / whoosh_out / swish / pop / pop_low / tick / click / drag
- shrink / impact / riser / chime / peel / stretch / glide
支持 4ms 滑动窗口能量峰值自动对准目标时刻、end 对齐（riser 收尾落爆点）及 0.15s 密集触发自动衰减。
"""

from __future__ import annotations

import argparse
import json
import sys
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from common import maybe_reexec_in_venv

if __name__ == "__main__":
    maybe_reexec_in_venv()

import numpy as np

SR = 48000


def _t_axis(dur: float) -> np.ndarray:
    return np.arange(max(1, int(round(dur * SR))), dtype=np.float64) / SR


def _onepole_lp(x: np.ndarray, fc: Any) -> np.ndarray:
    """高速一阶低通滤波器：恒定/扫频均使用 scipy.signal.lfilter 分块递推，较纯 Python 循环提速 50–100x。"""
    x64 = np.asarray(x, dtype=np.float64)
    n = len(x64)
    if n == 0:
        return x64.copy()
    fc_arr = np.asarray(fc, dtype=np.float64)
    try:
        from scipy.signal import lfilter

        if fc_arr.ndim == 0 or (fc_arr.size == 1) or float(np.ptp(fc_arr)) < 1e-6:
            f_val = float(np.clip(float(fc_arr.flat[0]), 20.0, SR * 0.45))
            a = 1.0 - float(np.exp(-2.0 * np.pi * f_val / SR))
            y, _ = lfilter([a], [1.0, -(1.0 - a)], x64, zi=[0.0])
            return y
        fc_vec = np.broadcast_to(fc_arr, (n,))
        alpha = 1.0 - np.exp(-2.0 * np.pi * np.clip(fc_vec, 20.0, SR * 0.45) / SR)
        # 按 64 点微块(1.3ms)做平滑状态连续 lfilter，听感完全平滑且比逐采样快 ~80 倍
        y = np.empty(n, dtype=np.float64)
        blk = 64
        zi = np.array([0.0], dtype=np.float64)
        for s in range(0, n, blk):
            e = min(n, s + blk)
            a_mid = float(alpha[(s + e - 1) // 2])
            yb, zi = lfilter([a_mid], [1.0, -(1.0 - a_mid)], x64[s:e], zi=zi)
            y[s:e] = yb
        return y
    except Exception:
        fc_vec = np.broadcast_to(fc_arr, (n,))
        alpha = 1.0 - np.exp(-2.0 * np.pi * np.clip(fc_vec, 20.0, SR * 0.45) / SR)
        y = np.empty_like(x64)
        acc = 0.0
        for i in range(n):
            acc += alpha[i] * (x64[i] - acc)
            y[i] = acc
        return y


def _band_sweep(dur: float, f0: float, f1: float, rng: np.random.Generator, q: float = 2.0) -> np.ndarray:
    n = max(1, int(round(dur * SR)))
    noise = rng.standard_normal(n)
    u = np.linspace(0.0, 1.0, n)
    freq = f0 * (f1 / max(1.0, f0)) ** u
    return _onepole_lp(noise, freq * (1.0 + 1.0 / q)) - _onepole_lp(noise, freq / (1.0 + 1.0 / q))


def _stereo_pan(mono: np.ndarray, pan_start: float = -0.5, pan_end: float = 0.5) -> np.ndarray:
    p = np.linspace(pan_start, pan_end, len(mono))
    left = mono * np.cos((p + 1.0) * np.pi * 0.25)
    right = mono * np.sin((p + 1.0) * np.pi * 0.25)
    return np.stack([left, right], axis=1)


def _norm_stereo(x: np.ndarray, peak_target: float = 0.707) -> np.ndarray:
    arr = np.asarray(x, dtype=np.float64)
    if arr.ndim == 1:
        arr = np.stack([arr, arr], axis=1)
    peak = float(np.max(np.abs(arr))) + 1e-9
    return (arr / peak * peak_target).astype(np.float32)


def synthesize_sfx_waveform(kind: str, seed: int = 19) -> np.ndarray:
    """按名称合成 48kHz 立体声 float32 音效波形（峰值 -3 dBFS）。"""
    rng = np.random.default_rng(seed)
    k = str(kind or "pop").strip().lower()

    if k in ("whoosh_in", "whoosh"):
        d = 0.56
        u = np.linspace(0.0, 1.0, int(d * SR))
        env = np.where(u < 0.55, (u / 0.55) ** 2.1, ((1.0 - u) / 0.45) ** 1.6)
        return _norm_stereo(_stereo_pan(_band_sweep(d, 260, 2900, rng) * env, -0.65, 0.65))

    if k == "whoosh_out":
        d = 0.52
        u = np.linspace(0.0, 1.0, int(d * SR))
        env = np.where(u < 0.40, (u / 0.40) ** 1.8, ((1.0 - u) / 0.60) ** 1.9)
        return _norm_stereo(_stereo_pan(_band_sweep(d, 2800, 260, rng) * env, 0.6, -0.6))

    if k == "swish":
        d = 0.28
        u = np.linspace(0.0, 1.0, int(d * SR))
        env = np.sin(u * np.pi) ** 1.6
        return _norm_stereo(_stereo_pan(_band_sweep(d, 600, 4200, rng, q=2.4) * env, -0.45, 0.45))

    if k in ("pop", "pop_low"):
        base_f = 520.0 if k == "pop_low" else 860.0
        t = _t_axis(0.12)
        ft = base_f * (1.0 + 1.15 * np.exp(-t * 58.0))
        ph = 2.0 * np.pi * np.cumsum(ft) / SR
        sig = np.sin(ph) * np.exp(-t * 36.0) + 0.24 * np.sin(2.0 * ph) * np.exp(-t * 58.0)
        return _norm_stereo(sig)

    if k == "tick":
        t = _t_axis(0.048)
        n = rng.standard_normal(len(t)) * np.exp(-t * 380.0)
        sig = (n - _onepole_lp(n, 2400.0)) + 0.55 * np.sin(2.0 * np.pi * 3100.0 * t) * np.exp(-t * 170.0)
        return _norm_stereo(sig)

    if k == "click":
        a = synthesize_sfx_waveform("tick", seed=seed)[:, 0]
        off = int(0.032 * SR)
        b = np.pad(a * 0.58, (off, 0))
        a_pad = np.pad(a, (0, max(0, len(b) - len(a))))
        return _norm_stereo(a_pad[: len(b)] + b)

    if k == "drag":
        d = 0.90
        n = int(d * SR)
        x = _band_sweep(d, 950, 560, rng, q=1.3)
        grain = (rng.random(n) < 0.004).astype(np.float64) * rng.standard_normal(n)
        grain = grain - _onepole_lp(grain, 1700.0)
        env = np.sin(np.linspace(0.0, np.pi, n)) ** 0.7
        return _norm_stereo(_stereo_pan((x * 0.78 + grain * 0.45) * env, -0.25, 0.25))

    if k == "shrink":
        d = 0.50
        t = _t_axis(d)
        f = 1050.0 * (230.0 / 1050.0) ** (t / d)
        ph = 2.0 * np.pi * np.cumsum(f) / SR
        sig = np.sin(ph) * np.exp(-t * 4.2) * (1.0 - np.exp(-t * 190.0))
        sig += 0.28 * _band_sweep(d, 2800, 380, rng)[: len(t)] * np.exp(-t * 5.0)
        return _norm_stereo(sig)

    if k == "impact":
        d = 1.25
        t = _t_axis(d)
        f = 118.0 * (38.0 / 118.0) ** np.clip(t / 0.42, 0.0, 1.0)
        ph = 2.0 * np.pi * np.cumsum(f) / SR
        boom = np.sin(ph) * np.exp(-t * 3.4)
        hit = _onepole_lp(rng.standard_normal(len(t)) * np.exp(-t * 42.0), 3800.0)
        tail = _band_sweep(d, 1600, 280, rng)[: len(t)] * np.exp(-t * 2.8) * 0.34
        return _norm_stereo(np.tanh((boom + hit * 0.52 + tail) * 1.5))

    if k == "riser":
        d = 1.10
        t = _t_axis(d)
        noise = _band_sweep(d, 380, 5800, rng)[: len(t)]
        f = 190.0 * (780.0 / 190.0) ** (t / d)
        tone = np.sin(2.0 * np.pi * np.cumsum(f) / SR) * 0.24
        env = (t / d) ** 2.4
        tail_n = min(len(env), int(0.02 * SR))
        env[-tail_n:] *= np.linspace(1.0, 0.0, tail_n)
        return _norm_stereo(_stereo_pan((noise + tone) * env, -0.35, 0.35))

    if k == "chime":
        d = 1.35
        t = _t_axis(d)
        sig = np.zeros_like(t)
        for idx_h, (mult, amp, dec) in enumerate([(1.0, 1.0, 3.2), (2.01, 0.42, 4.6), (3.02, 0.2, 6.2)]):
            sig += amp * np.sin(2.0 * np.pi * 880.0 * mult * t + idx_h) * np.exp(-t * dec)
        sig *= 1.0 - np.exp(-t * 360.0)
        return _norm_stereo(np.stack([sig, np.roll(sig, 110) * 0.9], axis=1))

    if k == "peel":
        d = 0.85
        n = int(d * SR)
        sig = np.zeros(n, dtype=np.float64)
        pos = 0
        while pos < n:
            ln = int(rng.uniform(0.01, 0.042) * SR)
            burst = rng.standard_normal(ln) * np.hanning(ln) * rng.uniform(0.35, 1.0)
            end = min(n, pos + ln)
            sig[pos:end] += burst[: end - pos]
            pos += int(rng.uniform(0.005, 0.026) * SR)
        sig = sig - _onepole_lp(sig, 600.0)
        return _norm_stereo(sig)

    if k == "stretch":
        d = 0.65
        t = _t_axis(d)
        f = 240.0 * (640.0 / 240.0) ** (t / d)
        ph = 2.0 * np.pi * np.cumsum(f) / SR
        env = np.sin(np.linspace(0.0, np.pi, len(t))) ** 0.85
        sig = (np.sin(ph) * 0.6 + 0.35 * _band_sweep(d, 500, 1900, rng)[: len(t)]) * env
        return _norm_stereo(sig)

    # glide 默认
    d = 0.44
    t = _t_axis(d)
    f = 420.0 + 220.0 * np.sin(np.pi * t / d)
    ph = 2.0 * np.pi * np.cumsum(f) / SR
    env = np.sin(np.linspace(0.0, np.pi, len(t))) ** 1.3
    return _norm_stereo(_stereo_pan(np.sin(ph) * env, -0.3, 0.3))


ALL_SFX_KINDS = (
    "whoosh_in", "whoosh_out", "swish", "pop", "pop_low", "tick", "click",
    "drag", "shrink", "impact", "riser", "chime", "peel", "stretch", "glide",
)


def write_wav_stereo(path: Path, stereo: np.ndarray, sr: int = SR) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    clipped = np.clip(stereo, -0.98, 0.98)
    pcm = (clipped * 32767.0).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


def _peak_offset_samples(stereo: np.ndarray) -> int:
    """用 4ms 滑动能量窗找到音效听感峰值所在采样点，用于精准对齐视觉爆点。"""
    mono_sq = np.mean(stereo.astype(np.float64) ** 2, axis=1)
    win = max(1, int(0.004 * SR))
    if len(mono_sq) <= win:
        return int(np.argmax(mono_sq))
    kernel = np.ones(win, dtype=np.float64) / win
    env = np.convolve(mono_sq, kernel, mode="same")
    return int(np.argmax(env))


def mix_sfx_cues(
    cues: List[Dict[str, Any]],
    total_duration_sec: float,
    out_wav: Optional[Path] = None,
) -> np.ndarray:
    """将动效事件表 [{t, sfx, gain, align}] 能量峰值对齐混成 48kHz 立体声轨（含 0.15s 密集衰减）。"""
    total_samples = max(SR, int(round(max(0.5, total_duration_sec) * SR)))
    buf = np.zeros((total_samples, 2), dtype=np.float64)
    cache: Dict[Tuple[str, int], Tuple[np.ndarray, int]] = {}
    sorted_cues = sorted(cues, key=lambda c: float(c.get("t", 0.0)))

    recent_times: List[float] = []
    for idx, cue in enumerate(sorted_cues):
        t_sec = float(cue.get("t", 0.0))
        kind = str(cue.get("sfx") or cue.get("kind") or "pop")
        gain = float(cue.get("gain", 0.25))
        align = str(cue.get("align") or ("end" if kind == "riser" else "peak")).lower()
        variant = idx % 3

        key = (kind, variant)
        if key not in cache:
            wav = synthesize_sfx_waveform(kind, seed=19 + variant * 31)
            cache[key] = (wav, _peak_offset_samples(wav))
        wav, pk = cache[key]

        # 0.15s 内扎堆触发自动衰减 0.7^k 防止轰头
        recent_times = [rt for rt in recent_times if t_sec - rt <= 0.15]
        crowd_scale = 0.7 ** len(recent_times)
        recent_times.append(t_sec)

        target_s = int(round(t_sec * SR))
        if align == "end":
            start_s = target_s - len(wav)
        elif align == "start":
            start_s = target_s
        else:
            start_s = target_s - pk

        src_s = max(0, -start_s)
        dst_s = max(0, start_s)
        copy_n = min(len(wav) - src_s, total_samples - dst_s)
        if copy_n > 0:
            buf[dst_s : dst_s + copy_n] += wav[src_s : src_s + copy_n] * (gain * crowd_scale)

    # 软限幅防削波
    out = np.tanh(buf * 1.1) / 1.1
    out_f32 = out.astype(np.float32)
    if out_wav is not None:
        write_wav_stereo(out_wav, out_f32)
    return out_f32


def generate_sfx_pack(out_dir: Path) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    result: Dict[str, str] = {}
    for kind in ALL_SFX_KINDS:
        p = out_dir / f"{kind}.wav"
        write_wav_stereo(p, synthesize_sfx_waveform(kind))
        result[kind] = str(p.resolve())
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="程序化合成 15 种无版权动效拟音与峰值对齐混音")
    ap.add_argument("--out-dir", help="导出全套 15 种 WAV 音效到目录")
    ap.add_argument("--cues-json", help="按事件表 JSON 混音输出 WAV")
    ap.add_argument("--duration", type=float, default=10.0)
    ap.add_argument("--out-wav", help="混音输出路径")
    args = ap.parse_args()

    if args.out_dir:
        res = generate_sfx_pack(Path(args.out_dir))
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return
    if args.cues_json and args.out_wav:
        cues = json.loads(Path(args.cues_json).read_text(encoding="utf-8"))
        if isinstance(cues, dict):
            cues = cues.get("cues") or []
        mix_sfx_cues(cues, args.duration, Path(args.out_wav))
        print(f"[synth_motion_sfx] 已输出混音轨 -> {args.out_wav}")
        return
    ap.print_help()


if __name__ == "__main__":
    main()

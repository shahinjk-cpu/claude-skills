#!/usr/bin/env python3
"""
[Step 8: 广播级人声母带链 + dB域双频段闪避 + 三端同源分轨 + 一次校准 EBU R128 混音]
1. 从 01_manifest 未剪静音原声测真实静音谷值（TTS 跳过降噪），杜绝紧凑干声误触发 afftdn 水声。
2. dB 对数域平滑 + 相对人声门限的 4 阶 Butterworth (250–4000Hz) 双频段闪避；缺 scipy 时如实记 False。
3. 一次校准增益始终基于未限幅原混源 pre_mix 重算，彻底杜绝多代串联限幅与 TP 空转。
4. 同步产出 08_voice_master.wav、08_bgm_ducked.wav (供剪映/HyperFrames 同源听感) 及轻量 08_sfx_audit_window.json (供 tidy 后 #20 二次质检)。
输出：08_mixed_master.wav, 08_stem_nosfx.wav, 08_voice_master.wav, 08_bgm_ducked.wav, 08_mix_metrics.json, 08_sfx_audit_window.json
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from common import (
    TARGET_LUFS,
    compute_sfx_band_windows,
    find_bin,
    load_style_applied,
    maybe_reexec_in_venv,
    measure_lufs_ebur128,
    read_json,
    run_cmd,
    write_json,
)

if __name__ == "__main__":
    maybe_reexec_in_venv()

import numpy as np
from step3_lock_audio import SR, load_stereo_wav_np, save_stereo_wav_np


def _estimate_raw_noise_floor_db(pipeline_dir: Path, fallback_voice: np.ndarray) -> float:
    """
    优先从 01_manifest 原始长音轨测未裁切环境谷值底噪（p8），防止在已去静音的 03_locked_voice 上测到轻声词尾。
    """
    man_p = pipeline_dir / "01_manifest.json"
    sample_arr = fallback_voice
    if man_p.exists():
        try:
            man = read_json(man_p)
            ar_wav = next((it.get("normalized_wav") for it in man.get("items", []) if it.get("role") == "a_roll" and it.get("normalized_wav")), None)
            if ar_wav and Path(ar_wav).is_file():
                sample_arr, _ = load_stereo_wav_np(Path(ar_wav))
        except Exception:
            pass

    hop = int(0.02 * SR)
    usable_len = (len(sample_arr) // hop) * hop
    if usable_len < hop:
        return -70.0
    n_hops = usable_len // hop
    mono = sample_arr[:usable_len].mean(axis=1).reshape(n_hops, hop)
    rms = np.sqrt(np.mean(mono ** 2, axis=1) + 1e-12)
    nonzero = rms[rms > 2e-6]
    if len(nonzero) == 0:
        return -70.0
    p8 = float(np.percentile(nonzero, 8))
    return 20.0 * math.log10(max(1e-6, p8))


def split_bgm_dual_band(bgm_arr: np.ndarray, sr: int = SR) -> tuple[np.ndarray, np.ndarray, bool]:
    """零相位拆分 BGM 为中频冲突带 (250Hz-4kHz) 与外围低/高频带，并如实返回是否生效。"""
    if len(bgm_arr) <= 128 or importlib.util.find_spec("scipy") is None:
        return bgm_arr.copy(), np.zeros_like(bgm_arr), False
    try:
        from scipy.signal import butter, sosfiltfilt
        sos = butter(4, [250.0, 4000.0], btype="bandpass", fs=sr, output="sos")
        bgm_mid = sosfiltfilt(sos, bgm_arr, axis=0).astype(np.float32)
        bgm_outer = (bgm_arr - bgm_mid).astype(np.float32)
        return bgm_mid, bgm_outer, True
    except Exception:
        return bgm_arr.copy(), np.zeros_like(bgm_arr), False


def compute_mono_phase_correlation(audio: np.ndarray) -> float:
    if len(audio) < 10:
        return 1.0
    l_ch = audio[:, 0].astype(np.float64)
    r_ch = audio[:, 1].astype(np.float64)
    denom = float(np.linalg.norm(l_ch) * np.linalg.norm(r_ch))
    if denom < 1e-10:
        return 1.0
    return round(float(np.dot(l_ch, r_ch) / denom), 4)


def run_step8(
    pipeline_dir: Path,
    target_lufs: float = TARGET_LUFS,
    bgm_base_gain_db: Optional[float] = None,
    duck_depth_db: Optional[float] = None,
    licenses_path: Optional[Path] = None,
    out_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    ffmpeg = find_bin("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("需要 ffmpeg 执行广播级人声处理与混音。")

    style_id = load_style_applied(pipeline_dir)
    vibe_prof = None
    if style_id:
        try:
            from vibe_sound import get_style_sound_profile
            vibe_prof = get_style_sound_profile(str(style_id))
        except Exception:
            vibe_prof = None
    if bgm_base_gain_db is None:
        bgm_base_gain_db = float(vibe_prof.get("bgm_base_db", -15.0)) if vibe_prof else -15.0
    if duck_depth_db is None:
        duck_depth_db = float(vibe_prof.get("duck_depth_db", -11.0)) if vibe_prof else -11.0

    tr_p = pipeline_dir / "02_transcript.json"
    is_tts = (read_json(tr_p).get("source_type") == "tts") if tr_p.exists() else False
    audio_events = read_json(pipeline_dir / "03_audio_events.json")
    voice_in = Path(audio_events["locked_voice_wav"])
    bgm_in = Path(audio_events["locked_bgm_wav"])
    sfx_in = pipeline_dir / "06_sfx_track.wav"

    raw_v_arr, _ = load_stereo_wav_np(voice_in)
    noise_floor_db = _estimate_raw_noise_floor_db(pipeline_dir, raw_v_arr)
    # 按输入人声活性电平动态确定压缩阈值，避免小声片段压缩不触发或大声过压
    act_samples = raw_v_arr[np.abs(raw_v_arr) > 0.005]
    if len(act_samples) > 100:
        act_rms_db = 20.0 * math.log10(max(1e-5, float(np.sqrt(np.mean(act_samples.astype(np.float64) ** 2)))))
        comp_thresh_db = round(max(-28.0, min(-12.0, act_rms_db - 2.0)), 1)
    else:
        comp_thresh_db = -18.0

    # 仅真实采得有效低静音噪底 (-55dB <= nf <= -28dB) 才启轻量降噪；高于 -28dB 说明无静音采样、绝不误杀持续信号
    use_denoise = (not is_tts) and (-55.0 <= noise_floor_db <= -28.0)
    afftdn_nf = max(-55.0, min(-38.0, noise_floor_db - 4.0))
    denoise_stage = f",afftdn=nf={afftdn_nf:.1f}:tn=0" if use_denoise else ""
    vocal_chain = (
        f"highpass=f=80{denoise_stage},"
        "equalizer=f=240:t=q:w=1.2:g=-2.5,"
        "equalizer=f=3400:t=q:w=1.4:g=2.2,"
        "deesser=i=0.35:m=0.5:f=0.5:s=o,"
        f"acompressor=threshold={comp_thresh_db:.1f}dB:ratio=2.0:attack=8:release=140:makeup=1.5"
    )

    voice_clean_wav = pipeline_dir / "08_voice_denoised.wav"
    run_cmd([
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(voice_in),
        "-af", vocal_chain,
        "-ar", str(SR), "-ac", "2", "-acodec", "pcm_s16le",
        str(voice_clean_wav),
    ])

    voice_arr, _ = load_stereo_wav_np(voice_clean_wav)
    bgm_arr, _ = load_stereo_wav_np(bgm_in)
    n_samples = len(voice_arr)

    if len(bgm_arr) < n_samples:
        bgm_arr = np.concatenate([bgm_arr, np.zeros((n_samples - len(bgm_arr), 2), dtype=np.float32)], axis=0)
    bgm_arr = bgm_arr[:n_samples]

    if sfx_in.exists():
        sfx_arr, _ = load_stereo_wav_np(sfx_in)
        if len(sfx_arr) < n_samples:
            sfx_arr = np.concatenate([sfx_arr, np.zeros((n_samples - len(sfx_arr), 2), dtype=np.float32)], axis=0)
        sfx_arr = sfx_arr[:n_samples]
    else:
        sfx_arr = np.zeros_like(voice_arr)

    # 2. 自适应相对人声门限 + 前瞻包络 + dB 对数域平滑闪避
    mono_v = np.abs(voice_arr).mean(axis=1)
    win = int(0.025 * SR)
    env = np.convolve(mono_v, np.ones(win, dtype=np.float32) / win, mode="same")
    nz_env = env[env > 0.002]
    speech_ref = float(np.percentile(nz_env, 75)) if len(nz_env) > 20 else 0.05
    gate_low = max(0.002, speech_ref * 0.14)
    gate_span = max(0.006, speech_ref * 0.45)

    lookahead = int(0.035 * SR)
    shifted_env = np.concatenate([env[lookahead:], env[-lookahead:]]) if len(env) > lookahead else env
    raw_active = np.clip((shifted_env - gate_low) / gate_span, 0.0, 1.0).astype(np.float32)

    hop = max(1, int(0.010 * SR))
    n_hops = (len(raw_active) + hop - 1) // hop
    pad_len = n_hops * hop - len(raw_active)
    padded_act = np.concatenate([raw_active, np.zeros(pad_len, dtype=np.float32)]) if pad_len else raw_active
    hop_peaks = padded_act.reshape(n_hops, hop).max(axis=1)

    dt_hop = hop / float(SR)
    alpha_atk = 1.0 - float(np.exp(-dt_hop / 0.035))
    alpha_rel = 1.0 - float(np.exp(-dt_hop / 0.280))
    duck_ctrl = np.zeros(n_hops, dtype=np.float32)
    cur_d = 0.0
    for hi in range(n_hops):
        tgt = float(hop_peaks[hi])
        alpha = alpha_atk if tgt > cur_d else alpha_rel
        cur_d = cur_d + alpha * (tgt - cur_d)
        duck_ctrl[hi] = cur_d

    t_hops = (np.arange(n_hops, dtype=np.float32) + 0.5) * hop
    duck_factor = np.interp(np.arange(n_samples, dtype=np.float32), t_hops, duck_ctrl).astype(np.float32)

    bgm_mid, bgm_outer, dual_band_ok = split_bgm_dual_band(bgm_arr, SR)
    mid_gain_db = bgm_base_gain_db + duck_depth_db * duck_factor
    outer_gain_db = bgm_base_gain_db + (duck_depth_db * 0.32) * duck_factor
    mid_lin = np.power(10.0, mid_gain_db / 20.0).astype(np.float32)
    outer_lin = np.power(10.0, outer_gain_db / 20.0).astype(np.float32)
    ducked_bgm = bgm_mid * mid_lin[:, None] + bgm_outer * outer_lin[:, None]

    act_mask = duck_factor > 0.35
    if np.any(act_mask):
        v_rms = float(np.sqrt(np.mean((voice_arr[act_mask] * 0.95) ** 2) + 1e-12))
        b_rms = float(np.sqrt(np.mean(ducked_bgm[act_mask] ** 2) + 1e-12))
        voice_bgm_snr_db = round(20.0 * math.log10(max(1e-6, v_rms) / max(1e-6, b_rms)), 2)
    else:
        voice_bgm_snr_db = 20.0

    pre_mix_nosfx = voice_arr * 0.95 + ducked_bgm

    # B-roll 现场动作同期声轻混（彻底修复 step1 -an 导致旧版抽 media_path 100% 失败的死链：优先从 normalized_wav / ambient_audio_path 抽取）
    broll_ambient_arr = np.zeros_like(voice_arr)
    broll_ambient_mixed_count = 0
    edl_p = pipeline_dir / "04_edl.json"
    man_p2 = pipeline_dir / "01_manifest.json"
    wav_by_mp4: Dict[str, str] = {}
    dur_by_mp4: Dict[str, float] = {}
    if man_p2.is_file():
        for mit in read_json(man_p2).get("items") or []:
            mp_k = str(mit.get("normalized_mp4") or "")
            w_cand = mit.get("normalized_wav") or (mit.get("source_path") if mit.get("has_audio") else None)
            if mp_k and w_cand:
                wav_by_mp4[mp_k] = str(w_cand)
            if mp_k and mit.get("duration_sec"):
                dur_by_mp4[mp_k] = float(mit["duration_sec"])
    if edl_p.is_file():
        try:
            import tempfile
            edl_clips = read_json(edl_p).get("clips") or []
            amb_clips = [c for c in edl_clips if c.get("keep_broll_ambient")]
            if amb_clips:
                with tempfile.TemporaryDirectory(prefix="svs_amb_") as amb_td:
                    for ai, ac in enumerate(amb_clips):
                        mp_path_str = str(ac.get("media_path") or "")
                        aud_src = str(ac.get("ambient_audio_path") or wav_by_mp4.get(mp_path_str) or "")
                        if not aud_src or not Path(aud_src).is_file():
                            continue
                        t0 = max(0.0, float(ac.get("timeline_in_sec", 0.0)))
                        t1 = min(n_samples / float(SR), float(ac.get("timeline_out_sec", t0)))
                        dur_a = t1 - t0
                        src_in = max(0.0, float(ac.get("source_in_sec", 0.0)))
                        src_cap = float(ac.get("source_out_sec") or dur_by_mp4.get(mp_path_str) or 0.0)
                        if src_cap > src_in:
                            dur_a = min(dur_a, src_cap - src_in)
                        if dur_a < 0.25:
                            continue
                        amb_wav = Path(amb_td) / f"amb_{ai:02d}.wav"
                        res_a = run_cmd([
                            ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                            "-ss", f"{src_in:.4f}", "-t", f"{dur_a:.4f}",
                            "-i", aud_src,
                            "-vn", "-af", "highpass=f=150,lowpass=f=7500",
                            "-ar", str(SR), "-ac", "2", "-acodec", "pcm_s16le",
                            str(amb_wav),
                        ], check=False)
                        if res_a.returncode != 0 or not amb_wav.is_file():
                            continue
                        amb_arr, _ = load_stereo_wav_np(amb_wav)
                        if len(amb_arr) < 128 or float(np.max(np.abs(amb_arr))) < 1e-4:
                            continue
                        s_i = int(round(t0 * SR))
                        e_i = min(n_samples, s_i + len(amb_arr))
                        seg_len = e_i - s_i
                        if seg_len < 128:
                            continue
                        seg_amb = amb_arr[:seg_len].copy()
                        # 有人声时限制现场声比人声低至少 11dB 防掩蔽；无口播的纯特写动作间隙按参考人声/设定增益自然放出滋啦声
                        gain_db = min(-9.5, float(ac.get("ambient_gain_db", -10.0)))
                        v_seg_rms = float(np.sqrt(np.mean((voice_arr[s_i:e_i] * 0.95) ** 2) + 1e-10))
                        a_seg_rms = float(np.sqrt(np.mean(seg_amb ** 2) + 1e-10))
                        v_ref_rms = max(v_seg_rms, 0.08) if v_seg_rms < 0.015 else v_seg_rms
                        lin_g = min(10.0 ** (gain_db / 20.0), (v_ref_rms * 0.30) / max(1e-5, a_seg_rms))
                        fade_n = min(int(0.035 * SR), seg_len // 4)
                        if fade_n > 1:
                            seg_amb[:fade_n] *= np.linspace(0.0, 1.0, fade_n, dtype=np.float32)[:, None]
                            seg_amb[-fade_n:] *= np.linspace(1.0, 0.0, fade_n, dtype=np.float32)[:, None]
                        broll_ambient_arr[s_i:e_i] += seg_amb * lin_g
                        pre_mix_nosfx[s_i:e_i] += seg_amb * lin_g
                        broll_ambient_mixed_count += 1
        except Exception:
            pass

    # 局部防掩蔽校准：逐条核对 06_packaging SFX 峰值窗口 [t-0.04, t+0.16] 的 2–8kHz 可听度（不加噪、统一写入 pre_mix 与 08_sfx_master）
    pkg_p = pipeline_dir / "06_packaging.json"
    cues_early = read_json(pkg_p).get("sfx_cues", []) if pkg_p.exists() else []
    if cues_early and float(np.max(np.abs(sfx_arr))) > 1e-6:
        try:
            from scipy import signal as sp_sig
            from common import SFX_AUDIT_POST_SEC, SFX_AUDIT_PRE_SEC

            sos_hf = sp_sig.butter(4, [2000.0, 8000.0], btype="bandpass", fs=float(SR), output="sos")
            nosfx_hf = sp_sig.sosfiltfilt(sos_hf, pre_mix_nosfx.mean(axis=1).astype(np.float64))
            sfx_hf = sp_sig.sosfiltfilt(sos_hf, (sfx_arr * 0.95).mean(axis=1).astype(np.float64))
            fade_n = int(0.020 * SR)
            for cue in cues_early:
                pk_t = float(cue.get("peak_time_sec", cue.get("time_sec", 0.0)))
                on_t = float(cue.get("onset_time_sec", max(0.0, pk_t - 0.04)))
                ws_i = max(0, int(round((pk_t - SFX_AUDIT_PRE_SEC) * SR)))
                we_i = min(n_samples, int(round((pk_t + SFX_AUDIT_POST_SEC) * SR)))
                if we_i - ws_i < 64:
                    continue
                bg_rms = float(np.sqrt(np.mean(nosfx_hf[ws_i:we_i] ** 2) + 1e-12))
                cur_sfx_rms = float(np.sqrt(np.mean(sfx_hf[ws_i:we_i] ** 2) + 1e-12))
                if cur_sfx_rms < 1e-5:
                    continue
                # 若直接合成后的 2–8kHz 增量未显著高出人声掩蔽基底（预留 +4.2dB 压限余量），按平滑窗局部抬升
                comb_rms = float(np.sqrt(np.mean((nosfx_hf[ws_i:we_i] + sfx_hf[ws_i:we_i]) ** 2) + 1e-12))
                cur_lift_db = 20.0 * math.log10(max(1e-8, comb_rms) / max(1e-8, bg_rms))
                if cur_lift_db >= 4.2:
                    continue
                target_sfx_rms = bg_rms * (10.0 ** (4.4 / 20.0))
                need_scale = min(3.2, max(1.0, target_sfx_rms / cur_sfx_rms))
                if need_scale <= 1.05:
                    continue
                loc0 = max(0, int(round((on_t - 0.02) * SR)))
                loc1 = min(n_samples, int(round((on_t + 0.45) * SR)))
                if loc1 <= loc0 + 16:
                    continue
                loc_pk = float(np.max(np.abs(sfx_arr[loc0:loc1])))
                safe_scale = min(need_scale, 0.72 / max(1e-4, loc_pk))
                if safe_scale <= 1.05:
                    continue
                env_loc = np.full(loc1 - loc0, safe_scale, dtype=np.float32)
                fn = min(fade_n, (loc1 - loc0) // 4)
                if fn > 1:
                    env_loc[:fn] = np.linspace(1.0, safe_scale, fn, dtype=np.float32)
                    env_loc[-fn:] = np.linspace(safe_scale, 1.0, fn, dtype=np.float32)
                sfx_arr[loc0:loc1] *= env_loc[:, None]
        except Exception:
            pass

    pre_mix = pre_mix_nosfx + sfx_arr * 0.95
    pre_mix_wav = pipeline_dir / "08_premix_raw.wav"
    pre_mix_nosfx_wav = pipeline_dir / "08_premix_nosfx_raw.wav"
    save_stereo_wav_np(pre_mix_wav, pre_mix, SR)
    save_stereo_wav_np(pre_mix_nosfx_wav, pre_mix_nosfx, SR)

    # 3. 单源叠加迭代增益校准：保证最终磁盘 WAV 与 final_gain_db 100% 锁定一致
    master_wav = pipeline_dir / "08_mixed_master.wav"
    stem_nosfx_wav = pipeline_dir / "08_stem_nosfx.wav"
    init_metrics = measure_lufs_ebur128(pre_mix_wav)
    if init_metrics["integrated_lufs"] <= -65.0:
        cur_gain_db = 0.0
    else:
        cur_gain_db = max(-24.0, min(24.0, target_lufs - init_metrics["integrated_lufs"]))

    def _render_master_pair(gain_db: float) -> Dict[str, float]:
        g_clamped = max(-24.0, min(24.0, gain_db))
        for wav_src, wav_dst in ((pre_mix_wav, master_wav), (pre_mix_nosfx_wav, stem_nosfx_wav)):
            run_cmd([
                ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(wav_src),
                "-af", f"volume={g_clamped:.2f}dB,alimiter=limit=0.794:attack=2:release=45:level=disabled:latency=true",
                "-ar", str(SR), "-ac", "2", "-acodec", "pcm_s16le",
                str(wav_dst),
            ])
        return measure_lufs_ebur128(master_wav)

    metrics = _render_master_pair(cur_gain_db)
    if init_metrics["integrated_lufs"] > -65.0:
        for _attempt in range(3):
            err = target_lufs - metrics["integrated_lufs"]
            if abs(err) <= 0.35 and metrics["true_peak_dbtp"] <= -1.5:
                break
            if metrics["true_peak_dbtp"] > -1.5:
                cur_gain_db -= max(0.5, metrics["true_peak_dbtp"] + 1.5)
            else:
                cur_gain_db += err
            cur_gain_db = max(-24.0, min(24.0, cur_gain_db))
            metrics = _render_master_pair(cur_gain_db)

    # 同步导出三轨分离分轨 (人声规范母带 + 已闪避定电平 BGM含现场动作声 + 定电平 SFX)
    # 统一采用与母带 alimiter 一致的 0.794 (-2.0dB) 峰值上限，保证三轨求和真峰值不越线
    final_scale = 10.0 ** (cur_gain_db / 20.0)
    v_stem_raw = voice_arr * 0.95 * final_scale
    b_stem_raw = (ducked_bgm + broll_ambient_arr) * final_scale
    s_stem_raw = sfx_arr * 0.95 * final_scale
    bus_raw = v_stem_raw + b_stem_raw + s_stem_raw
    if n_samples > 0:
        win_n = max(64, int(0.020 * SR))
        n_blocks = max(1, (n_samples + win_n - 1) // win_n)
        pad_n = n_blocks * win_n - n_samples
        abs_bus = np.max(np.abs(bus_raw), axis=1)
        if pad_n > 0:
            abs_bus = np.pad(abs_bus, (0, pad_n), mode="constant")
        blk_peaks = np.max(abs_bus.reshape(n_blocks, win_n), axis=1)
        blk_gains = np.minimum(1.0, 0.794 / np.maximum(1e-5, blk_peaks)).astype(np.float32)
        if n_blocks >= 3:
            # 前看后看平滑避免瞬态陡变
            blk_gains = np.minimum(blk_gains, np.roll(blk_gains, -1))
            blk_gains = np.convolve(np.pad(blk_gains, (1, 1), mode="edge"), np.array([0.25, 0.5, 0.25], dtype=np.float32), mode="valid")
        centers = (np.arange(n_blocks, dtype=np.float64) + 0.5) * win_n
        env_gain = np.interp(np.arange(n_samples, dtype=np.float64), centers, blk_gains).astype(np.float32)[:, None]
        post_peak = float(np.max(np.abs(bus_raw * env_gain)))
        hard_cap = min(1.0, 0.84 / max(1e-5, post_peak))
        stem_gain_curve = env_gain * hard_cap
        bus_safe_scale = float(np.mean(stem_gain_curve))
    else:
        stem_gain_curve = np.ones((0, 1), dtype=np.float32)
        bus_safe_scale = 1.0
    voice_master_path = pipeline_dir / "08_voice_master.wav"
    bgm_ducked_path = pipeline_dir / "08_bgm_ducked.wav"
    sfx_master_path = pipeline_dir / "08_sfx_master.wav"
    save_stereo_wav_np(voice_master_path, v_stem_raw * stem_gain_curve, SR)
    save_stereo_wav_np(bgm_ducked_path, b_stem_raw * stem_gain_curve, SR)
    save_stereo_wav_np(sfx_master_path, s_stem_raw * stem_gain_curve, SR)

    # 使用 common 唯一权威函数 compute_sfx_band_windows 持久化全量 SFX 基准，供 #20 复验
    pkg_p = pipeline_dir / "06_packaging.json"
    cues = read_json(pkg_p).get("sfx_cues", []) if pkg_p.exists() else []
    scaled_nosfx, _ = load_stereo_wav_np(stem_nosfx_wav)
    sfx_windows = compute_sfx_band_windows(cues, scaled_nosfx.mean(axis=1).astype(np.float64), SR)
    write_json(pipeline_dir / "08_sfx_audit_window.json", {
        "step": "08_sfx_audit_window",
        "master_gain_db": round(cur_gain_db, 2),
        "windows": sfx_windows,
    })

    pre_mix_nosfx_wav.unlink(missing_ok=True)
    pre_mix_wav.unlink(missing_ok=True)
    voice_clean_wav.unlink(missing_ok=True)

    master_arr, _ = load_stereo_wav_np(master_wav)
    mono_phase_corr = compute_mono_phase_correlation(master_arr)

    out_metrics = {
        "step": "08_mix_audio",
        "master_wav": str(master_wav.resolve()),
        "stem_nosfx_wav": str(stem_nosfx_wav.resolve()),
        "voice_master_wav": str(voice_master_path.resolve()),
        "bgm_ducked_wav": str(bgm_ducked_path.resolve()),
        "sfx_master_wav": str(sfx_master_path.resolve()),
        "target_lufs": target_lufs,
        "master_gain_db": round(cur_gain_db, 2),
        "measured_lufs": metrics["integrated_lufs"],
        "lra_lu": metrics["lra_lu"],
        "true_peak_dbtp": metrics["true_peak_dbtp"],
        "voice_bgm_snr_db": voice_bgm_snr_db,
        "mono_phase_corr": mono_phase_corr,
        "noise_floor_db": round(noise_floor_db, 1),
        "vocal_comp_threshold_db": comp_thresh_db,
        "vocal_broadcast_chain": True,
        "dual_band_ducking": dual_band_ok,
        "voice_denoised": bool(use_denoise),
        "bgm_ducking_applied": True,
        "broll_ambient_mixed_count": broll_ambient_mixed_count,
        "stem_bus_safe_scale": round(bus_safe_scale, 4),
        "duration_sec": round(n_samples / float(SR), 4),
    }
    write_json(pipeline_dir / "08_mix_metrics.json", out_metrics)

    from compliance_guard import build_asset_license_manifest
    build_asset_license_manifest(pipeline_dir, out_dir=out_dir, licenses_path=licenses_path)

    print(
        f"[step8] 广播级混音完成：响度 {metrics['integrated_lufs']:.2f} LUFS | LRA {metrics['lra_lu']:.1f} LU | "
        f"SNR {voice_bgm_snr_db:.1f}dB | 单声道相位 {mono_phase_corr:.2f} -> 08_mixed_master.wav"
    )
    return out_metrics


def main() -> None:
    maybe_reexec_in_venv()
    parser = argparse.ArgumentParser(description="Step 8: 广播级人声母带、双频段闪避与 -14 LUFS 混音")
    parser.add_argument("--pipeline-dir", required=True)
    parser.add_argument("--target-lufs", type=float, default=TARGET_LUFS)
    parser.add_argument("--licenses-json", help="可选：外部商用授权登记 licenses.json")
    parser.add_argument("--out-dir", help="可选：同步写出授权清单的 out 目录")
    args = parser.parse_args()
    run_step8(
        Path(args.pipeline_dir),
        target_lufs=args.target_lufs,
        licenses_path=Path(args.licenses_json) if args.licenses_json else None,
        out_dir=Path(args.out_dir) if args.out_dir else None,
    )


if __name__ == "__main__":
    main()

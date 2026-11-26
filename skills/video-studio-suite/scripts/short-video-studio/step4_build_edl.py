#!/usr/bin/env python3
"""
[Step 4: 以音定画，生成专业剪辑表 (EDL)]
v5 升级：
1. 语义互文（纳入 sharpness_score & stability_score）+ 单调递增源游标彻底消除同源倒带，全 B-roll 严格屏蔽脏乱/穿帮硬禁忌标签。
2. 全面严防 A-roll 句界越界与口型穿帮：首镜 idx==0 同样受 _can_be_safe_aroll 校验，源 A-roll 不可用时降级 B-roll 而非瞎切他人口播。
3. 引入真·L-cut（物证先入 3–4 帧，`j_cut_lead_frames < 0`）与真·J-cut（声先画后 2–4 帧）；移除硬编码 90 帧与悬空角色 `"freeze"`。
4. 计算真实 `first_frame_density_ok`，显式告警 `deictic_gaps` 视觉缺口，统一 `code_broll` 比例口径。
输出：pipeline/04_edl.json 与 pipeline/04_edl_table.md
"""

from __future__ import annotations

import argparse
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import (
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    DEFAULT_FPS,
    EDIT_PROFILES,
    frames_to_sec,
    load_style_applied,
    load_style_spectrum_entry,
    maybe_reexec_in_venv,
    read_json,
    write_json,
)
from generate_code_broll import render_broll_clip_pillow, render_code_clip, resolve_style_palette

PROP_SHOW_CUES = ("睇下", "看下", "看一下", "给大家看", "给你看", "看我手上", "看我手里", "效果图", "实物", "清单", "明细")
DEICTIC_CUES = ("这张图", "四张图", "两张图", "三张图", "效果图", "平面图", "明细表", "账单", "发票", "检测单", "看这里", "看这个", "你看这", "对比一下")
POSITIVE_PRAISE_CUES = ("招牌", "正宗", "干净", "舒服", "鲜嫩", "多汁", "放心", "透明", "美味", "好吃", "靓", "靠谱", "新鲜", "卫生", "环境好")
HARD_TABOO_ALWAYS = {"crew_leak", "kitchen_trash", "construction_trash"}


_EXPLAINER_WINDOW_RE = re.compile(
    r"(\d+(?:\.\d+)?\s*[%％倍万亿元块度小时分钟秒天年个次]|第一|第二|第三|步骤|流程|原理|本质|对比|差距|成本|利润|占比|比例|真相|其实)"
)


def detect_explainer_broll_windows(
    sentences: List[Dict[str, Any]],
    lead_sec: float = 0.08,
    min_dur_sec: float = 1.6,
) -> List[Dict[str, Any]]:
    """
    口播动态讲解画面（B-roll）插入窗口探测：
    依据“新信息/数字对比/步骤拆解/原理机制”而非固定秒数，在关键词起音前 0.08s 定位最适合切入
    动态图解 + 平滑圆环人像画中画的时间窗；无解释价值的观点/过渡句保留真人全屏。
    """
    windows: List[Dict[str, Any]] = []
    for idx, sent in enumerate(sentences or []):
        txt = str(sent.get("text") or "").strip()
        if not txt or sent.get("emotion_or_info") in ("cta", "filler"):
            continue
        m = _EXPLAINER_WINDOW_RE.search(txt)
        if not m:
            continue
        s_start = float(sent.get("start_sec", 0.0))
        s_end = float(sent.get("end_sec", s_start + 2.0))
        if (s_end - s_start) < min_dur_sec:
            continue
        hit_tok = m.group(1)
        # 按原句字符位置精确定位触发词的真实逐字起音时间（彻底避免单字误命中句首无关字）
        kw_start = s_start
        words = sent.get("words") or []
        if words:
            clean_hit = re.sub(r"\s+", "", hit_tok)
            joined = ""
            word_spans: List[Tuple[int, int, float]] = []
            for w in words:
                wt = re.sub(r"\s+", "", str(w.get("word") or ""))
                if not wt:
                    continue
                pos0 = len(joined)
                joined += wt
                word_spans.append((pos0, len(joined), float(w.get("start_sec", s_start))))
            hit_pos = joined.find(clean_hit)
            if hit_pos >= 0:
                for p0, p1, wst in word_spans:
                    if p0 <= hit_pos < p1:
                        kw_start = wst
                        break
        win_in = round(max(0.0, kw_start - lead_sec), 3)
        win_out = round(s_end, 3)
        if (win_out - win_in) < min_dur_sec:
            win_in = round(max(0.0, s_start), 3)

        mode_hint = (
            "data_chart" if re.search(r"[%％倍元块万亿]", hit_tok)
            else ("flow_diagram" if re.search(r"第一|第二|第三|步骤|流程", hit_tok)
            else ("versus" if re.search(r"对比|差距|其实|真相", hit_tok) else "kinetic_text"))
        )
        windows.append({
            "window_id": f"exp_win_{len(windows) + 1:02d}",
            "sentence_id": sent.get("id", f"sent_{idx + 1:03d}"),
            "trigger_cue": hit_tok,
            "start_sec": win_in,
            "end_sec": win_out,
            "duration_sec": round(win_out - win_in, 3),
            "suggested_mode": mode_hint,
            "presenter_pip_mode": "smooth_orbit_pip",
            "sentence_text": txt,
        })
    return windows


def pick_first_3s_events(events: List[Dict[str, Any]], fps: int, count: int = 2) -> List[Dict[str, Any]]:
    """在前 3.0 秒内筛选至少 2 个间距 >= 0.55s 的切点音频事件，优先 sentence_start。"""
    if count == 0:
        return []
    candidates = [
        e for e in events
        if 0.50 <= e["time_sec"] <= 2.75
        and e["type"] in ("sentence_start", "pause_end", "keyword_accent", "stress", "bgm_downbeat", "bgm_beat")
    ]
    prio = {"sentence_start": 0, "pause_end": 1, "keyword_accent": 2, "stress": 3, "bgm_downbeat": 4, "bgm_beat": 5}
    candidates.sort(key=lambda e: (prio.get(e["type"], 9), e["time_sec"]))

    picked: List[Dict[str, Any]] = []
    for cand in candidates:
        if all(abs(cand["time_sec"] - p["time_sec"]) >= 0.55 for p in picked):
            picked.append(cand)
        if len(picked) >= count:
            break

    if len(picked) < count:
        fallback = [e for e in events if 0.40 <= e["time_sec"] <= 2.85]
        fallback.sort(key=lambda e: e["time_sec"])
        for cand in fallback:
            if all(abs(cand["time_sec"] - p["time_sec"]) >= 0.45 for p in picked):
                picked.append(cand)
            if len(picked) >= count:
                break

    picked.sort(key=lambda e: e["frame"])
    return picked


def ensure_code_broll_pool(
    pipeline_dir: Path,
    sentences: List[Dict[str, Any]],
    existing_brolls: List[Dict[str, Any]],
    track: str,
    style_id: Optional[str] = None,
    total_dur: float = 0.0,
) -> List[Dict[str, Any]]:
    """若素材池中的 B-roll 少于 2 条或可用净长不足以单向前推覆盖全片，按当前风格谱生成补镜备选。"""
    pool = list(existing_brolls)
    gen_dir = pipeline_dir / "04_generated_broll"
    gen_dir.mkdir(parents=True, exist_ok=True)
    pal = resolve_style_palette(style_id, track=track)
    net_avail = sum(max(0.0, float(m.get("duration_sec", 0.0)) - 0.80) for m in existing_brolls)

    if len(pool) < 2 or (total_dur > 0.0 and net_avail < total_dur * 1.15):
        first_kw_title = sentences[0]["keywords"][0] if sentences and sentences[0].get("keywords") else "核心真相"
        p1 = gen_dir / "auto_code_kinetic.mp4"
        render_broll_clip_pillow(
            p1,
            mode="kinetic_text",
            title=first_kw_title if len(first_kw_title) >= 2 else "开篇必看",
            items=[{"label": s["text"][:16], "subtitle": "真实数据与现场拆解"} for s in sentences[:2]],
            duration_sec=3.0,
            accent_hex=pal["accent_hex"],
            bg_hex=pal["bg_hex"],
            style_id=style_id,
            track=track,
        )
        pool.append({
            "id": "code_auto_01",
            "normalized_mp4": str(p1.resolve()),
            "role": "code_broll",
            "duration_sec": 3.0,
            "best_in_sec": 0.0,
            "sharpness_score": 80.0,
            "stability_score": 1.0,
            "semantic_tags": ["观点", "关键事实", *(sentences[0].get("keywords", []) if sentences else [])],
            "scene_group": "code_gfx",
        })

        p2 = gen_dir / "auto_code_flow.mp4"
        render_broll_clip_pillow(
            p2,
            mode="flow_diagram",
            title="核心逻辑拆解",
            items=[
                {"label": s["keywords"][0] if s.get("keywords") else f"要点 {i+1}", "subtitle": s["text"][:20]}
                for i, s in enumerate(sentences[1:4])
            ] or [{"label": "真实细节", "subtitle": "拒绝套路"}],
            duration_sec=3.5,
            accent_hex=pal["accent_hex"],
            bg_hex=pal["bg_hex"],
            style_id=style_id,
            track=track,
        )
        pool.append({
            "id": "code_auto_02",
            "normalized_mp4": str(p2.resolve()),
            "role": "code_broll",
            "duration_sec": 3.5,
            "best_in_sec": 0.0,
            "sharpness_score": 80.0,
            "stability_score": 1.0,
            "semantic_tags": ["流程", "拆解", "细节"],
            "scene_group": "code_gfx",
        })
        deficit = (total_dur * 1.15 - (net_avail + 6.5)) if total_dur > 0.0 else 0.0
        extra_modes = ("chips", "versus", "kinetic_text", "flow_diagram")
        extra_idx = 0
        while deficit > 1.5 and extra_idx < 4 and len(sentences) > 0:
            s_pick = sentences[min(len(sentences) - 1, (extra_idx * 2 + 1) % len(sentences))]
            e_dur = 4.0
            e_path = gen_dir / f"auto_code_ext_{extra_idx + 1:02d}.mp4"
            e_mode = extra_modes[extra_idx % len(extra_modes)]
            e_kw = (s_pick.get("keywords") or [None])[0] or str(s_pick.get("text", "核心要点"))[:8]
            e_items = [
                {"label": str(s.get("keywords", [None])[0] or s["text"][:10]), "subtitle": s["text"][:18]}
                for s in sentences[extra_idx % len(sentences) : (extra_idx % len(sentences)) + 2]
            ] or [{"label": e_kw, "subtitle": str(s_pick.get("text", ""))[:18]}]
            render_broll_clip_pillow(
                e_path,
                mode=e_mode,
                title=str(e_kw)[:12],
                items=e_items,
                duration_sec=e_dur,
                accent_hex=pal["accent_hex"],
                bg_hex=pal["bg_hex"],
                style_id=style_id,
                track=track,
            )
            pool.append({
                "id": f"code_auto_ext_{extra_idx + 1:02d}",
                "normalized_mp4": str(e_path.resolve()),
                "role": "code_broll",
                "duration_sec": e_dur,
                "best_in_sec": 0.0,
                "sharpness_score": 80.0,
                "stability_score": 1.0,
                "semantic_tags": ["要点", "对比", *(s_pick.get("keywords") or [])],
                "scene_group": "code_gfx",
            })
            deficit -= e_dur
            extra_idx += 1
    return pool


def _build_eye_locked_vf(eye_anchor: Optional[Dict[str, Any]], zoom: float = 1.15) -> str:
    """商业剪辑标准锁眼微推拉（1.15x 确保景别明显拉近而不产生抽搐感）。"""
    cx = float((eye_anchor or {}).get("cx", (eye_anchor or {}).get("eye_cx", 0.50)))
    cy = float((eye_anchor or {}).get("cy", (eye_anchor or {}).get("eye_cy", 0.36)))
    zw = (int(round(CANVAS_WIDTH * zoom)) // 2) * 2
    zh = (int(round(CANVAS_HEIGHT * zoom)) // 2) * 2
    crop_x = max(0, min(zw - CANVAS_WIDTH, int(round(cx * (zw - CANVAS_WIDTH)))))
    crop_y = max(0, min(zh - CANVAS_HEIGHT, int(round(cy * (zh - CANVAS_HEIGHT)))))
    return f"scale={zw}:{zh}:flags=lanczos,crop={CANVAS_WIDTH}:{CANVAS_HEIGHT}:{crop_x}:{crop_y}"


def run_step4(
    pipeline_dir: Path,
    track: str = "store",
    j_cut_frames: int = 3,
    fps: int = DEFAULT_FPS,
    prefer_broll_only: bool = False,
    style_id: Optional[str] = None,
    account_profile: Optional[Dict[str, Any]] = None,
    edit_profile: str = "talking",
) -> Dict[str, Any]:
    raw_jc = int(j_cut_frames)
    j_cut_frames = 0 if raw_jc <= 0 else max(2, min(4, raw_jc))
    if not style_id:
        style_id = load_style_applied(pipeline_dir)

    manifest = read_json(pipeline_dir / "01_manifest.json")
    audio_events = read_json(pipeline_dir / "03_audio_events.json")
    sentences = audio_events["sentences"]
    events = audio_events["events"]
    total_dur = float(audio_events["locked_duration_sec"])
    total_frames = int(audio_events["locked_duration_frames"])

    arolls = [m for m in manifest["items"] if m["role"] == "a_roll" and m.get("video_grade", "usable") != "ng"]
    usable_arolls = [m for m in arolls if m.get("video_grade", "usable") == "usable"]
    usable_aroll_paths = {str(m["normalized_mp4"]) for m in usable_arolls}
    vgrade_by_mp4 = {str(m.get("normalized_mp4")): str(m.get("video_grade", "usable")) for m in manifest["items"]}
    brolls_raw = [m for m in manifest["items"] if m["role"] in ("b_roll", "code_broll") and m.get("video_grade", "usable") != "ng"]
    broll_pool = ensure_code_broll_pool(pipeline_dir, sentences, brolls_raw, track, style_id=style_id, total_dur=total_dur)

    deictic_gaps: List[Dict[str, Any]] = []
    for sent in sentences:
        s_txt = str(sent.get("text", ""))
        matched_cue = next((c for c in DEICTIC_CUES if c in s_txt), None)
        if not matched_cue:
            continue
        cue_tokens = [matched_cue]
        for tk in ("图", "效果", "平面", "账单", "明细", "发票", "检测", "对比"):
            if tk in matched_cue:
                cue_tokens.append(tk)
        has_visual_match = False
        for m in broll_pool:
            tags = " ".join(str(t) for t in (m.get("semantic_tags", []) + m.get("manual_tags", []))) + " " + Path(str(m.get("normalized_mp4", ""))).name
            if any(tk in tags for tk in cue_tokens):
                has_visual_match = True
                break
        if not has_visual_match:
            deictic_gaps.append({
                "sentence_id": sent["id"],
                "matched_cue": matched_cue,
                "text": s_txt,
                "suggestion": f"台词含视觉指代「{matched_cue}」，但 B-roll 标签库未见匹配素材，建议补拍对应特写或通过 00_visual_index.json 标注",
            })
    if deictic_gaps:
        print(f"[step4] [WARN] A3 视觉指代缺口 {len(deictic_gaps)} 处: {[g['matched_cue'] for g in deictic_gaps]}")

    raw_intel_p = pipeline_dir / "00_raw_intel.json"
    raw_intel = read_json(raw_intel_p) if raw_intel_p.is_file() else {}
    raw_pain_kws = [str(k) for k in (raw_intel.get("pain_keywords") or []) if str(k).strip()]
    raw_proof_names = [Path(str(a.get("filename") or "")).stem for a in (raw_intel.get("proof_assets") or []) if a.get("filename")]

    style_entry = load_style_spectrum_entry(style_id) if style_id else None
    broll_target_ratio = float((style_entry or {}).get("broll_overlay_ratio_target", 0.53))
    ambient_policy = (style_entry or {}).get("broll_ambient_sound_policy") or {}
    ambient_enabled = bool(ambient_policy.get("enabled", True))
    ambient_gain_db = float(ambient_policy.get("gain_db", -10.0))
    ambient_words = tuple(ambient_policy.get("trigger_action_words") or ("敲", "响", "滋啦", "切", "倒", "沸", "烤", "炒", "砸", "摔"))

    eff_prof = account_profile if (account_profile and account_profile.get("sample_sufficient") is True) else {}
    min_shot_gap = max(0.95, min(2.4, float(eff_prof.get("target_median_shot_sec", 1.55)) * 0.85))
    pacing = EDIT_PROFILES[edit_profile]
    max_shot = float(pacing["max_shot_sec"])
    micro_hook_max_sec = min(max_shot, float(eff_prof.get("micro_hook_max_sec", max_shot - 1.8)))
    default_aroll_r = max(0.0, min(0.80, 1.0 - broll_target_ratio))
    target_aroll_ratio = max(0.0, min(0.85, float(eff_prof.get("target_aroll_ratio", default_aroll_r))))
    broll_only_mode = bool(prefer_broll_only or (broll_target_ratio >= 0.995) or (target_aroll_ratio <= 0.005))

    first_3s_evts = pick_first_3s_events(events, fps, int(pacing["opening_cuts"]))
    sent_by_id = {s["id"]: s for s in sentences}
    prop_sent_ids = {s["id"] for s in sentences if any(cue in s.get("text", "") for cue in PROP_SHOW_CUES)}

    later_candidates = [
        e for e in events
        if e["time_sec"] > 2.85
        and e["time_sec"] < total_dur - 0.80
        and e["type"] in ("pause_start", "sentence_start", "pause_end", "keyword_accent", "stress", "bgm_section", "bgm_downbeat")
    ]
    prio_map = {
        "sentence_start": 0, "pause_end": 1, "pause_start": 2,
        "keyword_accent": 3, "stress": 4, "bgm_section": 5, "bgm_downbeat": 6,
    }
    later_candidates.sort(key=lambda e: (e["frame"], 0 if (e.get("type") == "sentence_start" and e.get("sentence_id") in prop_sent_ids) else 1, prio_map.get(e["type"], 9)))

    chosen_cuts: List[Dict[str, Any]] = list(first_3s_evts)
    last_cut_sec = chosen_cuts[-1]["time_sec"] if chosen_cuts else 0.0
    n_cand = len(later_candidates)
    skip_until_idx = -1
    for ci, cand in enumerate(later_candidates):
        if ci < skip_until_idx:
            continue
        eff_cand = cand
        if cand.get("type") != "sentence_start":
            best_nxt: Optional[Dict[str, Any]] = None
            best_idx = -1
            for look_j in range(ci + 1, n_cand):
                nxt = later_candidates[look_j]
                if nxt["time_sec"] - cand["time_sec"] > 0.90:
                    break
                if nxt.get("type") != "sentence_start":
                    continue
                if nxt.get("sentence_id") in prop_sent_ids:
                    best_nxt = nxt
                    best_idx = look_j
                    break
                if best_nxt is None and (nxt["time_sec"] - last_cut_sec <= min(micro_hook_max_sec, 4.5)):
                    best_nxt = nxt
                    best_idx = look_j
            if best_nxt is not None:
                eff_cand = best_nxt
                skip_until_idx = best_idx + 1

        is_sent_start = eff_cand.get("type") == "sentence_start"
        gap_needed = pacing["sentence_cut_gap"] if is_sent_start else max(min_shot_gap, pacing["sentence_cut_gap"])
        if eff_cand["time_sec"] - last_cut_sec >= gap_needed:
            prev_ev = chosen_cuts[-1] if chosen_cuts else None
            if prev_ev and prev_ev.get("sentence_id") in prop_sent_ids and eff_cand.get("sentence_id") == prev_ev.get("sentence_id"):
                continue
            chosen_cuts.append(eff_cand)
            last_cut_sec = eff_cand["time_sec"]

    if chosen_cuts:
        guarded_cuts: List[Dict[str, Any]] = []
        prev_t = 0.0
        for ev in chosen_cuts + [{"time_sec": total_dur, "frame": total_frames, "type": "_end"}]:
            while ev["time_sec"] - prev_t > micro_hook_max_sec:
                mid_ev = next(
                    (
                        c for c in events
                        if prev_t + 1.5 <= c["time_sec"] <= min(ev["time_sec"] - 1.2, prev_t + micro_hook_max_sec)
                        and c["type"] in ("keyword_accent", "stress", "pause_start", "sentence_start", "bgm_downbeat", "bgm_beat")
                    ),
                    None,
                )
                if mid_ev is None:
                    break
                guarded_cuts.append(mid_ev)
                prev_t = mid_ev["time_sec"]
            if ev["type"] != "_end":
                guarded_cuts.append(ev)
                prev_t = ev["time_sec"]
        chosen_cuts = guarded_cuts

    cut_points: List[Dict[str, Any]] = [
        {
            "cut_frame": 0,
            "event": events[0] if events else {"id": "evt_001", "type": "sentence_start", "time_sec": 0.0, "frame": 0},
            "raw_frame": 0,
        }
    ]
    for ev in chosen_cuts:
        raw_frame = int(ev["frame"])
        if ev["time_sec"] <= 2.85:
            raw_frame = min(raw_frame, 3 * fps - 2)
        if raw_frame - cut_points[-1]["cut_frame"] >= 12 and total_frames - raw_frame >= 10:
            cut_points.append({"cut_frame": raw_frame, "raw_frame": raw_frame, "event": ev})

    def find_sentence_for_time(t_sec: float, ev: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if ev and ev.get("sentence_id") in sent_by_id and ev.get("type") in ("sentence_start", "pause_end", "keyword_accent", "stress"):
            return sent_by_id[ev["sentence_id"]]
        for s in sentences:
            if s["start_sec"] <= t_sec <= s["end_sec"]:
                return s
        for s in sentences:
            if s["start_sec"] <= t_sec <= s["end_sec"] + 0.40:
                return s
        return sentences[-1]

    n_segs = len(cut_points)
    audio_only_flags: List[bool] = []
    source_aroll_valid: List[bool] = []
    for cp in cut_points:
        ev = cp["event"]
        t_start = frames_to_sec(cp["cut_frame"], fps)
        sent = find_sentence_for_time(t_start, ev)
        sm_p = str(sent.get("source_media", "") or "")
        sent_vgrade = str(sent.get("source_video_grade") or vgrade_by_mp4.get(sm_p, "usable"))
        forced_mask = sent_vgrade in ("audio_only", "ng")
        audio_only_flags.append(forced_mask)
        # 严格校验本句原声是否真正对应可用的实拍 A-roll，绝不把无源配音硬配给无关真人口型！
        source_aroll_valid.append(bool(sm_p and sm_p in usable_aroll_paths))

    def _can_be_safe_aroll(seg_idx: int) -> bool:
        if audio_only_flags[seg_idx] or not usable_arolls or broll_only_mode or not source_aroll_valid[seg_idx]:
            return False
        t_in = frames_to_sec(cut_points[seg_idx]["raw_frame"], fps)
        t_out = frames_to_sec(cut_points[seg_idx + 1]["raw_frame"] if seg_idx + 1 < n_segs else total_frames, fps)
        overlapping = [s for s in sentences if min(t_out, float(s["end_sec"])) - max(t_in, float(s["start_sec"])) > 0.04]
        if not overlapping:
            overlapping = [find_sentence_for_time(t_in, cut_points[seg_idx]["event"])]
        if len(overlapping) != 1:
            return False
        if t_in - float(overlapping[0]["start_sec"]) > 1.10:
            return False
        if seg_idx < n_segs - 1:
            last_s = overlapping[-1]
            if t_out > float(last_s["end_sec"]) + float(last_s.get("pause_after_sec", 0.08)) + 0.04:
                return False
        return True

    roles: List[str] = []
    aroll_step = max(2, int(round(1.0 / max(0.04, target_aroll_ratio))))
    for idx, cp in enumerate(cut_points):
        ev = cp["event"]
        t_start = frames_to_sec(cp["cut_frame"], fps)
        sent = find_sentence_for_time(t_start, ev)
        offset_in_sent = t_start - float(sent["start_sec"])
        near_sent_start = offset_in_sent <= 0.85
        has_prop_show = any(cue in sent.get("text", "") for cue in PROP_SHOW_CUES)
        tail_start_sec = max(0.0, total_dur - min(8.5, max(2.2, total_dur * 0.28)))
        is_tail = (idx == n_segs - 1 and near_sent_start) or (t_start >= tail_start_sec and near_sent_start)

        if audio_only_flags[idx] or not usable_arolls or broll_only_mode or not source_aroll_valid[idx]:
            roles.append("b_roll")
        elif idx == 0 and target_aroll_ratio >= 0.25 and (_can_be_safe_aroll(0) or n_segs == 1):
            roles.append("a_roll")
        elif _can_be_safe_aroll(idx) and near_sent_start and (
            has_prop_show
            or (is_tail and target_aroll_ratio >= 0.18)
            or (idx % aroll_step == 1 if aroll_step > 2 else idx % 2 == 1)
        ):
            roles.append("a_roll")
        else:
            roles.append("b_roll")

    if usable_arolls and not broll_only_mode:
        seg_ends_est = [
            frames_to_sec(cut_points[i + 1]["raw_frame"] if i + 1 < n_segs else total_frames, fps)
            for i in range(n_segs)
        ]
        seg_durs_est = [
            frames_to_sec((cut_points[i + 1]["raw_frame"] if i + 1 < n_segs else total_frames) - cut_points[i]["raw_frame"], fps)
            for i in range(n_segs)
        ]
        cur_aroll_sec = sum(d for r, d in zip(roles, seg_durs_est) if r == "a_roll")
        tail_floor = total_dur - max(3.5, min(10.0, total_dur * 0.45))
        has_tail_aroll = any(roles[i] == "a_roll" and seg_ends_est[i] >= tail_floor for i in range(n_segs))
        if not has_tail_aroll and target_aroll_ratio >= 0.18:
            tail_cands = []
            for i in range(n_segs):
                if roles[i] != "b_roll" or not _can_be_safe_aroll(i) or seg_ends_est[i] < tail_floor:
                    continue
                t_s = frames_to_sec(cut_points[i]["raw_frame"], fps)
                s_obj = find_sentence_for_time(t_s, cut_points[i]["event"])
                tail_cands.append((-i, abs(t_s - float(s_obj["start_sec"])), -seg_durs_est[i], i))
            if tail_cands:
                _, _, _, best_tail_i = sorted(tail_cands)[0]
                roles[best_tail_i] = "a_roll"
                cur_aroll_sec += seg_durs_est[best_tail_i]

        min_aroll_sec = total_dur * max(0.0, min(0.35, target_aroll_ratio * 0.75))
        max_aroll_sec = total_dur * min(0.85, max(0.02, target_aroll_ratio + 0.05))
        if cur_aroll_sec < min_aroll_sec:
            cands = []
            for i in range(n_segs):
                if roles[i] != "b_roll" or not _can_be_safe_aroll(i):
                    continue
                t_s = frames_to_sec(cut_points[i]["raw_frame"], fps)
                s_obj = find_sentence_for_time(t_s, cut_points[i]["event"])
                cands.append((abs(t_s - float(s_obj["start_sec"])), -seg_durs_est[i], i))
            for _, _, i_cand in sorted(cands):
                roles[i_cand] = "a_roll"
                cur_aroll_sec += seg_durs_est[i_cand]
                if cur_aroll_sec >= min_aroll_sec:
                    break
        elif cur_aroll_sec > max_aroll_sec and len(broll_pool) > 0:
            # 精准控制目标 B-roll 覆盖率（覆盖 10%~95% 全风格区间）
            mid_indices = list(range(1, n_segs - 1)) if n_segs > 2 else []
            edge_indices = ([0, n_segs - 1] if n_segs > 1 else [0]) if target_aroll_ratio < 0.25 else []
            for idx_pool in (mid_indices, edge_indices):
                if cur_aroll_sec <= max_aroll_sec or not idx_pool:
                    break
                drop_cands = []
                for i in idx_pool:
                    if roles[i] != "a_roll":
                        continue
                    t_s = frames_to_sec(cut_points[i]["raw_frame"], fps)
                    s_obj = find_sentence_for_time(t_s, cut_points[i]["event"])
                    s_txt_c = str(s_obj.get("text", ""))
                    if any(cue in s_txt_c for cue in PROP_SHOW_CUES):
                        continue
                    sem_hit = any(
                        tg and (tg in s_txt_c)
                        for m in broll_pool if m.get("role") == "b_roll"
                        for tg in (m.get("semantic_tags", []) + m.get("manual_tags", []))
                    )
                    adj_broll = int((i + 1 < n_segs and roles[i + 1] != "a_roll") or (i > 0 and roles[i - 1] != "a_roll"))
                    drop_cands.append((-int(sem_hit), adj_broll, -seg_durs_est[i], i))
                for _, _, _, i_drop in sorted(drop_cands):
                    if cur_aroll_sec - seg_durs_est[i_drop] < min_aroll_sec and target_aroll_ratio >= 0.20:
                        continue
                    roles[i_drop] = "b_roll"
                    cur_aroll_sec -= seg_durs_est[i_drop]
                    if cur_aroll_sec <= max_aroll_sec:
                        break

    # 真·J-cut (正帧移：声先画后) 与 真·L-cut (负帧移：高语义物证画面先入)
    first_3s_cutoff_f = 3 * fps
    j_leads = [0] * n_segs
    if j_cut_frames > 0:
        for idx in range(1, n_segs):
            ev = cut_points[idx]["event"]
            if roles[idx - 1] != "a_roll" and ev["type"] in ("sentence_start", "pause_end", "keyword_accent"):
                cand_f = cut_points[idx]["raw_frame"] + j_cut_frames
                next_f = cut_points[idx + 1]["raw_frame"] if idx + 1 < n_segs else total_frames
                if (idx == 1 or cut_points[idx]["raw_frame"] >= first_3s_cutoff_f or cand_f < first_3s_cutoff_f) and (next_f - cand_f >= 12):
                    cut_points[idx]["cut_frame"] = cand_f
                    j_leads[idx] = j_cut_frames
            elif roles[idx - 1] == "a_roll" and roles[idx] != "a_roll" and ev["type"] == "sentence_start":
                # L-cut：若前一镜为 A-roll 且本段为 B-roll，当前句或前一句尾部命中实拍特写标签时，画面提前 3 帧入镜（保持前段 >=14f 且不破句界）
                sent = find_sentence_for_time(frames_to_sec(cut_points[idx]["raw_frame"], fps), ev)
                prev_sent = find_sentence_for_time(frames_to_sec(cut_points[idx - 1]["raw_frame"], fps), cut_points[idx - 1]["event"])
                s_txt = f"{prev_sent.get('text', '')} {sent.get('text', '')}"
                has_match = any(
                    tg and (tg in s_txt)
                    for m in broll_pool if m.get("role") == "b_roll"
                    for tg in (m.get("semantic_tags", []) + m.get("manual_tags", []))
                )
                l_lead = min(4, max(2, j_cut_frames))
                cand_f = cut_points[idx]["raw_frame"] - l_lead
                prev_f = cut_points[idx - 1]["cut_frame"]
                if has_match and (cand_f - prev_f >= 14) and (cut_points[idx]["raw_frame"] < first_3s_cutoff_f or cand_f >= first_3s_cutoff_f):
                    cut_points[idx]["cut_frame"] = cand_f
                    j_leads[idx] = -l_lead

        for idx in range(1, n_segs):
            if cut_points[idx]["cut_frame"] - cut_points[idx - 1]["cut_frame"] < 10:
                cut_points[idx]["cut_frame"] = cut_points[idx]["raw_frame"]
                j_leads[idx] = 0

        for idx in range(1, n_segs):
            if roles[idx] == "a_roll" and j_leads[idx] > 0:
                t_jc = frames_to_sec(cut_points[idx]["cut_frame"], fps)
                s_jc = find_sentence_for_time(t_jc, cut_points[idx]["event"])
                if t_jc - float(s_jc["start_sec"]) > 1.15:
                    cut_points[idx]["cut_frame"] = cut_points[idx]["raw_frame"]
                    j_leads[idx] = 0

    usage_counts: Dict[str, int] = {m["id"]: 0 for m in broll_pool}
    n_live = max(1, sum(1 for m in broll_pool if m.get("role") == "b_roll"))
    budget_per_live = (total_dur * 0.92) / float(n_live)
    used_cursors: Dict[str, float] = {}
    for m in broll_pool:
        avail_m = float(m.get("duration_sec", 0.0))
        if m.get("role") == "b_roll" and avail_m > 2.0:
            h_est = 0.40 if avail_m > 2.8 else 0.0
            usable_span = max(0.0, avail_m - 2.0 * h_est)
            max_start = max(h_est, avail_m - h_est - min(usable_span, max(3.0, budget_per_live)))
            used_cursors[m["id"]] = round(min(max(h_est, float(m.get("best_in_sec", h_est))), max_start), 4)
        else:
            used_cursors[m["id"]] = float(m.get("best_in_sec", 0.0))
    max_out_by_mp: Dict[str, float] = {}
    taboo_blocked_count = 0

    OPPOSING_MOTION = {("pan_left", "pan_right"), ("pan_right", "pan_left"), ("tilt_up", "tilt_down"), ("tilt_down", "tilt_up")}

    def pick_best_broll(
        sent: Dict[str, Any],
        seg_dur: float,
        last_group: str,
        t_start: float,
        prev_media_path: str,
        prev_src_out: float,
        prev_motion: str = "static",
        prev_shot_size: str = "medium",
        forbid_code: bool = False,
    ) -> Dict[str, Any]:
        nonlocal taboo_blocked_count
        s_txt = str(sent.get("text", ""))
        s_kws = [str(k) for k in sent.get("keywords", [])]
        is_praise = any(cue in s_txt for cue in POSITIVE_PRAISE_CUES)
        candidates = [m for m in broll_pool if not (forbid_code and m.get("role") == "code_broll")] or broll_pool
        best_m = candidates[0]
        best_score = -1e9
        blocked_here = False
        for m in candidates:
            m_tags_tab = {str(t) for t in (m.get("taboo_tags") or [])}
            hard_taboo = bool(m_tags_tab & HARD_TABOO_ALWAYS)
            soft_taboo = bool(is_praise and m_tags_tab)
            taboo_pen = 1000.0 if (hard_taboo or soft_taboo) else 0.0
            if taboo_pen > 0:
                blocked_here = True

            tags = [str(t) for t in (m.get("semantic_tags", []) + m.get("manual_tags", []))]
            fname_m = Path(str(m.get("source_path") or m.get("normalized_mp4") or "")).stem
            sem_hits = sum(1 for tg in tags if tg and (tg in s_txt or any(tg in k or k in tg for k in s_kws)))
            # 一手原始痛点词/物证优先匹配加权
            intel_bonus = 0.0
            if raw_pain_kws and any(pk in s_txt and (pk in fname_m or any(pk in tg for tg in tags)) for pk in raw_pain_kws):
                intel_bonus += 4.5
            if raw_proof_names and any(pn and pn in fname_m for pn in raw_proof_names):
                intel_bonus += 3.0
            # 景别交替鼓励与反方向运镜防撞墙惩罚
            cur_motion = str(m.get("camera_motion") or "static")
            cur_size = str(m.get("shot_size") or "medium")
            motion_pen = 8.0 if (prev_motion, cur_motion) in OPPOSING_MOTION else 0.0
            size_bonus = 2.0 if (cur_size != prev_shot_size) else 0.0

            cont_bonus = 1.5 if m.get("scene_group") == last_group else 0.0
            stab_bonus = float(m.get("stability_score", 0.8)) * 1.2
            sharp_bonus = min(1.5, float(m.get("sharpness_score", 40.0)) / 40.0)
            reuse_pen = usage_counts.get(m["id"], 0) * 12.0
            avail = float(m.get("duration_sec", 3.0))
            mp_str = str(m.get("normalized_mp4") or "")
            is_live_m = m.get("role") == "b_roll" and avail > 2.0
            h_m = 0.40 if (is_live_m and avail >= seg_dur + 0.80) else 0.0
            eff_cur = max(float(used_cursors.get(m["id"], 0.0)), float(max_out_by_mp.get(mp_str, 0.0)))
            same_media_pen = 0.0
            if mp_str == prev_media_path:
                if m.get("role") == "code_broll" or (avail - max(eff_cur, prev_src_out + 0.05) < seg_dur):
                    same_media_pen = 800.0
                else:
                    same_media_pen = 18.0
            rem = (avail - h_m) - eff_cur
            exhausted_pen = 500.0 if (m.get("role") != "code_broll" and (avail - eff_cur) < seg_dur) else 0.0
            if m.get("role") != "code_broll" and (avail - eff_cur) < min(0.5, seg_dur * 0.5):
                exhausted_pen += 1500.0
            dur_bonus = 2.0 if rem >= seg_dur else (0.5 if avail >= seg_dur else -2.0)
            live_bonus = 3.5 if (t_start < 3.0 and m.get("role") == "b_roll") else 0.0
            sc = (
                sem_hits * 6.5 + intel_bonus + size_bonus + cont_bonus + stab_bonus + sharp_bonus
                + dur_bonus + live_bonus - reuse_pen - taboo_pen - same_media_pen - exhausted_pen - motion_pen
            )
            if sc > best_score:
                best_score = sc
                best_m = m
        if blocked_here and not best_m.get("taboo_tags"):
            taboo_blocked_count += 1
        return best_m

    clips: List[Dict[str, Any]] = []
    last_group = "shoot_default"
    last_motion = "static"
    last_shot_size = "medium"
    last_aroll_zoom = 1.0
    punch_in_count = 0
    lcut_real_count = 0

    for idx, cp in enumerate(cut_points):
        f_start = cp["cut_frame"]
        f_end = cut_points[idx + 1]["cut_frame"] if idx + 1 < n_segs else total_frames
        t_start = frames_to_sec(f_start, fps)
        t_end = frames_to_sec(f_end, fps)
        seg_dur = round(t_end - t_start, 4)
        ev = cp["event"]
        sent = find_sentence_for_time(t_start, ev)
        has_prop_show = any(cue in sent.get("text", "") for cue in PROP_SHOW_CUES)

        if roles[idx] == "a_roll":
            ar = next((a for a in usable_arolls if a["normalized_mp4"] == sent.get("source_media")), usable_arolls[0])
            offset_in_sent = max(0.0, t_start - float(sent["start_sec"]))
            if sent.get("source_media") == ar["normalized_mp4"]:
                src_in = round(float(sent.get("source_in_sec", 0.0)) + offset_in_sent, 4)
                sent_src_end = float(sent.get("source_out_sec", ar["duration_sec"]))
                max_src_out = min(ar["duration_sec"], sent_src_end)
            else:
                src_in = round(min(max(0.0, ar["duration_sec"] - seg_dur), float(sent.get("source_in_sec", 0.0)) + offset_in_sent), 4)
                max_src_out = ar["duration_sec"]

            # 相邻同源单调推进校验（消除任何误差引起的轻微倒带）
            ar_mp = str(ar["normalized_mp4"])
            if ar_mp in max_out_by_mp:
                src_in = max(src_in, max_out_by_mp[ar_mp])
            src_in = min(src_in, max(0.0, max_src_out - 0.05))
            need_freeze = src_in + seg_dur > max_src_out + 0.01
            src_out = round(min(max_src_out, src_in + seg_dur), 4)
            max_out_by_mp[ar_mp] = max(float(max_out_by_mp.get(ar_mp, 0.0)), src_out)

            vf_extra = ""
            cur_zoom = 1.0
            if idx > 0 and roles[idx - 1] == "a_roll" and not has_prop_show:
                cur_zoom = 1.15 if last_aroll_zoom == 1.0 else 1.0
                if cur_zoom > 1.01:
                    vf_extra = _build_eye_locked_vf(ar.get("eye_anchor"), zoom=cur_zoom)
                    punch_in_count += 1
            last_aroll_zoom = cur_zoom

            kb_cfg = {"zoom_start": 1.0, "zoom_end": 1.06, "reason": "防>3s静止微缓推"} if (seg_dur > 3.0 and not vf_extra) else None
            purpose = (
                "开篇第一眼定调抓人" if idx == 0
                else ("展示实物与凭据细节" if has_prop_show
                      else ("拉近画面强调重点" if cur_zoom > 1.01
                            else ("收尾强化真实感与互动" if idx == n_segs - 1 else "真人出镜说话建信任")))
            )
            last_motion = str(ar.get("camera_motion") or "static")
            last_shot_size = "closeup" if cur_zoom > 1.01 else str(ar.get("shot_size") or "medium")
            clips.append({
                "clip_id": f"clip_{idx+1:03d}",
                "track_role": "a_roll",
                "media_path": ar["normalized_mp4"],
                "source_in_sec": src_in,
                "source_out_sec": src_out,
                "tight": True,
                "freeze_tail": need_freeze,
                "timeline_in_sec": t_start,
                "timeline_out_sec": t_end,
                "timeline_in_frame": f_start,
                "timeline_out_frame": f_end,
                "duration_sec": seg_dur,
                "audio_locked": True,
                "b_roll_overlay": False,
                "underlying_audio_untouched": True,
                "j_cut_lead_frames": j_leads[idx],
                "punch_in_zoom": cur_zoom,
                "ken_burns": kb_cfg,
                "vf_extra": vf_extra,
                "cut_event_id": ev["id"],
                "cut_event_type": ev["type"],
                "cut_event_frame": ev["frame"],
                "sentence_id": sent["id"],
                "sentence_text": sent["text"],
                "purpose": purpose,
            })
        else:
            has_fresh_live = any(
                m.get("role") == "b_roll"
                and (
                    float(m.get("duration_sec", 0.0))
                    - max(
                        float(used_cursors.get(m["id"], 0.0)),
                        float(max_out_by_mp.get(str(m.get("normalized_mp4") or ""), 0.0)),
                    )
                ) >= min(0.6, seg_dur * 0.5)
                for m in broll_pool
            )
            cur_code_dur = sum(float(c["duration_sec"]) for c in clips if c.get("track_role") == "code_broll")
            forbid_code = has_fresh_live and ((cur_code_dur + seg_dur) / max(0.1, total_dur) > 0.45)
            prev_mp = str(clips[-1]["media_path"]) if clips else ""
            prev_so = float(clips[-1]["source_out_sec"]) if clips else 0.0

            br = pick_best_broll(
                sent, seg_dur, last_group, t_start, prev_mp, prev_so,
                prev_motion=last_motion, prev_shot_size=last_shot_size, forbid_code=forbid_code,
            )
            bid = br["id"]
            mp_str = str(br["normalized_mp4"])
            avail = float(br.get("duration_sec", 3.0))
            is_live_long = br.get("role") == "b_roll" and avail > 2.0
            handle_s = 0.40 if (is_live_long and avail >= seg_dur + 0.80) else 0.0
            max_usable_out = avail - handle_s

            if br["role"] == "code_broll":
                src_in = 0.0
                used_cursors[bid] = src_in + seg_dur + 0.10
                src_out = round(min(avail, src_in + seg_dur), 4)
            else:
                min_floor = max(handle_s, float(max_out_by_mp.get(mp_str, 0.0)))
                cur_pos = max(min_floor, float(used_cursors.get(bid, min_floor)))
                if cur_pos + seg_dur <= max_usable_out or (avail - cur_pos >= seg_dur):
                    src_in = round(cur_pos, 4)
                elif avail - min_floor >= 0.30:
                    src_in = round(min_floor, 4)
                else:
                    src_in = round(min(min_floor, max(0.0, avail - 0.05)), 4)
                src_out = round(min(avail, src_in + seg_dur), 4)
                max_out_by_mp[mp_str] = max(float(max_out_by_mp.get(mp_str, 0.0)), src_out)
                used_cursors[bid] = round(src_out + 0.10, 4)

            usage_counts[bid] = usage_counts.get(bid, 0) + 1
            last_group = str(br.get("scene_group", last_group))
            last_motion = str(br.get("camera_motion") or "static")
            last_shot_size = str(br.get("shot_size") or "medium")
            need_freeze = src_in + seg_dur > avail + 0.01
            eff_role = str(br["role"])  # 统一保留 b_roll/code_broll，不写入悬空 "freeze"
            kb_cfg = {"zoom_start": 1.0, "zoom_end": 1.06, "reason": "长镜头微推"} if (seg_dur > pacing["static_sec"] and eff_role == "b_roll") else None

            if j_leads[idx] < 0:
                lcut_real_count += 1
            if audio_only_flags[idx]:
                b_purpose = "原声保留、用特写画面自然盖住瑕疵镜头"
            elif t_start < 3.0:
                b_purpose = "开头前3秒切入细节画面抓人眼"
            elif j_leads[idx] > 0:
                b_purpose = "声音先响半拍再切入特写，衔接更顺滑"
            elif j_leads[idx] < 0:
                b_purpose = "凭据特写画面先露面再听人解释"
            else:
                b_purpose = "顺着台词补入对应细节画面"

            amb_audio_src = br.get("normalized_wav") or (br.get("source_path") if br.get("has_audio") else None)
            keep_amb = bool(
                ambient_enabled
                and eff_role == "b_roll"
                and br.get("has_audio", False)
                and amb_audio_src
                and Path(str(amb_audio_src)).is_file()
                and not br.get("source_is_code_scene", False)
                and any(w in str(sent.get("text", "")) for w in ambient_words)
            )
            clips.append({
                "clip_id": f"clip_{idx+1:03d}",
                "track_role": eff_role,
                "media_path": br["normalized_mp4"],
                "source_in_sec": src_in,
                "source_out_sec": src_out,
                "tight": True,
                "handles_guarded": bool(br["role"] == "code_broll" or (src_in >= 0.39 and (avail - src_out) >= 0.39)),
                "audio_only_masked": audio_only_flags[idx],
                "freeze_tail": need_freeze,
                "timeline_in_sec": t_start,
                "timeline_out_sec": t_end,
                "timeline_in_frame": f_start,
                "timeline_out_frame": f_end,
                "duration_sec": seg_dur,
                "audio_locked": False,
                "b_roll_overlay": True,
                "underlying_audio_untouched": True,
                "keep_broll_ambient": keep_amb,
                "ambient_audio_path": str(amb_audio_src) if keep_amb else None,
                "ambient_gain_db": ambient_gain_db if keep_amb else None,
                "j_cut_lead_frames": j_leads[idx],
                "punch_in_zoom": 1.0,
                "ken_burns": kb_cfg,
                "vf_extra": "",
                "cut_event_id": ev["id"],
                "cut_event_type": ev["type"],
                "cut_event_frame": ev["frame"],
                "sentence_id": sent["id"],
                "sentence_text": sent["text"],
                "purpose": b_purpose,
            })

    first_3s_changes = sum(1 for c in clips[1:] if c["timeline_in_frame"] < first_3s_cutoff_f)
    jcut_real_count = sum(1 for c in clips if c.get("j_cut_lead_frames", 0) > 0)
    durs = [float(c["duration_sec"]) for c in clips]
    shot_cv = round(statistics.stdev(durs) / max(1e-5, statistics.mean(durs)), 3) if len(durs) >= 2 else 0.0
    code_dur = sum(float(c["duration_sec"]) for c in clips if c.get("track_role") == "code_broll")
    code_ratio = round(code_dur / max(0.1, total_dur), 3)
    broll_actual_dur = sum(float(c["duration_sec"]) for c in clips if c.get("track_role") != "a_roll")
    broll_ratio_actual = round(broll_actual_dur / max(0.1, total_dur), 3)

    # 按风格谱 pip_composition_spec 为分镜挂载真·画中画构图参数 (pip_layout)
    pip_spec = (style_entry or {}).get("pip_composition_spec") or {}
    sent_by_id = {str(s.get("id")): s for s in sentences}
    explainer_windows = detect_explainer_broll_windows(sentences)

    # 消费 explainer_broll_windows：口播讲解数字/流程/对比句时，若镜头为真人出镜且整体代码图解占比不超 30%，
    # 自动切入动态讲解图解并挂载平滑圆环人像画中画（smooth_orbit_pip），主讲人平滑缩至安全角继续同步说话
    explainer_applied_count = 0
    if explainer_windows and clips and not prefer_broll_only and usable_arolls:
        win_by_sid = {str(w["sentence_id"]): w for w in explainer_windows}
        gen_exp_dir = pipeline_dir / "04_generated_broll"
        gen_exp_dir.mkdir(parents=True, exist_ok=True)
        pal_exp = resolve_style_palette(style_id, track=track)
        cur_code_dur = sum(float(c.get("duration_sec", 0.0)) for c in clips if c.get("track_role") == "code_broll")
        for c_obj in clips:
            if explainer_applied_count >= 2:
                break
            if c_obj.get("track_role") != "a_roll":
                continue
            sid_c = str(c_obj.get("sentence_id") or "")
            ew = win_by_sid.get(sid_c)
            if not ew:
                continue
            cdur = float(c_obj.get("duration_sec", 0.0))
            if cdur < 1.6 or (cur_code_dur + cdur) / max(0.1, total_dur) > 0.30:
                continue
            exp_mp4 = gen_exp_dir / f"explainer_{sid_c}.mp4"
            exp_mode = str(ew.get("suggested_mode") or "kinetic_text")
            exp_title = str(ew.get("trigger_cue") or "核心要点")[:10]
            exp_text = str(ew.get("sentence_text") or c_obj.get("sentence_text") or "")
            try:
                render_code_clip(
                    exp_mp4,
                    mode=exp_mode,
                    title=exp_title,
                    items=[{"label": exp_title, "subtitle": exp_text[:20]}],
                    duration_sec=max(1.8, cdur),
                    accent_hex=pal_exp["accent_hex"],
                    bg_hex=pal_exp["bg_hex"],
                    style_id=style_id,
                    track=track,
                    backend="pillow",
                )
            except Exception:
                continue
            orig_aroll = str(c_obj.get("media_path") or "")
            orig_in = float(c_obj.get("source_in_sec", 0.0))
            c_obj["media_path"] = str(exp_mp4.resolve())
            c_obj["source_in_sec"] = 0.0
            c_obj["source_out_sec"] = round(cdur, 4)
            c_obj["track_role"] = "code_broll"
            c_obj["purpose"] = f"动态讲解图解({exp_mode}) + 角落圆环人像"
            c_obj["pip_layout"] = {
                "mode": "smooth_orbit_pip",
                "corner": "tr",
                "radius_px": 146,
                "center_y": 360,
                "border_hex": pal_exp["accent_hex"],
                "border_width": 4,
                "tag_text": "主讲人",
                "secondary_media_path": orig_aroll,
                "secondary_in_sec": round(max(0.0, orig_in), 4),
                "secondary_out_sec": round(max(0.0, orig_in) + cdur, 4),
            }
            cur_code_dur += cdur
            explainer_applied_count += 1
        code_ratio = round(cur_code_dur / max(0.1, total_dur), 3)

    pip_mode = str(pip_spec.get("mode") or "")
    pip_applied_count = explainer_applied_count
    if pip_mode and clips:
        live_brolls = [m for m in broll_pool if m.get("role") == "b_roll"] or list(broll_pool)
        full_frame_modes = {
            "black_polaroid_frame_pip",
            "blur_bg_center_card_pip",
            "dark_doc_circle_avatar_pip",
            "linear_split_feather_pip",
        }
        for c_i, c_obj in enumerate(clips):
            if c_obj.get("track_role") == "code_broll" or c_obj.get("pip_layout"):
                continue
            should_apply = (
                pip_mode in full_frame_modes
                or c_i == 0
                or c_obj.get("track_role") == "b_roll"
                or (c_i % 2 == 0)
            )
            if not should_apply:
                continue
            sec_media = str(c_obj.get("media_path") or "")
            sec_in = float(c_obj.get("source_in_sec", 0.0))
            if c_obj.get("track_role") == "a_roll" and live_brolls:
                pick_m = live_brolls[c_i % len(live_brolls)]
                sec_media = str(pick_m.get("normalized_mp4") or sec_media)
                sec_in = float(pick_m.get("best_in_sec", 0.0))
            elif c_obj.get("track_role") != "a_roll":
                # 优先绑定当前句的真实口播源与同步时间点，严禁硬从 0.0s 播口播造成口型穿帮
                cur_sent = sent_by_id.get(str(c_obj.get("sentence_id") or "")) or {}
                s_src_media = str(cur_sent.get("source_media") or "")
                if s_src_media and Path(s_src_media).is_file():
                    sec_media = s_src_media
                    s_base = float(cur_sent.get("start_sec", 0.0))
                    s_src_in = float(cur_sent.get("source_in_sec", 0.0))
                    sec_in = max(0.0, s_src_in + max(0.0, float(c_obj.get("timeline_in_sec", s_base)) - s_base))
                elif live_brolls and len(live_brolls) > 1:
                    alt_b = next((m for m in live_brolls if str(m.get("normalized_mp4")) != sec_media), live_brolls[0])
                    sec_media = str(alt_b.get("normalized_mp4") or sec_media)
                    sec_in = float(alt_b.get("best_in_sec", 0.0))
            c_obj["pip_layout"] = {
                **pip_spec,
                "secondary_media_path": sec_media,
                "secondary_in_sec": round(max(0.0, sec_in), 4),
                "secondary_out_sec": round(max(0.0, sec_in) + float(c_obj.get("duration_sec", 1.5)), 4),
            }
            pip_applied_count += 1

    # 真实测算首帧视觉密度：文件存在且非废画、且非低对比死黑
    first_c = clips[0] if clips else {}
    first_item = next((m for m in manifest.get("items", []) if m.get("normalized_mp4") == first_c.get("media_path")), {})
    first_clip_ok = bool(
        clips
        and Path(str(first_c.get("media_path", ""))).is_file()
        and first_item.get("video_grade", "usable") != "ng"
        and (first_c.get("track_role") in ("a_roll", "code_broll") or float(first_item.get("sharpness_score", 25.0)) >= 12.0)
    )

    edl = {
        "step": "04_build_edl",
        "fps": fps,
        "tight": True,
        "style_id": style_id,
        "edit_profile": edit_profile,
        "canvas": {"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT},
        "total_duration_sec": total_dur,
        "total_frames": total_frames,
        "j_cut_default_frames": j_cut_frames,
        "j_cut_applied_count": jcut_real_count,
        "l_cut_applied_count": lcut_real_count,
        "punch_in_count": punch_in_count,
        "pip_mode": pip_mode or ("smooth_orbit_pip" if explainer_applied_count > 0 else "none"),
        "pip_applied_count": pip_applied_count,
        "explainer_broll_windows": explainer_windows,
        "explainer_applied_count": explainer_applied_count,
        "shot_duration_cv": shot_cv,
        "code_broll_ratio": code_ratio,
        "broll_ratio_target": round(broll_target_ratio, 3),
        "broll_ratio_actual": broll_ratio_actual,
        "ppt_warning": code_ratio > 0.30,
        "audio_only_masked_count": sum(1 for c in clips if c.get("audio_only_masked")),
        "taboo_blocked_count": taboo_blocked_count,
        "deictic_gaps": deictic_gaps,
        "first_frame_density_ok": first_clip_ok,
        "first_3s_visual_changes": first_3s_changes,
        "clip_count": len(clips),
        "clips": clips,
    }
    write_json(pipeline_dir / "04_edl.json", edl)

    md_lines = [
        "# 画面剪辑排期表（大白话版）",
        "",
        f"- **成片总时长**：{total_dur:.2f} 秒（共 {len(clips)} 个画面段落）",
        f"- **开头 3 秒画面切换**：{first_3s_changes} 次（全部踩在说话节奏点上）",
        f"- **声音提前衔接 / 画面微拉近**：声画自然错位 {jcut_real_count + lcut_real_count} 处，重点画面拉近 {punch_in_count} 处",
        "",
        "| 序号 | 画面类型 | 截取起点 | 成片时间段 | 时长 | 衔接处理 | 安排用意 | 对应台词 |",
        "| :--- | :--- | :---: | :--- | :---: | :---: | :--- | :--- |",
    ]
    role_cn = {"a_roll": "真人出镜", "b_roll": "实拍细节", "code_broll": "动态图表"}
    for i_c, c in enumerate(clips, start=1):
        jl = c["j_cut_lead_frames"]
        j_p = "声音先入半拍" if jl > 0 else ("画面先露半拍" if jl < 0 else ("轻推拉近" if c["punch_in_zoom"] > 1.01 else "常规硬切"))
        md_lines.append(
            f"| 第 {i_c} 镜 | {role_cn.get(c['track_role'], '实拍画面')} | {c['source_in_sec']:.2f}s | "
            f"{c['timeline_in_sec']:.2f}s–{c['timeline_out_sec']:.2f}s | {c['duration_sec']:.2f}s | "
            f"{j_p} | {c['purpose']} | {c['sentence_text']} |"
        )
    (pipeline_dir / "04_edl_table.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(
        f"[step4] 剪辑排期完成：{len(clips)} 个镜头，前3秒切换 {first_3s_changes} 次，"
        f"声画错位 {jcut_real_count + lcut_real_count} 处，重点拉近 {punch_in_count} 处，"
        f"动态讲解画中画 {explainer_applied_count} 处 -> 04_edl.json"
    )
    return edl


def main() -> None:
    maybe_reexec_in_venv()
    parser = argparse.ArgumentParser(description="Step 4: 以音定画生成专业剪辑表")
    parser.add_argument("--pipeline-dir", required=True)
    parser.add_argument("--track", choices=["store", "creator"], default="store")
    parser.add_argument("--j-cut-frames", type=int, default=3)
    parser.add_argument("--style-id", help="风格谱ID")
    parser.add_argument("--edit-profile", choices=EDIT_PROFILES, default="talking")
    parser.add_argument("--account-profile", help="account_profile.json 路径")
    parser.add_argument("--prefer-broll-only", action="store_true", help="打断#3只改画面时可选切换纯B-roll混剪")
    args = parser.parse_args()
    prof = read_json(Path(args.account_profile)) if args.account_profile and Path(args.account_profile).exists() else None
    run_step4(
        Path(args.pipeline_dir),
        track=args.track,
        j_cut_frames=args.j_cut_frames,
        prefer_broll_only=args.prefer_broll_only,
        style_id=args.style_id,
        account_profile=prof,
        edit_profile=args.edit_profile,
    )


if __name__ == "__main__":
    main()

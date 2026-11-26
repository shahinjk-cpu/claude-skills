#!/usr/bin/env python3
"""
[商业发布合规守卫与商用授权 SHA-256 清单]
1. 广告法 / 平台规则双级拦截：
   - must 级：极限词、绝对承诺、非医疗功效、国家机关背书（白名单精确排除「最近/最后/最怕/第一口」零误杀）
   - warn 级：纯天然、零添加、原厂、祖传、站外导流暗语（支持账号白名单 compliance_whitelist.json 凭证核销 ack）
   - 真人口播原声前置标记：实拍原声命中 must 时标 action="drop_sentence_or_reshoot"，整句弃用并留痕，绝不掩耳盗铃改字幕
2. 渲染副产物带 SHA-256 商用授权清单：
   - 扫描真实使用的 BGM / SFX / 字体 / LUT，逐文件算 sha256 与授权分类
   - 发现未登记第三方外置资产则 passed=False 拦停，输出 asset_license_manifest.json
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from common import ASSETS_DIR, is_verified_commercial_font, read_json, sha256_file, write_json

EXEMPT_PHRASES = (
    "最近", "最后", "最怕", "最常", "最早", "最晚", "最初", "起初", "一开始",
    "最起码", "至少", "最终", "最终版", "最多也就是", "最开始", "最关键在于",
    "第一次", "第一天", "第一口", "第一步", "第一眼", "第一段", "第一个", "第一批",
    "第一声", "第一版", "第一轮", "第一时间", "第1次", "第1天", "第1口", "第1步",
    "最高气温", "最低消费", "最大限度", "绝大部分", "绝对值", "最底层原理",
)

MUST_RULES: List[Tuple[str, str, str, str]] = [
    (
        "极限用语",
        r"全网第[一1]|行业第[一1]|全国第[一1]|全城第[一1]|销量第[一1]|口碑第[一1]|第[一1]品牌|唯一指定|全网独家|销量遥遥领先|全行业最强",
        "业内口碑靠前",
        "涉嫌《广告法》第九条“第一/唯一/遥遥领先”绝对化排行宣称",
    ),
    (
        "极限用语",
        r"最(?:好吃|好用|好喝|佳|强|大|高|低|牛|顶|便宜|正宗|有效|靠谱|专业|权威|划算|实惠|高级|好)",
        "很受顾客认可",
        "涉嫌《广告法》第九条“最……”绝对化用语（已排除“最近/最后/最怕”等日常词）",
    ),
    (
        "极限用语",
        r"顶级|极品|绝品|天花板级|殿堂级|史无前例|前无古人|国家级|世界级|绝无仅有",
        "高标准制作",
        "涉嫌绝对化/国家级最高级用语风险",
    ),
    (
        "百分百绝对承诺",
        r"100%好评|100%|百分之百|百分百|零风险|0风险|零副作用|无任何副作用|绝对(?:有效|安全|正品|不踩坑|好吃)|稳赚不赔|包赚|必赚|躺赚|永久有效|绝不反弹",
        "尽量把控品质、减少踩坑",
        "涉嫌绝对承诺与效果/收益担保风险",
    ),
    (
        "医疗功效违规",
        r"包治百病|包治|根治|药到病除|立竿见影|防癌|抗癌|降三高|消炎杀菌|纯中药秘方|包瘦|包白|一个月瘦\d+斤",
        "日常搭配更安心",
        "普通食品/服务严禁涉医疗治疗或承诺减肥美白功效宣称",
    ),
    (
        "机关背书违规",
        r"国家指定|政府推荐|央视认证|官方指定|军工品质|人民大会堂特供|国宴特供",
        "行业规范标准",
        "严禁冒用国家机关/权威机构名义背书",
    ),
]

WARN_RULES: List[Tuple[str, str, str, str]] = [
    (
        "资质凭证提示",
        r"纯天然|零添加|0添加|无任何添加|原厂原装|祖传秘方|百年老字号|非遗传承",
        "坚持手工现做、少用繁杂调料",
        "需备齐检测报告/品牌授权/老字号证书等凭证方可口播（whitelist ack 后放行）",
    ),
    (
        "站外导流暗语与谐音",
        r"加[Vv微]|威信|[Vv]信|微[♥❤➕+]|私信发微信|私聊[领发加]|微信号|(?<![a-z0-9])vx[:：\s]?|扫码进群|扫[一 ]?码[领加]|加群领|二维码找我|主页领优惠券|扣我\d*",
        "评论区扣 1 或主页看门店详情",
        "平台高风险站外导流及谐音暗语触发限流预警",
    ),
]


def _mask_exempt_phrases(text: str) -> str:
    """将白名单日常词替换为等长占位符，保证正则匹配偏移量与原文严格一致。"""
    masked = text
    for phrase in sorted(EXEMPT_PHRASES, key=len, reverse=True):
        if phrase in masked:
            masked = masked.replace(phrase, "\u0000" * len(phrase))
    return masked


def _load_whitelist_terms(whitelist_path: Optional[Path]) -> set[str]:
    if not whitelist_path or not whitelist_path.is_file():
        return set()
    try:
        raw = read_json(whitelist_path)
        if isinstance(raw, dict):
            return {str(x).strip() for x in raw.get("acked_terms", []) if str(x).strip()}
        if isinstance(raw, list):
            return {str(x).strip() for x in raw if str(x).strip()}
    except Exception:
        pass
    return set()


def audit_text_line(
    text: str,
    acked_terms: Optional[set[str]] = None,
) -> Dict[str, Any]:
    """扫描单句文案/转写，返回 must/warn 命中详情与温和改写文本。"""
    masked = _mask_exempt_phrases(text)
    acked = acked_terms or set()
    hits: List[Dict[str, Any]] = []
    must_spans: List[Tuple[int, int, str]] = []
    masked_chars = list(masked)

    for cat, pat, repl, reason in MUST_RULES:
        for m in re.finditer(pat, "".join(masked_chars), flags=re.IGNORECASE):
            term = text[m.start() : m.end()]
            hits.append({
                "severity": "must",
                "category": cat,
                "matched_term": term,
                "start_char": m.start(),
                "end_char": m.end(),
                "context": text[max(0, m.start() - 22): m.end() + 22],
                "reason": reason,
                "suggestion": repl,
                "acked": False,
            })
            must_spans.append((m.start(), m.end(), repl))
            for k in range(m.start(), m.end()):
                masked_chars[k] = " "

    # 按命中偏移逆序切片替换，绝不误改前面豁免短语；并基于屏蔽掉 must 后的文本检查 warn
    rewritten = text
    for st, en, repl in sorted(must_spans, key=lambda x: x[0], reverse=True):
        rewritten = rewritten[:st] + repl + rewritten[en:]

    masked_for_warn = "".join(masked_chars)
    for cat, pat, repl, reason in WARN_RULES:
        for m in re.finditer(pat, masked_for_warn, flags=re.IGNORECASE):
            term = text[m.start() : m.end()]
            is_acked = term in acked
            hits.append({
                "severity": "warn",
                "category": cat,
                "matched_term": term,
                "start_char": m.start(),
                "end_char": m.end(),
                "context": text[max(0, m.start() - 22): m.end() + 22],
                "reason": reason,
                "suggestion": repl,
                "acked": is_acked,
            })

    return {
        "has_must": any(h["severity"] == "must" for h in hits),
        "has_unacked_warn": any(h["severity"] == "warn" and not h["acked"] for h in hits),
        "hits": hits,
        "suggested_text": rewritten if must_spans else text,
    }


def audit_script_compliance(
    sentences: List[Dict[str, Any]],
    source_type: str = "script",
    pipeline_dir: Optional[Path] = None,
    whitelist_path: Optional[Path] = None,
    auto_action: bool = True,
) -> Dict[str, Any]:
    """
    对口播/转写句列表执行合规审校：
    - 真人口播原声 (real_voice / asr / asr_whisper) 命中 must -> action="drop_sentence_or_reshoot"
    - 文本/配音脚本命中 must -> action="auto_rewrite_or_block"
    """
    is_real_voice = str(source_type) in (
        "real_voice",
        "asr",
        "asr_whisper",
        "asr_script_forced",
        "asr_char_mapped",
        "vad_energy_aligned",
        "multi_aroll_mixed",
    )
    acked = _load_whitelist_terms(whitelist_path)

    findings: List[Dict[str, Any]] = []
    must_count = 0
    warn_count = 0
    unacked_warn_count = 0
    dropped_sentence_ids: List[str] = []
    rewritten_count = 0

    for idx, seg in enumerate(sentences, start=1):
        if seg.get("is_filler"):
            continue
        sid = str(seg.get("id") or f"seg_{idx:03d}")
        txt = str(seg.get("text") or "").strip()
        if not txt:
            continue
        res = audit_text_line(txt, acked_terms=acked)
        if not res["hits"]:
            continue

        if res["has_must"]:
            must_count += 1
            action = "drop_sentence_or_reshoot" if is_real_voice else "auto_rewrite_or_block"
            if auto_action:
                if is_real_voice:
                    seg["is_filler"] = True
                    seg["emotion"] = "filler"
                    seg["drop_reason"] = "compliance_must_violation"
                    dropped_sentence_ids.append(sid)
                else:
                    seg["original_text_before_compliance"] = txt
                    seg["text"] = res["suggested_text"]
                    rewritten_count += 1
        else:
            action = "warn_acked" if not res["has_unacked_warn"] else "warn_need_proof_ack"

        for h in res["hits"]:
            if h["severity"] == "warn":
                warn_count += 1
                if not h["acked"]:
                    unacked_warn_count += 1

        findings.append({
            "sentence_id": sid,
            "source_type": source_type,
            "original_text": txt,
            "source_media": seg.get("source_media"),
            "start_sec": seg.get("start_sec"),
            "end_sec": seg.get("end_sec"),
            "suggested_text": res["suggested_text"],
            "action": action,
            "hits": res["hits"],
            "resolved": True if (auto_action and res["has_must"]) else (not res["has_must"]),
        })

    unresolved_must = sum(1 for f in findings if any(h["severity"] == "must" for h in f["hits"]) and not f["resolved"])
    active_non_filler = sum(1 for s in sentences if not s.get("is_filler"))
    total_checked = active_non_filler + len(dropped_sentence_ids)
    real_voice_collapse = is_real_voice and total_checked > 0 and (
        active_non_filler == 0 or (len(dropped_sentence_ids) / float(total_checked) > 0.40)
    )
    passed = (unresolved_must == 0) and (not real_voice_collapse)
    report = {
        "step": "00_compliance_guard",
        "source_type": source_type,
        "is_real_voice": is_real_voice,
        "real_voice_total": total_checked if is_real_voice else 0,
        "passed": passed,
        "real_voice_collapse_blocked": real_voice_collapse,
        "must_sentence_count": must_count,
        "unresolved_must_count": unresolved_must,
        "warn_hit_count": warn_count,
        "unacked_warn_count": unacked_warn_count,
        "dropped_real_voice_ids": dropped_sentence_ids,
        "auto_rewritten_count": rewritten_count,
        "whitelist_path": str(whitelist_path.resolve()) if whitelist_path and whitelist_path.is_file() else None,
        "findings": findings,
    }

    if pipeline_dir is not None:
        write_compliance_report_files(pipeline_dir, report)

    return report


def write_compliance_report_files(pipeline_dir: Path, report: Dict[str, Any]) -> None:
    """统一写入 00_compliance_report.json 与 00_compliance_report.md，防止 JSON 与 MD 脱节。"""
    findings = list(report.get("findings") or [])
    is_real_voice = bool(report.get("is_real_voice"))
    passed = bool(report.get("passed"))
    must_count = int(report.get("must_sentence_count", 0))
    warn_count = int(report.get("warn_hit_count", 0))
    unacked_warn_count = int(report.get("unacked_warn_count", 0))
    write_json(pipeline_dir / "00_compliance_report.json", report)
    md_lines = [
        "# 广告法与平台合规审校报告",
        "",
        f"- **音源性质**：{'实拍真人口播（违规原声只能整句弃用或重拍，严禁靠改字幕遮掩）' if is_real_voice else '文本/配音脚本'}",
        f"- **判定结论**：{'✅ 合规通过' if passed else '❌ 存在未处置的禁止红线表达'}（禁止红线={must_count} 句，需凭证提醒={warn_count} 处，待补充凭证={unacked_warn_count} 处）",
        "",
    ]
    if findings:
        md_lines += [
            "| 句子 | 级别 | 命中词 | 原话 | 改写/处置建议 | 触发原因 |",
            "| :--- | :---: | :--- | :--- | :--- | :--- |",
        ]
        for f in findings:
            sev = "禁止红线" if any(h["severity"] == "must" for h in f["hits"]) else "需凭证提醒"
            terms = "、".join(h["matched_term"] for h in f["hits"])
            reasons = "；".join(h["reason"] for h in f["hits"])
            act = f"【已弃用原声句】建议重拍：{f['suggested_text']}" if f["action"] == "drop_sentence_or_reshoot" else f["suggested_text"]
            md_lines.append(f"| `{f['sentence_id']}` | {sev} | `{terms}` | {f['original_text']} | {act} | {reasons} |")
    else:
        md_lines.append("- 全文未检出违禁或高风险表达。")
    (pipeline_dir / "00_compliance_report.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")


def _classify_asset_license(path: Path, asset_kind: str, pipeline_dir: Path,
                            reg_map: Dict[str, Any], asset_hash: str) -> Dict[str, Any]:
    if asset_hash in reg_map:
        info = reg_map[asset_hash]
        return {
            "source_tier": "external_registered",
            "license": str(info["license"]),
            "commercial_ok": bool(info["commercial_ok"]),
            "authorization_path": info["authorization_path"],
            "authorization_sha256": info["authorization_sha256"],
        }

    resolved = path.resolve()
    if ASSETS_DIR.resolve() in resolved.parents:
        return {"source_tier": "builtin_svs", "license": "见 assets-attribution.md", "commercial_ok": True}
    if asset_kind == "font" and is_verified_commercial_font(str(resolved)):
        return {
            "source_tier": "verified_commercial_font",
            "license": "已核验免费可商用开源字体 (OFL / Apache-2.0)",
            "commercial_ok": True,
            "commercial_verified": True,
        }
    generated_roots = (
        pipeline_dir.resolve() / "04_generated_broll",
        pipeline_dir.resolve() / "01_normalized",
        pipeline_dir.resolve() / "01_code_scenes",
        pipeline_dir.resolve() / "06_custom_graphics",
        pipeline_dir.resolve(),
        pipeline_dir.resolve().parent / "animation" / "work",
    )
    if asset_kind in ("code_broll", "graphic", "sticker", "sfx") and any(
        root == resolved.parent or root in resolved.parents for root in generated_roots
    ):
        return {"source_tier": "project_generated", "license": "项目程序化生成内容", "commercial_ok": True}
    return {"source_tier": "unregistered_external", "license": "未关联授权原件", "commercial_ok": False}


def build_asset_license_manifest(
    pipeline_dir: Path,
    out_dir: Optional[Path] = None,
    licenses_path: Optional[Path] = None,
) -> Dict[str, Any]:
    reg_map: Dict[str, Any] = {}
    cand_lic = licenses_path or (pipeline_dir.parent / "licenses.json")
    if cand_lic.is_file():
        raw = read_json(cand_lic)
        for item in (raw.get("assets", []) if isinstance(raw, dict) else raw):
            if not isinstance(item, dict) or not item.get("license") or not item.get("authorization_path"):
                continue
            asset_hash = str(item.get("sha256") or "").lower()
            document = (cand_lic.resolve().parent / item["authorization_path"]).resolve()
            if not re.fullmatch(r"[a-f0-9]{64}", asset_hash) or not document.is_file():
                continue
            document_hash = sha256_file(document)
            if item.get("authorization_sha256") and item["authorization_sha256"].lower() != document_hash:
                continue
            reg_map[asset_hash] = {**item, "commercial_ok": item.get("commercial_ok") is True,
                                   "authorization_path": str(document), "authorization_sha256": document_hash}

    raw_assets: List[Tuple[str, Path]] = []
    ae_p = pipeline_dir / "03_audio_events.json"
    if ae_p.is_file():
        ae = read_json(ae_p)
        bgm_f = (ae.get("bgm") or {}).get("file")
        if bgm_f:
            raw_assets.append(("bgm", Path(bgm_f)))

    sub_p = pipeline_dir / "05_subtitles.json"
    if sub_p.is_file():
        sub = read_json(sub_p)
        if sub.get("font_path"):
            raw_assets.append(("font", Path(sub["font_path"])))

    pkg_p = pipeline_dir / "06_packaging.json"
    if pkg_p.is_file():
        pkg = read_json(pkg_p)
        for sfx in pkg.get("sfx_cues", []):
            if sfx.get("file"):
                raw_assets.append(("sfx", Path(sfx["file"])))
        for elem in pkg.get("visual_elements", []):
            cp = elem.get("custom_png")
            if cp:
                raw_assets.append(("graphic", Path(cp)))
            ta = str(elem.get("text_or_asset") or "")
            if ta.endswith((".svg", ".png")) and Path(ta).exists():
                raw_assets.append(("sticker", Path(ta)))

    col_p = pipeline_dir / "07_color_plan.json"
    if col_p.is_file():
        col = read_json(col_p)
        if col.get("source_lut_path") or col.get("lut_path"):
            raw_assets.append(("lut", Path(col.get("source_lut_path") or col["lut_path"])))

    edl_p = pipeline_dir / "04_edl.json"
    if edl_p.is_file():
        for clip in (read_json(edl_p).get("clips") or []):
            if clip.get("track_role") == "code_broll" and clip.get("media_path"):
                raw_assets.append(("code_broll", Path(clip["media_path"])))

    code_spec = pipeline_dir / "00_code_spec.json"
    if code_spec.is_file():
        for asset in read_json(code_spec).get("assets", []):
            if asset.get("path"):
                raw_assets.append(("code_input", Path(asset["path"])))

    # 扫描知识讲解动画的音频与字体资产（确保 knowledge-animation 模式也有完整授权清单）
    anim_stage_fonts = pipeline_dir.parent / "animation" / "stage" / "fonts"
    if anim_stage_fonts.is_dir():
        for fp in sorted(anim_stage_fonts.iterdir()):
            if fp.is_file() and fp.suffix.lower() in (".otf", ".ttf", ".woff2"):
                raw_assets.append(("font", fp))
    anim_aud_p = pipeline_dir / "10_animation_audit.json"
    if anim_aud_p.is_file():
        try:
            aa = read_json(anim_aud_p)
            bgm_used = (aa.get("audio_mix") or {}).get("bgm_file")
            if bgm_used and Path(bgm_used).is_file():
                raw_assets.append(("bgm", Path(bgm_used)))
            sfx_used = (aa.get("audio_mix") or {}).get("sfx_wav")
            if sfx_used and Path(sfx_used).is_file():
                raw_assets.append(("sfx", Path(sfx_used)))
        except Exception:
            pass

    # 扫描 02_transcript.json 是否使用了合成语音配音并区分 Edge TTS 与系统朗读
    tts_commercial_notice: Optional[str] = None
    tr_p = pipeline_dir / "02_transcript.json"
    if tr_p.is_file():
        try:
            tr = read_json(tr_p)
            src_t = str(tr.get("source_type") or "")
            tts_prov = str(tr.get("tts_provider") or tr.get("tts_engine") or "").lower()
            if tr.get("uses_synthetic_voice", src_t == "tts") or "edge" in tts_prov or "say" in tts_prov:
                if "say" in tts_prov or "macos" in tts_prov:
                    tts_commercial_notice = (
                        "检测到当前成片音频由本机系统朗读 (macOS say) 兜底合成："
                        "正式发布前建议替换为真人实拍配音或商用授权配音。"
                    )
                else:
                    tts_commercial_notice = (
                        "检测到当前成片音频由在线语音合成 (Edge TTS) 生成：仅适合演示/测试与非直接商业转售，"
                        "正式商业投放或广告购买前建议替换为真人实拍配音或采购商业 TTS 授权。"
                    )
        except Exception:
            pass

    dedup: Dict[str, Tuple[str, Path]] = {}
    for kind, p in raw_assets:
        rp = str(p.resolve()) if p.exists() else str(p)
        if rp not in dedup:
            dedup[rp] = (kind, p)

    entries: List[Dict[str, Any]] = []
    unregistered: List[str] = []
    unverified_fonts: List[str] = []
    for rp, (kind, p) in sorted(dedup.items()):
        exists = p.is_file()
        sha = sha256_file(p) if exists else ""
        sz = p.stat().st_size if exists else 0
        cls = _classify_asset_license(p, kind, pipeline_dir, reg_map, sha)
        if kind == "font" and not cls.get("commercial_ok"):
            unverified_fonts.append(p.name)
        if not exists or not cls["commercial_ok"]:
            unregistered.append(f"{kind}:{p.name} ({cls['source_tier']})")
        entries.append({
            "kind": kind,
            "category": kind,
            "filename": p.name,
            "name": p.name,
            "path": rp,
            "exists": exists,
            "size_bytes": sz,
            "sha256": sha,
            "commercial_verified": bool(cls.get("commercial_verified", cls.get("commercial_ok", False))),
            **cls,
        })

    if col_p.is_file() and col.get("source_lut_path") and col.get("lut_path") != col["source_lut_path"]:
        derived = Path(col["lut_path"])
        master = Path(col["source_lut_path"]).resolve()
        source_entry = next((item for item in entries if item["path"] == str(master)), None)
        if derived.is_file() and source_entry and source_entry.get("commercial_ok"):
            entries.append({
                "kind": "lut", "category": "lut",
                "filename": derived.name, "name": derived.name,
                "exists": True, "size_bytes": derived.stat().st_size,
                "path": str(derived.resolve()), "sha256": sha256_file(derived),
                "source_tier": "project_derived_lut", "source_path": str(master),
                "source_sha256": source_entry["sha256"],
                "license": str(source_entry.get("license") or "CC0 1.0 (Derived)"),
                "commercial_ok": True,
                "commercial_verified": True,
            })
        else:
            unregistered.append(f"lut:{derived.name} 缺少可核对的底表授权或派生文件")

    all_ok = (len(unregistered) == 0 and len(unverified_fonts) == 0 and len(entries) > 0)
    warnings: List[str] = [tts_commercial_notice] if tts_commercial_notice else []
    manifest = {
        "step": "asset_license_manifest",
        "passed": all_ok,
        "all_commercial_verified": all_ok,
        "assets_count": len(entries),
        "total_assets": len(entries),
        "unregistered_count": len(unregistered),
        "unregistered_items": unregistered,
        "unverified_fonts": unverified_fonts,
        "tts_commercial_notice": tts_commercial_notice,
        "warnings": warnings,
        "assets": entries,
    }
    p_manifest = pipeline_dir / "asset_license_manifest.json"
    write_json(p_manifest, manifest)
    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p_manifest, out_dir / "asset_license_manifest.json")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="商业合规双级拦截与 SHA-256 商用授权清单")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_aud = sub.add_parser("audit-script", help="审查脚本或转写 JSON 的广告法/平台合规性")
    p_aud.add_argument("--input-json", required=True, help="脚本列表 JSON / 02_transcript.json / 03_audio_events.json")
    p_aud.add_argument("--source-type", default="script", choices=["script", "real_voice", "tts"])
    p_aud.add_argument("--pipeline-dir", help="输出 00_compliance_report.json/md 的目录")
    p_aud.add_argument("--whitelist", help="可选 compliance_whitelist.json 路径")
    p_aud.add_argument("--no-auto-action", action="store_true", help="仅检测不自动改写/弃用")
    p_aud.add_argument("--write-back", action="store_true", help="将自动改写/弃用结果写回原 --input-json")

    p_lic = sub.add_parser("build-licenses", help="生成带 SHA-256 的渲染副产物授权清单")
    p_lic.add_argument("--pipeline-dir", required=True)
    p_lic.add_argument("--out-dir", help="同步写入 out 目录路径")
    p_lic.add_argument("--licenses-json", help="外置授权登记 licenses.json")

    args = parser.parse_args()
    if args.cmd == "audit-script":
        in_path = Path(args.input_json)
        raw = read_json(in_path)
        if isinstance(raw, dict):
            primary_key = "sentences" if "sentences" in raw else ("segments" if "segments" in raw else None)
            primary_sents = list(raw.get(primary_key) or []) if primary_key else []
        else:
            primary_key = None
            primary_sents = list(raw or [])
        sents = list(primary_sents)
        if args.pipeline_dir:
            pdir = Path(args.pipeline_dir)
            pkg_p = pdir / "06_packaging.json"
            if pkg_p.is_file():
                for e in (read_json(pkg_p).get("visual_elements") or []):
                    if e.get("text_or_asset"):
                        sents.append({"id": e.get("id", "pkg"), "text": str(e["text_or_asset"])})
            cov_p = pdir / "09_title_cover.json"
            if cov_p.is_file():
                cj = read_json(cov_p)
                for idx, t in enumerate(cj.get("titles") or []):
                    sents.append({"id": f"title_{idx+1}", "text": str(t)})
                for k in ("cover_main", "cover_sub"):
                    if cj.get(k):
                        sents.append({"id": k, "text": str(cj[k])})
            pack_p = pdir / "09_publish_copy_pack.json"
            if pack_p.is_file():
                pj = read_json(pack_p)
                for plat_k, plat_v in (pj.get("platforms") or {}).items():
                    if not isinstance(plat_v, dict):
                        continue
                    for tidx, tt in enumerate(plat_v.get("titles") or [], 1):
                        sents.append({"id": f"copy_{plat_k}_t{tidx}", "text": str(tt)})
                    if plat_v.get("body"):
                        sents.append({"id": f"copy_{plat_k}_body", "text": str(plat_v["body"])})
        rep = audit_script_compliance(
            sents,
            source_type=args.source_type,
            pipeline_dir=Path(args.pipeline_dir) if args.pipeline_dir else None,
            whitelist_path=Path(args.whitelist) if args.whitelist else None,
            auto_action=not args.no_auto_action,
        )
        if args.write_back and not args.no_auto_action and (rep["auto_rewritten_count"] > 0 or rep["dropped_real_voice_ids"]):
            if isinstance(raw, dict) and primary_key:
                raw[primary_key] = primary_sents
                write_json(in_path, raw)
            elif isinstance(raw, list):
                write_json(in_path, primary_sents)
            print(f"[compliance] 已将合规处置结果写回 {in_path}")
        print(f"[compliance] 合规审校完成: passed={rep['passed']}, must={rep['must_sentence_count']}, warn={rep['warn_hit_count']}")
        if not rep["passed"]:
            raise SystemExit(2)
    else:
        rep = build_asset_license_manifest(
            Path(args.pipeline_dir),
            out_dir=Path(args.out_dir) if args.out_dir else None,
            licenses_path=Path(args.licenses_json) if args.licenses_json else None,
        )
        print(f"[license] 商用授权清单生成: {rep['total_assets']} 项, 未登记={rep['unregistered_count']}, passed={rep['passed']}")
        if not rep["passed"]:
            raise SystemExit(2)


if __name__ == "__main__":
    main()

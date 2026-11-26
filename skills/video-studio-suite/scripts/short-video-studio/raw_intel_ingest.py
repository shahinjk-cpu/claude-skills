#!/usr/bin/env python3
"""
[阶段 1：一手原始材料接入与口语去 AI 味剧本检查器]
拒绝二手模板填空，直接从一手原始材料抽取客户真实语言与物证：
1. 原始评论区 / 微信客服导出 / 收银台高频提问文本 -> 提取客户原话顾虑动词、高频追问与真实痛点词组。
2. 原始不可伪造物证目录 (发票/原料/对比照/检测单) -> 建立物证资产索引。
3. 剧本「口语化 + 留存节拍 + 实证锚点」静态检查器：
   - 单句有效字数 > 16 字预警（一口气断句红线）
   - 拦截书面语/AI陈词滥调（赋能/综上所述/不仅如此/痛点/打造/90%的人/别再无效努力 等）
   - 检验首句物理锚点、每 6–8 秒模式中断 (Micro-Hook) 与连续平铺缺乏数字/实物证据警告
输出：pipeline/00_raw_intel.json 与 pipeline/00_script_lint.md
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import read_json, sha256_file, write_json

PAIN_TRIGGERS = [
    "怕", "坑", "贵", "假", "拼接", "预制", "冻肉", "冷冻", "添加剂", "多久",
    "地址", "在哪", "价格", "多少钱", "真假", "靠谱", "退", "包退", "售后", "翻车",
    "后悔", "智商税", "踩雷", "踩坑", "新鲜", "坏了", "偷工", "减料", "套路", "隐形",
    "质保", "保修", "教程", "零基础", "平替", "避坑", "虚标", "溢价", "对比", "实测",
    "原厂", "收费",
]

AI_CLICHE_BLACKLIST = [
    "综上所述", "赋能", "抓手", "不仅如此", "与此同时", "痛点", "打造",
    "90%的人", "别再无效努力", "让我们一起", "众所周知", "总而言之",
    "接下来让我们", "不容错过", "深度剖析", "闭环思维", "干货满满",
]

MICRO_HOOK_CUES = (
    "但是", "其实", "结果", "没想到", "记住", "关键", "你看", "看我", "真相",
    "为什么", "千万别", "反而", "到底", "?", "？", "!", "！",
)

PROOF_KEYWORDS = {
    "发票": "财务/进货凭证",
    "进货": "进货单据",
    "账单": "成本账单",
    "对比": "前后对比",
    "原料": "原材料实拍",
    "后厨": "制作环境",
    "检测": "检验/检测报告",
    "聊天": "真实客户反馈",
    "订单": "真实成交单据",
}

_TS_PREFIX_RE = re.compile(
    r"^\[?\d{4}[-/]\d{1,2}[-/]\d{1,2}(?:[ T]\d{1,2}:\d{2}(?::\d{2})?)?\]?\s*"
)


def _clean_utterance(raw_line: str) -> str:
    line = raw_line.strip()
    if not line:
        return ""
    # 剥离聊天记录常见导出前缀（精确匹配 YYYY-MM-DD HH:MM(:SS)，不贪婪吞掉无方括号整行文本）
    m_ts = _TS_PREFIX_RE.match(line)
    has_ts = bool(m_ts)
    if m_ts:
        line = line[m_ts.end():]
    if has_ts:
        line = re.sub(r"^[^：:\n]{1,18}[：:]\s*", "", line)
    else:
        line = re.sub(r"^(?:用户\w*|客户\w*|网友\w*|买家\w*|顾客\w*|客服\w*|@[^\s：:]{1,16})[：:]\s*", "", line)
    return line.strip()


def _is_url_or_num_token(val: str) -> bool:
    s = val.strip()
    return not s or s.isdigit() or s.startswith(("http://", "https://", "www."))


def read_source_utterances(files: List[Path]) -> List[Dict[str, Any]]:
    utterances: List[Dict[str, Any]] = []

    def add(raw: str, file: Path, digest: str, locator: str, metadata: Dict[str, Any]) -> None:
        clean = _clean_utterance(raw)
        if len(clean) < 3 or _is_url_or_num_token(clean) or clean.startswith(("#", "---")):
            return
        role = str(
            metadata.get("role")
            or metadata.get("speaker_role")
            or metadata.get("角色")
            or metadata.get("发言人")
            or ""
        ).strip().lower()
        role_map = {"客服": "support", "agent": "support", "客户": "customer", "用户": "customer", "viewer": "customer"}
        roles = {"support", "customer"}
        role = role_map.get(role, role)
        if role not in roles:
            raw_s = raw.lstrip()
            m_ts = _TS_PREFIX_RE.match(raw_s)
            prefix = raw_s[m_ts.end():] if m_ts else raw_s
            if re.match(r"^\s*客服[^：:]{0,16}[：:]", prefix):
                role = "support"
            elif re.match(r"^\s*(?:用户|客户|顾客|买家|网友)[^：:]{0,16}[：:]", prefix):
                role = "customer"
            else:
                role = "unknown"
        utterances.append({
            "id": f"{digest[:16]}:{locator}",
            "source_path": str(file.resolve()), "source_sha256": digest, "locator": locator,
            "quote": clean, "role": role,
            "timestamp": metadata.get("timestamp") or metadata.get("created_at") or metadata.get("时间") or metadata.get("发布时间"),
            "participant_id": metadata.get("participant_id") or metadata.get("author_id") or metadata.get("user_id") or metadata.get("用户id") or metadata.get("作者id") or metadata.get("昵称"),
            "record_id": metadata.get("id") or metadata.get("message_id"),
        })
    for fp in files:
        if not fp.exists():
            continue
        suf = fp.suffix.lower()
        digest = sha256_file(fp)
        if suf == ".csv":
            with fp.open("r", encoding="utf-8-sig", errors="ignore") as f:
                rows = list(csv.reader(f))
                if not rows:
                    continue
                text_col: Optional[int] = None
                header = [c.strip().lower() for c in rows[0]]
                for idx, col_name in enumerate(header):
                    if any(k in col_name for k in ("comment", "content", "text", "msg", "quote", "评论", "内容", "问题", "原话")):
                        text_col = idx
                        break
                data_rows = rows[1:] if text_col is not None else rows
                if text_col is None and data_rows:
                    col_scores = []
                    max_cols = max(len(r) for r in data_rows)
                    for ci in range(max_cols):
                        vals = [r[ci].strip() for r in data_rows if ci < len(r)]
                        valid = [v for v in vals if not _is_url_or_num_token(v)]
                        avg_l = (sum(len(v) for v in valid) / len(valid)) if valid else 0.0
                        zh_bonus = 1.5 if any(re.search(r"[\u4e00-\u9fff]", v) for v in valid) else 0.3
                        col_scores.append((avg_l * zh_bonus, ci))
                    text_col = max(col_scores)[1] if col_scores else 0
                first_record = 2 if len(data_rows) < len(rows) else 1
                for record_number, row in enumerate(data_rows, first_record):
                    if text_col is not None and text_col < len(row):
                        add(row[text_col], fp, digest, f"csv:{record_number}", dict(zip(header, row)) if first_record == 2 else {})
        elif suf == ".json":
            raw = read_json(fp)
            if isinstance(raw, dict):
                preferred = ("comments", "messages", "items", "utterances", "sentences")
                key = next((k for k in (*preferred, *raw) if isinstance(raw.get(k), list) and raw[k]), None)
                cand_list = raw[key] if key else []
                root = "/" + key.replace("~", "~0").replace("/", "~1") if key else ""
            else:
                root = ""
                cand_list = raw if isinstance(raw, list) else []
            for index, item in enumerate(cand_list):
                fields = item if isinstance(item, dict) else {}
                txt = fields.get("text") or fields.get("content") or fields.get("comment") or (item if isinstance(item, str) else "")
                add(str(txt), fp, digest, f"json:{root}/{index}", fields)
        else:
            for line_no, raw in enumerate(fp.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                add(raw, fp, digest, f"line:{line_no}", {})
    return list({row["id"]: row for row in utterances}.values())


def extract_raw_intel(
    comments_files: List[Path],
    proof_dir: Optional[Path] = None,
    track: str = "store",
    verified_customer_export: bool = False,
    target_platform: str = "",
) -> Dict[str, Any]:
    source_rows = read_source_utterances(comments_files)
    usable_rows = [row for row in source_rows if row["role"] != "support"]
    by_quote: Dict[str, List[str]] = {}
    for row in usable_rows:
        by_quote.setdefault(row["quote"], []).append(row["id"])
    utterances = list(by_quote)
    trigger_counts: Counter[str] = Counter()
    pain_phrases: List[Dict[str, Any]] = []
    customer_questions: List[str] = []

    store_boost = {"地址", "在哪", "价格", "多少钱", "冻肉", "预制", "新鲜", "售后", "退", "隐形"}
    for u in utterances:
        hits = [kw for kw in PAIN_TRIGGERS if kw in u]
        for kw in hits:
            trigger_counts[kw] += (2 if (track == "store" and kw in store_boost) else 1)
        is_q = any(q in u for q in ("?", "？", "吗", "怎么", "多少", "哪", "是不是", "能不能", "会不会", "有没"))
        if is_q and u not in customer_questions:
            customer_questions.append(u)
        if hits or is_q:
            pain_phrases.append({
                "quote": u,
                "source_ids": by_quote[u],
                "triggers": hits,
                "is_question": is_q,
                "score": len(hits) * 2 + (1 if is_q else 0),
            })

    pain_phrases.sort(key=lambda x: (-x["score"], len(x["quote"])))

    proof_assets: List[Dict[str, Any]] = []
    if proof_dir and proof_dir.exists():
        exts = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".pdf", ".csv", ".xlsx", ".txt", ".json"}
        for f in sorted(proof_dir.iterdir()):
            if not f.is_file() or f.suffix.lower() not in exts:
                continue
            label = "实景物证"
            for k, v in PROOF_KEYWORDS.items():
                if k in f.name:
                    label = v
                    break
            digest = sha256_file(f)
            proof_assets.append({
                "id": f"proof:{digest[:16]}",
                "sha256": digest,
                "locator": "asset",
                "filename": f.name,
                "path": str(f.resolve()),
                "ext": f.suffix.lower(),
                "proof_type": label,
            })

    top_keywords = [k for k, _ in trigger_counts.most_common(10)]
    return {
        "step": "00_raw_intel",
        "track": track,
        "target_platform": str(target_platform or "").strip().lower(),
        "verified_by_real_users": bool(verified_customer_export and usable_rows),
        "source_utterances": source_rows,
        "identified_participant_count": len({str(row["participant_id"]) for row in usable_rows if row["participant_id"]}),
        "utterance_count": len(utterances),
        "top_pain_triggers": [{"word": k, "count": c} for k, c in trigger_counts.most_common(12)],
        "pain_keywords": top_keywords,
        "raw_pain_phrases": pain_phrases[:20],
        "customer_questions": customer_questions[:15],
        "proof_assets": proof_assets,
    }


_EXAGGERATED_CLAIMS = ("全网第一", "100%有效", "必火", "绝对能爆", "震惊全网", "99%的人都不知道", "最强没有之一")
_PLATFORM_RESIDUE_MAP = {
    "xiaohongshu": ("左下角小黄车", "一键三连", "投币收藏", "点进橱窗"),
    "bilibili": ("左下角小黄车", "点进橱窗", "主页笔记"),
    "douyin": ("一键三连", "投币", "主页笔记"),
    "shipinhao": ("左下角小黄车", "一键三连", "投币"),
}
_DANGLING_START_RE = re.compile(r"^(?:这个|那个|它|这里|那样)[，,。]?")


def _item_text(it: Dict[str, Any]) -> str:
    return str(it.get("text") or it.get("show") or it.get("say") or "").strip()


def lint_script(script_items: List[Dict[str, Any]], raw_intel: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """对口播台词做口语化断句、去 AI 陈词滥调、实证锚点、四轮审稿与 6–8 秒留存节拍体检。"""
    issues: List[Dict[str, Any]] = []
    valid_items = [it for it in script_items if not it.get("is_filler", False) and _item_text(it)]

    if valid_items:
        first_txt = _item_text(valid_items[0])
        if re.match(r"^(大家好|哈喽|hello|今天我们来|今天给大家|我是)", first_txt, re.IGNORECASE):
            issues.append({
                "line": 1,
                "severity": "error",
                "code": "weak_opening",
                "text": first_txt,
                "message": "开头 3 秒别寒暄或自我介绍，直接抛具体问题、数字或顾客最关心的原话。",
            })

    target_platform = str((raw_intel or {}).get("target_platform") or "").strip().lower()
    seen_norms: List[Tuple[int, set]] = []
    chars_since_hook = 0
    dry_abstract_run = 0
    full_chunks: List[str] = []

    for idx, it in enumerate(valid_items, start=1):
        txt = _item_text(it)
        full_chunks.append(txt)
        eff_chars = re.sub(r"[\s，。！？、；：“”‘’（）.,!?;:]+", "", txt)
        char_len = len(eff_chars)

        if char_len > 16:
            issues.append({
                "line": idx,
                "severity": "warn",
                "code": "too_long_breath",
                "text": txt,
                "message": f"这句有 {char_len} 个字，一口气念太长，建议拆成两句短话，字幕也更好看。",
            })

        cliches = [c for c in AI_CLICHE_BLACKLIST if c in txt]
        if cliches:
            issues.append({
                "line": idx,
                "severity": "error",
                "code": "ai_cliche",
                "text": txt,
                "message": f"出现了书面套话 {cliches}，建议换成平时跟客人聊天的大白话。",
            })

        for bad_claim in _EXAGGERATED_CLAIMS:
            if bad_claim in txt:
                issues.append({
                    "line": idx,
                    "severity": "error",
                    "code": "exaggerated_claim",
                    "text": txt,
                    "message": f"包含无法兑现的夸大说法「{bad_claim}」，建议改成可核验的具体事实或实测数据。",
                })

        if idx == 1 and _DANGLING_START_RE.match(txt):
            issues.append({
                "line": idx,
                "severity": "warn",
                "code": "dangling_pronoun",
                "text": txt,
                "message": "第一句用「这个/那个/它」开头指向不明确，建议直接说出具体东西的名字。",
            })

        if target_platform in _PLATFORM_RESIDUE_MAP:
            for res_w in _PLATFORM_RESIDUE_MAP[target_platform]:
                if res_w in txt:
                    issues.append({
                        "line": idx,
                        "severity": "warn",
                        "code": "platform_residue",
                        "text": txt,
                        "message": f"当前目标平台为 {target_platform}，但句子里留有其他平台话术「{res_w}」，建议改掉。",
                    })

        if char_len >= 8:
            cur_set = set(eff_chars)
            for prev_i, prev_set in seen_norms:
                overlap = len(cur_set & prev_set) / max(1, len(cur_set | prev_set))
                if overlap >= 0.82:
                    issues.append({
                        "line": idx,
                        "severity": "warn",
                        "code": "redundant_paragraph",
                        "text": txt,
                        "message": f"与第 {prev_i} 句意思高度重复，做一遍“删除测试”：若没有新增例子或限制条件建议删掉。",
                    })
                    break
            seen_norms.append((idx, cur_set))

        has_concrete = bool(re.search(r"\d+|半|两|三|块|元|年|天|小时|分钟|秒|斤|克|米|厘米|后厨|门店|合同|报告|票|图|表|实测|拆", txt))
        if has_concrete:
            dry_abstract_run = 0
        else:
            dry_abstract_run += 1
            if dry_abstract_run >= 4:
                issues.append({
                    "line": idx,
                    "severity": "warn",
                    "code": "abstract_fluff",
                    "text": txt,
                    "message": "连着 4 句没给具体数字、时间或实拍细节，容易显得在讲大道理，建议补一个实拍细节。",
                })
                dry_abstract_run = 0

        emo = str(it.get("emotion", "info"))
        has_hook_cue = emo in ("hook", "twist", "persona", "cta") or any(c in txt for c in MICRO_HOOK_CUES)
        if idx > 1:
            if has_hook_cue:
                chars_since_hook = 0
            else:
                chars_since_hook += char_len
                if chars_since_hook > 34:
                    issues.append({
                        "line": idx,
                        "severity": "warn",
                        "code": "missing_micro_hook",
                        "text": txt,
                        "message": f"连着约 {chars_since_hook/4.5:.1f} 秒（{chars_since_hook}字）一直在平铺直叙，建议在这里加一句转折、反问或切出一个实物特写抓回注意力。",
                    })
                    chars_since_hook = 0

    pain_kws = (raw_intel or {}).get("pain_keywords", [])
    full_txt = "".join(full_chunks)
    matched_pains = [k for k in pain_kws if k in full_txt]

    errors = sum(1 for i in issues if i["severity"] == "error")
    warns = sum(1 for i in issues if i["severity"] == "warn")
    return {
        "passed": errors == 0,
        "error_count": errors,
        "warn_count": warns,
        "sentence_count": len(valid_items),
        "matched_raw_pain_keywords": matched_pains,
        "issues": issues,
    }


def export_script_deliverables(
    out_dir: Path,
    title: str,
    sentences: List[Dict[str, Any]],
    opening_candidates: Optional[List[Dict[str, str]]] = None,
    platform: str = "douyin",
    todo_items: Optional[List[str]] = None,
    proof_assets: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, str]:
    """
    口播文案双文件解耦导出：
    1. 00_口播纯享稿.txt：零 Markdown、零停顿符与画面提示，过滤废话句，直接放进提词器顺口开念；
    2. 00_拍摄执行方案.md：含 3 选 1 开头候选（标出兑现段）、带停顿/画面配合逐字稿、易卡句提醒与原始凭证核验槽位。
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    active_sents = [s for s in sentences if not s.get("is_filler", False)]
    clean_lines = [
        str(s.get("say") or s.get("text") or s.get("show") or "").strip()
        for s in active_sents
        if str(s.get("say") or s.get("text") or s.get("show") or "").strip()
    ]
    pure_txt_p = out_dir / "00_口播纯享稿.txt"
    pure_txt_p.write_text("\n".join(clean_lines) + "\n", encoding="utf-8")

    cands = opening_candidates or [
        {"type": "数据反常识（推荐）", "text": clean_lines[0] if clean_lines else title, "payoff": "第 2 段直接给出真实对照"},
        {"type": "具体场景切入", "text": f"你有没有遇到过这种情况：{clean_lines[0] if clean_lines else title}", "payoff": "第 2–3 段给出解法"},
        {"type": "常见误解纠偏", "text": "很多人以为不是这样，但实际测下来恰恰相反", "payoff": "第 2 段用实拍验证"},
    ]
    hard_to_read = [ln for ln in clean_lines if len(re.sub(r"[\s，。！？、]", "", ln)) > 16][:2]
    total_chars = sum(len(re.sub(r"[\s，。！？、]", "", ln)) for ln in clean_lines)
    est_sec = round(total_chars / 4.2, 1)

    auto_todos = list(todo_items or [])
    proof_count = len(proof_assets or [])
    for idx, ln in enumerate(clean_lines, 1):
        if re.search(r"\d+(?:\.\d+)?[%％倍元块斤克万亿小时分钟天年]", ln) and proof_count == 0:
            auto_todos.append(f"第 {idx} 句含具体数字/对比（「{ln[:18]}」），请准备对应实拍特写或单据原件，若无则收敛表述")
            if len(auto_todos) >= 5:
                break

    plat_cn = {"douyin": "抖音", "xiaohongshu": "小红书", "shipinhao": "视频号", "bilibili": "B站"}.get(
        str(platform or "").lower(), str(platform or "通用平台")
    )
    md_lines = [
        f"# 《{title}》口播拍摄执行方案",
        "",
        f"- **适配平台**：{plat_cn} | **全稿字数**：约 `{total_chars}` 字 | **预计口播时长**：约 `{est_sec}` 秒 | **已关联物证**：`{proof_count}` 件",
        "- **开念纯享稿**：直接打开同目录 `00_口播纯享稿.txt`（零符号干扰，放提词器直接照念）",
        "",
        "## 一、开头 3 选 1 候选（已标出正文兑现位置）",
        *[f"{i}. **【{c.get('type', '候选')}】** {c.get('text', '')}（兑现：{c.get('payoff', '正文展开')}）" for i, c in enumerate(cands[:3], 1)],
        "",
        "## 二、带停顿与画面配合的逐字稿",
        *[f"{i}. {ln}  〔画面：匹配实拍特写或重点图解〕" for i, ln in enumerate(clean_lines, 1)],
        "",
        "## 三、开录前防卡壳提醒",
        *(
            [f"- 偏长易喘气句（建议中间停半拍）：「{ln}」" for ln in hard_to_read]
            if hard_to_read
            else ["- 全稿均为短句，正常语速顺口可读。"]
        ),
        "",
        "## 四、发布前待补 / 凭证核验清单",
        *([f"- [ ] {x}" for x in auto_todos] if auto_todos else ["- 已备齐核验材料，确认片中数字准确即可开拍。"]),
        "",
    ]
    plan_md_p = out_dir / "00_拍摄执行方案.md"
    plan_md_p.write_text("\n".join(md_lines), encoding="utf-8")
    return {"pure_script_txt": str(pure_txt_p.resolve()), "execution_plan_md": str(plan_md_p.resolve())}


def render_lint_markdown(lint_res: Dict[str, Any], raw_intel: Dict[str, Any]) -> str:
    honest_banner = (
        ""
        if raw_intel.get("verified_by_real_users")
        else "> ⚠️ **实话提醒**：当前还没导入真实评论区或客服记录，这次的选题角度主要靠行业经验推演，**还没经过真实顾客提问验证**。\n\n"
    )
    code_zh = {
        "weak_opening": "开头太客套",
        "too_long_breath": "句子偏长",
        "ai_cliche": "书面套话",
        "abstract_fluff": "缺少具体细节",
        "missing_micro_hook": "平铺缺少转折",
        "exaggerated_claim": "夸大无法兑现",
        "dangling_pronoun": "开句指代不明",
        "platform_residue": "跨平台话术残留",
        "redundant_paragraph": "段落意思重复",
    }
    sev_zh = {"error": "建议必改", "warn": "优化提醒"}
    lines = [
        "# 顾客原话提炼与口播稿体检报告",
        "",
        honest_banner.rstrip("\n"),
        f"- **读入顾客原话数**：{raw_intel.get('utterance_count', 0)} 条 | 实拍凭证材料：{len(raw_intel.get('proof_assets', []))} 件",
        f"- **是否来自真实顾客反馈**：{'✅ 是，已拿到真实原话' if raw_intel.get('verified_by_real_users') else '⚠️ 暂未导入真实评论，先按经验推演'}",
        f"- **顾客最常问的关键词**：{', '.join(raw_intel.get('pain_keywords', [])) or '（尚未导入评论记录）'}",
        f"- **口播稿体检结论**：{'✅ 自然顺口，可以直接拍' if lint_res['passed'] else '❌ 有几处套话或开头太客套，建议先改再拍'} "
        f"（必改 {lint_res['error_count']} 处 / 建议优化 {lint_res['warn_count']} 处）",
        "",
    ]
    if raw_intel.get("customer_questions"):
        lines += ["## 顾客高频原话提问（可以直接拿来做开头第一句）"]
        for q in raw_intel["customer_questions"][:6]:
            lines.append(f"- 「{q}」")
        lines.append("")

    if lint_res["issues"]:
        lines += [
            "## 逐句修改建议",
            "",
            "| 句号 | 重要度 | 问题类型 | 原句 | 修改建议 |",
            "| :---: | :---: | :--- | :--- | :--- |",
        ]
        for iss in lint_res["issues"]:
            lines.append(
                f"| 第{iss['line']}句 | {sev_zh.get(iss['severity'], iss['severity'])} | {code_zh.get(iss['code'], iss['code'])} | "
                f"{iss['text']} | {iss['message']} |"
            )
    else:
        lines.append("整篇口播稿口语自然、断句顺畅、节奏起伏到位，可以直接开拍。")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="一手原始材料接入与口语去AI味剧本检查器")
    parser.add_argument("--comments-file", nargs="*", default=[], help="同行评论区/客服聊天导出文件(.txt/.md/.csv/.json)")
    parser.add_argument("--verified-customer-export", action="store_true", help="确认导出文件来自真实客户互动")
    parser.add_argument("--proof-dir", help="门店原始物证材料目录")
    parser.add_argument("--script-json", help="待体检口播文案 JSON")
    parser.add_argument("--track", choices=["store", "creator"], default="store")
    parser.add_argument("--platform", default="", help="目标发布平台(douyin/xiaohongshu/shipinhao/bilibili)，用于检查跨平台残留话术")
    parser.add_argument("--export-script-dir", help="可选：导出 00_口播纯享稿.txt 与 00_拍摄执行方案.md 的目录")
    parser.add_argument("--title", default="", help="可选：拍摄执行方案标题")
    parser.add_argument("--output", required=True, help="输出 00_raw_intel.json 路径")
    args = parser.parse_args()

    comment_paths = [Path(p) for p in args.comments_file]
    proof_p = Path(args.proof_dir) if args.proof_dir else None
    intel = extract_raw_intel(
        comment_paths,
        proof_dir=proof_p,
        track=args.track,
        verified_customer_export=args.verified_customer_export,
        target_platform=args.platform,
    )

    script_items: List[Dict[str, Any]] = []
    if args.script_json and Path(args.script_json).exists():
        raw_script = read_json(Path(args.script_json))
        script_items = (
            raw_script.get("sentences") or raw_script.get("segments") or []
            if isinstance(raw_script, dict)
            else raw_script
        )
        lint_res = lint_script(script_items, raw_intel=intel)
    else:
        lint_res = lint_script([], raw_intel=intel)

    intel["script_lint"] = lint_res
    out_json = Path(args.output)
    write_json(out_json, intel)
    lint_md = out_json.parent / "00_script_lint.md"
    lint_md.write_text(render_lint_markdown(lint_res, intel), encoding="utf-8")
    if args.export_script_dir and script_items:
        exp = export_script_deliverables(
            Path(args.export_script_dir),
            title=args.title or (Path(args.script_json).stem if args.script_json else "口播视频"),
            sentences=script_items,
            platform=args.platform or "douyin",
            proof_assets=intel.get("proof_assets"),
        )
        print(f"[raw_intel] 已导出双文件提词稿与拍摄方案 -> {exp['pure_script_txt']}")
    print(
        f"[raw_intel] 已整理顾客原话 {intel['utterance_count']} 条 / 实拍凭证 {len(intel['proof_assets'])} 件，"
        f"口播稿体检：必改 {lint_res['error_count']} 处 / 建议优化 {lint_res['warn_count']} 处 -> {out_json}"
    )


if __name__ == "__main__":
    main()

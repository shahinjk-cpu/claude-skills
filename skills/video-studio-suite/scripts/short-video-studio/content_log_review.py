#!/usr/bin/env python3
"""Journal platform snapshots, review comparable cohorts and propose tested parameters."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from common import read_json, resolve_workspace_paths, write_json
from content_experiment import (
    activate_candidate, evaluate_plan, refresh_candidates, register_plan,
    snapshot_key, validate_snapshot,
)

DEMO_RECORDS = [
    {
        "video_id": "v_001", "date": "2026-11-08", "track": "store", "platform": "douyin",
        "traffic_source": "local_feed", "observation_hours": 48, "duration_sec": 42,
        "published_at": "2026-11-08T10:00:00+08:00", "captured_at": "2026-11-10T10:00:00+08:00",
        "title": "价格越高的菜利润越低", "style_id": "style_14",
        "metrics": {
            "retention_3s": {"numerator": 11840, "denominator": 18500},
            "completion_rate": {"numerator": 6290, "denominator": 18500},
            "inquiry_rate": {"numerator": 24, "denominator": 18500},
        },
    },
    {
        "video_id": "v_002", "date": "2026-11-09", "track": "store", "platform": "douyin",
        "traffic_source": "local_feed", "observation_hours": 48, "duration_sec": 44,
        "published_at": "2026-11-09T10:00:00+08:00", "captured_at": "2026-11-11T10:00:00+08:00",
        "title": "八年老店老板的底线", "style_id": "style_14",
        "metrics": {
            "retention_3s": {"numerator": 5336, "denominator": 9200},
            "completion_rate": {"numerator": 2852, "denominator": 9200},
            "inquiry_rate": {"numerator": 31, "denominator": 9200},
        },
    },
    {
        "video_id": "v_003", "date": "2026-11-11", "track": "store", "platform": "douyin",
        "traffic_source": "local_feed", "observation_hours": 48, "duration_sec": 38,
        "published_at": "2026-11-11T10:00:00+08:00", "captured_at": "2026-11-13T10:00:00+08:00",
        "title": "门店日常工作实拍", "style_id": "style_06", "drop_off_sec": 4.2,
        "metrics": {
            "retention_3s": {"numerator": 1209, "denominator": 3100},
            "completion_rate": {"numerator": 496, "denominator": 3100},
            "inquiry_rate": {"numerator": 3, "denominator": 3100},
        },
    },
    {
        "video_id": "v_004", "date": "2026-11-13", "track": "store", "platform": "douyin",
        "traffic_source": "local_feed", "observation_hours": 48, "duration_sec": 41,
        "published_at": "2026-11-13T10:00:00+08:00", "captured_at": "2026-11-15T10:00:00+08:00",
        "title": "高于20块才敢用的鲜羊排真相", "style_id": "style_14",
        "metrics": {
            "retention_3s": {"numerator": 16974, "denominator": 24600},
            "completion_rate": {"numerator": 9348, "denominator": 24600},
            "inquiry_rate": {"numerator": 29, "denominator": 24600},
        },
    },
]

METRIC_NAMES = {
    "retention_3s": "3 秒仍在看",
    "completion_rate": "看完整条",
    "inquiry_rate": "有效咨询",
    "store_visit_rate": "到店核销",
    "follow_rate": "新增关注",
}

PLATFORM_NAMES = {
    "douyin": "抖音",
    "xiaohongshu": "小红书",
    "shipinhao": "视频号",
    "bilibili": "B站",
    "kuaishou": "快手",
}

TRAFFIC_SOURCE_NAMES = {
    "local_feed": "同城推荐",
    "feed": "推荐页自然流",
    "organic": "自然推荐",
    "search": "主动搜索",
    "profile": "主页回看",
    "paid": "付费推广",
}


def load_records(jsonl_path: Path) -> List[Dict[str, Any]]:
    if not jsonl_path.is_file():
        return []
    indexed: dict[tuple[Any, ...], dict[str, Any]] = {}
    with jsonl_path.open(encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            if not line.strip():
                continue
            row = json.loads(line)
            key = snapshot_key(row) or ("legacy-row", index)
            indexed[key] = row
    return list(indexed.values())


def append_record(log_dir: Path, record: Dict[str, Any]) -> Path:
    validate_snapshot(record)
    log_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = log_dir / "records.jsonl"
    key = snapshot_key(record)
    if key is not None:
        prior = next((row for row in load_records(jsonl_path) if snapshot_key(row) == key), None)
        if prior is not None:
            if prior.get("track", "store") != record.get("track", "store"):
                raise ValueError("同一平台视频快照已归属另一轨道")
            if record == prior or ("date" not in record and record == {k: v for k, v in prior.items() if k != "date"}):
                return jsonl_path
    row = {"date": datetime.now().date().isoformat(), **record}
    with jsonl_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
    return jsonl_path


def diagnose_edl_drop_off(record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """根据后台留存曲线最大断崖秒数 drop_off_sec 反查当时 04_edl.json 对应的镜头与台词。"""
    drop_t = record.get("drop_off_sec")
    edl_p = record.get("edl_path")
    if drop_t is None or not edl_p:
        return None
    p = Path(str(edl_p))
    if not p.is_file():
        return None
    try:
        edl = json.loads(p.read_text(encoding="utf-8"))
        t = float(drop_t)
        clips = edl.get("clips", [])
        hit = next((c for c in clips if float(c["timeline_in_sec"]) <= t <= float(c["timeline_out_sec"])), None)
        if not hit and clips:
            hit = min(clips, key=lambda c: abs(float(c["timeline_in_sec"]) - t))
        if not hit:
            return None
        return {
            "title": record.get("title", "未命名"),
            "drop_off_sec": round(t, 2),
            "clip_id": hit.get("clip_id"),
            "track_role": hit.get("track_role"),
            "clip_span": f"{hit.get('timeline_in_sec', 0):.2f}s–{hit.get('timeline_out_sec', 0):.2f}s",
            "duration_sec": hit.get("duration_sec"),
            "sentence_text": hit.get("sentence_text", ""),
            "purpose": hit.get("purpose", ""),
        }
    except Exception:
        return None


def _active_profile(log_dir: Path, track: str) -> Path:
    path = log_dir / f"account_profile_{track}.json"
    if path.is_file():
        return path
    legacy = log_dir / "account_profile.json"
    existing = read_json(legacy) if legacy.is_file() else {}
    if existing and existing.get("track", "store") == track:
        write_json(path, existing)
    else:
        write_json(path, {"track": track, "sample_sufficient": False, "active_candidate": None})
    return path


def generate_weekly_review(log_dir: Path, out_md: Optional[Path] = None, track: Optional[str] = None) -> Dict[str, Any]:
    all_records = load_records(log_dir / "records.jsonl")
    if not all_records:
        raise ValueError("暂无发布记录。")
    if track is None:
        track = Counter(row.get("track", "store") for row in all_records).most_common(1)[0][0]
    records = [row for row in all_records if row.get("track", "store") == track]
    if not records:
        raise ValueError(f"当前轨道 {track} 暂无发布记录。")
    out_md = out_md or log_dir / f"weekly_review_{track}.md"

    def captured_date(row: Dict[str, Any]) -> date:
        value = str(row.get("captured_at") or row.get("date") or "")
        if not value:
            return date.min
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return date.min

    dated = [row for row in records if captured_date(row) != date.min]
    last_day = max((captured_date(row) for row in dated), default=date.today())
    first_day = last_day - timedelta(days=6)
    recent = [row for row in records if first_day <= captured_date(row) <= last_day]
    cohorts: dict[tuple[str, float, str, int], dict[str, list[int]]] = {}
    cohort_video_ids: dict[tuple[str, float, str, int], set[str]] = {}
    for row in recent:
        if not row.get("metrics"):
            continue
        sk = snapshot_key(row)
        if not sk or len(sk) != 3 or sk[0] == "legacy" or row.get("duration_sec") is None or not row.get("traffic_source"):
            continue
        platform, video_id, hours = sk
        band = int(float(row["duration_sec"]) // 15) * 15
        group = (platform, hours, str(row["traffic_source"]), band)
        totals = cohorts.setdefault(group, {})
        cohort_video_ids.setdefault(group, set()).add(video_id)
        for name, values in row["metrics"].items():
            if not isinstance(values, dict) or "numerator" not in values or "denominator" not in values:
                continue
            count = totals.setdefault(name, [0, 0])
            count[0] += values["numerator"]
            count[1] += values["denominator"]

    active_path = _active_profile(log_dir, track)
    profile = read_json(active_path)
    candidates = refresh_candidates(log_dir, records, track)
    diagnoses = [item for row in recent if (item := diagnose_edl_drop_off(row))]
    lines = [
        f"# {'门店' if track == 'store' else '博主'}运营周复盘",
        "",
        f"统计日期：{first_day.isoformat()} 至 {last_day.isoformat()}，共整理 {len(recent)} 条已发布视频的后台数据。",
        "",
        "## 按相同发布条件分组的表现",
        "",
    ]
    if not cohorts:
        lines.append("本期还缺少带完整观看与转化人数的数据记录，历史手填记录已为你保留查阅。")
    for (platform, hours, traffic, band), metrics in sorted(cohorts.items()):
        units = len(cohort_video_ids[(platform, hours, traffic, band)])
        plat_zh = PLATFORM_NAMES.get(str(platform).casefold(), str(platform))
        traf_zh = TRAFFIC_SOURCE_NAMES.get(str(traffic).casefold(), str(traffic))
        lines.append(f"- {plat_zh} · 发布后 {hours:g} 小时 · {traf_zh} · 片长 {band}–{band + 15} 秒 · 共 {units} 条")
        for name, (numerator, denominator) in sorted(metrics.items()):
            label = METRIC_NAMES.get(name, name)
            lines.append(f"  - {label}：{numerator}/{denominator}（{numerator / denominator:.2%}）")
    if diagnoses:
        lines.extend(["", "## 观众滑走最集中的画面时间点（建议下次优先改这里）", ""])
        for item in diagnoses:
            role_zh = "真人出镜说话" if item.get("track_role") == "a_roll" else "特写/补拍画面"
            lines.append(
                f"- 《{item['title']}》第 {item['drop_off_sec']:.1f} 秒滑走最多"
                f"（对应镜头 {item['clip_span']}，{role_zh}·{item.get('purpose') or '展示画面'}，当时正在讲：「{item['sentence_text']}」）"
            )
    lines.extend([
        "",
        "## 对比测试与下次沿用设置",
        "",
        "> 提醒：单条视频的涨跌受当天话题和推荐池波动影响很大，只有凑够多条同条件视频、效果稳稳高出一截时，系统才会建议把它变成你的固定做法。",
        "",
    ])
    active_ver = profile.get("active_candidate")
    lines.append(f"- 当前沿用的剪辑习惯：{'已按实测胜出方案自动记住（编号 ' + str(active_ver)[:8] + '）' if active_ver else '沿用默认设置'}")
    if not candidates:
        lines.append("- 目前还没有正在跑的对比测试。")
    statuses = {"CANDIDATE": "效果稳稳高出一截，可以放心采纳", "INCONCLUSIVE": "目前差距还不明显，建议再观察", "INSUFFICIENT": "对比的视频条数还不够，继续积累"}
    for candidate in candidates:
        counts = candidate["units"]
        short_cid = str(candidate["candidate_id"])[:8]
        line = (f"- 测试项「{candidate['plan']['id']}」 · {statuses[candidate['status']]} · "
                f"旧做法 {counts['control']} 条 vs 新做法 {counts['variant']} 条（方案号 {short_cid}）")
        if "effect" in candidate:
            low, high = candidate["interval_95"]
            line += f" · 平均变化 {candidate['effect']:+.2%}（波动范围 {low:+.2%} ~ {high:+.2%}）"
        if candidate["plan"]["design"] == "matched":
            line += " · 同题配对对比"
        lines.append(line)
    lines.append("")
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"[content_log] 复盘 {out_md} · 当前配置 {active_path}")
    return {
        "track": track, "record_count": len(records), "weekly_record_count": len(recent),
        "account_profile_json": str(active_path.resolve()), "weekly_review_md": str(out_md.resolve()),
        "drop_diagnoses": diagnoses, "candidates": candidates,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="content-log 微观留存诊断与账号参数基因库复盘")
    parser.add_argument("--log-dir", help="content-log 存储目录（未传时可配 --account 自动隔离）")
    parser.add_argument("--account", help="账号标识，自动定位该账号专属 content-log/")
    parser.add_argument("--track", choices=["store", "creator"], help="按赛道轨道隔离计算基线与账号参数档案")
    parser.add_argument("--workspace-root", help="可选：自定义专属工作区根目录")
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("--add-json", help="追加一条发布后台数据 JSON 字符串或文件")
    input_group.add_argument("--register-plan", type=Path, help="在发布前登记对照规则")
    input_group.add_argument("--replay-plan", type=Path, help="用历史数据回放，不生成可启用版本")
    input_group.add_argument("--activate-candidate", help="复核后启用达到门槛的版本")
    input_group.add_argument("--demo", action="store_true", help="在独立目录内生成示例数据与复盘")
    args = parser.parse_args()

    if args.log_dir:
        log_dir = Path(args.log_dir)
    else:
        ws = resolve_workspace_paths(
            account=args.account or "default",
            workspace_root=Path(args.workspace_root) if args.workspace_root else None,
        )
        log_dir = ws["content_log_dir"]
    if args.register_plan:
        print(register_plan(log_dir, read_json(args.register_plan)))
        return
    if args.replay_plan:
        result = evaluate_plan(read_json(args.replay_plan), load_records(log_dir / "records.jsonl"), None)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    if args.activate_candidate:
        print(activate_candidate(log_dir, load_records(log_dir / "records.jsonl"), args.activate_candidate))
        return
    if args.demo:
        if args.track == "creator":
            parser.error("复盘示例仅含门店轨数据。")
        demo_root = log_dir.parent / "review-demos"
        demo_root.mkdir(parents=True, exist_ok=True)
        log_dir = Path(tempfile.mkdtemp(prefix="store-", dir=demo_root))
        for r in DEMO_RECORDS:
            append_record(log_dir, dict(r))
    elif args.add_json:
        if args.add_json.lstrip().startswith("{"):
            rec = json.loads(args.add_json)
        else:
            rec = read_json(Path(args.add_json))
        if args.track:
            if rec.get("track", args.track) != args.track:
                parser.error("数据中的 track 与 --track 不一致。")
            rec["track"] = args.track
        append_record(log_dir, rec)

    generate_weekly_review(log_dir, track=args.track)


if __name__ == "__main__":
    main()

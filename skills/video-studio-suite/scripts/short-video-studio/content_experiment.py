"""Evaluate predeclared video-level experiments and activate one measured parameter."""

import hashlib
import json
import math
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from common import read_json, write_json


PARAMETER_LIMITS = {
    "pause_sec": (0.14, 0.32),
    "persona_pause_sec": (0.18, 0.32),
    "twist_pause_sec": (0.20, 0.36),
    "narrative_pause_sec": (0.16, 0.30),
    "target_median_shot_sec": (1.12, 2.82),
    "target_aroll_ratio": (0.0, 0.75),
    "micro_hook_max_sec": (3.0, 20.0),
}
METRICS = {
    "store": {"inquiry_rate", "store_visit_rate"},
    "creator": {"retention_3s", "completion_rate", "follow_rate"},
}


def _identifier(value: Any) -> str:
    identifier = str(value or "")
    if not re.fullmatch(r"[\w-]{1,64}", identifier):
        raise ValueError("实验编号须为 1 至 64 个字母、数字、下划线或短横线")
    return identifier


def _fingerprint(data: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _timestamp(value: str) -> datetime:
    written = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if written.tzinfo is None:
        raise ValueError("实验时间必须包含时区")
    return written.astimezone(timezone.utc)


def validate_plan(plan: dict[str, Any]) -> None:
    _identifier(plan["id"])
    if plan.get("design") not in ("matched", "randomized"):
        raise ValueError("设计须为 matched 或 randomized")
    if plan.get("primary_metric") not in METRICS.get(plan.get("track"), set()):
        raise ValueError("主指标与账号轨道不匹配")
    if not all(isinstance(plan.get(key), str) and plan[key].strip() for key in ("platform", "traffic_source", "variable")):
        raise ValueError("须预先记录平台、流量来源和唯一变量")
    if not 0 < float(plan["observation_hours"]) <= 24 * 90:
        raise ValueError("观察时长须在 90 天内")
    lower, upper = plan["duration_band_sec"]
    if not 0 < float(lower) <= float(upper) < math.inf:
        raise ValueError("片长范围无效")
    if not isinstance(plan.get("min_units_per_arm"), int) or plan["min_units_per_arm"] < 5:
        raise ValueError("每组须预先指定至少 5 个独立视频")
    if not 0 < float(plan["min_effect"]) < 1:
        raise ValueError("最小有意义提升须以 0 到 1 的比例表示")
    if "control_value" not in plan or "variant_value" not in plan or plan["control_value"] == plan["variant_value"]:
        raise ValueError("须指定两个不同的对照值")
    parameter = plan.get("parameter")
    if parameter and parameter != plan["variable"]:
        raise ValueError("可启用的参数必须与唯一实验变量一致")
    if parameter == "preferred_style_id":
        if not all(re.fullmatch(r"style_(0[1-9]|1\d|2[0-4])", str(plan[key])) for key in ("control_value", "variant_value")):
            raise ValueError("风格编号无效")
    elif parameter:
        if parameter not in PARAMETER_LIMITS:
            raise ValueError("该变量当前不能自动写入制作配置")
        low, high = PARAMETER_LIMITS[parameter]
        if not all(low <= float(plan[key]) <= high for key in ("control_value", "variant_value")):
            raise ValueError("参数超出制作范围")


def register_plan(log_dir: Path, plan: dict[str, Any]) -> Path:
    validate_plan(plan)
    path = log_dir / "experiment_plans" / f"{plan['id']}.json"
    if path.is_file():
        if read_json(path)["plan"] != plan:
            raise ValueError("实验编号已登记。修改规则时使用新实验编号")
        return path
    write_json(path, {"plan": plan, "registered_at": datetime.now(timezone.utc).isoformat()})
    return path


def snapshot_key(record: dict[str, Any]) -> tuple[Any, ...] | None:
    if record.get("platform") and record.get("video_id") and record.get("observation_hours") is not None:
        return (str(record["platform"]).strip().casefold(), str(record["video_id"]), float(record["observation_hours"]))
    if record.get("video_id"):
        return ("legacy", record.get("track", "store"), str(record["video_id"]), record.get("observation_hours"))
    return None


def validate_snapshot(record: dict[str, Any]) -> None:
    metrics = record.get("metrics")
    if metrics is None:
        return
    required = ("platform", "video_id", "observation_hours", "duration_sec", "traffic_source", "published_at", "captured_at")
    if any(record.get(key) in (None, "") for key in required):
        raise ValueError("带原始分子分母的快照须提供来源、时间与片长")
    expected = float(record["observation_hours"])
    captured_hours = (_timestamp(record["captured_at"]) - _timestamp(record["published_at"])).total_seconds() / 3600
    if not 0 < expected <= 24 * 90 or not math.isfinite(float(record["duration_sec"])) or float(record["duration_sec"]) <= 0:
        raise ValueError("观察时长或视频时长无效")
    if abs(captured_hours - expected) > min(1.0, expected * 0.05):
        raise ValueError("实际取数时间与声明的观察窗口不一致")
    if not isinstance(metrics, dict) or not metrics:
        raise ValueError("metrics 不能为空")
    for name, metric in metrics.items():
        numerator, denominator = metric["numerator"], metric["denominator"]
        if type(numerator) is not int or type(denominator) is not int or not 0 <= numerator <= denominator or denominator == 0:
            raise ValueError(f"指标 {name} 须提供整数分子及正分母")
    if record.get("experiment"):
        _identifier(record["experiment"]["id"])


def _bootstrap(control: list[float], variant: list[float], paired: bool) -> tuple[float, float]:
    rng = random.Random(302117)
    estimates = []
    if paired:
        differences = [b - a for a, b in zip(control, variant)]
        estimates = [mean(rng.choices(differences, k=len(differences))) for _ in range(2000)]
    else:
        for _ in range(2000):
            estimates.append(mean(rng.choices(variant, k=len(variant))) - mean(rng.choices(control, k=len(control))))
    estimates.sort()
    return estimates[50], estimates[1949]


def evaluate_plan(
    plan: dict[str, Any], records: list[dict[str, Any]], registered_at: str | None,
) -> dict[str, Any]:
    validate_plan(plan)
    timestamp = _timestamp(registered_at) if registered_at else None
    lo, hi = map(float, plan["duration_band_sec"])
    groups: dict[str, list[dict[str, Any]]] = {"control": [], "variant": []}
    seen_videos: set[str] = set()
    excluded = 0
    for row in records:
        trial = row.get("experiment") or {}
        if trial.get("id") != plan["id"]:
            continue
        arm = trial.get("arm")
        compatible = (
            arm in groups and row.get("track", "store") == plan["track"]
            and str(row.get("platform")).casefold() == plan["platform"].casefold()
            and row.get("traffic_source") == plan["traffic_source"]
            and row.get("observation_hours") is not None
            and float(row["observation_hours"]) == float(plan["observation_hours"])
            and row.get("duration_sec") is not None and lo <= float(row["duration_sec"]) <= hi
            and trial.get("variable") == plan["variable"]
            and trial.get("value") == plan[f"{arm}_value"]
            and plan["primary_metric"] in (row.get("metrics") or {})
            and str(row.get("video_id")) not in seen_videos
            and (not timestamp or (row.get("published_at") and _timestamp(row["published_at"]) >= timestamp))
        )
        if not compatible:
            excluded += 1
            continue
        try:
            validate_snapshot(row)
        except ValueError:
            excluded += 1
            continue
        seen_videos.add(str(row["video_id"]))
        groups[arm].append(row)

    matched = plan["design"] == "matched"
    if matched:
        pairs: dict[str, dict[str, list[dict[str, Any]]]] = {}
        for arm, rows in groups.items():
            for row in rows:
                key = row["experiment"].get("pair_id")
                if key:
                    pairs.setdefault(str(key), {"control": [], "variant": []})[arm].append(row)
        compare_pairs = [pair for _, pair in sorted(pairs.items())
                         if len(pair["control"]) == len(pair["variant"]) == 1]
        excluded += sum(map(len, groups.values())) - len(compare_pairs) * 2
        groups = {arm: [pair[arm][0] for pair in compare_pairs] for arm in groups}

    rates = {}
    for arm, rows in groups.items():
        metrics = [row["metrics"][plan["primary_metric"]] for row in sorted(rows, key=lambda row: str(row["video_id"]))] if not matched else [
            row["metrics"][plan["primary_metric"]] for row in rows
        ]
        rates[arm] = [m["numerator"] / m["denominator"] for m in metrics]
    counts = {arm: len(values) for arm, values in rates.items()}
    evidence = {
        "plan": plan, "registered_at": registered_at, "units": counts, "excluded_snapshots": excluded,
        "included": {arm: sorted((str(row["video_id"]), row["metrics"][plan["primary_metric"]]) for row in rows)
                     for arm, rows in groups.items()},
        "method": "paired video bootstrap" if matched else "video-level bootstrap",
        "basis": "descriptive matched comparison" if matched else "operator-declared random assignment",
        "status": "INSUFFICIENT",
    }
    if min(counts.values()) >= plan["min_units_per_arm"]:
        effect = mean(rates["variant"]) - mean(rates["control"])
        interval = _bootstrap(rates["control"], rates["variant"], matched)
        evidence.update(effect=effect, interval_95=list(interval),
                        status="CANDIDATE" if interval[0] >= float(plan["min_effect"]) else "INCONCLUSIVE")
    evidence["candidate_id"] = _fingerprint(evidence)[:20]
    evidence["activation_allowed"] = bool(timestamp and plan.get("parameter") and evidence["status"] == "CANDIDATE")
    return evidence


def refresh_candidates(log_dir: Path, records: list[dict[str, Any]], track: str) -> list[dict[str, Any]]:
    out = []
    for path in sorted((log_dir / "experiment_plans").glob("*.json")):
        registered = read_json(path)
        if registered["plan"]["track"] == track:
            candidate = evaluate_plan(registered["plan"], records, registered["registered_at"])
            write_json(log_dir / "candidates" / f"{candidate['candidate_id']}.json", candidate)
            out.append(candidate)
    return out


def activate_candidate(log_dir: Path, records: list[dict[str, Any]], candidate_id: str) -> Path:
    candidate = read_json(log_dir / "candidates" / f"{_identifier(candidate_id)}.json")
    plan = candidate["plan"]
    registered = read_json(log_dir / "experiment_plans" / f"{_identifier(plan['id'])}.json")
    current = evaluate_plan(registered["plan"], records, registered["registered_at"])
    if current["candidate_id"] != candidate_id or not current["activation_allowed"]:
        raise ValueError("候选版本已失效或证据不足，请重新生成复盘")
    profile_path = log_dir / f"account_profile_{plan['track']}.json"
    profile = read_json(profile_path) if profile_path.is_file() else {"track": plan["track"]}
    if profile.get("active_candidate") == candidate_id:
        return profile_path
    if profile.get("active_candidate") and str(profile.get("platform") or "").casefold() != str(plan["platform"]).casefold():
        raise ValueError("当前配置属于其他平台，需要独立账号配置")
    if profile_path.is_file():
        write_json(log_dir / "profile_history" / f"{plan['track']}_{_fingerprint(profile)[:20]}.json", profile)
    profile.update({
        plan["parameter"]: plan["variant_value"],
        "sample_sufficient": True, "active_candidate": candidate_id, "platform": plan["platform"],
        "activated_at": datetime.now(timezone.utc).isoformat(),
    })
    write_json(profile_path, profile)
    return profile_path

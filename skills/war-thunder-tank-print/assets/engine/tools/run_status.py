"""Report the real outcome of a pipeline run from its run.json.

Use this instead of trusting echoed text: a hard-coded "exit 0" in a wrapper
cannot turn a failed run green here.

Exit codes: 0 completed, 1 failed, 3 still running or unreadable.
Run: python tools/run_status.py [--run logs/pipeline_.../run.json]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, help="run.json of one run (default: logs/latest_run.json)")
    args = parser.parse_args(argv)
    path = args.run or PROJECT / "logs" / "latest_run.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        print(json.dumps({"status": "unknown", "error": f"{path}: {error}"}, ensure_ascii=True))
        return 3
    failed = [e["stage"] for e in data.get("events", []) if e.get("status") == "failed"]
    summary = {k: data.get(k) for k in ("status", "requested_stage", "vehicle", "engine_snapshot", "updated_utc",
                                        "geometry_passed", "combine_status", "deliverable",
                                        "deliverable_sha256", "review_flags", "error", "run_json")}
    summary["failed_stages"] = failed
    summary["skipped"] = [e for e in data.get("events", []) if e.get("status") == "skipped"]
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    if data.get("status") == "completed" and not failed:
        return 0
    return 1 if data.get("status") == "failed" or failed else 3


if __name__ == "__main__":
    raise SystemExit(main())

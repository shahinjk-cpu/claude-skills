#!/usr/bin/env python3
"""route-stats.py: summarise metrics/parts.tsv per task type and model, to guide routing.

Usage: route-stats.py metrics/parts.tsv
Columns: date lane part task_type grade model attempts verdict p1_count cost_usd minutes_to_merge escaped
"""
import csv, sys
from collections import defaultdict


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    groups = defaultdict(list)
    with open(sys.argv[1], encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            groups[(row["task_type"], row["model"])].append(row)
    head = ("task_type", "model", "parts", "first_pass", "avg_attempts", "p1_per_part",
            "avg_cost", "cost_per_accepted", "avg_minutes", "escaped")
    print("\t".join(head))
    for (task, model), rows in sorted(groups.items()):
        n = len(rows)
        accepted = [row for row in rows if row["verdict"] in ("PASS", "PASS WITH FOLLOW-UPS", "none")]
        first = sum(1 for row in accepted if num(row["attempts"]) == 1 and num(row["p1_count"]) == 0)
        cost = sum(num(r["cost_usd"]) for r in rows)
        print("\t".join([
            task, model, str(n), "%.0f%%" % (100.0 * first / n),
            "%.1f" % (sum(num(r["attempts"]) for r in rows) / n),
            "%.2f" % (sum(num(r["p1_count"]) for r in rows) / n),
            "%.2f" % (cost / n), "%.2f" % (cost / len(accepted)) if accepted else "n/a",
            "%.0f" % (sum(num(r["minutes_to_merge"]) for r in rows) / n),
            str(int(sum(num(r["escaped"]) for r in rows))),
        ]))


if __name__ == "__main__":
    main()

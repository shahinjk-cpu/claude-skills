"""Regenerate the placement and CTA tables in SPEC.md and references/placements.md
from assets/placements.json. Run after editing placements.json."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metaads  # noqa: E402

cfg = metaads.load_placements()
R = cfg["ratios"]


def rn(x):
    return metaads.ratio_name(x, R)


def rule_txt(r):
    lo, hi = rn(r["native_min"]), rn(r["native_max"])
    span = lo if lo == hi else f"{lo} – {hi}"
    return f"{span} native (ideal {rn(r['ideal'])}); else {r.get('outside', 'crop')}"


rows = ["| ID | Placement | Formats | Media fit | Primary text | Headline | Description | Safe zone |",
        "|---|---|---|---|---|---|---|---|"]
for p in cfg["placements"]:
    m = p["media"]
    if "default" in m:
        fit = rule_txt(m["default"])
    else:
        fit = "<br>".join(f"{k}: {rule_txt(v)}" for k, v in m.items())
    t = p.get("text", {})
    def tx(f):
        c = t.get(f) or {}
        if not c.get("show", f == "primary_text"):
            return "not shown"
        bits = []
        if c.get("chars"):
            bits.append(f"≤{c['chars']} rec.")
        if c.get("lines"):
            bits.append(f"{c['lines']} lines then “{c.get('more', '…')}”")
        return ", ".join(bits) or "shown"
    sz = p.get("safe_zone")
    szt = f"top {int(sz['top']*100)}%, bottom {int(sz['bottom']*100)}%, sides {int(sz['left']*100)}%" if sz else "–"
    rows.append(f"| `{p['id']}` | {p['name']} | {', '.join(p['formats'])} | {fit} | {tx('primary_text')} | {tx('headline')} | {tx('description')} | {szt} |")
placements_table = "\n".join(rows)

cta_rows = ["| Code | Button label |", "|---|---|"] + [f"| `{k}` | {v} |" for k, v in cfg["cta"].items()]
cta_table = "\n".join(cta_rows)


def splice(path, name, body):
    p = metaads.SKILL_DIR / path
    s = p.read_text(encoding="utf-8")
    pat = re.compile(rf"(<!-- BEGIN:{name}[^>]*-->)(.*?)(<!-- END:{name} -->)", re.S)
    if not pat.search(s):
        return
    s = pat.sub(lambda m: m.group(1) + "\n" + body + "\n" + m.group(3), s)
    p.write_text(s, encoding="utf-8")
    print(f"updated {name} table in {path}")


splice("SPEC.md", "placements", placements_table)
splice("SPEC.md", "cta", cta_table)
splice("references/placements.md", "placements", placements_table)

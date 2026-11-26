"""Validate an ads.json and report what each ad x placement needs.

Usage:
    python check.py path/to/ads.json [--out DIR] [--quiet]

Writes inventory.json (for agents) and inventory.md (for people) into DIR
(default: next to ads.json) and prints a short summary. Exit code 1 if the
spec has errors that block rendering. Never modifies the spec.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import metaads  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def run(spec_path, out_dir=None, quiet=False):
    spec, p, rep = metaads.load_spec(spec_path)
    if spec is None:
        for e in rep.errors:
            print(f"ERROR {e['where']}: {e['message']}")
        return None, None, rep
    res = metaads.resolve(spec, p, rep)
    inv = metaads.inventory(res, rep)
    out = Path(out_dir) if out_dir else p.parent
    out.mkdir(parents=True, exist_ok=True)
    (out / "inventory.json").write_text(json.dumps(inv, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "inventory.md").write_text(metaads.inventory_md(res, inv), encoding="utf-8")
    if not quiet:
        summarize(res, inv, out)
    return res, inv, rep


def summarize(res, inv, out):
    c = inv["counts"]
    print(f"{len(res['ads'])} ads x {len(res['placements'])} placements: "
          f"{c.get('actual',0)} actual, {c.get('simulated',0)} simulated, "
          f"{c.get('not_eligible',0)} not eligible, {c.get('excluded',0)} excluded")
    if inv["errors"]:
        print(f"\n{len(inv['errors'])} ERROR(S) - fix before rendering:")
        for e in inv["errors"][:40]:
            print(f"  {e['where']}: {e['message']}")
    if inv["warnings"]:
        print(f"\n{len(inv['warnings'])} warning(s):")
        for w in inv["warnings"][:20]:
            print(f"  {w['where']}: {w['message']}")
        if len(inv["warnings"]) > 20:
            print("  ... see inventory.md")
    if inv["unlock"]:
        print("\nTop unlocks:")
        for u in inv["unlock"][:5]:
            print(f"  - {u['text']}")
    print(f"\nWrote {out / 'inventory.md'} and inventory.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--out")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    _, inv, rep = run(a.spec, a.out, a.quiet)
    sys.exit(1 if rep.errors else 0)

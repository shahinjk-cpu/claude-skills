#!/usr/bin/env python3
"""Backtest the desk's exact trade on each shortlist name, on its last ~60 sessions.

For every past session of every ticker, the rule the desk trades:

  entry   a buy-stop one cent over the opening-range high, live from no_entries_before
          (9:45) to no_entries_after (15:30); it fills at that price, or at the bar's open
          if the bar opens above it (skipped if that open is more than 1 % over: the desk
          never chases further)
  stop    the opening-range low, but never closer to the entry than 0.25 x the daily ATR
          (ATR of the 14 sessions before)
  T1      half the shares at entry + 1R; the other half's stop moves to the entry
  T2      the other half at entry + kR, for k in 2, 3, 4 (each tested; the best kept)
  close   whatever is left is sold at 15:55

Bars are 5 minutes, so the order of events inside one bar is unknown. Every tie is read
against the trade: the stop before any target in the same bar, no target on the fill bar.

After the close, run it on tomorrow's shortlist with --drop-losers: names whose best k lost
money on average are dropped, the rest ranked best first, and names with too few trades kept
at the end, marked thin.

Usage (from the project root):
    python backtest.py --shortlist trader/shortlist.json --drop-losers
    python backtest.py --symbols PDD,WMT --json
    python backtest.py --symbols PDD --offline-dir tests/fixtures/backtest

Paper research only: a past average is not a forecast, and real fills are worse.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "trade-scout"))
import features  # noqa: E402

OPEN = 9 * 60 + 30
KS = (2.0, 3.0, 4.0)
MIN_TRADES = 5
MAX_CHASE = 0.01


def hm(s: str) -> int:
    h, m = s.split(":")
    return int(h) * 60 + int(m)


def atr_before(days: dict[str, list], date: str, lookback: int = 14) -> float | None:
    """Daily ATR(14) from the full sessions before `date` (5-minute bars rolled up)."""
    trs, prev = [], None
    for d in sorted(days):
        if d >= date or len(days[d]) < 70:
            continue
        bars = days[d]
        hi, lo, cl = max(b[2] for b in bars), min(b[3] for b in bars), bars[-1][4]
        trs.append(hi - lo if prev is None else max(hi - lo, abs(hi - prev), abs(lo - prev)))
        prev = cl
    trs = trs[-lookback:]
    return sum(trs) / len(trs) if len(trs) >= 5 else None


def session_trade(
    bars: list,
    atr: float,
    k: float,
    or_minutes: int = 5,
    min_stop_atr: float = 0.25,
    entry_from: str = "09:45",
    entry_until: str = "15:30",
    flat_by: str = "15:55",
    max_chase: float = MAX_CHASE,
) -> dict[str, Any] | None:
    """One session's trade, or None if the buy-stop never filled (or would have chased)."""
    or_end = OPEN + or_minutes
    rng = [b for b in bars if b[0] < or_end]
    if len(rng) < max(1, or_minutes // 5):
        return None
    level = max(b[2] for b in rng)
    or_low = min(b[3] for b in rng)
    trigger = round(level + 0.01, 2)
    start, until, flat = hm(entry_from), hm(entry_until), hm(flat_by)
    fill_i = next(
        (
            i
            for i, b in enumerate(bars)
            if b[0] >= max(or_end, start) and b[0] < until and b[2] >= trigger
        ),
        None,
    )
    if fill_i is None:
        return None
    fb = bars[fill_i]
    fill = max(trigger, fb[1])
    if fill > trigger * (1 + max_chase):
        return None
    stop = math.floor(min(or_low, fill - min_stop_atr * atr) * 100) / 100
    r = fill - stop
    if r <= 0:
        return None
    t1, t2 = fill + r, fill + k * r
    trade = {"date": "", "time": f"{fb[0] // 60}:{fb[0] % 60:02d}", "entry": round(fill, 2)}
    trade |= {"stop": stop, "t1": round(t1, 2), "t2": round(t2, 2)}
    if fb[3] <= stop:  # the fill bar already traded through the stop
        return trade | {"r": -1.0, "how": "stop on the fill bar"}

    half1 = half2 = None  # R each half made, once closed
    cur_stop = stop
    for b in bars[fill_i + 1 :]:
        if b[0] >= flat:
            px = b[1]
            half1 = (px - fill) / r if half1 is None else half1
            half2 = (px - fill) / r if half2 is None else half2
            break
        if b[3] <= cur_stop:  # stop first: the worst reading of the bar
            out = (cur_stop - fill) / r
            half1 = out if half1 is None else half1
            half2 = out if half2 is None else half2
            break
        if half1 is None and b[2] >= t1:
            half1, cur_stop = 1.0, fill  # T1: half off, the rest to breakeven
            if b[3] <= cur_stop:  # the same bar also traded back to the entry: read it so
                half2 = 0.0
                break
        if half1 is not None and b[2] >= t2:
            half2 = k
            break
    else:  # ran out of bars (early close): out at the last close
        px = bars[-1][4]
        half1 = (px - fill) / r if half1 is None else half1
        half2 = (px - fill) / r if half2 is None else half2
    total = 0.5 * half1 + 0.5 * half2
    how = (
        "T1 then T2"
        if half2 == k
        else "T1 then breakeven"
        if half1 == 1.0 and abs(half2) < 1e-9
        else "T1 then the close"
        if half1 == 1.0
        else "stop"
        if total <= -0.999
        else "the close"
    )
    return trade | {"r": round(total, 3), "how": how}


def stats(trades: list[dict[str, Any]]) -> dict[str, Any]:
    rs = [t["r"] for t in trades]
    if not rs:
        return {"n": 0, "avg_r": 0.0, "win_rate": 0.0, "total_r": 0.0, "max_dd_r": 0.0}
    peak = cum = dd = 0.0
    for x in rs:
        cum += x
        peak = max(peak, cum)
        dd = min(dd, cum - peak)
    return {
        "n": len(rs),
        "avg_r": round(sum(rs) / len(rs), 3),
        "win_rate": round(sum(1 for x in rs if x > 0) / len(rs), 3),
        "total_r": round(sum(rs), 2),
        "max_dd_r": round(dd, 2),
    }


def backtest_symbol(chart: dict[str, Any], symbol: str, **rule: Any) -> dict[str, Any]:
    days = features.sessions(chart)
    by_k: dict[str, Any] = {}
    for k in KS:
        trades = []
        for d in sorted(days):
            atr = atr_before(days, d)
            if atr is None:
                continue
            t = session_trade(days[d], atr, k, **rule)
            if t:
                trades.append(t | {"date": d})
        by_k[f"{k:g}R"] = {"stats": stats(trades), "trades": trades}
    # Best average R; a tie goes to the nearer T2, which fills more often.
    best = max(by_k, key=lambda key: (by_k[key]["stats"]["avg_r"], -float(key[:-1])))
    return {
        "symbol": symbol,
        "sessions": len(days),
        "best_t2": best,
        "best": by_k[best]["stats"],
        "by_t2": {key: v["stats"] for key, v in by_k.items()},
        "trades": by_k[best]["trades"],
    }


def verdict(res: dict[str, Any], min_trades: int = MIN_TRADES) -> str:
    if res["best"]["n"] < min_trades:
        return "thin"
    return "keep" if res["best"]["avg_r"] > 0 else "drop"


def rank(results: list[dict[str, Any]], min_trades: int = MIN_TRADES) -> list[dict[str, Any]]:
    """Kept names best first, thin ones after (fewest trades last), dropped ones out."""
    for r in results:
        r["verdict"] = verdict(r, min_trades)
    kept = sorted((r for r in results if r["verdict"] == "keep"), key=lambda r: -r["best"]["avg_r"])
    thin = sorted((r for r in results if r["verdict"] == "thin"), key=lambda r: -r["best"]["n"])
    return kept + thin


def get_chart(symbol: str, offline_dir: Path | None) -> dict[str, Any]:
    if offline_dir:
        for name in (f"{symbol}.json.gz", f"{symbol}.json"):
            if (offline_dir / name).exists():
                return features.load_chart(offline_dir / name)
        raise RuntimeError(f"no offline chart for {symbol} in {offline_dir}")
    time.sleep(0.3)  # polite to Yahoo
    return features.fetch_chart(symbol, "60d", "5m")


def read_symbols(shortlist: Path) -> tuple[dict[str, Any], list[str]]:
    doc = json.loads(shortlist.read_text(encoding="utf-8-sig"))
    return doc, [h["symbol"].upper() for h in doc.get("hits", [])]


def report(results: list[dict[str, Any]], ranked: list[dict[str, Any]], when: str) -> str:
    lines = [f"# Backtest of the desk's trade, {when}", ""]
    lines.append(
        "Buy-stop over the opening-range high; stop at the range low, at least 0.25x ATR; "
        "half at +1R then breakeven; half at the best of 2R/3R/4R; out at 15:55. "
        "Ties inside a bar go against the trade."
    )
    lines += ["", "| # | ticker | T2 | trades | avg R | win | total R | max DD R | verdict |"]
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    order = ranked + [r for r in results if r not in ranked]
    for i, r in enumerate(order, 1):
        b = r.get("best") or {}
        if "error" in r:
            lines.append(f"| {i} | {r['symbol']} | - | - | - | - | - | - | error: {r['error']} |")
            continue
        lines.append(
            f"| {i} | {r['symbol']} | {r['best_t2']} | {b['n']} | {b['avg_r']:+.2f} | "
            f"{b['win_rate']:.0%} | {b['total_r']:+.1f} | {b['max_dd_r']:.1f} | {r['verdict']} |"
        )
    lines += ["", "A past average on ~60 sessions is not a forecast. Paper only."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--shortlist", type=Path, help="trader/shortlist.json")
    g.add_argument("--symbols", help="comma-separated tickers")
    ap.add_argument("--drop-losers", action="store_true", help="rewrite the shortlist: ranked")
    ap.add_argument("--min-trades", type=int, default=MIN_TRADES)
    ap.add_argument("--config", type=Path, default=Path("trader/config.json"))
    ap.add_argument("--out-dir", type=Path, default=Path("trader/backtest"))
    ap.add_argument("--offline-dir", type=Path, help="saved 60-day charts, SYM.json(.gz)")
    ap.add_argument("--refresh", action="store_true", help="ignore today's cached results")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    cfg = json.loads(a.config.read_text(encoding="utf-8")) if a.config.exists() else {}
    sc = cfg.get("scout") or {}
    rule = {
        "or_minutes": int(sc.get("or_minutes", 5)),
        "min_stop_atr": float(sc.get("min_stop_atr", 0.25)),
        "entry_from": cfg.get("no_entries_before", "09:45"),
        "entry_until": cfg.get("no_entries_after", "15:30"),
        "flat_by": cfg.get("flat_by", "15:55"),
    }
    doc, symbols = read_symbols(a.shortlist) if a.shortlist else (None, [])
    if a.symbols:
        symbols = [s.strip().upper() for s in a.symbols.split(",") if s.strip()]
    today = dt.datetime.now(features.NY).date().isoformat()
    cache = a.out_dir / today
    cache.mkdir(parents=True, exist_ok=True)

    results = []
    for sym in symbols:
        f = cache / f"{sym}.json"
        if f.exists() and not a.refresh and not a.offline_dir:
            cached = json.loads(f.read_text(encoding="utf-8"))
            if cached.get("rule") == rule:  # same day AND same rule, or it is run again
                results.append(cached)
                continue
        try:
            res = backtest_symbol(get_chart(sym, a.offline_dir), sym, **rule) | {"rule": rule}
        except (OSError, RuntimeError, ValueError) as e:
            results.append({"symbol": sym, "error": str(e)[:160]})
            continue
        f.write_text(json.dumps(res) + "\n", encoding="utf-8")
        results.append(res)

    ok = [r for r in results if "error" not in r]
    ranked = rank(ok, a.min_trades)
    md = report(results, ranked, today)
    (cache / "summary.md").write_text(md, encoding="utf-8")
    summary = {
        "date": today,
        "rule": rule,
        "ranked": [
            {"symbol": r["symbol"], "verdict": r["verdict"], "t2": r["best_t2"], **r["best"]}
            for r in ranked
        ],
        "dropped": [r["symbol"] for r in ok if r["verdict"] == "drop"],
        "errors": {r["symbol"]: r["error"] for r in results if "error" in r},
    }
    (cache / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    if a.drop_losers and a.shortlist and doc is not None:
        info = {r["symbol"]: r for r in ranked}
        old = {h["symbol"].upper(): h for h in doc.get("hits", [])}
        errored = [s for s in symbols if s in summary["errors"]]  # no data: kept, unranked
        doc["hits"] = [
            old[s]
            | {
                "backtest": {
                    "verdict": info[s]["verdict"],
                    "t2": info[s]["best_t2"],
                    **{k: info[s]["best"][k] for k in ("n", "avg_r", "win_rate")},
                }
            }
            for s in info
            if s in old
        ] + [old[s] for s in errored if s in old]
        doc["dropped"] = summary["dropped"]
        doc["backtest"] = str(cache / "summary.json")
        a.shortlist.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

    if a.json:
        print(json.dumps(summary, indent=2))
    else:
        print(md)
        if a.drop_losers and a.shortlist:
            print(
                f"Shortlist rewritten: {len(doc['hits'])} kept, "
                f"{len(summary['dropped'])} dropped ({', '.join(summary['dropped']) or 'none'})."
            )
    return 0 if ranked else 1


if __name__ == "__main__":
    sys.exit(main())

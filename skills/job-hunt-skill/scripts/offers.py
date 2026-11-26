#!/usr/bin/env python3
"""Compare job offers on net monthly pay, benefits and currency risk. Estimates, not tax advice.

Offers file: <workspace>/interview/offers.json (example in the skill's templates/interview/offers.json):
  [{"name": "Acme CLT", "contract": "employee_local", "amount": 25000, "currency": "BRL", "per": "month",
    "benefitsMonthly": 1500},
   {"name": "Globex contract", "contract": "contractor", "amount": 7500, "currency": "EUR", "per": "month",
    "equity": "0.05% options, 4-year vest", "billableMonths": 12}]
contract: employee_local | pj_local | contractor | eor.  per: month | year | hour.

Usage:
  python3 offers.py --workspace WS [--file offers.json] [--no-history]
For offers paid in another currency it shows net pay if that currency moves -20..+20%, and at the lowest and
highest rate of the last 12 months (ECB rates via frankfurter.app). Equity is listed but never added to totals.
"""
import argparse, datetime as dt, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import load_config, read_json  # noqa: E402
import netpay  # noqa: E402
import scan  # noqa: E402
from filter import fx_table  # noqa: E402

SHOCKS = (-0.20, -0.10, 0.10, 0.20)


def monthly_gross(o, cfg):
    per = (o.get("per") or "month").lower()
    amt = float(o["amount"])
    if per.startswith("hour"):
        return amt * cfg["pay"]["hoursPerMonth"], "rate"
    if per.startswith("day"):
        return amt * cfg["pay"]["hoursPerMonth"] / 8, "rate"
    if per.startswith("week"):
        return amt * 4.33, "rate"
    if per.startswith("year") or per.startswith("annual"):
        return amt / 12, "year"
    if not per.startswith("month"):
        raise SystemExit(f"offer {o.get('name')!r}: per must be hour, day, week, month or year (got {per!r})")
    return amt, ("rate" if o.get("contract") in ("contractor", "pj_local") else None)


def history_range(cur, home, today=None):
    """(min, max) of the cur->home rate over the last 12 months, or None."""
    today = today or dt.date.today()
    d = scan.getj(f"https://api.frankfurter.app/{today - dt.timedelta(days=365)}..{today}?from={cur}&to={home}")
    vals = [v.get(home) for v in ((d or {}).get("rates") or {}).values() if v.get(home)]
    return (min(vals), max(vals)) if vals else None


def net(g, contract, person, basis):
    r = netpay.net_monthly(g, contract, person, basis)
    return r["net"] if r and r.get("net") is not None else None


def breakeven_clt(target_net, person):
    """Monthly CLT/local-employee gross whose net equals target_net (bisection)."""
    lo, hi = 0.0, max(1000.0, target_net * 4)
    if (net(hi, "employee_local", person, None) or 0) < target_net:
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        if (net(mid, "employee_local", person, None) or 0) < target_net:
            lo = mid
        else:
            hi = mid
    return round(hi)


def compare(offers, cfg, fx, history=True, today=None):
    home = cfg["profile"]["currency"].upper()
    out = []
    for o in offers:
        person = dict(cfg["person"])
        if o.get("billableMonths"):
            person["contractorBillableMonths"] = o["billableMonths"]
        cur = (o.get("currency") or home).upper()
        if cur not in fx:
            out.append({"name": o["name"], "error": f"no exchange rate for {cur}"})
            continue
        g_cur, basis = monthly_gross(o, cfg)
        rate = fx[cur]
        g = g_cur * rate
        r = netpay.net_monthly(g, o["contract"], person, basis)
        n = r["net"] if r and r.get("net") is not None else None
        ben = float(o.get("benefitsMonthly") or 0)
        row = {"name": o["name"], "contract": o["contract"], "currency": cur, "gross_home": round(g), "net": n, "benefits": round(ben),
               "total": (n + round(ben)) if n is not None else None, "deferred": (r or {}).get("detail", {}).get("fgts_deferred"),
               "equity": o.get("equity"), "assumptions": (r or {}).get("assumptions", [])}
        if cur != home and n is not None:
            row["fx"] = {f"{s:+.0%}": net(g_cur * rate * (1 + s), o["contract"], person, basis) for s in SHOCKS}
            rng = history_range(cur, home, today) if history else None
            if rng:
                row["fx_12m"] = {"rate_min": rng[0], "rate_max": rng[1], "rate_now": round(rate, 4),
                                 "net_min": net(g_cur * rng[0], o["contract"], person, basis), "net_max": net(g_cur * rng[1], o["contract"], person, basis)}
        if o["contract"] != "employee_local" and n is not None:
            row["clt_breakeven_gross"] = breakeven_clt(n, person)
        out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--file", help="offers JSON (default: <workspace>/interview/offers.json)")
    ap.add_argument("--no-history", action="store_true", help="skip the 12-month exchange-rate range")
    a = ap.parse_args()
    ws = os.path.abspath(os.path.expanduser(a.workspace))
    cfg = load_config(ws, require_queries=False)
    path = a.file or os.path.join(ws, "interview", "offers.json")
    offers = read_json(path)
    home = cfg["profile"]["currency"].upper()
    rows = compare(offers, cfg, fx_table(cfg), not a.no_history)
    print(f"Offers compared in {home}/month (estimates, not tax advice)\n")
    print(f"{'offer':30} {'contract':15} {'gross':>9} {'net':>9} {'benefits':>9} {'total':>9}  local-employee gross for same net")
    for r in rows:
        if r.get("error"):
            print(f"{r['name'][:30]:30} {r['error']}")
            continue
        f = lambda v: f"{v:,}" if isinstance(v, (int, float)) else "-"  # noqa: E731
        print(f"{r['name'][:30]:30} {r['contract']:15} {f(r['gross_home']):>9} {f(r['net']):>9} {f(r['benefits']):>9} {f(r['total']):>9}  {f(r.get('clt_breakeven_gross'))}")
    for r in rows:
        if r.get("error"):
            continue
        extra = []
        if r.get("deferred"):
            extra.append(f"FGTS {r['deferred']:,}/month deferred (not in net)")
        if r.get("equity"):
            extra.append(f"equity: {r['equity']} (uncertain, not in totals)")
        if r.get("fx"):
            extra.append(f"{r['currency']} moves: " + ", ".join(f"{k} → {v:,}" for k, v in r["fx"].items() if v is not None))
        if r.get("fx_12m"):
            x = r["fx_12m"]
            extra.append(f"last 12 months {r['currency']}/{home} {x['rate_min']:.2f}–{x['rate_max']:.2f} (now {x['rate_now']:.2f}): net {x['net_min']:,}–{x['net_max']:,}")
        if extra or r["assumptions"]:
            print(f"\n{r['name']}:")
            for e in extra:
                print("   ", e)
            for s in r["assumptions"]:
                print("    -", s)


if __name__ == "__main__":
    main()

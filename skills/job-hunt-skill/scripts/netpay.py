#!/usr/bin/env python3
"""Net monthly pay estimates, so a CLT salary, a local PJ rate and a foreign contract can be compared.

All amounts are in the user's home currency per month. Results are estimates for comparing offers,
not tax advice. Country rules live in netpay/<CC>.json (data, with sources and a validity date);
countries without a module use the user's flat rates (person.netRates).

Contracts:
  employee_local      local payroll (e.g. Brazilian CLT)
  eor                 employer-of-record: a local payroll entity employs you (treated as employee_local)
  pj_local            your company invoices a local client
  contractor          your company (or you) invoices a foreign client: export of services
  employee_foreign    foreign payroll (e.g. US W-2): usually impossible without living there -> no estimate

Usage (CLI, for checking an offer):
  python3 netpay.py --workspace WS --gross 25000 --contract employee_local
  python3 netpay.py --workspace WS --gross 52000 --contract contractor
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
_MODELS = {}


def _read(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def load_model(cc):
    cc = (cc or "").upper()
    if cc and cc not in _MODELS:
        p = os.path.join(HERE, "netpay", f"{cc}.json")
        _MODELS[cc] = _read(p) if os.path.exists(p) else None
    return _MODELS.get(cc)


# ------------------------------------------------------------------ Brazil
def br_inss_employee(m, g):
    tot, lo = 0.0, 0.0
    for hi, rate in m["inssEmployee"]:
        if g > lo:
            tot += (min(g, hi) - lo) * rate
        lo = hi
    return round(tot, 2)


def br_irrf(m, gross, inss):
    """Monthly IRRF on a salary or pró-labore, with the 2026 reduction (Lei 15.270/2025)."""
    base = gross - max(inss, m["irrfSimplifiedDiscount"])
    tax = 0.0
    for hi, rate, ded in m["irrf"]:
        if hi is None or base <= hi:
            tax = max(0.0, base * rate - ded)
            break
    r = m["irrfReduction"]
    if gross <= r["fullUpTo"]:
        tax = max(0.0, tax - min(tax, r["maxFull"]))
    elif gross <= r["phaseOutUntil"]:
        tax = max(0.0, tax - max(0.0, r["a"] - r["b"] * gross))
    return round(tax, 2)


def br_clt(m, gross):
    inss = br_inss_employee(m, gross)
    irrf = br_irrf(m, gross, inss)
    monthly = gross - inss - irrf
    yearly_factor = (m["clt"]["salariesPerYear"] + m["clt"]["vacationBonus"]) / 12  # 13th salary + 1/3 vacation bonus
    return {"net": round(monthly * yearly_factor), "basis": "employee_local",
            "detail": {"inss": inss, "irrf": irrf, "monthly_paycheck": round(monthly), "fgts_deferred": round(gross * m["fgtsRate"])},
            "assumptions": ["13th salary + 1/3 vacation bonus spread over 12 months",
                            "no dependants; simplified discount if larger than INSS",
                            "FGTS (8%) is extra but locked: shown apart, not in net"]}


def br_simples(m, monthly_revenue, export, accountant, fx_spread):
    """Best of Anexo III (Fator R: pró-labore >= 28% of revenue) and Anexo V (pró-labore = minimum wage)."""
    s, rbt12 = m["simples"], monthly_revenue * 12
    band = next((i for i, hi in enumerate(s["bands"]) if rbt12 <= hi), None)
    if band is None:
        return None  # above the Simples ceiling: needs another regime, no estimate
    options = []
    for anexo in ("III", "V"):
        t = s[anexo]
        eff = (rbt12 * t["rates"][band] - t["deduct"][band]) / rbt12
        if export:
            eff *= 1 - t["exportExemptShare"][band]
        das = monthly_revenue * eff
        prolabore = max(m["minimumWage"], s["fatorR"] * monthly_revenue) if anexo == "III" else m["minimumWage"]
        inss = round(min(prolabore, m["inssCeiling"]) * m["inssProLaboreRate"], 2)
        irrf = br_irrf(m, prolabore, inss)
        costs = das + accountant + (monthly_revenue * fx_spread if export else 0)
        dividends = max(0.0, monthly_revenue - costs - prolabore)
        dw = m["dividendWithholding"]
        div_tax = dividends * dw["rate"] if dividends > dw["monthlyThreshold"] else 0.0
        mt, annual = m["minimumAnnualTax"], 12 * (prolabore + dividends)
        min_rate = 0.0 if annual <= mt["from"] else mt["maxRate"] if annual >= mt["full"] else mt["maxRate"] * (annual - mt["from"]) / (mt["full"] - mt["from"])
        min_tax = max(0.0, min_rate * annual - 12 * (irrf + div_tax)) / 12
        net = prolabore - inss - irrf + dividends - div_tax - min_tax
        options.append({"anexo": anexo, "net": round(net), "das_rate": round(eff, 4), "das": round(das), "prolabore": round(prolabore),
                        "inss": inss, "irrf": irrf, "dividends": round(dividends), "dividend_tax": round(div_tax), "min_annual_tax_month": round(min_tax)})
    best = max(options, key=lambda o: o["net"])
    return best, options


def br_company(m, gross, export, person):
    d = m["defaults"]
    acc = person.get("accountantMonthly", d["accountantMonthly"])
    fx = person.get("fxSpread", d["fxSpread"])
    r = br_simples(m, gross, export, acc, fx)
    if not r:
        return None
    best, options = r
    a = [f"Simples Nacional: shows the higher of Anexo III (pró-labore ≥ 28%) and Anexo V ({best['anexo']} here); both are in the detail. "
         "Choosing the regime and pró-labore is for your accountant",
         f"accountant {acc:.0f}/month" + (f", FX/transfer spread {fx:.1%}" if export else ""),
         "profits paid out as dividends; 10% withheld above 50k/month and annual minimum tax above 600k/year (Lei 15.270/2025), without the corporate-tax credit (conservative)"]
    if export:
        a.append("export of services: no ISS, PIS or Cofins in the DAS")
    return {"net": best["net"], "basis": "contractor" if export else "pj_local", "detail": {"best": best, "options": options}, "assumptions": a}


# Country registry: netpay/<CC>.json holds the data (with sources and validity dates); these functions
# hold the rules. A country needs at least "employee" (local payroll) or "company" (own company / contractor);
# anything missing falls back to the user's flat person.netRates. Guide: docs/netpay-countries.md.
COUNTRIES = {
    "BR": {"employee": br_clt, "company": br_company,
           "salaries_per_year": lambda m: m["clt"]["salariesPerYear"] + m["clt"]["vacationBonus"]},
}


# ------------------------------------------------------------------ generic
def flat(gross, contract, person):
    rates = person.get("netRates") or {}
    key = "employee" if contract in ("employee_local", "eor") else "contractor"
    rate = rates.get(key)
    if not rate:
        return None
    return {"net": round(gross * rate), "basis": contract, "detail": {"rate": rate},
            "assumptions": [f"flat {rate:.0%} of gross (person.netRates.{key}); add a country module for real tax rules"]}


def net_monthly(gross, contract, person, months_basis=None):
    """gross: monthly amount in home currency for that contract. months_basis: 'rate' when the job posted an
    hourly/daily/monthly rate (contractor billable months apply), 'year' for an annual amount."""
    if gross is None or gross <= 0:
        return None
    if contract == "employee_foreign":
        return {"net": None, "basis": contract, "detail": {}, "assumptions": ["foreign payroll: usually requires living there; no estimate"]}
    if contract in ("contractor", "pj_local") and months_basis == "rate":  # own company: unpaid time off
        bm = person.get("contractorBillableMonths", 11)
        gross = gross * bm / 12
    m = load_model(person.get("netModel"))
    funcs = COUNTRIES.get((m or {}).get("country"), {})
    out = None
    if m and funcs:
        if contract in ("employee_local", "eor") and funcs.get("employee"):
            spread = funcs.get("salaries_per_year", lambda _m: 12)(m) / 12
            out = funcs["employee"](m, gross / spread if months_basis == "year" else gross)
            if months_basis == "year" and spread != 1:
                out["assumptions"].append(f"annual amount treated as total pay: monthly salary = annual / {spread * 12:.2f}")
            if contract == "eor":
                out["assumptions"].append("assumes the posted pay becomes your local gross salary; employers often set a lower local salary")
        elif contract in ("pj_local", "contractor") and funcs.get("company"):
            out = funcs["company"](m, gross, contract == "contractor", person)
        if out:
            out["assumptions"].append(f"{m['country']} rules valid {m['validFrom']}..{m['validUntil']}; estimate, not tax advice")
    if out is None:
        out = flat(gross, contract, person)
    if out and contract in ("contractor", "pj_local") and months_basis == "rate":
        out["assumptions"].append(f"{person.get('contractorBillableMonths', 11)} billable months a year")
    return out


def scenarios(gross, contract, currency_is_home, person, months_basis=None):
    """Contracts to estimate for one job. Unknown contract: local options for home-currency pay, else foreign ones."""
    if contract and contract != "unknown":
        cs = [contract]
    elif currency_is_home:
        cs = ["employee_local", "pj_local"]
    else:
        cs = ["contractor", "eor"]
    allowed = person.get("contracts") or []
    if allowed:  # only contracts the user accepts; a known contract type is always shown
        cs = [c for c in cs if c in allowed or c == contract] or [c for c in allowed if c != "employee_foreign"] or cs
    res = {c: net_monthly(gross, c, person, months_basis) for c in cs}
    return {c: r for c, r in res.items() if r}


def main():
    sys.path.insert(0, HERE)
    from config import load_config
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--gross", type=float, required=True, help="monthly gross in home currency")
    ap.add_argument("--contract", default="unknown")
    ap.add_argument("--rate", action="store_true", help="gross is a monthly rate (apply contractor billable months)")
    a = ap.parse_args()
    cfg = load_config(os.path.abspath(os.path.expanduser(a.workspace)))
    cur = cfg["profile"]["currency"]
    for c, r in scenarios(a.gross, a.contract, True if a.contract == "unknown" else None, cfg["person"], "rate" if a.rate else None).items():
        print(f"{c}: net ≈ {cur} {r['net']:,}/month" if r["net"] is not None else f"{c}: no estimate")
        for x in r["assumptions"]:
            print("   -", x)
        print("   ", json.dumps(r["detail"], ensure_ascii=False))


if __name__ == "__main__":
    main()

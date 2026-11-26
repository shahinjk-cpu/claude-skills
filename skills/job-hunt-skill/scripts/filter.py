#!/usr/bin/env python3
"""Apply the workspace rules to a raw scan.

Usage:
    python3 filter.py --workspace PATH [--raw PATH/search/scans/raw-YYYY-MM-DD.json] [--today YYYY-MM-DD]

Rules (all configured in PATH/search/filters.md):
  relevance  -> title keywords + role words, or role words + enough description keywords
  location   -> remote only (optional), allowed regions, drop remote jobs restricted elsewhere
  ghost      -> too old, reposted over a long span, talent-pool / evergreen listings
  pay        -> monthly pay converted to home currency must reach the floor
  dedupe     -> same company + normalized title across boards
  scams      -> free-mail contacts, fees, messenger-only contact, missing company, implausible pay
Writes PATH/search/scans/results-YYYY-MM-DD.json and prints a ranked summary.
"""
import argparse, collections, datetime as dt, glob, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import load_config, write_atomic  # noqa: E402
import eligibility as EL  # noqa: E402
import netpay  # noqa: E402

GLOBAL = re.compile(r"worldwide|anywhere|global|unrestricted|all countries|any (location|country|timezone)|work from anywhere", re.I)
RESTRICT = re.compile(
    r"(?:must|need to|required to|should)\s+(?:be\s+)?(?:currently\s+)?(?:be\s+)?(?:based|located|reside|residing|live|living)\s+in\s+(?:the\s+)?([a-z .]{2,30})"
    r"|authori[sz]ed to work in (?:the\s+)?([a-z .]{2,20})"
    r"|only (?:open to |accepting )?(?:candidates|applicants) (?:based |located |residing )?in (?:the\s+)?([a-z .]{2,20})"
    r"|\b(us|usa|u\.s\.|uk|eu|europe|canada)[- ]only\b"
    r"|((?:us|u\.s\.) citizen|green card|security clearance|ts/sci|\bitar\b)", re.I)
GHOST = re.compile(r"talent pool|banco de talentos|future opportunit|evergreen|always (be )?hiring|pipeline for future|"
                   r"not an active (opening|role)|general application|expression of interest|cadastro reserva", re.I)
SCAM = re.compile(r"telegram|whatsapp|wire transfer|western union|check deposit|purchase (your own |the )?equipment|training fee|"
                  r"registration fee|application fee|pay (a|the) fee|\busdt\b|bitcoin|crypto(currency)? payment|no experience (required|needed)|"
                  r"earn up to \$|guaranteed (income|earnings)|unlimited earning|text (us|me) at", re.I)
FREEMAIL = re.compile(r"[\w.+-]+@(gmail|yahoo|hotmail|outlook|proton(mail)?|icloud|aol)\.(com|me)", re.I)


def words_re(words):
    words = [w for w in words if w]
    if not words:
        return re.compile(r"(?!x)x")
    return re.compile(r"(?:" + "|".join(r"\b" + re.escape(w).replace(r"\ ", r"[\s-]?") + r"\b" for w in words) + r")", re.I)


LEGAL = re.compile(r"\b(the|a|inc|llc|ltd|ltda|gmbh|s\.?a|plc|corp|corporation|co|bv|ag|sas|srl|spa|limited|me|eireli)\b\.?")


def company_words(name):
    """Significant words of a company name: no legal suffixes, articles or punctuation ('The Acme Co.' -> ['acme'])."""
    return re.sub(r"[^a-z0-9 ]", " ", LEGAL.sub(" ", (name or "").lower())).split()


def same_company(a, b):
    """'Acme' matches 'Acme Corp' and 'Acme Robotics' (one name starts the other); 'The X' never matches 'The Y'."""
    wa, wb = company_words(a), company_words(b)
    n = min(len(wa), len(wb))
    return n > 0 and wa[:n] == wb[:n]


def norm_title(s):
    s = (s or "").lower()
    s = re.sub(r"job id:?\s*\S+|\b[a-z]{2}\d{4,}\b", " ", s)
    # drop location/marker parentheses like "(Remote)", "(m/f/d)", "(US only)"; keep meaningful ones like "(Vision)"
    s = re.sub(r"\((?:[^)]*\b(?:remote|remoto|hybrid|h[ií]brido|on-?site|only|position|part|full)\b[^)]*|[mfwdh]\s*/\s*[mfwdh](?:\s*/\s*[mfwdhx])?|latam|emea|apac|us|usa|uk|eu|europe)\)", " ", s)
    s = re.sub(r"\b(senior|sr\.?|s[êe]nior|pleno|semi[- ]?senior|mid[- ]level|staff|principal|lead|ii+|iv|i|remote|remoto|remota)\b", " ", s)
    return re.sub(r"[^a-z0-9à-ú]+", " ", s).strip()


def fx_table(cfg):
    home = cfg["profile"]["currency"].upper()
    try:
        if os.environ.get("JOB_HUNT_OFFLINE"):
            raise RuntimeError("offline")
        out = subprocess.run(["curl", "-s", "-L", "--proto", "=https", "--proto-redir", "=https", "--max-redirs", "3", "-m", "15", "--",
                              f"https://api.frankfurter.app/latest?from={home}"], capture_output=True, text=True).stdout
        rates = json.loads(out)["rates"]
    except Exception:
        rates = cfg["fallbackFxPerCurrency"]
        if not os.environ.get("JOB_HUNT_OFFLINE"):
            have = ", ".join(sorted(rates)) or "none"
            print(f"WARNING: live exchange rates unavailable; using fallbackFxPerCurrency from filters.md ({have}). "
                  "Pay in other currencies can't be converted: those jobs show 'salary not listed' and skip the pay floor.", file=sys.stderr)
    tbl = {k.upper(): 1 / v for k, v in rates.items() if v}
    tbl[home] = 1.0
    return tbl


NUM = re.compile(r"(\d{1,3}(?:[.,]\d{3})+|\d+)([.,]\d{1,2})?(?!\d)\s*(k\b)?", re.I)


def amounts(txt):
    """Amounts in salary text: '4.000' / '4,000' -> 4000, '4.5k' -> 4500, and a trailing k covers the range ('50-60k')."""
    found = []
    for m in NUM.finditer(txt):
        v = int(re.sub(r"[.,]", "", m.group(1))) + (float("0." + m.group(2)[1:]) if m.group(2) else 0)
        found.append((v, bool(m.group(3))))
    k = any(x[1] for x in found)
    vals = [v * 1000 if (kk or (k and v < 1000)) else v for v, kk in found]
    return [v for v in vals if v > 5]


def period(txt):
    """Pay period named in salary text ('' when none)."""
    t = txt.lower()
    for per, pat in (("hour", r"hour|/h\b|\bhr\b|/hr|\bhora"), ("day", r"\bday\b|/day|daily|\bdia\b|di[áa]ria"),
                     ("week", r"week|semana"), ("year", r"year|annual|\byr\b|/y\b|\bp\.?a\.?\b|a[ñn]o\b|anual|jahr"),
                     ("month", r"month|/mo\b|m[êe]s\b|monat")):
        if re.search(pat, t):
            return per
    return ""


def monthly_pay(j, cfg, fx):
    """Return (low, high) monthly pay in home currency, or None."""
    s, hours = j.get("sal"), cfg["pay"]["hoursPerMonth"]
    vals, cur, per = [], None, ""
    if s and "text" in s:
        txt = s["text"]
        cur = "EUR" if "€" in txt else "GBP" if "£" in txt else "BRL" if "R$" in txt else "USD"
        vals, per = amounts(txt), period(txt)
    elif not s:  # no salary field: look for an amount in the home currency in the text (e.g. Brazilian "R$ 18.000")
        home = cfg["profile"]["currency"].upper()
        sym = {"BRL": r"R\$", "EUR": r"€", "GBP": r"£"}.get(home)
        m = re.search(sym + r"\s?(\d{1,3}(?:[.,]\d{3})+|\d{4,6})(?:[.,]\d{2})?(?!\d)", j.get("text", "")) if sym else None
        floor = cfg["pay"]["floorMonthly"] or 0
        if m:
            v = float(re.sub(r"[.,]", "", m.group(1)))
            if (floor * 0.1 if floor else 500) <= v <= (floor * 20 if floor else 10 ** 6):
                vals, cur, per = [v], home, "month"
    if s and "text" not in s:
        for x in (s.get("min"), s.get("max")):
            try:
                if x and float(x) > 0:
                    vals.append(float(x))
            except (TypeError, ValueError):
                pass
        cur, per = (s.get("cur") or "USD").upper(), str(s.get("per") or "").lower()
    if not vals or cur not in fx:
        return None
    lo, hi = min(vals), max(vals)
    if "hour" in per or "hr" in per:
        f = hours
    elif "day" in per:
        f = hours / 8
    elif "week" in per:
        f = 4.33
    elif "month" in per:
        f = 1
    elif "year" in per or "annual" in per:
        f = 1 / 12
    else:  # guess from magnitude (in USD terms)
        usd = hi * fx[cur] / fx.get("USD", 1)
        f = 1 / 12 if usd > 20000 else hours if usd < 300 else 1
    return round(lo * f * fx[cur]), round(hi * f * fx[cur])


def attach_net(j, cfg):
    """Net monthly range in home currency, across the plausible contracts for this job (None without a pay range
    or without a net model / net rates in the person block)."""
    person, pay = cfg["person"], j.get("pay_monthly")
    j["pay_net"], j["net_contracts"] = None, []
    if not pay or not (person.get("netModel") or person.get("netRates")):
        return None
    s = j.get("sal") or {}
    per = str(s.get("per") or s.get("text") or "").lower()
    basis = "year" if re.search(r"year|annual|\byr\b|/y\b", per) else "rate" if per else None
    home = cfg["profile"]["currency"].upper()
    at_home = (str(s.get("cur") or "").upper() == home) or j.get("source") == "Gupy" or (home == "BRL" and "R$" in per)
    lo = netpay.scenarios(pay[0], j.get("contract"), at_home, person, basis)
    hi = netpay.scenarios(pay[1], j.get("contract"), at_home, person, basis)
    nets = [r["net"] for r in list(lo.values()) + list(hi.values()) if r and r.get("net") is not None]
    if nets:
        j["pay_net"], j["net_contracts"] = (min(nets), max(nets)), sorted(hi)
    return j["pay_net"]


def classify(j, cfg, R, fx, today):
    title, text, loc = j["title"], j["text"], j["loc"]
    head = text[:3000]
    reasons, flags = [], []
    roles = cfg["roles"]

    # ---- relevance
    if R["excl_title"].search(title):
        return "irrelevant", ["excluded title word"], flags
    kw_title = bool(R["title_kw"].search(title))
    role_title = bool(R["role"].search(title))
    hits = len({m.group(0).lower() for m in R["text_kw"].finditer(text)})
    if not ((kw_title and (role_title or hits >= 1)) or (role_title and hits >= roles["minTextHits"])):
        return "irrelevant", ["not target role"], flags
    if R["excl_unless"].search(title) and not kw_title:
        return "irrelevant", ["excluded specialisation"], flags

    # ---- location
    L = cfg["location"]
    locl = loc.lower()
    if j["source"] == "RemoteRocketship":
        tw = set(re.sub(r"[^a-z0-9 ]", " ", title.lower()).split())
        locl = " ".join(w for w in locl.replace("slug:", "").split() if w not in tw and w != "remote" and not w.isdigit())
        j["loc"] = "location: " + (locl or "?")
    if j["source"] == "Gupy":
        wp = loc.split(" ")[0]
        if wp != "remote" and L["remoteOnly"] and not R["hybrid_city"].search(loc):
            reasons.append(f"{wp}, not remote")
    elif L["remoteOnly"] and re.search(r"\bonsite\b|on-site only|in[- ]office", loc, re.I) and not re.search("remote", loc, re.I):
        reasons.append("onsite")
    elif L["remoteOnly"] and j["source"].startswith("HN") and not re.search("remote", loc, re.I):
        reasons.append("not remote")
    elif L["remoteOnly"] and re.search(r"\bhybrid\b|h[íi]brido", loc, re.I) and not R["hybrid_city"].search(loc):
        reasons.append("hybrid")
    place = re.sub(r"(?:100%\s*|fully\s+)?\bremot[eo]\b|[()/|]", " ", locl)  # a bare "Remote" names no place
    stated = place.strip(" ,;-") not in ("", "?", "unrestricted") and j["source"] not in ("HN WhoIsHiring", "Gupy")
    if stated and not GLOBAL.search(locl) and not R["allowed"].search(locl) and not R["hybrid_city"].search(locl):
        reasons.append("restricted to " + locl.strip()[:40])
    m = RESTRICT.search(text)
    if m and not GLOBAL.search(locl) and not R["allowed"].search(locl):
        target = next((g for g in m.groups() if g), m.group(0))
        if not R["allowed"].search(target):
            if EL.countries(target):
                reasons.append("restricted: " + m.group(0)[:50])
            else:  # "must be located in a time zone…", "…in one of the countries where we have an entity"
                flags.append("location condition: " + m.group(0)[:60])
    if not stated and not GLOBAL.search(loc + " " + head) and not R["allowed"].search(loc + " " + head):
        if L["acceptUnstated"]:
            flags.append("location not stated: verify eligibility")
        else:
            reasons.append("location not stated")

    # ---- ghost
    G = cfg["ghost"]
    if j["posted"]:
        age = (today - dt.datetime.fromisoformat(j["posted"])).days
        j["age_days"] = age
        if age > G["maxAgeDays"]:
            reasons.append(f"open {age} days (stale)")
        elif age > G["warnAgeDays"]:
            flags.append(f"{age} days old")
    else:
        flags.append("no post date")
    gm = GHOST.search(text)
    if gm:
        reasons.append(f'talent pool / ghost ("{gm.group(0)}")')

    # ---- eligibility (advisory: flags only; hard location rules above still decide)
    el = EL.eligibility(j, cfg["person"], today)
    j["eligibility"], j["eligibility_reasons"], j["contract"] = el["verdict"], el["reasons"], el["contract"]
    if el["verdict"] in ("relocation", "no") and cfg["person"].get("residence"):
        flags.append(f"eligibility: {el['verdict']} ({el['reasons'][0]})")

    # ---- pay
    P = cfg["pay"]
    pay = monthly_pay(j, cfg, fx)
    j["pay_monthly"] = pay
    cur = cfg["profile"]["currency"]
    net = attach_net(j, cfg)
    basis = net if P.get("floorBasis") == "net" and net else pay
    label = "net" if basis is net and net else "pay"
    if basis and P["floorMonthly"]:
        if basis[1] < P["floorMonthly"]:
            reasons.append(f"{label} max ~{cur} {basis[1]:,}/mo < floor {P['floorMonthly']:,}")
        elif basis[0] < P["floorMonthly"]:
            flags.append(f"range starts below floor ({label} {cur} {basis[0]:,}–{basis[1]:,}/mo)")
    elif not pay:
        unlisted = P.get("unlisted", "flag")
        if unlisted == "hide":
            reasons.append("salary not listed")
        elif unlisted != "keep":
            flags.append("salary not listed")

    # ---- companies
    co = j["company"].lower()
    if co and any(c.lower() in co for c in cfg["excludedCompanies"] if c):
        reasons.append("company excluded")
    if co and any(r.get("company", "").lower() in co and norm_title(r.get("title", "")) == norm_title(j["title"])
                  for r in cfg["excludedRoles"]):
        reasons.append("role excluded")
    if co and R["applied"] and any(same_company(a, co) for a in R["applied"]):
        flags.append("ALREADY APPLIED / in pipeline")

    # ---- scams
    sc = []
    fm = FREEMAIL.search(text)
    if fm:
        sc.append("free-mail contact (@" + fm.group(0).split("@")[1] + ")")
    sm = SCAM.search(text)
    if sm:
        sc.append(f'keyword "{sm.group(0)}"')
    if not j["company"] or re.search(r"confidential|stealth|undisclosed|^n/?a$", j["company"], re.I):
        sc.append("company not named")
    if len(text) < 400:
        sc.append("very short description")
    if pay and P["maxPlausibleMonthly"] and pay[1] > P["maxPlausibleMonthly"]:
        sc.append("implausibly high pay")
    if sc:
        flags.append("SCAM CHECK: " + "; ".join(sc))
    return ("excluded" if reasons else "keep"), reasons, flags


def safe_search(pattern, text):
    """fit / penalizeKeywords accept regexes ("c\\+\\+", "vis[ãa]o"); an invalid one like "c++" is matched literally instead of crashing."""
    try:
        return re.search(pattern, text, re.I)
    except re.error:
        return re.search(re.escape(pattern), text, re.I)


def fit_score(j, cfg, R):
    t = (j["title"] + " " + j["text"]).lower()
    s = sum(w for p, w in cfg["fit"].items() if safe_search(p, t))
    if R["title_kw"].search(j["title"]):
        s += 4
    if R["allowed"].search(j["loc"] + " " + j["text"][:3000]):
        s += 3
    pay = j.get("pay_net") if cfg["pay"].get("floorBasis") == "net" and j.get("pay_net") else j.get("pay_monthly")
    if pay and cfg["pay"]["floorMonthly"] and pay[1] >= cfg["pay"]["floorMonthly"]:
        s += 2
    s -= 2 * sum(1 for p in cfg["penalizeKeywords"] if safe_search(p, t))
    return s


def run(ws, raw_path=None, today=None):
    cfg = load_config(ws)
    scans = os.path.join(ws, "search", "scans")
    if not raw_path:  # newest day; the main raw-DATE.json wins over a smaller same-day raw-DATE-HHMM.json
        files = glob.glob(os.path.join(scans, "raw-????-??-??*.json"))
        if not files:
            raise SystemExit(f"no raw scan in {scans}: run scan.py first")
        raw_path = max(files, key=lambda f: (os.path.basename(f)[4:14], os.path.basename(f) == f"raw-{os.path.basename(f)[4:14]}.json"))
    with open(raw_path) as fh:
        raw = json.load(fh)
    today = today or dt.datetime.now(dt.timezone.utc)
    apps_md = os.path.join(ws, "applications.md")
    applied = set()
    if os.path.exists(apps_md):
        with open(apps_md, encoding="utf-8") as fh:
            applied = {m.strip().lower() for m in re.findall(r"^\|\s*\d{4}-\d{2}(?:-\d{2})?\s*\|\s*([^|]+)\|", fh.read(), re.M)}
    R = {
        "title_kw": words_re(cfg["roles"]["titleKeywords"]),
        "role": words_re(cfg["roles"]["titleRoleWords"]),
        "text_kw": words_re(cfg["roles"]["textKeywords"]),
        "excl_title": words_re(cfg["roles"]["excludeTitle"]),
        "excl_unless": words_re(cfg["roles"]["excludeTitleUnlessKeyword"]),
        "allowed": words_re(cfg["location"]["allowed"]),
        "hybrid_city": words_re(cfg["location"]["hybridOkCities"]),
        "applied": applied,
    }
    fx = fx_table(cfg)
    for j in raw:
        j["status"], j["reasons"], j["flags"] = classify(j, cfg, R, fx, today)

    groups = collections.defaultdict(list)
    for j in raw:
        if j["status"] != "irrelevant":
            groups[((company_words(j["company"]) or [""])[0], norm_title(j["title"]))].append(j)
    final = []
    for g in groups.values():
        g.sort(key=lambda x: x["posted"] or "")
        dates = sorted({x["posted"][:10] for x in g if x["posted"]})
        best = dict(g[-1])
        if not best.get("pay_monthly"):  # keep salary info from any duplicate
            withpay = [x for x in g if x.get("pay_monthly")]
            if withpay:
                best["pay_monthly"], best["sal"] = withpay[-1]["pay_monthly"], withpay[-1]["sal"]
                attach_net(best, cfg)
                best["flags"] = [f for f in best["flags"] if f != "salary not listed"]
                best["reasons"] = [r for r in best["reasons"] if r != "salary not listed"]
                if best["status"] == "excluded" and not best["reasons"]:
                    best["status"] = "keep"
        best["sources"] = sorted({x["source"] for x in g})
        best["urls"] = list(dict.fromkeys(x["url"] for x in g if x["url"]))[:3]
        if len(dates) >= 2 and (dt.date.fromisoformat(dates[-1]) - dt.date.fromisoformat(dates[0])).days > cfg["ghost"]["repostSpanDays"]:
            best["status"] = "excluded"
            best["reasons"] = best["reasons"] + [f"reposted ({len(g)} postings, {dates[0]} → {dates[-1]})"]
        inherited = [r for x in g for r in x["reasons"] if r.startswith(("restricted", "onsite", "pay max", "open "))]
        if best["status"] == "keep" and inherited:
            best["status"], best["reasons"] = "excluded", inherited[:1]
        best["fit"] = fit_score(best, cfg, R)
        final.append(best)

    keep = sorted([j for j in final if j["status"] == "keep"], key=lambda x: -x["fit"])
    exc = [j for j in final if j["status"] == "excluded"]
    base = os.path.basename(raw_path)
    res_path = os.path.join(os.path.dirname(raw_path), ("results-" + base[4:]) if base.startswith("raw-") else ("results-" + base))
    if os.path.abspath(res_path) == os.path.abspath(raw_path):
        raise SystemExit("refusing to overwrite the raw scan with results")
    write_atomic(res_path, json.dumps({"keep": keep, "excluded": exc}, ensure_ascii=False, indent=1))
    first = [j["reasons"][0] for j in exc]
    summary = collections.Counter("restricted to (location)" if x.startswith("restricted to ") else
                                  "restricted (posting text)" if x.startswith("restricted:") else re.sub(r"\d[\d,]*|\(.*|:.*", "#", x)[:40]
                                  for x in first)
    places = collections.Counter(x[14:].strip(" ,")[:20] for x in first if x.startswith("restricted to "))
    return dict(places=places.most_common(6), raw=len(raw), irrelevant=sum(j["status"] == "irrelevant" for j in raw), unique=len(final),
                keep=keep, excluded=exc, reasons=summary.most_common(), path=res_path, currency=cfg["profile"]["currency"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--raw")
    ap.add_argument("--today", help="YYYY-MM-DD (for reproducible runs)")
    a = ap.parse_args()
    today = dt.datetime.fromisoformat(a.today).replace(tzinfo=dt.timezone.utc) if a.today else None
    r = run(os.path.abspath(os.path.expanduser(a.workspace)), a.raw, today)
    print(f"raw {r['raw']} | irrelevant {r['irrelevant']} | unique relevant {r['unique']} | keep {len(r['keep'])} | excluded {len(r['excluded'])}")
    print("excluded by reason:", ", ".join(f"{k} {n}" for k, n in r["reasons"][:12]))
    if r["places"]:
        print("  restricted locations (top):", ", ".join(f"{k} {n}" for k, n in r["places"]))
    for j in r["keep"]:
        pay = f"{r['currency']} {j['pay_monthly'][0]:,}–{j['pay_monthly'][1]:,}/mo" if j.get("pay_monthly") else "no salary"
        if j.get("pay_net"):
            pay += f" → net ≈ {j['pay_net'][0]:,}–{j['pay_net'][1]:,} ({'/'.join(j['net_contracts'])}; estimate)"
        print(f"\n[{j['fit']}] {j['title']} — {j['company']} | {'+'.join(j['sources'])} | {j.get('age_days')}d | {pay}")
        print("   loc:", j["loc"][:110], f"| eligibility: {j.get('eligibility')}")
        flags = [f for f in j["flags"] if f != "salary not listed"]  # already shown as "no salary"
        if flags:
            print("   flags:", "; ".join(flags))
        print("  ", j["urls"][0] if j["urls"] else "")
    print("\nsaved", r["path"])
    try:  # structured outcome log (outcomes/outcomes.jsonl); never fail the scan because of it
        import outcomes
        outcomes.log_scan(os.path.abspath(os.path.expanduser(a.workspace)), r["path"])
    except Exception as e:
        print("outcomes: log failed:", e, file=sys.stderr)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Can this employer hire the user where they live? Advisory verdicts that read the posting's text; no network.
Not legal or immigration advice: the user confirms work rights with the employer.

verdict:
  eligible    the posting says the user's country/region (or worldwide) is fine
  likely      remote with no restriction found
  unclear     no location information at all
  relocation  requires residence somewhere the user may work (e.g. EU citizen living outside the EU)
  no          requires residence/citizenship/payroll the user doesn't have

It separates residence ("must reside in", "residence required") from the right to work ("authorized to work in",
"citizens of"): a passport satisfies the second, not the first.
"""
import datetime as dt, re, sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

EU = "AT BE BG HR CY CZ DK EE FI FR DE GR HU IE IT LV LT LU MT NL PL PT RO SK SI ES SE".split()
EEA = EU + ["NO", "IS", "LI"]
LATAM = "AR BO BR CL CO CR CU DO EC SV GT HN MX NI PA PY PE PR UY VE".split()
REGIONS = [  # (regex, members) - checked in order; country names after regions
    (r"\b(european union|eu|eea)\b", EEA), (r"\beurope(an)?\b|\bemea\b", EEA + ["GB", "CH", "UA", "RS"]),
    (r"\blatam\b|latin america|south america", LATAM), (r"\bamericas\b", LATAM + ["US", "CA"]),
    (r"\bnorth america\b", ["US", "CA", "MX"]), (r"\bapac\b|asia[- ]pacific", ["AU", "NZ", "SG", "JP", "KR", "IN", "PH", "ID", "MY", "TH", "VN"]),
    (r"united states|\busa\b|u\.s\.|\bamerica\b|\bthe us\b", ["US"]), (r"united kingdom|\buk\b|britain|england|london", ["GB"]),
    (r"canada|toronto|vancouver", ["CA"]), (r"brazil|brasil", ["BR"]), (r"portugal|lisbon", ["PT"]), (r"spain|madrid|barcelona", ["ES"]),
    (r"germany|deutschland|berlin|munich", ["DE"]), (r"france|paris", ["FR"]), (r"ital(y|ia)", ["IT"]), (r"netherlands|amsterdam", ["NL"]),
    (r"poland|warsaw", ["PL"]), (r"ireland|dublin", ["IE"]), (r"switzerland|zurich", ["CH"]), (r"finland|helsinki", ["FI"]),
    (r"mexico", ["MX"]), (r"argentina", ["AR"]), (r"colombia", ["CO"]), (r"chile", ["CL"]), (r"india|bengaluru|bangalore", ["IN"]),
    (r"romania|bucharest", ["RO"]), (r"ukraine|kyiv", ["UA"]), (r"czech|prague", ["CZ"]), (r"hungary|budapest", ["HU"]),
    (r"sweden|stockholm", ["SE"]), (r"austria|vienna", ["AT"]), (r"belgium|brussels", ["BE"]), (r"uruguay", ["UY"]), (r"peru", ["PE"]),
    (r"israel", ["IL"]), (r"australia", ["AU"]), (r"japan|tokyo", ["JP"]), (r"singapore", ["SG"]),
]
WORLD = re.compile(r"worldwide|anywhere|unrestricted|all countries|any (location|country)|work from anywhere|hire globally|global(ly)? remote", re.I)
RESIDENCE = re.compile(
    r"(?:must|need to|required to|should)\s+(?:currently\s+)?(?:be\s+)?(?:reside|residing|live|living|be based|based|located|be located)\s+(?:in|within)\s+(?:the\s+)?([a-z .]{2,40})"
    r"|([a-z]+(?: [a-z]+)?) residen(?:ce|cy) (?:is )?required|residen(?:ce|t) (?:in|of) (?:the\s+)?([a-z .]{2,30})"
    r"|(?:only|exclusively) (?:open to |for )?(?:candidates|applicants|people) (?:based|located|living|residing) in (?:the\s+)?([a-z .]{2,30})", re.I)
RIGHT_TO_WORK = re.compile(
    r"(?:right|authori[sz](?:ed|ation)|eligib(?:le|ility)|permit(?:ted)?|legally able) to work (?:in|for) (?:the\s+)?([a-z .]{2,30})"
    r"|work authori[sz]ation (?:in|for) (?:the\s+)?([a-z .]{2,30})|([a-z]+) citizens?(?:hip)? (?:only|required)|citizens? of (?:the\s+)?([a-z .]{2,30})", re.I)
US_PAYROLL = re.compile(r"\bw-?2\b|security clearance|ts/sci|\bitar\b|u\.?s\.? (person|citizen)|green card|401\(?k\)?", re.I)
EOR = re.compile(r"\b(deel|remote\.com|oyster ?hr|rippling|velocity global|multiplier|papaya global|employer of record|\beor\b)", re.I)
CONTRACTOR = re.compile(r"\b(contractor|contract role|independent contract|b2b|freelanc|1099|\bpj\b|pessoa jur[ií]dica|invoice)", re.I)
LOCAL_EMPLOYEE = re.compile(r"\bclt\b|carteira assinada|regime clt", re.I)  # country-specific local payroll terms
TZ = {"PST": -8, "PT": -8, "PDT": -7, "MST": -7, "CST": -6, "CT": -6, "EST": -5, "ET": -5, "EDT": -4, "BRT": -3, "GMT": 0, "UTC": 0,
      "WET": 0, "BST": 1, "CET": 1, "CEST": 2, "EET": 2, "IST": 5.5, "SGT": 8, "JST": 9, "AEST": 10}
TZ_MENTION = re.compile(r"\b(?:utc|gmt)\s?([+-]\d{1,2})\b|\b(" + "|".join(TZ) + r")\b(?=[^.]{0,60}(?:overlap|hours|time ?zone|business|core))"
                        r"|(?:overlap|time ?zone|core hours|working hours)[^.]{0,60}\b(" + "|".join(TZ) + r")\b", re.I)


def countries(text):
    t = (text or "").lower()
    out = ["US"] if re.search(r"\bUS\b", text or "") else []  # upper case only: "works for us" is not the USA
    for pat, members in REGIONS:
        if re.search(pat, t):
            out += [m for m in members if m not in out]
    return out


def detect_contract(job):
    text = (job.get("title", "") + " " + job.get("text", "") + " " + str((job.get("extra") or {}).get("emp") or ""))
    if job.get("source") == "Gupy" or LOCAL_EMPLOYEE.search(text):
        return "employee_local"
    if EOR.search(text):
        return "eor"
    if CONTRACTOR.search(text):
        return "contractor"
    if re.search(r"\bw-?2\b|401\(?k\)?", text, re.I):
        return "employee_foreign"
    return "unknown"


def tz_overlap(job, person, today=None):
    """Hours of a 9-17 workday shared with the employer's time zone (None if no zone is named)."""
    m = TZ_MENTION.search(job.get("text", "")[:6000] + " " + job.get("loc", ""))
    if not m or not person.get("timezone"):
        return None, None
    off = float(m.group(1)) if m.group(1) else TZ.get((m.group(2) or m.group(3) or "").upper())
    if off is None:
        return None, None
    today = today or dt.datetime.now(dt.timezone.utc)
    try:
        zone = ZoneInfo(person["timezone"])
    except (ZoneInfoNotFoundError, ValueError):
        print(f"person.timezone {person['timezone']!r} is not an IANA zone (e.g. America/Sao_Paulo, Europe/Lisbon); "
              "time-zone overlap skipped (on Windows: pip install tzdata)", file=sys.stderr)
        return None, None
    mine = zone.utcoffset(today.replace(tzinfo=None)).total_seconds() / 3600
    return max(0.0, 8 - abs(mine - off)), m.group(0).strip()


def eligibility(job, person, today=None):
    res, cits = (person.get("residence") or "").upper(), [c.upper() for c in person.get("citizenships") or []]
    may_work = set(cits) | {p.upper() for p in person.get("workPermits") or []} | ({res} if res else set())
    if may_work & set(EEA):
        may_work |= set(EEA) | {"CH"}  # EU/EEA free movement
    text, loc = job.get("text", "")[:8000], job.get("loc", "")
    reasons, verdict = [], None

    for m in RESIDENCE.finditer(text):
        place = next(g for g in m.groups() if g)
        cs = countries(place)
        if not cs or WORLD.search(place):
            continue
        if res in cs:
            verdict = verdict or "eligible"
            reasons.append(f"residence in {place.strip()}: you live there")
        elif may_work & set(cs):
            verdict = "relocation"
            reasons.append(f"the posting requires residence in {place.strip()}: your citizenship may allow it (confirm), but you'd have to move")
        else:
            verdict = "no"
            reasons.append(f"the posting requires residence in {place.strip()}")
    for m in RIGHT_TO_WORK.finditer(text):
        place = next(g for g in m.groups() if g)
        cs = countries(place)
        if not cs:
            continue
        if may_work & set(cs):
            reasons.append(f"the posting asks for the right to work in {place.strip()}: your citizenship suggests you have it (confirm with the employer)")
            if res not in cs and verdict is None:
                verdict = "relocation" if not WORLD.search(loc) else None
                if verdict:
                    reasons.append("…but no sign they hire people living elsewhere")
        else:
            verdict = "no"
            reasons.append(f"the posting asks for the right to work in {place.strip()}")
    if US_PAYROLL.search(text) and res != "US" and "US" not in cits:
        if WORLD.search(loc) and verdict in (None, "likely", "eligible"):
            verdict = "likely"  # worldwide role that also lists US benefits: non-US hires are often contractors
            reasons.append("mentions US payroll/benefits (W-2, 401k, clearance): ask how they hire outside the US")
        else:
            verdict = "no" if verdict in (None, "likely", "eligible") else verdict
            reasons.append("US payroll/clearance signal (W-2, clearance, US person)")

    loc_cs = countries(loc)
    if verdict is None:
        if WORLD.search(loc) or (not loc_cs and WORLD.search(text[:1500])):
            verdict = "eligible"
            reasons.append("worldwide / anywhere")
        elif loc_cs:
            if res in loc_cs:
                verdict = "eligible"
                reasons.append(f"location includes your country ({res})")
            elif may_work & set(loc_cs):
                verdict = "relocation"
                reasons.append(f"location {loc.strip()[:40]}: you may work there but don't live there")
            else:
                verdict = "no"
                reasons.append(f"location {loc.strip()[:40]}")
        elif re.search(r"remote|remoto", loc + " " + text[:600], re.I):
            verdict = "likely"
            reasons.append("remote, no country restriction found")
        else:
            verdict = "unclear"
            reasons.append("no location stated")

    contract = detect_contract(job)
    if contract == "eor" and verdict in ("likely", "unclear"):
        reasons.append("hires through an employer of record: ask whether your country is covered")
    overlap, tzm = tz_overlap(job, person, today)
    if overlap is not None:
        reasons.append(f"time zone {tzm!r}: ~{overlap:.0f}h overlap with a 9-17 day")
        if overlap < person.get("minOverlapHours", 4) and verdict in ("eligible", "likely"):
            verdict = "likely"
            reasons.append(f"less than {person.get('minOverlapHours', 4)}h overlap")
    return {"verdict": verdict, "reasons": reasons, "contract": contract, "tz_overlap": overlap}

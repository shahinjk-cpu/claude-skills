#!/usr/bin/env python3
"""Is this company real? An explainable trust score from public signals. It never proves a company is safe.

Signals: domain age (RDAP), mail setup (MX/SPF via DNS-over-HTTPS), website (reachable, parked), a public
job board (Greenhouse/Ashby/Lever/Workable), recruiter email domain, LEI (GLEIF), Brazilian CNPJ status
(BrasilAPI, when a CNPJ is given), number of job boards listing the company, and scam flags from filter.py.
Results are cached in <workspace>/search/company-cache.json for 30 days.

Usage:
  python3 verify_company.py --workspace WS --company "Acme" [--domain acme.com] [--email jane@acme.com] [--cnpj 00.000.000/0001-00]
  python3 verify_company.py --workspace WS --results search/scans/results-DATE.json   # kept jobs, unknown companies only
"""
import argparse, datetime as dt, json, os, re, sys, time
from urllib.parse import quote, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scan  # noqa: E402  (get, getj, ATS_APIS)
from config import write_atomic, read_json  # noqa: E402
from filter import FREEMAIL  # noqa: E402

TTL_DAYS = 30
PARKED = re.compile(r"domain (is )?for sale|buy this domain|parked (free|domain)|domain im kundenauftrag registriert|this domain (has been|was) registered|"
                    r"coming soon|under construction|sedoparking|parkingcrew|bodis|hugedomains|dan\.com|afternic", re.I)
NOT_COMPANY = re.compile(r"greenhouse\.io|ashbyhq\.com|lever\.co|workable\.com|smartrecruiters|gupy\.io|linkedin|indeed|remoterocketship|himalayas|"
                         r"remoteok|remotive|jobicy|weworkremotely|workingnomads|getonbrd|arbeitnow|ycombinator|perfectrole|wellfound|glassdoor|"
                         r"personio|bamboohr|recruitee|teamtailor|breezy|jobvite|icims|myworkdayjobs|kula\.ai|talentlyft", re.I)


def http(url, timeout=20):
    """(status, final_url, body); every redirect hop must be a public host (scan.fetch_public)."""
    return scan.fetch_public(url, timeout)


def norm(s):
    return re.sub(r"\b(inc|llc|ltd|gmbh|s\.?a\.?|ltda|plc|corp|co|bv|ag|sas|srl|spa|limited|group|holdings?)\b\.?", " ", (s or "").lower()).strip()


def slugs(company):
    w = re.sub(r"[^a-z0-9 ]", "", norm(company)).split()
    return list(dict.fromkeys(x for x in ("".join(w), "-".join(w), w[0] if w else "") if x))


SOCIAL = re.compile(r"linkedin|twitter|x\.com|facebook|instagram|youtube|github|medium|glassdoor|crunchbase|google|apple\.com|bit\.ly", re.I)


def domain_from_text(company, text):
    """The company's own domain when the posting mentions it (e.g. 'learn more at acme.com')."""
    words = re.sub(r"[^a-z0-9 ]", "", norm(company)).split()
    if not words:
        return None
    for m in re.finditer(r"(?:https?://)?(?:www\.)?([a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,6})(?![a-z0-9])", (text or "").lower()):
        host = m.group(1)
        if NOT_COMPANY.search(host) or SOCIAL.search(host) or "@" in text[max(0, m.start() - 1):m.start()]:
            continue
        if words[0] in host.split(".")[0] or "".join(words) == host.split(".")[0]:
            return host
    return None


def guess_domain(company):
    """Try <name>.com/.io/.ai/.co/.com.br; accept only if the page title or final host names the company."""
    words = re.sub(r"[^a-z0-9 ]", "", norm(company)).split()
    if not words:
        return None
    for base in dict.fromkeys(("".join(words), words[0])):
        for tld in (".com", ".io", ".ai", ".co", ".com.br"):
            code, final, body = http(f"https://{base}{tld}", timeout=12)
            if not code or code >= 400 or PARKED.search(body[:20000]):
                continue
            title = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
            t = (title.group(1) if title else "").lower()
            host = urlparse(final).netloc.lower().removeprefix("www.")
            if words[0] in t or words[0] in host.split(".")[0]:
                return host or f"{base}{tld}"
    return None


def domain_age_days(domain, today):
    d = scan.getj(f"https://rdap.org/domain/{quote(domain)}")
    for e in (d or {}).get("events", []):
        if e.get("eventAction") == "registration":
            reg = dt.datetime.fromisoformat(e["eventDate"].replace("Z", "+00:00")[:19]).replace(tzinfo=dt.timezone.utc)
            return (today - reg).days, e["eventDate"][:10]
    return None, None


def dns(domain, rtype):
    d = scan.getj(f"https://dns.google/resolve?name={quote(domain)}&type={rtype}")
    return [a.get("data", "") for a in (d or {}).get("Answer", [])]


def ats_board(company):
    for s in slugs(company):
        for kind, url in scan.ATS_APIS.items():
            d = scan.getj(url.format(s), timeout=15)
            n = len(d) if isinstance(d, list) else len((d or {}).get("jobs") or []) if isinstance(d, dict) else 0
            if n:
                return f"{kind}/{s} ({n} jobs)"
    return None


def lei(company):
    d = scan.getj(f"https://api.gleif.org/api/v1/fuzzycompletions?field=entity.legalName&q={quote(company)}")
    target = norm(company)
    for x in (d or {}).get("data", [])[:10]:
        name = (x.get("attributes") or {}).get("value", "")
        if target and (norm(name) == target or norm(name).startswith(target + " ")):
            return name
    return None


def cnpj_status(cnpj):
    digits = re.sub(r"\D", "", cnpj or "")
    if len(digits) != 14:
        return None
    d = scan.getj(f"https://brasilapi.com.br/api/cnpj/v1/{digits}")
    if not d or "razao_social" not in d:
        return {"found": False}
    return {"found": True, "name": d.get("razao_social"), "status": d.get("descricao_situacao_cadastral"), "opened": d.get("data_inicio_atividade")}


def safe_host(h):
    """Public hostnames only: no IPs, localhost or internal names (a posting must not make us probe the local network)."""
    h = (h or "").lower().rstrip(".")
    if not h or "." not in h or h == "localhost" or h.endswith((".local", ".internal", ".lan")):
        return None
    if re.fullmatch(r"[\d.]+|\[?[0-9a-f:]+\]?", h):
        return None
    return h


def job_domain(company, job):
    """The company's own domain from a job's URLs or text, accepted only when its name matches the company
    (an unknown ATS or redirect host must never stand in for the employer). Returns (domain, source)."""
    words = re.sub(r"[^a-z0-9 ]", "", norm(company)).split()
    for u in job.get("urls") or [job.get("url")]:
        h = safe_host(urlparse(u or "").hostname)
        if h and words and not NOT_COMPANY.search(h):
            h = h.removeprefix("www.")
            label = h.split(".")[-2] if h.count(".") >= 1 else h
            if words[0] in label or "".join(words) == label:
                return h, "job link"
    d = domain_from_text(company, job.get("text", ""))
    return (safe_host(d), "posting text") if d and safe_host(d) else (None, None)


def check(company, domain=None, email=None, cnpj=None, job=None, today=None, guess=True):
    """Returns {trust, verdict, signals[(points, text)], next_steps[]}."""
    today = today or dt.datetime.now(dt.timezone.utc)
    sig, nxt = [], []
    given = (domain or "").lower().removeprefix("www.")
    domain = safe_host(given)
    if given and not domain:
        sig.append((0, f"--domain {given!r} refused: public hostnames only"))
    if not domain and job:
        domain, how = job_domain(company, job)
        if domain:
            sig.append((0, f"website from the {how}: {domain} (its name matches the company)"))
    guessed = False
    if not domain and guess:
        domain = guess_domain(company)
        guessed = bool(domain)
    if guessed:
        sig.append((0, f"website GUESSED from the name: {domain} (may be a different company)"))
        nxt.append(f"confirm the company's website; re-run with --domain if it isn't {domain}")
    if domain:
        age, reg = domain_age_days(domain, today)
        if age is None:
            sig.append((0, f"domain {domain}: registration date not found"))
        elif age < 180:
            sig.append((-30, f"domain {domain} registered {reg} ({age} days ago)"))
        elif age < 730:
            sig.append((-10, f"domain {domain} registered {reg} (under 2 years)"))
        elif age >= 1825:
            sig.append((15, f"domain {domain} registered {reg} (5+ years)"))
        else:
            sig.append((5, f"domain {domain} registered {reg}"))
        mx = dns(domain, "MX")
        sig.append((5, "mail server (MX) configured") if mx else (-10, "no mail server (MX) for the domain"))
        if any("v=spf1" in t for t in dns(domain, "TXT")):
            sig.append((3, "SPF record present"))
        code, final, body = http(f"https://{domain}")
        if not code or code >= 400:
            sig.append((-15, f"website unreachable (HTTP {code})"))
        elif PARKED.search(body[:20000]):
            sig.append((-25, "website looks parked / placeholder"))
        else:
            title = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
            sig.append((10, f"website up, title (untrusted text): \"{scan.strip(title.group(1))[:60] if title else final}\""))
    else:
        sig.append((-5, "no company website found"))
        nxt.append("find the company's own website (not a job board) and re-run with --domain")
    board = ats_board(company)
    sig.append((15, f"public job board found: {board}") if board else (0, "no public Greenhouse/Ashby/Lever/Workable board"))
    if email:
        ed = email.split("@")[-1].lower()
        if FREEMAIL.search(email):
            sig.append((-25, f"recruiter uses a free email ({ed})"))
            nxt.append("ask for a message from a company email address")
        elif domain and (ed == domain or ed.endswith("." + domain)):
            sig.append((10, "recruiter email matches the company domain"))
        else:
            sig.append((-5, f"recruiter email domain {ed} differs from the company domain"))
    name = lei(company)
    if name:
        sig.append((5, f"an entity named {name} has an LEI (check it is the same company)"))
    if cnpj:
        c = cnpj_status(cnpj)
        if c and c.get("found"):
            ok = (c.get("status") or "").upper() == "ATIVA"
            sig.append((15 if ok else -30, f"CNPJ {c['name']}: {c.get('status')} since {c.get('opened')}"))
        elif c is not None:
            sig.append((-20, "CNPJ not found"))
    if job:
        n = len(job.get("sources") or [])
        if n >= 2:
            sig.append((5, f"listed on {n} job boards"))
        if any("SCAM" in f for f in job.get("flags", [])):
            sig.append((-20, "scam keywords in the posting"))
    trust = max(0, min(100, 50 + sum(p for p, _ in sig)))
    verdict = "ok" if trust >= 65 else "caution" if trust >= 40 else "high-risk"
    if (guessed or not domain) and not email:
        verdict = "unverified"  # domain unknown or unconfirmed: the score is only a hint
    if verdict in ("caution", "high-risk"):
        nxt += ["ask for the legal entity name, country and registration number, and check it in the official registry",
                "never send ID, bank details or money, or install software, before a signed contract with that entity"]
    return {"company": company, "domain": domain, "trust": trust, "verdict": verdict, "signals": sig,
            "next_steps": list(dict.fromkeys(nxt)), "checked": today.date().isoformat()}


class Cache:
    def __init__(self, ws):
        self.path = os.path.join(ws, "search", "company-cache.json")
        self.data = read_json(self.path) if os.path.exists(self.path) else {}

    def get(self, key, today):
        r = self.data.get(key)
        if r and (today.date() - dt.date.fromisoformat(r["checked"])).days <= TTL_DAYS:
            return r
        return None

    def put(self, key, r, today=None):
        today = today or dt.date.today()
        self.data = {k: v for k, v in self.data.items() if (today - dt.date.fromisoformat(v["checked"])).days <= TTL_DAYS}  # keep nothing expired
        self.data[key] = r
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        write_atomic(self.path, json.dumps(self.data, ensure_ascii=False, indent=1))


def show(r):
    print(f"\n{r['company']} ({r['domain'] or 'no domain'}): trust {r['trust']}/100 → {r['verdict'].upper()}")
    for p, t in r["signals"]:
        print(f"   {p:+4d}  {t}")
    for s in r["next_steps"]:
        print("   next:", s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--company")
    ap.add_argument("--domain")
    ap.add_argument("--email")
    ap.add_argument("--cnpj")
    ap.add_argument("--results", help="results-DATE.json: check the kept jobs' companies")
    ap.add_argument("--refresh", action="store_true", help="ignore the cache")
    a = ap.parse_args()
    ws = os.path.abspath(os.path.expanduser(a.workspace))
    cache, today = Cache(ws), dt.datetime.now(dt.timezone.utc)
    todo = []
    if a.results:
        res = read_json(a.results)
        todo = [(j["company"], None, None, None, j) for j in res["keep"] if j.get("company")]
    elif a.company:
        todo = [(a.company, a.domain, a.email, a.cnpj, None)]
    else:
        sys.exit("give --company or --results")
    for company, domain, email, cnpj, job in todo:
        derived = domain or (job_domain(company, job)[0] if job else None)
        key = (derived or "") + "|" + norm(company)  # a new apply domain under a known name gets its own check
        r = None if a.refresh or email or cnpj else cache.get(key, today)
        if not r:
            r = check(company, domain, email, cnpj, job, today)
            cache.put(key, r)
            time.sleep(0.5)
        show(r)
    print("\nEstimates from public signals: a high score is not proof that a company is safe.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Multi-source job scan driven by the workspace config.

Usage:
    python3 scan.py --workspace PATH            # all enabled sources
    python3 scan.py --workspace PATH --only remotive,himalayas
    python3 scan.py --workspace PATH --probe-ats roboflow,mapbox   # find company job-board slugs

Reads  PATH/search/filters.md  (JSON block: "queries", "sources", "gupyTerms", "remoteRocketship", "atsBoards")
Writes PATH/search/scans/raw-YYYY-MM-DD.json  (list of normalized jobs)

Normalized job: {source, sid, title, company, loc, url, text, posted (ISO-8601 UTC), sal, extra}
sal: {min, max, cur, per} | {text} | null
Only public APIs / RSS feeds are used. No login-walled sites are scraped.
"""
import argparse, datetime as dt, html, ipaddress, json, os, re, socket, stat, subprocess, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, urljoin, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import load_config, write_atomic, read_json  # noqa: E402

UA = "Mozilla/5.0 (X11; Linux x86_64) job-hunt-skill/1.0"


CURL_SAFE = ["--proto", "=https,http", "--proto-redir", "=https,http", "--max-redirs", "5", "--max-filesize", "20M"]


def get(url, timeout=40):
    return subprocess.run(["curl", "-s", "-L", *CURL_SAFE, "-m", str(timeout), "-A", UA, "--", url], capture_output=True, text=True).stdout


def public_ip(host):
    """The host's first address when every address it resolves to is public; None for localhost, private,
    link-local or internal names (a posting or redirect must never make us probe the local network)."""
    host = (host or "").lower().rstrip(".")
    if not host or host == "localhost" or host.endswith((".local", ".internal", ".lan", ".localhost")):
        return None
    try:
        ips = [ipaddress.ip_address(i[4][0].split("%")[0]) for i in socket.getaddrinfo(host, None)]
    except (OSError, ValueError):
        return None
    return str(ips[0]) if ips and all(ip.is_global for ip in ips) else None


def fetch_public(url, timeout=20, max_redirects=5):
    """(status, final_url, body) for an untrusted URL: http(s) only, every hop checked with public_ip and pinned
    to that address (no DNS rebinding). Status 0 when refused or unreachable."""
    for _ in range(max_redirects + 1):
        p = urlparse(url)
        ip = public_ip(p.hostname) if p.scheme in ("http", "https") else None
        if not ip:
            return 0, url, ""
        port = p.port or (443 if p.scheme == "https" else 80)
        pin = f"{p.hostname}:{port}:{'[' + ip + ']' if ':' in ip else ip}"
        r = subprocess.run(["curl", "-s", *CURL_SAFE, "--resolve", pin, "-m", str(timeout), "-A", UA, "-o", "-",
                            "-w", "\n__META__%{http_code} %{redirect_url}", "--", url], capture_output=True, text=True)
        body, _, meta = r.stdout.rpartition("\n__META__")
        code, _, nxt = meta.partition(" ")
        code = int(code) if code.isdigit() else 0
        if 300 <= code < 400 and nxt.strip():
            url = urljoin(url, nxt.strip())
            continue
        return code, url, body
    return 0, url, ""


def cached_getj(cfg, name, url, ttl_hours, max_per_day=None):
    """GET JSON once per ttl and at most max_per_day times a day (some APIs ask for that), cached in the workspace."""
    ws = cfg.get("_workspace")
    if not ws:
        return getj(url)
    d = os.path.join(ws, "search", "cache")
    os.makedirs(d, exist_ok=True)
    path, meta_path = os.path.join(d, f"{name}.json"), os.path.join(d, f"{name}.meta.json")
    meta = read_json(meta_path) if os.path.exists(meta_path) else {}
    now, today = time.time(), dt.date.today().isoformat()
    fresh = os.path.exists(path) and now - meta.get("fetched", 0) < ttl_hours * 3600
    calls = meta.get("calls", {}).get(today, 0)
    if not fresh and (max_per_day is None or calls < max_per_day):
        data = getj(url)
        if data is not None:
            write_atomic(path, json.dumps(data))
            meta = {"fetched": now, "calls": {today: calls + 1}}
            write_atomic(meta_path, json.dumps(meta))
            return data
    elif not fresh:
        print(f"{name}: daily request limit ({max_per_day}) reached, using cached data", file=sys.stderr)
    return read_json(path) if os.path.exists(path) else None


def getj(url, **kw):
    try:
        return json.loads(get(url, **kw))
    except Exception:
        return None


CONTROL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f\u200b-\u200f\u202a-\u202e\u2066-\u2069]")  # escapes, bidi/zero-width tricks


NONTEXT = re.compile(r"<(script|style|noscript|svg|head|nav|footer)\b.*?</\1\s*>|<!--.*?-->", re.I | re.S)  # code, styling, page chrome


def strip(s):
    """HTML to plain text for untrusted fields; drops control, bidi and zero-width characters (terminal/link spoofing)."""
    s = NONTEXT.sub(" ", str(s or ""))
    return re.sub(r"\s+", " ", CONTROL.sub(" ", html.unescape(re.sub(r"<[^>]+>", " ", s)))).strip()


def pdate(s):
    if not s:
        return None
    try:
        if isinstance(s, (int, float)) or (isinstance(s, str) and s.isdigit()):
            return dt.datetime.fromtimestamp(int(s), dt.timezone.utc)
        s = str(s).replace("Z", "+00:00")
        if re.match(r"\d{4}-\d{2}-\d{2}", s):
            t = s[11:19] if len(s) > 10 else "00:00:00"
            return dt.datetime.fromisoformat(s[:10] + "T" + t).replace(tzinfo=dt.timezone.utc)
        return dt.datetime.strptime(s[:25].strip(), "%a, %d %b %Y %H:%M:%S").replace(tzinfo=dt.timezone.utc)
    except Exception:
        return None


def safe_url(u):
    """Keep only plain http(s) links from untrusted sources (no javascript:, file:, control or bidi characters)."""
    u = CONTROL.sub("", str(u or "")).strip()
    return u if re.match(r"https?://[^\s/]+", u, re.I) else ""


def job(source, sid, title, company, loc, url, text, posted, sal=None, extra=None):
    return dict(source=source, sid=str(sid), title=strip(title), company=strip(company or ""), loc=strip(loc or ""),
                url=safe_url(url), text=strip(text)[:20000], posted=posted.isoformat() if posted else None, sal=sal, extra=extra or {})


# ---------------------------------------------------------------- sources
class NoRedirect(urllib.request.HTTPRedirectHandler):
    """urllib copies every header, Authorization included, to a redirect target: refuse redirects instead."""
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise urllib.error.HTTPError(req.full_url, code, f"redirect to {newurl} refused (API key stays here)", headers, fp)


API = urllib.request.build_opener(NoRedirect)


def rr_post(keyf, body):
    """POST with the API key in a header, read into memory only: never in a command line, log or error message."""
    if os.stat(keyf).st_mode & (stat.S_IRWXG | stat.S_IRWXO):
        print(f"remoterocketship: {keyf} is readable by other users; run: chmod 600 {keyf}", file=sys.stderr)
    key = open(keyf).read().strip()
    req = urllib.request.Request("https://www.remoterocketship.com/api/openclaw/jobs/", data=body, method="POST",
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json", "User-Agent": UA})
    with API.open(req, timeout=60) as r:  # fixed https URL above, no user-controlled scheme  # nosec B310
        return json.loads(r.read(20_000_000).decode())


def src_remoterocketship(cfg):
    rr = cfg.get("remoteRocketship") or {}
    keyf = os.path.expanduser(rr.get("apiKeyFile", "~/.config/remoterocketship/api-key"))
    if not os.path.exists(keyf):
        print("remoterocketship: no API key file, skipped", file=sys.stderr)
        return []
    out = []
    for kw in cfg["queries"]:
        for page in range(1, rr.get("maxPages", 3) + 1):
            f = {"keywordFilters": [kw], "showRemoteJobs": True, "itemsPerPage": 50, "page": page}
            if rr.get("seniority"):
                f["seniorityFilters"] = rr["seniority"]
            body = json.dumps({"filters": f, "includeJobDescription": True}).encode()
            try:
                jobs = rr_post(keyf, body).get("jobOpenings") or []
            except urllib.error.HTTPError as e:
                hint = {401: "API key rejected (check the key file)", 403: "membership inactive", 429: "daily limit reached"}.get(e.code, "")
                print(f"remoterocketship: HTTP {e.code} {hint}; stopping this source", file=sys.stderr)
                return out
            except Exception as e:
                print(f"remoterocketship: {type(e).__name__}; retrying", file=sys.stderr)
                time.sleep(3)
                continue
            for j in jobs:
                s = j.get("salaryRange")
                sal = dict(min=s.get("min"), max=s.get("max"), cur=s.get("currencyCode"),
                           per=s.get("salaryType") or s.get("salaryHumanReadableText")) if s else None
                txt = " ".join(str(j.get(k) or "") for k in ("roleDescription", "roleRequirements", "benefits"))
                # RR has no location field; the slug ends with "<location>-remote"
                out.append(job("RemoteRocketship", j["id"], j.get("roleTitle"), (j.get("company") or {}).get("name"),
                               "slug: " + (j.get("slug") or "").replace("-", " "), j.get("url"), txt, pdate(j.get("created_at")), sal))
            if len(jobs) < 50:
                break
            time.sleep(1)
    return out


def src_remoteok(cfg):
    d = getj("https://remoteok.com/api") or []
    return [job("RemoteOK", j.get("id"), j.get("position"), j.get("company"), j.get("location"), j.get("apply_url") or j.get("url"),
                (j.get("description") or "") + " tags: " + " ".join(j.get("tags") or []), pdate(j.get("date")),
                dict(min=j.get("salary_min"), max=j.get("salary_max"), cur="USD", per="year") if j.get("salary_max") else None)
            for j in d[1:] if isinstance(j, dict)]


def src_remotive(cfg):
    """Remotive asks for at most 4 API requests a day and attribution (source name + link back, shown in every report).
    One full-feed request, cached for 6 hours and capped at 4 a day; queries are matched locally."""
    words = [w.lower() for q in cfg["queries"] for w in [q] if w]
    out = []
    for j in (cached_getj(cfg, "remotive", "https://remotive.com/api/remote-jobs", 6, 4) or {}).get("jobs", []):
        hay = (j.get("title", "") + " " + j.get("description", "")[:4000]).lower()
        if words and not any(w in hay for w in words):
            continue
        out.append(job("Remotive", j["id"], j.get("title"), j.get("company_name"), j.get("candidate_required_location"), j.get("url"),
                       j.get("description"), pdate(j.get("publication_date")), {"text": j["salary"]} if j.get("salary") else None))
    return out


def src_himalayas(cfg):
    out = []
    for t in cfg["queries"]:
        for page in range(1, 4):
            jobs = (getj(f"https://himalayas.app/jobs/api/search?q={quote(t)}&page={page}") or {}).get("jobs") or []
            for j in jobs:
                loc = ", ".join(j.get("locationRestrictions") or []) or "unrestricted"
                sal = dict(min=j.get("minSalary"), max=j.get("maxSalary"), cur=j.get("currency") or "USD",
                           per=j.get("salaryPeriod") or "year") if j.get("maxSalary") else None
                out.append(job("Himalayas", j.get("guid") or j.get("applicationLink"), j.get("title"), j.get("companyName"), loc,
                               j.get("applicationLink"), (j.get("description") or "") + " " + (j.get("excerpt") or ""), pdate(j.get("pubDate")), sal))
            if len(jobs) < 20:
                break
    return out


def src_jobicy(cfg):
    out = []
    for t in cfg["queries"]:
        for j in (getj("https://jobicy.com/api/v2/remote-jobs?count=50&tag=" + quote(t)) or {}).get("jobs", []):
            mx = j.get("annualSalaryMax") or j.get("salaryMax")
            sal = dict(min=j.get("annualSalaryMin") or j.get("salaryMin"), max=mx, cur=j.get("salaryCurrency") or "USD",
                       per=j.get("salaryPeriod") or "year") if mx else None
            out.append(job("Jobicy", j["id"], j.get("jobTitle"), j.get("companyName"), j.get("jobGeo"), j.get("url"),
                           j.get("jobDescription") or j.get("jobExcerpt"), pdate(j.get("pubDate")), sal))
    return out


def src_arbeitnow(cfg):
    out = []
    for page in range(1, 8):
        d = getj(f"https://www.arbeitnow.com/api/job-board-api?page={page}") or {}
        for j in d.get("data", []):
            out.append(job("Arbeitnow", j.get("slug"), j.get("title"), j.get("company_name"),
                           (j.get("location") or "") + (" remote" if j.get("remote") else " onsite"), j.get("url"),
                           (j.get("description") or "") + " tags: " + " ".join(j.get("tags") or []), pdate(j.get("created_at"))))
        if not d.get("data"):
            break
    return out


def src_weworkremotely(cfg):
    out = []
    for feed in ["remote-jobs.rss", "categories/remote-programming-jobs.rss", "categories/remote-back-end-programming-jobs.rss",
                 "categories/remote-front-end-programming-jobs.rss", "categories/remote-full-stack-programming-jobs.rss",
                 "categories/remote-design-jobs.rss", "categories/remote-devops-sysadmin-jobs.rss", "categories/all-other-remote-jobs.rss"]:
        x = get("https://weworkremotely.com/" + feed)
        for it in re.findall(r"<item>(.*?)</item>", x, re.S):
            def g(t):
                m = re.search(rf"<{t}>(.*?)</{t}>", it, re.S)
                return (m.group(1) if m else "").replace("<![CDATA[", "").replace("]]>", "")
            comp, _, ttl = strip(g("title")).partition(":")
            out.append(job("WeWorkRemotely", strip(g("guid") or g("link")), ttl or comp, comp, strip(g("region")), strip(g("link")),
                           g("description"), pdate(strip(g("pubDate")))))
    return out


def src_workingnomads(cfg):
    d = getj("https://www.workingnomads.com/api/exposed_jobs/") or []
    return [job("WorkingNomads", j.get("url"), j.get("title"), j.get("company_name"), j.get("location"), j.get("url"),
                (j.get("description") or "") + " tags: " + str(j.get("tags")), pdate(j.get("pub_date"))) for j in d]


def src_getonbrd(cfg):
    out = []
    for t in cfg["queries"]:
        # note: adding expand=... makes this endpoint return nothing
        for j in (getj("https://www.getonbrd.com/api/v0/search/jobs?per_page=100&query=" + quote(t)) or {}).get("data", []):
            a = j.get("attributes", {})
            sal = dict(min=a.get("min_salary"), max=a.get("max_salary"), cur="USD", per="month") if a.get("max_salary") else None
            loc = ("remote " + str(a.get("remote_modality") or "")) if a.get("remote") else "onsite"
            loc += " countries: " + ",".join(a.get("countries") or [])
            out.append(job("GetOnBoard", j.get("id"), a.get("title"), "", loc,
                           (j.get("links") or {}).get("public_url") or f"https://www.getonbrd.com/jobs/{j.get('id')}",
                           " ".join(str(a.get(k) or "") for k in ("description", "functions", "desirable", "benefits")),
                           pdate(a.get("published_at")), sal))
    return out


GUPY_TERMS_WARNING = ("gupy: Gupy's terms of use for candidates forbid aggregating, copying or duplicating parts of the platform, "
                      "including job postings. This source is on because you enabled it; you are responsible for that choice. "
                      "Gupy jobs also appear via other sources (e.g. Himalayas, Remote Rocketship).")


def src_gupy(cfg):
    """Brazil only, OFF by default and never recommended: Gupy's candidate terms forbid aggregating or copying postings.
    Parses __NEXT_DATA__ from the public search page (the JSON APIs return 404)."""
    print(GUPY_TERMS_WARNING, file=sys.stderr)
    out = []
    for t in cfg.get("gupyTerms") or cfg["queries"]:
        for off in range(0, 120, 12):
            url = f"https://portal.gupy.io/job-search/term={quote(t)}" + (f"&offset={off}" if off else "")
            m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', get(url), re.S)
            if not m:
                break
            try:
                d = json.loads(m.group(1))["props"]["pageProps"]["initialJobList"]
            except Exception:
                break
            data = d.get("data") or []
            for j in data:
                out.append(job("Gupy", j["id"], j.get("name"), j.get("careerPageName"),
                               f"{j.get('workplaceType')} {j.get('city') or ''} {j.get('state') or ''} Brazil",
                               j.get("jobUrl"), j.get("description"), pdate(j.get("publishedDate")), None, {"type": j.get("type")}))
            if not data or off + 12 >= (d.get("pagination") or {}).get("total", 0):
                break
    return out


def src_hn(cfg):
    """Latest 'Ask HN: Who is hiring?' thread, found automatically."""
    s = getj("https://hn.algolia.com/api/v1/search_by_date?tags=story,author_whoishiring&query=who%20is%20hiring") or {}
    tid = next((h["objectID"] for h in s.get("hits", []) if h.get("title", "").lower().startswith("ask hn: who is hiring")), None)
    if not tid:
        return []
    out = []
    for c in (getj(f"https://hn.algolia.com/api/v1/items/{tid}") or {}).get("children", []):
        t = strip(c.get("text"))
        if not t or re.match(r"\s*(seeking|looking for|available for)\b", t, re.I):
            continue  # candidates advertising themselves, not jobs
        parts = [p.strip() for p in t.split("|")]
        out.append(job("HN WhoIsHiring", c.get("id"), " | ".join(parts[1:3])[:150] or t[:100], parts[0][:60], " | ".join(parts[:6])[:300],
                       f"https://news.ycombinator.com/item?id={c.get('id')}", t, pdate(c.get("created_at"))))
    return out


def slug_re(words):
    parts = [re.sub(r"[^a-z0-9]+", "-", w.lower()).strip("-") for w in words if w]
    return re.compile("|".join(r"(?:^|-)" + re.escape(p) + r"(?:-|$)" for p in parts if p) or r"$^", re.I)


def src_perfectrole(cfg):
    """perfectrole.app: robots.txt allows the job sitemaps and /jobs/<slug> pages (not /api/ or query URLs).
    Keep slugs that contain a target title keyword or query, then read each page's JSON-LD JobPosting (~1 request/s)."""
    keep = slug_re(cfg["roles"]["titleKeywords"] + cfg["queries"])
    drop = slug_re(cfg["roles"]["excludeTitle"])
    urls = []
    for i in range(10):
        locs = re.findall(r"<loc>([^<]+)</loc>", get(f"https://perfectrole.app/sitemaps/jobs-{i}.xml", timeout=60))
        if not locs:
            break
        urls += [u for u in locs if keep.search(u.rsplit("/", 1)[-1]) and not drop.search(u.rsplit("/", 1)[-1])]
    out = []
    for u in urls[: (cfg.get("perfectRole") or {}).get("maxPages", 400)]:
        h = get(u, timeout=30)
        time.sleep(0.8)
        for m in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', h, re.S):
            try:
                d = json.loads(m)
            except Exception:  # skip malformed JSON-LD blocks on third-party pages  # nosec B112
                continue
            for jp in (d if isinstance(d, list) else [d]):
                if not isinstance(jp, dict) or jp.get("@type") != "JobPosting":
                    continue
                jl = jp.get("jobLocation") or []
                jl = jl if isinstance(jl, list) else [jl]
                places = []
                for l in jl:
                    a = (l or {}).get("address") or {}
                    places.append(", ".join(x for x in (a.get("addressLocality"), a.get("addressRegion"), a.get("addressCountry")) if x))
                arl = jp.get("applicantLocationRequirements") or []
                arl = arl if isinstance(arl, list) else [arl]
                req = ", ".join((r or {}).get("name", "") for r in arl if isinstance(r, dict))
                remote = jp.get("jobLocationType") == "TELECOMMUTE"
                loc = ("remote " if remote else "onsite ") + (req or "; ".join(p for p in places if p))
                bs = jp.get("baseSalary") or {}
                bv = bs.get("value") or {}
                mx = bv.get("maxValue") or bv.get("value")
                sal = dict(min=bv.get("minValue"), max=mx, cur=bs.get("currency"), per=str(bv.get("unitText") or "").lower()) if mx else None
                out.append(job("PerfectRole", u.rsplit("/", 1)[-1].split("-")[0], jp.get("title"), (jp.get("hiringOrganization") or {}).get("name"),
                               loc, u, jp.get("description"), pdate(jp.get("datePosted")), sal, {"validThrough": jp.get("validThrough")}))
    return out


ATS_APIS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{}/jobs?content=true",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{}?includeCompensation=true",
    "lever": "https://api.lever.co/v0/postings/{}?mode=json",
    "workable": "https://apply.workable.com/api/v1/widget/accounts/{}?details=true",
}


def ats_title_re(cfg):
    words = cfg["roles"]["titleKeywords"] + [w for q in cfg["queries"] for w in q.split() if len(w) > 3]
    return re.compile("|".join(re.escape(w) for w in words if w) or r"$^", re.I)


def ats_board(kind, slug, title_re):
    """One company's public job board. Keeps titles that match the target keywords."""
    d = getj(ATS_APIS[kind].format(slug))
    out = []
    if kind == "greenhouse":
        for j in (d or {}).get("jobs") or []:
            if title_re.search(j.get("title") or ""):
                out.append(job("ATS:greenhouse", f"{slug}-{j.get('id')}", j.get("title"), j.get("company_name") or slug,
                               (j.get("location") or {}).get("name"), j.get("absolute_url"), html.unescape(j.get("content") or ""),
                               pdate(j.get("first_published") or j.get("updated_at"))))
    elif kind == "ashby":
        for j in (d or {}).get("jobs") or []:
            if not title_re.search(j.get("title") or ""):
                continue
            wt = j.get("workplaceType") or ("Remote" if j.get("isRemote") else "")  # isRemote is also true for Hybrid jobs
            locs = [j.get("location") or ""] + [x.get("location", "") for x in j.get("secondaryLocations") or []]
            comp = (j.get("compensation") or {}).get("compensationTierSummary")
            out.append(job("ATS:ashby", f"{slug}-{j.get('id')}", j.get("title"), slug, f"{wt} " + "; ".join(x for x in locs if x),
                           j.get("jobUrl"), (j.get("descriptionPlain") or "") + (f" Compensation: {comp}" if comp else ""),
                           pdate(j.get("publishedAt"))))
    elif kind == "lever":
        for j in d if isinstance(d, list) else []:
            if not title_re.search(j.get("text") or ""):
                continue
            c = j.get("categories") or {}
            sr = j.get("salaryRange") or None
            sal = dict(min=sr.get("min"), max=sr.get("max"), cur=sr.get("currency"), per=str(sr.get("interval") or "").replace("per-", "")) if sr else None
            text = " ".join(str(j.get(k) or "") for k in ("descriptionPlain", "additionalPlain")) + " " + " ".join(strip(x.get("content")) for x in j.get("lists") or [])
            out.append(job("ATS:lever", f"{slug}-{j.get('id')}", j.get("text"), slug,
                           f"{j.get('workplaceType') or ''} {c.get('location') or ''} {' '.join(c.get('allLocations') or [])}",
                           j.get("hostedUrl"), text, pdate(j["createdAt"] // 1000) if j.get("createdAt") else None, sal))
    elif kind == "workable":
        for j in (d or {}).get("jobs") or []:
            if title_re.search(j.get("title") or ""):
                loc = ("remote " if j.get("telecommuting") else "") + ", ".join(x for x in (j.get("city"), j.get("state"), j.get("country")) if x)
                out.append(job("ATS:workable", f"{slug}-{j.get('shortcode')}", j.get("title"), d.get("name") or slug, loc,
                               j.get("url") or j.get("shortlink"), j.get("description") or "", pdate(j.get("published_on") or j.get("created_at"))))
    return out


def src_ats(cfg):
    """Companies' own job boards (Greenhouse, Ashby, Lever, Workable) listed in filters.md -> atsBoards.
    Catches openings before the aggregators do. Find a company's slug with: scan.py --probe-ats name1,name2"""
    title_re = ats_title_re(cfg)
    pairs = [(k, s) for k, slugs in cfg["atsBoards"].items() if k in ATS_APIS for s in slugs]
    out = []
    with ThreadPoolExecutor(8) as ex:
        for r in ex.map(lambda p: ats_board(p[0], p[1], title_re), pairs):
            out += r
    return out


def probe_ats(slugs):
    """Which job-board systems answer for these company slugs, and how many jobs each lists."""
    for s in slugs:
        hits = []
        for kind, url in ATS_APIS.items():
            d = getj(url.format(s), timeout=20)
            n = len(d) if isinstance(d, list) else len((d or {}).get("jobs") or []) if isinstance(d, dict) and "jobs" in d else None
            if n:  # an empty board looks the same as a missing one on some systems
                hits.append(f"{kind} ({n} jobs)")
        print(f"{s}: {', '.join(hits) or 'not found (try another slug: name, name-ai, namehq…)'}")


SOURCES = {name[4:]: fn for name, fn in list(globals().items()) if name.startswith("src_")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--only", help="comma-separated source names: " + ",".join(SOURCES))
    ap.add_argument("--probe-ats", help="comma-separated company slugs: find which job-board system each uses, then exit")
    a = ap.parse_args()
    if a.probe_ats:
        return probe_ats([x.strip() for x in a.probe_ats.split(",") if x.strip()])
    ws = os.path.abspath(os.path.expanduser(a.workspace))
    cfg = load_config(ws)
    cfg["_workspace"] = ws
    enabled = [s for s, on in cfg["sources"].items() if on and s in SOURCES
               and (s != "ats" or any(cfg["atsBoards"].values()))]  # no company boards listed yet: nothing to scan
    if a.only:
        enabled = [s.strip() for s in a.only.split(",") if s.strip()]
        bad = [s for s in enabled if s not in SOURCES]
        if bad:
            raise SystemExit(f"unknown source(s): {', '.join(bad)}. Valid: {', '.join(SOURCES)}")
    allj, stats = [], {}
    with ThreadPoolExecutor(6) as ex:
        futs = {s: ex.submit(SOURCES[s], cfg) for s in enabled}
        for s, fu in futs.items():
            try:
                r = fu.result()
            except Exception as e:
                print("ERR", s, repr(e), file=sys.stderr)
                r = []
            stats[s] = len(r)
            if not r:
                print(f"{s}: 0 jobs (network problem, key, rate limit or no match?)", file=sys.stderr)
            allj += r
    out = os.path.join(ws, "search", "scans")
    os.makedirs(out, exist_ok=True)
    fn = os.path.join(out, f"raw-{dt.date.today().isoformat()}.json")
    if os.path.exists(fn):  # never replace a good same-day scan with an empty or much smaller one
        prev = len(read_json(fn))
        if len(allj) < prev / 2:
            fn = fn.replace(".json", f"-{dt.datetime.now():%H%M}.json")
            print(f"this scan ({len(allj)} jobs) is much smaller than today's earlier one ({prev}); kept that and saved this as {os.path.basename(fn)}",
                  file=sys.stderr)
    write_atomic(fn, json.dumps(allj))
    print(json.dumps(stats), "total", len(allj))
    print("saved", fn)


if __name__ == "__main__":
    main()

"""Find reference photos of a place when the user gave none (or too few).

    python3 photos.py <project> [--query "Lotus Tower Colombo"] [--max 24] [--browser]
    python3 photos.py <project> --drop cc_04,cc_08        (set aside what is not the place: art, interiors, models)

Tier 1 (always): sources that publish photos under stated licences, through their public APIs.
    Wikimedia Commons   photos taken near the pin (geosearch) and photos found by the place's name
    Wikidata            the place's main image, and facts: height, year (saved to refs/_facts.json)
    Openverse           Creative Commons photos by name
  Files: refs/cc_NN_<source>.jpg. Licence and author are recorded; these may be shown with credit.

Tier 2 (only with --browser or PF_PHOTO_BROWSER=1 in .env): a public image-search results page, read in a browser.
CloakBrowser is installed on first use into ~/.cache/placeforge/cloak-venv (nothing is bundled in this repository):
version 0.6.3, whose free browser build runs without a licence key; with CLOAKBROWSER_LICENSE_KEY in .env the current
release is used instead. If it cannot be installed or started, the Chrome already on this machine does the same job.
  Rules: read-only; public pages; no login; one page at a time; 10 s between
  searches; at most three searches and 30 images; on a captcha or a block it stops and says so (no retry, no other
  engine).
  Files: refs/web_NN.jpg. Licence unknown: reference only, never publish them. They are git-ignored.

Every photo is listed in refs/_sources.json; refs/CREDITS.md has the credit lines for the licensed ones.
Then: pf refs <project>, look at the contact sheet, choose the target, and tell the user what was found.
"""
import hashlib, html, json, math, os, re, subprocess, sys, time, urllib.parse, urllib.request

UA = "placeforge-landmark/0.1 (open-source 3D place builder)"
COMMONS = "https://commons.wikimedia.org/w/api.php"
WIKIDATA = "https://www.wikidata.org/w/api.php"
OPENVERSE = "https://api.openverse.org/v1/images/"
NOT_A_PHOTO = re.compile(r"\b(map|logo|plan|diagram|flag|coat of arms|locator|icon|stamp|banknote|coin|drawing|sketch|blueprint|chart|poster|ticket|sign)\b|\.svg|\.gif|\.tif", re.I)
HERE = os.path.dirname(os.path.abspath(__file__))
VENV = os.path.expanduser("~/.cache/placeforge/cloak-venv")
# CloakBrowser 0.6.3 is the last line whose free browser build launches without a licence key (0.7 asks for one at
# launch). It needs a Playwright of its time: newer ones dropped a module it imports.
CLOAK_FREE = ("cloakbrowser==0.6.3", "playwright==1.60.0")
CLOAK_KEYED = ("cloakbrowser", "playwright")       # with CLOAKBROWSER_LICENSE_KEY in .env: the current release


def get(url, params=None, timeout=40, raw=False):
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)
    data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout).read()
    return data if raw else json.loads(data)


def strip(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", s or ""))).strip()[:160]


def commons_items(d, source):
    out = []
    for p in sorted((d.get("query") or {}).get("pages") or [], key=lambda p: p.get("index", 0)):
        ii = (p.get("imageinfo") or [{}])[0]
        if ii.get("mime") not in ("image/jpeg", "image/png") or ii.get("width", 0) < 1000 or NOT_A_PHOTO.search(p.get("title", "")):
            continue
        m = ii.get("extmetadata") or {}
        v = lambda k: strip((m.get(k) or {}).get("value", ""))
        out.append({"source": source, "title": p["title"].replace("File:", ""), "url": ii.get("thumburl") or ii["url"],
                    "page": ii.get("descriptionurl", ""), "author": v("Artist") or "unknown", "licence": v("LicenseShortName") or "see page",
                    "w": ii.get("width"), "h": ii.get("height"), "date": v("DateTimeOriginal")[:10]})
    return out


def commons_near(lat, lon, radius):
    d = get(COMMONS, {"action": "query", "format": "json", "formatversion": 2, "generator": "geosearch", "ggscoord": "%f|%f" % (lat, lon),
                      "ggsradius": int(min(10000, max(radius * 2.5, 1500))), "ggslimit": 60, "ggsnamespace": 6,
                      "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1600})
    return commons_items(d, "commons-near")


def commons_named(query):
    d = get(COMMONS, {"action": "query", "format": "json", "formatversion": 2, "generator": "search", "gsrsearch": query + " filetype:bitmap",
                      "gsrnamespace": 6, "gsrlimit": 50, "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1600})
    return commons_items(d, "commons-name")


def wikidata(query, lat, lon):
    """The entity with this name within 3 km of the pin: its main image and a few facts."""
    facts, items = {}, []
    hits = get(WIKIDATA, {"action": "wbsearchentities", "format": "json", "language": "en", "search": query, "limit": 6}).get("search", [])
    for h in hits:
        e = get(WIKIDATA, {"action": "wbgetentities", "format": "json", "ids": h["id"], "props": "claims|labels"})["entities"][h["id"]]
        c = e.get("claims", {})
        val = lambda p: ((c.get(p) or [{}])[0].get("mainsnak", {}).get("datavalue", {}) or {}).get("value")
        co = val("P625")
        if not co:
            continue
        dist = math.hypot((co["latitude"] - lat) * 110574, (co["longitude"] - lon) * 111320 * math.cos(math.radians(lat)))
        if dist > 3000:
            continue
        facts = {"wikidata": h["id"], "label": h.get("label"), "description": h.get("description"), "pin_offset_m": round(dist)}
        if val("P2048"):
            facts["height_m"] = float(val("P2048")["amount"])
        if val("P571"):
            facts["inception"] = val("P571")["time"][1:11]
        if val("P2046"):
            facts["area"] = val("P2046")["amount"]
        img = val("P18")
        if img:
            d = get(COMMONS, {"action": "query", "format": "json", "formatversion": 2, "titles": "File:" + img, "prop": "imageinfo",
                              "iiprop": "url|size|mime|extmetadata", "iiurlwidth": 1600})
            items = commons_items(d, "wikidata-main")
        break
    return facts, items


def openverse(query):
    d = get(OPENVERSE, {"q": query, "page_size": 20, "mature": "false"})
    out = []
    for r in d.get("results", []):
        if (r.get("width") or 0) < 1000 or NOT_A_PHOTO.search(r.get("title") or ""):
            continue
        out.append({"source": "openverse", "title": (r.get("title") or "")[:120], "url": r["url"], "page": r.get("foreign_landing_url", ""),
                    "author": r.get("creator") or "unknown", "licence": ("CC %s %s" % (r.get("license", ""), r.get("license_version") or "")).upper().strip(),
                    "w": r.get("width"), "h": r.get("height"), "date": ""})
    return out


def cloak_python(key=""):
    """The skill's own Python with CloakBrowser in it (~/.cache/placeforge/cloak-venv), installed on first use.
    Without a licence key: the pinned free line. With one: the current release."""
    import shutil
    py = os.path.join(VENV, "bin", "python") if os.name != "nt" else os.path.join(VENV, "Scripts", "python.exe")
    ok = lambda: os.path.exists(py) and subprocess.run([py, "-I", "-c", "import cloakbrowser"], capture_output=True).returncode == 0
    ver = lambda: subprocess.run([py, "-I", "-c", "import cloakbrowser; print(cloakbrowser.__version__)"], capture_output=True, text=True).stdout.strip()
    want = CLOAK_KEYED if key else CLOAK_FREE
    if ok() and (key or ver() == CLOAK_FREE[0].split("==")[1]):
        return py
    base = next((p for p in ("python3.13", "python3.12", "python3.11", "python3.10", "python3") if shutil.which(p) and subprocess.run(
        [p, "-c", "import sys; sys.exit(sys.version_info < (3, 9))"], capture_output=True).returncode == 0), None)
    if not base:
        return None
    print("browser tier: installing CloakBrowser into %s (about 200 MB, once; its browser, about 350 MB, downloads on first launch)" % VENV, flush=True)
    os.makedirs(os.path.dirname(VENV), exist_ok=True)
    if not os.path.exists(py) and subprocess.run([base, "-m", "venv", VENV]).returncode:
        return None
    if subprocess.run([py, "-m", "pip", "install", "-q", "--disable-pip-version-check", "-U", *want]).returncode:
        return None
    return py if ok() else None


def browser_search(query, limit, key=""):
    """CloakBrowser (installed on first use; its free build needs no key), else the Chrome already on this machine.
    Chrome is only the fallback for a browser that will not install or start; a search page that blocks is never
    retried in the other browser. Same rules either way; see photos_browser.py."""
    script, env = os.path.join(HERE, "photos_browser.py"), dict(os.environ)

    def run(cmd):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=900, env=env, cwd=HERE)
        except subprocess.TimeoutExpired:
            return None, "timed out"
        for line in r.stdout.splitlines()[::-1]:
            if line.startswith("{"):
                return json.loads(line), ""
        return None, re.sub(r"https?://\S+", "<link>", (r.stderr.strip().splitlines() or ["?"])[-1])[:160]

    res, py = None, cloak_python(key)
    if py:
        if key:
            env["CLOAKBROWSER_LICENSE_KEY"] = key
        res, err = run([py, "-I", script, "cloak", query, str(limit)])     # -I: a stray json.py in a folder must not shadow the standard library
        if res is None:
            print("browser tier: CloakBrowser did not start (%s); using this machine's Chrome" % err)
    else:
        print("browser tier: CloakBrowser could not be installed here (needs Python 3.9+ and pip); using this machine's Chrome")
    if res is None:
        # not -I here: it would hide packages installed with pip --user. cwd = this folder, so nothing foreign is imported
        if subprocess.run([sys.executable, "-c", "import websocket"], capture_output=True, cwd=HERE).returncode:
            print("browser tier: Chrome needs `pip install websocket-client`. Skipped.")
            return []
        res, err = run([sys.executable, script, "chrome", query, str(limit)])
        if res is None:
            print("browser tier: no answer from Chrome (%s)" % err)
            return []
    print("browser tier: %s, %d results%s" % (res.get("engine"), len(res.get("items", [])),
          ("; then a page asked for verification or came back empty: stopped there (no retry)" if res.get("items") else
           ": the search page asked for verification or showed nothing. Stopped (no retry). Ask the user for photos.") if res.get("blocked") else ""))
    return [{"source": "web-search", "title": i.get("title", "")[:120], "url": i["url"], "page": i.get("page", ""), "author": "unknown",
             "licence": "unknown: reference only, do not publish", "w": 0, "h": 0, "date": ""} for i in res.get("items", [])]


def main():
    a = sys.argv[1:]
    if not a:
        raise SystemExit(__doc__)
    proj = os.path.abspath(a[0])
    P = json.load(open(os.path.join(proj, "place.json")))
    opt = lambda k, d=None: a[a.index(k) + 1] if k in a else d
    if "--drop" in a:                 # photos.py P --drop cc_04,web_02 : set aside what is not this place (paintings, interiors)
        refs, n = os.path.join(proj, "refs"), 0
        os.makedirs(os.path.join(refs, "_rejected"), exist_ok=True)
        for f in sorted(os.listdir(refs)):
            if any(f.startswith(k.strip()) for k in opt("--drop").split(",") if k.strip()) and os.path.isfile(os.path.join(refs, f)):
                os.replace(os.path.join(refs, f), os.path.join(refs, "_rejected", f))
                n += 1
        print("set aside %d photo(s) in refs/_rejected/ (pf refs skips them)" % n)
        return
    query, cap = opt("--query", P["name"]), int(opt("--max", 24))
    lat, lon, radius = float(P["lat"]), float(P["lon"]), float(P.get("radius_m", 800))
    env = open(os.path.join(proj, ".env")).read() if os.path.exists(os.path.join(proj, ".env")) else ""
    use_browser = "--browser" in a or re.search(r"^\s*PF_PHOTO_BROWSER\s*=\s*(1|true|yes)\s*$", env, re.M | re.I) or os.environ.get("PF_PHOTO_BROWSER") == "1"
    refs = os.path.join(proj, "refs")
    os.makedirs(refs, exist_ok=True)
    sp = os.path.join(refs, "_sources.json")
    known = json.load(open(sp)) if os.path.exists(sp) else []
    pools, facts = [], {}
    def wd():
        for q in dict.fromkeys((query, P["name"])):          # the bare name finds the entity when "name + city" does not
            f, r = wikidata(q, lat, lon)
            if f:
                return f, r
        return {}, []

    for name, fn in (("wikidata", wd), ("commons-name", lambda: commons_named(query)), ("commons-name", lambda: commons_named(query)[25:]),
                     ("commons-near", lambda: commons_near(lat, lon, radius)), ("openverse", lambda: openverse(query))):
        try:
            r = fn()
            if name == "wikidata":
                facts, r = r
            pools.append(r)
            print("%-13s %d candidates" % (name, len(r)), flush=True)
        except Exception as e:
            print("%-13s failed (%s)" % (name, str(e)[:70]))
        time.sleep(1.0)
    if facts:
        json.dump(facts, open(os.path.join(refs, "_facts.json"), "w"), indent=1)
        print("facts:", facts)
    # round-robin across sources so one source cannot fill the quota; licensed tier first
    picked, seen = [], {k["url"] for k in known}
    while len(picked) < cap and any(pools):
        for pool in pools:
            while pool:
                it = pool.pop(0)
                if it["url"] not in seen and it["title"] not in {p["title"] for p in picked}:
                    seen.add(it["url"])
                    picked.append(it)
                    break
            if len(picked) >= cap:
                break
    web = []
    if use_browser:
        km = re.search(r"^[ \t]*CLOAKBROWSER_LICENSE_KEY[ \t]*=[ \t]*([^\s#]+)", env, re.M)      # same line only: an empty value is no key
        web = [i for i in browser_search(query, 30, os.environ.get("CLOAKBROWSER_LICENSE_KEY") or (km.group(1).strip("\"'") if km else "")) if i["url"] not in seen][:30]
        print("%-13s %d candidates" % ("web-search", len(web)))
    hashes = {k.get("sha1") for k in known}
    n_cc = sum(1 for k in known if k["tier"] == 1)
    n_web = sum(1 for k in known if k["tier"] == 2)
    got = 0
    for it in picked + web:
        tier = 2 if it["source"] == "web-search" else 1
        try:
            data = get(it["url"], timeout=60, raw=True)
        except Exception:
            continue
        if len(data) < 30000 or data[:3] not in (b"\xff\xd8\xff", b"\x89PN"):
            continue
        h = hashlib.sha1(data).hexdigest()
        if h in hashes:
            continue
        hashes.add(h)
        ext = ".png" if data[:3] == b"\x89PN" else ".jpg"
        if tier == 1:
            n_cc += 1
            fn = "cc_%02d_%s%s" % (n_cc, it["source"].split("-")[0], ext)
        else:
            n_web += 1
            fn = "web_%02d%s" % (n_web, ext)
        open(os.path.join(refs, fn), "wb").write(data)
        try:
            from PIL import Image
            it["w"], it["h"] = Image.open(os.path.join(refs, fn)).size
            if it["w"] < 700:
                os.remove(os.path.join(refs, fn))
                continue
        except ImportError:
            pass
        known.append(dict(it, file=fn, tier=tier, sha1=h, fetched=time.strftime("%Y-%m-%d")))
        got += 1
        time.sleep(0.4)
    json.dump(known, open(sp, "w"), indent=1)
    with open(os.path.join(refs, "CREDITS.md"), "w") as f:
        f.write("# Reference photo credits\n\nLicensed photos (may be shown with this credit):\n\n")
        for k in known:
            if k["tier"] == 1:
                f.write("- `%s`: \"%s\" by %s, %s. %s\n" % (k["file"], k["title"], k["author"], k["licence"], k["page"]))
        if any(k["tier"] == 2 for k in known):
            f.write("\nFound by web search (licence unknown: reference only, never publish):\n\n")
            for k in known:
                if k["tier"] == 2:
                    f.write("- `%s`: %s\n" % (k["file"], k["page"] or k["url"]))
    gi = os.path.join(proj, ".gitignore")
    if os.path.exists(gi) and "refs/web_*" not in open(gi).read():
        open(gi, "a").write("refs/web_*\n")
    t1, t2 = sum(1 for k in known if k["tier"] == 1), sum(1 for k in known if k["tier"] == 2)
    print("photos: %d new; %d licensed (cc_*), %d web-search (web_*, reference only) in %s" % (got, t1, t2, refs))
    if t1 + t2 < 3:
        print("TOO FEW: ask the user for photos (one wide, level view and two close-ups)%s." % ("" if use_browser else ", or rerun with --browser if they agree to a web image search"))
    else:
        print("next: pf refs %s ; read refs/_contact.jpg ; set refs.target in place.json to the best wide, level photo ; tell the user which photos were found" % proj)


if __name__ == "__main__":
    main()

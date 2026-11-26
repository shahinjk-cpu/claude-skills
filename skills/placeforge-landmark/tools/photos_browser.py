"""Tier 2 of photos.py: read a public image-search results page in a browser and list what it shows.
Prints one JSON line: {"items": [...], "blocked": bool, "engine": "chrome" | "cloakbrowser"}.

    python3 -I photos_browser.py chrome "<query>" <limit>          the Chrome already on this machine (DevTools protocol)
    <cloak venv python> -I photos_browser.py cloak "<query>" <limit>   CloakBrowser (needs CLOAKBROWSER_LICENSE_KEY)

Rules (do not loosen them): read-only; public results pages; no login; a fresh empty profile that is deleted after;
one page at a time; 10 s between searches; at most three searches; on a captcha, a verification wall or a page with
no results it stops and reports blocked. It never retries and never switches engine.
"""
import json, os, shutil, subprocess, sys, tempfile, time, urllib.parse, urllib.request

ENGINE = "https://www.bing.com/images/search?form=HDRSC2&first=1&q="
WALL = ("captcha", "verify you are human", "unusual traffic", "are you a robot", "access denied")
TILES = "Array.from(document.querySelectorAll('a.iusc')).map(e => e.getAttribute('m'))"
BODY = "(document.body ? document.body.innerText : '').slice(0, 4000).toLowerCase()"


def search(goto, evaluate, query, limit):
    items, blocked, seen = [], False, set()
    for k, extra in enumerate(("", " aerial view", " close up")):
        if k:
            time.sleep(10)
        goto(ENGINE + urllib.parse.quote(query + extra))
        time.sleep(3.0)
        body = evaluate(BODY) or ""
        if any(w in body for w in WALL):
            blocked = True
            break
        evaluate("window.scrollBy(0, 2400)")
        time.sleep(1.5)
        found = evaluate(TILES) or []
        if not found:
            blocked = True
            break
        n = 0
        for m in found:
            try:
                d = json.loads(m)
            except Exception:
                continue
            u = d.get("murl", "")
            if not u.startswith("http") or u in seen or not u.lower().split("?")[0].endswith((".jpg", ".jpeg", ".png")):
                continue
            seen.add(u)
            items.append({"url": u, "page": d.get("purl", ""), "title": d.get("t", "")})
            n += 1
            if n >= limit // 3 + 1 or len(items) >= limit:
                break
        if len(items) >= limit:
            break
    return items, blocked


def with_cloak(query, limit):
    from cloakbrowser import launch
    browser = launch(headless=True)
    try:
        page = browser.new_page()
        return search(lambda u: page.goto(u, wait_until="domcontentloaded", timeout=45000), page.evaluate, query, limit)
    finally:
        browser.close()


def with_chrome(query, limit):
    import websocket                                  # pip install websocket-client
    exe = next((p for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", shutil.which("google-chrome") or "",
                            shutil.which("chromium") or "", shutil.which("chromium-browser") or "",
                            r"C:\Program Files\Google\Chrome\Application\chrome.exe") if p and os.path.exists(p)), None)
    if not exe:
        raise SystemExit("no Chrome or Chromium found on this machine")
    prof, port = tempfile.mkdtemp(prefix="pf-photos-"), 9347
    p = subprocess.Popen([exe, "--headless=new", "--remote-debugging-port=%d" % port, "--user-data-dir=" + prof, "--window-size=1400,2200",
                          "--no-first-run", "--remote-allow-origins=*", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        tabs = None
        for _ in range(60):
            try:
                tabs = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json" % port))
                break
            except Exception:
                time.sleep(0.25)
        ws = websocket.create_connection([t for t in tabs if t["type"] == "page"][0]["webSocketDebuggerUrl"], timeout=60)
        n = [0]

        def call(method, **params):
            n[0] += 1
            ws.send(json.dumps({"id": n[0], "method": method, "params": params}))
            while True:
                m = json.loads(ws.recv())
                if m.get("id") == n[0]:
                    return m.get("result", {})

        call("Page.enable")
        call("Runtime.enable")
        goto = lambda u: call("Page.navigate", url=u)
        evaluate = lambda e: call("Runtime.evaluate", expression=e, returnByValue=True).get("result", {}).get("value")
        return search(goto, evaluate, query, limit)
    finally:
        p.terminate()
        p.wait()
        shutil.rmtree(prof, ignore_errors=True)


if __name__ == "__main__":
    engine, query, limit = sys.argv[1], sys.argv[2], int(sys.argv[3])
    items, blocked = (with_cloak if engine == "cloak" else with_chrome)(query, limit)
    print(json.dumps({"items": items, "blocked": blocked, "engine": "cloakbrowser" if engine == "cloak" else "chrome"}))

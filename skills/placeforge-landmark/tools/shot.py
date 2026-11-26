"""shot.py URL OUT.png [settle_seconds] [WxH] : open the page in headless Chrome, wait for window.__ready, capture.
Prints console messages and uncaught errors. (Chrome DevTools Protocol over a websocket.)"""
import sys, json, time, subprocess, urllib.request, base64, tempfile, websocket
url, out = sys.argv[1], sys.argv[2]
settle = float(sys.argv[3]) if len(sys.argv) > 3 else 4.0
W, H = (sys.argv[4] if len(sys.argv) > 4 else "1200x800").split("x")
port = 9333
prof = tempfile.mkdtemp()
p = subprocess.Popen(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--headless=new", "--remote-debugging-port=%d" % port,
                      "--user-data-dir=" + prof, "--window-size=%s,%s" % (W, H), "--hide-scrollbars", "--remote-allow-origins=*", "about:blank"],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
try:
    for _ in range(50):
        try:
            tabs = json.load(urllib.request.urlopen("http://127.0.0.1:%d/json" % port)); break
        except Exception:
            time.sleep(0.2)
    ws = websocket.create_connection([t for t in tabs if t["type"] == "page"][0]["webSocketDebuggerUrl"], timeout=120)
    n = [0]
    def call(method, **params):
        n[0] += 1; ws.send(json.dumps({"id": n[0], "method": method, "params": params}))
        while True:
            m = json.loads(ws.recv())
            if m.get("id") == n[0]: return m.get("result", {})
            if m.get("method") == "Runtime.consoleAPICalled":
                print("console:", " ".join(str(a.get("value", a.get("description", ""))) for a in m["params"]["args"])[:300])
            if m.get("method") == "Runtime.exceptionThrown":
                d = m["params"]["exceptionDetails"]; print("EXCEPTION:", (d.get("exception", {}).get("description") or d.get("text"))[:600])
    call("Runtime.enable"); call("Page.enable")
    call("Page.navigate", url=url)
    t0 = time.time(); ready = False
    while time.time() - t0 < 120:
        r = call("Runtime.evaluate", expression="window.__ready === true")
        if r.get("result", {}).get("value"): ready = True; break
        time.sleep(0.5)
    print("ready" if ready else "NOT READY", "%.1f s" % (time.time() - t0))
    import os
    if os.environ.get("PRE"): call("Runtime.evaluate", expression=os.environ["PRE"])
    time.sleep(settle)
    r = call("Runtime.evaluate", awaitPromise=True, expression="new Promise(r => { let n = 0; const t0 = performance.now(); const f = () => { n++; if (performance.now() - t0 < 2000) requestAnimationFrame(f); else r(n / ((performance.now() - t0) / 1000)); }; requestAnimationFrame(f); })")
    print("FPS %.1f" % r.get("result", {}).get("value", 0))
    call("Runtime.evaluate", expression="1")
    open(out, "wb").write(base64.b64decode(call("Page.captureScreenshot", format="png")["data"]))
finally:
    p.terminate()
    p.wait()
    time.sleep(0.5)

"""Export PNG mockups from a rendered output folder using headless Chrome/Edge.

Usage:
    python export_png.py OUTPUT_DIR [--ads A1,A2] [--placements ig_reels,fb_feed_mobile]
                         [--dark] [--badges] [--scale 2] [--workers 4] [--all-cards]

OUTPUT_DIR is the folder render.py wrote (it contains index.html and data.js).
PNGs go to OUTPUT_DIR/png/<ad>__<placement>[__dark][__cardN].png. Only actual or
simulated mockups are exported. Clean in-situ view by default (no overlays).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

KEY = (1, 254, 2)  # export-mode page background, trimmed away


def find_browser(explicit=None):
    if explicit:
        if os.path.exists(explicit):
            return explicit
        sys.exit(f"--browser path not found: {explicit}")
    cands = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
             r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
             r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser"),
             shutil.which("chrome"), shutil.which("msedge")]
    for c in cands:
        if c and os.path.exists(c):
            return c
    sys.exit("No Chrome/Edge found. Pass the browser executable with --browser PATH.")


def load_data(out):
    txt = (out / "data.js").read_text(encoding="utf-8")
    return json.loads(txt[txt.index("=") + 1:].strip().rstrip(";"))


def trim(png):
    from PIL import Image
    with Image.open(png) as im:
        im = im.convert("RGB")
        px = im.load()
        w, h = im.size
        def is_key(p):
            return abs(p[0] - KEY[0]) < 12 and abs(p[1] - KEY[1]) < 12 and abs(p[2] - KEY[2]) < 12
        bottom = h
        step = max(1, w // 40)
        while bottom > 1 and all(is_key(px[x, bottom - 1]) for x in range(0, w, step)):
            bottom -= 1
        right = w
        while right > 1 and all(is_key(px[right - 1, y]) for y in range(0, bottom, max(1, bottom // 40))):
            right -= 1
        im.crop((0, 0, right, bottom)).save(png, optimize=True)


def shoot(browser, url, png, width, height, scale, profile):
    cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--mute-audio",
           "--no-first-run", "--no-default-browser-check", "--allow-file-access-from-files",
           f"--force-device-scale-factor={scale}", f"--window-size={width},{height}",
           "--virtual-time-budget=6000", f"--user-data-dir={profile}",
           f"--screenshot={png}", url]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if not Path(png).exists():
        raise RuntimeError(r.stderr.strip()[-300:] or "no screenshot written")
    trim(png)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--ads")
    ap.add_argument("--placements")
    ap.add_argument("--dark", action="store_true")
    ap.add_argument("--badges", action="store_true", help="include simulated/placeholder warning badges")
    ap.add_argument("--safe", action="store_true", help="draw Stories/Reels safe-zone overlays")
    ap.add_argument("--limits", action="store_true", help="draw text-length / truncation markers")
    ap.add_argument("--scale", type=float, default=2.0, help="device pixel ratio (2 = retina-sharp)")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--all-cards", action="store_true", help="carousels in Stories/Reels: one PNG per card")
    ap.add_argument("--browser", help="path to Chrome/Edge, if it isn't found automatically")
    a = ap.parse_args()

    out = Path(a.out).resolve()
    if not (out / "index.html").exists():
        sys.exit(f"{out} has no index.html; run render.py first")
    data = load_data(out)
    pl = {p["id"]: p for p in data["placements"]}
    ads = [x["id"] for x in data["ads"]]
    if a.ads:
        want = a.ads.split(",")
        bad = [x for x in want if x not in ads]
        if bad:
            sys.exit(f"unknown ad id(s): {', '.join(bad)}")
        ads = want
    pls = list(pl)
    if a.placements:
        pls = a.placements.split(",")
        bad = [x for x in pls if x not in pl]
        if bad:
            sys.exit(f"unknown placement(s): {', '.join(bad)}")
    adm = {x["id"]: x for x in data["ads"]}

    jobs = []
    for ad in ads:
        for pid in pls:
            cell = data["matrix"][ad][pid]
            if cell["status"] not in ("actual", "simulated"):
                continue
            p = pl[pid]
            full = p["template"] in ("fb_stories", "ig_stories", "fb_reels", "ig_reels")
            cards = [0]
            if a.all_cards and full and adm[ad]["format"] == "carousel":
                cards = list(range(len(adm[ad]["cards"])))
            for ci in cards:
                flags = {"dark": a.dark, "badges": a.badges, "safe": a.safe, "trunc": a.limits}
                frag = f"export&ad={ad}&pl={pid}&card={ci}&" + "&".join(f"{k}={'1' if v else '0'}" for k, v in flags.items())
                tags = "".join(f"__{t}" for t, on in (("dark", a.dark), ("review", a.badges or a.safe or a.limits)) if on)
                name = f"{ad}__{pid}{tags}{f'__card{ci+1}' if len(cards) > 1 else ''}.png"
                w = 1280 if p["device"] == "desktop" else 393
                h = 852 if full else (2600 if p["device"] == "desktop" else 2600)  # tall window; trim() removes the excess
                jobs.append(((out / "index.html").as_uri() + "#" + frag, name, w, h))
    if not jobs:
        print("Nothing to export (no actual/simulated mockups match).")
        return
    png_dir = out / "png"
    png_dir.mkdir(exist_ok=True)
    browser = find_browser(a.browser)
    tmp = Path(tempfile.mkdtemp(prefix="metaads-chrome-"))
    profiles = [tmp / f"p{i}" for i in range(max(1, a.workers))]
    print(f"Exporting {len(jobs)} PNG(s) with {Path(browser).name} ...")
    failures = []

    def run(i_job):
        i, (url, name, w, h) = i_job
        try:
            shoot(browser, url, str(png_dir / name), w, h, a.scale, profiles[i % len(profiles)])
            return None
        except Exception as e:  # noqa: BLE001
            return f"{name}: {e}"

    # one job per profile at a time: chunk by worker index
    with ThreadPoolExecutor(max_workers=len(profiles)) as ex:
        chunks = [[(i, j) for i, j in enumerate(jobs) if i % len(profiles) == k] for k in range(len(profiles))]
        def run_chunk(ch):
            return [r for r in (run(x) for x in ch) if r]
        for res in ex.map(run_chunk, chunks):
            failures.extend(res)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"Wrote {len(jobs) - len(failures)} PNG(s) to {png_dir}")
    for f in failures:
        print("  FAILED", f)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()

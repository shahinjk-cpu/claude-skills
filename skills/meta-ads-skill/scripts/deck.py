"""Build a designed slide deck (PDF and/or PowerPoint) from rendered mockups.

Usage:
    python deck.py quick --library DIR --ads A1,A2 [--layout concept|lineup|versus]
                         [--placements fb_feed_mobile,ig_feed,ig_reels] [--format pdf,pptx]
                         [--title "..."] [--subtitle "..."] [--dark]
    python deck.py build DECK.json [--format pdf,pptx]

--library is a library folder (meta-ads/<library>, with ads.json and viewer/) or a viewer
folder render.py wrote. `quick` writes a deck file next to the output and builds it; edit
that .deck.json (titles, slide order, notes) and run `build` to rebuild.

Layouts:
  concept  one slide per ad: the ad in up to 3 placements, with its copy as text
  lineup   ads side by side in one placement (the first of --placements), up to 4 per slide
  versus   brand against brand in one placement: the chosen ads must come from exactly two
           brands; up to 3 ads per side per slide

--dark draws the mockups in the apps' dark mode (a deck file stores it as "dark": true); the
viewer adds it when the user has the viewer in dark mode.

Every deck gets a cover and a closing "about these mockups" slide. Output goes to the
library's exports/ folder (or next to the deck file for `build`). The PDF is printed by
headless Chrome/Edge, the PowerPoint is written with python-pptx (editable text, mockups as
images, full ad text in the speaker notes). Videos appear as their cover frame.
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import export_png  # noqa: E402  (headless browser + screenshot trimming)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

W, H = 1920, 1080            # slide grid in px; PowerPoint: 1 px = 6350 EMU = 0.5 pt (13.333 x 7.5 in)
EMU = 6350
M = 96                       # side margin
THEME = {"bg": "#F4F3EF", "panel": "#FFFFFF", "text": "#16181D", "sub": "#636A73", "line": "#DEDBD3",
         "accent": "#2F5BEA", "font": "Segoe UI"}
DEFAULT_PL = ["fb_feed_mobile", "ig_feed", "ig_reels"]
FALLBACK_PL = ["ig_stories", "fb_stories", "fb_reels", "fb_feed_desktop"]
FULLSCREEN = ("fb_stories", "ig_stories", "fb_reels", "ig_reels")


# ------------------------------------------------------------------ data
def slug(s):
    s = re.sub(r"[^A-Za-z0-9]+", "-", s or "deck").strip("-").lower()
    return s[:50] or "deck"


def clip(t, n):
    t = re.sub(r"\s+", " ", (t or "")).strip()
    if len(t) <= n:
        return t
    cut = t[:n - 1]
    if " " in cut[int(n * 0.6):]:
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" ,.;:-") + "…"


def viewer_dir(p):
    p = Path(p).resolve()
    if (p / "viewer" / "data.js").exists():
        return p / "viewer"
    if (p / "data.js").exists():
        return p
    sys.exit(f"{p} is not a rendered library or viewer folder (no data.js); render it first")


class Lib:
    def __init__(self, path):
        self.viewer = viewer_dir(path)
        txt = (self.viewer / "data.js").read_text(encoding="utf-8")
        self.data = json.loads(txt[txt.index("=") + 1:].strip().rstrip(";"))
        self.stamp = str((self.viewer / "data.js").stat().st_mtime_ns)
        self.ads = {a["id"]: a for a in self.data["ads"]}
        self.pl = {p["id"]: p for p in self.data["placements"]}
        self.name = (self.data.get("campaign") or {}).get("name") or self.viewer.parent.name

    def ad(self, ad_id):
        if ad_id not in self.ads:
            sys.exit(f"ad {ad_id} is not in {self.name}")
        return self.ads[ad_id]

    def status(self, ad_id, pl):
        return ((self.data["matrix"].get(ad_id) or {}).get(pl) or {}).get("status")

    def eligible(self, ad_id, pl):
        return self.status(ad_id, pl) in ("actual", "simulated")

    def brand(self, ad):
        b = (self.data.get("brands") or {}).get(ad.get("brand")) or {}
        return b.get("page_name") or ad.get("brand") or ""

    def cta(self, code):
        return (self.data.get("cta") or {}).get(code, code) if code else ""


def ad_name(ad):
    first = (ad.get("cards") or [{}])[0] if ad.get("cards") else {}
    return ad.get("label") or ad.get("headline") or first.get("headline") or (ad.get("primary_text") or "").split("\n")[0] or ad["id"]


def ad_headline(ad):
    if ad.get("format") == "carousel":
        return ((ad.get("cards") or [{}])[0] or {}).get("headline") or ""
    return ad.get("headline") or ""


def ad_cta(lib, ad):
    if ad.get("format") == "carousel":
        return lib.cta(((ad.get("cards") or [{}])[0] or {}).get("cta") or ad.get("cta"))
    return lib.cta(ad.get("cta"))


def fmt_label(ad):
    f = ad.get("format")
    if f == "carousel":
        return f"Carousel, {len(ad.get('cards') or [])} cards"
    if f == "video":
        return "Video ad (cover frame shown)"
    return "Image ad"


# ------------------------------------------------------------------ mockup images
class Shots:
    """Collects (library, ad, placement) mockups, renders the missing ones once, in parallel."""

    def __init__(self, build_dir, browser=None, dark=False):
        self.dir = build_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.want = {}
        self.browser = browser
        self.dark = dark

    def path(self, lib, ad_id, pl):
        key = hashlib.sha1(f"{lib.viewer}|{lib.stamp}|{ad_id}|{pl}{'|dark' if self.dark else ''}".encode()).hexdigest()[:20]
        p = self.dir / f"{key}.png"
        self.want[p] = (lib, ad_id, pl)
        return p

    def render(self):
        todo = [(p, v) for p, v in self.want.items() if not p.exists()]
        if not todo:
            return
        browser = export_png.find_browser(self.browser)
        tmp = Path(tempfile.mkdtemp(prefix="metaads-deck-"))
        profiles = [tmp / f"p{i}" for i in range(4)]
        print(f"Rendering {len(todo)} mockup image(s) with {Path(browser).name} ...")

        def run(chunk):
            errs = []
            for i, (p, (lib, ad_id, pl)) in chunk:
                place = lib.pl[pl]
                url = (lib.viewer / "index.html").as_uri() + "#export&ad=" + urllib.parse.quote(ad_id) + \
                    f"&pl={pl}&card=0&dark={1 if self.dark else 0}&badges=0&safe=0&trunc=0"
                w = 1280 if place["device"] == "desktop" else 393
                h = 852 if place["template"] in FULLSCREEN else 2600
                try:
                    export_png.shoot(browser, url, str(p), w, h, 2.0, profiles[i % len(profiles)])
                except Exception as e:  # noqa: BLE001
                    errs.append(f"{ad_id} / {pl}: {e}")
            return errs

        jobs = list(enumerate(todo))
        chunks = [[j for j in jobs if j[0] % len(profiles) == k] for k in range(len(profiles))]
        errs = []
        with ThreadPoolExecutor(max_workers=len(profiles)) as ex:
            for r in ex.map(run, chunks):
                errs.extend(r)
        shutil.rmtree(tmp, ignore_errors=True)
        if errs:
            sys.exit("Could not render: " + "; ".join(errs))


def img_size(p):
    from PIL import Image
    with Image.open(p) as im:
        return im.size


# ------------------------------------------------------------------ layout (shared by PDF and PowerPoint)
# The viewer's Save PDF and Save PowerPoint (assets/viewer.html: deckPlan, deckLayout, pptxFiles)
# lay out and write the same deck in JavaScript. Change one, change the other. Deliberate
# differences there: JPEG pictures, exact line spacing (matching the PDF), letter-spaced caps.
def est_h(text, w, size, bold=False, lh=1.25):
    """Rough height of wrapped text (Segoe UI averages ~0.5 em per character, bold ~0.55)."""
    per_line = max(1, int(w / (size * (0.53 if bold else 0.47))))
    lines = sum(max(1, -(-len(par) // per_line)) for par in (text or "").split("\n"))
    return lines * size * lh


def T(x, y, w, h, text, size, color="text", bold=False, align="left", upper=False, lh=1.25):
    return {"k": "text", "x": x, "y": y, "w": w, "h": h, "text": text.upper() if upper else text, "size": size,
            "color": color, "bold": bold, "align": align, "lh": lh, "upper": upper}


def R(x, y, w, h, fill, radius=0, line=None):
    return {"k": "rect", "x": x, "y": y, "w": w, "h": h, "fill": fill, "radius": radius, "line": line}


def I(path, box, valign="top"):
    """Image fitted inside box (x, y, w, h), keeping its shape."""
    x, y, w, h = box
    iw, ih = img_size(path)
    s = min(w / iw, h / ih)
    dw, dh = iw * s, ih * s
    dx = x + (w - dw) / 2
    dy = y + ((h - dh) / 2 if valign == "middle" else 0)
    return {"k": "img", "x": dx, "y": dy, "w": dw, "h": dh, "path": path}


def caption_for(lib, ad_id, pl):
    name = lib.pl[pl]["name"]
    return name + ("  ·  simulated" if lib.status(ad_id, pl) == "simulated" else "")


def footer(deck, n):
    return [T(M, 1016, 1200, 30, clip(deck["title"], 90), 18, "sub"),
            T(W - M - 200, 1016, 200, 30, str(n), 18, "sub", align="right")]


def slide_cover(deck, shots, ctx):
    els = [R(M, 150, 120, 8, "accent"),
           T(M, 186, 1000, 36, "Ad concepts  ·  Facebook & Instagram", 24, "sub", upper=True),
           T(M, 240, 1000, 330, clip(deck["title"], 70), 84, bold=True, lh=1.1)]
    y = 240 + min(330, est_h(clip(deck["title"], 70), 1000, 84, True, 1.1)) + 36
    if deck.get("subtitle"):
        els.append(T(M, y, 960, 160, clip(deck["subtitle"], 150), 34, "sub"))
    els.append(T(M, 900, 1000, 40, ctx["meta"], 24, "sub"))
    # three mockups fanned on the right
    pics = ctx["cover_pics"][:3]
    xs = [1130, 1327, 1524][:len(pics)] if len(pics) == 3 else [1260, 1524][:len(pics)] if len(pics) == 2 else [1524]
    for i, (p, x) in enumerate(zip(pics, xs)):
        top = 150 + (0 if i % 2 == 0 else 70)
        els.append(I(p, (x, top, 300, 780)))
    return els


def slide_concept(deck, shots, s, n):
    lib, ad = s["_lib"], s["_ad"]
    pls = s["_pls"]
    title = clip(s.get("title") or ad_name(ad), 70)
    els = [T(M, 96, 560, 32, clip(lib.brand(ad), 40), 22, "accent", bold=True, upper=True),
           T(M, 136, 560, 200, title, 50, bold=True, lh=1.12)]
    y = 136 + min(200, est_h(title, 560, 50, True, 1.12)) + 64
    hl = clip(ad_headline(ad), 70)
    if hl:
        hh = min(84, est_h(hl, 560, 30, True))
        els += [T(M, y, 560, 26, "Headline", 18, "sub", upper=True), T(M, y + 32, 560, hh + 4, hl, 30, bold=True)]
        y += 32 + hh + 44
    pt = clip(ad.get("primary_text") or "", 260)
    if pt:
        ph = min(330, est_h(pt, 560, 23, lh=1.35))
        els += [T(M, y, 560, 26, "Primary text", 18, "sub", upper=True), T(M, y + 32, 560, ph + 6, pt, 23, lh=1.35)]
        y += 32 + ph + 44
    cta = ad_cta(lib, ad)
    if cta:
        els += [R(M, y, 24 + 13 * len(cta) + 24, 52, "panel", radius=10, line="line"),
                T(M + 24, y + 11, 13 * len(cta) + 20, 32, cta, 22, bold=True)]
        y += 76
    els.append(T(M, min(y, 940), 560, 30, fmt_label(ad), 20, "sub"))
    # mockups
    x0, x1, top, bottom = 720, W - M, 96, 950
    gap = 40
    cw = (x1 - x0 - gap * (len(pls) - 1)) / len(pls)
    for i, pl in enumerate(pls):
        cx = x0 + i * (cw + gap)
        p = shots.path(lib, ad["id"], pl)
        s.setdefault("_imgs", []).append((p, (cx, top, cw, bottom - top - 56), cx, cw, caption_for(lib, ad["id"], pl)))
    return els


def place_images(s):
    """Second pass, after rendering: images need their real sizes for fitting."""
    els = []
    imgs = [(I(p, box), cx, cw, cap) for p, box, cx, cw, cap in s.get("_imgs", [])]
    base = max((im["y"] + im["h"] for im, *_ in imgs), default=0) + 18
    for im, cx, cw, cap in imgs:
        els.append(im)
        els.append(T(cx, base, cw, 30, cap, 19, "sub", align="center"))
    cols = [(I(p, box), cx, cw, lines) for p, box, cx, cw, lines in s.get("_cols", [])]
    base = max((im["y"] + im["h"] for im, *_ in cols), default=0) + 18
    for im, cx, cw, lines in cols:
        els.append(im)
        yy = base
        for txt, size, color, bold in lines:
            els.append(T(cx, yy, cw, size * 1.5, txt, size, color, bold, align="center"))
            yy += size * 1.45
    return els


def slide_lineup(deck, shots, s, n):
    pl = s["placement"]
    items = s["_items"]
    lib0 = items[0][0]
    els = [T(M, 72, 1500, 60, s.get("title") or lib0.pl[pl]["name"], 44, bold=True),
           T(M, 134, 1500, 32, f"{len(items)} ads side by side" if len(items) > 1 else "", 22, "sub")]
    x0, x1, top, bottom = M, W - M, 196, 930
    gap = 48
    cw = (x1 - x0 - gap * (len(items) - 1)) / len(items)
    cw_max = 420
    if cw > cw_max:   # few ads: keep them phone-sized and centred
        x0 += (cw - cw_max) * len(items) / 2
        cw = cw_max
    for i, (lib, ad) in enumerate(items):
        cx = x0 + i * (cw + gap)
        p = shots.path(lib, ad["id"], pl)
        sim = "  ·  simulated" if lib.status(ad["id"], pl) == "simulated" else ""
        s.setdefault("_cols", []).append((p, (cx, top, cw, bottom - top - 80), cx, cw,
                                          [(clip(ad_name(ad), 46), 20, "text", True),
                                           (clip(lib.brand(ad), 40) + sim, 17, "sub", False)]))
    return els


def slide_versus(deck, shots, s, n):
    pl = s["placement"]
    sides = s["_sides"]
    lib0 = sides[0]["items"][0][0]
    els = [T(M, 72, 1600, 60, s.get("title") or f"{sides[0]['label']}  vs  {sides[1]['label']}", 44, bold=True),
           T(M, 134, 1500, 32, lib0.pl[pl]["name"], 22, "sub"),
           R(W / 2 - 1, 200, 2, 760, "line")]
    gap = 32
    half = W / 2 - 48 - M
    cw = min([330] + [(half - gap * (len(sd["items"]) - 1)) / len(sd["items"]) for sd in sides])   # same size both sides
    for k, side in enumerate(sides):
        x0 = M if k == 0 else W / 2 + 48
        x1 = W / 2 - 48 if k == 0 else W - M
        els.append(T(x0, 196, x1 - x0, 40, clip(side["label"], 40), 28, "accent", bold=True, upper=True))
        items = side["items"]
        start = x0 + ((x1 - x0) - (cw * len(items) + gap * (len(items) - 1))) / 2
        for i, (lib, ad) in enumerate(items):
            cx = start + i * (cw + gap)
            p = shots.path(lib, ad["id"], pl)
            pt = ad.get("primary_text") or ""
            info = " · ".join(x for x in (ad_cta(lib, ad), f"text {len(pt)} chars" if pt else "") if x)
            s.setdefault("_cols", []).append((p, (cx, 256, cw, 600), cx, cw,
                                              [(clip(ad_name(ad), 34), 19, "text", True), (info, 16, "sub", False)]))
    return els


def slide_about(deck, n, ctx):
    pts = ["These are mockups drawn to look like the Facebook and Instagram apps. They are close approximations, not Meta’s own rendering.",
           "“Simulated” marks a mockup where the creative was adjusted to fit: cropped, padded or a placeholder.",
           "Video ads are shown as their cover frame.",
           "Not live ads. For internal review only."]
    els = [T(M, 96, 1200, 60, "About these mockups", 44, bold=True)]
    y = 210
    for p in pts:
        h = est_h(p, 1300, 28, lh=1.35)
        els += [R(M, y + 15, 10, 10, "accent", radius=5), T(M + 36, y, 1300, h + 8, p, 28, lh=1.35)]
        y += h + 34
    els.append(T(M, 900, 1500, 36, f"Made {ctx['date']} with the meta-ads mockup tool.", 22, "sub"))
    return els


# ------------------------------------------------------------------ deck assembly
def resolve(deck, deck_dir):
    libs = {}

    def lib_for(ref):
        p = Path(ref)
        if not p.is_absolute():
            p = (deck_dir / p)
        key = str(p.resolve())
        if key not in libs:
            libs[key] = Lib(p)
        return libs[key]

    default = deck.get("library")
    slides = []
    for s in deck["slides"]:
        s = dict(s)
        def ad_of(ref):
            if isinstance(ref, str):
                lib = lib_for(default)
                return lib, lib.ad(ref)
            lib = lib_for(ref.get("library") or default)
            return lib, lib.ad(ref["ad"])
        lay = s["layout"]
        if lay == "concept":
            s["_lib"], s["_ad"] = ad_of(s["ad"])
            want = s.get("placements") or DEFAULT_PL
            pls = [p for p in want if p in s["_lib"].pl and s["_lib"].eligible(s["_ad"]["id"], p)]
            for p in FALLBACK_PL + DEFAULT_PL:
                if len(pls) >= min(3, len(want)):
                    break
                if p not in pls and p in s["_lib"].pl and s["_lib"].eligible(s["_ad"]["id"], p):
                    pls.append(p)
            if not pls:
                print(f"  skipping {s['_ad']['id']}: not eligible in any chosen placement")
                continue
            s["_pls"] = pls[:3]
        elif lay == "lineup":
            items = [ad_of(r) for r in s["ads"]]
            items = [(l, a) for l, a in items if l.eligible(a["id"], s["placement"])]
            if not items:
                continue
            s["_items"] = items[:4]
        elif lay == "versus":
            s["_sides"] = []
            for side in s["sides"]:
                items = [(l, a) for l, a in (ad_of(r) for r in side["ads"]) if l.eligible(a["id"], s["placement"])]
                s["_sides"].append({"label": side.get("label") or (items and items[0][0].brand(items[0][1])) or "", "items": items[:3]})
            if any(not sd["items"] for sd in s["_sides"]):
                continue
        slides.append(s)
    return slides, list(libs.values())


def layout(deck, deck_dir, shots):
    slides, libs = resolve(deck, deck_dir)
    if not slides:
        sys.exit("No slides: none of the chosen ads can run in the chosen placements.")
    d = dt.date.today()
    ads_seen = {}
    for s in slides:
        for lib, ad in ([(s["_lib"], s["_ad"])] if "_ad" in s else s.get("_items", []) +
                        [x for sd in s.get("_sides", []) for x in sd["items"]]):
            ads_seen[(str(lib.viewer), ad["id"])] = (lib, ad)
    brands = sorted({lib.brand(ad) for lib, ad in ads_seen.values() if lib.brand(ad)})
    ctx = {"date": f"{d:%B} {d.day}, {d.year}",
           "meta": f"{len(ads_seen)} ad{'s' if len(ads_seen) != 1 else ''}  ·  " +
                   (", ".join(brands[:3]) + (f" and {len(brands) - 3} more" if len(brands) > 3 else "")) +
                   f"  ·  {d:%B} {d.day}, {d.year}",
           "cover_pics": []}
    pages = []
    for s in slides:
        n = len(pages) + 2
        if s["layout"] == "concept":
            els = slide_concept(deck, shots, s, n)
        elif s["layout"] == "lineup":
            els = slide_lineup(deck, shots, s, n)
        else:
            els = slide_versus(deck, shots, s, n)
        pages.append((s, els))
    # cover pictures: the first full-screen mockup of the first few slides, else their first image
    for s, _ in pages:
        cand = [c[0] for c in s.get("_imgs", [])] + [c[0] for c in s.get("_cols", [])]
        if cand:
            ctx["cover_pics"].append(cand[-1] if s["layout"] == "concept" else cand[0])
        if len(ctx["cover_pics"]) == 3:
            break
    shots.render()
    out = [(None, slide_cover(deck, shots, ctx))]
    for i, (s, els) in enumerate(pages):
        out.append((s, els + place_images(s) + footer(deck, i + 2)))
    out.append((None, slide_about(deck, len(out) + 1, ctx) + footer(deck, len(out) + 1)))
    return out


def notes_for(s):
    if not s:
        return ""
    if "_ad" in s:
        ad = s["_ad"]
        return "\n\n".join(x for x in (ad_name(ad), ad_headline(ad), ad.get("primary_text") or "", s.get("notes") or "") if x)
    items = s.get("_items") or [x for sd in s.get("_sides", []) for x in sd["items"]]
    return "\n\n".join(f"{ad_name(a)}\n{a.get('primary_text') or ''}" for _, a in items) + ("\n\n" + s["notes"] if s.get("notes") else "")


# ------------------------------------------------------------------ PDF (HTML printed by Chrome/Edge)
def color(theme, c):
    return theme.get(c, c)


def write_pdf(pages, theme, build_dir, out_pdf, browser=None):
    css = f"""@page{{size:{W}px {H}px;margin:0}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{background:{theme['bg']};-webkit-print-color-adjust:exact;print-color-adjust:exact}}
body{{font-family:"{theme['font']}","Segoe UI",-apple-system,"Helvetica Neue",Arial,sans-serif;color:{theme['text']}}}
.s{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:{theme['bg']};break-after:page}}
.s:last-child{{break-after:auto}}
.t{{position:absolute;overflow:hidden;white-space:pre-wrap}}
.r{{position:absolute}}
.i{{position:absolute;border-radius:14px;box-shadow:0 10px 32px rgba(20,20,30,.14),0 2px 6px rgba(20,20,30,.08);background:#fff}}"""
    body = []
    for _, els in pages:
        parts = []
        for e in els:
            if e["k"] == "text":
                ls = "letter-spacing:.08em;" if e["upper"] else ""
                parts.append(f'<div class="t" style="left:{e["x"]:.1f}px;top:{e["y"]:.1f}px;width:{e["w"]:.1f}px;height:{e["h"]:.1f}px;'
                             f'font-size:{e["size"]}px;line-height:{e["lh"]};color:{color(theme, e["color"])};font-weight:{700 if e["bold"] else 400};'
                             f'text-align:{e["align"]};{ls}">{html.escape(e["text"])}</div>')
            elif e["k"] == "rect":
                border = f'border:2px solid {color(theme, e["line"])};' if e.get("line") else ""
                parts.append(f'<div class="r" style="left:{e["x"]:.1f}px;top:{e["y"]:.1f}px;width:{e["w"]:.1f}px;height:{e["h"]:.1f}px;'
                             f'background:{color(theme, e["fill"])};border-radius:{e["radius"]}px;{border}"></div>')
            else:
                parts.append(f'<img class="i" src="{Path(e["path"]).as_uri()}" style="left:{e["x"]:.1f}px;top:{e["y"]:.1f}px;width:{e["w"]:.1f}px;height:{e["h"]:.1f}px">')
        body.append('<section class="s">' + "".join(parts) + "</section>")
    page = f'<!doctype html><html><head><meta charset="utf-8"><style>{css}</style></head><body>{"".join(body)}</body></html>'
    src = build_dir / "deck.html"
    src.write_text(page, encoding="utf-8")
    b = export_png.find_browser(browser)
    prof = Path(tempfile.mkdtemp(prefix="metaads-pdf-"))
    out_pdf.unlink(missing_ok=True)
    subprocess.run([b, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
                    "--allow-file-access-from-files", f"--user-data-dir={prof}", "--no-pdf-header-footer",
                    "--virtual-time-budget=5000", f"--print-to-pdf={out_pdf}", src.as_uri()],
                   capture_output=True, text=True, timeout=300)
    shutil.rmtree(prof, ignore_errors=True)
    if not out_pdf.exists():
        sys.exit("The browser didn't write the PDF")
    pages_in_pdf = len(re.findall(rb"/Type\s*/Page[^s]", out_pdf.read_bytes()))
    if pages_in_pdf != len(pages):
        print(f"  note: the PDF has {pages_in_pdf} pages for {len(pages)} slides")


# ------------------------------------------------------------------ PowerPoint
def write_pptx(pages, theme, out_pptx):
    try:
        from pptx import Presentation
        from pptx.dml.color import RGBColor
        from pptx.enum.shapes import MSO_SHAPE
        from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
        from pptx.util import Emu, Pt
    except ImportError:
        print("  PowerPoint skipped: python-pptx isn't installed. See https://python-pptx.readthedocs.io/en/latest/user/install.html")
        return False

    def rgb(c):
        c = color(theme, c).lstrip("#")
        return RGBColor(int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))

    prs = Presentation()
    prs.slide_width, prs.slide_height = Emu(W * EMU), Emu(H * EMU)
    blank = prs.slide_layouts[6]
    for s, els in pages:
        sl = prs.slides.add_slide(blank)
        sl.background.fill.solid()
        sl.background.fill.fore_color.rgb = rgb("bg")
        for e in els:
            x, y, w, h = (Emu(int(v * EMU)) for v in (e["x"], e["y"], e["w"], e["h"]))
            if e["k"] == "rect":
                shp = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE if e["radius"] else MSO_SHAPE.RECTANGLE, x, y, w, h)
                if e["radius"]:
                    shp.adjustments[0] = min(0.5, e["radius"] / max(1, min(e["w"], e["h"])))
                shp.fill.solid()
                shp.fill.fore_color.rgb = rgb(e["fill"])
                if e.get("line"):
                    shp.line.color.rgb = rgb(e["line"])
                    shp.line.width = Emu(2 * EMU)
                else:
                    shp.line.fill.background()
                shp.shadow.inherit = False
            elif e["k"] == "img":
                pad = 2
                fr = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, Emu(int((e["x"] - pad) * EMU)), Emu(int((e["y"] - pad) * EMU)),
                                         Emu(int((e["w"] + 2 * pad) * EMU)), Emu(int((e["h"] + 2 * pad) * EMU)))
                fr.fill.solid()
                fr.fill.fore_color.rgb = rgb("line")
                fr.line.fill.background()
                fr.shadow.inherit = False
                sl.shapes.add_picture(str(e["path"]), x, y, w, h)
            else:
                tb = sl.shapes.add_textbox(x, y, w, h)
                tf = tb.text_frame
                tf.word_wrap = True
                tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
                tf.vertical_anchor = MSO_ANCHOR.TOP
                p = tf.paragraphs[0]
                p.alignment = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}[e["align"]]
                p.line_spacing = e["lh"]
                r = p.add_run()
                r.text = e["text"]
                r.font.size = Pt(e["size"] * 0.5)
                r.font.bold = e["bold"]
                r.font.name = theme["font"]
                r.font.color.rgb = rgb(e["color"])
        notes = notes_for(s)
        if notes:
            sl.notes_slide.notes_text_frame.text = notes
    prs.save(str(out_pptx))
    return True


# ------------------------------------------------------------------ commands
def build(deck, deck_dir, out_base, formats, browser=None):
    theme = {**THEME, **(deck.get("theme") or {})}
    build_dir = out_base.parent / ".build"
    shots = Shots(build_dir, browser, bool(deck.get("dark")))
    pages = layout(deck, deck_dir, shots)
    made = []
    if "pdf" in formats:
        pdf = out_base.with_suffix(".pdf")
        write_pdf(pages, theme, build_dir, pdf, browser)
        made.append(pdf)
    if "pptx" in formats:
        pptx = out_base.with_suffix(".pptx")
        if write_pptx(pages, theme, pptx):
            made.append(pptx)
    print(f"Built {len(pages)} slides:")
    for m in made:
        print(f"  {m}  ({m.stat().st_size / 1e6:.1f} MB)")
    return made


def refresh_index(lib_dir):
    try:
        import library
        root = library.root_of(lib_dir / "ads.json")
        if root:
            library.write_index(root)
    except Exception:  # noqa: BLE001  (the deck is built either way)
        pass


def cmd_quick(a):
    lib = Lib(a.library)
    lib_dir = lib.viewer.parent if lib.viewer.name == "viewer" else lib.viewer
    ids = [x.strip() for x in (a.ads or "").split(",") if x.strip()] or list(lib.ads)
    for x in ids:
        lib.ad(x)
    pls = [p.strip() for p in (a.placements or "").split(",") if p.strip()] or DEFAULT_PL
    bad = [p for p in pls if p not in lib.pl]
    if bad:
        sys.exit(f"unknown placement(s): {', '.join(bad)}")
    ref = str(lib_dir)
    slides = []
    if a.layout == "concept":
        slides = [{"layout": "concept", "ad": x, "placements": pls[:3]} for x in ids]
    elif a.layout == "lineup":
        n = -(-len(ids) // 4)
        per = -(-len(ids) // n)          # spread evenly: 5 ads make 3 + 2, not 4 + 1
        slides = [{"layout": "lineup", "placement": pls[0], "ads": ids[i:i + per]} for i in range(0, len(ids), per)]
    else:
        by = {}
        for x in ids:
            by.setdefault(lib.ads[x].get("brand"), []).append(x)
        if len(by) != 2:
            sys.exit(f"versus needs ads from exactly two brands; these come from {len(by)}")
        (b1, a1), (b2, a2) = list(by.items())
        for i in range(0, max(len(a1), len(a2)), 3):
            s1, s2 = a1[i:i + 3] or a1[-3:], a2[i:i + 3] or a2[-3:]
            slides.append({"layout": "versus", "placement": pls[0],
                           "sides": [{"label": lib.brand(lib.ads[s1[0]]), "ads": s1}, {"label": lib.brand(lib.ads[s2[0]]), "ads": s2}]})
    title = a.title or lib.name
    deck = {"deck_version": 1, "title": title, "subtitle": a.subtitle or "", "library": ref, "slides": slides}
    if a.dark:
        deck["dark"] = True
    exports = lib_dir / "exports"
    exports.mkdir(exist_ok=True)
    base = exports / f"{slug(title)}-{a.layout}-{dt.date.today().isoformat()}"
    deck_file = base.with_suffix(".deck.json")
    deck_file.write_text(json.dumps(deck, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Deck file: {deck_file}")
    build(deck, exports, base, a.format.split(","), a.browser)
    refresh_index(lib_dir)


def cmd_build(a):
    f = Path(a.deck).resolve()
    deck = json.loads(f.read_text(encoding="utf-8-sig"))
    base = f.with_name(f.name[:-len(".deck.json")] if f.name.endswith(".deck.json") else f.stem)
    build(deck, f.parent, base, a.format.split(","), a.browser)
    if f.parent.name == "exports":
        refresh_index(f.parent.parent)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("quick", help="make and build a deck from one library")
    q.add_argument("--library", required=True)
    q.add_argument("--ads", help="comma-separated ad IDs (default: all)")
    q.add_argument("--layout", choices=["concept", "lineup", "versus"], default="concept")
    q.add_argument("--placements", help="comma-separated placement IDs")
    q.add_argument("--title")
    q.add_argument("--subtitle")
    q.add_argument("--dark", action="store_true", help="mockups in the apps' dark mode")
    b = sub.add_parser("build", help="build an existing .deck.json")
    b.add_argument("deck")
    for p in (q, b):
        p.add_argument("--format", default="pdf,pptx", help="pdf, pptx or both (default)")
        p.add_argument("--browser", help="path to Chrome/Edge, if it isn't found automatically")
    a = ap.parse_args()
    (cmd_quick if a.cmd == "quick" else cmd_build)(a)


if __name__ == "__main__":
    main()

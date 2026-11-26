#!/usr/bin/env python3
"""Carousel engine: script + screenshots -> carousel slides (PNGs, PDF, contact sheet).

  engine.py parse script.txt > slides.json   split a "Slide 1 / Slide 2 ..." script into slides
  engine.py info shot1.png shot2.png          print image sizes, for choosing crop boxes
  engine.py render slides.json [--out DIR]    build every slide
"""
import argparse
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEFAULT_BRAND = {
    "size": [1080, 1350],
    "colors": {"bg": "#FFF6EE", "text": "#1A1A1A", "accent": "#FF4FA3"},
    "fonts": {
        "headline": {"family": "Helvetica Neue", "weight": 800},
        "body": {"family": "Helvetica Neue", "weight": 400},
        "aside": {"family": "Georgia, serif", "weight": 400, "style": "italic"},
    },
}
HEADER = re.compile(r"^\s*slide\s*(\d+)\s*(?:[:.\-–—]\s*(.*)|\s*)$", re.I)


def parse_script(text):
    """Split a script into slides. 'Slide N' lines start a slide; else blank lines do."""
    lines = text.splitlines()
    if any(HEADER.match(l) for l in lines):
        chunks = [[]]  # text before the first header becomes its own slide
        for line in lines:
            m = HEADER.match(line)
            if m:
                chunks.append([m.group(2) or ""])
            else:
                chunks[-1].append(line)
    else:
        chunks = [c.splitlines() for c in re.split(r"\n\s*\n", text)]
    slides = []
    for chunk in chunks:
        rows = [r.strip() for r in chunk if r.strip()]
        if not rows:
            continue
        slide = {"layout": "cover" if not slides else "text"}
        if len(rows) > 1 and len(rows[0]) <= 90:
            slide["headline"], slide["body"] = rows[0], "\n".join(rows[1:])
        elif len(rows) == 1 and len(rows[0]) <= 120:
            slide["headline"] = rows[0]
        else:
            slide["body"] = "\n".join(rows)
        slides.append(slide)
    return slides


def markup(text):
    """*word* -> accent underline, _word_ -> aside font. Everything else is escaped."""
    t = html.escape(text)
    t = re.sub(r"\*(.+?)\*", r'<span class="em">\1</span>', t)
    t = re.sub(r"(?<!\w)_(.+?)_(?!\w)", r'<span class="aside f-aside">\1</span>', t)
    return t.replace("\n", "<br>")


def load_brand(path):
    brand = json.loads(json.dumps(DEFAULT_BRAND))
    if path:
        user = json.loads(path.read_text())
        for key, value in user.items():
            if key == "fonts":
                for role, font in value.items():
                    brand["fonts"][role] = {**brand["fonts"].get(role, {"family": "sans-serif"}), **font}
            elif isinstance(value, dict) and key in brand:
                brand[key] = {**brand[key], **value}
            else:
                brand[key] = value
        for font in brand["fonts"].values():
            if font.get("file"):
                font["file"] = (path.parent / font["file"]).resolve().as_uri()
    return brand


def font_css(brand):
    css = []
    for role, f in brand["fonts"].items():
        if f.get("file"):
            css.append(f"@font-face{{font-family:'brand-{role}';src:url('{f['file']}');"
                       f"font-weight:{f.get('weight', 400)};font-style:{f.get('style', 'normal')}}}")
            f["family"] = f"brand-{role}"
        css.append(
            f".f-{role}{{font-family:{f['family']},sans-serif;font-weight:{f.get('weight', 400)};"
            f"font-style:{f.get('style', 'normal')}}}"
        )
    links = "".join(f'<link rel="stylesheet" href="{html.escape(u)}">' for u in brand.get("font_css", []))
    return links, "".join(css)


def cutout_binary():
    binary, source = HERE / ".build" / "cutout", HERE / "cutout.swift"
    if not binary.exists() or binary.stat().st_mtime < source.stat().st_mtime:
        binary.parent.mkdir(exist_ok=True)
        subprocess.run(["swiftc", "-O", str(source), "-o", str(binary)], check=True)
    return binary


def prepare_image(spec, base, work, n):
    """Crop the photo out of a screenshot, then optionally cut the subject out."""
    src = (base / spec["src"]).resolve()
    im = ImageOps.exif_transpose(Image.open(src))
    if spec.get("crop"):
        x, y, w, h = spec["crop"]
        im = im.crop((x, y, x + w, y + h))
    cropped = work / f"img{n}.png"
    im.save(cropped)
    if not spec.get("cutout"):
        return cropped, False
    cut = work / f"img{n}_cut.png"
    try:
        r = subprocess.run([str(cutout_binary()), str(cropped), str(cut)], capture_output=True, text=True)
        error = r.stderr.strip() if r.returncode else None
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        error = f"cutout tool unavailable: {e}"
    if error:
        print(f"slide {n}: cutout failed ({error}), using the cropped photo", file=sys.stderr)
        return cropped, False
    return cut, True


def slide_html(slide, n, total, brand, handle, links, fonts, image):
    W, H = brand["size"]
    c = brand["colors"]
    parts = {
        "h": f'<div class="h f-headline">{markup(slide["headline"])}</div>' if slide.get("headline") else "",
        "b": f'<div class="b f-body">{markup(slide["body"])}</div>' if slide.get("body") else "",
        "p": "",
    }
    if image:
        path, is_cut = image
        parts["p"] = f'<div class="pic {"cut" if is_cut else "photo"}"><img src="{path.as_uri()}"></div>'
    order = "hpb" if slide.get("layout") == "image" else "hbp"
    swipe = "swipe →" if n < total else ""
    return f"""<!doctype html><html><head><meta charset="utf-8">{links}<style>{fonts}
*{{margin:0;box-sizing:border-box}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;background:{c['bg']};color:{c['text']}}}
body{{padding:96px 84px 120px;display:flex;flex-direction:column;gap:44px}}
body.text{{justify-content:safe center}}
.h,.b{{overflow-wrap:anywhere}}
.h{{font-size:92px;line-height:1.04;letter-spacing:-.02em;flex:none}}
body.cover .h{{font-size:132px}}
.b{{font-size:46px;line-height:1.32;flex:none}}
.em{{text-decoration:underline {c['accent']} .14em;text-underline-offset:.1em;text-decoration-skip-ink:none}}
.aside{{color:{c['accent']};font-size:1.3em;line-height:0}}
.pic{{flex:1 1 0;min-height:38%;display:flex;align-items:center;justify-content:center}}
.pic.cut{{align-items:flex-end;margin-bottom:-120px}}
.pic img{{max-width:100%;max-height:100%;object-fit:contain}}
.photo img{{border-radius:28px;box-shadow:0 18px 50px rgba(0,0,0,.18)}}
.foot{{position:absolute;left:84px;right:84px;bottom:44px;display:flex;justify-content:space-between;
  font-size:26px;z-index:2}}
.foot span{{background:{c['bg']};padding:4px 12px;border-radius:99px;opacity:.75}}
.foot span:empty{{visibility:hidden}}
</style></head>
<body class="{slide.get('layout', 'text')}">
{''.join(parts[k] for k in order)}
<div class="foot f-body"><span>{html.escape(handle)}</span><span>{n}/{total}</span><span>{swipe}</span></div>
<script>
document.fonts.ready.then(() => {{
  const text = [...document.querySelectorAll('.h,.b')];
  for (let i = 0; i < 60 && (document.body.scrollHeight > {H} + 1 ||
       Math.max(...text.map(e => e.getBoundingClientRect().bottom)) > {H} - 110); i++)
    for (const el of text) el.style.fontSize = parseFloat(getComputedStyle(el).fontSize) * 0.95 + 'px';
}});
</script></body></html>"""


def screenshot(html_path, png, size, profile):
    W, H = size
    subprocess.run(
        [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
         f"--user-data-dir={profile}", f"--window-size={W},{H}", "--virtual-time-budget=4000",
         f"--screenshot={png}", html_path.as_uri()],
        check=True, capture_output=True, timeout=90,
    )


def render(spec_path, out):
    spec_path, out = spec_path.resolve(), out.resolve()  # Chrome needs absolute file:// URLs
    spec = json.loads(spec_path.read_text())
    base = spec_path.parent
    brand = load_brand((base / spec["brand"]).resolve() if spec.get("brand") else None)
    links, fonts = font_css(brand)
    slides = spec["slides"]
    if not slides:
        sys.exit("slides.json has no slides")
    out.mkdir(parents=True, exist_ok=True)
    work = out / "work"
    work.mkdir(exist_ok=True)
    pngs = []
    with tempfile.TemporaryDirectory() as profile:
        for n, slide in enumerate(slides, 1):
            image = prepare_image(slide["image"], base, work, n) if slide.get("image") else None
            page = work / f"slide{n:02}.html"
            page.write_text(slide_html(slide, n, len(slides), brand, spec.get("handle") or brand.get("handle", ""), links, fonts, image))
            png = out / f"slide{n:02}.png"
            screenshot(page, png, brand["size"], profile)
            pngs.append(png)
            print(f"slide {n}/{len(slides)} -> {png.name}")
    Image.init()  # Pillow's PDF writer needs the JPEG plugin registered first
    frames = [Image.open(p).convert("RGB") for p in pngs]
    frames[0].save(out / "carousel.pdf", save_all=True, append_images=frames[1:])  # LinkedIn takes PDFs
    contact_sheet(frames, out / "contact-sheet.jpg")
    print(f"done: {out}")


def contact_sheet(frames, path, cols=5, thumb=270):
    th = int(thumb * frames[0].height / frames[0].width)
    rows = -(-len(frames) // cols)
    sheet = Image.new("RGB", (cols * (thumb + 12) + 12, rows * (th + 12) + 12), "#222")
    for i, f in enumerate(frames):
        sheet.paste(f.resize((thumb, th)), (12 + (i % cols) * (thumb + 12), 12 + (i // cols) * (th + 12)))
    sheet.save(path, quality=88)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("parse").add_argument("script", type=Path)
    sub.add_parser("info").add_argument("images", type=Path, nargs="+")
    r = sub.add_parser("render")
    r.add_argument("slides", type=Path)
    r.add_argument("--out", type=Path)
    a = ap.parse_args()
    if a.cmd == "parse":
        print(json.dumps({"brand": None, "handle": "", "slides": parse_script(a.script.read_text())}, indent=2))
    elif a.cmd == "info":
        for p in a.images:
            w, h = ImageOps.exif_transpose(Image.open(p)).size
            print(f"{p}\t{w}x{h}")
    else:
        render(a.slides, a.out or a.slides.parent / "out")


if __name__ == "__main__":
    main()

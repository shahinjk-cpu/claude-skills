#!/usr/bin/env python3
"""Extract a dominant palette from game art / frames. Usage: palette.py IMG [IMG...] [--k 8]
Prints colors with share, saturation and lightness so Claude can choose primary/accent/dark."""
import sys, json, colorsys
from PIL import Image

k = 8
paths = [p for p in sys.argv[1:] if not p.startswith("--")]
if "--k" in sys.argv: k = int(sys.argv[sys.argv.index("--k") + 1]); paths = [p for p in paths if p != str(k)]
px = []
for p in paths:
    try:
        im = Image.open(p).convert("RGBA"); im.thumbnail((200, 200))
        b = im.tobytes(); px += [tuple(b[i:i + 3]) for i in range(0, len(b), 4) if b[i + 3] > 128]
    except Exception as e: print(f"skip {p}: {e}", file=sys.stderr)
if not px: sys.exit("no pixels")
img = Image.new("RGB", (len(px), 1)); img.putdata(px)
q = img.quantize(colors=k, method=Image.Quantize.MEDIANCUT)
pal = q.getpalette(); counts = sorted(q.getcolors(), reverse=True); total = sum(c for c, _ in counts)
out = []
for c, i in counts:
    r, g, b = pal[i * 3:i * 3 + 3]; h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
    out.append({"hex": f"#{r:02x}{g:02x}{b:02x}", "share": round(c / total, 3), "sat": round(s, 2), "light": round(l, 2)})
# Vivid pass: the saturated, mid-light colors (characters, logo, FX) that median-cut averages away
viv = [p for p in px if (lambda h, l, s: s > 0.5 and 0.35 < l < 0.75)(*colorsys.rgb_to_hls(p[0] / 255, p[1] / 255, p[2] / 255))]
vivid = []
if viv:
    vi = Image.new("RGB", (len(viv), 1)); vi.putdata(viv)
    vq = vi.quantize(colors=6, method=Image.Quantize.MEDIANCUT); vp = vq.getpalette(); vc = sorted(vq.getcolors(), reverse=True); vt = sum(c for c, _ in vc)
    for c, i in vc:
        r, g, b = vp[i * 3:i * 3 + 3]; vivid.append({"hex": f"#{r:02x}{g:02x}{b:02x}", "share_of_vivid": round(c / vt, 3)})
print(json.dumps({"dominant": out, "vivid": vivid}, indent=2))

#!/usr/bin/env python3
"""Score captured frames, drop duplicates/boring ones, and build a numbered contact sheet
for Claude to look at. Usage: pick.py RAW_DIR [--top 16] [--out DIR]  (default: parent of RAW_DIR)"""
import argparse, json, math, os, glob
from PIL import Image, ImageChops, ImageFilter, ImageStat, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument("raw"); ap.add_argument("--top", type=int, default=16); ap.add_argument("--out", default=None)
a = ap.parse_args()
# default: the work/ folder that holds RAW_DIR (store-assets/work/raw -> store-assets/work)
a.out = a.out or os.path.dirname(os.path.abspath(a.raw))

def dhash(im, n=12):
    g = im.convert("L").resize((n + 1, n))
    p = g.tobytes()
    return [p[r * (n + 1) + c] > p[r * (n + 1) + c + 1] for r in range(n) for c in range(n)]

def colorfulness(im):
    # Hasler & Suesstrunk colorfulness, computed with ImageStat (fast, no per-pixel Python loops)
    r, g, b = [ImageChops.add(x, Image.new("L", x.size), 1, 0) for x in im.convert("RGB").resize((160, 160)).split()]
    rg = ImageChops.subtract(r, g, 2, 128)                        # (r-g)/2 + 128
    yb = ImageChops.subtract(ImageChops.add(r, g, 4, 0), b, 2, 128)  # ((r+g)/2 - b)/2 + 128 approx
    s1, s2 = ImageStat.Stat(rg), ImageStat.Stat(yb)
    sd = math.hypot(s1.stddev[0], s2.stddev[0]) * 2
    mu = math.hypot(s1.mean[0] - 128, s2.mean[0] - 128) * 2
    return sd + 0.3 * mu

frames = []
for f in sorted(glob.glob(os.path.join(a.raw, "*.png"))):
    if f.endswith(".view.png"): continue  # droid.mjs grid previews are not frames
    try: im = Image.open(f); im.draft("RGB", (480, 480)); im.load()
    except Exception: continue
    small = im.convert("RGB").resize((240, int(240 * im.height / im.width)))
    std = sum(ImageStat.Stat(small.convert("L")).stddev)
    edges = ImageStat.Stat(small.convert("L").filter(ImageFilter.FIND_EDGES)).mean[0]
    score = colorfulness(small) * 1.0 + edges * 2.0 + min(std, 70) * 0.6
    if std < 12: score -= 200  # flat/blank/loading frame
    sig = list(small.resize((4, 8)).tobytes())  # coarse color layout = "which scene/level is this"
    frames.append({"file": f, "score": round(score, 1), "hash": dhash(small), "sig": sig, "size": im.size})

# Greedy max-marginal-relevance: high score, but strongly prefer frames that look unlike the ones already picked
# (different era/level/colors), so the set shows variety instead of 10 near-identical moments.
if frames:
    hi = max(f["score"] for f in frames); lo = min(f["score"] for f in frames)
    for f in frames: f["n"] = (f["score"] - lo) / ((hi - lo) or 1)
def sim(x, y):
    d = math.sqrt(sum((p - q) ** 2 for p, q in zip(x["sig"], y["sig"])) / len(x["sig"]))
    return max(0.0, 1 - d / 55)  # 1 = same scene colors, 0 = very different
picked, pool = [], frames[:]
while pool and len(picked) < a.top:
    best = max(pool, key=lambda f: f["n"] - 1.6 * max((sim(f, p) for p in picked), default=0))
    pool.remove(best)
    if all(sum(x != y for x, y in zip(best["hash"], p["hash"])) > 22 for p in picked): picked.append(best)
os.makedirs(a.out, exist_ok=True)
cols = 4; tw = 270; th = int(tw * picked[0]["size"][1] / picked[0]["size"][0]) if picked else 480
rows = math.ceil(len(picked) / cols) or 1
sheet = Image.new("RGB", (cols * (tw + 10) + 10, rows * (th + 40) + 10), (18, 18, 22))
d = ImageDraw.Draw(sheet)
try: font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 22)
except Exception: font = ImageFont.load_default()
for i, fr in enumerate(picked):
    x, y = 10 + (i % cols) * (tw + 10), 10 + (i // cols) * (th + 40)
    sheet.paste(Image.open(fr["file"]).convert("RGB").resize((tw, th)), (x, y + 30))
    d.text((x, y + 2), f"#{i+1}  {os.path.basename(fr['file'])[:22]}", fill=(255, 210, 80), font=font)
sheet_path = os.path.join(a.out, "contact-sheet.png"); sheet.save(sheet_path)
res = [{"n": i + 1, "file": fr["file"], "score": fr["score"]} for i, fr in enumerate(picked)]
json.dump(res, open(os.path.join(a.out, "candidates.json"), "w"), indent=2)
print(json.dumps({"total_frames": len(frames), "contact_sheet": sheet_path, "candidates": res}, indent=2))

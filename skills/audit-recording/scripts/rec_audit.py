#!/usr/bin/env python3
"""rec_audit.py: measure a screen recording for a UI / design / latency audit.

Scripts measure, Claude judges. Everything here is Python 3.8+ standard library plus
ffmpeg/ffprobe. All times come from real frame timestamps (PTS), never frame index / fps,
because screen recordings are variable frame rate.

Subcommands
  analyze VIDEO [--out DIR]          probe, change timeline, bursts, auto-signals, frames, grids
  measure DIR --input T              latency for one interaction (T = input time, seconds)
  strip   DIR --from A --to B        labelled filmstrip of a time window (to mark input, zoom in)
  frames  DIR --at T1,T2,...         full-resolution frames at given times
"""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys

LONG_EDGE = 1568          # Claude downscales images to this long edge; never exceed it
DIFF_LONG = 1600          # long edge used for the change-detection pass (one typed character must register)
PIX_THRESH = 24           # per-pixel luma delta (0-255) that counts as "changed"
CELL_HIT = 6              # cell value (0-255 = share of the cell changed) that marks a cell as changed (~2.4%)
MERGE_GAP = 0.15          # s: active frames closer than this belong to one burst
SETTLE_QUIET = 0.5        # s: quiet this long after a change = visually settled

# ---------------------------------------------------------------- utilities


def die(msg):
    print("error: " + msg, file=sys.stderr)
    sys.exit(1)


def need_tools():
    for t in ("ffmpeg", "ffprobe"):
        if not shutil.which(t):
            die(t + " not found. Install ffmpeg (macOS: brew install ffmpeg) and rerun.")


def run(cmd, stdout=True):
    return subprocess.run(cmd, stdout=subprocess.PIPE if stdout else subprocess.DEVNULL,
                          stderr=subprocess.PIPE)


def ft(t):
    """seconds -> MM:SS.mmm"""
    t = max(0.0, t)
    m = int(t // 60)
    return "%02d:%06.3f" % (m, t - 60 * m)


def ms(t):
    return int(round(t * 1000))


def pct(x):
    return "%.2f%%" % (100.0 * x)


def median(xs):
    s = sorted(xs)
    if not s:
        return 0.0
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def percentile(xs, p):
    s = sorted(xs)
    if not s:
        return 0.0
    k = min(len(s) - 1, max(0, int(round(p / 100.0 * (len(s) - 1)))))
    return s[k]


SHOWINFO_RE = re.compile(r"\bn:\s*(\d+)\b.*?\bpts_time:\s*([-\d.e]+)")

# ---------------------------------------------------------------- bitmap font (no drawtext needed)
# Homebrew ffmpeg often lacks drawtext (no freetype). Labels are drawn as tiny PGM images instead.

_G = {
    '0': '.###. #...# #..## #.#.# ##..# #...# .###.',
    '1': '..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.',
    '2': '.###. #...# ....# ...#. ..#.. .#... #####',
    '3': '##### ...#. ..#.. ...#. ....# #...# .###.',
    '4': '...#. ..##. .#.#. #..#. ##### ...#. ...#.',
    '5': '##### #.... ####. ....# ....# #...# .###.',
    '6': '..##. .#... #.... ####. #...# #...# .###.',
    '7': '##### ....# ...#. ..#.. .#... .#... .#...',
    '8': '.###. #...# #...# .###. #...# #...# .###.',
    '9': '.###. #...# #...# .#### ....# ...#. .##..',
    'A': '.###. #...# #...# ##### #...# #...# #...#',
    'B': '####. #...# #...# ####. #...# #...# ####.',
    'C': '.###. #...# #.... #.... #.... #...# .###.',
    'D': '####. #...# #...# #...# #...# #...# ####.',
    'E': '##### #.... #.... ####. #.... #.... #####',
    'F': '##### #.... #.... ####. #.... #.... #....',
    'G': '.###. #...# #.... #.### #...# #...# .####',
    'H': '#...# #...# #...# ##### #...# #...# #...#',
    'I': '.###. ..#.. ..#.. ..#.. ..#.. ..#.. .###.',
    'J': '..### ...#. ...#. ...#. ...#. #..#. .##..',
    'K': '#...# #..#. #.#.. ##... #.#.. #..#. #...#',
    'L': '#.... #.... #.... #.... #.... #.... #####',
    'M': '#...# ##.## #.#.# #.#.# #...# #...# #...#',
    'N': '#...# #...# ##..# #.#.# #..## #...# #...#',
    'O': '.###. #...# #...# #...# #...# #...# .###.',
    'P': '####. #...# #...# ####. #.... #.... #....',
    'Q': '.###. #...# #...# #...# #.#.# #..#. .##.#',
    'R': '####. #...# #...# ####. #.#.. #..#. #...#',
    'S': '.#### #.... #.... .###. ....# ....# ####.',
    'T': '##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..',
    'U': '#...# #...# #...# #...# #...# #...# .###.',
    'V': '#...# #...# #...# #...# #...# .#.#. ..#..',
    'W': '#...# #...# #...# #.#.# #.#.# #.#.# .#.#.',
    'X': '#...# #...# .#.#. ..#.. .#.#. #...# #...#',
    'Y': '#...# #...# .#.#. ..#.. ..#.. ..#.. ..#..',
    'Z': '##### ....# ...#. ..#.. .#... #.... #####',
    ':': '..... ..#.. ..#.. ..... ..#.. ..#.. .....',
    '.': '..... ..... ..... ..... ..... .##.. .##..',
    '+': '..... ..#.. ..#.. ##### ..#.. ..#.. .....',
    '-': '..... ..... ..... ##### ..... ..... .....',
    '#': '.#.#. .#.#. ##### .#.#. ##### .#.#. .#.#.',
    '/': '....# ...#. ...#. ..#.. .#... .#... #....',
    '(': '...#. ..#.. .#... .#... .#... ..#.. ...#.',
    ')': '.#... ..#.. ...#. ...#. ...#. ..#.. .#...',
    '=': '..... ..... ##### ..... ##### ..... .....',
    '%': '##..# ##.#. ...#. ..#.. .#... .#.## #..##',
    '>': '.#... ..#.. ...#. ....# ...#. ..#.. .#...',
    '~': '..... ..... .#... #.#.# ...#. ..... .....',
    ' ': '..... ..... ..... ..... ..... ..... .....',
}


def _glyph(ch):
    return _G.get(ch.upper(), _G[" "]).replace(" ", "")


def write_label_pgm(text, path):
    """White 5x7 text on black, 1px gaps, 1px border. Returns (w, h)."""
    text = text[:80]
    w = 1 + 6 * len(text)
    h = 9
    rows = []
    for y in range(h):
        row = bytearray(w)
        if 1 <= y <= 7:
            for i, ch in enumerate(text):
                g = _glyph(ch)
                for x in range(5):
                    if g[(y - 1) * 5 + x] == "#":
                        row[1 + 6 * i + x] = 255
        rows.append(bytes(row))
    with open(path, "wb") as f:
        f.write(("P5\n%d %d\n255\n" % (w, h)).encode())
        f.write(b"".join(rows))
    return w, h

# ---------------------------------------------------------------- probing and decoding


def probe(video):
    p = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=codec_name,width,height,r_frame_rate,avg_frame_rate,pix_fmt:format=duration",
             "-of", "json", video])
    try:
        info = json.loads(p.stdout.decode() or "{}")
    except ValueError:
        info = {}
    st = (info.get("streams") or [{}])[0]
    if not st:
        die("no video stream found in " + video)
    # displayed size (after rotation metadata, which ffmpeg applies when decoding)
    p2 = run(["ffmpeg", "-hide_banner", "-i", video, "-frames:v", "1", "-vf", "showinfo",
              "-f", "null", "-"], stdout=False)
    m = re.search(r"\bs:(\d+)x(\d+)", p2.stderr.decode("utf-8", "replace"))
    w, h = (int(m.group(1)), int(m.group(2))) if m else (st.get("width"), st.get("height"))
    return {
        "codec": st.get("codec_name"), "pix_fmt": st.get("pix_fmt"),
        "stored_w": st.get("width"), "stored_h": st.get("height"), "w": w, "h": h,
        "r_frame_rate": st.get("r_frame_rate"), "avg_frame_rate": st.get("avg_frame_rate"),
        "duration": float((info.get("format") or {}).get("duration") or 0),
    }


def grid_dims(w, h):
    return (48, 27) if w >= h else (27, 48)


def decode_passes(video, w, h, cache):
    """Pass A: per-frame changed-pixel fraction on a GWxGH cell grid. Pass B: grey thumbnails."""
    gw, gh = grid_dims(w, h)
    if w >= h:
        dw, dh = DIFF_LONG, -2
        tw, th = 160, 90
    else:
        dw, dh = -2, DIFF_LONG
        tw, th = 90, 160
    vf_a = ("scale=%d:%d,format=gray,tblend=all_mode=difference,"
            "lut=y='if(gt(val,%d),255,0)',scale=%d:%d:flags=area,showinfo" % (dw, dh, PIX_THRESH, gw, gh))
    pa = run(["ffmpeg", "-hide_banner", "-nostats", "-i", video, "-an", "-fps_mode", "passthrough",
              "-vf", vf_a, "-f", "rawvideo", "-pix_fmt", "gray", "-"])
    vf_b = "scale=%d:%d:flags=area,format=gray,showinfo" % (tw, th)
    pb = run(["ffmpeg", "-hide_banner", "-nostats", "-i", video, "-an", "-fps_mode", "passthrough",
              "-vf", vf_b, "-f", "rawvideo", "-pix_fmt", "gray", "-"])
    if pb.returncode != 0 or not pb.stdout:
        die("ffmpeg could not decode the video:\n" + pb.stderr.decode("utf-8", "replace")[-1500:])
    pts = [float(t) for _, t in SHOWINFO_RE.findall(pb.stderr.decode("utf-8", "replace"))]
    n = len(pb.stdout) // (tw * th)
    pts = pts[:n]
    if len(pts) < n:
        die("could not read frame timestamps (got %d of %d)" % (len(pts), n))
    pts_a = [float(t) for _, t in SHOWINFO_RE.findall(pa.stderr.decode("utf-8", "replace"))]
    na = len(pa.stdout) // (gw * gh)
    pts_a = pts_a[:na]
    # tblend emits one frame per consecutive pair; align each diff to the frame it ends on
    cells = gw * gh
    diffs = [None] * n
    index_by_pts = {round(t, 4): i for i, t in enumerate(pts)}
    aligned = 0
    for k in range(na):
        i = index_by_pts.get(round(pts_a[k], 4)) if k < len(pts_a) else None
        if i is None:
            i = k + 1
        else:
            aligned += 1
        if 0 < i < n:
            diffs[i] = pa.stdout[k * cells:(k + 1) * cells]
    # Some ffmpeg builds (seen on Ubuntu's 8.0) range-convert after the lut, so an unchanged cell
    # comes out as ~2 instead of 0. Take the lowest value in the whole diff stream as "no change".
    present = [d for d in diffs if d]
    floor = min(min(d) for d in present) if present else 0
    if floor:
        table = bytes(max(0, v - floor) for v in range(256))
        diffs = [d.translate(table) if d else d for d in diffs]
    os.makedirs(cache, exist_ok=True)
    with open(os.path.join(cache, "thumbs.bin"), "wb") as f:
        f.write(pb.stdout[:n * tw * th])
    with open(os.path.join(cache, "diffs.bin"), "wb") as f:
        for d in diffs:
            f.write(d if d is not None else bytes(cells))
    meta = {"pts": pts, "gw": gw, "gh": gh, "tw": tw, "th": th, "n": n,
            "diff_alignment": "pts" if aligned >= na * 0.9 else "offset+1"}
    with open(os.path.join(cache, "frames.json"), "w") as f:
        json.dump(meta, f)
    return meta


def load_cache(d):
    cache = os.path.join(d, "cache")
    try:
        with open(os.path.join(cache, "frames.json")) as f:
            meta = json.load(f)
        with open(os.path.join(d, "analysis.json")) as f:
            an = json.load(f)
    except (OSError, ValueError):
        die("no analysis found in %s. Run: rec_audit.py analyze VIDEO --out %s" % (d, d))
    cells = meta["gw"] * meta["gh"]
    with open(os.path.join(cache, "diffs.bin"), "rb") as f:
        raw = f.read()
    meta["diffs"] = [raw[i * cells:(i + 1) * cells] for i in range(meta["n"])]
    with open(os.path.join(cache, "thumbs.bin"), "rb") as f:
        raw = f.read()
    ts = meta["tw"] * meta["th"]
    meta["thumbs"] = [raw[i * ts:(i + 1) * ts] for i in range(meta["n"])]
    return meta, an

# ---------------------------------------------------------------- masks and per-frame signals


def rect_to_cells(rect, w, h, gw, gh):
    """rect = (x, y, w, h) in displayed pixels -> set of cell indexes it touches."""
    x, y, rw, rh = rect
    c0 = max(0, int(x / w * gw))
    c1 = min(gw - 1, int(math.ceil((x + rw) / w * gw)) - 1)
    r0 = max(0, int(y / h * gh))
    r1 = min(gh - 1, int(math.ceil((y + rh) / h * gh)) - 1)
    return {r * gw + c for r in range(r0, r1 + 1) for c in range(c0, c1 + 1)}


def parse_rect(s):
    try:
        parts = [float(v) for v in s.split(",")]
        assert len(parts) == 4
        return tuple(parts)
    except (ValueError, AssertionError):
        die("bad rect %r, expected x,y,w,h in pixels of the displayed frame" % s)


def frame_signals(meta, masked):
    gw, gh = meta["gw"], meta["gh"]
    live = [c for c in range(gw * gh) if c not in masked]
    denom = 255.0 * max(1, len(live))
    frac, hits = [], []
    for d in meta["diffs"]:
        s = 0
        hc = []
        for c in live:
            v = d[c]
            if v:
                s += v
                if v >= CELL_HIT:
                    hc.append(c)
        frac.append(s / denom)
        hits.append(hc)
    return frac, hits


def bbox_of(cells, gw, gh):
    if not cells:
        return None
    xs = [c % gw for c in cells]
    ys = [c // gw for c in cells]
    return (min(xs), min(ys), max(xs), max(ys))


def bbox_area(bb, gw, gh):
    if not bb:
        return 0.0
    return (bb[2] - bb[0] + 1) * (bb[3] - bb[1] + 1) / float(gw * gh)


def bbox_px(bb, w, h, gw, gh):
    x0, y0, x1, y1 = bb
    return (int(x0 * w / gw), int(y0 * h / gh), int((x1 + 1 - x0) * w / gw), int((y1 + 1 - y0) * h / gh))


def where(bb, gw, gh):
    if not bb:
        return "-"
    cx = (bb[0] + bb[2] + 1) / 2.0 / gw
    cy = (bb[1] + bb[3] + 1) / 2.0 / gh
    if bbox_area(bb, gw, gh) > 0.5:
        return "most of screen"
    v = "top" if cy < 0.34 else ("bottom" if cy > 0.66 else "middle")
    hz = "left" if cx < 0.34 else ("right" if cx > 0.66 else "center")
    return v + "-" + hz

# ---------------------------------------------------------------- bursts and signals


def find_bursts(pts, frac, hits, floor, gw, gh):
    active = [i for i in range(1, len(pts)) if frac[i] > floor or len(hits[i]) > 0]
    groups = []
    for i in active:
        if groups and pts[i] - pts[groups[-1][-1]] <= MERGE_GAP:
            groups[-1].append(i)
        else:
            groups.append([i])
    bursts = []
    for g in groups:
        i0, i1 = g[0], g[-1]
        union = set()
        for i in g:
            union.update(hits[i])
        bb = bbox_of(union, gw, gh)
        area = bbox_area(bb, gw, gh)
        cover = len(union) / float(gw * gh)
        cl = clusters(union, gw, gh)
        # size of what changes at once (a moving cursor leaves a trail; the trail is not a region)
        big = 0.0
        for i in g:
            if len(hits[i]) * 1.0 / (gw * gh) >= 0.002:
                big = max(big, max(bbox_area(c, gw, gh) for c in clusters(hits[i], gw, gh)))
        frame_cover = max(len(hits[i]) for i in g) / float(gw * gh)
        peak = max(frac[i] for i in g)
        gaps = [pts[i + 1] - pts[i] for i in range(i0, i1)] if i1 > i0 else []
        if peak >= 0.25 or frame_cover >= 0.35:
            kind = "screen"
        elif peak >= 0.03 or big >= 0.06:
            kind = "region"
        elif big <= 0.012 and peak < 0.002:
            kind = "tiny"
        else:
            kind = "local"
        bursts.append({
            "i0": i0, "i1": i1, "t0": pts[i0], "t1": pts[i1], "dur": pts[i1] - pts[i0],
            "frames": len(g), "peak": peak, "bbox": bb, "area": area, "kind": kind,
            "clusters": cl[:4], "cover": cover,
            "max_gap": max(gaps) if gaps else 0.0,
        })
    for k, b in enumerate(bursts):
        b["id"] = "E%02d" % (k + 1)
    return bursts


def luma_stats(thumb):
    n = len(thumb)
    mean = sum(thumb) / float(n)
    var = sum((v - mean) ** 2 for v in thumb[::3]) / float(len(thumb[::3]))
    return mean, math.sqrt(var)


def thumb_diff(a, b):
    return sum(abs(x - y) for x, y in zip(a, b)) / float(len(a))


def state_diff(a, b, tw, th, block=4):
    """Largest mean abs luma difference over block x block tiles: sensitive to a changed word."""
    best = 0.0
    for by in range(0, th, block):
        for bx in range(0, tw, block):
            s = 0
            cnt = 0
            for y in range(by, min(th, by + block)):
                row = y * tw
                for x in range(bx, min(tw, bx + block)):
                    s += abs(a[row + x] - b[row + x])
                    cnt += 1
            v = s / float(cnt)
            if v > best:
                best = v
    return best


def clusters(cells, gw, gh):
    """8-connected groups of changed cells -> list of bboxes, largest first."""
    left = set(cells)
    out = []
    while left:
        c = left.pop()
        stack = [c]
        comp = [c]
        while stack:
            k = stack.pop()
            x, y = k % gw, k // gw
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < gw and 0 <= ny < gh:
                        nk = ny * gw + nx
                        if nk in left:
                            left.discard(nk)
                            stack.append(nk)
                            comp.append(nk)
        out.append((len(comp), bbox_of(comp, gw, gh)))
    out.sort(key=lambda t: -t[0])
    return [bb for _, bb in out]

# ---------------------------------------------------------------- frame extraction, labels, grids


def extract_frames(video, indexes, outdir):
    """Full-resolution frames for decoded-frame indexes (cache; scale down when presenting)."""
    os.makedirs(outdir, exist_ok=True)
    want = sorted(set(i for i in indexes if not os.path.exists(os.path.join(outdir, "f_%06d.jpg" % i))))
    if not want:
        return
    tmp = os.path.join(outdir, "_tmp")
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for start in range(0, len(want), 150):
        chunk = want[start:start + 150]
        sel = "+".join("eq(n,%d)" % i for i in chunk)
        p = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", video, "-an",
                 "-vf", "select='%s',format=yuvj420p" % sel, "-fps_mode", "passthrough",
                 "-q:v", "2", os.path.join(tmp, "x_%05d.jpg")], stdout=False)
        got = sorted(os.listdir(tmp))
        if len(got) != len(chunk):
            die("frame extraction returned %d of %d frames: %s" % (len(got), len(chunk), p.stderr.decode()[-800:]))
        for name, i in zip(got, chunk):
            os.replace(os.path.join(tmp, name), os.path.join(outdir, "f_%06d.jpg" % i))
    shutil.rmtree(tmp, ignore_errors=True)


def save_capped(src, dst):
    """Copy a frame with its long edge capped at LONG_EDGE (what Claude can actually see)."""
    scale = "scale='if(gte(iw,ih),min(%d,iw),-2)':'if(gte(iw,ih),-2,min(%d,ih))'" % (LONG_EDGE, LONG_EDGE)
    p = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-vf", scale,
             "-q:v", "2", dst], stdout=False)
    if p.returncode != 0:
        die("could not write " + dst)


def grid_layout(n, aspect, lh, margin=8):
    """Pick cols/rows that give the biggest cells while the grid long edge stays <= LONG_EDGE."""
    best = None
    for cols in range(1, n + 1):
        rows = int(math.ceil(n / float(cols)))
        cw_w = (LONG_EDGE - margin * (cols + 1)) / float(cols)
        ch_h = (LONG_EDGE - margin * (rows + 1)) / float(rows) - lh
        cw = min(cw_w, ch_h * aspect)
        if cw <= 0:
            continue
        key = (cw, -abs(cols - rows))
        if best is None or key > best[0]:
            best = (key, cols, rows, cw)
    _, cols, rows, cw = best
    return cols, rows, int(cw) // 2 * 2, int(cw / aspect) // 2 * 2


def build_grid(frame_files, labels, out_path, w, h, crop=None):
    """Tile labelled frames into one image whose long edge is about LONG_EDGE.
    crop = (x, y, w, h) in displayed-frame pixels: zoom every cell into that region."""
    n = len(frame_files)
    if n == 0:
        return None
    margin = 8
    pre = ""
    if crop:
        cx, cy, cw0, ch0 = [int(v) for v in crop]
        pre = "crop=%d:%d:%d:%d," % (cw0, ch0, cx, cy)
        w, h = cw0, ch0
    aspect = w / float(h)
    lh = 9 * 3 + 8
    cols, rows, cw, ch = grid_layout(n, aspect, lh, margin)
    # never upscale a crop more than 2x
    if crop and cw > 2 * w:
        cw, ch = int(2 * w) // 2 * 2, int(2 * h) // 2 * 2
    k = max(2, min(4, int(round(cw / 220.0))))
    lh = 9 * k + 8
    tmp = out_path + "_cells"
    shutil.rmtree(tmp, ignore_errors=True)
    os.makedirs(tmp)
    for j, (src, lab) in enumerate(zip(frame_files, labels)):
        lp = os.path.join(tmp, "l_%03d.pgm" % j)
        write_label_pgm(lab, lp)
        fc = ("[0:v]%sscale=%d:%d,setsar=1,pad=%d:%d:0:%d:color=black[c];"
              "[1:v]scale=iw*%d:ih*%d:flags=neighbor[l];[c][l]overlay=6:%d,format=yuvj420p"
              % (pre, cw, ch, cw, ch + lh, lh, k, k, 4))
        p = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src, "-i", lp,
                 "-filter_complex", fc, "-frames:v", "1", "-q:v", "3",
                 os.path.join(tmp, "c_%03d.jpg" % j)], stdout=False)
        if p.returncode != 0:
            die("labelling failed: " + p.stderr.decode()[-600:])
    p = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", os.path.join(tmp, "c_%03d.jpg"),
             "-vf", "tile=%dx%d:margin=%d:padding=%d:color=white" % (cols, rows, margin, margin),
             "-frames:v", "1", "-q:v", "3", out_path], stdout=False)
    if p.returncode != 0:
        die("tiling failed: " + p.stderr.decode()[-600:])
    shutil.rmtree(tmp, ignore_errors=True)
    return {"cols": cols, "rows": rows, "cell_px": [cw, ch]}


def zoom_rect(bbs, w, h, gw, gh, min_frac=0.3):
    """Padded crop around changed areas, or None when the change already covers most of the frame."""
    bbs = [b for b in bbs if b]
    if not bbs:
        return None
    x0 = min(b[0] for b in bbs); y0 = min(b[1] for b in bbs)
    x1 = max(b[2] for b in bbs) + 1; y1 = max(b[3] for b in bbs) + 1
    px0, py0, px1, py1 = x0 * w / float(gw), y0 * h / float(gh), x1 * w / float(gw), y1 * h / float(gh)
    bw, bh = px1 - px0, py1 - py0
    aspect = w / float(h)
    cw = max(bw * 1.6, w * min_frac)
    ch = max(bh * 1.6, cw / aspect)
    cw = max(cw, ch * aspect)
    if cw >= w * 0.85 or ch >= h * 0.85:
        return None
    cx, cy = (px0 + px1) / 2.0, (py0 + py1) / 2.0
    x = min(max(0, cx - cw / 2), w - cw)
    y = min(max(0, cy - ch / 2), h - ch)
    return (int(x) // 2 * 2, int(y) // 2 * 2, int(cw) // 2 * 2, int(ch) // 2 * 2)


def nearest_frame(pts, t):
    """index of the frame on screen at time t (last frame with pts <= t)."""
    lo, hi = 0, len(pts) - 1
    if t <= pts[0]:
        return 0
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if pts[mid] <= t + 1e-6:
            lo = mid
        else:
            hi = mid - 1
    return lo


def even_thin(items, cap):
    if len(items) <= cap:
        return items, False
    if cap <= 1:
        return items[:1], True
    step = (len(items) - 1) / float(cap - 1)
    return [items[int(round(k * step))] for k in range(cap)], True

# ---------------------------------------------------------------- analyze


def classify_platform(w, h, given):
    if given and given != "auto":
        return given
    a = w / float(h)
    if a < 0.7:
        return "phone"
    if a < 1.0:
        return "tablet-portrait"
    return "desktop-or-web"


def cmd_analyze(a):
    need_tools()
    video = os.path.abspath(a.video)
    if not os.path.exists(video):
        die("video not found: " + video)
    base = os.path.splitext(os.path.basename(video))[0]
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-")[:60] or "recording"
    out = os.path.abspath(a.out or os.path.join(os.getcwd(), "recording-audits", safe))
    os.makedirs(out, exist_ok=True)
    cache = os.path.join(out, "cache")

    pr = probe(video)
    w, h = pr["w"], pr["h"]
    print("probing done: %dx%d, %.2fs; decoding..." % (w, h, pr["duration"]), file=sys.stderr)
    meta = decode_passes(video, w, h, cache)
    pts = meta["pts"]
    n = meta["n"]
    gw, gh = meta["gw"], meta["gh"]
    with open(os.path.join(cache, "diffs.bin"), "rb") as f:
        raw = f.read()
    cells = gw * gh
    meta["diffs"] = [raw[i * cells:(i + 1) * cells] for i in range(n)]
    with open(os.path.join(cache, "thumbs.bin"), "rb") as f:
        raw = f.read()
    tw, th = meta["tw"], meta["th"]
    ts = tw * th
    thumbs = [raw[i * ts:(i + 1) * ts] for i in range(n)]

    platform = classify_platform(w, h, a.platform)
    # masks: user rects, phone status bar / home indicator, and always-changing cells
    masked = set()
    mask_notes = []
    for r in a.mask or []:
        rect = parse_rect(r)
        masked |= rect_to_cells(rect, w, h, gw, gh)
        mask_notes.append("user mask %s" % (r,))
    if platform == "phone" and not a.no_default_mask:
        masked |= rect_to_cells((0, 0, w, h * 0.055), w, h, gw, gh)
        masked |= rect_to_cells((0, h * 0.97, w, h * 0.03), w, h, gw, gh)
        mask_notes.append("phone status bar (top 5.5%) and home indicator (bottom 3%)")
    if n > 40:
        counts = [0] * cells
        for d in meta["diffs"][1:]:
            for c in range(cells):
                if d[c] >= CELL_HIT:
                    counts[c] += 1
        always = {c for c in range(cells) if counts[c] > 0.5 * (n - 1)}
        if always:
            bb = bbox_of(always, gw, gh)
            masked |= always
            mask_notes.append("always-changing region (changes in >50%% of frames: clock, video, "
                              "animation) at %s px %s, %d cells" % (where(bb, gw, gh), bbox_px(bb, w, h, gw, gh), len(always)))

    frac, hits = frame_signals(meta, masked)
    nonzero = [f for f in frac[1:] if f > 0]
    # noise floor from the quiet majority of frames (compression shimmer), not from real changes
    floor = min(0.002, max(0.0002, median(frac[1:]) * 3)) if n > 2 else 0.0004
    bursts = find_bursts(pts, frac, hits, floor, gw, gh)

    # pacing
    deltas = [pts[i + 1] - pts[i] for i in range(n - 1)]
    med = median(deltas) if deltas else 0
    p95 = percentile(deltas, 95) if deltas else 0
    mx = max(deltas) if deltas else 0
    vfr = bool(deltas) and (p95 > med * 1.5 or mx > med * 3)
    active_deltas = [pts[b["i0"] + k + 1] - pts[b["i0"] + k] for b in bursts for k in range(b["i1"] - b["i0"])]
    motion_med = median(active_deltas) if active_deltas else med
    fps_motion = (1.0 / motion_med) if motion_med > 0 else 0

    # signals
    signals = []
    hitch_thr = max(3 * motion_med, 0.05)
    for b in bursts:
        if b["kind"] in ("region", "screen") and b["dur"] >= 0.2:
            gaps = [(pts[i + 1] - pts[i], i) for i in range(b["i0"], b["i1"])]
            bad = [(g, i) for g, i in gaps if g > hitch_thr]
            if bad:
                g, i = max(bad)
                signals.append({"type": "hitch", "t": pts[i], "burst": b["id"],
                                "text": "%s: %d frame gap(s) longer than %d ms during motion, longest %d ms at %s "
                                        "(no new frame while the screen was changing: app jank or recorder drop)"
                                        % (b["id"], len(bad), ms(hitch_thr), ms(g), ft(pts[i]))})
        if b["kind"] in ("tiny", "local") and b["dur"] >= 0.6:
            spread = b["area"] > 0.1
            signals.append({"type": "continuous-local", "t": b["t0"], "burst": b["id"],
                            "text": "%s: %s %s keeps changing for %d ms (%s: check frames)"
                                    % (b["id"], "small changes moving across a wide area" if spread else
                                       "small area at " + where(b["bbox"], gw, gh), bbox_px(b["bbox"], w, h, gw, gh),
                                       ms(b["dur"]), "most likely the cursor, typing or small text updates" if spread
                                       else "spinner, progress, animation, typing or cursor")})
        if b["kind"] in ("region", "screen") and b["dur"] >= 1.0 and b["peak"] >= 0.005:
            signals.append({"type": "long-change", "t": b["t0"], "burst": b["id"],
                            "text": "%s: screen keeps changing for %d ms (slow load, progressive render, long "
                                    "animation or scrolling: check frames)" % (b["id"], ms(b["dur"]))})
    lum = [luma_stats(t) for t in thumbs]
    med_l = median([m for m, _ in lum])
    for i in range(1, n):
        mean, sd = lum[i]
        if sd < 2.5 and (mean < 12 or mean > 243) and not (lum[0][1] < 2.5):
            signals.append({"type": "blank", "t": pts[i],
                            "text": "blank %s frame at %s (whole frame one colour)" % ("black" if mean < 128 else "white", ft(pts[i]))})
    # flash: luma jumps far from both neighbours' baseline and comes back within 0.5 s
    for i in range(1, n - 1):
        mean = lum[i][0]
        j = i
        while j + 1 < n and pts[j + 1] - pts[i] < 0.5 and abs(lum[j + 1][0] - lum[i - 1][0]) > 40:
            j += 1
        if abs(mean - lum[i - 1][0]) > 40 and j + 1 < n and abs(lum[j + 1][0] - lum[i - 1][0]) < 15 \
                and pts[j + 1] - pts[i] < 0.5:
            signals.append({"type": "flash", "t": pts[i],
                            "text": "brightness flash at %s for ~%d ms (luma %d -> %d -> %d)"
                                    % (ft(pts[i]), ms(pts[j + 1] - pts[i]), lum[i - 1][0], mean, lum[j + 1][0])})
    # A->B->A revert: a state that comes back within 1.5 s after a big change (flicker / stale content)
    for k in range(len(bursts) - 1):
        b, c = bursts[k], bursts[k + 1]
        if b["kind"] != "tiny" and c["t0"] - b["t1"] < 1.5:
            before = thumbs[b["i0"] - 1]
            after = thumbs[c["i1"]]
            mid = thumbs[b["i1"]]
            if state_diff(before, after, tw, th) < 1.0 and state_diff(before, mid, tw, th) > 3.0:
                signals.append({"type": "revert", "t": b["t0"], "burst": b["id"],
                                "text": "%s/%s: screen changed and came back to the earlier state within %d ms "
                                        "(flicker, stale content, failed action or undo: check frames)"
                                        % (b["id"], c["id"], ms(c["t1"] - b["t0"]))})
    # repeating pattern: 3+ bursts touching the same areas at a steady interval (loops, flicker, polling redraws)
    def same_place(x, y):
        for c1 in x.get("clusters") or []:
            for c2 in y.get("clusters") or []:
                if not (c1[2] < c2[0] or c2[2] < c1[0] or c1[3] < c2[1] or c2[3] < c1[1]):
                    return True
        return False
    used = set()
    for k in range(len(bursts)):
        if k in used:
            continue
        chain = [k]
        for j in range(k + 1, len(bursts)):
            if same_place(bursts[k], bursts[j]) and abs(bursts[j]["dur"] - bursts[k]["dur"]) <= max(0.15, 0.5 * bursts[k]["dur"]):
                chain.append(j)
        if len(chain) >= 3:
            starts = [bursts[j]["t0"] for j in chain]
            gaps = [starts[q + 1] - starts[q] for q in range(len(starts) - 1)]
            mg = median(gaps)
            regular = [g for g in gaps if abs(g - mg) <= max(0.06, 0.2 * mg)]
            if 0 < mg <= 2.5 and len(regular) >= 2 and len(regular) >= 0.6 * len(gaps):
                used.update(chain)
                b0 = bursts[chain[0]]
                signals.append({"type": "repeating", "t": b0["t0"], "burst": b0["id"],
                                "text": "%s: the same area changes again every ~%d ms (%d times, %s to %s) with no new "
                                        "input expected: loop, flicker, state reset, polling redraw, or a blinking caret / "
                                        "animation (check strips)" % (", ".join(bursts[j]["id"] for j in chain), ms(mg),
                                                                      len(chain), ft(starts[0]), ft(bursts[chain[-1]]["t1"]))})
    # dedupe flash/blank spam
    seen = set()
    sig2 = []
    for s in sorted(signals, key=lambda s: s["t"]):
        key = (s["type"], round(s["t"], 1))
        if key not in seen:
            seen.add(key)
            sig2.append(s)
    signals = sig2

    # candidate inputs: small change shortly before a bigger change
    cand_inputs = []
    for k, b in enumerate(bursts):
        if b["kind"] not in ("region", "screen", "local"):
            continue
        pre = [p for p in bursts[:k] if p["kind"] in ("tiny", "local") and p["cover"] < b["cover"]
               and 0 < b["t0"] - p["t1"] <= 1.5]
        if pre:
            p = pre[-1]
            cand_inputs.append({"t": p["t0"], "response": b["id"],
                                "text": "small change at %s (%s) %d ms before %s: possible press / hover / cursor feedback"
                                        % (ft(p["t0"]), where(p["bbox"], gw, gh), ms(b["t0"] - p["t0"]), b["id"])})

    # ---- frames to extract
    fdir = os.path.join(out, "cache", "frames")
    states = [{"i": 0, "why": "start"}]
    for b in bursts:
        states.append({"i": b["i1"], "why": "after " + b["id"], "burst": b["id"]})
    # dedupe near-identical states
    kept = []
    for s in states:
        if kept and state_diff(thumbs[kept[-1]["i"]], thumbs[s["i"]], tw, th) < 2.0:
            kept[-1]["why"] += ", " + s["why"]
            continue
        kept.append(s)
    state_bursts = set()
    for s in kept:
        if s.get("burst"):
            state_bursts.add(s["burst"])
    states, thinned = even_thin(kept, a.max_states)
    for k, s in enumerate(states):
        s["id"] = "S%02d" % (k + 1)

    strip_bursts = [b for b in bursts if b["kind"] in ("region", "screen") or b["dur"] >= 0.3 or
                    b["id"] in state_bursts]
    strip_bursts, strips_thinned = even_thin(strip_bursts, a.max_strips)
    strip_frames = {}
    for b in strip_bursts:
        idx = [max(0, b["i0"] - 1), b["i0"]]
        inner = list(range(b["i0"] + 1, b["i1"]))
        idx += even_thin(inner, 3)[0]
        idx.append(b["i1"])
        after = nearest_frame(pts, b["t1"] + SETTLE_QUIET)
        if after > b["i1"]:
            idx.append(after)
        seen_i = []
        for i in idx:
            if i not in seen_i:
                seen_i.append(i)
        strip_frames[b["id"]] = seen_i
    allidx = [s["i"] for s in states] + [i for v in strip_frames.values() for i in v]
    print("extracting %d frames..." % len(set(allidx)), file=sys.stderr)
    extract_frames(video, allidx, fdir)

    # states as individual full-res files
    sdir = os.path.join(out, "states")
    shutil.rmtree(sdir, ignore_errors=True)
    os.makedirs(sdir)
    for s in states:
        name = "%s_%s.jpg" % (s["id"], ft(pts[s["i"]]).replace(":", "-"))
        save_capped(os.path.join(fdir, "f_%06d.jpg" % s["i"]), os.path.join(sdir, name))
        s["file"] = os.path.join("states", name)
        s["t"] = pts[s["i"]]

    # overview grids
    gdir = os.path.join(out, "grids")
    shutil.rmtree(gdir, ignore_errors=True)
    os.makedirs(gdir)
    per = a.cells or (8 if platform == "phone" else (6 if platform.startswith("tablet") else 4))
    grids = []
    for g in range(0, len(states), per):
        chunk = states[g:g + per]
        path = os.path.join(gdir, "overview_%02d.jpg" % (g // per + 1))
        info = build_grid([os.path.join(fdir, "f_%06d.jpg" % s["i"]) for s in chunk],
                          ["%s %s" % (s["id"], ft(s["t"])) for s in chunk], path, w, h)
        grids.append({"file": os.path.relpath(path, out), "states": [s["id"] for s in chunk], "layout": info})

    # event filmstrips
    edir = os.path.join(out, "events")
    shutil.rmtree(edir, ignore_errors=True)
    os.makedirs(edir)
    strips = []
    for b in strip_bursts:
        idx = strip_frames[b["id"]]
        labels = []
        for i in idx:
            rel = ms(pts[i] - b["t0"])
            labels.append("%s %s %s%dMS" % (b["id"], ft(pts[i]), "+" if rel >= 0 else "", rel))
        path = os.path.join(edir, "%s_%s.jpg" % (b["id"], ft(b["t0"]).replace(":", "-")))
        zr = zoom_rect(b.get("clusters") or [], w, h, gw, gh)
        build_grid([os.path.join(fdir, "f_%06d.jpg" % i) for i in idx], labels, path, w, h, crop=zr)
        strips.append({"burst": b["id"], "file": os.path.relpath(path, out), "zoom": zr,
                       "frames": [{"t": pts[i], "rel_ms": ms(pts[i] - b["t0"])} for i in idx]})

    analysis = {
        "video": video, "out": out, "probe": pr, "platform_guess": platform,
        "frames": n, "interval_ms": {"median": med * 1000, "p95": p95 * 1000, "max": mx * 1000,
                                       "median_during_motion": motion_med * 1000},
        "vfr": vfr, "fps_during_motion": fps_motion, "noise_floor": floor,
        "masks": mask_notes, "masked_cells": sorted(masked), "bursts": bursts, "signals": signals,
        "candidate_inputs": cand_inputs, "states": states, "states_thinned": thinned,
        "grids": grids, "strips": strips, "strips_thinned": strips_thinned,
        "grid": [gw, gh], "focus": a.focus,
    }
    with open(os.path.join(out, "analysis.json"), "w") as f:
        json.dump(analysis, f, indent=1)
    md = render_analysis_md(analysis, w, h, gw, gh)
    with open(os.path.join(out, "analysis.md"), "w") as f:
        f.write(md)
    print(md)
    print("\n[written] %s" % os.path.join(out, "analysis.md"), file=sys.stderr)


def render_analysis_md(an, w, h, gw, gh):
    pr = an["probe"]
    iv = an["interval_ms"]
    L = []
    L.append("# Recording analysis: %s" % os.path.basename(an["video"]))
    L.append("")
    L.append("Output folder: `%s`" % an["out"])
    if an.get("focus"):
        L.append("Focus: %s" % an["focus"])
    L.append("")
    L.append("## Recording")
    L.append("- %dx%d displayed (stored %sx%s), %s, %.2f s, %d frames decoded. Platform guess from shape: **%s** "
             "(confirm with the user)." % (w, h, pr["stored_w"], pr["stored_h"], pr["codec"], pr["duration"],
                                          an["frames"], an["platform_guess"]))
    L.append("- Frame intervals: median %.1f ms, during motion %.1f ms (~%.0f fps), p95 %.1f ms, max %.0f ms. "
             "Nominal rate %s is a timebase, not the real rate."
             % (iv["median"], iv["median_during_motion"], an["fps_during_motion"], iv["p95"], iv["max"], pr["r_frame_rate"]))
    res = iv["median_during_motion"]
    L.append("- **Timing resolution: about ±%d ms** (one frame during motion). %s"
             % (round(res), "Variable frame rate: the recorder writes frames mostly when the screen changes, so a gap "
                "between frames means nothing changed (or the recorder dropped frames)." if an["vfr"] else ""))
    if res > 34:
        L.append("- Under 30 fps during motion: smoothness and jank cannot be judged; only stalls of 2+ frames.")
    L.append("- Change detection: pixel changes > %d/255 at %d px long edge on a %dx%d cell grid; noise floor %s of the screen."
             % (PIX_THRESH, DIFF_LONG, gw, gh, pct(an["noise_floor"])))
    if an["masks"]:
        L.append("- Ignored for change detection: " + "; ".join(an["masks"]) + ".")
    L.append("")
    L.append("## Activity timeline")
    L.append("Each row is a burst of visual change. `start` is the first frame showing the change, `end` the last "
             "changed frame (the new state). Kind: screen (most of the screen), region (a panel or section), local "
             "(a small area: button, toast, spinner), tiny (a few characters, an icon, the cursor or caret). "
             "Tiny is not unimportant: typed text and label changes are tiny.")
    L.append("")
    L.append("| ID | start | end | dur ms | kind | peak | where: separate changed areas (px x,y,w,h) | frames | longest gap ms |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    tiny = []
    for b in an["bursts"]:
        if b["kind"] == "tiny" and b["dur"] < 0.6 and len(an["bursts"]) > 60:
            tiny.append(b)
            continue
        places = "; ".join("%s %s" % (where(c, gw, gh), bbox_px(c, w, h, gw, gh)) for c in b.get("clusters") or [])
        L.append("| %s | %s | %s | %d | %s | %s | %s | %d | %d |"
                 % (b["id"], ft(b["t0"]), ft(b["t1"]), ms(b["dur"]), b["kind"], pct(b["peak"]),
                    places or "-", b["frames"], ms(b["max_gap"])))
    if tiny:
        L.append("")
        L.append("%d tiny changes (cursor, caret or small icon sized) not listed: %s"
                 % (len(tiny), ", ".join("%s@%s" % (b["id"], ft(b["t0"])) for b in tiny[:40])
                    + (" ..." if len(tiny) > 40 else "")))
    L.append("")
    L.append("## Auto-signals (hypotheses: verify each on frames before reporting; expect ~40% noise)")
    if an["signals"]:
        for s in an["signals"]:
            L.append("- [%s] %s" % (s["type"], s["text"]))
    else:
        L.append("- none")
    L.append("")
    L.append("## Candidate input moments")
    L.append("Input times are not in the video unless touches/clicks are shown. Confirm or correct each on its "
             "event strip, then run `measure` with the input time.")
    if an["candidate_inputs"]:
        for c in an["candidate_inputs"]:
            L.append("- " + c["text"])
    else:
        L.append("- none detected automatically; mark inputs from the strips.")
    L.append("")
    L.append("## Images to review")
    L.append("Overview grids (one cell per distinct visual state, labels show state id and time):")
    for g in an["grids"]:
        L.append("- `%s`: %s" % (g["file"], ", ".join(g["states"])))
    L.append("")
    L.append("Full-resolution state frames (use these for text, spacing, alignment, contrast):")
    for s in an["states"]:
        L.append("- %s %s `%s` (%s)" % (s["id"], ft(s["t"]), s["file"], s["why"]))
    if an["states_thinned"]:
        L.append("- (states were thinned evenly to fit the budget; use `frames` for others)")
    L.append("")
    L.append("Event filmstrips (frame before, first change, middle, last change, +%d ms; labels show +ms from "
             "the first change):" % ms(SETTLE_QUIET))
    for s in an["strips"]:
        L.append("- `%s`%s" % (s["file"], (" (zoomed to x,y,w,h %s)" % (tuple(s["zoom"]),)) if s.get("zoom") else ""))
    if an["strips_thinned"]:
        L.append("- (strips were thinned evenly; use `strip` for others)")
    L.append("")
    return "\n".join(L) + "\n"

# ---------------------------------------------------------------- measure


def cmd_measure(a):
    need_tools()
    d = os.path.abspath(a.dir)
    meta, an = load_cache(d)
    pts = meta["pts"]
    n = meta["n"]
    gw, gh = meta["gw"], meta["gh"]
    w, h = an["probe"]["w"], an["probe"]["h"]
    masked = set(an["masked_cells"])
    for r in a.ignore or []:
        masked |= rect_to_cells(parse_rect(r), w, h, gw, gh)
    frac, hits = frame_signals(meta, masked)
    floor = an["noise_floor"]
    t_in = a.input
    i_in = nearest_frame(pts, t_in)
    end_t = a.until if a.until is not None else pts[-1]
    i_end = nearest_frame(pts, end_t)
    res = an["interval_ms"]["median_during_motion"]

    def active(i):
        return frac[i] > floor or bool(hits[i])

    # 1) every distinct change in the window, as sub-bursts (gap > 60 ms splits)
    subs = []
    for i in range(i_in + 1, i_end + 1):
        if not active(i):
            continue
        if subs and pts[i] - pts[subs[-1]["last"]] <= 0.06:
            s = subs[-1]
        else:
            s = {"first": i, "last": i, "cells": set(), "peak": 0.0}
            subs.append(s)
        s["last"] = i
        s["cells"].update(hits[i])
        s["peak"] = max(s["peak"], frac[i])
    for s in subs:
        cl = clusters(s["cells"], gw, gh)
        s["clusters"] = cl
        s["big"] = max([bbox_area(c, gw, gh) for c in cl] or [0])

    def substantial(s):
        return s["peak"] >= 0.03 or s["big"] >= 0.08

    feedback = subs[0] if subs else None
    response = next((s for s in subs if substantial(s)), None)
    # 2) settled: first quiet stretch >= SETTLE_QUIET after the last change that starts before it
    settled = None
    still_changing = None
    if subs:
        last = subs[0]["last"]
        for s in subs[1:]:
            if pts[s["first"]] - pts[last] >= SETTLE_QUIET:
                break
            last = s["last"]
        quiet_end = pts[i_end] if a.until is not None else pts[-1]
        if quiet_end - pts[last] >= SETTLE_QUIET or (a.until is not None):
            settled = last
        else:
            still_changing = last
    # 3) waits with no change at all between input and the response (or settle)
    target = response["first"] if response else (settled if settled is not None else i_end)
    frozen = []
    prev = i_in
    for i in range(i_in + 1, target + 1):
        if active(i) or i == target:
            if pts[i] - pts[prev] >= 0.25:
                frozen.append((pts[prev], pts[i]))
            prev = i
    # 4) busy indicator: small changes that keep recurring (gaps <= 300 ms) for >= 400 ms
    stop = settled if settled is not None else i_end
    runs = []  # each: [first_i, last_i, bbox]

    def near(p, q):
        return not (p[2] + 1 < q[0] or q[2] + 1 < p[0] or p[3] + 1 < q[1] or q[3] + 1 < p[1])
    for i in range(i_in + 1, stop + 1):
        if not hits[i] or frac[i] >= 0.03:
            continue
        for bb in clusters(hits[i], gw, gh):
            if bbox_area(bb, gw, gh) >= 0.06:
                continue
            for r in runs:
                if pts[i] - pts[r[1]] <= 0.3 and near(bb, r[2]):
                    r[1] = i
                    r[2] = (min(r[2][0], bb[0]), min(r[2][1], bb[1]), max(r[2][2], bb[2]), max(r[2][3], bb[3]))
                    break
            else:
                runs.append([i, i, bb])
    busy = [(r[0], r[1], r[2]) for r in runs if pts[r[1]] - pts[r[0]] >= 0.4]

    def rel(i):
        return ms(pts[i] - t_in)

    def verdict(v, good, poor):
        return "good" if v <= good else ("needs work" if v <= poor else "POOR")

    def place(s):
        return "; ".join("%s %s" % (where(c, gw, gh), bbox_px(c, w, h, gw, gh)) for c in s["clusters"][:3]) or "-"

    L = []
    L.append("### %s" % (a.label or "interaction at %s" % ft(t_in)))
    L.append("- Input: %s (frame on screen %s), found by: %s. Resolution about ±%d ms; every number below is "
             "measured from the input frame." % (ft(t_in), ft(pts[i_in]), a.method, round(res)))
    if not subs:
        L.append("- **No visual change after the input** until %s (%d ms)." % (ft(pts[i_end]), rel(i_end)))
    else:
        L.append("- Changes after the input (each row is one distinct change):")
        L.append("")
        L.append("  | # | starts | ends | peak | changed areas (px x,y,w,h) |")
        L.append("  |---|---|---|---|---|")
        for k, s in enumerate(subs[:15]):
            L.append("  | %d | +%d ms | +%d ms | %s | %s |" % (k + 1, rel(s["first"]), rel(s["last"]), pct(s["peak"]), place(s)))
        if len(subs) > 15:
            L.append("  | ... | %d more | | | |" % (len(subs) - 15))
        L.append("")
        L.append("- First visible change: +%d ms [%s vs 100 / 250 ms]. %s"
                 % (rel(feedback["first"]), verdict(rel(feedback["first"]), 100, 250),
                    "Small: likely pressed state, hover, cursor or caret; confirm on the strip."
                    if not substantial(feedback) else "Substantial."))
        if response is not None and response is not feedback:
            L.append("- First substantial change (response): +%d ms [%s vs 100 ms / 1 s]"
                     % (rel(response["first"]), verdict(rel(response["first"]), 100, 1000)))
        elif response is None:
            L.append("- No substantial change (>= 3%% of screen or a >= 8%% area) in the window: the result may be "
                     "small (toast, label, counter) or missing. Check the strip.")
        if settled is not None:
            L.append("- Visually settled: +%d ms at %s (then %d ms or more without change) [%s vs 1 s action / 3 s view]"
                     % (rel(settled), ft(pts[settled]), ms(SETTLE_QUIET), verdict(rel(settled), 1000, 3000)))
        elif still_changing is not None:
            L.append("- **Did not settle** before the recording ends: still changing at %s (+%d ms)."
                     % (ft(pts[still_changing]), rel(still_changing)))
    for f0, f1 in frozen:
        L.append("- Nothing changed from %s to %s (%d ms) while waiting for the result: no feedback during this wait."
                 % (ft(f0), ft(f1), ms(f1 - f0)))
    for b0, b1, bb in busy:
        L.append("- A small area kept changing from +%d to +%d ms at %s %s: spinner / progress / animation "
                 "candidate (or the cursor). Confirm on the strip." % (rel(b0), rel(b1), where(bb, gw, gh),
                                                                    bbox_px(bb, w, h, gw, gh) if bb else ""))
    L.append("- Ignored regions are excluded. A recorder that skips unchanged frames can hide short changes; "
             "confirm every number on the strip.")

    idx = [max(0, i_in - 1), i_in]
    if feedback:
        idx.append(feedback["first"])
    if response:
        idx.append(response["first"])
    for b0, b1, _ in busy[:1]:
        idx.append((b0 + b1) // 2)
    end_i = settled if settled is not None else still_changing
    if end_i is not None:
        start_i = response["first"] if response else (feedback["first"] if feedback else i_in)
        if end_i - start_i > 2:
            idx += even_thin(list(range(start_i + 1, end_i)), 2)[0]
        idx.append(end_i)
        after = nearest_frame(pts, pts[end_i] + SETTLE_QUIET)
        if after > end_i:
            idx.append(after)
    idx = sorted(set(idx))[:12]
    fdir = os.path.join(d, "cache", "frames")
    extract_frames(an["video"], idx, fdir)
    mdir = os.path.join(d, "measure")
    os.makedirs(mdir, exist_ok=True)
    path = os.path.join(mdir, "M_%s.jpg" % ft(t_in).replace(":", "-"))
    zr = parse_rect(a.crop) if a.crop else None
    build_grid([os.path.join(fdir, "f_%06d.jpg" % i) for i in idx],
               ["%s %s%dMS" % (ft(pts[i]), "+" if pts[i] >= t_in else "", ms(pts[i] - t_in)) for i in idx],
               path, w, h, crop=zr)
    L.append("- Strip: `%s`" % os.path.relpath(path, d))
    text = "\n".join(L) + "\n"
    with open(os.path.join(d, "measurements.md"), "a") as f:
        f.write(text + "\n")
    print(text)

# ---------------------------------------------------------------- strip and frames


def cmd_strip(a):
    need_tools()
    d = os.path.abspath(a.dir)
    meta, an = load_cache(d)
    pts = meta["pts"]
    w, h = an["probe"]["w"], an["probe"]["h"]
    if a.at:
        times = [float(x) for x in a.at.split(",")]
        idx = [nearest_frame(pts, t) for t in times]
        t_ref = times[0] if a.ref is None else a.ref
    else:
        if a.frm is None or a.to is None:
            die("give --from and --to, or --at")
        i0, i1 = nearest_frame(pts, a.frm), nearest_frame(pts, a.to)
        allf = list(range(i0, i1 + 1))
        idx = even_thin(allf, a.cells)[0]
        t_ref = a.frm if a.ref is None else a.ref
    idx = sorted(set(idx))
    fdir = os.path.join(d, "cache", "frames")
    extract_frames(an["video"], idx, fdir)
    sdir = os.path.join(d, "strips")
    os.makedirs(sdir, exist_ok=True)
    name = a.name or "strip_%s_%s" % (ft(pts[idx[0]]).replace(":", "-"), ft(pts[idx[-1]]).replace(":", "-"))
    files = []
    per = a.per_image
    for k in range(0, len(idx), per):
        chunk = idx[k:k + per]
        path = os.path.join(sdir, "%s_%d.jpg" % (name, k // per + 1)) if len(idx) > per else os.path.join(sdir, name + ".jpg")
        build_grid([os.path.join(fdir, "f_%06d.jpg" % i) for i in chunk],
                   ["#%d %s %s%dMS" % (i, ft(pts[i]), "+" if pts[i] >= t_ref else "", ms(pts[i] - t_ref)) for i in chunk],
                   path, w, h, crop=parse_rect(a.crop) if a.crop else None)
        files.append(path)
    print("frames: " + ", ".join("#%d@%s" % (i, ft(pts[i])) for i in idx))
    for f in files:
        print("strip: " + f)


def cmd_frames(a):
    need_tools()
    d = os.path.abspath(a.dir)
    meta, an = load_cache(d)
    pts = meta["pts"]
    times = [float(x) for x in a.at.split(",")]
    idx = [nearest_frame(pts, t) for t in times]
    fdir = os.path.join(d, "cache", "frames")
    extract_frames(an["video"], idx, fdir)
    odir = os.path.join(d, "frames")
    os.makedirs(odir, exist_ok=True)
    for t, i in zip(times, idx):
        dst = os.path.join(odir, "t_%s.jpg" % ft(pts[i]).replace(":", "-"))
        if a.crop:
            x, y, cw, ch = [int(v) for v in parse_rect(a.crop)]
            dst = dst[:-4] + "_crop.jpg"
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", os.path.join(fdir, "f_%06d.jpg" % i),
                 "-vf", "crop=%d:%d:%d:%d,scale='min(%d,iw*2)':-2" % (cw, ch, x, y, LONG_EDGE), "-q:v", "2", dst], stdout=False)
        else:
            save_capped(os.path.join(fdir, "f_%06d.jpg" % i), dst)
        print("%s (asked %s) -> %s" % (ft(pts[i]), ft(t), dst))

# ---------------------------------------------------------------- main


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("analyze")
    p.add_argument("video")
    p.add_argument("--out", help="output folder (default ./recording-audits/<video name>)")
    p.add_argument("--platform", default="auto", help="auto, ios, android, web-mobile, web-desktop, macos, windows, electron")
    p.add_argument("--mask", action="append", help="x,y,w,h px region to ignore for change detection (repeatable)")
    p.add_argument("--no-default-mask", action="store_true", help="do not mask the phone status bar")
    p.add_argument("--max-states", type=int, default=24)
    p.add_argument("--max-strips", type=int, default=14)
    p.add_argument("--cells", type=int, help="states per overview grid (default phone 8, tablet 6, desktop 4)")
    p.add_argument("--focus", help="what the user wants checked (recorded in the analysis)")
    p.set_defaults(fn=cmd_analyze)
    p = sub.add_parser("measure")
    p.add_argument("dir")
    p.add_argument("--input", type=float, required=True, help="input time in seconds")
    p.add_argument("--until", type=float, help="end of window (default: end of recording)")
    p.add_argument("--ignore", action="append", help="x,y,w,h px to ignore (cursor area, the pressed button itself)")
    p.add_argument("--method", default="marked by Claude from frames", help="how the input time was found")
    p.add_argument("--label")
    p.add_argument("--crop", help="x,y,w,h px region to zoom the strip into")
    p.set_defaults(fn=cmd_measure)
    p = sub.add_parser("strip")
    p.add_argument("dir")
    p.add_argument("--from", dest="frm", type=float)
    p.add_argument("--to", type=float)
    p.add_argument("--at", help="comma-separated times")
    p.add_argument("--cells", type=int, default=12, help="max frames in the window")
    p.add_argument("--per-image", type=int, default=6)
    p.add_argument("--ref", type=float, help="time the +ms labels count from")
    p.add_argument("--name")
    p.add_argument("--crop", help="x,y,w,h px region to zoom into")
    p.set_defaults(fn=cmd_strip)
    p = sub.add_parser("frames")
    p.add_argument("dir")
    p.add_argument("--at", required=True)
    p.add_argument("--crop", help="x,y,w,h px region (full resolution, up to 2x zoom)")
    p.set_defaults(fn=cmd_frames)
    a = ap.parse_args()
    if not getattr(a, "fn", None):
        ap.print_help()
        sys.exit(2)
    a.fn(a)


if __name__ == "__main__":
    main()

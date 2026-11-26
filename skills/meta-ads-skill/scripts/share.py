"""Make a single-file copy of a rendered viewer, to send to someone.

Usage:
    python share.py VIEWER_DIR [--ads A1,A2] [--out FILE] [--full-res]

VIEWER_DIR is a folder render.py wrote (a library's viewer/, or a meta-ads-output/ folder).
The result is one .html file with the viewer, the data and every image inside it. It opens
offline by double-click, with no other files, so it can go by email, Slack, Teams or a
shared drive. Nothing is uploaded.

- Videos become their cover frame: the share shows how the ad looks on the device
  (text against image, margins, safe areas), not playback. The viewer says so.
- Images are scaled to at most 1440 px on the long side (enough for phone mockups at 2x)
  unless --full-res is given, to keep the file small.
- --ads limits the copy to some ads; media no remaining ad or brand uses is left out.
- The copy has no Library menu and asks search engines not to index it.

Default output: <library>/exports/<name>-<date>.html for a library, else <VIEWER_DIR>/exports/.
"""
import argparse
import base64
import datetime as dt
import io
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

MAX_SIDE = 1440
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp",
        ".gif": "image/gif", ".svg": "image/svg+xml"}


def slug(s):
    s = re.sub(r"[^A-Za-z0-9]+", "-", s or "ads").strip("-").lower()
    return s[:60] or "ads"


def load_data(folder):
    txt = (folder / "data.js").read_text(encoding="utf-8")
    return json.loads(txt[txt.index("=") + 1:].strip().rstrip(";"))


def data_uri(path, full_res):
    ext = path.suffix.lower()
    raw = path.read_bytes()
    if not full_res and ext in (".jpg", ".jpeg", ".png", ".webp"):
        try:
            from PIL import Image
            with Image.open(io.BytesIO(raw)) as im:
                if max(im.size) > MAX_SIDE:
                    im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
                    buf = io.BytesIO()
                    if ext == ".png" and im.mode in ("RGBA", "LA", "P"):
                        im.save(buf, "PNG", optimize=True)
                    else:
                        im.convert("RGB").save(buf, "JPEG", quality=85, optimize=True)
                        ext = ".jpg"
                    if buf.tell() < len(raw):
                        raw = buf.getvalue()
                    else:
                        ext = path.suffix.lower()
        except Exception as e:  # noqa: BLE001  (unreadable image: embed as-is)
            print(f"  could not scale {path.name}: {e}")
    return f"data:{MIME.get(ext, 'application/octet-stream')};base64," + base64.b64encode(raw).decode("ascii")


def media_ids(x):
    """Every string that could be a media ID, anywhere in an ad or brand."""
    if isinstance(x, dict):
        for v in x.values():
            yield from media_ids(v)
    elif isinstance(x, list):
        for v in x:
            yield from media_ids(v)
    elif isinstance(x, str):
        yield x


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("viewer")
    ap.add_argument("--ads", help="comma-separated ad IDs to include (default: all)")
    ap.add_argument("--out", help="output .html file")
    ap.add_argument("--full-res", action="store_true", help="embed images at their original size")
    a = ap.parse_args()

    src = Path(a.viewer).resolve()
    if not (src / "index.html").exists() or not (src / "data.js").exists():
        sys.exit(f"{src} has no index.html and data.js; pass a folder render.py wrote")
    data = load_data(src)

    if a.ads:
        want = [x.strip() for x in a.ads.split(",") if x.strip()]
        have = {ad["id"] for ad in data["ads"]}
        bad = [x for x in want if x not in have]
        if bad:
            sys.exit(f"unknown ad id(s): {', '.join(bad)}")
        keep = set(want)
        data["ads"] = [ad for ad in data["ads"] if ad["id"] in keep]
        data["matrix"] = {k: v for k, v in data["matrix"].items() if k in keep}
        used_brands = {ad.get("brand") for ad in data["ads"]}
        data["brands"] = {k: v for k, v in data["brands"].items() if k in used_brands}
    used = set(media_ids(data["ads"])) | set(media_ids(data["brands"]))
    data["media"] = {k: v for k, v in data["media"].items() if k in used}

    videos = missing = 0
    for mid, m in data["media"].items():
        if m.get("kind") == "video":
            m.pop("src", None)          # cover frame only; the viewer shows the poster
            videos += 1
            if not m.get("poster"):
                missing += 1
                print(f"  video {mid} has no cover frame (ffmpeg wasn't available at render); it will show blank")
        for k in ("src", "poster"):
            v = m.get(k)
            if isinstance(v, str) and not v.startswith("data:"):
                f = (src / v).resolve()
                if f.exists():
                    m[k] = data_uri(f, a.full_res)
                else:
                    print(f"  missing file for {mid}.{k}: {v}")
                    m.pop(k, None)
    in_library = src.name == "viewer" and (src.parent / "ads.json").exists()
    # The library's folder name lets the copy link back to the library and home page when it's opened
    # where it was made (<library>/exports/). Sent elsewhere, those files don't exist and no links show.
    data["share"] = {"created": dt.datetime.now().isoformat(timespec="minutes"), "videos_as_frames": videos,
                     "library": src.parent.name if in_library else None}

    html = (src / "index.html").read_text(encoding="utf-8")
    payload = "window.META_ADS = " + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + ";"
    html, n = re.subn(r'<script src="data\.js(\?v=[^"]*)?"></script>', lambda _: f"<script>{payload}</script>", html, count=1)
    if not n:
        sys.exit("index.html doesn't load data.js the expected way; re-render with this skill version first")
    html = re.sub(r'<meta name="meta-ads-(library|embed)"[^>]*>\n?', "", html)   # no Library menu or Save in a share
    html = html.replace('<meta charset="utf-8">', '<meta charset="utf-8">\n<meta name="robots" content="noindex, nofollow">', 1)
    title = ((data.get("campaign") or {}).get("name") or "Ad mockups") + " (shared)"
    title = title.replace("&", "&amp;").replace("<", "&lt;")
    html = re.sub(r"<title>[^<]*</title>", lambda _: f"<title>{title}</title>", html, count=1)

    name = slug((data.get("campaign") or {}).get("name"))
    if a.out:
        out = Path(a.out).resolve()
    else:
        base = src.parent if (src.name == "viewer" and (src.parent / "ads.json").exists()) else src
        out = base / "exports" / f"{name}-{dt.date.today().isoformat()}.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8", newline="")
    mb = out.stat().st_size / 1e6
    if in_library and not a.out:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import library  # noqa: E402
        root = library.root_of(src.parent / "ads.json")
        if root:
            library.write_index(root)
    print(f"Wrote {out}")
    print(f"  {len(data['ads'])} ads, {len(data['media'])} media embedded, {videos} video(s) as cover frames, {mb:.1f} MB")
    if mb > 20:
        print("  Over 20 MB: too big for most email. Use --ads to share fewer ads, or a shared folder.")


if __name__ == "__main__":
    main()

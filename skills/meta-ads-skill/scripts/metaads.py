"""Core logic shared by check.py and render.py.

Loads an ads.json spec, measures media, applies defaults, and resolves every
ad x placement into a concrete rendering plan (which media, how it is fitted,
status, warnings). The viewer only draws what this module decides, so the
rules live in exactly one place.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

SKILL_DIR = Path(__file__).resolve().parent.parent
PLACEMENTS_FILE = SKILL_DIR / "assets" / "placements.json"

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}

AD_FIELDS = {
    "id", "label", "group", "brand", "format", "primary_text", "headline",
    "description", "cta", "display_link", "destination_url", "creative",
    "cards", "engagement", "placements", "source", "notes",
}
CARD_FIELDS = {"creative", "headline", "description", "destination_url", "cta", "display_link"}
BRAND_FIELDS = {"page_name", "avatar", "ig_handle", "ig_avatar", "verified"}
MEDIA_FIELDS = {"kind", "src", "poster", "ratio", "label", "color", "notes"}
DEFAULTABLE = AD_FIELDS - {"id", "label", "source", "notes"}

DEFAULT_ENGAGEMENT = {"reactions": 248, "comments": 31, "shares": 12, "views": 18400, "likes": 1248}


# --------------------------------------------------------------------------- utils

def load_placements() -> dict:
    with open(PLACEMENTS_FILE, encoding="utf-8") as f:
        return json.load(f)


def parse_ratio(value, ratios: dict) -> float | None:
    """'4:5' -> 0.8, '1.91:1' -> 1.91, 0.8 -> 0.8."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    s = str(value).strip()
    if s in ratios:
        return float(ratios[s])
    m = re.fullmatch(r"\s*([\d.]+)\s*[:x/]\s*([\d.]+)\s*", s)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return a / b if a > 0 and b > 0 else None
    return None


def ratio_name(aspect: float, ratios: dict, tol: float = 0.03) -> str:
    best, dist = None, 9.0
    for name, val in ratios.items():
        d = abs(math.log(aspect / val))
        if d < dist:
            best, dist = name, d
    if best and dist <= tol:
        return best
    w = round(aspect * 100)
    return f"{aspect:.2f}:1" if aspect >= 1 else f"1:{1/aspect:.2f}"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def probe(path: Path) -> dict:
    """Measure an image or video. Returns {w,h,duration?,kind}."""
    ext = path.suffix.lower()
    if ext in VIDEO_EXT:
        try:
            out = subprocess.run(
                ["ffprobe", "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height:stream_side_data=rotation:format=duration",
                 "-of", "json", str(path)],
                capture_output=True, text=True, timeout=60)
            data = json.loads(out.stdout or "{}")
            st = (data.get("streams") or [{}])[0]
            w, h = int(st.get("width", 0)), int(st.get("height", 0))
            rot = 0
            for sd in st.get("side_data_list", []) or []:
                if "rotation" in sd:
                    rot = abs(int(sd["rotation"]))
            if rot in (90, 270):
                w, h = h, w
            dur = float((data.get("format") or {}).get("duration", 0) or 0)
            return {"kind": "video", "w": w, "h": h, "duration": round(dur, 2)}
        except Exception as e:  # noqa: BLE001
            return {"kind": "video", "error": f"ffprobe failed: {e}"}
    try:
        from PIL import Image, ImageOps
        with Image.open(path) as im:
            im = ImageOps.exif_transpose(im)
            return {"kind": "image", "w": im.width, "h": im.height}
    except Exception as e:  # noqa: BLE001
        return {"kind": "image", "error": f"cannot read image: {e}"}


def dhash(path: Path) -> tuple[int, tuple] | None:
    """Perceptual fingerprint: (difference hash of the luminance, mean RGB colour).
    The colour part keeps same-shape, different-colour images (e.g. one logo in
    several brand colours) from counting as duplicates."""
    try:
        from PIL import Image, ImageStat
        with Image.open(path) as im:
            rgb = im.convert("RGB")
            mean = tuple(round(v) for v in ImageStat.Stat(rgb).mean)
            g = rgb.convert("L").resize((9, 8))
            px = list(g.getdata())
        bits = 0
        for r in range(8):
            for c in range(8):
                bits = (bits << 1) | (px[r * 9 + c] > px[r * 9 + c + 1])
        return bits, mean
    except Exception:  # noqa: BLE001
        return None


def domain_of(url: str | None) -> str | None:
    if not url:
        return None
    try:
        host = urlparse(url if "//" in url else "https://" + url).hostname or ""
        return host[4:] if host.startswith("www.") else host or None
    except Exception:  # noqa: BLE001
        return None


# --------------------------------------------------------------------------- loading

class Report:
    def __init__(self):
        self.errors: list[dict] = []
        self.warnings: list[dict] = []

    def error(self, where: str, msg: str):
        self.errors.append({"where": where, "message": msg})

    def warn(self, where: str, msg: str):
        self.warnings.append({"where": where, "message": msg})


def load_spec(path: str | os.PathLike) -> tuple[dict | None, Path, Report]:
    rep = Report()
    p = Path(path).resolve()
    try:
        with open(p, encoding="utf-8-sig") as f:
            spec = json.load(f)
    except FileNotFoundError:
        rep.error("file", f"{p} not found")
        return None, p, rep
    except json.JSONDecodeError as e:
        rep.error("file", f"invalid JSON at line {e.lineno} col {e.colno}: {e.msg}")
        return None, p, rep
    if not isinstance(spec, dict):
        rep.error("file", "top level must be a JSON object")
        return None, p, rep
    return spec, p, rep


def resolve(spec: dict, spec_path: Path, rep: Report, placements_cfg: dict | None = None,
            measure: bool = True) -> dict:
    """Validate and resolve a spec. Never invents ad content; only reports."""
    cfg = placements_cfg or load_placements()
    ratios = cfg["ratios"]
    plist = cfg["placements"]
    pmap = {p["id"]: p for p in plist}
    cta_labels = cfg["cta"]
    base = spec_path.parent

    # ---- top level
    if spec.get("spec_version") != 1:
        rep.error("spec_version", "must be 1")
    for k in spec:
        if k not in {"spec_version", "campaign", "brands", "media", "defaults", "ads", "notes", "source"}:
            rep.warn(k, "unknown top-level field ignored")
    campaign = spec.get("campaign") or {}
    if not isinstance(campaign, dict) or not campaign.get("name"):
        rep.error("campaign.name", "required (used for the output folder name)")
        campaign = {"name": "untitled"} if not isinstance(campaign, dict) else {**campaign, "name": campaign.get("name") or "untitled"}

    # ---- media
    media_in = spec.get("media")
    if not isinstance(media_in, dict):
        rep.error("media", "required: an object mapping media IDs to media entries ({} is allowed)")
        media_in = {}
    media: dict[str, dict] = {}
    by_hash: dict[str, list[str]] = {}
    avatar_ids = {b.get(k) for b in (spec.get("brands") or {}).values() if isinstance(b, dict)
                  for k in ("avatar", "ig_avatar")} - {None}
    for mid, m in media_in.items():
        where = f"media.{mid}"
        if not isinstance(m, dict):
            rep.error(where, "must be an object")
            continue
        for k in m:
            if k not in MEDIA_FIELDS:
                rep.warn(f"{where}.{k}", "unknown field ignored")
        kind = m.get("kind")
        if kind not in ("image", "video", "placeholder"):
            rep.error(f"{where}.kind", "must be 'image', 'video' or 'placeholder'")
            continue
        entry = {"id": mid, "kind": kind, "label": m.get("label"), "notes": m.get("notes")}
        if kind == "placeholder":
            asp = parse_ratio(m.get("ratio"), ratios)
            if not asp:
                rep.error(f"{where}.ratio", "placeholders need a ratio such as '1:1', '4:5', '9:16', '1.91:1'")
                continue
            entry.update({"aspect": asp, "ratio": ratio_name(asp, ratios), "color": m.get("color") or "#3a3b3c",
                          "placeholder": True})
            media[mid] = entry
            continue
        src = m.get("src")
        if not src:
            rep.error(f"{where}.src", "required for image/video")
            continue
        entry["placeholder"] = False
        if re.match(r"^https?://", str(src)):
            entry["src_url"] = src
            asp = parse_ratio(m.get("ratio"), ratios)
            rep.warn(f"{where}.src", "remote URL: downloaded at render time; Meta CDN links expire within days, prefer local files")
            if asp:
                entry.update({"aspect": asp, "ratio": ratio_name(asp, ratios)})
            else:
                rep.warn(f"{where}.ratio", "remote media without 'ratio': measured only after download")
            media[mid] = entry
            continue
        fp = (base / src).resolve() if not os.path.isabs(src) else Path(src)
        entry["path"] = str(fp)
        if not fp.exists():
            rep.error(f"{where}.src", f"file not found: {fp}")
            continue
        ext = fp.suffix.lower()
        if kind == "image" and ext in VIDEO_EXT:
            rep.error(f"{where}.kind", "file is a video but kind is 'image'")
        if kind == "video" and ext in IMAGE_EXT:
            rep.error(f"{where}.kind", "file is an image but kind is 'video'")
        if measure:
            info = probe(fp)
            if info.get("error"):
                rep.error(where, info["error"])
                continue
            entry.update({"w": info["w"], "h": info["h"]})
            if info.get("duration"):
                entry["duration"] = info["duration"]
            if not info["w"] or not info["h"]:
                rep.error(where, "could not measure dimensions")
                continue
            asp = info["w"] / info["h"]
            entry.update({"aspect": asp, "ratio": ratio_name(asp, ratios)})
            declared = parse_ratio(m.get("ratio"), ratios)
            if declared and abs(math.log(declared / asp)) > 0.03:
                rep.warn(f"{where}.ratio", f"declared {m.get('ratio')} but file measures {entry['ratio']} ({info['w']}x{info['h']}); using the measured ratio")
            if min(info["w"], info["h"]) < (160 if mid in avatar_ids else 600):
                rep.warn(where, f"low resolution {info['w']}x{info['h']} (Meta recommends at least 1080 px on the short side)")
            sha = file_sha256(fp)
            entry["sha256"] = sha
            by_hash.setdefault(sha, []).append(mid)
            if kind == "image":
                entry["dhash"] = dhash(fp)
        if kind == "video":
            poster = m.get("poster")
            if poster:
                pp = (base / poster).resolve() if not os.path.isabs(poster) else Path(poster)
                if pp.exists():
                    entry["poster_path"] = str(pp)
                else:
                    rep.warn(f"{where}.poster", f"poster not found ({pp}); a frame will be extracted")
        media[mid] = entry

    for sha, ids in by_hash.items():
        if len(ids) > 1:
            rep.warn("media", f"{', '.join(ids)} are the same file content; list it once and reuse the ID (stored once either way)")
    imgs = [m for m in media.values() if m.get("dhash") is not None]
    seen_pairs = set()
    for i, a in enumerate(imgs):
        for b in imgs[i + 1:]:
            if a.get("sha256") == b.get("sha256"):
                continue
            (ha, ca), (hb, cb) = a["dhash"], b["dhash"]
            same_colour = max(abs(x - y) for x, y in zip(ca, cb)) <= 12
            if same_colour and bin(ha ^ hb).count("1") <= 4 and abs(math.log(a["aspect"] / b["aspect"])) < 0.02:
                key = tuple(sorted((a["id"], b["id"])))
                if key not in seen_pairs:
                    seen_pairs.add(key)
                    rep.warn("media", f"{a['id']} and {b['id']} look like the same picture (different files); consider listing it once")

    # ---- brands
    brands_in = spec.get("brands")
    brands: dict[str, dict] = {}
    if not isinstance(brands_in, dict) or not brands_in:
        rep.error("brands", "required: at least one brand, e.g. {\"b_main\": {\"page_name\": \"…\"}}")
        brands_in = {}
    for bid, b in brands_in.items():
        where = f"brands.{bid}"
        if not isinstance(b, dict):
            rep.error(where, "must be an object")
            continue
        for k in b:
            if k not in BRAND_FIELDS:
                rep.warn(f"{where}.{k}", "unknown field ignored")
        nb = {"id": bid, "page_name": b.get("page_name"), "ig_handle": b.get("ig_handle"),
              "verified": bool(b.get("verified")), "placeholder_fields": []}
        if not nb["page_name"]:
            rep.warn(f"{where}.page_name", "missing; mockups show 'Your Brand'")
            nb["page_name"] = "Your Brand"
            nb["placeholder_fields"].append("page_name")
        if not nb["ig_handle"]:
            derived = re.sub(r"[^a-z0-9._]", "", nb["page_name"].lower().replace(" ", ""))
            nb["ig_handle"] = derived or "yourbrand"
            rep.warn(f"{where}.ig_handle", f"missing; Instagram mockups show '{nb['ig_handle']}'")
            nb["placeholder_fields"].append("ig_handle")
        for key in ("avatar", "ig_avatar"):
            ref = b.get(key)
            if ref is None:
                continue
            if ref not in media:
                if ref not in media_in:  # entries that failed validation already reported an error
                    rep.error(f"{where}.{key}", f"unknown media ID '{ref}'")
            elif media[ref]["kind"] == "video":
                rep.error(f"{where}.{key}", "avatar must be an image or placeholder media entry, not a video")
            else:
                nb[key] = ref
                if media[ref]["kind"] == "placeholder" and key == "avatar":
                    nb["placeholder_fields"].append("avatar")
                    rep.warn(f"{where}.avatar", f"placeholder '{ref}'; replace with the page's real profile picture when available")
        if "avatar" not in b:
            rep.error(f"{where}.avatar", "required: media ID of the page's profile picture (save it locally), or of a "
                      "placeholder such as {\"kind\": \"placeholder\", \"ratio\": \"1:1\", \"label\": \"<brand> logo\", "
                      "\"color\": \"#…\"} when you don't have it")
            nb["placeholder_fields"].append("avatar")
        brands[bid] = nb
    default_brand = next(iter(brands), None)

    # ---- defaults
    defaults = spec.get("defaults") or {}
    if not isinstance(defaults, dict):
        rep.error("defaults", "must be an object")
        defaults = {}
    for k in defaults:
        if k not in DEFAULTABLE:
            rep.warn(f"defaults.{k}", "not a defaultable ad field; ignored")

    # ---- ads
    ads_in = spec.get("ads")
    if not isinstance(ads_in, list) or not ads_in:
        rep.error("ads", "required: a non-empty list")
        ads_in = []
    ads: list[dict] = []
    ids_seen = set()
    for i, a in enumerate(ads_in):
        where = f"ads[{i}]"
        if not isinstance(a, dict):
            rep.error(where, "must be an object")
            continue
        aid = a.get("id")
        if not aid or not isinstance(aid, str):
            rep.error(f"{where}.id", "required string")
            aid = f"ad{i+1}"
        elif not re.fullmatch(r"[A-Za-z0-9_.-]{1,40}", aid):
            rep.error(f"{where}.id", "use letters, digits, '_', '-', '.' (max 40); it becomes part of file names")
        if aid in ids_seen:
            rep.error(f"{where}.id", f"duplicate id '{aid}'")
        ids_seen.add(aid)
        where = f"ads[{aid}]"
        for k in a:
            if k not in AD_FIELDS:
                rep.warn(f"{where}.{k}", "unknown field ignored")
        ad = {k: defaults[k] for k in DEFAULTABLE if k in defaults}
        ad.update({k: v for k, v in a.items() if k in AD_FIELDS})
        ad["id"] = aid
        ad["_placeholders"] = []
        fmt = ad.get("format")
        if fmt not in ("image", "video", "carousel"):
            rep.error(f"{where}.format", "must be 'image', 'video' or 'carousel'")
            continue
        bid = ad.get("brand") or default_brand
        if bid not in brands:
            rep.error(f"{where}.brand", f"unknown brand ID '{bid}'")
            continue
        ad["brand"] = bid
        for f in ("primary_text", "headline", "description", "display_link", "destination_url", "label", "group"):
            if f in ad and ad[f] is not None and not isinstance(ad[f], str):
                rep.error(f"{where}.{f}", "must be a string")
                ad[f] = str(ad[f])
        if not ad.get("primary_text"):
            rep.warn(f"{where}.primary_text", "missing; mockups show it empty")
        # CTA
        if "cta" in ad and ad["cta"] is not None:
            code = str(ad["cta"]).strip().upper().replace(" ", "_")
            if code not in cta_labels:
                label_match = [c for c, l in cta_labels.items() if l.lower() == str(ad["cta"]).strip().lower()]
                if label_match:
                    rep.warn(f"{where}.cta", f"'{ad['cta']}' is a label; use the code {label_match[0]}")
                    code = label_match[0]
                else:
                    rep.error(f"{where}.cta", f"unknown CTA '{ad['cta']}' (see the CTA table in SPEC.md)")
                    code = None
            ad["cta"] = None if code == "NO_BUTTON" else code
        elif "cta" not in ad:
            rep.warn(f"{where}.cta", "not given; rendered with no button (set null to silence this)")
            ad["cta"] = None
        if not ad.get("display_link"):
            d = domain_of(ad.get("destination_url"))
            if d:
                ad["display_link"] = d
        # engagement
        eng = dict(DEFAULT_ENGAGEMENT)
        if isinstance(ad.get("engagement"), dict):
            for k, v in ad["engagement"].items():
                if k in eng and (v is None or isinstance(v, (int, float))):
                    eng[k] = v
                else:
                    rep.warn(f"{where}.engagement.{k}", "unknown key or non-numeric value ignored")
        ad["engagement"] = eng
        # creative
        def check_creative(cmap, w):
            out = {}
            if not isinstance(cmap, dict) or not cmap:
                rep.error(w, "required: object mapping ratio -> media ID, e.g. {\"1:1\": \"m_hero\"}")
                return out
            for key, mid in cmap.items():
                if mid not in media:
                    rep.error(f"{w}.{key}", f"unknown media ID '{mid}'")
                    continue
                mk = media[mid]["kind"]
                if fmt == "video" and mk == "image":
                    rep.error(f"{w}.{key}", f"video ad points at image media '{mid}'")
                    continue
                if fmt in ("image", "carousel") and mk == "video" and fmt == "image":
                    rep.error(f"{w}.{key}", f"image ad points at video media '{mid}' (use format 'video')")
                    continue
                declared = parse_ratio(key, ratios)
                asp = media[mid].get("aspect")
                if declared is None:
                    rep.warn(f"{w}.{key}", f"key '{key}' is not a ratio; the media's measured ratio is used")
                elif asp and abs(math.log(declared / asp)) > 0.03:
                    rep.warn(f"{w}.{key}", f"listed as {key} but '{mid}' measures {media[mid].get('ratio')}; the measured ratio is used")
                out[key] = mid
            return out
        if fmt in ("image", "video"):
            ad["creative"] = check_creative(ad.get("creative"), f"{where}.creative")
            if ad.get("cards"):
                rep.warn(f"{where}.cards", "ignored: only carousel ads use cards")
            ad["cards"] = []
        else:
            cards = ad.get("cards")
            if not isinstance(cards, list) or not (2 <= len(cards) <= 10):
                rep.error(f"{where}.cards", "carousel needs 2-10 cards")
                cards = cards if isinstance(cards, list) else []
            norm = []
            for j, c in enumerate(cards):
                cw = f"{where}.cards[{j}]"
                if not isinstance(c, dict):
                    rep.error(cw, "must be an object")
                    continue
                for k in c:
                    if k not in CARD_FIELDS:
                        rep.warn(f"{cw}.{k}", "unknown field ignored")
                nc = {k: c.get(k) for k in CARD_FIELDS}
                nc["creative"] = check_creative(c.get("creative"), f"{cw}.creative")
                if nc.get("cta") is not None:
                    code = str(nc["cta"]).strip().upper().replace(" ", "_")
                    nc["cta"] = code if code in cta_labels and code != "NO_BUTTON" else None
                    if code not in cta_labels:
                        rep.error(f"{cw}.cta", f"unknown CTA '{c.get('cta')}'")
                elif "cta" not in c:
                    nc["cta"] = ad.get("cta")
                if not nc.get("headline"):
                    rep.warn(f"{cw}.headline", "missing")
                norm.append(nc)
            ad["cards"] = norm
            if ad.get("creative"):
                rep.warn(f"{where}.creative", "ignored: carousel ads use per-card creative")
            ad["creative"] = {}
        # placements filter
        pl = ad.get("placements", "auto")
        if pl in (None, "auto"):
            allowed = [p["id"] for p in plist]
        elif isinstance(pl, list):
            bad = [x for x in pl if x not in pmap]
            for x in bad:
                rep.error(f"{where}.placements", f"unknown placement '{x}'")
            allowed = [x for x in pl if x in pmap]
        elif isinstance(pl, dict) and isinstance(pl.get("exclude"), list):
            for x in pl["exclude"]:
                if x not in pmap:
                    rep.error(f"{where}.placements.exclude", f"unknown placement '{x}'")
            allowed = [p["id"] for p in plist if p["id"] not in pl["exclude"]]
        else:
            rep.error(f"{where}.placements", "use 'auto', a list of placement IDs, or {\"exclude\": [...]}")
            allowed = [p["id"] for p in plist]
        ad["_allowed"] = allowed
        ads.append(ad)

    # ---- matrix
    matrix: dict[str, dict] = {}
    for ad in ads:
        row = {}
        for p in plist:
            row[p["id"]] = plan_placement(ad, p, media, brands, ratios, cfg)
        matrix[ad["id"]] = row

    return {
        "campaign": campaign,
        "brands": brands,
        "media": media,
        "ads": ads,
        "matrix": matrix,
        "placements": plist,
        "cta": cta_labels,
        "ratios": ratios,
        "placements_version": cfg.get("version_date"),
    }


# --------------------------------------------------------------------------- planning

def _fit(aspect: float, rule: dict) -> tuple[str, float]:
    """Return (mode, box_aspect) for media of `aspect` in a slot governed by `rule`."""
    lo, hi = rule["native_min"], rule["native_max"]
    if lo - 0.01 <= aspect <= hi + 0.01:
        return "native", min(max(aspect, lo), hi)
    out = rule.get("outside", "crop")
    if out in ("crop", "pad"):
        return out, lo if aspect < lo else hi
    return out, rule.get("box", rule["ideal"])


def _choose(cmap: dict, rule: dict, media: dict) -> tuple[str | None, str, float]:
    best = None
    for key, mid in cmap.items():
        m = media.get(mid)
        if not m or not m.get("aspect"):
            continue
        mode, box = _fit(m["aspect"], rule)
        dist = abs(math.log(m["aspect"] / rule["ideal"]))
        score = (0 if mode == "native" else 1, 1 if m.get("placeholder") else 0, dist)
        if best is None or score < best[0]:
            best = (score, mid, mode, box)
    if best is None:
        return None, "missing", rule["ideal"]
    return best[1], best[2], best[3]


def plan_placement(ad, p, media, brands, ratios, cfg) -> dict:
    fmt = ad["format"]
    res = {"status": "actual", "reasons": [], "slots": [], "needs": []}
    if p["id"] not in ad["_allowed"]:
        return {"status": "excluded", "reasons": ["excluded by the ad's placements setting"], "slots": [], "needs": []}
    if fmt not in p["formats"]:
        return {"status": "not_eligible", "reasons": [f"{fmt} ads don't run in {p['name']}"], "slots": [], "needs": []}
    rule = p["media"][fmt] if fmt in p["media"] else p["media"].get("default")
    cmaps = [ad["creative"]] if fmt != "carousel" else [c["creative"] for c in ad["cards"]]
    if fmt == "carousel" and len(ad["cards"]) < p.get("carousel_min_cards", 2):
        return {"status": "not_eligible", "reasons": [f"{p['name']} carousels need at least {p['carousel_min_cards']} cards"],
                "slots": [], "needs": []}
    if not cmaps or all(not c for c in cmaps):
        return {"status": "not_eligible", "reasons": ["no usable creative"], "slots": [], "needs": []}
    ideal_name = ratio_name(rule["ideal"], ratios)
    for idx, cmap in enumerate(cmaps):
        mid, mode, box = _choose(cmap, rule, media)
        slot = {"media": mid, "mode": mode, "box": box}
        res["slots"].append(slot)
        label = f"card {idx+1}" if fmt == "carousel" else "creative"
        if mid is None:
            res["status"] = "not_eligible"
            res["reasons"].append(f"{label}: no usable media")
            continue
        m = media[mid]
        if m.get("placeholder"):
            res["reasons"].append(f"{label}: placeholder creative ({m.get('label') or mid})")
            res["needs"].append({"type": "placeholder", "media": mid})
        if mode != "native":
            how = {"crop": "cropped", "pad": "padded with gray bars", "fill": "shown smaller on a blurred fill",
                   "letterbox": "letterboxed"}.get(mode, mode)
            res["reasons"].append(f"{label}: {m['ratio']} {how}; {ideal_name} would fit natively")
            res["needs"].append({"type": "ratio", "media": mid, "ratio": ideal_name})
    b = brands[ad["brand"]]
    if b["placeholder_fields"]:
        relevant = [f for f in b["placeholder_fields"] if not (f == "ig_handle" and p["platform"] != "instagram")]
        if relevant:
            res["reasons"].append("placeholder identity: " + ", ".join(relevant))
        if "avatar" in b["placeholder_fields"] and b.get("avatar") and res["status"] != "not_eligible":
            res["needs"].append({"type": "placeholder", "media": b["avatar"]})
    if res["status"] != "not_eligible" and res["reasons"]:
        res["status"] = "simulated"
    # copy checks
    res["copy"] = copy_checks(ad, p)
    return res


def copy_checks(ad, p) -> list[str]:
    notes = []
    t = p.get("text", {})
    pt = ad.get("primary_text") or ""
    lim = (t.get("primary_text") or {}).get("chars")
    if pt and lim and len(pt) > lim and (t.get("primary_text") or {}).get("show", True):
        notes.append(f"primary text {len(pt)} chars; truncates around {lim} with '{t['primary_text'].get('more', '…See more')}'")
    for f in ("headline", "description"):
        cfg = t.get(f) or {}
        v = ad.get(f) or ""
        if ad["format"] == "carousel":
            v = max((c.get(f) or "" for c in ad["cards"]), key=len, default="")
        if v and cfg.get("show") and cfg.get("chars") and len(v) > cfg["chars"]:
            notes.append(f"{f} {len(v)} chars; recommended ≤ {cfg['chars']} here")
    return notes


# --------------------------------------------------------------------------- inventory

def inventory(res: dict, rep: Report) -> dict:
    plist = res["placements"]
    counts = {"actual": 0, "simulated": 0, "not_eligible": 0, "excluded": 0}
    unlock: dict[tuple, dict] = {}
    for ad in res["ads"]:
        for p in plist:
            cell = res["matrix"][ad["id"]][p["id"]]
            counts[cell["status"]] = counts.get(cell["status"], 0) + 1
            for need in cell.get("needs", []):
                if need["type"] == "ratio":
                    key = ("ratio", need["media"], need["ratio"])
                else:
                    key = ("placeholder", need["media"], None)
                u = unlock.setdefault(key, {"ads": set(), "placements": set(), "mockups": 0})
                u["ads"].add(ad["id"])
                u["placements"].add(p["id"])
                u["mockups"] += 1
    unlock_list = []
    for (typ, mid, ratio), u in sorted(unlock.items(), key=lambda kv: -kv[1]["mockups"]):
        m = res["media"][mid]
        if typ == "ratio":
            text = f"Add a {ratio} version of {mid} ({m.get('label') or m.get('ratio')}) → {u['mockups']} mockups become native"
        else:
            text = f"Replace placeholder {mid} ('{m.get('label') or ''}') with a real file → {u['mockups']} mockups stop using a stand-in"
        unlock_list.append({"type": typ, "media": mid, "ratio": ratio, "mockups": u["mockups"],
                            "ads": sorted(u["ads"]), "placements": sorted(u["placements"]), "text": text})
    # shopping list: placeholders and which ratios their placements want
    usage: dict[str, set] = {}
    for ad in res["ads"]:
        cmaps = [ad["creative"]] if ad["format"] != "carousel" else [c["creative"] for c in ad["cards"]]
        for cm in cmaps:
            for mid in cm.values():
                usage.setdefault(mid, set()).add(ad["id"])
    avatar_of: dict[str, list] = {}
    for bid, b in res["brands"].items():
        for key in ("avatar", "ig_avatar"):
            if b.get(key):
                avatar_of.setdefault(b[key], []).append(bid)
    shopping = []
    for mid, m in res["media"].items():
        if not m.get("placeholder"):
            continue
        want = set()
        for ad in res["ads"]:
            if ad["id"] not in usage.get(mid, ()):
                continue
            for p in plist:
                cell = res["matrix"][ad["id"]][p["id"]]
                if cell["status"] in ("actual", "simulated"):
                    rule = p["media"].get(ad["format"]) or p["media"].get("default")
                    want.add(ratio_name(rule["ideal"], res["ratios"]))
        used = sorted(usage.get(mid, ()))
        if mid in avatar_of:
            used += [f"avatar of {bid}" for bid in avatar_of[mid]]
            want.add("1:1")
        shopping.append({"media": mid, "label": m.get("label"), "ratio": m.get("ratio"),
                         "used_by": used, "ratios_for_full_coverage": sorted(want)})
    media_report = []
    for mid, m in res["media"].items():
        media_report.append({"media": mid, "kind": m["kind"], "ratio": m.get("ratio"),
                             "size": f"{m['w']}x{m['h']}" if m.get("w") else None,
                             "used_by": sorted(usage.get(mid, ()))})
    return {
        "ok": not rep.errors,
        "errors": rep.errors,
        "warnings": rep.warnings,
        "counts": counts,
        "unlock": unlock_list,
        "shopping_list": shopping,
        "media": media_report,
        "matrix": {aid: {pid: {k: v for k, v in cell.items() if k in ("status", "reasons", "copy")}
                         for pid, cell in row.items()} for aid, row in res["matrix"].items()},
        "placements_version": res.get("placements_version"),
    }


ICON = {"actual": "✅", "simulated": "⚠️", "not_eligible": "⛔", "excluded": "·"}


def inventory_md(res: dict, inv: dict) -> str:
    plist = res["placements"]
    L = [f"# Inventory — {res['campaign'].get('name')}", ""]
    c = inv["counts"]
    L.append(f"{len(res['ads'])} ads × {len(plist)} placements: ✅ {c.get('actual',0)} actual · ⚠️ {c.get('simulated',0)} simulated · ⛔ {c.get('not_eligible',0)} not eligible · · {c.get('excluded',0)} excluded")
    L.append(f"\nPlacement specs dated {inv.get('placements_version')}.\n")
    if inv["errors"]:
        L.append("## Errors (must fix before rendering)\n")
        L += [f"- `{e['where']}`: {e['message']}" for e in inv["errors"]]
        L.append("")
    if inv["unlock"]:
        L.append("## To unlock more (biggest impact first)\n")
        L += [f"{i+1}. {u['text']} (ads: {', '.join(u['ads'][:8])}{'…' if len(u['ads'])>8 else ''})" for i, u in enumerate(inv["unlock"][:25])]
        L.append("")
    if inv["shopping_list"]:
        L.append("## Creative shopping list (placeholders)\n")
        L.append("| Media | Intended image | Used by | Ratios for full coverage |")
        L.append("|---|---|---|---|")
        for s in inv["shopping_list"]:
            n_ads = sum(1 for u in s["used_by"] if not u.startswith("avatar of "))
            avs = [u for u in s["used_by"] if u.startswith("avatar of ")]
            used = ", ".join(([f"{n_ads} ads"] if n_ads else []) + avs)
            L.append(f"| {s['media']} | {s['label'] or ''} | {used} | {', '.join(s['ratios_for_full_coverage'])} |")
        L.append("")
    L.append("## Status grid\n")
    L.append("| Ad | " + " | ".join(p["short"] for p in plist) + " |")
    L.append("|---|" + "---|" * len(plist))
    for ad in res["ads"]:
        L.append(f"| {ad['id']} | " + " | ".join(ICON[inv['matrix'][ad['id']][p['id']]['status']] for p in plist) + " |")
    L.append("\nColumns: " + ", ".join(f"{p['short']} = {p['name']}" for p in plist) + "\n")
    L.append("## Details\n")
    for ad in res["ads"]:
        L.append(f"### {ad['id']}{' — ' + ad['label'] if ad.get('label') else ''}\n")
        for p in plist:
            cell = inv["matrix"][ad["id"]][p["id"]]
            if cell["status"] == "actual" and not cell.get("copy"):
                continue
            bits = cell.get("reasons", []) + cell.get("copy", [])
            if bits:
                L.append(f"- {ICON[cell['status']]} **{p['name']}**: " + "; ".join(bits))
        L.append("")
    if inv["warnings"]:
        L.append("## Warnings\n")
        L += [f"- `{w['where']}`: {w['message']}" for w in inv["warnings"]]
        L.append("")
    L.append("## Media\n")
    L.append("| Media | Kind | Ratio | Size | Used by |")
    L.append("|---|---|---|---|---|")
    for m in inv["media"]:
        L.append(f"| {m['media']} | {m['kind']} | {m['ratio'] or ''} | {m['size'] or ''} | {len(m['used_by'])} ads |")
    return "\n".join(L) + "\n"

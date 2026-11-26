"""Real map data for a place: OpenStreetMap inside a radius -> map/osm.json in metres east / north of the pin.

    python3 osm_fetch.py <project dir>                 (reads place.json: lat, lon, radius_m, far_radius_m)
    python3 osm_fetch.py <project dir> --file x.json   (use a saved Overpass / OSM API JSON extract instead of the network)

Sources, tried in order: Overpass mirrors (one filtered query), then the OpenStreetMap API in tiles (always complete
but only practical up to about 3 km). The far ring (coast, big water, main roads, land use out to far_radius_m) needs
Overpass; without it the engine fills the distance procedurally.

Output keys: buildings, roads, rails, water, waterways, coast, areas, trees, points, far{...}, meta.
Data (c) OpenStreetMap contributors, ODbL: say so wherever the result is shown.
"""
import json, math, os, sys, time, urllib.request, urllib.parse, urllib.error

UA = "placeforge/0.1 (open-source 3D place builder)"
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter",
            "https://overpass.private.coffee/api/interpreter", "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
API = "https://api.openstreetmap.org/api/0.6/map.json?bbox=%.6f,%.6f,%.6f,%.6f"
GREEN = {"park": "park", "garden": "park", "playground": "park", "pitch": "pitch", "golf_course": "grass",
         "grass": "grass", "meadow": "grass", "village_green": "grass", "recreation_ground": "grass", "cemetery": "grass",
         "forest": "forest", "wood": "forest", "scrub": "scrub", "orchard": "forest", "farmland": "farm",
         "sand": "sand", "beach": "sand", "parking": "parking", "residential": "residential", "commercial": "commercial",
         "retail": "commercial", "industrial": "industrial", "railway": "railyard", "construction": "construction",
         "swimming_pool": "pool", "wetland": "wetland", "bare_rock": "rock", "heath": "scrub"}


def http(url, data=None, timeout=60):
    req = urllib.request.Request(url, data=data, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def overpass(query, timeout=90):
    body = urllib.parse.urlencode({"data": query}).encode()
    for u in OVERPASS:
        try:
            t0 = time.time()
            d = json.loads(http(u, body, timeout))
            if "elements" in d:
                print("overpass ok: %s, %d elements, %.0f s" % (u.split("/")[2], len(d["elements"]), time.time() - t0))
                return d
        except Exception as e:
            print("overpass failed: %s (%s)" % (u.split("/")[2], str(e)[:70]))
    return None


def api_tiles(lat, lon, radius):
    """The plain OSM API, bbox by bbox (50,000 nodes per call): split a tile in four when it is refused."""
    dlat, dlon = radius / 110574.0, radius / (111320.0 * math.cos(math.radians(lat)))
    n = max(1, int(math.ceil(2 * dlat / 0.012)))
    if n > 6:
        raise SystemExit("radius %.0f m is too large for the OSM API fallback (Overpass is unreachable). Retry later, "
                         "lower radius_m, or pass --file with an extract." % radius)
    todo = []
    for i in range(n):
        for j in range(n):
            todo.append((lon - dlon + 2 * dlon * i / n, lat - dlat + 2 * dlat * j / n,
                         lon - dlon + 2 * dlon * (i + 1) / n, lat - dlat + 2 * dlat * (j + 1) / n))
    seen, out, calls = set(), [], 0
    while todo:
        b = todo.pop()
        try:
            d = json.loads(http(API % b, timeout=90))
            calls += 1
        except urllib.error.HTTPError as e:
            if e.code in (400, 509) and b[2] - b[0] > 0.001:
                mx, my = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
                todo += [(b[0], b[1], mx, my), (mx, b[1], b[2], my), (b[0], my, mx, b[3]), (mx, my, b[2], b[3])]
                continue
            raise
        for e in d["elements"]:
            k = (e["type"], e["id"])
            if k not in seen:
                seen.add(k)
                out.append(e)
        time.sleep(1.0)
    print("OSM API ok: %d calls, %d elements" % (calls, len(out)))
    return {"elements": out}


def q_near(lat, lon, r):
    a = "(around:%d,%.6f,%.6f)" % (r, lat, lon)
    sel = ['way%s[building]', 'relation%s[building]', 'way%s["building:part"]', 'way%s[highway]', 'way%s[railway]',
           'way%s[natural]', 'relation%s[natural]', 'way%s[waterway]', 'relation%s[waterway]', 'way%s[landuse]',
           'relation%s[landuse]', 'way%s[leisure]', 'relation%s[leisure]', 'way%s[amenity~"parking|fountain"]',
           'way%s[man_made~"pier|breakwater|bridge|groyne"]', 'way%s[place=square]', 'node%s[natural=tree]',
           'node%s[highway=street_lamp]', 'node%s[amenity~"fountain|bench"]']
    return "[out:json][timeout:90];(%s);out body;>;out skel qt;" % "".join(s % a + ";" for s in sel)


def q_far(lat, lon, r):
    a = "(around:%d,%.6f,%.6f)" % (r, lat, lon)
    sel = ['way%s[natural=coastline]', 'way%s[natural=water]', 'relation%s[natural=water]',
           'way%s[waterway~"river|canal"]', 'way%s[highway~"^(motorway|trunk|primary)$"]',
           'way%s[landuse~"forest|residential|industrial|commercial|retail"]', 'way%s[natural=wood]',
           'way%s[leisure=park]', 'way%s[railway=rail]']
    return "[out:json][timeout:120];(%s);out body;>;out skel qt;" % "".join(s % a + ";" for s in sel)


def num(s, default=None):
    """'12 m', '12.5', '40 ft' -> metres."""
    if s is None:
        return default
    s = str(s).strip().lower().replace(",", ".")
    k = 0.3048 if ("ft" in s or "'" in s) else 1.0
    t = ""
    for ch in s:
        if ch.isdigit() or ch in ".-":
            t += ch
        elif t:
            break
    try:
        return float(t) * k
    except ValueError:
        return default


def rings(ways_pts):
    """Join member ways end to end into closed rings (multipolygon outers)."""
    segs = [list(p) for p in ways_pts if len(p) >= 2]
    out = []
    while segs:
        cur = segs.pop()
        grew = True
        while grew and cur[0] != cur[-1]:
            grew = False
            for i, s in enumerate(segs):
                if s[0] == cur[-1]:
                    cur += s[1:]
                elif s[-1] == cur[-1]:
                    cur += s[::-1][1:]
                elif s[-1] == cur[0]:
                    cur = s[:-1] + cur
                elif s[0] == cur[0]:
                    cur = s[::-1][:-1] + cur
                else:
                    continue
                segs.pop(i)
                grew = True
                break
        if len(cur) >= 4 and cur[0] == cur[-1]:
            out.append(cur[:-1])
    return out


def convert(d, lat0, lon0, radius, far=False):
    ky, kx = 110574.0, 111320.0 * math.cos(math.radians(lat0))
    nodes = {e["id"]: e for e in d["elements"] if e["type"] == "node"}
    ways = {e["id"]: e for e in d["elements"] if e["type"] == "way"}

    def xy(n):
        return (round((n["lon"] - lon0) * kx, 2), round((n["lat"] - lat0) * ky, 2))

    def pts(w):
        return [xy(nodes[i]) for i in w["nodes"] if i in nodes]

    def near(p, m=1.0):
        return any(x * x + y * y <= (radius * m) ** 2 for x, y in p)

    out = {"buildings": [], "roads": [], "rails": [], "water": [], "waterways": [], "coast": [], "areas": [],
           "trees": [], "points": []}
    in_rel = set()
    rel_items = []
    for e in d["elements"]:
        if e["type"] != "relation":
            continue
        t = e.get("tags", {})
        outer = [pts(ways[m["ref"]]) for m in e.get("members", []) if m["type"] == "way" and m.get("role") != "inner"
                 and m["ref"] in ways]
        for m in e.get("members", []):
            if m["type"] == "way" and not ways.get(m["ref"], {}).get("tags"):
                in_rel.add(m["ref"])
        for ring in rings(outer):
            rel_items.append((t, ring))

    def area_kind(t):
        for key in ("leisure", "landuse", "natural", "amenity"):
            if t.get(key) in GREEN:
                return GREEN[t[key]]
        if t.get("place") == "square" or (t.get("highway") == "pedestrian" and t.get("area") == "yes"):
            return "plaza"
        if t.get("man_made") in ("pier", "breakwater", "groyne", "bridge"):
            return "pier"
        return None

    def building(t, p, part=False):
        b = {"p": p, "k": t.get("building:part" if part else "building", "yes")}
        h, lv = num(t.get("height") or t.get("building:height")), num(t.get("building:levels"))
        if h:
            b["h"] = round(h, 1)
        if lv:
            b["lv"] = lv
        for a, k in (("min_height", "minh"), ("roof:height", "roofh"), ("roof:levels", "rooflv")):
            v = num(t.get(a))
            if v:
                b[k] = v
        for a, k in (("name", "name"), ("roof:shape", "roof"), ("building:material", "mat"), ("building:colour", "col"),
                     ("roof:colour", "roofcol"), ("amenity", "am"), ("man_made", "mm"), ("tourism", "tourism")):
            if t.get(a):
                b[k] = t[a]
        if part:
            b["part"] = 1
        return b

    def poly(t, p):
        """One closed ring with tags -> the right list."""
        if len(p) < 3 or not near(p):
            return
        if "building" in t and t["building"] != "no" and not far:
            out["buildings"].append(building(t, p))
        elif "building:part" in t and t["building:part"] != "no" and not far:
            out["buildings"].append(building(t, p, True))
        elif t.get("natural") == "water" or t.get("waterway") in ("riverbank", "dock") or t.get("landuse") in ("reservoir", "basin"):
            out["water"].append({"p": p, "k": t.get("water", "water"), "name": t.get("name")})
        else:
            k = area_kind(t)
            if k:
                out["areas"].append({"p": p, "k": k, "name": t.get("name"), "sport": t.get("sport")})

    for t, ring in rel_items:
        poly(t, ring)
    for w in ways.values():
        t = w.get("tags", {})
        if not t:
            continue
        p = pts(w)
        if len(p) < 2:
            continue
        closed = w["nodes"][0] == w["nodes"][-1] and len(p) >= 4
        if t.get("natural") == "coastline":
            out["coast"].append({"p": p})
        elif "highway" in t and not (closed and t.get("area") == "yes"):
            if far or near(p):
                out["roads"].append({"p": p, "k": t["highway"], "lanes": num(t.get("lanes")), "oneway": t.get("oneway") in ("yes", "1", "true"),
                                     "bridge": t.get("bridge", "no") != "no", "tunnel": t.get("tunnel", "no") != "no",
                                     "name": t.get("name"), "surface": t.get("surface"), "layer": num(t.get("layer"), 0)})
        elif t.get("railway") in ("rail", "tram", "light_rail", "subway", "narrow_gauge", "monorail"):
            if far or near(p):
                out["rails"].append({"p": p, "k": t["railway"], "service": t.get("service", "main"),
                                     "bridge": t.get("bridge", "no") != "no", "tunnel": t.get("tunnel", "no") != "no"})
        elif t.get("waterway") in ("river", "canal", "stream", "drain", "ditch") and not closed:
            if far or near(p):
                wd = num(t.get("width")) or {"river": 30.0, "canal": 10.0, "stream": 3.0, "drain": 2.0, "ditch": 1.5}[t["waterway"]]
                out["waterways"].append({"p": p, "k": t["waterway"], "w": wd, "name": t.get("name"), "tunnel": t.get("tunnel", "no") != "no"})
        elif t.get("natural") == "tree_row":
            for (x0, y0), (x1, y1) in zip(p, p[1:]):
                L = math.hypot(x1 - x0, y1 - y0)
                for k in range(int(L / 9) + 1):
                    f = k * 9 / max(L, 1e-6)
                    out["trees"].append((round(x0 + (x1 - x0) * f, 1), round(y0 + (y1 - y0) * f, 1)))
        elif closed:
            poly(t, p[:-1])
    for n in nodes.values():
        t = n.get("tags")
        if not t:
            continue
        q = xy(n)
        if q[0] ** 2 + q[1] ** 2 > radius ** 2:
            continue
        if t.get("natural") == "tree":
            out["trees"].append(q)
        elif t.get("highway") == "street_lamp":
            out["points"].append({"k": "lamp", "x": q[0], "y": q[1]})
        elif t.get("amenity") in ("fountain", "bench"):
            out["points"].append({"k": t["amenity"], "x": q[0], "y": q[1]})
    # a building drawn in 3D parts: keep the parts, drop the outline they sit in
    parts = [b for b in out["buildings"] if b.get("part")]
    if parts:
        cents = [(sum(q[0] for q in b["p"]) / len(b["p"]), sum(q[1] for q in b["p"]) / len(b["p"])) for b in parts]
        keep = []
        for b in out["buildings"]:
            if not b.get("part") and any(inside(b["p"], cx, cy) for cx, cy in cents):
                continue
            keep.append(b)
        out["buildings"] = keep
    return out


def inside(poly, x, y):
    c = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            c = not c
        j = i
    return c


def preview(osm, path, radius, camera=None, size=1400):
    """A picture of the map (north up) so the agent and the user can check the pin, the radius and the camera."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return print("map preview skipped (pip install pillow)")
    ext = radius * 1.25
    if camera:
        ext = max(ext, 1.1 * max(abs(camera["x"]), abs(camera["y"])))
    k = size / (2 * ext)
    P = lambda q: (size / 2 + q[0] * k, size / 2 - q[1] * k)
    im = Image.new("RGB", (size, size), (238, 236, 228))
    d = ImageDraw.Draw(im)
    far = osm.get("far") or {}
    col = {"park": (190, 220, 170), "grass": (205, 228, 180), "forest": (160, 200, 150), "scrub": (190, 210, 165),
           "pitch": (170, 215, 170), "parking": (215, 215, 215), "sand": (240, 228, 180), "plaza": (228, 222, 210),
           "residential": (232, 228, 220), "commercial": (236, 222, 222), "industrial": (226, 220, 232),
           "railyard": (220, 215, 225), "farm": (228, 232, 196), "pier": (200, 196, 188)}
    for a in far.get("areas", []) + osm["areas"]:
        if len(a["p"]) >= 3:
            d.polygon([P(q) for q in a["p"]], fill=col.get(a["k"], (225, 225, 215)))
    for w in far.get("water", []) + osm["water"]:
        if len(w["p"]) >= 3:
            d.polygon([P(q) for q in w["p"]], fill=(150, 190, 225))
    for w in far.get("waterways", []) + osm["waterways"]:
        d.line([P(q) for q in w["p"]], fill=(150, 190, 225), width=max(1, int(w["w"] * k)))
    for c in far.get("coast", []) + osm["coast"]:
        d.line([P(q) for q in c["p"]], fill=(40, 90, 170), width=3)
    for r in far.get("roads", []) + osm["roads"]:
        big = r["k"] in ("motorway", "trunk", "primary", "secondary")
        foot = r["k"] in ("footway", "path", "steps", "pedestrian", "cycleway")
        d.line([P(q) for q in r["p"]], fill=(200, 200, 200) if foot else (255, 255, 255) if not big else (250, 215, 130),
               width=1 if foot else max(1, int((9 if big else 5) * k)))
    for r in osm["rails"]:
        d.line([P(q) for q in r["p"]], fill=(90, 90, 100), width=1)
    for b in osm["buildings"]:
        d.polygon([P(q) for q in b["p"]], fill=(196, 182, 170), outline=(150, 138, 128))
    for t in osm["trees"]:
        x, y = P(t)
        d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=(90, 160, 90))
    step = 100 if radius <= 1200 else 500 if radius <= 6000 else 1000
    g = -int(ext / step) * step
    while g <= ext:
        d.line([P((g, -ext)), P((g, ext))], fill=(214, 212, 204) if g else (150, 150, 150), width=1)
        d.line([P((-ext, g)), P((ext, g))], fill=(214, 212, 204) if g else (150, 150, 150), width=1)
        g += step
    c = P((0, 0))
    d.ellipse((c[0] - radius * k, c[1] - radius * k, c[0] + radius * k, c[1] + radius * k), outline=(220, 40, 60), width=3)
    d.line((c[0] - 14, c[1], c[0] + 14, c[1]), fill=(220, 40, 60), width=3)
    d.line((c[0], c[1] - 14, c[0], c[1] + 14), fill=(220, 40, 60), width=3)
    if camera:
        cx, cy = P((camera["x"], camera["y"]))
        b, half = math.radians(camera["bearing"]), math.radians(camera.get("hfov", 60) / 2)
        L = 2.2 * ext * k
        for a in (b - half, b + half):
            d.line((cx, cy, cx + L * math.sin(a), cy - L * math.cos(a)), fill=(20, 110, 220), width=2)
        d.ellipse((cx - 7, cy - 7, cx + 7, cy + 7), fill=(20, 110, 220))
        d.text((cx + 10, cy - 6), "camera", fill=(20, 110, 220))
    d.text((12, 10), "N up   grid %d m   red ring = radius %d m   (c) OpenStreetMap contributors" % (step, radius), fill=(30, 30, 30))
    im.save(path)
    print("map preview:", path)


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    proj = os.path.abspath(args[0])
    place = json.load(open(os.path.join(proj, "place.json")))
    lat, lon, radius = float(place["lat"]), float(place["lon"]), float(place.get("radius_m", 800))
    fr = place.get("far_radius_m", "auto")
    far_r = min(8000.0, max(3000.0, 4 * radius)) if fr in ("auto", None, "") else float(fr)
    os.makedirs(os.path.join(proj, "map"), exist_ok=True)
    raw_p = os.path.join(proj, "map", "osm_raw.json")
    src, far = "file", None
    if "--file" in args:
        raw = json.load(open(args[args.index("--file") + 1]))
    elif "--reuse" in args and os.path.exists(raw_p):
        raw = json.load(open(raw_p))
        src = "cached"
    else:
        raw = None if "--api" in args else overpass(q_near(lat, lon, radius * 1.08))
        src = "overpass"
        if raw is None:
            raw = api_tiles(lat, lon, radius * 1.08)
            src = "osm-api"
        json.dump(raw, open(raw_p, "w"))
    osm = convert(raw, lat, lon, radius * 1.08)
    if far_r > radius and "--file" not in args and "--nofar" not in args:
        far_p = os.path.join(proj, "map", "osm_far_raw.json")
        fr = json.load(open(far_p)) if ("--reuse" in args and os.path.exists(far_p)) else overpass(q_far(lat, lon, far_r), 150)
        if fr:
            json.dump(fr, open(far_p, "w"))
            far = convert(fr, lat, lon, far_r, far=True)
            far = {k: far[k] for k in ("water", "waterways", "coast", "roads", "rails", "areas")}
        else:
            print("far ring: Overpass unreachable, the engine will fill the distance procedurally (rerun `pf map` later)")
    osm["far"] = far
    osm["meta"] = {"lat": lat, "lon": lon, "radius_m": radius, "far_radius_m": far_r if far else 0, "source": src,
                   "fetched": time.strftime("%Y-%m-%d"), "attribution": "(c) OpenStreetMap contributors, ODbL 1.0",
                   "counts": {k: len(v) for k, v in osm.items() if isinstance(v, list)}}
    dst = os.path.join(proj, "map", "osm.json")
    json.dump(osm, open(dst, "w"), separators=(",", ":"))
    print("map:", dst, "%.0f kB" % (os.path.getsize(dst) / 1e3), osm["meta"]["counts"])
    c = osm["meta"]["counts"]
    if c["buildings"] < 30:
        print("NOTE: only %d mapped buildings. The area is thinly mapped: raise infill.density in place.json and check "
              "the pin with map/preview.png." % c["buildings"])
    cam = None
    cm = place.get("camera") or {}
    if cm.get("distance_m"):
        b = math.radians(cm.get("bearing_deg", 0.0))
        off = cm.get("offset_right_m", 0.0)
        cam = {"x": -cm["distance_m"] * math.sin(b) - off * math.cos(b), "y": -cm["distance_m"] * math.cos(b) + off * math.sin(b),
               "bearing": cm.get("bearing_deg", 0.0), "hfov": cm.get("hfov_deg", 60)}
    preview(osm, os.path.join(proj, "map", "preview.png"), radius, cam)


if __name__ == "__main__":
    main()

"""placeforge engine, city: the real neighbourhood from OpenStreetMap (map/osm.json, made by tools/osm_fetch.py)
turned into geometry. Mapped things are drawn as mapped; the generator only fills what the map leaves empty
(unmapped streets inside the radius, and the far ring out to the horizon).

Data (c) OpenStreetMap contributors, ODbL.
"""
import bpy, bmesh, json, math, os, random
from mathutils import Vector, Matrix, noise
from mathutils.geometry import tessellate_polygon
import pf_core as pf
import pf_look as look
from pf_core import cfg

WIDTH = {"motorway": 11.0, "motorway_link": 6.0, "trunk": 9.0, "primary": 8.5, "trunk_link": 6.0, "primary_link": 6.0,
         "secondary": 8.0, "secondary_link": 6.0, "tertiary": 7.5, "tertiary_link": 5.5, "residential": 6.0,
         "living_street": 5.0, "unclassified": 6.0, "service": 4.0, "track": 3.0, "pedestrian": 5.0, "footway": 2.0,
         "cycleway": 2.0, "path": 1.6, "steps": 2.2, "busway": 7.0, "road": 6.0}
FOOT = ("pedestrian", "footway", "path", "steps", "cycleway", "bridleway", "corridor")
SKIP_ROADS = ("proposed", "construction", "razed", "abandoned", "platform", "elevator", "bus_stop", "rest_area", "services", "raceway", "via_ferrata")
BIG = ("motorway", "trunk", "primary", "secondary", "tertiary")
LOW = ("house", "detached", "semidetached_house", "bungalow", "hut", "shed", "garage", "garages", "cabin", "farm_auxiliary",
       "kiosk", "roof", "carport", "greenhouse", "static_caravan", "terrace", "residential")
SHED = ("industrial", "warehouse", "shed", "hangar", "garage", "garages", "manufacture", "barn", "farm_auxiliary", "roof", "carport")
NAMED = {"white": "#f2f2f2", "black": "#1a1a1a", "grey": "#808080", "gray": "#808080", "red": "#a03020", "brown": "#6b4a32",
         "yellow": "#d8c060", "beige": "#d6c8a8", "cream": "#e8dfc8", "green": "#4a7050", "blue": "#4a6890", "orange": "#c87838",
         "pink": "#d8a0a0", "silver": "#b8b8bc", "tan": "#c8a878", "maroon": "#682828", "lightgrey": "#c0c0c0", "darkgrey": "#505050"}


def colour(s):
    """An OSM colour tag (#rrggbb or a name) as linear RGB, or None."""
    if not s:
        return None
    s = NAMED.get(s.strip().lower().replace(" ", "").replace("_", ""), s.strip())
    if s.startswith("#") and len(s) in (4, 7):
        h = s[1:]
        if len(h) == 3:
            h = "".join(c * 2 for c in h)
        try:
            return tuple(((int(h[i:i + 2], 16) / 255.0) ** 2.2) * 0.85 for i in (0, 2, 4))
        except ValueError:
            return None
    return None


def area(p):
    return pf.signed_area(p)


def centroid(p):
    return sum(q[0] for q in p) / len(p), sum(q[1] for q in p) / len(p)


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


def obb(p):
    """Smallest rectangle round a footprint: centre x, y, width, depth, angle of the width axis."""
    best = None
    for i in range(len(p)):
        (x0, y0), (x1, y1) = p[i], p[(i + 1) % len(p)]
        if math.hypot(x1 - x0, y1 - y0) < 0.5:
            continue
        a = math.atan2(y1 - y0, x1 - x0)
        c, s = math.cos(a), math.sin(a)
        us = [x * c + y * s for x, y in p]
        vs = [-x * s + y * c for x, y in p]
        w, d = max(us) - min(us), max(vs) - min(vs)
        if best is None or w * d < best[0]:
            u, v = (max(us) + min(us)) / 2, (max(vs) + min(vs)) / 2
            best = (w * d, u * c - v * s, u * s + v * c, w, d, a)
    return best[1:] if best else (*centroid(p), 1.0, 1.0, 0.0)


def length(p):
    return sum(math.hypot(p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1]) for i in range(len(p) - 1))


def walk(p, s):
    """Point and heading at distance s along a polyline."""
    for i in range(len(p) - 1):
        (x0, y0), (x1, y1) = p[i], p[i + 1]
        L = math.hypot(x1 - x0, y1 - y0)
        if s <= L or i == len(p) - 2:
            f = s / max(L, 1e-6)
            return x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, math.atan2(y1 - y0, x1 - x0)
        s -= L
    return p[-1][0], p[-1][1], 0.0


def thin(p, step):
    out = [p[0]]
    for q in p[1:-1]:
        if math.hypot(q[0] - out[-1][0], q[1] - out[-1][1]) >= step:
            out.append(q)
    if len(p) > 1:
        out.append(p[-1])
    return out


def chain(items, directed=False):
    """Join ways that meet end to end and share a key (OSM splits one street or one shore into many ways)."""
    items = [dict(i, p=list(i["p"])) for i in items]
    while True:
        ends = {}
        for idx, it in enumerate(items):
            if it is not None:
                for e in (0, -1):
                    ends.setdefault((round(it["p"][e][0], 1), round(it["p"][e][1], 1), it.get("key")), []).append((idx, e))
        done = True
        for lst in ends.values():
            if len(lst) != 2 or lst[0][0] == lst[1][0]:
                continue
            (i, ei), (j, ej) = lst
            a, b = items[i], items[j]
            if a is None or b is None:
                continue
            if directed or a.get("oneway"):
                if ei == 0 and ej == -1:
                    i, j, a, b, ei, ej = j, i, b, a, ej, ei
                elif not (ei == -1 and ej == 0):
                    continue
            pa = a["p"] if ei == -1 else a["p"][::-1]
            pb = b["p"] if ej == 0 else b["p"][::-1]
            a["p"] = pa + pb[1:]
            items[j] = None
            done = False
        if done:
            return [i for i in items if i]


class Grid:
    def __init__(self, cell):
        self.c, self.d = cell, {}

    def add(self, x, y, item):
        self.d.setdefault((int(x // self.c), int(y // self.c)), []).append(item)

    def near(self, x, y):
        i, j = int(x // self.c), int(y // self.c)
        for a in (i - 1, i, i + 1):
            for b in (j - 1, j, j + 1):
                yield from self.d.get((a, b), ())


class Mask:
    """A raster of yes / no over a square (thousands of wet / dry questions while the city is generated)."""

    def __init__(self, half, cell):
        self.h, self.c = half, cell
        self.n = int(2 * half / cell) + 2
        self.rows = [bytearray(self.n) for _ in range(self.n)]

    def poly(self, p, v=1):
        ys = [q[1] for q in p]
        j0, j1 = max(0, int((min(ys) + self.h) / self.c)), min(self.n - 1, int((max(ys) + self.h) / self.c) + 1)
        n = len(p)
        for j in range(j0, j1 + 1):
            y = -self.h + (j + 0.5) * self.c
            xs = []
            for i in range(n):
                (x0, y0), (x1, y1) = p[i], p[(i + 1) % n]
                if (y0 > y) != (y1 > y):
                    xs.append(x0 + (x1 - x0) * (y - y0) / (y1 - y0))
            xs.sort()
            row = self.rows[j]
            for k in range(0, len(xs) - 1, 2):
                i0 = max(0, int((xs[k] + self.h) / self.c + 0.5))
                i1 = min(self.n, int((xs[k + 1] + self.h) / self.c + 0.5))
                if i1 > i0:
                    row[i0:i1] = bytes([v]) * (i1 - i0)

    def line(self, p, hw):
        r = max(1, int(hw / self.c))
        L, s = length(p), 0.0
        while s <= L:
            x, y, _ = walk(p, s)
            i, j = int((x + self.h) / self.c), int((y + self.h) / self.c)
            i0, i1 = max(0, i - r), min(self.n, i + r + 1)
            if i1 > i0:                                   # an empty or reversed slice assignment would shorten the row
                for b in range(max(0, j - r), min(self.n, j + r + 1)):
                    self.rows[b][i0:i1] = b"\x01" * (i1 - i0)
            s += self.c

    def get(self, x, y):
        i, j = int((x + self.h) / self.c), int((y + self.h) / self.c)
        return 0 <= i < self.n and 0 <= j < self.n and self.rows[j][i]

    def covers(self, x, y):
        return abs(x) < self.h and abs(y) < self.h


def clip_circle(p, R):
    """The parts of a polyline inside the circle of radius R, with exact entry and exit points on it."""
    runs, cur = [], []
    for (x0, y0), (x1, y1) in zip(p, p[1:]):
        dx, dy = x1 - x0, y1 - y0
        a = dx * dx + dy * dy
        if a < 1e-9:
            continue
        b = 2 * (x0 * dx + y0 * dy)
        c = x0 * x0 + y0 * y0 - R * R
        disc = b * b - 4 * a * c
        ts = []
        if disc > 0:
            sq = math.sqrt(disc)
            ts = [t for t in ((-b - sq) / (2 * a), (-b + sq) / (2 * a)) if 0.0 < t < 1.0]
        ins = c <= 0
        if ins and not cur:
            cur = [(x0, y0)]
        for t in ts:
            q = (x0 + dx * t, y0 + dy * t)
            if ins:
                cur.append(q)
                runs.append(cur)
                cur = []
            else:
                cur = [q]
            ins = not ins
        if ins:
            cur.append((x1, y1))
    if len(cur) > 1:
        runs.append(cur)
    return runs


def sea_polygons(coast, R):
    """OpenStreetMap coastlines run with the land on their left. Close each stretch along the circle of radius R on
    its right-hand side: those polygons are the sea. Closed loops inside are islands (returned separately)."""
    ways = chain([{"p": c["p"], "key": 0} for c in coast], directed=True)
    runs, islands = [], []
    for w in ways:
        p = w["p"]
        if p[0] == p[-1] and all(x * x + y * y < R * R for x, y in p):
            islands.append(p[:-1])
            continue
        for r in clip_circle(p, R * 0.985):
            if len(r) >= 2:
                runs.append(r)
    ang = lambda q: math.atan2(q[1], q[0])
    polys, used = [], set()
    for s in range(len(runs)):
        if s in used:
            continue
        poly, i = [], s
        for _ in range(len(runs) + 1):
            used.add(i)
            poly += runs[i]
            a0 = ang(runs[i][-1])
            # clockwise along the circle (sea on the right of the coast) to the next stretch's start
            best, bd = None, 1e9
            for k in range(len(runs)):
                d = (a0 - ang(runs[k][0])) % (2 * math.pi)
                if d < bd and (k == s or k not in used):
                    best, bd = k, d
            n = max(1, int(bd / math.radians(4)))
            rr = R * 0.985
            poly += [(rr * math.cos(a0 - bd * t / n), rr * math.sin(a0 - bd * t / n)) for t in range(1, n)]
            if best == s or best is None:
                break
            i = best
        if len(poly) >= 3:
            polys.append(poly)
    return polys, islands


class Map:
    """The place's map in world metres, with fast lookups."""

    def __init__(self, path):
        d = json.load(open(path))
        self.meta = d.get("meta", {})
        self.R = float(cfg("radius_m"))
        fr = cfg("far_radius_m")
        self.FR = max(self.R, min(8000.0, max(3000.0, 4 * self.R)) if fr in ("auto", None) else float(fr))
        far = d.get("far") or {}
        self.has_far = bool(far)
        tp = lambda p: [(float(x), float(y)) for x, y in p]
        self.buildings = []
        for b in d["buildings"]:
            p = tp(b["p"])
            if len(p) < 3 or abs(area(p)) < 4.0:
                continue
            if area(p) < 0:
                p.reverse()
            self.buildings.append(dict(b, p=p))
        self.roads = []
        for i, r in enumerate(d["roads"]):
            if r["k"] in SKIP_ROADS or r.get("tunnel"):
                continue
            foot = r["k"] in FOOT
            w = r["lanes"] * 3.3 if r.get("lanes") and not foot else WIDTH.get(r["k"], 5.0)
            self.roads.append({"p": tp(r["p"]), "k": r["k"], "w": w, "foot": foot, "oneway": bool(r.get("oneway")), "id": len(self.roads),
                               "bridge": bool(r.get("bridge")), "key": (r.get("name") or r["k"], r["k"], bool(r.get("oneway")), w)})
        self.rails = [{"p": tp(r["p"]), "k": r.get("k", "rail"), "service": r.get("service", "main"), "key": r.get("service", "main")}
                      for r in d["rails"] if not r.get("tunnel")]
        self.areas = []
        for a in d["areas"] + [dict(a, far=1) for a in far.get("areas", [])]:
            p = tp(a["p"])
            if len(p) < 3:
                continue
            if area(p) < 0:
                p.reverse()
            xs, ys = [q[0] for q in p], [q[1] for q in p]
            self.areas.append({"p": p, "k": a["k"], "sport": a.get("sport"), "far": a.get("far", 0), "bb": (min(xs), min(ys), max(xs), max(ys))})
        self.garea = Grid(200.0)
        for a in self.areas:
            bb = a["bb"]
            for i in range(int(bb[0] // 200), int(bb[2] // 200) + 1):
                for j in range(int(bb[1] // 200), int(bb[3] // 200) + 1):
                    self.garea.d.setdefault((i, j), []).append(a)
        self.trees = [tuple(t) for t in d["trees"]]
        self.points = d.get("points", [])
        # water: polygons (lakes, river banks), centre lines (rivers, canals), the sea from the coastline
        seen, self.water = set(), []
        for w in d["water"] + far.get("water", []):
            p = thin(tp(w["p"]), 3.0)
            k = (round(p[0][0]), round(p[0][1]), len(p))
            if len(p) >= 3 and k not in seen and abs(area(p)) > 30:
                seen.add(k)
                self.water.append(p)
        self.waterways = [{"p": tp(w["p"]), "w": float(w["w"])} for w in (far.get("waterways") or d["waterways"]) if not w.get("tunnel")]
        coast = far.get("coast") or d["coast"]
        self.sea, self.islands = sea_polygons([{"p": thin(tp(c["p"]), 6.0)} for c in coast], self.FR * 1.6 if coast else 1.0) if coast else ([], [])
        E = self.R * 1.15
        self.wet = Mask(E, max(2.0, E / 450.0))
        self.wet_far = Mask(self.FR * 1.1, max(12.0, self.FR / 260.0))
        for mk in (self.wet, self.wet_far):
            for p in self.water + self.sea:
                mk.poly(p)
            for p in self.islands:
                mk.poly(p, 0)
            for w in self.waterways:
                if w["w"] >= mk.c:
                    mk.line(w["p"], w["w"] / 2)
        self.bmask = Mask(E, max(2.0, E / 450.0))
        for b in self.buildings:
            self.bmask.poly(b["p"])
        # lookups
        self.groad, self.grail, self.gbld = Grid(30.0), Grid(30.0), Grid(25.0)
        for r in self.roads:
            hw = r["w"] / 2
            for (x0, y0), (x1, y1) in zip(r["p"], r["p"][1:]):
                L = math.hypot(x1 - x0, y1 - y0)
                a = math.atan2(y1 - y0, x1 - x0)
                for k in range(int(L / 5) + 1):
                    f = min(k * 5 / max(L, 1e-6), 1.0)
                    self.groad.add(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, hw, a, r["foot"], r["id"]))
        for r in self.rails:
            for (x0, y0), (x1, y1) in zip(r["p"], r["p"][1:]):
                L = math.hypot(x1 - x0, y1 - y0)
                for k in range(int(L / 5) + 1):
                    f = min(k * 5 / max(L, 1e-6), 1.0)
                    self.grail.add(x0 + (x1 - x0) * f, y0 + (y1 - y0) * f, (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f))
        for b in self.buildings:
            p = b["p"]
            self.gbld.add(*centroid(p), centroid(p))
            for i in range(len(p)):
                (x0, y0), (x1, y1) = p[i], p[(i + 1) % len(p)]
                L = math.hypot(x1 - x0, y1 - y0)
                for k in range(int(L / 4) + 1):
                    f = min(k * 4 / max(L, 1e-6), 1.0)
                    q = (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
                    self.gbld.add(*q, q)
        # long drivable streets and running lines: traffic, trains, lamps, pavements
        self.drive = [r for r in chain([r for r in self.roads if not r["foot"] and r["k"] not in ("service", "track")]) if length(r["p"]) > 60]
        self.tracks = sorted(chain([r for r in self.rails if r["service"] == "main" and r["k"] == "rail"]), key=lambda r: -length(r["p"]))
        self.keep_out = []          # (x, y, r): nothing generated here (the landmark's own ground)
        cr = float(cfg("landmark.clear_radius_m", 0) or 0)
        if cr > 0:
            self.keep_out.append((0.0, 0.0, cr))

    def in_water(self, x, y):
        return bool(self.wet.get(x, y) if self.wet.covers(x, y) else self.wet_far.get(x, y))

    def in_building(self, x, y):
        return bool(self.bmask.get(x, y))

    def kept_out(self, x, y, m=0.0):
        return any((x - a) ** 2 + (y - b) ** 2 < (r + m) ** 2 for a, b, r in self.keep_out)

    def road_near(self, x, y, drive_only=False, skip=None):
        """(gap to the road's edge in metres, the road's direction) for the nearest road within about 45 m."""
        best = None
        for qx, qy, hw, a, foot, rid in self.groad.near(x, y):
            if (drive_only and foot) or rid == skip:
                continue
            g = math.hypot(x - qx, y - qy) - hw
            if best is None or g < best[0]:
                best = (g, a)
        return best

    def rail_dist(self, x, y):
        return min((math.hypot(x - qx, y - qy) for qx, qy in self.grail.near(x, y)), default=1e9)

    def bld_dist(self, x, y):
        return min((math.hypot(x - qx, y - qy) for qx, qy in self.gbld.near(x, y)), default=1e9)

    def in_area(self, x, y):
        for a in self.garea.d.get((int(x // 200), int(y // 200)), ()):
            bb = a["bb"]
            if bb[0] <= x <= bb[2] and bb[1] <= y <= bb[3] and inside(a["p"], x, y):
                return a["k"]
        return None

    def free(self, x, y, m=1.0):
        """Open, dry ground: not water, building, road, railway or the landmark's own plot."""
        if self.in_water(x, y) or self.in_building(x, y) or self.kept_out(x, y, m):
            return False
        r = self.road_near(x, y)
        return not (r and r[0] < m) and self.rail_dist(x, y) > 3.0 + m


# ---------------------------------------------------------------- buildings
class Blocks:
    """Many buildings as one mesh, with face attributes for the buildings material."""

    def __init__(self):
        self.v, self.f, self.col, self.roof, self.glass, self.rnd = [], [], [], [], [], []
        self.params = []          # one row per box, for the web viewer
        self.polys = []           # extruded footprints, for the web viewer

    def face(self, idx, col, roof, glass, rnd):
        self.f.append(idx)
        self.col.append(col)
        self.roof.append(roof)
        self.glass.append(glass)
        self.rnd.append(rnd)

    def box(self, cx, cy, w, d, h, rot, wall, roofc, glass=0.0, rnd=0.5, z0=0.0, pitch=0.0, top=True):
        self.params.append((cx, cy, z0, w, d, h, rot, pitch, 1.0 if top else 0.0, *wall, *roofc, glass, rnd))
        c, s = math.cos(rot), math.sin(rot)
        P = [(cx + x * c - y * s, cy + x * s + y * c) for x, y in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2))]
        b = len(self.v)
        self.v += [(x, y, z0) for x, y in P] + [(x, y, z0 + h) for x, y in P]
        for i in range(4):
            j = (i + 1) % 4
            self.face((b + i, b + j, b + 4 + j, b + 4 + i), wall, 0.0, glass, rnd)
        if pitch <= 0:
            if top:
                self.face((b + 4, b + 5, b + 6, b + 7), roofc, 1.0, 0.0, rnd)
            return
        L, D = (w, d) if w >= d else (d, w)                     # hipped roof: ridge along the longer side
        ridge = max(L - D, 0.0) / 2
        r1, r2 = ((-ridge, 0.0), (ridge, 0.0)) if w >= d else ((0.0, -ridge), (0.0, ridge))
        e = len(self.v)
        self.v += [(cx + x * c - y * s, cy + x * s + y * c, z0 + h + pitch * D) for x, y in (r1, r2)]
        t = [b + 4, b + 5, b + 6, b + 7]
        if w >= d:
            quads, tris = ((t[0], t[1], e + 1, e), (t[2], t[3], e, e + 1)), ((t[1], t[2], e + 1), (t[3], t[0], e))
        else:
            quads, tris = ((t[1], t[2], e + 1, e), (t[3], t[0], e, e + 1)), ((t[0], t[1], e), (t[2], t[3], e + 1))
        for q in quads + tris:
            self.face(q, roofc, 1.0, 0.0, rnd)

    def poly(self, pts, h, wall, roofc, glass=0.0, rnd=0.5, z0=0.0):
        """A footprint (counter-clockwise) extruded to a flat roof."""
        self.polys.append([round(h, 2), round(z0, 2), *[round(c, 3) for c in (*wall, *roofc)], glass, round(rnd, 3),
                           [round(c, 2) for q in pts for c in q]])
        n, b = len(pts), len(self.v)
        self.v += [(x, y, z0) for x, y in pts] + [(x, y, z0 + h) for x, y in pts]
        for i in range(n):
            j = (i + 1) % n
            self.face((b + i, b + j, b + n + j, b + n + i), wall, 0.0, glass, rnd)
        for t in tessellate_polygon([[Vector((x, y, 0.0)) for x, y in pts]]):
            (x0, y0), (x1, y1), (x2, y2) = (pts[k] for k in t)
            if (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0) < 0:
                t = t[::-1]
            self.face(tuple(b + n + k for k in t), roofc, 1.0, 0.0, rnd)

    def build(self, name, mat):
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.v, [], self.f)
        me.update()
        me.attributes.new("col", "FLOAT_COLOR", "FACE").data.foreach_set("color", [x for c in self.col for x in (*c, 1.0)])
        for nm, vals in (("roof", self.roof), ("glass", self.glass), ("rnd", self.rnd)):
            me.attributes.new(nm, "FLOAT", "FACE").data.foreach_set("value", vals)
        me.materials.append(mat)
        return pf.link_obj(bpy.data.objects.new(name, me))


def pick(rng, table):
    r = rng.random() * sum(w for _, w in table)
    for c, w in table:
        r -= w
        if r <= 0:
            return tuple(c)
    return tuple(table[-1][0])


def jitter(rng, c, k=0.08):
    f = 1 + rng.uniform(-k, k)
    return tuple(min(1.0, max(0.0, x * f + rng.uniform(-k, k) * 0.15)) for x in c)


def roof_clutter(B, rng, pts, h, wall, big):
    """What flat roofs carry: a stair room, plant, water tanks where the region uses them."""
    cx, cy = centroid(pts)
    xs, ys = [q[0] for q in pts], [q[1] for q in pts]
    spots = []
    for _ in range(12):
        x, y = rng.uniform(min(xs), max(xs)), rng.uniform(min(ys), max(ys))
        x, y = cx + (x - cx) * 0.7, cy + (y - cy) * 0.7
        if inside(pts, x, y) and all(inside(pts, x + dx, y + dy) for dx, dy in ((2.2, 2.2), (-2.2, 2.2), (2.2, -2.2), (-2.2, -2.2))):
            spots.append((x, y))
    rot = rng.uniform(0, math.pi)
    tanks = float(cfg("region.roof_tanks", 0.0))
    for x, y in spots[:(3 if big else 1)]:
        r = rng.random()
        if r < tanks:
            tc = rng.choice(((0.025, 0.025, 0.03), (0.025, 0.025, 0.03), (0.04, 0.12, 0.38), (0.6, 0.6, 0.58)))
            B.box(x, y, 1.3, 1.3, 1.5, rot + 0.7, tc, tc, 0.0, 0.01, z0=h + 0.4)
        elif r < tanks + 0.4 and h > 6:
            B.box(x, y, 3.2, 3.6, 2.8, rot, wall, (0.3, 0.3, 0.28), 0.0, 0.01, z0=h)
        elif big:
            B.box(x, y, 2.4, 1.6, 1.3, rot, (0.55, 0.56, 0.57), (0.5, 0.5, 0.5), 0.0, 0.01, z0=h)


def lot(B, rng, px, py, w, d, h, rot, wall, roofc, rnd, flat=True):
    """A generated building lot: the main block, often an annex one floor higher or lower, a parapet, roof clutter."""
    c, s_ = math.cos(rot), math.sin(rot)
    FL = float(cfg("region.floor_m", 3.2))
    if rng.random() < 0.4:
        aw, ad = w * rng.uniform(0.4, 0.65), d * rng.uniform(0.5, 0.8)
        ox, oy = rng.choice((-1, 1)) * (w / 2 + aw / 2 - 0.5), rng.uniform(-0.3, 0.3) * d
        B.box(px + ox * c - oy * s_, py + ox * s_ + oy * c, aw, ad, max(FL, h + rng.choice((-FL, -FL, FL))), rot, jitter(rng, wall, 0.12),
              jitter(rng, pick(rng, cfg("region.roofs_flat"))), 0.0, rnd)
    if not flat:
        B.box(px, py, w, d, h, rot, wall, roofc, 0.0, rnd, pitch=0.32)
        return
    B.box(px, py, w, d, h, rot, wall, roofc, 0.0, rnd)
    if rng.random() < 0.6:
        t = 0.25
        for ox, oy, sw, sd in ((0, d / 2 - t / 2, w, t), (0, -d / 2 + t / 2, w, t), (w / 2 - t / 2, 0, t, d), (-w / 2 + t / 2, 0, t, d)):
            B.box(px + ox * c - oy * s_, py + ox * s_ + oy * c, sw, sd, 0.9, rot, wall, wall, 0.0, 0.01, z0=h)
    P = [(px + x * c - y * s_, py + x * s_ + y * c) for x, y in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2))]
    roof_clutter(B, rng, P, h, wall, False)


def height_of(b, rng, ar):
    FL = float(cfg("region.floor_m", 3.2))
    if b.get("h"):
        return max(2.5, b["h"])
    if b.get("lv"):
        return max(2.5, b["lv"] * FL + (0.4 if b["lv"] > 1 else 0.0))
    k = b["k"]
    lo, hi = cfg("region.default_floors", [1, 4])
    if k in SHED:
        return rng.uniform(4.5, 9.0) if ar > 150 else rng.uniform(2.6, 4.0)
    if k in LOW:
        return FL * rng.choice((1, 1, 2)) + 0.3
    if k in ("church", "cathedral", "chapel", "mosque", "temple", "synagogue", "shrine"):
        return rng.uniform(9.0, 18.0)
    if k in ("apartments", "dormitory", "hotel", "office", "commercial", "hospital", "university", "civic", "government", "public"):
        return FL * rng.randint(max(2, lo + 1), max(3, hi + 3))
    if ar < 60:
        return FL * 1 + 0.3
    if ar < 250:
        return FL * rng.randint(lo, max(lo, hi - 1))
    return FL * rng.randint(max(1, lo), hi + (1 if ar > 900 else 0))


def osm_buildings(mp, B, rng):
    """Every mapped footprint, at its mapped height where the map knows it, in the region's colours otherwise."""
    walls, flat, pitched = cfg("region.walls"), cfg("region.roofs_flat"), cfg("region.roofs_pitched")
    share, gshare = float(cfg("region.pitched_share", 0.35)), float(cfg("region.glass_share", 0.5))
    names = [n.lower() for n in cfg("landmark.remove_names", [])]
    n = 0
    for b in mp.buildings:
        p = b["p"]
        cx, cy = centroid(p)
        if mp.kept_out(cx, cy) or (mp.keep_out and inside(p, 0.0, 0.0)) or (b.get("name", "").lower() in names and names):
            continue
        r = random.Random(int(cx * 7.31 + cy * 13.7) & 0xffffff)
        ar = abs(area(p))
        h = height_of(b, r, ar)
        z0 = min(float(b.get("minh", 0.0)), h - 1.0)
        wall = colour(b.get("col")) or jitter(r, pick(r, walls))
        rnd = r.uniform(0.06, 1.0)
        if b["k"] in SHED:
            rnd = 0.02
            wall = jitter(r, r.choice(((0.45, 0.47, 0.48), (0.36, 0.40, 0.44), (0.50, 0.46, 0.38), (0.30, 0.36, 0.40))))
        glass = 1.0 if (h > 38 and r.random() < gshare) or b.get("mat") == "glass" else 0.0
        ox, oy, w, d, rot = obb(p)
        boxy = ar / max(w * d, 1e-6) > 0.84 and len(p) <= 8
        shape = b.get("roof")
        want_pitch = shape in ("gabled", "hipped", "pyramidal", "half-hipped", "gambrel", "mansard", "saltbox") or \
            (shape is None and b["k"] not in SHED and h < 11 and ar < 380 and r.random() < share)
        if want_pitch and boxy and z0 == 0:
            B.box(ox, oy, w, d, h, rot, wall, colour(b.get("roofcol")) or jitter(r, pick(r, pitched)), 0.0, rnd, pitch=0.3 if min(w, d) < 14 else 0.18)
        else:
            roofc = colour(b.get("roofcol")) or jitter(r, pick(r, flat))
            if b["k"] in SHED:
                roofc = jitter(r, r.choice(((0.42, 0.44, 0.45), (0.30, 0.32, 0.34), (0.36, 0.22, 0.16))))
            B.poly(p, h - z0, wall, roofc, glass, rnd, z0=z0)
            if rnd > 0.05 and not glass and ar > 45 and not b.get("part"):
                roof_clutter(B, r, p, h, wall, ar > 500)
        n += 1
    return n


def infill(mp, B, trees, rng):
    """Streets the map shows without buildings (thinly mapped regions): lots along both sides, aligned to the street.
    A mapped building within 30 m switches it off for that spot, so well-mapped places are left exactly as mapped."""
    dens = cfg("infill.density", "auto")
    if dens in (0, "0", False, None):
        return 0
    dens = 0.75 if dens == "auto" else float(dens)
    lo, hi = cfg("infill.lot_m", [9, 16])
    flo, fhi = cfg("infill.floors", [1, 3])
    FL = float(cfg("region.floor_m", 3.2))
    walls, flat, pitched = cfg("region.walls"), cfg("region.roofs_flat"), cfg("region.roofs_pitched")
    share = float(cfg("region.pitched_share", 0.35))
    placed = Grid(20.0)
    n = 0
    for r in mp.roads:
        if r["foot"] or r["k"] in ("motorway", "motorway_link", "trunk_link", "track"):
            continue
        L, s = length(r["p"]), rng.uniform(4, 10)
        while s < L - 4:
            w, d = rng.uniform(lo, hi), rng.uniform(lo, hi)
            x, y, a = walk(r["p"], s)
            s += w + rng.uniform(1.0, 5.0)
            for side in (1, -1):
                if rng.random() > dens:
                    continue
                off = r["w"] / 2 + rng.uniform(2.5, 5.0) + d / 2
                px, py = x - math.sin(a) * off * side, y + math.cos(a) * off * side
                if px * px + py * py > mp.R ** 2 or mp.bld_dist(px, py) < 30.0 or not mp.free(px, py, 2.0):
                    continue
                if mp.in_area(px, py) in ("park", "grass", "forest", "pitch", "parking", "railyard", "sand", "scrub", "plaza", "farm", "pool", "wetland"):
                    continue
                corners = [(px + cx * math.cos(a) - cy * math.sin(a), py + cx * math.sin(a) + cy * math.cos(a))
                           for cx, cy in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2))]
                if any(not mp.free(cx, cy, 0.5) for cx, cy in corners):
                    continue
                if any(math.hypot(px - qx, py - qy) < (max(w, d) + qs) * 0.62 for qx, qy, qs in placed.near(px, py)):
                    continue
                placed.add(px, py, (px, py, max(w, d)))
                tile = rng.random() < share
                lot(B, rng, px, py, w, d, FL * rng.randint(flo, fhi) + 0.3, a, jitter(rng, pick(rng, walls)),
                    jitter(rng, pick(rng, pitched if tile else flat)), rng.uniform(0.06, 1.0), flat=not tile)
                n += 1
                if rng.random() < 0.3 * float(cfg("region.tree_density", 1.0)):
                    tx, ty = px - math.sin(a) * (d / 2 + 3) * side, py + math.cos(a) * (d / 2 + 3) * side
                    if mp.free(tx, ty, 1.0):
                        trees.append(tree_at(rng, tx, ty))
    return n


def far_city(mp, B, trees, rng):
    """Beyond the detailed radius, out to far_radius_m: blocks and tree clumps thinning with distance, kept off the
    water, shaped by the far ring's land use where the map has it. This is what the horizon is made of."""
    urban, tk = float(cfg("far.urban", 0.65)), float(cfg("far.trees", 0.5)) * float(cfg("region.tree_density", 1.0))
    if mp.FR <= mp.R * 1.05 or urban <= 0:
        return 0
    FL = float(cfg("region.floor_m", 3.2))
    walls, flat, pitched = cfg("region.walls"), cfg("region.roofs_flat"), cfg("region.roofs_pitched")
    share = float(cfg("region.pitched_share", 0.35))
    lo, hi = cfg("region.default_floors", [1, 4])
    use_lu = mp.has_far and any(a["far"] and a["k"] in ("residential", "commercial", "industrial") for a in mp.areas)
    n = 0
    ring = mp.R
    while ring < mp.FR:
        cell = 26.0 + 60.0 * (ring - mp.R) / max(mp.FR - mp.R, 1.0)
        circ = 2 * math.pi * (ring + cell / 2)
        for k in range(int(circ / cell)):
            a = 2 * math.pi * k / int(circ / cell) + ring * 0.01
            rr = ring + cell * rng.uniform(0.15, 0.85)
            x, y = rr * math.cos(a) + rng.uniform(-0.3, 0.3) * cell, rr * math.sin(a) + rng.uniform(-0.3, 0.3) * cell
            if x * x + y * y < (mp.R * 0.97) ** 2 and mp.bld_dist(x, y) < 40:
                continue
            if mp.in_water(x, y) or mp.in_water(x + cell * 0.4, y) or mp.in_water(x, y + cell * 0.4) or mp.in_water(x - cell * 0.4, y - cell * 0.4):
                continue
            lu = mp.in_area(x, y)
            if lu in ("forest", "park", "scrub", "wetland"):
                for _ in range(3 if lu == "forest" else 1):
                    trees.append(tree_at(rng, x + rng.uniform(-0.4, 0.4) * cell, y + rng.uniform(-0.4, 0.4) * cell, 1.25))
                continue
            if lu in ("grass", "pitch", "farm", "sand", "railyard", "parking", "pier"):
                continue
            p_build = urban if not use_lu else (0.9 if lu in ("residential", "commercial", "industrial") else urban * 0.35)
            if rng.random() < p_build:
                w, d = cell * rng.uniform(0.38, 0.75), cell * rng.uniform(0.38, 0.75)
                tall = rng.random() < 0.03
                h = FL * (rng.randint(hi + 2, hi + 12) if tall else rng.randint(lo, hi)) + 0.3
                tile = (not tall) and rng.random() < share
                wallc = jitter(rng, pick(rng, walls))
                if lu == "industrial":
                    B.box(x, y, w * 1.3, d * 1.3, rng.uniform(6, 11), rng.uniform(0, math.pi), jitter(rng, (0.42, 0.44, 0.46)), jitter(rng, (0.4, 0.42, 0.43)), 0.0, 0.02)
                else:
                    B.box(x, y, w, d, h, rng.uniform(0, math.pi), wallc, jitter(rng, pick(rng, pitched if tile else flat)),
                          1.0 if tall and rng.random() < 0.5 else 0.0, rng.uniform(0.06, 1.0), pitch=0.3 if tile else 0.0)
                n += 1
            if rng.random() < 0.55 * tk:
                trees.append(tree_at(rng, x + rng.uniform(-0.5, 0.5) * cell, y + rng.uniform(-0.5, 0.5) * cell, 1.2))
        ring += cell
    return n


# ---------------------------------------------------------------- trees and lamps
KINDS = ["broad", "round", "tall", "palm", "conifer"]


def tree_at(rng, x, y, k=1.0):
    w = cfg("region.trees")
    r = rng.random() * (sum(w.get(n, 0.0) for n in KINDS) or 1.0)
    kind = 0
    for i, nme in enumerate(KINDS):
        r -= w.get(nme, 0.0)
        if r <= 0:
            kind = i
            break
    return (x, y, 0.0, k * rng.uniform(0.75, 1.3), kind, rng.uniform(0, 6.283))


def place_trees(mp, rng):
    """Mapped trees first, then woods, parks and street trees where the map says there is green."""
    tk = float(cfg("region.tree_density", 1.0))
    trees = [tree_at(rng, x, y) for x, y in mp.trees if not mp.in_building(x, y) and not mp.kept_out(x, y)]
    per = {"forest": 55.0, "park": 420.0, "scrub": 160.0, "residential": 1400.0, "wetland": 300.0}
    for a in mp.areas:
        if a["k"] not in per or a["far"]:
            continue
        bb = a["bb"]
        n = min(5000, int((bb[2] - bb[0]) * (bb[3] - bb[1]) / per[a["k"]] * tk))
        for _ in range(n):
            x, y = rng.uniform(bb[0], bb[2]), rng.uniform(bb[1], bb[3])
            if x * x + y * y < (mp.R * 1.05) ** 2 and inside(a["p"], x, y) and mp.free(x, y, 1.5):
                trees.append(tree_at(rng, x, y, 0.55 if a["k"] == "scrub" else 1.0))
    for r in mp.drive:
        if r["k"] in ("motorway", "trunk"):
            continue
        L, s = length(r["p"]), rng.uniform(8, 30)
        while s < L - 6:
            x, y, a = walk(r["p"], s)
            s += rng.uniform(16, 40)
            if rng.random() > 0.3 * tk:
                continue
            side = rng.choice((1, -1))
            off = r["w"] / 2 + 2.6
            tx, ty = x - math.sin(a) * off * side, y + math.cos(a) * off * side
            if tx * tx + ty * ty < mp.R ** 2 and mp.free(tx, ty, 1.2):
                trees.append(tree_at(rng, tx, ty, 0.8))
    return trees


def tree_protos():
    """Tree shapes in a collection left out of the view layer; the scatter instances them. Names sort in KINDS order."""
    coll = pf.collection("tree_protos")
    leaves, cards, bark = look.mat_leaves(), look.mat_leaf_cards(), pf.simple_mat("bark", (0.10, 0.08, 0.06), 0.9)
    dark = look.mat_leaves("needles", [(0.0, (0.020, 0.055, 0.025)), (0.5, (0.030, 0.075, 0.030)), (1.0, (0.045, 0.095, 0.035))])
    for name, cz, spread, flat, nb, rad in (("p0_broad", 7.0, 5.5, 0.55, 20, 3.4), ("p1_round", 5.0, 3.0, 0.85, 14, 2.5), ("p2_tall", 8.0, 2.2, 1.35, 14, 2.2)):
        rng = random.Random(sum(map(ord, name)))
        bm = bmesh.new()
        uvl = bm.loops.layers.uv.new("UVMap")
        r = bmesh.ops.create_cone(bm, cap_ends=False, segments=6, radius1=0.35, radius2=0.22, depth=cz, matrix=Matrix.Translation((0, 0, cz / 2)))
        for f in {f for v in r["verts"] for f in v.link_faces}:
            f.material_index = 1
        for k in range(nb):
            c = Vector((rng.gauss(0, spread * 0.45), rng.gauss(0, spread * 0.45), cz + rng.gauss(0, 1.2) * flat))
            rr = rad * rng.uniform(0.6, 1.0)
            ico = bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0, matrix=Matrix.Translation(c))
            for v in ico["verts"]:
                nrm = (v.co - c).normalized()
                disp = (1 + 0.30 * noise.noise(v.co * 0.45 + Vector((k, 0, 0))) + 0.16 * noise.noise(v.co * 1.6 + Vector((0, k, 0))) + 0.07 * noise.noise(v.co * 4.0))
                v.co = c + Vector((nrm.x * rr, nrm.y * rr, nrm.z * rr * flat)) * disp * 0.9
            for q in range(200):                                # leaf sprays standing off the clump
                th, cz2 = rng.uniform(0, 6.283), rng.uniform(-0.55, 1.0)
                sr = math.sqrt(max(0.0, 1 - cz2 * cz2))
                dv = Vector((math.cos(th) * sr, math.sin(th) * sr, cz2))
                o_ = c + Vector((dv.x * rr, dv.y * rr, dv.z * rr * flat)) * rng.uniform(0.86, 1.12)
                nrm = (dv + Vector((rng.uniform(-0.6, 0.6), rng.uniform(-0.6, 0.6), rng.uniform(-0.2, 0.7)))).normalized()
                t1 = nrm.cross(Vector((0, 0, 1)))
                t1 = t1.normalized() if t1.length > 1e-3 else Vector((1, 0, 0))
                t2 = nrm.cross(t1)
                a_, sz = rng.uniform(0, 6.283), rng.uniform(0.55, 1.05)
                u = (t1 * math.cos(a_) + t2 * math.sin(a_)) * sz
                w = nrm.cross(u).normalized() * sz * 0.8
                f = bm.faces.new([bm.verts.new(o_ - u - w), bm.verts.new(o_ + u - w), bm.verts.new(o_ + u + w), bm.verts.new(o_ - u + w)])
                f.material_index = 2
                for loop, uvc in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
                    loop[uvl].uv = uvc
        pf.mesh_obj(name, bm, [leaves, bark, cards], coll=coll)
    bm = bmesh.new()                                            # palm
    pts = [Vector((0.6 * math.sin(i / 10 * 1.2) * i / 10, 0, 13.0 * i / 10)) for i in range(11)]
    for a, b in zip(pts, pts[1:]):
        r = bmesh.ops.create_cone(bm, cap_ends=False, segments=6, radius1=0.24, radius2=0.2, depth=(b - a).length,
                                  matrix=Matrix.Translation((a + b) / 2) @ (b - a).to_track_quat("Z", "Y").to_matrix().to_4x4())
        for f in {f for v in r["verts"] for f in v.link_faces}:
            f.material_index = 1
    rng = random.Random(77)
    for k in range(14):
        az, up, L = 2 * math.pi * k / 14 + rng.uniform(-0.15, 0.15), rng.uniform(0.2, 0.9), rng.uniform(4.0, 5.5)
        prev = None
        for i in range(9):
            t = i / 8
            dv = Vector((math.cos(az) * L * t, math.sin(az) * L * t, (up * t - 1.4 * t * t) * L * 0.45))
            side = Vector((-math.sin(az), math.cos(az), 0)) * 0.55 * math.sin(math.pi * min(t * 1.1, 1.0)) + Vector((0, 0, 0.001))
            a_, b_ = bm.verts.new(pts[-1] + dv - side), bm.verts.new(pts[-1] + dv + side)
            if prev:
                bm.faces.new((prev[0], prev[1], b_, a_))
            prev = (a_, b_)
    pf.mesh_obj("p3_palm", bm, [leaves, bark], coll=coll)
    bm = bmesh.new()                                            # conifer: stacked, drooping skirts
    r = bmesh.ops.create_cone(bm, cap_ends=False, segments=6, radius1=0.3, radius2=0.08, depth=14.0, matrix=Matrix.Translation((0, 0, 7.0)))
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = 1
    rng = random.Random(5)
    for i in range(9):
        z, rr = 2.2 + i * 1.35, 3.3 * (1 - i / 9.5)
        seg = 11
        ring0 = [bm.verts.new((rr * rng.uniform(0.82, 1.1) * math.cos(2 * math.pi * k / seg + i), rr * rng.uniform(0.82, 1.1) * math.sin(2 * math.pi * k / seg + i), z - 0.5)) for k in range(seg)]
        top = bm.verts.new((0, 0, z + 2.0))
        for k in range(seg):
            bm.faces.new((ring0[k], ring0[(k + 1) % seg], top))
    pf.mesh_obj("p4_conifer", bm, [dark, bark], coll=coll)
    bpy.context.view_layer.layer_collection.children[coll.name].exclude = True
    return coll


def scatter(name, pts, coll):
    """Instance the collection's children on points: (x, y, z, scale, kind index, rotation about Z)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(p[0], p[1], p[2]) for p in pts], [], [])
    me.attributes.new("scl", "FLOAT", "POINT").data.foreach_set("value", [p[3] for p in pts])
    me.attributes.new("kind", "INT", "POINT").data.foreach_set("value", [int(p[4]) for p in pts])
    me.attributes.new("rot", "FLOAT", "POINT").data.foreach_set("value", [p[5] for p in pts])
    o = pf.link_obj(bpy.data.objects.new(name, me))
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    gi, go = ng.nodes.new("NodeGroupInput"), ng.nodes.new("NodeGroupOutput")
    iop, ci = ng.nodes.new("GeometryNodeInstanceOnPoints"), ng.nodes.new("GeometryNodeCollectionInfo")
    ci.inputs["Collection"].default_value = coll
    ci.inputs["Separate Children"].default_value = True
    ci.inputs["Reset Children"].default_value = True

    def named(n, t):
        a = ng.nodes.new("GeometryNodeInputNamedAttribute")
        a.data_type = t
        a.inputs["Name"].default_value = n
        return a.outputs["Attribute"]

    cz = ng.nodes.new("ShaderNodeCombineXYZ")
    ng.links.new(named("rot", "FLOAT"), cz.inputs["Z"])
    try:
        e2r = ng.nodes.new("FunctionNodeEulerToRotation")
        ng.links.new(cz.outputs[0], e2r.inputs[0])
        rot_out = e2r.outputs[0]
    except Exception:
        rot_out = cz.outputs[0]
    ng.links.new(gi.outputs[0], iop.inputs["Points"])
    ng.links.new(ci.outputs[0], iop.inputs["Instance"])
    iop.inputs["Pick Instance"].default_value = True
    ng.links.new(named("kind", "INT"), iop.inputs["Instance Index"])
    ng.links.new(rot_out, iop.inputs["Rotation"])
    ng.links.new(named("scl", "FLOAT"), iop.inputs["Scale"])
    ng.links.new(iop.outputs[0], go.inputs[0])
    o.modifiers.new("scatter", "NODES").node_group = ng
    return o


def street_lamps(mp, rng):
    """Lamp posts: the mapped ones, and along main streets where the map has none. Lit at night."""
    if not cfg("life.street_lamps", True):
        return []
    pts = [(q["x"], q["y"], 0.0, 1.0, 0, rng.uniform(0, 6.283)) for q in mp.points if q["k"] == "lamp"]
    if len(pts) < 20:
        for r in mp.drive:
            if r["k"] not in BIG and r["k"] != "residential":
                continue
            gap = 32.0 if r["k"] in BIG else 45.0
            L, s, side = length(r["p"]), 6.0, 1
            while s < L - 4:
                x, y, a = walk(r["p"], s)
                off = r["w"] / 2 + 0.7
                lx, ly = x - math.sin(a) * off * side, y + math.cos(a) * off * side
                if lx * lx + ly * ly < mp.R ** 2 and not mp.in_water(lx, ly) and not mp.in_building(lx, ly):
                    pts.append((lx, ly, 0.0, 1.0, 0, a - math.pi / 2 * side))
                s += gap
                side = -side
    if not pts:
        return []
    night = pf.tod() == "night"
    coll = pf.collection("lamp_protos")
    bm = bmesh.new()
    pf.beam(bm, (0, 0, 0), (0, 0, 8.0), 0.14, mat=0)
    pf.beam(bm, (0, 0, 7.9), (1.6, 0, 8.3), 0.09, mat=0)
    pf.cube(bm, (1.7, 0, 8.25), (0.7, 0.28, 0.1), mat=1)
    head = pf.emit_mat("lamp_head", (1.0, 0.78, 0.5), 60.0) if night else pf.simple_mat("lamp_head", (0.85, 0.85, 0.8), 0.3)
    pf.mesh_obj("lamp", bm, [pf.simple_mat("lamp_post", (0.22, 0.23, 0.24), 0.5, 0.6), head], coll=coll)
    bpy.context.view_layer.layer_collection.children[coll.name].exclude = True
    scatter("street_lamps", pts, coll)
    if night:
        near = sorted(pts, key=lambda p: p[0] ** 2 + p[1] ** 2)[:int(pf.arg("lamps", 900))]
        lc = pf.collection("lamp_lights")
        ld = bpy.data.lights.new("lamp_light", "POINT")
        ld.energy, ld.color, ld.shadow_soft_size = 900.0, (1.0, 0.76, 0.48), 0.25
        for x, y, _, _, _, a in near:
            o = bpy.data.objects.new("ll", ld)
            o.location = (x + math.cos(a) * 1.7, y + math.sin(a) * 1.7, 8.0)
            lc.objects.link(o)
    return pts


# ---------------------------------------------------------------- ground, water, roads, railways
def ground(mp):
    R = max(mp.FR * 6.0, 30000.0)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=R)
    pf.mesh_obj("ground", bm, [look.mat_ground(mp.R, mp.FR)])
    lake = look.mat_water("water", tuple(cfg("region.water")), 0.05, 2.0)
    sea = look.mat_water("sea", tuple(cfg("region.sea")), 0.12, 0.6)
    if mp.water or mp.waterways:
        bm = bmesh.new()
        for p in mp.water:
            pf.fill(bm, p, 0.10)
        for w in mp.waterways:
            pf.ribbon(bm, thin(w["p"], 4.0), w["w"] / 2, 0.09)
        pf.mesh_obj("water", bm, [lake])
    if mp.sea:
        bm = bmesh.new()
        for p in mp.sea:
            pf.fill(bm, p, 0.10)
        pf.mesh_obj("sea", bm, [sea])
    if mp.islands:
        bm = bmesh.new()
        for p in mp.islands:
            pf.fill(bm, p, 0.13)
        pf.mesh_obj("islands", bm, [pf.tex_mat("island_ground", "leafy_grass", 3.5, (0.55, 0.95, 0.40), (0.10, 0.15, 0.05))])
    shore = cfg("region.shore", "soft")
    bm = bmesh.new()
    for p in mp.water + mp.sea:
        n = len(p)
        for i in range(n):
            (x0, y0), (x1, y1) = p[i], p[(i + 1) % n]
            if max(x0 * x0 + y0 * y0, x1 * x1 + y1 * y1) > (mp.R * 1.1) ** 2 or math.hypot(x1 - x0, y1 - y0) < 0.3:
                continue
            if shore == "wall":
                pf.wall(bm, [(x0, y0), (x1, y1)], 0.0, 0.0, 1.0)
            else:                                               # a damp margin just outside the waterline
                L = math.hypot(x1 - x0, y1 - y0)
                nx, ny = -(y1 - y0) / L, (x1 - x0) / L
                if mp.in_water((x0 + x1) / 2 + nx * 2.5, (y0 + y1) / 2 + ny * 2.5):
                    nx, ny = -nx, -ny
                pf.ribbon(bm, [(x0 + nx * 1.4, y0 + ny * 1.4), (x1 + nx * 1.4, y1 + ny * 1.4)], 1.6, 0.02, ext=True)
    if len(bm.faces):
        pf.mesh_obj("shore", bm, [look.mat_embankment() if shore == "wall" else pf.simple_mat("shore_mud", (0.11, 0.10, 0.075), 0.55, bump=0.2)])
    else:
        bm.free()


def wet_runs(mp, p, step=5.0):
    """Stretches of a polyline that cross water: [(start, end distance along it)]."""
    L, s, runs, a = length(p), 0.0, [], None
    while s <= L:
        x, y, _ = walk(p, s)
        if mp.in_water(x, y):
            a = s if a is None else a
        elif a is not None:
            runs.append((a, s))
            a = None
        s += step
    if a is not None:
        runs.append((a, L))
    return [(max(0.0, a - 4.0), min(L, b + 4.0)) for a, b in runs if b - a >= step]


def sub(p, a, b, step=4.0):
    out, s = [], a
    while s < b:
        out.append(walk(p, s)[:2])
        s += step
    out.append(walk(p, b)[:2])
    return out


def surfaces(mp):
    """Streets, footpaths, pavements, lane lines, bridges over water, railways, parks, pitches, car parks, plazas."""
    asphalt = pf.tex_mat("asphalt", "asphalt_02", 5.0, (0.62, 0.62, 0.64), (0.05, 0.05, 0.055))
    paint = pf.simple_mat("road_paint", (0.55, 0.55, 0.52), 0.7)
    paver = pf.tex_mat("paver", "interlocking_concrete_pavers", 2.4, (0.95, 0.92, 0.88), (0.34, 0.31, 0.27))
    concrete = pf.simple_mat("bridge_concrete", (0.48, 0.47, 0.44), 0.85, bump=0.15)
    bm, bridges = bmesh.new(), []
    for r in mp.roads:
        pf.ribbon(bm, r["p"], r["w"] / 2, 0.045 if r["foot"] else 0.06 + 0.002 * (r["id"] % 5), 2 if r["foot"] else 0)
        if r["w"] >= 3.0 or r["foot"]:
            for a, b in wet_runs(mp, r["p"]):
                bridges.append((1 if r["foot"] else 0, r["w"], sub(r["p"], a, b)))
    for r in mp.drive:
        L = length(r["p"])
        if r["w"] >= 6.5:                                       # dashed centre line
            k = 2.0
            while k < L - 4:
                x0, y0, a = walk(r["p"], k)
                pf.ribbon(bm, [(x0, y0), (x0 + 3 * math.cos(a), y0 + 3 * math.sin(a))], 0.08, 0.08, 1, ext=False)
                k += 10.0
        if r["k"] in ("motorway", "motorway_link", "trunk"):
            continue
        for side in (1, -1):                                    # pavements, broken where another street joins
            off, k = side * (r["w"] / 2 + 1.05), 0.0
            while k < L:
                x0, y0, a = walk(r["p"], k)
                x1, y1, _ = walk(r["p"], min(k + 4.0, L))
                mx, my = (x0 + x1) / 2 - math.sin(a) * off, (y0 + y1) / 2 + math.cos(a) * off
                k += 4.0
                if mx * mx + my * my > (mp.R * 1.05) ** 2 or mp.in_water(mx, my) or mp.in_building(mx, my):
                    continue
                if any(math.hypot(mx - qx, my - qy) < hw + 1.2 and not foot and mp.roads[rid]["key"] != r["key"]
                       for qx, qy, hw, _, foot, rid in mp.groad.near(mx, my)):
                    continue
                pf.ribbon(bm, [(x0, y0), (x1, y1)], 1.0, 0.15, 2, off=off, ext=False)
                pf.wall(bm, [(x0, y0), (x1, y1)], off - side * 1.0, 0.05, 0.15, 3)
    pf.mesh_obj("roads", bm, [asphalt, paint, paver, pf.simple_mat("kerb", (0.5, 0.5, 0.47), 0.8)])
    if mp.rails:
        ballast = pf.tex_mat("ballast", "gravel_stones", 2.0, (0.80, 0.72, 0.64), (0.23, 0.20, 0.17), bump=0.6)
        bm = bmesh.new()
        total = sum(length(r["p"]) for r in mp.rails)
        for r in mp.rails:
            tram = r["k"] in ("tram", "light_rail")
            g = 0.7175 if not tram else 0.7175
            if not tram:
                pf.ribbon(bm, r["p"], 2.5, 0.04, 0)
                pf.ribbon(bm, r["p"], 1.7, 0.12, 0)
            for sd in (-g, g):
                pf.ribbon(bm, r["p"], 0.075, 0.19 if not tram else 0.07, 1, off=sd)
                pf.ribbon(bm, r["p"], 0.036, 0.30 if not tram else 0.085, 3, off=sd)
            if not tram and total < 25000:
                L, k = length(r["p"]), 0.3
                while k < L:
                    x, y, a = walk(r["p"], k)
                    if x * x + y * y < (mp.R * 0.8) ** 2:
                        ca, sa = math.cos(a) * 0.125, math.sin(a) * 0.125
                        pf.ribbon(bm, [(x - ca, y - sa), (x + ca, y + sa)], 1.3, 0.165, 2, ext=False)
                    k += 0.65
            for a, b in wet_runs(mp, r["p"]):
                bridges.append((2, 4.4, sub(r["p"], a, b)))
        pf.mesh_obj("rails", bm, [ballast, pf.simple_mat("rail", (0.10, 0.08, 0.07), 0.5, 0.6), pf.simple_mat("sleeper", (0.40, 0.39, 0.36), 0.9),
                                  pf.simple_mat("rail_head", (0.45, 0.44, 0.42), 0.25, 0.9)])
    if bridges:
        bm = bmesh.new()
        for kind, w, run in bridges:
            hw = w / 2
            if kind == 2:
                pf.ribbon(bm, run, hw, 0.14, 3)
                for sd in (1, -1):
                    pf.wall(bm, run, sd * hw, 0.0, 0.85, 3)
            else:
                pf.ribbon(bm, run, hw + 0.5, 0.15, 0)
                pf.ribbon(bm, run, hw, 0.165, 2 if kind else 1)
                for sd in (1, -1):
                    pf.wall(bm, run, sd * (hw + 0.5), 0.0, 1.05, 0)
                    pf.wall(bm, run, sd * (hw + 0.3), 0.165, 1.05, 0)
                    pf.ribbon(bm, run, 0.1, 1.05, 0, off=sd * (hw + 0.4))
        pf.mesh_obj("bridges", bm, [concrete, asphalt, paver, pf.simple_mat("girder", (0.10, 0.11, 0.12), 0.6, 0.5)])
    mp.bridges = bridges
    grass = pf.tex_mat("grass", "leafy_grass", 3.5, (0.55, 0.95, 0.40), (0.09, 0.16, 0.03), bump=0.5, vary=0.18)
    mats = [grass, paver, pf.simple_mat("court", (0.04, 0.17, 0.26), 0.6), look.mat_water("pool", (0.04, 0.22, 0.30), 0.05, 0.3),
            pf.tex_mat("sand", "sand_01", 3.0, (1.0, 0.95, 0.85), (0.55, 0.47, 0.33), bump=0.3), asphalt,
            pf.simple_mat("woodland_floor", (0.05, 0.075, 0.025), 0.9, bump=0.3), pf.simple_mat("farmland", (0.20, 0.19, 0.09), 0.9, bump=0.2)]
    idx = {"park": 0, "grass": 0, "pitch": 0, "plaza": 1, "pier": 1, "pool": 3, "sand": 4, "parking": 5, "forest": 6, "scrub": 6, "wetland": 6, "farm": 7}
    bm = bmesh.new()
    for a in mp.areas:
        if a["k"] not in idx:
            continue
        mat = idx[a["k"]]
        if a["k"] == "pitch" and a.get("sport") in ("tennis", "basketball", "multi", "netball", "volleyball"):
            mat = 2
        pf.fill(bm, thin(a["p"], 8.0) if a["far"] else a["p"], (0.1 if mat == 3 else 0.035 if mat != 6 else 0.02) - (0.012 if a["far"] else 0.0), mat)
    if len(bm.faces):
        pf.mesh_obj("areas", bm, mats)
    else:
        bm.free()


def build(seed=1, keep_out=()):
    """The whole place except the landmark. keep_out: [(x, y, r)] discs the landmark claims. Returns (map, blocks, trees)."""
    path = os.path.join(pf.PROJECT, "map", "osm.json")
    if not os.path.exists(path):
        raise SystemExit("pf: no map yet. Run: pf map %s" % pf.PROJECT)
    rng = random.Random(seed)
    mp = Map(path)
    mp.keep_out += [tuple(k) for k in keep_out]
    pf.log("map: %d buildings, %d roads, %d rails, %d water, sea %d, radius %.0f m, far %.0f m (%s)" % (
        len(mp.buildings), len(mp.roads), len(mp.rails), len(mp.water), len(mp.sea), mp.R, mp.FR, "mapped" if mp.has_far else "procedural"))
    ground(mp)
    surfaces(mp)
    B = Blocks()
    n = osm_buildings(mp, B, rng)
    trees = place_trees(mp, rng)
    ni = infill(mp, B, trees, rng)
    nf = far_city(mp, B, trees, rng)
    pf.log("buildings: %d mapped, %d infill, %d far; trees %d" % (n, ni, nf, len(trees)))
    if n < 30 and ni == 0:
        pf.log("WARNING: almost nothing is mapped here and infill is off; set infill.density in place.json")
    return mp, B, trees


def finish(mp, B, trees, rng):
    """After the landmark has claimed its ground: drop trees it displaced, then make the big meshes."""
    trees = [t for t in trees if not mp.kept_out(t[0], t[1], 2.0)]
    B.build("city", look.mat_buildings())
    if trees:
        scatter("trees", trees, tree_protos())
    mp.lamps = street_lamps(mp, rng)
    return trees

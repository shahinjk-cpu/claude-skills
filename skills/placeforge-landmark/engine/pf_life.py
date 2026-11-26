"""placeforge engine, life: traffic on the real streets, parked cars, people walking, trains on the running lines,
a helicopter circling the landmark.

Recognisable things are never hand-built boxes: they are downloaded models (assets/assets.json, fetched by
`pf assets`). No model file, no object: the scene stays empty of that kind rather than showing a placeholder.

Every mover's place is a pure function of film time, so frames can render in any order on any machine, and the
Three.js viewer replays exactly the same motion (export() hands it the same lanes, speeds and offsets):
    vehicles keep to their side of the road (region.drive), one speed per lane, looping along the street;
    walkers slide along footways and pavements while their mesh steps through poses baked from the walk action;
    the helicopter flies a banked circle, main and tail rotor each turning about its own hub.
"""
import bpy, bmesh, colorsys, json, math, os, random
from array import array
from mathutils import Vector, Matrix
import pf_core as pf
import pf_city as city
from pf_core import cfg

POSES = 6
# paint jobs for cars: (hue shift, saturation x, value x). Neutral parts (bumpers, glass, lamps) barely move.
PAINTS = [(0.0, 1.0, 1.0), (0.0, 0.06, 1.45), (0.0, 0.08, 0.32), (0.0, 0.05, 0.85), (0.42, 0.9, 0.75), (0.58, 1.0, 0.9), (0.80, 0.7, 0.6)]
_NOT_BODY = ("glass", "window", "light", "lamp", "tire", "tyre", "wheel", "rim", "hub", "trim", "black", "grey", "gray", "display")


def load_model(path, name, coll, yaw=90.0, length=None, height=None, action=None, frame=None, only=None, skip=None):
    """Import a GLB as one mesh object in the engine's convention: +X forward, +Z up, metres, origin on the ground
    under the whole model's middle. action / frame pose a rigged model before it is flattened. only / skip pick
    parts by name (a rotor apart from its body); the whole model still sets scale and origin, so parts line up."""
    before = set(bpy.data.objects)
    acts_before = set(bpy.data.actions)
    try:
        bpy.ops.import_scene.gltf(filepath=path)
    except Exception as e:
        pf.log("model import failed:", os.path.basename(path), e)
        return None
    new = [o for o in bpy.data.objects if o not in before]
    if action:
        for o in new:
            if o.type == "ARMATURE":
                act = next((a for a in bpy.data.actions if a not in acts_before and action.lower() in a.name.lower()), None)       # this model's own clip
                if act:
                    if not o.animation_data:
                        o.animation_data_create()
                    o.animation_data.action = act
                    if (frame or 1) <= 1:
                        pf.log("pose clip:", os.path.basename(path), act.name.split("|")[-1])
                    try:
                        o.animation_data.action_slot = act.slots[0]
                    except Exception:
                        pass
        bpy.context.scene.frame_set(int(frame or 1))
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    parts, mats = [], []
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    for o in new:
        nm = o.name.lower()
        if o.type != "MESH" or nm.startswith("icosphere"):      # the importer's bone-shape helper
            continue
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        me.transform(o.matrix_world)
        for v in me.vertices:
            lo, hi = Vector(map(min, lo, v.co)), Vector(map(max, hi, v.co))
        if (only and not any(k in nm for k in only)) or (skip and any(k in nm for k in skip)):
            bpy.data.meshes.remove(me)
            continue
        idx = []
        for m in me.materials:
            if m not in mats:
                mats.append(m)
            idx.append(mats.index(m))
        parts.append((me, [idx[p.material_index] if idx else 0 for p in me.polygons]))
    if not parts:
        for o in new:
            bpy.data.objects.remove(o, do_unlink=True)
        return None
    bm = bmesh.new()
    for me, _ in parts:
        bm.from_mesh(me)
    out = bpy.data.meshes.new(name)
    bm.to_mesh(out)
    bm.free()
    k = 0
    for me, mi in parts:
        for i in mi:
            out.polygons[k].material_index = i
            k += 1
    size = hi - lo
    sc = height / max(size.z, 1e-6) if height else (length / max(size.x, size.y, 1e-6) if length else 1.0)
    ctr = (lo + hi) / 2
    out.transform(Matrix.Rotation(math.radians(yaw), 4, "Z") @ Matrix.Scale(sc, 4) @ Matrix.Translation((-ctr.x, -ctr.y, -lo.z)))
    for m in mats:
        out.materials.append(m)
    for me, _ in parts:
        bpy.data.meshes.remove(me)
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    ob = bpy.data.objects.new(name, out)
    coll.objects.link(ob)
    return ob


# ---------------------------------------------------------------- colour: paint jobs, and colours for the viewer
def _principled(m):
    return next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if m and m.node_tree else None


def _hsv(c, hsv):
    h, s, v = colorsys.rgb_to_hsv(*[max(0.0, min(1.0, x)) for x in c[:3]])
    return colorsys.hsv_to_rgb((h + hsv[0]) % 1.0, min(1.0, s * hsv[1]), min(1.0, v * hsv[2]))


def body_slots(me):
    """Which material slots are the paintwork: a textured '*body*' material, else the largest coloured one."""
    area = {}
    for p in me.polygons:
        area[p.material_index] = area.get(p.material_index, 0.0) + p.area
    best = None
    for i, m in enumerate(me.materials):
        pr = _principled(m)
        if not pr:
            continue
        nm = m.name.lower()
        bc = pr.inputs["Base Color"]
        if bc.links and "body" in nm:
            return [i]
        if bc.links or any(k in nm for k in _NOT_BODY):
            continue
        h, s, v = colorsys.rgb_to_hsv(*bc.default_value[:3])
        if s > 0.18 and v > 0.08 and (best is None or area.get(i, 0) > best[0]):
            best = (area.get(i, 0), i)
    return [best[1]] if best else []


_PAINTED = {}


def painted(m, hsv):
    """A copy of a material with its colour shifted (hue), drained (saturation) or darkened (value)."""
    key = (m.name, hsv)
    if key in _PAINTED:
        return _PAINTED[key]
    c = m.copy()
    pr = _principled(c)
    bc = pr.inputs["Base Color"]
    if bc.links:
        src = bc.links[0].from_socket
        n = c.node_tree.nodes.new("ShaderNodeHueSaturation")
        n.inputs["Hue"].default_value = (0.5 + hsv[0]) % 1.0
        n.inputs["Saturation"].default_value = hsv[1]
        n.inputs["Value"].default_value = hsv[2]
        c.node_tree.links.new(src, n.inputs["Color"])
        c.node_tree.links.new(n.outputs[0], bc)
        c["pf_hsv"] = list(hsv)
    else:
        bc.default_value = (*_hsv(bc.default_value, hsv), 1.0)
    _PAINTED[key] = c
    return c


def paint_variants(me, rng, n):
    """The same car in several colours (mesh copies sharing everything but the paint material)."""
    slots = body_slots(me)
    out = [me]
    if not slots:
        return out
    for hsv in rng.sample(PAINTS[1:], min(n - 1, len(PAINTS) - 1)):
        c = me.copy()
        for i in slots:
            c.materials[i] = painted(me.materials[i], hsv)
        out.append(c)
    return out


_IMG = {}


def _texel(img, u, v):
    import numpy as np
    if img.name not in _IMG:
        w, h = img.size
        a = np.empty(w * h * 4, dtype=np.float32)
        try:
            img.pixels.foreach_get(a)
            _IMG[img.name] = (a.reshape(h, w, 4), w, h)
        except Exception:
            _IMG[img.name] = (None, 0, 0)
    a, w, h = _IMG[img.name]
    if a is None or not w:
        return (0.5, 0.5, 0.5)
    px = a[int((v % 1.0) * (h - 1)), int((u % 1.0) * (w - 1))]
    return (float(px[0]), float(px[1]), float(px[2]))


def soup(me, target):
    """A mesh as triangles for the web viewer: position 3, normal 3, colour 3 per vertex. Decimated to about
    `target` triangles (hundreds of full-detail cars would sink the frame rate); texture colours are baked per face."""
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    ob = bpy.data.objects.new("pf_tmp", me)
    bpy.context.scene.collection.objects.link(ob)
    if tris > target * 1.15:
        md = ob.modifiers.new("d", "DECIMATE")
        md.ratio = max(0.02, target / float(tris))
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    em = ev.to_mesh()
    em.calc_loop_triangles()
    uv = em.uv_layers.active.data if em.uv_layers.active else None
    info = []
    for m in em.materials:
        pr = _principled(m)
        tex, col = None, (0.5, 0.5, 0.5)
        if pr:
            bc = pr.inputs["Base Color"]
            node = bc.links[0].from_node if bc.links else None
            if node and node.type == "HUE_SAT" and node.inputs["Color"].links:
                node = node.inputs["Color"].links[0].from_node
            if node and node.type == "TEX_IMAGE" and node.image:
                tex = node.image
            elif not bc.links:
                col = tuple(bc.default_value[:3])
        info.append((tex, col, tuple(m["pf_hsv"]) if m and "pf_hsv" in m else None))
    out = array("f")
    vs = em.vertices
    for t in em.loop_triangles:
        tex, col, hsv = info[t.material_index] if t.material_index < len(info) else (None, (0.5, 0.5, 0.5), None)
        if tex and uv:
            u = sum(uv[l].uv[0] for l in t.loops) / 3.0
            v = sum(uv[l].uv[1] for l in t.loops) / 3.0
            col = _texel(tex, u, v)
            if hsv:
                col = _hsv(col, hsv)
        for k in range(3):
            co = vs[t.vertices[k]].co
            n = t.split_normals[k] if t.use_smooth else t.normal
            out.extend((co[0], co[1], co[2], n[0], n[1], n[2], col[0], col[1], col[2]))
    ev.to_mesh_clear()
    bpy.data.objects.remove(ob, do_unlink=True)
    return out


def hub_of(me):
    """Where a rotor turns: the middle of its hub material's faces (blades make the bounding box lopsided)."""
    pts = [me.vertices[i].co for p in me.polygons if p.material_index < len(me.materials) and me.materials[p.material_index]
           and "hub" in me.materials[p.material_index].name.lower() for i in p.vertices]
    if not pts:
        pts = [v.co for v in me.vertices]
    lo = Vector((min(p[i] for p in pts) for i in range(3)))
    hi = Vector((max(p[i] for p in pts) for i in range(3)))
    return (lo + hi) / 2


# ---------------------------------------------------------------- the moving scene
class Life:
    def __init__(self):
        self.protos, self.roles = [], []          # mesh datas and their roles, by index (cars, bus, loco, coach)
        self.people = []                           # per person model: POSES mesh datas
        self.lanes, self.paths, self.tracks = [], [], []     # polylines: vehicles, walkers, trains
        self.cars, self.parked, self.walkers, self.trains = [], [], [], []
        self.heli = None
        self.lamps_live = []                       # (point light, car index): head-lamp pools at night

    def car_xy(self, c, t):
        _, pi, li, s0, v, off, z = c
        p, L = self.lanes[li]
        x, y, a = city.walk(p, (s0 + v * t) % L)
        return x - math.sin(a) * off, y + math.cos(a) * off, a

    def update(self, f, t):
        for c in self.cars:
            x, y, a = self.car_xy(c, t)
            c[0].location, c[0].rotation_euler = (x, y, c[6]), (0, 0, a)
        for lo, ci in self.lamps_live:
            x, y, a = self.car_xy(self.cars[ci], t)
            lo.location = (x + math.cos(a) * 3.2, y + math.sin(a) * 3.2, 0.7)
        for o, mi, pi, s0, v, off, ph in self.walkers:
            p, L = self.paths[pi]
            s = (s0 + abs(v) * t) % L
            x, y, a = city.walk(p, s if v > 0 else L - s)
            o.location = (x - math.sin(a) * off, y + math.cos(a) * off, 0.16)
            o.rotation_euler = (0, 0, a if v > 0 else a + math.pi)
            o.data = self.people[mi][int((t * 1.9 + ph) * POSES) % POSES]
        for o, pi, ti, s0, v in self.trains:
            p, L = self.tracks[ti]
            x, y, a = city.walk(p, (s0 + v * t) % L)
            o.location, o.rotation_euler = (x, y, 0.30), (0, 0, a)
        h = self.heli
        if h:
            ang = h["a0"] - h["w"] * t                     # clockwise seen from above
            h["root"].location = (h["cx"] + h["r"] * math.sin(ang), h["cy"] + h["r"] * math.cos(ang), h["z"] + 2.5 * math.sin(t * 0.6))
            h["root"].rotation_euler = (math.radians(h["bank"]), math.radians(-3.0), -ang)
            h["main"].rotation_euler = (0, 0, t * 2 * math.pi * h["rps"])
            h["tail"].rotation_euler = tuple(t * 2 * math.pi * h["tail_rps"] if i == h["tail_axis"] else 0.0 for i in range(3))

    def export(self):
        """Everything the Three.js viewer needs to replay the same life: light meshes and the motion's numbers."""
        d = {"poses": POSES, "protos": [], "people": [], "heli": None}
        tgt = {"car": 1100, "van": 1300, "bus": 2200, "loco": 2600, "coach": 2200}
        for me, role in zip(self.protos, self.roles):
            d["protos"].append({"role": role, "soup": soup(me, tgt.get(role, 1200))})
        for poses in self.people:
            d["people"].append([soup(me, 4000) for me in poses])       # people are not decimated: a low-poly figure falls apart
        r3 = lambda p: [round(v, 2) for q in p for v in q]
        d["lanes"], d["paths"], d["tracks"] = [r3(p) for p, _ in self.lanes], [r3(p) for p, _ in self.paths], [r3(p) for p, _ in self.tracks]
        d["cars"] = [v for c in self.cars for v in (c[1], c[2], c[3], c[4], c[5], c[6])]
        d["parked"] = [v for c in self.parked for v in c]
        d["walkers"] = [v for w in self.walkers for v in (w[1], w[2], w[3], w[4], w[5], w[6])]
        d["trains"] = [v for tr in self.trains for v in (tr[1], tr[2], tr[3], tr[4])]
        h = self.heli
        if h:
            d["heli"] = {k: h[k] for k in ("cx", "cy", "r", "z", "a0", "w", "bank", "rps", "tail_rps", "tail_axis")}
            d["heli"].update(main_hub=list(h["main"].location), tail_hub=list(h["tail"].location),
                             soups=[soup(h["body"].data, 4200), soup(h["main"].data, 500), soup(h["tail"].data, 200)])
        return d


def build(mp, rng, H=60.0):
    p = os.path.join(pf.PROJECT, "assets", "assets.json")
    if not os.path.exists(p):
        pf.log("life: no assets/assets.json (pf assets): no vehicles, people or helicopter")
        return None
    spec = json.load(open(p)).get("models", {})
    mdir = os.path.join(pf.PROJECT, "assets", "models")
    have = {k: m for k, m in spec.items() if os.path.exists(os.path.join(mdir, m["file"]))}
    if not have:
        pf.log("life: no model files yet (pf assets): no vehicles, people or helicopter")
        return None
    kv, kp = float(cfg("life.vehicles", 0.6)), float(cfg("life.people", 0.5))
    night = pf.tod() == "night"
    protos = pf.collection("life_protos")
    coll = pf.collection("life")
    L_ = Life()
    by_role = {}
    for k, m in sorted(have.items()):
        path = os.path.join(mdir, m["file"])
        role = m["role"]
        if role == "person":
            poses = []
            for i in range(POSES):
                o = load_model(path, "life_p_%s_%d" % (k, i), protos, m.get("yaw", 90), height=m.get("height", 1.7), action=m.get("action", "walk"), frame=1 + i * 4)
                if o:
                    poses.append(o.data)
            if len(poses) == POSES:
                L_.people.append(poses)
        elif role == "helicopter":
            by_role["helicopter"] = (path, m)
        else:
            o = load_model(path, "life_m_" + k, protos, m.get("yaw", 90), length=m.get("length"))
            if not o:
                continue
            for me in (paint_variants(o.data, rng, 4) if role in ("car", "van") else [o.data]):
                by_role.setdefault(role, []).append(len(L_.protos))
                L_.protos.append(me)
                L_.roles.append(role)
    if night:                                           # head and tail lamps glow on every model that names them
        seen = set()
        for me in L_.protos:
            for m in me.materials:
                if m and m.name not in seen:
                    seen.add(m.name)
                    nm = m.name.lower()
                    if "headlight" in nm or "light_butter" in nm or "head_l" in nm:
                        pf.add_emission(m, (1.0, 0.9, 0.7), 6.0)
                    elif "taillight" in nm or "tail_l" in nm:
                        pf.add_emission(m, (1.0, 0.08, 0.04), 2.5)
    side = -1.0 if cfg("region.drive", "right") == "right" else 1.0       # offset to the left of travel is positive
    cars = by_role.get("car", []) + by_role.get("van", [])
    if cars and kv > 0:
        for r in mp.drive:
            Lr = city.length(r["p"])
            if Lr < 80 or r["w"] < 5:
                continue
            big = r["k"] in city.BIG
            lanes = [(r["p"], side * r["w"] / 4 if not r["oneway"] else 0.0)]
            if not r["oneway"]:
                lanes.append((r["p"][::-1], side * r["w"] / 4))
            for path, off in lanes:
                li = len(L_.lanes)
                L_.lanes.append((path, Lr))
                v = rng.uniform(9, 13) if big else rng.uniform(5, 8)
                s = rng.uniform(0, 40)
                while s < Lr - 10 and len(L_.cars) < 1800:
                    x, y, _ = city.walk(path, s)
                    if x * x + y * y < (mp.R * 1.05) ** 2 and rng.random() < kv:
                        pi = rng.choice(by_role["bus"]) if (big and by_role.get("bus") and rng.random() < 0.07) else rng.choice(cars)
                        o = bpy.data.objects.new("life_car", L_.protos[pi])
                        coll.objects.link(o)
                        L_.cars.append([o, pi, li, s, v, off, 0.07])
                    s += rng.uniform(14, 50) / max(kv, 0.1) * (0.6 if big else 1.0)
        for a in mp.areas:                                        # parked cars
            if a["k"] != "parking" or a["far"]:
                continue
            cx, cy, w, d, rot = city.obb(a["p"])
            c, s_ = math.cos(rot), math.sin(rot)
            u = -w / 2 + 2.0
            while u < w / 2 - 1.5 and len(L_.parked) < 800:
                for vrow in ([-d / 2 + 3.0, d / 2 - 3.0] if d > 12 else [0.0]):
                    x, y = cx + u * c - vrow * s_, cy + u * s_ + vrow * c
                    if rng.random() < 0.6 and city.inside(a["p"], x, y) and not mp.in_building(x, y):
                        pi = rng.choice(cars)
                        o = bpy.data.objects.new("life_parked", L_.protos[pi])
                        ra = rot + math.pi / 2 + (math.pi if rng.random() < 0.5 else 0)
                        o.location, o.rotation_euler = (x, y, 0.04), (0, 0, ra)
                        coll.objects.link(o)
                        L_.parked.append((pi, round(x, 2), round(y, 2), round(ra, 3)))
                u += 2.7
        if night:                                               # a pool of light ahead of the nearest moving cars
            ld = bpy.data.lights.new("car_light", "POINT")
            ld.energy, ld.color, ld.shadow_soft_size = 260.0, (1.0, 0.93, 0.8), 0.3
            lc = pf.collection("life_lights")
            order = sorted(range(len(L_.cars)), key=lambda i: sum(v * v for v in L_.car_xy(L_.cars[i], 0.0)[:2]))[:int(pf.arg("carlights", 220))]
            for ci in order:
                o = bpy.data.objects.new("ll_car", ld)
                lc.objects.link(o)
                L_.lamps_live.append((o, ci))
    if L_.people and kp > 0:
        near = min(mp.R, 600.0)
        paths = [(r["p"], 0.0) for r in mp.roads if r["foot"] and city.length(r["p"]) > 25]
        paths += [(r["p"], sd * (r["w"] / 2 + 1.05)) for r in mp.drive if r["k"] not in ("motorway", "trunk") for sd in (1, -1)]
        for path, off in paths:
            Lp, s = city.length(path), rng.uniform(0, 30)
            pi = None
            while s < Lp - 2 and len(L_.walkers) < 900:
                x, y, a = city.walk(path, s)
                px, py = x - math.sin(a) * off, y + math.cos(a) * off
                if px * px + py * py < near * near and rng.random() < kp and not mp.in_water(px, py) and not mp.in_building(px, py):
                    if pi is None:
                        pi = len(L_.paths)
                        L_.paths.append((path, Lp))
                    mi = rng.randrange(len(L_.people))
                    o = bpy.data.objects.new("life_walker", L_.people[mi][0])
                    coll.objects.link(o)
                    L_.walkers.append((o, mi, pi, s, rng.choice((1, -1)) * rng.uniform(1.1, 1.5), off + rng.uniform(-0.5, 0.5), rng.random()))
                s += rng.uniform(12, 45) / max(kp, 0.1)
    if by_role.get("loco") and by_role.get("coach"):
        for tr in mp.tracks[:4:2]:
            Lt = city.length(tr["p"])
            if Lt < 300:
                continue
            ti = len(L_.tracks)
            L_.tracks.append((tr["p"], Lt))
            s0 = rng.uniform(0, Lt)
            for k in range(6):
                pi = by_role["loco"][0] if k == 0 else by_role["coach"][0]
                o = bpy.data.objects.new("life_train", L_.protos[pi])
                coll.objects.link(o)
                L_.trains.append((o, pi, ti, s0 - k * 20.4, 11.0))
    if by_role.get("helicopter") and int(cfg("life.helicopter", 1)) > 0:
        path, m = by_role["helicopter"]
        rot, tail = m.get("rotor", "main_rotor"), m.get("tail_rotor", "tail_rotor")
        a = dict(yaw=m.get("yaw", 90), length=m.get("length", 9.5))
        body = load_model(path, "life_heli_body", coll, skip=(rot, tail), **a)
        main = load_model(path, "life_heli_rotor", coll, only=(rot,), **a)
        tl = load_model(path, "life_heli_tail", coll, only=(tail,), **a)
        if body and main and tl:
            root = bpy.data.objects.new("life_heli", None)
            coll.objects.link(root)
            for o in (main, tl):                                # each rotor turns about its own hub
                hub = hub_of(o.data)
                o.data.transform(Matrix.Translation(-hub))
                o.location = hub
            dims = [max(v.co[i] for v in tl.data.vertices) - min(v.co[i] for v in tl.data.vertices) for i in range(3)]
            for o in (body, main, tl):
                o.parent = root
            r = float(cfg("life.heli_radius", 0) or max(0.9 * H + 110.0, 200.0))
            z = float(cfg("life.heli_height", 0) or max(0.6 * H, 80.0))
            L_.heli = {"root": root, "body": body, "main": main, "tail": tl, "cx": 0.0, "cy": 0.0, "r": r, "z": z,
                       "a0": math.radians(float(cfg("life.heli_bearing", 140))), "w": 30.0 / r, "bank": 9.0, "rps": 6.3, "tail_rps": 27.0,
                       "tail_axis": dims.index(min(dims))}
    L_.update(1, 0.0)
    pf.log("life: %d vehicles moving, %d parked, %d people, %d train cars, helicopter %s (models: %s)" % (
        len(L_.cars), len(L_.parked), len(L_.walkers), len(L_.trains), "yes" if L_.heli else "no", ", ".join(sorted(have))))
    return L_

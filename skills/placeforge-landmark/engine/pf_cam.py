"""placeforge engine, cameras: the camera matched to the reference photo, named look-dev views, and film shots.

Views (view=<name>):
    photo    the reference photo's camera (place.json "camera", written by tools/camera_match.py)
    hero, wide, close, top, street    made from the landmark's height and the map when nothing else is given
    anything in place.json "views": {"name": {"from": [x, y, z], "to": [x, y, z], "lens": 35}}

Film (anim=1): <project>/film/shots.json, a list of shots, each {"name", "seconds", "tod", "move", ...}:
    {"move": "orbit",   "target": [x, y, z], "radius": [r0, r1], "height": [h0, h1], "bearing": [b0, b1], "lens": 35}
    {"move": "dolly",   "from": [..], "to": [..], "look_from": [..], "look_to": [..], "lens": [l0, l1]}
    {"move": "topdown", "height": [h0, h1], "turn": [deg0, deg1], "lens": 24}
    {"move": "photo",   "push": 0.15}      (starts on the photo camera's viewpoint, pushes in)
"""
import bpy, json, math, os
from mathutils import Vector, Matrix
import pf_core as pf
from pf_core import cfg, arg


def photo_pose():
    """(location, bearing, lens mm, shift_y, aspect) of the reference photo's camera, or None."""
    c = cfg("camera") or {}
    if not c.get("distance_m"):
        return None
    b = math.radians(c.get("bearing_deg", 0.0))
    f, r = Vector((math.sin(b), math.cos(b), 0.0)), Vector((math.cos(b), -math.sin(b), 0.0))
    loc = -f * c["distance_m"] - r * c.get("offset_right_m", 0.0) + Vector((0, 0, c.get("height_m", 1.7)))
    W, H = float(c.get("ref_w", 1920)), float(c.get("ref_h", 1080))
    F = float(c.get("focal_px", W * 0.78))
    return loc, c.get("bearing_deg", 0.0), 36.0 * F / W, (float(c.get("horizon_row", H / 2)) - H / 2) / W, W / H


def views(mp, H):
    """Named cameras as {"from", "to", "lens"}; place.json "views" override or add to the automatic ones."""
    H = max(H, 12.0)
    v = {"hero": {"from": [-(1.6 * H + 70) * 0.5, -(1.6 * H + 70) * 0.87, 0.42 * H + 12], "to": [0, 0, 0.5 * H], "lens": 32},
         "wide": {"from": [-(3.0 * H + 250) * 0.6, -(3.0 * H + 250) * 0.8, 0.8 * H + 60], "to": [0, 0, 0.4 * H], "lens": 26},
         "close": {"from": [-(1.6 * H + 70) * 0.5, -(1.6 * H + 70) * 0.87, 0.42 * H + 12], "to": [0, 0, 0.82 * H], "lens": 135},
         "top": {"from": [0, -1, max(2.2 * H, 320.0)], "to": [0, 0, 0], "lens": 28}}
    best = None                                   # street: standing by the nearest proper street, looking at the landmark
    for r in mp.drive:
        for x, y in r["p"]:
            d = math.hypot(x, y)
            if 0.5 * H + 30 < d < 1.5 * H + 220 and (best is None or d < best[0]) and not mp.in_water(x, y):
                best = (d, x, y, r["w"])
    if best:
        _, x, y, w = best
        k = (w / 2 + 1.2) / max(math.hypot(x, y), 1.0)
        v["street"] = {"from": [x * (1 + k), y * (1 + k), 1.7], "to": [0, 0, 0.45 * H], "lens": 22}
    for name, d in (cfg("views") or {}).items():
        v[name] = d
    return v


def aim(o, loc, look):
    d = Vector(look) - Vector(loc)
    o.location = loc
    if d.length < 1e-6:
        return
    if abs(d.normalized().z) < 0.98:
        o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    else:                                         # straight down: picture-up = north
        o.rotation_euler = (0.0, 0.0, 0.0)


def camera(sc, mp, H):
    c = bpy.data.cameras.new("cam")
    c.sensor_fit = "HORIZONTAL"
    c.sensor_width = 36.0
    c.clip_start, c.clip_end = 0.5, 200000
    o = pf.link_obj(bpy.data.objects.new("cam", c))
    sc.camera = o
    name = arg("view")
    pose = photo_pose()
    vs = views(mp, H)
    if name is None:
        name = "photo" if pose else "hero"
    if name == "photo":
        if not pose:
            raise SystemExit("pf: view=photo needs place.json \"camera\" (run: pf camera ...). Views here: %s" % ", ".join(vs))
        loc, b, lens, shift, aspect = pose
        o.location, c.lens, c.shift_y = loc, lens, shift
        o.rotation_euler = (math.radians(90), 0, -math.radians(b))
        if not arg("h"):
            sc.render.resolution_y = int(round(sc.render.resolution_x / aspect / 2) * 2)
    elif name in vs:
        v = vs[name]
        c.lens = float(v.get("lens", 35))
        aim(o, v["from"], v["to"])
    else:
        raise SystemExit("pf: no view '%s'. Views here: %s" % (name, ", ".join(["photo"] * bool(pose) + list(vs))))
    pf.log("view:", name, "lens %.0f mm" % c.lens, "at", tuple(round(x, 1) for x in o.location))
    return o


# ---------------------------------------------------------------- film
def load_shots():
    p = os.path.join(pf.PROJECT, "film", "shots.json")
    if not os.path.exists(p):
        raise SystemExit("pf: no film plan. Run: pf film plan %s --seconds 30" % pf.PROJECT)
    fps = int(cfg("film.fps", 24))
    shots, f = [], 1
    for s in json.load(open(p))["shots"]:
        n = max(2, int(round(float(s["seconds"]) * fps)))
        shots.append(dict(s, a=f, b=f + n - 1))
        f += n
    return shots, fps


def ease(t):
    """Half linear, half smoothstep: slow in, slow out, never a dead stop."""
    t = min(max(t, 0.0), 1.0)
    return 0.5 * t + 0.5 * t * t * (3 - 2 * t)


def _pair(v, t):
    if isinstance(v, (list, tuple)) and len(v) == 2 and not isinstance(v[0], (list, tuple)):
        return v[0] + (v[1] - v[0]) * t
    return float(v)


def shot_pose(s, f):
    """Frame -> (location, look-at point, lens mm) for one shot."""
    t = ease((f - s["a"]) / max(s["b"] - s["a"], 1))
    mv = s.get("move", "orbit")
    if mv == "dolly":
        loc = Vector(s["from"]).lerp(Vector(s["to"]), t)
        look = Vector(s["look_from"]).lerp(Vector(s.get("look_to", s["look_from"])), t)
        return loc, look, _pair(s.get("lens", 30), t)
    if mv == "topdown":
        th = math.radians(_pair(s.get("turn", [0, 30]), t))
        h = _pair(s.get("height", [500, 400]), t)
        tg = Vector(s.get("target", [0, 0, 0]))
        return tg + Vector((0.06 * h * math.sin(th), -0.06 * h * math.cos(th), h)), tg, _pair(s.get("lens", 24), t)
    if mv == "photo":
        pose = photo_pose()
        if pose:
            loc, b, lens, _, _ = pose
            fwd = pf.bearing_vec(b)
            look0 = loc + fwd * 1000.0
            tg = Vector(s.get("target", [0, 0, loc.z]))
            k = float(s.get("push", 0.15)) * t
            return loc.lerp(tg, k), look0.lerp(tg, 0.5 + 0.5 * t), lens * (1 + 0.1 * t)
    tg = Vector(s.get("target", [0, 0, 0]))                    # orbit
    b = math.radians(_pair(s.get("bearing", [200, 250]), t))
    r, h = _pair(s.get("radius", [300, 260]), t), _pair(s.get("height", [120, 140]), t)
    return Vector((tg.x + r * math.sin(b), tg.y + r * math.cos(b), h)), tg, _pair(s.get("lens", 35), t)


def animate(sc, o, shots, fps):
    c = o.data
    c.shift_y = 0.0
    o.rotation_mode = "QUATERNION"
    sc.render.fps = fps
    sc.frame_start, sc.frame_end = 1, shots[-1]["b"]
    prev = None
    poses = {}
    for s in shots:
        for f in range(s["a"], s["b"] + 1):
            loc, look, lens = shot_pose(s, f)
            d = look - loc
            q = d.to_track_quat("-Z", "Y") if abs(d.normalized().z) < 0.98 else Matrix.Rotation(math.atan2(-d.x, d.y), 4, "Z").to_quaternion()
            if prev is not None and prev.dot(q) < 0:
                q.negate()
            prev = q.copy()
            poses[f] = (loc.copy(), q, lens)
    return poses


def set_frame(o, poses, f):
    loc, q, lens = poses[f]
    o.location, o.rotation_quaternion, o.data.lens = loc, q, lens

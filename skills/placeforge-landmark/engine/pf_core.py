"""placeforge engine, core: arguments, the place's config, shader-node and mesh helpers.

World convention (every module and every landmark.py uses it):
    metres, +X east, +Y north, +Z up, the map pin (place.json lat / lon) at the origin, ground at z = 0.
    A compass bearing b (0 = north, 90 = east) is the direction (sin b, cos b).
"""
import bpy, bmesh, json, math, os, sys
from mathutils import Vector, Matrix

ENGINE = os.path.dirname(os.path.abspath(__file__))

DEFAULTS = {
    "name": "Place", "radius_m": 800, "far_radius_m": "auto",
    "landmark": {"script": "landmark.py", "height_m": 0, "clear_radius_m": 0, "remove_names": []},
    "camera": {},                       # the matched photo camera (tools/camera_match.py writes it)
    "views": {},                        # extra look-dev cameras: {"name": {"from": [x, y, z], "to": [x, y, z], "lens": 35}}
    "time": {"tod": "day",
             "day": {"sun_elevation": 48, "sun_bearing": 150},
             "sunset": {"sun_elevation": 3.5, "sun_bearing": 262},
             "night": {"sun_elevation": 40, "sun_bearing": 120}},
    "look": {"exposure": {"day": 0.4, "sunset": -0.4, "night": 1.0}, "agx": "punchy", "saturation": 1.08, "contrast": 5.0,
             "sky": "physical", "sky_stops": [[0.0, [0.46, 0.60, 0.66]], [0.05, [0.16, 0.45, 0.70]], [0.25, [0.05, 0.30, 0.66]], [1.0, [0.02, 0.15, 0.48]]],
             "sky_camera": 0.85, "sky_light": 0.5, "sun_strength": {"day": 6.0, "sunset": 4.0, "night": 0.05},
             "haze": {"day": 0.00005, "sunset": 0.000045, "night": 0.0}, "haze_top_m": 800,
             "clouds": 0.35, "cloud_shadows": False, "aerosol": 0.5},
    "region": {"drive": "right", "floor_m": 3.2, "default_floors": [1, 4], "weathering": 0.6,
               "walls": [[[0.47, 0.45, 0.40], 30], [[0.50, 0.44, 0.35], 14], [[0.40, 0.39, 0.36], 16], [[0.53, 0.48, 0.40], 12],
                         [[0.60, 0.58, 0.54], 12], [[0.42, 0.33, 0.27], 8], [[0.36, 0.40, 0.42], 8]],
               "roofs_flat": [[[0.26, 0.25, 0.23], 34], [[0.34, 0.33, 0.30], 22], [[0.46, 0.46, 0.44], 6], [[0.18, 0.19, 0.20], 16]],
               "roofs_pitched": [[[0.30, 0.10, 0.05], 50], [[0.26, 0.09, 0.05], 25], [[0.36, 0.16, 0.09], 15], [[0.16, 0.16, 0.17], 10]],
               "pitched_share": 0.35, "glass_share": 0.5, "roof_tanks": 0.0,
               "trees": {"broad": 0.45, "round": 0.3, "tall": 0.15, "palm": 0.0, "conifer": 0.1}, "tree_density": 1.0,
               "water": [0.02, 0.07, 0.07], "sea": [0.01, 0.05, 0.075], "wind_bearing": 240},
    "infill": {"density": "auto", "lot_m": [9, 16], "floors": [1, 3]},
    "far": {"urban": 0.65, "trees": 0.5},
    "life": {"vehicles": 0.6, "people": 0.5, "street_lamps": True, "helicopter": 1, "heli_bearing": 140, "heli_radius": 0, "heli_height": 0},
    "render": {"w": 1920, "h": 1080, "samples": 256, "noise": 0.012, "preview_pct": 50, "preview_samples": 64},
    "film": {"fps": 24},
}


def _args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    return dict(x.split("=", 1) for x in a if "=" in x)


ARGS = _args()
CFG = {}
PROJECT = ""
TIMED = []          # (socket, f(t seconds)): shader values the film sets every frame


def arg(name, default=None):
    return ARGS.get(name, default)


def _merge(a, b):
    out = dict(a)
    for k, v in b.items():
        out[k] = _merge(a[k], v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return out


def _coerce(s):
    try:
        return json.loads(s)
    except (ValueError, TypeError):
        return s


def init(project):
    """Load <project>/place.json over the defaults; any dotted key=value argument overrides it for this run
    (look.exposure.day=0.6, region.pitched_share=0.1): the loop tunes with arguments, then writes winners to place.json."""
    global CFG, PROJECT
    PROJECT = os.path.abspath(project)
    CFG = _merge(DEFAULTS, json.load(open(os.path.join(PROJECT, "place.json"))))
    for k, v in ARGS.items():
        if "." in k:
            d = CFG
            parts = k.split(".")
            for p in parts[:-1]:
                d = d.setdefault(p, {})
                if not isinstance(d, dict):
                    break
            else:
                d[parts[-1]] = _coerce(v)
    return CFG


def cfg(path, default=None):
    d = CFG
    for p in path.split("."):
        if not isinstance(d, dict) or p not in d:
            return default
        d = d[p]
    return d


def tod():
    return arg("tod") or cfg("time.tod", "day")


def by_tod(path, default=None):
    """A config value that may be one number or {"day": .., "sunset": .., "night": ..}."""
    v = cfg(path, default)
    return v.get(tod(), default) if isinstance(v, dict) else v


def bearing_vec(b, length=1.0):
    r = math.radians(b)
    return Vector((math.sin(r) * length, math.cos(r) * length, 0.0))


def sun_dir():
    """Unit vector toward the sun (or the moon at night)."""
    e = math.radians(float(arg("sun_el", cfg("time.%s.sun_elevation" % tod(), 45))))
    b = math.radians(float(arg("sun_bearing", cfg("time.%s.sun_bearing" % tod(), 150))))
    return Vector((math.sin(b) * math.cos(e), math.cos(b) * math.cos(e), math.sin(e)))


# ---------------------------------------------------------------- shader nodes
def nd(nt, kind, inputs=None, **props):
    n = nt.nodes.new(kind)
    for k, v in props.items():
        setattr(n, k, v)
    for k, v in (inputs or {}).items():
        put(nt, n.inputs[k], v)
    return n


def put(nt, sock, x):
    if isinstance(x, (int, float, tuple, list)):
        sock.default_value = x
    else:
        nt.links.new(x, sock)


def M(nt, op, a, b=None, clamp=False):
    n = nt.nodes.new("ShaderNodeMath")
    n.operation = op
    n.use_clamp = clamp
    put(nt, n.inputs[0], a)
    if b is not None:
        put(nt, n.inputs[1], b)
    return n.outputs[0]


def VM(nt, op, a, b=None, out=0):
    n = nt.nodes.new("ShaderNodeVectorMath")
    n.operation = op
    put(nt, n.inputs[0], a)
    if b is not None:
        put(nt, n.inputs[1], b)
    return n.outputs[out]


def mix(nt, fac, a, b, mode="MIX"):
    n = nt.nodes.new("ShaderNodeMixRGB")
    n.blend_type = mode
    put(nt, n.inputs[0], fac)
    put(nt, n.inputs[1], a)
    put(nt, n.inputs[2], b)
    return n.outputs[0]


def sep(nt, v):
    n = nt.nodes.new("ShaderNodeSeparateXYZ")
    put(nt, n.inputs[0], v)
    return n.outputs


def comb(nt, x, y, z):
    n = nt.nodes.new("ShaderNodeCombineXYZ")
    for i, c in enumerate((x, y, z)):
        put(nt, n.inputs[i], c)
    return n.outputs[0]


def noise_t(nt, vec, scale, detail=4.0, rough=0.5, dist=0.0, out="Fac"):
    n = nt.nodes.new("ShaderNodeTexNoise")
    put(nt, n.inputs["Vector"], vec)
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    n.inputs["Distortion"].default_value = dist
    return n.outputs[out]


def noise4(nt, vec, scale, detail, rough, speed, dist=0.0):
    """A noise that drifts in time during a film (W = speed x seconds)."""
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.noise_dimensions = "4D"
    put(nt, n.inputs["Vector"], vec)
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = detail
    n.inputs["Roughness"].default_value = rough
    n.inputs["Distortion"].default_value = dist
    TIMED.append((n.inputs["W"], lambda t, k=speed: k * t))
    return n.outputs["Fac"]


def time_value(nt, f=lambda t: t):
    """A Value node the film drives: f(seconds) every frame (blinking lights, colour cycles)."""
    v = nt.nodes.new("ShaderNodeValue")
    TIMED.append((v.outputs[0], f))
    return v.outputs[0]


def ramp(nt, fac, stops):
    n = nt.nodes.new("ShaderNodeValToRGB")
    e = n.color_ramp.elements
    e[0].position, e[0].color = stops[0][0], (*stops[0][1], 1)
    e[1].position, e[1].color = stops[-1][0], (*stops[-1][1], 1)
    for p, c in stops[1:-1]:
        k = e.new(p)
        k.color = (*c, 1)
    put(nt, n.inputs[0], fac)
    return n.outputs[0]


def maprange(nt, v, a, b, c=0.0, d=1.0, clamp=True):
    n = nt.nodes.new("ShaderNodeMapRange")
    n.clamp = clamp
    put(nt, n.inputs["Value"], v)
    n.inputs["From Min"].default_value = a
    n.inputs["From Max"].default_value = b
    n.inputs["To Min"].default_value = c
    n.inputs["To Max"].default_value = d
    return n.outputs[0]


def geo(nt):
    return nd(nt, "ShaderNodeNewGeometry")


def attr(nt, name, out="Fac"):
    return nd(nt, "ShaderNodeAttribute", attribute_name=name, attribute_type="GEOMETRY").outputs[out]


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out


def rgba(c):
    return tuple(c) if len(c) == 4 else (*c, 1.0)


def principled(nt, color, rough=0.5, metal=0.0, coat=0.0, spec=0.5, normal=None):
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    put(nt, p.inputs["Base Color"], rgba(color) if isinstance(color, (tuple, list)) else color)
    put(nt, p.inputs["Roughness"], rough)
    put(nt, p.inputs["Metallic"], metal)
    for nm, v in (("Coat Weight", coat), ("Specular IOR Level", spec)):
        if nm in p.inputs:
            p.inputs[nm].default_value = v
    if normal is not None:
        nt.links.new(normal, p.inputs["Normal"])
    return p


def simple_mat(name, color, rough=0.5, metal=0.0, coat=0.0, bump=0.0, bscale=2.0):
    """One Principled surface. Constant inputs like these survive the glTF export to the web viewer."""
    m, nt, out = new_mat(name)
    nrm = None
    if bump:
        tc = nd(nt, "ShaderNodeTexCoord")
        b = nd(nt, "ShaderNodeBump", {"Strength": bump, "Distance": 0.05})
        nt.links.new(noise_t(nt, tc.outputs["Object"], bscale, 6), b.inputs["Height"])
        nrm = b.outputs[0]
    p = principled(nt, color, rough, metal, coat, normal=nrm)
    nt.links.new(p.outputs[0], out.inputs[0])
    m.diffuse_color = rgba(color)
    return m


def viewer_color(m, color, rough=None, metal=None):
    """What a material with a procedural (node-driven) colour should look like in the Three.js viewer, where node
    shaders do not travel: one honest average colour, and optionally roughness and metallic."""
    m.diffuse_color = rgba(color)
    if rough is not None:
        m.roughness = rough
    if metal is not None:
        m.metallic = metal
    return m


def viewer_emission(m, color, strength=1.0):
    """The light a node-driven material gives off at night in the Three.js viewer (the viewer fades it in after dusk)."""
    m["pf_emit"] = [c * strength for c in color[:3]]
    return m


def add_emission(m, color, strength):
    """Add light to a material's surface (night lighting, signs, LEDs)."""
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    src = out.inputs[0].links[0].from_socket
    e = nt.nodes.new("ShaderNodeEmission")
    put(nt, e.inputs["Color"], rgba(color) if isinstance(color, (tuple, list)) else color)
    put(nt, e.inputs["Strength"], strength)
    ad = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(src, ad.inputs[0])
    nt.links.new(e.outputs[0], ad.inputs[1])
    nt.links.new(ad.outputs[0], out.inputs[0])


def emit_mat(name, color, strength):
    m, nt, out = new_mat(name)
    e = nd(nt, "ShaderNodeEmission", {"Color": rgba(color), "Strength": strength})
    nt.links.new(e.outputs[0], out.inputs[0])
    return m


def tex_path(tex, kind):
    """A photographed surface map (Poly Haven CC0, fetched by `pf assets`): <project>/assets/tex/<id>_<kind>_1k.jpg."""
    p = os.path.join(PROJECT, "assets", "tex", "%s_%s_1k.jpg" % (tex, kind))
    return p if os.path.exists(p) else None


def tex_mat(name, tex, size, tint=(1.0, 1.0, 1.0), fallback=(0.3, 0.3, 0.3), bump=0.25, vary=0.25, rough=0.85):
    """Colour + roughness maps laid flat on the ground, one tile every `size` metres, with a slow change of tone over
    tens of metres so the tiling does not show from the air. Without the files: a procedural stand-in."""
    d = tex_path(tex, "diff")
    m, nt, out = new_mat(name)
    g = geo(nt)
    P = g.outputs["Position"]
    tone = maprange(nt, noise_t(nt, P, 0.03, 3), 0.3, 0.7, 1.0 - vary, 1.0 + vary * 0.4)
    if not d:
        grain = maprange(nt, noise_t(nt, P, 3.0 / max(size, 0.5), 5, 0.65), 0.3, 0.7, 0.8, 1.15)
        c = mix(nt, 1.0, rgba(fallback), M(nt, "MULTIPLY", tone, grain), "MULTIPLY")
        b = nd(nt, "ShaderNodeBump", {"Strength": bump, "Distance": 0.03})
        nt.links.new(noise_t(nt, P, 12.0 / max(size, 0.5), 4, 0.6), b.inputs["Height"])
        p = principled(nt, c, rough, normal=b.outputs[0])
        nt.links.new(p.outputs[0], out.inputs[0])
        m.diffuse_color = rgba(fallback)
        return m
    mp = nd(nt, "ShaderNodeMapping")
    nt.links.new(P, mp.inputs["Vector"])
    mp.inputs["Scale"].default_value = (1.0 / size,) * 3

    def img(path, data):
        n = nt.nodes.new("ShaderNodeTexImage")
        n.image = bpy.data.images.load(path, check_existing=True)
        if data:
            n.image.colorspace_settings.name = "Non-Color"
        nt.links.new(mp.outputs[0], n.inputs["Vector"])
        return n

    di = img(d, False)
    c = mix(nt, 1.0, mix(nt, 1.0, di.outputs["Color"], rgba(tint), "MULTIPLY"), tone, "MULTIPLY")
    b = nd(nt, "ShaderNodeBump", {"Strength": bump, "Distance": 0.03})
    nt.links.new(di.outputs["Color"], b.inputs["Height"])
    p = principled(nt, c, rough, normal=b.outputs[0])
    r = tex_path(tex, "rough")
    if r:
        nt.links.new(img(r, True).outputs["Color"], p.inputs["Roughness"])
    nt.links.new(p.outputs[0], out.inputs[0])
    m.diffuse_color = rgba(fallback)
    return m


# ---------------------------------------------------------------- meshes
def collection(name, hidden=False):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        if hidden:
            bpy.context.view_layer.layer_collection.children[c.name].exclude = True
    return c


def link_obj(o, coll=None):
    (coll or bpy.context.scene.collection).objects.link(o)
    return o


def mesh_obj(name, bm, mats=(), smooth=False, loc=(0, 0, 0), coll=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    o.location = loc
    return link_obj(o, coll)


def lathe(bm, prof, seg=96, mat=0, cap_top=False, cap_bottom=False):
    """prof: [(radius, z), ...] bottom to top, spun about the Z axis. The workhorse for towers, domes, columns."""
    rings = []
    for r, z in prof:
        rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg), z))
                      for i in range(seg)])
    for a, b in zip(rings, rings[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((a[i], a[j], b[j], b[i])).material_index = mat
    if cap_top:
        bm.faces.new(rings[-1]).material_index = mat
    if cap_bottom:
        bm.faces.new(rings[0][::-1]).material_index = mat
    return rings


def cube(bm, center, size, rotz=0.0, mat=0):
    m = Matrix.Translation(center) @ Matrix.Rotation(rotz, 4, "Z") @ Matrix.Diagonal((*size, 1))
    r = bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mat


def beam(bm, p1, p2, w, h=None, mat=0):
    """A square bar from p1 to p2 (struts, cables, railings, masts)."""
    p1, p2 = Vector(p1), Vector(p2)
    d = p2 - p1
    if d.length < 1e-6:
        return
    rot = d.to_track_quat("Z", "Y").to_matrix().to_4x4()
    m = Matrix.Translation((p1 + p2) / 2) @ rot @ Matrix.Diagonal((w, h or w, d.length, 1))
    r = bmesh.ops.create_cube(bm, size=1.0, matrix=m)
    for f in {f for v in r["verts"] for f in v.link_faces}:
        f.material_index = mat


def extrude(bm, pts, z0, z1, mat=0, cap=True):
    """A footprint [(x, y), ...] pulled up from z0 to z1 (walls, slabs, plinths)."""
    from mathutils.geometry import tessellate_polygon
    if signed_area(pts) < 0:
        pts = pts[::-1]
    lo = [bm.verts.new((x, y, z0)) for x, y in pts]
    hi = [bm.verts.new((x, y, z1)) for x, y in pts]
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((lo[i], lo[j], hi[j], hi[i])).material_index = mat
    if cap:
        for t in tessellate_polygon([[Vector((x, y, 0.0)) for x, y in pts]]):
            (x0, y0), (x1, y1), (x2, y2) = (pts[k] for k in t)
            if (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0) < 0:
                t = t[::-1]
            try:
                bm.faces.new([hi[k] for k in t]).material_index = mat
            except ValueError:
                pass


def signed_area(p):
    return 0.5 * sum(p[i][0] * p[(i + 1) % len(p)][1] - p[(i + 1) % len(p)][0] * p[i][1] for i in range(len(p)))


def ribbon(bm, pts, hw, z, mat=0, off=0.0, ext=True, uvl=None):
    """A flat strip of half-width hw along a polyline (roads, paths, lines), `off` metres to the left of it."""
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 0.05:
            continue
        ux, uy = (x1 - x0) / L, (y1 - y0) / L
        nx, ny = -uy, ux
        e = min(hw, 4.0) * 0.5 if ext else 0.0            # overlap at the joints
        a, b = (x0 - ux * e + nx * off, y0 - uy * e + ny * off), (x1 + ux * e + nx * off, y1 + uy * e + ny * off)
        f = bm.faces.new([bm.verts.new((a[0] - nx * hw, a[1] - ny * hw, z)), bm.verts.new((b[0] - nx * hw, b[1] - ny * hw, z)),
                          bm.verts.new((b[0] + nx * hw, b[1] + ny * hw, z)), bm.verts.new((a[0] + nx * hw, a[1] + ny * hw, z))])
        f.material_index = mat
        if uvl is not None:
            for lp, t in zip(f.loops, ((0, 0), (L, 0), (L, 1), (0, 1))):
                lp[uvl].uv = t


def wall(bm, pts, off, z0, z1, mat=0):
    """A vertical sheet along a polyline (parapets, fences, embankments), `off` metres to the left of it."""
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        if L < 0.05:
            continue
        nx, ny = -(y1 - y0) / L * off, (x1 - x0) / L * off
        bm.faces.new([bm.verts.new((x0 + nx, y0 + ny, z0)), bm.verts.new((x1 + nx, y1 + ny, z0)),
                      bm.verts.new((x1 + nx, y1 + ny, z1)), bm.verts.new((x0 + nx, y0 + ny, z1))]).material_index = mat


def fill(bm, pts, z, mat=0):
    """A flat polygon at height z (water, lawns, plazas)."""
    from mathutils.geometry import tessellate_polygon
    vs = [bm.verts.new((x, y, z)) for x, y in pts]
    for t in tessellate_polygon([[Vector((x, y, 0.0)) for x, y in pts]]):
        (x0, y0), (x1, y1), (x2, y2) = (pts[k] for k in t)
        if (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0) < 0:
            t = t[::-1]
        try:
            bm.faces.new([vs[k] for k in t]).material_index = mat
        except ValueError:
            pass


def log(*a):
    print("pf:", *a, flush=True)

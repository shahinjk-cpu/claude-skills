"""placeforge engine, look: render settings and devices, sky, sun, haze, clouds, the colour grade and the shared
materials (buildings with windows drawn by the shader, ground, water, foliage, roads)."""
import bpy, bmesh, math, sys
from mathutils import Vector
import pf_core as pf
from pf_core import nd, put, M, VM, mix, sep, comb, noise_t, noise4, ramp, maprange, geo, attr, new_mat, principled, simple_mat, arg, cfg


def scene():
    """Empty scene, Cycles on the best device this machine has: Metal on a Mac, OptiX / CUDA on NVIDIA, HIP on AMD,
    oneAPI on Intel Arc, otherwise the CPU. device=CPU|CUDA|OPTIX|HIP|ONEAPI|METAL forces one."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.frame_start = sc.frame_end = 1
    r = cfg("render")
    sc.render.resolution_x, sc.render.resolution_y = int(arg("w", r["w"])), int(arg("h", r["h"]))
    sc.render.resolution_percentage = int(arg("pct", 100))
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    want = arg("device")
    kinds = (want.upper(),) if want else (("METAL",) if sys.platform == "darwin" else ("OPTIX", "CUDA", "HIP", "ONEAPI"))
    gpu = False
    for kind in kinds:
        if kind == "CPU":
            break
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
        except Exception:
            continue
        if any(d.type == kind for d in prefs.devices):
            gpu = True
            break
    for d in prefs.devices:
        d.use = gpu and (d.type != "CPU" or sys.platform == "darwin")
    c = sc.cycles
    c.device = "GPU" if gpu else "CPU"
    pf.log("cycles device:", [(d.name, d.type) for d in prefs.devices if d.use] if gpu else "CPU (no supported GPU found)")
    c.samples = int(arg("samples", r["samples"]))
    c.use_adaptive_sampling = True
    c.adaptive_threshold = float(arg("noise", r["noise"]))
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    try:
        c.denoising_use_gpu = gpu          # on a rented GPU the CPU denoise is the bottleneck
    except Exception:
        pass
    c.max_bounces, c.diffuse_bounces, c.glossy_bounces, c.transmission_bounces = 8, 3, 4, 4
    c.volume_bounces = 2
    c.volume_max_steps = 512
    c.transparent_max_bounces = 8
    c.caustics_reflective = c.caustics_refractive = False
    c.blur_glossy = 1.0
    sc.view_settings.view_transform = "AgX"
    look = {"base": "AgX - Base Contrast", "mh": "AgX - Medium High Contrast", "punchy": "AgX - Punchy", "none": "None"}
    try:
        sc.view_settings.look = look.get(str(arg("agx", cfg("look.agx"))), "AgX - Punchy")
    except Exception:
        pass
    sc.view_settings.exposure = float(arg("exp", pf.by_tod("look.exposure", 0.4)))
    return sc


def world(sc):
    """Sky. day: the physical sky (or a gradient matched to the reference photo: look.sky = "gradient"), with the light
    it gives the scene set apart from what the camera sees; sunset: the physical sky with the sun's disc; night: a dark
    gradient, stars and a low city glow."""
    w = bpy.data.worlds.new("sky")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes.get("Background") or nt.nodes.new("ShaderNodeBackground")
    if not bg.outputs[0].links:
        nt.links.new(bg.outputs[0], (nt.nodes.get("World Output") or nt.nodes.new("ShaderNodeOutputWorld")).inputs[0])
    sky = nt.nodes.new("ShaderNodeTexSky")
    for kind in ("MULTIPLE_SCATTERING", "NISHITA"):
        try:
            sky.sky_type = kind
            break
        except TypeError:
            continue
    s = pf.sun_dir()
    sky.sun_elevation = math.asin(max(-1.0, min(1.0, s.z)))
    sky.sun_rotation = math.atan2(s.x, s.y)
    sky.sun_disc = False
    for k, v in (("altitude", 0), ("air_density", 1.0), ("aerosol_density", float(cfg("look.aerosol", 0.5))), ("ozone_density", 1.0)):
        try:
            setattr(sky, k, v)
        except Exception:
            pass
    g = geo(nt)
    d = VM(nt, "SCALE", g.outputs["Incoming"])
    d.node.inputs["Scale"].default_value = -1.0
    _, _, dz = sep(nt, d)
    t = pf.tod()
    lp = nd(nt, "ShaderNodeLightPath")
    if t == "night":
        ng = ramp(nt, dz, [(0.0, (0.060, 0.042, 0.035)), (0.05, (0.028, 0.030, 0.045)), (0.3, (0.008, 0.012, 0.030)), (1.0, (0.003, 0.005, 0.016))])
        st = nd(nt, "ShaderNodeTexVoronoi", {"Scale": 420.0, "Randomness": 1.0})
        nt.links.new(d, st.inputs["Vector"])
        wn = nd(nt, "ShaderNodeTexWhiteNoise", noise_dimensions="3D")
        nt.links.new(st.outputs["Position"], wn.inputs["Vector"])
        star = M(nt, "MULTIPLY", M(nt, "MULTIPLY", maprange(nt, st.outputs["Distance"], 0.045, 0.0, 0.0, 1.0), M(nt, "GREATER_THAN", wn.outputs["Value"], 0.82)),
                 maprange(nt, dz, 0.05, 0.3, 0.0, 0.06))
        nt.links.new(mix(nt, 1.0, ng, comb(nt, star, star, star), "ADD"), bg.inputs[0])
        bg.inputs[1].default_value = 1.0
    elif t == "sunset":
        sky.sun_disc = True
        try:
            sky.sun_size = math.radians(1.6)
        except Exception:
            pass
        nt.links.new(sky.outputs[0], bg.inputs[0])
        bg.inputs[1].default_value = float(cfg("look.sky_light", 0.5))
    else:
        if cfg("look.sky") == "gradient":
            col = ramp(nt, dz, [(p, tuple(c)) for p, c in cfg("look.sky_stops")])
        else:
            col = sky.outputs[0]
        nt.links.new(col, bg.inputs[0])
        sk, sl = float(cfg("look.sky_camera", 0.85)), float(cfg("look.sky_light", 0.5))
        if cfg("look.sky") != "gradient":
            sk, sl = sk * 0.35, sl * 0.35           # the physical sky is far brighter than a hand-set gradient
        nt.links.new(M(nt, "ADD", sl, M(nt, "MULTIPLY", lp.outputs["Is Camera Ray"], sk - sl)), bg.inputs[1])
    return w


def sun_lamp():
    t = pf.tod()
    l = bpy.data.lights.new("sun", "SUN")
    l.energy = float(arg("sunk", pf.by_tod("look.sun_strength", 6.0)))
    l.color = {"day": (1.0, 0.92, 0.80), "sunset": (1.0, 0.48, 0.18), "night": (0.55, 0.66, 1.0)}[t]
    l.angle = math.radians(0.6)
    o = pf.link_obj(bpy.data.objects.new("sun", l))
    o.rotation_euler = (-pf.sun_dir()).to_track_quat("-Z", "Y").to_euler()
    return o


def haze(reach):
    """A slab of thin scattering air: far things fade and turn blue (aerial perspective). Thickness in metres matters:
    too tall and the low sky goes grey."""
    dens = float(arg("haze", pf.by_tod("look.haze", 0.00005)))
    if dens <= 0:
        return
    t = pf.tod()
    m, nt, out = new_mat("haze")
    s = nd(nt, "ShaderNodeVolumeScatter", {"Color": {"day": (0.78, 0.86, 1.0, 1), "sunset": (1.0, 0.72, 0.42, 1), "night": (0.8, 0.8, 0.85, 1)}[t],
                                           "Density": dens, "Anisotropy": 0.55})
    nt.links.new(s.outputs[0], out.inputs["Volume"])
    top = float(cfg("look.haze_top_m", 800))
    bm = bmesh.new()
    pf.cube(bm, (0, 0, top / 2), (reach * 2, reach * 2, top))
    pf.mesh_obj("haze", bm, [m])


def cloud_layer(name, z0, z1, reach, cell, patch, cov, dens):
    """A slab of procedural volumetric cloud lit by the sun. cell: puff size (m); patch: size of the cloudy areas (m);
    cov: 0..1 threshold, higher = fewer clouds."""
    m, nt, out = new_mat(name)
    tc = nd(nt, "ShaderNodeTexCoord")
    P = tc.outputs["Object"]
    _, _, pz = sep(nt, P)
    h = maprange(nt, pz, z0, z1)
    prof = M(nt, "SUBTRACT", 1.0, M(nt, "POWER", M(nt, "ABSOLUTE", M(nt, "SUBTRACT", M(nt, "MULTIPLY", h, 2.0), 1.0)), 2.0))
    prof = M(nt, "MULTIPLY", prof, maprange(nt, h, 0.0, 0.35, 0.55, 1.0))
    warp = noise_t(nt, P, 2.0 / patch, 2, 0.5, out="Color")
    off = VM(nt, "SCALE", VM(nt, "SUBTRACT", warp, (0.5, 0.5, 0.5)), None)
    off.node.inputs["Scale"].default_value = cell * 1.5
    big = noise_t(nt, VM(nt, "MULTIPLY", P, (1.0, 1.0, 0.0)), 1.0 / patch, 3, 0.55)
    small = noise_t(nt, VM(nt, "ADD", P, off), 1.0 / cell, 6, 0.58)
    d = M(nt, "ADD", M(nt, "MULTIPLY", big, 0.55), M(nt, "MULTIPLY", small, 0.45))
    d = M(nt, "SUBTRACT", d, M(nt, "MULTIPLY", M(nt, "SUBTRACT", 1.0, prof), 0.3))
    d = maprange(nt, d, cov, cov + 0.08, 0.0, dens)
    v = nd(nt, "ShaderNodeVolumePrincipled", {"Color": (0.97, 0.97, 0.98, 1), "Anisotropy": 0.45})
    nt.links.new(d, v.inputs["Density"])
    nt.links.new(v.outputs[0], out.inputs["Volume"])
    bm = bmesh.new()
    pf.cube(bm, (0, 0, (z0 + z1) / 2), (reach * 2, reach * 2, z1 - z0))
    o = pf.mesh_obj(name, bm, [m])
    o.visible_shadow = bool(cfg("look.cloud_shadows", False))     # a reference photo in full sun: keep cloud shadows off


def clouds(reach):
    c = float(arg("clouds", cfg("look.clouds", 0.35)))
    if c <= 0 or pf.tod() == "night":
        return
    cloud_layer("clouds_high", 2600, 2820, reach, 240.0, 5000.0, 0.62 - 0.25 * c, 0.005)
    cloud_layer("clouds_low", 1000, 1500, reach, 520.0, 6000.0, 0.68 - 0.2 * c, 0.02)


def grade(sc):
    """Compositor finish: glow at sunset and night, saturation, contrast. Skipped if this Blender's API differs."""
    t = pf.tod()
    try:
        ng = bpy.data.node_groups.new("grade", "CompositorNodeTree")
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        rl = ng.nodes.new("CompositorNodeRLayers")
        go = ng.nodes.new("NodeGroupOutput")
        img = rl.outputs["Image"]
        for gtype, thr, k in {"sunset": [("Fog Glow", 4.0, 0.6), ("Bloom", 3.0, 0.4)], "night": [("Bloom", 1.5, 0.3)], "day": []}[t]:
            gn = ng.nodes.new("CompositorNodeGlare")
            try:
                gn.inputs["Type"].default_value = gtype
                gn.inputs["Threshold"].default_value = thr
                gn.inputs["Strength"].default_value = k
            except Exception:
                continue
            ng.links.new(img, gn.inputs["Image"])
            img = gn.outputs[0]
        hs = ng.nodes.new("CompositorNodeHueSat")
        ng.links.new(img, hs.inputs["Image"])
        hs.inputs["Saturation"].default_value = float(arg("sat", cfg("look.saturation", 1.08))) * {"day": 1.0, "sunset": 1.2, "night": 1.15}[t]
        bc = ng.nodes.new("CompositorNodeBrightContrast")
        ng.links.new(hs.outputs[0], bc.inputs["Image"])
        bc.inputs["Contrast"].default_value = float(arg("con", cfg("look.contrast", 5.0)))
        ng.links.new(bc.outputs[0], go.inputs[0])
        sc.compositing_node_group = ng
        sc.render.use_compositing = True
    except Exception as e:
        pf.log("grade skipped:", e)


# ---------------------------------------------------------------- materials
def mat_buildings():
    """Every ordinary building is one mesh with face attributes: col (wall or roof colour), roof (1 on roofs),
    glass (curtain wall), rnd (per building; below 0.05 = shed without windows). The shader draws floors, window
    bays, frames, sills, rain streaks and roof patches from world position, and lights windows at night."""
    m, nt, out = new_mat("buildings")
    g = geo(nt)
    FL = float(cfg("region.floor_m", 3.2))
    wk = float(cfg("region.weathering", 0.6))
    col, roof, glass, rnd = attr(nt, "col", "Color"), attr(nt, "roof"), attr(nt, "glass"), attr(nt, "rnd")
    P, N = g.outputs["Position"], g.outputs["Normal"]
    _, _, pz = sep(nt, P)
    _, _, nz = sep(nt, N)
    wall = maprange(nt, M(nt, "ABSOLUTE", nz), 0.6, 0.3)
    tang = VM(nt, "NORMALIZE", VM(nt, "CROSS_PRODUCT", N, (0.0, 0.0, 1.0)))
    hc = VM(nt, "DOT_PRODUCT", P, tang, out=1)
    fz = M(nt, "FRACT", M(nt, "ADD", M(nt, "DIVIDE", pz, FL), M(nt, "MULTIPLY", rnd, 0.7)))
    fh = M(nt, "FRACT", M(nt, "ADD", M(nt, "DIVIDE", hc, 3.4), M(nt, "MULTIPLY", rnd, 13.7)))
    ww = M(nt, "ADD", 0.08, M(nt, "MULTIPLY", M(nt, "FRACT", M(nt, "MULTIPLY", rnd, 7.3)), 0.16))
    wtop = M(nt, "ADD", 0.82, M(nt, "MULTIPLY", M(nt, "FRACT", M(nt, "MULTIPLY", rnd, 3.1)), 0.1))
    wv = M(nt, "MULTIPLY", M(nt, "GREATER_THAN", fz, 0.30), M(nt, "LESS_THAN", fz, wtop))
    wh = M(nt, "MULTIPLY", M(nt, "GREATER_THAN", fh, ww), M(nt, "LESS_THAN", fh, M(nt, "SUBTRACT", 1.0, ww)))
    above = M(nt, "GREATER_THAN", pz, 2.8)
    win = M(nt, "MULTIPLY", M(nt, "MULTIPLY", wv, wh), above)
    mull = M(nt, "MULTIPLY", M(nt, "GREATER_THAN", M(nt, "FRACT", M(nt, "DIVIDE", hc, 1.6)), 0.07),
             M(nt, "GREATER_THAN", M(nt, "FRACT", M(nt, "DIVIDE", pz, FL + 0.4)), 0.1))
    win = M(nt, "ADD", M(nt, "MULTIPLY", win, M(nt, "SUBTRACT", 1.0, glass)), M(nt, "MULTIPLY", mull, glass))
    has_win = M(nt, "GREATER_THAN", rnd, 0.05)
    not_roof = M(nt, "SUBTRACT", 1.0, roof)
    win = M(nt, "MULTIPLY", M(nt, "MULTIPLY", win, wall), M(nt, "MULTIPLY", has_win, not_roof), clamp=True)
    wv2 = M(nt, "MULTIPLY", M(nt, "GREATER_THAN", fz, 0.25), M(nt, "LESS_THAN", fz, M(nt, "ADD", wtop, 0.035)))
    wh2 = M(nt, "MULTIPLY", M(nt, "GREATER_THAN", fh, M(nt, "SUBTRACT", ww, 0.035)), M(nt, "LESS_THAN", fh, M(nt, "SUBTRACT", 1.035, ww)))
    frame = M(nt, "MULTIPLY", M(nt, "MULTIPLY", M(nt, "MULTIPLY", wv2, wh2), above),
              M(nt, "MULTIPLY", M(nt, "MULTIPLY", wall, has_win), M(nt, "MULTIPLY", not_roof, M(nt, "SUBTRACT", 1.0, glass))))
    frame = M(nt, "SUBTRACT", frame, win, clamp=True)
    reveal = M(nt, "MULTIPLY", win, M(nt, "LESS_THAN", M(nt, "SUBTRACT", wtop, fz), 0.06))
    streak = noise_t(nt, VM(nt, "MULTIPLY", P, (0.25, 0.25, 0.035)), 1.0, 5, 0.6)
    dirt = maprange(nt, streak, 0.45, 0.75, 1.0, 1.0 - 0.6 * wk)
    patch = maprange(nt, noise_t(nt, P, 0.35, 4, 0.6), 0.3, 0.7, 1.0 - 0.7 * wk, 1.05)
    slab = M(nt, "LESS_THAN", fz, 0.07)
    ground_dirt = maprange(nt, pz, 0.0, 2.5, 1.0 - 0.6 * wk, 1.0)
    sill = maprange(nt, noise_t(nt, VM(nt, "MULTIPLY", P, (0.6, 0.6, 0.12)), 1.5, 3, 0.5), 0.5, 0.8, 1.0, 1.0 - 0.4 * wk)
    shade = M(nt, "ADD", M(nt, "MULTIPLY", M(nt, "MULTIPLY", dirt, ground_dirt), sill), M(nt, "MULTIPLY", slab, 0.18))
    under = M(nt, "MULTIPLY", M(nt, "MULTIPLY", wh, M(nt, "LESS_THAN", fz, 0.30)), M(nt, "MULTIPLY", above, has_win))
    shade = M(nt, "MULTIPLY", shade, M(nt, "SUBTRACT", 1.0, M(nt, "MULTIPLY", under, maprange(nt, fz, 0.0, 0.3, 0.05, 0.35 * wk))))
    wc = mix(nt, 1.0, col, shade, "MULTIPLY")
    wc = mix(nt, M(nt, "MULTIPLY", frame, 0.75), wc, (0.80, 0.79, 0.75, 1))
    rc = mix(nt, 1.0, col, patch, "MULTIPLY")
    base = mix(nt, roof, wc, rc)
    shed = M(nt, "SUBTRACT", 1.0, has_win)                       # sheds: sheet cladding seams, rust, big dark doors
    seam = M(nt, "MULTIPLY", M(nt, "LESS_THAN", M(nt, "FRACT", M(nt, "DIVIDE", hc, 0.9)), 0.1), shed)
    base = mix(nt, M(nt, "MULTIPLY", seam, 0.32), base, (0.0, 0.0, 0.0, 1))
    rust = M(nt, "MULTIPLY", maprange(nt, noise_t(nt, VM(nt, "MULTIPLY", P, (0.12, 0.12, 0.5)), 1.0, 4, 0.6), 0.52, 0.78, 0.0, 0.9 * wk), shed)
    base = mix(nt, rust, base, (0.22, 0.10, 0.05, 1))
    dfr = M(nt, "FRACT", M(nt, "DIVIDE", hc, 24.0))
    door = M(nt, "MULTIPLY", M(nt, "MULTIPLY", M(nt, "GREATER_THAN", dfr, 0.42), M(nt, "LESS_THAN", dfr, 0.60)),
             M(nt, "MULTIPLY", M(nt, "LESS_THAN", pz, 4.6), M(nt, "MULTIPLY", wall, M(nt, "MULTIPLY", shed, not_roof))))
    base = mix(nt, door, base, (0.06, 0.07, 0.08, 1))
    wallb = principled(nt, base, 0.85)
    wn = nd(nt, "ShaderNodeTexWhiteNoise", noise_dimensions="3D")
    cell = comb(nt, M(nt, "FLOOR", M(nt, "DIVIDE", hc, 3.4)), M(nt, "FLOOR", M(nt, "DIVIDE", pz, FL)), M(nt, "MULTIPLY", rnd, 97.0))
    nt.links.new(cell, wn.inputs["Vector"])
    gcol = mix(nt, wn.outputs["Value"], (0.05, 0.06, 0.065, 1), (0.16, 0.18, 0.19, 1))
    gcol = mix(nt, M(nt, "MULTIPLY", reveal, 0.8), gcol, (0.01, 0.01, 0.012, 1))
    gl = principled(nt, gcol, M(nt, "ADD", 0.03, M(nt, "MULTIPLY", wn.outputs["Value"], 0.15)), 0.0, spec=0.9)
    ms = nd(nt, "ShaderNodeMixShader")
    put(nt, ms.inputs[0], win)
    nt.links.new(wallb.outputs[0], ms.inputs[1])
    nt.links.new(gl.outputs[0], ms.inputs[2])
    nt.links.new(ms.outputs[0], out.inputs[0])
    if pf.tod() == "night":             # about a quarter of the windows lit, warm and cool
        wl = nd(nt, "ShaderNodeTexWhiteNoise", noise_dimensions="3D")
        nt.links.new(VM(nt, "ADD", cell, (0.0, 0.0, 13.0)), wl.inputs["Vector"])
        lit = M(nt, "GREATER_THAN", wl.outputs["Value"], 0.74)
        wc_ = ramp(nt, wl.outputs["Color"], [(0.0, (1.0, 0.62, 0.30)), (0.6, (1.0, 0.80, 0.55)), (0.92, (0.80, 0.88, 1.0)), (1.0, (0.55, 0.70, 1.0))])
        pf.add_emission(m, wc_, M(nt, "MULTIPLY", M(nt, "MULTIPLY", win, lit), 1.6))
    return m


def mat_ground(city_r, far_r):
    """Bare land under everything: earth and worn grass near; far away a mosaic of roofs and tree tops, so the land
    beyond the built radius does not read as an empty plain."""
    m, nt, out = new_mat("ground")
    g = geo(nt)
    P = g.outputs["Position"]
    n1, n2 = noise_t(nt, P, 0.02, 6, 0.6), noise_t(nt, P, 0.15, 4, 0.6)
    soil = ramp(nt, M(nt, "ADD", M(nt, "MULTIPLY", n1, 0.7), M(nt, "MULTIPLY", n2, 0.3)),
                [(0.3, (0.06, 0.09, 0.025)), (0.45, (0.13, 0.12, 0.07)), (0.6, (0.19, 0.16, 0.11)), (0.75, (0.24, 0.22, 0.18))])
    vor = nd(nt, "ShaderNodeTexVoronoi", {"Scale": 0.045})
    nt.links.new(P, vor.inputs["Vector"])
    far = ramp(nt, vor.outputs["Color"], [(0.0, (0.04, 0.08, 0.02)), (0.3, (0.05, 0.09, 0.03)), (0.45, (0.5, 0.48, 0.44)),
                                          (0.6, (0.62, 0.6, 0.56)), (0.75, (0.35, 0.12, 0.07)), (0.9, (0.45, 0.45, 0.47))])
    dist = VM(nt, "LENGTH", VM(nt, "MULTIPLY", P, (1.0, 1.0, 0.0)), out=1)
    c = mix(nt, maprange(nt, dist, far_r * 0.9, far_r * 1.3), soil, far)
    p = principled(nt, c, 0.9)
    nt.links.new(p.outputs[0], out.inputs[0])
    return m


def mat_water(name, color, rough=0.05, wave=1.0, spec=0.5):
    """Wind on open water: wavelets in three scales that drift with time in a film, calm streaks and cat's paws,
    murk drifting in blooms. Water's own reflectance does the rest: dark looking down, a mirror at grazing angles."""
    m, nt, out = new_mat(name)
    g = geo(nt)
    P = g.outputs["Position"]
    a = math.radians(90.0 - float(cfg("region.wind_bearing", 240)))
    ca, sa = math.cos(a), math.sin(a)
    px, py, pz = sep(nt, P)
    u = M(nt, "ADD", M(nt, "MULTIPLY", px, ca), M(nt, "MULTIPLY", py, sa))
    v = M(nt, "SUBTRACT", M(nt, "MULTIPLY", py, ca), M(nt, "MULTIPLY", px, sa))
    W = comb(nt, u, M(nt, "MULTIPLY", v, 0.38), pz)
    patch = maprange(nt, noise4(nt, P, 0.006, 3, 0.55, 0.03), 0.35, 0.68, 0.18, 1.0)
    rip, chop, swell = noise4(nt, W, 2.2, 6, 0.62, 0.9), noise4(nt, W, 0.55, 4, 0.55, 0.45, 0.3), noise4(nt, W, 0.09, 2, 0.5, 0.12)
    hgt = M(nt, "MULTIPLY", M(nt, "ADD", M(nt, "ADD", M(nt, "MULTIPLY", rip, 0.35), M(nt, "MULTIPLY", chop, 0.45)), M(nt, "MULTIPLY", swell, 0.5)), patch)
    b = nd(nt, "ShaderNodeBump", {"Strength": min(wave, 1.0), "Distance": 0.04 * max(wave, 1.0)})
    nt.links.new(hgt, b.inputs["Height"])
    bloom = maprange(nt, noise4(nt, P, 0.012, 4, 0.6, 0.01, 0.4), 0.3, 0.72, 0.0, 1.0)
    col = mix(nt, bloom, pf.rgba(color), (color[0] * 1.45, color[1] * 1.08, color[2] * 0.7, 1))
    col = mix(nt, M(nt, "MULTIPLY", maprange(nt, noise_t(nt, P, 0.09, 3, 0.6), 0.55, 0.75, 0.0, 1.0), 0.35), col,
              (color[0] * 0.75, color[1] * 0.85, color[2] * 0.9, 1))
    p = principled(nt, col, M(nt, "ADD", rough * 0.3, M(nt, "MULTIPLY", patch, rough)), spec=spec, normal=b.outputs[0])
    p.inputs["IOR"].default_value = 1.333
    nt.links.new(p.outputs[0], out.inputs[0])
    m.diffuse_color = pf.rgba(color)
    return m


def mat_embankment():
    """Concrete with a dark wet band and algae stain at the waterline, streaks above."""
    m, nt, out = new_mat("embankment")
    g = geo(nt)
    P = g.outputs["Position"]
    _, _, pz = sep(nt, P)
    wl = maprange(nt, M(nt, "ADD", pz, M(nt, "MULTIPLY", noise_t(nt, P, 1.5, 3, 0.6), 0.25)), 0.55, 0.25, 0.0, 1.0)
    streak = maprange(nt, noise_t(nt, VM(nt, "MULTIPLY", P, (3.0, 3.0, 0.25)), 1.0, 4, 0.6), 0.45, 0.7, 0.0, 1.0)
    base = mix(nt, M(nt, "MULTIPLY", streak, 0.5), (0.42, 0.41, 0.38, 1), (0.28, 0.28, 0.25, 1))
    hb = nd(nt, "ShaderNodeBump", {"Strength": 0.25, "Distance": 0.02})
    nt.links.new(noise_t(nt, P, 6.0, 4, 0.6), hb.inputs["Height"])
    p = principled(nt, mix(nt, wl, base, (0.07, 0.09, 0.04, 1)), M(nt, "SUBTRACT", 0.88, M(nt, "MULTIPLY", wl, 0.45)), spec=0.4, normal=hb.outputs[0])
    nt.links.new(p.outputs[0], out.inputs[0])
    return m


LEAF_GREENS = [(0.0, (0.050, 0.100, 0.020)), (0.3, (0.080, 0.150, 0.030)), (0.6, (0.115, 0.190, 0.040)), (0.85, (0.15, 0.21, 0.05)), (1.0, (0.19, 0.22, 0.07))]


def mat_leaves(name="leaves", greens=None):
    """Canopy: a green per tree, light and dark clumps inside a crown, a leaf-clump bump, light shining through.
    Albedo is kept high enough to look sunlit: dark crowns read as holes."""
    m, nt, out = new_mat(name)
    oi = nd(nt, "ShaderNodeObjectInfo")
    O = nd(nt, "ShaderNodeTexCoord").outputs["Object"]
    base = ramp(nt, oi.outputs["Random"], greens or LEAF_GREENS)
    vor = nd(nt, "ShaderNodeTexVoronoi", {"Scale": 1.4, "Randomness": 1.0})
    nt.links.new(O, vor.inputs["Vector"])
    clump = maprange(nt, vor.outputs["Distance"], 0.0, 0.7, 1.0, 0.0)
    var = maprange(nt, noise_t(nt, O, 0.6, 3, 0.6), 0.3, 0.7, 0.65, 1.25)
    c = mix(nt, 1.0, base, M(nt, "MULTIPLY", var, M(nt, "ADD", 0.75, M(nt, "MULTIPLY", clump, 0.35))), "MULTIPLY")
    b = nd(nt, "ShaderNodeBump", {"Strength": 1.0, "Distance": 0.35})
    nt.links.new(M(nt, "ADD", clump, M(nt, "MULTIPLY", noise_t(nt, O, 6.0, 3, 0.6), 0.5)), b.inputs["Height"])
    p = principled(nt, c, 0.7, spec=0.35, normal=b.outputs[0])
    tr = nd(nt, "ShaderNodeBsdfTranslucent")
    put(nt, tr.inputs["Color"], mix(nt, 1.0, c, (1.6, 1.9, 0.9, 1), "MULTIPLY"))
    nt.links.new(b.outputs[0], tr.inputs["Normal"])
    ms = nd(nt, "ShaderNodeMixShader", {"Fac": 0.22})
    nt.links.new(p.outputs[0], ms.inputs[1])
    nt.links.new(tr.outputs[0], ms.inputs[2])
    nt.links.new(ms.outputs[0], out.inputs[0])
    m.diffuse_color = (0.1, 0.17, 0.035, 1)
    return m


def mat_leaf_cards():
    """Leaf sprays: each small card shows a handful of leaves cut out of it. Close up, clumps alone read as green
    boulders; the cards give a crown its leafy, broken edge."""
    m, nt, out = new_mat("leaf_cards")
    oi = nd(nt, "ShaderNodeObjectInfo")
    tc = nd(nt, "ShaderNodeTexCoord")
    uv = tc.outputs["UV"]
    base = ramp(nt, oi.outputs["Random"], [(p, tuple(min(1.0, x * 1.08) for x in c)) for p, c in LEAF_GREENS])
    vor = nd(nt, "ShaderNodeTexVoronoi", {"Scale": 4.2, "Randomness": 0.9})
    mp = nd(nt, "ShaderNodeMapping")
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    mp.inputs["Scale"].default_value = (3.7, 3.7, 3.7)
    nt.links.new(VM(nt, "ADD", uv, mp.outputs[0]), vor.inputs["Vector"])
    leaf = M(nt, "LESS_THAN", vor.outputs["Distance"], 0.36)
    ux, uy, _ = sep(nt, uv)
    rad = M(nt, "SQRT", M(nt, "ADD", M(nt, "POWER", M(nt, "SUBTRACT", ux, 0.5), 2.0), M(nt, "POWER", M(nt, "SUBTRACT", uy, 0.5), 2.0)))
    alpha = M(nt, "MULTIPLY", leaf, M(nt, "LESS_THAN", rad, 0.48))
    c = mix(nt, 1.0, base, maprange(nt, noise_t(nt, tc.outputs["Object"], 0.9, 3, 0.6), 0.3, 0.7, 0.7, 1.3), "MULTIPLY")
    p = principled(nt, c, 0.55, spec=0.4)
    tr = nd(nt, "ShaderNodeBsdfTranslucent")
    put(nt, tr.inputs["Color"], mix(nt, 1.0, c, (1.7, 2.0, 0.9, 1), "MULTIPLY"))
    ms = nd(nt, "ShaderNodeMixShader", {"Fac": 0.35})
    nt.links.new(p.outputs[0], ms.inputs[1])
    nt.links.new(tr.outputs[0], ms.inputs[2])
    tp = nd(nt, "ShaderNodeBsdfTransparent")
    cut = nd(nt, "ShaderNodeMixShader")
    nt.links.new(alpha, cut.inputs[0])
    nt.links.new(tp.outputs[0], cut.inputs[1])
    nt.links.new(ms.outputs[0], cut.inputs[2])
    nt.links.new(cut.outputs[0], out.inputs[0])
    m.diffuse_color = (0.11, 0.19, 0.04, 1)
    return m


def mat_glass(name="glass", color=(0.10, 0.14, 0.16), mullion=3.0, rough=0.06):
    """Curtain-wall glass for a landmark: dark reflective panes with a thin frame every `mullion` metres."""
    m, nt, out = new_mat(name)
    g = geo(nt)
    P, N = g.outputs["Position"], g.outputs["Normal"]
    _, _, pz = sep(nt, P)
    tang = VM(nt, "NORMALIZE", VM(nt, "CROSS_PRODUCT", N, (0.0, 0.0, 1.0)))
    hc = VM(nt, "DOT_PRODUCT", P, tang, out=1)
    fr = M(nt, "MAXIMUM", M(nt, "LESS_THAN", M(nt, "FRACT", M(nt, "DIVIDE", hc, mullion)), 0.04),
           M(nt, "LESS_THAN", M(nt, "FRACT", M(nt, "DIVIDE", pz, mullion * 1.2)), 0.04))
    p = principled(nt, mix(nt, fr, pf.rgba(color), (0.55, 0.56, 0.57, 1)), M(nt, "ADD", rough, M(nt, "MULTIPLY", fr, 0.4)), 0.0, spec=0.9)
    nt.links.new(p.outputs[0], out.inputs[0])
    m.diffuse_color = pf.rgba(color)
    return m

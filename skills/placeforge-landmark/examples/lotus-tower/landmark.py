"""Lotus Tower (Nelum Kuluna), Colombo: the worked example of a placeforge landmark.

351.5 m in all. Heights measured on the reference photos: podium 0-21 m (two inverted cones of glass, a white
scalloped rim), shaft 21-190 m (r 13.6 -> 8.4), collar 190 m, green calyx 193-226 m, pink bud 226-256 m (widest r 19 m
at 232 m), grey cap 255-268 m, tan mast 268-295 m, white antenna 295-351.5 m.

What the perfection loop taught (renders/LOOPS.md of the original project):
    the bud's proportions came from close-ups, never the wide shot (height / width 1.35, the cup sitting wide on the rings);
    faceted mirror glass = flat-shaded panels with some metal; outer layers must be outermost (cup lobes over tier 1);
    night: one saturated LED colour at a time on the bud, low emission strengths (bright saturated light goes white).
"""
import bmesh, math, random
from mathutils import Vector, Matrix
import pf_core as pf
import pf_look as look
from pf_core import (nd, put, M, mix, sep, comb, noise_t, maprange, new_mat, principled, simple_mat, add_emission,
                     mesh_obj, lathe, cube, beam)

NIGHT = pf.tod() == "night"
KEEP_OUT = [(0.0, 0.0, 56.0)]          # the tower's own plot: the map's stand-in footprints and trees are cleared
TURN = math.radians(5.0)               # the model was drawn facing the photo (bearing 355): turn it to true north


def facing_k(nt, k=0.7, p=1.5):
    """1 facing the camera, falling to 1-k at grazing angles: lit surfaces read round, not flat."""
    lw = nd(nt, "ShaderNodeLayerWeight", {"Blend": 0.5})
    return M(nt, "SUBTRACT", 1.0, M(nt, "MULTIPLY", M(nt, "POWER", lw.outputs["Facing"], p), k))


def mat_tower_green(name="tower_green", color=(0.004, 0.17, 0.042)):
    """The shaft and calyx: green cladding, 48 vertical panel joints and 2.4 m horizontal joints."""
    m, nt, out = new_mat(name)
    tc = nd(nt, "ShaderNodeTexCoord")
    x, y, z = sep(nt, tc.outputs["Object"])
    ang = M(nt, "ARCTAN2", y, x)
    fa = M(nt, "FRACT", M(nt, "MULTIPLY", ang, 48 / (2 * math.pi)))
    seam = M(nt, "MAXIMUM", M(nt, "LESS_THAN", fa, 0.04), M(nt, "LESS_THAN", M(nt, "FRACT", M(nt, "DIVIDE", z, 2.4)), 0.025))
    b = nd(nt, "ShaderNodeBump", {"Strength": 0.35, "Distance": 0.05})
    nt.links.new(M(nt, "SUBTRACT", 1.0, seam), b.inputs["Height"])
    tone = maprange(nt, noise_t(nt, tc.outputs["Object"], 0.08, 3, 0.5), 0.3, 0.7, 0.9, 1.08)
    c = mix(nt, 1.0, (*color, 1), tone, "MULTIPLY")
    c = mix(nt, M(nt, "MULTIPLY", seam, 0.5), c, (0.01, 0.12, 0.03, 1))
    p = principled(nt, c, 0.32, 0.0, coat=0.3, normal=b.outputs[0])
    nt.links.new(p.outputs[0], out.inputs[0])
    if NIGHT and name == "tower_calyx":     # green LED strips on the panel joints over a dimly lit green body
        e = M(nt, "ADD", M(nt, "MULTIPLY", seam, float(pf.arg("calyxk", 1.2))), 0.30)
        add_emission(m, (0.10, 1.0, 0.22), M(nt, "MULTIPLY", e, facing_k(nt, 0.6)))
    elif NIGHT:                     # floodlit from the podium: bright at the foot, fading up, darker toward the sides
        fl = M(nt, "ADD", 0.18, M(nt, "MULTIPLY", M(nt, "EXPONENT", M(nt, "DIVIDE", z, -55.0)), 1.6))
        fl = M(nt, "MULTIPLY", fl, M(nt, "ADD", 1.0, M(nt, "MULTIPLY", seam, 0.6)))
        add_emission(m, (0.55, 0.95, 0.70), M(nt, "MULTIPLY", M(nt, "MULTIPLY", fl, float(pf.arg("shaftk", 0.6))), facing_k(nt, 0.75)))
    return m


BUD_SHOW = [(0.55, 0.12, 1.0), (1.0, 0.04, 0.10), (1.0, 0.85, 0.55), (0.10, 1.0, 0.15), (0.10, 0.95, 0.85), (0.10, 0.30, 1.0),
            (0.75, 0.10, 1.0), (1.0, 0.05, 0.35), (1.0, 0.55, 0.40), (0.35, 1.0, 0.10), (0.15, 1.0, 0.65), (0.15, 0.55, 1.0),
            (0.40, 0.10, 1.0), (1.0, 0.10, 0.85), (1.0, 0.06, 0.06), (1.0, 0.92, 0.30)]


def bud_colour(t, step=1.1, fade=0.35):
    """The bud's colour at time t: holds each colour `step` s, cross-fades over `fade` s."""
    k = int(t / step)
    u = min(max((t - k * step - (step - fade)) / fade, 0.0), 1.0)
    a, b = BUD_SHOW[k % len(BUD_SHOW)], BUD_SHOW[(k + 1) % len(BUD_SHOW)]
    return (*(a[i] + (b[i] - a[i]) * u for i in range(3)), 1.0)


def mat_petal():
    """The bud's petals: magenta glazed panels between mullions and transoms, light frames and ridge (UV: u across, v along)."""
    m, nt, out = new_mat("petal")
    uv = nd(nt, "ShaderNodeUVMap", uv_map="UVMap")
    u, v, _ = sep(nt, uv.outputs[0])
    uc = M(nt, "MULTIPLY", M(nt, "SUBTRACT", u, 0.5), 2.0)
    g1 = M(nt, "FRACT", M(nt, "MULTIPLY", uc, 3.0))                 # meridian mullions
    g2 = M(nt, "FRACT", M(nt, "MULTIPLY", v, 9.0))                  # horizontal transoms
    lat = M(nt, "MAXIMUM", M(nt, "LESS_THAN", g1, 0.05), M(nt, "LESS_THAN", g2, 0.06))
    rim = M(nt, "GREATER_THAN", M(nt, "ABSOLUTE", uc), 0.86)        # the thick light frame of each petal
    vein = M(nt, "LESS_THAN", M(nt, "ABSOLUTE", uc), 0.035)         # the ridge
    lines = M(nt, "MAXIMUM", M(nt, "MAXIMUM", M(nt, "MULTIPLY", lat, 0.35), rim), M(nt, "MULTIPLY", vein, 0.7))
    wn = nd(nt, "ShaderNodeTexWhiteNoise", noise_dimensions="2D")
    nt.links.new(comb(nt, M(nt, "FLOOR", M(nt, "MULTIPLY", uc, 3.0)), M(nt, "FLOOR", M(nt, "MULTIPLY", v, 9.0)), 0.0),
                 wn.inputs["Vector"])
    oi = nd(nt, "ShaderNodeObjectInfo")
    panel = mix(nt, wn.outputs["Value"], (0.36, 0.035, 0.10, 1), (0.60, 0.08, 0.20, 1))
    panel = mix(nt, maprange(nt, v, 0.0, 1.0, 0.25, 0.0), panel, (0.22, 0.02, 0.07, 1))
    c = mix(nt, lines, panel, (0.88, 0.30, 0.45, 1))
    b = nd(nt, "ShaderNodeBump", {"Strength": 0.4, "Distance": 0.04})
    nt.links.new(lines, b.inputs["Height"])
    metal = M(nt, "MULTIPLY", M(nt, "SUBTRACT", 1.0, M(nt, "MINIMUM", M(nt, "MULTIPLY", lines, 2.0), 1.0)), 0.55)
    p = principled(nt, c, M(nt, "ADD", M(nt, "MULTIPLY", lines, 0.35), 0.05), metal, coat=0.2, normal=b.outputs[0])
    nt.links.new(p.outputs[0], out.inputs[0])
    if NIGHT:                       # the bud's LED show (the tower's own video): one saturated colour at a time, cycling,
        rgb = nt.nodes.new("ShaderNodeRGB")         # the lattice a little lighter than the glass
        pf.TIMED.append((rgb.outputs[0], bud_colour))
        ecol = mix(nt, M(nt, "MULTIPLY", M(nt, "MINIMUM", M(nt, "MULTIPLY", lines, 2.0), 1.0), 0.3), rgb.outputs[0], (1.0, 1.0, 1.0, 1))
        glass = M(nt, "MULTIPLY", M(nt, "ADD", 0.45, M(nt, "MULTIPLY", wn.outputs["Value"], 0.55)),     # panel to panel
                  maprange(nt, v, 0.0, 1.0, 1.0, 0.55))                                               # brighter low
        e = M(nt, "ADD", M(nt, "MULTIPLY", lines, float(pf.arg("budline", 3.0))), M(nt, "MULTIPLY", glass, float(pf.arg("budk", 0.7))))
        add_emission(m, ecol, M(nt, "MULTIPLY", e, facing_k(nt, 0.55)))
    return m


def mat_mast():
    """The square mast: tan concrete with tall recessed panels (darker joints)."""
    m, nt, out = new_mat("mast")
    tc = nd(nt, "ShaderNodeTexCoord")
    x, y, z = sep(nt, tc.outputs["Object"])
    h = M(nt, "ADD", x, y)
    lines = M(nt, "MAXIMUM", M(nt, "LESS_THAN", M(nt, "FRACT", M(nt, "DIVIDE", h, 1.6)), 0.12),
              M(nt, "LESS_THAN", M(nt, "FRACT", M(nt, "DIVIDE", z, 4.0)), 0.04))
    c = mix(nt, lines, (0.42, 0.36, 0.26, 1), (0.20, 0.17, 0.13, 1))
    b = nd(nt, "ShaderNodeBump", {"Strength": 0.5, "Distance": 0.08})
    nt.links.new(M(nt, "SUBTRACT", 1.0, lines), b.inputs["Height"])
    p = principled(nt, c, 0.6, normal=b.outputs[0])
    nt.links.new(p.outputs[0], out.inputs[0])
    if NIGHT:                       # the spire glowing gold
        add_emission(m, (1.0, 0.42, 0.04), M(nt, "MULTIPLY", M(nt, "ADD", float(pf.arg("mastk", 1.6)), M(nt, "MULTIPLY", lines, 1.5)), facing_k(nt, 0.6)))
    return m


def mat_glass(name, color, mull=3.0):
    """Podium curtain wall: tinted glass between vertical mullions."""
    m, nt, out = new_mat(name)
    tc = nd(nt, "ShaderNodeTexCoord")
    x, y, z = sep(nt, tc.outputs["Object"])
    ang = M(nt, "ARCTAN2", y, x)
    fa = M(nt, "FRACT", M(nt, "MULTIPLY", ang, 80 / (2 * math.pi)))
    fz = M(nt, "FRACT", M(nt, "DIVIDE", z, mull))
    ml = M(nt, "MAXIMUM", M(nt, "LESS_THAN", fa, 0.08), M(nt, "LESS_THAN", fz, 0.06))
    gp = principled(nt, color, 0.04, 0.0, spec=0.9)
    mp = principled(nt, (0.6, 0.62, 0.64), 0.4, 0.8)
    ms = nd(nt, "ShaderNodeMixShader")
    put(nt, ms.inputs[0], ml)
    nt.links.new(gp.outputs[0], ms.inputs[1])
    nt.links.new(mp.outputs[0], ms.inputs[2])
    nt.links.new(ms.outputs[0], out.inputs[0])
    return m


# ---------------------------------------------------------------- the tower
# bud profile (r, z), measured on the close-ups (user's daylight and sunset crops, lotus/image copy 10.png): the
# green cup sits wide on the upper ring (r 10.4 at 199.2 m), widest r 19 m about 55% up, petals end at 250.7 m (r 12.5),
# then a grey glazed cone to the drums. Height / width about 1.35.
BUD = [(7.6, 198.6), (10.45, 199.20), (11.78, 202.29), (13.68, 206.92), (15.96, 212.07), (17.67, 217.22), (18.62, 222.38), (19.00, 227.52), (18.81, 232.67), (18.05, 237.82), (16.72, 242.97), (14.82, 247.09), (12.54, 250.70)]
NP = 10                      # sepals and petals per tier


def bud_r(z):
    if z <= BUD[0][1]:
        return BUD[0][0]
    for (r0, z0), (r1, z1) in zip(BUD, BUD[1:]):
        if z0 <= z <= z1:
            return r0 + (r1 - r0) * (z - z0) / max(z1 - z0, 1e-6)
    return BUD[-1][0]


def petals(bm, uvl, n, phase, half_w, z0, z1, off0, off1, ridge, mat, kind="gothic", nu=12, nv=22, flare=0.0):
    """n leaf shells round the bud. u across (-1..1), t along (0 base .. 1 tip). gothic: pointed arch;
    sepal: rounded lobe. The offset from the bud surface ramps from off0 to off1 over the lower third."""
    for k in range(n):
        phi = phase + 2 * math.pi * k / n
        rows = []
        for i in range(nv + 1):
            t = i / nv
            z = z0 + (z1 - z0) * t
            if kind == "gothic":
                w = half_w * max(1 - t ** 2.6, 0.0) ** 0.62
            else:
                w = half_w * max(1 - t ** 2.6, 0.0) ** 0.5
            ramp_ = min(t / 0.35, 1.0)
            off = off0 + (off1 - off0) * (3 * ramp_ ** 2 - 2 * ramp_ ** 3) + flare * t ** 3
            row = []
            for j in range(nu + 1):
                u = -1 + 2 * j / nu
                r = bud_r(z) + off + ridge * (1 - abs(u)) * (1 - t) ** 0.5
                a = phi + u * w
                row.append((bm.verts.new((r * math.cos(a), r * math.sin(a), z)), u, t))
            rows.append(row)
        for i in range(nv):
            for j in range(nu):
                q = (rows[i][j], rows[i][j + 1], rows[i + 1][j + 1], rows[i + 1][j])
                f = bm.faces.new([x[0] for x in q])
                f.material_index = mat
                for loop, x in zip(f.loops, q):
                    loop[uvl].uv = ((x[1] + 1) / 2, x[2])


def railing(bm, r, z, h=1.1, n=96, mat=0):
    """A balcony railing: posts and a top rail."""
    for k in range(n):
        a = 2 * math.pi * k / n
        beam(bm, (r * math.cos(a), r * math.sin(a), z), (r * math.cos(a), r * math.sin(a), z + h), 0.08, mat=mat)
    lathe(bm, [(r - 0.05, z + h - 0.06), (r + 0.05, z + h - 0.06), (r + 0.05, z + h), (r - 0.05, z + h)], seg=n, mat=mat)


def tower():
    T = Vector((0.0, 0.0, 0.0))
    green = mat_tower_green()
    calyx = mat_tower_green("tower_calyx", (0.008, 0.13, 0.065))
    petal = mat_petal()
    core = simple_mat("bud_core", (0.14, 0.008, 0.04), 0.15, 0.2, coat=0.3)
    if NIGHT:
        add_emission(core, (1.0, 0.45, 0.55), 0.35)
    white = simple_mat("tower_white", (0.78, 0.78, 0.76), 0.35, bump=0.1)
    grey = simple_mat("tower_grey", (0.50, 0.52, 0.52), 0.4, 0.3)
    mast = simple_mat("tower_mast", (0.44, 0.40, 0.33), 0.45, 0.2, bump=0.2)
    roofm = simple_mat("podium_roof", (0.55, 0.53, 0.48), 0.8, bump=0.2, bscale=0.8)     # pale concrete (drone photo)
    glass_lo = mat_glass("podium_glass_lo", (0.07, 0.22, 0.50), 4.3)     # photo: bright blue lower band
    glass_hi = mat_glass("podium_glass_hi", (0.11, 0.17, 0.18), 2.8)     # photo: grey-teal, reflecting the sky
    if NIGHT:
        add_emission(glass_lo, (0.45, 0.6, 1.0), 2.2)
        add_emission(glass_hi, (1.0, 0.78, 0.5), 1.8)
        add_emission(white, (1.0, 0.97, 0.92), 1.0)

    # podium: two inverted cones of glass, a white scalloped rim (white lotus petals), a flat roof
    bm = bmesh.new()
    lathe(bm, [(33.5, 0.0), (37.6, 8.6)], mat=0)
    lathe(bm, [(37.6, 8.6), (36.4, 8.6), (36.4, 9.4)], mat=2)
    lathe(bm, [(36.4, 9.4), (40.4, 17.6)], mat=1)
    lathe(bm, [(40.4, 17.6), (41.4, 17.8), (41.4, 20.6), (40.6, 20.9)], mat=2)     # the roof disc is its own object (no coplanar twin)
    for k in range(132):
        a = 2 * math.pi * k / 132
        m = (Matrix.Translation((41.6 * math.cos(a), 41.6 * math.sin(a), 18.6)) @ Matrix.Rotation(a, 4, "Z")
             @ Matrix.Diagonal((0.45, 0.95, 1.2, 1)))
        r = bmesh.ops.create_uvsphere(bm, u_segments=10, v_segments=6, radius=1.0, matrix=m)
        for f in {f for v in r["verts"] for f in v.link_faces}:
            f.material_index = 2
    for a, rr, s in ((0.3, 22, (7, 5, 3.2)), (1.9, 24, (6, 6, 3.0)), (3.4, 21, (8, 5, 3.4)), (4.8, 23, (5, 7, 3.0)),
                     (5.6, 30, (4, 3, 2.2))):        # rooftop plant rooms
        cube(bm, (rr * math.cos(a), rr * math.sin(a), 20.9 + s[2] / 2), s, a, mat=2)
    mesh_obj("podium", bm, [glass_lo, glass_hi, white], loc=T)
    bm = bmesh.new()
    lathe(bm, [(40.6, 20.92), (13.6, 20.92)], mat=0)
    mesh_obj("podium_roof", bm, [roofm], loc=T)
    # roof garden (drone photo): square planters with shrubs scattered between the plant rooms
    bm = bmesh.new()
    prng = random.Random(41)
    for k in range(46):
        a, r = prng.uniform(0, 6.283), prng.uniform(17.5, 38.0)
        if any(abs(a - aa) < 0.35 and abs(r - rr) < 6 for aa, rr, _ in ((0.3, 22, 0), (1.9, 24, 0), (3.4, 21, 0), (4.8, 23, 0), (5.6, 30, 0))):
            continue
        cube(bm, (r * math.cos(a), r * math.sin(a), 21.3), (1.3, 1.3, 0.7), a, mat=0)
        sp = bmesh.ops.create_icosphere(bm, subdivisions=2, radius=0.8, matrix=Matrix.Translation((r * math.cos(a), r * math.sin(a), 22.2)) @ Matrix.Diagonal((1.0, 1.0, 0.85, 1.0)))
        for f in {f for v in sp["verts"] for f in v.link_faces}:
            f.material_index = 1
    mesh_obj("roof_garden", bm, [simple_mat("planter", (0.32, 0.31, 0.29), 0.8), look.mat_leaves("lm_leaves")], loc=T)

    # shaft: a flared skirt on the podium roof, then a straight taper to the neck
    bm = bmesh.new()
    lathe(bm, [(14.2, 20.9), (12.9, 25.0), (12.2, 30.0), (7.6, 198.6)], seg=160)
    mesh_obj("shaft", bm, [green], smooth=True, loc=T)
    # two balcony rings under the calyx
    bm = bmesh.new()
    for z, r0, r1 in ((190.7, 7.7, 10.2), (198.2, 7.6, 9.7)):
        lathe(bm, [(r0, z - 0.45), (r1, z - 0.45), (r1, z + 0.15), (r0, z + 0.15)], seg=160)
        railing(bm, r1 - 0.15, z + 0.15, 1.1, 120)
    mesh_obj("rings", bm, [grey], loc=T)

    # bud: core (green cup below, dark glass above), a green cup of ten rounded lobes, three tiers of ten
    # faceted mirror-glass petals (flat panels: the patchy reflections of the real glazing)
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new("UVMap")
    zc = 214.0
    lathe(bm, [p for p in BUD if p[1] <= zc] + [(bud_r(zc), zc)], seg=160, mat=1)
    lathe(bm, [(bud_r(zc), zc)] + [p for p in BUD if p[1] > zc], seg=160, mat=2)
    for f in bm.faces:
        for loop in f.loops:
            loop[uvl].uv = (0.5, 0.05)
    hw = math.pi / NP * 1.03
    petals(bm, uvl, NP, math.pi / NP, hw * 1.08, 209.0, 232.0, 0.0, 1.4, 1.5, 0, nu=6, nv=10, flare=0.8)   # tier 1
    petals(bm, uvl, NP, 0.0, hw, 216.0, 240.6, 0.0, 0.85, 1.2, 0, nu=6, nv=10, flare=1.0)          # tier 2
    petals(bm, uvl, NP, math.pi / NP, hw, 228.0, 252.6, 0.0, 0.45, 0.9, 0, nu=6, nv=10, flare=1.8) # tier 3 crown
    petals(bm, uvl, NP, 0.0, math.pi / NP * 1.04, 199.6, 225.0, 0.0, 2.2, 0.0, 1, kind="sepal", nv=14)  # cup lobes (outermost)
    bo = mesh_obj("bud", bm, [petal, calyx, core], smooth=False, loc=T)
    s = bo.modifiers.new("thick", "SOLIDIFY")
    s.thickness = 0.3
    s.offset = -1.0
    bm = bmesh.new()
    lathe(bm, [(12.4, 250.4), (9.5, 255.3), (0.5, 255.4)], seg=160)
    mesh_obj("bud_top", bm, [mat_glass("bud_top_glass", (0.05, 0.05, 0.055), 1.2)], loc=T)

    # cap: a white drum with a balcony, a narrower white drum with a railing
    bm = bmesh.new()
    lathe(bm, [(9.5, 255.3), (9.5, 261.0), (10.0, 261.0), (10.0, 261.3), (7.7, 261.3)], seg=128, mat=0)
    railing(bm, 9.85, 261.3, 1.1, 110, mat=1)
    lathe(bm, [(7.7, 261.3), (7.7, 267.8), (8.1, 267.8), (8.1, 268.1), (3.0, 268.1)], seg=128, mat=0, cap_top=True)
    railing(bm, 7.95, 268.1, 1.1, 90, mat=1)
    for z, r in ((258.2, 9.52), (264.5, 7.72)):
        lathe(bm, [(r, z - 0.12), (r, z + 0.12)], seg=128, mat=1)
    mesh_obj("cap", bm, [white, grey], smooth=False, loc=T)
    # mast: square, 6.6 m tapering to 5.8 m, recessed panels, a wider block on top; then the round white antenna
    bm = bmesh.new()
    lathe(bm, [(4.67, 268.1), (4.10, 296.8), (5.0, 296.8), (5.0, 299.4), (1.2, 299.5)], seg=4, mat=0, cap_top=True)
    mo = mesh_obj("mast", bm, [mat_mast()], loc=T)
    mo.rotation_euler = (0, 0, math.radians(45 + 8.5))
    bm = bmesh.new()
    lathe(bm, [(1.05, 299.4), (0.9, 315.0), (0.72, 330.0), (1.0, 330.2), (1.0, 331.2), (0.55, 331.4), (0.38, 345.0),
               (0.16, 351.5)], seg=32, mat=0, cap_top=True)
    mesh_obj("antenna", bm, [white], smooth=True, loc=T)

    # plaza and gardens round the podium
    pave = pf.tex_mat("pave", "concrete_pavers", 3.0, (1.0, 0.98, 0.95), (0.36, 0.34, 0.31))
    lawn = simple_mat("lawn", (0.05, 0.13, 0.025), 0.9, bump=0.3, bscale=3.0)
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=True, segments=96, radius=54.0,
                            matrix=Matrix.Translation((0, 0, 0.08)))
    mesh_obj("plaza", bm, [pave], loc=T)

def build(mp):
    import bpy
    before = set(bpy.data.objects)
    tower()
    for o in bpy.data.objects:
        if o not in before:
            o.rotation_euler.z += TURN
    # the viewer cannot run these node shaders: give each an honest average colour
    for name, col, rough, metal in (("petal", (0.50, 0.06, 0.16), 0.15, 0.5), ("tower_green", (0.004, 0.17, 0.042), 0.32, 0.0),
                                    ("tower_calyx", (0.008, 0.13, 0.065), 0.32, 0.0), ("mast", (0.42, 0.36, 0.26), 0.6, 0.0),
                                    ("podium_glass_lo", (0.07, 0.22, 0.50), 0.06, 0.2), ("podium_glass_hi", (0.11, 0.17, 0.18), 0.06, 0.2),
                                    ("bud_top_glass", (0.05, 0.05, 0.055), 0.06, 0.2), ("lm_leaves", (0.09, 0.16, 0.035), 0.8, 0.0)):
        if name in bpy.data.materials:
            pf.viewer_color(bpy.data.materials[name], col, rough, metal)
    for name, col, k in (("petal", (1.0, 0.10, 0.45), 1.6), ("tower_green", (0.35, 0.95, 0.55), 0.35), ("tower_calyx", (0.10, 1.0, 0.22), 0.8),
                         ("mast", (1.0, 0.42, 0.04), 1.4), ("tower_white", (1.0, 0.97, 0.92), 0.8), ("podium_glass_lo", (0.45, 0.6, 1.0), 1.2),
                         ("podium_glass_hi", (1.0, 0.78, 0.5), 1.0)):
        if name in bpy.data.materials:
            pf.viewer_emission(bpy.data.materials[name], col, k * 0.22)      # low: saturated light goes white
    return {"height": 351.5}

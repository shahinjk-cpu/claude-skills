"""placeforge engine, Blender -> Three.js. Writes <project>/web/data/scene.json + scene.bin.gz for viewer/build.py.

What travels is the generator's output, not heavy meshes:
    boxes   17 float32 per generated building (the viewer rebuilds walls, hipped roofs, windows in its shader)
    polys   mapped footprints as triangles: position 3, colour 3, roof, glass, rnd per vertex
    trees   x, y, scale, kind, rotation per tree (the viewer instances its own tree shapes)
    lamps   x, y, rotation
    meshes  everything else (roads, water, areas, bridges, the landmark) as triangles with normals, grouped by
            material; each material's Principled constants (colour, roughness, metallic, emission) go in the JSON.
A landmark's procedural shader detail does not travel: give its materials honest constant colours, or accept flat ones.
"""
import bpy, gzip, json, os, struct
from array import array
from mathutils import Vector
import pf_core as pf
import pf_cam as cam
from pf_core import cfg

SKIP = ("city", "trees", "street_lamps", "haze", "clouds_high", "clouds_low", "ground", "sun", "cam")


def mat_info(m, obj_name):
    d = {"name": m.name if m else "none", "color": [0.5, 0.5, 0.5], "rough": 0.8, "metal": 0.0, "emit": [0, 0, 0], "alpha": 1.0}
    if not m:
        return d
    d["color"] = [round(c, 4) for c in m.diffuse_color[:3]]
    nt = m.node_tree
    p = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None) if nt else None
    if p:
        bc = p.inputs["Base Color"]
        if not bc.links:
            d["color"] = [round(c, 4) for c in bc.default_value[:3]]
        for key, nm, fb in (("rough", "Roughness", m.roughness), ("metal", "Metallic", m.metallic), ("alpha", "Alpha", 1.0)):
            if nm in p.inputs:
                d[key] = round(float(fb if p.inputs[nm].links else p.inputs[nm].default_value), 3)
        if "Emission Strength" in p.inputs and not p.inputs["Emission Strength"].links and not p.inputs["Emission Color"].links:
            s = float(p.inputs["Emission Strength"].default_value)
            d["emit"] = [round(c * s, 3) for c in p.inputs["Emission Color"].default_value[:3]]
    e = next((n for n in nt.nodes if n.type == "EMISSION"), None) if nt else None
    if e and not e.inputs["Color"].links and not e.inputs["Strength"].links:
        s = float(e.inputs["Strength"].default_value)
        d["emit"] = [round(c * min(s, 8.0), 3) for c in e.inputs["Color"].default_value[:3]]
        if not p:
            d["color"] = [0.02, 0.02, 0.02]
    if "pf_emit" in m:
        d["emit"] = [round(float(c), 3) for c in m["pf_emit"]]
    nm = (m.name + " " + obj_name).lower()
    d["kind"] = "water" if any(k in nm for k in ("water", "sea", "pool", "lake")) and "shore" not in nm else \
        "grass" if any(k in nm for k in ("grass", "woodland", "farmland", "island")) else "glass" if "glass" in nm else "solid"
    return d


def export(mp, B, trees, H, life=None):
    out = os.path.join(pf.PROJECT, "web", "data")
    os.makedirs(out, exist_ok=True)
    buf = bytearray()
    chunks = {}

    def put(name, floats, stride):
        a = array("f", floats)
        chunks[name] = {"off": len(buf), "n": len(a) // stride, "stride": stride}
        buf.extend(a.tobytes())

    put("boxes", [x for p in B.params for x in p], 17)
    pv = []
    from mathutils.geometry import tessellate_polygon
    for h, z0, wr, wg, wb, rr, rg, rb, glass, rnd, flat in B.polys:
        pts = [(flat[i], flat[i + 1]) for i in range(0, len(flat), 2)]
        n = len(pts)
        for i in range(n):
            (x0, y0), (x1, y1) = pts[i], pts[(i + 1) % n]
            for x, y, z in ((x0, y0, z0), (x1, y1, z0), (x1, y1, z0 + h), (x0, y0, z0), (x1, y1, z0 + h), (x0, y0, z0 + h)):
                pv += [x, y, z, wr, wg, wb, 0.0, glass, rnd]
        for t in tessellate_polygon([[Vector((x, y, 0.0)) for x, y in pts]]):
            (x0, y0), (x1, y1), (x2, y2) = (pts[k] for k in t)
            if (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0) < 0:
                t = t[::-1]
            for k in t:
                pv += [pts[k][0], pts[k][1], z0 + h, rr, rg, rb, 1.0, 0.0, rnd]
    put("polys", pv, 9)
    put("trees", [v for t in trees for v in (t[0], t[1], t[3], t[4], t[5])], 5)
    put("lamps", [v for t in getattr(mp, "lamps", []) for v in (t[0], t[1], t[5])], 3)
    dg = bpy.context.evaluated_depsgraph_get()
    meshes = []
    for o in bpy.context.scene.objects:
        if o.type != "MESH" or o.name in SKIP or o.name.startswith(("ll", "life_", "pf_tmp")) or not o.visible_get():
            continue
        if any(md.type == "NODES" for md in o.modifiers):
            continue
        me = o.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles()
        if not me.loop_triangles:
            continue
        mw = o.matrix_world
        nm = mw.to_3x3().inverted_safe().transposed()
        by_mat = {}
        vs = me.vertices
        for t in me.loop_triangles:
            L = by_mat.setdefault(t.material_index, [])
            for k in range(3):
                co = mw @ vs[t.vertices[k]].co
                n = (nm @ Vector(t.split_normals[k] if t.use_smooth else t.normal)).normalized()
                L += [co.x, co.y, co.z, n[0], n[1], n[2]]
        groups = []
        for mi in sorted(by_mat):
            m = me.materials[mi] if mi < len(me.materials) else None
            a = array("f", by_mat[mi])
            groups.append({"mat": mat_info(m, o.name), "off": len(buf), "n": len(a) // 6})
            buf.extend(a.tobytes())
        meshes.append({"name": o.name, "groups": groups})
        o.evaluated_get(dg).to_mesh_clear()
    lf = None
    if life:
        lf = life.export()

        def blob(a):
            off = len(buf)
            buf.extend(a.tobytes())
            return {"off": off, "n": len(a) // 9}

        for p in lf["protos"]:
            p["soup"] = blob(p["soup"])
        lf["people"] = [[blob(a) for a in poses] for poses in lf["people"]]
        if lf["heli"]:
            lf["heli"]["soups"] = [blob(a) for a in lf["heli"]["soups"]]
        for k in ("cars", "parked", "walkers", "trains"):
            lf[k] = [round(float(v), 3) for v in lf[k]]
    pose = cam.photo_pose()
    meta = {"name": cfg("name"), "radius": mp.R, "far": mp.FR, "height": H, "floor": cfg("region.floor_m", 3.2),
            "attribution": "Map data (c) OpenStreetMap contributors", "links": cfg("web.links") or None, "views": cam.views(mp, H),
            "photo": {"from": list(pose[0]), "bearing": pose[1], "lens": pose[2]} if pose else None,
            "sun": {"elevation": cfg("time.day.sun_elevation"), "bearing": cfg("time.day.sun_bearing"),
                    "sunset_bearing": cfg("time.sunset.sun_bearing")},
            "water": cfg("region.water"), "sea": cfg("region.sea"), "chunks": chunks, "meshes": meshes,
            "tree_kinds": ["broad", "round", "tall", "palm", "conifer"], "life": lf}
    json.dump(meta, open(os.path.join(out, "scene.json"), "w"), separators=(",", ":"))
    with gzip.open(os.path.join(out, "scene.bin.gz"), "wb", 6) as f:
        f.write(bytes(buf))
    pf.log("EXPORTED web data: %d boxes, %d footprint vertices, %d trees, %d meshes, %.1f MB raw, %.1f MB gz" % (
        len(B.params), len(pv) // 9, len(trees), len(meshes), len(buf) / 1e6, os.path.getsize(os.path.join(out, "scene.bin.gz")) / 1e6))

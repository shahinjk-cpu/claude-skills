"""Conservative, component-wise print repair; input/output coordinates are mm.

No global voxel remeshing or convex-hull replacement. The returned audit
records capping, local dilation and unresolved disconnected shells. A closed
surface does not itself establish that every feature can print successfully.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import trimesh
import manifold3d as md


def _outward_growth(source_bounds, result_bounds):
    source = np.asarray(source_bounds, dtype=float)
    result = np.asarray(result_bounds, dtype=float)
    if source.shape != (2, 3) or result.shape != (2, 3):
        return float("inf")
    if not np.isfinite(source).all() or not np.isfinite(result).all():
        return float("inf")
    return float(max(0, np.max(source[0]-result[0]), np.max(result[1]-source[1])))


def cache_compatible(audit, target_mm=0.8):
    """Whether a pre-guard repair audit satisfies the new component bound rule.

    The caller must separately match source geometry, target and an explicitly
    approved prior implementation signature. This does not authenticate caches.
    """
    if not isinstance(audit, dict) or abs(audit.get("target_mm", -1)-target_mm) > 1e-9:
        return False
    components = audit.get("components")
    if not isinstance(components, list) or not components:
        return False
    limit = target_mm + 0.10
    return all(isinstance(c, dict) and c.get("source_bounds_mm") is not None
               and c.get("result_bounds_mm") is not None
               and _outward_growth(c["source_bounds_mm"], c["result_bounds_mm"]) <= limit
               for c in components)


def _clean(mesh):
    result = mesh.copy()
    result.merge_vertices(digits_vertex=6)
    result.update_faces(result.unique_faces())
    result.update_faces(result.nondegenerate_faces(height=1e-7))
    result.remove_unreferenced_vertices()
    result.fix_normals(multibody=True)
    return result


def _manifold(mesh):
    # Trimesh may mark cached arrays read-only; the native binding requires
    # writable C-contiguous buffers even though geometry values are unchanged.
    candidate = md.Manifold(md.Mesh64(np.array(mesh.vertices, dtype=np.float64, order="C", copy=True),
                                     np.array(mesh.faces, dtype=np.uint64, order="C", copy=True)))
    if candidate.status() != md.Error.NoError or candidate.is_empty():
        raise ValueError(f"Manifold rejected component: {candidate.status()}")
    return candidate


def _trimesh(solid):
    # 0.0001 mm is far below print resolution but above STL float32 rounding
    # at vehicle-scale coordinates, avoiding microscopic sliver edges.
    result = solid.simplify(1e-4).to_mesh64()
    mesh = trimesh.Trimesh(np.asarray(result.vert_properties[:, :3]),
                          np.asarray(result.tri_verts), process=False)
    mesh.fix_normals(multibody=True)
    return mesh


def _bmesh_cap(mesh):
    import bpy
    import bmesh
    data = bpy.data.meshes.new("print_repair_temporary")
    bm = bmesh.new()
    try:
        data.from_pydata(mesh.vertices.tolist(), [], mesh.faces.tolist())
        bm.from_mesh(data)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)
        edges = [e for e in bm.edges if e.is_boundary]
        if edges:
            bmesh.ops.holes_fill(bm, edges=edges, sides=0)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.to_mesh(data)
        data.update()
        return _clean(trimesh.Trimesh(
            np.array([v.co[:] for v in data.vertices]),
            np.array([f.vertices[:] for f in data.polygons]), process=True))
    finally:
        bm.free()
        bpy.data.meshes.remove(data)


def _solidify(mesh, thickness, *, bounded=False, mode="NON_MANIFOLD"):
    import bpy
    data = bpy.data.meshes.new("print_sheet_temporary")
    obj = None
    try:
        data.from_pydata(mesh.vertices.tolist(), [], mesh.faces.tolist())
        data.update()
        obj = bpy.data.objects.new("print_sheet_temporary", data)
        bpy.context.scene.collection.objects.link(obj)
        mod = obj.modifiers.new("Print wall", "SOLIDIFY")
        mod.solidify_mode = mode
        mod.thickness = float(thickness)
        mod.offset = 0
        mod.use_even_offset = not bounded
        if bounded:
            # CONSTRAINTS compensates acute angles with potentially enormous
            # miters. FIXED keeps the requested normal displacement bounded.
            mod.nonmanifold_thickness_mode = "FIXED"
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        out = evaluated.to_mesh()
        try:
            out.calc_loop_triangles()
            result = _clean(trimesh.Trimesh(
                [v.co[:] for v in out.vertices],
                [t.vertices[:] for t in out.loop_triangles], process=True))
        finally:
            evaluated.to_mesh_clear()
        return result
    finally:
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)
        if data.users == 0:
            bpy.data.meshes.remove(data)


def _local_voxel(mesh, pitch=0.05):
    """Repair only an isolated already-thickened sheet part at fine resolution."""
    import bpy
    data = bpy.data.meshes.new("local_track_repair_temporary")
    obj = None
    try:
        data.from_pydata(mesh.vertices.tolist(), [], mesh.faces.tolist())
        data.update()
        obj = bpy.data.objects.new("local_track_repair_temporary", data)
        bpy.context.scene.collection.objects.link(obj)
        mod = obj.modifiers.new("Local numeric topology repair", "REMESH")
        mod.mode = "VOXEL"
        mod.voxel_size = float(pitch)
        mod.adaptivity = 0.0
        mod.use_smooth_shade = False
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        out = evaluated.to_mesh()
        try:
            out.calc_loop_triangles()
            return _clean(trimesh.Trimesh([v.co[:] for v in out.vertices],
                                         [t.vertices[:] for t in out.loop_triangles], process=True))
        finally:
            evaluated.to_mesh_clear()
    finally:
        if obj:
            bpy.data.objects.remove(obj, do_unlink=True)
        if data.users == 0:
            bpy.data.meshes.remove(data)


def _sample_thickness(mesh, count=96):
    """Inward normal rays; diagnostic sampled thickness, not a proof of minimum."""
    triangles = mesh.triangles
    # Area sampling avoids letting tiny bevels dominate plate-wall estimates.
    weights = mesh.area_faces
    cumulative = np.cumsum(weights)
    probes = np.unique(np.searchsorted(cumulative, (np.arange(count)+0.5)/count*cumulative[-1]))
    edge1 = triangles[:, 1] - triangles[:, 0]
    edge2 = triangles[:, 2] - triangles[:, 0]
    distances = []
    for index in probes:
        direction = -mesh.face_normals[index]
        origin = mesh.triangles_center[index] + direction*1e-5
        h = np.cross(np.broadcast_to(direction, edge2.shape), edge2)
        a = np.einsum("ij,ij->i", edge1, h)
        good = np.abs(a) > 1e-10
        inverse = np.zeros_like(a)
        inverse[good] = 1/a[good]
        s = origin - triangles[:, 0]
        u = inverse*np.einsum("ij,ij->i", s, h)
        q = np.cross(s, edge1)
        v = inverse*np.einsum("j,ij->i", direction, q)
        t = inverse*np.einsum("ij,ij->i", edge2, q)
        good &= (u >= -1e-7) & (v >= -1e-7) & (u+v <= 1+1e-7) & (t > 1e-4)
        if np.any(good):
            distances.append(float(t[good].min()+1e-5))
    if not distances:
        return None
    return {"sample_count":len(distances), "p10_mm":float(np.quantile(distances,.1)),
            "median_mm":float(np.median(distances)), "minimum_sample_mm":min(distances)}


def repair_mesh(trimesh_mesh, target_mm=0.8, label="mesh", *, sheet_first=None):
    """Return a closed repaired mesh and explicit audit, preserving world position.

    Cap missing ends first. Solidify only open components for which capping
    does not produce a valid volume. Closed, structurally thin shells receive
    a small per-component morphological dilation, bounded to target_mm/2.
    Decorative islands smaller than target_mm retain their scale: growing all
    screws/bolts to 0.8 mm would destroy the model's appearance.
    """
    if target_mm <= 0:
        raise ValueError("target_mm must be positive")
    if sheet_first is None:
        # Animated track assets are open ribbons, not incomplete solid blocks.
        # Capping their boundary loops fills the wheel opening with large disks.
        sheet_first = label.startswith("track_") and label.endswith("_mesh")
    source = _clean(trimesh_mesh)
    if len(source.faces) == 0:
        raise ValueError(f"{label}: empty mesh")
    solids = []
    audit = {"label":label, "target_mm":target_mm, "method":"component_caps_and_local_dilation",
             "original_bounds_mm":source.bounds.tolist(), "components":[],
             "global_remesh":False, "minimum_thickness_certified":False,
             "sheet_first_preserve_openings":bool(sheet_first),
             "component_outward_growth_limit_mm":target_mm+0.10}
    face_groups = trimesh.graph.connected_components(source.face_adjacency,
                                                     nodes=np.arange(len(source.faces)))
    # Trimesh.split repairs small holes by default. Keep that operation explicit
    # so the audit accounts for every cap rather than hiding automatic repairs.
    components = source.submesh(face_groups, append=False, repair=False)
    for index, original in enumerate(components):
        component = _clean(original)
        row = {"index":index,"source_faces":len(component.faces),
               "source_watertight":bool(component.is_watertight),
               "source_bounds_mm":component.bounds.tolist(),"actions":[]}
        if not component.is_watertight:
            if sheet_first:
                component = _solidify(component, target_mm)
                row["actions"].append("solidified_open_sheet_preserving_openings")
            else:
                capped = _bmesh_cap(component)
                if capped.is_volume and capped.volume > 1e-8:
                    component = capped
                    row["actions"].append("capped_boundary_loops")
                else:
                    component = _solidify(component, target_mm)
                    row["actions"].append("solidified_open_sheet")
        if not component.is_volume or component.volume <= 1e-8:
            raise ValueError(f"{label} component {index}: no valid positive closed volume after conservative repair")
        solid = _manifold(component)
        thickness = _sample_thickness(component)
        row["sampled_thickness_before"] = thickness
        # Small decorative details are retained, not enlarged into blobs.
        structural = float(max(component.extents)) >= 2*target_mm
        extents = np.sort(component.extents)
        preserved_rod = bool(component.is_watertight and extents[0] >= target_mm
                             and extents[2] / max(extents[1], 1e-8) > 10)
        if sheet_first:
            row["actions"].append("preserved_track_sheet_thickness")
        elif preserved_rod:
            row["actions"].append("retained_closed_rod_at_target_width")
        elif structural and thickness and thickness["p10_mm"] < target_mm-0.03:
            radius = min(target_mm/2, max(0, (target_mm-thickness["p10_mm"])/2))
            if radius > 0.015:
                solid = solid.minkowski_sum(md.Manifold.sphere(radius, 16))
                if solid.status() != md.Error.NoError or solid.is_empty():
                    raise ValueError(f"{label} component {index}: local thickness dilation failed")
                row["actions"].append("local_minkowski_thickening")
                row["dilation_radius_mm"] = radius
        elif not structural:
            row["actions"].append("retained_small_decorative_detail")
        repaired = _trimesh(solid)
        growth_limit = target_mm+0.10
        growth = _outward_growth(original.bounds, repaired.bounds)
        if growth > growth_limit:
            rejected = {"actions":list(row["actions"]),
                        "bounds_mm":repaired.bounds.tolist(),"outward_growth_mm":growth}
            recovered = None
            errors = []
            for solidify_mode in ("NON_MANIFOLD", "EXTRUDE"):
                try:
                    candidate = _solidify(original, target_mm, bounded=True, mode=solidify_mode)
                    if not candidate.is_volume:
                        raise ValueError("bounded sheet is not a positive closed volume")
                    candidate_solid = _manifold(candidate)
                    candidate_mesh = _trimesh(candidate_solid)
                    candidate_growth = _outward_growth(original.bounds, candidate_mesh.bounds)
                    if candidate_growth > growth_limit:
                        raise ValueError(f"bounded sheet exceeds limit: {candidate_growth}")
                    recovered = (candidate_solid, candidate_mesh, candidate_growth, solidify_mode)
                    break
                except (ValueError, RuntimeError) as error:
                    errors.append(f"{solidify_mode}: {error}")
            if recovered is None:
                raise ValueError(f"{label} component {index}: outward growth {growth:.6f} mm "
                                 f"exceeds {growth_limit:.6f} mm; bounded fallback failed: {errors}")
            solid, repaired, growth, used_mode = recovered
            row["rejected_unbounded_result"] = rejected
            row["actions"] = ["bounded_fixed_thickness_fallback"]
            row["bounded_solidify_mode"] = used_mode
            row["bounded_fallback_attempt_errors"] = errors
            row.pop("dilation_radius_mm", None)
        row["outward_growth_mm"] = growth
        row["result_bounds_mm"] = repaired.bounds.tolist()
        row["result_faces"] = len(repaired.faces)
        row["result_volume_mm3"] = float(repaired.volume)
        row["result_watertight"] = bool(repaired.is_watertight)
        solids.append(solid)
        audit["components"].append(row)
    united = md.Manifold.batch_boolean(solids, md.OpType.Add)
    if united.status() != md.Error.NoError or united.is_empty():
        raise ValueError(f"{label}: exact component union failed: {united.status()}")
    result = _trimesh(united)
    unquantized = result.copy()
    # STL stores coordinates as float32. Resolve sliver triangles that collapse
    # during that conversion now, then verify the actual deliverable topology.
    prior_faces = len(result.faces)
    result = trimesh.Trimesh(result.vertices.astype(np.float32), result.faces, process=True)
    result.update_faces(result.nondegenerate_faces())
    result.update_faces(result.unique_faces())
    result.remove_unreferenced_vertices()
    result.fix_normals(multibody=True)
    audit["stl_quantization_degenerate_faces_removed"] = prior_faces-len(result.faces)
    if not result.is_volume and sheet_first:
        # The source's nearly coplanar animated ribbons can create micron-scale
        # slivers during exact union. This fallback is restricted to the track
        # sheet object; wheels, suspension, hull and other objects are untouched.
        voxel = _local_voxel(unquantized, pitch=0.05)
        dense_faces = len(voxel.faces)
        voxel = _trimesh(_manifold(voxel).simplify(0.01))
        result = trimesh.Trimesh(voxel.vertices.astype(np.float32), voxel.faces, process=True)
        result.update_faces(result.nondegenerate_faces())
        result.remove_unreferenced_vertices()
        result.fix_normals(multibody=True)
        audit["localized_voxel_fallback"] = {
            "reason":"track_union_micro_slivers_after_stl_float32_quantization",
            "pitch_mm":0.05,"scope":"this_track_sheet_object_only",
            "bounded_simplification_tolerance_mm":0.01,"dense_voxel_faces":dense_faces,
            "input_faces":len(unquantized.faces),"output_faces":len(result.faces),
            "maximum_bounds_change_from_thickened_mm":float(np.abs(result.bounds-unquantized.bounds).max()),
        }
    if not result.is_volume:
        error = ValueError(f"{label}: final mesh is not a consistently oriented closed volume "
                           f"(watertight={result.is_watertight}, winding={result.is_winding_consistent}, "
                           f"volume={result.volume}, euler={result.euler_number})")
        error.mesh = result
        error.unquantized_mesh = unquantized
        error.audit = audit
        raise error
    audit.update(result_bounds_mm=result.bounds.tolist(), result_faces=len(result.faces),
                 result_volume_mm3=float(result.volume), result_watertight=bool(result.is_watertight),
                 result_components=len(result.split(only_watertight=False)),
                 maximum_bounds_change_mm=float(np.abs(result.bounds-source.bounds).max()))
    audit["requires_attachment_review"] = audit["result_components"] > 1
    return result, audit


def probe(blend_path, output, names):
    import bpy
    from inspect_scene import world_mesh
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.open_mainfile(filepath=str(Path(blend_path).resolve()))
    reports = []
    for name in names:
        source = world_mesh(bpy.data.objects[name])
        source.apply_scale(1000/72)
        source.export(output/f"{name}_source.stl")
        result, audit = repair_mesh(source, label=name)
        result.export(output/f"{name}_repaired.stl")
        (output/f"{name}_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
        reports.append({k:audit[k] for k in ["label","result_watertight","result_components",
                        "result_volume_mm3","maximum_bounds_change_mm"]})
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--names", nargs="+", default=["ex_armor_turret_l_06","gun_barrel_01"])
    args = parser.parse_args()
    probe(args.blend, args.output, args.names)

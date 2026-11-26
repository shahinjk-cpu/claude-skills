"""Recipe-driven (schema 2) printable-part builder for arbitrary ground vehicles.

All construction values are print millimetres. The recipe maps every source mesh
object to a part or to a reasoned exclusion; unknown objects stop the build.
Turret ring clearance is derived from the actual repaired turret geometry by a
revolved sweep envelope, then verified on re-imported final STL files.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import bpy
import numpy as np
import trimesh
import manifold3d as md

from auto_recipe import ATTACHMENT_DEFAULTS
from inspect_scene import import_model, reset_scene, world_mesh, render_preview
from prepare_vehicle import (box, clip_above, cylinder_between, difference,
                             from_manifold, manifold, mesh_object, union)

IMPLEMENTATION_FILES = ("prepare_generic.py", "prepare_vehicle.py", "mesh_repair.py",
                        "inspect_scene.py", "stl_precision.py", "auto_recipe.py")
IMPLEMENTATION_SHA256 = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                         for name in IMPLEMENTATION_FILES}
BED_TARGET_MM = 170.0
PRINT_RESERVE_MM = 16.0

ORIENTATIONS = {
    "as_is": np.eye(4),
    "left_inner_down": trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]),
    "right_inner_down": trimesh.transformations.rotation_matrix(-np.pi/2, [1, 0, 0]),
    "muzzle_up": trimesh.transformations.rotation_matrix(-np.pi/2, [0, 1, 0]),
    "upside_down": trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]),
}


# ---------------------------------------------------------------- recipe ----

def validate_recipe(recipe, scale):
    if recipe.get("schema") != 2:
        raise ValueError("prepare_generic.py requires a schema-2 recipe")
    if recipe.get("profile") != "a1mini_02_pla":
        raise ValueError("Unsupported print profile")
    if scale not in recipe.get("validated_scales", []):
        raise ValueError(f"Recipe values were measured for {recipe.get('validated_scales')}; regenerate for 1:{scale}")
    names = [p["name"] for p in recipe["parts"]]
    if len(set(names)) != len(names) or "hull" not in names:
        raise ValueError("Recipe parts must be unique and include hull")
    for part in recipe["parts"]:
        if part.get("orientation", "as_is") not in ORIENTATIONS:
            raise ValueError(f"Unknown orientation {part.get('orientation')} for {part['name']}")
        target = part.get("merge_into")
        if target and (target not in names or target == part["name"]):
            raise ValueError(f"Invalid merge target for {part['name']}")
    unknown = set(recipe["objects"].values())-set(names)
    if unknown:
        raise ValueError(f"Objects assigned to undeclared parts: {sorted(unknown)}")
    turret = recipe.get("turret", {})
    if turret.get("mode") == "rotating":
        required = ("axis_xy_mm", "trim_z_mm", "bearing_radius_mm", "cap_radius_mm", "pin_diameter_mm",
                    "radial_clearance_mm", "bore_depth_mm", "pin_engagement_mm")
        missing = [k for k in required if k not in turret]
        if missing:
            raise ValueError(f"Turret joint values missing: {missing}")
        if turret["part"] not in names:
            raise ValueError("Turret part not declared")
    for key in recipe.get("glue_keys", []):
        if key["fixed"] not in names or key["moving"] not in names:
            raise ValueError(f"Glue key references unknown part: {key}")
    keyed = {k["moving"] for k in recipe.get("glue_keys", [])}
    for part in recipe["parts"]:
        if part["name"] == "gun_group" and not part.get("merge_into") and "gun_group" not in keyed:
            raise ValueError("gun_group has neither merge_into (turret or hull) nor a reviewed glue key; "
                             "a loose gun cannot be attached")
    attachment = recipe.get("attachment", {})
    if attachment.get("bridge_diameter_mm", .8) < .6 or attachment.get("bridge_retry_step_mm", .2) <= 0:
        raise ValueError("attachment.bridge_diameter_mm must be >= 0.6 and bridge_retry_step_mm > 0")


def chain(obj):
    names = []
    while obj is not None:
        names.append(obj.name)
        obj = obj.parent
    return names


def group_source(input_path, recipe, scale):
    digest = hashlib.sha256(Path(input_path).read_bytes()).hexdigest()
    if digest != recipe["source_glb_sha256"]:
        raise ValueError("Source snapshot changed; regenerate/review the recipe for the new geometry.")
    reset_scene()
    import_model(input_path)
    unit = 1000.0/scale
    assigned = recipe["objects"]
    excluded = {e["object"]: e["reason"] for e in recipe.get("excluded_objects", [])}
    grouped = {p["name"]: [] for p in recipe["parts"]}
    membership = {name: [] for name in grouped}
    origins, unmapped = {}, []
    for obj in list(bpy.context.scene.objects):
        origins[obj.name] = (np.asarray(obj.matrix_world.translation)*unit).tolist()
        if obj.type != "MESH":
            continue
        if obj.name in excluded:
            continue
        if obj.name not in assigned:
            unmapped.append(obj.name)
            continue
        mesh = world_mesh(obj)
        mesh.apply_scale(unit)
        if not len(mesh.faces):
            continue
        # The exporter's mirror root flips handedness; normals are recomputed.
        mesh.merge_vertices(digits_vertex=3)
        mesh.remove_unreferenced_vertices()
        mesh.update_faces(mesh.unique_faces())
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.fix_normals(multibody=True)
        part = assigned[obj.name]
        grouped[part].append((obj.name, mesh))
        membership[part].append(obj.name)
    if unmapped:
        raise ValueError(f"Source objects neither assigned nor excluded in recipe: {unmapped}")
    missing = set(assigned)-{n for items in membership.values() for n in items}
    if missing:
        raise ValueError(f"Recipe objects absent from source: {sorted(missing)}")
    empty = [name for name, items in grouped.items() if not items]
    if empty:
        raise ValueError(f"Print parts without source geometry: {empty}")
    return grouped, membership, origins


# ---------------------------------------------------------------- repair ----

def small_detail_hull(component, target):
    """Convex hull of a small detail; flat sheets get the target wall thickness."""
    hull = component.convex_hull
    if hull.is_volume and hull.volume > 1e-6 and min(hull.extents) >= .05:
        return hull
    points = np.asarray(component.vertices)
    centred = points-points.mean(axis=0)
    normal = np.linalg.svd(centred, full_matrices=False)[2][-1]
    offset = normal*target/2
    return trimesh.convex.convex_hull(np.vstack((points+offset, points-offset)))


def repair_by_component(mesh, target, label, sheet):
    """Fallback when one component of an object defeats the conservative repair.

    Each connected component is repaired on its own. A component that still has
    no closed volume is replaced locally: small details (<= 6 mm) by their convex
    hull, larger ones by a bounded sheet thickening plus fine local voxel remesh.
    Every replacement is audited; nothing is silently dropped.
    """
    from mesh_repair import _clean, _local_voxel, _solidify, repair_mesh
    source = _clean(mesh)
    groups = trimesh.graph.connected_components(source.face_adjacency, nodes=np.arange(len(source.faces)))
    pieces, rows = [], []
    for index, component in enumerate(source.submesh(groups, append=False, repair=False)):
        row = {"component": index, "faces": len(component.faces), "bounds_mm": component.bounds.tolist()}
        try:
            result, audit = repair_mesh(component, target_mm=target, label=f"{label}#{index}", sheet_first=sheet)
            row["method"] = "conservative"
        except ValueError as error:
            candidate = getattr(error, "unquantized_mesh", None)
            if candidate is not None and candidate.is_volume:
                result, row["method"] = candidate, "conservative_float64"
            elif max(component.extents) <= 6.0:
                result, row["method"] = small_detail_hull(component, target), "convex_hull_replacement_small_detail"
            else:
                result = None
                for mode in ("EXTRUDE", "NON_MANIFOLD"):
                    try:
                        candidate = _local_voxel(_solidify(component, target, bounded=True, mode=mode), pitch=0.05)
                    except (ValueError, RuntimeError):
                        continue
                    if candidate.is_volume and candidate.volume > 1e-9:
                        result, row["method"] = candidate, f"bounded_thickening_{mode.lower()}_local_voxel_0.05mm"
                        break
                if result is None:
                    raise ValueError(f"{label} component {index} ({component.extents.round(2).tolist()} mm): "
                                     "no closed volume even with local fallback; recipe exclusion/review required") from error
            row["error"] = str(error)
        if not result.is_volume or result.volume <= 1e-9:
            raise ValueError(f"{label} component {index}: no closed volume even with local fallback")
        row["result_volume_mm3"] = float(result.volume)
        pieces.append(result)
        rows.append(row)
    solid = md.Manifold.batch_boolean([manifold(p) for p in pieces], md.OpType.Add)
    result = from_manifold(solid)
    audit = {"label": label, "target_mm": target, "method": "per_component_fallback",
             "components": rows, "result_bounds_mm": result.bounds.tolist(),
             "result_faces": len(result.faces), "result_volume_mm3": float(result.volume),
             "result_components": len(result.split(only_watertight=False)),
             "maximum_bounds_change_mm": float(np.abs(result.bounds-mesh.bounds).max()),
             "minimum_thickness_certified": False}
    return result, audit


def repair_source(groups, out, target, sheet_objects):
    from mesh_repair import repair_mesh
    import mesh_repair
    cache = out/"repaired_objects"
    cache.mkdir(exist_ok=True)
    implementation = hashlib.sha256(Path(mesh_repair.__file__).read_bytes()).hexdigest()
    repaired = {name: [] for name in groups}
    audits = {}
    for group, items in groups.items():
        for name, mesh in items:
            sheet = name in sheet_objects
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
            signature = hashlib.sha256(mesh.vertices.tobytes()+mesh.faces.tobytes()+implementation.encode()
                                       + f"{target}|{sheet}".encode()).hexdigest()
            path, audit_path = cache/f"{safe}.npz", cache/f"{safe}.json"
            cached = json.loads(audit_path.read_text()) if audit_path.exists() else None
            if path.exists() and cached and cached.get("cache_signature") == signature:
                arr = np.load(path)
                result = trimesh.Trimesh(arr["vertices"], arr["faces"], process=False)
                audit = cached
                print(f"CACHED {group}/{name}", flush=True)
            else:
                print(f"REPAIR {group}/{name}: {len(mesh.faces)} triangles", flush=True)
                try:
                    result, audit = repair_mesh(mesh, target_mm=target, label=name, sheet_first=sheet)
                except ValueError as error:
                    candidate = getattr(error, "unquantized_mesh", None)
                    if candidate is None or not candidate.is_volume:
                        print(f"FALLBACK {group}/{name}: {error}", flush=True)
                        result, audit = repair_by_component(mesh, target, name, sheet)
                        audit["first_attempt_error"] = str(error)
                        audit["cache_signature"] = signature
                        np.savez_compressed(path, vertices=result.vertices, faces=result.faces)
                        audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
                        repaired[group].append((name, result))
                        audits[name] = audit
                        continue
                    result, audit = candidate, error.audit
                    audit.update(result_bounds_mm=result.bounds.tolist(), result_faces=len(result.faces),
                                 result_volume_mm3=float(result.volume), result_watertight=bool(result.is_watertight),
                                 result_components=len(result.split(only_watertight=False)),
                                 stl_quantization_deferred_until_final_union=True)
                audit["cache_signature"] = signature
                np.savez_compressed(path, vertices=result.vertices, faces=result.faces)
                audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
            repaired[group].append((name, result))
            audits[name] = audit
    return repaired, audits


# ----------------------------------------------------------- construction ----

def running_gear_backplate(track, sign, cfg):
    """Hidden glue plate inside the running-gear silhouette, measured per vehicle."""
    from shapely.geometry import MultiPoint, box as polygon_box
    vertices = np.asarray(track.vertices)
    low, high = vertices.min(axis=0), vertices.max(axis=0)
    length, height = high[0]-low[0], high[2]-low[2]
    margin = cfg["x_margin_fraction"]*length
    window = polygon_box(low[0]+margin, low[2]+cfg["z_low_fraction"]*height,
                         high[0]-margin, high[2]-cfg["z_high_fraction"]*height)
    outline = MultiPoint(vertices[:, [0, 2]]).convex_hull.buffer(-cfg["inset_mm"]).intersection(window)
    if outline.is_empty or outline.geom_type != "Polygon":
        raise ValueError("Running-gear outline cannot contain a continuous hidden backplate")
    inner = np.abs(vertices[:, 1]).min()
    thickness = min(cfg["thickness_mm"], 0.5*(np.abs(vertices[:, 1]).max()-inner))
    plate = trimesh.creation.extrude_polygon(outline, thickness, engine="earcut")
    start = inner-cfg["inner_offset_mm"]
    plate.apply_transform(np.array([[1, 0, 0, 0], [0, 0, sign, sign*start],
                                    [0, 1, 0, 0], [0, 0, 0, 1]], dtype=float))
    return plate, {"y_inner_mm": float(sign*start), "thickness_mm": float(thickness),
                   "outline_area_mm2": float(outline.area)}


def turret_floor(turret, z, inset=0.1):
    """Filled turret outline at its trimmed base, joining walls and bearing disk."""
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    section = turret.section([0, 0, 1], [0, 0, z])
    if section is None:
        return None
    polygons = []
    for loop in section.discrete:
        if len(loop) >= 4:
            shape = Polygon(loop[:, :2]).buffer(0)
            if shape.area > 1.0:
                polygons.append(Polygon(shape.exterior) if shape.geom_type == "Polygon" else shape.convex_hull)
    if not polygons:
        return None
    outline = unary_union(polygons).buffer(-inset)
    if outline.is_empty:
        return None
    pieces = [outline] if outline.geom_type == "Polygon" else list(outline.geoms)
    solids = []
    for piece in pieces:
        if piece.area > 1.0:
            solid = trimesh.creation.extrude_polygon(Polygon(piece.exterior), 0.8, engine="earcut")
            solid.apply_translation([0, 0, z-0.4])
            solids.append(solid)
    return union(solids) if solids else None


def socket_cutter(cfg):
    """Pin bore; every part rotating with the turret must keep it free (breech overhangs)."""
    x, y = cfg["axis_xy_mm"]
    trim = cfg["trim_z_mm"]
    return cylinder_between([x, y, trim-1], [x, y, trim+cfg["bore_depth_mm"]],
                            cfg["pin_diameter_mm"]/2+cfg["radial_clearance_mm"], 96)


def build_turret_joint(parts, cfg, audit):
    name = cfg["part"]
    x, y = cfg["axis_xy_mm"]
    trim = cfg["trim_z_mm"]
    seat = trim-cfg["vertical_clearance_mm"]
    bearing, cap_radius = cfg["bearing_radius_mm"], cfg["cap_radius_mm"]
    before = float(parts[name].volume)
    parts[name] = clip_above(parts[name], trim)
    clipped = before-float(parts[name].volume)
    # Gun breech/cradle below the ring plane is hull interior and would sweep
    # through the deck cap on every turn.
    clipped_attached = {}
    for other in cfg.get("sweep_excluded_parts", []):
        if other in parts and parts[other].bounds[0, 2] < trim:
            volume = float(parts[other].volume)
            parts[other] = clip_above(parts[other], trim)
            clipped_attached[other] = volume-float(parts[other].volume)
    top = max(float(m.bounds[1, 2]) for m in parts.values())+5
    parts["hull"] = difference(parts["hull"], [cylinder_between([x, y, seat], [x, y, top], cap_radius)])
    cap = cylinder_between([x, y, seat-cfg["cap_depth_mm"]], [x, y, seat], cap_radius)
    pad = cylinder_between([x, y, seat], [x, y, trim], cfg["bearing_pad_radius_mm"], 96)
    parts["hull"] = union([parts["hull"], cap, pad])
    floor = turret_floor(parts[name], trim+0.4)
    disk = cylinder_between([x, y, trim], [x, y, trim+cfg["disk_thickness_mm"]], bearing)
    hub = cylinder_between([x, y, trim], [x, y, max(cfg["hub_top_z_mm"], trim+1.5)], cfg["hub_radius_mm"])
    pin_r = cfg["pin_diameter_mm"]/2
    tip_z = trim+cfg["pin_engagement_mm"]
    chamfer = cfg["pin_tip_chamfer_mm"]
    pin = cylinder_between([x, y, seat-1.0], [x, y, tip_z-chamfer], pin_r, 96)
    tip = from_manifold(md.Manifold.cylinder(chamfer, pin_r, pin_r-chamfer, 96).translate([x, y, tip_z-chamfer]))
    parts["hull"] = union([parts["hull"], pin, tip])
    parts[name] = union([parts[name], disk, hub]+([floor] if floor is not None else []))
    parts[name] = difference(parts[name], [socket_cutter(cfg)])
    audit["joints"]["turret"] = {"axis_xy_mm": [float(x), float(y)], "trim_z_mm": trim, "seat_z_mm": seat,
        "radial_clearance_mm": cfg["radial_clearance_mm"], "pin_diameter_mm": pin_r*2,
        "engagement_mm": cfg["pin_engagement_mm"], "bore_depth_mm": cfg["bore_depth_mm"],
        "bearing_disk_radius_mm": bearing, "hull_cap_radius_mm": cap_radius,
        "outer_disc_clearance_mm": cfg["vertical_clearance_mm"], "pin_owner": "hull",
        "turret_floor_added": floor is not None, "clipped_turret_volume_mm3": clipped,
        "clipped_below_ring_mm3": clipped_attached}
    audit["reinforcements"].append("Turret basket below ring plane removed; concealed floor, bearing disk, hub and hull cap/pin added.")


def sweep_profile(mesh, axis, z0, z1, band):
    """Maximum radius of a body per Z band (exact for linear triangles)."""
    x, y = axis
    vertices = np.asarray(mesh.vertices)
    edges = vertices[mesh.edges_unique]
    zs = np.arange(z0, z1+band, band)
    radius = np.hypot(vertices[:, 0]-x, vertices[:, 1]-y)
    band_index = np.floor((vertices[:, 2]-z0)/band).astype(int)
    rmax = np.zeros(len(zs)-1)
    inside = (band_index >= 0) & (band_index < len(rmax))
    np.maximum.at(rmax, band_index[inside], radius[inside])
    a, b = edges[:, 0], edges[:, 1]
    for k, z in enumerate(zs):
        crossing = (np.minimum(a[:, 2], b[:, 2]) <= z) & (np.maximum(a[:, 2], b[:, 2]) >= z) & (np.abs(b[:, 2]-a[:, 2]) > 1e-12)
        if not crossing.any():
            continue
        t = (z-a[crossing, 2])/(b[crossing, 2]-a[crossing, 2])
        points = a[crossing]+(b[crossing]-a[crossing])*t[:, None]
        r = float(np.hypot(points[:, 0]-x, points[:, 1]-y).max())
        for index in (k-1, k):
            if 0 <= index < len(rmax):
                rmax[index] = max(rmax[index], r)
    return zs, rmax


def relieve_sweep(parts, cfg, fixed, movable, audit):
    """Remove fixed geometry inside the revolved envelope of the moving turret."""
    x, y = cfg["axis_xy_mm"]
    clearance = cfg["radial_clearance_mm"]+cfg["ring_eccentric_margin_mm"]
    swept = [n for n in movable if n not in cfg.get("sweep_excluded_parts", [])]
    body = trimesh.util.concatenate([parts[n] for n in swept])
    z0 = cfg["trim_z_mm"]
    z1 = min(float(body.bounds[1, 2]), max(float(parts[n].bounds[1, 2]) for n in fixed))
    if z1 <= z0:
        audit["sweep_relief"] = {"removed_mm3": {}, "note": "no fixed geometry above ring plane"}
        return
    zs, rmax = sweep_profile(body, (x, y), z0, z1, cfg["sweep_band_mm"])
    cylinders = []
    for k, r in enumerate(rmax):
        if r <= 0:
            continue
        low = zs[k]-cfg["vertical_clearance_mm"]
        cylinders.append(md.Manifold.cylinder(zs[k+1]-low+0.02, r+clearance, r+clearance, 192).translate([x, y, low]))
    if not cylinders:
        return
    envelope = md.Manifold.batch_boolean(cylinders, md.OpType.Add)
    core = md.Manifold.cylinder(500, cfg["protected_core_radius_mm"], cfg["protected_core_radius_mm"], 96).translate([x, y, -100])
    envelope = envelope-core
    removed, fraction = {}, {}
    for name in fixed:
        solid = manifold(parts[name])
        relieved = solid-envelope
        volume = float(solid.volume()-relieved.volume())
        if volume > 1e-4:
            parts[name] = from_manifold(relieved)
        removed[name] = volume
        fraction[name] = volume/max(float(solid.volume()), 1e-9)
    audit["sweep_relief"] = {"radial_clearance_mm": clearance, "vertical_clearance_mm": cfg["vertical_clearance_mm"],
        "band_mm": cfg["sweep_band_mm"], "z_range_mm": [z0, z1], "swept_parts": swept,
        "max_swept_radius_mm": float(rmax.max()), "removed_mm3": removed, "removed_fraction": fraction,
        "protected_core_radius_mm": cfg["protected_core_radius_mm"],
        "purpose": "Rotation gap between turret and fixed deck/collar derived from actual turret profile"}
    worst = max(fraction.values())
    if worst > 0.15:
        raise ValueError(f"Turret sweep would remove {worst:.1%} of a fixed part; recipe review required")
    if worst > 0.03:
        audit.setdefault("review_flags", []).append(f"Turret sweep removed {worst:.1%} of a fixed part; inspect visible deck detail")


def apply_reliefs(parts, pairs, audit):
    rows = []
    for receiver, insert in pairs:
        if receiver not in parts or insert not in parts:
            continue
        a, b = manifold(parts[receiver]), manifold(parts[insert])
        volume = abs(float((a ^ b).volume()))
        if volume > .001:
            parts[receiver] = from_manifold(a-b)
        rows.append({"receiver": receiver, "insert": insert, "relieved_overlap_mm3": volume})
    audit["assembly_reliefs"] = audit.get("assembly_reliefs", [])+rows


def apply_glue_keys(parts, recipe, audit):
    tolerance = recipe.get("glue_clearance_per_side_mm", .15)
    for key in recipe.get("glue_keys", []):
        low, high = np.array(key["low_mm"]), np.array(key["high_mm"])
        parts[key["fixed"]] = union([parts[key["fixed"]], box(low, high)])
        parts[key["moving"]] = difference(parts[key["moving"]], [box(low-tolerance, high+tolerance)])
        audit["joints"][f"{key['fixed']}_to_{key['moving']}"] = {"type": "keyed_glue",
            "key_bounds_mm": [low.tolist(), high.tolist()], "clearance_per_side_mm": tolerance}


def attachment_config(recipe):
    return {**ATTACHMENT_DEFAULTS, **recipe.get("attachment", {})}


def solid_shells(mesh, min_volume):
    """Split into shells; drop zero-volume slivers by volume alone, whatever their size.

    Flat Boolean leftovers (e.g. four coplanar faces) can span millimetres yet
    enclose nothing; Manifold rejects them, so an extent limit must not keep them.
    """
    kept, dropped = [], []
    for shell in mesh.split(only_watertight=False):
        volume = abs(float(shell.volume))
        reason = None
        if volume < min_volume:
            reason = "zero/sub-extrusion volume sliver"
        else:
            try:
                manifold(shell)
            except ValueError:
                if volume >= 50*min_volume:
                    raise
                reason = "degenerate shell rejected by Manifold"
        if reason:
            dropped.append({"volume_mm3": volume, "faces": int(len(shell.faces)),
                            "bounds_mm": shell.bounds.tolist(), "reason": reason})
        else:
            kept.append(shell)
    return sorted(kept, key=lambda m: abs(m.volume), reverse=True), dropped


def connect_parts(mesh, label, cfg):
    """Join detail shells with the shortest local bridges; diameter from the recipe.

    Attempt 0 uses bridge_diameter_mm; each retry (only if the union still has
    several shells) re-bridges the remainder with bridges bridge_retry_step_mm
    thicker, at most bridge_max_retries times. Every bridge records its attempt.
    """
    from scipy.spatial import cKDTree
    audit = {"part": label, "bridges": [], "removed_slivers": [], "attempts": []}
    shells, dropped = solid_shells(mesh, cfg["min_shell_volume_mm3"])
    audit["removed_slivers"] += dropped
    audit["original_shells"] = len(shells)
    if not shells:
        raise ValueError(f"{label}: no substantial geometry")
    for attempt in range(int(cfg["bridge_max_retries"])+1):
        diameter = float(cfg["bridge_diameter_mm"])+attempt*float(cfg["bridge_retry_step_mm"])
        if len(shells) == 1:
            break
        audit["attempts"].append({"attempt": attempt, "shells_in": len(shells), "bridge_diameter_mm": diameter})
        if attempt:
            print(f"RECONNECT {label}: attempt {attempt}/{cfg['bridge_max_retries']}, {len(shells)} shells, "
                  f"bridge diameter {diameter:.2f} mm", flush=True)
        members, bridges = [shells[0]], []
        pending = shells[1:]
        connected_vertices = shells[0].vertices.copy()
        while pending:
            tree = cKDTree(connected_vertices)
            choices = []
            for i, shell in enumerate(pending):
                distances, indices = tree.query(shell.vertices, k=1)
                j = int(np.argmin(distances))
                choices.append((float(distances[j]), i, shell.vertices[j], connected_vertices[indices[j]]))
            distance, index, a, b = min(choices, key=lambda c: c[0])
            if distance > cfg["max_bridge_gap_mm"]:
                raise ValueError(f"{label}: detail shell {distance:.3f} mm away exceeds max_bridge_gap_mm "
                                 f"{cfg['max_bridge_gap_mm']}; assign it to another part, exclude it or add a glue key")
            shell = pending.pop(index)
            direction = (b-a)/distance if distance > 1e-5 else members[0].centroid-shell.centroid
            if np.linalg.norm(direction) < 1e-8:
                direction = np.array([0., 0., 1.])
            direction = direction/np.linalg.norm(direction)
            bridges.append(cylinder_between(a-direction*.35, b+direction*.35, diameter/2, 24))
            members.append(shell)
            connected_vertices = np.vstack((connected_vertices, shell.vertices))
            audit["bridges"].append({"start": a.tolist(), "end": b.tolist(), "gap_mm": distance,
                                     "diameter_mm": diameter, "attempt": attempt})
        joined = union(members+bridges)
        shells, dropped = solid_shells(joined, cfg["min_shell_volume_mm3"])
        audit["removed_slivers"] += [{**d, "generated_by_union": True} for d in dropped]
    if len(shells) != 1:
        summary = [{"volume": float(s.volume), "bounds": s.bounds.tolist()} for s in shells]
        raise ValueError(f"{label}: {len(shells)} shells left after {cfg['bridge_max_retries']} bridge retries: {summary}")
    audit["final_shells"] = 1
    audit["retries_used"] = max(0, len(audit["attempts"])-1)
    return shells[0], audit


def attachment_review_flags(entry, cfg):
    """Automatic review hints: long or thin bridges, many joined shells, retries."""
    flags, label = [], entry["part"]
    long = [b for b in entry["bridges"] if b["gap_mm"] > cfg["review_bridge_gap_mm"]]
    if long:
        worst = max(b["gap_mm"] for b in long)
        flags.append(f"{label}: {len(long)} bridge(s) span gaps > {cfg['review_bridge_gap_mm']} mm "
                     f"(max {worst:.2f} mm); visible strut, check detail placement")
    # Long AND thin: a free-standing strut that can snap. Short thin joints are normal.
    thin = [b for b in long if b["diameter_mm"] < cfg["review_thin_bridge_diameter_mm"]]
    if thin:
        flags.append(f"{label}: {len(thin)} of these bridge(s) thinner than "
                     f"{cfg['review_thin_bridge_diameter_mm']} mm; fragile with a 0.2-mm nozzle, "
                     f"consider attachment.bridge_diameter_mm")
    if entry["original_shells"] > cfg["review_max_shells"]:
        flags.append(f"{label}: {entry['original_shells']} separate shells joined by bridges "
                     f"(> {cfg['review_max_shells']}); check for floating details")
    if entry["retries_used"]:
        diameters = sorted({b["diameter_mm"] for b in entry["bridges"]})
        flags.append(f"{label}: bridge retry needed ({entry['retries_used']}x); mixed bridge diameters "
                     f"{', '.join(f'{d:.2f}' for d in diameters)} mm")
    return flags


def drop_fragments(parts, audit, keep_regions):
    """Remove sub-extrusion Boolean slivers; bridge or reject everything else."""
    removed = []
    for name in list(parts):
        shells = sorted(parts[name].split(only_watertight=False), key=lambda m: abs(m.volume), reverse=True)
        if len(shells) == 1:
            continue
        retained = [shells[0]]
        for shell in shells[1:]:
            tiny = abs(shell.volume) < .002  # volume only: flat slivers can be large
            hidden = (abs(shell.volume) < .2 and max(shell.extents) < 2.5 and any(
                np.all(shell.bounds[0] >= low-.5) and np.all(shell.bounds[1] <= high+.5) for low, high in keep_regions))
            if tiny or hidden:
                removed.append({"part": name, "volume_mm3": float(shell.volume), "bounds_mm": shell.bounds.tolist(),
                                "reason": "sub-extrusion Boolean fragment" if tiny else "hidden stub isolated inside running-gear recess"})
            else:
                retained.append(shell)
        parts[name] = trimesh.util.concatenate(retained) if len(retained) > 1 else retained[0]
    audit["removed_fragments"] = audit.get("removed_fragments", [])+removed


def build_parts(groups, recipe, audit):
    parts = {}
    for name, items in groups.items():
        print(f"UNION {name}", flush=True)
        solid = md.Manifold.batch_boolean([manifold(m) for _, m in items], md.OpType.Add)
        parts[name] = from_manifold(solid.simplify(.01))
    gear = [n for n in parts if n.startswith("running_gear_")]
    plate_cfg = recipe.get("running_gear_backplate", {})
    if plate_cfg.get("enabled") and gear:
        for name in gear:
            sign = 1 if name.endswith("left") else -1
            sheets = [m for label, m in groups[name] if label in recipe.get("sheet_objects", [])]
            reference = trimesh.util.concatenate(sheets) if sheets else parts[name]
            plate, info = running_gear_backplate(reference, sign, plate_cfg)
            parts[name] = union([parts[name], plate])
            audit["joints"][f"hull_to_{name}"] = {"type": "glue_backplate", **info}
        audit["reinforcements"].append("Concealed running-gear backplates create flat glue faces inside the track outline.")
    turret = recipe.get("turret", {})
    if turret.get("mode") == "rotating":
        build_turret_joint(parts, turret, audit)
    apply_glue_keys(parts, recipe, audit)
    return parts


def merge_parts(parts, recipe, audit):
    for part in recipe["parts"]:
        target = part.get("merge_into")
        if target and part["name"] in parts:
            parts[target] = union([parts[target], parts.pop(part["name"])])
            audit.setdefault("merged_parts", []).append({"part": part["name"], "into": target})


def movable_parts(recipe, parts):
    turret = recipe.get("turret", {})
    if turret.get("mode") != "rotating":
        return []
    names = {turret["part"]}
    for part in recipe["parts"]:
        if part.get("merge_into") == turret["part"] or part.get("moves_with") == turret["part"]:
            names.add(part["name"])
    return [n for n in parts if n in names]


def check_rotation(parts, audit, recipe):
    movable = movable_parts(recipe, parts)
    if not movable:
        audit["rotation_check"] = {"applicable": False}
        return
    fixed = [n for n in parts if n not in movable]
    fixed_solid = md.Manifold.batch_boolean([manifold(parts[n]) for n in fixed], md.OpType.Add)
    moving = md.Manifold.batch_boolean([manifold(parts[n]) for n in movable], md.OpType.Add)
    x, y = audit["joints"]["turret"]["axis_xy_mm"]
    play = audit["joints"]["turret"]["radial_clearance_mm"]
    samples = []
    for dx, dy in ((0, 0), (play, 0), (-play, 0), (0, play), (0, -play)):
        for degrees in range(0, 360, 15):
            moved = moving.translate([-x, -y, 0]).rotate([0, 0, degrees]).translate([x+dx, y+dy, 0])
            clash = fixed_solid ^ moved
            volume = abs(float(clash.volume())) if not clash.is_empty() else 0.0
            samples.append({"degrees": degrees, "eccentric_offset_xy_mm": [dx, dy], "intersection_mm3": volume})
    blocked = sorted({s["degrees"] for s in samples if s["intersection_mm3"] > .01})
    worst = max(samples, key=lambda s: s["intersection_mm3"])
    diagnosis = {}
    if worst["intersection_mm3"] > .01:
        dx, dy = worst["eccentric_offset_xy_mm"]
        for f in fixed:
            for m in movable:
                moved = manifold(parts[m]).translate([-x, -y, 0]).rotate([0, 0, worst["degrees"]]).translate([x+dx, y+dy, 0])
                clash = manifold(parts[f]) ^ moved
                if not clash.is_empty() and abs(float(clash.volume())) > .001:
                    box_ = from_manifold(clash).bounds
                    diagnosis[f"{m}~{f}"] = {"mm3": abs(float(clash.volume())), "bounds_mm": box_.tolist()}
    centred_zero = next(s for s in samples if s["degrees"] == 0 and s["eccentric_offset_xy_mm"] == [0, 0])
    audit["rotation_check"] = {"applicable": True, "step_degrees": 15, "samples": samples,
        "maximum_intersection_mm3": max(s["intersection_mm3"] for s in samples),
        "blocked_angles_degrees": blocked, "rotation_limited": bool(blocked),
        "worst_sample": worst, "worst_sample_contacts": diagnosis,
        "continuous_rotation_proven": False}
    if centred_zero["intersection_mm3"] > .01:
        raise ValueError(f"Assembled turret pose intersects fixed parts: {centred_zero['intersection_mm3']:.4f} mm3")
    flags = [f for f in audit.get("review_flags", []) if not f.startswith("Turret/gun touches")]
    if blocked:
        flags.append(f"Turret/gun touches fixed parts at {blocked} degrees (e.g. barrel over rear deck); rotation is limited there")
    audit["review_flags"] = flags


def elevate_gun(parts, recipe, audit):
    """Raise a depressed default-pose gun about its trunnion until traverse is clear.

    Game models often store the barrel slightly depressed into the glacis. The
    gun group is pitched about the bone_gun origin in 1-degree steps up to the
    recipe limit; the first elevation clearing all 24 traverse angles is used,
    otherwise the smallest one clearing the assembled pose (blocked angles are
    then reported by the rotation check).
    """
    gun = recipe.get("gun", {})
    turret = recipe.get("turret", {})
    name = gun.get("part", "gun_group")
    if not gun.get("auto_elevate") or turret.get("mode") != "rotating" or name not in parts:
        return
    x, y = turret["axis_xy_mm"]
    pivot = np.asarray(gun["pivot_mm"], dtype=float)
    direction = 1.0 if parts[name].centroid[0] >= pivot[0] else -1.0
    movable = {turret["part"], name}
    fixed = [n for n in parts if n not in movable]
    window = manifold(box([-500, -500, turret["trim_z_mm"]-1], [500, 500, 500]))
    fixed_top = md.Manifold.batch_boolean([manifold(parts[n]) for n in fixed], md.OpType.Add) ^ window
    base = manifold(parts[name])
    # Raising the muzzle lowers the breech; anything below the ring plane is interior.
    above = manifold(box([-500, -500, turret["trim_z_mm"]], [500, 500, 500]))-manifold(socket_cutter(turret))

    def pitched(degrees):
        return base.translate((-pivot).tolist()).rotate([0, -direction*degrees, 0]).translate(pivot.tolist()) ^ above

    def contacts(solid, angles):
        result = {}
        for a in angles:
            moved = solid.translate([-x, -y, 0]).rotate([0, 0, a]).translate([x, y, 0])
            clash = fixed_top ^ moved
            result[a] = 0.0 if clash.is_empty() else abs(float(clash.volume()))
        return result

    angles = list(range(0, 360, 15))
    rows, chosen = [], None
    for degrees in range(0, int(gun.get("max_elevation_deg", 12))+1):
        hits = contacts(pitched(degrees), angles)
        rows.append({"elevation_deg": degrees, "assembled_mm3": hits[0], "max_traverse_mm3": max(hits.values()),
                     "blocked_angles": [a for a, v in hits.items() if v > .01]})
        if max(hits.values()) <= .01:
            chosen = degrees
            break
    if chosen is None:
        clear_zero = [r["elevation_deg"] for r in rows if r["assembled_mm3"] <= .01]
        chosen = clear_zero[0] if clear_zero else 0
    if chosen:
        parts[name] = from_manifold(pitched(chosen))
        audit.setdefault("review_flags", []).append(
            f"Gun raised {chosen} deg about the trunnion so the barrel clears the hull (source pose was depressed)")
    audit["gun_elevation"] = {"pivot_mm": pivot.tolist(), "chosen_deg": chosen, "trials": rows,
                              "barrel_direction_x": direction}


def finish_parts(parts, recipe, audit):
    """Reliefs, sweep, merges and fragment control; every part ends as one body."""
    turret = recipe.get("turret", {})
    elevate_gun(parts, recipe, audit)
    apply_reliefs(parts, recipe.get("assembly_reliefs", []), audit)
    if turret.get("mode") == "rotating":
        movable = [n for n in parts if n == turret["part"] or n in turret.get("sweep_excluded_parts", [])]
        fixed = [n for n in parts if n not in movable]
        relieve_sweep(parts, turret, fixed, movable, audit)
    merge_parts(parts, recipe, audit)
    if turret.get("mode") == "rotating":
        for name in movable_parts(recipe, parts):
            parts[name] = difference(parts[name], [socket_cutter(turret)])
    gear = [parts[n].bounds for n in parts if n.startswith("running_gear_")]
    drop_fragments(parts, audit, gear)
    cfg = attachment_config(recipe)
    audit["attachment_config"] = cfg
    for name, mesh in list(parts.items()):
        print(f"ATTACH {name}", flush=True)
        parts[name], entry = connect_parts(mesh, name, cfg)
        audit.setdefault("attachments", []).append(entry)
        audit.setdefault("review_flags", []).extend(attachment_review_flags(entry, cfg))
    for name, mesh in parts.items():
        if not mesh.is_volume or len(mesh.split(only_watertight=False)) != 1:
            raise ValueError(f"{name}: not one closed body after assembly fitting")
    check_rotation(parts, audit, recipe)
    return parts


# ----------------------------------------------------------------- export ----

def validate_and_export(parts, audit, recipe, out, scale):
    from mesh_repair import _sample_thickness
    from stl_precision import prepare_stl_mesh
    output_stl = out/"stl"
    output_stl.mkdir(exist_ok=True)
    for old in output_stl.glob("*.stl"):
        old.unlink()
    orientation = {p["name"]: p.get("orientation", "as_is") for p in recipe["parts"]}
    blend = f"{recipe['vehicle_id']}_1_{scale}.blend"
    report = {"vehicle_id": recipe["vehicle_id"], "display_name": recipe.get("display_name"),
              "builder": "prepare_generic.py", "recipe_schema": 2,
              "source_sha256": recipe["source_glb_sha256"], "recipe_sha256": recipe["_recipe_sha256"],
              "profile": recipe["profile"], "implementation_sha256": IMPLEMENTATION_SHA256,
              "scale_denominator": scale, "geometry_passed": False, "blend_file": blend,
              "physical_print_verified": False, "physical_calibration_passed": False,
              "recipe_auto_generated": bool(recipe.get("review", {}).get("auto_generated")),
              "recipe_human_reviewed": bool(recipe.get("review", {}).get("human_reviewed")),
              "parts": [], "construction": audit,
              "minimum_wall_target_mm": recipe["minimum_structural_thickness_mm"],
              "minimum_wall_thickness_globally_certified": False,
              "excluded_objects": recipe.get("excluded_objects", []),
              "review_flags": audit.get("review_flags", []),
              "limitations": ["Small cosmetic relief may be below the structural 0.8-mm target.",
                              "Turret ring clearance and running-gear plates are derived automatically from this model; verify visually.",
                              "Physical fit requires the PLA calibration print."]}
    reset_scene()
    collection = bpy.data.collections.new(f"Assembled {recipe['vehicle_id']} (mm)")
    bpy.context.scene.collection.children.link(collection)
    bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[collection.name]
    actual = {}
    for name, original in parts.items():
        mesh, reduction = original, []
        for tolerance in (.01, .001, .0001):
            candidate = from_manifold(manifold(original).simplify(tolerance))
            connected = candidate.is_volume and len(candidate.split(only_watertight=False)) == 1
            reduction.append({"tolerance_mm": tolerance, "closed_connected": bool(connected)})
            if connected:
                mesh = candidate
                break
        if not mesh.is_volume or len(mesh.split(only_watertight=False)) != 1:
            raise ValueError(f"{name}: final part is not one closed positive volume")
        printable = mesh.copy()
        transform = ORIENTATIONS[orientation.get(name, "as_is")].copy()
        printable.apply_transform(transform)
        translation = -printable.bounds[0]
        printable.apply_translation(translation)
        transform[:3, 3] += translation
        printable, stl_audit = prepare_stl_mesh(printable, max_displacement_mm=.001)
        target = output_stl/f"{name}.stl"
        printable.export(target)
        loaded = trimesh.load_mesh(target, process=True)
        loaded.remove_unreferenced_vertices()
        if not loaded.is_volume or len(loaded.split(only_watertight=False)) != 1:
            raise ValueError(f"{name}: exported STL failed closed/connected readback")
        if max(loaded.extents[:2]+PRINT_RESERVE_MM) > BED_TARGET_MM or loaded.extents[2] > BED_TARGET_MM:
            raise ValueError(f"{name}: {loaded.extents.round(1).tolist()} mm plus print reserve exceeds the "
                             f"{BED_TARGET_MM:.0f}-mm target at 1:{scale}; choose a larger denominator or split the part")
        assembled = loaded.copy()
        assembled.apply_transform(np.linalg.inv(transform))
        actual[name] = assembled
        mesh_object(name, assembled)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        report["parts"].append({"name": name, "exported_stl": f"stl/{name}.stl", "sha256": digest,
            "exported_stl_sha256": digest, "orientation": orientation.get(name, "as_is"),
            "bounds_assembly_mm": assembled.bounds.tolist(), "print_dimensions_mm": loaded.extents.tolist(),
            "assembly_to_print_transform": transform.tolist(), "triangles": len(loaded.faces),
            "volume_mm3": float(loaded.volume), "watertight": True, "connected_components": 1,
            "simplification_attempts": reduction, "sampled_thickness": _sample_thickness(loaded, 128),
            "stl_precision": stl_audit})
    check_rotation(actual, audit, recipe)
    if audit["rotation_check"].get("applicable"):
        audit["rotation_check"]["geometry_source"] = "final_exported_stl_readback"
    report["review_flags"] = audit.get("review_flags", [])
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = .001
    bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"
    bpy.ops.wm.save_as_mainfile(filepath=str(out/blend))
    render_preview(out/"assembly_preview.png", resolution=1600)
    report["geometry_passed"] = True
    (out/"construction_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    (out/"print_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--recipe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scale", type=int, default=72)
    parser.add_argument("--inspect-only", action="store_true")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if not args.inspect_only:
        (out/"print_report.json").write_text(json.dumps({"geometry_passed": False, "status": "preparing",
                                                         "physical_print_verified": False}), encoding="utf-8")
    recipe = json.loads(args.recipe.read_text(encoding="utf-8"))
    if recipe.get("vehicle_id") != args.recipe.stem:
        raise ValueError("Recipe file name must equal its vehicle_id")
    recipe["_recipe_sha256"] = hashlib.sha256(args.recipe.read_bytes()).hexdigest()
    validate_recipe(recipe, args.scale)
    groups, members, origins = group_source(args.input, recipe, args.scale)
    source = {"source": str(args.input.resolve()), "scale": args.scale, "members": members, "groups": {}}
    for name, items in groups.items():
        mesh = trimesh.util.concatenate([m for _, m in items])
        source["groups"][name] = {"bounds_mm": mesh.bounds.tolist(), "faces": len(mesh.faces), "source_objects": len(items)}
    (out/"source_groups.json").write_text(json.dumps(source, indent=2), encoding="utf-8")
    if args.inspect_only:
        print(json.dumps(source["groups"], indent=2))
        return
    work = out/"work"
    work.mkdir(exist_ok=True)
    repaired, audits = repair_source(groups, work, recipe["minimum_structural_thickness_mm"],
                                     set(recipe.get("sheet_objects", [])))
    (out/"repair_audits.json").write_text(json.dumps(audits, indent=2), encoding="utf-8")
    audit = {"reinforcements": [], "attachments": [], "joints": {}}
    fallbacks = {name: [c["method"] for c in a["components"] if c["method"] != "conservative"]
                 for name, a in audits.items() if a.get("method") == "per_component_fallback"}
    if fallbacks:
        audit["fallback_repairs"] = fallbacks
        audit["review_flags"] = [f"Local replacement geometry in {name}: {sorted(set(m))}"
                                 for name, m in fallbacks.items()]
    try:
        parts = build_parts(repaired, recipe, audit)
        parts = finish_parts(parts, recipe, audit)
    finally:
        (out/"construction_audit.json").write_text(json.dumps(audit, indent=2, default=str), encoding="utf-8")
    report = validate_and_export(parts, audit, recipe, out, args.scale)
    print(json.dumps({"geometry_passed": report["geometry_passed"], "parts": [p["name"] for p in report["parts"]],
                      "review_flags": report["review_flags"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()

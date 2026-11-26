"""Derive a reviewable generic (schema 2) vehicle recipe from an exported GLB.

Runs inside the project Python with bpy. The source snapshot is only read.
Every mesh object is either assigned to exactly one print part or excluded with
an explicit reason, so the builder can enforce a complete hierarchy mapping.
Measured turret-ring values are print millimetres for the requested scale.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

import numpy as np

SCHEMA = 2
PROFILE = "a1mini_02_pla"

EXCLUDE_NAME = [
    (r"(^|_)dmg(_|$)", "damage-state geometry"),
    (r"(^|_)destr(oyed)?(_|$)", "destroyed-state geometry"),
    (r"^emtr_", "effect emitter"),
    (r"collision|^col_|_col$", "collision helper"),
    (r"^xray|_xray", "x-ray helper"),
]
TRACK_BELT = r"^track_(l|r)(_|$)"
SIDE_GEAR = r"^(track|wheel|suspension|bone_wheel|bone_suspension|bone_track|sprocket|idler|roller)_({side})(_|$)"


# Bridges joining separated detail shells (see prepare_generic.connect_parts).
ATTACHMENT_DEFAULTS = {"bridge_diameter_mm": 0.8, "bridge_retry_step_mm": 0.2, "bridge_max_retries": 2,
                       "max_bridge_gap_mm": 5.0, "min_shell_volume_mm3": 0.002,
                       "review_bridge_gap_mm": 1.0, "review_thin_bridge_diameter_mm": 1.0,
                       "review_max_shells": 100}


def chain(obj):
    names = []
    while obj is not None:
        names.append(obj.name)
        obj = obj.parent
    return names


def primary_turret(objects):
    """Largest top-level turret branch; nested turrets stay inside it."""
    candidates = []
    for obj in objects:
        if not re.fullmatch(r"bone_turret(_\d+)?", obj.name):
            continue
        if any(re.fullmatch(r"bone_turret(_\d+)?", n) for n in chain(obj)[1:]):
            continue
        faces = 0
        for other in objects:
            if other.type == "MESH" and obj.name in chain(other):
                faces += len(other.data.polygons)
        if faces:
            candidates.append((obj.name != "bone_turret", -faces, obj.name))
    return sorted(candidates)[0][2] if candidates else None


def classify(objects, unit):
    """Return {object: part}, exclusions and secondary-turret notes."""
    from inspect_scene import world_mesh
    turret = primary_turret(objects)
    assignment, excluded, notes, meshes = {}, [], [], {}
    for obj in objects:
        if obj.type != "MESH":
            continue
        names = chain(obj)
        reason = next((why for pattern, why in EXCLUDE_NAME
                       if any(re.search(pattern, n, re.I) for n in names)), None)
        mesh = world_mesh(obj)
        mesh.apply_scale(unit)
        if not len(mesh.faces):
            excluded.append({"object": obj.name, "reason": "no referenced triangles"})
            continue
        if reason:
            excluded.append({"object": obj.name, "reason": reason})
            continue
        extents = np.sort(mesh.extents)
        if extents[2] > 8.0 and extents[1] < 0.6:
            excluded.append({"object": obj.name, "reason": "whip/wire thinner than 0.6 mm at this scale; not printable with 0.2-mm nozzle",
                             "extents_mm": mesh.extents.tolist()})
            continue
        if extents[2] < 0.3:
            excluded.append({"object": obj.name, "reason": "sub-extrusion speck below 0.3 mm", "extents_mm": mesh.extents.tolist()})
            continue
        part = "hull"
        if turret and turret in names:
            part = "gun_group" if "bone_gun" in names[:names.index(turret)] else "turret"
        else:
            for side, label in (("l", "left"), ("r", "right")):
                if any(re.search(SIDE_GEAR.format(side=side), n) for n in names):
                    part = f"running_gear_{label}"
            other = [n for n in names if re.fullmatch(r"bone_turret(_\d+)?", n)]
            if other:
                notes.append(f"{obj.name}: secondary turret branch {other[0]} kept fixed on hull")
        assignment[obj.name] = part
        meshes[obj.name] = mesh
    return turret, assignment, excluded, notes, meshes


def ray_top(intersector, x, y, ceiling=400.0):
    locations, _, _ = intersector.intersects_location([[x, y, ceiling]], [[0, 0, -1.0]], multiple_hits=False)
    return float(locations[0, 2]) if len(locations) else np.nan


def ray_up(intersector, x, y, z):
    locations, _, _ = intersector.intersects_location([[x, y, z]], [[0, 0, 1.0]], multiple_hits=False)
    return float(locations[0, 2]) if len(locations) else np.nan


def measure_ring(hull, turret, axis):
    """Locate the hull deck around the turret axis and a bearing radius."""
    from trimesh.ray.ray_triangle import RayMeshIntersector
    x, y, axis_z = axis
    hits = RayMeshIntersector(hull)
    angles = np.linspace(0, 2*np.pi, 36, endpoint=False)
    profile = []
    for radius in np.arange(1.0, 40.0, 0.5):
        tops = [ray_top(hits, x+radius*np.cos(a), y+radius*np.sin(a)) for a in angles]
        tops = np.array(tops)
        profile.append([float(radius), float(np.nanmedian(tops)) if np.isfinite(tops).any() else None])
    radii = np.array([p[0] for p in profile])
    medians = np.array([np.nan if p[1] is None else p[1] for p in profile])
    near = np.isfinite(medians) & (medians >= axis_z - 6.0) & (medians <= axis_z + 4.0)
    hole_index = None
    for i in range(len(radii)-6):
        if near[i:i+6].all():
            hole_index = i
            break
    if hole_index is None:
        raise ValueError("Hull deck around turret axis not found; set turret.mode or values manually")
    hole_radius = float(radii[hole_index]) if hole_index else 0.0
    deck_z = float(np.median(medians[hole_index:hole_index+6]))
    trim = deck_z + 0.5
    # Outward reach of the turret base: section polylines are exact on long
    # triangles, vertices alone miss walls whose corners lie outside the band.
    vertices = turret.vertices
    points = [vertices[(vertices[:, 2] >= trim) & (vertices[:, 2] <= trim+4.0)]]
    for z in np.arange(trim+0.25, trim+4.01, 0.25):
        section = turret.section([0, 0, 1], [0, 0, z])
        if section is not None:
            points.append(np.asarray(section.vertices))
    band = np.vstack([p for p in points if len(p)])
    delta = band[:, :2]-[x, y]
    radius = np.hypot(delta[:, 0], delta[:, 1])
    sector = ((np.arctan2(delta[:, 1], delta[:, 0])+np.pi)/(2*np.pi)*36).astype(int) % 36
    reach = np.array([float(radius[sector == s].max()) for s in range(36) if (sector == s).any()])
    # A few narrow sectors (gun slot, open hatch) must not shrink the bearing.
    turret_reach = float(np.percentile(reach, 15)) if len(reach) >= 18 else float(np.median(radius))
    warnings = []
    bearing = min(max(8.0, hole_radius+1.5), turret_reach-1.0)
    if bearing < 6.0:
        bearing = 6.0
        warnings.append("Narrow turret base: bearing disk may show outside turret outline")
    # The hull cap closes the ring hole and must overlap the surrounding deck.
    cap = max(bearing, hole_radius+1.5)
    turret_hits = RayMeshIntersector(turret)
    roof = ray_up(turret_hits, x, y, trim+0.05)
    hub_top = float(min(roof+0.5, trim+12.0)) if np.isfinite(roof) else trim+5.8
    return {"axis_xy_mm": [float(x), float(y)], "bone_origin_z_mm": float(axis_z),
            "deck_z_mm": deck_z, "trim_z_mm": trim, "ring_hole_radius_mm": hole_radius,
            "bearing_radius_mm": float(bearing), "cap_radius_mm": float(cap),
            "turret_base_reach_p15_mm": turret_reach,
            "hub_top_z_mm": hub_top, "deck_profile_r_z_mm": profile, "warnings": warnings}


def build_recipe(glb, scale, vehicle_id, display_name=None):
    import bpy
    import trimesh
    from inspect_scene import import_model, reset_scene
    glb = Path(glb).resolve()
    reset_scene()
    import_model(glb)
    unit = 1000.0/scale
    objects = list(bpy.context.scene.objects)
    turret, assignment, excluded, notes, meshes = classify(objects, unit)
    parts = sorted(set(assignment.values()))
    tracked = any(re.search(TRACK_BELT, n) for n, p in assignment.items() if p.startswith("running_gear"))
    sheets = sorted(n for n, p in assignment.items() if p.startswith("running_gear") and re.search(TRACK_BELT, n))
    if not tracked:
        # Wheeled: separate wheel sets would show their glue plate between wheels.
        for name, part in assignment.items():
            if part.startswith("running_gear"):
                assignment[name] = "hull"
        notes.append("No track belt found: wheels/suspension stay on the hull part")
        parts = sorted(set(assignment.values()))
    turret_cfg = {"mode": "none"}
    if turret and "turret" in parts:
        hull = trimesh.util.concatenate([meshes[n] for n, p in assignment.items() if p == "hull"])
        body = trimesh.util.concatenate([meshes[n] for n, p in assignment.items() if p == "turret"])
        origin = np.asarray(bpy.data.objects[turret].matrix_world.translation)*unit
        ring = measure_ring(hull, body, origin)
        turret_cfg = {"mode": "rotating", "root": turret, "part": "turret", **ring,
                      "vertical_clearance_mm": 0.3, "cap_depth_mm": 4.2, "disk_thickness_mm": 0.8,
                      "hub_radius_mm": 4.0, "bearing_pad_radius_mm": 5.0,
                      "pin_owner": "hull", "pin_diameter_mm": 5.0, "pin_engagement_mm": 3.0,
                      "bore_depth_mm": 3.4, "radial_clearance_mm": 0.2, "pin_tip_chamfer_mm": 0.25,
                      "ring_eccentric_margin_mm": 0.15, "protected_core_radius_mm": 5.1,
                      "sweep_band_mm": 0.25, "sweep_excluded_parts": ["gun_group"]}
    elif "turret" in parts:
        notes.append("Turret geometry without bone origin: turret glued fixed")
    gun_cfg = {}
    if "gun_group" in parts and turret_cfg.get("mode") == "rotating" and "bone_gun" in bpy.data.objects:
        pivot = np.asarray(bpy.data.objects["bone_gun"].matrix_world.translation)*unit
        gun_cfg = {"part": "gun_group", "pivot_mm": pivot.tolist(), "auto_elevate": True, "max_elevation_deg": 12}
    orientation = {"hull": "as_is", "turret": "as_is", "gun_group": "muzzle_up",
                   "running_gear_left": "left_inner_down", "running_gear_right": "right_inner_down"}
    # The gun always joins a body: the turret when there is one, otherwise the
    # hull (casemate/assault guns, or a bone_turret that only carries the gun).
    # A free gun part would need reviewed glue keys, which are never guessed.
    merge = {}
    if "gun_group" in parts:
        merge["gun_group"] = "turret" if "turret" in parts else "hull"
        if merge["gun_group"] == "hull":
            notes.append("No turret body: fixed gun merged into the hull (merge_into hull)")
    reliefs = [["hull", p] for p in parts if p.startswith("running_gear")]
    if "gun_group" in parts and "turret" in parts:
        reliefs.append(["turret", "gun_group"])
        reliefs.append(["hull", "gun_group"])
    digest = hashlib.sha256(glb.read_bytes()).hexdigest()
    return {
        "schema": SCHEMA, "vehicle_id": vehicle_id, "display_name": display_name or vehicle_id,
        "source_glb_sha256": digest, "source_file": glb.name, "source_unit": "metre",
        "scale_denominator": int(scale), "validated_scales": [int(scale)], "profile": PROFILE,
        "minimum_structural_thickness_mm": 0.8,
        "objects": dict(sorted(assignment.items())), "excluded_objects": excluded,
        "sheet_objects": sheets,
        "parts": [{"name": p, "orientation": orientation.get(p, "as_is"),
                   **({"merge_into": merge[p]} if p in merge else {})} for p in parts],
        "turret": turret_cfg, "gun": gun_cfg,
        "running_gear_backplate": {"enabled": tracked, "thickness_mm": 2.0, "inset_mm": 0.6,
                                   "inner_offset_mm": 0.35, "x_margin_fraction": 0.035,
                                   "z_low_fraction": 0.175, "z_high_fraction": 0.16},
        "assembly_reliefs": reliefs, "glue_keys": [],
        "attachment": dict(ATTACHMENT_DEFAULTS),
        "glue_clearance_per_side_mm": 0.15,
        "notes": notes,
        "review": {"auto_generated": True, "generator": "auto_recipe.py",
                   "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                   "human_reviewed": False,
                   "check": "Compare source_inspection preview, part assignment and assembly_exploded.png"},
        "physical_calibration_passed": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="recipes/<vehicle_id>.json")
    parser.add_argument("--scale", type=int, default=72)
    parser.add_argument("--display-name")
    args = parser.parse_args(argv)
    vehicle = args.output.stem
    if not re.fullmatch(r"[a-z0-9_]+", vehicle):
        parser.error("Recipe file name must be the exact vehicle ID")
    recipe = build_recipe(args.input, args.scale, vehicle, args.display_name)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(recipe, indent=2, ensure_ascii=False), encoding="utf-8")
    counts = {}
    for part in recipe["objects"].values():
        counts[part] = counts.get(part, 0)+1
    print(json.dumps({"recipe": str(args.output), "parts": counts, "excluded": len(recipe["excluded_objects"]),
                      "turret": {k: recipe["turret"].get(k) for k in ("mode", "deck_z_mm", "trim_z_mm", "bearing_radius_mm", "ring_hole_radius_mm")},
                      "notes": recipe["notes"]}, indent=2), flush=True)


if __name__ == "__main__":
    main()

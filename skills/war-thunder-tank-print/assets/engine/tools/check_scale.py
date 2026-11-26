"""Measure an exported Pantsir reference; this does not certify print-ready meshes."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

import bpy
import numpy as np
from mathutils import Matrix

from inspect_scene import import_model, reset_scene, render_preview

PROJECT = Path(__file__).resolve().parents[1]


def measured_vertices(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        indices = {i for t in mesh.loop_triangles for i in t.vertices}
        return np.asarray([evaluated.matrix_world @ mesh.vertices[i].co for i in indices], dtype=float)
    finally:
        evaluated.to_mesh_clear()


def combine_bounds(rows):
    boxes = np.array([r["bounds_metres_xyz"] for r in rows])
    bounds = np.array([boxes[:, 0].min(axis=0), boxes[:, 1].max(axis=0)])
    return bounds, bounds[1] - bounds[0]


def ancestors(obj):
    names = [obj.name]
    while obj.parent:
        obj = obj.parent
        names.append(obj.name)
    return names


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=PROJECT / "raw/ussr_pantsyr_s1/pantsyr_s1_0.glb")
    parser.add_argument("--output", type=Path, default=PROJECT / "outputs/pantsir_1_72")
    parser.add_argument("--scale", type=float, default=72)
    parser.add_argument("--render", action="store_true")
    args = parser.parse_args()
    if args.scale <= 0:
        parser.error("Scale denominator must be positive")
    source = args.input.resolve()
    output = args.output.resolve()
    if not output.is_relative_to(PROJECT) or output == PROJECT:
        raise ValueError("Reference output must stay inside project")
    output.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = json.loads((source.parent / "extraction_manifest.json").read_text(encoding="utf-8"))
    if digest != manifest["sha256"]:
        raise RuntimeError("Raw source SHA256 mismatch")
    reset_scene()
    import_model(source)
    bpy.context.view_layer.update()
    objects = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    rows = []
    for obj in objects:
        vertices = measured_vertices(obj)
        if not len(vertices):
            continue
        chain = ancestors(obj)
        # Chassis = body/cab/wheels/suspension and attached chassis details;
        # omit the complete rotating combat module and its direct root meshes.
        chassis = not any(re.match(r"^(bone_turret|turret|bone_gun|gun_|bone_rocket)", name, re.I)
                          for name in chain)
        bounds = [vertices.min(axis=0).tolist(), vertices.max(axis=0).tolist()]
        rows.append({"name": obj.name, "ancestors": chain, "chassis": chassis,
                     "referenced_vertices": len(vertices), "bounds_metres_xyz": bounds})
    all_bounds, all_extents = combine_bounds(rows)
    chassis_rows = [r for r in rows if r["chassis"]]
    chassis_bounds, chassis_extents = combine_bounds(chassis_rows)
    factor = 1000 / args.scale
    all_mm = all_extents * factor
    chassis_mm = chassis_extents * factor
    inventory = json.loads((source.parent / "geometry_inventory.json").read_text(encoding="utf-8"))
    expected_blender = np.asarray(inventory["extents_world"])[[0, 2, 1]]
    importer_delta = np.abs(all_extents - expected_blender)
    if np.max(importer_delta) > 0.01:
        raise RuntimeError(f"Unexpected import scale/axis difference: {importer_delta}")
    # This allowance is a planning envelope, not a generated-support guarantee.
    brim_each_side = 3.0
    support_extra_each_side = 5.0
    reserve = 2 * (brim_each_side + support_extra_each_side)
    footprint = chassis_mm[:2] + reserve
    status = "reference_fits_planning_envelope" if bool(np.all(footprint <= 170) and chassis_mm[2] <= 180) else "reference_exceeds_planning_envelope"
    report = {
        "vehicle_id": manifest["vehicle_id"], "status": status,
        "source": str(source), "source_sha256": digest,
        "exporter_commit": manifest["exporter_commit"], "source_grp": manifest["model"]["grp"],
        "blender_version": bpy.app.version_string, "scale_denominator": args.scale,
        "coordinate_order": "X length, Y width, Z height (Blender Z-up)",
        "units": {"source": "metres", "output": "millimetres", "multiplier": factor,
                  "verification": "glTF specifies metres; exporter copies decoded vertex/skeleton distances without an additional unit multiplier. Blender import swaps Y-up to Z-up without length scaling. Vehicle-size plausibility checked; not a survey of a physical vehicle.",
                  "references": ["https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html#coordinate-system-and-units",
                                 "https://wiki.warthunder.com/cdk/249-creating-a-3d-tank-model"],
                  "exporter_source": "vendor/wt_asset_explorer/dae_core/parse/gltf_conv.py: skeleton translation copies tm[:3,3]; mesh positions preserve coordinates; wt_mirror_z scale [1,1,-1] changes handedness only"},
        "full_assembly_metres_xyz": all_extents.tolist(),
        "full_assembly_mm_xyz": all_mm.tolist(),
        "chassis_selection": "Meshes outside bone_turret/turret/bone_gun/gun_/bone_rocket ancestor branches; all source chassis/cab/wheel/suspension parts retained, no longitudinal cuts",
        "chassis_metres_xyz": chassis_extents.tolist(), "chassis_mm_xyz": chassis_mm.tolist(),
        "full_bounds_metres_xyz": all_bounds.tolist(), "chassis_bounds_metres_xyz": chassis_bounds.tolist(),
        "chassis_meshes": [r["name"] for r in chassis_rows], "meshes": rows,
        "blender_vs_gltf_extents_delta_metres_xyz": importer_delta.tolist(),
        "planning_allowance": {"brim_each_side_mm": brim_each_side,
                               "additional_support_each_side_mm": support_extra_each_side,
                               "chassis_footprint_with_allowance_mm_xy": footprint.tolist(),
                               "target_footprint_mm_xy": [170, 170],
                               "printer_volume_mm_xyz": [180, 180, 180]},
        "limitations": ["Reference geometry only: not repaired or sliced.",
                        "Actual support/brim toolpaths still require Bambu Studio validation when Pantsir print parts are prepared.",
                        "Default exported pose includes erect radar/antennae; no alternative travel/deployed pose authored.",
                        "World geometry measured only at triangle-referenced vertices, excluding unused buffer vertices."],
    }
    (output / "scale_check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    original_roots = [o for o in bpy.context.scene.objects if o.parent is None]
    scale_root = bpy.data.objects.new(f"Reference_1_to_{args.scale:g}_millimetres", None)
    bpy.context.collection.objects.link(scale_root)
    for obj in original_roots:
        original = obj.matrix_world.copy()
        obj.parent = scale_root
        obj.matrix_parent_inverse = Matrix.Identity(4)
        obj.matrix_basis = original
    scale_root.scale = (factor, factor, factor)
    scale_root.location.z = -float(all_bounds[0, 2]) * factor
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.unit_settings.scale_length = 0.001
    bpy.context.scene.unit_settings.length_unit = "MILLIMETERS"
    bpy.context.view_layer.update()
    scaled_boxes = []
    for obj in objects:
        vertices = measured_vertices(obj)
        if len(vertices):
            scaled_boxes.append([vertices.min(axis=0), vertices.max(axis=0)])
    scaled_boxes = np.asarray(scaled_boxes)
    scaled_extents = scaled_boxes[:, 1].max(axis=0) - scaled_boxes[:, 0].min(axis=0)
    if not np.allclose(scaled_extents, all_mm, atol=0.002, rtol=0):
        raise RuntimeError(f"Scaled Blender scene differs from measured millimetres: {scaled_extents} vs {all_mm}")
    report["scaled_blender_scene_mm_xyz"] = scaled_extents.tolist()
    report["scaled_blender_scene_matches_report"] = True
    (output / "scale_check.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.render:
        render_preview(output / "pantsir_reference_preview.png", direction=(1.4, -1.7, 1.1), resolution=1400)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / f"pantsir_reference_1_{args.scale:g}.blend"))
    print(json.dumps({"status": status, "assembly_mm": all_mm.tolist(), "chassis_mm": chassis_mm.tolist(),
                      "footprint_with_allowance_mm": footprint.tolist(), "output": str(output)}), flush=True)


if __name__ == "__main__":
    main()

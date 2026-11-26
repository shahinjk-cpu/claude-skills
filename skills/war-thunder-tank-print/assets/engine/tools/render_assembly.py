"""Render reviewable assembly views without altering the saved print geometry."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import bpy
from mathutils import Vector

from inspect_scene import import_model, render_preview


BMPT_PARTS = ("hull", "track_left", "track_right", "turret", "gun_group", "missile_left", "missile_right")
BMPT_SLOTS = {"hull": (0, -25), "track_left": (-110, -35), "track_right": (110, -35), "turret": (0, 60),
              "gun_group": (85, 55), "missile_left": (-65, 65), "missile_right": (-65, 35)}
PARTS = BMPT_PARTS
DIRECTION = (1.4, -1.7, 1.2)


def grid_slots(names, sizes):
    """Exploded layout for any part set: rows in the view plane, no box overlap."""
    order = sorted(names, key=lambda n: -sizes[n][0]*sizes[n][1])
    columns = max(1, round(len(order) ** .5))
    rows = [order[i:i+columns] for i in range(0, len(order), columns)]
    gap = .15*max(max(s) for s in sizes.values())
    slots, y = {}, 0.0
    heights = [max(sizes[n][1] for n in row) for row in rows]
    total = sum(heights)+gap*(len(rows)-1)
    y = total/2
    for row, height in zip(rows, heights):
        width = sum(sizes[n][0] for n in row)+gap*(len(row)-1)
        x = -width/2
        for name in row:
            slots[name] = (x+sizes[name][0]/2, y-height/2)
            x += sizes[name][0]+gap
        y -= height+gap
    return slots


def corners(obj):
    return [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]


def fit_projected_bounds(scene, *_args):
    """Fit horizontal ortho width using actual projected extents and aspect."""
    bpy.context.view_layer.update()
    camera = scene.camera
    camera_inverse = camera.matrix_world.inverted()
    points = [camera_inverse @ point for obj in scene.objects
              if obj.type == "MESH" and not obj.hide_render for point in corners(obj)]
    low = Vector((min(p.x for p in points), min(p.y for p in points)))
    high = Vector((max(p.x for p in points), max(p.y for p in points)))
    center = (low + high) / 2
    extent = high - low
    aspect = (scene.render.resolution_x * scene.render.pixel_aspect_x /
              (scene.render.resolution_y * scene.render.pixel_aspect_y))
    camera.location += camera.matrix_world.to_quaternion() @ Vector((center.x, center.y, 0))
    camera.data.ortho_scale = max(extent.x, extent.y * aspect) * 1.12
    bpy.context.view_layer.update()


def report_points(name):
    return corners(bpy.data.objects[name])


def delete_view_helpers():
    for obj in list(bpy.context.scene.objects):
        if obj.type in ("CAMERA", "LIGHT"):
            bpy.data.objects.remove(obj, do_unlink=True)


def projection_report():
    scene = bpy.context.scene
    camera_inverse = scene.camera.matrix_world.inverted()
    aspect = scene.render.resolution_x / scene.render.resolution_y
    frame = (scene.camera.data.ortho_scale / 2, scene.camera.data.ortho_scale / aspect / 2)
    result = {}
    for name in PARTS:
        obj = bpy.data.objects[name]
        points = [camera_inverse @ point for point in corners(obj)]
        low = [min(p[i] for p in points) for i in (0, 1)]
        high = [max(p[i] for p in points) for i in (0, 1)]
        within = all(-frame[i] < low[i] <= high[i] < frame[i] for i in (0, 1))
        result[name] = {"camera_plane_bounds_mm": [low, high], "inside_frame": within}
    if not all(row["inside_frame"] for row in result.values()):
        raise ValueError("A required part lies outside the rendered camera frame")
    return result


def render_views(blend, output, resolution=1600, report=None):
    global PARTS
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if report:
        PARTS = tuple(p["name"] for p in json.loads(Path(report).read_text(encoding="utf-8"))["parts"])
    import_model(blend)
    missing = [name for name in PARTS if name not in bpy.data.objects]
    if missing:
        raise ValueError(f"Required assembly objects missing: {missing}")
    for obj in bpy.context.scene.objects:
        if obj.type == "MESH":
            obj.hide_render = obj.name not in PARTS
    delete_view_helpers()
    bpy.app.handlers.render_pre.append(fit_projected_bounds)
    try:
        render_preview(output / "assembly_preview.png", direction=DIRECTION, resolution=resolution)
        report = {"assembled": projection_report()}
        # Moving along the view plane preserves each actual part's geometry,
        # size and orientation, while making every group independently visible.
        orientation = (-Vector(DIRECTION)).to_track_quat("-Z", "Y")
        right = orientation @ Vector((1, 0, 0))
        up = orientation @ Vector((0, 1, 0))
        if set(PARTS) == set(BMPT_PARTS):
            slots = BMPT_SLOTS
        else:
            sizes = {}
            for name in PARTS:
                points = [corner for corner in report_points(name)]
                sizes[name] = (max(p.dot(right) for p in points)-min(p.dot(right) for p in points),
                               max(p.dot(up) for p in points)-min(p.dot(up) for p in points))
            slots = grid_slots(PARTS, sizes)
        for name, (x, y) in slots.items():
            obj = bpy.data.objects[name]
            center = sum(corners(obj), Vector()) / 8
            obj.location += right * x + up * y - center
        bpy.context.view_layer.update()
        delete_view_helpers()
        render_preview(output / "assembly_exploded.png", direction=DIRECTION, resolution=resolution)
        report["exploded"] = projection_report()
        # These bounds are conservative projections of complete object boxes.
        # Disjoint boxes guarantee no pair can hide another in this view.
        conflicts = []
        for index, left in enumerate(PARTS):
            a = report["exploded"][left]["camera_plane_bounds_mm"]
            for right_name in PARTS[index + 1:]:
                b = report["exploded"][right_name]["camera_plane_bounds_mm"]
                if all(a[0][i] < b[1][i] and b[0][i] < a[1][i] for i in (0, 1)):
                    conflicts.append([left, right_name])
        report["exploded_projected_box_overlaps"] = conflicts
        report["source_blend_modified"] = False
        (output / "presentation_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        if conflicts:
            raise ValueError(f"Exploded-view projected part boxes overlap: {conflicts}")
    finally:
        bpy.app.handlers.render_pre.remove(fit_projected_bounds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blend", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--resolution", type=int, default=1600)
    parser.add_argument("--report", help="print_report.json naming the parts (default: BMPT set)")
    args = parser.parse_args()
    render_views(args.blend, args.output, args.resolution, args.report)

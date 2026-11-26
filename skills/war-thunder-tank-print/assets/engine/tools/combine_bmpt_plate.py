"""Reposition the verified seven BMPT parts using measured support envelopes.

Uses the existing merged 3MF without changing meshes, rotations, or print settings.
The 3 mm envelope gap is a placement estimate; native slicing supplies final QA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

from package_bambu import (CORE, DEFAULT_EXE, mesh_thumbnails, read_stl,
                           slice_project, slice_status, write_json)
from pipeline import verified_parts

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("hull", "track_left", "track_right", "turret", "gun_group",
         "missile_left", "missile_right")
IDENTITY = [1., 0., 0., 0., 1., 0., 0., 0., 1.]


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def placement(parts, gap=3.):
    """Two columns, based on all-layer extrusion bounds including support/brim."""
    columns = (NAMES[:3], NAMES[3:])
    widths = [max(parts[n]["slice"]["extrusion_size_xy_mm"][0] for n in col)
              for col in columns]
    heights = [sum(parts[n]["slice"]["extrusion_size_xy_mm"][1] for n in col)
               + gap * (len(col)-1) for col in columns]
    width, height = sum(widths)+gap, max(heights)
    if max(width, height) > 170:
        raise ValueError(f"Support envelopes exceed 170 mm: {width}, {height}")
    positions, x = {}, 90-width/2
    for col, column_width in zip(columns, widths):
        y = 90-height/2
        for name in col:
            part = parts[name]
            bounds = part["slice"]["extrusion_bbox_xy_mm"]
            old = part["plate_translation_mm"]
            shift = [x-bounds[0]+old[0], y-bounds[1]+old[1], old[2]]
            size = part["slice"]["extrusion_size_xy_mm"]
            positions[name] = {"translation_mm": shift,
                               "predicted_extrusion_bbox_xy_mm": [x, y, x+size[0], y+size[1]]}
            y += size[1]+gap
        x += column_width+gap
    return positions, [width, height]


def prepare(project, output, model_output, individual_report, profile_dir):
    source_glb = ROOT / "raw" / "ussr_bmpt_72" / "bmpt_72_0.glb"
    verified = verified_parts(model_output, digest(source_glb), 72,
                              ROOT / "recipes" / "ussr_bmpt_72.json")
    valid_files = {p["name"]: model_output/p["path"] for p in verified}
    parts = {p["name"]: p for p in json.loads(individual_report.read_text(encoding="utf-8"))["parts"]}
    if set(parts) != set(NAMES) or set(valid_files) != set(NAMES):
        raise ValueError("Exactly seven verified BMPT parts are required")
    for name, part in parts.items():
        if digest(valid_files[name]) != part["source_sha256"]:
            raise ValueError(f"Stale individual slice/source: {name}")
        if slice_status(part["slice"]) != "passed":
            raise ValueError(f"Individual slice not passed: {name}")
    positions, footprint = placement(parts)
    with zipfile.ZipFile(project) as archive:
        if archive.testzip():
            raise ValueError("Input 3MF CRC failed")
        model = ET.fromstring(archive.read("3D/3dmodel.model"))
        config = ET.fromstring(archive.read("Metadata/model_settings.config"))
    if model.get("unit") != "millimeter":
        raise ValueError("Input 3MF must use millimeters")
    resources = model.find(f"{{{CORE}}}resources")
    resource_before = ET.tostring(resources)
    objects = {o.get("id"): o for o in resources}
    configuration = {}
    for obj in config.findall("object"):
        name = next(m.get("value") for m in obj.findall("metadata") if m.get("key") == "name")
        configuration[obj.get("id")] = name
    items = model.findall(f"{{{CORE}}}build/{{{CORE}}}item")
    if (len(items) != 7 or set(configuration.values()) != set(NAMES)
            or {item.get("objectid") for item in items} != set(configuration)):
        raise ValueError("Merged 3MF object membership mismatch")
    preview_vertices, preview_faces, rows = [], [], []
    for item in items:
        name = configuration[item.get("objectid")]
        transform = list(map(float, item.get("transform", "").split()))
        if len(transform) != 12 or transform[:9] != IDENTITY:
            raise ValueError(f"Unexpected input scale/rotation: {name}")
        components = objects[item.get("objectid")].findall(f"{{{CORE}}}components/{{{CORE}}}component")
        if len(components) != 1:
            raise ValueError(f"Unexpected component hierarchy: {name}")
        component_transform = list(map(float, components[0].get("transform", "1 0 0 0 1 0 0 0 1 0 0 0").split()))
        if component_transform != IDENTITY+[0., 0., 0.]:
            raise ValueError(f"Unexpected component transform: {name}")
        mesh = objects[components[0].get("objectid")].find(f"{{{CORE}}}mesh")
        vertices = [tuple(float(v.get(k)) for k in "xyz") for v in mesh.find(f"{{{CORE}}}vertices")]
        faces = [tuple(int(t.get(k)) for k in ("v1", "v2", "v3"))
                 for t in mesh.find(f"{{{CORE}}}triangles")]
        stl_vertices, stl_faces, _, _ = read_stl(valid_files[name])
        expected_vertices = [tuple(float(f"{v:.9g}") for v in vertex) for vertex in stl_vertices]
        if vertices != expected_vertices or faces != [tuple(face) for face in stl_faces]:
            raise ValueError(f"Merged mesh differs from verified STL: {name}")
        shift = positions[name]["translation_mm"]
        if shift[2] != transform[11]:
            raise ValueError(f"Bed contact height changed: {name}")
        item.set("transform", "1 0 0 0 1 0 0 0 1 " + " ".join(f"{v:.12g}" for v in shift))
        offset = len(preview_vertices)
        preview_vertices.extend(tuple(v[i]+shift[i] for i in range(3)) for v in vertices)
        preview_faces.extend(tuple(i+offset for i in face) for face in faces)
        rows.append({"name": name, "source_stl_sha256": parts[name]["source_sha256"],
                     "mesh_matches_verified_stl": True, "old_translation_mm": transform[9:],
                     **positions[name]})
    if ET.tostring(resources) != resource_before:
        raise ValueError("Geometry resources were modified")
    for meta in config.findall("plate/metadata"):
        if meta.get("key") == "plater_name":
            meta.set("value", "BMPT-72 1:72 - alle 7 Teile")
    print("Verified seven unchanged meshes; rendering spaced-plate previews", flush=True)
    thumbnails = mesh_thumbnails(preview_vertices, preview_faces, output)
    replacements = {"3D/3dmodel.model": ET.tostring(model, encoding="utf-8", xml_declaration=True),
                    "Metadata/model_settings.config": ET.tostring(config, encoding="utf-8", xml_declaration=True),
                    **{"Metadata/"+name: data for name, data in thumbnails.items()}}
    with zipfile.ZipFile(project) as original, zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in original.namelist():
            archive.writestr(name, replacements.pop(name, original.read(name)))
        for name, data in replacements.items():
            archive.writestr(name, data)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip():
            raise ValueError("Output 3MF CRC failed")
        written = ET.fromstring(archive.read("3D/3dmodel.model"))
        if ET.tostring(written.find(f"{{{CORE}}}resources")) != resource_before:
            raise ValueError("Written geometry does not match original")
    return {"status": "packaged_not_sliced", "project": str(output), "project_sha256": digest(output),
            "source_project": str(project), "source_project_sha256": digest(project),
            "vehicle_id": "ussr_bmpt_72", "scale_denominator": 72,
            "part_count": 7, "plate_count": 1, "geometry_unchanged": True,
            "rotation_and_scale_unchanged": True, "z_placement_unchanged": True,
            "resources_sha256": hashlib.sha256(resource_before).hexdigest(),
            "predicted_footprint_xy_mm": footprint, "predicted_support_box_gap_mm": 3.,
            "prediction_note": "Measured individual support envelopes; native combined slice is authoritative.",
            "physical_print_verified": False, "parts": rows,
            "profile_sha256": {p.name: digest(p) for p in profile_dir.glob("*.json")}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    default_output = ROOT/"outputs"/"ussr_bmpt_72_1_72"
    parser.add_argument("--model-output", type=Path, default=default_output)
    parser.add_argument("--bambu-exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--no-slice", action="store_true")
    parser.add_argument("--slice-existing", action="store_true", help="Slice the previously verified spaced project")
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args(argv)
    model_output = args.model_output.resolve()
    directory = model_output/"bambu_gesamt"
    project = directory/"BMPT72_1-72_A1mini.3mf"
    output = directory/"BMPT72_1-72_A1mini_abstand.3mf"
    report_path = directory/"spaced_plate_report.json"
    if args.slice_existing:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if digest(output) != report["project_sha256"] or digest(project) != report["source_project_sha256"]:
            raise ValueError("Prepared/source project changed")
    else:
        report = prepare(project, output, model_output, model_output/"bambu"/"packaging_report.json",
                         directory/"profiles")
        write_json(report_path, report)
    if not args.no_slice:
        report["status"] = "slicing"
        write_json(report_path, report)
        try:
            for name, expected in report["profile_sha256"].items():
                if digest(directory/"profiles"/name) != expected:
                    raise ValueError(f"Profile changed: {name}")
            verified_parts(model_output, digest(ROOT/"raw"/"ussr_bmpt_72"/"bmpt_72_0.glb"), 72,
                           ROOT/"recipes"/"ussr_bmpt_72.json")
            for part in report["parts"]:
                if digest(model_output/"stl"/(part["name"]+".stl")) != part["source_stl_sha256"]:
                    raise ValueError("Source STL changed since placement")
            print("Starting native slice of spaced seven-part plate", flush=True)
            report["slice"] = slice_project(args.bambu_exe.resolve(), output,
                                             directory/"combined_spaced_slice", directory/"profiles", args.timeout)
            report["status"] = slice_status(report["slice"])
        except Exception as error:
            report.update(status="failed", error=str(error))
        write_json(report_path, report)
    print(json.dumps({"status": report["status"], "project": str(output),
                      "error": report.get("error")}), flush=True)
    return 0 if report["status"] in ("passed", "packaged_not_sliced") else 1


if __name__ == "__main__":
    sys.exit(main())

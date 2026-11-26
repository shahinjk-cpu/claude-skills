"""Place every verified part of any vehicle on one A1-mini plate and slice it natively.

Input: the verified STL set (print_report.json) and its individual native slices
(bambu/packaging_report.json). Each part keeps its print orientation; only a
translation and optionally a 90-degree turn about Z (bed normal) are applied.
Placement uses the measured all-layer extrusion envelopes including supports and
brim. The final combined native slice is authoritative for the 170-mm target.
"""
from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import re
import shutil
import sys
import xml.etree.ElementTree as ET
import zipfile

from package_bambu import (CORE, DEFAULT_EXE, IDENTITY, mesh_thumbnails, read_stl,
                           slice_project, slice_status, write_json)
from pipeline import read_json, verified_parts, verify_snapshot

TARGET = 170.0
ORIGIN = (180.0-TARGET)/2


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def envelopes(individual, files):
    """Per part: model size and support/brim envelope relative to the model's XY minimum."""
    rows = {}
    for part in individual["parts"]:
        name = part["name"]
        if name not in files:
            continue
        if part.get("status") != "passed" or slice_status(part["slice"]) != "passed":
            raise ValueError(f"Individual slice not passed: {name}")
        if digest(files[name]) != part["source_sha256"]:
            raise ValueError(f"Stale individual slice/source: {name}")
        lo, hi = part["source_bbox_mm"]
        shift = part["plate_translation_mm"]
        mx, my = lo[0]+shift[0], lo[1]+shift[1]
        e = part["slice"]["extrusion_bbox_xy_mm"]
        rows[name] = {"model_size": [hi[0]-lo[0], hi[1]-lo[1]],
                      "envelope_local": [e[0]-mx, e[1]-my, e[2]-mx, e[3]-my]}
    missing = set(files)-set(rows)
    if missing:
        raise ValueError(f"Individual slices missing for: {sorted(missing)}")
    return rows


def rotated(row, quarter):
    """Envelope rectangle (local to model min) after quarter turns CCW about Z."""
    w, h = row["model_size"]
    a0, b0, a1, b1 = row["envelope_local"]
    if quarter % 2 == 0:
        return [a0, b0, a1, b1]
    # (x, y) -> (-y, x), then shift so the model minimum is at the origin again.
    return [h-b1, a0, h-b0, a1]


def pack(rows, gap, size=TARGET):
    """Bottom-left placement of envelope rectangles; tries orders and quarter turns."""
    names = list(rows)
    best = None
    orders = {
        "area": sorted(names, key=lambda n: -_area(rows[n])),
        "long_side": sorted(names, key=lambda n: -max(_dims(rows[n], 0))),
        "height": sorted(names, key=lambda n: -_dims(rows[n], 0)[1]),
        "width": sorted(names, key=lambda n: -_dims(rows[n], 0)[0]),
    }
    for order in orders.values():
        for turns in itertools.product((0, 1), repeat=len(order)) if len(order) <= 9 else [(0,)*len(order)]:
            placed, ok = [], True
            for name, quarter in zip(order, turns):
                w, h = _dims(rows[name], quarter)
                spot = _bottom_left(placed, w, h, gap, size)
                if spot is None:
                    ok = False
                    break
                placed.append((name, quarter, spot[0], spot[1], w, h))
            if not ok:
                continue
            width = max(p[2]+p[4] for p in placed)
            height = max(p[3]+p[5] for p in placed)
            score = (max(width, height), width*height)
            if best is None or score < best[0]:
                best = (score, placed, [width, height])
    return (best[1], best[2]) if best else (None, None)


def _dims(row, quarter):
    e = rotated(row, quarter)
    return e[2]-e[0], e[3]-e[1]


def _area(row):
    w, h = _dims(row, 0)
    return w*h


def _bottom_left(placed, w, h, gap, size):
    candidates = {(0.0, 0.0)}
    for _, _, x, y, pw, ph in placed:
        candidates |= {(x+pw+gap, y), (x, y+ph+gap), (0.0, y+ph+gap), (x+pw+gap, 0.0)}
    for x, y in sorted(candidates, key=lambda c: (c[1], c[0])):
        if x+w > size+1e-9 or y+h > size+1e-9:
            continue
        if all(x+w+gap <= px+1e-9 or px+pw+gap <= x+1e-9 or y+h+gap <= py+1e-9 or py+ph+gap <= y+1e-9
               for _, _, px, py, pw, ph in placed):
            return x, y
    return None


def read_project_mesh(project):
    with zipfile.ZipFile(project) as archive:
        if archive.testzip():
            raise ValueError(f"CRC failure: {project}")
        model = ET.fromstring(archive.read("3D/3dmodel.model"))
        settings = archive.read("Metadata/project_settings.config")
    mesh = model.find(f"{{{CORE}}}resources/{{{CORE}}}object/{{{CORE}}}mesh")
    vertices = [tuple(float(v.get(k)) for k in "xyz") for v in mesh.find(f"{{{CORE}}}vertices")]
    faces = [tuple(int(t.get(k)) for k in ("v1", "v2", "v3")) for t in mesh.find(f"{{{CORE}}}triangles")]
    return vertices, faces, settings


def write_project(destination, title, items, settings):
    """items: [(name, vertices, faces, translation)] -> one plate, one object per part."""
    model = ET.Element(f"{{{CORE}}}model", unit="millimeter", attrib={"xml:lang": "en-US"})
    ET.SubElement(model, f"{{{CORE}}}metadata", name="Application").text = "BambuStudio-02.08.02.61"
    ET.SubElement(model, f"{{{CORE}}}metadata", name="BambuStudio:3mfVersion").text = "1"
    ET.SubElement(model, f"{{{CORE}}}metadata", name="Title").text = title
    resources = ET.SubElement(model, f"{{{CORE}}}resources")
    build = ET.SubElement(model, f"{{{CORE}}}build")
    config = ET.Element("config")
    preview_vertices, preview_faces = [], []
    for index, (name, vertices, faces, shift) in enumerate(items):
        mesh_id, wrapper_id = 2*index+1, 2*index+2
        obj = ET.SubElement(resources, f"{{{CORE}}}object", id=str(mesh_id), type="model")
        mesh = ET.SubElement(obj, f"{{{CORE}}}mesh")
        points = ET.SubElement(mesh, f"{{{CORE}}}vertices")
        for vertex in vertices:
            ET.SubElement(points, f"{{{CORE}}}vertex", **{k: f"{v:.9g}" for k, v in zip("xyz", vertex)})
        triangles = ET.SubElement(mesh, f"{{{CORE}}}triangles")
        for face in faces:
            ET.SubElement(triangles, f"{{{CORE}}}triangle", **{f"v{i+1}": str(v) for i, v in enumerate(face)})
        wrapper = ET.SubElement(resources, f"{{{CORE}}}object", id=str(wrapper_id), type="model")
        components = ET.SubElement(wrapper, f"{{{CORE}}}components")
        ET.SubElement(components, f"{{{CORE}}}component", objectid=str(mesh_id), transform=IDENTITY)
        ET.SubElement(build, f"{{{CORE}}}item", objectid=str(wrapper_id), printable="1",
                      transform="1 0 0 0 1 0 0 0 1 " + " ".join(f"{v:.12g}" for v in shift))
        entry = ET.SubElement(config, "object", id=str(wrapper_id))
        ET.SubElement(entry, "metadata", key="name", value=name)
        ET.SubElement(entry, "metadata", key="extruder", value="1")
        ET.SubElement(entry, "metadata", face_count=str(len(faces)))
        part = ET.SubElement(entry, "part", id=str(mesh_id), subtype="normal_part")
        ET.SubElement(part, "metadata", key="name", value=name)
        ET.SubElement(part, "mesh_stat", face_count=str(len(faces)), edges_fixed="0", degenerate_facets="0",
                      facets_removed="0", facets_reversed="0", backwards_edges="0")
        offset = len(preview_vertices)
        preview_vertices.extend(tuple(v[i]+shift[i] for i in range(3)) for v in vertices)
        preview_faces.extend(tuple(i+offset for i in f) for f in faces)
    plate = ET.SubElement(config, "plate")
    for key, value in (("plater_id", "1"), ("plater_name", title), ("locked", "false"),
                       ("thumbnail_file", "Metadata/plate_1.png"),
                       ("thumbnail_no_light_file", "Metadata/plate_no_light_1.png"),
                       ("top_file", "Metadata/top_1.png"), ("pick_file", "Metadata/pick_1.png")):
        ET.SubElement(plate, "metadata", key=key, value=value)
    for index in range(len(items)):
        instance = ET.SubElement(plate, "model_instance")
        for key, value in (("object_id", str(2*index+2)), ("instance_id", "0"), ("identify_id", str(index+1))):
            ET.SubElement(instance, "metadata", key=key, value=value)
    types = ('<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
             '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
             '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
             '<Default Extension="png" ContentType="image/png"/></Types>')
    rels = ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
            '<Relationship Target="/Metadata/plate_1.png" Id="rel-2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"/></Relationships>')
    thumbnails = mesh_thumbnails(preview_vertices, preview_faces, destination)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("3D/3dmodel.model", ET.tostring(model, encoding="utf-8", xml_declaration=True))
        archive.writestr("Metadata/model_settings.config", ET.tostring(config, encoding="utf-8", xml_declaration=True))
        archive.writestr("Metadata/project_settings.config", settings)
        for name, data in thumbnails.items():
            archive.writestr("Metadata/"+name, data)


def turn(vertices, quarter):
    if quarter % 2 == 0:
        return list(vertices)
    return [(-y, x, z) for x, y, z in vertices]


def safe_name(text):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_") or "vehicle"


def combine(args):
    model_output = args.model_output.resolve()
    project_root = model_output.parents[1]
    _, source_digest = verify_snapshot(project_root, args.vehicle)
    recipe_path = project_root/"recipes"/f"{args.vehicle}.json"
    verified = verified_parts(model_output, source_digest, args.scale, recipe_path)
    files = {p["name"]: model_output/p["path"] for p in verified}
    individual = read_json(model_output/"bambu"/"packaging_report.json")
    rows = envelopes(individual, files)
    placed, footprint = pack(rows, args.gap)
    directory = model_output/"bambu_gesamt"
    directory.mkdir(exist_ok=True)
    report = {"status": "placing", "vehicle_id": args.vehicle, "scale_denominator": args.scale,
              "part_count": len(files), "plate_count": 1, "gap_mm": args.gap,
              "physical_print_verified": False, "envelopes": rows}
    if placed is None:
        report.update(status="does_not_fit_one_plate",
                      error=("Measured support/brim envelopes do not fit 170 x 170 mm on one plate at "
                             f"1:{args.scale}. Keep the scale and build a multi-plate project, or choose another scale."))
        return report, directory
    recipe = read_json(recipe_path)
    title = f"{recipe.get('display_name') or args.vehicle} 1:{args.scale} - alle {len(files)} Teile"
    projects = {p["name"]: Path(p["project"]) for p in individual["parts"] if p["name"] in files}
    items, rows_out, settings = [], [], None
    x0 = ORIGIN+(TARGET-footprint[0])/2
    y0 = ORIGIN+(TARGET-footprint[1])/2
    for name, quarter, x, y, w, h in placed:
        vertices, faces, settings = read_project_mesh(projects[name])
        stl_vertices, stl_faces, _, _ = read_stl(files[name])
        if vertices != [tuple(float(f"{v:.9g}") for v in vertex) for vertex in stl_vertices] or \
                faces != [tuple(face) for face in stl_faces]:
            raise ValueError(f"Packaged mesh differs from verified STL: {name}")
        vertices = turn(vertices, quarter)
        lo = [min(v[i] for v in vertices) for i in range(3)]
        env = rotated(rows[name], quarter)
        shift = [x0+x-env[0]-lo[0], y0+y-env[1]-lo[1], -lo[2]]
        items.append((name, vertices, faces, shift))
        rows_out.append({"name": name, "quarter_turns_about_z": quarter, "translation_mm": shift,
                         "predicted_envelope_xy_mm": [x0+x, y0+y, x0+x+w, y0+y+h],
                         "source_stl_sha256": digest(files[name]), "mesh_matches_verified_stl": True})
    base = f"{safe_name(recipe.get('display_name') or args.vehicle)}_1-{args.scale}_A1mini"
    project = directory/f"{base}.3mf"
    write_project(project, title, items, settings)
    with zipfile.ZipFile(project) as archive:
        if archive.testzip():
            raise ValueError("Combined 3MF CRC failed")
        built = ET.fromstring(archive.read("3D/3dmodel.model"))
        if len(built.findall(f"{{{CORE}}}build/{{{CORE}}}item")) != len(files):
            raise ValueError("Combined project object count mismatch")
    report.update(status="packaged_not_sliced", project=str(project), project_sha256=digest(project),
                  predicted_footprint_xy_mm=footprint, parts=rows_out, title=title,
                  prediction_note="Measured individual envelopes; combined native slice is authoritative.")
    if args.no_slice:
        return report, directory
    profiles = model_output/"bambu"/"profiles"
    report["slice"] = slice_project(args.bambu_exe.resolve(), project, directory/"combined_slice", profiles, args.timeout)
    report["status"] = slice_status(report["slice"])
    with zipfile.ZipFile(report["slice"]["sliced_file"]) as archive:
        config = ET.fromstring(archive.read("Metadata/model_settings.config"))
        names = sorted(m.get("value") for o in config.findall("object") for m in o.findall("metadata") if m.get("key") == "name")
    if names != sorted(files):
        report.update(status="failed", error=f"Sliced project objects {names} differ from verified parts")
    for name in files:
        if digest(files[name]) != dict((r["name"], r["source_stl_sha256"]) for r in rows_out)[name]:
            report.update(status="failed", error=f"STL changed during slicing: {name}")
    if report["status"] == "passed" and args.deliver_dir:
        deliverable = args.deliver_dir.resolve()/f"{base}.gcode.3mf"
        shutil.copyfile(report["slice"]["sliced_file"], deliverable)
        if digest(deliverable) != digest(report["slice"]["sliced_file"]):
            raise ValueError("Deliverable copy differs from verified slice")
        report["deliverable"] = str(deliverable)
        report["deliverable_sha256"] = digest(deliverable)
    return report, directory


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-output", type=Path, required=True, help="outputs/<vehicle>_1_<scale>")
    parser.add_argument("--vehicle", required=True)
    parser.add_argument("--scale", type=int, required=True)
    parser.add_argument("--gap", type=float, default=3.0, help="mm between measured support envelopes")
    parser.add_argument("--deliver-dir", type=Path, help="Copy the verified .gcode.3mf here")
    parser.add_argument("--bambu-exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--no-slice", action="store_true")
    parser.add_argument("--timeout", type=int, default=3600)
    args = parser.parse_args(argv)
    directory = args.model_output.resolve()/"bambu_gesamt"
    directory.mkdir(parents=True, exist_ok=True)
    try:
        report, directory = combine(args)
    except Exception as error:
        report = {"status": "failed", "error": str(error), "physical_print_verified": False}
    write_json(directory/"combined_report.json", report)
    summary = {k: report.get(k) for k in ("status", "deliverable", "predicted_footprint_xy_mm", "error")}
    if report.get("slice"):
        s = report["slice"]
        summary.update(extrusion_size_xy_mm=s["extrusion_size_xy_mm"], layers=s["layers"],
                       estimated_hours=round(s["estimated_seconds"]/3600, 2), filament_g=s["estimated_filament_g"],
                       warnings=s["slicer_warnings"])
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if report["status"] in ("passed", "packaged_not_sliced") else 1


if __name__ == "__main__":
    sys.exit(main())

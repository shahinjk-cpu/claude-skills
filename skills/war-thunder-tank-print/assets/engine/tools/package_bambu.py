"""Package millimetre STL parts for A1 mini / 0.2 mm / PLA and audit real slices.

One independently editable plate per part. Input orientation is preserved; only
translation to the plate centre and Z=0 is applied. No printer connection occurs.
NumPy, matplotlib and Pillow provide software previews for headless exports.
"""
from __future__ import annotations

import argparse
import copy
from collections import defaultdict
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
import zipfile


DEFAULT_EXE = Path(r"C:\Program Files\Bambu Studio\bambu-studio.exe")
MACHINE = "Bambu Lab A1 mini 0.2 nozzle"
PROCESS = "0.08mm High Quality @BBL A1M 0.2 nozzle"
FILAMENT = "Generic PLA @BBL A1M 0.2 nozzle"
CORE = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
PACKAGE = "http://schemas.bambulab.com/package/2021"
ET.register_namespace("", CORE)
ET.register_namespace("BambuStudio", PACKAGE)
IDENTITY = "1 0 0 0 1 0 0 0 1 0 0 0"


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_profile(root, kind, name, stack=()):
    """Resolve Bambu inheritance AND include templates without installed user state."""
    if name in stack:
        raise ValueError("Profile inheritance cycle: " + " -> ".join((*stack, name)))
    source = root / kind / (name + ".json")
    value = json.loads(source.read_text(encoding="utf-8"))
    result = {}
    if value.get("inherits"):
        result.update(resolve_profile(root, kind, value["inherits"], (*stack, name)))
    for included in value.get("include", []):
        result.update(resolve_profile(root, kind, included, (*stack, name)))
    result.update({k: v for k, v in value.items() if k not in ("inherits", "include")})
    return result


def profiles(exe, output, supports=True):
    root = exe.parent / "resources" / "profiles" / "BBL"
    machine = resolve_profile(root, "machine", MACHINE)
    process = resolve_profile(root, "process", PROCESS)
    filament = resolve_profile(root, "filament", FILAMENT)
    process.update({
        "name": "WT PLA 0.08 mm A1 mini 0.2", "from": "user",
        "layer_height": "0.08", "initial_layer_print_height": "0.1",
        "wall_loops": "4", "sparse_infill_density": "15%",
        "sparse_infill_pattern": "gyroid", "print_sequence": "by layer",
        "enable_support": "1" if supports else "0", "support_type": "tree(auto)",
        "support_style": "default", "support_on_build_plate_only": "0",
        "support_threshold_angle": "30", "support_top_z_distance": "0.16",
        "support_bottom_z_distance": "0.16", "support_object_xy_distance": "0.3",
        "support_interface_top_layers": "3", "brim_type": "outer_only",
        "brim_width": "3", "brim_object_gap": "0.1", "enable_arc_fitting": "0",
        "enable_prime_tower": "0", "outer_wall_speed": ["35"],
        "inner_wall_speed": ["50"], "top_surface_speed": ["30"],
        "process_notes": "War Thunder miniature; A1 mini; 0.2 mm nozzle; PLA. Physical fit unverified.",
    })
    # Keep manufacturer PLA temperatures/flow limits; do not borrow a PETG profile.
    machine["best_object_pos"] = "0.5x0.5"
    process["print_settings_id"] = process["name"]
    machine["printer_settings_id"] = MACHINE
    filament["filament_settings_id"] = [FILAMENT]
    output.mkdir(parents=True, exist_ok=True)
    for name, profile in (("machine", machine), ("process", process), ("filament", filament)):
        write_json(output / (name + ".json"), profile)
    metadata = {"type", "name", "from", "instantiation", "setting_id", "description",
                "compatible_printers", "compatible_printers_condition", "filament_id"}
    combined = {}
    for profile in (machine, process, filament):
        combined.update({k: v for k, v in profile.items() if k not in metadata})
    combined.update({
        "printer_settings_id": MACHINE, "print_settings_id": process["name"],
        "filament_settings_id": [FILAMENT], "filament_ids": [filament.get("filament_id", "GFL99")],
        "filament_colour": ["#808080"], "curr_bed_type": "Textured PEI Plate",
        "bed_type": "Textured PEI Plate", "filament_is_support": ["0"],
    })
    return combined


def read_stl(path):
    """Read binary or ASCII STL, deduplicate identical vertices, reject bad data."""
    data = Path(path).read_bytes()
    triangles = []
    if len(data) >= 84 and 84 + struct.unpack_from("<I", data, 80)[0] * 50 == len(data):
        for values in struct.iter_unpack("<12fH", data[84:]):
            triangles.append([values[3:6], values[6:9], values[9:12]])
    else:
        vertices = [tuple(map(float, match)) for match in re.findall(
            r"\bvertex\s+([-+\deE.]+)\s+([-+\deE.]+)\s+([-+\deE.]+)",
            data.decode("ascii"))]
        if len(vertices) % 3:
            raise ValueError(f"Incomplete ASCII STL triangle: {path}")
        triangles = [vertices[i:i + 3] for i in range(0, len(vertices), 3)]
    if not triangles:
        raise ValueError(f"No triangles in {path}")
    vertices, faces, lookup = [], [], {}
    for triangle in triangles:
        face = []
        for vertex in triangle:
            vertex = tuple(vertex)
            if not all(math.isfinite(value) for value in vertex):
                raise ValueError(f"Non-finite STL coordinate: {path}")
            if vertex not in lookup:
                lookup[vertex] = len(vertices)
                vertices.append(vertex)
            face.append(lookup[vertex])
        if len(set(face)) != 3:
            raise ValueError(f"Degenerate STL triangle: {path}")
        faces.append(face)
    lo = [min(v[i] for v in vertices) for i in range(3)]
    hi = [max(v[i] for v in vertices) for i in range(3)]
    return vertices, faces, lo, hi


def package_project(stl, output, name, settings):
    vertices, faces, lo, hi = read_stl(stl)
    size = [hi[i] - lo[i] for i in range(3)]
    if any(s <= 0 for s in size) or max(size) > 180:
        raise ValueError(f"Part dimensions exceed A1 mini or have zero extent: {size}")
    shift = [90 - (lo[0] + hi[0]) / 2, 90 - (lo[1] + hi[1]) / 2, -lo[2]]
    model = ET.Element(f"{{{CORE}}}model", unit="millimeter", attrib={"xml:lang": "en-US"})
    ET.SubElement(model, f"{{{CORE}}}metadata", name="Application").text = "BambuStudio-02.08.02.61"
    ET.SubElement(model, f"{{{CORE}}}metadata", name="BambuStudio:3mfVersion").text = "1"
    ET.SubElement(model, f"{{{CORE}}}metadata", name="Title").text = name
    resources = ET.SubElement(model, f"{{{CORE}}}resources")
    mesh_object = ET.SubElement(resources, f"{{{CORE}}}object", id="1", type="model")
    mesh = ET.SubElement(mesh_object, f"{{{CORE}}}mesh")
    points = ET.SubElement(mesh, f"{{{CORE}}}vertices")
    for vertex in vertices:
        ET.SubElement(points, f"{{{CORE}}}vertex", **{k: f"{v:.9g}" for k, v in zip("xyz", vertex)})
    triangles = ET.SubElement(mesh, f"{{{CORE}}}triangles")
    for face in faces:
        ET.SubElement(triangles, f"{{{CORE}}}triangle", **{f"v{i+1}": str(v) for i, v in enumerate(face)})
    outer = ET.SubElement(resources, f"{{{CORE}}}object", id="2", type="model")
    components = ET.SubElement(outer, f"{{{CORE}}}components")
    ET.SubElement(components, f"{{{CORE}}}component", objectid="1", transform=IDENTITY)
    build = ET.SubElement(model, f"{{{CORE}}}build")
    ET.SubElement(build, f"{{{CORE}}}item", objectid="2", printable="1",
                  transform="1 0 0 0 1 0 0 0 1 " + " ".join(f"{v:.9g}" for v in shift))
    config = ET.Element("config")
    obj = ET.SubElement(config, "object", id="2")
    ET.SubElement(obj, "metadata", key="name", value=name)
    ET.SubElement(obj, "metadata", key="extruder", value="1")
    ET.SubElement(obj, "metadata", face_count=str(len(faces)))
    part = ET.SubElement(obj, "part", id="1", subtype="normal_part")
    ET.SubElement(part, "metadata", key="name", value=name)
    ET.SubElement(part, "metadata", key="source_file", value=Path(stl).name)
    ET.SubElement(part, "mesh_stat", face_count=str(len(faces)), edges_fixed="0",
                  degenerate_facets="0", facets_removed="0", facets_reversed="0", backwards_edges="0")
    plate = ET.SubElement(config, "plate")
    for key, value in (("plater_id", "1"), ("plater_name", name), ("locked", "false"),
                       ("thumbnail_file", "Metadata/plate_1.png"),
                       ("thumbnail_no_light_file", "Metadata/plate_no_light_1.png"),
                       ("top_file", "Metadata/top_1.png"), ("pick_file", "Metadata/pick_1.png")):
        ET.SubElement(plate, "metadata", key=key, value=value)
    instance = ET.SubElement(plate, "model_instance")
    for key, value in (("object_id", "2"), ("instance_id", "0"), ("identify_id", "1")):
        ET.SubElement(instance, "metadata", key=key, value=value)
    types = '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/><Default Extension="png" ContentType="image/png"/></Types>'
    rels = '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Target="/3D/3dmodel.model" Id="rel-1" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/><Relationship Target="/Metadata/plate_1.png" Id="rel-2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/thumbnail"/></Relationships>'
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("3D/3dmodel.model", ET.tostring(model, encoding="utf-8", xml_declaration=True))
        archive.writestr("Metadata/model_settings.config", ET.tostring(config, encoding="utf-8", xml_declaration=True))
        archive.writestr("Metadata/project_settings.config", json.dumps(settings, ensure_ascii=False))
        thumbnails = mesh_thumbnails(vertices, faces, output)
        for filename, data in thumbnails.items():
            archive.writestr("Metadata/" + filename, data)
    return {"size_mm": size, "source_bbox_mm": [lo, hi], "plate_translation_mm": shift,
            "triangles": len(faces), "source_sha256": hashlib.sha256(Path(stl).read_bytes()).hexdigest()}


def mesh_thumbnails(vertices, faces, output):
    """Software mesh previews keep headless native export independent of OpenGL."""
    os.environ.setdefault("MPLCONFIGDIR", str(Path(output).parent / ".matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    from PIL import Image
    lo = [min(v[i] for v in vertices) for i in range(3)]
    hi = [max(v[i] for v in vertices) for i in range(3)]
    center = [(a + b) / 2 for a, b in zip(lo, hi)]
    radius = max(b - a for a, b in zip(lo, hi)) * .56
    previews = {}
    triangles = [[vertices[v] for v in face] for face in faces]
    for name, elevation, azimuth in (("plate_1.png", 28, -55), ("top_1.png", 90, -90)):
        fig = plt.figure(figsize=(5.12, 5.12), dpi=100)
        axis = fig.add_subplot(projection="3d")
        axis.add_collection3d(Poly3DCollection(triangles, facecolors="#8a9294", linewidths=0, shade=True))
        axis.set(xlim=(center[0]-radius, center[0]+radius), ylim=(center[1]-radius, center[1]+radius),
                 zlim=(center[2]-radius, center[2]+radius))
        axis.set_box_aspect((1, 1, 1))
        axis.view_init(elev=elevation, azim=azimuth)
        axis.set_axis_off()
        fig.subplots_adjust(0, 0, 1, 1)
        buf = io.BytesIO()
        fig.savefig(buf, format="png", transparent=True)
        plt.close(fig)
        previews[name] = buf.getvalue()
    previews["plate_no_light_1.png"] = previews["plate_1.png"]
    # A neutral pick map avoids stale object IDs; interactive Studio regenerates selection buffers.
    buf = io.BytesIO()
    Image.new("RGBA", (512, 512), (0, 0, 0, 0)).save(buf, format="PNG")
    previews["pick_1.png"] = buf.getvalue()
    return previews


def merge_projects(projects, destination, title):
    """Shelf-pack independent objects with 10 mm spacing, preserving orientation."""
    collected, x, y, row_height, total_width = [], 0.0, 0.0, 0.0, 0.0
    for project in projects:
        with zipfile.ZipFile(project) as archive:
            model = ET.fromstring(archive.read("3D/3dmodel.model"))
            config = ET.fromstring(archive.read("Metadata/model_settings.config"))
            settings = archive.read("Metadata/project_settings.config")
        mesh = model.find(f"{{{CORE}}}resources/{{{CORE}}}object/{{{CORE}}}mesh")
        vertices = [tuple(float(v.get(k)) for k in "xyz") for v in mesh.find(f"{{{CORE}}}vertices")]
        faces = [tuple(int(t.get(k)) for k in ("v1", "v2", "v3")) for t in mesh.find(f"{{{CORE}}}triangles")]
        lo = [min(v[i] for v in vertices) for i in range(3)]
        hi = [max(v[i] for v in vertices) for i in range(3)]
        width, height = hi[0]-lo[0], hi[1]-lo[1]
        if x and x + width > 160:
            x, y, row_height = 0, y + row_height + 10, 0
        if max(width, height) > 160 or y + height > 160:
            raise ValueError("Single plate cannot fit inside 160 mm model area; use individual plates")
        collected.append((model, config, vertices, faces, lo, (x, y)))
        total_width = max(total_width, x + width)
        row_height = max(row_height, height)
        x += width + 10
    total_height = y + row_height
    new_model = ET.Element(f"{{{CORE}}}model", unit="millimeter", attrib={"xml:lang": "en-US"})
    ET.SubElement(new_model, f"{{{CORE}}}metadata", name="Application").text = "BambuStudio-02.08.02.61"
    ET.SubElement(new_model, f"{{{CORE}}}metadata", name="BambuStudio:3mfVersion").text = "1"
    resources = ET.SubElement(new_model, f"{{{CORE}}}resources")
    build = ET.SubElement(new_model, f"{{{CORE}}}build")
    new_config = ET.Element("config")
    plate = copy.deepcopy(collected[0][1].find("plate"))
    for instance in list(plate.findall("model_instance")):
        plate.remove(instance)
    for meta in plate.findall("metadata"):
        if meta.get("key") == "plater_name":
            meta.set("value", title)
    preview_vertices, preview_faces = [], []
    positions = []
    for index, (model, config, vertices, faces, lo, pos) in enumerate(collected):
        offset = 2 * index
        shift = (90-total_width/2+pos[0]-lo[0], 90-total_height/2+pos[1]-lo[1], -lo[2])
        for source in model.find(f"{{{CORE}}}resources"):
            obj = copy.deepcopy(source)
            obj.set("id", str(int(obj.get("id"))+offset))
            for component in obj.iter(f"{{{CORE}}}component"):
                component.set("objectid", str(int(component.get("objectid"))+offset))
            resources.append(obj)
        ET.SubElement(build, f"{{{CORE}}}item", objectid=str(2+offset), printable="1",
                      transform="1 0 0 0 1 0 0 0 1 " + " ".join(f"{v:.9g}" for v in shift))
        obj_config = copy.deepcopy(config.find("object"))
        obj_config.set("id", str(2+offset))
        obj_config.find("part").set("id", str(1+offset))
        new_config.append(obj_config)
        instance = ET.SubElement(plate, "model_instance")
        for key, value in (("object_id", str(2+offset)), ("instance_id", "0"), ("identify_id", str(index+1))):
            ET.SubElement(instance, "metadata", key=key, value=value)
        vertex_offset = len(preview_vertices)
        preview_vertices.extend(tuple(v[i]+shift[i] for i in range(3)) for v in vertices)
        preview_faces.extend(tuple(v+vertex_offset for v in face) for face in faces)
        positions.append({"source": str(projects[index]), "translation_mm": shift})
    new_config.append(plate)
    thumbnails = mesh_thumbnails(preview_vertices, preview_faces, destination)
    with zipfile.ZipFile(projects[0]) as first, zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in ("[Content_Types].xml", "_rels/.rels"):
            archive.writestr(name, first.read(name))
        archive.writestr("3D/3dmodel.model", ET.tostring(new_model, encoding="utf-8", xml_declaration=True))
        archive.writestr("Metadata/model_settings.config", ET.tostring(new_config, encoding="utf-8", xml_declaration=True))
        archive.writestr("Metadata/project_settings.config", settings)
        for name, data in thumbnails.items():
            archive.writestr("Metadata/"+name, data)
    return {"part_count": len(projects), "model_footprint_mm": [total_width, total_height], "positions": positions}


def audit_gcode(text):
    """Audit every labelled print extrusion including supports, brim and skirt.

    Startup/purge/wipe machine macros are deliberately excluded: these are not the
    model's footprint. Bead width is included, not merely toolpath centre lines.
    """
    xy = [None, None]
    absolute_xyz, relative_e, e = True, False, 0.0
    layer_z, feature, width = None, "Custom", 0.22
    paths = defaultdict(list)
    arc_count = 0
    for line in text.splitlines():
        if line.startswith("; Z_HEIGHT:"):
            layer_z = float(line.split(":", 1)[1])
        elif line.startswith("; FEATURE:"):
            feature = line.split(":", 1)[1].strip()
        elif line.startswith("; LINE_WIDTH:"):
            width = float(line.split(":", 1)[1])
        code = line.split(";", 1)[0].strip()
        if not code:
            continue
        command = code.split()[0]
        if command == "M83":
            relative_e = True
        elif command == "M82":
            relative_e = False
        elif command == "G90":
            absolute_xyz = True
        elif command == "G91":
            absolute_xyz = False
        values = {k: float(v) for k, v in re.findall(r"([XYZE])([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)", code)}
        if command == "G92":
            e = values.get("E", e)
            xy = [values.get(axis, xy[i]) for i, axis in enumerate("XY")]
        if command not in ("G0", "G1", "G2", "G3"):
            continue
        new_xy = [values.get(axis, xy[i]) if absolute_xyz else
                  (xy[i] + values.get(axis, 0) if xy[i] is not None else None)
                  for i, axis in enumerate("XY")]
        extrusion = values.get("E", 0) if relative_e else values.get("E", e) - e
        if "E" in values:
            e = e + values["E"] if relative_e else values["E"]
        if extrusion > 1e-8 and layer_z is not None and feature not in ("Custom", "Travel"):
            if command in ("G2", "G3"):
                arc_count += 1
            if None not in xy + new_xy and math.dist(xy, new_xy) > 1e-8:
                paths[layer_z].append((tuple(xy), tuple(new_xy), feature, width))
        xy = new_xy
    if not paths:
        raise ValueError("No labelled print extrusion in sliced G-code")
    if arc_count:
        raise ValueError("Unexpected print arcs; disable arc fitting before linear-path QA")
    bounds = [float("inf"), float("inf"), -float("inf"), -float("inf")]
    lengths = defaultdict(float)
    for segments in paths.values():
        for a, b, feature, width in segments:
            lengths[feature] += math.dist(a, b)
            for point in (a, b):
                for i in range(2):
                    bounds[i] = min(bounds[i], point[i] - width / 2)
                    bounds[i + 2] = max(bounds[i + 2], point[i] + width / 2)
    size = [bounds[2] - bounds[0], bounds[3] - bounds[1]]
    inside = bounds[0] >= 0 and bounds[1] >= 0 and bounds[2] <= 180 and bounds[3] <= 180 and max(paths) <= 180
    target = inside and max(size) <= 170 + 1e-6
    report = {"layers": len(paths), "layer_z_min_mm": min(paths), "layer_z_max_mm": max(paths),
              "extrusion_bbox_xy_mm": bounds, "extrusion_size_xy_mm": size,
              "includes_supports_brim_skirt": True, "includes_startup_purge": False,
              "within_180mm_build_volume": inside, "within_170mm_target": target,
              "feature_lengths_mm": dict(sorted(lengths.items())),
              "extrusion_segments": sum(map(len, paths.values())),
              "physical_print_verified": False,
              "layer_summary": [{"z_mm": z, "segments": len(paths[z])} for z in sorted(paths)]}
    return report, paths


def layer_preview(paths, output, title):
    """Selected layers from actual G-code; all layers remain in the slicer project."""
    try:
        os.environ.setdefault("MPLCONFIGDIR", str(Path(output).parent / ".matplotlib"))
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from matplotlib.collections import LineCollection
    except ImportError:
        return False
    zs = sorted(paths)
    selected = sorted({zs[round(i * (len(zs) - 1) / 5)] for i in range(6)})
    colors = {"Outer wall": "#153e75", "Inner wall": "#287d8e", "Support": "#d49319",
              "Support interface": "#e85021", "Brim": "#8a6999", "Bridge": "#d63957"}
    all_points = [p for segments in paths.values() for seg in segments for p in seg[:2]]
    lo = [min(p[i] for p in all_points) - 2 for i in range(2)]
    hi = [max(p[i] for p in all_points) + 2 for i in range(2)]
    cols = min(3 if (hi[0]-lo[0]) > 2*(hi[1]-lo[1]) else 6, len(selected))
    rows = math.ceil(len(selected)/cols)
    fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 3*rows), squeeze=False)
    for axis in axes.flat:
        axis.set_axis_off()
    for axis, z in zip(axes.flat, selected):
        axis.set_axis_on()
        by_feature = defaultdict(list)
        for a, b, feature, width in paths[z]:
            by_feature[feature].append((a, b))
        for feature, segments in by_feature.items():
            axis.add_collection(LineCollection(segments, colors=colors.get(feature, "#669999"), linewidths=.45))
        axis.set(xlim=(lo[0], hi[0]), ylim=(lo[1], hi[1]), aspect="equal", title=f"Z {z:g} mm", xlabel="mm")
    fig.suptitle(title + " | Actual extrusion paths | PLA / 0.2 nozzle / 0.08 layers")
    fig.tight_layout()
    fig.savefig(output, dpi=140)
    plt.close(fig)
    return True


def read_native_result(path):
    """Require the current native run's explicit success and warning evidence."""
    path = Path(path)
    if not path.is_file():
        raise RuntimeError(f"Fresh native result.json missing: {path}")
    result = json.loads(path.read_text(encoding="utf-8"))
    if type(result.get("return_code")) is not int or result["return_code"] != 0:
        raise RuntimeError(f"Native result.json reports failure: {result.get('return_code')}: {result.get('error_string', '')}")
    plates = result.get("sliced_plates")
    if not isinstance(plates, list) or len(plates) != 1:
        raise RuntimeError("Native result.json must describe exactly one sliced plate")
    if not isinstance(plates[0].get("warning_message"), str):
        raise RuntimeError("Native result.json lacks explicit plate warning status")
    return result


def run_native(args, destination, sliced, result_file, timeout):
    """Retry only observed transient Windows access violations, never slicer errors."""
    attempts = []
    for attempt in range(1, 4):
        if sliced.exists():
            sliced.unlink()  # Only this helper's exact output, never an input or directory.
        if result_file.exists():
            result_file.unlink()  # A previous native success must not certify a new run.
        start = time.monotonic()
        result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace",
                                timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        log = result.stdout + "\n" + result.stderr
        (destination / f"cli_attempt_{attempt:02d}.log").write_text(log, encoding="utf-8")
        (destination / "cli.log").write_text(log, encoding="utf-8")
        attempts.append({"attempt": attempt, "returncode": result.returncode,
                         "elapsed_seconds": round(time.monotonic()-start, 3)})
        write_json(destination / "command.json", {"argv": args, "returncode": result.returncode, "attempts": attempts})
        if (result.returncode & 0xFFFFFFFF) != 0xC0000005 or attempt == 3:
            return result, attempts
        print(f"Native access violation; retry {attempt+1}/3: {sliced.name}", flush=True)
        time.sleep(.5 * attempt)
    raise AssertionError("Unreachable retry state")


def slice_project(exe, project, destination, profile_dir, timeout):
    destination.mkdir(parents=True, exist_ok=True)
    sliced = destination / (project.stem + ".gcode.3mf")
    result_file = destination / "result.json"
    args = [str(exe), "--load-settings", str(profile_dir / "machine.json") + ";" + str(profile_dir / "process.json"),
            "--load-filaments", str(profile_dir / "filament.json"), "--arrange", "0", "--orient", "0",
            "--slice", "1", "--outputdir", str(destination), "--export-3mf", sliced.name, str(project)]
    result, attempts = run_native(args, destination, sliced, result_file, timeout)
    if result.returncode != 0 or not sliced.exists():
        raise RuntimeError(f"Bambu slice failed (exit {result.returncode}); inspect {destination}")
    cli_result = read_native_result(result_file)
    with zipfile.ZipFile(sliced) as archive:
        if archive.testzip():
            raise ValueError("Sliced 3MF CRC error")
        entries = [n for n in archive.namelist() if n.endswith(".gcode")]
        if len(entries) != 1:
            raise ValueError(f"Expected one sliced plate; got {entries}")
        data = archive.read(entries[0])
        md5_name = entries[0] + ".md5"
        if md5_name in archive.namelist():
            checksum = archive.read(md5_name).decode().strip()
            if checksum.lower() != hashlib.md5(data).hexdigest():
                raise ValueError("G-code MD5 mismatch")
        embedded = json.loads(archive.read("Metadata/project_settings.config"))
        for key, expected in (("printer_model", "Bambu Lab A1 mini"), ("nozzle_diameter", ["0.2"]),
                              ("filament_type", ["PLA"]), ("layer_height", "0.08")):
            if embedded.get(key) != expected:
                raise ValueError(f"Sliced profile mismatch {key}: {embedded.get(key)!r} != {expected!r}")
    report, paths = audit_gcode(data.decode("utf-8"))
    report["native_attempts"] = attempts
    report["slicer_warnings"] = [p["warning_message"] for p in cli_result["sliced_plates"] if p["warning_message"]]
    report["estimated_seconds"] = sum(p.get("total_predication", 0) for p in cli_result["sliced_plates"])
    report["estimated_filament_g"] = sum(f.get("total_used_g", 0) for p in cli_result["sliced_plates"] for f in p.get("filaments", []))
    report["sliced_file"] = str(sliced)
    report["layer_preview"] = layer_preview(paths, destination / "layers.png", project.stem)
    write_json(destination / "slice_audit.json", report)
    return report


def slice_status(report):
    if not report["within_170mm_target"]:
        return "footprint_failed"
    if report.get("slicer_warnings"):
        return "review_required"
    return "passed"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--input-dir", type=Path)
    inputs.add_argument("--manifest", type=Path, help="JSON list or {parts: [{name,path}]} relative to manifest")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--name", default="war_thunder")
    parser.add_argument("--bambu-exe", type=Path, default=DEFAULT_EXE)
    parser.add_argument("--no-slice", action="store_true")
    parser.add_argument("--single-plate", action="store_true", help="Pack small test parts together without rotating them")
    parser.add_argument("--no-support", action="store_true")
    parser.add_argument("--supports", choices=("auto", "off"), default="auto")
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args(argv)
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    if args.input_dir:
        parts = [{"name": p.stem, "path": p.resolve()} for p in sorted(args.input_dir.glob("*.stl"))]
    else:
        value = json.loads(args.manifest.read_text(encoding="utf-8"))
        parts = value["parts"] if isinstance(value, dict) else value
        parts = [{"name": p["name"], "path": (args.manifest.parent / p["path"]).resolve()} for p in parts]
    if not parts:
        parser.error("No STL parts found")
    settings = profiles(args.bambu_exe.resolve(), out / "profiles", not args.no_support and args.supports != "off")
    reports, prepared = [], []
    for index, part in enumerate(parts, 1):
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", part["name"])[:80]
        stem = f"{args.name}_{index:02d}_{safe}"
        project = out / (stem + ".3mf")
        report = {"name": part["name"], "source": str(part["path"]), "project": str(project)}
        try:
            report.update(package_project(part["path"], project, part["name"], settings))
            prepared.append(project)
            if not args.no_slice and not args.single_plate:
                # Short slice folder: the vehicle ID already names the file (Windows MAX_PATH).
                report["slice"] = slice_project(args.bambu_exe.resolve(), project, out / f"{index:02d}_{safe}_slice", out / "profiles", args.timeout)
                report["status"] = slice_status(report["slice"])
            else:
                report["status"] = "packaged_not_sliced"
        except Exception as error:
            report["status"] = "failed"
            report["error"] = str(error)
        reports.append(report)
        print(json.dumps({"part": part["name"], "status": report["status"], "error": report.get("error")}), flush=True)
        write_json(out / "packaging_report.json", {"machine": MACHINE, "filament": FILAMENT, "parts": reports})
    if args.single_plate and all(p["status"] == "packaged_not_sliced" for p in reports):
        project = out / (args.name + ".3mf")
        report = {"name": args.name, "project": str(project)}
        try:
            report.update(merge_projects(prepared, project, args.name))
            if not args.no_slice:
                report["slice"] = slice_project(args.bambu_exe.resolve(), project, out / "combined_slice", out / "profiles", args.timeout)
                report["status"] = slice_status(report["slice"])
            else:
                report["status"] = "packaged_not_sliced"
        except Exception as error:
            report.update(status="failed", error=str(error))
        reports.append(report)
        print(json.dumps({"part": args.name, "status": report["status"], "error": report.get("error")}), flush=True)
        write_json(out / "packaging_report.json", {"machine": MACHINE, "filament": FILAMENT, "parts": reports})
    return 0 if all(p["status"] in ("passed", "packaged_not_sliced") for p in reports) else 1


if __name__ == "__main__":
    sys.exit(main())

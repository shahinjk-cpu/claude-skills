"""Preserve closed indexed topology across binary STL's float32 boundary.

Boolean unions can contain distinct vertices closer than one float32 ULP.
Dropping collapsed faces opens the model. Instead separate only duplicate
positions and collapsed-triangle endpoints by a deterministic bounded movement.
No faces are removed, added or joined. Unchanged face indices prove a surface
distance bound via corresponding barycentric points, without random sampling.
This does not certify self-intersection absence; native slicing remains required.
"""
from __future__ import annotations
import argparse, io, json
from pathlib import Path
import numpy as np
import trimesh


def _component_count(mesh):
    return len(np.unique(trimesh.graph.connected_component_labels(
        mesh.face_adjacency, node_count=len(mesh.faces))))


def stats(mesh):
    _, counts = np.unique(mesh.edges_sorted, axis=0, return_counts=True)
    return {"closed": bool(mesh.is_volume), "watertight": bool(mesh.is_watertight),
            "components": _component_count(mesh), "faces": len(mesh.faces),
            "bad_edges": int(np.sum(counts != 2)), "volume_mm3": float(mesh.volume)}


def prepare_stl_mesh(mesh: trimesh.Trimesh, max_displacement_mm: float = .001):
    """Return a float32-safe mesh and audit, requiring one closed positive body.

    Keeps input indexing/winding. All coordinates become exact float32 values.
    Local separation stays inside the original quantized bounding box, retaining
    the print floor. A fresh binary STL readback must preserve every triangle.
    Caller can export the returned mesh with the standard binary STL exporter.
    """
    if not np.isfinite(max_displacement_mm) or max_displacement_mm <= 0:
        raise ValueError("max_displacement_mm must be finite and positive")
    if not len(mesh.faces) or not np.isfinite(mesh.vertices).all():
        raise ValueError("STL input must contain finite vertices and faces")
    if not mesh.is_volume or _component_count(mesh) != 1:
        raise ValueError("STL input must be one closed positive-volume body")
    reference = np.asarray(mesh.vertices, dtype=np.float64).copy()
    with np.errstate(over="ignore", invalid="ignore"):
        quantized = reference.astype(np.float32).astype(np.float64)
    if not np.isfinite(quantized).all():
        raise ValueError("STL coordinates exceed float32 range")
    base_motion = np.linalg.norm(quantized - reference, axis=1)
    if float(base_motion.max()) > max_displacement_mm:
        raise ValueError("float32 rounding alone exceeds displacement bound")
    lower, upper = quantized.min(axis=0), quantized.max(axis=0)
    rng = np.random.default_rng(872947)
    changed, attempts = set(), []
    result = mesh.copy()
    for step in range(12):
        result.vertices = quantized.copy()
        _, inverse, count = np.unique(np.round(quantized, 8), axis=0,
                                     return_inverse=True, return_counts=True)
        duplicates = np.flatnonzero(count[inverse] > 1)
        degenerate = ~result.nondegenerate_faces(height=2e-6)
        affected = np.unique(np.concatenate([duplicates, result.faces[degenerate].ravel()]))
        attempts.append({"iteration": step, "duplicate_vertices": int(len(duplicates)),
                         "collapsed_triangles": int(degenerate.sum())})
        if not len(affected):
            break
        directions = rng.normal(size=(len(affected), 3))
        directions /= np.linalg.norm(directions, axis=1)[:, None]
        radius = min(.00008 * (1 + step * .25), max_displacement_mm * .75)
        separated = np.clip(reference[affected] + directions * radius, lower, upper)
        quantized[affected] = separated.astype(np.float32).astype(np.float64)
        changed.update(map(int, affected))
    else:
        raise ValueError("Unable to separate collapsed STL topology within bound")
    maximum = float(np.linalg.norm(result.vertices - reference, axis=1).max())
    if maximum > max_displacement_mm:
        raise ValueError("Local STL separation exceeded displacement bound")
    if not result.is_volume or _component_count(result) != 1:
        raise ValueError("STL separation damaged indexed topology")
    loaded = trimesh.load_mesh(io.BytesIO(trimesh.exchange.stl.export_stl(result)),
                               file_type="stl", process=True)
    readback = stats(loaded)
    if (not readback["closed"] or readback["components"] != 1
            or readback["bad_edges"] or len(loaded.faces) != len(mesh.faces)):
        raise ValueError("Binary STL readback did not preserve closed topology")
    audit = {"method": "bounded_local_vertex_separation", "format": "binary_stl_float32",
        "quantized_float32": True, "faces_removed": 0, "faces_added": 0,
        "indexed_topology_preserved": True, "local_separation_vertices": len(changed),
        "max_float32_rounding_mm": float(base_motion.max()),
        "max_corresponding_vertex_displacement_mm": maximum,
        "bidirectional_surface_distance_bound_mm": maximum,
        "surface_bound_basis": "unchanged faces; corresponding barycentric points",
        "requested_displacement_bound_mm": float(max_displacement_mm),
        "volume_before_mm3": float(mesh.volume), "volume_after_mm3": float(result.volume),
        "volume_delta_mm3": float(result.volume - mesh.volume),
        "bounds_delta_mm": (result.bounds - mesh.bounds).tolist(),
        "attempts": attempts, "binary_stl_readback": readback,
        "limitations": ["Local separation preserves topology but does not certify absence of self-intersections.",
                        "Final assembly clearance and native slicing require separate checks."]}
    return result, audit


def probe(snapshot, output, names):
    """Explicit asset integration probe with production print orientations."""
    import manifold3d as md
    transforms = {"hull": np.eye(4), "turret": np.eye(4),
        "track_left": trimesh.transformations.rotation_matrix(np.pi/2, [1,0,0]),
        "track_right": trimesh.transformations.rotation_matrix(-np.pi/2, [1,0,0]),
        "gun_group": trimesh.transformations.rotation_matrix(-np.pi/2, [0,1,0]),
        "missile_left": trimesh.transformations.rotation_matrix(-np.pi/2, [1,0,0]),
        "missile_right": trimesh.transformations.rotation_matrix(np.pi/2, [1,0,0])}
    data = np.load(snapshot)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = []
    for name in names:
        original = trimesh.Trimesh(data[name+"_vertices"], data[name+"_faces"], process=False)
        solid = md.Manifold(md.Mesh64(np.asarray(original.vertices, dtype=np.float64),
                                    np.asarray(original.faces, dtype=np.uint64)))
        candidate = original
        for tolerance in (.01, .001, .0001, 0):
            if not tolerance:
                break
            raw = solid.simplify(tolerance).to_mesh64()
            attempt = trimesh.Trimesh(raw.vert_properties[:,:3], raw.tri_verts, process=False)
            if attempt.is_volume and _component_count(attempt) == 1:
                candidate = attempt
                break
        candidate.apply_transform(transforms[name])
        candidate.apply_translation(-candidate.bounds[0])
        result, audit = prepare_stl_mesh(candidate)
        target = output/f"{name}.stl"
        result.export(target)
        audit.update({"name": name, "simplify_tolerance_mm": tolerance, "file": str(target),
                      "fresh_file_readback": stats(trimesh.load_mesh(target))})
        report.append(audit)
        print(json.dumps(audit), flush=True)
        (output/"precision_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--names", nargs="+", default=["hull", "turret", "track_left", "track_right", "gun_group", "missile_left", "missile_right"])
    args = parser.parse_args()
    probe(args.snapshot, args.output, args.names)

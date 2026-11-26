"""Export exact War Thunder vehicle IDs into immutable, hash-checked GLB snapshots.

Run with the project virtual environment. Game data is read only; all cache and
outputs live below the project directory. No GUI or live game injection is used.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone

PROJECT = Path(__file__).resolve().parents[1]
VENDOR = PROJECT / "vendor" / "wt_asset_explorer"
DEFAULT_GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\War Thunder")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def project_child(path: Path) -> Path:
    path = path.resolve()
    if not path.is_relative_to(PROJECT) or path == PROJECT:
        raise ValueError(f"Output/cache path must be inside {PROJECT}: {path}")
    return path


def inspect_glb(path: Path) -> dict:
    import numpy as np
    import trimesh
    from pygltflib import GLTF2
    gltf = GLTF2().load(str(path))
    scene = trimesh.load_scene(path, process=False)
    meshes = []
    for node_name in scene.graph.nodes_geometry:
        transform, mesh_name = scene.graph[node_name]
        mesh = scene.geometry[mesh_name].copy()
        # glTF material primitives may share a larger POSITION accessor; only
        # referenced vertices belong to this primitive's actual surface.
        mesh.remove_unreferenced_vertices()
        points = trimesh.transform_points(mesh.vertices, transform)
        meshes.append({"node": node_name, "geometry": mesh_name,
                       "vertices": len(mesh.vertices), "triangles": len(mesh.faces),
                       "bounds_world": [points.min(axis=0).tolist(), points.max(axis=0).tolist()],
                       "transform_world": np.asarray(transform).tolist(),
                       "watertight": bool(mesh.is_watertight)})
    parents = {child: i for i, n in enumerate(gltf.nodes) for child in (n.children or [])}
    return {"gltf_asset": dataclasses.asdict(gltf.asset),
            "coordinate_convention": "glTF right-handed Y-up; length unit metres per glTF specification; verify physical plausibility",
            "bounds_world": scene.bounds.tolist(), "extents_world": scene.extents.tolist(),
            "node_count": len(gltf.nodes), "mesh_count": len(gltf.meshes),
            "triangle_count": sum(m["triangles"] for m in meshes),
            "nodes": [{"index": i, "name": n.name, "mesh": n.mesh,
                       "parent": parents.get(i), "children": n.children,
                       "translation": n.translation, "rotation": n.rotation,
                       "scale": n.scale, "matrix": n.matrix} for i, n in enumerate(gltf.nodes)],
            "meshes": meshes}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("vehicles", nargs="+", help="Exact catalog IDs; no fuzzy matching")
    parser.add_argument("--game-dir", type=Path, default=DEFAULT_GAME)
    parser.add_argument("--output-dir", type=Path, default=PROJECT / "raw")
    parser.add_argument("--cache-dir", type=Path, default=PROJECT / "cache" / "exporter")
    args = parser.parse_args()
    for vehicle_id in args.vehicles:
        if not re.fullmatch(r"[a-z0-9_]+", vehicle_id):
            parser.error(f"Invalid exact vehicle ID: {vehicle_id}")
    output = project_child(args.output_dir)
    cache = project_child(args.cache_dir)
    game = args.game_dir.resolve()
    for name in ("aces.vromfs.bin", "char.vromfs.bin", "lang.vromfs.bin"):
        if not (game / name).is_file():
            raise FileNotFoundError(game / name)
    output.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    pending = []
    for vehicle_id in args.vehicles:
        dest = project_child(output / vehicle_id)
        manifest_path = dest / "extraction_manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            glb = dest / manifest["glb_file"]
            if not glb.is_file() or sha256(glb) != manifest["sha256"]:
                raise RuntimeError(f"Raw snapshot integrity failure: {glb}")
            print(f"REUSED immutable snapshot: {glb}", flush=True)
        elif dest.exists() and any(dest.iterdir()):
            raise RuntimeError(f"Refusing to overwrite incomplete raw directory: {dest}")
        else:
            pending.append(vehicle_id)
    if not pending:
        return 0

    # PySide must load before the native Dagor libraries on Windows.
    from PySide6.QtCore import QCoreApplication
    app = QCoreApplication.instance() or QCoreApplication([])
    sys.path.insert(0, str(VENDOR))
    sys.path.insert(0, str(VENDOR / "dae_core"))
    dll_handles = []
    if os.name == "nt":
        dll_handles.append(os.add_dll_directory(str(VENDOR / "lib")))
        os.environ["PATH"] = str(VENDOR / "lib") + os.pathsep + os.environ.get("PATH", "")
        original_popen = subprocess.Popen
        class HiddenPopen(original_popen):
            def __init__(self, *a, **kw):
                kw["creationflags"] = kw.get("creationflags", 0) | subprocess.CREATE_NO_WINDOW
                super().__init__(*a, **kw)
        subprocess.Popen = HiddenPopen
    from wtx.assets import AssetLibrary
    from wtx.vehicles import VehicleCatalog
    wt_ext = PROJECT / "vendor" / "wt_ext_cli-0.6.6" / "wt_ext_cli.exe"
    if not wt_ext.is_file():
        raise FileNotFoundError(wt_ext)

    def say(message):
        print(message, flush=True)

    catalog = VehicleCatalog(game, wt_ext, cache)
    # These read-only mesh exports do not need weapon/icon UI caches.
    catalog._prepare_icons = lambda status: None
    # Vendor cache cleanup stays confined to an explicitly verified local subtree.
    for old in cache.glob("gamedata_*"):
        project_child(old)
        if old.is_symlink():
            raise RuntimeError(f"Unsafe cache symlink: {old}")
    catalog.extract(say, use_cache=True)
    vehicles = {v.id: v for v in catalog.scan(say)}
    missing = [v for v in pending if v not in vehicles]
    if missing:
        raise RuntimeError(f"Exact vehicle IDs absent from current catalog: {missing}")
    library = AssetLibrary(game, cache)
    library.build_index(say)
    library.preload_base_descs(say)
    commit = subprocess.check_output(["git", "-C", str(VENDOR), "rev-parse", "HEAD"], text=True).strip()
    source_signatures = {n: {"bytes": (game / n).stat().st_size,
                             "mtime_ns": (game / n).stat().st_mtime_ns}
                         for n in ("aces.vromfs.bin", "char.vromfs.bin", "lang.vromfs.bin")}
    for vehicle_id in pending:
        vehicle = vehicles[vehicle_id]
        refs = library.find_vehicle_models(vehicle.id, vehicle.model_id)
        say(f"{vehicle_id}: model_id={vehicle.model_id}; candidates=" + repr(refs))
        if not refs:
            raise RuntimeError(f"No model found for exact vehicle ID {vehicle_id}")
        # Prefer exact catalog model; reject ambiguous matching rather than silently
        # selecting a related vehicle variant or a damaged model.
        exact_names = {vehicle.model_id.lower(), vehicle.id.lower(), vehicle.model_id.lower() + "_dynmodel"}
        exact = [r for r in refs if r.name.lower() in exact_names]
        candidates = exact or refs
        names = {r.name.lower() for r in candidates}
        if len(names) != 1:
            raise RuntimeError(f"Ambiguous model mapping for {vehicle_id}: {candidates}")
        ref = candidates[0]  # Vendor orders duplicate models HQ before base content.
        dest = project_child(output / vehicle_id)
        dest.mkdir(parents=True, exist_ok=True)
        library.vehicle_blk = vehicle.path
        glb = Path(library.export_gltf(ref, dest, say, textures=False, lod=0,
                                      animations=False, strip_fx=True, prune_unused=False))
        inspection = inspect_glb(glb)
        (dest / "geometry_inventory.json").write_text(json.dumps(inspection, indent=2), encoding="utf-8")
        manifest = {"vehicle_id": vehicle.id, "display_name": vehicle.name,
                    "catalog_model_id": vehicle.model_id, "model": dataclasses.asdict(ref),
                    "glb_file": glb.name, "sha256": sha256(glb),
                    "exported_utc": datetime.now(timezone.utc).isoformat(),
                    "exporter_commit": commit, "game_dir": str(game),
                    "source_vromfs": source_signatures, "source_grp_sha256": sha256(game / ref.grp),
                    "options": {"textures": False, "lod": 0, "animations": False, "strip_fx": True},
                    "raw_snapshot_policy": "Never overwrite; verify SHA-256 on reuse. Export into a new output directory after a game update.",
                    "extents_world": inspection["extents_world"]}
        (dest / "extraction_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        say(f"EXPORTED {vehicle_id}: {glb}; extents={inspection['extents_world']}; meshes={inspection['mesh_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

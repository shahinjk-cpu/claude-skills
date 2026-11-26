"""Copy the bundled source engine into a fresh project; optionally reuse a local runtime/raw snapshot."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def confined(root: Path, relative: str) -> Path:
    # Reject Windows paths too when this helper happens to run on another OS.
    if not relative or "\\" in relative or ":" in relative:
        raise ValueError(f"Invalid relative path: {relative!r}")
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError(f"Path escapes source root: {relative!r}")
    return path


def bootstrap(destination: Path, *, runtime_project: Path | None = None,
              source_project: Path | None = None, source_vehicle: str | None = None,
              skill_root: Path = SKILL) -> dict:
    skill_root, destination = skill_root.resolve(), destination.resolve()
    engine = skill_root / "assets" / "engine"
    manifest_path = skill_root / "assets" / "engine-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest.get("files")
    if not isinstance(entries, dict) or not entries:
        raise ValueError("Engine manifest has no file hashes")
    if destination.is_relative_to(skill_root) or skill_root.is_relative_to(destination):
        raise ValueError("Destination must be separate from the installed skill")
    if destination.exists() and (not destination.is_dir() or any(destination.iterdir())):
        raise ValueError("Destination must be absent or an empty directory")
    copies: list[tuple[Path, Path]] = []
    for relative, expected in sorted(entries.items()):
        source = confined(engine, relative)
        if not source.is_file() or digest(source) != expected:
            raise ValueError(f"Bundled source integrity failure: {relative}")
        copies.append((source, confined(destination, relative)))

    metadata: dict = {"engine_manifest_sha256": digest(manifest_path),
                      "runtime_project": None, "python_executable": None,
                      "source_vehicle": None, "raw_glb_sha256": None,
                      "status": "source_project_created_not_print_validated"}
    if runtime_project is not None:
        runtime_project = runtime_project.resolve()
        interpreter = runtime_project / ".venv" / "Scripts" / "python.exe"
        if not interpreter.is_file():
            raise ValueError(f"Runtime interpreter missing: {interpreter}")
        metadata.update(runtime_project=str(runtime_project), python_executable=str(interpreter))
    if source_vehicle is not None:
        if not re.fullmatch(r"[a-z0-9_]+", source_vehicle):
            raise ValueError("source_vehicle must be an exact catalog ID")
        source_project = source_project or runtime_project
        if source_project is None:
            raise ValueError("A source or runtime project is required for source_vehicle")
        raw = source_project.resolve() / "raw" / source_vehicle
        raw_manifest = raw / "extraction_manifest.json"
        extraction = json.loads(raw_manifest.read_text(encoding="utf-8-sig"))
        if extraction.get("vehicle_id") != source_vehicle:
            raise ValueError("Raw manifest vehicle ID mismatch")
        glb_name = extraction.get("glb_file", "")
        glb = confined(raw, glb_name)
        if glb.suffix.lower() != ".glb" or digest(glb) != extraction.get("sha256"):
            raise ValueError("Raw GLB hash mismatch or invalid GLB path")
        inventory = raw / "geometry_inventory.json"
        if not inventory.is_file():
            raise ValueError("Raw geometry inventory missing")
        raw_out = destination / "raw" / source_vehicle
        copies.extend((p, raw_out / p.name) for p in (glb, raw_manifest, inventory))
        metadata.update(source_vehicle=source_vehicle, raw_glb_sha256=digest(glb))
    elif source_project is not None:
        raise ValueError("source_project requires source_vehicle")

    # All inputs and guards checked before the first write. Exclusive creation
    # prevents accidental overwrite if another task populated the destination.
    destination.mkdir(parents=True, exist_ok=True)
    for source, output in copies:
        output.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as src, output.open("xb") as dst:
            shutil.copyfileobj(src, dst)
        if digest(source) != digest(output):
            raise RuntimeError(f"Copy verification failed: {output}")
    with (destination / "local_runtime.json").open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return {"project": str(destination), "copied_files": len(copies), **metadata}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--runtime-project", type=Path)
    parser.add_argument("--source-project", type=Path)
    parser.add_argument("--source-vehicle")
    args = parser.parse_args()
    try:
        result = bootstrap(args.destination, runtime_project=args.runtime_project,
                           source_project=args.source_project, source_vehicle=args.source_vehicle)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=True))
        return 1
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

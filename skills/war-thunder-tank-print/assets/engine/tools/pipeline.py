"""Local, fail-closed orchestration for the War Thunder miniature workflow.

Each Blender/FreeCAD/slicer command runs in its own process. No stage contacts a
printer. Raw snapshots and prepared-part provenance are checked before reuse.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid
import zipfile


PROJECT = Path(__file__).resolve().parents[1]
# Generic engine marker. A pipeline.py whose --help lacks this line (and the
# recipe/combine stages) is an old BMPT-only copy, e.g. in the runtime project.
ENGINE_SNAPSHOT = "2026-11-25-generic"
# Bambu Studio cannot export beyond the classic Windows MAX_PATH (260 incl. NUL):
# the slice succeeds, then "Failed exporting 3mf files" (return -13).
WINDOWS_PATH_LIMIT = 259
PANTSIR = "ussr_pantsyr_s1"
STAGES = ("all", "export", "recipe", "check-scale", "inspect", "prepare", "package", "combine",
          "calibration", "check-pantsir")
GEOMETRY_IMPLEMENTATION = ("prepare_vehicle.py", "mesh_repair.py", "inspect_scene.py", "stl_precision.py")
GENERIC_IMPLEMENTATION = ("prepare_generic.py", "prepare_vehicle.py", "mesh_repair.py",
                          "inspect_scene.py", "stl_precision.py", "auto_recipe.py")


def builder_for(recipe):
    """Schema-2 recipes use the generic builder; the reviewed BMPT recipe keeps its own."""
    if recipe.get("schema") == 2:
        return "prepare_generic.py", GENERIC_IMPLEMENTATION
    return "prepare_vehicle.py", GEOMETRY_IMPLEMENTATION


class PipelineError(RuntimeError):
    pass


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def owned_child(base, value):
    base = Path(base).resolve()
    path = (base / value).resolve()
    if path == base or not path.is_relative_to(base):
        raise PipelineError(f"Pfad ausserhalb Arbeitsverzeichnis: {path}")
    return path


def verify_snapshot(project, vehicle):
    directory = owned_child(Path(project) / "raw", vehicle)
    manifest_path = directory / "extraction_manifest.json"
    if not manifest_path.is_file():
        raise PipelineError(f"Originalexport fehlt: {vehicle}. Zuerst --stage export ausfuehren.")
    manifest = read_json(manifest_path)
    if manifest.get("vehicle_id") != vehicle:
        raise PipelineError(f"Falsches Fahrzeug im Exportmanifest: {vehicle}")
    source = owned_child(directory, manifest["glb_file"])
    if source.suffix.lower() != ".glb" or not source.is_file():
        raise PipelineError(f"GLB-Datei fehlt: {source}")
    digest = sha256(source)
    if digest != manifest.get("sha256"):
        raise PipelineError(f"Originalexport veraendert: SHA256 stimmt nicht: {source}")
    return source, digest


def implementation_hashes(tools, files=GEOMETRY_IMPLEMENTATION):
    result = {}
    for name in files:
        path = Path(tools) / name
        if not path.is_file():
            raise PipelineError(f"Geometriewerkzeug fehlt: {path}")
        result[name] = sha256(path)
    return result


def validate_recipe(recipe_path, vehicle, profile, scale):
    recipe_path = Path(recipe_path)
    if not recipe_path.is_file():
        raise PipelineError(f"Fahrzeugrezept fehlt: {recipe_path}")
    recipe = read_json(recipe_path)
    if recipe.get("vehicle_id") != vehicle:
        raise PipelineError("Fahrzeug-ID im Rezept passt nicht zum Auftrag.")
    if recipe.get("profile") != profile:
        raise PipelineError("Druckprofil im Rezept passt nicht zum Auftrag.")
    if scale not in recipe.get("validated_scales", [recipe.get("scale_denominator")]):
        raise PipelineError("Fahrzeugrezept wurde fuer diesen Massstab noch nicht geprueft.")
    return recipe


def verified_parts(output, digest, scale, recipe_path, profile="a1mini_02_pla"):
    """A successful subprocess alone is insufficient to authorize packaging."""
    output = Path(output).resolve()
    report_path = output / "print_report.json"
    if not report_path.is_file():
        raise PipelineError(f"Druckgeometrie-Pruefbericht fehlt: {report_path}. Zuerst --stage prepare.")
    report = read_json(report_path)
    if report.get("geometry_passed") is not True:
        raise PipelineError("Druckgeometrie nicht freigegeben; print_report.json pruefen.")
    if not isinstance(report.get("physical_print_verified"), bool):
        raise PipelineError("Pruefbericht muss physischen Pruefstatus ausdruecklich enthalten.")
    reported_hash = report.get("source_sha256", report.get("source_glb_sha256"))
    if reported_hash != digest:
        raise PipelineError("Druckteile stammen nicht aus aktuellem Originalexport.")
    if report.get("scale_denominator", report.get("scale")) != scale:
        raise PipelineError("Massstab der Druckteile stimmt nicht mit Auftrag ueberein.")
    recipe_path = Path(recipe_path).resolve()
    recipe = validate_recipe(recipe_path, recipe_path.stem, profile, scale)
    if report.get("vehicle_id") != recipe_path.stem or report.get("profile") != profile:
        raise PipelineError("Fahrzeug/Druckprofil im Pruefbericht passt nicht zum Auftrag.")
    if report.get("recipe_sha256") != sha256(recipe_path):
        raise PipelineError("Fahrzeugrezept seit Geometriepruefung geaendert; --stage prepare erneut ausfuehren.")
    if report.get("implementation_sha256") != implementation_hashes(recipe_path.parent.parent / "tools",
                                                                    builder_for(recipe)[1]):
        raise PipelineError("Geometriecode seit Pruefung geaendert; --stage prepare erneut ausfuehren.")
    items = report.get("parts")
    if not isinstance(items, list) or not items:
        raise PipelineError("Keine geprueften Druckteile im Pruefbericht.")
    result, names, files = [], set(), set()
    for item in items:
        if not isinstance(item, dict) or not item.get("name") or not item.get("exported_stl"):
            raise PipelineError("Jeder Druckteil-Eintrag braucht name und exported_stl.")
        path = owned_child(output / "stl", owned_child(output, item["exported_stl"]))
        if path.suffix.lower() != ".stl" or not path.is_file() or path.stat().st_size == 0:
            raise PipelineError(f"Gepruefte STL fehlt oder ist leer: {path}")
        expected = item.get("exported_stl_sha256", item.get("sha256"))
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise PipelineError(f"STL-Pruefsumme fehlt oder ist ungueltig: {path}")
        if expected != sha256(path):
            raise PipelineError(f"Gepruefte STL wurde nachtraeglich veraendert: {path}")
        if item["name"] in names or path in files:
            raise PipelineError(f"Doppelter Druckteil-Eintrag: {item['name']}")
        names.add(item["name"])
        files.add(path)
        result.append({"name": item["name"], "path": str(path.relative_to(output))})
    return result


class Pipeline:
    def __init__(self, args, project=PROJECT):
        self.args = args
        self.project = Path(project).resolve()
        self.python = Path(sys.executable).resolve()
        self.tools = self.project / "tools"
        self.output = self.project / "outputs" / f"{args.vehicle}_1_{args.scale}"
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        self.log_dir = self.project / "logs" / f"pipeline_{stamp}_{uuid.uuid4().hex[:8]}"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.events = []

    def log(self, message):
        print(message, flush=True)

    def run(self, name, script, *arguments, python=None, tools=None, cwd=None):
        command = [str(python or self.python), str((tools or self.tools) / script), *map(str, arguments)]
        log = self.log_dir / f"{len(self.events)+1:02d}_{name}.log"
        event = {"stage": name, "argv": command, "log": str(log), "status": "running"}
        self.events.append(event)
        self.log(f"START {name} | Protokoll: {log}")
        start = time.monotonic()
        environment = os.environ.copy()
        environment["PYTHONUNBUFFERED"] = "1"
        environment["MPLCONFIGDIR"] = str(self.project / "runtime" / "matplotlib")
        try:
            with log.open("w", encoding="utf-8") as stream:
                result = subprocess.run(command, cwd=cwd or self.project, env=environment, stdin=subprocess.DEVNULL,
                                        stdout=stream, stderr=subprocess.STDOUT, timeout=self.args.timeout,
                                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            event["returncode"] = result.returncode
            if result.returncode:
                raise PipelineError(f"{name} fehlgeschlagen (Exit {result.returncode}). Protokoll: {log}")
            event["status"] = "completed"
            self.log(f"FERTIG {name}")
        except subprocess.TimeoutExpired as error:
            event["status"] = "failed"
            raise PipelineError(f"{name}: Zeitlimit erreicht. Protokoll: {log}") from error
        except Exception:
            event["status"] = "failed"
            raise
        finally:
            event["elapsed_seconds"] = round(time.monotonic()-start, 3)
            self.write_status("running")

    def summary(self, status, error=None):
        """Machine-readable run state; the only valid source for success/failure."""
        result = {"status": status, "requested_stage": self.args.stage, "vehicle": self.args.vehicle,
                  "scale_denominator": self.args.scale, "profile": self.args.profile,
                  "engine_snapshot": ENGINE_SNAPSHOT, "project": str(self.project),
                  "run_json": str(self.log_dir / "run.json"),
                  "updated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                  "physical_print_verified": False, "output": str(self.output),
                  "events": self.events, "error": error}
        if status != "running":
            for key, path in (("print_report", self.output / "print_report.json"),
                              ("combined", self.output / "bambu_gesamt" / "combined_report.json")):
                try:
                    data = read_json(path)
                except (OSError, ValueError):
                    continue
                if key == "print_report":
                    result["geometry_passed"] = data.get("geometry_passed")
                    result["review_flags"] = data.get("review_flags", [])
                else:
                    # A deliverable counts only if this very run combined it.
                    combined_now = any(e.get("stage") == "combine" and e.get("status") == "completed"
                                       for e in self.events)
                    result["combine_status"] = data.get("status") if combined_now else \
                        f"not_run_in_this_run (last report: {data.get('status')})"
                    result["deliverable"] = data.get("deliverable") if combined_now else None
                    result["deliverable_sha256"] = data.get("deliverable_sha256") if combined_now else None
        return result

    def write_status(self, status, error=None):
        data = self.summary(status, error)
        write_json(self.log_dir / "run.json", data)
        write_json(self.project / "logs" / "latest_run.json", data)
        return data

    def export(self):
        if (self.project / "raw" / self.args.vehicle / "extraction_manifest.json").is_file() and not self.args.reexport:
            verify_snapshot(self.project, self.args.vehicle)
            self.log(f"WIEDERVERWENDET Originalexport {self.args.vehicle} (SHA256 geprueft)")
            return
        if (self.project / "vendor" / "wt_asset_explorer").is_dir():
            self.run("export", "export_vehicle.py", self.args.vehicle)
        else:
            self.export_via_runtime()
        verify_snapshot(self.project, self.args.vehicle)

    def export_via_runtime(self):
        """Bootstrapped projects without vendor/: export in the recorded runtime, copy hash-checked."""
        config = self.project / "local_runtime.json"
        runtime = read_json(config).get("runtime_project") if config.is_file() else None
        if not runtime or not (Path(runtime) / "vendor" / "wt_asset_explorer").is_dir():
            raise PipelineError("Kein Exporter: vendor/wt_asset_explorer fehlt hier und in local_runtime.json; "
                                "Setup-Panzer.ps1 ausfuehren oder --runtime-project beim Bootstrap setzen.")
        runtime = Path(runtime).resolve()
        if not (runtime / "raw" / self.args.vehicle / "extraction_manifest.json").is_file() or self.args.reexport:
            self.run("export", "export_vehicle.py", self.args.vehicle, python=runtime / ".venv" / "Scripts" / "python.exe",
                     tools=runtime / "tools", cwd=runtime)
        source, digest = verify_snapshot(runtime, self.args.vehicle)
        target = owned_child(self.project / "raw", self.args.vehicle)
        if target.exists() and any(target.iterdir()):
            raise PipelineError(f"Abweichender Snapshot bereits vorhanden: {target}; nicht ueberschreiben.")
        target.mkdir(parents=True, exist_ok=True)
        for name in (source.name, "extraction_manifest.json", "geometry_inventory.json"):
            (target / name).write_bytes((source.parent / name).read_bytes())
        if verify_snapshot(self.project, self.args.vehicle)[1] != digest:
            raise PipelineError("Kopierter Originalexport weicht ab.")

    def recipe_path(self):
        return self.project / "recipes" / (self.args.vehicle + ".json")

    def recipe(self):
        """Create or refresh an automatic schema-2 recipe; reviewed recipes are never overwritten."""
        source, digest = verify_snapshot(self.project, self.args.vehicle)
        path = self.recipe_path()
        if path.is_file():
            current = read_json(path)
            review = current.get("review", {})
            fits = (current.get("source_glb_sha256") == digest
                    and self.args.scale in current.get("validated_scales", [current.get("scale_denominator")]))
            if fits and not self.args.regenerate_recipe:
                self.log(f"Rezept vorhanden: {path.name}")
                return
            if current.get("schema") != 2 or review.get("human_reviewed") or not review.get("auto_generated"):
                raise PipelineError("Geprueftes Rezept passt nicht zu Quelle/Massstab; manuell pruefen statt ueberschreiben.")
            (self.log_dir / ("previous_" + path.name)).write_bytes(path.read_bytes())
        arguments = ["--input", source, "--output", path, "--scale", self.args.scale]
        if self.args.display_name:
            arguments += ["--display-name", self.args.display_name]
        self.run("recipe", "auto_recipe.py", *arguments)
        recipe = read_json(path)
        if recipe.get("source_glb_sha256") != digest:
            raise PipelineError("Automatisches Rezept passt nicht zum Originalexport.")

    def check_scale(self):
        """Early feasibility check of the chassis footprint at the requested scale."""
        source, digest = verify_snapshot(self.project, self.args.vehicle)
        output = self.output / "scale_check"
        self.run("check-scale", "check_scale.py", "--input", source, "--output", output, "--scale", self.args.scale)
        report = read_json(output / "scale_check.json")
        if report.get("source_sha256") != digest:
            raise PipelineError("Massstabspruefung passt nicht zur Quelle.")
        if report.get("status") != "reference_fits_planning_envelope":
            raise PipelineError(f"Wanne bei 1:{self.args.scale} zu gross fuer 170 mm inkl. Reserve "
                                f"({report.get('chassis_mm_xyz')}); groesseren Massstabsnenner waehlen oder Teilung planen.")

    def inspect(self):
        source, digest = verify_snapshot(self.project, self.args.vehicle)
        arguments = ["--input", source, "--output", self.output / "source_inspection"]
        if self.args.render_source:
            arguments.append("--render")
        self.run("inspect", "inspect_scene.py", *arguments)
        if verify_snapshot(self.project, self.args.vehicle)[1] != digest:
            raise PipelineError("Originalexport nach Inspektion veraendert.")

    def check_pantsir(self):
        source, digest = verify_snapshot(self.project, PANTSIR)
        output = self.project / "outputs" / f"pantsir_1_{self.args.scale}"
        arguments = ["--input", source, "--output", output, "--scale", self.args.scale]
        if self.args.render_source:
            arguments.append("--render")
        self.run("check-pantsir", "check_scale.py", *arguments)
        report = read_json(output / "scale_check.json")
        if report.get("source_sha256") != digest or report.get("scale_denominator") != self.args.scale:
            raise PipelineError("Pantsir-Pruefbericht passt nicht zu Quelle/Massstab.")
        if report.get("status") != "reference_fits_planning_envelope":
            raise PipelineError("Pantsir ueberschreitet Bauraumreserve; Massstab/Teilung neu planen.")
        verify_snapshot(self.project, PANTSIR)

    def prepare(self):
        source, digest = verify_snapshot(self.project, self.args.vehicle)
        recipe = self.recipe_path()
        if not recipe.is_file():
            raise PipelineError(f"Fahrzeugrezept fehlt: {recipe}. Zuerst --stage recipe ausfuehren.")
        data = validate_recipe(recipe, self.args.vehicle, self.args.profile, self.args.scale)
        builder, _ = builder_for(data)
        self.invalidate_prepared_outputs(digest, recipe)
        self.run("prepare", builder, "--input", source, "--recipe", recipe,
                 "--output", self.output, "--scale", self.args.scale)
        verify_snapshot(self.project, self.args.vehicle)
        verified_parts(self.output, digest, self.args.scale, recipe, self.args.profile)
        report = read_json(self.output / "print_report.json")
        blend = report.get("blend_file", f"bmpt72_1_{self.args.scale}.blend")
        self.run("preview", "render_assembly.py", "--blend", self.output / blend,
                 "--output", self.output, "--report", self.output / "print_report.json")

    def invalidate_prepared_outputs(self, digest, recipe):
        """A failed rebuild must never leave an earlier successful gate active."""
        self.output.mkdir(parents=True, exist_ok=True)
        print_report = self.output / "print_report.json"
        package_report = self.output / "bambu" / "packaging_report.json"
        combined_report = self.output / "bambu_gesamt" / "combined_report.json"
        for path, archive_name in ((print_report, "previous_print_report.json"),
                                   (package_report, "previous_packaging_report.json"),
                                   (combined_report, "previous_combined_report.json")):
            if path.is_file():
                (self.log_dir / archive_name).write_bytes(path.read_bytes())
        write_json(print_report, {"vehicle_id": self.args.vehicle, "profile": self.args.profile,
                   "scale_denominator": self.args.scale, "source_sha256": digest,
                   "recipe_sha256": sha256(recipe), "status": "preparing",
                   "geometry_passed": False, "physical_print_verified": False, "parts": []})
        if package_report.parent.exists():
            write_json(package_report, {"status": "stale", "parts": [],
                       "reason": "Geometry rebuild started; previous slices require regeneration."})
        if combined_report.parent.exists():
            # The delivered .gcode.3mf in the project folder now belongs to older geometry.
            write_json(combined_report, {"status": "stale", "deliverable": None,
                       "reason": "Geometry rebuild started; run package and combine again."})

    def slicer_paths(self, items):
        """Longest files the slicer will write; mirrors package_bambu/combine_plate naming."""
        paths = []
        for index, item in enumerate(items, 1):
            safe = re.sub(r"[^A-Za-z0-9_.-]", "_", item["name"])[:80]
            stem = f"{self.args.vehicle}_{index:02d}_{safe}"
            paths.append(self.output / "bambu" / f"{index:02d}_{safe}_slice" / f"{stem}.gcode.3mf")
        name = self.args.display_name
        try:
            name = name or read_json(self.recipe_path()).get("display_name")
        except (OSError, ValueError):
            pass
        base = re.sub(r"[^A-Za-z0-9._-]+", "_", name or self.args.vehicle).strip("_") or "vehicle"
        paths.append(self.output / "bambu_gesamt" / "combined_slice" / f"{base}_1-{self.args.scale}_A1mini.gcode.3mf")
        return paths

    def check_path_budget(self, items):
        longest = max(self.slicer_paths(items), key=lambda path: len(str(path)))
        if len(str(longest)) > WINDOWS_PATH_LIMIT:
            raise PipelineError(
                f"Ausgabepfad {len(str(longest))} Zeichen > {WINDOWS_PATH_LIMIT} (Windows-Grenze; Bambu Studio "
                f"slict, kann dann aber nicht exportieren): {longest}. Projekt in einen kuerzeren Ordner legen "
                f"(Projektpfad um mindestens {len(str(longest))-WINDOWS_PATH_LIMIT} Zeichen kuerzen).")

    def package(self):
        _, digest = verify_snapshot(self.project, self.args.vehicle)
        recipe = self.recipe_path()
        items = verified_parts(self.output, digest, self.args.scale, recipe, self.args.profile)
        self.check_path_budget(items)
        manifest = self.output / "packaging_manifest.json"
        write_json(manifest, {"parts": items})
        self.run("package", "package_bambu.py", "--manifest", manifest, "--output-dir", self.output / "bambu",
                 "--name", self.args.vehicle, "--supports", "auto")
        report = read_json(self.output / "bambu" / "packaging_report.json")
        if len(report.get("parts", [])) != len(items) or any(p.get("status") != "passed" for p in report["parts"]):
            raise PipelineError("Mindestens eine Druckplatte braucht Nacharbeit; packaging_report.json pruefen.")
        # Detect edits/concurrent rebuilds during a potentially long native slice.
        verified_parts(self.output, digest, self.args.scale, recipe, self.args.profile)
        expected_hashes = {item["name"]: sha256(self.output / item["path"]) for item in items}
        actual_hashes = {part["name"]: part.get("source_sha256") for part in report["parts"]}
        if actual_hashes != expected_hashes:
            raise PipelineError("Slicerpaket stammt nicht aus den aktuell geprueften STL-Dateien.")

    def combine(self):
        """All verified parts on one natively sliced plate: the single deliverable file."""
        _, digest = verify_snapshot(self.project, self.args.vehicle)
        self.check_path_budget(verified_parts(self.output, digest, self.args.scale, self.recipe_path(), self.args.profile))
        self.run("combine", "combine_plate.py", "--model-output", self.output, "--vehicle", self.args.vehicle,
                 "--scale", self.args.scale, "--deliver-dir", self.project)
        report = read_json(self.output / "bambu_gesamt" / "combined_report.json")
        if report.get("status") != "passed":
            raise PipelineError(f"Gesamtplatte nicht freigegeben: {report.get('status')} {report.get('error', '')}")

    def calibration_ready(self):
        """Reuse only checked coupons whose exact STL hashes still match packaging."""
        directory = self.project / "calibration"
        try:
            report = read_json(directory / "calibration_report.json")
            package = read_json(directory / "bambu" / "packaging_report.json")
            if report.get("radial_clearances_mm") != [.15, .20, .25] or report.get("material") != "PLA":
                return False
            if report.get("units") != "mm" or report.get("nozzle_mm") != .2 or report.get("layer_height_mm") != .08:
                return False
            if len(report.get("parts", [])) != 5:
                return False
            for item in report["parts"]:
                if not (item.get("cad_valid") and item.get("mesh_closed") and not item.get("mesh_non_manifold") and item.get("solid_count") == 1):
                    return False
                stl = owned_child(directory, item["stl"])
                matches = [p for p in package["parts"] if p.get("name") == item["name"]]
                if len(matches) != 1 or matches[0].get("source_sha256") != sha256(stl):
                    return False
            combined = [p for p in package["parts"] if p.get("name") == "calibration" and p.get("status") == "passed"]
            if len(combined) != 1 or combined[0].get("slice", {}).get("within_170mm_target") is not True:
                return False
            if combined[0]["slice"].get("slicer_warnings"):
                return False
            with zipfile.ZipFile(directory / "bambu" / "calibration.3mf") as editable:
                if editable.testzip() or "3D/3dmodel.model" not in editable.namelist():
                    return False
            sliced = owned_child(directory, combined[0]["slice"]["sliced_file"])
            with zipfile.ZipFile(sliced) as archive:
                if archive.testzip():
                    return False
                settings = json.loads(archive.read("Metadata/project_settings.config"))
                expected = {"printer_model": "Bambu Lab A1 mini", "nozzle_diameter": ["0.2"],
                            "filament_type": ["PLA"], "layer_height": "0.08", "enable_support": "0"}
                if any(settings.get(k) != v for k, v in expected.items()):
                    return False
                gcode_entries = [n for n in archive.namelist() if n.endswith(".gcode")]
                if len(gcode_entries) != 1:
                    return False
                name = gcode_entries[0]
                if archive.read(name + ".md5").decode().strip().lower() != hashlib.md5(archive.read(name)).hexdigest():
                    return False
            return True
        except (OSError, ValueError, KeyError, TypeError, zipfile.BadZipFile, PipelineError):
            return False

    def freecad_python(self):
        explicit = self.args.freecad_python or os.environ.get("WT_FREECAD_PYTHON")
        if explicit:
            path = Path(explicit).resolve()
            if not path.is_file():
                raise PipelineError(f"FreeCAD-Python fehlt: {path}")
            return path
        preferred = Path(r"C:\Program Files\FreeCAD 1.0\bin\python.exe")
        if preferred.is_file():
            return preferred
        candidates = sorted(Path(os.environ.get("ProgramFiles", r"C:\Program Files")).glob("FreeCAD*/bin/python.exe"), reverse=True)
        if candidates:
            return candidates[0]
        raise PipelineError("FreeCAD-Python nicht gefunden. --freecad-python oder WT_FREECAD_PYTHON setzen.")

    def turret_joint_planned(self):
        """Pin/socket coupons only test a rotating turret joint; the legacy BMPT recipe has one."""
        try:
            recipe = read_json(self.recipe_path())
        except (OSError, ValueError):
            return True
        return recipe.get("schema") != 2 or recipe.get("turret", {}).get("mode") == "rotating"

    def calibration(self):
        if not self.turret_joint_planned():
            self.events.append({"stage": "calibration", "status": "skipped",
                                "reason": "recipe turret.mode is not rotating; no pin/socket joint to calibrate"})
            self.log("UEBERSPRUNGEN calibration: kein Drehturm im Rezept, Zapfen-Passprobe ohne Nutzen.")
            return
        if self.calibration_ready():
            self.events.append({"stage": "calibration", "status": "reused_verified",
                                "project": str(self.project / "calibration" / "bambu" / "calibration.3mf")})
            self.log("WIEDERVERWENDET Kalibrierplatte: Geometrie-Hashes, Profil und Slice geprueft.")
            return
        output = self.project / "calibration"
        self.run("calibration-generate", "make_calibration.py", "--output-dir", output, python=self.freecad_python())
        self.run("calibration-package", "package_bambu.py", "--input-dir", output, "--output-dir", output / "bambu",
                 "--name", "calibration", "--single-plate", "--supports", "off")
        if not self.calibration_ready():
            raise PipelineError("Kalibrierpaket hat abschliessende Pruefung nicht bestanden.")

    def execute(self):
        if self.args.stage == "all":
            self.export()
            self.recipe()
            self.check_scale()
            self.inspect()
            self.prepare()
            self.package()
            self.combine()
            self.calibration()
        else:
            getattr(self, self.args.stage.replace("-", "_"))()


def arguments(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, epilog=f"Engine snapshot: {ENGINE_SNAPSHOT}")
    parser.add_argument("--vehicle", default="ussr_bmpt_72")
    parser.add_argument("--scale", type=int, default=72)
    parser.add_argument("--profile", choices=("a1mini_02_pla",), default="a1mini_02_pla")
    parser.add_argument("--stage", choices=STAGES, default="all")
    parser.add_argument("--render-source", action="store_true")
    parser.add_argument("--freecad-python", type=Path)
    parser.add_argument("--timeout", type=int, default=7200, help="Maximum seconds per child process")
    parser.add_argument("--display-name", help="Human-readable vehicle name for reports and file names")
    parser.add_argument("--regenerate-recipe", action="store_true", help="Rebuild an automatic (unreviewed) recipe")
    parser.add_argument("--reexport", action="store_true", help="Export again even if a verified snapshot exists")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[a-z0-9_]+", args.vehicle):
        parser.error("Fahrzeug braucht exakte ID aus Kleinbuchstaben, Zahlen und Unterstrichen.")
    if not 35 <= args.scale <= 200:
        parser.error("Massstabsnenner muss zwischen 35 und 200 liegen.")
    if args.timeout < 1:
        parser.error("Zeitlimit muss positiv sein.")
    return args


def result_line(data):
    """One parseable final line; read status from run.json, never from echoed text."""
    keys = ("status", "requested_stage", "vehicle", "run_json", "deliverable", "error")
    return "PIPELINE_RESULT " + json.dumps({k: data.get(k) for k in keys}, ensure_ascii=True)


def main(argv=None):
    pipeline = Pipeline(arguments(argv), PROJECT)
    pipeline.log(f"ENGINE {ENGINE_SNAPSHOT} | Projekt: {pipeline.project}")
    try:
        pipeline.write_status("running")
        pipeline.execute()
    except Exception as error:
        data = pipeline.write_status("failed", str(error))
        print(f"FEHLER: {error}\nLaufprotokoll: {pipeline.log_dir / 'run.json'}", file=sys.stderr, flush=True)
        print(result_line(data), flush=True)
        return 1
    data = pipeline.write_status("completed")
    pipeline.log(f"ABGESCHLOSSEN {pipeline.args.stage}. Physischer Druck weiterhin ungeprueft.\nLaufprotokoll: {pipeline.log_dir / 'run.json'}")
    print(result_line(data), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

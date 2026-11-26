"""Provenance and failure-propagation tests; no game or printer needed."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import pipeline

TEST_ROOT = Path(__file__).resolve().parent


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(dir=TEST_ROOT)
        self.root = Path(self.directory.name).resolve()
        self.assertEqual(self.root.parent, TEST_ROOT)
        self.recipe = self.root / "recipes" / "ussr_bmpt_72.json"
        self.recipe.parent.mkdir()
        pipeline.write_json(self.recipe, {"vehicle_id": "ussr_bmpt_72", "profile": "a1mini_02_pla",
                                        "validated_scales": [72], "turret_clearance_mm": .20})
        (self.root / "tools").mkdir()
        for name in pipeline.GEOMETRY_IMPLEMENTATION:
            (self.root / "tools" / name).write_text("# verified geometry implementation\n")

    def tearDown(self):
        self.directory.cleanup()

    def snapshot(self):
        raw = self.root / "raw" / "ussr_bmpt_72"
        raw.mkdir(parents=True)
        source = raw / "tank.glb"
        source.write_bytes(b"fixture original snapshot")
        digest = pipeline.sha256(source)
        manifest = {"vehicle_id": "ussr_bmpt_72", "glb_file": source.name, "sha256": digest}
        pipeline.write_json(raw / "extraction_manifest.json", manifest)
        return source, digest, manifest

    def report(self, digest):
        output = self.root / "outputs" / "ussr_bmpt_72_1_72"
        (output / "stl").mkdir(parents=True)
        stl = output / "stl" / "hull.stl"
        stl.write_bytes(b"fixture previously verified mesh")
        report = {"geometry_passed": True, "physical_print_verified": False,
                  "vehicle_id": "ussr_bmpt_72", "profile": "a1mini_02_pla",
                  "source_sha256": digest, "scale_denominator": 72,
                  "recipe_sha256": pipeline.sha256(self.recipe),
                  "implementation_sha256": pipeline.implementation_hashes(self.root / "tools"),
                  "parts": [{"name": "hull", "exported_stl": "stl/hull.stl",
                             "exported_stl_sha256": pipeline.sha256(stl)}]}
        pipeline.write_json(output / "print_report.json", report)
        return output, stl, report

    def test_modified_raw_source_is_rejected(self):
        source, digest, _ = self.snapshot()
        self.assertEqual(pipeline.verify_snapshot(self.root, "ussr_bmpt_72"), (source, digest))
        source.write_bytes(b"changed")
        with self.assertRaisesRegex(pipeline.PipelineError, "SHA256"):
            pipeline.verify_snapshot(self.root, "ussr_bmpt_72")

    def test_raw_manifest_cannot_escape_snapshot_directory(self):
        source, digest, manifest = self.snapshot()
        manifest["glb_file"] = "../../outside.glb"
        pipeline.write_json(source.parent / "extraction_manifest.json", manifest)
        with self.assertRaisesRegex(pipeline.PipelineError, "ausserhalb"):
            pipeline.verify_snapshot(self.root, "ussr_bmpt_72")

    def test_package_gate_requires_geometry_source_scale_and_exact_mesh(self):
        output, stl, report = self.report("original_hash")
        self.assertEqual(pipeline.verified_parts(output, "original_hash", 72, self.recipe),
                         [{"name": "hull", "path": str(Path("stl/hull.stl"))}])
        for key, replacement in (("geometry_passed", False), ("source_sha256", "other"), ("scale_denominator", 64)):
            altered = dict(report, **{key: replacement})
            pipeline.write_json(output / "print_report.json", altered)
            with self.assertRaises(pipeline.PipelineError):
                pipeline.verified_parts(output, "original_hash", 72, self.recipe)
        pipeline.write_json(output / "print_report.json", report)
        stl.write_bytes(b"mesh modified after verification")
        with self.assertRaisesRegex(pipeline.PipelineError, "nachtraeglich"):
            pipeline.verified_parts(output, "original_hash", 72, self.recipe)

    def test_changed_turret_clearance_requires_new_preparation(self):
        output, _, _ = self.report("original_hash")
        recipe = pipeline.read_json(self.recipe)
        recipe["turret_clearance_mm"] = .25
        pipeline.write_json(self.recipe, recipe)
        with self.assertRaisesRegex(pipeline.PipelineError, "Fahrzeugrezept.*geaendert"):
            pipeline.verified_parts(output, "original_hash", 72, self.recipe)

    def test_changed_geometry_implementation_requires_new_preparation(self):
        output, _, _ = self.report("original_hash")
        (self.root / "tools" / "mesh_repair.py").write_text("# changed repair algorithm\n")
        with self.assertRaisesRegex(pipeline.PipelineError, "Geometriecode.*geaendert"):
            pipeline.verified_parts(output, "original_hash", 72, self.recipe)

    def test_changed_stl_precision_cleanup_requires_new_preparation(self):
        output, _, _ = self.report("original_hash")
        (self.root / "tools" / "stl_precision.py").write_text("# changed final STL topology cleanup\n")
        with self.assertRaisesRegex(pipeline.PipelineError, "Geometriecode.*geaendert"):
            pipeline.verified_parts(output, "original_hash", 72, self.recipe)

    def test_recipe_vehicle_and_profile_must_match_request(self):
        for key, value in (("vehicle_id", "ussr_other_tank"), ("profile", "other_printer")):
            recipe = pipeline.read_json(self.recipe)
            recipe[key] = value
            pipeline.write_json(self.recipe, recipe)
            with self.assertRaises(pipeline.PipelineError):
                pipeline.validate_recipe(self.recipe, "ussr_bmpt_72", "a1mini_02_pla", 72)
            recipe[key] = "ussr_bmpt_72" if key == "vehicle_id" else "a1mini_02_pla"
            pipeline.write_json(self.recipe, recipe)

    def test_missing_stl_hash_cannot_bypass_tamper_gate(self):
        output, _, report = self.report("original_hash")
        del report["parts"][0]["exported_stl_sha256"]
        pipeline.write_json(output / "print_report.json", report)
        with self.assertRaisesRegex(pipeline.PipelineError, "STL-Pruefsumme"):
            pipeline.verified_parts(output, "original_hash", 72, self.recipe)

    def test_failed_rebuild_invalidates_previous_geometry_and_slices(self):
        source, digest, _ = self.snapshot()
        output, _, report = self.report(digest)
        (output / "bambu").mkdir()
        pipeline.write_json(output / "bambu" / "packaging_report.json", {"parts": [{"status": "passed"}]})
        flow = pipeline.Pipeline(pipeline.arguments(["--stage", "prepare"]), self.root)
        with mock.patch.object(flow, "run", side_effect=pipeline.PipelineError("build failed")):
            with self.assertRaisesRegex(pipeline.PipelineError, "build failed"):
                flow.prepare()
        self.assertFalse(pipeline.read_json(output / "print_report.json")["geometry_passed"])
        self.assertEqual(pipeline.read_json(output / "bambu" / "packaging_report.json")["status"], "stale")
        self.assertEqual(pipeline.read_json(flow.log_dir / "previous_print_report.json"), report)

    def test_prepare_refreshes_presentation_after_geometry_gate(self):
        _, digest, _ = self.snapshot()
        output, _, report = self.report(digest)
        flow = pipeline.Pipeline(pipeline.arguments(["--stage", "prepare"]), self.root)
        calls = []
        def completed_stage(name, script, *arguments, **kwargs):
            calls.append((name, script, arguments))
            if name == "prepare":
                pipeline.write_json(output / "print_report.json", report)
        with mock.patch.object(flow, "run", side_effect=completed_stage):
            flow.prepare()
        self.assertEqual([call[0] for call in calls], ["prepare", "preview"])
        self.assertEqual(calls[-1][1], "render_assembly.py")
        self.assertEqual(calls[-1][2], ("--blend", output / "bmpt72_1_72.blend", "--output", output,
                                        "--report", output / "print_report.json"))

    def test_package_gate_does_not_accept_source_or_debug_stl_outside_final_folder(self):
        output, stl, report = self.report("original_hash")
        outside = output / "debug.stl"
        outside.write_bytes(stl.read_bytes())
        report["parts"][0]["exported_stl"] = "debug.stl"
        pipeline.write_json(output / "print_report.json", report)
        with self.assertRaisesRegex(pipeline.PipelineError, "ausserhalb"):
            pipeline.verified_parts(output, "original_hash", 72, self.recipe)

    def test_all_stops_before_packaging_when_preparation_fails(self):
        flow = pipeline.Pipeline(pipeline.arguments([]), self.root)
        calls = []
        for stage in ("export", "recipe", "check_scale", "inspect", "package", "combine", "calibration"):
            setattr(flow, stage, lambda value=stage: calls.append(value))
        def fail():
            calls.append("prepare")
            raise pipeline.PipelineError("source needs repair")
        flow.prepare = fail
        with self.assertRaisesRegex(pipeline.PipelineError, "repair"):
            flow.execute()
        self.assertEqual(calls, ["export", "recipe", "check_scale", "inspect", "prepare"])

    def test_schema_two_recipe_selects_generic_builder_and_its_hash_set(self):
        recipe = pipeline.read_json(self.recipe)
        self.assertEqual(pipeline.builder_for(recipe)[0], "prepare_vehicle.py")
        recipe["schema"] = 2
        builder, files = pipeline.builder_for(recipe)
        self.assertEqual(builder, "prepare_generic.py")
        self.assertIn("auto_recipe.py", files)
        pipeline.write_json(self.recipe, recipe)
        for name in files:
            (self.root / "tools" / name).write_text("# generic implementation\n")
        output, _, report = self.report("original_hash")
        # A report hashed with the legacy file set must not release generic geometry.
        report["implementation_sha256"] = pipeline.implementation_hashes(self.root / "tools")
        pipeline.write_json(output / "print_report.json", report)
        with self.assertRaisesRegex(pipeline.PipelineError, "Geometriecode"):
            pipeline.verified_parts(output, "original_hash", 72, self.recipe)
        report["implementation_sha256"] = pipeline.implementation_hashes(self.root / "tools", files)
        pipeline.write_json(output / "print_report.json", report)
        self.assertEqual(len(pipeline.verified_parts(output, "original_hash", 72, self.recipe)), 1)

    def test_reviewed_recipe_is_never_overwritten_automatically(self):
        self.snapshot()
        recipe = pipeline.read_json(self.recipe)
        recipe.update(schema=2, source_glb_sha256="older_source", review={"auto_generated": True, "human_reviewed": True})
        pipeline.write_json(self.recipe, recipe)
        flow = pipeline.Pipeline(pipeline.arguments(["--stage", "recipe"]), self.root)
        with mock.patch.object(flow, "run") as run:
            with self.assertRaisesRegex(pipeline.PipelineError, "manuell"):
                flow.recipe()
            run.assert_not_called()

    def test_stale_automatic_recipe_is_archived_and_regenerated(self):
        _, digest, _ = self.snapshot()
        recipe = pipeline.read_json(self.recipe)
        recipe.update(schema=2, source_glb_sha256="older_source", review={"auto_generated": True})
        pipeline.write_json(self.recipe, recipe)
        flow = pipeline.Pipeline(pipeline.arguments(["--stage", "recipe"]), self.root)
        def regenerate(name, script, *arguments, **kwargs):
            pipeline.write_json(self.recipe, dict(recipe, source_glb_sha256=digest))
        with mock.patch.object(flow, "run", side_effect=regenerate) as run:
            flow.recipe()
        self.assertEqual(run.call_args[0][1], "auto_recipe.py")
        self.assertEqual(pipeline.read_json(flow.log_dir / "previous_ussr_bmpt_72.json")["source_glb_sha256"], "older_source")

    def test_failed_child_propagates_and_creates_diagnostic_log(self):
        flow = pipeline.Pipeline(pipeline.arguments(["--timeout", "30"]), self.root)
        flow.tools.mkdir(exist_ok=True)
        (flow.tools / "failure.py").write_text("print('test failure detail', flush=True)\nraise SystemExit(7)\n")
        with self.assertRaisesRegex(pipeline.PipelineError, "Exit 7"):
            flow.run("expected-failure", "failure.py")
        event = flow.events[0]
        self.assertEqual(event["status"], "failed")
        self.assertIn("test failure detail", Path(event["log"]).read_text())

    def test_main_failure_is_recorded_in_run_json_and_run_status(self):
        import contextlib
        import io
        import run_status
        with mock.patch.object(pipeline, "PROJECT", self.root), \
                mock.patch.object(pipeline.Pipeline, "execute", side_effect=pipeline.PipelineError("boom")), \
                contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            code = pipeline.main(["--stage", "prepare"])
        self.assertEqual(code, 1)
        latest = pipeline.read_json(self.root / "logs" / "latest_run.json")
        self.assertEqual((latest["status"], latest["error"]), ("failed", "boom"))
        self.assertEqual(latest["engine_snapshot"], pipeline.ENGINE_SNAPSHOT)
        self.assertEqual(pipeline.read_json(Path(latest["run_json"]))["status"], "failed")
        line = [l for l in out.getvalue().splitlines() if l.startswith("PIPELINE_RESULT ")][-1]
        self.assertEqual(json.loads(line.split(" ", 1)[1])["status"], "failed")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_status.main(["--run", str(self.root / "logs" / "latest_run.json")]), 1)
        pipeline.write_json(self.root / "logs" / "latest_run.json", dict(latest, status="completed", error=None))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_status.main(["--run", str(self.root / "logs" / "latest_run.json")]), 0)
            self.assertEqual(run_status.main(["--run", str(self.root / "missing.json")]), 3)

    def test_status_reports_deliverable_only_when_this_run_combined_it(self):
        _, digest, _ = self.snapshot()
        output = self.root / "outputs" / "ussr_bmpt_72_1_72"
        combined = output / "bambu_gesamt" / "combined_report.json"
        combined.parent.mkdir(parents=True)
        pipeline.write_json(combined, {"status": "passed", "deliverable": "old.gcode.3mf", "deliverable_sha256": "abc"})
        flow = pipeline.Pipeline(pipeline.arguments(["--stage", "prepare"]), self.root)
        stale = flow.summary("completed")
        self.assertIsNone(stale["deliverable"])
        self.assertTrue(stale["combine_status"].startswith("not_run_in_this_run"))
        flow.events.append({"stage": "combine", "status": "completed"})
        self.assertEqual(flow.summary("completed")["deliverable"], "old.gcode.3mf")
        flow.invalidate_prepared_outputs(digest, self.recipe)
        self.assertEqual(pipeline.read_json(combined)["status"], "stale")
        self.assertIsNone(pipeline.read_json(combined)["deliverable"])

    def test_overlong_slicer_output_path_fails_before_slicing(self):
        flow = pipeline.Pipeline(pipeline.arguments(["--stage", "package"]), self.root)
        items = [{"name": "running_gear_left"}]
        flow.check_path_budget(items)  # short test root passes
        longest = max(len(str(p)) for p in flow.slicer_paths(items))
        flow.output = Path(str(flow.output) + "x" * (pipeline.WINDOWS_PATH_LIMIT - longest + 1))
        with self.assertRaisesRegex(pipeline.PipelineError, "Windows-Grenze"):
            flow.check_path_budget(items)

    def test_calibration_skipped_without_rotating_turret(self):
        recipe = pipeline.read_json(self.recipe)
        pipeline.write_json(self.recipe, dict(recipe, schema=2, turret={"mode": "none"}))
        flow = pipeline.Pipeline(pipeline.arguments(["--stage", "calibration"]), self.root)
        with mock.patch.object(flow, "run") as run, mock.patch.object(flow, "log"):
            flow.calibration()
            run.assert_not_called()
        self.assertEqual(flow.events[-1]["status"], "skipped")
        pipeline.write_json(self.recipe, dict(recipe, schema=2, turret={"mode": "rotating"}))
        self.assertTrue(flow.turret_joint_planned())
        pipeline.write_json(self.recipe, recipe)  # legacy BMPT recipe keeps its pin coupons
        self.assertTrue(flow.turret_joint_planned())


if __name__ == "__main__":
    unittest.main()

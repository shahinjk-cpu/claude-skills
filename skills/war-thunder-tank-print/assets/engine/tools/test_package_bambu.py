"""Focused regression tests for safety-relevant profile and toolpath checks."""
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
from unittest import mock

import package_bambu as target

TEST_ROOT = Path(__file__).resolve().parent


class ProfileTests(unittest.TestCase):
    def test_inheritance_and_included_start_gcode_are_both_preserved(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as tmp:
            assert Path(tmp).resolve().parent == TEST_ROOT
            root = Path(tmp)
            (root / "machine").mkdir()
            items = {"base": {"nozzle_diameter": ["0.4"], "printable_height": "180"},
                     "start": {"machine_start_gcode": "G28"},
                     "child": {"inherits": "base", "include": ["start"], "nozzle_diameter": ["0.2"]}}
            for name, value in items.items():
                (root / "machine" / (name + ".json")).write_text(json.dumps(value))
            resolved = target.resolve_profile(root, "machine", "child")
            self.assertEqual(resolved["nozzle_diameter"], ["0.2"])
            self.assertEqual(resolved["machine_start_gcode"], "G28")
            self.assertEqual(resolved["printable_height"], "180")


class ToolpathTests(unittest.TestCase):
    prefix = "M83\nG90\nG1 X-20 Y-20 E10\n; Z_HEIGHT: 0.1\n; FEATURE: Outer wall\n; LINE_WIDTH: 0.22\nG1 X10 Y10\n"

    def test_bead_width_and_supports_count_but_startup_purge_does_not(self):
        report, paths = target.audit_gcode(self.prefix + "G1 X20 E1\n; FEATURE: Support\nG1 X175 Y175 E1\n")
        self.assertEqual(report["layers"], 1)
        self.assertAlmostEqual(report["extrusion_bbox_xy_mm"][0], 9.89)
        self.assertAlmostEqual(report["extrusion_bbox_xy_mm"][2], 175.11)
        self.assertTrue(report["within_180mm_build_volume"])
        self.assertIn("Support", report["feature_lengths_mm"])

    def test_bead_overhang_beyond_bed_is_rejected_even_with_centerline_inside(self):
        report, _ = target.audit_gcode(self.prefix + "G1 X179.95 E1\n")
        self.assertFalse(report["within_180mm_build_volume"])

    def test_absolute_extrusion_reset_and_retractions(self):
        text = self.prefix.replace("M83", "M82") + "G92 E0\nG1 X20 E1\nG1 X999 E0\nG1 X20 E1\nG92 E0\nG1 X21 E1\n"
        report, paths = target.audit_gcode(text)
        # Retract-only travel does not count, but subsequent extruding return does.
        self.assertFalse(report["within_180mm_build_volume"])
        self.assertEqual(report["extrusion_segments"], 3)

    def test_unexpected_arcs_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "Unexpected print arcs"):
            target.audit_gcode(self.prefix + "G2 X20 Y20 I5 J5 E1\n")


class MeshTests(unittest.TestCase):
    def test_binary_stl_header_starting_solid_is_still_binary(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as tmp:
            assert Path(tmp).resolve().parent == TEST_ROOT
            path = Path(tmp) / "test.stl"
            path.write_bytes(b"solid binary".ljust(80, b"\0") + struct.pack("<I", 1) +
                             struct.pack("<12fH", 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 1, 0))
            vertices, faces, lo, hi = target.read_stl(path)
            self.assertEqual(len(faces), 1)
            self.assertEqual(hi, [1, 1, 1])


class NativeResultTests(unittest.TestCase):
    def test_access_violations_are_bounded_and_regular_errors_not_retried(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as tmp:
            assert Path(tmp).resolve().parent == TEST_ROOT
            root = Path(tmp)
            for codes, expected_calls in (([3221225477, 3221225477, 0], 3),
                                          ([3221225477, 3221225477, 3221225477], 3),
                                          ([-13], 1)):
                responses = [subprocess.CompletedProcess(["bambu.exe"], code, "", "") for code in codes]
                with mock.patch.object(target.subprocess, "run", side_effect=responses) as run, mock.patch.object(target.time, "sleep"):
                    result, attempts = target.run_native(["bambu.exe"], root, root / "result.3mf", root / "result.json", 30)
                self.assertEqual(run.call_count, expected_calls)
                self.assertEqual(len(attempts), expected_calls)
                self.assertEqual(result.returncode, codes[-1])

    def test_missing_native_result_fails_closed(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as tmp:
            assert Path(tmp).resolve().parent == TEST_ROOT
            with self.assertRaisesRegex(RuntimeError, "Fresh native result.json missing"):
                target.read_native_result(Path(tmp) / "result.json")

    def test_native_failure_or_missing_warning_status_cannot_pass(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as tmp:
            assert Path(tmp).resolve().parent == TEST_ROOT
            path = Path(tmp) / "result.json"
            for value in ({"return_code": -13, "sliced_plates": [{"warning_message": ""}]},
                          {"return_code": 0, "sliced_plates": [{}]}):
                path.write_text(json.dumps(value))
                with self.assertRaises(RuntimeError):
                    target.read_native_result(path)

    def test_stale_native_success_is_removed_before_next_slice(self):
        with tempfile.TemporaryDirectory(dir=TEST_ROOT) as tmp:
            assert Path(tmp).resolve().parent == TEST_ROOT
            root = Path(tmp)
            destination = root / "slice"
            destination.mkdir()
            result = destination / "result.json"
            result.write_text(json.dumps({"return_code": 0, "sliced_plates": [{"warning_message": ""}]}))
            sliced = destination / "model.gcode.3mf"
            sliced.write_bytes(b"old artifact")
            def successful_process_without_native_report(*args, **kwargs):
                self.assertFalse(result.exists())
                self.assertFalse(sliced.exists())
                sliced.write_bytes(b"new artifact, but incomplete native run")
                return subprocess.CompletedProcess(args[0], 0, "", "")
            with mock.patch.object(target.subprocess, "run", side_effect=successful_process_without_native_report):
                with self.assertRaisesRegex(RuntimeError, "Fresh native result.json missing"):
                    target.slice_project(Path("bambu.exe"), root / "model.3mf", destination, root / "profiles", 30)


if __name__ == "__main__":
    unittest.main()

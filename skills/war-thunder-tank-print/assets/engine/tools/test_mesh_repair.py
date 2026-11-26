"""Maintained acceptance tests for conservative miniature mesh repair.

Run with the project's .venv Python. Synthetic tests always run. Optional
vehicle integration checks run only when repair_probe artifacts exist.
They verify digital geometry; they do not certify physical printability.
"""
import json
from pathlib import Path
import unittest

import numpy as np
import trimesh

from mesh_repair import repair_mesh, cache_compatible, _solidify, _outward_growth


PROBES = Path(__file__).resolve().parents[1] / "outputs" / "repair_probe"
MODEL_PROBES = ("ex_armor_turret_l_06", "gun_barrel_01")
TRACK_PROBES = ("track_l_mesh", "track_r_mesh")


class MeshRepairTests(unittest.TestCase):
    def test_cap_open_cube_without_inflation(self):
        cube = trimesh.creation.box(extents=(3, 3, 3))
        cube.update_faces(np.arange(len(cube.faces)) != 0)
        fixed, audit = repair_mesh(cube)
        self.assertTrue(fixed.is_volume)
        self.assertAlmostEqual(fixed.volume, 27, places=5)
        self.assertLess(audit["maximum_bounds_change_mm"], 1e-5)

    def test_planar_sheet_gets_real_thickness(self):
        sheet = trimesh.Trimesh([[0, 0, 0], [4, 0, 0], [0, 4, 0]], [[0, 1, 2]])
        fixed, audit = repair_mesh(sheet)
        self.assertTrue(fixed.is_volume)
        self.assertGreaterEqual(fixed.extents[2], 0.7999)
        self.assertIn("solidified_open_sheet", audit["components"][0]["actions"])
        self.assertFalse(audit["minimum_thickness_certified"])

    def test_fine_rod_not_erased_or_globally_remeshed(self):
        rod = trimesh.creation.cylinder(radius=0.45, height=12, sections=24)
        fixed, audit = repair_mesh(rod)
        np.testing.assert_allclose(fixed.bounds, rod.bounds, atol=1e-5)
        self.assertTrue(fixed.is_volume)
        self.assertFalse(audit["global_remesh"])
        self.assertIn("retained_closed_rod_at_target_width", audit["components"][0]["actions"])

    def test_detached_details_are_reported_not_discarded(self):
        first = trimesh.creation.box(extents=(1, 1, 1))
        second = first.copy().apply_translation((3, 0, 0))
        fixed, audit = repair_mesh(trimesh.util.concatenate([first, second]))
        self.assertEqual(audit["result_components"], 2)
        self.assertTrue(audit["requires_attachment_review"])
        self.assertAlmostEqual(fixed.volume, 2)

    def test_empty_input_fails_explicitly(self):
        with self.assertRaises(ValueError):
            repair_mesh(trimesh.Trimesh())

    def test_acute_fold_uses_bounded_fallback_instead_of_miter_spike(self):
        folded = trimesh.Trimesh(
            [[-10,0,0],[10,0,0],[-10,5,0],[10,5,0],[-10,5,.05],[10,5,.05]],
            [[0,1,3],[0,3,2],[1,0,4],[1,4,5]], process=True)
        # This real acute fold reproduces the original non-manifold miter bug:
        # 0.8 mm requested thickness used to extend the surface by about 80 mm.
        legacy = _solidify(folded, .8)
        self.assertGreater(_outward_growth(folded.bounds, legacy.bounds), 10)
        fixed, audit = repair_mesh(folded, label="acute_fold_test", sheet_first=True)
        self.assertTrue(fixed.is_volume)
        self.assertLessEqual(_outward_growth(folded.bounds, fixed.bounds), .401)
        self.assertIn("bounded_fixed_thickness_fallback", audit["components"][0]["actions"])
        self.assertGreater(audit["components"][0]["rejected_unbounded_result"]["outward_growth_mm"],10)

    def test_cache_compatibility_rejects_spikes_and_missing_evidence(self):
        good = {"target_mm":.8,"components":[{
            "source_bounds_mm":[[0,0,0],[2,3,4]],
            "result_bounds_mm":[[-.4,-.4,-.4],[2.4,3.4,4.4]]}]}
        self.assertTrue(cache_compatible(good, .8))
        self.assertFalse(cache_compatible(good, .6))
        self.assertFalse(cache_compatible({"target_mm":.8,"components":[]}, .8))
        bad = json.loads(json.dumps(good))
        bad["components"][0]["result_bounds_mm"][0][0] = -48
        self.assertFalse(cache_compatible(bad, .8))
        bad["components"][0]["result_bounds_mm"][0][0] = float("nan")
        self.assertFalse(cache_compatible(bad, .8))

    @unittest.skipUnless(
        all((PROBES/f"bone_turret_component_{i}_repaired.npz").exists()
            and (PROBES/f"bone_turret_component_{i}_audit.json").exists() for i in (644,646)),
        "Optional guarded turret component probes have not been generated",
    )
    def test_real_turret_has_no_solidify_miter_spikes(self):
        for index in (644,646):
            with self.subTest(component=index):
                data = np.load(PROBES/f"bone_turret_component_{index}_repaired.npz")
                mesh = trimesh.Trimesh(data["vertices"],data["faces"],process=False)
                audit = json.loads((PROBES/f"bone_turret_component_{index}_audit.json").read_text())
                self.assertTrue(mesh.is_volume)
                self.assertTrue(cache_compatible(audit,.8))
                self.assertIn("bounded_fixed_thickness_fallback",audit["components"][0]["actions"])
                self.assertLessEqual(audit["components"][0]["outward_growth_mm"],.401)
                # Float64 intermediate validity is separate from STL readiness.
                # Any quantization failure must stay explicit until final assembly.
                if audit["stl_quantization_deferred"]:
                    self.assertIn("strict_quantization_error",audit)
                else:
                    exported = trimesh.load_mesh(PROBES/f"bone_turret_component_{index}_repaired.stl")
                    self.assertTrue(exported.is_volume)

    @unittest.skipUnless(
        all((PROBES / f"{name}_repaired.stl").exists() for name in MODEL_PROBES),
        "Optional BMPT repair probes have not been generated",
    )
    def test_real_exported_probes_are_closed_after_stl_load(self):
        for name in MODEL_PROBES:
            with self.subTest(part=name):
                mesh = trimesh.load_mesh(PROBES / f"{name}_repaired.stl")
                self.assertTrue(mesh.is_volume)

    @unittest.skipUnless(
        all((PROBES / f"{name}_repaired.stl").exists()
            and (PROBES / f"{name}_audit.json").exists() for name in TRACK_PROBES),
        "Optional left/right track repair probes have not been generated",
    )
    def test_real_tracks_retain_center_opening_and_outline(self):
        for name in TRACK_PROBES:
            with self.subTest(track=name):
                mesh = trimesh.load_mesh(PROBES / f"{name}_repaired.stl")
                audit = json.loads((PROBES / f"{name}_audit.json").read_text())
                self.assertTrue(mesh.is_volume)
                self.assertEqual(len(mesh.split(only_watertight=False)), 1)
                original = np.array(audit["original_bounds_mm"])
                self.assertLess(np.max(np.abs(mesh.bounds - original)), 0.43)
                center = original.mean(axis=0)
                points = np.array([center + [-20, 0, 0], center, center + [20, 0, 0]])
                self.assertFalse(mesh.contains(points).any())
                self.assertTrue(audit["sheet_first_preserve_openings"])
                self.assertLess(len(mesh.faces), 200000)


if __name__ == "__main__":
    unittest.main()

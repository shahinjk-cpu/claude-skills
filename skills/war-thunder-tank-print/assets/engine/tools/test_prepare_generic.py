"""Geometry checks for the generic (schema 2) builder without game assets.

Run: .venv/Scripts/python.exe -m unittest discover -s tools -p test_prepare_generic.py -v
"""
from __future__ import annotations

import unittest

import numpy as np
import manifold3d as md
import trimesh

from prepare_generic import (ORIENTATIONS, build_turret_joint, check_rotation, relieve_sweep,
                             running_gear_backplate, sweep_profile, validate_recipe)
from prepare_vehicle import box, from_manifold, manifold


def cylinder(axis, radius, z0, z1):
    return md.Manifold.cylinder(z1-z0, radius, radius, 128).translate([axis[0], axis[1], z0])


def turret_cfg(axis):
    return {"mode": "rotating", "part": "turret", "axis_xy_mm": list(axis), "trim_z_mm": 20.0,
            "bearing_radius_mm": 14.0, "cap_radius_mm": 15.0, "vertical_clearance_mm": .3,
            "cap_depth_mm": 4.2, "disk_thickness_mm": .8, "hub_radius_mm": 4.0, "hub_top_z_mm": 25.0,
            "bearing_pad_radius_mm": 5.0, "pin_diameter_mm": 5.0, "pin_engagement_mm": 3.0,
            "bore_depth_mm": 3.4, "radial_clearance_mm": .2, "pin_tip_chamfer_mm": .25,
            "ring_eccentric_margin_mm": .15, "protected_core_radius_mm": 5.1, "sweep_band_mm": .25,
            "sweep_excluded_parts": []}


class GenericTurretTests(unittest.TestCase):
    def fixture(self):
        axis = (3.0, -1.0)
        # Hull: roof slab with a ring hole plus a raised collar around the turret.
        slab = manifold(box([-40, -25, 14], [40, 25, 19.5]))-cylinder(axis, 12, 13, 20)
        collar = cylinder(axis, 22, 19.5, 23)-cylinder(axis, 17.4, 19, 24)
        hull = from_manifold(slab+collar)
        # Turret: shell whose lower skirt (r 18) overlaps the collar interior (17.4).
        body = cylinder(axis, 18, 20.5, 30)+cylinder(axis, 16, 10, 20.5)
        turret = from_manifold(body)
        return axis, {"hull": hull, "turret": turret}

    def test_profile_matches_known_cylinder_radius(self):
        mesh = from_manifold(cylinder((1.0, 2.0), 7.5, 0, 4))
        zs, rmax = sweep_profile(mesh, (1.0, 2.0), 0, 4, .5)
        self.assertEqual(len(rmax), len(zs)-1)
        self.assertTrue(np.all(rmax <= 7.5+1e-6))
        self.assertTrue(np.all(rmax >= 7.5*np.cos(np.pi/128)-1e-6))

    def test_joint_and_sweep_give_clear_rotation_with_eccentric_play(self):
        axis, parts = self.fixture()
        cfg = turret_cfg(axis)
        audit = {"joints": {}, "reinforcements": []}
        build_turret_joint(parts, cfg, audit)
        self.assertGreater(audit["joints"]["turret"]["clipped_turret_volume_mm3"], 0)
        self.assertGreaterEqual(parts["turret"].bounds[0, 2], 20.0-1e-6)
        relieve_sweep(parts, cfg, ["hull"], ["turret"], audit)
        self.assertGreater(audit["sweep_relief"]["removed_mm3"]["hull"], 0)
        recipe = {"turret": cfg, "parts": [{"name": "hull"}, {"name": "turret"}]}
        check_rotation(parts, audit, recipe)
        self.assertFalse(audit["rotation_check"]["rotation_limited"])
        self.assertLess(audit["rotation_check"]["maximum_intersection_mm3"], .01)
        # Pin and bearing pad survive inside the protected core.
        hull = manifold(parts["hull"])
        pin = cylinder(axis, 2.4, 20.1, 22.5)
        self.assertAlmostEqual(float((hull ^ pin).volume()), float(pin.volume()), places=3)
        # Outer collar wall beyond the turret reach is untouched.
        outer = cylinder(axis, 22, 20, 22.9)-cylinder(axis, 19.0, 19.9, 23)
        self.assertAlmostEqual(float((hull ^ outer).volume()), float(outer.volume()), places=3)
        for name in ("hull", "turret"):
            self.assertTrue(parts[name].is_volume)

    def test_breech_over_pin_keeps_bore_free_after_merge(self):
        from prepare_generic import finish_parts
        axis, parts = self.fixture()
        cfg = dict(turret_cfg(axis), sweep_excluded_parts=["gun_group"])
        # Breech block straddling the turret axis just above the ring plane, barrel forward.
        breech = manifold(box([axis[0]-6, axis[1]-3, 20.2], [axis[0]+12, axis[1]+3, 26]))
        barrel = manifold(box([axis[0]+11, axis[1]-1, 24], [axis[0]+30, axis[1]+1, 26]))
        parts["gun_group"] = from_manifold(breech+barrel)
        audit = {"joints": {}, "reinforcements": [], "attachments": []}
        build_turret_joint(parts, cfg, audit)
        recipe = {"turret": cfg, "parts": [{"name": "hull"}, {"name": "turret"},
                                           {"name": "gun_group", "merge_into": "turret"}],
                  "assembly_reliefs": [["turret", "gun_group"], ["hull", "gun_group"]]}
        finish_parts(parts, recipe, audit)
        self.assertNotIn("gun_group", parts)
        self.assertLess(audit["rotation_check"]["maximum_intersection_mm3"], .01)
        bore = np.array([[axis[0]+2.6, axis[1], 21.0], [axis[0], axis[1], 22.5]])
        self.assertFalse(parts["turret"].contains(bore).any())

    def test_excessive_sweep_removal_requires_review(self):
        axis, parts = self.fixture()
        cfg = turret_cfg(axis)
        parts["turret"] = from_manifold(cylinder(axis, 60, 20, 40))
        parts["hull"] = from_manifold(manifold(box([-30, -30, 0], [30, 30, 38])))
        with self.assertRaisesRegex(ValueError, "recipe review"):
            relieve_sweep(parts, cfg, ["hull"], ["turret"], {"joints": {}})


class GunElevationTests(unittest.TestCase):
    def test_depressed_barrel_is_raised_until_traverse_is_clear(self):
        from prepare_generic import elevate_gun
        axis = (0.0, 0.0)
        cfg = turret_cfg(axis)
        hull = from_manifold(manifold(box([-60, -20, 0], [60, 20, 20]))+manifold(box([30, -20, 20], [60, 20, 23])))
        turret = from_manifold(cylinder(axis, 15, 20.3, 30))
        # Barrel from trunnion (12, 0, 25) sloping down to z 22 at x 55: dips into the glacis block.
        barrel = trimesh.creation.cylinder(1.0, segment=[[12, 0, 25], [55, 0, 22]], sections=32)
        parts = {"hull": hull, "turret": turret, "gun_group": barrel}
        recipe = {"turret": cfg, "gun": {"part": "gun_group", "pivot_mm": [12, 0, 25], "auto_elevate": True,
                                         "max_elevation_deg": 12}}
        audit = {}
        elevate_gun(parts, recipe, audit)
        chosen = audit["gun_elevation"]["chosen_deg"]
        self.assertGreater(chosen, 0)
        self.assertLessEqual(chosen, 12)
        self.assertGreater(audit["gun_elevation"]["trials"][0]["assembled_mm3"], .01)
        self.assertLessEqual(audit["gun_elevation"]["trials"][-1]["max_traverse_mm3"], .01)
        # Muzzle end now above the glacis top (z 23) with the 1-mm barrel radius.
        muzzle = parts["gun_group"].vertices[parts["gun_group"].vertices[:, 0] > 54]
        self.assertGreater(muzzle[:, 2].min(), 23.0)
        self.assertGreaterEqual(parts["gun_group"].bounds[0, 2], cfg["trim_z_mm"]-1e-6)


class GenericRunningGearTests(unittest.TestCase):
    def test_backplate_sits_inside_measured_outline(self):
        from shapely.geometry import Point, Polygon
        outline = Polygon([(-40, 5), (-34, 0), (38, 0), (45, 6), (45, 10), (40, 16), (-34, 16), (-40, 11)])
        track = trimesh.creation.extrude_polygon(outline, 4.0, engine="earcut")
        track.apply_transform(np.array([[1, 0, 0, 0], [0, 0, 1, 14], [0, 1, 0, 0], [0, 0, 0, 1]], dtype=float))
        cfg = {"thickness_mm": 2.0, "inset_mm": .6, "inner_offset_mm": .35, "x_margin_fraction": .035,
               "z_low_fraction": .175, "z_high_fraction": .16}
        plate, info = running_gear_backplate(track, 1, cfg)
        self.assertTrue(plate.is_volume)
        np.testing.assert_allclose(plate.bounds[:, 1], [13.65, 15.65], atol=1e-6)
        for x, z in plate.vertices[:, [0, 2]]:
            self.assertGreaterEqual(Point(float(x), float(z)).distance(outline.boundary), .6-1e-6)
        mirrored = track.copy()
        mirrored.apply_scale([1, -1, 1])
        right, _ = running_gear_backplate(mirrored, -1, cfg)
        np.testing.assert_allclose(right.bounds[:, 1], [-15.65, -13.65], atol=1e-6)
        self.assertAlmostEqual(plate.volume, right.volume, places=5)


class AttachmentTests(unittest.TestCase):
    def cfg(self, **overrides):
        from prepare_generic import ATTACHMENT_DEFAULTS
        return {**ATTACHMENT_DEFAULTS, **overrides}

    def test_flat_zero_volume_sliver_is_dropped_by_volume_not_size(self):
        from prepare_generic import connect_parts
        body = box([0, 0, 0], [10, 10, 5])
        # Four coplanar faces spanning 3 mm: no volume, Manifold would reject it.
        sliver = trimesh.Trimesh(vertices=[[12, 0, 0], [15, 0, 0], [15, 3, 0], [12, 3, 0]],
                                 faces=[[0, 1, 2], [0, 2, 3], [0, 2, 1], [0, 3, 2]], process=False)
        joined, audit = connect_parts(trimesh.util.concatenate([body, sliver]), "hull", self.cfg())
        self.assertTrue(joined.is_volume)
        self.assertEqual(len(joined.split(only_watertight=False)), 1)
        self.assertEqual(audit["bridges"], [])
        self.assertTrue(audit["removed_slivers"])
        self.assertTrue(all(r["reason"].startswith("zero") for r in audit["removed_slivers"]))
        widest = max(float(max(np.subtract(*np.asarray(r["bounds_mm"])[::-1]))) for r in audit["removed_slivers"])
        self.assertGreaterEqual(widest, 3.0-1e-9)  # larger than the old 0.3/0.8-mm extent limits

    def test_bridge_diameter_comes_from_recipe_and_long_thin_bridges_are_flagged(self):
        from prepare_generic import attachment_review_flags, connect_parts
        mesh = trimesh.util.concatenate([box([0, 0, 0], [10, 10, 5]), box([12.09, 8, 3], [14, 10, 5])])
        joined, audit = connect_parts(mesh, "turret", self.cfg())
        self.assertEqual(len(joined.split(only_watertight=False)), 1)
        self.assertEqual([b["diameter_mm"] for b in audit["bridges"]], [.8])
        self.assertAlmostEqual(audit["bridges"][0]["gap_mm"], 2.09, places=6)
        flags = attachment_review_flags(audit, self.cfg())
        self.assertTrue(any("gaps > 1.0 mm (max 2.09 mm)" in f for f in flags), flags)
        self.assertTrue(any("thinner than 1.0 mm" in f for f in flags), flags)
        _, thick = connect_parts(mesh, "turret", self.cfg(bridge_diameter_mm=1.2))
        self.assertEqual([b["diameter_mm"] for b in thick["bridges"]], [1.2])
        self.assertFalse(any("thinner" in f for f in attachment_review_flags(thick, self.cfg(bridge_diameter_mm=1.2))))

    def test_gap_beyond_limit_names_the_recipe_key(self):
        from prepare_generic import connect_parts
        mesh = trimesh.util.concatenate([box([0, 0, 0], [10, 10, 5]), box([20, 0, 0], [22, 2, 2])])
        with self.assertRaisesRegex(ValueError, "max_bridge_gap_mm"):
            connect_parts(mesh, "hull", self.cfg())

    def test_many_shells_and_retries_raise_review_flags(self):
        from prepare_generic import attachment_review_flags
        entry = {"part": "hull", "original_shells": 120, "retries_used": 1,
                 "bridges": [{"gap_mm": .3, "diameter_mm": .8}, {"gap_mm": .4, "diameter_mm": 1.0}]}
        flags = attachment_review_flags(entry, self.cfg())
        self.assertTrue(any("120 separate shells" in f for f in flags), flags)
        self.assertFalse(any("thinner" in f for f in flags), flags)  # short joints are not fragile struts
        self.assertTrue(any("retry needed (1x); mixed bridge diameters 0.80, 1.00 mm" in f for f in flags), flags)


class RecipeValidationTests(unittest.TestCase):
    def recipe(self):
        return {"schema": 2, "profile": "a1mini_02_pla", "validated_scales": [72],
                "parts": [{"name": "hull"}, {"name": "turret", "orientation": "as_is"}],
                "objects": {"@root": "hull", "bone_turret": "turret"}, "turret": {"mode": "none"}}

    def test_valid_recipe_and_rejections(self):
        validate_recipe(self.recipe(), 72)
        with self.assertRaisesRegex(ValueError, "measured"):
            validate_recipe(self.recipe(), 48)
        bad = self.recipe()
        bad["objects"]["gun"] = "gun_group"
        with self.assertRaisesRegex(ValueError, "undeclared"):
            validate_recipe(bad, 72)
        bad = self.recipe()
        bad["parts"][1]["orientation"] = "sideways"
        with self.assertRaisesRegex(ValueError, "orientation"):
            validate_recipe(bad, 72)

    def test_loose_gun_without_turret_needs_a_merge_target(self):
        recipe = self.recipe()
        recipe["parts"].append({"name": "gun_group", "orientation": "muzzle_up"})
        recipe["objects"]["bone_gun"] = "gun_group"
        with self.assertRaisesRegex(ValueError, "merge_into"):
            validate_recipe(recipe, 72)
        recipe["parts"][-1]["merge_into"] = "hull"
        validate_recipe(recipe, 72)

    def test_orientations_are_proper_rotations(self):
        for name, matrix in ORIENTATIONS.items():
            with self.subTest(name=name):
                self.assertAlmostEqual(float(np.linalg.det(matrix[:3, :3])), 1.0, places=9)


if __name__ == "__main__":
    unittest.main(verbosity=2)

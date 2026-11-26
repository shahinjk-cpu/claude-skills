"""Functional topology checks for the printable-part construction helpers.

Run: .venv/Scripts/python.exe -m unittest discover -s tools -p test_prepare_vehicle.py -v
No game extraction or full model rebuild is performed.
"""
from __future__ import annotations

import unittest

import numpy as np
import trimesh
import manifold3d as md

from prepare_vehicle import (box, clip_above, connect_shells, manifold,
                             running_gear_backplate, relieve_turret_ring, from_manifold)


class PrintableTopologyTests(unittest.TestCase):
    @staticmethod
    def rounded_track_fixture():
        from shapely.geometry import Polygon
        # Chamfered lower nose makes the old rectangle corner X43/Z2.7 visibly
        # protrude. The original track outline is the independently known fixture.
        outline = Polygon([(-40, 5), (-34, 0), (38, 0), (45, 6),
                           (45, 10), (40, 16), (-34, 16), (-40, 11)])
        track = trimesh.creation.extrude_polygon(outline, 4.0, engine="earcut")
        track.apply_transform(np.array([[1, 0, 0, 0], [0, 0, 1, 14],
                                        [0, 1, 0, 0], [0, 0, 0, 1]], dtype=float))
        return track, outline

    def test_horizontal_trim_preserves_known_volume_and_closes_cut(self):
        # A 4 x 4 x 8 mm solid crossing the trim plane leaves 4 x 4 x 4 mm.
        source = box([-1.0, -2.0, -3.0], [3.0, 2.0, 5.0])
        original_vertices = source.vertices.copy()
        result = clip_above(source, 1.0)

        self.assertTrue(result.is_volume)
        self.assertTrue(result.is_watertight)
        self.assertEqual(len(result.split(only_watertight=False)), 1)
        np.testing.assert_allclose(result.bounds, [[-1, -2, 1], [3, 2, 5]], atol=1e-6)
        self.assertAlmostEqual(result.volume, 64.0, places=5)
        # A real cut cap has 16 mm² area, so an open trimmed surface cannot pass.
        cap_faces = np.all(np.isclose(result.triangles[:, :, 2], 1.0, atol=1e-6), axis=1)
        self.assertAlmostEqual(float(result.area_faces[cap_faces].sum()), 16.0, places=5)
        np.testing.assert_array_equal(source.vertices, original_vertices)

    def test_local_bridge_connects_bodies_without_removing_either(self):
        first = box([-2.0, -1.0, 0.0], [0.0, 1.0, 2.0])
        second = box([1.0, -1.0, 0.0], [3.0, 1.0, 2.0])
        source = trimesh.util.concatenate([first, second])
        self.assertEqual(len(source.split(only_watertight=False)), 2)

        result, audit = connect_shells(source, "local_detail", radius=0.4, max_gap=5.0)

        self.assertTrue(result.is_volume)
        self.assertTrue(result.is_watertight)
        self.assertEqual(len(result.split(only_watertight=False)), 1)
        self.assertGreater(result.volume, first.volume + second.volume)
        # Both original 8 mm³ solids must survive completely inside the union.
        solid = manifold(result)
        for original in (first, second):
            retained_volume = float((solid ^ manifold(original)).volume())
            self.assertAlmostEqual(retained_volume, original.volume, places=4)
        self.assertEqual(audit["original_shells"], 2)
        self.assertEqual(audit["final_shells"], 1)
        self.assertEqual(len(audit["bridges"]), 1)
        self.assertAlmostEqual(audit["bridges"][0]["diameter_mm"], 0.8, places=6)
        self.assertAlmostEqual(audit["bridges"][0]["gap_mm"], 1.0, places=6)
        self.assertEqual(audit["removed_unprintable_specks"], [])

    def test_distant_body_requires_review_instead_of_long_automatic_bridge(self):
        first = box([0.0, 0.0, 0.0], [2.0, 2.0, 2.0])
        second = box([8.0, 0.0, 0.0], [10.0, 2.0, 2.0])
        source = trimesh.util.concatenate([first, second])
        original_vertices = source.vertices.copy()
        with self.assertRaisesRegex(ValueError, "disconnected structural shell"):
            connect_shells(source, "detached_structure", radius=0.4, max_gap=5.0)
        # Rejected repair must leave the supplied source geometry intact.
        np.testing.assert_array_equal(source.vertices, original_vertices)
        self.assertEqual(len(source.split(only_watertight=False)), 2)

    def test_backplate_stays_inside_rounded_track_nose_with_margin(self):
        from shapely.geometry import Point
        track, outline = self.rounded_track_fixture()
        plate = running_gear_backplate(track, sign=1)

        self.assertTrue(plate.is_volume)
        self.assertTrue(plate.is_watertight)
        self.assertEqual(len(plate.split(only_watertight=False)), 1)
        np.testing.assert_allclose(plate.bounds[:, 1], [14.45, 16.45], atol=1e-7)
        self.assertGreater(plate.volume, 1000.0)
        for x, z in plate.vertices[:, [0, 2]]:
            point = Point(float(x), float(z))
            self.assertTrue(outline.covers(point), (x, z))
            self.assertGreaterEqual(point.distance(outline.boundary), 0.6 - 1e-6)
        # A useful central glue face survives, while the old rectangular tab
        # below the rounded nose is absent from the actual 3D volume.
        occupied = plate.contains(np.array([[0.0, 15.45, 8.0], [42.8, 15.45, 2.9]]))
        np.testing.assert_array_equal(occupied, [True, False])
        self.assertGreaterEqual(plate.bounds[0, 0], -38.0 - 1e-7)
        self.assertLessEqual(plate.bounds[1, 0], 43.0 + 1e-7)
        self.assertGreaterEqual(plate.bounds[0, 2], 2.7 - 1e-7)
        self.assertLessEqual(plate.bounds[1, 2], 13.0 + 1e-7)

    def test_backplates_are_mirrored_positive_volumes_without_changing_tracks(self):
        left_track, _ = self.rounded_track_fixture()
        original_vertices = left_track.vertices.copy()
        right_track = left_track.copy()
        right_track.apply_scale([1.0, -1.0, 1.0])
        left = running_gear_backplate(left_track, sign=1)
        right = running_gear_backplate(right_track, sign=-1)

        for plate in (left, right):
            self.assertTrue(plate.is_volume)
            self.assertTrue(plate.is_watertight)
            self.assertEqual(len(plate.split(only_watertight=False)), 1)
        self.assertAlmostEqual(left.volume, right.volume, places=5)
        np.testing.assert_allclose(right.bounds[:, 1], [-16.45, -14.45], atol=1e-7)
        mirrored_left = left.vertices * [1, -1, 1]
        sort_left = np.lexsort(mirrored_left.T[::-1])
        sort_right = np.lexsort(right.vertices.T[::-1])
        np.testing.assert_allclose(mirrored_left[sort_left], right.vertices[sort_right], atol=1e-7)
        np.testing.assert_array_equal(left_track.vertices, original_vertices)


class TurretRingReliefTests(unittest.TestCase):
    @staticmethod
    def fixture():
        axis=np.array([-1.389132295217779,.00009877891216092394])
        def cylinder(radius,z0,z1):
            return md.Manifold.cylinder(z1-z0,radius,radius,128).translate([*axis,z0])
        base=cylinder(20,18,19.7)
        collar=cylinder(20,19.7,26)-cylinder(17.3,19.6,26.1)
        bearing=cylinder(5,19.6,20)
        pin=cylinder(2.5,19.5,23)
        hull=base+collar+bearing+pin
        turret=cylinder(18.2,20,27.3)-cylinder(2.7,19.9,23.4)
        feature=manifold(box([axis[0]+17,axis[1]-2,26.5],[axis[0]+20,axis[1]+2,29]))
        turret=turret+feature
        parts={"hull":from_manifold(hull),"turret":from_manifold(turret)}
        audit={"joints":{"turret":{"axis_xy_mm":axis.tolist()}}}
        settings={"radius_profile_z_r_mm":[[20,16.6],[20.5,16.6],[21,17.5],[26.3,17.5]],
                  "radial_clearance_mm":.2,"protected_bearing_radius_mm":5.1}
        return parts,audit,settings,axis,{"bearing":bearing,"pin":pin,"feature":feature,
            "outer_collar":cylinder(20,21,25.9)-cylinder(19.2,20.9,26)}

    def test_relief_preserves_pin_bearing_outer_collar_and_upper_detail(self):
        parts,audit,settings,axis,protected=self.fixture()
        relieve_turret_ring(parts,audit,settings)
        hull,turret=manifold(parts["hull"]),manifold(parts["turret"])
        for name in ("pin","bearing","outer_collar"):
            with self.subTest(protected=name):
                self.assertAlmostEqual(float((hull^protected[name]).volume()),
                                       float(protected[name].volume()),places=5)
        self.assertAlmostEqual(float((turret^protected["feature"]).volume()),
                               float(protected["feature"].volume()),places=5)
        for name in ("hull","turret"):
            self.assertTrue(parts[name].is_volume)
            # The allowed upper box and revolved volume must overlap rather
            # than merely touch numerically at Z26.3.
            self.assertEqual(len(parts[name].split(only_watertight=False)),1)
        self.assertEqual(audit["turret_ring_relief"]["upper_boolean_overlap_mm"],.05)
        self.assertGreater(audit["turret_ring_relief"]["removed_hull_volume_mm3"],0)
        self.assertGreater(audit["turret_ring_relief"]["removed_turret_volume_mm3"],0)

    def test_ring_gap_and_rotation_remain_clear_at_non_cardinal_angles(self):
        parts,audit,settings,axis,_=self.fixture()
        relieve_turret_ring(parts,audit,settings)
        hull,turret=manifold(parts["hull"]),manifold(parts["turret"])
        # Check points between the polygon vertices as well as rotated poses.
        angles=np.deg2rad(np.arange(0,360,15)+.703125)
        points=np.column_stack([axis[0]+17.6*np.cos(angles),
                                axis[1]+17.6*np.sin(angles),np.full(len(angles),24)])
        self.assertFalse(parts["hull"].contains(points).any())
        self.assertFalse(parts["turret"].contains(points).any())
        for angle in (0,7.5,15,37.5,90,135,180,225,270,315,352.5):
            moved=turret.translate([-axis[0],-axis[1],0]).rotate([0,0,angle]).translate([*axis,0])
            self.assertLess(abs(float((hull^moved).volume())),1e-6)


if __name__ == "__main__":
    unittest.main(verbosity=2)

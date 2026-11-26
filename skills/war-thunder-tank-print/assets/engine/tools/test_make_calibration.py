"""Geometric acceptance checks for calibration dimensions and actual fit."""

import unittest

import FreeCAD as App
import Part

from make_calibration import (
    PIN_DIAMETER_MM, ENGAGEMENT_MM, BORE_DEPTH_MM, CLEARANCES_MM,
    make_pin, make_socket, make_detail_sample, inspect_shape,
)


class CalibrationGeometryTests(unittest.TestCase):
    def test_pin_real_dimensions_and_single_solid(self):
        pin = make_pin()
        _, checks = inspect_shape(pin)
        self.assertEqual(checks["size_mm"], [8.0, 8.0, 5.0])
        self.assertAlmostEqual(checks["z_min_mm"], 0.0)
        self.assertTrue(pin.isInside(App.Vector(2.49, 0, 3.0), 1e-6, False))
        self.assertFalse(pin.isInside(App.Vector(2.51, 0, 3.0), 1e-6, False))

    def test_socket_clearances_and_rotational_fit(self):
        pin = make_pin()
        # Flange rests at top z=5; stem points downward to z=2.
        pin.rotate(App.Vector(0, 0, 0), App.Vector(1, 0, 0), 180)
        pin.translate(App.Vector(9.0, 9.0, 7.0))
        for clearance in CLEARANCES_MM:
            with self.subTest(clearance=clearance):
                socket = make_socket(clearance)
                inspect_shape(socket)
                radius = PIN_DIAMETER_MM / 2 + clearance
                self.assertFalse(socket.isInside(App.Vector(9 + radius - .01, 9, 3), 1e-6, False))
                self.assertTrue(socket.isInside(App.Vector(9 + radius + .01, 9, 3), 1e-6, False))
                self.assertAlmostEqual(socket.common(pin).Volume, 0.0, places=7)
                # Working cylinder extends into bore with explicit radial gap.
                cylinder = Part.makeCylinder(2.5, ENGAGEMENT_MM, App.Vector(9, 9, 2))
                self.assertAlmostEqual(socket.distToShape(cylinder)[0], clearance, places=6)
                # Socket bottom remains thick and bore is 0.4 mm deeper than stem.
                self.assertTrue(socket.isInside(App.Vector(9, 9, 1.59), 1e-6, False))
                self.assertFalse(socket.isInside(App.Vector(9, 9, 1.61), 1e-6, False))

    def test_detail_sample_geometry(self):
        shape = make_detail_sample()
        _, checks = inspect_shape(shape)
        self.assertEqual(checks["size_mm"], [50.0, 32.0, 9.6])
        # Check the target 0.8 mm rod and grille opening remain distinct.
        self.assertTrue(shape.isInside(App.Vector(11.39, 9, 4), 1e-6, False))
        self.assertFalse(shape.isInside(App.Vector(11.41, 9, 4), 1e-6, False))
        self.assertFalse(shape.isInside(App.Vector(30.0, 8.4, 5.0), 1e-6, False))
        self.assertTrue(shape.isInside(App.Vector(28.4, 8.4, 5.0), 1e-6, False))


if __name__ == "__main__":
    unittest.main()

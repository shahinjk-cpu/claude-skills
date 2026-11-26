"""Placement logic of the generic single-plate combiner; no slicer needed."""
import unittest

from combine_plate import TARGET, _dims, pack, rotated, turn


def row(w, h, margin=4.0):
    return {"model_size": [w, h], "envelope_local": [-margin, -margin, w+margin, h+margin]}


class CombinePlateTests(unittest.TestCase):
    def test_quarter_turn_maps_envelope_like_mesh(self):
        r = {"model_size": [30.0, 10.0], "envelope_local": [-2.0, -1.0, 33.0, 12.0]}
        self.assertEqual(rotated(r, 0), [-2.0, -1.0, 33.0, 12.0])
        # Rotate the model corners exactly as turn() rotates mesh vertices.
        corners = [(-2.0, -1.0, 0), (33.0, 12.0, 0)]
        model = [(0.0, 0.0, 0), (30.0, 10.0, 0)]
        turned, turned_model = turn(corners, 1), turn(model, 1)
        lo = [min(v[i] for v in turned_model) for i in range(2)]
        expected = [min(v[0] for v in turned)-lo[0], min(v[1] for v in turned)-lo[1],
                    max(v[0] for v in turned)-lo[0], max(v[1] for v in turned)-lo[1]]
        self.assertEqual(rotated(r, 1), expected)
        self.assertEqual(_dims(r, 1), (13.0, 35.0))

    def test_pack_keeps_gap_and_bounds(self):
        rows = {"hull": row(110, 50), "turret": row(140, 45), "left": row(105, 16), "right": row(105, 16)}
        placed, footprint = pack(rows, 3.0)
        self.assertIsNotNone(placed)
        self.assertLessEqual(max(footprint), TARGET)
        for i, a in enumerate(placed):
            self.assertLessEqual(a[2]+a[4], TARGET+1e-9)
            for b in placed[i+1:]:
                separated = (a[2]+a[4]+3 <= b[2]+1e-9 or b[2]+b[4]+3 <= a[2]+1e-9 or
                             a[3]+a[5]+3 <= b[3]+1e-9 or b[3]+b[5]+3 <= a[3]+1e-9)
                self.assertTrue(separated, (a, b))

    def test_quarter_turn_used_when_needed(self):
        rows = {"long": row(160, 20, 2), "tall": row(20, 120, 2)}
        placed, _ = pack(rows, 3.0)
        self.assertIsNotNone(placed)

    def test_oversized_set_is_reported_not_squeezed(self):
        rows = {n: row(120, 60) for n in ("a", "b", "c")}
        self.assertEqual(pack(rows, 3.0), (None, None))


if __name__ == "__main__":
    unittest.main(verbosity=2)

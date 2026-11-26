"""Quantization topology regressions; no external assets required."""
import io
import unittest
import numpy as np
import trimesh
from stl_precision import prepare_stl_mesh


def sliver_box():
    """Closed box with an edge subdivision below a float32 ULP."""
    mesh = trimesh.creation.box(extents=[1,2,3])
    mesh.apply_translation([100,100,100])
    a,b = map(int,mesh.edges_unique[0])
    vertices = np.vstack([mesh.vertices,mesh.vertices[a]*(1-1e-9)+mesh.vertices[b]*1e-9])
    added,faces = len(vertices)-1,[]
    for face in mesh.faces:
        if a in face and b in face:
            for i in range(3):
                u,v,w = map(int,[face[i],face[(i+1)%3],face[(i+2)%3]])
                if {u,v} == {a,b}:
                    faces.extend([[u,added,w],[added,v,w]])
                    break
        else:
            faces.append(face)
    return trimesh.Trimesh(vertices,faces,process=False)


class STLPrecisionTests(unittest.TestCase):
    def test_binary_collapse_repaired_without_face_changes(self):
        source = sliver_box()
        self.assertTrue(source.is_volume)
        naive = trimesh.load_mesh(io.BytesIO(trimesh.exchange.stl.export_stl(source)),file_type="stl")
        self.assertFalse(naive.is_volume)
        result,audit = prepare_stl_mesh(source)
        loaded = trimesh.load_mesh(io.BytesIO(trimesh.exchange.stl.export_stl(result)),file_type="stl")
        self.assertTrue(loaded.is_volume)
        self.assertEqual(len(loaded.split()),1)
        self.assertEqual(len(source.faces),len(loaded.faces))
        np.testing.assert_array_equal(result.faces,source.faces)
        self.assertGreater(audit["local_separation_vertices"],0)
        self.assertLessEqual(audit["bidirectional_surface_distance_bound_mm"],.001)
        self.assertLess(abs(audit["volume_delta_mm3"]),.001)

    def test_exact_float_box_unchanged(self):
        source = trimesh.creation.box(extents=[1,2,3])
        result,audit = prepare_stl_mesh(source)
        np.testing.assert_array_equal(result.vertices,source.vertices)
        np.testing.assert_array_equal(result.faces,source.faces)
        self.assertEqual(audit["local_separation_vertices"],0)

    def test_deterministic_and_retains_print_floor(self):
        source = sliver_box()
        source.apply_translation(-source.bounds[0])
        first,_ = prepare_stl_mesh(source)
        second,_ = prepare_stl_mesh(source)
        np.testing.assert_array_equal(first.vertices,second.vertices)
        self.assertGreaterEqual(first.bounds[0,2],0)
        self.assertEqual(trimesh.exchange.stl.export_stl(first),trimesh.exchange.stl.export_stl(second))

    def test_open_and_disconnected_inputs_rejected(self):
        opened = trimesh.creation.box()
        opened.update_faces(np.arange(len(opened.faces)-1))
        with self.assertRaisesRegex(ValueError,"one closed"):
            prepare_stl_mesh(opened)
        box = trimesh.creation.box()
        other = box.copy()
        other.apply_translation([4,0,0])
        with self.assertRaisesRegex(ValueError,"one closed"):
            prepare_stl_mesh(trimesh.util.concatenate([box,other]))

    def test_absolute_displacement_bound_enforced(self):
        source = trimesh.creation.box(extents=[1.0001,2.0001,3.0001])
        source.apply_translation([10000,10000,10000])
        with self.assertRaisesRegex(ValueError,"rounding alone"):
            prepare_stl_mesh(source,max_displacement_mm=1e-8)


if __name__ == "__main__":
    unittest.main()

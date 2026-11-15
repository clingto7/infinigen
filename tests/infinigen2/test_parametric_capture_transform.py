"""Verify generation-time box coordinates survive placement without fitting shape."""
import unittest

import bpy
import numpy as np
from mathutils import Matrix, Vector

from infinigen2.workpieces.parametric_capture import ParametricCapture


class Wrapped:
    def __init__(self, obj):
        self.obj = obj

    def item(self):
        return self.obj


class CaptureTransformTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.mesh.primitive_cube_add(size=2)
        self.obj = bpy.context.object
        self.wrapped = Wrapped(self.obj)
        target = self.obj.data.attributes.new('spray_target', 'BOOLEAN', 'FACE')
        for face in target.data:
            face.value = True

    def capture(self):
        capture = ParametricCapture()
        capture.board(self.wrapped, (2, 2, 2), 'test_board')
        return capture

    def test_post_capture_placement_and_applied_uniform_scale(self):
        capture = self.capture()
        transform = Matrix.Translation(Vector((0.7, -1.3, 2.1))) @ Matrix.Rotation(0.43, 4, 'Y') @ Matrix.Scale(1.8, 4)
        # Join/apply-transform changes mesh coordinates, not stored source values.
        for vertex in self.obj.data.vertices:
            vertex.co = transform @ vertex.co
        self.obj.matrix_world = Matrix.Translation(Vector((0.4, 0.2, -0.1)))
        artifact = capture.export(self.wrapped)
        self.assertEqual(artifact['description_coverage']['represented_target_triangle_count'], 12)
        surfaces = artifact['parts'][0]['surfaces']
        self.assertEqual(len(surfaces), 6)
        for surface in surfaces:
            self.assertAlmostEqual(np.linalg.norm(surface['geometry']['normal']), 1)
        expected_origin = self.obj.matrix_world @ transform @ Vector((-1, -1, -1))
        np.testing.assert_allclose(surfaces[0]['geometry']['origin'], expected_origin, atol=1e-6)

    def test_source_deformation_is_rejected(self):
        capture = self.capture()
        self.obj.data.vertices[0].co.x += 0.1
        with self.assertRaisesRegex(ValueError, 'deformed'):
            capture.export(self.wrapped)

    def test_thin_board_float32_roundoff(self):
        for vertex in self.obj.data.vertices:
            vertex.co.z *= 0.005
        capture = ParametricCapture()
        capture.board(self.wrapped, (2, 2, 0.01), 'thin_board')
        transform = Matrix.Translation(Vector((0.7, -1.3, 2.1))) @ Matrix.Rotation(0.43, 4, 'Y')
        for vertex in self.obj.data.vertices:
            vertex.co = transform @ vertex.co
        artifact = capture.export(self.wrapped)
        self.assertEqual(artifact['description_coverage']['represented_target_triangle_count'], 12)

    def test_missing_source_tags_are_diagnostic_not_approval(self):
        capture = ParametricCapture()
        coverage = capture.coverage(self.wrapped, {})
        self.assertEqual(coverage['target_triangles'], 12)
        self.assertEqual(coverage['tagged_target_triangles'], 0)
        self.assertEqual(coverage['untagged_target_triangle_ids'], list(range(12)))

    def test_nonuniform_scale_is_not_silently_accepted(self):
        capture = self.capture()
        self.obj.matrix_world = Matrix.Diagonal((2, 1, 1, 1))
        with self.assertRaisesRegex(ValueError, 'uniform scale'):
            capture.export(self.wrapped)

    def test_source_coordinate_loss_is_rejected(self):
        capture = self.capture()
        self.obj.data.attributes.remove(self.obj.data.attributes['parametric_source_position'])
        with self.assertRaisesRegex(ValueError, 'correspondences'):
            capture.export(self.wrapped)

    def test_duplicate_capture_is_rejected(self):
        capture = self.capture()
        with self.assertRaisesRegex(ValueError, 'already captured'):
            capture.board(self.wrapped, (2, 2, 2), 'duplicate')


if __name__ == '__main__':
    unittest.main()

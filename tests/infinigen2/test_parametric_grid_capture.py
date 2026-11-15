"""Construction lineage, deformation and unsupported topology for ruled panels."""
from pathlib import Path
import sys
import unittest

import bpy
import numpy as np
import procfunc as pf

from infinigen2.objects.chair import chair_back_solid, chair_seat_dining
from infinigen2.workpieces.parametric_capture import ParametricCapture

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from spraybot_parametric_sweep_validate import validate_sweep
from spraybot_parametric_consumer import consume


class GridCaptureTests(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def seat(self):
        return pf.nodes.to_mesh_object(chair_seat_dining(
            depth=.5, half_width=.25, thickness=.045,
            front_bow=.03, back_bow=.02, front_dip=.01,
        ).seat)

    def check(self, obj):
        pf.ops.attr.write_attribute(obj, True, 'spray_target', domain='FACE')
        capture = ParametricCapture()
        self.assertTrue(capture.grid(obj, 'panel'), capture.unsupported_primitives)
        artifact = capture.export(obj)
        mesh = obj.item().data
        mesh.calc_loop_triangles()
        triangles = np.asarray([[obj.item().matrix_world @ mesh.vertices[i].co
                                 for i in tri.vertices] for tri in mesh.loop_triangles])
        for surface in artifact['parts'][0]['surfaces']:
            validate_sweep(surface, triangles)
        self.assertEqual(artifact['description_coverage']['represented_target_triangle_count'], len(triangles))
        self.assertTrue(consume(artifact))

    def test_bowed_dipped_seat(self):
        self.check(self.seat())

    def test_bowed_solid_back(self):
        obj = pf.nodes.to_mesh_object(chair_back_solid(
            dimensions=(.035, .5, .4), top_rise=.04,
        ))
        self.check(obj)

    def test_bevel_cannot_be_mislabeled_as_source_grid(self):
        obj = self.seat()
        pf.ops.modifier.bevel(obj, width=.005, segments=2)
        capture = ParametricCapture()
        self.assertFalse(capture.grid(obj, 'panel'))
        self.assertTrue(capture.unsupported_primitives)
        self.assertFalse(capture.instances)
        self.assertIsNone(obj.item().data.attributes.get('parametric_instance'))

    def test_missing_lineage_does_not_fall_back_to_mesh(self):
        obj = self.seat()
        mesh = obj.item().data
        mesh.attributes.remove(mesh.attributes['parametric_grid_address'])
        capture = ParametricCapture()
        self.assertFalse(capture.grid(obj, 'panel'))
        self.assertFalse(capture.instances)


if __name__ == '__main__':
    unittest.main()

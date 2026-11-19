"""Geometric checks that protect a planned spray path from hitting other parts."""

import sys
import unittest
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from spraybot_trajectory.path_checks import (
    check_exported_motion, check_exported_rays, clear_motion, clear_rays,
)


class TrajectoryGeometryChecks(unittest.TestCase):
    def test_ray_to_wrong_part_is_rejected_even_at_expected_distance(self):
        seat = trimesh.creation.box(extents=[40, 40, 10])
        seat.apply_translation([0, 0, -5])  # target surface z=0
        arm = trimesh.creation.box(extents=[20, 20, 10])
        arm.apply_translation([0, 0, -3])  # arm surface z=2, close enough for distance tolerance
        mesh = trimesh.util.concatenate([seat, arm])
        allowed = np.zeros(len(mesh.faces), dtype=bool)
        allowed[:len(seat.faces)] = True
        surface = np.array([[0.0, 0.0, 0.0]])
        nozzle = np.array([[0.0, 0.0, 120.0]])

        self.assertTrue(clear_rays(mesh, surface, nozzle)[0])
        self.assertFalse(clear_rays(mesh, surface, nozzle, allowed)[0])

    def test_nozzle_travel_requires_clearance_not_just_no_intersection(self):
        arm = trimesh.creation.box(extents=[20, 20, 20])
        nozzle = np.array([[-50.0, 25.0, 0.0], [50.0, 25.0, 0.0]])

        self.assertTrue(clear_motion(arm, nozzle)[0])
        self.assertFalse(clear_motion(arm, nozzle, arm, 30.0)[0])

    def test_exported_aims_reject_wrong_part_and_empty_rays(self):
        seat = trimesh.creation.box(extents=[40, 40, 10])
        seat.apply_translation([0, 0, -5])
        arm = trimesh.creation.box(extents=[20, 20, 10])
        arm.apply_translation([0, 0, -3])
        mesh = trimesh.util.concatenate([seat, arm])
        labels = np.array([0] * len(seat.faces) + [1] * len(arm.faces))
        sources = [{"part": "seat"}]
        down = [{"points": [[0, 0, 0.12], [0.005, 0, 0.12]],
                 "aims": [[0, 0, -1], [0, 0, -1]]}]
        up = [{"points": [[0, 0, 0.12], [0.005, 0, 0.12]],
               "aims": [[0, 0, 1], [0, 0, 1]]}]

        for paths in (down, up):
            check = check_exported_rays(mesh, paths, sources, 120.0, labels,
                                        {"0": "seat", "1": "arm"})
            self.assertEqual(check["invalid_stroke_ids"], [0])

    def test_generic_exported_geometry_rejects_empty_ray_and_crossing_path(self):
        mesh = trimesh.creation.box(extents=[20, 20, 20])
        wrong_direction = [{"points": [[0, 0, 0.12], [0.005, 0, 0.12]],
                            "aims": [[0, 0, 1], [0, 0, 1]]}]
        crossing = [{"points": [[-0.05, 0, 0], [0.05, 0, 0]],
                     "aims": [[0, 0, -1], [0, 0, -1]]}]

        self.assertEqual(check_exported_rays(mesh, wrong_direction,
                                             [{"part": "unknown"}], None)["invalid_stroke_ids"], [0])
        self.assertEqual(check_exported_motion(mesh, crossing)["invalid_stroke_ids"], [0])


if __name__ == "__main__":
    unittest.main()

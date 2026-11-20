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
from spraybot_trajectory.armchair import relocate_stroke


class TrajectoryGeometryChecks(unittest.TestCase):
    def test_seam_repair_moves_entire_stroke_without_changing_its_shape(self):
        seat = trimesh.creation.box(extents=[20, 20, 10])
        seat.apply_translation([-10, 0, -5])
        arm = trimesh.creation.box(extents=[100, 20, 10])
        arm.apply_translation([50, 0, -5])
        mesh = trimesh.util.concatenate([seat, arm])
        allowed = np.zeros(len(mesh.faces), dtype=bool)
        allowed[len(seat.faces):] = True
        surface = [[0.0, 0.0, 0.0], [20.0, 0.0, 0.0],
                   [40.0, 0.0, 0.0], [60.0, 0.0, 0.0], [80.0, 0.0, 0.0]]
        stroke = {"surface_points": surface,
                  "nozzle_points": [[x, y, z + 120] for x, y, z in surface]}
        original_surface = np.asarray(stroke["surface_points"])
        original_nozzle = np.asarray(stroke["nozzle_points"])

        repaired, mode, shift_mm = relocate_stroke(mesh, stroke, allowed)

        self.assertEqual(len(repaired["surface_points"]), len(surface))
        self.assertIn(mode, ("nozzle", "rigid"))
        self.assertLessEqual(shift_mm, 2)
        shifted_surface = np.asarray(repaired["surface_points"])
        shifted_nozzle = np.asarray(repaired["nozzle_points"])
        np.testing.assert_allclose(np.diff(shifted_surface, axis=0),
                                   np.diff(original_surface, axis=0), atol=1e-10)
        np.testing.assert_allclose(np.diff(shifted_nozzle, axis=0),
                                   np.diff(original_nozzle, axis=0), atol=1e-10)
        np.testing.assert_allclose(np.ptp(shifted_surface-original_surface, axis=0), 0,
                                   atol=1e-10)
        np.testing.assert_allclose(np.ptp(shifted_nozzle-original_nozzle, axis=0), 0,
                                   atol=1e-10)

    def test_seat_repair_moves_entire_nozzle_path_away_from_arm(self):
        seat = trimesh.creation.box(extents=[200, 200, 10])
        seat.apply_translation([0, 0, -5])
        arm = trimesh.creation.box(extents=[120, 20, 20])
        arm.apply_translation([0, 80, 120])
        mesh = trimesh.util.concatenate([seat, arm])
        allowed = np.zeros(len(mesh.faces), dtype=bool)
        allowed[:len(seat.faces)] = True
        surface = np.array([[-50., 80., 0.], [0., 80., 0.], [50., 80., 0.]])
        nozzle = surface + [0., 0., 120.]
        stroke = {"surface_points": surface.tolist(), "nozzle_points": nozzle.tolist()}

        repaired, mode, shift_mm = relocate_stroke(mesh, stroke, allowed, arm)

        self.assertEqual(mode, 'lateral_nozzle')
        self.assertGreaterEqual(shift_mm, 30)
        np.testing.assert_allclose(repaired['surface_points'], surface)
        shifted = np.asarray(repaired['nozzle_points'])
        np.testing.assert_allclose(np.diff(shifted, axis=0), np.diff(nozzle, axis=0))
        np.testing.assert_allclose(np.ptp(shifted-nozzle, axis=0), 0, atol=1e-10)
        self.assertGreaterEqual(arm.nearest.on_surface(shifted)[1].min(), 30)

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

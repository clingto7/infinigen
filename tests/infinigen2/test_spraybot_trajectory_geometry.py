"""Geometric checks that protect a planned spray path from hitting other parts."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from spraybot_trajectory.path_checks import (
    check_exported_motion, check_exported_rays, check_exported_smoothness,
    clear_motion, clear_rays,
)
from spraybot_trajectory.armchair import coating_scope, relocate_stroke
from spraybot_trajectory.planar import _join_rows, _rectangle_rows, _selected


class TrajectoryGeometryChecks(unittest.TestCase):
    def test_narrow_board_edge_has_one_centered_row(self):
        surface = {"type": "plane_rectangle", "geometry": {
            "origin": [0, 0, 0], "u": [0.6, 0, 0], "v": [0, 0.03, 0],
            "normal": [0, 0, 1]}}
        rows = _rectangle_rows(surface)
        self.assertEqual(len(rows), 1)
        self.assertAlmostEqual(rows[0][0, 1], 15.0)

    def test_board_edge_policy_includes_both_axes(self):
        for semantic in ("top", "seat", "shelf"):
            for axis in (0, 1):
                for sign in (-1, 1):
                    normal = np.eye(3)[axis] * sign
                    surface = {"type": "plane_rectangle", "geometry": {
                        "origin": [0, 0, 0], "u": [0.5, 0, 0],
                        "v": [0, 0, 0.03], "normal": normal.tolist()},
                        "mesh_mapping": {"construction_triangle_ids": [0]}}
                    self.assertTrue(_selected(surface, semantic, np.array([True]),
                                              np.zeros(3), "folding_table"))

    def test_corner_shelf_diagonal_edge_is_planned(self):
        normal = np.array([0.68, 0.74, 0.0])
        normal /= np.linalg.norm(normal)
        surface = {"type": "plane_rectangle", "geometry": {
            "origin": [0, 0, 0], "u": [0.4, 0.4, 0],
            "v": [0, 0, 0.016], "normal": normal.tolist()},
            "mesh_mapping": {"construction_triangle_ids": [0]}}
        self.assertTrue(_selected(surface, "shelf", np.array([True]),
                                  np.zeros(3), "corner_shelf"))

    def test_ladder_back_slats_do_not_depend_on_whole_chair_center(self):
        surface = {"type": "plane_rectangle", "geometry": {
            "origin": [-0.234, 0, 0.52], "u": [0, 0.41, 0],
            "v": [0, 0, 0.022], "normal": [-1, 0, 0]},
            "mesh_mapping": {"construction_triangle_ids": [0]}}
        for center in (np.array([-226., 0., 644.]), np.array([0., 0., 400.])):
            self.assertTrue(_selected(surface, "slat", np.array([True]),
                                      center, "ladder_back_chair"))

    def test_back_post_inner_edge_is_not_planned(self):
        surface = {"type": "plane_rectangle", "geometry": {
            "origin": [0, 0.3, 0], "u": [0, 0, 0.5],
            "v": [0.03, 0, 0], "normal": [0, -1, 0]},
            "mesh_mapping": {"construction_triangle_ids": [0]}}
        self.assertFalse(_selected(surface, "back", np.array([True]),
                                   np.zeros(3), "ladder_back_chair"))

    def test_staggered_shelf_keeps_exposed_front_thin_edge(self):
        surface = {"type": "plane_rectangle", "geometry": {
            "origin": [0.15, 0, 0], "u": [0, 0.3, 0],
            "v": [0, 0, 0.016], "normal": [1, 0, 0]},
            "mesh_mapping": {"construction_triangle_ids": [0]}}
        self.assertTrue(_selected(surface, "shelf", np.array([True]),
                                  np.zeros(3), "staggered_display_shelf"))
        surface["geometry"]["normal"] = [-1, 0, 0]
        self.assertFalse(_selected(surface, "shelf", np.array([True]),
                                   np.zeros(3), "staggered_display_shelf"))

    def test_adjacent_clear_rows_form_one_rounded_serpentine(self):
        mesh = trimesh.creation.box(extents=[500, 300, 20])
        allowed = mesh.face_normals[:, 2] > 0.9
        rows = []
        for index, y in enumerate((-40.0, 40.0)):
            landing = np.column_stack((np.linspace(-200, 200, 29),
                                       np.full(29, y), np.full(29, 10.0)))
            rows.append({"surface_points": landing.tolist(),
                         "nozzle_points": (landing + [0, 0, 120]).tolist(),
                         "reason": f"board:top:row_{index}", "part": "top"})
        joined = _join_rows(mesh, rows, allowed, np.array([0., 0., 1.]))
        self.assertEqual(len(joined), 1)
        self.assertEqual(joined[0]["reason"], "board:top:serpentine")

    def test_exported_smoothness_flags_a_sharp_turn(self):
        paths = [
            {'points': [[0., 0., 0.], [0.02, 0., 0.], [0.02, 0.02, 0.]]},
            {'points': [[0., 0., 0.], [0.02, 0., 0.], [0.04, 0.005, 0.]]},
        ]
        result = check_exported_smoothness(paths)
        self.assertEqual(result['invalid_stroke_ids'], [0])
        self.assertAlmostEqual(result['observed_max_turn_deg'], 90.)

    def test_armchair_scope_includes_seat_front_and_side_rim(self):
        normals = ([0., 0., 1.], [1., 0., 0.],
                   [0., -1., 0.], [-1., 0., 0.])
        surfaces = []
        for index, normal in enumerate(normals):
            x = float(index * 10)
            surfaces.append({
                'normal': normal,
                'geometry': {'corners': [[x, 0., 0.], [x + 1, 0., 0.],
                                         [x + 1, 1., 0.], [x, 1., 0.]]},
                'mesh_mapping': {'construction_triangle_ids': [index]},
            })

        def fake_sampler(surface):
            return 'plane_rectangle', 1, 1, lambda u, v: (np.zeros(3), surface['normal'])

        with patch('spraybot_trajectory.armchair.sampler', side_effect=fake_sampler):
            selected, _ = coating_scope({'parts': [{'semantic': 'seat',
                                                     'surfaces': surfaces}]},
                                         np.ones(4, dtype=bool))
        self.assertEqual(selected.tolist(), [True, True, True, False])

    def test_armchair_scope_includes_front_post_face_for_L_pass(self):
        specs = (
            ([[0., -20., 100.], [100., -20., 100.],
              [100., 0., 100.], [0., 0., 100.]], [0., 0., 1.]),
            ([[100., -20., 0.], [100., 0., 0.],
              [100., 0., 100.], [100., -20., 100.]], [1., 0., 0.]),
            ([[0., -20., 0.], [0., 0., 0.],
              [0., 0., 100.], [0., -20., 100.]], [1., 0., 0.]),
        )
        parts = []
        for index, (corners, normal) in enumerate(specs):
            surface = {'geometry': {'corners': corners}, 'normal': normal,
                       'mesh_mapping': {'construction_triangle_ids': [index]}}
            parts.append({'semantic': 'arm', 'surfaces': [surface]})

        def fake_sampler(surface):
            return 'plane_rectangle', 1, 1, lambda u, v: (np.zeros(3), surface['normal'])

        with patch('spraybot_trajectory.armchair.sampler', side_effect=fake_sampler):
            selected, _ = coating_scope({'parts': parts}, np.ones(3, dtype=bool))
        self.assertEqual(selected.tolist(), [True, True, False])

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
        joint = [{"part": "seat", "allowed_parts": ["seat", "arm"]}]
        self.assertEqual(check_exported_rays(mesh, down, joint, 120.0, labels,
                                             {"0": "seat", "1": "arm"})["invalid_stroke_ids"], [])

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

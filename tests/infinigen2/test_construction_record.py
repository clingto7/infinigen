"""Checks that observed parameters describe the generated geometry without changing it."""

import json
import sys

import bpy
import numpy as np
import unittest

from infinigen2.util.construction_record import ConstructionRecorder
from infinigen2.workpieces.common import REGISTRY
import infinigen2.workpieces  # populate registry


def geometry(obj):
    obj = obj.item()
    obj.data.calc_loop_triangles()
    return (np.array([obj.matrix_world @ v.co for v in obj.data.vertices]),
            np.array([t.vertices[:] for t in obj.data.loop_triangles]))


def check_recording_preserves_geometry_and_rng(category):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rng = np.random.default_rng(42)
    expected = geometry(REGISTRY[category].build(rng))
    expected_rng = rng.random()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rng = np.random.default_rng(42)
    with ConstructionRecorder() as recorder:
        actual = geometry(REGISTRY[category].build(rng))
    for left, right in zip(expected, actual):
        np.testing.assert_array_equal(left, right)
    assert rng.random() == expected_rng
    json.dumps(recorder.payload(), allow_nan=False)
    assert recorder.calls and recorder.sources
    assert sys.getprofile() is None


def test_arm_board_parameters_match_generated_vertices():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with ConstructionRecorder() as recorder:
        result = REGISTRY["armchair"].build(np.random.default_rng(8))
    vertices, _ = geometry(result)
    boards = [r for r in recorder.calls if r["function"].endswith(".board")
              and r["inputs"].get("part") == "arm"]
    assert len(boards) == 6  # two rails and four posts
    signs = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)])
    for record in boards:
        args = record["inputs"]
        corners = np.array(args["center"]) + signs * np.array(args["size"]) / 2
        for corner in corners:
            assert np.linalg.norm(vertices - corner, axis=1).min() < 2e-7


def test_profile_restored_after_failure():
    with unittest.TestCase().assertRaisesRegex(ValueError, "intentional"):
        with ConstructionRecorder():
            raise ValueError("intentional")
    assert sys.getprofile() is None


class ConstructionRecordTests(unittest.TestCase):
    def test_geometry_and_randomness(self):
        for category in ("armchair", "cabriole_leg_table", "corner_shelf"):
            with self.subTest(category=category):
                check_recording_preserves_geometry_and_rng(category)

    def test_arm_geometry(self):
        test_arm_board_parameters_match_generated_vertices()

    def test_cleanup(self):
        test_profile_restored_after_failure()

    def test_native_chair_seeds_the_entire_build(self):
        from infinigen2.workpieces.native_spraybot.infinigen_chair import build

        results = []
        for global_seed in (123, 456):
            bpy.ops.wm.read_factory_settings(use_empty=True)
            np.random.seed(global_seed)
            result = build(np.random.default_rng(0))
            results.append((geometry(result.mesh), result.structure_priors))
        # Blender modifiers can differ by float32 roundoff; sampled parameters
        # and centerlines must be exact and independent of ambient RNG state.
        self.assertEqual(results[0][1], results[1][1])
        np.testing.assert_allclose(results[0][0][0], results[1][0][0], atol=1e-7, rtol=0)
        # Float32 roundoff may also choose a different quad diagonal during
        # tessellation; seed reproducibility does not promise triangle indices.
        self.assertEqual(results[0][0][1].shape, results[1][0][1].shape)


if __name__ == "__main__":
    unittest.main()

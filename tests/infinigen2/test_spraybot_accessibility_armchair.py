"""A support must not hide an otherwise exterior seat polygon."""

import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from spraybot_mass_worker import generate  # noqa: E402


class ArmchairAccessibilityTest(unittest.TestCase):
    def test_exposed_seat_triangles_next_to_arm_supports(self):
        # These are the reported seed 0/4/6 failures in the exported OBJ order.
        for seed, triangles in ((0, (680, 682)), (4, (680, 682)), (6, (680,))):
            with self.subTest(seed=seed):
                result = generate("workpiece:armchair", seed)
                mesh = result.mesh.item().data
                mesh.calc_loop_triangles()
                accessible = mesh.attributes["geometry_accessible"].data
                for triangle in triangles:
                    polygon = mesh.loop_triangles[triangle].polygon_index
                    self.assertTrue(accessible[polygon].value,
                                    f"seed {seed} seat triangle {triangle} is exterior")


if __name__ == "__main__":
    unittest.main()

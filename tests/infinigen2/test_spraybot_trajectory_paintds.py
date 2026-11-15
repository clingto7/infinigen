"""Native Spraybot trajectory files encode the spray aim as tool Z in ZYX Euler."""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from spraybot_trajectory.paintds import aim_to_zyx_deg, euler_zyx_to_aim  # noqa: E402


class PaintDSConventionTest(unittest.TestCase):
    def test_roundtrip_cardinal_and_oblique_aims(self):
        directions = np.array([[0., 0., 1.], [0., 0., -1.], [1., 0., 0.],
                               [0., 1., 0.], [0.3, -0.4, 0.8660254]])
        directions /= np.linalg.norm(directions, axis=1, keepdims=True)
        encoded = aim_to_zyx_deg(directions)
        np.testing.assert_allclose(euler_zyx_to_aim(encoded), directions, atol=1e-9)
        np.testing.assert_allclose(encoded[0], [0., 0., 0.], atol=1e-9)


if __name__ == "__main__":
    unittest.main()

"""A trajectory is available only for the exact review model it names."""

import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import spraybot_generator_ui_server as server  # noqa: E402


class TrajectoryBindingTest(unittest.TestCase):
    def test_model_change_invalidates_trajectory(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            review = root / "review"
            trajectories = root / "trajectories"
            model = review / "interfaces/workpiece:armchair/episodes/seed_0000000000/model.json"
            artifact = trajectories / "workpiece:armchair/seed_0000000000.json"
            model.parent.mkdir(parents=True)
            artifact.parent.mkdir(parents=True)
            model.write_text('{"seed":0,"vertices":[]}', encoding="utf-8")
            artifact.write_text(json.dumps({"model_sha256": hashlib.sha256(model.read_bytes()).hexdigest()}))
            with patch.object(server, "REVIEW_ROOT", review), patch.object(server, "TRAJECTORY_ROOT", trajectories):
                self.assertEqual(server.paired_trajectory("workpiece:armchair", "seed_0000000000"), artifact)
                model.write_text('{"seed":0,"vertices":[1]}', encoding="utf-8")
                self.assertIsNone(server.paired_trajectory("workpiece:armchair", "seed_0000000000"))


if __name__ == "__main__":
    unittest.main()

"""The review workspace must not become the source of interface decisions."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import spraybot_interface_state as state  # noqa: E402
import spraybot_review_root as review_root  # noqa: E402


class InterfaceStateTest(unittest.TestCase):
    def test_machine_pass_review_and_invalidation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            records = root / "records"
            check = root / "machine-check.json"
            check.write_text(json.dumps({
                "geometry_gate": {"status": "parametric_geometry_gate_passed",
                                  "category_id": "coat_rack", "episodes": 20},
                "capture_invariance": {"status": "capture_invariance_passed",
                                       "category_id": "coat_rack",
                                       "seeds_compared": list(range(20))},
            }))
            state.record_machine_pass("workpiece:coat_rack", check, records)
            self.assertEqual(state.read_record("workpiece:coat_rack", records)["status"], "awaiting_review")
            state.save_human_review("workpiece:coat_rack", {
                "status": "needs_fix", "reviewer": "reviewer", "notes": "bad geometry",
                "field_issues": [{"seed": 0, "field": "model", "note": "bad geometry"}],
            }, records)
            self.assertEqual(state.read_record("workpiece:coat_rack", records)["status"], "needs_fix")
            with self.assertRaisesRegex(ValueError, "new machine evidence"):
                state.record_machine_pass("workpiece:coat_rack", check, records)
            with self.assertRaisesRegex(ValueError, "new machine gate"):
                state.save_human_review("workpiece:coat_rack", {
                    "status": "accepted", "reviewer": "reviewer", "field_issues": [],
                }, records)
            state.invalidate("workpiece:coat_rack", "generator changed", records)
            self.assertEqual(state.read_record("workpiece:coat_rack", records)["status"], "developing")

    def test_review_writes_only_project_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "review-root"
            records = Path(directory) / "project-records"
            generator = "workpiece:coat_rack"
            episode = root / "interfaces" / generator / "episodes" / "seed_0000000000"
            episode.mkdir(parents=True)
            (episode / "model.json").write_text("{}")
            (root / "review_manifest.json").write_text(json.dumps({
                "schema": review_root.SCHEMA,
                "interfaces": {generator: {"episodes": [episode.name]}},
            }))
            machine = {"schema": state.SCHEMA, "interface_id": generator,
                       "status": "awaiting_review", "machine_gate": {"status": "passed"},
                       "human_review": None}
            with patch.object(review_root, "read_committed_record", return_value=machine), \
                 patch.object(review_root, "save_human_review",
                              side_effect=lambda name, data: state.save_human_review(name, data, records)):
                state.write_record(machine, records)
                review_root.save_review(root, generator, {
                    "status": "accepted", "reviewer": "reviewer", "notes": "checked",
                    "field_issues": [], "seed_issues": [],
                })
            self.assertFalse((root / "interfaces" / generator / "human-review.json").exists())
            self.assertEqual(state.read_record(generator, records)["status"], "ready")


if __name__ == "__main__":
    unittest.main()

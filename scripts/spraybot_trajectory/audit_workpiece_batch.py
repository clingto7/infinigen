"""Audit the active reviewed workpiece interfaces before human trajectory review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from spraybot_trajectory.pair_workpiece import _check_paintds


CATEGORIES = (
    "corner_shelf", "ladder_shelf", "metal_shelving",
    "backed_bench", "backless_bench", "bar_chair", "armchair",
    "folding_chair", "ladder_back_chair", "windsor_chair",
    "cabriole_leg_table", "corner_desk", "folding_table", "hairpin_leg_table",
    "trestle_table", "workbench", "crib", "coat_rack", "serving_cart",
)


def audit(review_root: Path, trajectory_root: Path) -> dict:
    results = []
    for category in CATEGORIES:
        interface_id = f"workpiece:{category}"
        for seed in range(10):
            episode = f"seed_{seed:010d}"
            model_path = review_root / "interfaces" / interface_id / "episodes" / episode / "model.json"
            artifact_path = trajectory_root / interface_id / f"{episode}.json"
            paintds_path = trajectory_root / interface_id / "paintds" / f"{episode}.txt"
            errors = []
            try:
                model_hash = hashlib.sha256(model_path.read_bytes()).hexdigest()
                artifact = json.loads(artifact_path.read_bytes())
                check = artifact["check"]
                if (artifact["interface_id"], artifact["seed"], artifact["model_sha256"]) != (
                        interface_id, seed, model_hash):
                    errors.append("model/trajectory identity mismatch")
                if check.get("machine_gate") != "passed":
                    errors.append("machine gate failed")
                for name in ("path_ray_check", "exported_ray_check", "exported_motion_check",
                             "exported_smoothness_check"):
                    if check.get(name, {}).get("invalid_stroke_ids"):
                        errors.append(f"{name} invalid strokes")
                if check.get("path_ray_check", {}).get("sample_count", 0) <= 0:
                    errors.append("no sampled path rays")
                if not artifact["strokes"] or len(artifact["strokes"]) != len(artifact["stroke_sources"]):
                    errors.append("stroke/source mismatch")
                source_path = Path(check["source_planner"])
                if hashlib.sha256(source_path.read_bytes()).hexdigest() != check["source_planner_sha256"]:
                    errors.append("source planner hash mismatch")
                for key, filename in (
                        ("round_planner_sha256", "round_members.py"),
                        ("curved_planner_sha256", "curved_members.py"),
                        ("adapter_sha256", "pair_workpiece.py"),
                        ("path_checks_sha256", "path_checks.py"),
                        ("paintds_sha256", "paintds.py"),
                        ("curved_helpers_sha256", "armchair.py")):
                    if key in check and hashlib.sha256(Path(__file__).with_name(filename).read_bytes()).hexdigest() != check[key]:
                        errors.append(f"{filename} hash mismatch")
                paintds_check = _check_paintds(paintds_path, artifact["strokes"])
                if paintds_check["status"] != "passed":
                    errors.append("PaintDS/Web mismatch")
            except Exception as error:
                errors.append(f"{type(error).__name__}: {error}")
            results.append({"interface_id": interface_id, "seed": seed,
                            "status": "passed" if not errors else "failed", "errors": errors})
    return {"schema": "spraybot.trajectory-batch-audit.v1",
            "expected_interfaces": len(CATEGORIES), "expected_episodes": len(CATEGORIES) * 10,
            "passed": sum(row["status"] == "passed" for row in results),
            "failed": sum(row["status"] == "failed" for row in results),
            "results": results}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--trajectory-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.review_root, args.trajectory_root)
    if args.output:
        args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("expected_interfaces", "expected_episodes", "passed", "failed")}))
    raise SystemExit(0 if result["failed"] == 0 else 1)

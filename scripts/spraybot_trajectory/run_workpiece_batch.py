"""Generate paired trajectories for reviewed workpiece seeds and retain all checks."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from spraybot_trajectory.pair_workpiece import pair


def run(review_root: Path, output_root: Path, categories: list[str],
        seeds: list[int]) -> dict:
    if not categories or not seeds:
        raise ValueError("categories and seeds are required")
    output_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for category in categories:
        interface_id = f"workpiece:{category}"
        for seed in seeds:
            model = (review_root / "interfaces" / interface_id / "episodes"
                     / f"seed_{seed:010d}" / "model.json")
            try:
                check = pair(model, output_root)
                row = {"interface_id": interface_id, "seed": seed,
                       "status": check["geometry_gate"],
                       "strokes": check["stroke_count"],
                       "invalid_rays": len(check["exported_ray_check"]["invalid_stroke_ids"]),
                       "invalid_motion": len(check["exported_motion_check"]["invalid_stroke_ids"]),
                       "invalid_smoothness": len(check["exported_smoothness_check"]["invalid_stroke_ids"]),
                       "unplanned_rows": check["visible_unplanned_rows"],
                       "fully_occluded_rows": check["fully_occluded_rows"]}
            except Exception as error:
                row = {"interface_id": interface_id, "seed": seed,
                       "status": "error", "error": f"{type(error).__name__}: {error}"}
            rows.append(row)
            (output_root / "batch-check.json").write_text(
                json.dumps({"schema": "spraybot.trajectory-batch.v1",
                            "results": rows,
                            "status_counts": dict(Counter(item["status"] for item in rows))},
                           indent=2) + "\n")
            print(json.dumps(row), flush=True)
    return {"results": rows,
            "status_counts": dict(Counter(item["status"] for item in rows))}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--categories", nargs="+", required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(10)))
    args = parser.parse_args()
    run(args.review_root, args.output, args.categories, args.seeds)

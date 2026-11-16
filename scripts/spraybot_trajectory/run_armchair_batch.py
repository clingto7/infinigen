"""Build the reviewed Armchair 10-seed trajectory pilot and browser artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from spraybot_trajectory.armchair import generate
from spraybot_trajectory.check_visibility import evaluate
from spraybot_trajectory.prepare_viewer import package


def run(batch: Path, review_record: Path, review_root: Path, output: Path, count: int = 10) -> dict:
    if output.exists():
        raise FileExistsError(f"output must be new: {output}")
    episodes = {}
    for path in batch.glob("episode_*/metadata.json"):
        seed = json.loads(path.read_text())["seed"]
        if seed in episodes:
            raise ValueError(f"duplicate seed {seed}: {batch}")
        episodes[seed] = path.parent
    if set(range(count)) - episodes.keys():
        raise ValueError(f"batch lacks seeds: {sorted(set(range(count)) - episodes.keys())}")
    output.mkdir(parents=True)
    checks = []
    for seed in range(count):
        directory = output / f"seed_{seed:010d}"
        generate(episodes[seed], directory, review_record, 25, 10, 100)
        checks.append(evaluate(directory))
    result = {"schema": "spraybot.parametric-armchair-batch.v1", "episodes": checks}
    (output / "batch-check.json").write_text(json.dumps(result, indent=2) + "\n")
    package(output, review_root)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("machine_batch", type=Path)
    parser.add_argument("review_record", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--count", type=int, default=10)
    args = parser.parse_args()
    if args.count < 1:
        parser.error("count must be positive")
    result = run(args.machine_batch, args.review_record, args.review_root, args.output, args.count)
    print(json.dumps({"episodes": len(result["episodes"]),
                      "strokes": sum(x["stroke_count"] for x in result["episodes"]),
                      "waypoints": sum(x["waypoint_count"] for x in result["episodes"])}))

"""Batch acceptance screen for exported parametric episodes.

Run after the generator worker finishes. This command reads only the exported
files; it does not import Blender, the generator, or source geometry modules.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from spraybot_parametric_consumer import consume
from spraybot_parametric_validate import validate


def gate(batch: Path, minimum_seeds: int = 20, expected_instance_counts: set[int] | None = None) -> dict:
    episodes = sorted(batch.glob("episode_*/metadata.json"))
    if len(episodes) < minimum_seeds:
        raise ValueError(f"need at least {minimum_seeds} episodes; found {len(episodes)}")
    seeds, categories, instance_counts = set(), set(), set()
    target_triangles = surfaces = strokes = points = 0
    max_normal_angle = 0.0
    for metadata_path in episodes:
        metadata = json.loads(metadata_path.read_text())
        seed = metadata["seed"]
        if seed in seeds:
            raise ValueError(f"duplicate seed: {seed}")
        seeds.add(seed)
        categories.add(metadata["category_id"])
        row = validate(metadata_path.parent)
        artifact_name = metadata.get("parametric_file") or metadata.get("parametric_candidate_file")
        artifact = json.loads((metadata_path.parent / artifact_name).read_text())
        paths = consume(artifact)
        instance_counts.add(row["parts"])
        target_triangles += row["target_triangles"]
        surfaces += row["surfaces"]
        strokes += len(paths)
        points += sum(len(path["points"]) for path in paths)
        max_normal_angle = max(max_normal_angle, row["max_normal_angle_deg"])
    if len(categories) != 1:
        raise ValueError(f"batch contains multiple categories: {sorted(categories)}")
    if expected_instance_counts and not expected_instance_counts <= instance_counts:
        raise ValueError(f"missing expected instance-count variants: {sorted(expected_instance_counts - instance_counts)}")
    return {"category_id": categories.pop(), "episodes": len(episodes),
            "seeds": sorted(seeds), "instance_counts": sorted(instance_counts),
            "target_triangles": target_triangles, "surfaces": surfaces,
            "consumer_strokes": strokes, "consumer_points": points,
            "max_mesh_normal_angle_deg": max_normal_angle,
            "status": "parametric_geometry_gate_passed"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("batch", type=Path)
    parser.add_argument("--minimum-seeds", type=int, default=20)
    parser.add_argument("--expect-instance-count", type=int, action="append", default=[])
    args = parser.parse_args()
    if args.minimum_seeds < 1 or any(count < 1 for count in args.expect_instance_count):
        parser.error("seed and instance counts must be positive")
    print(json.dumps(gate(args.batch, args.minimum_seeds, set(args.expect_instance_count)), allow_nan=False))

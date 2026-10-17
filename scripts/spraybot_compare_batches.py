"""Compare two spraybot_validate output directories seed-by-seed.

For every (interface, seed) pair present in both batches, compare the recorded
geometry hashes. Exact hashes are raw float32 vertex bytes and can differ below
Blender's ~1e-6 noise-eval jitter; normalized hashes (bbox-relative, 1/1000
rounding) are the reproduction signal. A normalized-hash mismatch on the same
interface and seed means the two batches did not reproduce each other.
"""

import argparse
import json
from pathlib import Path


def collect(root: Path) -> dict[tuple[str, int], dict]:
    samples = {}
    for result in sorted(root.glob("*/seed_*/result.json")):
        seed_dir = result.parent
        data = json.loads(result.read_text(encoding="utf-8"))
        samples[(seed_dir.parent.name, int(seed_dir.name.split("_")[1]))] = data[
            "metrics"
        ]
    return samples


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    args = parser.parse_args()
    old_samples = collect(args.old)
    new_samples = collect(args.new)
    shared = sorted(set(old_samples) & set(new_samples))
    exact_matches = sum(
        old_samples[k]["geometry_sha256"] == new_samples[k]["geometry_sha256"]
        for k in shared
    )
    normalized_matches = sum(
        old_samples[k]["normalized_shape_sha256"] == new_samples[k]["normalized_shape_sha256"]
        for k in shared
    )
    mismatched = [
        k for k in shared
        if old_samples[k]["normalized_shape_sha256"] != new_samples[k]["normalized_shape_sha256"]
    ]
    report = {
        "old_batch": str(args.old),
        "new_batch": str(args.new),
        "old_samples": len(old_samples),
        "new_samples": len(new_samples),
        "shared_pairs": len(shared),
        "exact_hash_matches": exact_matches,
        "normalized_hash_matches": normalized_matches,
        "normalized_mismatches": [
            {
                "interface": interface,
                "seed": seed,
                "old_triangles": old_samples[(interface, seed)]["triangles"],
                "new_triangles": new_samples[(interface, seed)]["triangles"],
            }
            for interface, seed in mismatched
        ],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

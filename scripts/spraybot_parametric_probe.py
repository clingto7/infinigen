"""Radar-side probe of generation-time capture for a registered workpiece."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import bpy
import numpy as np

from infinigen2.workpieces import generate
from infinigen2.workpieces.parametric_capture import ParametricCapture


def run(category: str, seed: int) -> dict:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with ParametricCapture() as capture:
        result = generate(category, np.random.default_rng(seed))
    artifact = capture.export(result.mesh)
    artifact["source"] = {"category_id": category, "seed": seed}
    return artifact


def main() -> None:
    if len(sys.argv) < 4:
        raise SystemExit("usage: script OUTPUT_DIRECTORY CATEGORY SEED [SEED ...]")
    output = Path(sys.argv[1]); output.mkdir(parents=True, exist_ok=True)
    category = sys.argv[2]
    for seed_text in sys.argv[3:]:
        seed = int(seed_text)
        artifact = run(category, seed)
        path = output / f"{category}-{seed:05d}.parametric.json"
        path.write_text(json.dumps(artifact, allow_nan=False, separators=(",", ":")) + "\n")
        surfaces = sum(len(part["surfaces"]) for part in artifact["parts"])
        print(json.dumps({"category_id": category, "seed": seed, "instances": len(artifact["parts"]),
                          "surfaces": surfaces,
                          "target_triangles": artifact["description_coverage"]["spray_target_triangle_count"],
                          "path": str(path)}), flush=True)


if __name__ == "__main__":
    main()

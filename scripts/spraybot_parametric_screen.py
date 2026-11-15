"""Radar-side one-seed coverage inventory for registered workpiece interfaces.

This is a triage tool, not a readiness gate. It reports which target faces
remain untagged by generation-time primitive capture, grouped by spray part.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import bpy
import numpy as np

from infinigen2.workpieces import CATEGORY_IDS, generate
from infinigen2.workpieces.parametric_capture import ParametricCapture
from spraybot_parametric_readiness import load as load_parametric_certifications


def screen(category: str, seed: int) -> dict:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    with ParametricCapture() as capture:
        result = generate(category, np.random.default_rng(seed))
    mesh = result.mesh.item().data
    mesh.calc_loop_triangles()
    target = mesh.attributes["spray_target"]
    part = mesh.attributes["spray_part"]
    tag = mesh.attributes.get("parametric_instance")
    missing = Counter()
    target_count = captured_count = 0
    for triangle in mesh.loop_triangles:
        polygon = triangle.polygon_index
        if not target.data[polygon].value:
            continue
        target_count += 1
        if tag is not None and tag.data[polygon].value > 0:
            captured_count += 1
        else:
            name = result.part_legend[part.data[polygon].value]
            missing[name] += 1
    try:
        capture.export(result.mesh)
        status, error = "surface_check_passed", None
    except Exception as exc:
        status, error = "incomplete", f"{type(exc).__name__}: {exc}"
    return {"category_id": category, "seed": seed, "status": status,
            "target_triangles": target_count, "captured_target_triangles": captured_count,
            "missing_by_part": dict(sorted(missing.items())), "error": error}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--only-incomplete", action="store_true")
    args = parser.parse_args()
    certified = load_parametric_certifications()
    names = [name for name in CATEGORY_IDS
             if not args.only_incomplete or f"workpiece:{name}" not in certified]
    rows = []
    for name in names:
        try:
            row = screen(name, args.seed)
        except Exception as exc:
            row = {"category_id": name, "seed": args.seed, "status": "generation_failed",
                   "error": f"{type(exc).__name__}: {exc}"}
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    summary = {"seed": args.seed, "checked": len(rows),
               "surface_check_passed": sum(row["status"] == "surface_check_passed" for row in rows),
               "incomplete": sum(row["status"] == "incomplete" for row in rows),
               "generation_failed": sum(row["status"] == "generation_failed" for row in rows)}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"summary": summary, "interfaces": rows}, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"summary": summary, "output": str(args.output) if args.output else None}), flush=True)


if __name__ == "__main__":
    main()

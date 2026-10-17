"""Sample one Spraybot workpiece into a compact mesh and inspection record.

Run with the Infinigen Python environment:
PYTHONPATH=src /path/to/.venv/bin/python scripts/spraybot_probe.py CATEGORY SEED OUTDIR
"""

import argparse
import json
from pathlib import Path

import bpy
import numpy as np

from infinigen2.objects.spraybot import generate_workpiece


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("category")
    parser.add_argument("seed", type=int)
    parser.add_argument("outdir", type=Path)
    parser.add_argument("--check-modifiers", action="store_true")
    args = parser.parse_args()

    result = generate_workpiece(args.category, np.random.default_rng(args.seed))
    obj = result.mesh.item()
    mesh = obj.data
    part_attr = mesh.attributes.get("spray_part")
    target_attr = mesh.attributes.get("spray_target")
    if part_attr is None or target_attr is None:
        raise RuntimeError("Missing generated spray face attributes")
    if part_attr.domain != "FACE" or target_attr.domain != "FACE":
        raise RuntimeError("Spray attributes must be on faces")

    vertices = np.asarray([v.co[:] for v in mesh.vertices], dtype=np.float32)
    mesh.calc_loop_triangles()
    faces = np.asarray([t.vertices[:] for t in mesh.loop_triangles], dtype=np.int32)
    face_part = np.asarray([d.value for d in part_attr.data], dtype=np.int32)
    face_target = np.asarray([d.value for d in target_attr.data], dtype=np.bool_)
    tri_part = face_part[[t.polygon_index for t in mesh.loop_triangles]]
    tri_target = face_target[[t.polygon_index for t in mesh.loop_triangles]]
    if not len(faces) or not np.isfinite(vertices).all():
        raise RuntimeError("Empty or nonfinite mesh")
    triangle_areas = 0.5 * np.linalg.norm(
        np.cross(
            vertices[faces[:, 1]] - vertices[faces[:, 0]],
            vertices[faces[:, 2]] - vertices[faces[:, 0]],
        ),
        axis=1,
    )
    if not np.isfinite(triangle_areas).all() or np.any(triangle_areas < 1e-9):
        raise RuntimeError("Mesh contains zero-area triangles")
    if set(np.unique(tri_part)) != set(result.part_legend):
        raise RuntimeError(f"Part labels differ from legend: {np.unique(tri_part)}")

    structure_priors = getattr(result, "structure_priors", None)

    args.outdir.mkdir(parents=True, exist_ok=True)
    payload = {
        "vertices": vertices,
        "faces": faces,
        # Spraybot's existing Infinigen adapter calls the per-triangle
        # semantic label `part_id`; keep the fork-native name as well.
        "part_id": tri_part,
        "spray_part": tri_part,
        "spray_target": tri_target,
    }
    if structure_priors is not None:
        payload["structure_priors"] = np.array(structure_priors, dtype=object)
    np.savez_compressed(args.outdir / "mesh.npz", **payload)
    bbox_min = vertices.min(axis=0)
    bbox_max = vertices.max(axis=0)
    summary = {
        "category_id": result.category_id,
        "seed": args.seed,
        "vertices": int(len(vertices)),
        "triangles": int(len(faces)),
        "bbox_min": bbox_min.tolist(),
        "bbox_max": bbox_max.tolist(),
        "part_legend": result.part_legend,
        "triangles_by_part": {
            name: int(np.count_nonzero(tri_part == code))
            for code, name in result.part_legend.items()
        },
        "target_triangle_fraction": float(np.mean(tri_target)),
        "target_status": "candidate_only_not_reachability_checked",
        "removed_degenerate_faces": result.removed_degenerate_faces,
        "structure_priors": structure_priors,
        "surface_area": float(triangle_areas.sum()),
    }
    if args.check_modifiers:
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        evaluated_mesh = evaluated.to_mesh()
        try:
            evaluated_part = evaluated_mesh.attributes.get("spray_part")
            evaluated_target = evaluated_mesh.attributes.get("spray_target")
            summary["evaluated_faces"] = len(evaluated_mesh.polygons)
            summary["evaluated_part_labels"] = (
                sorted({d.value for d in evaluated_part.data})
                if evaluated_part is not None else None
            )
            summary["evaluated_target_fraction"] = (
                sum(bool(d.value) for d in evaluated_target.data)
                / len(evaluated_mesh.polygons)
                if evaluated_target is not None and evaluated_mesh.polygons else None
            )
        finally:
            evaluated.to_mesh_clear()
    (args.outdir / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary))


if __name__ == "__main__":
    main()

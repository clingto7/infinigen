"""One-shot Blender worker for the local Spraybot generator UI."""

import json
import sys
from pathlib import Path

import bpy
import numpy as np

from infinigen2.util.spray import SPRAY_TARGET_REASON_NAMES


def plain(value):
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def main():
    generator, seed, output_path = sys.argv[-3], int(sys.argv[-2]), Path(sys.argv[-1])
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if generator.startswith("workpiece:"):
        from infinigen2.workpieces import generate

        result = generate(generator.removeprefix("workpiece:"), np.random.default_rng(seed))
    elif generator.startswith("spraybot:"):
        from infinigen2.objects.spraybot import generate_workpiece

        result = generate_workpiece(generator.removeprefix("spraybot:"), np.random.default_rng(seed))
    else:
        raise ValueError(f"unsupported generator: {generator}")

    obj = result.mesh.item()
    mesh = obj.data
    mesh.calc_loop_triangles()
    world = obj.matrix_world
    vertices = [list(world @ vertex.co) for vertex in mesh.vertices]
    triangles = []
    polygon_ids = []
    for triangle in mesh.loop_triangles:
        triangles.append(list(triangle.vertices))
        polygon_ids.append(int(triangle.polygon_index))

    def face_values(name, default):
        attribute = mesh.attributes.get(name)
        if attribute is None or attribute.domain != "FACE":
            return [default] * len(triangles)
        return [plain(attribute.data[index].value) for index in polygon_ids]

    payload = {
        "generator": generator,
        "seed": seed,
        "vertices": vertices,
        "triangles": triangles,
        "part_id": face_values("spray_part", -1),
        "spray_target": face_values("spray_target", False),
        "spray_target_reason": face_values("spray_target_reason", 2),
        "geometry_accessible": face_values("geometry_accessible", False),
        "max_passable_radius_m": face_values("max_passable_radius_m", 0.0),
        "part_legend": plain(getattr(result, "part_legend", {})),
        "spray_target_reason_legend": plain(SPRAY_TARGET_REASON_NAMES),
        "structure_priors": plain(getattr(result, "structure_priors", None)),
        "triangle_count": len(triangles),
        "vertex_count": len(vertices),
    }
    radii = np.asarray(payload["max_passable_radius_m"], dtype=float)
    payload["max_passable_radius_p95_m"] = float(np.percentile(radii, 95)) if len(radii) else 0.0
    payload["bbox_min_m"] = np.min(np.asarray(vertices), axis=0).tolist()
    payload["bbox_max_m"] = np.max(np.asarray(vertices), axis=0).tolist()
    output_path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    main()

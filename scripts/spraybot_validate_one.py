"""Generate and inspect one registered Infinigen Object seed.

Each invocation uses a fresh process so Blender and procfunc state cannot leak
between seeds. The saved .blend is the model artifact; two workbench PNGs are
intended for structural review rather than photorealistic presentation.
"""

import argparse
import hashlib
import importlib
import json
import os
import platform
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


def _face_attribute(mesh: bpy.types.Mesh, name: str) -> dict | None:
    attr = mesh.attributes.get(name)
    if attr is None:
        return None
    info = {"domain": attr.domain, "data_type": attr.data_type}
    if attr.domain != "FACE":
        return {**info, "error": "expected FACE"}
    counts: dict[str, int] = {}
    for datum in attr.data:
        key = str(datum.value)
        counts[key] = counts.get(key, 0) + 1
    return {**info, "counts": counts}


def _geometry_metrics(obj: bpy.types.Object, mesh: bpy.types.Mesh) -> dict:
    vertices = np.asarray([v.co[:] for v in mesh.vertices], dtype=np.float32)
    if len(vertices) == 0 or not np.isfinite(vertices).all():
        raise ValueError("mesh has no finite vertices")
    mesh.calc_loop_triangles()
    triangles = np.asarray(
        [triangle.vertices[:] for triangle in mesh.loop_triangles], dtype=np.int32
    )
    if len(triangles) == 0:
        raise ValueError("mesh has no triangles")
    world = np.asarray(obj.matrix_world, dtype=np.float64)
    world_vertices = vertices.astype(np.float64) @ world[:3, :3].T + world[:3, 3]
    lo, hi = world_vertices.min(axis=0), world_vertices.max(axis=0)
    extent = hi - lo
    if not np.isfinite(extent).all() or np.max(extent) <= 0:
        raise ValueError("mesh has invalid bounds")
    a, b, c = (world_vertices[triangles[:, i]] for i in range(3))
    areas = np.linalg.norm(np.cross(b - a, c - a), axis=1) * 0.5
    if not np.isfinite(areas).all():
        raise ValueError("mesh has nonfinite triangle areas")
    exact_hash = hashlib.sha256()
    exact_hash.update(vertices.tobytes())
    exact_hash.update(triangles.tobytes())
    normalized = np.rint((world_vertices - lo) / np.max(extent) * 1000).astype(
        np.int16
    )
    normalized_hash = hashlib.sha256()
    normalized_hash.update(normalized.tobytes())
    normalized_hash.update(triangles.tobytes())
    return {
        "vertices": int(len(vertices)),
        "triangles": int(len(triangles)),
        "bbox_min_m": lo.tolist(),
        "bbox_max_m": hi.tolist(),
        "extent_m": extent.tolist(),
        "surface_area_m2": float(areas.sum()),
        "near_zero_triangle_fraction": float(np.mean(areas < 1e-9)),
        "geometry_sha256": exact_hash.hexdigest(),
        "normalized_shape_sha256": normalized_hash.hexdigest(),
        "spray_part": _face_attribute(mesh, "spray_part"),
        "spray_target": _face_attribute(mesh, "spray_target"),
    }


def _spray_checks(mesh: bpy.types.Mesh, legend: dict[int, str] | None) -> dict:
    issues = []
    part = mesh.attributes.get("spray_part")
    target = mesh.attributes.get("spray_target")
    if part is None:
        issues.append("spray_part_missing")
    elif part.domain != "FACE" or part.data_type != "INT":
        issues.append("spray_part_must_be_int_face_attribute")
    if target is None:
        issues.append("spray_target_missing")
    elif target.domain != "FACE" or target.data_type != "BOOLEAN":
        issues.append("spray_target_must_be_boolean_face_attribute")
    if legend is None:
        issues.append("part_legend_missing")
    elif not legend or any(not isinstance(k, int) or k < 0 or not v for k, v in legend.items()):
        issues.append("part_legend_invalid")

    part_ids = None
    if part is not None and part.domain == "FACE" and part.data_type == "INT":
        part_ids = {int(d.value) for d in part.data}
        if len(part.data) != len(mesh.polygons) or any(k < 0 for k in part_ids):
            issues.append("spray_part_values_invalid")
        if legend is not None and part_ids != set(legend):
            issues.append("spray_part_legend_mismatch")

    target_faces = 0
    target_area_fraction = None
    if target is not None and target.domain == "FACE" and target.data_type == "BOOLEAN":
        if len(target.data) != len(mesh.polygons):
            issues.append("spray_target_length_mismatch")
        else:
            target_faces = sum(bool(d.value) for d in target.data)
            if target_faces == 0:
                issues.append("spray_target_empty")
            total_area = sum(face.area for face in mesh.polygons)
            if total_area > 0:
                target_area_fraction = sum(
                    face.area for face, datum in zip(mesh.polygons, target.data) if datum.value
                ) / total_area
            if target_area_fraction is None or target_area_fraction <= 0:
                issues.append("spray_target_zero_area")
    return {
        "passed": not issues,
        "issues": issues,
        "part_ids": sorted(part_ids) if part_ids is not None else None,
        "target_faces": target_faces,
        "target_area_fraction": target_area_fraction,
    }


def _render_views(obj: bpy.types.Object, output: Path, extent: list[float]) -> None:
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = 384
    scene.render.resolution_y = 384
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    obj.color = (0.47, 0.62, 0.78, 1.0)
    for other in bpy.data.objects:
        if other is not obj:
            other.hide_render = True

    bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    center = sum(corners, Vector()) / len(corners)
    span = max(extent)
    camera_data = bpy.data.cameras.new("ReviewCamera")
    camera_data.type = "ORTHO"
    camera_data.ortho_scale = span * 1.9
    camera = bpy.data.objects.new("ReviewCamera", camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    for index, direction in enumerate(((1.0, -1.0, 0.65), (-1.0, 1.0, 0.65))):
        camera.location = center + Vector(direction).normalized() * max(span * 3, 1)
        camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = str(output / f"view_{index}.png")
        bpy.ops.render.render(write_still=True)
        if not (output / f"view_{index}.png").is_file():
            raise RuntimeError(f"view_{index}.png was not rendered")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("generator", help="full dotted name from manifest.json")
    parser.add_argument("seed", type=int)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if args.generator.startswith("spraybot:"):
        from infinigen2.objects.spraybot import generate_workpiece

        result = generate_workpiece(
            args.generator.removeprefix("spraybot:"), np.random.default_rng(args.seed)
        )
    else:
        module_name, function_name = args.generator.rsplit(".", 1)
        function = getattr(importlib.import_module(module_name), function_name)
        result = function(np.random.default_rng(args.seed))
    mesh_object = getattr(result, "mesh", None)
    if mesh_object is None:
        raise TypeError("Object generator did not return a mesh field")
    obj = mesh_object.item()
    if obj.type != "MESH":
        raise TypeError(f"Object generator returned {obj.type}, expected MESH")
    obj.name = "Workpiece"
    bpy.context.view_layer.update()
    legend = getattr(result, "part_legend", None)
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    evaluated_mesh = evaluated.to_mesh()
    try:
        metrics = _geometry_metrics(obj, evaluated_mesh)
        spray_checks = _spray_checks(evaluated_mesh, legend)
    finally:
        evaluated.to_mesh_clear()
    _render_views(obj, args.output, metrics["extent_m"])
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output / "model.blend"), compress=True)
    if not (args.output / "model.blend").is_file():
        raise RuntimeError("model.blend was not saved")
    env = {
        "blender_version": bpy.app.version_string,
        "python_executable": sys.executable,
        "python_version": sys.version,
        "numpy_version": np.__version__,
        "platform": platform.platform(),
    }
    if os.environ.get("SPRAYBOT_GIT_COMMIT"):
        env["git_commit"] = os.environ["SPRAYBOT_GIT_COMMIT"]
        env["git_branch"] = os.environ.get("SPRAYBOT_GIT_BRANCH", "")
        env["git_dirty"] = os.environ.get("SPRAYBOT_GIT_DIRTY", "")
    status = {
        "generator": args.generator,
        "seed": args.seed,
        "elapsed_sec": round(time.monotonic() - started, 3),
        "metrics": metrics,
        "part_legend": legend,
        "spray_checks": spray_checks,
        "env": env,
        "artifacts": ["model.blend", "view_0.png", "view_1.png"],
    }
    (args.output / "result.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"generator": args.generator, "seed": args.seed, "ok": True}))


if __name__ == "__main__":
    main()

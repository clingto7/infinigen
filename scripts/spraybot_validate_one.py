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
from PIL import Image, ImageDraw
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


def _visibility_stats(mesh: bpy.types.Mesh) -> dict | None:
    attr = mesh.attributes.get("spray_visibility")
    if attr is None or attr.domain != "FACE" or attr.data_type != "FLOAT":
        return None
    values = np.asarray([d.value for d in attr.data], dtype=np.float64)
    return {
        "mean": float(values.mean()),
        "min": float(values.min()),
        "frac_below_0_25": float(np.mean(values < 0.25)),
    }


def _accessibility_metrics(mesh: bpy.types.Mesh) -> dict:
    accessible = mesh.attributes.get("geometry_accessible")
    if accessible is None:
        return {"geometry_accessible": None}
    flags = np.asarray([item.value for item in accessible.data], dtype=bool)
    if len(flags) == 0:
        return {"geometry_accessible": None}
    return {
        "geometry_accessible": {
            "accessible_faces": int(flags.sum()),
            "inaccessible_faces": int((~flags).sum()),
            "fraction_accessible": float(flags.mean()),
        },
    }


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
        "spray_target_reason": _face_attribute(mesh, "spray_target_reason"),
        "spray_visibility": _visibility_stats(mesh),
        **_accessibility_metrics(mesh),
    }


def _spray_checks(mesh: bpy.types.Mesh, legend: dict[int, str] | None) -> dict:
    issues = []
    part = mesh.attributes.get("spray_part")
    target = mesh.attributes.get("spray_target")
    reason = mesh.attributes.get("spray_target_reason")
    if part is None:
        issues.append("spray_part_missing")
    elif part.domain != "FACE" or part.data_type != "INT":
        issues.append("spray_part_must_be_int_face_attribute")
    if target is None:
        issues.append("spray_target_missing")
    elif target.domain != "FACE" or target.data_type != "BOOLEAN":
        issues.append("spray_target_must_be_boolean_face_attribute")
    if reason is None:
        issues.append("spray_target_reason_missing")
    elif reason.domain != "FACE" or reason.data_type != "INT":
        issues.append("spray_target_reason_must_be_int_face_attribute")
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
    if reason is not None and reason.domain == "FACE" and reason.data_type == "INT":
        if len(reason.data) != len(mesh.polygons):
            issues.append("spray_target_reason_length_mismatch")
        else:
            codes = [int(item.value) for item in reason.data]
            if any(code not in {0, 1, 2, 3} for code in codes):
                issues.append("spray_target_reason_code_invalid")
            if target is not None and len(target.data) == len(reason.data):
                if any(bool(t.value) != (code == 0) for t, code in zip(target.data, codes)):
                    issues.append("spray_target_reason_target_mismatch")
    accessible = mesh.attributes.get("geometry_accessible")
    if accessible is None:
        issues.append("geometry_accessible_missing")
    elif accessible.domain != "FACE" or accessible.data_type != "BOOLEAN":
        issues.append("geometry_accessible_must_be_boolean_face_attribute")
    elif len(accessible.data) != len(mesh.polygons):
        issues.append("geometry_accessible_length_mismatch")
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
    scene.render.resolution_x = 448
    scene.render.resolution_y = 448
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.film_transparent = False
    scene.display.shading.light = "STUDIO"
    scene.display.shading.color_type = "OBJECT"
    # Use a neutral viewport background and an explicit floor.  The old black
    # background hid small gaps under seats, ladders, and cabinet doors and
    # made correctly touching parts look detached.
    scene.display.shading.background_type = "VIEWPORT"
    scene.display.shading.background_color = (0.12, 0.14, 0.18)
    scene.display.shading.show_shadows = True
    scene.display.shading.shadow_intensity = 0.75
    scene.display.shading.show_cavity = True
    scene.display.shading.cavity_type = "BOTH"
    scene.display.shading.cavity_ridge_factor = 1.35
    scene.display.shading.cavity_valley_factor = 1.15
    obj.color = (0.47, 0.62, 0.78, 1.0)
    for other in bpy.data.objects:
        if other is not obj:
            other.hide_render = True

    bpy.context.view_layer.update()
    corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    center = sum(corners, Vector()) / len(corners)
    span = max(extent)
    # A temporary floor gives the review image a contact shadow and makes
    # unsupported or floating geometry immediately visible.  It is removed
    # before the .blend artifact is saved.
    floor_z = min(float(v[2]) for v in corners)
    bpy.ops.mesh.primitive_plane_add(
        size=max(span * 3.0, 3.0), location=(0.0, 0.0, floor_z - 0.002)
    )
    floor = bpy.context.object
    floor.name = "_ReviewFloor"
    floor.color = (0.16, 0.18, 0.22, 1.0)
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

    _render_face_fields(obj, output, center, span, camera)

    bpy.data.objects.remove(floor, do_unlink=True)


def _render_face_fields(
    obj: bpy.types.Object,
    output: Path,
    center: Vector,
    span: float,
    camera: bpy.types.Object,
) -> None:
    mesh = obj.data
    scene = bpy.context.scene
    scene.display.shading.color_type = "MATERIAL"
    original_indices = [poly.material_index for poly in mesh.polygons]
    original_materials = list(mesh.materials)
    palettes = {
        "spray_target": [(0.24, 0.28, 0.32, 1), (0.93, 0.25, 0.15, 1)],
        "spray_target_reason": [
            (0.20, 0.72, 0.55, 1), (0.94, 0.74, 0.28, 1),
            (0.67, 0.42, 0.85, 1), (0.30, 0.61, 0.91, 1),
        ],
        "geometry_accessible": [(0.91, 0.30, 0.17, 1), (0.16, 0.72, 0.45, 1)],
    }
    radius_palette = [
        (0.16, 0.23, 0.55, 1), (0.16, 0.43, 0.72, 1),
        (0.12, 0.63, 0.69, 1), (0.22, 0.75, 0.48, 1),
        (0.61, 0.80, 0.25, 1), (0.94, 0.72, 0.18, 1),
        (0.94, 0.42, 0.13, 1), (0.70, 0.16, 0.20, 1),
    ]
    specs = [
        ("spray_target", "spray_target", "False", "True", None),
        ("spray_target_reason", "spray_target_reason", "target / material / component / cavity", "see compatibility contract", None),
        ("geometry_accessible", "geometry_accessible", "No", "Yes", None),
    ]
    try:
        for attr_name, filename, _, _, scale_max in specs:
            attr = mesh.attributes[attr_name]
            values = [item.value for item in attr.data]
            palette = palettes.get(attr_name, radius_palette)
            first_material = len(mesh.materials)
            for index, color in enumerate(palette):
                material = bpy.data.materials.new(f"_Review_{attr_name}_{index}")
                material.diffuse_color = color
                mesh.materials.append(material)
            for polygon, value in zip(mesh.polygons, values):
                if scale_max is None:
                    palette_index = int(bool(value)) if attr_name == "spray_target" else int(value)
                else:
                    palette_index = min(len(palette) - 1, int(float(value) / scale_max * len(palette)))
                polygon.material_index = first_material + palette_index
            for view, direction in enumerate(((1.0, -1.0, 0.65), (-1.0, 1.0, 0.65))):
                camera.location = center + Vector(direction).normalized() * max(span * 3, 1)
                camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
                scene.render.filepath = str(output / f"{filename}_{view}.png")
                bpy.ops.render.render(write_still=True)
    finally:
        while mesh.materials:
            mesh.materials.pop(index=len(mesh.materials) - 1)
        for material in original_materials:
            mesh.materials.append(material)
        for polygon, index in zip(mesh.polygons, original_indices):
            polygon.material_index = index
        for material in list(bpy.data.materials):
            if material.name.startswith("_Review_"):
                bpy.data.materials.remove(material)
        scene.display.shading.color_type = "OBJECT"

    width, height, legend_h = 448, 448, 62
    sheet = Image.new("RGB", (width * 2, (height + legend_h) * len(specs)), "#f4f5f7")
    draw = ImageDraw.Draw(sheet)
    for row, (attr_name, filename, low_text, high_text, scale_max) in enumerate(specs):
        for view in range(2):
            with Image.open(output / f"{filename}_{view}.png") as image:
                sheet.paste(image.convert("RGB"), (view * width, row * (height + legend_h)))
        y = row * (height + legend_h) + height + 5
        if scale_max is None:
            palette = palettes[attr_name]
            draw.text((10, y), f"{attr_name}:", fill="#172238")
            for x, color, label in ((170, palette[0], low_text), (300, palette[1], high_text)):
                draw.rectangle((x, y, x + 20, y + 18), fill=tuple(int(channel * 255) for channel in color[:3]))
                draw.text((x + 26, y), label, fill="#172238")
        else:
            draw.text((10, y), f"{attr_name}: min {radius_values.min():.4f} m", fill="#172238")
            x0, bar_w = 270, 145
            for index, color in enumerate(radius_palette):
                left = x0 + index * bar_w // len(radius_palette)
                right = x0 + (index + 1) * bar_w // len(radius_palette)
                draw.rectangle((left, y, right, y + 18), fill=tuple(int(channel * 255) for channel in color[:3]))
            draw.text((x0 + bar_w + 5, y), f"{radius_max:.4f} m (p95)", fill="#172238")
    sheet.save(output / "face_fields.png")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("generator", help="full dotted name from manifest.json")
    parser.add_argument("seed", type=int)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if args.generator.startswith("workpiece:"):
        from infinigen2.workpieces import generate

        result = generate(
            args.generator.removeprefix("workpiece:"), np.random.default_rng(args.seed)
        )
    elif args.generator.startswith("spraybot:"):
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
        # Validate semantic attributes on the source mesh.  The generated
        # workpiece is exported from this mesh; upstream subdivision/mirror
        # modifiers may retain their pre-remap local attributes on the
        # evaluated copy, which would compare unrelated label spaces against
        # the shared legend.
        spray_checks = _spray_checks(obj.data, legend)
    finally:
        evaluated.to_mesh_clear()
    metrics.update(_accessibility_metrics(obj.data))
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
        "structure_priors": getattr(result, "structure_priors", None),
        "spray_checks": spray_checks,
        "env": env,
        "artifacts": ["model.blend", "view_0.png", "view_1.png", "face_fields.png"],
    }
    (args.output / "result.json").write_text(
        json.dumps(status, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"generator": args.generator, "seed": args.seed, "ok": True}))


if __name__ == "__main__":
    main()

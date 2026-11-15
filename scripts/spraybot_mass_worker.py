"""Internal Blender worker for :mod:`spraybot_mass_generate`."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import bpy
import numpy as np

from spraybot_parametric_readiness import load as load_parametric_certifications

CERTIFIED_PARAMETRIC_GENERATORS = load_parametric_certifications()
def generate(generator: str, seed: int):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rng = np.random.default_rng(seed)
    if generator.startswith("workpiece:"):
        from infinigen2.workpieces import generate as generate_workpiece

        return generate_workpiece(generator.removeprefix("workpiece:"), rng, record_parameters=True)
    if generator.startswith("spraybot:"):
        from infinigen2.objects.spraybot import generate_workpiece

        return generate_workpiece(generator.removeprefix("spraybot:"), rng)
    raise ValueError(f"Unsupported generator: {generator}")


def dataset_category(category_id: str) -> str:
    return "".join(part.title() for part in category_id.split("_"))


def existing_seeds(batch: Path, category_id: str) -> set[int]:
    existing = set()
    for metadata_path in batch.glob("episode_*/metadata.json"):
        try:
            row = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if row.get("category_id") == category_id:
            obj_name = row.get("model_file")
            if obj_name and (metadata_path.parent / obj_name).is_file():
                if not all((metadata_path.parent / name).is_file() for name in ("structure.json", "face_attributes.npz")):
                    raise ValueError(
                        f"Legacy mesh-only episode: {metadata_path.parent}. "
                        "Use spraybot_recover_priors.py to create a verified overlay."
                    )
                existing.add(int(row["seed"]))
    return existing


def write_episode(
    batch: Path,
    category_id: str,
    generator: str,
    seed: int,
    existing: set[int],
) -> None:
    category = dataset_category(category_id)
    if seed in existing:
        return

    from infinigen2.workpieces.parametric_capture import ParametricCapture

    with ParametricCapture() as capture:
        result = generate(generator, seed)
    obj = result.mesh.item()
    mesh = obj.data
    mesh.calc_loop_triangles()
    world = obj.matrix_world
    vertices = [world @ vertex.co for vertex in mesh.vertices]
    triangles = [triangle.vertices[:] for triangle in mesh.loop_triangles]

    case = f"{category}_{seed:05d}"
    now = datetime.now(ZoneInfo("Asia/Shanghai"))
    episode = "episode_" + now.strftime("%Y%m%d_%H%M_%S_%f")
    partial = batch / f".partial_{seed:08d}"
    partial.mkdir(parents=True, exist_ok=True)
    obj_name = f"{case}.obj"
    obj_path = partial / obj_name
    with obj_path.open("w", encoding="ascii", newline="\n") as file:
        for vertex in vertices:
            file.write(
                f"v {vertex.x * 1000.0:.6f} {vertex.y * 1000.0:.6f} "
                f"{vertex.z * 1000.0:.6f}\n"
            )
        for face in triangles:
            file.write(f"f {face[0] + 1} {face[1] + 1} {face[2] + 1}\n")
        file.flush()
        os.fsync(file.fileno())

    metadata = {
        "category": category,
        "category_id": category_id,
        "generator": generator,
        "seed": seed,
        "case": case,
        "episode": episode,
        "generated_at": now.isoformat(timespec="microseconds"),
        "vertices": len(vertices),
        "faces": len(triangles),
        "model_file": obj_name,
        "obj_bytes": obj_path.stat().st_size,
        "coordinate_unit": "mm",
    }
    # OBJ cannot retain per-face data or the generation-time construction record.
    # Keep these in sibling files with triangle order identical to the OBJ.
    polygon_indices = [triangle.polygon_index for triangle in mesh.loop_triangles]
    face_data = {}
    for name in ("spray_part", "spray_target", "spray_target_reason", "part_id", "part_type",
                 "geometry_accessible", "max_passable_radius_m"):
        attr = mesh.attributes.get(name)
        if attr is not None:
            if attr.domain != "FACE":
                raise ValueError(f"Expected face attribute: {name}")
            face_data[name] = np.array([value.value for value in attr.data])[polygon_indices]
    for name in ("spray_part", "spray_target", "spray_target_reason"):
        if name not in face_data:
            raise ValueError(f"Missing required face data: {name}")
    np.savez_compressed(partial / "face_attributes.npz", **face_data)
    priors = {
        "schema": "spraybot.generation-data.v1",
        "structure_priors": result.structure_priors,
        "part_legend": result.part_legend,
        "prior_coordinate_unit": "m",
        "obj_coordinate_unit": "mm",
        "object_to_obj_mm": (np.diag([1000., 1000., 1000., 1.]) @ np.array(world)).tolist(),
    }
    (partial / "structure.json").write_text(json.dumps(priors, allow_nan=False) + "\n", encoding="utf-8")
    metadata["face_attributes_file"] = "face_attributes.npz"
    metadata["structure_file"] = "structure.json"
    if capture.native_surface_sources:
        native_name = 'parametric.native-source.json'
        native_owner = mesh.attributes.get('parametric_native_source')
        native_face = mesh.attributes.get('parametric_native_face')
        native_uv = mesh.attributes.get('parametric_native_uv')
        if (native_owner is None or native_owner.domain != 'FACE'
            or native_face is None or native_face.domain != 'FACE'
            or native_uv is None or native_uv.domain != 'POINT'):
            raise ValueError('native surface source addresses were lost')
        (partial / native_name).write_text(json.dumps({
            'schema': 'spraybot.native-source.v1', 'unit': 'm',
            'sources': capture.native_surface_sources,
            'final_triangle_source_ids': [int(native_owner.data[i].value) for i in polygon_indices],
            'final_triangle_source_face_ids': [int(native_face.data[i].value) for i in polygon_indices],
            'final_vertex_uv': [[float(x) for x in data.vector[:2]] for data in native_uv.data],
        }, allow_nan=False, separators=(',', ':')) + '\n', encoding='utf-8')
        metadata['parametric_native_source_file'] = native_name
    if capture.solid_operations or capture.bevel_sources:
        source_name = "parametric.source.json"
        source_attr = mesh.attributes.get('parametric_solid_source')
        face_attr = mesh.attributes.get('parametric_solid_face')
        source_rows = ([int(source_attr.data[index].value) for index in polygon_indices]
                       if source_attr is not None and source_attr.domain == 'FACE' else [])
        face_rows = ([int(face_attr.data[index].value) for index in polygon_indices]
                     if face_attr is not None and face_attr.domain == 'FACE' else [])
        bevel_attr = mesh.attributes.get('parametric_bevel_source_face')
        bevel_rows = ([int(bevel_attr.data[index].value) for index in polygon_indices]
                      if bevel_attr is not None and bevel_attr.domain == 'FACE' else [])
        source_counts = {operation['id']: operation['source_face_count']
                         for operation in capture.solid_operations
                         if operation['operation'] == 'source'}
        recovered_lineage = []
        if (capture.solid_operations and len(source_rows) == len(triangles)
                and len(face_rows) == len(triangles)):
            from spraybot_parametric_csg import recover_missing_lineage
            scale = float((result.structure_priors or {}).get('post_build_uniform_scale', 1))
            recovered_lineage = recover_missing_lineage(
                capture.solid_operations, source_rows, face_rows,
                np.asarray(vertices, dtype=float), np.asarray(triangles, dtype=int), scale,
            )
        invalid_lineage = [] if not capture.solid_operations else (
            list(range(len(triangles))) if len(source_rows) != len(triangles)
            or len(face_rows) != len(triangles) else [
                index for index, (source, face) in enumerate(zip(source_rows, face_rows))
                if source_counts.get(source, 0) < face or face < 1
            ]
        )
        (partial / source_name).write_text(json.dumps({
            "schema": "spraybot.parametric-source.v1",
            "unit": "m",
            "status": "construction_only",
            "operations": capture.solid_operations,
            "bevel_sources": capture.bevel_sources,
            "final_triangle_bevel_source_face_ids": bevel_rows,
            "final_triangle_source_ids": source_rows,
            "final_triangle_source_face_ids": face_rows,
            "recovered_lineage_triangle_ids": recovered_lineage,
            "invalid_lineage_triangle_ids": invalid_lineage,
        }, allow_nan=False, separators=(",", ":")) + "\n", encoding="utf-8")
        metadata["parametric_source_file"] = source_name
    certification = CERTIFIED_PARAMETRIC_GENERATORS.get(generator)
    ready = certification is not None
    try:
        parametric = capture.export(result.mesh)
    except ValueError as error:
        if ready:
            raise RuntimeError(f"Certified parametric interface failed: {generator}: {error}") from error
        parametric = None
        if capture.native_surface_sources:
            try:
                from spraybot_parametric_native import build as build_native
                parametric = build_native(partial, metadata)
            except ValueError as native_error:
                metadata["parametric_description_status"] = "incomplete"
                metadata["parametric_incomplete_reason"] = f"{error}; native: {native_error}"
        elif capture.solid_operations:
            try:
                from spraybot_parametric_csg import build as build_csg
                parametric = build_csg(partial, metadata)
            except ValueError as csg_error:
                metadata["parametric_description_status"] = "incomplete"
                metadata["parametric_incomplete_reason"] = f"{error}; CSG: {csg_error}"
                parametric = None
        else:
            metadata["parametric_description_status"] = "incomplete"
            metadata["parametric_incomplete_reason"] = str(error)
    if parametric is not None:
        if generator == 'workpiece:infinigen_chair':
            from spraybot_parametric_native_chair import compact
            parametric = compact(parametric)
        if ready and parametric["schema"] != certification["parametric_schema"]:
            raise RuntimeError(
                f"Certified schema changed for {generator}: {parametric['schema']}"
            )
        parametric_name = "parametric.json" if ready else "parametric.candidate.json"
        if not ready:
            parametric["schema"] = parametric["schema"].replace(
                "spraybot.parametric.", "spraybot.parametric-candidate.", 1
            )
        parametric["source"] = {"category_id": category_id, "seed": seed}
        (partial / parametric_name).write_text(
            json.dumps(parametric, allow_nan=False, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        metadata["parametric_description_status"] = "ready" if ready else "candidate"
        metadata["parametric_file" if ready else "parametric_candidate_file"] = parametric_name
    (partial / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    destination = batch / episode
    os.rename(partial, destination)
    existing.add(seed)


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit(
            "usage: spraybot_mass_worker.py DATASET_ROOT COUNT START_SEED "
            "WORKER_ID WORKER_COUNT"
        )
    dataset_root = Path(sys.argv[1])
    count, start_seed, worker_id, worker_count = map(int, sys.argv[2:])
    manifest_path = dataset_root.parent / "production_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = []
    processed = 0
    for category_index, item in enumerate(manifest["categories"]):
        if category_index % worker_count != worker_id:
            continue
        category_id = item["category_id"]
        batch = dataset_root / item["dataset_category"] / item["batch_directory"]
        batch.mkdir(parents=True, exist_ok=True)
        done_seeds = existing_seeds(batch, category_id)
        for offset in range(count):
            seed = start_seed + offset
            processed += 1
            try:
                write_episode(batch, category_id, item["generator"], seed, done_seeds)
            except Exception as error:
                failures.append(
                    {
                        "category_id": category_id,
                        "seed": seed,
                        "error": f"{type(error).__name__}: {error}",
                    }
                )
            if processed % 100 == 0:
                print(
                    f"worker={worker_id} processed={processed} failures={len(failures)}",
                    flush=True,
                )
    failure_path = dataset_root.parent / f"worker-{worker_id:02d}-failures.json"
    failure_path.write_text(json.dumps(failures, indent=2) + "\n", encoding="utf-8")
    print(
        f"worker={worker_id} done processed={processed} failures={len(failures)}",
        flush=True,
    )
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

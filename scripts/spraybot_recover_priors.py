"""Recover generation data into a separate overlay, verifying every original OBJ.

Run using the original Blender environment. Never overwrites original episodes.
The 20 newer categories use the frozen production source; native categories use
Spraybot's original factories/seeds, and Chair uses its retained NPZ cache.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

import bpy  # load before bmesh
import bmesh
import numpy as np


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


RECORD = load_module(
    "spraybot_construction_record",
    Path(__file__).resolve().parents[1] / "src/infinigen2/util/construction_record.py",
)


def plain(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(v) for v in value]
    return value


def obj_bytes(vertices_mm, faces):
    return ("".join(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n" for v in vertices_mm)
            + "".join(f"f {int(f[0])+1} {int(f[1])+1} {int(f[2])+1}\n" for f in faces)).encode("ascii")


def native_factory(category, seed, spraybot):
    sys.path[:0] = [str(spraybot / "datagen" / category.lower()),
                    str(spraybot / "datagen/factories_ref")]
    from infinigen.core.util import blender as butil
    butil.clear_scene()
    if category == "OpusChair":
        from opus_chair import OpusChairFactory
        factory = OpusChairFactory(seed)
    else:
        from car_bumper import CarBumperFactory
        factory = CarBumperFactory(seed)
    obj = factory.create_asset()
    # Match the original bmesh triangulation and indexing exactly.
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bm.verts.ensure_lookup_table()
        indices = {v: i for i, v in enumerate(bm.verts)}
        vertices = np.array([v.co[:] for v in bm.verts], dtype=float)
        faces = np.array([[indices[v] for v in f.verts] for f in bm.faces], dtype=np.int32)
        layer = bm.faces.layers.int.get("part_type")
        if layer is None:
            layer = bm.faces.layers.float.get("part_type")
        if layer is None:
            raise ValueError("Native factory lost part_type")
        attributes = {"part_type": np.array([f[layer] for f in bm.faces], dtype=np.int32)}
    finally:
        bm.free()
    return vertices * 1000.0, faces, attributes, {
        "representation": "native_factory_record", "coordinate_unit": "m",
        "factory_seed": seed, "structure_priors": plain(factory._rec),
        "prior_to_obj_mm": (np.diag([1000.0, 1000.0, 1000.0, 1.0])
                            @ np.linalg.inv(np.asarray(obj.matrix_world))).tolist(),
    }


def cached_chair(path):
    # Only the user's own locally generated cache is loaded with allow_pickle.
    with np.load(path, allow_pickle=True) as data:
        vertices_mm = np.asarray(data["vertices"], dtype=float) * 1000.0
        center = (vertices_mm.min(0) + vertices_mm.max(0)) * 0.5
        vertices_mm = (vertices_mm - center).astype(np.float32).astype(float)
        faces = data["faces"].copy()
        attrs = {name: data[name].copy() for name in ("part_id", "part_type")}
        cls = plain(data["centerlines"].item())
        meta = plain(data["back_meta"].item())
    transform = np.diag([1000.0, 1000.0, 1000.0, 1.0])
    transform[:3, 3] = -center
    return vertices_mm, faces, attrs, {
        "representation": "native_chair_priors", "coordinate_unit": "m",
        "structure_priors": {"centerlines": cls, "back_meta": meta},
        "centerline_representation": "ordered_sampled_polyline_not_bezier_control_points",
        "prior_to_obj_mm": transform.tolist(),
        "source_npz_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def production(category_id, seed):
    from infinigen2.workpieces.common import REGISTRY, BuiltWorkpiece, _remove_degenerate_faces
    from infinigen2.util import spray

    bpy.ops.wm.read_factory_settings(use_empty=True)
    category = REGISTRY[category_id]
    if category.scale_range is not None:
        raise ValueError("Published 20-category recovery expects no post-build scaling")
    with RECORD.ConstructionRecorder() as recorder:
        built = category.build(np.random.default_rng(seed))
    mesh_object = built.mesh if isinstance(built, BuiltWorkpiece) else built
    if category.remove_degenerate:
        _remove_degenerate_faces(mesh_object)
    spray.ensure_spray_target_reason(mesh_object)
    obj = mesh_object.item()
    mesh = obj.data
    mesh.calc_loop_triangles()
    vertices = np.array([obj.matrix_world @ v.co for v in mesh.vertices], dtype=float)
    faces = np.array([t.vertices[:] for t in mesh.loop_triangles], dtype=np.int32)
    polygon_indices = np.array([t.polygon_index for t in mesh.loop_triangles])
    attrs = {}
    for name in ("spray_part", "spray_target", "spray_target_reason", "part_id", "part_type"):
        attribute = mesh.attributes.get(name)
        if attribute is not None:
            if attribute.domain != "FACE":
                raise ValueError(f"Unexpected attribute domain: {name}")
            attrs[name] = np.array([v.value for v in attribute.data])[polygon_indices]
    for name in ("spray_part", "spray_target", "spray_target_reason"):
        if name not in attrs:
            raise ValueError(f"Missing face attribute: {name}")
    if not np.array_equal(attrs["spray_target"], attrs["spray_target_reason"] == 0):
        raise ValueError("Target and reason disagree")
    return vertices * 1000.0, faces, attrs, {
        "representation": "executed_source_parameters",
        "construction_record": recorder.payload(),
        "part_legend": spray.present_part_legend(mesh_object),
        "object_to_obj_mm": (np.diag([1000., 1000., 1000., 1.]) @ np.array(obj.matrix_world)).tolist(),
        "geometry_accessibility": "not_recomputed_in_parameter_recovery",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production", type=Path, required=True)
    parser.add_argument("--spraybot", type=Path, required=True)
    parser.add_argument("--generator-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=1)
    args = parser.parse_args()
    if not 0 <= args.shard < args.shards:
        parser.error("Invalid shard")
    sys.path.insert(0, str(args.generator_root / "src"))
    category = args.category
    manifest = json.loads((args.production / "production_manifest.json").read_text())
    item = next((x for x in manifest["categories"] if x["dataset_category"] == category), None)
    if item:
        batch = args.production / "SPS_V2.0" / category / item["batch_directory"]
        # Import the registry only after selecting the frozen source root.
        import infinigen2.workpieces
    else:
        batch = args.spraybot / "SPS_V2.0" / category / f"0901__{category}_LDB01_8098"
    rows = sorted((json.loads(p.read_text()) for p in batch.glob("episode_*/metadata.json")), key=lambda x: x["seed"])
    if args.limit:
        rows = rows[:args.limit]
    rows = rows[args.shard::args.shards]
    cache = {}
    if category == "Chair":
        for p in (args.spraybot / "datagen/bulk8098/_chair_npz").rglob("Chair_*.npz"):
            seed = int(p.stem.split("_")[-1])
            if seed in cache:
                raise ValueError(f"Duplicate cached Chair seed: {seed}")
            cache[seed] = p
    out = args.output / "SPS_V2.0" / category / batch.name
    out.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    successes = 0
    failures = []
    for row in rows:
        ep = row["episode"]
        dest = out / ep
        source_obj = batch / ep / row.get("model_file", f"{row['case']}.obj")
        original_sha = hashlib.sha256(source_obj.read_bytes()).hexdigest()
        if (dest / "structure.json").is_file() and (dest / "face_attributes.npz").is_file():
            existing = json.loads((dest / "structure.json").read_text())
            if existing.get("obj_sha256") == original_sha and existing.get("schema") == "spraybot.prior-overlay.v1":
                successes += 1
                continue
            raise ValueError(f"Existing overlay belongs to different geometry: {dest}")
        try:
            if item:
                V, F, attrs, priors = production(item["category_id"], row["seed"])
            elif category == "Chair":
                V, F, attrs, priors = cached_chair(cache[row["seed"]])
            else:
                V, F, attrs, priors = native_factory(category, row["seed"], args.spraybot)
            replay_sha = hashlib.sha256(obj_bytes(V, F)).hexdigest()
            if replay_sha != original_sha:
                raise ValueError(f"Replayed OBJ SHA mismatch: {replay_sha} != {original_sha}")
            if any(len(a) != len(F) for a in attrs.values()):
                raise ValueError("Face attribute length mismatch")
            if not np.isfinite(V).all() or not len(F):
                raise ValueError("Invalid mesh")
            record = {
                "schema": "spraybot.prior-overlay.v1", "category": category,
                "seed": row["seed"], "episode": ep, "case": row["case"],
                "obj_sha256": original_sha, "mesh_verification": "byte_identical_replay",
                "obj_coordinate_unit": "mm", "faces": len(F), "vertices": len(V),
                "face_attributes": "face_attributes.npz", **priors,
            }
            temp = out / (".partial_" + ep)
            temp.mkdir(exist_ok=True)
            np.savez_compressed(temp / "face_attributes.npz", **attrs)
            (temp / "structure.json").write_text(json.dumps(plain(record), separators=(",", ":"), allow_nan=False) + "\n")
            os.rename(temp, dest)
            successes += 1
        except Exception as error:
            failures.append({"seed": row["seed"], "episode": ep, "error": str(error)})
            print(f"FAIL {category} {row['seed']}: {error}", flush=True)
        if (successes + len(failures)) % 25 == 0:
            print(f"PROGRESS {category} shard={args.shard} ok={successes} failures={len(failures)} elapsed={time.monotonic()-started:.1f}s", flush=True)
    summary = {"category": category, "shard": args.shard, "expected": len(rows),
               "verified": successes, "failures": failures,
               "elapsed_s": time.monotonic()-started}
    (out / f"recovery-{args.shard}.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary), flush=True)
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

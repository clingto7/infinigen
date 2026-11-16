"""Pair the three established SprayBot planners with Infinigen review episodes.

The original planners remain in SprayBot. This adapter uses the factory priors
saved with each Infinigen interface seed, validates the path against that exact
model, and writes a model-hash-bound PaintDS and Web trajectory artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
from types import SimpleNamespace

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial import cKDTree
import trimesh

from spraybot_trajectory.paintds import write_paintds


KINDS = ("infinigen_chair", "opus_chair", "car_bumper", "armchair")


def _chair_case(model: dict, chair_npz: Path) -> Path:
    """Recover the source Chair labels from this exact reviewed mesh and priors."""
    priors = model["structure_priors"]
    faces = np.asarray(model["triangles"], dtype=np.int32)
    vertices = np.asarray(model["vertices"], dtype=float)
    tags = np.full(len(faces), -1, dtype=np.int32)
    types = np.full(len(faces), -1, dtype=np.int32)
    constructors = {"make_seat": 0, "make_legs": 1, "make_backs": 2,
                    "make_leg_decors": 3, "make_arms": 4, "make_back_decors": 5}
    parts = []
    for part in model["parametric"]["parts"]:
        recipe = part.get("source_recipe", "")
        constructor = (recipe.get("constructor") if isinstance(recipe, dict)
                       else (match.group(1) if (match := re.search(r"'constructor': '([^']+)'", recipe)) else None))
        if constructor not in constructors:
            raise ValueError(f"missing source constructor for {part['id']}")
        ids = np.unique([index for surface in part["surfaces"]
                         for index in surface["mesh_mapping"]["construction_triangle_ids"]])
        if len(ids) == 0:
            raise ValueError(f"empty source part: {part['id']}")
        parts.append((part, ids, constructor))
    centerlines = {int(key): np.asarray(value, dtype=float)
                   for key, value in priors["centerlines"].items()}
    keys = list(centerlines)
    trees = [cKDTree(vertices[np.unique(faces[ids])]) for _, ids, _ in parts]
    costs = np.asarray([[np.median(tree.query(centerlines[key])[0]) for tree in trees]
                        for key in keys])
    rows, columns = linear_sum_assignment(costs)
    if np.any(costs[rows, columns] > 0.05):
        raise ValueError("source centerlines do not match reviewed Chair parts")
    matched = {int(column): keys[row] for row, column in zip(rows, columns)}
    for index, (part, ids, constructor) in enumerate(parts):
        tag = matched.get(index, 10000 + index)
        if np.any(tags[ids] >= 0):
            raise ValueError(f"overlapping or empty source part: {part['id']}")
        tags[ids] = tag
        types[ids] = constructors[constructor]
    if np.any(tags < 0):
        raise ValueError("source part mapping does not cover the reviewed Chair mesh")
    if not set(centerlines) <= set(tags):
        raise ValueError("centerlines refer to missing source parts")
    chair_npz.mkdir(parents=True, exist_ok=True)
    source = chair_npz / f"PairedChair_{priors['factory_seed']}_{model['seed']}.npz"
    np.savez_compressed(source, vertices=np.asarray(model["vertices"], dtype=np.float32),
                        faces=faces, part_id=tags, part_type=types,
                        centerlines=np.array(centerlines, dtype=object),
                        back_meta=np.array({key: priors[key] for key in
                                            ("back_type", "back_profile", "back_vertical_cuts", "back_height")},
                                           dtype=object))
    return source


def _source_strokes(kind: str, model: dict, spraybot: Path, chair_npz: Path):
    priors = model["structure_priors"]
    sys.path.insert(0, str(spraybot))
    if kind == "armchair":
        return _armchair_strokes(model, spraybot)
    if kind == "infinigen_chair":
        from datagen.chair_spray.chair_spray import generate_strokes
        source = _chair_case(model, chair_npz)
        with np.load(source, allow_pickle=True) as data:
            source_vertices = np.asarray(data["vertices"])
        center_mm = (source_vertices.min(axis=0) + source_vertices.max(axis=0)) * 500
        _, strokes = generate_strokes(source)
        return strokes, center_mm, spraybot / "datagen/chair_spray/chair_spray.py"
    if kind == "opus_chair":
        from datagen.opuschair.opus_spray import generate_strokes
        record = json.loads(json.dumps(priors))
        square = record["seat"]["shape"] == "square"
        if square:
            # The source factory scales a unit cube by r, making its half-width r/2;
            # the source planner treats r as the half-width. Match the saved model.
            record["seat"]["r"] *= 0.5
        strokes = generate_strokes(record)
        if square:
            top_shift = priors["seat"]["t"] * 250  # source cube top = -t/4, mm
            for stroke in strokes:
                if stroke["reason"] == "seat_top":
                    for key in ("surface_points", "nozzle_points"):
                        points = np.asarray(stroke[key], dtype=float)
                        points[:, 2] -= top_shift
                        stroke[key] = points.tolist()
        return strokes, np.zeros(3), spraybot / "datagen/opuschair/opus_spray.py"
    from datagen.carbumper.bumper_spray import generate_strokes
    return generate_strokes(priors), np.zeros(3), spraybot / "datagen/carbumper/bumper_spray.py"


def _armchair_strokes(model: dict, spraybot: Path):
    """Map Armchair's generated parts to the source Chair's region planners."""
    from datagen.chair_spray.chair_spray import (
        generate_seat_serpentine, generate_back_strokes, generate_edge_strokes,
        generate_arm_strokes, generate_leg_strokes, shrink_nozzles,
    )

    vertices = np.asarray(model["vertices"], dtype=float) * 1000
    faces = np.asarray(model["triangles"], dtype=int)
    types = np.full(len(faces), -1, dtype=int)
    tags = np.full(len(faces), -1, dtype=int)
    centerlines = {}
    semantic_codes = {"seat": 0, "leg_base": 1, "back": 5, "arm": 4}
    for index, part in enumerate(model["parametric"]["parts"]):
        ids = np.unique([i for surface in part["surfaces"]
                         for i in surface["mesh_mapping"]["construction_triangle_ids"]])
        if not len(ids) or np.any(tags[ids] >= 0):
            raise ValueError(f"invalid Armchair part mapping: {part['id']}")
        tags[ids] = index + 1
        types[ids] = semantic_codes[part["semantic"]]
        if part["semantic"] == "arm":
            points = vertices[np.unique(faces[ids])]
            low, high = points.min(axis=0), points.max(axis=0)
            axis = int(np.argmax(high - low))
            start, end = (low + high) * 0.5, (low + high) * 0.5
            start[axis], end[axis] = low[axis], high[axis]
            centerlines[index + 1] = np.stack((start, end))
    if np.any(tags < 0):
        raise ValueError("Armchair parts do not cover the reviewed model")
    leg_ids = np.flatnonzero(types == 1)
    leg_vertices = vertices[np.unique(faces[leg_ids])]
    mid = np.median(leg_vertices[:, :2], axis=0)
    centers = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            region = leg_vertices[((leg_vertices[:, 0] - mid[0]) * sx > 0)
                                  & ((leg_vertices[:, 1] - mid[1]) * sy > 0)]
            low_z, high_z = np.percentile(region[:, 2], [2, 98])
            low = region[region[:, 2] <= low_z + 25].mean(axis=0)
            high = region[region[:, 2] >= high_z - 25].mean(axis=0)
            centerlines[100 + len(centers)] = np.stack((low, high))
            centers.append((sx, sy, low, high))
    tri_centers = vertices[faces[leg_ids]].mean(axis=1)
    midpoints = np.asarray([(low + high) * 0.5 for _, _, low, high in centers])
    nearest = cKDTree(midpoints[:, :2]).query(tri_centers[:, :2])[1]
    tags[leg_ids] = 100 + nearest
    tess = SimpleNamespace(placed=SimpleNamespace(vertices=vertices, faces=faces), cad_face_tags=tags)
    seat = generate_seat_serpentine(tess, types)
    back = generate_back_strokes(tess, types, {"back_type": "whole"})
    edges = generate_edge_strokes(tess, types)
    arms = generate_arm_strokes(tess, centerlines, types)
    legs = generate_leg_strokes(tess, centerlines, types)
    shrink_nozzles(seat, 0.72)
    shrink_nozzles([stroke for stroke in back if not stroke["reason"].endswith("_rear")], 0.72)
    shrink_nozzles([stroke for stroke in back if stroke["reason"].endswith("_rear")], 0.72)
    # The original Chair program keeps each arm's upper passes together.
    arm_groups = {}
    for stroke in arms:
        arm_groups.setdefault(stroke["part_id"], []).append(stroke)
    for group in arm_groups.values():
        shrink_nozzles(group, 0.72)
    strokes = seat + back + edges + arms + legs
    for index, stroke in enumerate(strokes):
        stroke["stroke_id"] = index
    return strokes, np.zeros(3), spraybot / "datagen/chair_spray/chair_spray.py"


def pair(review_root: Path, trajectory_root: Path, spraybot: Path,
         chair_npz: Path, kind: str, seed: int) -> dict:
    if kind not in KINDS:
        raise ValueError(f"unknown native interface: {kind}")
    interface_id = f"workpiece:{kind}"
    episode = f"seed_{seed:010d}"
    model_file = review_root / "interfaces" / interface_id / "episodes" / episode / "model.json"
    model_bytes = model_file.read_bytes()
    model = json.loads(model_bytes)
    if model["generator"] != interface_id or model["seed"] != seed:
        raise ValueError(f"review episode identity mismatch: {model_file}")
    priors = model["structure_priors"]
    if not priors or (kind != "armchair" and "factory_seed" not in priors):
        raise ValueError(f"missing source factory priors: {model_file}")
    source_strokes, offset_mm, source_path = _source_strokes(kind, model, spraybot, chair_npz)
    if not source_strokes:
        raise ValueError(f"source planner returned no strokes: {interface_id} {episode}")
    mesh = trimesh.Trimesh(vertices=np.asarray(model["vertices"]) * 1000,
                           faces=np.asarray(model["triangles"]), process=False)
    paths, sources, paintds = [], [], []
    surface_points = []
    for source in source_strokes:
        surface = np.asarray(source["surface_points"], dtype=float) + offset_mm
        nozzle = np.asarray(source["nozzle_points"], dtype=float) + offset_mm
        if surface.shape != nozzle.shape or surface.ndim != 2 or surface.shape[1] != 3 or len(surface) < 2:
            raise ValueError(f"invalid source stroke: {source.get('reason')}")
        aim = surface - nozzle
        aim /= np.linalg.norm(aim, axis=1, keepdims=True)
        paths.append({"points": (nozzle / 1000).round(6).tolist(), "aims": aim.round(6).tolist()})
        sources.append({"part": source.get("part", source.get("part_id", kind)),
                        "surface": source.get("reason", source.get("line", "source planner"))})
        paintds.append(SimpleNamespace(positions_mm=nozzle, aim=aim))
        surface_points.append(surface)
    surface_points = np.concatenate(surface_points)
    surface_gap = mesh.nearest.on_surface(surface_points)[1]
    p95_gap = float(np.percentile(surface_gap, 95))
    max_gap = float(surface_gap.max())
    # This gate rejects a different model/frame; smaller gaps remain review findings.
    if p95_gap > 50 or max_gap > 75:
        raise ValueError(f"source paths do not match the current model: p95={p95_gap:.1f} mm, max={max_gap:.1f} mm")
    target = np.asarray(model["spray_target"], dtype=bool) & np.asarray(model["geometry_accessible"], dtype=bool)
    centroids = np.asarray(model["vertices"])[np.asarray(model["triangles"])[target]].mean(axis=1) * 1000
    target_gap = cKDTree(surface_points).query(centroids)[0]
    origins = np.asarray([stroke.positions_mm[len(stroke.positions_mm) // 2] for stroke in paintds])
    directions = np.asarray([stroke.aim[len(stroke.aim) // 2] for stroke in paintds])
    hits, ray_ids, _ = mesh.ray.intersects_location(origins, directions, multiple_hits=False)
    first_hit = np.full(len(paths), np.nan)
    first_hit[ray_ids] = np.linalg.norm(hits - origins[ray_ids], axis=1)
    intended = np.asarray([np.linalg.norm(
        np.asarray(source_strokes[i]["surface_points"])[len(source_strokes[i]["surface_points"]) // 2]
        - np.asarray(source_strokes[i]["nozzle_points"])[len(source_strokes[i]["nozzle_points"]) // 2])
        for i in range(len(paths))])
    blocked = np.flatnonzero(first_hit < intended - 5).tolist()
    missed = np.flatnonzero(np.isnan(first_hit) | (first_hit > intended + 25)).tolist()
    check = {"schema": "spraybot.paired-native-trajectory.v1", "interface_id": interface_id,
             "seed": seed, "factory_seed": priors.get("factory_seed"),
             "source_planner": str(source_path),
             "stroke_count": len(paths), "waypoint_count": len(surface_points),
             "model_surface_gap_p95_mm": round(p95_gap, 3), "model_surface_gap_max_mm": round(max_gap, 3),
             "coverage_threshold_mm": 45.0,
             "target_centroid_within_threshold_fraction": float((target_gap <= 45).mean()),
             "target_centroid_gap_p95_mm": float(np.percentile(target_gap, 95)),
             "status": "trajectory_review_required"}
    visibility = {"schema": "spraybot.stroke-visibility.v1", "method": "one midpoint ray per stroke",
                  "blocked_stroke_ids": blocked, "missed_stroke_ids": missed,
                  "clear_strokes": len(paths) - len(blocked) - len(missed)}
    output = trajectory_root / interface_id
    output.mkdir(parents=True, exist_ok=True)
    paintds_dir = output / "paintds"
    paintds_dir.mkdir(exist_ok=True)
    write_paintds(paintds, paintds_dir / f"{episode}.txt")
    payload = {"interface_id": interface_id, "seed": seed,
               "model_sha256": hashlib.sha256(model_bytes).hexdigest(),
               "check": check, "visibility": visibility,
               "stroke_sources": sources, "strokes": paths}
    (output / f"{episode}.json").write_text(json.dumps(payload, separators=(",", ":")))
    return {**check, "blocked_strokes": len(blocked), "missed_strokes": len(missed)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-root", type=Path, required=True)
    parser.add_argument("--trajectory-root", type=Path, required=True)
    parser.add_argument("--spraybot", type=Path, required=True)
    parser.add_argument("--chair-npz", type=Path, required=True)
    parser.add_argument("--kinds", nargs="+", choices=KINDS, default=KINDS)
    parser.add_argument("--seeds", nargs="+", type=int, default=list(range(10)))
    args = parser.parse_args()
    for kind in args.kinds:
        for seed in args.seeds:
            print(json.dumps(pair(args.review_root, args.trajectory_root, args.spraybot,
                                  args.chair_npz, kind, seed)), flush=True)

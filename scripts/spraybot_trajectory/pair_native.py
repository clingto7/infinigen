"""Pair SprayBot reference planners and a dedicated Armchair planner with review episodes.

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
    if kind != "armchair" and (not priors or "factory_seed" not in priors):
        raise ValueError(f"missing source factory priors: {model_file}")
    mesh = trimesh.Trimesh(vertices=np.asarray(model["vertices"]) * 1000,
                           faces=np.asarray(model["triangles"]), process=False)
    repair_metrics = None
    if kind == "armchair":
        from spraybot_trajectory.armchair import coating_scope, plan
        raw_target_labels = np.asarray(model["spray_target"], dtype=bool) & np.asarray(
            model["geometry_accessible"], dtype=bool)
        target_labels, scope_metrics = coating_scope(model["parametric"], raw_target_labels)
        scope_metrics["selected_accessible_target_area_fraction"] = float(
            mesh.area_faces[target_labels].sum() / mesh.area_faces[raw_target_labels].sum())
        source_strokes, repair_metrics = plan(model["parametric"], target_labels, mesh)
        offset_mm, source_path = np.zeros(3), Path(__file__).with_name("armchair.py")
    else:
        source_strokes, offset_mm, source_path = _source_strokes(kind, model, spraybot, chair_npz)
    if not source_strokes:
        raise ValueError(f"planner returned no strokes: {interface_id} {episode}")
    paths, sources, paintds = [], [], []
    surface_points = []
    nozzle_points = []
    for source in source_strokes:
        surface = np.asarray(source["surface_points"], dtype=float) + offset_mm
        nozzle = np.asarray(source["nozzle_points"], dtype=float) + offset_mm
        if surface.shape != nozzle.shape or surface.ndim != 2 or surface.shape[1] != 3 or len(surface) < 2:
            raise ValueError(f"invalid source stroke: {source.get('reason')}")
        aim = surface - nozzle
        aim /= np.linalg.norm(aim, axis=1, keepdims=True)
        paths.append({"points": (nozzle / 1000).round(6).tolist(), "aims": aim.round(6).tolist()})
        sources.append({"part": source.get("part", str(source.get("reason", kind)).split("_")[0]),
                        "surface": source.get("reason", source.get("line", "source planner"))})
        paintds.append(SimpleNamespace(positions_mm=nozzle, aim=aim))
        surface_points.append(surface)
        nozzle_points.append(nozzle)
    surface_points = np.concatenate(surface_points)
    nozzle_points = np.concatenate(nozzle_points)
    surface_gap = mesh.nearest.on_surface(surface_points)[1]
    p95_gap = float(np.percentile(surface_gap, 95))
    max_gap = float(surface_gap.max())
    # This gate rejects a different model/frame; smaller gaps remain review findings.
    if p95_gap > 50 or max_gap > 75:
        raise ValueError(f"source paths do not match the current model: p95={p95_gap:.1f} mm, max={max_gap:.1f} mm")
    target = (target_labels if kind == "armchair" else
              np.asarray(model["spray_target"], dtype=bool) &
              np.asarray(model["geometry_accessible"], dtype=bool))
    centroids = np.asarray(model["vertices"])[np.asarray(model["triangles"])[target]].mean(axis=1) * 1000
    target_gap = cKDTree(surface_points).query(centroids)[0]
    # A nearby path on the other side of a thin board does not coat this face.
    # Count only samples within half the 90 mm spray swath and facing the same
    # side of the surface (up to a 60 degree incidence angle).
    sample_outward = nozzle_points - surface_points
    sample_outward /= np.linalg.norm(sample_outward, axis=1, keepdims=True)
    neighbors = min(16, len(surface_points))
    oriented_gap, oriented_ids = cKDTree(surface_points).query(centroids, k=neighbors)
    if neighbors == 1:
        oriented_gap, oriented_ids = oriented_gap[:, None], oriented_ids[:, None]
    alignment = np.einsum("ij,ikj->ik", mesh.face_normals[target],
                          sample_outward[oriented_ids])
    oriented_covered = np.any((oriented_gap <= 45) & (alignment >= 0.5), axis=1)
    target_area = mesh.area_faces[target]
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
    check = {"schema": "spraybot.paired-trajectory.v1" if kind == "armchair" else
             "spraybot.paired-native-trajectory.v1", "interface_id": interface_id,
             "seed": seed, "factory_seed": priors.get("factory_seed") if isinstance(priors, dict) else None,
             "source_planner": str(source_path),
             "source_planner_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
             "stroke_count": len(paths), "waypoint_count": len(surface_points),
             "model_surface_gap_p95_mm": round(p95_gap, 3), "model_surface_gap_max_mm": round(max_gap, 3),
             "coverage_threshold_mm": 45.0,
             "target_centroid_within_threshold_fraction": float((target_gap <= 45).mean()),
             "oriented_target_centroid_coverage_fraction": float(oriented_covered.mean()),
             "oriented_target_area_coverage_fraction": float(
                 target_area[oriented_covered].sum() / target_area.sum()),
             "target_centroid_gap_p95_mm": float(np.percentile(target_gap, 95)),
             "status": "trajectory_review_required"}
    if kind == "armchair":
        check["strategy"] = "armchair_parametric_part_planner"
        check["planner"] = repair_metrics
        check["coating_scope"] = scope_metrics
        check["input_source"] = "parametric surfaces and spray target labels"
        lengths = np.asarray([np.linalg.norm(np.diff(np.asarray(s["surface_points"]), axis=0),
                                            axis=1).sum() for s in source_strokes])
        member_ratios = [float(length / max(1.0, np.linalg.norm(
            np.asarray(source_strokes[index]["surface_points"])[-1]
            - np.asarray(source_strokes[index]["surface_points"])[0])))
            for index, length in enumerate(lengths)
            if source_strokes[index]["reason"].endswith("_length")]
        short_strokes = np.flatnonzero(lengths < 100).tolist()
        check["stroke_length_min_mm"] = float(lengths.min())
        check["member_path_max_length_to_chord_ratio"] = max(member_ratios)
        check["linear_path_max_length_to_chord_ratio"] = float(max(
            length / max(1.0, np.linalg.norm(
                np.asarray(source_strokes[index]["surface_points"])[-1]
                - np.asarray(source_strokes[index]["surface_points"])[0]))
            for index, length in enumerate(lengths)
            if source_strokes[index]["reason"] != "seat_serpentine"))
        check["seat_serpentine_strokes"] = sum(
            source["reason"] == "seat_serpentine" for source in source_strokes)
        check["short_stroke_ids"] = short_strokes
        check["target_area_within_threshold_fraction"] = float(
            target_area[target_gap <= 45].sum() / target_area.sum())
        from spraybot_trajectory.path_checks import clear_rays
        invalid_strokes = []
        for index, stroke in enumerate(source_strokes):
            surface = np.asarray(stroke["surface_points"], dtype=float)
            nozzle = np.asarray(stroke["nozzle_points"], dtype=float)
            samples_surface = np.concatenate((surface, (surface[:-1] + surface[1:]) / 2))
            samples_nozzle = np.concatenate((nozzle, (nozzle[:-1] + nozzle[1:]) / 2))
            if not np.all(clear_rays(mesh, samples_surface, samples_nozzle)):
                invalid_strokes.append(index)
        check["path_ray_check"] = {"method": "all waypoints and segment midpoints",
                                   "invalid_stroke_ids": invalid_strokes,
                                   "sample_count": int(sum(2 * len(s["surface_points"]) - 1 for s in source_strokes))}
        check["machine_gate_scope"] = "model pairing and sampled ray safety only; coating quality requires human review"
        check["machine_gate"] = (
            "passed" if not invalid_strokes and not blocked and not missed
            and max_gap <= 25 else "failed"
        )
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

"""Pair an interface-specific trajectory with one reviewed Web model episode."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from scipy.spatial import cKDTree
import trimesh

from spraybot_trajectory.paintds import euler_zyx_to_aim, write_paintds
from spraybot_trajectory.path_checks import (
    check_exported_motion, check_exported_rays, check_exported_smoothness,
)
from spraybot_trajectory.planar import PLANAR_WORKPIECES, STANDOFF_MM, plan_planar_faces
from spraybot_trajectory.round_members import plan_round_members
from spraybot_trajectory.curved_members import CURVED_WORKPIECES, plan_curved_members


def _export_path(surface: np.ndarray, nozzle: np.ndarray) -> tuple[dict, np.ndarray]:
    aim = surface - nozzle
    aim /= np.linalg.norm(aim, axis=1, keepdims=True)
    return {"points": np.round(nozzle / 1000, 6).tolist(),
            "aims": np.round(aim, 6).tolist()}, aim


def _repair_whole_stroke(mesh, surface: np.ndarray, nozzle: np.ndarray,
                         semantic: str, model: dict) -> tuple[np.ndarray, np.ndarray, dict]:
    """Move a complete stroke within its face to avoid join-line ray ambiguity."""
    outward = np.mean(nozzle - surface, axis=0)
    outward /= np.linalg.norm(outward)
    along = surface[-1] - surface[0]
    along /= np.linalg.norm(along)
    across = np.cross(outward, along)
    across /= np.linalg.norm(across)
    shifts = [np.zeros(3)]
    for distance in (1.0, 2.0, 5.0, 10.0):
        shifts.extend((direction * sign * distance
                       for direction in (across, along) for sign in (-1, 1)))
    for shift in shifts:
        moved_surface, moved_nozzle = surface + shift, nozzle + shift
        path, _ = _export_path(moved_surface, moved_nozzle)
        source = {"part": semantic}
        rays = check_exported_rays(mesh, [path], [source], STANDOFF_MM,
                                   model["part_id"], model["part_legend"])
        motion = check_exported_motion(mesh, [path])
        if not rays["invalid_stroke_ids"] and not motion["invalid_stroke_ids"]:
            return moved_surface, moved_nozzle, {
                "method": "whole-stroke in-face translation",
                "shift_mm": shift.tolist(),
            }
    return surface, nozzle, {"method": "unresolved", "shift_mm": [0.0, 0.0, 0.0]}


def _check_paintds(path: Path, web_paths: list[dict]) -> dict:
    rows = [line.split(";") for line in path.read_text().splitlines()[1:] if line]
    expected_count = sum(len(item["points"]) for item in web_paths)
    if len(rows) != expected_count:
        return {"status": "failed", "reason": "waypoint count mismatch"}
    offset = 0
    worst_position_mm = worst_aim = 0.0
    for stroke_id, item in enumerate(web_paths):
        batch = rows[offset:offset + len(item["points"])]
        if any(int(float(row[6])) != stroke_id for row in batch):
            return {"status": "failed", "reason": "stroke order mismatch"}
        positions = np.asarray([[float(value) for value in row[:3]] for row in batch])
        angles = np.asarray([[float(value) for value in row[3:6]] for row in batch])
        aims = euler_zyx_to_aim(angles)
        expected_position = np.asarray(item["points"]) * 1000
        expected_aim = np.asarray(item["aims"])
        worst_position_mm = max(worst_position_mm, float(np.max(np.linalg.norm(
            positions - expected_position, axis=1))))
        worst_aim = max(worst_aim, float(np.max(np.linalg.norm(
            aims - expected_aim, axis=1))))
        offset += len(batch)
    return {"status": "passed" if worst_position_mm <= 0.001 and worst_aim <= 1e-4 else "failed",
            "waypoints": len(rows), "max_position_delta_mm": worst_position_mm,
            "max_aim_vector_delta": worst_aim}


def _row_covered_by_same_face(row: dict, model: dict, mesh, paths: list[dict],
                              sources: list[dict]) -> bool:
    """A short missing row is harmless only if another row coats that same face."""
    surface = next((surface for part in model["parametric"]["parts"]
                    if part["id"] == row["part"] for surface in part["surfaces"]
                    if surface["id"] == row["surface"]), None)
    if surface is None:
        return False
    prefix = f"{row['part']}:{row['surface']}:"
    same_face = [path for path, source in zip(paths, sources)
                 if source["surface"].startswith(prefix)]
    if not same_face:
        return False
    nozzles = np.concatenate([np.asarray(path["points"]) * 1000 for path in same_face])
    aims = np.concatenate([np.asarray(path["aims"]) for path in same_face])
    landings = nozzles + aims * STANDOFF_MM
    face_ids = surface["mesh_mapping"]["construction_triangle_ids"]
    for center, normal in zip(mesh.triangles_center[face_ids], mesh.face_normals[face_ids]):
        distance = np.linalg.norm(landings - center, axis=1)
        if not np.any((distance <= 45) & ((-aims) @ normal >= 0.5)):
            return False
    return True


def pair(model_path: Path, output_root: Path) -> dict:
    model_path = model_path.resolve()
    model_bytes = model_path.read_bytes()
    model = json.loads(model_bytes)
    interface_id = model["generator"]
    seed = model["seed"]
    if model_path.parent.name != f"seed_{seed:010d}" or model_path.parent.parent.parent.name != interface_id:
        raise ValueError(f"review episode identity mismatch: {model_path}")
    category = interface_id.split(":", 1)[1]
    if category not in PLANAR_WORKPIECES and category not in CURVED_WORKPIECES:
        raise ValueError(f"no workpiece trajectory planner for {interface_id}")
    planner_path = Path(__file__).with_name(
        "planar.py" if category in PLANAR_WORKPIECES else "curved_members.py")
    mesh = trimesh.Trimesh(vertices=np.asarray(model["vertices"], dtype=float) * 1000,
                           faces=np.asarray(model["triangles"], dtype=int), process=False)
    if category in PLANAR_WORKPIECES:
        strokes, diagnostics = plan_planar_faces(model, mesh)
    else:
        strokes, diagnostics = [], {"blocked_rows": [], "selected_surfaces": 0}
    curved_strokes, curved_diagnostics = plan_curved_members(model, mesh)
    strokes.extend(curved_strokes)
    diagnostics["curved_members"] = curved_diagnostics
    round_strokes, round_diagnostics = plan_round_members(model, mesh)
    strokes.extend(round_strokes)
    diagnostics["round_members"] = round_diagnostics
    if not strokes:
        raise ValueError(f"planner returned no strokes: {interface_id} seed {seed}")

    paths, sources, paintds = [], [], []
    landing_points, nozzle_points = [], []
    repairs = []
    for stroke in strokes:
        surface = np.asarray(stroke["surface_points"], dtype=float)
        nozzle = np.asarray(stroke["nozzle_points"], dtype=float)
        if surface.shape != nozzle.shape or surface.ndim != 2 or len(surface) < 2:
            raise ValueError(f"invalid stroke: {stroke['reason']}")
        surface, nozzle, repair = _repair_whole_stroke(mesh, surface, nozzle,
                                                       stroke["part"], model)
        path, aim = _export_path(surface, nozzle)
        paths.append(path)
        sources.append({"part": stroke["part"], "surface": stroke["reason"]})
        paintds.append(SimpleNamespace(positions_mm=nozzle, aim=aim))
        landing_points.append(surface)
        nozzle_points.append(nozzle)
        repairs.append(repair)

    rays = check_exported_rays(mesh, paths, sources, STANDOFF_MM,
                               model["part_id"], model["part_legend"])
    motion = check_exported_motion(mesh, paths)
    smoothness = check_exported_smoothness(paths)
    unplanned_candidates = [row for row in diagnostics["blocked_rows"]
                            if row["valid_samples"] > 0 and not row["retained_segments"]]
    covered_rows = [row for row in unplanned_candidates
                    if _row_covered_by_same_face(row, model, mesh, paths, sources)]
    unplanned = [row for row in unplanned_candidates if row not in covered_rows]
    occluded = [row for row in diagnostics["blocked_rows"]
                if row["valid_samples"] == 0 and not row["retained_segments"]]
    target = np.asarray(model["spray_target"], dtype=bool) & np.asarray(
        model["geometry_accessible"], dtype=bool)
    centroids = mesh.triangles_center[target]
    landing_points = np.concatenate(landing_points)
    nozzle_points = np.concatenate(nozzle_points)
    tree = cKDTree(landing_points)
    neighbors = min(16, len(landing_points))
    gaps, ids = tree.query(centroids, k=neighbors)
    if neighbors == 1:
        gaps, ids = gaps[:, None], ids[:, None]
    outward = nozzle_points - landing_points
    outward /= np.linalg.norm(outward, axis=1, keepdims=True)
    aligned = np.einsum("ij,ikj->ik", mesh.face_normals[target], outward[ids])
    within = np.any(gaps <= 45, axis=1)
    oriented = np.any((gaps <= 45) & (aligned >= 0.5), axis=1)
    area = mesh.area_faces[target]
    surface_gap = mesh.nearest.on_surface(landing_points)[1]
    stroke_lengths = [float(np.linalg.norm(np.diff(np.asarray(path["points"]) * 1000,
                                              axis=0), axis=1).sum()) for path in paths]
    blocked_midpoints, missed_midpoints = [], []
    semantic_ids = {name: int(index) for index, name in model["part_legend"].items()}
    for index, (path, source) in enumerate(zip(paths, sources)):
        middle = len(path["points"]) // 2
        origin = np.asarray(path["points"][middle]) * 1000
        direction = np.asarray(path["aims"][middle])
        hits, ray_ids, face_ids = mesh.ray.intersects_location(
            origin[None], direction[None], multiple_hits=False)
        if len(ray_ids) == 0:
            missed_midpoints.append(index)
            continue
        first = float(np.linalg.norm(hits[0] - origin))
        if first < STANDOFF_MM - 5 or int(model["part_id"][face_ids[0]]) != semantic_ids[source["part"]]:
            blocked_midpoints.append(index)
        elif first > STANDOFF_MM + 25:
            missed_midpoints.append(index)
    visibility = {"schema": "spraybot.stroke-visibility.v1",
                  "method": "first hit at exported stroke midpoint",
                  "blocked_stroke_ids": blocked_midpoints,
                  "missed_stroke_ids": missed_midpoints,
                  "clear_strokes": len(paths) - len(blocked_midpoints) - len(missed_midpoints)}
    check = {
        "schema": "spraybot.paired-trajectory.v1",
        "interface_id": interface_id,
        "seed": seed,
        "source_planner": str(planner_path),
        "source_planner_sha256": hashlib.sha256(planner_path.read_bytes()).hexdigest(),
        "round_planner_sha256": hashlib.sha256(Path(__file__).with_name("round_members.py").read_bytes()).hexdigest(),
        "curved_planner_sha256": hashlib.sha256(Path(__file__).with_name("curved_members.py").read_bytes()).hexdigest(),
        "adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "path_checks_sha256": hashlib.sha256(Path(__file__).with_name("path_checks.py").read_bytes()).hexdigest(),
        "paintds_sha256": hashlib.sha256(Path(__file__).with_name("paintds.py").read_bytes()).hexdigest(),
        "curved_helpers_sha256": hashlib.sha256(Path(__file__).with_name("armchair.py").read_bytes()).hexdigest(),
        "model_sha256": hashlib.sha256(model_bytes).hexdigest(),
        "standoff_mm": STANDOFF_MM,
        "stroke_count": len(strokes),
        "waypoint_count": sum(len(path["points"]) for path in paths),
        "stroke_length_min_mm": min(stroke_lengths),
        "stroke_length_median_mm": float(np.median(stroke_lengths)),
        "short_stroke_threshold_mm": 50.0,
        "short_stroke_ids": [index for index, length in enumerate(stroke_lengths) if length < 50],
        "coverage_threshold_mm": 45.0,
        "target_centroid_within_threshold_fraction": float(within.mean()),
        "target_area_within_threshold_fraction": float(area[within].sum() / area.sum()),
        "oriented_target_area_coverage_fraction": float(area[oriented].sum() / area.sum()),
        "model_surface_gap_p95_mm": float(np.percentile(surface_gap, 95)),
        "model_surface_gap_max_mm": float(surface_gap.max()),
        "coverage_diagnostic_scope": "all accessible spray_target faces; this is broader than the planned coating scope",
        "coating_scope": diagnostics,
        "fully_occluded_rows": len(occluded),
        "same_face_covered_rows": len(covered_rows),
        "visible_unplanned_rows": len(unplanned),
        "whole_stroke_repairs": repairs,
        "exported_ray_check": rays,
        "path_ray_check": rays,
        "exported_motion_check": motion,
        "exported_smoothness_check": smoothness,
        "status": "trajectory_review_required",
    }
    output = output_root / interface_id
    output.mkdir(parents=True, exist_ok=True)
    episode = f"seed_{seed:010d}"
    paintds_dir = output / "paintds"
    paintds_dir.mkdir(exist_ok=True)
    paintds_path = paintds_dir / f"{episode}.txt"
    write_paintds(paintds, paintds_path)
    check["paintds_export_check"] = _check_paintds(paintds_path, paths)
    check["geometry_gate"] = (
        "passed" if not unplanned and not rays["invalid_stroke_ids"]
        and not motion["invalid_stroke_ids"] and not smoothness["invalid_stroke_ids"]
        and not blocked_midpoints and not missed_midpoints
        and surface_gap.max() <= 25
        and check["paintds_export_check"]["status"] == "passed" else "failed"
    )
    check["machine_gate"] = check["geometry_gate"]
    check["machine_gate_scope"] = "model hash, exported Web/PaintDS pairing, sampled rays, nozzle clearance, continuity and stroke heading"
    payload = {"interface_id": interface_id, "seed": seed,
               "model_sha256": check["model_sha256"],
               "check": check, "visibility": visibility,
               "stroke_sources": sources, "strokes": paths}
    (output / f"{episode}.json").write_text(json.dumps(payload, separators=(",", ":")))
    return check


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(pair(args.model, args.output)))

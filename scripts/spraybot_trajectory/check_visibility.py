"""Screen each stroke's midpoint ray for spray-line obstruction by the model."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import trimesh

from spraybot_trajectory.paintds import euler_zyx_to_aim


def evaluate(episode: Path) -> dict:
    metadata = json.loads((episode / "source-metadata.json").read_text())
    check_path = episode / "trajectory-check.json"
    check = json.loads(check_path.read_text())
    mesh = trimesh.load_mesh(episode / metadata["model_file"], process=False)
    mesh.apply_scale(0.001)
    midpoint_rows = {}
    for line in (episode / "trajectory.txt").read_text().splitlines()[1:]:
        if line:
            row = line.split(";")
            midpoint_rows.setdefault(int(float(row[6])), []).append(row)
    if sorted(midpoint_rows) != list(range(check["stroke_count"])):
        raise ValueError(f"PaintDS stroke IDs do not match the trajectory check: {episode}")
    middle = [rows[len(rows) // 2] for rows in midpoint_rows.values()]
    origins = np.asarray([[float(value) / 1000 for value in row[:3]] for row in middle])
    angles = np.asarray([[float(value) for value in row[3:6]] for row in middle])
    directions = euler_zyx_to_aim(angles)
    hits, ray_ids, _ = mesh.ray.intersects_location(origins, directions, multiple_hits=False)
    first_hit = np.full(len(origins), np.nan)
    first_hit[ray_ids] = np.linalg.norm(hits - origins[ray_ids], axis=1)
    standoff = check["standoff_mm"] / 1000
    blocked = np.flatnonzero(first_hit < standoff - 0.005).tolist()
    missed = np.flatnonzero(np.isnan(first_hit) | (first_hit > standoff + 0.005)).tolist()
    result = {"schema": "spraybot.stroke-visibility.v1", "method": "one midpoint ray per stroke",
              "standoff_mm": check["standoff_mm"], "tolerance_mm": 5,
              "stroke_count": len(origins), "blocked_stroke_ids": blocked,
              "missed_stroke_ids": missed,
              "clear_strokes": len(origins) - len(blocked) - len(missed)}
    (episode / "visibility-check.json").write_text(json.dumps(result, indent=2) + "\n")
    check["visibility"] = {"clear_strokes": result["clear_strokes"],
                           "blocked_strokes": len(blocked), "missed_strokes": len(missed)}
    check["status"] = ("trajectory_visibility_review_required" if blocked or missed
                       else "geometric_trajectory_pilot_passed")
    check_path.write_text(json.dumps(check, indent=2) + "\n")
    return check

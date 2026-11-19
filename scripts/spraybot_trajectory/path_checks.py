"""Geometric ray and continuity checks for source-planned spray paths."""
from __future__ import annotations
import numpy as np

def clear_rays(mesh, surface: np.ndarray, nozzle: np.ndarray) -> np.ndarray:
    direction = surface - nozzle
    distance = np.linalg.norm(direction, axis=1)
    direction /= distance[:, None]
    hits, ray_ids, _ = mesh.ray.intersects_location(nozzle, direction, multiple_hits=False)
    first = np.full(len(surface), np.nan)
    first[ray_ids] = np.linalg.norm(hits - nozzle[ray_ids], axis=1)
    return np.isfinite(first) & (first >= distance - 5) & (first <= distance + 25)


def clear_motion(mesh, nozzle: np.ndarray) -> np.ndarray:
    """Reject nozzle travel segments that pass through another chair part."""
    travel = np.diff(nozzle, axis=0)
    lengths = np.linalg.norm(travel, axis=1)
    clear = lengths > 0
    if not clear.any():
        return clear
    directions = travel[clear] / lengths[clear, None]
    origins = nozzle[:-1][clear] + directions * 1e-3
    hits, ray_ids, _ = mesh.ray.intersects_location(origins, directions, multiple_hits=False)
    first = np.full(len(origins), np.inf)
    if len(ray_ids):
        first[ray_ids] = np.linalg.norm(hits - origins[ray_ids], axis=1)
    clear[np.flatnonzero(clear)] = first >= lengths[clear] - 1e-3
    return clear


def _stroke(surface: np.ndarray, nozzle: np.ndarray, reason: str, part: str) -> dict:
    return {"surface_points": surface.tolist(), "nozzle_points": nozzle.tolist(),
            "reason": reason, "part": part}


def split_runs(mesh, surface: np.ndarray, nozzle: np.ndarray,
               valid: np.ndarray, reason: str, part: str,
               max_step_mm: float = 90.0) -> list[dict]:
    if len(surface) < 2:
        return []
    step = np.linalg.norm(np.diff(nozzle, axis=0), axis=1)
    aim = surface - nozzle
    aim /= np.linalg.norm(aim, axis=1)[:, None]
    turn = (aim[:-1] * aim[1:]).sum(axis=1)
    joined = valid[:-1] & valid[1:] & (step <= max_step_mm) & (turn >= 0.75)
    joined &= clear_motion(mesh, nozzle)
    candidates = np.flatnonzero(joined)
    if len(candidates):
        middle_surface = (surface[candidates] + surface[candidates + 1]) * 0.5
        middle_nozzle = (nozzle[candidates] + nozzle[candidates + 1]) * 0.5
        joined[candidates] &= clear_rays(mesh, middle_surface, middle_nozzle)
    out = []
    start = 0
    for index in range(len(joined) + 1):
        if index < len(joined) and joined[index]:
            continue
        end = index + 1
        if end - start >= 2 and np.all(valid[start:end]):
            out.append(_stroke(surface[start:end], nozzle[start:end], reason, part))
        start = index + 1
    return out



"""Geometric ray and continuity checks for source-planned spray paths."""
from __future__ import annotations
import numpy as np

def clear_rays(mesh, surface: np.ndarray, nozzle: np.ndarray,
               allowed_faces: np.ndarray | None = None) -> np.ndarray:
    direction = surface - nozzle
    distance = np.linalg.norm(direction, axis=1)
    direction /= distance[:, None]
    hits, ray_ids, faces = mesh.ray.intersects_location(nozzle, direction, multiple_hits=False)
    first = np.full(len(surface), np.nan)
    correct = np.zeros(len(surface), dtype=bool)
    if len(ray_ids):
        first[ray_ids] = np.linalg.norm(hits - nozzle[ray_ids], axis=1)
        correct[ray_ids] = True if allowed_faces is None else allowed_faces[faces]
    return correct & np.isfinite(first) & (first >= distance - 5) & (first <= distance + 25)


def clear_motion(mesh, nozzle: np.ndarray, clearance_mesh=None,
                 min_clearance_mm: float = 0.0) -> np.ndarray:
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
    if clearance_mesh is not None:
        for i in np.flatnonzero(clear):
            count = max(2, int(np.ceil(lengths[i] / 5)) + 1)
            probes = np.linspace(nozzle[i], nozzle[i + 1], count)
            if np.min(clearance_mesh.nearest.on_surface(probes)[1]) < min_clearance_mm:
                clear[i] = False
    return clear


def _stroke(surface: np.ndarray, nozzle: np.ndarray, reason: str, part: str) -> dict:
    return {"surface_points": surface.tolist(), "nozzle_points": nozzle.tolist(),
            "reason": reason, "part": part}


def split_runs(mesh, surface: np.ndarray, nozzle: np.ndarray,
               valid: np.ndarray, reason: str, part: str,
               max_step_mm: float = 90.0, allowed_faces: np.ndarray | None = None,
               clearance_mesh=None, min_clearance_mm: float = 0.0) -> list[dict]:
    if len(surface) < 2:
        return []
    if clearance_mesh is not None:
        valid = valid & (clearance_mesh.nearest.on_surface(nozzle)[1] >= min_clearance_mm)
    step = np.linalg.norm(np.diff(nozzle, axis=0), axis=1)
    aim = surface - nozzle
    aim /= np.linalg.norm(aim, axis=1)[:, None]
    turn = (aim[:-1] * aim[1:]).sum(axis=1)
    joined = valid[:-1] & valid[1:] & (step <= max_step_mm) & (turn >= 0.75)
    joined &= clear_motion(mesh, nozzle, clearance_mesh, min_clearance_mm)
    candidates = np.flatnonzero(joined)
    if len(candidates):
        probes_surface, probes_nozzle, owner = [], [], []
        for i in candidates:
            count = max(2, int(np.ceil(step[i] / 5)))
            for t in np.arange(1, count) / count:
                probes_surface.append((1 - t) * surface[i] + t * surface[i + 1])
                probes_nozzle.append((1 - t) * nozzle[i] + t * nozzle[i + 1])
                owner.append(i)
        if owner:
            valid_probes = clear_rays(mesh, np.asarray(probes_surface),
                                      np.asarray(probes_nozzle), allowed_faces)
            joined[np.asarray(owner)[~valid_probes]] = False
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


def check_exported_rays(mesh, paths: list[dict], sources: list[dict],
                        standoff_mm: float | list[float] | None,
                        face_parts: np.ndarray | None = None,
                        part_legend: dict | None = None) -> dict:
    """Validate the rounded path/aim vectors that the Web page actually receives."""
    semantic_ids = ({name: int(index) for index, name in part_legend.items()}
                    if part_legend is not None else {})
    invalid, count = [], 0
    for index, (path, source) in enumerate(zip(paths, sources)):
        positions = np.asarray(path['points'], dtype=float) * 1000
        aims = np.asarray(path['aims'], dtype=float)
        nozzles, directions = [positions[0]], [aims[0]]
        for i in range(len(positions) - 1):
            steps = max(1, int(np.ceil(np.linalg.norm(positions[i + 1] - positions[i]) / 5)))
            for t in np.arange(1, steps + 1) / steps:
                direction = (1 - t) * aims[i] + t * aims[i + 1]
                direction /= np.linalg.norm(direction)
                nozzles.append((1 - t) * positions[i] + t * positions[i + 1])
                directions.append(direction)
        nozzles = np.asarray(nozzles)
        directions = np.asarray(directions)
        count += len(nozzles)
        allowed = (np.asarray(face_parts) == semantic_ids[source['part']]
                   if face_parts is not None and source['part'] in semantic_ids else None)
        if standoff_mm is None:
            hits, ray_ids, faces = mesh.ray.intersects_location(
                nozzles, directions, multiple_hits=False)
            valid = np.zeros(len(nozzles), dtype=bool)
            if len(ray_ids):
                distance = np.linalg.norm(hits - nozzles[ray_ids], axis=1)
                valid[ray_ids] = distance <= 300
                if allowed is not None:
                    valid[ray_ids] &= allowed[faces]
        else:
            distance = standoff_mm[index] if isinstance(standoff_mm, list) else standoff_mm
            intended = nozzles + directions * distance
            valid = clear_rays(mesh, intended, nozzles, allowed)
        if not np.all(valid):
            invalid.append(index)
    return {'method': 'rounded exported aims every 5 mm; intended part when labelled',
            'invalid_stroke_ids': invalid, 'sample_count': count}


def check_exported_motion(mesh, paths: list[dict], clearance_mm: float = 1.0) -> dict:
    """Check that each rounded nozzle path stays outside the workpiece."""
    invalid, closest = [], np.inf
    for index, path in enumerate(paths):
        nozzle = np.asarray(path['points'], dtype=float) * 1000
        distances = mesh.nearest.on_surface(nozzle)[1]
        closest = min(closest, float(distances.min()))
        if np.any(distances < clearance_mm) or not np.all(clear_motion(mesh, nozzle)):
            invalid.append(index)
    return {'method': 'nozzle position clearance and segment intersection',
            'invalid_stroke_ids': invalid, 'min_clearance_mm': closest}


def check_exported_smoothness(paths: list[dict], max_turn_deg: float = 45.0) -> dict:
    """Screen abrupt changes in the exported nozzle travel direction."""
    invalid, worst = [], 0.0
    for index, path in enumerate(paths):
        points = np.asarray(path['points'], dtype=float)
        steps = np.diff(points, axis=0)
        lengths = np.linalg.norm(steps, axis=1)
        if np.any(lengths < 1e-6):
            invalid.append(index)
            continue
        if len(steps) < 2:
            continue
        unit = steps / lengths[:, None]
        angles = np.degrees(np.arccos(np.clip(np.sum(unit[:-1] * unit[1:], axis=1), -1, 1)))
        worst = max(worst, float(np.max(angles)))
        if np.any(angles > max_turn_deg):
            invalid.append(index)
    return {'method': 'adjacent exported nozzle segments heading change',
            'max_turn_deg': max_turn_deg, 'observed_max_turn_deg': worst,
            'invalid_stroke_ids': invalid}



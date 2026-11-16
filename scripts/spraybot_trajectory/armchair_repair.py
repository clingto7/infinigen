"""Machine-guided Armchair corrections after the native Chair region planner.

The source planner proposes part-level paths. This module projects member paths
onto the reviewed mesh, clips obstructed path points, and fills uncovered target
regions with grouped surface-normal sweeps. Every retained point is ray checked.
"""

from __future__ import annotations

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree


def clear_rays(mesh, surface: np.ndarray, nozzle: np.ndarray) -> np.ndarray:
    direction = surface - nozzle
    distance = np.linalg.norm(direction, axis=1)
    direction /= distance[:, None]
    hits, ray_ids, _ = mesh.ray.intersects_location(nozzle, direction, multiple_hits=False)
    first = np.full(len(surface), np.nan)
    first[ray_ids] = np.linalg.norm(hits - nozzle[ray_ids], axis=1)
    return np.isfinite(first) & (first >= distance - 5) & (first <= distance + 25)


def _stroke(surface: np.ndarray, nozzle: np.ndarray, reason: str, part: str) -> dict:
    return {"surface_points": surface.tolist(), "nozzle_points": nozzle.tolist(),
            "reason": reason, "part": part}


def _split_runs(mesh, surface: np.ndarray, nozzle: np.ndarray,
                valid: np.ndarray, reason: str, part: str) -> list[dict]:
    if len(surface) < 2:
        return []
    step = np.linalg.norm(np.diff(nozzle, axis=0), axis=1)
    aim = surface - nozzle
    aim /= np.linalg.norm(aim, axis=1)[:, None]
    turn = (aim[:-1] * aim[1:]).sum(axis=1)
    joined = valid[:-1] & valid[1:] & (step <= 90) & (turn >= 0.75)
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


def _order(points: np.ndarray) -> np.ndarray:
    if len(points) <= 2:
        return np.arange(len(points))
    center = points.mean(axis=0)
    _, _, basis = np.linalg.svd(points - center, full_matrices=False)
    along = (points - center) @ basis[0]
    across = (points - center) @ basis[1]
    if np.ptp(across) < 45:
        return np.argsort(along)
    rows = np.floor((across - across.min()) / 45).astype(int)
    order = []
    for row in range(rows.min(), rows.max() + 1):
        indices = np.flatnonzero(rows == row)
        indices = indices[np.argsort(along[indices])]
        order.extend(indices[::-1] if row % 2 else indices)
    return np.asarray(order, dtype=int)


def repair(model: dict, mesh, source_strokes: list[dict]) -> tuple[list[dict], dict]:
    retained = []
    clipped_points = 0
    for stroke in source_strokes:
        surface = np.asarray(stroke["surface_points"], dtype=float)
        nozzle = np.asarray(stroke["nozzle_points"], dtype=float)
        reason = stroke["reason"]
        if reason.startswith(("arm_", "leg_")):
            projected = mesh.nearest.on_surface(surface)[0]
            nozzle += projected - surface
            surface = projected
        valid = clear_rays(mesh, surface, nozzle)
        clipped_points += int((~valid).sum())
        retained.extend(_split_runs(mesh, surface, nozzle, valid, reason, reason.split("_")[0]))
    surface_points = np.vstack([s["surface_points"] for s in retained])
    target = np.asarray(model["spray_target"], dtype=bool) & np.asarray(model["geometry_accessible"], dtype=bool)
    ids = np.flatnonzero(target)
    centers = mesh.triangles_center[ids]
    normals = mesh.face_normals[ids]
    uncovered = cKDTree(surface_points).query(centers)[0] > 45
    ids, centers, normals = ids[uncovered], centers[uncovered], normals[uncovered]
    nozzle = centers + normals * 100
    clear = clear_rays(mesh, centers, nozzle)
    unresolved = int((~clear).sum())
    ids, centers, normals, nozzle = ids[clear], centers[clear], normals[clear], nozzle[clear]
    part_ids = np.full(len(mesh.faces), -1, dtype=int)
    for index, part in enumerate(model["parametric"]["parts"]):
        for surface in part["surfaces"]:
            part_ids[surface["mesh_mapping"]["construction_triangle_ids"]] = index
    if np.any(part_ids[ids] < 0):
        raise ValueError("unmapped Armchair target triangles")
    axes = np.argmax(np.abs(normals), axis=1)
    keys = part_ids[ids] * 6 + axes * 2 + (normals[np.arange(len(ids)), axes] < 0)
    extra = []
    for key in np.unique(keys):
        group = np.flatnonzero(keys == key)
        points = centers[group]
        pairs = np.asarray(list(cKDTree(points).query_pairs(90)), dtype=int).reshape(-1, 2)
        graph = coo_matrix((np.ones(len(pairs) * 2),
                            (np.r_[pairs[:, 0], pairs[:, 1]], np.r_[pairs[:, 1], pairs[:, 0]])),
                           shape=(len(group), len(group))).tocsr()
        _, components = connected_components(graph, directed=False)
        for component in np.unique(components):
            members = group[components == component]
            order = _order(centers[members])
            selected = members[order]
            surface = centers[selected]
            path = nozzle[selected]
            part = model["parametric"]["parts"][part_ids[ids[selected[0]]]]["semantic"]
            if len(selected) == 1:
                triangle = mesh.vertices[mesh.faces[ids[selected[0]]]]
                tangent = triangle[1] - triangle[0]
                surface = np.stack((surface[0] - tangent * 0.2, surface[0] + tangent * 0.2))
                path = surface + normals[selected[0]] * 100
            valid = clear_rays(mesh, surface, path)
            extra.extend(_split_runs(mesh, surface, path, valid, "target_patch", part))
    output = retained + extra
    if not output:
        raise ValueError("Armchair repair produced no path")
    return output, {"source_strokes": len(source_strokes), "source_points_clipped": clipped_points,
                    "target_centers_unresolved": unresolved, "repair_strokes": len(extra)}

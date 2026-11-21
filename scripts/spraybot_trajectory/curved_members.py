"""Panel rasters and lengthwise passes for generated swept furniture members."""

from __future__ import annotations

import numpy as np
from scipy.spatial import ConvexHull

from spraybot_trajectory.armchair import corners, face_mask, member_line, samples, smooth_stroke, surface_components, sweep
from spraybot_trajectory.path_checks import check_exported_rays, clear_motion


CURVED_WORKPIECES = {
    "backed_bench", "backless_bench", "bar_chair", "ladder_back_chair", "windsor_chair",
}


def _exported_rays_clear(mesh, stroke: dict, allowed_faces: np.ndarray) -> bool:
    """Check interpolated and rounded aims before accepting a joined stroke."""
    surface = np.asarray(stroke["surface_points"])
    nozzle = np.asarray(stroke["nozzle_points"])
    aim = surface - nozzle
    aim /= np.linalg.norm(aim, axis=1)[:, None]
    path = {"points": np.round(nozzle / 1000, 6).tolist(),
            "aims": np.round(aim, 6).tolist()}
    result = check_exported_rays(mesh, [path], [{"part": "target"}], 120.0,
                                 allowed_faces.astype(np.int8), {"1": "target"})
    return not result["invalid_stroke_ids"]


def _outside_back_envelope(rows: list[dict], equations: np.ndarray) -> list[dict]:
    """Keep the longest run of each seat row outside the back hull."""
    retained = []
    for row in rows:
        surface = np.asarray(row["surface_points"])
        nozzle = np.asarray(row["nozzle_points"])
        outside = np.max(nozzle @ equations[:, :3].T + equations[:, 3], axis=1) >= 2.0
        joined = outside[:-1] & outside[1:]
        for index in np.flatnonzero(joined):
            length = np.linalg.norm(nozzle[index + 1] - nozzle[index])
            probes = np.linspace(nozzle[index], nozzle[index + 1],
                                 max(2, int(np.ceil(length / 5)) + 1))
            joined[index] = np.all(np.max(probes @ equations[:, :3].T + equations[:, 3],
                                          axis=1) >= 2.0)
        cuts = np.flatnonzero(~joined)
        starts = np.r_[0, cuts + 1]
        stops = np.r_[cuts + 1, len(nozzle)]
        candidates = [(start, stop) for start, stop in zip(starts, stops)
                      if stop - start >= 2 and np.all(outside[start:stop])]
        if not candidates:
            continue
        start, stop = max(candidates, key=lambda pair: np.linalg.norm(
            np.diff(surface[pair[0]:pair[1]], axis=0), axis=1).sum())
        if np.linalg.norm(np.diff(surface[start:stop], axis=0), axis=1).sum() < 100:
            continue
        retained.append({**row, "surface_points": surface[start:stop].tolist(),
                         "nozzle_points": nozzle[start:stop].tolist()})
    return retained


def _prefer_connected(mesh, separate: list[dict], connected: list[dict],
                      allowed_faces: np.ndarray, clearance_mesh=None,
                      min_clearance_mm: float = 0.0) -> list[dict]:
    if not connected or len(connected) >= len(separate):
        return separate
    for stroke in connected:
        nozzle = np.asarray(stroke["nozzle_points"])
        travel = np.diff(nozzle, axis=0)
        length = np.linalg.norm(travel, axis=1)
        if (np.any(length < 1) or not _exported_rays_clear(mesh, stroke, allowed_faces)
                or not np.all(clear_motion(mesh, nozzle))):
            return separate
        if (clearance_mesh is not None and np.min(
                clearance_mesh.nearest.on_surface(nozzle)[1]) < min_clearance_mm):
            return separate
        heading = travel / length[:, None]
        if np.any(np.sum(heading[:-1] * heading[1:], axis=1) < np.cos(np.deg2rad(45))):
            return separate
    return connected


def _join_curved_rows(mesh, rows: list[dict], allowed_faces: np.ndarray,
                      outward: np.ndarray) -> list[dict]:
    """Connect neighboring curved panel rows with a projected, rounded turn."""
    if len(rows) < 2:
        return rows
    panel = mesh.submesh([np.flatnonzero(allowed_faces)], append=True, repair=False)
    result = [rows[0]]
    for following in rows[1:]:
        previous = result[-1]
        first = np.asarray(previous["surface_points"])
        second = np.asarray(following["surface_points"])
        gap = np.linalg.norm(second[0] - first[-1])
        cut = max(2, int(np.ceil(gap / 40)))
        if gap > 120 or min(len(first), len(second)) <= 2 * cut + 4:
            result.append(following)
            continue
        first, second = first[:-cut], second[cut:]
        start, end = first[-1], second[0]
        across = end - start
        radius = np.linalg.norm(across) / 2
        forward = first[-1] - first[-2]
        forward /= np.linalg.norm(forward)
        across /= 2 * radius
        center = (start + end) / 2
        trial = np.asarray([center + forward * radius * np.sin(angle)
                            - across * radius * np.cos(angle)
                            for angle in np.linspace(0, np.pi, 9)[1:-1]])
        projected, _, faces = panel.nearest.on_surface(trial)
        normals = panel.face_normals[faces]
        if np.any(normals @ outward < 0.5):
            result.append(following)
            continue
        surface = np.vstack((first, projected, second))
        prior_nozzle = np.asarray(previous["nozzle_points"])[:-cut]
        next_nozzle = np.asarray(following["nozzle_points"])[cut:]
        nozzle = np.vstack((prior_nozzle, projected + normals * 120.0, next_nozzle))
        rounded = smooth_stroke({**previous, "surface_points": surface.tolist(),
                                 "nozzle_points": nozzle.tolist()}, passes=12)
        surface = np.asarray(rounded["surface_points"])
        nozzle = np.asarray(rounded["nozzle_points"])
        travel = np.diff(nozzle, axis=0)
        lengths = np.linalg.norm(travel, axis=1)
        if np.any(lengths < 1):
            result.append(following)
            continue
        unit = travel / lengths[:, None]
        if (np.any(np.sum(unit[:-1] * unit[1:], axis=1) < np.cos(np.deg2rad(45)))
                or not _exported_rays_clear(mesh, rounded, allowed_faces)
                or not np.all(clear_motion(mesh, nozzle))):
            result.append(following)
            continue
        result[-1] = {**rounded, "reason": previous["reason"].replace("_raster", "_serpentine")}
    return result


def plan_curved_members(model: dict, mesh) -> tuple[list[dict], dict]:
    category = model["generator"].split(":", 1)[1]
    if category not in CURVED_WORKPIECES:
        return [], {"curved_components": 0, "scope": "none"}
    target = np.asarray(model["spray_target"], dtype=bool)
    vertices = np.asarray(mesh.vertices)
    object_center = (vertices.min(axis=0) + vertices.max(axis=0)) / 2
    strokes, counts = [], {"seat": 0, "back": 0, "leg_base": 0}
    part_ids = np.asarray(model["part_id"])
    back_ids = [int(index) for index, name in model["part_legend"].items()
                if name in {"back", "back_panel"}]
    back_faces = np.flatnonzero(np.isin(part_ids, back_ids))
    back_mesh = mesh.submesh([back_faces], append=True, repair=False) if len(back_faces) else None
    back_envelope = (ConvexHull(back_mesh.vertices).equations
                     if category == "ladder_back_chair" and back_mesh is not None else None)
    for part in model["parametric"]["parts"]:
        semantic = "leg_base" if part["semantic"] == "storage_grid_legs" else part["semantic"]
        if semantic not in counts or part["surfaces"][0]["type"] not in {"sweep_quad", "sweep_cap"}:
            continue
        for component in surface_components(part):
            points, normals = samples(component, target)
            if len(points) < 2:
                continue
            bounds = np.vstack([corners(s) for s in component]) * 1000
            extent = np.ptp(bounds, axis=0)
            position = (bounds.min(axis=0) + bounds.max(axis=0)) / 2
            center = points.mean(axis=0)
            allowed = face_mask(mesh, component)
            counts[semantic] += 1
            if semantic == "seat":
                along = int(np.argmax(extent[:2]))
                across = 1 - along
                def seat_rows(serpentine):
                    return [smooth_stroke(stroke, passes=16) for stroke in
                            sweep(mesh, points, normals, center, np.eye(3),
                                  np.array([0.0, 0.0, 1.0]), across, along,
                                  semantic, "seat_top_raster", serpentine=serpentine,
                                  allowed_faces=allowed, clearance_mesh=back_mesh,
                                  min_clearance_mm=70.0)]
                separate, connected = seat_rows(False), seat_rows(True)
                if back_envelope is not None:
                    separate = _outside_back_envelope(separate, back_envelope)
                    connected = _outside_back_envelope(connected, back_envelope)
                strokes.extend(_prefer_connected(mesh, separate, connected, allowed,
                                                 back_mesh, 60.0))
                edge_directions = [np.eye(3)[axis] * sign
                                   for axis in (0, 1) for sign in (-1, 1)]
            elif semantic == "back":
                along = 1 if extent[1] > extent[2] else 2
                across = 2 if along == 1 else 1
                for sign in (-1, 1):
                    def back_rows(serpentine):
                        return [smooth_stroke(stroke, passes=8, landing=False) for stroke in
                                sweep(mesh, points, normals, center, np.eye(3),
                                      np.array([float(sign), 0.0, 0.0]), across, along,
                                      semantic, f"back_{'front' if sign > 0 else 'rear'}_raster",
                                      serpentine=serpentine, allowed_faces=allowed)]
                    separate = back_rows(False)
                    if category == "bar_chair":
                        projected = _join_curved_rows(mesh, separate, allowed,
                                                      np.array([float(sign), 0.0, 0.0]))
                        connected = (projected if len(projected) < len(separate) else
                                     _prefer_connected(mesh, separate, back_rows(True), allowed))
                    else:
                        connected = _prefer_connected(mesh, separate, back_rows(True), allowed)
                    strokes.extend(connected)
                edge_directions = [np.array([0.0, float(sign), 0.0]) for sign in (-1, 1)]
            else:
                branches = [component]
                if (category in {"backed_bench", "backless_bench"} and extent[1] > 180
                        and extent[2] > 250):
                    # A U-shaped support is one connected mesh but contains two legs.
                    branches = []
                    for sign in (-1, 1):
                        branch = [surface for surface in component if
                                  sign * (corners(surface).mean(axis=0)[1] * 1000 - position[1])
                                  > extent[1] * 0.2]
                        if branch:
                            branches.append(branch)
                    bottom = [surface for surface in component if
                              np.max(corners(surface)[:, 2]) * 1000 < bounds[:, 2].min() + 90]
                    if bottom:
                        outward_x = np.eye(3)[0] * (1 if position[0] >= object_center[0] else -1)
                        strokes.extend(member_line(mesh, bottom, outward_x, semantic,
                                                   "u_support_bottom_length",
                                                   trim_mm=8.0,
                                                   allowed_faces=face_mask(mesh, bottom),
                                                   dense=True))
                for branch in branches:
                    branch_bounds = np.vstack([corners(s) for s in branch]) * 1000
                    branch_extent = np.ptp(branch_bounds, axis=0)
                    branch_position = (branch_bounds.min(axis=0) + branch_bounds.max(axis=0)) / 2
                    radial = branch_position[:2] - object_center[:2]
                    if int(np.argmax(branch_extent)) == 2:
                        directions = [np.eye(3)[axis] * (1 if radial[axis] >= 0 else -1)
                                      for axis in (0, 1)]
                    else:
                        across = 1 - int(np.argmax(branch_extent[:2]))
                        directions = [np.eye(3)[across] * (1 if radial[across] >= 0 else -1)]
                    branch_faces = face_mask(mesh, branch)
                    for direction in directions:
                        lines = member_line(mesh, branch, direction, semantic,
                                            "leg_or_stretcher_length",
                                            allowed_faces=branch_faces, dense=True)
                        if (category == "backed_bench" and branch_extent[2] < 100
                                and branch_extent[0] > 200 and len(lines) > 1):
                            # Keep the outer line of a wide horizontal support.
                            axis = int(np.argmax(np.abs(direction)))
                            positions = [np.mean(line["surface_points"], axis=0)[axis]
                                         for line in lines]
                            best = max(positions) if direction[axis] > 0 else min(positions)
                            lines = [line for line, value in zip(lines, positions)
                                     if abs(value - best) < 50]
                        strokes.extend(lines)
                edge_directions = []
            for direction in edge_directions:
                edge_surfaces = [surface for surface in component
                                 if np.dot(surface["geometry"]["normal"], direction) > 0.7
                                 and abs(surface["geometry"]["normal"][2]) < 0.3]
                if not edge_surfaces:
                    continue
                for edge in surface_components({"surfaces": edge_surfaces}):
                    strokes.extend(member_line(mesh, edge, direction, semantic,
                                               f"{semantic}_narrow_edge",
                                               trim_mm=8.0,
                                               allowed_faces=allowed, dense=True))
    return strokes, {"curved_components": counts,
                     "scope": "seat top and narrow edges, back front/rear and outer edges; "
                              "two outward leg sides and outward stretchers"}

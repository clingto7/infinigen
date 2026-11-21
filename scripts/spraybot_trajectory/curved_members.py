"""Panel rasters and lengthwise passes for generated swept furniture members."""

from __future__ import annotations

import numpy as np

from spraybot_trajectory.armchair import corners, face_mask, member_line, samples, smooth_stroke, surface_components, sweep
from spraybot_trajectory.path_checks import clear_motion, clear_rays


CURVED_WORKPIECES = {
    "backed_bench", "backless_bench", "bar_chair", "ladder_back_chair", "windsor_chair",
}


def _prefer_connected(mesh, separate: list[dict], connected: list[dict],
                      allowed_faces: np.ndarray) -> list[dict]:
    if not connected or len(connected) >= len(separate):
        return separate
    for stroke in connected:
        surface = np.asarray(stroke["surface_points"])
        nozzle = np.asarray(stroke["nozzle_points"])
        travel = np.diff(nozzle, axis=0)
        length = np.linalg.norm(travel, axis=1)
        if (np.any(length < 1) or not np.all(clear_rays(mesh, surface, nozzle, allowed_faces))
                or not np.all(clear_motion(mesh, nozzle))):
            return separate
        heading = travel / length[:, None]
        if np.any(np.sum(heading[:-1] * heading[1:], axis=1) < np.cos(np.deg2rad(45))):
            return separate
    return connected


def plan_curved_members(model: dict, mesh) -> tuple[list[dict], dict]:
    category = model["generator"].split(":", 1)[1]
    if category not in CURVED_WORKPIECES:
        return [], {"curved_components": 0, "scope": "none"}
    target = np.asarray(model["spray_target"], dtype=bool)
    vertices = np.asarray(mesh.vertices)
    object_center = (vertices.min(axis=0) + vertices.max(axis=0)) / 2
    strokes, counts = [], {"seat": 0, "back": 0, "leg_base": 0}
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
                                  allowed_faces=allowed)]
                strokes.extend(_prefer_connected(mesh, seat_rows(False), seat_rows(True), allowed))
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
                    strokes.extend(_prefer_connected(mesh, back_rows(False), back_rows(True),
                                                     allowed))
                edge_directions = [np.array([0.0, float(sign), 0.0]) for sign in (-1, 1)]
            else:
                branches = [component]
                if (category == "backless_bench" and extent[1] > 180
                        and extent[2] > 250):
                    # A U-shaped support is one connected mesh but contains two legs.
                    branches = []
                    for sign in (-1, 1):
                        branch = [surface for surface in component if
                                  sign * (corners(surface).mean(axis=0)[1] * 1000 - position[1])
                                  > extent[1] * 0.2]
                        if branch:
                            branches.append(branch)
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
                        strokes.extend(member_line(mesh, branch, direction, semantic,
                                                   "leg_or_stretcher_length",
                                                   allowed_faces=branch_faces))
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
                                               allowed_faces=face_mask(mesh, edge), dense=True))
    return strokes, {"curved_components": counts,
                     "scope": "seat top and narrow edges, back front/rear and outer edges; "
                              "two outward leg sides and outward stretchers"}

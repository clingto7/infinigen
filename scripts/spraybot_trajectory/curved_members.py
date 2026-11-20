"""Panel rasters and lengthwise passes for generated swept furniture members."""

from __future__ import annotations

import numpy as np

from spraybot_trajectory.armchair import corners, face_mask, member_line, samples, smooth_stroke, surface_components, sweep


CURVED_WORKPIECES = {
    "backed_bench", "backless_bench", "bar_chair", "ladder_back_chair", "windsor_chair",
}


def plan_curved_members(model: dict, mesh) -> tuple[list[dict], dict]:
    category = model["generator"].split(":", 1)[1]
    if category not in CURVED_WORKPIECES:
        return [], {"curved_components": 0, "scope": "none"}
    target = np.asarray(model["spray_target"], dtype=bool)
    vertices = np.asarray(mesh.vertices)
    object_center = (vertices.min(axis=0) + vertices.max(axis=0)) / 2
    strokes, counts = [], {"seat": 0, "back": 0, "leg_base": 0}
    for part in model["parametric"]["parts"]:
        semantic = part["semantic"]
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
                strokes.extend(smooth_stroke(stroke, passes=16) for stroke in
                               sweep(mesh, points, normals, center, np.eye(3),
                                     np.array([0.0, 0.0, 1.0]), across, along,
                                     semantic, "seat_top_raster", allowed_faces=allowed))
            elif semantic == "back":
                along = 1 if extent[1] > extent[2] else 2
                across = 2 if along == 1 else 1
                for sign in (-1, 1):
                    strokes.extend(smooth_stroke(stroke, passes=8, landing=False) for stroke in
                                   sweep(mesh, points, normals, center, np.eye(3),
                                         np.array([float(sign), 0.0, 0.0]), across, along,
                                         semantic, f"back_{'front' if sign > 0 else 'rear'}_raster",
                                         allowed_faces=allowed))
            else:
                axis = int(np.argmax(extent))
                if axis == 2:
                    horizontal = position[:2] - object_center[:2]
                    primary = int(np.argmax(np.abs(horizontal)))
                    sign = 1.0 if horizontal[primary] >= 0 else -1.0
                    direction = np.eye(3)[primary] * sign
                else:
                    direction = np.array([0.0, 0.0, 1.0])
                strokes.extend(member_line(mesh, component, direction, semantic,
                                           "leg_or_stretcher_length", allowed_faces=allowed))
    return strokes, {"curved_components": counts,
                     "scope": "seat top and back front/rear rasters; outward legs and upper stretchers"}

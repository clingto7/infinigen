"""Whole-face raster paths for planar boards and members in furniture.

Each row belongs to one generation-time surface, not to a mesh triangle. A row
that cannot be sprayed continuously is reported as blocked for interface-specific
repair rather than silently cropped into short strokes.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from spraybot_trajectory.path_checks import clear_motion, clear_rays, split_runs


STANDOFF_MM = 120.0
SPACING_MM = 85.0
SAMPLE_STEP_MM = 15.0
EDGE_TRIM_MM = 25.0
JOIN_GUARD_SAMPLES = 1
MIN_ROW_MM = 65.0


@dataclass(frozen=True)
class SurfacePolicy:
    broad_horizontal: bool = True
    broad_vertical: bool = True
    front_edges: bool = True


OPEN_SHELF_POLICIES = {
    "corner_shelf": SurfacePolicy(),
    "ladder_shelf": SurfacePolicy(),
    "metal_shelving": SurfacePolicy(),
    "staggered_display_shelf": SurfacePolicy(),
}

PLANAR_WORKPIECES = {
    **OPEN_SHELF_POLICIES,
    **{name: SurfacePolicy() for name in (
        "backless_bench", "cabriole_leg_table", "corner_desk", "crib",
        "folding_chair", "folding_table", "hairpin_leg_table",
        "ladder_back_chair", "serving_cart", "trestle_table", "workbench",
        "coat_rack",
    )},
}


def _plane(surface: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    if surface["type"] != "plane_rectangle":
        raise ValueError(f"not a rectangular plane: {surface['type']}")
    geometry = surface["geometry"]
    return tuple(np.asarray(geometry[key], dtype=float) * (1000 if key != "normal" else 1)
                 for key in ("origin", "u", "v", "normal"))


def _area_mm2(surface: dict) -> float:
    if surface["type"] == "plane_rectangle":
        _, u, v, _ = _plane(surface)
        return float(np.linalg.norm(np.cross(u, v)))
    if surface["type"] == "plane_triangle":
        _, u, v, _ = _plane({**surface, "type": "plane_rectangle"})
        return float(np.linalg.norm(np.cross(u, v)) / 2)
    return 0.0


def _selected(surface: dict, semantic: str, target: np.ndarray,
              object_center: np.ndarray, category: str) -> bool:
    ids = surface["mesh_mapping"]["construction_triangle_ids"]
    if not np.any(target[ids]) or _area_mm2(surface) < 2500:
        return False
    normal = np.asarray(surface["geometry"]["normal"], dtype=float)
    origin, u, v, _ = _plane({**surface, "type": "plane_rectangle"})
    if category == "staggered_display_shelf" and min(np.linalg.norm(u), np.linalg.norm(v)) < 25:
        return False
    center = origin + (u + v) * (1 / 3 if surface["type"] == "plane_triangle" else 0.5)
    if (category == "crib" and semantic == "frame" and normal[2] > 0.8
            and min(np.linalg.norm(u), np.linalg.norm(v)) < 30
            and center[2] < object_center[2] + 250
            and abs(u[0]) + abs(v[0]) > 1.5 * (abs(u[1]) + abs(v[1]))):
        return False
    if semantic in {"top", "seat"}:
        return normal[2] > 0.8 or normal[0] > 0.8
    if semantic == "shelf":
        return abs(normal[2]) > 0.8 or normal[0] > 0.8
    if semantic in {"back_panel", "back"}:
        return abs(normal[0]) > 0.8
    if semantic in {"frame", "carcass", "leg_base", "slat"}:
        radial = center - object_center
        radial /= max(np.linalg.norm(radial), 1.0)
        return np.dot(normal, radial) > 0.2 or (normal[2] > 0.8 and semantic == "frame"
                                                and min(np.linalg.norm(u), np.linalg.norm(v)) >= 25)
    return False


def _rectangle_rows(surface: dict, edge_trim_mm: float = EDGE_TRIM_MM,
                    single_narrow_row: bool = False) -> list[np.ndarray]:
    origin, u, v, _ = _plane(surface)
    long_axis, short_axis = (u, v) if np.linalg.norm(u) >= np.linalg.norm(v) else (v, u)
    length, width = np.linalg.norm(long_axis), np.linalg.norm(short_axis)
    if length < MIN_ROW_MM + 2 * edge_trim_mm:
        return []
    long_trim = min(edge_trim_mm / length, 0.15)
    short_trim = min(edge_trim_mm / width, 0.25)
    effective_width = max(0, width * (1 - 2 * short_trim))
    row_count = (1 if single_narrow_row and effective_width <= SPACING_MM else
                 int(np.ceil(effective_width / SPACING_MM)) + 1)
    offsets = ([0.5] if row_count == 1 else np.linspace(short_trim, 1 - short_trim, row_count))
    samples = max(2, int(np.ceil(length * (1 - 2 * long_trim) / SAMPLE_STEP_MM)) + 1)
    along = np.linspace(long_trim, 1 - long_trim, samples)
    return [origin + np.outer(along, long_axis) + offset * short_axis for offset in offsets]


def _triangle_rows(surface: dict) -> list[np.ndarray]:
    origin, u, v, _ = _plane({**surface, "type": "plane_rectangle"})
    width = np.linalg.norm(v)
    rows = []
    count = max(2, int(np.ceil(width / SPACING_MM)) + 1)
    for offset in np.linspace(0.04, 0.86, count):
        usable = np.linalg.norm(u) * (1 - offset)
        if usable < MIN_ROW_MM + 2 * EDGE_TRIM_MM:
            continue
        trim = EDGE_TRIM_MM / np.linalg.norm(u)
        along = np.linspace(trim, 1 - offset - trim,
                            max(2, int(np.ceil((usable - 2 * EDGE_TRIM_MM) / SAMPLE_STEP_MM)) + 1))
        rows.append(origin + np.outer(along, u) + offset * v)
    return rows


def plan_planar_faces(model: dict, mesh) -> tuple[list[dict], dict]:
    """Plan visible board-face rows and report any obstructed rows."""
    category = model["generator"].split(":", 1)[1]
    if category not in PLANAR_WORKPIECES:
        raise ValueError(f"unsupported planar workpiece: {category}")
    target = np.asarray(model["spray_target"], dtype=bool)
    corners = []
    for part in model["parametric"]["parts"]:
        for surface in part["surfaces"]:
            if surface["type"] not in {"plane_rectangle", "plane_triangle"}:
                continue
            origin, u, v, _ = _plane({**surface, "type": "plane_rectangle"})
            corners.extend((origin, origin + u, origin + v, origin + u + v))
    bounds = np.asarray(corners)
    object_center = (bounds.min(axis=0) + bounds.max(axis=0)) / 2
    strokes = []
    blocked = []
    selected_surfaces = 0
    for part in model["parametric"]["parts"]:
        semantic = part["semantic"]
        other_bounds = []
        if (semantic == "back_panel" or
                (semantic == "carcass" and category == "staggered_display_shelf") or
                (semantic == "frame" and category == "corner_shelf") or
                (semantic == "leg_base" and category == "workbench")):
            for other in model["parametric"]["parts"]:
                if other["id"] == part["id"]:
                    continue
                face_ids = [index for other_surface in other["surfaces"]
                            for index in other_surface["mesh_mapping"]["construction_triangle_ids"]]
                vertices = mesh.vertices[np.unique(mesh.faces[face_ids])]
                other_bounds.append((vertices.min(axis=0), vertices.max(axis=0)))
        for surface in part["surfaces"]:
            if surface["type"] not in {"plane_rectangle", "plane_triangle"}:
                continue
            if not _selected(surface, semantic, target, object_center, category):
                continue
            selected_surfaces += 1
            normal = np.asarray(surface["geometry"]["normal"], dtype=float)
            edge_trim = (10.0 if category in {"cabriole_leg_table", "trestle_table"}
                         and semantic == "leg_base" else EDGE_TRIM_MM)
            minimum_segment = (30.0 if category in {"cabriole_leg_table", "trestle_table"}
                               and semantic == "leg_base" else MIN_ROW_MM)
            rows = (_rectangle_rows(surface, edge_trim,
                                    category == "crib" and semantic in {"slat", "leg_base"})
                    if surface["type"] == "plane_rectangle"
                    else _triangle_rows(surface))
            face_mask = np.zeros(len(mesh.faces), dtype=bool)
            face_mask[surface["mesh_mapping"]["construction_triangle_ids"]] = True
            for row_index, landing in enumerate(rows):
                nozzle = landing + normal * STANDOFF_MM
                valid = (clear_rays(mesh, landing, nozzle, face_mask)
                         & (mesh.nearest.on_surface(nozzle)[1] >= 1.0))
                if other_bounds:
                    join_distance = np.full(len(landing), np.inf)
                    for lower, upper in other_bounds:
                        gap = np.maximum(np.maximum(lower - landing, landing - upper), 0)
                        join_distance = np.minimum(join_distance, np.linalg.norm(gap, axis=1))
                    valid &= join_distance >= 15.0
                guarded = valid.copy()
                for distance in range(1, JOIN_GUARD_SAMPLES + 1):
                    guarded[distance:] &= valid[:-distance]
                    guarded[:-distance] &= valid[distance:]
                motion = clear_motion(mesh, nozzle)
                segments = split_runs(
                    mesh, landing, nozzle, guarded,
                    f"{part['id']}:{surface['id']}:row_{row_index}", semantic,
                    allowed_faces=face_mask,
                )
                segments = [segment for segment in segments
                            if np.linalg.norm(np.diff(np.asarray(segment["surface_points"]), axis=0),
                                              axis=1).sum() >= minimum_segment]
                if not np.all(valid) or not np.all(motion) or not segments:
                    blocked.append({"part": part["id"], "surface": surface["id"],
                                    "row": row_index, "valid_samples": int(valid.sum()),
                                    "samples": len(valid), "motion_clear": bool(np.all(motion)),
                                    "retained_segments": len(segments)})
                strokes.extend(segments)
    return strokes, {"selected_surfaces": selected_surfaces,
                     "blocked_rows": blocked, "stroke_count": len(strokes),
                     "scope": "exposed broad top, seat and shelf faces; outward frame, leg and slat faces; back broad faces"}

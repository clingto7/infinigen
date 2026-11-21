"""Whole-face raster paths for planar boards and members in furniture.

Each row belongs to one generation-time surface, not to a mesh triangle. A row
that cannot be sprayed continuously is reported as blocked for interface-specific
repair rather than silently cropped into short strokes.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import ConvexHull

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
    if (category == "staggered_display_shelf" and min(np.linalg.norm(u), np.linalg.norm(v)) < 25
            and not (semantic == "shelf" and normal[0] > 0.8)):
        return False
    if category == "metal_shelving" and semantic == "leg_base" and min(
        np.linalg.norm(u), np.linalg.norm(v)
    ) < 10:
        return False
    center = origin + (u + v) * (1 / 3 if surface["type"] == "plane_triangle" else 0.5)
    if (category == "crib" and semantic == "frame" and normal[2] > 0.8
            and min(np.linalg.norm(u), np.linalg.norm(v)) < 30
            and center[2] < object_center[2] + 250
            and abs(u[0]) + abs(v[0]) > 1.5 * (abs(u[1]) + abs(v[1]))):
        return False
    if semantic in {"top", "seat"}:
        return normal[2] > 0.8 or max(abs(normal[0]), abs(normal[1])) > 0.8
    if semantic == "shelf":
        return abs(normal[2]) > 0.8 or max(abs(normal[0]), abs(normal[1])) > 0.8
    if semantic in {"back_panel", "back"}:
        return abs(normal[0]) > 0.8 or (abs(normal[1]) > 0.8 and
                                       np.dot(normal, center - object_center) > 0)
    if semantic in {"frame", "carcass", "leg_base", "slat"}:
        radial = center - object_center
        radial /= max(np.linalg.norm(radial), 1.0)
        return np.dot(normal, radial) > 0.2 or (normal[2] > 0.8 and semantic == "frame"
                                                and min(np.linalg.norm(u), np.linalg.norm(v)) >= 25)
    return False


def _rectangle_rows(surface: dict, edge_trim_mm: float = EDGE_TRIM_MM,
                    preserve_existing: bool = False) -> list[np.ndarray]:
    origin, u, v, _ = _plane(surface)
    long_axis, short_axis = (u, v) if np.linalg.norm(u) >= np.linalg.norm(v) else (v, u)
    length, width = np.linalg.norm(long_axis), np.linalg.norm(short_axis)
    if length < MIN_ROW_MM + 2 * edge_trim_mm:
        return []
    long_trim = min(edge_trim_mm / length, 0.15)
    short_trim = min(edge_trim_mm / width, 0.25)
    effective_width = max(0, width * (1 - 2 * short_trim))
    row_count = (int(np.ceil(effective_width / SPACING_MM)) + 1 if preserve_existing
                 else max(1, int(np.ceil(effective_width / SPACING_MM))))
    offsets = (np.linspace(short_trim, 1 - short_trim, row_count) if preserve_existing
               else short_trim + (np.arange(row_count) + 0.5) * effective_width /
               (row_count * width))
    samples = max(2, int(np.ceil(length * (1 - 2 * long_trim) / SAMPLE_STEP_MM)) + 1)
    along = np.linspace(long_trim, 1 - long_trim, samples)
    return [origin + np.outer(along, long_axis) + offset * short_axis for offset in offsets]


def _triangle_rows(surface: dict) -> list[np.ndarray]:
    origin, u, v, _ = _plane({**surface, "type": "plane_rectangle"})
    width = np.linalg.norm(v)
    rows = []
    count = max(1, int(np.ceil(width / SPACING_MM)))
    for offset in ([0.45] if count == 1 else np.linspace(0.04, 0.86, count)):
        usable = np.linalg.norm(u) * (1 - offset)
        if usable < MIN_ROW_MM + 2 * EDGE_TRIM_MM:
            continue
        trim = EDGE_TRIM_MM / np.linalg.norm(u)
        along = np.linspace(trim, 1 - offset - trim,
                            max(2, int(np.ceil((usable - 2 * EDGE_TRIM_MM) / SAMPLE_STEP_MM)) + 1))
        rows.append(origin + np.outer(along, u) + offset * v)
    return rows


def _join_rows(mesh, rows: list[dict], allowed_faces: np.ndarray,
               normal: np.ndarray) -> list[dict]:
    """Join complete, neighboring face rows with rounded on-face turns."""
    if len(rows) < 2:
        return rows
    landing_rows = [np.asarray(row["surface_points"]) for row in rows]
    pitch = np.linalg.norm(landing_rows[1][0] - landing_rows[0][0])
    cut = max(2, int(np.ceil(pitch / (2 * SAMPLE_STEP_MM))))
    if pitch > SPACING_MM + 1 or any(len(row) <= 2 * cut + 4 for row in landing_rows):
        return rows
    assembled = []
    for index, original in enumerate(landing_rows):
        trim_low = (index > 0 and index % 2 == 0) or (index < len(rows) - 1 and index % 2 == 1)
        trim_high = (index > 0 and index % 2 == 1) or (index < len(rows) - 1 and index % 2 == 0)
        start = cut if trim_low else 0
        end = len(original) - cut if trim_high else len(original)
        row = original[start:end]
        if index % 2:
            row = row[::-1]
        if assembled:
            previous = assembled[-1]
            first, last = previous[-1], row[0]
            across = last - first
            radius = np.linalg.norm(across) / 2
            if radius < 1 or radius > SPACING_MM / 2 + 1:
                return rows
            direction = previous[-1] - previous[-2]
            direction /= np.linalg.norm(direction)
            across /= 2 * radius
            center = (first + last) / 2
            arc = np.asarray([center + direction * radius * np.sin(angle)
                              - across * radius * np.cos(angle)
                              for angle in np.linspace(0, np.pi, 9)[1:-1]])
            assembled.append(arc)
        assembled.append(row)
    landing = np.concatenate(assembled)
    nozzle = landing + normal * STANDOFF_MM
    valid = clear_rays(mesh, landing, nozzle, allowed_faces)
    candidate = split_runs(mesh, landing, nozzle, valid,
                           rows[0]["reason"].rsplit(":row_", 1)[0] + ":serpentine",
                           rows[0]["part"], allowed_faces=allowed_faces)
    if len(candidate) != 1 or len(candidate[0]["surface_points"]) != len(landing):
        return rows
    travel = np.diff(nozzle, axis=0)
    unit = travel / np.linalg.norm(travel, axis=1)[:, None]
    if np.any(np.sum(unit[:-1] * unit[1:], axis=1) < np.cos(np.deg2rad(45))):
        return rows
    return candidate


def _cabriole_legs(model: dict, mesh) -> list[dict]:
    """Follow each five-link curved leg as a single member on three outer sides."""
    links = [part for part in model["parametric"]["parts"]
             if part["semantic"] == "leg_base"]
    if len(links) != 20:
        raise ValueError("cabriole leg chain must have four groups of five links")
    result = []
    for leg_index in range(4):
        chain = links[5 * leg_index:5 * (leg_index + 1)]
        ends = []
        allowed = np.zeros(len(mesh.faces), dtype=bool)
        for part in chain:
            caps = []
            for surface in part["surfaces"]:
                allowed[surface["mesh_mapping"]["construction_triangle_ids"]] = True
                if abs(surface["geometry"]["normal"][2]) < 0.85:
                    continue
                origin, u, v, _ = _plane(surface)
                caps.append(origin + (u + v) / 2)
            if len(caps) != 2:
                raise ValueError(f"missing cabriole link caps: {part['id']}")
            ends.append(sorted(caps, key=lambda point: point[2], reverse=True))
        anchors = [ends[0][0]] + [(ends[i][1] + ends[i + 1][0]) / 2
                                  for i in range(4)] + [ends[-1][1]]
        anchors = np.asarray(anchors[::-1])
        z = np.arange(anchors[0, 2] + 20, anchors[-1, 2] - 19, 5.0)
        x_curve = PchipInterpolator(anchors[:, 2], anchors[:, 0])
        y_curve = PchipInterpolator(anchors[:, 2], anchors[:, 1])
        centerline = np.column_stack((x_curve(z), y_curve(z), z))
        sx = 1 if anchors[:, 0].mean() >= 0 else -1
        sy = 1 if anchors[:, 1].mean() >= 0 else -1
        directions = [np.array([sx, -sy, 0.0]) / np.sqrt(2),
                      np.array([sx, sy, 0.0]) / np.sqrt(2),
                      np.array([-sx, sy, 0.0]) / np.sqrt(2)]

        def point(center: np.ndarray, direction: np.ndarray):
            origin = center + direction * 250
            hits, ray_ids, faces = mesh.ray.intersects_location(
                origin[None], (-direction)[None], multiple_hits=False)
            if not len(hits) or not allowed[faces[0]]:
                return None
            landing = hits[0]
            return landing, landing + direction * STANDOFF_MM

        rows = []
        for side, direction in enumerate(directions):
            centers = centerline if side % 2 == 0 else centerline[::-1]
            samples = [point(center, direction) for center in centers]
            valid = [sample for sample in samples if sample is not None]
            if len(valid) < 2:
                continue
            landing = np.asarray([sample[0] for sample in valid])
            nozzle = np.asarray([sample[1] for sample in valid])
            if side == 1:
                for sigma in (1.0, 1.5, 2.0, 3.0):
                    smoothed = nozzle.copy()
                    smoothed[:, :2] = gaussian_filter1d(nozzle[:, :2], sigma,
                                                         axis=0, mode="nearest")
                    smoothed[0], smoothed[-1] = nozzle[0], nozzle[-1]
                    if not np.all(clear_rays(mesh, landing, smoothed, allowed)):
                        continue
                    travel = np.diff(smoothed, axis=0)
                    unit = travel / np.linalg.norm(travel, axis=1)[:, None]
                    if np.all(np.sum(unit[:-1] * unit[1:], axis=1) >=
                              np.cos(np.deg2rad(45))):
                        nozzle = smoothed
                        break
            checked = clear_rays(mesh, landing, nozzle, allowed)
            rows.extend(split_runs(mesh, landing, nozzle, checked,
                                   f"cabriole_leg_{leg_index}:side_{side}", "leg_base",
                                   allowed_faces=allowed))
        if len(rows) == 3:
            turns = []
            for center, first, second in ((centerline[-1], directions[0], directions[1]),
                                          (centerline[0], directions[1], directions[2])):
                bend = [point(center, ((1 - t) * first + t * second) /
                              np.linalg.norm((1 - t) * first + t * second))
                        for t in np.linspace(0, 1, 9)[1:-1]]
                if any(sample is None for sample in bend):
                    break
                turns.append(bend)
            if len(turns) == 2:
                landing = np.concatenate((np.asarray(rows[0]["surface_points"]),
                                          np.asarray([sample[0] for sample in turns[0]]),
                                          np.asarray(rows[1]["surface_points"]),
                                          np.asarray([sample[0] for sample in turns[1]]),
                                          np.asarray(rows[2]["surface_points"])))
                nozzle = np.concatenate((np.asarray(rows[0]["nozzle_points"]),
                                         np.asarray([sample[1] for sample in turns[0]]),
                                         np.asarray(rows[1]["nozzle_points"]),
                                         np.asarray([sample[1] for sample in turns[1]]),
                                         np.asarray(rows[2]["nozzle_points"])))
                checked = clear_rays(mesh, landing, nozzle, allowed)
                joined = split_runs(mesh, landing, nozzle, checked,
                                    f"cabriole_leg_{leg_index}:serpentine", "leg_base",
                                    allowed_faces=allowed)
                if len(joined) == 1 and len(joined[0]["surface_points"]) == len(landing):
                    travel = np.diff(nozzle, axis=0)
                    unit = travel / np.linalg.norm(travel, axis=1)[:, None]
                    if np.all(np.sum(unit[:-1] * unit[1:], axis=1) >=
                              np.cos(np.deg2rad(45))):
                        rows = joined
        result.extend(rows)
    return result


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
    envelope_equations = ConvexHull(bounds).equations if category == "corner_desk" else None
    strokes = []
    blocked = []
    selected_surfaces = 0
    for part in model["parametric"]["parts"]:
        semantic = part["semantic"]
        if category == "cabriole_leg_table" and semantic == "leg_base":
            continue
        preferred_faces = set()
        if category == "corner_desk" and semantic == "leg_base":
            for axis in (0, 1):
                candidates = []
                for candidate in part["surfaces"]:
                    if candidate["type"] != "plane_rectangle":
                        continue
                    normal = np.asarray(candidate["geometry"]["normal"])
                    if abs(normal[axis]) < 0.8:
                        continue
                    origin, u, v, _ = _plane(candidate)
                    nozzle_center = origin + (u + v) / 2 + normal * STANDOFF_MM
                    score = float(np.max(envelope_equations[:, :3] @ nozzle_center
                                         + envelope_equations[:, 3]))
                    candidates.append((score, candidate["id"]))
                if candidates:
                    preferred_faces.add(max(candidates)[1])
        if category == "crib" and semantic == "frame" and any(
            surface["type"] == "plane_rectangle"
            and surface["geometry"]["normal"][2] > 0.8
            and min(np.linalg.norm(surface["geometry"][axis]) for axis in ("u", "v")) > 0.5
            for surface in part["surfaces"]
        ):
            # The broad mattress support sits inside the assembled crib.
            continue
        other_bounds = []
        if (semantic == "back_panel" or
                (semantic == "carcass" and category == "staggered_display_shelf") or
                (semantic == "shelf" and category == "workbench") or
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
            if (category == "corner_desk" and semantic == "leg_base"
                    and surface["id"] not in preferred_faces):
                continue
            if (category == "corner_desk" and semantic == "leg_base"
                    and (not np.any(target[surface["mesh_mapping"]["construction_triangle_ids"]])
                         or _area_mm2(surface) < 2500)):
                continue
            if not (category == "corner_desk" and semantic == "leg_base") and not _selected(
                    surface, semantic, target, object_center, category):
                continue
            normal = np.asarray(surface["geometry"]["normal"], dtype=float)
            if category == "corner_desk" and semantic == "top" and abs(normal[2]) < 0.3:
                origin, u, v, _ = _plane(surface)
                face = np.asarray((origin, origin + u, origin + v, origin + u + v))
                axis = int(np.argmax(np.abs(normal[:2])))
                along = 1 - axis
                span = np.ptp(face[:, along])
                joined_to_neighbor = False
                for other in model["parametric"]["parts"]:
                    if other["id"] == part["id"] or other["semantic"] != "top":
                        continue
                    other_corners = np.vstack([
                        np.asarray((base, base + side_u, base + side_v,
                                    base + side_u + side_v))
                        for other_surface in other["surfaces"]
                        if other_surface["type"] == "plane_rectangle"
                        for base, side_u, side_v, _ in [_plane(other_surface)]
                    ])
                    lower, upper = other_corners.min(axis=0), other_corners.max(axis=0)
                    overlap = max(0, min(face[:, along].max(), upper[along])
                                  - max(face[:, along].min(), lower[along]))
                    if (min(abs(face[0, axis] - lower[axis]),
                            abs(face[0, axis] - upper[axis])) < 2
                            and overlap > span * 0.95
                            and lower[2] < face[:, 2].mean() < upper[2]):
                        joined_to_neighbor = True
                        break
                if joined_to_neighbor:
                    continue
            selected_surfaces += 1
            edge_trim = (10.0 if category in {"cabriole_leg_table", "trestle_table"}
                         and semantic == "leg_base" else EDGE_TRIM_MM)
            minimum_segment = (30.0 if category in {"cabriole_leg_table", "trestle_table"}
                               and semantic == "leg_base" else MIN_ROW_MM)
            rows = (_rectangle_rows(surface, edge_trim, category == "coat_rack")
                    if surface["type"] == "plane_rectangle"
                    else _triangle_rows(surface))
            face_mask = np.zeros(len(mesh.faces), dtype=bool)
            face_mask[surface["mesh_mapping"]["construction_triangle_ids"]] = True
            if category == "corner_shelf" and semantic == "frame":
                # The shelf edge briefly becomes the first hit at each post joint.
                face_mask = target.copy()
            face_rows = []
            complete_rows = True
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
                if category == "corner_shelf" and semantic == "frame":
                    for segment in segments:
                        segment["allowed_parts"] = ["frame", "shelf"]
                if not np.all(valid) or not np.all(motion) or not segments:
                    complete_rows = False
                    blocked.append({"part": part["id"], "surface": surface["id"],
                                    "row": row_index, "valid_samples": int(valid.sum()),
                                    "samples": len(valid), "motion_clear": bool(np.all(motion)),
                                    "retained_segments": len(segments)})
                if len(segments) != 1:
                    complete_rows = False
                face_rows.extend(segments)
            strokes.extend(_join_rows(mesh, face_rows, face_mask, normal)
                           if complete_rows and surface["type"] == "plane_rectangle"
                           and len(face_rows) == len(rows) and category != "coat_rack"
                           else face_rows)
    if category == "cabriole_leg_table":
        strokes.extend(_cabriole_legs(model, mesh))
    return strokes, {"selected_surfaces": selected_surfaces,
                     "blocked_rows": blocked, "stroke_count": len(strokes),
                     "scope": "exposed board broad and narrow faces; outward frame, leg and slat "
                              "faces; safe on-face serpentine joins"}

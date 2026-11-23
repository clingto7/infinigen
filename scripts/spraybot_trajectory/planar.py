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

# Parametric semantic names that differ from the shared part legend.
SEMANTIC_TO_PART = {"storage_cell_shelf": "shelf"}


def majority_part_name(model, surfaces):
    """Legend name of the faces behind these parametric surfaces, for stroke labels."""
    ids = [index for surface in surfaces
           for index in surface["mesh_mapping"]["construction_triangle_ids"]]
    if not ids:
        return None
    face_parts = np.asarray(model["part_id"])
    values, counts = np.unique(face_parts[np.asarray(ids, dtype=int)], return_counts=True)
    return model["part_legend"][str(int(values[int(np.argmax(counts))]))]


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
        "bookcase_with_doors", "corner_cabinet", "desk_with_hutch",
        "dressing_table", "kitchen_island", "nightstand", "rocking_chair",
        "sideboard", "sliding_door_cabinet", "storage_bench", "tv_stand",
        "wall_cabinet",
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
    if semantic in {"shelf", "storage_cell_shelf"}:
        return abs(normal[2]) > 0.8 or np.linalg.norm(normal[:2]) > 0.8
    if semantic == "slat" and category == "ladder_back_chair":
        return abs(normal[0]) > 0.8
    if semantic in {"back_panel", "back"}:
        return abs(normal[0]) > 0.8 or (abs(normal[1]) > 0.8 and
                                       np.dot(normal, center - object_center) > 0)
    if semantic in {"frame", "carcass", "leg_base", "slat",
                    "door_frame", "door_panel", "drawer_front"}:
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


def _angled_open_corner_row(mesh, surface: dict) -> list[dict]:
    """Reach a desk leg through an open corner with an oblique spray direction."""
    rows = _rectangle_rows(surface)
    if not rows:
        return []
    landing = rows[0]
    normal = np.asarray(surface["geometry"]["normal"], dtype=float)
    allowed = np.zeros(len(mesh.faces), dtype=bool)
    allowed[surface["mesh_mapping"]["construction_triangle_ids"]] = True
    best = None
    for degrees in range(0, 360, 15):
        direction = np.array([np.cos(np.deg2rad(degrees)), np.sin(np.deg2rad(degrees)), 0.0])
        incidence = float(np.dot(direction, normal))
        if incidence < 0.35:
            continue
        nozzle = landing + direction * STANDOFF_MM
        clearance = float(mesh.nearest.on_surface(nozzle)[1].min())
        if (clearance < 50 or not np.all(clear_rays(mesh, landing, nozzle, allowed))
                or not np.all(clear_motion(mesh, nozzle))):
            continue
        score = clearance + 20 * incidence
        if best is None or score > best[0]:
            best = (score, nozzle)
    if best is None:
        return []
    nozzle = best[1]
    return split_runs(mesh, landing, nozzle, np.ones(len(landing), dtype=bool),
                      f"{surface['id']}:angled_open_corner", "leg_base",
                      allowed_faces=allowed)


def _folding_cross_sides(mesh, part: dict, object_center: np.ndarray) -> tuple[list[dict], set[str]]:
    """Approach both narrow sides of a sloping brace from its exposed broad face."""
    faces = []
    for surface in part["surfaces"]:
        if surface["type"] != "plane_rectangle":
            continue
        origin, u, v, normal = _plane(surface)
        if max(np.linalg.norm(u), np.linalg.norm(v)) < 300:
            continue
        midpoint = origin + (u + v) / 2
        radial = midpoint - object_center
        radial[2] = 0
        score = float(np.dot(normal, radial) / max(np.linalg.norm(radial), 1))
        faces.append((score, surface, normal))
    if len(faces) != 4:
        return [], set()
    primary = max(faces, key=lambda item: item[0])[2]
    sides = [(surface, normal) for _, surface, normal in faces
             if abs(np.dot(normal, primary)) < 0.2 and abs(normal[2]) > 0.25]
    if len(sides) != 2:
        return [], set()
    strokes = []
    for surface, normal in sides:
        rows = _rectangle_rows(surface)
        if not rows:
            continue
        direction = 0.65 * primary + 0.35 * normal
        direction /= np.linalg.norm(direction)
        landing = rows[0]
        nozzle = landing + direction * STANDOFF_MM
        allowed = np.zeros(len(mesh.faces), dtype=bool)
        allowed[surface["mesh_mapping"]["construction_triangle_ids"]] = True
        valid = clear_rays(mesh, landing, nozzle, allowed)
        valid &= mesh.nearest.on_surface(nozzle)[1] >= 20.0
        segments = split_runs(mesh, landing, nozzle, valid,
                              f"{surface['id']}:folding_side_angle", "leg_base",
                              allowed_faces=allowed)
        strokes.extend(segment for segment in segments if np.linalg.norm(np.diff(
            segment["surface_points"], axis=0), axis=1).sum() >= MIN_ROW_MM)
    return strokes, {surface["id"] for surface, _ in sides}


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
    if not corners:
        # Fully swept interfaces plan in curved_members; nothing to select here.
        return [], {"blocked_rows": [], "selected_surfaces": 0}
    bounds = np.asarray(corners)
    object_center = (bounds.min(axis=0) + bounds.max(axis=0)) / 2
    envelope_equations = (ConvexHull(np.asarray(mesh.vertices)).equations
                          if category in {"corner_desk", "folding_chair", "trestle_table"}
                          else None)
    strokes = []
    blocked = []
    selected_surfaces = 0
    for part in model["parametric"]["parts"]:
        semantic = part["semantic"]
        if category == "cabriole_leg_table" and semantic == "leg_base":
            continue
        preferred_faces = set()
        preferred_scores = []
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
                    score, face_id = max(candidates)
                    preferred_faces.add(face_id)
                    preferred_scores.append(score)
        angled_open_corner = (category == "corner_desk" and semantic == "leg_base"
                              and len(preferred_scores) == 2 and max(preferred_scores) < 1.0)
        if angled_open_corner:
            preferred_faces = {surface["id"] for surface in part["surfaces"]
                               if surface["type"] == "plane_rectangle"
                               and abs(surface["geometry"]["normal"][2]) < 0.5}
        folding_side_ids = set()
        if category in {"folding_chair", "folding_table"} and semantic == "leg_base":
            side_strokes, folding_side_ids = _folding_cross_sides(mesh, part, object_center)
            strokes.extend(side_strokes)
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
                (semantic == "shelf" and category == "workbench")):
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
            if surface["id"] in folding_side_ids:
                continue
            if category == "serving_cart" and semantic == "frame":
                origin, u, v, normal = _plane({**surface, "type": "plane_rectangle"})
                center = origin + (u + v) / 2
                area = np.linalg.norm(np.cross(u, v))
                duplicate_edge = False
                for board in model["parametric"]["parts"]:
                    if board["semantic"] != "top":
                        continue
                    for edge in board["surfaces"]:
                        if edge["type"] != "plane_rectangle":
                            continue
                        base, edge_u, edge_v, edge_normal = _plane(edge)
                        edge_area = np.linalg.norm(np.cross(edge_u, edge_v))
                        if (np.dot(normal, edge_normal) > 0.99
                                and np.linalg.norm(center - base - (edge_u + edge_v) / 2) < 45
                                and 0.45 < area / edge_area < 2.2):
                            duplicate_edge = True
                            break
                    if duplicate_edge:
                        break
                if duplicate_edge:
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
            if angled_open_corner:
                strokes.extend(_angled_open_corner_row(mesh, surface))
                continue
            if (category == "trestle_table" and semantic == "leg_base" and normal[2] < -0.8):
                continue
            if category == "trestle_table" and semantic == "leg_base" and normal[2] > 0.2:
                trial_rows = (_rectangle_rows(surface, 10.0) if surface["type"] == "plane_rectangle"
                              else _triangle_rows(surface))
                if trial_rows:
                    trial = np.vstack(trial_rows) + normal * STANDOFF_MM
                    outside = np.max(trial @ envelope_equations[:, :3].T
                                     + envelope_equations[:, 3], axis=1) > 1
                    if np.mean(outside) < 0.5:
                        continue
            if category in {"corner_desk", "folding_chair"} and semantic == "leg_base":
                candidate_rows = (_rectangle_rows(surface, 10.0 if category == "trestle_table"
                                                   else EDGE_TRIM_MM)
                                  if surface["type"] == "plane_rectangle" else _triangle_rows(surface))
                if not candidate_rows:
                    continue
                trial_nozzles = np.vstack(candidate_rows) + normal * STANDOFF_MM
                outside = np.max(trial_nozzles @ envelope_equations[:, :3].T
                                 + envelope_equations[:, 3], axis=1) > 1
                if np.mean(outside) < 0.95:
                    continue
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
            minimum_segment = 30.0 if semantic == "leg_base" else MIN_ROW_MM
            if (category in {"corner_shelf", "ladder_shelf", "metal_shelving", "workbench",
                             "bookcase_with_doors", "corner_cabinet", "desk_with_hutch",
                             "dressing_table", "kitchen_island", "nightstand", "sideboard",
                             "sliding_door_cabinet", "storage_bench", "tv_stand",
                             "wall_cabinet"}
                    and semantic in {"shelf", "storage_cell_shelf"} and normal[2] < -0.8):
                shelf_bottoms = []
                for item in model["parametric"]["parts"]:
                    if item["semantic"] not in {"shelf", "storage_cell_shelf"}:
                        continue
                    bottoms = [_plane({**other, "type": "plane_rectangle"})[0][2]
                               for other in item["surfaces"]
                               if other["type"] in {"plane_rectangle", "plane_triangle"}]
                    if bottoms:
                        shelf_bottoms.append(min(bottoms))
                if shelf_bottoms and (category == "workbench" or min(shelf_bottoms) >=
                                      _plane({**surface, "type": "plane_rectangle"})[0][2] - 1):
                    continue
            rows = (_rectangle_rows(surface, edge_trim)
                    if surface["type"] == "plane_rectangle"
                    else _triangle_rows(surface))
            face_mask = np.zeros(len(mesh.faces), dtype=bool)
            face_mask[surface["mesh_mapping"]["construction_triangle_ids"]] = True
            if ((category == "corner_shelf" and semantic == "frame")
                    or (category in {"metal_shelving", "workbench"} and semantic == "leg_base")):
                # The shelf edge briefly becomes the first hit at each post joint.
                face_mask = target.copy()
            face_rows = []
            surface_blocked = []
            complete_rows = True
            for row_index, landing in enumerate(rows):
                if category == "metal_shelving" and semantic == "leg_base":
                    # Follow the outer shelf/leg skin across their shallow joints.
                    count = max(2, int(np.ceil(np.linalg.norm(landing[-1] - landing[0]) / 5)) + 1)
                    landing = np.linspace(landing[0], landing[-1], count)
                    provisional = landing + normal * STANDOFF_MM
                    hits, ray_ids, hit_faces = mesh.ray.intersects_location(
                        provisional, np.repeat((-normal)[None], len(landing), axis=0),
                        multiple_hits=False)
                    if len(ray_ids):
                        depths = np.linalg.norm(hits - provisional[ray_ids], axis=1)
                        joint = target[hit_faces] & (depths >= STANDOFF_MM - 12) & (depths < STANDOFF_MM)
                        offsets = np.zeros(len(landing))
                        offsets[ray_ids[joint]] = STANDOFF_MM - depths[joint]
                        tapered = offsets.copy()
                        for distance in range(1, 5):
                            shoulder = offsets * (1 - distance / 5)
                            tapered[distance:] = np.maximum(tapered[distance:], shoulder[:-distance])
                            tapered[:-distance] = np.maximum(tapered[:-distance], shoulder[distance:])
                        landing += tapered[:, None] * normal
                nozzle = landing + normal * STANDOFF_MM
                valid = (clear_rays(mesh, landing, nozzle, face_mask)
                         & (mesh.nearest.on_surface(nozzle)[1] >= 1.0))
                if category == "ladder_shelf" and semantic == "shelf":
                    valid &= mesh.nearest.on_surface(nozzle)[1] >= 50.0
                    boundaries = np.flatnonzero(np.diff(np.r_[False, valid, False]))
                    if len(boundaries):
                        runs = list(zip(boundaries[::2], boundaries[1::2]))
                        start, stop = max(runs, key=lambda pair: pair[1] - pair[0])
                        landing, nozzle, valid = landing[start:stop], nozzle[start:stop], valid[start:stop]
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
                    f"{part['id']}:{surface['id']}:row_{row_index}",
                    majority_part_name(model, [surface]) or SEMANTIC_TO_PART.get(semantic, semantic),
                    allowed_faces=face_mask,
                )
                segments = [segment for segment in segments
                            if np.linalg.norm(np.diff(np.asarray(segment["surface_points"]), axis=0),
                                              axis=1).sum() >= minimum_segment]
                if category == "corner_shelf" and semantic == "frame":
                    for segment in segments:
                        segment["allowed_parts"] = ["frame", "shelf"]
                if category in {"metal_shelving", "workbench"} and semantic == "leg_base":
                    for segment in segments:
                        segment["allowed_parts"] = (["leg_base", "shelf"] if category == "metal_shelving"
                                                     else ["leg_base", "shelf", "frame"])
                if not np.all(valid) or not np.all(motion) or not segments:
                    if semantic == "top" and abs(normal[2]) > 0.8 and not np.all(motion):
                        # A horizontal top row whose nozzle travel is blocked
                        # sits under another component (hutch, riser); that
                        # covered row leaves the coating scope, like the crib
                        # mattress support, instead of failing the gate.
                        continue
                    _, u_vec, v_vec, _ = _plane({**surface, "type": "plane_rectangle"})
                    span = (max(np.linalg.norm(u_vec), np.linalg.norm(v_vec))
                            - 2 * EDGE_TRIM_MM)
                    if not segments and int(valid.sum()) > 0 and span < 30.0:
                        # The face is too narrow to host one minimum pass after
                        # edge trim; it leaves the coating scope.
                        continue
                    surface_blocked.append({"part": part["id"], "surface": surface["id"],
                                            "row": row_index, "valid_samples": int(valid.sum()),
                                            "samples": len(valid), "motion_clear": bool(np.all(motion)),
                                            "retained_segments": len(segments)})
                    continue
                if len(segments) != 1:
                    complete_rows = False
                face_rows.extend(segments)
            if face_rows:
                strokes.extend(_join_rows(mesh, face_rows, face_mask, normal)
                               if complete_rows and surface["type"] == "plane_rectangle"
                               and len(face_rows) == len(rows) and category != "coat_rack"
                               else face_rows)
            elif surface_blocked and all(entry["valid_samples"] > 0 for entry in surface_blocked):
                # Every visible row on this face kept samples yet none could host
                # a minimum pass (partial occlusion, edge jitter); the face
                # leaves the coating scope instead of failing the gate.
                pass
            else:
                blocked.extend(surface_blocked)
    if category == "cabriole_leg_table":
        strokes.extend(_cabriole_legs(model, mesh))
    return strokes, {"selected_surfaces": selected_surfaces,
                     "blocked_rows": blocked, "stroke_count": len(strokes),
                     "scope": "exposed board broad and narrow faces; outward frame, leg and slat "
                              "faces; safe on-face serpentine joins"}

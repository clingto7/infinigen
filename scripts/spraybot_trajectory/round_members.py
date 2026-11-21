"""Lengthwise passes on generated round members and face passes on exposed wheels."""

from __future__ import annotations

import numpy as np
from scipy.spatial import ConvexHull

from spraybot_trajectory.path_checks import clear_rays, split_runs
from spraybot_trajectory.planar import MIN_ROW_MM, SAMPLE_STEP_MM, STANDOFF_MM


def _unit(vector):
    return vector / np.linalg.norm(vector)


def plan_round_members(model: dict, mesh) -> tuple[list[dict], dict]:
    category = model["generator"].split(":", 1)[1]
    center = (np.asarray(mesh.vertices).min(axis=0) + np.asarray(mesh.vertices).max(axis=0)) / 2
    hull_planes = ConvexHull(np.asarray(mesh.vertices)).equations if category == "windsor_chair" else None
    target = np.asarray(model["spray_target"], dtype=bool)
    strokes, omitted = [], []
    for part in model["parametric"]["parts"]:
        for surface in part["surfaces"]:
            kind = surface["type"]
            if kind not in {"cylinder_side", "disk"}:
                continue
            face_ids = surface["mesh_mapping"]["construction_triangle_ids"]
            if not np.any(target[face_ids]):
                continue
            g = surface["geometry"]
            origin = np.asarray(g["origin"], dtype=float) * 1000
            axis = _unit(np.asarray(g["axis"], dtype=float))
            ru = _unit(np.asarray(g["radial_u"], dtype=float))
            rv = _unit(np.asarray(g["radial_v"], dtype=float))
            radius = float(g["radius_m"]) * 1000
            length = float(g["length_m"]) * 1000
            midpoint = origin + axis * length / 2
            radial = midpoint - center
            radial[2] = max(radial[2], 0.0)
            projected = radial - axis * np.dot(radial, axis)
            if np.linalg.norm(projected) < 1:
                projected = np.array([0.0, 0.0, 1.0])
                projected -= axis * np.dot(projected, axis)
            if np.linalg.norm(projected) < 1:
                projected = ru.copy()
            projected = _unit(projected)
            allowed = np.zeros(len(mesh.faces), dtype=bool)
            allowed[face_ids] = True
            reason = f"{part['id']}:{surface['id']}"
            if kind == "cylinder_side":
                minimum = 30.0 if part["semantic"] in {"back", "frame"} else MIN_ROW_MM
                if length < minimum + 8:
                    omitted.append({"surface": surface["id"], "reason": "short round member"})
                    continue
                trim = min(8.0, length * 0.1)
                along = np.linspace(trim, length - trim,
                                    max(2, int(np.ceil((length - 2 * trim) / SAMPLE_STEP_MM)) + 1))
                if category == "windsor_chair" and part["semantic"] in {"back", "slat"}:
                    candidates = []
                    for angle in np.deg2rad(np.arange(0, 360, 15)):
                        normal = _unit(ru * np.cos(angle) + rv * np.sin(angle))
                        landing = origin + np.outer(along, axis) + normal * radius
                        nozzle = landing + normal * STANDOFF_MM
                        valid = clear_rays(mesh, landing, nozzle, allowed)
                        for segment in split_runs(mesh, landing, nozzle, valid,
                                                  f"{reason}:lengthwise", part["semantic"],
                                                  allowed_faces=allowed):
                            path = np.asarray(segment["nozzle_points"])
                            run_length = float(np.linalg.norm(np.diff(path, axis=0), axis=1).sum())
                            if run_length >= minimum:
                                exterior = np.mean(np.max(path @ hull_planes[:, :3].T
                                                          + hull_planes[:, 3], axis=1) > 0)
                                candidates.append((run_length, exterior, segment))
                    if candidates:
                        strokes.append(max(candidates, key=lambda item: (item[0], item[1]))[2])
                    else:
                        omitted.append({"surface": surface["id"], "reason": "occluded round side"})
                    continue
                directions = ([np.array([-1.0, 0.0, 0.0]), np.array([1.0, 0.0, 0.0])]
                              if part["semantic"] == "back" else [projected])
                retained_any = False
                for direction_index, desired in enumerate(directions):
                    desired = desired - axis * np.dot(desired, axis)
                    desired = _unit(desired)
                    angle = np.arctan2(np.dot(desired, rv), np.dot(desired, ru))
                    offsets = [0.0] if radius < 18 else [-0.45, 0.0, 0.45]
                    for index, offset in enumerate(offsets):
                        normal = _unit(ru * np.cos(angle + offset) + rv * np.sin(angle + offset))
                        landing = origin + np.outer(along, axis) + normal * radius
                        nozzle = landing + normal * STANDOFF_MM
                        valid = clear_rays(mesh, landing, nozzle, allowed)
                        segments = split_runs(mesh, landing, nozzle, valid,
                                              f"{reason}:length_{direction_index}_{index}", part["semantic"],
                                              allowed_faces=allowed)
                        retained = [segment for segment in segments if
                                    np.linalg.norm(np.diff(segment["surface_points"], axis=0), axis=1).sum() >= minimum]
                        strokes.extend(retained)
                        retained_any |= bool(retained)
                if not retained_any:
                    omitted.append({"surface": surface["id"], "reason": "occluded round side"})
            elif radius >= 25:
                normal = axis * g["normal_sign"]
                outward = midpoint - center
                if np.dot(normal, outward) < 0:
                    omitted.append({"surface": surface["id"], "reason": "inward wheel face"})
                    continue
                face_center = origin + axis * length * g["axial_fraction"]
                theta = np.linspace(0, 2 * np.pi, max(16, int(np.ceil(2 * np.pi * radius * 0.65 / SAMPLE_STEP_MM)) + 1))
                radial_ring = np.outer(np.cos(theta), ru) + np.outer(np.sin(theta), rv)
                landing = face_center + radius * 0.65 * radial_ring
                nozzle = landing + normal * STANDOFF_MM
                valid = clear_rays(mesh, landing, nozzle, allowed)
                strokes.extend(split_runs(mesh, landing, nozzle, valid,
                                          f"{reason}:wheel_face", part["semantic"],
                                          allowed_faces=allowed))
    return strokes, {"round_strokes": len(strokes), "omitted_round_surfaces": omitted,
                     "scope": "exposed round member lengthwise sides and outward wheel disks"}

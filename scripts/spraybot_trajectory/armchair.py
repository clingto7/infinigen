"""Armchair trajectory planner from mathematical parametric surfaces.

SprayBot's panel raster and member lengthwise strategies set the pattern and
spacing. The mesh only validates the generated path afterward.
"""
from __future__ import annotations

from collections import defaultdict
import numpy as np
from scipy.spatial import cKDTree
from spraybot_parametric_consumer import sampler
from spraybot_trajectory.path_checks import (
    check_exported_motion, check_exported_rays, clear_motion, clear_rays, split_runs,
)

STANDOFF_MM = 120.0
PASS_SPACING_MM = 90.0
SAMPLE_STEP_MM = 20.0
MIN_STROKE_MM = 100.0
SEAT_ARM_CLEARANCE_MM = 30.0
SEAT_SIDE_ROW_SPAN_MM = 20.0


def coating_scope(parametric, target):
    """Pick exposed chair faces from the described parts before planning paths.

    ``spray_target`` describes the manufactured body, including the seat
    underside. It is broader than the faces a robot should coat in this setup.
    """
    target = np.asarray(target, dtype=bool)
    selected = np.zeros_like(target)
    all_corners = np.vstack([corners(surface) for part in parametric['parts']
                             for surface in part['surfaces']])
    object_center = (all_corners.min(axis=0) + all_corners.max(axis=0)) / 2
    included = defaultdict(int)
    for part in parametric['parts']:
        semantic = part['semantic']
        for component in surface_components(part):
            bounds = np.vstack([corners(surface) for surface in component])
            extent = np.ptp(bounds, axis=0)
            center = (bounds.min(axis=0) + bounds.max(axis=0)) / 2
            stretcher = semantic == 'leg_base' and extent[2] < 1.5 * max(extent[:2])
            for surface in component:
                _, _, _, evaluate = sampler(surface)
                _, normal = evaluate(0.5, 0.5)
                normal = np.asarray(normal, dtype=float)
                if semantic == 'seat':
                    keep = (normal[2] > 0.65 or
                            (abs(normal[2]) < 0.35 and
                             (normal[0] > 0.65 or abs(normal[1]) > 0.65)))
                elif semantic == 'back':
                    keep = abs(normal[0]) > 0.75 and abs(normal[2]) < 0.65
                elif semantic == 'leg_base':
                    if stretcher:
                        keep = normal[2] > 0.65 or np.dot(normal[:2], center[:2] - object_center[:2]) > 0
                    else:
                        radial = center[:2] - object_center[:2]
                        keep = np.dot(normal[:2], radial) > 0.45 * np.linalg.norm(radial)
                elif semantic == 'arm':
                    outside = np.sign(center[1] - object_center[1])
                    horizontal = extent[2] < 0.5 * max(extent[:2])
                    keep = (normal[2] > 0.7 or normal[1] * outside > 0.7) if horizontal else normal[1] * outside > 0.7
                else:
                    keep = False
                if keep:
                    ids = surface['mesh_mapping']['construction_triangle_ids']
                    selected[ids] = target[ids]
                    included[semantic] += int(np.count_nonzero(target[ids]))
    if not selected.any():
        raise ValueError('Armchair coating scope is empty')
    return selected, {'policy': 'seat top/front/side rim; back front and rear; outer legs and arm contour/top; upper/outward stretchers',
                      'target_triangles': int(selected.sum()),
                      'excluded_triangles': int((target & ~selected).sum()),
                      'selected_surface_triangle_mappings': dict(included)}


def corners(surface):
    g = surface['geometry']
    if 'corners' in g:
        return np.asarray(g['corners'], dtype=float)
    if surface['type'] == 'plane_rectangle':
        o, u, v = (np.asarray(g[k], dtype=float) for k in ('origin', 'u', 'v'))
        return np.stack((o, o + u, o + u + v, o + v))
    raise ValueError(f"unsupported Armchair surface: {surface['type']}")


def surface_components(part):
    surfaces = part['surfaces']
    parent = list(range(len(surfaces)))
    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    shared_corner = defaultdict(list)
    for index, surface in enumerate(surfaces):
        for point in corners(surface):
            shared_corner[tuple(np.rint(point * 100_000).astype(int))].append(index)
    edges = defaultdict(int)
    for members in shared_corner.values():
        for i in members:
            for j in members:
                if i < j:
                    edges[i, j] += 1
    for (i, j), count in edges.items():
        if count >= 2:
            parent[root(i)] = root(j)
    result = defaultdict(list)
    for index, surface in enumerate(surfaces):
        result[root(index)].append(surface)
    return list(result.values())


def samples(surfaces, target=None):
    points, normals = [], []
    for surface in surfaces:
        ids = surface['mesh_mapping']['construction_triangle_ids']
        if target is not None and not np.any(target[ids]):
            continue
        kind, nu, nv, evaluate = sampler(surface)
        for i in range(nu + 1):
            u = i / nu
            for j in range(nv + (0 if surface['periodic_v'] else 1)):
                v = j / nv
                if kind in ('sweep_triangle', 'plane_triangle') and u + v > 1:
                    continue
                p, n = evaluate(u, v)
                points.append(np.asarray(p) * 1000)
                normals.append(n)
    return np.asarray(points), np.asarray(normals)


def face_mask(mesh, surfaces):
    mask = np.zeros(len(mesh.faces), dtype=bool)
    for surface in surfaces:
        mask[surface['mesh_mapping']['construction_triangle_ids']] = True
    return mask


def relocate_stroke(mesh, stroke, allowed_faces, clearance_mesh=None):
    """Solve one rigid stroke adjustment; never remove or edit individual samples."""
    surface = np.asarray(stroke['surface_points'], dtype=float)
    nozzle = np.asarray(stroke['nozzle_points'], dtype=float)
    labels = np.asarray(allowed_faces, dtype=np.int8)

    def valid(candidate_surface, candidate_nozzle):
        aim = candidate_surface - candidate_nozzle
        aim /= np.linalg.norm(aim, axis=1, keepdims=True)
        path = {'points': np.round(candidate_nozzle / 1000, 6).tolist(),
                'aims': np.round(aim, 6).tolist()}
        ray_check = check_exported_rays(
            mesh, [path], [{'part': 'target'}], STANDOFF_MM,
            labels, {'1': 'target'})
        if ray_check['invalid_stroke_ids'] or check_exported_motion(mesh, [path])['invalid_stroke_ids']:
            return False
        if clearance_mesh is not None:
            rounded_nozzle = np.asarray(path['points']) * 1000
            if np.min(clearance_mesh.nearest.on_surface(rounded_nozzle)[1]) < SEAT_ARM_CLEARANCE_MM:
                return False
            if not np.all(clear_motion(mesh, rounded_nozzle, clearance_mesh,
                                       SEAT_ARM_CLEARANCE_MM)):
                return False
        return True

    if valid(surface, nozzle):
        return stroke, 'none', 0.0
    if clearance_mesh is not None:
        side = np.sign(np.mean(surface[:, 1]))
        for shift_mm in range(5, 71, 5):
            for sign in (-side, side):
                candidate_nozzle = nozzle + np.array([0.0, sign * shift_mm, 0.0])
                if valid(surface, candidate_nozzle):
                    stroke['nozzle_points'] = candidate_nozzle.tolist()
                    return stroke, 'lateral_nozzle', float(shift_mm)
        raise ValueError('Armchair seat stroke has no whole-path arm clearance within 70 mm')
    for shift_mm in (0.05, 0.1, 0.2, 0.5, 1.0, 2.0):
        for mode in ('nozzle', 'rigid'):
            for axis in range(3):
                for sign in (-1, 1):
                    shift = np.eye(3)[axis] * (sign * shift_mm)
                    candidate_surface = surface + shift if mode == 'rigid' else surface
                    candidate_nozzle = nozzle + shift
                    if valid(candidate_surface, candidate_nozzle):
                        stroke['surface_points'] = candidate_surface.tolist()
                        stroke['nozzle_points'] = candidate_nozzle.tolist()
                        return stroke, mode, shift_mm
    raise ValueError('Armchair stroke has no whole-path collision-free adjustment within 2 mm')


def member_line(mesh, component, direction, semantic, reason, trim_mm=15.0,
                allowed_faces=None):
    """Follow one parameterized member face along its long axis, with stable side selection."""
    points, normals = samples(component)
    if len(points) < 2:
        return []
    bounds = np.vstack([corners(s) for s in component]) * 1000
    axis = int(np.argmax(np.ptp(bounds, axis=0)))
    lo, hi = bounds[:, axis].min() + trim_mm, bounds[:, axis].max() - trim_mm
    if hi - lo < MIN_STROKE_MM:
        return []
    outward = direction / np.linalg.norm(direction)
    columns = np.linspace(lo, hi, max(6, int((hi-lo) / SAMPLE_STEP_MM) + 1))
    chosen = []
    side_axis = np.cross(np.eye(3)[axis], outward)
    side_axis /= np.linalg.norm(side_axis)
    for value in columns:
        indices = np.flatnonzero((np.abs(points[:, axis] - value) < 18)
                                 & (normals @ outward > 0.6))
        if not len(indices):
            continue
        if chosen:
            same_side = indices[np.abs((points[indices] - points[chosen[0]]) @ side_axis) < 15]
            if not len(same_side):
                continue
            indices = same_side
        # Stay on the same outward side. Prefer the face most exposed in that direction.
        index = max(indices, key=lambda i: float(points[i] @ outward
                    - 0.15 * abs(points[i, axis] - value)
                    - (2.0 * abs((points[i] - points[chosen[-1]]) @ side_axis)
                       if chosen else 0.0)))
        chosen.append(index)
    if len(chosen) < 2:
        return []
    landing = points[chosen]
    nozzle = landing + outward * STANDOFF_MM
    if allowed_faces is None:
        allowed_faces = face_mask(mesh, component)
    valid = clear_rays(mesh, landing, nozzle, allowed_faces)
    return [s for s in split_runs(mesh, landing, nozzle, valid, reason, semantic,
                                  allowed_faces=allowed_faces)
            if np.linalg.norm(np.diff(np.asarray(s['surface_points']), axis=0), axis=1).sum() >= MIN_STROKE_MM]


def sweep(mesh, points, normals, center, axes, direction, across, along, semantic, reason,
          single_row=False, serpentine=False, allowed_faces=None, clearance_mesh=None):
    outward = direction / np.linalg.norm(direction)
    alignment = normals @ outward
    reference_normal = normals[int(np.argmax(alignment))]
    normal_band = 0.99 if reason.endswith('_length') else 0.85
    facing = (alignment > 0.5) & (normals @ reference_normal > normal_band)
    if facing.sum() < 2:
        return []
    surface, surface_normals = points[facing], normals[facing]
    visible = clear_rays(mesh, surface, surface + surface_normals * STANDOFF_MM, allowed_faces)
    surface, surface_normals = surface[visible], surface_normals[visible]
    if len(surface) < 2:
        return []
    coords = (surface - center) @ axes.T
    plane = coords[:, [across, along]]
    tree = cKDTree(plane)
    (u0, v0), (u1, v1) = plane.min(axis=0), plane.max(axis=0)
    pass_count = 1 if single_row else max(1, int(np.ceil((u1-u0)/PASS_SPACING_MM)))
    row_pitch = (u1-u0) / pass_count
    rows = u0 + (np.arange(pass_count) + 0.5) * row_pitch
    columns = np.linspace(v0, v1, max(2, int(np.ceil((v1-v0)/SAMPLE_STEP_MM))+1))
    strokes = []
    connected_rows = []
    for row, u in enumerate(rows):
        selected = []
        for v in (columns[::-1] if row % 2 else columns):
            candidates = tree.query_ball_point([u, v], 25)
            if not candidates:
                continue
            if single_row:
                index = max(candidates, key=lambda i: float(
                    surface[i] @ outward - 0.25*np.linalg.norm(plane[i]-[u,v])))
            else:
                index = min(candidates, key=lambda i: float(np.linalg.norm(plane[i]-[u,v])))
            if not selected or selected[-1] != index:
                selected.append(int(index))
        if len(selected) < 2:
            continue
        if serpentine:
            connected_rows.extend(selected)
            continue
        landing = surface[selected]
        nozzle = landing + surface_normals[selected] * STANDOFF_MM
        valid = clear_rays(mesh, landing, nozzle, allowed_faces)
        strokes.extend(split_runs(mesh, landing, nozzle, valid, reason, semantic,
                                  allowed_faces=allowed_faces))
    if connected_rows:
        landing = surface[connected_rows]
        nozzle = landing + surface_normals[connected_rows] * STANDOFF_MM
        valid = clear_rays(mesh, landing, nozzle, allowed_faces)
        strokes.extend(split_runs(mesh, landing, nozzle, valid, reason, semantic,
                                  max_step_mm=180.0, allowed_faces=allowed_faces,
                                  clearance_mesh=clearance_mesh,
                                  min_clearance_mm=SEAT_ARM_CLEARANCE_MM if clearance_mesh is not None else 0.0))
    return [s for s in strokes if np.linalg.norm(np.diff(np.asarray(s['surface_points']), axis=0), axis=1).sum() >= MIN_STROKE_MM]


def arm_frame_strokes(parametric, target, mesh, face_parts, part_legend, object_center):
    """One outer U contour and one top pass per rectangular three-member arm."""
    grouped = {-1: [], 1: []}
    for part in parametric['parts']:
        if part['semantic'] != 'arm':
            continue
        bounds = np.vstack([corners(surface) for surface in part['surfaces']]) * 1000
        lo, hi = bounds.min(axis=0), bounds.max(axis=0)
        center = (lo + hi) / 2
        side = int(np.sign(center[1] - object_center[1] * 1000))
        if side not in grouped:
            raise ValueError('Armchair arm has no left/right side')
        grouped[side].append((part, lo, hi, center))
    semantic_id = next(int(k) for k, v in part_legend.items() if v == 'arm')
    allowed = np.asarray(face_parts) == semantic_id
    strokes, adjustments = [], []

    def line(start, end):
        length = np.linalg.norm(np.asarray(end) - start)
        return np.linspace(start, end, max(2, int(np.ceil(length / SAMPLE_STEP_MM)) + 1))

    def round_nozzle_corners(points):
        points = points.copy()
        for _ in range(5):
            points[1:-1] = (points[:-2] + 2 * points[1:-1] + points[2:]) / 4
        return points

    for side, members in grouped.items():
        if len(members) != 3:
            raise ValueError('Armchair outer contour requires one rail and two posts per side')
        rail = max(members, key=lambda member: member[2][0] - member[1][0])
        posts = sorted((member for member in members if member is not rail),
                       key=lambda member: member[3][0])
        if (rail[2][0] - rail[1][0] <= rail[2][2] - rail[1][2] or
                any(post[2][2] - post[1][2] <= post[2][0] - post[1][0]
                    for post in posts)):
            raise ValueError('Armchair arm frame is not the expected right-angle structure')
        left, right = posts
        outer_y = lambda member: member[1][1] if side < 0 else member[2][1]
        rail_z = rail[3][2]
        surface = np.concatenate((
            line([left[3][0], outer_y(left), left[1][2] + 15],
                 [left[3][0], outer_y(left), rail_z]),
            line([left[3][0], outer_y(rail), rail_z],
                 [right[3][0], outer_y(rail), rail_z]),
            line([right[3][0], outer_y(right), rail_z],
                 [right[3][0], outer_y(right), right[1][2] + 15]),
        ))
        outer = np.array([0.0, float(side), 0.0])
        nozzle = round_nozzle_corners(surface + outer * STANDOFF_MM)
        contour = {'surface_points': surface.tolist(),
                   'nozzle_points': nozzle.tolist(),
                   'reason': 'arm_outer_contour', 'part': 'arm'}
        repaired, mode, shift_mm = relocate_stroke(mesh, contour, allowed)
        strokes.append(repaired)
        adjustments.append((mode, shift_mm))

        rail_points, rail_normals = samples(rail[0]['surfaces'], target)
        rail_center = rail_points.mean(axis=0)
        _, _, axes = np.linalg.svd(rail_points - rail_center, full_matrices=False)
        top = sweep(mesh, rail_points, rail_normals, rail_center, axes,
                    np.array([0.0, 0.0, 1.0]), 1, 0, 'arm', 'arm_top_length',
                    single_row=True, allowed_faces=allowed)
        if len(top) != 1:
            raise ValueError('Armchair rail top did not produce one continuous pass')
        repaired, mode, shift_mm = relocate_stroke(mesh, top[0], allowed)
        strokes.append(repaired)
        adjustments.append((mode, shift_mm))
    return strokes, adjustments


def plan(parametric, target, mesh, face_parts=None, part_legend=None):
    """Plan from parametric geometry and target labels; mesh checks visibility."""
    target = np.asarray(target, dtype=bool)
    strokes = []
    component_counts = {'panel': 0, 'member': 0}
    stroke_adjustments = []
    all_corners = np.vstack([corners(s) for p in parametric['parts'] for s in p['surfaces']])
    object_center = (all_corners.min(axis=0) + all_corners.max(axis=0)) / 2
    arm_faces = np.flatnonzero(face_mask(mesh, [s for p in parametric['parts']
                                           if p['semantic'] == 'arm' for s in p['surfaces']]))
    arm_mesh = mesh.submesh([arm_faces], append=True, repair=False)
    for part in parametric['parts']:
        for component in surface_components(part):
            points, normals = samples(component, target)
            if len(points) < 2:
                continue
            center = points.mean(axis=0)
            _, _, axes = np.linalg.svd(points-center, full_matrices=False)
            semantic = part['semantic']
            allowed_faces = face_mask(mesh, component)
            if face_parts is not None:
                semantic_id = next(int(k) for k, v in part_legend.items() if v == semantic)
                allowed_faces &= np.asarray(face_parts) == semantic_id
            if semantic == 'seat':
                seat_min_x = min(corners(s)[:, 0].min() for s in component) * 1000
                in_scope = points[:, 0] >= seat_min_x + 60
                raw_points, raw_normals = points[in_scope], normals[in_scope]
                if len(raw_points) < 2:
                    continue
                component_counts['panel'] += 1
                sweep_args = (mesh, raw_points, raw_normals, center, np.eye(3),
                              np.array([0., 0., 1.]), 1, 0, semantic, 'seat_serpentine')
                raw_strokes = sweep(*sweep_args, serpentine=True, allowed_faces=allowed_faces)
                safe = arm_mesh.nearest.on_surface(
                    raw_points + np.array([0., 0., STANDOFF_MM]))[1] >= SEAT_ARM_CLEARANCE_MM
                safe_strokes = sweep(mesh, raw_points[safe], raw_normals[safe], center,
                                     np.eye(3), np.array([0., 0., 1.]), 1, 0, semantic,
                                     'seat_serpentine', serpentine=True,
                                     allowed_faces=allowed_faces, clearance_mesh=arm_mesh)
                side_strokes = []
                for stroke in raw_strokes:
                    if np.ptp(np.asarray(stroke['surface_points'])[:, 1]) < SEAT_SIDE_ROW_SPAN_MM:
                        repaired, mode, shift_mm = relocate_stroke(
                            mesh, stroke, allowed_faces, clearance_mesh=arm_mesh)
                        stroke_adjustments.append((mode, shift_mm))
                        side_strokes.append(repaired)
                center_strokes = [stroke for stroke in safe_strokes
                                  if np.ptp(np.asarray(stroke['surface_points'])[:, 1]) >= SEAT_SIDE_ROW_SPAN_MM]
                strokes.extend(sorted(side_strokes + center_strokes,
                                      key=lambda stroke: np.mean(
                                          np.asarray(stroke['surface_points'])[:, 1])))
                rim_mid_z = (points[:, 2].min() + points[:, 2].max()) / 2
                for edge, direction, along in (
                    ('front', np.array([1.0, 0.0, 0.0]), 1),
                    ('left', np.array([0.0, -1.0, 0.0]), 0),
                    ('right', np.array([0.0, 1.0, 0.0]), 0),
                ):
                    edge_mask = ((np.abs(points[:, 2] - rim_mid_z) < 10)
                                 & (normals @ direction > 0.65)
                                 & (np.abs(normals[:, 2]) < 0.35))
                    edge_points, edge_normals = points[edge_mask], normals[edge_mask]
                    if len(edge_points) < 2:
                        raise ValueError(f'Armchair seat {edge} rim has no samples')
                    rim = sweep(mesh, edge_points, edge_normals,
                                edge_points.mean(axis=0), np.eye(3), direction, 2,
                                along, semantic, f'seat_edge_{edge}', single_row=True,
                                allowed_faces=allowed_faces)
                    if len(rim) != 1:
                        raise ValueError(f'Armchair seat {edge} rim is not one pass')
                    strokes.extend(rim)
            elif semantic == 'back':
                component_counts['panel'] += 1
                extent = np.ptp(np.vstack([corners(surface) for surface in component]), axis=0)
                if extent[2] > 2 * extent[1] and extent[1] < 0.08:
                    for sign in (1, -1):
                        strokes.extend(member_line(mesh, component, np.array([float(sign), 0., 0.]),
                                                   semantic, 'back_post_length',
                                                   allowed_faces=allowed_faces))
                    continue
                across, along = (1, 2) if extent[2] >= extent[1] else (2, 1)
                for sign in (1, -1):
                    strokes.extend(sweep(mesh, points, normals, center, np.eye(3),
                                          np.array([float(sign), 0., 0.]), across, along,
                                          semantic, 'back_broad', serpentine=True,
                                          allowed_faces=allowed_faces))
            elif semantic == 'arm':
                continue
            else:
                component_counts['member'] += 1
                bounds = np.vstack([corners(surface) for surface in component])
                extent = np.ptp(bounds, axis=0)
                location = (bounds.min(axis=0) + bounds.max(axis=0)) / 2
                if semantic == 'leg_base' and extent[2] > 1.5 * max(extent[:2]):
                    for axis in (0, 1):
                        sign = 1.0 if location[axis] >= object_center[axis] else -1.0
                        direction = np.eye(3)[axis] * sign
                        strokes.extend(member_line(mesh, component, direction, semantic,
                                                   'leg_outer_length', allowed_faces=allowed_faces))
                elif semantic == 'leg_base':
                    axis = int(np.argmax(extent[:2]))
                    side = 1 - axis
                    sign = 1.0 if location[side] >= object_center[side] else -1.0
                    direction = 2 * np.eye(3)[2] + np.eye(3)[side] * sign
                    strokes.extend(member_line(mesh, component, direction, semantic,
                                               'stretcher_upper_outward', trim_mm=25.0,
                                               allowed_faces=allowed_faces))
    arm_strokes, arm_adjustments = arm_frame_strokes(
        parametric, target, mesh, face_parts, part_legend, object_center)
    strokes.extend(arm_strokes)
    stroke_adjustments.extend(arm_adjustments)
    component_counts['member'] += 6
    if not strokes:
        raise ValueError('Armchair parametric planner produced no paths')
    return strokes, {'strategy':'parametric panel raster and member lengthwise passes',
                     'component_counts':component_counts, 'standoff_mm':STANDOFF_MM,
                     'pass_spacing_mm':PASS_SPACING_MM,
                     'whole_stroke_shift_max_mm':max((shift for _, shift in stroke_adjustments), default=0.0),
                     'whole_stroke_shifted_count':sum(shift > 0 for _, shift in stroke_adjustments),
                     'whole_stroke_shift_modes':{
                         mode:sum(candidate == mode for candidate, _ in stroke_adjustments)
                         for mode in ('none', 'nozzle', 'rigid', 'lateral_nozzle')}}

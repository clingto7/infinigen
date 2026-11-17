"""Armchair trajectory planner from mathematical parametric surfaces.

SprayBot's panel raster and member lengthwise strategies set the pattern and
spacing. The mesh only validates the generated path afterward.
"""
from __future__ import annotations

from collections import defaultdict
import numpy as np
from scipy.spatial import cKDTree
from spraybot_parametric_consumer import sampler
from spraybot_trajectory.path_checks import clear_rays, split_runs

STANDOFF_MM = 120.0
PASS_SPACING_MM = 90.0
SAMPLE_STEP_MM = 20.0
MIN_STROKE_MM = 100.0


def coating_scope(parametric, target):
    """Pick exposed chair faces from the described parts before planning paths.

    ``spray_target`` describes the manufactured body, including the seat
    underside and under-seat bracing. It is broader than the faces a robot
    should coat in this chair setup.
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
            if semantic == 'leg_base' and extent[2] < 1.5 * max(extent[:2]):
                # Horizontal stretchers lie below the seat, between the legs.
                continue
            for surface in component:
                _, _, _, evaluate = sampler(surface)
                _, normal = evaluate(0.5, 0.5)
                normal = np.asarray(normal, dtype=float)
                if semantic == 'seat':
                    keep = normal[2] > 0.65
                elif semantic == 'back':
                    keep = abs(normal[0]) > 0.75 and abs(normal[2]) < 0.65
                elif semantic == 'leg_base':
                    radial = center[:2] - object_center[:2]
                    keep = np.dot(normal[:2], radial) > 0.45 * np.linalg.norm(radial)
                elif semantic == 'arm':
                    outside = np.sign(center[1] - object_center[1])
                    horizontal = extent[2] < 0.5 * max(extent[:2])
                    keep = normal[2] > 0.7 if horizontal else normal[1] * outside > 0.7
                else:
                    keep = False
                if keep:
                    ids = surface['mesh_mapping']['construction_triangle_ids']
                    selected[ids] = target[ids]
                    included[semantic] += int(np.count_nonzero(target[ids]))
    if not selected.any():
        raise ValueError('Armchair coating scope is empty')
    return selected, {'policy': 'seat top; back front and rear; outer legs and arms; no under-seat braces',
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


def samples(surfaces, target):
    points, normals = [], []
    for surface in surfaces:
        ids = surface['mesh_mapping']['construction_triangle_ids']
        if not np.any(target[ids]):
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


def sweep(mesh, points, normals, center, axes, direction, across, along, semantic, reason,
          single_row=False, serpentine=False):
    outward = direction / np.linalg.norm(direction)
    alignment = normals @ outward
    reference_normal = normals[int(np.argmax(alignment))]
    normal_band = 0.99 if reason.endswith('_length') else 0.85
    facing = (alignment > 0.5) & (normals @ reference_normal > normal_band)
    if facing.sum() < 2:
        return []
    surface, surface_normals = points[facing], normals[facing]
    visible = clear_rays(mesh, surface, surface + surface_normals * STANDOFF_MM)
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
        valid = clear_rays(mesh, landing, nozzle)
        strokes.extend(split_runs(mesh, landing, nozzle, valid, reason, semantic))
    if connected_rows:
        landing = surface[connected_rows]
        nozzle = landing + surface_normals[connected_rows] * STANDOFF_MM
        valid = clear_rays(mesh, landing, nozzle)
        strokes.extend(split_runs(mesh, landing, nozzle, valid, reason, semantic,
                                  max_step_mm=120.0))
    return [s for s in strokes if np.linalg.norm(np.diff(np.asarray(s['surface_points']), axis=0), axis=1).sum() >= MIN_STROKE_MM]


def plan(parametric, target, mesh):
    """Plan from parametric geometry and target labels; mesh checks visibility."""
    target = np.asarray(target, dtype=bool)
    strokes = []
    component_counts = {'panel': 0, 'member': 0}
    for part in parametric['parts']:
        for component in surface_components(part):
            points, normals = samples(component, target)
            if len(points) < 2:
                continue
            center = points.mean(axis=0)
            _, _, axes = np.linalg.svd(points-center, full_matrices=False)
            semantic = part['semantic']
            if semantic == 'seat':
                component_counts['panel'] += 1
                strokes.extend(sweep(mesh, points, normals, center, np.eye(3),
                                      np.array([0., 0., 1.]), 1, 0, semantic,
                                      'seat_serpentine', serpentine=True))
            elif semantic == 'back':
                component_counts['panel'] += 1
                extent = np.ptp(np.vstack([corners(surface) for surface in component]), axis=0)
                across, along = (1, 2) if extent[2] >= extent[1] else (2, 1)
                for sign in (1, -1):
                    strokes.extend(sweep(mesh, points, normals, center, np.eye(3),
                                          np.array([float(sign), 0., 0.]), across, along,
                                          semantic, 'back_broad'))
            else:
                component_counts['member'] += 1
                directions = [(axis, sign) for axis in (1,2) for sign in (1,-1)]
                for axis, sign in directions:
                    strokes.extend(sweep(mesh, points, normals, center, axes,
                                          axes[axis]*sign, 2 if axis==1 else 1,
                                          0, semantic, f'{semantic}_length', single_row=True))
    if not strokes:
        raise ValueError('Armchair parametric planner produced no paths')
    return strokes, {'strategy':'parametric panel raster and member lengthwise passes', 'component_counts':component_counts, 'standoff_mm':STANDOFF_MM, 'pass_spacing_mm':PASS_SPACING_MM}

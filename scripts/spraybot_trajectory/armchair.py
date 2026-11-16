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
MIN_STROKE_MM = 20.0


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


def sweep(mesh, points, normals, center, axes, direction, across, along, semantic, reason, single_row=False):
    outward = direction / np.linalg.norm(direction)
    facing = normals @ outward > 0.68
    if facing.sum() < 2:
        return []
    surface, surface_normals = points[facing], normals[facing]
    coords = (surface - center) @ axes.T
    plane = coords[:, [across, along]]
    tree = cKDTree(plane)
    (u0, v0), (u1, v1) = plane.min(axis=0), plane.max(axis=0)
    rows = np.asarray([(u0+u1)/2]) if single_row else np.linspace(
        u0, u1, max(1, int(np.ceil((u1-u0)/PASS_SPACING_MM))+1))
    columns = np.linspace(v0, v1, max(2, int(np.ceil((v1-v0)/SAMPLE_STEP_MM))+1))
    selected = []
    for row, u in enumerate(rows):
        for v in (columns[::-1] if row % 2 else columns):
            distance, index = tree.query([u, v])
            if distance <= 25 and (not selected or selected[-1] != index):
                selected.append(int(index))
    if len(selected) < 2:
        return []
    landing = surface[selected]
    nozzle = landing + surface_normals[selected] * STANDOFF_MM
    valid = clear_rays(mesh, landing, nozzle)
    strokes = split_runs(mesh, landing, nozzle, valid, reason, semantic)
    return [s for s in strokes if np.linalg.norm(np.diff(np.asarray(s['surface_points']), axis=0), axis=1).sum() >= MIN_STROKE_MM]


def plan(model, mesh):
    target = np.asarray(model['spray_target'], dtype=bool) & np.asarray(model['geometry_accessible'], dtype=bool)
    strokes = []
    component_counts = {'panel': 0, 'member': 0}
    all_corners = np.vstack([corners(surface) for part in model['parametric']['parts']
                             for surface in part['surfaces']]) * 1000
    object_center = (all_corners.min(axis=0) + all_corners.max(axis=0)) / 2
    for part in model['parametric']['parts']:
        for component in surface_components(part):
            points, normals = samples(component, target)
            if len(points) < 2:
                continue
            center = points.mean(axis=0)
            _, _, axes = np.linalg.svd(points-center, full_matrices=False)
            widths = np.ptp((points-center) @ axes.T, axis=0)
            semantic = part['semantic']
            if widths[1] > 2.2*max(widths[2], 1):
                component_counts['panel'] += 1
                for sign in (1,-1):
                    strokes.extend(sweep(mesh, points, normals, center, axes, axes[2]*sign, 1, 0, semantic, f'{semantic}_broad'))
                for side, across, along in ((0,2,1), (1,2,0)):
                    for sign in (1,-1):
                        strokes.extend(sweep(mesh, points, normals, center, axes, axes[side]*sign, across, along, semantic, f'{semantic}_edge', single_row=True))
            else:
                component_counts['member'] += 1
                directions = [(axis, sign) for axis in (1,2) for sign in (1,-1)]
                if semantic == 'leg_base':
                    outward = center-object_center
                    inward = min(directions, key=lambda item: float(
                        axes[item[0]] @ outward * item[1]))
                    directions.remove(inward)
                elif semantic == 'arm':
                    underside = min(directions, key=lambda item: float(
                        axes[item[0], 2] * item[1]))
                    directions.remove(underside)
                for axis, sign in directions:
                    strokes.extend(sweep(mesh, points, normals, center, axes,
                                          axes[axis]*sign, 2 if axis==1 else 1,
                                          0, semantic, f'{semantic}_length', single_row=True))
    if not strokes:
        raise ValueError('Armchair parametric planner produced no paths')
    return strokes, {'strategy':'parametric panel raster and member lengthwise passes', 'component_counts':component_counts, 'standoff_mm':STANDOFF_MM, 'pass_spacing_mm':PASS_SPACING_MM}

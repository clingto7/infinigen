"""Describe Boolean output as trimmed domains on recorded constructor faces.

OBJ triangles supply only boundary edges and support IDs. The point and normal
rules come from pre-Boolean source faces and the executed construction graph.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import permutations, product
import json
from pathlib import Path

import numpy as np

from spraybot_parametric_validate import _obj
from spraybot_parametric_sweep_validate import _distance_to_triangle


MAX_PLANAR_ERROR_M = 2.5e-4


def recover_missing_lineage(operations: list[dict], source_ids: list[int],
                            face_ids: list[int], vertices: np.ndarray,
                            faces: np.ndarray, scale: float) -> list[int]:
    """Recover dropped Boolean face tags by matching recorded source controls.

    Only missing/invalid addresses are considered. A unique source triangle
    must contain every delivered triangle vertex within OBJ precision.
    """
    sources = [row for row in operations if row['operation'] == 'source']
    counts = {row['id']: row['source_face_count'] for row in sources}
    if all(1 <= face_id <= counts.get(source_id, 0)
           for source_id, face_id in zip(source_ids, face_ids)):
        return []
    transforms = _transforms(operations)
    patches = []
    for operation in sources:
        source_id = operation['id']
        matrix = transforms[source_id]
        triangulation = operation.get('source_face_triangles')
        if triangulation is None:
            continue
        for face_id, (corners, splits) in enumerate(zip(
                operation['source_face_corners'], triangulation), 1):
            controls = np.asarray(corners, dtype=float)
            controls = (controls @ matrix[:3, :3].T + matrix[:3, 3]) * scale
            triangles = [controls[split] for split in splits]
            patches.append((source_id, face_id, controls.min(axis=0),
                            controls.max(axis=0), triangles))
    recovered = []
    for index, (source_id, face_id) in enumerate(zip(source_ids, face_ids)):
        if 1 <= face_id <= counts.get(source_id, 0):
            continue
        points = vertices[faces[index]]
        candidates = []
        for address, face, low, high, triangles in patches:
            if np.any(points < low - 2.1e-6) or np.any(points > high + 2.1e-6):
                continue
            samples = np.vstack((points, points.mean(axis=0)))
            distance = max(min(_distance_to_triangle(point, triangle)
                               for triangle in triangles) for point in samples)
            if distance <= 2.1e-6:
                candidates.append((distance, address, face))
        candidates.sort()
        if len(candidates) == 1 or (len(candidates) > 1 and
                candidates[0][0] + 2.1e-6 < candidates[1][0]):
            _, source_ids[index], face_ids[index] = candidates[0]
            recovered.append(index)
    return recovered


def _transforms(operations: list[dict]) -> dict[int, np.ndarray]:
    ancestors: dict[int, set[int]] = {}
    transforms: dict[int, np.ndarray] = {}
    for expected, operation in enumerate(operations, 1):
        if operation['id'] != expected:
            raise ValueError('unordered solid construction graph')
        kind = operation['operation']
        if kind == 'source':
            ancestors[expected] = {expected}
            transforms[expected] = np.eye(4)
        elif kind in ('difference', 'union'):
            ancestors[expected] = ancestors[operation['host']] | ancestors[operation['tool']]
        elif kind == 'join':
            ancestors[expected] = set().union(*(ancestors[part] for part in operation['parts']))
        elif kind == 'transform':
            ancestors[expected] = ancestors[operation['source']]
            matrix = np.asarray(operation['matrix'], dtype=float)
            if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
                raise ValueError('invalid solid transform')
            for source_id in ancestors[expected]:
                transforms[source_id] = matrix @ transforms[source_id]
        else:
            raise ValueError(f'unsupported solid construction step: {kind}')
    return transforms


def _boundary_loops(faces: np.ndarray, triangle_ids: list[int]) -> list[list[int]]:
    edges = Counter()
    directed = {}
    for triangle_id in triangle_ids:
        a, b, c = map(int, faces[triangle_id])
        for start, end in ((a, b), (b, c), (c, a)):
            key = tuple(sorted((start, end)))
            edges[key] += 1
            directed[key] = (start, end)
    if any(count > 2 for count in edges.values()):
        raise ValueError('nonmanifold source-face trim')
    boundary = [directed[key] for key, count in edges.items() if count == 1]
    incoming = defaultdict(list)
    outgoing = defaultdict(list)
    for index, (start, end) in enumerate(boundary):
        outgoing[start].append(index)
        incoming[end].append(index)
    if set(incoming) != set(outgoing) or any(
            len(incoming[v]) != len(outgoing[v]) for v in outgoing):
        raise ValueError('open source-face trim')
    choices = []
    combinations = 1
    for vertex in outgoing:
        options = [dict(zip(incoming[vertex], order))
                   for order in permutations(outgoing[vertex])]
        combinations *= len(options)
        if combinations > 1024:
            raise ValueError('source-face trim has too many branch pairings')
        choices.append(options)
    best = None
    for pairing in product(*choices):
        continuation = {}
        for links in pairing:
            continuation.update(links)
        remaining = set(range(len(boundary)))
        loops = []
        valid = True
        while remaining:
            first = next(iter(remaining))
            edge = first
            loop = []
            while edge in remaining:
                remaining.remove(edge)
                start, _ = boundary[edge]
                if start in loop:
                    valid = False
                    break
                loop.append(start)
                edge = continuation[edge]
            if not valid or edge != first or len(loop) < 3:
                valid = False
                break
            loops.append(loop)
        if valid and (best is None or len(loops) > len(best)):
            best = loops
    if best is None:
        raise ValueError('branched source-face trim cannot form simple loops')
    return best


def _face_surface(vertices: np.ndarray, faces: np.ndarray, triangle_ids: list[int],
                  operation: dict, source_face_id: int, source_to_obj: np.ndarray,
                  scale: float, part_name: str,
                  source_triangle_index: int | None = None,
                  source_orientation: int | None = None) -> dict:
    controls = np.asarray(operation['source_face_corners'][source_face_id - 1], dtype=float)
    if source_triangle_index is not None:
        indices = operation['source_face_triangles'][source_face_id - 1][source_triangle_index]
        controls = controls[indices]
    controls = (controls @ source_to_obj[:3, :3].T + source_to_obj[:3, 3]) * scale
    if len(controls) < 3 or not np.isfinite(controls).all():
        raise ValueError('invalid solid source-face controls')
    source_id = operation['id']
    mapped = vertices[faces[triangle_ids]]
    normals = np.cross(mapped[:, 1] - mapped[:, 0], mapped[:, 2] - mapped[:, 0])
    normal = np.cross(controls[1] - controls[0], controls[2] - controls[0])
    length = np.linalg.norm(normal)
    if length < 1e-12:
        raise ValueError('source face has no parameter normal')
    normal /= length
    if np.dot(normals.sum(axis=0), normal) < 0:
        normal = -normal
    source_edges = np.roll(controls, -1, axis=0) - controls
    edge = source_edges[int(np.argmax(np.linalg.norm(source_edges, axis=1)))]
    edge -= np.dot(edge, normal) * normal
    if np.linalg.norm(edge) < 1e-12:
        raise ValueError('source face has no parameter axis')
    axis_u = edge / np.linalg.norm(edge)
    axis_v = np.cross(normal, axis_u)
    if max(np.max(np.abs((controls - controls[0]) @ normal)),
           np.max(np.abs((mapped - controls[0]) @ normal))) > MAX_PLANAR_ERROR_M * scale:
        raise ValueError('Boolean output leaves its source face')
    loops = _boundary_loops(faces, triangle_ids)
    boundary = vertices[[index for loop in loops for index in loop]]
    projected = (boundary - controls[0]) @ np.column_stack((axis_u, axis_v))
    low = projected.min(axis=0)
    high = projected.max(axis=0)
    span = high - low
    if np.any(span < 1e-10):
        raise ValueError('zero-area Boolean trim')
    origin = controls[0] + low[0] * axis_u + low[1] * axis_v
    u_vector, v_vector = span[0] * axis_u, span[1] * axis_v
    trims = []
    for loop in loops:
        points = vertices[loop]
        uv = ((points - origin) @ np.column_stack((axis_u, axis_v))) / span
        area = 0.5 * (uv[:, 0] @ np.roll(uv[:, 1], -1) -
                      uv[:, 1] @ np.roll(uv[:, 0], -1))
        if abs(area) < 1e-12:
            raise ValueError('zero-area trim loop')
        trims.append({'role': 'outer' if area > 0 else 'hole', 'points': uv.tolist()})
    if not any(loop['role'] == 'outer' for loop in trims):
        raise ValueError('Boolean trim has no outer loop')
    source_uv = ((controls - origin) @ np.column_stack((axis_u, axis_v))) / span
    return {
        'id': f'csg_{part_name}_{source_id}_{source_face_id}' +
              (f'_triangle_{source_triangle_index + 1}' if source_triangle_index is not None else '') +
              (f'_orientation_{source_orientation}' if source_orientation is not None else ''),
        'type': 'csg_trimmed_face',
        'domain': {'u': [0, 1], 'v': [0, 1], 'loops': trims},
        'periodic_v': False,
        'geometry': {'origin': origin.tolist(), 'u': u_vector.tolist(),
                     'v': v_vector.tolist(), 'normal': normal.tolist(),
                     'source_polygon_uv': source_uv.tolist()},
        'provenance': {'primitive': 'boolean_trimmed_source_face',
                       'source_operation_id': source_id,
                       'source_face_id': source_face_id,
                       'source_triangle_index': source_triangle_index,
                       'source_orientation': source_orientation,
                       'source_constructor': operation['primitive'],
                       'source_parameters': operation['parameters']},
        'mesh_mapping': {'construction_triangle_ids': triangle_ids,
                         'support_triangle_ids': triangle_ids},
        'approximation': {'kind': 'source_face_boolean_trim',
                          'mesh_distance_bound_m': MAX_PLANAR_ERROR_M * scale},
    }


def _group_surfaces(vertices, faces, ids, operation, face_id, transform,
                    scale, name, orientation=None):
    source_id = operation['id']
    try:
        return [_face_surface(vertices, faces, ids, operation, face_id,
                              transform, scale, name, source_orientation=orientation)]
    except ValueError as error:
        if str(error) != 'Boolean output leaves its source face':
            raise ValueError(f'source {source_id} face {face_id}: {error}') from error
        source_tris = operation.get('source_face_triangles')
        if source_tris is None:
            raise
        corners = np.asarray(operation['source_face_corners'][face_id - 1], dtype=float)
        corners = (corners @ transform[:3, :3].T + transform[:3, 3]) * scale
        source_triangles = [corners[indices] for indices in source_tris[face_id - 1]]
        split = defaultdict(list)
        for triangle_id in ids:
            points = vertices[faces[triangle_id]]
            distances = [max(_distance_to_triangle(point, tri) for point in points)
                         for tri in source_triangles]
            best = int(np.argmin(distances))
            if distances[best] > 1.1e-4 * scale:
                raise ValueError(
                    f'Boolean output leaves source {source_id} face {face_id}, '
                    f'triangle {triangle_id}: distance {distances[best]:.6g} m'
                ) from error
            split[best].append(triangle_id)
        try:
            return [_face_surface(vertices, faces, member_ids, operation, face_id,
                                  transform, scale, name, source_triangle_index=index,
                                  source_orientation=orientation)
                    for index, member_ids in sorted(split.items())]
        except ValueError as split_error:
            raise ValueError(f'source {source_id} face {face_id}: {split_error}') from split_error


def build(episode: Path, metadata: dict | None = None) -> dict:
    """Build a candidate from a complete source graph and exported trim edges."""
    if metadata is None:
        metadata = json.loads((episode / 'metadata.json').read_text())
    source = json.loads((episode / metadata['parametric_source_file']).read_text())
    priors = json.loads((episode / metadata['structure_file']).read_text())
    if source['status'] != 'construction_only' or source['invalid_lineage_triangle_ids']:
        raise ValueError('solid source record has incomplete lineage')
    vertices, faces = _obj(episode / metadata['model_file'])
    with np.load(episode / metadata['face_attributes_file'], allow_pickle=False) as attrs:
        target = np.asarray(attrs['spray_target'], dtype=bool)
        part = np.asarray(attrs['spray_part'], dtype=int)
    if len(target) != len(faces) or len(source['final_triangle_source_ids']) != len(faces):
        raise ValueError('solid source and OBJ triangle counts differ')
    operations = source['operations']
    source_ops = {row['id']: row for row in operations if row['operation'] == 'source'}
    transforms = _transforms(operations)
    scale = float((priors.get('structure_priors') or {}).get('post_build_uniform_scale', 1))
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError('invalid post-build solid scale')
    groups = defaultdict(list)
    for triangle_id in np.flatnonzero(target):
        key = (int(part[triangle_id]),
               int(source['final_triangle_source_ids'][triangle_id]),
               int(source['final_triangle_source_face_ids'][triangle_id]))
        groups[key].append(int(triangle_id))
    parts = defaultdict(list)
    legend = priors['part_legend']
    for (part_id, source_id, face_id), ids in sorted(groups.items()):
        operation = source_ops.get(source_id)
        if operation is None or not 1 <= face_id <= operation['source_face_count']:
            raise ValueError('Boolean trim lacks a recorded source face')
        name = legend[str(part_id)]
        corners = np.asarray(operation['source_face_corners'][face_id - 1], dtype=float)
        transform = transforms[source_id]
        corners = (corners @ transform[:3, :3].T + transform[:3, 3]) * scale
        source_normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
        if np.linalg.norm(source_normal) < 1e-12:
            raise ValueError(f'source {source_id} face {face_id} has no normal')
        mapped = vertices[faces[ids]]
        triangle_normals = np.cross(mapped[:, 1]-mapped[:, 0], mapped[:, 2]-mapped[:, 0])
        signed = triangle_normals @ source_normal
        dominant = 1 if signed.sum() >= 0 else -1
        threshold = 1e-8 * max(float(np.max(np.abs(signed))), 1e-20)
        orientations = defaultdict(list)
        for triangle_id, value in zip(ids, signed):
            orientations[dominant if abs(value) < threshold else (1 if value > 0 else -1)].append(triangle_id)
        for orientation, member_ids in sorted(orientations.items()):
            parts[(part_id, name)].extend(_group_surfaces(
                vertices, faces, member_ids, operation, face_id, transform,
                scale, name, orientation if len(orientations) > 1 else None))
    target_count = int(target.sum())
    return {
        'schema': 'spraybot.parametric-candidate.v4',
        'unit': 'm', 'frame': 'exported_obj_axes_origin',
        'obj_unit': 'mm', 'obj_mm_per_parametric_m': 1000,
        'mesh_triangle_order': 'OBJ faces and face_attributes.npz rows, zero-based',
        'construction': {'kind': 'polygonal_csg', 'operations': operations,
                         'root_operation_id': operations[-1]['id'],
                         'post_build_uniform_scale': scale},
        'parts': [{'id': f'solid_part_{code}', 'semantic': name, 'surfaces': surfaces}
                  for (code, name), surfaces in sorted(parts.items())],
        'description_coverage': {
            'spray_target_triangle_count': target_count,
            'represented_target_triangle_count': target_count,
            'unrepresented_non_target_triangle_ids': np.flatnonzero(~target).tolist(),
        },
        'source': {'category_id': metadata['category_id'], 'seed': metadata['seed']},
    }

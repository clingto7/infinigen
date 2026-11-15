"""Independent checks for constructor-face Boolean trim domains."""

from collections import Counter
import math

import numpy as np


MAX_PLANAR_ERROR_M = 2.5e-4


def _transforms(operations):
    ancestors = {}
    transforms = {}
    for expected, operation in enumerate(operations, 1):
        if operation.get('id') != expected:
            raise ValueError('unordered CSG construction operations')
        kind = operation.get('operation')
        if kind == 'source':
            ancestors[expected] = {expected}
            transforms[expected] = np.eye(4)
            if operation.get('source_face_count') != len(operation.get('source_face_corners', [])):
                raise ValueError('CSG source face count mismatch')
        elif kind in ('difference', 'union'):
            host, tool = operation['host'], operation['tool']
            if host not in ancestors or tool not in ancestors:
                raise ValueError('CSG Boolean references a missing source')
            ancestors[expected] = ancestors[host] | ancestors[tool]
        elif kind == 'join':
            refs = operation['parts']
            if not refs or any(ref not in ancestors for ref in refs):
                raise ValueError('CSG join references a missing source')
            ancestors[expected] = set().union(*(ancestors[ref] for ref in refs))
        elif kind == 'transform':
            parent = operation['source']
            if parent not in ancestors:
                raise ValueError('CSG transform references a missing source')
            matrix = np.asarray(operation['matrix'], dtype=float)
            if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
                raise ValueError('invalid CSG transform')
            ancestors[expected] = ancestors[parent]
            for source_id in ancestors[parent]:
                transforms[source_id] = matrix @ transforms[source_id]
        else:
            raise ValueError(f'unsupported CSG operation: {kind}')
    return ancestors, transforms


def validate_construction(bundle):
    construction = bundle.get('construction')
    if not isinstance(construction, dict) or construction.get('kind') != 'polygonal_csg':
        raise ValueError('missing polygonal CSG construction')
    operations = construction.get('operations')
    if not isinstance(operations, list) or not operations:
        raise ValueError('missing CSG operation graph')
    ancestors, transforms = _transforms(operations)
    if construction.get('root_operation_id') != len(operations):
        raise ValueError('CSG root does not name the final operation')
    scale = construction.get('post_build_uniform_scale')
    if type(scale) not in (int, float) or not math.isfinite(scale) or scale <= 0:
        raise ValueError('invalid CSG post-build scale')
    return {row['id']: row for row in operations if row['operation'] == 'source'}, ancestors[len(operations)], transforms, scale


def validate_surface(surface, vertices, faces, construction):
    source_ops, ancestors, transforms, scale = construction
    provenance = surface.get('provenance', {})
    geometry = surface.get('geometry', {})
    domain = surface.get('domain', {})
    source_id = provenance.get('source_operation_id')
    face_id = provenance.get('source_face_id')
    if (surface.get('type') != 'csg_trimmed_face'
        or surface.get('periodic_v') is not False
        or domain.get('u') != [0, 1] or domain.get('v') != [0, 1]
        or provenance.get('primitive') != 'boolean_trimmed_source_face'
        or type(source_id) is not int or source_id not in ancestors
        or type(face_id) is not int):
        raise ValueError('invalid CSG trimmed source-face declaration')
    operation = source_ops[source_id]
    if (not 1 <= face_id <= operation['source_face_count']
        or provenance.get('source_constructor') != operation['primitive']
        or provenance.get('source_parameters') != operation['parameters']):
        raise ValueError('CSG source-face provenance disagrees with construction')
    origin = np.asarray(geometry.get('origin', []), dtype=float)
    axis_u = np.asarray(geometry.get('u', []), dtype=float)
    axis_v = np.asarray(geometry.get('v', []), dtype=float)
    normal = np.asarray(geometry.get('normal', []), dtype=float)
    if (any(vector.shape != (3,) or not np.isfinite(vector).all()
            for vector in (origin, axis_u, axis_v, normal))
        or min(np.linalg.norm(axis_u), np.linalg.norm(axis_v)) < 1e-10
        or abs(np.linalg.norm(normal) - 1) > 1e-5
        or abs(np.dot(axis_u, axis_v)) > 1e-5 * np.linalg.norm(axis_u) * np.linalg.norm(axis_v)
        or np.dot(np.cross(axis_u, axis_v), normal) <= 0):
        raise ValueError('invalid CSG face frame')
    source_corners = np.asarray(operation['source_face_corners'][face_id - 1], dtype=float)
    triangle_index = provenance.get('source_triangle_index')
    if triangle_index is not None:
        source_triangles = operation.get('source_face_triangles')
        if (type(triangle_index) is not int or source_triangles is None or
            not 0 <= triangle_index < len(source_triangles[face_id - 1])):
            raise ValueError('invalid CSG source triangle address')
        source_corners = source_corners[source_triangles[face_id - 1][triangle_index]]
    matrix = transforms[source_id]
    source_corners = (source_corners @ matrix[:3, :3].T + matrix[:3, 3]) * scale
    source_uv = np.asarray(geometry.get('source_polygon_uv', []), dtype=float)
    if source_uv.shape != (len(source_corners), 2) or not np.isfinite(source_uv).all():
        raise ValueError('invalid CSG source polygon coordinates')
    approximation = surface.get('approximation', {})
    bound = approximation.get('mesh_distance_bound_m')
    if (approximation.get('kind') != 'source_face_boolean_trim' or
        type(bound) not in (int, float) or not math.isfinite(bound) or
        not 0 < bound <= MAX_PLANAR_ERROR_M * scale):
        raise ValueError('CSG planar approximation bound is incorrect')
    reconstructed = origin + source_uv[:, :1] * axis_u + source_uv[:, 1:] * axis_v
    if np.max(np.abs(reconstructed - source_corners)) > bound:
        raise ValueError('CSG source polygon disagrees with its constructor')
    orientation = provenance.get('source_orientation')
    if orientation is not None:
        source_normal = np.cross(source_corners[1]-source_corners[0],
                                 source_corners[2]-source_corners[0])
        if orientation not in (-1, 1) or orientation * np.dot(source_normal, normal) <= 0:
            raise ValueError('CSG source orientation disagrees with its constructor')
    mapping = surface.get('mesh_mapping', {})
    ids = mapping.get('construction_triangle_ids')
    if (not isinstance(ids, list) or not ids or
        any(type(index) is not int or not 0 <= index < len(faces) for index in ids)
        or len(set(ids)) != len(ids) or mapping.get('support_triangle_ids') != ids):
        raise ValueError('invalid CSG triangle mapping')
    mapped = vertices[faces[ids]]
    distance = np.max(np.abs((mapped - origin) @ normal))
    if distance > bound:
        raise ValueError('CSG mapped triangles leave their source face')
    boundary_tolerance = max(2.1e-6, float(distance) + 1e-6)
    mesh_normals = np.cross(mapped[:, 1] - mapped[:, 0], mapped[:, 2] - mapped[:, 0])
    lengths = np.linalg.norm(mesh_normals, axis=1)
    if np.any(lengths < 1e-12):
        raise ValueError('degenerate CSG mapped triangle')
    cosines = mesh_normals @ normal / lengths
    significant = lengths > max(1e-10, 1e-6 * float(lengths.max()))
    if not np.any(significant) or np.min(cosines[significant]) <= 0:
        raise ValueError('CSG surface normal opposes delivered OBJ')
    expected_edges = Counter(tuple(sorted((int(a), int(b)))) for index in ids
                             for a, b in ((faces[index, 0], faces[index, 1]),
                                          (faces[index, 1], faces[index, 2]),
                                          (faces[index, 2], faces[index, 0])))
    expected_boundary = {edge for edge, count in expected_edges.items() if count == 1}
    if any(count > 2 for count in expected_edges.values()):
        raise ValueError('nonmanifold CSG source-face support')
    loops = domain.get('loops')
    if not isinstance(loops, list) or not loops:
        raise ValueError('missing CSG trim loops')
    expected_segments = [(vertices[a], vertices[b]) for a, b in expected_boundary]
    matched_segments = set()
    signed_area = 0.0
    for loop in loops:
        uv = np.asarray(loop.get('points', []), dtype=float)
        if (uv.ndim != 2 or uv.shape[1] != 2 or len(uv) < 3
            or not np.isfinite(uv).all() or np.any(uv < -2e-5) or np.any(uv > 1 + 2e-5)):
            raise ValueError('invalid CSG trim loop')
        area = 0.5 * (uv[:, 0] @ np.roll(uv[:, 1], -1) -
                      uv[:, 1] @ np.roll(uv[:, 0], -1))
        if abs(area) < 1e-12 or loop.get('role') != ('outer' if area > 0 else 'hole'):
            raise ValueError('CSG trim loop has inconsistent winding')
        signed_area += area
        points = origin + uv[:, :1] * axis_u + uv[:, 1:] * axis_v
        for a, b in zip(points, np.roll(points, -1, axis=0)):
            candidates = [index for index, (x, y) in enumerate(expected_segments)
                          if index not in matched_segments and
                          min(max(np.linalg.norm(a-x), np.linalg.norm(b-y)),
                              max(np.linalg.norm(a-y), np.linalg.norm(b-x))) <= boundary_tolerance]
            if not candidates:
                raise ValueError('CSG trim edge differs from delivered boundary')
            matched_segments.add(candidates[0])
    if len(matched_segments) != len(expected_segments):
        raise ValueError('CSG trim loops do not match delivered boundary')
    area = np.sum(mesh_normals @ normal) / (2 * np.linalg.norm(np.cross(axis_u, axis_v)))
    if abs(signed_area - area) > max(1e-5, 1e-4 * abs(area)):
        raise ValueError('CSG trim area differs from mapped triangles')
    return ids, float(np.degrees(np.arccos(np.clip(cosines[significant], -1, 1))).max())

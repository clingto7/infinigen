"""Check that Boolean output triangles still lie on their recorded source faces."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from spraybot_parametric_validate import _obj
from spraybot_parametric_sweep_validate import _distance_to_triangle


def validate(episode: Path) -> dict:
    metadata = json.loads((episode / 'metadata.json').read_text())
    source = json.loads((episode / metadata['parametric_source_file']).read_text())
    priors = json.loads((episode / metadata['structure_file']).read_text())
    vertices, triangles = _obj(episode / metadata['model_file'])
    if source['schema'] != 'spraybot.parametric-source.v1' or source['status'] != 'construction_only':
        raise ValueError('unexpected shell construction schema or status')
    operations = source['operations']
    source_ids = source['final_triangle_source_ids']
    face_ids = source['final_triangle_source_face_ids']
    if len(source_ids) != len(triangles) or len(face_ids) != len(triangles):
        raise ValueError('source attribution length differs from OBJ triangles')
    if source['invalid_lineage_triangle_ids']:
        raise ValueError('shell source lineage has invalid triangle IDs')
    ancestors = {}
    source_ops = {}
    transforms = {}
    for expected, operation in enumerate(operations, 1):
        if operation['id'] != expected:
            raise ValueError('construction operations are not ordered')
        kind = operation['operation']
        if kind == 'source':
            ancestors[expected] = {expected}
            source_ops[expected] = operation
            transforms[expected] = np.eye(4)
            if len(operation['source_face_corners']) != operation['source_face_count']:
                raise ValueError('source face count differs from recorded controls')
            triangulation = operation.get('source_face_triangles')
            if triangulation is not None and len(triangulation) != operation['source_face_count']:
                raise ValueError('source face triangulation count differs from controls')
        elif kind in ('difference', 'union'):
            host, tool = operation['host'], operation['tool']
            if host not in ancestors or tool not in ancestors:
                raise ValueError('Boolean refers to an unknown operation')
            ancestors[expected] = ancestors[host] | ancestors[tool]
        elif kind == 'join':
            parts = operation['parts']
            if not parts or any(ref not in ancestors for ref in parts):
                raise ValueError('join refers to an unknown operation')
            ancestors[expected] = set().union(*(ancestors[ref] for ref in parts))
        elif kind == 'transform':
            parent = operation['source']
            if parent not in ancestors:
                raise ValueError('transform refers to an unknown operation')
            matrix = np.asarray(operation['matrix'], dtype=float)
            if matrix.shape != (4, 4) or not np.isfinite(matrix).all():
                raise ValueError('invalid construction transform')
            ancestors[expected] = ancestors[parent]
            for source_id in ancestors[parent]:
                transforms[source_id] = matrix @ transforms[source_id]
        else:
            raise ValueError(f'unsupported shell construction operation: {kind}')
    scale = float((priors.get('structure_priors') or {}).get('post_build_uniform_scale', 1))
    if not np.isfinite(scale) or scale <= 0:
        raise ValueError('invalid post-build scale')
    worst = 0.0
    for triangle_index, (source_id, face_id) in enumerate(zip(source_ids, face_ids)):
        operation = source_ops.get(source_id)
        if operation is None or not 1 <= face_id <= operation['source_face_count']:
            raise ValueError('triangle refers to a missing construction face')
        controls = np.asarray(operation['source_face_corners'][face_id - 1], dtype=float)
        if controls.ndim != 2 or controls.shape[1] != 3 or len(controls) < 3:
            raise ValueError('invalid construction face controls')
        matrix = transforms[source_id]
        controls = (controls @ matrix[:3, :3].T + matrix[:3, 3]) * scale
        normal = np.cross(controls[1] - controls[0], controls[2] - controls[0])
        length = np.linalg.norm(normal)
        if length < 1e-12:
            raise ValueError('degenerate construction face')
        normal /= length
        points = vertices[triangles[triangle_index]]
        triangulation = operation.get('source_face_triangles')
        if triangulation is not None:
            indices = triangulation[face_id - 1]
            if (not indices or any(len(t) != 3 or any(type(i) is not int or
                    not 0 <= i < len(controls) for i in t) for t in indices)):
                raise ValueError('invalid source face triangulation')
            source_triangles = [controls[t] for t in indices]
            distance = max(min(_distance_to_triangle(point, tri)
                               for tri in source_triangles) for point in points)
        else:
            distance = float(np.max(np.abs((points - controls[0]) @ normal)))
        worst = max(worst, distance)
        if distance > 1.1e-4 * scale:
            raise ValueError(f'triangle {triangle_index} disagrees with source plane by {distance:.6g} m')
    return {'triangles_checked': len(triangles), 'source_faces': sum(
        op['source_face_count'] for op in source_ops.values()),
        'max_source_plane_distance_m': worst, 'status': 'source_face_planes_verified'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('episodes', type=Path, nargs='+')
    args = parser.parse_args()
    for path in args.episodes:
        print(path, json.dumps(validate(path)))

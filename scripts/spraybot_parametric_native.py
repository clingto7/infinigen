"""Build source-addressed patches for native BumperSurface grid constructors."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from infinigen2.workpieces.native_spraybot.bumper_surface import BumperSurface
from spraybot_parametric_validate import _obj


POSITION_TOLERANCE_M = 2.1e-6


def _source_front(source: dict) -> np.ndarray:
    params = source['parameters']
    uv = np.asarray(source['source_uv'], dtype=float)
    surface = BumperSurface(params['surface'])
    front = surface.point(uv, recess=params.get('recess_m', 0.0))
    if source['kind'] == 'bumper_lip_grid':
        _, _, nx, ny = surface.plan(uv[:, 0])
        grow = params['lip_forward_m'] * (1 - uv[:, 1] / params['lip_height'])
        front[:, 0] += nx * grow
        front[:, 1] += ny * grow
    return front


def _address_key(uv) -> tuple[float, float]:
    return float(np.float32(uv[0])), float(np.float32(uv[1]))


def build(episode: Path, metadata: dict) -> dict:
    native_name = metadata.get('parametric_native_source_file')
    if not native_name or Path(native_name).name != native_name:
        raise ValueError('native source record is missing')
    source = json.loads((episode / native_name).read_text())
    if source.get('schema') != 'spraybot.native-source.v1' or source.get('unit') != 'm':
        raise ValueError('unsupported native source record')
    vertices, faces = _obj(episode / metadata['model_file'])
    owners = np.asarray(source['final_triangle_source_ids'], dtype=int)
    face_ids = np.asarray(source['final_triangle_source_face_ids'], dtype=int)
    final_uv = np.asarray(source['final_vertex_uv'], dtype=float)
    if (len(owners) != len(faces) or len(face_ids) != len(faces)
        or final_uv.shape != (len(vertices), 2)):
        raise ValueError('native source record disagrees with OBJ shape')
    parts = []
    worst_angle = 0.0
    covered = set()
    for record in source['sources']:
        source_id = record['id']
        if record['kind'] not in ('bumper_surface_grid', 'bumper_lip_grid'):
            raise ValueError('unsupported native source constructor')
        uv = np.asarray(record['source_uv'], dtype=float)
        source_faces = np.asarray(record['source_faces'], dtype=int)
        normals = np.asarray(record['source_vertex_normals'], dtype=float)
        front = _source_front(record)
        if (source_faces.ndim != 2 or source_faces.shape[1] != 3
            or normals.shape != front.shape or uv.shape != (len(front), 2)
            or not np.isfinite(normals).all()
            or np.max(np.abs(np.linalg.norm(normals, axis=1) - 1)) > 1e-5):
            raise ValueError('invalid native source grid or normals')
        thickness = float(record['parameters']['solidify_thickness_m'])
        if not 0 < thickness < 0.05:
            raise ValueError('invalid native solidify thickness')
        back = front - thickness * normals
        addresses = {_address_key(point): index for index, point in enumerate(uv)}
        if len(addresses) != len(uv):
            raise ValueError('ambiguous native source UV addresses')
        triangle_ids = np.flatnonzero(owners == source_id)
        if len(triangle_ids) == 0:
            raise ValueError('native source has no final triangles')
        vertex_ids = np.unique(faces[triangle_ids].ravel())
        address_id = {}
        layer = {}
        for vertex_id in vertex_ids:
            source_vertex = addresses.get(_address_key(final_uv[vertex_id]))
            if source_vertex is None:
                raise ValueError('final vertex lost native UV address')
            front_error = np.linalg.norm(vertices[vertex_id] - front[source_vertex])
            back_error = np.linalg.norm(vertices[vertex_id] - back[source_vertex])
            if min(front_error, back_error) > POSITION_TOLERANCE_M:
                raise ValueError('final vertex differs from native constructor')
            address_id[int(vertex_id)] = source_vertex
            layer[int(vertex_id)] = 0 if front_error < back_error else 1
        surfaces = []
        for triangle_id in triangle_ids:
            face_id = int(face_ids[triangle_id])
            if not 1 <= face_id <= len(source_faces):
                raise ValueError('native source face lineage is invalid')
            triangle = faces[triangle_id]
            indices = [address_id[int(vertex)] for vertex in triangle]
            layers = [layer[int(vertex)] for vertex in triangle]
            source_corner_ids = set(map(int, source_faces[face_id - 1]))
            if not set(indices) <= source_corner_ids:
                raise ValueError('triangle UV addresses disagree with source face')
            if len(set(indices)) == 3 and len(set(layers)) != 1:
                raise ValueError('native wall triangle has three source vertices')
            if len(set(indices)) == 2 and set(layers) != {0, 1}:
                raise ValueError('native wall lacks front and back source layers')
            if len(set(indices)) not in (2, 3):
                raise ValueError('unsupported native solidify triangle')
            corners = np.asarray([
                front[index] if side == 0 else back[index]
                for index, side in zip(indices, layers)
            ])
            normal = np.cross(corners[1] - corners[0], corners[2] - corners[0])
            length = np.linalg.norm(normal)
            if length < 1e-12:
                raise ValueError('degenerate native source triangle')
            normal /= length
            actual = vertices[triangle]
            actual_normal = np.cross(actual[1] - actual[0], actual[2] - actual[0])
            actual_normal /= np.linalg.norm(actual_normal)
            angle = float(np.degrees(np.arccos(np.clip(normal @ actual_normal, -1, 1))))
            worst_angle = max(worst_angle, angle)
            if angle > 0.1:
                raise ValueError('native source triangle normal differs from OBJ')
            surfaces.append({
                'id': f'native_{source_id}:triangle_{triangle_id}',
                'type': 'sweep_triangle',
                'domain': {'u': [0, 1], 'v': [0, 1], 'constraint': 'u+v<=1'},
                'periodic_v': False,
                'geometry': {'corners': corners.tolist(), 'normal': normal.tolist()},
                'provenance': {
                    'primitive': 'native_bumper_grid',
                    'source_id': source_id, 'source_face_id': face_id,
                    'source_vertex_ids': indices, 'solidify_layers': layers,
                },
                'mesh_mapping': {'construction_triangle_ids': [int(triangle_id)],
                                 'support_triangle_ids': [int(triangle_id)]},
                'approximation': {'kind': 'source_sweep_sections',
                                  'mesh_distance_bound_m': 2e-6},
            })
            covered.add(int(triangle_id))
        parts.append({'id': f'native_{source_id}',
                      'semantic': record['parameters']['part'], 'surfaces': surfaces})
    with np.load(episode / metadata['face_attributes_file'], allow_pickle=False) as attrs:
        targets = np.asarray(attrs['spray_target'], dtype=bool)
    target_ids = set(np.flatnonzero(targets).tolist())
    if not target_ids <= covered:
        raise ValueError('native source leaves spray target triangles undescribed')
    return {
        'schema': 'spraybot.parametric.v5', 'unit': 'm',
        'frame': 'exported_obj_axes_origin', 'obj_unit': 'mm',
        'obj_mm_per_parametric_m': 1000,
        'mesh_triangle_order': 'OBJ faces and face_attributes.npz rows, zero-based',
        'parts': parts,
        'description_coverage': {
            'spray_target_triangle_count': len(target_ids),
            'represented_target_triangle_count': len(target_ids),
            'unrepresented_non_target_triangle_ids': sorted(set(range(len(faces))) - covered),
        },
        'validation': {'max_mesh_to_surface_normal_angle_deg': worst_angle},
    }

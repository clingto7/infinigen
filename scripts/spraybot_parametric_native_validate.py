"""Independent source reconstruction for native BumperSurface patches.

This module reads exported records only; it does not import Blender or the
generator's BumperSurface implementation.
"""

from __future__ import annotations

import numpy as np


def _ramp(s, flat):
    a = np.clip((np.abs(s) - flat) / max(1 - flat, 1e-6), 0, 1)
    return a * a * (3 - 2 * a)


def _front(source):
    p = source['parameters']['surface']
    uv = np.asarray(source['source_uv'], dtype=float)
    s, v = uv[:, 0], uv[:, 1]
    grid = np.linspace(-1, 1, 401)
    turn = np.sign(grid) * float(p['wrap_phi']) * _ramp(grid, float(p['plan_flat']))
    dx = np.cos(turn) * float(p['W_lat']) / 2 * (grid[1] - grid[0])
    dy = np.sin(turn) * float(p['W_lat']) / 2 * (grid[1] - grid[0])
    x = np.concatenate([[0.0], np.cumsum((dx[1:] + dx[:-1]) / 2)])
    y = np.concatenate([[0.0], np.cumsum((dy[1:] + dy[:-1]) / 2)])
    x -= x[len(grid) // 2]
    y -= y[len(grid) // 2]
    psi = np.sign(s) * float(p['wrap_phi']) * _ramp(s, float(p['plan_flat']))
    nx, ny = np.sin(psi), -np.cos(psi)
    protrude = float(p['protrude'])
    profile = np.interp(v, [0, .22, float(p['bulge_v']), .80, 1],
                        [-float(p['chin']) * protrude, .72 * protrude,
                         protrude, .74 * protrude, -float(p['toproll']) * protrude])
    profile -= float(source['parameters'].get('recess_m', 0))
    height = float(p['H'])
    top_kind = p['top_kind']
    if top_kind == 'arch':
        top = height * (1 + float(p['arch_h']) * (1 - s * s))
    elif top_kind == 'dip':
        top = height * (1 - float(p['dip_h']) * (1 - s * s))
    elif top_kind == 'twin_horn':
        horn = np.exp(-((np.abs(s) - float(p['horn_s'])) / float(p['horn_w'])) ** 2)
        center = np.clip(1 - (s / max(float(p['horn_s']), 1e-3)) ** 2, 0, 1)
        top = height * (1 + float(p['horn_h']) * horn - .45 * float(p['dip_h']) * center)
    elif top_kind == 'shoulder':
        top = height * (1 + float(p['horn_h']) * .6
                        * np.clip((np.abs(s) - .35) / .65, 0, 1) ** 1.4)
    elif top_kind == 'flat':
        top = height * (1 - .015 * s * s)
    else:
        raise ValueError('unknown bumper top archetype')
    bottom_kind = p['bot_kind']
    if bottom_kind == 'valance':
        bottom = -height * float(p['val_h']) * (1 - s * s)
    elif bottom_kind == 'smile':
        bottom = height * float(p['smile_h']) * s * s
    elif bottom_kind == 'flat':
        bottom = np.zeros_like(s)
    else:
        raise ValueError('unknown bumper bottom archetype')
    point = np.column_stack([np.interp(s, grid, x) + nx * profile,
                             np.interp(s, grid, y) + ny * profile,
                             bottom + v * (top - bottom)])
    if source['kind'] == 'bumper_lip_grid':
        grow = float(source['parameters']['lip_forward_m']) * (
            1 - v / float(source['parameters']['lip_height']))
        point[:, 0] += nx * grow
        point[:, 1] += ny * grow
    return point


def prepare(source_record, vertices, faces):
    if source_record.get('schema') != 'spraybot.native-source.v1' or source_record.get('unit') != 'm':
        raise ValueError('invalid native source schema')
    owners = np.asarray(source_record['final_triangle_source_ids'], dtype=int)
    face_ids = np.asarray(source_record['final_triangle_source_face_ids'], dtype=int)
    uv = np.asarray(source_record['final_vertex_uv'], dtype=float)
    if (len(owners) != len(faces) or len(face_ids) != len(faces)
        or uv.shape != (len(vertices), 2) or not np.isfinite(uv).all()):
        raise ValueError('native source dimensions disagree with OBJ')
    prepared = {}
    for source in source_record['sources']:
        sid = source['id']
        if (type(sid) is not int or sid != len(prepared) + 1
            or source['kind'] not in ('bumper_surface_grid', 'bumper_lip_grid')):
            raise ValueError('unknown native source constructor')
        addresses = np.asarray(source['source_uv'], dtype=float)
        source_faces = np.asarray(source['source_faces'], dtype=int)
        normals = np.asarray(source['source_vertex_normals'], dtype=float)
        if (addresses.ndim != 2 or addresses.shape[1] != 2
            or not np.isfinite(addresses).all() or np.any(addresses[:, 0] < -1.001)
            or np.any(addresses[:, 0] > 1.001) or np.any(addresses[:, 1] < -1e-5)
            or np.any(addresses[:, 1] > 1.001)
            or source_faces.ndim != 2 or source_faces.shape[1] != 3
            or np.any(source_faces < 0) or np.any(source_faces >= len(addresses))
            or normals.shape != (len(addresses), 3)
            or not np.isfinite(normals).all()
            or np.max(np.abs(np.linalg.norm(normals, axis=1) - 1)) > 1e-5):
            raise ValueError('invalid native source grid')
        key = lambda point: (float(np.float32(point[0])), float(np.float32(point[1])))
        lookup = {key(point): i for i, point in enumerate(addresses)}
        if len(lookup) != len(addresses):
            raise ValueError('ambiguous native UV addresses')
        front = _front(source)
        thickness = float(source['parameters']['solidify_thickness_m'])
        if not 0 < thickness < .05:
            raise ValueError('invalid native solidify thickness')
        prepared[sid] = (source, source_faces, front, front - thickness * normals, lookup)
    if set(np.unique(owners)) != set(prepared):
        raise ValueError('native source IDs disagree with final faces')
    return owners, face_ids, uv, prepared


def validate_surface(surface, triangle_id, vertices, faces, native):
    owners, face_ids, final_uv, prepared = native
    provenance = surface.get('provenance', {})
    sid = provenance.get('source_id')
    face_id = provenance.get('source_face_id')
    indices = provenance.get('source_vertex_ids')
    layers = provenance.get('solidify_layers')
    if (surface.get('type') != 'sweep_triangle'
        or provenance.get('primitive') != 'native_bumper_grid'
        or type(sid) is not int or sid not in prepared
        or owners[triangle_id] != sid or type(face_id) is not int
        or face_ids[triangle_id] != face_id
        or not isinstance(indices, list) or len(indices) != 3
        or not isinstance(layers, list) or len(layers) != 3
        or any(type(x) is not int or x not in (0, 1) for x in layers)):
        raise ValueError('native surface provenance disagrees with source lineage')
    source, source_faces, front, back, lookup = prepared[sid]
    if not 1 <= face_id <= len(source_faces):
        raise ValueError('native source face is out of range')
    actual_indices = []
    for vertex_id in faces[triangle_id]:
        index = lookup.get((float(np.float32(final_uv[vertex_id, 0])),
                            float(np.float32(final_uv[vertex_id, 1]))))
        if index is None:
            raise ValueError('final vertex has no native source UV')
        actual_indices.append(index)
    if (indices != actual_indices or not set(indices) <= set(source_faces[face_id - 1])
        or len(set(indices)) not in (2, 3)
        or (len(set(indices)) == 3 and len(set(layers)) != 1)
        or (len(set(indices)) == 2 and set(layers) != {0, 1})):
        raise ValueError('native triangle does not follow source grid face')
    expected = np.asarray([front[i] if layer == 0 else back[i]
                           for i, layer in zip(indices, layers)])
    claimed = np.asarray(surface['geometry']['corners'], dtype=float)
    if (claimed.shape != (3, 3) or not np.isfinite(claimed).all()
        or np.max(np.abs(claimed - expected)) > 2.1e-6
        or np.max(np.abs(vertices[faces[triangle_id]] - expected)) > 2.1e-6):
        raise ValueError('native surface coordinates disagree with analytic constructor')

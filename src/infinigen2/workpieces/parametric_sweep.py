"""Source-addressed, piecewise sweep patches captured before assembly.

This provider describes the polygonal sections actually used by curve_to_mesh,
not an inferred smooth curve or a reconstruction of the delivered triangles.
Bilinear cells retain their twist; cap polygons must remain planar and convex.
"""
import numpy as np


def _sphere_provenance(patch, transform, indices=None):
    source = patch['uv_sphere_source']
    center = np.asarray(source['center']) @ transform[:3, :3].T + transform[:3, 3]
    axes = np.asarray(source['axes']) @ transform[:3, :3].T
    selected = list(range(len(patch['corners']))) if indices is None else indices
    return {
        'primitive': 'uv_sphere_sections', 'center_m': center.tolist(),
        'axes_m': axes.tolist(), 'segments': source['segments'],
        'rings': source['rings'], 'source_face_id': source['source_face_id'],
        'rail_indices': [patch['source_rail_indices'][i] for i in selected],
        'profile_indices': [patch['source_profile_indices'][i] for i in selected],
    }


def _window_provenance(patch, transform, indices=None):
    source = patch['window_source']
    result = {
        'primitive': 'window_frame_source',
        'source_constructor': '_window_geometry',
        'component': source['component'],
        'source_face_id': source['source_face_id'],
        'parameters': source['parameters'],
        'source_to_obj': transform.tolist(),
    }
    if indices is not None:
        parent = np.asarray(patch['corners']) @ transform[:3, :3].T + transform[:3, 3]
        result.update(source_quad_split=True,
                      source_quad_corners=parent.tolist(),
                      source_quad_corner_indices=indices)
    return result


def _wheeled_provenance(patch, transform, indices=None):
    source = patch['wheeled_source']
    result = {
        'primitive': 'wheeled_base_source',
        'source_constructor': '_wheeled_base_geometry',
        'component': source['component'],
        'source_face_id': source['source_face_id'],
        'sweep_addressed': source['sweep_addressed'],
        'parameters': source['parameters'],
        'source_to_obj': transform.tolist(),
    }
    if indices is not None:
        parent = np.asarray(patch['corners']) @ transform[:3, :3].T + transform[:3, 3]
        result.update(source_quad_split=True,
                      source_quad_corners=parent.tolist(),
                      source_quad_corner_indices=indices)
    return result


def _curvy_seat_provenance(patch, transform, indices=None):
    source = patch['curvy_seat_source']
    result = {
        'primitive': 'curvy_seat_loft_source',
        'source_constructor': '_curvy_seat_geometry',
        'source_face_id': source['source_face_id'],
        'parameters': source['parameters'],
        'source_to_obj': transform.tolist(),
    }
    if indices is not None:
        parent = np.asarray(patch['corners']) @ transform[:3, :3].T + transform[:3, 3]
        result.update(source_quad_split=True,
                      source_quad_corners=parent.tolist(),
                      source_quad_corner_indices=indices)
    return result


def _native_opus_provenance(patch, transform, indices=None):
    source = patch['native_opus_source']
    result = {
        'primitive': 'native_opus_constructor',
        'constructor': source['constructor'],
        'parameters': source['parameters'],
        'source_face_id': source['source_face_id'],
        'source_to_obj': transform.tolist(),
    }
    if indices is not None:
        parent = np.asarray(patch['corners']) @ transform[:3, :3].T + transform[:3, 3]
        result.update(source_quad_split=True,
                      source_quad_corners=parent.tolist(),
                      source_quad_corner_indices=indices)
    return result


def _native_chair_provenance(patch, transform, indices=None):
    source = patch['native_chair_source']
    result = {
        'primitive': 'native_chair_constructor',
        'constructor': source['constructor'],
        'parameters': source['parameters'],
        'source_face_id': source['source_face_id'],
        'source_to_obj': transform.tolist(),
    }
    if indices is not None:
        parent = np.asarray(patch['corners']) @ transform[:3, :3].T + transform[:3, 3]
        result.update(source_quad_split=True,
                      source_quad_corners=parent.tolist(),
                      source_quad_corner_indices=indices)
    return result


def capture_native_mesh_patches(obj, constructor, parameters, source_key):
    """Capture a known native constructor output before final assembly."""
    mesh = obj.data
    mesh.calc_loop_triangles()
    by_face = {}
    for tri in mesh.loop_triangles:
        by_face.setdefault(tri.polygon_index, []).append(
            np.asarray([mesh.vertices[i].co[:] for i in tri.vertices]))
    patches = []
    for face in mesh.polygons:
        corners = np.asarray([mesh.vertices[i].co[:] for i in face.vertices])
        if len(corners) < 3:
            raise ValueError('native Opus source face has fewer than three corners')
        edges = np.roll(corners, -1, axis=0) - corners
        normal = np.cross(corners - corners.mean(axis=0),
                          np.roll(corners - corners.mean(axis=0), -1, axis=0)).sum(axis=0)
        irregular = np.linalg.norm(normal) < 1e-12 or np.min(np.linalg.norm(edges, axis=1)) < 1e-7
        if not irregular:
            normal /= np.linalg.norm(normal)
        if irregular:
            kind = 'source_triangulation'
        elif len(corners) == 3:
            kind = 'sweep_triangle'
        elif len(corners) == 4:
            kind = 'sweep_quad'
            a, b, c, d = corners
            twist = a - b + c - d
            tangents = np.asarray([
                np.cross(b-a+v*twist, d-a+u*twist)
                for u, v in ((0, 0), (0, 1), (1, 0), (1, 1))
            ])
            triangles = np.asarray([np.cross(t[1]-t[0], t[2]-t[0])
                                    for t in by_face[face.index]])
            lengths = np.linalg.norm(tangents, axis=1)[:, None] * np.linalg.norm(triangles, axis=1)[None, :]
            if np.any(lengths < 1e-12) or np.min((tangents @ triangles.T) / lengths) < np.cos(np.deg2rad(5)):
                kind = 'sweep_split_quad'
        else:
            kind = 'sweep_cap'
            if (np.max(np.abs((corners-corners[0]) @ normal)) > 1e-6
                or np.any(np.cross(edges, np.roll(edges, -1, axis=0)) @ normal <= 1e-14)):
                kind = 'source_triangulation'
        patches.append({
            'type': kind, 'corners': corners.tolist(),
            'source_rail_indices': ([1, 1, 2, 2] if len(corners) == 4 else
                                    [1] * len(corners) if kind == 'sweep_cap' else
                                    list(range(1, len(corners) + 1))),
            'source_profile_indices': ([1, 2, 2, 1] if len(corners) == 4 else
                                       list(range(1, len(corners) + 1))),
            source_key: {
                'constructor': constructor, 'parameters': parameters,
                'source_face_id': face.index + 1,
            },
        })
    return patches


def capture_native_opus_patches(obj, constructor, parameters):
    return capture_native_mesh_patches(obj, constructor, parameters, 'native_opus_source')


def capture_bevel_patches(obj, source):
    """Capture convex bevel facets and planar caps from the known constructor."""
    mesh = obj.item().data
    attr = mesh.attributes.get('parametric_bevel_source_face')
    if attr is None or attr.domain != 'FACE':
        raise ValueError('bevel operation lost source-face lineage')
    mesh.calc_loop_triangles()
    source_triangles = {}
    for triangle in mesh.loop_triangles:
        source_triangles.setdefault(triangle.polygon_index, []).append(
            np.asarray([mesh.vertices[i].co[:] for i in triangle.vertices])
        )
    patches = []
    for face in mesh.polygons:
        source_id = int(attr.data[face.index].value)
        if len(face.vertices) < 3 or not 1 <= source_id <= len(source['source_face_corners']):
            raise ValueError(f'unsupported bevel facet on face {face.index}')
        corners = np.asarray([mesh.vertices[i].co[:] for i in face.vertices])
        edges = np.roll(corners, -1, axis=0) - corners
        offset = corners - corners.mean(axis=0)
        normal = np.cross(offset, np.roll(offset, -1, axis=0)).sum(axis=0)
        if np.linalg.norm(normal) < 1e-12 or np.min(np.linalg.norm(edges, axis=1)) < 1e-7:
            # Some bevels emit a zero-area construction face that is removed
            # by a later join. A retained final triangle is rejected during
            # export, where patch IDs must partition every captured triangle.
            patches.append(None)
            continue
        normal /= np.linalg.norm(normal)
        kind = 'sweep_quad' if len(corners) == 4 else 'sweep_cap'
        if kind == 'sweep_cap' and np.max(np.abs(offset @ normal)) > 1e-6:
            raise ValueError(f'nonplanar bevel cap on face {face.index}')
        if np.any(np.cross(edges, np.roll(edges, -1, axis=0)) @ normal <= 1e-14):
            raise ValueError(f'folded bevel facet on face {face.index}')
        if kind == 'sweep_quad':
            a, b, c, d = corners
            twist = a - b + c - d
            tangents = np.asarray([
                np.cross(b-a+v*twist, d-a+u*twist)
                for u, v in ((0, 0), (0, 1), (1, 0), (1, 1))
            ])
            triangle_normals = np.asarray([
                np.cross(t[1]-t[0], t[2]-t[0])
                for t in source_triangles[face.index]
            ])
            if np.any(tangents @ triangle_normals.T <= 0):
                kind = 'sweep_split_quad'
        patches.append({'type':kind, 'corners':corners.tolist(),
                        'source_rail_indices':([1,1,2,2] if kind in ('sweep_quad', 'sweep_split_quad') else [1] * len(corners)),
                        'source_profile_indices':([1,2,2,1] if kind in ('sweep_quad', 'sweep_split_quad') else list(range(1, len(corners) + 1))),
                        'bevel_source_face_id':source_id,
                        'bevel_source_corners':source['source_face_corners'][source_id-1],
                        'bevel_source_primitive':source['primitive'],
                        'bevel_width_m':source['bevel_width_m']})
    return patches


def capture_window_patches(obj, components):
    """Capture executed window subconstructor quads before object assembly."""
    mesh = obj.item().data
    mesh.calc_loop_triangles()
    triangles = {}
    for triangle in mesh.loop_triangles:
        triangles.setdefault(triangle.polygon_index, []).append(
            np.asarray([mesh.vertices[i].co[:] for i in triangle.vertices])
        )
    patches = []
    for face in mesh.polygons:
        if len(face.vertices) != 4 or components[face.index] not in (1, 2, 3):
            raise ValueError(f'window source face {face.index} lacks a known quad component')
        corners = np.asarray([mesh.vertices[i].co[:] for i in face.vertices])
        edges = np.roll(corners, -1, axis=0) - corners
        offset = corners - corners.mean(axis=0)
        normal = np.cross(offset, np.roll(offset, -1, axis=0)).sum(axis=0)
        if np.linalg.norm(normal) < 1e-12 or np.min(np.linalg.norm(edges, axis=1)) < 1e-7:
            raise ValueError(f'degenerate window source face {face.index}')
        normal /= np.linalg.norm(normal)
        if np.any(np.cross(edges, np.roll(edges, -1, axis=0)) @ normal <= 1e-14):
            raise ValueError(f'folded window source face {face.index}')
        a, b, c, d = corners
        twist = a - b + c - d
        tangents = np.asarray([
            np.cross(b-a+v*twist, d-a+u*twist)
            for u, v in ((0, 0), (0, 1), (1, 0), (1, 1))
        ])
        triangle_normals = np.asarray([
            np.cross(tri[1]-tri[0], tri[2]-tri[0]) for tri in triangles[face.index]
        ])
        kind = 'sweep_split_quad' if np.any(tangents @ triangle_normals.T <= 0) else 'sweep_quad'
        patches.append({
            'type': kind, 'corners': corners.tolist(),
            'source_rail_indices': [1, 1, 2, 2],
            'source_profile_indices': [1, 2, 2, 1],
            'window_source': {'component': int(components[face.index]),
                              'source_face_id': face.index + 1},
        })
    return patches


def capture_wheeled_patches(obj, components):
    """Capture the wheeled-base constructor before it joins a chair."""
    mesh = obj.item().data
    mesh.calc_loop_triangles()
    triangles = {}
    for triangle in mesh.loop_triangles:
        triangles.setdefault(triangle.polygon_index, []).append(
            np.asarray([mesh.vertices[i].co[:] for i in triangle.vertices])
        )
    rail = mesh.attributes.get('parametric_rail_index')
    profile = mesh.attributes.get('parametric_profile_index')
    patches = []
    for face in mesh.polygons:
        source_count = len(face.vertices)
        if source_count < 3 or components[face.index] not in (1, 2):
            raise ValueError(f'wheeled base face {face.index} lacks a known component')
        source_corners = np.asarray([mesh.vertices[i].co[:] for i in face.vertices])
        # The caster curve occasionally closes a cap with duplicate vertices.
        # Preserve its source face address while removing only zero-length edges.
        kept = [i for i in range(source_count)
                if np.linalg.norm(source_corners[i] - source_corners[i-1]) >= 1e-7]
        corners = source_corners[kept]
        count = len(corners)
        if count < 3:
            patches.append(None)
            continue
        edges = np.roll(corners, -1, axis=0) - corners
        offset = corners - corners.mean(axis=0)
        normal = np.cross(offset, np.roll(offset, -1, axis=0)).sum(axis=0)
        if np.linalg.norm(normal) < 1e-12 or np.min(np.linalg.norm(edges, axis=1)) < 1e-7:
            patches.append(None)
            continue
        normal /= np.linalg.norm(normal)
        turn = np.cross(edges, np.roll(edges, -1, axis=0)) @ normal
        roundoff = max(1e-12, float(np.max(np.linalg.norm(edges, axis=1)) ** 2) * 1e-5)
        if np.any(turn < -roundoff):
            raise ValueError(f'nonconvex wheeled base source face {face.index}')
        if count == 3:
            kind = 'sweep_triangle'
        elif count == 4:
            a, b, c, d = corners
            twist = a - b + c - d
            tangents = np.asarray([
                np.cross(b-a+v*twist, d-a+u*twist)
                for u, v in ((0, 0), (0, 1), (1, 0), (1, 1))
            ])
            triangle_normals = np.asarray([
                np.cross(tri[1]-tri[0], tri[2]-tri[0]) for tri in triangles[face.index]
            ])
            kind = 'sweep_split_quad' if np.any(tangents @ triangle_normals.T <= 0) else 'sweep_quad'
        else:
            if np.max(np.abs(offset @ normal)) > 1e-6:
                raise ValueError(f'nonplanar wheeled base source cap {face.index}')
            kind = 'sweep_cap'
        rails = ([rail.data[i].value for i in face.loop_indices]
                 if rail is not None and rail.domain == 'CORNER' else [])
        profiles = ([profile.data[i].value for i in face.loop_indices]
                    if profile is not None and profile.domain == 'CORNER' else [])
        if len(rails) == source_count:
            rails = [rails[i] for i in kept]
        if len(profiles) == source_count:
            profiles = [profiles[i] for i in kept]
        addressed = (len(rails) == count and len(profiles) == count
                     and min(rails + profiles) > 0)
        if not addressed:
            rails = [1] * count if kind == 'sweep_cap' else [1, 1, 2, 2] if count == 4 else [1, 2, 3]
            profiles = list(range(1, count + 1)) if kind != 'sweep_quad' else [1, 2, 2, 1]
        patches.append({
            'type': kind, 'corners': corners.tolist(),
            'source_rail_indices': rails, 'source_profile_indices': profiles,
            'wheeled_source': {'component': int(components[face.index]),
                               'source_face_id': face.index + 1,
                               'sweep_addressed': addressed},
        })
    return patches


def capture_grid_patches(obj, face_indices=None):
    """Capture cells of a ruled grid with one explicit extrusion layer.

    The three construction addresses survive deformation in the node graph.
    Only four distinct corners of a single lattice cell are supported. Bevels,
    cuts and missing lineage fail closed instead of becoming arbitrary patches.
    """
    mesh = obj.item().data
    attr = mesh.attributes.get('parametric_grid_address')
    if attr is None or attr.domain != 'CORNER':
        raise ValueError('missing ruled-grid corner addresses')
    patches = []
    faces = mesh.polygons if face_indices is None else [mesh.polygons[i] for i in face_indices]
    for face in faces:
        address = np.asarray([attr.data[i].vector[:] for i in face.loop_indices])
        if address.shape != (4, 3) or not np.isfinite(address).all() or np.any(address <= 0):
            raise ValueError(f'invalid ruled-grid addresses on face {face.index}')
        if not np.allclose(address, np.round(address), atol=1e-6, rtol=0):
            raise ValueError('ruled-grid addresses were interpolated by an unsupported operation')
        counts = [len(set(address[:, i])) for i in range(3)]
        if sorted(counts) != [1, 2, 2] or len(np.unique(address, axis=0)) != 4:
            raise ValueError('face does not span one ruled-grid cell')
        axes = [i for i, n in enumerate(counts) if n == 2]
        if any(np.ptp(address[:, i]) != 1 for i in axes):
            raise ValueError('ruled-grid cell skips a construction section')
        corners = np.asarray([mesh.vertices[i].co[:] for i in face.vertices])
        edges = np.roll(corners, -1, axis=0) - corners
        offset = corners - corners.mean(axis=0)
        normal = np.cross(offset, np.roll(offset, -1, axis=0)).sum(axis=0)
        if np.linalg.norm(normal) < 1e-12:
            raise ValueError('degenerate ruled-grid cell')
        normal /= np.linalg.norm(normal)
        if np.any(np.cross(edges, np.roll(edges, -1, axis=0)) @ normal <= 1e-14):
            raise ValueError('folded ruled-grid cell')
        patches.append({'type': 'sweep_quad', 'corners': corners.tolist(),
                        'source_rail_indices': address[:, axes[0]].tolist(),
                        'source_profile_indices': address[:, axes[1]].tolist(),
                        'grid_addresses': address.tolist()})
    return patches


def capture_patches(obj, face_indices=None):
    mesh = obj.item().data
    mesh.calc_loop_triangles()
    source_triangles = {}
    for triangle in mesh.loop_triangles:
        source_triangles.setdefault(triangle.polygon_index, []).append(tuple(triangle.vertices))
    rail = mesh.attributes.get('parametric_rail_index')
    profile = mesh.attributes.get('parametric_profile_index')
    if rail is None or profile is None:
        return None
    patches = []
    faces = mesh.polygons if face_indices is None else [mesh.polygons[i] for i in face_indices]
    for face in faces:
        if rail.domain != 'CORNER' or profile.domain != 'CORNER':
            raise ValueError('source sweep addresses must use the corner domain')
        rails = [rail.data[i].value for i in face.loop_indices]
        profiles = [profile.data[i].value for i in face.loop_indices]
        if min(rails + profiles) <= 0:
            raise ValueError(f'sweep source addresses missing on face {face.index}')
        if len(set(rails)) == 1:
            kind = 'sweep_cap'
        elif len(face.vertices) == 4 and len(set(rails)) == len(set(profiles)) == 2:
            kind = 'sweep_quad'
        elif len(face.vertices) == 3 and 2 <= len(set(rails)) <= 3 and 2 <= len(set(profiles)) <= 3:
            kind = 'sweep_triangle'
        else:
            raise ValueError(f'unsupported sweep cell topology on face {face.index}')
        corners = np.asarray([mesh.vertices[i].co[:] for i in face.vertices])
        offset = corners - corners.mean(axis=0)
        normal = np.cross(offset, np.roll(offset, -1, axis=0)).sum(axis=0)
        length = np.linalg.norm(normal)
        if length < 1e-12:
            raise ValueError(f'degenerate sweep source face {face.index}')
        normal /= length
        if kind == 'sweep_cap' and np.max(np.abs((corners - corners[0]) @ normal)) > 1e-6:
            raise ValueError(f'nonplanar sweep cap on source face {face.index}')
        # Require a strictly convex source profile/cell. Concavity needs trim domains.
        edges = np.roll(corners, -1, axis=0) - corners
        folded = np.any(np.cross(edges, np.roll(edges, -1, axis=0)) @ normal <= 1e-14)
        twisted = False
        if kind == 'sweep_quad' and len(source_triangles[face.index]) == 2:
            a, b, c, d = corners
            twist = a - b + c - d
            tangents = np.asarray([
                np.cross(b-a+v*twist, d-a+u*twist)
                for u, v in ((0, 0), (0, 1), (1, 0), (1, 1))
            ])
            triangle_normals = np.asarray([
                np.cross(
                    np.asarray(mesh.vertices[tri[1]].co[:]) - np.asarray(mesh.vertices[tri[0]].co[:]),
                    np.asarray(mesh.vertices[tri[2]].co[:]) - np.asarray(mesh.vertices[tri[0]].co[:]),
                ) for tri in source_triangles[face.index]
            ])
            twisted = np.any(tangents @ triangle_normals.T <= 0)
        if folded or twisted:
            if kind != 'sweep_quad' or len(source_triangles[face.index]) != 2:
                raise ValueError(f'folded or nonconvex sweep source face {face.index}')
            splits = []
            for vertices in source_triangles[face.index]:
                indices = [list(face.vertices).index(v) for v in vertices]
                tri = corners[indices]
                if np.linalg.norm(np.cross(tri[1]-tri[0], tri[2]-tri[0])) < 1e-12:
                    raise ValueError(f'degenerate source split {face.index}')
                splits.append({'corners': tri.tolist(), 'rail_indices': [rails[i] for i in indices],
                               'profile_indices': [profiles[i] for i in indices]})
            patches.append({'type': 'sweep_split_quad', 'corners': corners.tolist(),
                            'source_rail_indices': rails, 'source_profile_indices': profiles,
                            'splits': splits})
            continue
        patches.append({'type': kind, 'corners': corners.tolist(),
                        'source_rail_indices': rails, 'source_profile_indices': profiles})
    return patches


def export_patches(record, ids, patches, source_triangles):
    transform = np.asarray(record['transform'])
    surfaces = []
    for patch_id, patch in enumerate(record['patches'], 1):
        face_ids = ids[patches == patch_id]
        if patch is None:
            if len(face_ids):
                raise ValueError(f'degenerate bevel face {patch_id} survived assembly')
            continue
        if record.get('reflected'):
            patch = {
                **patch,
                'corners': patch['corners'][::-1],
                'source_rail_indices': patch['source_rail_indices'][::-1],
                'source_profile_indices': patch['source_profile_indices'][::-1],
            }
            if 'grid_addresses' in patch:
                patch['grid_addresses'] = patch['grid_addresses'][::-1]
        if not len(face_ids):
            if 'bevel_source_face_id' in patch or record.get('allow_removed_source_patches'):
                # Assembly can remove source faces; all surviving target
                # triangles still require a tagged source patch below.
                continue
            raise ValueError('source sweep patch lost its final triangles')
        if patch['type'] == 'source_triangulation':
            parent = np.asarray(patch['corners'])
            world_parent = parent @ transform[:3, :3].T + transform[:3, 3]
            for split_id, triangle_id in enumerate(face_ids, 1):
                observed = source_triangles[np.flatnonzero(ids == triangle_id)[0]]
                indices = [int(np.argmin(np.linalg.norm(parent - point, axis=1)))
                           for point in observed]
                if (len(set(indices)) != 3 or any(
                    np.linalg.norm(parent[i] - point) > 2e-6
                    for i, point in zip(indices, observed))):
                    raise ValueError('source polygon lost vertex lineage')
                corners = world_parent[indices]
                normal = np.cross(corners[1]-corners[0], corners[2]-corners[0])
                if np.linalg.norm(normal) < 1e-12:
                    raise ValueError('degenerate source polygon triangle')
                normal /= np.linalg.norm(normal)
                provenance = (_native_opus_provenance(patch, transform)
                              if 'native_opus_source' in patch else
                              _native_chair_provenance(patch, transform))
                provenance.update(source_polygon_triangulation=True,
                                  source_polygon_corners=world_parent.tolist(),
                                  source_polygon_corner_indices=indices)
                surfaces.append({
                    'id': f"instance_{record['instance_id']}:sweep_{patch_id}_{split_id}",
                    'type': 'sweep_triangle',
                    'domain': {'u':[0,1], 'v':[0,1], 'constraint':'u+v<=1'},
                    'periodic_v': False,
                    'geometry': {'corners': corners.tolist(), 'normal': normal.tolist()},
                    'provenance': provenance,
                    'mesh_mapping': {'construction_triangle_ids':[int(triangle_id)],
                                     'support_triangle_ids':[int(triangle_id)]},
                    'approximation': {'kind':'source_sweep_sections',
                                      'mesh_distance_bound_m':2e-6},
                })
            continue
        if patch['type'] == 'sweep_cap' and record.get('triangulate_source_caps'):
            parent = np.asarray(patch['corners'])
            world_parent = parent @ transform[:3, :3].T + transform[:3, 3]
            for split_id, triangle_id in enumerate(face_ids, 1):
                observed = source_triangles[np.flatnonzero(ids == triangle_id)[0]]
                indices = [int(np.argmin(np.linalg.norm(parent - point, axis=1)))
                           for point in observed]
                if (len(set(indices)) != 3 or
                    any(np.linalg.norm(parent[i] - point) > 2e-6
                        for i, point in zip(indices, observed))):
                    raise ValueError('source cap lost corner lineage')
                corners = world_parent[indices]
                normal = np.cross(corners[1]-corners[0], corners[2]-corners[0])
                if np.linalg.norm(normal) < 1e-12:
                    raise ValueError('degenerate source cap triangle')
                normal /= np.linalg.norm(normal)
                matched = [int(triangle_id)]
                surfaces.append({
                    'id': f"instance_{record['instance_id']}:sweep_{patch_id}_{split_id}",
                    'type': 'sweep_triangle',
                    'domain': {'u':[0,1], 'v':[0,1], 'constraint':'u+v<=1'},
                    'periodic_v': False,
                    'geometry': {'corners': corners.tolist(), 'normal': normal.tolist()},
                    'provenance': {
                        'primitive': 'source_cap_triangulation',
                        'source_cap_corners': world_parent.tolist(),
                        'source_corner_indices': indices,
                        'rail_indices': [patch['source_rail_indices'][i] for i in indices],
                        'profile_indices': [patch['source_profile_indices'][i] for i in indices],
                    },
                    'mesh_mapping': {'construction_triangle_ids': matched,
                                     'support_triangle_ids': matched},
                    'approximation': {'kind':'source_sweep_sections',
                                      'mesh_distance_bound_m':2e-6},
                })
                if 'wheeled_source' in patch:
                    surfaces[-1]['provenance']['wheeled_source'] = _wheeled_provenance(patch, transform)
                if 'curvy_seat_source' in patch:
                    surfaces[-1]['provenance']['curvy_seat_source'] = _curvy_seat_provenance(patch, transform)
                if 'native_opus_source' in patch:
                    surfaces[-1]['provenance']['native_opus_source'] = _native_opus_provenance(patch, transform)
                if 'native_chair_source' in patch:
                    surfaces[-1]['provenance']['native_chair_source'] = _native_chair_provenance(patch, transform)
            continue
        if patch['type'] == 'sweep_quad' and len(face_ids) == 1:
            patch = {**patch, 'type': 'sweep_split_quad', 'splits': []}
        if patch['type'] == 'sweep_split_quad':
            if len(face_ids) not in (1, 2):
                raise ValueError(f'source split quad {patch_id} changed triangle count: {len(face_ids)}')
            parent = np.asarray(patch['corners'])
            split_indices = []
            for triangle_id in face_ids:
                observed = source_triangles[np.flatnonzero(ids == triangle_id)[0]]
                indices = [int(np.argmin(np.linalg.norm(parent - point, axis=1))) for point in observed]
                if len(set(indices)) != 3 or any(np.linalg.norm(parent[i] - point) > 2e-6
                                                 for i, point in zip(indices, observed)):
                    raise ValueError('source quad lost corner lineage')
                split_indices.append(indices)
            if len(face_ids) == 2 and (
                len({i for tri in split_indices for i in tri}) != 4 or
                len(set(split_indices[0]) & set(split_indices[1])) != 2
            ):
                raise ValueError('source quad final triangulation is incomplete')
            for split_id, (triangle_id, indices) in enumerate(zip(face_ids, split_indices), 1):
                split = {'corners': parent[indices].tolist(),
                         'rail_indices': [patch['source_rail_indices'][i] for i in indices],
                         'profile_indices': [patch['source_profile_indices'][i] for i in indices]}
                matched = [int(triangle_id)]
                local = np.asarray(split['corners']) @ transform[:3, :3].T + transform[:3, 3]
                normal = np.cross(local[1]-local[0], local[2]-local[0])
                normal /= np.linalg.norm(normal)
                surfaces.append({
                    'id': f"instance_{record['instance_id']}:sweep_{patch_id}_{split_id}",
                    'type': 'sweep_triangle', 'domain': {'u':[0,1], 'v':[0,1], 'constraint':'u+v<=1'},
                    'periodic_v': False, 'geometry': {'corners': local.tolist(), 'normal': normal.tolist()},
                    'provenance': {'primitive':'curve_to_mesh_with_uv', 'rail_indices':split['rail_indices'],
                                   'profile_indices':split['profile_indices'],
                                   'source_quad_split': True,
                                   'source_quad_rail_indices': patch['source_rail_indices'],
                                   'source_quad_profile_indices': patch['source_profile_indices']},
                    'mesh_mapping': {'construction_triangle_ids': matched, 'support_triangle_ids': matched},
                    'approximation': {'kind':'source_sweep_sections', 'mesh_distance_bound_m':2e-6},
                })
                if 'uv_sphere_source' in patch:
                    surfaces[-1]['provenance'] = _sphere_provenance(patch, transform, indices)
                if 'window_source' in patch:
                    surfaces[-1]['provenance'] = _window_provenance(patch, transform, indices)
                if 'wheeled_source' in patch:
                    surfaces[-1]['provenance'] = _wheeled_provenance(patch, transform, indices)
                if 'curvy_seat_source' in patch:
                    surfaces[-1]['provenance'] = _curvy_seat_provenance(patch, transform, indices)
                if 'native_opus_source' in patch:
                    surfaces[-1]['provenance'] = _native_opus_provenance(patch, transform, indices)
                if 'native_chair_source' in patch:
                    surfaces[-1]['provenance'] = _native_chair_provenance(patch, transform, indices)
                if 'bevel_source_face_id' in patch:
                    source_corners = np.asarray(patch['bevel_source_corners']) @ transform[:3,:3].T + transform[:3,3]
                    surfaces[-1]['provenance'] = {
                        'primitive': 'source_bevel_quad',
                        'source_constructor': patch['bevel_source_primitive'],
                        'source_face_id': patch['bevel_source_face_id'],
                        'source_face_corners': source_corners.tolist(),
                        'bevel_width_m': float(patch['bevel_width_m'] * np.linalg.norm(transform[:3,0])),
                        'source_quad_split': True,
                        'source_quad_corners': (
                            parent @ transform[:3,:3].T + transform[:3,3]
                        ).tolist(),
                        'source_quad_corner_indices': indices,
                    }
            # Final triangle IDs are assigned from source corner correspondences
            # below, never from a fitted final-mesh surface.
            continue
        corners = np.asarray(patch['corners']) @ transform[:3, :3].T + transform[:3, 3]
        offset = corners - corners.mean(axis=0)
        normal = np.cross(offset, np.roll(offset, -1, axis=0)).sum(axis=0)
        normal /= np.linalg.norm(normal)
        surfaces.append({
            'id': f"instance_{record['instance_id']}:sweep_{patch_id}", 'type': patch['type'],
            'domain': ({'u': [0, 1], 'v': [0, 1], 'constraint': 'u+v<=1'}
                       if patch['type'] == 'sweep_triangle' else {'u': [0, 1], 'v': [0, 1]}), 'periodic_v': patch['type'] == 'sweep_cap',
            'geometry': {'corners': corners.tolist(), 'normal': normal.tolist()},
            'provenance': {'primitive': 'curve_to_mesh_with_uv',
                           'rail_indices': patch['source_rail_indices'],
                           'profile_indices': patch['source_profile_indices']},
            'mesh_mapping': {'construction_triangle_ids': face_ids.tolist(),
                             'support_triangle_ids': face_ids.tolist()},
            'approximation': {'kind': 'source_sweep_sections', 'mesh_distance_bound_m':
                float(np.linalg.norm(corners[0]-corners[1]+corners[2]-corners[3])/4 + 2e-6)
                if patch['type'] == 'sweep_quad' else 2e-6},
        })
        if 'grid_addresses' in patch:
            surfaces[-1]['provenance'] = {
                'primitive': 'ruled_grid_extrusion',
                'grid_addresses': patch['grid_addresses'],
            }
        if 'support_loop_box_source' in patch:
            surfaces[-1]['provenance'] = {
                'primitive': 'support_loop_box_subdivision',
                'grid_addresses': patch['grid_addresses'],
                **patch['support_loop_box_source'],
                'source_center_m': transform[:3,3].tolist(),
                'source_axes_m': transform[:3,:3].tolist(),
            }
        if 'bevel_source_face_id' in patch:
            source_corners = np.asarray(patch['bevel_source_corners']) @ transform[:3,:3].T + transform[:3,3]
            surfaces[-1]['provenance'] = {
                'primitive': 'source_bevel_quad',
                'source_constructor': patch['bevel_source_primitive'],
                'source_face_id': patch['bevel_source_face_id'],
                'source_face_corners': source_corners.tolist(),
                'bevel_width_m': float(patch['bevel_width_m'] * np.linalg.norm(transform[:3,0])),
            }
        if 'uv_sphere_source' in patch:
            surfaces[-1]['provenance'] = _sphere_provenance(patch, transform)
        if 'window_source' in patch:
            surfaces[-1]['provenance'] = _window_provenance(patch, transform)
        if 'wheeled_source' in patch:
            surfaces[-1]['provenance'] = _wheeled_provenance(patch, transform)
        if 'curvy_seat_source' in patch:
            surfaces[-1]['provenance'] = _curvy_seat_provenance(patch, transform)
        if 'native_opus_source' in patch:
            surfaces[-1]['provenance'] = _native_opus_provenance(patch, transform)
        if 'native_chair_source' in patch:
            surfaces[-1]['provenance'] = _native_chair_provenance(patch, transform)
    if sum(len(s['mesh_mapping']['construction_triangle_ids']) for s in surfaces) != len(ids):
        raise ValueError('sweep patch partition failed')
    return surfaces

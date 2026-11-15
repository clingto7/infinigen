"""Independent validation of source sweep patches against delivered triangles."""
import math
import numpy as np


def _distance_to_triangle(point, triangle):
    a, b, c = triangle
    ab, ac = b - a, c - a
    normal = np.cross(ab, ac)
    norm = np.linalg.norm(normal)
    if norm < 1e-12:
        return float('inf')
    normal /= norm
    projected = point - np.dot(point - a, normal) * normal
    v = projected - a
    d00, d01, d11 = np.dot(ab, ab), np.dot(ab, ac), np.dot(ac, ac)
    d20, d21 = np.dot(v, ab), np.dot(v, ac)
    denominator = d00 * d11 - d01 * d01
    beta = (d11 * d20 - d01 * d21) / denominator
    gamma = (d00 * d21 - d01 * d20) / denominator
    if beta >= -1e-8 and gamma >= -1e-8 and beta + gamma <= 1 + 1e-8:
        return abs(float(np.dot(point - a, normal)))
    distances = []
    for start, end in ((a, b), (b, c), (c, a)):
        edge = end - start
        fraction = np.clip(np.dot(point - start, edge) / np.dot(edge, edge), 0, 1)
        distances.append(np.linalg.norm(point - (start + fraction * edge)))
    return float(min(distances))


def _validate_wheeled_source(provenance, kind, corners):
    params = provenance.get('parameters')
    transform = np.asarray(provenance.get('source_to_obj', []), dtype=float)
    component = provenance.get('component')
    if (kind not in ('sweep_quad', 'sweep_cap', 'sweep_triangle')
        or provenance.get('primitive') != 'wheeled_base_source'
        or provenance.get('source_constructor') != '_wheeled_base_geometry'
        or type(provenance.get('source_face_id')) is not int
        or provenance['source_face_id'] < 1
        or type(component) is not int or component not in (1, 2)
        or type(provenance.get('sweep_addressed')) is not bool
        or not isinstance(params, dict)
        or transform.shape != (4, 4) or not np.isfinite(transform).all()
        or abs(np.linalg.det(transform[:3, :3])) < 1e-12):
        raise ValueError('invalid wheeled base source provenance')
    keys = ('top_height', 'joint_height', 'leg_diameter', 'arc_sweep_angle',
            'wheel_width', 'wheel_rotation', 'pole_length')
    if (any(type(params.get(k)) not in (int, float)
            or not math.isfinite(params[k]) for k in keys)
        or params['top_height'] <= 0
        or not 0 < params['joint_height'] < params['top_height']
        or params['leg_diameter'] <= 0 or params['wheel_width'] <= 0
        or params['pole_length'] <= 0
        or not 0 < params['arc_sweep_angle'] <= 360
        or type(params.get('leg_number')) is not int
        or params['leg_number'] not in (4, 5)):
        raise ValueError('invalid wheeled base constructor parameters')
    if provenance.get('source_quad_split') is True:
        parent = np.asarray(provenance.get('source_quad_corners', []), dtype=float)
        indices = provenance.get('source_quad_corner_indices')
        if (kind != 'sweep_triangle' or parent.shape != (4, 3)
            or not np.isfinite(parent).all() or not isinstance(indices, list)
            or len(indices) != 3
            or any(type(i) is not int or not 0 <= i < 4 for i in indices)
            or len(set(indices)) != 3
            or np.max(np.abs(corners - parent[indices])) > 2.1e-6):
            raise ValueError('invalid wheeled base source quad split')
    local = (corners - transform[:3, 3]) @ np.linalg.inv(transform[:3, :3]).T
    if np.any(np.abs(local) > max(2.0, 4 * params['top_height'])):
        raise ValueError('wheeled base controls exceed constructor envelope')


def _validate_curvy_seat_source(provenance, kind, corners):
    params = provenance.get('parameters')
    transform = np.asarray(provenance.get('source_to_obj', []), dtype=float)
    face_id = provenance.get('source_face_id')
    if (provenance.get('primitive') != 'curvy_seat_loft_source'
        or provenance.get('source_constructor') != '_curvy_seat_geometry'
        or kind not in ('sweep_quad', 'sweep_triangle')
        or type(face_id) is not int or not 2 <= face_id <= 162
        or not isinstance(params, dict)
        or params.get('u_resolution') != 16 or params.get('v_resolution') != 11
        or transform.shape != (4, 4) or not np.isfinite(transform).all()
        or abs(np.linalg.det(transform[:3, :3])) < 1e-12):
        raise ValueError('invalid curvy seat loft source')
    numeric = ('width', 'front_relative_width', 'front_bent', 'seat_bent',
               'mid_bent', 'mid_relative_width', 'back_bent',
               'back_relative_width', 'top_bent', 'top_relative_width',
               'mid_pos', 'seat_height')
    if (any(type(params.get(k)) not in (int, float) or not math.isfinite(params[k])
            for k in numeric)
        or params['width'] <= 0 or params['seat_height'] <= 0
        or any(params[k] <= 0 for k in ('front_relative_width', 'mid_relative_width',
                                      'back_relative_width', 'top_relative_width'))
        or not 0 < params['mid_pos'] < 1):
        raise ValueError('invalid curvy seat loft parameters')
    if provenance.get('source_quad_split') is True:
        parent = np.asarray(provenance.get('source_quad_corners', []), dtype=float)
        indices = provenance.get('source_quad_corner_indices')
        if (kind != 'sweep_triangle' or parent.shape != (4, 3)
            or not np.isfinite(parent).all() or not isinstance(indices, list)
            or len(indices) != 3 or any(type(i) is not int or not 0 <= i < 4 for i in indices)
            or len(set(indices)) != 3
            or np.max(np.abs(corners - parent[indices])) > 2.1e-6):
            raise ValueError('invalid curvy seat source quad split')


def _validate_native_opus_source(provenance, kind, corners):
    constructor = provenance.get('constructor')
    parameters = provenance.get('parameters')
    transform = np.asarray(provenance.get('source_to_obj', []), dtype=float)
    if (constructor not in ('beveled_seat', 'tapered_bezier_tube',
                            'mirrored_bezier_tubes', 'beveled_ornament_panel')
        or kind not in ('sweep_quad', 'sweep_cap', 'sweep_triangle')
        or type(provenance.get('source_face_id')) is not int
        or provenance['source_face_id'] < 1
        or not isinstance(parameters, dict)
        or transform.shape != (4, 4) or not np.isfinite(transform).all()
        or abs(np.linalg.det(transform[:3, :3])) < 1e-12):
        raise ValueError('invalid native Opus constructor provenance')
    if provenance.get('source_quad_split') is True:
        parent = np.asarray(provenance.get('source_quad_corners', []), dtype=float)
        indices = provenance.get('source_quad_corner_indices')
        if (kind != 'sweep_triangle' or parent.shape != (4, 3)
            or not np.isfinite(parent).all() or not isinstance(indices, list)
            or len(indices) != 3 or any(type(i) is not int or not 0 <= i < 4 for i in indices)
            or len(set(indices)) != 3
            or np.max(np.abs(corners - parent[indices])) > 2.1e-6):
            raise ValueError('invalid native Opus split source quad')
    if provenance.get('source_polygon_triangulation') is True:
        parent = np.asarray(provenance.get('source_polygon_corners', []), dtype=float)
        indices = provenance.get('source_polygon_corner_indices')
        if (kind != 'sweep_triangle' or parent.ndim != 2 or parent.shape[1] != 3
            or len(parent) < 3 or not np.isfinite(parent).all()
            or not isinstance(indices, list) or len(indices) != 3
            or any(type(i) is not int or not 0 <= i < len(parent) for i in indices)
            or len(set(indices)) != 3
            or np.max(np.abs(corners-parent[indices])) > 2.1e-6):
            raise ValueError('invalid native Opus source polygon triangulation')
    local = (corners - transform[:3, 3]) @ np.linalg.inv(transform[:3, :3]).T
    if constructor == 'beveled_seat':
        shape = parameters.get('shape')
        values = [parameters.get(key) for key in ('r', 'ry', 't', 'bevel_width_m')]
        if (shape not in ('round', 'square') or any(type(x) not in (int, float)
            or not math.isfinite(x) or x <= 0 for x in values)
            or parameters.get('bevel_segments') not in (4, 8)):
            raise ValueError('invalid native seat recipe')
        r, ry, thick, bevel = values
        extent = np.array([r + bevel, r * ry + bevel, thick + bevel])
        if np.any(np.abs(local) > extent + 2.1e-6):
            raise ValueError('native seat exceeds recipe envelope')
    elif constructor == 'beveled_ornament_panel':
        panel = parameters.get('panel')
        if not isinstance(panel, dict) or parameters.get('ornament_type') not in (
            'cloud', 'blob', 'scallop', 'shield'):
            raise ValueError('invalid native panel recipe')
        silhouette = np.asarray(panel.get('sil_xz', []), dtype=float)
        y, thick, bevel = (panel.get('y'), panel.get('t'), parameters.get('bevel_width_m'))
        if (silhouette.ndim != 2 or silhouette.shape[1] != 2 or len(silhouette) < 3
            or not np.isfinite(silhouette).all() or any(type(x) not in (int, float)
            or not math.isfinite(x) for x in (y, thick, bevel))
            or thick <= 0 or bevel <= 0 or parameters.get('bevel_segments') != 3):
            raise ValueError('invalid native panel silhouette')
        lower = np.array([silhouette[:, 0].min(), y-thick-bevel, silhouette[:, 1].min()])-bevel
        upper = np.array([silhouette[:, 0].max(), y+thick+bevel, silhouette[:, 1].max()])+bevel
        if np.any(local < lower-2.1e-6) or np.any(local > upper+2.1e-6):
            raise ValueError('native panel exceeds recipe envelope')
    else:
        if constructor == 'tapered_bezier_tube':
            rods = [parameters]
        else:
            rods = parameters.get('rods')
            if parameters.get('mirrored_x') is not True or not isinstance(rods, list) or not rods:
                raise ValueError('invalid native mirrored rod recipe')
        all_anchors = []
        max_radius = 0.0
        for rod in rods:
            anchors = np.asarray(rod.get('anchors_m', []), dtype=float)
            r0, r1 = rod.get('start_radius_m'), rod.get('end_radius_m')
            if (anchors.ndim != 2 or anchors.shape[1] != 3 or len(anchors) < 2
                or not np.isfinite(anchors).all() or any(type(x) not in (int, float)
                or not math.isfinite(x) or x <= 0 for x in (r0, r1))):
                raise ValueError('invalid native tube centerline and radii')
            all_anchors.append(anchors)
            max_radius = max(max_radius, r0, r1)
        anchors = np.concatenate(all_anchors)
        if constructor == 'mirrored_bezier_tubes':
            mirrored = anchors.copy();mirrored[:, 0] *= -1
            anchors = np.concatenate([anchors, mirrored])
        margin = max_radius * 8 + .05
        if np.any(local < anchors.min(axis=0)-margin) or np.any(local > anchors.max(axis=0)+margin):
            raise ValueError('native tube exceeds source centerline envelope')


def _validate_native_chair_source(provenance, kind, corners):
    method = provenance.get('constructor')
    params = provenance.get('parameters')
    transform = np.asarray(provenance.get('source_to_obj', []), dtype=float)
    if (method not in ('make_seat', 'make_legs', 'make_backs',
                       'make_leg_decors', 'make_arms', 'make_back_decors')
        or kind not in ('sweep_quad', 'sweep_cap', 'sweep_triangle')
        or type(provenance.get('source_face_id')) is not int
        or provenance['source_face_id'] < 1 or not isinstance(params, dict)
        or transform.shape != (4, 4) or not np.isfinite(transform).all()
        or abs(np.linalg.det(transform[:3, :3])) < 1e-12):
        raise ValueError('invalid native chair constructor provenance')
    positive = ('width', 'size', 'thickness', 'bevel_width', 'leg_thickness',
                'leg_height', 'back_height', 'back_thickness')
    if any(type(params.get(key)) not in (int, float) or not math.isfinite(params[key])
           or params[key] <= 0 for key in positive):
        raise ValueError('invalid native chair dimensions')
    if params.get('leg_type') not in ('vertical', 'straight', 'up-curved', 'down-curved'):
        raise ValueError('invalid native chair leg profile')
    if params.get('back_type') not in ('whole', 'partial', 'horizontal-bar', 'vertical-bar'):
        raise ValueError('invalid native chair back type')
    if provenance.get('source_quad_split') is True:
        parent = np.asarray(provenance.get('source_quad_corners', []), dtype=float)
        indices = provenance.get('source_quad_corner_indices')
        if (kind != 'sweep_triangle' or parent.shape != (4, 3)
            or not np.isfinite(parent).all() or not isinstance(indices, list)
            or len(indices) != 3 or any(type(i) is not int or not 0 <= i < 4 for i in indices)
            or len(set(indices)) != 3 or
            np.max(np.abs(corners-parent[indices])) > 2.1e-6):
            raise ValueError('invalid native chair split source quad')
    if provenance.get('source_polygon_triangulation') is True:
        parent = np.asarray(provenance.get('source_polygon_corners', []), dtype=float)
        indices = provenance.get('source_polygon_corner_indices')
        if (kind != 'sweep_triangle' or parent.ndim != 2 or parent.shape[1] != 3
            or len(parent) < 3 or not np.isfinite(parent).all()
            or not isinstance(indices, list) or len(indices) != 3
            or any(type(i) is not int or not 0 <= i < len(parent) for i in indices)
            or len(set(indices)) != 3 or
            np.max(np.abs(corners-parent[indices])) > 2.1e-6):
            raise ValueError('invalid native chair source polygon triangle')
    local = (corners - transform[:3, 3]) @ np.linalg.inv(transform[:3, :3]).T
    extent = max(params[key] for key in positive) * 4
    if np.any(np.abs(local) > extent + 2.1e-6):
        raise ValueError('native chair source exceeds recipe envelope')


def validate_sweep(surface, triangles):
    kind = surface['type']
    domain={'u':[0,1],'v':[0,1]}
    if kind=='sweep_triangle':domain['constraint']='u+v<=1'
    if surface['domain'] != domain or surface['periodic_v'] is not (kind == 'sweep_cap'):
        raise ValueError('invalid sweep parameter domain')
    corners = np.asarray(surface['geometry']['corners'], dtype=float)
    normal = np.asarray(surface['geometry']['normal'], dtype=float)
    if corners.ndim != 2 or corners.shape[1] != 3 or len(corners)<3 or not np.isfinite(corners).all():
        raise ValueError('invalid sweep corners')
    if normal.shape != (3,) or not np.isfinite(normal).all() or abs(np.linalg.norm(normal)-1)>1e-5:
        raise ValueError('invalid sweep normal')
    if kind == 'sweep_triangle' and (len(corners)!=3 or len(surface['mesh_mapping']['construction_triangle_ids'])!=1):
        raise ValueError('collapsed sweep cell must be one triangle')
    if kind == 'sweep_quad' and len(corners)!=4:
        raise ValueError('sweep cell must have four control points')
    ids = surface['mesh_mapping']['construction_triangle_ids']
    supports = surface['mesh_mapping']['support_triangle_ids']
    if not ids or any(type(i) is not int or not 0<=i<len(triangles) for i in ids+supports):
        raise ValueError('invalid sweep triangle mapping')
    if len(set(ids))!=len(ids) or set(ids)!=set(supports):
        raise ValueError('sweep mapping is duplicated or support differs')
    provenance = surface.get('provenance',{})
    if provenance.get('primitive') == 'ruled_grid_extrusion':
        grid = np.asarray(provenance.get('grid_addresses', []), dtype=float)
        if kind != 'sweep_quad' or grid.shape != (4, 3) or not np.isfinite(grid).all():
            raise ValueError('invalid ruled-grid provenance')
        if np.any(grid <= 0) or not np.allclose(grid, np.round(grid), atol=1e-6, rtol=0):
            raise ValueError('invalid ruled-grid construction addresses')
        counts = [len(np.unique(grid[:, axis])) for axis in range(3)]
        if sorted(counts) != [1, 2, 2] or len(np.unique(grid, axis=0)) != 4:
            raise ValueError('ruled-grid patch is not a single cell')
        if any(np.ptp(grid[:, axis]) != 1 for axis in range(3) if counts[axis] == 2):
            raise ValueError('ruled-grid patch skips construction sections')
    elif provenance.get('primitive') == 'support_loop_box_subdivision':
        grid = np.asarray(provenance.get('grid_addresses', []), dtype=float)
        size = np.asarray(provenance.get('size_m', []), dtype=float)
        offset = np.asarray(provenance.get('support_loop_offset_m', []), dtype=float)
        resolution = provenance.get('grid_resolution')
        center = np.asarray(provenance.get('source_center_m', []), dtype=float)
        axes = np.asarray(provenance.get('source_axes_m', []), dtype=float)
        if (kind != 'sweep_quad' or grid.shape != (4, 3) or size.shape != (3,)
            or offset.shape != (3,) or center.shape != (3,) or axes.shape != (3, 3)
            or not all(np.isfinite(x).all() for x in (grid, size, offset, center, axes))
            or np.any(size <= 0) or np.any(offset <= 0) or np.any(offset >= size / 2)
            or not isinstance(resolution, list) or len(resolution) != 3
            or any(type(x) is not int or x < 3 for x in resolution)
            or provenance.get('subdivision_level') != 1
            or abs(np.linalg.det(axes)) < 1e-12):
            raise ValueError('invalid support-loop box source')
        counts = [len(np.unique(grid[:, axis])) for axis in range(3)]
        if (np.any(grid < 2) or np.any(grid > 2 * np.asarray(resolution))
            or not np.allclose(grid, np.round(grid), atol=1e-6, rtol=0)
            or sorted(counts) != [1, 2, 2] or len(np.unique(grid, axis=0)) != 4
            or any(np.ptp(grid[:, axis]) != 1 for axis in range(3) if counts[axis] == 2)):
            raise ValueError('invalid support-loop box grid addresses')
        local = np.linalg.solve(axes, (corners - center).T).T
        if (np.any(np.abs(local) > size / 2 + 2e-6)
            or np.any(np.min(size / 2 - np.abs(local), axis=1) > max(offset) + 2e-6)):
            raise ValueError('support-loop box controls exceed source envelope')
    elif provenance.get('primitive') in ('storage_cell_shelf_bevel', 'source_bevel_quad'):
        source = np.asarray(provenance.get('source_face_corners', []), dtype=float)
        width = provenance.get('bevel_width_m')
        if (kind not in ('sweep_quad', 'sweep_cap', 'sweep_triangle') or source.ndim != 2 or source.shape[1] != 3
            or len(source) < 3 or not np.isfinite(source).all()
            or (provenance.get('primitive') == 'source_bevel_quad' and
                (not isinstance(provenance.get('source_constructor'), str) or
                 not provenance['source_constructor']))
            or type(provenance.get('source_face_id')) is not int
            or provenance['source_face_id'] < 1
            or type(width) not in (int, float) or not math.isfinite(width) or width <= 0):
            raise ValueError('invalid bevel source provenance')
        if kind == 'sweep_triangle':
            parent = np.asarray(provenance.get('source_quad_corners', []), dtype=float)
            indices = provenance.get('source_quad_corner_indices')
            if (provenance.get('source_quad_split') is not True or parent.shape != (4, 3)
                or not np.isfinite(parent).all() or not isinstance(indices, list)
                or len(indices) != 3 or any(type(i) is not int or not 0 <= i < 4 for i in indices)
                or len(set(indices)) != 3 or
                np.max(np.abs(corners - parent[indices])) > 2.1e-6):
                raise ValueError('invalid bevel source quad split')
        elif provenance.get('source_quad_split') is True:
            raise ValueError('bevel source quad split requires triangles')
        plane = np.cross(source[1]-source[0], source[2]-source[0])
        if np.linalg.norm(plane) < 1e-12:
            raise ValueError('degenerate bevel source face')
        plane /= np.linalg.norm(plane)
        if np.max(np.abs((source-source[0])@plane)) <= 1e-6:
            if np.max(np.abs((corners-source[0])@plane)) > width + 2e-6:
                raise ValueError('bevel facet exceeds source width')
        else:
            if len(source) != 4:
                raise ValueError('nonplanar bevel source is not a quad')
            triangles_of_source = [source[list(indices)] for indices in
                                   ((0,1,2),(0,2,3),(0,1,3),(1,2,3))]
            if max(min(_distance_to_triangle(point, tri)
                       for tri in triangles_of_source) for point in corners) > width + 2e-6:
                raise ValueError('bevel facet exceeds twisted source width')
    elif provenance.get('primitive') == 'window_frame_source':
        params = provenance.get('parameters')
        transform = np.asarray(provenance.get('source_to_obj', []), dtype=float)
        component = provenance.get('component')
        if (kind not in ('sweep_quad', 'sweep_triangle')
            or provenance.get('source_constructor') != '_window_geometry'
            or type(provenance.get('source_face_id')) is not int
            or provenance['source_face_id'] < 1
            or type(component) is not int or component not in (1, 2, 3)
            or not isinstance(params, dict)
            or transform.shape != (4, 4) or not np.isfinite(transform).all()
            or abs(np.linalg.det(transform[:3, :3])) < 1e-12):
            raise ValueError('invalid window source provenance')
        dimensions = np.asarray(params.get('dimensions', []), dtype=float)
        counts = ('panel_h_amount', 'panel_v_amount', 'sub_panel_h_amount',
                  'sub_panel_v_amount')
        lengths = ('frame_width', 'sub_frame_width', 'sub_frame_thickness',
                   'shutter_width', 'shutter_thickness', 'shutter_interval')
        if (dimensions.shape != (3,) or not np.isfinite(dimensions).all()
            or np.any(dimensions <= 0)
            or any(type(params.get(k)) is not int or params[k] < 1 for k in counts)
            or any(type(params.get(k)) not in (int, float)
                   or not math.isfinite(params[k]) or params[k] <= 0 for k in lengths)
            or any(type(params.get(k)) not in (int, float)
                   or not math.isfinite(params[k]) or params[k] < 0
                   for k in ('top_profile_height', 'bottom_profile_height'))
            or type(params.get('shutter')) is not bool
            or type(params.get('shutter_rotation')) not in (int, float)
            or not math.isfinite(params['shutter_rotation'])):
            raise ValueError('invalid window constructor parameters')
        if kind == 'sweep_triangle':
            parent = np.asarray(provenance.get('source_quad_corners', []), dtype=float)
            indices = provenance.get('source_quad_corner_indices')
            if (provenance.get('source_quad_split') is not True
                or parent.shape != (4, 3) or not np.isfinite(parent).all()
                or not isinstance(indices, list) or len(indices) != 3
                or any(type(i) is not int or not 0 <= i < 4 for i in indices)
                or len(set(indices)) != 3
                or np.max(np.abs(corners - parent[indices])) > 2.1e-6):
                raise ValueError('invalid window source quad split')
        elif provenance.get('source_quad_split') is True:
            raise ValueError('window source quad split requires triangles')
        local = (corners - transform[:3, 3]) @ np.linalg.inv(transform[:3, :3]).T
        if component in (1, 2) and np.any(np.abs(local) > dimensions[[0, 1, 2]] / 2 + 0.06):
            raise ValueError('window frame controls exceed source dimensions')
    elif provenance.get('primitive') == 'wheeled_base_source':
        _validate_wheeled_source(provenance, kind, corners)
    elif provenance.get('primitive') == 'curvy_seat_loft_source':
        _validate_curvy_seat_source(provenance, kind, corners)
    elif provenance.get('primitive') == 'source_cap_triangulation':
        parent = np.asarray(provenance.get('source_cap_corners', []), dtype=float)
        indices = provenance.get('source_corner_indices')
        rail = provenance.get('rail_indices', [])
        profile = provenance.get('profile_indices', [])
        if (kind != 'sweep_triangle' or parent.ndim != 2 or parent.shape[1] != 3
            or len(parent) < 3 or not np.isfinite(parent).all()
            or not isinstance(indices, list) or len(indices) != 3
            or any(type(i) is not int or not 0 <= i < len(parent) for i in indices)
            or len(set(indices)) != 3 or
            np.max(np.abs(corners - parent[indices])) > 2.1e-6
            or len(rail) != 3 or len(profile) != 3
            or any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0
                   for x in rail + profile)
            or len(set(rail)) != 1):
            raise ValueError('invalid source cap triangulation')
        parent_edge = np.roll(parent, -1, axis=0) - parent
        parent_normal = np.cross(parent, np.roll(parent, -1, axis=0)).sum(axis=0)
        parent_length = np.linalg.norm(parent_normal)
        if (parent_length < 1e-12 or
            np.max(np.abs((parent-parent[0]) @ (parent_normal / parent_length))) > 2.1e-6):
            raise ValueError('invalid source cap polygon')
        turn = np.cross(parent_edge, np.roll(parent_edge, -1, axis=0)) @ (parent_normal / parent_length)
        tolerance = max(1e-12, float(np.max(np.linalg.norm(parent_edge, axis=1)) ** 2) * 1e-5)
        if np.any(turn < -tolerance):
            if 'curvy_seat_source' not in provenance:
                raise ValueError('nonconvex source cap polygon')
            # A warped loft can leave a concave end ring. Check the recorded
            # source triangle lies inside that ring instead of assuming convexity.
            axis = int(np.argmax(np.abs(parent_normal)))
            polygon = np.delete(parent, axis, axis=1)
            triangle = np.delete(corners, axis, axis=1)
            def inside(point):
                winding = False
                for a, b in zip(polygon, np.roll(polygon, -1, axis=0)):
                    edge = b - a
                    fraction = np.clip(np.dot(point-a, edge) / max(np.dot(edge, edge), 1e-18), 0, 1)
                    if np.linalg.norm(point - (a + fraction * edge)) < 2.1e-6:
                        return True
                    if (a[1] > point[1]) != (b[1] > point[1]):
                        x = a[0] + (point[1]-a[1]) * edge[0] / edge[1]
                        if point[0] < x:
                            winding = not winding
                return winding
            samples = [triangle.mean(axis=0)]
            samples.extend((triangle[i] + triangle[(i+1) % 3]) * 0.5 for i in range(3))
            if not all(inside(point) for point in samples):
                raise ValueError('source cap triangle leaves concave loft ring')
        if 'wheeled_source' in provenance:
            _validate_wheeled_source(provenance['wheeled_source'], kind, corners)
        if 'curvy_seat_source' in provenance:
            _validate_curvy_seat_source(provenance['curvy_seat_source'], kind, corners)
        if 'native_opus_source' in provenance:
            _validate_native_opus_source(provenance['native_opus_source'], kind, corners)
        if 'native_chair_source' in provenance:
            _validate_native_chair_source(provenance['native_chair_source'], kind, corners)
    elif provenance.get('primitive') == 'native_opus_constructor':
        _validate_native_opus_source(provenance, kind, corners)
    elif provenance.get('primitive') == 'native_chair_constructor':
        _validate_native_chair_source(provenance, kind, corners)
    elif provenance.get('primitive') == 'native_bumper_grid':
        if (kind != 'sweep_triangle'
            or type(provenance.get('source_id')) is not int
            or type(provenance.get('source_face_id')) is not int
            or not isinstance(provenance.get('source_vertex_ids'), list)
            or len(provenance['source_vertex_ids']) != 3
            or not isinstance(provenance.get('solidify_layers'), list)
            or len(provenance['solidify_layers']) != 3):
            raise ValueError('invalid native bumper source addresses')
    elif provenance.get('primitive') == 'uv_sphere_sections':
        center = np.asarray(provenance.get('center_m', []), dtype=float)
        axes = np.asarray(provenance.get('axes_m', []), dtype=float)
        segments, rings = provenance.get('segments'), provenance.get('rings')
        rail = provenance.get('rail_indices', [])
        profile = provenance.get('profile_indices', [])
        if (kind not in ('sweep_quad', 'sweep_triangle') or center.shape != (3,)
            or axes.shape != (3, 3) or not np.isfinite(center).all()
            or not np.isfinite(axes).all() or abs(np.linalg.det(axes)) < 1e-12
            or type(segments) is not int or segments < 3
            or type(rings) is not int or rings < 3
            or type(provenance.get('source_face_id')) is not int
            or provenance['source_face_id'] < 1
            or len(rail) != len(corners) or len(profile) != len(corners)
            or any(type(x) not in (int, float) or not math.isfinite(x)
                   for x in rail + profile)):
            raise ValueError('invalid UV sphere source provenance')
        if (min(rail) < 1 or max(rail) > rings + 1 or
            min(profile) < 1 or max(profile) > segments + 1 or
            not np.allclose(rail, np.round(rail), atol=1e-6, rtol=0) or
            not np.allclose(profile, np.round(profile), atol=1e-6, rtol=0)):
            raise ValueError('invalid UV sphere section addresses')
        spherical = np.linalg.solve(axes.T, (corners - center).T).T
        if np.max(np.abs(np.linalg.norm(spherical, axis=1) - 1.0)) > 2e-4:
            raise ValueError('UV sphere controls disagree with source radii')
    else:
        if provenance.get('primitive')!='curve_to_mesh_with_uv':
            raise ValueError('missing source sweep provenance')
        rail,profile = provenance.get('rail_indices',[]),provenance.get('profile_indices',[])
        if len(rail)!=len(corners) or len(profile)!=len(corners) or any(type(i) not in (int,float) or not math.isfinite(i) or i<=0 for i in rail+profile):
            raise ValueError('invalid source sweep addresses')
        if kind=='sweep_triangle':
            if provenance.get('source_quad_split') is True:
                quad_rail=provenance.get('source_quad_rail_indices',[])
                quad_profile=provenance.get('source_quad_profile_indices',[])
                if (len(quad_rail)!=4 or len(quad_profile)!=4 or
                    len(set(quad_rail))!=2 or len(set(quad_profile))!=2 or
                    not set(rail).issubset(set(quad_rail)) or
                    not set(profile).issubset(set(quad_profile))):
                    raise ValueError('invalid source quad split addresses')
            elif not (2<=len(set(rail))<=3 and 2<=len(set(profile))<=3):
                raise ValueError('invalid collapsed sweep cell addresses')
        if kind=='sweep_quad' and (len(set(rail))!=2 or len(set(profile))!=2):
            raise ValueError('quad does not span a source sweep cell')
        if kind=='sweep_cap' and len(set(rail))!=1:
            raise ValueError('cap spans multiple source sections')
    xyz = triangles[ids]
    cross = np.cross(xyz[:,1]-xyz[:,0],xyz[:,2]-xyz[:,0])
    double_area = np.linalg.norm(cross,axis=1)
    if np.any(double_area<1e-12):
        raise ValueError('degenerate sweep triangle')
    normals = cross/double_area[:,None]
    edge = np.roll(corners,-1,axis=0)-corners
    if np.any(np.cross(edge,np.roll(edge,-1,axis=0))@normal <= 1e-14):
        raise ValueError('nonconvex source sweep polygon')
    approximation=surface['approximation']
    if approximation['kind']!='source_sweep_sections':
        raise ValueError('invalid sweep approximation model')
    if kind=='sweep_quad':
        distance=np.linalg.norm(xyz[:,:,None,:]-corners,axis=-1)
        if np.max(np.min(distance,axis=-1))>2.1e-6:
            raise ValueError('mesh vertices disagree with sweep controls')
        address=np.argmin(distance,axis=-1)
        sets={frozenset(x) for x in address.tolist()}
        if len(ids)!=2 or sets not in ({frozenset((0,1,2)),frozenset((0,2,3))},{frozenset((0,1,3)),frozenset((1,2,3))}):
            raise ValueError('sweep cell triangle coverage is incomplete')
        a,b,c,d=corners
        twist=a-b+c-d
        bound=np.linalg.norm(twist)/4+2e-6
        tangent_normals=np.asarray([np.cross(b-a+v*twist,d-a+u*twist) for u,v in ((0,0),(0,1),(1,0),(1,1))])
        lengths=np.linalg.norm(tangent_normals,axis=1)
        if np.any(lengths<1e-12) or np.any(tangent_normals@normal<=0):
            raise ValueError('folded or degenerate bilinear sweep cell')
        tangent_normals/=lengths[:,None]
        cosine=normals@tangent_normals.T
        if np.any(cosine<=0):
            raise ValueError('mesh orientation disagrees with sweep')
        angle=float(np.degrees(np.arccos(np.clip(cosine,-1,1))).max())
    else:
        bound=2e-6
        if np.max(np.abs((corners-corners[0])@normal))>2.1e-6 or np.max(np.abs((xyz-corners[0])@normal))>2.1e-6:
            raise ValueError('sweep cap is not planar')
        for p,e in zip(corners,edge):
            if np.min(np.cross(e,xyz-p)@normal)<-2.1e-6*np.linalg.norm(e):
                raise ValueError('cap triangle exceeds source polygon')
        polygon_area=abs(sum(np.cross(corners[i],corners[(i+1)%len(corners)])@normal for i in range(len(corners))))/2
        # Source controls are stored as float32 mesh coordinates while the OBJ
        # stores rounded world coordinates. On small caps, their area error is
        # governed by edge length times position error, not area alone.
        perimeter=float(np.linalg.norm(edge,axis=1).sum())
        if abs(double_area.sum()/2-polygon_area)>max(1e-10,polygon_area*1e-4,perimeter*1e-7):
            raise ValueError('cap area coverage differs from source polygon')
        angle=float(np.degrees(np.arccos(np.clip(normals@normal,-1,1))).max())
        allowed_angle=0.1
        native_polygon = (provenance.get('primitive') in
                          ('native_opus_constructor', 'native_chair_constructor')
                          or provenance.get('source_polygon_triangulation') is True
                          or (provenance.get('primitive') == 'source_cap_triangulation'
                              and any(key in provenance for key in
                                      ('native_opus_source', 'native_chair_source'))))
        if kind == 'sweep_triangle' and native_polygon:
            residual=float(np.max(np.linalg.norm(xyz[0]-corners,axis=1)))
            altitude=float(double_area[0]/np.max(np.linalg.norm(edge,axis=1)))
            allowed_angle=max(allowed_angle,min(1.0,np.degrees(3*residual/altitude)))
        if angle>allowed_angle:
            raise ValueError('sweep cap normal mismatch')
    claimed=approximation['mesh_distance_bound_m']
    if not isinstance(claimed,(int,float)) or not math.isfinite(claimed) or abs(claimed-bound)>1e-9:
        raise ValueError('sweep approximation bound disagrees with source controls')
    return ids,angle

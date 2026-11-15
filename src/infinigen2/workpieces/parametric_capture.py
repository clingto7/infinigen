"""Generation-time surface capture for shared board and rod primitives.

The capture is opt-in. Face instance tags survive object joins, so the final
triangle mapping is derived from the delivered mesh rather than guessed from
constructor order or spatial proximity.
"""

from __future__ import annotations

from contextvars import ContextVar
from collections import Counter
from copy import deepcopy
import math

import numpy as np


_active: ContextVar[ParametricCapture | None] = ContextVar("parametric_capture", default=None)
_ATTRIBUTE = "parametric_instance"


def active_capture() -> ParametricCapture | None:
    return _active.get()


class ParametricCapture:
    def __init__(self):
        self.instances: list[dict] = []
        self.unsupported_primitives: list[dict] = []
        self.solid_operations: list[dict] = []
        self.bevel_sources: list[dict] = []
        self.native_surface_sources: list[dict] = []
        self._solid_refs: dict[int, int] = {}
        self._token = None

    def bevel_source(self, obj, primitive: str, bevel_width: float) -> None:
        """Retain faces before an explicit bevel operation changes topology."""
        mesh = obj.item().data
        if mesh.attributes.get('parametric_bevel_source_face') is not None:
            raise ValueError('bevel source already recorded')
        attr = mesh.attributes.new('parametric_bevel_source_face', 'INT', 'FACE')
        for face in mesh.polygons:
            attr.data[face.index].value = face.index + 1
        self.bevel_sources.append({
            'primitive': primitive, 'bevel_width_m': float(bevel_width),
            'source_face_corners': [
                [list(map(float, mesh.vertices[i].co)) for i in face.vertices]
                for face in mesh.polygons
            ],
        })

    def bevel_finish(self, obj, part: str, part_legend: dict[int, str] | None = None) -> bool:
        from .parametric_sweep import capture_bevel_patches
        if not self.bevel_sources:
            return False
        try:
            patches = capture_bevel_patches(obj, self.bevel_sources[-1])
        except ValueError as error:
            self.unsupported_primitives.append({'primitive':self.bevel_sources[-1]['primitive'],
                                                'part':part, 'reason':str(error)})
            return False
        record = {'kind':'sweep', 'part':part, 'patches':patches}
        mesh = obj.item().data
        if part_legend is not None:
            semantic = mesh.attributes.get('spray_part')
            if semantic is None or semantic.domain != 'FACE':
                raise ValueError('bevel source lacks semantic face parts')
            record['part_legend'] = dict(part_legend)
            source_parts = mesh.attributes.new('parametric_source_part', 'INT', 'FACE')
            for face in mesh.polygons:
                source_parts.data[face.index].value = semantic.data[face.index].value
        self._tag(obj, record)
        attr = mesh.attributes.new('parametric_patch', 'INT', 'FACE')
        for index, face in enumerate(attr.data, 1):
            face.value = index
        return True

    def solid_source(self, obj, kind: str, **parameters) -> None:
        """Record an executed shell constructor before Boolean operations."""
        key = obj.item().as_pointer()
        if key in self._solid_refs:
            raise ValueError('shell source recorded twice')
        ref = len(self.solid_operations) + 1
        self._solid_refs[key] = ref
        mesh = obj.item().data
        mesh.calc_loop_triangles()
        source_triangles = [[] for _ in mesh.polygons]
        for triangle in mesh.loop_triangles:
            polygon = mesh.polygons[triangle.polygon_index]
            indices = list(polygon.vertices)
            source_triangles[polygon.index].append(
                [indices.index(vertex) for vertex in triangle.vertices]
            )
        owner = mesh.attributes.new('parametric_solid_source', 'INT', 'FACE')
        face = mesh.attributes.new('parametric_solid_face', 'INT', 'FACE')
        for polygon in mesh.polygons:
            owner.data[polygon.index].value = ref
            face.data[polygon.index].value = polygon.index + 1
        self.solid_operations.append({'id': ref, 'operation': 'source',
                                      'primitive': kind, 'parameters': parameters,
                                      'source_face_count': len(mesh.polygons),
                                      'source_face_corners': [
                                          [list(map(float, mesh.vertices[i].co)) for i in polygon.vertices]
                                          for polygon in mesh.polygons
                                      ],
                                      'source_face_triangles': source_triangles})

    def native_surface_source(self, obj, *, kind: str, parameters: dict,
                              uv, faces) -> None:
        """Keep a native generator's source grid before a topology modifier.

        Point and face addresses are Blender attributes so the later solidify
        and join operations can be checked against this construction record.
        """
        mesh = obj.data
        uv = np.asarray(uv, dtype=float)
        faces = np.asarray(faces, dtype=int)
        if (uv.shape != (len(mesh.vertices), 2) or faces.ndim != 2
            or faces.shape[1] != 3 or len(faces) != len(mesh.polygons)
            or not np.isfinite(uv).all() or np.any(faces < 0)
            or np.any(faces >= len(uv))):
            raise ValueError('invalid native source grid')
        if any(tuple(face.vertices) != tuple(row) for face, row in zip(mesh.polygons, faces)):
            raise ValueError('native source faces disagree with constructed mesh')
        source_id = len(self.native_surface_sources) + 1
        owner = mesh.attributes.new('parametric_native_source', 'INT', 'FACE')
        face_id = mesh.attributes.new('parametric_native_face', 'INT', 'FACE')
        address = mesh.attributes.new('parametric_native_uv', 'FLOAT_VECTOR', 'POINT')
        for vertex, point in zip(mesh.vertices, uv):
            address.data[vertex.index].vector = (float(point[0]), float(point[1]), 0.0)
        for face in mesh.polygons:
            owner.data[face.index].value = source_id
            face_id.data[face.index].value = face.index + 1
        self.native_surface_sources.append({
            'id': source_id, 'kind': kind, 'parameters': parameters,
            'source_uv': uv.tolist(), 'source_faces': faces.tolist(),
            'source_vertex_normals': [list(map(float, vertex.normal)) for vertex in mesh.vertices],
        })

    def solid_boolean(self, host, tool, operation: str) -> None:
        host_ref = self._solid_refs.get(host.item().as_pointer())
        tool_ref = self._solid_refs.get(tool.item().as_pointer())
        if host_ref is None or tool_ref is None:
            self.unsupported_primitives.append({'primitive': 'shell_boolean',
                                                'reason': 'host or tool lacks a recorded source',
                                                'operation': operation})
            self._solid_refs.pop(host.item().as_pointer(), None)
            return
        self.solid_operations.append({'id': len(self.solid_operations) + 1,
                                      'operation': operation, 'host': host_ref,
                                      'tool': tool_ref})
        self._solid_refs[host.item().as_pointer()] = len(self.solid_operations)

    def solid_rebase_source(self, obj, kind: str, **parameters) -> None:
        """Record a source after a topology-changing constructor modifier."""
        mesh = obj.item().data
        self._solid_refs.pop(obj.item().as_pointer(), None)
        for name in ('parametric_solid_source', 'parametric_solid_face'):
            attr = mesh.attributes.get(name)
            if attr is not None:
                mesh.attributes.remove(attr)
        self.solid_source(obj, kind, **parameters)

    def solid_transform(self, obj, matrix) -> None:
        ref = self._solid_refs.get(obj.item().as_pointer())
        if ref is None:
            return
        self.solid_operations.append({'id': len(self.solid_operations) + 1,
                                      'operation': 'transform', 'source': ref,
                                      'matrix': np.asarray(matrix, dtype=float).tolist()})
        self._solid_refs[obj.item().as_pointer()] = len(self.solid_operations)

    def solid_ref(self, obj) -> int | None:
        return self._solid_refs.get(obj.item().as_pointer())

    def solid_forget(self, obj) -> None:
        self._solid_refs.pop(obj.item().as_pointer(), None)

    def solid_join(self, obj, refs: list[int | None]) -> None:
        if any(ref is None for ref in refs):
            self.unsupported_primitives.append({'primitive': 'shell_join',
                                                'reason': 'part lacks source construction'})
            return
        if len(refs) == 1:
            self._solid_refs[obj.item().as_pointer()] = refs[0]
            return
        self.solid_operations.append({'id': len(self.solid_operations) + 1,
                                      'operation': 'join', 'parts': refs})
        self._solid_refs[obj.item().as_pointer()] = len(self.solid_operations)

    def __enter__(self):
        if active_capture() is not None:
            raise RuntimeError("nested parametric capture")
        self._token = _active.set(self)
        return self

    def __exit__(self, *_):
        _active.reset(self._token)
        self._token = None

    def _tag(self, obj, record: dict) -> None:
        mesh = obj.item().data
        if mesh.attributes.get(_ATTRIBUTE) is not None:
            raise ValueError("primitive already captured")
        tag = mesh.attributes.new(_ATTRIBUTE, "INT", "FACE")
        instance_id = len(self.instances) + 1
        for face in tag.data:
            face.value = instance_id
        record["instance_id"] = instance_id
        record["transform"] = np.asarray(obj.item().matrix_world, dtype=float).tolist()
        if record["kind"] in {"board", "sweep"}:
            # Correspondences follow joins and object transforms. These are
            # source coordinates, not geometry inferred from the final mesh.
            source = mesh.attributes.get("parametric_source_position")
            if source is None:
                source = mesh.attributes.new("parametric_source_position", "FLOAT_VECTOR", "CORNER")
            for loop in mesh.loops:
                source.data[loop.index].vector = mesh.vertices[loop.vertex_index].co
        self.instances.append(record)

    def duplicate(self, obj) -> None:
        """Give a copied construction its own source instance before placement."""
        mesh = obj.item().data
        owner = mesh.attributes.get(_ATTRIBUTE)
        if owner is None or owner.domain != 'FACE':
            return
        previous = sorted({face.value for face in owner.data if face.value > 0})
        for old_id in previous:
            if old_id > len(self.instances):
                raise ValueError(f'unknown captured instance {old_id} on clone')
            clone = deepcopy(self.instances[old_id - 1])
            new_id = len(self.instances) + 1
            clone['instance_id'] = new_id
            for face in owner.data:
                if face.value == old_id:
                    face.value = new_id
            self.instances.append(clone)

    def mirror_duplicate(self, obj, original_face_count: int) -> None:
        """Give faces created by a known mirror operation independent sources."""
        mesh = obj.item().data
        owner = mesh.attributes.get(_ATTRIBUTE)
        if owner is None or len(mesh.polygons) != 2 * original_face_count:
            raise ValueError('mirror did not preserve two source face sets')
        original = [face.value for face in owner.data[:original_face_count]]
        mirrored = [face.value for face in owner.data[original_face_count:]]
        if original != mirrored:
            raise ValueError('mirror lost source face order or instance tags')
        for old_id in sorted(set(mirrored) - {0}):
            if old_id > len(self.instances):
                raise ValueError(f'unknown captured instance {old_id} in mirror')
            clone = deepcopy(self.instances[old_id - 1])
            new_id = len(self.instances) + 1
            clone['instance_id'] = new_id
            clone['reflected'] = True
            for index, value in enumerate(mirrored, original_face_count):
                if value == old_id:
                    owner.data[index].value = new_id
            self.instances.append(clone)

    def bar_pull(self, obj, grip_length: float, grip_radius: float,
                 standoff_length: float, standoff_radius: float,
                 part: str) -> None:
        """Capture the three cylinders laid out by the bar-pull constructor."""
        mesh = obj.item().data
        components = mesh.attributes.get('parametric_handle_component')
        if components is None or components.domain != 'FACE':
            raise ValueError('bar pull lost cylinder component addresses')
        if {face.value for face in components.data} != {1, 2, 3}:
            raise ValueError('bar pull cylinder components are incomplete')
        component_values = [face.value for face in components.data]
        mesh.attributes.new(_ATTRIBUTE, 'INT', 'FACE')
        mesh.attributes.new('parametric_source_position', 'FLOAT_VECTOR', 'CORNER')
        owner = mesh.attributes[_ATTRIBUTE]
        source = mesh.attributes['parametric_source_position']
        for loop in mesh.loops:
            source.data[loop.index].vector = mesh.vertices[loop.vertex_index].co
        z = grip_length * 0.5 - grip_radius
        specs = (
            ((standoff_length, 0, -grip_length * 0.5),
             (standoff_length, 0, grip_length * 0.5), grip_radius,
             (1, 0, 0), (0, 1, 0)),
            ((0, 0, z), (standoff_length, 0, z), standoff_radius,
             (0, 1, 0), (0, 0, 1)),
            ((0, 0, -z), (standoff_length, 0, -z), standoff_radius,
             (0, 1, 0), (0, 0, 1)),
        )
        for component, (start, end, radius, radial_u, radial_v) in enumerate(specs, 1):
            instance_id = len(self.instances) + 1
            for face in mesh.polygons:
                if component_values[face.index] == component:
                    owner.data[face.index].value = instance_id
            self.instances.append({
                'instance_id': instance_id, 'kind': 'rod_local', 'part': part,
                'start': list(start), 'end': list(end), 'radius': float(radius),
                'resolution': 16, 'radial_u': list(radial_u),
                'radial_v': list(radial_v),
                'transform': np.asarray(obj.item().matrix_world, dtype=float).tolist(),
            })

    def knob(self, obj, base_radius: float, base_depth: float,
             stem_radius: float, stem_length: float, head_radius: float,
             part: str) -> None:
        """Capture two source cylinders and the UV sphere of a knob."""
        mesh = obj.item().data
        components = mesh.attributes.get('parametric_handle_component')
        rail = mesh.attributes.get('parametric_rail_index')
        profile = mesh.attributes.get('parametric_profile_index')
        if (components is None or components.domain != 'FACE' or
            rail is None or rail.domain != 'CORNER' or
            profile is None or profile.domain != 'CORNER' or
            {face.value for face in components.data} != {1, 2, 3}):
            raise ValueError('knob lost source component or sphere addresses')
        component_values = [face.value for face in components.data]
        rail_values = [corner.value for corner in rail.data]
        profile_values = [corner.value for corner in profile.data]
        mesh.attributes.new(_ATTRIBUTE, 'INT', 'FACE')
        mesh.attributes.new('parametric_source_position', 'FLOAT_VECTOR', 'CORNER')
        mesh.attributes.new('parametric_patch', 'INT', 'FACE')
        owner = mesh.attributes[_ATTRIBUTE]
        source = mesh.attributes['parametric_source_position']
        patch_ids = mesh.attributes['parametric_patch']
        for loop in mesh.loops:
            source.data[loop.index].vector = mesh.vertices[loop.vertex_index].co
        angle = 1.5708
        sine, cosine = math.sin(angle), math.cos(angle)
        axis = np.asarray((sine, 0.0, cosine))
        radial_u = (cosine, 0.0, -sine)
        radial_v = (0.0, 1.0, 0.0)
        specs = (
            (axis * 0.0, axis * base_depth, base_radius, 12),
            (axis * (base_depth * 0.5),
             axis * (base_depth + stem_length), stem_radius, 8),
        )
        for component, (start, end, radius, resolution) in enumerate(specs, 1):
            instance_id = len(self.instances) + 1
            for face in mesh.polygons:
                if component_values[face.index] == component:
                    owner.data[face.index].value = instance_id
            self.instances.append({
                'instance_id': instance_id, 'kind': 'rod_local', 'part': part,
                'start': start.tolist(), 'end': end.tolist(),
                'radius': float(radius), 'resolution': resolution,
                'radial_u': list(radial_u), 'radial_v': list(radial_v),
                'transform': np.asarray(obj.item().matrix_world, dtype=float).tolist(),
            })
        center = (axis * (base_depth + stem_length)).tolist()
        axes = [
            (np.asarray(radial_u) * head_radius).tolist(),
            (np.asarray(radial_v) * head_radius).tolist(),
            (axis * (head_radius * 0.8)).tolist(),
        ]
        patches = []
        instance_id = len(self.instances) + 1
        for face in mesh.polygons:
            if component_values[face.index] != 3:
                continue
            if len(face.vertices) not in (3, 4):
                raise ValueError('unsupported knob sphere face topology')
            corners = [list(map(float, mesh.vertices[i].co)) for i in face.vertices]
            rails = [float(rail_values[i]) for i in face.loop_indices]
            profiles = [float(profile_values[i]) for i in face.loop_indices]
            if min(rails + profiles) <= 0:
                raise ValueError('knob sphere lost section addresses')
            patches.append({
                'type': 'sweep_quad' if len(corners) == 4 else 'sweep_triangle',
                'corners': corners, 'source_rail_indices': rails,
                'source_profile_indices': profiles,
                'uv_sphere_source': {'center': center, 'axes': axes,
                                     'segments': 12, 'rings': 8,
                                     'source_face_id': len(patches) + 1},
            })
            owner.data[face.index].value = instance_id
            patch_ids.data[face.index].value = len(patches)
        if not patches:
            raise ValueError('knob sphere has no source faces')
        self.instances.append({
            'instance_id': instance_id, 'kind': 'sweep', 'part': part,
            'patches': patches,
            'transform': np.asarray(obj.item().matrix_world, dtype=float).tolist(),
        })

    def sweep(self, obj, part, *, allow_removed_source_patches: bool = False,
              triangulate_source_caps: bool = False) -> bool:
        from .parametric_sweep import capture_patches
        try:
            patches = capture_patches(obj)
        except ValueError as error:
            self.unsupported_primitives.append({"primitive": "curve_to_mesh_with_uv", "part": part, "reason": str(error)})
            return False
        if not patches:
            return False
        self._tag(obj, {"kind": "sweep", "part": part, "patches": patches,
                        "allow_removed_source_patches": allow_removed_source_patches,
                        "triangulate_source_caps": triangulate_source_caps})
        attr = obj.item().data.attributes.new("parametric_patch", "INT", "FACE")
        for index, face in enumerate(attr.data, 1):
            face.value = index
        return True

    def native_opus(self, obj, part: str, constructor: str, parameters: dict) -> None:
        from .parametric_sweep import capture_native_opus_patches
        import procfunc as pf
        patches = capture_native_opus_patches(obj, constructor, parameters)
        wrapped = pf.MeshObject(obj)
        self._tag(wrapped, {'kind': 'sweep', 'part': part, 'patches': patches,
                            'allow_removed_source_patches': True,
                            'triangulate_source_caps': True})
        attr = obj.data.attributes.new('parametric_patch', 'INT', 'FACE')
        for index, face in enumerate(attr.data, 1):
            face.value = index

    def native_chair(self, obj, part: str, constructor: str, parameters: dict) -> None:
        from .parametric_sweep import capture_native_mesh_patches
        import procfunc as pf
        patches = capture_native_mesh_patches(obj, constructor, parameters,
                                              'native_chair_source')
        self._tag(pf.MeshObject(obj), {
            'kind': 'sweep', 'part': part, 'patches': patches,
            'allow_removed_source_patches': True,
            'triangulate_source_caps': True,
        })
        attr = obj.data.attributes.new('parametric_patch', 'INT', 'FACE')
        for index, face in enumerate(attr.data, 1):
            face.value = index

    def box(self, obj, size, location, anchor, part) -> None:
        center = np.asarray(location) + (0.5 - np.asarray(anchor)) * np.asarray(size)
        self._tag(obj, {"kind": "board", "size": list(map(float, size)),
                        "local_center": center.tolist(), "part": part})

    def grid(self, obj, part, source: dict | None = None) -> bool:
        from .parametric_sweep import capture_grid_patches
        try:
            patches = capture_grid_patches(obj)
        except ValueError as error:
            self.unsupported_primitives.append({"primitive": "ruled_grid_extrusion",
                                                "part": part, "reason": str(error)})
            return False
        if not patches:
            return False
        if source is not None:
            for patch in patches:
                patch['support_loop_box_source'] = deepcopy(source)
        self._tag(obj, {"kind": "sweep", "part": part, "patches": patches})
        attr = obj.item().data.attributes.new("parametric_patch", "INT", "FACE")
        for index, face in enumerate(attr.data, 1):
            face.value = index
        return True

    def mixed_sweep_grid(self, obj, part) -> bool:
        """Capture one known constructor's swept slats and ruled-grid rail."""
        from .parametric_sweep import capture_grid_patches, capture_patches
        mesh = obj.item().data
        component = mesh.attributes.get('parametric_back_component')
        if component is None or component.domain != 'FACE':
            raise ValueError('slatted back lost source component addresses')
        values = [face.value for face in component.data]
        if set(values) != {1, 2}:
            raise ValueError('slatted back lacks sweep or grid source')
        sweep_ids = [i for i, value in enumerate(values) if value == 1]
        grid_ids = [i for i, value in enumerate(values) if value == 2]
        sweep = capture_patches(obj, sweep_ids)
        grid = capture_grid_patches(obj, grid_ids)
        if not sweep or len(sweep) != len(sweep_ids) or len(grid) != len(grid_ids):
            raise ValueError('slatted back source cells are incomplete')
        patches = [None] * len(values)
        for index, patch in zip(sweep_ids, sweep):
            patches[index] = patch
        for index, patch in zip(grid_ids, grid):
            patches[index] = patch
        self._tag(obj, {'kind':'sweep', 'part':part, 'patches':patches,
                        'triangulate_source_caps':True})
        attr = mesh.attributes.new('parametric_patch', 'INT', 'FACE')
        for index, face in enumerate(attr.data, 1):
            face.value = index
        return True

    def window_frame(self, obj, parameters: dict) -> None:
        """Capture a window constructor's frame, grid, and sash or shutter."""
        from .parametric_sweep import capture_window_patches
        mesh = obj.item().data
        attr = mesh.attributes.get('parametric_window_component')
        if attr is None or attr.domain != 'FACE':
            raise ValueError('window frame lost source component tags')
        components = [face.value for face in attr.data]
        if 1 not in components or any(value not in (1, 2, 3) for value in components):
            raise ValueError('window frame lacks an outer source or has unknown components')
        patches = capture_window_patches(obj, components)
        for patch in patches:
            patch['window_source']['parameters'] = deepcopy(parameters)
        self._tag(obj, {'kind':'sweep', 'part':'window_frame', 'patches':patches})
        patch_ids = mesh.attributes.new('parametric_patch', 'INT', 'FACE')
        for index, face in enumerate(patch_ids.data, 1):
            face.value = index

    def wheeled_base(self, obj, parameters: dict) -> None:
        """Capture the post and repeated castor arms of the sampled base."""
        from .parametric_sweep import capture_wheeled_patches
        mesh = obj.item().data
        attr = mesh.attributes.get('parametric_wheeled_component')
        if attr is None or attr.domain != 'FACE':
            raise ValueError('wheeled base lost source component tags')
        components = [face.value for face in attr.data]
        if set(components) != {1, 2}:
            raise ValueError('wheeled base lacks post or castor arms')
        patches = capture_wheeled_patches(obj, components)
        for patch in patches:
            if patch is not None:
                patch['wheeled_source']['parameters'] = deepcopy(parameters)
        self._tag(obj, {'kind':'sweep', 'part':'wheeled_base', 'patches':patches,
                        'allow_removed_source_patches':True,
                        'triangulate_source_caps':True})
        patch_ids = mesh.attributes.new('parametric_patch', 'INT', 'FACE')
        for index, face in enumerate(patch_ids.data, 1):
            face.value = index

    def curvy_seat(self, obj, parameters: dict) -> None:
        """Capture the sampled 16×11 loft before chair assembly."""
        from .parametric_sweep import capture_patches
        mesh = obj.item().data
        u, v = int(parameters['u_resolution']), int(parameters['v_resolution'])
        if (u != 16 or v != 11 or len(mesh.vertices) != u * v or
                len(mesh.polygons) != u * (v - 1) + 2 or
                len(mesh.polygons[0].vertices) != u or
                len(mesh.polygons[-1].vertices) != u or
                any(len(face.vertices) != 4 for face in list(mesh.polygons)[1:-1])):
            raise ValueError('curvy seat lost its sampled loft topology')
        rail = mesh.attributes.new('parametric_rail_index', 'FLOAT', 'CORNER')
        profile = mesh.attributes.new('parametric_profile_index', 'FLOAT', 'CORNER')
        for loop in mesh.loops:
            rail.data[loop.index].value = loop.vertex_index // u + 1
            profile.data[loop.index].value = loop.vertex_index % u + 1
        patches = [None] + capture_patches(obj, range(1, len(mesh.polygons) - 1))
        for patch in patches[1:]:
            # The first loft row can twist sharply. The constructor's two
            # source triangles preserve its actual piecewise normal field.
            patch['type'] = 'sweep_split_quad'
        cap = mesh.polygons[-1]
        patches.append({
            'type': 'sweep_cap',
            'corners': [list(map(float, mesh.vertices[i].co)) for i in cap.vertices],
            'source_rail_indices': [v] * u,
            'source_profile_indices': [int(i % u + 1) for i in cap.vertices],
        })
        sampled = {key: int(value) if key in ('u_resolution', 'v_resolution') else float(value)
                   for key, value in parameters.items()}
        for source_id, patch in enumerate(patches, 1):
            if patch is not None:
                patch['curvy_seat_source'] = {
                    'source_face_id': source_id, 'parameters': sampled,
                }
        self._tag(obj, {'kind': 'sweep', 'part': 'seat', 'patches': patches,
                        'allow_removed_source_patches': True,
                        'triangulate_source_caps': True})
        ids = mesh.attributes.new('parametric_patch', 'INT', 'FACE')
        for index, face in enumerate(ids.data, 1):
            face.value = index

    def board(self, obj, size, part) -> None:
        self._tag(obj, {"kind": "board", "size": list(map(float, size)),
                        "local_center": [0.0, 0.0, 0.0], "part": part})

    def slab(self, obj, size, part) -> None:
        """Capture a table-top box whose local Z range is [0, thickness]."""
        self._tag(obj, {"kind": "board", "size": list(map(float, size)),
                        "local_center": [0.0, 0.0, float(size[2]) * 0.5],
                        "part": part})

    def rod(self, obj, start, end, radius, resolution, part) -> None:
        self._tag(obj, {
            "kind": "rod", "start": list(map(float, start)),
            "end": list(map(float, end)), "radius": float(radius),
            "resolution": int(resolution), "part": part,
        })

    def triangle_prism(self, obj, size_x, size_y, thick, z, part) -> None:
        """Capture the five source faces of a right-triangle shelf."""
        mesh = obj.item().data
        if len(mesh.polygons) != 5:
            raise ValueError("triangle prism must have five source faces")
        self._tag(obj, {"kind": "triangle_prism", "size_x": float(size_x),
                        "size_y": float(size_y), "thick": float(thick),
                        "z": float(z), "part": part})
        patches = mesh.attributes.new("parametric_patch", "INT", "FACE")
        for index, face in enumerate(patches.data, 1):
            face.value = index

    def export(self, obj) -> dict:
        """Return a mesh-free parametric artifact in the final OBJ frame (meters)."""
        mesh = obj.item().data
        mesh.calc_loop_triangles()
        attr = mesh.attributes.get(_ATTRIBUTE)
        if attr is None or attr.domain != "FACE":
            raise ValueError("final mesh lost parametric instance tags")
        world = np.asarray(obj.item().matrix_world, dtype=float)
        vertices = np.asarray([world[:3, :3] @ np.asarray(v.co) + world[:3, 3] for v in mesh.vertices])
        triangles = np.asarray([t.vertices[:] for t in mesh.loop_triangles], dtype=int)
        triangle_vertices = vertices[triangles]
        owners = np.asarray([attr.data[t.polygon_index].value for t in mesh.loop_triangles], dtype=int)
        target_attr = mesh.attributes.get("spray_target")
        if target_attr is None or target_attr.domain != "FACE":
            raise ValueError("final mesh lacks spray_target")
        targets = np.asarray([bool(target_attr.data[t.polygon_index].value) for t in mesh.loop_triangles])
        parts = []
        used = set()
        worst_normal_angle = 0.0
        for record in self.instances:
            ids = np.flatnonzero(owners == record["instance_id"])
            if len(ids) == 0:
                raise ValueError(f"instance {record['instance_id']} has no final triangles")
            if record["kind"] in {"board", "sweep", "rod_local"}:
                record = dict(record)
                source = mesh.attributes.get("parametric_source_position")
                if source is None or source.domain != "CORNER":
                    raise ValueError("board lost source coordinate correspondences")
                coords = np.asarray([[source.data[i].vector[:] for i in mesh.loop_triangles[t].loops]
                                     for t in ids]).reshape(-1, 3)
                destination = triangle_vertices[ids].reshape(-1, 3)
                design = np.column_stack((coords, np.ones(len(coords))))
                affine, _, rank, _ = np.linalg.lstsq(design, destination, rcond=None)
                if rank != 4 or np.max(np.abs(design @ affine - destination)) > 2e-6:
                    raise ValueError("board source correspondences were deformed")
                linear = affine[:3].T
                centered_source = coords - coords.mean(axis=0)
                centered_destination = destination - destination.mean(axis=0)
                left, scales, right = np.linalg.svd(centered_source.T @ centered_destination)
                similarity = (right.T @ left.T) * (scales.sum() / np.sum(centered_source ** 2))
                offset = destination.mean(axis=0) - similarity @ coords.mean(axis=0)
                # Float32 source coordinates on thin boards amplify matrix
                # coefficient error. Test the physical residual, not coefficients.
                orientation = -1 if record.get('reflected') else 1
                if np.linalg.det(linear) * orientation <= 0 or np.max(np.abs(
                    coords @ similarity.T + offset - destination
                )) > 2e-6:
                    raise ValueError("board requires a rigid transform or positive uniform scale")
                transform = np.eye(4)
                transform[:3, :3] = similarity
                transform[:3, 3] = offset
                record["transform"] = transform.tolist()
                if record["kind"] == "board":
                    surfaces = self._board_surfaces(record, ids, triangle_vertices[ids])
                elif record["kind"] == "sweep":
                    from .parametric_sweep import export_patches
                    patch_attr = mesh.attributes.get("parametric_patch")
                    if patch_attr is None:
                        raise ValueError("sweep lost patch tags")
                    patches = np.asarray([patch_attr.data[t.polygon_index].value for t in mesh.loop_triangles])
                    surfaces = export_patches(record, ids, patches[ids], coords.reshape(-1, 3, 3))
                else:
                    surfaces = self._rod_surfaces(record, ids, triangle_vertices[ids])
            elif record["kind"] == "rod":
                surfaces = self._rod_surfaces(record, ids, triangle_vertices[ids])
            elif record["kind"] == "triangle_prism":
                patch_attr = mesh.attributes.get("parametric_patch")
                if patch_attr is None or patch_attr.domain != "FACE":
                    raise ValueError("triangle prism lost source patch tags")
                patches = np.asarray([patch_attr.data[t.polygon_index].value for t in mesh.loop_triangles])
                surfaces = self._triangle_prism_surfaces(record, ids, patches[ids])
            else:
                raise ValueError(f"unsupported captured primitive: {record['kind']}")
            for surface in surfaces:
                overlap = used.intersection(surface["mesh_mapping"]["construction_triangle_ids"])
                if overlap:
                    raise ValueError(f"duplicate triangle mapping: {sorted(overlap)[:5]}")
                used.update(surface["mesh_mapping"]["construction_triangle_ids"])
                worst_normal_angle = max(
                    worst_normal_angle,
                    self._check_surface(surface, triangle_vertices, record),
                )
            if 'part_legend' in record:
                semantic_attr = mesh.attributes.get('parametric_source_part')
                if semantic_attr is None or semantic_attr.domain != 'FACE':
                    raise ValueError('bevel lost semantic source parts')
                codes = np.asarray([semantic_attr.data[t.polygon_index].value
                                    for t in mesh.loop_triangles], dtype=int)
                grouped: dict[int, list[dict]] = {}
                for surface in surfaces:
                    surface_codes = set(codes[surface['mesh_mapping']['construction_triangle_ids']])
                    if len(surface_codes) != 1:
                        raise ValueError('source bevel surface crosses semantic parts')
                    code = surface_codes.pop()
                    if code not in record['part_legend']:
                        raise ValueError(f'unknown source bevel part {code}')
                    grouped.setdefault(code, []).append(surface)
                for code, group in grouped.items():
                    parts.append({"id": f"instance_{record['instance_id']}:part_{code}",
                                  "semantic": record['part_legend'][code], "surfaces": group})
            else:
                parts.append({"id": f"instance_{record['instance_id']}", "semantic": record["part"], "surfaces": surfaces})
        target_ids = set(np.flatnonzero(targets).tolist())
        missing = target_ids - used
        if missing:
            raise ValueError(f"{len(missing)} spray_target triangles lack parametric surfaces")
        return {
            "schema": "spraybot.parametric.v3" if any(rec["kind"] == "sweep" for rec in self.instances) else "spraybot.parametric.v2" if any(
                rec["kind"] == "triangle_prism" for rec in self.instances
            ) else "spraybot.parametric.v1",
            "unit": "m", "frame": "exported_obj_axes_origin",
            "obj_unit": "mm", "obj_mm_per_parametric_m": 1000,
            "mesh_triangle_order": "OBJ faces and face_attributes.npz rows, zero-based",
            "parts": parts,
            "description_coverage": {
                "spray_target_triangle_count": len(target_ids),
                "represented_target_triangle_count": len(target_ids),
                "unrepresented_non_target_triangle_ids": sorted(set(range(len(triangles))) - used),
            },
            "validation": {"max_mesh_to_surface_normal_angle_deg": worst_normal_angle},
        }

    def coverage(self, obj, part_legend) -> dict:
        """Report source-tag coverage even if surface export is incomplete.

        Tagged does not mean validated. Keep that distinction in diagnostic
        names so a failed geometry check cannot be mistaken for approval.
        """
        mesh = obj.item().data
        mesh.calc_loop_triangles()
        target = mesh.attributes.get("spray_target")
        part = mesh.attributes.get("spray_part")
        tag = mesh.attributes.get(_ATTRIBUTE)
        missing = []
        counts = Counter()
        targets = 0
        for index, triangle in enumerate(mesh.loop_triangles):
            polygon = triangle.polygon_index
            if target is None or not target.data[polygon].value:
                continue
            targets += 1
            if tag is not None and tag.data[polygon].value > 0:
                continue
            missing.append(index)
            code = part.data[polygon].value if part is not None else -1
            counts[str(part_legend.get(code, part_legend.get(str(code), code)))] += 1
        return {"unsupported_primitives": self.unsupported_primitives,
                "solid_construction": self.solid_operations,
                "captured_instances": len(self.instances), "target_triangles": targets,
                "tagged_target_triangles": targets - len(missing),
                "untagged_target_triangle_ids": missing, "missing_by_part": dict(counts)}

    @staticmethod
    def _mapping(ids) -> dict:
        values = ids.tolist()
        return {"construction_triangle_ids": values, "support_triangle_ids": values}

    @staticmethod
    def _check_surface(surface, all_triangles, record) -> float:
        ids = surface["mesh_mapping"]["construction_triangle_ids"]
        vertices = all_triangles[ids]
        cross = np.cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0])
        lengths = np.linalg.norm(cross, axis=1)
        if np.any(lengths < 1e-12):
            raise ValueError(f"degenerate mapped triangle on {surface['id']}")
        mesh_normal = cross / lengths[:, None]
        geometry = surface["geometry"]
        if surface["type"] == "sweep_quad":
            corners = np.asarray(geometry["corners"])
            if np.max(np.min(np.linalg.norm(vertices[:, :, None] - corners, axis=-1), axis=-1)) > 2e-6:
                raise ValueError("sweep quad final vertices differ from source corners")
            expected = np.asarray(geometry["normal"])
            if np.any(mesh_normal @ expected <= 0):
                raise ValueError("sweep quad is folded or reversed")
            return float(np.degrees(np.arccos(np.clip(mesh_normal @ expected, -1, 1))).max())
        elif surface["type"] in {"sweep_cap", "sweep_triangle"}:
            expected = np.asarray(geometry["normal"])
            distance = np.abs((vertices - geometry["corners"][0]) @ expected)
            bound = 2e-6
        elif surface["type"] in {"plane_rectangle", "plane_triangle"}:
            expected = np.asarray(geometry["normal"])
            distance = np.abs((vertices - geometry["origin"]) @ expected)
            bound = 2e-6
        else:
            axis = np.asarray(geometry["axis"])
            origin = np.asarray(geometry["origin"])
            axial = (vertices - origin) @ axis
            if surface["type"] == "cylinder_side":
                centers = vertices.mean(axis=1)
                radial = centers - origin - ((centers - origin) @ axis)[:, None] * axis
                expected = radial / np.linalg.norm(radial, axis=1)[:, None]
                distance = np.abs(np.linalg.norm(
                    vertices - origin - axial[:, :, None] * axis, axis=2
                ) - geometry["radius_m"])
                bound = 2e-6
            else:
                expected = geometry["normal_sign"] * axis
                distance = np.abs(axial - geometry["axial_fraction"] * geometry["length_m"])
                bound = 2e-6
        if np.max(distance) > bound:
            raise ValueError(f"surface position mismatch on {surface['id']}")
        cosine = np.sum(mesh_normal * expected, axis=1)
        angle = float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))).max())
        allowed = 180 / record["resolution"] + 0.1 if surface["type"] == "cylinder_side" else 0.1
        provenance = surface.get('provenance', {})
        native_polygon = (provenance.get('primitive') in
                          ('native_opus_constructor', 'native_chair_constructor')
                          or provenance.get('source_polygon_triangulation') is True
                          or (provenance.get('primitive') == 'source_cap_triangulation'
                              and any(key in provenance for key in
                                      ('native_opus_source', 'native_chair_source'))))
        if surface['type'] == 'sweep_triangle' and native_polygon:
            source = np.asarray(geometry['corners'], dtype=float)
            residual = float(np.max(np.linalg.norm(vertices[0] - source, axis=1)))
            longest = float(max(np.linalg.norm(source[i]-source[(i+1)%3]) for i in range(3)))
            altitude = float(lengths[0] / longest)
            allowed = max(allowed, min(1.0, np.degrees(3 * residual / altitude)))
        if angle > allowed:
            raise ValueError(f"outward normal mismatch on {surface['id']}: {angle:.3f} deg")
        return angle

    def _triangle_prism_surfaces(self, record, ids, patches):
        matrix = np.asarray(record["transform"])
        rotation = matrix[:3, :3]
        translation = matrix[:3, 3]
        sx, sy, thick, z = (record[key] for key in ("size_x", "size_y", "thick", "z"))
        if min(sx, sy, thick) <= 0 or not np.allclose(rotation.T @ rotation, np.eye(3), atol=1e-5):
            raise ValueError("triangle prism dimensions or transform are invalid")

        def point(x, y, height):
            return (rotation @ np.array([x, y, height]) + translation).tolist()

        def direction(x, y, height):
            return (rotation @ np.array([x, y, height])).tolist()

        diagonal_normal = np.array([sy, sx, 0.0])
        diagonal_normal /= np.linalg.norm(diagonal_normal)
        descriptions = (
            ("bottom", "plane_triangle", (0, 0, z), (sx, 0, 0), (0, sy, 0), (0, 0, -1)),
            ("top", "plane_triangle", (0, 0, z + thick), (sx, 0, 0), (0, sy, 0), (0, 0, 1)),
            ("wall_y0", "plane_rectangle", (0, 0, z), (sx, 0, 0), (0, 0, thick), (0, -1, 0)),
            ("wall_x0", "plane_rectangle", (0, 0, z), (0, sy, 0), (0, 0, thick), (-1, 0, 0)),
            ("wall_diagonal", "plane_rectangle", (sx, 0, z), (-sx, sy, 0), (0, 0, thick), diagonal_normal),
        )
        surfaces = []
        for index, (name, kind, origin, u, v, normal) in enumerate(descriptions, 1):
            face_ids = ids[patches == index]
            if len(face_ids) == 0:
                raise ValueError(f"triangle prism lost patch {index}")
            surfaces.append({
                "id": f"instance_{record['instance_id']}:{name}", "type": kind,
                "domain": {"u": [0, 1], "v": [0, 1], "constraint": "u+v<=1"}
                if kind == "plane_triangle" else {"u": [0, 1], "v": [0, 1]},
                "periodic_v": False,
                "geometry": {"origin": point(*origin), "u": direction(*u),
                             "v": direction(*v), "normal": direction(*normal)},
                "mesh_mapping": self._mapping(face_ids),
                "approximation": {"kind": "source_roundoff", "mesh_distance_bound_m": 2e-6},
            })
        if sum(len(surface["mesh_mapping"]["construction_triangle_ids"]) for surface in surfaces) != len(ids):
            raise ValueError("triangle prism patch partition failed")
        return surfaces

    def _board_surfaces(self, record, ids, triangle_vertices):
        matrix = np.asarray(record["transform"])
        rotation = matrix[:3, :3]
        center = rotation @ np.asarray(record["local_center"]) + matrix[:3, 3]
        size = np.asarray(record["size"])
        local = (triangle_vertices - center) @ np.linalg.inv(rotation).T
        surfaces = []
        for axis in range(3):
            for sign in (-1, 1):
                mask = np.max(np.abs(local[:, :, axis] - sign * size[axis] / 2), axis=1) < 2e-6
                if not mask.any():
                    raise ValueError("board plane has no final triangles")
                if np.any(np.abs(local[mask]) > size / 2 + 2e-6):
                    raise ValueError("board vertices exceed captured dimensions")
                other = [i for i in range(3) if i != axis]
                corner = -size / 2
                corner[axis] = sign * size[axis] / 2
                u = np.zeros(3); u[other[0]] = size[other[0]]
                v = np.zeros(3); v[other[1]] = size[other[1]]
                normal = np.zeros(3); normal[axis] = sign
                face_ids = ids[mask]
                surfaces.append({
                    "id": f"instance_{record['instance_id']}:plane_{axis}_{sign}",
                    "type": "plane_rectangle", "domain": {"u": [0, 1], "v": [0, 1]},
                    "periodic_v": False,
                    "geometry": {"origin": (rotation @ corner + center).tolist(),
                                 "u": (rotation @ u).tolist(), "v": (rotation @ v).tolist(),
                                 "normal": ((rotation @ normal) / np.linalg.norm(rotation @ normal)).tolist()},
                    "mesh_mapping": self._mapping(face_ids),
                    "approximation": {"kind": "source_roundoff", "mesh_distance_bound_m": 2e-6},
                })
        if sum(len(s["mesh_mapping"]["construction_triangle_ids"]) for s in surfaces) != len(ids):
            raise ValueError("board triangle partition failed")
        return surfaces

    def _rod_surfaces(self, record, ids, triangle_vertices):
        matrix = np.asarray(record["transform"])
        start = np.asarray(record["start"]); end = np.asarray(record["end"])
        if record["kind"] == "rod_local":
            start = matrix[:3, :3] @ start + matrix[:3, 3]
            end = matrix[:3, :3] @ end + matrix[:3, 3]
            radial_u = matrix[:3, :3] @ np.asarray(record['radial_u'])
            radial_v = matrix[:3, :3] @ np.asarray(record['radial_v'])
            radius = record['radius'] * np.linalg.norm(radial_u)
            radial_u /= np.linalg.norm(radial_u)
            radial_v /= np.linalg.norm(radial_v)
            if record.get('reflected'):
                radial_v = -radial_v
        else:
            radial_u = matrix[:3, 0]; radial_u /= np.linalg.norm(radial_u)
            radial_v = matrix[:3, 1]; radial_v /= np.linalg.norm(radial_v)
            radius = record["radius"]
        length = float(np.linalg.norm(end - start))
        axis = (end - start) / length
        axial = (triangle_vertices - start) @ axis
        bottom = np.max(np.abs(axial), axis=1) < 2e-6
        top = np.max(np.abs(axial - length), axis=1) < 2e-6
        wall = ~(bottom | top)
        if not (bottom.any() and top.any() and wall.any()):
            raise ValueError("rod cap/side partition failed")
        radial = triangle_vertices - start - axial[:, :, None] * axis
        if np.max(np.abs(np.linalg.norm(radial[wall], axis=2) - radius)) > 2e-6:
            raise ValueError("rod wall vertices disagree with captured radius")
        common = {"origin": start.tolist(), "axis": axis.tolist(),
                  "radial_u": radial_u.tolist(), "radial_v": radial_v.tolist(),
                  "radius_m": radius, "length_m": length,
                  "angular_segments": record["resolution"]}
        approximation = {"kind": "inscribed_polygon_mesh",
                         "mesh_distance_bound_m": radius * (1 - math.cos(math.pi / record["resolution"])) + 2e-6,
                         "mesh_normal_bound_deg": 180 / record["resolution"] + 0.05}
        surfaces = []
        for name, kind, mask, axial_fraction, normal_sign in (
            ("wall", "cylinder_side", wall, None, None),
            ("bottom", "disk", bottom, 0, -1),
            ("top", "disk", top, 1, 1),
        ):
            geometry = dict(common)
            if kind == "disk":
                geometry.update(axial_fraction=axial_fraction, normal_sign=normal_sign)
            surfaces.append({
                "id": f"instance_{record['instance_id']}:{name}", "type": kind,
                "domain": {"u": [0, 1], "v": [0, 1]}, "periodic_v": True,
                "geometry": geometry, "mesh_mapping": self._mapping(ids[mask]),
                "approximation": approximation,
            })
        return surfaces

"""Current Infinigen chair generator exposed as a Spraybot category."""

import bmesh
import numpy as np
import procfunc as pf

from infinigen2.workpieces.native_spraybot.common import BuiltWorkpiece, category, json_safe, map_part_type, native_seed, register, write_source_face_attribute
from infinigen2.workpieces.parametric_capture import active_capture


PARTS = {0: "seat", 1: "leg_base", 2: "back", 3: "slat", 4: "arm", 5: "back"}
_METHOD_CODES = {
    "make_seat": 0,
    "make_legs": 1,
    "make_backs": 2,
    "make_leg_decors": 3,
    "make_arms": 4,
    "make_back_decors": 5,
}


def build(rng):
    import infinigen.assets.objects.seating.chairs.chair as chair_mod
    from infinigen.core.util.math import FixedSeed

    seed = native_seed(rng)
    state = {"part_id": 0, "centerlines": {}, "part_type_legend": dict(PARTS)}
    raw_centerlines = {}
    original_methods = {name: getattr(chair_mod.ChairFactory, name) for name in _METHOD_CODES}
    original_join = chair_mod.join_objects
    original_curves = {
        name: getattr(chair_mod, name) for name in ("align_bezier", "bezier_curve")
    }

    def order_points(points):
        points = np.asarray(points, dtype=float)
        if len(points) < 2:
            return points
        start = int(np.argmax(points @ (points.max(0) - points.min(0))))
        order = [start]
        used = {start}
        for _ in range(len(points) - 1):
            distance = np.linalg.norm(points - points[order[-1]], axis=1)
            distance[list(used)] = 1e18
            index = int(np.argmin(distance))
            order.append(index)
            used.add(index)
        return points[order]

    def wrap_curve(original):
        def capture(*args, **kwargs):
            obj = original(*args, **kwargs)
            try:
                points = np.asarray([vertex.co[:] for vertex in obj.data.vertices], dtype=float)
                if len(points) >= 3:
                    raw_centerlines[obj.name] = order_points(points)
            except (AttributeError, ReferenceError):
                pass
            return obj
        return capture

    def wrap_method(name, code, original):
        def tagged(self, *args, **kwargs):
            state['factory'] = self
            result = original(self, *args, **kwargs)
            objects = result if isinstance(result, (list, tuple)) else [result]
            for obj in objects:
                if obj is not None:
                    obj["_spraybot_part_type"] = code
                    obj["_spraybot_constructor"] = name
            return result
        return tagged

    def tagged_join(objects, *args, **kwargs):
        if isinstance(objects, (list, tuple)):
            final_assembly = bool(objects) and objects[0] is not None and (
                objects[0].get('_spraybot_constructor') == 'make_seat')
            capture = active_capture() if final_assembly else None
            factory = state.get('factory')
            factory_parameters = None
            if capture is not None:
                keys = ('width', 'size', 'thickness', 'bevel_width', 'seat_back',
                        'seat_mid', 'seat_mid_x', 'seat_mid_z', 'seat_front',
                        'is_seat_round', 'is_seat_subsurf', 'leg_thickness',
                        'limb_profile', 'leg_height', 'back_height',
                        'is_leg_round', 'leg_type', 'back_thickness',
                        'back_type', 'back_profile', 'back_vertical_cuts',
                        'back_partial_scale', 'has_arm', 'arm_thickness',
                        'arm_height', 'arm_y', 'arm_z', 'arm_mid', 'arm_profile')
                factory_parameters = json_safe({key: getattr(factory, key) for key in keys})
            for obj in objects:
                code = int(obj.get("_spraybot_part_type", 0))
                write_source_face_attribute(obj.data, "part_type", code)
                write_source_face_attribute(obj.data, "part_id", state["part_id"])
                if obj.name in raw_centerlines:
                    state["centerlines"][state["part_id"]] = raw_centerlines[obj.name]
                if capture is not None and len(obj.data.polygons):
                    capture.native_chair(obj, PARTS[code],
                                         str(obj.get('_spraybot_constructor', 'unknown')),
                                         factory_parameters)
                state["part_id"] += 1
        return original_join(objects, *args, **kwargs)

    try:
        for name, code in _METHOD_CODES.items():
            setattr(chair_mod.ChairFactory, name, wrap_method(name, code, original_methods[name]))
        chair_mod.join_objects = tagged_join
        for name, function in original_curves.items():
            setattr(chair_mod, name, wrap_curve(function))
        # create_asset also samples (e.g. back decoration). Constructor-only
        # seeding leaves those choices dependent on prior process RNG state.
        with FixedSeed(seed):
            factory = chair_mod.ChairFactory(seed)
            obj = factory.create_asset()
    finally:
        chair_mod.join_objects = original_join
        for name, method in original_methods.items():
            setattr(chair_mod.ChairFactory, name, method)
        for name, function in original_curves.items():
            setattr(chair_mod, name, function)

    mesh = map_part_type(pf.MeshObject(obj), PARTS)
    mesh_data = mesh.item().data
    part_ids = mesh_data.attributes.get("part_id")
    centerlines, bounds = state["centerlines"], {}
    bm = bmesh.new()
    try:
        bm.from_mesh(mesh_data)
        for face in bm.faces:
            part_id = int(part_ids.data[face.index].value) if part_ids else 0
            lo, hi = bounds.setdefault(part_id, [np.full(3, np.inf), np.full(3, -np.inf)])
            for vertex in face.verts:
                lo[:] = np.minimum(lo, vertex.co[:])
                hi[:] = np.maximum(hi, vertex.co[:])
    finally:
        bm.free()

    def rotate_z(points, degrees):
        theta = np.radians(degrees)
        c, s = np.cos(theta), np.sin(theta)
        return np.asarray(points, dtype=float) @ np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]]).T

    best_degrees, best_hits = 0, -1
    for degrees in (0, 90, 180, 270):
        hits = 0
        for part_id, points in centerlines.items():
            if part_id not in bounds:
                continue
            lo, hi = bounds[part_id]
            mean = rotate_z(points, degrees).mean(0)
            if np.all(mean >= lo - 0.03) and np.all(mean <= hi + 0.03):
                hits += 1
        if hits > best_hits:
            best_degrees, best_hits = degrees, hits
    aligned_centerlines = {
        int(part_id): rotate_z(points, best_degrees)
        for part_id, points in centerlines.items()
    }
    priors = {
        "factory_seed": seed,
        "centerline_representation": "ordered_sampled_polyline_not_bezier_control_points",
        "back_type": str(factory.back_type),
        "back_profile": factory.back_profile.tolist() if hasattr(factory.back_profile, "tolist") else factory.back_profile,
        "back_vertical_cuts": int(factory.back_vertical_cuts),
        "back_height": float(factory.back_height),
        "has_arm": bool(factory.has_arm),
        "leg_type": str(factory.leg_type),
        "part_type_legend": dict(PARTS),
        "centerlines": aligned_centerlines,
        "centerline_rotation_degrees": best_degrees,
        "centerline_rotation_matches": best_hits,
    }
    return BuiltWorkpiece(mesh, json_safe(priors))


register(category("infinigen_chair", "N03", "ChairFactory 原生随机结构", build, PARTS.values()))

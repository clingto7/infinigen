"""Validate a parametric candidate against the delivered OBJ and face mask.

This process imports no Blender or generator code. It reads only one exported
episode and checks the surface descriptions in OBJ coordinates (converted from
millimeters to meters), triangle order, outward normals, and target coverage.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np


SCHEMAS = {
    "candidate": {"spraybot.parametric-candidate.v1", "spraybot.parametric-candidate.v2", "spraybot.parametric-candidate.v3", "spraybot.parametric-candidate.v4", "spraybot.parametric-candidate.v5", "spraybot.parametric-candidate.v6"},
    "ready": {"spraybot.parametric.v1", "spraybot.parametric.v2", "spraybot.parametric.v3", "spraybot.parametric.v4", "spraybot.parametric.v5", "spraybot.parametric.v6"},
}
POSITION_TOLERANCE_M = 2.1e-6
PLANE_NORMAL_TOLERANCE_DEG = 0.1


def _vector(value, name: str) -> np.ndarray:
    result = np.asarray(value, dtype=float)
    if result.shape != (3,) or not np.isfinite(result).all():
        raise ValueError(f"{name} must be a finite three-vector")
    return result


def _unit(value, name: str) -> np.ndarray:
    result = _vector(value, name)
    if abs(np.linalg.norm(result) - 1.0) > 1e-5:
        raise ValueError(f"{name} must have unit length")
    return result


def _positive(value, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be positive and finite")
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise ValueError(f"{name} must be positive and finite")
    return result


def _obj(path: Path) -> tuple[np.ndarray, np.ndarray]:
    vertices, triangles = [], []
    with path.open(encoding="ascii") as file:
        for line in file:
            fields = line.split()
            if not fields:
                continue
            if fields[0] == "v":
                if len(fields) != 4:
                    raise ValueError("OBJ vertex must have three coordinates")
                vertices.append([float(x) / 1000 for x in fields[1:]])
            elif fields[0] == "f":
                if len(fields) != 4 or any("/" in x for x in fields[1:]):
                    raise ValueError("OBJ faces must be plain triangles")
                triangles.append([int(x) - 1 for x in fields[1:]])
    v = np.asarray(vertices, dtype=float)
    f = np.asarray(triangles, dtype=int)
    if v.ndim != 2 or v.shape[1] != 3 or f.ndim != 2 or f.shape[1] != 3:
        raise ValueError("OBJ has invalid vertices or triangles")
    if not np.isfinite(v).all() or np.any(f < 0) or np.any(f >= len(v)):
        raise ValueError("OBJ has invalid coordinates or face indices")
    return v, f


def _ids(value, face_count: int, name: str) -> list[int]:
    if not isinstance(value, list) or any(type(x) is not int or not 0 <= x < face_count for x in value):
        raise ValueError(f"{name} must contain zero-based OBJ triangle IDs")
    if len(set(value)) != len(value):
        raise ValueError(f"{name} contains duplicate triangle IDs")
    return value


def _surface(surface: dict, triangles: np.ndarray) -> tuple[list[int], float]:
    kind = surface["type"]
    if kind in {"sweep_quad", "sweep_cap", "sweep_triangle"}:
        from spraybot_parametric_sweep_validate import validate_sweep
        return validate_sweep(surface, triangles)
    if kind not in {"plane_rectangle", "plane_triangle", "cylinder_side", "disk"}:
        raise ValueError(f"unsupported surface type: {kind}")
    expected_domain = {"u": [0, 1], "v": [0, 1]}
    if kind == "plane_triangle":
        expected_domain["constraint"] = "u+v<=1"
    if surface["domain"] != expected_domain:
        raise ValueError("unsupported surface domain")
    if surface["periodic_v"] is not (kind not in {"plane_rectangle", "plane_triangle"}):
        raise ValueError("surface periodicity disagrees with its type")
    g = surface["geometry"]
    mesh_mapping = surface["mesh_mapping"]
    count = len(triangles)
    ids = _ids(mesh_mapping["construction_triangle_ids"], count, "construction mapping")
    if not ids:
        raise ValueError("surface has no construction triangles")
    supports = _ids(mesh_mapping["support_triangle_ids"], count, "support mapping")
    if not set(ids) <= set(supports):
        raise ValueError("construction mapping is absent from its support mapping")
    bound = _positive(surface["approximation"]["mesh_distance_bound_m"], "mesh distance bound")
    xyz = triangles[ids]
    cross = np.cross(xyz[:, 1] - xyz[:, 0], xyz[:, 2] - xyz[:, 0])
    areas = np.linalg.norm(cross, axis=1)
    if np.any(areas < 1e-12):
        raise ValueError("mapped OBJ triangle is degenerate")
    mesh_normal = cross / areas[:, None]
    if kind in {"plane_rectangle", "plane_triangle"}:
        if surface["approximation"]["kind"] != "source_roundoff":
            raise ValueError("plane approximation kind is incorrect")
        origin = _vector(g["origin"], "plane origin")
        u = _vector(g["u"], "plane u")
        v = _vector(g["v"], "plane v")
        normal = _unit(g["normal"], "plane normal")
        uu, vv = float(u @ u), float(v @ v)
        if min(uu, vv) <= 0 or abs(u @ v) > 1e-5 * math.sqrt(uu * vv):
            raise ValueError("plane edges must be nonzero and orthogonal")
        if max(abs(normal @ u), abs(normal @ v)) > 1e-5:
            raise ValueError("plane normal is not perpendicular to its edges")
        offset = xyz - origin
        distance = np.abs(offset @ normal)
        u_coord, v_coord = offset @ u / uu, offset @ v / vv
        if np.any(u_coord < -1e-4) or np.any(u_coord > 1 + 1e-4) or np.any(v_coord < -1e-4) or np.any(v_coord > 1 + 1e-4):
            raise ValueError("OBJ vertices fall outside the plane domain")
        if kind == "plane_triangle" and np.any(u_coord + v_coord > 1 + 1e-4):
            raise ValueError("OBJ vertices fall outside the triangle domain")
        expected = normal
        allowed_angle = PLANE_NORMAL_TOLERANCE_DEG
    else:
        if surface["approximation"]["kind"] != "inscribed_polygon_mesh":
            raise ValueError("rod approximation kind is incorrect")
        origin = _vector(g["origin"], "rod origin")
        axis = _unit(g["axis"], "rod axis")
        radial_u = _unit(g["radial_u"], "rod radial_u")
        radial_v = _unit(g["radial_v"], "rod radial_v")
        if max(abs(axis @ radial_u), abs(axis @ radial_v), abs(radial_u @ radial_v)) > 1e-5:
            raise ValueError("rod frame is not orthogonal")
        if np.linalg.norm(np.cross(radial_u, radial_v) - axis) > 1e-5:
            raise ValueError("rod frame is not right handed")
        radius = _positive(g["radius_m"], "rod radius")
        length = _positive(g["length_m"], "rod length")
        segments = g["angular_segments"]
        if type(segments) is not int or segments < 3:
            raise ValueError("rod angular_segments must be at least three")
        polygon_bound = radius * (1 - math.cos(math.pi / segments))
        if bound + POSITION_TOLERANCE_M < polygon_bound:
            raise ValueError("claimed polygon distance bound is too small")
        axial = (xyz - origin) @ axis
        radial = xyz - origin - axial[:, :, None] * axis
        radii = np.linalg.norm(radial, axis=2)
        if kind == "cylinder_side":
            if np.any(axial < -POSITION_TOLERANCE_M) or np.any(axial > length + POSITION_TOLERANCE_M):
                raise ValueError("cylinder vertices fall outside the axial domain")
            distance = np.abs(radii - radius)
            centers = xyz.mean(axis=1)
            center_axial = (centers - origin) @ axis
            direction = centers - origin - center_axial[:, None] * axis
            expected = direction / np.linalg.norm(direction, axis=1)[:, None]
            claimed_angle = _positive(surface["approximation"]["mesh_normal_bound_deg"], "mesh normal bound")
            theoretical_angle = 180 / segments
            if claimed_angle > theoretical_angle + 0.2 or claimed_angle >= 90:
                raise ValueError("claimed cylinder normal bound is too loose")
            allowed_angle = claimed_angle + 0.1
        else:
            fraction, sign = g["axial_fraction"], g["normal_sign"]
            if type(fraction) is not int or fraction not in (0, 1) or type(sign) is not int or sign not in (-1, 1):
                raise ValueError("disk position or outward sign is invalid")
            if np.any(radii > radius + POSITION_TOLERANCE_M):
                raise ValueError("disk vertices fall outside its radius")
            distance = np.abs(axial - fraction * length)
            expected = sign * axis
            allowed_angle = PLANE_NORMAL_TOLERANCE_DEG
    # These three source primitives place mesh vertices on their analytic
    # surfaces. The larger polygon bound concerns face interiors, not a
    # license to fit the wrong radius or plane through displaced vertices.
    if np.max(distance) > POSITION_TOLERANCE_M:
        raise ValueError(f"OBJ vertices disagree with {surface['id']}")
    cosine = np.sum(mesh_normal * expected, axis=1)
    angle = float(np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0))).max())
    if angle > allowed_angle:
        raise ValueError(f"OBJ normal disagrees with {surface['id']}: {angle:.3f} degrees")
    return ids, angle


def validate(episode: Path) -> dict:
    metadata = json.loads((episode / "metadata.json").read_text())
    status = metadata.get("parametric_description_status")
    if status not in SCHEMAS:
        raise ValueError("episode has no supported parametric status")
    name = metadata.get("parametric_candidate_file") if status == "candidate" else metadata.get("parametric_file")
    if not name or Path(name).name != name:
        raise ValueError("metadata lacks a safe parametric artifact reference")
    artifact = json.loads((episode / name).read_text())
    if artifact.get("schema") not in SCHEMAS[status] or artifact.get("unit") != "m" or artifact.get("frame") != "exported_obj_axes_origin":
        raise ValueError("unsupported parametric schema, unit or frame")
    if artifact.get("obj_unit") != "mm" or artifact.get("obj_mm_per_parametric_m") != 1000:
        raise ValueError("incorrect OBJ unit conversion")
    if artifact.get("mesh_triangle_order") != "OBJ faces and face_attributes.npz rows, zero-based":
        raise ValueError("incorrect triangle order declaration")
    if artifact.get("source", {}).get("category_id") != metadata.get("category_id") or artifact.get("source", {}).get("seed") != metadata.get("seed"):
        raise ValueError("parametric source disagrees with episode metadata")
    vertices, faces = _obj(episode / metadata["model_file"])
    triangles = vertices[faces]
    with np.load(episode / metadata["face_attributes_file"], allow_pickle=False) as attrs:
        targets = np.asarray(attrs["spray_target"], dtype=bool)
    if len(targets) != len(faces) or metadata["faces"] != len(faces):
        raise ValueError("OBJ and face attribute triangle counts disagree")
    csg = None
    native = None
    source_record = None
    if artifact['schema'].endswith('.v4'):
        from spraybot_parametric_csg_validate import validate_construction
        csg = validate_construction(artifact)
        source_name = metadata.get('parametric_source_file')
        if not source_name or Path(source_name).name != source_name:
            raise ValueError('CSG description lacks a safe source record')
        source_record = json.loads((episode / source_name).read_text())
        if (source_record.get('status') != 'construction_only'
            or source_record.get('operations') != artifact['construction']['operations']
            or source_record.get('invalid_lineage_triangle_ids')):
            raise ValueError('CSG description disagrees with recorded construction')
    if artifact['schema'].endswith('.v5'):
        from spraybot_parametric_native_validate import prepare
        source_name = metadata.get('parametric_native_source_file')
        if not source_name or Path(source_name).name != source_name:
            raise ValueError('native description lacks a safe source record')
        native = prepare(json.loads((episode / source_name).read_text()), vertices, faces)
    used, part_ids, surface_ids = set(), set(), set()
    worst_angle = 0.0
    surface_count = 0
    for part in artifact["parts"]:
        if part["id"] in part_ids or not part["surfaces"]:
            raise ValueError("duplicate or empty part instance")
        part_ids.add(part["id"])
        chair_recipe = part.get('source_recipe') if artifact['schema'].endswith('.v6') else None
        if artifact['schema'].endswith('.v6') and chair_recipe is None:
            raise ValueError('native chair part lacks its constructor recipe')
        if chair_recipe is not None:
            expected_semantic = {'make_seat': 'seat', 'make_legs': 'leg_base',
                                 'make_backs': 'back', 'make_leg_decors': 'slat',
                                 'make_arms': 'arm', 'make_back_decors': 'back'}
            if part['semantic'] != expected_semantic.get(chair_recipe.get('constructor')):
                raise ValueError('native chair part semantic disagrees with constructor')
        if native is not None:
            source_id = int(part['id'].removeprefix('native_')) if part['id'].startswith('native_') else -1
            record = native[3].get(source_id)
            if record is None or part['semantic'] != record[0]['parameters']['part']:
                raise ValueError('native part disagrees with source constructor')
        for surface in part["surfaces"]:
            if surface["type"] in {"sweep_quad", "sweep_cap", "sweep_triangle"} and not artifact["schema"].endswith((".v3", ".v5", ".v6")):
                raise ValueError("sweep patches require schema v3")
            if artifact["schema"].endswith(".v1") and surface["type"] == "plane_triangle":
                raise ValueError("plane_triangle requires parametric schema v2")
            if surface["id"] in surface_ids:
                raise ValueError("duplicate surface ID")
            surface_ids.add(surface["id"])
            if surface['type'] == 'csg_trimmed_face':
                if csg is None:
                    raise ValueError('CSG trimmed faces require schema v4')
                from spraybot_parametric_csg_validate import validate_surface
                ids, angle = validate_surface(surface, vertices, faces, csg)
                source_id = surface['provenance']['source_operation_id']
                face_id = surface['provenance']['source_face_id']
                if any(source_record['final_triangle_source_ids'][index] != source_id
                       or source_record['final_triangle_source_face_ids'][index] != face_id
                       for index in ids):
                    raise ValueError('CSG trim mapping disagrees with source-face lineage')
            else:
                if csg is not None:
                    raise ValueError('schema v4 requires CSG trimmed faces')
                checked_surface = surface
                if chair_recipe is not None:
                    from spraybot_parametric_native_chair import expand_surface
                    checked_surface = expand_surface(surface, chair_recipe)
                ids, angle = _surface(checked_surface, triangles)
                if native is not None:
                    from spraybot_parametric_native_validate import validate_surface as validate_native_surface
                    if len(ids) != 1:
                        raise ValueError('native grid patch must map one OBJ triangle')
                    validate_native_surface(surface, ids[0], vertices, faces, native)
            if used.intersection(ids):
                raise ValueError("construction triangles overlap")
            used.update(ids)
            worst_angle = max(worst_angle, angle)
            surface_count += 1
    target_ids = set(np.flatnonzero(targets).tolist())
    if not target_ids <= used:
        raise ValueError(f"{len(target_ids - used)} spray_target triangles are undescribed")
    coverage = artifact["description_coverage"]
    if coverage["spray_target_triangle_count"] != len(target_ids) or coverage["represented_target_triangle_count"] != len(target_ids):
        raise ValueError("reported spray target coverage is false")
    unrepresented = _ids(coverage["unrepresented_non_target_triangle_ids"], len(faces), "unrepresented non-target IDs")
    if unrepresented != sorted(set(range(len(faces))) - used):
        raise ValueError("unrepresented non-target list is incorrect")
    return {"episode": str(episode), "parts": len(part_ids), "surfaces": surface_count,
            "target_triangles": len(target_ids), "max_normal_angle_deg": worst_angle}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("episodes", type=Path, nargs="+")
    args = parser.parse_args()
    for path in args.episodes:
        print(json.dumps(validate(path), allow_nan=False))

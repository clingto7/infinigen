"""Adapters for the source-native Spraybot factories."""

import numpy as np
import procfunc as pf
from infinigen2.workpieces.common import BuiltWorkpiece, Category, register

from infinigen2.util import spray


def native_seed(rng: pf.RNG) -> int:
    """Draw the seed consumed by the source Infinigen AssetFactory APIs."""
    return int(pf.random.randint(rng, 0, 2**31 - 1))


def map_part_type(mesh: pf.MeshObject, mapping: dict[int, str]) -> pf.MeshObject:
    """Map a source factory's FACE ``part_type`` into the shared spray vocabulary."""
    source = pf.ops.attr.read_attribute(mesh, "part_type", domain="FACE").astype(
        np.int32
    )
    unknown = set(np.unique(source).tolist()) - set(mapping)
    if unknown:
        raise ValueError(f"Unmapped native part_type codes: {sorted(unknown)}")
    shared = np.empty_like(source, dtype=np.int32)
    for code, name in mapping.items():
        shared[source == code] = spray.part_id(name)
    pf.ops.attr.write_attribute(
        mesh, shared, "spray_part", domain="FACE", overwrite=True
    )
    spray.write_spray_target(mesh)
    return mesh


def write_source_face_attribute(data, name: str, value: int) -> None:
    """Write an integer FACE attribute before source mesh parts are joined."""
    attr = data.attributes.get(name)
    if attr is None or attr.domain != "FACE" or attr.data_type != "INT":
        if attr is not None:
            data.attributes.remove(attr)
        attr = data.attributes.new(name, "INT", "FACE")
    attr.data.foreach_set("value", [int(value)] * len(data.polygons))


def json_safe(value):
    """Convert NumPy values in source factory priors to JSON-native values."""
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def category(category_id, code, title, build, parts):
    return Category(
        category_id=category_id,
        code=code,
        family="Spraybot 原生接口",
        criterion=title,
        build=build,
        allowed_parts=frozenset(parts),
    )


__all__ = ["BuiltWorkpiece", "category", "json_safe", "map_part_type", "native_seed", "register", "write_source_face_attribute"]

"""Shared Spraybot face-tag vocabulary and helpers.

``spray_part`` codes come from one table so nested generators (a desk built
from a cabinet built from drawers) can tag their own parts without the
caller remapping them.
"""

import bmesh
import math

import numpy as np
import procfunc as pf
from mathutils import Vector
from mathutils.bvhtree import BVHTree

SPRAY_PART_IDS: dict[str, int] = {
    "seat": 0,
    "back": 1,
    "slat": 2,
    "arm": 3,
    "leg_base": 4,
    "top": 5,
    "carcass": 6,
    "shelf": 7,
    "back_panel": 8,
    "door_frame": 9,
    "door_panel": 10,
    "drawer_front": 11,
    "headboard": 12,
    "frame": 13,
    "handle": 14,
    "outer_frame": 15,
    "mullion": 16,
    "sash": 17,
    "louver": 18,
    "casing": 19,
    "glass": 20,
    "drawer_box": 21,
    # D-tier shells. These are spray bodies, not furniture members.
    "shell": 22,
    "rib": 23,
    "flange": 24,
    "boss": 25,
}
SPRAY_PART_NAMES = {code: name for name, code in SPRAY_PART_IDS.items()}

# Hardware, glass and closed-drawer interiors are not coated with the body.
NON_TARGET_PARTS = frozenset({"handle", "glass", "drawer_box"})

# Codes written by storage_composite_rand / storage_with_legs_rand when spray_tags
# is set. Existing Spraybot categories keep these integers; new workpieces remap.
REMOTE_STORAGE_PARTS = {
    0: "carcass",
    1: "back_panel",
    2: "shelf",
    3: "shelf",
    4: "door_frame",
    5: "door_panel",
    6: "handle",
    7: "drawer_front",
    8: "leg_base",
}


def part_id(name: str) -> int:
    return SPRAY_PART_IDS[name]


def has_spray_part(obj: pf.MeshObject) -> bool:
    return "spray_part" in obj.item().data.attributes


def write_spray_part(obj: pf.MeshObject, name: str) -> None:
    count = len(obj.item().data.polygons)
    pf.ops.attr.write_attribute(
        obj,
        np.full(count, part_id(name), dtype=np.int32),
        "spray_part",
        domain="FACE",
        overwrite=True,
    )


def remap_spray_part(obj: pf.MeshObject, mapping: dict[int, str]) -> None:
    """Rewrite generator-local part codes into the shared vocabulary."""
    local = pf.ops.attr.read_attribute(obj, "spray_part", domain="FACE")
    unknown = set(np.unique(local).tolist()) - set(mapping)
    if unknown:
        raise ValueError(f"Unmapped local spray_part codes: {sorted(unknown)}")
    shared = np.empty_like(local, dtype=np.int32)
    for code, name in mapping.items():
        shared[local == code] = part_id(name)
    pf.ops.attr.write_attribute(obj, shared, "spray_part", domain="FACE", overwrite=True)


def write_spray_target(obj: pf.MeshObject) -> None:
    parts = pf.ops.attr.read_attribute(obj, "spray_part", domain="FACE")
    excluded = [part_id(name) for name in NON_TARGET_PARTS]
    pf.ops.attr.write_attribute(
        obj, ~np.isin(parts, excluded), "spray_target", domain="FACE", overwrite=True
    )


def write_spray_visibility(obj: pf.MeshObject, samples: int = 16) -> None:
    """Write per-face ``spray_visibility`` in [0, 1].

    The value is the fraction of ``samples`` deterministic hemisphere
    directions around the outward normal from which a ray escapes the solid
    unobstructed. Rays run in mesh coordinates (D-tier meshes store world
    coordinates in vertices), so occlusion by other parts of the same
    workpiece is included. Outer faces score ~1, closed-cavity walls ~0, and
    outward-opening pockets score in between. ``spray_target`` stays
    all-inclusive; this attribute lets consumers discount unreachable faces
    without changing the target-face contract.
    """
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.item().data)
        bm.faces.ensure_lookup_table()
        bvh = BVHTree.FromBMesh(bm)
        golden = math.pi * (3.0 - math.sqrt(5.0))
        local_dirs = []
        for i in range(samples):
            z = (i + 0.5) / samples
            r = math.sqrt(max(0.0, 1.0 - z * z))
            phi = i * golden
            local_dirs.append(Vector((r * math.cos(phi), r * math.sin(phi), z)))
        eps = 2e-4
        values = np.empty(len(bm.faces), dtype=np.float32)
        up = Vector((0.0, 0.0, 1.0))
        for face in bm.faces:
            normal = face.normal
            if normal.length < 1e-9:
                values[face.index] = 0.0
                continue
            normal.normalize()
            spin = up.rotation_difference(normal)
            origin = face.calc_center_median() + normal * eps
            escaped = sum(
                1 for local in local_dirs if bvh.ray_cast(origin, spin @ local)[0] is None
            )
            values[face.index] = escaped / samples
        pf.ops.attr.write_attribute(
            obj, values, "spray_visibility", domain="FACE", overwrite=True
        )
    finally:
        bm.free()


def present_part_legend(obj: pf.MeshObject) -> dict[int, str]:
    parts = pf.ops.attr.read_attribute(obj, "spray_part", domain="FACE")
    return {int(code): SPRAY_PART_NAMES[int(code)] for code in np.unique(parts)}

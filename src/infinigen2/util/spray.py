"""Shared Spraybot face-tag vocabulary and helpers.

``spray_part`` codes come from one table so nested generators (a desk built
from a cabinet built from drawers) can tag their own parts without the
caller remapping them.
"""

import numpy as np
import procfunc as pf

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


def present_part_legend(obj: pf.MeshObject) -> dict[int, str]:
    parts = pf.ops.attr.read_attribute(obj, "spray_part", domain="FACE")
    return {int(code): SPRAY_PART_NAMES[int(code)] for code in np.unique(parts)}

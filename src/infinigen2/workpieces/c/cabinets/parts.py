"""Shared pieces for C-tier cabinets.

Boards and rods are the aimed members from C-tier seating. Cabinets use a
min-corner frame: X is depth, Y is width, Z is height, and the front is +X.
"""

import numpy as np
import procfunc as pf

from infinigen2.objects import door, handles
from infinigen2.util import mesh, spray
from infinigen2.workpieces.assemble import hard_material, join_tagged
from infinigen2.workpieces.c.seating.parts import (
    Category,
    board,
    chain,
    register,
    rod,
    strut,
)
from infinigen2.workpieces.common import Category as _Category

__all__ = [
    "Category",
    "board",
    "chain",
    "door_leaf",
    "hard_material",
    "join_tagged",
    "open_carcass",
    "register",
    "rod",
    "strut",
    "triangle_slab",
]

# Re-export the registry type used by every category module.
assert Category is _Category


def placed(
    size: tuple[float, float, float],
    origin: tuple[float, float, float],
    material: pf.Material,
    part: str,
) -> pf.MeshObject:
    """Axis-aligned box whose min corner is ``origin``."""
    center = tuple(origin[i] + size[i] * 0.5 for i in range(3))
    return board(size, center, material, part)


def open_carcass(
    material: pf.Material,
    depth: float,
    width: float,
    height: float,
    thickness: float = 0.016,
    z0: float = 0.0,
    include_top: bool = True,
) -> list[pf.MeshObject]:
    """Box with an open +X face. ``z0`` is the bottom of the box."""
    t = thickness
    parts = [
        placed((depth, width, t), (0.0, 0.0, z0), material, "carcass"),
        placed((t, width, height), (0.0, 0.0, z0), material, "back_panel"),
        placed((depth, t, height), (0.0, 0.0, z0), material, "carcass"),
        placed((depth, t, height), (0.0, width - t, z0), material, "carcass"),
    ]
    if include_top:
        parts.append(placed((depth, width, t), (0.0, 0.0, z0 + height - t), material, "carcass"))
    return parts


def door_leaf(
    rng: pf.RNG,
    thickness: float,
    width: float,
    height: float,
    origin: tuple[float, float, float],
) -> pf.MeshObject:
    rng_door, rng_handle = rng.spawn(2)
    leaf = door.door_body_rand(
        rng_door,
        dimensions=pf.Vector((thickness, width, height)),
        spray_tags=True,
    ).mesh
    spray.remap_spray_part(leaf, {0: "door_frame", 1: "door_panel"})
    pf.ops.object.set_transform(leaf, location=origin)
    pull = handles.handle_bar_pull_rand(rng_handle, grip_length=0.12).mesh
    spray.write_spray_part(pull, "handle")
    pf.ops.object.set_transform(
        pull,
        location=(origin[0] + thickness, origin[1] + width * 0.5, height * 0.55),
    )
    return join_tagged([leaf, pull])


def triangle_slab(
    size_x: float,
    size_y: float,
    thick: float,
    z: float,
    material: pf.Material,
    part: str,
) -> pf.MeshObject:
    """Right-triangle shelf in the +X/+Y quadrant, min corner at the origin."""
    z1 = z + thick
    corners = np.array(
        [
            [0, 0, z], [size_x, 0, z], [0, size_y, z],
            [0, 0, z1], [0, size_y, z1], [size_x, 0, z1],
            [0, 0, z], [size_x, 0, z], [size_x, 0, z1], [0, 0, z1],
            [0, 0, z], [0, 0, z1], [0, size_y, z1], [0, size_y, z],
            [size_x, 0, z], [0, size_y, z], [0, size_y, z1], [size_x, 0, z1],
        ],
        dtype=np.float64,
    )
    sizes = np.array([3, 3, 4, 4, 4])
    uvs = np.stack((corners[:, 0], corners[:, 1]), axis=1).astype(np.float32)
    obj = mesh.mesh_from_corners(corners, sizes, uvs)
    pf.ops.object.set_material(
        obj, surface=material.surface, displacement=material.displacement
    )
    spray.write_spray_part(obj, part)
    return obj

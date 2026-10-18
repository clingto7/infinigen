"""Shared members for C-tier tables.

Straight boards and rods are the same aimed segments used by C-tier seating.
Each table category stays in its own module. Tops are centered on X and Y,
with length along Y.
"""

import procfunc as pf

from infinigen2.workpieces.assemble import tagged_slab
from infinigen2.workpieces.c.seating.parts import (
    Category,
    board,
    chain,
    join_tagged,
    register,
    rod,
    strut,
)

__all__ = [
    "Category",
    "board",
    "chain",
    "join_tagged",
    "register",
    "rod",
    "strut",
    "tabletop",
]


def tabletop(
    size: tuple[float, float, float],
    material: pf.Material,
    z: float,
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> pf.MeshObject:
    """Slab whose bottom sits at ``z`` until ``rotation`` is applied around that origin."""
    top = tagged_slab(size, material, "top")
    pf.ops.object.set_transform(top, location=(0.0, 0.0, z), rotation_euler=rotation)
    return top

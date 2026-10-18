"""C-tier furniture outside the seating, table, cabinet, and bed families.

Boards and rods are the shared aimed members. Screens reuse a door leaf.
"""

import procfunc as pf

from infinigen2.workpieces.assemble import hard_material, join_tagged
from infinigen2.workpieces.c.seating.parts import Category, board, register, rod, strut

__all__ = [
    "Category",
    "board",
    "hard_material",
    "join_tagged",
    "placed",
    "register",
    "rod",
    "strut",
]


def placed(
    size: tuple[float, float, float],
    origin: tuple[float, float, float],
    material: pf.Material,
    part: str,
) -> pf.MeshObject:
    center = tuple(origin[i] + size[i] * 0.5 for i in range(3))
    return board(size, center, material, part)

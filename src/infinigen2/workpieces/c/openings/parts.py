"""C-tier door and window trim.

Wall coordinates: X is the projection off the wall, Y is width, Z is height.
The opening's min corner is the origin. Boards are the shared aimed members.
"""

import procfunc as pf

from infinigen2.workpieces.assemble import hard_material, join_tagged
from infinigen2.workpieces.c.seating.parts import Category, board, register

__all__ = [
    "Category",
    "hard_material",
    "join_tagged",
    "placed",
    "register",
]


def placed(
    size: tuple[float, float, float],
    origin: tuple[float, float, float],
    material: pf.Material,
    part: str,
) -> pf.MeshObject:
    center = tuple(origin[i] + size[i] * 0.5 for i in range(3))
    return board(size, center, material, part)

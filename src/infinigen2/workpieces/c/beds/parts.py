"""Shared members for C-tier beds.

Beds are centered on X and Y. X is the length, Y is the width, and the head
is at -X. Boards and rods are the same aimed members used by the other
C-tier packages.
"""

from infinigen2.workpieces.c.seating.parts import (
    Category,
    board,
    join_tagged,
    register,
    strut,
)
from infinigen2.workpieces.assemble import hard_material

__all__ = [
    "Category",
    "board",
    "hard_material",
    "join_tagged",
    "register",
    "strut",
]

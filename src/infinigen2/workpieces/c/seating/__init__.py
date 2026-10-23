"""C-tier seating categories.

One module per category. New rods, boards, and frames stay in this package
instead of the A/B workpiece modules.
"""

from infinigen2.workpieces.c.seating import (
    armchair,
    cantilever_chair,
    folding_chair,
    high_chair,
    ladder_back_chair,
    lounge_chair,
    park_bench,
    rocking_chair,
    windsor_chair,
)

__all__ = [
    "armchair",
    "cantilever_chair",
    "folding_chair",
    "high_chair",
    "ladder_back_chair",
    "lounge_chair",
    "park_bench",
    "rocking_chair",
    "windsor_chair",
]

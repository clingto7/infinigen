"""Workpiece entries, grouped by tier and then by family.

Import this package, not ``infinigen2.objects.spraybot``. Category ids stay
the same. ``common.py`` holds the registry and ``assemble.py`` holds shared
placement. Each category is one module under ``a/``, ``b/``, or ``c/``.

    from infinigen2.workpieces import generate
    generate("storage_bench", rng)
"""

from infinigen2.workpieces import a, b, c
from infinigen2.workpieces.common import REGISTRY, WorkpieceResult, generate

# Registration happens at import, so the id list is complete only after the
# category modules above have been imported.
CATEGORY_IDS = tuple(REGISTRY)

__all__ = [
    "CATEGORY_IDS",
    "WorkpieceResult",
    "a",
    "b",
    "c",
    "generate",
]

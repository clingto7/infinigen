"""S23 踏步凳。

结构判据：两到三级踏板，侧板支撑。
级数是构型。低的踏板在前，高的踏板靠后，左右侧板托住每一级。
"""

import procfunc as pf

from infinigen2.workpieces.assemble import hard_material
from infinigen2.workpieces.c.seating.parts import (
    Category,
    board,
    join_tagged,
    register,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    steps = pf.control.choice(rng_size, [(2, 1.0), (3, 1.0)])
    rise = pf.random.uniform(rng_size, 0.18, 0.24)
    tread = pf.random.uniform(rng_size, 0.22, 0.28)
    width = pf.random.uniform(rng_size, 0.36, 0.46)
    material = hard_material(rng_mat)
    plate = 0.018
    parts = []
    for index in range(steps):
        height = (index + 1) * rise
        x0 = index * tread
        for side in (-1.0, 1.0):
            y = side * (width * 0.5 - plate)
            parts.append(board(
                (tread, plate, height),
                (x0 + tread * 0.5, y, height * 0.5),
                material, "leg_base",
            ))
        parts.append(board(
            (tread + 0.02, width, 0.022),
            (x0 + tread * 0.5, 0.0, height + 0.011),
            material, "seat",
        ))
    return join_tagged(parts)


register(Category(
    category_id="step_stool",
    code="S23",
    family="坐具",
    criterion="两到三级踏板，侧板支撑",
    build=build,
    allowed_parts=frozenset({"seat", "leg_base"}),
))

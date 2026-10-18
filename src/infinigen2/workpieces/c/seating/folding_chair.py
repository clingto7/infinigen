"""S18 折叠椅。

结构判据：X 形交叉腿，座面与腿铰接。
每侧两根木条在中部交叉。一根延到靠背高度，座面横条搭在交叉点上方。
"""

import procfunc as pf

from infinigen2.workpieces.assemble import hard_material
from infinigen2.workpieces.c.seating.parts import (
    Category,
    board,
    join_tagged,
    register,
    strut,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    width = pf.random.uniform(rng_size, 0.42, 0.50)
    seat_z = pf.random.uniform(rng_size, 0.44, 0.48)
    back_z = pf.random.uniform(rng_size, 0.86, 0.98)
    material = hard_material(rng_mat)
    y_side = width * 0.46
    section = (0.028, 0.018)
    parts = []
    for side in (-1.0, 1.0):
        y = side * y_side
        parts.append(strut((0.26, y, 0.02), (-0.06, y, seat_z), section, material, "leg_base"))
        parts.append(strut((-0.06, y, seat_z), (-0.14, y, back_z), section, material, "leg_base"))
        parts.append(strut((-0.22, y, 0.02), (0.18, y, seat_z), section, material, "leg_base"))
    seat_ys = width * 0.5 + 0.02
    for x in (-0.02, 0.06, 0.14):
        parts.append(board((0.055, seat_ys * 2.0, 0.016), (x, 0.0, seat_z + 0.012), material, "seat"))
    for z in (seat_z + (back_z - seat_z) * 0.45, seat_z + (back_z - seat_z) * 0.82):
        x = -0.06 + (z - seat_z) / (back_z - seat_z) * (-0.08)
        parts.append(board((0.018, seat_ys * 2.0, 0.028), (x, 0.0, z), material, "back"))
    return join_tagged(parts)


register(Category(
    category_id="folding_chair",
    code="S18",
    family="坐具",
    criterion="X 形交叉腿，座面与腿铰接",
    build=build,
    allowed_parts=frozenset({"seat", "back", "leg_base"}),
))

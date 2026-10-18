"""T22 课桌。

结构判据：桌面下有开口书斗，常为金属框加木面。
书斗挂在桌面下，朝前方开口，有底、后板和两侧。四根圆管腿收到桌面，前腿间有脚踏。
"""

import procfunc as pf

from infinigen2.workpieces.assemble import hard_material
from infinigen2.workpieces.c.tables.parts import (
    Category,
    board,
    join_tagged,
    register,
    rod,
    tabletop,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    depth = pf.random.uniform(rng_size, 0.48, 0.58)
    width = pf.random.uniform(rng_size, 0.55, 0.70)
    height = pf.random.uniform(rng_size, 0.70, 0.76)
    top_t = pf.random.uniform(rng_size, 0.024, 0.034)
    box_h = pf.random.uniform(rng_size, 0.16, 0.22)
    radius = 0.012
    material = hard_material(rng_mat)
    under = height - top_t
    parts = [tabletop((depth, width, top_t), material, under)]
    x_leg = depth * 0.5 - 0.045
    y_leg = width * 0.5 - 0.045
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            parts.append(rod(
                (sx * x_leg, sy * y_leg, radius),
                (sx * x_leg, sy * y_leg, under),
                radius, material, "leg_base",
            ))
    parts.append(rod(
        (x_leg, -y_leg, 0.18), (x_leg, y_leg, 0.18),
        0.010, material, "leg_base",
    ))
    x_back = -x_leg + 0.035
    x_front = x_leg - 0.06
    box_w = y_leg * 2.0 - 0.04
    z_bot = under - box_h
    span = x_front - x_back
    mid_x = (x_back + x_front) * 0.5
    parts.append(board((span, box_w, 0.012), (mid_x, 0.0, z_bot + 0.006), material, "carcass"))
    parts.append(board((0.012, box_w, box_h), (x_back, 0.0, z_bot + box_h * 0.5), material, "carcass"))
    for side in (-1.0, 1.0):
        parts.append(board(
            (span, 0.012, box_h),
            (mid_x, side * box_w * 0.5, z_bot + box_h * 0.5),
            material, "carcass",
        ))
    return join_tagged(parts)


register(Category(
    category_id="school_desk",
    code="T22",
    family="桌台",
    criterion="桌面下有开口书斗，常为金属框加木面",
    build=build,
    allowed_parts=frozenset({"top", "leg_base", "carcass"}),
))

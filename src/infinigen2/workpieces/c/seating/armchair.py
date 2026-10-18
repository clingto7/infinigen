"""S14 扶手椅。

结构判据：餐椅两侧有扶手和扶手立柱。
座靠复用餐椅，条板或实心靠背是构型。扶手在座面之上，前后各有一根立柱落到座面。
"""

import procfunc as pf

from infinigen2.workpieces.assemble import hard_material
from infinigen2.workpieces.c.seating.parts import (
    Category,
    board,
    dining_with_back,
    four_legs,
    join_tagged,
    register,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_back, rng_seat, rng_base, rng_mat = rng.spawn(6)
    depth = pf.random.uniform(rng_size, 0.48, 0.56)
    width = pf.random.uniform(rng_size, 0.50, 0.58)
    elevation = pf.random.uniform(rng_size, 0.44, 0.50)
    thickness = pf.random.uniform(rng_size, 0.040, 0.055)
    back_height = pf.random.uniform(rng_size, 0.36, 0.48)
    arm_rise = pf.random.uniform(rng_size, 0.18, 0.24)
    material = hard_material(rng_mat)
    body = dining_with_back(
        rng_style, rng_back, rng_seat,
        depth, width, elevation, thickness, back_height, material,
    )
    legs = four_legs(rng_base, depth, width, elevation - thickness * 0.5, material)
    arm_z = elevation + arm_rise
    parts = [legs, body]
    rail_x0 = -depth * 0.42
    rail_x1 = depth * 0.28
    for side in (-1.0, 1.0):
        y = side * (width * 0.5 - 0.045)
        parts.append(board(
            (rail_x1 - rail_x0, 0.038, 0.032),
            ((rail_x0 + rail_x1) * 0.5, y, arm_z),
            material, "arm",
        ))
        for x in (rail_x0 + 0.02, rail_x1 - 0.02):
            parts.append(board(
                (0.032, 0.032, arm_rise),
                (x, y, elevation + arm_rise * 0.5),
                material, "arm",
            ))
    return join_tagged(parts)


register(Category(
    category_id="armchair",
    code="S14",
    family="坐具",
    criterion="餐椅两侧有扶手和扶手立柱",
    build=build,
    allowed_parts=frozenset({"seat", "back", "arm", "leg_base"}),
))

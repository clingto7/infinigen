"""T19 工作台。

结构判据：厚台面、腿间有横撑和下层搁板。
四条方腿收到台面下。台面下有一圈裙板，搁板嵌在腿间，腿穿过搁板。
"""

import procfunc as pf

from infinigen2.workpieces.assemble import hard_material
from infinigen2.workpieces.c.tables.parts import (
    Category,
    board,
    join_tagged,
    register,
    tabletop,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    depth = pf.random.uniform(rng_size, 0.62, 0.78)
    length = pf.random.uniform(rng_size, 1.30, 1.80)
    height = pf.random.uniform(rng_size, 0.86, 0.94)
    top_t = pf.random.uniform(rng_size, 0.048, 0.068)
    shelf_z = pf.random.uniform(rng_size, 0.18, 0.28)
    material = hard_material(rng_mat)
    under = height - top_t
    leg = 0.055
    x_leg = depth * 0.5 - 0.07
    y_leg = length * 0.5 - 0.07
    parts = [tabletop((depth, length, top_t), material, under)]
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            parts.append(board(
                (leg, leg, under - 0.02),
                (sx * x_leg, sy * y_leg, (under + 0.02) * 0.5),
                material, "leg_base",
            ))
    apron_h = 0.09
    apron_z = under - apron_h * 0.5
    parts.append(board((0.022, length - 0.10, apron_h), (depth * 0.5 - 0.05, 0.0, apron_z), material, "frame"))
    parts.append(board((0.022, length - 0.10, apron_h), (-depth * 0.5 + 0.05, 0.0, apron_z), material, "frame"))
    parts.append(board((depth - 0.10, 0.022, apron_h), (0.0, length * 0.5 - 0.05, apron_z), material, "frame"))
    parts.append(board((depth - 0.10, 0.022, apron_h), (0.0, -length * 0.5 + 0.05, apron_z), material, "frame"))
    parts.append(board(
        (x_leg * 2.0 + leg, y_leg * 2.0 + leg, 0.020),
        (0.0, 0.0, shelf_z),
        material, "shelf",
    ))
    return join_tagged(parts)


register(Category(
    category_id="workbench",
    code="T19",
    family="桌台",
    criterion="厚台面、腿间有横撑和下层搁板",
    build=build,
    allowed_parts=frozenset({"top", "frame", "shelf", "leg_base"}),
))

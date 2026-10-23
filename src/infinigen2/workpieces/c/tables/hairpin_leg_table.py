"""T20 发夹腿桌。

结构判据：每条腿是一根弯成 V 形的金属细杆。
四角各一根。V 的尖在桌面下，两脚在地面分开。
"""

import procfunc as pf

from infinigen2.workpieces.assemble import hard_material
from infinigen2.workpieces.c.tables.parts import (
    Category,
    chain,
    join_tagged,
    register,
    tabletop,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    depth = pf.random.uniform(rng_size, 0.55, 0.75)
    length = pf.random.uniform(rng_size, 0.90, 1.25)
    height = pf.random.uniform(rng_size, 0.72, 0.76)
    top_t = pf.random.uniform(rng_size, 0.028, 0.040)
    gap = pf.random.uniform(rng_size, 0.11, 0.16)
    radius = pf.random.uniform(rng_size, 0.006, 0.008)
    material = hard_material(rng_mat)
    under = height - top_t
    parts = [tabletop((depth, length, top_t), material, under)]
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            x = sx * (depth * 0.5 - 0.06)
            y = sy * (length * 0.5 - 0.08)
            # The apex must enter the top slab; stopping it short leaves the
            # whole table as a floating top over four detached V legs.
            apex = (x, y, under + 0.004)
            foot_a = (x + sx * 0.04, y - gap * 0.5, radius)
            foot_b = (x + sx * 0.04, y + gap * 0.5, radius)
            parts.extend(chain(
                [foot_a, apex, foot_b], material, "leg_base",
                radius=radius, overlap=radius,
            ))
    return join_tagged(parts)


register(Category(
    category_id="hairpin_leg_table",
    code="T20",
    family="桌台",
    criterion="每条腿是一根弯成 V 形的金属细杆",
    build=build,
    allowed_parts=frozenset({"top", "leg_base"}),
))

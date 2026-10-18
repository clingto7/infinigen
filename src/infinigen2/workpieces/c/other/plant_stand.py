"""O03 花架。

结构判据：多层阶梯式小台面。
三级踏步由低到高向后收。每一级是一块小台面，侧板从地面托到该级。
"""

import procfunc as pf

from infinigen2.workpieces.c.other.parts import (
    Category,
    hard_material,
    join_tagged,
    placed,
    register,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    tread = pf.random.uniform(rng_size, 0.22, 0.28)
    rise = pf.random.uniform(rng_size, 0.26, 0.34)
    width = pf.random.uniform(rng_size, 0.34, 0.46)
    material = hard_material(rng_mat)
    plate = 0.016
    parts = []
    for index in range(3):
        height = (index + 1) * rise
        x0 = index * tread
        for side in (0.0, width - plate):
            parts.append(placed((tread, plate, height), (x0, side, 0.0), material, "leg_base"))
        parts.append(placed(
            (tread + 0.02, width + 0.02, 0.018),
            (x0 - 0.01, -0.01, height),
            material, "top",
        ))
    return join_tagged(parts)


register(Category(
    category_id="plant_stand",
    code="O03",
    family="其他家具",
    criterion="多层阶梯式小台面",
    build=build,
    allowed_parts=frozenset({"top", "leg_base"}),
))

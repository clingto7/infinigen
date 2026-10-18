"""C24 带盖储物箱。

结构判据：无腿或矮脚箱体，顶部是盖板。
有没有矮脚是构型。盖板比箱口略大，盖在箱体上。
"""

import procfunc as pf

from infinigen2.workpieces.c.cabinets.parts import (
    Category,
    hard_material,
    join_tagged,
    open_carcass,
    placed,
    register,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_mat = rng.spawn(3)
    depth = pf.random.uniform(rng_size, 0.40, 0.55)
    width = pf.random.uniform(rng_size, 0.70, 1.10)
    height = pf.random.uniform(rng_size, 0.38, 0.52)
    feet = pf.control.choice(rng_style, [(False, 1.0), (True, 1.0)])
    material = hard_material(rng_mat)
    lift = 0.08 if feet else 0.0
    parts = []
    if feet:
        for x in (0.04, depth - 0.08):
            for y in (0.04, width - 0.08):
                parts.append(placed((0.045, 0.045, lift), (x, y, 0.0), material, "leg_base"))
    parts.extend(open_carcass(material, depth, width, height, z0=lift, include_top=False))
    parts.append(placed((0.016, width, height), (depth - 0.016, 0.0, lift), material, "carcass"))
    parts.append(placed(
        (depth + 0.03, width + 0.03, 0.018),
        (-0.015, -0.015, lift + height),
        material, "top",
    ))
    return join_tagged(parts)


register(Category(
    category_id="storage_chest",
    code="C24",
    family="柜架",
    criterion="无腿或矮脚箱体，顶部是盖板",
    build=build,
    allowed_parts=frozenset({"carcass", "back_panel", "leg_base", "top"}),
))

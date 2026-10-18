"""C23 金属货架。

结构判据：四根角钢立柱加多层薄板，无侧板和背板。
立柱是两条薄板拼成的 L 形。层数是构型，层板只搭在四角上。
"""

import procfunc as pf

from infinigen2.workpieces.c.cabinets.parts import (
    Category,
    hard_material,
    join_tagged,
    placed,
    register,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    depth = pf.random.uniform(rng_size, 0.40, 0.55)
    width = pf.random.uniform(rng_size, 0.90, 1.25)
    height = pf.random.uniform(rng_size, 1.60, 1.90)
    count = int(pf.control.choice(rng_size, [(4, 1.0), (5, 1.0)]))
    material = hard_material(rng_mat)
    flange = 0.028
    thick = 0.004
    parts = []
    for x, y, x_dir, y_dir in (
        (0.0, 0.0, 1.0, 1.0),
        (depth, 0.0, -1.0, 1.0),
        (0.0, width, 1.0, -1.0),
        (depth, width, -1.0, -1.0),
    ):
        parts.append(placed(
            (flange, thick, height),
            (x + min(x_dir, 0.0) * flange, y - thick * 0.5, 0.0),
            material, "leg_base",
        ))
        parts.append(placed(
            (thick, flange, height),
            (x - thick * 0.5, y + min(y_dir, 0.0) * flange, 0.0),
            material, "leg_base",
        ))
    for index in range(count):
        z = height * (index + 1) / (count + 1)
        parts.append(placed(
            (depth + 0.02, width + 0.02, 0.012),
            (-0.01, -0.01, z),
            material, "shelf",
        ))
    return join_tagged(parts)


register(Category(
    category_id="metal_shelving",
    code="C23",
    family="柜架",
    criterion="四根角钢立柱加多层薄板，无侧板和背板",
    build=build,
    allowed_parts=frozenset({"leg_base", "shelf"}),
))

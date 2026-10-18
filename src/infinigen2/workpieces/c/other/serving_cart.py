"""O04 餐车。

结构判据：金属或木框，两到三层托盘，带脚轮。
层数是构型。四角立柱落到脚轮上，托盘有一圈矮边，一端有推手。
"""

import procfunc as pf

from infinigen2.workpieces.c.other.parts import (
    Category,
    hard_material,
    join_tagged,
    placed,
    register,
    rod,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    depth = pf.random.uniform(rng_size, 0.40, 0.50)
    width = pf.random.uniform(rng_size, 0.70, 0.90)
    height = pf.random.uniform(rng_size, 0.75, 0.90)
    tiers = int(pf.control.choice(rng_size, [(2, 1.0), (3, 1.0)]))
    material = hard_material(rng_mat)
    radius = 0.040
    post = 0.022
    parts = []
    corners = (
        (post, post),
        (depth - post * 2.0, post),
        (post, width - post * 2.0),
        (depth - post * 2.0, width - post * 2.0),
    )
    for x, y in corners:
        parts.append(rod(
            (x + post * 0.5, y, radius),
            (x + post * 0.5, y + 0.018, radius),
            radius, material, "leg_base", resolution=12,
        ))
        parts.append(placed(
            (post, post, height - radius * 2.0),
            (x, y, radius * 2.0),
            material, "frame",
        ))
    for index in range(tiers):
        z = radius * 2.0 + 0.04 + (height - radius * 2.0 - 0.08) * index / (tiers - 1)
        parts.append(placed((depth, width, 0.014), (0.0, 0.0, z), material, "top"))
        parts.append(placed((0.012, width, 0.028), (0.0, 0.0, z + 0.014), material, "frame"))
        parts.append(placed((0.012, width, 0.028), (depth - 0.012, 0.0, z + 0.014), material, "frame"))
        parts.append(placed((depth, 0.012, 0.028), (0.0, 0.0, z + 0.014), material, "frame"))
        parts.append(placed((depth, 0.012, 0.028), (0.0, width - 0.012, z + 0.014), material, "frame"))
    grip_z = height + 0.16
    parts.append(rod((0.04, width, height - 0.02), (0.04, width, grip_z), 0.012, material, "frame"))
    parts.append(rod((depth - 0.04, width, height - 0.02), (depth - 0.04, width, grip_z), 0.012, material, "frame"))
    parts.append(rod((0.04, width, grip_z), (depth - 0.04, width, grip_z), 0.012, material, "frame"))
    return join_tagged(parts)


register(Category(
    category_id="serving_cart",
    code="O04",
    family="其他家具",
    criterion="金属或木框，两到三层托盘，带脚轮",
    build=build,
    allowed_parts=frozenset({"top", "frame", "leg_base"}),
))

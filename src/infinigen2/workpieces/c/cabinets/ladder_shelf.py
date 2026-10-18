"""C19 梯形架。

结构判据：两根斜立柱靠墙，搁板由下往上变窄。
立柱下端向前、上端靠后。搁板数是构型，每一层都搭在当时的立柱间距上。
"""

import procfunc as pf

from infinigen2.workpieces.c.cabinets.parts import (
    Category,
    board,
    hard_material,
    join_tagged,
    register,
    strut,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    height = pf.random.uniform(rng_size, 1.50, 1.80)
    bottom_w = pf.random.uniform(rng_size, 0.58, 0.76)
    top_w = pf.random.uniform(rng_size, 0.30, 0.40)
    count = int(pf.control.choice(rng_size, [(4, 1.0), (5, 1.0)]))
    material = hard_material(rng_mat)
    x_foot = 0.34
    x_head = 0.08
    y_mid = bottom_w * 0.5
    parts = []
    for side in (-1.0, 1.0):
        parts.append(strut(
            (x_foot, y_mid + side * bottom_w * 0.5, 0.02),
            (x_head, y_mid + side * top_w * 0.5, height),
            (0.028, 0.022), material, "frame",
        ))
    for index in range(count):
        t = (index + 0.5) / count
        width = bottom_w + (top_w - bottom_w) * t
        depth = 0.30 + (0.16 - 0.30) * t
        x = x_foot + (x_head - x_foot) * t
        z = height * t
        parts.append(board(
            (depth, width + 0.02, 0.016),
            (x + depth * 0.35, y_mid, z),
            material, "shelf",
        ))
    return join_tagged(parts)


register(Category(
    category_id="ladder_shelf",
    code="C19",
    family="柜架",
    criterion="两根斜立柱靠墙，搁板由下往上变窄",
    build=build,
    allowed_parts=frozenset({"frame", "shelf"}),
))

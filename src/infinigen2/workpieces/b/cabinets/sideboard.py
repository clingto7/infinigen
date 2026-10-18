"""C11 餐边柜。

结构判据：中等高度，抽屉列与门柜列左右并排。
左右哪一侧是抽屉是构型。两列同深同高，顶面平齐。
"""

import procfunc as pf

from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_order, rng_drawers, rng_doors = rng.spawn(4)
    depth = pf.random.uniform(rng_size, 0.42, 0.50)
    height = pf.random.uniform(rng_size, 0.78, 0.95)
    drawer_w = pf.random.uniform(rng_size, 0.42, 0.58)
    door_w = pf.random.uniform(rng_size, 0.55, 0.85)
    drawers_first = pf.control.choice(rng_order, [(True, 1.0), (False, 1.0)])
    drawers = assemble.fronted_bay(
        rng_drawers, (depth, drawer_w, height), "drawer", n_spaces_y=1
    )
    doors = assemble.fronted_bay(
        rng_doors, (depth, door_w, height), "door", n_spaces_y=1
    )
    if drawers_first:
        return assemble.place_row([(drawers, drawer_w), (doors, door_w)])
    return assemble.place_row([(doors, door_w), (drawers, drawer_w)])


register(
    Category(
        category_id="sideboard",
        code="C11",
        family="柜架",
        criterion="中等高度，抽屉列与门柜列左右并排",
        build=build,
        allowed_parts=frozenset(
            {
                "carcass",
                "shelf",
                "back_panel",
                "drawer_front",
                "drawer_box",
                "handle",
                "door_frame",
                "door_panel",
            }
        ),
    )
)

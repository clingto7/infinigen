"""C10 电视柜。

结构判据：低而宽，开敞格与门或抽屉横向并排。
三格：两侧开敞，中间是门或抽屉。中间正面类型是构型。
"""

import procfunc as pf

from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_front, rng_left, rng_mid, rng_right = rng.spawn(5)
    depth = pf.random.uniform(rng_size, 0.38, 0.48)
    height = pf.random.uniform(rng_size, 0.38, 0.50)
    side = pf.random.uniform(rng_size, 0.34, 0.48)
    center = pf.random.uniform(rng_size, 0.55, 0.80)
    front = pf.control.choice(rng_front, [("door", 1.0), ("drawer", 1.0)])
    left = assemble.open_bay(rng_left, (depth, side, height), 1, 1)
    middle = assemble.fronted_bay(
        rng_mid, (depth, center, height), front, n_spaces_y=1, n_spaces_z=1
    )
    right = assemble.open_bay(rng_right, (depth, side, height), 1, 1)
    return assemble.place_row([(left, side), (middle, center), (right, side)])


register(
    Category(
        category_id="tv_stand",
        code="C10",
        family="柜架",
        criterion="低而宽，开敞格与门或抽屉横向并排",
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

"""C15 吊柜。

结构判据：无底座，浅柜体，底面外露。
没有腿或踢脚。深度停在 0.28–0.36 m，底面就是柜体底板。
单扇或双开门是构型。
"""

import procfunc as pf

from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_body = rng.spawn(2)
    depth = pf.random.uniform(rng_size, 0.28, 0.36)
    width = pf.random.uniform(rng_size, 0.60, 1.00)
    height = pf.random.uniform(rng_size, 0.48, 0.72)
    cabinet = assemble.fronted_bay(
        rng_body, (depth, width, height), "door", n_spaces_y=1, n_spaces_z=1
    )
    return assemble.join_tagged([cabinet])


register(
    Category(
        category_id="wall_cabinet",
        code="C15",
        family="柜架",
        criterion="无底座，浅柜体，底面外露",
        build=build,
        allowed_parts=frozenset(
            {
                "carcass",
                "shelf",
                "back_panel",
                "door_frame",
                "door_panel",
                "handle",
            }
        ),
    )
)

"""C09 床头柜。

结构判据：小柜体，上部抽屉、下部开敞格。
下部不是门柜，避免和 C03 抽屉门柜混成一类。抽屉层数是构型。
"""

import procfunc as pf

from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_lower, rng_upper = rng.spawn(3)
    depth = pf.random.uniform(rng_size, 0.35, 0.45)
    width = pf.random.uniform(rng_size, 0.40, 0.55)
    lower_h = pf.random.uniform(rng_size, 0.28, 0.38)
    upper_h = pf.random.uniform(rng_size, 0.18, 0.28)
    n_drawers = 1 if upper_h < 0.24 else 2
    lower = assemble.open_bay(rng_lower, (depth, width, lower_h), n_spaces_y=1, n_spaces_z=1)
    upper = assemble.fronted_bay(
        rng_upper,
        (depth, width, upper_h),
        front_style="drawer",
        n_spaces_y=1,
        n_spaces_z=n_drawers,
    )
    return assemble.place_stack(lower, upper, lower_h)


register(
    Category(
        category_id="nightstand",
        code="C09",
        family="柜架",
        criterion="小柜体，上部抽屉、下部开敞格",
        build=build,
        allowed_parts=frozenset(
            {
                "carcass",
                "shelf",
                "back_panel",
                "drawer_front",
                "drawer_box",
                "handle",
            }
        ),
    )
)

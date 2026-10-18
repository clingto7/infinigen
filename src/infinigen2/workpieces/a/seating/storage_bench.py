"""S09 储物长凳。

结构判据：无靠背，座面下是开敞格或抽屉柜体。
门正面不在判据里，这里锁掉；开敞和抽屉保留为构型。
座面就是柜体的顶板，部件名用 carcass，不再单列 seat。
"""

import procfunc as pf

from infinigen2.objects import storage
from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_front, rng_bench = rng.spawn(2)
    front = pf.control.choice(rng_front, [("open", 1.0), ("drawer", 1.0)])
    mesh = storage.storage_bench_rand(
        rng_bench, front_style=front, spray_tags=True
    ).mesh
    return assemble.adopt_storage(mesh)


register(
    Category(
        category_id="storage_bench",
        code="S09",
        family="坐具",
        criterion="无靠背，座面下是开敞格或抽屉柜体",
        build=build,
        allowed_parts=frozenset(
            {
                "carcass",
                "shelf",
                "back_panel",
                "drawer_front",
                "drawer_box",
                "handle",
                "leg_base",
            }
        ),
    )
)

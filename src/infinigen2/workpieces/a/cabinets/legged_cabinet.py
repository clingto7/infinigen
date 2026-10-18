"""C07 带腿柜。

结构判据：柜体由 0.15–0.3 m 高的腿托起，腿高由 storage_with_legs_rand 抽样。
正面锁成抽屉。开敞正面会和待定的 C06 带底座格架重叠，门正面另计。
"""

import procfunc as pf

from infinigen2.objects import storage
from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register


def build(rng: pf.RNG) -> pf.MeshObject:
    mesh = storage.storage_with_legs_rand(
        rng, front_style="drawer", spray_tags=True
    ).mesh
    return assemble.adopt_storage(mesh)


register(
    Category(
        category_id="legged_cabinet",
        code="C07",
        family="柜架",
        criterion="柜体由 0.15–0.3 m 高的腿托起",
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

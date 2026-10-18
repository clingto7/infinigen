"""S08 靠背长椅。

结构判据：多人宽的座面加整排靠背，底座跨度大。
条板或实心靠背、直腿或框腿都是构型，入口不锁定。
"""

import procfunc as pf

from infinigen2.objects import chair
from infinigen2.workpieces.common import Category, register


def build(rng: pf.RNG) -> pf.MeshObject:
    return chair.chair_bench_rand(rng, spray_tags=True).mesh


register(
    Category(
        category_id="backed_bench",
        code="S08",
        family="坐具",
        criterion="多人宽的座面加整排靠背，底座跨度大",
        build=build,
        allowed_parts=frozenset({"seat", "back", "leg_base"}),
    )
)

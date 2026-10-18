"""D05 拱顶门。

结构判据：门扇顶边是圆弧，门内为窗格棂条。
玻璃不生成。坐标仍是墙坐标：X 为厚度，Y 为宽度，Z 为高度。
"""

import procfunc as pf

from infinigen2.objects import door, window
from infinigen2.util import spray
from infinigen2.workpieces.common import Category, register

_DOOR_PARTS = {0: "outer_frame", 2: "handle"}


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_profile, rng_door = rng.spawn(3)
    dimensions = pf.Vector(
        (
            pf.random.uniform(rng_size, 0.035, 0.045),
            pf.random.uniform(rng_size, 0.7, 0.95),
            pf.random.uniform(rng_size, 1.9, 2.1),
        )
    )
    profile = window.top_rounded_profile_rand(rng_profile, dimensions)
    mesh = door.door_glass_from_profile_rand(
        rng_door, profile, include_glass_pane=False, spray_tags=True
    ).mesh
    spray.remap_spray_part(mesh, _DOOR_PARTS)
    return mesh


register(
    Category(
        category_id="arched_door",
        code="D05",
        family="门窗",
        criterion="门扇顶边是圆弧，门内为窗格棂条",
        build=build,
        allowed_parts=frozenset({"outer_frame", "mullion", "sash", "handle"}),
    )
)

"""D06 百叶门。

结构判据：门芯由多根斜向百叶条组成。
门体锁成窗格，百叶打开，玻璃不生成。把手是构型。
坐标仍是墙坐标：X 为厚度，Y 为宽度，Z 为高度。
"""

import procfunc as pf

from infinigen2.objects import door
from infinigen2.util import spray
from infinigen2.workpieces.common import Category, register

# Window leaves tag the frame, grid and louvers together as 0, and the handle as 2.
_DOOR_PARTS = {0: "outer_frame", 2: "handle"}


def build(rng: pf.RNG) -> pf.MeshObject:
    mesh = door.door_composite_rand(
        rng,
        body_style="glass_grid",
        shutter=True,
        include_glass_pane=False,
        spray_tags=True,
    ).mesh
    spray.remap_spray_part(mesh, _DOOR_PARTS)
    return mesh


register(
    Category(
        category_id="louvered_door",
        code="D06",
        family="门窗",
        criterion="门芯由多根斜向百叶条组成",
        build=build,
        allowed_parts=frozenset({"outer_frame", "mullion", "louver", "handle"}),
    )
)

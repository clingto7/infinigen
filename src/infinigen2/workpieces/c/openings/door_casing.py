"""D07 门套。

结构判据：贴墙的 U 形三边框，截面为线脚。
左右立边加顶边，底部留空。每边是贴墙平板加一条靠洞口的凸线。
墙坐标：X 为出墙厚度，Y 为宽度，Z 为高度。
"""

import procfunc as pf

from infinigen2.workpieces.c.openings.parts import (
    Category,
    hard_material,
    join_tagged,
    placed,
    register,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    opening_w = pf.random.uniform(rng_size, 0.80, 1.00)
    opening_h = pf.random.uniform(rng_size, 2.00, 2.20)
    leg = pf.random.uniform(rng_size, 0.07, 0.10)
    plate = pf.random.uniform(rng_size, 0.016, 0.022)
    material = hard_material(rng_mat)
    outer_w = opening_w + 2.0 * leg
    bead = leg * 0.42
    bead_t = 0.012
    parts = [
        placed((plate, leg, opening_h), (0.0, 0.0, 0.0), material, "casing"),
        placed((plate, leg, opening_h), (0.0, leg + opening_w, 0.0), material, "casing"),
        placed((plate, outer_w, leg), (0.0, 0.0, opening_h), material, "casing"),
        placed((bead_t, bead, opening_h), (plate, leg - bead, 0.0), material, "casing"),
        placed((bead_t, bead, opening_h), (plate, leg + opening_w, 0.0), material, "casing"),
        placed((bead_t, outer_w - 2.0 * (leg - bead), bead), (plate, leg - bead, opening_h), material, "casing"),
    ]
    return join_tagged(parts)


register(Category(
    category_id="door_casing",
    code="D07",
    family="门窗",
    criterion="贴墙的 U 形三边框，截面为线脚",
    build=build,
    allowed_parts=frozenset({"casing"}),
))

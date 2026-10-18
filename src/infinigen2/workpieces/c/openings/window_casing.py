"""W05 窗套。

结构判据：四边框加下方外伸的窗台板。
四边是贴墙线脚，窗台板比框更伸出墙面，并长过两侧。
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
    opening_w = pf.random.uniform(rng_size, 0.80, 1.40)
    opening_h = pf.random.uniform(rng_size, 0.90, 1.40)
    leg = pf.random.uniform(rng_size, 0.055, 0.075)
    plate = pf.random.uniform(rng_size, 0.016, 0.022)
    sill_d = pf.random.uniform(rng_size, 0.14, 0.20)
    material = hard_material(rng_mat)
    outer_w = opening_w + 2.0 * leg
    sill_t = 0.032
    ear = 0.03
    parts = [
        placed((plate, leg, opening_h), (0.0, 0.0, sill_t), material, "casing"),
        placed((plate, leg, opening_h), (0.0, leg + opening_w, sill_t), material, "casing"),
        placed((plate, outer_w, leg), (0.0, 0.0, sill_t + opening_h), material, "casing"),
        placed((plate, outer_w, leg), (0.0, 0.0, sill_t), material, "casing"),
        placed(
            (sill_d, outer_w + 2.0 * ear, sill_t),
            (0.0, -ear, 0.0),
            material, "frame",
        ),
    ]
    return join_tagged(parts)


register(Category(
    category_id="window_casing",
    code="W05",
    family="门窗",
    criterion="四边框加下方外伸的窗台板",
    build=build,
    allowed_parts=frozenset({"casing", "frame"}),
))

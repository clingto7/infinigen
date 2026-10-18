"""B06 四柱床。

结构判据：四角立柱高出床头，顶部可有框。
床体是硬质床框：床头、床尾、侧梁和床板。四根立柱升到床头以上，顶部连成框。
"""

import procfunc as pf

from infinigen2.workpieces.c.beds.parts import (
    Category,
    board,
    hard_material,
    join_tagged,
    register,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    length = pf.random.uniform(rng_size, 1.95, 2.10)
    width = pf.random.uniform(rng_size, 1.05, 1.55)
    deck = pf.random.uniform(rng_size, 0.34, 0.42)
    head_h = pf.random.uniform(rng_size, 1.00, 1.20)
    post_h = pf.random.uniform(rng_size, 1.90, 2.10)
    material = hard_material(rng_mat)
    hx = length * 0.5
    hy = width * 0.5
    post = 0.070
    parts = [
        board((length - 0.08, width - 0.10, 0.04), (0.0, 0.0, deck), material, "frame"),
        board((0.04, width - 0.08, head_h - deck), (-hx + 0.04, 0.0, (deck + head_h) * 0.5), material, "headboard"),
        board((0.03, width - 0.08, 0.28), (hx - 0.04, 0.0, deck + 0.10), material, "frame"),
        board((length, 0.04, 0.08), (0.0, hy - 0.03, deck - 0.02), material, "frame"),
        board((length, 0.04, 0.08), (0.0, -hy + 0.03, deck - 0.02), material, "frame"),
    ]
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            parts.append(board(
                (post, post, post_h),
                (sx * (hx + 0.02), sy * (hy + 0.02), post_h * 0.5),
                material, "leg_base",
            ))
    z_top = post_h - 0.03
    parts.append(board((length + 0.08, 0.035, 0.035), (0.0, hy + 0.02, z_top), material, "frame"))
    parts.append(board((length + 0.08, 0.035, 0.035), (0.0, -hy - 0.02, z_top), material, "frame"))
    parts.append(board((0.035, width + 0.08, 0.035), (hx + 0.02, 0.0, z_top), material, "frame"))
    parts.append(board((0.035, width + 0.08, 0.035), (-hx - 0.02, 0.0, z_top), material, "frame"))
    return join_tagged(parts)


register(Category(
    category_id="four_poster_bed",
    code="B06",
    family="床具",
    criterion="四角立柱高出床头，顶部可有框",
    build=build,
    allowed_parts=frozenset({"headboard", "frame", "leg_base"}),
))

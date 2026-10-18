"""B05 上下铺。

结构判据：两层床面由四根立柱连接，带爬梯和护栏。
爬梯在床尾，上层靠外的长边有护栏。
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
    length = pf.random.uniform(rng_size, 1.90, 2.05)
    width = pf.random.uniform(rng_size, 0.90, 1.05)
    lower = pf.random.uniform(rng_size, 0.42, 0.50)
    upper = pf.random.uniform(rng_size, 1.15, 1.28)
    post_h = upper + 0.55
    material = hard_material(rng_mat)
    hx = length * 0.5
    hy = width * 0.5
    post = 0.055
    parts = []
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            parts.append(board(
                (post, post, post_h),
                (sx * (hx + 0.01), sy * (hy + 0.01), post_h * 0.5),
                material, "leg_base",
            ))
    for z in (lower, upper):
        parts.append(board((length, width, 0.04), (0.0, 0.0, z), material, "frame"))
        parts.append(board((length, 0.04, 0.08), (0.0, hy - 0.02, z - 0.05), material, "frame"))
        parts.append(board((length, 0.04, 0.08), (0.0, -hy + 0.02, z - 0.05), material, "frame"))
    for rise in (0.16, 0.34):
        parts.append(board(
            (length - 0.35, 0.02, 0.04),
            (-0.08, hy + 0.03, upper + rise),
            material, "slat",
        ))
    ladder_x = hx + 0.10
    for y in (-0.16, 0.16):
        parts.append(board((0.028, 0.028, upper), (ladder_x, y, upper * 0.5), material, "frame"))
    for index in range(4):
        z = 0.22 + index * (upper - 0.28) / 3.0
        parts.append(board((0.022, 0.32, 0.022), (ladder_x, 0.0, z), material, "slat"))
    return join_tagged(parts)


register(Category(
    category_id="bunk_bed",
    code="B05",
    family="床具",
    criterion="两层床面由四根立柱连接，带爬梯和护栏",
    build=build,
    allowed_parts=frozenset({"frame", "leg_base", "slat"}),
))

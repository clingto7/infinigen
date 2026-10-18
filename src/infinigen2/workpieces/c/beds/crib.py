"""B04 婴儿床。

结构判据：四周都是竖栏，床面离地较高。
四根角柱之间是竖栏，床板高于普通床。
"""

import procfunc as pf

from infinigen2.workpieces.c.beds.parts import (
    Category,
    board,
    hard_material,
    join_tagged,
    register,
)


def _slats(material, x0, x1, y0, y1, z0, z1, along_x: bool) -> list:
    span = (x1 - x0) if along_x else (y1 - y0)
    count = max(3, int(span / 0.09))
    height = z1 - z0
    parts = []
    for index in range(count):
        t = (index + 0.5) / count
        if along_x:
            center = (x0 + (x1 - x0) * t, (y0 + y1) * 0.5, (z0 + z1) * 0.5)
            size = (0.014, 0.014, height)
        else:
            center = ((x0 + x1) * 0.5, y0 + (y1 - y0) * t, (z0 + z1) * 0.5)
            size = (0.014, 0.014, height)
        parts.append(board(size, center, material, "slat"))
    return parts


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    length = pf.random.uniform(rng_size, 1.20, 1.40)
    width = pf.random.uniform(rng_size, 0.65, 0.75)
    deck = pf.random.uniform(rng_size, 0.42, 0.55)
    top = pf.random.uniform(rng_size, 0.95, 1.08)
    material = hard_material(rng_mat)
    hx = length * 0.5
    hy = width * 0.5
    post = 0.035
    parts = [
        board((length - 0.06, width - 0.06, 0.018), (0.0, 0.0, deck), material, "frame"),
    ]
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            parts.append(board(
                (post, post, top),
                (sx * hx, sy * hy, top * 0.5),
                material, "leg_base",
            ))
    for y, z in ((hy, top - 0.02), (-hy, top - 0.02), (hy, deck + 0.03), (-hy, deck + 0.03)):
        parts.append(board((length - post, 0.022, 0.022), (0.0, y, z), material, "frame"))
    for x, z in ((hx, top - 0.02), (-hx, top - 0.02), (hx, deck + 0.03), (-hx, deck + 0.03)):
        parts.append(board((0.022, width - post, 0.022), (x, 0.0, z), material, "frame"))
    inset = post * 0.5 + 0.01
    parts.extend(_slats(material, -hx + inset, hx - inset, hy, hy, deck + 0.04, top - 0.04, True))
    parts.extend(_slats(material, -hx + inset, hx - inset, -hy, -hy, deck + 0.04, top - 0.04, True))
    parts.extend(_slats(material, hx, hx, -hy + inset, hy - inset, deck + 0.04, top - 0.04, False))
    parts.extend(_slats(material, -hx, -hx, -hy + inset, hy - inset, deck + 0.04, top - 0.04, False))
    return join_tagged(parts)


register(Category(
    category_id="crib",
    code="B04",
    family="床具",
    criterion="四周都是竖栏，床面离地较高",
    build=build,
    allowed_parts=frozenset({"frame", "leg_base", "slat"}),
))

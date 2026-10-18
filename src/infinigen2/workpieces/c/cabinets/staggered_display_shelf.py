"""C21 博古架。

结构判据：格子大小不一、错位排列。
下半层和上半层的竖隔不在同一条线上，横隔的高度也不均匀。
"""

import procfunc as pf

from infinigen2.workpieces.c.cabinets.parts import (
    Category,
    hard_material,
    join_tagged,
    open_carcass,
    placed,
    register,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    depth = pf.random.uniform(rng_size, 0.22, 0.30)
    width = pf.random.uniform(rng_size, 0.80, 1.10)
    height = pf.random.uniform(rng_size, 1.40, 1.75)
    lower_split = pf.random.uniform(rng_size, 0.34, 0.46)
    upper_split = pf.random.uniform(rng_size, 0.58, 0.72)
    material = hard_material(rng_mat)
    t = 0.016
    mid = height * pf.random.uniform(rng_size, 0.42, 0.52)
    low = mid * pf.random.uniform(rng_size, 0.42, 0.58)
    high = mid + (height - mid) * pf.random.uniform(rng_size, 0.45, 0.60)
    parts = open_carcass(material, depth, width, height, t)
    parts.append(placed((depth, t, mid), (0.0, width * lower_split, 0.0), material, "shelf"))
    parts.append(placed((depth, t, height - mid), (0.0, width * upper_split, mid), material, "shelf"))
    parts.append(placed((depth, width, t), (0.0, 0.0, low), material, "shelf"))
    parts.append(placed((depth, width * lower_split, t), (0.0, 0.0, mid), material, "shelf"))
    parts.append(placed((depth, width * (1.0 - lower_split), t), (0.0, width * lower_split, mid * 0.55), material, "shelf"))
    parts.append(placed((depth, width, t), (0.0, 0.0, high), material, "shelf"))
    return join_tagged(parts)


register(Category(
    category_id="staggered_display_shelf",
    code="C21",
    family="柜架",
    criterion="格子大小不一、错位排列",
    build=build,
    allowed_parts=frozenset({"carcass", "back_panel", "shelf"}),
))

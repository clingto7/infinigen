"""S17 摇椅。

结构判据：腿落在两根弧形摇脚上。
座靠复用餐椅。四根短柱从摇脚接到座板下，柱脚不落地。
"""

import procfunc as pf

from infinigen2.workpieces.assemble import hard_material
from infinigen2.workpieces.c.seating.parts import (
    Category,
    dining_with_back,
    join_tagged,
    register,
    rocker,
    strut,
)


def _rocker_z(x: float, radius: float, lift: float) -> float:
    return radius - (radius * radius - x * x) ** 0.5 + lift


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_back, rng_seat, rng_mat = rng.spawn(5)
    depth = pf.random.uniform(rng_size, 0.50, 0.58)
    width = pf.random.uniform(rng_size, 0.48, 0.56)
    elevation = pf.random.uniform(rng_size, 0.46, 0.52)
    thickness = pf.random.uniform(rng_size, 0.040, 0.052)
    back_height = pf.random.uniform(rng_size, 0.40, 0.50)
    radius = pf.random.uniform(rng_size, 0.88, 1.05)
    material = hard_material(rng_mat)
    body = dining_with_back(
        rng_style, rng_back, rng_seat,
        depth, width, elevation, thickness, back_height, material,
    )
    x_front = depth * 0.34
    x_rear = -depth * 0.36
    under = elevation - thickness
    section = (0.034, 0.022)
    parts = [body]
    for side in (-1.0, 1.0):
        y = side * width * 0.40
        parts.extend(rocker(y, -0.48, 0.42, radius, section, material))
        for x in (x_front, x_rear):
            z0 = _rocker_z(x, radius, section[0] * 0.5)
            parts.append(strut((x, y, z0), (x, y, under), (0.032, 0.028), material, "leg_base"))
    return join_tagged(parts)


register(Category(
    category_id="rocking_chair",
    code="S17",
    family="坐具",
    criterion="腿落在两根弧形摇脚上",
    build=build,
    allowed_parts=frozenset({"seat", "back", "leg_base"}),
))

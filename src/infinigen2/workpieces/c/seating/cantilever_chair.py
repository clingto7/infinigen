"""S19 悬臂管椅。

结构判据：一根连续弯管形成底座和座下支撑，无后腿。
左右各一根圆管：前部着地，经后方弯上，再伸到座下并在到位前停下。座靠复用餐椅。
"""

import procfunc as pf

from infinigen2.workpieces.assemble import hard_material
from infinigen2.workpieces.c.seating.parts import (
    Category,
    chain,
    dining_with_back,
    join_tagged,
    register,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_back, rng_seat, rng_mat = rng.spawn(5)
    depth = pf.random.uniform(rng_size, 0.48, 0.56)
    width = pf.random.uniform(rng_size, 0.46, 0.54)
    elevation = pf.random.uniform(rng_size, 0.44, 0.48)
    thickness = pf.random.uniform(rng_size, 0.036, 0.048)
    back_height = pf.random.uniform(rng_size, 0.34, 0.44)
    radius = pf.random.uniform(rng_size, 0.012, 0.016)
    material = hard_material(rng_mat)
    body = dining_with_back(
        rng_style, rng_back, rng_seat,
        depth, width, elevation, thickness, back_height, material,
    )
    under = elevation - thickness
    rear_x = -depth * 0.5 - 0.02
    parts = [body]
    for side in (-1.0, 1.0):
        y = side * width * 0.42
        parts.extend(chain(
            [
                (depth * 0.42, y, radius),
                (rear_x, y, radius),
                (rear_x, y, under),
                (depth * 0.12, y, under),
            ],
            material, "leg_base", radius=radius, overlap=radius,
        ))
    return join_tagged(parts)


register(Category(
    category_id="cantilever_chair",
    code="S19",
    family="坐具",
    criterion="一根连续弯管形成底座和座下支撑，无后腿",
    build=build,
    allowed_parts=frozenset({"seat", "back", "leg_base"}),
))

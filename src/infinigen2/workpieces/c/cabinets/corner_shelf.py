"""C20 三角角架。

结构判据：平面为三角形的多层搁板，放墙角。
直角在原点，两条直角边贴墙，斜边朝向室内。层数是构型。
"""

import procfunc as pf

from infinigen2.workpieces.c.cabinets.parts import (
    Category,
    hard_material,
    join_tagged,
    placed,
    register,
    triangle_slab,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    span = pf.random.uniform(rng_size, 0.32, 0.46)
    height = pf.random.uniform(rng_size, 0.70, 1.05)
    count = int(pf.control.choice(rng_size, [(3, 1.0), (4, 1.0)]))
    material = hard_material(rng_mat)
    parts = [placed((0.028, 0.028, height), (0.0, 0.0, 0.0), material, "frame")]
    for index in range(count):
        z = 0.08 + (height - 0.12) * index / (count - 1)
        parts.append(triangle_slab(span, span * 0.92, 0.016, z, material, "shelf"))
    return join_tagged(parts)


register(Category(
    category_id="corner_shelf",
    code="C20",
    family="柜架",
    criterion="平面为三角形的多层搁板，放墙角",
    build=build,
    allowed_parts=frozenset({"frame", "shelf"}),
))

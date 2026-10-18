"""O02 衣帽架。

结构判据：单根立柱，底部三到四只脚，顶部挂钩。
脚数是构型。脚从立柱下端向外撑到地面，挂钩在立柱上部向外再向上弯。
"""

import math

import procfunc as pf

from infinigen2.workpieces.c.other.parts import (
    Category,
    board,
    hard_material,
    join_tagged,
    register,
    rod,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    height = pf.random.uniform(rng_size, 1.70, 1.85)
    feet = int(pf.control.choice(rng_size, [(3, 1.0), (4, 1.0)]))
    reach = pf.random.uniform(rng_size, 0.22, 0.30)
    material = hard_material(rng_mat)
    parts = [board((0.045, 0.045, height - 0.16), (0.0, 0.0, 0.16 + (height - 0.16) * 0.5), material, "leg_base")]
    for index in range(feet):
        theta = math.tau * index / feet
        parts.append(rod(
            (0.0, 0.0, 0.20),
            (reach * math.cos(theta), reach * math.sin(theta), 0.016),
            0.012, material, "leg_base",
        ))
    hook_z = height - 0.12
    for index in range(4):
        theta = math.tau * (index + 0.5) / 4.0
        tip = (0.11 * math.cos(theta), 0.11 * math.sin(theta), hook_z)
        parts.append(rod((0.0, 0.0, hook_z), tip, 0.008, material, "frame"))
        parts.append(rod(tip, (tip[0], tip[1], hook_z + 0.045), 0.008, material, "frame"))
    return join_tagged(parts)


register(Category(
    category_id="coat_rack",
    code="O02",
    family="其他家具",
    criterion="单根立柱，底部三到四只脚，顶部挂钩",
    build=build,
    allowed_parts=frozenset({"leg_base", "frame"}),
))

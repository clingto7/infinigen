"""C17 翻斗鞋柜。

结构判据：正面是向外翻出的斗，内部是斜置隔板。
斗数是构型。每个斗绕下沿向前翻，斗里有一块更斜的隔板。
"""

import math

import procfunc as pf

from infinigen2.workpieces.c.cabinets.parts import (
    Category,
    board,
    hard_material,
    join_tagged,
    open_carcass,
    register,
)


def _spin(local, hinge, angle):
    x, y, z = local
    cosine = math.cos(angle)
    sine = math.sin(angle)
    return (
        hinge[0] + x * cosine + z * sine,
        hinge[1] + y,
        hinge[2] - x * sine + z * cosine,
    )


def _bin(material, hinge, depth, width, height, angle) -> list[pf.MeshObject]:
    parts = []
    specs = [
        ((0.014, width, height), (0.0, 0.0, height * 0.5), angle, "drawer_front"),
        ((depth, width, 0.012), (-depth * 0.5, 0.0, 0.008), angle, "drawer_front"),
        ((depth, 0.012, height), (-depth * 0.5, width * 0.5, height * 0.5), angle, "drawer_front"),
        ((depth, 0.012, height), (-depth * 0.5, -width * 0.5, height * 0.5), angle, "drawer_front"),
        ((depth * 0.82, width - 0.03, 0.010), (-depth * 0.42, 0.0, height * 0.42), angle + 0.35, "shelf"),
    ]
    for size, local, tilt, part in specs:
        parts.append(board(size, _spin(local, hinge, angle), material, part, rotation=(0.0, tilt, 0.0)))
    return parts


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    depth = pf.random.uniform(rng_size, 0.28, 0.36)
    width = pf.random.uniform(rng_size, 0.60, 0.90)
    height = pf.random.uniform(rng_size, 0.90, 1.15)
    count = int(pf.control.choice(rng_size, [(2, 1.0), (3, 1.0)]))
    angle = pf.random.uniform(rng_size, 0.40, 0.58)
    material = hard_material(rng_mat)
    parts = open_carcass(material, depth, width, height)
    slot = height / count
    bin_w = width - 0.08
    for index in range(count):
        hinge = (depth - 0.01, width * 0.5, index * slot + 0.02)
        parts.extend(_bin(material, hinge, depth * 0.72, bin_w, slot - 0.04, angle))
    return join_tagged(parts)


register(Category(
    category_id="tilt_out_shoe_cabinet",
    code="C17",
    family="柜架",
    criterion="正面是向外翻出的斗，内部是斜置隔板",
    build=build,
    allowed_parts=frozenset({"carcass", "back_panel", "drawer_front", "shelf"}),
))

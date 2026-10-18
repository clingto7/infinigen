"""S22 躺椅。

结构判据：长条座面，靠背可倾斜，常为条木。
两侧支架沿座面再折上成靠背，倾斜程度是构型。条木横跨在支架上。
"""

import math

import procfunc as pf

from infinigen2.workpieces.assemble import hard_material
from infinigen2.workpieces.c.seating.parts import (
    Category,
    chain,
    join_tagged,
    oriented_board,
    register,
    strut,
)


def _samples(start, end, count):
    points = []
    for index in range(count):
        t = (index + 0.5) / count
        points.append(tuple(start[i] + (end[i] - start[i]) * t for i in range(3)))
    return points


def _up_normal(start, end):
    dx = end[0] - start[0]
    dz = end[2] - start[2]
    length = math.hypot(dx, dz)
    return (dz / length, 0.0, -dx / length)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    width = pf.random.uniform(rng_size, 0.58, 0.70)
    recline = pf.random.uniform(rng_size, 0.55, 0.85)
    material = hard_material(rng_mat)
    y_side = width * 0.42
    front = (0.70, 0.0, 0.28)
    hip = (0.05, 0.0, 0.36)
    head = (-0.15 - 0.18 * recline, 0.0, 0.62 + 0.22 * recline)
    normal_seat = _up_normal(front, hip)
    normal_back = _up_normal(hip, head)
    parts = []
    for side in (-1.0, 1.0):
        y = side * y_side
        rail = [(front[0], y, front[2]), (hip[0], y, hip[2]), (head[0], y, head[2])]
        parts.extend(chain(rail, material, "frame", section=(0.036, 0.022), overlap=0.02))
        parts.append(strut((0.62, y, 0.016), (0.62, y, front[2] - 0.01), (0.032, 0.024), material, "leg_base"))
        parts.append(strut((0.02, y, 0.016), (0.02, y, hip[2] - 0.01), (0.032, 0.024), material, "leg_base"))
    span = width * 0.5 + 0.03
    for center in _samples(front, hip, 8):
        lifted = (center[0], 0.0, center[2] + 0.012)
        parts.append(oriented_board(lifted, normal_seat, (0.055, span * 2.0, 0.016), material, "seat"))
    for center in _samples(hip, head, 6):
        lifted = (center[0], 0.0, center[2] + 0.012)
        parts.append(oriented_board(lifted, normal_back, (0.055, span * 2.0, 0.016), material, "back"))
    return join_tagged(parts)


register(Category(
    category_id="lounge_chair",
    code="S22",
    family="坐具",
    criterion="长条座面，靠背可倾斜，常为条木",
    build=build,
    allowed_parts=frozenset({"seat", "back", "leg_base", "frame"}),
))

"""S21 公园长椅。

结构判据：座面和靠背由多根横向条木组成，两端是侧框。
条木沿长度方向。靠背条木跟着后腿后倾。侧框含前腿、后腿和扶手。
"""

import procfunc as pf

from infinigen2.workpieces.assemble import hard_material
from infinigen2.workpieces.c.seating.parts import (
    Category,
    board,
    join_tagged,
    oriented_board,
    register,
    strut,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    length = pf.random.uniform(rng_size, 1.35, 1.70)
    seat_z = pf.random.uniform(rng_size, 0.42, 0.48)
    lean = pf.random.uniform(rng_size, 0.10, 0.16)
    material = hard_material(rng_mat)
    y_frame = length * 0.5 - 0.045
    rear_top = seat_z + 0.50
    rear_dx = -lean
    parts = []
    for side in (-1.0, 1.0):
        y = side * y_frame
        parts.append(strut((0.18, y, 0.02), (0.18, y, seat_z + 0.20), (0.038, 0.028), material, "leg_base"))
        parts.append(strut((-0.16, y, 0.02), (-0.16 + rear_dx, y, rear_top), (0.038, 0.028), material, "leg_base"))
        arm_z = seat_z + 0.22
        t = arm_z / rear_top
        arm_x = -0.16 + rear_dx * t
        parts.append(strut((arm_x, y, arm_z), (0.18, y, arm_z), (0.032, 0.028), material, "arm"))
        parts.append(strut((-0.14, y, seat_z), (0.16, y, seat_z), (0.03, 0.024), material, "leg_base"))
    slat_y = length - 0.06
    n_seat = 4
    for index in range(n_seat):
        x = -0.10 + index * 0.07
        parts.append(board((0.055, slat_y, 0.02), (x, 0.0, seat_z + 0.016), material, "seat"))
    n_back = 3
    normal = (rear_top, 0.0, -rear_dx)
    for index in range(n_back):
        z = seat_z + 0.16 + index * 0.12
        t = z / rear_top
        x = -0.16 + rear_dx * t
        parts.append(oriented_board((x, 0.0, z), normal, (0.045, slat_y, 0.02), material, "back"))
    return join_tagged(parts)


register(Category(
    category_id="park_bench",
    code="S21",
    family="坐具",
    criterion="座面和靠背由多根横向条木组成，两端是侧框",
    build=build,
    allowed_parts=frozenset({"seat", "back", "arm", "leg_base"}),
))

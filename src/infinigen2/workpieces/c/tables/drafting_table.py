"""T18 绘图桌。

结构判据：桌面倾斜，带挡边。
前缘低、后缘高。挡边立在低的前缘上，跟着桌面一起倾斜。前腿短、后腿长。
"""

import math

import procfunc as pf

from infinigen2.workpieces.assemble import hard_material
from infinigen2.workpieces.c.tables.parts import (
    Category,
    board,
    join_tagged,
    register,
    strut,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    depth = pf.random.uniform(rng_size, 0.72, 0.90)
    length = pf.random.uniform(rng_size, 1.15, 1.55)
    front_z = pf.random.uniform(rng_size, 0.74, 0.80)
    angle = pf.random.uniform(rng_size, 0.22, 0.40)
    thick = pf.random.uniform(rng_size, 0.028, 0.040)
    material = hard_material(rng_mat)
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    center_z = front_z + depth * 0.5 * sin_a - thick * 0.5 * cos_a
    top = board(
        (depth, length, thick), (0.0, 0.0, center_z), material, "top",
        rotation=(0.0, angle, 0.0),
    )
    lip_h = 0.030
    lip_t = 0.014
    wx = depth * 0.5 * cos_a + thick * 0.5 * sin_a
    wz = -depth * 0.5 * sin_a + thick * 0.5 * cos_a + center_z
    lip = board(
        (lip_t, length * 0.96, lip_h),
        (
            wx + sin_a * lip_h * 0.5 - cos_a * lip_t * 0.5,
            0.0,
            wz + cos_a * lip_h * 0.5 + sin_a * lip_t * 0.5,
        ),
        material, "frame", rotation=(0.0, angle, 0.0),
    )
    parts = [top, lip]
    y_leg = length * 0.5 - 0.08
    for sx in (-1.0, 1.0):
        x_local = sx * (depth * 0.5 - 0.09)
        x = x_local * cos_a - thick * 0.5 * sin_a
        z_top = -x_local * sin_a - thick * 0.5 * cos_a + center_z
        for sy in (-1.0, 1.0):
            parts.append(strut(
                (x, sy * y_leg, 0.02), (x, sy * y_leg, z_top),
                (0.040, 0.040), material, "leg_base",
            ))
        parts.append(strut(
            (x, -y_leg, 0.16), (x, y_leg, 0.16),
            (0.028, 0.022), material, "leg_base",
        ))
    return join_tagged(parts)


register(Category(
    category_id="drafting_table",
    code="T18",
    family="桌台",
    criterion="桌面倾斜，带挡边",
    build=build,
    allowed_parts=frozenset({"top", "frame", "leg_base"}),
))

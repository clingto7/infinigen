"""S20 儿童高脚椅。

结构判据：高腿外撑，前方有托盘，座面有围挡。
腿从较窄的座下斜到较宽的地面。托盘在座面前方，两侧和前方有围挡。
"""

import procfunc as pf

from infinigen2.workpieces.assemble import hard_material
from infinigen2.workpieces.c.seating.parts import (
    Category,
    board,
    join_tagged,
    point_at_z,
    register,
    rod,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    depth = pf.random.uniform(rng_size, 0.30, 0.36)
    width = pf.random.uniform(rng_size, 0.30, 0.36)
    elevation = pf.random.uniform(rng_size, 0.54, 0.62)
    thickness = 0.028
    back_h = pf.random.uniform(rng_size, 0.36, 0.46)
    splay = pf.random.uniform(rng_size, 0.08, 0.12)
    material = hard_material(rng_mat)
    parts = [board((depth, width, thickness), (0.0, 0.0, elevation - thickness * 0.5), material, "seat")]
    x_back = -depth * 0.5 + 0.016
    parts.append(board(
        (0.018, width * 0.82, back_h),
        (x_back, 0.0, elevation + back_h * 0.45),
        material, "back",
    ))
    for side in (-1.0, 1.0):
        parts.append(board(
            (0.024, 0.024, back_h + 0.02),
            (x_back, side * width * 0.40, elevation + back_h * 0.42),
            material, "back",
        ))
    under = elevation - thickness
    corners = [(-1.0, -1.0), (-1.0, 1.0), (1.0, -1.0), (1.0, 1.0)]
    floor = {}
    for sx, sy in corners:
        top = (sx * depth * 0.36, sy * width * 0.36, under + 0.01)
        foot = (sx * (depth * 0.36 + splay), sy * (width * 0.36 + splay), 0.014)
        floor[(sx, sy)] = (foot, top)
        parts.append(rod(foot, top, 0.014, material, "leg_base"))
    left = point_at_z(*floor[(1, -1)], 0.20)
    right = point_at_z(*floor[(1, 1)], 0.20)
    parts.append(rod(left, right, 0.012, material, "leg_base"))
    # The guards reach down into the seat and the front guard overlaps the
    # side guards; otherwise the whole arm assembly floats about a
    # centimetre above the chair.
    for side in (-1.0, 1.0):
        parts.append(board(
            (depth * 0.92, 0.016, 0.14),
            (0.0, side * (width * 0.5 + 0.004), elevation + 0.06),
            material, "arm",
        ))
    parts.append(board(
        (0.016, width * 1.02, 0.10),
        (depth * 0.46, 0.0, elevation + 0.07),
        material, "arm",
    ))
    tray_z = elevation + 0.14
    parts.append(board(
        (0.20, width + 0.08, 0.016),
        (depth * 0.5 + 0.08, 0.0, tray_z),
        material, "arm",
    ))
    for side in (-1.0, 1.0):
        y = side * (width * 0.5 + 0.004)
        parts.append(rod(
            (depth * 0.20, y, elevation + 0.12),
            (depth * 0.5 + 0.06, y, tray_z),
            0.010, material, "arm",
        ))
    return join_tagged(parts)


register(Category(
    category_id="high_chair",
    code="S20",
    family="坐具",
    criterion="高腿外撑，前方有托盘，座面有围挡",
    build=build,
    allowed_parts=frozenset({"seat", "back", "arm", "leg_base"}),
))

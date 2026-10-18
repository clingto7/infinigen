"""C13 转角柜。

结构判据：平面为 L 形，两段柜体在转角相接。
主柜正面朝 +X，回柜正面朝 +Y，两段只在接缝处相贴。
内角立一根封板，落在两段柜体之外的房间一侧。
"""

import math

import procfunc as pf

from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat, rng_main, rng_return = rng.spawn(4)
    main_depth = pf.random.uniform(rng_size, 0.35, 0.45)
    main_width = pf.random.uniform(rng_size, 0.80, 1.15)
    return_length = pf.random.uniform(rng_size, 0.60, 0.95)
    return_depth = pf.random.uniform(rng_size, 0.35, 0.45)
    height = pf.random.uniform(rng_size, 0.72, 0.95)
    main = assemble.fronted_bay(
        rng_main, (main_depth, main_width, height), "door", n_spaces_y=1
    )
    # local X is depth and becomes world +Y after a +90 degree yaw
    side = assemble.fronted_bay(
        rng_return, (return_depth, return_length, height), "door", n_spaces_y=1
    )
    pf.ops.object.set_transform(
        side,
        location=(main_depth + return_length, 0.0, 0.0),
        rotation_euler=(0.0, 0.0, math.pi / 2.0),
    )
    post = assemble.tagged_box(
        (0.02, 0.02, height),
        (main_depth, return_depth, 0.0),
        assemble.hard_material(rng_mat),
        "carcass",
    )
    return assemble.join_tagged([main, side, post])


register(
    Category(
        category_id="corner_cabinet",
        code="C13",
        family="柜架",
        criterion="平面为 L 形，两段柜体在转角相接",
        build=build,
        allowed_parts=frozenset(
            {
                "carcass",
                "shelf",
                "back_panel",
                "door_frame",
                "door_panel",
                "handle",
            }
        ),
    )
)

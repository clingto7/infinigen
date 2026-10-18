"""T13 梳妆台。

结构判据：书桌加两侧抽屉，桌面后方竖立镜框。
两侧柜正面锁成抽屉。镜面是 glass，不喷涂。镜宽留在两侧柜之间的空档内。
"""

import procfunc as pf

from infinigen2.objects import desk
from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register


def _mirror(
    rng: pf.RNG, width: float, material: pf.Material
) -> tuple[pf.MeshObject, float]:
    frame = pf.random.uniform(rng, 0.035, 0.050)
    height = pf.random.uniform(rng, 0.45, 0.68)
    thickness = 0.028
    opening_w = width - 2.0 * frame
    opening_h = height - 2.0 * frame
    parts = [
        assemble.tagged_box(
            (thickness, opening_w, frame), (0.0, frame, 0.0), material, "frame"
        ),
        assemble.tagged_box(
            (thickness, opening_w, frame),
            (0.0, frame, height - frame),
            material,
            "frame",
        ),
        assemble.tagged_box((thickness, frame, height), (0.0, 0.0, 0.0), material, "frame"),
        assemble.tagged_box(
            (thickness, frame, height), (0.0, width - frame, 0.0), material, "frame"
        ),
        assemble.tagged_box(
            (0.006, opening_w - 0.004, opening_h - 0.004),
            (0.011, frame + 0.002, frame + 0.002),
            material,
            "glass",
        ),
    ]
    return assemble.join_tagged(parts), height


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_desk, rng_mirror, rng_mat = rng.spawn(3)
    body = desk.desk_with_side_storage_rand(
        rng_desk, spray_tags=True, front_style="drawer", shared_parts=True
    ).mesh
    x0, _x1, y0, y1, _z0, z1 = assemble.vertex_bounds(body)
    desk_width = y1 - y0
    # side cabinets are 15–30% of the width each, so the center gap is at least 40%
    mirror_width = desk_width * pf.random.uniform(rng_mirror, 0.28, 0.36)
    material = assemble.hard_material(rng_mat)
    mirror, _height = _mirror(rng_mirror, mirror_width, material)
    pf.ops.object.set_transform(
        mirror,
        location=(x0 + 0.012, (y0 + y1) / 2.0 - mirror_width / 2.0, z1),
    )
    return assemble.join_tagged([body, mirror])


register(
    Category(
        category_id="dressing_table",
        code="T13",
        family="桌台",
        criterion="书桌加两侧抽屉，桌面后方竖立镜框",
        build=build,
        allowed_parts=frozenset(
            {
                "top",
                "carcass",
                "shelf",
                "back_panel",
                "drawer_front",
                "drawer_box",
                "handle",
                "frame",
                "glass",
            }
        ),
    )
)

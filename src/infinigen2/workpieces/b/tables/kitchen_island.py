"""T15 厨房岛台。

结构判据：柜体组合加外伸台面，一侧可坐。
两只同高柜并排，正面同为门或同为抽屉。台面在 -Y 侧悬出，悬出段下面没有腿。
"""

import procfunc as pf

from infinigen2.objects import storage
from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_front, rng_left, rng_right, rng_top = rng.spawn(5)
    depth = pf.random.uniform(rng_size, 0.58, 0.70)
    width = pf.random.uniform(rng_size, 0.58, 0.85)
    height = pf.random.uniform(rng_size, 0.86, 0.92)
    overhang = pf.random.uniform(rng_size, 0.30, 0.40)
    thickness = pf.random.uniform(rng_size, 0.035, 0.050)
    front = pf.control.choice(rng_front, [("door", 1.0), ("drawer", 1.0)])
    cabinets = []
    for index, cabinet_rng in enumerate((rng_left, rng_right)):
        cabinet = storage.storage_composite_rand(
            cabinet_rng,
            dimensions=pf.Vector((depth, width, height)),
            n_spaces_y=1,
            front_style=front,
            spray_tags=True,
        ).mesh
        assemble.adopt_storage(cabinet)
        pf.ops.object.set_transform(cabinet, location=(0.0, index * width, 0.0))
        cabinets.append(cabinet)
    total_width = 2.0 * width
    top = assemble.tagged_slab(
        (depth, total_width + overhang, thickness),
        assemble.hard_material(rng_top),
        "top",
    )
    # cabinets occupy y in [0, total_width]; the extra length hangs off -Y
    pf.ops.object.set_transform(
        top,
        location=(depth / 2.0, (total_width - overhang) / 2.0, height),
    )
    return assemble.join_tagged([*cabinets, top])


register(
    Category(
        category_id="kitchen_island",
        code="T15",
        family="桌台",
        criterion="柜体组合加外伸台面，一侧可坐",
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
                "door_frame",
                "door_panel",
            }
        ),
    )
)

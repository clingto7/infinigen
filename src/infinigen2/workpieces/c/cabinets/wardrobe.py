"""C16 衣柜。

结构判据：高柜，内部挂衣杆和顶部搁板，大门扇。
单扇或双开门是构型。挂衣杆在搁板下方，门盖住正面。
"""

import procfunc as pf

from infinigen2.workpieces.assemble import open_bay
from infinigen2.workpieces.c.cabinets.parts import (
    Category,
    board,
    door_leaf,
    hard_material,
    join_tagged,
    register,
    rod,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_bay, rng_door, rng_mat = rng.spawn(4)
    depth = pf.random.uniform(rng_size, 0.56, 0.64)
    width = pf.random.uniform(rng_size, 0.90, 1.30)
    height = pf.random.uniform(rng_size, 1.85, 2.05)
    leaves = int(pf.control.choice(rng_size, [(1, 1.0), (2, 1.0)]))
    material = hard_material(rng_mat)
    carcass = open_bay(rng_bay, (depth, width, height), n_spaces_y=1, n_spaces_z=1)
    shelf_z = height - 0.26
    parts = [
        carcass,
        board(
            (depth - 0.05, width - 0.05, 0.016),
            (depth * 0.5, width * 0.5, shelf_z),
            material, "shelf",
        ),
        rod(
            (depth * 0.48, 0.06, shelf_z - 0.14),
            (depth * 0.48, width - 0.06, shelf_z - 0.14),
            0.012, material, "frame",
        ),
    ]
    door_h = height - 0.03
    gap = 0.008
    leaf_w = (width - gap * (leaves + 1)) / leaves
    rngs = rng_door.spawn(leaves)
    for index, door_rng in enumerate(rngs):
        parts.append(door_leaf(
            door_rng, 0.022, leaf_w, door_h,
            (depth, gap + index * (leaf_w + gap), 0.015),
        ))
    return join_tagged(parts)


register(Category(
    category_id="wardrobe",
    code="C16",
    family="柜架",
    criterion="高柜，内部挂衣杆和顶部搁板，大门扇",
    build=build,
    allowed_parts=frozenset({
        "carcass", "shelf", "back_panel", "frame",
        "door_frame", "door_panel", "handle",
    }),
))

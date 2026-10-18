"""C18 百叶门柜。

结构判据：门芯由多根斜向百叶条组成。
柜体是开敞格。门扇数是构型，门芯是斜百叶而不是平板。
"""

import procfunc as pf

from infinigen2.workpieces.assemble import open_bay
from infinigen2.workpieces.c.cabinets.parts import (
    Category,
    board,
    hard_material,
    join_tagged,
    register,
)


def _louver_leaf(material, origin, width, height, thickness) -> list[pf.MeshObject]:
    x, y, z = origin
    stile = 0.035
    rail = 0.04
    parts = [
        board((thickness, stile, height), (x, y + stile * 0.5, z + height * 0.5), material, "door_frame"),
        board((thickness, stile, height), (x, y + width - stile * 0.5, z + height * 0.5), material, "door_frame"),
        board((thickness, width, rail), (x, y + width * 0.5, z + rail * 0.5), material, "door_frame"),
        board((thickness, width, rail), (x, y + width * 0.5, z + height - rail * 0.5), material, "door_frame"),
    ]
    inner_h = height - 2.0 * rail
    inner_w = width - 2.0 * stile
    count = max(6, int(inner_h / 0.048))
    pitch = inner_h / count
    for index in range(count):
        center_z = z + rail + pitch * (index + 0.5)
        parts.append(board(
            (0.012, inner_w, 0.036),
            (x, y + width * 0.5, center_z),
            material, "louver", rotation=(0.0, 0.62, 0.0),
        ))
    return parts


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_bay, rng_mat = rng.spawn(3)
    depth = pf.random.uniform(rng_size, 0.34, 0.44)
    width = pf.random.uniform(rng_size, 0.55, 0.95)
    height = pf.random.uniform(rng_size, 0.80, 1.25)
    leaves = int(pf.control.choice(rng_size, [(1, 1.0), (2, 1.0)]))
    material = hard_material(rng_mat)
    parts = [open_bay(rng_bay, (depth, width, height), n_spaces_y=1, n_spaces_z=1)]
    leaf_w = width / leaves
    for index in range(leaves):
        parts.extend(_louver_leaf(
            material, (depth + 0.004, index * leaf_w, 0.0), leaf_w, height, 0.018
        ))
    return join_tagged(parts)


register(Category(
    category_id="louvered_cabinet",
    code="C18",
    family="柜架",
    criterion="门芯由多根斜向百叶条组成",
    build=build,
    allowed_parts=frozenset({"carcass", "shelf", "back_panel", "door_frame", "louver"}),
))

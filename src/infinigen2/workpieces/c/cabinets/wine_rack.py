"""C22 格子酒架。

结构判据：菱形或 X 形交叉隔板。
外框里每一格是一对交叉斜板。格数是构型。
"""

import procfunc as pf

from infinigen2.workpieces.c.cabinets.parts import (
    Category,
    hard_material,
    join_tagged,
    open_carcass,
    register,
    strut,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    depth = pf.random.uniform(rng_size, 0.22, 0.30)
    width = pf.random.uniform(rng_size, 0.50, 0.80)
    height = pf.random.uniform(rng_size, 0.50, 0.80)
    count = int(pf.control.choice(rng_size, [(2, 1.0), (3, 1.0)]))
    material = hard_material(rng_mat)
    parts = open_carcass(material, depth, width, height)
    margin = 0.02
    cell_w = (width - 2.0 * margin) / count
    cell_h = (height - 2.0 * margin) / count
    x = depth * 0.5
    section = (0.012, depth * 0.62)
    for row in range(count):
        for col in range(count):
            y0 = margin + col * cell_w
            z0 = margin + row * cell_h
            parts.append(strut((x, y0, z0), (x, y0 + cell_w, z0 + cell_h), section, material, "shelf"))
            parts.append(strut((x, y0, z0 + cell_h), (x, y0 + cell_w, z0), section, material, "shelf"))
    return join_tagged(parts)


register(Category(
    category_id="wine_rack",
    code="C22",
    family="柜架",
    criterion="菱形或 X 形交叉隔板",
    build=build,
    allowed_parts=frozenset({"carcass", "back_panel", "shelf"}),
))

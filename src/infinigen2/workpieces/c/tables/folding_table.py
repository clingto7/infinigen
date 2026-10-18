"""T17 折叠桌。

结构判据：桌面下是可折叠的 X 腿或 U 形管腿。
X 形和 U 形是构型。X 在左右两侧各一对，沿长度交叉。U 形管在两端，弯在地面。
"""

import procfunc as pf

from infinigen2.workpieces.assemble import hard_material
from infinigen2.workpieces.c.tables.parts import (
    Category,
    chain,
    join_tagged,
    register,
    strut,
    tabletop,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_mat = rng.spawn(3)
    depth = pf.random.uniform(rng_size, 0.70, 0.86)
    length = pf.random.uniform(rng_size, 1.10, 1.50)
    height = pf.random.uniform(rng_size, 0.72, 0.76)
    top_t = pf.random.uniform(rng_size, 0.028, 0.040)
    radius = pf.random.uniform(rng_size, 0.012, 0.016)
    style = pf.control.choice(rng_style, [("x", 1.0), ("u", 1.0)])
    material = hard_material(rng_mat)
    under = height - top_t
    parts = [tabletop((depth, length, top_t), material, under)]
    if style == "x":
        y0 = length * 0.40
        section = (0.036, 0.022)
        for side in (-1.0, 1.0):
            x = side * depth * 0.30
            parts.append(strut((x, -y0, 0.02), (x, y0, under), section, material, "leg_base"))
            parts.append(strut((x, y0, 0.02), (x, -y0, under), section, material, "leg_base"))
    else:
        y_end = length * 0.5 - 0.14
        x0 = depth * 0.32
        for y in (-y_end, y_end):
            parts.extend(chain(
                [
                    (-x0, y, under),
                    (-x0, y, radius),
                    (x0, y, radius),
                    (x0, y, under),
                ],
                material, "leg_base", radius=radius, overlap=radius,
            ))
    return join_tagged(parts)


register(Category(
    category_id="folding_table",
    code="T17",
    family="桌台",
    criterion="桌面下是可折叠的 X 腿或 U 形管腿",
    build=build,
    allowed_parts=frozenset({"top", "leg_base"}),
))

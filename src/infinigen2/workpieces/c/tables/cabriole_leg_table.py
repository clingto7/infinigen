"""T21 弯腿边桌。

结构判据：S 形弯腿，腿上部有裙板。
腿先向外弯出膝，再收回踝，脚略向外。裙板挂在桌面下、四腿之间。
"""

import procfunc as pf

from infinigen2.workpieces.assemble import hard_material
from infinigen2.workpieces.c.tables.parts import (
    Category,
    board,
    chain,
    join_tagged,
    register,
    tabletop,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    depth = pf.random.uniform(rng_size, 0.42, 0.55)
    length = pf.random.uniform(rng_size, 0.48, 0.66)
    height = pf.random.uniform(rng_size, 0.68, 0.74)
    top_t = pf.random.uniform(rng_size, 0.028, 0.040)
    bow = pf.random.uniform(rng_size, 0.045, 0.065)
    material = hard_material(rng_mat)
    under = height - top_t
    apron_h = 0.07
    section = (0.036, 0.036)
    parts = [tabletop((depth, length, top_t), material, under)]
    leg_top = under - apron_h + 0.012
    for sx in (-1.0, 1.0):
        for sy in (-1.0, 1.0):
            x0 = sx * (depth * 0.5 - 0.055)
            y0 = sy * (length * 0.5 - 0.055)
            samples = ((1.0, 0.0), (0.82, 0.35), (0.64, 1.0), (0.42, 0.55), (0.22, 0.05), (0.0, 0.40))
            points = []
            for height, flare in samples:
                z = 0.025 + (leg_top - 0.025) * height
                points.append((x0 + sx * bow * flare, y0 + sy * bow * flare, z))
            parts.extend(chain(points, material, "leg_base", section=section, overlap=0.016))
    z_apron = under - apron_h * 0.5
    parts.append(board((0.016, length - 0.06, apron_h), (depth * 0.5 - 0.03, 0.0, z_apron), material, "frame"))
    parts.append(board((0.016, length - 0.06, apron_h), (-depth * 0.5 + 0.03, 0.0, z_apron), material, "frame"))
    parts.append(board((depth - 0.06, 0.016, apron_h), (0.0, length * 0.5 - 0.03, z_apron), material, "frame"))
    parts.append(board((depth - 0.06, 0.016, apron_h), (0.0, -length * 0.5 + 0.03, z_apron), material, "frame"))
    return join_tagged(parts)


register(Category(
    category_id="cabriole_leg_table",
    code="T21",
    family="桌台",
    criterion="S 形弯腿，腿上部有裙板",
    build=build,
    allowed_parts=frozenset({"top", "frame", "leg_base"}),
))

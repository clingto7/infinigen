"""S16 梯背椅。

结构判据：靠背是两根立柱间的多根横档，不是竖条板。
横档沿宽度方向水平排列。立柱标为靠背，横档标为条板。
"""

import procfunc as pf

from infinigen2.objects.chair import chair_seat_dining
from infinigen2.workpieces.assemble import hard_material
from infinigen2.workpieces.c.seating.parts import (
    Category,
    board,
    four_legs,
    join_tagged,
    register,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_base, rng_mat = rng.spawn(3)
    depth = pf.random.uniform(rng_size, 0.46, 0.54)
    width = pf.random.uniform(rng_size, 0.44, 0.52)
    elevation = pf.random.uniform(rng_size, 0.44, 0.50)
    thickness = pf.random.uniform(rng_size, 0.040, 0.052)
    back_h = pf.random.uniform(rng_size, 0.40, 0.52)
    n_rails = pf.control.choice(rng_size, [(3, 1.0), (4, 1.0), (5, 1.0)])
    material = hard_material(rng_mat)
    seat_geo = chair_seat_dining(
        depth=depth,
        half_width=width * 0.5,
        thickness=thickness,
        front_bow=0.03 * depth,
        back_bow=0.0,
        front_dip=0.0,
        material=material,
    ).seat
    seat_geo = pf.nodes.geo.transform(seat_geo, translation=(0.0, 0.0, elevation))
    seat_geo = pf.nodes.geo.store_named_attribute(
        geometry=seat_geo, name="spray_part", value=0, domain="FACE", data_type="INT"
    )
    seat = pf.nodes.to_mesh_object(seat_geo)
    legs = four_legs(rng_base, depth, width, elevation - thickness * 0.5, material)
    stile_h = back_h + 0.03
    stile_z = elevation - 0.02 + stile_h * 0.5
    x = -depth * 0.5 + 0.02
    y_stile = width * 0.5 - 0.035
    parts = [legs, seat]
    for side in (-1.0, 1.0):
        parts.append(board(
            (0.028, 0.028, stile_h),
            (x, side * y_stile, stile_z),
            material, "back",
        ))
    span = y_stile * 2.0 - 0.02
    for index in range(n_rails):
        z = elevation + 0.08 + (back_h - 0.10) * index / (n_rails - 1)
        parts.append(board((0.016, span, 0.022), (x, 0.0, z), material, "slat"))
    return join_tagged(parts)


register(Category(
    category_id="ladder_back_chair",
    code="S16",
    family="坐具",
    criterion="靠背是两根立柱间的多根横档，不是竖条板",
    build=build,
    allowed_parts=frozenset({"seat", "back", "slat", "leg_base"}),
))

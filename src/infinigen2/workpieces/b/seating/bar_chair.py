"""S12 吧椅。

结构判据：带靠背的高脚椅，加脚踏横档。
座高 0.65–0.8 m。条板或实心靠背是构型。前缘不下凹，避免座面中部下沉碰到腿顶。
"""

import procfunc as pf

from infinigen2.objects.chair import (
    _dining_seat_with_back,
    _dining_slat_back,
    _dining_solid_back,
)
from infinigen2.objects import furniture_bases
from infinigen2.util import spray
from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register


def build(rng: pf.RNG) -> pf.MeshObject:
    (
        rng_size,
        rng_style,
        rng_back,
        rng_shape,
        rng_seat,
        rng_base,
        rng_mat,
        rng_foot,
    ) = rng.spawn(8)
    depth = pf.random.uniform(rng_size, 0.40, 0.48)
    width = pf.random.uniform(rng_size, 0.40, 0.48)
    elevation = pf.random.uniform(rng_size, 0.65, 0.80)
    thickness = pf.random.uniform(rng_size, 0.035, 0.055)
    front_bow = pf.random.uniform(rng_shape, 0.0, 0.12) * depth
    back_bow = pf.random.uniform(rng_shape, 0.0, 0.18) * depth
    material = assemble.hard_material(rng_mat)
    back_style = pf.control.choice(rng_style, [("slat", 0.6), ("solid", 0.4)])
    back_fn = {"slat": _dining_slat_back, "solid": _dining_solid_back}[back_style]
    back_height = pf.random.uniform(rng_back, 0.32, 0.48)
    back_sink = thickness * 0.5
    back_built = back_height + back_sink
    back_geo, back_round = back_fn(
        rng_back, width, back_built, material, material
    )
    slant = pf.random.uniform(rng_shape, 0.05, 0.25)
    seat = _dining_seat_with_back(
        rng_seat,
        (depth, width, elevation),
        thickness,
        front_bow,
        back_bow,
        0.0,
        material,
        back_geo,
        back_round,
        back_built,
        back_sink,
        slant,
        0.0,
        spray_tags=True,
    )
    leg_height = elevation - thickness * 0.5
    foot_z = min(pf.random.uniform(rng_foot, 0.18, 0.28), leg_height * 0.45)
    base = furniture_bases.base_straight_rand(
        rng_base,
        dimensions=(depth * 0.84, width * 0.84, leg_height),
        material=material,
        leg_diameter_range=(0.028, 0.042),
        leg_placement_bottom_scale=1.0,
        leg_inset_range=(0.0, 0.0),
        leg_placement_top_scale=1.0,
        stretcher_increment=1,
        stretcher_relative_pos=assemble.stretcher_relative_for_height(leg_height, foot_z),
    ).mesh
    spray.write_spray_part(base, "leg_base")
    return assemble.join_tagged([base, seat])


register(
    Category(
        category_id="bar_chair",
        code="S12",
        family="坐具",
        criterion="带靠背的高脚椅，加脚踏横档",
        build=build,
        allowed_parts=frozenset({"seat", "back", "leg_base"}),
    )
)

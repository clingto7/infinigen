"""S11 吧凳。

结构判据：座高 0.65–0.8 m，腿间有脚踏横档。
圆座或方座是构型。脚踏连接相邻四腿，高度约 0.18–0.28 m。
"""

import procfunc as pf

from infinigen2.objects import chair, furniture_bases
from infinigen2.util import spray
from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register


def _footrest(rng: pf.RNG, leg_height: float) -> float:
    foot_z = pf.random.uniform(rng, 0.18, 0.28)
    return assemble.stretcher_relative_for_height(leg_height, min(foot_z, leg_height * 0.45))


def _square(rng: pf.RNG, seat_height: float, material: pf.Material) -> pf.MeshObject:
    rng_size, rng_base, rng_foot = rng.spawn(3)
    side = pf.random.uniform(rng_size, 0.32, 0.40)
    thickness = pf.random.uniform(rng_size, 0.03, 0.045)
    leg_height = seat_height - thickness
    seat = assemble.tagged_slab((side, side, thickness), material, "seat")
    pf.ops.object.set_transform(seat, location=(0.0, 0.0, leg_height))
    base = furniture_bases.base_straight_rand(
        rng_base,
        dimensions=(side * 0.78, side * 0.78, leg_height),
        material=material,
        leg_diameter_range=(0.028, 0.042),
        leg_placement_bottom_scale=1.0,
        leg_inset_range=(0.0, 0.0),
        leg_placement_top_scale=1.0,
        stretcher_increment=1,
        stretcher_relative_pos=_footrest(rng_foot, leg_height),
    ).mesh
    spray.write_spray_part(base, "leg_base")
    return assemble.join_tagged([base, seat])


def _round(rng: pf.RNG, seat_height: float, material: pf.Material) -> pf.MeshObject:
    rng_size, rng_base, rng_foot = rng.spawn(3)
    # chair_seat_round's radius is the built diameter, and its thickness
    # comes out a little over twice the argument.
    radius = pf.random.uniform(rng_size, 0.32, 0.40)
    thickness = pf.random.uniform(rng_size, 0.022, 0.032)
    seat = chair.chair_seat_round(
        thickness=thickness,
        radius=radius,
        cap_radius=pf.random.uniform(rng_size, 2.2, 3.0),
        bevel_factor=pf.random.uniform(rng_size, 0.008, 0.020),
    ).mesh
    pf.ops.object.set_material(
        seat, surface=material.surface, displacement=material.displacement
    )
    x0, x1, y0, y1, z0, z1 = assemble.vertex_bounds(seat)
    shift = seat_height - z1
    pf.ops.object.set_transform(seat, location=(0.0, 0.0, shift))
    leg_height = z0 + shift
    spray.write_spray_part(seat, "seat")
    footprint = min(x1 - x0, y1 - y0) * 0.72
    base = furniture_bases.base_straight_rand(
        rng_base,
        dimensions=(footprint, footprint, leg_height),
        material=material,
        leg_diameter_range=(0.028, 0.042),
        leg_placement_bottom_scale=1.0,
        leg_inset_range=(0.0, 0.0),
        leg_placement_top_scale=1.0,
        stretcher_increment=1,
        stretcher_relative_pos=_footrest(rng_foot, leg_height),
    ).mesh
    spray.write_spray_part(base, "leg_base")
    return assemble.join_tagged([seat, base])


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_style, rng_height, rng_mat, rng_body = rng.spawn(4)
    seat_height = pf.random.uniform(rng_height, 0.65, 0.80)
    material = assemble.hard_material(rng_mat)
    style = pf.control.choice(rng_style, [("square", 1.0), ("round", 1.0)])
    if style == "square":
        return _square(rng_body, seat_height, material)
    return _round(rng_body, seat_height, material)


register(
    Category(
        category_id="bar_stool",
        code="S11",
        family="坐具",
        criterion="座高 0.65–0.8 m，腿间有脚踏横档",
        build=build,
        allowed_parts=frozenset({"seat", "leg_base"}),
    )
)

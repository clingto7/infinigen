"""T14 双层茶几。

结构判据：腿间多一块下层搁板。
直腿或两端框腿是构型，不用独柱。搁板按脚的落点放大，让内收的腿和两端框都穿过它。
直腿的横档贴在桌面下，不和搁板抢同一高度。
"""

import procfunc as pf

from infinigen2.objects import furniture_bases
from infinigen2.util import spray
from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_mat, rng_base, rng_shelf = rng.spawn(5)
    depth = pf.random.uniform(rng_size, 0.55, 0.80)
    width = pf.random.uniform(rng_size, 0.90, 1.30)
    height = pf.random.uniform(rng_size, 0.38, 0.48)
    thickness = pf.random.uniform(rng_size, 0.025, 0.040)
    leg_height = height - thickness
    material = assemble.hard_material(rng_mat)
    style = pf.control.choice(rng_style, [("straight", 1.0), ("square", 1.0)])
    dimensions = (depth, width, leg_height)
    if style == "straight":
        base = furniture_bases.base_straight_rand(
            rng_base,
            dimensions=dimensions,
            material=material,
            leg_diameter_range=(0.03, 0.06),
            leg_placement_bottom_scale=1.0,
            leg_inset_range=(0.03, 0.06),
            leg_placement_top_scale=0.82,
            stretcher_increment=1,
            stretcher_relative_pos=0.04,
        ).mesh
    else:
        base = furniture_bases.base_square_rand(
            rng_base,
            dimensions=dimensions,
            material=material,
            leg_diameter_range=(0.035, 0.06),
            close_edges=True,
        ).mesh
    spray.write_spray_part(base, "leg_base")
    x0, x1, y0, y1, _z0, _z1 = assemble.vertex_bounds(base)
    # cover the feet so inset legs and end frames both pass through the shelf
    shelf_x = min(depth, (x1 - x0) + 0.04)
    shelf_y = min(width, (y1 - y0) + 0.04)
    top = assemble.tagged_slab((depth, width, thickness), material, "top")
    pf.ops.object.set_transform(top, location=(0.0, 0.0, leg_height))
    shelf_thickness = pf.random.uniform(rng_shelf, 0.016, 0.026)
    shelf = assemble.tagged_slab((shelf_x, shelf_y, shelf_thickness), material, "shelf")
    shelf_z = leg_height * pf.random.uniform(rng_shelf, 0.28, 0.42)
    pf.ops.object.set_transform(shelf, location=(0.0, 0.0, shelf_z))
    return assemble.join_tagged([base, top, shelf])


register(
    Category(
        category_id="two_tier_coffee_table",
        code="T14",
        family="桌台",
        criterion="腿间多一块下层搁板",
        build=build,
        allowed_parts=frozenset({"top", "leg_base", "shelf"}),
    )
)

"""S10 方凳。

结构判据：方形座板加四腿，无靠背。
框式两端腿不是四条独立的腿，这里只用直腿。横档有无是构型。
"""

import procfunc as pf

from infinigen2.objects import furniture_bases
from infinigen2.util import spray
from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat, rng_base = rng.spawn(3)
    side = pf.random.uniform(rng_size, 0.32, 0.42)
    height = pf.random.uniform(rng_size, 0.42, 0.50)
    thickness = pf.random.uniform(rng_size, 0.028, 0.045)
    leg_height = height - thickness
    material = assemble.hard_material(rng_mat)
    seat = assemble.tagged_slab((side, side, thickness), material, "seat")
    pf.ops.object.set_transform(seat, location=(0.0, 0.0, leg_height))
    base = furniture_bases.base_straight_rand(
        rng_base,
        dimensions=(side, side, leg_height),
        material=material,
        leg_diameter_range=(0.028, 0.045),
        leg_placement_bottom_scale=1.0,
        leg_inset_range=(0.02, 0.045),
        leg_placement_top_scale=1.0,
    ).mesh
    spray.write_spray_part(base, "leg_base")
    return assemble.join_tagged([base, seat])


register(
    Category(
        category_id="square_stool",
        code="S10",
        family="坐具",
        criterion="方形座板加四腿，无靠背，与圆凳的座面轮廓不同",
        build=build,
        allowed_parts=frozenset({"seat", "leg_base"}),
    )
)

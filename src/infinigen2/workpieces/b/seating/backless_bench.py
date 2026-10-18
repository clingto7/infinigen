"""S13 无靠背长凳。

结构判据：长座板加两端框腿，无靠背。
框腿沿长度方向分在两端。框底有无横档是构型。
"""

import procfunc as pf

from infinigen2.objects import furniture_bases
from infinigen2.util import spray
from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat, rng_base = rng.spawn(3)
    length = pf.random.uniform(rng_size, 1.00, 1.80)
    depth = pf.random.uniform(rng_size, 0.32, 0.42)
    height = pf.random.uniform(rng_size, 0.42, 0.48)
    thickness = pf.random.uniform(rng_size, 0.03, 0.045)
    leg_height = height - thickness
    material = assemble.hard_material(rng_mat)
    seat = assemble.tagged_slab((length, depth, thickness), material, "seat")
    pf.ops.object.set_transform(seat, location=(0.0, 0.0, leg_height))
    # box frames separate along local X, which is the bench length here
    base = furniture_bases.base_square_rand(
        rng_base,
        dimensions=(length * 0.94, depth * 0.88, leg_height),
        material=material,
        leg_diameter_range=(0.035, 0.055),
        close_edges=True,
    ).mesh
    spray.write_spray_part(base, "leg_base")
    return assemble.join_tagged([base, seat])


register(
    Category(
        category_id="backless_bench",
        code="S13",
        family="坐具",
        criterion="长座板加两端框腿，无靠背",
        build=build,
        allowed_parts=frozenset({"seat", "leg_base"}),
    )
)

"""T11 带书架书桌。

结构判据：桌面后方立起一组开敞格架。
格架背板可有可无。格数是构型。格架深度小于桌深，正面朝使用者。
"""

import procfunc as pf

from infinigen2.objects import desk, storage
from infinigen2.util import spray
from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register

_SHELF_PARTS = {0: "carcass", 1: "back_panel", 2: "shelf", 3: "shelf"}


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_desk, rng_hutch, rng_count = rng.spawn(3)
    body = desk.desk_tabletop_rand(rng_desk, spray_tags=True, shared_parts=True).mesh
    x0, x1, y0, y1, _z0, z1 = assemble.vertex_bounds(body)
    desk_depth = x1 - x0
    desk_width = y1 - y0
    hutch_depth = min(pf.random.uniform(rng_hutch, 0.18, 0.26), desk_depth * 0.42)
    hutch_depth = max(hutch_depth, 0.16)
    hutch_width = desk_width * pf.random.uniform(rng_hutch, 0.86, 0.96)
    hutch_height = pf.random.uniform(rng_hutch, 0.36, 0.58)
    n_spaces_y = pf.control.choice(rng_count, [(2, 1.0), (3, 1.0), (4, 1.0)])
    n_spaces_z = pf.control.choice(rng_count, [(1, 1.0), (2, 1.0)])
    hutch = storage.storage_cell_shelf_rand(
        rng_hutch,
        dimensions=(hutch_depth, hutch_width, hutch_height),
        n_spaces_y=n_spaces_y,
        n_spaces_z=n_spaces_z,
        spray_tags=True,
    ).mesh
    spray.remap_spray_part(hutch, _SHELF_PARTS)
    # shelf origin is its min corner; min X of the desk is the rear edge
    pf.ops.object.set_transform(
        hutch, location=(x0, -hutch_width / 2.0, z1)
    )
    return assemble.join_tagged([body, hutch])


register(
    Category(
        category_id="desk_with_hutch",
        code="T11",
        family="桌台",
        criterion="桌面后方立起一组开敞格架",
        build=build,
        allowed_parts=frozenset({"top", "leg_base", "carcass", "back_panel", "shelf"}),
    )
)

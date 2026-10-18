"""C12 带门书柜。

结构判据：上部开敞书架，下部门柜。
上下同深同宽。格数、单扇或双开门是构型。
"""

import procfunc as pf

from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_count, rng_base, rng_shelf = rng.spawn(4)
    depth = pf.random.uniform(rng_size, 0.28, 0.38)
    width = pf.random.uniform(rng_size, 0.75, 1.10)
    base_h = pf.random.uniform(rng_size, 0.70, 0.90)
    shelf_h = pf.random.uniform(rng_size, 0.75, 1.05)
    n_y = int(pf.control.choice(rng_count, [(2, 1.0), (3, 1.0)]))
    n_z = int(pf.control.choice(rng_count, [(2, 1.0), (3, 1.0)]))
    base = assemble.fronted_bay(
        rng_base, (depth, width, base_h), "door", n_spaces_y=1
    )
    shelf = assemble.open_bay(rng_shelf, (depth, width, shelf_h), n_y, n_z)
    return assemble.place_stack(base, shelf, base_h)


register(
    Category(
        category_id="bookcase_with_doors",
        code="C12",
        family="柜架",
        criterion="上部开敞书架，下部门柜",
        build=build,
        allowed_parts=frozenset(
            {
                "carcass",
                "shelf",
                "back_panel",
                "door_frame",
                "door_panel",
                "handle",
            }
        ),
    )
)

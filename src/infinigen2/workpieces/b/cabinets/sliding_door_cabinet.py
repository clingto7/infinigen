"""C14 推拉门柜。

结构判据：两扇门前后错开，在轨道上滑动，部分重叠。
柜体是开敞格。两扇门都宽过一半，前后相差一个门厚，中间互相遮挡。
"""

import procfunc as pf

from infinigen2.objects import door, handles
from infinigen2.util import spray
from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register

_DOOR_PARTS = {0: "door_frame", 1: "door_panel"}


def _leaf(
    rng: pf.RNG,
    thickness: float,
    width: float,
    height: float,
    origin: tuple[float, float, float],
) -> pf.MeshObject:
    rng_door, rng_handle = rng.spawn(2)
    leaf = door.door_body_rand(
        rng_door,
        dimensions=pf.Vector((thickness, width, height)),
        spray_tags=True,
    ).mesh
    spray.remap_spray_part(leaf, _DOOR_PARTS)
    pf.ops.object.set_transform(leaf, location=origin)
    pull = handles.handle_bar_pull_rand(rng_handle, grip_length=0.10).mesh
    spray.write_spray_part(pull, "handle")
    # mount on the inner stile, just proud of the door face
    pf.ops.object.set_transform(
        pull,
        location=(origin[0] + thickness, origin[1] + width * 0.5, height * 0.5),
    )
    return assemble.join_tagged([leaf, pull])


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_carcass, rng_left, rng_right = rng.spawn(4)
    width = pf.random.uniform(rng_size, 0.90, 1.40)
    height = pf.random.uniform(rng_size, 0.70, 1.05)
    door_t = 0.018
    gap = 0.006
    carcass_depth = pf.random.uniform(rng_size, 0.32, 0.42)
    leaf_w = width * pf.random.uniform(rng_size, 0.56, 0.64)
    carcass = assemble.open_bay(rng_carcass, (carcass_depth, width, height), n_spaces_y=2, n_spaces_z=2)
    left = _leaf(rng_left, door_t, leaf_w, height, (carcass_depth, 0.0, 0.0))
    right = _leaf(
        rng_right,
        door_t,
        leaf_w,
        height,
        (carcass_depth + door_t + gap, width - leaf_w, 0.0),
    )
    return assemble.join_tagged([carcass, left, right])


register(
    Category(
        category_id="sliding_door_cabinet",
        code="C14",
        family="柜架",
        criterion="两扇门前后错开，在轨道上滑动，部分重叠",
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

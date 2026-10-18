"""O01 屏风。

结构判据：三到四扇框板铰接，呈折线放置。
扇数是构型。每扇是一块门芯框板，绕竖边交替折叠。
"""

import math

import procfunc as pf

from infinigen2.objects import door
from infinigen2.util import spray
from infinigen2.workpieces.c.other.parts import Category, join_tagged, register


def _leaf(rng: pf.RNG, thickness: float, width: float, height: float) -> pf.MeshObject:
    leaf = door.door_body_rand(
        rng,
        dimensions=pf.Vector((thickness, width, height)),
        spray_tags=True,
    ).mesh
    spray.remap_spray_part(leaf, {0: "door_frame", 1: "door_panel"})
    return leaf


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_doors = rng.spawn(2)
    count = int(pf.control.choice(rng_size, [(3, 1.0), (4, 1.0)]))
    width = pf.random.uniform(rng_size, 0.42, 0.52)
    height = pf.random.uniform(rng_size, 1.60, 1.80)
    angle = pf.random.uniform(rng_size, 0.35, 0.55)
    thickness = 0.020
    hinge = (0.0, 0.0)
    parts = []
    for index, leaf_rng in enumerate(rng_doors.spawn(count)):
        theta = angle if index % 2 == 0 else -angle
        leaf = _leaf(leaf_rng, thickness, width, height)
        pf.ops.object.set_transform(
            leaf, location=(hinge[0], hinge[1], 0.0), rotation_euler=(0.0, 0.0, theta)
        )
        parts.append(leaf)
        hinge = (
            hinge[0] - width * math.sin(theta),
            hinge[1] + width * math.cos(theta),
        )
    return join_tagged(parts)


register(Category(
    category_id="folding_screen",
    code="O01",
    family="其他家具",
    criterion="三到四扇框板铰接，呈折线放置",
    build=build,
    allowed_parts=frozenset({"door_frame", "door_panel"}),
))

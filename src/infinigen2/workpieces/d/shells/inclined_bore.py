"""G08 斜贯穿孔厚块。

厚板被绕 Y 轴倾斜的圆柱打穿。倾角从板法向算起，孔心可在板面内偏移，
两端开口因此错开。浅槽是可选构型，只开在顶面，不打穿。
"""

import math

import procfunc as pf

from infinigen2.workpieces.d.shells.parts import (
    Category,
    box,
    cut,
    cylinder,
    finish,
    hard_material,
    register,
    rest_on_ground,
    tag,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_mat = rng.spawn(3)
    length = pf.random.uniform(rng_size, 0.36, 0.56)
    width = pf.random.uniform(rng_size, 0.24, 0.40)
    thick = pf.random.uniform(rng_size, 0.09, 0.15)
    radius = pf.random.uniform(rng_size, 0.030, 0.052)
    theta = math.radians(pf.random.uniform(rng_size, 14.0, 36.0))
    if pf.control.choice(rng_style, [(False, 1.0), (True, 1.0)]):
        theta = -theta
    margin = 0.022
    shift = abs(math.tan(theta)) * thick * 0.5
    room_x = length * 0.5 - radius - shift - margin
    room_y = width * 0.5 - radius - margin
    offset_x = pf.random.uniform(rng_size, -1.0, 1.0) * max(room_x, 0.0)
    offset_y = pf.random.uniform(rng_size, -1.0, 1.0) * max(room_y, 0.0)

    shell = box((length, width, thick), (0.0, 0.0, thick * 0.5))
    cut(
        shell,
        cylinder(
            radius,
            thick / math.cos(theta) + 0.12,
            center=(offset_x, offset_y, thick * 0.5),
            rotation=(0.0, theta, 0.0),
            vertices=40,
        ),
        what="inclined bore",
    )
    if pf.control.choice(rng_style, [(False, 1.0), (True, 1.0)]):
        slot_w = pf.random.uniform(rng_style, 0.045, 0.080)
        slot_d = pf.random.uniform(rng_style, 0.012, min(0.028, thick * 0.28))
        slot_l = width * pf.random.uniform(rng_style, 0.55, 0.82)
        top_x = offset_x + math.tan(theta) * thick * 0.5
        slot_x = -math.copysign(length * 0.30, top_x if top_x != 0.0 else 1.0)
        slot_x = max(-(length * 0.5 - slot_w * 0.5 - 0.012), min(slot_x, length * 0.5 - slot_w * 0.5 - 0.012))
        cut(
            shell,
            box(
                (slot_w, slot_l, slot_d + 0.02),
                (slot_x, 0.0, thick - slot_d * 0.5 + 0.01),
            ),
            what="shallow slot",
        )
    return rest_on_ground(finish([tag(shell, hard_material(rng_mat), "shell")]))


register(Category(
    category_id="inclined_bore",
    code="G08",
    family="壳体",
    criterion="厚板有倾斜贯穿圆孔，可在顶面加一条浅槽",
    build=build,
    allowed_parts=frozenset({"shell"}),
))

"""G11 缺口环形法兰。

扁圆柱减去中心孔，再减去一段扇区，环上留下断口。
凸缘贴在外圆、位于缺口对面，比环更厚，并随缺口一起转动。
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
    pose,
    register,
    rest_on_ground,
    tag,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    outer = pf.random.uniform(rng_size, 0.15, 0.26)
    inner = outer * pf.random.uniform(rng_size, 0.40, 0.66)
    thick = pf.random.uniform(rng_size, 0.018, 0.038)
    notch = math.radians(pf.random.uniform(rng_size, 34.0, 100.0))
    yaw = pf.random.uniform(rng_size, 0.0, 2.0 * math.pi)
    lip_w = pf.random.uniform(rng_size, 0.014, 0.032)
    lip_span = outer * pf.random.uniform(rng_size, 0.42, 0.85)

    ring = cylinder(outer, thick, center=(0.0, 0.0, thick * 0.5), vertices=64)
    cut(
        ring,
        cylinder(inner, thick + 0.04, center=(0.0, 0.0, thick * 0.5), vertices=48),
        what="flange bore",
    )
    half = notch * 0.5
    # Parallel sides through the rim chord of this angle. The inner face sits
    # inside the bore so the notch breaks the ring.
    x0 = inner * math.cos(half) - 0.012
    x1 = outer + 0.03
    cut(
        ring,
        box(
            (x1 - x0, 2.0 * outer * math.sin(half), thick + 0.04),
            ((x0 + x1) * 0.5, 0.0, thick * 0.5),
        ),
        what="sector notch",
    )
    material = hard_material(rng_mat)
    lip = box(
        (lip_w, lip_span, thick * 1.65),
        (-(outer + lip_w * 0.15), 0.0, thick * 0.5),
    )
    body = finish([tag(ring, material, "shell"), tag(lip, material, "flange")])
    return rest_on_ground(pose(body, rotation=(0.0, 0.0, yaw)))


register(Category(
    category_id="notched_flange",
    code="G11",
    family="壳体",
    criterion="带中心孔的扁环切去一段扇区，缺口对面有局部凸缘",
    build=build,
    allowed_parts=frozenset({"shell", "flange"}),
))

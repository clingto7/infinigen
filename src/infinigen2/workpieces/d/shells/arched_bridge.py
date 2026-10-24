"""G07 拱洞桥块。

厚块沿厚度方向减去横向圆柱。圆柱与底面交出洞宽，冠部高度是洞高，
两侧留下桥墩。拱可以沿跨度偏移。顶脊是可选构型。
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

_ALONG_Y = (math.pi / 2.0, 0.0, 0.0)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_mat = rng.spawn(3)
    hole_w = pf.random.uniform(rng_size, 0.20, 0.36)
    hole_h = pf.random.uniform(rng_size, 0.11, 0.22)
    pier = pf.random.uniform(rng_size, 0.045, 0.075)
    thickness = pf.random.uniform(rng_size, 0.16, 0.34)
    slab = pf.random.uniform(rng_size, 0.040, 0.080)
    # Keep a pier on both sides after the arch shifts along the span.
    offset = pf.random.uniform(rng_size, -0.45, 0.45) * pier
    width = hole_w + 2.0 * pier
    height = hole_h + slab
    radius = (hole_h ** 2 + (hole_w * 0.5) ** 2) / (2.0 * hole_h)
    center_z = hole_h - radius

    shell = box((width, thickness, height), (0.0, 0.0, height * 0.5))
    cut(
        shell,
        cylinder(
            radius,
            thickness + 0.08,
            center=(offset, 0.0, center_z),
            rotation=_ALONG_Y,
            vertices=48,
        ),
        what="arch tunnel",
    )
    material = hard_material(rng_mat)
    parts = [tag(shell, material, "shell")]
    if pf.control.choice(rng_style, [(False, 1.0), (True, 1.4)]):
        ridge_h = pf.random.uniform(rng_style, 0.018, 0.040)
        ridge_t = pf.random.uniform(rng_style, 0.045, 0.090)
        ridge_w = width * pf.random.uniform(rng_style, 0.55, 0.88)
        parts.append(tag(
            box(
                (ridge_w, ridge_t, ridge_h),
                (offset * 0.3, 0.0, height + ridge_h * 0.5 - 0.003),
            ),
            material,
            "rib",
        ))
    return rest_on_ground(finish(parts))


register(Category(
    category_id="arched_bridge",
    code="G07",
    family="壳体",
    criterion="厚块底部为宽拱洞，两侧留桥墩，可加顶脊",
    build=build,
    allowed_parts=frozenset({"shell", "rib"}),
))

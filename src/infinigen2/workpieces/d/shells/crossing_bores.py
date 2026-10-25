"""G09 正交双孔块。

厚块减去两根大圆柱。第一根沿厚度的 Y 向，第二根在水平面内与它成
70 到 110 度。轴线可错开，但两孔在块内互相切入。
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
    rng_size, rng_mat = rng.spawn(2)
    span_x = pf.random.uniform(rng_size, 0.34, 0.50)
    span_y = pf.random.uniform(rng_size, 0.34, 0.50)
    span_z = pf.random.uniform(rng_size, 0.28, 0.42)
    wall = 0.030
    r1 = pf.random.uniform(rng_size, 0.055, min(span_x, span_z) * 0.5 - wall)
    r2 = pf.random.uniform(rng_size, 0.050, min(span_y, span_z) * 0.5 - wall)
    phi = math.radians(pf.random.uniform(rng_size, 70.0, 110.0))
    alpha = math.asin(max(-1.0, min(1.0, -math.cos(phi))))
    skew_cap = min(0.40 * (r1 + r2), span_z * 0.5 - max(r1, r2) - 0.018)
    skew = pf.random.uniform(rng_size, -1.0, 1.0) * max(skew_cap, 0.0)
    offset_x = pf.random.uniform(rng_size, -0.12, 0.12) * span_x
    offset_y = pf.random.uniform(rng_size, -0.12, 0.12) * span_y
    center_z = span_z * 0.5

    shell = box((span_x, span_y, span_z), (0.0, 0.0, center_z))
    cut(
        shell,
        cylinder(
            r1,
            span_y + 0.10,
            center=(offset_x, 0.0, center_z),
            rotation=_ALONG_Y,
            vertices=40,
        ),
        what="bore along y",
    )
    cut(
        shell,
        cylinder(
            r2,
            span_x / max(abs(math.cos(alpha)), 0.50) + 0.12,
            center=(0.0, offset_y, center_z + skew),
            rotation=(0.0, math.pi / 2.0, alpha),
            vertices=40,
        ),
        what="crossing bore",
    )
    return rest_on_ground(finish([tag(shell, hard_material(rng_mat), "shell")]))


register(Category(
    category_id="crossing_bores",
    code="G09",
    family="壳体",
    criterion="厚块内两根大圆孔斜交或正交，并在块内交汇",
    build=build,
    allowed_parts=frozenset({"shell"}),
))

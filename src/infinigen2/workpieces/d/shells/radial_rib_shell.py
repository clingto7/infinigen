"""G20 辐射肋圆筒壳。

短粗圆筒挖空，底面留壁厚，顶面大口敞开。外壁均布 4 到 8 条径向厚肋。
端环是构型，贴在顶口外沿。
"""

import math

import procfunc as pf

from infinigen2.workpieces.d.shells.parts import (
    Category,
    box,
    cut,
    cylinder,
    finish,
    flange_ring,
    hard_material,
    register,
    rest_on_ground,
    tag,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_mat = rng.spawn(3)
    outer_r = pf.random.uniform(rng_size, 0.10, 0.16)
    inner_r = outer_r * pf.random.uniform(rng_size, 0.55, 0.75)
    height = pf.random.uniform(rng_size, 0.12, 0.22)
    floor = pf.random.uniform(rng_size, 0.016, 0.028)
    n_rib = int(pf.random.randint(rng_size, 4, 9))
    rib_t = pf.random.uniform(rng_size, 0.016, 0.032)
    rib_h = pf.random.uniform(rng_size, 0.022, 0.045)
    rib_z0 = height * pf.random.uniform(rng_size, 0.04, 0.16)
    rib_z1 = height * pf.random.uniform(rng_size, 0.82, 0.98)
    yaw0 = pf.random.uniform(rng_style, 0.0, 2.0 * math.pi / n_rib)
    with_ring = pf.control.choice(rng_style, [(False, 1.0), (True, 1.2)])
    ring_w = min(pf.random.uniform(rng_style, 0.012, 0.024), (outer_r - inner_r) * 0.9)

    shell = cylinder(outer_r, height, (0.0, 0.0, height * 0.5), vertices=48)
    cut(
        shell,
        cylinder(
            inner_r,
            height - floor + 0.04,
            (0.0, 0.0, floor + (height - floor + 0.04) * 0.5),
            vertices=40,
        ),
        what="shell bore",
    )
    material = hard_material(rng_mat)
    parts = [tag(shell, material, "shell")]
    rib_len = rib_h + 0.008
    rib_span = rib_z1 - rib_z0
    for index in range(n_rib):
        yaw = yaw0 + index * (2.0 * math.pi / n_rib)
        center_r = outer_r + rib_h * 0.5 - 0.004
        parts.append(tag(
            box(
                (rib_len, rib_t, rib_span),
                (math.cos(yaw) * center_r, math.sin(yaw) * center_r, rib_z0 + rib_span * 0.5),
                rotation=(0.0, 0.0, yaw),
            ),
            material,
            "rib",
        ))
    if with_ring:
        thick = 0.010
        parts.append(tag(
            flange_ring(
                outer_r + 0.004,
                inner_r,
                thick,
                (0.0, 0.0, height + thick * 0.5 - 0.002),
            ),
            material,
            "flange",
        ))
    return rest_on_ground(finish(parts))


register(Category(
    category_id="radial_rib_shell",
    code="G20",
    family="壳体",
    criterion="短粗圆筒顶面大口，外壁有径向厚肋，可加顶环",
    build=build,
    allowed_parts=frozenset({"shell", "rib", "flange"}),
))

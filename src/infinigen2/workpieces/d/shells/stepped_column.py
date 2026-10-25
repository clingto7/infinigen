"""G23 偏心阶梯柱座。

2 到 4 层半径递减的圆柱错位堆叠并集。侧面切掉一段扇区或一条竖槽，
让台阶在缺口处断开。
"""

import math

import procfunc as pf

from infinigen2.workpieces.d.shells.parts import (
    Category,
    box,
    cut,
    cylinder,
    finish,
    fuse,
    hard_material,
    pose,
    register,
    rest_on_ground,
    tag,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_mat = rng.spawn(3)
    layers = int(pf.random.randint(rng_size, 2, 5))
    r0 = pf.random.uniform(rng_size, 0.090, 0.140)
    shrink = pf.random.uniform(rng_size, 0.72, 0.86)
    step_h = pf.random.uniform(rng_size, 0.045, 0.080)
    notch = math.radians(pf.random.uniform(rng_size, 40.0, 95.0))
    yaw = pf.random.uniform(rng_style, 0.0, 2.0 * math.pi)
    slot = pf.control.choice(rng_style, [(False, 1.0), (True, 1.0)])

    radii = [r0 * (shrink ** index) for index in range(layers)]
    heights = [step_h * pf.random.uniform(rng_size, 0.85, 1.15) for _ in range(layers)]
    z = 0.0
    offsets = [(0.0, 0.0)]
    for index in range(1, layers):
        ecc = pf.random.uniform(rng_size, 0.35, 0.85) * (radii[index - 1] - radii[index])
        ang = pf.random.uniform(rng_size, 0.0, 2.0 * math.pi)
        offsets.append((offsets[index - 1][0] + ecc * math.cos(ang), offsets[index - 1][1] + ecc * math.sin(ang)))

    shell = cylinder(radii[0], heights[0], (*offsets[0], heights[0] * 0.5), vertices=40)
    z = heights[0]
    for index in range(1, layers):
        fuse(
            shell,
            cylinder(
                radii[index],
                heights[index],
                (*offsets[index], z + heights[index] * 0.5),
                vertices=36,
            ),
            what="column step",
        )
        z += heights[index]
    total_h = z
    if slot:
        cut(
            shell,
            box(
                (radii[0] + 0.04, max(0.028, radii[-1] * 0.45), total_h + 0.04),
                (radii[0] * 0.55, 0.0, total_h * 0.5),
            ),
            what="column slot",
        )
    else:
        half = notch * 0.5
        x0 = radii[-1] * math.cos(half) - 0.01
        x1 = radii[0] + 0.04
        cut(
            shell,
            box(
                (x1 - x0, 2.0 * radii[0] * math.sin(half), total_h + 0.04),
                ((x0 + x1) * 0.5, 0.0, total_h * 0.5),
            ),
            what="column sector",
        )
    body = finish([tag(shell, hard_material(rng_mat), "shell")])
    return rest_on_ground(pose(body, rotation=(0.0, 0.0, yaw)))


register(Category(
    category_id="stepped_column",
    code="G23",
    family="壳体",
    criterion="多层偏心圆柱堆叠，侧面有扇形缺口或竖槽",
    build=build,
    allowed_parts=frozenset({"shell"}),
))

"""G04 阶梯凹腔箱体。

盒体从顶面向下连续减去两到三层嵌套方腔。
外层腔口大而浅，内层更小更深，底面留出壁厚。
腔口相对盒心可偏，偏置量不超过两侧多出来的壁厚。
"""

import procfunc as pf

from infinigen2.workpieces.d.shells.parts import (
    Category,
    box,
    cut,
    finish,
    hard_material,
    register,
    rest_on_ground,
    tag,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    steps = pf.random.randint(rng_size, 2, 4)
    mouth_x = pf.random.uniform(rng_size, 0.16, 0.28)
    mouth_y = pf.random.uniform(rng_size, 0.20, 0.36)
    step_depth = pf.random.uniform(rng_size, 0.030, 0.052)
    wall = pf.random.uniform(rng_size, 0.016, 0.030)
    floor = pf.random.uniform(rng_size, 0.016, 0.028)
    lip = min(
        pf.random.uniform(rng_size, 0.014, 0.026),
        min(mouth_x, mouth_y) / (2.0 * steps + 2.0),
    )
    extra_x = pf.random.uniform(rng_size, 0.02, 0.06)
    extra_y = pf.random.uniform(rng_size, 0.02, 0.06)
    offset_x = pf.random.uniform(rng_size, -extra_x * 0.5, extra_x * 0.5)
    offset_y = pf.random.uniform(rng_size, -extra_y * 0.5, extra_y * 0.5)
    material = hard_material(rng_mat)

    height = steps * step_depth + floor
    shell = box(
        (mouth_x + 2.0 * wall + extra_x, mouth_y + 2.0 * wall + extra_y, height),
        (0.0, 0.0, height * 0.5),
    )
    for index in range(steps):
        depth = (index + 1) * step_depth
        span_x = mouth_x - 2.0 * index * lip
        span_y = mouth_y - 2.0 * index * lip
        top = height + 0.02
        bottom = height - depth
        cutter = box(
            (span_x, span_y, top - bottom),
            (offset_x, offset_y, (top + bottom) * 0.5),
        )
        cut(shell, cutter, what=f"cavity step {index + 1}")
    return rest_on_ground(finish([tag(shell, material, "shell")]))


register(Category(
    category_id="stepped_cavity",
    code="G04",
    family="壳体",
    criterion="顶面多层台阶凹腔，腔口可偏，底面留壁厚",
    build=build,
    allowed_parts=frozenset({"shell"}),
))

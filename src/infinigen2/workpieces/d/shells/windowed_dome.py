"""G27 开窗穹顶防护罩。

外球减内球再裁平底面，得到开底的球冠壳。侧面开 1 到 3 个宽窗，
底边加一圈加强环。窗口停在轴线一侧，保留拱顶。
"""

import math

import procfunc as pf

from infinigen2.workpieces.d.shells.parts import (
    Category,
    box,
    cut,
    finish,
    flange_ring,
    hard_material,
    register,
    rest_on_ground,
    sphere,
    tag,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_mat = rng.spawn(3)
    outer_r = pf.random.uniform(rng_size, 0.18, 0.26)
    cap_h = outer_r * pf.random.uniform(rng_size, 0.62, 0.98)
    wall = min(pf.random.uniform(rng_size, 0.012, 0.022), outer_r * 0.14)
    inner_r = outer_r - wall
    n_win = int(pf.random.randint(rng_size, 1, 4))
    yaw0 = pf.random.uniform(rng_style, 0.0, 2.0 * math.pi)
    ring_t = pf.random.uniform(rng_size, 0.010, 0.018)
    ring_w = pf.random.uniform(rng_size, 0.012, 0.024)

    cz = cap_h - outer_r
    shell = sphere((outer_r, outer_r, outer_r), (0.0, 0.0, cz), segments=40, rings=20)
    cut(
        shell,
        sphere((inner_r, inner_r, inner_r), (0.0, 0.0, cz), segments=32, rings=16),
        what="dome cavity",
    )
    cut(
        shell,
        box((outer_r * 2.4, outer_r * 2.4, outer_r * 2.0), (0.0, 0.0, -outer_r)),
        what="dome floor",
    )

    if n_win == 1:
        opening = math.radians(pf.random.uniform(rng_size, 48.0, 100.0))
    elif n_win == 2:
        opening = math.radians(pf.random.uniform(rng_size, 36.0, 58.0))
    else:
        opening = math.radians(pf.random.uniform(rng_size, 28.0, 44.0))
    win_h = cap_h * pf.random.uniform(rng_size, 0.34, 0.58)
    r_open = math.sqrt(max(outer_r * outer_r - cz * cz, 1e-4))
    for index in range(n_win):
        yaw = yaw0 + index * (2.0 * math.pi / n_win)
        half_chord = outer_r * math.sin(opening * 0.5)
        outer_end = outer_r + 0.03
        inner_end = max(inner_r * 0.40, 0.016)
        center_r = (outer_end + inner_end) * 0.5
        center_z = min(max(cap_h * 0.42, win_h * 0.5 + 0.012), cap_h - 0.02 - win_h * 0.5)
        cut(
            shell,
            box(
                (outer_end - inner_end, max(2.0 * half_chord, 0.02), win_h),
                (math.cos(yaw) * center_r, math.sin(yaw) * center_r, center_z),
                rotation=(0.0, 0.0, yaw),
            ),
            what="dome window",
        )

    material = hard_material(rng_mat)
    parts = [tag(shell, material, "shell")]
    parts.append(tag(
        flange_ring(r_open + 0.006, max(0.02, r_open - ring_w), ring_t, (0.0, 0.0, ring_t * 0.35)),
        material,
        "flange",
    ))
    return rest_on_ground(finish(parts))


register(Category(
    category_id="windowed_dome",
    code="G27",
    family="壳体",
    criterion="开底球冠壳，侧面有宽窗，底边有加强环",
    build=build,
    allowed_parts=frozenset({"shell", "flange"}),
))

"""G25 双腔连通鼓形壳。

两个椭球鼓沿腰管相连。两端从外侧挖大凹口，再用短于外壳的内孔
把两腔打通，内孔停在鼓内，不把远端壁打穿。
"""

import math

import procfunc as pf

from infinigen2.workpieces.d.shells.parts import (
    Category,
    aim_z,
    cut,
    cylinder,
    finish,
    fuse,
    hard_material,
    register,
    rest_on_ground,
    sphere,
    tag,
)


def _unit(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_mat = rng.spawn(3)
    rx_a = pf.random.uniform(rng_size, 0.090, 0.130)
    ry_a = rx_a * pf.random.uniform(rng_size, 0.72, 0.95)
    rz_a = rx_a * pf.random.uniform(rng_size, 0.78, 1.05)
    scale_b = pf.random.uniform(rng_size, 0.78, 1.12)
    rx_b = rx_a * scale_b
    ry_b = ry_a * pf.random.uniform(rng_size, 0.88, 1.08)
    rz_b = rz_a * pf.random.uniform(rng_size, 0.88, 1.08)
    sep = (rx_a + rx_b) * pf.random.uniform(rng_size, 0.92, 1.08)
    r_neck = min(ry_a, ry_b, rz_a, rz_b) * pf.random.uniform(rng_size, 0.42, 0.58)
    wall = min(0.016, r_neck * 0.28)
    mouth_a = rx_a * pf.random.uniform(rng_size, 0.62, 0.82)
    mouth_b = rx_b * pf.random.uniform(rng_size, 0.62, 0.82)
    yaw = math.radians(pf.random.uniform(rng_style, -22.0, 22.0))

    center_a = (-sep * 0.5, 0.0, rz_a)
    center_b = (sep * 0.5 * math.cos(yaw), sep * 0.5 * math.sin(yaw), rz_b)
    axis = _unit((
        center_b[0] - center_a[0],
        center_b[1] - center_a[1],
        center_b[2] - center_a[2],
    ))
    mid = (
        (center_a[0] + center_b[0]) * 0.5,
        (center_a[1] + center_b[1]) * 0.5,
        (center_a[2] + center_b[2]) * 0.5,
    )
    span = math.sqrt(sum((center_b[i] - center_a[i]) ** 2 for i in range(3)))
    neck_len = span + min(rx_a, rx_b) * 0.55

    shell = sphere((rx_a, ry_a, rz_a), center_a, segments=32, rings=16)
    fuse(shell, sphere((rx_b, ry_b, rz_b), center_b, segments=32, rings=16), what="second drum")
    fuse(
        shell,
        cylinder(r_neck, neck_len, mid, rotation=aim_z(axis), vertices=28),
        what="neck",
    )
    out_a = (-axis[0], -axis[1], -axis[2])
    cut(
        shell,
        sphere(
            (mouth_a, mouth_a, mouth_a * 0.90),
            (
                center_a[0] + out_a[0] * rx_a * 0.58,
                center_a[1] + out_a[1] * rx_a * 0.58,
                center_a[2] + out_a[2] * rx_a * 0.20,
            ),
        ),
        what="drum mouth a",
    )
    cut(
        shell,
        sphere(
            (mouth_b, mouth_b, mouth_b * 0.90),
            (
                center_b[0] + axis[0] * rx_b * 0.58,
                center_b[1] + axis[1] * rx_b * 0.58,
                center_b[2] + axis[2] * rx_b * 0.20,
            ),
        ),
        what="drum mouth b",
    )
    bore_len = max(0.06, span - rx_a * 0.20 - rx_b * 0.20)
    cut(
        shell,
        cylinder(max(0.012, r_neck - wall), bore_len, mid, rotation=aim_z(axis), vertices=24),
        what="neck bore",
    )
    return rest_on_ground(finish([tag(shell, hard_material(rng_mat), "shell")]))


register(Category(
    category_id="connected_drums",
    code="G25",
    family="壳体",
    criterion="两个鼓形腔由短粗管连通，两端各有大凹口",
    build=build,
    allowed_parts=frozenset({"shell"}),
))

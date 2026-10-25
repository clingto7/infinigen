"""G01 偏心月牙圆筒。

大圆柱减去偏心内圆柱，再沿薄壁一侧用裁切盒打开一个轴向缺口。
薄壁厚度把内孔压在外壳之内，缺口才是开口。端面盘是构型。
开口朝向绕 Z 转动。坐标：Z 为筒轴，底面在 z = 0。
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
    rng_size, rng_style, rng_mat = rng.spawn(3)
    radius = pf.random.uniform(rng_size, 0.14, 0.22)
    height = pf.random.uniform(rng_size, 0.20, 0.46)
    ratio = pf.random.uniform(rng_size, 1.35, 1.85)
    opening = math.radians(pf.random.uniform(rng_size, 36.0, 100.0))
    wall = pf.random.uniform(rng_size, 0.010, 0.024)
    disc = pf.control.choice(rng_style, [(False, 1.0), (True, 1.0)])
    material = hard_material(rng_mat)

    cut_r = radius / ratio
    eccentricity = radius - cut_r - wall
    if eccentricity < 0.012:
        cut_r = radius - wall - 0.012
        eccentricity = 0.012

    z0 = 0.0
    parts = []
    if disc:
        plate_t = max(wall, 0.012)
        plate = cylinder(radius * 1.05, plate_t, center=(0.0, 0.0, plate_t * 0.5))
        parts.append(tag(plate, material, "flange"))
        z0 = plate_t - 0.001

    shell = cylinder(radius, height, center=(0.0, 0.0, z0 + height * 0.5), vertices=56)
    bore = cylinder(
        cut_r,
        height + 0.04,
        center=(eccentricity, 0.0, z0 + height * 0.5),
        vertices=48,
    )
    cut(shell, bore, what="eccentric bore")

    chord = min(2.0 * radius * math.sin(opening * 0.5), radius * 1.85)
    mouth_inner = eccentricity + cut_r - 0.008
    mouth_outer = radius + 0.03
    notch = box(
        (mouth_outer - mouth_inner, max(chord, 0.02), height + 0.08),
        ((mouth_outer + mouth_inner) * 0.5, 0.0, z0 + height * 0.5),
    )
    cut(shell, notch, what="axial mouth")
    parts.insert(0, tag(shell, material, "shell"))
    yaw = pf.random.uniform(rng_style, 0.0, 2.0 * math.pi)
    return rest_on_ground(pose(finish(parts), rotation=(0.0, 0.0, yaw)))


register(Category(
    category_id="eccentric_crescent",
    code="G01",
    family="壳体",
    criterion="偏心内孔的圆筒，薄壁一侧有轴向开口，可带端面盘",
    build=build,
    allowed_parts=frozenset({"shell", "flange"}),
))

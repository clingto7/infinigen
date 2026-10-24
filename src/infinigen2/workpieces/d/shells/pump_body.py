"""G30 综合异形泵体原型。

圆角盒并入偏心鼓形腔和一根侧向粗管，再减去顶面大开口和侧面凹槽，
最后并上 2 到 4 条肋板。多机制叠在同一件上，作综合外形。
"""

import math

import procfunc as pf

from infinigen2.workpieces.d.shells.parts import (
    Category,
    aim_z,
    box,
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


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_mat = rng.spawn(3)
    hx = pf.random.uniform(rng_size, 0.12, 0.18)
    hy = pf.random.uniform(rng_size, 0.09, 0.14)
    hz = pf.random.uniform(rng_size, 0.07, 0.12)
    fillet = min(pf.random.uniform(rng_size, 0.010, 0.020), 0.28 * min(hx, hy, hz))
    drum_r = pf.random.uniform(rng_size, 0.055, 0.090)
    drum_off_x = pf.random.uniform(rng_size, -0.04, 0.06)
    drum_off_y = pf.random.uniform(rng_size, -0.03, 0.03)
    pipe_r = pf.random.uniform(rng_size, 0.028, 0.048)
    pipe_len = pf.random.uniform(rng_size, 0.08, 0.14)
    n_rib = int(pf.random.randint(rng_size, 2, 5))
    rib_t = pf.random.uniform(rng_size, 0.014, 0.026)
    rib_h = pf.random.uniform(rng_size, 0.028, 0.050)
    yaw_pipe = pf.random.uniform(rng_style, -0.6, 0.6)

    shell = box((hx * 2.0, hy * 2.0, hz * 2.0), (0.0, 0.0, hz))
    pf.ops.modifier.bevel(shell, width=fillet, segments=2)
    fuse(
        shell,
        sphere(
            (drum_r * 1.15, drum_r, drum_r * 0.92),
            (drum_off_x, drum_off_y, hz * 2.0 + drum_r * 0.15),
            segments=28,
            rings=14,
        ),
        what="pump drum",
    )
    direction = (math.cos(yaw_pipe), math.sin(yaw_pipe), 0.18)
    length = math.sqrt(sum(v * v for v in direction))
    direction = (direction[0] / length, direction[1] / length, direction[2] / length)
    pipe_center = (
        direction[0] * (hx * 0.55 + pipe_len * 0.35),
        direction[1] * (hy * 0.55 + pipe_len * 0.35),
        hz + direction[2] * pipe_len * 0.2,
    )
    fuse(
        shell,
        cylinder(pipe_r, pipe_len + hx * 0.4, pipe_center, rotation=aim_z(direction), vertices=28),
        what="pump pipe",
    )
    drum_top = hz * 2.0 + drum_r * 0.15 + drum_r * 0.92
    mouth_r = drum_r * pf.random.uniform(rng_size, 0.62, 0.88)
    cut(
        shell,
        sphere(
            (mouth_r, mouth_r, mouth_r),
            (drum_off_x, drum_off_y, drum_top + mouth_r * 0.18),
            segments=24,
            rings=12,
        ),
        what="pump mouth",
    )
    slot_w = hy * pf.random.uniform(rng_size, 0.42, 0.72)
    slot_d = hx * pf.random.uniform(rng_size, 0.45, 0.80)
    side = 1.0 if pf.control.choice(rng_style, [(False, 1.0), (True, 1.0)]) else -1.0
    cut(
        shell,
        box(
            (slot_d, slot_w, hz * 1.35),
            (side * (hx - slot_d * 0.35), 0.0, hz * 1.15),
        ),
        what="pump slot",
    )
    pipe_bore = pipe_r - min(0.012, pipe_r * 0.28)
    if pipe_bore > 0.010:
        cut(
            shell,
            cylinder(
                pipe_bore,
                pipe_len + hx * 0.15,
                (
                    direction[0] * (hx * 0.85 + pipe_len * 0.45),
                    direction[1] * (hy * 0.85 + pipe_len * 0.45),
                    hz + direction[2] * pipe_len * 0.25,
                ),
                rotation=aim_z(direction),
                vertices=24,
            ),
            what="pipe bore",
        )

    material = hard_material(rng_mat)
    parts = [tag(shell, material, "shell")]
    embed = 0.005
    for index in range(n_rib):
        t = 0.5 if n_rib == 1 else index / (n_rib - 1)
        y = (-hy * 0.55) + t * (hy * 1.10)
        parts.append(tag(
            box(
                (hx * 1.05, rib_t, rib_h + 0.012),
                (0.0, y, rib_h * 0.35),
            ),
            material,
            "rib",
        ))
    return rest_on_ground(finish(parts))


register(Category(
    category_id="pump_body",
    code="G30",
    family="壳体",
    criterion="圆角盒并鼓腔和侧管，再开大口和槽，带底肋",
    build=build,
    allowed_parts=frozenset({"shell", "rib"}),
))

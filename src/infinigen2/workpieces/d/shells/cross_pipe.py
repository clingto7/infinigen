"""G16 十字四通管壳。

两根粗圆管互相穿过后并集，再减去两根更长的内孔，四个端口连通。
夹角在水平面内偏离直角一点点。第二根管可以沿竖直方向错开，但仍相交。
端环是构型。
"""

import math

import procfunc as pf

from infinigen2.workpieces.d.shells.parts import (
    Category,
    aim_z,
    cut,
    cylinder,
    finish,
    flange_ring,
    fuse,
    hard_material,
    register,
    rest_on_ground,
    tag,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_mat = rng.spawn(3)
    r_a = pf.random.uniform(rng_size, 0.050, 0.085)
    r_b = pf.random.uniform(rng_size, 0.045, 0.080)
    wall = min(pf.random.uniform(rng_size, 0.008, 0.014), min(r_a, r_b) * 0.28)
    len_a = pf.random.uniform(rng_size, 0.32, 0.52)
    len_b = pf.random.uniform(rng_size, 0.30, 0.50)
    phi = math.radians(pf.random.uniform(rng_size, 75.0, 105.0))
    direction_b = (math.sin(phi), math.cos(phi), 0.0)
    skew_cap = min(0.32 * (r_a + r_b), r_a + r_b - 0.018)
    skew = pf.random.uniform(rng_size, -1.0, 1.0) * max(skew_cap, 0.0)
    if not pf.control.choice(rng_style, [(False, 1.4), (True, 1.0)]):
        skew = 0.0
    with_rings = pf.control.choice(rng_style, [(False, 1.0), (True, 1.2)])
    ring_w = pf.random.uniform(rng_style, 0.012, 0.024)
    ring_t = pf.random.uniform(rng_style, 0.009, 0.014)

    along_a = (0.0, 1.0, 0.0)
    shell = cylinder(r_a, len_a, (0.0, 0.0, 0.0), aim_z(along_a), vertices=40)
    fuse(
        shell,
        cylinder(r_b, len_b, (0.0, 0.0, skew), aim_z(direction_b), vertices=40),
        what="cross pipe",
    )
    cut(
        shell,
        cylinder(r_a - wall, len_a + 0.08, (0.0, 0.0, 0.0), aim_z(along_a), vertices=32),
        what="cross bore a",
    )
    cut(
        shell,
        cylinder(r_b - wall, len_b + 0.08, (0.0, 0.0, skew), aim_z(direction_b), vertices=32),
        what="cross bore b",
    )

    material = hard_material(rng_mat)
    parts = [tag(shell, material, "shell")]
    if with_rings:
        half_a = len_a * 0.5 - ring_t * 0.5 + 0.002
        half_b = len_b * 0.5 - ring_t * 0.5 + 0.002
        ports = [
            (r_a, r_a - wall, (0.0, half_a, 0.0), aim_z(along_a)),
            (r_a, r_a - wall, (0.0, -half_a, 0.0), aim_z(along_a)),
            (
                r_b,
                r_b - wall,
                (direction_b[0] * half_b, direction_b[1] * half_b, skew),
                aim_z(direction_b),
            ),
            (
                r_b,
                r_b - wall,
                (-direction_b[0] * half_b, -direction_b[1] * half_b, skew),
                aim_z(direction_b),
            ),
        ]
        for outer, hole, center, rotation in ports:
            parts.append(tag(
                flange_ring(outer + ring_w, hole, ring_t, center, rotation=rotation, vertices=32),
                material,
                "flange",
            ))
    return rest_on_ground(finish(parts))


register(Category(
    category_id="cross_pipe",
    code="G16",
    family="壳体",
    criterion="两根粗管相交成四通，可错层，可加端环",
    build=build,
    allowed_parts=frozenset({"shell", "flange"}),
))

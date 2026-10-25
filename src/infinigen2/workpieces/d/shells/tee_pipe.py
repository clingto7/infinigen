"""G14 T 型三通管体。

沿 Y 的主管与沿 Z 的支管先并成外壳，再依次减去两根更长的内圆柱，
让三处端口和交汇腔连通。法兰是构型，三个端口都有或都没有。
"""

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

_ALONG_Y = (0.0, 1.0, 0.0)
_ALONG_Z = (0.0, 0.0, 1.0)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_mat = rng.spawn(3)
    r_main = pf.random.uniform(rng_size, 0.055, 0.090)
    r_branch = pf.random.uniform(rng_size, 0.042, min(0.080, r_main * 1.05))
    wall = min(pf.random.uniform(rng_size, 0.008, 0.015), r_branch * 0.28)
    main_len = pf.random.uniform(rng_size, 0.36, 0.58)
    branch_len = pf.random.uniform(rng_size, 0.16, 0.28)
    room = main_len * 0.5 - r_branch - 0.04
    offset = pf.random.uniform(rng_size, -1.0, 1.0) * max(room, 0.0)
    with_flange = pf.control.choice(rng_style, [(False, 1.0), (True, 1.4)])
    flange_w = pf.random.uniform(rng_style, 0.016, 0.032)
    flange_t = pf.random.uniform(rng_style, 0.010, 0.016)
    embed = r_main * 0.55

    shell = cylinder(r_main, main_len, (0.0, 0.0, 0.0), aim_z(_ALONG_Y), vertices=40)
    fuse(
        shell,
        cylinder(
            r_branch,
            branch_len + embed,
            (0.0, offset, (branch_len - embed) * 0.5),
            aim_z(_ALONG_Z),
            vertices=36,
        ),
        what="tee branch",
    )
    cut(
        shell,
        cylinder(r_main - wall, main_len + 0.08, (0.0, 0.0, 0.0), aim_z(_ALONG_Y), vertices=32),
        what="tee main bore",
    )
    # Stop inside the main cavity; do not punch through the far wall.
    reach = r_main - wall - 0.004
    cut(
        shell,
        cylinder(
            r_branch - wall,
            branch_len + reach + 0.04,
            (0.0, offset, (branch_len + 0.04 - reach) * 0.5),
            aim_z(_ALONG_Z),
            vertices=32,
        ),
        what="tee branch bore",
    )

    material = hard_material(rng_mat)
    parts = [tag(shell, material, "shell")]
    if with_flange:
        ports = [
            (r_main, r_main - wall, (0.0, main_len * 0.5 - flange_t * 0.5 + 0.002, 0.0), aim_z(_ALONG_Y)),
            (r_main, r_main - wall, (0.0, -main_len * 0.5 + flange_t * 0.5 - 0.002, 0.0), aim_z(_ALONG_Y)),
            (
                r_branch,
                r_branch - wall,
                (0.0, offset, branch_len - flange_t * 0.5 + 0.002),
                aim_z(_ALONG_Z),
            ),
        ]
        for outer, hole, center, rotation in ports:
            parts.append(tag(
                flange_ring(outer + flange_w, hole, flange_t, center, rotation=rotation),
                material,
                "flange",
            ))
    return rest_on_ground(finish(parts))


register(Category(
    category_id="tee_pipe",
    code="G14",
    family="壳体",
    criterion="正交三通管，主管与支管在内部连通，可加三端法兰",
    build=build,
    allowed_parts=frozenset({"shell", "flange"}),
))

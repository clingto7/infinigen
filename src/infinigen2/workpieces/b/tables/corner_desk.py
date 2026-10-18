"""T12 L 形书桌。

结构判据：两块桌面成直角拼接，转角处共用腿。
主台面沿 Y，回台沿 +X 接在主台面的前段。两块台面只在接缝处相贴，体积不重叠。
"""

import procfunc as pf

from infinigen2.workpieces import assemble
from infinigen2.workpieces.common import Category, register


def _legs(
    material: pf.Material,
    leg: float,
    height: float,
    points: list[tuple[float, float]],
) -> list[pf.MeshObject]:
    return [
        assemble.tagged_box(
            (leg, leg, height),
            (x, y, 0.0),
            material,
            "leg_base",
            anchor=(0.5, 0.5, 0.0),
        )
        for x, y in points
    ]


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    main_depth = pf.random.uniform(rng_size, 0.58, 0.72)
    main_width = pf.random.uniform(rng_size, 1.25, 1.70)
    return_length = pf.random.uniform(rng_size, 0.75, 1.15)
    return_depth = pf.random.uniform(rng_size, 0.50, 0.62)
    height = pf.random.uniform(rng_size, 0.72, 0.76)
    thickness = pf.random.uniform(rng_size, 0.03, 0.05)
    leg_height = height - thickness
    leg = 0.045
    margin = 0.06
    material = assemble.hard_material(rng_mat)

    main = assemble.tagged_slab((main_depth, main_width, thickness), material, "top")
    pf.ops.object.set_transform(
        main, location=(main_depth / 2.0, main_width / 2.0, leg_height)
    )
    # abut the main slab at x = main_depth; no shared volume
    side = assemble.tagged_slab((return_length, return_depth, thickness), material, "top")
    pf.ops.object.set_transform(
        side,
        location=(
            main_depth + return_length / 2.0,
            return_depth / 2.0,
            leg_height,
        ),
    )
    # centered on the re-entrant corner so the leg sits under both tops
    shared = (main_depth, return_depth)
    points = [
        (margin, margin),
        (margin, main_width - margin),
        (main_depth - margin, main_width - margin),
        (main_depth, margin),
        (main_depth + return_length - margin, margin),
        (main_depth + return_length - margin, return_depth - margin),
        shared,
    ]
    parts = [main, side, *_legs(material, leg, leg_height, points)]
    return assemble.join_tagged(parts, subdiv_levels=2)


register(
    Category(
        category_id="corner_desk",
        code="T12",
        family="桌台",
        criterion="两块桌面成直角拼接，转角处共用腿",
        build=build,
        allowed_parts=frozenset({"top", "leg_base"}),
    )
)

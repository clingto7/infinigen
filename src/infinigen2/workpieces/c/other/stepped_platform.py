"""Stepped plant stand and step stool built from the same platform assembly."""

import procfunc as pf

from infinigen2.workpieces.c.other.parts import (
    Category,
    hard_material,
    join_tagged,
    placed,
    register,
)


def build(rng: pf.RNG) -> pf.MeshObject:
    """Choose either a fixed three-tier stand or a two/three-step stool."""
    rng_mode, rng_size, rng_mat = rng.spawn(3)
    plant_stand = pf.control.choice(rng_mode, [(True, 1.0), (False, 1.0)])
    if plant_stand:
        steps = 3
        tread = pf.random.uniform(rng_size, 0.22, 0.28)
        rise = pf.random.uniform(rng_size, 0.26, 0.34)
        width = pf.random.uniform(rng_size, 0.34, 0.46)
        plate, top_depth, top_width, top_height = 0.016, tread + 0.02, width + 0.02, 0.018
    else:
        steps = pf.control.choice(rng_size, [(2, 1.0), (3, 1.0)])
        tread = pf.random.uniform(rng_size, 0.22, 0.28)
        rise = pf.random.uniform(rng_size, 0.18, 0.24)
        width = pf.random.uniform(rng_size, 0.36, 0.46)
        plate, top_depth, top_width, top_height = 0.018, tread + 0.02, width, 0.022

    material = hard_material(rng_mat)
    parts = []
    for index in range(steps):
        height = (index + 1) * rise
        x0 = index * tread
        for side in (0.0, width - plate):
            parts.append(placed((tread, plate, height), (x0, side, 0.0), material, "leg_base"))
        parts.append(placed(
            (top_depth, top_width, top_height),
            (x0 - (0.01 if plant_stand else 0.0), -0.01 if plant_stand else 0.0, height),
            material,
            "seat",
        ))
    return join_tagged(parts)


register(Category(
    category_id="stepped_platform",
    code="C-stepped-platform",
    family="其他家具",
    criterion="两到三级阶梯踏板；每级由左右侧板支撑",
    build=build,
    allowed_parts=frozenset({"seat", "leg_base"}),
))

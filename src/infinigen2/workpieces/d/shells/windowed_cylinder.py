"""G06 侧窗空心圆筒。

外圆柱减去同轴内圆柱，再在侧面用盒子切出矩形窗口。
窗口角宽是轴线处的张角，窗口高度留出上下边。
端环是构型：没有、只有上端，或上下都有。环宽落在筒壁端面以内。
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
    register,
    rest_on_ground,
    tag,
)


def _ring(outer_r: float, ring_w: float, thick: float, z: float) -> pf.MeshObject:
    ring = cylinder(outer_r + 0.004, thick, center=(0.0, 0.0, z), vertices=48)
    return cut(
        ring,
        cylinder(outer_r - ring_w, thick + 0.02, center=(0.0, 0.0, z), vertices=40),
        what="end ring",
    )


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_mat = rng.spawn(3)
    outer_r = pf.random.uniform(rng_size, 0.12, 0.20)
    inner_ratio = pf.random.uniform(rng_size, 0.55, 0.78)
    inner_r = outer_r * inner_ratio
    height = pf.random.uniform(rng_size, 0.24, 0.50)
    opening = math.radians(pf.random.uniform(rng_size, 40.0, 110.0))
    win_h = pf.random.uniform(rng_size, 0.30, 0.62) * height
    azimuth = pf.random.uniform(rng_size, 0.0, 2.0 * math.pi)
    z_shift = pf.random.uniform(rng_size, -0.12, 0.12) * height
    ring_w = min(
        pf.random.uniform(rng_size, 0.012, 0.028),
        (outer_r - inner_r) * 0.72,
    )
    rings = pf.control.choice(rng_style, [("none", 1.0), ("top", 1.5), ("both", 1.0)])
    material = hard_material(rng_mat)

    shell = cylinder(outer_r, height, center=(0.0, 0.0, height * 0.5), vertices=56)
    cut(
        shell,
        cylinder(inner_r, height + 0.06, center=(0.0, 0.0, height * 0.5), vertices=48),
        what="cylinder bore",
    )
    half_chord = outer_r * math.sin(opening * 0.5)
    # Stay on the window's side of the axis so the opposite wall remains.
    outer_end = outer_r + 0.025
    inner_end = max(inner_r * 0.45, 0.012)
    margin = 0.018
    center_z = min(max(height * 0.5 + z_shift, margin + win_h * 0.5), height - margin - win_h * 0.5)
    center_r = (outer_end + inner_end) * 0.5
    window = box(
        (outer_end - inner_end, max(2.0 * half_chord, 0.02), win_h),
        (math.cos(azimuth) * center_r, math.sin(azimuth) * center_r, center_z),
        rotation=(0.0, 0.0, azimuth),
    )
    cut(shell, window, what="side window")

    parts = [tag(shell, material, "shell")]
    thick = 0.010
    if rings in ("top", "both"):
        parts.append(tag(
            _ring(outer_r, ring_w, thick, height + thick * 0.5 - 0.002),
            material,
            "flange",
        ))
    if rings == "both":
        parts.append(tag(
            _ring(outer_r, ring_w, thick, thick * 0.5 - 0.002),
            material,
            "flange",
        ))
    return rest_on_ground(finish(parts))


register(Category(
    category_id="windowed_cylinder",
    code="G06",
    family="壳体",
    criterion="空心圆筒带侧向矩形窗，可在端面加环",
    build=build,
    allowed_parts=frozenset({"shell", "flange"}),
))

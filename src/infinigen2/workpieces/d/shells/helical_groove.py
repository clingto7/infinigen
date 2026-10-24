"""G12 宽螺旋槽圆柱。

实心粗圆柱减去沿缓螺旋扫掠的矩形槽。圈数约 0.6 到 1.8，螺距大于槽宽，
避免并成细牙螺纹。槽在两端留出实心余量。
剖面宽度沿曲线法向，也就是径向吃入深度；高度沿副法向，也就是槽宽。
"""

import procfunc as pf

from infinigen2.workpieces.d.shells.parts import (
    Category,
    cut,
    cylinder,
    finish,
    hard_material,
    register,
    rest_on_ground,
    tag,
)


def _groove_cutter(
    helix_r: float,
    turns: float,
    travel: float,
    radial: float,
    groove_w: float,
    margin: float,
) -> pf.MeshObject:
    resolution = max(32, int(turns * 56))
    spiral = pf.nodes.geo.curve_spiral(
        resolution=resolution,
        rotations=turns,
        start_radius=helix_r,
        end_radius=helix_r,
        height=travel,
    )
    profile = pf.nodes.geo.curve_quadrilateral(width=radial, height=groove_w)
    solid = pf.nodes.geo.curve_to_mesh(curve=spiral, profile_curve=profile, fill_caps=True)
    placed = pf.nodes.geo.transform(solid, translation=(0.0, 0.0, margin))
    return pf.nodes.to_mesh_object(placed)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    radius = pf.random.uniform(rng_size, 0.10, 0.16)
    height = pf.random.uniform(rng_size, 0.30, 0.50)
    turns = pf.random.uniform(rng_size, 0.60, 1.80)
    margin = pf.random.uniform(rng_size, 0.035, 0.060)
    groove_w = pf.random.uniform(rng_size, 0.040, 0.070)
    groove_d = pf.random.uniform(rng_size, 0.016, 0.030)
    travel = height - 2.0 * margin
    # Adjacent turns stay apart, so the groove does not close into a thread.
    min_pitch = groove_w * 1.20
    if travel / turns < min_pitch:
        turns = max(0.55, travel / min_pitch)
    radial = groove_d + 0.030
    helix_r = radius - groove_d + radial * 0.5

    shell = cylinder(radius, height, center=(0.0, 0.0, height * 0.5), vertices=64)
    cut(
        shell,
        _groove_cutter(helix_r, turns, travel, radial, groove_w, margin),
        what="helical groove",
    )
    return rest_on_ground(finish([tag(shell, hard_material(rng_mat), "shell")]))


register(Category(
    category_id="helical_groove",
    code="G12",
    family="壳体",
    criterion="粗圆柱表面有不到两圈的宽螺旋槽，两端留余量",
    build=build,
    allowed_parts=frozenset({"shell"}),
))

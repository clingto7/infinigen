"""G02 离心风机蜗壳原型。

平面螺旋中心线上扫掠渐变矩形截面，再减去缩小的内扫掠体形成壳体。
螺旋末端沿切向接出矩形风口，并用更小的盒子把风口掏通。
入口是螺旋起点顶面上的圆孔，孔边有一圈法兰。
螺旋扩张率是终点半径与起点半径之比。截面沿程按同一比例放大。
"""

import math

import procfunc as pf

from infinigen2.workpieces.d.shells.parts import (
    Category,
    box,
    cut,
    cylinder,
    finish,
    fuse,
    hard_material,
    register,
    rest_on_ground,
    tag,
)

_RESOLUTION = 48


def _spiral_solid(
    start_r: float,
    end_r: float,
    turns: float,
    width: float,
    height: float,
    growth: float,
    trim: tuple[float, float] | None = None,
) -> pf.MeshObject:
    spiral = pf.nodes.geo.curve_spiral(
        resolution=_RESOLUTION,
        rotations=turns,
        start_radius=start_r,
        end_radius=end_r,
        height=0.0,
    )
    factor = pf.nodes.geo.spline_parameter().factor
    scale = pf.nodes.math.map_range(
        value=factor, from_min=0.0, from_max=1.0, to_min=1.0, to_max=growth
    )
    sized = pf.nodes.geo.set_curve_radius(spiral, radius=scale)
    if trim is not None:
        sized = pf.nodes.geo.trim_curve(sized, start=trim[0], end=trim[1])
    profile = pf.nodes.geo.curve_quadrilateral(width=width, height=height)
    solid = pf.nodes.geo.curve_to_mesh(curve=sized, profile_curve=profile, fill_caps=True)
    return pf.nodes.to_mesh_object(solid)


def _end_tangent(start_r: float, end_r: float, turns: float) -> tuple[float, float, float, float]:
    theta = turns * 2.0 * math.pi
    dr = (end_r - start_r) / theta
    tangent_x = dr * math.cos(theta) - end_r * math.sin(theta)
    tangent_y = dr * math.sin(theta) + end_r * math.cos(theta)
    return end_r * math.cos(theta), end_r * math.sin(theta), tangent_x, tangent_y


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    turns = pf.random.uniform(rng_size, 1.05, 1.30)
    start_r = pf.random.uniform(rng_size, 0.10, 0.15)
    expansion = pf.random.uniform(rng_size, 1.65, 2.20)
    end_r = start_r * expansion
    radial_pitch = (end_r - start_r) / turns
    growth = pf.random.uniform(rng_size, 1.35, 1.75)
    shell_h1 = pf.random.uniform(rng_size, 0.09, 0.14)
    h0 = shell_h1 / growth
    w1 = min(pf.random.uniform(rng_size, 0.055, 0.095), radial_pitch * 0.72)
    w1 = max(w1, 0.046)
    w0 = w1 / growth
    wall = min(0.009, w0 * 0.22, h0 * 0.22)
    outlet_angle = pf.random.uniform(rng_size, -0.35, 0.40)
    outlet_len = pf.random.uniform(rng_size, 0.08, 0.14)
    inlet_d = pf.random.uniform(rng_size, 0.42, 0.72) * min(w0 - 2.0 * wall, h0 - 2.0 * wall)
    flange_w = pf.random.uniform(rng_size, 0.010, 0.018)
    material = hard_material(rng_mat)

    shell = _spiral_solid(start_r, end_r, turns, w0, h0, growth)
    end_x, end_y, tangent_x, tangent_y = _end_tangent(start_r, end_r, turns)
    yaw = math.atan2(tangent_y, tangent_x) + outlet_angle
    direction = (math.cos(yaw), math.sin(yaw))
    overlap = 0.028
    outlet = box(
        (outlet_len + overlap, w1 * 0.96, shell_h1 * 0.96),
        (
            end_x + direction[0] * (outlet_len - overlap) * 0.5,
            end_y + direction[1] * (outlet_len - overlap) * 0.5,
            0.0,
        ),
        rotation=(0.0, 0.0, yaw),
    )
    fuse(shell, outlet, what="volute outlet")

    cavity = _spiral_solid(
        start_r,
        end_r,
        turns,
        w0 - 2.0 * wall,
        h0 - 2.0 * wall,
        growth,
        trim=(0.04, 0.96),
    )
    cut(shell, cavity, what="volute cavity")

    inlet_r = inlet_d * 0.5
    cut(
        shell,
        cylinder(inlet_r, h0 * 2.6, center=(start_r, 0.0, 0.0), vertices=32),
        what="volute inlet",
    )
    void_back = overlap + 0.07
    void_forward = outlet_len + 0.012
    void_span = void_back + void_forward
    void_center = (void_forward - void_back) * 0.5
    inner_w1 = (w0 - 2.0 * wall) * growth
    inner_h1 = (h0 - 2.0 * wall) * growth
    void = box(
        (void_span, inner_w1, inner_h1),
        (
            end_x + direction[0] * void_center,
            end_y + direction[1] * void_center,
            0.0,
        ),
        rotation=(0.0, 0.0, yaw),
    )
    cut(shell, void, what="volute outlet bore")

    ring_t = 0.008
    ring_z = h0 * 0.5 + ring_t * 0.5 - 0.002
    ring = cylinder(inlet_r + flange_w, ring_t, center=(start_r, 0.0, ring_z), vertices=32)
    cut(
        ring,
        cylinder(inlet_r, ring_t + 0.02, center=(start_r, 0.0, ring_z), vertices=32),
        what="inlet flange",
    )
    return rest_on_ground(finish([
        tag(shell, material, "shell"),
        tag(ring, material, "flange"),
    ]))


register(Category(
    category_id="volute_housing",
    code="G02",
    family="壳体",
    criterion="螺旋扫掠壳体，侧向矩形出口，圆孔入口带法兰",
    build=build,
    allowed_parts=frozenset({"shell", "flange"}),
))

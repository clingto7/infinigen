"""G18 圆转方过渡风道。

一端圆形、一端圆角矩形的开口壳体，中间按高度线性混合两个截面。
矩形口可以相对圆口偏心。向内加厚得到壁厚，两端保持开口。
圆口和方口各加一圈宽法兰。
"""

import math

import procfunc as pf

from infinigen2.workpieces.d.shells.parts import (
    Category,
    box,
    cut,
    finish,
    flange_ring,
    hard_material,
    register,
    rest_on_ground,
    tag,
)


def _open_tube(radius: float, depth: float, center: tuple[float, float, float]) -> pf.MeshObject:
    solid = pf.nodes.geo.mesh_cone(
        vertices=48,
        side_segments=12,
        radius_top=radius,
        radius_bottom=radius,
        depth=depth,
        fill_type="NONE",
    )
    centered = pf.nodes.geo.transform(solid.mesh, translation=(0.0, 0.0, -depth * 0.5))
    placed = pf.nodes.geo.transform(centered, translation=center)
    return pf.nodes.to_mesh_object(placed)


def _rounded_rect(theta: float, half_w: float, half_h: float, corner: float) -> tuple[float, float]:
    dx, dy = math.cos(theta), math.sin(theta)
    hits: list[float] = []
    straight_x = half_w - corner
    straight_y = half_h - corner
    if abs(dy) > 1e-9:
        for sign in (1.0, -1.0):
            scale = sign * half_h / dy
            if scale > 0.0 and abs(scale * dx) <= straight_x + 1e-8:
                hits.append(scale)
    if abs(dx) > 1e-9:
        for sign in (1.0, -1.0):
            scale = sign * half_w / dx
            if scale > 0.0 and abs(scale * dy) <= straight_y + 1e-8:
                hits.append(scale)
    for side_x in (1.0, -1.0):
        for side_y in (1.0, -1.0):
            cx, cy = side_x * straight_x, side_y * straight_y
            b = -2.0 * (dx * cx + dy * cy)
            c = cx * cx + cy * cy - corner * corner
            disc = b * b - 4.0 * c
            if disc < 0.0:
                continue
            root = math.sqrt(disc)
            for scale in ((-b - root) * 0.5, (-b + root) * 0.5):
                if scale <= 0.0:
                    continue
                px, py = scale * dx, scale * dy
                if (px - cx) * side_x >= -1e-8 and (py - cy) * side_y >= -1e-8:
                    hits.append(scale)
    if not hits:
        raise RuntimeError(f"rounded-rect ray missed at theta={theta:.3f}")
    t = min(hits)
    return t * dx, t * dy


def _morph(
    obj: pf.MeshObject,
    z0: float,
    length: float,
    start_r: float,
    half_w: float,
    half_h: float,
    corner: float,
    offset: float,
) -> pf.MeshObject:
    data = obj.item().data
    for vertex in data.vertices:
        t = (vertex.co.z - z0) / length
        rho = math.hypot(vertex.co.x, vertex.co.y)
        if rho < 1e-7:
            vertex.co.x = offset * t
            continue
        theta = math.atan2(vertex.co.y, vertex.co.x)
        sx = start_r * math.cos(theta)
        sy = start_r * math.sin(theta)
        ex, ey = _rounded_rect(theta, half_w, half_h, corner)
        vertex.co.x = (1.0 - t) * sx + t * (ex + offset)
        vertex.co.y = (1.0 - t) * sy + t * ey
    data.update()
    return obj


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    r_circle = pf.random.uniform(rng_size, 0.065, 0.105)
    half_w = pf.random.uniform(rng_size, 0.100, 0.165)
    half_h = pf.random.uniform(rng_size, 0.045, 0.075)
    corner = min(pf.random.uniform(rng_size, 0.016, 0.038), 0.42 * min(half_w, half_h))
    wall = min(pf.random.uniform(rng_size, 0.008, 0.015), 0.22 * min(r_circle, half_h))
    length = pf.random.uniform(rng_size, 0.22, 0.40)
    offset = pf.random.uniform(rng_size, -0.55, 0.55) * max(half_w - r_circle, 0.012)
    flange_w = pf.random.uniform(rng_size, 0.018, 0.034)
    flange_t = pf.random.uniform(rng_size, 0.010, 0.016)

    shell = _open_tube(r_circle, length, (0.0, 0.0, length * 0.5))
    _morph(shell, 0.0, length, r_circle, half_w, half_h, corner, offset)
    pf.ops.modifier.solidify(shell, thickness=wall, offset=-1.0, use_even_offset=True, use_rim=True)

    material = hard_material(rng_mat)
    round_flange = flange_ring(
        r_circle + flange_w,
        r_circle - wall,
        flange_t,
        (0.0, 0.0, flange_t * 0.35),
    )
    plate = box(
        (2.0 * half_w + 2.0 * flange_w, 2.0 * half_h + 2.0 * flange_w, flange_t),
        (offset, 0.0, length - flange_t * 0.35),
    )
    cutter = box(
        (2.0 * (half_w - wall * 0.2), 2.0 * (half_h - wall * 0.2), flange_t + 0.04),
        (offset, 0.0, length - flange_t * 0.35),
    )
    pf.ops.modifier.bevel(cutter, width=max(corner - wall, 0.008), segments=2)
    cut(plate, cutter, what="rect flange opening")
    return rest_on_ground(finish([
        tag(shell, material, "shell"),
        tag(round_flange, material, "flange"),
        tag(plate, material, "flange"),
    ]))


register(Category(
    category_id="circle_rect_duct",
    code="G18",
    family="壳体",
    criterion="圆口到圆角方口的过渡风道，两端带法兰，可偏心",
    build=build,
    allowed_parts=frozenset({"shell", "flange"}),
))

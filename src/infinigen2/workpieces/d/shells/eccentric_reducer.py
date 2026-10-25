"""G17 偏心变径圆管。

大小两端用圆台连接，再把轴线沿高度错开，形成偏心变径。
可选的轻微弯曲叠在偏心上。先做成开口圆台再向内加厚，避免内壳布尔
把下端切掉。法兰贴在两个端口上，小端法兰跟着偏心走。
"""

import math

import procfunc as pf

from infinigen2.workpieces.d.shells.parts import (
    Category,
    finish,
    flange_ring,
    hard_material,
    register,
    rest_on_ground,
    tag,
)


def _open_frustum(
    radius_bottom: float,
    radius_top: float,
    depth: float,
    center: tuple[float, float, float],
    vertices: int = 48,
    side_segments: int = 10,
) -> pf.MeshObject:
    solid = pf.nodes.geo.mesh_cone(
        vertices=vertices,
        side_segments=side_segments,
        radius_top=radius_top,
        radius_bottom=radius_bottom,
        depth=depth,
        fill_type="NONE",
    )
    # Mesh Cone sits on z = 0; ``center`` is the geometric center.
    centered = pf.nodes.geo.transform(solid.mesh, translation=(0.0, 0.0, -depth * 0.5))
    placed = pf.nodes.geo.transform(centered, translation=center)
    return pf.nodes.to_mesh_object(placed)


def _shift_x(obj: pf.MeshObject, offset: float, z0: float, z1: float, bend: float) -> pf.MeshObject:
    span = z1 - z0
    data = obj.item().data
    for vertex in data.vertices:
        t = (vertex.co.z - z0) / span
        vertex.co.x += offset * t + bend * math.sin(math.pi * t)
    data.update()
    return obj


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    r_large = pf.random.uniform(rng_size, 0.075, 0.120)
    r_small = r_large * pf.random.uniform(rng_size, 0.42, 0.62)
    wall = min(pf.random.uniform(rng_size, 0.008, 0.015), r_small * 0.30)
    length = pf.random.uniform(rng_size, 0.22, 0.40)
    ecc = pf.random.uniform(rng_size, 0.82, 1.0) * (r_large - r_small)
    bend = pf.random.uniform(rng_size, 0.0, 0.040)
    flange_w = pf.random.uniform(rng_size, 0.016, 0.032)
    flange_t = pf.random.uniform(rng_size, 0.010, 0.016)

    shell = _open_frustum(r_large, r_small, length, (0.0, 0.0, length * 0.5), vertices=48, side_segments=10)
    _shift_x(shell, ecc, 0.0, length, bend)
    pf.ops.modifier.solidify(shell, thickness=wall, offset=-1.0, use_even_offset=True, use_rim=True)

    material = hard_material(rng_mat)
    bottom = flange_ring(
        r_large + flange_w,
        r_large - wall,
        flange_t,
        (0.0, 0.0, flange_t * 0.35),
    )
    top = flange_ring(
        r_small + flange_w,
        r_small - wall,
        flange_t,
        (ecc, 0.0, length - flange_t * 0.35),
    )
    return rest_on_ground(finish([
        tag(shell, material, "shell"),
        tag(bottom, material, "flange"),
        tag(top, material, "flange"),
    ]))


register(Category(
    category_id="eccentric_reducer",
    code="G17",
    family="壳体",
    criterion="大小圆口偏心过渡的变径管，两端带法兰",
    build=build,
    allowed_parts=frozenset({"shell", "flange"}),
))

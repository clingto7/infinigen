"""G13 大弯头带法兰。

沿平面圆弧扫掠圆截面得到弯管，再减去更小的内扫掠体掏出通道。
内扫掠在两端各多伸出一段，把端盖切掉。法兰贴在两个端口上。
"""

import math

import procfunc as pf

from infinigen2.workpieces.d.shells.parts import (
    Category,
    aim_z,
    cut,
    finish,
    flange_ring,
    hard_material,
    pose,
    register,
    rest_on_ground,
    tag,
)


def _arc_tube(
    path_r: float,
    start: float,
    sweep: float,
    pipe_r: float,
    *,
    resolution: int = 36,
    profile: int = 32,
) -> pf.MeshObject:
    arc = pf.nodes.geo.curve_arc(
        resolution=resolution,
        radius=path_r,
        start_angle=start,
        sweep_angle=sweep,
    )
    arc = pf.nodes.geo.set_curve_normal(arc, mode="Z_UP")
    circle = pf.nodes.geo.curve_circle(resolution=profile, radius=pipe_r)
    solid = pf.nodes.geo.curve_to_mesh(curve=arc, profile_curve=circle, fill_caps=True)
    return pf.nodes.to_mesh_object(solid)


def _port(path_r: float, angle: float) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    position = (path_r * math.cos(angle), path_r * math.sin(angle), 0.0)
    tangent = (-math.sin(angle), math.cos(angle), 0.0)
    return position, tangent


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_mat = rng.spawn(2)
    outer_r = pf.random.uniform(rng_size, 0.055, 0.095)
    wall = min(pf.random.uniform(rng_size, 0.009, 0.016), outer_r * 0.28)
    inner_r = outer_r - wall
    path_r = max(pf.random.uniform(rng_size, 0.16, 0.30), outer_r * 1.55)
    bend = math.radians(pf.random.uniform(rng_size, 70.0, 115.0))
    flange_w = pf.random.uniform(rng_size, 0.018, 0.036)
    flange_t = pf.random.uniform(rng_size, 0.010, 0.018)
    extra = 0.045 / path_r

    shell = _arc_tube(path_r, 0.0, bend, outer_r)
    cut(
        shell,
        _arc_tube(path_r, -extra, bend + 2.0 * extra, inner_r, resolution=36, profile=28),
        what="elbow bore",
    )

    material = hard_material(rng_mat)
    parts = [tag(shell, material, "shell")]
    for angle, outward in ((0.0, -1.0), (bend, 1.0)):
        origin, tangent = _port(path_r, angle)
        shift = flange_t * 0.5 - 0.002
        center = (
            origin[0] + outward * tangent[0] * shift,
            origin[1] + outward * tangent[1] * shift,
            origin[2],
        )
        parts.append(tag(
            flange_ring(
                outer_r + flange_w,
                inner_r,
                flange_t,
                center,
                rotation=aim_z(tangent),
            ),
            material,
            "flange",
        ))
    # Stand the elbow so one flange sits on the ground and the other points sideways.
    return rest_on_ground(pose(finish(parts), rotation=(math.pi / 2.0, 0.0, 0.0)))


register(Category(
    category_id="flanged_elbow",
    code="G13",
    family="壳体",
    criterion="圆弧弯管两端带法兰，内通道贯通",
    build=build,
    allowed_parts=frozenset({"shell", "flange"}),
))

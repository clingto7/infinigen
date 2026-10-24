"""G15 Y 型分流管体。

三根圆管在节点处并集。入口沿 −Y，两根支管在水平面内对称分开，
其中一根可以再带一点倾角。内孔都伸过节点，三向贯通。
圆滑节点是构型：在交汇处并入一个球再挖空。
"""

import math

import procfunc as pf

from infinigen2.workpieces.d.shells.parts import (
    Category,
    aim_z,
    cut,
    cylinder,
    finish,
    fuse,
    hard_material,
    register,
    rest_on_ground,
    sphere,
    tag,
)


def _unit(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    length = math.sqrt(vector[0] ** 2 + vector[1] ** 2 + vector[2] ** 2)
    return (vector[0] / length, vector[1] / length, vector[2] / length)


def _tilt_around_x(direction: tuple[float, float, float], tilt: float) -> tuple[float, float, float]:
    cosine, sine = math.cos(tilt), math.sin(tilt)
    return _unit((direction[0], direction[1] * cosine - direction[2] * sine, direction[1] * sine + direction[2] * cosine))


def _limb(
    radius: float,
    length: float,
    direction: tuple[float, float, float],
    embed: float,
    vertices: int,
) -> pf.MeshObject:
    total = length + embed
    center = (
        direction[0] * (length - embed) * 0.5,
        direction[1] * (length - embed) * 0.5,
        direction[2] * (length - embed) * 0.5,
    )
    return cylinder(radius, total, center, aim_z(direction), vertices=vertices)


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_mat = rng.spawn(3)
    r_stem = pf.random.uniform(rng_size, 0.050, 0.082)
    ratio = pf.random.uniform(rng_size, 0.72, 1.0)
    r_a = r_stem * ratio
    r_b = r_stem * pf.random.uniform(rng_size, 0.72, 1.0)
    wall = min(pf.random.uniform(rng_size, 0.008, 0.014), min(r_a, r_b) * 0.28)
    stem_len = pf.random.uniform(rng_size, 0.18, 0.30)
    len_a = pf.random.uniform(rng_size, 0.16, 0.28)
    len_b = pf.random.uniform(rng_size, 0.16, 0.28)
    fork = math.radians(pf.random.uniform(rng_size, 48.0, 95.0))
    tilt = math.radians(pf.random.uniform(rng_size, 10.0, 26.0))
    if not pf.control.choice(rng_style, [(False, 1.2), (True, 1.0)]):
        tilt = 0.0
    smooth = pf.control.choice(rng_style, [(False, 1.0), (True, 1.1)])
    half = fork * 0.5
    # Stem sits on the ground; the two arms rise in the XZ plane.
    directions = [
        (0.0, 0.0, -1.0),
        (math.sin(half), 0.0, math.cos(half)),
        _tilt_around_x((-math.sin(half), 0.0, math.cos(half)), tilt),
    ]
    radii = [r_stem, r_a, r_b]
    lengths = [stem_len, len_a, len_b]
    embed = max(radii) * 0.70

    shell = _limb(radii[0], lengths[0], directions[0], embed, 40)
    fuse(shell, _limb(radii[1], lengths[1], directions[1], embed, 36), what="wye arm")
    fuse(shell, _limb(radii[2], lengths[2], directions[2], embed, 36), what="wye arm")
    if smooth:
        node_r = max(radii) * 1.12
        fuse(shell, sphere((node_r, node_r, node_r), (0.0, 0.0, 0.0), segments=32, rings=16), what="wye node")
        cut(
            shell,
            sphere((node_r - wall, node_r - wall, node_r - wall), (0.0, 0.0, 0.0), segments=28, rings=14),
            what="wye node cavity",
        )
    for radius, length, direction in zip(radii, lengths, directions):
        cut(
            shell,
            _limb(radius - wall, length + 0.04, direction, embed + 0.06, 32),
            what="wye bore",
        )
    return rest_on_ground(finish([tag(shell, hard_material(rng_mat), "shell")]))


register(Category(
    category_id="wye_pipe",
    code="G15",
    family="壳体",
    criterion="Y 形三通，两支管可不等径，节点可圆滑，内腔贯通",
    build=build,
    allowed_parts=frozenset({"shell"}),
))

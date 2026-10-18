"""T16 支架桌。

结构判据：两端是 A 形或 I 形支架，中间一根长横撑。
A 形和 I 形是构型。桌面沿 Y 为长度，支架立在两端，横撑沿长度穿过两架。
"""

import math

import procfunc as pf

from infinigen2.util import mesh, spray
from infinigen2.workpieces.assemble import hard_material, join_tagged, tagged_slab
from infinigen2.workpieces.c.tables.parts import Category, register


def _board(
    material: pf.Material,
    size: tuple[float, float, float],
    location: tuple[float, float, float],
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> pf.MeshObject:
    """Box whose bottom-center is the object origin, then placed in the world."""
    geo = mesh.metric_box_uv(
        mesh.box(size=size, location=(0.0, 0.0, 0.0), anchor=(0.5, 0.5, 0.0))
    )
    obj = pf.nodes.to_mesh_object(geo)
    pf.ops.object.set_material(
        obj, surface=material.surface, displacement=material.displacement
    )
    spray.write_spray_part(obj, "leg_base")
    pf.ops.object.set_transform(obj, location=location, rotation_euler=rotation)
    return obj


def _slant(
    material: pf.Material,
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    face: float,
    thick: float,
) -> pf.MeshObject:
    dx = end[0] - start[0]
    dz = end[2] - start[2]
    length = math.hypot(dx, dz)
    angle = math.atan2(dx, dz)
    return _board(material, (face, thick, length), start, rotation=(0.0, angle, 0.0))


def _a_frame(material, y, span, leg_h, face, thick, z_bar) -> list[pf.MeshObject]:
    foot_h = 0.045
    cleat_h = 0.05
    cleat_w = span * 0.22
    z_bot = foot_h * 0.55
    z_top = leg_h - cleat_h * 0.45
    x_bot = span * 0.5 - face * 0.35
    x_top = cleat_w * 0.5
    foot = _board(material, (span, thick, foot_h), (0.0, y, 0.0))
    cleat = _board(material, (cleat_w, thick, cleat_h), (0.0, y, leg_h - cleat_h))
    left = _slant(material, (-x_bot, y, z_bot), (-x_top, y, z_top), face, thick)
    right = _slant(material, (x_bot, y, z_bot), (x_top, y, z_top), face, thick)
    rise = z_top - z_bot
    along = (z_bar - z_bot) / rise
    x_here = x_bot + along * (x_top - x_bot)
    bar = _board(material, (x_here * 2.0, thick, 0.04), (0.0, y, z_bar - 0.02))
    return [foot, cleat, left, right, bar]


def _i_frame(material, y, span, leg_h, face, thick) -> list[pf.MeshObject]:
    beam_h = 0.08
    post_w = max(face, 0.07)
    embed = 0.012
    bottom = _board(material, (span, thick, beam_h), (0.0, y, 0.0))
    top = _board(material, (span, thick, beam_h), (0.0, y, leg_h - beam_h))
    post_h = leg_h - 2.0 * beam_h + 2.0 * embed
    post = _board(material, (post_w, thick, post_h), (0.0, y, beam_h - embed))
    return [bottom, top, post]


def build(rng: pf.RNG) -> pf.MeshObject:
    rng_size, rng_style, rng_mat = rng.spawn(3)
    depth = pf.random.uniform(rng_size, 0.75, 0.95)
    length = pf.random.uniform(rng_size, 1.50, 2.10)
    height = pf.random.uniform(rng_size, 0.72, 0.76)
    top_t = pf.random.uniform(rng_size, 0.030, 0.045)
    overhang = pf.random.uniform(rng_size, 0.16, 0.26)
    span = depth * pf.random.uniform(rng_size, 0.70, 0.84)
    thick = pf.random.uniform(rng_size, 0.035, 0.050)
    face = pf.random.uniform(rng_size, 0.055, 0.075)
    leg_h = height - top_t
    y0 = length * 0.5 - overhang
    style = pf.control.choice(rng_style, [("a", 1.0), ("i", 1.0)])
    material = hard_material(rng_mat)
    z_bar = leg_h * 0.42
    if style == "a":
        trestles = [
            part
            for y in (-y0, y0)
            for part in _a_frame(material, y, span, leg_h, face, thick, z_bar)
        ]
    else:
        trestles = [
            part
            for y in (-y0, y0)
            for part in _i_frame(material, y, span, leg_h, face, thick)
        ]
    stretcher = _board(material, (0.05, y0 * 2.0, 0.05), (0.0, 0.0, z_bar - 0.025))
    top = tagged_slab((depth, length, top_t), material, "top")
    pf.ops.object.set_transform(top, location=(0.0, 0.0, leg_h))
    return join_tagged([top, stretcher, *trestles], subdiv_levels=0)


register(Category(
    category_id="trestle_table",
    code="T16",
    family="桌台",
    criterion="两端是 A 形或 I 形支架，中间一根长横撑",
    build=build,
    allowed_parts=frozenset({"top", "leg_base"}),
))

"""New geometry for C-tier seating.

Boards and rods are tagged before they move. A member's long axis is local Z.
Blender's XYZ Euler ``(0, pitch, yaw)`` aims that axis from the start point to
the end point, and the member stays centered on the segment.
"""

import math

import procfunc as pf

from infinigen2.objects import furniture_bases
from infinigen2.objects.chair import (
    _dining_seat_with_back,
    _dining_slat_back,
    _dining_solid_back,
    chair_seat_round,
)
from infinigen2.util import mesh, spray
from infinigen2.workpieces.assemble import join_tagged, vertex_bounds
from infinigen2.workpieces.common import Category, register

__all__ = [
    "Category",
    "aim",
    "board",
    "chain",
    "dining_with_back",
    "four_legs",
    "join_tagged",
    "oriented_board",
    "point_at_z",
    "register",
    "rocker",
    "rod",
    "round_seat",
    "strut",
    "vertex_bounds",
]


def _materialize(geo, material: pf.Material, part: str) -> pf.MeshObject:
    obj = pf.nodes.to_mesh_object(geo)
    pf.ops.object.set_material(
        obj, surface=material.surface, displacement=material.displacement
    )
    spray.write_spray_part(obj, part)
    return obj


def board(
    size: tuple[float, float, float],
    center: tuple[float, float, float],
    material: pf.Material,
    part: str,
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> pf.MeshObject:
    """Axis-aligned box until ``rotation`` aims it. ``center`` is its center."""
    geo = mesh.box(size=size, location=(0.0, 0.0, 0.0), anchor=(0.5, 0.5, 0.5))
    obj = _materialize(geo, material, part)
    pf.ops.object.set_transform(obj, location=center, rotation_euler=rotation)
    return obj


def aim(
    start: tuple[float, float, float], end: tuple[float, float, float]
) -> tuple[float, tuple[float, float, float], tuple[float, float, float]]:
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    dz = end[2] - start[2]
    length = math.hypot(dx, dy, dz)
    if length < 1e-6:
        raise ValueError("member length must be positive")
    pitch = math.atan2(math.hypot(dx, dy), dz)
    yaw = math.atan2(dy, dx)
    mid = (
        (start[0] + end[0]) * 0.5,
        (start[1] + end[1]) * 0.5,
        (start[2] + end[2]) * 0.5,
    )
    return length, mid, (0.0, pitch, yaw)


def strut(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    section: tuple[float, float],
    material: pf.Material,
    part: str,
) -> pf.MeshObject:
    """Straight board. ``section`` is (local X, local Y) and local Z runs the span."""
    length, mid, rotation = aim(start, end)
    return board((section[0], section[1], length), mid, material, part, rotation)


def rod(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    radius: float,
    material: pf.Material,
    part: str,
    resolution: int = 8,
) -> pf.MeshObject:
    length, mid, rotation = aim(start, end)
    geo = mesh.quad_cylinder(radius=radius, depth=length, resolution=resolution)
    obj = _materialize(geo, material, part)
    pf.ops.object.set_transform(obj, location=mid, rotation_euler=rotation)
    return obj


def _add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def chain(
    points: list[tuple[float, float, float]],
    material: pf.Material,
    part: str,
    section: tuple[float, float] | None = None,
    radius: float | None = None,
    overlap: float = 0.0,
) -> list[pf.MeshObject]:
    """Members through ``points``. ``overlap`` extends every joint so corners meet."""
    made = []
    last = len(points) - 2
    for index, (start, end) in enumerate(zip(points, points[1:])):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        dz = end[2] - start[2]
        length = math.hypot(dx, dy, dz)
        direction = (dx / length, dy / length, dz / length)
        if index > 0:
            start = _add(start, _scale(direction, -overlap))
        if index < last:
            end = _add(end, _scale(direction, overlap))
        if radius is None:
            made.append(strut(start, end, section, material, part))
        else:
            made.append(rod(start, end, radius, material, part))
    return made


def oriented_board(
    center: tuple[float, float, float],
    normal: tuple[float, float, float],
    size: tuple[float, float, float],
    material: pf.Material,
    part: str,
) -> pf.MeshObject:
    """``size`` is (slope width, Y length, thickness). Thickness follows ``normal``."""
    _, _, rotation = aim((0.0, 0.0, 0.0), normal)
    return board(size, center, material, part, rotation)


def point_at_z(
    start: tuple[float, float, float],
    end: tuple[float, float, float],
    z: float,
) -> tuple[float, float, float]:
    """Point on the segment from ``start`` to ``end`` at height ``z``."""
    span = end[2] - start[2]
    if abs(span) < 1e-6:
        raise ValueError("segment has no vertical span")
    t = (z - start[2]) / span
    return tuple(start[i] + (end[i] - start[i]) * t for i in range(3))


def rocker(
    y: float,
    x0: float,
    x1: float,
    radius: float,
    section: tuple[float, float],
    material: pf.Material,
    n: int = 8,
) -> list[pf.MeshObject]:
    """Arc in the XZ plane. The circle is centered at z=radius, so it touches z=0 at x=0."""
    if abs(x0) >= radius or abs(x1) >= radius:
        raise ValueError("rocker ends must lie inside the circle")
    points = []
    for step in range(n):
        x = x0 + (x1 - x0) * step / (n - 1)
        z = radius - math.sqrt(radius * radius - x * x) + section[0] * 0.5
        points.append((x, y, z))
    return chain(points, material, "leg_base", section=section, overlap=section[0] * 0.5)


def four_legs(
    rng: pf.RNG,
    depth: float,
    width: float,
    leg_height: float,
    material: pf.Material,
) -> pf.MeshObject:
    base = furniture_bases.base_straight_rand(
        rng,
        dimensions=(depth * 0.86, width * 0.86, leg_height),
        material=material,
        leg_diameter_range=(0.028, 0.040),
        leg_placement_bottom_scale=1.0,
        leg_inset_range=(0.02, 0.045),
        leg_placement_top_scale=1.0,
        stretcher_increment=1,
        stretcher_relative_pos=0.62,
    ).mesh
    spray.write_spray_part(base, "leg_base")
    return base


def dining_with_back(
    rng_style: pf.RNG,
    rng_back: pf.RNG,
    rng_seat: pf.RNG,
    depth: float,
    width: float,
    elevation: float,
    thickness: float,
    back_height: float,
    material: pf.Material,
) -> pf.MeshObject:
    """Seat pan plus a slatted or solid back. Front edge stays flat so legs can meet it."""
    style = pf.control.choice(rng_style, [("slat", 1.0), ("solid", 1.0)])
    back_fn = {"slat": _dining_slat_back, "solid": _dining_solid_back}[style]
    back_sink = thickness * 0.5
    back_geo, back_round = back_fn(
        rng_back, width * 0.92, back_height + back_sink, material, material
    )
    return _dining_seat_with_back(
        rng_seat,
        (depth, width, elevation),
        thickness,
        0.04 * depth,
        0.06 * depth,
        0.0,
        material,
        back_geo,
        back_round,
        back_height + back_sink,
        back_sink,
        0.12,
        0.0,
        spray_tags=True,
    )


def round_seat(
    material: pf.Material,
    radius: float,
    thickness: float,
    seat_height: float,
) -> pf.MeshObject:
    """Round pad whose highest vertex sits at ``seat_height``. ``radius`` is the built diameter."""
    seat = chair_seat_round(
        thickness=thickness, radius=radius, cap_radius=2.4, bevel_factor=0.012
    ).mesh
    pf.ops.object.set_material(
        seat, surface=material.surface, displacement=material.displacement
    )
    spray.write_spray_part(seat, "seat")
    z_max = vertex_bounds(seat)[5]
    pf.ops.object.set_transform(seat, location=(0.0, 0.0, seat_height - z_max))
    return seat

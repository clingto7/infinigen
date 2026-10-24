"""Shared solids for D-tier spray shells.

Furniture boards stay in ``assemble`` and ``c/*/parts``. Shells are closed
meshes cut with the exact boolean solver. Cutters are removed afterwards so a
saved blend only contains the workpiece. Z is up. Vertices are stored in the
mesh, not in the object transform, because the probe reads local coordinates.
"""

import bmesh
import bpy
import mathutils
import procfunc as pf

from infinigen2.util import spray
from infinigen2.workpieces.assemble import hard_material, join_tagged
from infinigen2.workpieces.common import Category, register

__all__ = [
    "Category",
    "aim_z",
    "box",
    "cut",
    "cylinder",
    "finish",
    "flange_ring",
    "frustum",
    "fuse",
    "hard_material",
    "pose",
    "register",
    "rest_on_ground",
    "sphere",
    "tag",
]


def _realize(geometry) -> pf.MeshObject:
    return pf.nodes.to_mesh_object(geometry)


def box(
    size: tuple[float, float, float],
    center: tuple[float, float, float],
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> pf.MeshObject:
    """Axis-aligned box until ``rotation``, then moved so ``center`` is its center."""
    cube = pf.nodes.geo.mesh_cube(size=size)
    placed = pf.nodes.geo.transform(cube.mesh, translation=center, rotation=rotation)
    return _realize(placed)


def cylinder(
    radius: float,
    depth: float,
    center: tuple[float, float, float],
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    vertices: int = 48,
) -> pf.MeshObject:
    """Cylinder along local Z, then rotated and moved. ``depth`` is the full length."""
    solid = pf.nodes.geo.mesh_cylinder(
        vertices=vertices, radius=radius, depth=depth, fill_type="NGON"
    )
    placed = pf.nodes.geo.transform(solid.mesh, translation=center, rotation=rotation)
    return _realize(placed)


def sphere(
    radii: tuple[float, float, float],
    center: tuple[float, float, float],
    segments: int = 36,
    rings: int = 18,
) -> pf.MeshObject:
    """Ellipsoid with the given radii, centered at ``center``."""
    solid = pf.nodes.geo.mesh_uv_sphere(segments=segments, rings=rings, radius=1.0)
    scaled = pf.nodes.geo.transform(solid.mesh, scale=radii)
    placed = pf.nodes.geo.transform(scaled, translation=center)
    return _realize(placed)


def frustum(
    radius_bottom: float,
    radius_top: float,
    depth: float,
    center: tuple[float, float, float],
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    vertices: int = 48,
    side_segments: int = 8,
) -> pf.MeshObject:
    """Tapered cylinder along local Z, then rotated and moved. ``depth`` is the full length."""
    solid = pf.nodes.geo.mesh_cone(
        vertices=vertices,
        side_segments=side_segments,
        radius_top=radius_top,
        radius_bottom=radius_bottom,
        depth=depth,
        fill_type="NGON",
    )
    # Mesh Cone sits on z = 0; shift to the center, then rotate like cylinder.
    centered = pf.nodes.geo.transform(solid.mesh, translation=(0.0, 0.0, -depth * 0.5))
    placed = pf.nodes.geo.transform(centered, translation=center, rotation=rotation)
    return _realize(placed)


def aim_z(direction: tuple[float, float, float]) -> tuple[float, float, float]:
    """Euler XYZ that sends the local Z axis of a cylinder onto ``direction``."""
    target = mathutils.Vector(direction)
    if target.length < 1e-9:
        return (0.0, 0.0, 0.0)
    euler = mathutils.Vector((0.0, 0.0, 1.0)).rotation_difference(target.normalized()).to_euler("XYZ")
    return (float(euler.x), float(euler.y), float(euler.z))


def flange_ring(
    outer_r: float,
    hole_r: float,
    thick: float,
    center: tuple[float, float, float],
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
    vertices: int = 40,
) -> pf.MeshObject:
    """Annular disc whose hole is coaxial with the given rotation."""
    ring = cylinder(outer_r, thick, center=center, rotation=rotation, vertices=vertices)
    return cut(
        ring,
        cylinder(
            hole_r,
            thick + 0.04,
            center=center,
            rotation=rotation,
            vertices=max(24, vertices - 8),
        ),
        what="flange bore",
    )


def _require_solid(obj: pf.MeshObject, what: str) -> pf.MeshObject:
    data = obj.item().data
    if len(data.polygons) < 4:
        raise RuntimeError(f"{what} produced no solid faces")
    return obj


def discard(obj: pf.MeshObject) -> None:
    """Unlink a cutter so it is not saved with the workpiece."""
    item = obj.item()
    data = item.data
    bpy.data.objects.remove(item, do_unlink=True)
    if data is not None and data.users == 0:
        bpy.data.meshes.remove(data)


def _weld(host: pf.MeshObject) -> None:
    # Boolean seams leave coincident vertices. 0.1 mm does not close an 8 mm wall.
    pf.ops.modifier.weld(host, merge_threshold=1e-4, mode="CONNECTED")


def cut(host: pf.MeshObject, cutter: pf.MeshObject, *, what: str = "difference") -> pf.MeshObject:
    pf.ops.modifier.boolean_difference(host, cutter, fast=False, hole_tolerant=True)
    discard(cutter)
    _weld(host)
    return _require_solid(host, what)


def fuse(host: pf.MeshObject, piece: pf.MeshObject, *, what: str = "union") -> pf.MeshObject:
    pf.ops.modifier.boolean_union(host, piece, fast=False, hole_tolerant=True)
    discard(piece)
    _weld(host)
    return _require_solid(host, what)


def _outward_normals(obj: pf.MeshObject) -> None:
    data = obj.item().data
    bm = bmesh.new()
    try:
        bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.to_mesh(data)
        data.update()
    finally:
        bm.free()


def tag(obj: pf.MeshObject, material: pf.Material, part: str) -> pf.MeshObject:
    _outward_normals(obj)
    pf.ops.object.set_material(
        obj, surface=material.surface, displacement=material.displacement
    )
    spray.write_spray_part(obj, part)
    return obj


def finish(parts: list[pf.MeshObject]) -> pf.MeshObject:
    return join_tagged(parts)


def pose(
    obj: pf.MeshObject,
    *,
    location: tuple[float, float, float] = (0.0, 0.0, 0.0),
    rotation: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> pf.MeshObject:
    """Bake a rigid move into vertex coordinates and leave the object at the origin."""
    matrix = mathutils.Euler(rotation, "XYZ").to_matrix().to_4x4()
    matrix.translation = mathutils.Vector(location)
    data = obj.item().data
    data.transform(matrix)
    data.update()
    return obj


def rest_on_ground(obj: pf.MeshObject) -> pf.MeshObject:
    """Shift the mesh so its lowest vertex sits on z = 0."""
    low = min(vertex.co.z for vertex in obj.item().data.vertices)
    if abs(low) < 1e-6:
        return obj
    return pose(obj, location=(0.0, 0.0, -low))

"""Shared placement helpers for workpieces built from existing parts.

Geometry functions stay in the original modules. Callers here only size a
part, tag it, and join it. ``stretcher_relative_pos`` on a straight base runs
from 0 at the top of the legs to 1 on the floor.
"""

import procfunc as pf

from infinigen2.objects import storage, table
from infinigen2.shaders.functionality_lists import furniture_material_rand
from infinigen2.util import mesh, spray

# Local codes written by storage._shelf_geometry.
_SHELF_PARTS = {0: "carcass", 1: "back_panel", 2: "shelf", 3: "shelf"}


def hard_material(rng: pf.RNG) -> pf.Material:
    return furniture_material_rand(rng, pf.nodes.shader.coord().uv)


def stretcher_relative_for_height(leg_height: float, height_from_floor: float) -> float:
    """Rail height as ``base_straight_rand``'s stretcher parameter."""
    if leg_height <= 1e-6:
        raise ValueError("leg_height must be positive")
    relative = 1.0 - height_from_floor / leg_height
    return min(0.92, max(0.08, relative))


def support_loop(size: tuple[float, float, float]) -> tuple[float, float, float]:
    corner = min(0.02, 0.08 * min(size[0], size[1]))
    edge = min(0.006, 0.2 * size[2])
    return (corner, corner, edge)


def tagged_slab(
    size: tuple[float, float, float],
    material: pf.Material,
    part: str,
) -> pf.MeshObject:
    """XY-centered slab occupying z in [0, size[2]]."""
    geo = table.table_top(size=size, support_loop_offset=support_loop(size))
    obj = pf.nodes.to_mesh_object(geo)
    pf.ops.object.set_material(
        obj, surface=material.surface, displacement=material.displacement
    )
    spray.write_spray_part(obj, part)
    return obj


def tagged_box(
    size: tuple[float, float, float],
    location: tuple[float, float, float],
    material: pf.Material,
    part: str,
    anchor: tuple[float, float, float] = (0.0, 0.0, 0.0),
) -> pf.MeshObject:
    """Box with ``location`` at ``anchor``. Anchor 0 is the min corner."""
    geo = mesh.metric_box_uv(mesh.box(size=size, location=location, anchor=anchor))
    obj = pf.nodes.to_mesh_object(geo)
    pf.ops.object.set_material(
        obj, surface=material.surface, displacement=material.displacement
    )
    spray.write_spray_part(obj, part)
    return obj


def vertex_bounds(obj: pf.MeshObject) -> tuple[float, float, float, float, float, float]:
    item = obj.item()
    matrix = item.matrix_world
    coords = [matrix @ vertex.co for vertex in item.data.vertices]
    xs = [co.x for co in coords]
    ys = [co.y for co in coords]
    zs = [co.z for co in coords]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def open_bay(
    rng: pf.RNG,
    dimensions: tuple[float, float, float],
    n_spaces_y: int | None = None,
    n_spaces_z: int | None = None,
) -> pf.MeshObject:
    """Open cell shelf. dimensions are depth, width, height; min corner at the origin."""
    bay = storage.storage_cell_shelf_rand(
        rng,
        dimensions=pf.Vector(dimensions),
        n_spaces_y=n_spaces_y,
        n_spaces_z=n_spaces_z,
        spray_tags=True,
    ).mesh
    spray.remap_spray_part(bay, _SHELF_PARTS)
    return bay


def adopt_storage(mesh: pf.MeshObject) -> pf.MeshObject:
    """Rewrite a storage generator's local part codes into the shared vocabulary."""
    spray.remap_spray_part(mesh, spray.REMOTE_STORAGE_PARTS)
    return mesh


def fronted_bay(
    rng: pf.RNG,
    dimensions: tuple[float, float, float],
    front_style: str,
    n_spaces_y: int | None = 1,
    n_spaces_z: int | None = None,
) -> pf.MeshObject:
    """Door or drawer cabinet. The front slab is inside the given depth."""
    bay = storage.storage_composite_rand(
        rng,
        dimensions=pf.Vector(dimensions),
        n_spaces_y=n_spaces_y,
        n_spaces_z=n_spaces_z,
        front_style=front_style,
        spray_tags=True,
    ).mesh
    return adopt_storage(bay)


def place_row(bays: list[tuple[pf.MeshObject, float]]) -> pf.MeshObject:
    """Abut min-corner cabinets along +Y. Each width is that cabinet's Y size."""
    placed = []
    cursor = 0.0
    for bay, width in bays:
        pf.ops.object.set_transform(bay, location=(0.0, cursor, 0.0))
        placed.append(bay)
        cursor += width
    return join_tagged(placed)


def place_stack(
    lower: pf.MeshObject, upper: pf.MeshObject, lower_height: float
) -> pf.MeshObject:
    """Sit ``upper`` on ``lower``. Both are min-corner cabinets of the same footprint."""
    pf.ops.object.set_transform(upper, location=(0.0, 0.0, lower_height))
    return join_tagged([lower, upper])


def join_tagged(
    parts: list[pf.MeshObject], subdiv_levels: int | None = None
) -> pf.MeshObject:
    for part in parts:
        if not spray.has_spray_part(part):
            raise RuntimeError("refusing to join a part that has no spray_part")
    host = parts[0]
    for part in parts[1:]:
        pf.ops.object.join(host, part)
    spray.write_spray_target(host)
    if subdiv_levels is not None:
        pf.ops.modifier.subdivide_surface(host, levels=subdiv_levels, _skip_apply=True)
    return host

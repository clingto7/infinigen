"""Experimental fixed-structure workpiece entrances for Spraybot sampling.

The returned mesh carries FACE attributes ``spray_part`` (integer part type)
and ``spray_target`` (boolean candidate paint surface). Target membership is a
generation-side proposal; reachability and the actual coating task still need
review before a category is accepted.
"""

from typing import NamedTuple

import bmesh
import procfunc as pf

from infinigen2.objects import chair, door, storage, vase


CATEGORY_IDS = (
    "slat_back_chair",
    "open_cell_shelf",
    "opaque_panel_door",
    "cup_body_candidate",
)


class WorkpieceResult(NamedTuple):
    mesh: pf.MeshObject
    category_id: str
    part_legend: dict[int, str]
    removed_degenerate_faces: int


def _remove_degenerate_faces(mesh: pf.MeshObject) -> int:
    """Remove tiny source triangles before they reach trajectory geometry."""
    data = mesh.item().data
    bm = bmesh.new()
    try:
        bm.from_mesh(data)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        bad = [face for face in bm.faces if face.calc_area() < 1e-7]
        if bad:
            bmesh.ops.delete(bm, geom=bad, context="FACES_ONLY")
            loose_edges = [edge for edge in bm.edges if not edge.link_faces]
            if loose_edges:
                bmesh.ops.delete(bm, geom=loose_edges, context="EDGES")
            bm.to_mesh(data)
            data.update()
        return len(bad)
    finally:
        bm.free()


def generate_workpiece(category_id: str, rng: pf.RNG) -> WorkpieceResult:
    """Generate one instance of a fixed structural type from ``rng``."""
    if category_id == "slat_back_chair":
        result = chair.chair_dining_rand(
            rng, back_style="slat", base_style="straight", spray_tags=True
        )
        legend = {0: "seat", 1: "slat_back", 2: "straight_base"}
    elif category_id == "open_cell_shelf":
        rng_grid, rng_shelf = rng.spawn(2)
        result = storage.storage_cell_shelf_rand(
            rng_shelf,
            n_spaces_y=pf.random.randint(rng_grid, 2, 5),
            n_spaces_z=pf.random.randint(rng_grid, 2, 5),
            back_width=0.02,
            spray_tags=True,
        )
        legend = {
            0: "outer_frame",
            1: "back_panel",
            2: "horizontal_divider",
            3: "vertical_divider",
        }
    elif category_id == "opaque_panel_door":
        result = door.door_body_rand(rng, spray_tags=True)
        legend = {0: "frame", 1: "recessed_panel"}
    elif category_id == "cup_body_candidate":
        # The mesh is ready for structural review; a real cup coating task is
        # deliberately not assumed here.
        result = vase.cup_rand(rng, spray_tags=True)
        legend = {0: "cup_body"}
    else:
        raise ValueError(f"Unknown Spraybot category: {category_id}")
    removed = (
        _remove_degenerate_faces(result.mesh)
        if category_id == "slat_back_chair"
        else 0
    )
    return WorkpieceResult(result.mesh, category_id, legend, removed)

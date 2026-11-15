"""Shared result type and registry for the per-category workpiece entries.

Geometry stays in the original generators. A category module only locks
branches, asks for spray tags, and declares which part names may appear.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import NamedTuple

import bmesh
import procfunc as pf

from infinigen2.util import spray


class Category(NamedTuple):
    category_id: str
    code: str
    family: str
    criterion: str
    build: Callable[[pf.RNG], pf.MeshObject | BuiltWorkpiece]
    allowed_parts: frozenset[str]
    remove_degenerate: bool = True
    scale_range: tuple[float, float] | None = None


class BuiltWorkpiece(NamedTuple):
    """Mesh plus optional generation-time data supplied by a native generator."""

    mesh: pf.MeshObject
    structure_priors: dict[str, object] | None = None


class WorkpieceResult(NamedTuple):
    mesh: pf.MeshObject
    category_id: str
    part_legend: dict[int, str]
    removed_degenerate_faces: int
    structure_priors: dict[str, object] | None = None


REGISTRY: dict[str, Category] = {}


def register(category: Category) -> Category:
    if category.category_id in REGISTRY:
        raise ValueError(f"Duplicate workpiece category: {category.category_id}")
    REGISTRY[category.category_id] = category
    return category


def _remove_degenerate_faces(mesh: pf.MeshObject) -> int:
    """Drop triangles under 1e-7 area. Same cleanup as objects.spraybot."""
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


def generate(category_id: str, rng: pf.RNG, *, record_parameters: bool = False) -> WorkpieceResult:
    try:
        category = REGISTRY[category_id]
    except KeyError:
        known = ", ".join(REGISTRY) or "(none registered)"
        raise ValueError(f"Unknown workpiece category: {category_id}; known: {known}")
    construction_record = None
    if record_parameters and category_id not in {"car_bumper", "opus_chair", "infinigen_chair"}:
        from infinigen2.util.construction_record import ConstructionRecorder

        with ConstructionRecorder() as recorder:
            built = category.build(rng)
        construction_record = recorder.payload()
    else:
        built = category.build(rng)
    if isinstance(built, BuiltWorkpiece):
        mesh = built.mesh
        structure_priors = built.structure_priors
    else:
        mesh = built
        structure_priors = None
    if construction_record is not None:
        # Preserve native factory keys consumed by existing trajectory rules.
        structure_priors = dict(structure_priors or {})
        structure_priors["construction_record"] = construction_record
    if category.scale_range is not None:
        scale = pf.random.uniform(rng, *category.scale_range)
        data = mesh.item().data
        for vertex in data.vertices:
            vertex.co *= scale
        data.update()
        if structure_priors is not None:
            structure_priors["post_build_uniform_scale"] = float(scale)
    removed = _remove_degenerate_faces(mesh) if category.remove_degenerate else 0
    spray.ensure_spray_target_reason(mesh)
    spray.write_geometry_accessibility(mesh)
    legend = spray.present_part_legend(mesh)
    unexpected = set(legend.values()) - category.allowed_parts
    if unexpected:
        raise RuntimeError(f"{category_id} produced unexpected parts: {sorted(unexpected)}")
    if not legend:
        raise RuntimeError(f"{category_id} produced no spray_part faces")
    return WorkpieceResult(mesh, category_id, legend, removed, structure_priors)

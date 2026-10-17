"""Experimental fixed-structure workpiece entrances for Spraybot sampling.

The returned mesh carries FACE attributes ``spray_part`` (integer part type)
and ``spray_target`` (boolean candidate paint surface). Target membership is a
generation-side proposal; reachability and the actual coating task still need
review before a category is accepted.

Structure forks inside a generator are either pinned under ``spray_tags=True``
(chair.py / tap.py / bed.py precedent) or deliberately kept as instance
variation; see docs/spraybot/ for the per-category legends and review status.
"""

from collections.abc import Callable
from typing import NamedTuple

import bmesh
import procfunc as pf

from infinigen2.objects import (
    bathtub,
    bathroom_hardware,
    bed,
    bowl,
    ceiling_light,
    chair,
    cushion,
    desk,
    door,
    drawer,
    furniture_bases,
    handles,
    lamp,
    monitor,
    rug,
    sink,
    sofa,
    storage,
    table,
    tap,
    toilet,
    vase,
    wall_art,
    window,
)


def _slat_back_chair(rng: pf.RNG):
    return chair.chair_dining_rand(
        rng, back_style="slat", base_style="straight", spray_tags=True
    )


def _open_cell_shelf(rng: pf.RNG):
    rng_grid, rng_shelf = rng.spawn(2)
    return storage.storage_cell_shelf_rand(
        rng_shelf,
        n_spaces_y=pf.random.randint(rng_grid, 2, 5),
        n_spaces_z=pf.random.randint(rng_grid, 2, 5),
        back_width=0.02,
        spray_tags=True,
    )


LEGACY_BUILDERS: dict[str, Callable[[pf.RNG], object]] = {
    # seating / storage precedents
    "slat_back_chair": _slat_back_chair,
    "open_cell_shelf": _open_cell_shelf,
    "storage_cabinet_single_door": lambda rng: storage.storage_cabinet_with_door_rand(
        rng, spray_tags=True
    ),
    "storage_drawer_cabinet": lambda rng: storage.storage_drawer_door_rand(
        rng, spray_tags=True
    ),
    "storage_shelf_on_base": lambda rng: storage.storage_cabinet_with_base_rand(
        rng, spray_tags=True
    ),
    "drawer_box": lambda rng: drawer.drawer_rand(rng, spray_tags=True),
    # doors / windows
    "door_with_handle": lambda rng: door.door_with_handle_rand(rng, spray_tags=True),
    "door_double": lambda rng: door.door_double_rand(rng, spray_tags=True),
    "window_rectangular": lambda rng: window.window_rectangular_composite_rand(
        rng, spray_tags=True
    ),
    "window_curved": lambda rng: window.window_curved_rand(rng, spray_tags=True),
    "curtain": lambda rng: window.curtain_rand(rng, spray_tags=True),
    # bathroom & door hardware
    "hardware_hook": lambda rng: bathroom_hardware.hardware_hook_rand(
        rng, spray_tags=True
    ),
    "hardware_towel_single": lambda rng: bathroom_hardware.hardware_holder_rand(
        rng, spray_tags=True
    ),
    "hardware_towel_double": lambda rng: bathroom_hardware.hardware_bar_rand(
        rng, spray_tags=True
    ),
    "hardware_ring": lambda rng: bathroom_hardware.hardware_ring_rand(
        rng, spray_tags=True
    ),
    "handle_lever": lambda rng: handles.handle_lever_rand(rng, spray_tags=True),
    "handle_pull_bar": lambda rng: handles.handle_bar_pull_rand(rng, spray_tags=True),
    "handle_pull_curved": lambda rng: handles.handle_curved_pull_rand(
        rng, spray_tags=True
    ),
    "handle_knob": lambda rng: handles.handle_knob_rand(rng, spray_tags=True),
    # lamps
    "ceiling_light": lambda rng: ceiling_light.light_ceiling_rand(
        rng, spray_tags=True
    ),
    "desk_lamp": lambda rng: lamp.lamp_desk_rand(rng, spray_tags=True),
    "pendant_lamp": lambda rng: lamp.lamp_ceiling_shade_rand(rng, spray_tags=True),
    "floor_lamp": lambda rng: lamp.lamp_floor_rand(rng, spray_tags=True),
    # bathroom fixtures
    "bathtub": lambda rng: bathtub.bathtub_rand(rng, spray_tags=True),
    "bathroom_sink": lambda rng: bathtub.sink_bathroom_rand(rng, spray_tags=True),
    "counter_sink": lambda rng: sink.sink_rand(rng, spray_tags=True),
    "toilet": lambda rng: toilet.toilet_rand(rng, spray_tags=True),
    "tap": lambda rng: tap.tap_rand(rng, spray_tags=True),
    # vessels
    "cup_body_candidate": lambda rng: vase.cup_rand(rng, spray_tags=True),
    "bowl": lambda rng: bowl.bowl_rand(rng, spray_tags=True),
    "vase": lambda rng: vase.vase_rand(rng, spray_tags=True),
    # soft furnishings / decor / appliances
    "pillow": lambda rng: cushion.cushion_throw_pillow_rand(rng, spray_tags=True),
    "rug": lambda rng: rug.rug_rand(rng, spray_tags=True),
    "wall_frame": lambda rng: wall_art.wall_art_rand(rng, spray_tags=True),
    "monitor": lambda rng: monitor.monitor_rand(rng, spray_tags=True),
    "bed": lambda rng: bed.bed_rand(rng, spray_tags=True),
    "sofa": lambda rng: sofa.sofa_rand(rng, spray_tags=True),
    # table bases (independent spray parts)
    "table_base_straight": lambda rng: furniture_bases.base_straight_rand(
        rng, spray_tags=True
    ),
    "table_base_pedestal": lambda rng: furniture_bases.base_pedestal_rand(
        rng, spray_tags=True
    ),
    "table_base_square": lambda rng: furniture_bases.base_square_rand(
        rng, spray_tags=True
    ),
}

LEGACY_LEGENDS: dict[str, dict[int, str]] = {
    "slat_back_chair": {0: "seat", 1: "slat_back", 2: "straight_base"},
    "open_cell_shelf": {
        0: "outer_frame",
        1: "back_panel",
        2: "horizontal_divider",
        3: "vertical_divider",
    },
    "storage_cabinet_single_door": {
        0: "outer_frame",
        1: "back_panel",
        2: "horizontal_divider",
        3: "vertical_divider",
        4: "door_frame",
        5: "door_panel",
        6: "door_handle",
    },
    "storage_drawer_cabinet": {
        0: "outer_frame",
        1: "back_panel",
        2: "horizontal_divider",
        3: "vertical_divider",
        4: "door_frame",
        5: "door_panel",
        6: "door_handle",
        7: "drawer",
    },
    "storage_shelf_on_base": {
        0: "outer_frame",
        1: "back_panel",
        2: "horizontal_divider",
        3: "vertical_divider",
        4: "base",
    },
    "drawer_box": {0: "drawer_box", 1: "front_panel", 2: "handle"},
    "door_with_handle": {0: "frame", 1: "panel", 2: "handle"},
    "door_double": {0: "frame", 1: "panel", 2: "handle"},
    "window_rectangular": {0: "frame", 1: "glass_pane"},
    "window_curved": {0: "frame", 1: "glass_pane"},
    "curtain": {0: "fabric_panels", 1: "rail_frame"},
    "hardware_hook": {0: "wall_attachment", 1: "hook"},
    "hardware_towel_single": {0: "wall_attachment", 1: "rail"},
    "hardware_towel_double": {0: "wall_attachment", 1: "rail"},
    "hardware_ring": {0: "wall_attachment", 1: "ring"},
    "handle_lever": {0: "rose_plate", 1: "lever", 2: "lock_button"},
    "handle_pull_bar": {0: "grip", 1: "standoff_posts"},
    "handle_pull_curved": {0: "curved_tube"},
    "handle_knob": {0: "base_disc", 1: "stem", 2: "head"},
    "ceiling_light": {0: "bulb_diffuser", 1: "frame_rim"},
    "desk_lamp": {0: "base", 1: "head"},
    "pendant_lamp": {0: "ceiling_mount", 1: "head"},
    "floor_lamp": {0: "base", 1: "head"},
    "bathtub": {0: "shell", 1: "drain"},
    "bathroom_sink": {0: "shell", 1: "drain"},
    "counter_sink": {
        0: "rim",
        1: "bowl_bottom",
        2: "drain_wall",
        3: "drain_ring",
        4: "bowl_cap",
        5: "bowl_lip",
    },
    "toilet": {0: "bowl", 1: "tank"},
    "tap": {0: "base", 1: "mount", 2: "handle", 3: "spout"},
    "cup_body_candidate": {0: "cup_body"},
    "bowl": {0: "bowl_body"},
    "vase": {0: "vase_body"},
    "pillow": {0: "body", 1: "piping"},
    "rug": {0: "rug_body"},
    "wall_frame": {0: "panel", 1: "frame"},
    "monitor": {0: "body", 1: "stand"},
    "bed": {0: "bed_frame_assembly", 1: "mattress"},
    "sofa": {0: "cushions_and_base_board", 1: "back_board", 2: "arms"},
    "table_base_straight": {0: "base"},
    "table_base_pedestal": {0: "base"},
    "table_base_square": {0: "base"},
}

def _straight_leg_desk(rng: pf.RNG):
    return desk.desk_tabletop_rand(rng, spray_tags=True)


def _legged_solid_headboard_bed(rng: pf.RNG):
    # bed_rand(spray_tags=True) pins the base to legs, the headboard to solid,
    # and removes the footboard branch. It also keeps the mattress as a
    # non-target part of the complete workpiece.
    return bed.bed_rand(rng, spray_tags=True)


def _rectangular_window_frame(rng: pf.RNG):
    return window.window_rectangular_rand(
        rng,
        include_glass_pane=False,
        include_portal=False,
        shutter=False,
        spray_tags=True,
    )


def _solid_back_chair(rng: pf.RNG):
    return chair.chair_dining_rand(
        rng, back_style="solid", base_style="straight", spray_tags=True
    )


def _wheeled_dining_chair(rng: pf.RNG):
    return chair.chair_dining_rand(
        rng, back_style="slat", base_style="wheeled", spray_tags=True
    )


def _rectangular_dining_table(rng: pf.RNG):
    return table.table_dining_rand(rng, spray_tags=True)


def _round_dining_table(rng: pf.RNG):
    return table.table_dining_circular_rand(rng, spray_tags=True)


# Only accepted furniture/door/window workpieces are formally exposed. The
# legacy registry remains available inside this module for historical probes
# and future migration, but is not part of CATEGORY_IDS.
BUILDERS: dict[str, Callable[[pf.RNG], object]] = {
    "slat_back_chair": LEGACY_BUILDERS["slat_back_chair"],
    "open_cell_shelf": LEGACY_BUILDERS["open_cell_shelf"],
    "storage_cabinet_single_door": LEGACY_BUILDERS["storage_cabinet_single_door"],
    "storage_drawer_cabinet": LEGACY_BUILDERS["storage_drawer_cabinet"],
    "storage_shelf_on_base": LEGACY_BUILDERS["storage_shelf_on_base"],
    "door_with_handle": LEGACY_BUILDERS["door_with_handle"],
    "door_double": LEGACY_BUILDERS["door_double"],
    "straight_leg_desk": _straight_leg_desk,
    "legged_solid_headboard_bed": _legged_solid_headboard_bed,
    "window_rectangular_frame": _rectangular_window_frame,
    "solid_back_chair": _solid_back_chair,
    "wheeled_dining_chair": _wheeled_dining_chair,
    "rectangular_dining_table": _rectangular_dining_table,
    "round_dining_table": _round_dining_table,
}

LEGENDS: dict[str, dict[int, str]] = {
    category: LEGACY_LEGENDS[category]
    for category in (
        "slat_back_chair",
        "open_cell_shelf",
        "storage_cabinet_single_door",
        "storage_drawer_cabinet",
        "storage_shelf_on_base",
        "door_with_handle",
        "door_double",
    )
}
LEGENDS.update(
    {
        "straight_leg_desk": {0: "tabletop", 1: "straight_base"},
        "legged_solid_headboard_bed": {0: "bed_frame", 1: "mattress"},
        "window_rectangular_frame": {0: "frame"},
        "solid_back_chair": {0: "seat", 1: "solid_back", 2: "straight_base"},
        "wheeled_dining_chair": {0: "seat", 1: "slat_back", 2: "wheeled_base"},
        "rectangular_dining_table": {0: "tabletop", 1: "base"},
        "round_dining_table": {0: "tabletop", 1: "base"},
    }
)

CATEGORY_IDS = tuple(BUILDERS)

assert set(BUILDERS) == set(LEGENDS), "builder/legend registry mismatch"


class WorkpieceResult(NamedTuple):
    mesh: pf.MeshObject
    category_id: str
    part_legend: dict[int, str]
    removed_degenerate_faces: int
    structure_priors: dict[str, object] | None = None


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
    builder = BUILDERS.get(category_id)
    if builder is None:
        raise ValueError(f"Unknown Spraybot category: {category_id}")
    result = builder(rng)
    mesh_object = getattr(result, "mesh", None)
    if mesh_object is None:
        raise TypeError(f"Builder for {category_id} returned no mesh field")
    # Every formally exposed workpiece must reach downstream tessellation with
    # non-degenerate triangles. The old registry only needed this for the
    # chair precedent; furniture assemblies can produce the same artifact.
    removed = _remove_degenerate_faces(mesh_object)
    return WorkpieceResult(mesh_object, category_id, LEGENDS[category_id], removed, None)

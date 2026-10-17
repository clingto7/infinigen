# Spraybot compatibility contract

The Infinigen fork owns workpiece generation and generation-side semantic data.
Spraybot owns trajectory rules, PaintDS writing, and training-format conversion.
The repositories communicate through exported data, not Python imports.

## Required mesh export

A generated workpiece export contains:

- `vertices`: `(N, 3)` float coordinates in meters;
- `faces`: `(T, 3)` triangle indices;
- `part_id`: `(T,)` integer semantic part IDs, matching the existing Spraybot Infinigen adapter contract;
- `spray_part`: `(T,)` integer fork-native alias of `part_id`;
- `spray_target`: `(T,)` boolean target-face mask;
- optional `structure_priors`: category-specific generation-time metadata.

`part_id` is per triangle after triangulation. The category legend maps its integer
values to stable semantic names. Non-spray materials remain in the complete mesh
when needed, but their triangles must have `spray_target=False`.

## Existing Spraybot precedents

The ordinary Infinigen chair consumes per-face semantic labels plus generation-time
centerlines and back metadata. OpusChair consumes a generation record containing
leg and ornament priors. CarBumper consumes a reconstructable parameterized surface
shared by the mesh and trajectory generator. The new furniture categories may
provide optional `structure_priors` when a downstream rule needs equivalent
information; simple categories need only the mesh and semantic face data.

The current pilot exports the required mesh and label fields. A full Spraybot
adapter import test remains environment-dependent because the checked-out Spraybot
repository does not include its `hybrid_per_station` package in this workspace.

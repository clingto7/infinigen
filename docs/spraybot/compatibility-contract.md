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
- `spray_target_reason`: `(T,)` integer code explaining target inclusion/exclusion;
- optional `structure_priors`: category-specific generation-time metadata.

`part_id` is per triangle after triangulation. The category legend maps its integer
values to stable semantic names. Non-spray materials remain in the complete mesh
when needed, but their triangles must have `spray_target=False`.

## Generation-side face attributes

D-tier shell workpieces additionally carry `spray_visibility`, a per-face float
in [0, 1]: the fraction of 16 deterministic hemisphere directions around the
outward normal from which a ray escapes the solid unobstructed, computed on the
final joined mesh so self-occlusion is included. This is a geometric line-of-sight
estimate, not a binary sprayability decision and not a guarantee of trajectory,
robot, or coating feasibility. It is independent from `spray_target`; category
policy may exclude an internal surface from the coating task even when visibility
or exterior connectivity is nonzero.

The general accessibility schema describes geometry only and does not depend on
a particular spray gun or coating process. It keeps access information separate
from `spray_target`. The agreed per-face fields are:

| Field | Type / domain | Meaning |
| --- | --- | --- |
| `spray_target` | boolean, one value per face | Whether the face belongs to the coating task under that interface's task and material policy. This is independent from geometric access. For `valve_housing` and `tee_pipe`, internal cavity and bore walls are explicitly non-target, though their free space may connect to the exterior. |
| `spray_target_reason` | integer, one value per face | Stable reason code: `0=target`, `1=non_spray_material` (for example glass), `2=component_policy` (for example handles or closed drawer boxes), `3=internal_cavity` (for example valve/tee flow passages). Target faces use 0; non-target faces use a nonzero reason. |
| `geometry_accessible` | boolean, one value per face | Whether free space adjacent to the face connects to exterior free space along a path that does not cross the workpiece. This reports geometric point connectivity only; it does not decide coating intent or guarantee sprayability. |
| `max_passable_radius_m` | float in meters, one value per face | Largest spherical probe radius that can travel from exterior free space to the face along an unobstructed path. Narrow openings lower the value even when the interior connects to the exterior. |

Direction probes may support computation, but the result is face-aligned; a
small set of probe directions alone is not the face-level contract. The existing
`spray_visibility` field remains a separate line-of-sight estimate where
currently available. It does not replace connectivity or passage clearance.

The current Infinigen implementation voxelizes the final joined mesh at 96 cells
per longest bounding-box dimension. It flood-fills exterior free cells and uses
clearance-constrained grid propagation for `max_passable_radius_m`. These fields
are geometric estimates at voxel resolution: openings narrower than a voxel can
be closed by discretization, and clearances are quantized. `scripts/spraybot_validate_one.py`
checks the per-face schema and writes `face_fields.png`, which shows two views
each for target intent, exclusion reason, exterior connectivity, and passage radius. The validation
contact-sheet command also builds a per-category face-field sheet.

`spray_target` is assigned from the interface's task policy and material labels;
it is never inferred from `geometry_accessible`. For example, internal walls in
`valve_housing` and `tee_pipe` are deliberately excluded from the coating target.
Their `geometry_accessible` value can still be true because the bores open to the
exterior, and `max_passable_radius_m` still describes their geometric clearance.

## Existing Spraybot precedents

The ordinary Infinigen chair consumes per-face semantic labels plus generation-time
centerlines and back metadata. OpusChair consumes a generation record containing
leg and ornament priors. CarBumper consumes a reconstructable parameterized surface
shared by the mesh and trajectory generator. The new furniture categories may
provide optional `structure_priors` when a downstream rule needs equivalent
information; simple categories need only the mesh and semantic face data.

The `infinigen_chair` entry returns centerlines keyed by source `part_id`, transformed
into the generated mesh frame, plus the source back metadata and the rotation selected
by the source script's centerline-to-part bounds check. `opus_chair` and `car_bumper`
return their source factory records under `structure_priors`.

The current pilot exports the required mesh and label fields. A full Spraybot
adapter import test remains environment-dependent because the checked-out Spraybot
repository does not include its `hybrid_per_station` package in this workspace.

## Native Spraybot generator interfaces

The `car_bumper`, `opus_chair`, and `infinigen_chair` entries preserve their
source generators' original random structural branches. This is a one-time
integration exception for these Spraybot-native interfaces; it does not change
the project's general rule that other formal workpiece categories lock their
structural branch. The exception is recorded in [ADR 0001](../adr/0001-preserve-spraybot-native-generators.md).

## Visual inspection of face data

Every face-level field in the generation schema must be inspectable on the
generated mesh. Provide a face-colored view for target labels and geometric
openness/access data, with a legend and value scale. The inspection output should let a reviewer
compare the visualization with the same mesh geometry and verify the 20-seed
validation set before accepting an interface.

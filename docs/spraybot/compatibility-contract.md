# Spraybot compatibility contract

The Infinigen fork owns workpiece generation and generation-side semantic data.
Infinigen keeps newly reviewed interface-specific trajectory rules and PaintDS writing alongside the generator; Spraybot owns downstream training-format conversion. The three original Spraybot trajectory programs remain reference implementations (ADR 0007).
The repositories communicate through exported data, not Python imports.

## Required mesh export

A generated workpiece export contains:

- `vertices`: `(N, 3)` float coordinates in meters;
- `faces`: `(T, 3)` triangle indices;
- `spray_part`: `(T,)` integer semantic part-type IDs;
- `part_id`: native per-instance part IDs when supplied by the source (notably Chair);
  legacy exports without instance IDs may alias `spray_part`, but must identify this
  as `semantic_legacy_alias` and must not use that alias to index native centerlines;
- `spray_target`: `(T,)` boolean target-face mask;
- `spray_target_reason`: `(T,)` integer code explaining target inclusion/exclusion;
- optional `structure_priors`: category-specific generation-time metadata.

`part_id` is per triangle after triangulation. The category legend maps
`spray_part` values to stable semantic names, not native instance IDs.
Non-spray materials remain in the complete mesh
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
| `max_passable_radius_m` | deprecated legacy field | The current estimate is unreliable across workpieces. It is no longer a required export or a valid input to trajectory planning, validation gates, review decisions, or downstream consumption. Existing artifacts may still contain it for compatibility; consumers must ignore it. |

Direction probes may support computation, but the result is face-aligned; a
small set of probe directions alone is not the face-level contract. The existing
`spray_visibility` field remains a separate line-of-sight estimate where
currently available. It does not replace connectivity or passage clearance.

The current Infinigen implementation voxelizes the final joined mesh at 96 cells
per longest bounding-box dimension and flood-fills exterior free cells. The legacy
clearance propagation still may emit `max_passable_radius_m`, but its result is
unreliable and must be ignored. `scripts/spraybot_validate_one.py` checks the
active per-face schema; review should use target intent, exclusion reason, and
exterior connectivity, not passage radius.

`spray_target` is assigned from the interface's task policy and material labels;
it is never inferred from `geometry_accessible`. For example, internal walls in
`valve_housing` and `tee_pipe` are deliberately excluded from the coating target.
Their `geometry_accessible` value can still be true because the bores open to the
exterior; no usable passage-width value is currently supplied.

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

The current pilot exports mesh and label fields, but is not yet a complete
Spraybot consumption interface. The checked-out Spraybot provides a fallback
adapter that can run the Chair reader and trajectory generator locally. Its
reader expects top-level `centerlines` and `back_meta`, whereas the probe stores
them inside `structure_priors`; an explicit adapter is still required. The probe
also exports object-local vertices without the object-world transform, unlike
the production OBJ exporter. Neither the probe nor the batch face-attribute NPZ
currently persists `geometry_accessible` or `max_passable_radius_m`.

## Persisting generation parameters

The throwaway planar-arm experiment is captured on local branch
`prototype/parametric-arm-paths-20261102` (initial commit `fbc4106a`, independent
blind trial `d27e6f48`). Its contract and
reproduction command are in `scripts/prototype_parametric/README.md` on that
branch. Seven seeds passed geometric checks with one fixed consumer that imports
no Infinigen code; a deliberate 20 mm offset failed. The verified requirement is
explicit coordinate units/frame, surface domains, normals, and per-instance
triangle correspondence. This does not select a universal surface schema or
validate curved surfaces, full-chair coverage, or contact trimming. A subsequent
fresh agent received only the contract, two development packages and the output
schema/sampling requirement. Its frozen consumer passed all five held-out seeds;
removing mesh arrays and seed metadata still produced identical paths. The
blind trial used an instruction-enforced read boundary on a shared filesystem,
not an OS sandbox. GitHub Issues was disabled when capturing this experiment.

The subsequent cylinder/disk experiment is on the same prototype branch at
`07dbe428`, under `scripts/prototype_parametric/curved/`. One shared rod observer
exported both high_chair and coat_rack; a new blind consumer saw only two
high_chair development examples and passed the other twelve samples. All fourteen
instrumented meshes matched the uninstrumented vertices and triangles exactly.
The analytic cylinder is not identical to its eight-sided mesh: sampled distance
and normal differences were checked against explicit tessellation bounds, not
the planar experiment's thresholds or manufacturing tolerances. This validates
reuse of one geometric-type adapter across these categories, not arbitrary
surfaces. The plane and cylinder experiments still use separate prototype
consumers; production schema compatibility and integration remain pending.

The Bezier-origin leg experiment (`5ce3cb18` on the same prototype branch,
`scripts/prototype_parametric/bezier/`) exports initial/resolved control points
and the actual section loft used after source curve discretization. A fresh
consumer passed analytic contract checks on ten seeds, but four instances
(0, 2, 4, 19) failed geometric acceptance: twelve patches fold locally and show
opposing analytic/source mesh normals. They are explicitly not integration-ready.
Welding also requires separating surviving construction-face provenance from
overlapping geometric support in neighboring spans. Geometry acceptance must be
independent of consumer/formula correctness; small point-to-mesh distance alone
does not establish valid orientation. The source has ambient random ornament
variation; observer invariance was verified under identical global NumPy state,
not claimed as proof of production seed determinism.

`workpieces.generate(..., record_parameters=True)` executes the normal builder
while recording concrete function inputs, sampled/derived numeric values, and
object transform/assembly calls. New categories receive a `construction_record`;
the three native interfaces retain their existing factory records instead. The
batch worker and probe enable this option. The record
does not consume random numbers or fit parameters back from the mesh.

This is a source-defined construction representation, not a universal analytic
surface API. For example, an `armchair` arm is a board (dimensions and transform),
and `cabriole_leg_table` uses a polyline of straight members (points, section and
joint overlap). These must not be relabelled as Bezier control points. Opaque
procedural nodes and materials are explicitly marked `unrecorded_type`; the
versioned generator source supplies their interpretation. Object references link
construction calls, not semantic part instances. Native Chair centerlines are
ordered sampled polylines, and native Opus records contain anchors and radii;
neither is a generic full Bezier control-point/handle/sweep-frame specification.
Native records now also identify the actual `factory_seed`, which differs from
the fork's outer RNG seed. The Chair wrapper seeds the whole asset construction,
including random sampling outside the factory constructor. Blender modifier
roundoff and tessellation can still prevent byte-for-byte replay; existing Chair supplements use
the retained source NPZ rather than regenerating that geometry.

New production episodes include `structure.json` and `face_attributes.npz` beside
the OBJ. Numeric NPZ arrays follow the OBJ triangle order. JSON stores native
priors, construction records and coordinate transforms. Internal geometry uses
meters, OBJ uses millimeters. Do not apply one global conversion to dimensionless
parameters or angles. Do not overwrite native `part_id` with `spray_part`.

For the existing 23 published categories, `scripts/spraybot_recover_priors.py`
writes a separate overlay. Each episode must pass a byte-identical replay of its
original OBJ before any metadata is accepted. The overlay binds to the original
OBJ SHA-256 and episode/seed, and retains face attributes in a numeric-only NPZ.
Chair recovery uses the original cached NPZ and the original bbox-centering and
float32 conversion. Its priors remain in the source frame; `prior_to_obj_mm`
includes both the unit conversion and centering translation. Opus/CarBumper use
the original factory seed directly, not the fork's RNG-to-native-seed mapping.
The newer 20 use the frozen production source and record actual construction
parameters. Accessibility is not recomputed by this recovery tool.

The production manifest from 2026-10-27 has an empty Git commit. A supplement must
therefore ship a hashed source snapshot and environment provenance; a seed alone
is not sufficient evidence of reproducibility. Records are useful for writing
category-specific trajectory rules, but do not themselves certify trajectory
coverage, collision freedom, or a fully normalized per-part surface parameterization.

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

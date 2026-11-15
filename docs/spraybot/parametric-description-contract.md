# Parametric description delivery contract

Production schemas `spraybot.parametric.v1` and `spraybot.parametric.v2` share
the generation-time surface envelope. `v1` supports rectangular planes,
cylinder sides, and disks; `v2` additionally supports triangular planes.
The geometric description gate and the
workpiece category's manual review are separate. Passing this contract means
the interface's parametric description is ready; it does not approve the
category for production model use. Other geometric types require an explicit
versioned extension.

## Episode and coordinates

Existing OBJ, `face_attributes.npz`, and `structure.json` keep their meanings.
A ready episode adds `parametric.json`, referenced by `metadata.json` as
`parametric_file`, and sets `parametric_description_status` to `ready`.
Unsupported episodes set that status to `incomplete`; they do not advertise
parametric readiness. Earlier pilot episodes may carry
`spraybot.parametric-candidate.v1` in `parametric.candidate.json` and status
`candidate`; they remain distinguishable from ready output. Candidate `v2`
uses the same suffix with `spraybot.parametric-candidate.v2`.

OBJ vertices are in millimeters. All parametric points and length-bearing
vectors are in meters in the exported OBJ's axes and origin. The artifact
states `obj_mm_per_parametric_m=1000`. Triangle IDs are zero-based indices in
OBJ `f` line order, also the row order in `face_attributes.npz`.

Each surface's `mesh_mapping.construction_triangle_ids` identifies source
faces surviving in the final mesh. `support_triangle_ids` identifies faces
usable for geometric comparison; future welded patches may share supports.
Construction IDs have one owner. All `spray_target` rows must be mapped.
`unrepresented_non_target_triangle_ids` is exactly the complement of all
construction IDs. Non-target faces may also be described.

## Surface equations

Each part has a unique instance `id`, semantic name, and nonempty `surfaces`.
Each surface has a globally unique `id`, `type`, `geometry`, normalized
`domain`, `periodic_v`, `mesh_mapping`, and
`approximation`. Unknown types fail. All numbers must be finite. Normals and
direction axes are unit length. Approximation means mesh discrepancy, never
an assumed spraying tolerance.

The common domain is `{"u":[0,1],"v":[0,1]}`. `plane_triangle` adds
`"constraint":"u+v<=1"`; sampling outside that triangle is invalid.

Let `theta=2*pi*v`, `R(theta)=cos(theta)*radial_u+sin(theta)*radial_v`:

| Type | Point `P(u,v)` | Outward normal | `periodic_v` |
| --- | --- | --- | --- |
| `plane_rectangle` | `origin + u*U + v*V` | supplied `normal` | false |
| `plane_triangle` (v2) | `origin + u*U + v*V`, with `u+v<=1` | supplied `normal` | false |
| `cylinder_side` | `origin + u*length_m*axis + radius_m*R(theta)` | `R(theta)` | true |
| `disk` | `origin + axial_fraction*length_m*axis + u*radius_m*R(theta)` | `normal_sign*axis` | true |

For planes, `U`, `V`, and the normal are perpendicular. For rods, `axis`,
`radial_u`, and `radial_v` form a right-handed orthonormal frame.
`axial_fraction` is 0 or 1; `normal_sign` is -1 or +1. At disk center `u=0`,
the point and cap normal remain defined. Cylinder mesh is an inscribed
polygon with `angular_segments`; the analytic surface differs deliberately
from its faceted OBJ. Its distance bound covers at least
`radius_m*(1-cos(pi/angular_segments))`, and normal bound is at most
`180/angular_segments` degrees plus numerical allowance.

The v2 triangle type follows source face provenance, including the corrected
outward winding of `triangle_slab` top and bottom faces. The prototype also
tested `section_loft` and `section_disk`; they are not yet
supported by the production exporter or validator. Their introduction
requires an explicit versioned extension and final-mesh correspondence checks.

## Readiness gate

1. Capture actual parameters while building, tag source faces before joins,
   and derive final mapping from the delivered mesh.
2. Export an episode and run `scripts/spraybot_parametric_validate.py` in a
   separate process. It reads the actual OBJ, face mask, metadata, and
   description without importing generator code. It checks units, mappings,
   domains, positions, outward normals, and complete target coverage.
3. Run at least 10 deterministic seeds for the manual Web UI review, spanning
   known structural branches. The machine gate may use a larger batch when
   needed for statistical or regression evidence.
   Compare meshes and target masks with capture disabled to detect observer
   side effects.
4. Use a source-independent consumer to evaluate points and normals across
   seeds. Confirm that missing mappings, inward normals, wrong units, and
   unknown types fail.
5. Only after these checks may an interface be marked
   parametric-description ready. Existing generators remain usable while
   awaiting the gate. Category acceptance remains a separate review.

The worker applies capture to every registered `workpiece:` generator. It does
not use the certified set to decide whether capture should run. A complete
description for an uncertified interface is written as
`parametric.candidate.json`; a missing primitive mapping leaves the normal
episode intact and records `parametric_description_status=incomplete` with the
reason. The certified manifest is
`scripts/spraybot_parametric_readiness.json`; only its entries may claim
`ready` and use `parametric.json`. Adding a new interface therefore requires
only its shared primitive adapters plus the same batch gate, then one manifest
entry after evidence is complete.

The Web UI is the primary manual review surface. It must support both live
generation and loading one existing review root containing all interfaces in a
run. A review root has a manifest, interface entries, and episode
subdirectories containing the exported mesh, face attributes, metadata, and
optional parametric artifact. The selector uses `<interface-id> -
<workpiece-name>` and supports search. The UI may show historical priors as
well as the newly generated description; the machine gate remains responsible
for strict checks that a human visual review cannot prove.

The default manual sample is ten seeds per interface. Human review is recorded
once per interface in the Git-tracked project record under `reviews/interfaces/`;
issue entries refer to concrete seeds. Interface status is `developing`,
`awaiting_review`, `needs_fix`, or `ready`; a saved review becomes formal when
its record is committed. Existing `parametric_description_status=ready` in an
episode denotes the legacy machine-certified artifact, not interface readiness.
The review root keeps samples and evidence, not the authoritative conclusion. The existing
contact-sheet exporter can read the same immutable review root on demand for
reports and presentations.

For coat rack, the exported-file portion is one command:

```bash
python scripts/spraybot_parametric_gate.py <batch-directory> \
  --expect-instance-count 12 --expect-instance-count 13
```

This checks at least 20 distinct seeds, every episode's OBJ and face mask,
and samples every described surface with the source-independent consumer.
The expected instance counts cover the known three-foot and four-foot
branches. Geometry and RNG invariance with capture disabled is a separate
generator-side check; the file-only gate cannot establish it.

Run that check on radar with
`scripts/spraybot_parametric_compare_uncaptured.py <batch-directory>`. It
regenerates each exported seed without capture and compares OBJ vertices,
triangle order, `spray_target`, and `spray_part`. For prioritization only,
`scripts/spraybot_parametric_screen.py --only-incomplete` gives a one-seed
inventory of missing target faces by part; it cannot confer readiness.

## Current ready interfaces (2026-11-11)

The ready set is declared in `scripts/spraybot_mass_worker.py`. Each row below
passed a 20-seed exported-file gate, source-independent sampling, and a
20-seed capture-on/off comparison of vertices, triangle order, and target mask
on radar. Category-level manual review remains separate.

| Interface | Observed 20-seed variants | Target triangles across 20 seeds |
| --- | --- | ---: |
| `coat_rack` | 3 or 4 feet (13 / 7 seeds) | 13,860 |
| `stepped_platform` | 2-step stool, 3-step stool, 3-tier plant stand (8 / 8 / 4 seeds) | 1,872 |
| `serving_cart` | 2 or 3 tiers (13 / 7 seeds) | 14,740 |
| `park_bench` | 15 captured instances | 3,600 |
| `folding_chair` | 11 captured instances | 2,640 |
| `bunk_bed` | 18 captured instances | 4,320 |
| `crib` | 51, 53, or 55 captured instances | 12,816 |
| `four_poster_bed` | 13 captured instances | 3,120 |
| `ladder_shelf` | 6 or 7 captured instances | 1,524 |
| `high_chair` | 15 captured instances | 10,320 |
| `drafting_table` | 8 captured instances | 1,920 |
| `lounge_chair` | 22 captured instances | 5,280 |
| `tilt_out_shoe_cabinet` | 15 or 20 captured instances | 4,020 |
| `hairpin_leg_table` | 9 captured instances | 11,760 |
| `workbench` | 10 captured instances | 4,320 |
| `school_desk` | 10 captured instances | 9,120 |
| `cabriole_leg_table` | 25 captured instances | 7,920 |
| `folding_table` | 5 or 7 captured instances | 5,616 |
| `metal_shelving` | 12 or 13 captured instances | 2,964 |
| `staggered_display_shelf` | 11 captured instances | 2,640 |
| `storage_chest` | 6 or 10 captured instances | 1,824 |
| `wine_rack` | 13 or 23 captured instances | 3,960 |
| `window_casing` | 5 captured instances | 1,200 |
| `corner_shelf` (v2) | 3 or 4 triangular shelves | 808 |

Across these 24 interfaces, all 132,164 target triangles in 480 seeded
episodes have mapped surfaces. Each of the later twenty-one interfaces also passed
a seed-21 smoke test after promotion to `parametric.json` and `ready` metadata.

The exported-file validator also rejected deliberate missing target mappings,
inward normals, wrong unit conversion, and unknown surface types.

### Shared box placement tracking

Box and slab providers record generation-time local corner coordinates alongside
instance tags. The exported transform is recovered from those retained source
correspondences after placement and joins; this does not infer dimensions or
primitive type from the final mesh. The provider accepts positive uniform scale
and rigid placement, and rejects missing correspondences, reflection, shear,
nonuniform scale, and deformation outside the 2 micrometer positional tolerance.
Thin boards are checked by positional residual rather than affine coefficient
roundoff. Source dimensions and the existing typed plane schema remain authoritative.

The shared `tagged_box` and `tagged_slab` constructors now own these providers;
tabletop wrappers must not capture a second time. New complete outputs remain
candidates until machine validation and interface-level human review are complete.
`spraybot_parametric_regression.py` runs the existing exported-artifact gate and
capture-invariance checks in isolated workers, retaining per-interface results.

### Version 3: source sweep patches

Candidate schema `spraybot.parametric-candidate.v3` includes all v1/v2 types and:

- `sweep_quad`: four controls `a,b,c,d` in source winding order. On `[0,1]^2`,
  `P(u,v)=a+u(b-a)+v(d-a)+uv(a-b+c-d)`. The normal is the normalized cross
  product of the two partial derivatives. The parameter seam is not periodic.
- `sweep_cap`: a convex planar source profile, represented by its ordered
  corners and outward normal. `u` is radial fraction from the vertex-average
  center; `v` walks its boundary by equal parameter intervals per edge and is
  periodic. The domain is `[0,1]^2`, with all `u=0` values at the center.

Both store `provenance.primitive=curve_to_mesh_with_uv`, with source rail and
profile indices. The approximation kind is `source_sweep_sections`. Cap distance
bound is 2 micrometers; quad bound is `norm(a-b+c-d)/4 + 2e-6` meters, explicitly
accounting for the source quad's triangulation. These are not claims about
smooth curves or unapplied subdivision modifiers. Folded patches, nonconvex
caps, missing source addresses, and changes outside the supported placement
contract fail automatic checks. No v3 interface has been human-approved by this
implementation step.

The v3 sweep provider also supports `sweep_triangle`, a source sweep cell that
collapsed at a rotational pole or one retained triangle of a known filled cap.
Its domain is `u>=0, v>=0, u+v<=1`; three source controls define affine
interpolation and a constant outward normal. Its distance bound is 2
micrometers. A cap triangle carries `source_cap_triangulation` provenance with
the parent cap controls and three source corner indices; the independent
validator checks those indices and the delivered triangle. This handles cap
triangulation that changes during assembly without treating arbitrary final
mesh facets as source geometry.

Source addresses are stored on corners so welding does not conflate adjacent
charts. They are positive floating-point source-index parameters: evaluated
Bezier segments interpolate their control indices, and a merged pole may average
the two rail addresses. The original integer address is retained where no
interpolation occurs. Polygon profiles use their source fill-mesh indices;
explicit extrusion levels supply the round-seat cap's three section addresses.
## Ruled-grid construction provenance (v3)

`sweep_quad` can also originate from `ruled_grid_extrusion`: a sampled ruled
panel and one explicit extrusion layer. Its `provenance.grid_addresses` is
a four-by-three array of positive integer construction addresses in corner
winding order (row, curve sample, extrusion layer). Exactly two axes vary by
one step and the third is constant. The four addresses must be distinct.
The existing bilinear point, normal, mesh mapping and twist-error-bound rules
remain unchanged. This is a shared provider, not a per-interface schema.

Addresses are created by the grid/extrusion operators before assembly.
They are not inferred from the delivered OBJ. Lost lineage, bevels and cuts
are unsupported; their presence must not silently become arbitrary mesh
patches or a complete description. A primitive passing this contract does
not imply that every interface using that primitive has passed its gates.

## Curvy shell chair loft

The curvy shell chair seat uses the sampled 16×11 loft as its source. Its
side cells retain rail and profile addresses from the constructor grid and
are split along the source triangulation where the warped first row twists.
The final end ring is triangulated from the constructor's cap polygon; the
collapsed first ring has no surviving target triangles. Each surface carries
the sampled loft parameters, source face ID, and source-to-OBJ transform.
The independent validator checks source addresses, cap containment, OBJ
vertices, and outward normals before this interface can pass its gate.

## Shell construction source record

For D-tier shells, an incomplete episode may also contain
`parametric.source.json` (`spraybot.parametric-source.v1`). It records the
executed box, cylinder, sphere and frustum constructor parameters, followed
by difference, union and rigid-transform operations with source references.
Each source primitive also stores its face corners before any Boolean edit.
Its source-face triangulation is recorded as corner indices, so nonplanar
quad faces from a sampled loft can be checked against their actual piecewise
surface instead of an arbitrary plane through the first three corners.
Topology-changing constructor modifiers are followed by a new source record:
the circle-to-rectangle duct registers its solidified loft and the beveled
flange cutter; the eccentric reducer registers its solidified frustum.
Its status is `construction_only`. Face attributes surviving the Boolean
operations are exported as source primitive and source face IDs in final OBJ
triangle order. These IDs establish ownership, but do not yet provide the
trimmed domains, point and outward-normal rules. This record must never be
interpreted as a complete parametric description or count toward readiness.
`invalid_lineage_triangle_ids` lists any missing or inconsistent source IDs.
`spraybot_shell_source_validate.py` independently checks that attributed
triangles lie on their source face after recorded transforms and category
scale; a retained Blender attribute alone is not evidence of a correct match.
The current check covers source-face planes, not Boolean trim domains.

## Polygonal CSG trimmed faces (v4 candidate)

Shells with complete constructor lineage may export `csg_trimmed_face` surfaces.
The shared `construction` graph records the executed primitive constructors,
Boolean operations, joins, transforms, and post-build scale. Each surface
names a source operation and face, retains its constructor parameters, and
defines a planar point/normal rule. Boolean output contributes only closed
boundary loops in that source face's normalized `(u, v)` coordinates and OBJ
triangle support IDs. The loops are the surface domain, including holes; the
consumer samples scanlines inside them. Nonplanar source quads can use their
recorded pre-Boolean source triangulation as separate addressed surfaces.

The independent validator checks the construction graph, source controls,
final OBJ mapping, outward normals, trim edge equality, and signed domain
area. Any incomplete source attribution, open or branched trim, or face that
departs from its recorded source remains incomplete. This representation
does not substitute arbitrary final OBJ facets for source surfaces.

For shared storage cell shelves, `bevel_sources` records the constructed
pre-bevel faces and the sampled bevel width. The
`final_triangle_bevel_source_face_ids` array retains the pre-bevel face owner
in final OBJ triangle order. This is construction provenance only: bevel
creates new planes and curved strips, so the source face ID alone cannot
provide their point and normal rules. Such episodes remain `incomplete`.

When the shared `storage_cell_shelf` bevel produces convex quadrilateral
facets or planar convex caps, capture exports them as the existing v3
`sweep_quad` or `sweep_cap` form.
The same source-face bevel capture is used by the shared dining-chair seat
and back constructors; `source_constructor` identifies the executed source.
The door-body constructor retains its frame/panel face codes through assembly,
so one captured construction exports separate `door_frame` and `door_panel`
parts with the same source-face checks.
Its bilinear point and derivative-normal rules describe the evaluated bevel
construction. The facet provenance contains the pre-bevel source face ID,
its controls and the sampled bevel width; the independent validator requires
the facet controls to lie within that width of the source face. A quadrilateral
whose bilinear interpolation reverses relative to its construction triangles
exports two source-addressed `sweep_triangle` patches with the original quad
corners and split indices. The independent validator checks that lineage.
Small cap area comparisons account for source float32 and OBJ coordinate
rounding while retaining the convexity, boundary, and normal checks. Missing
source IDs and folded facets fail closed. A degenerate source face may be
omitted only when it has no final triangles; the final partition check rejects
any surviving triangle without a source patch. Complete target coverage and
the normal multi-seed gates remain necessary for an interface candidate.

The bed platform records the executed `box_with_support_loops` size, support
offset, grid resolution, and one applied subdivision level. Its corner grid
addresses are carried through that subdivision before assembly. Exported v3
patches use `support_loop_box_subdivision` provenance; the independent validator
checks the source dimensions, address steps, transform, and box envelope.

The slatted bed headboard combines two existing source constructions in one
mesh: each slat has curve sweep rail/profile addresses, and the crest rail has
support-loop box grid addresses. A face-level constructor tag selects the
corresponding capture rule before assembly. Every retained target triangle
must map back to one of those source patches.

The window constructor tags its outer frame, primary grid, and sash or shutter
subgeometry before joining glass or door hardware. Its source quads export as
v3 sweep patches with `window_frame_source` provenance: the sampled window
parameters, component ID, source face ID, and source-to-OBJ transform. The
independent validator checks the constructor fields, source frame bounds,
source split lineage, and OBJ triangle correspondence. Glass carries a
separate non-target marker through a storage-bed join, so frame-level target
assignment does not turn the pane into a paint surface.

## Native generator source patches (v3, v5, v6 candidates)

The Opus chair captures the outputs of its seat, tapered tube, and ornament
constructors before the final join. The v3 patch provenance retains the
constructor recipe, source face ID, and source-to-OBJ transform. Convex quads
use bilinear patches; strongly twisted quads and irregular source polygons
use source-corner-addressed triangles. The independent validator checks each
recipe's dimensions, source controls, and final triangle mapping. Random
choices made during ornament construction run under the factory seed so
capture-on/off comparison is repeatable.

The car bumper's v5 record keeps the generated `(s, v)` source grid, native
`BumperSurface` parameters, pre-solidify vertex normals, face IDs, and
solidify thickness. Point addresses survive shell, grille, and lip assembly.
Each exported triangle is reconstructed from source `(s, v)` and its front or
back solidify layer; a wall triangle uses both layers. The independent
validator implements the source equations separately from the generator and
checks those controls against the OBJ and face lineage. The consumer samples
the resulting source triangles with the existing sweep-triangle rule.

The Infinigen ChairFactory captures its final seat, limb, back, and arm
constructor outputs before assembly. Its v6 surface evaluator is the v3 sweep
triangle, quad, or cap evaluator. V6 moves the repeated constructor recipe
and transform to `part.source_recipe`; each surface retains its source face
address and a `recipe_scope: part` reference. The validator expands that
reference, checks constructor parameters and source geometry, and then checks
the final OBJ mapping. This avoids repeating the factory's full sampled
parameter set on every small source patch.

Native output remains a candidate until the same 20-seed geometry, independent
consumer, and capture-invariance gates pass. Manual Web review opens only
after all 100 registered interfaces complete those automatic checks.

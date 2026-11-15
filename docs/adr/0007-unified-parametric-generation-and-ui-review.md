# Unified parametric generation and UI review

All registered Workpieces and legacy Spraybot generation interfaces use one
generation-time parametric capture path. Shared construction primitives provide
typed geometry providers. An interface-level adapter may add instance
composition, semantic part identity, structural branch information, and target
face ownership, but it may not define a private geometry schema. Unsupported
primitive mappings remain explicit as candidate or incomplete output.

The existing generator workflow gains two outputs from the same generation:
the mesh and the parametric description. The local generator UI displays both.
It overlays resampled parametric surfaces on the mesh, colors by `surface_id`,
shows target coverage and unrepresented target faces, and exposes point/normal
and mesh discrepancy information for the selected surface. This UI review is a
required human check before an interface enters the readiness manifest.

The UI is the primary human review surface for parameterized interfaces. It
supports loading an existing review directory with a required manifest and
episode layout, so reviewers can inspect previously generated models and their
descriptions without regenerating them. The interface selector shows
`<interface-id> - <workpiece-name>` and supports search. It can inspect both
newly produced descriptions and historical structure priors or parameter
artifacts.

The batch gate remains process independent: it validates the exported OBJ,
face attributes, metadata reference, typed description, target coverage,
outward normals, multi-seed consistency, and a source-independent consumer.
The standard machine checks remain mandatory. Parameterized interfaces use ten
manual-review seeds in the Web UI by default; contact sheets are no longer the
primary parameterization review surface, though they remain available as an
export from the same review root and existing category-review artifacts remain
valid historical evidence. Parametric readiness and category acceptance are
recorded as related but separate decisions.

The review root is shared by all interfaces in one run and is loaded by the
same UI startup command. The UI writes only review records and optional
screenshots or overlay exports. It does not mutate generated meshes, OBJ files,
parametric artifacts, or machine-check results. `human-review.json` records one
interface-level status (`pending`, `accepted`, `needs_fix`, or `rejected`),
reviewer, time, conclusion, and notes. Individual issues include the seed
that demonstrates the problem; seeds are evidence references, not separate
approval records. Contact sheets are generated on demand from the immutable
review root without regenerating models.

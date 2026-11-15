# Source-addressed sweep patches

The next shared provider captures the section addresses retained by
`curve_to_mesh_with_uv` before furniture bases are assembled. Repeated bases
share the same implementation; category adapters do not introduce private
surface schemas. The provider uses evaluated source section coordinates, not
spatial fitting or classification of the final exported triangles.

Version 3 adds a bilinear `sweep_quad`, a convex planar `sweep_cap`, and an affine
`sweep_triangle` for cells collapsed at rotational poles. A quad's
four controls are in source face winding order; its point and normal are the
bilinear interpolation and normalized derivative cross product. A cap uses a
radial parameter from its vertex-average center to its piecewise-linear closed
boundary. Source rail and profile addresses accompany each patch. Corner-domain floating
addresses preserve evaluated Bezier segments and welding boundaries.

This describes the piecewise sections used by the generator. It does not claim
to reconstruct an underlying smooth Bezier curve or an unapplied subdivision
modifier. Nonconvex caps, folded cells, lost source addresses and topology
changes remain explicit unsupported cases. The quad-to-triangulation distance
bound is one quarter of the bilinear twist magnitude, plus source roundoff.
The consumer, independent validator and Web overlay must understand version 3
before it is accepted into the standard workflow.

All 100 currently registered interfaces must complete automatic checks before
opening the human-review stage for this effort. New complete outputs remain
candidates; neither single-seed screening nor this schema extension promotes
readiness or opens human review.

The same v3 bilinear cell evaluator also supports the shared ruled-panel
construction (`fill_between_curves` followed by one explicit extrusion).
This provider records three corner addresses: cross-curve row, along-curve
sample and extrusion layer. It exports `sweep_quad` with provenance primitive
`ruled_grid_extrusion` and `grid_addresses`, rather than claiming that the
panel was made by `curve_to_mesh_with_uv`. Both capture and the independent
validator require four distinct integer-addressed corners spanning one cell.
The geometry, normals and approximation bound use the existing bilinear
contract, so the consumer and Web evaluator need no separate surface schema.

The first interface adapter is the unbeveled ladder-back chair seat. The
shared construction also covers solid backs at the primitive level; this
does not certify the assembled interfaces using them. Bevels, Boolean cuts,
multiple extrusion layers and arbitrary final-mesh recovery are outside this
provider's contract. Missing or interpolated lineage stays incomplete. The
beveled dining-seat/back and door/cabinet families still need additional
operation providers before they can become complete candidates.

Tight sweep fillets can produce a nonconvex four-corner source cell. The
provider now records its source triangulation before assembly. If a later
weld reduces the cell to one triangle, its surviving three source corners
must match three of the recorded four controls. Each surviving triangle is
described by `sweep_triangle` with `source_quad_split` provenance and exact
final triangle ownership. Missing or ambiguous correspondence fails closed.

## Problem Statement

Current generation interfaces can produce meshes, face attributes, structure priors, and some parametric descriptions, but there is no unified review root and Web review flow. The existing Web UI cannot load prior batch results, overlay parameter surfaces, or save human review. Parameter descriptions, machine checks, manual review, and contact-sheet export do not share one stable review contract.

## Solution

Create one review root and one episode contract shared by live UI generation, batch export, strict validation, source-independent consumption, human review, and contact-sheet export.

All registered Workpieces and legacy Spraybot interfaces use one capture path:

- shared geometric primitives provide typed geometry providers;
- interface adapters provide composition, semantic parts, structural branches, and target ownership;
- complete but uncertified output is candidate;
- missing target coverage is incomplete while preserving normal model output;
- only machine-gated and human-reviewed interfaces enter the readiness manifest and emit ready/parametric.json.

The Web UI loads an existing review root or performs live generation. It overlays resampled parameter surfaces on the mesh. Contact sheets remain available as an export from the same review root, but are no longer the primary parameterization review surface.

## User Stories

1. As a workpiece developer, I want every registered interface to use one parameter capture entrypoint, so that new interfaces do not need a separate export workflow.
2. As a workpiece developer, I want reusable primitives such as boards, rods, cylinders, tabletops, triangular shelves, door panels, and supports to provide typed descriptions, so that interfaces reuse one implementation.
3. As a workpiece developer, I want an interface adapter to describe composition and semantic ownership without defining a private geometry schema.
4. As a workpiece developer, I want unsupported mappings reported explicitly.
5. As a batch operator, I want one review root to contain every interface in a run.
6. As a batch operator, I want each episode to keep OBJ, face attributes, structure priors, metadata, and optional parametric artifacts together.
7. As a batch operator, I want complete uncertified descriptions stored as candidate artifacts.
8. As a batch operator, I want incomplete interfaces to preserve normal model outputs with a failure reason.
9. As a reviewer, I want to load an existing review root without regenerating models.
10. As a reviewer, I want interface labels in the form interface-id - workpiece-name.
11. As a reviewer, I want search and filtering for large registries.
12. As a reviewer, I want to select an interface and seed.
13. As a reviewer, I want the mesh and resampled parametric surfaces overlaid.
14. As a reviewer, I want surfaces colored by surface ID.
15. As a reviewer, I want toggles for mesh, lines, points, normals, and target coverage.
16. As a reviewer, I want a readable default physical sampling spacing with sparse, standard, and dense display modes.
17. As a reviewer, I want selected-surface type, parameters, domain, normal, approximation, and mapped triangle IDs.
18. As a reviewer, I want undescribed target faces highlighted.
19. As a reviewer, I want machine coverage, normal, and discrepancy summaries.
20. As a reviewer, I want historical priors and parameter artifacts visible alongside new descriptions.
21. As a reviewer, I want one human conclusion per interface rather than one verdict per seed.
22. As a reviewer, I want issue notes to reference concrete seeds.
23. As a reviewer, I want fixed statuses pending, accepted, needs_fix, and rejected.
24. As a reviewer, I want reviewer, time, conclusion, and notes saved.
25. As a reviewer, I want the UI to write only review records and optional screenshots or overlays.
26. As a reviewer, I want ten default manual-review seeds per interface.
27. As a machine-validation operator, I want strict checks for units, triangle order, domains, outward normals, mappings, and target coverage.
28. As a machine-validation operator, I want capture-on/off comparisons.
29. As a machine-validation operator, I want a source-independent consumer.
30. As a maintainer, I want readiness evidence generated from machine results and human review records.
31. As a maintainer, I want the readiness manifest separate from worker control flow.
32. As a maintainer, I want contact sheets generated from existing review roots without regeneration.
33. As a downstream trajectory agent, I want one stable schema with typed geometry variants.
34. As a downstream trajectory agent, I want points and normals in the exported OBJ frame with explicit units.
35. As a project maintainer, I want parameter readiness and category acceptance recorded separately.
36. As a project maintainer, I want legacy Spraybot interfaces to use the same envelope and status model.

## Implementation Decisions

- Use one review-root and episode seam shared by UI generation, batch export, validation, consumer sampling, human review, and contact-sheet export.
- Keep generated episode artifacts immutable after export.
- Add a review-root manifest indexing interface IDs, names, seeds, episode locations, machine results, and human-review records.
- Add a loader for a review root and a server startup option for it.
- Extend the UI response with parameter status, description or incomplete reason, coverage summary, and machine references.
- Use interface labels in the form interface-id - workpiece-name with search.
- Register typed providers for shared primitives. Providers return typed surfaces, domains, point/normal evaluators, approximation records, and final mesh mappings.
- Keep interface adapters limited to composition, semantic parts, structural branches, and target ownership.
- Keep v1 for rectangular planes, cylinder sides, and disks; use v2 for triangular planes; require explicit extensions for new geometry.
- Generate candidate for complete but uncertified output; generate incomplete with a reason when mapping fails.
- Only certified manifest entries may claim ready and emit parametric.json.
- Add UI overlays for mesh, sampled surfaces, IDs, coverage, normals, selected details, and undescribed target faces.
- Use ten manual-review seeds per interface by default; machine regression batches may be larger.
- Save one interface-level human-review.json with pending, accepted, needs_fix, or rejected status; issue entries reference seeds.
- Keep contact-sheet export available from the same review root but remove it as the primary new parameterization gate.
- Require strict machine checks, capture invariance, source-independent consumer checks, and human Web review before promotion.
- Preserve category manual review and compatibility export as separate acceptance decisions.

## Testing Decisions

- Test the review-root and HTTP/API seams, not provider implementation details.
- Test indexing multiple interfaces, labels, and search.
- Test live generation and existing-directory loading yield the same episode representation.
- Test ready, candidate, and incomplete API states.
- Test overlays for plane, triangle plane, cylinder, and disk providers against independent evaluators.
- Test triangle mappings, target coverage, outward normals, units, approximation bounds, and invalid type rejection.
- Test capture-on/off geometry, triangle order, target mask, and part labels.
- Test source-independent consumption without source metadata.
- Test human review persistence, interface-level status, seed-linked issues, and immutable artifacts.
- Test contact-sheet export reads an existing review root without generating models.
- Reuse existing parametric validator, consumer, capture comparator, batch gate, generator UI API, and contact-sheet exporter.
- Run cross-family tests for furniture, tables, cabinets, beds, doors/windows, and legacy Spraybot interfaces.
- Run the ten-seed manual Web review workflow and larger machine regression batches as needed.

## Out of Scope

- Converting arbitrary external 3D models into Infinigen generators.
- Automatically deciding spray-task suitability.
- Replacing human category review with machine checks.
- Robot motion planning, gun dynamics, coating thickness, or real spray-quality validation.
- A second schema for legacy Spraybot interfaces.
- Inventing parameterizations for unsupported complex geometry without providers.
- Removing contact-sheet generation.
- Changing existing OBJ, structure.json, or face_attributes.npz meanings.
- Batch trajectory or PaintDS production.

## Further Notes

The current certified manifest contains 24 Workpieces interfaces. The implementation must make readiness data-driven rather than embed a growing hard-coded worker list. The immediate target is review-root loading and parameter-surface overlay; provider expansion follows the same registry and evidence path.

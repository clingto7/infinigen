# Generation priors supplement v1

This supplement augments the existing 23-category SPS_V2.0 dataset. Extract each
`*.priors-v1.tar.zst` at the same root as its original archive. It adds
`structure.json` and `face_attributes.npz` to each original episode; it does not
replace the OBJ, trajectory, or original metadata.

Every accepted episode was reconstructed using its recorded seed (or recovered
from the retained Chair NPZ) and serialized with the original OBJ writer. The
reconstructed OBJ SHA-256 must equal the original file SHA-256. The JSON records
this hash, episode identity and verification result. Face arrays follow that
exact OBJ triangle order and load with `numpy.load(..., allow_pickle=False)`.

## What is included

| Categories | Representation |
| --- | --- |
| Chair | Native unique `part_id`, semantic `part_type`, sampled centerlines, back metadata; original NPZ hash and source-to-OBJ transform |
| OpusChair | Native seat dimensions, leg/ornament anchors and radii, panel silhouette, semantic `part_type` |
| CarBumper | Native reconstructable surface parameters, shell/opening/grille metadata, semantic `part_type` |
| New 20 categories | Concrete construction-function arguments, sampled/derived numeric values, return values, object transforms/assembly references, hashed source files, `spray_part`, `spray_target`, `spray_target_reason` |

All OBJ coordinates are millimeters. Native priors use source-frame meters;
apply the JSON `prior_to_obj_mm` matrix to homogeneous positions. Chair includes
bbox-centering translation; OpusChair and CarBumper use the inverse object-world
transform followed by meter-to-millimeter scaling, since their original OBJ
exporters wrote object-local vertices. For the
newer categories, construction parameters use each source function's frame.
Follow the recorded object transforms and assembly operations. Do not transform
dimensionless values, counts, angles, or UV parameters as spatial coordinates.

`part_id` and `part_type` are different. Native Chair centerlines index unique
part instances. `spray_part` groups semantic types; multiple legs share a code.
Construction `object_ref` links an object's appearances in the executed call
record and is not a semantic face ID.

For example, to retrieve new Armchair rail/post dimensions:

```python
import json
from pathlib import Path

record = json.loads(Path("structure.json").read_text())
calls = record["construction_record"]["calls"]
arms = [c for c in calls if c["function"].endswith(".board")
        and c["inputs"].get("part") == "arm"]
for arm in arms:
    print(arm["inputs"]["size"], arm["inputs"]["center"],
          arm["inputs"]["rotation"], arm["output"])
```

For CabrioleLegTable, `.chain` calls contain the actual polyline `points`,
`section` and `overlap`; `.strut`/`.board` calls describe individual segments.
Use the matching hashed source in `generation-source.tar.gz` to interpret other
generators. `provenance.json` records source hashes and environment versions.

## Boundaries

The executed construction record is not a universal analytic CAD surface schema.
Opaque procedural nodes/materials are explicitly marked `unrecorded_type`; their
meaning lives in the accompanying source. Numeric values are observed during
normal generation, not estimated from final meshes. Native Chair centerlines are
sampled polylines, not original Bezier handles. Opus anchors/radii likewise rely
on the original curve constructor. These distinctions matter when evaluating
surface positions and normals.

Recovery does not recompute accessibility, change target policies, generate new
trajectories, or certify collision-free/complete coating paths. Existing target
label quality limitations remain. New trajectory rules should be validated
against the unchanged original mesh. A complete release is identified by
`generation-priors/v1/manifest.json` with `complete: true`, 23 categories and
224294 verified episodes. Individual category archives may appear earlier while
the release is being built.

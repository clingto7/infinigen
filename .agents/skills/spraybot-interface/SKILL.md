---
name: spraybot-interface
description: Use for work on an Infinigen Spraybot workpiece interface: generator or face fields, parametric export, trajectory planning, machine gates, Web review, review records, or paired evidence.
---

# Spraybot interface work

Read [the interface workflow](../../../docs/spraybot/interface-workflow.md) and [project vocabulary](../../../CONTEXT.md). Read only the contracts for the stage being changed. For an existing interface, read its `docs/spraybot/interfaces/<group>__<name>.md` record if present, both `reviews/` records if present, and the relevant Git history. An interface ID such as `workpiece:armchair` maps to `workpiece__armchair.md`.

## Work from the requested stage

1. Identify the interface ID, the user's requested change, the current committed model and trajectory review states, and the source and evidence versions. The user's conversation determines which interface and stage to work on; the workflow does not select a backlog item.
2. Preserve the separate claims: parametric description `candidate`/`incomplete`/`ready`, generation interface `developing`/`awaiting_review`/`needs_fix`/`ready`, and trajectory review `needs_fix`/`accepted`. A passing machine check or a high coverage number never supplies human acceptance.
3. Implement and verify the affected stage using the workflow. Use generation-time geometry provenance and exported artifacts; bind trajectories to the reviewed model and seed. Run checks on the data actually delivered to the Web page or PaintDS, including export rounding where relevant.
4. When review finds a defect, commit the review finding and its reproducible seed or stroke evidence before the repair. Repair the structural cause across relevant variants; re-run the affected machine checks and Web review. If an accepted artifact changes, invalidate or refresh its evidence before presenting it as current.
5. After each review or repair cycle, update the interface experience record with the observed symptom, affected structure, cause, repair, verification, and commit IDs. Keep the formal decision and artifact hashes in `reviews/interfaces/` or `reviews/trajectories/`. A new interface receives its experience record when the first substantive decision or defect is found, not an empty template file.
6. Promote a recurring or transferable lesson to the shared workflow. When a defect is objectively detectable, first retain a failing example, then add a regression check with its applicability and false-positive limits. Check representative structural variants and relevant native precedents before making it a hard gate. Keep a judgement that cannot be checked reliably in the human review list.

## Completion check

The affected artifact and review evidence refer to the same interface, seed, model and source revision; relevant checks have recorded outcomes; the review status reflects the actual reviewer decision or remains pending; the experience record reflects the cycle; and Git status does not disguise an uncommitted review as an accepted one. State any unverified robot reachability or coating-quality claim explicitly.

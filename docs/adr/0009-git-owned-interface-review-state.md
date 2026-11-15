# Keep interface review state in the repository

The Git-tracked project record is the authority for each registered workpiece interface's `developing`, `awaiting_review`, `needs_fix`, or `ready` state and its human review conclusion. A review root may be any selected workspace containing generated samples and inspection evidence; it does not own interface state. Machine gates and human review are evaluated per interface, so one interface may enter review without waiting for every registered interface to pass. This separates durable decisions from replaceable batch outputs and supports adding interfaces one at a time.

A `ready` conclusion applies to the generation behavior and exported contract that were reviewed. A change affecting geometry, parameter surfaces, target-face policy, or export invalidates the affected interface's prior conclusion until its machine gate and human review are repeated. Documentation and review UI changes alone do not invalidate it.

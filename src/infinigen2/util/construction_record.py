"""Record concrete construction parameters while executing existing generators.

This is an executed construction record, not a fitted CAD model. Numeric inputs,
sampled local values and object transforms retain their source function context.
Opaque node/material values are explicitly identified, never converted to repr.
The accompanying source snapshot defines the interpretation of each operation.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path
import sys

import numpy as np


SCHEMA = "spraybot.construction-record.v1"
_MISSING = object()
_PREFIXES = (
    "infinigen2.workpieces.", "infinigen2.objects.", "infinigen2.curves.",
    "infinigen2.util.mesh", "infinigen2.util.curve",
)
_OBJECT_OPS = {"set_transform", "join", "duplicate", "apply_transform"}


def numeric_value(value):
    """JSON values only; unsupported values are distinguished from JSON null."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else _MISSING
    if isinstance(value, np.generic):
        return numeric_value(value.item())
    if isinstance(value, np.ndarray):
        if value.dtype.kind not in "biuf" or not np.isfinite(value).all():
            return _MISSING
        return value.tolist()
    if type(value).__module__ == "mathutils":
        return numeric_value(np.asarray(value))
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if not isinstance(key, (str, int)):
                return _MISSING
            encoded = numeric_value(item)
            if encoded is _MISSING:
                return _MISSING
            result[str(key)] = encoded
        return result
    if isinstance(value, (list, tuple)):
        result = [numeric_value(item) for item in value]
        return _MISSING if any(item is _MISSING for item in result) else result
    return _MISSING


class ConstructionRecorder:
    """Process-local observer; use one Blender process per worker, never threads.

    The observer does not consume randomness or change geometry. Object references
    link assembly/transform calls; they are NOT semantic part-instance IDs. Face
    semantics and native part-instance IDs are exported separately.
    """

    def __init__(self):
        self.calls = []
        self.active = {}
        self.sources = {}
        self.objects = {}
        self._object_refs = []  # prevent Python identity reuse during one build
        self._previous = None

    def _encode(self, value):
        from procfunc.types import Object

        if isinstance(value, Object):
            try:
                obj = value.item()
                key = obj.as_pointer()
                if key not in self.objects:
                    self.objects[key] = len(self.objects) + 1
                    self._object_refs.append(obj)
                return {
                    "object_ref": self.objects[key],
                    "matrix_world": [list(row) for row in obj.matrix_world],
                }
            except (ReferenceError, RuntimeError):
                return {"unavailable_object": True}
        if isinstance(value, tuple) and hasattr(value, "_fields"):
            return {key: self._encode(item) for key, item in zip(value._fields, value)}
        if isinstance(value, (list, tuple)) and any(isinstance(x, Object) for x in value):
            return [self._encode(x) for x in value]
        result = numeric_value(value)
        if result is _MISSING:
            return {"unrecorded_type": f"{type(value).__module__}.{type(value).__qualname__}"}
        return result

    def _profile(self, frame, event, arg):
        if event not in {"call", "return"}:
            return
        module = frame.f_globals.get("__name__", "")
        name = frame.f_code.co_name
        selected = module.startswith(_PREFIXES) or (
            module == "procfunc.ops.object" and name in _OBJECT_OPS
        )
        if not selected or name.startswith("<") or module.endswith(".common"):
            return
        if event == "call":
            parent = frame.f_back
            while parent is not None and id(parent) not in self.active:
                parent = parent.f_back
            filename = frame.f_code.co_filename
            if filename not in self.sources:
                self.sources[filename] = hashlib.sha256(Path(filename).read_bytes()).hexdigest()
            count = frame.f_code.co_argcount + frame.f_code.co_kwonlyargcount
            args = frame.f_code.co_varnames[:count]
            record = {
                "id": len(self.calls),
                "parent": self.active.get(id(parent)) if parent else None,
                "function": f"{module}.{frame.f_code.co_qualname}",
                "source_sha256": self.sources[filename],
                "source_line": frame.f_code.co_firstlineno,
                "inputs": {k: self._encode(frame.f_locals[k]) for k in args if k in frame.f_locals},
            }
            self.active[id(frame)] = len(self.calls)
            self.calls.append(record)
        elif id(frame) in self.active:
            record = self.calls[self.active.pop(id(frame))]
            record["output"] = self._encode(arg)
            # Locals include sampled dimensions, selected structural branches,
            # anchor arrays, section dimensions, and parameter profiles.
            values = {}
            for key, value in frame.f_locals.items():
                if key not in record["inputs"]:
                    encoded = numeric_value(value)
                    if encoded is not _MISSING:
                        values[key] = encoded
            record["sampled_and_derived"] = values

    def __enter__(self):
        self._previous = sys.getprofile()
        if self._previous is not None:
            raise RuntimeError("Construction recording cannot replace an active profiler")
        sys.setprofile(self._profile)
        return self

    def __exit__(self, *_):
        sys.setprofile(self._previous)

    def payload(self):
        return {
            "schema": SCHEMA,
            "coordinate_unit": "m",
            "units_note": "Follow each source function: lengths in meters, Euler rotations in radians; ratios, counts and UV parameters are not lengths.",
            "coordinate_frame": "function-local; follow recorded object transforms",
            "representation": "executed_source_parameters",
            "calls": self.calls,
            "sources": {
                key.split("/src/", 1)[-1]: value for key, value in self.sources.items()
            },
        }

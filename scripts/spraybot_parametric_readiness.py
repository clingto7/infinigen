"""Read the certified interface manifest used by the episode worker."""

from __future__ import annotations

import json
from pathlib import Path


MANIFEST = Path(__file__).with_name("spraybot_parametric_readiness.json")
SCHEMA = "spraybot.parametric-readiness.v1"


def load(path: Path = MANIFEST) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA or not isinstance(data.get("certified"), dict):
        raise ValueError(f"invalid parametric readiness manifest: {path}")
    for generator, row in data["certified"].items():
        if not generator.startswith(("workpiece:", "spraybot:")):
            raise ValueError(f"invalid certified generator: {generator}")
        if row.get("parametric_schema") not in {"spraybot.parametric.v1", "spraybot.parametric.v2", "spraybot.parametric.v3", "spraybot.parametric.v4", "spraybot.parametric.v5", "spraybot.parametric.v6"}:
            raise ValueError(f"invalid certified schema for {generator}")
    return data["certified"]

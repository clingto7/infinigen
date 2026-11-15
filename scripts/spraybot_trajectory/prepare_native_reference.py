"""Package original Spraybot model and PaintDS pairs for comparison in the Web UI."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from spraybot_trajectory.paintds import euler_zyx_to_aim
from spraybot_trajectory.prepare_viewer import _obj_vertices_and_faces


REFERENCES = (("chair", "Chair_000", "Chair 原生轨迹"),
              ("opus", "OpusChair_00000", "OpusChair 原生轨迹"),
              ("bumper", "CarBumper_00000", "CarBumper 原生轨迹"))


def package(source: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    entries = []
    for key, name, label in REFERENCES:
        episode = source / key / name
        vertices, triangles = _obj_vertices_and_faces(episode / f"{name}.obj")
        strokes = []
        for line in (episode / "trajectory.txt").read_text().splitlines()[1:]:
            if not line:
                continue
            row = line.split(";")
            sid = int(float(row[6]))
            if sid == len(strokes):
                strokes.append({"points": [], "aims": []})
            if sid >= len(strokes):
                raise ValueError(f"nonsequential stroke ID: {episode}")
            aim = euler_zyx_to_aim(np.asarray([[float(x) for x in row[3:6]]]))[0]
            strokes[sid]["points"].append([round(float(x) / 1000, 6) for x in row[:3]])
            strokes[sid]["aims"].append([round(float(x), 6) for x in aim])
        payload = {"key": key, "label": label,
                   "model": {"generator": f"reference:{key}", "seed": 0,
                             "vertices": vertices.round(6).tolist(),
                             "triangles": triangles.tolist(),
                             "triangle_count": len(triangles), "vertex_count": len(vertices)},
                   "trajectory": {"strokes": strokes,
                                  "stroke_sources": [{"part": label, "surface": "原生程序"} for _ in strokes],
                                  "visibility": None,
                                  "check": {"stroke_count": len(strokes),
                                            "waypoint_count": sum(len(x["points"]) for x in strokes)}}}
        (output / f"{key}.json").write_text(json.dumps(payload, separators=(",", ":")))
        entries.append({"key": key, "label": label, "model": name,
                        "strokes": len(strokes),
                        "waypoints": payload["trajectory"]["check"]["waypoint_count"]})
    index = {"schema": "spraybot.native-trajectory-references.v1", "entries": entries}
    (output / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n")
    return index


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(package(args.source, args.output)))

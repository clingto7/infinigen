"""Package paired OBJ and PaintDS episodes for the browser trajectory viewer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from spraybot_trajectory.paintds import euler_zyx_to_aim


def _obj_vertices_and_faces(path: Path) -> tuple[np.ndarray, np.ndarray]:
    vertices, faces = [], []
    for line in path.read_text(encoding="ascii").splitlines():
        if line.startswith("v "):
            vertices.append([float(value) / 1000 for value in line.split()[1:4]])
        elif line.startswith("f "):
            faces.append([int(value.split("/")[0]) - 1 for value in line.split()[1:4]])
    return np.asarray(vertices, dtype=float), np.asarray(faces, dtype=int)


def package(root: Path) -> dict:
    entries = []
    data_dir = root / "viewer-data"
    data_dir.mkdir(exist_ok=True)
    for episode in sorted(root.glob("seed_*/trajectory-check.json")):
        directory = episode.parent
        check = json.loads(episode.read_text())
        visibility = json.loads((directory / "visibility-check.json").read_text())
        sources = json.loads((directory / "stroke-sources.json").read_text())
        metadata = json.loads((directory / "source-metadata.json").read_text())
        vertices, faces = _obj_vertices_and_faces(directory / metadata["model_file"])
        strokes = []
        for line in (directory / "trajectory.txt").read_text().splitlines()[1:]:
            if not line:
                continue
            fields = line.split(";")
            sid = int(float(fields[6]))
            if sid == len(strokes):
                strokes.append({"points": [], "aims": []})
            if sid >= len(strokes):
                raise ValueError(f"nonsequential stroke IDs: {directory}")
            aim = euler_zyx_to_aim(np.asarray([[float(x) for x in fields[3:6]]]))[0]
            strokes[sid]["points"].append([round(float(x) / 1000, 6) for x in fields[:3]])
            strokes[sid]["aims"].append([round(float(x), 6) for x in aim])
        if len(strokes) != check["stroke_count"]:
            raise ValueError(f"stroke count mismatch: {directory}")
        if len(sources) != len(strokes):
            raise ValueError(f"stroke provenance count mismatch: {directory}")
        filename = f"seed_{check['seed']:010d}.json"
        payload = {"seed": check["seed"], "vertices": vertices.round(6).tolist(),
                   "triangles": faces.tolist(), "strokes": strokes, "check": check,
                   "visibility": visibility, "stroke_sources": sources}
        (data_dir / filename).write_text(json.dumps(payload, separators=(",", ":")))
        entries.append({"seed": check["seed"], "file": f"viewer-data/{filename}",
                        "strokes": len(strokes), "waypoints": check["waypoint_count"]})
    if not entries:
        raise ValueError(f"no trajectory episodes: {root}")
    index = {"schema": "spraybot.trajectory-viewer.v1", "episodes": entries}
    (root / "viewer-index.json").write_text(json.dumps(index, indent=2) + "\n")
    return index


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    print(json.dumps(package(parser.parse_args().root)))

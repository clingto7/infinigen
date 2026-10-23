"""Structural island audit for validated workpiece samples.

Loads every ``model.blend`` under a validation output root, splits the joined
workpiece mesh into edge-connected components, merges components whose
axis-aligned bounding boxes touch within a tolerance, and reports the islands
that remain.  Islands made only of movable labels (doors, drawer fronts,
handles, glass, drawer boxes) are expected clearance and only reported when
they drift far from the body; any other island is a sub-assembly that is not
joined to the workpiece, such as a detached bunk-bed ladder.

The merge test is an axis-aligned bounding-box gap, so rotated members can
merge before their surfaces truly touch.  The audit is a screening pass for
manual review, not an exact contact solver.

Example:
  .venv/bin/python scripts/spraybot_island_audit.py \
      outputs_scratch/review-expansion-20seed-20261020
"""

import argparse
import collections
import glob
import json
import os

import numpy as np
import bpy

# door_frame, door_panel, drawer_front, handle, glass, drawer_box
MOVABLE = {9, 10, 11, 14, 20, 21}
LOOSE_MOVABLE_GAP = 0.05


def _components(me):
    adj = [set() for _ in me.vertices]
    for e in me.edges:
        a, b = e.vertices
        adj[a].add(b)
        adj[b].add(a)
    seen = set()
    out = []
    for v in range(len(adj)):
        if v in seen:
            continue
        stack = [v]
        seen.add(v)
        comp = []
        while stack:
            x = stack.pop()
            comp.append(x)
            for n in adj[x]:
                if n not in seen:
                    seen.add(n)
                    stack.append(n)
        out.append(comp)
    return out


def _aabb_gap(a, b):
    d = np.maximum(np.maximum(a[0] - b[1], b[0] - a[1]), 0.0)
    return float(np.linalg.norm(d))


def audit_blend(path, tol):
    bpy.ops.wm.open_mainfile(filepath=path)
    objs = [o for o in bpy.data.objects if o.type == "MESH"]
    if len(objs) != 1:
        return [{"error": f"{len(objs)} mesh objects"}]
    obj = objs[0]
    me = obj.data
    verts = np.array([obj.matrix_world @ v.co for v in me.vertices], dtype=float)
    comps = _components(me)
    part = me.attributes.get("spray_part")
    vcomp = {v: i for i, c in enumerate(comps) for v in c}
    face_of_comp = collections.defaultdict(int)
    lab_of_comp = collections.defaultdict(collections.Counter)
    for p in me.polygons:
        ci = vcomp[p.vertices[0]]
        face_of_comp[ci] += 1
        if part is not None:
            lab_of_comp[ci][part.data[p.index].value] += 1
    boxes = []
    for i, c in enumerate(comps):
        pts = verts[c]
        boxes.append((pts.min(0), pts.max(0), lab_of_comp[i], face_of_comp[i]))

    parent = list(range(len(boxes)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(boxes)):
        for j in range(i):
            if _aabb_gap(boxes[i], boxes[j]) <= tol:
                a, b = find(i), find(j)
                if a != b:
                    parent[b] = a
    islands = collections.defaultdict(list)
    for i in range(len(boxes)):
        islands[find(i)].append(i)

    result = []
    if len(islands) == 1:
        return result
    for members in islands.values():
        labels = collections.Counter()
        faces = 0
        mn = np.full(3, 1e9)
        mx = np.full(3, -1e9)
        for i in members:
            labels.update(boxes[i][2])
            faces += boxes[i][3]
            mn = np.minimum(mn, boxes[i][0])
            mx = np.maximum(mx, boxes[i][1])
        gaps = [
            min(_aabb_gap(boxes[i], boxes[j]) for i in members for j in other)
            for other in islands.values()
            if other is not members
        ]
        result.append(
            {
                "labels": {int(k): int(v) for k, v in labels.items()},
                "faces": int(faces),
                "min_gap": round(min(gaps), 4) if gaps else None,
                "zmin": round(float(mn[2]), 3),
                "zmax": round(float(mx[2]), 3),
                "movable": set(int(k) for k in labels) <= MOVABLE,
            }
        )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("root", help="validation output directory")
    parser.add_argument("--tol", type=float, default=0.001, help="merge gap in metres")
    parser.add_argument("--out", default=None, help="write JSON here instead of stdout")
    args = parser.parse_args()

    findings = {}
    paths = sorted(glob.glob(os.path.join(args.root, "*", "seed_*", "model.blend")))
    if not paths:
        raise SystemExit(f"no seed model.blend under {args.root}")
    for path in paths:
        rel = os.path.relpath(path, args.root)
        cat = rel.split(os.sep)[0]
        try:
            res = audit_blend(path, args.tol)
        except Exception as exc:  # noqa: BLE001
            findings.setdefault(cat, {"hard": [], "loose": [], "errors": []})
            findings[cat]["errors"].append((rel, str(exc)))
            continue
        hard = [r for r in res if "error" not in r and not r["movable"]]
        loose = [
            r for r in res
            if "error" not in r and r["movable"] and r["min_gap"] > LOOSE_MOVABLE_GAP
        ]
        errors = [r for r in res if "error" in r]
        if hard or loose or errors:
            entry = findings.setdefault(cat, {"hard": [], "loose": [], "errors": []})
            entry["hard"] += hard
            entry["loose"] += loose
            entry["errors"] += [(rel, e["error"]) for e in errors]

    text = json.dumps(findings, ensure_ascii=False, indent=1, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
    # bpy redirects sys.stdout to its own console; sys.__stdout__ still works
    import sys

    sys.__stdout__.write(text + "\n")


if __name__ == "__main__":
    main()

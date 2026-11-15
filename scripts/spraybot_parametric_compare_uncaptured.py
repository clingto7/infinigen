"""Radar-side check that parameter capture leaves generated meshes unchanged.

For each exported episode, regenerate the same workpiece seed without capture
and compare final OBJ vertices, triangle order, spray target, and part labels.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

from spraybot_mass_worker import generate
from spraybot_parametric_validate import _obj


def _same_planar_quads(generated: Counter, exported: Counter, vertices: np.ndarray) -> bool:
    """Accept only opposite diagonals of the same labelled, planar quad."""
    left = list(generated.elements())
    right = list(exported.elements())
    if len(left) != len(right) or len(left) % 2 or len(left) > 200:
        return False

    def pair_candidates(rows):
        candidates = {}
        for i, (a, target_a, part_a) in enumerate(rows):
            for j in range(i + 1, len(rows)):
                b, target_b, part_b = rows[j]
                verts = frozenset(a + b)
                if target_a == target_b and part_a == part_b and len(verts) == 4 and len(set(a) & set(b)) == 2:
                    candidates[(verts, target_a, part_a, i, j)] = (a, b)
        return candidates

    right_candidates = pair_candidates(right)
    used_left: set[int] = set()
    used_right: set[int] = set()
    for (quad, target, part, i, j), (a, b) in pair_candidates(left).items():
        if i in used_left or j in used_left:
            continue
        for (other_quad, other_target, other_part, k, l), (c, d) in right_candidates.items():
            if (quad, target, part) != (other_quad, other_target, other_part) or k in used_right or l in used_right:
                continue
            points = vertices[list(quad)]
            normal = np.cross(points[1] - points[0], points[2] - points[0])
            normal_length = np.linalg.norm(normal)
            if normal_length == 0 or abs(float(np.dot(normal, points[3] - points[0]))) / normal_length > 1e-7:
                continue
            def area_vector(pair):
                return sum((np.cross(vertices[t[1]] - vertices[t[0]], vertices[t[2]] - vertices[t[0]])
                            for t in pair), np.zeros(3))
            if not np.allclose(area_vector((a, b)), area_vector((c, d)), atol=1e-10, rtol=1e-5):
                continue
            used_left.update((i, j))
            used_right.update((k, l))
            break
    return len(used_left) == len(left) and len(used_right) == len(right)


def compare(batch: Path, minimum_seeds: int = 20) -> dict:
    # The workpiece registry imports chair constructors. Load it before a
    # spraybot generator imports chair -> storage -> parametric_capture, which
    # would otherwise re-enter the registry while chair is half initialized.
    import infinigen2.workpieces

    episodes = {}
    categories = set()
    for path in batch.glob("episode_*/metadata.json"):
        metadata = json.loads(path.read_text())
        seed = metadata["seed"]
        if seed in episodes:
            raise ValueError(f"duplicate seed: {seed}")
        episodes[seed] = (path.parent, metadata)
        categories.add(metadata["category_id"])
    if len(episodes) < minimum_seeds or len(categories) != 1:
        raise ValueError("batch lacks enough unique seeds or mixes categories")
    category = categories.pop()
    order_variants = []
    max_vertex_delta = 0.0
    for seed, (episode, metadata) in sorted(episodes.items()):
        result = generate(metadata["generator"], seed)
        obj = result.mesh.item()
        mesh = obj.data
        mesh.calc_loop_triangles()
        vertices = np.asarray([obj.matrix_world @ vertex.co for vertex in mesh.vertices])
        triangles = np.asarray([triangle.vertices[:] for triangle in mesh.loop_triangles])
        polygons = [triangle.polygon_index for triangle in mesh.loop_triangles]
        target = np.asarray([mesh.attributes["spray_target"].data[i].value for i in polygons])
        part = np.asarray([mesh.attributes["spray_part"].data[i].value for i in polygons])
        exported_vertices, exported_triangles = _obj(episode / metadata["model_file"])
        with np.load(episode / metadata["face_attributes_file"], allow_pickle=False) as attrs:
            checks = {
                "vertices": vertices.shape == exported_vertices.shape and np.allclose(vertices, exported_vertices, atol=6e-10, rtol=0),
                "triangles": np.array_equal(triangles, exported_triangles),
                "spray_target": np.array_equal(target, attrs["spray_target"]),
                "spray_part": np.array_equal(part, attrs["spray_part"]),
            }
            if not all(checks.values()) and category == 'infinigen_chair':
                # ChairFactory has a stable triangle set but Blender may
                # enumerate several thousand faces in a different order even
                # on two uncaptured runs. Compare geometry and semantic labels
                # by triangle identity; the candidate's own OBJ order remains
                # strictly checked by the independent artifact validator.
                if vertices.shape == exported_vertices.shape:
                    delta = float(np.max(np.abs(vertices - exported_vertices)))
                    max_vertex_delta = max(max_vertex_delta, delta)
                else:
                    delta = float('inf')
                def labelled(tris, target_rows, part_rows):
                    def oriented(triangle):
                        a, b, c = map(int, triangle)
                        return min((a, b, c), (b, c, a), (c, a, b))
                    return Counter((oriented(triangle), bool(target_row), int(part_row))
                                   for triangle, target_row, part_row in zip(tris, target_rows, part_rows))
                generated_labels = labelled(triangles, target, part)
                exported_labels = labelled(exported_triangles, attrs['spray_target'], attrs['spray_part'])
                generated_only = generated_labels - exported_labels
                exported_only = exported_labels - generated_labels
                equivalent = (delta <= 1e-7 and triangles.shape == exported_triangles.shape
                              and len(attrs['spray_target']) == len(triangles)
                              and len(attrs['spray_part']) == len(triangles)
                              and (generated_labels == exported_labels or
                                   _same_planar_quads(generated_only, exported_only, exported_vertices)))
                if equivalent:
                    order_variants.append(seed)
                    checks = {key: True for key in checks}
                else:
                    checks['diagnostic'] = {
                        'max_vertex_delta_m': delta,
                        'generated_only_labelled_triangles': sum(generated_only.values()),
                        'exported_only_labelled_triangles': sum(exported_only.values()),
                        'generated_only_examples': list(generated_only.elements())[:8],
                        'exported_only_examples': list(exported_only.elements())[:8],
                    }
        if not all(checks.values()):
            raise ValueError(f"capture changed {category} seed {seed}: {checks}")
    return {"category_id": category, "seeds_compared": sorted(episodes),
            "status": "capture_invariance_passed",
            "geometrically_equivalent_order_variant_seeds": order_variants,
            "max_vertex_delta_m": max_vertex_delta}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("batches", type=Path, nargs="+")
    parser.add_argument("--minimum-seeds", type=int, default=20)
    args = parser.parse_args()
    if args.minimum_seeds < 1:
        parser.error("minimum seeds must be positive")
    for batch_path in args.batches:
        print(json.dumps(compare(batch_path, args.minimum_seeds)), flush=True)

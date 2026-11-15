"""Generate an Armchair PaintDS geometric pilot from reviewed parametric data.

The script never imports an Infinigen generator. It reads one machine-gated
episode (OBJ, face attributes, and parametric JSON) and writes a model plus
surface-following trajectory. Robot reachability is outside this pilot.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import shutil

import numpy as np
from scipy.spatial import cKDTree

from spraybot_trajectory.paintds import write_paintds


@dataclass
class Stroke:
    positions_mm: np.ndarray
    aim: np.ndarray


def _line(start: np.ndarray, end: np.ndarray, step_m: float) -> np.ndarray:
    count = max(2, math.ceil(float(np.linalg.norm(end - start)) / step_m) + 1)
    return start[None, :] + np.linspace(0, 1, count)[:, None] * (end - start)[None, :]


def _surface_strokes(surface: dict, pitch_m: float, step_m: float) -> list[tuple[np.ndarray, np.ndarray]]:
    kind, g = surface['type'], surface['geometry']
    if kind in {'plane_rectangle', 'sweep_quad'}:
        normal = np.asarray(g['normal'], dtype=float)
        if kind == 'plane_rectangle':
            origin, u, v = (np.asarray(g[key], dtype=float) for key in ('origin', 'u', 'v'))
        else:
            corners = np.asarray(g['corners'], dtype=float)
            if corners.shape != (4, 3):
                raise ValueError(f'invalid sweep quad: {surface["id"]}')
            origin, u, v = corners[0], corners[1] - corners[0], corners[3] - corners[0]
        across, along = (u, v) if np.linalg.norm(u) <= np.linalg.norm(v) else (v, u)
        count = max(1, math.ceil(float(np.linalg.norm(across)) / pitch_m))
        result = []
        for index in range(count + 1):
            start = origin + across * (index / count)
            points = _line(start, start + along, step_m)
            if index % 2:
                points = points[::-1]
            result.append((points, np.broadcast_to(normal, points.shape)))
        return result
    raise ValueError(f'Armchair pilot does not support surface type {kind}')


def _obj_vertices_and_faces(path: Path) -> tuple[np.ndarray, np.ndarray]:
    vertices, faces = [], []
    with path.open(encoding='ascii') as stream:
        for line in stream:
            if line.startswith('v '):
                vertices.append([float(value) / 1000 for value in line.split()[1:4]])
            elif line.startswith('f '):
                faces.append([int(value) - 1 for value in line.split()[1:4]])
    return np.asarray(vertices, dtype=float), np.asarray(faces, dtype=int)


def generate(episode: Path, output: Path, review_record: Path,
             pitch_mm: float, step_mm: float, standoff_mm: float) -> dict:
    metadata = json.loads((episode / 'metadata.json').read_text())
    if metadata['category_id'] != 'armchair' or metadata['parametric_description_status'] not in {'ready', 'candidate'}:
        raise ValueError('expected a complete armchair episode')
    gate_bytes = (episode.parent / 'machine-check.json').read_bytes()
    gate = json.loads(gate_bytes)
    if (gate['geometry_gate']['status'] != 'parametric_geometry_gate_passed'
            or gate['capture_invariance']['status'] != 'capture_invariance_passed'):
        raise ValueError('source batch has not passed both machine gates')
    review = json.loads(review_record.read_text())
    if (review.get('interface_id') != 'workpiece:armchair' or review.get('status') != 'ready'
            or (review.get('human_review') or {}).get('status') != 'accepted'
            or (review.get('machine_gate') or {}).get('sha256') != hashlib.sha256(gate_bytes).hexdigest()):
        raise ValueError('source batch is not the reviewed and accepted armchair machine gate')
    parametric_name = metadata.get('parametric_file') or metadata.get('parametric_candidate_file')
    bundle = json.loads((episode / parametric_name).read_text())
    if (bundle['unit'] != 'm' or bundle['frame'] != 'exported_obj_axes_origin'
            or bundle['schema'] not in {'spraybot.parametric-candidate.v3', 'spraybot.parametric-description.v1'}):
        raise ValueError('unexpected parameter units, frame, or schema')
    with np.load(episode / metadata['face_attributes_file'], allow_pickle=False) as attributes:
        target = np.asarray(attributes['spray_target'], dtype=bool)
        accessible = np.asarray(attributes['geometry_accessible'], dtype=bool)
    vertices, faces = _obj_vertices_and_faces(episode / metadata['model_file'])
    if len(target) != len(faces):
        raise ValueError('target mask and OBJ triangle order differ')
    pitch_m, step_m, standoff_m = pitch_mm / 1000, step_mm / 1000, standoff_mm / 1000
    if min(pitch_m, step_m, standoff_m) <= 0:
        raise ValueError('pitch, point step, and standoff must be positive')
    paintable = target & accessible
    planned = np.zeros(len(faces), dtype=bool)
    strokes: list[Stroke] = []
    surface_ids = []
    stroke_sources = []
    for part in bundle['parts']:
        for surface in part['surfaces']:
            ids = np.asarray(surface['mesh_mapping']['construction_triangle_ids'], dtype=int)
            if not len(ids) or np.any(ids < 0) or np.any(ids >= len(faces)):
                raise ValueError(f'invalid triangle mapping: {surface["id"]}')
            selected = ids[paintable[ids]]
            if not len(selected):
                continue
            planned[selected] = True
            surface_ids.append(surface['id'])
            if surface['type'] == 'sweep_cap':
                normal = np.asarray(surface['geometry']['normal'], dtype=float)
                # Cap triangulation clips the parameter polygon at inaccessible regions.
                paths = []
                for i in selected:
                    triangle = vertices[faces[i]]
                    pairs = ((0, 1), (1, 2), (2, 0))
                    a, b = max(pairs, key=lambda pair: np.linalg.norm(triangle[pair[0]] - triangle[pair[1]]))
                    center = triangle.mean(axis=0)
                    points = np.stack((.5 * (center + triangle[a]), .5 * (center + triangle[b])))
                    paths.append((points, np.broadcast_to(normal, points.shape)))
            elif len(selected) == len(ids):
                paths = _surface_strokes(surface, pitch_m, step_m)
            else:
                raise ValueError(f'partially accessible non-cap surface: {surface["id"]}')
            for points, normals in paths:
                if not np.isfinite(points).all() or not np.isfinite(normals).all():
                    raise ValueError(f'nonfinite stroke: {surface["id"]}')
                strokes.append(Stroke((points + standoff_m * normals) * 1000, -normals.copy()))
                stroke_sources.append({'part': part['semantic'], 'surface': surface['id'],
                                       'surface_type': surface['type']})
    if not np.array_equal(planned, paintable) or not strokes:
        raise ValueError('trajectory surfaces do not cover exactly the accessible target triangle mask')
    aim = np.concatenate([stroke.aim for stroke in strokes])
    nozzle_m = np.concatenate([stroke.positions_mm for stroke in strokes]) / 1000
    hits = nozzle_m + standoff_m * aim
    centroids = vertices[faces[paintable]].mean(axis=1)
    gaps, _ = cKDTree(hits).query(centroids)
    max_gap_mm = float(gaps.max() * 1000)
    if max_gap_mm > 1.5 * pitch_mm:
        raise ValueError(f'target triangle centroid is too far from trajectory samples: {max_gap_mm:.2f} mm')
    output.mkdir(parents=True, exist_ok=False)
    write_paintds(strokes, output / 'trajectory.txt')
    (output / 'stroke-sources.json').write_text(json.dumps(stroke_sources, separators=(',', ':')) + '\n')
    shutil.copy2(episode / metadata['model_file'], output / metadata['model_file'])
    shutil.copy2(episode / parametric_name, output / 'parametric.json')
    shutil.copy2(episode / metadata['face_attributes_file'], output / 'face_attributes.npz')
    shutil.copy2(episode / 'metadata.json', output / 'source-metadata.json')
    shutil.copy2(review_record, output / 'interface-review.json')
    check = {
        'schema': 'spraybot.parametric-armchair-pilot.v1',
        'source_episode': str(episode),
        'review_record': str(review_record),
        'machine_gate_sha256': hashlib.sha256(gate_bytes).hexdigest(),
        'seed': metadata['seed'],
        'surface_count': len(surface_ids),
        'target_triangles': int(target.sum()),
        'inaccessible_target_triangles': int((target & ~accessible).sum()),
        'accessible_target_triangles': int(paintable.sum()),
        'planned_target_triangles': int(planned.sum()),
        'stroke_count': len(strokes),
        'waypoint_count': len(aim),
        'pitch_mm': pitch_mm,
        'point_step_mm': step_mm,
        'standoff_mm': standoff_mm,
        'max_target_centroid_gap_mm': max_gap_mm,
        'p95_target_centroid_gap_mm': float(np.percentile(gaps, 95) * 1000),
        'max_aim_norm_error': float(np.max(np.abs(np.linalg.norm(aim, axis=1) - 1))),
        'robot_reachability': 'not_checked',
        'status': 'geometric_coverage_passed_visibility_unchecked',
    }
    (output / 'trajectory-check.json').write_text(json.dumps(check, indent=2) + '\n')
    return check


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('episode', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--review-record', type=Path, required=True)
    parser.add_argument('--pitch-mm', type=float, default=25)
    parser.add_argument('--point-step-mm', type=float, default=10)
    parser.add_argument('--standoff-mm', type=float, default=100)
    args = parser.parse_args()
    print(json.dumps(generate(args.episode, args.output, args.review_record, args.pitch_mm, args.point_step_mm,
                              args.standoff_mm)))

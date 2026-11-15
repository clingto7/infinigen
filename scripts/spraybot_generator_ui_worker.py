"""One-shot Blender worker for the local Spraybot generator UI."""

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

from infinigen2.util.spray import SPRAY_TARGET_REASON_NAMES


def plain(value):
    if isinstance(value, dict):
        return {str(key): plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain(item) for item in value]
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def episode_payload(generator, seed):
    """Use the same exported source description as the machine gate."""
    from spraybot_mass_worker import write_episode

    category = generator.split(':', 1)[1]
    with tempfile.TemporaryDirectory(prefix='spraybot-native-ui-') as directory:
        batch = Path(directory) / generator
        batch.mkdir()
        write_episode(batch, category, generator, seed, set())
        episode = next(batch.glob('episode_*'))
        return payload_from_episode(episode, generator, seed)


def payload_from_episode(episode, generator, seed):
    """Load a machine-validated episode into the Web review payload."""
    from spraybot_parametric_validate import _obj, validate

    metadata = json.loads((episode / 'metadata.json').read_text())
    if metadata['category_id'] != generator.split(':', 1)[1] or metadata['seed'] != seed:
        raise ValueError(f'episode identity mismatch: {episode}')
    vertices, triangles = _obj(episode / metadata['model_file'])
    with np.load(episode / 'face_attributes.npz', allow_pickle=False) as attrs:
        face = {name: attrs[name].tolist() for name in attrs.files}
    structure = json.loads((episode / 'structure.json').read_text())
    status = metadata['parametric_description_status']
    parametric = None
    if status in ('candidate', 'ready'):
        validate(episode)
        parametric = json.loads((episode / metadata.get(
            'parametric_file' if status == 'ready' else 'parametric_candidate_file')).read_text())
    radii = np.asarray(face.get('max_passable_radius_m', []), dtype=float)
    targets = np.asarray(face['spray_target'], dtype=bool)
    coverage = (parametric or {}).get('description_coverage', {})
    return {
        'generator': generator, 'seed': seed,
        'vertices': vertices.tolist(), 'triangles': triangles.tolist(),
        'part_id': face['spray_part'],
        'spray_target': face['spray_target'],
        'spray_target_reason': face['spray_target_reason'],
        'geometry_accessible': face.get('geometry_accessible', [False] * len(triangles)),
        'max_passable_radius_m': face.get('max_passable_radius_m', [0.0] * len(triangles)),
        'part_legend': structure['part_legend'],
        'spray_target_reason_legend': plain(SPRAY_TARGET_REASON_NAMES),
        'structure_priors': structure['structure_priors'],
        'triangle_count': len(triangles), 'vertex_count': len(vertices),
        'max_passable_radius_p95_m': float(np.percentile(radii, 95)) if len(radii) else 0.0,
        'bbox_min_m': vertices.min(axis=0).tolist(),
        'bbox_max_m': vertices.max(axis=0).tolist(),
        'parametric_capture_coverage': {
            'captured_instances': len(parametric['parts']) if parametric else 0,
            'target_triangles': int(targets.sum()),
            'tagged_target_triangles': coverage.get('represented_target_triangle_count', 0),
            'untagged_target_triangle_ids': [] if parametric else np.flatnonzero(targets).tolist(),
        },
        'parametric': parametric,
        'parametric_description_status': status,
        'parametric_incomplete_reason': metadata.get('parametric_incomplete_reason'),
    }


def main():
    generator, seed, output_path = sys.argv[-3], int(sys.argv[-2]), Path(sys.argv[-1])
    output_path.write_text(json.dumps(episode_payload(generator, seed), separators=(',', ':')),
                           encoding='utf-8')


if __name__ == "__main__":
    main()

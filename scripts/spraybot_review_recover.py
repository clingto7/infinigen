"""Repair Web review episodes from batches that passed both machine gates."""

import argparse
import json
import hashlib
from pathlib import Path

from spraybot_generator_ui_worker import payload_from_episode
from spraybot_generator_ui_server import GENERATORS
from spraybot_review_batch import existing_status
from spraybot_review_root import load, save_episode
from spraybot_interface_state import read_committed_record


def recover(root: Path, batches: list[Path], count: int) -> dict:
    restored = []
    labels = {item['id']: item for item in GENERATORS}
    for batch in batches:
        check = json.loads((batch / 'machine-check.json').read_text())
        if (check['geometry_gate']['status'] != 'parametric_geometry_gate_passed'
                or check['capture_invariance']['status'] != 'capture_invariance_passed'):
            raise ValueError(f'machine gate did not pass: {batch}')
        generator = batch.name
        if check['geometry_gate']['category_id'] != generator.split(':', 1)[1]:
            raise ValueError(f'machine gate category mismatch: {batch}')
        episodes = {}
        for metadata_path in batch.glob('episode_*/metadata.json'):
            metadata = json.loads(metadata_path.read_text())
            seed = metadata['seed']
            if seed in episodes:
                raise ValueError(f'duplicate machine seed {seed}: {batch}')
            episodes[seed] = metadata_path.parent
        entry = load(root)['interfaces'].get(generator, {})
        for seed in range(count):
            existing = root / 'interfaces' / generator / 'episodes' / f'seed_{seed:010d}' / 'model.json'
            if existing.exists() and existing_status(existing) in ('candidate', 'ready'):
                continue
            payload = payload_from_episode(episodes[seed], generator, seed)
            if payload['parametric_description_status'] not in ('candidate', 'ready'):
                raise ValueError(f'machine episode has no complete description: {episodes[seed]}')
            registered = labels.get(generator, {})
            payload.update(label=entry.get('label', registered.get('label', generator)),
                           group=entry.get('group', registered.get('group', 'Workpieces')))
            save_episode(root, payload)
            restored.append({'generator': generator, 'seed': seed})
        record = read_committed_record(generator)
        gate = record.get('machine_gate') or {}
        digest = hashlib.sha256((batch / 'machine-check.json').read_bytes()).hexdigest()
        if gate.get('status') != 'passed' or gate.get('sha256') != digest:
            raise ValueError(f'batch is not the committed machine gate: {batch}')
        manifest = load(root)
        manifest['interfaces'][generator]['machine_gate'] = {
            'sha256': digest, 'source_commit': gate.get('source_commit'),
        }
        (root / 'review_manifest.json').write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    return {'restored': restored, 'count': len(restored)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review_root', type=Path)
    parser.add_argument('machine_batches', type=Path, nargs='+')
    parser.add_argument('--count', type=int, default=10)
    args = parser.parse_args()
    if args.count < 1:
        parser.error('count must be positive')
    print(json.dumps(recover(args.review_root, args.machine_batches, args.count)))

"""Open a Web review root only after every registered interface passes machine checks."""

import argparse
from collections import Counter
import json
from pathlib import Path

from spraybot_generator_ui_server import GENERATORS
from spraybot_review_root import load


def audit(review_root: Path, checks_root: Path, seeds_per_interface: int) -> dict:
    registered = {item['id'] for item in GENERATORS}
    manifest = load(review_root)
    if set(manifest['interfaces']) != registered:
        raise ValueError(f'review manifest differs from registry: {sorted(registered - set(manifest["interfaces"]))}')
    batch = json.loads((review_root / 'batch-status.json').read_text())
    rows = batch['results']
    expected = {(generator, seed) for generator in registered for seed in range(seeds_per_interface)}
    seen = {(row['generator'], row['seed']) for row in rows}
    if (batch['completed'] != len(expected) or batch['planned'] != len(expected)
            or len(rows) != len(expected) or seen != expected
            or any(row['status'] not in {'candidate', 'ready'} for row in rows)):
        raise ValueError('review batch is not complete and free of incomplete descriptions')
    for generator in registered:
        episodes = manifest['interfaces'][generator]['episodes']
        if set(episodes) != {f'seed_{seed:010d}' for seed in range(seeds_per_interface)}:
            raise ValueError(f'review root has wrong seeds: {generator}')
    evidence = {}
    for path in checks_root.rglob('machine-check.json'):
        generator = path.parent.name
        if generator not in registered or generator in evidence:
            continue
        check = json.loads(path.read_text())
        geometry = check.get('geometry_gate', {})
        invariance = check.get('capture_invariance', {})
        if (geometry.get('status') == 'parametric_geometry_gate_passed'
                and invariance.get('status') == 'capture_invariance_passed'
                and geometry.get('episodes', 0) >= 20
                and len(invariance.get('seeds_compared', [])) >= 20
                and geometry.get('category_id') == generator.split(':', 1)[1]
                and invariance.get('category_id') == generator.split(':', 1)[1]):
            evidence[generator] = str(path)
    if set(evidence) != registered:
        raise ValueError(f'missing passed machine gates: {sorted(registered - set(evidence))}')
    return {
        'registered_interfaces': len(registered),
        'screen_complete': len(registered),
        'machine_gate_passed': len(evidence),
        'passed_interfaces': sorted(evidence),
        'machine_gate_evidence': evidence,
        'review_episodes': len(rows),
        'review_status_counts': dict(Counter(row['status'] for row in rows)),
        'incomplete_interfaces': [],
        'gate_failures': [],
        'all_automatic_checks_passed': True,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('review_root', type=Path)
    parser.add_argument('machine_checks_root', type=Path)
    parser.add_argument('--seeds-per-interface', type=int, default=10)
    args = parser.parse_args()
    if args.seeds_per_interface < 1:
        parser.error('seeds per interface must be positive')
    result = audit(args.review_root, args.machine_checks_root, args.seeds_per_interface)
    destination = args.review_root / 'automation-status.json'
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(destination)
    print(json.dumps({key: result[key] for key in ('registered_interfaces', 'machine_gate_passed',
                                                  'review_episodes', 'review_status_counts',
                                                  'all_automatic_checks_passed')}))

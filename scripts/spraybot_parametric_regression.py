"""Generate and gate multiple interfaces in isolated Blender processes."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys


def archive_incomplete(batch: Path) -> None:
    """Keep failed attempts outside the active episode glob before retrying."""
    for metadata_path in batch.glob('episode_*/metadata.json'):
        try:
            metadata = json.loads(metadata_path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if metadata.get('parametric_description_status') != 'incomplete':
            continue
        archive = batch / '.incomplete_archive'
        archive.mkdir(exist_ok=True)
        target = archive / metadata_path.parent.name
        if target.exists():
            raise FileExistsError(f'incomplete retry archive already exists: {target}')
        metadata_path.parent.rename(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--generator', action='append', default=[])
    parser.add_argument('--count', type=int, default=20)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--one', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.count < 20 or args.workers < 1:
        parser.error('at least 20 seeds and one worker are required')
    args.output.mkdir(parents=True, exist_ok=True)
    if args.one:
        from spraybot_mass_worker import write_episode, existing_seeds
        from spraybot_parametric_gate import gate
        from spraybot_parametric_compare_uncaptured import compare
        category = args.one.split(':', 1)[1]
        batch = args.output / args.one
        batch.mkdir(exist_ok=True)
        archive_incomplete(batch)
        done = existing_seeds(batch, category)
        for seed in range(args.count):
            write_episode(batch, category, args.one, seed, done)
            print(json.dumps({'generator': args.one, 'generated_seed': seed}), flush=True)
        result = {'geometry_gate': gate(batch, args.count),
                  'capture_invariance': compare(batch, args.count)}
        (batch / 'machine-check.json').write_text(json.dumps(result, indent=2) + '\n')
        return
    from spraybot_parametric_readiness import load
    generators = args.generator or list(load())
    if any(not x.startswith(('workpiece:', 'spraybot:')) or '/' in x or '..' in x for x in generators):
        parser.error('invalid generator')
    logs = args.output / 'logs'
    logs.mkdir(exist_ok=True)
    def run(generator):
        with (logs / f'{generator}.log').open('w') as log:
            result = subprocess.run([sys.executable, __file__, str(args.output), '--one', generator,
                                     '--count', str(args.count)], stdout=log, stderr=subprocess.STDOUT)
        return {'generator': generator, 'status': 'passed' if result.returncode == 0 else 'failed'}
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        results = list(pool.map(run, generators))
    (args.output / 'regression.json').write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results), flush=True)
    if any(row['status'] == 'failed' for row in results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()

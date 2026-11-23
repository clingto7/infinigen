"""Generate registered interfaces into a Web review root with bounded workers.

Each seed runs in a fresh Blender process. Only the coordinator writes the
manifest; failures are recorded and do not stop unrelated interfaces.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from threading import Lock

from spraybot_review_root import ensure, save_episode

ROOT = Path(__file__).resolve().parents[1]


def existing_status(path: Path) -> str:
    """Read the trailing status without loading a possibly huge mesh JSON."""
    with path.open('rb') as stream:
        stream.seek(0, os.SEEK_END)
        stream.seek(max(0, stream.tell() - 4096))
        tail = stream.read().decode('utf-8', errors='ignore')
    matches = re.findall(r'"parametric_description_status"\s*:\s*"([^"]+)"', tail)
    if matches:
        return matches[-1]
    return json.loads(path.read_text())['parametric_description_status']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--count', type=int, default=10)
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('--categories', nargs='+', metavar='ID',
                        help='limit to these interface IDs; bare workpiece names are accepted')
    args = parser.parse_args()
    if min(args.count, args.workers, args.timeout) < 1:
        parser.error('count, workers, timeout must be positive')
    from spraybot_generator_ui_server import GENERATORS
    categories = ({value if ':' in value else f'workpiece:{value}'
                   for value in args.categories} if args.categories else None)
    unknown = sorted(categories - {item['id'] for item in GENERATORS}) if categories else []
    if unknown:
        parser.error(f'unknown categories: {", ".join(unknown)}')
    root = ensure(args.output)
    logs = root / 'run-logs'
    logs.mkdir(exist_ok=True)
    jobs = [(item, seed) for seed in range(args.count) for item in GENERATORS
            if categories is None or item['id'] in categories]
    results = []
    save_lock = Lock()

    def run(item, seed):
        generator = item['id']
        try:
            existing = root / 'interfaces' / generator / 'episodes' / f'seed_{seed:010d}' / 'model.json'
            if existing.exists():
                status = existing_status(existing)
                if status in ('ready', 'candidate'):
                    return item, seed, status, None
            environment = dict(os.environ, PYTHONPATH=str(ROOT / 'src'), OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1')
            with tempfile.TemporaryDirectory(prefix='spraybot-review-') as directory:
                output = Path(directory) / 'model.json'
                with (logs / f'{generator}-{seed}.log').open('w') as log:
                    process = subprocess.run(
                        [sys.executable, str(ROOT / 'scripts/spraybot_generator_ui_worker.py'), generator, str(seed), str(output)],
                        cwd=ROOT, env=environment, stdout=log, stderr=subprocess.STDOUT, timeout=args.timeout,
                    )
                if process.returncode:
                    raise RuntimeError(f'worker exited {process.returncode}; see run-logs')
                payload = json.loads(output.read_text())
            status = payload['parametric_description_status']
            if status in ('ready', 'candidate'):
                payload.update(label=item['label'], group=item['group'])
                with save_lock:
                    save_episode(root, payload)
            return item, seed, status, payload.get('parametric_incomplete_reason')
        except Exception as error:
            return item, seed, 'failed', str(error)

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run, item, seed) for item, seed in jobs}
        for future in as_completed(futures):
            item, seed, status, error = future.result()
            futures.remove(future)
            row = {'generator': item['id'], 'seed': seed, 'status': status, 'error': error}
            results.append(row)
            summary = {'planned': len(jobs), 'completed': len(results), 'results': results,
                       'strict_machine_gate': 'not_run'}
            temporary = root / 'batch-status.tmp'
            temporary.write_text(json.dumps(summary, indent=2) + '\n')
            temporary.replace(root / 'batch-status.json')
            print(json.dumps({'completed': len(results), 'planned': len(jobs), **row}), flush=True)


if __name__ == '__main__':
    main()

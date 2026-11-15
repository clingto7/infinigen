"""Screen the full registry, then machine-gate every complete interface.

This coordinator never promotes readiness or starts human review. Its final
summary distinguishes a finished run from complete interface coverage.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args()
    if args.workers<1:parser.error('workers must be positive')
    root=args.output.resolve()
    root.mkdir(parents=True,exist_ok=True)
    scripts=Path(__file__).resolve().parent
    screen=root/'screen'
    subprocess.run([sys.executable,str(scripts/'spraybot_review_batch.py'),str(screen),
                    '--count','1','--workers',str(args.workers)],check=True)
    rows=json.loads((screen/'batch-status.json').read_text())['results']
    complete=[r['generator'] for r in rows if r['status'] in ('ready','candidate')]
    gate=root/'machine-gates'
    command=[sys.executable,str(scripts/'spraybot_parametric_regression.py'),str(gate),'--count','20',
             '--workers',str(args.workers)]
    for generator in complete:command.extend(['--generator',generator])
    if complete:
        process=subprocess.run(command)
        if not (gate/'regression.json').exists():
            raise RuntimeError(f'gate process exited {process.returncode} without a summary')
        checks=json.loads((gate/'regression.json').read_text())
    else:
        checks=[]
    passed=[r['generator'] for r in checks if r['status']=='passed']
    summary={'registered_interfaces':len(rows),'screen_complete':len(complete),
             'machine_gate_passed':len(passed),'passed_interfaces':passed,
             'incomplete_interfaces':[r for r in rows if r['generator'] not in complete],
             'gate_failures':[r for r in checks if r['status']!='passed'],
             'all_automatic_checks_passed':len(passed)==len(rows) and bool(rows),
             'human_review':'not_started'}
    (root/'coverage-status.json').write_text(json.dumps(summary,indent=2)+'\n')
    (screen/'automation-status.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary),flush=True)


if __name__=='__main__':
    main()

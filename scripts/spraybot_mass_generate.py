"""Resumable production generation for the reviewed Spraybot workpiece set.

This writes model-only episodes under the existing ``SPS_V2.0/<Category>/
<batch>/episode_...`` directory layout. Trajectory files are intentionally not
created by this tool.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
WORKER = Path(__file__).with_name("spraybot_mass_worker.py")
SELECTION = (
    "corner_shelf",
    "ladder_shelf",
    "metal_shelving",
    "staggered_display_shelf",
    "backed_bench",
    "backless_bench",
    "bar_chair",
    "armchair",
    "folding_chair",
    "ladder_back_chair",
    "windsor_chair",
    "cabriole_leg_table",
    "corner_desk",
    "folding_table",
    "hairpin_leg_table",
    "trestle_table",
    "workbench",
    "crib",
    "coat_rack",
    "serving_cart",
)


def dataset_category(category_id: str) -> str:
    return "".join(part.title() for part in category_id.split("_"))


def atomic_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="run directory; contains SPS_V2.0/")
    parser.add_argument("--count", type=int, default=10_000, help="models per category")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--start-seed", type=int, default=0)
    args = parser.parse_args()
    if args.count < 1 or args.workers < 1 or args.start_seed < 0:
        parser.error("count/workers must be positive and start-seed nonnegative")

    output = args.output.expanduser().resolve()
    dataset_root = output / "SPS_V2.0"
    log_root = output / "run-logs"
    dataset_root.mkdir(parents=True, exist_ok=True)
    log_root.mkdir(parents=True, exist_ok=True)

    from infinigen2.workpieces import CATEGORY_IDS as WORKPIECE_IDS
    from infinigen2.objects.spraybot import CATEGORY_IDS as SPRAYBOT_IDS

    missing = [
        category
        for category in SELECTION
        if category not in WORKPIECE_IDS and category not in SPRAYBOT_IDS
    ]
    if missing:
        raise SystemExit(f"Selected categories are not registered: {missing}")

    now_local = datetime.now(ZoneInfo("Asia/Shanghai"))
    date_tag = now_local.strftime("%m%d")
    categories = [
        {
            "category_id": category,
            "dataset_category": dataset_category(category),
            "batch_directory": (
                f"{date_tag}__{dataset_category(category)}_LDB01_{args.count}"
            ),
            "generator": (
                f"spraybot:{category}"
                if category in SPRAYBOT_IDS
                else f"workpiece:{category}"
            ),
        }
        for category in SELECTION
    ]
    manifest = {
        "format": "SPS_V2.0 model-only episodes",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            capture_output=True, check=False
        ).stdout.strip(),
        "count_per_category": args.count,
        "start_seed": args.start_seed,
        "workers": args.workers,
        "coordinate_unit": "millimeter",
        "includes_trajectory": False,
        "categories": categories,
    }
    manifest_path = output / "production_manifest.json"
    if manifest_path.exists():
        prior = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key in ("format", "count_per_category", "start_seed"):
            if prior.get(key) != manifest.get(key):
                raise SystemExit(
                    f"Output directory belongs to a different run ({key} differs): {output}"
                )
        if [x["category_id"] for x in prior["categories"]] != list(SELECTION):
            raise SystemExit(f"Output directory has a different category selection: {output}")
        categories = prior["categories"]
        manifest = prior
    else:
        atomic_json(manifest_path, manifest)

    processes = []
    stopping = False

    def stop_workers(signum, _frame):
        nonlocal stopping
        if stopping:
            return
        stopping = True
        for process, _log_file in processes:
            if process.poll() is None:
                process.terminate()
        for process, log_file in processes:
            process.wait()
            log_file.close()
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, stop_workers)
    signal.signal(signal.SIGINT, stop_workers)
    for worker_id in range(args.workers):
        log_path = log_root / f"worker-{worker_id:02d}.log"
        log_file = log_path.open("a", encoding="utf-8")
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            [str(ROOT / "src"), str(ROOT), env.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)
        process = subprocess.Popen(
            [
                sys.executable,
                str(WORKER),
                str(dataset_root),
                str(args.count),
                str(args.start_seed),
                str(worker_id),
                str(args.workers),
            ],
            cwd=ROOT,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
        processes.append((process, log_file))

    failures = []
    for worker_id, (process, log_file) in enumerate(processes):
        code = process.wait()
        log_file.close()
        if code:
            failures.append({"worker": worker_id, "exit_code": code})

    sample_failures = []
    for worker_id in range(args.workers):
        failure_path = output / f"worker-{worker_id:02d}-failures.json"
        if failure_path.exists():
            sample_failures.extend(json.loads(failure_path.read_text(encoding="utf-8")))
    summary = {
        "requested_per_category": args.count,
        "categories": [],
        "worker_failures": failures,
        "sample_failures": sample_failures,
    }
    for item in categories:
        batch = dataset_root / item["dataset_category"] / item["batch_directory"]
        rows = []
        for metadata_path in sorted(batch.glob("episode_*/metadata.json")):
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            rows.append(metadata)
        rows.sort(key=lambda row: row["seed"])
        index_path = batch / "index.jsonl"
        temporary_index = index_path.with_suffix(".jsonl.tmp")
        temporary_index.write_text(
            "".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows),
            encoding="utf-8",
        )
        os.replace(temporary_index, index_path)
        summary["categories"].append(
            {
                "category_id": item["category_id"],
                "generated": len(rows),
                "requested": args.count,
                "complete": len(rows) == args.count,
            }
        )
    atomic_json(output / "production_summary.json", summary)
    complete = all(item["complete"] for item in summary["categories"])
    print(f"generated {sum(x['generated'] for x in summary['categories'])}/"
          f"{len(categories) * args.count} models; complete={complete}")
    print(f"dataset root: {dataset_root}")
    if failures or sample_failures or not complete:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

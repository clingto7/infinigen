"""Run independent Spraybot generation probes over a seed range."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


CATEGORIES = ("slat_back_chair", "open_cell_shelf", "opaque_panel_door")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("outdir", type=Path)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--category", choices=CATEGORIES)
    args = parser.parse_args()
    if args.count < 1:
        parser.error("--count must be positive")

    args.outdir.mkdir(parents=True, exist_ok=True)
    rows = []
    failures = []
    probe = Path(__file__).with_name("spraybot_probe.py")
    for category in (args.category,) if args.category else CATEGORIES:
        for seed in range(args.count):
            outdir = args.outdir / category / str(seed)
            run = subprocess.run(
                [sys.executable, str(probe), category, str(seed), str(outdir)],
                capture_output=True,
                text=True,
            )
            if run.returncode:
                failures.append(
                    {"category_id": category, "seed": seed, "error": run.stderr[-3000:]}
                )
                continue
            rows.append(
                json.loads((outdir / "summary.json").read_text(encoding="utf-8"))
            )
        completed = sum(r["category_id"] == category for r in rows)
        print(f"{category}: {completed}/{args.count} generated", flush=True)

    summary = {
        "requested_per_category": args.count,
        "samples": rows,
        "failures": failures,
    }
    (args.outdir / "batch_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(f"failures: {len(failures)}; summary: {args.outdir / 'batch_summary.json'}")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

"""Resumable per-generator validation for Infinigen and Spraybot workpieces.

Example:
  .venv/bin/python scripts/spraybot_validate.py outputs_scratch/object-audit \
      --seeds 20 --workers 1
  .venv/bin/python scripts/spraybot_validate.py outputs_scratch/workpiece-audit \
      --category slat_back_chair --seeds 20

This checks generation and within-interface variation. It deliberately does
not decide whether two interfaces represent distinct Spraybot workpieces or
whether the generated object has a real industrial coating task.
"""

import argparse
import csv
import hashlib
import json
import os
import platform
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "src/infinigen2/manifest.json"
WORKER = Path(__file__).with_name("spraybot_validate_one.py")
ARTIFACTS = ("model.blend", "view_0.png", "view_1.png")
# Identity of the sampled grid; anything else in run_info is provenance metadata
# that may legitimately differ between a resume and the original launch.
CORE_RUN_KEYS = ("manifest_sha256", "generators", "seeds", "timeout_sec")


def _short_name(name: str) -> str:
    return name.removeprefix("spraybot:").removeprefix("workpiece:").rsplit(".", 1)[-1]


def _object_entries() -> list[str]:
    entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return [entry["name"] for entry in entries if entry["category"] == "Object"]


def _sample_dir(output: Path, index: int, name: str, seed: int) -> Path:
    return output / f"{index:03d}_{_short_name(name)}" / f"seed_{seed:04d}"


def _complete(sample_dir: Path) -> bool:
    return (sample_dir / "result.json").is_file() and all(
        (sample_dir / artifact).is_file() for artifact in ARTIFACTS
    )


def _git_state() -> dict:
    def git(*args: str) -> str | None:
        try:
            run = subprocess.run(
                ["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=10
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        return run.stdout.strip() if run.returncode == 0 else None

    commit = git("rev-parse", "HEAD")
    if commit is None:
        return {"available": False}
    status = git("status", "--porcelain") or ""
    return {
        "available": True,
        "commit": commit,
        "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "dirty": bool(status),
        "changed_files": [line[3:] for line in status.splitlines()],
    }


def _worker_env(git_state: dict) -> dict:
    env = dict(os.environ)
    if git_state.get("available"):
        env["SPRAYBOT_GIT_COMMIT"] = git_state["commit"]
        env["SPRAYBOT_GIT_BRANCH"] = git_state.get("branch") or ""
        env["SPRAYBOT_GIT_DIRTY"] = str(bool(git_state.get("dirty")))
    return env


def _run_sample(task: tuple, timeout_sec: int, worker_env: dict) -> None:
    name, seed, sample_dir = task
    sample_dir.mkdir(parents=True, exist_ok=True)
    failure_file = sample_dir / "failure.json"
    if failure_file.exists():
        failure_file.unlink()
    try:
        run = subprocess.run(
            [sys.executable, str(WORKER), name, str(seed), str(sample_dir)],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            env=worker_env,
        )
        if run.returncode == 0 and _complete(sample_dir):
            return
        error = {
            "generator": name,
            "seed": seed,
            "kind": "worker_failure",
            "returncode": run.returncode,
            "stderr_tail": run.stderr[-6000:],
            "stdout_tail": run.stdout[-1000:],
        }
    except subprocess.TimeoutExpired as exc:
        error = {
            "generator": name,
            "seed": seed,
            "kind": "timeout",
            "timeout_sec": timeout_sec,
            "stderr_tail": (
                (exc.stderr or b"").decode(errors="replace")
                if isinstance(exc.stderr, bytes)
                else (exc.stderr or "")
            )[-3000:],
        }
    failure_file.write_text(json.dumps(error, indent=2) + "\n", encoding="utf-8")


def _summarize(output: Path, names: list[str], seeds: list[int]) -> dict:
    summary = {"registered_object_interfaces": len(names), "seeds": seeds, "interfaces": []}
    review_rows = []
    interface_rows = []
    for index, name in enumerate(names):
        rows = []
        for seed in seeds:
            sample_dir = _sample_dir(output, index, name, seed)
            rel = sample_dir.relative_to(output)
            if _complete(sample_dir):
                data = json.loads((sample_dir / "result.json").read_text(encoding="utf-8"))
                metrics = data["metrics"]
                spray_checks = data.get("spray_checks")
                status = "generated"
            elif (sample_dir / "failure.json").is_file():
                data = json.loads((sample_dir / "failure.json").read_text(encoding="utf-8"))
                metrics = {}
                spray_checks = None
                status = data["kind"]
            else:
                metrics = {}
                spray_checks = None
                status = "pending"
            rows.append({"seed": seed, "status": status, "metrics": metrics, "spray_checks": spray_checks})
            review_rows.append(
                {
                    "generator": name,
                    "seed": seed,
                    "status": status,
                    "model": str(rel / "model.blend") if status == "generated" else "",
                    "view_0": str(rel / "view_0.png") if status == "generated" else "",
                    "view_1": str(rel / "view_1.png") if status == "generated" else "",
                    "extent_m": json.dumps(metrics.get("extent_m", [])),
                    "triangles": metrics.get("triangles", ""),
                    "near_zero_triangle_fraction": metrics.get(
                        "near_zero_triangle_fraction", ""
                    ),
                    "spray_metadata_passed": spray_checks["passed"] if spray_checks else "",
                    "spray_metadata_issues": ";".join(spray_checks["issues"]) if spray_checks else "",
                    "target_area_fraction": spray_checks.get("target_area_fraction", "") if spray_checks else "",
                }
            )
        generated = [row["metrics"] for row in rows if row["status"] == "generated"]
        flags = []
        if len(generated) < len(seeds):
            flags.append("incomplete_or_generation_failure")
        if generated and any(
            metric["near_zero_triangle_fraction"] > 0.01 for metric in generated
        ):
            flags.append("degenerate_geometry")
        unique_geometry = len({m["geometry_sha256"] for m in generated})
        unique_normalized = len({m["normalized_shape_sha256"] for m in generated})
        if len(generated) > 1 and unique_normalized < 2:
            flags.append("no_shape_variation_detected")
        checks = [row["spray_checks"] for row in rows if row["status"] == "generated"]
        if generated and any(
            m.get("spray_part") is None or m.get("spray_target") is None for m in generated
        ):
            flags.append("spray_metadata_missing")
        if any(check is None for check in checks):
            flags.append("full_spray_checks_not_run")
        if any(check is not None and not check["passed"] for check in checks):
            flags.append("spray_metadata_invalid")
        metadata_passed = bool(checks) and len(checks) == len(seeds) and all(
            check is not None and check["passed"] for check in checks
        )
        geometry_passed = len(generated) == len(seeds) and "degenerate_geometry" not in flags
        variation_detected = (
            unique_normalized > 1 if len(seeds) > 1 and len(generated) > 1 else None
        )
        if len(seeds) < 2:
            flags.append("variation_not_tested_single_seed")
        triangle_counts = [metric["triangles"] for metric in generated]
        near_zero_fractions = [metric["near_zero_triangle_fraction"] for metric in generated]
        target_area_fractions = [
            check["target_area_fraction"] for check in checks
            if check is not None and check.get("target_area_fraction") is not None
        ]
        if len(generated) < len(seeds):
            next_step = "fix_generation"
        elif not geometry_passed:
            next_step = "inspect_geometry"
        elif variation_detected is not True:
            next_step = "sample_or_fix_variation"
        elif not metadata_passed:
            next_step = "define_coating_task_and_add_semantic_tags"
        else:
            next_step = "human_category_and_coating_review"
        flags.append("human_category_and_coating_review_required")
        summary["interfaces"].append(
            {
                "index": index,
                "generator": name,
                "generated": len(generated),
                "requested": len(seeds),
                "unique_geometry_hashes": unique_geometry,
                "unique_normalized_shape_hashes": unique_normalized,
                "geometry_screen_passed": geometry_passed,
                "variation_detected": variation_detected,
                "spray_metadata_passed": metadata_passed,
                "automatic_screen_passed": bool(geometry_passed and variation_detected and metadata_passed),
                "next_step": next_step,
                "flags": flags,
                "samples": rows,
            }
        )
        interface_rows.append({
            "generator": name,
            "generated": len(generated),
            "requested": len(seeds),
            "geometry_screen_passed": geometry_passed,
            "variation_detected": variation_detected,
            "spray_metadata_passed": metadata_passed,
            "automatic_screen_passed": bool(geometry_passed and variation_detected and metadata_passed),
            "next_step": next_step,
            "triangles_min": min(triangle_counts) if triangle_counts else "",
            "triangles_max": max(triangle_counts) if triangle_counts else "",
            "near_zero_triangle_fraction_max": max(near_zero_fractions) if near_zero_fractions else "",
            "target_area_fraction_min": min(target_area_fractions) if target_area_fractions else "",
            "target_area_fraction_max": max(target_area_fractions) if target_area_fractions else "",
            "flags": ";".join(flags),
            "contact_sheet": f"contact_sheets/{index:03d}_{_short_name(name)}.jpg",
        })
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    with (output / "review.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=review_rows[0].keys())
        writer.writeheader()
        writer.writerows(review_rows)
    with (output / "interfaces.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=interface_rows[0].keys())
        writer.writeheader()
        writer.writerows(interface_rows)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--start-seed", type=int, default=0)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--timeout-sec", type=int, default=300)
    parser.add_argument("--only", action="append", help="full or short generator name")
    parser.add_argument(
        "--category", action="append",
        help="registered Object name or fixed Spraybot workpiece ID; repeatable",
    )
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument("--resummarize", action="store_true", help="rebuild summaries from saved results")
    args = parser.parse_args()
    if min(args.seeds, args.workers, args.timeout_sec) < 1:
        parser.error("--seeds, --workers, and --timeout-sec must be positive")
    if args.category and args.only:
        parser.error("use --category or --only, not both")
    object_names = _object_entries()
    if args.category:
        from infinigen2.objects.spraybot import CATEGORY_IDS
        from infinigen2.workpieces import CATEGORY_IDS as WORKPIECE_IDS

        names = []
        for category in args.category:
            if category in CATEGORY_IDS:
                names.append(f"spraybot:{category}")
                continue
            if category in WORKPIECE_IDS:
                names.append(f"workpiece:{category}")
                continue
            matches = [
                name for name in object_names
                if name == category or _short_name(name) == category
            ]
            if len(matches) != 1:
                parser.error(f"unknown or ambiguous category/interface: {category}")
            names.append(matches[0])
        if len(names) != len(set(names)):
            parser.error("duplicate --category selection")
    else:
        names = object_names
    if args.only:
        requested = set(args.only)
        names = [name for name in names if name in requested or _short_name(name) in requested]
        if not names:
            parser.error("--only did not match any registered Object interface")
    seeds = list(range(args.start_seed, args.start_seed + args.seeds))
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    git_state = _git_state()
    run_info = {
        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "argv": sys.argv,
        "python_executable": sys.executable,
        "python_version": sys.version,
        "numpy_version": np.__version__,
        "platform": platform.platform(),
        "hostname": platform.node(),
        "git": git_state,
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "worker_sha256": hashlib.sha256(WORKER.read_bytes()).hexdigest(),
        "generators": names,
        "seeds": seeds,
        "timeout_sec": args.timeout_sec,
    }
    info_path = output / "run_info.json"
    if info_path.exists():
        prior = json.loads(info_path.read_text(encoding="utf-8"))
        core = {key: run_info[key] for key in CORE_RUN_KEYS}
        prior_core = {key: prior.get(key) for key in CORE_RUN_KEYS}
        if prior_core != core:
            parser.error("output directory belongs to a different manifest or run configuration")
        if prior != run_info:
            prior_names = prior.get("generators", [])
            same_slots = (
                prior.get("seeds") == seeds
                and prior.get("timeout_sec") == args.timeout_sec
                and [_short_name(name) for name in prior_names]
                == [_short_name(name) for name in names]
            )
            has_success = any(
                _complete(_sample_dir(output, index, name, seed))
                for index, name in enumerate(names) for seed in seeds
            ) if same_slots else True
            if not args.resummarize and same_slots and not has_success:
                info_path.write_text(json.dumps(run_info, indent=2) + "\n", encoding="utf-8")
                args.retry_failed = True
                print("retrying failure-only output with updated interface", flush=True)
            else:
                info_path.write_text(json.dumps(run_info, indent=2) + "\n", encoding="utf-8")
                changed = sorted(
                    key for key in set(run_info) | set(prior)
                    if run_info.get(key) != prior.get(key)
                )
                print(f"warning: run metadata updated in place: {changed}", flush=True)
                print(
                    "warning: samples already in this directory keep their original "
                    "per-sample provenance in result.json",
                    flush=True,
                )
    else:
        info_path.write_text(json.dumps(run_info, indent=2) + "\n", encoding="utf-8")
    if args.resummarize:
        _summarize(output, names, seeds)
        print(f"summaries rebuilt from saved results: {output}")
        return
    tasks = []
    for index, name in enumerate(names):
        for seed in seeds:
            sample_dir = _sample_dir(output, index, name, seed)
            if _complete(sample_dir):
                continue
            if (sample_dir / "failure.json").exists() and not args.retry_failed:
                continue
            tasks.append((name, seed, sample_dir))
    print(f"Generator interfaces: {len(names)}; samples: {len(names) * len(seeds)}; pending: {len(tasks)}", flush=True)
    worker_env = _worker_env(git_state)
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(_run_sample, task, args.timeout_sec, worker_env)
            for task in tasks
        ]
        for completed, future in enumerate(as_completed(futures), 1):
            future.result()
            if completed % 20 == 0 or completed == len(tasks):
                summary = _summarize(output, names, seeds)
                generated = sum(item["generated"] for item in summary["interfaces"])
                print(f"processed={completed}/{len(tasks)} generated={generated}", flush=True)
    summary = _summarize(output, names, seeds)
    generated = sum(item["generated"] for item in summary["interfaces"])
    print(f"complete: {generated}/{len(names) * len(seeds)} samples; {output}")


if __name__ == "__main__":
    main()

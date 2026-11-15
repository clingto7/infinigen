"""Run, validate, package and upload the 23-category prior overlay on radar.

Uploads are opt-in. A category is published only after every episode passes OBJ
replay verification. The complete release manifest is published last.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import threading


def digest(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--production", type=Path, required=True)
    p.add_argument("--spraybot", type=Path, required=True)
    p.add_argument("--generator-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--workers", type=int, default=12)
    p.add_argument("--upload", action="store_true")
    p.add_argument("--ms", default="ms")
    p.add_argument("--repo", default="v1Nyl777/Spraybot_SPS_V2_0_3x8098_20260901")
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=True)
    logs = a.output / "logs"
    logs.mkdir(exist_ok=True)
    release = a.output / "release"
    release.mkdir(exist_ok=True)
    production = json.loads((a.production / "production_manifest.json").read_text())
    categories = [(x["dataset_category"], x["batch_directory"], production["count_per_category"])
                  for x in production["categories"]]
    categories += [(c, f"0901__{c}_LDB01_8098", 8098) for c in ("Chair", "OpusChair", "CarBumper")]
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    runner = Path(__file__).with_name("spraybot_recover_priors.py")
    upload_lock = threading.Lock()

    def upload(file, remote):
        if a.upload:
            with upload_lock, (logs / "upload.log").open("a") as log:
                subprocess.run([a.ms, "upload", a.repo, str(file), remote, "--repo-type", "dataset"],
                               stdout=log, stderr=subprocess.STDOUT, check=True, env=env)

    # Save source files defining concrete call parameters and native records.
    snapshot = release / "generation-source.tar.gz"
    source_files = {}
    with tarfile.open(snapshot, "w:gz") as archive:
        for prefix, root in (("production", a.generator_root), ("spraybot", a.spraybot),
                             ("recovery", runner.resolve().parents[1])):
            files = list((root / "src").rglob("*.py")) if prefix == "production" else []
            if prefix == "spraybot":
                files = list((root / "datagen").rglob("*.py")) + list((root / "datagen").rglob("*.yaml"))
            if prefix == "recovery":
                files = [runner, Path(__file__).resolve(), root / "src/infinigen2/util/construction_record.py"]
            files += [root / f for f in ("pyproject.toml", "uv.lock") if (root / f).is_file()]
            for file in sorted(set(files)):
                path = f"{prefix}/{file.relative_to(root)}"
                archive.add(file, arcname=path)
                source_files[path] = digest(file)
    environment = {}
    for name in ("bpy", "numpy", "procfunc", "infinigen", "scipy"):
        try:
            environment[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            environment[name] = None
    provenance = {"python": sys.version, "packages": environment, "source_files": source_files,
                  "source_archive_sha256": digest(snapshot), "original_production_manifest": production}
    provenance_path = release / "provenance.json"
    provenance_path.write_text(json.dumps(provenance, indent=2) + "\n")
    upload(snapshot, "generation-priors/v1/generation-source.tar.gz")
    upload(provenance_path, "generation-priors/v1/provenance.json")
    guide = runner.resolve().parents[1] / "docs/spraybot/prior-overlay.md"
    upload(guide, "generation-priors/v1/README.md")

    def recover(item):
        category, batch, count = item
        command = [sys.executable, str(runner), "--production", str(a.production),
                   "--spraybot", str(a.spraybot), "--generator-root", str(a.generator_root),
                   "--output", str(a.output / "overlay"), "--category", category]
        with (logs / f"{category}.log").open("a") as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=env, check=True)
        base = a.output / "overlay/SPS_V2.0" / category / batch
        summary = json.loads((base / "recovery-0.json").read_text())
        if summary["expected"] != count or summary["verified"] != count or summary["failures"]:
            raise ValueError(f"Incomplete category: {category}")
        episodes = list(base.glob("episode_*/structure.json"))
        if len(episodes) != count:
            raise ValueError(f"Unexpected episode count: {category}")
        seen_seeds = set()
        for file in episodes:
            record = json.loads(file.read_text())
            if record["mesh_verification"] != "byte_identical_replay" or record["seed"] in seen_seeds:
                raise ValueError(f"Invalid verification/duplicate seed: {file}")
            seen_seeds.add(record["seed"])
            if not (file.parent / "face_attributes.npz").is_file():
                raise ValueError(f"Missing face attributes: {file}")
        relative = Path("SPS_V2.0") / category / batch
        target = release / "SPS_V2.0" / category / f"{batch}.priors-v1.tar.zst"
        target.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["tar", "--zstd", "-cf", str(target), "-C", str(a.output / "overlay"), str(relative)], check=True)
        sha = digest(target)
        sidecar = Path(str(target) + ".sha256")
        sidecar.write_text(f"{sha}  {target.name}\n")
        remote = target.relative_to(release).as_posix()
        # Each category upload has its own completion log entry. Full manifest is last.
        upload(target, remote)
        upload(sidecar, remote + ".sha256")
        result = {"category": category, "episodes": count, "archive": remote,
                  "sha256": sha, "bytes": target.stat().st_size,
                  "uploaded": a.upload, "all_obj_replays_byte_identical": True}
        (release / f"{category}.complete.json").write_text(json.dumps(result) + "\n")
        print(json.dumps(result), flush=True)
        return result

    results = []
    errors = []
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        futures = {pool.submit(recover, item): item[0] for item in categories}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as error:
                errors.append({"category": futures[future], "error": str(error)})
                print(json.dumps(errors[-1]), flush=True)
    manifest = {"schema": "spraybot.prior-release.v1", "complete": not errors,
                "total_verified_episodes": sum(x["episodes"] for x in results),
                "categories": sorted(results, key=lambda x: x["category"]), "errors": errors,
                "source_archive_sha256": provenance["source_archive_sha256"],
                "representation": "native priors for 3 categories; executed source parameters for 20 categories"}
    manifest_path = release / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    if errors:
        raise SystemExit("Recovery incomplete; complete manifest was not published")
    upload(manifest_path, "generation-priors/v1/manifest.json")
    print(f"COMPLETE verified={manifest['total_verified_episodes']} uploaded={a.upload}", flush=True)


if __name__ == "__main__":
    main()

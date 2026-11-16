"""Git-tracked human decisions for model-bound trajectory artifacts."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from spraybot_interface_state import PROJECT, record_path


RECORDS = PROJECT / "reviews" / "trajectories"
SCHEMA = "spraybot.trajectory-review.v1"


def artifact_evidence(interface_id: str, review_root: Path, trajectory_root: Path) -> list[dict]:
    if not interface_id.startswith("workpiece:"):
        raise ValueError("trajectory review requires a workpiece interface")
    evidence = []
    for seed in range(10):
        episode = f"seed_{seed:010d}"
        model = review_root / "interfaces" / interface_id / "episodes" / episode / "model.json"
        artifact = trajectory_root / interface_id / f"{episode}.json"
        if not model.is_file() or not artifact.is_file():
            raise ValueError(f"missing paired trajectory: {interface_id} {episode}")
        raw = artifact.read_bytes()
        data = json.loads(raw)
        check = data.get("check", {})
        if data.get("interface_id") != interface_id or data.get("seed") != seed:
            raise ValueError(f"trajectory identity mismatch: {artifact}")
        if data.get("model_sha256") != hashlib.sha256(model.read_bytes()).hexdigest():
            raise ValueError(f"trajectory model hash mismatch: {artifact}")
        if check.get("machine_gate") != "passed":
            raise ValueError(f"trajectory machine gate has not passed: {artifact}")
        evidence.append({"seed": seed, "trajectory_sha256": hashlib.sha256(raw).hexdigest(),
                         "model_sha256": data["model_sha256"],
                         "coverage_fraction": check["target_centroid_within_threshold_fraction"],
                         "ray_samples": check["path_ray_check"]["sample_count"]})
    return evidence


def path_for(interface_id: str) -> Path:
    return record_path(interface_id, RECORDS)


def read(interface_id: str, review_root: Path | None, trajectory_root: Path | None) -> dict:
    path = path_for(interface_id)
    data = json.loads(path.read_text()) if path.exists() else {
        "schema": SCHEMA, "interface_id": interface_id, "status": "pending",
        "reviewer": "", "notes": "", "seed_issues": [], "evidence": [], "history": []}
    if data.get("schema") != SCHEMA or data.get("interface_id") != interface_id:
        raise ValueError("invalid trajectory review record")
    try:
        current = artifact_evidence(interface_id, review_root, trajectory_root) if review_root and trajectory_root else []
        gate_error = None if current else "trajectory root is unavailable"
    except ValueError as exc:
        current, gate_error = [], str(exc)
    fresh = bool(current and current == data.get("evidence"))
    git_status = subprocess.run(["git", "status", "--porcelain", "--", str(path)],
                                cwd=PROJECT, capture_output=True, text=True, check=True).stdout
    return {**data, "status": "pending" if data["status"] == "accepted" and not fresh else data["status"],
            "machine_gate": "passed" if current else "failed",
            "machine_gate_error": gate_error, "evidence_current": fresh,
            "committed": path.exists() and not git_status.strip()}


def save(request: dict, review_root: Path, trajectory_root: Path) -> Path:
    interface_id = request["interface_id"]
    status = request["status"]
    if status not in {"pending", "accepted", "needs_fix"}:
        raise ValueError("unknown trajectory review status")
    try:
        current = artifact_evidence(interface_id, review_root, trajectory_root)
    except ValueError:
        if status == "accepted":
            raise
        current = []
    reviewer = str(request.get("reviewer", "")).strip()
    if not reviewer:
        raise ValueError("reviewer is required")
    issues = request.get("seed_issues", [])
    if not isinstance(issues, list) or any(
        not isinstance(item, dict) or type(item.get("seed")) is not int
        or not 0 <= item["seed"] < 10 or not str(item.get("note", "")).strip()
        for item in issues
    ):
        raise ValueError("seed issues must have a seed 0–9 and a nonempty note")
    if status == "accepted" and issues:
        raise ValueError("clear unresolved seed issues before accepting")
    old = read(interface_id, review_root, trajectory_root)
    if status == "accepted" and old["status"] == "needs_fix" and old.get("evidence") == current:
        raise ValueError("needs_fix requires a revised trajectory before acceptance")
    history = old.get("history", [])
    if old.get("reviewed_at"):
        history = [*history, {key: old.get(key) for key in
                             ("status", "reviewer", "notes", "seed_issues", "evidence", "reviewed_at")}]
    data = {"schema": SCHEMA, "interface_id": interface_id, "status": status,
            "reviewer": reviewer, "notes": str(request.get("notes", "")).strip(),
            "seed_issues": issues, "evidence": current, "history": history,
            "reviewed_at": datetime.now(timezone.utc).isoformat()}
    path = path_for(interface_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)
    return path

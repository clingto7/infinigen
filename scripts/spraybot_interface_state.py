"""Git-tracked, per-interface review decisions. Review roots contain evidence only."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
RECORDS = PROJECT / "reviews" / "interfaces"
SCHEMA = "spraybot.interface-review.v1"
STATES = {"developing", "awaiting_review", "needs_fix", "ready"}


def record_path(generator: str, records: Path = RECORDS) -> Path:
    group, separator, name = generator.partition(":")
    if not separator or group not in {"workpiece", "spraybot"} or not name or any(
        char not in "abcdefghijklmnopqrstuvwxyz0123456789_" for char in name
    ):
        raise ValueError(f"invalid interface id: {generator!r}")
    return records / f"{group}__{name}.json"


def read_record(generator: str, records: Path = RECORDS) -> dict:
    path = record_path(generator, records)
    if not path.exists():
        return {"schema": SCHEMA, "interface_id": generator, "status": "developing",
                "machine_gate": None, "human_review": None}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA or data.get("interface_id") != generator or data.get("status") not in STATES:
        raise ValueError(f"invalid interface review record: {path}")
    return data


def write_record(data: dict, records: Path = RECORDS) -> Path:
    path = record_path(data["interface_id"], records)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)
    return path


def archive_review(data: dict) -> None:
    if data.get("human_review") is not None:
        data.setdefault("review_history", []).append({
            "human_review": data["human_review"],
            "machine_gate": data.get("machine_gate"),
        })


def committed(generator: str, records: Path = RECORDS) -> bool:
    path = record_path(generator, records)
    if not path.exists():
        return False
    result = subprocess.run(["git", "status", "--porcelain", "--", str(path)],
                            cwd=PROJECT, capture_output=True, text=True, check=True)
    return not result.stdout.strip()


def read_committed_record(generator: str, records: Path = RECORDS) -> dict:
    path = record_path(generator, records)
    relative = path.relative_to(PROJECT)
    result = subprocess.run(["git", "show", f"HEAD:{relative.as_posix()}"],
                            cwd=PROJECT, capture_output=True, text=True)
    if result.returncode:
        return {"schema": SCHEMA, "interface_id": generator, "status": "developing",
                "machine_gate": None, "human_review": None}
    data = json.loads(result.stdout)
    if data.get("schema") != SCHEMA or data.get("interface_id") != generator or data.get("status") not in STATES:
        raise ValueError(f"invalid committed interface review record: {relative}")
    return data


def record_machine_pass(generator: str, check_path: Path, records: Path = RECORDS,
                        source_commit: str | None = None) -> Path:
    raw = check_path.read_bytes()
    check = json.loads(raw)
    geometry = check.get("geometry_gate", {})
    invariance = check.get("capture_invariance", {})
    category = generator.split(":", 1)[1]
    if (geometry.get("status") != "parametric_geometry_gate_passed"
            or invariance.get("status") != "capture_invariance_passed"
            or geometry.get("category_id") != category
            or invariance.get("category_id") != category
            or geometry.get("episodes", 0) < 20
            or len(invariance.get("seeds_compared", [])) < 20):
        raise ValueError(f"machine check did not pass for {generator}: {check_path}")
    data = read_record(generator, records)
    digest = hashlib.sha256(raw).hexdigest()
    previous = data.get("machine_gate") or {}
    if data["status"] == "ready" and previous.get("sha256") == digest:
        return record_path(generator, records)
    if (data["status"] == "needs_fix" and previous.get("sha256") == digest
            and previous.get("source_commit") == source_commit):
        raise ValueError("needs_fix requires new machine evidence or source revision")
    archive_review(data)
    data.update(status="awaiting_review", machine_gate={
        "status": "passed", "sha256": digest,
        "source_commit": source_commit,
        "geometry_episodes": geometry["episodes"],
        "invariance_seeds": len(invariance["seeds_compared"]),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }, human_review=None)
    return write_record(data, records)


def save_human_review(generator: str, review: dict, records: Path = RECORDS) -> Path:
    data = read_record(generator, records)
    if not data.get("machine_gate") or data["machine_gate"].get("status") != "passed":
        raise ValueError("interface has no recorded machine gate")
    status = review["status"]
    if status not in {"pending", "accepted", "needs_fix"}:
        raise ValueError("unknown human review status")
    if data["status"] == "needs_fix" and status != "needs_fix":
        raise ValueError("needs_fix requires a new machine gate before acceptance")
    if status == "accepted" and (review.get("field_issues") or review.get("seed_issues")):
        raise ValueError("accepted review still has unresolved issues")
    reviewer = review.get("reviewer", "").strip()
    if not reviewer:
        raise ValueError("reviewer is required")
    data["human_review"] = {**review, "interface_id": generator, "reviewer": reviewer,
                            "reviewed_at": datetime.now(timezone.utc).isoformat()}
    data["status"] = {"pending": "awaiting_review", "accepted": "ready",
                      "needs_fix": "needs_fix"}[status]
    return write_record(data, records)


def invalidate(generator: str, reason: str, records: Path = RECORDS) -> Path:
    if not reason.strip():
        raise ValueError("invalidation reason is required")
    data = read_record(generator, records)
    archive_review(data)
    data.update(status="developing", machine_gate=None, human_review=None,
                invalidation={"reason": reason.strip(),
                              "recorded_at": datetime.now(timezone.utc).isoformat()})
    return write_record(data, records)


def review_for_ui(generator: str, records: Path = RECORDS) -> dict:
    data = read_record(generator, records)
    review = data.get("human_review") or {"interface_id": generator, "status": "pending",
                                           "notes": "", "field_issues": [], "seed_issues": []}
    return {**review, "interface_status": data["status"], "committed": committed(generator, records)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    one = sub.add_parser("machine-pass")
    one.add_argument("generator")
    one.add_argument("machine_check", type=Path)
    batch = sub.add_parser("import-automation")
    batch.add_argument("automation_status", type=Path)
    invalid = sub.add_parser("invalidate")
    invalid.add_argument("generator")
    invalid.add_argument("reason")
    args = parser.parse_args()
    if args.command == "machine-pass":
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT,
                                  capture_output=True, text=True, check=True).stdout.strip()
        print(record_machine_pass(args.generator, args.machine_check, source_commit=revision))
    elif args.command == "invalidate":
        print(invalidate(args.generator, args.reason))
    else:
        status = json.loads(args.automation_status.read_text())
        for generator in status["passed_interfaces"]:
            check = Path(status["machine_gate_evidence"][generator])
            print(record_machine_pass(generator, check))


if __name__ == "__main__":
    main()

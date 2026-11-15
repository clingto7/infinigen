"""Small, dependency-free contract for Web review roots.

The root is intentionally boring: one manifest, one directory per interface,
and immutable seed episodes.  This module is also used by the UI server so a
reviewer can load an existing run without importing Blender.
"""

from __future__ import annotations

import json
from pathlib import Path


SCHEMA = "spraybot.review-root.v1"
REVIEW_FIELDS = frozenset({
    "model", "spray_part", "spray_target", "spray_target_reason",
    "geometry_accessible", "max_passable_radius_m", "structure_priors", "parametric",
})


def _safe_id(value: str) -> str:
    value = str(value)
    if not value or value in {".", ".."} or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-:." for char in value):
        raise ValueError(f"unsafe review-root id: {value!r}")
    return value


def ensure(root: Path) -> Path:
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / "review_manifest.json"
    if not manifest.exists():
        manifest.write_text(json.dumps({
            "schema": SCHEMA,
            "review_root": root.name,
            "interfaces": {},
        }, indent=2) + "\n", encoding="utf-8")
    return root


def load(root: Path) -> dict:
    root = Path(root).resolve()
    path = root / "review_manifest.json"
    if not path.is_file():
        return {"schema": SCHEMA, "review_root": root.name, "interfaces": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA:
        raise ValueError(f"unsupported review root schema: {data.get('schema')}")
    data.setdefault("interfaces", {})
    return data


def _save_manifest(root: Path, data: dict) -> None:
    (root / "review_manifest.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def save_episode(root: Path, payload: dict) -> Path:
    root = ensure(root)
    generator = _safe_id(payload["generator"])
    seed = int(payload["seed"])
    if seed < 0:
        raise ValueError("seed must be non-negative")
    interface_dir = root / "interfaces" / generator
    episode = interface_dir / "episodes" / f"seed_{seed:010d}"
    episode.mkdir(parents=True, exist_ok=True)
    model = episode / "model.json"
    if model.exists():
        saved = json.loads(model.read_text(encoding="utf-8"))
        if saved != payload:
            if (saved.get("parametric_description_status") != "incomplete"
                    or payload.get("parametric_description_status") not in {"candidate", "ready"}):
                raise FileExistsError(f"immutable episode already exists: {episode}")
            archive = episode / "model.incomplete.json"
            if archive.exists() and json.loads(archive.read_text(encoding="utf-8")) != saved:
                raise FileExistsError(f"incomplete episode archive already exists: {archive}")
            temporary = episode / "model.tmp"
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
            )
            model.replace(archive)
            temporary.replace(model)
    else:
        temporary = episode / "model.tmp"
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8"
        )
        temporary.replace(model)
    manifest = load(root)
    entries = manifest.setdefault("interfaces", {})
    entries[generator] = {
        "id": generator,
        "label": payload.get("label") or generator,
        "group": payload.get("group") or generator.split(":", 1)[0],
        "episodes": sorted(path.name for path in (interface_dir / "episodes").iterdir() if path.is_dir()),
    }
    _save_manifest(root, manifest)
    return episode


def index(root: Path) -> dict:
    root = Path(root).resolve()
    manifest = load(root)
    interfaces = []
    for generator, entry in sorted(manifest.get("interfaces", {}).items()):
        item = dict(entry)
        item.setdefault("id", generator)
        item.setdefault("label", generator)
        item.setdefault("group", generator.split(":", 1)[0])
        episode_dir = root / "interfaces" / generator / "episodes"
        item["episodes"] = sorted(path.name for path in episode_dir.iterdir() if path.is_dir()) if episode_dir.is_dir() else []
        interfaces.append(item)
    return {"schema": SCHEMA, "root": str(root), "interfaces": interfaces,
            "review_enabled": review_enabled(root)}


def review_enabled(root: Path) -> bool:
    """The current campaign opens human review only after full automatic gates."""
    path = Path(root) / "automation-status.json"
    if not path.is_file():
        return False
    status = json.loads(path.read_text(encoding="utf-8"))
    passed = status.get("passed_interfaces", [])
    expected = set(load(root).get("interfaces", {}))
    return (bool(expected) and status.get("all_automatic_checks_passed") is True
            and status.get("registered_interfaces") == len(expected)
            and len(passed) == len(expected) and set(passed) == expected
            and not status.get("incomplete_interfaces") and not status.get("gate_failures"))


def read_episode(root: Path, generator: str, episode: str) -> dict:
    generator = _safe_id(generator)
    episode = _safe_id(episode)
    path = Path(root).resolve() / "interfaces" / generator / "episodes" / episode / "model.json"
    if not path.is_file():
        raise FileNotFoundError(episode)
    return json.loads(path.read_text(encoding="utf-8"))


def save_review(root: Path, generator: str, review: dict) -> Path:
    root = ensure(root)
    if not review_enabled(root):
        raise ValueError("human review requires automatic checks for every registered interface")
    generator = _safe_id(generator)
    status = review.get("status")
    if generator not in load(root)["interfaces"]:
        raise ValueError("interface is absent from this review root")
    if status not in {"pending", "accepted", "needs_fix", "rejected"}:
        raise ValueError("review status must be pending, accepted, needs_fix, or rejected")
    issues = review.get("field_issues", [])
    if not isinstance(issues, list):
        raise ValueError("field_issues must be a list")
    seen = set()
    for issue in issues:
        if not isinstance(issue, dict) or issue.get("field") not in REVIEW_FIELDS:
            raise ValueError("field issue has an unknown field")
        seed = issue.get("seed")
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ValueError("field issue has an invalid seed")
        if not (root / "interfaces" / generator / "episodes" / f"seed_{seed:010d}" / "model.json").is_file():
            raise ValueError("field issue seed is absent from this review root")
        if not isinstance(issue.get("note"), str) or not issue["note"].strip():
            raise ValueError("field issue needs a nonempty note")
        key = (seed, issue["field"])
        if key in seen:
            raise ValueError("duplicate field issue for one seed")
        seen.add(key)
    if status == "accepted" and (issues or review.get("seed_issues")):
        raise ValueError("accepted review still has unresolved issues")
    path = root / "interfaces" / generator / "human-review.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({**review, "interface_id": generator}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def read_review(root: Path, generator: str) -> dict:
    path = Path(root).resolve() / "interfaces" / _safe_id(generator) / "human-review.json"
    if not path.is_file():
        return {"interface_id": generator, "status": "pending", "notes": "", "seed_issues": []}
    return json.loads(path.read_text(encoding="utf-8"))

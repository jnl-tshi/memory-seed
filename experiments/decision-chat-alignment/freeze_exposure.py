"""Freeze a private, metadata-only baseline of local Codex rollout exposure.

This is prospective: every root present at freeze time is treated as already
exposed or of unknown prior exposure. It cannot retroactively certify old
cases as fresh, and it never copies conversation text into the manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


def _alignment_module() -> Any:
    path = Path(__file__).with_name("align_decisions.py")
    name = "decision_chat_alignment_for_exposure"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot load canonical rollout metadata reader")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def resolve_roots(metas: Sequence[Any]) -> dict[str, tuple[str, str | None]]:
    """Resolve logical session roots; unresolved lineage never becomes a root."""
    parents: dict[str, set[str | None]] = defaultdict(set)
    for meta in metas:
        parents[meta.session_id].add(meta.parent_thread_id)
    result: dict[str, tuple[str, str | None]] = {}
    visiting: set[str] = set()

    def visit(session_id: str) -> tuple[str, str | None]:
        if session_id in result:
            return result[session_id]
        if session_id in visiting:
            return "cycle", None
        values = parents.get(session_id)
        if values is None:
            return "missing_parent", None
        if len(values) != 1:
            result[session_id] = ("ambiguous_parent", None)
            return result[session_id]
        parent = next(iter(values))
        if parent is None:
            result[session_id] = ("resolved", session_id)
            return result[session_id]
        if parent not in parents:
            result[session_id] = ("missing_parent", None)
            return result[session_id]
        visiting.add(session_id)
        parent_status, root = visit(parent)
        visiting.remove(session_id)
        if parent_status == "cycle":
            result[session_id] = ("cycle", None)
        elif parent_status != "resolved":
            result[session_id] = ("ancestor_unresolved", None)
        else:
            result[session_id] = ("resolved", root)
        return result[session_id]

    for session_id in sorted(parents):
        visit(session_id)
    return result


def validate_output_path(path: Path) -> Path:
    target = path.resolve()
    if target.exists():
        raise FileExistsError(f"private snapshot already exists: {target}")
    if not target.parent.is_dir():
        raise ValueError("private snapshot parent directory must already exist")
    if any((parent / ".git").exists() for parent in (target.parent, *target.parents)):
        raise ValueError("private snapshot must be outside a Git checkout")
    return target


def prospective_roots(baseline: dict, current: dict) -> set[str]:
    """Return roots absent from the local baseline and started afterwards."""
    if baseline.get("schema_version") != 2 or current.get("schema_version") != 2:
        raise ValueError("prospective freshness requires a timestamped baseline and current snapshot")
    try:
        if any(row.get("lineage_status") != "resolved"
               for snapshot in (baseline, current) for row in snapshot["rollouts"]):
            raise ValueError("unresolved rollout metadata prevents a freshness claim")
        freeze_time = datetime.fromisoformat(baseline["created_at_utc"].replace("Z", "+00:00"))
        current_time = datetime.fromisoformat(current["created_at_utc"].replace("Z", "+00:00"))
        previous = {
            row["root_session_id"] for row in baseline["rollouts"]
            if row.get("root_session_id")
        }
        grouped: dict[str, list[datetime]] = defaultdict(list)
        for row in current["rollouts"]:
            root = row.get("root_session_id")
            if row.get("lineage_status") != "resolved" or not root or root in previous:
                continue
            stamp = row.get("session_started_at_utc")
            if not stamp:
                continue
            grouped[root].append(datetime.fromisoformat(stamp.replace("Z", "+00:00")))
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("invalid timestamped exposure snapshots") from exc
    return {root for root, starts in grouped.items()
            if starts and freeze_time < min(starts) <= current_time}


def _file_digest(path: Path) -> tuple[str, int, bool]:
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    after = path.stat()
    stable = (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
    return digest.hexdigest(), after.st_size, stable


def build_snapshot(codex_home: Path) -> dict[str, Any]:
    alignment = _alignment_module()
    paths = list(alignment.iter_rollout_paths(codex_home))
    parsed = [(path, alignment.read_session_meta(path)) for path in paths]
    metas = [meta for _, meta in parsed if meta is not None]
    alignment.validate_unique_rollouts(metas)
    roots = resolve_roots(metas)
    rows: list[dict[str, Any]] = []
    for path, meta in parsed:
        try:
            digest, size, stable = _file_digest(path)
        except OSError:
            digest, size, stable = None, None, False
        if meta is None:
            status, root = "unparsed", None
        else:
            status, root = roots[meta.session_id]
        if not stable:
            status, root = "unstable", None
        rows.append({
            "source_path": str(path.resolve()),
            "source_sha256": digest,
            "source_bytes": size,
            "rollout_id": meta.rollout_id if meta else None,
            "session_id": meta.session_id if meta else None,
            "session_started_at_utc": meta.timestamp if meta else None,
            "parent_thread_id": meta.parent_thread_id if meta else None,
            "root_session_id": root,
            "lineage_status": status,
        })
    status_counts = Counter(row["lineage_status"] for row in rows)
    roots_seen = {row["root_session_id"] for row in rows if row["root_session_id"]}
    material = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return {
        "schema_version": 2,
        "purpose": "prospective prior-or-unknown exposure baseline; not a retrospective freshness certificate",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "codex_home": str(codex_home.resolve()),
        "reader_sha256": hashlib.sha256(Path(__file__).with_name("align_decisions.py").read_bytes()).hexdigest(),
        "snapshot_tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "rollouts": rows,
        "summary": {
            "rollout_files": len(paths),
            "parsed_rollouts": len(metas),
            "resolved_roots": len(roots_seen),
            "lineage_status_counts": dict(sorted(status_counts.items())),
            "rollout_rows_sha256": hashlib.sha256(material.encode("utf-8")).hexdigest(),
        },
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--private-output", required=True, type=Path)
    parser.add_argument("--baseline", type=Path, help="private timestamped baseline to compare")
    args = parser.parse_args(argv)
    target = validate_output_path(args.private_output)
    snapshot = build_snapshot(args.codex_home.resolve())
    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        roots = prospective_roots(baseline, snapshot)
        snapshot["prospective_comparison"] = {
            "baseline_rows_sha256": baseline["summary"]["rollout_rows_sha256"],
            "new_root_ids": sorted(roots),
        }
        snapshot["summary"]["new_roots_since_baseline"] = len(roots)
    # Exclusive creation means an earlier audit can never be silently replaced.
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(snapshot, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    print(json.dumps(snapshot["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

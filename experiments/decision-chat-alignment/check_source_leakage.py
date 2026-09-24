"""Audit final-set leakage by *verified source lineage*, not ranked candidate.

Run only after the held-out labels are opened for final scoring. Source groups
are logical sessions collapsed through parent-agent links. A candidate-session
split is provisional until this check passes; a detected overlap must be
reported, not repaired by retuning on the held-out labels.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("align_decisions_leakage", BASE / "align_decisions.py")
assert SPEC and SPEC.loader
alignment = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = alignment
SPEC.loader.exec_module(alignment)


def root_group(rollout_id: str, metas: dict[str, Any]) -> str:
    meta = metas.get(rollout_id)
    if meta is None:
        raise ValueError(f"Cited rollout unavailable: {rollout_id}")
    parents: dict[str, set[str]] = {}
    for entry in metas.values():
        if entry.parent_thread_id:
            parents.setdefault(str(entry.session_id), set()).add(str(entry.parent_thread_id))
    session = str(meta.session_id)
    seen = set()
    while True:
        if session in seen:
            raise ValueError("Cycle in source-session parent lineage")
        seen.add(session)
        candidates = parents.get(session, set())
        if len(candidates) > 1:
            raise ValueError("Conflicting parent task IDs for one source session")
        if not candidates:
            return session
        session = next(iter(candidates))


def source_groups(row: dict[str, Any], metas: dict[str, Any]) -> set[str]:
    adjudication = row["adjudication"]
    if adjudication["label"] == "unresolved":
        return set()
    return {
        root_group(str(ref["rollout_id"]), metas)
        for ref in adjudication.get("evidence_refs", [])
    }


def overlap(
    development: list[dict[str, Any]], held_out: list[dict[str, Any]],
    metas: dict[str, Any], known: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    development_groups = set().union(*(source_groups(row, metas) for row in development))
    known_groups = set().union(*(source_groups(row, metas) for row in (known or [])))
    final_groups = set().union(*(source_groups(row, metas) for row in held_out))
    leaked = final_groups & (development_groups | known_groups)
    return {
        "development_source_groups": len(development_groups),
        "known_source_groups": len(known_groups),
        "held_out_source_groups": len(final_groups),
        "overlapping_source_groups": len(leaked),
        "source_group_disjoint": not leaked,
        "overlap_group_hashes": sorted(hashlib.sha256(value.encode("utf-8")).hexdigest()[:16] for value in leaked),
        "limitation": "Unresolved rows have no verified source; this audit cannot prove their actual source-group separation.",
    }


def read_gold(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--development-gold", type=Path, required=True)
    parser.add_argument("--held-out-gold", type=Path, required=True)
    parser.add_argument("--known-gold", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    known = read_gold(args.known_gold)
    development = read_gold(args.development_gold)
    held_out = read_gold(args.held_out_gold)
    metas = {}
    for path in alignment.iter_rollout_paths(args.codex_home):
        meta = alignment.read_session_meta(path)
        if meta:
            if meta.rollout_id in metas:
                raise ValueError(f"Duplicate rollout ID: {meta.rollout_id}")
            metas[meta.rollout_id] = meta
    result = overlap(development, held_out, metas, known)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))
    return 0 if result["source_group_disjoint"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

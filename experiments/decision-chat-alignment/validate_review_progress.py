"""Validate completed private review rows without requiring the full gold set.

This reads only cited Codex rollouts, checks exact raw message ordinals and
decision-minute causality, and prints counts without raw transcript text.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, BASE / filename)
    if not spec or not spec.loader:
        raise RuntimeError(f"Could not load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


assembly = load_module("assemble_extended_gold_progress", "assemble_extended_gold.py")
alignment = assembly.alignment


def validate(packet: dict[str, Any], codex_home: Path) -> dict[str, Any]:
    completed = [row for row in packet["reviews"] if row["review"].get("label") is not None]
    required = {
        str(ref["rollout_id"])
        for row in completed
        for ref in row["review"].get("evidence_refs", [])
    }
    found: dict[str, tuple[Path, Any]] = {}
    for path in alignment.iter_rollout_paths(codex_home):
        meta = alignment.read_session_meta(path)
        if meta and meta.rollout_id in required:
            if meta.rollout_id in found:
                raise ValueError(f"Duplicate cited rollout ID: {meta.rollout_id}")
            found[meta.rollout_id] = (path, meta)
    missing = required - set(found)
    if missing:
        raise ValueError(f"Cited rollout unavailable: {', '.join(sorted(missing))}")
    blocks = {rollout_id: alignment.parse_rollout(path, meta) for rollout_id, (path, meta) in found.items()}
    for row in completed:
        decision_id = row["decision_id"]
        review = row["review"]
        assembly._review_complete(review, decision_id, "review")
        cutoff = alignment.parse_iso_timestamp(row["timestamp"])
        if cutoff is None:
            raise ValueError(f"{decision_id}: invalid decision timestamp")
        assembly._validate_refs(review, decision_id, blocks, cutoff)
    return {
        "verifier": packet.get("verifier"),
        "completed": len(completed),
        "total": len(packet["reviews"]),
        "cited_rollouts_checked": len(found),
        "labels": dict(sorted(Counter(row["review"]["label"] for row in completed).items())),
        "review_modes": dict(sorted(Counter(row["review"].get("review_mode", "unspecified") for row in completed).items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path, required=True)
    args = parser.parse_args()
    result = validate(json.loads(args.packet.read_text(encoding="utf-8")), args.codex_home)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

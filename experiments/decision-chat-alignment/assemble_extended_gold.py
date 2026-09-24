"""Fail-closed assembly of independently reviewed decision/source gold rows.

The assembler validates evidence against normalized local Codex coordinates and
writes no raw conversation text. Run it separately for development and held-out
rows; do not open held-out reviews while tuning.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
ALLOWED_LABELS = {"verified_source", "partial_multi_turn", "child_result", "wrong_candidate", "unresolved"}


def _alignment_module():
    spec = importlib.util.spec_from_file_location("align_decisions", BASE / "align_decisions.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load alignment parser")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


alignment = _alignment_module()


def _index(rows: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    for row in rows:
        decision_id = row.get("decision_id")
        if not isinstance(decision_id, str) or not decision_id:
            raise ValueError(f"{label}: missing decision_id")
        if decision_id in output:
            raise ValueError(f"{label}: duplicate decision_id {decision_id}")
        output[decision_id] = row
    return output


def _review_complete(review: dict[str, Any], decision_id: str, label: str) -> None:
    kind = review.get("label")
    if kind not in ALLOWED_LABELS:
        raise ValueError(f"{decision_id}: {label} incomplete or invalid label")
    if kind != "unresolved" and not review.get("evidence_refs"):
        raise ValueError(f"{decision_id}: {label} incomplete evidence_refs")
    if not isinstance(review.get("rationale"), str) or not review["rationale"].strip():
        raise ValueError(f"{decision_id}: {label} incomplete rationale")


def _validate_refs(
    review: dict[str, Any], decision_id: str, blocks_by_rollout: dict[str, list[Any]], cutoff: Any,
) -> None:
    for ref in review.get("evidence_refs", []):
        rollout_id = ref.get("rollout_id")
        turn = ref.get("turn")
        ordinals = ref.get("ordinals")
        if not isinstance(rollout_id, str) or not isinstance(turn, int) or not isinstance(ordinals, list) or not ordinals:
            raise ValueError(f"{decision_id}: evidence ref lacks rollout, turn, or source ordinals")
        blocks = blocks_by_rollout.get(rollout_id, [])
        matching = [block for block in blocks if block.turn_number == turn]
        if len(matching) != 1:
            raise ValueError(f"{decision_id}: evidence turn is unavailable or ambiguous")
        items = [*matching[0].items, *matching[0].reasoning_summary_items]
        by_ordinal = {item.source_ordinal: item for item in items}
        expected_timestamps = ref.get("timestamps")
        expected_actors = ref.get("actors")
        if expected_timestamps is not None and len(expected_timestamps) != len(ordinals):
            raise ValueError(f"{decision_id}: timestamp/ordinal length mismatch")
        if expected_actors is not None and len(expected_actors) != len(ordinals):
            raise ValueError(f"{decision_id}: actor/ordinal length mismatch")
        for index, ordinal in enumerate(ordinals):
            item = by_ordinal.get(ordinal)
            if item is None:
                raise ValueError(f"{decision_id}: source ordinal {ordinal} absent from cited turn")
            stamp = alignment.parse_iso_timestamp(item.timestamp)
            if stamp is None or stamp >= cutoff + timedelta(minutes=1):
                raise ValueError(f"{decision_id}: evidence is not causally prior")
            if expected_timestamps is not None and expected_timestamps[index] != item.timestamp:
                raise ValueError(f"{decision_id}: evidence timestamp does not match raw item")
            if expected_actors is not None and expected_actors[index] != item.role:
                raise ValueError(f"{decision_id}: evidence actor does not match raw item")
    evidence_ordinals = {
        (ref["rollout_id"], ordinal)
        for ref in review.get("evidence_refs", [])
        for ordinal in ref["ordinals"]
    }
    for ref in review.get("minimal_useful_refs", []):
        rollout_id = ref.get("rollout_id")
        ordinals = ref.get("ordinals")
        if not isinstance(rollout_id, str) or not isinstance(ordinals, list) or not ordinals:
            raise ValueError(f"{decision_id}: minimal-useful ref lacks message ordinals")
        if any((rollout_id, ordinal) not in evidence_ordinals for ordinal in ordinals):
            raise ValueError(f"{decision_id}: minimal-useful source ordinal is not cited evidence")


def assemble(
    split: dict[str, Any], alignments: dict[str, Any], packet_a: dict[str, Any],
    packet_b: dict[str, Any], adjudications: dict[str, Any],
    blocks_by_rollout: dict[str, list[Any]], *, split_name: str,
) -> list[dict[str, Any]]:
    if split_name not in {"development", "sealed_final"}:
        raise ValueError("split_name must be development or sealed_final")
    ids = split[split_name]["decision_ids"]
    if len(ids) != len(set(ids)):
        raise ValueError("split has duplicate decision IDs")
    align_by_id = {
        row["decision"]["decision_id"]: row for row in alignments["alignments"]
    }
    reviews_a = _index(packet_a["reviews"], "verifier A")
    reviews_b = _index(packet_b["reviews"], "verifier B")
    finals = _index(adjudications["reviews"], "adjudication")
    expected = set(ids)
    if set(reviews_a) != expected or set(reviews_b) != expected:
        raise ValueError("verifier packet IDs differ from split")
    if not expected <= set(finals) or not expected <= set(align_by_id):
        raise ValueError("adjudication or alignment is missing split IDs")
    if packet_a.get("verifier") != "A" or packet_b.get("verifier") != "B":
        raise ValueError("verifier identities are missing or swapped")
    rows: list[dict[str, Any]] = []
    for decision_id in ids:
        a = reviews_a[decision_id]["review"]
        b = reviews_b[decision_id]["review"]
        final = finals[decision_id]["final_adjudication"]
        for label, review in (("verifier A", a), ("verifier B", b), ("final", final)):
            _review_complete(review, decision_id, label)
        source = align_by_id[decision_id]
        decision = source["decision"]
        cutoff = alignment.parse_iso_timestamp(decision["decision_timestamp"])
        if cutoff is None:
            raise ValueError(f"{decision_id}: bad decision timestamp")
        for review in (a, b, final):
            _validate_refs(review, decision_id, blocks_by_rollout, cutoff)
        candidate = source.get("best_candidate") or {}
        window = candidate.get("window") or {}
        evidence_coords = {(ref["rollout_id"], ref["turn"]) for ref in final["evidence_refs"]}
        inside = {
            (rollout_id, turn) for rollout_id, turn in evidence_coords
            if rollout_id == candidate.get("rollout_id")
            and isinstance(window.get("turn_start"), int)
            and window["turn_start"] <= turn <= window["turn_end"]
        }
        rows.append({
            "schema_version": "decision-source-gold/2.0",
            "cohort": {
                "sample_ids_sha256": alignments["metadata"]["sample_ids_sha256"],
                "sample_seed": alignments["metadata"]["sample_seed"],
                "split": split_name,
                "source_alignment": "cohort-100/alignments/alignments.json",
            },
            "decision": {
                "id": decision_id, "title": decision["title"],
                "timestamp": decision["decision_timestamp"],
                "record_path": decision["source_path"],
                "record_start_line": decision["start_line"],
                "record_end_line": decision["end_line"],
            },
            "selected_candidate": {
                "rollout_id": candidate.get("rollout_id"),
                "logical_session_id": candidate.get("session_id"),
                "turn": candidate.get("winning_turn"),
                "turn_id": candidate.get("winning_turn_id"),
                "turn_start_timestamp": candidate.get("turn_start_timestamp"),
                "turn_end_timestamp": candidate.get("turn_end_timestamp"),
                "source_path": candidate.get("source_path"),
                "matcher_confidence": source.get("confidence"),
                "matcher_appears_unique": source.get("appears_unique"),
                "window_turn_start": window.get("turn_start"),
                "window_turn_end": window.get("turn_end"),
                "window_contains_any_cited_evidence": bool(inside),
                "window_contains_all_cited_evidence": bool(evidence_coords) and evidence_coords <= inside,
            },
            "verifier_a_review": a,
            "verifier_b_review": b,
            "adjudication": final,
        })
    return rows


def _read(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--split-name", choices=("development", "sealed_final"), required=True)
    parser.add_argument("--alignments", type=Path, required=True)
    parser.add_argument("--verifier-a", type=Path, required=True)
    parser.add_argument("--verifier-b", type=Path, required=True)
    parser.add_argument("--adjudication", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    split = _read(args.split)
    packet_a, packet_b, adjudications = (_read(path) for path in (args.verifier_a, args.verifier_b, args.adjudication))
    refs = [
        ref for row in [*packet_a["reviews"], *packet_b["reviews"]]
        for ref in row["review"].get("evidence_refs", [])
    ]
    refs.extend(ref for row in adjudications["reviews"] for ref in row["final_adjudication"].get("evidence_refs", []))
    wanted = {ref["rollout_id"] for ref in refs}
    blocks_by_rollout: dict[str, list[Any]] = {}
    for path in alignment.iter_rollout_paths(args.codex_home):
        meta = alignment.read_session_meta(path)
        if meta and meta.rollout_id in wanted:
            blocks_by_rollout[meta.rollout_id] = alignment.parse_rollout(path, meta)
    if wanted - set(blocks_by_rollout):
        raise ValueError("Cited rollout missing from local Codex history")
    rows = assemble(
        split, _read(args.alignments), packet_a, packet_b, adjudications,
        blocks_by_rollout, split_name=args.split_name,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    print(json.dumps({"rows": len(rows), "split": args.split_name}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

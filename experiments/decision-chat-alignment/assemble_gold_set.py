from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "decision-source-gold/1.0"
ALLOWED_LABELS = {
    "verified_source",
    "partial_multi_turn",
    "child_result",
    "wrong_candidate",
    "unresolved",
}


def read_jsonl_parts(parts_dir: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for path in sorted(parts_dir.glob("part-*.jsonl")):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
            decision_id = row.get("decision_id")
            if not isinstance(decision_id, str) or not decision_id:
                raise RuntimeError(f"{path}:{line_number}: missing decision_id")
            if decision_id in rows:
                raise RuntimeError(f"duplicate gold decision_id: {decision_id}")
            if row.get("schema_version") != SCHEMA_VERSION:
                raise RuntimeError(f"{decision_id}: unexpected schema_version")
            rows[decision_id] = row
    return rows


def validated_gold_rows(
    alignment_payload: dict[str, Any], audit_rows: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    metadata = alignment_payload["metadata"]
    alignments = {
        row["decision"]["decision_id"]: row for row in alignment_payload["alignments"]
    }
    expected_ids = metadata["sample_ids"]
    if set(audit_rows) != set(expected_ids):
        missing = sorted(set(expected_ids) - set(audit_rows))
        extra = sorted(set(audit_rows) - set(expected_ids))
        raise RuntimeError(f"gold cohort mismatch; missing={missing}, extra={extra}")

    output = []
    for decision_id in expected_ids:
        alignment = alignments[decision_id]
        audit = audit_rows[decision_id]
        candidate = alignment.get("best_candidate")
        selected = audit.get("selected_candidate") or {}
        if not candidate:
            raise RuntimeError(f"{decision_id}: frozen alignment has no best candidate")
        expected_identity = (candidate["rollout_id"], candidate["winning_turn"])
        audited_identity = (selected.get("rollout_id"), selected.get("turn"))
        if audited_identity != expected_identity:
            raise RuntimeError(
                f"{decision_id}: audited candidate {audited_identity} != frozen {expected_identity}"
            )
        adjudication = audit.get("adjudication") or {}
        label = adjudication.get("label")
        if label not in ALLOWED_LABELS:
            raise RuntimeError(f"{decision_id}: invalid label {label!r}")
        evidence_refs = adjudication.get("evidence_refs")
        if label != "unresolved" and not evidence_refs:
            raise RuntimeError(f"{decision_id}: {label} requires evidence_refs")
        decision = alignment["decision"]
        window = candidate["window"]
        evidence_locations = [
            (ref.get("rollout_id"), ref.get("turn"))
            for ref in evidence_refs or []
            if isinstance(ref, dict)
        ]
        evidence_inside_window = [
            rollout_id == candidate["rollout_id"]
            and isinstance(turn_number, int)
            and window["turn_start"] <= turn_number <= window["turn_end"]
            for rollout_id, turn_number in evidence_locations
        ]
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "cohort": {
                    "sample_ids_sha256": metadata["sample_ids_sha256"],
                    "sample_seed": metadata["sample_seed"],
                    "decision_agent_filter": metadata["decision_agent_filter"],
                    "source_alignment": "results-codex-causal-minute-fixed/alignments.json",
                },
                "decision": {
                    "id": decision_id,
                    "title": decision["title"],
                    "timestamp": decision["decision_timestamp"],
                    "record_path": decision["source_path"],
                    "record_start_line": decision["start_line"],
                    "record_end_line": decision["end_line"],
                },
                "selected_candidate": {
                    "rollout_id": candidate["rollout_id"],
                    "logical_session_id": candidate["session_id"],
                    "turn": candidate["winning_turn"],
                    "turn_id": candidate["winning_turn_id"],
                    "turn_start_timestamp": candidate["turn_start_timestamp"],
                    "turn_end_timestamp": candidate["turn_end_timestamp"],
                    "source_path": candidate["source_path"],
                    "matcher_confidence": alignment["confidence"],
                    "matcher_appears_unique": alignment["appears_unique"],
                    "window_turn_start": window["turn_start"],
                    "window_turn_end": window["turn_end"],
                    "window_contains_any_cited_evidence": any(evidence_inside_window),
                    "window_contains_all_cited_evidence": bool(evidence_inside_window)
                    and all(evidence_inside_window),
                },
                "adjudication": adjudication,
            }
        )
    return output


def write_outputs(rows: list[dict[str, Any]], jsonl_path: Path, csv_path: Path) -> None:
    jsonl_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
        newline="\n",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "decision_id",
                "decision_title",
                "decision_timestamp",
                "selected_rollout_id",
                "selected_turn",
                "matcher_confidence",
                "gold_label",
                "evidence_shape",
                "source_role",
                "coverage",
                "selected_candidate_describes_decision",
                "window_contains_any_cited_evidence",
                "window_contains_all_cited_evidence",
                "evidence_ref_count",
                "parent_hops",
                "rationale",
            ],
        )
        writer.writeheader()
        for row in rows:
            decision = row["decision"]
            selected = row["selected_candidate"]
            adjudication = row["adjudication"]
            writer.writerow(
                {
                    "decision_id": decision["id"],
                    "decision_title": decision["title"],
                    "decision_timestamp": decision["timestamp"],
                    "selected_rollout_id": selected["rollout_id"],
                    "selected_turn": selected["turn"],
                    "matcher_confidence": selected["matcher_confidence"],
                    "gold_label": adjudication["label"],
                    "evidence_shape": adjudication["evidence_shape"],
                    "source_role": adjudication["source_role"],
                    "coverage": adjudication["coverage"],
                    "selected_candidate_describes_decision": adjudication[
                        "selected_candidate_describes_decision"
                    ],
                    "window_contains_any_cited_evidence": selected[
                        "window_contains_any_cited_evidence"
                    ],
                    "window_contains_all_cited_evidence": selected[
                        "window_contains_all_cited_evidence"
                    ],
                    "evidence_ref_count": len(adjudication.get("evidence_refs", [])),
                    "parent_hops": len(adjudication.get("parent_chain_traversed", [])),
                    "rationale": adjudication["rationale"],
                }
            )


def main() -> int:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--alignments",
        type=Path,
        default=base / "results-codex-causal-minute-fixed" / "alignments.json",
    )
    parser.add_argument("--parts", type=Path, default=base / "gold-parts")
    parser.add_argument("--output-jsonl", type=Path, default=base / "GOLD-SET.jsonl")
    parser.add_argument("--output-csv", type=Path, default=base / "GOLD-SET.csv")
    args = parser.parse_args()

    alignment_payload = json.loads(args.alignments.read_text(encoding="utf-8"))
    audit_rows = read_jsonl_parts(args.parts)
    rows = validated_gold_rows(alignment_payload, audit_rows)
    write_outputs(rows, args.output_jsonl, args.output_csv)
    counts = Counter(row["adjudication"]["label"] for row in rows)
    print(json.dumps({"rows": len(rows), "labels": counts}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

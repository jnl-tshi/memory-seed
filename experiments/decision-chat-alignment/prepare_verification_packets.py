from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


SPLIT_SCHEMA = "decision-verification-split/1.0"
PACKET_SCHEMA = "decision-verification-packet/1.0"
ADJUDICATION_SCHEMA = "decision-verification-adjudication/1.0"
DEVELOPMENT_SIZE = 33
FINAL_SIZE = 20


def sha256_ids(values: list[str]) -> str:
    return hashlib.sha256("\n".join(sorted(values)).encode("utf-8")).hexdigest()


def group_assignment_sha256(rows: list[dict[str, Any]]) -> str:
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        groups[row["logical_session_id"]].append(row["decision_id"])
    canonical = [
        {"session": session_id, "decision_ids": sorted(decision_ids)}
        for session_id, decision_ids in sorted(groups.items())
    ]
    payload = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def read_gold_sessions(path: Path) -> set[str]:
    sessions: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        candidate = row.get("selected_candidate") or {}
        session_id = candidate.get("logical_session_id")
        if isinstance(session_id, str) and session_id:
            sessions.add(session_id)
    return sessions


def _candidate_rows(manifest: dict[str, Any], alignments: dict[str, Any]) -> list[dict[str, Any]]:
    metadata = manifest.get("metadata") or {}
    sample_ids = metadata.get("sample_ids")
    if not isinstance(sample_ids, list) or not all(isinstance(value, str) for value in sample_ids):
        raise ValueError("manifest.metadata.sample_ids must be a list of strings")
    if len(sample_ids) != len(set(sample_ids)):
        raise ValueError("manifest contains duplicate sample IDs")

    alignment_rows = alignments.get("alignments")
    if not isinstance(alignment_rows, list):
        raise ValueError("alignment payload must contain an alignments list")
    by_id: dict[str, dict[str, Any]] = {}
    for row in alignment_rows:
        decision = row.get("decision") or {}
        decision_id = decision.get("decision_id")
        if not isinstance(decision_id, str) or not decision_id or decision_id in by_id:
            raise ValueError("alignments must have unique decision.decision_id values")
        by_id[decision_id] = row
    if set(by_id) != set(sample_ids):
        raise ValueError("manifest sample IDs and alignment decision IDs differ")

    output = []
    for decision_id in sample_ids:
        row = by_id[decision_id]
        decision = row.get("decision") or {}
        candidate = row.get("best_candidate") or {}
        session_id = candidate.get("session_id")
        rollout_id = candidate.get("rollout_id")
        if not isinstance(session_id, str) or not session_id:
            raise ValueError(f"{decision_id}: best_candidate.session_id is required for leakage control")
        if not isinstance(rollout_id, str) or not rollout_id:
            raise ValueError(f"{decision_id}: best_candidate.rollout_id is required")
        output.append(
            {
                "decision_id": decision_id,
                "title": str(decision.get("title") or ""),
                "timestamp": str(decision.get("decision_timestamp") or ""),
                "record_path": str(decision.get("source_path") or ""),
                "record_start_line": decision.get("start_line"),
                "record_end_line": decision.get("end_line"),
                "logical_session_id": session_id,
                "rollout_id": rollout_id,
                "winning_turn": candidate.get("winning_turn"),
                "source_path": candidate.get("source_path"),
                "window_turn_start": (candidate.get("window") or {}).get("turn_start"),
                "window_turn_end": (candidate.get("window") or {}).get("turn_end"),
            }
        )
    return output


def choose_final_sessions(
    grouped: dict[str, list[dict[str, Any]]], known_sessions: set[str], final_size: int = FINAL_SIZE
) -> set[str]:
    """Choose whole groups summing to final_size, preferring sessions unseen in prior gold."""
    # DP stores the best group tuple for each attainable row count. Higher unseen-row
    # coverage wins; a stable digest breaks ties independently of input ordering.
    states: dict[int, tuple[int, tuple[str, ...]]] = {0: (0, ())}
    for session_id in sorted(grouped):
        rows = grouped[session_id]
        weight = len(rows)
        unseen_weight = weight if session_id not in known_sessions else 0
        for total, (unseen, chosen) in sorted(list(states.items()), reverse=True):
            next_total = total + weight
            if next_total > final_size:
                continue
            candidate = (unseen + unseen_weight, chosen + (session_id,))
            existing = states.get(next_total)
            if existing is None or candidate[0] > existing[0]:
                states[next_total] = candidate
            elif candidate[0] == existing[0]:
                current_key = tuple(hashlib.sha256(s.encode("utf-8")).hexdigest() for s in existing[1])
                candidate_key = tuple(hashlib.sha256(s.encode("utf-8")).hexdigest() for s in candidate[1])
                if candidate_key < current_key:
                    states[next_total] = candidate
    if final_size not in states:
        attainable = {0}
        for session_id in sorted(grouped):
            weight = len(grouped[session_id])
            attainable |= {value + weight for value in attainable}
        raise ValueError(
            f"cannot form an exact {final_size}-decision final set from whole sessions; "
            f"nearest attainable counts are {max((n for n in attainable if n < final_size), default=0)} "
            f"and {min((n for n in attainable if n > final_size), default=0)}"
        )
    return set(states[final_size][1])


def build_split(
    manifest: dict[str, Any],
    alignments: dict[str, Any],
    known_sessions: set[str],
    development_size: int = DEVELOPMENT_SIZE,
    final_size: int = FINAL_SIZE,
) -> dict[str, Any]:
    rows = _candidate_rows(manifest, alignments)
    if len(rows) != development_size + final_size:
        raise ValueError(
            f"expected {development_size + final_size} cohort rows, found {len(rows)}"
        )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["logical_session_id"]].append(row)
    final_sessions = choose_final_sessions(grouped, known_sessions, final_size)
    final_rows = sorted(
        (row for row in rows if row["logical_session_id"] in final_sessions),
        key=lambda row: row["decision_id"],
    )
    development_rows = sorted(
        (row for row in rows if row["logical_session_id"] not in final_sessions),
        key=lambda row: row["decision_id"],
    )
    if len(final_rows) != final_size or len(development_rows) != development_size:
        raise ValueError("whole-session split did not produce requested partition sizes")
    return {
        "rows": rows,
        "development": development_rows,
        "final": final_rows,
        "known_sessions": known_sessions,
    }


def public_manifest(split: dict[str, Any], cohort_metadata: dict[str, Any]) -> dict[str, Any]:
    development = split["development"]
    final = split["final"]
    return {
        "schema_version": SPLIT_SCHEMA,
        "cohort": {
            "schema_version": cohort_metadata.get("schema_version"),
            "repository_revision": cohort_metadata.get("repository_revision"),
            "sample_seed": cohort_metadata.get("sample_seed"),
            "sample_ids_sha256": cohort_metadata.get("sample_ids_sha256"),
        },
        "split_method": "exact subset sum over best_candidate.session_id groups; final prefers sessions absent from known gold",
        "development": {
            "size": len(development),
            "decision_ids": [row["decision_id"] for row in development],
            "decision_ids_sha256": sha256_ids([row["decision_id"] for row in development]),
            "logical_session_ids": sorted({row["logical_session_id"] for row in development}),
            "coordinates": development,
        },
        "sealed_final": {
            "size": len(final),
            "decision_ids": [row["decision_id"] for row in final],
            "decision_ids_sha256": sha256_ids([row["decision_id"] for row in final]),
            "group_count": len({row["logical_session_id"] for row in final}),
            "group_assignment_sha256": group_assignment_sha256(final),
        },
    }


def private_split_artifact(split: dict[str, Any], cohort_hash: str) -> dict[str, Any]:
    final = split["final"]
    return {
        "schema_version": "decision-verification-private-split/1.0",
        "cohort_ids_sha256": cohort_hash,
        "sealed_final": {
            "size": len(final),
            "decision_ids_sha256": sha256_ids([row["decision_id"] for row in final]),
            "group_assignment_sha256": group_assignment_sha256(final),
            "logical_session_ids": sorted({row["logical_session_id"] for row in final}),
            "coordinates": final,
        },
    }


def verifier_packet(rows: list[dict[str, Any]], verifier: str, cohort_hash: str) -> dict[str, Any]:
    return {
        "schema_version": PACKET_SCHEMA,
        "verifier": verifier,
        "cohort_ids_sha256": cohort_hash,
        "instructions": (
            "Independently verify the source of each decision using causally prior evidence. "
            "Do not infer from the decision record alone. Preserve evidence coordinates and a concise rationale."
        ),
        "reviews": [
            {
                "decision_id": row["decision_id"],
                "title": row["title"],
                "timestamp": row["timestamp"],
                "record_path": row["record_path"],
                "record_start_line": row["record_start_line"],
                "record_end_line": row["record_end_line"],
                "review": {
                    "label": None,
                    "evidence_refs": [],
                    "minimal_useful_refs": [],
                    "evidence_shape": None,
                    "source_role": None,
                    "coverage": None,
                    "selected_candidate_describes_decision": None,
                    "rationale": None,
                },
            }
            for row in rows
        ],
    }


def adjudication_template(split: dict[str, Any]) -> dict[str, Any]:
    rows = split["development"] + split["final"]
    return {
        "schema_version": ADJUDICATION_SCHEMA,
        "label_vocabulary": [
            "verified_source", "partial_multi_turn", "child_result", "wrong_candidate", "unresolved"
        ],
        "reviews": [
            {
                "decision_id": row["decision_id"],
                "verifier_a_review": {
                    "label": None,
                    "evidence_refs": [],
                    "minimal_useful_refs": [],
                    "evidence_shape": None,
                    "source_role": None,
                    "coverage": None,
                    "selected_candidate_describes_decision": None,
                    "rationale": None,
                },
                "verifier_b_review": {
                    "label": None,
                    "evidence_refs": [],
                    "minimal_useful_refs": [],
                    "evidence_shape": None,
                    "source_role": None,
                    "coverage": None,
                    "selected_candidate_describes_decision": None,
                    "rationale": None,
                },
                "final_adjudication": {
                    "label": None,
                    "evidence_refs": [],
                    "minimal_useful_refs": [],
                    "evidence_shape": None,
                    "source_role": None,
                    "coverage": None,
                    "selected_candidate_describes_decision": None,
                    "rationale": None,
                    "disagreement_resolution": None,
                },
            }
            for row in sorted(rows, key=lambda item: item["decision_id"])
        ],
        "review_shape": {
            "label": None,
            "evidence_refs": [],
            "minimal_useful_refs": [],
            "evidence_shape": None,
            "source_role": None,
            "coverage": None,
            "selected_candidate_describes_decision": None,
            "rationale": None,
        },
        "final_adjudication_shape": {
            "label": None,
            "evidence_refs": [],
            "minimal_useful_refs": [],
            "evidence_shape": None,
            "source_role": None,
            "coverage": None,
            "selected_candidate_describes_decision": None,
            "rationale": None,
            "disagreement_resolution": None,
        },
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare(
    manifest_path: Path,
    alignments_path: Path,
    gold_path: Path,
    public_path: Path,
    private_dir: Path,
) -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    private_dir = private_dir.resolve()
    if private_dir == repo_root or repo_root in private_dir.parents:
        raise ValueError("private packet directory must be outside the tracked repository")
    manifest = read_json(manifest_path)
    alignments = read_json(alignments_path)
    split = build_split(manifest, alignments, read_gold_sessions(gold_path))
    cohort_hash = str((manifest.get("metadata") or {}).get("sample_ids_sha256") or "")
    if not cohort_hash:
        raise ValueError("cohort manifest is missing metadata.sample_ids_sha256")
    public = public_manifest(split, manifest.get("metadata") or {})
    write_json(public_path, public)
    write_json(
        private_dir / "sealed-final-coordinates.json",
        private_split_artifact(split, cohort_hash),
    )
    write_json(
        private_dir / "verifier-a-development.json",
        verifier_packet(split["development"], "A", cohort_hash),
    )
    write_json(
        private_dir / "verifier-b-development.json",
        verifier_packet(split["development"], "B", cohort_hash),
    )
    write_json(
        private_dir / "verifier-a-sealed-final.json",
        verifier_packet(split["final"], "A", cohort_hash),
    )
    write_json(
        private_dir / "verifier-b-sealed-final.json",
        verifier_packet(split["final"], "B", cohort_hash),
    )
    write_json(private_dir / "adjudication-template.json", adjudication_template(split))
    return public


def main() -> int:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=base / "cohort-100" / "manifest.json")
    parser.add_argument(
        "--alignments", type=Path, default=base / "cohort-100" / "alignments" / "alignments.json"
    )
    parser.add_argument("--known-gold", type=Path, default=base / "GOLD-SET.jsonl")
    parser.add_argument("--public-output", type=Path, default=base / "cohort-100" / "verification-split.json")
    parser.add_argument(
        "--private-output-dir",
        type=Path,
        required=True,
        help="directory for the two verifier packets and adjudication template",
    )
    args = parser.parse_args()
    public = prepare(
        args.manifest.resolve(),
        args.alignments.resolve(),
        args.known_gold.resolve(),
        args.public_output.resolve(),
        args.private_output_dir.resolve(),
    )
    print(
        json.dumps(
            {
                "development_size": public["development"]["size"],
                "final_size": public["sealed_final"]["size"],
                "public_output": str(args.public_output.resolve()),
                "private_output_dir": str(args.private_output_dir.resolve()),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .parser import DecisionParser


CORPUS_SCHEMA = "p0.2-corpus-manifest-v1"
SOURCE_PATHS = (
    "experiments/decision-chat-alignment/GOLD-SET.jsonl",
    "experiments/decision-chat-alignment/cohort-100/development-gold.jsonl",
    "experiments/decision-chat-alignment/cohort-100/heldout-gold.jsonl",
)
DOCUMENTATION_CONTROLS = frozenset(
    {
        "mse_30022b9j3aprw5ye:d1",
        "mse_30v60e8c3xa380yd:d1",
        "mse_caj7ys6j6zbxp5rk:d1",
    }
)
SOURCE_OVERLAP = frozenset(
    {
        "mse_3hx7ym0qajvxm1w4:d2",
        "mse_ak94rd4r1zna4bc7:d2",
        "mse_jem7xd5yd771rkwq:d2",
        "mse_jem7xd5yd771rkwq:d3",
    }
)
LIVE_TASK_CONTAMINATED = frozenset({"mse_38b7jfjbwy8dfdtt:d1"})


def _canonical(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _flatten_refs(row: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for ref in row.get("adjudication", {}).get("evidence_refs", []):
        rollout = ref.get("rollout_id")
        turn = ref.get("turn")
        if "source_ordinal" in ref:
            result.append(
                {
                    "rollout_id": rollout,
                    "turn": turn,
                    "source_ordinal": ref.get("source_ordinal"),
                    "actor": ref.get("actor"),
                    "timestamp": ref.get("timestamp"),
                }
            )
            continue
        ordinals = ref.get("ordinals", [])
        actors = ref.get("actors", [])
        timestamps = ref.get("timestamps", [])
        for index, ordinal in enumerate(ordinals):
            result.append(
                {
                    "rollout_id": rollout,
                    "turn": turn,
                    "source_ordinal": ordinal,
                    "actor": actors[index] if index < len(actors) else None,
                    "timestamp": timestamps[index] if index < len(timestamps) else None,
                }
            )
    return sorted(result, key=lambda value: (str(value["rollout_id"]), value["source_ordinal"] or -1))


def _partition(decision_id: str, source_index: int) -> tuple[str, list[str]]:
    flags: list[str] = []
    if decision_id in DOCUMENTATION_CONTROLS:
        return "audit_only", ["documentation_control"]
    if decision_id in SOURCE_OVERLAP:
        return "audit_only", ["source_lineage_overlap"]
    if decision_id in LIVE_TASK_CONTAMINATED:
        return "audit_only", ["live_task_contaminated"]
    if source_index in {0, 1}:
        return "development", flags
    return "heldout_descriptive", flags


def _normalized_row(row: dict[str, Any], artifact: str, artifact_sha: str, source_index: int) -> dict[str, Any]:
    decision = row["decision"]
    decision_id = decision["id"]
    partition, flags = _partition(decision_id, source_index)
    refs = _flatten_refs(row)
    lineage_material = "|".join(sorted({str(ref["rollout_id"]) for ref in refs if ref["rollout_id"]})) or decision_id.split(":", 1)[0]
    return {
        "case_id": decision_id,
        "entry_id": decision_id.split(":", 1)[0],
        "record_kind": "Documentation" if decision_id in DOCUMENTATION_CONTROLS else "Decision",
        "source_artifact": artifact,
        "source_artifact_sha256": artifact_sha,
        "cohort": "historical" if source_index == 0 else "extension",
        "split": partition,
        "root_source_group_hash": _sha(("p0.2-source-group|" + lineage_material).encode("utf-8"))[:16],
        "gold_version": "frozen",
        "record": {
            "path": decision.get("record_path"),
            "start_line": decision.get("record_start_line"),
            "end_line": decision.get("record_end_line"),
            "timestamp": decision.get("timestamp"),
            "title": decision.get("title"),
        },
        "adjudication_label": row.get("adjudication", {}).get("label"),
        "coverage": row.get("adjudication", {}).get("coverage"),
        "evidence_coordinates": refs,
        "selected_candidate": row.get("selected_candidate"),
        "contamination_flags": flags,
        "acceptance_state": "unlabelled",
        "permitted_metrics": ["source_window_recall", "winning_turn_precision"] if partition != "audit_only" else ["audit"],
    }


def build_manifest(repo_root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    for source_index, relative in enumerate(SOURCE_PATHS):
        path = repo_root / relative
        raw = path.read_bytes()
        artifact_sha = _sha(raw)
        source_rows = _read_jsonl(path)
        artifacts.append({"path": relative, "sha256": artifact_sha, "rows": len(source_rows)})
        rows.extend(_normalized_row(row, relative, artifact_sha, source_index) for row in source_rows)
    rows.sort(key=lambda value: value["case_id"])
    if len({row["case_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate decision identity in canonical inputs")
    corpus_bytes = b"".join(_canonical(row) for row in rows)
    counts = {
        "formal_records": len(rows),
        "typed_decisions": sum(row["record_kind"] == "Decision" for row in rows),
        "documentation_controls": sum(row["record_kind"] == "Documentation" for row in rows),
        "development": sum(row["split"] == "development" for row in rows),
        "heldout_descriptive": sum(row["split"] == "heldout_descriptive" for row in rows),
        "audit_only_formal": sum(row["split"] == "audit_only" for row in rows),
        "postaudit_amendments": 5,
        "audit_only": sum(row["split"] == "audit_only" for row in rows) + 5,
    }
    core = {
        "schema_version": CORPUS_SCHEMA,
        "counts": counts,
        "source_artifacts": artifacts,
        "corpus_sha256": _sha(corpus_bytes),
        "rows": rows,
        "limitations": [
            "retrospective decision-known corpus",
            "accepted/proposed is not gold-labelled",
            "15 clean descriptive held-out rows; 14 verified recall denominators",
            "post-audit amendments are audit-only",
        ],
    }
    digest_payload = {key: value for key, value in core.items() if key != "rows"}
    return {**core, "manifest_sha256": _sha(_canonical(digest_payload))}


def write_manifest(repo_root: Path, output_dir: Path) -> dict[str, Any]:
    manifest = build_manifest(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "corpus.jsonl").write_bytes(b"".join(_canonical(row) for row in manifest["rows"]))
    header = {key: value for key, value in manifest.items() if key != "rows"}
    (output_dir / "manifest.json").write_bytes(_canonical(header))
    return header


def evaluate_negative_controls(path: Path) -> dict[str, Any]:
    parser = DecisionParser()
    cases = _read_jsonl(path)
    predictions: list[dict[str, Any]] = []
    for case in cases:
        candidates = parser.parse(case["case_id"], case["messages"])
        predicted = "accepted" if any(candidate["state"] == "accepted" for candidate in candidates) else (
            "proposed" if any(candidate["state"] == "proposed" for candidate in candidates) else "not_accepted"
        )
        predictions.append({"case_id": case["case_id"], "expected": case["expected"], "predicted": predicted})
    accepted_predictions = [item for item in predictions if item["predicted"] == "accepted"]
    correct_accepted = [item for item in accepted_predictions if item["expected"] == "accepted"]
    false_accepts = [item["case_id"] for item in accepted_predictions if item["expected"] != "accepted"]
    return {
        "cases": len(cases),
        "parser_backend": parser.backend,
        "accepted_precision": len(correct_accepted) / len(accepted_predictions) if accepted_predictions else 0.0,
        "false_accepts": false_accepts,
        "predictions": predictions,
    }

"""Historical source-coverage diagnostic for adaptive decision reconstruction.

This uses known gold coordinates only for scoring the disclosure window. No
model receives gold data, no semantic decision is inferred, and no case here
qualifies for the prospective accuracy gate. Per-case metadata stays private.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from hosted.capture.evaluation import _load_alignment_parser, _rollout_paths
from hosted.capture.evidence_ledger import EvidenceLedger
from hosted.evaluation.adaptive_arms import prepare_arms
from hosted.evaluation.adaptive_replay import AdaptiveReplay


CONFIG = {
    "model_name": "source-audit-no-model",
    "reasoning_effort": "none",
    "prompt_protocol_version": "v1",
    "arm_policy": "paired-source-v1",
}


def coordinate(value: dict) -> tuple[str, int, int]:
    return (str(value["rollout_id"]).lower(), int(value["turn"]),
            int(value["source_ordinal"]))


def verify_source_hash(frozen_hashes: dict, rollout: str, current_hash: str) -> None:
    if frozen_hashes.get(rollout) != current_hash:
        raise ValueError("source differs from frozen replay or has no frozen replay hash")


def audit_case(messages: list[dict], anchor: tuple[str, int, int],
               gold_refs: list[dict], case_id: str) -> dict:
    """Measure oracle-earliest source coverage, never semantic correctness."""
    if not gold_refs:
        raise ValueError("case needs adjudicated source references")
    gold = {coordinate(ref) for ref in gold_refs}
    available = {coordinate(message) for message in messages}
    arms = prepare_arms(messages, anchor, case_id, CONFIG)
    replay = AdaptiveReplay(messages, anchor, case_id, arms["configuration_hash"])
    seen: set[tuple[str, int, int]] = set()
    first_expansions: int | None = None
    first_characters: int | None = None
    initial_covered = False
    initial_characters = 0
    while (request := replay.request()) is not None:
        seen.update(coordinate(message) for message in request["messages"])
        if request["batch_index"] == 0:
            initial_covered = gold <= seen
            initial_characters = sum(len(message["text"]) for message in request["messages"])
        if first_expansions is None and gold <= seen:
            first_expansions = replay.disclosure.expansion_calls
            first_characters = sum(len(message["text"]) for batch in replay.disclosure.batches
                                   for message in batch["messages"])
        replay.import_response({
            "request_id": request["request_id"], "candidate_id": case_id,
            "answers": {slot: None for slot in EvidenceLedger.SLOTS},
            "reference_links": [],
        })
    def arm_coverage(name: str) -> bool:
        request = arms["arms"][name]["request"]
        return request is not None and gold <= {coordinate(m) for m in request["messages"]}

    return {
        "case_id": case_id,
        "source_ref_count": len(gold),
        "source_refs_present": len(gold & available),
        "unavailable_gold_refs": len(gold - available),
        "initial_gold_covered": initial_covered,
        "initial_source_characters": initial_characters,
        "oracle_gold_covered": gold <= seen,
        "oracle_expansions_to_cover": first_expansions,
        "oracle_source_characters_to_cover": first_characters,
        "adaptive_requests_to_exhaustion": replay.summary()["request_count"],
        "adaptive_source_characters_to_exhaustion": replay.summary()["disclosed_source_characters"],
        "stop_reason": replay.summary()["stop_reason"],
        "fixed_gold_covered": arm_coverage("fixed_window"),
        "fixed_unavailable": arms["arms"]["fixed_window"]["summary"]["unavailability_reason"],
        "fixed_span_status": arms["arms"]["fixed_window"]["summary"]["source_span_status"],
        "full_gold_covered": arm_coverage("full_window"),
        "full_unavailable": arms["arms"]["full_window"]["summary"]["unavailability_reason"],
        "semantic_decision_accuracy": None,
    }


def _source_inventory(blocks: list[Any], rollout: str, *, include_tools: bool) -> list[dict]:
    roles = {"user", "assistant", "tool"} if include_tools else {"user", "assistant"}
    return [{"rollout_id": rollout, "turn": block.turn_number,
             "source_ordinal": item.source_ordinal,
             "actor": "agent" if item.role == "assistant" else item.role,
             "text": item.text}
            for block in blocks for item in block.items
            if item.role in roles and isinstance(item.source_ordinal, int)]


def _summary(rows: list[dict]) -> dict:
    covered = [row for row in rows if row["oracle_gold_covered"]]
    return {
        "cases": len(rows),
        "gold_refs": sum(row["source_ref_count"] for row in rows),
        "gold_refs_absent_from_projection": sum(row["unavailable_gold_refs"] for row in rows),
        "initial_all_gold_covered_cases": sum(row["initial_gold_covered"] for row in rows),
        "oracle_all_gold_covered_cases": len(covered),
        "oracle_expansion_histogram": dict(sorted(Counter(
            str(row["oracle_expansions_to_cover"]) for row in covered).items())),
        "median_source_characters_to_oracle_cover": (
            statistics.median(row["oracle_source_characters_to_cover"] for row in covered)
            if covered else None),
        "fixed_all_gold_covered_cases": sum(row["fixed_gold_covered"] for row in rows),
        "full_all_gold_covered_cases": sum(row["full_gold_covered"] for row in rows),
        "fixed_unavailable_reasons": dict(sorted(Counter(
            row["fixed_unavailable"] for row in rows if row["fixed_unavailable"]).items())),
        "full_unavailable_reasons": dict(sorted(Counter(
            row["full_unavailable"] for row in rows if row["full_unavailable"]).items())),
        "adaptive_stop_reasons": dict(sorted(Counter(row["stop_reason"] for row in rows).items())),
        "semantic_decision_accuracy": None,
    }


def audit_historical(repo: Path, codex_home: Path) -> dict:
    paired = json.loads((repo / "hosted/evaluation/paired-results.json").read_text(encoding="utf-8"))
    cases = [row for row in paired["cases"] if row.get("split") == "heldout_descriptive"]
    if len(cases) != 14 or len({row["case_id"] for row in cases}) != 14:
        raise ValueError("frozen held-out case set changed")
    case_ids = {row["case_id"] for row in cases}
    with (repo / "hosted/evaluation/results/corpus.jsonl").open(encoding="utf-8") as handle:
        gold_rows = [row for line in handle if (row := json.loads(line))["case_id"] in case_ids]
    gold_by_id = {row["case_id"]: row for row in gold_rows}
    if len(gold_rows) != len(cases) or len(gold_by_id) != len(cases):
        raise ValueError("paired case and gold corpus identities disagree")
    paths = _rollout_paths(codex_home)
    alignment = _load_alignment_parser(repo)
    parsed: dict[str, tuple[list[Any], str]] = {}
    results = {"dialogue_only": [], "dialogue_and_tool_calls": []}
    for case in cases:
        rollout = str(case["anchor"]["rollout_id"]).lower()
        if rollout not in parsed:
            path = paths.get(rollout)
            if path is None:
                raise ValueError("historical source rollout unavailable")
            before = hashlib.sha256(path.read_bytes()).hexdigest()
            meta = alignment.read_session_meta(path)
            if meta is None or meta.rollout_id.lower() != rollout:
                raise ValueError("historical source metadata mismatch")
            blocks = alignment.parse_rollout(path, meta)
            after = hashlib.sha256(path.read_bytes()).hexdigest()
            if before != after:
                raise ValueError("historical source changed during audit")
            verify_source_hash(paired["source_hashes"], rollout, after)
            parsed[rollout] = blocks, before
        blocks, source_hash = parsed[rollout]
        gold = gold_by_id[case["case_id"]]
        anchor = (rollout, int(case["anchor"]["turn"]),
                  int(case["anchor"]["source_ordinal"]))
        for name, include_tools in (("dialogue_only", False), ("dialogue_and_tool_calls", True)):
            messages = _source_inventory(blocks, rollout, include_tools=include_tools)
            result = audit_case(messages, anchor, gold["evidence_coordinates"], case["case_id"])
            result["source_file_sha256"] = source_hash
            results[name].append(result)
    return {
        "schema_version": 1,
        "purpose": "historical oracle source coverage only; not semantic or fresh-gate accuracy",
        "source_manifest_sha256": hashlib.sha256(
            (repo / "hosted/evaluation/results/corpus.jsonl").read_bytes()).hexdigest(),
        "paired_results_sha256": hashlib.sha256(
            (repo / "hosted/evaluation/paired-results.json").read_bytes()).hexdigest(),
        "summary": {name: _summary(rows) for name, rows in results.items()},
        "cases": results,
    }


def _private_target(path: Path) -> Path:
    module_path = Path(__file__).with_name("freeze_exposure.py")
    spec = importlib.util.spec_from_file_location("decision_exposure_guard_for_audit", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load private-output guard")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.validate_output_path(path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--private-output", type=Path, required=True)
    args = parser.parse_args(argv)
    target = _private_target(args.private_output)
    repo = Path(__file__).resolve().parents[2]
    result = audit_historical(repo, args.codex_home)
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, ensure_ascii=False, sort_keys=True, indent=2)
        handle.write("\n")
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

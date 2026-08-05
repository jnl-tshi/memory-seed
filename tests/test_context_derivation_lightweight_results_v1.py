from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "experiments" / "context-derivation" / "lightweight_results_v1.py"
SPEC = importlib.util.spec_from_file_location("lightweight_results_v1", PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


def evidence(query, gold):
    return {
        "decisions": [{"ref": ref, "excerpt": ref} for ref in sorted(set(gold["authoritative_refs"]) | {binding["decision_ref"] for binding in gold["required_constitution_bindings"]})],
        "adrs": [{"adr_id": adr, "current": {"authoritative_ref": gold["authoritative_refs"][0], "status": gold["expected_statuses"][adr]}} for adr in gold["required_adr_ids"]],
        "constitution": [{"ref": ref, "text": ref} for binding in gold["required_constitution_bindings"] for ref in binding["constitution_refs"]],
    }


def answer(gold):
    constitution = sorted({ref for binding in gold["required_constitution_bindings"] for ref in binding["constitution_refs"]})
    citations = sorted(set(gold["authoritative_refs"]) | set(constitution))
    return {
        "schema": "context-answer.v1", "adr_ids": list(gold["required_adr_ids"]), "authoritative_refs": list(gold["authoritative_refs"]),
        "adr_statuses": dict(gold["expected_statuses"]), "lineage_edges": list(gold["required_lineage_edges"]),
        "related_edges": list(gold.get("required_related_edges", [])), "citations": citations, "explanation": "mechanical fixture",
        "insufficient_evidence": gold["insufficient_evidence"], "missing_refs": list(gold.get("required_missing_refs", [])),
    }


def fixtures():
    corpus, rows = module.queries.load_query_variants()
    gold_by_parent = {query["parent_task_id"]: gold for query, gold in module.queries.join_queries_to_gold()}
    packets, results = [], []
    for query in rows:
        gold = gold_by_parent[query["parent_task_id"]]
        for arm in module.ARMS:
            item_evidence = evidence(query, gold)
            payload = {"schema": module.subjects.PACKET_SCHEMA, "arm": arm, "evidence": item_evidence}
            packet = {"schema": module.PACKET_MANIFEST_SCHEMA, "query_id": query["query_id"], "parent_task_id": query["parent_task_id"], "arm": arm, "evidence": item_evidence, "packet_fingerprint": module.fingerprint(payload), "context_fingerprint": module.fingerprint(item_evidence)}
            packets.append(packet)
            for subject in module.SUBJECTS:
                pin = {"subject": subject, "requested_model": subject, "reported_model": subject, "model_digest": "sha256:fixture", "quantization": "Q4", "context_window": 4096, "decoding": {"temperature": 0}, "provider_version": "fixture", "cli_version": None, "adapter_version": "fixture"}
                results.append({"schema": module.subjects.RESULT_SCHEMA, "query_id": query["query_id"], "parent_task_id": query["parent_task_id"], "arm": arm, "subject": subject, "packet_fingerprint": packet["packet_fingerprint"], "context_fingerprint": packet["context_fingerprint"], "task_fingerprint": module.fingerprint(query), "corpus_fingerprint": corpus["canonical_fingerprint"], "pin": pin, "pin_fingerprint": module.fingerprint(pin), "duration_ms": 12.5, "usage": {"input_tokens": 20}, "token_proxy": 10, "protocol_failure": None, "parsed_answer": answer(gold)})
    return rows, packets, results


def test_complete_360_results_score_and_render_deterministically(tmp_path):
    rows, packets, results = fixtures()
    first = module.score_experiment(results, packets, query_rows=rows)
    second = module.score_experiment(list(reversed(results)), packets, query_rows=rows)
    assert first == second
    assert first["recommendation"] == "adr-constitution"
    assert first["subjects"]["local"]["adr-constitution"]["gates"]["complete_correct"] == {"passing": 60, "required": 60, "threshold": 54, "complete": True}
    assert module.render_markdown(first) == module.render_markdown(second)
    output = module.write_reports(first, tmp_path / "summary.json", tmp_path / "summary.md")
    assert json.loads(output[0].read_text()) == first and output[1].read_text() == module.render_markdown(first)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "extra", "cross-corpus", "protocol", "packet-fingerprint"])
def test_results_reject_incomplete_or_untrusted_cells(mutation):
    rows, packets, results = fixtures()
    if mutation == "missing": results.pop()
    elif mutation == "duplicate": results.append(dict(results[0]))
    elif mutation == "extra": results[0] = {**results[0], "subject": "other"}
    elif mutation == "cross-corpus": results[0] = {**results[0], "corpus_fingerprint": "sha256:" + "0" * 64}
    elif mutation == "protocol": results[0] = {**results[0], "protocol_failure": "invalid-answer-schema"}
    else: results[0] = {**results[0], "packet_fingerprint": "sha256:" + "0" * 64}
    with pytest.raises(ValueError):
        module.score_experiment(results, packets, query_rows=rows)


def test_hard_gates_fail_independently_at_the_54_boundary():
    rows, packets, results = fixtures()
    targets = [row for row in results if row["subject"] == "local" and row["arm"] == "adr-constitution"][:6]
    for row in targets:
        row["parsed_answer"] = {**row["parsed_answer"], "adr_ids": []}
    scored = module.score_experiment(results, packets, query_rows=rows)
    local = scored["subjects"]["local"]["adr-constitution"]
    assert local["complete_correct"] == 54
    assert not local["passing"] and not scored["recommendation"]


@pytest.mark.parametrize("field", ["authoritative_refs", "adr_statuses", "citations", "related_edges"])
def test_authority_status_citation_and_related_failures_cannot_be_repaired_by_high_accuracy(field):
    rows, packets, results = fixtures()
    target = next(row for row in results if row["subject"] == "luna" and row["arm"] == "adr-constitution" and row["parent_task_id"] == "CTX-11")
    bad = dict(target["parsed_answer"])
    bad[field] = {} if field == "adr_statuses" else []
    target.update(parsed_answer=bad)
    scored = module.score_experiment(results, packets, query_rows=rows)
    assert scored["subjects"]["luna"]["adr-constitution"]["complete_correct"] == 59
    assert scored["recommendation"] is None


def test_arm_noninferiority_is_per_subject_and_judges_are_non_authoritative():
    rows, packets, results = fixtures()
    constitution = next(row for row in results if row["subject"] == "local" and row["arm"] == "adr-constitution")
    constitution["parsed_answer"] = {**constitution["parsed_answer"], "adr_ids": []}
    reviewed = [{"schema": module.JUDGE_SCHEMA, "subject": "local", "query_id": constitution["query_id"], "verdict": "excellent"}]
    scored = module.score_experiment(results, packets, query_rows=rows, judge_records=reviewed)
    assert scored["subjects"]["local"]["adr-constitution"]["noninferior_to"]["adr-current"] is False
    assert scored["recommendation"] is None and scored["explanation_reviews"] == reviewed


def test_not_run_is_explicit_and_non_vacuous():
    result = module.score_experiment([], [])
    assert result["status"] == "not_run"
    assert result["observed_cell_count"] == 0 and result["expected_cell_count"] == 360
    assert result["recommendation"] is None

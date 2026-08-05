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
    edge_refs = {ref for edge in [*gold["required_lineage_edges"], *gold.get("required_related_edges", [])] for ref in (edge["source"], edge["target"])}
    return {
        "decisions": [{"ref": ref, "excerpt": ref} for ref in sorted(set(gold["authoritative_refs"]) | {binding["decision_ref"] for binding in gold["required_constitution_bindings"]} | edge_refs)],
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
            subject_query = module._subject_query(query)
            full_evidence = {"query": subject_query, **item_evidence}
            payload = {"schema": module.subjects.PACKET_SCHEMA, "arm": arm, "evidence": full_evidence}
            packet = {"schema": module.PACKET_MANIFEST_SCHEMA, "query_id": query["query_id"], "parent_task_id": query["parent_task_id"], "arm": arm, "query": subject_query, "corpus_fingerprint": corpus["canonical_fingerprint"], "task_fingerprint": module.fingerprint(subject_query), "evidence": item_evidence, "packet_fingerprint": module.fingerprint(payload), "context_fingerprint": module.fingerprint(full_evidence)}
            packets.append(packet)
            for subject in module.SUBJECTS:
                pin = {"subject": subject, "requested_model": subject, "reported_model": subject, "model_digest": "sha256:fixture", "quantization": "Q4", "context_window": 4096, "decoding": {"temperature": 0}, "provider_version": "fixture", "cli_version": None, "adapter_version": "fixture"}
                results.append({"schema": module.subjects.RESULT_SCHEMA, "query_id": query["query_id"], "parent_task_id": query["parent_task_id"], "arm": arm, "subject": subject, "packet_fingerprint": packet["packet_fingerprint"], "context_fingerprint": packet["context_fingerprint"], "task_fingerprint": packet["task_fingerprint"], "corpus_fingerprint": corpus["canonical_fingerprint"], "pin": pin, "pin_fingerprint": module.fingerprint(pin), "duration_ms": 12.5, "usage": {"input_tokens": 20}, "token_proxy": 10, "transcript": "transcript.json", "protocol_failure": None, "isolation": {"empty_cwd": True, "repo_access": False, "mcp_enabled": False}, "parsed_answer": answer(gold)})
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


def test_canonical_query_body_packet_gold_leak_and_minimal_pin_cannot_self_validate():
    rows, packets, results = fixtures()
    altered_rows = [dict(row) for row in rows]
    altered_rows[0]["question"] = "same id but a different caller-supplied question"
    with pytest.raises(ValueError, match="frozen 60-query"):
        module.score_experiment(results, packets, query_rows=altered_rows)
    leaked = [dict(packet) for packet in packets]
    leaked[0]["evidence"] = {**leaked[0]["evidence"], "required_adr_ids": ["adr_leak"]}
    with pytest.raises(ValueError, match="gold"):
        module.score_experiment(results, leaked, query_rows=rows)
    minimal = list(results)
    minimal[0] = {**minimal[0], "pin": {"subject": "local"}, "pin_fingerprint": module.fingerprint({"subject": "local"})}
    with pytest.raises(ValueError, match="pin"):
        module.score_experiment(minimal, packets, query_rows=rows)


def test_hard_gates_fail_independently_at_the_54_boundary():
    rows, packets, results = fixtures()
    targets = [row for row in results if row["subject"] == "local" and row["arm"] == "adr-constitution"][:6]
    for row in targets:
        row["parsed_answer"] = {**row["parsed_answer"], "adr_ids": []}
    scored = module.score_experiment(results, packets, query_rows=rows)
    local = scored["subjects"]["local"]["adr-constitution"]
    assert local["complete_correct"] == 54
    assert not local["passing"] and not scored["recommendation"]


def test_ctx12_gate_requires_five_complete_negative_control_answers():
    rows, packets, results = fixtures()
    for row in [row for row in results if row["subject"] == "local" and row["arm"] == "adr-constitution" and row["parent_task_id"] == "CTX-12"]:
        row["parsed_answer"] = {**row["parsed_answer"], "adr_ids": ["adr_unsupported_claim"]}
    scored = module.score_experiment(results, packets, query_rows=rows)
    gate = scored["subjects"]["local"]["adr-constitution"]["gates"]["missing_evidence_abstention"]
    assert gate == {"passing": 0, "required": 5, "threshold": 5, "complete": False}


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


def test_adr_citations_and_explanation_refs_must_be_declared_in_evidence():
    rows, packets, results = fixtures()
    target = next(row for row in results if row["subject"] == "local" and row["arm"] == "adr-constitution" and row["parent_task_id"] == "CTX-01")
    target["parsed_answer"] = {**target["parsed_answer"], "citations": ["adr_mcp_decision_envelope_review"], "explanation": "See adr_undeclared."}
    scored = module.score_experiment(results, packets, query_rows=rows)
    checks = scored["subjects"]["local"]["adr-constitution"]["failures_by_task_family"]
    assert {"task_id": "CTX-01", "failures": ["constitution_refs", "material_refs"]} in checks


def test_evidence_present_gold_adr_citation_is_allowed():
    rows, packets, results = fixtures()
    target = next(row for row in results if row["subject"] == "local" and row["arm"] == "adr-constitution" and row["parent_task_id"] == "CTX-01")
    target["parsed_answer"] = {**target["parsed_answer"], "citations": [*target["parsed_answer"]["citations"], "adr_mcp_decision_envelope_review"]}
    scored = module.score_experiment(results, packets, query_rows=rows)
    assert scored["subjects"]["local"]["adr-constitution"]["complete_correct"] == 60


@pytest.mark.parametrize("mutation", ["numeric-pin", "unsafe-isolation", "pin-drift"])
def test_pin_types_safe_isolation_and_subject_pin_consistency_are_enforced(mutation):
    rows, packets, results = fixtures()
    target = results[0]
    if mutation == "numeric-pin":
        pin = {**target["pin"], "requested_model": 7}
        results[0] = {**target, "pin": pin, "pin_fingerprint": module.fingerprint(pin)}
    elif mutation == "unsafe-isolation":
        results[0] = {**target, "isolation": {**target["isolation"], "empty_cwd": False}}
    else:
        target = next(row for row in results if row["subject"] == "local" and row["query_id"] != results[0]["query_id"])
        pin = {**target["pin"], "model_digest": "sha256:changed"}
        target.update(pin=pin, pin_fingerprint=module.fingerprint(pin))
    with pytest.raises(ValueError, match="pin|isolation"):
        module.score_experiment(results, packets, query_rows=rows)


def valid_topk_aggregate():
    shards = {}
    for k in (1, 3, 5):
        shards[str(k)] = {"k": k, "cell_count": 60, "query_corpus_fingerprint": module.queries.load_query_variants()[0]["canonical_fingerprint"], "complete_query_recall": {"passing": 60, "required": 60, "threshold": 57, "rate": 1.0, "complete": True}, "critical_gates": {name: {"applicable": 1, "passing": 1, "required": 1, "complete": True} for name in module.topk.CRITICAL_DIMENSIONS}, "errors": [], "passing": True}
    result = {"schema": module.topk.SCHEMA, "k_values": [1, 3, 5], "results": shards, "ranking_arm": "production-default", "recommended_k": 1}
    result["fingerprint"] = module.fingerprint(result)
    return result


def test_topk_rejects_self_fingerprinted_empty_shards():
    empty = {"schema": module.topk.SCHEMA, "k_values": [1, 3, 5], "results": {"1": {}, "3": {}, "5": {}}, "ranking_arm": "production-default", "recommended_k": None}
    empty["fingerprint"] = module.fingerprint(empty)
    with pytest.raises(ValueError, match="incomplete"):
        module.score_experiment([], [], topk_aggregate=empty)
    assert module.score_experiment([], [], topk_aggregate=valid_topk_aggregate())["topk"]["recommended_k"] == 1


def test_topk_rejects_semantic_failure_hidden_by_empty_errors_and_passing_flag():
    aggregate = valid_topk_aggregate()
    shard = aggregate["results"]["3"]
    shard["complete_query_recall"] = {"passing": 0, "required": 60, "threshold": 57, "rate": 0.0, "complete": False}
    aggregate["fingerprint"] = module.fingerprint({key: value for key, value in aggregate.items() if key != "fingerprint"})
    with pytest.raises(ValueError, match="semantic"):
        module.score_experiment([], [], topk_aggregate=aggregate)


def test_topk_rejects_hidden_critical_gate_numerator_failure():
    aggregate = valid_topk_aggregate()
    aggregate["results"]["5"]["critical_gates"]["authority"] = {"applicable": 60, "passing": 59, "required": 60, "complete": False}
    aggregate["fingerprint"] = module.fingerprint({key: value for key, value in aggregate.items() if key != "fingerprint"})
    with pytest.raises(ValueError, match="semantic"):
        module.score_experiment([], [], topk_aggregate=aggregate)


def test_not_run_is_explicit_and_non_vacuous():
    result = module.score_experiment([], [])
    assert result["status"] == "not_run"
    assert result["observed_cell_count"] == 0 and result["expected_cell_count"] == 360
    assert result["recommendation"] is None
    assert result["subjects"]["luna"]["adr-constitution"]["gates"]["complete_correct"]["threshold"] == 54
    assert result["subjects"]["local"]["adr-constitution"]["noninferior_to"]["decision-only"] == "not_evaluated"
    markdown = module.render_markdown(result)
    assert "0/60 (threshold 54)" in markdown and "Task-family failures and distributions" in markdown and "not_evaluated" in markdown

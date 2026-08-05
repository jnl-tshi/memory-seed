from __future__ import annotations

import copy
import importlib.util
import sys
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "experiments" / "context-derivation" / "lightweight_topk_v1.py"
SPEC = importlib.util.spec_from_file_location("lightweight_topk_v1", PATH)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


FIXTURE_SPEC = importlib.util.spec_from_file_location("lightweight_topk_fixture_builder", ROOT / "experiments" / "context-derivation" / "generate_fixtures.py")
assert FIXTURE_SPEC and FIXTURE_SPEC.loader
fixture_builder = importlib.util.module_from_spec(FIXTURE_SPEC)
sys.modules[FIXTURE_SPEC.name] = fixture_builder
FIXTURE_SPEC.loader.exec_module(fixture_builder)


D1 = "mse_alpha123:d1"
D2 = "mse_bravo234:d1"
CORPUS = "sha256:" + "a" * 64


def query(query_id: str = "CTX-01.V01") -> dict[str, object]:
    return {"query_id": query_id, "parent_task_id": query_id.split(".")[0], "question": "test"}


def gold(*, decisions: list[str] | None = None, binding_decision: str = D1) -> dict[str, object]:
    return {
        "relevant_refs": decisions or [D1],
        "required_adr_ids": ["adr_alpha"],
        "authoritative_refs": [D1],
        "expected_statuses": {"adr_alpha": "accepted"},
        "required_lineage_edges": [{"source": D1, "target": D2, "type": "evolves"}],
        "required_related_edges": [{"source": D1, "target": D2, "type": "related"}],
        "required_constitution_bindings": [{"adr_id": "adr_alpha", "decision_ref": binding_decision, "constitution_refs": ["constitution:v1#authority"]}],
    }


def packet(*, trigger_ref: str = D1, trigger_kind: str = "ranked", extra_adr: bool = False) -> dict[str, object]:
    adrs = [{
        "adr_id": "adr_alpha", "trigger": {"decision_ref": trigger_ref, "kind": trigger_kind},
        "current": {"authoritative_ref": D1, "status": "accepted"},
        "constitution": [{"ref": "constitution:v1#authority"}],
        "relevant_lineage": [{"ref": D1, "predecessors": [{"ref": D2, "type": "evolves"}]}],
    }]
    if extra_adr:
        adrs.append({"adr_id": "adr_extra", "trigger": {"decision_ref": trigger_ref, "kind": trigger_kind}, "current": {"authoritative_ref": D1, "status": "accepted"}, "constitution": [], "relevant_lineage": []})
    return {"schema": module.resolver.RESULT_SCHEMA, "tiers": [{"decision": {"ref": trigger_ref, "links": {"related": [D2]}}, "adrs": adrs}], "fingerprint": "packet"}


def ranked(*, related: bool = False) -> list[dict[str, object]]:
    return [{"ref": D1, "relevance": "strong", "excerpt": "one", "links": {"related": [D2]}, "trigger_kind": "related" if related else "ranked"}, {"ref": D2, "relevance": "strong", "excerpt": "two", "links": {"related": []}, "trigger_kind": "ranked"}]


def cell(query_id: str = "CTX-01.V01", *, k: int = 1) -> dict[str, object]:
    return module.score_query_cell(query(query_id), gold(), ranked(), packet(), k=k, query_corpus_fingerprint=CORPUS)


def cells_for(k: int, *, failures: int = 0) -> list[dict[str, object]]:
    rows = []
    for index, query_id in enumerate(module.QUERY_IDS):
        row = cell(query_id, k=k)
        if index < failures:
            row["complete_query_decision_recall"] = {**row["complete_query_decision_recall"], "complete": False}
        rows.append(row)
    return rows


def approved_topk_receipt(fixture_roots):
    receipt = module.topk_frozen_run_proposal(fixture_roots)
    receipt["approval_status"] = "APPROVED"
    receipt["fingerprint"] = module.subjects.fingerprint({key: value for key, value in receipt.items() if key != "fingerprint"})
    return receipt


def approved_ranking_receipt(question, fixture_root):
    receipt = module.bridge.ranking_receipt_proposal(question, fixture_root, top_k=max(module.K_VALUES))
    receipt["approval_status"] = "APPROVED"
    receipt["fingerprint"] = module.bridge.fingerprint({key: value for key, value in receipt.items() if key != "fingerprint"})
    return receipt


def test_complete_query_recall_keeps_k1_multi_decision_infeasible() -> None:
    result = module.score_query_cell(query(), gold(decisions=[D1, D2]), ranked(), packet(), k=1, query_corpus_fingerprint=CORPUS)
    assert result["complete_query_decision_recall"] == {"hits": 1, "required": 2, "complete": False, "infeasible": True}
    assert "incomplete-query-decision-recall" in result["failures"]


def test_one_error_in_any_critical_dimension_fails_exact_closure() -> None:
    result = module.score_query_cell(query(), gold(), ranked(), packet(extra_adr=True), k=1, query_corpus_fingerprint=CORPUS)
    assert result["critical"]["adr_closure"]["extra"] == ["adr_extra"]
    assert "adr_closure" in result["failures"]


def test_binding_pair_mismatch_fails_even_when_the_flat_constitution_ref_matches() -> None:
    result = module.score_query_cell(query(), gold(binding_decision=D1), ranked(), packet(trigger_ref=D2), k=3, query_corpus_fingerprint=CORPUS)
    assert result["critical"]["constitution_binding"]["missing"]
    assert result["critical"]["constitution_binding"]["extra"]
    assert "constitution_binding" in result["failures"]


def test_related_trigger_leakage_is_a_hard_failure() -> None:
    result = module.score_query_cell(query(), gold(), ranked(related=True), packet(trigger_kind="related"), k=1, query_corpus_fingerprint=CORPUS)
    assert result["provenance_failures"] == ["adr_alpha:related-trigger-leakage"]
    assert "adr_alpha:related-trigger-leakage" in result["failures"]


def test_reducer_enforces_57_of_60_and_deterministically_selects_smallest_passing_k() -> None:
    result = module.aggregate_cells(cells_for(1, failures=4) + cells_for(3, failures=3) + cells_for(5, failures=3))
    assert result["results"]["1"]["complete_query_recall"]["passing"] == 56
    assert result["results"]["1"]["passing"] is False
    assert result["results"]["3"]["complete_query_recall"]["passing"] == 57
    assert result["results"]["3"]["passing"] is True
    assert result["recommended_k"] == 3


def test_reducer_fails_closed_for_missing_duplicate_and_mixed_fingerprint_cells() -> None:
    complete = cells_for(1) + cells_for(3) + cells_for(5)
    missing = module.aggregate_cells(complete[:-1])
    assert "incomplete-shard" in missing["results"]["5"]["errors"]
    duplicate = copy.deepcopy(complete)
    duplicate[-1]["query_id"] = duplicate[-2]["query_id"]
    reduced = module.aggregate_cells(duplicate)
    assert "duplicate-query-cell" in reduced["results"]["5"]["errors"]
    mixed = copy.deepcopy(complete)
    mixed[0]["query_corpus_fingerprint"] = "sha256:" + "b" * 64
    reduced = module.aggregate_cells(mixed)
    assert "mixed-query-corpus-fingerprint" in reduced["results"]["1"]["errors"]


def test_lexical_diagnostic_cells_can_never_select_a_k() -> None:
    rows = cells_for(1) + cells_for(3) + cells_for(5)
    for row in rows:
        row["ranking_arm"] = "lexical-diagnostic"
    assert module.aggregate_cells(rows)["recommended_k"] is None


def test_k5_failure_removes_any_recommendation() -> None:
    result = module.aggregate_cells(cells_for(1) + cells_for(3) + cells_for(5, failures=4))
    assert result["results"]["3"]["passing"] is True
    assert result["results"]["5"]["passing"] is False
    assert result["recommended_k"] is None


def test_vacuous_critical_coverage_fails_closed() -> None:
    rows = cells_for(1) + cells_for(3) + cells_for(5)
    for row in rows:
        row["critical"]["lineage"] = {"required": 0, "complete": True}
    result = module.aggregate_cells(rows)
    assert result["results"]["1"]["critical_gates"]["lineage"] == {"applicable": 0, "passing": 0, "required": 0, "complete": False}
    assert result["recommended_k"] is None


def test_aggregate_provenance_failure_blocks_k_selection_even_when_recall_and_critical_gates_pass() -> None:
    rows = cells_for(1) + cells_for(3) + cells_for(5)
    for k in module.K_VALUES:
        row = next(row for row in rows if row["k"] == k and row["query_id"] == "CTX-01.V01")
        row["provenance_failures"] = ["adr_alpha:related-trigger-leakage"]
        row["failures"] = ["adr_alpha:related-trigger-leakage"]
    result = module.aggregate_cells(rows)
    assert result["results"]["3"]["critical_gates"]["related"]["complete"] is True
    assert result["results"]["3"]["provenance_failures_by_query"] == [{"query_id": "CTX-01.V01", "failures": ["adr_alpha:related-trigger-leakage"]}]
    assert "provenance-gate" in result["results"]["3"]["errors"]
    assert result["recommended_k"] is None


@pytest.mark.parametrize("dimension", ["related", "constitution_binding"])
def test_zero_denominator_extras_are_hard_failures_for_negative_controls(dimension: str) -> None:
    rows = cells_for(1) + cells_for(3) + cells_for(5)
    unexpected = "unexpected-related" if dimension == "related" else "unexpected-binding"
    for k in module.K_VALUES:
        row = next(row for row in rows if row["k"] == k and row["query_id"] == "CTX-01.V01")
        row["critical"][dimension] = {"required": 0, "found": [unexpected], "extra": [unexpected], "complete": False}
    result = module.aggregate_cells(rows)
    assert result["results"]["5"]["critical_gates"][dimension]["applicable"] == 60
    assert f"{dimension}-gate" in result["results"]["5"]["errors"]
    assert result["recommended_k"] is None


def test_corpus_fingerprint_must_match_across_all_k_shards() -> None:
    rows = cells_for(1) + cells_for(3) + cells_for(5)
    for row in rows:
        if row["k"] == 5:
            row["query_corpus_fingerprint"] = "sha256:" + "b" * 64
    result = module.aggregate_cells(rows)
    assert result["results"]["1"]["query_corpus_fingerprint"] == CORPUS
    assert result["results"]["5"]["query_corpus_fingerprint"] == "sha256:" + "b" * 64
    assert "mixed-query-corpus-fingerprint-across-k" in result["results"]["3"]["errors"]
    assert result["recommended_k"] is None


@pytest.mark.parametrize("parent", ["CTX-02", "CTX-04", "CTX-10"])
def test_offline_evaluator_materializes_fixture_revision_bindings_without_duplicate_adr_prose(monkeypatch, parent) -> None:
    with tempfile.TemporaryDirectory() as temporary:
        built = {item.fixture_id: item.path for item in fixture_builder.build_all(Path(temporary) / "fixtures")}
        query, gold = next((query, gold) for query, gold in module.queries.join_queries_to_gold() if query["parent_task_id"] == parent)
        roots = {query["fixture"]: built[query["fixture"]]}
        rows = [{"ref": ref, "relevance": "strong", "excerpt": ref, "links": {"evolves": [], "replaces": [], "related": []}} for ref in gold["relevant_refs"]]
        monkeypatch.setattr(module.bridge, "ranked_fixture_payload", lambda *_args, **_kwargs: {"rows": rows, "relevance_calibrated": False})
        receipt = approved_ranking_receipt(query["question"], roots[query["fixture"]])
        cells = module.evaluate_query_offline(query, gold, roots[query["fixture"]], query_corpus_fingerprint=module.queries.load_query_variants()[0]["canonical_fingerprint"], frozen_run=approved_topk_receipt(roots), ranking_receipt=receipt)
        cell = next(item for item in cells if item["k"] == 3)
        expected = {
            (binding["adr_id"], binding["decision_ref"], tuple(sorted(binding["constitution_refs"])))
            for binding in gold["required_constitution_bindings"]
        }
        assert len(expected) == 2
        assert set(cell["critical"]["constitution_binding"]["found"]) == expected
        altered_gold = copy.deepcopy(gold)
        altered_gold["required_constitution_bindings"] = []
        altered = module.evaluate_query_offline(query, altered_gold, roots[query["fixture"]], query_corpus_fingerprint=module.queries.load_query_variants()[0]["canonical_fingerprint"], frozen_run=approved_topk_receipt(roots), ranking_receipt=receipt)
        altered_cell = next(item for item in altered if item["k"] == 3)
        assert altered_cell["packet_fingerprint"] == cell["packet_fingerprint"]
        assert altered_cell["critical"]["constitution_binding"]["found"] == cell["critical"]["constitution_binding"]["found"]


@pytest.mark.parametrize("stale", [False, True])
def test_offline_evaluator_gate_blocks_ranking_before_any_reader_call(monkeypatch, stale) -> None:
    calls = []
    monkeypatch.setattr(module.bridge, "ranked_fixture_payload", lambda *_args, **_kwargs: calls.append("ranking") or {"rows": [], "relevance_calibrated": False})
    fixture_roots = {"real-current": Path("missing-fixture")}
    receipt = None
    if stale:
        receipt = {"schema": module.subjects.FROZEN_RUN_SCHEMA, "kind": "topk", "approval_status": "APPROVED", "corpus_fingerprint": "sha256:" + "0" * 64, "schedule_fingerprint": "sha256:" + "0" * 64, "packet_fingerprint": "sha256:" + "0" * 64, "selected_pins": {}, "fingerprint": "sha256:" + "0" * 64}
    with pytest.raises(RuntimeError, match="frozen-run|approved frozen-run"):
        module.evaluate_corpus_offline(fixture_roots, frozen_run=receipt)
    assert calls == []


def test_perfect_rankings_close_all_base_task_gates_without_gold_packet_construction(monkeypatch) -> None:
    """Gold supplies test expectations only; packets read ranked refs plus frozen scope."""
    with tempfile.TemporaryDirectory() as temporary:
        built = {item.fixture_id: item.path for item in fixture_builder.build_all(Path(temporary) / "fixtures")}
        cases = [pair for pair in module.queries.join_queries_to_gold() if pair[0]["variant_index"] == 1]
        ranking_by_question = {}
        for query, gold in cases:
            related = {}
            for edge in gold.get("required_related_edges", []):
                related.setdefault(edge["source"], []).append(edge["target"])
            ranking_by_question[query["question"]] = [
                {"ref": ref, "relevance": "strong", "excerpt": ref, "links": {"evolves": [], "replaces": [], "related": related.get(ref, [])}}
                for ref in gold["relevant_refs"]
            ]
        monkeypatch.setattr(module.bridge, "ranked_fixture_payload", lambda question, *_args, **_kwargs: {"rows": ranking_by_question[question], "relevance_calibrated": False})
        found_by_parent = {}
        for query, gold in cases:
            roots = {query["fixture"]: built[query["fixture"]]}
            cells = module.evaluate_query_offline(
                query, gold, roots[query["fixture"]],
                query_corpus_fingerprint=module.queries.load_query_variants()[0]["canonical_fingerprint"],
                frozen_run=approved_topk_receipt(roots),
                ranking_receipt=approved_ranking_receipt(query["question"], roots[query["fixture"]]),
            )
            cell = next(row for row in cells if row["k"] == 5)
            assert cell["failures"] == []
            found_by_parent[query["parent_task_id"]] = set(cell["critical"]["constitution_binding"]["found"])
        assert set(found_by_parent) == {f"CTX-{number:02d}" for number in range(1, 13)}
        assert found_by_parent["CTX-01"] == {("adr_mcp_decision_envelope_review", "mse_17d0qqh34a07qp5b:d1", ("constitution:v1#authority", "constitution:v1#lineage"))}
        assert found_by_parent["CTX-05"] == {("adr_session_decision_authority", "mse_17d0qqh34a07qp5b:d1", ("constitution:v1#authority", "constitution:v1#provenance"))}
        assert found_by_parent["CTX-06"] == {
            ("adr_mcp_decision_envelope_review", "mse_17d0qqh34a07qp5b:d1", ("constitution:v1#authority",)),
            ("adr_session_decision_authority", "mse_17d0qqh34a07qp5b:d1", ("constitution:v1#provenance",)),
        }

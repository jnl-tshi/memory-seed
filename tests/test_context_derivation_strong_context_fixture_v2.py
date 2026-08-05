import importlib.util
import sys
import tempfile
from pathlib import Path

import pytest

from memory_seed.adr import AdrRecord, parse_adr, render_adr


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "context-derivation"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, EXPERIMENT / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fixture_builder = _load("strong_context_fixture_builder", "generate_fixtures.py")
bridge = _load("strong_context_fixture_bridge", "strong_context_fixture_v2.py")
strong = _load("strong_context_fixture_resolver", "strong_context_v2.py")


@pytest.fixture()
def fixtures():
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "fixtures"
        built = fixture_builder.build_all(output)
        yield {item.fixture_id: item.path for item in built}


def approved_ranking_receipt(query, fixture_root, *, top_k=8):
    receipt = bridge.ranking_receipt_proposal(query, fixture_root, top_k=top_k)
    receipt["approval_status"] = "APPROVED"
    receipt["fingerprint"] = bridge.fingerprint({key: value for key, value in receipt.items() if key != "fingerprint"})
    return receipt


def test_materializes_actual_adr_ledgers_and_constitution_bindings(fixtures):
    document = bridge.materialize_fixture_bindings(fixtures["adversarial-shared-decision"])

    assert document["schema"] == "strong-context-v2-bindings.v1"
    rows = {row["adr_id"]: row for row in document["adrs"]}
    assert set(rows) == {"adr_shared_cache", "adr_shared_audit"}
    assert rows["adr_shared_cache"]["current"]["authoritative_ref"] == "mse_ctxshared:d1"
    assert rows["adr_shared_audit"]["current"]["authoritative_ref"] == "mse_ctxshared:d1"
    assert rows["adr_shared_cache"]["constitution_refs"][0] == {
        "ref": "constitution:v1#locality",
        "role": "governing",
        "excerpt": "Context should include the smallest relevant evidence slice before broader project material.",
    }
    index = strong.load_bindings(document)
    revision = bridge.materialize_revision_constitution_bindings(fixtures["adversarial-shared-decision"], index)
    assert {(row["adr_id"], row["decision_ref"]) for row in revision} == {
        ("adr_shared_cache", "mse_ctxshared:d1"), ("adr_shared_audit", "mse_ctxshared:d1"),
    }


def test_related_supporting_evidence_remains_outside_membership(fixtures):
    document = bridge.materialize_fixture_bindings(fixtures["adversarial-related-only"])
    row = document["adrs"][0]

    assert row["membership"] == ["mse_ctxrelhead:d1"]
    assert row["related_refs"] == ["mse_ctxrelcontext:d1"]


def test_pending_revision_does_not_displace_the_accepted_head(fixtures):
    document = bridge.materialize_fixture_bindings(fixtures["adversarial-pending"])
    row = document["adrs"][0]

    assert row["current"]["authoritative_ref"] == "mse_ctxpendinghead:d1"
    assert row["current"]["status"] == "accepted"
    assert [item["ref"] for item in row["lineage"]] == [
        "mse_ctxpendinghead:d1", "mse_ctxpendingnew:d1"
    ]
    assert row["lineage"][1]["status"] == "proposed"
    assert row["lineage"][1]["predecessors"] == [
        {"ref": "mse_ctxpendinghead:d1", "type": "replaces"}
    ]


def test_unaccepted_adr_never_uses_a_proposal_as_an_authoritative_synopsis(fixtures):
    root = fixtures["adversarial-pending"]
    path = root / ".memory-seed" / "decisions" / "adr_pending_storage.md"
    original = parse_adr(path)
    unaccepted = AdrRecord(
        original.schema_version, original.adr_id, original.title, original.topics,
        original.created_at, original.user_initials, original.agent_type, original.source,
        [event for event in original.events if event.kind != "revision-accepted"], path,
    )
    path.write_text(render_adr(unaccepted), encoding="utf-8")

    row = bridge.materialize_fixture_bindings(root)["adrs"][0]
    assert row["current"] == {
        "authoritative_ref": None,
        "status": "proposed",
        "decision": "",
        "why": "",
        "evolution": "",
    }


def test_matched_pending_and_rejected_branches_keep_typed_evidence_and_authority(fixtures):
    pending = strong.resolve_strong_context(
        [{"ref": "mse_ctxpendingnew:d1", "relevance": "strong", "excerpt": "pending", "links": {"evolves": [], "replaces": [], "related": []}}],
        bridge.materialize_fixture_bindings(fixtures["adversarial-pending"]),
    )
    pending_lineage = pending["tiers"][0]["adrs"][0]["relevant_lineage"]
    assert [row["ref"] for row in pending_lineage] == ["mse_ctxpendinghead:d1", "mse_ctxpendingnew:d1"]
    assert pending_lineage[1]["status"] == "proposed"
    assert pending_lineage[1]["predecessors"][0]["type"] == "replaces"

    rejected = strong.resolve_strong_context(
        [{"ref": "mse_ctxbrbad:d1", "relevance": "strong", "excerpt": "rejected", "links": {"evolves": [], "replaces": [], "related": []}}],
        bridge.materialize_fixture_bindings(fixtures["adversarial-branch-reject"]),
    )
    rejected_adr = rejected["tiers"][0]["adrs"][0]
    assert rejected_adr["current"]["authoritative_ref"] == "mse_ctxbrgood:d1"
    assert {row["ref"] for row in rejected_adr["relevant_lineage"]} == {
        "mse_ctxbrroot:d1", "mse_ctxbrgood:d1", "mse_ctxbrbad:d1"
    }
    assert next(row for row in rejected_adr["relevant_lineage"] if row["ref"] == "mse_ctxbrbad:d1")["status"] == "rejected"


def test_lineage_cap_never_hides_the_matched_branch_or_its_typed_link(fixtures):
    resolved = strong.resolve_strong_context(
        [{"ref": "mse_ctxpendingnew:d1", "relevance": "strong", "excerpt": "pending", "links": {"evolves": [], "replaces": [], "related": []}}],
        bridge.materialize_fixture_bindings(fixtures["adversarial-pending"]),
        {"lineage_item_cap": 0},
    )
    lineage = resolved["tiers"][0]["adrs"][0]["relevant_lineage"]
    assert [row["ref"] for row in lineage] == ["mse_ctxpendinghead:d1", "mse_ctxpendingnew:d1"]
    assert lineage[1]["predecessors"] == [{"ref": "mse_ctxpendinghead:d1", "type": "replaces"}]


def test_related_supporting_evidence_is_exposed_without_becoming_lineage(fixtures):
    resolved = strong.resolve_strong_context(
        [{"ref": "mse_ctxrelhead:d1", "relevance": "strong", "excerpt": "head", "links": {"evolves": [], "replaces": [], "related": ["mse_ctxrelcontext"]}}],
        bridge.materialize_fixture_bindings(fixtures["adversarial-related-only"]),
    )
    adr = resolved["tiers"][0]["adrs"][0]
    assert adr["related_refs"] == ["mse_ctxrelcontext:d1"]
    assert all(not row["predecessors"] for row in adr["relevant_lineage"])


def test_production_decision_ranking_feeds_the_experiment_adapter(fixtures):
    query = "signed checkpoints cache synchronization audit recovery"
    receipt = approved_ranking_receipt(query, fixtures["adversarial-shared-decision"], top_k=4)
    rows = bridge.ranked_fixture_results(
        query,
        fixtures["adversarial-shared-decision"],
        top_k=4,
        ranking_receipt=receipt,
    )

    assert rows
    assert all({"ref", "relevance", "excerpt", "links"} == set(row) for row in rows)
    assert "mse_ctxshared:d1" in [row["ref"] for row in rows]
    assert all(row["relevance"] in {"strong", "weak", "none"} for row in rows)
    payload = bridge.ranked_fixture_payload(
        query, fixtures["adversarial-shared-decision"], top_k=4, ranking_receipt=receipt,
    )
    assert payload["rows"] == rows
    assert payload["relevance_calibrated"] is False


@pytest.mark.parametrize("stale", [False, True])
def test_ranking_receipt_gate_makes_zero_reader_calls(monkeypatch, fixtures, stale):
    calls = []
    monkeypatch.setattr(bridge, "search_memory", lambda *_args, **_kwargs: calls.append("reader") or {"results": []})
    root, query = fixtures["adversarial-pending"], "pending storage authority"
    receipt = None
    if stale:
        receipt = approved_ranking_receipt(query, root)
        receipt["fingerprint"] = "sha256:" + "0" * 64
    with pytest.raises(RuntimeError, match="ranking receipt"):
        bridge.ranked_fixture_payload(query, root, ranking_receipt=receipt)
    assert calls == []


@pytest.mark.parametrize("drift_target", ["session", "adr", "revision-map"])
def test_ranking_receipt_rehashes_live_canonical_content_before_reader_call(monkeypatch, fixtures, drift_target):
    calls = []
    root, query = fixtures["adversarial-pending"], "pending storage authority"
    receipt = approved_ranking_receipt(query, root)
    if drift_target == "session":
        path = next((root / ".memory-seed" / "sessions").rglob("*.md"))
    elif drift_target == "adr":
        path = next((root / ".memory-seed" / "decisions").glob("*.md"))
    else:
        path = root / "REVISION_CONSTITUTION_BINDINGS.json"
    path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    monkeypatch.setattr(bridge, "search_memory", lambda *_args, **_kwargs: calls.append("reader") or {"results": []})
    with pytest.raises(RuntimeError, match="fixture content drift"):
        bridge.ranked_fixture_payload(query, root, ranking_receipt=receipt)
    assert calls == []


def test_missing_adr_ledger_fails_closed(fixtures):
    root = fixtures["adversarial-pending"]
    for path in (root / ".memory-seed" / "decisions").glob("*.md"):
        path.unlink()

    with pytest.raises(ValueError, match="coverage"):
        bridge.materialize_fixture_bindings(root)

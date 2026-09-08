"""Shared public adapters exercise real disposable Git transaction fixtures."""
import pytest

from memory_seed import reflection_ledger as kernel
from memory_seed.reflection_operations import run_reflection_operation as run
from test_reflection_workstream_ledger import _planned_transaction, _transaction_state, _git, _commit_transaction_receipts, _session_entry


@pytest.mark.parametrize("arguments", [
    {"apply": "false"}, {"apply": 1}, {"retention_days": 7.0}, {"retention_days": True},
    {"unknown": True}, {"cwd": []}, [],
])
def test_strict_arguments_before_git(arguments):
    assert run("ledger_init", arguments)["error"]["code"] == "invalid_arguments"


def test_init_preview_identity_no_write_and_apply_from_subdirectory(tmp_path):
    root, _preview, _ = _planned_transaction(tmp_path, "init")
    before = _transaction_state(root)
    preview = run("ledger_init", {"cwd": str(root / ".memory-seed")})
    assert preview["ok"], preview
    assert preview["workstream_id"].startswith("rwl_")
    assert not preview["applied"]
    assert _transaction_state(root) == before
    result = run("ledger_init", {"cwd": str(root), "apply": True, "expected_head": preview["head"]})
    assert result["ok"], result
    assert result["workstream_id"].startswith("rwl_")
    assert result["applied"]


def test_append_uses_shared_kernel_and_strict_boolean(tmp_path):
    root, preview, _ = _planned_transaction(tmp_path, "append")
    args = dict(cwd=str(root), workstream_id=preview.ledger_path.split("/")[-2], role="planner",
                no_related_thread=True, relationship="no_related_thread", conclusion="root", reasoning="reason", source="test")
    before = _transaction_state(root)
    assert run("ledger_append", {**args, "no_related_thread": "false"})["error"]["code"] == "invalid_arguments"
    assert _transaction_state(root) == before
    result = run("ledger_append", {**args, "apply": True})
    assert result["ok"] and result["applied"], result


def test_close_preview_apply_and_pending_receipt_completion(tmp_path):
    root, _, context = _planned_transaction(tmp_path, "close")
    locator = {key: value for key, value in context["receipt_locator"].items() if key != "chain_id"}
    args = dict(cwd=str(root), workstream_id=context["close_kwargs"]["workstream_id"],
                chain_id=context["chain"], receipts=[locator])
    before = _transaction_state(root)
    preview = run("ledger_close", args)
    assert preview["ok"], preview
    assert preview["status"] == "ready_to_close"
    assert not preview["missing_receipts"] and len(preview["required_receipts"]) == 4
    assert _transaction_state(root) == before
    result = run("ledger_close", {**args, "apply": True, "expected_head": preview["head"],
                                  "expected_ledger_digest": preview["pre_ledger_digest"]})
    assert result["ok"], result
    assert result["applied"] and result["status"] == "closed_receipts_pending"
    assert {item["kind"] for item in result["missing_receipts"]} == {"member", "closure"}
    board = run("board_view", {"cwd": str(root)})
    assert board["items"][0]["status"] == "closed_receipts_pending"
    # Draft the new close receipts in a new ordinary entry, without rewriting
    # the pre-close decision that supplied member coverage.
    close_locator = {**locator, "entry_id": "mse_abcdef0123456789"}
    drafted = run("ledger_close", {**args, "receipts": [close_locator]})
    assert len(drafted["required_receipts"]) == 2, drafted
    session = root / locator["session_path"]
    import yaml
    with session.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write("\n" + _session_entry("2026-09-06 12:20 - Close outcome", close_locator["entry_id"]))
        for mapping in drafted["required_receipts"]:
            stream.write("\n```yaml\n" + yaml.safe_dump(mapping, sort_keys=False) + "```\n")
    _git(root, "add", locator["session_path"])
    _git(root, "commit", "--quiet", "-m", "record close outcome receipts")
    closed = run("ledger_close", args)
    assert closed["status"] == "closed" and not closed["missing_receipts"], closed


def test_close_missing_receipts_and_malformed_locator_no_write(tmp_path):
    root, _, context = _planned_transaction(tmp_path, "close")
    args = dict(cwd=str(root), workstream_id=context["close_kwargs"]["workstream_id"], chain_id=context["chain"])
    before = _transaction_state(root)
    preview = run("ledger_close", args)
    assert preview["ok"] and len(preview["missing_receipts"]) == 4, preview
    assert all(item["receipt_id"].startswith("rrc_") for item in preview["required_receipts"])
    assert not run("ledger_close", {**args, "apply": True})["ok"]
    assert run("ledger_close", {**args, "receipts": [{"entry_id": "bad"}]})["error"]["code"] == "invalid_arguments"
    assert _transaction_state(root) == before


def test_close_stale_preview_and_kernel_cas_refusal(tmp_path, monkeypatch):
    root, _, context = _planned_transaction(tmp_path, "close")
    locator = {key: value for key, value in context["receipt_locator"].items() if key != "chain_id"}
    args = dict(cwd=str(root), workstream_id=context["close_kwargs"]["workstream_id"], chain_id=context["chain"], receipts=[locator])
    preview = run("ledger_close", args)
    assert preview["ok"], preview
    _git(root, "commit", "--allow-empty", "--quiet", "-m", "advance preview head")
    before = _transaction_state(root)
    refused = run("ledger_close", {**args, "apply": True, "expected_head": preview["head"]})
    assert refused["error"]["code"] == "stale_head"
    assert _transaction_state(root) == before
    apply = kernel.apply_workstream_commit
    def raced(cwd, planned):
        def race(stage):
            if stage == "before-cas":
                _git(root, "update-ref", "refs/heads/integration", preview["head"], planned.expected_head)
        return apply(cwd, planned, fault_injector=race)
    monkeypatch.setattr(kernel, "apply_workstream_commit", raced)
    refused = run("ledger_close", {**args, "apply": True})
    assert refused["error"]["code"] == "stale_ref", refused


def test_already_covered_promoted_receipts_and_witness_identity(tmp_path):
    from dataclasses import replace
    root, preview, context = _planned_transaction(tmp_path, "rebind")
    result = kernel.apply_workstream_commit(root, preview)
    loaded = kernel.load_trusted_workstream_ledger(root, trusted_ref="integration", ledger_path=preview.ledger_path)
    locator = {**context["receipt_locator"], "disposition": "already-covered-by-decision"}
    _commit_transaction_receipts(root, loaded, locator)
    loaded = kernel.load_trusted_workstream_ledger(root, trusted_ref="integration", ledger_path=preview.ledger_path)
    verifier = kernel.GitWorkstreamIntegrationVerifier(loaded)
    witness = verifier.witness()
    assert witness == result.integration_witness
    assert not verifier.verify_witness(replace(witness, source_tip="0" * 40))
    args = dict(cwd=str(root), workstream_id=loaded.ledger.header.workstream_id, chain_id=context["chain"],
                receipts=[{key: value for key, value in locator.items() if key != "chain_id"}], apply=True)
    closed = run("ledger_close", args)
    assert closed["ok"] and closed["status"] == "closed_receipts_pending", closed


def test_git_witness_refuses_rebind_without_its_exact_merge_parent(tmp_path):
    root, preview, context = _planned_transaction(tmp_path, "rebind")
    # A structurally valid rebind is not authority if its introduction is
    # separated from the integration it claims to immediately follow.
    _git(root, "commit", "--allow-empty", "--quiet", "-m", "unrelated intervening commit")
    path = root / preview.ledger_path
    with path.open("ab") as stream:
        stream.write(preview.suffix_bytes)
    _git(root, "add", preview.ledger_path)
    _git(root, "commit", "--quiet", "-m", "structural rebind only")
    loaded = kernel.load_trusted_workstream_ledger(root, trusted_ref="integration", ledger_path=preview.ledger_path)
    with pytest.raises(kernel.ReflectionValidationError, match="immediately follow"):
        kernel.GitWorkstreamIntegrationVerifier(loaded).witness()

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


@pytest.mark.parametrize("guard", ["expected_head", "expected_ledger_digest"])
def test_append_refuses_guard_change_between_load_and_kernel_preview(tmp_path, monkeypatch, guard):
    root, initial, _ = _planned_transaction(tmp_path, "append")
    args = dict(cwd=str(root), workstream_id=initial.ledger_path.split("/")[-2], role="planner",
                no_related_thread=True, relationship="no_related_thread", conclusion="root", reasoning="reason", source="test",
                apply=True)
    args[guard] = initial.expected_head if guard == "expected_head" else initial.pre_ledger_digest
    preview = kernel.preview_workstream_append_commit
    advanced = {}

    def advance_before_preview(cwd, **kwargs):
        if guard == "expected_head":
            _git(root, "commit", "--allow-empty", "--quiet", "-m", "advance after public guard")
        else:
            kernel.apply_workstream_commit(root, preview(cwd, **kwargs))
        advanced["state"] = _transaction_state(root)
        return preview(cwd, **kwargs)

    monkeypatch.setattr(kernel, "preview_workstream_append_commit", advance_before_preview)
    result = run("ledger_append", args)
    assert result["error"]["code"] == ("stale_head" if guard == "expected_head" else "stale_ledger_digest"), result
    assert _transaction_state(root) == advanced["state"]


def test_close_preview_apply_and_pending_receipt_completion(tmp_path, monkeypatch):
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
    loaded = kernel.load_trusted_workstream_ledger(root, trusted_ref="integration",
        ledger_path=kernel.workstream_ledger_path(args["workstream_id"]))
    classify = kernel._classify_trusted_workstream_ledger
    classifications = []

    def counted(*args, **kwargs):
        classifications.append(args)
        return classify(*args, **kwargs)

    monkeypatch.setattr(kernel, "_classify_trusted_workstream_ledger", counted)
    assert kernel.workstream_closed_receipt_status(loaded) == [
        {"chain_id": args["chain_id"], "status": "closed", "missing_receipts": []}]
    assert len(classifications) == 1


@pytest.mark.parametrize("duplicates", [1, 4])
def test_closed_receipt_status_classifies_once_with_duplicate_invalid_mappings(tmp_path, monkeypatch, duplicates):
    root, preview, context = _planned_transaction(tmp_path, "close")
    kernel.apply_workstream_commit(root, preview)
    loaded = kernel.load_trusted_workstream_ledger(root, trusted_ref="integration", ledger_path=preview.ledger_path)
    close = loaded.ledger.records[-1]
    mappings = kernel._committed_session_mappings(loaded)
    members = [value for value in mappings if "record_id" in value]
    assert len(members) == 4
    # Malformed candidates precede the exact receipts; unrelated mappings and
    # repeated copies must not trigger a history walk or whole-chain drafting.
    candidates = [{**value, "disposition": "invalid"} for value in members] * duplicates
    candidates += [{**value, "record_id": "unrelated"} for value in members] * duplicates
    candidates += mappings * duplicates
    monkeypatch.setattr(kernel, "_committed_session_mappings", lambda current: candidates)
    classify = kernel._classify_trusted_workstream_ledger
    classifications = []

    def counted(*args, **kwargs):
        classifications.append(args)
        return classify(*args, **kwargs)

    def no_chain_drafting(*args, **kwargs):
        pytest.fail("status must derive each candidate member directly")

    monkeypatch.setattr(kernel, "_classify_trusted_workstream_ledger", counted)
    monkeypatch.setattr(kernel, "plan_workstream_chain_receipts", no_chain_drafting)
    before = _transaction_state(root)
    assert kernel.workstream_closed_receipt_status(loaded) == [{
        "chain_id": context["chain"], "status": "closed_receipts_pending", "missing_receipts": [
            {"kind": "member", "workstream_id": loaded.ledger.header.workstream_id,
             "chain_id": close.chain_id, "record_id": close.record_id, "detail_digest": close.detail_digest,
             "receipt_id": kernel.workstream_receipt_id(loaded.ledger.header.id_salt,
                 loaded.ledger.header.workstream_id, close.chain_id, close.detail_digest)},
            {"kind": "closure", "chain_id": close.chain_id, "closed_record_id": close.record_id,
             "closed_record_digest": close.detail_digest}]}]
    assert len(classifications) == 1
    assert _transaction_state(root) == before
    # A stale caller snapshot still reports unverified member coverage as
    # missing, preserving the status reader's existing diagnostic contract.
    _git(root, "commit", "--allow-empty", "--quiet", "-m", "advance status snapshot")
    classifications.clear()
    stale = kernel.workstream_closed_receipt_status(loaded)
    assert stale[0]["status"] == "closed_receipts_pending"
    assert [item["record_id"] for item in stale[0]["missing_receipts"] if item["kind"] == "member"] == [
        record.record_id for record in loaded.ledger.records]
    assert stale[0]["missing_receipts"][-1]["kind"] == "closure"
    assert len(classifications) == 1


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


def test_git_witness_accepts_unchanged_advancement_after_exact_merge(tmp_path):
    root, preview, context = _planned_transaction(tmp_path, "rebind")
    # The merge event remains the integration identity after unchanged
    # target advancement; the later rebind introduction has its own CAS head.
    _git(root, "commit", "--allow-empty", "--quiet", "-m", "unrelated intervening commit")
    path = root / preview.ledger_path
    with path.open("ab") as stream:
        stream.write(preview.suffix_bytes)
    _git(root, "add", preview.ledger_path)
    _git(root, "commit", "--quiet", "-m", "structural rebind only")
    loaded = kernel.load_trusted_workstream_ledger(root, trusted_ref="integration", ledger_path=preview.ledger_path)
    assert kernel.GitWorkstreamIntegrationVerifier(loaded).witness().integration_commit == preview.expected_head


def _public_rebind_fixture(tmp_path, *, pr=False):
    root, first, _ = _planned_transaction(tmp_path, "append")
    applied = kernel.apply_workstream_commit(root, first)
    source = applied.ledger.effective_branch
    for name in _git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads/").splitlines():
        if name != source and name != "main":
            _git(root, "branch", "-m", name, "main")
    if pr:
        (root / ".memory-seed/project.yaml").write_text("integration_mode: pr\n", encoding="utf-8")
        _git(root, "add", ".memory-seed/project.yaml")
        _git(root, "commit", "--quiet", "-m", "final source preparation")
    args = dict(cwd=str(root), workstream_id=applied.ledger.header.workstream_id,
                source=source, reason="verified integration")
    return root, args, first.ledger_path


def _merge_public_source(root, args):
    _git(root, "checkout", "--quiet", "main")
    _git(root, "merge", "--quiet", "--no-ff", "-m", "integrate prepared source", args["source"])
    return _git(root, "rev-parse", "HEAD")


@pytest.mark.parametrize("pr", [False, True])
@pytest.mark.parametrize("delay", [False, True])
def test_public_rebind_happy_paths_and_unchanged_target_advancement(tmp_path, pr, delay):
    root, args, path = _public_rebind_fixture(tmp_path, pr=pr)
    if pr:
        before = _transaction_state(root)
        prepare = {key: args[key] for key in ("cwd", "workstream_id")}
        prepared = run("ledger_prepare", prepare)
        assert prepared["ok"] and not prepared["applied"], prepared
        assert _transaction_state(root) == before
        prepared = run("ledger_prepare", {**prepare, "apply": True})
        assert prepared["ok"] and prepared["applied"], prepared
        # Target may advance before the merge if it still has no source ledger.
        _git(root, "checkout", "--quiet", "main")
        _git(root, "commit", "--allow-empty", "--quiet", "-m", "target advances before merge")
    merge = _merge_public_source(root, args)
    if delay:
        _git(root, "commit", "--allow-empty", "--quiet", "-m", "target advances after merge")
    cas_head = _git(root, "rev-parse", "HEAD")
    operation = "ledger_finalize" if pr else "ledger_rebind"
    before = _transaction_state(root)
    preview = run(operation, args)
    assert preview["ok"] and not preview["applied"], preview
    assert preview["integration_commit"] == merge and preview["head"] == cas_head
    assert _transaction_state(root) == before
    result = run(operation, {**args, "apply": True})
    assert result["ok"] and result["applied"], result
    assert _git(root, "rev-parse", "HEAD^") == cas_head
    loaded = kernel.load_trusted_workstream_ledger(root, trusted_ref="main", ledger_path=path)
    assert kernel.GitWorkstreamIntegrationVerifier(loaded).witness().integration_commit == merge
    before = _transaction_state(root)
    assert not run(operation, {**args, "apply": True})["ok"]
    assert _transaction_state(root) == before


@pytest.mark.parametrize("mutation", ["delete", "advance", "move", "squash", "rebase", "reverse", "three-parents", "ledger-change"])
def test_public_finalize_refuses_changed_source_or_invalid_merge(tmp_path, mutation):
    root, args, path = _public_rebind_fixture(tmp_path, pr=True)
    prepare = {key: args[key] for key in ("cwd", "workstream_id")}
    assert run("ledger_prepare", {**prepare, "apply": True})["ok"]
    source_tip = _git(root, "rev-parse", "HEAD")
    base = _git(root, "rev-parse", "main")
    merge = _merge_public_source(root, args)
    if mutation == "delete":
        _git(root, "branch", "-D", args["source"])
    elif mutation in {"advance", "move"}:
        tip = base if mutation == "move" else _git(root, "commit-tree", source_tip + "^{tree}", "-p", source_tip, "-m", "advance source")
        _git(root, "update-ref", "refs/heads/" + args["source"], tip)
    elif mutation in {"squash", "rebase", "reverse", "three-parents"}:
        parents = [base] if mutation in {"squash", "rebase"} else [source_tip, base]
        if mutation == "rebase":
            parents = [_git(root, "commit-tree", base + "^{tree}", "-p", base, "-m", "new rebase base")]
        if mutation == "three-parents":
            extra = _git(root, "commit-tree", base + "^{tree}", "-p", base, "-m", "extra parent")
            parents = [base, source_tip, extra]
        options = [part for parent in parents for part in ("-p", parent)]
        replacement = _git(root, "commit-tree", merge + "^{tree}", *options, "-m", "invalid merge shape")
        _git(root, "update-ref", "refs/heads/main", replacement, merge)
    else:
        (root / path).write_bytes((root / path).read_bytes() + b"\ninvalid ledger\n")
        _git(root, "add", path)
        _git(root, "commit", "--quiet", "-m", "changed integrated ledger")
    before = _transaction_state(root)
    result = run("ledger_finalize", {**args, "apply": True})
    assert not result["ok"], result
    assert _transaction_state(root) == before


@pytest.mark.parametrize("operation", ["ledger_rebind", "ledger_prepare", "ledger_finalize"])
@pytest.mark.parametrize("extra", [{"apply": "false"}, {"token": "raw"}, {"target_branch": "other"},
                                  {"source_tip": "0" * 40}, {"expected_head": "0" * 40}, {"unknown": True}])
def test_rebind_public_arguments_are_locator_only(operation, extra):
    args = dict(workstream_id="rwl_invalid")
    if operation != "ledger_prepare":
        args["source"] = "feature"
        args["reason"] = "reason"
    assert run(operation, {**args, **extra})["error"]["code"] == "invalid_arguments"


@pytest.mark.parametrize("apply", [False, True])
def test_prepare_rejects_unused_reason_before_git(monkeypatch, apply):
    import memory_seed.reflection_operations as operations

    def no_git(*args, **kwargs):
        pytest.fail("unknown prepare fields must be rejected before repository access")

    monkeypatch.setattr(operations, "_context", no_git)
    result = run("ledger_prepare", dict(workstream_id="rwl_invalid", reason="unused", apply=apply))
    assert result["error"]["code"] == "invalid_arguments"
    assert result["error"]["message"] == "unsupported reflection argument(s): reason"


def test_prepare_requires_final_source_preparation_and_live_source_locator(tmp_path):
    root, args, _ = _public_rebind_fixture(tmp_path, pr=True)
    base = _git(root, "rev-parse", "main")
    advanced = _git(root, "commit-tree", base + "^{tree}", "-p", base, "-m", "target advances")
    _git(root, "update-ref", "refs/heads/main", advanced, base)
    prepare = {key: args[key] for key in ("cwd", "workstream_id")}
    result = run("ledger_prepare", prepare)
    assert not result["ok"] and "finish source preparation" in result["error"]["message"], result
    _git(root, "merge", "--quiet", "--no-ff", "-m", "finish preparing source", "main")
    assert run("ledger_prepare", {**prepare, "apply": True})["ok"]
    _merge_public_source(root, args)
    for source in (_git(root, "rev-parse", args["source"]), args["source"] + "~0", "../other", "refs/tags/source"):
        assert not run("ledger_finalize", {**args, "source": source, "apply": True})["ok"]


def test_finalize_handoff_is_canonical_nonsecret_and_repository_bound(tmp_path):
    import json
    import shutil
    root, args, _ = _public_rebind_fixture(tmp_path, pr=True)
    prepare = {key: args[key] for key in ("cwd", "workstream_id")}
    assert run("ledger_prepare", {**prepare, "apply": True})["ok"]
    handoff = next((root / ".git/memory-seed-reflection-handoffs").glob("*.json"))
    raw = handoff.read_bytes()
    payload = json.loads(raw)
    assert set(payload) == {"schema", "version", "repository", "workstream_id", "source_ref", "source_tip",
                            "target_ref", "target_tip", "ledger_blob", "pre_ledger_digest"}
    assert not _git(root, "status", "--porcelain")
    assert not run("ledger_prepare", {**prepare, "apply": True})["ok"]
    _merge_public_source(root, args)
    copied = tmp_path / "copied-repository"
    shutil.copytree(root, copied)
    refused = run("ledger_finalize", {**args, "cwd": str(copied), "apply": True})
    assert refused["error"]["code"] == "rebind-handoff", refused
    handoff.write_bytes(raw + b" ")
    assert not run("ledger_finalize", {**args, "apply": True})["ok"]
    assert not handoff.with_suffix(".consumed").exists()


def test_finalize_source_ref_cas_race_consumes_handoff_without_target_commit(tmp_path, monkeypatch):
    root, args, path = _public_rebind_fixture(tmp_path, pr=True)
    prepare = {key: args[key] for key in ("cwd", "workstream_id")}
    assert run("ledger_prepare", {**prepare, "apply": True})["ok"]
    source_tip = _git(root, "rev-parse", "HEAD")
    merge = _merge_public_source(root, args)
    raw = (root / path).read_bytes()
    apply = kernel.apply_workstream_commit

    def raced(cwd, preview):
        def race(stage):
            if stage == "before-cas":
                advanced = _git(root, "commit-tree", source_tip + "^{tree}", "-p", source_tip, "-m", "race source")
                _git(root, "update-ref", "refs/heads/" + args["source"], advanced, source_tip)
        return apply(cwd, preview, fault_injector=race)

    monkeypatch.setattr(kernel, "apply_workstream_commit", raced)
    result = run("ledger_finalize", {**args, "apply": True})
    assert result["error"]["code"] == "stale_ref", result
    assert _git(root, "rev-parse", "HEAD") == merge
    assert (root / path).read_bytes() == raw and not _git(root, "status", "--porcelain")
    _git(root, "update-ref", "refs/heads/" + args["source"], source_tip)
    assert run("ledger_finalize", {**args, "apply": True})["error"]["code"] == "rebind-handoff"


def test_rebind_ancestry_rejects_transient_ledger_edits_and_divergence(tmp_path):
    from test_reflection_workstream_ledger import _new_git_workstream
    root, _, path = _new_git_workstream(tmp_path)
    base = _git(root, "rev-parse", "HEAD")
    raw = (root / path).read_bytes()
    (root / path).write_bytes(raw + b"temporary edit\n")
    _git(root, "add", path)
    _git(root, "commit", "--quiet", "-m", "intervening ledger mutation")
    (root / path).write_bytes(raw)
    _git(root, "add", path)
    _git(root, "commit", "--quiet", "-m", "restore exact ledger bytes")
    with pytest.raises(kernel.ReflectionValidationError, match="target advancement changed"):
        kernel._unchanged_rebind_ancestry(root, base, _git(root, "rev-parse", "HEAD"), path)
    unrelated = _git(root, "commit-tree", base + "^{tree}", "-m", "unrelated target history")
    with pytest.raises(kernel.ReflectionValidationError, match="not descended"):
        kernel._unchanged_rebind_ancestry(root, base, unrelated, path)

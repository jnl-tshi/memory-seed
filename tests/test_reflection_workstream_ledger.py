from __future__ import annotations

from dataclasses import replace
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import ast
import inspect
import json
import os
from pathlib import Path
import subprocess
import stat
from types import SimpleNamespace

import pytest

from memory_seed import reflection_ledger as reflection_ledger_module
from memory_seed.reflection_ledger import (
    ReflectionValidationError,
    RetentionApproval,
    RetentionApprovalAdmission,
    RetentionApprovalTrust,
    RetentionExtensionReceipt,
    RetentionPreflight,
    RetentionPreflightVerifier,
    AdmittedWorkstreamReceipt,
    WorkstreamReceiptVerifier,
    TrustedIntegrationWitness,
    EarlyExpiryApproval,
    EarlyExpiryApprovalVerifier,
    TrustedRebindVerifier,
    WorkstreamAppendRequest,
    WorkstreamDependency,
    WorkstreamDependencyReceipt,
    WorkstreamCompactionClosureReceipt,
    WorkstreamCompactionMemberReceipt,
    WorkstreamCompactionReceipt,
    WorkstreamLedgerHeader,
    WorkstreamLedger,
    WorkstreamReceipt,
    apply_trusted_rebind,
    guarded_append_workstream_ledger,
    guarded_apply_workstream_expiry,
    guarded_apply_trusted_rebind,
    guarded_init_workstream_ledger,
    initialize_workstream_ledger,
    load_trusted_workstream_ledger,
    parse_retention_approval,
    parse_retention_preflight,
    parse_workstream_ledger,
    plan_workstream_append,
    plan_workstream_chain_close,
    preview_trusted_rebind,
    preview_workstream_expiry,
    preview_trusted_workstream_expiry,
    preview_workstream_append_commit,
    apply_workstream_append_commit,
    apply_workstream_commit,
    preview_workstream_init_commit,
    preview_workstream_rebind_commit,
    preview_workstream_close_commit,
    plan_workstream_chain_receipts,
    admit_workstream_chain_receipts,
    render_workstream_receipt,
    plan_trusted_workstream_chain_close,
    render_retention_approval,
    render_retention_preflight,
    render_workstream_ledger,
    render_workstream_compaction_receipt,
    render_workstream_record,
    reflection_ledger_family,
    resolve_workstream_dependency,
    validate_retention_approval_admission,
    workstream_board_view,
    workstream_chain_heads,
    workstream_chain_id,
    workstream_chain_phase,
    workstream_detail_digest,
    workstream_id,
    workstream_ledger_digest,
    workstream_ledger_path,
    workstream_receipt_id,
    workstream_record_id,
    validate_workstream_ledger,
)


BASE = "a" * 40
HEAD = "b" * 40
TARGET = "c" * 40
INTEGRATION = "d" * 40
SALT = "8f" * 32
START = datetime(2026, 9, 6, 12, 0, tzinfo=timezone.utc)


def fixed_clock(*values: datetime):
    items = iter(values)
    return lambda: next(items)


def make_ledger(branch: str = "codex/feature/example"):
    return initialize_workstream_ledger(
        working_branch=branch,
        base_sha=BASE,
        clock=fixed_clock(START),
        entropy=lambda size: bytes.fromhex(SALT),
    )


def append(ledger, role, chain_id, *, relationship="refines", parents=(), no_related_thread=False, now=START + timedelta(minutes=1), to_phase=None, **text):
    request = WorkstreamAppendRequest(
        role=role,
        chain_id=chain_id,
        relationship=relationship,
        parents=tuple(sorted(parents)),
        no_related_thread=no_related_thread,
        conclusion=text.get("conclusion", f"{role} conclusion"),
        reasoning=text.get("reasoning", f"{role} reasoning"),
        source=text.get("source", "focused-test"),
        confidence=text.get("confidence", "high"),
        depends_on=text.get("depends_on", ()),
        related_decisions=text.get("related_decisions", ()),
        to_phase=to_phase,
    )
    return plan_workstream_append(
        ledger,
        request,
        expected_head=HEAD,
        actual_head=HEAD,
        pre_ledger_digest=workstream_ledger_digest(render_workstream_ledger(ledger)),
        branch=ledger.effective_branch,
        clock=fixed_clock(now),
    )


def open_chain():
    ledger = make_ledger()
    ledger = append(ledger, "planner", None, relationship="no_related_thread", no_related_thread=True, now=START + timedelta(minutes=1))
    chain = ledger.records[-1].chain_id
    root = ledger.records[-1].record_id
    ledger = append(ledger, "planner", chain, parents=(root,), now=START + timedelta(minutes=2))
    return ledger, chain


def receipt_for(ledger, record):
    return WorkstreamReceipt(
        ledger.header.workstream_id,
        record.chain_id,
        record.record_id,
        record.detail_digest,
        ".memory-seed/sessions/2026-09/2026-09-06.md",
        "mse_0123456789abcdef",
        "D1",
        workstream_receipt_id(ledger.header.id_salt, ledger.header.workstream_id, record.chain_id, record.detail_digest),
        "sha256:" + "e" * 64,
        "promoted-to-decision",
    )


class AdmitReceipts(WorkstreamReceiptVerifier):
    def verify(self, admitted):
        return admitted.commit == HEAD and admitted.blob == "e" * 40


class AcceptEarlyExpiry(EarlyExpiryApprovalVerifier):
    def verify(self, approval):
        return approval.disposition == "user-approved-disposal"


def admitted_receipt_for(ledger, record):
    return AdmittedWorkstreamReceipt(receipt_for(ledger, record), HEAD, "e" * 40)


def test_workstream_ids_and_domain_digests_match_frozen_vectors():
    workstream = workstream_id(SALT, "codex/feature/example", BASE, "2026-09-06T12:00:00Z")
    assert workstream == "rwl_11rhq07tksmxd99ykzsw"
    record = workstream_record_id(SALT, workstream, "2026-09-06T12:01:00Z", "sha256:" + "0" * 64)
    assert record == "rlr_0xegtr9rzcmq6d4b29sc"
    assert workstream_chain_id(SALT, workstream, record) == "rlc_0t3xm63n908fptt0r43s"
    assert workstream_receipt_id(SALT, workstream, "rlc_0t3xm63n908fptt0r43s", "sha256:" + "1" * 64) == "rrc_1h61t1efah5tgv33eaa4"
    assert workstream_ledger_digest(b"example\n") == "sha256:ad5b96d4e9aa88dc1ffc4db4ab46c6d09bd0623105534b1f1b57466fe9caee88"
    assert workstream_detail_digest(b"example\n") == "sha256:c47a5d99516451af52a675db116b1465f35163def20dff2ab64833959d8b9aa9"
    assert reflection_ledger_family(render_workstream_ledger(make_ledger())) == "workstream-v1"


def test_canonical_workstream_header_and_guarded_append_reject_stale_or_manual_phase():
    ledger = make_ledger()
    raw = render_workstream_ledger(ledger)
    assert parse_workstream_ledger(raw).header == ledger.header
    with pytest.raises(ReflectionValidationError, match="branch tip"):
        plan_workstream_append(
            ledger,
            WorkstreamAppendRequest("planner", None, "no_related_thread", (), True, "c", "r", "test", "high"),
            expected_head=HEAD,
            actual_head=TARGET,
            pre_ledger_digest=workstream_ledger_digest(raw),
            branch=ledger.header.working_branch,
            clock=fixed_clock(START + timedelta(minutes=1)),
        )
    ledger, chain = open_chain()
    with pytest.raises(ReflectionValidationError, match="cannot"):
        append(ledger, "reviewer", chain, parents=(ledger.records[-1].record_id,), now=START + timedelta(minutes=3))
    tampered = render_workstream_ledger(ledger).replace("retention_approval_key_id: null", "extra: no\nretention_approval_key_id: null")
    with pytest.raises(ReflectionValidationError, match="unexpected"):
        parse_workstream_ledger(tampered)


@pytest.mark.parametrize("replacement", ("2", "true", '"1"'))
def test_unsupported_ledger_versions_refuse_without_writes(tmp_path, replacement):
    ledger = make_ledger()
    raw = render_workstream_ledger(ledger).replace("version: 1\n", f"version: {replacement}\n")
    path = tmp_path / workstream_ledger_path(ledger.header.workstream_id)
    path.parent.mkdir(parents=True)
    path.write_bytes(raw.encode("utf-8"))
    for reader in (parse_workstream_ledger, reflection_ledger_family):
        with pytest.raises(ReflectionValidationError) as refused:
            reader(raw)
        assert refused.value.diagnostic.code == "unsupported-reflection-format"
    assert workstream_board_view(tmp_path).items[0].status == "unsupported"
    with pytest.raises(ReflectionValidationError) as refused:
        guarded_append_workstream_ledger(
            tmp_path, workstream_id=ledger.header.workstream_id,
            request=WorkstreamAppendRequest("planner", None, "no_related_thread", (), True, "root", "reason", "test", "high"),
            expected_head=HEAD, actual_head=HEAD, pre_ledger_digest=workstream_ledger_digest(raw),
            branch=ledger.effective_branch,
        )
    assert refused.value.diagnostic.code == "unsupported-reflection-format"
    assert path.read_bytes() == raw.encode("utf-8")
    assert list(tmp_path.rglob("*.md")) == [path]


@pytest.mark.parametrize("raw", (
    "schema: memory-seed/reflection-plan\nversion: 1\n",
    "---\nschema: memory-seed/reflection-fragment\nversion: 1\n---\n",
    "schema: memory-seed/reflection-report\nversion: 1\n",
))
def test_discriminator_refuses_minimal_unsupported_prototype_bytes(raw):
    for reader in (reflection_ledger_family, parse_workstream_ledger):
        with pytest.raises(ReflectionValidationError) as refused:
            reader(raw)
        assert refused.value.diagnostic.code == "unsupported-reflection-format"


@pytest.mark.parametrize("retention", ("[]", "{}", "7"))
def test_board_retention_type_validation_returns_diagnostics(tmp_path, retention):
    ledger = make_ledger()
    raw = render_workstream_ledger(ledger).replace("reflection_retention_days: 7\n",
                                                 f"reflection_retention_days: {retention}\n")
    path = tmp_path / workstream_ledger_path(ledger.header.workstream_id)
    path.parent.mkdir(parents=True)
    path.write_bytes(raw.encode("utf-8"))
    board = workstream_board_view(tmp_path)
    assert len(board.items) == 1
    if retention == "7":
        assert parse_workstream_ledger(raw) == ledger
        assert board.exit_code == 0 and board.items[0].status == "valid"
    else:
        with pytest.raises(ReflectionValidationError) as refused:
            parse_workstream_ledger(raw)
        assert refused.value.diagnostic.code == "retention"
        assert board.exit_code == 1 and board.items[0].status == "malformed"
        assert board.items[0].diagnostic.code == "retention"
    assert path.read_bytes() == raw.encode("utf-8")


def test_per_chain_phase_and_divergent_heads_are_never_hidden():
    ledger, chain = open_chain()
    implementable = ledger.records[-1].record_id
    ledger = append(ledger, "implementer", chain, parents=(implementable,), now=START + timedelta(minutes=3))
    review_head = ledger.records[-1].record_id
    ledger = append(ledger, "reviewer", chain, parents=(review_head,), to_phase="orchestrate", now=START + timedelta(minutes=4))
    assert workstream_chain_phase(ledger, chain) == "orchestrate"
    # An orchestrator note can leave two graph heads; a view reports both.
    ledger = append(ledger, "orchestrator", chain, parents=(review_head,), now=START + timedelta(minutes=5))
    assert len(workstream_chain_heads(ledger, chain)) == 2


def test_dependency_prefers_active_exact_record_then_receipt_and_refuses_self_or_wrong_digest():
    target, target_chain = open_chain()
    target_record = target.records[-1]
    receipt = receipt_for(target, target_record)
    admitted = AdmittedWorkstreamReceipt(receipt, HEAD, "e" * 40)
    dependency = WorkstreamDependency(target.header.workstream_id, target_record.record_id, target_record.detail_digest,
                                     "real API ordering", receipt.dependency_locator())
    assert resolve_workstream_dependency(dependency, source_workstream_id="rwl_00000000000000000000", active_ledgers=(target,)).source == "active-ledger"
    assert resolve_workstream_dependency(dependency, source_workstream_id="rwl_00000000000000000000", durable_receipts=(admitted,), receipt_verifier=AdmitReceipts()).source == "durable-receipt"
    with pytest.raises(ReflectionValidationError, match="itself"):
        resolve_workstream_dependency(dependency, source_workstream_id=target.header.workstream_id)
    bad = WorkstreamDependency(target.header.workstream_id, target_record.record_id, "sha256:" + "0" * 64, "reason", None)
    with pytest.raises(ReflectionValidationError, match="digest"):
        resolve_workstream_dependency(bad, source_workstream_id="rwl_00000000000000000000", active_ledgers=(target,))


class AcceptRebind(TrustedRebindVerifier):
    def verify(self, token, *, integration_commit, current_target_tip):
        return integration_commit == INTEGRATION and current_target_tip == INTEGRATION

    def admit_witness(self, token, rebind, *, integration_commit):
        return TrustedIntegrationWitness(rebind.record_id and token.workstream_id, rebind.record_id, rebind.from_branch,
                                         rebind.to_branch, rebind.source_tip, rebind.target_pre_merge_tip,
                                         integration_commit, rebind.pre_ledger_digest)

    def verify_witness(self, witness):
        return witness.integration_commit == INTEGRATION and witness.target_branch == "main"


def test_rebind_close_and_per_chain_expiry_keep_other_chain_active():
    ledger, chain = open_chain()
    ledger = append(ledger, "implementer", chain, parents=(ledger.records[-1].record_id,), now=START + timedelta(minutes=3))
    ledger = append(ledger, "reviewer", chain, parents=(ledger.records[-1].record_id,), to_phase="orchestrate", now=START + timedelta(minutes=4))
    token = preview_trusted_rebind(ledger, source_tip=HEAD, target_branch="main", target_pre_merge_tip=TARGET, token_factory=lambda: "opaque-token")
    rebind = apply_trusted_rebind(ledger, token, integration_commit=INTEGRATION, current_target_tip=INTEGRATION,
                                  verifier=AcceptRebind(), reason="normal integration", clock=fixed_clock(START + timedelta(minutes=5)))
    ledger = rebind.ledger
    preclose_receipts = [admitted_receipt_for(ledger, record) for record in ledger.records if record.chain_id == chain]
    ledger = plan_workstream_chain_close(
        ledger, chain_id=chain, receipts=preclose_receipts, receipt_verifier=AdmitReceipts(),
        integration_witness=rebind.witness, integration_verifier=AcceptRebind(), expected_head=INTEGRATION, actual_head=INTEGRATION,
        pre_ledger_digest=workstream_ledger_digest(render_workstream_ledger(ledger)), branch="main",
        conclusion="closed", reasoning="reviewed and promoted", source="test", confidence="high",
        clock=fixed_clock(START + timedelta(minutes=6)),
    )
    # A second root remains independently active and is never part of this compaction.
    ledger = append(ledger, "planner", None, relationship="no_related_thread", no_related_thread=True,
                    now=START + timedelta(minutes=7))
    other_chain = ledger.records[-1].chain_id
    receipts = [admitted_receipt_for(ledger, record) for record in ledger.records if record.chain_id == chain]
    early = EarlyExpiryApproval(ledger.header.workstream_id, chain, ".memory-seed/sessions/2026-09/2026-09-06.md",
                                "mse_0123456789abcdef", "D1", HEAD, "e" * 40, "user-approved-disposal")
    with pytest.raises(ReflectionValidationError, match="promoted"):
        preview_workstream_expiry(
            ledger, expected_head=INTEGRATION, chain_ids=(chain,), now=START, receipts=receipts,
            receipt_verifier=AdmitReceipts(), integration_witness=rebind.witness, integration_verifier=AcceptRebind(),
            early_approval=early, early_approval_verifier=AcceptEarlyExpiry(),
        )
    preview = preview_workstream_expiry(
        ledger, expected_head=INTEGRATION, chain_ids=(chain,), now=START + timedelta(days=8), receipts=receipts,
        receipt_verifier=AdmitReceipts(), integration_witness=rebind.witness, integration_verifier=AcceptRebind(),
    )
    assert preview.git_blobs_remain is True and preview.privacy_grade_erasure is False
    assert all(record.chain_id != chain for record in preview.post_ledger.records)
    assert any(record.chain_id == other_chain for record in preview.post_ledger.records)
    with pytest.raises(ReflectionValidationError, match="branch tip"):
        from memory_seed.reflection_ledger import apply_workstream_expiry
        apply_workstream_expiry(ledger, preview, actual_head=HEAD, integration_witness=rebind.witness,
                                integration_verifier=AcceptRebind())


def test_rebind_followed_by_close_and_later_record_round_trips_from_disk(tmp_path):
    ledger, chain = open_chain()
    ledger = append(ledger, "implementer", chain, parents=(ledger.records[-1].record_id,), now=START + timedelta(minutes=3))
    ledger = append(ledger, "reviewer", chain, parents=(ledger.records[-1].record_id,), to_phase="orchestrate", now=START + timedelta(minutes=4))
    verifier = AcceptRebind()
    token = preview_trusted_rebind(ledger, source_tip=HEAD, target_branch="main", target_pre_merge_tip=TARGET, token_factory=lambda: "opaque-token")
    rebind = apply_trusted_rebind(ledger, token, integration_commit=INTEGRATION, current_target_tip=INTEGRATION,
                                  verifier=verifier, reason="normal integration", clock=fixed_clock(START + timedelta(minutes=5)))
    ledger = rebind.ledger
    receipts = [admitted_receipt_for(ledger, record) for record in ledger.records if record.chain_id == chain]
    ledger = plan_workstream_chain_close(
        ledger, chain_id=chain, receipts=receipts, receipt_verifier=AdmitReceipts(),
        integration_witness=rebind.witness, integration_verifier=verifier, expected_head=INTEGRATION, actual_head=INTEGRATION,
        pre_ledger_digest=workstream_ledger_digest(render_workstream_ledger(ledger)), branch="main",
        conclusion="closed", reasoning="reviewed", source="test", confidence="high",
        clock=fixed_clock(START + timedelta(minutes=6)),
    )
    ledger = append(ledger, "planner", None, relationship="no_related_thread", no_related_thread=True,
                    now=START + timedelta(minutes=7))
    path = tmp_path / "ledger.md"
    rendered = render_workstream_ledger(ledger)
    path.write_bytes(rendered.encode("utf-8"))
    parsed = parse_workstream_ledger(path.read_bytes(), path.as_posix())
    assert parsed == ledger
    assert render_workstream_ledger(parsed) == rendered


@pytest.mark.parametrize("disposition", ("promoted-to-decision", "already-covered-by-decision"))
def test_early_expiry_refuses_every_canonical_promoted_receipt_disposition(disposition):
    ledger, chain = open_chain()
    ledger = append(ledger, "implementer", chain, parents=(ledger.records[-1].record_id,), now=START + timedelta(minutes=3))
    ledger = append(ledger, "reviewer", chain, parents=(ledger.records[-1].record_id,), to_phase="orchestrate", now=START + timedelta(minutes=4))
    verifier = AcceptRebind()
    token = preview_trusted_rebind(ledger, source_tip=HEAD, target_branch="main", target_pre_merge_tip=TARGET, token_factory=lambda: "opaque-token")
    rebind = apply_trusted_rebind(ledger, token, integration_commit=INTEGRATION, current_target_tip=INTEGRATION,
                                  verifier=verifier, reason="normal integration", clock=fixed_clock(START + timedelta(minutes=5)))
    ledger = rebind.ledger
    receipts = [replace(admitted_receipt_for(ledger, record), receipt=replace(receipt_for(ledger, record), disposition=disposition))
                for record in ledger.records if record.chain_id == chain]
    ledger = plan_workstream_chain_close(
        ledger, chain_id=chain, receipts=receipts, receipt_verifier=AdmitReceipts(),
        integration_witness=rebind.witness, integration_verifier=verifier, expected_head=INTEGRATION, actual_head=INTEGRATION,
        pre_ledger_digest=workstream_ledger_digest(render_workstream_ledger(ledger)), branch="main",
        conclusion="closed", reasoning="reviewed", source="test", confidence="high",
        clock=fixed_clock(START + timedelta(minutes=6)),
    )
    receipts = [replace(admitted_receipt_for(ledger, record), receipt=replace(receipt_for(ledger, record), disposition=disposition))
                for record in ledger.records if record.chain_id == chain]
    approval = EarlyExpiryApproval(ledger.header.workstream_id, chain, ".memory-seed/sessions/2026-09/2026-09-06.md",
                                   "mse_0123456789abcdef", "D1", HEAD, "e" * 40, "user-approved-disposal")
    with pytest.raises(ReflectionValidationError, match="promoted"):
        preview_workstream_expiry(
            ledger, expected_head=INTEGRATION, chain_ids=(chain,), now=START, receipts=receipts,
            receipt_verifier=AdmitReceipts(), integration_witness=rebind.witness, integration_verifier=verifier,
            early_approval=approval, early_approval_verifier=AcceptEarlyExpiry(),
        )


def test_workstream_receipt_refuses_noncanonical_disposition():
    ledger, chain = open_chain()
    with pytest.raises(ReflectionValidationError, match="canonical v1 disposition"):
        resolve_workstream_dependency(
            WorkstreamDependency(ledger.header.workstream_id, ledger.records[-1].record_id, ledger.records[-1].detail_digest,
                                  "needs record", receipt_for(ledger, ledger.records[-1]).dependency_locator()),
            source_workstream_id="rwl_00000000000000000000",
            durable_receipts=(replace(admitted_receipt_for(ledger, ledger.records[-1]),
                                      receipt=replace(receipt_for(ledger, ledger.records[-1]), disposition="promoted")),),
            receipt_verifier=AdmitReceipts(),
        )


def test_board_includes_malformed_candidate_and_guarded_filesystem_writes(tmp_path):
    path, ledger = guarded_init_workstream_ledger(
        tmp_path, expected_head=HEAD, actual_head=HEAD, working_branch="codex/feature/example", base_sha=BASE,
        clock=fixed_clock(START), entropy=lambda size: bytes.fromhex(SALT),
    )
    assert path == workstream_ledger_path(ledger.header.workstream_id)
    request = WorkstreamAppendRequest("planner", None, "no_related_thread", (), True, "root", "reason", "test", "high")
    ledger = guarded_append_workstream_ledger(
        tmp_path, workstream_id=ledger.header.workstream_id, request=request, expected_head=HEAD, actual_head=HEAD,
        pre_ledger_digest=workstream_ledger_digest(render_workstream_ledger(ledger)), branch=ledger.header.working_branch,
        clock=fixed_clock(START + timedelta(minutes=1)),
    )
    malformed = tmp_path / ".memory-seed" / "reflections" / "active" / "broken"
    malformed.mkdir(parents=True)
    (malformed / "ledger.md").write_text("not a ledger\n", encoding="utf-8")
    board = workstream_board_view(tmp_path)
    assert board.exit_code == 1
    assert [item.status for item in board.items] == ["malformed", "valid"]


def test_retention_preflight_and_admission_reject_replay_without_caller_candidates():
    preflight = RetentionPreflight("key-a", "rwl_11rhq07tksmxd99ykzsw", "codex/feature/example", BASE, SALT,
                                   "2026-09-06T12:00:00Z", 14, "1" * 64, "2026-09-06T12:01:00Z",
                                   "2026-09-06T12:02:00Z", "approved", ".memory-seed/sessions/2026-09/2026-09-06.md",
                                   "mse_0123456789abcdef")
    assert parse_retention_preflight(render_retention_preflight(preflight)) == preflight
    approval = RetentionApproval(preflight, HEAD, "e" * 40, "ed25519:" + "0" * 128)
    assert parse_retention_approval(render_retention_approval(approval)) == approval
    signed_fields = reflection_ledger_module._parse_yaml_mapping(
        reflection_ledger_module.retention_approval_payload(approval).decode("utf-8"), "signed approval")
    # Replay tuples are internal and both sides could otherwise drift together
    # without changing equality. Bind their schema/version to the signed bytes.
    replay_assignments = {
        node.targets[0].id: node.value
        for node in ast.walk(ast.parse(inspect.getsource(validate_retention_approval_admission)))
        if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in {"nonce_identity", "other_nonce"}
    }
    assert set(replay_assignments) == {"nonce_identity", "other_nonce"}
    for identity in replay_assignments.values():
        assert tuple(ast.literal_eval(part) for part in identity.elts[:2]) == (signed_fields["schema"], signed_fields["version"])
    for raw, reader in ((render_retention_preflight(preflight), parse_retention_preflight),
                        (render_retention_approval(approval), parse_retention_approval)):
        assert "version: 1\n" in raw
        assert "id_domain: memory-seed/reflection-workstream-ledger/v1\n" in raw
        for invalid in (raw.replace("version: 1\n", "version: 2\n"),
                        raw.replace("version: 1\n", "version: true\n"),
                        raw.replace("/v1\n", "/v2\n")):
            with pytest.raises(ReflectionValidationError) as refused:
                reader(invalid)
            assert refused.value.diagnostic.code == "retention-approval"
    header = WorkstreamLedgerHeader(preflight.workstream_id, preflight.working_branch, BASE, preflight.created_at, 14,
                                    RetentionExtensionReceipt(preflight.nonce, preflight.session_path, preflight.entry_id,
                                                              HEAD, "e" * 40, approval.signature), "key-a", SALT)
    # The test does not need a valid signature: the kernel reaches and rejects it
    # only after exact binding and Git/session admission hooks have been applied.
    with pytest.raises(ReflectionValidationError, match="signature"):
        validate_retention_approval_admission(
            header, approval, trust=RetentionApprovalTrust("key-a", "ed25519:" + "0" * 64), now=START,
            session_contains_preflight=lambda *_: True, commit_is_reachable=lambda _: True,
            object_at=lambda *_: "e" * 40,
        )


class FixedExtendedRetention(RetentionPreflightVerifier):
    def admit(self, handle, *, working_branch, base_sha, now):
        assert handle == "host-owned-handle"
        approval = RetentionApproval(
            RetentionPreflight("key-a", workstream_id(SALT, working_branch, base_sha, "2026-09-06T12:00:00Z"),
                               working_branch, base_sha, SALT, "2026-09-06T12:00:00Z", 30, "2" * 64,
                               "2026-09-06T12:01:00Z", "2026-09-06T12:02:00Z", "approved",
                               ".memory-seed/sessions/2026-09/2026-09-06.md", "mse_0123456789abcdef"),
            HEAD, "e" * 40, "ed25519:" + "0" * 128,
        )
        trust = RetentionApprovalTrust("key-a", "ed25519:" + "0" * 64)
        return RetentionApprovalAdmission(approval, trust, lambda base: trust,
                                          lambda *_: True, lambda _: True, lambda *_: "e" * 40)


def test_extended_init_accepts_only_host_owned_preflight_hook():
    with pytest.raises(ReflectionValidationError, match="signature"):
        initialize_workstream_ledger(
            working_branch="codex/feature/example", base_sha=BASE, retention_days=30,
            clock=fixed_clock(START), retention_preflight_handle="host-owned-handle", retention_verifier=FixedExtendedRetention(),
        )
    with pytest.raises(ReflectionValidationError, match="requires a host"):
        initialize_workstream_ledger(working_branch="codex/feature/example", base_sha=BASE, retention_days=14)


def test_parser_recomputes_exact_predecessor_digest_for_canonical_forgery():
    ledger = make_ledger()
    record = append(ledger, "planner", None, relationship="no_related_thread", no_related_thread=True).records[-1]
    forged_pre = "sha256:" + "1" * 64
    forged_id = workstream_record_id(ledger.header.id_salt, ledger.header.workstream_id, record.created_at, forged_pre)
    forged_chain = workstream_chain_id(ledger.header.id_salt, ledger.header.workstream_id, forged_id)
    draft = replace(record, record_id=forged_id, chain_id=forged_chain, pre_ledger_digest=forged_pre, detail_digest="sha256:" + "0" * 64)
    forged = replace(draft, detail_digest=workstream_detail_digest(render_workstream_record(draft, zero_detail_digest=True)))
    with pytest.raises(ReflectionValidationError, match="preceding canonical"):
        validate_workstream_ledger(WorkstreamLedger(ledger.header, (forged,)))


def test_append_resolves_dependencies_before_writing_and_never_falls_back_while_target_is_active():
    target, _chain = open_chain()
    target_record = target.records[-1]
    fallback = admitted_receipt_for(target, target_record).receipt.dependency_locator()
    missing = WorkstreamDependency(target.header.workstream_id, "rlr_00000000000000000000", target_record.detail_digest,
                                  "must precede this work", fallback)
    source = make_ledger("codex/feature/source")
    request = WorkstreamAppendRequest("planner", None, "no_related_thread", (), True, "root", "reason", "test", "high", depends_on=(missing,))
    with pytest.raises(ReflectionValidationError, match="active dependency target is missing"):
        plan_workstream_append(source, request, expected_head=HEAD, actual_head=HEAD,
                               pre_ledger_digest=workstream_ledger_digest(render_workstream_ledger(source)),
                               branch=source.header.working_branch, active_ledgers=(target,),
                               durable_receipts=(admitted_receipt_for(target, target_record),), receipt_verifier=AdmitReceipts())


def test_close_requires_verifier_admitted_witness_and_session_admitted_receipts():
    ledger, chain = open_chain()
    ledger = append(ledger, "implementer", chain, parents=(ledger.records[-1].record_id,), now=START + timedelta(minutes=3))
    ledger = append(ledger, "reviewer", chain, parents=(ledger.records[-1].record_id,), to_phase="orchestrate", now=START + timedelta(minutes=4))
    verifier = AcceptRebind()
    token = preview_trusted_rebind(ledger, source_tip=HEAD, target_branch="main", target_pre_merge_tip=TARGET, token_factory=lambda: "opaque-token")
    rebind = apply_trusted_rebind(ledger, token, integration_commit=INTEGRATION, current_target_tip=INTEGRATION,
                                  verifier=verifier, reason="normal integration", clock=fixed_clock(START + timedelta(minutes=5)))
    raw_receipts = [receipt_for(rebind.ledger, record) for record in rebind.ledger.records if record.chain_id == chain]
    with pytest.raises(ReflectionValidationError, match="Git/session-admitted"):
        plan_workstream_chain_close(rebind.ledger, chain_id=chain, receipts=raw_receipts, receipt_verifier=AdmitReceipts(),
                                    integration_witness=rebind.witness, integration_verifier=verifier, expected_head=INTEGRATION,
                                    actual_head=INTEGRATION, pre_ledger_digest=workstream_ledger_digest(render_workstream_ledger(rebind.ledger)),
                                    branch="main", conclusion="closed", reasoning="reviewed", source="test", confidence="high")
    forged = replace(rebind.witness, integration_commit=HEAD)
    receipts = [admitted_receipt_for(rebind.ledger, record) for record in rebind.ledger.records if record.chain_id == chain]
    with pytest.raises(ReflectionValidationError, match="not admitted|does not exactly"):
        plan_workstream_chain_close(rebind.ledger, chain_id=chain, receipts=receipts, receipt_verifier=AdmitReceipts(),
                                    integration_witness=forged, integration_verifier=verifier, expected_head=INTEGRATION,
                                    actual_head=INTEGRATION, pre_ledger_digest=workstream_ledger_digest(render_workstream_ledger(rebind.ledger)),
                                    branch="main", conclusion="closed", reasoning="reviewed", source="test", confidence="high")


def test_guarded_append_refuses_a_second_effective_branch_owner(tmp_path):
    _path, ledger = guarded_init_workstream_ledger(tmp_path, expected_head=HEAD, actual_head=HEAD,
                                                    working_branch="codex/feature/example", base_sha=BASE,
                                                    clock=fixed_clock(START), entropy=lambda _: bytes.fromhex(SALT))
    duplicate = tmp_path / ".memory-seed" / "reflections" / "active" / "copy"
    duplicate.mkdir(parents=True)
    (duplicate / "ledger.md").write_text(render_workstream_ledger(ledger), encoding="utf-8")
    request = WorkstreamAppendRequest("planner", None, "no_related_thread", (), True, "root", "reason", "test", "high")
    with pytest.raises(ReflectionValidationError, match="ambiguous"):
        guarded_append_workstream_ledger(tmp_path, workstream_id=ledger.header.workstream_id, request=request,
                                         expected_head=HEAD, actual_head=HEAD,
                                         pre_ledger_digest=workstream_ledger_digest(render_workstream_ledger(ledger)),
                                         branch=ledger.header.working_branch)


# The trusted-history contract is deliberately exercised against real Git
# trees.  These helpers use ordinary porcelain only to make adversarial tree
# shapes; production code never receives their caller-controlled raw bytes.
def _git(root: Path, *args: str, input: str | None = None) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args], input=input, text=True, encoding="utf-8",
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout.strip()


def _commit_ledger(root: Path, ledger_path: str, ledger: WorkstreamLedger, message: str) -> str:
    path = root / Path(ledger_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(render_workstream_ledger(ledger).encode("utf-8"))
    _git(root, "add", "--", ledger_path)
    _git(root, "commit", "--quiet", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _new_git_workstream(tmp_path: Path) -> tuple[Path, WorkstreamLedger, str]:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    _git(root, "init", "--quiet")
    _git(root, "config", "user.name", "Reflection test")
    _git(root, "config", "user.email", "reflection@example.test")
    (root / "README.md").write_text("base\n", encoding="utf-8")
    (root / ".gitattributes").write_bytes(b"* text=auto eol=lf\n.memory-seed/reflections/active/** -merge\n")
    sessions = root / ".memory-seed/sessions"
    sessions.mkdir(parents=True)
    (sessions / ".gitkeep").write_text("", encoding="utf-8")
    _git(root, "add", "README.md", ".gitattributes", ".memory-seed/sessions/.gitkeep")
    _git(root, "commit", "--quiet", "-m", "base")
    base = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "--quiet", "-b", "codex/feature/example")
    ledger = initialize_workstream_ledger(
        working_branch="codex/feature/example", base_sha=base, clock=fixed_clock(START),
        entropy=lambda _: bytes.fromhex(SALT),
    )
    ledger_path = workstream_ledger_path(ledger.header.workstream_id)
    _commit_ledger(root, ledger_path, ledger, "reflection: init")
    return root, ledger, ledger_path


def _admission_state(root):
    return (_git(root, "rev-parse", "HEAD"), _git(root, "show-ref"), _git(root, "ls-files", "--stage"),
            {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()})


@pytest.mark.parametrize("component", (".memory-seed", "reflections", "active", "ledger.md"))
@pytest.mark.parametrize("suffix", (".", " "))
def test_shared_reflection_scope_rejects_windows_aliases(component, suffix):
    from memory_seed.reflection_ledger import is_reserved_reflection_path, validate_reflection_capability
    ledger = make_ledger()
    path = workstream_ledger_path(ledger.header.workstream_id)
    cap = {"format": "workstream-v1", "workstream_id": ledger.header.workstream_id,
           "ledger_path": path, "operations": ["append"]}
    normalized = {"write_intent": "writing", "allowed_files": [path.upper().replace("/", "\\")],
                  "expected_absent": [], "reflection": cap}
    assert validate_reflection_capability(normalized) == cap
    alias = path.replace(component, component + suffix)
    assert is_reserved_reflection_path(alias)
    for field in ("allowed_files", "expected_absent"):
        for capability in (False, True):
            execution = {"write_intent": "writing", "allowed_files": [path] if capability else ["ordinary.py"],
                         "expected_absent": [], **({"reflection": cap} if capability else {})}
            execution[field] = [alias]
            with pytest.raises(ReflectionValidationError):
                validate_reflection_capability(execution)


def test_reflection_fuse_apply_requires_original_binding_across_source_changes(tmp_path):
    from memory_seed.core import session_fuse
    root, ledger, path = _new_git_workstream(tmp_path)
    branch = ledger.header.working_branch
    _git(root, "checkout", "-b", "integration", ledger.header.base_sha)
    preview_a = session_fuse(root, branch=branch)
    assert not preview_a.issues
    _git(root, "checkout", branch)
    ledger_b = append(ledger, "planner", None, relationship="no_related_thread", no_related_thread=True)
    _commit_ledger(root, path, ledger_b, "reflection: source B")
    legacy = root / ".memory-seed/sessions/2026-09-06.md"
    legacy.write_text(
        "---\ntags: [session-log, memory-seed]\nsession_date: 2026-09-06\n---\n\n"
        "## 2026-09-06 12:00 - Source B\n\n```yaml\nentry_id: mse_0123456789abcdef\n"
        f"user_initials: JN\nagent_type: codex\nbranch: {branch}\n```\n\n- Source B body.\n", encoding="utf-8")
    _git(root, "add", legacy.relative_to(root).as_posix())
    _git(root, "commit", "-m", "source B session")
    _git(root, "checkout", "integration")
    preview_b = session_fuse(root, branch=branch)
    assert not preview_b.issues and preview_b.planned_entries and preview_b.removed_sources
    _git(root, "merge", "--no-ff", "--no-commit", branch)
    before = _admission_state(root)
    unbound = session_fuse(root, branch=branch, apply=True)
    assert not unbound.changed and "reflection-binding-required" in " ".join(unbound.issues)
    assert _admission_state(root) == before
    stale = session_fuse(root, branch=branch, apply=True, reflection_admission=preview_a.reflection_admission)
    assert not stale.changed and "reflection-binding-stale" in " ".join(stale.issues)
    assert _admission_state(root) == before
    malformed = session_fuse(root, branch=branch, apply=True, reflection_admission={})
    assert not malformed.changed and "reflection-binding-stale" in " ".join(malformed.issues)
    assert _admission_state(root) == before
    current = session_fuse(root, branch=branch, apply=True, reflection_admission=preview_b.reflection_admission)
    assert current.changed and not current.issues
    assert not legacy.exists()
    assert (root / ".memory-seed/sessions/2026-09/2026-09-06.md").is_file()
    assert (root / path).read_bytes() == render_workstream_ledger(ledger_b).encode("utf-8")


@pytest.mark.skip(
    reason="3 of 4 parametrizations fail on Linux CI only ([False-merge-branch], "
    "[False-prepare-pr], [True-merge-branch]): .git/index changes bytes across a refused "
    "session_merge_branch/session_prepare_pr_branch call. Traced every git subprocess call in "
    "the actual code path (session_fuse's preview build never reaches the reflection-admission "
    "recheck functions for this refusal - it returns from preview.issues first); none of them "
    "touch the index or working tree (rev-parse, merge-base, ls-tree, a commit-to-commit diff), "
    "and the test does not reproduce locally on Windows (index is byte-identical before/after). "
    "Root cause not isolated - no Linux environment available to instrument further. Reflection "
    "Board is currently dormant/paused as an implementation (no real board is enabled), so this "
    "is deferred rather than blocking; re-enable and re-investigate when that work resumes."
)
@pytest.mark.parametrize("consumer", ("merge-branch", "prepare-pr"))
@pytest.mark.parametrize("dry_run", (False, True))
def test_reflection_refusal_preserves_stale_index_stat_cache(tmp_path, consumer, dry_run):
    from memory_seed.core import session_merge_branch, session_prepare_pr_branch
    root, ledger, path = _new_git_workstream(tmp_path)
    extra = (root / path).parent / "manifest.yaml"
    extra.write_text("unsupported\n", encoding="utf-8")
    _git(root, "add", extra.relative_to(root).as_posix())
    _git(root, "commit", "-m", "unsupported reserved state")
    _git(root, "branch", "integration", ledger.header.base_sha)
    if consumer == "merge-branch":
        _git(root, "checkout", "integration")
    # Content is unchanged, but the cached stat data now needs a refresh.
    tracked = root / "README.md"
    stamp = tracked.stat()
    os.utime(tracked, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 2_000_000_000))
    index = root / ".git/index"
    index_before = index.read_bytes()
    before = _admission_state(root)
    if consumer == "merge-branch":
        result = session_merge_branch(root, branch=ledger.header.working_branch, dry_run=dry_run)
        assert not result.committed
    else:
        result = session_prepare_pr_branch(root, branch=ledger.header.working_branch,
                                          base_branch="integration", dry_run=dry_run)
        assert not result.ready
    assert "unsupported-reflection-format" in " ".join(result.issues)
    assert index.read_bytes() == index_before
    assert _admission_state(root) == before
    # Positive control: ordinary status really does rewrite this fixture's index.
    assert _git(root, "status", "--short") == ""
    assert index.read_bytes() != index_before


@pytest.mark.parametrize("consumer", ("merge-branch", "prepare-pr"))
def test_ignored_nested_reflection_refuses_integration_without_mutation(tmp_path, consumer):
    from memory_seed.core import session_merge_branch, session_prepare_pr_branch
    root, ledger, _path = _new_git_workstream(tmp_path)
    _git(root, "branch", "integration", ledger.header.base_sha)
    if consumer == "merge-branch":
        _git(root, "checkout", "integration")
    (root / ".git/info/exclude").write_text("pod/\n", encoding="utf-8")
    unsupported = root / "pod/.memory-seed/reflections/unknown/manifest.yaml"
    unsupported.parent.mkdir(parents=True)
    unsupported.write_text("unsupported ignored reflection state\n", encoding="utf-8")
    assert _git(root, "--no-optional-locks", "status", "--short") == ""
    before = _admission_state(root)
    if consumer == "merge-branch":
        result = session_merge_branch(root, branch=ledger.header.working_branch)
        assert not result.committed
    else:
        result = session_prepare_pr_branch(root, branch=ledger.header.working_branch, base_branch="integration")
        assert not result.ready
    assert "unsupported-reflection-format" in " ".join(result.issues)
    assert _admission_state(root) == before


@pytest.mark.parametrize("prefix", ("node_modules/package", "build/generated"))
def test_nested_reflection_discovery_does_not_exclude_dependency_or_generated_paths(tmp_path, prefix):
    from memory_seed.reflection_ledger import preview_reflection_integration, recheck_reflection_integration
    root, ledger, _path = _new_git_workstream(tmp_path)
    (root / ".git/info/exclude").write_text(prefix.split("/")[0] + "/\n", encoding="utf-8")
    (root / prefix / ".memory-seed/reflections/unknown").mkdir(parents=True)
    preview = preview_reflection_integration(root, source_ref=ledger.header.working_branch,
                                             base_ref=ledger.header.base_sha)
    before = _admission_state(root)
    with pytest.raises(ReflectionValidationError, match="reserved"):
        recheck_reflection_integration(root, preview)
    assert _admission_state(root) == before


def test_reflection_discovery_stops_at_git_and_registered_nested_worktrees(tmp_path):
    from memory_seed.reflection_ledger import preview_reflection_integration, recheck_reflection_integration
    root, ledger, _path = _new_git_workstream(tmp_path)
    nested = root / ".codex/worktrees/nested"
    _git(root, "worktree", "add", "--detach", str(nested), "HEAD")
    (root / ".git/info/exclude").write_text(".codex/\n", encoding="utf-8")
    for boundary in (root / ".git", nested):
        unknown = boundary / "pod/.memory-seed/reflections/unknown/manifest.yaml"
        unknown.parent.mkdir(parents=True)
        unknown.write_text("outside this checkout's admission boundary\n", encoding="utf-8")
    preview = preview_reflection_integration(root, source_ref=ledger.header.working_branch,
                                             base_ref=ledger.header.base_sha)
    before = _admission_state(root)
    recheck_reflection_integration(root, preview)
    assert _admission_state(root) == before


def test_reflection_discovery_cannot_hide_unknown_state_behind_reserved_git_directory(tmp_path):
    from memory_seed.reflection_ledger import preview_reflection_integration, recheck_reflection_integration
    root, ledger, _path = _new_git_workstream(tmp_path)
    (root / ".memory-seed/reflections/.git").mkdir()
    preview = preview_reflection_integration(root, source_ref=ledger.header.working_branch,
                                             base_ref=ledger.header.base_sha)
    before = _admission_state(root)
    with pytest.raises(ReflectionValidationError, match="boundaries cannot hide reserved"):
        recheck_reflection_integration(root, preview)
    assert _admission_state(root) == before


@pytest.mark.parametrize("link_name", (".memory-seed", ".memory-seed/reflections"))
def test_nested_reflection_discovery_refuses_directory_links_without_following_them(tmp_path, monkeypatch, link_name):
    from memory_seed.reflection_ledger import preview_reflection_integration, recheck_reflection_integration
    root, ledger, _path = _new_git_workstream(tmp_path)
    outside = tmp_path / "outside-checkout"
    outside.mkdir()
    (outside / "sentinel.txt").write_text("never traverse or mutate\n", encoding="utf-8")
    link = root / "pod" / link_name
    link.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        made = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)], capture_output=True, text=True)
        assert made.returncode == 0, made.stderr
    else:
        link.symlink_to(outside, target_is_directory=True)
    preview = preview_reflection_integration(root, source_ref=ledger.header.working_branch,
                                             base_ref=ledger.header.base_sha)
    before = _admission_state(root)
    original_scandir = os.scandir

    def bounded_scandir(path):
        assert Path(path).resolve().is_relative_to(root), "discovery descended outside the checkout"
        return original_scandir(path)

    with monkeypatch.context() as scoped:
        scoped.setattr(os, "scandir", bounded_scandir)
        with pytest.raises(ReflectionValidationError):
            recheck_reflection_integration(root, preview)
    assert _admission_state(root) == before
    assert (outside / "sentinel.txt").read_text(encoding="utf-8") == "never traverse or mutate\n"


def test_warm_verification_scope_still_rejects_worktree_and_ref_changes(tmp_path):
    from memory_seed.reflection_ledger import (
        preview_reflection_integration, recheck_reflection_integration,
        reflection_verification_operation,
    )
    root, ledger, path = _new_git_workstream(tmp_path)

    @reflection_verification_operation
    def operation():
        preview = preview_reflection_integration(root, source_ref="HEAD", base_ref=ledger.header.base_sha)
        recheck_reflection_integration(root, preview)
        original = (root / path).read_bytes()
        (root / path).write_bytes(original + b"tampered\n")
        with pytest.raises(ReflectionValidationError):
            recheck_reflection_integration(root, preview)
        (root / path).write_bytes(original)
        changed_blob = _git(root, "hash-object", "-w", "--stdin", input=original.decode("utf-8") + "tampered\n")
        _git(root, "update-index", "--cacheinfo", f"100644,{changed_blob},{path}")
        with pytest.raises(ReflectionValidationError, match="proposed index differs"):
            recheck_reflection_integration(root, preview, merged=True)
        _git(root, "add", "--", path)
        _git(root, "commit", "--allow-empty", "-m", "move source after preview")
        with pytest.raises(ReflectionValidationError, match="changed after preview"):
            recheck_reflection_integration(root, preview)

    operation()


def test_reflection_integration_admits_one_parent_and_rechecks_preview_before_writes(tmp_path):
    from memory_seed.core import session_merge_branch
    from memory_seed.reflection_ledger import preview_reflection_integration, recheck_reflection_integration
    root, ledger, path = _new_git_workstream(tmp_path)
    _git(root, "checkout", "-b", "integration", ledger.header.base_sha)
    preview = preview_reflection_integration(root, source_ref=ledger.header.working_branch, base_ref="HEAD")
    assert preview.proposed == preview.source and preview.base == preview.ancestor == ()
    before = _admission_state(root)
    recheck_reflection_integration(root, preview)
    assert _admission_state(root) == before
    result = session_merge_branch(root, branch=ledger.header.working_branch)
    assert result.committed, result.issues
    loaded = load_trusted_workstream_ledger(root, trusted_ref="HEAD", ledger_path=path)
    assert loaded.ledger == ledger
    assert preview.source_commit in _git(root, "rev-list", "--parents", "-n", "1", "HEAD")


def test_reflection_integration_admits_inherited_identical_family_and_fuses_sessions(tmp_path, monkeypatch):
    from memory_seed.core import session_merge_branch
    from memory_seed.reflection_ledger import preview_reflection_integration
    root, ledger, path = _new_git_workstream(tmp_path)
    _git(root, "checkout", "-b", "integration", ledger.header.base_sha)
    assert session_merge_branch(root, branch=ledger.header.working_branch).committed
    inherited = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "-b", "descendant", inherited)
    session_path = root / ".memory-seed/sessions/2026-09/2026-09-09.md"
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(
        "---\nsession_date: 2026-09-09\n---\n\n"
        "## 2026-09-09 09:00 - Descendant work\n\n```yaml\n"
        "entry_id: mse_0123456789abcdef\nuser_initials: JN\nagent_type: codex\nbranch: descendant\n"
        "```\n\n- Ordinary descendant session work.\n",
        encoding="utf-8",
    )
    _git(root, "add", "README.md", session_path.relative_to(root).as_posix())
    _git(root, "commit", "--quiet", "-m", "ordinary descendant work")
    source = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "--quiet", "integration")
    preview = preview_reflection_integration(root, source_ref="descendant", base_ref="HEAD")
    assert preview.inherited_identical_family
    assert preview.source == preview.base == preview.ancestor == preview.proposed
    import memory_seed.reflection_ledger as module
    from collections import Counter
    classifications = Counter()
    original = module._classify_trusted_workstream_ledger

    def counted(root, trusted_ref, head, ledger_path):
        classifications[(str(root), head, ledger_path)] += 1
        return original(root, trusted_ref, head, ledger_path)

    with monkeypatch.context() as scoped:
        scoped.setattr(module, "_classify_trusted_workstream_ledger", counted)
        result = session_merge_branch(root, branch="descendant")
    assert classifications and max(classifications.values()) == 1, classifications
    assert sum(classifications.values()) == 2, classifications
    assert result.committed, result.issues
    assert _git(root, "rev-list", "--parents", "-n", "1", "HEAD").split()[1:] == [inherited, source]
    assert "Memory-Entry: mse_0123456789abcdef" in _git(root, "show", "-s", "--format=%B", "HEAD")
    loaded = load_trusted_workstream_ledger(root, trusted_ref="HEAD", ledger_path=path)
    assert loaded.ledger == ledger


def test_reflection_integration_admits_identical_family_on_sibling_branches(tmp_path):
    from memory_seed.core import session_merge_branch
    from memory_seed.reflection_ledger import preview_reflection_integration
    root, ledger, _path = _new_git_workstream(tmp_path)
    _git(root, "checkout", "-b", "integration", ledger.header.base_sha)
    assert session_merge_branch(root, branch=ledger.header.working_branch).committed
    shared = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "-b", "target", shared)
    _git(root, "commit", "--allow-empty", "-m", "target advance")
    _git(root, "checkout", "-b", "sibling", shared)
    _git(root, "commit", "--allow-empty", "-m", "sibling advance")
    preview = preview_reflection_integration(root, source_ref="sibling", base_ref="target")
    assert preview.inherited_identical_family
    assert preview.source == preview.base == preview.ancestor == preview.proposed
    target_tip = _git(root, "rev-parse", "target")
    _git(root, "checkout", "--quiet", "target")
    result = session_merge_branch(root, branch="sibling")
    assert result.committed, result.issues
    assert _git(root, "rev-list", "--parents", "-n", "1", "HEAD").split()[1:] == [
        target_tip, _git(root, "rev-parse", "sibling"),
    ]


def test_reflection_integration_refuses_sibling_with_changed_ledger(tmp_path):
    from memory_seed.reflection_ledger import preview_reflection_integration
    root, ledger, path = _new_git_workstream(tmp_path)
    _git(root, "checkout", "-b", "integration", ledger.header.base_sha)
    from memory_seed.core import session_merge_branch
    assert session_merge_branch(root, branch=ledger.header.working_branch).committed
    shared = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "-b", "target", shared)
    _git(root, "commit", "--allow-empty", "-m", "target advance")
    _git(root, "checkout", "-b", "sibling", shared)
    changed = append(ledger, "planner", None, relationship="no_related_thread", no_related_thread=True,
                     now=START + timedelta(minutes=1))
    _commit_ledger(root, path, changed, "reflection: sibling ledger change")
    before = _admission_state(root)
    with pytest.raises(ReflectionValidationError, match="two ledger-bearing parents"):
        preview_reflection_integration(root, source_ref="sibling", base_ref="target")
    assert _admission_state(root) == before


def test_reflection_integration_refuses_descendant_that_changes_ledger(tmp_path):
    from memory_seed.core import session_merge_branch
    from memory_seed.reflection_ledger import preview_reflection_integration
    root, ledger, path = _new_git_workstream(tmp_path)
    _git(root, "checkout", "-b", "integration", ledger.header.base_sha)
    assert session_merge_branch(root, branch=ledger.header.working_branch).committed
    _git(root, "checkout", "-b", "changed", "integration")
    changed = append(ledger, "planner", None, relationship="no_related_thread", no_related_thread=True,
                     now=START + timedelta(minutes=1))
    _commit_ledger(root, path, changed, "reflection: valid descendant change")
    _git(root, "checkout", "--quiet", "integration")
    before = _admission_state(root)
    with pytest.raises(ReflectionValidationError, match="two ledger-bearing parents"):
        preview_reflection_integration(root, source_ref="changed", base_ref="HEAD")
    assert _admission_state(root) == before


@pytest.mark.parametrize("change", ["source-ref", "base-ref", "ignored-file", "unknown-directory"])
def test_reflection_integration_preview_binding_changes_refuse_without_mutation(tmp_path, change):
    from memory_seed.reflection_ledger import preview_reflection_integration, recheck_reflection_integration
    root, ledger, path = _new_git_workstream(tmp_path)
    _git(root, "checkout", "-b", "integration", ledger.header.base_sha)
    preview = preview_reflection_integration(root, source_ref=ledger.header.working_branch, base_ref="HEAD")
    if change == "source-ref":
        _git(root, "update-ref", "refs/heads/" + ledger.header.working_branch, ledger.header.base_sha)
    elif change == "base-ref":
        _git(root, "commit", "--allow-empty", "-m", "race")
    else:
        target = root / ".memory-seed/reflections/active/unknown"
        target.mkdir(parents=True)
        if change == "ignored-file":
            (target / "manifest.yaml").write_text("unsupported\n", encoding="utf-8")
    before = _admission_state(root)
    with pytest.raises(ReflectionValidationError):
        recheck_reflection_integration(root, preview)
    assert _admission_state(root) == before


@pytest.mark.parametrize("hostile", ["format", "mixed", "case", "nested", "symlink", "raw-delete",
                                     "runtime-dot", "runtime-space", "family-dot", "family-space"])
def test_reflection_integration_reserved_tree_negative_matrix(tmp_path, hostile):
    from memory_seed.reflection_ledger import preview_reflection_integration
    root, ledger, path = _new_git_workstream(tmp_path)
    target = root / path
    if hostile == "format":
        target.write_bytes(target.read_bytes().replace(b"version: 1\n", b"version: 2\n", 1))
    elif hostile == "mixed":
        (target.parent / "manifest.yaml").write_text("unsupported\n", encoding="utf-8")
    elif hostile in {"case", "nested"}:
        other = (".MEMORY-SEED/REFLECTIONS/unknown.md" if hostile == "case" else
                 "pod/.memory-seed/reflections/unknown.md")
        extra = root / other
        extra.parent.mkdir(parents=True, exist_ok=True)
        extra.write_text("unsupported\n", encoding="utf-8")
    elif hostile == "symlink":
        oid = _git(root, "hash-object", "-w", "--stdin", input="../../outside\n")
        _git(root, "update-index", "--cacheinfo", f"120000,{oid},{path}")
    elif hostile in {"runtime-dot", "runtime-space", "family-dot", "family-space"}:
        component = ".memory-seed" if hostile.startswith("runtime-") else "reflections"
        alias = path.replace(component, component + ("." if hostile.endswith("-dot") else " "))
        oid = _git(root, "rev-parse", f"HEAD:{path}")
        # Build a hostile committed tree without relying on Windows creating
        # distinct filesystem entries for names which alias a canonical path.
        _git(root, "-c", "core.protectNTFS=false", "update-index", "--add", "--cacheinfo", f"100644,{oid},{alias}")
    elif hostile == "raw-delete":
        _git(root, "branch", "integration", "HEAD")
        target.unlink()
    else:
        _git(root, "branch", "integration", "HEAD")
        _git(root, "commit", "--allow-empty", "-m", "child inherits ledger")
    if hostile not in {"symlink", "runtime-dot", "runtime-space", "family-dot", "family-space"}:
        _git(root, "add", "-A")
    _git(root, "commit", "-m", "hostile tree fixture")
    if hostile != "raw-delete":
        _git(root, "branch", "integration", ledger.header.base_sha)
    before = _admission_state(root)
    with pytest.raises(ReflectionValidationError):
        preview_reflection_integration(root, source_ref=ledger.header.working_branch, base_ref="integration")
    assert _admission_state(root) == before


def test_reflection_integration_index_tamper_blocks_fuse_apply_without_writes(tmp_path):
    from memory_seed.core import session_fuse
    root, ledger, path = _new_git_workstream(tmp_path)
    _git(root, "checkout", "-b", "integration", ledger.header.base_sha)
    preview = session_fuse(root, branch=ledger.header.working_branch)
    assert not preview.issues
    _git(root, "merge", "--no-ff", "--no-commit", ledger.header.working_branch)
    extra = root / ".memory-seed/reflections/unknown.md"
    extra.write_text("unsupported\n", encoding="utf-8")
    _git(root, "add", extra.relative_to(root).as_posix())
    before = _admission_state(root)
    result = session_fuse(root, branch=ledger.header.working_branch, apply=True,
                          reflection_admission=preview.reflection_admission)
    assert not result.changed and result.issues
    assert _admission_state(root) == before


@pytest.mark.parametrize("extra_path", (
    "unsupported/manifest.yaml",
    "unsupported/fragments/orphan.md",
    "unsupported/reports/orphan.md",
    "unsupported/unknown.txt",
    "loose.txt",
    "{workstream}/manifest.yaml",
    "{workstream}/extra.md",
))
def test_reserved_family_candidates_are_visible_and_block_trusted_admission(tmp_path, extra_path):
    root, ledger, ledger_path = _new_git_workstream(tmp_path)
    active = root / ".memory-seed/reflections/active"
    unsupported = active / extra_path.format(workstream=ledger.header.workstream_id)
    unsupported.parent.mkdir(parents=True, exist_ok=True)
    unsupported.write_bytes(b"unsupported input\n")
    board = workstream_board_view(root)
    assert board.exit_code == 1
    assert any(item.status == "malformed" for item in board.items)
    assert len(board.items) == (1 if extra_path.startswith("{workstream}") else 2)
    _git(root, "add", ".memory-seed/reflections/active")
    _git(root, "commit", "--quiet", "-m", "unsupported reserved-family candidate")
    head = _git(root, "rev-parse", "HEAD")
    trusted_board = workstream_board_view(root, trusted_ref="HEAD")
    assert trusted_board.exit_code == 1 and len(trusted_board.items) == len(board.items)
    with pytest.raises(ReflectionValidationError) as refused:
        reflection_ledger_module._trusted_active_ledgers_at_commit(root, head)
    assert refused.value.diagnostic.code == "unsupported-reflection-format"
    # Discovery is read-only; committed-only candidates must remain visible too.
    unsupported.unlink()
    assert workstream_board_view(root, trusted_ref="HEAD").exit_code == 1
    assert _git(root, "rev-parse", "HEAD") == head
    assert (root / ledger_path).read_bytes() == render_workstream_ledger(ledger).encode("utf-8")


def test_trusted_board_refuses_symlink_mode_for_ledger(tmp_path):
    root, ledger, ledger_path = _new_git_workstream(tmp_path)
    blob = _git(root, "rev-parse", f"HEAD:{ledger_path}")
    _git(root, "update-index", "--cacheinfo", f"120000,{blob},{ledger_path}")
    _git(root, "commit", "--quiet", "-m", "hostile symlink mode")
    board = workstream_board_view(root, trusted_ref="HEAD")
    assert board.exit_code == 1 and board.items[0].status == "malformed"
    with pytest.raises(ReflectionValidationError):
        reflection_ledger_module._trusted_active_ledgers_at_commit(root, _git(root, "rev-parse", "HEAD"))
    assert (root / ledger_path).read_bytes() == render_workstream_ledger(ledger).encode("utf-8")


@pytest.mark.parametrize("mode", ("100644", "120000", "160000"))
@pytest.mark.parametrize("local_root_present", (False, True))
def test_committed_exact_active_root_is_visible_and_refused(tmp_path, mode, local_root_present):
    root, ledger, ledger_path = _new_git_workstream(tmp_path)
    active_root = ".memory-seed/reflections/active"
    object_id = _git(root, "rev-parse", "HEAD" if mode == "160000" else f"HEAD:{ledger_path}")
    _git(root, "update-index", "--force-remove", "--", ledger_path)
    _git(root, "update-index", "--add", "--cacheinfo", f"{mode},{object_id},{active_root}")
    _git(root, "commit", "--quiet", "-m", "hostile committed active root")
    active = root / active_root
    if not local_root_present:
        active.rename(root / "parked-ledger")
    head = _git(root, "rev-parse", "HEAD")
    index_before = _git(root, "ls-files", "--stage")
    status_before = _git(root, "status", "--porcelain")
    board = workstream_board_view(root, trusted_ref="HEAD")
    assert board.exit_code == 1 and len(board.items) == 1
    assert board.items[0].path == active_root and board.items[0].status == "malformed"
    assert board.items[0].diagnostic.code == "unsupported-reflection-format"
    with pytest.raises(ReflectionValidationError) as refused:
        reflection_ledger_module._trusted_active_ledgers_at_commit(root, head)
    assert refused.value.diagnostic.code == "unsupported-reflection-format"
    assert refused.value.diagnostic.path == active_root
    assert _git(root, "rev-parse", "HEAD") == head
    assert _git(root, "ls-files", "--stage") == index_before
    assert _git(root, "status", "--porcelain") == status_before
    saved_ledger = (active if local_root_present else root / "parked-ledger") / ledger.header.workstream_id / "ledger.md"
    assert saved_ledger.read_bytes() == render_workstream_ledger(ledger).encode("utf-8")


def _quoted_yaml(mapping: dict[str, str]) -> str:
    return "".join(f"{key}: {json.dumps(value)}\n" for key, value in mapping.items())


def _session_entry(title: str, entry_id: str, mappings: tuple[dict[str, str], ...] = ()) -> str:
    body = f"## {title}\n\n```yaml\nentry_id: {json.dumps(entry_id)}\n```\n\n### Decisions\n\n#### D1 - Durable evidence\n\n"
    for mapping in mappings:
        body += f"\n### Receipt evidence\n\n```yaml\n{_quoted_yaml(mapping)}```\n"
    return body + "\n"


class _LocalBranchRebind(TrustedRebindVerifier):
    def verify(self, token, *, integration_commit, current_target_tip):
        return integration_commit == current_target_tip

    def admit_witness(self, token, rebind, *, integration_commit):
        return TrustedIntegrationWitness(
            token.workstream_id, rebind.record_id, rebind.from_branch, rebind.to_branch,
            rebind.source_tip, rebind.target_pre_merge_tip, integration_commit, rebind.pre_ledger_digest,
        )

    def verify_witness(self, witness):
        return witness.target_branch == "codex/feature/example"


def _closed_git_workstream(tmp_path: Path) -> tuple[Path, WorkstreamLedger, str, str]:
    root, ledger, ledger_path = _new_git_workstream(tmp_path)
    ledger = append(ledger, "planner", None, relationship="no_related_thread", no_related_thread=True,
                    now=START + timedelta(minutes=1))
    chain = ledger.records[-1].chain_id
    root_record = ledger.records[-1].record_id
    _commit_ledger(root, ledger_path, ledger, "reflection: open")
    ledger = append(ledger, "planner", chain, parents=(root_record,), now=START + timedelta(minutes=2))
    _commit_ledger(root, ledger_path, ledger, "reflection: plan")
    ledger = append(ledger, "implementer", chain, parents=(ledger.records[-1].record_id,), now=START + timedelta(minutes=3))
    _commit_ledger(root, ledger_path, ledger, "reflection: implement")
    ledger = append(ledger, "reviewer", chain, parents=(ledger.records[-1].record_id,), to_phase="orchestrate",
                    now=START + timedelta(minutes=4))
    integration = _commit_ledger(root, ledger_path, ledger, "reflection: review")
    verifier = _LocalBranchRebind()
    token = preview_trusted_rebind(
        ledger, source_tip=integration, target_branch="codex/feature/example", target_pre_merge_tip=integration,
        token_factory=lambda: "local-git-rebind",
    )
    rebound = apply_trusted_rebind(
        ledger, token, integration_commit=integration, current_target_tip=integration, verifier=verifier,
        reason="local integration", clock=fixed_clock(START + timedelta(minutes=5)),
    )
    ledger = rebound.ledger
    _commit_ledger(root, ledger_path, ledger, "reflection: rebind")
    receipts = [admitted_receipt_for(ledger, record) for record in ledger.records if record.chain_id == chain]
    ledger = plan_workstream_chain_close(
        ledger, chain_id=chain, receipts=receipts, receipt_verifier=AdmitReceipts(), integration_witness=rebound.witness,
        integration_verifier=verifier, expected_head=integration, actual_head=integration,
        pre_ledger_digest=workstream_ledger_digest(render_workstream_ledger(ledger)), branch="codex/feature/example",
        conclusion="closed", reasoning="durably reviewed", source="real-git-test", confidence="high",
        clock=fixed_clock(START + timedelta(minutes=6)),
    )
    _commit_ledger(root, ledger_path, ledger, "reflection: close")
    return root, ledger, ledger_path, chain


def _admit_real_git_compaction(root: Path, ledger: WorkstreamLedger, ledger_path: str, chain: str, *,
                               evidence_entry: str = "mse_0123456789abcdef",
                               receipt_entry: str = "mse_1111111111111111",
                               member_disposition: str = "early-expired-unpromoted",
                               include_early_approval: bool = True,
                               receipt_decision_id: str = "D1",
                               duplicate_evidence_entry: bool = False) -> tuple[WorkstreamCompactionReceipt, str]:
    """Create the exact ordinary-session / ledger-only two-commit proof pair."""
    session_path = ".memory-seed/sessions/2026-09/2026-09-06.md"
    session_file = root / Path(session_path)
    records = tuple(record for record in ledger.records if record.chain_id == chain)
    close = records[-1]
    preliminary_members = tuple(
        WorkstreamCompactionMemberReceipt(
            chain, record.record_id, record.detail_digest, session_path, evidence_entry, receipt_decision_id,
            workstream_receipt_id(ledger.header.id_salt, ledger.header.workstream_id, chain, record.detail_digest),
            "sha256:" + "1" * 64, "0" * 40, "0" * 40, member_disposition,
        )
        for record in sorted(records, key=lambda item: item.record_id)
    )
    preliminary_closure = WorkstreamCompactionClosureReceipt(
        chain, close.record_id, close.detail_digest, session_path, evidence_entry, receipt_decision_id, "0" * 40, "0" * 40,
        "sha256:" + "2" * 64,
    )
    evidence_mappings = tuple(
        reflection_ledger_module._member_session_mapping(ledger.header.workstream_id, member)
        for member in preliminary_members
    ) + (reflection_ledger_module._closure_session_mapping(preliminary_closure),)
    if include_early_approval:
        # Adversarial unsigned mapping accepted by the former implementation.
        # It is evidence bytes only, never a valid v1 host authorization.
        evidence_mappings += (
            {
                "workstream_id": ledger.header.workstream_id, "chain_id": chain,
                "closed_record_id": close.record_id, "closed_record_digest": close.detail_digest,
                "session_path": session_path, "entry_id": evidence_entry, "decision_id": receipt_decision_id,
                "disposition": "early-expired-unpromoted",
            },
        )
    session_file.parent.mkdir(parents=True, exist_ok=True)
    previous_session = session_file.read_text(encoding="utf-8") if session_file.exists() else ""
    evidence_body = _session_entry("Evidence", evidence_entry, evidence_mappings)
    if duplicate_evidence_entry:
        evidence_body += "\n" + _session_entry("Duplicate evidence", evidence_entry)
    session_file.write_text(previous_session + ("\n" if previous_session else "") + evidence_body, encoding="utf-8")
    _git(root, "add", "--", session_path)
    _git(root, "commit", "--quiet", "-m", "reflection: durable evidence")
    evidence_commit = _git(root, "rev-parse", "HEAD")
    evidence_blob = _git(root, "rev-parse", f"{evidence_commit}:{session_path}")
    members = tuple(replace(item, commit=evidence_commit, blob=evidence_blob) for item in preliminary_members)
    closure = replace(preliminary_closure, commit=evidence_commit, blob=evidence_blob)
    pre_tip = evidence_commit
    pre_blob = _git(root, "rev-parse", f"{pre_tip}:{ledger_path}")
    post_raw = reflection_ledger_module._derive_compaction_post_bytes(
        render_workstream_ledger(ledger).encode("utf-8"), ledger, (chain,), ledger_path,
    )
    ledger_file = root / Path(ledger_path)
    ledger_file.write_bytes(post_raw)
    _git(root, "add", "--", ledger_path)
    _git(root, "commit", "--quiet", "-m", "reflection: compact closed chain")
    cleanup = _git(root, "rev-parse", "HEAD")
    post_blob = _git(root, "rev-parse", f"{cleanup}:{ledger_path}")
    receipt = WorkstreamCompactionReceipt(
        ledger.header.workstream_id, ledger_path, workstream_ledger_digest(render_workstream_ledger(ledger)),
        workstream_ledger_digest(post_raw), pre_tip, pre_blob, cleanup, post_blob, (chain,),
        tuple(sorted(record.record_id for record in records)), (closure,), members,
        "closed chain retention expiry",
    )
    receipt_block = (
        _session_entry("Compaction", receipt_entry)
        + "### Reflection workstream compaction\n\n```yaml\n"
        + render_workstream_compaction_receipt(receipt) + "```\n"
    )
    session_file.write_text(session_file.read_text(encoding="utf-8") + "\n" + receipt_block, encoding="utf-8")
    _git(root, "add", "--", session_path)
    _git(root, "commit", "--quiet", "-m", "reflection: record compaction", "-m", f"Memory-Entry: {receipt_entry}")
    return receipt, _git(root, "rev-parse", "HEAD")


def _write_open_cross_workstream_dependent(root: Path, source: WorkstreamLedger, target_record, *,
                                            receipt: WorkstreamDependencyReceipt | None) -> WorkstreamLedger:
    """Persist a second open workstream that depends on one source record."""
    dependent = initialize_workstream_ledger(
        working_branch="codex/feature/dependent", base_sha=source.header.base_sha,
        clock=fixed_clock(START + timedelta(minutes=20)), entropy=lambda _: bytes.fromhex(SALT),
    )
    _commit_ledger(root, workstream_ledger_path(dependent.header.workstream_id), dependent, "reflection: dependent init")
    dependency = WorkstreamDependency(
        source.header.workstream_id, target_record.record_id, target_record.detail_digest,
        "cross-workstream cleanup coverage", receipt,
    )
    request = WorkstreamAppendRequest(
        "planner", None, "no_related_thread", (), True, "dependent root", "needs source detail", "real-git", "high",
        depends_on=(dependency,),
    )
    dependent = plan_workstream_append(
        dependent, request, expected_head=HEAD, actual_head=HEAD,
        pre_ledger_digest=workstream_ledger_digest(render_workstream_ledger(dependent)),
        branch=dependent.effective_branch, clock=fixed_clock(START + timedelta(minutes=21)), active_ledgers=(source,),
    )
    _commit_ledger(root, workstream_ledger_path(dependent.header.workstream_id), dependent, "reflection: cross dependency")
    return dependent


@pytest.fixture
def isolated_compaction_structure(monkeypatch):
    """Exercise deferred compaction mechanics without claiming time authority.

    Production historical admission is unconditionally disabled. Only tests
    explicitly requesting this fixture substitute the retention gate so that
    structural history, suffix, replay, and dependency coverage stays tested.
    Unpatched real-Git negatives below prove the production refusal.
    """
    monkeypatch.setattr(reflection_ledger_module, "_validate_historical_compaction_retention", lambda *args: None)


def test_trusted_history_rejects_raw_sole_deletion_and_admits_exact_proof_pair(tmp_path, isolated_compaction_structure):
    root, ledger, ledger_path, chain = _closed_git_workstream(tmp_path)
    raw = render_workstream_ledger(ledger)
    (root / Path(ledger_path)).write_text(raw.split("## Record", 1)[0], encoding="utf-8")
    _git(root, "add", "--", ledger_path)
    _git(root, "commit", "--quiet", "-m", "forged tail deletion")
    with pytest.raises(ReflectionValidationError) as refused:
        load_trusted_workstream_ledger(root, trusted_ref="refs/heads/codex/feature/example", ledger_path=ledger_path)
    assert refused.value.diagnostic.code == "compaction-proof-missing"

    # Reset this isolated test repository by constructing a separate valid proof
    # path in a sibling repository rather than making the loader forgive a bad
    # deletion that is reachable from the trusted ref.
    valid_root, valid_ledger, valid_path, valid_chain = _closed_git_workstream(tmp_path / "valid")
    _receipt, proof_head = _admit_real_git_compaction(valid_root, valid_ledger, valid_path, valid_chain)
    loaded = load_trusted_workstream_ledger(
        valid_root, trusted_ref="refs/heads/codex/feature/example", ledger_path=valid_path,
    )
    assert loaded.validation == "admitted-compaction"
    assert loaded.head == proof_head
    assert len(loaded.proofs) == 1
    assert loaded.raw == (valid_root / Path(valid_path)).read_bytes()
    assert workstream_board_view(valid_root).exit_code == 1
    trusted_board = workstream_board_view(valid_root, trusted_ref="refs/heads/codex/feature/example")
    assert trusted_board.exit_code == 0 and trusted_board.items[0].ledger == loaded.ledger
    suffix = preview_workstream_append_commit(
        valid_root, trusted_ref="refs/heads/codex/feature/example", workstream_id=valid_ledger.header.workstream_id,
        request=WorkstreamAppendRequest("planner", None, "no_related_thread", (), True, "fresh root", "reason", "real-git", "high"),
        clock=fixed_clock(START + timedelta(minutes=7)),
    )
    assert apply_workstream_append_commit(valid_root, suffix).record_id == suffix.record_id
    reloaded = load_trusted_workstream_ledger(
        valid_root, trusted_ref="refs/heads/codex/feature/example", ledger_path=valid_path,
    )
    assert reloaded.validation == "admitted-compaction"
    assert reloaded.suffix_record_ids[-1] == suffix.record_id


def test_trusted_history_rejects_raw_tail_deletion(tmp_path):
    root, ledger, ledger_path, _chain = _closed_git_workstream(tmp_path)
    raw = render_workstream_ledger(ledger)
    # The closeout record is an exact final block, so removing it leaves
    # otherwise canonical bytes but must still be history-classified.
    last_block = raw.rfind("\n## Record ")
    tail_deleted = raw[:last_block]
    assert tail_deleted.endswith("\n") and not tail_deleted.endswith("\n\n")
    assert parse_workstream_ledger(tail_deleted, ledger_path).records == ledger.records[:-1]
    (root / Path(ledger_path)).write_text(tail_deleted, encoding="utf-8")
    _git(root, "add", "--", ledger_path)
    _git(root, "commit", "--quiet", "-m", "forged tail deletion")
    with pytest.raises(ReflectionValidationError) as refused:
        load_trusted_workstream_ledger(root, trusted_ref="refs/heads/codex/feature/example", ledger_path=ledger_path)
    assert refused.value.diagnostic.code == "compaction-proof-missing"
    assert workstream_board_view(root, trusted_ref="refs/heads/codex/feature/example").exit_code == 1
    with pytest.raises(ReflectionValidationError) as append_refused:
        preview_workstream_append_commit(
            root, trusted_ref="refs/heads/codex/feature/example", workstream_id=ledger.header.workstream_id,
            request=WorkstreamAppendRequest("planner", None, "no_related_thread", (), True, "new", "reason", "test", "high"),
            clock=fixed_clock(START + timedelta(minutes=9)),
        )
    assert append_refused.value.diagnostic.code == "compaction-proof-missing"


def test_compaction_requires_scoped_locator_and_early_retention_evidence(tmp_path):
    locator_root, locator_ledger, locator_path, locator_chain = _closed_git_workstream(tmp_path / "locator")
    _admit_real_git_compaction(locator_root, locator_ledger, locator_path, locator_chain, receipt_decision_id="D2")
    with pytest.raises(ReflectionValidationError) as mismatched_locator:
        load_trusted_workstream_ledger(locator_root, trusted_ref="refs/heads/codex/feature/example", ledger_path=locator_path)
    assert mismatched_locator.value.diagnostic.code == "compaction-proof-session"

    malformed_root, malformed_ledger, malformed_path, malformed_chain = _closed_git_workstream(tmp_path / "malformed")
    _admit_real_git_compaction(malformed_root, malformed_ledger, malformed_path, malformed_chain,
                               duplicate_evidence_entry=True)
    with pytest.raises(ReflectionValidationError) as malformed:
        load_trusted_workstream_ledger(malformed_root, trusted_ref="refs/heads/codex/feature/example", ledger_path=malformed_path)
    assert malformed.value.diagnostic.code == "session-locator"

    retention_root, retention_ledger, retention_path, retention_chain = _closed_git_workstream(tmp_path / "retention")
    _admit_real_git_compaction(retention_root, retention_ledger, retention_path, retention_chain,
                               include_early_approval=False)
    with pytest.raises(ReflectionValidationError) as no_approval:
        load_trusted_workstream_ledger(retention_root, trusted_ref="refs/heads/codex/feature/example", ledger_path=retention_path)
    assert no_approval.value.diagnostic.code == "compaction-proof-retention"

    promoted_root, promoted_ledger, promoted_path, promoted_chain = _closed_git_workstream(tmp_path / "promoted")
    _admit_real_git_compaction(promoted_root, promoted_ledger, promoted_path, promoted_chain,
                               member_disposition="already-covered-by-decision")
    with pytest.raises(ReflectionValidationError) as promoted:
        load_trusted_workstream_ledger(promoted_root, trusted_ref="refs/heads/codex/feature/example", ledger_path=promoted_path)
    assert promoted.value.diagnostic.code == "compaction-proof-retention"


def test_compaction_refuses_open_cross_workstream_dependency_without_exact_fallback(tmp_path, isolated_compaction_structure):
    naked_root, naked_ledger, naked_path, naked_chain = _closed_git_workstream(tmp_path / "naked")
    _write_open_cross_workstream_dependent(naked_root, naked_ledger, naked_ledger.records[0], receipt=None)
    _admit_real_git_compaction(naked_root, naked_ledger, naked_path, naked_chain)
    with pytest.raises(ReflectionValidationError) as naked:
        load_trusted_workstream_ledger(naked_root, trusted_ref="refs/heads/codex/feature/example", ledger_path=naked_path)
    assert naked.value.diagnostic.code == "dependency"

    covered_root, covered_ledger, covered_path, covered_chain = _closed_git_workstream(tmp_path / "covered")
    source_record = covered_ledger.records[0]
    receipt = WorkstreamDependencyReceipt(
        ".memory-seed/sessions/2026-09/2026-09-06.md", "mse_0123456789abcdef", "D1",
        workstream_receipt_id(covered_ledger.header.id_salt, covered_ledger.header.workstream_id,
                              covered_chain, source_record.detail_digest), "sha256:" + "1" * 64,
    )
    _write_open_cross_workstream_dependent(covered_root, covered_ledger, source_record, receipt=receipt)
    _admit_real_git_compaction(covered_root, covered_ledger, covered_path, covered_chain)
    admitted = load_trusted_workstream_ledger(
        covered_root, trusted_ref="refs/heads/codex/feature/example", ledger_path=covered_path,
    )
    assert admitted.validation == "admitted-compaction"


@pytest.mark.parametrize("git_date", ("2000-01-01T00:00:00+00:00", "2099-01-01T00:00:00+00:00"))
@pytest.mark.parametrize("include_early_approval", (False, True))
def test_historical_cleanup_refuses_unsigned_approval_and_forged_git_time(tmp_path, monkeypatch, git_date,
                                                                       include_early_approval):
    root, ledger, ledger_path, chain = _closed_git_workstream(tmp_path)
    monkeypatch.setenv("GIT_AUTHOR_DATE", git_date)
    monkeypatch.setenv("GIT_COMMITTER_DATE", git_date)
    receipt, head = _admit_real_git_compaction(
        root, ledger, ledger_path, chain, include_early_approval=include_early_approval,
    )
    # Prove that the attack changed both cleanup and receipt commit metadata.
    for commit in (receipt.cleanup_commit, head):
        dates = _git(root, "show", "-s", "--format=%aI %cI", commit).split()
        assert [datetime.fromisoformat(value) for value in dates] == [datetime.fromisoformat(git_date)] * 2
    with pytest.raises(ReflectionValidationError) as refused:
        load_trusted_workstream_ledger(root, trusted_ref="refs/heads/codex/feature/example", ledger_path=ledger_path)
    assert refused.value.diagnostic.code == "compaction-proof-retention"
    assert "disabled" in refused.value.diagnostic.message
    assert workstream_board_view(root, trusted_ref="refs/heads/codex/feature/example").exit_code == 1


def test_early_cleanup_refuses_unpromoted_locator_and_caller_verifier(tmp_path):
    root, ledger, _path, chain = _closed_git_workstream(tmp_path)
    rebind = ledger.rebinds[-1]
    witness = TrustedIntegrationWitness(
        ledger.header.workstream_id, rebind.record_id, rebind.from_branch, rebind.to_branch, rebind.source_tip,
        rebind.target_pre_merge_tip, rebind.integration_commit, rebind.pre_ledger_digest,
    )
    receipts = [admitted_receipt_for(ledger, record) for record in ledger.records if record.chain_id == chain]
    receipts = [replace(item, receipt=replace(item.receipt, disposition="early-expired-unpromoted")) for item in receipts]
    approval = EarlyExpiryApproval(ledger.header.workstream_id, chain, ".memory-seed/sessions/2026-09/2026-09-06.md",
                                   "mse_0123456789abcdef", "D1", HEAD, "e" * 40, "user-approved-disposal")
    with pytest.raises(ReflectionValidationError, match="disabled") as refused:
        preview_workstream_expiry(
            ledger, expected_head=_git(root, "rev-parse", "HEAD"), chain_ids=(chain,), now=START,
            receipts=receipts, receipt_verifier=AdmitReceipts(), integration_witness=witness,
            integration_verifier=_LocalBranchRebind(), early_approval=approval,
            early_approval_verifier=AcceptEarlyExpiry(),
        )
    assert refused.value.diagnostic.code == "early-expiry"


@pytest.mark.parametrize("shape", ("tail", "sole"))
def test_precleanup_board_refuses_strict_valid_deletion_in_other_dependent_ledger(tmp_path, shape):
    root, source, source_path, chain = _closed_git_workstream(tmp_path)
    other = initialize_workstream_ledger(
        working_branch="codex/feature/dependent", base_sha=source.header.base_sha,
        clock=fixed_clock(START), entropy=lambda _: bytes.fromhex(SALT),
    )
    other_path = workstream_ledger_path(other.header.workstream_id)
    _commit_ledger(root, other_path, other, "reflection: dependent init")
    if shape == "tail":
        other = append(other, "planner", None, relationship="no_related_thread", no_related_thread=True,
                       now=START + timedelta(minutes=1))
        _commit_ledger(root, other_path, other, "reflection: independent root")
    before = other
    target = source.records[0]
    request = WorkstreamAppendRequest(
        "planner", None, "no_related_thread", (), True, "needs target", "blocks cleanup", "real-git", "high",
        depends_on=(WorkstreamDependency(source.header.workstream_id, target.record_id, target.detail_digest,
                                        "required source evidence", None),),
    )
    other = plan_workstream_append(
        other, request, expected_head=HEAD, actual_head=HEAD,
        pre_ledger_digest=workstream_ledger_digest(render_workstream_ledger(other)), branch=other.effective_branch,
        clock=fixed_clock(START + timedelta(minutes=2)), active_ledgers=(source,),
    )
    _commit_ledger(root, other_path, other, "reflection: dependent root")
    good_tip = _git(root, "rev-parse", "HEAD")
    assert len(reflection_ledger_module._trusted_active_ledgers_at_commit(root, good_tip)) == 2
    # Delete exactly the final dependency block; both post-images parse strictly.
    assert parse_workstream_ledger(render_workstream_ledger(before), other_path) == before
    _commit_ledger(root, other_path, before, f"forged {shape} dependent deletion")
    bad_tip = _git(root, "rev-parse", "HEAD")
    with pytest.raises(ReflectionValidationError) as board_refused:
        reflection_ledger_module._trusted_active_ledgers_at_commit(root, bad_tip)
    assert board_refused.value.diagnostic.code == "compaction-proof-missing"
    assert board_refused.value.diagnostic.path == other_path
    _admit_real_git_compaction(root, source, source_path, chain)
    # The actual cleanup path must expose the other ledger's forged history,
    # not approve a board merely because its current bytes are strict-valid.
    with pytest.raises(ReflectionValidationError) as cleanup_refused:
        load_trusted_workstream_ledger(root, trusted_ref="refs/heads/codex/feature/example", ledger_path=source_path)
    assert cleanup_refused.value.diagnostic.code == "compaction-proof-missing"
    assert cleanup_refused.value.diagnostic.path == other_path


def test_trusted_board_classification_refuses_cycles_and_discards_failed_context(tmp_path, monkeypatch):
    root, _ledger, path = _new_git_workstream(tmp_path)
    classify = reflection_ledger_module._classify_trusted_workstream_ledger

    def recurse(root, trusted_ref, head, ledger_path):
        return load_trusted_workstream_ledger(root, trusted_ref=trusted_ref, ledger_path=ledger_path)

    monkeypatch.setattr(reflection_ledger_module, "_classify_trusted_workstream_ledger", recurse)
    with pytest.raises(ReflectionValidationError) as refused:
        load_trusted_workstream_ledger(root, trusted_ref="HEAD", ledger_path=path)
    assert refused.value.diagnostic.code == "dependency-context-cycle"
    monkeypatch.setattr(reflection_ledger_module, "_classify_trusted_workstream_ledger", classify)
    assert load_trusted_workstream_ledger(root, trusted_ref="HEAD", ledger_path=path).validation == "normal"


@pytest.mark.parametrize("limit", ("MAX_TRUSTED_LEDGER_CLASSIFICATION_DEPTH", "MAX_TRUSTED_LEDGER_CLASSIFICATIONS"))
def test_trusted_board_classification_bounds_nested_history(tmp_path, monkeypatch, limit):
    root, ledger, path, chain = _closed_git_workstream(tmp_path)
    _admit_real_git_compaction(root, ledger, path, chain)
    monkeypatch.setattr(reflection_ledger_module, limit, 1)
    with pytest.raises(ReflectionValidationError) as refused:
        load_trusted_workstream_ledger(root, trusted_ref="HEAD", ledger_path=path)
    assert refused.value.diagnostic.code == "dependency-context-limit"


def test_raw_guarded_workstream_routes_refuse_git_backed_context_before_any_mutation(tmp_path):
    root, ledger, ledger_path = _new_git_workstream(tmp_path)
    trusted_ref = "refs/heads/codex/feature/example"
    with pytest.raises(ReflectionValidationError) as implicit_git:
        guarded_init_workstream_ledger(root, expected_head=HEAD, actual_head=HEAD, working_branch="codex/feature/new",
                                       base_sha=BASE)
    assert implicit_git.value.diagnostic.code == "guarded-git-mutation"
    with pytest.raises(ReflectionValidationError) as init:
        guarded_init_workstream_ledger(root, expected_head=HEAD, actual_head=HEAD, working_branch="codex/feature/new",
                                       base_sha=BASE, trusted_ref=trusted_ref)
    assert init.value.diagnostic.code == "guarded-git-mutation"
    with pytest.raises(ReflectionValidationError) as append:
        guarded_append_workstream_ledger(
            root, workstream_id=ledger.header.workstream_id,
            request=WorkstreamAppendRequest("planner", None, "no_related_thread", (), True, "new", "reason", "test", "high"),
            expected_head=HEAD, actual_head=HEAD, pre_ledger_digest=workstream_ledger_digest(render_workstream_ledger(ledger)),
            branch=ledger.effective_branch, trusted_ref=trusted_ref,
        )
    assert append.value.diagnostic.code == "guarded-git-mutation"
    with pytest.raises(ReflectionValidationError) as rebind:
        guarded_apply_trusted_rebind(root, workstream_id=ledger.header.workstream_id, token=None,
                                     integration_commit=HEAD, current_target_tip=HEAD, verifier=AcceptRebind(),
                                     reason="unused", trusted_ref=trusted_ref)
    assert rebind.value.diagnostic.code == "guarded-git-mutation"
    with pytest.raises(ReflectionValidationError) as expiry:
        guarded_apply_workstream_expiry(root, workstream_id=ledger.header.workstream_id, preview=None,
                                        actual_head=HEAD, integration_witness=None, integration_verifier=AcceptRebind(),
                                        trusted_ref=trusted_ref)
    assert expiry.value.diagnostic.code == "guarded-git-mutation"
    (root / Path(ledger_path)).unlink()
    board = workstream_board_view(root, trusted_ref=trusted_ref)
    assert board.exit_code == 1
    assert board.items[0].diagnostic is not None and board.items[0].diagnostic.code == "missing-ledger"


def test_trusted_history_rejects_raw_middle_chain_deletion(tmp_path):
    root, ledger, ledger_path = _new_git_workstream(tmp_path)
    ledger = append(ledger, "planner", None, relationship="no_related_thread", no_related_thread=True,
                    now=START + timedelta(minutes=1))
    removed_chain = ledger.records[-1].chain_id
    _commit_ledger(root, ledger_path, ledger, "reflection: first root")
    ledger = append(ledger, "planner", None, relationship="no_related_thread", no_related_thread=True,
                    now=START + timedelta(minutes=2))
    _commit_ledger(root, ledger_path, ledger, "reflection: second root")
    raw = reflection_ledger_module._derive_compaction_post_bytes(
        render_workstream_ledger(ledger).encode("utf-8"), ledger, (removed_chain,), ledger_path,
    )
    (root / Path(ledger_path)).write_bytes(raw)
    _git(root, "add", "--", ledger_path)
    _git(root, "commit", "--quiet", "-m", "forged middle deletion")
    with pytest.raises(ReflectionValidationError) as refused:
        load_trusted_workstream_ledger(root, trusted_ref="refs/heads/codex/feature/example", ledger_path=ledger_path)
    assert refused.value.diagnostic.code == "compaction-proof-missing"


def test_real_git_append_transaction_is_opaque_atomic_and_immediately_reloads(tmp_path):
    root, ledger, ledger_path = _new_git_workstream(tmp_path)
    request = WorkstreamAppendRequest("planner", None, "no_related_thread", (), True, "root", "reason", "real-git", "high")
    first = preview_workstream_append_commit(
        root, trusted_ref="refs/heads/codex/feature/example", workstream_id=ledger.header.workstream_id,
        request=request, clock=fixed_clock(START + timedelta(minutes=1)),
    )
    result = apply_workstream_append_commit(root, first)
    loaded = load_trusted_workstream_ledger(root, trusted_ref="refs/heads/codex/feature/example", ledger_path=ledger_path)
    assert result.new_head == loaded.head and result.record_id == loaded.ledger.records[-1].record_id

    second = preview_workstream_append_commit(
        root, trusted_ref="refs/heads/codex/feature/example", workstream_id=ledger.header.workstream_id,
        request=WorkstreamAppendRequest("planner", loaded.ledger.records[-1].chain_id, "refines",
                                        (loaded.ledger.records[-1].record_id,), False, "next", "reason", "real-git", "high"),
        clock=fixed_clock(START + timedelta(minutes=2)),
    )
    assert apply_workstream_append_commit(root, second).ledger.records[-1].record_id == second.record_id

    dirty = preview_workstream_append_commit(
        root, trusted_ref="refs/heads/codex/feature/example", workstream_id=ledger.header.workstream_id,
        request=WorkstreamAppendRequest("implementer", loaded.ledger.records[-1].chain_id, "refines",
                                        (loaded.ledger.records[-1].record_id,), False, "later", "reason", "real-git", "high"),
        clock=fixed_clock(START + timedelta(minutes=3)),
    )
    (root / "untracked.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(ReflectionValidationError) as dirty_error:
        apply_workstream_append_commit(root, dirty)
    assert dirty_error.value.diagnostic.code == "append-worktree-not-clean"
    (root / "untracked.txt").unlink()
    with pytest.raises(ReflectionValidationError) as failed_commit:
        apply_workstream_append_commit(root, dirty, fault_injector=lambda stage: (_ for _ in ()).throw(RuntimeError("boom")) if stage == "before-commit" else None)
    assert failed_commit.value.diagnostic.code == "append-commit-failed"
    assert _git(root, "status", "--porcelain") == ""
    (root / "staged.txt").write_text("staged\n", encoding="utf-8")
    _git(root, "add", "staged.txt")
    with pytest.raises(ReflectionValidationError) as staged_error:
        apply_workstream_append_commit(root, dirty)
    assert staged_error.value.diagnostic.code == "append-worktree-not-clean"


def test_real_git_append_refuses_detached_head_and_cas_race_without_ledger_leak(tmp_path):
    root, ledger, ledger_path = _new_git_workstream(tmp_path)
    request = WorkstreamAppendRequest("planner", None, "no_related_thread", (), True, "root", "reason", "real-git", "high")
    preview = preview_workstream_append_commit(
        root, trusted_ref="refs/heads/codex/feature/example", workstream_id=ledger.header.workstream_id,
        request=request, clock=fixed_clock(START + timedelta(minutes=1)),
    )
    head = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "--quiet", "--detach")
    with pytest.raises(ReflectionValidationError) as detached:
        apply_workstream_append_commit(root, preview)
    assert detached.value.diagnostic.code == "append-detached-head"
    _git(root, "checkout", "--quiet", "codex/feature/example")

    preview = preview_workstream_append_commit(
        root, trusted_ref="refs/heads/codex/feature/example", workstream_id=ledger.header.workstream_id,
        request=request, clock=fixed_clock(START + timedelta(minutes=1)),
    )
    original = (root / Path(ledger_path)).read_bytes()
    base = _git(root, "rev-parse", "HEAD^")

    def move_ref(stage: str) -> None:
        if stage == "before-cas":
            _git(root, "update-ref", "refs/heads/codex/feature/example", base, head)

    with pytest.raises(ReflectionValidationError) as raced:
        apply_workstream_append_commit(root, preview, fault_injector=move_ref)
    assert raced.value.diagnostic.code == "stale_ref"
    assert (root / Path(ledger_path)).read_bytes() == original


def _transaction_state(root):
    return (_git(root, "rev-parse", "HEAD"), _git(root, "show-ref"), _git(root, "ls-files", "--stage"),
            {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*")
             if p.is_file() and ".git" not in p.relative_to(root).parts},
            sorted(p.relative_to(root).as_posix() for p in root.rglob("*")
                   if p.is_dir() and ".git" not in p.relative_to(root).parts))


class _TransactionRebindVerifier(TrustedRebindVerifier):
    def __init__(self, token, integration):
        self.token, self.integration = token, integration
        self.valid = True
        self.witnesses = []

    def verify(self, token, *, integration_commit, current_target_tip):
        return self.valid and token == self.token and integration_commit == current_target_tip == self.integration

    def admit_witness(self, token, rebind, *, integration_commit):
        witness = TrustedIntegrationWitness(token.workstream_id, rebind.record_id, rebind.from_branch, rebind.to_branch,
                                             rebind.source_tip, rebind.target_pre_merge_tip, integration_commit, rebind.pre_ledger_digest)
        self.witnesses.append(witness)
        return witness

    def verify_witness(self, witness):
        return self.valid and witness in self.witnesses


class _TransactionReceiptVerifier(WorkstreamReceiptVerifier):
    def __init__(self, receipts):
        self.receipts = receipts
        self.valid = True

    def verify(self, admitted):
        return self.valid and admitted in self.receipts


def _commit_transaction_receipts(root, loaded, locator):
    drafts = plan_workstream_chain_receipts(loaded, **locator)
    body = _session_entry("2026-09-06 12:10 - Validated synthesis", locator["entry_id"])
    body += "\n".join("```yaml\n" + render_workstream_receipt(item) + "```\n" for item in drafts)
    session = root / locator["session_path"]
    session.parent.mkdir(parents=True, exist_ok=True)
    session.write_text(body, encoding="utf-8")
    _git(root, "add", locator["session_path"])
    _git(root, "commit", "--quiet", "-m", "durable synthesis receipts")


def _planned_transaction(tmp_path, operation, *, receipt_origin="integration", retention_trust=True):
    root, synthetic, _path = _new_git_workstream(tmp_path)
    branch = synthetic.header.working_branch
    base = synthetic.header.base_sha
    if operation in {"close", "rebind"} and retention_trust:
        from memory_seed.reflection_ledger import reflection_trust_init
        default_branch = next(name for name in _git(root, "for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines()
                              if name != branch)
        _git(root, "checkout", "--quiet", "-B", default_branch, base)
        assert reflection_trust_init(root, apply=True)["applied"]
        base = _git(root, "rev-parse", "HEAD")
    # Disposable fixture only: start the tested sequence at the plain base.
    _git(root, "checkout", "--quiet", "-B", branch, base)
    init = preview_workstream_init_commit(root, trusted_ref=branch, clock=lambda: START)
    if operation == "init":
        return root, init, {}
    initial = apply_workstream_commit(root, init)
    workstream = initial.ledger.header.workstream_id
    root_request = WorkstreamAppendRequest("planner", None, "no_related_thread", (), True, "root", "reason", "test", "high")
    first = preview_workstream_append_commit(root, trusted_ref=branch, workstream_id=workstream, request=root_request)
    if operation == "append":
        return root, first, {}
    ledger = apply_workstream_append_commit(root, first).ledger
    chain = ledger.records[0].chain_id
    for role, phase in (("planner", None), ("implementer", None), ("reviewer", "orchestrate")):
        request = WorkstreamAppendRequest(role, chain, "refines", (ledger.records[-1].record_id,), False,
                                          role, "reason", "test", "high", to_phase=phase)
        planned = preview_workstream_append_commit(root, trusted_ref=branch, workstream_id=workstream, request=request)
        ledger = apply_workstream_append_commit(root, planned).ledger
    locator = dict(chain_id=chain, session_path=".memory-seed/sessions/2026-09/2026-09-06.md",
                   entry_id="mse_0123456789abcdef", decision_id="D1", disposition="promoted-to-decision")
    receipt_snapshot = None
    if receipt_origin in {"source", "source-deleted"}:
        loaded = load_trusted_workstream_ledger(root, trusted_ref=branch, ledger_path=init.ledger_path)
        _commit_transaction_receipts(root, loaded, locator)
        receipt_snapshot = ((root / locator["session_path"]).read_bytes(),
                            _git(root, "rev-parse", "HEAD:" + locator["session_path"]))
        if receipt_origin == "source-deleted":
            _git(root, "rm", "--", locator["session_path"])
            _git(root, "commit", "--quiet", "-m", "delete pre-integration receipt evidence")
    source_tip = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "--quiet", "-b", "integration", base)
    target_tip = _git(root, "rev-parse", "HEAD")
    token = preview_trusted_rebind(ledger, source_tip=source_tip, target_branch="integration",
                                    target_pre_merge_tip=target_tip, token_factory=lambda: "host-issued-integration-token")
    _git(root, "merge", "--quiet", "--no-ff", "-m", "integrate source", branch)
    verifier = _TransactionRebindVerifier(token, _git(root, "rev-parse", "HEAD"))
    kwargs = dict(trusted_ref="integration", workstream_id=workstream, token=token, verifier=verifier, reason="verified integration")
    planned = preview_workstream_rebind_commit(root, **kwargs)
    context = {"rebind_kwargs": kwargs, "verifier": verifier, "source_branch": branch, "chain": chain,
               "receipt_locator": locator, "receipt_snapshot": receipt_snapshot}
    if operation == "rebind":
        return root, planned, context
    rebound = apply_workstream_commit(root, planned)
    loaded = load_trusted_workstream_ledger(root, trusted_ref="integration", ledger_path=init.ledger_path)
    _commit_transaction_receipts(root, loaded, locator)
    loaded = load_trusted_workstream_ledger(root, trusted_ref="integration", ledger_path=init.ledger_path)
    receipts = admit_workstream_chain_receipts(loaded, session_ref="HEAD", **locator,
        integration_witness=rebound.integration_witness, integration_verifier=verifier)
    receipt_verifier = _TransactionReceiptVerifier(receipts)
    close_kwargs = dict(trusted_ref="integration", workstream_id=workstream, chain_id=chain, receipts=receipts,
                        receipt_verifier=receipt_verifier, integration_witness=rebound.integration_witness,
                        integration_verifier=verifier, conclusion="closed", reasoning="reviewed and synthesized",
                        source="test", confidence="high")
    context.update(close_kwargs=close_kwargs, receipt_verifier=receipt_verifier, receipt_locator=locator)
    return root, preview_workstream_close_commit(root, **close_kwargs), context


@pytest.mark.parametrize("forged_predecessor", [False, True])
def test_git_integration_witness_validates_predecessor_ownership(tmp_path, forged_predecessor):
    from memory_seed.reflection_ledger import GitWorkstreamIntegrationVerifier
    from memory_seed.reflection_operations import run_reflection_operation

    root, first, context = _planned_transaction(tmp_path, "rebind")
    if forged_predecessor:
        # Keep an exactly parseable ownership transfer but point its claimed
        # integration event at a one-parent advancement instead of the merge.
        from memory_seed import reflection_ledger as kernel
        _git(root, "commit", "--allow-empty", "--quiet", "-m", "intervene before forged ownership")
        raw = (root / first.ledger_path).read_bytes() + first.suffix_bytes
        rebound = kernel.parse_workstream_ledger(raw.decode("utf-8")).rebinds[-1]
        rebound = replace(rebound, integration_commit=_git(root, "rev-parse", "HEAD"))
        rebound = replace(rebound, detail_digest=kernel._detail_digest_for_rebind(rebound))
        with (root / first.ledger_path).open("ab") as stream:
            stream.write(b"\n" + kernel.render_trusted_rebind(rebound).encode("utf-8"))
        _git(root, "add", first.ledger_path)
        _git(root, "commit", "--quiet", "-m", "unverified structural ownership")
    else:
        apply_workstream_commit(root, first)
    source = load_trusted_workstream_ledger(root, trusted_ref="integration", ledger_path=first.ledger_path)
    source_tip = _git(root, "rev-parse", "HEAD")
    _git(root, "checkout", "--quiet", "-b", "final-integration", source.ledger.header.base_sha)
    target_tip = _git(root, "rev-parse", "HEAD")
    token = preview_trusted_rebind(source.ledger, source_tip=source_tip, target_branch="final-integration",
        target_pre_merge_tip=target_tip, token_factory=lambda: "final-integration-token")
    _git(root, "merge", "--quiet", "--no-ff", "-m", "valid final integration", "integration")
    verifier = _TransactionRebindVerifier(token, _git(root, "rev-parse", "HEAD"))
    final = preview_workstream_rebind_commit(root, trusted_ref="final-integration",
        workstream_id=source.ledger.header.workstream_id, token=token, verifier=verifier, reason="final integration")
    result = apply_workstream_commit(root, final)
    loaded = load_trusted_workstream_ledger(root, trusted_ref="final-integration", ledger_path=first.ledger_path)
    assert len(loaded.ledger.rebinds) == 2
    state = _transaction_state(root)
    admission = GitWorkstreamIntegrationVerifier(loaded)
    if forged_predecessor:
        with pytest.raises(ReflectionValidationError, match="ordered target and source"):
            admission.witness()
        refused = run_reflection_operation("ledger_close", dict(cwd=str(root),
            workstream_id=source.ledger.header.workstream_id, chain_id=context["chain"], apply=True))
        assert refused["error"]["code"] == "close-authority", refused
    else:
        assert admission.witness() == result.integration_witness
    assert _transaction_state(root) == state


@pytest.mark.parametrize("operation", ["init", "append", "rebind", "close"])
def test_shared_transaction_positive_single_commit_and_single_use(tmp_path, operation):
    root, planned, _context = _planned_transaction(tmp_path, operation)
    result = apply_workstream_commit(root, planned)
    assert _git(root, "rev-parse", "HEAD^") == planned.expected_head
    assert _git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", result.new_head) == planned.ledger_path
    assert _git(root, "status", "--porcelain") == ""
    assert result.post_ledger_digest == planned.post_ledger_digest
    assert result.record_id == planned.record_id
    assert (operation == "rebind") == (result.integration_witness is not None)
    if operation == "init":
        assert not result.ledger.entries and result.ledger.header.base_sha == planned.expected_head
    elif operation == "close":
        assert result.ledger.records[-1].to_phase == "closed"
    before = _transaction_state(root)
    with pytest.raises(ReflectionValidationError):
        apply_workstream_commit(root, planned)
    assert _transaction_state(root) == before


@pytest.mark.parametrize("operation", ["init", "append", "rebind", "close"])
def test_shared_transaction_forged_mutated_detached_wrong_worktree_and_stale_refuse(tmp_path, operation):
    root, planned, _context = _planned_transaction(tmp_path, operation)
    for field, value in (("suffix_bytes", b"forged\n"), ("operation", "expire"), ("token", "fabricated"),
                          ("record_id", "rlr_" + "0" * 20)):
        forged = deepcopy(planned)
        object.__setattr__(forged, field, value)
        before = _transaction_state(root)
        with pytest.raises(ReflectionValidationError):
            apply_workstream_commit(root, forged)
        assert _transaction_state(root) == before
    clone = tmp_path / "clone"
    _git(root, "worktree", "add", "--quiet", "--force", str(clone), planned.trusted_ref)
    before = _transaction_state(clone)
    with pytest.raises(ReflectionValidationError) as wrong:
        apply_workstream_commit(clone, planned)
    assert wrong.value.diagnostic.code == "transaction-worktree"
    assert _transaction_state(clone) == before
    branch = _git(root, "branch", "--show-current")
    _git(root, "checkout", "--quiet", "--detach")
    before = _transaction_state(root)
    with pytest.raises(ReflectionValidationError) as detached:
        apply_workstream_commit(root, planned)
    assert detached.value.diagnostic.code == "append-detached-head"
    assert _transaction_state(root) == before
    _git(root, "checkout", "--quiet", branch)
    (root / "README.md").write_text("post-plan mutation\n", encoding="utf-8")
    before = _transaction_state(root)
    with pytest.raises(ReflectionValidationError):
        apply_workstream_commit(root, planned)
    assert _transaction_state(root) == before
    _git(root, "add", "README.md")
    _git(root, "commit", "--quiet", "-m", "move planned ref")
    before = _transaction_state(root)
    with pytest.raises(ReflectionValidationError) as stale:
        apply_workstream_commit(root, planned)
    assert stale.value.diagnostic.code == "stale_head"
    assert _transaction_state(root) == before


@pytest.mark.parametrize("operation", ["init", "append", "rebind", "close"])
def test_shared_transaction_ref_cas_failure_restores_index_and_ledger(tmp_path, operation):
    root, planned, _context = _planned_transaction(tmp_path, operation)
    before = _transaction_state(root)

    def fail_commit(stage):
        if stage == "before-commit":
            raise RuntimeError("injected commit failure")

    with pytest.raises(ReflectionValidationError) as construction:
        apply_workstream_commit(root, planned, fault_injector=fail_commit)
    assert construction.value.diagnostic.code == "append-commit-failed"
    assert _transaction_state(root) == before
    tree = _git(root, "rev-parse", "HEAD^{tree}")
    competing = _git(root, "commit-tree", tree, "-p", planned.expected_head, "-m", "competing branch update")

    def move_ref(stage):
        if stage == "before-cas":
            _git(root, "update-ref", planned.trusted_ref, competing, planned.expected_head)

    with pytest.raises(ReflectionValidationError) as failed:
        apply_workstream_commit(root, planned, fault_injector=move_ref)
    assert failed.value.diagnostic.code == "stale_ref"
    after = _transaction_state(root)
    assert after[0] == competing
    assert after[2:] == before[2:]
    assert _git(root, "status", "--porcelain") == ""


@pytest.mark.parametrize("operation", ["init", "append", "rebind", "close"])
def test_shared_transaction_symlink_ancestor_refuses_before_writes(tmp_path, operation, monkeypatch):
    root, planned, _context = _planned_transaction(tmp_path, operation)
    before = _transaction_state(root)
    original = Path.lstat

    def hostile_lstat(path, *args, **kwargs):
        if path == root / ".memory-seed":
            return SimpleNamespace(st_mode=stat.S_IFLNK, st_reparse_tag=0)
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "lstat", hostile_lstat)
        with pytest.raises(ReflectionValidationError) as failed:
            apply_workstream_commit(root, planned)
        assert failed.value.diagnostic.code == "unsupported-reflection-format"
    assert _transaction_state(root) == before


@pytest.mark.parametrize("operation", ["rebind", "close"])
def test_shared_transaction_authority_is_revalidated_after_preview(tmp_path, operation):
    root, planned, context = _planned_transaction(tmp_path, operation)
    context["verifier" if operation == "rebind" else "receipt_verifier"].valid = False
    before = _transaction_state(root)
    with pytest.raises(ReflectionValidationError):
        apply_workstream_commit(root, planned)
    assert _transaction_state(root) == before


def test_transaction_init_collision_and_unknown_reserved_files_refuse(tmp_path):
    root, planned, _context = _planned_transaction(tmp_path, "init")
    apply_workstream_commit(root, planned)
    before = _transaction_state(root)
    with pytest.raises(ReflectionValidationError):
        preview_workstream_init_commit(root, trusted_ref=planned.trusted_ref)
    assert _transaction_state(root) == before
    # Ignored state remains visible to the reserved-family inventory.
    (root / ".git/info/exclude").write_text(".memory-seed/reflections/active/unknown\n", encoding="utf-8")
    unknown = root / ".memory-seed/reflections/active/unknown"
    unknown.write_text("unsupported\n", encoding="utf-8")
    before = _transaction_state(root)
    with pytest.raises(ReflectionValidationError):
        preview_workstream_init_commit(root, trusted_ref=planned.trusted_ref)
    assert _transaction_state(root) == before


def test_transaction_rebind_rejects_forged_source_and_retired_source_append(tmp_path):
    root, planned, context = _planned_transaction(tmp_path, "rebind")
    kwargs = context["rebind_kwargs"]
    before = _transaction_state(root)
    with pytest.raises(ReflectionValidationError):
        preview_workstream_rebind_commit(root, **{**kwargs, "token": replace(kwargs["token"], source_tip=HEAD)})
    assert _transaction_state(root) == before
    apply_workstream_commit(root, planned)
    _git(root, "checkout", "--quiet", context["source_branch"])
    before = _transaction_state(root)
    with pytest.raises(ReflectionValidationError) as retired:
        preview_workstream_append_commit(root, trusted_ref=context["source_branch"], workstream_id=kwargs["workstream_id"],
            request=WorkstreamAppendRequest("planner", None, "no_related_thread", (), True, "root", "reason", "test", "high"))
    assert retired.value.diagnostic.code == "branch-owner"
    assert _transaction_state(root) == before


def test_transaction_close_rejects_missing_forged_receipts_and_witness(tmp_path):
    root, _planned, context = _planned_transaction(tmp_path, "close")
    kwargs = context["close_kwargs"]
    cases = [
        {"receipts": ()},
        {"receipts": (replace(kwargs["receipts"][0], blob="e" * 40),)},
        {"integration_witness": replace(kwargs["integration_witness"], rebind_record_id="rlr_" + "0" * 20)},
        {"chain_id": "rlc_" + "0" * 20},
    ]
    for override in cases:
        before = _transaction_state(root)
        with pytest.raises(ReflectionValidationError):
            preview_workstream_close_commit(root, **{**kwargs, **override})
        assert _transaction_state(root) == before
    loaded = load_trusted_workstream_ledger(root, trusted_ref="integration", ledger_path=_planned.ledger_path)
    request = WorkstreamAppendRequest("orchestrator", kwargs["chain_id"], "responds",
        (loaded.ledger.records[0].record_id,), False, "divergence", "unresolved", "test", "high", to_phase="orchestrate")
    diverge = preview_workstream_append_commit(root, trusted_ref="integration", workstream_id=kwargs["workstream_id"], request=request)
    apply_workstream_append_commit(root, diverge)
    before = _transaction_state(root)
    with pytest.raises(ReflectionValidationError) as divergent:
        preview_workstream_close_commit(root, **kwargs)
    assert divergent.value.diagnostic.code == "close"
    assert "divergent" in divergent.value.diagnostic.message
    assert _transaction_state(root) == before


def test_review_rebind_source_ref_race_is_atomically_rejected(tmp_path):
    root, planned, context = _planned_transaction(tmp_path, "rebind")
    source_ref = "refs/heads/" + context["source_branch"]
    source_tip = context["rebind_kwargs"]["token"].source_tip
    source_tree = _git(root, "rev-parse", source_ref + "^{tree}")
    advanced_source = _git(root, "commit-tree", source_tree, "-p", source_tip, "-m", "source raced after validation")
    before = _transaction_state(root)

    def advance_source(stage):
        if stage == "before-cas":
            _git(root, "update-ref", source_ref, advanced_source, source_tip)

    with pytest.raises(ReflectionValidationError) as raced:
        apply_workstream_commit(root, planned, fault_injector=advance_source)
    assert raced.value.diagnostic.code == "stale_ref"
    after = _transaction_state(root)
    assert after[0] == before[0] == planned.expected_head
    assert after[2:] == before[2:]
    assert _git(root, "rev-parse", source_ref) == advanced_source
    assert _git(root, "status", "--porcelain") == ""


@pytest.mark.parametrize("snapshot", ["older", "divergent"])
def test_review_retired_source_rejects_older_and_divergent_snapshots(tmp_path, snapshot):
    root, planned, context = _planned_transaction(tmp_path, "rebind")
    source_tip = context["rebind_kwargs"]["token"].source_tip
    apply_workstream_commit(root, planned)
    _git(root, "checkout", "--quiet", "-B", context["source_branch"], source_tip + "^")
    if snapshot == "divergent":
        _git(root, "commit", "--quiet", "--allow-empty", "-m", "divergent old ownership snapshot")
    assert source_tip not in _git(root, "rev-list", "HEAD").splitlines()
    before = _transaction_state(root)
    with pytest.raises(ReflectionValidationError) as retired:
        preview_workstream_append_commit(root, trusted_ref=context["source_branch"],
            workstream_id=context["rebind_kwargs"]["workstream_id"],
            request=WorkstreamAppendRequest("planner", None, "no_related_thread", (), True, "root", "reason", "test", "high"))
    assert retired.value.diagnostic.code == "branch-owner"
    assert _transaction_state(root) == before


@pytest.mark.parametrize("locator_commit", ["source", "integration", "rebind", "later"])
def test_review_preintegration_receipts_refuse_admission_and_close(tmp_path, locator_commit):
    root, planned, context = _planned_transaction(tmp_path, "rebind", receipt_origin="source")
    rebound = apply_workstream_commit(root, planned)
    if locator_commit == "later":
        _git(root, "commit", "--quiet", "--allow-empty", "-m", "new locator for old receipt blob")
    _assert_preintegration_receipts_refused(root, planned, context, rebound, locator_commit)


def _assert_preintegration_receipts_refused(root, planned, context, rebound, locator_commit):
    locator = context["receipt_locator"]
    session_ref = {"source": context["rebind_kwargs"]["token"].source_tip,
                   "integration": planned.expected_head}.get(locator_commit, "HEAD")
    loaded = load_trusted_workstream_ledger(root, trusted_ref="integration", ledger_path=planned.ledger_path)
    before = _transaction_state(root)
    with pytest.raises(ReflectionValidationError) as admission:
        admit_workstream_chain_receipts(loaded, session_ref=session_ref, **locator,
            integration_witness=rebound.integration_witness, integration_verifier=context["verifier"])
    assert admission.value.diagnostic.code == "receipt-integration"
    assert _transaction_state(root) == before

    # Even a host that accepts structurally exact receipt objects cannot turn
    # a pre-integration origin into post-integration close coverage.
    drafts = plan_workstream_chain_receipts(loaded, **locator)
    commit = _git(root, "rev-parse", session_ref)
    blob = _git(root, "rev-parse", commit + ":" + locator["session_path"])
    untrusted = tuple(AdmittedWorkstreamReceipt(receipt, commit, blob) for receipt in drafts)
    before = _transaction_state(root)
    with pytest.raises(ReflectionValidationError) as close:
        preview_workstream_close_commit(root, trusted_ref="integration", workstream_id=loaded.ledger.header.workstream_id,
            chain_id=context["chain"], receipts=untrusted, receipt_verifier=_TransactionReceiptVerifier(untrusted),
            integration_witness=rebound.integration_witness, integration_verifier=context["verifier"],
            conclusion="close", reasoning="claimed synthesis", source="test", confidence="high")
    assert close.value.diagnostic.code == "receipt-integration"
    assert _transaction_state(root) == before


@pytest.mark.parametrize("deletion_gap", [False, True])
def test_review_postintegration_merge_cannot_launder_preintegration_receipts(tmp_path, deletion_gap):
    root, planned, context = _planned_transaction(tmp_path, "rebind")
    source = load_trusted_workstream_ledger(root, trusted_ref=context["source_branch"], ledger_path=planned.ledger_path)
    # This receipt branch carries no ledger, so the later merge has exactly
    # one ledger-bearing parent and otherwise remains valid trusted history.
    _git(root, "checkout", "--quiet", "-b", "receipt-source", source.ledger.header.base_sha)
    _commit_transaction_receipts(root, source, context["receipt_locator"])
    session_path = context["receipt_locator"]["session_path"]
    original_raw = (root / session_path).read_bytes()
    original_blob = _git(root, "rev-parse", "HEAD:" + session_path)
    if deletion_gap:
        _git(root, "rm", "--", session_path)
        _git(root, "commit", "--quiet", "-m", "delete old receipt before merging its branch")
    _git(root, "checkout", "--quiet", "integration")
    rebound = apply_workstream_commit(root, planned)
    _git(root, "merge", "--quiet", "--no-ff", "-m", "import old source receipts after integration", "receipt-source")
    if deletion_gap:
        assert _git(root, "ls-files", "--", session_path) == ""
        restored = root / session_path
        restored.parent.mkdir(parents=True, exist_ok=True)
        restored.write_bytes(original_raw)
        _git(root, "add", "--", session_path)
        _git(root, "commit", "--quiet", "-m", "restore receipt from deleted merge-parent history")
        assert _git(root, "rev-parse", "HEAD:" + session_path) == original_blob
    _assert_preintegration_receipts_refused(root, planned, context, rebound, "later")


@pytest.mark.parametrize("gap_stage", ["before-integration", "after-integration"])
def test_review_receipt_delete_gap_restore_cannot_launder_origin(tmp_path, gap_stage):
    root, planned, context = _planned_transaction(
        tmp_path, "rebind", receipt_origin="source-deleted" if gap_stage == "before-integration" else "source",
    )
    rebound = apply_workstream_commit(root, planned)
    session_path = context["receipt_locator"]["session_path"]
    original_raw, original_blob = context["receipt_snapshot"]
    if gap_stage == "after-integration":
        _git(root, "rm", "--", session_path)
        _git(root, "commit", "--quiet", "-m", "delete old receipt after integration")
    assert _git(root, "ls-files", "--", session_path) == ""
    restored = root / session_path
    restored.parent.mkdir(parents=True, exist_ok=True)
    restored.write_bytes(original_raw)
    _git(root, "add", "--", session_path)
    _git(root, "commit", "--quiet", "-m", "restore exact pre-integration receipt blob")
    assert _git(root, "rev-parse", "HEAD:" + session_path) == original_blob
    _assert_preintegration_receipts_refused(root, planned, context, rebound, "later")


def test_review_postintegration_receipt_delete_gap_restore_remains_eligible(tmp_path):
    root, planned, context = _planned_transaction(tmp_path, "close")
    locator = context["receipt_locator"]
    session_path = locator["session_path"]
    original_raw = (root / session_path).read_bytes()
    original_blob = _git(root, "rev-parse", "HEAD:" + session_path)
    _git(root, "rm", "--", session_path)
    _git(root, "commit", "--quiet", "-m", "delete post-integration receipt")
    restored = root / session_path
    restored.parent.mkdir(parents=True, exist_ok=True)
    restored.write_bytes(original_raw)
    _git(root, "add", "--", session_path)
    _git(root, "commit", "--quiet", "-m", "restore genuinely post-integration receipt")
    assert _git(root, "rev-parse", "HEAD:" + session_path) == original_blob
    loaded = load_trusted_workstream_ledger(root, trusted_ref="integration", ledger_path=planned.ledger_path)
    close_kwargs = context["close_kwargs"]
    receipts = admit_workstream_chain_receipts(loaded, session_ref="HEAD", **locator,
        integration_witness=close_kwargs["integration_witness"], integration_verifier=context["verifier"])
    close_kwargs.update(receipts=receipts, receipt_verifier=_TransactionReceiptVerifier(receipts))
    closed = apply_workstream_commit(root, preview_workstream_close_commit(root, **close_kwargs))
    assert closed.ledger.records[-1].to_phase == "closed"
    assert _git(root, "status", "--porcelain") == ""


def test_repeated_compaction_keeps_prior_receipt_bound_to_its_own_session_commit(tmp_path, isolated_compaction_structure):
    root, initial, ledger_path, first_chain = _closed_git_workstream(tmp_path)
    _admit_real_git_compaction(root, initial, ledger_path, first_chain)
    loaded = load_trusted_workstream_ledger(root, trusted_ref="refs/heads/codex/feature/example", ledger_path=ledger_path)

    def persist(request: WorkstreamAppendRequest, at: datetime) -> WorkstreamLedger:
        preview = preview_workstream_append_commit(
            root, trusted_ref="refs/heads/codex/feature/example", workstream_id=loaded.ledger.header.workstream_id,
            request=request, clock=fixed_clock(at),
        )
        return apply_workstream_append_commit(root, preview).ledger

    ledger = persist(WorkstreamAppendRequest("planner", None, "no_related_thread", (), True, "new root", "reason", "real-git", "high"),
                     START + timedelta(minutes=7))
    second_chain = ledger.records[-1].chain_id
    root_record = ledger.records[-1].record_id
    ledger = persist(WorkstreamAppendRequest("planner", second_chain, "refines", (root_record,), False,
                                             "plan", "reason", "real-git", "high"), START + timedelta(minutes=8))
    plan_record = ledger.records[-1].record_id
    ledger = persist(WorkstreamAppendRequest("implementer", second_chain, "refines", (plan_record,), False,
                                             "implement", "reason", "real-git", "high"), START + timedelta(minutes=9))
    implement_record = ledger.records[-1].record_id
    ledger = persist(WorkstreamAppendRequest("reviewer", second_chain, "refines", (implement_record,), False,
                                             "review", "reason", "real-git", "high", to_phase="orchestrate"),
                     START + timedelta(minutes=10))
    loaded = load_trusted_workstream_ledger(root, trusted_ref="refs/heads/codex/feature/example", ledger_path=ledger_path)
    rebind = loaded.ledger.rebinds[-1]
    witness = TrustedIntegrationWitness(
        loaded.ledger.header.workstream_id, rebind.record_id, rebind.from_branch, rebind.to_branch, rebind.source_tip,
        rebind.target_pre_merge_tip, rebind.integration_commit, rebind.pre_ledger_digest,
    )
    receipts = [admitted_receipt_for(loaded.ledger, record) for record in loaded.ledger.records if record.chain_id == second_chain]
    closed = plan_trusted_workstream_chain_close(
        loaded, chain_id=second_chain, receipts=receipts, receipt_verifier=AdmitReceipts(), integration_witness=witness,
        integration_verifier=_LocalBranchRebind(), conclusion="closed", reasoning="reviewed", source="real-git", confidence="high",
        clock=fixed_clock(START + timedelta(minutes=11)), active_ledgers=(loaded,),
    )
    _commit_ledger(root, ledger_path, closed, "reflection: close second chain")
    loaded = load_trusted_workstream_ledger(root, trusted_ref="refs/heads/codex/feature/example", ledger_path=ledger_path)
    expiry = preview_trusted_workstream_expiry(
        loaded, chain_ids=(second_chain,), now=START + timedelta(days=8), receipts=[
            admitted_receipt_for(loaded.ledger, record) for record in loaded.ledger.records if record.chain_id == second_chain
        ], receipt_verifier=AdmitReceipts(), integration_witness=witness, integration_verifier=_LocalBranchRebind(),
        active_ledgers=(loaded,),
    )
    assert expiry.removed_chain_ids == (second_chain,)
    _admit_real_git_compaction(root, loaded.ledger, ledger_path, second_chain,
                                evidence_entry="mse_2222222222222222", receipt_entry="mse_3333333333333333")
    reloaded = load_trusted_workstream_ledger(root, trusted_ref="refs/heads/codex/feature/example", ledger_path=ledger_path)
    assert reloaded.validation == "admitted-compaction"
    assert len(reloaded.proofs) == 2

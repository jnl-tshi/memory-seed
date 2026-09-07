from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess

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


def test_v2_ids_and_domain_digests_match_frozen_vectors():
    workstream = workstream_id(SALT, "codex/feature/example", BASE, "2026-09-06T12:00:00Z")
    assert workstream == "rwl_1j3nf0zkee6vx8zgg4v3"
    record = workstream_record_id(SALT, workstream, "2026-09-06T12:01:00Z", "sha256:" + "0" * 64)
    assert record == "rlr_0fcr9wh0xh9yn0nhyqyn"
    assert workstream_chain_id(SALT, workstream, record) == "rlc_1mhbzbsjzv646b2k845s"
    assert workstream_receipt_id(SALT, workstream, "rlc_1mhbzbsjzv646b2k845s", "sha256:" + "1" * 64) == "rrc_0hge300ydfdke03v8hfh"
    assert workstream_ledger_digest(b"example\n") == "sha256:aa964f81fd64a3e391f79079266e4e8f5e4dfe27a36f29078228a57762af46fc"
    assert workstream_detail_digest(b"example\n") == "sha256:520584969953ed7b72863bf987e267e297e4afed3ed2af2f6691e6bd6915014c"
    assert reflection_ledger_family("schema: memory-seed/reflection-plan\nversion: 1\n") == "v1"


def test_canonical_v2_header_and_guarded_append_reject_stale_or_manual_phase():
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
    with pytest.raises(ReflectionValidationError, match="canonical v2 disposition"):
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
    preflight = RetentionPreflight("key-a", "rwl_1j3nf0zkee6vx8zgg4v3", "codex/feature/example", BASE, SALT,
                                   "2026-09-06T12:00:00Z", 14, "1" * 64, "2026-09-06T12:01:00Z",
                                   "2026-09-06T12:02:00Z", "approved", ".memory-seed/sessions/2026-09/2026-09-06.md",
                                   "mse_0123456789abcdef")
    assert parse_retention_preflight(render_retention_preflight(preflight)) == preflight
    approval = RetentionApproval(preflight, HEAD, "e" * 40, "ed25519:" + "0" * 128)
    assert parse_retention_approval(render_retention_approval(approval)) == approval
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
    _git(root, "add", "README.md")
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
        evidence_mappings += (
            reflection_ledger_module._historical_early_expiry_mapping(
                ledger.header.workstream_id, chain, preliminary_closure,
            ),
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


def test_trusted_history_rejects_raw_sole_deletion_and_admits_exact_proof_pair(tmp_path):
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
    assert promoted.value.diagnostic.code == "early-expiry"


def test_compaction_refuses_open_cross_workstream_dependency_without_exact_fallback(tmp_path):
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


def test_raw_guarded_v2_routes_refuse_git_backed_context_before_any_mutation(tmp_path):
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


def test_repeated_compaction_keeps_prior_receipt_bound_to_its_own_session_commit(tmp_path):
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

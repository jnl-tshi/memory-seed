from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from memory_seed.reflection_ledger import (
    ReflectionValidationError,
    RetentionApproval,
    RetentionApprovalTrust,
    RetentionExtensionReceipt,
    RetentionPreflight,
    RetentionPreflightVerifier,
    TrustedRebindVerifier,
    WorkstreamAppendRequest,
    WorkstreamDependency,
    WorkstreamDependencyReceipt,
    WorkstreamLedgerHeader,
    WorkstreamReceipt,
    apply_trusted_rebind,
    guarded_append_workstream_ledger,
    guarded_init_workstream_ledger,
    initialize_workstream_ledger,
    parse_retention_approval,
    parse_retention_preflight,
    parse_workstream_ledger,
    plan_workstream_append,
    plan_workstream_chain_close,
    preview_trusted_rebind,
    preview_workstream_expiry,
    render_retention_approval,
    render_retention_preflight,
    render_workstream_ledger,
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
        "promoted",
    )


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
    dependency = WorkstreamDependency(target.header.workstream_id, target_record.record_id, target_record.detail_digest,
                                     "real API ordering", receipt.dependency_locator())
    assert resolve_workstream_dependency(dependency, source_workstream_id="rwl_00000000000000000000", active_ledgers=(target,)).source == "active-ledger"
    assert resolve_workstream_dependency(dependency, source_workstream_id="rwl_00000000000000000000", durable_receipts=(receipt,)).source == "durable-receipt"
    with pytest.raises(ReflectionValidationError, match="itself"):
        resolve_workstream_dependency(dependency, source_workstream_id=target.header.workstream_id)
    bad = WorkstreamDependency(target.header.workstream_id, target_record.record_id, "sha256:" + "0" * 64, "reason", None)
    with pytest.raises(ReflectionValidationError, match="digest"):
        resolve_workstream_dependency(bad, source_workstream_id="rwl_00000000000000000000", active_ledgers=(target,))


class AcceptRebind(TrustedRebindVerifier):
    def verify(self, token, *, integration_commit, current_target_tip):
        return integration_commit == INTEGRATION and current_target_tip == INTEGRATION


def test_rebind_close_and_per_chain_expiry_keep_other_chain_active():
    ledger, chain = open_chain()
    ledger = append(ledger, "implementer", chain, parents=(ledger.records[-1].record_id,), now=START + timedelta(minutes=3))
    ledger = append(ledger, "reviewer", chain, parents=(ledger.records[-1].record_id,), to_phase="orchestrate", now=START + timedelta(minutes=4))
    token = preview_trusted_rebind(ledger, source_tip=HEAD, target_branch="main", target_pre_merge_tip=TARGET, token_factory=lambda: "opaque-token")
    ledger = apply_trusted_rebind(ledger, token, integration_commit=INTEGRATION, current_target_tip=INTEGRATION,
                                  verifier=AcceptRebind(), reason="normal integration", clock=fixed_clock(START + timedelta(minutes=5)))
    preclose_receipts = [receipt_for(ledger, record) for record in ledger.records if record.chain_id == chain]
    ledger = plan_workstream_chain_close(
        ledger, chain_id=chain, receipts=preclose_receipts, expected_head=INTEGRATION, actual_head=INTEGRATION,
        pre_ledger_digest=workstream_ledger_digest(render_workstream_ledger(ledger)), branch="main",
        conclusion="closed", reasoning="reviewed and promoted", source="test", confidence="high",
        clock=fixed_clock(START + timedelta(minutes=6)),
    )
    # A second root remains independently active and is never part of this compaction.
    ledger = append(ledger, "planner", None, relationship="no_related_thread", no_related_thread=True,
                    now=START + timedelta(minutes=7))
    other_chain = ledger.records[-1].chain_id
    receipts = [receipt_for(ledger, record) for record in ledger.records if record.chain_id == chain]
    preview = preview_workstream_expiry(
        ledger, expected_head=INTEGRATION, chain_ids=(chain,), now=START + timedelta(days=8), receipts=receipts,
    )
    assert preview.git_blobs_remain is True and preview.privacy_grade_erasure is False
    assert all(record.chain_id != chain for record in preview.post_ledger.records)
    assert any(record.chain_id == other_chain for record in preview.post_ledger.records)
    with pytest.raises(ReflectionValidationError, match="branch tip"):
        from memory_seed.reflection_ledger import apply_workstream_expiry
        apply_workstream_expiry(ledger, preview, actual_head=HEAD)


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
        return RetentionApproval(
            RetentionPreflight("key-a", workstream_id(SALT, working_branch, base_sha, "2026-09-06T12:00:00Z"),
                               working_branch, base_sha, SALT, "2026-09-06T12:00:00Z", 30, "2" * 64,
                               "2026-09-06T12:01:00Z", "2026-09-06T12:02:00Z", "approved",
                               ".memory-seed/sessions/2026-09/2026-09-06.md", "mse_0123456789abcdef"),
            HEAD, "e" * 40, "ed25519:" + "0" * 128,
        )


def test_extended_init_accepts_only_host_owned_preflight_hook():
    ledger = initialize_workstream_ledger(
        working_branch="codex/feature/example", base_sha=BASE, retention_days=30,
        clock=fixed_clock(START), retention_preflight_handle="host-owned-handle", retention_verifier=FixedExtendedRetention(),
    )
    assert ledger.header.reflection_retention_days == 30
    assert ledger.header.retention_extension_receipt is not None
    with pytest.raises(ReflectionValidationError, match="requires a host"):
        initialize_workstream_ledger(working_branch="codex/feature/example", base_sha=BASE, retention_days=14)

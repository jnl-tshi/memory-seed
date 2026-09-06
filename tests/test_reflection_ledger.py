from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import replace
from hashlib import sha512
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile

import pytest

from memory_seed.reflection_ledger import (
    REFLECTION_ROOT,
    EarlyExpiryApprovalReceipt,
    ReflectionChainClose,
    ReflectionFragment,
    ReflectionManifest,
    ReflectionParticipant,
    ReflectionReceipt,
    ReflectionRecord,
    ReflectionReport,
    ReflectionReservation,
    _apply_reflection_fuse_plan,
    admit_reflection_closeout,
    admit_reflection_git_tree,
    canonical_id,
    common_view,
    ed25519_verify,
    early_expiry_approval_payload,
    eligible_expiry_paths,
    live_heads,
    parse_closeout,
    parse_fragment,
    parse_manifest,
    parse_receipt,
    parse_report,
    participants_seal,
    record_id,
    reflection_fuse,
    render_closeout,
    render_early_expiry_approval,
    render_fragment,
    render_manifest,
    render_receipt,
    render_report,
    reservation_id,
    validate_chain_close,
    validate_fragment,
    validate_relationships,
)


SEED = "8f2c5e8d4ab1c0ffeeddccbbaa99887766554433221100fedcba9876543210ab"
PLAN = "reflection-ledger-v1"
BASE = "a" * 40
KERNEL = "ledger-kernel"
BRANCH = "codex/feature/reflection-ledger-kernel"
TRACK = "kernel"
CHAIN = "rlc_0123456789abcdefghjk"
TEST_APPROVAL_KEY_ID = "test-host-key"
TEST_APPROVAL_PUBLIC_KEY = "ed25519:d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"


def make_manifest(*, base_sha=BASE, state="active", people=None, early_expiry_approval_public_key=TEST_APPROVAL_PUBLIC_KEY):
    people = people or (
        (KERNEL, "worker", BRANCH, TRACK),
        ("codex-orchestrator", "orchestrator", "codex/feature/reflection-ledger-integration", "integration"),
    )
    participants = []
    for participant, role, branch, track in people:
        report_id = reservation_id("rpr_", SEED, PLAN, participant, track, 1, "report")
        fragment_id = reservation_id("rfl_", SEED, PLAN, participant, track, 1, "fragment")
        reservation = ReflectionReservation(1, report_id, fragment_id, f"reports/{track}/{report_id}.md", f"fragments/{track}/{fragment_id}.md")
        participants.append(ReflectionParticipant(participant, role, branch, track, (reservation,)))
    orchestrator = next(item for item in participants if item.role == "orchestrator")
    provisional = ReflectionManifest(PLAN, "main", base_sha, state, "2026-09-06T12:00:00Z", 7, "sha256-crockford-v1", SEED, "0" * 64,
                                     TEST_APPROVAL_KEY_ID, early_expiry_approval_public_key,
                                     {"participant": orchestrator.participant, "branch": orchestrator.branch}, tuple(participants))
    return ReflectionManifest(PLAN, "main", base_sha, state, provisional.created_at, 7, "sha256-crockford-v1", SEED,
                              participants_seal(provisional), provisional.early_expiry_approval_key_id,
                              provisional.early_expiry_approval_public_key, provisional.orchestrator, provisional.participants)


def make_report(manifest, participant=KERNEL, *, branch=BRANCH, track=TRACK):
    reservation = manifest.reservation(participant, 1)
    return ReflectionReport(reservation.report_id, PLAN, participant, track, branch, manifest.base_sha, "sha256:" + "b" * 64, "DONE",
                            "2026-09-06T12:01:00Z", ({"command": "pytest", "exit_code": 0},), "Measured result.\n")


def make_record(manifest, fragment_id, ordinal=1, *, kind="opinion", relationship="orphan", parents=(), created="2026-09-06T12:02:00Z", corrects=None, no_related_thread=True):
    return ReflectionRecord(record_id(manifest.reservation_seed, fragment_id, ordinal), ordinal, kind, CHAIN, tuple(parents), relationship,
                            "reflection-ledger", "implementation-review", ("reflection",), (), "medium", "write-time", created,
                            "Keep temporary parsing separate.", "Session discovery must remain durable-only.", corrects=corrects,
                            no_related_thread=no_related_thread)


def make_fragment(manifest, records, *, participant=KERNEL, branch=BRANCH, track=TRACK):
    reservation = manifest.reservation(participant, 1)
    return ReflectionFragment(reservation.fragment_id, PLAN, participant, track, branch, 1, "write-time", reservation.report_id, manifest.base_sha,
                              "2026-09-06T12:02:00Z", "Kernel reflection", tuple(records))


def reports_for(manifest):
    return [make_report(manifest, person.participant, branch=person.branch, track=person.track)
            for person in manifest.participants]


def admitted_for(tmp_path, manifest, fragments, close=None):
    root = Path(tempfile.mkdtemp(prefix="reflection-admission-", dir=tmp_path))
    subprocess.run(["git", "-C", str(root), "init", "-q"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True, capture_output=True)
    base = root / manifest.active_dir
    base.mkdir(parents=True)
    (base / "manifest.yaml").write_text(render_manifest(manifest), encoding="utf-8")
    for fragment in fragments:
        reservation = manifest.reservation(fragment.participant, fragment.sequence)
        report_path = base / reservation.report_path
        fragment_path = base / reservation.fragment_path
        report_path.parent.mkdir(parents=True, exist_ok=True)
        fragment_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_report(make_report(manifest, fragment.participant, branch=fragment.working_branch, track=fragment.track)), encoding="utf-8")
        fragment_path.write_text(render_fragment(fragment), encoding="utf-8")
    if close is not None:
        (base / "closeout.md").write_text(render_closeout(manifest.plan_id, [close]), encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "reflection evidence"], check=True, capture_output=True)
    admitted = admit_reflection_git_tree(root, source="HEAD", plan_id=manifest.plan_id)
    if close is None:
        return root, admitted, None
    closes = admit_reflection_closeout(admitted)
    assert len(closes) == 1
    return root, admitted, closes[0]


def test_ids_match_published_vectors_and_reject_forgery():
    assert reservation_id("rpr_", SEED, PLAN, KERNEL, TRACK, 1, "report") == "rpr_14fyc35b2ze6e1ygw4ft"
    assert reservation_id("rfl_", SEED, PLAN, KERNEL, TRACK, 1, "fragment") == "rfl_14h1h37xrrp19qb9s1kd"
    assert record_id(SEED, "rfl_14h1h37xrrp19qb9s1kd", 1) == "rlr_1an0dh39bsnjxfnpqtqh"
    assert record_id(SEED, "rfl_14h1h37xrrp19qb9s1kd", 2) == "rlr_0v66ws242aeshw23ppwr"
    assert canonical_id("rrc_", SEED, "x") != canonical_id("rrc_", SEED, "y")


def test_ed25519_approval_verifier_matches_rfc8032_vector():
    public_key = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
    signature = bytes.fromhex(
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
        "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
    )
    assert ed25519_verify(public_key, b"", signature)
    assert not ed25519_verify(public_key, b"forged", signature)


def test_manifest_report_fragment_canonical_bytes_and_ownership():
    manifest = make_manifest()
    assert parse_manifest(render_manifest(manifest)) == manifest
    report = make_report(manifest)
    assert parse_report(render_report(report)) == report
    fragment = make_fragment(manifest, [make_record(manifest, manifest.reservation(KERNEL, 1).fragment_id)])
    assert parse_fragment(render_fragment(fragment)) == fragment
    validate_fragment(fragment, manifest, report, branch=BRANCH)
    with pytest.raises(ValueError, match="canonical"):
        parse_report(render_report(report).replace("# Worker report", "# Report"))
    forged = ReflectionFragment("rfl_0123456789abcdefghjk", fragment.plan_id, fragment.participant, fragment.track,
                                fragment.working_branch, fragment.sequence, fragment.source, fragment.report_id,
                                fragment.base_sha, fragment.created_at, fragment.title, fragment.records)
    with pytest.raises(ValueError, match="reserved"):
        validate_fragment(forged, manifest, report)


def test_relationships_keep_divergent_heads_and_select_all_descendants():
    manifest = make_manifest()
    fragment_id = manifest.reservation(KERNEL, 1).fragment_id
    first = make_record(manifest, fragment_id)
    second = make_record(manifest, fragment_id, 2, relationship="responds", parents=(first.record_id,), created="2026-09-06T12:03:00Z", no_related_thread=False)
    third = make_record(manifest, fragment_id, 3, relationship="challenges", parents=(first.record_id,), created="2026-09-06T12:04:00Z", no_related_thread=False)
    fragment = make_fragment(manifest, [first, second, third])
    validate_relationships([fragment], manifest)
    reports = reports_for(manifest)
    assert {record.record_id for record in live_heads([fragment], manifest, reports=reports)[CHAIN]} == {first.record_id, second.record_id, third.record_id}
    assert {record.record_id for record in common_view([fragment], manifest, reports=reports, responds_to=first.record_id, transitive=True)} == {second.record_id, third.record_id}
    bad = make_record(manifest, fragment_id, 2, relationship="orphan", parents=(first.record_id,), created="2026-09-06T12:03:00Z")
    with pytest.raises(ValueError, match="orphan"):
        validate_relationships([make_fragment(manifest, [first, bad])], manifest)


def test_close_and_expiry_require_independent_coverage_and_closed_at_window(tmp_path):
    reviewer = "ledger-auditor"
    manifest = make_manifest(people=(
        (KERNEL, "worker", BRANCH, TRACK),
        (reviewer, "validator", "codex/feature/reflection-ledger-audit", "verification"),
        ("codex-orchestrator", "orchestrator", "codex/feature/reflection-ledger-integration", "integration"),
    ))
    worker_record = make_record(manifest, manifest.reservation(KERNEL, 1).fragment_id)
    worker_fragment = make_fragment(manifest, [worker_record])
    reviewer_record = make_record(manifest, manifest.reservation(reviewer, 1).fragment_id, ordinal=1, relationship="responds", parents=(worker_record.record_id,), created="2026-09-06T12:03:00Z", no_related_thread=False)
    reviewer_fragment = make_fragment(manifest, [reviewer_record], participant=reviewer, branch="codex/feature/reflection-ledger-audit", track="verification")
    orch_record = make_record(manifest, manifest.reservation("codex-orchestrator", 1).fragment_id, ordinal=1, kind="resolution", relationship="responds", parents=(reviewer_record.record_id,), created="2026-09-06T12:04:00Z", no_related_thread=False)
    orch_fragment = make_fragment(manifest, [orch_record], participant="codex-orchestrator", branch="codex/feature/reflection-ledger-integration", track="integration")
    receipt = ReflectionReceipt("rrc_0123456789abcdefghjk", PLAN, CHAIN, (worker_record.record_id, reviewer_record.record_id, orch_record.record_id),
                                (worker_record.record_id, reviewer_record.record_id, orch_record.record_id), "Settled.", "already-covered", (), "2026-09-06T12:05:00Z", "sha256:" + "c" * 64)
    assert parse_receipt(render_receipt(receipt)) == receipt
    close = ReflectionChainClose(CHAIN, "2026-09-06T12:06:00Z", 7, "2026-09-13T12:06:00Z", (worker_record.record_id,), (reviewer_record.record_id,),
                                 (orch_record.record_id,), orch_record.record_id, (worker_record.record_id, reviewer_record.record_id, orch_record.record_id), (), "validation:ok", (receipt.receipt_id,), "closeout.md")
    _root, admitted, git_close = admitted_for(tmp_path, manifest, [worker_fragment, reviewer_fragment, orch_fragment], close)
    validate_chain_close(git_close, admitted, [receipt])
    assert eligible_expiry_paths([git_close], admitted, [receipt], now=datetime(2026, 9, 13, 12, 6, tzinfo=timezone.utc)) == (git_close.closeout_path,)
    assert eligible_expiry_paths([git_close], admitted, [receipt], now=datetime(2026, 9, 13, 12, 5, tzinfo=timezone.utc)) == ()
    assert parse_closeout(render_closeout(PLAN, [close])) == (PLAN, (close,))


def test_admissible_views_refuse_missing_reports_forged_fragments_and_path_aliases():
    manifest = make_manifest()
    fragment_id = manifest.reservation(KERNEL, 1).fragment_id
    fragment = make_fragment(manifest, [make_record(manifest, fragment_id)])
    with pytest.raises(ValueError, match="admitted reports"):
        common_view([fragment], manifest)
    forged_record = replace(fragment.records[0], record_id="rlr_0123456789abcdefghjk")
    with pytest.raises(ValueError, match="does not match deterministic"):
        common_view([replace(fragment, records=(forged_record,))], manifest, reports=reports_for(manifest))
    with pytest.raises(ValueError, match="clean relative"):
        parse_manifest(render_manifest(manifest).replace("reports/kernel/", "reports//kernel/"))


def test_close_parser_and_validation_refuse_retention_and_topology_shortcuts(tmp_path):
    reviewer = "ledger-auditor"
    manifest = make_manifest(people=(
        (KERNEL, "worker", BRANCH, TRACK),
        (reviewer, "validator", "codex/feature/reflection-ledger-audit", "verification"),
        ("codex-orchestrator", "orchestrator", "codex/feature/reflection-ledger-integration", "integration"),
    ))
    worker = make_record(manifest, manifest.reservation(KERNEL, 1).fragment_id)
    reviewer_record = make_record(manifest, manifest.reservation(reviewer, 1).fragment_id, relationship="responds", parents=(worker.record_id,), created="2026-09-06T12:03:00Z", no_related_thread=False)
    orchestrator = make_record(manifest, manifest.reservation("codex-orchestrator", 1).fragment_id, kind="resolution", relationship="responds", parents=(reviewer_record.record_id,), created="2026-09-06T12:04:00Z", no_related_thread=False)
    fragments = (
        make_fragment(manifest, [worker]),
        make_fragment(manifest, [reviewer_record], participant=reviewer, branch="codex/feature/reflection-ledger-audit", track="verification"),
        make_fragment(manifest, [orchestrator], participant="codex-orchestrator", branch="codex/feature/reflection-ledger-integration", track="integration"),
    )
    receipt = ReflectionReceipt("rrc_0123456789abcdefghjk", PLAN, CHAIN, (worker.record_id, reviewer_record.record_id, orchestrator.record_id),
                                (worker.record_id, reviewer_record.record_id, orchestrator.record_id), "Settled.", "expired-unpromoted", (), "2026-09-06T12:05:00Z", "sha256:" + "c" * 64)
    close = ReflectionChainClose(CHAIN, "2026-09-06T12:06:00Z", 7, "2026-09-13T12:06:00Z", (worker.record_id,), (reviewer_record.record_id,),
                                 (orchestrator.record_id,), orchestrator.record_id, (worker.record_id, reviewer_record.record_id, orchestrator.record_id), (), "validation:ok", (receipt.receipt_id,))
    _root, admitted, git_close = admitted_for(tmp_path, manifest, fragments, close)
    with pytest.raises(ValueError, match="Git-admitted closeout"):
        validate_chain_close(close, admitted, [receipt])
    with pytest.raises(ValueError, match="Git-admitted reflection documents"):
        validate_chain_close(git_close, fragments, [receipt])
    with pytest.raises(ValueError, match="immutable Git tree"):
        validate_chain_close(replace(git_close, closeout_oid="0" * 40), admitted, [receipt])
    forged_record = replace(worker, conclusion="Agent supplied a different conclusion.")
    fabricated_canonical_fragment = parse_fragment(render_fragment(replace(fragments[0], records=(forged_record,))))
    forged_documents = replace(admitted, fragments=(fabricated_canonical_fragment,) + fragments[1:])
    with pytest.raises(ValueError, match="immutable Git tree"):
        validate_chain_close(git_close, forged_documents, [receipt])
    _root, bad_retention_admitted, bad_retention_close = admitted_for(tmp_path, manifest, fragments, replace(close, retention_days=6, expires_at="2026-09-12T12:06:00Z"))
    with pytest.raises(ValueError, match="manifest policy"):
        validate_chain_close(bad_retention_close, bad_retention_admitted, [receipt])
    with pytest.raises(ValueError, match="positive integer"):
        parse_closeout(render_closeout(PLAN, [close]).replace("retention_days: 7", "retention_days: seven"))
    unrelated = make_record(manifest, manifest.reservation("codex-orchestrator", 1).fragment_id, kind="resolution")
    unrelated_fragment = make_fragment(manifest, [unrelated], participant="codex-orchestrator", branch="codex/feature/reflection-ledger-integration", track="integration")
    unrelated_close = replace(close, orchestrator_record_ids=(unrelated.record_id,), synthesis_record_id=unrelated.record_id,
                              resolved_head_ids=(worker.record_id, reviewer_record.record_id, unrelated.record_id))
    _root, unrelated_admitted, unrelated_git_close = admitted_for(tmp_path, manifest, fragments[:2] + (unrelated_fragment,), unrelated_close)
    with pytest.raises(ValueError, match="not connected to reviewer"):
        validate_chain_close(unrelated_git_close, unrelated_admitted, [receipt])


class AlwaysTrueAgentVerifier:
    def verify_reflection_expiry(self, *args, **kwargs):
        return True


def host_sign_for_test(seed, message):
    """Test-only trusted-host signer; production code has verification only."""
    prime = 2**255 - 19
    order = 2**252 + 27742317777372353535851937790883648493
    curve_d = (-121665 * pow(121666, prime - 2, prime)) % prime
    base_y = (4 * pow(5, prime - 2, prime)) % prime
    base_x_squared = ((base_y * base_y - 1) * pow(curve_d * base_y * base_y + 1, prime - 2, prime)) % prime
    base_x = pow(base_x_squared, (prime + 3) // 8, prime)
    if base_x & 1:
        base_x = prime - base_x

    def add(left, right):
        x1, y1 = left
        x2, y2 = right
        dx = pow((1 + curve_d * x1 * x2 * y1 * y2) % prime, prime - 2, prime)
        dy = pow((1 - curve_d * x1 * x2 * y1 * y2) % prime, prime - 2, prime)
        return ((x1 * y2 + x2 * y1) * dx % prime, (y1 * y2 + x1 * x2) * dy % prime)

    def multiply(point, scalar):
        total = (0, 1)
        while scalar:
            if scalar & 1:
                total = add(total, point)
            point = add(point, point)
            scalar >>= 1
        return total

    def encode(point):
        x, y = point
        return (y | ((x & 1) << 255)).to_bytes(32, "little")

    digest = sha512(seed).digest()
    scalar = int.from_bytes(bytes([digest[0] & 248]) + digest[1:31] + bytes([(digest[31] & 63) | 64]), "little")
    nonce = int.from_bytes(sha512(digest[32:] + message).digest(), "little") % order
    encoded_r = encode(multiply((base_x, base_y), nonce))
    public_key = encode(multiply((base_x, base_y), scalar))
    challenge = int.from_bytes(sha512(encoded_r + public_key + message).digest(), "little") % order
    return public_key, encoded_r + ((nonce + challenge * scalar) % order).to_bytes(32, "little")


def signed_approval(signing_seed, manifest, close, member_ids):
    unsigned = EarlyExpiryApprovalReceipt(
        TEST_APPROVAL_KEY_ID, manifest.plan_id, close.chain_id, tuple(member_ids), "User approved early cleanup.",
        "2026-09-07T12:06:00Z", close.expires_at, "ed25519:" + "0" * 128,
    )
    _public_key, signature = host_sign_for_test(signing_seed, early_expiry_approval_payload(unsigned))
    signed = replace(unsigned, signature="ed25519:" + signature.hex())
    return render_early_expiry_approval(signed)


def test_early_expiry_needs_verified_host_receipt_and_a_valid_complete_close(tmp_path):
    reviewer = "ledger-auditor"
    signing_seed = secrets.token_bytes(32)
    public_key, _signature = host_sign_for_test(signing_seed, b"")
    manifest = make_manifest(people=(
        (KERNEL, "worker", BRANCH, TRACK),
        (reviewer, "validator", "codex/feature/reflection-ledger-audit", "verification"),
        ("codex-orchestrator", "orchestrator", "codex/feature/reflection-ledger-integration", "integration"),
    ), early_expiry_approval_public_key="ed25519:" + public_key.hex())
    worker = make_record(manifest, manifest.reservation(KERNEL, 1).fragment_id)
    reviewer_record = make_record(manifest, manifest.reservation(reviewer, 1).fragment_id, relationship="responds", parents=(worker.record_id,), created="2026-09-06T12:03:00Z", no_related_thread=False)
    orchestrator = make_record(manifest, manifest.reservation("codex-orchestrator", 1).fragment_id, kind="resolution", relationship="responds", parents=(reviewer_record.record_id,), created="2026-09-06T12:04:00Z", no_related_thread=False)
    fragments = (make_fragment(manifest, [worker]), make_fragment(manifest, [reviewer_record], participant=reviewer, branch="codex/feature/reflection-ledger-audit", track="verification"), make_fragment(manifest, [orchestrator], participant="codex-orchestrator", branch="codex/feature/reflection-ledger-integration", track="integration"))
    receipt = ReflectionReceipt("rrc_0123456789abcdefghjk", PLAN, CHAIN, (worker.record_id, reviewer_record.record_id, orchestrator.record_id), (worker.record_id, reviewer_record.record_id, orchestrator.record_id), "Settled.", "expired-unpromoted", (), "2026-09-06T12:05:00Z", "sha256:" + "c" * 64)
    close = ReflectionChainClose(CHAIN, "2026-09-06T12:06:00Z", 7, "2026-09-13T12:06:00Z", (worker.record_id,), (reviewer_record.record_id,), (orchestrator.record_id,), orchestrator.record_id, (worker.record_id, reviewer_record.record_id, orchestrator.record_id), (), "validation:ok", (receipt.receipt_id,))
    _root, admitted, git_close = admitted_for(tmp_path, manifest, fragments, close)
    now = datetime(2026, 9, 7, 12, 6, tzinfo=timezone.utc)
    member_ids = (worker.record_id, reviewer_record.record_id, orchestrator.record_id)
    with pytest.raises(ValueError, match="canonical signed approval"):
        eligible_expiry_paths([git_close], admitted, [receipt], now=now, chain=CHAIN, early=True)
    with pytest.raises(ValueError, match="canonical signed approval"):
        eligible_expiry_paths([git_close], admitted, [receipt], now=now, chain=CHAIN, early=True, approval_receipt=AlwaysTrueAgentVerifier())
    with pytest.raises(ValueError, match="canonical signed approval"):
        eligible_expiry_paths(
            [git_close], admitted, [receipt], now=now, chain=CHAIN, early=True,
            approval_receipt=EarlyExpiryApprovalReceipt(TEST_APPROVAL_KEY_ID, PLAN, CHAIN, member_ids, "forged", "2026-09-07T12:06:00Z", git_close.close.expires_at, "ed25519:" + "0" * 128),
        )
    valid_approval = signed_approval(signing_seed, manifest, git_close.close, member_ids)
    tampered_approval = valid_approval[:-2] + ("0" if valid_approval[-2] != "0" else "1") + "\n"
    with pytest.raises(ValueError, match="does not verify"):
        eligible_expiry_paths([git_close], admitted, [receipt], now=now, chain=CHAIN, early=True, approval_receipt=tampered_approval)
    assert eligible_expiry_paths([git_close], admitted, [receipt], now=now, chain=CHAIN, early=True, approval_receipt=valid_approval) == (git_close.closeout_path,)
    with pytest.raises(ValueError, match="unavailable durable receipt"):
        _root, bad_admitted, bad_close = admitted_for(tmp_path, manifest, fragments, replace(close, receipt_ids=("rrc_1123456789abcdefghjk",)))
        eligible_expiry_paths([bad_close], bad_admitted, [receipt], now=now, chain=CHAIN, early=True, approval_receipt=signed_approval(signing_seed, manifest, bad_close.close, member_ids))


class TestFuse:
    def _git(self, cwd, *args):
        return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True)

    def _project(self):
        path = Path(tempfile.mkdtemp(prefix="reflection-ledger-test-"))
        self._git(path, "init", "-q")
        self._git(path, "config", "user.name", "Test")
        self._git(path, "config", "user.email", "test@example.com")
        self._git(path, "branch", "-M", "main")
        return path

    def _prepared_pair(self, record):
        cwd = self._project()
        (cwd / "bootstrap.txt").write_text("base\n", encoding="utf-8")
        self._git(cwd, "add", "-A")
        self._git(cwd, "commit", "-qm", "bootstrap")
        manifest = make_manifest(base_sha=self._git(cwd, "rev-parse", "HEAD").stdout.strip())
        base = cwd / REFLECTION_ROOT / PLAN
        base.mkdir(parents=True)
        (base / "manifest.yaml").write_text(render_manifest(manifest), encoding="utf-8")
        self._git(cwd, "add", "-A")
        self._git(cwd, "commit", "-qm", "manifest")
        self._git(cwd, "switch", "-qc", BRANCH)
        reservation = manifest.reservation(KERNEL, 1)
        (base / reservation.report_path).parent.mkdir(parents=True, exist_ok=True)
        (base / reservation.report_path).write_text(render_report(make_report(manifest)), encoding="utf-8")
        (base / reservation.fragment_path).parent.mkdir(parents=True, exist_ok=True)
        (base / reservation.fragment_path).write_text(render_fragment(make_fragment(manifest, [record])), encoding="utf-8")
        self._git(cwd, "add", "-A")
        self._git(cwd, "commit", "-qm", "reflection pair")
        self._git(cwd, "switch", "main")
        return cwd, manifest

    def test_fuse_accepts_only_reserved_canonical_pair(self):
        cwd = self._project()
        try:
            (cwd / "bootstrap.txt").write_text("base\n", encoding="utf-8")
            self._git(cwd, "add", "-A")
            self._git(cwd, "commit", "-qm", "bootstrap")
            manifest = make_manifest(base_sha=self._git(cwd, "rev-parse", "HEAD").stdout.strip())
            base = cwd / REFLECTION_ROOT / PLAN
            base.mkdir(parents=True)
            (base / "manifest.yaml").write_text(render_manifest(manifest), encoding="utf-8")
            self._git(cwd, "add", "-A")
            self._git(cwd, "commit", "-qm", "manifest")
            self._git(cwd, "switch", "-qc", BRANCH)
            reservation = manifest.reservation(KERNEL, 1)
            report = make_report(manifest)
            fragment = make_fragment(manifest, [make_record(manifest, reservation.fragment_id)])
            (base / reservation.report_path).parent.mkdir(parents=True, exist_ok=True)
            (base / reservation.report_path).write_text(render_report(report), encoding="utf-8")
            (base / reservation.fragment_path).parent.mkdir(parents=True, exist_ok=True)
            (base / reservation.fragment_path).write_text(render_fragment(fragment), encoding="utf-8")
            self._git(cwd, "add", "-A")
            self._git(cwd, "commit", "-qm", "reflection pair")
            self._git(cwd, "switch", "main")
            result = reflection_fuse(cwd, plan_id=PLAN, branch=BRANCH)
            assert result.issues == []
            assert sorted(result.planned_paths) == sorted([f"{REFLECTION_ROOT}/{PLAN}/{reservation.report_path}", f"{REFLECTION_ROOT}/{PLAN}/{reservation.fragment_path}"])
        finally:
            shutil.rmtree(cwd, ignore_errors=True)

    def test_fuse_admission_rejects_a_dangling_parent(self):
        manifest = make_manifest()
        record = make_record(manifest, manifest.reservation(KERNEL, 1).fragment_id, relationship="responds", parents=("rlr_0123456789abcdefghjk",), no_related_thread=False)
        cwd, _manifest = self._prepared_pair(record)
        try:
            result = reflection_fuse(cwd, plan_id=PLAN, branch=BRANCH)
            assert result.issues and result.issues[0].code == "dangling-parent"
        finally:
            shutil.rmtree(cwd, ignore_errors=True)

    def test_internal_apply_rechecks_base_tip_and_manifest_state(self):
        manifest = make_manifest()
        record = make_record(manifest, manifest.reservation(KERNEL, 1).fragment_id)
        cwd, _manifest = self._prepared_pair(record)
        try:
            preview = reflection_fuse(cwd, plan_id=PLAN, branch=BRANCH)
            assert preview.issues == [] and preview._plan is not None
            (cwd / "base-toctou.txt").write_text("changed\n", encoding="utf-8")
            self._git(cwd, "add", "-A")
            self._git(cwd, "commit", "-qm", "advance base")
            applied = _apply_reflection_fuse_plan(cwd, preview._plan, preview_token=preview.preview_token)
            assert applied.issues and applied.issues[0].code == "base-tip"
        finally:
            shutil.rmtree(cwd, ignore_errors=True)

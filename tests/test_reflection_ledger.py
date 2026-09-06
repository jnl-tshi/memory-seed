from __future__ import annotations

from datetime import datetime, timezone
from dataclasses import replace
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest

from memory_seed.reflection_ledger import (
    REFLECTION_ROOT,
    ReflectionChainClose,
    ReflectionFragment,
    LiveUserExpiryApproval,
    ReflectionManifest,
    ReflectionParticipant,
    ReflectionReceipt,
    ReflectionRecord,
    ReflectionReport,
    ReflectionReservation,
    _apply_reflection_fuse_plan,
    admit_reflection_documents,
    canonical_id,
    common_view,
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


def make_manifest(*, base_sha=BASE, state="active", people=None):
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
                                     {"participant": orchestrator.participant, "branch": orchestrator.branch}, tuple(participants))
    return ReflectionManifest(PLAN, "main", base_sha, state, provisional.created_at, 7, "sha256-crockford-v1", SEED,
                              participants_seal(provisional), provisional.orchestrator, provisional.participants)


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


def admitted_for(manifest, fragments):
    documents = {}
    for fragment in fragments:
        reservation = manifest.reservation(fragment.participant, fragment.sequence)
        documents[f"{manifest.active_dir}/{reservation.report_path}"] = render_report(
            make_report(manifest, fragment.participant, branch=fragment.working_branch, track=fragment.track)
        )
        documents[f"{manifest.active_dir}/{reservation.fragment_path}"] = render_fragment(fragment)
    return admit_reflection_documents(manifest, documents)


def admitted_close(manifest, close):
    plan_id, closes = parse_closeout(render_closeout(manifest.plan_id, [close]))
    assert plan_id == manifest.plan_id
    assert len(closes) == 1
    return closes[0]


def test_ids_match_published_vectors_and_reject_forgery():
    assert reservation_id("rpr_", SEED, PLAN, KERNEL, TRACK, 1, "report") == "rpr_14fyc35b2ze6e1ygw4ft"
    assert reservation_id("rfl_", SEED, PLAN, KERNEL, TRACK, 1, "fragment") == "rfl_14h1h37xrrp19qb9s1kd"
    assert record_id(SEED, "rfl_14h1h37xrrp19qb9s1kd", 1) == "rlr_1an0dh39bsnjxfnpqtqh"
    assert record_id(SEED, "rfl_14h1h37xrrp19qb9s1kd", 2) == "rlr_0v66ws242aeshw23ppwr"
    assert canonical_id("rrc_", SEED, "x") != canonical_id("rrc_", SEED, "y")


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


def test_close_and_expiry_require_independent_coverage_and_closed_at_window():
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
    admitted = admitted_for(manifest, [worker_fragment, reviewer_fragment, orch_fragment])
    close = admitted_close(manifest, close)
    validate_chain_close(close, admitted, manifest, [receipt])
    assert eligible_expiry_paths([close], admitted, manifest, [receipt], now=datetime(2026, 9, 13, 12, 6, tzinfo=timezone.utc)) == ("closeout.md",)
    assert eligible_expiry_paths([close], admitted, manifest, [receipt], now=datetime(2026, 9, 13, 12, 5, tzinfo=timezone.utc)) == ()
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


def test_close_parser_and_validation_refuse_retention_and_topology_shortcuts():
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
    admitted = admitted_for(manifest, fragments)
    with pytest.raises(ValueError, match="canonically parsed closeout"):
        validate_chain_close(close, admitted, manifest, [receipt])
    close = admitted_close(manifest, close)
    with pytest.raises(ValueError, match="canonically admitted reflection documents"):
        validate_chain_close(close, fragments, manifest, [receipt])
    forged_record = replace(worker, conclusion="Agent supplied a different conclusion.")
    forged_documents = replace(admitted, fragments=(replace(fragments[0], records=(forged_record,)),) + fragments[1:])
    with pytest.raises(ValueError, match="differ from their canonical bytes"):
        validate_chain_close(close, forged_documents, manifest, [receipt])
    with pytest.raises(ValueError, match="manifest policy"):
        validate_chain_close(admitted_close(manifest, replace(close, retention_days=6, expires_at="2026-09-12T12:06:00Z")), admitted, manifest, [receipt])
    with pytest.raises(ValueError, match="differs from its admitted canonical bytes"):
        validate_chain_close(replace(close, retention_days=6, expires_at="2026-09-12T12:06:00Z"), admitted, manifest, [receipt])
    with pytest.raises(ValueError, match="positive integer"):
        parse_closeout(render_closeout(PLAN, [close]).replace("retention_days: 7", "retention_days: seven"))
    unrelated = make_record(manifest, manifest.reservation("codex-orchestrator", 1).fragment_id, kind="resolution")
    unrelated_fragment = make_fragment(manifest, [unrelated], participant="codex-orchestrator", branch="codex/feature/reflection-ledger-integration", track="integration")
    unrelated_close = replace(close, orchestrator_record_ids=(unrelated.record_id,), synthesis_record_id=unrelated.record_id,
                              resolved_head_ids=(worker.record_id, reviewer_record.record_id, unrelated.record_id))
    with pytest.raises(ValueError, match="not connected to reviewer"):
        validate_chain_close(admitted_close(manifest, unrelated_close), admitted_for(manifest, fragments[:2] + (unrelated_fragment,)), manifest, [receipt])


class AlwaysTrueAgentVerifier:
    def verify_reflection_expiry(self, *args, **kwargs):
        return True


def test_early_expiry_needs_host_verification_and_a_valid_complete_close():
    reviewer = "ledger-auditor"
    manifest = make_manifest(people=(
        (KERNEL, "worker", BRANCH, TRACK),
        (reviewer, "validator", "codex/feature/reflection-ledger-audit", "verification"),
        ("codex-orchestrator", "orchestrator", "codex/feature/reflection-ledger-integration", "integration"),
    ))
    worker = make_record(manifest, manifest.reservation(KERNEL, 1).fragment_id)
    reviewer_record = make_record(manifest, manifest.reservation(reviewer, 1).fragment_id, relationship="responds", parents=(worker.record_id,), created="2026-09-06T12:03:00Z", no_related_thread=False)
    orchestrator = make_record(manifest, manifest.reservation("codex-orchestrator", 1).fragment_id, kind="resolution", relationship="responds", parents=(reviewer_record.record_id,), created="2026-09-06T12:04:00Z", no_related_thread=False)
    fragments = (make_fragment(manifest, [worker]), make_fragment(manifest, [reviewer_record], participant=reviewer, branch="codex/feature/reflection-ledger-audit", track="verification"), make_fragment(manifest, [orchestrator], participant="codex-orchestrator", branch="codex/feature/reflection-ledger-integration", track="integration"))
    receipt = ReflectionReceipt("rrc_0123456789abcdefghjk", PLAN, CHAIN, (worker.record_id, reviewer_record.record_id, orchestrator.record_id), (worker.record_id, reviewer_record.record_id, orchestrator.record_id), "Settled.", "expired-unpromoted", (), "2026-09-06T12:05:00Z", "sha256:" + "c" * 64)
    close = ReflectionChainClose(CHAIN, "2026-09-06T12:06:00Z", 7, "2026-09-13T12:06:00Z", (worker.record_id,), (reviewer_record.record_id,), (orchestrator.record_id,), orchestrator.record_id, (worker.record_id, reviewer_record.record_id, orchestrator.record_id), (), "validation:ok", (receipt.receipt_id,))
    admitted = admitted_for(manifest, fragments)
    close = admitted_close(manifest, close)
    now = datetime(2026, 9, 7, 12, 6, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="sealed trusted-host approval"):
        eligible_expiry_paths([close], admitted, manifest, [receipt], now=now, chain=CHAIN, early=True)
    with pytest.raises(ValueError, match="sealed trusted-host approval"):
        eligible_expiry_paths([close], admitted, manifest, [receipt], now=now, chain=CHAIN, early=True, approval=AlwaysTrueAgentVerifier())
    with pytest.raises(TypeError, match="issued only by the trusted"):
        LiveUserExpiryApproval(object(), "agent-forged", PLAN, CHAIN, (worker.record_id,), close.expires_at)
    with pytest.raises(ValueError, match="unavailable durable receipt"):
        eligible_expiry_paths([admitted_close(manifest, replace(close, receipt_ids=("rrc_1123456789abcdefghjk",)))], admitted, manifest, [receipt], now=now, chain=CHAIN, early=True)


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

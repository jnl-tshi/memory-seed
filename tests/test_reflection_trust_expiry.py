"""Adversarial retirement authority and shared public/hook admission."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from memory_seed import reflection_ledger as ledger
from memory_seed.cli import main
from memory_seed.mcp_server import TOOLS, call_tool
from memory_seed.reflection_operations import run_reflection_operation as operate
from test_reflection_workstream_ledger import _git, _session_entry, _transaction_state


START = datetime(2026, 1, 1, tzinfo=timezone.utc)
SOURCE = Path(__file__).resolve().parents[1]


def _root(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "--quiet", "--initial-branch=main")
    _git(root, "config", "user.name", "Reflection test")
    _git(root, "config", "user.email", "reflection@example.test")
    _git(root, "config", "core.autocrlf", "false")
    (root / ".memory-seed/sessions").mkdir(parents=True)
    (root / ".memory-seed/sessions/.gitkeep").write_bytes(b"")
    (root / ".gitattributes").write_bytes(b"* text=auto eol=lf\n.memory-seed/reflections/active/** -merge\n")
    _git(root, "add", ".")
    _git(root, "commit", "--quiet", "-m", "base")
    return root


def _commit_receipts(root, workstream, chain, *, closure=False):
    loaded = ledger.load_trusted_workstream_ledger(root, trusted_ref="main", ledger_path=ledger.workstream_ledger_path(workstream))
    entry_id = "mse_0123456789abcde" + ("f" if closure else "0")
    relative = ".memory-seed/sessions/2026-01/2026-01-0" + ("2.md" if closure else "1.md")
    drafts = ledger.plan_workstream_chain_receipts(loaded, chain_id=chain, session_path=relative,
        entry_id=entry_id, decision_id="D1", disposition="expired-unpromoted")
    mappings = tuple(ledger.workstream_receipt_mapping(item) for item in drafts)
    if closure:
        mappings += (ledger.workstream_closure_mapping(loaded.ledger.records[-1], session_path=relative,
            entry_id=entry_id, decision_id="D1"),)
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_session_entry("2026-01-02 12:00 - Receipt evidence", entry_id, mappings), encoding="utf-8")
    _git(root, "add", relative)
    _git(root, "commit", "--quiet", "-m", "durable receipts")
    return dict(session_path=relative, entry_id=entry_id, decision_id="D1", disposition="expired-unpromoted")


@pytest.fixture(scope="module")
def expiry_template(tmp_path_factory):
    root = _root(tmp_path_factory.mktemp("expiry-template"))
    assert ledger.reflection_trust_init(root, apply=True)["applied"]
    _git(root, "checkout", "--quiet", "-b", "feature")
    init = ledger.preview_workstream_init_commit(root, trusted_ref="feature", clock=lambda: START)
    result = ledger.apply_workstream_commit(root, init)
    workstream = result.ledger.header.workstream_id
    chain = None
    for index, role in enumerate(("planner", "planner", "implementer", "reviewer")):
        request = ledger.WorkstreamAppendRequest(role, chain, "no_related_thread" if index == 0 else "refines",
            () if index == 0 else (result.ledger.records[-1].record_id,), index == 0,
            "conclusion", "reasoning", "test", "high", to_phase="orchestrate" if index == 3 else None)
        result = ledger.apply_workstream_commit(root, ledger.preview_workstream_append_commit(root,
            trusted_ref="feature", workstream_id=workstream, request=request, clock=lambda: START))
        chain = result.ledger.records[-1].chain_id
    _git(root, "checkout", "--quiet", "main")
    _git(root, "merge", "--quiet", "--no-ff", "-m", "integrate", "feature")
    rebound = operate("ledger_rebind", dict(cwd=str(root), workstream_id=workstream, source="feature", reason="integrate", apply=True))
    assert rebound["ok"], rebound
    locator = _commit_receipts(root, workstream, chain)
    loaded = ledger.load_trusted_workstream_ledger(root, trusted_ref="main", ledger_path=init.ledger_path)
    integration = ledger.GitWorkstreamIntegrationVerifier(loaded)
    witness = integration.witness()
    receipts = ledger.admit_workstream_chain_receipts(loaded, chain_id=chain, **locator,
        session_ref="HEAD", integration_witness=witness, integration_verifier=integration)
    preview = ledger.preview_workstream_close_commit(root, trusted_ref="main", workstream_id=workstream,
        chain_id=chain, receipts=receipts, receipt_verifier=ledger.GitWorkstreamReceiptVerifier(loaded, witness.integration_commit),
        integration_witness=witness, integration_verifier=integration, conclusion="closed", reasoning="synthesized",
        source="test", confidence="high", clock=lambda: START + timedelta(minutes=1))
    original_clock = ledger._clock_timestamp
    with pytest.MonkeyPatch.context() as host:
        host.setattr(ledger, "_clock_timestamp", lambda clock=None: original_clock(clock or (lambda: START + timedelta(minutes=1))))
        ledger.apply_workstream_commit(root, preview)
    _commit_receipts(root, workstream, chain, closure=True)
    return root, workstream, chain


@pytest.fixture
def ready(tmp_path, expiry_template):
    template, workstream, chain = expiry_template
    root = tmp_path / "repo"
    shutil.copytree(template, root)
    return root, dict(cwd=str(root), workstream_id=workstream, chain_id=chain)


def test_signer_matches_rfc8032_vector():
    seed = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    public, signature = ledger._ed25519_sign(seed, b"")
    assert public.hex() == "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    assert signature.hex() == ("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155"
        "5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
    assert ledger.ed25519_verify(public, b"", signature)


def test_trust_bootstrap_preview_apply_idempotence_and_cli_only(tmp_path, monkeypatch, capsys):
    root = _root(tmp_path)
    before = _transaction_state(root)
    monkeypatch.chdir(root)
    assert main(["reflection", "trust", "init", "--json"]) == 0
    assert not json.loads(capsys.readouterr().out)["applied"]
    assert _transaction_state(root) == before
    assert not ledger._retention_key_path(root).exists()
    assert main(["reflection", "trust", "init", "--apply", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["applied"] and payload["initialized"]
    assert _git(root, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD") == ledger.RETENTION_TRUST_PATH
    assert "ed25519.seed" not in _git(root, "ls-files")
    assert ledger._retention_key_path(root).is_relative_to(ledger._rebind_common_directory(root))
    assert not ledger.reflection_trust_init(root, apply=True)["applied"]
    assert not any(tool["name"].startswith("memory_reflection_trust") for tool in TOOLS)
    _git(root, "checkout", "--quiet", "-b", "feature")
    with pytest.raises(ledger.ReflectionValidationError, match="integration/default"):
        ledger.reflection_trust_init(root, apply=True)


@pytest.mark.parametrize("field", ["now", "timestamp", "signature", "attestation", "approval", "early", "receipt", "token", "expected_head"])
def test_caller_authority_rejected_identically(field):
    args = dict(workstream_id="invalid", chain_id="invalid", **{field: "forged"})
    result = call_tool("memory_reflection_ledger_expire", args)
    assert result == operate("ledger_expire", args)
    assert result["error"]["code"] == "invalid_arguments"


@pytest.mark.parametrize("apply", ["false", 1, None])
def test_expiry_boolean_is_strict(apply):
    assert not call_tool("memory_reflection_ledger_expire", dict(workstream_id="w", chain_id="c", apply=apply))["ok"]


@pytest.mark.parametrize("option", ["--early", "--now", "--timestamp", "--signature", "--approval", "--attestation"])
def test_cli_has_no_early_or_authority_options(option):
    with pytest.raises(SystemExit) as exc:
        main(["reflection", "ledger", "expire", "w", "--chain-id", "c", option])
    assert exc.value.code == 2


def test_expiry_preview_cli_mcp_parity_and_one_cas(ready, monkeypatch, capsys):
    root, args = ready
    before = _transaction_state(root)
    expected = call_tool("memory_reflection_ledger_expire", args)
    assert expected["ok"], expected
    monkeypatch.chdir(root)
    assert main(["reflection", "ledger", "expire", args["workstream_id"], "--chain-id", args["chain_id"], "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == expected
    assert _transaction_state(root) == before
    updates, original = [], ledger._git

    def track(root, *argv, **kwargs):
        if argv[0] == "update-ref":
            updates.append(argv)
        return original(root, *argv, **kwargs)

    monkeypatch.setattr(ledger, "_git", track)
    applied = call_tool("memory_reflection_ledger_expire", dict(args, apply=True))
    assert applied["ok"] and applied["applied"], applied
    assert len(updates) == 1
    assert _git(root, "rev-list", "--count", expected["head"] + "..HEAD") == "2"
    assert _git(root, "status", "--porcelain") == ""
    loaded = ledger.load_trusted_workstream_ledger(root, trusted_ref="main", ledger_path=ledger.workstream_ledger_path(args["workstream_id"]))
    assert isinstance(loaded, ledger.AdmittedCompactedLedger)
    assert not loaded.ledger.records and len(loaded.proofs) == 1
    assert "not cryptographic erasure" in applied["disclosure"]
    assert "garbage collection" in applied["disclosure"]


@pytest.mark.parametrize("point", ["before-commit", "after-cleanup-commit", "after-receipt-commit", "before-cas"])
def test_expiry_partial_transaction_failure_has_no_visible_state(ready, point):
    root, args = ready
    before = _transaction_state(root)
    plan = ledger.preview_workstream_expiry_commit(root, trusted_ref="main", workstream_id=args["workstream_id"], chain_id=args["chain_id"])

    def fault(stage):
        if stage == point:
            raise RuntimeError("injected transaction interruption")

    with pytest.raises(ledger.ReflectionValidationError):
        ledger.apply_workstream_commit(root, plan, fault_injector=fault)
    assert _transaction_state(root) == before


def test_git_dates_cannot_make_retention_elapsed(ready, monkeypatch):
    root, args = ready
    original = ledger._clock_timestamp
    monkeypatch.setattr(ledger, "_clock_timestamp", lambda clock=None: original(clock or (lambda: START + timedelta(days=1))))
    monkeypatch.setenv("GIT_AUTHOR_DATE", "2050-01-01T00:00:00Z")
    monkeypatch.setenv("GIT_COMMITTER_DATE", "2050-01-01T00:00:00Z")
    _git(root, "commit", "--allow-empty", "--quiet", "-m", "forged future Git dates")
    before = _transaction_state(root)
    result = operate("ledger_expire", dict(args, apply=True))
    assert not result["ok"] and "not elapsed" in result["error"]["message"]
    assert _transaction_state(root) == before


def test_mismatched_key_and_anchor_fail_without_replacement(ready):
    root, args = ready
    key = ledger._retention_key_path(root)
    key.write_bytes(bytes(32))
    before = _transaction_state(root)
    assert not operate("trust_init", dict(cwd=str(root), apply=True))["ok"]
    assert not operate("ledger_expire", dict(args, apply=True))["ok"]
    assert key.read_bytes() == bytes(32)
    assert _transaction_state(root) == before


@pytest.mark.parametrize("mutation", ["signature", "observed_at", "record_set", "integration", "receipt_origin"])
def test_signed_history_rejects_altered_bindings(ready, mutation):
    root, args = ready
    result = operate("ledger_expire", dict(args, apply=True))
    assert result["ok"], result
    path = ledger.workstream_ledger_path(args["workstream_id"])
    loaded = ledger.load_trusted_workstream_ledger(root, trusted_ref="main", ledger_path=path)
    proof = loaded.proofs[0]
    receipt = proof.receipt
    value = json.loads(receipt.elapsed_attestation)
    if mutation == "signature":
        value["signature"] = "ed25519:" + "0" * 128
    elif mutation == "observed_at":
        value["observed_at"] = "2050-01-01T00:00:00Z"
        value["expires_at"] = "2050-01-01T00:05:00Z"
    elif mutation == "integration":
        value["integration_commit"] = "0" * 40
    elif mutation == "record_set":
        receipt = replace(receipt, removed_record_ids=receipt.removed_record_ids[:-1])
    else:
        receipt = replace(receipt, member_receipts=(replace(receipt.member_receipts[0], commit=loaded.ledger.header.base_sha), *receipt.member_receipts[1:]))
    receipt = replace(receipt, elapsed_attestation=json.dumps(value))
    pre = ledger.load_trusted_workstream_ledger(root, trusted_ref=receipt.pre_tip, ledger_path=path)
    with pytest.raises(ledger.ReflectionValidationError):
        ledger._validate_historical_compaction_retention(root, receipt, pre.ledger, proof.receipt_commit, receipt.cleanup_commit)


def test_hook_rejects_manual_staging_and_forged_kernel_messages(ready):
    root, args = ready
    path = root / ledger.workstream_ledger_path(args["workstream_id"])
    path.write_bytes(path.read_bytes() + b"forged\n")
    _git(root, "add", str(path))
    message = root / ".git/COMMIT_EDITMSG"
    message.write_text("reflection: expiry\n\nReflection-Workstream: " + args["workstream_id"], encoding="utf-8")
    for hook in (SOURCE / ".memory-seed/hooks/prepare-commit-msg.py", SOURCE / "memory_seed/seed/.memory-seed/hooks/prepare-commit-msg.py"):
        process = subprocess.run([sys.executable, str(hook), str(message)], cwd=root, capture_output=True, text=True)
        assert process.returncode == 1
        assert "Refusing commit" in process.stderr
    assert not operate("commit_admission", dict(cwd=str(root)))["ok"]


@pytest.mark.parametrize("mutation", ["rotate", "alias", "delete_restore"])
def test_trust_history_rejects_rotation_alias_and_restoration(ready, mutation):
    root, args = ready
    path = root / ledger.RETENTION_TRUST_PATH
    original = path.read_bytes()
    if mutation == "rotate":
        public, _ = ledger._ed25519_sign(bytes(32), b"")
        trust = ledger.RetentionApprovalTrust("sha256:" + ledger.sha256(public).hexdigest(), "ed25519:" + public.hex())
        path.write_text(ledger._render_retention_trust(trust), encoding="utf-8")
    elif mutation == "alias":
        path = path.with_name("retention-approval.alias.yaml")
        path.write_bytes(original)
    else:
        _git(root, "rm", ledger.RETENTION_TRUST_PATH)
        _git(root, "commit", "--quiet", "-m", "delete anchor")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(original)
    _git(root, "add", str(path))
    _git(root, "commit", "--quiet", "-m", "manual trust mutation")
    before = _transaction_state(root)
    assert not operate("ledger_expire", dict(args, apply=True))["ok"]
    assert not operate("trust_init", dict(cwd=str(root), apply=True))["ok"]
    assert _transaction_state(root) == before


def test_identical_anchor_merge_carrier_and_divergent_parent_refusal(ready):
    root, _args = ready
    base = _git(root, "rev-parse", "feature~4")
    # Select the public-anchor bootstrap before any ledger was introduced.
    while _git(root, "ls-tree", "-r", "--name-only", base, "--", ledger.REFLECTION_ROOT):
        base = _git(root, "rev-parse", base + "^")
    _git(root, "checkout", "--quiet", "-b", "other", base)
    _git(root, "commit", "--quiet", "--allow-empty", "-m", "independent work")
    _git(root, "checkout", "--quiet", "main")
    _git(root, "merge", "--no-ff", "--no-commit", "other")
    assert operate("commit_admission", dict(cwd=str(root)))["ok"]
    _git(root, "commit", "--quiet", "-m", "exact anchor carrier")
    assert ledger._retention_anchor(root, _git(root, "rev-parse", "HEAD"))
    _git(root, "checkout", "--quiet", "other")
    anchor = root / ledger.RETENTION_TRUST_PATH
    public, _ = ledger._ed25519_sign(bytes(32), b"")
    trust = ledger.RetentionApprovalTrust("sha256:" + ledger.sha256(public).hexdigest(), "ed25519:" + public.hex())
    anchor.write_text(ledger._render_retention_trust(trust), encoding="utf-8")
    _git(root, "add", str(anchor))
    _git(root, "commit", "--quiet", "-m", "divergent trust parent")
    with pytest.raises(ledger.ReflectionValidationError):
        ledger.preview_reflection_integration(root, source_ref="other", base_ref="main")


def test_stale_expiry_cas_rolls_back_both_paths(ready):
    root, args = ready
    path = root / ledger.workstream_ledger_path(args["workstream_id"])
    before = path.read_bytes()
    sessions = {str(item): item.read_bytes() for item in (root / ".memory-seed/sessions").rglob("*.md")}
    plan = ledger.preview_workstream_expiry_commit(root, trusted_ref="main", workstream_id=args["workstream_id"], chain_id=args["chain_id"])
    race = []

    def change_ref(stage):
        if stage == "before-cas":
            tree = _git(root, "rev-parse", plan.expected_head + "^{tree}")
            race.append(_git(root, "commit-tree", tree, "-p", plan.expected_head, "-m", "concurrent advance"))
            _git(root, "update-ref", plan.trusted_ref, race[0], plan.expected_head)

    with pytest.raises(ledger.ReflectionValidationError, match="compare-and-swap"):
        ledger.apply_workstream_commit(root, plan, fault_injector=change_ref)
    assert _git(root, "rev-parse", "HEAD") == race[0]
    assert path.read_bytes() == before and _git(root, "status", "--porcelain") == ""
    assert {str(item): item.read_bytes() for item in (root / ".memory-seed/sessions").rglob("*.md")} == sessions


def test_bypassing_hook_cannot_authorize_manual_cleanup(ready):
    root, args = ready
    relative = ledger.workstream_ledger_path(args["workstream_id"])
    loaded = ledger.load_trusted_workstream_ledger(root, trusted_ref="main", ledger_path=relative)
    (root / relative).write_bytes(ledger._derive_compaction_post_bytes(loaded.raw, loaded.ledger, (args["chain_id"],), relative))
    _git(root, "add", relative)
    _git(root, "-c", "core.hooksPath=", "commit", "--quiet", "-m", "reflection: expiry")
    result = operate("ledger_check", dict(cwd=str(root), workstream_id=args["workstream_id"]))
    assert not result["ok"] and result["error"]["code"] == "compaction-proof-missing"


def test_merge_cannot_launder_preclose_receipt_origin(ready):
    root, args = ready
    loaded = ledger.load_trusted_workstream_ledger(root, trusted_ref="main", ledger_path=ledger.workstream_ledger_path(args["workstream_id"]))
    relative = ".memory-seed/sessions/2026-01/2026-01-02.md"
    evidence = (root / relative).read_bytes()
    _git(root, "checkout", "--quiet", "-b", "receipt-attack", loaded.ledger.header.base_sha)
    (root / relative).parent.mkdir(parents=True, exist_ok=True)
    (root / relative).write_bytes(evidence)
    _git(root, "add", relative)
    _git(root, "commit", "--quiet", "-m", "preclose receipt on another history")
    _git(root, "checkout", "--quiet", "main")
    _git(root, "merge", "--quiet", "--no-ff", "-m", "merge identical receipt bytes", "receipt-attack")
    before = _transaction_state(root)
    result = operate("ledger_expire", dict(args, apply=True))
    assert not result["ok"] and result["error"]["code"] == "receipt-integration", result
    assert _transaction_state(root) == before


def test_signed_issue_window_is_rechecked_before_cas(ready, monkeypatch):
    root, args = ready
    before = _transaction_state(root)
    original = ledger._clock_timestamp
    current = ledger._as_utc(original())
    plan = ledger.preview_workstream_expiry_commit(root, trusted_ref="main", workstream_id=args["workstream_id"], chain_id=args["chain_id"])

    def expire_attestation(stage):
        if stage == "before-cas":
            monkeypatch.setattr(ledger, "_clock_timestamp", lambda clock=None: original(clock or (lambda: current + timedelta(minutes=6))))

    with pytest.raises(ledger.ReflectionValidationError, match="expired before CAS"):
        ledger.apply_workstream_commit(root, plan, fault_injector=expire_attestation)
    assert _transaction_state(root) == before


def test_expiry_preserves_an_unrelated_open_chain(ready):
    root, args = ready
    appended = operate("ledger_append", dict(cwd=str(root), workstream_id=args["workstream_id"], role="planner",
        relationship="no_related_thread", no_related_thread=True, conclusion="a different chain",
        reasoning="independent work", source="test", apply=True))
    assert appended["ok"], appended
    result = operate("ledger_expire", dict(args, apply=True))
    assert result["ok"], result
    loaded = ledger.load_trusted_workstream_ledger(root, trusted_ref="main", ledger_path=ledger.workstream_ledger_path(args["workstream_id"]))
    assert [record.record_id for record in loaded.ledger.records] == [appended["record_id"]]
    assert len(loaded.ledger.rebinds) == 1


def _replace_close_introduction(root, args, mutation):
    relative = ledger.workstream_ledger_path(args["workstream_id"])
    loaded = ledger.load_trusted_workstream_ledger(root, trusted_ref="main", ledger_path=relative)
    close = loaded.ledger.records[-1]
    _initial, _blob, transitions = ledger._ledger_lineage(root, loaded.head, relative)
    transition = next(item for item in transitions if item.blob.content == item.parent_blob.content
                      + b"\n" + ledger.render_workstream_record(close).encode("utf-8"))
    message = ledger._git_commit_message(root, transition.commit)
    prefix, proof_text = message.split("\nReflection-Close-Time: ")
    proof = json.loads(proof_text)
    _git(root, "checkout", "--quiet", "-B", "main", transition.parent)
    if mutation == "missing":
        message = prefix
    elif mutation == "parent":
        _git(root, "commit", "--quiet", "--allow-empty", "-m", "different close parent")
    else:
        if mutation == "signature":
            proof["signature"] = "ed25519:" + "0" * 128
        elif mutation == "observed_at":
            proof["observed_at"] = "2026-01-02T00:00:00Z"
            proof["expires_at"] = "2026-01-02T00:05:00Z"
        elif mutation == "anchor":
            proof["trust_anchor_blob"] = "0" * 40
        elif mutation == "record":
            proof["close_record_digest"] = "sha256:" + "0" * 64
        elif mutation == "post_blob":
            proof["post_blob"] = "0" * 40
        message = prefix + "\nReflection-Close-Time: " + json.dumps(proof, sort_keys=True, separators=(",", ":"))
    (root / relative).write_bytes(transition.blob.content)
    _git(root, "add", relative)
    _git(root, "-c", "core.hooksPath=", "commit", "--quiet", "-m", message)
    _commit_receipts(root, args["workstream_id"], args["chain_id"], closure=True)
    return close


@pytest.mark.parametrize("mutation", ["missing", "signature", "observed_at", "anchor", "record", "post_blob", "parent"])
def test_raw_backdated_close_and_altered_host_proof_cannot_expire(ready, mutation):
    root, args = ready
    close = _replace_close_introduction(root, args, mutation)
    assert ledger._as_utc(close.closed_at) + timedelta(days=7) < ledger._as_utc(ledger._clock_timestamp())
    # The canonical legacy ledger is still readable, but its authored date is
    # not an authenticated observation of elapsed retention.
    assert operate("ledger_check", dict(cwd=str(root), workstream_id=args["workstream_id"]))["ok"]
    before = _transaction_state(root)
    result = operate("ledger_expire", dict(args, apply=True))
    assert not result["ok"] and result["error"]["code"] == "close-time-proof", result
    assert _transaction_state(root) == before


def test_historical_elapsed_signature_does_not_replace_missing_close_proof(ready, monkeypatch):
    root, args = ready
    close = _replace_close_introduction(root, args, "missing")
    # Emulate an earlier unsafe host signing elapsed evidence for a raw close.
    # Independent historical replay must still require original close authority.
    with monkeypatch.context() as unsafe_host:
        unsafe_host.setattr(ledger, "_verified_close_time", lambda *args: {"observed_at": close.closed_at})
        assert operate("ledger_expire", dict(args, apply=True))["ok"]
    ledger.clear_trusted_workstream_history_cache()
    result = operate("ledger_check", dict(cwd=str(root), workstream_id=args["workstream_id"]))
    assert not result["ok"] and result["error"]["code"] == "close-time-proof", result


def test_close_requires_trust_at_its_immutable_base(tmp_path):
    from test_reflection_workstream_ledger import _planned_transaction
    with pytest.raises(ledger.ReflectionValidationError, match="trust init must precede the ledger base"):
        _planned_transaction(tmp_path, "close", retention_trust=False)


def test_expiry_uses_apply_time_observation_not_backdated_close_record(ready):
    root, args = ready
    relative = ledger.workstream_ledger_path(args["workstream_id"])
    # Re-open only this disposable fixture at the original pre-close tip.
    _git(root, "checkout", "--quiet", "-B", "main", "HEAD~2")
    loaded = ledger.load_trusted_workstream_ledger(root, trusted_ref="main", ledger_path=relative)
    integration = ledger.GitWorkstreamIntegrationVerifier(loaded)
    witness = integration.witness()
    receipts = ledger.admit_workstream_chain_receipts(loaded, chain_id=args["chain_id"], session_ref="HEAD",
        session_path=".memory-seed/sessions/2026-01/2026-01-01.md", entry_id="mse_0123456789abcde0",
        decision_id="D1", disposition="expired-unpromoted", integration_witness=witness, integration_verifier=integration)
    plan = ledger.preview_workstream_close_commit(root, trusted_ref="main", workstream_id=args["workstream_id"],
        chain_id=args["chain_id"], receipts=receipts, receipt_verifier=ledger.GitWorkstreamReceiptVerifier(loaded, witness.integration_commit),
        integration_witness=witness, integration_verifier=integration, conclusion="closed", reasoning="synthesized",
        source="test", confidence="high", clock=lambda: START + timedelta(minutes=1))
    before_apply = ledger._as_utc(ledger._clock_timestamp())
    applied = ledger.apply_workstream_commit(root, plan)
    proof = json.loads(ledger._git_commit_message(root, applied.new_head).split("\nReflection-Close-Time: ")[1])
    assert ledger._as_utc(proof["observed_at"]) >= before_apply
    assert proof["closed_at"] == "2026-01-01T00:01:00Z"
    _commit_receipts(root, args["workstream_id"], args["chain_id"], closure=True)
    before = _transaction_state(root)
    result = operate("ledger_expire", dict(args, apply=True))
    assert not result["ok"] and "not elapsed" in result["error"]["message"], result
    assert _transaction_state(root) == before


@pytest.mark.parametrize("concurrent", ["uncommitted", "staged", "committed", "committed_owned_bytes"])
def test_cas_failure_preserves_concurrent_session_content_and_index(ready, monkeypatch, concurrent):
    _assert_concurrent_session_cas_failure(ready, monkeypatch, concurrent)


@pytest.mark.parametrize("concurrent", ["uncommitted", "committed"])
def test_cas_failure_preserves_existing_session_content(ready, monkeypatch, concurrent):
    from memory_seed.core import session_append_entry
    root, _args = ready
    baseline = session_append_entry(root, title="Existing session content", user_initials="MS", agent_type="test",
        body="### Summary\n\nPreviously authored content must remain intact.\n")
    assert baseline.ok
    _git(root, "add", baseline.path.relative_to(root).as_posix())
    _git(root, "commit", "--quiet", "-m", "existing ordinary session\n\nMemory-Entry: " + baseline.entry_id)
    _assert_concurrent_session_cas_failure(ready, monkeypatch, concurrent)


def _new_per_user_session(ready, monkeypatch):
    from memory_seed.core import session_target
    root, _args = ready
    project = root / ".memory-seed/project.yaml"
    project.write_text("schema_version: 1\nparticipants:\n"
        "  - slug: jean\n    initials: JN\n    display_name: Jean\n"
        "  - slug: amina\n    initials: AM\n    display_name: Amina\n", encoding="utf-8", newline="\n")
    _git(root, "add", ".memory-seed/project.yaml")
    _git(root, "commit", "--quiet", "-m", "two session participants")
    monkeypatch.setenv("MEMORY_SEED_USER", "jean")
    target = session_target(root)
    assert target.user == "jean" and target.layout == "month-user"
    assert not target.path.exists()
    return target.path


def test_public_expiry_creates_new_per_user_session_with_author_frontmatter(ready, monkeypatch):
    root, args = ready
    session = _new_per_user_session(ready, monkeypatch)
    before = _git(root, "rev-parse", "HEAD")
    result = call_tool("memory_reflection_ledger_expire", dict(args, apply=True))
    assert result["ok"] and result["applied"], result
    raw = session.read_bytes()
    assert raw.startswith(b"---\nschema_version: 2\n")
    assert b"hash_id: msm_" in raw and b"user: jean\ncreated_at: " in raw
    assert b"### Reflection workstream compaction" in raw
    assert _git(root, "rev-list", "--count", before + "..HEAD") == "2"
    assert _git(root, "status", "--porcelain") == ""
    loaded = ledger.load_trusted_workstream_ledger(root, trusted_ref="main",
        ledger_path=ledger.workstream_ledger_path(args["workstream_id"]))
    assert isinstance(loaded, ledger.AdmittedCompactedLedger)
    assert len(loaded.proofs) == 1 and not loaded.ledger.records


def test_cas_failure_removes_only_owned_new_per_user_session(ready, monkeypatch):
    root, args = ready
    session = _new_per_user_session(ready, monkeypatch)
    before = _transaction_state(root)
    original_git, attempted = ledger._git, []

    def fail_cas(cwd, *argv, **kwargs):
        if argv[:2] == ("update-ref", "--stdin"):
            attempted.append(session.read_bytes())
            assert b"schema_version: 2\n" in attempted[-1]
            assert b"### Reflection workstream compaction" in attempted[-1]
            return 1, "injected unsuccessful CAS"
        return original_git(cwd, *argv, **kwargs)

    monkeypatch.setattr(ledger, "_git", fail_cas)
    result = call_tool("memory_reflection_ledger_expire", dict(args, apply=True))
    assert not result["ok"] and result["error"]["code"] == "stale_ref", result
    assert len(attempted) == 1
    assert not session.exists()
    assert _transaction_state(root) == before


@pytest.mark.parametrize("concurrent", ["uncommitted", "staged", "committed", "committed_owned_bytes"])
def test_cas_failure_preserves_concurrent_new_per_user_session(ready, monkeypatch, concurrent):
    _new_per_user_session(ready, monkeypatch)
    _assert_concurrent_session_cas_failure(ready, monkeypatch, concurrent)


def test_per_user_creation_append_race_does_not_claim_concurrent_preimage(ready, monkeypatch):
    from memory_seed import core
    root, args = ready
    session = _new_per_user_session(ready, monkeypatch)
    original_write = core._write_session_file
    marker = b"\nConcurrent content between session creation and append.\n"

    def concurrent_write(path, content, **kwargs):
        written = original_write(path, content, **kwargs)
        if path == session and kwargs["preimage"] is None and written:
            path.write_bytes(path.read_bytes() + marker)
        return written

    monkeypatch.setattr(core, "_write_session_file", concurrent_write)
    before = _git(root, "rev-parse", "HEAD")
    result = call_tool("memory_reflection_ledger_expire", dict(args, apply=True))
    assert not result["ok"] and result["error"]["code"] == "append-rollback-conflict", result
    assert marker in session.read_bytes()
    assert _git(root, "rev-parse", "HEAD") == before
    assert _git(root, "diff", "--cached", "--name-only") == ""


def _assert_concurrent_session_cas_failure(ready, monkeypatch, concurrent):
    root, args = ready
    relative = ledger.workstream_ledger_path(args["workstream_id"])
    pre_ledger = (root / relative).read_bytes()
    plan = ledger.preview_workstream_expiry_commit(root, trusted_ref="main", workstream_id=args["workstream_id"], chain_id=args["chain_id"])
    original_git, race = ledger._git, {}

    def fail_cas(cwd, *argv, **kwargs):
        if argv[:2] == ("update-ref", "--stdin"):
            session = next(path for path in _git(root, "diff", "--cached", "--name-only").splitlines()
                           if path.startswith(".memory-seed/sessions/"))
            target = root / session
            content = target.read_bytes()
            if concurrent != "committed_owned_bytes":
                content += b"\nConcurrent session author: preserve this content.\n"
                target.write_bytes(content)
            if concurrent == "staged":
                _git(root, "add", session)
            if concurrent.startswith("committed"):
                with monkeypatch.context() as isolated_index:
                    isolated_index.setenv("GIT_INDEX_FILE", str(root / ".git" / "concurrent-session-index"))
                    _git(root, "read-tree", plan.expected_head)
                    _git(root, "add", session)
                    tree = _git(root, "write-tree")
                    advanced = _git(root, "commit-tree", tree, "-p", plan.expected_head, "-m", "concurrent session commit")
                _git(root, "update-ref", plan.trusted_ref, advanced, plan.expected_head)
            race.update(path=session, content=content, index=_git(root, "ls-files", "-s", "--", session),
                        head=_git(root, "rev-parse", "HEAD"))
            return 1, "injected stale CAS after concurrent session write"
        return original_git(cwd, *argv, **kwargs)

    monkeypatch.setattr(ledger, "_git", fail_cas)
    with pytest.raises(ledger.ReflectionValidationError) as refused:
        ledger.apply_workstream_commit(root, plan)
    assert refused.value.diagnostic.code == "append-rollback-conflict"
    assert race["path"] in refused.value.diagnostic.details["preserved_paths"]
    assert (root / race["path"]).read_bytes() == race["content"]
    assert _git(root, "ls-files", "-s", "--", race["path"]) == race["index"]
    assert _git(root, "rev-parse", "HEAD") == race["head"]
    assert (root / relative).read_bytes() == pre_ledger

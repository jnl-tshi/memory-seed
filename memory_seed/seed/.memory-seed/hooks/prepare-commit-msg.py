#!/usr/bin/env python3
"""Git prepare-commit-msg hook: stamp provenance trailers automatically.

`session merge-branch` stamps one `Memory-Entry: <entry_id>` trailer per
fused session entry, but ordinary commits that carry entries only get the
trailer if the author remembers to write it - and a forgotten trailer
silently downgrades Memory Trace's commit-accurate merge rendering to a
positional estimate. This hook makes the entry->commit join true by
construction: it scans the staged diff for newly added `entry_id:` lines
under the session tree and appends one trailer per new id, deduplicated
against trailers already present in the message.

An active Task Packet stores a full compiler/activation receipt inside this
worktree's Git directory. This hook recomputes the packet, dispatch, and
Evidence Pack fingerprint relationships before verifying that receipt against
the current branch, worktree, base SHA, selected evidence, and staged scope; a
Git configuration value or skeletal JSON alone can never activate attribution.

Git invokes this script through the
`.git/hooks/prepare-commit-msg` shim that `memory-seed init` (or
`memory-seed hooks install`) writes. Operational errors fail open, but an
ordinary commit with more than ten newly authored entries is refused unless the
message records a durable, live-approved `Memory-Bulk-Reason:` trailer. Reserved
reflection admission uses the installed shared facade and fails closed.
"""

import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
from pathlib import Path

# Both id generations plus the wider lowercase ids other agents author
# (mirrors memory_seed.core._TRAILER_ENTRY_ID_RE; kept in sync by the
# hook-contract test in the control-plane repo).
_ENTRY_ID_RE = re.compile(r"^\+entry_id:\s*((?:ms-[0-9a-f]{8}|mse_[0-9a-z]{8,32}))\s*$")
_TRAILER_RE = re.compile(r"^Memory-Entry:\s*(\S+)\s*$", re.MULTILINE)
_IMPLEMENTS_REF_RE = re.compile(r"(?:ms-[0-9a-f]{8}|mse_[0-9a-z]{8,32}):d[1-9][0-9]*\Z")
_IMPLEMENTS_TRAILER_RE = re.compile(r"^Memory-Implements:\s*(\S+)\s*$", re.MULTILINE)
_BULK_REASON_RE = re.compile(r"^Memory-Bulk-Reason:\s*\S.+$", re.MULTILINE)
_TRAILER_LINE_RE = re.compile(r"[A-Za-z][A-Za-z0-9-]*: ")
MAX_ORDINARY_NEW_ENTRIES = 10
_FULL_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
_SLUG_RE = re.compile(r"[a-z][a-z0-9_-]*\Z")
_TASK_PACKET_KEYS = {
    "packet_schema", "packet_version", "dispatch", "dispatch_fingerprint",
    "runtime_binding", "retrieval_profile", "evidence_pack",
    "materialized_evidence", "worker_baseline", "constitution_projection", "execution_defaults",
    "input_ledger", "cost_ledger", "fingerprint",
}
_DISPATCH_KEYS = {
    "schema", "version", "objective", "constitution_refs", "project_context",
    "execution", "retrieval", "budget", "memory_update_policy", "memory_checkpoints",
}
_EXECUTION_KEYS = {
    "role", "persona", "capability_tier", "write_intent", "allowed_files",
    "forbidden_files", "validation", "output_contract", "expected_absent",
    "acceptance_observables", "implements",
}
_BINDING_KEYS = {
    "owner", "agent_type", "base_branch", "base_sha", "working_branch",
    "worktree", "expected_directory", "integration_artifact",
}


def staged_entry_ids() -> list[str]:
    return list(dict.fromkeys(staged_entry_records()))


def staged_entry_records() -> list[str]:
    # Restricted to session trees (root and nested subproject runtimes): the
    # control-plane repo's own test fixtures also contain entry_id: lines and
    # must never be stamped.
    #
    # SIDECARS ARE EXCLUDED, and that is the whole correctness of this hook.
    # A trailer claims "this commit CARRIES this entry". A session document's
    # `entry_id:` is the entry being authored; a sidecar's is a REFERENCE to one
    # authored somewhere else entirely - possibly months earlier.
    #
    # Latent until 2026-07-27, when a topic sweep wrote one sidecar block per
    # entry across the whole corpus and two commits stamped 520 trailers each.
    # Before that, sidecars named two or three entries at a time and the
    # over-stamping was invisible. Links and diagrams have always had the same
    # defect at a smaller scale, so all three are excluded rather than just the
    # family that made it obvious.
    proc = subprocess.run(
        [
            "git", "diff", "--cached", "-U0", "--",
            ".memory-seed/sessions",
            ":(glob)**/.memory-seed/sessions/**",
            ":(exclude,glob)**/.memory-seed/sessions/topics/**",
            ":(exclude,glob)**/.memory-seed/sessions/links/**",
            ":(exclude,glob)**/.memory-seed/sessions/diagrams/**",
            ":(exclude).memory-seed/sessions/topics",
            ":(exclude).memory-seed/sessions/links",
            ":(exclude).memory-seed/sessions/diagrams",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if proc.returncode != 0:
        return []
    records: list[str] = []
    for line in proc.stdout.splitlines():
        match = _ENTRY_ID_RE.match(line)
        if match:
            records.append(match.group(1))
    return records


def _canonical_json(payload) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _activation_artifact(root: Path, branch: str) -> Path | None:
    git_dir = subprocess.run(
        ["git", "rev-parse", "--git-dir"], capture_output=True, text=True, timeout=10
    )
    if git_dir.returncode != 0 or not git_dir.stdout.strip():
        return None
    directory = Path(git_dir.stdout.strip())
    if not directory.is_absolute():
        directory = root / directory
    token = hashlib.sha256(branch.encode("utf-8")).hexdigest()
    return directory.resolve() / "memory-seed" / "task-packets" / f"{token}.json"


def _fingerprint(payload: object) -> str | None:
    try:
        return "sha256:" + hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    except (TypeError, ValueError):
        return None


def _evidence_pack_fingerprint(pack: dict) -> str | None:
    """Mirror the compiler's v2 Evidence Pack identity calculation."""
    if pack.get("pack_schema") != "memory-seed/evidence-pack" or pack.get("pack_version") != 2:
        return None
    if pack.get("resolver_version") != 3 or not isinstance(pack.get("evidence"), list):
        return None
    try:
        identity = {
            "pack_schema": pack["pack_schema"],
            "pack_version": pack["pack_version"],
            "resolver_version": pack["resolver_version"],
            "corpus_revision": pack["corpus_revision"],
            "effective_spec_fingerprint": pack["effective_spec_fingerprint"],
            "evidence": [],
        }
        for item in pack["evidence"]:
            if not isinstance(item, dict):
                return None
            record = {
                key: item[key]
                for key in (
                    "id", "kind", "source", "line_range", "chunk_id", "graph_distance",
                    "selected_by", "content_digest", "model_selection_reasons", "pinned_required",
                )
            }
            identity["evidence"].append(record)
    except (KeyError, TypeError):
        return None
    return _fingerprint(identity)


def _valid_worker_baseline(baseline: object, dispatch: dict) -> bool:
    """Mirror the packet's embedded-baseline integrity checks without source rereads."""
    if not isinstance(baseline, dict) or set(baseline) != {"sources", "fingerprint"}:
        return False
    sources = baseline.get("sources")
    if not isinstance(sources, dict) or set(sources) != {"agent_rules", "session_logging"}:
        return False
    session_required = (
        dispatch.get("memory_update_policy") == "worker_checkpoint"
        or any(
            isinstance(path, str)
            and path.replace("\\", "/").casefold().startswith(".memory-seed/sessions/")
            for path in dispatch.get("execution", {}).get("allowed_files", [])
        )
    )
    for name, expected_source, required in (
        ("agent_rules", ".memory-seed/agent-rules.md", True),
        ("session_logging", ".memory-seed/skills/session_logging.md", session_required),
    ):
        item = sources.get(name)
        if item is None:
            if required:
                return False
            continue
        if not isinstance(item, dict) or set(item) != {"source", "byte_count", "token_estimate", "content_digest", "content"}:
            return False
        content = item.get("content")
        if item.get("source") != expected_source or not isinstance(content, str):
            return False
        payload = content.encode("utf-8")
        if item.get("byte_count") != len(payload) or item.get("token_estimate") != (len(payload) + 3) // 4:
            return False
        if item.get("content_digest") != "sha256:" + hashlib.sha256(payload).hexdigest():
            return False
    expected = _fingerprint(sources)
    return isinstance(expected, str) and secrets.compare_digest(baseline.get("fingerprint", ""), expected)


def _verified_receipt(packet: object, root: Path, branch: str) -> tuple[list[str], list[str]] | None:
    """Return packet refs/scope only for a full compiler activation receipt.

    The receipt is local operational evidence, not a cryptographic signature:
    a malicious repository writer can alter it. Its purpose is to ensure a
    normal hook trailer is traceable to the same complete Memory Seed packet
    validation path, never to arbitrary Git config or skeletal JSON.
    """
    if not isinstance(packet, dict) or set(packet) != _TASK_PACKET_KEYS:
        return None
    if packet.get("packet_schema") != "memory-seed/task-packet" or packet.get("packet_version") != 1:
        return None
    fingerprint = packet.get("fingerprint")
    identity = dict(packet)
    identity.pop("fingerprint", None)
    expected = _fingerprint(identity)
    if not isinstance(fingerprint, str) or not isinstance(expected, str) or not secrets.compare_digest(fingerprint, expected):
        return None
    dispatch = packet.get("dispatch")
    binding = packet.get("runtime_binding")
    evidence_pack = packet.get("evidence_pack")
    evidence = packet.get("materialized_evidence")
    worker_baseline = packet.get("worker_baseline")
    if (
        not isinstance(dispatch, dict)
        or set(dispatch) != _DISPATCH_KEYS
        or not isinstance(binding, dict)
        or set(binding) != _BINDING_KEYS
        or not isinstance(evidence_pack, dict)
        or not isinstance(evidence, list)
        or not _valid_worker_baseline(worker_baseline, dispatch)
    ):
        return None
    if dispatch.get("schema") != "memory-seed/task-dispatch" or dispatch.get("version") != 1:
        return None
    if not isinstance(dispatch.get("objective"), str) or not dispatch["objective"].strip():
        return None
    dispatch_fingerprint = _fingerprint(dispatch)
    if dispatch_fingerprint is None or not secrets.compare_digest(packet.get("dispatch_fingerprint", ""), dispatch_fingerprint):
        return None
    execution = dispatch.get("execution")
    if not isinstance(execution, dict) or set(execution) != _EXECUTION_KEYS:
        return None
    if execution.get("write_intent") != "writing" or execution.get("role") not in {"worker", "validator", "researcher"}:
        return None
    implements = execution.get("implements")
    allowed_files = execution.get("allowed_files")
    if not isinstance(implements, list) or not isinstance(allowed_files, list) or not all(isinstance(path, str) for path in allowed_files):
        return None
    if not all(isinstance(value, str) for value in (binding.get("owner"), binding.get("agent_type"), binding.get("base_branch"), binding.get("base_sha"), binding.get("working_branch"), binding.get("worktree"), binding.get("expected_directory"), binding.get("integration_artifact"))):
        return None
    if _SLUG_RE.fullmatch(binding["owner"]) is None or _SLUG_RE.fullmatch(binding["agent_type"]) is None:
        return None
    if binding["integration_artifact"] not in {"pr", "merge-request", "patch", "branch", "handoff"}:
        return None
    if binding["working_branch"] != branch:
        return None
    if os.path.normcase(os.path.realpath(binding["worktree"])) != os.path.normcase(os.path.realpath(root)):
        return None
    if os.path.normcase(os.path.realpath(binding["expected_directory"])) != os.path.normcase(os.path.realpath(root)):
        return None
    base_sha = binding.get("base_sha")
    if not isinstance(base_sha, str) or _FULL_SHA_RE.fullmatch(base_sha.lower()) is None:
        return None
    base_ref = subprocess.run(
        ["git", "show-ref", "--verify", "--hash", f"refs/heads/{binding['base_branch']}"],
        capture_output=True, text=True, timeout=10,
    )
    if base_ref.returncode != 0 or not base_ref.stdout.strip():
        return None
    if base_ref.stdout.strip().lower() != base_sha.lower():
        # The active branch is allowed to advance from the packet's immutable
        # base; another mutable base branch is not.
        if binding["base_branch"] != branch:
            return None
        base_ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", base_sha, base_ref.stdout.strip()],
            capture_output=True, text=True, timeout=10,
        )
        if base_ancestor.returncode != 0:
            return None
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base_sha, "HEAD"], capture_output=True, text=True, timeout=10
    )
    if ancestor.returncode != 0:
        return None
    expected_evidence = _evidence_pack_fingerprint(evidence_pack)
    if expected_evidence is None or not secrets.compare_digest(evidence_pack.get("fingerprint", ""), expected_evidence):
        return None
    expected_materialized = [
        (item.get("id"), item.get("kind"), item.get("source"), item.get("line_range"), item.get("content_digest"))
        for item in evidence_pack["evidence"] if item.get("kind") != "constitution"
    ]
    observed_materialized = []
    for item in evidence:
        if not isinstance(item, dict) or not isinstance(item.get("content"), str):
            return None
        digest = "sha256:" + hashlib.sha256(item["content"].encode("utf-8")).hexdigest()
        if item.get("content_digest") != digest:
            return None
        observed_materialized.append((item.get("id"), item.get("kind"), item.get("source"), item.get("line_range"), item.get("content_digest")))
    if observed_materialized != expected_materialized:
        return None
    selected = {item.get("id") for item in evidence if item.get("kind") == "decision"}
    refs: list[str] = []
    for reference in implements:
        if not isinstance(reference, str) or _IMPLEMENTS_REF_RE.fullmatch(reference) is None:
            return None
        if reference not in selected:
            return None
        if reference not in refs:
            refs.append(reference)
    return refs, allowed_files


def _valid_activated_packet(payload: object, root: Path, branch: str) -> list[str]:
    if not isinstance(payload, dict):
        return []
    packet = payload.get("packet")
    verification = _verified_receipt(packet, root, branch)
    receipt = payload.get("receipt")
    if verification is None or not isinstance(packet, dict) or not isinstance(receipt, dict):
        return []
    refs, allowed_files = verification
    expected_receipt = {
        "schema": "memory-seed/task-packet-activation-receipt",
        "version": 1,
        "compiler": "memory_seed.task_packet.compile_task_packet",
        "activation": "memory_seed.task_packet.activate_task_packet",
        "packet_fingerprint": packet["fingerprint"],
        "dispatch_fingerprint": packet["dispatch_fingerprint"],
        "evidence_pack_fingerprint": packet["evidence_pack"]["fingerprint"],
        "runtime_binding": packet["runtime_binding"],
        "objective": packet["dispatch"]["objective"],
        "implements": packet["dispatch"]["execution"]["implements"],
    }
    if receipt != expected_receipt:
        return []
    changed = subprocess.run(
        ["git", "diff", "--cached", "--name-only"], capture_output=True, text=True, timeout=10
    )
    if changed.returncode != 0:
        return []
    allowed = set(allowed_files)
    if any(path and path not in allowed for path in changed.stdout.splitlines()):
        return []
    return refs


def active_packet_implements() -> list[str]:
    """Verify an exact packet artifact; config values alone can never activate."""
    branch = subprocess.run(
        ["git", "branch", "--show-current"], capture_output=True, text=True, timeout=10
    )
    if branch.returncode != 0 or not branch.stdout.strip():
        return []
    root = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=10
    )
    if root.returncode != 0 or not root.stdout.strip():
        return []
    artifact = _activation_artifact(Path(root.stdout.strip()), branch.stdout.strip())
    if artifact is None:
        return []
    try:
        payload = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    if not isinstance(payload, dict) or payload.get("schema") != "memory-seed/task-packet-activation" or payload.get("version") != 1:
        return []
    return _valid_activated_packet(payload, Path(root.stdout.strip()), branch.stdout.strip())


def reflection_admitted() -> bool:
    try:
        # A source checkout uses its own facade; seeded projects use the
        # installed package selected by the hook's Python interpreter.
        source_root = Path(__file__).resolve().parents[2]
        if (source_root / "memory_seed" / "reflection_operations.py").is_file():
            sys.path.insert(0, str(source_root))
        from memory_seed.reflection_operations import run_reflection_operation
        result = run_reflection_operation("commit_admission", {"cwd": str(Path.cwd())})
        if result.get("ok") is True:
            return True
        detail = result.get("error", {}).get("message", "shared admission refused the commit")
    except Exception as exc:
        detail = f"shared reflection admission is unavailable: {exc}"
    print(f"Refusing commit: {detail}", file=sys.stderr)
    return False


def main() -> int:
    if len(sys.argv) < 2:
        return 0
    if not reflection_admitted():
        return 1
    msg_path = sys.argv[1]
    records = staged_entry_records()
    ids = list(dict.fromkeys(records))
    implements = active_packet_implements()
    if not ids and not implements:
        return 0
    try:
        with open(msg_path, "r", encoding="utf-8") as handle:
            message = handle.read()
    except OSError:
        return 0
    if len(records) > MAX_ORDINARY_NEW_ENTRIES and _BULK_REASON_RE.search(message) is None:
        print(
            "Refusing commit: it carries more than 10 newly authored Memory-Entry records. "
            "Obtain live approval and record it as `Memory-Bulk-Reason: <reason>` in the commit message.",
            file=sys.stderr,
        )
        return 1
    existing_entries = set(_TRAILER_RE.findall(message))
    existing_implements = set(_IMPLEMENTS_TRAILER_RE.findall(message))
    missing_entries = [entry_id for entry_id in ids if entry_id not in existing_entries]
    missing_implements = [reference for reference in implements if reference not in existing_implements]
    if not missing_entries and not missing_implements:
        return 0
    trailer_block = "\n".join(
        [*(f"Memory-Entry: {entry_id}" for entry_id in missing_entries),
         *(f"Memory-Implements: {reference}" for reference in missing_implements)]
    )
    body = message.rstrip("\n")
    if not body:
        message = trailer_block + "\n"
    else:
        last_line = body.rsplit("\n", 1)[-1]
        # Append CONTIGUOUSLY when the message already ends in a trailer line: a
        # blank line would split the trailer block, and git's trailer parser
        # (and Memory Trace's commit-accurate merge geometry) reads ONLY the
        # final contiguous block - silently dropping every earlier Memory-Entry,
        # including a merge's own branch entry. Separate with a blank line only
        # when the message ends in prose, so the trailers still form a block.
        joiner = "\n" if _TRAILER_LINE_RE.match(last_line) else "\n\n"
        message = body + joiner + trailer_block + "\n"
    try:
        with open(msg_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(message)
    except OSError:
        return 0
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Provenance stamping remains fail-open. Reserved admission catches
        # its own operational errors and explicitly refuses in main().
        sys.exit(0)

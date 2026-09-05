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

An active Task Packet stores a full, fingerprint-verified activation artifact
inside this worktree's Git directory. This hook verifies that artifact against
the current branch, worktree, base SHA, selected evidence, and staged scope; a
Git configuration value alone can never activate decision attribution.

Standalone by design (no memory_seed import): git invokes it through the
`.git/hooks/prepare-commit-msg` shim that `memory-seed init` (or
`memory-seed hooks install`) writes. Operational errors fail open, but an
ordinary commit with more than ten newly authored entries is refused unless the
message records a durable, live-approved `Memory-Bulk-Reason:` trailer.
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


def _valid_activated_packet(packet: object, root: Path, branch: str) -> list[str]:
    if not isinstance(packet, dict):
        return []
    fingerprint = packet.get("fingerprint")
    identity = dict(packet)
    identity.pop("fingerprint", None)
    try:
        expected = "sha256:" + hashlib.sha256(_canonical_json(identity).encode("utf-8")).hexdigest()
    except (TypeError, ValueError):
        return []
    if not isinstance(fingerprint, str) or not secrets.compare_digest(fingerprint, expected):
        return []
    dispatch = packet.get("dispatch")
    binding = packet.get("runtime_binding")
    evidence = packet.get("materialized_evidence")
    if not isinstance(dispatch, dict) or not isinstance(binding, dict) or not isinstance(evidence, list):
        return []
    execution = dispatch.get("execution")
    if not isinstance(execution, dict) or execution.get("write_intent") != "writing":
        return []
    implements = execution.get("implements")
    allowed_files = execution.get("allowed_files")
    if not isinstance(implements, list) or not isinstance(allowed_files, list):
        return []
    if binding.get("working_branch") != branch or not isinstance(binding.get("worktree"), str):
        return []
    if os.path.normcase(os.path.realpath(binding["worktree"])) != os.path.normcase(os.path.realpath(root)):
        return []
    base_sha = binding.get("base_sha")
    if not isinstance(base_sha, str) or re.fullmatch(r"[0-9a-f]{40}", base_sha.lower()) is None:
        return []
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", base_sha, "HEAD"], capture_output=True, text=True, timeout=10
    )
    if ancestor.returncode != 0:
        return []
    selected = {item.get("id") for item in evidence if isinstance(item, dict) and item.get("kind") == "decision"}
    refs: list[str] = []
    for reference in implements:
        if not isinstance(reference, str) or _IMPLEMENTS_REF_RE.fullmatch(reference) is None:
            return []
        if reference not in selected:
            return []
        if reference not in refs:
            refs.append(reference)
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
    return _valid_activated_packet(payload.get("packet"), Path(root.stdout.strip()), branch.stdout.strip())


def main() -> int:
    if len(sys.argv) < 2:
        return 0
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
        # Only the deliberate cadence refusal above blocks a commit.
        sys.exit(0)

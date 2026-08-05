"""Frozen, experiment-local specification for the unscored eight-call pilot."""
from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path
from typing import Any, Mapping

from contracts import AGENTS, ARMS, canonical_json, fingerprint

PILOT_TASK_ID = "PILOT-01"
PILOT_SCHEMA = "context-pilot-tasks.v1"
PILOT_SUMMARY_SCHEMA = "context-pilot-summary.v1"
PILOT_CLAIM_PATH = Path(tempfile.gettempdir()) / "memory-seed-context-derivation-pilot-01.claim"
PILOT_CLAUDE_SHA256 = "0F73196359A07F9AD435A8C83CA7C741B9F2ADBC0AD9B05F71A0C2F4AABE906A"
PILOT_AUTH_ENV = "MEMORY_SEED_CONTEXT_PILOT_AUTH"
PILOT_AUTHORITY_MARKER = ".context-pilot-authority.json"
PILOT_CELLS = tuple((agent, arm, 1) for agent in AGENTS for arm in ARMS)


def pilot_cell_claim_path(cell: tuple[str, str, int]) -> Path:
    agent, arm, repetition = cell
    return PILOT_CLAIM_PATH.with_name(f"{PILOT_CLAIM_PATH.name}.{agent}.{arm}.r{repetition}.cell")

SOURCE = {
    "fixture_id": "pilot-authority-links",
    "entries": [
        {"entry_id": "mse_abcd1234efgh5678", "title": "Choose full rebuilds", "decisions": [{"ordinal": "d1", "title": "Rebuild the index", "decision": "Rebuild the complete index after every change.", "why": "The first corpus was small."}]},
        {"entry_id": "mse_bcde2345fghj6789", "title": "Adopt incremental indexing", "evolves": ["d1 -> mse_abcd1234efgh5678:d1"], "related_entries": ["mse_cdef3456ghjk7890"], "decisions": [{"ordinal": "d1", "title": "Update incrementally", "decision": "Update only affected index segments.", "why": "It preserves local speed as the corpus grows."}]},
        {"entry_id": "mse_cdef3456ghjk7890", "title": "Record scale measurements", "related_entries": ["mse_bcde2345fghj6789"], "decisions": [{"ordinal": "d1", "title": "Measure rebuild cost", "decision": "Record rebuild latency at corpus scale.", "why": "This supports the index choice but does not govern it."}]},
        {"entry_id": "mse_defg4567hjkm8901", "title": "Choose status colours", "decisions": [{"ordinal": "d1", "title": "Use blue labels", "decision": "Use blue labels.", "why": "This is unrelated visual noise."}]},
    ],
    "adrs": [{"adr_id": "adr_pilot_local_index", "title": "Local index update strategy", "events": [
        {"kind": "revision-proposed", "decision_ref": "mse_abcd1234efgh5678:d1", "decision": "Rebuild the complete index after every change.", "why": "The first corpus was small.", "evolution": "Initial strategy."},
        {"kind": "revision-accepted", "decision_ref": "mse_abcd1234efgh5678:d1", "expected_head": None, "reason": "Initial governing head."},
        {"kind": "revision-proposed", "decision_ref": "mse_bcde2345fghj6789:d1", "predecessors": [{"decision": "mse_abcd1234efgh5678:d1", "type": "evolves"}], "supporting_decisions": ["mse_cdef3456ghjk7890:d1"], "decision": "Update only affected index segments.", "why": "It preserves local speed as the corpus grows.", "evolution": "Evolves full rebuilds after scale measurement."},
        {"kind": "revision-accepted", "decision_ref": "mse_bcde2345fghj6789:d1", "expected_head": "mse_abcd1234efgh5678:d1", "reason": "Accepted after scale validation."},
    ]}],
}

LINEAGE = {"source": "mse_bcde2345fghj6789:d1", "target": "mse_abcd1234efgh5678:d1", "type": "evolves"}
RELATED = {"source": "mse_bcde2345fghj6789:d1", "target": "mse_cdef3456ghjk7890:d1", "type": "related"}
ALL_REFS = ["adr_pilot_local_index", "mse_bcde2345fghj6789:d1", "mse_abcd1234efgh5678:d1", "mse_cdef3456ghjk7890:d1"]


def _packet(strategy: str, detail: bool) -> str:
    evidence = [
        {"ref": "mse_bcde2345fghj6789:d1", "text": "Update only affected index segments. It preserves local speed as the corpus grows."},
        {"ref": "mse_abcd1234efgh5678:d1", "text": "Rebuild the complete index after every change. The first corpus was small."},
        {"ref": "mse_cdef3456ghjk7890:d1", "text": "Record rebuild latency at corpus scale; supporting context only."},
    ]
    if detail:
        evidence.append({"ref": "mse_defg4567hjkm8901:d1", "text": "Use blue status labels; unrelated visual noise."})
    return canonical_json({
        "schema": "context-packet.v1", "task_id": PILOT_TASK_ID,
        "strategy_fingerprint": strategy,
        "selected_adrs": [{"adr_id": "adr_pilot_local_index", "authoritative_ref": "mse_bcde2345fghj6789:d1", "status": "accepted"}],
        "lineage_edges": [LINEAGE], "related_edges": [RELATED], "evidence": evidence,
        "selected_refs": ALL_REFS[1:], "token_proxy": 165 if detail else 105,
    })


def task_payload(fixture: Path) -> dict[str, Any]:
    row = {
        "schema": "context-benchmark-task.v1", "task_id": PILOT_TASK_ID,
        "task_type": "pilot-authority-links",
        "question": "For the local-index concern, identify the accepted governing decision, its evolves predecessor, and the measurement that is related supporting context rather than lineage.",
        "fixture": str(fixture.resolve()),
        "packets": {
            "retrieval-v1-packet": _packet("pilot-retrieval-v1", True),
            "adr-candidate-packet": _packet("pilot-adr-candidate", False),
        },
        "included_refs_by_arm": {arm: list(ALL_REFS) for arm in ARMS},
        "context_token_proxy_by_arm": {"retrieval-v1-packet": 165, "adr-candidate-packet": 105},
    }
    payload = {"schema": PILOT_SCHEMA, "tasks": [row]}
    payload["fingerprint"] = pilot_tasks_fingerprint(payload)
    return payload


def pilot_tasks_fingerprint(payload: Mapping[str, Any]) -> str:
    stable = json.loads(json.dumps({key: value for key, value in payload.items() if key != "fingerprint"}))
    for row in stable.get("tasks", []):
        row["fixture"] = "<runtime-fixture>"
    return fingerprint(stable)


def validate_task_payload(payload: Mapping[str, Any]) -> bool:
    rows = payload.get("tasks") or []
    return (
        payload.get("schema") == PILOT_SCHEMA and len(rows) == 1
        and rows[0].get("task_id") == PILOT_TASK_ID
        and set((rows[0].get("packets") or {})) == {"retrieval-v1-packet", "adr-candidate-packet"}
        and payload.get("fingerprint") == pilot_tasks_fingerprint(payload)
    )


def gold_payload() -> dict[str, Any]:
    return {"schema": "context-pilot-gold.v1", "tasks": [{
        "task_id": PILOT_TASK_ID, "required_adr_ids": ["adr_pilot_local_index"],
        "authoritative_refs": ["mse_bcde2345fghj6789:d1"],
        "expected_statuses": {"adr_pilot_local_index": "accepted"},
        "required_lineage_edges": [LINEAGE], "required_related_edges": [RELATED],
        "allowed_citations": ALL_REFS[1:], "distractor_refs": ["mse_defg4567hjkm8901:d1"],
        "insufficient_evidence": False, "required_missing_refs": [],
    }]}


def regular_non_reparse_file(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return False
    attrs = getattr(info, "st_file_attributes", 0)
    return stat.S_ISREG(info.st_mode) and not path.is_symlink() and not bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def verified_claude_executable(path: Path) -> Path:
    resolved = path.resolve(strict=True)
    if resolved != path.absolute() or not regular_non_reparse_file(resolved):
        raise ValueError("pilot Claude executable must be an exact resolved regular non-reparse file")
    digest = hashlib.sha256(resolved.read_bytes()).hexdigest().upper()
    if digest != PILOT_CLAUDE_SHA256:
        raise ValueError("pilot Claude executable SHA256 does not match the approved archive")
    return resolved


def safe_empty_temp_root(value: str | Path, repo_root: Path) -> Path:
    root = Path(value).absolute()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if root == temp_root or root.resolve() != root:
        raise ValueError("pilot output must be a dedicated resolved OS-temporary directory")
    try:
        root.relative_to(temp_root)
    except ValueError as exc:
        raise ValueError("pilot output must be under the OS temporary directory") from exc
    try:
        root.relative_to(repo_root.resolve())
    except ValueError:
        pass
    else:
        raise ValueError("pilot output must be outside the repository")
    current = root
    while current != temp_root:
        if current.exists() and (current.is_symlink() or bool(getattr(current.lstat(), "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))):
            raise ValueError("pilot output path must not traverse a reparse point")
        current = current.parent
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        raise ValueError("pilot output directory must be empty")
    return root


def safe_absent_temp_path(value: str | Path, repo_root: Path) -> Path:
    """Validate a fresh output path without creating it."""
    root = Path(value).absolute()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if root == temp_root or root.resolve() != root:
        raise ValueError("pilot output must be a dedicated resolved OS-temporary path")
    try: root.relative_to(temp_root)
    except ValueError as exc: raise ValueError("pilot output must be under the OS temporary directory") from exc
    try: root.relative_to(repo_root.resolve())
    except ValueError: pass
    else: raise ValueError("pilot output must be outside the repository")
    if root.exists() or root.is_symlink():
        raise ValueError("pilot output must be a fresh nonexistent path")
    parent = root.parent
    if not parent.is_dir() or parent.resolve() != parent:
        raise ValueError("pilot output parent must be an existing resolved directory")
    current = parent
    while current != temp_root:
        attrs = getattr(current.lstat(), "st_file_attributes", 0)
        if current.is_symlink() or bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise ValueError("pilot output parent must not traverse a reparse point")
        current = current.parent
    return root


def output_authority_payload(output: Path, claim_bytes: bytes, auth: str) -> dict[str, Any]:
    return {
        "schema": "context-pilot-output-authority.v1",
        "output_path_sha256": sha256_text(str(output.resolve())),
        "output_identity": path_identity(output),
        "claim_sha256": hashlib.sha256(claim_bytes).hexdigest(),
        "auth_sha256": sha256_text(auth),
    }


def verify_output_authority(output: Path, claim_path: Path, auth: str) -> bool:
    try:
        marker = output / PILOT_AUTHORITY_MARKER
        if not regular_non_reparse_file(marker): return False
        observed = json.loads(marker.read_text(encoding="utf-8"))
        expected = output_authority_payload(output, claim_path.read_bytes(), auth)
        return observed == expected
    except (OSError, ValueError, json.JSONDecodeError):
        return False


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def path_identity(path: Path) -> str:
    resolved = path.resolve(strict=True)
    info = resolved.stat()
    payload = {
        "resolved": str(resolved), "device": info.st_dev, "inode": info.st_ino,
        "mode": info.st_mode, "is_directory": resolved.is_dir(),
    }
    return fingerprint(payload)

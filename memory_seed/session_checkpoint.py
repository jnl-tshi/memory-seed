"""Evidence-backed session-record checkpoints.

The JSON file managed here is operational state only.  Markdown session entries
remain the durable authority; a new entry clears debt and establishes the next
Git evidence baseline.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .core import resolve_runtime, session_target


CHECKPOINT_STATE_VERSION = 2
STATE_NAME = ".session-log-check-state"
_ENTRY_HEADING_RE = re.compile(
    r"^##\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s+-\s+.*$", re.MULTILINE
)
_ENTRY_ID_RE = re.compile(r"^entry_id:\s*(mse_[a-z0-9]{16})\s*$", re.MULTILINE)
_EXCLUDE_PREFIXES = (
    ".memory-seed/sessions/",
    ".AGENTS/sessions/",
    ".memory-seed/.session-log-check-state",
)
_EXCLUDE_EXACT = {
    ".memory-seed/.retrieval-log.jsonl",
    ".memory-seed/.file-touch-stamp",
}


class CheckpointUnavailable(RuntimeError):
    """Evaluation cannot safely create record debt, so the caller must fail open."""


def _iso_minute(value: datetime) -> str:
    return value.replace(second=0, microsecond=0).isoformat(timespec="minutes")


def _run_git(root: Path, args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise CheckpointUnavailable(f"Git evidence unavailable: {exc}") from exc
    if check and result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise CheckpointUnavailable(f"Git evidence unavailable: {detail}")
    return result


def _excluded(path_text: str) -> bool:
    normalized = path_text.replace("\\", "/")
    return normalized in _EXCLUDE_EXACT or any(normalized.startswith(p) for p in _EXCLUDE_PREFIXES)


def _status_rows(root: Path) -> list[tuple[str, str]]:
    raw = _run_git(root, ["status", "--porcelain=v1", "--untracked-files=all"]).stdout
    rows: list[tuple[str, str]] = []
    for line in raw.splitlines():
        if len(line) < 4:
            continue
        code = line[:2]
        path_text = line[3:]
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1]
        path_text = path_text.strip('"').replace("\\", "/")
        if not _excluded(path_text):
            rows.append((code, path_text))
    return rows


def _git_snapshot(root: Path) -> dict[str, Any]:
    head = _run_git(root, ["rev-parse", "HEAD"]).stdout.strip()
    if not head:
        raise CheckpointUnavailable("Git evidence unavailable: HEAD could not be resolved")
    parts: list[str] = []
    rows = _status_rows(root)
    for code, path_text in rows:
        if "D" in code:
            digest = "DELETED"
        else:
            try:
                digest = hashlib.sha256((root / path_text).read_bytes()).hexdigest()
            except OSError as exc:
                raise CheckpointUnavailable(
                    f"Git evidence unavailable: could not read changed path {path_text}: {exc}"
                ) from exc
        parts.append(f"{code}:{path_text}:{digest}")
    fingerprint = ""
    if parts:
        fingerprint = hashlib.sha256("\n".join(sorted(parts)).encode("utf-8")).hexdigest()
    return {"head": head, "diff_fingerprint": fingerprint, "status_rows": rows}


def _latest_entry(target: Path) -> dict[str, Any]:
    if not target.exists():
        return {"identity": f"none:{target.as_posix()}", "entry_id": None, "timestamp": None}
    try:
        text = target.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise CheckpointUnavailable(f"Session target unavailable: {exc}") from exc
    headings = list(_ENTRY_HEADING_RE.finditer(text))
    if not headings:
        return {"identity": f"none:{target.as_posix()}", "entry_id": None, "timestamp": None}
    heading = headings[-1]
    block = text[heading.start() :]
    match = _ENTRY_ID_RE.search(block)
    entry_id = match.group(1) if match else None
    timestamp = heading.group(1)
    fallback = hashlib.sha256(block.encode("utf-8")).hexdigest()[:20]
    identity = f"{entry_id or 'legacy-' + fallback}@{timestamp}"
    return {"identity": identity, "entry_id": entry_id, "timestamp": timestamp}


def _state_path(root: Path) -> Path:
    runtime = resolve_runtime(root)
    return runtime.memory_dir / STATE_NAME


def _load_state(path: Path) -> tuple[dict[str, Any], bool]:
    if not path.exists():
        return {}, False
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise CheckpointUnavailable(f"Checkpoint state is unreadable or corrupt: {exc}") from exc
    if not isinstance(raw, dict):
        raise CheckpointUnavailable("Checkpoint state is corrupt: expected a JSON object")
    version = raw.get("schema_version")
    if version is None:
        # v1 compatibility: preserve the old diff baseline where possible, then
        # establish the missing HEAD baseline without inventing debt.
        return {
            "schema_version": CHECKPOINT_STATE_VERSION,
            "target": raw.get("target"),
            "latest_entry_identity": raw.get("last_seen_entry"),
            "latest_entry_timestamp": raw.get("last_seen_entry"),
            "baseline_head": None,
            "baseline_diff_fingerprint": raw.get("baseline_diff_fingerprint"),
            "pending_checkpoint": None,
            "clean_advisory_entry": None,
            "initialized_at": None,
            "last_mechanical_resolution": None,
        }, True
    if version != CHECKPOINT_STATE_VERSION:
        raise CheckpointUnavailable(
            f"Checkpoint state schema {version!r} is unsupported; expected {CHECKPOINT_STATE_VERSION}"
        )
    return raw, False


def _save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        temp.write_text(
            json.dumps(state, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        os.replace(temp, path)
    except OSError as exc:
        try:
            temp.unlink(missing_ok=True)
        except OSError:
            pass
        raise CheckpointUnavailable(f"Checkpoint state could not be written atomically: {exc}") from exc


def _checkpoint_id(
    latest_identity: str,
    baseline_head: str,
    current_head: str,
    baseline_diff: str,
    current_diff: str,
) -> str:
    material = "\0".join(
        (latest_identity, baseline_head, current_head, baseline_diff, current_diff)
    )
    return "msc_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def _result(
    *,
    ok: bool,
    target: str | None = None,
    latest: dict[str, Any] | None = None,
    pending: dict[str, Any] | None = None,
    clean_advisory: bool = False,
    resolution_status: str = "none",
    issues: list[str] | None = None,
) -> dict[str, Any]:
    latest = latest or {}
    evidence = list((pending or {}).get("evidence_kinds", []))
    if pending:
        required_action = "record-session-entry"
    elif clean_advisory:
        required_action = "self-check-only"
    else:
        required_action = "none"
    return {
        "ok": ok,
        "pending": bool(pending),
        "checkpoint_id": (pending or {}).get("checkpoint_id"),
        "evidence_kinds": evidence,
        "first_seen": (pending or {}).get("first_seen"),
        "required_action": required_action,
        "resolution_status": resolution_status,
        "clean_advisory": clean_advisory,
        "target": target,
        "latest_entry_id": latest.get("entry_id"),
        "latest_entry_timestamp": latest.get("timestamp"),
        "issues": issues or [],
    }


def inspect_checkpoint(
    cwd: str | Path = ".",
    *,
    now: datetime | None = None,
    deliver_clean_advisory: bool = False,
    explicit_user: str | None = None,
) -> dict[str, Any]:
    """Inspect checkpoint debt and optionally consume the clean-work advisory.

    A corrupt/unwritable state or unavailable Git repository returns
    ``ok=false, pending=false``.  Hooks therefore fail open instead of turning
    an environmental fault into record debt.
    """

    moment = now or datetime.now()
    root = resolve_runtime(cwd).workspace_root
    target = session_target(
        root,
        date_str=moment.strftime("%Y-%m-%d"),
        explicit_user=explicit_user,
    ).path
    target_label = target.relative_to(root).as_posix()
    try:
        latest = _latest_entry(target)
        snapshot = _git_snapshot(root)
        path = _state_path(root)
        state, legacy = _load_state(path)
        initialized = bool(state)

        same_entry = (
            initialized
            and state.get("target") == target_label
            and (
                state.get("latest_entry_identity") == latest["identity"]
                or (
                    legacy
                    and state.get("latest_entry_timestamp") == latest.get("timestamp")
                )
            )
        )
        prior_pending = state.get("pending_checkpoint") if isinstance(state.get("pending_checkpoint"), dict) else None
        resolution_status = "none"

        if not same_entry or not state.get("baseline_head"):
            state = {
                "schema_version": CHECKPOINT_STATE_VERSION,
                "target": target_label,
                "latest_entry_identity": latest["identity"],
                "latest_entry_timestamp": latest.get("timestamp"),
                "baseline_head": snapshot["head"],
                "baseline_diff_fingerprint": snapshot["diff_fingerprint"],
                "pending_checkpoint": None,
                "clean_advisory_entry": None,
                "initialized_at": _iso_minute(moment),
                "last_mechanical_resolution": state.get("last_mechanical_resolution"),
            }
            resolution_status = "cleared-by-new-entry" if prior_pending and not legacy else "baseline-initialized"
            pending = None
        else:
            baseline_head = str(state.get("baseline_head") or "")
            baseline_diff = str(state.get("baseline_diff_fingerprint") or "")
            evidence: list[str] = []
            if snapshot["head"] != baseline_head:
                evidence.append("head")
            if snapshot["diff_fingerprint"] != baseline_diff:
                evidence.append("worktree")
            pending = None
            if evidence:
                identifier = _checkpoint_id(
                    latest["identity"],
                    baseline_head,
                    snapshot["head"],
                    baseline_diff,
                    snapshot["diff_fingerprint"],
                )
                first_seen = _iso_minute(moment)
                if prior_pending and prior_pending.get("checkpoint_id") == identifier:
                    first_seen = str(prior_pending.get("first_seen") or first_seen)
                pending = {
                    "checkpoint_id": identifier,
                    "evidence_kinds": evidence,
                    "first_seen": first_seen,
                    "latest_entry_identity": latest["identity"],
                    "baseline_head": baseline_head,
                    "current_head": snapshot["head"],
                    "baseline_diff_fingerprint": baseline_diff,
                    "current_diff_fingerprint": snapshot["diff_fingerprint"],
                }
            elif prior_pending:
                # Evidence returning to the baseline does not prove that the
                # intermediate work needed no record. Preserve the original,
                # stable checkpoint until a new entry or explicit mechanical
                # proof resolves it.
                pending = prior_pending
                resolution_status = "pending-evidence-at-baseline"
            state["pending_checkpoint"] = pending

        clean_due = False
        if pending is None and state.get("clean_advisory_entry") != latest["identity"]:
            anchor_text = latest.get("timestamp") or state.get("initialized_at")
            if anchor_text:
                try:
                    anchor = datetime.fromisoformat(str(anchor_text))
                    clean_due = moment >= anchor + timedelta(minutes=15)
                except ValueError:
                    clean_due = False
        if clean_due and deliver_clean_advisory:
            # Persist consumption before the hook emits. Claude may force one
            # continuation to make the advisory model-visible; the replay must
            # then stay silent.
            state["clean_advisory_entry"] = latest["identity"]

        _save_state(path, state)
        return _result(
            ok=True,
            target=target_label,
            latest=latest,
            pending=pending,
            clean_advisory=clean_due,
            resolution_status=resolution_status,
        )
    except CheckpointUnavailable as exc:
        return _result(ok=False, target=target_label, issues=[str(exc)])
    except (OSError, UnicodeError, ValueError) as exc:
        return _result(
            ok=False,
            target=target_label,
            issues=[f"Checkpoint evaluation unavailable: {exc}"],
        )


def _mechanical_proof_issues(root: Path, state: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    baseline_head = state.get("baseline_head")
    baseline_diff = state.get("baseline_diff_fingerprint")
    if baseline_diff != "":
        issues.append("whitespace-only proof requires a clean baseline")
    if not isinstance(baseline_head, str) or not baseline_head:
        issues.append("whitespace-only proof requires a known baseline HEAD")
        return issues

    snapshot = _git_snapshot(root)
    if snapshot["head"] != baseline_head:
        issues.append("whitespace-only proof refuses a changed HEAD")
    if any(code == "??" for code, _ in snapshot["status_rows"]):
        issues.append("whitespace-only proof refuses untracked paths")

    names = _run_git(root, ["diff", "--name-status", "--find-renames", baseline_head, "--"]).stdout
    for line in names.splitlines():
        if not line.strip():
            continue
        status = line.split("\t", 1)[0]
        if status != "M":
            issues.append(
                "whitespace-only proof refuses added, deleted, renamed, copied, or type-changed paths"
            )
            break
    numstat = _run_git(root, ["diff", "--numstat", baseline_head, "--"]).stdout
    if any(line.startswith("-\t-\t") for line in numstat.splitlines()):
        issues.append("whitespace-only proof refuses binary changes")
    semantic = _run_git(
        root,
        ["diff", "--quiet", "--ignore-all-space", "--ignore-blank-lines", baseline_head, "--"],
        check=False,
    )
    if semantic.returncode not in (0, 1):
        raise CheckpointUnavailable("Git could not evaluate whitespace-only proof")
    if semantic.returncode == 1:
        issues.append("whitespace-only proof found semantic changes")
    return issues


def resolve_checkpoint(
    cwd: str | Path = ".",
    *,
    checkpoint_id: str,
    proof: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Resolve a pending checkpoint using the closed mechanical proof v1."""

    if proof != "whitespace-only":
        return _result(ok=False, issues=["unsupported proof; expected 'whitespace-only'"])
    moment = now or datetime.now()
    root = resolve_runtime(cwd).workspace_root
    inspected = inspect_checkpoint(root, now=moment, deliver_clean_advisory=False)
    if not inspected["ok"]:
        return inspected
    if not inspected["pending"]:
        return _result(
            ok=False,
            target=inspected.get("target"),
            issues=["no pending checkpoint exists"],
        )
    if inspected["checkpoint_id"] != checkpoint_id:
        return _result(
            ok=False,
            target=inspected.get("target"),
            issues=["stale checkpoint id; inspect again before resolving"],
        )

    try:
        path = _state_path(root)
        state, _ = _load_state(path)
        pending = state.get("pending_checkpoint")
        if not isinstance(pending, dict) or pending.get("checkpoint_id") != checkpoint_id:
            return _result(ok=False, issues=["stale checkpoint id; inspect again before resolving"])
        issues = _mechanical_proof_issues(root, state)
        if issues:
            return {
                **inspected,
                "ok": False,
                "resolution_status": "refused",
                "issues": issues,
            }
        snapshot = _git_snapshot(root)
        state["baseline_head"] = snapshot["head"]
        state["baseline_diff_fingerprint"] = snapshot["diff_fingerprint"]
        state["pending_checkpoint"] = None
        state["clean_advisory_entry"] = state.get("latest_entry_identity")
        state["last_mechanical_resolution"] = {
            "checkpoint_id": checkpoint_id,
            "proof": proof,
            "resolved_at": _iso_minute(moment),
        }
        _save_state(path, state)
        latest = {
            "entry_id": inspected.get("latest_entry_id"),
            "timestamp": inspected.get("latest_entry_timestamp"),
        }
        return _result(
            ok=True,
            target=inspected.get("target"),
            latest=latest,
            resolution_status="mechanical-whitespace-only",
        )
    except CheckpointUnavailable as exc:
        return _result(ok=False, issues=[str(exc)])


__all__ = [
    "CHECKPOINT_STATE_VERSION",
    "inspect_checkpoint",
    "resolve_checkpoint",
]

"""Incremental, derived verification of decision timestamp lineage.

Git can establish a relative ordering in reachable history.  It cannot prove
wall-clock time on its own, because commit clocks are locally controlled.  This
module records that distinction explicitly and keeps only a rebuildable JSON
projection beside retrieval-attention state.
"""

from __future__ import annotations

import json
import os
import hashlib
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .provenance_git import GitUnavailableError, _git, git_available, git_head


TEMPORAL_LINEAGE_SCHEMA = "memory-seed/temporal-lineage-cache"
TEMPORAL_LINEAGE_VERSION = 1
CACHE_NAME = ".temporal-lineage.json"
GITIGNORE_ENTRY = f".memory-seed/{CACHE_NAME}"
_DECISION_REF = re.compile(r"(?:ms-[0-9a-f]{8}|mse_[0-9a-z]{8,32}):d[1-9][0-9]*\Z")


def temporal_lineage_cache_path(cwd: str | Path = ".") -> Path:
    return Path(cwd) / ".memory-seed" / CACHE_NAME


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat(timespec="seconds") if value is not None else None


def _decision_value(value: Mapping[str, Any]) -> dict[str, Any]:
    ref = value.get("decision_ref", value.get("id"))
    digest = value.get("source_digest", value.get("content_digest"))
    claimed = value.get("claimed_timestamp", value.get("timestamp"))
    source_path = value.get("source_path", value.get("source"))
    needle = value.get("needle", value.get("source_text", ref))
    if not isinstance(ref, str) or not _DECISION_REF.fullmatch(ref.strip()):
        raise ValueError("decision_ref must be an exact <entry_id>:dN reference")
    if not isinstance(digest, str) or not digest.strip():
        raise ValueError("source_digest is required")
    if not isinstance(claimed, str) or _parse_timestamp(claimed) is None:
        raise ValueError("claimed_timestamp must be an ISO-8601 timestamp")
    if source_path is not None and (not isinstance(source_path, str) or not source_path.strip()):
        raise ValueError("source_path must be a non-empty path when supplied")
    if not isinstance(needle, str) or not needle:
        raise ValueError("decision needle must be a non-empty string")
    return {
        "decision_ref": ref.strip(),
        "source_digest": digest.strip(),
        "claimed_timestamp": _iso(_parse_timestamp(claimed)),
        "source_path": source_path.replace("\\", "/") if isinstance(source_path, str) else None,
        "needle": needle,
    }


def _load_cache(path: Path) -> tuple[dict[str, Any] | None, str]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "missing"
    except (OSError, ValueError, json.JSONDecodeError):
        return None, "corrupt"
    if not isinstance(payload, dict):
        return None, "corrupt"
    if payload.get("schema") != TEMPORAL_LINEAGE_SCHEMA or payload.get("version") != TEMPORAL_LINEAGE_VERSION:
        return None, "incompatible"
    if not isinstance(payload.get("head"), str) or not isinstance(payload.get("decisions"), dict):
        return None, "corrupt"
    return payload, "available"


def _head_reachable(cwd: str | Path, cached_head: str, current_head: str) -> bool:
    completed = subprocess.run(
        ["git", "-C", str(cwd), "merge-base", "--is-ancestor", cached_head, current_head],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return completed.returncode == 0


def _commit_timestamp(cwd: str | Path, commit: str) -> datetime | None:
    try:
        raw = _git(cwd, "show", "-s", "--format=%cI", commit).decode("ascii", "strict").strip()
    except GitUnavailableError:
        return None
    return _parse_timestamp(raw)


def _first_introducing_commit(cwd: str | Path, decision: Mapping[str, Any]) -> str | None:
    """Find the earliest reachable commit containing the decision's exact needle."""

    args = ["rev-list", "--reverse", "HEAD"]
    if decision["source_path"]:
        args.extend(["--", decision["source_path"]])
    commits = _git(cwd, *args).decode("ascii", "strict").splitlines()
    for commit in commits:
        try:
            if decision["source_path"]:
                content = _git(cwd, "show", f"{commit}:{decision['source_path']}")
            else:
                # No source file still permits evidence, but requires Git's
                # pickaxe rather than silently asserting a source location.
                matches = _git(cwd, "log", "--format=%H", "-1", "-S", decision["needle"], commit)
                if matches.decode("ascii", "strict").strip() != commit:
                    continue
                return commit
        except GitUnavailableError:
            continue
        if decision["needle"].encode("utf-8") in content:
            return commit
    return None


def _checkpoint_records(
    checkpoints: Iterable[Mapping[str, Any]] | Mapping[str, Any],
) -> list[dict[str, str]]:
    values: Iterable[Any]
    if isinstance(checkpoints, Mapping):
        values = ({"commit": commit, "witnessed_at": timestamp} for commit, timestamp in checkpoints.items())
    else:
        values = checkpoints
    normalized: list[dict[str, str]] = []
    for item in values:
        if not isinstance(item, Mapping):
            continue
        commit = item.get("commit")
        witnessed = item.get("witnessed_at", item.get("timestamp"))
        if isinstance(commit, str) and isinstance(witnessed, str) and _parse_timestamp(witnessed) is not None:
            normalized.append({"commit": commit, "witnessed_at": _iso(_parse_timestamp(witnessed)) or ""})
    return sorted(normalized, key=lambda item: (item["witnessed_at"], item["commit"]))


def _checkpoint_fingerprint(checkpoints: Sequence[Mapping[str, str]]) -> str:
    encoded = json.dumps(list(checkpoints), sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _is_ancestor(cwd: str | Path, earlier: str, later: str) -> bool:
    return _head_reachable(cwd, earlier, later)


def _classify(
    cwd: str | Path,
    decision: Mapping[str, Any],
    first_commit: str | None,
    checkpoints: Sequence[Mapping[str, str]],
    now: datetime,
) -> dict[str, Any]:
    claimed = _parse_timestamp(decision["claimed_timestamp"])
    assert claimed is not None
    commit_time = _commit_timestamp(cwd, first_commit) if first_commit else None
    if first_commit is None:
        relative = "not-found"
    else:
        relative = "verified-reachable-order"
    if claimed > now:
        claim_relation = "future-dated"
    elif commit_time is None:
        claim_relation = "uncompared"
    elif claimed < commit_time:
        claim_relation = "backdated-relative-to-commit-clock"
    elif claimed > commit_time:
        claim_relation = "postdated-relative-to-commit-clock"
    else:
        claim_relation = "same-as-commit-clock"
    witnesses = [
        dict(checkpoint)
        for checkpoint in checkpoints
        if first_commit is not None and _is_ancestor(cwd, first_commit, checkpoint["commit"])
    ]
    calendar = "independently-witnessed" if witnesses else "unwitnessed"
    return {
        "first_introducing_commit": first_commit,
        "commit_timestamp": _iso(commit_time),
        "relative_order": relative,
        "claimed_timestamp_relation": claim_relation,
        "calendar_time": calendar,
        "trusted_checkpoint_evidence": witnesses,
    }


def _ensure_ignored(cwd: Path) -> None:
    """Make the derived cache disposable when it is first published."""

    try:
        from .core import _ensure_gitignore_entry

        _ensure_gitignore_entry(cwd, GITIGNORE_ENTRY)
    except Exception:
        # The cache remains derived even when a repository is read-only. Its
        # publication must never change the verification result.
        return


def _write_cache(path: Path, payload: Mapping[str, Any]) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, path)
        return True
    except OSError:
        return False


def refresh_temporal_lineage(
    cwd: str | Path,
    decisions: Iterable[Mapping[str, Any]],
    *,
    cache_path: str | Path | None = None,
    trusted_checkpoints: Iterable[Mapping[str, Any]] | Mapping[str, Any] = (),
    now: datetime | None = None,
) -> dict[str, Any]:
    """Rebuild or incrementally refresh the derived lineage projection.

    Unchanged exact decision identities reuse their previous result when the
    cached head is an ancestor of current ``HEAD``.  A rewrite makes that claim
    unsafe, so every cached result is invalidated and reconstructed.  No network
    clock or provider assertion is consulted.
    """

    source = [_decision_value(value) for value in decisions]
    if len({item["decision_ref"] for item in source}) != len(source):
        raise ValueError("decision refs must be unique within a lineage refresh")
    root = Path(cwd)
    path = Path(cache_path) if cache_path is not None else temporal_lineage_cache_path(root)
    if not git_available(root):
        return {
            "schema": TEMPORAL_LINEAGE_SCHEMA,
            "version": TEMPORAL_LINEAGE_VERSION,
            "git_available": False,
            "cache_status": "git-unavailable",
            "decisions": {},
            "reused": [],
            "recomputed": [item["decision_ref"] for item in source],
            "invalidated": False,
        }
    head = git_head(root)
    cached, cache_status = _load_cache(path)
    reachable = bool(cached and _head_reachable(root, cached["head"], head))
    invalidated = bool(cached and not reachable)
    if invalidated:
        cache_status = "rewritten-ancestry"
        cached = None
    checkpoints = _checkpoint_records(trusted_checkpoints)
    checkpoint_fingerprint = _checkpoint_fingerprint(checkpoints)
    moment = now.astimezone(timezone.utc) if now and now.tzinfo else (now.replace(tzinfo=timezone.utc) if now else datetime.now(timezone.utc))
    prior = cached.get("decisions", {}) if cached else {}
    output: dict[str, dict[str, Any]] = {}
    reused: list[str] = []
    recomputed: list[str] = []
    for item in source:
        previous = prior.get(item["decision_ref"])
        same_source = isinstance(previous, Mapping) and all(
            previous.get(key) == item[key] for key in ("source_digest", "claimed_timestamp", "source_path")
        ) and cached.get("checkpoint_fingerprint") == checkpoint_fingerprint
        if same_source:
            record = dict(previous)
            record["last_checked_git_head"] = head
            output[item["decision_ref"]] = record
            reused.append(item["decision_ref"])
            continue
        classification = _classify(root, item, _first_introducing_commit(root, item), checkpoints, moment)
        output[item["decision_ref"]] = {
            "source_digest": item["source_digest"],
            "claimed_timestamp": item["claimed_timestamp"],
            "source_path": item["source_path"],
            "last_checked_git_head": head,
            **classification,
        }
        recomputed.append(item["decision_ref"])
    payload = {
        "schema": TEMPORAL_LINEAGE_SCHEMA,
        "version": TEMPORAL_LINEAGE_VERSION,
        "head": head,
        "checkpoint_fingerprint": checkpoint_fingerprint,
        "decisions": output,
    }
    _ensure_ignored(root)
    published = _write_cache(path, payload)
    return {
        **payload,
        "git_available": True,
        "cache_status": cache_status,
        "cache_published": published,
        "reused": reused,
        "recomputed": recomputed,
        "invalidated": invalidated,
    }


# A compact name for future ESR integration without coupling this module to ESR.
refresh = refresh_temporal_lineage

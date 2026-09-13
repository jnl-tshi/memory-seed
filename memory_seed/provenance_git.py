"""Git-backed, reference-only provenance derivation and projection.

This is deliberately an adapter around :mod:`memory_seed.provenance`: bindings
retain only Git object ids, ranges, and a digest of each exact unified-hunk body.
Source text is read only while a caller asks for a projection; it is never put in
the binding or a cache.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping, Sequence

from .provenance import (
    PATCH_BYTES_CANONICALIZATION,
    ProvenanceValidationError,
    build_binding,
    normalize_binding,
    patch_bytes_digest,
)


EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
GIT_PROJECTION_SCHEMA = "memory-seed/git-provenance-projection"
GIT_PROJECTION_VERSION = 1
_DECISION_REF = re.compile(r"(?:ms-[0-9a-f]{8}|mse_[0-9a-z]{8,32}):d[1-9][0-9]*\Z")
_PATH_METACHAR = re.compile(r'[*?\[\]{}!<>:"|]')
_HUNK_HEADER = re.compile(
    rb"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    rb"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
)


class GitUnavailableError(RuntimeError):
    """Git could not be used from the requested repository."""


class GitEvidenceError(RuntimeError):
    """A claimed binding does not match the objects currently in Git."""


@dataclass(frozen=True)
class DecisionCandidate:
    """A decision plus the exact runtime-relative paths it declares in ``F:``.

    The engine intentionally has no Markdown parser.  A caller supplies already
    extracted decision identities and exact file values; wildcards and directory
    prefixes never match a changed path.
    """

    decision_ref: str
    files: frozenset[str]
    reason: str | None = None

    @classmethod
    def from_value(cls, value: Mapping[str, Any]) -> "DecisionCandidate":
        ref = str(value.get("decision_ref") or value.get("id") or "").strip()
        if not _DECISION_REF.fullmatch(ref):
            raise ValueError("decision_ref must be an exact <entry_id>:dN reference")
        paths = value.get("files", value.get("f_paths", ()))
        if isinstance(paths, str):
            paths = (paths,)
        if not isinstance(paths, Sequence):
            raise ValueError("candidate files must be a sequence of exact paths")
        return cls(ref, frozenset(_safe_path(path) for path in paths), _optional_text(value.get("reason")))


def _optional_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _safe_path(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("file paths must be non-empty strings")
    text = value.strip().replace("\\", "/")
    path = PurePosixPath(text)
    if (
        path.is_absolute()
        or any(part in {"", ".", ".."} for part in text.split("/"))
        or _PATH_METACHAR.search(text)
    ):
        raise ValueError("file paths must be safe runtime-relative POSIX paths")
    return path.as_posix()


def _git(cwd: str | Path, *args: str, input: bytes | None = None) -> bytes:
    """Run one non-shell Git command and turn availability failures into one type."""

    try:
        completed = subprocess.run(
            ["git", "-C", str(cwd), *args],
            input=input,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as error:
        raise GitUnavailableError(str(error)) from error
    if completed.returncode:
        message = completed.stderr.decode("utf-8", "replace").strip()
        raise GitUnavailableError(message or f"git {' '.join(args)} failed")
    return completed.stdout


def git_available(cwd: str | Path = ".") -> bool:
    try:
        _git(cwd, "rev-parse", "--git-dir")
    except GitUnavailableError:
        return False
    return True


def git_head(cwd: str | Path = ".") -> str:
    return _git(cwd, "rev-parse", "HEAD").decode("ascii", "strict").strip()


def _parents(cwd: str | Path, commit: str) -> list[str]:
    fields = _git(cwd, "rev-list", "--parents", "-n", "1", commit).decode("ascii", "strict").split()
    if not fields:
        raise GitUnavailableError(f"commit {commit!r} does not resolve")
    return fields[1:]


def _blob_id(cwd: str | Path, treeish: str | None, path: str) -> str | None:
    if treeish is None:
        return None
    completed = subprocess.run(
        ["git", "-C", str(cwd), "rev-parse", f"{treeish}:{path}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        return None
    value = completed.stdout.decode("ascii", "strict").strip()
    return value if re.fullmatch(r"[0-9a-f]{40,64}", value) else None


def _changed_paths(cwd: str | Path, commit: str, parent: str | None) -> list[str]:
    base = parent or EMPTY_TREE
    raw = _git(cwd, "diff-tree", "--no-commit-id", "--name-only", "-r", "-z", "--no-renames", base, commit)
    return [_safe_path(name.decode("utf-8", "surrogateescape")) for name in raw.split(b"\0") if name]


def _parse_hunks(patch: bytes) -> list[dict[str, Any]]:
    """Parse only unified-diff range markers; no language or symbol parsing."""

    found: list[dict[str, Any]] = []
    current_header: re.Match[bytes] | None = None
    current_body: list[bytes] = []
    for line in patch.splitlines(keepends=True):
        matched = _HUNK_HEADER.match(line)
        if matched:
            if current_header is not None:
                found.append(_hunk_from_parts(current_header, current_body))
            current_header, current_body = matched, []
        elif current_header is not None:
            current_body.append(line)
    if current_header is not None:
        found.append(_hunk_from_parts(current_header, current_body))
    return found


def _hunk_from_parts(header: re.Match[bytes], body: Sequence[bytes]) -> dict[str, Any]:
    def number(name: str, default: int) -> int:
        value = header.group(name)
        return int(value) if value is not None else default

    # The byte sequence begins after ``@@`` by contract: headers are locators,
    # while the exact added/removed/context lines are the hunk body evidence.
    digest = "sha256:" + hashlib.sha256(b"".join(body)).hexdigest()
    return {
        "old_range": {"start": number("old_start", 0), "count": number("old_count", 1)},
        "new_range": {"start": number("new_start", 0), "count": number("new_count", 1)},
        "patch_bytes": patch_bytes_digest(digest),
        "context_hint": None,
    }


def _file_hunks(cwd: str | Path, commit: str, parent: str | None, path: str) -> list[dict[str, Any]]:
    if parent is None:
        patch = _git(cwd, "diff-tree", "--root", "--no-commit-id", "-p", "-U0", "--no-renames", commit, "--", path)
    else:
        patch = _git(cwd, "diff", "--no-ext-diff", "-U0", "--no-renames", parent, commit, "--", path)
    return _parse_hunks(patch)


def parse_memory_implements(message: str) -> list[str]:
    """Read ``Memory-Implements:`` trailers, preserving trailer order and uniqueness."""

    values: list[str] = []
    for line in message.splitlines():
        if not line.lower().startswith("memory-implements:"):
            continue
        for item in re.split(r"[\s,]+", line.split(":", 1)[1].strip()):
            if item and _DECISION_REF.fullmatch(item) and item not in values:
                values.append(item)
    return values


def commit_memory_implements(cwd: str | Path, commit: str) -> list[str]:
    return parse_memory_implements(_git(cwd, "show", "-s", "--format=%B", commit).decode("utf-8", "replace"))


def _candidate_index(candidates: Iterable[DecisionCandidate | Mapping[str, Any]]) -> dict[str, DecisionCandidate]:
    indexed: dict[str, DecisionCandidate] = {}
    for raw in candidates:
        candidate = raw if isinstance(raw, DecisionCandidate) else DecisionCandidate.from_value(raw)
        if candidate.decision_ref in indexed and indexed[candidate.decision_ref] != candidate:
            raise ValueError(f"conflicting candidate definitions for {candidate.decision_ref}")
        indexed[candidate.decision_ref] = candidate
    return indexed


def resolve_attribution(
    changed_files: Iterable[str],
    candidates: Iterable[DecisionCandidate | Mapping[str, Any]],
    *,
    memory_implements: Iterable[str] = (),
) -> dict[str, Any]:
    """Resolve only unambiguous per-file attribution.

    Resolution is intentionally narrow and deterministic:

    1. If valid ``Memory-Implements`` refs are supplied, they constrain the
       candidate pool (unknown explicit refs are reported, not guessed).
    2. Every decision/file pair must be an exact ``F:`` path equality.
    3. One match becomes automatic; multiple matches remain shared and zero
       matches remain unmatched.  Neither shared nor unmatched candidates cause
       a binding to be manufactured.
    """

    indexed = _candidate_index(candidates)
    explicit: list[str] = []
    for value in memory_implements:
        if not isinstance(value, str) or not _DECISION_REF.fullmatch(value):
            raise ValueError("Memory-Implements values must be exact decision references")
        if value not in explicit:
            explicit.append(value)
    pool = [indexed[ref] for ref in explicit if ref in indexed] if explicit else list(indexed.values())
    automatic: list[dict[str, str]] = []
    shared: list[dict[str, Any]] = []
    unmatched: list[str] = []
    for raw_path in changed_files:
        path = _safe_path(raw_path)
        matches = sorted(candidate.decision_ref for candidate in pool if path in candidate.files)
        if len(matches) == 1:
            automatic.append({"file": path, "decision_ref": matches[0]})
        elif matches:
            shared.append({"file": path, "decision_refs": matches})
        else:
            unmatched.append(path)
    return {
        "resolution_order": ["memory-implements", "exact-f-path", "unique-automatic"],
        "explicit_decision_refs": explicit,
        "unknown_explicit_decision_refs": [ref for ref in explicit if ref not in indexed],
        "automatic": automatic,
        "shared": shared,
        "unmatched": unmatched,
    }


def derive_commit_bindings(
    cwd: str | Path,
    commit: str,
    candidates: Iterable[DecisionCandidate | Mapping[str, Any]],
    *,
    authorship: Mapping[str, Any],
    memory_implements: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Derive bindings for a non-merge commit without retaining source text.

    A merge is an integration event, not a second implementation claim.  It is
    returned as ``integration-only`` and neither its combined diff nor either
    parent is used to create a duplicate binding.
    """

    parents = _parents(cwd, commit)
    if len(parents) > 1:
        return {
            "commit": commit,
            "mode": "integration-only",
            "parents": parents,
            "bindings": [],
            "resolution": {"automatic": [], "shared": [], "unmatched": []},
        }
    parent = parents[0] if parents else None
    changed = _changed_paths(cwd, commit, parent)
    explicit = list(memory_implements) if memory_implements is not None else commit_memory_implements(cwd, commit)
    resolution = resolve_attribution(changed, candidates, memory_implements=explicit)
    bindings: list[dict[str, Any]] = []
    successful_automatic: list[dict[str, str]] = []
    for item in resolution["automatic"]:
        path = item["file"]
        hunks = _file_hunks(cwd, commit, parent, path)
        # Binary changes have no unified hunk body and cannot support a hunk
        # reference. They stay visible to the caller as unmatched evidence.
        if not hunks:
            resolution["unmatched"].append(path)
            continue
        old_blob = _blob_id(cwd, parent, path)
        new_blob = _blob_id(cwd, commit, path)
        if old_blob is None and new_blob is None:
            resolution["unmatched"].append(path)
            continue
        for hunk in hunks:
            from .provenance import hunk_id

            hunk["hunk_id"] = hunk_id(
                commit=commit,
                parent=parent,
                file=path,
                old_range=hunk["old_range"],
                new_range=hunk["new_range"],
                patch_bytes=hunk["patch_bytes"],
            )
        bindings.append(build_binding(
            decision_ref=item["decision_ref"], authorship=authorship, commit=commit,
            parent=parent, file=path, old_blob=old_blob, new_blob=new_blob, hunks=hunks,
        ))
        successful_automatic.append(item)
    # A path that has no hunk cannot be automatically attributed, even if it
    # originally matched exactly. Report each path once and leave automatic as a
    # faithful record of resolution rather than a claim that binding succeeded.
    resolution["unmatched"] = sorted(set(resolution["unmatched"]))
    resolution["automatic"] = successful_automatic
    return {"commit": commit, "mode": "derived", "parent": parent, "bindings": bindings, "resolution": resolution}


def _verification_failure(code: str, message: str) -> dict[str, Any]:
    return {"verified": False, "evidence_state": code, "reason": message}


def verify_binding_git(binding: Mapping[str, Any], cwd: str | Path = ".") -> dict[str, Any]:
    """Independently reconstruct binding evidence and reject object/range tampering."""

    try:
        normalized = normalize_binding(binding)
    except ProvenanceValidationError as error:
        return _verification_failure("invalid-binding", str(error))
    try:
        _git(cwd, "cat-file", "-e", f"{normalized['commit']}^{{commit}}")
        actual_parents = _parents(cwd, normalized["commit"])
        if len(actual_parents) > 1:
            return _verification_failure("integration-only", "merge commits are integration-only")
        actual_parent = actual_parents[0] if actual_parents else None
        if actual_parent != normalized["parent"]:
            return _verification_failure("parent-mismatch", "binding parent does not match commit history")
        old_blob = _blob_id(cwd, actual_parent, normalized["file"])
        new_blob = _blob_id(cwd, normalized["commit"], normalized["file"])
        if old_blob != normalized["old_blob"] or new_blob != normalized["new_blob"]:
            return _verification_failure("blob-mismatch", "binding blobs do not match commit trees")
        observed = _file_hunks(cwd, normalized["commit"], actual_parent, normalized["file"])
        expected = [
            (hunk["old_range"], hunk["new_range"], hunk["patch_bytes"]["digest"])
            for hunk in normalized["hunks"]
        ]
        seen = [(item["old_range"], item["new_range"], item["patch_bytes"]["digest"]) for item in observed]
        if expected != seen:
            return _verification_failure("hunk-mismatch", "binding hunk ranges or exact patch-byte digests differ")
    except GitUnavailableError as error:
        return _verification_failure("git-unavailable", str(error))
    return {"verified": True, "evidence_state": "available", "reason": None}


def _bounded_context(value: int, name: str) -> int:
    if type(value) is not int or not 0 <= value <= 20:
        raise ValueError(f"{name} must be an integer from 0 through 20")
    return value


def _blob_lines(cwd: str | Path, blob: str | None) -> list[str] | None:
    if blob is None:
        return []
    try:
        raw = _git(cwd, "cat-file", "blob", blob)
    except GitUnavailableError:
        return None
    return raw.decode("utf-8", "surrogateescape").splitlines()


def _range_projection(lines: list[str], focus: Mapping[str, int], before: int, after: int) -> dict[str, Any]:
    start, count = focus["start"], focus["count"]
    # Empty-side unified ranges use start 0. They have no historical source line
    # but still return a precise empty range with bounded context.
    first = max(1, start - before) if start else 1
    last_focus = start + max(count - 1, 0)
    last = min(len(lines), last_focus + after) if last_focus else min(len(lines), after)
    return {
        "focus": {"start": start, "count": count},
        "range": {"start": first, "end": last},
        "lines": [{"number": index, "text": lines[index - 1]} for index in range(first, last + 1)],
    }


def project_binding(
    binding: Mapping[str, Any],
    cwd: str | Path = ".",
    *,
    before: int = 3,
    after: int = 3,
    decision: Mapping[str, Any] | str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    """Render verified historical ranges on demand; never persist the rendered code."""

    before, after = _bounded_context(before, "before"), _bounded_context(after, "after")
    normalized = normalize_binding(binding)
    if reason is None and isinstance(decision, Mapping):
        reason = _optional_text(decision.get("reason"))
    verification = verify_binding_git(normalized, cwd)
    projection: dict[str, Any] = {
        "schema": GIT_PROJECTION_SCHEMA,
        "version": GIT_PROJECTION_VERSION,
        "binding_id": normalized["binding_id"],
        "decision_ref": normalized["decision_ref"],
        "decision": decision if decision is not None else {"ref": normalized["decision_ref"]},
        "reason": reason,
        "verification": verification,
        "code_available": False,
        "context": {"before": before, "after": after},
        "hunks": [],
    }
    if not verification["verified"]:
        return projection
    old_lines = _blob_lines(cwd, normalized["old_blob"])
    new_lines = _blob_lines(cwd, normalized["new_blob"])
    if old_lines is None or new_lines is None:
        projection["verification"] = _verification_failure("git-unavailable", "a referenced blob is unavailable")
        return projection
    projection["code_available"] = True
    projection["hunks"] = [
        {
            "hunk_id": hunk["hunk_id"],
            "file": normalized["file"],
            "before": _range_projection(old_lines, hunk["old_range"], before, after),
            "after": _range_projection(new_lines, hunk["new_range"], before, after),
        }
        for hunk in normalized["hunks"]
    ]
    return projection


# Short aliases make the adapter easy for future CLI/MCP callers to discover.
derive_bindings = derive_commit_bindings
verify_binding = verify_binding_git

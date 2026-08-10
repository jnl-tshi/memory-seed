"""Fail-closed, reconstructable corpus projections.

The Markdown corpus is always authoritative.  This module only keeps a private,
best-effort copy outside the repository to avoid repeating the deterministic
parse/sidecar composition within and across invocations.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import subprocess
import tempfile
import time
from dataclasses import dataclass, fields
from datetime import date, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from .core import (
    iter_link_sidecar_documents,
    iter_session_documents,
    iter_topic_sidecar_documents,
    resolve_runtime,
)
from .semantic_cache import ContinuityBlock, MemoryChunk


CACHE_SCHEMA_VERSION = 1
SERIALIZER_VERSION = 2
_GRANULARITIES = ("entry", "section", "decision")
_VIEWS = ("raw", "augmented")
# This literal is intentionally not derived from ``fields(MemoryChunk)``.  A
# new field is a serializer contract change: make its representation explicit
# and bump SERIALIZER_VERSION rather than silently emitting an incomplete view.
_SERIALIZED_CHUNK_FIELDS = (
    "chunk_id", "source_path", "source_file", "session_date", "entry_datetime", "heading_path",
    "heading_level", "title", "text", "tags", "contexts", "lexical_terms", "start_line",
    "end_line", "entry_id", "user_initials", "agent_type", "project_path", "subproject_path",
    "user", "file_hash_id", "related_entries", "replaces", "evolves", "decision_edges",
    "commits", "continuity", "topics", "inferred_topics", "inferred_decision_topics", "branch",
    "entry_title", "entry_line_range", "sections", "granularity",
)
_CHUNK_FIELDS = _SERIALIZED_CHUNK_FIELDS
_TUPLE_FIELDS = {
    "heading_path", "tags", "contexts", "lexical_terms", "related_entries", "replaces",
    "evolves", "decision_edges", "commits", "continuity", "topics", "inferred_topics",
    "inferred_decision_topics", "sections",
}


def _serializer_is_compatible() -> bool:
    """Whether this package can faithfully encode/decode the current chunk model."""
    return tuple(field.name for field in fields(MemoryChunk)) == _SERIALIZED_CHUNK_FIELDS


@dataclass(frozen=True)
class CorpusSnapshot:
    """Immutable raw and augmented corpus views from one verified source state."""

    origin: str
    fingerprint: str | None
    _views: Mapping[tuple[str, str], tuple[MemoryChunk, ...]]

    @classmethod
    def empty(cls, *, origin: str = "isolated") -> "CorpusSnapshot":
        return cls(
            origin,
            None,
            MappingProxyType({(granularity, view): () for granularity in _GRANULARITIES for view in _VIEWS}),
        )

    def chunks(self, granularity: str = "decision", view: str = "augmented") -> tuple[MemoryChunk, ...]:
        if granularity not in _GRANULARITIES:
            raise ValueError("granularity must be 'entry', 'decision' or 'section'")
        if view not in _VIEWS:
            raise ValueError("view must be 'raw' or 'augmented'")
        return self._views[(granularity, view)]


def _git_identity(workspace_root: Path, memory_dir: Path) -> dict[str, str] | None:
    def git(*args: str) -> str | None:
        try:
            result = subprocess.run(
                ["git", "-C", str(workspace_root), *args], capture_output=True,
                text=True, timeout=3, check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return result.stdout.strip() if result.returncode == 0 and result.stdout.strip() else None

    head = git("rev-parse", "HEAD")
    common = git("rev-parse", "--git-common-dir")
    git_dir = git("rev-parse", "--git-dir")
    if not (head and common and git_dir):
        return None

    def resolved(value: str) -> str:
        path = Path(value)
        return str((workspace_root / path if not path.is_absolute() else path).resolve())

    return {
        "workspace_root": str(workspace_root.resolve()),
        "memory_dir": str(memory_dir.resolve()),
        "git_common_dir": resolved(common),
        "git_dir": resolved(git_dir),
        "head": head,
    }


def _source_manifest(workspace_root: Path, memory_dir: Path) -> tuple[list[dict[str, str]], str] | None:
    sessions = memory_dir / "sessions"
    paths = {doc.path for doc in iter_session_documents(sessions)}
    paths.update(doc.path for doc in iter_link_sidecar_documents(sessions))
    paths.update(doc.path for doc in iter_topic_sidecar_documents(sessions))
    project = memory_dir / "project.yaml"
    if project.is_file():
        paths.add(project)
    manifest: list[dict[str, str]] = []
    for path in sorted(paths, key=lambda item: item.as_posix()):
        try:
            data = path.read_bytes()
            relative = path.resolve().relative_to(workspace_root.resolve()).as_posix()
        except (OSError, ValueError):
            # A byte hash we cannot actually read is not a fingerprint.  Do
            # not turn an unreadable/disappearing file into a fake stable value.
            return None
        manifest.append({"path": relative, "sha256": hashlib.sha256(data).hexdigest()})
    encoded = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    return manifest, hashlib.sha256(encoded).hexdigest()


def _fingerprint(identity: Mapping[str, str], manifest: list[dict[str, str]]) -> str:
    value = {
        "schema": CACHE_SCHEMA_VERSION,
        "serializer": SERIALIZER_VERSION,
        "identity": dict(identity),
        "manifest": manifest,
    }
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _default_source_builder(cwd: str | Path) -> Mapping[tuple[str, str], tuple[MemoryChunk, ...]]:
    # Local import keeps retrieval -> corpus_cache free of an import cycle.
    from .retrieval import augment_chunks_with_link_sidecars, augment_chunks_with_topic_sidecars
    from .semantic_cache import extract_memory_chunks

    built: dict[tuple[str, str], tuple[MemoryChunk, ...]] = {}
    for granularity in _GRANULARITIES:
        raw = tuple(extract_memory_chunks(cwd, granularity=granularity))
        built[(granularity, "raw")] = raw
        built[(granularity, "augmented")] = tuple(
            augment_chunks_with_topic_sidecars(augment_chunks_with_link_sidecars(raw, cwd), cwd)
        )
    return built


def _encode_chunk(chunk: MemoryChunk) -> dict[str, Any]:
    if not _serializer_is_compatible():
        raise RuntimeError("MemoryChunk serializer is incomplete; update fields and serializer version")
    value = {name: getattr(chunk, name) for name in _CHUNK_FIELDS}
    value["session_date"] = chunk.session_date.isoformat()
    value["entry_datetime"] = chunk.entry_datetime.isoformat() if chunk.entry_datetime else None
    value["continuity"] = [
        {"kind": block.kind, "from_ref": block.from_ref, "to_ref": block.to_ref}
        for block in chunk.continuity
    ]
    for name in _TUPLE_FIELDS - {"continuity"}:
        value[name] = [list(item) if isinstance(item, tuple) else item for item in value[name]]
    if chunk.entry_line_range is not None:
        value["entry_line_range"] = list(chunk.entry_line_range)
    return value


def _decode_chunk(value: Any) -> MemoryChunk:
    if not isinstance(value, dict) or set(value) != set(_CHUNK_FIELDS):
        raise ValueError("chunk fields do not match serializer schema")
    decoded = dict(value)
    try:
        decoded["session_date"] = date.fromisoformat(decoded["session_date"])
        encoded_datetime = decoded["entry_datetime"]
        decoded["entry_datetime"] = datetime.fromisoformat(encoded_datetime) if encoded_datetime else None
        decoded["continuity"] = tuple(ContinuityBlock(**item) for item in decoded["continuity"])
        for name in _TUPLE_FIELDS - {"continuity"}:
            if not isinstance(decoded[name], list):
                raise ValueError(f"{name} is not a list")
            decoded[name] = tuple(tuple(item) if isinstance(item, list) else item for item in decoded[name])
        if decoded["entry_line_range"] is not None:
            decoded["entry_line_range"] = tuple(decoded["entry_line_range"])
        if not isinstance(decoded["source_path"], str) or not isinstance(decoded["start_line"], int):
            raise ValueError("chunk has wrong scalar types")
        chunk = MemoryChunk(**decoded)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("invalid serialized chunk") from exc
    # The round trip is also a strict field/type guard for corrupt or stale JSON.
    if _encode_chunk(chunk) != value:
        raise ValueError("chunk does not round trip exactly")
    return chunk


def _integrity_binding(document: Mapping[str, Any]) -> str:
    """Digest the complete persisted envelope, excluding the digest itself.

    This detects accidental corruption, not a hostile writer: the cache is not
    signed and source reconstruction remains the authority on a mismatch.
    """
    protected = {key: value for key, value in document.items() if key != "integrity"}
    encoded = json.dumps(protected, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _payload(snapshot: CorpusSnapshot, identity: Mapping[str, str], manifest: list[dict[str, str]]) -> bytes:
    views = {
        f"{granularity}/{view}": [_encode_chunk(chunk) for chunk in snapshot.chunks(granularity, view)]
        for granularity in _GRANULARITIES for view in _VIEWS
    }
    document: dict[str, Any] = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "serializer_version": SERIALIZER_VERSION,
        "identity": dict(identity),
        "manifest": manifest,
        "fingerprint": snapshot.fingerprint,
        "views": views,
        "view_counts": {key: len(value) for key, value in views.items()},
    }
    document["integrity"] = _integrity_binding(document)
    return json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _load(path: Path, identity: Mapping[str, str], manifest: list[dict[str, str]], fingerprint: str) -> CorpusSnapshot | None:
    try:
        # Field evolution is normal cache incompatibility, not a consumer
        # error: do this before decoding a warm payload.
        if not _serializer_is_compatible():
            return None
        document = json.loads(path.read_text(encoding="utf-8"))
        expected_keys = {
            "schema_version", "serializer_version", "identity", "manifest", "fingerprint", "views",
            "view_counts", "integrity",
        }
        if not isinstance(document, dict) or set(document) != expected_keys:
            return None
        if document.get("schema_version") != CACHE_SCHEMA_VERSION:
            return None
        if document.get("serializer_version") != SERIALIZER_VERSION or document.get("identity") != dict(identity):
            return None
        if document.get("manifest") != manifest or document.get("fingerprint") != fingerprint:
            return None
        views = document.get("views")
        if not isinstance(views, dict) or set(views) != {f"{g}/{v}" for g in _GRANULARITIES for v in _VIEWS}:
            return None
        if document.get("view_counts") != {key: len(value) for key, value in views.items()}:
            return None
        integrity = document.get("integrity")
        if not isinstance(integrity, str) or integrity != _integrity_binding(document):
            return None
        rebuilt = {
            (granularity, view): tuple(_decode_chunk(chunk) for chunk in views[f"{granularity}/{view}"])
            for granularity in _GRANULARITIES for view in _VIEWS
        }
        return CorpusSnapshot("persistent", fingerprint, MappingProxyType(rebuilt))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError):
        return None


class _Lease:
    """A bounded, cross-platform advisory lease using exclusive lock creation.

    Deliberately never steal an old lease: a slow owner is indistinguishable
    from a dead one without introducing a stale-writer race. A leaked lease
    costs only cache reuse; callers reconstruct isolated authoritative data.
    """

    def __init__(self, target: Path) -> None:
        self.path = target.with_suffix(target.suffix + ".lease")
        self.acquired = False
        self.owner_token = secrets.token_hex(16)

    def acquire(self, attempts: int = 4) -> bool:
        for attempt in range(attempts):
            try:
                fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(self.owner_token)
                    handle.flush()
                    try:
                        os.fsync(handle.fileno())
                    except OSError:
                        pass
                self.acquired = True
                return True
            except FileExistsError:
                time.sleep(0.01 * (attempt + 1))
            except OSError:
                return False
        return False

    def release(self) -> None:
        if self.acquired:
            try:
                if self.path.read_text(encoding="utf-8") == self.owner_token:
                    self.path.unlink()
            except OSError:
                pass
            finally:
                self.acquired = False


def _cache_dir(override: str | Path | None) -> Path:
    if override is not None:
        return Path(override)
    configured = os.environ.get("MEMORY_SEED_CORPUS_CACHE_DIR")
    if configured:
        return Path(configured)
    base = os.environ.get("LOCALAPPDATA") if os.name == "nt" else os.environ.get("XDG_CACHE_HOME")
    return Path(base) / "memory-seed" / "corpus-cache" if base else Path.home() / ".cache" / "memory-seed" / "corpus-cache"


def _publish(path: Path, data: bytes, replace: Callable[[str, str], Any]) -> bool:
    temp: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("wb", dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as handle:
            temp = Path(handle.name)
            handle.write(data)
            handle.flush()
            try:
                os.fsync(handle.fileno())
            except OSError:
                pass
        for attempt in range(3):
            try:
                replace(str(temp), str(path))
                return True
            except OSError:
                time.sleep(0.01 * (attempt + 1))
        return False
    except OSError:
        return False
    finally:
        if temp is not None:
            try:
                temp.unlink(missing_ok=True)
            except OSError:
                pass


def get_corpus_snapshot(
    cwd: str | Path = ".", *, cache_dir: str | Path | None = None,
    source_builder: Callable[[str | Path], Mapping[tuple[str, str], tuple[MemoryChunk, ...]]] | None = None,
    replace: Callable[[str, str], Any] = os.replace,
) -> CorpusSnapshot:
    """Return a verified snapshot, rebuilding from authority on every uncertainty.

    ``source_builder`` and ``replace`` are deliberately injectable seams for
    deterministic tests and operational fault handling.
    """
    runtime = resolve_runtime(cwd)
    identity = _git_identity(runtime.workspace_root, runtime.memory_dir)
    if identity is None:  # no-Git is never trusted or published persistently
        views = (source_builder or _default_source_builder)(cwd)
        return CorpusSnapshot("isolated", None, MappingProxyType(dict(views)))
    manifest_result = _source_manifest(runtime.workspace_root, runtime.memory_dir)
    if manifest_result is None:
        views = (source_builder or _default_source_builder)(cwd)
        return CorpusSnapshot("isolated", None, MappingProxyType(dict(views)))
    manifest, _ = manifest_result
    fingerprint = _fingerprint(identity, manifest)
    key = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    try:
        artifact = _cache_dir(cache_dir) / f"{key}.json"
        hit = _load(artifact, identity, manifest, fingerprint)
    except OSError:
        artifact = None
        hit = None
    if hit is not None:
        return hit

    builder = source_builder or _default_source_builder
    snapshot: CorpusSnapshot | None = None
    stable = False
    for _attempt in range(2):
        built = builder(cwd)
        before_identity, before_manifest = identity, manifest
        after_identity = _git_identity(runtime.workspace_root, runtime.memory_dir)
        after_manifest_result = _source_manifest(runtime.workspace_root, runtime.memory_dir)
        if after_manifest_result is None:
            return CorpusSnapshot("isolated", None, MappingProxyType(dict(built)))
        after_manifest, _ = after_manifest_result
        if after_identity == before_identity and after_manifest == before_manifest:
            snapshot = CorpusSnapshot("reconstructed", fingerprint, MappingProxyType(dict(built)))
            stable = True
            break
        identity, manifest = after_identity or {}, after_manifest
        if after_identity is None:
            return CorpusSnapshot("isolated", None, MappingProxyType(dict(built)))
        fingerprint = _fingerprint(after_identity, after_manifest)
    if snapshot is None:
        # A moving source must never be published; this is still an authoritative
        # source reconstruction from the second attempt.
        return CorpusSnapshot("isolated", None, MappingProxyType(dict(built)))
    if not stable or artifact is None:
        return snapshot

    try:
        artifact.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return CorpusSnapshot("isolated", snapshot.fingerprint, snapshot._views)

    lease = _Lease(artifact)
    if not lease.acquire():
        return CorpusSnapshot("isolated", snapshot.fingerprint, snapshot._views)
    try:
        # A peer may have won while we waited.  Validate its full payload first.
        winner = _load(artifact, identity, manifest, fingerprint)
        if winner is not None:
            return winner
        # Waiting on another writer may have allowed a source edit after our
        # post-build check.  Do not publish that now-stale projection.
        current_manifest_result = _source_manifest(runtime.workspace_root, runtime.memory_dir)
        if _git_identity(runtime.workspace_root, runtime.memory_dir) != identity or current_manifest_result is None or current_manifest_result[0] != manifest:
            late_views = builder(cwd)
            return CorpusSnapshot("isolated", None, MappingProxyType(dict(late_views)))
        try:
            payload = _payload(snapshot, identity, manifest)
        except (RuntimeError, TypeError, ValueError, OverflowError, UnicodeError):
            return CorpusSnapshot("isolated", snapshot.fingerprint, snapshot._views)
        if not _publish(artifact, payload, replace):
            return CorpusSnapshot("isolated", snapshot.fingerprint, snapshot._views)
        return snapshot
    finally:
        lease.release()

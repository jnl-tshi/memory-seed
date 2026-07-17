"""Deterministic read-only evidence packs for Memory Trace.

Phase 1 of the AI timeline summarisation plan is a pure builder over the
canonical Memory Seed and Memory Trace readers. This module does not parse
Markdown itself, does not rank independently, and does not write caches or any
other project state.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import date
from pathlib import Path
from typing import Any, Sequence

from memory_seed.core import resolve_runtime
from memory_seed.retrieval import (
    augment_chunks_with_link_sidecars,
    chunk_to_dict,
    entry_diagram_sidecars,
)
from memory_seed.semantic_cache import MemoryChunk, build_related_entry_graph, extract_memory_chunks

from .service import (
    _chunk_datetime,
    _filter_chunks,
    _git_head,
    _graph_edges,
    _neighborhood,
    _parse_date,
    _tracked_document_paths,
    _working_tree_signature,
)

TIMELINE_EVIDENCE_PACK_SCHEMA_VERSION = "timeline_evidence_pack.v1"
DEFAULT_EDGE_TYPES = ("related", "supersedes", "evolves", "branch")

EvidencePack = dict[str, Any]


def build_timeline_evidence_pack(
    cwd: str | Path = ".",
    *,
    date_from: str | date | None = None,
    date_to: str | date | None = None,
    entry_ids: Sequence[str] | None = None,
    topic: str | None = None,
    user: str | None = None,
    agent: str | None = None,
    graph_entry_id: str | None = None,
    graph_depth: int = 1,
    edge_types: Sequence[str] = DEFAULT_EDGE_TYPES,
    include_sections: bool = True,
    max_entries: int | None = None,
    generated_at: str | None = None,
) -> EvidencePack:
    """Build a deterministic, JSON-ready timeline evidence pack.

    The builder is intentionally read-only: it operates on the same chunk and
    graph readers used by retrieval and Trace, but never touches the SQLite
    projection or any write path.
    """
    runtime = resolve_runtime(Path(cwd).resolve())
    root = runtime.workspace_root
    normalized_entry_ids = _dedupe_strings(entry_ids)
    normalized_edge_types = tuple(sorted(set(edge_types or DEFAULT_EDGE_TYPES)))
    normalized_date_from = _normalize_date(date_from)
    normalized_date_to = _normalize_date(date_to)
    normalized_graph_depth = max(int(graph_depth), 1)

    all_entries = augment_chunks_with_link_sidecars(extract_memory_chunks(root, granularity="entry"), root)
    all_sections = augment_chunks_with_link_sidecars(extract_memory_chunks(root, granularity="section"), root)
    filtered_entries = _filter_chunks(
        all_entries,
        agent=agent,
        user=user,
        date_from=normalized_date_from,
        date_to=normalized_date_to,
        topic=topic,
        cwd=root,
    )
    filtered_entry_ids = {chunk.entry_id for chunk in filtered_entries if chunk.entry_id}
    corpus_entry_ids = {chunk.entry_id for chunk in all_entries if chunk.entry_id}

    selected_entries = list(filtered_entries)
    if normalized_entry_ids:
        requested = set(normalized_entry_ids)
        selected_entries = [chunk for chunk in selected_entries if chunk.entry_id in requested]

    graph_edges = _graph_edges(filtered_entries, set(normalized_edge_types))
    if graph_entry_id:
        visible_ids = set(_neighborhood(graph_entry_id, graph_edges, depth=normalized_graph_depth))
        selected_entries = [chunk for chunk in selected_entries if chunk.entry_id in visible_ids]

    selected_entries.sort(key=lambda chunk: (_chunk_datetime(chunk), chunk.start_line, chunk.chunk_id))
    total_selected_before_limit = len(selected_entries)
    if max_entries is not None:
        selected_entries = selected_entries[: max(int(max_entries), 0)]

    selected_ids = [chunk.entry_id for chunk in selected_entries if chunk.entry_id]
    selected_id_set = set(selected_ids)
    selected_sections = []
    if include_sections:
        selected_sections = [
            chunk
            for chunk in all_sections
            if chunk.granularity != "entry" and chunk.entry_id in selected_id_set
        ]
        selected_sections.sort(key=lambda chunk: (_chunk_datetime(chunk), chunk.start_line, chunk.chunk_id))

    graph = build_related_entry_graph(chunks=filtered_entries)
    diagram_map = entry_diagram_sidecars(root)
    commit_ids_by_entry = _commit_reference_map(root, filtered_entries)
    section_ids_by_entry = _section_ids_by_entry(selected_sections)
    edge_sort_keys = {
        chunk.entry_id: (_chunk_datetime(chunk), chunk.start_line, chunk.chunk_id)
        for chunk in filtered_entries
        if chunk.entry_id
    }
    selected_edges = [
        edge
        for edge in graph_edges
        if edge["source"] in selected_id_set and edge["target"] in selected_id_set
    ]
    selected_edges.sort(
        key=lambda edge: (
            edge_sort_keys.get(edge["source"], (_max_datetime(), 0, edge["source"])),
            edge_sort_keys.get(edge["target"], (_max_datetime(), 0, edge["target"])),
            edge["type"],
            edge["source"],
            edge["target"],
        )
    )

    entries_payload = [
        _entry_payload(
            chunk,
            graph=graph,
            diagrams=diagram_map.get(chunk.entry_id or ""),
            commit_ids=commit_ids_by_entry.get(chunk.entry_id or "", ()),
            section_ids=section_ids_by_entry.get(chunk.entry_id or "", ()),
        )
        for chunk in selected_entries
    ]
    chunks_payload = [_chunk_payload(chunk) for chunk in selected_sections]
    missing_evidence = _missing_evidence(
        requested_entry_ids=normalized_entry_ids,
        graph_entry_id=graph_entry_id,
        corpus_entry_ids=corpus_entry_ids,
        filtered_entry_ids=filtered_entry_ids,
        selected_entry_ids=selected_id_set,
        selected_entries=selected_entries,
        filtered_entries=filtered_entries,
    )
    contradictions = _contradictions(selected_edges)
    tracked_documents = _tracked_documents_payload(runtime)
    source_revision = _source_revision(root, runtime, tracked_documents)

    selection = {
        "date_from": normalized_date_from,
        "date_to": normalized_date_to,
        "entry_ids": normalized_entry_ids,
        "topic": topic,
        "user": user,
        "agent": agent,
        "graph_entry_id": graph_entry_id,
        "graph_depth": normalized_graph_depth if graph_entry_id else None,
        "edge_types": list(normalized_edge_types),
        "include_sections": include_sections,
        "max_entries": max_entries,
        "matched_entry_count": total_selected_before_limit,
        "returned_entry_count": len(selected_entries),
    }

    pack: EvidencePack = {
        "schema_version": TIMELINE_EVIDENCE_PACK_SCHEMA_VERSION,
        "pack_type": "timeline_evidence_pack",
        "workspace_label": runtime.workspace_root.name,
        "selection": selection,
        "provenance": {
            "builder": {
                "module": "memory_trace.evidence",
                "function": "build_timeline_evidence_pack",
                "read_only": True,
            },
            "corpus": {
                "runtime_legacy": runtime.legacy,
                "tracked_documents": tracked_documents,
            },
            "source_revision": source_revision,
            "freshness": {
                "corpus_state": source_revision["working_tree_state"],
                "provider_state": "not_applicable",
            },
        },
        "entries": entries_payload,
        "chunks": chunks_payload,
        "graph": {
            "edge_types": list(normalized_edge_types),
            "entry_order": selected_ids,
            "edges": selected_edges,
        },
        "contradictions": contradictions,
        "missing_evidence": missing_evidence,
        "constraints": {
            "use_only_evidence_pack": True,
            "cite_entry_ids": True,
            "cite_chunk_ids": True,
            "do_not_infer_unseen_repository_state": True,
        },
    }
    if generated_at is not None:
        pack["generated_at"] = generated_at
    pack["selection"]["selection_fingerprint"] = _json_fingerprint(selection)
    pack["pack_fingerprint"] = _json_fingerprint(pack)
    return pack


def _entry_payload(
    chunk: MemoryChunk,
    *,
    graph: dict[str, Any],
    diagrams: dict[str, Any] | None,
    commit_ids: Sequence[str],
    section_ids: Sequence[str],
) -> dict[str, Any]:
    payload = chunk_to_dict(chunk)
    node = graph.get(chunk.entry_id or "")
    entry_payload = {
        "entry_id": payload["entry_id"],
        "chunk_id": payload["chunk_id"],
        "title": payload["title"],
        "entry_title": payload["entry_title"],
        "path": payload["path"],
        "source_file": payload["source_file"],
        "session_date": payload["session_date"],
        "entry_datetime": payload["entry_datetime"],
        "agent_type": payload["agent_type"],
        "agent_name": payload["agent_name"],
        "user": payload["user"],
        "branch": payload["branch"],
        "topics": payload["topics"],
        "tags": payload["tags"],
        "contexts": payload["contexts"],
        "heading_path": payload["heading_path"],
        "line_range": payload["line_range"],
        "related_entries": payload["related_entries"],
        "supersedes": payload["supersedes"],
        "evolves": payload["evolves"],
        "superseded_by": list(node.superseded_by) if node else [],
        "evolved_by": list(node.evolved_by) if node else [],
        "inbound_relation_count": len(node.inbound) if node else 0,
        "importance_score": round(node.importance_score, 6) if node else 0.0,
        "commit_reference_count": len(commit_ids),
        "commit_reference_ids": commit_ids,
        "diagrams": [diagrams] if diagrams else [],
        "chunk_ids": list(section_ids),
        "text": payload["text"],
    }
    entry_payload["fingerprint"] = _json_fingerprint(_fingerprintable_chunk_payload(payload))
    return entry_payload


def _commit_reference_map(root: Path, entries: Sequence[MemoryChunk]) -> dict[str, tuple[str, ...]]:
    commit_ids_by_entry: dict[str, set[str]] = {}
    for chunk in entries:
        if not chunk.entry_id:
            continue
        commit_ids_by_entry[chunk.entry_id] = {
            sha for sha in chunk.commits if len(sha) == 40 and all(ch in "0123456789abcdef" for ch in sha.lower())
        }

    if (root / ".git").exists():
        for entry_id, trailer_ids in _trailer_commit_map(root).items():
            if entry_id in commit_ids_by_entry:
                commit_ids_by_entry[entry_id].update(trailer_ids)

    return {
        entry_id: tuple(sorted(commit_ids))
        for entry_id, commit_ids in commit_ids_by_entry.items()
    }


def _trailer_commit_map(root: Path) -> dict[str, set[str]]:
    try:
        proc = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "log",
                "--all",
                "--grep=Memory-Entry:",
                "--format=%x01%H%x1f%B%x1e",
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeDecodeError):
        return {}
    if proc.returncode != 0:
        return {}

    commit_ids_by_entry: dict[str, set[str]] = {}
    for record in proc.stdout.split("\x1e"):
        record = record.lstrip("\n")
        if not record.startswith("\x01"):
            continue
        body_parts = record[1:].split("\x1f", 1)
        if len(body_parts) != 2:
            continue
        sha, body = body_parts
        sha = sha.strip()
        if not sha:
            continue
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped.startswith("Memory-Entry:"):
                continue
            entry_id = stripped[len("Memory-Entry:") :].strip()
            if entry_id:
                commit_ids_by_entry.setdefault(entry_id, set()).add(sha)
    return commit_ids_by_entry


def _chunk_payload(chunk: MemoryChunk) -> dict[str, Any]:
    payload = chunk_to_dict(chunk)
    chunk_payload = {
        "chunk_id": payload["chunk_id"],
        "entry_id": payload["entry_id"],
        "title": payload["title"],
        "path": payload["path"],
        "session_date": payload["session_date"],
        "entry_datetime": payload["entry_datetime"],
        "granularity": payload["granularity"],
        "heading_path": payload["heading_path"],
        "line_range": payload["line_range"],
        "topics": payload["topics"],
        "tags": payload["tags"],
        "contexts": payload["contexts"],
        "lexical_terms": payload["lexical_terms"],
        "text": payload["text"],
    }
    chunk_payload["fingerprint"] = _json_fingerprint(_fingerprintable_chunk_payload(payload))
    return chunk_payload


def _fingerprintable_chunk_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "chunk_id": payload["chunk_id"],
        "entry_id": payload["entry_id"],
        "path": payload["path"],
        "source_file": payload.get("source_file"),
        "session_date": payload["session_date"],
        "entry_datetime": payload["entry_datetime"],
        "granularity": payload["granularity"],
        "heading_path": payload["heading_path"],
        "line_range": payload["line_range"],
        "title": payload["title"],
        "text": payload["text"],
        "related_entries": payload["related_entries"],
        "supersedes": payload["supersedes"],
        "evolves": payload["evolves"],
        "continuity": payload["continuity"],
        "topics": payload["topics"],
        "tags": payload["tags"],
        "contexts": payload["contexts"],
        "lexical_terms": payload["lexical_terms"],
        "branch": payload["branch"],
        "entry_title": payload["entry_title"],
        "sections": payload["sections"],
    }


def _tracked_documents_payload(runtime: Any) -> list[dict[str, Any]]:
    documents = []
    for path in sorted(_tracked_document_paths(runtime), key=lambda item: item.as_posix()):
        rel = path.relative_to(runtime.workspace_root).as_posix()
        documents.append(
            {
                "path": rel,
                "kind": _document_kind(rel),
                "fingerprint": _file_fingerprint(path),
            }
        )
    return documents


def _source_revision(root: Path, runtime: Any, tracked_documents: Sequence[dict[str, Any]]) -> dict[str, Any]:
    sessions = runtime.memory_dir / "sessions"
    try:
        pathspec = sessions.relative_to(runtime.workspace_root).as_posix()
    except ValueError:
        pathspec = str(sessions)
    git_head = _git_head(root)
    dirty_signature = _working_tree_signature(root, pathspec) if git_head else None
    if git_head is None:
        working_tree_state = "no_git"
    elif dirty_signature == "[]":
        working_tree_state = "clean"
    else:
        working_tree_state = "dirty"
    return {
        "git_head": git_head,
        "working_tree_state": working_tree_state,
        "working_tree_signature": dirty_signature,
        "tracked_document_count": len(tracked_documents),
        "tracked_document_fingerprint": _json_fingerprint(list(tracked_documents)),
    }


def _missing_evidence(
    *,
    requested_entry_ids: Sequence[str],
    graph_entry_id: str | None,
    corpus_entry_ids: set[str | None],
    filtered_entry_ids: set[str | None],
    selected_entry_ids: set[str],
    selected_entries: Sequence[MemoryChunk],
    filtered_entries: Sequence[MemoryChunk],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    corpus_ids = {item for item in corpus_entry_ids if item}
    filtered_ids = {item for item in filtered_entry_ids if item}
    for entry_id in requested_entry_ids:
        if entry_id not in corpus_ids:
            issues.append({"kind": "requested_entry_missing", "entry_id": entry_id})
        elif entry_id not in filtered_ids:
            issues.append({"kind": "requested_entry_excluded_by_filters", "entry_id": entry_id})
    if graph_entry_id:
        if graph_entry_id not in corpus_ids:
            issues.append({"kind": "graph_entry_missing", "entry_id": graph_entry_id})
        elif graph_entry_id not in filtered_ids:
            issues.append({"kind": "graph_entry_excluded_by_filters", "entry_id": graph_entry_id})
    if not selected_entries:
        issues.append({"kind": "no_entries_match_selection"})

    filtered_index = {chunk.entry_id: chunk for chunk in filtered_entries if chunk.entry_id}
    for chunk in selected_entries:
        refs: dict[str, set[str]] = {}
        for relation, values in (
            ("related", chunk.related_entries),
            ("supersedes", chunk.supersedes),
            ("evolves", chunk.evolves),
        ):
            for ref in values:
                refs.setdefault(ref, set()).add(relation)
        for ref, relation_types in sorted(refs.items()):
            if ref in selected_entry_ids:
                continue
            if ref not in corpus_ids:
                reason = "missing_from_corpus"
            elif ref not in filtered_ids:
                reason = "excluded_by_filters"
            else:
                reason = "outside_selection"
            issues.append(
                {
                    "kind": "referenced_entry_not_in_pack",
                    "entry_id": chunk.entry_id,
                    "referenced_entry_id": ref,
                    "relation_types": sorted(relation_types),
                    "reason": reason,
                    "referenced_entry_title": filtered_index.get(ref).title if ref in filtered_index else None,
                }
            )
    issues.sort(
        key=lambda item: (
            item["kind"],
            item.get("entry_id") or "",
            item.get("referenced_entry_id") or "",
        )
    )
    return issues


def _contradictions(edges: Sequence[dict[str, str]]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    directed: dict[tuple[str, str], set[str]] = {}
    typed_pairs = {(edge["source"], edge["target"], edge["type"]) for edge in edges}
    for edge in edges:
        if edge["type"] not in {"supersedes", "evolves"}:
            continue
        directed.setdefault((edge["source"], edge["target"]), set()).add(edge["type"])
    for (source, target), types in sorted(directed.items()):
        if len(types) > 1:
            issues.append(
                {
                    "kind": "mixed_lifecycle_edge",
                    "source": source,
                    "target": target,
                    "edge_types": sorted(types),
                }
            )
    for source, target, edge_type in sorted(typed_pairs):
        if edge_type not in {"supersedes", "evolves"}:
            continue
        if (target, source, edge_type) in typed_pairs and source < target:
            issues.append(
                {
                    "kind": "reciprocal_lifecycle_edge",
                    "edge_type": edge_type,
                    "entries": [source, target],
                }
            )
    return issues


def _section_ids_by_entry(chunks: Sequence[MemoryChunk]) -> dict[str, tuple[str, ...]]:
    by_entry: dict[str, list[str]] = {}
    for chunk in chunks:
        if chunk.entry_id:
            by_entry.setdefault(chunk.entry_id, []).append(chunk.chunk_id)
    return {entry_id: tuple(chunk_ids) for entry_id, chunk_ids in by_entry.items()}


def _document_kind(path: str) -> str:
    if "/links/" in path:
        return "link_sidecar"
    if "/diagrams/" in path:
        return "diagram_sidecar"
    return "session"


def _file_fingerprint(path: Path) -> str:
    """Fingerprint a tracked document by its canonical text form.

    Hashing raw bytes made the fingerprint platform-dependent: the same
    logical document is CRLF in a Windows working copy and LF on a Linux
    checkout, so packs built from identical corpora disagreed (caught by the
    snapshot test the first time CI ever ran it). Text documents hash their
    `normalize_text` canonical form (NFC + LF - the same canonicalization
    every Memory Seed write already applies); unreadable/binary content falls
    back to raw bytes, where no canonical text form exists.
    """
    from memory_seed.text_files import normalize_text

    digest = hashlib.sha256()
    try:
        digest.update(normalize_text(path.read_text(encoding="utf-8")).encode("utf-8"))
    except (UnicodeDecodeError, OSError):
        digest.update(path.read_bytes())
    return f"sha256:{digest.hexdigest()}"


def _json_fingerprint(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_stable_json(value).encode('utf-8')).hexdigest()}"


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _normalize_date(value: str | date | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    return _parse_date(value).isoformat()


def _dedupe_strings(values: Sequence[str] | None) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values or ():
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _max_datetime() -> Any:
    from datetime import datetime

    return datetime.max

"""Public retrieval service - the MCP-independent search/fetch surface.

This module is the canonical search-orchestration and result-dict contract for
every consumer: the MCP server (`memory_seed/mcp_server.py`) wraps it, the
deprecated in-package Memory Lense shim routes users to Memory Trace, and the
standalone `memory-trace` companion UI imports it as its frozen public API. Do
not fork result-dict shapes per consumer - same
answers as MCP, richer navigation for humans.

The shared substrate (parser + ranker) lives in `memory_seed/semantic_cache.py`;
this module owns what used to be MCP-coupled: semantic-provider resolution,
search orchestration, and the canonical result dictionaries. See
docs/2_Todo/memory-trace-distribution-plan.md (Phase 1) and
docs/3_Spec/graph-edge-contract.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .semantic_cache import (
    EmbeddingProvider,
    MemoryChunk,
    Model2VecEmbeddingProvider,
    RankedMemoryChunk,
    build_related_entry_graph,
    extract_memory_chunks,
    rank_session_memory,
)


def resolve_semantic_provider(
    query: str,
    override: Any = None,
    *,
    enabled: bool = True,
) -> tuple[EmbeddingProvider | None, str | None, str | None]:
    """Resolve the embedding provider for a query: (provider, name, fallback_reason).

    Disabled -> (None, None, None). A provider that fails to embed the query is
    reported by name with the failure reason, and search falls back to lexical
    ranking - the caller surfaces `semantic_fallback_reason` instead of erroring.
    """
    if not enabled:
        return None, None, None
    provider = override or Model2VecEmbeddingProvider()
    provider_name = getattr(provider, "name", f"model2vec:{Model2VecEmbeddingProvider.default_model_name}")
    try:
        provider.embed([query])
    except Exception as exc:
        return None, provider_name, str(exc)
    return provider, provider_name, None


def search_memory(
    query: str,
    cwd: str | Path = ".",
    *,
    top_k: int = 8,
    today: date | None = None,
    lambda_days: float = 0.01,
    recency_enabled: bool = True,
    recency_floor: float = 0.15,
    semantic_enabled: bool = True,
    embedding_provider: Any = None,
    granularity: str = "entry",
    user: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    exclude_superseded: bool = False,
    topics: list[str] | None = None,
) -> dict[str, Any]:
    """Search session memory and return the canonical result payload.

    This is the full orchestration the MCP `memory_search` tool exposes:
    semantic-provider resolution (with lexical fallback), shared ranking via
    `rank_session_memory`, and `format_search_results` formatting. Non-MCP
    consumers call this directly and get identical answers.
    """
    provider, provider_name, fallback_reason = resolve_semantic_provider(
        query,
        embedding_provider,
        enabled=semantic_enabled,
    )
    chunks = extract_memory_chunks(cwd, granularity=granularity)
    topic_filter: set[str] | None = None
    if topics:
        # Alias-aware expansion (canonical + aliases both match); fail-open on
        # unknown names so vocabulary drift narrows results instead of erroring.
        from .topics import expand_topic_filter

        topic_filter = expand_topic_filter(cwd, topics)
    ranked = rank_session_memory(
        query,
        cwd,
        top_k=top_k,
        today=today or date.today(),
        lambda_days=lambda_days,
        recency_enabled=recency_enabled,
        recency_floor=recency_floor,
        embedding_provider=provider,
        granularity=granularity,
        user=user,
        date_from=date_from,
        date_to=date_to,
        exclude_superseded=exclude_superseded,
        chunks=chunks,
        topics=topic_filter,
    )
    payload = format_search_results(
        query,
        ranked,
        top_k=top_k,
        semantic_enabled=provider is not None,
        semantic_provider=provider_name,
        semantic_fallback_reason=fallback_reason,
    )
    # Freshness at the moment of consumption (evolution-edges-plan.md D7):
    # each result carries the computed lifecycle status so a consumer sees
    # "retired" / "newer development builds on this" without a per-result
    # get_chunk round trip. Additive, read-only, and reuses the corpus
    # extracted above - ranking and result order are untouched.
    graph = build_related_entry_graph(cwd, chunks=chunks)
    for result in payload["results"]:
        node = graph.get(result.get("entry_id") or "")
        result["superseded_by"] = list(node.superseded_by) if node else []
        result["evolved_by"] = list(node.evolved_by) if node else []
    return payload


def get_chunk(chunk_id: str, cwd: str | Path = ".", *, include_diagrams: bool = False) -> dict[str, Any]:
    """Fetch one chunk by ``chunk_id`` and return its canonical payload dict,
    enriched with the read-only graph metrics from docs/3_Spec/graph-edge-contract.md
    (`superseded_by`, `inbound_relation_count`, `importance_score`,
    `commit_reference_count`). Raises ``ValueError`` for an unknown id.

    ``include_diagrams=True`` additionally attaches ``diagrams``: authored
    decision-diagram sidecar metadata for the chunk's entry (see
    `entry_diagram_sidecars`). Off by default so the MCP tool contract is
    unchanged; Explorer/Trail consumers opt in.
    """
    entry_chunks = extract_memory_chunks(cwd, granularity="entry")
    found = next((chunk for chunk in entry_chunks if chunk.chunk_id == chunk_id), None)
    if found is None:
        found = next(
            (chunk for chunk in extract_memory_chunks(cwd, granularity="section") if chunk.chunk_id == chunk_id),
            None,
        )
    if found is None:
        raise ValueError(f"chunk_id not found: {chunk_id}")
    payload = chunk_to_dict(found)
    superseded_by: list[str] = []
    evolved_by: list[str] = []
    inbound_relation_count = 0
    importance_score = 0.0
    if found.entry_id:
        node = build_related_entry_graph(chunks=entry_chunks).get(found.entry_id)
        if node is not None:
            superseded_by = list(node.superseded_by)
            # Read-time-only inverse of evolves: newer entries that extend this
            # decision while it stays valid. Never stored, never dampens.
            evolved_by = list(node.evolved_by)
            # How many other entries reference this one via related_entries
            # (inbound backlinks only) - the raw signal importance_score is
            # built on. Distinct from Lense's `connectivity`, which counts
            # combined inbound+outbound edges for node sizing.
            inbound_relation_count = len(node.inbound)
            # inbound_relation_count dampened when this entry is superseded
            # (read-only; not blended into default search ranking).
            importance_score = node.importance_score
    commit_reference_count = 0
    if found.entry_id:
        from .core import commit_reference_ids, resolve_runtime

        commit_reference_count = len(
            commit_reference_ids(resolve_runtime(cwd).workspace_root, found.entry_id, found.commits)
        )
    payload["superseded_by"] = superseded_by
    payload["evolved_by"] = evolved_by
    payload["inbound_relation_count"] = inbound_relation_count
    payload["importance_score"] = importance_score
    payload["commit_reference_count"] = commit_reference_count
    if include_diagrams:
        sidecar = entry_diagram_sidecars(cwd).get(found.entry_id or "")
        payload["diagrams"] = [sidecar] if sidecar else []
    return payload


_DIAGRAM_ENTRY_RE = re.compile(
    r"^##\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s+-\s*([^\n]*)\n\s*```ya?ml\s*\n(.*?)^```\s*$",
    re.MULTILINE | re.DOTALL,
)

# A balanced fenced ```mermaid ... ``` block. Used to surface the raw diagram
# source (not just a count) so a consumer can render it client-side. Still no
# Mermaid *semantics* are parsed here - this only extracts the fenced text.
_MERMAID_BLOCK_RE = re.compile(r"^```mermaid\s*\n(.*?)^```\s*$", re.MULTILINE | re.DOTALL)


def entry_diagram_sidecars(cwd: str | Path = ".") -> dict[str, dict[str, Any]]:
    """Authored decision-diagram sidecar metadata, keyed by ``entry_id``.

    New sidecars live at
    ``.memory-seed/sessions/diagrams/YYYY-MM/YYYY-MM-DD.md`` - one dated file
    per day, mirroring the month-grouped session-log convention so a human
    browsing the filesystem without the Explorer can find a day's diagrams next
    to that day's session log. Legacy ``diagrams/YYYY-MM-DD.md`` sidecars remain
    readable. Each diagram is a heading block
    shaped like a session entry (``## <timestamp> - <title>`` + a fenced
    ```` ```yaml ```` block naming ``entry_id`` + fenced ```` ```mermaid ````
    block(s)), so multiple diagrams append to the same date file across a day.
    These are the Class-2 reasoning diagrams from
    docs/2_Todo/session-decision-diagrams-plan.md, authored at session-entry
    time because a no-LLM consumer cannot derive them from prose. This reader
    is metadata-only and deterministic: it never parses Mermaid semantics, and
    unreadable or malformed blocks are skipped (``links check`` owns reporting
    them). Sidecars are optional per entry.
    """
    from .core import iter_diagram_sidecar_documents, resolve_runtime

    runtime = resolve_runtime(cwd)
    diagrams_dir = runtime.memory_dir / "sessions" / "diagrams"
    sidecars: dict[str, dict[str, Any]] = {}
    if not diagrams_dir.is_dir():
        return sidecars
    for diagram_doc in iter_diagram_sidecar_documents(runtime.memory_dir / "sessions"):
        if diagram_doc.malformed_reason:
            continue
        path = diagram_doc.path
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            rel = path.relative_to(runtime.workspace_root).as_posix()
        except ValueError:
            rel = path.as_posix()
        blocks = list(_DIAGRAM_ENTRY_RE.finditer(text))
        for index, block in enumerate(blocks):
            heading_ts, title, yaml_block = block.groups()
            entry_id = None
            for line in yaml_block.splitlines():
                line = line.strip()
                if line.startswith("entry_id:"):
                    entry_id = line.split(":", 1)[1].strip().strip("'\"")
                    break
            if not entry_id:
                continue
            section_end = blocks[index + 1].start() if index + 1 < len(blocks) else len(text)
            section_text = text[block.end():section_end]
            mermaid_blocks = [match.group(1).rstrip("\n") for match in _MERMAID_BLOCK_RE.finditer(section_text)]
            mermaid_block_count = sum(
                1 for line in section_text.splitlines() if line.strip().startswith("```mermaid")
            )
            sidecars[entry_id] = {
                "entry_id": entry_id,
                "path": rel,
                "title": title.strip() or None,
                "heading_datetime": heading_ts,
                "mermaid_block_count": mermaid_block_count,
                # Raw fenced Mermaid source(s), for client-side rendering. Balanced
                # blocks only; malformed fences are left to `links check`.
                "mermaid_blocks": mermaid_blocks,
            }
    return sidecars


def format_search_results(
    query: str,
    ranked: list[RankedMemoryChunk],
    *,
    top_k: int = 8,
    semantic_enabled: bool | None = None,
    semantic_provider: str | None = None,
    semantic_fallback_reason: str | None = None,
) -> dict[str, Any]:
    results = [ranked_to_dict(result) for result in ranked[:top_k]]
    effective_semantic_enabled = (
        any(result["semantic_score"] is not None for result in results)
        if semantic_enabled is None
        else semantic_enabled
    )
    return {
        "query": query,
        "semantic_enabled": effective_semantic_enabled,
        "semantic_provider": semantic_provider if effective_semantic_enabled else semantic_provider,
        "semantic_fallback_reason": semantic_fallback_reason,
        "results": results,
        "human_report": _human_report(query, results),
    }


def ranked_to_dict(result: RankedMemoryChunk) -> dict[str, Any]:
    chunk = result.chunk
    return {
        "chunk_id": chunk.chunk_id,
        "score": round(result.final_score, 6),
        "match_score": round(result.match_score, 6),
        "lexical_score": round(result.lexical_score, 6),
        "semantic_score": None
        if result.semantic_score is None
        else round(result.semantic_score, 6),
        "recency_multiplier": round(result.recency_multiplier, 6),
        "age_days": result.age_days,
        "date": chunk.session_date.isoformat(),
        "session_date": chunk.session_date.isoformat(),
        "entry_datetime": None
        if chunk.entry_datetime is None
        else chunk.entry_datetime.isoformat(),
        "source": chunk.source_path,
        "path": chunk.source_path,
        "user": chunk.user,
        "file_hash_id": chunk.file_hash_id,
        "related_entries": list(chunk.related_entries),
        "supersedes": list(chunk.supersedes),
        "evolves": list(chunk.evolves),
        "continuity": [
            {"kind": block.kind, "from": block.from_ref, "to": block.to_ref}
            for block in chunk.continuity
        ],
        "topics": list(chunk.topics),
        "line_range": [chunk.start_line, chunk.end_line],
        "heading_path": list(chunk.heading_path),
        "matched_terms": list(result.matched_terms),
        "matched_fields": list(result.matched_fields),
        "excerpt": _excerpt(chunk.text),
        "entry_id": chunk.entry_id,
        "user_initials": chunk.user_initials,
        "agent_type": chunk.agent_type,
        "agent_name": chunk.agent_name,
        "project_path": chunk.project_path,
        "subproject_path": chunk.subproject_path,
        "branch": chunk.branch,
        "entry_title": chunk.entry_title,
        "entry_line_range": None if chunk.entry_line_range is None else list(chunk.entry_line_range),
        "sections": list(chunk.sections),
        "granularity": chunk.granularity,
    }


def chunk_to_dict(chunk: MemoryChunk) -> dict[str, Any]:
    return {
        "chunk_id": chunk.chunk_id,
        "source": chunk.source_path,
        "path": chunk.source_path,
        "source_file": chunk.source_file,
        "date": chunk.session_date.isoformat(),
        "session_date": chunk.session_date.isoformat(),
        "user": chunk.user,
        "file_hash_id": chunk.file_hash_id,
        "related_entries": list(chunk.related_entries),
        "supersedes": list(chunk.supersedes),
        "evolves": list(chunk.evolves),
        "continuity": [
            {"kind": block.kind, "from": block.from_ref, "to": block.to_ref}
            for block in chunk.continuity
        ],
        "topics": list(chunk.topics),
        "entry_datetime": None
        if chunk.entry_datetime is None
        else chunk.entry_datetime.isoformat(),
        "line_range": [chunk.start_line, chunk.end_line],
        "heading_path": list(chunk.heading_path),
        "heading_level": chunk.heading_level,
        "title": chunk.title,
        "text": chunk.text,
        "tags": list(chunk.tags),
        "contexts": list(chunk.contexts),
        "lexical_terms": list(chunk.lexical_terms),
        "entry_id": chunk.entry_id,
        "user_initials": chunk.user_initials,
        "agent_type": chunk.agent_type,
        "agent_name": chunk.agent_name,
        "project_path": chunk.project_path,
        "subproject_path": chunk.subproject_path,
        "branch": chunk.branch,
        "entry_title": chunk.entry_title,
        "entry_line_range": None if chunk.entry_line_range is None else list(chunk.entry_line_range),
        "sections": list(chunk.sections),
        "granularity": chunk.granularity,
    }


@dataclass(frozen=True)
class EntryRollup:
    """One visible entry-level result rolled up from ranked matches.

    The UI-facing object model (memory-explorer-entry-level-ui-results-plan.md):
    session entries are the selectable result; section-chunk matches influence
    scoring and highlighting but never appear as separate selectable records.

    - ``representative``: the entry-granularity member when one matched, else
      the best-scoring section member (its fields still carry the parent
      entry's identity via ``entry_id``/``entry_title``/``entry_line_range``).
    - ``best``: the strongest-scoring member; its score/matched-terms drive the
      rolled-up record.
    - ``sections``: section-granularity members that actually matched the
      query, preserved as highlight metadata for the reader view.
    - ``score_source``: ``"entry"`` when the entry chunk itself is the best
      match, ``"section-rollup"`` when a section drove the score.
    """

    entry_key: str
    representative: RankedMemoryChunk
    best: RankedMemoryChunk
    sections: tuple[RankedMemoryChunk, ...]
    score_source: str


def rollup_entry_matches(ranked: list[RankedMemoryChunk]) -> list[EntryRollup]:
    """Collapse ranked results (any granularity mix) into one rollup per session
    entry, preserving the ranker's order (an entry ranks where its strongest
    member ranked). The canonical grouping every Explorer/Trail surface uses -
    do not fork per consumer. MCP granularity behavior is unaffected: this is a
    post-ranking view, not a ranking change.
    """
    groups: dict[str, list[RankedMemoryChunk]] = {}
    order: list[str] = []
    for result in ranked:
        # Section chunk IDs are `<entry_id>#<section-slug>`; entries without an
        # entry_id fall back to the chunk_id root so nothing is dropped.
        key = result.chunk.entry_id or result.chunk.chunk_id.split("#", 1)[0]
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append(result)
    rollups: list[EntryRollup] = []
    for key in order:
        members = groups[key]
        best = members[0]  # ranked order is preserved within each group
        entry_member = next((m for m in members if m.chunk.granularity == "entry"), None)
        sections = tuple(
            m for m in members if m.chunk.granularity != "entry" and m.matched_fields
        )
        rollups.append(
            EntryRollup(
                entry_key=key,
                representative=entry_member or best,
                best=best,
                sections=sections,
                score_source="entry" if best.chunk.granularity == "entry" else "section-rollup",
            )
        )
    return rollups


def rollup_entry_results(ranked: list[RankedMemoryChunk], *, top_k: int = 8) -> list[dict[str, Any]]:
    """Entry-level result dicts for Explorer/Trail consumers: the canonical
    ``ranked_to_dict`` fields of the representative, scored by the strongest
    member, plus ``best_match_chunk_id``, ``score_source``, and
    ``matched_sections`` highlight metadata.
    """
    records: list[dict[str, Any]] = []
    for rollup in rollup_entry_matches(ranked)[:top_k]:
        record = ranked_to_dict(rollup.representative)
        best = rollup.best
        record.update(
            {
                "score": round(best.final_score, 6),
                "match_score": round(best.match_score, 6),
                "lexical_score": round(best.lexical_score, 6),
                "semantic_score": None if best.semantic_score is None else round(best.semantic_score, 6),
                "recency_multiplier": round(best.recency_multiplier, 6),
                "matched_terms": list(best.matched_terms),
                "matched_fields": list(best.matched_fields),
            }
        )
        record["best_match_chunk_id"] = best.chunk.chunk_id
        record["score_source"] = rollup.score_source
        record["matched_sections"] = [
            {
                "chunk_id": section.chunk.chunk_id,
                "heading_path": list(section.chunk.heading_path),
                "line_range": [section.chunk.start_line, section.chunk.end_line],
                "excerpt": _excerpt(section.chunk.text),
            }
            for section in rollup.sections
        ]
        records.append(record)
    return records


def _human_report(query: str, results: list[dict[str, Any]]) -> str:
    lines = [f"Query: {query}", "Top results:"]
    for index, result in enumerate(results, start=1):
        heading = " > ".join(result["heading_path"]) or "(untitled)"
        lines.append(
            f"{index}. {result['date']} {heading} "
            f"[score={result['score']}, source={result['source']}:{result['line_range'][0]}]"
        )
    if not results:
        lines.append("No matching memory chunks found.")
    return "\n".join(lines)


def _excerpt(text: str, limit: int = 280) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."

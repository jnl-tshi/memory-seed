"""Public retrieval service - the MCP-independent search/fetch surface.

This module is the canonical search-orchestration and result-dict contract for
every consumer: the MCP server (`memory_seed/mcp_server.py`) wraps it, the
deprecated in-package Memory Lense shim routes users to Memory Trace, and the
bundled `memory-trace` companion UI imports it as its frozen public API. Do
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
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:
    from .core import DecisionSummary

from .semantic_cache import (
    EmbeddingProvider,
    MemoryChunk,
    Model2VecEmbeddingProvider,
    RankedMemoryChunk,
    build_related_entry_graph,
    evolves_lineage_heads,
    extract_memory_chunks,
    rank_session_memory,
    superseding_lineage_heads,
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
    supersession_damping: bool = True,
    superseding_successor_boost: bool = True,
    topics: list[str] | None = None,
) -> dict[str, Any]:
    """Search session memory and return the canonical result payload.

    This is the full orchestration the MCP `memory_search` tool exposes:
    semantic-provider resolution (with lexical fallback), shared ranking via
    `rank_session_memory`, and `format_search_results` formatting. Non-MCP
    consumers call this directly and get identical answers.

    ``supersession_damping`` (freshness-aware-memory-ranking-proposal.md) is the
    supersession rank-dampener, ON by default: an entry with a non-empty
    ``superseded_by`` (drawn from the sidecar-augmented graph below) is
    multiplicatively down-ranked so a live replacement out-ranks the decision it
    retires. It only re-orders - it never hard-excludes (that stays
    ``exclude_superseded``) and never hides an entry: a superseded entry stays
    fully retrievable, just lower. Pass ``False`` to restore full-weight ordering.
    Graduated to default-on after validation on the real corpus (both YAML- and
    sidecar-authored supersession lineages surfaced the live replacement above the
    decisions it retired, with no effect on queries lacking a superseded hit).

    ``superseding_successor_boost`` is the separate, bounded successor-lift
    signal from supersession-successor-surfacing-proposal.md. It is ON by
    default here after fixture coverage plus the real-corpus ``ranking-ab`` gate
    passed. Pass ``False`` to restore damp-only ordering. Even when enabled,
    only terminal live replacements that already match the query can be lifted;
    nothing is hard-injected.
    """
    provider, provider_name, fallback_reason = resolve_semantic_provider(
        query,
        embedding_provider,
        enabled=semantic_enabled,
    )
    chunks = augment_chunks_with_link_sidecars(extract_memory_chunks(cwd, granularity=granularity), cwd)
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
        supersession_damping=supersession_damping,
        superseding_successor_boost=superseding_successor_boost,
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
        entry_id = result.get("entry_id") or ""
        node = graph.get(entry_id)
        result["superseded_by"] = list(node.superseded_by) if node else []
        result["superseding_head"] = list(superseding_lineage_heads(graph, entry_id))
        result["evolved_by"] = list(node.evolved_by) if node else []
        # Evolves successor-surfacing (freshness-aware-memory-ranking-proposal.md
        # item 2): point an evolved-but-still-valid hit at the head of its
        # evolution lineage - the current, fuller form - so it is reachable
        # without burying the original. Additive and read-only: evolves is never
        # dampened, and this changes no ordering. Empty when nothing evolves this
        # entry further; follows the chain transitively through the (sidecar-
        # augmented) graph.
        result["evolved_head"] = list(evolves_lineage_heads(graph, entry_id))
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
    entry_chunks = augment_chunks_with_link_sidecars(extract_memory_chunks(cwd, granularity="entry"), cwd)
    found = next((chunk for chunk in entry_chunks if chunk.chunk_id == chunk_id), None)
    if found is None:
        section_chunks = augment_chunks_with_link_sidecars(
            extract_memory_chunks(cwd, granularity="section"),
            cwd,
        )
        found = next((chunk for chunk in section_chunks if chunk.chunk_id == chunk_id), None)
    if found is None:
        raise ValueError(f"chunk_id not found: {chunk_id}")
    payload = chunk_to_dict(found)
    superseded_by: list[str] = []
    superseding_head: list[str] = []
    evolved_by: list[str] = []
    inbound_relation_count = 0
    importance_score = 0.0
    graph = build_related_entry_graph(chunks=entry_chunks)
    if found.entry_id:
        node = graph.get(found.entry_id)
        if node is not None:
            superseded_by = list(node.superseded_by)
            superseding_head = list(superseding_lineage_heads(graph, found.entry_id))
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
    payload["superseding_head"] = superseding_head
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
# Same entry-block shape as _DIAGRAM_ENTRY_RE; a link sidecar block is keyed to
# its source entry's id and carries the typed lifecycle edges authored later.
_LINK_ENTRY_RE = re.compile(
    r"^##\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2})\s+-\s*([^\n]*)\n\s*```ya?ml\s*\n(.*?)^```\s*$",
    re.MULTILINE | re.DOTALL,
)


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


def entry_link_sidecars(cwd: str | Path = ".") -> dict[str, dict[str, Any]]:
    """Late-authored lifecycle edges, keyed by source ``entry_id``.

    Mirrors ``entry_diagram_sidecars``: sidecars live under
    ``.memory-seed/sessions/links/YYYY-MM/YYYY-MM-DD.md`` (legacy flat
    ``links/YYYY-MM-DD.md`` also read), one dated file per day. Each block is a
    session-entry-shaped heading plus a fenced yaml carrying the source
    ``entry_id`` and any of ``supersedes`` / ``evolves`` / ``related_entries``
    lists - the typed edges an entry gained *after* it was written, without
    reopening the append-only entry. Refs are extracted with the same regex
    ``links check`` validates against, so the reader and the integrity gate
    agree. Multiple blocks keyed to one entry union their edges. Returns an
    empty map when the dir is absent; malformed sidecars are skipped here and
    surfaced by ``links check``.
    """
    # _TRAILER_ENTRY_ID_RE, not the strict _RELATED_ENTRY_REF_RE: real corpus
    # ids include non-Crockford letters (o/u/i/l, e.g. codex-authored entries),
    # which the strict charset silently drops - an edge that vanishes without a
    # trace. The wider match is safe because links check validates every ref
    # against known entries: a bad token becomes a dangling-* issue, not a
    # silent no-op.
    from .core import (
        _frontmatter_list_refs,
        iter_link_sidecar_documents,
        resolve_runtime,
    )

    runtime = resolve_runtime(cwd)
    links_dir = runtime.memory_dir / "sessions" / "links"
    sidecars: dict[str, dict[str, Any]] = {}
    if not links_dir.is_dir():
        return sidecars
    for link_doc in iter_link_sidecar_documents(runtime.memory_dir / "sessions"):
        if link_doc.malformed_reason:
            continue
        path = link_doc.path
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        try:
            rel = path.relative_to(runtime.workspace_root).as_posix()
        except ValueError:
            rel = path.as_posix()
        for block in _LINK_ENTRY_RE.finditer(text):
            heading_ts, _title, yaml_block = block.groups()
            entry_id = None
            for line in yaml_block.splitlines():
                stripped = line.strip()
                if stripped.startswith("entry_id:"):
                    entry_id = stripped.split(":", 1)[1].strip().strip("'\"")
                    break
            if not entry_id:
                continue
            # Entry-level refs keep their existing keys unchanged. Decision
            # refs are collected separately and NEVER folded into them: "D2 of
            # B supersedes D1 of A" does not license "B supersedes A", so a
            # consumer that does not model decisions must see exactly the edge
            # set it saw before this feature existed.
            found: dict[str, Any] = {}
            decisions: list[tuple[str, str, str]] = []
            for key in ("supersedes", "evolves", "related_entries"):
                entry_level: list[str] = []
                for parsed in _frontmatter_list_refs(yaml_block, key):
                    if not parsed.ok:
                        continue  # links check reports it; readers skip it
                    if parsed.decision is None:
                        entry_level.append(parsed.entry_id)
                    else:
                        decisions.append((key, parsed.entry_id, parsed.decision))
                found[key] = tuple(entry_level)
            found["decision_edges"] = tuple(decisions)
            existing = sidecars.get(entry_id)
            if existing:
                # decision_edges is merged alongside the entry-level keys: two
                # sidecar blocks may key to one entry (different days, or a
                # correction), and dropping the later block's decision refs
                # would lose edges silently rather than loudly.
                for key in ("supersedes", "evolves", "related_entries", "decision_edges"):
                    existing[key] = tuple(dict.fromkeys(existing.get(key, ()) + found[key]))
            else:
                sidecars[entry_id] = {
                    "entry_id": entry_id,
                    "path": rel,
                    "heading_datetime": heading_ts,
                    **found,
                }
    return sidecars


def augment_chunks_with_link_sidecars(
    chunks: Iterable[MemoryChunk],
    cwd: str | Path = ".",
) -> list[MemoryChunk]:
    """Union entry YAML edges with append-only link sidecar edges.

    Link sidecars are authored after a session entry is written, so the
    effective graph is ``union(entry YAML, sidecar)`` at read time. This helper
    augments the input chunks before callers build ``build_related_entry_graph``
    so outbound edges, inverse freshness fields, and result payloads all agree
    without teaching ``semantic_cache`` how to read sidecar files.
    """
    entries = list(chunks)
    sidecars = entry_link_sidecars(cwd)
    if not sidecars:
        return entries

    def union(base: tuple[str, ...], extra: Iterable[str], entry_id: str | None) -> tuple[str, ...]:
        merged = list(base)
        for ref in extra:
            if ref and ref != entry_id and ref not in merged:
                merged.append(ref)
        return tuple(merged)

    augmented: list[MemoryChunk] = []
    for chunk in entries:
        extra = sidecars.get(chunk.entry_id or "")
        if not extra:
            augmented.append(chunk)
            continue
        augmented.append(
            replace(
                chunk,
                related_entries=union(chunk.related_entries, extra.get("related_entries", ()), chunk.entry_id),
                supersedes=union(chunk.supersedes, extra.get("supersedes", ()), chunk.entry_id),
                evolves=union(chunk.evolves, extra.get("evolves", ()), chunk.entry_id),
            )
        )
    return augmented


# Weight on idf-summed shared TITLE terms, alongside FILE_OVERLAP_BOOST on
# shared files. Tuned against ground truth rather than taste: the 101
# supersedes/evolves edges authors declared in entry YAML across the corpus.
# Those are human-confirmed and predate this change, so they are not the
# handful of edges that motivated it. At this weight recall@5 goes 45% -> 59%,
# recall@10 52% -> 68%, and the true target's median rank 8 -> 3.
TITLE_OVERLAP_BOOST = 2.0

# Weight on model2vec cosine similarity between two entries' full text. Set by
# a sweep against ground truth, not by taste - see the session entry for the
# table. Large relative to the lexical boosts because cosine is bounded to
# [0,1] while an idf sum is not; the two are on different scales, not
# different importances.
SEMANTIC_OVERLAP_BOOST = 160.0


def _embed_entries_for_link_audit(chunks: list[MemoryChunk]) -> dict[str, Any] | None:
    """L2-normalised embeddings per entry, or None when unavailable.

    Returns None rather than raising on any failure - a missing provider is the
    documented lightweight install (`pip install --no-deps memory-seed`), not an
    error, and link audit must still produce lexical results there.
    """
    provider, _name, fallback = resolve_semantic_provider("link audit", enabled=True)
    if provider is None or fallback:
        return None
    ids = [chunk.entry_id or "" for chunk in chunks]
    try:
        raw = provider.embed([f"{chunk.title}\n{chunk.text}" for chunk in chunks])
    except Exception:
        return None
    vectors: dict[str, Any] = {}
    for entry_id, vector in zip(ids, raw):
        if not entry_id:
            continue
        norm = sum(value * value for value in vector) ** 0.5 or 1.0
        vectors[entry_id] = [value / norm for value in vector]
    return vectors

# Title words that carry no discriminating signal in this corpus: workstream
# labels and the verbs nearly every entry title opens with. Without these
# removed, two unrelated entries both called "Phase 0 B0b: add ..." score as
# neighbours - which is the failure the title signal exists to avoid, not a
# version of it.
_TITLE_STOP_TERMS = frozenset(
    # Function words, on linguistic grounds - not tuned to any observed pair.
    """the a an and or to of for in on at is are be with not no its it into from by as that this
    all any both each more most only own same some such too very out off over per via but than
    then when where which while
    """.split()
    # Corpus-specific: workstream labels and the verbs nearly every title opens
    # with. idf alone does not demote these enough, because they are frequent
    # AND correlated with each other rather than with any real relationship.
    + """add adds fix fixes ship ships make makes complete completes phase slice b0a b0b
    memory trace seed new use uses run runs""".split()
)


def _title_terms(title: str) -> set[str]:
    """Distinctive lowercase words in an entry title, for overlap scoring.

    The leading ``YYYY-MM-DD HH:MM - `` stamp is stripped first. A chunk's
    title carries it, and left in it makes "2026" a term shared by essentially
    every pair in the corpus - which would turn a discriminating signal into a
    universal one.
    """
    stripped = re.sub(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}\s*-\s*", "", title or "")
    return {
        word
        for word in re.findall(r"[a-z0-9]+", stripped.lower())
        if len(word) > 2 and word not in _TITLE_STOP_TERMS
    }


@dataclass(frozen=True)
class LinkGapCandidate:
    entry_id: str
    title: str
    session_date: str
    shared_files: tuple[str, ...]
    shared_topics: tuple[str, ...]
    # Distinctive title words the two entries share, idf-weighted. Measured
    # against the 101 lifecycle edges authors declared in entry YAML, adding
    # this to the score moved recall@5 from 45% to 59% and the true target's
    # median rank from 8 to 3 - file overlap alone ranks whichever foundational
    # entry touched the same high-churn file above the actual predecessor.
    shared_title_terms: tuple[str, ...]
    file_overlap_score: float
    # True when a related_entries link already exists but no lifecycle edge -
    # the "supersession mislabelled as related" case the sweep should upgrade.
    already_related: bool = False
    # The candidate's own decisions (ordinal + name + body), so an edge can be
    # narrowed to `:dN`. Empty for a no-decision entry. This is surfaced, not
    # scored: the mechanical evidence is entry-level and cannot discriminate
    # decisions, so which one an edge targets is a human's (or a judgment
    # agent's) call, exactly as the supersedes/evolves/related TYPE already is.
    decisions: tuple[DecisionSummary, ...] = ()


@dataclass(frozen=True)
class LinkGap:
    entry_id: str
    title: str
    session_date: str
    candidates: tuple[LinkGapCandidate, ...]
    # The audited (newer) entry's own decisions - the source side of any edge.
    decisions: tuple[DecisionSummary, ...] = ()


@dataclass(frozen=True)
class LinkAuditApplyResult:
    path: Path
    added_entry_ids: tuple[str, ...]
    skipped_entry_ids: tuple[str, ...]

    @property
    def changed(self) -> bool:
        return bool(self.added_entry_ids)


def audit_link_gaps(
    cwd: str | Path = ".",
    *,
    entry_id: str | None = None,
    session_date: str | None = None,
    top_k: int = 5,
    semantic_enabled: bool = True,
) -> list[LinkGap]:
    """Find entry pairs that share files or topics but carry no recorded edge.

    Candidate generation deliberately avoids an all-pairs semantic scan: for
    each target entry the candidate set is the OLDER entries that share >=1
    ``F:`` file OR >=1 topic with it. File overlap qualifies a pair even when no
    topic is shared - matching files override the absence of a topic link.
    Candidates already captured by any edge (``related_entries`` /
    ``supersedes`` / ``evolves``, entry YAML or a link sidecar) are dropped, so
    only genuine gaps remain. The survivors rank by IDF-weighted file overlap
    (hub files like a shared app.js contribute ~nothing) then shared-topic
    count - the classification into supersedes/evolves/related is left to the
    caller (the end-of-session sweep). Read-only; forward-only by construction.

    ``session_date`` (YYYY-MM-DD) scopes the TARGETS to one session's entries
    while candidates remain the full corpus - the end-of-session sweep audits
    only the entries it just wrote (O(K*N), K = today's entries) instead of
    re-auditing history every session.
    """
    import math

    from .core import entry_body_decisions
    from .semantic_cache import (
        FILE_OVERLAP_BOOST,
        _continuity_alias_map,
        _entry_file_refs,
        _entry_order_key,
        extract_memory_chunks,
    )

    chunks = [chunk for chunk in extract_memory_chunks(cwd, granularity="entry") if chunk.entry_id]
    if not chunks:
        return []
    by_id = {chunk.entry_id: chunk for chunk in chunks}
    if entry_id is not None and entry_id not in by_id:
        raise LookupError(f"entry_id {entry_id} not found")

    sidecars = entry_link_sidecars(cwd)
    alias = _continuity_alias_map(chunks)
    file_refs: dict[str, set[str]] = {}
    topics_of: dict[str, set[str]] = {}
    document_frequency: dict[str, int] = {}
    order: dict[str, Any] = {}
    # Decision structure per entry, so a surfaced pair can be narrowed to `:dN`.
    # Extracted once here, attached to both ends below; never fed to scoring.
    decisions_of: dict[str, tuple[Any, ...]] = {
        chunk.entry_id or "": tuple(entry_body_decisions(chunk.text)) for chunk in chunks
    }
    for chunk in chunks:
        refs = {alias.get(ref, ref) for ref in _entry_file_refs(chunk.text)}
        file_refs[chunk.entry_id or ""] = refs
        topics_of[chunk.entry_id or ""] = set(chunk.topics)
        order[chunk.entry_id or ""] = _entry_order_key(chunk)
        for ref in refs:
            document_frequency[ref] = document_frequency.get(ref, 0) + 1
    total = len(chunks)

    def idf(ref: str) -> float:
        occurrences = document_frequency.get(ref, 0)
        return max(math.log(total / occurrences), 0.0) if occurrences > 0 else 0.0

    # Title terms, same idf treatment as file refs. The stop list is the words
    # that carry no discriminating signal in THIS corpus - workstream names and
    # verbs nearly every entry title uses - so "Phase 0 B0b: add file graph
    # mode" contributes "file", "graph", "mode" and not "phase"/"add".
    title_frequency: dict[str, int] = {}
    title_terms: dict[str, set[str]] = {}
    for chunk in chunks:
        terms = _title_terms(chunk.title)
        title_terms[chunk.entry_id or ""] = terms
        for term in terms:
            title_frequency[term] = title_frequency.get(term, 0) + 1

    def title_idf(term: str) -> float:
        occurrences = title_frequency.get(term, 0)
        return max(math.log(total / occurrences), 0.0) if occurrences > 0 else 0.0

    def related_of(chunk: MemoryChunk) -> set[str]:
        sidecar = sidecars.get(chunk.entry_id or "", {})
        return set(chunk.related_entries) | set(sidecar.get("related_entries", ()))

    def lifecycle_of(chunk: MemoryChunk) -> set[str]:
        sidecar = sidecars.get(chunk.entry_id or "", {})
        return (
            set(chunk.supersedes)
            | set(chunk.evolves)
            | set(sidecar.get("supersedes", ()))
            | set(sidecar.get("evolves", ()))
            # A decision-level ref (`<id>:dN`) records the pair at FINER
            # granularity. It deliberately never projects into the entry-level
            # edge sets, but for gap-finding the pair is linked - without this
            # union every decision-narrowed edge re-surfaces as a "gap" forever.
            | {
                eid
                for kind, eid, _ordinal in sidecar.get("decision_edges", ())
                if kind in ("supersedes", "evolves")
            }
        )

    # Semantic similarity, when the embedding provider is available. Purely a
    # RANKING term: cosine is dense - every pair scores non-zero - so using it
    # to decide whether a pair is a candidate at all would make every earlier
    # entry a candidate for every later one. The lexical gate below still
    # decides membership; this only reorders what got through.
    #
    # Fails open exactly like search_memory: no provider means lexical-only
    # scoring, which is the documented lightweight install, not an error.
    vectors: dict[str, Any] | None = None
    if semantic_enabled:
        vectors = _embed_entries_for_link_audit(chunks)

    def semantic_similarity(source_id: str, candidate_id: str) -> float:
        if not vectors:
            return 0.0
        a = vectors.get(source_id)
        b = vectors.get(candidate_id)
        if a is None or b is None:
            return 0.0
        return max(0.0, float(sum(x * y for x, y in zip(a, b))))

    if entry_id is not None:
        targets = [by_id[entry_id]]
    elif session_date is not None:
        targets = [chunk for chunk in chunks if chunk.session_date.isoformat() == session_date]
    else:
        targets = chunks
    gaps: list[LinkGap] = []
    for target in targets:
        tid = target.entry_id or ""
        target_files = file_refs.get(tid, set())
        target_topics = topics_of.get(tid, set())
        target_title_terms = title_terms.get(tid, set())
        target_related = related_of(target)
        target_lifecycle = lifecycle_of(target)
        target_key = order[tid]
        candidates: list[LinkGapCandidate] = []
        for chunk in chunks:
            cid = chunk.entry_id or ""
            if cid == tid or order[cid] >= target_key:  # forward-only: only older entries
                continue
            if cid in target_lifecycle:  # a lifecycle edge already records this pair
                continue
            shared_files = tuple(sorted(target_files & file_refs.get(cid, set())))
            shared_topics = tuple(sorted(target_topics & topics_of.get(cid, set())))
            shared_title = tuple(sorted(target_title_terms & title_terms.get(cid, set())))
            # Files or a distinctive shared title term surface a lifecycle
            # candidate (even if merely "related" today - the upgrade case).
            # Topic-only overlap is far weaker, so any existing edge suppresses
            # it - it isn't worth flagging a topic-mate you already linked.
            if shared_files or shared_title:
                pass
            elif shared_topics and cid not in target_related:
                pass
            else:
                continue
            score = FILE_OVERLAP_BOOST * sum(idf(ref) for ref in shared_files) + TITLE_OVERLAP_BOOST * sum(
                title_idf(term) for term in shared_title
            )
            similarity = semantic_similarity(tid, cid)
            score += SEMANTIC_OVERLAP_BOOST * similarity
            candidates.append(
                LinkGapCandidate(
                    entry_id=cid,
                    title=chunk.title,
                    session_date=chunk.session_date.isoformat(),
                    shared_files=shared_files,
                    shared_topics=shared_topics,
                    shared_title_terms=shared_title,
                    file_overlap_score=round(score, 6),
                    already_related=cid in target_related,
                    decisions=decisions_of.get(cid, ()),
                )
            )
        candidates.sort(key=lambda c: (c.file_overlap_score, len(c.shared_topics)), reverse=True)
        if candidates:
            gaps.append(
                LinkGap(
                    entry_id=tid,
                    title=target.title,
                    session_date=target.session_date.isoformat(),
                    candidates=tuple(candidates[:top_k]),
                    decisions=decisions_of.get(tid, ()),
                )
            )
    return gaps


def apply_link_gap_stubs(
    gaps: Iterable[LinkGap],
    *,
    session_date: str,
    cwd: str | Path = ".",
) -> LinkAuditApplyResult:
    """Add inert classification stubs to one dated link sidecar.

    Existing sidecar blocks are never changed. New blocks are inserted by the
    source entry's timestamp, carry only ``classify_pending: true`` plus
    comment-only candidate evidence, and are skipped when any sidecar block
    already exists for that source entry. Session entries are read only.
    """
    from .core import _parse_frontmatter_scalars, resolve_runtime
    from .semantic_cache import _entry_order_key, extract_memory_chunks
    from .text_files import read_text_file, write_text_file

    try:
        parsed_date = date.fromisoformat(session_date)
    except ValueError as exc:
        raise ValueError(f"Invalid session date: {session_date}") from exc
    if parsed_date.isoformat() != session_date:
        raise ValueError(f"Invalid session date: {session_date}")

    runtime = resolve_runtime(cwd)
    target = (
        runtime.memory_dir
        / "sessions"
        / "links"
        / session_date[:7]
        / f"{session_date}.md"
    )
    gap_list = list(gaps)
    existing_sources = set(entry_link_sidecars(cwd))
    pending = [gap for gap in gap_list if gap.entry_id not in existing_sources]
    skipped = tuple(gap.entry_id for gap in gap_list if gap.entry_id in existing_sources)
    if not pending:
        return LinkAuditApplyResult(path=target, added_entry_ids=(), skipped_entry_ids=skipped)

    chunks = {
        chunk.entry_id: chunk
        for chunk in extract_memory_chunks(cwd, granularity="entry")
        if chunk.entry_id
    }
    missing = [gap.entry_id for gap in pending if gap.entry_id not in chunks]
    if missing:
        raise ValueError(f"Cannot scaffold unknown entry_id(s): {', '.join(missing)}")
    for gap in pending:
        chunk = chunks[gap.entry_id]
        if chunk.session_date.isoformat() != session_date:
            raise ValueError(
                f"entry_id {gap.entry_id} belongs to {chunk.session_date.isoformat()}, not {session_date}"
            )
        if chunk.entry_datetime is None:
            raise ValueError(f"entry_id {gap.entry_id} has no parseable heading timestamp")

    frontmatter = "\n".join(
        [
            "---",
            "tags:",
            "  - session-log-links",
            f"link_date: {session_date}",
            "---",
            "",
        ]
    )
    existing = ""
    existing_blocks: list[re.Match[str]] = []
    if target.exists():
        existing = read_text_file(target)
        frontmatter_match = re.match(r"\A---\s*\n(.*?)^---\s*\n", existing, re.MULTILINE | re.DOTALL)
        if frontmatter_match is None:
            raise ValueError(f"Existing link sidecar has no frontmatter: {target}")
        scalars = _parse_frontmatter_scalars(frontmatter_match.group(1))
        has_tag = bool(re.search(r"^\s*-\s*session-log-links\s*$", frontmatter_match.group(1), re.MULTILINE))
        if scalars.get("link_date") != session_date or not has_tag:
            raise ValueError(f"Existing link sidecar has incorrect frontmatter: {target}")
        existing_blocks = list(_LINK_ENTRY_RE.finditer(existing))
        if existing[frontmatter_match.end():].strip() and not existing_blocks:
            raise ValueError(f"Existing link sidecar has no parseable entry blocks: {target}")
        timestamps = [match.group(1) for match in existing_blocks]
        if timestamps != sorted(timestamps):
            raise ValueError(f"Existing link sidecar blocks are not chronological: {target}")
    else:
        existing = frontmatter

    def render_stub(gap: LinkGap) -> tuple[str, str, str]:
        chunk = chunks[gap.entry_id]
        timestamp = chunk.entry_datetime.strftime("%Y-%m-%d %H:%M")
        lines = [
            f"## {chunk.title}",
            "",
            "```yaml",
            f"entry_id: {gap.entry_id}",
            "classify_pending: true",
            "# candidates (evidence):",
        ]
        for candidate in gap.candidates:
            evidence: list[str] = []
            if candidate.shared_files:
                evidence.append(f"files: {', '.join(candidate.shared_files)}")
            if candidate.shared_topics:
                evidence.append(f"topics: {', '.join(candidate.shared_topics)}")
            if candidate.already_related:
                evidence.append("already related; consider a lifecycle upgrade")
            suffix = f"  # {' | '.join(evidence)}" if evidence else ""
            lines.append(f"#   - {candidate.entry_id}{suffix}")
        lines.extend(["```", ""])
        return timestamp, gap.entry_id, "\n".join(lines)

    rendered = [render_stub(gap) for gap in sorted(pending, key=lambda gap: _entry_order_key(chunks[gap.entry_id]))]
    insertions: dict[int, list[tuple[str, str, str]]] = {}
    for item in rendered:
        timestamp = item[0]
        offset = next(
            (match.start() for match in existing_blocks if match.group(1) > timestamp),
            len(existing),
        )
        insertions.setdefault(offset, []).append(item)

    updated = existing
    for offset in sorted(insertions, reverse=True):
        items = sorted(insertions[offset], key=lambda item: (item[0], item[1]))
        addition = "\n".join(item[2].rstrip("\n") for item in items) + "\n\n"
        prefix = updated[:offset]
        suffix = updated[offset:]
        if prefix and not prefix.endswith("\n\n"):
            prefix = prefix + ("\n" if prefix.endswith("\n") else "\n\n")
        updated = prefix + addition + suffix

    write_text_file(target, updated.rstrip("\n") + "\n")
    return LinkAuditApplyResult(
        path=target,
        added_entry_ids=tuple(item[1] for item in rendered),
        skipped_entry_ids=skipped,
    )


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

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from functools import lru_cache
from typing import Any, Callable, Protocol, Sequence

from .core import SessionDocument, _parse_continuity_items, iter_session_documents, resolve_runtime


HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
TAG_RE = re.compile(r"(?<![\w/.-])#([A-Za-z][A-Za-z0-9_-]*)")
IDENTIFIER_RE = re.compile(
    r"(?<![\w/])(?:`?)([A-Za-z0-9_.-]*[A-Za-z_][A-Za-z0-9_.-]*(?:/[A-Za-z0-9_.-]+)*)(?:`?)"
)
STRUCTURAL_QUERY_TERMS = (
    "architecture",
    "baseline",
    "bootstrap",
    "control plane",
    "spec",
    "design",
)
ENTRY_DATETIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2})\s+-\s+.+$")

# Multiplier applied to a superseded entry's importance_score (the harmony
# contract from supersession-edges-plan.md). A superseded decision drops to a
# quarter of its raw citation weight - strong enough that a well-cited but
# retired decision ranks below a live, moderately-cited one, without erasing it
# (never hide, only deprioritize). Tunable; affects only the read-only
# importance_score signal, never default memory_search ranking.
SUPERSEDED_IMPORTANCE_DAMPING = 0.25

# Multiplier folded into final_score for a superseded entry when the caller opts
# into supersession-aware ranking (freshness-aware-memory-ranking-proposal.md).
# Mirrors the SUPERSEDED_IMPORTANCE_DAMPING harmony constant so a replaced
# decision sinks beneath its live replacement in the default order - but it is
# DEFAULT-OFF: rank_memory_chunks only applies it when passed the superseded id
# set (gated by rank_session_memory / search_memory's supersession_damping flag).
# It composes multiplicatively with recency_multiplier and never hard-excludes
# (that stays exclude_superseded): a superseded entry is down-ranked, not hidden.
SUPERSEDED_RANK_DAMPING = 0.25

# Scale applied to the rarity-weighted F:-file-overlap sum when re-ranking
# link-suggest candidates (evolution-edges-plan.md D5). Overlap is a precision
# boost layered on the similarity ranking, never a gate: entries without F:
# paths get a zero bonus and no penalty, and hub files shared by most entries
# contribute ~nothing via the idf weighting.
FILE_OVERLAP_BOOST = 0.75


@dataclass(frozen=True)
class ContinuityBlock:
    """One stored ``continuity:`` item - artifact lineage, not an entry edge.

    Records that an artifact (file path, directory, command, or concept term)
    was renamed, migrated, or removed, with direction preserved
    (evolution-edges-plan.md D6). Values are historical labels like ``branch:``
    - never validated against the live filesystem or git. ``to_ref`` is None
    for ``removal`` (a removal with a successor is a rename or a supersession).
    Malformed items are kept as parsed; ``links check`` owns reporting them.
    """

    kind: str
    from_ref: str
    to_ref: str | None = None


@dataclass(frozen=True)
class MemoryChunk:
    chunk_id: str
    source_path: str
    source_file: str
    session_date: date
    entry_datetime: datetime | None
    heading_path: tuple[str, ...]
    heading_level: int
    title: str
    text: str
    tags: tuple[str, ...]
    contexts: tuple[str, ...]
    lexical_terms: tuple[str, ...]
    start_line: int
    end_line: int
    entry_id: str | None = None
    user_initials: str | None = None
    agent_type: str | None = None
    agent_name: str | None = None
    project_path: str | None = None
    subproject_path: str | None = None
    user: str | None = None
    file_hash_id: str | None = None
    related_entries: tuple[str, ...] = ()
    supersedes: tuple[str, ...] = ()
    # Typed lifecycle edge: earlier decisions this entry extends/refines while
    # they stay valid (evolves), vs. supersedes which retires its targets.
    evolves: tuple[str, ...] = ()
    commits: tuple[str, ...] = ()
    # Stored artifact-lineage blocks (rename/migration/removal); see
    # ContinuityBlock. A label family like ``branch:``, not an entry edge.
    continuity: tuple[ContinuityBlock, ...] = ()
    # Authored controlled-vocabulary membership (1-3 slugs from
    # .memory-seed/topics.yaml). Distinct from hashtag-derived ``tags`` and
    # heading-derived ``contexts``, which remain the display fallback.
    topics: tuple[str, ...] = ()
    # Optional git branch the entry's work happened on, captured at record time
    # (parallel in spirit to ``commits``). Forward-only, never backfilled, and a
    # durable historical label - not validated against live git refs.
    branch: str | None = None
    entry_title: str | None = None
    entry_line_range: tuple[int, int] | None = None
    sections: tuple[str, ...] = ()
    granularity: str = "legacy"


@dataclass(frozen=True)
class RankedMemoryChunk:
    chunk: MemoryChunk
    final_score: float
    match_score: float
    lexical_score: float
    semantic_score: float | None
    recency_multiplier: float
    age_days: int
    matched_terms: tuple[str, ...]
    matched_fields: tuple[str, ...]


class EmbeddingProvider(Protocol):
    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        ...


class Model2VecEmbeddingProvider:
    default_model_name = "minishlab/potion-base-8M"

    def __init__(
        self,
        model_name: str = default_model_name,
        model_loader: Callable[[str], Any] | None = None,
    ):
        self.model_name = model_name
        self.name = f"model2vec:{model_name}"
        self._model_loader = model_loader or _load_model2vec_model
        self._model: Any | None = None

    def embed(self, texts: Sequence[str]) -> Sequence[Sequence[float]]:
        model = self._get_model()
        vectors = model.encode(list(texts))
        return [_vector_to_tuple(vector) for vector in vectors]

    def _get_model(self) -> Any:
        if self._model is None:
            self._model = self._model_loader(self.model_name)
        return self._model


@lru_cache(maxsize=2)
def _load_model2vec_model(model_name: str) -> Any:
    from model2vec import StaticModel

    return StaticModel.from_pretrained(model_name)


def _vector_to_tuple(vector: Any) -> tuple[float, ...]:
    if hasattr(vector, "tolist"):
        vector = vector.tolist()
    return tuple(float(value) for value in vector)


def extract_memory_chunks(cwd: str | Path = ".", *, granularity: str = "entry") -> list[MemoryChunk]:
    if granularity not in ("entry", "section"):
        raise ValueError("granularity must be 'entry' or 'section'")
    runtime = resolve_runtime(cwd)
    target_root = runtime.workspace_root
    sessions_dir = runtime.memory_dir / "sessions"
    if not sessions_dir.is_dir():
        return []

    chunks: list[MemoryChunk] = []
    for doc in iter_session_documents(sessions_dir):
        try:
            session_date = datetime.strptime(doc.session_date, "%Y-%m-%d").date()
        except ValueError:
            continue
        chunks.extend(_extract_chunks_from_file(target_root, doc, session_date, granularity=granularity))
    return chunks


def rank_session_memory(
    query: str,
    cwd: str | Path = ".",
    *,
    top_k: int = 8,
    today: date | None = None,
    lambda_days: float = 0.01,
    recency_enabled: bool = True,
    recency_floor: float = 0.15,
    embedding_provider: EmbeddingProvider | None = None,
    granularity: str = "entry",
    user: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    exclude_superseded: bool = False,
    supersession_damping: bool = False,
    chunks: Sequence[MemoryChunk] | None = None,
    topics: set[str] | None = None,
) -> list[RankedMemoryChunk]:
    # Pass ``chunks`` to reuse an already-extracted corpus (matching
    # ``granularity``) and keep the search path free of re-parsing.
    # ``topics`` is a pre-expanded slug match set (canonical + aliases; see
    # topics.expand_topic_filter) - a pre-ranking gate like user/date filters.
    corpus = list(chunks) if chunks is not None else extract_memory_chunks(cwd, granularity=granularity)
    chunks = _filter_chunks(corpus, user=user, date_from=date_from, date_to=date_to, topics=topics)
    # The superseded id set feeds both the opt-in hard filter (exclude_superseded)
    # and the opt-in rank-dampener (supersession_damping); build it once over the
    # pre-filter corpus so a superseding entry outside the user/date window still
    # counts. When ``corpus`` is the sidecar-augmented set passed by search_memory,
    # sidecar-authored supersessions are included. Being evolved never lands here -
    # evolution is freshness, not retirement.
    superseded_ids: set[str] = set()
    if exclude_superseded or supersession_damping:
        superseded_ids = {
            node.entry_id
            for node in build_related_entry_graph(cwd, chunks=corpus).values()
            if node.superseded_by
        }
    if exclude_superseded:
        # Opt-in narrowing (like date_from/date_to): drop entries that have been
        # superseded by a later decision. Never a default and never a hard
        # exclusion unless the caller asks - superseded entries remain fully
        # retrievable by default (deprioritized via the dampener/importance_score,
        # not hidden).
        chunks = [chunk for chunk in chunks if chunk.entry_id not in superseded_ids]
    return rank_memory_chunks(
        query,
        chunks,
        top_k=top_k,
        today=today,
        lambda_days=lambda_days,
        recency_enabled=recency_enabled,
        recency_floor=recency_floor,
        embedding_provider=embedding_provider,
        # DEFAULT-OFF: only pass the dampener input when the caller opted in, so
        # default ranking order stays byte-for-byte identical to today.
        superseded_ids=superseded_ids if supersession_damping else None,
    )


def _filter_chunks(
    chunks: Sequence[MemoryChunk],
    *,
    user: str | None,
    date_from: date | None,
    date_to: date | None,
    topics: set[str] | None = None,
) -> list[MemoryChunk]:
    filtered: list[MemoryChunk] = []
    for chunk in chunks:
        if user is not None and chunk.user != user:
            continue
        if date_from is not None and chunk.session_date < date_from:
            continue
        if date_to is not None and chunk.session_date > date_to:
            continue
        if topics is not None and not (topics & set(chunk.topics)):
            continue
        filtered.append(chunk)
    return filtered


@dataclass(frozen=True)
class RelatedEntryNode:
    """One node in the related-entry graph.

    ``outbound`` is the entry's stored ``related_entries`` (the forward edges it
    declared at write time). ``inbound`` is computed at read time from every
    other entry that points here - the backlinks that make traversal
    bidirectional without ever editing a historical entry. Inbound is built only
    from refs that resolve to a known entry_id; ``outbound`` is reported as
    stored (run ``links check`` to surface any dangling outbound ref).

    ``supersedes`` is the entry's stored typed edge marking earlier decisions it
    replaces; ``superseded_by`` is its computed inverse, built the same way as
    ``inbound``. The two edge kinds are never merged: a supersession is a status
    signal (this decision is retired), not a relatedness signal.

    ``evolves`` is the entry's stored typed edge marking earlier decisions it
    extends or refines *while they remain valid*; ``evolved_by`` is its
    computed, read-time-only inverse (never stored in any file - append-only is
    preserved because the inverse exists only in this derived layer). Being
    evolved is a freshness signal, not a retirement: it never dampens
    ``importance_score`` and never feeds ``exclude_superseded``.

    ``importance_score`` is the read-only ranking precursor: the inbound
    ``related_entries`` count (``len(inbound)``), dampened by
    ``SUPERSEDED_IMPORTANCE_DAMPING`` when the entry has any ``superseded_by``
    edge. Supersession edges never contribute to the count itself - the
    dampener is applied after, as a hard override. ``evolved_by`` edges never
    dampen. Not blended into default ``memory_search`` ranking.
    """

    entry_id: str
    title: str
    source_path: str
    session_date: date
    outbound: tuple[str, ...]
    inbound: tuple[str, ...]
    supersedes: tuple[str, ...] = ()
    superseded_by: tuple[str, ...] = ()
    evolves: tuple[str, ...] = ()
    evolved_by: tuple[str, ...] = ()
    importance_score: float = 0.0


def _entry_order_key(chunk: MemoryChunk) -> tuple[date, datetime, int]:
    """Chronological sort key: session date, then within-file append order."""
    return (chunk.session_date, chunk.entry_datetime or datetime.min, chunk.start_line)


def build_related_entry_graph(
    cwd: str | Path = ".",
    *,
    chunks: Sequence[MemoryChunk] | None = None,
) -> dict[str, RelatedEntryNode]:
    """Build the bidirectional related-entry graph over all session entries.

    Stored edges are directed (an entry declares ``related_entries`` to prior
    entries). This inverts them at read time so each node also exposes its
    backlinks, giving MCP and future UI consumers an old<->new view without rewriting
    history. Assumes a ``links check``-clean corpus; on a duplicate ``entry_id``
    the first occurrence wins.

    Pass ``chunks`` to reuse an already-extracted entry-granularity corpus and
    skip re-parsing (e.g. a caller that already called ``extract_memory_chunks``).
    """
    if chunks is None:
        chunks = extract_memory_chunks(cwd, granularity="entry")
    by_id: dict[str, MemoryChunk] = {}
    for chunk in chunks:
        if chunk.entry_id and chunk.entry_id not in by_id:
            by_id[chunk.entry_id] = chunk

    inbound: dict[str, list[str]] = {entry_id: [] for entry_id in by_id}
    superseded_by: dict[str, list[str]] = {entry_id: [] for entry_id in by_id}
    evolved_by: dict[str, list[str]] = {entry_id: [] for entry_id in by_id}
    for chunk in chunks:
        if not chunk.entry_id:
            continue
        for ref in chunk.related_entries:
            if ref in by_id and ref != chunk.entry_id:
                inbound[ref].append(chunk.entry_id)
        for ref in chunk.supersedes:
            if ref in by_id and ref != chunk.entry_id:
                superseded_by[ref].append(chunk.entry_id)
        for ref in chunk.evolves:
            if ref in by_id and ref != chunk.entry_id:
                evolved_by[ref].append(chunk.entry_id)

    graph: dict[str, RelatedEntryNode] = {}
    for entry_id, chunk in by_id.items():
        inbound_ids = tuple(dict.fromkeys(inbound[entry_id]))
        superseded_by_ids = tuple(dict.fromkeys(superseded_by[entry_id]))
        evolved_by_ids = tuple(dict.fromkeys(evolved_by[entry_id]))
        importance = float(len(inbound_ids))
        if superseded_by_ids:
            # evolved_by deliberately does not dampen: an evolved decision is
            # still live, just incomplete without its evolutions.
            importance *= SUPERSEDED_IMPORTANCE_DAMPING
        graph[entry_id] = RelatedEntryNode(
            entry_id=entry_id,
            title=chunk.title,
            source_path=chunk.source_path,
            session_date=chunk.session_date,
            outbound=tuple(chunk.related_entries),
            inbound=inbound_ids,
            supersedes=tuple(chunk.supersedes),
            superseded_by=superseded_by_ids,
            evolves=tuple(chunk.evolves),
            evolved_by=evolved_by_ids,
            importance_score=importance,
        )
    return graph


def evolves_lineage_heads(
    graph: dict[str, RelatedEntryNode], entry_id: str
) -> tuple[str, ...]:
    """Follow the ``evolved_by`` chain from ``entry_id`` to the head(s) of its
    lineage - the newest entries that evolve this decision and are not themselves
    evolved further (the current, fuller form).

    Freshness-successor surfacing (freshness-aware-memory-ranking-proposal.md
    item 2 / evolution-edges-plan.md): evolves is *never* dampened, so this only
    points a reader at the up-to-date form without burying the still-valid
    original - it re-ranks and hides nothing. Returns terminal successor ids
    (excluding ``entry_id`` itself), empty when the entry has no evolutions. The
    evolves graph is acyclic by the edge contract; a ``seen`` set guards against a
    malformed cycle. Result is sorted for a deterministic payload.
    """
    node = graph.get(entry_id)
    if node is None or not node.evolved_by:
        return ()
    heads: set[str] = set()
    seen: set[str] = {entry_id}
    stack = list(node.evolved_by)
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        successor = graph.get(current)
        if successor is None or not successor.evolved_by:
            # Terminal: nothing evolves this one further -> head of lineage.
            heads.add(current)
        else:
            stack.extend(successor.evolved_by)
    return tuple(sorted(heads))


@dataclass(frozen=True)
class RelatedEntrySuggestion:
    """One link-suggest candidate: similarity ranking plus D5 file-overlap
    evidence. ``shared_files`` names the (alias-canonicalized) F: paths the
    candidate shares with the target - shown so the agent's
    evolves/supersedes/related judgment is concrete. ``chunk``/``final_score``
    pass-throughs keep older consumers of the plain ranked shape working."""

    result: RankedMemoryChunk
    shared_files: tuple[str, ...] = ()
    file_overlap_bonus: float = 0.0
    adjusted_score: float = 0.0

    @property
    def chunk(self) -> MemoryChunk:
        return self.result.chunk

    @property
    def final_score(self) -> float:
        return self.adjusted_score


_BACKTICK_TOKEN_RE = re.compile(r"`([^`\n]+)`")


def _normalize_file_ref(value: str) -> str:
    return value.strip().replace("\\", "/").rstrip(".,;")


def _entry_file_refs(text: str) -> tuple[str, ...]:
    """Conservatively extract file paths from an entry body's ``F:`` lines.

    Only backtick-quoted, whitespace-free tokens containing a ``/`` or ``.``
    are accepted - prose fragments ("same as D1", "live + seed") are ignored.
    Missed paths are acceptable; false ones are not (evolution-edges-plan.md
    D5). Continuation lines (indented, not a new bullet) are included so
    wrapped F: lists parse.
    """
    refs: list[str] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        stripped = lines[index].strip()
        if stripped.startswith("- F:"):
            block = [stripped[4:]]
            probe = index + 1
            while (
                probe < len(lines)
                and lines[probe][:1] in (" ", "\t")
                and not lines[probe].strip().startswith("- ")
            ):
                block.append(lines[probe].strip())
                probe += 1
            for token in _BACKTICK_TOKEN_RE.findall(" ".join(block)):
                if any(char.isspace() for char in token):
                    continue
                if "/" not in token and "." not in token:
                    continue
                normalized = _normalize_file_ref(token)
                if normalized:
                    refs.append(normalized)
            index = probe
            continue
        index += 1
    return tuple(dict.fromkeys(refs))


def _continuity_alias_map(chunks: Sequence[MemoryChunk]) -> dict[str, str]:
    """Old-name -> newest-name mapping derived from stored continuity blocks.

    Follows rename/migration chains transitively (Explorer -> Lense -> Trace
    resolves old names to the terminal one) with a cycle guard. Removals carry
    no ``to`` and never alias. Derived read-time only - nothing is written
    back (evolution-edges-plan.md D6).
    """
    mapping: dict[str, str] = {}
    for chunk in chunks:
        for block in chunk.continuity:
            if block.kind in ("rename", "migration") and block.from_ref and block.to_ref:
                mapping[_normalize_file_ref(block.from_ref)] = _normalize_file_ref(block.to_ref)
    resolved: dict[str, str] = {}
    for start in mapping:
        seen = {start}
        current = mapping[start]
        while current in mapping and current not in seen:
            seen.add(current)
            current = mapping[current]
        resolved[start] = current
    return resolved


def suggest_related_entries(
    cwd: str | Path = ".",
    *,
    entry_id: str | None = None,
    top_k: int = 5,
    embedding_provider: EmbeddingProvider | None = None,
) -> tuple[MemoryChunk, list[RelatedEntrySuggestion]]:
    """Rank candidate prior entries to link from a target entry.

    Forward-only by construction: candidates are restricted to entries *older*
    than the target, so acting on a suggestion only ever adds a backward-in-time
    edge to the target's own ``related_entries`` (the bidirectional model the
    user chose). Self and already-linked entries are excluded. The default
    target is the newest entry - "suggest links for the entry I just wrote".
    Read-only; it never writes. Ranking reuses ``rank_memory_chunks`` with
    recency disabled so similarity, not age, drives the ordering, then applies
    the D5 file-overlap boost: shared ``F:`` paths (alias-resolved through
    recorded continuity renames, rarity-weighted so hub files contribute
    ~nothing) raise semantically comparable candidates that touch the same
    decision surface. Entries without ``F:`` paths are never penalized.
    """
    chunks = [chunk for chunk in extract_memory_chunks(cwd, granularity="entry") if chunk.entry_id]
    if not chunks:
        raise LookupError("no session entries with an entry_id were found")

    if entry_id is not None:
        target = next((chunk for chunk in chunks if chunk.entry_id == entry_id), None)
        if target is None:
            raise LookupError(f"entry_id {entry_id} not found")
    else:
        target = max(chunks, key=_entry_order_key)

    target_key = _entry_order_key(target)
    linked = set(target.related_entries)
    candidates = [
        chunk
        for chunk in chunks
        if chunk.entry_id != target.entry_id
        and chunk.entry_id not in linked
        and _entry_order_key(chunk) < target_key
    ]
    if not candidates:
        return target, []

    alias = _continuity_alias_map(chunks)
    file_refs: dict[str, set[str]] = {}
    document_frequency: dict[str, int] = {}
    for chunk in chunks:
        refs = {alias.get(ref, ref) for ref in _entry_file_refs(chunk.text)}
        file_refs[chunk.entry_id or ""] = refs
        for ref in refs:
            document_frequency[ref] = document_frequency.get(ref, 0) + 1
    total_entries = len(chunks)

    def _idf(ref: str) -> float:
        occurrences = document_frequency.get(ref, 0)
        if occurrences <= 0:
            return 0.0
        return max(math.log(total_entries / occurrences), 0.0)

    query = f"{target.title}\n{target.text}".strip()
    ranked = rank_memory_chunks(
        query,
        candidates,
        top_k=len(candidates),
        recency_enabled=False,
        embedding_provider=embedding_provider,
    )
    target_files = file_refs.get(target.entry_id or "", set())
    suggestions: list[RelatedEntrySuggestion] = []
    for item in ranked:
        shared = tuple(sorted(target_files & file_refs.get(item.chunk.entry_id or "", set())))
        bonus = FILE_OVERLAP_BOOST * sum(_idf(ref) for ref in shared)
        suggestions.append(
            RelatedEntrySuggestion(
                result=item,
                shared_files=shared,
                file_overlap_bonus=bonus,
                adjusted_score=item.final_score + bonus,
            )
        )
    suggestions.sort(
        key=lambda suggestion: (
            suggestion.adjusted_score,
            suggestion.result.match_score,
            suggestion.result.lexical_score,
            -suggestion.result.age_days,
            suggestion.result.chunk.source_file,
            suggestion.result.chunk.start_line,
        ),
        reverse=True,
    )
    return target, suggestions[: max(top_k, 0)]


def rank_memory_chunks(
    query: str,
    chunks: Sequence[MemoryChunk],
    *,
    top_k: int = 8,
    today: date | None = None,
    lambda_days: float = 0.01,
    recency_enabled: bool = True,
    recency_floor: float = 0.15,
    embedding_provider: EmbeddingProvider | None = None,
    superseded_ids: set[str] | None = None,
) -> list[RankedMemoryChunk]:
    # ``superseded_ids`` is the opt-in supersession rank-dampener input
    # (freshness-aware-memory-ranking-proposal.md): the entry_ids that a later
    # decision has superseded, sourced by the caller from the (sidecar-augmented)
    # related-entry graph. When provided, a matching entry's final_score is scaled
    # by SUPERSEDED_RANK_DAMPING so a live replacement out-ranks the decision it
    # retires. DEFAULT None -> no dampening and byte-for-byte-identical ordering;
    # evolves is never in this set (evolution is freshness, not retirement).
    current_date = today or date.today()
    query_terms = _query_terms(query)
    semantic_scores = _semantic_scores(query, chunks, embedding_provider)
    effective_lambda = _effective_lambda(query, lambda_days)

    ranked: list[RankedMemoryChunk] = []
    for index, chunk in enumerate(chunks):
        lexical_score, matched_terms, matched_fields = _lexical_score(query_terms, chunk)
        semantic_score = semantic_scores[index] if semantic_scores is not None else None
        semantic_component = max(semantic_score or 0.0, 0.0) * 3.0
        match_score = lexical_score + semantic_component
        age_days = max((current_date - chunk.session_date).days, 0)
        recency_multiplier = _recency_multiplier(
            age_days,
            effective_lambda,
            recency_enabled=recency_enabled,
            recency_floor=recency_floor,
        )
        final_score = match_score * recency_multiplier
        if superseded_ids and chunk.entry_id and chunk.entry_id in superseded_ids:
            # Down-rank only, never hide: the superseded entry stays in the
            # results, just multiplicatively demoted beneath a fresher match.
            final_score *= SUPERSEDED_RANK_DAMPING
        ranked.append(
            RankedMemoryChunk(
                chunk=chunk,
                final_score=final_score,
                match_score=match_score,
                lexical_score=lexical_score,
                semantic_score=semantic_score,
                recency_multiplier=recency_multiplier,
                age_days=age_days,
                matched_terms=tuple(sorted(matched_terms)),
                matched_fields=tuple(sorted(matched_fields)),
            )
        )

    ranked.sort(
        key=lambda result: (
            result.final_score,
            result.match_score,
            result.lexical_score,
            -result.age_days,
            result.chunk.source_file,
            result.chunk.start_line,
        ),
        reverse=True,
    )
    return ranked[: max(top_k, 0)]


def _extract_chunks_from_file(
    target_root: Path,
    doc: SessionDocument,
    session_date: date,
    *,
    granularity: str,
) -> list[MemoryChunk]:
    path = doc.path
    lines = path.read_text(encoding="utf-8").splitlines()
    file_metadata = _extract_file_frontmatter(lines)
    file_hash_id = file_metadata.get("hash_id")
    file_user = doc.user
    entries = _find_entry_ranges(lines)
    if entries:
        return _extract_entry_chunks_from_file(
            target_root,
            path,
            session_date,
            lines,
            entries,
            granularity,
            user=file_user,
            file_hash_id=file_hash_id,
        )
    return _extract_legacy_chunks_from_file(
        target_root,
        path,
        session_date,
        lines,
        user=file_user,
        file_hash_id=file_hash_id,
    )


def _find_entry_ranges(lines: Sequence[str]) -> list[tuple[int, int, str]]:
    entries: list[tuple[int, int, str]] = []
    starts: list[tuple[int, str]] = []
    for lineno, line in enumerate(lines, start=1):
        heading = HEADING_RE.match(line)
        if heading and len(heading.group(1)) == 2:
            starts.append((lineno, heading.group(2).strip()))

    for index, (start, title) in enumerate(starts):
        end = starts[index + 1][0] - 1 if index + 1 < len(starts) else len(lines)
        entries.append((start, end, title))
    return entries


def _extract_entry_chunks_from_file(
    target_root: Path,
    path: Path,
    session_date: date,
    lines: Sequence[str],
    entries: Sequence[tuple[int, int, str]],
    granularity: str,
    *,
    user: str | None,
    file_hash_id: str | None,
) -> list[MemoryChunk]:
    chunks: list[MemoryChunk] = []
    source_path = path.relative_to(target_root).as_posix()
    for start_line, end_line, title in entries:
        entry_lines = list(lines[start_line:end_line])
        metadata = _extract_entry_metadata(entry_lines)
        entry_id = _metadata_value(metadata, "entry_id")
        related_entries = _metadata_list(metadata, "related_entries")
        supersedes = _metadata_list(metadata, "supersedes")
        evolves = _metadata_list(metadata, "evolves")
        commits = _metadata_list(metadata, "commits")
        continuity = _extract_entry_continuity(entry_lines)
        entry_topics = _metadata_list(metadata, "topics")
        sections = _entry_sections(entry_lines)
        heading_path = (title,)
        entry_range = (start_line, end_line)

        if granularity == "entry":
            text = "\n".join(entry_lines).strip()
            payload = "\n".join((title, text)).strip()
            chunk_id = entry_id or _chunk_id(source_path, start_line, heading_path, payload)
            chunks.append(
                MemoryChunk(
                    chunk_id=chunk_id,
                    source_path=source_path,
                    source_file=path.name,
                    session_date=session_date,
                    entry_datetime=_entry_datetime(title),
                    heading_path=heading_path,
                    heading_level=2,
                    title=title,
                    text=text,
                    tags=_extract_tags(entry_lines),
                    contexts=_extract_contexts(heading_path),
                    lexical_terms=_extract_lexical_terms(payload),
                    start_line=start_line,
                    end_line=end_line,
                    entry_id=entry_id,
                    user_initials=_metadata_value(metadata, "user_initials"),
                    agent_type=_metadata_value(metadata, "agent_type"),
                    agent_name=_metadata_value(metadata, "agent_name"),
                    project_path=_metadata_value(metadata, "project_path"),
                    subproject_path=_metadata_value(metadata, "subproject_path"),
                    user=user,
                    file_hash_id=file_hash_id,
                    related_entries=related_entries,
                    supersedes=supersedes,
                    evolves=evolves,
                    commits=commits,
                    continuity=continuity,
                    topics=entry_topics,
                    branch=_metadata_value(metadata, "branch"),
                    entry_title=title,
                    entry_line_range=entry_range,
                    sections=sections,
                    granularity="entry",
                )
            )
            continue

        section_ranges = _find_section_ranges(entry_lines, start_line)
        if not section_ranges:
            text = "\n".join(entry_lines).strip()
            payload = "\n".join((title, text)).strip()
            chunk_id = entry_id or _chunk_id(source_path, start_line, heading_path, payload)
            chunks.append(
                MemoryChunk(
                    chunk_id=chunk_id,
                    source_path=source_path,
                    source_file=path.name,
                    session_date=session_date,
                    entry_datetime=_entry_datetime(title),
                    heading_path=heading_path,
                    heading_level=2,
                    title=title,
                    text=text,
                    tags=_extract_tags(entry_lines),
                    contexts=_extract_contexts(heading_path),
                    lexical_terms=_extract_lexical_terms(payload),
                    start_line=start_line,
                    end_line=end_line,
                    entry_id=entry_id,
                    user_initials=_metadata_value(metadata, "user_initials"),
                    agent_type=_metadata_value(metadata, "agent_type"),
                    agent_name=_metadata_value(metadata, "agent_name"),
                    project_path=_metadata_value(metadata, "project_path"),
                    subproject_path=_metadata_value(metadata, "subproject_path"),
                    user=user,
                    file_hash_id=file_hash_id,
                    related_entries=related_entries,
                    supersedes=supersedes,
                    evolves=evolves,
                    commits=commits,
                    continuity=continuity,
                    topics=entry_topics,
                    branch=_metadata_value(metadata, "branch"),
                    entry_title=title,
                    entry_line_range=entry_range,
                    sections=sections,
                    granularity="section",
                )
            )
            continue

        for section_start, section_end, section_title, section_path in section_ranges:
            section_lines = list(lines[section_start:section_end])
            heading_path = (title, *section_path)
            text = "\n".join(section_lines).strip()
            payload = "\n".join((*heading_path, text)).strip()
            section_id = "/".join(_slugify(section) for section in section_path)
            chunk_id = f"{entry_id}#{section_id}" if entry_id else _chunk_id(source_path, section_start, heading_path, payload)
            chunks.append(
                MemoryChunk(
                    chunk_id=chunk_id,
                    source_path=source_path,
                    source_file=path.name,
                    session_date=session_date,
                    entry_datetime=_entry_datetime(title),
                    heading_path=heading_path,
                    heading_level=2 + len(section_path),
                    title=section_title,
                    text=text,
                    tags=_extract_tags(section_lines),
                    contexts=_extract_contexts(heading_path),
                    lexical_terms=_extract_lexical_terms(payload),
                    start_line=section_start,
                    end_line=section_end,
                    entry_id=entry_id,
                    user_initials=_metadata_value(metadata, "user_initials"),
                    agent_type=_metadata_value(metadata, "agent_type"),
                    agent_name=_metadata_value(metadata, "agent_name"),
                    project_path=_metadata_value(metadata, "project_path"),
                    subproject_path=_metadata_value(metadata, "subproject_path"),
                    user=user,
                    file_hash_id=file_hash_id,
                    related_entries=related_entries,
                    supersedes=supersedes,
                    evolves=evolves,
                    commits=commits,
                    continuity=continuity,
                    topics=entry_topics,
                    branch=_metadata_value(metadata, "branch"),
                    entry_title=title,
                    entry_line_range=entry_range,
                    sections=sections,
                    granularity="section",
                )
            )
    return chunks


def _extract_legacy_chunks_from_file(
    target_root: Path,
    path: Path,
    session_date: date,
    lines: Sequence[str],
    *,
    user: str | None = None,
    file_hash_id: str | None = None,
) -> list[MemoryChunk]:
    chunks: list[MemoryChunk] = []
    source_path = path.relative_to(target_root).as_posix()
    heading_stack: list[str] = []
    current_title: str | None = None
    current_level = 0
    current_start = 1
    current_lines: list[str] = []

    def flush(end_line: int) -> None:
        nonlocal current_title, current_level, current_start, current_lines
        if current_title is None:
            return
        text = "\n".join(current_lines).strip()
        title_path = tuple(heading for heading in heading_stack[:current_level] if heading)
        payload = "\n".join((current_title, text)).strip()
        chunks.append(
            MemoryChunk(
                chunk_id=_chunk_id(source_path, current_start, title_path, payload),
                source_path=source_path,
                source_file=path.name,
                session_date=session_date,
                entry_datetime=_entry_datetime(current_title),
                heading_path=title_path,
                heading_level=current_level,
                title=current_title,
                text=text,
                tags=_extract_tags(current_lines),
                contexts=_extract_contexts(title_path),
                lexical_terms=_extract_lexical_terms(payload),
                start_line=current_start,
                end_line=end_line,
                user=user,
                file_hash_id=file_hash_id,
            )
        )
        current_lines = []

    for lineno, line in enumerate(lines, start=1):
        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            title = heading.group(2).strip()
            flush(lineno - 1)
            if len(heading_stack) < level:
                heading_stack.extend([""] * (level - len(heading_stack)))
            heading_stack[level - 1] = title
            del heading_stack[level:]
            current_title = title
            current_level = level
            current_start = lineno
            current_lines = []
            continue

        if current_title is None and line.strip():
            current_title = "(preamble)"
            current_level = 1
            heading_stack = [current_title]
            current_start = lineno
        if current_title is not None:
            current_lines.append(line)

    flush(len(lines))
    return chunks


def _extract_file_frontmatter(lines: Sequence[str]) -> dict[str, str]:
    if not lines or lines[0].strip() != "---":
        return {}
    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line or line[:1] in (" ", "\t", "-"):
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and value:
            metadata[key] = value
    return metadata


def _entry_yaml_lines(entry_lines: Sequence[str]) -> list[str]:
    """The raw lines of the entry's leading fenced ```yaml block, or []."""
    index = 0
    while index < len(entry_lines) and not entry_lines[index].strip():
        index += 1
    if index >= len(entry_lines) or entry_lines[index].strip() not in ("```yaml", "```yml"):
        return []
    yaml_lines: list[str] = []
    for line in entry_lines[index + 1 :]:
        if line.strip() == "```":
            break
        yaml_lines.append(line)
    return yaml_lines


def _extract_entry_continuity(entry_lines: Sequence[str]) -> tuple[ContinuityBlock, ...]:
    """Parse stored ``continuity:`` items (kind/from/to mappings) from the
    entry's yaml block. Items are kept as parsed, malformed or not - ``links
    check`` owns validation; the alias map filters to well-formed
    rename/migration items itself."""
    yaml_lines = _entry_yaml_lines(entry_lines)
    region: list[str] = []
    collecting = False
    for line in yaml_lines:
        if collecting:
            if line[:1] in (" ", "\t"):
                region.append(line)
                continue
            break
        if line.strip() == "continuity:":
            collecting = True
    if not region:
        return ()
    return tuple(
        ContinuityBlock(
            kind=item.get("kind", ""),
            from_ref=item.get("from", ""),
            to_ref=item.get("to") or None,
        )
        for item in _parse_continuity_items("\n".join(region))
    )


def _extract_entry_metadata(entry_lines: Sequence[str]) -> dict[str, str | tuple[str, ...]]:
    yaml_lines = _entry_yaml_lines(entry_lines)
    if not yaml_lines:
        return {}
    metadata: dict[str, str | tuple[str, ...]] = {}

    line_index = 0
    while line_index < len(yaml_lines):
        line = yaml_lines[line_index]
        if ":" not in line or line[:1] in (" ", "\t", "-"):
            line_index += 1
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if not key:
            line_index += 1
            continue
        if not value:
            items: list[str] = []
            probe = line_index + 1
            while probe < len(yaml_lines) and yaml_lines[probe][:1] in (" ", "\t"):
                stripped = yaml_lines[probe].strip()
                if stripped.startswith("- "):
                    items.append(stripped[2:].strip().strip("\"'"))
                probe += 1
            if items:
                metadata[key] = tuple(items)
            line_index = probe
            continue
        if value == "null":
            value = ""
        metadata[key] = value
        line_index += 1
    return metadata


def _metadata_value(metadata: dict[str, str | tuple[str, ...]], key: str) -> str | None:
    value = metadata.get(key)
    if isinstance(value, tuple):
        return None
    return value or None


def _metadata_list(metadata: dict[str, str | tuple[str, ...]], key: str) -> tuple[str, ...]:
    value = metadata.get(key)
    if isinstance(value, tuple):
        return value
    if isinstance(value, str) and value:
        return (value,)
    return ()


def _entry_sections(entry_lines: Sequence[str]) -> tuple[str, ...]:
    sections: list[str] = []
    for line in entry_lines:
        heading = HEADING_RE.match(line)
        if heading and len(heading.group(1)) >= 3:
            sections.append(heading.group(2).strip())
    return tuple(sections)


def _find_section_ranges(
    entry_lines: Sequence[str],
    entry_start_line: int,
) -> list[tuple[int, int, str, tuple[str, ...]]]:
    headings: list[tuple[int, int, str, tuple[str, ...]]] = []
    stack: list[str] = []
    for offset, line in enumerate(entry_lines, start=entry_start_line + 1):
        heading = HEADING_RE.match(line)
        if not heading:
            continue
        level = len(heading.group(1))
        if level < 3:
            continue
        title = heading.group(2).strip()
        stack_index = level - 3
        if len(stack) <= stack_index:
            stack.extend([""] * (stack_index + 1 - len(stack)))
        stack[stack_index] = title
        del stack[stack_index + 1 :]
        headings.append((offset, level, title, tuple(value for value in stack if value)))

    ranges: list[tuple[int, int, str, tuple[str, ...]]] = []
    for index, (start, _level, title, section_path) in enumerate(headings):
        end = headings[index + 1][0] - 1 if index + 1 < len(headings) else entry_start_line + len(entry_lines)
        ranges.append((start, end, title, section_path))
    return ranges


def _extract_tags(lines: Sequence[str]) -> tuple[str, ...]:
    tags: set[str] = set()
    for line in lines:
        if HEADING_RE.match(line):
            continue
        for match in TAG_RE.finditer(line):
            tags.add(match.group(1).lower())
    return tuple(sorted(tags))


def _entry_datetime(title: str) -> datetime | None:
    match = ENTRY_DATETIME_RE.match(title)
    if not match:
        return None
    try:
        return datetime.strptime(" ".join(match.groups()), "%Y-%m-%d %H:%M")
    except ValueError:
        return None


def _extract_contexts(heading_path: Sequence[str]) -> tuple[str, ...]:
    contexts: list[str] = []
    for heading in heading_path:
        if heading.lower().startswith("context:"):
            value = heading.split(":", 1)[1].strip()
            if value:
                contexts.append(value)
    return tuple(contexts)


def _extract_lexical_terms(text: str) -> tuple[str, ...]:
    terms: set[str] = set()
    for match in IDENTIFIER_RE.finditer(text):
        value = match.group(1).strip("`,:;()[]{}").rstrip(".,")
        if not value or value.startswith("#"):
            continue
        if _is_notable_identifier(value):
            terms.add(value)
    return tuple(sorted(terms, key=str.lower))


def _is_notable_identifier(value: str) -> bool:
    return (
        "_" in value
        or "-" in value
        or "/" in value
        or "." in value
        or value.startswith(".")
    )


def _query_terms(query: str) -> tuple[str, ...]:
    terms: set[str] = set()
    for tag in TAG_RE.findall(query):
        terms.add(tag.lower())
    for identifier in _extract_lexical_terms(query):
        terms.add(identifier.lower())
    for word in re.findall(r"[A-Za-z0-9]+", query.lower()):
        if len(word) > 1:
            terms.add(word)
    normalized = _normalize(query)
    if normalized:
        terms.add(normalized)
    return tuple(sorted(terms))


def _lexical_score(
    query_terms: Sequence[str],
    chunk: MemoryChunk,
) -> tuple[float, set[str], set[str]]:
    score = 0.0
    matched_terms: set[str] = set()
    matched_fields: set[str] = set()
    field_values = {
        "tags": chunk.tags,
        "contexts": chunk.contexts,
        "heading_path": chunk.heading_path,
        "lexical_terms": chunk.lexical_terms,
    }
    weights = {
        "tags": 12.0,
        "contexts": 8.0,
        "heading_path": 6.0,
        "lexical_terms": 4.0,
    }

    for field, values in field_values.items():
        for term in query_terms:
            if any(_term_matches_value(term, value) for value in values):
                score += weights[field]
                matched_terms.add(term)
                matched_fields.add(field)

    normalized_text = _normalize(chunk.text)
    for term in query_terms:
        if term and term in normalized_text:
            score += 1.0
            matched_terms.add(term)
            matched_fields.add("text")

    return score, matched_terms, matched_fields


def _term_matches_value(term: str, value: str) -> bool:
    normalized_term = _normalize(term)
    normalized_value = _normalize(value)
    return normalized_term == normalized_value or normalized_term in normalized_value


def _semantic_scores(
    query: str,
    chunks: Sequence[MemoryChunk],
    embedding_provider: EmbeddingProvider | None,
) -> list[float] | None:
    if embedding_provider is None or not chunks:
        return None
    try:
        vectors = embedding_provider.embed([query, *(chunk.text for chunk in chunks)])
    except Exception:
        return None
    if len(vectors) != len(chunks) + 1:
        return None
    query_vector = vectors[0]
    return [_cosine_similarity(query_vector, vector) for vector in vectors[1:]]


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def _effective_lambda(query: str, lambda_days: float) -> float:
    normalized_query = _normalize(query)
    if any(term in normalized_query for term in STRUCTURAL_QUERY_TERMS):
        return lambda_days / 2.0
    return lambda_days


def _recency_multiplier(
    age_days: int,
    lambda_days: float,
    *,
    recency_enabled: bool,
    recency_floor: float,
) -> float:
    if not recency_enabled:
        return 1.0
    floor = min(max(recency_floor, 0.0), 1.0)
    return max(floor, math.exp(-lambda_days * age_days))


def _chunk_id(
    source_file: str,
    start_line: int,
    heading_path: Sequence[str],
    payload: str,
) -> str:
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:10]
    path_slug = "/".join(_normalize(heading) for heading in heading_path)
    return f"{source_file}:{start_line}:{path_slug}:{digest}"


def _slugify(value: str) -> str:
    normalized = "-".join(re.findall(r"[a-z0-9]+", value.lower()))
    return normalized or "section"


def _normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))

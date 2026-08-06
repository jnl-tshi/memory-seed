from __future__ import annotations

import hashlib
import math
from collections import Counter
import re
from dataclasses import dataclass, replace
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
ENTRY_TITLE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}\s+-\s+")

# Multiplier applied to a replaced entry's importance_score (the harmony
# contract from supersession-edges-plan.md). A replaced decision drops to a
# quarter of its raw citation weight - strong enough that a well-cited but
# retired decision ranks below a live, moderately-cited one, without erasing it
# (never hide, only deprioritize). Tunable; affects only the read-only
# importance_score signal, never default memory_search ranking.
REPLACED_IMPORTANCE_DAMPING = 0.25

# Multiplier folded into final_score for a replaced entry when the caller opts
# into supersession-aware ranking (freshness-aware-memory-ranking-proposal.md).
# Mirrors the REPLACED_IMPORTANCE_DAMPING harmony constant so a replaced
# decision sinks beneath its live replacement in the default order - but it is
# DEFAULT-OFF: rank_memory_chunks only applies it when passed the replaced id
# set (gated by rank_session_memory / search_memory's supersession_damping flag).
# It composes multiplicatively with recency_multiplier and never hard-excludes
# (that stays exclude_replaced): a replaced entry is down-ranked, not hidden.
# Strengthened 0.25 -> 0.10 so supersession does its own job. With recency neutralised, the
# replacement out-ranked the entry it retired in 21 of 23 cases at 0.25 and 22 of 23 at 0.10 -
# recovering the single case a global recency penalty had been covering, at no measured recall
# cost (paraphrase@8 unchanged at 115/180 across the sweep).
REPLACED_RANK_DAMPING = 0.10

# Fractional multiplier applied to a live terminal replacement when the caller
# opts into the bounded successor boost. One strongest-matching replaced
# lineage can lift its terminal replacement by 75%. The boost is never a hard
# injection: only already-matching terminal replacements are eligible, only the
# strongest replaced lineage(s) for the query may contribute, and the caller
# must explicitly turn it on.
REPLACING_SUCCESSOR_BOOST = 0.75

# Scale applied to the rarity-weighted F:-file-overlap sum when re-ranking
# link-suggest candidates (evolution-edges-plan.md D5). Overlap is a precision
# boost layered on the similarity ranking, never a gate: entries without F:
# paths get a zero bonus and no penalty, and hub files shared by most entries
# contribute ~nothing via the idf weighting.
FILE_OVERLAP_BOOST = 0.75

# Scale for the opt-in attention boost (attention-retrieval-signal-proposal.md):
# final_score *= 1 + ATTENTION_RANK_BOOST * log1p(decayed_fetch_score). Log-
# scaled to blunt rich-get-richer; DEFAULT-OFF - rank_memory_chunks only applies
# it when handed an attention_scores map (gated by the attention_boost flag),
# and the default flip is gated behind `memory-seed ranking-ab --signal
# attention` on real accumulated usage. The shape is provisional until that gate.
ATTENTION_RANK_BOOST = 0.5

# Weight on model2vec cosine when blending semantic similarity into the lexical
# match score. Cosine is bounded to [0,1]; the lexical score is not - one tag
# term match alone is 12.0 - so this weight is what decides whether semantic
# similarity can reorder anything at all. `retrieval.SEMANTIC_OVERLAP_BOOST`
# solves the same scale mismatch for link suggestion and sits at 160.0, with the
# note that the two components are "on different scales, not different
# importances". This value was never fitted; see the blend function below.
# Switch between the BM25F lexical scorer (rarity + term frequency + length normalisation,
# defined further down) and the original binary-per-field one. Default OFF until the paired
# measurement on the frozen corpus says otherwise: shipping an unvalidated constant is how
# every ranking number this session had to fix came to exist.
BM25F_ENABLED = True

SEMANTIC_BLEND_WEIGHT = 15.0

# Floor on the recency multiplier: max(floor, exp(-lambda * age_days)). At 0.98 recency can only
# reorder near-ties, which is what it is FOR - preferring the current form of a decision is the
# lifecycle graph's job, done precisely by replaces/evolves edges, not a global decay applied to
# every result. Measured on 180 paired paraphrase queries, moving off 0.15 gains 9 answers into the
# top 8 (p=0.052 alone) and costs nothing on the lifecycle guard once REPLACED_RANK_DAMPING is
# strengthened. It also bounds the penalty permanently: at 0.15 the spread is 2.2x on an 80-day-old
# corpus and reaches 6.7x past ~190 days, so the old default got worse as the archive aged - exactly
# backwards for a decision store.
RECENCY_FLOOR = 0.98


def blend_match_score(
    lexical_score: float,
    semantic_score: float | None,
    query_term_count: int,
) -> float:
    """Combine the lexical and semantic components into one match score.

    Extracted so the blend is a single named place rather than an expression buried in the ranking
    loop, and so an experiment can substitute a different shape without reimplementing ranking
    (which is how a harness ends up measuring something production does not do).

    ``query_term_count`` is unused by the current additive form and is passed because it is the
    axis the additive form is suspected to get wrong: lexical accumulates over matched terms and
    fields while cosine is a single bounded number, so one constant cannot be right for a 3-term
    and a 20-term query.
    """
    return lexical_score + SEMANTIC_BLEND_WEIGHT * max(semantic_score or 0.0, 0.0)


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
    project_path: str | None = None
    subproject_path: str | None = None
    user: str | None = None
    file_hash_id: str | None = None
    related_entries: tuple[str, ...] = ()
    replaces: tuple[str, ...] = ()
    # Typed lifecycle edge: earlier decisions this entry extends/refines while
    # they stay valid (evolves), vs. replaces which retires its targets.
    evolves: tuple[str, ...] = ()
    # Decision-level lifecycle refs authored in the entry's own YAML
    # (`d1 -> mse_x:d2,d4` items in `replaces:`/`evolves:` lists - write-time
    # grammar per JNL's 2026-07-24 direction). (kind, source_ordinal,
    # target_entry_id, target_ordinal) tuples, kind in {"replaces",
    # "evolves"}; either ordinal is "" when unspecified (never both).
    # Deliberately NOT folded into the entry-level lists above: "d1 of B
    # replaces d2 of A" does not license "B replaces A" (the ratified
    # decision-refs contract), so consumers that do not model decisions keep
    # seeing the same edge set as before.
    decision_edges: tuple[tuple[str, str, str, str], ...] = ()
    commits: tuple[str, ...] = ()
    # Stored artifact-lineage blocks (rename/migration/removal); see
    # ContinuityBlock. A label family like ``branch:``, not an entry edge.
    continuity: tuple[ContinuityBlock, ...] = ()
    # Authored controlled-vocabulary membership (1-3 slugs from
    # .memory-seed/topics.yaml). Distinct from hashtag-derived ``tags`` and
    # heading-derived ``contexts``, which remain the display fallback.
    topics: tuple[str, ...] = ()
    # Sidecar-inferred topics, deliberately a DISTINCT channel from authored
    # ``topics`` above rather than merged into it: provenance is not a detail a
    # consumer may lose (invariant #3, and the Trace inspector already shows
    # Authority and Provenance as separate rows). Each consumer decides for
    # itself whether to union the two - the search filter and link-audit
    # candidate generation do; payload dicts and topic inspect keep them apart.
    # Rolled up to entry level: a decision-keyed slug also appears here, because
    # every existing consumer is entry-level and would otherwise read a fully
    # tagged entry as topicless.
    inferred_topics: tuple[str, ...] = ()
    # The (decision ordinal, slug) attribution behind ``inferred_topics``, with
    # "" as the ordinal for a bare entry-level slug. Kept so a decision-node
    # graph can colour per decision instead of painting an entry's decisions
    # identically - the reason decision keying exists at all.
    inferred_decision_topics: tuple[tuple[str, str], ...] = ()
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


def extract_memory_chunks(
    cwd: str | Path = ".",
    *,
    granularity: str = "entry",
    paths: Sequence[str | Path] | None = None,
) -> list[MemoryChunk]:
    """Extract chunks from the session tree.

    ``paths`` optionally restricts extraction to specific session documents
    (matched by resolved absolute path), so an incremental consumer can
    reparse exactly the files that changed instead of the whole corpus. None
    (the default) keeps the historical parse-everything behavior.
    """
    if granularity not in ("entry", "section", "decision"):
        raise ValueError("granularity must be 'entry', 'decision' or 'section'")
    runtime = resolve_runtime(cwd)
    target_root = runtime.workspace_root
    sessions_dir = runtime.memory_dir / "sessions"
    if not sessions_dir.is_dir():
        return []

    wanted: set[Path] | None = None
    if paths is not None:
        wanted = {Path(path).resolve() for path in paths}

    chunks: list[MemoryChunk] = []
    for doc in iter_session_documents(sessions_dir):
        if wanted is not None and doc.path.resolve() not in wanted:
            continue
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
    recency_floor: float = RECENCY_FLOOR,
    embedding_provider: EmbeddingProvider | None = None,
    granularity: str = "decision",
    user: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    exclude_replaced: bool = False,
    supersession_damping: bool = False,
    replacing_successor_boost: bool = False,
    attention_boost: bool = False,
    chunks: Sequence[MemoryChunk] | None = None,
    topics: set[str] | None = None,
) -> list[RankedMemoryChunk]:
    # Pass ``chunks`` to reuse an already-extracted corpus (matching
    # ``granularity``) and keep the search path free of re-parsing.
    # ``topics`` is a pre-expanded slug match set (canonical + aliases; see
    # topics.expand_topic_filter) - a pre-ranking gate like user/date filters.
    corpus = list(chunks) if chunks is not None else extract_memory_chunks(cwd, granularity=granularity)
    chunks = _filter_chunks(corpus, user=user, date_from=date_from, date_to=date_to, topics=topics)
    # The replaced id set feeds both the opt-in hard filter (exclude_replaced)
    # and the opt-in rank-dampener (supersession_damping); build it once over the
    # pre-filter corpus so a replacing entry outside the user/date window still
    # counts. When ``corpus`` is the sidecar-augmented set passed by search_memory,
    # sidecar-authored supersessions are included. Being evolved never lands here -
    # evolution is freshness, not retirement.
    graph: dict[str, RelatedEntryNode] | None = None
    replaced_ids: set[str] = set()
    if exclude_replaced or supersession_damping or replacing_successor_boost:
        graph = build_related_entry_graph(cwd, chunks=corpus)
        replaced_ids = {
            node.entry_id
            for node in graph.values()
            if node.replaced_by
        }
    if exclude_replaced:
        # Opt-in narrowing (like date_from/date_to): drop entries that have been
        # replaced by a later decision. Never a default and never a hard
        # exclusion unless the caller asks - replaced entries remain fully
        # retrievable by default (deprioritized via the dampener/importance_score,
        # not hidden).
        chunks = [chunk for chunk in chunks if chunk.entry_id not in replaced_ids]
    replacing_heads_by_id: dict[str, tuple[str, ...]] | None = None
    if supersession_damping and replacing_successor_boost and graph is not None:
        replacing_heads_by_id = {
            entry_id: heads
            for entry_id in replaced_ids
            if (heads := replacing_lineage_heads(graph, entry_id))
        }
    attention: dict[str, float] | None = None
    if attention_boost:
        # DEFAULT-OFF like the dampener: attention data is loaded and applied
        # only when the caller opts in, so default ordering stays byte-for-byte
        # identical. I/O stays here (this function already owns cwd); the pure
        # ranking loop below only ever sees a plain dict.
        from .attention import attention_scores as _attention_scores

        attention = _attention_scores(resolve_runtime(cwd).memory_dir)
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
        replaced_ids=replaced_ids if supersession_damping else None,
        replacing_heads_by_id=replacing_heads_by_id,
        attention_scores=attention,
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
        # Authored UNION inferred: a filter for `graph` that missed entries whose
        # graph-ness is known only from a topic sidecar would defeat the point of
        # attributing topics after the fact. Filtering is a reachability
        # question, not a provenance claim - the two channels stay separable on
        # the chunk and in every payload, so a caller can still tell which is
        # which after the filter has run.
        if topics is not None and not (topics & (set(chunk.topics) | set(chunk.inferred_topics))):
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

    ``replaces`` is the entry's stored typed edge marking earlier decisions it
    replaces; ``replaced_by`` is its computed inverse, built the same way as
    ``inbound``. The two edge kinds are never merged: a supersession is a status
    signal (this decision is retired), not a relatedness signal.

    ``evolves`` is the entry's stored typed edge marking earlier decisions it
    extends or refines *while they remain valid*; ``evolved_by`` is its
    computed, read-time-only inverse (never stored in any file - append-only is
    preserved because the inverse exists only in this derived layer). Being
    evolved is a freshness signal, not a retirement: it never dampens
    ``importance_score`` and never feeds ``exclude_replaced``.

    ``importance_score`` is the read-only ranking precursor: the inbound
    ``related_entries`` count (``len(inbound)``), dampened by
    ``REPLACED_IMPORTANCE_DAMPING`` when the entry has any ``replaced_by``
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
    replaces: tuple[str, ...] = ()
    replaced_by: tuple[str, ...] = ()
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
    replaced_by: dict[str, list[str]] = {entry_id: [] for entry_id in by_id}
    evolved_by: dict[str, list[str]] = {entry_id: [] for entry_id in by_id}
    for chunk in chunks:
        if not chunk.entry_id:
            continue
        for ref in chunk.related_entries:
            if ref in by_id and ref != chunk.entry_id:
                inbound[ref].append(chunk.entry_id)
        for ref in chunk.replaces:
            if ref in by_id and ref != chunk.entry_id:
                replaced_by[ref].append(chunk.entry_id)
        for ref in chunk.evolves:
            if ref in by_id and ref != chunk.entry_id:
                evolved_by[ref].append(chunk.entry_id)

    graph: dict[str, RelatedEntryNode] = {}
    for entry_id, chunk in by_id.items():
        inbound_ids = tuple(dict.fromkeys(inbound[entry_id]))
        replaced_by_ids = tuple(dict.fromkeys(replaced_by[entry_id]))
        evolved_by_ids = tuple(dict.fromkeys(evolved_by[entry_id]))
        importance = float(len(inbound_ids))
        if replaced_by_ids:
            # evolved_by deliberately does not dampen: an evolved decision is
            # still live, just incomplete without its evolutions.
            importance *= REPLACED_IMPORTANCE_DAMPING
        graph[entry_id] = RelatedEntryNode(
            entry_id=entry_id,
            title=chunk.title,
            source_path=chunk.source_path,
            session_date=chunk.session_date,
            outbound=tuple(chunk.related_entries),
            inbound=inbound_ids,
            replaces=tuple(chunk.replaces),
            replaced_by=replaced_by_ids,
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


def replacing_lineage_heads(
    graph: dict[str, RelatedEntryNode], entry_id: str
) -> tuple[str, ...]:
    """Follow the ``replaced_by`` chain from ``entry_id`` to its terminal
    live replacement(s).

    Symmetric with ``evolves_lineage_heads``: the graph already exposes the
    computed inverse of ``replaces`` as ``replaced_by``. This helper makes
    the current replacement reachable without changing ordering. Returns the
    terminal successors only (excluding ``entry_id`` itself), empty when the
    entry is not replaced. A ``seen`` set guards against malformed cycles.
    """
    node = graph.get(entry_id)
    if node is None or not node.replaced_by:
        return ()
    heads: set[str] = set()
    seen: set[str] = {entry_id}
    stack = list(node.replaced_by)
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        successor = graph.get(current)
        if successor is None or not successor.replaced_by:
            heads.add(current)
        else:
            stack.extend(successor.replaced_by)
    return tuple(sorted(heads))


@dataclass(frozen=True)
class RelatedEntrySuggestion:
    """One link-suggest candidate: similarity ranking plus D5 file-overlap
    evidence. ``shared_files`` names the (alias-canonicalized) F: paths the
    candidate shares with the target - shown so the agent's
    evolves/replaces/related judgment is concrete. ``consulted`` marks a
    candidate the caller retrieved while grounding the work (the memory axis of
    candidacy, complementary to structural file overlap); consulted candidates
    sort first because "I actually used this entry" is a stronger link signal
    than "it touched the same file" - especially for the decision-lineage edges
    (``replaces``/``evolves``) that file overlap is worst at surfacing.
    ``chunk``/``final_score`` pass-throughs keep older consumers of the plain
    ranked shape working."""

    result: RankedMemoryChunk
    shared_files: tuple[str, ...] = ()
    file_overlap_bonus: float = 0.0
    adjusted_score: float = 0.0
    consulted: bool = False

    @property
    def chunk(self) -> MemoryChunk:
        return self.result.chunk

    @property
    def final_score(self) -> float:
        return self.adjusted_score


_BACKTICK_TOKEN_RE = re.compile(r"`([^`\n]+)`")
# Decision-ref item in a replaces/evolves list (write-time grammar,
# 2026-07-24): optional `dM -> ` arrow prefix naming the authoring decision,
# then `<entry_id>:dN[,dN...]` with comma-separated target ordinals. Mirrors
# core's _DECISION_REF_RE / _SOURCE_DECISION_PREFIX_RE without importing core
# (dependency direction: core imports this module).
_DECISION_REF_ITEM_RE = re.compile(
    r"^(?:(d\d+)\s*->\s*)?(ms-[0-9a-f]{8}|mse_[0-9a-z]{8,32}):\s*(d\d+(?:\s*,\s*d\d+)*)$"
)
# Arrow-prefixed BARE ref (`d2 -> mse_x`): entry-level on its target side,
# decision-level on its source side. The target id stays in the entry-level
# list; the source attribution peels into decision_edges.
_ARROW_BARE_ITEM_RE = re.compile(r"^(d\d+)\s*->\s*(ms-[0-9a-f]{8}|mse_[0-9a-z]{8,32})$")


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


@dataclass(frozen=True)
class RelatedEntryAddResult:
    """Outcome of ``add_related_entry``. ``added`` is False when the edge was
    already present (the idempotent no-op path)."""

    source: MemoryChunk
    target: MemoryChunk
    added: bool
    path: Path


def add_related_entry(
    cwd: str | Path = ".",
    *,
    target_entry_id: str,
    from_entry_id: str | None = None,
) -> RelatedEntryAddResult:
    """Add one ``related_entries`` edge to the current/newest entry.

    The append-only-safe half of Related-entries P2. The default (and only
    permitted) source is the **newest** entry - "link the entry I just wrote to
    the prior one it builds on". That entry is still being authored, so adding
    to its YAML does not rewrite history and stays clean under Constitution
    Invariant #2.

    Editing an *older* entry is refused: that is historical curation, and
    Invariant #2 ("the past is append-only - extend and replace, never
    rewrite") forbids it. The plan's `link backfill` half therefore needs an
    explicit constitutional ruling before it can exist; this writer will not
    silently become it.

    Forward-only by construction, matching ``suggest_related_entries`` and the
    graph-edge contract: the target must be older than the source, so an edge
    can never point forward in time or create a cycle. Idempotent - re-adding an
    existing edge rewrites nothing and reports ``added=False``. Only the entry's
    YAML metadata is touched; prose is never modified.
    """
    from .text_files import read_text_file, write_text_file

    root = Path(cwd).resolve()
    chunks = [chunk for chunk in extract_memory_chunks(root, granularity="entry") if chunk.entry_id]
    if not chunks:
        raise LookupError("no session entries with an entry_id were found")

    newest = max(chunks, key=_entry_order_key)
    if from_entry_id is None:
        source = newest
    else:
        source = next((chunk for chunk in chunks if chunk.entry_id == from_entry_id), None)
        if source is None:
            raise LookupError(f"entry_id {from_entry_id} not found")
        if source.entry_id != newest.entry_id:
            raise ValueError(
                f"refusing to edit {source.entry_id}: it is not the newest entry "
                f"({newest.entry_id}). Editing an older entry is historical curation. "
                "Constitution Invariant #2 permits that only as a one-off, per-edge-approved "
                "human procedure - never as a standing command, which is what this is. Record "
                "the link in a new entry instead, or follow the curation procedure in "
                "docs/2_Todo/related-entries-p2-mutation-plan.md."
            )

    target = next((chunk for chunk in chunks if chunk.entry_id == target_entry_id), None)
    if target is None:
        raise LookupError(f"entry_id {target_entry_id} not found")
    if target.entry_id == source.entry_id:
        raise ValueError(f"refusing to self-link {source.entry_id}")
    if _entry_order_key(target) >= _entry_order_key(source):
        raise ValueError(
            f"refusing to link {source.entry_id} to {target.entry_id}: edges are forward-only, "
            "so the target must be older than the source"
        )

    path = root / source.source_path
    if target.entry_id in source.related_entries:
        return RelatedEntryAddResult(source=source, target=target, added=False, path=path)

    text = read_text_file(path)
    # read_text_file reads with universal newlines and write_text_file re-emits
    # the canonical LF, so line endings are normalized either way - don't try to
    # preserve them here.
    lines = text.split("\n")
    # ``start_line`` is the entry heading's 1-based line number, so slicing the
    # 0-based ``lines`` at it yields the entry body *after* the heading - the
    # same convention ``_find_entry_ranges``/``_extract_entry_metadata`` use.
    body_start = source.start_line
    entry_lines = lines[body_start : source.end_line]
    fence_offset = next(
        (i for i, line in enumerate(entry_lines) if line.strip() in ("```yaml", "```yml")),
        None,
    )
    if fence_offset is None:
        raise ValueError(f"entry {source.entry_id} has no fenced yaml metadata block to edit")
    # Bound the search for the closing fence to this entry. Scanning ``lines``
    # instead would run past EOF on an unterminated block, and could swallow a
    # later entry's fence and splice metadata into someone else's prose.
    close_offset = next(
        (
            i
            for i in range(fence_offset + 1, len(entry_lines))
            if entry_lines[i].strip() == "```"
        ),
        None,
    )
    if close_offset is None:
        raise ValueError(
            f"entry {source.entry_id} has an unterminated yaml metadata block; "
            "refusing to edit it"
        )
    yaml_start = body_start + fence_offset + 1
    yaml_end = body_start + close_offset  # exclusive: the closing fence line

    block = list(lines[yaml_start:yaml_end])
    key_index = next(
        (i for i, line in enumerate(block) if line.strip() == "related_entries:"), None
    )
    if key_index is None:
        block.extend(["related_entries:", f"  - {target.entry_id}"])
    else:
        insert_at = key_index + 1
        while insert_at < len(block) and block[insert_at][:1] in (" ", "\t"):
            insert_at += 1
        block.insert(insert_at, f"  - {target.entry_id}")

    # split("\n")/join("\n") round-trips the trailing newline as its own final
    # element, so the file's ending is preserved without special-casing it.
    updated = lines[:yaml_start] + block + lines[yaml_end:]
    write_text_file(path, "\n".join(updated))
    return RelatedEntryAddResult(source=source, target=target, added=True, path=path)


def suggest_related_entries(
    cwd: str | Path = ".",
    *,
    entry_id: str | None = None,
    top_k: int = 5,
    consulted: Sequence[str] | None = None,
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

    ``consulted`` is the optional *memory axis* of candidacy: entry ids the
    caller retrieved while grounding the work (from the pre-work history
    lookup). Any candidate whose id is in this set is flagged ``consulted`` and
    sorts ahead of purely structural (file-overlap) candidates - "I actually
    used this entry" outranks "it touched the same file", and it is the natural
    source for the ``replaces``/``evolves`` decision-lineage edges that file
    overlap misses (a lineage parent that shares no file still surfaces here).
    This only *reorders and labels* candidates - it fabricates no relevance and
    creates no edge; the caller still classifies. An empty/omitted ``consulted``
    leaves ordering and output byte-for-byte identical to the file-only path.
    """
    consulted_ids = {cid for cid in (consulted or []) if cid}
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
                consulted=(item.chunk.entry_id or "") in consulted_ids,
            )
        )
    # Consulted-first (the memory axis outranks the structural one), then the
    # existing file-overlap-adjusted order. When ``consulted`` is empty every
    # flag is False, so this leading key is constant and ordering stays
    # byte-for-byte identical to the file-only path.
    suggestions.sort(
        key=lambda suggestion: (
            suggestion.consulted,
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
    recency_floor: float = RECENCY_FLOOR,
    embedding_provider: EmbeddingProvider | None = None,
    replaced_ids: set[str] | None = None,
    replacing_heads_by_id: dict[str, tuple[str, ...]] | None = None,
    attention_scores: dict[str, float] | None = None,
) -> list[RankedMemoryChunk]:
    # ``replaced_ids`` is the opt-in supersession rank-dampener input
    # (freshness-aware-memory-ranking-proposal.md): the entry_ids that a later
    # decision has replaced, sourced by the caller from the (sidecar-augmented)
    # related-entry graph. When provided, a matching entry's final_score is scaled
    # by REPLACED_RANK_DAMPING so a live replacement out-ranks the decision it
    # retires. DEFAULT None -> no dampening and byte-for-byte-identical ordering;
    # evolves is never in this set (evolution is freshness, not retirement).
    current_date = today or date.today()
    query_terms = _query_terms(query)
    semantic_scores = _semantic_scores(query, chunks, embedding_provider)
    effective_lambda = _effective_lambda(query, lambda_days)
    # Corpus statistics for BM25F, computed once per ranking call over exactly the chunks being
    # ranked - so a filtered or subsampled corpus gets its own rarity profile rather than inheriting
    # the whole store's.
    corpus_stats = build_corpus_stats(chunks) if BM25F_ENABLED else None

    ranked: list[RankedMemoryChunk] = []
    for index, chunk in enumerate(chunks):
        if corpus_stats is not None:
            lexical_score, matched_terms, matched_fields = _bm25f_score(
                query_terms, chunk, corpus_stats
            )
        else:
            lexical_score, matched_terms, matched_fields = _lexical_score(query_terms, chunk)
        semantic_score = semantic_scores[index] if semantic_scores is not None else None
        match_score = blend_match_score(lexical_score, semantic_score, len(query_terms))
        age_days = max((current_date - chunk.session_date).days, 0)
        recency_multiplier = _recency_multiplier(
            age_days,
            effective_lambda,
            recency_enabled=recency_enabled,
            recency_floor=recency_floor,
        )
        final_score = match_score * recency_multiplier
        if replaced_ids and chunk.entry_id and chunk.entry_id in replaced_ids:
            # Down-rank only, never hide: the replaced entry stays in the
            # results, just multiplicatively demoted beneath a fresher match.
            final_score *= REPLACED_RANK_DAMPING
        if attention_scores and chunk.entry_id:
            # Opt-in attention boost (attention-retrieval-signal-proposal.md):
            # decayed fetch frequency, log-scaled so a heavily-fetched entry is
            # lifted without runaway rich-get-richer. DEFAULT None -> byte-for-
            # byte-identical ordering; the multiplier shape is provisional until
            # the ranking-ab gate decides the default.
            attended = attention_scores.get(chunk.entry_id, 0.0)
            if attended > 0.0:
                final_score *= 1.0 + ATTENTION_RANK_BOOST * math.log1p(attended)
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

    if replacing_heads_by_id:
        ranked = _apply_replacing_successor_boost(query, ranked, replacing_heads_by_id)
    ranked.sort(key=_ranked_result_sort_key, reverse=True)
    return ranked[: max(top_k, 0)]


def _apply_replacing_successor_boost(
    query: str,
    ranked: Sequence[RankedMemoryChunk],
    replacing_heads_by_id: dict[str, tuple[str, ...]],
) -> list[RankedMemoryChunk]:
    """Apply a bounded boost to already-matching terminal replacements.

    The signal is explicit and additive to the ranking pipeline: a retired
    entry must itself positively match the query, and the terminal replacement
    must also have positive query relevance. We never hard-inject a replacement
    with zero match score, and we boost by entry id so section-granularity
    searches keep their within-entry relative order.
    """
    best_by_entry: dict[str, RankedMemoryChunk] = {}
    for result in ranked:
        entry_id = result.chunk.entry_id
        if not entry_id:
            continue
        incumbent = best_by_entry.get(entry_id)
        if incumbent is None or _ranked_result_sort_key(result) > _ranked_result_sort_key(incumbent):
            best_by_entry[entry_id] = result

    candidates: list[tuple[tuple[int, int, float, float], set[str]]] = []
    for predecessor_id, heads in replacing_heads_by_id.items():
        predecessor = best_by_entry.get(predecessor_id)
        if predecessor is None or predecessor.match_score <= 0:
            continue
        eligible_successors = {
            successor_id
            for successor_id in heads
            if (successor := best_by_entry.get(successor_id)) is not None and successor.match_score > 0
        }
        if not eligible_successors:
            continue
        candidates.append((_replacing_query_alignment(query, predecessor), set(eligible_successors)))

    if not candidates:
        return list(ranked)
    if len(candidates) == 1:
        boost_successor_ids = candidates[0][1]
    else:
        best_alignment = max(alignment for alignment, _ in candidates)
        if best_alignment[:3] == (0, 0, 0.0):
            return list(ranked)
        top = [successors for alignment, successors in candidates if alignment == best_alignment]
        if len(top) != 1:
            return list(ranked)
        boost_successor_ids = top[0]

    boosted: list[RankedMemoryChunk] = []
    for result in ranked:
        entry_id = result.chunk.entry_id or ""
        if entry_id in boost_successor_ids and result.match_score > 0:
            boosted.append(replace(result, final_score=result.final_score * (1.0 + REPLACING_SUCCESSOR_BOOST)))
        else:
            boosted.append(result)
    return boosted


def _replacing_query_alignment(query: str, predecessor: RankedMemoryChunk) -> tuple[int, int, float, float]:
    """Score how specifically a query points at a retired predecessor title.

    The successor boost is intentionally fail-closed on ambiguous queries. We
    strip the timestamp prefix from authored entry titles, then prefer a unique
    title-level alignment over broad overall relevance so unrelated retired
    lineages cannot ride shared date/generic tokens into the window.
    """
    normalized_query = _normalize(ENTRY_TITLE_PREFIX_RE.sub("", query).strip())
    stripped_title = ENTRY_TITLE_PREFIX_RE.sub("", predecessor.chunk.title).strip()
    normalized_title = _normalize(stripped_title)
    title_terms = {
        word
        for word in re.findall(r"[A-Za-z0-9]+", stripped_title.lower())
        if len(word) > 1
    }
    if not normalized_title and not title_terms:
        return (0, 0, 0.0, predecessor.match_score)
    exact_phrase_match = int(bool(normalized_title) and normalized_title in normalized_query)
    overlap_count = sum(1 for term in title_terms if term in normalized_query)
    overlap_ratio = (overlap_count / len(title_terms)) if title_terms else float(exact_phrase_match)
    return (exact_phrase_match, overlap_count, overlap_ratio, predecessor.match_score)


def _ranked_result_sort_key(result: RankedMemoryChunk) -> tuple[float, float, float, int, str, int]:
    return (
        result.final_score,
        result.match_score,
        result.lexical_score,
        -result.age_days,
        result.chunk.source_file,
        result.chunk.start_line,
    )


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
        _related_raw = _metadata_list(metadata, "related_entries")
        # `supersedes:` is the legacy spelling of `replaces:` (renamed
        # 2026-07-24, JNL's direction: one term across Seed and Trace).
        # Corpora written by <=2.19 carry the old key; read both forever,
        # write only the new one.
        _replaces_new = _metadata_list(metadata, "replaces")
        _replaces_legacy = _metadata_list(metadata, "supersedes")
        _replaces_raw = tuple(_replaces_new) + tuple(
            ref for ref in _replaces_legacy if ref not in _replaces_new
        )
        _evolves_raw = _metadata_list(metadata, "evolves")
        # `mse_x:d2` items are decision-level refs (write-time grammar,
        # 2026-07-24): they peel off into decision_edges and never join the
        # entry-level lists - the ratified no-projection rule. Anything that is
        # neither a bare id nor a decision ref stays in the entry-level list
        # verbatim, exactly as before (links check owns flagging it).
        replaces_list: list[str] = []
        evolves_list: list[str] = []
        related_list: list[str] = []
        entry_decision_edges: list[tuple[str, str, str, str]] = []
        # `related_entries` joins replaces/evolves here since 2026-07-25: a
        # `:dN` related ref peels into decision_edges exactly like a lifecycle
        # one (kind="related"), so a decision-level related edge terminates on
        # the target's decision row. Bare related refs stay entry-level. The
        # no-projection rule holds: a `:dN` related edge never rejoins the
        # entry-level related list.
        for kind, raw_refs, sink in (
            ("replaces", _replaces_raw, replaces_list),
            ("evolves", _evolves_raw, evolves_list),
            ("related", _related_raw, related_list),
        ):
            for raw in raw_refs:
                m = _DECISION_REF_ITEM_RE.match(raw)
                if m:
                    source_ordinal = m.group(1) or ""
                    for ordinal in (part.strip() for part in m.group(3).split(",")):
                        if ordinal:
                            entry_decision_edges.append((kind, source_ordinal, m.group(2), ordinal))
                    continue
                m = _ARROW_BARE_ITEM_RE.match(raw)
                if m:
                    # Entry-level edge (bare target id, arrow stripped) plus a
                    # source-attributed decision edge with no target ordinal.
                    sink.append(m.group(2))
                    entry_decision_edges.append((kind, m.group(1), m.group(2), ""))
                    continue
                sink.append(raw)
        replaces = tuple(replaces_list)
        evolves = tuple(evolves_list)
        related_entries = tuple(related_list)
        commits = _metadata_list(metadata, "commits")
        continuity = _extract_entry_continuity(entry_lines)
        entry_topics = _metadata_list(metadata, "topics")
        sections = _entry_sections(entry_lines)
        heading_path = (title,)
        entry_range = (start_line, end_line)

        # Decision granularity: one chunk per `#### Dn - ...` DRAFT block, keyed by the
        # canonical `mse_x:dN` identity that topics, lifecycle edges, ADRs and Trace already
        # speak. Entries without decision headings fall through to the entry unit below - the
        # 2026-05-26 reasoning (a decision must never be separated from its rationale) still
        # governs those, and is *preserved* here because a `#### Dn` block carries its own
        # D/R/A/F/T by construction.
        if granularity == "decision":
            decision_ranges = _find_decision_ranges(entry_lines, start_line)
            if decision_ranges:
                for d_start, d_end, d_title, ordinal in decision_ranges:
                    d_lines = list(lines[d_start:d_end])
                    d_heading_path = (title, d_title)
                    text = "\n".join(d_lines).strip()
                    payload = "\n".join((*d_heading_path, text)).strip()
                    chunk_id = (
                        f"{entry_id}:{ordinal}"
                        if entry_id
                        else _chunk_id(source_path, d_start, d_heading_path, payload)
                    )
                    chunks.append(
                        MemoryChunk(
                            chunk_id=chunk_id,
                            source_path=source_path,
                            source_file=path.name,
                            session_date=session_date,
                            entry_datetime=_entry_datetime(title),
                            heading_path=d_heading_path,
                            heading_level=4,
                            title=d_title,
                            text=text,
                            tags=_extract_tags(d_lines),
                            contexts=_extract_contexts(d_heading_path),
                            lexical_terms=_extract_lexical_terms(payload),
                            start_line=d_start,
                            end_line=d_end,
                            entry_id=entry_id,
                            user_initials=_metadata_value(metadata, "user_initials"),
                            agent_type=_metadata_value(metadata, "agent_type"),
                            project_path=_metadata_value(metadata, "project_path"),
                            subproject_path=_metadata_value(metadata, "subproject_path"),
                            user=user,
                            file_hash_id=file_hash_id,
                            related_entries=related_entries,
                            replaces=replaces,
                            evolves=evolves,
                            # Only the edges this decision authors, plus untargeted entry-level
                            # ones - so a decision row carries its own lifecycle, not its
                            # siblings'.
                            decision_edges=tuple(
                                edge
                                for edge in entry_decision_edges
                                if edge[1] in ("", ordinal)
                            ),
                            commits=commits,
                            continuity=continuity,
                            topics=_decision_topics(entry_topics, ordinal),
                            branch=_metadata_value(metadata, "branch"),
                            entry_title=title,
                            entry_line_range=entry_range,
                            sections=sections,
                            granularity="decision",
                        )
                    )
                continue

        if granularity in ("entry", "decision"):
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
                    project_path=_metadata_value(metadata, "project_path"),
                    subproject_path=_metadata_value(metadata, "subproject_path"),
                    user=user,
                    file_hash_id=file_hash_id,
                    related_entries=related_entries,
                    replaces=replaces,
                    evolves=evolves,
                    decision_edges=tuple(entry_decision_edges),
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
                    project_path=_metadata_value(metadata, "project_path"),
                    subproject_path=_metadata_value(metadata, "subproject_path"),
                    user=user,
                    file_hash_id=file_hash_id,
                    related_entries=related_entries,
                    replaces=replaces,
                    evolves=evolves,
                    decision_edges=tuple(entry_decision_edges),
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
                    project_path=_metadata_value(metadata, "project_path"),
                    subproject_path=_metadata_value(metadata, "subproject_path"),
                    user=user,
                    file_hash_id=file_hash_id,
                    related_entries=related_entries,
                    replaces=replaces,
                    evolves=evolves,
                    decision_edges=tuple(entry_decision_edges),
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


_DECISION_HEADING_RE = re.compile(r"^\s*#{4}\s+(D(\d+))\s*[-–—]\s*(.+?)\s*$")

# LEGACY. The entry format used to have two shapes for decisions: `#### Dn - title` under a
# `### Decisions` heading for two or more, and a bare singular `### Decision` for one. As of
# 2026-08-06 the numbered form is the only one authored - see session_logging.md - but 494 entries
# already use the singular form and the store is append-only, so the reader must keep seeing them.
# Matched here rather than treated as a co-equal shape: there is one concept of a decision, and this
# regex exists only to map old markdown onto it. `Decisions` plural is deliberately excluded, since
# that heading owns `#### Dn` children and must not also become a chunk.
_LEGACY_SINGLE_DECISION_RE = re.compile(r"^\s*#{3}\s+Decision\s*$", re.IGNORECASE)


def _find_decision_ranges(
    entry_lines: Sequence[str],
    entry_start_line: int,
) -> list[tuple[int, int, str, str]]:
    """Line ranges for each `#### Dn - title` DRAFT block: (start, end, title, ordinal).

    A decision block runs to the next decision heading or to the next heading at level 3 or
    shallower (so trailing entry sections after the decisions are not swallowed). Returns []
    for entries with no decision headings - those keep the whole-entry unit.
    """
    starts: list[tuple[int, str, str]] = []
    boundaries: list[int] = []
    legacy_single: tuple[int, str, str] | None = None
    for offset, line in enumerate(entry_lines, start=entry_start_line + 1):
        decision = _DECISION_HEADING_RE.match(line)
        if decision:
            ordinal = decision.group(1).lower()
            starts.append((offset, f"{decision.group(1)} - {decision.group(3)}", ordinal))
            boundaries.append(offset)
            continue
        heading = HEADING_RE.match(line)
        if heading and len(heading.group(1)) <= 3:
            boundaries.append(offset)
            if legacy_single is None and _LEGACY_SINGLE_DECISION_RE.match(line):
                # Held, not appended: an entry could in principle carry both shapes, and the
                # numbered blocks win. Only usable once the whole entry has been scanned.
                legacy_single = (offset, "D1 - Decision", "d1")

    if not starts and legacy_single is not None:
        starts.append(legacy_single)

    ranges: list[tuple[int, int, str, str]] = []
    entry_end = entry_start_line + len(entry_lines)
    for start, title, ordinal in starts:
        following = [b for b in boundaries if b > start]
        end = (following[0] - 1) if following else entry_end
        ranges.append((start, end, title, ordinal))
    return ranges


def _decision_topics(entry_topics: Sequence[str], ordinal: str) -> tuple[str, ...]:
    """Topics scoped to one decision.

    Authored topics may be decision-qualified (`operations:d1`). Keep those matching this
    decision (unqualified, so downstream vocabulary checks still match) plus any bare
    entry-level topics, which apply to every decision in the entry.
    """
    scoped: list[str] = []
    for topic in entry_topics:
        slug, _, qualifier = topic.partition(":")
        if not qualifier:
            scoped.append(topic)
        elif qualifier.strip().lower() == ordinal:
            scoped.append(slug.strip())
    return tuple(dict.fromkeys(scoped))


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


# --------------------------------------------------------------------------- #
# BM25F lexical scoring
# --------------------------------------------------------------------------- #

# Field weights. `topics` leads because it is the curated vocabulary a human or a
# topic-inference pass assigned to the decision, and it covers 74-83% of the corpus; `tags` was
# the ORIGINAL home of that idea (`#hashtag` syntax) and survives on 1% of chunks, so the two are
# scored as one field rather than kept as a live weight on an abandoned convention. `contexts` is
# gone: it matched 0 of 1259 chunks and no session entry records why it ever existed.
BM25F_FIELD_WEIGHTS: dict[str, float] = {
    "topics": 8.0,
    "heading_path": 6.0,
    "lexical_terms": 3.0,
    "text": 1.0,
}

# Term-frequency saturation. Above roughly k1 occurrences an extra mention adds almost nothing,
# which is the property the previous scorer lacked entirely: it was binary per field, so a decision
# naming a term twenty times scored exactly the same as one naming it once.
BM25F_K1 = 1.2

# Length normalisation, per field. 1.0 divides fully by relative length, 0.0 not at all. Short
# fields (topics, headings) are deliberately less normalised - a two-topic decision is not "more
# about" each topic than a five-topic one in the way a short body would be.
BM25F_B: dict[str, float] = {
    "topics": 0.3,
    "heading_path": 0.5,
    "lexical_terms": 0.5,
    "text": 0.75,
}


@dataclass(frozen=True)
class CorpusStats:
    """Document frequencies and mean field lengths, computed over the ranked corpus."""

    n_docs: int
    doc_freq: dict[str, int]
    avg_field_len: dict[str, float]


def _chunk_field_tokens(chunk: MemoryChunk) -> dict[str, list[str]]:
    """Tokens per scored field.

    Topic slugs are emitted whole AND split on hyphens, so a query saying "topic vocabulary"
    reaches `topic-vocabulary` without the caller knowing the slug. That is the cheap half of
    letting an agent search by subject; the other half is exposing the vocabulary itself.
    """
    topics: list[str] = []
    for slug in tuple(chunk.topics or ()) + tuple(chunk.inferred_topics or ()) + tuple(chunk.tags or ()):
        if not slug:
            continue
        topics.append(slug.lower())
        topics.extend(part for part in re.split(r"[-_]", slug.lower()) if part)
    for item in chunk.inferred_decision_topics or ():
        slug = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else ""
        if slug:
            topics.append(slug.lower())
            topics.extend(part for part in re.split(r"[-_]", slug.lower()) if part)

    return {
        "topics": topics,
        "heading_path": _normalize(" ".join(chunk.heading_path or ())).split(),
        "lexical_terms": [t.lower() for t in (chunk.lexical_terms or ())],
        "text": _normalize(chunk.text or "").split(),
    }


def build_corpus_stats(chunks: Sequence[MemoryChunk]) -> CorpusStats:
    """One pass over the corpus for document frequency and mean field lengths.

    Document frequency is counted once per document across all fields, which is the standard BM25F
    treatment: a term is rare in the corpus or it is not, independently of which field it landed in.
    """
    doc_freq: dict[str, int] = {}
    totals: dict[str, int] = {field: 0 for field in BM25F_FIELD_WEIGHTS}
    for chunk in chunks:
        fields = _chunk_field_tokens(chunk)
        seen: set[str] = set()
        for field, tokens in fields.items():
            totals[field] = totals.get(field, 0) + len(tokens)
            seen.update(tokens)
        for token in seen:
            doc_freq[token] = doc_freq.get(token, 0) + 1
    n = max(len(chunks), 1)
    return CorpusStats(
        n_docs=len(chunks),
        doc_freq=doc_freq,
        avg_field_len={field: (totals.get(field, 0) / n) or 1.0 for field in BM25F_FIELD_WEIGHTS},
    )


def _bm25f_idf(term: str, stats: CorpusStats) -> float:
    """Robertson-Sparck-Jones idf, +1 inside the log so it can never go negative.

    This is the piece the previous scorer had no equivalent of. Measured on this corpus, "memory"
    appears in 79% of decisions and "sourdough" in one, and both used to score identically - so a
    query's total was driven as much by words that distinguish nothing as by words that do.
    """
    df = stats.doc_freq.get(term, 0)
    return math.log(1.0 + (stats.n_docs - df + 0.5) / (df + 0.5))


def _bm25f_score(
    query_terms: Sequence[str],
    chunk: MemoryChunk,
    stats: CorpusStats,
) -> tuple[float, set[str], set[str]]:
    """BM25F: per-field weighted pseudo-frequency, saturated once, weighted by term rarity."""
    matched_terms: set[str] = set()
    matched_fields: set[str] = set()
    fields = _chunk_field_tokens(chunk)
    counts = {field: Counter(tokens) for field, tokens in fields.items()}

    score = 0.0
    for term in query_terms:
        normalized = _normalize(term)
        if not normalized:
            continue
        pseudo_tf = 0.0
        for field, weight in BM25F_FIELD_WEIGHTS.items():
            tf = counts[field].get(normalized, 0)
            if not tf:
                continue
            b = BM25F_B.get(field, 0.75)
            avg = stats.avg_field_len.get(field) or 1.0
            norm = 1.0 - b + b * (len(fields[field]) / avg)
            pseudo_tf += weight * tf / (norm or 1.0)
            matched_terms.add(term)
            matched_fields.add(field)
        if pseudo_tf:
            score += _bm25f_idf(normalized, stats) * pseudo_tf / (BM25F_K1 + pseudo_tf)
    return score, matched_terms, matched_fields


def semantic_text(chunk: MemoryChunk) -> str:
    """The surface the semantic side scores. Body text only.

    It is reasonable to expect this should match what the lexical side reads - `_lexical_score`
    also scores tags (12), contexts (8), heading_path (6) and lexical_terms (4), so embedding the
    body alone compares two different things, and any blend weight fitted on that partly fits the
    mismatch rather than the weighting. That argument was acted on, then tested, and the test did
    not support it. Holding everything else at the shipped configuration and varying ONLY this
    surface, over 180 paraphrase and 120 title queries:

        paraphrase@8   body-only 132/180    heading+tags+body 130/180   (net -2, p = 0.48)
        title@8        body-only 114/120    heading+tags+body 114/120   (no query changed)

    The composed surface bought nothing and cost two answers, so it was reverted. This stays a
    named function rather than being inlined back into `_semantic_scores` because the argument is
    not wrong in principle - it simply does not pay on this corpus with this model - and it is
    worth re-testing if either changes.

    One caveat on the title result: those probes use exact entry titles, which lexical already
    matches through `heading_path`, so the comparison ran on queries where semantic similarity has
    little left to contribute. Near-miss titles could still separate the two.
    """
    return chunk.text or ""


def _semantic_scores(
    query: str,
    chunks: Sequence[MemoryChunk],
    embedding_provider: EmbeddingProvider | None,
) -> list[float] | None:
    if embedding_provider is None or not chunks:
        return None
    try:
        vectors = embedding_provider.embed([query, *(semantic_text(chunk) for chunk in chunks)])
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
    """Halve the decay rate for structural queries.

    RETAINED BUT DOMINATED as of 2026-08-05. `RECENCY_FLOOR` is now 0.98, so the whole recency
    multiplier spans [0.98, 1.0] and halving the exponent inside that band moves a score by well
    under a percent - far less than the gap between adjacent results. It is kept rather than deleted
    because it costs nothing and becomes meaningful again if a future recalibration lowers the
    floor; it is documented rather than left as a second, silent recency mechanism, which is the
    overlap that produced the previous state.
    """
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

"""Real-corpus A/B for a ranking signal -- the gate before any default flip.

The graph-edge contract's "Expose before you rank" rule requires a signal to
prove itself on a branch before a default flip. This module supplies the
*real-corpus* half of that gate: it runs a named ranking signal **off vs on**
over the live corpus at **full k** and reports how each affected entry's rank
moves. Green fixtures prove the mechanism fires; only the real corpus proves the
signal helps live queries without regressing ordinary ones.

A ranking *signal* is a named on/off knob in the ranking pipeline. Signals live
in ``SIGNAL_REGISTRY`` so this generalizes to any future default-ranking signal,
not just the supersession dampener that motivated it.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
import re
from typing import Callable, Sequence

from .semantic_cache import (
    MemoryChunk,
    build_related_entry_graph,
    extract_memory_chunks,
    rank_session_memory,
    replacing_lineage_heads,
)


# --------------------------------------------------------------------------- #
# Result types
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RankChange:
    """How one affected entry's full-corpus position moved off -> on."""

    entry_id: str
    title: str
    rank_off: int  # 1-based position with the signal OFF
    rank_on: int  # 1-based position with the signal ON
    score_off: float
    score_on: float

    @property
    def delta(self) -> int:
        """Positions moved: positive = moved DOWN (demoted), negative = UP."""
        return self.rank_on - self.rank_off


@dataclass(frozen=True)
class QueryABResult:
    query: str
    label: str
    identical: bool  # off and on orderings identical (nothing moved)
    has_affected_hit: bool  # an entry the signal touches matched this query
    changes: tuple[RankChange, ...]
    # Set only for signals with a directional expectation (e.g. supersession:
    # the live replacement should out-rank the entry it retires).
    winner_id: str | None = None
    loser_id: str | None = None
    winner_rank_on: int | None = None
    loser_rank_on: int | None = None
    winner_max_rank_on: int | None = None
    allowed_changed_ids: tuple[str, ...] = ()
    # Unexpected terminal heads that *benefited* from the signal. Pure
    # displacement stays visible in ``changes`` but does not fail the gate.
    unexpected_changed_ids: tuple[str, ...] = ()

    @property
    def winner_beats_loser(self) -> bool | None:
        if self.winner_id is None and self.loser_id is None:
            return None
        if self.winner_rank_on is None or self.loser_rank_on is None:
            return False
        return self.winner_rank_on < self.loser_rank_on

    @property
    def winner_within_max_rank(self) -> bool | None:
        if self.winner_max_rank_on is None:
            return None
        if self.winner_rank_on is None:
            return False
        return self.winner_rank_on <= self.winner_max_rank_on

    @property
    def directional_pass(self) -> bool | None:
        checks: list[bool] = []
        if self.winner_id is not None or self.loser_id is not None:
            checks.append(self.winner_beats_loser is True)
        if self.winner_max_rank_on is not None:
            checks.append(self.winner_within_max_rank is True)
        if self.allowed_changed_ids:
            checks.append(not self.unexpected_changed_ids)
        if not checks:
            return None
        return all(checks)


@dataclass(frozen=True)
class ABResult:
    signal: str
    corpus_size: int
    affected_ids: tuple[str, ...]
    queries: tuple[QueryABResult, ...]
    requires_no_hit_control: bool = False

    @property
    def no_hit_queries_identical(self) -> bool:
        """Every query the signal does NOT touch is byte-identical off vs on."""
        controls = [q for q in self.queries if not q.has_affected_hit]
        if self.requires_no_hit_control and not controls:
            return False
        return all(q.identical for q in controls)

    @property
    def directional_queries_pass(self) -> bool:
        """Every directional query has its winner out-ranking its loser."""
        verdicts = [
            q.directional_pass
            for q in self.queries
            if q.directional_pass is not None
        ]
        return all(verdicts) if verdicts else True

    @property
    def passed(self) -> bool:
        return bool(self.queries) and self.no_hit_queries_identical and self.directional_queries_pass


# --------------------------------------------------------------------------- #
# Signal registry
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class QuerySpec:
    """A query to run, plus an optional directional expectation."""

    query: str
    label: str
    winner_id: str | None = None  # expected to rank ABOVE loser_id when ON
    loser_id: str | None = None
    winner_max_rank_on: int | None = None
    allowed_changed_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class Signal:
    """A named on/off ranking knob and how to exercise it over a corpus."""

    name: str
    describe: str
    off_kwargs: dict
    on_kwargs: dict
    # entries the signal *touches* (whose score it can change), given cwd+corpus
    affected: Callable[[Path, Sequence[MemoryChunk]], set[str]]
    # queries derived from the corpus when the caller passes none
    default_queries: Callable[[Path, Sequence[MemoryChunk]], list[QuerySpec]]
    requires_no_hit_control: bool


def _replaced_ids(cwd: Path, corpus: Sequence[MemoryChunk]) -> set[str]:
    graph = build_related_entry_graph(cwd, chunks=corpus)
    return {node.entry_id for node in graph.values() if node.replaced_by}


def _supersession_lineage_queries(cwd: Path, corpus: Sequence[MemoryChunk]) -> list[QuerySpec]:
    """One query per supersession lineage: the retired entry's own title.

    Querying the retired decision's title surfaces both it and its live
    replacement (they share a topic), so the A/B can check the replacement now
    out-ranks the entry it retires -- exactly the strict criterion the throwaway
    script checked, made repeatable.
    """
    graph = build_related_entry_graph(cwd, chunks=corpus)
    by_id = {c.entry_id: c for c in corpus if c.entry_id}
    specs: list[QuerySpec] = []
    for node in graph.values():
        if not node.replaced_by:
            continue
        retired = by_id.get(node.entry_id)
        if retired is None or not retired.title.strip():
            continue
        query = _ENTRY_TITLE_PREFIX_RE.sub("", retired.title).strip() or retired.title
        for replacement_id in node.replaced_by:
            specs.append(
                QuerySpec(
                    query=query,
                    label=f"{replacement_id} replaces {node.entry_id}",
                    winner_id=replacement_id,
                    loser_id=node.entry_id,
                )
            )
    return specs


def _terminal_replacing_heads(cwd: Path, corpus: Sequence[MemoryChunk]) -> set[str]:
    graph = build_related_entry_graph(cwd, chunks=corpus)
    heads: set[str] = set()
    for node in graph.values():
        heads.update(replacing_lineage_heads(graph, node.entry_id))
    return heads


def _replacing_head_queries(cwd: Path, corpus: Sequence[MemoryChunk]) -> list[QuerySpec]:
    """One query per retired entry, expecting the terminal live replacement to
    enter the default result window."""
    graph = build_related_entry_graph(cwd, chunks=corpus)
    by_id = {c.entry_id: c for c in corpus if c.entry_id}
    specs: list[QuerySpec] = []
    for node in graph.values():
        if not node.replaced_by:
            continue
        retired = by_id.get(node.entry_id)
        if retired is None or not retired.title.strip():
            continue
        query = _ENTRY_TITLE_PREFIX_RE.sub("", retired.title).strip() or retired.title
        for replacement_id in replacing_lineage_heads(graph, node.entry_id):
            specs.append(
                QuerySpec(
                    query=query,
                    label=f"{replacement_id} is terminal replacement for {node.entry_id}",
                    winner_id=replacement_id,
                    loser_id=node.entry_id,
                    winner_max_rank_on=8,
                    allowed_changed_ids=(replacement_id,),
                )
            )
    return specs


SIGNAL_REGISTRY: dict[str, Signal] = {
    "supersession_damping": Signal(
        name="supersession_damping",
        describe="down-rank an entry a later decision has replaced so the live replacement leads",
        off_kwargs={"supersession_damping": False},
        on_kwargs={"supersession_damping": True},
        affected=_replaced_ids,
        default_queries=_supersession_lineage_queries,
        requires_no_hit_control=True,
    ),
    "recency": Signal(
        name="recency",
        describe="age-decay multiplier that favours newer entries",
        off_kwargs={"recency_enabled": False},
        on_kwargs={"recency_enabled": True},
        # Recency touches every dated entry; there is no lineage to derive
        # queries from, so the caller must pass --query for a meaningful A/B.
        affected=lambda cwd, corpus: {c.entry_id for c in corpus if c.entry_id},
        default_queries=lambda cwd, corpus: [],
        requires_no_hit_control=False,
    ),
    "replacing_successor_boost": Signal(
        name="replacing_successor_boost",
        describe="bounded lift for a matching terminal replacement of a replaced entry",
        off_kwargs={"supersession_damping": True, "replacing_successor_boost": False},
        on_kwargs={"supersession_damping": True, "replacing_successor_boost": True},
        affected=_terminal_replacing_heads,
        default_queries=_replacing_head_queries,
        requires_no_hit_control=True,
    ),
}


# --------------------------------------------------------------------------- #
# Harness
# --------------------------------------------------------------------------- #


def _rank(cwd: Path, query: str, corpus: Sequence[MemoryChunk], kwargs: dict, today: date | None):
    # Full-k: rank the whole corpus so a demotion out of the default window is
    # still visible (the #10-outside-top-8 case that motivated this).
    return rank_session_memory(
        query,
        cwd,
        top_k=max(len(corpus), 1),
        chunks=list(corpus),
        embedding_provider=None,  # lexical: the deterministic, reproducible baseline
        today=today,
        **kwargs,
    )


_ENTRY_TITLE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}\s+-\s+")


def _no_hit_control(
    cwd: Path,
    corpus: Sequence[MemoryChunk],
    signal: Signal,
    affected_ids: set[str],
    today: date | None,
) -> QuerySpec | None:
    """Find one real query that matches the corpus but no affected entry."""
    affected_text = "\n".join(
        " ".join(
            (
                chunk.title,
                chunk.text,
                *chunk.tags,
                *chunk.contexts,
                *chunk.heading_path,
                *chunk.lexical_terms,
            )
        ).lower()
        for chunk in corpus
        if chunk.entry_id in affected_ids
    )
    candidates = sorted(
        (chunk for chunk in corpus if chunk.entry_id not in affected_ids),
        key=lambda chunk: (chunk.session_date, chunk.title, chunk.entry_id or ""),
        reverse=True,
    )
    for chunk in candidates:
        title = _ENTRY_TITLE_PREFIX_RE.sub("", chunk.title).strip()
        unique_words = [
            word
            for word in re.findall(r"[a-z0-9][a-z0-9_-]{3,}", title.lower())
            if word not in affected_text
        ]
        if not unique_words:
            continue
        query = " ".join(dict.fromkeys(unique_words[:3]))
        ranked = _rank(cwd, query, corpus, signal.off_kwargs, today)
        matched_ids = {
            item.chunk.entry_id
            for item in ranked
            if item.match_score > 0 and item.chunk.entry_id is not None
        }
        if matched_ids and not (matched_ids & affected_ids):
            return QuerySpec(query=query, label=f"no-affected-hit control: {query}")
    return None


def _compare_query(
    cwd: Path,
    spec: QuerySpec,
    corpus: Sequence[MemoryChunk],
    signal: Signal,
    affected_ids: set[str],
    today: date | None,
) -> QueryABResult:
    off = _rank(cwd, spec.query, corpus, signal.off_kwargs, today)
    on = _rank(cwd, spec.query, corpus, signal.on_kwargs, today)

    identical = off == on

    pos_off = {r.chunk.entry_id: i + 1 for i, r in enumerate(off) if r.chunk.entry_id}
    pos_on = {r.chunk.entry_id: i + 1 for i, r in enumerate(on) if r.chunk.entry_id}
    score_off = {r.chunk.entry_id: r.final_score for r in off if r.chunk.entry_id}
    score_on = {r.chunk.entry_id: r.final_score for r in on if r.chunk.entry_id}
    title_of = {r.chunk.entry_id: r.chunk.title for r in off if r.chunk.entry_id}

    # An affected entry counts as a "hit" for this query only if it actually
    # matched (a zero-match entry sorts to the deterministic tail either way).
    matched = {r.chunk.entry_id for r in off if r.match_score > 0 and r.chunk.entry_id}
    affected_hits = affected_ids & matched

    changes: list[RankChange] = []
    for entry_id in sorted(affected_hits):
        ro, rn = pos_off.get(entry_id), pos_on.get(entry_id)
        so, sn = score_off.get(entry_id, 0.0), score_on.get(entry_id, 0.0)
        if ro != rn or so != sn:
            changes.append(
                RankChange(
                    entry_id=entry_id,
                    title=title_of.get(entry_id, ""),
                    rank_off=ro or 0,
                    rank_on=rn or 0,
                    score_off=so,
                    score_on=sn,
                )
            )
    unexpected_changed_ids = tuple(
        sorted(
            change.entry_id
            for change in changes
            if (
                spec.allowed_changed_ids
                and change.entry_id not in spec.allowed_changed_ids
                and (
                    change.score_on > change.score_off
                    or (change.rank_on and change.rank_off and change.rank_on < change.rank_off)
                )
            )
        )
    )

    return QueryABResult(
        query=spec.query,
        label=spec.label,
        identical=identical,
        has_affected_hit=bool(affected_hits),
        changes=tuple(changes),
        winner_id=spec.winner_id,
        loser_id=spec.loser_id,
        winner_rank_on=pos_on.get(spec.winner_id) if spec.winner_id else None,
        loser_rank_on=pos_on.get(spec.loser_id) if spec.loser_id else None,
        winner_max_rank_on=spec.winner_max_rank_on,
        allowed_changed_ids=spec.allowed_changed_ids,
        unexpected_changed_ids=unexpected_changed_ids,
    )


def run_ab(
    signal_name: str,
    cwd: str | Path = ".",
    *,
    queries: Sequence[str] | None = None,
    corpus: Sequence[MemoryChunk] | None = None,
    today: date | None = None,
) -> ABResult:
    """Run the off-vs-on A/B for ``signal_name`` over the live corpus.

    ``queries`` extends the signal's derived default queries. ``corpus`` lets a
    caller (or a fixture) supply an already-extracted entry-granularity corpus so
    the branch fixture and the real-corpus check run the identical comparison.
    """
    signal = SIGNAL_REGISTRY.get(signal_name)
    if signal is None:
        known = ", ".join(sorted(SIGNAL_REGISTRY))
        raise KeyError(f"unknown ranking signal {signal_name!r}; known signals: {known}")

    path = Path(cwd).resolve()
    if corpus is None:
        corpus = extract_memory_chunks(path, granularity="entry")

    affected_ids = signal.affected(path, corpus)

    specs = signal.default_queries(path, corpus)
    if queries is not None:
        specs.extend(QuerySpec(query=q, label=q) for q in queries)
    if signal.requires_no_hit_control:
        control = _no_hit_control(path, corpus, signal, affected_ids, today)
        if control is not None and all(spec.query != control.query for spec in specs):
            specs.append(control)

    results = tuple(_compare_query(path, spec, corpus, signal, affected_ids, today) for spec in specs)
    return ABResult(
        signal=signal_name,
        corpus_size=len(corpus),
        affected_ids=tuple(sorted(affected_ids)),
        queries=results,
        requires_no_hit_control=signal.requires_no_hit_control,
    )


def format_ab_report(result: ABResult) -> str:
    """Human-readable A/B report for the CLI."""
    signal = SIGNAL_REGISTRY.get(result.signal)
    lines: list[str] = []
    lines.append(f"Ranking A/B -- signal: {result.signal}")
    if signal is not None:
        lines.append(f"  ({signal.describe})")
    lines.append(
        f"  corpus: {result.corpus_size} entries | affected by signal: {len(result.affected_ids)} | "
        f"queries: {len(result.queries)}"
    )
    lines.append("")

    if not result.queries:
        lines.append("No queries to run. This signal has no derived default queries -- pass --query <q>.")
        return "\n".join(lines)

    for q in result.queries:
        header = f"- {q.label}"
        if q.label != q.query:
            header += f'   [query: "{q.query}"]'
        lines.append(header)
        if q.winner_beats_loser is not None:
            mark = "PASS" if q.winner_beats_loser else "REGRESSION"
            lines.append(
                f"    {mark}  replacement {q.winner_id} #{q.winner_rank_on} vs "
                f"retired {q.loser_id} #{q.loser_rank_on}"
            )
        if q.winner_within_max_rank is not None:
            rank_mark = "PASS" if q.winner_within_max_rank else "REGRESSION"
            lines.append(
                f"    {rank_mark}  replacement {q.winner_id} within top {q.winner_max_rank_on}: "
                f"#{q.winner_rank_on}"
            )
        if q.unexpected_changed_ids:
            lines.append(
                "    REGRESSION  unexpected affected terminal heads benefited: "
                + ", ".join(q.unexpected_changed_ids)
            )
        if not q.has_affected_hit:
            state = "identical off/on" if q.identical else "CHANGED with no affected hit"
            lines.append(f"    no affected entry matched -- {state}")
        for change in q.changes:
            direction = "down" if change.delta > 0 else ("up" if change.delta < 0 else "same")
            if change.score_on > change.score_off:
                why = "boosted"
            elif change.score_on < change.score_off:
                why = "demoted"
            else:
                why = "displaced"
            lines.append(
                f"    {change.entry_id}  #{change.rank_off} -> #{change.rank_on} "
                f"({direction} {abs(change.delta)}, {why})  score {change.score_off:.3f} -> {change.score_on:.3f}"
            )
        lines.append("")

    verdict = "PASS" if result.passed else "FAIL"
    lines.append(f"Gate verdict: {verdict}")
    lines.append(f"  no-affected-hit queries byte-identical: {result.no_hit_queries_identical}")
    lines.append(f"  directional queries (replacement out-ranks retired): {result.directional_queries_pass}")
    return "\n".join(lines)


def ab_result_to_dict(result: ABResult) -> dict:
    """Machine-readable result including computed gate verdicts."""
    payload = asdict(result)
    for query_payload, query in zip(payload["queries"], result.queries):
        query_payload["winner_beats_loser"] = query.winner_beats_loser
        query_payload["winner_within_max_rank"] = query.winner_within_max_rank
        query_payload["directional_pass"] = query.directional_pass
    payload.update(
        {
            "no_hit_queries_identical": result.no_hit_queries_identical,
            "directional_queries_pass": result.directional_queries_pass,
            "passed": result.passed,
        }
    )
    return payload

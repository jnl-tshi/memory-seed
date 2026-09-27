"""Clause-level Constitution selection shared by retrieval and Task Packets.

The Constitution is authority, but a whole-document read spends most of a small
evidence budget on clauses unrelated to the work.  This module parses the
anchor-delimited clauses and selects the relevant ones through one cascade:

1. explicit anchors (a caller mandate - exclusive, like a dispatch's refs);
2. governing/supporting bindings of the ADRs in hand, plus ``S:`` anchors;
3. the topic->clause map (derived from ADR topics x bindings, plus authored
   ``constitution-topics`` markers on clauses no ADR binds);
4. BM25F keyword ranking over clause text.

Steps 3-4 are relevance guesses, so they only fill the room left under
``ranked_cap``.  Callers fall back to the whole document only when the cascade
selects nothing.  Everything here is read-time: no cache, no stored map.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

CONSTITUTION_ANCHOR_RE = re.compile(
    r"<!--\s*constitution-ref:\s*(constitution:v\d+#[a-z0-9-]+)\s*-->"
)
CONSTITUTION_TOPICS_RE = re.compile(r"<!--\s*constitution-topics:\s*([^>]*?)\s*-->")
CONSTITUTION_VERSION_RE = re.compile(
    r"\*\*Version:\*\*\s*([0-9]+(?:\.[0-9]+)*)[^\n]*\*\*RATIFIED"
)
CONSTITUTION_BINDING_RE = re.compile(
    r"`(constitution:v\d+#[a-z0-9][a-z0-9-]*)`\s*\((governing|supporting)\)"
)
DEFAULT_RANKED_CAP = 4_000
# Clauses are short (~100 tokens), so a token cap alone admits most of the
# document; ranked selection also stops at this many clauses.
DEFAULT_RANKED_LIMIT = 8

# Selection stages, in cascade order.  They are also the ``selected_by``
# vocabulary a pack records, so a reader can see why each clause is present.
STAGE_ANCHOR = "constitution.anchors"
STAGE_BINDING = "constitution.adr_bindings"
STAGE_SOURCE = "constitution.source_anchors"
STAGE_TOPIC = "constitution.topic_map"
STAGE_KEYWORD = "constitution.keywords"
STAGE_FALLBACK = "constitution.fallback_whole"


class ConstitutionProjectionError(ValueError):
    """The Constitution cannot be parsed or an explicit anchor is absent."""

    def __init__(self, code: str, message: str, details: Mapping[str, Any] | None = None) -> None:
        self.code = code
        self.details = dict(details or {})
        super().__init__(message)


@dataclass(frozen=True)
class ConstitutionClause:
    ref: str
    heading: str
    line_range: tuple[int, int]  # 1-based, inclusive
    content: str
    authored_topics: tuple[str, ...] = ()

    @property
    def slug(self) -> str:
        return self.ref.split("#", 1)[-1]


@dataclass(frozen=True)
class ConstitutionDocument:
    source: str
    content: str
    ratified_version: str
    clauses: tuple[ConstitutionClause, ...]

    @property
    def line_count(self) -> int:
        return max(1, len(self.content.splitlines()))

    @property
    def full_digest(self) -> str:
        return content_digest(self.content)

    @property
    def current_major(self) -> int:
        return int(self.ratified_version.split(".", 1)[0])

    def by_ref(self) -> dict[str, ConstitutionClause]:
        return {clause.ref: clause for clause in self.clauses}

    def current_ref(self, reference: str) -> str:
        """Resolve a legacy ``vK#slug`` name to the renamed current anchor.

        Older dispatches and ADR bindings keep resolving after the
        Constitution is re-namespaced; an unknown name is returned unchanged.
        """
        match = re.fullmatch(r"constitution:v(\d+)#([a-z0-9-]+)", reference)
        if match and int(match.group(1)) < self.current_major:
            renamed = f"constitution:v{self.current_major}#{match.group(2)}"
            if renamed in self.by_ref():
                return renamed
        return reference


@dataclass
class SelectedClause:
    clause: ConstitutionClause
    stages: set[str] = field(default_factory=set)
    reasons: set[str] = field(default_factory=set)


@dataclass
class ClauseSelection:
    selected: list[SelectedClause]
    mode: str  # explicit_anchors | cascade | fallback_whole
    ranked_cap: int
    unmatched_source_anchors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def fallback(self) -> bool:
        return self.mode == "fallback_whole"


def content_digest(content: str) -> str:
    return "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()


def estimate_tokens(text: str) -> int:
    # The retrieval resolver's fixed proxy, so caps and pack budgets agree.
    return max(1, (len(text.encode("utf-8")) + 3) // 4)


def heading_slug(heading: str) -> str:
    """GitHub-style anchor slug - identical to the resolver's ``S:`` matcher."""
    text = heading.strip().lstrip("#").strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def parse_constitution(content: str, source: str) -> ConstitutionDocument:
    """Parse complete, anchor-delimited clauses.

    An anchor owns every line through the line before the next anchor or the
    next heading, so a selected clause is always complete and a trailing
    section (such as the version log) never rides along.  A
    ``constitution-topics`` marker belongs to the clause whose anchor precedes
    it; like the anchor, it is an HTML comment inside the clause's lines.
    """
    content = "\n".join(content.splitlines())
    lines = content.splitlines()
    version_match = CONSTITUTION_VERSION_RE.search(content)
    if version_match is None:
        raise ConstitutionProjectionError(
            "invalid_constitution_projection",
            "Constitution projection requires explicit ratified Version metadata",
            {"source": source},
        )
    ratified_version = version_match.group(1)
    expected_prefix = f"constitution:v{ratified_version.split('.', 1)[0]}#"
    anchors = [
        (index, match.group(1))
        for index, line in enumerate(lines)
        if (match := CONSTITUTION_ANCHOR_RE.search(line)) is not None
    ]
    incompatible = sorted(ref for _index, ref in anchors if not ref.startswith(expected_prefix))
    if incompatible:
        raise ConstitutionProjectionError(
            "invalid_constitution_projection",
            "Constitution anchors must use the ratified Version's major identity",
            {
                "source": source,
                "ratified_version": ratified_version,
                "expected_anchor_prefix": expected_prefix,
                "incompatible_anchors": incompatible,
            },
        )
    clauses: list[ConstitutionClause] = []
    for ordinal, (start, reference) in enumerate(anchors):
        end = anchors[ordinal + 1][0] if ordinal + 1 < len(anchors) else len(lines)
        for candidate_index in range(start + 1, end):
            if lines[candidate_index].startswith("#"):
                end = candidate_index
                break
        heading = ""
        for candidate in reversed(lines[: start + 1]):
            if candidate.startswith("#"):
                heading = candidate.strip()
                break
        topics: list[str] = []
        for line in lines[start + 1 : end]:
            match = CONSTITUTION_TOPICS_RE.search(line)
            if match:
                topics.extend(item.strip() for item in match.group(1).split(",") if item.strip())
        clauses.append(
            ConstitutionClause(
                ref=reference,
                heading=heading or "(unheaded constitutional clause)",
                line_range=(start + 1, max(start + 1, end)),
                content="\n".join(lines[start:end]),
                authored_topics=tuple(dict.fromkeys(topics)),
            )
        )
    return ConstitutionDocument(
        source=source,
        content=content,
        ratified_version=ratified_version,
        clauses=tuple(clauses),
    )


def find_constitution(root: Path) -> Path | None:
    return next(
        (path for path in (root / "docs" / "CONSTITUTION.md", root / "CONSTITUTION.md") if path.is_file()),
        None,
    )


def adr_constitution_bindings(record: Any) -> list[tuple[str, str]]:
    """``(ref, role)`` bindings an ADR declares across its event ledger."""
    seen: dict[str, str] = {}
    for event in getattr(record, "events", ()):
        for item in getattr(event, "constitution_refs", ()):
            # governing outranks supporting when an ADR names a clause both ways
            if seen.get(item.ref) != "governing":
                seen[item.ref] = item.role
    return sorted(seen.items())


def derived_topic_clause_map(
    document: ConstitutionDocument,
    adrs: Iterable[Any],
) -> dict[str, dict[str, dict[str, int]]]:
    """``{topic: {clause_ref: {"governing": n, "supporting": m, "authored": 0|1}}}``.

    Derived by joining each ADR's ``topics`` with its Constitution bindings,
    then extended by authored ``constitution-topics`` markers.  Built on
    demand from Markdown, never stored.
    """
    known = document.by_ref()
    mapping: dict[str, dict[str, dict[str, int]]] = {}

    def bump(topic: str, ref: str, key: str) -> None:
        counts = mapping.setdefault(topic, {}).setdefault(
            ref, {"governing": 0, "supporting": 0, "authored": 0}
        )
        counts[key] += 1

    for record in adrs:
        for ref, role in adr_constitution_bindings(record):
            current = document.current_ref(ref)
            if current not in known:
                continue
            for topic in getattr(record, "topics", ()):
                bump(topic, current, role if role in {"governing", "supporting"} else "supporting")
    for clause in document.clauses:
        for topic in clause.authored_topics:
            counts = mapping.setdefault(topic, {}).setdefault(
                clause.ref, {"governing": 0, "supporting": 0, "authored": 0}
            )
            counts["authored"] = 1
    return mapping


def topic_map_report(cwd: str | Path = ".", *, topic: str | None = None) -> dict[str, Any]:
    """The live topic->clause map, each row naming its source, for review.

    Also reports the clauses no topic reaches, so a gap is visible rather
    than silently served only by keyword ranking.
    """
    from .adr import iter_adrs
    from .core import resolve_runtime
    from .topics import load_topic_index

    root = resolve_runtime(cwd).workspace_root
    path = find_constitution(root)
    if path is None:
        return {"ok": False, "error": "no docs/CONSTITUTION.md"}
    document = parse_constitution(path.read_text(encoding="utf-8"), path.relative_to(root).as_posix())
    mapping = derived_topic_clause_map(document, iter_adrs(cwd))
    known_topics = set(load_topic_index(cwd).resolution())
    rows = []
    for slug in sorted(mapping):
        if topic is not None and slug != topic:
            continue
        for ref, counts in sorted(mapping[slug].items()):
            sources = []
            if counts["governing"] or counts["supporting"]:
                sources.append(f"derived ({counts['governing']} governing, {counts['supporting']} supporting)")
            if counts["authored"]:
                sources.append("authored tag")
            rows.append({"topic": slug, "clause": ref, "sources": sources})
    reached = {ref for refs in mapping.values() for ref in refs}
    return {
        "ok": True,
        "constitution": document.source,
        "ratified_version": document.ratified_version,
        "rows": rows,
        "unreached_clauses": sorted(clause.ref for clause in document.clauses if clause.ref not in reached),
        "unknown_authored_topics": sorted(
            {t for clause in document.clauses for t in clause.authored_topics} - known_topics
        ),
    }


def _keyword_terms(keywords: Sequence[str]) -> list[str]:
    from .semantic_cache import normalize_lexical_text

    terms: list[str] = []
    for keyword in keywords:
        for word in re.split(r"[^\w]+", normalize_lexical_text(keyword)):
            if len(word) >= 3 and word not in terms:
                terms.append(word)
    return terms


def _clause_pseudo_chunks(
    document: ConstitutionDocument,
    clause_topics: Mapping[str, Sequence[str]],
) -> list[Any]:
    from types import SimpleNamespace

    return [
        SimpleNamespace(
            ref=clause.ref,
            topics=tuple(clause_topics.get(clause.ref, ())),
            inferred_topics=(),
            tags=(clause.slug,),
            inferred_decision_topics=(),
            heading_path=(re.sub(r"^#+\s*", "", clause.heading),),
            lexical_terms=(),
            text=clause.content,
        )
        for clause in document.clauses
    ]


def rank_clauses_by_keywords(
    document: ConstitutionDocument,
    keywords: Sequence[str],
    *,
    clause_topics: Mapping[str, Sequence[str]] | None = None,
) -> list[tuple[float, ConstitutionClause, list[str]]]:
    """BM25F over clauses, reusing the memory-search scorer and field weights."""
    from .semantic_cache import _bm25f_score, build_corpus_stats

    terms = _keyword_terms(keywords)
    if not terms or not document.clauses:
        return []
    chunks = _clause_pseudo_chunks(document, clause_topics or {})
    stats = build_corpus_stats(chunks)
    by_ref = document.by_ref()
    ranked: list[tuple[float, ConstitutionClause, list[str]]] = []
    for chunk in chunks:
        score, matched, _fields = _bm25f_score(terms, chunk, stats)
        if score > 0:
            ranked.append((score, by_ref[chunk.ref], sorted(matched)))
    ranked.sort(key=lambda item: (-item[0], item[1].ref))
    return ranked


def select_clauses(
    document: ConstitutionDocument,
    *,
    anchors: Sequence[str] = (),
    adr_bindings: Sequence[tuple[str, str, str]] = (),
    related_adr_bindings: Sequence[tuple[str, str, str]] = (),
    source_anchors: Sequence[str] = (),
    topics: Sequence[str] = (),
    topic_map: Mapping[str, Mapping[str, Mapping[str, int]]] | None = None,
    keywords: Sequence[str] = (),
    ranked_cap: int = DEFAULT_RANKED_CAP,
    ranked_limit: int = DEFAULT_RANKED_LIMIT,
) -> ClauseSelection:
    """Run the clause cascade.  Bindings are ``(ref, adr_id, role)``.

    Two tiers.  *Mandated* clauses are complete even over the cap: explicit
    anchors (exclusive, exactly as a dispatch's ``constitution_refs`` always
    were), bindings of ADRs the caller named (``adr_bindings``: pinned or
    path-selected), and ``S:`` anchors naming one clause.  *Ranked* clauses
    fill only the room left under ``ranked_cap``: ``S:`` anchors naming a
    whole section, bindings of ADRs found by relevance
    (``related_adr_bindings``, in the caller's order), the topic map, then
    keywords.  An explicit anchor absent from the document raises: a caller
    mandate must fail closed, never widen.
    """
    by_ref = document.by_ref()
    picked: dict[str, SelectedClause] = {}
    order: list[str] = []
    warnings: list[str] = []

    def add(clause: ConstitutionClause, stage: str, reason: str) -> None:
        entry = picked.get(clause.ref)
        if entry is None:
            entry = picked[clause.ref] = SelectedClause(clause)
            order.append(clause.ref)
        entry.stages.add(stage)
        entry.reasons.add(reason)

    explicit = list(dict.fromkeys(document.current_ref(ref) for ref in anchors))
    missing = sorted(set(explicit) - set(by_ref))
    if missing:
        raise ConstitutionProjectionError(
            "missing_constitution_anchor",
            "names anchor(s) absent from the Constitution",
            {"missing_refs": missing, "source": document.source},
        )
    for ref in explicit:
        add(by_ref[ref], STAGE_ANCHOR, "explicit Constitution anchor")

    if not explicit:
        missing_bindings = []
        for ref, adr_id, role in adr_bindings:
            current = document.current_ref(ref)
            clause = by_ref.get(current)
            if clause is None:
                missing_bindings.append({"adr_id": adr_id, "role": role, "missing_anchor": ref})
                continue
            add(clause, STAGE_BINDING, f"ADR {adr_id} {role} binding")
        if missing_bindings:
            warnings.append(
                "ADR binding(s) name anchors absent from the Constitution: "
                + ", ".join(f"{item['adr_id']}->{item['missing_anchor']}" for item in missing_bindings)
            )

    unmatched: list[str] = []
    section_anchor_matches: list[tuple[str, ConstitutionClause]] = []
    for anchor in source_anchors:
        exact = [clause for clause in document.clauses if clause.slug == anchor]
        section = [
            clause
            for clause in document.clauses
            if heading_slug(clause.heading) == anchor and clause not in exact
        ]
        if not exact and not section:
            unmatched.append(anchor)
        for clause in exact:
            add(clause, STAGE_SOURCE, f"decision S: Constitution anchor #{anchor}")
        section_anchor_matches.extend((anchor, clause) for clause in section)

    if explicit:
        # An explicit mandate keeps section-level S: citations complete too,
        # as the dispatch projection always did.
        for anchor, clause in section_anchor_matches:
            add(clause, STAGE_SOURCE, f"decision S: Constitution anchor #{anchor}")
    else:
        # Ranked clauses are relevance guesses.  Every signal adds to one
        # score per clause, so a clause several signals agree on outranks one
        # that a single weak signal reaches; the best ``ranked_limit`` are
        # kept, whole, while they fit under ``ranked_cap``.
        scores: dict[str, float] = {}
        signals: dict[str, list[tuple[str, str]]] = {}

        def vote(ref: str, weight: float, stage: str, reason: str) -> None:
            if ref not in by_ref:
                return
            scores[ref] = scores.get(ref, 0.0) + weight
            signals.setdefault(ref, []).append((stage, reason))

        for anchor, clause in section_anchor_matches:
            vote(clause.ref, 2.0, STAGE_SOURCE, f"decision S: Constitution section anchor #{anchor}")
        for ref, adr_id, role in related_adr_bindings:
            vote(
                document.current_ref(ref),
                2.0 if role == "governing" else 1.0,
                STAGE_BINDING,
                f"related ADR {adr_id} {role} binding",
            )
        clause_topics: dict[str, list[str]] = {}
        for topic, refs in (topic_map or {}).items():
            for ref, counts in refs.items():
                clause_topics.setdefault(ref, []).append(topic)
                if topic not in topics:
                    continue
                governing = int(counts.get("governing", 0))
                supporting = int(counts.get("supporting", 0))
                if counts.get("authored"):
                    vote(ref, 3.0, STAGE_TOPIC, f"topic {topic!r} maps to this clause (authored tag)")
                if governing or supporting:
                    # Diminishing: many ADRs in one topic citing a clause is
                    # one signal about that topic, not many.
                    vote(
                        ref,
                        min(3.0, governing * 1.0 + supporting * 0.5),
                        STAGE_TOPIC,
                        f"topic {topic!r} maps to this clause ({governing} governing / {supporting} supporting ADR binding(s))",
                    )
        ranked_keywords = rank_clauses_by_keywords(document, keywords, clause_topics=clause_topics)
        top_keyword = ranked_keywords[0][0] if ranked_keywords else 0.0
        for score, clause, matched in ranked_keywords:
            # Normalised to the best keyword match, so keywords weigh like one
            # strong structural signal rather than swamping the others.
            vote(clause.ref, 3.0 * score / top_keyword, STAGE_KEYWORD, f"keyword BM25F {score:.2f} ({', '.join(matched)})")

        used = sum(estimate_tokens(picked[ref].clause.content) for ref in order)
        admitted = 0
        for ref in sorted(scores, key=lambda value: (-scores[value], value)):
            if admitted >= ranked_limit:
                break
            clause = by_ref[ref]
            if ref not in picked:
                cost = estimate_tokens(clause.content)
                # The best one is always admitted when nothing else was.
                if order and used + cost > ranked_cap:
                    continue
                used += cost
                admitted += 1
            for stage, reason in signals[ref]:
                add(clause, stage, reason)

    selected = [picked[ref] for ref in order]
    selected.sort(key=lambda item: item.clause.line_range[0])
    if explicit:
        mode = "explicit_anchors"
    elif selected:
        mode = "cascade"
    else:
        mode = "fallback_whole"
    return ClauseSelection(
        selected=selected,
        mode=mode,
        ranked_cap=ranked_cap,
        unmatched_source_anchors=unmatched,
        warnings=warnings,
    )

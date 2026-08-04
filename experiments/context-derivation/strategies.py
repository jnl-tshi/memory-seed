"""Deterministic, experiment-only ADR context strategies.

The module deliberately composes Memory Seed's public readers.  It does not
parse session or ADR Markdown itself and has no production write surface.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass
from functools import lru_cache
from itertools import product
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

# Direct ``python experiments/context-derivation/strategies.py`` execution puts
# only this directory on sys.path. Add the source checkout root so the CLI uses
# the same production readers as an installed package invocation.
_SOURCE_ROOT = Path(__file__).resolve().parents[2]
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from memory_seed.adr import AdrRecord, adr_membership, iter_adrs
from memory_seed.core import entry_body_decisions, resolve_runtime
from memory_seed.retrieval import (
    RetrievalSpecResolutionError,
    augment_chunks_with_link_sidecars,
    augment_chunks_with_topic_sidecars,
    resolve_retrieval_spec,
)
from memory_seed.semantic_cache import (
    MemoryChunk,
    build_related_entry_graph,
    extract_memory_chunks,
    rank_session_memory,
)

from contracts import STRATEGY_SCHEMA, canonical_json, fingerprint, require_schema


RESULT_SCHEMA = "context-strategy-result.v1"
FAMILIES = ("search", "timeline", "retrieval-v1", "adr-structural", "adr-hybrid", "oracle")
LINEAGE_TYPES = frozenset({"evolves", "replaces"})
_RELATION_RE = re.compile(
    r"^link:(?P<source>[^:]+:d\d+):(?P<type>evolves|replaces):(?P<target>[^:]+:d\d+)$"
)

DEFAULTS: dict[str, dict[str, Any]] = {
    "search": {"top_k": 8, "max_items": 40, "max_tokens": 16_000},
    "timeline": {
        "graph_depth": 1,
        "edge_types": ["related", "replaces", "evolves", "branch"],
        "include_sections": True,
        "max_entries": 40,
        "max_items": 80,
        "max_tokens": 16_000,
    },
    "retrieval-v1": {
        "related_depth": 2,
        "neighbouring_entries": 4,
        "max_items": 40,
        "max_tokens": 16_000,
    },
    "adr-structural": {
        "scope": "current",
        "lineage_depth": "all",
        "lineage_direction": "ancestor",
        "include_non_authoritative": False,
        "include_pending": False,
        "include_rejected": False,
        "include_no_change": False,
        "related_depth": 0,
        "detail": "decision",
        "semantic_gap_top_k": 0,
        "max_items": 40,
        "max_tokens": 16_000,
    },
    "adr-hybrid": {
        "scope": "current",
        "lineage_depth": "all",
        "lineage_direction": "ancestor",
        "include_non_authoritative": False,
        "include_pending": False,
        "include_rejected": False,
        "include_no_change": False,
        "related_depth": 0,
        "detail": "decision",
        "semantic_gap_top_k": 3,
        "max_items": 40,
        "max_tokens": 16_000,
    },
    "oracle": {"detail": "decision", "max_items": 100, "max_tokens": 20_000},
}


@dataclass(frozen=True)
class DecisionEvidence:
    ref: str
    entry_id: str
    ordinal: str
    text: str
    source: str
    chunk_id: str
    session_date: str


@dataclass(frozen=True)
class ExperimentCorpus:
    root: Path
    chunks: tuple[MemoryChunk, ...]
    by_entry: Mapping[str, MemoryChunk]
    graph: Mapping[str, Any]
    adrs: tuple[AdrRecord, ...]
    adr_by_id: Mapping[str, AdrRecord]
    decisions: Mapping[str, DecisionEvidence]
    adr_by_ref: Mapping[str, tuple[str, ...]]


def _load_corpus_uncached(cwd: str | Path) -> ExperimentCorpus:
    root = Path(resolve_runtime(cwd).workspace_root).resolve()
    chunks = tuple(
        augment_chunks_with_topic_sidecars(
            augment_chunks_with_link_sidecars(
                extract_memory_chunks(root, granularity="entry"), root
            ),
            root,
        )
    )
    by_entry = {}
    for chunk in chunks:
        if chunk.entry_id:
            by_entry.setdefault(chunk.entry_id, chunk)
    decisions: dict[str, DecisionEvidence] = {}
    for entry_id, chunk in by_entry.items():
        for item in entry_body_decisions(chunk.text):
            ref = f"{entry_id}:{item.ordinal}"
            text = ((item.name + "\n") if item.name else "") + item.text
            decisions[ref] = DecisionEvidence(
                ref, entry_id, item.ordinal, text, chunk.source_path,
                chunk.chunk_id, chunk.session_date.isoformat(),
            )
    adrs = tuple(iter_adrs(root))
    adr_by_ref: dict[str, list[str]] = {}
    for record in adrs:
        for ref in adr_membership(record):
            adr_by_ref.setdefault(ref, []).append(record.adr_id)
    return ExperimentCorpus(
        root=root,
        chunks=chunks,
        by_entry=by_entry,
        graph=build_related_entry_graph(root, chunks=chunks),
        adrs=adrs,
        adr_by_id={record.adr_id: record for record in adrs},
        decisions=decisions,
        adr_by_ref={key: tuple(sorted(value)) for key, value in adr_by_ref.items()},
    )


@lru_cache(maxsize=16)
def _cached_corpus(root: str) -> ExperimentCorpus:
    return _load_corpus_uncached(root)


def load_corpus(cwd: str | Path = ".", *, refresh: bool = False) -> ExperimentCorpus:
    """Load the canonical corpus once per resolved runtime in this process."""
    root = str(Path(resolve_runtime(cwd).workspace_root).resolve())
    if refresh:
        _cached_corpus.cache_clear()
        _retrieval_v1_pack.cache_clear()
        _timeline_pack.cache_clear()
    return _cached_corpus(root)


def normalize_strategy(strategy: Mapping[str, Any]) -> dict[str, Any]:
    require_schema(strategy, STRATEGY_SCHEMA)
    family = strategy.get("family")
    if family not in FAMILIES:
        raise ValueError(f"unsupported strategy family: {family!r}")
    raw = strategy.get("parameters")
    if not isinstance(raw, Mapping):
        raise ValueError("strategy parameters must be an object")
    unknown = set(raw) - set(DEFAULTS[family])
    if unknown:
        raise ValueError(f"unknown {family} parameter(s): {', '.join(sorted(unknown))}")
    parameters = {**DEFAULTS[family], **raw}
    if parameters["max_items"] < 1 or parameters["max_tokens"] < 1:
        raise ValueError("max_items and max_tokens must be positive")
    if family in {"adr-structural", "adr-hybrid"}:
        if parameters["include_non_authoritative"]:
            parameters["include_pending"] = True
            parameters["include_rejected"] = True
            parameters["include_no_change"] = True
        if parameters["scope"] not in {"current", "accepted", "full"}:
            raise ValueError("scope must be current, accepted, or full")
        if parameters["lineage_depth"] not in {0, 1, 2, "all"}:
            raise ValueError("lineage_depth must be 0, 1, 2, or all")
        if parameters["lineage_direction"] not in {"ancestor", "both"}:
            raise ValueError("lineage_direction must be ancestor or both")
        if parameters["related_depth"] not in {0, 1, 2}:
            raise ValueError("related_depth must be 0, 1, or 2")
        if parameters["detail"] not in {"synopsis", "decision", "full-entry"}:
            raise ValueError("detail must be synopsis, decision, or full-entry")
        if parameters["semantic_gap_top_k"] not in {0, 3, 6}:
            raise ValueError("semantic_gap_top_k must be 0, 3, or 6")
        for key in ("include_non_authoritative", "include_pending", "include_rejected", "include_no_change"):
            if not isinstance(parameters[key], bool):
                raise ValueError(f"{key} must be boolean")
    if family == "timeline":
        if parameters["graph_depth"] not in {1, 2}:
            raise ValueError("timeline graph_depth must be 1 or 2")
        if not isinstance(parameters["edge_types"], list) or not parameters["edge_types"]:
            raise ValueError("timeline edge_types must be a non-empty list")
        allowed_edges = {"related", "replaces", "evolves", "branch"}
        if not set(parameters["edge_types"]) <= allowed_edges:
            raise ValueError("timeline edge_types contains an unsupported edge")
        parameters["edge_types"] = sorted(set(parameters["edge_types"]))
        if parameters["max_entries"] < 1:
            raise ValueError("timeline max_entries must be positive")
    if family == "search" and parameters["top_k"] < 1:
        raise ValueError("search top_k must be positive")
    if family == "retrieval-v1":
        if parameters["related_depth"] not in {1, 2, 3, 4, 5}:
            raise ValueError("retrieval-v1 related_depth must be from 1 through 5")
        if parameters["neighbouring_entries"] < 1:
            raise ValueError("retrieval-v1 neighbouring_entries must be positive")
    return {"schema": STRATEGY_SCHEMA, "family": family, "parameters": parameters}


def strategy_fingerprint(strategy: Mapping[str, Any]) -> str:
    return fingerprint(normalize_strategy(strategy))


def strategy_grid() -> list[dict[str, Any]]:
    """Return the frozen baseline and ADR candidate parameter grid."""
    result: list[dict[str, Any]] = []
    for top_k in (4, 8, 16):
        result.append({
            "schema": STRATEGY_SCHEMA, "strategy_id": f"search-k{top_k}",
            "family": "search", "parameters": {**DEFAULTS["search"], "top_k": top_k},
        })
    for depth, edge_types, sections, entry_limit in product(
        (1, 2),
        (["related", "replaces", "evolves", "branch"], ["replaces", "evolves"], ["related"]),
        (False, True),
        (8, 20, 40),
    ):
        parameters = {
            **DEFAULTS["timeline"], "graph_depth": depth,
            "edge_types": list(edge_types), "include_sections": sections,
            "max_entries": entry_limit,
        }
        normalized = {"schema": STRATEGY_SCHEMA, "family": "timeline", "parameters": parameters}
        result.append({**normalized, "strategy_id": "timeline-" + fingerprint(normalized).split(":", 1)[1][:16]})
    for related, neighbours, entries, tokens in product((1, 2, 3), (1, 4, 8), (20, 40), (2_000, 4_000, 8_000, 16_000)):
        parameters = {
            **DEFAULTS["retrieval-v1"], "related_depth": related,
            "neighbouring_entries": neighbours, "max_items": entries,
            "max_tokens": tokens,
        }
        normalized = {"schema": STRATEGY_SCHEMA, "family": "retrieval-v1", "parameters": parameters}
        result.append({**normalized, "strategy_id": "retrieval-v1-" + fingerprint(normalized).split(":", 1)[1][:16]})
    for family in ("oracle",):
        result.append({
            "schema": STRATEGY_SCHEMA,
            "strategy_id": f"{family}-current",
            "family": family,
            "parameters": dict(DEFAULTS[family]),
        })
    common = list(product(
        ("current", "accepted", "full"),
        (0, 1, 2, "all"),
        ("ancestor", "both"),
        (False, True),
        (0, 1, 2),
        ("synopsis", "decision", "full-entry"),
        ((8, 2_000), (16, 4_000), (32, 8_000), (40, 16_000)),
    ))
    for family in ("adr-structural", "adr-hybrid"):
        semantic_values = (0,) if family == "adr-structural" else (0, 3, 6)
        for values in common:
            scope, depth, direction, nonauth, related, detail, budget = values
            pending = rejected = no_change = nonauth
            item_limit, token_limit = budget
            for semantic in semantic_values:
                parameters = {
                    "scope": scope, "lineage_depth": depth,
                    "lineage_direction": direction,
                    "include_non_authoritative": nonauth,
                    "include_pending": pending,
                    "include_rejected": rejected,
                    "include_no_change": no_change,
                    "related_depth": related, "detail": detail,
                    "semantic_gap_top_k": semantic,
                    "max_items": item_limit, "max_tokens": token_limit,
                }
                normalized = {"schema": STRATEGY_SCHEMA, "family": family, "parameters": parameters}
                fp = fingerprint(normalized).split(":", 1)[1][:16]
                result.append({**normalized, "strategy_id": f"{family}-{fp}"})
        # Isolated probes make each non-authoritative state observable without
        # multiplying the full factorial by three additional boolean axes.
        for label, flags in (
            ("pending", (True, False, False)),
            ("rejected", (False, True, False)),
            ("no-change", (False, False, True)),
        ):
            pending, rejected, no_change = flags
            parameters = {
                **DEFAULTS[family], "include_pending": pending,
                "include_rejected": rejected, "include_no_change": no_change,
            }
            normalized = {"schema": STRATEGY_SCHEMA, "family": family, "parameters": parameters}
            result.append({**normalized, "strategy_id": f"{family}-{label}"})
    return list({strategy_fingerprint(item): item for item in result}.values())


def _task_hints(task: Mapping[str, Any]) -> Mapping[str, Any]:
    hints = task.get("resolver_hints", {})
    return hints if isinstance(hints, Mapping) else {}


def _query(task: Mapping[str, Any]) -> str:
    hints = _task_hints(task)
    terms = [str(task.get("question", ""))]
    for key in ("topics", "paths", "adr_ids", "decision_refs"):
        terms.extend(str(item) for item in hints.get(key, []) if isinstance(item, str))
    return " ".join(terms)


def _root_records(task: Mapping[str, Any], corpus: ExperimentCorpus) -> list[AdrRecord]:
    hints = _task_hints(task)
    ids = {str(item) for item in hints.get("adr_ids", [])}
    explicit_identity = bool(ids or hints.get("decision_refs"))
    refs = {str(item) for item in hints.get("decision_refs", [])}
    topics = {str(item).lower() for item in hints.get("topics", [])}
    ids.update(adr_id for ref in refs for adr_id in corpus.adr_by_ref.get(ref, ()))
    records = [record for record in corpus.adrs if record.adr_id in ids]
    if explicit_identity:
        return sorted(records, key=lambda item: item.adr_id)
    if not records and topics:
        records = [record for record in corpus.adrs if topics & {item.lower() for item in record.topics}]
    if not records:
        query_terms = set(re.findall(r"[a-z0-9_-]+", _query(task).lower()))
        scored = []
        for record in corpus.adrs:
            haystack = {record.adr_id.lower(), *map(str.lower, record.topics)} | set(
                re.findall(r"[a-z0-9_-]+", record.title.lower())
            )
            score = len(query_terms & haystack)
            if score:
                scored.append((score, record.adr_id, record))
        records = [item[2] for item in sorted(scored, key=lambda x: (-x[0], x[1]))]
    return sorted(records, key=lambda item: item.adr_id)


def _record_refs(record: AdrRecord, parameters: Mapping[str, Any]) -> set[str]:
    state = record.state
    scope = parameters["scope"]
    if scope == "current":
        refs = {state.authoritative_decision} if state.authoritative_decision else set()
    elif scope == "accepted":
        refs = {ref for ref, status in state.revision_statuses.items() if status == "accepted"}
    else:
        refs = set(adr_membership(record))
    if parameters["include_non_authoritative"] or parameters["include_pending"]:
        refs.update(state.pending_decisions)
    if parameters["include_non_authoritative"] or parameters["include_rejected"]:
        refs.update(state.rejected_decisions)
    return {ref for ref in refs if ref}


def _adr_edges(record: AdrRecord) -> list[dict[str, str]]:
    edges: list[dict[str, str]] = []
    for event in record.events:
        if event.kind != "revision-proposed" or not event.decision_ref:
            continue
        for predecessor in event.predecessors:
            match = _RELATION_RE.fullmatch(predecessor.relation_assertion)
            edge = {
                "source": event.decision_ref,
                "target": predecessor.decision,
                "type": match.group("type") if match else "evolves",
            }
            edges.append(edge)
    return _dedupe_dicts(edges)


def _dedupe_dicts(items: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique = {canonical_json(dict(item)): dict(item) for item in items}
    return [unique[key] for key in sorted(unique)]


def _lineage_closure(
    roots: set[str], edges: Sequence[Mapping[str, str]], depth: int | str, direction: str
) -> tuple[set[str], list[dict[str, str]]]:
    selected, frontier = set(roots), set(roots)
    used: list[dict[str, str]] = []
    remaining = None if depth == "all" else int(depth)
    while frontier and (remaining is None or remaining > 0):
        next_frontier: set[str] = set()
        for edge in edges:
            source, target = edge["source"], edge["target"]
            matched = source in frontier
            if direction == "both":
                matched = matched or target in frontier
            if not matched:
                continue
            used.append(dict(edge))
            for ref in (source, target):
                if ref not in selected:
                    selected.add(ref)
                    next_frontier.add(ref)
        frontier = next_frontier
        if remaining is not None:
            remaining -= 1
    return selected, _dedupe_dicts(used)


def _related_closure(
    roots: set[str], corpus: ExperimentCorpus, depth: int
) -> tuple[set[str], list[dict[str, str]]]:
    entries = {ref.rsplit(":", 1)[0] for ref in roots}
    seen, frontier, edges = set(entries), set(entries), []
    for _ in range(depth):
        upcoming: set[str] = set()
        for entry_id in sorted(frontier):
            node = corpus.graph.get(entry_id)
            if not node:
                continue
            for target in sorted(set(node.outbound)):
                edges.append({"source": entry_id, "target": target, "type": "related"})
                if target not in seen:
                    seen.add(target)
                    upcoming.add(target)
            for source in sorted(set(node.inbound)):
                edges.append({"source": source, "target": entry_id, "type": "related"})
                if source not in seen:
                    seen.add(source)
                    upcoming.add(source)
        frontier = upcoming
    refs = {ref for ref in corpus.decisions if ref.rsplit(":", 1)[0] in seen}
    return refs, _dedupe_dicts(edges)


def _chunk_evidence(chunk: MemoryChunk, selected_by: str, *, full: bool = True) -> dict[str, Any]:
    text = chunk.text if full else (chunk.title or chunk.entry_title or chunk.entry_id or "")
    return {
        "ref": chunk.entry_id or chunk.chunk_id,
        "kind": "entry",
        "source": chunk.source_path,
        "chunk_id": chunk.chunk_id,
        "session_date": chunk.session_date.isoformat(),
        "selected_by": [selected_by],
        "text": text,
        "token_proxy": _token_proxy(text),
    }


def _decision_evidence(
    item: DecisionEvidence, corpus: ExperimentCorpus, selected_by: str, detail: str
) -> dict[str, Any]:
    chunk = corpus.by_entry[item.entry_id]
    if detail == "synopsis":
        text = item.text.splitlines()[0] if item.text else item.ref
    elif detail == "full-entry":
        text = chunk.text
    else:
        text = item.text
    return {
        "ref": item.ref, "kind": "decision", "source": item.source,
        "chunk_id": item.chunk_id, "session_date": item.session_date,
        "selected_by": [selected_by], "text": text,
        "token_proxy": _token_proxy(text),
    }


def _token_proxy(text: str) -> int:
    return max(1, (len(text.encode("utf-8")) + 3) // 4)


def _limit(items: Sequence[dict[str, Any]], max_items: int, max_tokens: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected, omitted, tokens = [], [], 0
    seen: set[str] = set()
    for item in items:
        identity = f"{item['kind']}:{item['ref']}"
        if identity in seen:
            continue
        seen.add(identity)
        reason = None
        if len(selected) >= max_items:
            reason = "item-limit"
        elif tokens + int(item["token_proxy"]) > max_tokens:
            reason = "token-limit"
        if reason:
            omitted.append({"ref": item["ref"], "reason": reason, "token_proxy": item["token_proxy"]})
        else:
            selected.append(item)
            tokens += int(item["token_proxy"])
    return selected, omitted


def _baseline_refs(task: Mapping[str, Any], corpus: ExperimentCorpus, family: str, parameters: Mapping[str, Any]) -> tuple[set[str], list[dict[str, Any]]]:
    query = _query(task)
    selected = [item.chunk for item in rank_session_memory(
        query, corpus.root, top_k=int(parameters.get("top_k", 8)),
        embedding_provider=None, chunks=corpus.chunks,
        supersession_damping=True, replacing_successor_boost=True,
    )]
    refs = {ref for ref in corpus.decisions if ref.rsplit(":", 1)[0] in {c.entry_id for c in selected}}
    evidence = [_chunk_evidence(chunk, family) for chunk in selected]
    return refs, evidence


def _timeline_builder() -> Any:
    try:
        from memory_trace.evidence import build_timeline_evidence_pack
    except ModuleNotFoundError:
        # Source checkouts keep the companion distribution in a sibling folder.
        import sys

        companion = Path(__file__).resolve().parents[2] / "memory-trace"
        if str(companion) not in sys.path:
            sys.path.insert(0, str(companion))
        from memory_trace.evidence import build_timeline_evidence_pack
    return build_timeline_evidence_pack


@lru_cache(maxsize=256)
def _timeline_pack(root: str, arguments_json: str) -> Mapping[str, Any]:
    import json

    return _timeline_builder()(root, **json.loads(arguments_json))


def _timeline_baseline(
    task: Mapping[str, Any], corpus: ExperimentCorpus, parameters: Mapping[str, Any]
) -> tuple[set[str], list[dict[str, Any]], list[dict[str, str]], list[dict[str, Any]]]:
    hints = _task_hints(task)
    root_entries = sorted({str(ref).rsplit(":", 1)[0] for ref in hints.get("decision_refs", [])})
    arguments = {
        "topic": next(iter(hints.get("topics", [])), None),
        "graph_entry_id": root_entries[0] if root_entries else None,
        "graph_depth": int(parameters["graph_depth"]),
        "edge_types": list(parameters["edge_types"]),
        "include_sections": bool(parameters["include_sections"]),
        "max_entries": int(parameters["max_entries"]),
    }
    pack = _timeline_pack(str(corpus.root), canonical_json(arguments))
    evidence, refs = [], set()
    for item in pack.get("entries", []):
        text = str(item.get("text", ""))
        entry_id = str(item.get("entry_id", ""))
        evidence.append({
            "ref": entry_id, "kind": "entry", "source": item.get("path"),
            "chunk_id": item.get("chunk_id"), "session_date": item.get("session_date"),
            "selected_by": ["timeline"], "text": text, "token_proxy": _token_proxy(text),
        })
        refs.update(ref for ref in corpus.decisions if ref.rsplit(":", 1)[0] == entry_id)
    for item in pack.get("chunks", []):
        text = str(item.get("text", ""))
        evidence.append({
            "ref": str(item.get("chunk_id", "")), "kind": "section", "source": item.get("path"),
            "chunk_id": item.get("chunk_id"), "session_date": item.get("session_date"),
            "selected_by": ["timeline"], "text": text, "token_proxy": _token_proxy(text),
        })
    edges = [dict(edge) for edge in pack.get("graph", {}).get("edges", [])]
    absence = [dict(item) for item in pack.get("missing_evidence", [])]
    return refs, evidence, edges, absence


@lru_cache(maxsize=256)
def _retrieval_v1_pack(root: str, spec_json: str) -> Mapping[str, Any]:
    import json

    return resolve_retrieval_spec(json.loads(spec_json), root)


def _retrieval_v1_baseline(
    task: Mapping[str, Any], corpus: ExperimentCorpus, parameters: Mapping[str, Any]
) -> tuple[set[str], list[dict[str, Any]], list[dict[str, Any]]]:
    hints = _task_hints(task)
    spec = {
        "schema": "memory-seed/retrieval-spec", "version": 1,
        "required": {
            "constitution": True,
            "related_decisions": {"depth": int(parameters["related_depth"])},
            "evidence": {"mode": "latest"},
        },
        "optional": {"sessions": {"neighbouring_entries": int(parameters["neighbouring_entries"])}},
        "filters": {
            "topics": [str(item) for item in hints.get("topics", [])],
            "paths": [str(item) for item in hints.get("paths", [])],
        },
        "limits": {"max_entries": int(parameters["max_items"]), "max_tokens": int(parameters["max_tokens"])},
        "output": {"include_resolution_trace": False, "include_excerpts": True},
    }
    try:
        pack = _retrieval_v1_pack(str(corpus.root), canonical_json(spec))
    except (RetrievalSpecResolutionError, ValueError) as exc:
        code = exc.code if isinstance(exc, RetrievalSpecResolutionError) else type(exc).__name__
        return set(), [], [{"kind": "retrieval-v1-missing", "code": code, "refs": []}]
    refs, evidence = set(), []
    for item in pack.get("evidence", []):
        ref = str(item.get("ref", ""))
        if ref in corpus.decisions:
            refs.add(ref)
            value = _decision_evidence(corpus.decisions[ref], corpus, "retrieval-v1", "decision")
        else:
            entry_id = ref.split(":", 1)[0]
            chunk = corpus.by_entry.get(entry_id)
            if chunk is not None:
                value = _chunk_evidence(chunk, "retrieval-v1")
                refs.update(candidate for candidate in corpus.decisions if candidate.rsplit(":", 1)[0] == entry_id)
            else:
                text = str(item.get("excerpt") or "")
                value = {
                    "ref": ref, "kind": str(item.get("kind", "markdown")),
                    "source": item.get("source"), "chunk_id": item.get("chunk_id"),
                    "session_date": item.get("session_date"), "selected_by": ["retrieval-v1"],
                    "text": text, "token_proxy": int(item.get("token_estimate") or _token_proxy(text)),
                }
        evidence.append(value)
    return refs, evidence, []


def resolve_strategy(
    task: Mapping[str, Any], strategy: Mapping[str, Any], cwd: str | Path = ".",
    *, corpus: ExperimentCorpus | None = None,
) -> dict[str, Any]:
    """Resolve one task through one strategy into the common result envelope."""
    started = time.perf_counter()
    normalized = normalize_strategy(strategy)
    sfp = fingerprint(normalized)
    corpus = corpus or load_corpus(cwd)
    family, parameters = normalized["family"], normalized["parameters"]
    selected_records: list[AdrRecord] = []
    refs: set[str] = set()
    typed_edges: list[dict[str, str]] = []
    evidence: list[dict[str, Any]] = []
    resolution_absence: list[dict[str, Any]] = []

    if family in {"search", "timeline", "retrieval-v1"}:
        if family == "timeline":
            refs, evidence, typed_edges, resolution_absence = _timeline_baseline(task, corpus, parameters)
        elif family == "retrieval-v1":
            refs, evidence, resolution_absence = _retrieval_v1_baseline(task, corpus, parameters)
        else:
            refs, evidence = _baseline_refs(task, corpus, family, parameters)
        selected_records = sorted(
            {
                adr_id: corpus.adr_by_id[adr_id]
                for ref in refs for adr_id in corpus.adr_by_ref.get(ref, ())
            }.values(),
            key=lambda record: record.adr_id,
        )
    else:
        if family == "oracle":
            hints = _task_hints(task)
            exact_ids = {str(item) for item in hints.get("adr_ids", [])}
            for ref in hints.get("decision_refs", []):
                exact_ids.update(corpus.adr_by_ref.get(str(ref), ()))
            selected_records = [corpus.adr_by_id[item] for item in sorted(exact_ids) if item in corpus.adr_by_id]
            refs = {str(item) for item in _task_hints(task).get("decision_refs", [])}
            for record in selected_records:
                refs.update(_record_refs(record, {**DEFAULTS["adr-structural"], "scope": "full", "include_non_authoritative": True}))
            all_edges = [edge for record in corpus.adrs for edge in _adr_edges(record)]
            typed_edges = [edge for edge in all_edges if edge["source"] in refs or edge["target"] in refs]
        else:
            selected_records = _root_records(task, corpus)
            refs = {ref for record in selected_records for ref in _record_refs(record, parameters)}
            all_edges = [edge for record in corpus.adrs for edge in _adr_edges(record)]
            refs, typed_edges = _lineage_closure(
                refs, all_edges, parameters["lineage_depth"], parameters["lineage_direction"]
            )
            related_refs, related_edges = _related_closure(refs, corpus, int(parameters["related_depth"]))
            refs.update(related_refs)
            typed_edges.extend(related_edges)
        if family in {"adr-structural", "adr-hybrid"}:
            # Supporting refs are source evidence, not lineage.  Include them
            # for every selected revision so a dangling support claim becomes
            # an explicit material absence instead of silently disappearing.
            supporting_refs = {
                supporting
                for record in selected_records
                for event in record.events
                if event.kind == "revision-proposed" and event.decision_ref in refs
                for supporting in event.supporting_decisions
            }
            refs.update(supporting_refs)
        detail = parameters["detail"]
        evidence = [
            _decision_evidence(corpus.decisions[ref], corpus, family, detail)
            for ref in sorted(refs) if ref in corpus.decisions
        ]
        if parameters.get("include_no_change", False):
            for record in selected_records:
                for event in record.events:
                    if event.kind != "reviewed-no-change":
                        continue
                    text = event.reason or "Reviewed with no architectural change."
                    evidence.append({
                        "ref": f"{record.adr_id}#{event.event_id}",
                        "kind": "adr-event", "source": str(record.path) if record.path else None,
                        "chunk_id": None, "session_date": event.timestamp[:10],
                        "selected_by": [family, "reviewed-no-change"],
                        "text": text, "token_proxy": _token_proxy(text),
                    })
        top_k = int(parameters.get("semantic_gap_top_k", 0))
        if family == "adr-hybrid" and top_k:
            selected_entries = {ref.rsplit(":", 1)[0] for ref in refs}
            ranked = rank_session_memory(
                _query(task), corpus.root, top_k=max(top_k * 3, top_k),
                embedding_provider=None, chunks=corpus.chunks,
                supersession_damping=True, replacing_successor_boost=True,
            )
            gap = [item.chunk for item in ranked if item.chunk.entry_id not in selected_entries][:top_k]
            evidence.extend(_chunk_evidence(chunk, "semantic-gap") for chunk in gap)
            refs.update(ref for ref in corpus.decisions if ref.rsplit(":", 1)[0] in {c.entry_id for c in gap})

    selected_records = sorted(
        {record.adr_id: record for record in [*selected_records, *(corpus.adr_by_id[a] for ref in refs for a in corpus.adr_by_ref.get(ref, ()))]}.values(),
        key=lambda record: record.adr_id,
    )
    evidence, omissions = _limit(evidence, int(parameters["max_items"]), int(parameters["max_tokens"]))
    included_entries = {str(item["ref"]) for item in evidence if item["kind"] == "entry"}
    included_decisions = {str(item["ref"]) for item in evidence if item["kind"] == "decision"}
    included_refs = sorted(
        ref for ref in refs
        if ref in included_decisions or ref.rsplit(":", 1)[0] in included_entries
    )
    missing = sorted(ref for ref in refs if ref not in corpus.decisions)
    hints = _task_hints(task)
    expected_refs = {str(item) for item in hints.get("decision_refs", [])}
    absence = list(resolution_absence)
    if missing:
        absence.append({"kind": "missing-decision-evidence", "refs": missing})
    if expected_refs and not (expected_refs & set(included_refs)):
        absence.append({"kind": "no-hinted-evidence", "refs": sorted(expected_refs)})
    if not evidence:
        absence.append({"kind": "no-evidence", "refs": []})
    result: dict[str, Any] = {
        "schema": RESULT_SCHEMA,
        "task_id": task.get("task_id"),
        "strategy": normalized,
        "strategy_fingerprint": sfp,
        "selected_adrs": [
            {"adr_id": record.adr_id, "status": record.current_status,
             "authoritative_ref": record.authoritative_decision}
            for record in selected_records
        ],
        "selected_refs": included_refs,
        "typed_edges": _dedupe_dicts(typed_edges),
        "lineage_edges": _dedupe_dicts(edge for edge in typed_edges if edge["type"] in LINEAGE_TYPES),
        "related_edges": _dedupe_dicts(edge for edge in typed_edges if edge["type"] == "related"),
        "evidence": evidence,
        "omissions": omissions,
        "absence": absence,
        "insufficient_evidence": bool(absence),
        "token_proxy": sum(int(item["token_proxy"]) for item in evidence),
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 6),
    }
    stable = {key: value for key, value in result.items() if key not in {"elapsed_ms", "fingerprint"}}
    result["fingerprint"] = fingerprint(stable)
    return result


def stable_result(result: Mapping[str, Any]) -> dict[str, Any]:
    """Projection used by the sweep's repeatability gate."""
    return {key: value for key, value in result.items() if key != "elapsed_ms"}


def strategy_manifest(*, families: Sequence[str] | None = None) -> dict[str, Any]:
    """Build the executable normalized/deduplicated sweep manifest."""
    wanted = set(families or FAMILIES)
    unknown = wanted - set(FAMILIES)
    if unknown:
        raise ValueError("unknown strategy families: " + ", ".join(sorted(unknown)))
    rows = []
    for strategy in strategy_grid():
        if strategy["family"] not in wanted:
            continue
        normalized = normalize_strategy(strategy)
        rows.append({
            **normalized,
            "strategy_id": strategy["strategy_id"],
            "strategy_fingerprint": fingerprint(normalized),
        })
    rows.sort(key=lambda item: item["strategy_fingerprint"])
    return {"schema": "context-strategy-manifest.v1", "strategies": rows}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Emit the frozen context strategy manifest")
    parser.add_argument("--family", action="append", choices=FAMILIES)
    args = parser.parse_args(argv)
    print(canonical_json(strategy_manifest(families=args.family)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

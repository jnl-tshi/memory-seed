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

import hashlib
import json
import re
import time
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Iterable, Mapping, Sequence

from .corpus_cache import CorpusSnapshot, get_corpus_snapshot

if TYPE_CHECKING:
    from .core import DecisionSummary

from .semantic_cache import (
    RECENCY_FLOOR,
    EmbeddingProvider,
    MemoryChunk,
    Model2VecEmbeddingProvider,
    RankedMemoryChunk,
    build_related_entry_graph,
    evolves_lineage_heads,
    extract_memory_chunks,
    rank_session_memory,
    replacing_lineage_heads,
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
    recency_floor: float = RECENCY_FLOOR,
    semantic_enabled: bool = True,
    embedding_provider: Any = None,
    granularity: str = "decision",
    user: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    exclude_replaced: bool = False,
    supersession_damping: bool = True,
    replacing_successor_boost: bool = True,
    attention_boost: bool = False,
    topics: list[str] | None = None,
    snapshot: "CorpusSnapshot | None" = None,
) -> dict[str, Any]:
    """Search session memory and return the canonical result payload.

    This is the full orchestration the MCP `memory_search` tool exposes:
    semantic-provider resolution (with lexical fallback), shared ranking via
    `rank_session_memory`, and `format_search_results` formatting. Non-MCP
    consumers call this directly and get identical answers.

    ``supersession_damping`` (freshness-aware-memory-ranking-proposal.md) is the
    supersession rank-dampener, ON by default: an entry with a non-empty
    ``replaced_by`` (drawn from the sidecar-augmented graph below) is
    multiplicatively down-ranked so a live replacement out-ranks the decision it
    retires. It only re-orders - it never hard-excludes (that stays
    ``exclude_replaced``) and never hides an entry: a replaced entry stays
    fully retrievable, just lower. Pass ``False`` to restore full-weight ordering.
    Graduated to default-on after validation on the real corpus (both YAML- and
    sidecar-authored supersession lineages surfaced the live replacement above the
    decisions it retired, with no effect on queries lacking a replaced hit).

    ``replacing_successor_boost`` is the separate, bounded successor-lift
    signal from supersession-successor-surfacing-proposal.md. It is ON by
    default here after fixture coverage plus the real-corpus ``ranking-ab`` gate
    passed. Pass ``False`` to restore damp-only ordering. Even when enabled,
    only terminal live replacements that already match the query can be lifted;
    nothing is hard-injected.

    ``attention_boost`` (attention-retrieval-signal-proposal.md) folds the
    decayed fetch-frequency signal into ranking. OFF by default and stays off
    until `memory-seed ranking-ab --signal attention` passes on real accumulated
    usage - until then the signal is exposure-only (`attention_score` /
    `fetch_count` / `last_fetch` on every result row).
    """
    provider, provider_name, fallback_reason = resolve_semantic_provider(
        query,
        embedding_provider,
        enabled=semantic_enabled,
    )
    chunks = load_corpus(cwd, granularity, snapshot=snapshot)
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
        exclude_replaced=exclude_replaced,
        supersession_damping=supersession_damping,
        replacing_successor_boost=replacing_successor_boost,
        attention_boost=attention_boost,
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
    # Mechanical relevance classification: the tool, not the model, decides whether a
    # result is a real match. Bands come from the score distribution (absolute floor plus
    # the gap to the pack), so "not recorded" becomes a tool-reported fact an agent may
    # repeat rather than a judgement it has to make from raw floats.
    _classify_relevance(payload)
    # Attention exposure (attention-retrieval-signal-proposal.md): decayed
    # fetch-frequency per entry, shown beside the lifecycle heads so "most
    # looked-at" and "most evolved" read side by side. Read-only metadata in the
    # importance_score mould - computed, surfaced, and deliberately NOT blended
    # into default ranking until the ranking-ab gate passes ("expose before you
    # rank", Constitution §3).
    from .attention import load_attention
    from .core import resolve_runtime as _resolve_runtime

    attention = load_attention(_resolve_runtime(cwd).memory_dir)
    for result in payload["results"]:
        entry_id = result.get("entry_id") or ""
        node = graph.get(entry_id)
        attended = attention.get(entry_id)
        result["attention_score"] = attended["attention_score"] if attended else 0.0
        result["fetch_count"] = attended["fetch_count"] if attended else 0
        result["last_fetch"] = attended["last_fetch"] if attended else None
        result["replaced_by"] = list(node.replaced_by) if node else []
        result["replacing_head"] = list(replacing_lineage_heads(graph, entry_id))
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


# INERT as of 2026-08-05. BM25F derives term rarity from the corpus, so a chunk's score now
# depends on how much is stored - the same chunk scores lower in a 7-entry fixture than in a
# 1259-chunk store. An ABSOLUTE floor cannot survive that, on top of already being uncalibrated
# (it banded 34 of 34 negatives answerable). Set to 0.0 so the band stops making a threshold claim
# in either direction rather than swapping "everything is strong" for "everything is no-match",
# which is what 6.0 became under the new scorer. The replacement is `top_over_median`, which is
# scale-free by construction and measured at 0.87 held-out balanced accuracy - it needs refitting
# against the BM25F distribution before it ships.
RELEVANCE_FLOOR = 0.0
RELEVANCE_STRONG_RATIO = 0.55


def _classify_relevance(payload: dict[str, Any]) -> None:
    """Attach `relevance` per result and `no_match_above_threshold` to the payload.

    Deterministic and explainable (Constitution §3 - a stated rule, not a hidden score):
    a result is `strong` when it clears an absolute floor AND holds at least
    RELEVANCE_STRONG_RATIO of the top score; `weak` when it clears the floor only; `none`
    otherwise.

    UNCALIBRATED as of 2026-08-05. Measured on the 836-entry corpus, these thresholds do not
    discriminate: nonsense queries return results banded `strong`, and `no_match_above_threshold`
    fired for zero of twelve probe queries, with semantic ranking on or off. Neither the absolute
    score nor the top-versus-pack gap separated real queries from nonsense. The constants were set
    against a 7-entry fixture where every result banded `strong` and the answer was present anyway,
    which hid the saturation. The payload therefore carries `relevance_calibrated: False` and
    consumers must judge relevance from the served content; see
    `experiments/decision-retrieval-scale/` for the distribution the recalibration needs.
    """
    results = payload.get("results") or []
    if not results:
        payload["no_match_above_threshold"] = True
        payload["relevance_rule"] = (
            f"strong: score >= {RELEVANCE_FLOOR} and >= {RELEVANCE_STRONG_RATIO:.0%} of top; "
            f"weak: score >= {RELEVANCE_FLOOR}; else none"
        )
        payload["relevance_calibrated"] = False
        return
    top = max(float(row.get("score") or 0.0) for row in results)
    for row in results:
        score = float(row.get("score") or 0.0)
        if score >= RELEVANCE_FLOOR and top > 0 and score >= RELEVANCE_STRONG_RATIO * top:
            row["relevance"] = "strong"
        elif score >= RELEVANCE_FLOOR:
            row["relevance"] = "weak"
        else:
            row["relevance"] = "none"
    payload["no_match_above_threshold"] = not any(
        row.get("relevance") == "strong" for row in results
    )
    payload["relevance_rule"] = (
        f"strong: score >= {RELEVANCE_FLOOR} and >= {RELEVANCE_STRONG_RATIO:.0%} of top; "
        f"weak: score >= {RELEVANCE_FLOOR}; else none"
    )
    payload["relevance_calibrated"] = False


def get_chunk(chunk_id: str, cwd: str | Path = ".", *, include_diagrams: bool = False) -> dict[str, Any]:
    """Fetch one chunk by ``chunk_id`` and return its canonical payload dict,
    enriched with the read-only graph metrics from docs/3_Spec/graph-edge-contract.md
    (`replaced_by`, `inbound_relation_count`, `importance_score`,
    `commit_reference_count`). Raises ``ValueError`` for an unknown id.

    ``include_diagrams=True`` additionally attaches ``diagrams``: authored
    decision-diagram sidecar metadata for the chunk's entry (see
    `entry_diagram_sidecars`). Off by default so the MCP tool contract is
    unchanged; Explorer/Trail consumers opt in.
    """
    entry_chunks = augment_chunks_with_topic_sidecars(
        augment_chunks_with_link_sidecars(extract_memory_chunks(cwd, granularity="entry"), cwd),
        cwd,
    )
    found = next((chunk for chunk in entry_chunks if chunk.chunk_id == chunk_id), None)
    if found is None:
        section_chunks = augment_chunks_with_topic_sidecars(
            augment_chunks_with_link_sidecars(
                extract_memory_chunks(cwd, granularity="section"),
                cwd,
            ),
            cwd,
        )
        found = next((chunk for chunk in section_chunks if chunk.chunk_id == chunk_id), None)
    if found is None:
        # Decision chunks were unreachable here until 2026-08-06, which made two shipped behaviours
        # dead letters: the truncation marker on a long decision reads "call memory_get_chunk for
        # the full decision" and that call raised, and the attention layer scores on
        # `memory_get_chunk` fetches, so no decision chunk could ever register one. Searched last
        # because entry and section ids are more common and cheaper to match.
        decision_chunks = augment_chunks_with_topic_sidecars(
            augment_chunks_with_link_sidecars(
                extract_memory_chunks(cwd, granularity="decision"),
                cwd,
            ),
            cwd,
        )
        found = next((chunk for chunk in decision_chunks if chunk.chunk_id == chunk_id), None)
    if found is None:
        raise ValueError(f"chunk_id not found: {chunk_id}")
    payload = chunk_to_dict(found)
    # A decision fetched on its own arrives without the entry that frames it. Attach the entry's
    # non-decision sections - Summary, Follow-up, Validation, Facts, whatever the author wrote at
    # entry level - so the caller sees the decision in the context it was recorded in rather than a
    # bare D/R/A/F/T block. Sibling decisions are NOT included: the container is excluded, so asking
    # for :d1 does not drag :d2 along with it.
    payload["entry_context"] = []
    if found.granularity == "decision" and found.entry_id:
        parent = next((c for c in entry_chunks if c.chunk_id == found.entry_id), None)
        if parent is not None:
            payload["entry_context"] = entry_context_sections(parent.text or "")
    replaced_by: list[str] = []
    replacing_head: list[str] = []
    evolved_by: list[str] = []
    inbound_relation_count = 0
    importance_score = 0.0
    graph = build_related_entry_graph(chunks=entry_chunks)
    if found.entry_id:
        node = graph.get(found.entry_id)
        if node is not None:
            replaced_by = list(node.replaced_by)
            replacing_head = list(replacing_lineage_heads(graph, found.entry_id))
            # Read-time-only inverse of evolves: newer entries that extend this
            # decision while it stays valid. Never stored, never dampens.
            evolved_by = list(node.evolved_by)
            # How many other entries reference this one via related_entries
            # (inbound backlinks only) - the raw signal importance_score is
            # built on. Distinct from Lense's `connectivity`, which counts
            # combined inbound+outbound edges for node sizing.
            inbound_relation_count = len(node.inbound)
            # inbound_relation_count dampened when this entry is replaced
            # (read-only; not blended into default search ranking).
            importance_score = node.importance_score
    commit_reference_count = 0
    if found.entry_id:
        from .core import commit_reference_ids, resolve_runtime

        commit_reference_count = len(
            commit_reference_ids(resolve_runtime(cwd).workspace_root, found.entry_id, found.commits)
        )
    payload["replaced_by"] = replaced_by
    payload["replacing_head"] = replacing_head
    payload["evolved_by"] = evolved_by
    payload["inbound_relation_count"] = inbound_relation_count
    payload["importance_score"] = importance_score
    payload["commit_reference_count"] = commit_reference_count
    # Attention exposure - same read-only contract as importance_score above.
    from .attention import load_attention
    from .core import resolve_runtime as _resolve_runtime

    attended = load_attention(_resolve_runtime(cwd).memory_dir).get(found.entry_id or "")
    payload["attention_score"] = attended["attention_score"] if attended else 0.0
    payload["fetch_count"] = attended["fetch_count"] if attended else 0
    payload["last_fetch"] = attended["last_fetch"] if attended else None
    if include_diagrams:
        sidecar = entry_diagram_sidecars(cwd).get(found.entry_id or "")
        payload["diagrams"] = [sidecar] if sidecar else []
    return payload


RETRIEVAL_RESOLVER_VERSION = 1
RETRIEVAL_PREVIEW_SCHEMA = "memory-seed/retrieval-spec-preview"
EVIDENCE_PACK_SCHEMA = "memory-seed/evidence-pack"
EVIDENCE_PACK_VERSION = 1
DEFAULT_RETRIEVAL_TIMEOUT_MS = 5_000
_RETRIEVAL_REQUIRED_CLAUSES = (
    "required.constitution",
    "required.related_decisions",
    "required.evidence",
)
_FORBIDDEN_RETRIEVAL_PATH_PARTS = frozenset(
    {".git", ".codex", ".claude", ".cursor", ".gemini"}
)


class RetrievalSpecResolutionError(RuntimeError):
    """Structured, fail-closed error from Retrieval Specification resolution."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        stage: str,
        completed_stages: Iterable[str] = (),
        details: Mapping[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.stage = stage
        self.completed_stages = tuple(completed_stages)
        self.details = dict(details or {})
        super().__init__(f"retrieval resolution {code} at {stage}: {message}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "stage": self.stage,
            "completed_stages": list(self.completed_stages),
            "details": self.details,
        }


@dataclass
class _RetrievalCandidate:
    ref: str
    kind: str
    source: str
    line_range: tuple[int, int]
    chunk_id: str | None
    session_date: str | None
    graph_distance: int | None
    text: str
    selected_by: set[str]
    reasons: set[str]

    @property
    def token_estimate(self) -> int:
        # Fixed local proxy. It is deliberately provider/tokenizer independent.
        return max(1, (len(self.text.encode("utf-8")) + 3) // 4)


def canonical_retrieval_json(payload: Mapping[str, Any]) -> str:
    """Canonical JSON shared byte-for-byte by CLI and MCP adapters."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _retrieval_corpus_revision(
    cwd: str | Path,
    normalized_spec: Mapping[str, Any],
) -> str:
    """Content-address the exact local Markdown families this resolver reads."""
    from .core import _git_text, resolve_runtime

    runtime = resolve_runtime(cwd)
    root = runtime.workspace_root.resolve()
    inputs: set[Path] = set()
    for constitution in (root / "docs" / "CONSTITUTION.md", root / "CONSTITUTION.md"):
        if constitution.is_file():
            inputs.add(constitution)
    topics_index = runtime.memory_dir / "topics.yaml"
    if topics_index.is_file():
        inputs.add(topics_index)
    sessions = runtime.memory_dir / "sessions"
    if sessions.is_dir():
        inputs.update(path for path in sessions.rglob("*.md") if path.is_file())
    for relative in normalized_spec["filters"]["paths"]:
        if any(
            part.lower() in _FORBIDDEN_RETRIEVAL_PATH_PARTS
            for part in Path(relative).parts
        ):
            continue
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        if candidate.is_file() and candidate.suffix.lower() == ".md":
            inputs.add(candidate)

    digest = hashlib.sha256()
    digest.update(b"memory-seed-retrieval-corpus-v1\0")
    for path in sorted(inputs, key=lambda item: item.as_posix()):
        try:
            relative = path.relative_to(root).as_posix()
        except ValueError:
            relative = path.as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        try:
            digest.update(path.read_bytes())
        except OSError as exc:
            digest.update(f"<unreadable:{type(exc).__name__}>".encode("utf-8"))
        digest.update(b"\0")
    code, head = _git_text(root, ("rev-parse", "HEAD"))
    content_revision = "sha256:" + digest.hexdigest()
    return f"git:{head}:{content_revision}" if code == 0 and head else content_revision


def _runtime_scoped_path(root: Path, relative: str) -> Path:
    parts = Path(relative).parts
    if any(part.lower() in _FORBIDDEN_RETRIEVAL_PATH_PARTS for part in parts):
        raise RetrievalSpecResolutionError(
            "forbidden_path",
            "path enters an agent or Git control directory",
            stage="path_filters",
            details={"path": relative},
        )
    target = (root / relative).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise RetrievalSpecResolutionError(
            "forbidden_path",
            "path resolves outside the active runtime",
            stage="path_filters",
            details={"path": relative},
        ) from exc
    return target


def _candidate_sort_key(candidate: _RetrievalCandidate) -> tuple[Any, ...]:
    required = any(clause.startswith("required.") for clause in candidate.selected_by)
    distance = -1 if candidate.graph_distance is None else candidate.graph_distance
    # ISO dates sort lexically; invert their integer representation for newest first.
    recency = -int(candidate.session_date.replace("-", "")) if candidate.session_date else 0
    return (0 if required else 1, distance, recency, candidate.ref)


def _merge_candidate(
    candidates: dict[str, _RetrievalCandidate],
    candidate: _RetrievalCandidate,
) -> None:
    existing = candidates.get(candidate.ref)
    if existing is None:
        candidates[candidate.ref] = candidate
        return
    existing.selected_by.update(candidate.selected_by)
    existing.reasons.update(candidate.reasons)
    if existing.graph_distance is None:
        existing.graph_distance = candidate.graph_distance
    elif candidate.graph_distance is not None:
        existing.graph_distance = min(existing.graph_distance, candidate.graph_distance)


def _decision_candidates(
    chunk: MemoryChunk,
    *,
    root: Path,
    source_lines: dict[str, tuple[str, ...]],
    selected_by: set[str],
    reasons: set[str],
    graph_distance: int,
    ordinals: set[str] | None = None,
) -> list[_RetrievalCandidate]:
    from .core import entry_body_decisions

    decisions = entry_body_decisions(chunk.text)
    if not decisions:
        return []
    path_lines = source_lines.get(chunk.source_path)
    if path_lines is None:
        source = _runtime_scoped_path(root, chunk.source_path)
        try:
            path_lines = tuple(source.read_text(encoding="utf-8").splitlines())
        except (OSError, UnicodeDecodeError) as exc:
            raise RetrievalSpecResolutionError(
                "unfetchable_ref",
                "canonical session Markdown is unreadable",
                stage="related_decisions",
                details={"source": chunk.source_path},
            ) from exc
        source_lines[chunk.source_path] = path_lines

    entry_start = max(0, chunk.start_line - 1)
    entry_end = min(len(path_lines), chunk.end_line)
    numbered: list[tuple[int, str]] = []
    singular: int | None = None
    for index in range(entry_start, entry_end):
        line = path_lines[index]
        match = re.match(r"^####\s+D(\d+)\s*[-–]", line)
        if match:
            numbered.append((index, f"d{int(match.group(1))}"))
        elif singular is None and re.match(r"^###\s+Decision\s*$", line):
            singular = index

    starts = numbered if numbered else ([(singular, "d1")] if singular is not None else [])
    spans: dict[str, tuple[int, int, str]] = {}
    for start, ordinal in starts:
        end = entry_end
        for index in range(start + 1, entry_end):
            if re.match(r"^#{2,4}\s", path_lines[index]):
                end = index
                break
        spans[ordinal] = (
            start + 1,
            max(start + 1, end),
            "\n".join(path_lines[start:end]),
        )

    multiple = len(decisions) > 1
    candidates: list[_RetrievalCandidate] = []
    for decision in decisions:
        if ordinals is not None and decision.ordinal not in ordinals:
            continue
        span = spans.get(decision.ordinal)
        if span is None:
            raise RetrievalSpecResolutionError(
                "unfetchable_ref",
                "canonical decision line range could not be resolved",
                stage="related_decisions",
                details={
                    "ref": f"{chunk.entry_id}:{decision.ordinal}",
                    "source": chunk.source_path,
                },
            )
        candidates.append(
            _RetrievalCandidate(
                ref=(
                    f"{chunk.entry_id}:{decision.ordinal}"
                    if multiple
                    else str(chunk.entry_id)
                ),
                kind="decision",
                source=chunk.source_path,
                line_range=(span[0], span[1]),
                # A decision is fetched by its exact canonical Markdown lines.
                # Reusing the entry chunk id here would fetch every decision in
                # the entry and invalidate both this estimate and pack bounds.
                chunk_id=None,
                session_date=chunk.session_date.isoformat(),
                graph_distance=graph_distance,
                text=span[2],
                selected_by=set(selected_by),
                reasons=set(reasons),
            )
        )
    return candidates


def _entry_candidate(
    chunk: MemoryChunk,
    *,
    selected_by: set[str],
    reasons: set[str],
    graph_distance: int,
) -> _RetrievalCandidate:
    return _RetrievalCandidate(
        ref=str(chunk.entry_id or chunk.chunk_id),
        kind="session",
        source=chunk.source_path,
        line_range=(chunk.start_line, chunk.end_line),
        chunk_id=chunk.chunk_id,
        session_date=chunk.session_date.isoformat(),
        graph_distance=graph_distance,
        text=chunk.text,
        selected_by=set(selected_by),
        reasons=set(reasons),
    )


def _check_retrieval_timeout(
    clock: Callable[[], float],
    started: float,
    timeout_ms: int,
    *,
    stage: str,
    completed_stages: list[str],
) -> None:
    if (clock() - started) * 1_000 <= timeout_ms:
        return
    raise RetrievalSpecResolutionError(
        "timeout",
        f"resolution exceeded the local {timeout_ms} ms deadline",
        stage=stage,
        completed_stages=completed_stages,
    )


def _build_retrieval_plan(
    normalized: Mapping[str, Any],
    cwd: str | Path,
    *,
    clock: Callable[[], float],
    started: float,
    timeout_ms: int,
) -> dict[str, Any]:
    from .core import resolve_runtime
    from .semantic_cache import _entry_file_refs
    from .topics import expand_topic_filter, load_topic_index

    completed: list[str] = []
    trace: list[dict[str, Any]] = []
    warnings: list[dict[str, str]] = []
    runtime = resolve_runtime(cwd)
    root = runtime.workspace_root.resolve()
    if not runtime.memory_dir.is_dir():
        raise RetrievalSpecResolutionError(
            "missing_required",
            "active .memory-seed runtime is absent",
            stage="runtime",
            completed_stages=completed,
            details={"clauses": list(_RETRIEVAL_REQUIRED_CLAUSES)},
        )
    completed.append("runtime")
    trace.append(
        {
            "stage": "runtime",
            "reader": "resolve_runtime",
            "workspace": root.as_posix(),
        }
    )
    _check_retrieval_timeout(
        clock, started, timeout_ms, stage="constitution", completed_stages=completed
    )

    candidates: dict[str, _RetrievalCandidate] = {}
    constitution_path = next(
        (
            path
            for path in (root / "docs" / "CONSTITUTION.md", root / "CONSTITUTION.md")
            if path.is_file()
        ),
        None,
    )
    if constitution_path is None:
        raise RetrievalSpecResolutionError(
            "missing_required",
            "canonical Constitution Markdown was not found",
            stage="constitution",
            completed_stages=completed,
            details={"clause": "required.constitution"},
        )
    try:
        constitution_text = constitution_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise RetrievalSpecResolutionError(
            "missing_required",
            "canonical Constitution Markdown is unreadable",
            stage="constitution",
            completed_stages=completed,
            details={"clause": "required.constitution"},
        ) from exc
    constitution_text = "\n".join(constitution_text.splitlines())
    constitution_source = constitution_path.relative_to(root).as_posix()
    _merge_candidate(
        candidates,
        _RetrievalCandidate(
            ref=constitution_source,
            kind="constitution",
            source=constitution_source,
            line_range=(1, max(1, len(constitution_text.splitlines()))),
            chunk_id=None,
            session_date=None,
            graph_distance=None,
            text=constitution_text,
            selected_by={"required.constitution"},
            reasons={"governing Constitution required by the inline v1 contract"},
        ),
    )
    completed.append("constitution")
    trace.append(
        {
            "stage": "constitution",
            "reader": "canonical Constitution Markdown reader",
            "candidate_count": 1,
        }
    )
    _check_retrieval_timeout(
        clock, started, timeout_ms, stage="sessions", completed_stages=completed
    )

    chunks = augment_chunks_with_topic_sidecars(
        augment_chunks_with_link_sidecars(
            extract_memory_chunks(root, granularity="entry"),
            root,
        ),
        root,
    )
    by_id: dict[str, MemoryChunk] = {}
    for chunk in chunks:
        if chunk.entry_id and chunk.entry_id not in by_id:
            by_id[chunk.entry_id] = chunk
    completed.append("sessions")
    trace.append(
        {
            "stage": "sessions",
            "reader": "canonical session-log reader",
            "candidate_count": len(by_id),
        }
    )
    _check_retrieval_timeout(
        clock, started, timeout_ms, stage="topic_filters", completed_stages=completed
    )

    # Empty ordinal means an entry-level selector. A concrete ``dN`` means the
    # canonical topic sidecar attributed only that decision, and the resolver
    # must not flatten the match back to every decision in the entry.
    root_selection: dict[str, dict[str, set[str]]] = {}

    def add_root(entry_id: str, ordinal: str, reason: str) -> None:
        root_selection.setdefault(entry_id, {}).setdefault(ordinal, set()).add(
            reason
        )

    topic_index = load_topic_index(root)
    resolution = topic_index.resolution()
    for requested in normalized["filters"]["topics"]:
        expanded = expand_topic_filter(root, [requested])
        if requested not in resolution:
            warnings.append(
                {
                    "code": "unknown_topic",
                    "clause": "filters.topics",
                    "detail": requested,
                }
            )
        for chunk in chunks:
            if not chunk.entry_id:
                continue
            if chunk.inferred_topics:
                matched = False
                for ordinal, slug in chunk.inferred_decision_topics:
                    if slug in expanded:
                        add_root(
                            chunk.entry_id,
                            ordinal,
                            f"topic {requested!r} matched canonical sidecar metadata",
                        )
                        matched = True
                # Legacy sidecars still expose a rolled-up channel. Preserve
                # their entry-level meaning when no decision pair is present.
                if (
                    not matched
                    and not chunk.inferred_decision_topics
                    and set(chunk.inferred_topics) & expanded
                ):
                    add_root(
                        chunk.entry_id,
                        "",
                        f"topic {requested!r} matched canonical sidecar metadata",
                    )
            elif set(chunk.topics) & expanded:
                # Canonical precedence is sidecar -> authored. Authored topics
                # are an entry-level fallback only when no sidecar attribution
                # exists, never a union with the current sidecar reading.
                add_root(
                    chunk.entry_id,
                    "",
                    f"topic {requested!r} matched canonical authored metadata",
                )
    completed.append("topic_filters")
    trace.append(
        {
            "stage": "topic_filters",
            "reader": "topic-sidecar reader with topic vocabulary expansion",
            "requested": list(normalized["filters"]["topics"]),
            "matched_entries": sum(
                1
                for selectors in root_selection.values()
                if any(
                    reason.startswith("topic ")
                    for reasons in selectors.values()
                    for reason in reasons
                )
            ),
        }
    )
    _check_retrieval_timeout(
        clock, started, timeout_ms, stage="path_filters", completed_stages=completed
    )

    direct_markdown: list[_RetrievalCandidate] = []
    normalized_paths = list(normalized["filters"]["paths"])
    for requested in normalized_paths:
        target = _runtime_scoped_path(root, requested)
        matched = False
        for chunk in chunks:
            if requested in _entry_file_refs(chunk.text) and chunk.entry_id:
                add_root(
                    chunk.entry_id,
                    "",
                    f"path {requested!r} matched canonical session file evidence"
                )
                matched = True
        if target.is_file() and target.suffix.lower() == ".md":
            try:
                text = target.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as exc:
                raise RetrievalSpecResolutionError(
                    "forbidden_path",
                    "declared Markdown path is unreadable",
                    stage="path_filters",
                    completed_stages=completed,
                    details={"path": requested},
                ) from exc
            text = "\n".join(text.splitlines())
            source = target.relative_to(root).as_posix()
            direct_markdown.append(
                _RetrievalCandidate(
                    ref=source,
                    kind="markdown",
                    source=source,
                    line_range=(1, max(1, len(text.splitlines()))),
                    chunk_id=None,
                    session_date=None,
                    graph_distance=0,
                    text=text,
                    selected_by={"required.evidence", "filters.paths"},
                    reasons={f"declared canonical Markdown path {requested!r}"},
                )
            )
            matched = True
        if not matched:
            warnings.append(
                {
                    "code": "path_no_evidence",
                    "clause": "filters.paths",
                    "detail": requested,
                }
            )
    for candidate in direct_markdown:
        _merge_candidate(candidates, candidate)
    completed.append("path_filters")
    trace.append(
        {
            "stage": "path_filters",
            "reader": "runtime-bounded canonical Markdown path reader",
            "requested": normalized_paths,
            "matched_entries": sum(
                1
                for selectors in root_selection.values()
                if any(
                    reason.startswith("path ")
                    for reasons in selectors.values()
                    for reason in reasons
                )
            ),
            "direct_markdown": len(direct_markdown),
        }
    )
    _check_retrieval_timeout(
        clock, started, timeout_ms, stage="related_decisions", completed_stages=completed
    )

    graph = build_related_entry_graph(root, chunks=chunks)
    depth_limit = normalized["required"]["related_decisions"]["depth"]
    from .core import entry_body_decisions

    decision_ordinals = {
        entry_id: tuple(
            decision.ordinal for decision in entry_body_decisions(chunk.text)
        )
        for entry_id, chunk in by_id.items()
    }

    def target_states(
        entry_id: str,
        ordinal: str | None = None,
    ) -> list[tuple[str, str]]:
        if entry_id not in by_id:
            return []
        available = decision_ordinals.get(entry_id, ()) or ("",)
        selected = (
            [ordinal]
            if ordinal
            else list(available)
        )
        selected = [item for item in selected if item in available]
        root_selectors = root_selection.get(entry_id)
        if root_selectors is not None and "" not in root_selectors:
            allowed = set(root_selectors)
            selected = [item for item in selected if item in allowed]
        return [(entry_id, item) for item in selected]

    root_state_reasons: dict[tuple[str, str], set[str]] = {}
    for entry_id, selectors in root_selection.items():
        for state in target_states(entry_id):
            ordinal = state[1]
            reasons = set(selectors.get("", ()))
            reasons.update(selectors.get(ordinal, ()))
            root_state_reasons[state] = reasons

    decision_inbound: dict[
        str, list[tuple[str, str, str, str]]
    ] = {}
    for source_id, chunk in sorted(by_id.items()):
        for kind, source_ordinal, target_id, target_ordinal, *_ in sorted(
            set(chunk.decision_edges)
        ):
            if target_id in by_id and target_id != source_id:
                decision_inbound.setdefault(target_id, []).append(
                    (source_id, kind, source_ordinal, target_ordinal)
                )

    distances: dict[tuple[str, str], int] = {
        state: 0 for state in root_state_reasons
    }
    frontier = sorted(distances)

    def enqueue(state: tuple[str, str], next_distance: int) -> None:
        if state not in distances or next_distance < distances[state]:
            distances[state] = next_distance
            frontier.append(state)

    while frontier:
        frontier.sort(key=lambda state: (distances[state], state[0], state[1]))
        entry_id, ordinal = frontier.pop(0)
        distance = distances[(entry_id, ordinal)]
        if distance >= depth_limit:
            continue
        node = graph.get(entry_id)
        next_distance = distance + 1
        if node is not None:
            neighbours = sorted(
                set(
                    node.outbound
                    + node.inbound
                    + node.replaces
                    + node.replaced_by
                    + node.evolves
                    + node.evolved_by
                )
            )
            for neighbour in neighbours:
                for state in target_states(neighbour):
                    enqueue(state, next_distance)

        for (
            _kind,
            source_ordinal,
            target_id,
            target_ordinal,
            *_,
        ) in sorted(set(by_id[entry_id].decision_edges)):
            if source_ordinal and source_ordinal != ordinal:
                continue
            for state in target_states(
                target_id,
                target_ordinal or None,
            ):
                enqueue(state, next_distance)

        for (
            source_id,
            _kind,
            source_ordinal,
            target_ordinal,
        ) in sorted(decision_inbound.get(entry_id, ())):
            if target_ordinal and target_ordinal != ordinal:
                continue
            for state in target_states(
                source_id,
                source_ordinal or None,
            ):
                enqueue(state, next_distance)

    related_count = 0
    root_decision_refs_by_entry: dict[str, list[str]] = {}
    source_lines: dict[str, tuple[str, ...]] = {}
    for (entry_id, ordinal), distance in sorted(
        distances.items(),
        key=lambda item: (item[1], item[0][0], item[0][1]),
    ):
        if not ordinal:
            continue
        chunk = by_id[entry_id]
        state = (entry_id, ordinal)
        reasons = set(root_state_reasons.get(state, ()))
        reasons.add(f"related decision graph distance {distance}")
        decision_candidates = _decision_candidates(
            chunk,
            root=root,
            source_lines=source_lines,
            selected_by={"required.related_decisions"},
            reasons=reasons,
            graph_distance=distance,
            ordinals={ordinal},
        )
        for candidate in decision_candidates:
            _merge_candidate(candidates, candidate)
            if state in root_state_reasons:
                root_decision_refs_by_entry.setdefault(entry_id, []).append(
                    candidate.ref
                )
            related_count += 1

    latest_root: MemoryChunk | None = None
    if root_selection:
        latest_root = max(
            (
                by_id[entry_id]
                for entry_id in root_selection
                if entry_id in by_id
            ),
            key=lambda chunk: (
                chunk.session_date,
                chunk.entry_datetime or datetime.min,
                chunk.start_line,
                chunk.entry_id or "",
            ),
            default=None,
        )
    if latest_root is not None:
        refs = root_decision_refs_by_entry.get(str(latest_root.entry_id), [])
        if refs:
            for ref in refs:
                candidates[ref].selected_by.add("required.evidence")
                candidates[ref].reasons.add("latest matching canonical session evidence")
        else:
            _merge_candidate(
                candidates,
                _entry_candidate(
                    latest_root,
                    selected_by={"required.evidence"},
                    reasons={"latest matching canonical session evidence"},
                    graph_distance=0,
                ),
            )
    completed.append("related_decisions")
    trace.append(
        {
            "stage": "related_decisions",
            "reader": "canonical session/link graph reader",
            "root_entries": len(root_selection),
            "visited_entries": len({entry_id for entry_id, _ in distances}),
            "visited_decisions": len(
                [ordinal for _, ordinal in distances if ordinal]
            ),
            "candidate_count": related_count,
            "depth": depth_limit,
        }
    )
    _check_retrieval_timeout(
        clock, started, timeout_ms, stage="optional_sessions", completed_stages=completed
    )

    optional = normalized["optional"]["sessions"]
    optional_count = 0
    if optional and root_selection:
        ordered_chunks = sorted(
            by_id.values(),
            key=lambda chunk: (
                chunk.session_date,
                chunk.entry_datetime or datetime.min,
                chunk.start_line,
                chunk.entry_id or "",
            ),
        )
        indexes = {
            str(chunk.entry_id): index for index, chunk in enumerate(ordered_chunks)
        }
        root_indexes = [
            indexes[entry_id]
            for entry_id in root_selection
            if entry_id in indexes
        ]
        visited_entries = {entry_id for entry_id, _ordinal in distances}
        neighbours = [
            chunk
            for chunk in ordered_chunks
            if chunk.entry_id not in visited_entries
        ]
        neighbours.sort(
            key=lambda chunk: (
                min(abs(indexes[str(chunk.entry_id)] - root_index) for root_index in root_indexes),
                -int(chunk.session_date.strftime("%Y%m%d")),
                chunk.entry_id or "",
            )
        )
        for chunk in neighbours[: optional["neighbouring_entries"]]:
            distance = min(
                abs(indexes[str(chunk.entry_id)] - root_index)
                for root_index in root_indexes
            )
            _merge_candidate(
                candidates,
                _entry_candidate(
                    chunk,
                    selected_by={"optional.sessions"},
                    reasons={f"chronological neighbour distance {distance}"},
                    graph_distance=distance,
                ),
            )
            optional_count += 1
        if optional_count == 0:
            warnings.append(
                {
                    "code": "optional_missing",
                    "clause": "optional.sessions",
                    "detail": "no neighbouring canonical session entries were available",
                }
            )
    completed.append("optional_sessions")
    trace.append(
        {
            "stage": "optional_sessions",
            "reader": "canonical session-log reader",
            "candidate_count": optional_count,
        }
    )

    missing = [
        clause
        for clause in _RETRIEVAL_REQUIRED_CLAUSES
        if not any(clause in candidate.selected_by for candidate in candidates.values())
    ]
    if missing:
        raise RetrievalSpecResolutionError(
            "missing_required",
            "one or more required clauses produced no canonical evidence",
            stage="required_coverage",
            completed_stages=completed,
            details={"clauses": missing},
        )
    _check_retrieval_timeout(
        clock, started, timeout_ms, stage="limits", completed_stages=completed
    )

    ordered = sorted(candidates.values(), key=_candidate_sort_key)
    selected: list[_RetrievalCandidate] = []
    omitted: list[_RetrievalCandidate] = []
    tokens = 0
    max_entries = normalized["limits"]["max_entries"]
    max_tokens = normalized["limits"]["max_tokens"]
    for candidate in ordered:
        if (
            len(selected) >= max_entries
            or tokens + candidate.token_estimate > max_tokens
        ):
            omitted.append(candidate)
            continue
        selected.append(candidate)
        tokens += candidate.token_estimate
    covered = {
        clause
        for candidate in selected
        for clause in candidate.selected_by
        if clause in _RETRIEVAL_REQUIRED_CLAUSES
    }
    lost = [clause for clause in _RETRIEVAL_REQUIRED_CLAUSES if clause not in covered]
    if lost:
        raise RetrievalSpecResolutionError(
            "required_limit_exceeded",
            "limits would remove required clause coverage",
            stage="limits",
            completed_stages=completed,
            details={
                "clauses": lost,
                "max_entries": max_entries,
                "max_tokens": max_tokens,
            },
        )
    if omitted:
        warnings.append(
            {
                "code": "truncated",
                "clause": "limits",
                "detail": f"{len(omitted)} candidate(s) omitted",
            }
        )
    completed.append("limits")
    trace.append(
        {
            "stage": "limits",
            "reader": "M1 bounded-pack limiter",
            "candidate_count": len(ordered),
            "selected_count": len(selected),
            "omitted_count": len(omitted),
            "token_estimate": tokens,
        }
    )
    return {
        "selected": selected,
        "candidate_count": len(ordered),
        "omitted_count": len(omitted),
        "token_estimate": tokens,
        "warnings": warnings,
        "trace": trace,
        "completed_stages": completed,
    }


def _evidence_record(
    candidate: _RetrievalCandidate,
    *,
    include_excerpt: bool,
) -> dict[str, Any]:
    fetch = (
        {
            "tool": "memory_get_chunk",
            "arguments": {"chunk_id": candidate.chunk_id},
        }
        if candidate.chunk_id
        else {
            "path": candidate.source,
            "line_start": candidate.line_range[0],
            "line_end": candidate.line_range[1],
        }
    )
    return {
        "ref": candidate.ref,
        "kind": candidate.kind,
        "source": candidate.source,
        "line_range": list(candidate.line_range),
        "chunk_id": candidate.chunk_id,
        "session_date": candidate.session_date,
        "graph_distance": candidate.graph_distance,
        "selected_by": sorted(candidate.selected_by),
        "reasons": sorted(candidate.reasons),
        "token_estimate": candidate.token_estimate,
        "fetch": fetch,
        "excerpt": (
            (
                _decision_body(candidate.text)
                if getattr(candidate, "granularity", "") == "decision"
                # A candidate carries no matched terms, so this degrades to the head of the
                # fence-stripped text - query-blind, but never metadata.
                else _selection_preview(candidate.text)
            )
            if include_excerpt
            else None
        ),
    }


def _evidence_pack_fingerprint(pack: Mapping[str, Any]) -> str:
    identity = {
        "pack_schema": pack["pack_schema"],
        "pack_version": pack["pack_version"],
        "resolver_version": pack["resolver_version"],
        "corpus_revision": pack["corpus_revision"],
        "effective_spec_fingerprint": pack["effective_spec_fingerprint"],
        "evidence": [
            {
                key: item[key]
                for key in (
                    "ref",
                    "kind",
                    "source",
                    "line_range",
                    "chunk_id",
                    "graph_distance",
                    "selected_by",
                )
            }
            for item in pack["evidence"]
        ],
    }
    return "sha256:" + hashlib.sha256(
        canonical_retrieval_json(identity).encode("utf-8")
    ).hexdigest()


def _stable_retrieval_plan(
    spec: Mapping[str, Any],
    cwd: str | Path,
    *,
    clock: Callable[[], float],
    timeout_ms: int,
    revision_reader: Callable[[str | Path, Mapping[str, Any]], str],
) -> tuple[dict[str, Any], dict[str, Any], str, int, float]:
    from .retrieval_spec import normalize_retrieval_spec

    normalized = normalize_retrieval_spec(spec)
    started = clock()
    seen: list[tuple[str, str]] = []
    for attempt in (1, 2):
        start_revision = revision_reader(cwd, normalized)
        plan = _build_retrieval_plan(
            normalized,
            cwd,
            clock=clock,
            started=started,
            timeout_ms=timeout_ms,
        )
        end_revision = revision_reader(cwd, normalized)
        _check_retrieval_timeout(
            clock,
            started,
            timeout_ms,
            stage="revision_check",
            completed_stages=plan["completed_stages"],
        )
        seen.append((start_revision, end_revision))
        if start_revision == end_revision:
            return normalized, plan, start_revision, attempt, started
    raise RetrievalSpecResolutionError(
        "corpus_changed",
        "corpus changed during both resolution attempts",
        stage="revision_check",
        completed_stages=plan["completed_stages"],
        details={"attempts": [list(pair) for pair in seen]},
    )


def preview_retrieval_spec(
    spec: Mapping[str, Any],
    cwd: str | Path = ".",
    *,
    _clock: Callable[[], float] = time.monotonic,
    _timeout_ms: int = DEFAULT_RETRIEVAL_TIMEOUT_MS,
    _revision_reader: Callable[
        [str | Path, Mapping[str, Any]], str
    ] = _retrieval_corpus_revision,
) -> dict[str, Any]:
    """Validate and plan an inline spec without creating an Evidence Pack."""
    from .retrieval_spec import retrieval_spec_fingerprint

    normalized, plan, revision, attempt, started = _stable_retrieval_plan(
        spec,
        cwd,
        clock=_clock,
        timeout_ms=_timeout_ms,
        revision_reader=_revision_reader,
    )
    preview = {
        "preview_schema": RETRIEVAL_PREVIEW_SCHEMA,
        "preview_version": 1,
        "resolver_version": RETRIEVAL_RESOLVER_VERSION,
        "valid": True,
        "corpus_revision": revision,
        "effective_spec": normalized,
        "effective_spec_fingerprint": retrieval_spec_fingerprint(normalized),
        "candidate_count": plan["candidate_count"],
        "selected_count": len(plan["selected"]),
        "omitted_count": plan["omitted_count"],
        "token_estimate": plan["token_estimate"],
        "warnings": plan["warnings"],
        "plan": plan["trace"],
        "revision_attempt": attempt,
        "write_surface": "read-only; no Evidence Pack created",
    }
    _check_retrieval_timeout(
        _clock,
        started,
        _timeout_ms,
        stage="preview_format",
        completed_stages=[*plan["completed_stages"], "revision_check"],
    )
    return preview


def resolve_retrieval_spec(
    spec: Mapping[str, Any],
    cwd: str | Path = ".",
    *,
    _clock: Callable[[], float] = time.monotonic,
    _timeout_ms: int = DEFAULT_RETRIEVAL_TIMEOUT_MS,
    _revision_reader: Callable[
        [str | Path, Mapping[str, Any]], str
    ] = _retrieval_corpus_revision,
) -> dict[str, Any]:
    """Resolve an inline spec into one deterministic, ephemeral Evidence Pack."""
    from .retrieval_spec import retrieval_spec_fingerprint

    normalized, plan, revision, attempt, started = _stable_retrieval_plan(
        spec,
        cwd,
        clock=_clock,
        timeout_ms=_timeout_ms,
        revision_reader=_revision_reader,
    )
    pack: dict[str, Any] = {
        "pack_schema": EVIDENCE_PACK_SCHEMA,
        "pack_version": EVIDENCE_PACK_VERSION,
        "resolver_version": RETRIEVAL_RESOLVER_VERSION,
        "corpus_revision": revision,
        "effective_spec": normalized,
        "effective_spec_fingerprint": retrieval_spec_fingerprint(normalized),
        "completeness": "partial" if plan["omitted_count"] else "complete",
        "warnings": plan["warnings"],
        "evidence": [
            _evidence_record(
                candidate,
                include_excerpt=normalized["output"]["include_excerpts"],
            )
            for candidate in plan["selected"]
        ],
        "resolution_trace": (
            [*plan["trace"], {"stage": "revision_check", "attempt": attempt}]
            if normalized["output"]["include_resolution_trace"]
            else []
        ),
        "token_estimate": plan["token_estimate"],
        "fingerprint": "",
    }
    pack["fingerprint"] = _evidence_pack_fingerprint(pack)
    _check_retrieval_timeout(
        _clock,
        started,
        _timeout_ms,
        stage="pack_format",
        completed_stages=[*plan["completed_stages"], "revision_check"],
    )
    return pack


def validate_evidence_pack(
    pack: Mapping[str, Any],
    cwd: str | Path = ".",
    *,
    _revision_reader: Callable[
        [str | Path, Mapping[str, Any]], str
    ] = _retrieval_corpus_revision,
) -> dict[str, Any]:
    """Reject stale, tampered, or no-longer-fetchable ephemeral packs."""
    from .core import resolve_runtime
    from .retrieval_spec import retrieval_spec_fingerprint

    if pack.get("pack_schema") != EVIDENCE_PACK_SCHEMA or pack.get(
        "pack_version"
    ) != EVIDENCE_PACK_VERSION:
        raise RetrievalSpecResolutionError(
            "invalid_pack",
            "unsupported Evidence Pack identity",
            stage="pack_validation",
        )
    effective_spec = pack.get("effective_spec")
    if not isinstance(effective_spec, Mapping):
        raise RetrievalSpecResolutionError(
            "invalid_pack",
            "effective_spec is missing",
            stage="pack_validation",
        )
    if pack.get("effective_spec_fingerprint") != retrieval_spec_fingerprint(
        effective_spec
    ):
        raise RetrievalSpecResolutionError(
            "fingerprint_mismatch",
            "effective_spec does not match its fingerprint",
            stage="pack_validation",
        )
    current_revision = _revision_reader(cwd, effective_spec)
    if current_revision != pack.get("corpus_revision"):
        raise RetrievalSpecResolutionError(
            "stale_pack",
            "Evidence Pack corpus revision is not current",
            stage="pack_validation",
            details={
                "pack_revision": pack.get("corpus_revision"),
                "current_revision": current_revision,
            },
        )
    if pack.get("fingerprint") != _evidence_pack_fingerprint(pack):
        raise RetrievalSpecResolutionError(
            "fingerprint_mismatch",
            "Evidence Pack fingerprint does not match its canonical references",
            stage="pack_validation",
        )
    root = Path(resolve_runtime(cwd).workspace_root).resolve()
    for item in pack.get("evidence", []):
        source = item.get("source")
        if not isinstance(source, str):
            raise RetrievalSpecResolutionError(
                "unfetchable_ref",
                "evidence source is missing",
                stage="pack_validation",
            )
        path = _runtime_scoped_path(root, source)
        if not path.is_file():
            raise RetrievalSpecResolutionError(
                "unfetchable_ref",
                f"canonical Markdown source is absent: {source}",
                stage="pack_validation",
                details={"ref": item.get("ref")},
            )
        chunk_id = item.get("chunk_id")
        if chunk_id:
            try:
                get_chunk(str(chunk_id), root)
            except ValueError as exc:
                raise RetrievalSpecResolutionError(
                    "unfetchable_ref",
                    f"chunk is absent: {chunk_id}",
                    stage="pack_validation",
                    details={"ref": item.get("ref")},
                ) from exc
    return {
        "valid": True,
        "corpus_revision": current_revision,
        "fingerprint": pack["fingerprint"],
        "ref_count": len(pack.get("evidence", [])),
    }


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


def entry_topic_sidecars(cwd: str | Path = ".") -> dict[str, dict[str, Any]]:
    """Late-attributed topics, keyed by ``entry_id``.

    The third sidecar family's reader. Topics are attributed to an entry (and,
    with the `<slug>:dN` grammar, to one of its decisions) *after* it was
    written, because append-only forbids reopening the entry to add them.

    Precedence is **most-recent-wins per entry**, not a union: a topic list is a
    state replaced wholesale by a better one, so a later block supersedes the
    earlier list entirely while the earlier stays readable as what was
    previously believed. That is the opposite of ``entry_link_sidecars``, where
    each edge is an independent assertion and blocks union - see
    docs/3_Spec/draft/sidecar-supersession-model.md. Ordering is the same
    (heading timestamp, block index) rule ``entry_diagram_sidecars`` uses, so
    the winner never depends on directory-walk order.

    Returns ``{entry_id: {"topics": (slug, ...), "decision_topics":
    ((ordinal, slug), ...)}}`` where ordinal is "" for a bare entry-level slug.
    Slugs are returned exactly as authored and are NOT alias-resolved here:
    ``links check`` already rejects a non-canonical alias in a sidecar, so
    resolving would silently accept what the validator refuses and leave the
    two surfaces disagreeing. Malformed blocks are skipped and reported there.
    """
    from .core import _frontmatter_list_region, _parse_topic_slug, iter_topic_sidecar_documents, resolve_runtime

    runtime = resolve_runtime(cwd)
    topics_dir = runtime.memory_dir / "sessions" / "topics"
    sidecars: dict[str, dict[str, Any]] = {}
    # entry_id -> (heading timestamp, block index) of the block currently held.
    block_precedence: dict[str, tuple[str, int]] = {}
    if not topics_dir.is_dir():
        return sidecars
    for topic_doc in iter_topic_sidecar_documents(runtime.memory_dir / "sessions"):
        if topic_doc.malformed_reason:
            continue
        try:
            text = topic_doc.path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for index, block in enumerate(_LINK_ENTRY_RE.finditer(text)):
            heading_ts, _title, yaml_block = block.groups()
            entry_id = None
            for line in yaml_block.splitlines():
                stripped = line.strip()
                if stripped.startswith("entry_id:"):
                    entry_id = stripped.split(":", 1)[1].strip().strip("'\"")
                    break
            if not entry_id:
                continue
            precedence = (heading_ts, index)
            if precedence < block_precedence.get(entry_id, ("", -1)):
                continue
            rolled: list[str] = []
            pairs: list[tuple[str, str]] = []
            axis_pairs: dict[str, list[tuple[str, str]]] = {"area": [], "activity": []}
            # TWO SHAPES ARE ACCEPTED under `topics:`. The nested one declares
            # the axis structurally:
            #
            #     topics:
            #       area:
            #         - graph:d1
            #       activity:
            #         - bugfix:d1
            #
            # and the flat one - every sidecar written before 2026-07-27 - lists
            # slugs directly and leaves the axis to be derived from topics.yaml.
            #
            # The nested form is readable by the flat reader (it collects the
            # same `- ` lines and ignores the sub-keys), which is what makes the
            # migration safe in both directions: an old reader sees a correct if
            # axis-blind list rather than an empty one.
            region = _frontmatter_list_region(yaml_block, "topics")
            # Split on the axis sub-keys by INDENT, not with
            # `_frontmatter_list_region`. That helper stops at the first line
            # that is not indented at all, so asking it for `area` inside this
            # region runs straight through `activity:` and returns both lists -
            # which read back as every activity slug also being an area.
            axis_regions: dict[str, list[str]] = {"area": [], "activity": []}
            current = ""
            for line in region.splitlines():
                key = line.strip().rstrip(":")
                if line.strip().endswith(":") and key in axis_regions:
                    current = key
                    continue
                if current:
                    axis_regions[current].append(line)
            nested = any(axis_regions.values())
            buckets = (
                [(axis, lines) for axis, lines in axis_regions.items()]
                if nested
                else [("", region.splitlines())]
            )
            for axis, source in buckets:
                for line in source:
                    stripped = line.strip()
                    if not stripped.startswith("-"):
                        continue
                    token = stripped[1:].strip().strip("'\"")
                    if not token:
                        continue
                    slug, ordinal, well_formed = _parse_topic_slug(token)
                    if not well_formed:
                        continue
                    pairs.append((ordinal or "", slug))
                    if axis:
                        axis_pairs[axis].append((ordinal or "", slug))
                    if slug not in rolled:
                        rolled.append(slug)
            if not pairs:
                continue
            block_precedence[entry_id] = precedence
            sidecars[entry_id] = {
                "topics": tuple(rolled),
                "decision_topics": tuple(pairs),
                # Empty for a flat block: the axis was never DECLARED there, and
                # deriving it here would hand consumers a guess wearing the same
                # shape as a fact. A consumer that wants the axis of a flat
                # sidecar asks topics.yaml, which is where that answer lives.
                "decision_area": tuple(axis_pairs["area"]),
                "decision_activity": tuple(axis_pairs["activity"]),
            }
    return sidecars


def augment_chunks_with_topic_sidecars(
    chunks: Iterable[MemoryChunk],
    cwd: str | Path = ".",
) -> list[MemoryChunk]:
    """Attach sidecar-inferred topics to chunks as a channel beside authored ones.

    Mirrors ``augment_chunks_with_link_sidecars``, with one deliberate
    difference: nothing is unioned into ``chunk.topics``. Authored and inferred
    stay separable all the way to the consumer, which is what lets a payload
    report provenance instead of a merged list.
    """
    entries = list(chunks)
    sidecars = entry_topic_sidecars(cwd)
    if not sidecars:
        return entries
    augmented: list[MemoryChunk] = []
    for chunk in entries:
        extra = sidecars.get(chunk.entry_id or "")
        if not extra:
            augmented.append(chunk)
            continue
        augmented.append(
            replace(
                chunk,
                inferred_topics=extra["topics"],
                inferred_decision_topics=extra["decision_topics"],
            )
        )
    return augmented


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
    # entry_id -> (heading timestamp, block index) of the block currently held.
    block_precedence: dict[str, tuple[str, int]] = {}
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
            # Most-recent-wins: one entry may accrue several diagram blocks over
            # time (a repair of an unrenderable diagram is an APPENDED block,
            # never an edit of the published one), so the newest declaration is
            # the current record and the older stays readable as what was
            # authored. The heading timestamp carries its own date, so it orders
            # correctly across files whatever order the directory walk yields;
            # the block index only breaks a same-timestamp tie within one file.
            precedence = (heading_ts, index)
            if precedence < block_precedence.get(entry_id, ("", -1)):
                continue
            block_precedence[entry_id] = precedence
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


def adr_diagram_sidecars(cwd: str | Path = ".") -> dict[str, dict[str, Any]]:
    """Diagram blocks keyed by ``adr_id`` instead of ``entry_id``.

    A DELIBERATELY SEPARATE reader, not a widening of
    ``entry_diagram_sidecars``. The two share the sidecar file family and the
    block grammar and nothing else: an entry diagram is filed under its entry's
    session date and is optional per entry, while an ADR diagram is filed under
    the date it was drawn and every ADR owes an answer. Folding them into one
    map would silently shift what ``diagrams_today`` and
    ``entries_since_last_diagram`` count, and an adr-keyed block would
    otherwise vanish from the entry reader with no match and no error.

    ``grounded_in`` carries the decision refs whose shape the diagram draws -
    the evidence that the picture is of something recorded rather than
    invented. ``diagram_status: not_applicable`` is the sanctioned answer for
    an ADR with nothing structural to draw; such a block needs no Mermaid, and
    the reader surfaces it so a caller can tell "answered, nothing to draw"
    from "never looked". Most-recent-wins per ``adr_id``, as for entries.
    """
    from .core import _frontmatter_list_refs, iter_diagram_sidecar_documents, resolve_runtime

    runtime = resolve_runtime(cwd)
    diagrams_dir = runtime.memory_dir / "sessions" / "diagrams"
    sidecars: dict[str, dict[str, Any]] = {}
    precedence_of: dict[str, tuple[str, int]] = {}
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
            scalars: dict[str, str] = {}
            for line in yaml_block.splitlines():
                stripped = line.strip()
                if ":" in stripped and not stripped.startswith(("-", "#")):
                    key, _, value = stripped.partition(":")
                    scalars[key.strip()] = value.strip().strip("'\"")
            adr_id = scalars.get("adr_id")
            if not adr_id:
                continue
            precedence = (heading_ts, index)
            if precedence < precedence_of.get(adr_id, ("", -1)):
                continue
            precedence_of[adr_id] = precedence
            section_end = blocks[index + 1].start() if index + 1 < len(blocks) else len(text)
            section_text = text[block.end():section_end]
            sidecars[adr_id] = {
                "adr_id": adr_id,
                "path": rel,
                "title": title.strip() or None,
                "heading_datetime": heading_ts,
                "status": (scalars.get("diagram_status") or "").strip().lower() or None,
                "note": scalars.get("note") or None,
                "grounded_in": tuple(
                    parsed.raw for parsed in _frontmatter_list_refs(yaml_block, "grounded_in")
                ),
                "mermaid_blocks": [
                    match.group(1).rstrip("\n") for match in _MERMAID_BLOCK_RE.finditer(section_text)
                ],
            }
    return sidecars


def entry_link_sidecars(cwd: str | Path = ".") -> dict[str, dict[str, Any]]:
    """Late-authored lifecycle edges, keyed by source ``entry_id``.

    Mirrors ``entry_diagram_sidecars``: sidecars live under
    ``.memory-seed/sessions/links/YYYY-MM/YYYY-MM-DD.md`` (legacy flat
    ``links/YYYY-MM-DD.md`` also read), one dated file per day. Each block is a
    session-entry-shaped heading plus a fenced yaml carrying the source
    ``entry_id`` and any of ``replaces`` / ``evolves`` / ``related_entries``
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
        _frontmatter_list_region,
        _parse_edge_confidence,
        _parse_retract,
        iter_link_sidecar_documents,
        resolve_runtime,
    )

    runtime = resolve_runtime(cwd)
    links_dir = runtime.memory_dir / "sessions" / "links"
    sidecars: dict[str, dict[str, Any]] = {}
    # Append-only retractions, accumulated across ALL blocks then applied once at
    # the end: a `retracts:` in a later block removes an edge an earlier block
    # declared, so the subtraction can only run after the union is complete.
    # entry-level identity = (canonical_kind, target_id); decision identity =
    # (kind, source_ordinal, target_id, target_ordinal).
    retract_entry: dict[str, set[tuple[str, str]]] = {}
    retract_decision: dict[str, set[tuple[str, str, str, str]]] = {}
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
            # B replaces D1 of A" does not license "B replaces A", so a
            # consumer that does not model decisions must see exactly the edge
            # set it saw before this feature existed.
            found: dict[str, Any] = {}
            # (kind, source_ordinal, target_entry_id, target_ordinal); either
            # ordinal "" when unspecified - same shape as
            # MemoryChunk.decision_edges so the Trail merges both streams.
            decisions: list[tuple[str, str, str, str]] = []
            # "supersedes" is the legacy authored key for "replaces" (renamed
            # 2026-07-24); it canonicalises on read so every consumer sees one
            # spelling and legacy corpora keep their edges.
            # (authored key, entry-level list key, decision-edge kind). The
            # entry-level key keeps its long spelling (`related_entries`) that
            # consumers read; the decision-edge kind is the short `related`,
            # matching MemoryChunk.decision_edges and the Trail's kind map.
            for key, canonical, decision_kind in (
                ("replaces", "replaces", "replaces"),
                ("supersedes", "replaces", "replaces"),
                ("evolves", "evolves", "evolves"),
                ("related_entries", "related_entries", "related"),
            ):
                entry_level: list[str] = []
                for parsed in _frontmatter_list_refs(yaml_block, key):
                    if not parsed.ok:
                        continue  # links check reports it; readers skip it
                    if parsed.decision is None:
                        # Bare target: the edge is entry-level on that side
                        # even when an arrow names the authoring decision.
                        entry_level.append(parsed.entry_id)
                    # A TYPE alone makes an edge decision-level information even
                    # when neither ordinal is named: `mse_x (refines)` says which
                    # kind of evolution this is, and that fact has nowhere else to
                    # live - the entry-level list is bare ids. Without this the
                    # survivor check below cannot see a typed bare edge, and a
                    # retract-and-retype deletes it.
                    if (parsed.decision is not None or parsed.source_decision is not None
                            or parsed.evolution_type):
                        # Fifth element is the evolution type (2026-08-09). This
                        # is the SECOND parser building decision_edges - the
                        # other lives in `semantic_cache` - and the two must
                        # agree on arity, or a retract key built here can never
                        # match an edge built there.
                        decisions.append(
                            (decision_kind, parsed.source_decision or "", parsed.entry_id,
                             parsed.decision or "", parsed.evolution_type or "")
                        )
                found[canonical] = tuple(dict.fromkeys(tuple(found.get(canonical, ())) + tuple(entry_level)))
            found["decision_edges"] = tuple(decisions)
            # Structured per-edge confidence (campaign metadata), keyed by the
            # kind-agnostic (source_ord, target, target_ord) identity so a graph
            # consumer joins it to any edge. Absent = human-authored, unscored.
            found["edge_confidence"] = _parse_edge_confidence(yaml_block)
            # Retractions this block declares (against this or an earlier block's
            # edges). A bare/entry-level ref subtracts by (kind, target); a
            # decision ref subtracts the exact 4-tuple. Applied after the union.
            for line in _frontmatter_list_region(yaml_block, "retracts").splitlines():
                item = line.strip()
                if not item.startswith("- "):
                    continue
                retract = _parse_retract(item[2:])
                if not retract.ok or retract.ref is None:
                    continue  # links check reports it; readers skip it
                if retract.ref.decision is None:
                    retract_entry.setdefault(entry_id, set()).add((retract.kind, retract.ref.entry_id))
                    # An arrow-prefixed bare ref (`d2 -> X`) is authored as ONE
                    # statement but collected TWICE - an entry-level edge AND a
                    # source-only decision edge (kind, dN, target, "") - so the
                    # retract must remove both twins or the decision one survives.
                    if retract.ref.source_decision is not None:
                        retract_decision.setdefault(entry_id, set()).add(
                            (retract.kind, retract.ref.source_decision, retract.ref.entry_id, "",
                             retract.ref.evolution_type or "")
                        )
                else:
                    retract_decision.setdefault(entry_id, set()).add(
                        (retract.kind, retract.ref.source_decision or "", retract.ref.entry_id,
                         retract.ref.decision, retract.ref.evolution_type or "")
                    )
            existing = sidecars.get(entry_id)
            if existing:
                # decision_edges is merged alongside the entry-level keys: two
                # sidecar blocks may key to one entry (different days, or a
                # correction), and dropping the later block's decision refs
                # would lose edges silently rather than loudly.
                for key in ("replaces", "evolves", "related_entries", "decision_edges"):
                    existing[key] = tuple(dict.fromkeys(existing.get(key, ()) + found[key]))
                existing["edge_confidence"] = {**existing.get("edge_confidence", {}), **found["edge_confidence"]}
            else:
                sidecars[entry_id] = {
                    "entry_id": entry_id,
                    "path": rel,
                    "heading_datetime": heading_ts,
                    **found,
                }
    # Apply retractions to the completed union: an edge a `retracts:` named is
    # removed from the effective set, the append-only way to downgrade/delete a
    # published edge. A downgrade pairs this with a fresh edge of the new kind.
    # Decision-level retractions apply FIRST, because the entry-level drop below
    # consults what survives them. Each set is ALSO exported on the sidecar
    # (`retracted_decision_edges` / `retracted_entry_edges`): a retract may name
    # an edge authored in the ENTRY's own YAML, which lives on the chunk rather
    # than in any sidecar list, so `augment_chunks_with_link_sidecars` must see
    # the sets to apply them there - without the export, retracting an
    # entry-YAML edge was a silent no-op.
    for eid, ids in retract_decision.items():
        sidecar = sidecars.get(eid)
        if not sidecar:
            continue
        if sidecar.get("decision_edges"):
            sidecar["decision_edges"] = tuple(e for e in sidecar["decision_edges"] if tuple(e) not in ids)
        sidecar["retracted_decision_edges"] = tuple(sorted(ids))
    for eid, keys in retract_entry.items():
        sidecar = sidecars.get(eid)
        if not sidecar:
            continue
        sidecar["retracted_entry_edges"] = tuple(sorted(keys))
        # An entry-level list holds bare target ids and therefore carries no
        # type, so "retract the untyped edge to X" cannot be told apart from
        # "retract the typed one" at this level. The entry-level list is a
        # PROJECTION of the edges, so the rule follows from that: drop the target
        # only when no decision edge of that kind to it survived. Otherwise a
        # retract-and-retype in one block deleted its own replacement's
        # projection - which is how the 2026-08-09 backfill removed 807 edges
        # with `links check` reading OK throughout.
        surviving = {
            (edge[0], edge[2]) for edge in sidecar.get("decision_edges", ()) if len(edge) > 2
        }
        for canonical, list_key in (("replaces", "replaces"), ("evolves", "evolves"), ("related", "related_entries")):
            drop = {
                target
                for kind, target in keys
                if kind == canonical and (canonical, target) not in surviving
            }
            if drop and sidecar.get(list_key):
                sidecar[list_key] = tuple(t for t in sidecar[list_key] if t not in drop)
    return sidecars


def augment_chunks_with_link_sidecars(
    chunks: Iterable[MemoryChunk],
    cwd: str | Path = ".",
) -> list[MemoryChunk]:
    """Union entry YAML edges with append-only link sidecar edges.

    Link sidecars are authored after a session entry is written, so the
    effective graph is ``union(entry YAML, sidecar) minus retracts`` at read
    time. This helper augments the input chunks before callers build
    ``build_related_entry_graph`` so outbound edges, inverse freshness fields,
    and result payloads all agree without teaching ``semantic_cache`` how to
    read sidecar files. Retract sets apply to the chunk's own entry-YAML lists
    too (scoped to the same ``entry_id``): a sidecar is the only append-only
    surface that can downgrade a published edge, wherever it was authored.
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

    def union_decisions(
        base: tuple[tuple[str, str, str, str, str], ...],
        extra: Iterable[tuple[str, str, str, str, str]],
    ) -> tuple[tuple[str, str, str, str, str], ...]:
        # Arity-tolerant on input: a caller holding a pre-2026-08-09 4-tuple
        # (a cached corpus, a test fixture) is padded rather than crashed, since
        # "no type recorded" and "typed empty" are the same statement here.
        merged = list(base)
        for edge in extra:
            canonical = tuple(edge) + ("",) * (5 - len(tuple(edge)))
            if canonical not in merged:
                merged.append(canonical)
        return tuple(merged)

    augmented: list[MemoryChunk] = []
    for chunk in entries:
        extra = sidecars.get(chunk.entry_id or "")
        if not extra:
            augmented.append(chunk)
            continue
        # Retractions reach the CHUNK's entry-YAML edges here (2026-08-09).
        # `entry_link_sidecars` subtracts them from the sidecar's own lists, but
        # an edge authored in the entry's YAML lives on the chunk, so applying
        # them only there made such a retract a silent no-op. Scoped to this
        # entry_id by construction: the sets ride on the sidecar keyed to it.
        retract_dec = {tuple(e) for e in extra.get("retracted_decision_edges", ())}
        retract_ent = {tuple(k) for k in extra.get("retracted_entry_edges", ())}
        merged_decisions = union_decisions(chunk.decision_edges, extra.get("decision_edges", ()))
        if retract_dec:
            merged_decisions = tuple(
                e for e in merged_decisions
                if tuple(e) + ("",) * (5 - len(tuple(e))) not in retract_dec
            )
        related = union(chunk.related_entries, extra.get("related_entries", ()), chunk.entry_id)
        replaces = union(chunk.replaces, extra.get("replaces", ()), chunk.entry_id)
        evolves = union(chunk.evolves, extra.get("evolves", ()), chunk.entry_id)
        if retract_ent:
            # Mirror of the sidecar-side rule: an entry-level list is a
            # PROJECTION of the edges, so a target drops only when no decision
            # edge of that kind to it survived - otherwise a retract-and-retype
            # deletes its own replacement's projection.
            surviving = {(e[0], e[2]) for e in merged_decisions if len(e) > 2}

            def _drop(kind: str, values: tuple[str, ...]) -> tuple[str, ...]:
                gone = {
                    t for k, t in retract_ent
                    if k == kind and (kind, t) not in surviving
                }
                return tuple(t for t in values if t not in gone) if gone else values

            related = _drop("related", related)
            replaces = _drop("replaces", replaces)
            evolves = _drop("evolves", evolves)
        augmented.append(
            replace(
                chunk,
                related_entries=related,
                replaces=replaces,
                evolves=evolves,
                decision_edges=merged_decisions,
            )
        )
    return augmented


def load_corpus(
    cwd: str | Path = ".",
    granularity: str = "decision",
    *,
    view: str = "augmented",
    snapshot: "CorpusSnapshot | None" = None,
) -> list[MemoryChunk]:
    """The canonical corpus read: extraction plus EVERY sidecar augmentation.

    Sidecars are append-only edits authored after an entry is written - link sidecars carry the
    typed lifecycle edges (`replaces` / `evolves` / `related_entries`), topic sidecars carry topic
    assignments. `extract_memory_chunks` alone returns none of them, so a caller that skips the
    augmenters silently reads a PARTIAL corpus: the chunks look well-formed, the counts look
    plausible, and the lifecycle graph is simply missing most of its edges.

    That failure has now happened three times in this project, twice in measurement harnesses and
    once in a shipped gate (`ranking_ab.run_ab`, which computed the supersession signal's affected
    set from a raw corpus and therefore A/B-tested against a fraction of the real edges). It fails
    silently in every case, which is why the fix is a default rather than documentation.

    Use this instead of calling `extract_memory_chunks` directly. `tests/test_corpus_read_path.py`
    holds the allowlist of the remaining direct callers and the reason each is exempt; adding a new
    one fails that test.
    """
    # The projection validates its full source manifest before every persistent
    # hit; absent/corrupt/unprovable artifacts reconstruct from authority.
    # Supplying a snapshot lets one invocation share its verified corpus rather
    # than repeatedly deserialize or rebuild it.
    if snapshot is None:
        snapshot = get_corpus_snapshot(cwd)
    return list(snapshot.chunks(granularity, view))


# Weight on idf-summed shared TITLE terms, alongside FILE_OVERLAP_BOOST on
# shared files. Tuned against ground truth rather than taste: the 101
# replaces/evolves edges authors declared in entry YAML across the corpus.
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
# How many purely-semantic candidates may join a gap that the lexical gate could
# never have surfaced. A SEPARATE cap, applied after the gated `top_k` slice, so
# an ungated candidate widens recall but can never displace evidence a human can
# check. Two, because the gate misses rarely and an unfiltered suggestion costs a
# reader more than a gated one: it carries no shared file, topic or title to
# justify itself, only a cosine.
UNGATED_CANDIDATE_CAP = 2


def _embed_entries_for_link_audit(
    chunks: list[MemoryChunk],
) -> tuple[dict[str, Any] | None, str | None, str | None]:
    """L2-normalised embeddings per entry: (vectors, provider_name, fallback_reason).

    ``vectors`` is None rather than raising on any failure - a missing provider is
    the documented lightweight install (`pip install --no-deps memory-seed`), not
    an error, and link audit must still produce lexical results there. The
    fallback REASON is returned rather than swallowed: because the semantic term
    dominates ranking, a silent degradation to lexical changes almost every
    ordering with nothing on screen to say so, so the caller must be able to
    report it (same contract as `search_memory`'s `semantic_fallback_reason`).
    """
    provider, name, fallback = resolve_semantic_provider("link audit", enabled=True)
    if provider is None or fallback:
        return None, name, fallback or "semantic provider unavailable"
    ids = [chunk.entry_id or "" for chunk in chunks]
    try:
        raw = provider.embed([f"{chunk.title}\n{chunk.text}" for chunk in chunks])
    except Exception as exc:  # pragma: no cover - provider-specific failure
        return None, name, str(exc)
    vectors: dict[str, Any] = {}
    for entry_id, vector in zip(ids, raw):
        if not entry_id:
            continue
        norm = sum(value * value for value in vector) ** 0.5 or 1.0
        vectors[entry_id] = [value / norm for value in vector]
    return vectors, name, None

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
    # TOTAL rank score, lexical + semantic. The name predates semantic ranking
    # (2026-07-22) and is kept for its existing consumers; `lexical_score` and
    # `semantic_score` below decompose it.
    file_overlap_score: float
    # True when a related_entries link already exists but no lifecycle edge -
    # the "supersession mislabelled as related" case the sweep should upgrade.
    already_related: bool = False
    # The candidate's own decisions (ordinal + name + body), so an edge can be
    # narrowed to `:dN`. Empty for a no-decision entry. This is surfaced, not
    # scored: the mechanical evidence is entry-level and cannot discriminate
    # decisions, so which one an edge targets is a human's (or a judgment
    # agent's) call, exactly as the replaces/evolves/related TYPE already is.
    decisions: tuple[DecisionSummary, ...] = ()
    # The lexical half of `file_overlap_score` (files + title terms) on its own.
    lexical_score: float = 0.0
    # Raw model2vec cosine in [0,1], BEFORE SEMANTIC_OVERLAP_BOOST is applied -
    # `None` when semantic ranking was off or unavailable. Exposed rather than
    # left folded into the total because the boost is large (160) and dominates
    # ranking: without this field an operator cannot tell whether a candidate is
    # here on shared-file evidence they can check or on an opaque cosine, nor
    # whether the ranking silently degraded to lexical.
    semantic_score: float | None = None
    # True when the lexical gate could NOT have surfaced this pair - it shares no
    # file and no distinctive title term, and any topic it shares was suppressed
    # because the pair is already `related`. It arrived on semantic rank alone.
    # A gated set cannot contain such a pair BY CONSTRUCTION however related the
    # two entries are, so without this second source the swarm's ceiling is set
    # by the gate rather than by its own judgement. Flagged rather than silently
    # mixed in: an ungated candidate offers a reader no evidence they can check,
    # so it must not read like one that does.
    ungated: bool = False
    # Chain-position awareness (2026-08-09): the lifecycle graph knows each
    # candidate's position in a `refines` chain, and position constrains what
    # kind of edge is coherent - every lifecycle edge into a chain attaches at
    # its HEAD; interior members take only `related`; a replaced decision is
    # not a lifecycle target at all. Removing the invalid option from the menu
    # beats asking a judge to avoid it (the closed-list lesson).
    #   "head"     - open: the full verdict space applies.
    #   "interior" - a refines successor holds this candidate's slot; the chain
    #                lives at `current_form`. Related-only.
    #   "replaced" - retired; never surfaced (its terminal replacement is
    #                offered instead, carrying `substitute_for`).
    chain_position: str = "head"
    # The decision ref occupying this candidate's refines slot, when interior.
    refines_taken_by: str | None = None
    # The current form of the candidate's own lineage: the chain head for an
    # interior member, the terminal replacement for a replaced one.
    current_form: str | None = None
    # Set on a candidate surfaced IN PLACE OF a replaced one: the replaced
    # entry's id, so the reader knows why this candidate is here.
    substitute_for: str | None = None


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
    semantic_status: dict[str, Any] | None = None,
    snapshot: "CorpusSnapshot | None" = None,
) -> list[LinkGap]:
    """Find entry pairs that share files or topics but carry no recorded edge.

    Candidate MEMBERSHIP is decided lexically and never by an all-pairs semantic
    scan: for each target entry the candidate set is the OLDER entries that share
    >=1 ``F:`` file OR >=1 topic with it. (Semantic similarity does participate,
    as a RANKING term over that set - see ``SEMANTIC_OVERLAP_BOOST`` - and an
    all-pairs cosine matrix IS computed for it; what the lexical gate rules out
    is cosine deciding *whether* a pair is a candidate. Cosine is dense, so that
    would make every earlier entry a candidate for every later one.)

    SINCE 2026-08-09 a bounded second source runs after that gated set: up to
    ``UNGATED_CANDIDATE_CAP`` further candidates on semantic rank ALONE, flagged
    ``ungated=True``. The paragraph above rules out an unbounded cosine
    THRESHOLD, which is still ruled out; a bounded top-N is a different thing
    and does not make every earlier entry a candidate. It exists because the
    gate's blind spot is structural rather than unlikely - a genuinely related
    entry sharing no file, title term or unsuppressed topic can never appear,
    however related it is, so the gate silently caps what any downstream
    judgment can reach. Skipped entirely when semantic ranking is off.
    File overlap qualifies a pair even when no
    topic is shared - matching files override the absence of a topic link.
    Candidates already captured by any edge (``related_entries`` /
    ``replaces`` / ``evolves``, entry YAML or a link sidecar) are dropped, so
    only genuine gaps remain. The survivors rank by IDF-weighted file overlap
    (hub files like a shared app.js contribute ~nothing) then shared-topic
    count - the classification into replaces/evolves/related is left to the
    caller (the end-of-session sweep). Read-only; forward-only by construction.

    ``session_date`` (YYYY-MM-DD) scopes the TARGETS to one session's entries
    while candidates remain the full corpus - the end-of-session sweep audits
    only the entries it just wrote (O(K*N), K = today's entries) instead of
    re-auditing history every session.

    ``semantic_enabled=False`` ranks lexically and skips the embedding provider
    entirely, so no model is loaded (``--no-semantic`` on the CLI). ``semantic_status``,
    if given, is a dict this fills with ``requested``/``active``/``provider``/
    ``fallback_reason`` so a caller can report that ranking degraded to lexical
    instead of presenting a silently different ordering as if nothing changed.
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

    # Seeded BEFORE the empty-corpus early return: left unset there, a caller
    # reading `requested` would be told semantic ranking was never asked for.
    if semantic_status is not None:
        semantic_status.update(requested=semantic_enabled, active=False, provider=None, fallback_reason=None)

    raw_chunks = (
        snapshot.chunks("entry", "raw") if snapshot is not None
        else tuple(extract_memory_chunks(cwd, granularity="entry"))
    )
    chunks = [
        chunk for chunk in augment_chunks_with_topic_sidecars(raw_chunks, cwd) if chunk.entry_id
    ]
    if not chunks:
        return []
    by_id = {chunk.entry_id: chunk for chunk in chunks}
    if entry_id is not None and entry_id not in by_id:
        raise LookupError(f"entry_id {entry_id} not found")

    sidecars = entry_link_sidecars(cwd)

    # Chain-position context (2026-08-09): each candidate is annotated from the
    # decision-keyed refines spine and the replacement graph, so an incoherent
    # lifecycle target is marked (interior member: related-only, the chain lives
    # at its head) or never offered at all (replaced: its terminal replacement
    # is surfaced instead) at candidate-generation time - the closed-list
    # lesson: do not ask a judge to avoid an answer you can remove from the
    # menu. This filters a CANDIDATE list; retrieval elsewhere is untouched.
    from .semantic_cache import (
        build_refines_spine,
        build_related_entry_graph,
        replacing_lineage_heads,
    )

    # Fail-open like the sibling call sites (`check_session_links`,
    # `_adr_head_reviews`): the annotation is advisory context on a candidate
    # list, not a gate, so a spine failure degrades to unannotated candidates
    # rather than taking down the audit (and the whole ESR preflight with it).
    try:
        augmented_chunks = augment_chunks_with_link_sidecars(chunks, cwd)
        spine = build_refines_spine(augmented_chunks)
        lineage_graph = build_related_entry_graph(cwd, chunks=augmented_chunks)
    except Exception:
        spine = None
        lineage_graph = {}
    taken_by_entry: dict[str, list[tuple[tuple[str, str], tuple[tuple[str, str], ...]]]] = {}
    if spine is not None:
        for spine_key, spine_successors in spine.successors.items():
            taken_by_entry.setdefault(spine_key[0], []).append((spine_key, spine_successors))

    def _decision_ref(key: tuple[str, str]) -> str:
        return f"{key[0]}:{key[1]}" if key[1] else key[0]

    def _annotate_chain_position(candidate: LinkGapCandidate) -> LinkGapCandidate:
        if spine is None:
            return candidate
        taken = taken_by_entry.get(candidate.entry_id)
        if not taken:
            return candidate
        spine_key, spine_successors = taken[0]
        walked = spine.head(*spine_key)
        return replace(
            candidate,
            chain_position="interior",
            refines_taken_by=", ".join(_decision_ref(s) for s in spine_successors),
            current_form=_decision_ref(walked[0]) if walked else _decision_ref(spine_successors[0]),
        )

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
        # Union here too: a shared topic is evidence two entries are about the
        # same thing whether a human or a sidecar said so. NOTE this composes two
        # inference layers - a topic backfill widens link audit's candidate set,
        # which is the input the link swarm judges. Both stay suggest-only and
        # human-gated, but the composition is real and was never separately
        # chosen; see the topic-consumer decision entry.
        topics_of[chunk.entry_id or ""] = set(chunk.topics) | set(chunk.inferred_topics)
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
        return (
            set(chunk.related_entries)
            | set(sidecar.get("related_entries", ()))
            # Decision-level related refs (`<id>:dN`, since 2026-07-25) never
            # project to the entry-level related list, but for gap-finding the
            # pair is linked - same rule as lifecycle_of below.
            | {eid for kind, _src, eid, *_ in sidecar.get("decision_edges", ()) if kind == "related"}
            | {eid for kind, _src, eid, *_ in chunk.decision_edges if kind == "related"}
        )

    def lifecycle_of(chunk: MemoryChunk) -> set[str]:
        sidecar = sidecars.get(chunk.entry_id or "", {})
        return (
            set(chunk.replaces)
            | set(chunk.evolves)
            | set(sidecar.get("replaces", ()))
            | set(sidecar.get("evolves", ()))
            # A decision-level ref (`<id>:dN`) records the pair at FINER
            # granularity. It deliberately never projects into the entry-level
            # edge sets, but for gap-finding the pair is linked - without this
            # union every decision-narrowed edge re-surfaces as a "gap" forever.
            # Both homes count: sidecar blocks and, since the write-time
            # grammar (2026-07-24), the entry's own yaml.
            | {
                eid
                for kind, _src, eid, *_ in sidecar.get("decision_edges", ())
                if kind in ("replaces", "evolves")
            }
            | {
                eid
                for kind, _src, eid, *_ in chunk.decision_edges
                if kind in ("replaces", "evolves")
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
    provider_name: str | None = None
    fallback_reason: str | None = None
    if semantic_enabled:
        vectors, provider_name, fallback_reason = _embed_entries_for_link_audit(chunks)
    if semantic_status is not None:
        semantic_status.update(
            requested=semantic_enabled,
            active=bool(vectors),
            provider=provider_name,
            fallback_reason=fallback_reason,
        )

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
            lexical = FILE_OVERLAP_BOOST * sum(idf(ref) for ref in shared_files) + TITLE_OVERLAP_BOOST * sum(
                title_idf(term) for term in shared_title
            )
            similarity = semantic_similarity(tid, cid)
            score = lexical + SEMANTIC_OVERLAP_BOOST * similarity
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
                    lexical_score=round(lexical, 6),
                    semantic_score=round(similarity, 6) if vectors else None,
                )
            )
        candidates.sort(key=lambda c: (c.file_overlap_score, len(c.shared_topics)), reverse=True)
        selected = candidates[:top_k]

        # THE UNGATED PASS. Everything above is bounded by the lexical gate, so a
        # genuinely related entry sharing no file, title term or unsuppressed
        # topic is invisible to it however related it is - the swarm cannot judge
        # what it is never shown. This adds a bounded top-N on semantic rank
        # alone, appended AFTER the slice so it neither competes in the sort
        # above (which has no stable tie-break beyond score and topic count) nor
        # displaces a gated candidate.
        #
        # The docstring's objection to semantic membership - "cosine is dense, so
        # that would make every earlier entry a candidate for every later one" -
        # is an argument against an unbounded cosine THRESHOLD, which this is
        # not. Cost is already sunk: the all-pairs matrix is computed for
        # ranking regardless.
        #
        # Skipped outright when `vectors` is empty (--no-semantic, or a provider
        # that failed to load), because `semantic_similarity` returns 0.0 for
        # every pair there and a top-N over all-zeros is an arbitrary set wearing
        # the authority of a ranking.
        if vectors:
            gated_ids = {candidate.entry_id for candidate in candidates}
            pool: list[tuple[float, str, Any]] = []
            for chunk in chunks:
                cid = chunk.entry_id or ""
                if cid == tid or order[cid] >= target_key:
                    continue
                if cid in target_lifecycle or cid in gated_ids:
                    continue
                # Also skip a pair the target already calls `related`. The gate
                # suppresses topic-only candidates for exactly that reason - "it
                # isn't worth flagging a topic-mate you already linked" - and an
                # ungated candidate carries strictly WEAKER evidence than a
                # topic-only one, so it cannot justify a laxer rule. The
                # upgrade case (related -> lifecycle) is still surfaced by the
                # gated path whenever files or title terms back it.
                if cid in target_related:
                    continue
                similarity = semantic_similarity(tid, cid)
                if similarity <= 0.0:
                    continue
                pool.append((similarity, cid, chunk))
            # entry_id breaks a cosine tie, so the set is reproducible run to run.
            pool.sort(key=lambda item: (item[0], item[1]), reverse=True)
            for similarity, cid, chunk in pool[:UNGATED_CANDIDATE_CAP]:
                selected.append(
                    LinkGapCandidate(
                        entry_id=cid,
                        title=chunk.title,
                        session_date=chunk.session_date.isoformat(),
                        # Recomputed rather than assumed empty: a pair suppressed
                        # for being already-`related` can still share topics, and
                        # the reader should see them.
                        shared_files=tuple(sorted(target_files & file_refs.get(cid, set()))),
                        shared_topics=tuple(sorted(target_topics & topics_of.get(cid, set()))),
                        shared_title_terms=tuple(sorted(target_title_terms & title_terms.get(cid, set()))),
                        file_overlap_score=round(SEMANTIC_OVERLAP_BOOST * similarity, 6),
                        already_related=cid in target_related,
                        decisions=decisions_of.get(cid, ()),
                        lexical_score=0.0,
                        semantic_score=round(similarity, 6),
                        ungated=True,
                    )
                )

        # Chain-position pass over the finished selection: replaced candidates
        # are dropped (their terminal replacement substitutes when it is itself
        # a valid, unlinked, OLDER candidate); interior chain members stay but
        # carry the position and the reason. Runs after the gated + ungated
        # assembly so neither source escapes it.
        final: list[LinkGapCandidate] = []
        selected_ids = {candidate.entry_id for candidate in selected}
        for candidate in selected:
            node = lineage_graph.get(candidate.entry_id)
            if node is not None and node.replaced_by:
                for rep in replacing_lineage_heads(lineage_graph, candidate.entry_id):
                    if (
                        rep == tid
                        or rep in selected_ids
                        or rep in target_lifecycle
                        or rep not in by_id
                        or order[rep] >= target_key
                    ):
                        continue
                    rep_chunk = by_id[rep]
                    rep_files = tuple(sorted(target_files & file_refs.get(rep, set())))
                    rep_topics = tuple(sorted(target_topics & topics_of.get(rep, set())))
                    rep_title = tuple(sorted(target_title_terms & title_terms.get(rep, set())))
                    rep_lexical = FILE_OVERLAP_BOOST * sum(idf(ref) for ref in rep_files) + TITLE_OVERLAP_BOOST * sum(
                        title_idf(term) for term in rep_title
                    )
                    rep_similarity = semantic_similarity(tid, rep)
                    final.append(
                        _annotate_chain_position(
                            LinkGapCandidate(
                                entry_id=rep,
                                title=rep_chunk.title,
                                session_date=rep_chunk.session_date.isoformat(),
                                shared_files=rep_files,
                                shared_topics=rep_topics,
                                shared_title_terms=rep_title,
                                file_overlap_score=round(rep_lexical + SEMANTIC_OVERLAP_BOOST * rep_similarity, 6),
                                already_related=rep in target_related,
                                decisions=decisions_of.get(rep, ()),
                                lexical_score=round(rep_lexical, 6),
                                semantic_score=round(rep_similarity, 6) if vectors else None,
                                substitute_for=candidate.entry_id,
                            )
                        )
                    )
                    selected_ids.add(rep)
                    break
                continue
            final.append(_annotate_chain_position(candidate))

        if final:
            gaps.append(
                LinkGap(
                    entry_id=tid,
                    title=target.title,
                    session_date=target.session_date.isoformat(),
                    candidates=tuple(final),
                    decisions=decisions_of.get(tid, ()),
                )
            )
    return gaps


def link_audit_payload(
    gaps: Sequence[LinkGap], semantic_status: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Canonical structured evidence for the read-only link-gap audit.

    The CLI renders this payload for ``link audit --json`` and MCP returns it
    unchanged.  Keeping the judgment-ready shape here means both surfaces use
    the identical candidate ordering, ranking provenance, decision evidence,
    and chain constraints without either owning a second serializer.
    """

    def _decision_payload(decision: DecisionSummary) -> dict[str, str]:
        return {
            "ordinal": decision.ordinal,
            "name": decision.name,
            "text": decision.text,
        }

    return {
        "semantic": dict(semantic_status or {}),
        "criteria": {
            "replaces": "the newer decision retires or replaces the older one (the older is now wrong or dead)",
            "evolves": "the newer decision refines or extends the older one while it stays valid",
            "related": "the two inform each other but neither replaces nor evolves",
            "none": "no genuine lifecycle or relatedness link — a shared file or topic is not itself a link",
            "narrowing": "identify WHICH decision at each end the link connects; address a multi-decision target as <entry_id>:dN (a single-decision entry is :d1, which denotes the same edge as entry-level)",
            "forward_only": "the audited entry is always the newer end; an edge points from it back to the older candidate, never forward",
            "chain_position": "every lifecycle edge into a refines chain attaches at its HEAD - a candidate marked interior has its refines slot taken and may receive only related; replaced candidates are never offered (their terminal replacement substitutes)",
        },
        "gaps": [
            {
                "entry_id": gap.entry_id,
                "title": gap.title,
                "session_date": gap.session_date,
                "decisions": [_decision_payload(decision) for decision in gap.decisions],
                "candidates": [
                    {
                        "entry_id": candidate.entry_id,
                        "title": candidate.title,
                        "session_date": candidate.session_date,
                        "shared_files": list(candidate.shared_files),
                        "shared_topics": list(candidate.shared_topics),
                        "shared_title_terms": list(candidate.shared_title_terms),
                        "score": candidate.file_overlap_score,
                        "lexical_score": candidate.lexical_score,
                        "semantic_score": candidate.semantic_score,
                        "already_related": candidate.already_related,
                        "ungated": candidate.ungated,
                        "chain_position": candidate.chain_position,
                        "refines_taken_by": candidate.refines_taken_by,
                        "current_form": candidate.current_form,
                        "substitute_for": candidate.substitute_for,
                        "decisions": [
                            _decision_payload(decision) for decision in candidate.decisions
                        ],
                    }
                    for candidate in gap.candidates
                ],
            }
            for gap in gaps
        ],
    }


def apply_link_gap_stubs(
    gaps: Iterable[LinkGap],
    *,
    session_date: str,
    cwd: str | Path = ".",
) -> LinkAuditApplyResult:
    """Add inert classification stubs to one dated link sidecar.

    Existing sidecar block CONTENT is never changed. New blocks carry only
    ``classify_pending: true`` plus comment-only candidate evidence, and are
    skipped when any sidecar block already exists for that source entry.
    Session entries are read only.

    The whole block region is re-sorted by heading timestamp on write, exactly
    as ``_write_chronological_link_sidecar_file`` does for the fuse - a stable
    sort, so existing blocks keep their relative order within a minute and new
    blocks land after them. This used to REFUSE (``blocks are not
    chronological``) instead, which permanently closed a date to further
    scaffolding: a sidecar is filed under its SOURCE entry's date but a later
    enrichment pass stamps its blocks with the AUTHORING wall clock (block
    identity is ``(entry_id, heading timestamp)``, so a second block for one
    entry needs a distinct stamp - see docs/3_Spec/lifecycle-edge-linking-
    sidecars.md). Those two rules together make a re-visited file legitimately
    non-chronological, and four dates in this repo's own corpus were stuck that
    way. Reordering is a pure permutation, never a content edit, and only
    happens as part of a write - a file with nothing to add is left untouched.
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
            if candidate.substitute_for:
                evidence.append(f"substitute for replaced {candidate.substitute_for}")
            if candidate.chain_position == "interior":
                # Position first among the flags below: it changes the verdict
                # space itself (related-only), not just the evidence weight.
                evidence.insert(
                    0,
                    "INTERIOR chain member - related-only; refines taken by "
                    f"{candidate.refines_taken_by}; the chain lives at {candidate.current_form}",
                )
            if candidate.ungated:
                # Stated first on read even though it is appended last: a reader
                # must know this pair carries no checkable overlap before they
                # weigh whatever else the line says.
                evidence.insert(0, "UNGATED - semantic rank only, no shared file/title/topic gate")
            suffix = f"  # {' | '.join(evidence)}" if evidence else ""
            lines.append(f"#   - {candidate.entry_id}{suffix}")
        lines.extend(["```", ""])
        return timestamp, gap.entry_id, "\n".join(lines)

    rendered = [render_stub(gap) for gap in sorted(pending, key=lambda gap: _entry_order_key(chunks[gap.entry_id]))]

    # Everything from the first block to EOF is the block region; anything
    # before it (frontmatter, and any preamble prose) is preserved verbatim.
    if existing_blocks:
        preamble = existing[: existing_blocks[0].start()].rstrip() + "\n\n"
        spans = [
            (
                match.group(1),
                existing[match.start(): (existing_blocks[index + 1].start() if index + 1 < len(existing_blocks) else len(existing))].rstrip(),
            )
            for index, match in enumerate(existing_blocks)
        ]
    else:
        preamble = existing.rstrip() + "\n\n"
        spans = []

    # Existing first, incoming second, then a STABLE sort on the heading stamp:
    # blocks already in the file keep their relative order (a write never
    # re-positions history it did not touch) and new blocks land after existing
    # ones sharing that minute, which is what "append" means. Same contract as
    # _session_record_sort_key.
    ordered = sorted(spans + [(item[0], item[2].rstrip()) for item in rendered], key=lambda item: item[0])
    write_text_file(target, preamble + "\n\n".join(text for _timestamp, text in ordered).rstrip() + "\n")
    return LinkAuditApplyResult(
        path=target,
        added_entry_ids=tuple(item[1] for item in rendered),
        skipped_entry_ids=skipped,
    )


def describe_refines_chain(cwd: str | Path, ref: str) -> dict[str, Any] | None:
    """Derived view of the refines chain a decision belongs to.

    A chain is a thing, not just a path you can walk: the life of one decision
    through its successive forms. Its identity is its ROOT decision - the one
    member with no `refines` predecessor - which is stable under growth, where
    an id keyed to the head would be renamed by every extension. Entirely
    derivable from the edges (Constitution #6: a derived, rebuildable
    projection, never a second source of truth).

    ``ref`` is ``mse_x`` or ``mse_x:dN``. Returns None when the decision
    belongs to no chain (no refines predecessor or successor). The view carries
    root, ordered members (with dates/titles), head, length, and which ADR(s)
    hold a member as their authoritative decision.
    """
    from .semantic_cache import build_refines_spine, extract_memory_chunks

    chunks = augment_chunks_with_link_sidecars(
        extract_memory_chunks(cwd, granularity="entry"), cwd
    )
    entry_id, _, ordinal = ref.strip().partition(":")
    spine = build_refines_spine(chunks)
    chain = spine.chain_through(entry_id, ordinal or None)
    if not chain:
        return None
    by_id = {chunk.entry_id: chunk for chunk in chunks if chunk.entry_id}

    def _ref(key: tuple[str, str]) -> str:
        return f"{key[0]}:{key[1]}" if key[1] else key[0]

    members = [
        {
            "ref": _ref(key),
            "session_date": by_id[key[0]].session_date.isoformat() if key[0] in by_id else None,
            "title": by_id[key[0]].title if key[0] in by_id else None,
        }
        for key in chain
    ]
    adrs: list[dict[str, str]] = []
    try:
        from .adr import iter_adrs

        chain_keys = set(chain)
        for record in iter_adrs(cwd):
            head_ref = record.authoritative_decision
            if not head_ref:
                continue
            adr_entry, _, adr_ordinal = head_ref.partition(":")
            if spine.key(adr_entry, adr_ordinal or None) in chain_keys:
                adrs.append({"adr_id": record.adr_id, "member": head_ref})
    except Exception:
        # The ADR overlay is context, not the chain: a malformed ADR store must
        # not make the chain itself unreadable.
        adrs = []
    return {
        "root": members[0]["ref"],
        "head": members[-1]["ref"],
        "length": len(chain),
        "members": members,
        "adrs": adrs,
    }


GRAPH_SNAPSHOT_SCHEMA_VERSION = 1


def effective_graph_snapshot(cwd: str | Path = ".") -> dict[str, Any]:
    """A structural snapshot of the effective evolves/refines graph.

    Built for `links graph-diff`, whose reason for existing is a corpus
    invariant that has caught silent corruption twice - once as 807 vanished
    `evolves` edges while `links check` read OK throughout, once as a +3 edge
    resurrection - and until now only lived in throwaway campaign scripts.

    Read over the SAME effective corpus every graph consumer reads:
    ``augment_chunks_with_link_sidecars(extract_memory_chunks(cwd,
    granularity="entry"), cwd)`` feeding ``build_related_entry_graph`` and
    ``build_refines_spine``. A snapshot taken before a bulk sidecar write and
    one taken after therefore go through the identical union/retract
    pipeline; any difference is a real graph change, not a reader difference.

    ``evolves`` carries each node's stored outbound edges (the entry-level
    lifecycle facts `links graph-diff` gates on); ``refines_successors``
    carries the decision-keyed typed spine (informational - a retype
    campaign changes this by design). ``aggregates`` gives quick corpus-wide
    counts a human can sanity-check without diffing the maps by eye. A plain
    rebuildable projection (Constitution #6) - no automated baseline
    persistence exists anywhere in this codebase (`quality.py`'s report is
    the closest precedent and it, too, is recomputed on demand rather than
    stored), so this is a `json.dump`/`json.load` shape and nothing more.
    """
    from .core import _git_text
    from .semantic_cache import build_refines_spine

    chunks = augment_chunks_with_link_sidecars(
        extract_memory_chunks(cwd, granularity="entry"), cwd
    )
    graph = build_related_entry_graph(cwd, chunks=chunks)
    spine = build_refines_spine(chunks)

    code, head = _git_text(Path(cwd).resolve(), ("rev-parse", "HEAD"))
    corpus_revision = head if code == 0 and head else None

    def _spine_ref(key: tuple[str, str]) -> str:
        return f"{key[0]}:{key[1]}" if key[1] else key[0]

    evolves = {
        entry_id: sorted(node.evolves)
        for entry_id, node in graph.items()
        if node.evolves
    }
    refines_successors: dict[str, list[str]] = {}
    for key, successors in spine.successors.items():
        if not successors:
            continue
        refines_successors[_spine_ref(key)] = sorted(_spine_ref(s) for s in successors)

    return {
        "schema_version": GRAPH_SNAPSHOT_SCHEMA_VERSION,
        "corpus_revision": corpus_revision,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "aggregates": {
            "evolves_refs": sum(len(node.evolves) for node in graph.values()),
            "nodes_with_successors": sum(1 for node in graph.values() if node.evolved_by),
            "nodes_refined": sum(1 for successors in spine.successors.values() if successors),
        },
        "evolves": evolves,
        "refines_successors": refines_successors,
    }


def diff_graph_snapshots(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    """Structural diff between two ``effective_graph_snapshot()`` payloads.

    THE GATE (approved design): verdict is ``"changed"`` iff the entry-level
    `evolves` edge set differs - any per-node addition/removal in ``evolves``,
    or either evolves-related aggregate (``evolves_refs``,
    ``nodes_with_successors``) differing. This is exactly the historical
    campaign assertion that caught both the 807-edge vanishing and the +3
    edge resurrection.

    `refines_successors` deltas (and the `nodes_refined` aggregate) are always
    reported but never flip the verdict - a retype campaign (untyped ->
    `refines`/`builds-on`) changes typing BY DESIGN, and gating on it would
    fail a correct campaign. This mirrors `augment_chunks_with_link_sidecars`:
    a retract-and-retype must leave the effective `evolves` edge set alone
    while changing its recorded type.

    A ``schema_version`` mismatch is a hard error - per-node shapes are not
    guaranteed comparable across versions - and short-circuits before any
    other comparison. Reported as ``verdict: "error"`` in the return dict
    rather than raised, so a CLI caller can render it as an ordinary payload.
    """
    before_schema = before.get("schema_version")
    after_schema = after.get("schema_version")
    if before_schema != after_schema:
        return {
            "verdict": "error",
            "error": f"schema_version mismatch: before={before_schema!r} after={after_schema!r}",
            "aggregate_deltas": {},
            "evolves_added": {},
            "evolves_removed": {},
            "refines_successors_added": {},
            "refines_successors_removed": {},
        }

    def _agg_delta(key: str) -> dict[str, int]:
        b = int(before.get("aggregates", {}).get(key, 0) or 0)
        a = int(after.get("aggregates", {}).get(key, 0) or 0)
        return {"before": b, "after": a, "delta": a - b}

    aggregate_deltas = {
        key: _agg_delta(key)
        for key in ("evolves_refs", "nodes_with_successors", "nodes_refined")
    }

    def _set_deltas(
        before_map: Mapping[str, Any], after_map: Mapping[str, Any]
    ) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        added: dict[str, list[str]] = {}
        removed: dict[str, list[str]] = {}
        for node_id in sorted(set(before_map) | set(after_map)):
            b = set(before_map.get(node_id) or ())
            a = set(after_map.get(node_id) or ())
            gained = sorted(a - b)
            lost = sorted(b - a)
            if gained:
                added[node_id] = gained
            if lost:
                removed[node_id] = lost
        return added, removed

    evolves_added, evolves_removed = _set_deltas(
        before.get("evolves", {}), after.get("evolves", {})
    )
    refines_added, refines_removed = _set_deltas(
        before.get("refines_successors", {}), after.get("refines_successors", {})
    )

    edge_set_changed = (
        bool(evolves_added)
        or bool(evolves_removed)
        or aggregate_deltas["evolves_refs"]["delta"] != 0
        or aggregate_deltas["nodes_with_successors"]["delta"] != 0
    )

    return {
        "verdict": "changed" if edge_set_changed else "unchanged",
        "error": None,
        "aggregate_deltas": aggregate_deltas,
        "evolves_added": evolves_added,
        "evolves_removed": evolves_removed,
        "refines_successors_added": refines_added,
        "refines_successors_removed": refines_removed,
    }


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
        "replaces": list(chunk.replaces),
        "evolves": list(chunk.evolves),
        "continuity": [
            {"kind": block.kind, "from": block.from_ref, "to": block.to_ref}
            for block in chunk.continuity
        ],
        "topics": list(chunk.topics),
        # A SEPARATE key, never folded into `topics`: a consumer must be able to
        # tell a slug a human wrote from one a sidecar attributed later.
        "inferred_topics": list(chunk.inferred_topics),
        "line_range": [chunk.start_line, chunk.end_line],
        "heading_path": list(chunk.heading_path),
        "matched_terms": list(result.matched_terms),
        "matched_fields": list(result.matched_fields),
        # Decision results carry the complete DRAFT block; everything else is windowed on the
        # terms that made it rank. Note the branch is on the chunk's ACTUAL granularity, not the
        # requested one - an entry with no decision section comes back labelled "entry" even on a
        # decision-granularity search, which is why the preview path has to be good rather than
        # merely a fallback.
        "excerpt": (
            _decision_body(chunk.text)
            if chunk.granularity == "decision"
            else _selection_preview(chunk.text, matched_terms=result.matched_terms)
        ),
        "entry_id": chunk.entry_id,
        "user_initials": chunk.user_initials,
        "agent_type": chunk.agent_type,
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
        "replaces": list(chunk.replaces),
        "evolves": list(chunk.evolves),
        "continuity": [
            {"kind": block.kind, "from": block.from_ref, "to": block.to_ref}
            for block in chunk.continuity
        ],
        "topics": list(chunk.topics),
        # Separate keys for the same reason as in the search-result payload: the
        # rolled-up view for entry-level consumers, plus the per-decision
        # attribution a decision-node graph needs.
        "inferred_topics": list(chunk.inferred_topics),
        "inferred_decision_topics": [
            {"decision": ordinal or None, "topic": slug} for ordinal, slug in chunk.inferred_decision_topics
        ],
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
                "excerpt": _selection_preview(
                    section.chunk.text, matched_terms=section.matched_terms
                ),
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


# A decision result is served WHOLE: the agent gets the complete DRAFT block (D/R/A/F/T),
# not a preview of it, because the block is the unit it must reason about. 2500 chars covers
# 97.6% of recorded decisions in the reference corpus; the rest are truncated with an explicit
# marker so an agent knows to fetch rather than assuming it saw everything.
DECISION_TEXT_LIMIT = 2500


_ENTRY_SECTION_RE = re.compile(r"^###\s+(?!#)(.+?)\s*$")
_DECISIONS_CONTAINER_RE = re.compile(r"^decisions?$", re.IGNORECASE)


def entry_context_sections(entry_text: str) -> list[dict[str, str]]:
    """The entry's non-decision `###` sections, in document order.

    A decision block carries its own D/R/A/F/T, but that is not the whole record of the decision.
    The `### Summary` that frames it and the `### Follow-up` that continues it belong to the entry,
    and a reader handed only the block is missing context the author wrote deliberately - what the
    session was doing, what was validated, what was left open. Anything the author put at entry
    level may bear on any decision in that entry, so the whole set travels rather than a guess at
    which parts are relevant.

    The decisions container is excluded: its body IS the decision blocks, so including it would
    return every sibling decision alongside the one that was asked for. `####` headings never start
    a section here, so a decision heading inside the container cannot be mistaken for one.
    """
    sections: list[dict[str, str]] = []
    heading: str | None = None
    body: list[str] = []
    for line in entry_text.splitlines():
        match = _ENTRY_SECTION_RE.match(line)
        if match:
            if heading is not None:
                sections.append({"heading": heading, "text": "\n".join(body).strip()})
            heading = match.group(1).strip()
            body = []
            continue
        if heading is not None:
            body.append(line)
    if heading is not None:
        sections.append({"heading": heading, "text": "\n".join(body).strip()})
    return [
        section
        for section in sections
        if section["text"] and not _DECISIONS_CONTAINER_RE.match(section["heading"])
    ]


# A leading ```yaml ... ``` block is the entry's metadata fence. Non-greedy, so it stops at the
# FIRST closing fence rather than swallowing a later code block in the body.
_METADATA_FENCE_RE = re.compile(r"\A\s*```[a-zA-Z]*[ \t]*\n.*?\n[ \t]*```[ \t]*\n?", re.DOTALL)
PREVIEW_LIMIT = 280
_PREVIEW_LEAD = 60
_PREVIEW_MARKER = " [preview - call memory_get_chunk for the full entry]"


def _strip_metadata_fence(text: str) -> str:
    """Drop a leading metadata fence: it is envelope, never prose.

    Every field inside it - entry_id, user_initials, branch, topics, evolves - is already a
    structured key on the same search result, so serving it as the preview spends the reader's
    selection budget restating what it already has. Measured before removing it: 857 of 891 entry
    chunks led with the fence, it took a median 84% of the 280-character budget, and 124 previews
    never escaped it at all.
    """
    return _METADATA_FENCE_RE.sub("", text, count=1).lstrip()


def _selection_preview(
    text: str, *, matched_terms: Sequence[str] = (), limit: int = PREVIEW_LIMIT
) -> str:
    """The span a reader needs to decide whether to fetch this chunk in full.

    A preview answers one question - "is this the one I want?" - so it is windowed on the terms
    that made the chunk rank rather than taken from the head. `matched_terms` is already computed
    by the ranker and already on the wire, so this costs no re-scoring. Without them (the
    retrieval-spec path carries a candidate, not a ranked result) it degrades to the head of the
    stripped text, still strictly better than leading with metadata.

    Both cut ends are marked: an elided head with a leading ellipsis, an elided tail with a marker
    naming the follow-up call - matching `_decision_body`, so a fragment never reaches a reader
    announcing itself only as "...".
    """
    body = " ".join(_strip_metadata_fence(text).split())
    if len(body) <= limit:
        return body

    start = 0
    lowered = body.lower()
    hits = [
        found
        for found in (lowered.find(term.lower()) for term in matched_terms if term)
        if found >= 0
    ]
    if hits:
        # Lead in a little so the window does not open mid-sentence.
        start = max(0, min(hits) - _PREVIEW_LEAD)
    room = max(limit - (4 if start else 0) - len(_PREVIEW_MARKER), 0)
    window = body[start:start + room].rstrip()
    return ("... " if start else "") + window + _PREVIEW_MARKER


def _decision_body(text: str, limit: int = DECISION_TEXT_LIMIT) -> str:
    """The whole decision block, newlines preserved, truncated only past the cap."""
    body = text.strip()
    if len(body) <= limit:
        return body
    marker = "\n\n[truncated - call memory_get_chunk for the full decision]"
    return body[:limit].rstrip() + marker

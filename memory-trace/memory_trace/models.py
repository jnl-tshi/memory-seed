"""Pydantic response models for the versioned (/api/v1/*) Memory Trace API.

These formalize the exact dict shapes the LenseService methods already
return (see lense.py's _chunk_to_api/_ranked_to_api/_rollup_to_api/_graph_node
family) - the service itself is untouched and keeps returning plain dicts.
FastAPI validates/coerces those dicts against these models via response_model
on the /api/v1/* routes only; the legacy unversioned /api/* routes are
unaffected. Two fields go beyond what the service emits today -
ProvenanceClass and EdgeType - because docs/3_Spec/memory-trace-trail-search-
and-graph-ux.md and docs/3_Spec/graph-edge-contract.md name them as
forward-stable contract types even though every node emitted today is
"authored_memory" and every edge kind is already produced by _graph_edges.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel


class ProvenanceClass(str, Enum):
    """Fixed enum from the Trail/Graph UX spec (SS3.2) so future event types
    (PR review, CI, release, ...) never masquerade as authored memory. Only
    ``authored_memory`` is ever emitted today."""

    authored_memory = "authored_memory"
    source_control = "source_control"
    pr_review = "pr_review"
    automation_ci = "automation_ci"
    annotation = "annotation"
    release = "release"
    generated_artefact = "generated_artefact"


class EdgeType(str, Enum):
    """Every edge kind _graph_edges() can produce (graph-edge-contract.md)."""

    related = "related"
    supersedes = "supersedes"
    evolves = "evolves"
    branch = "branch"
    topic = "topic"
    agent = "agent"
    day = "day"


class RuntimeInfo(BaseModel):
    label: str
    workspace_root: str
    memory_dir: str
    cache_path: str
    legacy: bool
    entry_count: int
    date_bounds: list[str | None]


class FacetsRuntimeInfo(RuntimeInfo):
    chunk_count: int


class Facets(BaseModel):
    runtime: FacetsRuntimeInfo
    agents: dict[str, int]
    users: dict[str, int]
    topics: dict[str, int]


class ChunkSummary(BaseModel):
    """The shape shared by every chunk-derived model (_chunk_to_api)."""

    chunk_id: str
    entry_id: str | None
    title: str
    entry_title: str | None
    date: str
    time: str | None
    entry_datetime: str | None
    source: str | None
    path: str | None
    line_range: list[int]
    heading_path: list[str]
    sections: list[str]
    tags: list[str]
    topics: list[str]
    contexts: list[str]
    lexical_terms: list[str]
    agent_type: str | None
    agent_name: str | None
    user: str | None
    branch: str | None
    text: str
    excerpt: str
    granularity: str
    related_entries: list[str]


class ChunkBrief(BaseModel):
    """The compact shape used for commit_entries/suggestions (_chunk_summary)."""

    chunk_id: str
    entry_id: str | None
    title: str
    date: str
    time: str | None
    agent: str
    topics: list[str]


class MatchedSection(BaseModel):
    chunk_id: str
    heading_path: list[str]
    line_range: list[int]
    excerpt: str


class SearchResult(ChunkSummary):
    score: float
    match_score: float
    lexical_score: float
    semantic_score: float | None
    recency_multiplier: float
    matched_terms: list[str]
    matched_fields: list[str]
    score_explanation: str
    # Entry-level rollup search only (query non-empty, granularity=entry);
    # absent (defaulted) for section/all-granularity ranked results.
    best_match_chunk_id: str | None = None
    score_source: str | None = None
    matched_sections: list[MatchedSection] = []


class SearchResponse(BaseModel):
    query: str
    limit: int
    cursor: str | None
    next_cursor: str | None
    total: int
    results: list[SearchResult]


class CommitInfo(BaseModel):
    sha: str
    short: str
    date: str
    subject: str


class Suggestions(BaseModel):
    same_day: list[ChunkBrief]
    same_topic: list[ChunkBrief]
    same_agent: list[ChunkBrief]


class ChunkMetadata(BaseModel):
    source: str | None
    agent_type: str | None
    agent_name: str | None
    user: str | None
    file_hash_id: str | None
    project_path: str | None
    subproject_path: str | None
    granularity: str


class ChunkResponse(ChunkSummary):
    commit: CommitInfo | None
    commit_entry_ids: list[str]
    commit_entries: list[ChunkBrief]
    commit_tracking: bool
    backlinks: list[str]
    # Sidecar rendering itself is out of scope for this contract (deferred
    # decision-diagram integration); kept loose since only metadata passes
    # through today.
    diagrams: list[dict[str, Any]]
    suggestions: Suggestions
    metadata: ChunkMetadata


class GraphNode(BaseModel):
    id: str
    chunk_id: str
    entry_id: str | None
    title: str
    date: str
    datetime: str | None
    branch: str | None
    branch_inferred: bool
    agent: str
    topics: list[str]
    granularity: str
    connectivity: int
    importance_score: float
    provenance_class: ProvenanceClass = ProvenanceClass.authored_memory


class GraphEdge(BaseModel):
    source: str
    target: str
    type: EdgeType


class GraphResponse(BaseModel):
    entry_id: str | None
    granularity: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    edge_types: list[EdgeType]


class TrailEvent(GraphNode):
    """The Trail's own event contract. Structurally identical to GraphNode
    today (both are served by the same LenseService.graph() call, entry
    granularity) - named distinctly because the product UX treats Trail as
    the primary surface and Graph as a secondary, general-purpose one; a
    future divergence (e.g. Trail-only fields) should widen this model, not
    GraphNode."""


class TrailResponse(BaseModel):
    entry_id: str | None
    granularity: str
    nodes: list[TrailEvent]
    edges: list[GraphEdge]
    edge_types: list[EdgeType]

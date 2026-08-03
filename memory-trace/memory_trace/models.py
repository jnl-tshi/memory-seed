"""Pydantic response models for the versioned (/api/v1/*) Memory Trace API.

These formalize the exact dict shapes the TraceService methods already
return (see service.py's _chunk_to_api/_ranked_to_api/_rollup_to_api/_graph_node
family) - the service itself is untouched and keeps returning plain dicts.
FastAPI validates/coerces those dicts against these models via response_model
on the /api/v1/* routes only; the legacy unversioned /api/* routes are
unaffected. Two fields go beyond what the service emits today -
ProvenanceClass and EdgeType - because docs/3_Spec/memory-trace-trail-search-
and-graph-ux.md and docs/3_Spec/graph-edge-contract.md name them as
forward-stable contract types even though every node emitted today is
"authored_memory" and every edge kind is already produced by _graph_edges.

The commit-accurate Trail merge geometry (MergeEvent/BranchInfo on the
graph/trail responses, merged_by on the chunk response) shipped legacy-only
under the "vanilla only, polish first" ruling; after a full release cycle the
polish condition was met, so v1 now formalizes it too - additively (old
clients ignore the new keys).
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


class AuthorityClass(str, Enum):
    """What authority an item's *meaning* carries — a separate axis from
    ``ProvenanceClass`` (where it came from). Fixed vocabulary from the
    provenance/authority taxonomy (BG1) so generated or provider-derived content
    can never masquerade as authored project memory.

    Confidence is separate metadata and can never upgrade authority.
    """

    authored = "authored"  # explicit project memory, or an authorised annotation
    computed_canonical = "computed_canonical"  # deterministic Memory Seed semantics (inverse edges)
    git_derived = "git_derived"  # deterministic repository evidence tied to a revision
    provider_extracted = "provider_extracted"  # external observation, highest certainty
    provider_resolved = "provider_resolved"
    provider_inferred = "provider_inferred"  # external observation, lowest certainty
    generated = "generated"  # model/rule-generated interpretation; advisory until promoted


class EdgeType(str, Enum):
    """Every edge kind _graph_edges() can produce (graph-edge-contract.md)."""

    related = "related"
    replaces = "replaces"
    evolves = "evolves"
    branch = "branch"
    topic = "topic"
    agent = "agent"
    day = "day"


class WorktreeInfo(BaseModel):
    id: str
    path: str
    branch: str | None
    label: str
    is_primary: bool
    is_default: bool


class WorktreesResponse(BaseModel):
    worktrees: list[WorktreeInfo]
    default: str


class AdrPredecessor(BaseModel):
    decision: str
    relation_assertion: str


class AdrEvent(BaseModel):
    kind: str
    event_id: str
    timestamp: str
    source: str
    decision_ref: str | None = None
    update_entry_id: str | None = None
    expected_authoritative_decision: str | None = None
    predecessors: list[AdrPredecessor] = Field(default_factory=list)
    supporting_decisions: list[str] = Field(default_factory=list)
    matched_decisions: list[str] = Field(default_factory=list)
    decision: str = ""
    why: str = ""
    evolution: str = ""
    reason: str = ""
    replacement_adr: str | None = None


class AdrCurrent(BaseModel):
    decision_ref: str | None = None
    decision: str = ""
    why: str = ""
    evolution: str = ""


class AdrRecordResponse(BaseModel):
    adr_id: str
    title: str
    topics: list[str] = Field(default_factory=list)
    created_at: str
    source: str
    current_status: str
    authoritative_decision: str | None = None
    pending_decisions: list[str] = Field(default_factory=list)
    rejected_decisions: list[str] = Field(default_factory=list)
    superseded_by: str | None = None
    membership: list[str] = Field(default_factory=list)
    current: AdrCurrent
    digest: str
    path: str | None = None
    events: list[AdrEvent] = Field(default_factory=list)
    source_excerpts: dict[str, str] = Field(default_factory=dict)


class AdrsResponse(BaseModel):
    adrs: list[AdrRecordResponse]


class DirectoryEntry(BaseModel):
    name: str
    path: str
    # Cheap existence check only (a directory named .memory-seed is present) -
    # not a doctor() pass/fail. The picker uses this to hint which folders are
    # worth trying to open, not to promise they will open successfully.
    has_memory_seed: bool


class BrowseResponse(BaseModel):
    path: str
    parent: str | None
    entries: list[DirectoryEntry]


class OpenProjectResponse(BaseModel):
    ok: bool
    worktree: WorktreeInfo | None = None
    # Human-readable doctor() findings when ok is False - what is missing or
    # out of date, so the picker can say why rather than just refusing.
    issues: list[str] = Field(default_factory=list)


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


class OntologyNode(BaseModel):
    """One vocabulary slug, with its subtree. Recursive to arbitrary depth.

    `count` is the slug's own attributions; `total` includes every descendant,
    which is what SELECTING the node returns - `expand_topic_filter` matches a
    parent against its whole subtree. A navigator that showed `count` beside a
    parent whose children hold most of the corpus would print a number that
    disagrees with the result it produces.
    """

    id: str
    name: str
    count: int = 0
    total: int = 0
    children: list["OntologyNode"] = []


class Facets(BaseModel):
    runtime: FacetsRuntimeInfo
    agents: dict[str, int]
    users: dict[str, int]
    topics: dict[str, int]
    # Qualifying topics in colour-wheel order: co-occurring topics sit adjacent,
    # so the renderer can hand out hues that form coherent neighbourhoods and
    # paint multi-topic nodes as in-family mixtures.
    topic_wheel: list[str]
    # Every authorable topic name (canonical slug AND alias) -> the root of its
    # hierarchy. Colour is assigned at the root level so the palette is bounded
    # by roots and does not grow or reshuffle as children populate; grouping and
    # filtering keep reading the child. A root maps to itself, so an unknown
    # slug can safely fall back to identity.
    topic_roots: dict[str, str]
    # Every authorable topic name -> the canonical slug it denotes. Distinguishes
    # an ALIAS (a different spelling of one concept, which must take its
    # canonical's colour) from a CHILD (a narrower concept, which earns its own) —
    # a difference topic_roots cannot express, because both map to a root. Read
    # only where colour is keyed BELOW the root: the focused-topic view.
    topic_canonical: dict[str, str] = {}
    # The vocabulary's SHAPE, per axis, as a recursive tree - what the navigator
    # renders. `topic_roots` answers "which root owns this slug" and collapses
    # everything between; a browser has to draw what it collapsed.
    #
    # Keyed BY AXIS rather than as one forest: the axes answer different
    # questions and are navigated one at a time, so a third axis is a third key
    # and no consumer change. Defaults to empty, which is also what a broken
    # vocabulary yields - a navigator that disappears beats a payload that fails.
    ontology: dict[str, list[OntologyNode]] = {}


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
    user: str | None
    branch: str | None
    text: str
    excerpt: str
    granularity: str
    related_entries: list[str]
    continuity: list["ContinuityItem"]


class ChunkBrief(BaseModel):
    """The compact shape used for commit_entries/suggestions (_chunk_summary)."""

    chunk_id: str
    entry_id: str | None
    title: str
    date: str
    time: str | None
    agent: str
    topics: list[str]


class ContinuityItem(BaseModel):
    """One authored continuity block exposed through Trace read contracts."""

    model_config = ConfigDict(populate_by_name=True)

    kind: str
    from_ref: str = Field(alias="from")
    to_ref: str | None = Field(default=None, alias="to")


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


class ForkPoint(BaseModel):
    """Where a merged branch left the trunk: the merge-base of the merge
    commit's parents. No ``subject`` - a fork point is a plain trunk commit,
    not itself a merge."""

    sha: str
    short: str
    date: str


class MergeEvent(BaseModel):
    """A trunk merge commit carrying ``Memory-Entry:`` trailers - the
    commit-accurate join between a merge and the entries it landed on main
    (``session merge-branch`` stamps one trailer per merged entry). ``entry_ids``
    is filtered to the displayed nodes."""

    sha: str
    short: str
    date: str
    subject: str
    entry_ids: list[str]


class BranchInfo(BaseModel):
    """Per-branch Trail geometry recovered from trailer ground truth: the merge
    event that closed the branch's newest displayed entry (``merge`` is None when
    that newest entry is still open - the branch dangles, no fabricated merge),
    the fork point, and ``estimated`` (True only in the pre-trailer era, where the
    frontend keeps its positional heuristic)."""

    merge: CommitInfo | None
    fork: ForkPoint | None
    estimated: bool


class Suggestions(BaseModel):
    same_day: list[ChunkBrief]
    same_topic: list[ChunkBrief]
    same_agent: list[ChunkBrief]


class ChunkMetadata(BaseModel):
    source: str | None
    agent_type: str | None
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
    # The merge commit whose Memory-Entry trailer landed this entry on the
    # trunk ("Merged to main by" in the reader) - distinct from the authoring
    # ``commit`` above. None for unmerged or pre-trailer-era entries.
    merged_by: CommitInfo | None
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
    # Decision-derived topics retain their Dn association. `topics` remains
    # entry-level so display aggregation cannot widen filtering.
    decision_topics: dict[str, list[str]] = Field(default_factory=dict)
    granularity: str
    continuity: list[ContinuityItem]
    connectivity: int
    importance_score: float
    provenance_class: ProvenanceClass = ProvenanceClass.authored_memory
    # Whether the entry carries an authored Class-2 decision-diagram sidecar.
    # The service has always computed this; declaring it stops the v1
    # response_model from stripping it (additive, defaulted).
    has_diagram: bool = False
    # Per-decision Trail rows: set ONLY when the entry has >=2 numbered
    # '#### Dn -' decisions AND the caller opted in (the /trail route). The
    # parent row carries "d1" + the group size; each extra row carries its
    # own ordinal. Ordinary/singular-decision entries keep None/0, so this
    # doubles as the "row belongs to a rendered decision group" flag.
    # Declared here (not on TrailEvent alone) because TrailEvent inherits
    # GraphNode verbatim; /graph responses simply always carry the defaults
    # - additive, same precedent as has_diagram.
    decision_ordinal: str | None = None
    decision_count: int = 0


class GraphEdge(BaseModel):
    source: str
    target: str
    type: EdgeType
    # Model confidence (0..1) for a machine-suggested edge, absent for
    # human-authored edges. Structured metadata from the link-inference
    # campaign; lets the graph weight or filter low-confidence edges.
    confidence: float | None = None


class RendererGraphSource(BaseModel):
    chunk_id: str
    entry_id: str | None
    agent: str
    topics: list[str]
    # Kept separate from entry-level `topics`; renderer aggregation is display-only.
    decision_topics: dict[str, list[str]] = Field(default_factory=dict)


class RendererGraphCommunity(BaseModel):
    id: str
    label: str
    fingerprint: str


class RendererGraphTemporal(BaseModel):
    value: str
    source: str
    precision: str


class RendererGraphNode(BaseModel):
    id: str
    node_type: str
    label: str
    provenance_class: ProvenanceClass
    authority_class: AuthorityClass
    community: RendererGraphCommunity
    temporal: RendererGraphTemporal
    connectivity: float
    importance_score: float
    revision: str | None
    provider: str | None
    stale: bool
    source: RendererGraphSource


class RendererGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    edge_type: EdgeType
    directed: bool
    evidence_refs: list[str]
    # Model confidence (0..1) for a machine-suggested edge; absent for
    # human-authored edges. See GraphEdge.confidence.
    confidence: float | None = None


class RendererGraphResponse(BaseModel):
    nodes: list[RendererGraphNode]
    edges: list[RendererGraphEdge]
    # Entries the graph can ever address (entry-id-bearing), which is smaller
    # than runtime entry_count. The coverage readout needs this denominator so
    # "X of Y shown" cannot count entries no graph could show. Optional: the
    # bounded benchmark fixtures project without it.
    entry_total: int | None = None
    # Contextual, self-excluding Area/Activity availability for this exact
    # projection. It is derived from the active view before ontology filters,
    # never from the viewport.
    ontology: dict[str, list[OntologyNode]] = {}


class GraphResponse(BaseModel):
    entry_id: str | None
    granularity: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    edge_types: list[EdgeType]
    # Commit-accurate Trail merge geometry (see MergeEvent/BranchInfo): the
    # trailer-stamped merge events touching displayed nodes, and per-branch
    # merge/fork/estimated. Empty/estimated when git or trailers are absent.
    merges: list[MergeEvent]
    branches: dict[str, BranchInfo]
    ontology: dict[str, list[OntologyNode]] = {}


class TrailEvent(GraphNode):
    """The Trail's own event contract. Structurally identical to GraphNode
    today (both are served by the same TraceService.graph() call, entry
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
    # Same commit-accurate merge geometry as GraphResponse - the Trail is the
    # primary consumer of these fields (trunk merge dots, fork/merge lanes).
    merges: list[MergeEvent]
    branches: dict[str, BranchInfo]
    ontology: dict[str, list[OntologyNode]] = {}

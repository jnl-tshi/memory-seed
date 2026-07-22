"""Renderer-neutral B0a graph-fixture contract.

This module deliberately sits beside, rather than inside, the public Trace API.
It gives renderer prototypes one bounded semantic input without making layout,
colour, viewport, or library-specific state part of Memory Seed's graph truth.
"""
from __future__ import annotations

import copy
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence


FIXTURE_SCHEMA_VERSION = "memory-trace-graph-fixture/v1"
NODE_TYPES = frozenset(
    {
        "memory_entry",
        "decision_anchor",
        "commit",
        "pull_request",
        "annotation",
        "file",
        "symbol",
        "external_observation",
    }
)
PROVENANCE_CLASSES = frozenset(
    {
        "authored_memory",
        "source_control",
        "pr_review",
        "automation_ci",
        "annotation",
        "release",
        "generated_artefact",
    }
)
# The authority axis gets the same enum enforcement provenance already had.
# It previously shipped as a free-form string validated only as "non-empty",
# which is how it came to emit `canonical_memory` - a value from no declared
# vocabulary at all. A closed set is what stops that recurring.
AUTHORITY_CLASSES = frozenset(
    {
        "authored",
        "computed_canonical",
        "git_derived",
        "provider_extracted",
        "provider_resolved",
        "provider_inferred",
        "generated",
    }
)
EDGE_TYPES = frozenset({"related", "supersedes", "evolves", "branch", "topic", "agent", "day"})
TEMPORAL_SOURCES = {
    "memory_entry": "authored_timestamp",
    "decision_anchor": "anchor_entry_timestamp",
    "commit": "commit_timestamp",
    "pull_request": "event_timestamp",
    "annotation": "annotation_timestamp",
    "file": "revision_change_timestamp",
    "symbol": "revision_change_timestamp",
    "external_observation": "indexed_revision_and_observed_at",
}
RENDERER_OWNED_FIELDS = frozenset(
    {
        "colour",
        "color",
        "community_colour_slot",
        "node_positions",
        "position",
        "style",
        "viewport",
        "x",
        "y",
    }
)
REQUIRED_SELECTION_TRANSITIONS = frozenset({"layout_change", "pane_visibility", "workspace_view"})


class GraphProjectionContractError(ValueError):
    """The bounded benchmark fixture is not a renderer-neutral projection."""


# A topic must be this common across the WHOLE corpus before it can name a
# community. Measured rather than picked: 10 and 12 produce an identical
# partition on this corpus (15 communities, 351 of 561 rendered nodes), so the
# rule is not balanced on a knife edge. Below ~8 a long tail of one-off topics
# fragments the graph into dust.
MINIMUM_COMMUNITY_TOPIC_FREQUENCY = 10

UNASSIGNED_COMMUNITY = {
    "id": "community:unassigned",
    "label": "Unassigned",
    "fingerprint": "derived:unassigned",
}


# str.title() lowercases everything after the first letter, so an acronym slug
# renders as "Mcp Tools" / "Ui Design" in the graph legend. These are the ones
# the controlled vocabulary actually contains.
_TOPIC_ACRONYMS = frozenset({"adr", "api", "cli", "esr", "mcp", "pr", "ui", "yaml"})


def _humanise_topic(slug: str) -> str:
    """`mcp-tools` -> `MCP Tools`, `ui-design` -> `UI Design`."""
    words = slug.replace("_", "-").split("-")
    return " ".join(word.upper() if word in _TOPIC_ACRONYMS else word.title() for word in words)


def community_for_topics(
    topics: Sequence[str],
    frequencies: Mapping[str, int],
    minimum: int = MINIMUM_COMMUNITY_TOPIC_FREQUENCY,
) -> dict[str, str]:
    """Name a node's community after its most DISTINCTIVE authored topic.

    Communities come from authored topics rather than from structural detection
    (Louvain/Leiden), and that choice is what removes the whole of proposal
    §4.3. Its fingerprint/member-overlap/``community_previous_id`` retention
    machinery exists only because detected community ids are unstable across
    rebuilds; a topic slug IS a stable identity, so colour retention is
    automatic and there is nothing to persist.

    "Most distinctive" means lowest corpus-wide frequency, not highest. Choosing
    the most COMMON topic was measured and rejected: it puts 46% of the graph in
    one community, reproducing the giant-component hairball that made connected
    components useless here. Picking the first-listed topic was rejected too -
    topic lists are stored alphabetically sorted (measured: 304 of 304
    multi-topic nodes), so "first" carries no authored meaning at all.

    Frequencies MUST be corpus-wide, never counted over the nodes in one
    response: a node's community would otherwise change as more of the graph
    loaded, which is the exact instability this scheme exists to avoid.

    Ties break alphabetically so the result is deterministic. A node whose most
    distinctive topic is too rare falls back to its next most distinctive
    qualifying topic rather than going grey; a node with no qualifying topic is
    genuinely unassigned, and says so.
    """
    qualifying = [topic for topic in topics if frequencies.get(topic, 0) >= minimum]
    if not qualifying:
        return dict(UNASSIGNED_COMMUNITY)
    slug = min(qualifying, key=lambda topic: (frequencies.get(topic, 0), topic))
    return {
        "id": f"community:topic:{slug}",
        "label": _humanise_topic(slug),
        # The fingerprint IS the topic slug. Stability across rebuilds is a
        # property of the identity, not of a retention algorithm layered on top.
        "fingerprint": f"topic:{slug}",
    }


def load_graph_fixture(path: str | Path) -> dict[str, Any]:
    """Load and validate a JSON fixture before a renderer prototype consumes it."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_graph_fixture(payload)
    return payload


def renderer_input(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Return a detached, validated semantic payload for any renderer adapter.

    The copy prevents a prototype from accidentally mutating the fixture object
    held by its benchmark harness. Renderer state belongs in that adapter's
    rebuildable cache, never in the fixture or canonical Markdown graph.
    """
    validate_graph_fixture(payload)
    return copy.deepcopy(dict(payload))


def project_trace_graph(
    graph: Mapping[str, Any],
    *,
    topic_frequencies: Mapping[str, int] | None = None,
) -> dict[str, Any]:
    """Adapt the current Trace graph response into renderer-facing semantics.

    Communities are named after authored topics when ``topic_frequencies`` is
    supplied - see :func:`community_for_topics`. The argument is corpus-wide
    counts, NOT counts over ``graph``: deriving them from the response would
    make a node's community depend on how much of the graph happened to be
    loaded.

    Omitting it keeps every node in the single derived ``unassigned`` community,
    which is the original B0a behaviour and what the bounded benchmark fixtures
    still expect. Structural detection is still deliberately absent, so a
    renderer cannot promote its own visual clustering to canonical graph data.
    """
    _mapping(graph, "trace graph")
    entry_total = graph.get("entry_total")
    raw_nodes = graph.get("nodes")
    raw_edges = graph.get("edges")
    if not isinstance(raw_nodes, list) or not isinstance(raw_edges, list):
        raise GraphProjectionContractError("trace graph must contain node and edge lists")

    nodes: list[dict[str, Any]] = []
    entry_id_by_node: dict[str, str] = {}
    for index, raw in enumerate(raw_nodes):
        _mapping(raw, f"trace graph nodes[{index}]")
        node_id = raw.get("id")
        if not isinstance(node_id, str) or not node_id:
            raise GraphProjectionContractError(f"trace graph nodes[{index}].id must be a non-empty string")
        entry_id = raw.get("entry_id")
        if isinstance(entry_id, str) and entry_id:
            entry_id_by_node[node_id] = entry_id
        temporal_value, temporal_precision = _trace_temporal_value(raw, index)
        nodes.append(
            {
                "id": node_id,
                "node_type": "memory_entry",
                "label": raw.get("title") or node_id,
                "provenance_class": raw.get("provenance_class", "authored_memory"),
                "authority_class": "authored",
                "community": (
                    community_for_topics(raw.get("topics") or [], topic_frequencies)
                    if topic_frequencies is not None
                    else dict(UNASSIGNED_COMMUNITY)
                ),
                "temporal": {
                    "value": temporal_value,
                    "source": "authored_timestamp",
                    "precision": temporal_precision,
                },
                "connectivity": raw.get("connectivity", 0),
                "importance_score": raw.get("importance_score", 0.0),
                "revision": None,
                "provider": None,
                "stale": False,
                # Selection needs a way back to the canonical read API, but
                # this immutable source context is not renderer state.
                "source": {
                    "chunk_id": raw.get("chunk_id"),
                    "entry_id": raw.get("entry_id"),
                    "agent": raw.get("agent", "unknown"),
                    "topics": raw.get("topics", []),
                },
            }
        )

    edges: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_edges):
        _mapping(raw, f"trace graph edges[{index}]")
        source = raw.get("source")
        target = raw.get("target")
        edge_type = raw.get("type")
        if not isinstance(source, str) or not isinstance(target, str) or edge_type not in EDGE_TYPES:
            raise GraphProjectionContractError(f"trace graph edges[{index}] are not canonical graph edges")
        evidence_refs = [entry_id_by_node[item] for item in (source, target) if item in entry_id_by_node]
        edges.append(
            {
                "id": f"trace:{index}:{source}:{edge_type}:{target}",
                "source": source,
                "target": target,
                "edge_type": edge_type,
                "directed": True,
                "evidence_refs": evidence_refs or [source, target],
            }
        )
    projected: dict[str, Any] = {"nodes": nodes, "edges": edges}
    # Passed through only when the caller supplies it (the live service does;
    # the bounded benchmark fixtures do not), so fixture-shaped payloads keep
    # their exact two-key shape.
    if isinstance(entry_total, int):
        projected["entry_total"] = entry_total
    return projected


def validate_graph_fixture(payload: Mapping[str, Any]) -> None:
    """Validate the B0a bounded fixture without introducing a new public API."""
    _mapping(payload, "fixture")
    _required(payload, {"schema_version", "fixture_id", "scope", "nodes", "edges", "selection", "benchmark_cases", "requirements"}, "fixture")
    if payload["schema_version"] != FIXTURE_SCHEMA_VERSION:
        raise GraphProjectionContractError(
            f"fixture.schema_version must be {FIXTURE_SCHEMA_VERSION!r}"
        )
    if not isinstance(payload["fixture_id"], str) or not payload["fixture_id"]:
        raise GraphProjectionContractError("fixture.fixture_id must be a non-empty string")
    if not isinstance(payload["scope"], str) or not payload["scope"]:
        raise GraphProjectionContractError("fixture.scope must be a non-empty string")

    nodes = payload["nodes"]
    if not isinstance(nodes, list) or not nodes:
        raise GraphProjectionContractError("fixture.nodes must be a non-empty list")
    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        _mapping(node, f"nodes[{index}]")
        _reject_renderer_fields(node, f"nodes[{index}]")
        _required(
            node,
            {
                "id",
                "node_type",
                "label",
                "provenance_class",
                "authority_class",
                "community",
                "temporal",
                "connectivity",
                "importance_score",
                "revision",
                "provider",
                "stale",
            },
            f"nodes[{index}]",
        )
        node_id = node["id"]
        if not isinstance(node_id, str) or not node_id:
            raise GraphProjectionContractError(f"nodes[{index}].id must be a non-empty string")
        if node_id in node_ids:
            raise GraphProjectionContractError(f"duplicate node id {node_id!r}")
        node_ids.add(node_id)
        node_type = node["node_type"]
        if node_type not in NODE_TYPES:
            raise GraphProjectionContractError(f"nodes[{index}].node_type is not recognised: {node_type!r}")
        if node["provenance_class"] not in PROVENANCE_CLASSES:
            raise GraphProjectionContractError(f"nodes[{index}].provenance_class is not recognised")
        if node["authority_class"] not in AUTHORITY_CLASSES:
            raise GraphProjectionContractError(f"nodes[{index}].authority_class is not recognised")
        _validate_community(node["community"], f"nodes[{index}].community")
        _validate_temporal(node["temporal"], node_type, f"nodes[{index}].temporal")
        if not _non_negative_number(node["connectivity"]):
            raise GraphProjectionContractError(f"nodes[{index}].connectivity must be non-negative")
        if not _non_negative_number(node["importance_score"]):
            raise GraphProjectionContractError(f"nodes[{index}].importance_score must be non-negative")
        if node["revision"] is not None and not isinstance(node["revision"], str):
            raise GraphProjectionContractError(f"nodes[{index}].revision must be a string or null")
        if node["provider"] is not None and not isinstance(node["provider"], str):
            raise GraphProjectionContractError(f"nodes[{index}].provider must be a string or null")
        if not isinstance(node["stale"], bool):
            raise GraphProjectionContractError(f"nodes[{index}].stale must be boolean")

    edges = payload["edges"]
    if not isinstance(edges, list) or not edges:
        raise GraphProjectionContractError("fixture.edges must be a non-empty list")
    edge_ids: set[str] = set()
    for index, edge in enumerate(edges):
        _mapping(edge, f"edges[{index}]")
        _reject_renderer_fields(edge, f"edges[{index}]")
        _required(edge, {"id", "source", "target", "edge_type", "directed", "evidence_refs"}, f"edges[{index}]")
        edge_id = edge["id"]
        if not isinstance(edge_id, str) or not edge_id or edge_id in edge_ids:
            raise GraphProjectionContractError(f"edges[{index}].id must be unique and non-empty")
        edge_ids.add(edge_id)
        if edge["source"] not in node_ids or edge["target"] not in node_ids:
            raise GraphProjectionContractError(f"edges[{index}] references a node outside the fixture")
        if edge["source"] == edge["target"]:
            raise GraphProjectionContractError(f"edges[{index}] must not self-reference")
        if edge["edge_type"] not in EDGE_TYPES:
            raise GraphProjectionContractError(f"edges[{index}].edge_type is not a canonical graph edge")
        if not isinstance(edge["directed"], bool):
            raise GraphProjectionContractError(f"edges[{index}].directed must be boolean")
        if not isinstance(edge["evidence_refs"], list) or not all(isinstance(ref, str) and ref for ref in edge["evidence_refs"]):
            raise GraphProjectionContractError(f"edges[{index}].evidence_refs must be non-empty string ids")

    _validate_selection(payload["selection"], node_ids)
    _validate_benchmark_cases(payload["benchmark_cases"])
    _validate_requirements(payload["requirements"])


def _mapping(value: Any, label: str) -> None:
    if not isinstance(value, Mapping):
        raise GraphProjectionContractError(f"{label} must be an object")


def _required(value: Mapping[str, Any], keys: set[str], label: str) -> None:
    missing = sorted(keys - set(value))
    if missing:
        raise GraphProjectionContractError(f"{label} is missing required fields: {', '.join(missing)}")


def _reject_renderer_fields(value: Mapping[str, Any], label: str) -> None:
    leaked = sorted(RENDERER_OWNED_FIELDS & set(value))
    if leaked:
        raise GraphProjectionContractError(
            f"{label} contains renderer-owned field(s): {', '.join(leaked)}"
        )


def _validate_community(value: Any, label: str) -> None:
    _mapping(value, label)
    _required(value, {"id", "label", "fingerprint"}, label)
    for key in ("id", "label", "fingerprint"):
        if not isinstance(value[key], str) or not value[key]:
            raise GraphProjectionContractError(f"{label}.{key} must be a non-empty string")
    _reject_renderer_fields(value, label)


def _validate_temporal(value: Any, node_type: str, label: str) -> None:
    _mapping(value, label)
    _required(value, {"value", "source", "precision"}, label)
    if value["source"] != TEMPORAL_SOURCES[node_type]:
        raise GraphProjectionContractError(
            f"{label}.source must be {TEMPORAL_SOURCES[node_type]!r} for {node_type!r}"
        )
    if not isinstance(value["value"], str):
        raise GraphProjectionContractError(f"{label}.value must be an ISO-8601 timestamp")
    precision = value["precision"]
    try:
        if precision == "timestamp":
            datetime.fromisoformat(value["value"].replace("Z", "+00:00"))
        elif precision == "date":
            date.fromisoformat(value["value"])
        else:
            raise ValueError
    except ValueError as exc:
        raise GraphProjectionContractError(
            f"{label} must use an ISO-8601 {precision!r} temporal value"
        ) from exc


def _validate_selection(value: Any, node_ids: set[str]) -> None:
    _mapping(value, "selection")
    _required(value, {"selected_node_id", "preserves_across"}, "selection")
    if value["selected_node_id"] not in node_ids:
        raise GraphProjectionContractError("selection.selected_node_id must reference a fixture node")
    transitions = value["preserves_across"]
    if not isinstance(transitions, list) or not all(isinstance(item, str) for item in transitions):
        raise GraphProjectionContractError("selection.preserves_across must be a list of strings")
    if not REQUIRED_SELECTION_TRANSITIONS.issubset(transitions):
        raise GraphProjectionContractError("selection.preserves_across omits a B0a shared-selection transition")


def _validate_benchmark_cases(value: Any) -> None:
    if not isinstance(value, list) or not value:
        raise GraphProjectionContractError("benchmark_cases must be a non-empty list")
    case_ids: set[str] = set()
    for index, case in enumerate(value):
        _mapping(case, f"benchmark_cases[{index}]")
        _required(case, {"id", "layout", "temporal_strength"}, f"benchmark_cases[{index}]")
        if case["id"] in case_ids or not isinstance(case["id"], str) or not case["id"]:
            raise GraphProjectionContractError(f"benchmark_cases[{index}].id must be unique and non-empty")
        case_ids.add(case["id"])
        if case["layout"] not in {"topology", "temporal_topology", "evolution_hierarchy"}:
            raise GraphProjectionContractError(f"benchmark_cases[{index}].layout is not a B0a layout")
        if case["temporal_strength"] not in {"off", "mild", "strong"}:
            raise GraphProjectionContractError(f"benchmark_cases[{index}].temporal_strength is invalid")


def _validate_requirements(value: Any) -> None:
    _mapping(value, "requirements")
    _required(value, {"offline", "list_equivalent", "selection_preserved"}, "requirements")
    for key in ("offline", "list_equivalent", "selection_preserved"):
        if value[key] is not True:
            raise GraphProjectionContractError(f"requirements.{key} must be true for the B0a benchmark")


def _trace_temporal_value(raw: Mapping[str, Any], index: int) -> tuple[str, str]:
    timestamp = raw.get("datetime")
    if isinstance(timestamp, str) and timestamp:
        try:
            datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        except ValueError as exc:
            raise GraphProjectionContractError(
                f"trace graph nodes[{index}].datetime must be an ISO-8601 timestamp"
            ) from exc
        return timestamp, "timestamp"
    value = raw.get("date")
    if not isinstance(value, str):
        raise GraphProjectionContractError(f"trace graph nodes[{index}].date must be an ISO date")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise GraphProjectionContractError(f"trace graph nodes[{index}].date must be an ISO date") from exc
    return value, "date"


def _non_negative_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0

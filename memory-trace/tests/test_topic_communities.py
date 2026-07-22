"""Communities named after authored topics.

These pin the RULE and the two alternatives measured and rejected with it, so a
later change that reaches for "most common topic" or "first listed" trips a test
rather than silently reintroducing a partition that was already shown not to
work on this corpus.
"""

from __future__ import annotations

from memory_trace.graph_projection import (
    MINIMUM_COMMUNITY_TOPIC_FREQUENCY,
    community_for_topics,
    project_trace_graph,
)

# Shaped like the real corpus: a few head topics well above the floor, and a
# long tail of one-off topics below it.
FREQUENCIES = {
    "memory-trace": 165,
    "ui-design": 80,
    "graph": 62,
    "documentation": 55,
    "retrieval": 14,
    "release": 12,
    "mermaid": 8,
    "licensing": 1,
}


def test_the_most_distinctive_topic_names_the_community() -> None:
    # Rarest wins, NOT most common. Choosing the most common topic was measured
    # on the live graph and put 46% of nodes in one community - the same giant
    # component that made connected-component detection useless here.
    community = community_for_topics(["memory-trace", "retrieval"], FREQUENCIES)
    assert community["id"] == "community:topic:retrieval"
    assert community["label"] == "Retrieval"


def test_the_fingerprint_is_the_topic_slug_itself() -> None:
    # This is the whole reason proposal §4.3's retention apparatus is not built:
    # the identity is stable by construction, so there is no unstable detected
    # id to fingerprint, overlap-compare, or carry in community_previous_id.
    assert community_for_topics(["graph"], FREQUENCIES)["fingerprint"] == "topic:graph"


def test_a_topic_below_the_floor_cannot_name_a_community() -> None:
    # Otherwise the 40-odd one-off topics each become their own community and
    # the graph fragments into dust rather than clustering.
    assert community_for_topics(["licensing"], FREQUENCIES) == {
        "id": "community:unassigned",
        "label": "Unassigned",
        "fingerprint": "derived:unassigned",
    }


def test_a_rare_topic_falls_back_to_the_next_distinctive_qualifying_one() -> None:
    # Measured: without this fallback, coverage of rendered nodes is 50%; with
    # it, 63% - every node that carries any qualifying topic at all.
    community = community_for_topics(["licensing", "graph"], FREQUENCIES)
    assert community["id"] == "community:topic:graph"


def test_no_qualifying_topic_is_unassigned_rather_than_guessed() -> None:
    assert community_for_topics([], FREQUENCIES)["id"] == "community:unassigned"
    assert community_for_topics(["licensing"], FREQUENCIES)["id"] == "community:unassigned"


def test_ties_break_alphabetically_so_assignment_is_deterministic() -> None:
    frequencies = {"alpha": 20, "omega": 20}
    first = community_for_topics(["omega", "alpha"], frequencies)
    second = community_for_topics(["alpha", "omega"], frequencies)
    assert first == second
    assert first["id"] == "community:topic:alpha"


def test_input_order_never_changes_the_result() -> None:
    # Topic lists are stored alphabetically sorted (measured: 304 of 304
    # multi-topic nodes), so "first listed" carries no authored meaning. The
    # rule must not depend on order in any way.
    forward = community_for_topics(["documentation", "release", "ui-design"], FREQUENCIES)
    backward = community_for_topics(["ui-design", "release", "documentation"], FREQUENCIES)
    assert forward == backward == community_for_topics(["release"], FREQUENCIES)


def test_the_floor_is_not_balanced_on_a_knife_edge() -> None:
    # 10 and 12 were measured to produce an identical partition on the real
    # corpus. A rule that flipped between them would be tuned, not derived.
    for minimum in (MINIMUM_COMMUNITY_TOPIC_FREQUENCY, 12):
        assert community_for_topics(["memory-trace", "release"], FREQUENCIES, minimum)["id"] == (
            "community:topic:release"
        )


def _trace_graph() -> dict:
    return {
        "nodes": [
            {"id": "a", "entry_id": "a", "title": "A", "datetime": "2026-07-01T09:00:00", "topics": ["graph"]},
            {"id": "b", "entry_id": "b", "title": "B", "datetime": "2026-07-02T09:00:00", "topics": []},
        ],
        "edges": [{"id": "a-b", "source": "a", "target": "b", "type": "related"}],
    }


def test_omitting_frequencies_keeps_the_original_unassigned_behaviour() -> None:
    # The bounded benchmark fixtures still expect one derived community, so the
    # argument must be additive rather than a change of default.
    projected = project_trace_graph(_trace_graph())
    assert {node["community"]["id"] for node in projected["nodes"]} == {"community:unassigned"}


def test_supplying_frequencies_assigns_topic_communities() -> None:
    projected = project_trace_graph(_trace_graph(), topic_frequencies=FREQUENCIES)
    communities = {node["id"]: node["community"]["id"] for node in projected["nodes"]}
    assert communities["a"] == "community:topic:graph"
    # A node with no topics is unassigned, not forced into a neighbour's colour.
    assert communities["b"] == "community:unassigned"


def test_community_never_carries_a_renderer_owned_field() -> None:
    # community_colour_slot stays the renderer's to choose: the backend supplies
    # identity only. This is the split the blocked entry asked to have ratified.
    projected = project_trace_graph(_trace_graph(), topic_frequencies=FREQUENCIES)
    for node in projected["nodes"]:
        assert set(node["community"]) == {"id", "label", "fingerprint"}

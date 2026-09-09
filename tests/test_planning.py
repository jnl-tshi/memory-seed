"""Planning selects evidence; it never grants authority or changes lifecycle."""

from dataclasses import replace
from pathlib import Path

import pytest

from memory_seed.planning import (
    AUTHORITY_PRECEDENCE,
    PlanningCandidate,
    PlanningValidationError,
    assess_candidate,
    assess_conflict,
    parse_delivery_quality,
    resolve_delivery_quality,
)
from memory_seed.topics import TopicIndex, TopicRecord


@pytest.fixture
def topics():
    return TopicIndex("topics.yaml", True, "3", (
        TopicRecord("platform", axis="area"),
        TopicRecord("retrieval", aliases=("search",), parent="platform"),
        TopicRecord("ranking", parent="retrieval"),
        TopicRecord("debugging", axis="activity"),
    ))


@pytest.fixture
def candidate():
    return PlanningCandidate("mse_prior:d1", "Preserve lexical fallback.",
                             "session_evidence", topics=("retrieval",))


def test_defaults_and_project_ownership():
    root = Path(__file__).resolve().parents[1]
    text = (root / ".memory-seed/project.yaml").read_text(encoding="utf-8")
    assert parse_delivery_quality(text) == resolve_delivery_quality()
    assert "reflection_board: dormant" in text
    assert "merge_trigger: automatic" in text
    # Bootstrap owns these project-specific files, not the reusable seed.
    assert not (root / "memory_seed/seed/.memory-seed/policy.md").exists()
    assert not (root / "memory_seed/seed/.memory-seed/project.yaml").exists()
    assert resolve_delivery_quality() == {
        "schema_version": 1, "constitutional_conflict": "stop",
        "adr_conflict": "stop", "individual_decision_conflict": "warn",
        "failed_hypothesis_threshold": 3,
    }


@pytest.mark.parametrize("value", ["warn", "proceed", None, True, 1, [], {}])
def test_constitution_cannot_be_weakened(value):
    with pytest.raises(PlanningValidationError):
        resolve_delivery_quality({"delivery_quality": {
            "schema_version": 1, "constitutional_conflict": value}})


@pytest.mark.parametrize("override", [
    {"adr_conflict": "warn"}, {"adr_conflict": "proceed"},
    {"individual_decision_conflict": "proceed"}, {"failed_hypothesis_threshold": 4},
])
def test_local_override_cannot_weaken(override):
    with pytest.raises(PlanningValidationError, match="weaken"):
        resolve_delivery_quality(local_override=override)


def test_local_override_can_tighten_and_does_not_mutate():
    override = {"individual_decision_conflict": "stop", "failed_hypothesis_threshold": 2}
    result = resolve_delivery_quality(local_override=override)
    assert result["individual_decision_conflict"] == "stop"
    assert result["failed_hypothesis_threshold"] == 2
    assert "schema_version" not in override
    assert resolve_delivery_quality()["individual_decision_conflict"] == "warn"


@pytest.mark.parametrize("block", [None, [], "stop", {}, {"schema_version": True},
    {"schema_version": "1"}, {"schema_version": 2},
    {"schema_version": 1, "adr_conflict": "sometimes"},
    {"schema_version": 1, "failed_hypothesis_threshold": True},
    {"schema_version": 1, "failed_hypothesis_threshold": 0},
    {"schema_version": 1, "failed_hypothesis_threshold": 3.0},
    {"schema_version": 1, "failed_hypothesis_threshold": "3"},
    {"schema_version": 1, "adr_conflcit": "proceed"},
])
def test_malformed_recognized_mapping_fails(block):
    with pytest.raises(PlanningValidationError):
        resolve_delivery_quality({"delivery_quality": block})


@pytest.mark.parametrize("text", [
    "delivery_quality: null\n", "delivery_quality:\n", "delivery_quality: []\n",
    "delivery_quality:\n  schema_version: 1\n  adr_conflict: stop\n  adr_conflict: proceed\n",
    "delivery_quality:\n  schema_version: 1\ndelivery_quality:\n  schema_version: 1\n",
    "delivery_quality:\n schema_version: 1\n",
    "delivery_quality:\n  schema_version: 1\n  adr_conflict:\n    nested: stop\n",
])
def test_malformed_recognized_yaml_fails(text):
    with pytest.raises(PlanningValidationError):
        parse_delivery_quality(text)


def test_unrelated_project_settings_are_not_reinterpreted():
    assert parse_delivery_quality("other: &anchor !custom value\n") == resolve_delivery_quality()


@pytest.mark.parametrize("text", [
    "  delivery_quality:\n    schema_version: 2\n",
    "  delivery_quality:\n    schema_version: 1\n    individual_decision_conflict: stop\n",
    "{delivery_quality: {schema_version: 2}}\n",
    '{"delivery_quality": {schema_version: 1, individual_decision_conflict: stop}}\n',
    "{other: value, delivery_quality: {schema_version: 1, failed_hypothesis_threshold: 1}}\n",
    "delivery_quality:\n  schema_version: 1\n  individual_decision_conflict: stop\n"
    "{delivery_quality: {schema_version: 1}}\n",
])
def test_unsupported_recognized_policy_syntax_cannot_fall_back_to_defaults(text):
    with pytest.raises(PlanningValidationError, match="delivery_quality"):
        parse_delivery_quality(text)


def test_supported_inline_policy_preserves_tighter_settings():
    policy = parse_delivery_quality(
        "delivery_quality: {schema_version: 1, individual_decision_conflict: stop}\n")
    assert policy["individual_decision_conflict"] == "stop"


def test_policy_mentions_inside_comments_or_values_are_not_settings():
    text = '# {delivery_quality: {schema_version: 2}}\nother: "{delivery_quality: ignored}"\n'
    assert parse_delivery_quality(text) == resolve_delivery_quality()


def test_applicability_uses_task_ancestors_and_canonical_aliases(topics, candidate):
    match = assess_candidate(candidate, ("ranking",), topics)
    assert match.binding and match.matched_topics == ("retrieval",)
    assert assess_candidate(replace(candidate, topics=("search",)), ("search",), topics).binding
    assert not assess_candidate(candidate, ("platform",), topics).binding
    assert assess_candidate(candidate, ("platform",), topics).applicability == "out-of-scope"
    assert assess_candidate(replace(candidate, discovery="semantic"),
                            ("platform",), topics).applicability == "out-of-scope"


def test_types_are_not_independent_axes(topics, candidate):
    # No area/activity cross-product: a match on either actual topic is sufficient.
    assert assess_candidate(replace(candidate, topics=("debugging",)),
                            ("ranking", "debugging"), topics).binding


@pytest.mark.parametrize("changes, expected", [
    ({"topics": ()}, "unclassified"),
    ({"discovery": "semantic"}, "review-required"),
    ({"topic_source": "derived"}, "review-required"),
    ({"status": "superseded"}, "historical"),
    ({"status": "proposed"}, "review-required"),
    ({"authority": "derived_projection"}, "review-required"),
])
def test_candidates_never_silently_acquire_authority(topics, candidate, changes, expected):
    result = assess_candidate(replace(candidate, **changes), ("ranking",), topics)
    assert result.applicability == expected
    assert not result.binding


def test_untagged_semantic_nominee_stays_unclassified(topics, candidate):
    result = assess_candidate(replace(candidate, topics=(), discovery="semantic"), ("ranking",), topics)
    assert result.applicability == "unclassified" and not result.binding


def test_unknown_controlled_topics_fail(topics, candidate):
    with pytest.raises(PlanningValidationError, match="topic"):
        assess_candidate(candidate, ("invented",), topics)


def test_invalid_vocabulary_cannot_create_applicability(topics, candidate):
    cyclic = replace(topics, topics=(TopicRecord("retrieval", parent="ranking"),
                                    TopicRecord("ranking", parent="retrieval")))
    with pytest.raises(PlanningValidationError, match="topic vocabulary"):
        assess_candidate(candidate, ("ranking",), cyclic)


def test_precedence_is_explicit_not_discovery_order():
    assert AUTHORITY_PRECEDENCE == (
        "constitution", "control_file", "accepted_adr", "session_evidence", "derived_projection")


def test_global_authority_requires_explicit_scope_reason(topics):
    global_rule = PlanningCandidate("constitution:v1#append-only", "History is append-only.",
                                   "constitution", scope="global", scope_reason="Declared ratified ceiling.")
    assert assess_candidate(global_rule, (), topics).binding
    with pytest.raises(PlanningValidationError):
        assess_candidate(replace(global_rule, scope_reason=""), (), topics)


def test_conflict_requires_concrete_action_and_applicable_decision(topics, candidate):
    assessment = assess_candidate(candidate, ("ranking",), topics)
    for action in ("", " ", None):
        with pytest.raises(PlanningValidationError, match="proposed_action"):
            assess_conflict(assessment, proposed_action=action, conflict_reason="Removes fallback.")
    with pytest.raises(PlanningValidationError, match="applicable"):
        assess_conflict(assess_candidate(candidate, ("platform",), topics),
                        proposed_action="Remove fallback.", conflict_reason="Removes fallback.")


def test_default_individual_warning_requires_explicit_departure(topics, candidate):
    assessment = assess_candidate(candidate, ("ranking",), topics)
    result = assess_conflict(assessment, proposed_action="Remove lexical fallback from search_memory.",
                            conflict_reason="The earlier decision requires fallback.")
    assert result["disposition"] == "warn"
    assert "record_departure_and_lifecycle_review" in result["required_follow_up"]
    assert result["prior_decision"] == candidate.decision
    assert result["lifecycle_changed"] is False


def test_acceptance_does_not_turn_recommendation_into_authority(topics, candidate):
    assessment = assess_candidate(replace(candidate, authority="constitution"), ("ranking",), topics)
    acceptance = {"reference": "user-message:42", "scope": "this proposed action",
                  "reason": "User asked to explore an amendment."}
    result = assess_conflict(assessment, proposed_action="Delete recorded history.",
                            conflict_reason="Violates append-only.", agent_recommendation="proceed",
                            user_acceptance=acceptance)
    assert result["disposition"] == "stop"
    assert result["agent_recommendation"] == "proceed"
    assert result["user_acceptance"] == acceptance
    assert result["authority_granted"] is False
    assert "formal_constitutional_amendment" in result["required_follow_up"]


def test_recommendation_cannot_weaken_shared_adr_stop(topics, candidate):
    result = assess_conflict(assess_candidate(replace(candidate, authority="accepted_adr"),
                            ("ranking",), topics), proposed_action="Remove fallback.",
                            conflict_reason="ADR requires fallback.", agent_recommendation="proceed")
    assert result["disposition"] == "stop"
    assert result["user_acceptance"] is None


@pytest.mark.parametrize("acceptance", ["approved", {}, {"reference": "yes"},
    {"reference": "user:1", "scope": "", "reason": "okay"}])
def test_acceptance_requires_supplied_reference_scope_and_reason(topics, candidate, acceptance):
    with pytest.raises(PlanningValidationError, match="user_acceptance"):
        assess_conflict(assess_candidate(candidate, ("ranking",), topics),
                        proposed_action="Remove fallback.", conflict_reason="Removes fallback.",
                        user_acceptance=acceptance)


@pytest.mark.parametrize("setting", ["stop", "warn", "proceed"])
def test_shared_adr_disposition_preserves_governing_authority_review(topics, candidate, setting):
    policy = resolve_delivery_quality({"delivery_quality": {"schema_version": 1, "adr_conflict": setting}})
    result = assess_conflict(assess_candidate(replace(candidate, authority="accepted_adr"),
                            ("ranking",), topics), proposed_action="Remove fallback.",
                            conflict_reason="ADR requires fallback.", policy=policy)
    assert result["disposition"] == setting
    assert result["authority_granted"] is False
    assert "verify_governing_authority_allows_departure" in result["required_follow_up"]

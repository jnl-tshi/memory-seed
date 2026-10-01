from copy import deepcopy

import pytest

from hosted.capture.semantic import EXTRACTION_INSTRUCTIONS, PROMPT_VERSION, SemanticState


def msg(turn, actor, text, *, rollout="r", ordinal=None, **extra):
    return {
        "rollout_id": rollout,
        "turn": turn,
        "source_ordinal": ordinal if ordinal is not None else turn * 10,
        "actor": actor,
        "text": text,
        **extra,
    }


def accepted_candidate(proposal, agreement, *, candidate_id="model-1", **overrides):
    result = {
        "candidate_id": candidate_id,
        "issue": "durable capture",
        "selected_action": "use SQLite for the capture queue",
        "scope": "the capture queue",
        "agreement_quote": agreement["quote"],
        "reason": "it survives restart",
        "conditions": ["if restart recovery is required"],
        "state": "accepted",
        "deciding_actor": "user",
        "unresolved_references": [],
        "field_evidence": {
            "issue": [proposal],
            "selected_action": [proposal],
            "scope": [proposal],
            "agreement_quote": [agreement],
            "reason": [proposal],
            "conditions": [proposal],
        },
    }
    result.update(overrides)
    return result


def citation(message, start=0, end=None):
    text = message["text"]
    return {
        "rollout_id": message["rollout_id"],
        "turn": message["turn"],
        "source_ordinal": message["source_ordinal"],
        "start": start,
        "end": len(text) if end is None else end,
        "quote": text[start:len(text) if end is None else end],
    }


def setup_request(messages, marker=None):
    state = SemanticState("cfg")
    request = state.make_request(messages, marker)
    return state, request


def test_request_retry_is_identical_and_sources_are_defensively_copied():
    source = msg(1, "agent", "Issue: durable capture. Use SQLite for the queue.")
    state = SemanticState("cfg")
    request = state.make_request([source])
    source["text"] = "mutated after request"
    assert state.make_request([msg(1, "agent", "Issue: durable capture. Use SQLite for the queue.")]) == request
    assert request["schema_version"] == "p0.2-semantic-request-v1"
    assert request["messages"][0]["text"].startswith("Issue:")
    assert PROMPT_VERSION and EXTRACTION_INSTRUCTIONS


def test_successful_import_retains_validated_draft_and_next_request_is_delta_only():
    proposal = msg(1, "agent", "Issue: durable capture. Use SQLite for the capture queue because it survives restart.")
    agreement = msg(2, "user", "Yes, that is approved.")
    state, request = setup_request([proposal, agreement])
    draft = state.accept_response(request, {
        "request_id": request["request_id"],
        "candidates": [accepted_candidate(citation(proposal), citation(agreement))],
    })[0]
    assert draft["complete"] is True
    assert draft["authoritative"] is False
    assert draft["curator_verification_required"] is True
    assert draft["mechanically_valid"] is True
    assert draft["semantic_verified"] is False

    newer = msg(3, "agent", "Another evidence note.")
    next_request = state.make_request([proposal, agreement, newer])
    assert next_request["messages"] == [newer]
    assert next_request["retained_state"] == [draft]


def test_duplicate_coordinates_are_idempotent_but_changed_content_is_rejected():
    first = msg(1, "user", "Use SQLite for the queue.")
    state = SemanticState("cfg")
    request = state.make_request([first, deepcopy(first)])
    assert request["messages"] == [first]
    with pytest.raises(ValueError, match="changed content"):
        state.make_request([msg(1, "user", "Use PostgreSQL for the queue.")])


def test_response_must_match_pending_request_and_cannot_mutate_sources():
    proposal = msg(1, "agent", "Use SQLite for the queue.")
    agreement = msg(2, "user", "Yes, approved.")
    state, request = setup_request([proposal, agreement])
    altered = deepcopy(request)
    altered["messages"][0]["text"] = "changed source"
    with pytest.raises(ValueError):
        state.accept_response(altered, {"request_id": request["request_id"], "candidates": []})
    with pytest.raises(ValueError):
        state.accept_response(request, {"request_id": "fabricated", "candidates": []})


def test_pending_retry_rejects_changed_input_or_marker():
    first = msg(1, "agent", "Use SQLite for the queue.")
    state, request = setup_request([first], {"turn": 1})
    assert state.make_request([first], {"turn": 1}) == request
    with pytest.raises(ValueError, match="inputs changed"):
        state.make_request([msg(2, "user", "Yes.")], {"turn": 1})
    with pytest.raises(ValueError, match="marker changed"):
        state.make_request([first], {"turn": 2})


def test_citations_must_be_known_exact_and_typed():
    proposal = msg(1, "agent", "Use SQLite for the queue.")
    agreement = msg(2, "user", "Yes, approved.")
    state, request = setup_request([proposal, agreement])
    bad = accepted_candidate(citation(proposal), citation(agreement))
    bad["field_evidence"]["selected_action"][0]["quote"] = "fabricated"
    with pytest.raises(ValueError, match="quote"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [bad]})

    state, request = setup_request([proposal, agreement])
    bad = accepted_candidate(citation(proposal), citation(agreement))
    bad["field_evidence"]["issue"][0]["turn"] = True
    with pytest.raises(ValueError):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [bad]})


def test_unknown_citations_duplicates_and_model_authority_flags_are_rejected():
    proposal = msg(1, "agent", "Use SQLite for the queue.")
    agreement = msg(2, "user", "Yes, approved.")
    state, request = setup_request([proposal, agreement])
    candidate = accepted_candidate(citation(proposal), citation(agreement))
    candidate["field_evidence"]["issue"][0]["source_ordinal"] = 999
    with pytest.raises(ValueError, match="citation"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate]})

    state, request = setup_request([proposal, agreement])
    candidate = accepted_candidate(citation(proposal), citation(agreement))
    with pytest.raises(ValueError, match="duplicate"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate, deepcopy(candidate)]})

    state, request = setup_request([proposal, agreement])
    candidate = accepted_candidate(citation(proposal), citation(agreement))
    candidate["authoritative"] = True
    with pytest.raises(ValueError, match="authority"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate]})


def test_accepted_state_requires_user_actor_and_causal_acceptance():
    proposal = msg(2, "agent", "Use SQLite for the queue.")
    agreement = msg(3, "agent", "Yes, approved.")
    state, request = setup_request([proposal, agreement])
    candidate = accepted_candidate(citation(proposal), citation(agreement))
    with pytest.raises(ValueError, match="user"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate]})

    proposal = msg(3, "agent", "Use SQLite for the queue.")
    agreement = msg(2, "user", "Yes, approved.")
    state, request = setup_request([proposal, agreement])
    candidate = accepted_candidate(citation(proposal), citation(agreement))
    with pytest.raises(ValueError, match="chronolog"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate]})


def test_cross_rollout_acceptance_needs_timestamps_and_respects_boundaries():
    proposal = msg(1, "agent", "Use SQLite for the queue.", rollout="parent")
    agreement = msg(2, "user", "Yes, approved.", rollout="child")
    state, request = setup_request([proposal, agreement])
    candidate = accepted_candidate(citation(proposal), citation(agreement))
    with pytest.raises(ValueError, match="timestamp"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate]})

    proposal = msg(1, "agent", "Use SQLite for the queue.", timestamp="2026-01-01T10:00:00Z")
    boundary = msg(2, "system", "Implementation started.", implementation_started=True)
    agreement = msg(3, "user", "Yes, approved.", timestamp="2026-01-01T10:02:00Z")
    state, request = setup_request([proposal, boundary, agreement])
    candidate = accepted_candidate(citation(proposal), citation(agreement))
    with pytest.raises(ValueError, match="boundary"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate]})


def test_required_fields_and_populated_conditions_need_evidence_but_null_is_incomplete():
    proposal = msg(1, "agent", "Use SQLite for the queue.")
    agreement = msg(2, "user", "Yes, approved.")
    state, request = setup_request([proposal, agreement])
    candidate = accepted_candidate(citation(proposal), citation(agreement), conditions=["only if funded"])
    candidate["field_evidence"].pop("conditions")
    with pytest.raises(ValueError, match="conditions"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate]})

    state, request = setup_request([proposal, agreement])
    candidate = accepted_candidate(citation(proposal), citation(agreement), unresolved_references=["that option"])
    with pytest.raises(ValueError, match="unresolved_references"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate]})

    state, request = setup_request([proposal, agreement])
    candidate = accepted_candidate(citation(proposal), citation(agreement), conditions=[], reason="")
    candidate["field_evidence"].pop("conditions")
    candidate["field_evidence"].pop("reason")
    candidate["issue"] = None
    candidate["selected_action"] = None
    candidate["scope"] = None
    candidate["agreement_quote"] = None
    candidate["state"] = "proposed"
    candidate["deciding_actor"] = "agent"
    result = state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate]})[0]
    assert result["complete"] is False


def test_question_and_tentative_text_are_not_mechanically_suppressed():
    question = msg(1, "agent", "Could we use SQLite for the queue?")
    state, request = setup_request([question])
    c = {
        "candidate_id": "q",
        "issue": "durable capture",
        "selected_action": "use SQLite for the queue",
        "scope": "the queue",
        "agreement_quote": None,
        "reason": None,
        "conditions": [],
        "state": "proposed",
        "deciding_actor": "agent",
        "unresolved_references": [],
        "field_evidence": {name: [citation(question)] for name in ("issue", "selected_action", "scope")},
    }
    result = state.accept_response(request, {"request_id": request["request_id"], "candidates": [c]})[0]
    assert result["complete"] is False


def test_anchor_marker_is_not_a_boundary_and_bounds_reject_without_clipping():
    text = "I tentatively suggest SQLite for this queue."
    anchor = msg(1, "agent", text, decision_marker=True)
    state = SemanticState("cfg")
    request = state.make_request([anchor], {"turn": 1, "source_ordinal": 10, "trigger_quote": text})
    assert request["messages"] == [anchor]
    with pytest.raises(ValueError, match="limit"):
        SemanticState("cfg").make_request([msg(i, "user", "x" * 300) for i in range(1, 201)])


def test_request_and_response_serialized_limits_bound_retained_state_atomically():
    proposal = msg(1, "agent", "Use SQLite for the queue.")
    agreement = msg(2, "user", "Yes, approved.")
    state = SemanticState("cfg")
    request = state.make_request([proposal, agreement])
    oversized = accepted_candidate(citation(proposal), citation(agreement), reason="r" * 130_000)
    oversized["field_evidence"]["reason"] = [citation(proposal)]
    with pytest.raises(ValueError, match="response.*limit"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [oversized]})
    # An invalid oversized response leaves the same request pending and imports no draft.
    assert state.make_request([proposal, agreement]) == request
    concise = accepted_candidate(citation(proposal), citation(agreement), reason="restart-safe")
    accepted = state.accept_response(request, {"request_id": request["request_id"], "candidates": [concise]})[0]
    assert "source_messages" not in accepted
    next_request = state.make_request([proposal, agreement, msg(3, "agent", "Next note.")])
    assert next_request["retained_state"] == [accepted]


def test_oversized_retained_import_is_atomic_retryable_and_does_not_wedge_future_delta():
    proposal = msg(1, "agent", "Use SQLite for the queue.")
    agreement = msg(2, "user", "Yes, approved.")
    state, request = setup_request([proposal, agreement])
    draft = accepted_candidate(citation(proposal), citation(agreement), reason="r" * 105_000)
    draft["field_evidence"]["reason"] = [citation(proposal)]
    oversized = {"request_id": request["request_id"], "candidates": [draft]}
    with pytest.raises(ValueError, match="request.*limit"):
        state.accept_response(request, oversized)
    assert state.make_request([proposal, agreement]) == request

    concise = accepted_candidate(citation(proposal), citation(agreement), reason="restart-safe")
    imported = state.accept_response(request, {
        "request_id": request["request_id"], "candidates": [concise],
    })
    next_request = state.make_request([proposal, agreement, msg(3, "agent", "Next note.")])
    assert next_request["messages"] == [msg(3, "agent", "Next note.")]
    assert next_request["retained_state"] == imported


def test_zero_length_whitespace_and_mismatched_agreement_citations_reject():
    proposal = msg(1, "agent", "Use SQLite for the queue.")
    agreement = msg(2, "user", "Yes, approved.")
    state, request = setup_request([proposal, agreement])
    candidate = accepted_candidate(citation(proposal), citation(agreement))
    candidate["field_evidence"]["agreement_quote"][0].update(start=0, end=0, quote="")
    with pytest.raises(ValueError, match="nonempty"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate]})

    state, request = setup_request([proposal, msg(2, "user", "   ")])
    candidate = accepted_candidate(citation(proposal), citation(request["messages"][1]))
    with pytest.raises(ValueError, match="nonempty"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate]})

    state, request = setup_request([proposal, agreement])
    candidate = accepted_candidate(citation(proposal), citation(agreement), agreement_quote="I approve.")
    with pytest.raises(ValueError, match="agreement_quote"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate]})


def test_cross_rollout_untimestamped_boundaries_and_endpoints_are_rejected():
    proposal = msg(1, "agent", "Use SQLite for the queue.", rollout="parent", timestamp="2026-01-01T10:00:00Z")
    boundary = msg(2, "system", "A task boundary.", rollout="parent", task_boundary=True)
    agreement = msg(3, "user", "Yes, approved.", rollout="child", timestamp="2026-01-01T10:02:00Z")
    state, request = setup_request([proposal, boundary, agreement])
    candidate = accepted_candidate(citation(proposal), citation(agreement))
    with pytest.raises(ValueError, match="timestamp"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate]})

    # Any supplied, unanchored boundary with unknown placement makes a
    # cross-rollout link ambiguous, even when it belongs to a third rollout.
    unrelated = msg(8, "system", "Unknown task boundary.", rollout="third", task_boundary=True)
    state, request = setup_request([proposal, agreement, unrelated])
    candidate = accepted_candidate(citation(proposal), citation(agreement))
    with pytest.raises(ValueError, match="timestamp"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate]})

    boundary = msg(3, "user", "Yes, approved.", rollout="child", timestamp="2026-01-01T10:02:00Z", decision_marker=True)
    state, request = setup_request([proposal, boundary])
    candidate = accepted_candidate(citation(proposal), citation(boundary))
    with pytest.raises(ValueError, match="boundary"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate]})

    # The same endpoint sentinel is permitted when it is the exact marker anchor.
    marker = {"turn": 3, "source_ordinal": 30, "trigger_quote": boundary["text"]}
    state, request = setup_request([proposal, boundary], marker)
    candidate = accepted_candidate(citation(proposal), citation(boundary))
    assert state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate]})[0]["complete"]


def test_proposed_cross_rollout_citation_missing_timestamp_raises_value_error():
    proposal = msg(1, "agent", "Use SQLite for the queue.", rollout="parent")
    approval = msg(2, "user", "Maybe approved.", rollout="child")
    state, request = setup_request([proposal, approval])
    candidate = accepted_candidate(citation(proposal), citation(approval), state="proposed", deciding_actor="agent")
    with pytest.raises(ValueError, match="timestamp"):
        state.accept_response(request, {"request_id": request["request_id"], "candidates": [candidate]})


def test_candidate_count_limit_is_enforced_before_import():
    state, request = setup_request([])
    with pytest.raises(ValueError, match="candidate count limit"):
        state.accept_response(request, {
            "request_id": request["request_id"],
            "candidates": [{}] * 101,
        })

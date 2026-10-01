"""Focused offline replay contract tests."""
import json

import pytest

from hosted.evaluation.adaptive_replay import AdaptiveReplay


def msg(turn, text, ordinal=0, actor="user", **extra):
    return {"rollout_id": "r", "turn": turn, "source_ordinal": ordinal,
            "actor": actor, "text": text, **extra}


def cite(source, quote):
    start = source["text"].index(quote)
    return {"rollout_id": "r", "turn": source["turn"], "source_ordinal": source["source_ordinal"],
            "start": start, "end": start + len(quote), "quote": quote}


def answers(source=None, **overrides):
    result = {slot: None for slot in ("issue", "selected_action", "deciding_actor", "acceptance",
                                      "scope", "conditions", "proposal_reference", "topic_origin", "reason")}
    if source is not None:
        c = cite(source, source["text"])
        result.update({slot: {"value": "user" if slot == "deciding_actor" else slot, "citations": [c]}
                       for slot in result})
    result.update(overrides)
    return result


def response(request, answer_set, links=None, usage=None):
    result = {"request_id": request["request_id"], "candidate_id": request["candidate_id"],
              "answers": answer_set, "reference_links": [] if links is None else links}
    if usage is not None:
        result["usage"] = usage
    return result


def replay(messages, anchor=None):
    last = messages[-1] if anchor is None else anchor
    return AdaptiveReplay(messages, ("r", last["turn"], last["source_ordinal"]), "c", "frozen-config")


def test_current_turn_completion_stops_and_preserves_non_authority():
    source = msg(2, "Use capture because it is local.")
    run = replay([source])
    request = run.request()
    result = run.import_response(response(request, answers(source), usage={"prompt_tokens": 18, "completion_tokens": 9}))
    assert result["all_questions_answered"] is True
    assert result["semantic_verified"] is False and result["authoritative"] is False
    assert run.request() is None
    assert run.summary()["stop_reason"] == "answered_all_questions"
    assert run.summary()["request_count"] == 1


def test_two_turn_expansion_missing_reason_and_incomplete_explanation():
    messages = [msg(t, f"old {t}") for t in range(4)] + [msg(4, "Use capture.")]
    run = replay(messages)
    first = run.request()
    assert [m["turn"] for m in first["messages"]] == [4]
    result = run.import_response(response(first, answers(messages[-1], reason=None)))
    assert result["decision_established"] is True
    assert result["explanation_complete"] is False
    second = run.request()
    assert second["turns"] == [2, 3]
    assert [m["turn"] for m in second["messages"]] == [2, 3]
    assert second["ledger"]["answers"]["reason"] is None
    assert run.summary()["expansion_count"] == 1


def test_twenty_turn_exhaustion_retains_gaps_and_final_batch_can_complete():
    sources = [msg(t, f"text {t}") for t in range(31)]
    run = replay(sources)
    for _ in range(10):
        request = run.request()
        run.import_response(response(request, answers()))
    final = run.request()
    assert final["turns"] == [10, 11]
    result = run.import_response(response(final, answers()))
    assert run.request() is None
    assert run.summary()["stop_reason"] == "window_exhausted"
    assert run.summary()["expansion_count"] == 10
    assert run.summary()["disclosed_source_messages"] == 21
    assert "reason" in result["missing_slots"]
    assert result["semantic_verified"] is False

    completed = replay(sources)
    for _ in range(10):
        request = completed.request()
        completed.import_response(response(request, answers()))
    final = completed.request()
    completed.import_response(response(final, answers(sources[10])))
    assert completed.summary()["stop_reason"] == "answered_all_questions"


def test_multi_message_reference_and_ambiguous_reference():
    first = msg(0, "Plan A: capture.", actor="assistant")
    second = msg(0, "Plan A: exclude private.", ordinal=1, actor="assistant")
    approval = msg(1, "Yes, that plan.")
    run = replay([first, second, approval])
    initial = run.request()
    run.import_response(response(initial, answers()))
    request = run.request()
    proposal = {"value": "that plan", "citations": [cite(approval, "that plan")]}
    action = {"value": "Plan A", "citations": [cite(first, "Plan A"), cite(second, "Plan A")]}
    base = answers(approval, selected_action=action, proposal_reference=proposal)
    link = {"mention": cite(approval, "that plan"),
            "antecedents": [cite(first, "Plan A"), cite(second, "Plan A")], "status": "ambiguous"}
    unresolved = run.import_response(response(request, base, [link]))
    assert unresolved["decision_established"] is False
    assert unresolved["unresolved_references"]

    resolved_run = replay([first, second, approval])
    resolved_run.import_response(response(resolved_run.request(), answers()))
    result = resolved_run.import_response(response(resolved_run.request(), base, [dict(link, status="resolved")]))
    assert result["decision_established"] is True
    assert result["all_questions_answered"] is True


def test_same_turn_directive_and_bad_citation_rolls_back():
    source = msg(0, "Yes, use SQLite for this project.")
    run = replay([source])
    request = run.request()
    bad = answers(source)
    bad["issue"]["citations"][0]["quote"] = "wrong"
    with pytest.raises(ValueError, match="quote"):
        run.import_response(response(request, bad))
    assert run.summary()["request_count"] == 1
    assert run.summary()["response_count"] == 0
    result = run.import_response(response(request, answers(source)))
    assert result["decision_established"] is True


def test_byte_identical_request_retry_and_conflicting_response():
    source = msg(0, "Use capture.")
    run = replay([source])
    a = run.request()
    b = run.request()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
    accepted = response(a, answers(source), usage={"prompt_tokens": 3, "completion_tokens": 2})
    run.import_response(accepted)
    run.import_response(accepted)
    assert run.summary()["response_count"] == 1
    assert run.summary()["prompt_tokens"] == 3
    with pytest.raises(ValueError, match="conflicting"):
        run.import_response(response(a, answers()))
    with pytest.raises(ValueError, match="request_id"):
        run.import_response(dict(accepted, request_id="wrong"))


def test_usage_omission_is_unavailable_not_zero():
    run = replay([msg(0, "Use capture.")])
    run.import_response(response(run.request(), answers()))
    summary = run.summary()
    assert summary["prompt_tokens"] is None and summary["completion_tokens"] is None
    assert summary["usage_unavailable_requests"] == 1
    assert "cost" not in summary


def test_request_privacy_and_size_cap_and_huge_source():
    source = msg(0, "Use capture.", root_lineage="secret", gold_label="positive",
                 semantic_verified=True, private_metadata={"key": "hidden"})
    run = replay([source])
    request = run.request()
    serialized = json.dumps(request, sort_keys=True)
    assert "secret" not in serialized and "positive" not in serialized and "hidden" not in serialized
    assert "gold_label" not in serialized
    assert "semantic_verified" not in json.dumps(request["messages"])
    assert len(serialized) <= 100_000
    huge = replay([msg(0, "x" * 50_001)])
    assert huge.request() is None
    assert huge.summary()["stop_reason"] == "character_budget"


def test_request_cap_refuses_atomically_without_clipping():
    source = msg(1, "a" * 49_000)
    run = replay([msg(0, "b" * 1_000), source])
    # The answer ledger can be large after a valid response, so the next
    # request must fail closed before disclosing more source.
    request = run.request()
    huge_value = "v" * 99_000
    cited = {"value": huge_value, "citations": [cite(source, "a")]}
    answer_set = answers(issue=cited)
    run.import_response(response(request, answer_set))
    assert run.request() is None
    assert run.summary()["stop_reason"] == "request_budget"
    assert run.summary()["disclosed_source_messages"] == 1


def test_initial_request_cap_never_counts_unissued_source_and_coordinates_reject():
    source = msg(0, "Use capture.")
    oversized = AdaptiveReplay([source], ("r", 0, 0), "c", "x" * 100_000)
    assert oversized.request() is None
    assert oversized.summary()["stop_reason"] == "request_budget"
    assert oversized.summary()["disclosed_source_messages"] == 0
    with pytest.raises(ValueError, match="anchor coordinate"):
        AdaptiveReplay([source], ("r", 0, 1), "c", "config")


def test_request_specifies_importable_response_and_exact_source_coordinates():
    request = replay([msg(0, "Use capture.")]).request()
    contract = request["output_contract"]
    assert contract["required_fields"] == ["request_id", "candidate_id", "answers", "reference_links"]
    assert contract["optional_usage_fields"] == ["prompt_tokens", "completion_tokens"]
    assert "usage" in contract["usage_shape"]
    assert contract["answer_slots"] == list(answers())
    assert contract["citation_fields"] == ["rollout_id", "turn", "source_ordinal", "start", "end", "quote"]
    assert contract["reference_link_fields"] == ["mention", "antecedents", "status"]
    instructions = request["extraction_instructions"]
    assert "zero-based" in instructions and "end-exclusive" in instructions
    assert "original source" in instructions and "exact" in instructions
    assert "unknown" in instructions and "user" in instructions
    assert "semantic_verified" in instructions and "authoritative" in instructions
    assert "retained conversation context" in instructions

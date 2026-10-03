"""Record-first curator behavior and conditional source disclosure."""

from copy import deepcopy

import pytest

from hosted.curator.advisory import review_accepted_decision


def _submission():
    return {"record_id": "new", "accepted_write_id": "accepted-new",
            "source_owner_id": "owner", "provenance": "first-hand",
            "claim": "Use parser B for imports.",
            "anchor": {"rollout_id": "rollout", "turn": 3, "source_ordinal": 3},
            "topics": ["imports"], "links": []}


def _message():
    return {"rollout_id": "rollout", "turn": 3, "source_ordinal": 3,
            "actor": "user", "text": "Use parser B for imports."}


def _answer(*, more=False, questions=None, links=None, topics=None):
    return {"needs_more_context": more, "source_questions": questions or [],
            "topic_suggestions": topics or [], "link_suggestions": links or [],
            "conflict_flags": []}


def test_record_comparison_finishes_without_opening_source_window():
    submission = _submission()
    original = deepcopy(submission)
    calls = []

    def reviewer(claim, context, state):
        calls.append((context, state))
        return _answer(topics=[{"action": "add", "topic": "parser",
                                "reason": "The accepted claim names the parser.",
                                "citations": [{"kind": "accepted_claim", "start": 4,
                                               "end": 12, "quote": "parser B"}]}])

    report = review_accepted_decision(submission, [], {"parser": "Parser"}, {}, reviewer)
    assert len(calls) == 1
    assert calls[0][0]["kind"] == "records"
    assert calls[0][1]["phase"] == "records"
    assert report["status"] == "reviewed"
    assert report["source_check_requested"] is False
    assert report["window"]["disclosed_source_messages"] == 0
    assert report["window"]["expansion_calls"] == 0
    assert report["topic_suggestions"][0]["topic"] == "parser"
    assert submission == original


def test_existing_decision_is_required_for_link_suggestion_without_source_window():
    prior = {"old": {"claim": "Use parser A for imports."}}

    def reviewer(_claim, context, _state):
        assert context["existing_records"] == prior
        return _answer(links=[{"action": "add", "target_id": "old",
                               "kind": "replaces", "reason": "The new choice replaces A.",
                               "citations": [{"kind": "existing_record", "record_id": "old",
                                              "start": 0, "end": 25,
                                              "quote": "Use parser A for imports."}]}])

    report = review_accepted_decision(_submission(), [], {}, prior, reviewer)
    assert report["link_suggestions"][0]["target_id"] == "old"
    assert report["window"]["disclosed_source_messages"] == 0


def test_named_uncertainty_opens_bounded_dialogue_only_after_record_comparison():
    calls = []

    def reviewer(_claim, context, state):
        calls.append((context["kind"], state["phase"]))
        if context["kind"] == "records":
            return _answer(more=True, questions=["Did the user limit parser B to imports?"])
        assert state["source_questions"] == ["Did the user limit parser B to imports?"]
        assert [m["actor"] for m in context["messages"]] == ["user"]
        return _answer()

    messages = [_message(), {**_message(), "source_ordinal": 4,
                             "actor": "tool", "text": "private tool output"}]
    report = review_accepted_decision(_submission(), messages, {}, {}, reviewer)
    assert calls == [("records", "records"), ("dialogue", "source")]
    assert report["source_check_requested"] is True
    assert report["window"]["disclosed_source_messages"] == 1
    assert report["review_calls"] == 2


def test_source_request_without_specific_question_is_rejected():
    with pytest.raises(ValueError, match="source_questions"):
        review_accepted_decision(_submission(), [_message()], {}, {},
                                 lambda *_: _answer(more=True))


def test_unavailable_source_leaves_named_question_incomplete():
    report = review_accepted_decision(
        _submission(), [], {}, {},
        lambda *_: _answer(more=True, questions=["Was the choice limited to imports?"]))
    assert report["status"] == "incomplete"
    assert report["stop_reason"] == "source_unavailable"
    assert report["source_questions_remaining"] == ["Was the choice limited to imports?"]
    assert report["window"]["disclosed_source_messages"] == 0

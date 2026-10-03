"""Offline contract tests for post-write, advisory-only hosted curation."""

import pytest

from hosted.curator.advisory import review_accepted_decision


def _message(turn, ordinal, actor, text):
    return {"rollout_id": "rollout-a", "turn": turn, "source_ordinal": ordinal,
            "actor": actor, "text": text}


def _submission():
    return {
        "record_id": "decision-1", "accepted_write_id": "write-1",
        "source_owner_id": "member-1", "provenance": "first-hand",
        "claim": "Use option B for the parser.",
        "anchor": {"rollout_id": "rollout-a", "turn": 3, "source_ordinal": 3},
        "topics": ["capture"], "links": [],
    }


def _citation(message, quote):
    start = message["text"].index(quote)
    return {"rollout_id": message["rollout_id"], "turn": message["turn"],
            "source_ordinal": message["source_ordinal"], "start": start,
            "end": start + len(quote), "quote": quote}


def _claim_citation(claim, quote):
    start = claim.index(quote)
    return {"kind": "accepted_claim", "start": start,
            "end": start + len(quote), "quote": quote}


def test_curator_suggests_topics_and_links_without_mutating_submission():
    messages = [_message(1, 1, "user", "Option B builds on the capture decision."),
                _message(3, 3, "user", "Use option B for the parser.")]
    submission = _submission()
    calls = []

    def reviewer(claim, batch, state):
        if batch["kind"] == "records":
            return {"needs_more_context": True,
                    "source_questions": ["Which earlier proposal did the approval reference?"],
                    "topic_suggestions": [], "link_suggestions": [], "conflict_flags": []}
        calls.append([item["turn"] for item in batch["messages"]])
        if len(calls) == 1:
            return {"needs_more_context": True,
                    "source_questions": ["Which earlier proposal did the approval reference?"],
                    "topic_suggestions": [],
                    "link_suggestions": [], "conflict_flags": [],
                    "usage": {"prompt_tokens": 12, "completion_tokens": 4}}
        return {"needs_more_context": False,
                "topic_suggestions": [{"action": "add", "topic": "parser", "reason": "The choice concerns the parser.",
                                       "citations": [_citation(messages[1], "parser")]}],
                "link_suggestions": [{"action": "add", "target_id": "prior-1", "kind": "related",
                                      "reason": "The proposal refers to the earlier capture decision.",
                                      "citations": [_citation(messages[0], "capture decision")]}],
                "conflict_flags": [], "usage": {"prompt_tokens": 18, "completion_tokens": 8}}

    report = review_accepted_decision(
        submission, messages, {"capture": "Capture", "parser": "Parser"},
        {"prior-1": {"title": "Capture decision"}}, reviewer)
    assert report["status"] == "reviewed"
    assert calls == [[3], [1]]
    assert report["topic_suggestions"][0]["topic"] == "parser"
    assert report["link_suggestions"][0]["target_id"] == "prior-1"
    assert report["usage"] == {"prompt_tokens": 30, "completion_tokens": 12}
    assert submission["topics"] == ["capture"] and submission["links"] == []
    assert report["advisory_only"] is True
    assert report["claim_provenance"] == "first-hand"
    assert report["topic_suggestions"][0]["source"] == "reconstructed"


def test_window_exhaustion_flags_incomplete_without_expanding_further():
    messages = [_message(0, 1, "user", "An old proposal."),
                _message(3, 3, "user", "Use option B for the parser.")]

    def reviewer(claim, batch, state):
        return {"needs_more_context": True,
                "source_questions": ["What prompted this decision?"],
                "topic_suggestions": [],
                "link_suggestions": [], "conflict_flags": []}

    report = review_accepted_decision(_submission(), messages, {}, {}, reviewer)
    assert report["status"] == "incomplete"
    assert report["stop_reason"] == "session_start"
    assert report["review_calls"] == 4  # records, anchor, empty turn pair, old proposal


def test_twenty_turn_cap_does_not_reach_older_source():
    submission = _submission()
    submission["anchor"] = {"rollout_id": "rollout-a", "turn": 25, "source_ordinal": 25}
    messages = [_message(0, 0, "user", "The original proposal."),
                _message(25, 25, "user", "Use it.")]
    seen = []

    def reviewer(_claim, batch, _state):
        if batch["kind"] == "dialogue":
            seen.extend(item["turn"] for item in batch["messages"])
        return {"needs_more_context": True,
                "source_questions": ["What did 'it' refer to?"],
                "topic_suggestions": [],
                "link_suggestions": [], "conflict_flags": []}

    report = review_accepted_decision(submission, messages, {}, {}, reviewer)
    assert report["status"] == "incomplete"
    assert report["stop_reason"] == "window_exhausted"
    assert report["window"]["expansion_calls"] == 10
    assert report["review_calls"] == 12
    assert seen == [25]


def test_rejects_unaccepted_write_and_invalid_or_tool_only_citations():
    messages = [_message(3, 3, "user", "Use option B for the parser."),
                _message(3, 4, "tool", "Hidden tool evidence")]
    submission = _submission()
    submission["accepted_write_id"] = ""
    with pytest.raises(ValueError, match="accepted_write_id"):
        review_accepted_decision(submission, messages, {}, {}, lambda *_: {})
    submission["accepted_write_id"] = "write-1"
    submission["provenance"] = "reconstructed"
    with pytest.raises(ValueError, match="first-hand"):
        review_accepted_decision(submission, messages, {}, {}, lambda *_: {})
    submission["provenance"] = "first-hand"

    def invalid(_claim, _batch, _state):
        return {"needs_more_context": False,
                "topic_suggestions": [{"action": "add", "topic": "unknown", "reason": "Guess",
                                       "citations": [_claim_citation(_submission()["claim"], "parser")]}],
                "link_suggestions": [], "conflict_flags": []}

    with pytest.raises(ValueError, match="unknown topic"):
        review_accepted_decision(submission, messages, {}, {}, invalid)

    def tool_only(_claim, _batch, _state):
        if _batch["kind"] == "records":
            return {"needs_more_context": True,
                    "source_questions": ["Does dialogue support the reason?"],
                    "topic_suggestions": [], "link_suggestions": [], "conflict_flags": []}
        return {"needs_more_context": False, "topic_suggestions": [],
                "link_suggestions": [],
                "conflict_flags": [{"field": "reason", "reason": "Tool says otherwise",
                                    "citations": [_citation(messages[1], "Hidden")]}]}

    with pytest.raises(ValueError, match="undisclosed citation"):
        review_accepted_decision(submission, messages, {}, {}, tool_only)


def test_conflict_is_only_a_flag_and_link_targets_must_exist():
    messages = [_message(3, 3, "user", "Use option B for the parser.")]
    citation = _claim_citation(_submission()["claim"], "option B")

    def reviewer(_claim, _batch, _state):
        return {"needs_more_context": False, "topic_suggestions": [],
                "link_suggestions": [{"action": "add", "target_id": "missing", "kind": "related",
                                      "reason": "No record", "citations": [citation]}],
                "conflict_flags": []}

    with pytest.raises(ValueError, match="unknown link target"):
        review_accepted_decision(_submission(), messages, {}, {}, reviewer)

    def flagged(_claim, _batch, _state):
        return {"needs_more_context": False, "topic_suggestions": [],
                "link_suggestions": [],
                "conflict_flags": [{"field": "scope", "reason": "Check scope against user wording",
                                    "citations": [citation]}]}

    report = review_accepted_decision(_submission(), messages, {}, {}, flagged)
    assert report["conflict_flags"][0]["field"] == "scope"
    assert report["advisory_only"] is True


def test_stale_topic_and_link_can_only_be_proposed_for_removal():
    message = _message(3, 3, "user", "Use option B for the parser.")
    claim = _submission()
    claim["links"] = [{"target_id": "prior-1", "kind": "related"}]

    def reviewer(_claim, _batch, _state):
        evidence = [_claim_citation(claim["claim"], "parser")]
        return {"needs_more_context": False,
                "topic_suggestions": [{"action": "remove", "topic": "capture",
                                       "reason": "The current topic is stale for this decision.",
                                       "citations": evidence}],
                "link_suggestions": [{"action": "remove", "target_id": "prior-1",
                                      "kind": "related", "reason": "The existing link is not relevant.",
                                      "citations": evidence}],
                "conflict_flags": []}

    report = review_accepted_decision(claim, [message], {"capture": "Capture"},
                                      {"prior-1": {"title": "Capture"}}, reviewer)
    assert report["topic_suggestions"][0]["action"] == "remove"
    assert report["link_suggestions"][0]["action"] == "remove"
    assert claim["topics"] == ["capture"] and len(claim["links"]) == 1


def test_repeated_advice_across_expansions_is_one_suggestion():
    messages = [_message(1, 1, "user", "Parser proposal."),
                _message(3, 3, "user", "Use the parser proposal.")]

    def reviewer(_claim, _batch, state):
        if _batch["kind"] == "records":
            return {"needs_more_context": True,
                    "source_questions": ["Does the dialogue support the parser topic?"],
                    "topic_suggestions": [], "link_suggestions": [], "conflict_flags": []}
        more = state["review_call"] == 1
        return {"needs_more_context": more,
                "source_questions": ["Does the dialogue support the parser topic?"] if more else [],
                "topic_suggestions": [{"action": "add", "topic": "parser",
                                       "reason": f"Parser evidence pass {state['review_call']}",
                                       "citations": [_citation(messages[1], "parser")]}],
                "link_suggestions": [], "conflict_flags": []}

    report = review_accepted_decision(_submission(), messages, {"parser": "Parser"}, {}, reviewer)
    assert len(report["topic_suggestions"]) == 1


@pytest.mark.parametrize("bad_citation", [
    {"rollout_id": "rollout-a", "turn": [], "source_ordinal": 3,
     "start": 0, "end": 3, "quote": "Use"},
    {"rollout_id": "rollout-a", "turn": 3, "source_ordinal": 3,
     "start": 0, "end": 3, "quote": "Not"},
])
def test_untrusted_citations_fail_closed_as_validation_errors(bad_citation):
    message = _message(3, 3, "user", "Use option B for the parser.")

    def reviewer(_claim, _batch, _state):
        return {"needs_more_context": False,
                "topic_suggestions": [{"action": "add", "topic": "parser", "reason": "Parser",
                                       "citations": [bad_citation]}],
                "link_suggestions": [], "conflict_flags": []}

    with pytest.raises(ValueError, match="citation"):
        review_accepted_decision(_submission(), [message], {"parser": "Parser"}, {}, reviewer)

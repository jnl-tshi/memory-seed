import json

import pytest

from hosted.capture.disclosure import AdaptiveDisclosure


def message(turn, ordinal=0, text="x", rollout="r", actor="user"):
    return {"rollout_id": rollout, "turn": turn, "source_ordinal": ordinal, "actor": actor, "text": text}


def test_initial_current_turn_and_twenty_preceding_in_ten_expansions():
    d = AdaptiveDisclosure([message(t) for t in range(31)], ("r", 30, 0))
    assert d.batches[0]["turns"] == [30]
    batches = [d.expand() for _ in range(10)]
    assert [b["turns"] for b in batches] == [list(range(28,30)), list(range(26,28)), list(range(24,26)), list(range(22,24)), list(range(20,22)), list(range(18,20)), list(range(16,18)), list(range(14,16)), list(range(12,14)), list(range(10,12))]
    assert d.expand() is None
    assert d.stop_reason == "window_exhausted"
    assert d.expansion_calls == 10


def test_session_start_and_missing_turns_advance_positions_with_empty_batches():
    d = AdaptiveDisclosure([message(4), message(1)], ("r", 4, 0))
    assert d.expand()["turns"] == [2, 3]
    assert d.expand()["turns"] == [0, 1]
    assert d.stop_reason == "session_start"


def test_coordinate_validation_later_source_exclusion_and_order():
    with pytest.raises(ValueError):
        AdaptiveDisclosure([message(2), message(2)], ("r", 2, 0))
    with pytest.raises(ValueError):
        AdaptiveDisclosure([message(2), message(1, rollout="other")], ("r", 2, 0))
    d = AdaptiveDisclosure([message(2, 5), message(2, 1), message(2, 7), message(3)], ("r", 2, 5))
    assert [m["source_ordinal"] for m in d.batches[0]["messages"]] == [1, 5]


def test_budget_refusal_is_atomic_for_initial_and_expansion_batches():
    d = AdaptiveDisclosure([message(3, text="a" * 30000), message(2, text="b" * 25001)], ("r", 3, 0))
    assert d.batches[0]["source_characters"] == 30000
    assert d.expand() is None
    assert d.stop_reason == "character_budget"
    assert len(d.batches) == 1
    initial = AdaptiveDisclosure([message(1, text="a" * 50001)], ("r", 1, 0))
    assert initial.batches == []
    assert initial.stop_reason == "character_budget"


def test_question_complete_stop_usage_exact_once_and_json_roundtrip():
    d = AdaptiveDisclosure([message(t) for t in range(4)], ("r", 3, 0))
    d.record_usage(0, 10, 2)
    d.record_usage(0, 10, 2)
    with pytest.raises(ValueError):
        d.record_usage(0, 11, 2)
    d.mark_questions_complete()
    assert d.expand() is None
    assert d.stop_reason == "answered_all_questions"
    summary = d.summary()
    assert summary["prompt_tokens"] == 10 and summary["completion_tokens"] == 2
    assert len(json.loads(json.dumps(d.to_dict()))["batches"]) == 1


def test_batch_digest_stable_and_message_copies_are_isolated():
    source = message(0)
    d = AdaptiveDisclosure([source], ("r", 0, 0))
    source["text"] = "changed"
    assert d.batches[0]["messages"][0]["text"] == "x"
    assert len(d.batches[0]["digest"]) == 64


def test_returned_batches_and_history_snapshots_are_defensive_copies():
    d = AdaptiveDisclosure([message(t) for t in range(4)], ("r", 3, 0))
    batch = d.expand()
    digest = d.batches[0]["digest"]
    batch["messages"][0]["text"] = "mutated return"
    batch["turns"].clear()
    snapshot = d.batches
    snapshot[0]["messages"][0]["text"] = "mutated history"
    snapshot[0]["source_characters"] = 900
    serialized = d.to_dict()
    serialized["batches"][0]["messages"][0]["text"] = "mutated serialization"
    assert d.batches[0]["messages"][0]["text"] == "x"
    assert d.batches[0]["source_characters"] == 1
    assert d.batches[0]["digest"] == digest
    assert d.summary()["disclosed_source_characters"] == 3


def test_questions_complete_overrides_session_and_window_boundary_stop():
    at_session_start = AdaptiveDisclosure([message(0)], ("r", 0, 0))
    at_session_start.mark_questions_complete()
    assert at_session_start.stop_reason == "answered_all_questions"

    at_window_end = AdaptiveDisclosure([message(t) for t in range(31)], ("r", 30, 0))
    for _ in range(10):
        at_window_end.expand()
    assert at_window_end.stop_reason == "window_exhausted"
    at_window_end.mark_questions_complete()
    assert at_window_end.stop_reason == "answered_all_questions"

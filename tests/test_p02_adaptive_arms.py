import copy

import pytest

from hosted.evaluation.adaptive_arms import prepare_arms
from hosted.evaluation.adaptive_replay import AdaptiveReplay
from hosted.capture.evidence_ledger import EvidenceLedger


def frozen_config(**changes):
    config = {
        "model_name": "example-model",
        "reasoning_effort": "medium",
        "prompt_protocol_version": "v1",
        "arm_policy": "paired-source-v1",
    }
    config.update(changes)
    return config


def inventory(last_turn=4, *, rollout="r"):
    messages = []
    ordinal = 0
    for turn in range(last_turn + 1):
        messages.extend([
            {"rollout_id": rollout, "turn": turn, "source_ordinal": ordinal,
             "actor": "user", "text": f"user {turn}"},
            {"rollout_id": rollout, "turn": turn, "source_ordinal": ordinal + 1,
             "actor": "assistant", "text": f"assistant {turn}"},
        ])
        ordinal += 2
    return messages


def run(messages, anchor=None, config=None):
    anchor = anchor or ("r", messages[-1]["turn"], messages[-1]["source_ordinal"])
    return prepare_arms(messages, anchor, "case-1", config or frozen_config())


def packet(result, name):
    return result["arms"][name]["request"]


def test_adaptive_starts_at_anchor_and_static_arms_group_original_turns():
    messages = inventory(3)
    result = run(messages)
    assert packet(result, "adaptive")["messages"] == messages[-2:]
    fixed = packet(result, "fixed_window")
    assert fixed["turns"] == [0, 1, 2, 3]
    assert fixed["messages"] == messages
    assert packet(result, "full_window")["messages"] == messages
    fresh = AdaptiveReplay(messages, ("r", 3, 7), "case-1", result["configuration_hash"])
    adaptive_request = packet(result, "adaptive")
    assert adaptive_request == fresh.request()
    response = {
        "request_id": adaptive_request["request_id"],
        "candidate_id": "case-1",
        "answers": {slot: None for slot in EvidenceLedger.SLOTS},
        "reference_links": [],
    }
    fresh.import_response(response)
    assert all(result["arms"][arm]["summary"]["configuration_hash"] == result["configuration_hash"]
               for arm in result["arms"])


def test_fixed_arm_includes_exactly_twenty_preceding_turns():
    messages = inventory(25)
    result = run(messages)
    fixed = packet(result, "fixed_window")
    assert fixed["turns"] == list(range(5, 26))
    assert len(fixed["messages"]) == 42


def test_short_session_fixed_window_stops_at_session_start():
    messages = inventory(4)
    result = run(messages)
    assert packet(result, "fixed_window")["turns"] == [0, 1, 2, 3, 4]


def test_causal_filter_preserves_anchor_turn_group_but_excludes_later_messages():
    messages = inventory(3)
    anchor = ("r", 2, messages[4]["source_ordinal"])
    result = run(messages, anchor)
    assert all((m["turn"], m["source_ordinal"]) <= anchor[1:] for arm in result["arms"].values()
               if arm["request"] for m in arm["request"]["messages"])
    assert packet(result, "fixed_window")["messages"] == messages[:5]


def test_duplicate_coordinates_and_mixed_rollouts_are_rejected():
    messages = inventory(1)
    changed_duplicate = copy.deepcopy(messages)
    changed_duplicate.append({**messages[0], "text": "changed"})
    with pytest.raises(ValueError, match="coordinate"):
        run(changed_duplicate)
    with pytest.raises(ValueError, match="rollout"):
        run(inventory(1, rollout="other"), ("r", 1, 3))


def test_packets_exclude_private_evaluation_fields_and_summary_has_no_source_text():
    messages = inventory(1)
    messages[-1].update({"gold": "secret", "review": "secret", "root_id": "secret",
                         "split": "secret", "expected_output": "secret", "evaluation": "secret"})
    result = run(messages)
    for arm in result["arms"].values():
        serialized = repr(arm["request"])
        for secret in ("gold", "review", "root_id", "split", "expected_output", "evaluation", "secret"):
            assert secret not in serialized
        assert arm["summary"]["source_characters"] >= 0
        assert "text" not in repr(arm["summary"])


def test_hashes_are_stable_and_change_with_frozen_configuration():
    messages = inventory(2)
    first = run(messages)
    second = run(messages)
    changed = run(messages, config=frozen_config(reasoning_effort="high"))
    assert first["configuration_hash"] == second["configuration_hash"]
    assert first["arms"]["fixed_window"]["summary"]["request_id"] == second["arms"]["fixed_window"]["summary"]["request_id"]
    assert first["configuration_hash"] != changed["configuration_hash"]
    assert all(a["summary"]["configuration_hash"] == changed["configuration_hash"]
               for a in changed["arms"].values())


def test_huge_earlier_turn_makes_full_unavailable_without_truncation():
    messages = inventory(3)
    messages[0]["text"] = "x" * 50_001
    result = run(messages)
    full = result["arms"]["full_window"]
    assert full["request"] is None
    assert full["summary"]["unavailability_reason"]
    assert packet(result, "adaptive")["messages"] == messages[-2:]
    assert packet(result, "fixed_window")["messages"] == messages[2:]
    fixed_summary = result["arms"]["fixed_window"]["summary"]
    assert fixed_summary["source_span_status"] == "partial"
    assert fixed_summary["source_span_stop_reason"] == "character_budget"
    assert fixed_summary["arm"] == "fixed_window"


def test_tool_calls_are_absent_from_every_arm_and_do_not_block_earlier_dialogue():
    messages = inventory(2)
    messages.insert(2, {"rollout_id": "r", "turn": 0, "source_ordinal": 100,
                        "actor": "tool", "text": "x" * 50_001})
    result = run(messages, ("r", 2, 5))
    for arm in result["arms"].values():
        assert arm["request"] is not None
        assert all(message["actor"] != "tool" for message in arm["request"]["messages"])
    assert len(packet(result, "full_window")["messages"]) == 6
    assert packet(result, "fixed_window")["turns"] == [0, 1, 2]

"""Synthetic controls for the historical adaptive source audit."""

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


PATH = Path(__file__).with_name("audit_adaptive_sources.py")
SPEC = importlib.util.spec_from_file_location("audit_adaptive_sources", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def inventory(count=5, *, long_turn=None):
    rows = []
    for turn in range(count):
        rows.append({"rollout_id": "r", "turn": turn, "source_ordinal": turn,
                     "actor": "user", "text": "x" * 50_001 if turn == long_turn else f"turn {turn}"})
    return rows


def ref(turn, *, rollout="r"):
    return {"rollout_id": rollout, "turn": turn, "source_ordinal": turn}


def test_oracle_coverage_tracks_two_turn_expansions_without_claiming_semantics():
    result = MODULE.audit_case(inventory(), ("r", 4, 4), [ref(0)], "case")
    assert result["source_ref_count"] == 1
    assert result["initial_gold_covered"] is False
    assert result["oracle_gold_covered"] is True
    assert result["oracle_expansions_to_cover"] == 2
    assert result["fixed_gold_covered"] is True
    assert result["full_gold_covered"] is True
    assert result["semantic_decision_accuracy"] is None


def test_budget_failure_is_not_reported_as_gold_coverage():
    result = MODULE.audit_case(inventory(long_turn=2), ("r", 4, 4), [ref(0)], "case")
    assert result["oracle_gold_covered"] is False
    assert result["oracle_expansions_to_cover"] is None
    assert result["stop_reason"] == "character_budget"
    assert result["fixed_gold_covered"] is False


def test_out_of_rollout_gold_is_explicitly_unavailable():
    result = MODULE.audit_case(inventory(), ("r", 4, 4), [ref(0, rollout="parent")], "case")
    assert result["source_refs_present"] == 0
    assert result["oracle_gold_covered"] is False
    assert result["unavailable_gold_refs"] == 1


def test_missing_gold_ref_is_not_silently_dropped():
    missing = {"rollout_id": "r", "turn": 1, "source_ordinal": 99}
    result = MODULE.audit_case(inventory(), ("r", 4, 4), [missing], "case")
    assert result["source_refs_present"] == 0
    assert result["unavailable_gold_refs"] == 1


def test_direct_cli_can_load_project_modules():
    result = subprocess.run([sys.executable, str(PATH), "--help"],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


def test_frozen_replay_source_hash_must_match():
    MODULE.verify_source_hash({"r": "abc"}, "r", "abc")
    with pytest.raises(ValueError, match="frozen replay"):
        MODULE.verify_source_hash({"r": "abc"}, "r", "changed")
    with pytest.raises(ValueError, match="frozen replay"):
        MODULE.verify_source_hash({}, "r", "abc")


def test_tool_call_bulk_can_block_causal_dialogue_without_silent_clipping():
    blocks = [SimpleNamespace(turn_number=turn, items=[
        SimpleNamespace(role="user", source_ordinal=turn * 2, text=f"turn {turn}"),
        SimpleNamespace(role="tool", source_ordinal=turn * 2 + 1,
                        text="x" * 50_001 if turn == 2 else "tool"),
    ]) for turn in range(5)]
    dialogue = MODULE._source_inventory(blocks, "r", include_tools=False)
    with_tools = MODULE._source_inventory(blocks, "r", include_tools=True)
    anchor = ("r", 4, 8)
    evidence = [{"rollout_id": "r", "turn": 0, "source_ordinal": 0}]
    assert MODULE.audit_case(dialogue, anchor, evidence, "case")["oracle_gold_covered"]
    result = MODULE.audit_case(with_tools, anchor, evidence, "case")
    assert result["oracle_gold_covered"] is False
    assert result["stop_reason"] == "character_budget"

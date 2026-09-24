from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("measure_cited_messages", BASE / "measure_cited_messages.py")
assert SPEC and SPEC.loader
measure = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = measure
SPEC.loader.exec_module(measure)


class CitedMessageTests(unittest.TestCase):
    def test_collects_all_explicit_ordinals_without_turn_expansion(self) -> None:
        row = {"adjudication": {"evidence_refs": [
            {"rollout_id": "r1", "turn": 2, "ordinals": [11, 13]},
            {"rollout_id": "r1", "turn": 3, "ordinals": [18]},
        ]}}
        self.assertEqual(measure.wanted_refs(row), {("r1", 11), ("r1", 13), ("r1", 18)})

    def test_rejects_duplicate_decisions_across_gold_files(self) -> None:
        rows = [{"decision": {"id": "same"}}, {"decision": {"id": "same"}}]
        with self.assertRaisesRegex(ValueError, "Duplicate decision"):
            measure.validate_ids(rows, set())

    def test_expected_strict_total_excludes_documentation_controls(self) -> None:
        rows = [{"decision": {"id": "a"}}, {"decision": {"id": "doc"}}]
        self.assertEqual(measure.validate_ids(rows, {"doc"}), ["a"])

    def test_item_completed_agent_message_is_readable_cited_event(self) -> None:
        row = {"type": "event_msg", "payload": {"type": "item_completed", "item": {
            "type": "AgentMessage", "content": [{"type": "Text", "text": "A decision."}]}}}
        text, role, tool_output, omitted = measure.cited_raw_text(row)
        self.assertEqual(text, "A decision.")
        self.assertEqual(role, "assistant")
        self.assertFalse(tool_output)
        self.assertEqual(omitted, 0)


if __name__ == "__main__":
    unittest.main()

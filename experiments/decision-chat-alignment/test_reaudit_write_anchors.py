"""Regression tests for write-event anchoring in the post-audit pass."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


BASE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("reaudit_write_anchors", BASE / "reaudit_write_anchors.py")
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class WriteAnchorTests(unittest.TestCase):
    def _rollout(self, rows: list[dict]) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = Path(temp.name) / "rollout.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        return path

    def test_file_change_is_write_but_preview_is_not(self) -> None:
        entry_id = "mse_abcdef1234567890"
        path = self._rollout([
            {"timestamp": "2026-09-06T00:01:00Z", "ordinal": 1,
             "type": "response_item", "payload": {"type": "custom_tool_call_output",
             "output": f"Would append {entry_id} to .memory-seed/sessions/2026-09/2026-09-06.md"}},
            {"timestamp": "2026-09-06T00:02:00Z", "ordinal": 2,
             "type": "event_msg", "payload": {"type": "item_completed",
             "item": {"type": "FileChange", "status": "completed", "changes": {
                 "C:/repo/.memory-seed/sessions/2026-09/2026-09-06.md": {
                     "type": "update", "unified_diff": f"+entry_id: {entry_id}"}}}}},
        ])
        event = module.find_write_event(path, entry_id, ".memory-seed/sessions/2026-09/2026-09-06.md")
        self.assertIsNotNone(event)
        self.assertEqual(event.timestamp, "2026-09-06T00:02:00Z")
        self.assertEqual(event.kind, "file_change")

    def test_append_receipt_is_write_but_dry_run_is_not(self) -> None:
        entry_id = "mse_abcdef1234567890"
        path = self._rollout([
            {"timestamp": "2026-09-24T13:38:38Z", "ordinal": 1,
             "type": "response_item", "payload": {"type": "custom_tool_call_output",
             "output": [{"text": f"Would append {entry_id} to the session"}]}},
            {"timestamp": "2026-09-24T13:38:50Z", "ordinal": 2,
             "type": "response_item", "payload": {"type": "custom_tool_call_output",
             "output": [{"text": f"Appended {entry_id} to the session"}]}},
        ])
        event = module.find_write_event(path, entry_id, ".memory-seed/sessions/2026-09/2026-09-24.md")
        self.assertIsNotNone(event)
        self.assertEqual(event.timestamp, "2026-09-24T13:38:50Z")
        self.assertEqual(event.kind, "append_receipt")

    def test_legacy_flat_session_path_matches_grouped_current_path(self) -> None:
        entry_id = "mse_abcdef1234567890"
        path = self._rollout([{
            "timestamp": "2026-07-07T12:04:01Z", "ordinal": 5,
            "type": "event_msg", "payload": {"type": "item_completed", "item": {
                "type": "FileChange", "status": "completed", "changes": {
                    "C:/repo/.memory-seed/sessions/2026-07-07.md": {
                        "type": "update", "unified_diff": f"+entry_id: {entry_id}"}}}}},
        ])
        event = module.find_write_event(path, entry_id, ".memory-seed/sessions/2026-07/2026-07-07.md")
        self.assertIsNotNone(event)
        self.assertEqual(event.timestamp, "2026-07-07T12:04:01Z")

    def test_child_writer_is_in_selected_parent_lineage(self) -> None:
        parent = SimpleNamespace(session_id="parent", parent_thread_id=None)
        child = SimpleNamespace(session_id="child", parent_thread_id="parent")
        unrelated = SimpleNamespace(session_id="other", parent_thread_id=None)
        self.assertTrue(module.belongs_to_lineage(child, "parent", [parent, child, unrelated]))
        self.assertFalse(module.belongs_to_lineage(unrelated, "parent", [parent, child, unrelated]))

    def test_same_turn_content_is_clipped_at_write_event(self) -> None:
        items = [
            SimpleNamespace(timestamp="2026-09-24T13:38:20Z", source_ordinal=10),
            SimpleNamespace(timestamp="2026-09-24T13:38:50Z", source_ordinal=11),
            SimpleNamespace(timestamp="2026-09-24T13:39:01Z", source_ordinal=12),
        ]
        retained = module.prewrite_items(items, "2026-09-24T13:38:50Z")
        self.assertEqual([item.source_ordinal for item in retained], [10])

    def test_selection_rejects_post_write_citation(self) -> None:
        row = {"decision_id": "mse_test:d1", "status": "write_event_found",
               "write_event_timestamp": "2026-09-24T13:38:50Z",
               "backward_20_lineage_coordinates": [["rollout", 2]]}
        block = SimpleNamespace(turn_number=2, items=[
            SimpleNamespace(source_ordinal=10, timestamp="2026-09-24T13:38:49Z", role="assistant"),
            SimpleNamespace(source_ordinal=11, timestamp="2026-09-24T13:38:51Z", role="assistant")],
            reasoning_summary_items=[])
        selection = {"decision_id": "mse_test:d1", "label": "verified_source", "rationale": "test",
                     "evidence_refs": [{"rollout_id": "rollout", "turn": 2, "ordinals": [11]}]}
        with self.assertRaisesRegex(ValueError, "not before write"):
            module.validate_selection(selection, row, {"rollout": [block]})

    def test_selection_requires_citation_inside_lineage_scope(self) -> None:
        row = {"decision_id": "mse_test:d1", "status": "write_event_found",
               "write_event_timestamp": "2026-09-24T13:38:50Z",
               "backward_20_lineage_coordinates": [["rollout", 2]]}
        block = SimpleNamespace(turn_number=1, items=[
            SimpleNamespace(source_ordinal=10, timestamp="2026-09-24T13:38:49Z", role="assistant")],
            reasoning_summary_items=[])
        selection = {"decision_id": "mse_test:d1", "label": "verified_source", "rationale": "test",
                     "evidence_refs": [{"rollout_id": "rollout", "turn": 1, "ordinals": [10]}]}
        with self.assertRaisesRegex(ValueError, "outside backward scope"):
            module.validate_selection(selection, row, {"rollout": [block]})

    def test_unresolved_selection_cannot_claim_evidence(self) -> None:
        row = {"decision_id": "mse_test:d1", "status": "write_event_found",
               "write_event_timestamp": "2026-09-24T13:38:50Z",
               "backward_20_lineage_coordinates": []}
        selection = {"decision_id": "mse_test:d1", "label": "unresolved",
                     "evidence_refs": [{"rollout_id": "rollout", "turn": 2, "ordinals": [10]}]}
        with self.assertRaisesRegex(ValueError, "unresolved"):
            module.validate_selection(selection, row, {})


if __name__ == "__main__":
    unittest.main()

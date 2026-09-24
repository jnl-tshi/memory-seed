from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import evaluate_token_efficiency as evaluator


class FakeEncoding:
    def __init__(self, ids):
        self.ids = ids


class FakeTokenizer:
    def encode(self, text, add_special_tokens=False):
        return FakeEncoding(text.split())


@dataclass
class Item:
    source_ordinal: int | None
    timestamp: str | None
    turn_number: int
    role: str
    text: str


@dataclass
class Session:
    rollout_id: str
    session_id: str = "task"


@dataclass
class Block:
    session: Session
    turn_number: int
    items: list[Item]
    reasoning_summary_items: list[Item]


def fixture():
    blocks = {
        "roll": [
            Block(
                Session("roll"),
                1,
                [
                    Item(1, "2026-09-24T11:59:00Z", 1, "user", "PRIVATE_SENTINEL evidence"),
                    Item(2, "2026-09-24T12:01:05Z", 1, "assistant", "future message"),
                ],
                [Item(3, "2026-09-24T11:59:30Z", 1, "reasoning_summary", "readable summary")],
            ),
            Block(
                Session("roll"),
                2,
                [Item(4, "2026-09-24T12:02:00Z", 2, "assistant", "later session content")],
                [],
            ),
        ]
    }
    gold = [{
        "decision": {"id": "d1", "timestamp": "2026-09-24T12:00:00Z"},
        "selected_candidate": {"rollout_id": "roll"},
        "adjudication": {"evidence_refs": [{"rollout_id": "roll", "turn": 1}]},
    }]
    evidence_coords = [["roll", 1]]
    scope_coords = [["roll", 1]]
    envelope_coords = [["roll", 1]]
    ranked_coords = [["roll", 1]]
    window = {"rows": [{
        "decision_id": "d1",
        "evidence_turns": evidence_coords,
        "source_scope_turns": scope_coords,
        "strategies": {"lineage_backward_20": {"coordinates": envelope_coords}},
    }]}
    ranked = {"rows": [{
        "decision_id": "d1",
        "evidence_turns": [["roll", 1]],
        "strategies": {"lexical_top_3": {"coordinates": [*ranked_coords, *ranked_coords]}},
    }]}
    return gold, window, ranked, blocks


class TokenEfficiencyTests(unittest.TestCase):
    def test_tool_output_extraction_omits_image_payloads_and_preserves_text(self):
        output = [
            {"type": "input_text", "text": "visible tool output"},
            {"type": "input_image", "image_url": "data:image/png;base64,DO_NOT_TOKENIZE"},
        ]
        text, omitted = evaluator.extract_tool_output_text(output)
        self.assertEqual(text, "visible tool output")
        self.assertEqual(omitted, 1)
        self.assertNotIn("DO_NOT_TOKENIZE", text)

    def test_raw_tool_output_counts_are_causal_and_not_returned_in_report(self):
        gold, window, ranked, blocks = fixture()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "rollout.jsonl"
            source.write_text("\n".join(json.dumps(row) for row in [
                {"ordinal": 0, "timestamp": "2026-09-24T11:59:00Z", "type": "event_msg", "payload": {"type": "task_started"}},
                {"ordinal": 1, "timestamp": "2026-09-24T11:59:30Z", "type": "response_item", "payload": {"type": "function_call_output", "output": "RAW_OUTPUT_SENTINEL"}},
                {"ordinal": 2, "timestamp": "2026-09-24T12:01:05Z", "type": "response_item", "payload": {"type": "function_call_output", "output": "FUTURE_OUTPUT_SENTINEL"}},
            ]) + "\n", encoding="utf-8")
            blocks["roll"][0].session.source_path = str(source)
            gold[0]["adjudication"]["minimal_useful_refs"] = [
                {"rollout_id": "roll", "ordinal": 1},
            ]
            result = evaluator.evaluate_rows(gold, window, ranked, blocks, FakeTokenizer())
        stage = result["rows"][0]["stages"]["lineage_backward_20"]
        self.assertEqual(stage["raw_tool_output_message_count"], 1)
        self.assertGreater(stage["raw_tool_output_tokens"], 0)
        serialized = json.dumps(result)
        self.assertNotIn("RAW_OUTPUT_SENTINEL", serialized)
        self.assertNotIn("FUTURE_OUTPUT_SENTINEL", serialized)
        for stage_name in ("full_logical_session", "lineage_backward_20", "lexical_top_3", "minimal_useful_content"):
            self.assertGreater(result["rows"][0]["stages"][stage_name]["raw_tool_output_tokens"], 0)

    def test_minimal_useful_raw_output_ordinal_is_validated_and_counted(self):
        gold, window, ranked, blocks = fixture()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "rollout.jsonl"
            source.write_text("\n".join(json.dumps(row) for row in [
                {"ordinal": 0, "timestamp": "2026-09-24T11:59:00Z", "type": "event_msg", "payload": {"type": "task_started"}},
                {"ordinal": 5, "timestamp": "2026-09-24T11:59:30Z", "type": "response_item", "payload": {"type": "custom_tool_call_output", "output": "minimal raw result"}},
            ]) + "\n", encoding="utf-8")
            blocks["roll"][0].session.source_path = str(source)
            gold[0]["adjudication"]["minimal_useful_refs"] = [
                {"rollout_id": "roll", "ordinal": 5},
            ]
            result = evaluator.evaluate_rows(gold, window, ranked, blocks, FakeTokenizer())
        useful = result["rows"][0]["stages"]["minimal_useful_content"]
        self.assertEqual(useful["method"], "adjudicated_message_ordinals")
        self.assertEqual(useful["coordinates"], [["roll", 1]])
        self.assertEqual(useful["message_count"], 0)
        self.assertEqual(useful["raw_tool_output_message_count"], 1)
        self.assertGreater(useful["raw_tool_output_tokens"], 0)

    def test_minimal_useful_raw_output_after_cutoff_is_rejected(self):
        gold, window, ranked, blocks = fixture()
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "rollout.jsonl"
            source.write_text(json.dumps({
                "ordinal": 5, "timestamp": "2026-09-24T12:01:05Z", "type": "response_item",
                "payload": {"type": "function_call_output", "output": "future raw result"},
            }) + "\n", encoding="utf-8")
            blocks["roll"][0].session.source_path = str(source)
            gold[0]["adjudication"]["minimal_useful_refs"] = [
                {"rollout_id": "roll", "ordinal": 5},
            ]
            with self.assertRaisesRegex(ValueError, "Unresolved minimal useful"):
                evaluator.evaluate_rows(gold, window, ranked, blocks, FakeTokenizer())

    def test_rollouts_referenced_across_lineage_stages_are_loaded(self):
        gold, window, ranked, _ = fixture()
        parent_coord = ["parent-rollout", 7]
        window["rows"][0]["source_scope_turns"].append(parent_coord)
        window["rows"][0]["strategies"]["lineage_backward_20"]["coordinates"].append(parent_coord)
        ranked["rows"][0]["strategies"]["lexical_top_3"]["coordinates"].append(parent_coord)
        self.assertEqual(
            evaluator.referenced_rollout_ids(gold, window, ranked),
            {"roll", "parent-rollout"},
        )

    def test_missing_referenced_parent_rollout_fails_closed(self):
        with patch.object(evaluator.alignment, "iter_rollout_paths", return_value=[]), patch.object(
            evaluator.alignment, "validate_unique_rollouts"
        ):
            with self.assertRaisesRegex(ValueError, "Referenced rollout logs unavailable: parent-rollout"):
                evaluator.load_referenced_rollouts(Path("unused"), {"parent-rollout"})

    def test_loader_parses_every_referenced_rollout(self):
        paths = [Path("child.jsonl"), Path("parent.jsonl")]
        metas = {
            paths[0]: SimpleNamespace(rollout_id="roll", session_id="task"),
            paths[1]: SimpleNamespace(rollout_id="parent-rollout", session_id="parent-task"),
        }
        with patch.object(evaluator.alignment, "iter_rollout_paths", return_value=paths), patch.object(
            evaluator.alignment, "read_session_meta", side_effect=lambda path: metas[path]
        ), patch.object(
            evaluator.alignment, "parse_rollout", side_effect=lambda path, meta: [meta.rollout_id]
        ), patch.object(evaluator.alignment, "validate_unique_rollouts"):
            loaded = evaluator.load_referenced_rollouts(Path("unused"), {"roll", "parent-rollout"})
        self.assertEqual(loaded, {"roll": ["roll"], "parent-rollout": ["parent-rollout"]})

    def test_full_logical_session_includes_continuation_rollouts(self):
        gold, window, ranked, blocks = fixture()
        blocks["continuation"] = [
            Block(
                Session("continuation", "task"),
                8,
                [Item(10, "2026-09-24T12:00:30Z", 8, "user", "continuation content")],
                [],
            )
        ]
        result = evaluator.evaluate_rows(gold, window, ranked, blocks, FakeTokenizer())
        stages = result["rows"][0]["stages"]
        self.assertIn(["continuation", 8], stages["full_logical_session"]["coordinates"])
        self.assertIn(["continuation", 8], stages["causal_logical_session"]["coordinates"])

    def test_integer_source_scope_turn_count_is_recomputed_as_coordinates(self):
        gold, window, ranked, blocks = fixture()
        window["rows"][0]["source_scope_turns"] = 17
        expected = {("roll", 1)}
        with patch.object(evaluator.window_eval, "source_scope_coordinates", return_value=expected):
            result = evaluator.evaluate_rows(
                gold, window, ranked, blocks, FakeTokenizer(), metas=[object()]
            )
        self.assertEqual(
            result["rows"][0]["stages"]["source_lineage_scope_72h"]["coordinates"],
            [["roll", 1]],
        )

    def test_local_tokenizer_is_required_and_no_network_fallback_exists(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileNotFoundError):
                evaluator.load_tokenizer(Path(directory) / "missing-tokenizer.json")

    def test_evidence_ref_mismatch_fails_closed(self):
        gold, window, ranked, _ = fixture()
        ranked["rows"][0]["evidence_turns"] = [["other", 99]]
        with self.assertRaisesRegex(ValueError, "Evidence-ref coordinates mismatch"):
            evaluator.validate_artifacts(gold, window, ranked)

    def test_causal_cutoff_and_duplicate_spans_count_messages_once(self):
        gold, window, ranked, blocks = fixture()
        result = evaluator.evaluate_rows(gold, window, ranked, blocks, FakeTokenizer())
        stages = result["rows"][0]["stages"]
        self.assertEqual(stages["full_originating_rollout"]["message_count"], 4)
        self.assertEqual(stages["causal_originating_rollout"]["message_count"], 2)
        self.assertEqual(stages["lexical_top_3"]["coordinates"], [["roll", 1]])
        self.assertEqual(stages["lexical_top_3"]["message_count"], 2)
        self.assertEqual(stages["minimal_useful_content"]["message_count"], 2)
        self.assertEqual(stages["minimal_useful_content"]["method"], "cited_evidence_turns_approximation")

    def test_adjudicated_minimal_useful_ordinals_count_only_referenced_messages(self):
        gold, window, ranked, blocks = fixture()
        gold[0]["adjudication"]["minimal_useful_refs"] = [
            {"rollout_id": "roll", "ordinals": [1]},
        ]
        result = evaluator.evaluate_rows(gold, window, ranked, blocks, FakeTokenizer())
        useful = result["rows"][0]["stages"]["minimal_useful_content"]
        self.assertEqual(useful["method"], "adjudicated_message_ordinals")
        self.assertEqual(useful["message_count"], 1)
        self.assertEqual(useful["coordinates"], [["roll", 1]])

    def test_serialized_report_contains_coordinates_and_counts_only(self):
        gold, window, ranked, blocks = fixture()
        result = evaluator.evaluate_rows(gold, window, ranked, blocks, FakeTokenizer())
        serialized = json.dumps(result)
        self.assertNotIn("PRIVATE_SENTINEL", serialized)
        self.assertNotIn("future message", serialized)
        self.assertIn("billing_caveat", result["metadata"])
        self.assertFalse(result["metadata"]["full_parent_child_lineage_available"])
        self.assertEqual(
            result["metadata"]["source_lineage_scope_artifact_parity"],
            {"rows_checked": 0, "rows_matching": 0},
        )

    def test_tokenizer_fingerprint_does_not_expose_local_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            tokenizer_path = Path(directory) / "tokenizer.json"
            tokenizer_path.write_text("local test tokenizer", encoding="utf-8")
            result = {"metadata": {}}
            evaluator.attach_tokenizer_fingerprint(result, tokenizer_path)
            serialized = json.dumps(result)
        self.assertNotIn(directory, serialized)
        self.assertNotIn("tokenizer_path", serialized)
        self.assertNotIn("repository", serialized)
        self.assertEqual(result["metadata"]["tokenizer_label"], "local tokenizer.json")


if __name__ == "__main__":
    unittest.main()

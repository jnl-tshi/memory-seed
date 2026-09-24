from __future__ import annotations

import copy
import unittest
from dataclasses import dataclass

import assemble_extended_gold as assembly


@dataclass
class Item:
    source_ordinal: int
    timestamp: str
    turn_number: int
    role: str


@dataclass
class Session:
    rollout_id: str


@dataclass
class Block:
    session: Session
    turn_number: int
    items: list[Item]
    reasoning_summary_items: list[Item]


def fixture():
    sample_id = "entry:d1"
    split = {"development": {"decision_ids": [sample_id]}, "sealed_final": {"decision_ids": []}}
    alignments = {"metadata": {"sample_ids_sha256": "cohort-hash", "sample_seed": 7}, "alignments": [{
        "decision": {"decision_id": sample_id, "title": "Choose cache", "decision_timestamp": "2026-09-24T12:00:00Z", "source_path": "record.md", "start_line": 1, "end_line": 5},
        "best_candidate": {"rollout_id": "roll", "session_id": "task", "winning_turn": 2, "turn_id": "t2", "turn_start_timestamp": "2026-09-24T11:58:00Z", "turn_end_timestamp": None, "source_path": "source.jsonl", "window": {"turn_start": 1, "turn_end": 3}},
        "confidence": "Medium", "appears_unique": False,
    }]}
    ref = {"rollout_id": "roll", "turn": 1, "ordinals": [3], "timestamps": ["2026-09-24T11:57:00Z"], "actors": ["user"]}
    review = {"label": "verified_source", "evidence_refs": [ref], "minimal_useful_refs": [{"rollout_id": "roll", "ordinals": [3]}], "evidence_shape": "one_turn", "source_role": "user", "coverage": "complete", "selected_candidate_describes_decision": False, "rationale": "Choice is explicit in the prior turn."}
    packet_a = {"verifier": "A", "reviews": [{"decision_id": sample_id, "review": copy.deepcopy(review)}]}
    packet_b = {"verifier": "B", "reviews": [{"decision_id": sample_id, "review": copy.deepcopy(review)}]}
    adjudication = {"reviews": [{"decision_id": sample_id, "final_adjudication": copy.deepcopy(review)}]}
    blocks = {"roll": [Block(Session("roll"), 1, [Item(3, "2026-09-24T11:57:00Z", 1, "user")], [])]}
    return split, alignments, packet_a, packet_b, adjudication, blocks


class ExtendedGoldTests(unittest.TestCase):
    def test_assembles_only_reviewed_provenance_with_separate_reviews(self):
        values = fixture()
        rows = assembly.assemble(*values, split_name="development")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["adjudication"]["label"], "verified_source")
        self.assertEqual(rows[0]["verifier_a_review"]["label"], "verified_source")
        self.assertEqual(rows[0]["selected_candidate"]["window_contains_all_cited_evidence"], True)
        self.assertEqual(rows[0]["cohort"]["sample_ids_sha256"], "cohort-hash")

    def test_missing_review_fails_closed(self):
        values = list(fixture())
        values[3]["reviews"][0]["review"]["label"] = None
        with self.assertRaisesRegex(ValueError, "incomplete"):
            assembly.assemble(*values, split_name="development")

    def test_fabricated_source_ordinal_fails_closed(self):
        values = list(fixture())
        values[4]["reviews"][0]["final_adjudication"]["evidence_refs"][0]["ordinals"] = [999]
        with self.assertRaisesRegex(ValueError, "source ordinal"):
            assembly.assemble(*values, split_name="development")

    def test_later_message_fails_causal_gate(self):
        values = list(fixture())
        values[5]["roll"][0].items[0].timestamp = "2026-09-24T12:02:00Z"
        values[4]["reviews"][0]["final_adjudication"]["evidence_refs"][0]["timestamps"] = ["2026-09-24T12:02:00Z"]
        with self.assertRaisesRegex(ValueError, "causal"):
            assembly.assemble(*values, split_name="development")

    def test_extra_or_missing_ids_fail_closed(self):
        values = list(fixture())
        values[2]["reviews"].append(copy.deepcopy(values[2]["reviews"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            assembly.assemble(*values, split_name="development")


if __name__ == "__main__":
    unittest.main()

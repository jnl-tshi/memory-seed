from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("adjudicate_extended_reviews", BASE / "adjudicate_extended_reviews.py")
assert SPEC and SPEC.loader
adjudicate = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = adjudicate
SPEC.loader.exec_module(adjudicate)


class AdjudicationDraftTests(unittest.TestCase):
    def test_only_explicit_selections_become_final(self) -> None:
        packet_a = {"reviews": [self._row("one", "verified_source"), self._row("two", None)]}
        packet_b = {"reviews": [self._row("one", "unresolved"), self._row("two", None)]}
        selections = {"one": {"use_review": "A", "reason": "Independent check of implementation evidence", "selected_candidate_describes_decision": True}}
        result = adjudicate.build_draft(packet_a, packet_b, selections)
        self.assertEqual(result["reviews"][0]["final_adjudication"]["label"], "verified_source")
        self.assertIsNone(result["reviews"][1]["final_adjudication"]["label"])
        self.assertEqual(result["reviews"][0]["verifier_b_review"]["label"], "unresolved")

    def test_selection_must_name_one_original_review(self) -> None:
        packet = {"reviews": [self._row("one", "verified_source")]}
        with self.assertRaisesRegex(ValueError, "use_review"):
            adjudicate.build_draft(packet, packet, {"one": {"use_review": "C", "reason": "x"}})

    def test_adjudicator_can_mark_verified_alternative_source_to_wrong_candidate(self) -> None:
        packet_a = {"reviews": [self._row("one", "wrong_candidate")]}
        packet_b = {"reviews": [self._row("one", "unresolved")]}
        selected = {"one": {"use_review": "A", "reason": "Direct alternative source checked",
                            "selected_candidate_describes_decision": False,
                            "adjudicated_label": "verified_source"}}
        result = adjudicate.build_draft(packet_a, packet_b, selected)
        final = result["reviews"][0]["final_adjudication"]
        self.assertEqual(final["label"], "verified_source")
        self.assertEqual(final["reviewer_label"], "wrong_candidate")
        self.assertFalse(final["selected_candidate_describes_decision"])
        self.assertEqual(result["reviews"][0]["verifier_a_review"]["label"], "wrong_candidate")

    def test_label_override_requires_wrong_candidate_with_alternative_evidence(self) -> None:
        packet = {"reviews": [self._row("one", "unresolved")]}
        with self.assertRaisesRegex(ValueError, "verified alternative"):
            adjudicate.build_draft(packet, packet, {"one": {"use_review": "A", "reason": "x",
                "selected_candidate_describes_decision": False, "adjudicated_label": "verified_source"}})

    @staticmethod
    def _row(decision_id: str, label: str | None) -> dict:
        return {"decision_id": decision_id, "review": {
            "label": label, "evidence_refs": [{"rollout_id": "r", "turn": 1, "source_ordinal": 1}] if label else [],
            "minimal_useful_refs": [], "rationale": "Reason" if label else None,
        }}


if __name__ == "__main__":
    unittest.main()

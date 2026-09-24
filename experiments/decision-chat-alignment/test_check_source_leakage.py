from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("check_source_leakage", BASE / "check_source_leakage.py")
assert SPEC and SPEC.loader
leakage = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = leakage
SPEC.loader.exec_module(leakage)


class SourceLeakageTests(unittest.TestCase):
    def test_parent_and_child_are_same_group(self) -> None:
        metas = {
            "parent-rollout": SimpleNamespace(session_id="parent", parent_thread_id=None),
            "child-rollout": SimpleNamespace(session_id="child", parent_thread_id="parent"),
        }
        self.assertEqual(leakage.root_group("child-rollout", metas), "parent")

    def test_unresolved_rows_do_not_invent_source_group(self) -> None:
        row = {"adjudication": {"label": "unresolved", "evidence_refs": []}}
        self.assertEqual(leakage.source_groups(row, {}), set())

    def test_actual_source_overlap_detected_even_when_candidate_split_disjoint(self) -> None:
        metas = {
            "a": SimpleNamespace(session_id="same", parent_thread_id=None),
            "b": SimpleNamespace(session_id="child", parent_thread_id="same"),
        }
        dev = [{"decision": {"id": "dev:d1"}, "adjudication": {"label": "verified_source", "evidence_refs": [{"rollout_id": "a", "turn": 1}]}}]
        final = [{"decision": {"id": "held:d1"}, "adjudication": {"label": "verified_source", "evidence_refs": [{"rollout_id": "b", "turn": 1}]}}]
        result = leakage.overlap(dev, final, metas)
        self.assertEqual(result["overlapping_source_groups"], 1)
        self.assertFalse(result["source_group_disjoint"])

    def test_overlap_names_affected_decisions_and_comparison_set(self) -> None:
        metas = {
            "known": SimpleNamespace(session_id="shared", parent_thread_id=None),
            "held": SimpleNamespace(session_id="child", parent_thread_id="shared"),
        }
        known = [{"decision": {"id": "known:d1"}, "adjudication": {
            "label": "verified_source", "evidence_refs": [{"rollout_id": "known", "turn": 1}]}}]
        final = [{"decision": {"id": "held:d1"}, "adjudication": {
            "label": "verified_source", "evidence_refs": [{"rollout_id": "held", "turn": 2}]}}]
        result = leakage.overlap([], final, metas, known)
        self.assertEqual(result["affected_held_out_decision_ids"], ["held:d1"])
        self.assertEqual(result["overlap_with_known_group_count"], 1)
        self.assertEqual(result["overlap_with_development_group_count"], 0)


if __name__ == "__main__":
    unittest.main()

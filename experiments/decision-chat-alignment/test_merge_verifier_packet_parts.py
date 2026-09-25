from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("merge_verifier_packet_parts", BASE / "merge_verifier_packet_parts.py")
assert SPEC and SPEC.loader
merge = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = merge
SPEC.loader.exec_module(merge)


class MergePartsTests(unittest.TestCase):
    @staticmethod
    def packet(a: str | None, b: str | None) -> dict:
        return {"verifier": "A", "cohort_ids_sha256": "same", "reviews": [
            {"decision_id": "a", "review": {"label": a}},
            {"decision_id": "b", "review": {"label": b}},
        ]}

    def test_only_nonoverlapping_completed_rows_merge(self) -> None:
        result = merge.merge_parts(self.packet("verified_source", None), self.packet(None, "unresolved"))
        self.assertEqual([row["review"]["label"] for row in result["reviews"]], ["verified_source", "unresolved"])

    def test_overlapping_completed_rows_fail(self) -> None:
        with self.assertRaisesRegex(ValueError, "overlap"):
            merge.merge_parts(self.packet("verified_source", None), self.packet("unresolved", None))

    def test_cohort_drift_fails(self) -> None:
        tail = self.packet(None, "unresolved")
        tail["cohort_ids_sha256"] = "other"
        with self.assertRaisesRegex(ValueError, "cohort"):
            merge.merge_parts(self.packet("verified_source", None), tail)


if __name__ == "__main__":
    unittest.main()

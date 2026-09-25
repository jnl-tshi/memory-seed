from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


BASE = Path(__file__).resolve().parent
MODULE_PATH = BASE / "assemble_gold_set.py"
SPEC = importlib.util.spec_from_file_location("assemble_gold_set", MODULE_PATH)
assert SPEC and SPEC.loader
gold = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gold
SPEC.loader.exec_module(gold)


class GoldSetAssemblyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.alignments = json.loads(
            (BASE / "results-codex-causal-minute-fixed" / "alignments.json").read_text(
                encoding="utf-8"
            )
        )
        cls.audit_rows = gold.read_jsonl_parts(BASE / "gold-parts")

    def test_fixed_cohort_assembles_fifty_rows(self) -> None:
        rows = gold.validated_gold_rows(self.alignments, self.audit_rows)
        self.assertEqual(len(rows), 50)
        self.assertEqual(len({row["decision"]["id"] for row in rows}), 50)

    def test_candidate_identity_drift_fails_closed(self) -> None:
        corrupted = copy.deepcopy(self.audit_rows)
        first_id = self.alignments["metadata"]["sample_ids"][0]
        corrupted[first_id]["selected_candidate"]["turn"] += 1
        with self.assertRaisesRegex(RuntimeError, "audited candidate"):
            gold.validated_gold_rows(self.alignments, corrupted)

    def test_missing_audit_row_fails_closed(self) -> None:
        incomplete = copy.deepcopy(self.audit_rows)
        incomplete.pop(self.alignments["metadata"]["sample_ids"][0])
        with self.assertRaisesRegex(RuntimeError, "gold cohort mismatch"):
            gold.validated_gold_rows(self.alignments, incomplete)

    def test_untraversed_evidence_rollout_fails_closed(self) -> None:
        corrupted = copy.deepcopy(self.audit_rows)
        first_id = self.alignments["metadata"]["sample_ids"][0]
        corrupted[first_id]["adjudication"]["evidence_refs"][0]["rollout_id"] = (
            "00000000-0000-0000-0000-000000000000"
        )
        with self.assertRaisesRegex(RuntimeError, "evidence rollout was not selected or traversed"):
            gold.validated_gold_rows(self.alignments, corrupted)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import importlib.util
import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("prepare_extended_cohort.py")
SPEC = importlib.util.spec_from_file_location("prepare_extended_cohort", MODULE_PATH)
assert SPEC and SPEC.loader
cohort = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cohort
SPEC.loader.exec_module(cohort)


@dataclass
class Record:
    decision_id: str


class CohortTests(unittest.TestCase):
    def test_seeded_unseen_sample_is_order_independent_and_excludes_known(self) -> None:
        records = [Record(str(index)) for index in range(15)]
        first = cohort.choose_unseen(records, {"0", "1"}, 5, 17)
        second = cohort.choose_unseen(list(reversed(records)), {"0", "1"}, 5, 17)
        self.assertEqual([row.decision_id for row in first], [row.decision_id for row in second])
        self.assertFalse({row.decision_id for row in first} & {"0", "1"})

    def test_insufficient_and_duplicate_population_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "only 1 eligible"):
            cohort.choose_unseen([Record("a"), Record("b")], {"a"}, 2, 1)
        with self.assertRaisesRegex(RuntimeError, "not unique"):
            cohort.choose_unseen([Record("a"), Record("a")], set(), 1, 1)


if __name__ == "__main__":
    unittest.main()

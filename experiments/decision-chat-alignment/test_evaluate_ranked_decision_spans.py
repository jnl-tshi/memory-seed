from __future__ import annotations

import importlib.util
import sys
import unittest
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("evaluate_ranked_decision_spans", BASE / "evaluate_ranked_decision_spans.py")
assert SPEC and SPEC.loader
ranking = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ranking
SPEC.loader.exec_module(ranking)


@dataclass
class Item:
    timestamp: str
    role: str
    text: str


@dataclass
class Session:
    session_id: str
    rollout_id: str


@dataclass
class Block:
    session: Session
    turn_number: int
    start_utc: datetime
    items: list[Item]
    collaboration_mode: str | None = None
    reasoning_summary_items: list[Item] | None = None

    def __post_init__(self) -> None:
        if self.reasoning_summary_items is None:
            self.reasoning_summary_items = []


class RankedSpanTests(unittest.TestCase):
    def test_future_text_in_long_turn_is_not_scored(self) -> None:
        cutoff = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)
        block = Block(Session("task", "rollout"), 1, cutoff, [
            Item("2026-09-24T12:00:05Z", "assistant", "We need to inspect the code."),
            Item("2026-09-24T12:01:00Z", "assistant", "Choose the perfect architecture."),
        ])
        self.assertNotIn("perfect architecture", ranking.block_text(block, cutoff))

    def test_next_user_after_tools_is_only_soft_bonus(self) -> None:
        cutoff = datetime(2026, 9, 24, 13, 0, tzinfo=timezone.utc)
        blocks = [
            Block(Session("task", "rollout"), 1, datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc), [
                Item("2026-09-24T12:00:01Z", "tool", "test a"),
                Item("2026-09-24T12:00:02Z", "tool", "test b"),
                Item("2026-09-24T12:00:03Z", "tool", "test c"),
            ]),
            Block(Session("task", "rollout"), 2, datetime(2026, 9, 24, 12, 5, tzinfo=timezone.utc), [
                Item("2026-09-24T12:05:00Z", "user", "Choose local storage."),
            ]),
        ]
        lexical = ranking.rank_spans(blocks, "Choose local storage", None, cutoff, width=1, variant="lexical")
        phase = ranking.rank_spans(blocks, "Choose local storage", None, cutoff, width=1, variant="boundary")
        self.assertEqual(lexical[0]["coordinates"], {("rollout", 2)})
        self.assertEqual(phase[0]["coordinates"], {("rollout", 2)})
        self.assertGreater(phase[0]["score"], lexical[0]["score"])

    def test_short_ranker_does_not_require_gold_coordinates(self) -> None:
        cutoff = datetime(2026, 9, 24, 13, 0, tzinfo=timezone.utc)
        block = Block(Session("task", "rollout"), 1, datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc), [
            Item("2026-09-24T12:00:00Z", "assistant", "Prefer the local classifier."),
        ])
        self.assertEqual(ranking.select_top(ranking.rank_spans([block], "Local classifier", None, cutoff), 1), {("rollout", 1)})


if __name__ == "__main__":
    unittest.main()

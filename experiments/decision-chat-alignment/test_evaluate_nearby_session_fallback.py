from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace


BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("evaluate_nearby_session_fallback", BASE / "evaluate_nearby_session_fallback.py")
assert SPEC and SPEC.loader
fallback = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = fallback
SPEC.loader.exec_module(fallback)


class NearbySessionFallbackTests(unittest.TestCase):
    @staticmethod
    def block(rollout: str, session: str, turn: int, hour: int) -> SimpleNamespace:
        return SimpleNamespace(
            session=SimpleNamespace(rollout_id=rollout, session_id=session),
            turn_number=turn,
            start_utc=datetime(2026, 9, 9, hour, tzinfo=timezone.utc),
        )

    def test_recent_groups_use_turn_activity_not_session_start(self) -> None:
        blocks = {
            "old-start-active": [self.block("old-start-active", "old", 1, 14)],
            "new-start-idle": [self.block("new-start-idle", "new", 1, 12)],
        }
        coords = {("old-start-active", 1), ("new-start-idle", 1)}
        groups = fallback.rank_session_groups(coords, blocks)
        self.assertEqual([group[0] for group in groups], ["old", "new"])

    def test_selected_group_is_preserved_but_neighbor_can_add_other_rollout(self) -> None:
        blocks = {
            "candidate": [self.block("candidate", "chosen", 1, 12)],
            "voice": [self.block("voice", "earlier", 5, 13)],
        }
        coords = {("candidate", 1), ("voice", 5)}
        groups = fallback.rank_session_groups(coords, blocks)
        selected = fallback.select_coordinates(groups, selected_session="chosen", count=1)
        self.assertEqual(selected, coords)

    def test_selection_does_not_invent_missing_group(self) -> None:
        blocks = {"r": [self.block("r", "one", 1, 13)]}
        groups = fallback.rank_session_groups({("r", 1)}, blocks)
        self.assertEqual(fallback.select_coordinates(groups, selected_session="missing", count=1), {("r", 1)})

    def test_text_rank_can_raise_older_relevant_session(self) -> None:
        older = self.block("older", "relevant", 1, 12)
        older.items = [SimpleNamespace(role="assistant", text="Retrieval Specification becomes a first-class object", timestamp="2026-09-09T12:01:00Z")]
        older.reasoning_summary_items = []
        newer = self.block("newer", "other", 1, 14)
        newer.items = [SimpleNamespace(role="assistant", text="Unrelated activity", timestamp="2026-09-09T14:01:00Z")]
        newer.reasoning_summary_items = []
        blocks = {"older": [older], "newer": [newer]}
        groups = fallback.rank_session_groups({("older", 1), ("newer", 1)}, blocks)
        ordered = fallback.rank_groups_by_text(groups, blocks, "Retrieval Specification", datetime(2026, 9, 9, 15, tzinfo=timezone.utc))
        self.assertEqual(ordered[0][0], "relevant")


if __name__ == "__main__":
    unittest.main()

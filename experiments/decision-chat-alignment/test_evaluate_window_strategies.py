from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(__file__).resolve().parent


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, BASE / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


alignment = load_module("decision_alignment_for_window_eval", "align_decisions.py")
window_eval = load_module("evaluate_window_strategies", "evaluate_window_strategies.py")


class WindowStrategyTests(unittest.TestCase):
    def test_read_gold_accepts_a_unique_development_subset(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gold.jsonl"
            path.write_text("\n".join(json.dumps({"decision": {"id": item}}) for item in ("a", "b")), encoding="utf-8")
            self.assertEqual(len(window_eval.read_gold(path)), 2)

    def test_read_gold_rejects_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gold.jsonl"
            path.write_text("\n".join(json.dumps({"decision": {"id": "a"}}) for _ in range(2)), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unique"):
                window_eval.read_gold(path)

    def test_fixed_window_matches_existing_radius_two_contract(self) -> None:
        blocks = self._blocks(self._meta("child", "child-task"), range(1, 9))
        coordinates = window_eval.fixed_window_coordinates(blocks, winning_turn=5, radius=2)
        self.assertEqual(
            coordinates,
            {("child", turn) for turn in range(3, 8)},
        )

    def test_adaptive_window_reaches_nearest_plan_across_continuations(self) -> None:
        first = self._meta("first", "task")
        second = self._meta("second", "task")
        blocks_by_rollout = {
            "first": self._blocks(first, range(1, 4), plan_turns={2}, hour=9),
            "second": self._blocks(second, range(1, 5), hour=10),
        }
        result = window_eval.adaptive_task_coordinates(
            task_id="task",
            anchor_rollout_id="second",
            anchor_turn=3,
            cutoff=datetime(2026, 9, 24, 11, tzinfo=timezone.utc),
            metas=[first, second],
            blocks_by_rollout=blocks_by_rollout,
            plan_lookback=12,
            fallback_lookback=5,
            forward_turns=1,
        )
        self.assertIn(("first", 2), result)
        self.assertIn(("second", 3), result)
        self.assertIn(("second", 4), result)
        self.assertNotIn(("first", 1), result)

    def test_lineage_strategy_adds_parent_context_before_child_creation(self) -> None:
        parent = self._meta("parent", "parent-task")
        child = self._meta(
            "child",
            "child-task",
            parent_thread_id="parent-task",
            stamp="2026-09-24T10:22:00Z",
        )
        blocks_by_rollout = {
            "parent": self._blocks(parent, range(1, 7), plan_turns={4}, hour=10),
            "child": self._blocks(child, range(1, 4), hour=11),
        }
        result = window_eval.lineage_adaptive_coordinates(
            selected_rollout_id="child",
            anchor_turn=2,
            decision_time=datetime(2026, 9, 24, 12, tzinfo=timezone.utc),
            metas=[parent, child],
            blocks_by_rollout=blocks_by_rollout,
            plan_lookback=12,
            fallback_lookback=5,
            forward_turns=1,
            max_depth=2,
        )
        self.assertIn(("child", 2), result)
        self.assertIn(("parent", 4), result)
        self.assertNotIn(("parent", 6), result)

    def test_summary_reports_gold_coverage_and_turn_reduction(self) -> None:
        rows = [
            {
                "decision_id": "one",
                "gold_label": "verified_source",
                "evidence": {("a", 2)},
                "universe": {("a", 1), ("a", 2), ("a", 3), ("b", 1)},
                "source_scope": {("a", 1), ("a", 2), ("a", 3)},
                "strategies": {
                    "small": {("a", 2)},
                    "miss": {("a", 1)},
                },
            },
            {
                "decision_id": "two",
                "gold_label": "partial_multi_turn",
                "evidence": {("c", 1), ("c", 2)},
                "universe": {("c", 1), ("c", 2)},
                "source_scope": {("c", 1), ("c", 2)},
                "strategies": {
                    "small": {("c", 1)},
                    "miss": set(),
                },
            },
        ]
        summary = window_eval.summarize_results(rows)
        self.assertEqual(summary["small"]["all_evidence_rows"], 1)
        self.assertEqual(summary["small"]["any_evidence_rows"], 2)
        self.assertEqual(summary["small"]["verified_all_evidence_rows"], 1)
        self.assertEqual(summary["small"]["retained_turns"], 2)
        self.assertEqual(summary["small"]["search_universe_turns"], 6)
        self.assertAlmostEqual(summary["small"]["search_turn_reduction"], 2 / 3)

    def test_serialized_source_scope_preserves_coordinates_for_staged_fallback(self) -> None:
        row = {
            "decision_id": "d", "gold_label": "verified_source",
            "evidence": {("r", 2)}, "universe": {("r", 1), ("r", 2)},
            "source_scope": {("r", 1), ("r", 2)},
            "strategies": {"lineage_backward_20": {("r", 2)}},
        }
        serial = window_eval.serializable_row(row)
        self.assertEqual(serial["source_scope_turns"], 2)
        self.assertEqual(serial["source_scope_coordinates"], [["r", 1], ["r", 2]])

    @staticmethod
    def _meta(
        rollout_id: str,
        task_id: str,
        *,
        parent_thread_id: str | None = None,
        stamp: str = "2026-09-24T09:00:00Z",
    ):
        parsed = alignment.parse_iso_timestamp(stamp)
        assert parsed
        return alignment.SessionMeta(
            rollout_id=rollout_id,
            session_id=task_id,
            legacy_session_id=None,
            timestamp=parsed.isoformat(),
            timestamp_utc=parsed,
            cwd="C:/repo",
            source_path=f"{rollout_id}.jsonl",
            originator="Codex Desktop",
            source="vscode",
            cli_version="x",
            repository_url=None,
            git_branch="main",
            git_commit="abc",
            thread_source="user",
            parent_thread_id=parent_thread_id,
            agent_nickname=None,
            agent_path=None,
            agent_depth=1 if parent_thread_id else 0,
        )

    @staticmethod
    def _blocks(meta, turns, *, plan_turns=frozenset(), hour=10):
        output = []
        for index, turn in enumerate(turns):
            minute = index * 5
            output.append(
                alignment.TurnBlock(
                    meta,
                    turn,
                    f"turn-{turn}",
                    start_timestamp=f"2026-09-24T{hour:02d}:{minute:02d}:00Z",
                    end_timestamp=f"2026-09-24T{hour:02d}:{minute + 4:02d}:00Z",
                    collaboration_mode="plan" if turn in plan_turns else "default",
                )
            )
        return output


if __name__ == "__main__":
    unittest.main()

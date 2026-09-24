from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


BASE = Path(__file__).resolve().parent
MODULE_PATH = BASE / "evaluate_origin_phase_hypotheses.py"
SPEC = importlib.util.spec_from_file_location("evaluate_origin_phase_hypotheses", MODULE_PATH)
assert SPEC and SPEC.loader
phase = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = phase
SPEC.loader.exec_module(phase)


class OriginPhaseHypothesisTests(unittest.TestCase):
    def test_reads_decision_specific_origin(self) -> None:
        text = """## 2026-09-24 10:00 - Example

```yaml
entry_id: mse_example
decision_origins:
  d1: user
  d2: agent
```

### Records
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.md"
            path.write_text(text, encoding="utf-8")
            self.assertEqual(phase.read_explicit_origin(path, "mse_example", "d2"), "agent")

    def test_missing_origin_is_unknown_not_inferred(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "session.md"
            path.write_text("entry_id: mse_example\n", encoding="utf-8")
            self.assertIsNone(phase.read_explicit_origin(path, "mse_example", "d1"))

    def test_phase_tags_can_overlap(self) -> None:
        tags = phase.phase_tags(
            source_role="root_discussion_and_implementation",
            evidence_shape="multi_turn_with_review_refinement",
            actors={"user", "assistant_review_finding", "exec/apply_patch"},
        )
        self.assertEqual(tags, {"discussion", "implementation", "review"})

    def test_reviewer_signals_do_not_require_name(self) -> None:
        signals = phase.reviewer_signals(
            agent_nickname="worker-7",
            agent_path="/root/task_7",
            is_child=True,
            first_user_text="Review this diff for spec compliance and report findings.",
            assistant_text="Verdict: approved. No important findings.",
        )
        self.assertFalse(signals["name_signal"])
        self.assertTrue(signals["prompt_signal"])
        self.assertTrue(signals["output_signal"])
        self.assertTrue(signals["any_signal"])

    def test_root_session_prompt_does_not_label_every_later_turn_as_review(self) -> None:
        signals = phase.reviewer_signals(
            agent_nickname=None,
            agent_path="/root",
            is_child=False,
            first_user_text="Review the initial proposal.",
            assistant_text="Implementation completed and tests passed.",
        )
        self.assertFalse(signals["prompt_signal"])
        self.assertFalse(signals["any_signal"])

    def test_actual_source_timestamp_overrides_bad_gold_timestamp(self) -> None:
        row = {
            "adjudication": {
                "evidence_refs": [{
                    "rollout_id": "rollout-1",
                    "ordinal": 7,
                    "timestamp": "2026-09-09T12:00:00Z",
                }]
            }
        }
        actual = {("rollout-1", 7): datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)}
        self.assertEqual(phase.evidence_timestamps(row, actual), [actual[("rollout-1", 7)]])


if __name__ == "__main__":
    unittest.main()

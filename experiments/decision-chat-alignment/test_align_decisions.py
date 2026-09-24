from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("align_decisions.py")
SPEC = importlib.util.spec_from_file_location("decision_chat_alignment", MODULE_PATH)
assert SPEC and SPEC.loader
alignment = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = alignment
SPEC.loader.exec_module(alignment)


class AlignmentTests(unittest.TestCase):
    def test_parse_rollout_normalizes_messages_turns_and_tool_calls(self) -> None:
        rows = [
            {
                "timestamp": "2026-09-24T01:00:00Z",
                "ordinal": 0,
                "type": "session_meta",
                "payload": {"id": "session-1", "timestamp": "2026-09-24T01:00:00Z", "cwd": "C:/repo"},
            },
            {
                "timestamp": "2026-09-24T01:00:01Z",
                "ordinal": 1,
                "type": "event_msg",
                "payload": {
                    "type": "task_started",
                    "turn_id": "turn-1",
                    "collaboration_mode_kind": "plan",
                },
            },
            {
                "timestamp": "2026-09-24T01:00:02Z",
                "ordinal": 2,
                "type": "response_item",
                "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Choose SQLite."}]},
            },
            {
                "timestamp": "2026-09-24T01:00:03Z",
                "ordinal": 3,
                "type": "response_item",
                "payload": {"type": "custom_tool_call", "name": "exec", "input": "pytest tests/test_db.py"},
            },
            {
                "timestamp": "2026-09-24T01:00:04Z",
                "ordinal": 4,
                "type": "response_item",
                "payload": {
                    "type": "reasoning",
                    "summary": [
                        {"type": "summary_text", "text": "Prefer SQLite for the local store."}
                    ],
                    "encrypted_content": "must-not-leak",
                },
            },
            {
                "timestamp": "2026-09-24T01:00:05Z",
                "ordinal": 5,
                "type": "response_item",
                "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "SQLite was selected."}]},
            },
            {
                "timestamp": "2026-09-24T01:05:00Z",
                "ordinal": 6,
                "type": "event_msg",
                "payload": {
                    "type": "task_started",
                    "turn_id": "turn-2",
                    "collaboration_mode_kind": "default",
                },
            },
            {
                "timestamp": "2026-09-24T01:05:01Z",
                "ordinal": 7,
                "type": "response_item",
                "payload": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Continue."}]},
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollout.jsonl"
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            meta = alignment.read_session_meta(path)
            self.assertIsNotNone(meta)
            blocks = alignment.parse_rollout(path, meta)
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0].turn_number, 1)
        self.assertEqual([item.role for item in blocks[0].items], ["user", "tool", "assistant"])
        self.assertIn("SQLite was selected", blocks[0].text)
        self.assertNotIn("Prefer SQLite", blocks[0].text)
        self.assertNotIn("must-not-leak", blocks[0].reasoning_summary_text)
        self.assertEqual(blocks[0].reasoning_summary_text, "Prefer SQLite for the local store.")
        self.assertEqual(blocks[0].reasoning_summary_ordinals, [4])
        self.assertEqual(blocks[0].collaboration_mode, "plan")
        self.assertEqual(blocks[0].start_timestamp, "2026-09-24T01:00:01Z")
        self.assertEqual(blocks[0].end_timestamp, "2026-09-24T01:05:00Z")
        self.assertEqual(blocks[1].collaboration_mode, "default")

    def test_turn_context_can_supply_mode_and_final_turn_end(self) -> None:
        rows = [
            {
                "timestamp": "2026-09-24T02:00:00Z",
                "ordinal": 0,
                "type": "session_meta",
                "payload": {"id": "session-1", "timestamp": "2026-09-24T02:00:00Z", "cwd": "C:/repo"},
            },
            {
                "timestamp": "2026-09-24T02:00:01Z",
                "ordinal": 1,
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": "turn-1"},
            },
            {
                "timestamp": "2026-09-24T02:00:02Z",
                "ordinal": 2,
                "type": "turn_context",
                "payload": {"collaboration_mode": {"mode": "plan"}},
            },
            {
                "timestamp": "2026-09-24T02:00:09Z",
                "ordinal": 3,
                "type": "response_item",
                "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Done."}]},
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollout.jsonl"
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            meta = alignment.read_session_meta(path)
            self.assertIsNotNone(meta)
            block = alignment.parse_rollout(path, meta)[0]
        self.assertEqual(block.collaboration_mode, "plan")
        self.assertEqual(block.mode_source, "turn_context")
        self.assertEqual(block.end_timestamp, "2026-09-24T02:00:09Z")

    def test_parse_rollout_preserves_empty_turn_boundaries(self) -> None:
        rows = [
            {
                "timestamp": "2026-09-24T02:00:00Z",
                "ordinal": 0,
                "type": "session_meta",
                "payload": {"id": "session-1", "timestamp": "2026-09-24T02:00:00Z", "cwd": "C:/repo"},
            },
            {
                "timestamp": "2026-09-24T02:00:01Z",
                "ordinal": 1,
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": "turn-1"},
            },
            {
                "timestamp": "2026-09-24T02:05:00Z",
                "ordinal": 2,
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": "turn-2"},
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollout.jsonl"
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            meta = alignment.read_session_meta(path)
            self.assertIsNotNone(meta)
            blocks = alignment.parse_rollout(path, meta)
        self.assertEqual([block.turn_id for block in blocks], ["turn-1", "turn-2"])
        self.assertEqual(blocks[0].end_timestamp, "2026-09-24T02:05:00Z")

    def test_anchor_turn_uses_decision_minute_interval(self) -> None:
        meta = self._meta()
        blocks = [
            alignment.TurnBlock(meta, 1, "one", "2026-09-24T12:00:00Z", "2026-09-24T13:00:00Z"),
            alignment.TurnBlock(meta, 2, "two", "2026-09-24T13:00:00Z", "2026-09-24T14:00:00Z"),
        ]
        decision_time = datetime(2026, 9, 24, 12, 59, 30, tzinfo=timezone.utc)
        self.assertIs(alignment.anchor_turn(blocks, decision_time), blocks[0])
        decision_time = datetime(2026, 9, 24, 13, 0, tzinfo=timezone.utc)
        self.assertIs(alignment.anchor_turn(blocks, decision_time), blocks[1])

    def test_summary_bonus_is_bounded_and_plan_requires_visible_support(self) -> None:
        summary = alignment.auxiliary_ranking_signals(
            collaboration_mode="plan",
            visible_supported=False,
            summary_cosine=1.0,
        )
        self.assertEqual(summary["plan_bonus"], 0.0)
        self.assertEqual(summary["reasoning_summary_bonus"], 0.06)
        self.assertEqual(summary["ranking_bonus"], 0.06)

    def test_private_window_never_serializes_reasoning_summary_text(self) -> None:
        meta = self._meta()
        block = alignment.TurnBlock(
            meta,
            1,
            "turn-1",
            "2026-09-24T01:00:00Z",
            "2026-09-24T01:01:00Z",
            reasoning_summaries=["secret internal summary"],
            reasoning_summary_ordinals=[9],
        )
        payload = json.dumps(alignment.private_window([block]))
        self.assertNotIn("secret internal summary", payload)

    def test_alignment_exports_turn_anchor_and_summary_provenance_without_text(self) -> None:
        meta = self._meta()
        block = alignment.TurnBlock(
            meta,
            1,
            "turn-1",
            "2026-09-24T00:00:00Z",
            "2026-09-24T01:00:00Z",
            collaboration_mode="plan",
            mode_source="task_started",
            items=[
                alignment.NormalizedItem(
                    "s", "2026-09-24T00:00:02Z", 1, "turn-1", "user",
                    "Choose the durable local store.", "rollout.jsonl", 2,
                )
            ],
            reasoning_summaries=["SQLite is the selected durable local store."],
            reasoning_summary_ordinals=[3],
            reasoning_summary_timestamps=["2026-09-24T00:00:03Z"],
        )
        decision = alignment.DecisionRecord(
            decision_id="mse_test:d1", entry_id="mse_test", ordinal="d1", title="Choose SQLite",
            text="Use SQLite as the durable local store.", entry_title=None, source_path="x.md",
            start_line=1, end_line=2, session_date="2026-09-24",
            decision_timestamp="2026-09-24T00:30:00+00:00", agent_type="codex",
            project_path=".", branch="main", commits=(), source_refs=(),
        )
        row = alignment.align([decision], [meta], {"s": [block]})[0]
        best = row["best_candidate"]
        self.assertEqual(best["anchor_turn"], 1)
        self.assertEqual(best["turn_start_timestamp"], "2026-09-24T00:00:00Z")
        self.assertTrue(best["signals"]["reasoning_summary_used"])
        self.assertEqual(best["reasoning_summary"]["source_ordinals"], [3])
        self.assertNotIn("SQLite is the selected", json.dumps(row))

    @staticmethod
    def _meta() -> alignment.SessionMeta:
        return alignment.SessionMeta(
            session_id="s",
            timestamp="2026-09-24T00:00:00+00:00",
            timestamp_utc=datetime(2026, 9, 24, tzinfo=timezone.utc),
            cwd="C:/repo",
            source_path="rollout.jsonl",
            originator="Codex Desktop",
            source="vscode",
            cli_version="x",
            repository_url=None,
            git_branch="main",
            git_commit="abc",
            thread_source="user",
            parent_thread_id=None,
            agent_nickname=None,
        )

    def test_sampling_is_reproducible_and_order_independent(self) -> None:
        records = [
            alignment.DecisionRecord(
                decision_id=f"mse_{index}:d1", entry_id=f"mse_{index}", ordinal="d1", title="T",
                text=f"Decision {index}", entry_title=None, source_path="x.md", start_line=1,
                end_line=2, session_date="2026-09-24", decision_timestamp="2026-09-24T00:00:00+00:00",
                agent_type="codex", project_path=".", branch=None, commits=(), source_refs=(),
            )
            for index in range(10)
        ]
        first = alignment.deterministic_sample(records, 5, 42)
        second = alignment.deterministic_sample(list(reversed(records)), 5, 42)
        self.assertEqual([row.decision_id for row in first], [row.decision_id for row in second])

    def test_codex_default_cohort_requires_expected_sample_hash(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "sample hash changed"):
            alignment.validate_sample_identity(
                decision_agent="codex",
                sample_size=50,
                seed=20260924,
                sample_hash="wrong",
            )

    def test_fixed_sample_ids_must_all_exist(self) -> None:
        record = alignment.DecisionRecord(
            decision_id="mse_one:d1", entry_id="mse_one", ordinal="d1", title="T", text="D",
            entry_title=None, source_path="x.md", start_line=1, end_line=2,
            session_date="2026-09-24", decision_timestamp="2026-09-24T00:00:00+00:00",
            agent_type="codex", project_path=".", branch=None, commits=(), source_refs=(),
        )
        with self.assertRaisesRegex(RuntimeError, "missing from the current corpus"):
            alignment.fixed_sample([record], ["mse_one:d1", "mse_missing:d1"])

    def test_agent_filter_limits_population_before_sampling(self) -> None:
        records = [
            alignment.DecisionRecord(
                decision_id=f"mse_{index}:d1", entry_id=f"mse_{index}", ordinal="d1", title="T",
                text=f"Decision {index}", entry_title=None, source_path="x.md", start_line=1,
                end_line=2, session_date="2026-09-24", decision_timestamp="2026-09-24T00:00:00+00:00",
                agent_type=agent, project_path=".", branch=None, commits=(), source_refs=(),
            )
            for index, agent in enumerate(("codex", "claude", "CoDeX", None))
        ]
        filtered = alignment.filter_decisions(records, "codex")
        self.assertEqual([row.decision_id for row in filtered], ["mse_0:d1", "mse_2:d1"])
        self.assertTrue(all((row.agent_type or "").casefold() == "codex" for row in filtered))

    def test_confidence_negative_control_abstains(self) -> None:
        weak = {
            "score": 0.08,
            "cosine": 0.0,
            "token_overlap": 0.0,
            "longest_shared_phrase_tokens": 0,
            "identifier_overlap": 0.0,
            "actor_compatible": True,
            "branch_match": False,
            "commit_match": False,
        }
        self.assertEqual(alignment.confidence_for(weak, 0.08), "No match")

    def test_repo_membership_accepts_matching_remote_for_external_worktree(self) -> None:
        meta = alignment.SessionMeta(
            session_id="s", timestamp="2026-09-24T00:00:00+00:00",
            timestamp_utc=datetime(2026, 9, 24, tzinfo=timezone.utc), cwd="C:/elsewhere/worktree",
            source_path="rollout.jsonl", originator="Codex Desktop", source="vscode", cli_version="x",
            repository_url="https://github.com/example/repo", git_branch="main", git_commit="abc",
            thread_source="user", parent_thread_id=None, agent_nickname=None,
        )
        self.assertTrue(
            alignment.session_belongs_to_repo(
                meta, (Path("C:/canonical/repo"),), "https://github.com/example/repo"
            )
        )

    def test_replayed_approval_transcript_is_detected(self) -> None:
        self.assertTrue(
            alignment.is_replayed_transcript(
                "The following is the Codex agent history whose request action you are assessing."
            )
        )

    def test_tool_payload_keeps_paths_but_drops_decision_ids(self) -> None:
        compact = alignment.compact_tool_text(
            "memory_session_append",
            "mse_deadbeef .memory-seed/sessions/2026-09/2026-09-24.md memory_seed/core.py",
        )
        self.assertIn("memory_seed/core.py", compact)
        self.assertNotIn("mse_deadbeef", compact)
        self.assertNotIn(".memory-seed/sessions", compact)

    def test_public_session_path_removes_user_profile_prefix(self) -> None:
        public = alignment.public_session_path(
            "C:/Users/example/.codex/sessions/2026/09/24/rollout.jsonl"
        )
        self.assertEqual(public, ".codex/sessions/2026/09/24/rollout.jsonl")
        self.assertNotIn("Users/example", public)


if __name__ == "__main__":
    unittest.main()

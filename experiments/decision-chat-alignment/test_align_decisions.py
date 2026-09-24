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
                "payload": {"type": "task_started", "turn_id": "turn-1"},
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
                "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "SQLite was selected."}]},
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollout.jsonl"
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
            meta = alignment.read_session_meta(path)
            self.assertIsNotNone(meta)
            blocks = alignment.parse_rollout(path, meta)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].turn_number, 1)
        self.assertEqual([item.role for item in blocks[0].items], ["user", "tool", "assistant"])
        self.assertIn("SQLite was selected", blocks[0].text)

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

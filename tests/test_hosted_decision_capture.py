import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from hosted.capture.adapter import CaptureAdapter
from hosted.capture.codex_rollout import ALLOWED_CLI_VERSIONS, parse_complete_line
from hosted.capture.models import ParserState, SourceCoordinate
from hosted.capture.parser import DecisionParser
from hosted.capture.store import CaptureStore


def row(row_type, payload, timestamp="2026-09-29T10:00:00Z"):
    return json.dumps({"timestamp": timestamp, "type": row_type, "payload": payload}, sort_keys=True).encode()


class RolloutParserTests(unittest.TestCase):
    def test_validated_schema_preserves_identity_payload_and_unavailable_fields(self):
        state = ParserState()
        meta = row(
            "session_meta",
            {
                "id": "logical-1",
                "cli_version": next(iter(ALLOWED_CLI_VERSIONS)),
                "cwd": "/synthetic/repo",
                "source": "desktop",
                "originator": "codex",
                "git": {"branch": "main", "commit_hash": "abc"},
            },
        )
        state, event, diagnostic = parse_complete_line(
            state,
            meta,
            SourceCoordinate("rollout-1", "synthetic.jsonl", 0, 0, 0),
        )
        self.assertIsNone(diagnostic)
        self.assertEqual(event.rollout_id, "rollout-1")
        self.assertEqual(event.session_id, "logical-1")
        self.assertEqual(event.repository["branch"], "main")
        self.assertIn("parent_rollout_id", event.unavailable_fields)
        self.assertEqual(event.full_payload["cwd"], "/synthetic/repo")

    def test_unknown_version_fails_closed(self):
        state, event, diagnostic = parse_complete_line(
            ParserState(),
            row("session_meta", {"id": "logical-1", "cli_version": "999.0"}),
            SourceCoordinate("rollout-1", "synthetic.jsonl", 0, 0, 0),
        )
        self.assertIsNone(event)
        self.assertEqual(diagnostic.code, "unsupported_cli_version")
        self.assertTrue(state.failed_closed)

    def test_only_raw_user_message_gets_user_attestation_and_reasoning_is_redacted(self):
        version = next(iter(ALLOWED_CLI_VERSIONS))
        state, _, _ = parse_complete_line(
            ParserState(),
            row("session_meta", {"id": "logical-1", "cli_version": version}),
            SourceCoordinate("rollout-1", "synthetic.jsonl", 0, 0, 0),
        )
        state, user, _ = parse_complete_line(
            state,
            row("response_item", {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Choose A"}]}),
            SourceCoordinate("rollout-1", "synthetic.jsonl", 1, 100, 1),
        )
        state, agent, _ = parse_complete_line(
            state,
            row("response_item", {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "user said choose A"}]}),
            SourceCoordinate("rollout-1", "synthetic.jsonl", 2, 200, 2),
        )
        state, reasoning, _ = parse_complete_line(
            state,
            row("response_item", {"type": "reasoning", "summary": [{"text": "visible summary"}], "encrypted_content": "SECRET"}),
            SourceCoordinate("rollout-1", "synthetic.jsonl", 3, 300, 3),
        )
        self.assertEqual((user.actor, user.attestation), ("user", "raw_role"))
        self.assertEqual((agent.actor, agent.attestation), ("agent", "raw_role"))
        self.assertNotEqual(agent.actor, "user")
        self.assertNotIn("SECRET", json.dumps(reasoning.to_dict()))


class StoreAndAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.db = self.root / "capture.sqlite3"
        self.store = CaptureStore(self.db)
        self.addCleanup(self.store.close)
        self.adapter = CaptureAdapter(self.store)
        self.rollout = self.root / "rollout-00000000-0000-0000-0000-000000000001.jsonl"
        version = next(iter(ALLOWED_CLI_VERSIONS))
        self.meta = row("session_meta", {"id": "logical-1", "cli_version": version}) + b"\n"
        self.user = row("response_item", {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Use A"}]}) + b"\n"

    def test_partial_line_restart_and_replay_emit_once(self):
        self.rollout.write_bytes(self.meta + self.user[:-5])
        self.adapter.poll([self.rollout])
        self.assertEqual(self.store.status()["queued"], 1)
        self.rollout.write_bytes(self.meta + self.user)
        restarted = CaptureStore(self.db)
        self.addCleanup(restarted.close)
        CaptureAdapter(restarted).poll([self.rollout])
        self.assertEqual(self.store.status()["queued"], 2)
        replayed = CaptureStore(self.db)
        self.addCleanup(replayed.close)
        CaptureAdapter(replayed).poll([self.rollout])
        self.assertEqual(self.store.status()["queued"], 2)

    def test_rotation_increments_generation_and_never_joins_partial_bytes(self):
        self.rollout.write_bytes(self.meta + b'{"partial":')
        self.adapter.poll([self.rollout])
        first = self.store.cursor_for(str(self.rollout.resolve()))
        self.rollout.write_bytes(self.meta)
        self.adapter.poll([self.rollout])
        second = self.store.cursor_for(str(self.rollout.resolve()))
        self.assertEqual(second.generation, first.generation + 1)
        self.assertEqual(self.store.status()["queued"], 1)

    def test_pause_drains_queue_and_resume_skips_paused_bytes(self):
        self.rollout.write_bytes(self.meta)
        self.adapter.poll([self.rollout])
        self.adapter.pause([self.rollout])
        claimed = self.store.claim(10, "worker-1", 60)
        self.store.ack([item["event_id"] for item in claimed], "worker-1")
        self.rollout.write_bytes(self.meta + self.user)
        self.adapter.poll([self.rollout])
        self.adapter.resume([self.rollout])
        self.adapter.poll([self.rollout])
        self.assertEqual(self.store.status()["queued"], 0)
        followup = row("response_item", {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "Use B"}]}) + b"\n"
        with self.rollout.open("ab") as stream:
            stream.write(followup)
        self.adapter.poll([self.rollout])
        self.assertEqual(self.store.status()["queued"], 1)
        self.assertGreaterEqual(self.store.status()["gaps"], 1)

    def test_claims_are_lease_safe_across_store_instances(self):
        self.rollout.write_bytes(self.meta)
        self.adapter.poll([self.rollout])
        other = CaptureStore(self.db)
        self.addCleanup(other.close)
        first = self.store.claim(1, "worker-1", 60)
        second = other.claim(1, "worker-2", 60)
        self.assertEqual(len(first), 1)
        self.assertEqual(second, [])


class DeterministicDecisionParserTests(unittest.TestCase):
    def setUp(self):
        self.parser = DecisionParser()
        self.messages = [
            {"turn": 1, "source_ordinal": 10, "actor": "user", "text": "We need to choose a capture strategy."},
            {"turn": 1, "source_ordinal": 11, "actor": "agent", "text": "I propose using structured markers and a deterministic parser because it narrows the search."},
            {"turn": 2, "source_ordinal": 12, "actor": "user", "text": "Yes, that's the right approach. Use structured markers."},
            {"turn": 2, "source_ordinal": 13, "actor": "agent", "text": "I will implement it."},
        ]

    def test_marker_assisted_candidate_is_atomic_source_linked_and_stable(self):
        marker = {
            "turn": 2,
            "source_ordinal": 12,
            "strength": "hard",
            "state": "accepted",
            "origin": "user",
            "trigger_class": "contextual_acceptance",
            "issue_hint": "capture strategy",
            "trigger_quote": "that's the right approach",
        }
        outputs = [self.parser.parse("rollout-1", self.messages, marker=marker) for _ in range(3)]
        encoded = [json.dumps(value, sort_keys=True, separators=(",", ":")) for value in outputs]
        self.assertEqual(encoded[0], encoded[1])
        self.assertEqual(encoded[1], encoded[2])
        candidate = outputs[0][0]
        self.assertEqual(candidate["state"], "accepted")
        self.assertEqual(candidate["deciding_actor"], "user")
        self.assertEqual(candidate["agreement_quote"], "that's the right approach")
        self.assertTrue(candidate["candidate_id"].startswith("p02_"))
        self.assertEqual(candidate["source"]["rollout_id"], "rollout-1")
        self.assertIn("rule_path", candidate)

    def test_proposal_without_grounded_user_agreement_stays_proposed(self):
        candidates = self.parser.parse("rollout-1", self.messages[:2])
        self.assertTrue(candidates)
        self.assertTrue(all(candidate["state"] == "proposed" for candidate in candidates))

    def test_ambiguous_acknowledgement_is_not_accepted(self):
        messages = self.messages[:2] + [{"turn": 2, "source_ordinal": 12, "actor": "user", "text": "Okay."}]
        candidates = self.parser.parse("rollout-1", messages)
        self.assertTrue(candidates)
        self.assertTrue(all(candidate["state"] != "accepted" for candidate in candidates))

    def test_region_is_bounded_to_two_prior_one_following_and_limits(self):
        messages = [
            {"turn": index, "source_ordinal": index, "actor": "user" if index % 2 else "agent", "text": "x" * 1000}
            for index in range(1, 12)
        ]
        region = self.parser.region("rollout-1", messages, marker_turn=7)
        turns = {message["turn"] for message in region["messages"]}
        self.assertTrue(turns.issubset({5, 6, 7, 8}))
        self.assertLessEqual(len(region["messages"]), 20)
        self.assertLessEqual(len(json.dumps(region["messages"])), 9000)


if __name__ == "__main__":
    unittest.main()

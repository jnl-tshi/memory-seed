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

    def test_region_uses_twenty_turn_safety_envelope_and_ranks_short_spans(self):
        messages = [
            {
                "turn": index,
                "source_ordinal": index,
                "actor": "user" if index % 2 else "agent",
                "text": "ordinary context" if index != 7 else "I propose option A because it is deterministic.",
            }
            for index in range(1, 25)
        ]
        messages.append({"turn": 24, "source_ordinal": 25, "actor": "user", "text": "Yes, choose option A."})
        marker = {"turn": 24, "issue_hint": "choose deterministic option A", "trigger_quote": "choose option A"}
        region = self.parser.region("rollout-1", messages, marker_turn=24, marker=marker)
        turns = {message["turn"] for message in region["messages"]}
        self.assertEqual(min(turns), 4)
        self.assertEqual(max(turns), 24)
        self.assertIn(7, turns)
        self.assertIn("ranked_spans", region)
        ranked_turns = {turn for span in region["ranked_spans"][:3] for turn in span["turns"]}
        self.assertIn(7, ranked_turns)
        self.assertIn(24, ranked_turns)

    def test_marker_parser_expands_from_ranked_spans_to_full_envelope(self):
        messages = [
            {"turn": 2, "source_ordinal": 2, "actor": "agent", "text": "I propose option A because it preserves lineage."},
            *[
                {"turn": index, "source_ordinal": index, "actor": "agent", "text": "implementation detail"}
                for index in range(3, 20)
            ],
            {"turn": 20, "source_ordinal": 20, "actor": "user", "text": "Yes, choose option A."},
        ]
        marker = {
            "turn": 20,
            "source_ordinal": 20,
            "strength": "hard",
            "state": "accepted",
            "origin": "user",
            "trigger_class": "explicit_commitment",
            "issue_hint": "lineage option",
            "trigger_quote": "choose option A",
        }
        candidates = self.parser.parse("rollout-1", messages, marker=marker)
        self.assertTrue(candidates)
        self.assertEqual(candidates[0]["state"], "accepted")
        self.assertIn(2, candidates[0]["source"]["envelope_turns"])
        self.assertEqual(candidates[0]["source"]["retrieval_strategy"], "delta_only_components")

    def test_marker_parser_can_join_parent_lineage_proposal_to_child_acceptance(self):
        child = [
            {
                "rollout_id": "child-rollout",
                "turn": 4,
                "source_ordinal": 40,
                "actor": "user",
                "timestamp": "2026-09-29T10:04:00Z",
                "text": "Yes, that's the right approach.",
            }
        ]
        parent = [
            {
                "rollout_id": "parent-rollout",
                "turn": 18,
                "source_ordinal": 180,
                "actor": "agent",
                "timestamp": "2026-09-29T10:00:00Z",
                "text": "I propose we use lineage-aware retrieval for decision capture because the decision began in the parent task.",
            }
        ]
        marker = {
            "turn": 4,
            "strength": "hard",
            "state": "accepted",
            "origin": "user",
            "trigger_class": "contextual_acceptance",
            "issue_hint": "lineage retrieval",
            "trigger_quote": "that's the right approach",
        }
        candidates = self.parser.parse("child-rollout", child, marker=marker, lineage_messages=parent)
        self.assertTrue(candidates)
        coordinates = candidates[0]["source"]["source_coordinates"]
        self.assertEqual({coordinate["rollout_id"] for coordinate in coordinates}, {"parent-rollout", "child-rollout"})

    def test_stepped_forward_capture_stops_at_marker_when_decision_is_complete(self):
        marker = {
            "turn": 2,
            "strength": "hard",
            "state": "accepted",
            "origin": "user",
            "trigger_class": "explicit_commitment",
            "issue_hint": "capture strategy",
            "trigger_quote": "Use structured markers",
        }
        messages = [
            {"turn": 2, "source_ordinal": 20, "actor": "user", "text": "Issue: locating decisions. Use structured markers for decision capture."},
            {"turn": 3, "source_ordinal": 30, "actor": "agent", "text": "I will now recap the decision."},
        ]
        candidates = self.parser.parse_stepped("rollout-1", messages, marker=marker)
        self.assertTrue(candidates)
        self.assertEqual(candidates[0]["source"]["retrieval_trace"]["selected_stage"], "marker")
        self.assertEqual(candidates[0]["source"]["retrieval_trace"]["forward_turns"], 0)

    def test_earlier_acceptance_does_not_approve_a_future_proposal(self):
        marker = {
            "turn": 2,
            "strength": "hard",
            "state": "accepted",
            "origin": "user",
            "trigger_class": "contextual_acceptance",
            "issue_hint": "capture strategy",
            "trigger_quote": "that's the right approach",
        }
        messages = [
            {"turn": 2, "source_ordinal": 20, "actor": "user", "text": "Yes, that's the right approach."},
            {
                "turn": 3,
                "source_ordinal": 30,
                "actor": "agent",
                "text": "I propose we use structured markers and curator verification because that preserves provenance.",
            },
            {"turn": 6, "source_ordinal": 60, "actor": "agent", "text": "Unrelated later material."},
        ]
        candidates = self.parser.parse_stepped("rollout-1", messages, marker=marker)
        self.assertFalse(any(c["state"] == "accepted" for c in candidates))


if __name__ == "__main__":
    unittest.main()

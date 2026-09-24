from __future__ import annotations

import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


BASE = Path(__file__).resolve().parent
MODULE_PATH = BASE / "prepare_verification_packets.py"
SPEC = importlib.util.spec_from_file_location("prepare_verification_packets", MODULE_PATH)
assert SPEC and SPEC.loader
prepare_packets = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = prepare_packets
SPEC.loader.exec_module(prepare_packets)


def fixtures(group_sizes: list[tuple[str, int]]) -> tuple[dict, dict, set[str]]:
    ids: list[str] = []
    alignments = []
    known_sessions: set[str] = set()
    for session_index, (session_id, count) in enumerate(group_sizes):
        if session_id.startswith("known"):
            known_sessions.add(session_id)
        for row_index in range(count):
            decision_id = f"decision-{session_index:02d}-{row_index:02d}"
            ids.append(decision_id)
            alignments.append(
                {
                    "decision": {
                        "decision_id": decision_id,
                        "title": f"Decision {decision_id}",
                        "decision_timestamp": "2026-09-01T12:00:00Z",
                        "source_path": "sessions/example.md",
                        "start_line": row_index + 10,
                        "end_line": row_index + 12,
                    },
                    "best_candidate": {
                        "session_id": session_id,
                        "rollout_id": f"rollout-{session_id}",
                        "winning_turn": 80 + row_index,
                        "source_path": f".codex/sessions/{session_id}.jsonl",
                        "window": {"turn_start": 79, "turn_end": 82},
                    },
                }
            )
    return (
        {"metadata": {"sample_ids": ids, "sample_ids_sha256": "cohort-hash", "sample_seed": 123}},
        {"alignments": alignments},
        known_sessions,
    )


class VerificationPacketTests(unittest.TestCase):
    def test_exact_coverage_grouping_and_known_gold_preference(self) -> None:
        groups = [(f"unseen-{index:02d}", 1) for index in range(20)]
        groups += [("known-dev-a", 16), ("known-dev-b", 17)]
        manifest, alignments, known = fixtures(groups)
        split = prepare_packets.build_split(manifest, alignments, known)
        dev_ids = {row["decision_id"] for row in split["development"]}
        final_ids = {row["decision_id"] for row in split["final"]}
        self.assertEqual((len(dev_ids), len(final_ids)), (33, 20))
        self.assertFalse(dev_ids & final_ids)
        self.assertEqual(dev_ids | final_ids, set(manifest["metadata"]["sample_ids"]))
        self.assertEqual({row["logical_session_id"] for row in split["final"]},
                         {f"unseen-{index:02d}" for index in range(20)})

    def test_split_is_deterministic_under_input_reordering(self) -> None:
        manifest, alignments, known = fixtures(
            [(f"unseen-{index:02d}", 1) for index in range(20)]
            + [("known-dev-a", 16), ("known-dev-b", 17)]
        )
        first = prepare_packets.build_split(manifest, alignments, known)
        reordered_manifest = {"metadata": dict(manifest["metadata"])}
        reordered_manifest["metadata"]["sample_ids"] = list(reversed(manifest["metadata"]["sample_ids"]))
        reordered = prepare_packets.build_split(
            reordered_manifest, {"alignments": list(reversed(alignments["alignments"]))}, known
        )
        self.assertEqual(
            [row["decision_id"] for row in first["final"]],
            [row["decision_id"] for row in reordered["final"]],
        )
        self.assertEqual(
            [row["decision_id"] for row in first["development"]],
            [row["decision_id"] for row in reordered["development"]],
        )

    def test_public_manifest_does_not_expose_sealed_source_groups_or_coordinates(self) -> None:
        manifest, alignments, known = fixtures(
            [(f"unseen-{index:02d}", 1) for index in range(20)]
            + [("known-dev-a", 16), ("known-dev-b", 17)]
        )
        split = prepare_packets.build_split(manifest, alignments, known)
        public = prepare_packets.public_manifest(split, manifest["metadata"])
        sealed = public["sealed_final"]
        self.assertEqual(
            set(sealed),
            {"size", "decision_ids", "decision_ids_sha256", "group_count", "group_assignment_sha256"},
        )
        serialized = json.dumps(sealed)
        self.assertNotIn("logical_session_ids", serialized)
        self.assertNotIn("coordinates", serialized)
        self.assertNotIn("rollout_id", serialized)
        self.assertNotIn("source_path", serialized)
        self.assertEqual(sealed["group_count"], 20)
        self.assertEqual(len(sealed["group_assignment_sha256"]), 64)
        private = prepare_packets.private_split_artifact(split, "cohort-hash")
        private_final = private["sealed_final"]
        self.assertEqual(len(private_final["coordinates"]), 20)
        self.assertEqual(private_final["group_assignment_sha256"], sealed["group_assignment_sha256"])

    def test_impossible_whole_session_partition_fails_closed(self) -> None:
        manifest, alignments, known = fixtures([("session-a", 21), ("session-b", 32)])
        with self.assertRaisesRegex(ValueError, "cannot form an exact 20-decision final set"):
            prepare_packets.build_split(manifest, alignments, known)

    def test_verifier_packets_omit_candidate_ranking_and_holdout(self) -> None:
        manifest, alignments, known = fixtures(
            [(f"unseen-{index:02d}", 1) for index in range(20)]
            + [("known-dev-a", 16), ("known-dev-b", 17)]
        )
        split = prepare_packets.build_split(manifest, alignments, known)
        packet_a = prepare_packets.verifier_packet(split["development"], "A", "hash")
        packet_b = prepare_packets.verifier_packet(split["development"], "B", "hash")
        serialized_a = json.dumps(packet_a)
        serialized_b = json.dumps(packet_b)
        self.assertEqual(len(packet_a["reviews"]), 33)
        self.assertEqual(len(packet_b["reviews"]), 33)
        self.assertFalse({row["decision_id"] for row in packet_a["reviews"]} &
                         {row["decision_id"] for row in split["final"]})
        for serialized in (serialized_a, serialized_b):
            for forbidden in (
                "best_candidate", "winning_turn", "window_turn_start", "confidence",
                "ranking_score", "session_id", "rollout_id", "rollout-",
                "verifier_a_review", "verifier_b_review", "gold_label",
            ):
                self.assertNotIn(forbidden, serialized)
        self.assertIn("minimal_useful_refs", serialized_a)
        self.assertNotEqual(packet_a["verifier"], packet_b["verifier"])

    def test_adjudication_template_preserves_both_reviews_and_final_refs(self) -> None:
        manifest, alignments, known = fixtures(
            [(f"unseen-{index:02d}", 1) for index in range(20)]
            + [("known-dev-a", 16), ("known-dev-b", 17)]
        )
        template = prepare_packets.adjudication_template(
            prepare_packets.build_split(manifest, alignments, known)
        )
        self.assertEqual(len(template["reviews"]), 53)
        self.assertEqual(template["reviews"][0]["verifier_a_review"]["label"], None)
        self.assertEqual(template["reviews"][0]["verifier_b_review"]["minimal_useful_refs"], [])
        self.assertEqual(template["reviews"][0]["final_adjudication"]["evidence_refs"], [])
        self.assertEqual(template["final_adjudication_shape"]["minimal_useful_refs"], [])

    def test_cli_summary_does_not_read_removed_sealed_overlap_field(self) -> None:
        manifest, alignments, _known = fixtures(
            [(f"unseen-{index:02d}", 1) for index in range(20)]
            + [("known-dev-a", 16), ("known-dev-b", 17)]
        )
        with tempfile.TemporaryDirectory(prefix="verification-packets-") as temp_dir:
            root = Path(temp_dir)
            manifest_path = root / "manifest.json"
            alignments_path = root / "alignments.json"
            gold_path = root / "gold.jsonl"
            public_path = root / "public.json"
            private_dir = root / "private"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            alignments_path.write_text(json.dumps(alignments), encoding="utf-8")
            gold_path.write_text("", encoding="utf-8")
            argv = [
                "prepare_verification_packets.py",
                "--manifest", str(manifest_path),
                "--alignments", str(alignments_path),
                "--known-gold", str(gold_path),
                "--public-output", str(public_path),
                "--private-output-dir", str(private_dir),
            ]
            stdout = io.StringIO()
            with patch.object(sys, "argv", argv), redirect_stdout(stdout):
                self.assertEqual(prepare_packets.main(), 0)
            summary = json.loads(stdout.getvalue())
            self.assertEqual(summary["development_size"], 33)
            self.assertEqual(summary["final_size"], 20)
            self.assertNotIn("final_sessions_seen_in_known_gold", summary)


if __name__ == "__main__":
    unittest.main()

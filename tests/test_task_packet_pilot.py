import json
import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.task_packet import (
    canonical_task_packet_json,
    estimate_tokens,
    normalize_task_dispatch,
)
from tests.pilot_task_packet_fixture import (
    build_fixture_runtime,
    compile_fixture_packet,
    recorded_worker_assessment,
    semantic_dispatch,
    worker_environment,
)


class TaskPacketPilotTests(unittest.TestCase):
    def make_runtime(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="memory-seed-task-packet-pilot-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        return build_fixture_runtime(root)

    def test_offline_clean_session_packet_is_complete_bounded_and_nonexpansive(self):
        root = self.make_runtime()
        packet = compile_fixture_packet(root)
        packet_again = compile_fixture_packet(root)
        canonical = canonical_task_packet_json(packet)

        self.assertEqual(canonical, canonical_task_packet_json(packet_again))
        self.assertEqual(packet["dispatch"], normalize_task_dispatch(semantic_dispatch()))
        self.assertEqual(
            (packet["retrieval_profile"]["id"], packet["retrieval_profile"]["profile_version"]),
            ("implementation", 1),
        )
        self.assertEqual(packet["dispatch"]["execution"]["capability_tier"], "balanced")
        self.assertLessEqual(
            packet["input_ledger"]["total_context_envelope_tokens"],
            packet["input_ledger"]["band"]["soft_cap_tokens"],
        )
        self.assertEqual(
            estimate_tokens(canonical),
            packet["input_ledger"]["serialized_packet_input_tokens"],
        )
        self.assertEqual(packet["cost_ledger"]["status"], "unavailable")
        self.assertEqual(packet["cost_ledger"]["reason"], "pricing_not_supplied")
        self.assertGreater(packet["input_ledger"]["fixed_instruction_tokens"], 0)
        self.assertGreater(packet["input_ledger"]["tool_schema_input_tokens"], 0)
        accounted_input = (
            packet["input_ledger"]["serialized_packet_input_tokens"]
            + packet["input_ledger"]["fixed_instruction_tokens"]
            + packet["input_ledger"]["tool_schema_input_tokens"]
            + packet["input_ledger"]["supplemental_input_reserve_tokens"]
        )
        self.assertEqual(packet["input_ledger"]["total_input_tokens"], accounted_input)
        self.assertTrue(worker_environment()["fixed_instructions"])
        self.assertTrue(worker_environment()["tool_schemas"])

        manifest = packet["evidence_pack"]["evidence"]
        materialized = packet["materialized_evidence"]
        materialized_ids = {item["id"] for item in materialized}
        projection = packet["constitution_projection"]
        projected_constitution_ids = (
            {item["path"] for item in projection["clauses"]}
            if projection["mode"] == "anchored_clauses"
            else {projection["full_document"]["path"]}
        )
        supplied_ids = materialized_ids | projected_constitution_ids
        self.assertTrue(
            {"adr_task_packet_pilot", "mse_packetpilot:d1", "docs/pilot-support.md"}
            <= materialized_ids
        )
        self.assertEqual(len(materialized_ids), len(materialized))
        self.assertEqual(
            len({item["source"] for item in materialized}), len(materialized)
        )
        self.assertTrue(all(item["excerpt"] is None for item in manifest))
        for item in materialized:
            self.assertEqual(
                canonical.count(json.dumps(item["content"], ensure_ascii=False)), 1
            )

        # This versioned record is the genuine clean worker's self-report. The
        # harness can prove schema/reference/ledger consistency, but it cannot
        # turn no-refetch/no-discovery into independently instrumented facts.
        assessment = recorded_worker_assessment()
        cited_ids = {
            evidence_id
            for conclusion in assessment["conclusions"]
            for evidence_id in conclusion["evidence_ids"]
        }
        self.assertEqual(assessment["evidence_status"], "sufficient")
        self.assertTrue(cited_ids <= supplied_ids)
        self.assertEqual(
            set(assessment["evidence_id_correctness"]["referenced_evidence_ids"]),
            supplied_ids,
        )
        self.assertEqual(assessment["evidence_id_correctness"]["status"], "correct")
        self.assertTrue(assessment["evidence_id_correctness"]["all_present_in_packet"])
        self.assertEqual(assessment["missing_questions"], [])
        self.assertEqual(assessment["supplemental_sources"], [])
        self.assertEqual(assessment["supplemental_calls"], [])
        self.assertEqual(assessment["unsupported_assertions"], [])
        self.assertEqual(assessment["repeated_fetches"]["status"], "none")
        self.assertFalse(assessment["repeated_fetches"]["materialized_sources_refetched"])
        self.assertFalse(assessment["broad_discovery"]["occurred"])
        self.assertEqual(assessment["selected_tier"], "balanced")
        self.assertEqual(assessment["soft_cap_tokens"], 48_000)
        caller_accounting = assessment["caller_supplied_harness_accounting"]
        self.assertEqual(
            set(caller_accounting),
            {"status", "fixed_instruction_tokens", "tool_schema_tokens"},
        )
        self.assertEqual(caller_accounting["status"], "available")
        self.assertEqual(
            caller_accounting["fixed_instruction_tokens"],
            packet["input_ledger"]["fixed_instruction_tokens"],
        )
        self.assertEqual(
            caller_accounting["tool_schema_tokens"],
            packet["input_ledger"]["tool_schema_input_tokens"],
        )
        self.assertNotIn("platform_overhead", assessment)
        self.assertEqual(assessment["hidden_platform_overhead"]["status"], "unavailable")
        self.assertIn(
            "runtime did not surface",
            assessment["hidden_platform_overhead"]["reason"].lower(),
        )
        self.assertEqual(
            assessment["tool_call_instrumentation"]["status"],
            "self_report_only",
        )
        self.assertEqual(assessment["tool_call_instrumentation"]["tool_calls_made"], 0)
        for field in (
            "actual_provider_input",
            "actual_provider_usage",
            "actual_provider_latency",
            "actual_provider_cost",
        ):
            self.assertEqual(assessment[field]["status"], "unavailable")
            self.assertTrue(assessment[field]["reason"])

        forbidden_expansions = {
            "packet_registry",
            "worker_dispatch",
            "worktree_creation",
            "network_access",
            "authority_expansion",
        }
        self.assertTrue(forbidden_expansions.isdisjoint(packet))


if __name__ == "__main__":
    unittest.main()

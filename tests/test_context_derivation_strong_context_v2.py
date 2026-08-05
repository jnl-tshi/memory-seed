import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "experiments" / "context-derivation" / "strong_context_v2.py"
SPEC = importlib.util.spec_from_file_location("strong_context_v2", SCRIPT)
assert SPEC and SPEC.loader
module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = module
SPEC.loader.exec_module(module)


REF_OLD = "mse_alpha1234:d1"
REF_HEAD = "mse_beta5678:d1"
REF_SHARED = "mse_gamma9012:d1"
REF_RELATED = "mse_delta3456:d1"
REF_MID_ONE = "mse_epsilon6789:d1"
REF_MID_TWO = "mse_zeta0123:d1"


def binding_document():
    return {
        "schema": module.BINDINGS_SCHEMA,
        "adrs": [
            {
                "adr_id": "adr_indexing",
                "membership": [REF_OLD, REF_HEAD, REF_SHARED],
                "current": {
                    "authoritative_ref": REF_HEAD, "status": "accepted",
                    "decision": "Use the incremental local index.",
                    "why": "It avoids a full rebuild.",
                    "evolution": "It superseded the initial index.",
                },
                "lineage": [
                    {"ref": REF_OLD, "predecessors": [], "status": "accepted", "decision": "Use a full rebuild.", "why": "Initial design.", "evolution": "Initial."},
                    {"ref": REF_HEAD, "predecessors": [{"ref": REF_OLD, "type": "evolves"}], "status": "accepted", "decision": "Use an incremental index.", "why": "Scale test.", "evolution": "Evolves the full rebuild."},
                ],
                "constitution_refs": [
                    {"ref": "constitution:v1#local-first", "role": "governing", "excerpt": "Local-first state is the governing constraint."},
                    {"ref": "constitution:v1#observability", "role": "supporting", "excerpt": "Evidence must remain inspectable."},
                ],
                "related_refs": [REF_RELATED],
            },
            {
                "adr_id": "adr_shared_concern",
                "membership": [REF_SHARED],
                "current": {
                    "authoritative_ref": REF_SHARED, "status": "accepted",
                    "decision": "Keep shared evidence explicit.",
                    "why": "One decision affects two concerns.",
                    "evolution": "Initial.",
                },
                "lineage": [
                    {"ref": REF_SHARED, "predecessors": [], "status": "accepted", "decision": "Keep shared evidence explicit.", "why": "Two concerns.", "evolution": "Initial."},
                ],
                "constitution_refs": [
                    {"ref": "constitution:v1#provenance", "role": "governing", "excerpt": "Provenance must be explicit."},
                ],
                "related_refs": [],
            },
        ],
    }


def ranked():
    return [
        {"ref": REF_OLD, "relevance": "strong", "excerpt": "FULL OLD DECISION", "links": {"evolves": [], "replaces": [], "related": [REF_RELATED]}},
        {"ref": REF_SHARED, "relevance": "strong", "excerpt": "FULL SHARED DECISION", "links": {"evolves": [], "replaces": [], "related": []}},
        {"ref": REF_HEAD, "relevance": "strong", "excerpt": "FULL HEAD DECISION", "links": {"evolves": [REF_OLD], "replaces": [], "related": []}},
        {"ref": REF_RELATED, "relevance": "weak", "excerpt": "RELATED ONLY", "links": {"evolves": [], "replaces": [], "related": []}},
    ]


class StrongContextV2Tests(unittest.TestCase):
    def setUp(self):
        self.bindings = module.load_bindings(binding_document())

    def test_strong_signal_gets_full_three_level_context_and_lineage_path(self):
        result = module.resolve_strong_context(ranked(), self.bindings, {"strong_cap": 1, "adr_cap": 2})
        first = result["tiers"][0]
        self.assertEqual("full", first["tier"])
        self.assertEqual("FULL OLD DECISION", first["decision"]["excerpt"])
        adr = first["adrs"][0]
        self.assertEqual("adr_indexing", adr["adr_id"])
        self.assertEqual(REF_HEAD, adr["current"]["authoritative_ref"])
        self.assertEqual([REF_OLD, REF_HEAD], [item["ref"] for item in adr["relevant_lineage"]])
        self.assertEqual("constitution:v1#local-first", adr["constitution"][0]["ref"])
        self.assertEqual("governing", adr["constitution"][0]["role"])
        self.assertEqual([{"ref": REF_OLD, "type": "evolves"}], adr["relevant_lineage"][1]["predecessors"])

    def test_strong_and_adr_caps_preserve_rank_order_and_emit_deterministic_omissions(self):
        result = module.resolve_strong_context(ranked(), self.bindings, {"strong_cap": 2, "adr_cap": 1})
        self.assertEqual(["full", "full", "compact", "compact"], [item["tier"] for item in result["tiers"]])
        self.assertEqual(["adr_indexing"], [item["adr_id"] for item in result["tiers"][0]["adrs"]])
        # The shared decision belongs to two concerns.  The unique ADR cap
        # blocks the new concern but may reuse an ADR already admitted at a
        # higher rank without consuming another slot.
        self.assertEqual([], result["tiers"][1]["adrs"])
        self.assertEqual(["adr_indexing"], result["tiers"][1]["adr_refs"])
        self.assertEqual("adr_indexing", result["tiers"][1]["lineage_deltas"][0]["adr_id"])
        self.assertIn({"kind": "adr-cap", "rank": 2, "ref": REF_SHARED, "adr_ids": ["adr_shared_concern"]}, result["omissions"])
        self.assertIn({"kind": "strong-cap", "rank": 3, "ref": REF_HEAD}, result["omissions"])
        self.assertEqual(result, module.resolve_strong_context(ranked(), binding_document(), {"strong_cap": 2, "adr_cap": 1}))

    def test_related_never_triggers_expansion_or_membership(self):
        results = [{"ref": REF_RELATED, "relevance": "strong", "excerpt": "RELATED", "links": {"evolves": [], "replaces": [], "related": [REF_OLD]}}]
        resolved = module.resolve_strong_context(results, self.bindings)
        self.assertEqual("full", resolved["tiers"][0]["tier"])
        self.assertEqual([], resolved["tiers"][0]["adrs"])
        self.assertEqual([], resolved["trace"][0]["matched_adr_ids"])

    def test_noncanonical_or_nonstrong_result_is_compact_with_adr_refs_only(self):
        results = [
            {"ref": "mse_alpha1234", "relevance": "strong", "excerpt": "not a decision", "links": {"evolves": [], "replaces": [], "related": []}},
            {"ref": REF_SHARED, "relevance": "weak", "excerpt": "x" * 30, "links": {"evolves": [], "replaces": [], "related": []}},
        ]
        resolved = module.resolve_strong_context(results, self.bindings, {"compact_decision_chars": 10})
        self.assertEqual(["compact", "compact"], [item["tier"] for item in resolved["tiers"]])
        self.assertEqual([], resolved["tiers"][0]["adr_refs"])
        self.assertEqual(["adr_indexing", "adr_shared_concern"], resolved["tiers"][1]["adr_refs"])
        self.assertTrue(resolved["tiers"][1]["decision"]["truncated"])

    def test_top_k_recall_is_mechanical_and_related_does_not_count(self):
        metrics = module.top_k_recall(
            ranked(), self.bindings,
            required_decision_refs=[REF_SHARED],
            required_adr_ids=["adr_shared_concern"],
            required_constitution_refs=["constitution:v1#provenance"],
            ks=[1, 2, 3],
        )
        self.assertFalse(metrics["rows"][0]["complete"])
        self.assertTrue(metrics["rows"][1]["complete"])
        self.assertEqual([REF_OLD, REF_SHARED], metrics["rows"][1]["ranked_decision_refs"])
        related_metric = module.top_k_recall(
            [{"ref": REF_RELATED, "relevance": "strong", "excerpt": "related", "links": {"evolves": [], "replaces": [], "related": [REF_SHARED]}}],
            self.bindings,
            required_decision_refs=[], required_adr_ids=["adr_indexing"],
            required_constitution_refs=["constitution:v1#local-first"], ks=[1],
        )
        self.assertFalse(related_metric["rows"][0]["adr"]["complete"])
        self.assertFalse(related_metric["rows"][0]["constitution"]["complete"])

    def test_invalid_binding_rejects_related_as_lineage(self):
        invalid = binding_document()
        invalid["adrs"][0]["related_refs"] = [REF_OLD]
        with self.assertRaisesRegex(ValueError, "related_refs must not"):
            module.load_bindings(invalid)

    def test_current_authority_and_lineage_cycles_fail_closed(self):
        invalid = binding_document()
        invalid["adrs"][0]["current"]["status"] = "proposed"
        with self.assertRaisesRegex(ValueError, "conflicts"):
            module.load_bindings(invalid)

        missing_head = binding_document()
        missing_head["adrs"][0]["current"]["authoritative_ref"] = REF_SHARED
        with self.assertRaisesRegex(ValueError, "accepted lineage"):
            module.load_bindings(missing_head)

        cyclic = binding_document()
        cyclic["adrs"][0]["lineage"][0]["predecessors"] = [{"ref": REF_HEAD, "type": "evolves"}]
        with self.assertRaisesRegex(ValueError, "cycle"):
            module.load_bindings(cyclic)

    def test_zero_lineage_budget_keeps_only_mandatory_direct_evidence(self):
        long_chain = binding_document()
        adr = long_chain["adrs"][0]
        adr["membership"] = [REF_OLD, REF_MID_ONE, REF_MID_TWO, REF_HEAD]
        adr["lineage"] = [
            {"ref": REF_OLD, "predecessors": [], "status": "accepted", "decision": "root", "why": "root", "evolution": "root"},
            {"ref": REF_MID_ONE, "predecessors": [{"ref": REF_OLD, "type": "evolves"}], "status": "accepted", "decision": "one", "why": "one", "evolution": "one"},
            {"ref": REF_MID_TWO, "predecessors": [{"ref": REF_MID_ONE, "type": "evolves"}], "status": "accepted", "decision": "two", "why": "two", "evolution": "two"},
            {"ref": REF_HEAD, "predecessors": [{"ref": REF_MID_TWO, "type": "evolves"}], "status": "accepted", "decision": "head", "why": "head", "evolution": "head"},
        ]
        resolved = module.resolve_strong_context(
            [{"ref": REF_OLD, "relevance": "strong", "excerpt": "root", "links": {"evolves": [], "replaces": [], "related": []}}],
            long_chain,
            {"lineage_item_cap": 0},
        )
        lineage = resolved["tiers"][0]["adrs"][0]["relevant_lineage"]
        self.assertEqual([REF_OLD, REF_MID_TWO, REF_HEAD], [row["ref"] for row in lineage])
        self.assertIn({"kind": "lineage-cap", "adr_id": "adr_indexing", "omitted_refs": [REF_MID_ONE]}, resolved["omissions"])

        head_match = module.resolve_strong_context(
            [{"ref": REF_HEAD, "relevance": "strong", "excerpt": "head", "links": {"evolves": [], "replaces": [], "related": []}}],
            long_chain,
            {"lineage_item_cap": 0},
        )
        head_lineage = head_match["tiers"][0]["adrs"][0]["relevant_lineage"]
        self.assertEqual([REF_MID_TWO, REF_HEAD], [row["ref"] for row in head_lineage])
        self.assertIn({"kind": "lineage-cap", "adr_id": "adr_indexing", "omitted_refs": [REF_OLD, REF_MID_ONE]}, head_match["omissions"])


if __name__ == "__main__":
    unittest.main()

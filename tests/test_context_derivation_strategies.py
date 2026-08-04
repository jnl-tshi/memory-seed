import json
import sys
import tempfile
import unittest
from pathlib import Path

EXPERIMENT = Path(__file__).parents[1] / "experiments" / "context-derivation"
sys.path.insert(0, str(EXPERIMENT))

from contracts import STRATEGY_SCHEMA, TASK_SCHEMA  # noqa: E402
from materialize import materialize_packet  # noqa: E402
from reduce import reduce_shards  # noqa: E402
from strategies import load_corpus, resolve_strategy, strategy_grid  # noqa: E402
from sweep import SHARD_SCHEMA, run_sweep  # noqa: E402

from memory_seed.adr import AdrEvent, AdrPredecessor, AdrRecord, render_adr  # noqa: E402


def _event(kind, event_id, ref=None, *, predecessors=(), replacement=None):
    return AdrEvent(
        kind=kind,
        event_id=event_id,
        timestamp=f"2026-08-01T0{event_id[-1]}:00:00Z",
        source="write-time",
        decision_ref=ref,
        update_entry_id=ref.split(":", 1)[0] if ref else "mse_status",
        predecessors=tuple(predecessors),
        decision=f"Decision for {ref}." if ref else "",
        why="Fixture rationale.",
        evolution="Fixture evolution.",
        replacement_adr=replacement,
    )


class ContextDerivationStrategyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        sessions = self.root / ".memory-seed" / "sessions" / "2026-08"
        decisions = self.root / ".memory-seed" / "decisions"
        sessions.mkdir(parents=True)
        decisions.mkdir(parents=True)
        entries = [
            ("mse_old", "Old", "", "Use the old design."),
            ("mse_a", "Branch A", "evolves:\n  - mse_old", "Refine branch A."),
            ("mse_b", "Branch B", "evolves:\n  - mse_old", "Refine branch B."),
            ("mse_head", "Converged", "evolves:\n  - mse_a\n  - mse_b", "Use the converged design."),
            ("mse_pending", "Pending", "", "Try a pending design."),
            ("mse_rejected", "Rejected", "", "Reject this design."),
            ("mse_related", "Related", "related_entries:\n  - mse_head", "Related operational note."),
            ("mse_beta", "Beta", "", "Use the beta design."),
        ]
        body = ["---", "tags:", "  - session-log", "session_date: 2026-08-01", "---", ""]
        for hour, (entry_id, title, links, decision) in enumerate(entries, 9):
            body.extend([
                f"## 2026-08-01 {hour:02d}:00 - {title}", "", "```yaml",
                f"entry_id: {entry_id}", "user_initials: JNL", "agent_type: codex",
                "project_path: .", "subproject_path: null",
            ])
            if links:
                body.extend(links.splitlines())
            body.extend(["```", "", "### Decision", "", f"- D: {decision}", "- R: Fixture.", ""])
        (sessions / "2026-08-01.md").write_text("\n".join(body), encoding="utf-8")

        old = "mse_old:d1"
        a = "mse_a:d1"
        b = "mse_b:d1"
        head = "mse_head:d1"
        pending = "mse_pending:d1"
        rejected = "mse_rejected:d1"
        alpha = AdrRecord(
            1, "adr_alpha", "Alpha architecture", (), "2026-08-01T00:00:00Z",
            "JNL", "codex", "write-time",
            [
                _event("revision-proposed", "adre_old000000000000001", old),
                _event("revision-accepted", "adre_old000000000000002", old),
                _event("revision-proposed", "adre_bra000000000000003", a, predecessors=[AdrPredecessor(old, f"link:{a}:evolves:{old}")]),
                _event("revision-accepted", "adre_bra000000000000004", a),
                _event("revision-proposed", "adre_brb000000000000005", b, predecessors=[AdrPredecessor(old, f"link:{b}:evolves:{old}")]),
                _event("revision-proposed", "adre_hea000000000000006", head, predecessors=[AdrPredecessor(a, f"link:{head}:evolves:{a}"), AdrPredecessor(b, f"link:{head}:evolves:{b}")]),
                _event("revision-accepted", "adre_hea000000000000007", head),
                AdrEvent("reviewed-no-change", "adre_noc000000000000008", "2026-08-01T08:00:00Z", "write-time", decision_ref=head, update_entry_id="mse_head", reason="The accepted head remains valid."),
                _event("revision-proposed", "adre_pen000000000000008", pending),
                _event("revision-proposed", "adre_rej000000000000009", rejected),
                AdrEvent("revision-rejected", "adre_rej000000000000010", "2026-08-01T10:00:00Z", "write-time", decision_ref=rejected, update_entry_id="mse_rejected"),
            ],
            decisions / "adr_alpha.md",
        )
        beta_ref = "mse_beta:d1"
        beta = AdrRecord(
            1, "adr_beta", "Beta architecture", (), "2026-08-01T00:00:00Z",
            "JNL", "codex", "write-time",
            [_event("revision-proposed", "adre_bet000000000000001", beta_ref), _event("revision-accepted", "adre_bet000000000000002", beta_ref)],
            decisions / "adr_beta.md",
        )
        for record in (alpha, beta):
            record.path.write_text(render_adr(record), encoding="utf-8")
        load_corpus(self.root, refresh=True)

    def tearDown(self):
        load_corpus.cache_clear() if hasattr(load_corpus, "cache_clear") else None
        self.temp.cleanup()

    def _task(self, *, task_id="CTX-01", adrs=("adr_alpha",), refs=()):
        return {
            "schema": TASK_SCHEMA, "task_id": task_id, "fixture": "minimal",
            "question": "What is the current alpha architecture?", "task_type": "accepted-head",
            "resolver_hints": {"adr_ids": list(adrs), "decision_refs": list(refs), "topics": [], "paths": []},
        }

    def _strategy(self, **parameters):
        defaults = {
            "scope": "current", "lineage_depth": "all", "lineage_direction": "ancestor",
            "include_non_authoritative": False, "related_depth": 0, "detail": "decision",
            "semantic_gap_top_k": 0, "max_items": 40, "max_tokens": 16_000,
        }
        defaults.update(parameters)
        return {"schema": STRATEGY_SCHEMA, "strategy_id": "test", "family": "adr-structural", "parameters": defaults}

    def test_current_head_historical_lineage_convergence_and_repeatability(self):
        first = resolve_strategy(self._task(), self._strategy(), self.root)
        second = resolve_strategy(self._task(), self._strategy(), self.root)
        self.assertEqual(first["selected_adrs"][0]["authoritative_ref"], "mse_head:d1")
        self.assertIn("mse_old:d1", first["selected_refs"])
        self.assertIn({"source": "mse_head:d1", "target": "mse_b:d1", "type": "evolves"}, first["lineage_edges"])
        self.assertEqual(first["fingerprint"], second["fingerprint"])

    def test_multi_adr_nonauthoritative_states_related_and_limits(self):
        result = resolve_strategy(
            self._task(adrs=("adr_alpha", "adr_beta")),
            self._strategy(scope="full", include_non_authoritative=True, related_depth=1), self.root,
        )
        self.assertEqual({item["adr_id"] for item in result["selected_adrs"]}, {"adr_alpha", "adr_beta"})
        self.assertIn("mse_pending:d1", result["selected_refs"])
        self.assertIn("mse_rejected:d1", result["selected_refs"])
        self.assertTrue(any(edge["type"] == "related" for edge in result["typed_edges"]))
        self.assertTrue(result["related_edges"])
        self.assertFalse(any(edge["type"] == "related" for edge in result["lineage_edges"]))
        self.assertTrue(any(item["kind"] == "adr-event" for item in result["evidence"]))
        limited = resolve_strategy(self._task(), self._strategy(max_items=1), self.root)
        self.assertEqual(len(limited["evidence"]), 1)
        self.assertTrue(limited["omissions"])

    def test_missing_evidence_and_materialization(self):
        strategy = {"schema": STRATEGY_SCHEMA, "strategy_id": "oracle", "family": "oracle", "parameters": {}}
        result = resolve_strategy(self._task(adrs=(), refs=("mse_missing:d1",)), strategy, self.root)
        self.assertTrue(result["insufficient_evidence"])
        self.assertTrue(result["absence"])
        packet = materialize_packet(result)
        self.assertEqual(packet["strategy_fingerprint"], result["strategy_fingerprint"])

    def test_grid_covers_frozen_dimensions(self):
        grid = strategy_grid()
        families = {item["family"] for item in grid}
        self.assertEqual(families, {"search", "timeline", "retrieval-v1", "adr-structural", "adr-hybrid", "oracle"})
        hybrid = [item["parameters"] for item in grid if item["family"] == "adr-hybrid"]
        self.assertEqual({item["semantic_gap_top_k"] for item in hybrid}, {0, 3, 6})
        self.assertEqual({item["max_tokens"] for item in hybrid}, {2000, 4000, 8000, 16000})
        self.assertEqual({item["max_items"] for item in hybrid}, {8, 16, 32, 40})
        self.assertTrue(any(item["include_pending"] and not item["include_rejected"] for item in hybrid))
        self.assertTrue(any(item["include_rejected"] and not item["include_pending"] for item in hybrid))
        self.assertTrue(any(item["include_no_change"] and not item["include_pending"] for item in hybrid))
        timelines = [item["parameters"] for item in grid if item["family"] == "timeline"]
        self.assertEqual({item["graph_depth"] for item in timelines}, {1, 2})
        self.assertEqual({item["include_sections"] for item in timelines}, {False, True})
        retrieval = [item["parameters"] for item in grid if item["family"] == "retrieval-v1"]
        self.assertEqual({item["related_depth"] for item in retrieval}, {1, 2, 3})
        self.assertEqual({item["neighbouring_entries"] for item in retrieval}, {1, 4, 8})
        search = [item["parameters"] for item in grid if item["family"] == "search"]
        self.assertEqual({item["top_k"] for item in search}, {4, 8, 16})

    def test_timeline_uses_canonical_pack_and_separates_edges(self):
        strategy = {
            "schema": STRATEGY_SCHEMA, "strategy_id": "timeline", "family": "timeline",
            "parameters": {"graph_depth": 1, "edge_types": ["related", "evolves"], "include_sections": False, "max_entries": 20},
        }
        result = resolve_strategy(self._task(refs=("mse_head:d1",)), strategy, self.root)
        self.assertTrue(result["evidence"])
        self.assertFalse(any(edge["type"] == "related" for edge in result["lineage_edges"]))

    def test_sweep_resolves_twice_writes_unique_shard_and_resumes(self):
        output = self.root / "shards"
        paths = run_sweep([self._task()], [self._strategy()], self.root, output, workers=1)
        self.assertEqual(len(paths), 1)
        first_bytes = paths[0].read_bytes()
        shard = json.loads(first_bytes)
        self.assertTrue(shard["deterministic"])
        self.assertEqual(shard["result"]["fingerprint"], shard["repeat_fingerprint"])
        resumed = run_sweep([self._task()], [self._strategy()], self.root, output, workers=1)
        self.assertEqual(resumed, paths)
        self.assertEqual(paths[0].read_bytes(), first_bytes)


class ReducerTests(unittest.TestCase):
    def test_hard_gates_pareto_and_deterministic_tiebreak(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gold = {
                "schema": "context-gold.v1",
                "tasks": [{
                    "task_id": "CTX-01", "required_adr_ids": ["adr_alpha"],
                    "authoritative_refs": ["mse_head:d1"],
                    "required_lineage_edges": [], "relevant_refs": ["mse_head:d1"],
                    "distractor_refs": ["mse_noise:d1"], "expected_status": {"adr_alpha": "accepted"},
                    "insufficient_evidence": False, "allowed_citations": ["mse_head:d1", "mse_noise:d1"],
                    "expected_statuses": {"adr_alpha": "accepted"},
                }],
            }
            for suffix, sfp, tokens, latency in (("a", "sha256:a", 10, 2.0), ("b", "sha256:b", 10, 2.0)):
                result = {
                    "fingerprint": f"sha256:r{suffix}", "selected_adrs": [{"adr_id": "adr_alpha", "status": "accepted"}],
                    "selected_refs": ["mse_head:d1"], "lineage_edges": [], "absence": [],
                    "insufficient_evidence": False, "token_proxy": tokens,
                    "evidence": [{"ref": "mse_head:d1", "token_proxy": tokens}],
                }
                shard = {
                    "schema": SHARD_SCHEMA, "task_id": "CTX-01", "strategy_fingerprint": sfp,
                    "strategy": {"schema": STRATEGY_SCHEMA, "family": "oracle", "parameters": {}},
                    "deterministic": True, "result": result,
                    "repeat_fingerprint": result["fingerprint"], "timings_ms": [latency, latency],
                }
                (root / f"CTX-01--{suffix}.json").write_text(json.dumps(shard), encoding="utf-8")
            reduced = reduce_shards(root, gold, expected_strategy_fingerprints=["sha256:a", "sha256:b"])
            self.assertEqual(reduced["selected_strategy_fingerprint"], "sha256:a")
            self.assertEqual(reduced["pareto_frontier"], ["sha256:a", "sha256:b"])


if __name__ == "__main__":
    unittest.main()

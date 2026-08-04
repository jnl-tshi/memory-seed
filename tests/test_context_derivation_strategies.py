import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

EXPERIMENT = Path(__file__).parents[1] / "experiments" / "context-derivation"
sys.path.insert(0, str(EXPERIMENT))

from contracts import STRATEGY_SCHEMA, TASK_SCHEMA, fingerprint  # noqa: E402
from materialize import assemble_live_tasks, attach_task_packets, materialize_packet  # noqa: E402
from reduce import _gate, reduce_shards, reduction_payload_fingerprint  # noqa: E402
from strategies import (  # noqa: E402
    load_corpus, normalize_strategy, resolve_strategy, strategy_fingerprint,
    strategy_grid, strategy_manifest,
)
from sweep import (  # noqa: E402
    SHARD_SCHEMA, resolver_implementation_fingerprint, run_sweep,
    task_runtime,
)

from memory_seed.adr import AdrEvent, AdrPredecessor, AdrRecord, render_adr  # noqa: E402


def _event(kind, event_id, ref=None, *, predecessors=(), supporting=(), replacement=None):
    return AdrEvent(
        kind=kind,
        event_id=event_id,
        timestamp=f"2026-08-01T0{event_id[-1]}:00:00Z",
        source="write-time",
        decision_ref=ref,
        update_entry_id=ref.split(":", 1)[0] if ref else "mse_status",
        predecessors=tuple(predecessors),
        supporting_decisions=tuple(supporting),
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
        (self.root / "CONSTITUTION.md").write_text("# Test Constitution\n", encoding="utf-8")
        (self.root / ".memory-seed" / "topics.yaml").write_text(
            "schema_version: 2\n"
            "topics:\n"
            "  - slug: architecture\n"
            "    label: Architecture\n"
            "    description: Test architecture decisions.\n"
            "    status: active\n"
            "    axis: area\n"
            "    aliases: []\n",
            encoding="utf-8",
        )
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
                "topics:", "  - architecture",
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
                _event("revision-proposed", "adre_hea000000000000006", head, predecessors=[AdrPredecessor(a, f"link:{head}:evolves:{a}"), AdrPredecessor(b, f"link:{head}:evolves:{b}")], supporting=["mse_related:d1", "mse_support_missing:d1"]),
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
            "schema": TASK_SCHEMA, "task_id": task_id, "fixture": str(self.root),
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

    def _live_materialization_inputs(self, shard_dir):
        task = self._task()
        candidate_strategy = self._strategy()
        retrieval_strategy = {
            "schema": STRATEGY_SCHEMA, "strategy_id": "retrieval",
            "family": "retrieval-v1", "parameters": {},
        }
        run_sweep(
            [task], [candidate_strategy, retrieval_strategy], self.root,
            shard_dir, workers=1,
        )
        candidate = normalize_strategy(candidate_strategy)
        candidate_fingerprint = strategy_fingerprint(candidate)
        retrieval_fingerprint = strategy_fingerprint(retrieval_strategy)
        shards = [json.loads(path.read_text(encoding="utf-8")) for path in shard_dir.glob("*.json")]
        exemplar = shards[0]
        reduction = {
            "schema": "context-reduction.v1", "task_count": 1,
            "strategy_count": 2, "complete": True,
            "task_fingerprints": {task["task_id"]: exemplar["task_fingerprint"]},
            "runtime_fingerprints": {task["task_id"]: exemplar["runtime_fingerprint"]},
            "resolver_fingerprint": exemplar["resolver_fingerprint"],
            "shard_fingerprints": {
                f"{shard['task_id']}|{shard['strategy_fingerprint']}": fingerprint(shard)
                for shard in shards
            },
            "strategies": [{
                "strategy_fingerprint": candidate_fingerprint,
                "strategy": candidate, "eligible": True,
                "selection_eligible": True,
            }],
            "pareto_frontier": [candidate_fingerprint],
            "selected_strategy_fingerprint": candidate_fingerprint,
        }
        reduction["fingerprint"] = reduction_payload_fingerprint(reduction)
        manifest = {
            "schema": "context-candidate-manifest.v1",
            "strategy_fingerprint": candidate_fingerprint,
            "strategy": candidate,
            "reduction_fingerprint": reduction["fingerprint"],
        }
        return task, manifest, reduction, retrieval_fingerprint

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
        self.assertEqual(
            [{"source": "mse_related:d1", "target": "mse_head:d1", "type": "related"}],
            result["related_edges"],
        )
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

    def test_missing_support_marks_partial_structural_context_insufficient(self):
        result = resolve_strategy(self._task(), self._strategy(), self.root)
        self.assertTrue(result["evidence"])
        self.assertTrue(result["insufficient_evidence"])
        self.assertIn(
            {
                "source": "mse_related:d1",
                "target": "mse_head:d1",
                "type": "related",
            },
            result["related_edges"],
        )
        self.assertNotIn(
            {
                "source": "mse_support_missing:d1",
                "target": "mse_head:d1",
                "type": "related",
            },
            result["related_edges"],
        )
        self.assertFalse(any(edge["type"] == "related" for edge in result["lineage_edges"]))
        self.assertTrue(any(
            item["kind"] == "missing-decision-evidence"
            and "mse_support_missing:d1" in item["refs"]
            for item in result["absence"]
        ))

    def test_attaches_inline_packets_and_per_arm_accounting(self):
        retrieval = resolve_strategy(
            self._task(),
            {"schema": STRATEGY_SCHEMA, "strategy_id": "search", "family": "search", "parameters": {}},
            self.root,
        )
        candidate = resolve_strategy(self._task(), self._strategy(), self.root)
        payload = attach_task_packets(
            self._task(), retrieval_v1_result=retrieval, candidate_result=candidate
        )
        self.assertEqual(
            set(payload["packets"]), {"retrieval-v1-packet", "adr-candidate-packet"}
        )
        self.assertEqual(
            json.loads(payload["packets"]["adr-candidate-packet"])["selected_refs"],
            candidate["selected_refs"],
        )
        self.assertEqual(
            set(payload["included_refs_by_arm"]["retrieval-v1-packet"]),
            set(retrieval["selected_refs"]) | {item["adr_id"] for item in retrieval["selected_adrs"]},
        )
        self.assertEqual(
            payload["context_token_proxy_by_arm"]["adr-candidate-packet"],
            (len(payload["packets"]["adr-candidate-packet"].encode("utf-8")) + 3) // 4,
        )

    def test_assembles_all_fixed_arm_packets_from_frozen_shards(self):
        with tempfile.TemporaryDirectory() as temp:
            shard_dir = Path(temp)
            task, manifest, reduction, retrieval_fingerprint = self._live_materialization_inputs(shard_dir)
            live = assemble_live_tasks(
                {"tasks": [task]}, shard_dir, manifest, reduction,
                retrieval_fingerprint, fixture_base=self.root,
            )
        self.assertEqual("context-live-tasks.v1", live["schema"])
        self.assertEqual({"retrieval-v1-packet", "adr-candidate-packet"}, set(live["tasks"][0]["packets"]))

    def test_materialization_rejects_equally_stale_arms_after_corpus_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            shard_dir = Path(temp)
            task, manifest, reduction, retrieval_fingerprint = self._live_materialization_inputs(shard_dir)
            session = self.root / ".memory-seed" / "sessions" / "2026-08" / "2026-08-01.md"
            session.write_text(session.read_text(encoding="utf-8") + "\nCorpus changed.\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "stale"):
                assemble_live_tasks(
                    {"tasks": [task]}, shard_dir, manifest, reduction,
                    retrieval_fingerprint, fixture_base=self.root,
                )

    def test_materialization_rejects_tampered_reduction_and_candidate_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            shard_dir = Path(temp)
            task, manifest, reduction, retrieval_fingerprint = self._live_materialization_inputs(shard_dir)
            tampered = dict(reduction, task_count=2)
            with self.assertRaisesRegex(ValueError, "fingerprint is invalid"):
                assemble_live_tasks(
                    {"tasks": [task]}, shard_dir, manifest, tampered,
                    retrieval_fingerprint, fixture_base=self.root,
                )
            unbound = dict(manifest, reduction_fingerprint="sha256:wrong")
            with self.assertRaisesRegex(ValueError, "not bound"):
                assemble_live_tasks(
                    {"tasks": [task]}, shard_dir, unbound, reduction,
                    retrieval_fingerprint, fixture_base=self.root,
                )
            candidate_path = next(
                path for path in shard_dir.glob("*.json")
                if json.loads(path.read_text(encoding="utf-8"))["strategy_fingerprint"]
                == manifest["strategy_fingerprint"]
            )
            shard = json.loads(candidate_path.read_text(encoding="utf-8"))
            shard["timings_ms"] = [999.0, 999.0]
            candidate_path.write_text(json.dumps(shard), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not represented by the reduction"):
                assemble_live_tasks(
                    {"tasks": [task]}, shard_dir, manifest, reduction,
                    retrieval_fingerprint, fixture_base=self.root,
                )

    def test_grid_covers_frozen_dimensions(self):
        grid = strategy_grid()
        families = {item["family"] for item in grid}
        self.assertEqual(families, {"search", "timeline", "retrieval-v1", "adr-structural", "adr-hybrid", "oracle"})
        hybrid = [item["parameters"] for item in grid if item["family"] == "adr-hybrid"]
        self.assertEqual({item["semantic_gap_top_k"] for item in hybrid}, {0, 3, 6})
        self.assertEqual({item["max_tokens"] for item in hybrid}, {2000, 4000, 8000, 16000})
        self.assertEqual({item["max_items"] for item in hybrid}, {8, 16, 32, 40})
        self.assertTrue(any(item["max_items"] == 8 and item["max_tokens"] == 16000 for item in hybrid))
        self.assertTrue(any(item["include_pending"] and not item["include_rejected"] for item in hybrid))
        self.assertTrue(any(item["include_rejected"] and not item["include_pending"] for item in hybrid))
        self.assertTrue(any(item["include_no_change"] and not item["include_pending"] for item in hybrid))
        self.assertTrue(any(item["include_pending"] and item["include_no_change"] and not item["include_rejected"] for item in hybrid))
        timelines = [item["parameters"] for item in grid if item["family"] == "timeline"]
        self.assertEqual({item["graph_depth"] for item in timelines}, {1, 2})
        self.assertEqual({item["include_sections"] for item in timelines}, {False, True})
        retrieval = [item["parameters"] for item in grid if item["family"] == "retrieval-v1"]
        self.assertEqual({item["related_depth"] for item in retrieval}, {1, 2, 3})
        self.assertEqual({item["neighbouring_entries"] for item in retrieval}, {1, 4, 8})
        self.assertEqual({item["max_tokens"] for item in retrieval}, {2000, 4000, 8000, 16000})
        search = [item["parameters"] for item in grid if item["family"] == "search"]
        self.assertEqual({item["top_k"] for item in search}, {4, 8, 16})
        manifest = strategy_manifest()
        fingerprints = [item["strategy_fingerprint"] for item in manifest["strategies"]]
        self.assertEqual(len(fingerprints), len(set(fingerprints)))

    def test_timeline_uses_canonical_pack_and_separates_edges(self):
        strategy = {
            "schema": STRATEGY_SCHEMA, "strategy_id": "timeline", "family": "timeline",
            "parameters": {"graph_depth": 1, "edge_types": ["related", "evolves"], "include_sections": False, "max_entries": 20},
        }
        task = self._task(refs=("mse_head:d1",))
        task["resolver_hints"]["topics"] = ["architecture"]
        result = resolve_strategy(task, strategy, self.root)
        self.assertTrue(result["evidence"])
        self.assertFalse(any(edge["type"] == "related" for edge in result["lineage_edges"]))

    def test_retrieval_v1_fixture_has_required_constitution_and_evidence(self):
        strategy = {
            "schema": STRATEGY_SCHEMA, "strategy_id": "v1", "family": "retrieval-v1",
            "parameters": {"related_depth": 2, "neighbouring_entries": 4, "max_items": 40, "max_tokens": 16000},
        }
        task = self._task(refs=("mse_head:d1",))
        task["resolver_hints"]["topics"] = ["architecture"]
        result = resolve_strategy(task, strategy, self.root)
        self.assertTrue(result["evidence"])
        self.assertFalse(any(item.get("kind") == "retrieval-v1-missing" for item in result["absence"]))

    def test_sweep_resolves_twice_writes_unique_shard_and_resumes(self):
        output = self.root / "shards"
        paths = run_sweep([self._task()], [self._strategy()], self.root, output, workers=1)
        self.assertEqual(len(paths), 1)
        first_bytes = paths[0].read_bytes()
        shard = json.loads(first_bytes)
        self.assertTrue(shard["deterministic"])
        self.assertEqual(shard["result"]["fingerprint"], shard["repeat_fingerprint"])
        self.assertEqual(shard["resolver_fingerprint"], resolver_implementation_fingerprint())
        resumed = run_sweep([self._task()], [self._strategy()], self.root, output, workers=1)
        self.assertEqual(resumed, paths)
        self.assertEqual(paths[0].read_bytes(), first_bytes)
        changed = self._task()
        changed["question"] = "changed query"
        run_sweep([changed], [self._strategy()], self.root, output, workers=1)
        refreshed = json.loads(paths[0].read_text(encoding="utf-8"))
        self.assertNotEqual(shard["task_fingerprint"], refreshed["task_fingerprint"])

    def test_sweep_resume_rejects_tampered_repeat_and_resolver_fingerprints(self):
        output = self.root / "tampered-shards"
        task, strategy = self._task(), self._strategy()
        path = run_sweep([task], [strategy], self.root, output, workers=1)[0]
        shard = json.loads(path.read_text(encoding="utf-8"))
        shard["repeat_fingerprint"] = "sha256:tampered"
        path.write_text(json.dumps(shard), encoding="utf-8")
        run_sweep([task], [strategy], self.root, output, workers=1)
        repaired = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(repaired["repeat_fingerprint"], repaired["result"]["fingerprint"])
        repaired["resolver_fingerprint"] = "sha256:old-resolver"
        path.write_text(json.dumps(repaired), encoding="utf-8")
        run_sweep([task], [strategy], self.root, output, workers=1)
        repaired = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(repaired["resolver_fingerprint"], resolver_implementation_fingerprint())

    def test_missing_fixture_fails_closed_instead_of_using_parent_runtime(self):
        with self.assertRaisesRegex(ValueError, "missing .memory-seed"):
            task_runtime({"fixture": "does-not-exist"}, self.root)

    def test_atomic_shard_temp_name_does_not_repeat_long_destination(self):
        from sweep import _write_unique
        deep = self.root / ("nested-" + "x" * 80)
        destination = deep / ("CTX-01--" + "a" * 64 + ".json")
        _write_unique(destination, {"ok": True})
        self.assertEqual({"ok": True}, json.loads(destination.read_text(encoding="utf-8")))

    def test_sweep_resolves_each_task_against_its_own_fixture_runtime(self):
        fixture_base = self.root / "fixture-base"
        populated = fixture_base / "populated"
        empty = fixture_base / "empty"
        shutil.copytree(self.root / ".memory-seed", populated / ".memory-seed")
        (empty / ".memory-seed" / "sessions").mkdir(parents=True)
        (empty / ".memory-seed" / "decisions").mkdir(parents=True)
        first = self._task(task_id="CTX-01")
        first["fixture"] = "populated"
        second = self._task(task_id="CTX-02")
        second["fixture"] = "empty"
        oracle = {
            "schema": STRATEGY_SCHEMA, "strategy_id": "oracle",
            "family": "oracle", "parameters": {},
        }
        paths = run_sweep(
            [first, second], [oracle], fixture_base,
            self.root / "multi-runtime-shards", workers=1,
        )
        shards = {json.loads(path.read_text(encoding="utf-8"))["task_id"]: json.loads(path.read_text(encoding="utf-8")) for path in paths}
        self.assertTrue(shards["CTX-01"]["result"]["evidence"])
        self.assertFalse(shards["CTX-02"]["result"]["evidence"])
        self.assertTrue(shards["CTX-02"]["result"]["insufficient_evidence"])
        self.assertEqual(task_runtime({"fixture": str(populated)}, fixture_base), populated.resolve())


class ReducerTests(unittest.TestCase):
    def _write_valid_shards(self, root):
        gold = {
            "schema": "context-gold.v1",
            "tasks": [{
                "task_id": "CTX-01", "required_adr_ids": ["adr_alpha"],
                "authoritative_refs": ["mse_head:d1"],
                "required_lineage_edges": [], "relevant_refs": ["mse_head:d1"],
                "distractor_refs": ["mse_noise:d1"],
                "insufficient_evidence": False,
                "allowed_citations": ["mse_head:d1", "mse_noise:d1"],
                "expected_statuses": {"adr_alpha": "accepted"},
            }],
        }
        strategies = [
            {"schema": STRATEGY_SCHEMA, "family": "adr-structural", "parameters": {"max_items": 8}},
            {"schema": STRATEGY_SCHEMA, "family": "adr-structural", "parameters": {"max_items": 16}},
            {"schema": STRATEGY_SCHEMA, "family": "oracle", "parameters": {}},
        ]
        paths, fingerprints = [], []
        for index, strategy in enumerate(strategies):
            normalized = normalize_strategy(strategy)
            strategy_fp = strategy_fingerprint(normalized)
            fingerprints.append(strategy_fp)
            result = {
                "schema": "context-strategy-result.v1", "task_id": "CTX-01",
                "strategy": normalized, "strategy_fingerprint": strategy_fp,
                "selected_adrs": [{
                    "adr_id": "adr_alpha", "status": "accepted",
                    "authoritative_ref": "mse_head:d1",
                }],
                "selected_refs": ["mse_head:d1"], "lineage_edges": [],
                "related_edges": [], "citations": [], "absence": [],
                "insufficient_evidence": False, "token_proxy": 10 if index < 2 else 1,
                "evidence": [{"ref": "mse_head:d1", "token_proxy": 10 if index < 2 else 1}],
                "elapsed_ms": 2.0 if index < 2 else 1.0,
            }
            result["fingerprint"] = fingerprint({
                key: value for key, value in result.items()
                if key not in {"elapsed_ms", "fingerprint"}
            })
            shard = {
                "schema": SHARD_SCHEMA, "task_id": "CTX-01",
                "task_fingerprint": "sha256:task",
                "runtime_fingerprint": "sha256:runtime",
                "resolver_fingerprint": "sha256:resolver",
                "strategy_fingerprint": strategy_fp, "strategy": normalized,
                "deterministic": True, "result": result,
                "repeat_fingerprint": result["fingerprint"],
                "timings_ms": [result["elapsed_ms"], result["elapsed_ms"]],
            }
            path = root / f"CTX-01--{index}.json"
            path.write_text(json.dumps(shard), encoding="utf-8")
            paths.append(path)
        return gold, fingerprints, paths

    def test_missing_evidence_gate_requires_the_named_reference(self):
        result = {
            "selected_adrs": [], "selected_refs": [], "lineage_edges": [], "related_edges": [],
            "absence": [{"kind": "missing-decision-evidence", "refs": ["mse_wrong:d1"]}],
            "insufficient_evidence": True, "citations": [], "evidence": [],
        }
        gold = {"insufficient_evidence": True, "required_missing_refs": ["mse_expected:d1"]}
        self.assertIn("wrong-missing-evidence-ref", _gate(result, gold))

    def test_historical_ref_does_not_mask_wrong_authoritative_head(self):
        result = {
            "selected_adrs": [{
                "adr_id": "adr_alpha", "status": "accepted",
                "authoritative_ref": "mse_old:d1",
            }],
            "selected_refs": ["mse_old:d1", "mse_head:d1"],
            "lineage_edges": [], "related_edges": [], "evidence": [],
            "absence": [], "insufficient_evidence": False,
        }
        gold = {
            "required_adr_ids": ["adr_alpha"], "authoritative_refs": ["mse_head:d1"],
            "required_lineage_edges": [], "expected_statuses": {"adr_alpha": "accepted"},
            "insufficient_evidence": False, "allowed_citations": [],
        }
        self.assertIn("wrong-authoritative-head", _gate(result, gold))

    def test_hard_gates_pareto_and_deterministic_tiebreak(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gold, fingerprints, _ = self._write_valid_shards(root)
            reduced = reduce_shards(root, gold, expected_strategy_fingerprints=fingerprints)
            candidate_fingerprints = fingerprints[:2]
            self.assertEqual(reduced["selected_strategy_fingerprint"], min(candidate_fingerprints))
            self.assertEqual(reduced["pareto_frontier"], sorted(candidate_fingerprints))
            oracle = next(item for item in reduced["strategies"] if item["strategy_fingerprint"] == fingerprints[2])
            self.assertTrue(oracle["eligible"])
            self.assertFalse(oracle["selection_eligible"])
            self.assertEqual(oracle["selection_exclusion"], "oracle-lower-bound-only")
            self.assertEqual(reduced["resolver_fingerprint"], "sha256:resolver")

    def test_reducer_rejects_missing_mixed_and_tampered_provenance(self):
        mutations = (
            ("missing task fingerprint", lambda shard: shard.pop("task_fingerprint"), "missing task_fingerprint"),
            ("mixed task", lambda shard: shard.__setitem__("task_fingerprint", "sha256:other"), "mixed task/runtime"),
            ("mixed runtime", lambda shard: shard.__setitem__("runtime_fingerprint", "sha256:other"), "mixed task/runtime"),
            ("mixed resolver", lambda shard: shard.__setitem__("resolver_fingerprint", "sha256:other"), "mixed resolver"),
            ("tampered strategy", lambda shard: shard["strategy"]["parameters"].__setitem__("max_items", 40), "tampered strategy fingerprint"),
            ("tampered result", lambda shard: shard["result"]["selected_refs"].append("mse_tampered:d1"), "tampered result fingerprint"),
        )
        for label, mutate, message in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                gold, fingerprints, paths = self._write_valid_shards(root)
                shard = json.loads(paths[0].read_text(encoding="utf-8"))
                mutate(shard)
                paths[0].write_text(json.dumps(shard), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, message):
                    reduce_shards(root, gold, expected_strategy_fingerprints=fingerprints)

    def test_reducer_rejects_conflicting_duplicate_cells(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            gold, fingerprints, paths = self._write_valid_shards(root)
            duplicate = json.loads(paths[0].read_text(encoding="utf-8"))
            duplicate["timings_ms"] = [3.0, 3.0]
            (root / "duplicate.json").write_text(json.dumps(duplicate), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "conflicting duplicate shard"):
                reduce_shards(root, gold, expected_strategy_fingerprints=fingerprints)


if __name__ == "__main__":
    unittest.main()

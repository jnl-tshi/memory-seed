"""Provider-free gates for the one-shot unscored context pilot."""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1] / "experiments" / "context-derivation"
sys.path.insert(0, str(HERE))

import collect
import mcp_wrapper
import pilot
import pilot_spec
import run
import score


class PilotTests(unittest.TestCase):
    def test_spec_is_exactly_eight_unscored_cells_outside_benchmark(self):
        self.assertEqual(8, len(pilot_spec.PILOT_CELLS))
        self.assertEqual(8, len(set(pilot_spec.PILOT_CELLS)))
        self.assertTrue(all(cell[2] == 1 for cell in pilot_spec.PILOT_CELLS))
        self.assertEqual("PILOT-01", pilot_spec.PILOT_TASK_ID)
        self.assertNotIn("PILOT-01", {f"CTX-{number:02d}" for number in range(1, 13)})

    def test_fixture_and_packets_are_deterministic_and_gold_is_not_visible(self):
        with tempfile.TemporaryDirectory() as left, tempfile.TemporaryDirectory() as right:
            lf, lt, lg, _lgp = pilot.build_runtime(Path(left))
            rf, rt, rg, _rgp = pilot.build_runtime(Path(right))
            lp = json.loads(lt.read_text(encoding="utf-8")); rp = json.loads(rt.read_text(encoding="utf-8"))
            self.assertEqual(lp["fingerprint"], rp["fingerprint"])
            self.assertEqual(lg, rg)
            self.assertEqual(pilot._fingerprint_tree(lf), pilot._fingerprint_tree(rf))
            self.assertFalse(any("gold" in path.name.lower() for path in lf.rglob("*")))
            row = lp["tasks"][0]
            self.assertIn('"type":"evolves"', row["packets"]["adr-candidate-packet"])
            self.assertIn('"type":"related"', row["packets"]["adr-candidate-packet"])
            refs = [ref for ref in pilot_spec.ALL_REFS if ref.startswith("mse_")]
            self.assertTrue(all(re.fullmatch(r"mse_[0-9a-hjkmnp-tv-z]{16}:d1", ref) for ref in refs))
            excerpt = json.dumps({"result": {"refs": refs}})
            _text, extracted = collect.transcript_evidence([{"item": {"type": "mcp_tool_call", "result": excerpt}}])
            self.assertEqual(sorted(refs), extracted)

    def test_pilot_gold_byte_copy_is_rejected_even_with_benign_filename(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); gold = root / "private.json"; visible = root / "fixture"; visible.mkdir()
            gold.write_bytes(b'{"answer":"private"}\n')
            (visible / "notes.txt").write_bytes(gold.read_bytes())
            with self.assertRaisesRegex(ValueError, "gold bytes leaked"):
                pilot.assert_pilot_gold_isolated(gold, visible)

    def test_real_interactive_chains_survive_sanitization_and_score_complete(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); fixture, _tasks, gold, _gold_path = pilot.build_runtime(root / "runtime")
            answer = {
                "schema": "context-answer.v1", "adr_ids": ["adr_pilot_local_index"],
                "authoritative_refs": ["mse_bcde2345fghj6789:d1"],
                "adr_statuses": {"adr_pilot_local_index": "accepted"},
                "lineage_edges": [pilot_spec.LINEAGE], "related_edges": [pilot_spec.RELATED],
                "citations": ["mse_bcde2345fghj6789:d1"], "explanation": "fixture proof",
                "insufficient_evidence": False, "missing_refs": [],
            }
            chains = {
                "search-mcp": [
                    ("memory_search", {"query": "incremental indexing", "top_k": 8}),
                    ("memory_get_chunk", {"chunk_id": "mse_bcde2345fghj6789"}),
                ],
                "adr-mcp-workflow": [
                    ("memory_adrs_list", {}),
                    ("memory_adr_show", {"adr_id": "adr_pilot_local_index"}),
                ],
            }
            allowed_refs = {
                *pilot_spec.ALL_REFS, "mse_defg4567hjkm8901:d1",
            }
            for arm, calls in chains.items():
                raw_lines = []
                for index, (name, arguments) in enumerate(calls):
                    response = mcp_wrapper.handle_message(
                        {"jsonrpc": "2.0", "id": index, "method": "tools/call", "params": {"name": name, "arguments": arguments}},
                        arm=arm, fixture_cwd=fixture,
                    )
                    self.assertIn("result", response)
                    raw_lines.append(json.dumps({"type": "item.completed", "item": {"type": "mcp_tool_call", "tool": name, "result": response["result"]}}))
                sanitized = run.sanitize_pilot_stream("\n".join(raw_lines) + "\n")
                events = [json.loads(line) for line in sanitized.splitlines()]
                _excerpt, refs = collect.transcript_evidence(events)
                self.assertNotIn("adr_id", refs); self.assertTrue(set(refs) <= allowed_refs)
                required_observed = set(pilot_spec.ALL_REFS if arm == "adr-mcp-workflow" else pilot_spec.ALL_REFS[1:])
                self.assertTrue(required_observed <= set(refs))
                run_dir = root / arm; run_dir.mkdir()
                (run_dir / "transcript.jsonl").write_text(sanitized, encoding="utf-8")
                (run_dir / "final_answer.txt").write_text(json.dumps(answer), encoding="utf-8")
                manifest = {
                    "run_id": arm, "task_id": "PILOT-01", "agent": "codex", "arm": arm,
                    "repetition": 1, "pilot": True, "scored": False, "transcript": "transcript.jsonl",
                    "final_answer": "final_answer.txt", "integrity_failures": [], "failure_classification": None,
                }
                (run_dir / "RUN_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
                scored = score.score_run(pilot._pilot_row(run_dir), gold["tasks"][0])
                self.assertTrue(scored["citation_resolves"], arm)
                self.assertTrue(scored["complete_correct"], arm)

    def test_output_requires_empty_resolved_temp_directory(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "pilot-output"
            self.assertEqual(root.absolute(), pilot_spec.safe_absent_temp_path(root, HERE))
            root.mkdir(); (root / "occupied").write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "nonexistent"):
                pilot_spec.safe_absent_temp_path(root, HERE)
            empty = Path(temp) / "already-empty"; empty.mkdir()
            with self.assertRaisesRegex(ValueError, "nonexistent"):
                pilot_spec.safe_absent_temp_path(empty, HERE)
        with self.assertRaisesRegex(ValueError, "OS temporary"):
            pilot_spec.safe_absent_temp_path(HERE / "pilot-output", HERE)

    def test_claim_binds_exact_task_fixture_and_output_identities(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); runtime = root / "runtime"; runtime.mkdir()
            fixture, tasks_path, _gold, _gold_path = pilot.build_runtime(runtime)
            output = root / "output"; claim = root / "claim"
            payload = json.loads(tasks_path.read_text(encoding="utf-8")); auth = "bound-auth"
            with patch.object(pilot, "PILOT_CLAIM_PATH", claim):
                pilot._consume_claim(auth=auth, tasks_fingerprint=payload["fingerprint"], tasks_path=tasks_path, fixture=fixture, output=output)
                pilot._create_output_authority(output, auth)
            with patch.object(run, "PILOT_CLAIM_PATH", claim):
                self.assertTrue(run._pilot_claim_authorized(auth=auth, tasks=payload, tasks_path=tasks_path, output=output, cell=pilot_spec.PILOT_CELLS[0]))
                original = tasks_path.read_bytes()
                second_fixture = root / "other-fixture"; second_fixture.mkdir()
                rewritten = json.loads(original); rewritten["tasks"][0]["fixture"] = str(second_fixture)
                tasks_path.write_text(json.dumps(rewritten), encoding="utf-8")
                self.assertFalse(run._pilot_claim_authorized(auth=auth, tasks=rewritten, tasks_path=tasks_path, output=output, cell=pilot_spec.PILOT_CELLS[0]))
                tasks_path.write_bytes(original)
                (output / pilot_spec.PILOT_AUTHORITY_MARKER).unlink(); output.rmdir(); output.mkdir()
                self.assertFalse(run._pilot_claim_authorized(auth=auth, tasks=payload, tasks_path=tasks_path, output=output, cell=pilot_spec.PILOT_CELLS[0]))

    def test_output_insertion_and_reparse_are_rejected_before_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); output = root / "output"; output.mkdir()
            (output / "raced.txt").write_text("inserted", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "nonexistent"):
                pilot_spec.safe_absent_temp_path(output, HERE)
            target = root / "target"; target.mkdir(); link = root / "link"
            try: link.symlink_to(target, target_is_directory=True)
            except OSError: return
            with self.assertRaisesRegex(ValueError, "resolved|reparse"):
                pilot_spec.safe_absent_temp_path(link, HERE)

    def test_claim_to_mkdir_gap_rejects_creation_content_and_reparse_without_queues(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); runtime = root / "runtime"; runtime.mkdir()
            fixture, tasks, _gold, _gold_path = pilot.build_runtime(runtime)
            payload = json.loads(tasks.read_text(encoding="utf-8")); claim = root / "claim"
            for mode in ("empty", "content", "reparse"):
                output = root / f"output-{mode}"
                with patch.object(pilot, "PILOT_CLAIM_PATH", claim), patch.object(pilot, "_execute_queues") as queues:
                    pilot._consume_claim(auth="a", tasks_fingerprint=payload["fingerprint"], tasks_path=tasks, fixture=fixture, output=output)
                    if mode == "reparse":
                        target = root / "target-gap"; target.mkdir(exist_ok=True)
                        try: output.symlink_to(target, target_is_directory=True)
                        except OSError:
                            claim.unlink(); continue
                    else:
                        output.mkdir()
                        if mode == "content": (output / "inserted").write_text("race", encoding="utf-8")
                    with self.assertRaises((FileExistsError, RuntimeError, ValueError)):
                        pilot._create_output_authority(output, "a")
                    queues.assert_not_called()
                claim.unlink()

    def test_claim_to_mkdir_parent_reparse_swap_never_launches_queues(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); runtime = root / "runtime"; runtime.mkdir()
            fixture, tasks, _gold, _gold_path = pilot.build_runtime(runtime)
            payload = json.loads(tasks.read_text(encoding="utf-8"))
            parent = root / "output-parent"; parent.mkdir(); output = parent / "pilot-output"
            claim = root / "claim"; target = root / "junction-target"; target.mkdir()
            with patch.object(pilot, "PILOT_CLAIM_PATH", claim), patch.object(pilot, "_execute_queues") as queues:
                pilot._consume_claim(auth="a", tasks_fingerprint=payload["fingerprint"], tasks_path=tasks, fixture=fixture, output=output)
                saved_parent = root / "saved-output-parent"; parent.rename(saved_parent)
                try:
                    parent.symlink_to(target, target_is_directory=True)
                    context = nullcontext()
                except OSError:
                    parent.mkdir()
                    original_is_symlink = Path.is_symlink
                    context = patch.object(
                        Path, "is_symlink", autospec=True,
                        side_effect=lambda value: True if value.absolute() == parent.absolute() else original_is_symlink(value),
                    )
                with context, self.assertRaisesRegex(RuntimeError, "resolved path|reparse point"):
                    pilot._create_output_authority(output, "a")
                queues.assert_not_called()

    def test_archived_claude_requires_exact_file_hash_and_non_reparse(self):
        with tempfile.TemporaryDirectory() as temp:
            executable = Path(temp) / "claude.exe"; executable.write_bytes(b"approved archive")
            digest = hashlib.sha256(executable.read_bytes()).hexdigest().upper()
            with patch.object(pilot_spec, "PILOT_CLAUDE_SHA256", digest):
                self.assertEqual(executable.resolve(), pilot_spec.verified_claude_executable(executable))
            with self.assertRaisesRegex(ValueError, "SHA256"):
                pilot_spec.verified_claude_executable(executable)
            link = Path(temp) / "claude-link.exe"
            try:
                link.symlink_to(executable)
            except OSError:
                return
            with patch.object(pilot_spec, "PILOT_CLAUDE_SHA256", digest), self.assertRaisesRegex(ValueError, "non-reparse"):
                pilot_spec.verified_claude_executable(link)

    def test_global_claim_is_atomic_and_prevents_a_second_or_ninth_launch(self):
        with tempfile.TemporaryDirectory() as temp:
            claim = Path(temp) / "pilot.claim"; output = Path(temp) / "out"
            fixture = Path(temp) / "fixture"; fixture.mkdir()
            tasks_path = Path(temp) / "tasks.json"; tasks_path.write_text("{}", encoding="utf-8")
            errors: list[str] = []
            def consume():
                try:
                    pilot._consume_claim(auth="secret", tasks_fingerprint="fp", tasks_path=tasks_path, fixture=fixture, output=output)
                except RuntimeError:
                    errors.append("consumed")
            with patch.object(pilot, "PILOT_CLAIM_PATH", claim):
                threads = [threading.Thread(target=consume) for _ in range(2)]
                for thread in threads: thread.start()
                for thread in threads: thread.join()
                self.assertEqual(["consumed"], errors)
                payload = json.loads(claim.read_text(encoding="utf-8"))
                self.assertEqual(8, len(payload["cells"]))
                with self.assertRaisesRegex(RuntimeError, "already been consumed"):
                    consume_direct = pilot._consume_claim(auth="secret", tasks_fingerprint="fp", tasks_path=tasks_path, fixture=fixture, output=output)
            def cell_path(cell):
                agent, arm, repetition = cell
                return claim.with_name(f"{claim.name}.{agent}.{arm}.r{repetition}.cell")
            with patch.object(pilot, "pilot_cell_claim_path", side_effect=cell_path), patch.object(run, "pilot_cell_claim_path", side_effect=cell_path):
                run._consume_pilot_cell_claim(pilot_spec.PILOT_CELLS[0])
                writer_bytes = cell_path(pilot_spec.PILOT_CELLS[0]).read_bytes()
                self.assertEqual(b"consumed\n", writer_bytes)
                self.assertEqual("636f6e73756d65640a", writer_bytes.hex())
                with self.assertRaisesRegex(RuntimeError, "already been consumed"):
                    run._consume_pilot_cell_claim(pilot_spec.PILOT_CELLS[0])
                for cell in pilot.PILOT_CELLS[1:]:
                    path = cell_path(cell); path.write_bytes(b"consumed\n")
                self.assertTrue(pilot._claims_complete())
                cell_path(pilot_spec.PILOT_CELLS[-1]).write_bytes(b"wrong\n")
                self.assertFalse(pilot._claims_complete())

    def test_two_serial_queues_stop_unlaunched_cells_on_containment(self):
        stop = threading.Event(); calls: list[tuple[str, str]] = []
        def fake(agent, arm, **kwargs):
            if kwargs["stop"].is_set():
                return {"cell": [agent, arm, 1], "not_launched": "containment_stop"}
            calls.append((agent, arm))
            if agent == "claude" and arm == pilot.ARMS[0]:
                kwargs["stop"].set()
                return {"cell": [agent, arm, 1], "containment_failure": "child_integrity"}
            return {"cell": [agent, arm, 1]}
        with patch.object(pilot, "_run_cell", side_effect=fake):
            rows = pilot._queue("claude", output=Path("x"), tasks=Path("x"), claude_executable=Path("x"), pins={}, auth="x", stop=stop, timeout=1)
        self.assertEqual(1, len(calls)); self.assertEqual(3, sum("not_launched" in row for row in rows))

    def test_gold_mutation_is_a_containment_failure_before_next_queue_cell(self):
        with tempfile.TemporaryDirectory() as temp:
            gold = Path(temp) / "gold.json"; gold.write_text("before", encoding="utf-8")
            before = hashlib.sha256(gold.read_bytes()).hexdigest(); stop = threading.Event(); launched = []
            def check(): return hashlib.sha256(gold.read_bytes()).hexdigest() == before
            def fake(agent, arm, **kwargs):
                if kwargs["stop"].is_set(): return {"cell": [agent, arm, 1], "not_launched": "containment_stop"}
                launched.append(arm)
                gold.write_text("mutated", encoding="utf-8")
                if not kwargs["containment_check"](): kwargs["stop"].set()
                return {"cell": [agent, arm, 1], "containment_failure": "child_integrity"}
            with patch.object(pilot, "_run_cell", side_effect=fake):
                rows = pilot._queue("codex", output=Path("x"), tasks=Path("x"), claude_executable=Path("x"), pins={}, auth="x", stop=stop, timeout=1, containment_check=check)
            self.assertEqual([pilot.ARMS[0]], launched)
            self.assertEqual(3, sum("not_launched" in row for row in rows))

    def test_snapshot_read_exception_stops_queue_with_explicit_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp); arm = "retrieval-v1-packet"; run_dir = output / "child"; run_dir.mkdir()
            manifest = {"run_id": "child", "task_id": "PILOT-01", "agent": "claude", "arm": arm, "repetition": 1, "pilot": True, "scored": False, "transcript": "transcript.jsonl", "final_answer": "final_answer.txt", "integrity_failures": [], "parent_isolated": True, "fixture_isolated": True}
            (run_dir / "RUN_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
            result = run.CappedProcessResult([], 0, json.dumps({"output": str(run_dir)}) + "\n", "", overflow=False, timed_out=False)
            stop = threading.Event()
            with patch.object(pilot.subject_run, "capped_subprocess", return_value=result):
                receipt = pilot._run_cell(
                    "claude", arm, output=output, tasks=Path(temp) / "tasks.json",
                    claude_executable=Path(temp) / "claude.exe",
                    pins={"claude": {"model": "m", "cli_version": "v", "effort": None}},
                    auth="a", stop=stop, timeout=10,
                    containment_check=lambda: (_ for _ in ()).throw(FileNotFoundError("gold deleted")),
                )
            self.assertTrue(stop.is_set())
            self.assertEqual("containment_snapshot_read_failure", receipt["containment_failure"])

    def test_scheduler_submits_two_serial_ordered_queues_without_retries(self):
        lock = threading.Lock(); active = 0; maximum = 0; submissions = []
        def fake_queue(agent, **_kwargs):
            nonlocal active, maximum
            with lock:
                active += 1; maximum = max(maximum, active); submissions.append(agent)
            time.sleep(0.03)
            with lock: active -= 1
            return [{"manifest_cell": [agent, arm, 1], "run_dir": f"x/{agent}-{arm}"} for arm in pilot.ARMS]
        with patch.object(pilot, "_queue", side_effect=fake_queue):
            receipts = pilot._execute_queues({})
        self.assertEqual(["claude", "codex"], submissions)
        self.assertEqual(2, maximum); self.assertEqual(8, len(receipts))
        self.assertTrue(pilot._canonical_summary_order([tuple(row["manifest_cell"]) for row in receipts]))

    def test_main_runs_exact_eight_mocked_cells_with_canonical_summary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); output = root / "output"; claim = root / "pilot.claim"; executable = root / "claude.exe"; executable.write_bytes(b"mock")
            matrix = {"pins": {
                "claude": {"model": "claude-sonnet-5", "cli_version": "2.1.221", "effort": None},
                "codex": {"model": "gpt-5.6-luna", "cli_version": "codex-cli 0.146.0", "effort": "medium"},
            }}
            lock = threading.Lock(); active = 0; maximum = 0; per_agent = {"claude": 0, "codex": 0}; calls = []
            def cell_path(cell):
                agent, arm, repetition = cell
                return root / f"{agent}-{arm}-r{repetition}.cell"
            def fake_cell(agent, arm, **kwargs):
                nonlocal active, maximum
                with lock:
                    active += 1; per_agent[agent] += 1; maximum = max(maximum, active); calls.append((agent, arm, 1))
                time.sleep(0.01)
                run_dir = output / f"{agent}-{arm}"; run_dir.mkdir()
                expected_answer = {
                    "schema": "context-answer.v1", "adr_ids": ["adr_pilot_local_index"],
                    "authoritative_refs": ["mse_bcde2345fghj6789:d1"],
                    "adr_statuses": {"adr_pilot_local_index": "accepted"},
                    "lineage_edges": [pilot_spec.LINEAGE], "related_edges": [pilot_spec.RELATED],
                    "citations": ["mse_bcde2345fghj6789:d1"], "explanation": "mock",
                    "insufficient_evidence": False, "missing_refs": [],
                }
                evidence = json.dumps({"refs": pilot_spec.ALL_REFS})
                (run_dir / "transcript.jsonl").write_text(json.dumps({"item": {"type": "mcp_tool_call", "tool": "memory_search", "result": evidence}}) + "\n", encoding="utf-8")
                (run_dir / "final_answer.txt").write_text(json.dumps(expected_answer), encoding="utf-8")
                manifest = {
                    "run_id": run_dir.name, "task_id": "PILOT-01", "agent": agent, "arm": arm,
                    "repetition": 1, "pilot": True, "scored": False, "transcript": "transcript.jsonl",
                    "final_answer": "final_answer.txt", "integrity_failures": [], "parent_isolated": True,
                    "fixture_isolated": True, "included_refs": pilot_spec.ALL_REFS,
                    "failure_classification": None, "input_tokens": 1, "output_tokens": 1,
                }
                (run_dir / "RUN_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
                cell_path((agent, arm, 1)).write_bytes(b"consumed\n")
                with lock: active -= 1
                return {"cell": [agent, arm, 1], "manifest_cell": [agent, arm, 1], "returncode": 0, "run_dir": str(run_dir), "containment_failure": None}
            observed_versions = [("2.1.221", "2.1.221"), ("codex-cli 0.146.0", "codex-cli 0.146.0")]
            with patch.object(pilot, "PILOT_CLAIM_PATH", claim), patch.object(pilot, "pilot_cell_claim_path", side_effect=cell_path), patch.object(
                pilot, "safe_absent_temp_path", return_value=output
            ), patch.object(pilot, "verified_claude_executable", return_value=executable), patch.object(
                pilot, "live_execution_approved", return_value=True
            ), patch.object(pilot, "live_pin_matches", return_value=True), patch.object(
                pilot, "load_json", return_value=matrix
            ), patch.object(pilot.subject_run, "installed_cli_version", side_effect=observed_versions), patch.object(
                pilot, "_protected_snapshot", return_value={"repo": "r", "experiment": "e", "gold": "g", "fixture": "f"}
            ), patch.object(pilot, "_run_cell", side_effect=fake_cell):
                code = pilot.main(["--owner-approved", "--output", str(output), "--claude-executable", str(executable), "--timeout", "30"])
            self.assertEqual(0, code); self.assertEqual(8, len(calls)); self.assertEqual(8, len(set(calls)))
            for agent in ("claude", "codex"):
                self.assertEqual(list(pilot.ARMS), [arm for called_agent, arm, _rep in calls if called_agent == agent])
            self.assertEqual(2, maximum); self.assertEqual({"claude": 4, "codex": 4}, per_agent)
            summary = json.loads((output / "PILOT_SUMMARY.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["passed"]); self.assertEqual(8, summary["launched_calls"])
            self.assertEqual(list(pilot_spec.PILOT_CELLS), [(row["agent"], row["arm"], row["repetition"]) for row in summary["cells"]])
            self.assertTrue(summary["gold_used"]); self.assertEqual(0, summary["judges_run"])
            self.assertFalse(summary["normal_scoring_run"])
            self.assertIsNone(summary["usage"]["cost_usd"])

    def test_pilot_row_marks_zero_call_interactive_manifest_as_protocol_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            run_dir = Path(temp)
            manifest = {
                "run_id": "run", "task_id": "PILOT-01", "agent": "claude",
                "arm": "search-mcp", "repetition": 1, "pilot": True, "scored": False,
                "transcript": "transcript.jsonl", "final_answer": "final_answer.txt",
                "integrity_failures": [], "protocol_failures": ["interactive_no_mcp_calls"],
                "failure_classification": "pilot_protocol_failure",
            }
            (run_dir / "RUN_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
            (run_dir / "transcript.jsonl").write_text("", encoding="utf-8")
            (run_dir / "final_answer.txt").write_text(json.dumps({
                "schema": "context-answer.v1", "adr_ids": [], "authoritative_refs": [],
                "adr_statuses": {}, "lineage_edges": [], "related_edges": [],
                "citations": [], "explanation": "none", "insufficient_evidence": True,
                "missing_refs": [],
            }), encoding="utf-8")
            row = pilot._pilot_row(run_dir)
            self.assertEqual("interactive_no_mcp_calls", row["protocol_failure"])
            self.assertEqual("pilot_protocol_failure", row["harness_failure"])

    def test_usage_summary_preserves_unknown_cost(self):
        self.assertEqual(
            {"input_tokens": 3, "output_tokens": 4, "cost_usd": None},
            pilot._usage_summary([{"input_tokens": 3, "output_tokens": 4, "cost_usd": None}]),
        )
        self.assertEqual(
            1.25,
            pilot._usage_summary([{"cost_usd": None}, {"cost_usd": 1.25}])["cost_usd"],
        )

    def test_manifest_validation_rejects_wrong_cell_order_and_scored_flag(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp); run_dir = output / "run"; run_dir.mkdir()
            base = {"run_id": "run", "task_id": "PILOT-01", "agent": "claude", "arm": pilot.ARMS[0], "repetition": 1, "pilot": True, "scored": False, "transcript": "transcript.jsonl", "final_answer": "final_answer.txt"}
            self.assertEqual(("claude", pilot.ARMS[0], 1), pilot._validated_manifest_cell(base, ("claude", pilot.ARMS[0], 1), run_dir, output))
            self.assertIsNone(pilot._validated_manifest_cell({**base, "arm": pilot.ARMS[1]}, ("claude", pilot.ARMS[0], 1), run_dir, output))
            self.assertIsNone(pilot._validated_manifest_cell({**base, "scored": True}, ("claude", pilot.ARMS[0], 1), run_dir, output))
            ordered = list(pilot_spec.PILOT_CELLS); ordered[0], ordered[1] = ordered[1], ordered[0]
            self.assertFalse(pilot._canonical_summary_order(ordered))

    def test_pilot_stream_strips_tool_inputs_and_malformed_raw_lines(self):
        raw = "not-json-secret\n" + json.dumps({"type": "mcp_tool_call", "tool": "memory_search", "arguments": {"query": "secret"}, "cwd": "C:\\private\\cwd", "provider_metadata": "SENTINEL", "result": {"content": [{"type": "text", "text": "mse_abcd1234efgh5678:d1 C:\\private\\evidence \\\\server\\share\\private.txt"}], "metadata": "SENTINEL"}, "usage": {"input_tokens": 9}}) + "\n"
        cleaned = run.sanitize_pilot_stream(raw)
        self.assertNotIn("not-json-secret", cleaned); self.assertNotIn('"query"', cleaned)
        self.assertIn("memory_search", cleaned); self.assertIn('"input_tokens":9', cleaned)
        self.assertNotIn("SENTINEL", cleaned); self.assertNotIn("C:\\\\private", cleaned); self.assertNotIn("server", cleaned); self.assertIn("<path>", cleaned)

    def test_child_gate_rejects_missing_claim_before_cli_or_provider(self):
        with tempfile.TemporaryDirectory() as temp:
            runtime = Path(temp) / "runtime"; runtime.mkdir()
            _fixture, tasks, _gold, _gold_path = pilot.build_runtime(runtime)
            output = Path(temp) / "output"; output.mkdir()
            with patch.object(run, "PILOT_CLAIM_PATH", Path(temp) / "missing.claim"), patch.object(run, "live_execution_approved", return_value=True), patch.object(run, "live_pin_matches", return_value=True), patch.object(run, "installed_cli_version") as version, patch.object(run.subprocess, "run") as provider:
                with self.assertRaises(SystemExit):
                    run.main(["--owner-approved", "--pilot-output", str(output), "--task", "PILOT-01", "--arm", "retrieval-v1-packet", "--agent", "codex", "--repetition", "1", "--model", "m", "--cli-version", "v", "--effort", "medium", "--tasks", str(tasks)])
            version.assert_not_called(); provider.assert_not_called()

    def test_coordinator_rejects_archived_cli_version_before_claim_or_provider(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); output = root / "output"; executable = root / "claude.exe"
            executable.write_bytes(b"mock")
            matrix = {"pins": {
                "claude": {"model": "claude-sonnet-5", "cli_version": "2.1.221", "effort": None},
                "codex": {"model": "gpt-5.6-luna", "cli_version": "codex-cli 0.146.0", "effort": "medium"},
            }}
            claim = root / "missing.claim"
            with patch.object(pilot, "PILOT_CLAIM_PATH", claim), patch.object(
                pilot, "safe_absent_temp_path", return_value=output
            ), patch.object(pilot, "verified_claude_executable", return_value=executable), patch.object(
                pilot, "live_execution_approved", return_value=True
            ), patch.object(pilot, "load_json", return_value=matrix), patch.object(
                pilot.subject_run, "installed_cli_version", return_value=("2.1.220", "2.1.220")
            ), patch.object(pilot.subject_run.subprocess, "run") as provider:
                with self.assertRaises(SystemExit):
                    pilot.main(["--owner-approved", "--output", str(output), "--claude-executable", str(executable)])
            self.assertFalse(claim.exists()); provider.assert_not_called()

    def test_timeout_bounds_fail_before_claim_and_capped_capture_overflow_is_terminal(self):
        with self.assertRaises(SystemExit):
            pilot.main(["--owner-approved", "--output", "unused", "--claude-executable", "unused", "--timeout", "0"])
        with tempfile.TemporaryDirectory() as temp:
            result = run.capped_subprocess(
                [sys.executable, "-c", "import sys; sys.stdout.write('x'*200000)"],
                cwd=Path(temp), env=dict(os.environ), timeout=10, byte_limit=1024,
            )
            self.assertTrue(result.overflow); self.assertLessEqual(len(result.stdout.encode()), 1024)

    def test_pilot_final_answer_keeps_only_schema_valid_json(self):
        valid = {"schema": "context-answer.v1", "adr_ids": [], "authoritative_refs": [], "adr_statuses": {}, "lineage_edges": [], "related_edges": [], "citations": [], "explanation": "ok", "insufficient_evidence": False, "missing_refs": []}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); last = root / "RUN_LAST_MESSAGE.txt"
            last.write_text(json.dumps(valid), encoding="utf-8")
            run.sanitize_subject_artifacts(root, pilot=True)
            self.assertEqual(valid, json.loads(last.read_text(encoding="utf-8")))
            last.write_text('{"schema":"wrong","cwd":"C:\\\\secret","metadata":"SENTINEL"}', encoding="utf-8")
            run.sanitize_subject_artifacts(root, pilot=True)
            self.assertEqual("", last.read_text(encoding="utf-8"))

    def test_oversized_last_message_is_rejected_before_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); last = root / "RUN_LAST_MESSAGE.txt"
            last.write_bytes(b"x" * (run.PILOT_FINAL_OUTPUT_LIMIT + 1))
            self.assertFalse(run.sanitize_subject_artifacts(root, pilot=True))
            self.assertFalse(last.exists())

    def test_schema_valid_answer_redacts_paths_env_and_secret_values_everywhere(self):
        answer = {"schema": "context-answer.v1", "adr_ids": ["adr_pilot_local_index"], "authoritative_refs": ["mse_bcde2345fghj6789:d1"], "adr_statuses": {"adr_pilot_local_index": "accepted"}, "lineage_edges": [pilot_spec.LINEAGE], "related_edges": [pilot_spec.RELATED], "citations": ["mse_bcde2345fghj6789:d1"], "explanation": "C:\\private\\file \\\\server\\share\\file /var/private/file $SECRET_TOKEN TOP-SECRET-SENTINEL", "insufficient_evidence": False, "missing_refs": []}
        with patch.dict(os.environ, {"SECRET_TOKEN": "TOP-SECRET-SENTINEL"}):
            retained = run._schema_answer_json(json.dumps(answer))
        self.assertTrue(retained); self.assertNotIn("TOP-SECRET-SENTINEL", retained)
        self.assertNotIn("C:\\\\private", retained); self.assertNotIn("server", retained); self.assertNotIn("/var/private", retained)
        self.assertNotIn("$SECRET_TOKEN", retained); self.assertIn("mse_bcde2345fghj6789:d1", retained)

    def test_canonical_looking_secret_is_redacted_before_ref_recognition(self):
        secret_ref = "mse_bcde2345fghj6789:d1"
        answer = {"schema": "context-answer.v1", "adr_ids": ["adr_pilot_local_index"], "authoritative_refs": [secret_ref], "adr_statuses": {"adr_pilot_local_index": "accepted"}, "lineage_edges": [{"source": secret_ref, "target": "mse_abcd1234efgh5678:d1", "type": "evolves"}], "related_edges": [], "citations": [secret_ref], "explanation": "secret ref", "insufficient_evidence": False, "missing_refs": []}
        raw_tool = json.dumps({"item": {"type": "mcp_tool_call", "tool": "memory_search", "result": {"content": [{"type": "text", "text": secret_ref + " \\\\server\\share\\secret"}]}}})
        with patch.dict(os.environ, {"CANONICAL_SECRET_TOKEN": secret_ref}):
            retained_answer = run._schema_answer_json(json.dumps(answer))
            retained_tool = run.sanitize_pilot_stream(raw_tool + "\n")
        self.assertNotIn(secret_ref, retained_answer); self.assertNotIn(secret_ref, retained_tool)
        self.assertNotIn("server", retained_tool); self.assertIn("<redacted-env:CANONICAL_SECRET_TOKEN>", retained_answer)

    def test_retained_pilot_command_hides_archived_executable_and_subject_paths(self):
        work = Path(tempfile.gettempdir()) / "subject-secret-path"
        executable = Path(tempfile.gettempdir()) / "archive" / "claude.exe"
        retained = run._retained_command(
            [str(executable), "--mcp-config", str(work / "mcp.json"), "prompt"],
            prompt="prompt", work_dir=work, claude_executable=executable,
        )
        self.assertEqual(["<verified-claude-executable>", "--mcp-config", "<subject-path>", "<prompt>"], retained)

    def test_normal_collection_and_scoring_reject_pilot_artifacts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); run_dir = root / "pilot"; run_dir.mkdir()
            answer = {"schema": "context-answer.v1", "adr_ids": [], "authoritative_refs": [], "adr_statuses": {}, "lineage_edges": [], "related_edges": [], "citations": [], "explanation": "x", "insufficient_evidence": False, "missing_refs": []}
            manifest = {"schema": "context-run-manifest.v1", "run_id": "pilot", "task_id": "PILOT-01", "arm": "search-mcp", "agent": "codex", "repetition": 1, "schedule_seed": 20260804, "model": "m", "cli_version": "v", "started_at": "2026-08-05T00:00:00Z", "transcript": "transcript.jsonl", "final_answer": "final_answer.txt", "scored": False, "smoke": False, "pilot": True}
            (run_dir / "RUN_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
            (run_dir / "transcript.jsonl").write_text("{}\n", encoding="utf-8")
            (run_dir / "final_answer.txt").write_text(json.dumps(answer), encoding="utf-8")
            self.assertEqual([], collect.collect(root)["runs"])
            with self.assertRaisesRegex(ValueError, "smoke or unscored"):
                score.score_experiment({"runs": [{**manifest, "protocol_failure": "unscored_or_smoke_artifact"}]}, {"tasks": []}, require_complete=False)


if __name__ == "__main__":
    unittest.main()

"""Fast, offline checks for the experiment-local subject harness."""
from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1] / "experiments" / "context-derivation"


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec); assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


mcp = load("mcp_wrapper"); batch = load("batch"); collect = load("collect"); runner = load("run"); judge = load("judge"); contracts = load("contracts")


def answer(**overrides):
    value = {
        "schema": "context-answer.v1",
        "adr_ids": [],
        "authoritative_refs": [],
        "adr_statuses": {},
        "lineage_edges": [],
        "related_edges": [],
        "citations": [],
        "explanation": "ok",
        "insufficient_evidence": False,
        "missing_refs": [],
    }
    value.update(overrides)
    return value


class HarnessTests(unittest.TestCase):
    def test_allowlists_never_advertise_write_tools_and_pin_cwd(self):
        names = {item["name"] for item in mcp.filtered_tools("adr-mcp-workflow")}
        self.assertIn("memory_adr_show", names); self.assertNotIn("memory_session_append", names)
        with tempfile.TemporaryDirectory() as temp, patch.object(mcp.mcp_server, "call_tool", return_value={"ok": True}) as call:
            response = mcp.handle_message({"id": 1, "method": "tools/call", "params": {"name": "memory_search", "arguments": {"cwd": "wrong"}}}, arm="search-mcp", fixture_cwd=Path(temp))
            self.assertIn("result", response); self.assertEqual(call.call_args.args[1]["cwd"], str(Path(temp)))
            rejected = mcp.handle_message({"id": 2, "method": "tools/call", "params": {"name": "memory_session_append"}}, arm="search-mcp", fixture_cwd=Path(temp))
            self.assertIn("error", rejected)

    def test_schedule_is_exact_deterministic_and_topup_balanced(self):
        tasks = [f"CTX-{i:02d}" for i in range(1, 13)]
        first, second = batch.build_schedule(tasks), batch.build_schedule(tasks)
        self.assertEqual(first, second); self.assertEqual(288, len(first))
        counts = batch.Counter({("CTX-01", "search-mcp", "claude", 1): 1, ("CTX-01", "search-mcp", "claude", 2): 1})
        left = batch.top_up(first, counts)
        self.assertEqual(286, len(left)); self.assertEqual(1, sum(c["task_id"] == "CTX-01" and c["arm"] == "search-mcp" and c["agent"] == "claude" for c in left))

    def test_collects_codex_and_claude_shape_without_gold(self):
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp) / "r"; run.mkdir()
            manifest = {"schema": "context-run-manifest.v1", "run_id": "r", "task_id": "CTX-01", "arm": "search-mcp", "agent": "codex", "repetition": 1, "schedule_seed": 20260804, "model": "m", "cli_version": "v", "started_at": "2026-08-04T10:00:00Z", "transcript": "transcript.jsonl", "final_answer": "final_answer.txt", "duration_ms": 2, "parent_isolated": True}
            (run / "RUN_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
            (run / "transcript.jsonl").write_text(json.dumps({"type": "item.completed", "item": {"type": "mcp_tool_call", "tool": "memory_search"}}) + "\n", encoding="utf-8")
            result = answer(explanation="none", insufficient_evidence=True)
            (run / "final_answer.txt").write_text(json.dumps(result), encoding="utf-8")
            row = collect.collect(Path(temp))["runs"][0]
            self.assertEqual("memory_search", row["tool_calls"][0]); self.assertEqual(result, row["answer"]); self.assertIsNone(row["harness_failure"])

    def test_fixed_arm_has_no_mcp_config_and_mocked_runner_records_usage(self):
        task = {"schema": "context-benchmark-task.v1", "task_id": "CTX-01", "fixture": "unused", "question": "q", "task_type": "accepted-head", "resolver_hints": {}, "packets": {"retrieval-v1-packet": "evidence"}}
        result = answer()
        stream = json.dumps({"type": "result", "result": json.dumps(result), "usage": {"input_tokens": 3, "output_tokens": 4}}) + "\n"
        with tempfile.TemporaryDirectory() as temp:
            root, runs, tasks = Path(temp), Path(temp) / "runs", Path(temp) / "tasks.json"
            tasks.write_text(json.dumps({"tasks": [task]}), encoding="utf-8")
            command = runner.build_command("claude", root, "prompt", arm="retrieval-v1-packet", fixture=None, model="m", effort=None)
            self.assertNotIn("--mcp-config", command); self.assertNotIn("--dangerously-skip-permissions", command); self.assertIn("--tools", command)
            seen = {}
            def fake_run(*args, **kwargs):
                seen["cwd"] = Path(kwargs["cwd"]).resolve()
                return subprocess.CompletedProcess([], 0, stream, "")
            with patch.object(runner, "RUNS", runs), patch.object(runner, "REPO_ROOT", root), patch.object(runner, "live_execution_approved", return_value=True), patch.object(runner, "live_pin_matches", return_value=True), patch.object(runner, "live_tasks_match", return_value=True), patch.object(runner.subprocess, "run", side_effect=fake_run):
                self.assertEqual(0, runner.main(["--owner-approved", "--task", "CTX-01", "--arm", "retrieval-v1-packet", "--agent", "claude", "--repetition", "1", "--model", "m", "--cli-version", "v", "--tasks", str(tasks)]))
            with self.assertRaises(ValueError):
                seen["cwd"].relative_to(root.resolve())
            manifest = json.loads(next(runs.glob("*/RUN_MANIFEST.json")).read_text(encoding="utf-8"))
            self.assertTrue(manifest["fixed_arm_no_fixture"]); self.assertFalse(manifest["mcp_enabled"]); self.assertEqual(3, manifest["input_tokens"])
            self.assertEqual("provider_throttled", runner.classify_failure(timed_out=False, exit_code=1, stderr="429 rate limit", transcript=""))
            prompt = runner.subject_prompt(task, "retrieval-v1-packet")
            self.assertIn('"lineage_edges"', prompt); self.assertIn('"adr_statuses"', prompt); self.assertIn('"related_edges"', prompt)

    def test_command_execution_and_gold_path_are_protocol_failures(self):
        raw = [{"item": {"type": "command_execution", "command": "cat ../tasks/gold.json"}}]
        self.assertEqual(["command_execution"], collect.transcript_tool_calls(raw))
        self.assertTrue(runner._direct_filesystem_retrieval(json.dumps(raw[0])))
        self.assertFalse(runner._direct_filesystem_retrieval(json.dumps({"type": "result", "result": "I did not read the ADR files"})))
        with tempfile.TemporaryDirectory() as temp:
            run = Path(temp)
            manifest = {"schema": "context-run-manifest.v1", "run_id": "r", "task_id": "CTX-01", "arm": "retrieval-v1-packet", "agent": "codex", "repetition": 1, "schedule_seed": 20260804, "model": "m", "cli_version": "v", "started_at": "2026-08-04T10:00:00Z", "transcript": "transcript.jsonl", "final_answer": "final_answer.txt", "duration_ms": 2, "parent_isolated": True, "tool_calls": [], "undeclared_tool_calls": [], "direct_filesystem_retrieval": True}
            (run / "RUN_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
            (run / "transcript.jsonl").write_text(json.dumps(raw[0]) + "\n", encoding="utf-8")
            (run / "final_answer.txt").write_text(json.dumps(answer()), encoding="utf-8")
            row = collect.analyse_run(run)
            self.assertIn("undeclared_tool_call", row["protocol_failure"])
            self.assertIn("direct_filesystem_retrieval", row["protocol_failure"])

    def test_answer_parser_is_strict(self):
        self.assertEqual(answer(), collect.parse_answer(json.dumps(answer())))
        self.assertIsNone(collect.parse_answer(json.dumps(answer(extra=True))))
        self.assertIsNone(collect.parse_answer(json.dumps(answer(adr_statuses={"adr_x": "bogus"}))))
        self.assertIsNone(collect.parse_answer(json.dumps(answer(lineage_edges=[{"source": "a", "target": "b", "type": "related"}]))))

    def test_collect_extracts_only_tool_result_evidence_refs(self):
        raw = [{"message": {"content": [
            {"type": "text", "text": "ignore mse_prompt:d1"},
            {"type": "tool_result", "content": "accepted adr_alpha at mse_source:d2"},
        ]}}]
        excerpt, refs = collect.transcript_evidence(raw)
        self.assertIn("mse_source:d2", excerpt)
        self.assertEqual(["adr_alpha", "mse_source:d2"], refs)

    def test_throttling_reduces_only_that_agent_and_keeps_order(self):
        cells = [{"task_id": f"CTX-{i:02d}", "arm": "search-mcp", "agent": "claude", "repetition": 1} for i in range(1, 5)]
        calls = []
        def fake(cell, **_kwargs):
            calls.append(cell["task_id"])
            return {**cell, "failure_classification": "provider_throttled" if cell["task_id"] == "CTX-01" and calls.count("CTX-01") == 1 else None}
        with patch.object(batch.time, "sleep"):
            result = batch._run_queue(cells, agent="claude", jobs=3, model_by_agent={}, cli_versions={}, timeout=1, backoff=0, runner=fake)
        self.assertEqual([cell["task_id"] for cell in cells], [row["task_id"] for row in result])
        self.assertEqual([3, 3, 3, 2], [row["queue_concurrency"] for row in result])
        self.assertTrue(result[0]["throttle_retry"])

    def test_owner_approval_gate_prevents_non_dry_run(self):
        with self.assertRaises(SystemExit):
            batch.main(["--claude-model", "c", "--codex-model", "x", "--claude-cli-version", "1", "--codex-cli-version", "1"])
        with self.assertRaises(SystemExit):
            runner.main(["--task", "CTX-01", "--arm", "search-mcp", "--agent", "claude", "--repetition", "1", "--model", "m", "--cli-version", "v"])
        with self.assertRaises(SystemExit):
            batch.main(["--owner-approved", "--claude-model", "c", "--codex-model", "x", "--claude-cli-version", "1", "--codex-cli-version", "1"])
        with self.assertRaises(SystemExit):
            judge.require_execution_approval(owner_approved=False)
        with patch.object(judge, "live_execution_approved", return_value=False), self.assertRaises(SystemExit):
            judge.require_execution_approval(owner_approved=True)

    def test_live_gate_requires_candidate_matrix_pins_and_matching_tasks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "tasks").mkdir()
            (root / "PREREGISTRATION.md").write_text("Status: **APPROVED**", encoding="utf-8")
            (root / "tasks" / "gold.json").write_text(json.dumps({"approval_status": "APPROVED"}), encoding="utf-8")
            (root / "FROZEN_CANDIDATE.json").write_text(json.dumps({"schema": "context-candidate-manifest.v1", "strategy_fingerprint": "sha256:candidate"}), encoding="utf-8")
            rows = [{"task_id": f"CTX-{number:02d}", "packets": {"retrieval-v1-packet": "v1", "adr-candidate-packet": "adr"}} for number in range(1, 13)]
            live_payload = {"schema": "context-live-tasks.v1", "candidate_fingerprint": "sha256:candidate", "retrieval_strategy_fingerprint": "sha256:v1", "tasks": rows}
            live_payload["fingerprint"] = contracts.fingerprint(live_payload)
            matrix = {"schema": "context-live-matrix.v1", "status": "FROZEN", "task_count": 12, "arms": list(contracts.ARMS), "repetitions": 3, "agents": list(contracts.AGENTS), "subject_runs": 288, "schedule_seed": 20260804, "max_agent_concurrency": 3, "max_total_concurrency": 6, "candidate_fingerprint": "sha256:candidate", "retrieval_v1_fingerprint": "sha256:v1", "live_tasks_fingerprint": live_payload["fingerprint"], "pins": {"claude": {"model": "c", "cli_version": "1"}, "codex": {"model": "x", "cli_version": "2"}}}
            (root / "LIVE_MATRIX.json").write_text(json.dumps(matrix), encoding="utf-8")
            live_tasks = root / "live-tasks.json"
            live_tasks.write_text(json.dumps(live_payload), encoding="utf-8")
            self.assertTrue(contracts.live_execution_approved(root))
            self.assertTrue(contracts.live_pin_matches(root, "claude", "c", "1"))
            self.assertTrue(contracts.live_tasks_match(root, live_tasks))
            matrix["pins"]["claude"]["model"] = "PENDING_UNSCORED_PROBE"
            (root / "LIVE_MATRIX.json").write_text(json.dumps(matrix), encoding="utf-8")
            self.assertFalse(contracts.live_execution_approved(root))

    def test_single_run_dry_run_leaves_no_run_artifact(self):
        task = {"schema": "context-benchmark-task.v1", "task_id": "CTX-01", "fixture": "unused", "question": "q", "task_type": "accepted-head", "resolver_hints": {}, "packets": {"retrieval-v1-packet": "evidence"}}
        with tempfile.TemporaryDirectory() as temp:
            root, runs, tasks = Path(temp), Path(temp) / "runs", Path(temp) / "tasks.json"
            tasks.write_text(json.dumps({"tasks": [task]}), encoding="utf-8")
            with patch.object(runner, "RUNS", runs), patch.object(runner, "REPO_ROOT", root):
                self.assertEqual(0, runner.main(["--dry-run", "--task", "CTX-01", "--arm", "retrieval-v1-packet", "--agent", "claude", "--repetition", "1", "--model", "m", "--cli-version", "v", "--tasks", str(tasks)]))
            self.assertFalse(runs.exists() and any(runs.iterdir()))

    def test_parallel_results_retain_schedule_order(self):
        schedule = [
            {"task_id": "CTX-01", "arm": "search-mcp", "agent": "codex", "repetition": 1},
            {"task_id": "CTX-02", "arm": "search-mcp", "agent": "claude", "repetition": 1},
            {"task_id": "CTX-03", "arm": "search-mcp", "agent": "codex", "repetition": 1},
        ]
        def fake(cell, **_kwargs): return {**cell, "failure_classification": None}
        result = batch.run_parallel(schedule, jobs_per_agent=1, model_by_agent={}, cli_versions={}, timeout=1, throttle_backoff=0, runner=fake)
        self.assertEqual([batch.cell_key(cell) for cell in schedule], [batch.cell_key(row) for row in result])


if __name__ == "__main__": unittest.main()

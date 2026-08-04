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


mcp = load("mcp_wrapper"); batch = load("batch"); collect = load("collect"); runner = load("run")


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
            manifest = {"schema": "context-run-manifest.v1", "run_id": "r", "task_id": "CTX-01", "arm": "search-mcp", "agent": "codex", "repetition": 1, "schedule_seed": 20260804, "transcript": "transcript.jsonl", "final_answer": "final_answer.txt", "duration_ms": 2, "parent_isolated": True}
            (run / "RUN_MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
            (run / "transcript.jsonl").write_text(json.dumps({"type": "item.completed", "item": {"type": "mcp_tool_call", "tool": "memory_search"}}) + "\n", encoding="utf-8")
            answer = {"schema": "context-answer.v1", "adr_ids": [], "authoritative_refs": [], "adr_statuses": {}, "lineage_edges": [], "related_edges": [], "citations": [], "explanation": "none", "insufficient_evidence": True}
            (run / "final_answer.txt").write_text(json.dumps(answer), encoding="utf-8")
            row = collect.collect(Path(temp))["runs"][0]
            self.assertEqual("memory_search", row["tool_calls"][0]); self.assertEqual(answer, row["answer"]); self.assertIsNone(row["harness_failure"])

    def test_fixed_arm_has_no_mcp_config_and_mocked_runner_records_usage(self):
        task = {"schema": "context-benchmark-task.v1", "task_id": "CTX-01", "fixture": "unused", "question": "q", "task_type": "accepted-head", "resolver_hints": {}, "packets": {"retrieval-v1-packet": "evidence"}}
        answer = {"schema": "context-answer.v1", "adr_ids": [], "authoritative_refs": [], "lineage_edges": [], "citations": [], "explanation": "ok", "insufficient_evidence": False}
        stream = json.dumps({"type": "result", "result": json.dumps(answer), "usage": {"input_tokens": 3, "output_tokens": 4}}) + "\n"
        with tempfile.TemporaryDirectory() as temp:
            root, runs, tasks = Path(temp), Path(temp) / "runs", Path(temp) / "tasks.json"
            tasks.write_text(json.dumps({"tasks": [task]}), encoding="utf-8")
            command = runner.build_command("claude", root, "prompt", arm="retrieval-v1-packet", fixture=None, model="m", effort=None)
            self.assertNotIn("--mcp-config", command)
            with patch.object(runner, "RUNS", runs), patch.object(runner, "REPO_ROOT", root), patch.object(runner.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stream, "")):
                self.assertEqual(0, runner.main(["--owner-approved", "--task", "CTX-01", "--arm", "retrieval-v1-packet", "--agent", "claude", "--repetition", "1", "--model", "m", "--cli-version", "v", "--tasks", str(tasks)]))
            manifest = json.loads(next(runs.glob("*/RUN_MANIFEST.json")).read_text(encoding="utf-8"))
            self.assertTrue(manifest["fixed_arm_no_fixture"]); self.assertFalse(manifest["mcp_enabled"]); self.assertEqual(3, manifest["input_tokens"])
            self.assertEqual("provider_throttled", runner.classify_failure(timed_out=False, exit_code=1, stderr="429 rate limit", transcript=""))
            prompt = runner.subject_prompt(task, "retrieval-v1-packet")
            self.assertIn('"lineage_edges"', prompt); self.assertIn('"adr_statuses"', prompt); self.assertIn('"related_edges"', prompt)

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

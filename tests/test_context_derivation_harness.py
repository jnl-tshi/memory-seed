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


mcp = load("mcp_wrapper"); batch = load("batch"); collect = load("collect"); runner = load("run"); judge = load("judge"); contracts = load("contracts"); probe = load("probe")


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
            with patch.object(runner, "RUNS", runs), patch.object(runner, "REPO_ROOT", root), patch.object(runner, "live_execution_approved", return_value=True), patch.object(runner, "live_pin_matches", return_value=True), patch.object(runner, "live_tasks_match", return_value=True), patch.object(runner, "installed_cli_version", return_value=("v", "v")), patch.object(runner.subprocess, "run", side_effect=fake_run):
                self.assertEqual(0, runner.main(["--owner-approved", "--task", "CTX-01", "--arm", "retrieval-v1-packet", "--agent", "claude", "--repetition", "1", "--model", "m", "--cli-version", "v", "--tasks", str(tasks)]))
            with self.assertRaises(ValueError):
                seen["cwd"].relative_to(root.resolve())
            manifest = json.loads(next(runs.glob("*/RUN_MANIFEST.json")).read_text(encoding="utf-8"))
            self.assertTrue(manifest["fixed_arm_no_fixture"]); self.assertFalse(manifest["mcp_enabled"]); self.assertEqual(3, manifest["input_tokens"])
            self.assertEqual("provider_throttled", runner.classify_failure(timed_out=False, exit_code=1, stderr="429 rate limit", transcript=""))
            prompt = runner.subject_prompt(task, "retrieval-v1-packet")
            self.assertIn('"lineage_edges"', prompt); self.assertIn('"adr_statuses"', prompt); self.assertIn('"related_edges"', prompt)

    def test_subject_commands_enforce_tool_and_filesystem_isolation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture = root / "fixture"
            fixture.mkdir()
            claude = runner.build_command(
                "claude", root, "prompt", arm="search-mcp", fixture=fixture,
                model="claude-model", effort=None,
            )
            self.assertNotIn("--dangerously-skip-permissions", claude)
            self.assertEqual("", claude[claude.index("--tools") + 1])
            allowed = claude[claude.index("--allowed-tools") + 1].split(",")
            self.assertEqual(
                {f"mcp__context-fixture__{name}" for name in mcp.allowed_names("search-mcp")},
                set(allowed),
            )
            self.assertIn("--strict-mcp-config", claude)
            self.assertIn("dontAsk", claude)
            self.assertIn("--no-chrome", claude)
            self.assertIn("Bash,Read,Edit,Write,Glob,Grep,NotebookEdit,WebFetch,WebSearch,Task", claude)

            with self.assertRaisesRegex(RuntimeError, "running harness-owned broker"):
                runner.build_command(
                    "codex", root, "prompt", arm="adr-mcp-workflow", fixture=fixture,
                    model="codex-model", effort="medium",
                )
            interactive_codex = runner.build_command(
                "codex", root, "prompt", arm="adr-mcp-workflow", fixture=fixture,
                model="codex-model", effort="medium",
                broker_url="http://127.0.0.1:43123/mcp",
            )
            self.assertNotIn("mcp_servers={}", interactive_codex)
            self.assertNotIn("CONTEXT_DERIVATION_MCP_TOKEN=", " ".join(interactive_codex))
            self.assertIn(
                'mcp_servers.context_fixture.bearer_token_env_var="CONTEXT_DERIVATION_MCP_TOKEN"',
                interactive_codex,
            )
            self.assertIn('features.shell_tool=false', interactive_codex)
            self.assertIn('features.apps=false', interactive_codex)
            self.assertIn('web_search="disabled"', interactive_codex)
            codex = runner.build_command(
                "codex", root, "prompt", arm="adr-candidate-packet", fixture=None,
                model="codex-model", effort="medium",
            )
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", codex)
            self.assertNotIn("--sandbox", codex)
            self.assertIn("--ignore-user-config", codex)
            self.assertIn("--ignore-rules", codex)
            overrides = [codex[index + 1] for index, value in enumerate(codex[:-1]) if value == "-c"]
            self.assertIn('approval_policy="never"', overrides)
            self.assertIn('default_permissions="context_subject"', overrides)
            self.assertIn(
                'permissions.context_subject.filesystem={":root"="deny",":minimal"="read",'
                '":workspace_roots"={"."="read"}}',
                overrides,
            )
            self.assertIn("mcp_servers={}", overrides)
            self.assertFalse((root / ".codex").exists())
            self.assertEqual("claude-builtins-disabled", runner.subject_isolation("claude"))
            self.assertEqual("codex-deny-read-permission-profile", runner.subject_isolation("codex"))
            with patch.dict(runner.os.environ, {"OPENAI_API_KEY": "secret", "SAFE_SENTINEL": "kept"}):
                environment = runner.subject_environment()
            self.assertNotIn("OPENAI_API_KEY", environment)
            self.assertNotIn("SAFE_SENTINEL", environment)
            with patch.dict(runner.os.environ, {"UNLISTED_TOKEN": "oauth-abcdefghijklmnop"}):
                self.assertNotIn("oauth-abcdefghijklmnop", runner.redact_output("oauth-abcdefghijklmnop"))
            generated = "broker-secret-value"
            self.assertNotIn(generated, runner.redact_output(generated, secrets=(generated,)))
            self.assertTrue(runner.codex_broker_capable())
            self.assertFalse(runner.codex_interactive_ready())

    def test_subject_last_message_is_redacted_before_archival(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(
            runner.os.environ, {"UNLISTED_TOKEN": "oauth-abcdefghijklmnop"}
        ):
            work = Path(temp)
            raw = work / "RUN_LAST_MESSAGE.txt"
            raw.write_text("answer oauth-abcdefghijklmnop", encoding="utf-8")
            runner.sanitize_subject_artifacts(work)
            retained = raw.read_text(encoding="utf-8")
            self.assertNotIn("oauth-abcdefghijklmnop", retained)
            self.assertIn("<redacted-env:UNLISTED_TOKEN>", retained)
            self.assertEqual(retained, runner._final_answer(work, ""))

    def test_unscored_probe_is_repeated_version_bound_and_outside_runs(self):
        transcript = "\n".join([
            json.dumps({"type": "system", "subtype": "init", "model": "claude-canonical"}),
            json.dumps({"type": "result", "result": '{"probe":"ok"}', "modelUsage": {
                "claude-canonical": {}, "claude-auxiliary": {},
            }}),
        ])
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "claude-probe"
            with patch.object(probe, "installed_cli_version", return_value=("2.1.221 (Claude Code)", "2.1.221")), patch.object(
                probe.subprocess, "run",
                side_effect=[subprocess.CompletedProcess([], 0, transcript, ""), subprocess.CompletedProcess([], 0, transcript, "")],
            ):
                manifest = probe.run_probe(
                    agent="claude", model="sonnet", cli_version="2.1.221",
                    effort=None, output=output,
                )
            self.assertEqual("claude-canonical", manifest["resolved_model"])
            self.assertEqual(
                ["claude-auxiliary", "claude-canonical"],
                manifest["observations"][0]["observed_models"],
            )
            self.assertEqual(2, len(manifest["observations"]))
            self.assertFalse(manifest["scored"])
            self.assertFalse(manifest["gold_used"])
            self.assertIsNone(manifest["task_id"])
            self.assertTrue((output / "PROBE_MANIFEST.json").is_file())
        with self.assertRaises(SystemExit):
            probe.main([
                "--agent", "codex", "--model", "gpt", "--cli-version", "v",
                "--output", str(Path(tempfile.gettempdir()) / "not-created"),
            ])
        with tempfile.TemporaryDirectory() as temp, patch.object(
            probe, "installed_cli_version", return_value=("codex-cli 0.146.0", "codex-cli 0.146.0")
        ), patch.object(probe, "codex_catalog_slugs", return_value={"gpt-5.6-luna"}):
            with self.assertRaisesRegex(ValueError, "canonical bundled catalog slug"):
                probe.run_probe(
                    agent="codex", model="luna", cli_version="codex-cli 0.146.0",
                    effort=None, output=Path(temp) / "codex-probe",
                )

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
            result = batch._run_queue(cells, agent="claude", jobs=3, model_by_agent={}, cli_versions={}, effort_by_agent={}, timeout=1, backoff=0, runner=fake)
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
        with patch.object(runner, "live_execution_approved", return_value=True), patch.object(
            runner, "live_pin_matches", return_value=True
        ), patch.object(runner, "live_tasks_match", return_value=True), patch.object(
            runner, "installed_cli_version", return_value=("new", "new")
        ), self.assertRaises(SystemExit):
            runner.main([
                "--owner-approved", "--task", "CTX-01", "--arm", "adr-candidate-packet",
                "--agent", "codex", "--repetition", "1", "--model", "m",
                "--cli-version", "old",
            ])

    def test_live_gate_requires_candidate_matrix_pins_and_matching_tasks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); (root / "tasks").mkdir()
            (root / "PREREGISTRATION.md").write_text("Status: **APPROVED**", encoding="utf-8")
            (root / "tasks" / "gold.json").write_text(json.dumps({"approval_status": "APPROVED"}), encoding="utf-8")
            (root / "FROZEN_CANDIDATE.json").write_text(json.dumps({"schema": "context-candidate-manifest.v1", "strategy_fingerprint": "sha256:candidate", "reduction_fingerprint": "sha256:reduction"}), encoding="utf-8")
            rows = [{"task_id": f"CTX-{number:02d}", "packets": {"retrieval-v1-packet": "v1", "adr-candidate-packet": "adr"}} for number in range(1, 13)]
            live_payload = {"schema": "context-live-tasks.v1", "candidate_fingerprint": "sha256:candidate", "retrieval_strategy_fingerprint": "sha256:v1", "tasks": rows}
            live_payload["fingerprint"] = contracts.fingerprint(live_payload)
            offline = {"schema": "context-offline-selection.v1", "selected_strategy_fingerprint": "sha256:candidate", "reduction_fingerprint": "sha256:reduction", "resolver_fingerprint": __import__("sweep").resolver_implementation_fingerprint()}
            offline["fingerprint"] = contracts.fingerprint(offline)
            probes = {"schema": "context-probe-pins.v1", "agents": {"claude": {"requested_model": "c", "resolved_model": "c", "cli_version": "1", "effort": None, "observations": 2, "probe_fingerprint": "sha256:claude-probe"}, "codex": {"requested_model": "x", "resolved_model": "x", "cli_version": "2", "effort": "medium", "observations": 2, "probe_fingerprint": "sha256:codex-probe"}}}
            probes["fingerprint"] = contracts.fingerprint(probes)
            (root / "OFFLINE_SELECTION.json").write_text(json.dumps(offline), encoding="utf-8")
            (root / "PROBE_PINS.json").write_text(json.dumps(probes), encoding="utf-8")
            matrix = {"schema": "context-live-matrix.v1", "status": "FROZEN", "task_count": 12, "arms": list(contracts.ARMS), "repetitions": 3, "agents": list(contracts.AGENTS), "subject_runs": 288, "schedule_seed": 20260804, "max_agent_concurrency": 3, "max_total_concurrency": 6, "candidate_fingerprint": "sha256:candidate", "retrieval_v1_fingerprint": "sha256:v1", "live_tasks_fingerprint": live_payload["fingerprint"], "offline_selection_fingerprint": offline["fingerprint"], "probe_pins_fingerprint": probes["fingerprint"], "probe_fingerprints": {"claude": "sha256:claude-probe", "codex": "sha256:codex-probe"}, "pins": {"claude": {"model": "c", "cli_version": "1", "effort": None}, "codex": {"model": "x", "cli_version": "2", "effort": "medium"}}}
            (root / "LIVE_MATRIX.json").write_text(json.dumps(matrix), encoding="utf-8")
            live_tasks = root / "live-tasks.json"
            live_tasks.write_text(json.dumps(live_payload), encoding="utf-8")
            self.assertTrue(contracts.live_execution_approved(root))
            self.assertTrue(contracts.live_pin_matches(root, "claude", "c", "1", None))
            self.assertTrue(contracts.live_pin_matches(root, "codex", "x", "2", "medium"))
            self.assertFalse(contracts.live_pin_matches(root, "codex", "x", "2", None))
            self.assertTrue(contracts.live_tasks_match(root, live_tasks))
            matrix["pins"]["claude"]["model"] = "PENDING_UNSCORED_PROBE"
            (root / "LIVE_MATRIX.json").write_text(json.dumps(matrix), encoding="utf-8")
            self.assertFalse(contracts.live_execution_approved(root))

    def test_batch_stops_before_any_provider_call_without_codex_broker(self):
        with tempfile.TemporaryDirectory() as temp:
            tasks = Path(temp) / "live-tasks.json"
            tasks.write_text(json.dumps({
                "tasks": [{"task_id": f"CTX-{number:02d}"} for number in range(1, 13)],
            }), encoding="utf-8")
            args = [
                "--owner-approved", "--claude-model", "claude-sonnet-5",
                "--codex-model", "gpt-5.6-luna", "--codex-effort", "medium",
                "--claude-cli-version", "2.1.221", "--codex-cli-version", "codex-cli 0.146.0",
                "--tasks", str(tasks),
            ]
            with patch.object(batch, "live_execution_approved", return_value=True), patch.object(
                batch, "codex_interactive_ready", return_value=False,
            ), patch.object(batch, "run_parallel") as run_parallel, self.assertRaises(SystemExit):
                batch.main(args)
            run_parallel.assert_not_called()

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
        result = batch.run_parallel(schedule, jobs_per_agent=1, model_by_agent={}, cli_versions={}, effort_by_agent={}, timeout=1, throttle_backoff=0, runner=fake)
        self.assertEqual([batch.cell_key(cell) for cell in schedule], [batch.cell_key(row) for row in result])


if __name__ == "__main__": unittest.main()

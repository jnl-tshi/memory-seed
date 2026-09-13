from __future__ import annotations

import importlib
import json
import tempfile
import unittest
from pathlib import Path, PureWindowsPath


ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "experiments" / "task-packet-calibration"
PACKAGE = "experiments.task-packet-calibration"

contracts = importlib.import_module(f"{PACKAGE}.contracts")
mcp_wrapper = importlib.import_module(f"{PACKAGE}.mcp_wrapper")
prepare = importlib.import_module(f"{PACKAGE}.prepare")
runner = importlib.import_module(f"{PACKAGE}.run")
scorer = importlib.import_module(f"{PACKAGE}.score")

ANSWER_SCHEMA = contracts.ANSWER_SCHEMA
RUN_SCHEMA = contracts.RUN_SCHEMA
fingerprint = contracts.fingerprint
READ_ONLY_TOOLS = mcp_wrapper.READ_ONLY_TOOLS
filtered_tools = mcp_wrapper.filtered_tools
handle_message = mcp_wrapper.handle_message
prepare_bundle = prepare.prepare_bundle
_hermes_config = runner._hermes_config
_scrub_external_credentials = runner._scrub_external_credentials
score_run = scorer.score_run


class TaskPacketCalibrationHarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp(prefix="task-packet-calibration-test-"))
        self.tasks_path = HARNESS / "tasks" / "development.json"
        self.gold_path = HARNESS / "tasks" / "development.gold.json"

    def test_prepare_reconstructs_one_three_arm_bundle(self) -> None:
        bundle = self.temp / "bundle"
        first = prepare_bundle(self.tasks_path, "TPC-DEV-001", bundle)
        self.assertEqual(set(first["arms"]), {"no_memory", "memory_tools", "compiled_packet"})
        packet = json.loads((bundle / "task-packet.json").read_text(encoding="utf-8"))
        self.assertEqual(first["packet_fingerprint"], packet["fingerprint"])
        prompts = {
            arm: (bundle / row["path"]).read_text(encoding="utf-8")
            for arm, row in first["arms"].items()
        }
        self.assertNotIn("Compiled Task Packet:", prompts["no_memory"])
        self.assertNotIn("Compiled Task Packet:", prompts["memory_tools"])
        self.assertIn("Compiled Task Packet:", prompts["compiled_packet"])
        for arm, text in prompts.items():
            self.assertEqual(first["arms"][arm]["fingerprint"], fingerprint(text))

    def test_mcp_facade_is_read_only_pins_cwd_and_audits(self) -> None:
        bundle = self.temp / "bundle"
        prepare_bundle(self.tasks_path, "TPC-DEV-001", bundle)
        audit = self.temp / "audit.jsonl"
        self.assertEqual({row["name"] for row in filtered_tools()}, set(READ_ONLY_TOOLS))
        self.assertTrue(
            all(row["annotations"]["readOnlyHint"] for row in filtered_tools())
        )
        response = handle_message(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "memory_adrs_list",
                    "arguments": {"cwd": "C:/not/the/fixture"},
                },
            },
            fixture_cwd=bundle / "runtime",
            audit_log=audit,
        )
        self.assertIn("result", response)
        row = json.loads(audit.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(row["model_arguments"]["cwd"], "C:/not/the/fixture")
        self.assertEqual(Path(row["effective_cwd"]), (bundle / "runtime").resolve())
        blocked = handle_message(
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "memory_session_append", "arguments": {}},
            },
            fixture_cwd=bundle / "runtime",
            audit_log=audit,
        )
        self.assertIn("error", blocked)

    def test_hermes_config_has_no_builtin_tools_and_only_bounded_mcp(self) -> None:
        config = _hermes_config(
            model="qwen/qwen3.5-9b",
            arm="compiled_packet",
            fixture=self.temp / "runtime",
            audit_log=self.temp / "audit.jsonl",
            mcp_python=PureWindowsPath("C:/hermes/python.exe"),
        )
        self.assertEqual(
            config["platform_toolsets"]["cli"], ["mcp-memory_seed_calibration"]
        )
        self.assertEqual(config["tools"]["tool_search"]["enabled"], "off")
        server = config["mcp_servers"]["memory_seed_calibration"]
        self.assertEqual(server["command"], "C:\\hermes\\python.exe")
        self.assertEqual(server["trust"], "full")
        self.assertEqual(set(server["tools"]["include"]), set(READ_ONLY_TOOLS))
        no_memory = _hermes_config(
            model="qwen/qwen3.5-9b",
            arm="no_memory",
            fixture=self.temp / "runtime",
            audit_log=self.temp / "audit.jsonl",
            mcp_python=PureWindowsPath("C:/hermes/python.exe"),
        )
        self.assertNotIn("mcp_servers", no_memory)
        self.assertEqual(no_memory["platform_toolsets"]["cli"], [])
        scrubbed = _scrub_external_credentials(
            {"OPENAI_API_KEY": "secret", "ANTHROPIC_API_KEY": "secret", "SAFE": "yes"}
        )
        self.assertEqual(scrubbed, {"SAFE": "yes"})

    def test_mechanical_scorer_handles_packet_and_no_memory(self) -> None:
        bundle = self.temp / "bundle"
        manifest = prepare_bundle(self.tasks_path, "TPC-DEV-001", bundle)
        tasks = json.loads(self.tasks_path.read_text(encoding="utf-8"))
        task = tasks["tasks"][0]
        gold = json.loads(self.gold_path.read_text(encoding="utf-8"))
        packet = json.loads((bundle / "task-packet.json").read_text(encoding="utf-8"))
        answers = []
        for proposition in task["propositions"]:
            expected = gold["tasks"][task["id"]]["propositions"][proposition["id"]]
            answers.append(
                {
                    "proposition_id": proposition["id"],
                    "verdict": expected["verdict"],
                    "evidence_ids": [expected["evidence_ids"][0]],
                }
            )
        run = {
            "schema": RUN_SCHEMA,
            "run_fingerprint": "sha256:packet-run",
            "task_id": task["id"],
            "arm": "compiled_packet",
            "model": "test-model",
            "response": json.dumps(
                {"schema": ANSWER_SCHEMA, "answers": answers, "missing_questions": []}
            ),
            "tool_calls": [],
            "tool_call_count": 0,
            "usage": None,
            "wall_seconds": 1.0,
        }
        score = score_run(run, task, gold, packet)
        self.assertTrue(score["complete_correct"])
        self.assertFalse(score["repeated_materialized_fetch"])

        for row in answers:
            row["verdict"] = "insufficient"
            row["evidence_ids"] = []
        run["arm"] = "no_memory"
        run["run_fingerprint"] = "sha256:no-memory-run"
        run["response"] = json.dumps(
            {"schema": ANSWER_SCHEMA, "answers": answers, "missing_questions": []}
        )
        self.assertTrue(score_run(run, task, gold, None)["complete_correct"])


if __name__ == "__main__":
    unittest.main()

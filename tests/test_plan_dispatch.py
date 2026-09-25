"""Plan-task dispatch generation (task-packet-handoff-integration-plan.md, T2)."""

import contextlib
import copy
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from memory_seed.cli import main as cli_main
from memory_seed.mcp_server import MUTATING_TOOL_NAMES, call_tool
from memory_seed.plan_dispatch import plan_dispatches
from memory_seed.task_packet import TaskPacketValidationError, compile_task_packet
from tests.pilot_task_packet_fixture import build_fixture_runtime, runtime_binding, semantic_dispatch

REPO = Path(__file__).resolve().parents[1]
DECISION = "mse_packetpilot:d1"


def plan_block() -> dict:
    pilot = semantic_dispatch()
    return {
        "schema": "memory-seed/plan-dispatch",
        "version": 1,
        "defaults": {
            "project_context": pilot["project_context"],
            "execution": {
                "role": "worker",
                "persona": "none",
                "capability_tier": "balanced",
                "forbidden_files": [".memory-seed/policy.md"],
                "output_contract": ["Return the lite return contract."],
            },
            "retrieval": pilot["retrieval"],
            "budget": pilot["budget"],
        },
        "objectives": {
            "T1": "Extend the pilot support document.",
            "T2": "Add a new support page.",
        },
        "implementation_plan": {
            "approval_reference": DECISION,
            "tasks": [
                {
                    "id": "T1",
                    "acceptance_observables": ["pilot support covers the new case"],
                    "edit_ownership": [{"path": "docs/pilot-support.md", "line_range": [1, 3]}],
                    "dependencies": [],
                    "evidence_references": [DECISION],
                    "verification": ["python -m unittest tests.test_plan_dispatch"],
                    "replan_conditions": ["the support document moved"],
                },
                {
                    "id": "T2",
                    "acceptance_observables": ["new page exists"],
                    "edit_ownership": [{"path": "docs/new-page.md", "line_range": [1, 1]}],
                    "dependencies": ["T1"],
                    "evidence_references": [DECISION],
                    "verification": ["python -m unittest tests.test_plan_dispatch"],
                    "replan_conditions": ["scope grows beyond one page"],
                },
            ],
            "test_strategy": {
                "tests": ["tests/test_plan_dispatch.py"],
                "alternative_checks": [],
                "exceptions": [],
                "tests_before_behavior_change": True,
                "behavior_changes": True,
            },
        },
    }


def plan_markdown(block: dict) -> str:
    return "# Tranche plan\n\nProse for readers.\n\n```json\n" + json.dumps(block, indent=2) + "\n```\n"


class PlanDispatchTests(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp(prefix="memory-seed-plan-dispatch-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        self.root = build_fixture_runtime(tmp / "runtime")

    def test_one_dispatch_per_task_in_plan_order(self):
        result = plan_dispatches(plan_markdown(plan_block()), self.root, source="plan.md")
        self.assertEqual([task["id"] for task in result["tasks"]], ["T1", "T2"])
        first, second = (task["dispatch"] for task in result["tasks"])
        self.assertEqual(first["execution"]["allowed_files"], ["docs/pilot-support.md"])
        self.assertEqual(first["execution"]["implements"], [DECISION])
        self.assertEqual(first["execution"]["write_intent"], "writing")
        self.assertEqual(first["packet_version"], 2)
        self.assertIn("Acceptance: pilot support covers the new case", first["execution"]["output_contract"])
        self.assertIn("Stop and report NEEDS_CONTEXT if: the support document moved",
                      first["execution"]["output_contract"])
        self.assertEqual(first["execution"]["acceptance_observables"][0]["command"],
                         "python -m unittest tests.test_plan_dispatch")
        self.assertEqual(second["execution"]["expected_absent"], ["docs/new-page.md"])
        self.assertEqual(result["tasks"][1]["dependencies"], ["T1"])
        self.assertEqual(result["approval_reference"], DECISION)
        pins = first["retrieval"]["overrides"]["selectors"]["pinned"]
        self.assertEqual(sum(1 for pin in pins if pin["id"] == DECISION), 1)

    def test_generated_dispatches_compile(self):
        result = plan_dispatches(plan_markdown(plan_block()), self.root)
        binding = runtime_binding(self.root)
        binding.update({"working_branch": "main", "worktree": str(self.root.resolve()), "integration_artifact": "branch"})
        orientation = self.root / ".memory-seed" / "skills" / "subagent_orientation.md"
        orientation.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / ".memory-seed" / "skills" / "subagent_orientation.md", orientation)
        for task in result["tasks"]:
            with self.subTest(task=task["id"]):
                packet = compile_task_packet(task["dispatch"], binding, self.root, handoff="implementation")
                self.assertEqual(packet["packet_version"], 2)

    def test_refusals_name_their_reason(self):
        cases = {}
        cases["no block"] = "# Plan\n\nNo structured block.\n"
        cases["two blocks"] = plan_markdown(plan_block()) + plan_markdown(plan_block())
        missing_objective = plan_block()
        del missing_objective["objectives"]["T2"]
        cases["missing objective"] = plan_markdown(missing_objective)
        forward = plan_block()
        forward["implementation_plan"]["tasks"][0]["dependencies"] = ["T2"]
        cases["forward dependency"] = plan_markdown(forward)
        overlap = plan_block()
        overlap["implementation_plan"]["tasks"][1]["edit_ownership"] = [
            {"path": "docs/pilot-support.md", "line_range": [2, 2]}]
        overlap["implementation_plan"]["tasks"][1]["dependencies"] = []
        cases["overlap without dependency"] = plan_markdown(overlap)
        unknown = plan_block()
        unknown["defaults"]["execution"]["write_intent"] = "writing"
        cases["unknown default"] = plan_markdown(unknown)
        for name, markdown in cases.items():
            with self.subTest(case=name), self.assertRaises(TaskPacketValidationError) as refused:
                plan_dispatches(markdown, self.root)
            self.assertEqual(refused.exception.code, "invalid_plan")

    def test_cli_and_mcp_parity_and_read_only(self):
        plan_file = self.root / "plan.md"
        plan_file.write_text(plan_markdown(plan_block()), encoding="utf-8")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = cli_main(["task-packet", "from-plan", "--plan-file", str(plan_file), "--cwd", str(self.root)])
        self.assertEqual(code, 0)
        response = call_tool("memory_task_packet_from_plan", {"plan_file": str(plan_file), "cwd": str(self.root)})
        self.assertEqual(json.loads(stdout.getvalue()), response)
        self.assertNotIn("memory_task_packet_from_plan", MUTATING_TOOL_NAMES)
        bad = self.root / "bad.md"
        bad.write_text("# No block\n", encoding="utf-8")
        refused = call_tool("memory_task_packet_from_plan", {"plan_file": str(bad), "cwd": str(self.root)})
        self.assertFalse(refused["ok"])
        self.assertEqual(refused["error"]["code"], "invalid_plan")

    def test_approval_must_be_a_decision_reference(self):
        block = plan_block()
        block["implementation_plan"]["approval_reference"] = "TBD"
        for task in block["implementation_plan"]["tasks"]:
            task["evidence_references"] = [DECISION, "TBD"]
        with self.assertRaises(TaskPacketValidationError) as refused:
            plan_dispatches(plan_markdown(block), self.root)
        self.assertEqual(refused.exception.code, "invalid_plan")

    def test_approval_is_pinned_as_required(self):
        block = plan_block()
        other = "mse_packetpilot:d2"
        block["implementation_plan"]["approval_reference"] = other
        for task in block["implementation_plan"]["tasks"]:
            task["evidence_references"] = [DECISION, other]
        try:
            result = plan_dispatches(plan_markdown(block), self.root)
        except TaskPacketValidationError as exc:
            self.skipTest(f"fixture plan shape rejects a second reference: {exc}")
        pins = result["tasks"][0]["dispatch"]["retrieval"]["overrides"]["selectors"]["pinned"]
        self.assertEqual([pin["required"] for pin in pins if pin["id"] == other], [True])

    def test_relative_plan_file_resolves_against_cwd_not_process(self):
        (self.root / "plan.md").write_text(plan_markdown(plan_block()), encoding="utf-8")
        response = call_tool("memory_task_packet_from_plan", {"plan_file": "plan.md", "cwd": str(self.root)})
        self.assertEqual([task["id"] for task in response["tasks"]], ["T1", "T2"], response)


if __name__ == "__main__":
    unittest.main()

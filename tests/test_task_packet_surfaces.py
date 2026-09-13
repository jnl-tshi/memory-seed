"""CLI/MCP adapters replay the canonical Task Packet compiler without writes."""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory_seed.cli import _atomic_export_json, main as cli_main
from memory_seed.mcp_server import MUTATING_TOOL_NAMES, TOOLS, call_tool, handle_jsonrpc_message
from memory_seed.retrieval import canonical_retrieval_json
from memory_seed.task_packet import canonical_task_packet_json, compile_task_packet


class TaskPacketSurfaceTests(unittest.TestCase):
    def test_planning_evidence_additive_dispatch_has_cli_mcp_parity_and_structured_failure(self):
        from memory_seed.task_packet import prepare_planning_evidence
        root = self.make_project()
        dispatch = self.dispatch()
        source = next(item for item in compile_task_packet(dispatch, self.binding(root), root)["materialized_evidence"]
                      if item["kind"] == "markdown")
        draft = {"id": "compiler", "selected_alternative": "Reuse existing compiler",
                 "sources": [source["id"]],
                 "candidate": {"reference": source["id"], "decision": "Keep canonical evidence", "authority": "derived_projection"},
                 "assessed_scope": {"topics": [], "paths": [source["source"]]},
                 "compatibility_constraints": [], "proposed_action": "Reuse compiler", "conflict_reason": None,
                 "agent_recommendation": "proceed", "user_acceptance": None, "departure_reference": None}
        dispatch["planning_evidence"] = prepare_planning_evidence(dispatch, [draft], root)
        dispatch_file, binding_file = self.write_inputs(root)
        dispatch_file.write_text(json.dumps(dispatch), encoding="utf-8")
        expected = compile_task_packet(dispatch, self.binding(root), root)
        before = self.snapshot(root)
        code, stdout, stderr = self.cli(["task-packet", "compile", "--dispatch-file", str(dispatch_file),
                                        "--binding-file", str(binding_file), "--cwd", str(root)])
        self.assertEqual((code, stderr), (0, ""))
        self.assertEqual(json.loads(stdout), expected)
        response = call_tool("memory_task_packet_compile", {"dispatch": dispatch, "binding": self.binding(root), "cwd": str(root)})
        self.assertTrue(response["ok"])
        self.assertEqual(response["packet"], expected)
        self.assertEqual(self.snapshot(root), before)
        dispatch["planning_evidence"][0]["authority_granted"] = True
        response = call_tool("memory_task_packet_compile", {"dispatch": dispatch, "binding": self.binding(root), "cwd": str(root)})
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "planning_fingerprint_mismatch")

    def test_reflection_missing_capability_is_refused_by_cli_and_mcp_before_export(self):
        root = self.make_project()
        dispatch, binding = self.dispatch(), self.binding(root)
        dispatch["execution"]["write_intent"] = "writing"
        dispatch["execution"]["allowed_files"] = [".MEMORY-SEED\\REFLECTIONS\\active\\missing\\ledger.md"]
        dispatch["execution"]["expected_absent"] = list(dispatch["execution"]["allowed_files"])
        binding.update(working_branch="main", worktree=str(root))
        dispatch_file, binding_file = self.write_inputs(root)
        dispatch_file.write_text(json.dumps(dispatch), encoding="utf-8")
        binding_file.write_text(json.dumps(binding), encoding="utf-8")
        before = self.snapshot(root)
        for command in ("preview", "compile"):
            code, stdout, stderr = self.cli(["task-packet", command, "--dispatch-file", str(dispatch_file),
                                            "--binding-file", str(binding_file), "--cwd", str(root)])
            self.assertNotEqual(code, 0)
            self.assertIn("reflection-capability-required", stdout + stderr)
            result = call_tool("memory_task_packet_" + command, {"dispatch": dispatch, "binding": binding, "cwd": str(root)})
            self.assertFalse(result["ok"])
            self.assertIn("reflection-capability-required", json.dumps(result))
        self.assertEqual(self.snapshot(root), before)

    def make_project(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="memory-seed-task-packet-surfaces-"))
        self.addCleanup(lambda: shutil.rmtree(root, ignore_errors=True))
        (root / ".memory-seed" / "sessions").mkdir(parents=True)
        (root / ".memory-seed" / "skills").mkdir(parents=True)
        (root / ".memory-seed" / "retrieval-profiles" / "implementation").mkdir(parents=True)
        (root / "docs").mkdir()
        (root / "docs" / "CONSTITUTION.md").write_text(
            "# Constitution\n\n**Version:** 1.0 — **RATIFIED 2026-09-05**\n\n"
            "## Invariant\n\nMarkdown is authoritative.\n",
            encoding="utf-8",
        )
        (root / "docs" / "evidence.md").write_text("# Evidence\n\nCanonical source.\n", encoding="utf-8")
        (root / ".memory-seed" / "agent-rules.md").write_text(
            "# Active agent rules\n\nGovern every worker.\n", encoding="utf-8"
        )
        (root / ".memory-seed" / "skills" / "session_logging.md").write_text(
            "# Active session logging\n\nUse the guarded writer.\n", encoding="utf-8"
        )
        (root / ".memory-seed" / "sessions" / "2026-08-01.md").write_text(
            "## 2026-08-01 09:00 - Packet decision\n\n"
            "```yaml\nentry_id: mse_surface0001\nuser_initials: JN\nagent_type: codex\n"
            "project_path: .\nsubproject_path: null\n```\n\n"
            "### Decision\n\n- D: Replay one deterministic packet.\n"
            "- R: Adapters must not duplicate compilation.\n"
            "- F: `docs/evidence.md`.\n",
            encoding="utf-8",
        )
        (root / ".memory-seed" / "retrieval-profiles" / "implementation" / "v1.yaml").write_text(
            "schema: memory-seed/retrieval-profile\nschema_version: 1\nid: implementation\n"
            "profile_version: 1\nextends: []\nspec:\n"
            "  selectors:\n    path_references: true\n"
            "  filters:\n    paths:\n      - docs/evidence.md\n"
            "  output:\n    include_excerpts: true\n"
            "  limits:\n    max_entries: 20\n    max_tokens: 12000\n",
            encoding="utf-8",
        )
        self.git(root, "init", "-b", "main")
        self.git(root, "config", "user.email", "test@example.com")
        self.git(root, "config", "user.name", "Task Packet Surface Test")
        self.git(root, "add", ".")
        self.git(root, "commit", "-m", "fixture")
        return root

    @staticmethod
    def git(root: Path, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout.strip()

    def dispatch(self) -> dict:
        context = " ".join(["grounded"] * 15)
        return {
            "schema": "memory-seed/task-dispatch", "version": 1,
            "objective": "Compile one reconstructable Task Packet.",
            "constitution_refs": [],
            "project_context": {
                "project_type_and_purpose": context, "relevant_subsystem": context,
                "task_fit": context, "downstream_use": context,
                "non_goals": ["Do not create workers or worktrees."],
            },
            "execution": {
                "role": "worker", "persona": "none", "capability_tier": "balanced",
                "write_intent": "read-only", "allowed_files": [], "forbidden_files": [],
                "validation": ["python -m unittest tests.test_task_packet_surfaces"],
                "output_contract": ["Return one source-linked handoff."],
                "expected_absent": [],
                "acceptance_observables": [{
                    "name": "task-packet-surface-tests",
                    "command": "python -m unittest tests.test_task_packet_surfaces",
                    "expected_exit_code": 0,
                }],
                "implements": [],
            },
            "retrieval": {"profile": "implementation", "profile_version": 1, "overrides": {}},
            "budget": {"supplemental_input_tokens": 1000, "output_tokens": 2000,
                       "over_soft_cap": "fail", "over_soft_cap_reason": None},
        }

    def binding(self, root: Path) -> dict:
        return {
            "owner": "orchestrator", "agent_type": "codex", "base_branch": "main",
            "base_sha": self.git(root, "rev-parse", "main"), "working_branch": None,
            "worktree": None, "expected_directory": str(root), "integration_artifact": "handoff",
        }

    @staticmethod
    def snapshot(root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file() and ".git" not in path.parts
        }

    def cli(self, args: list[str]) -> tuple[int, str, str]:
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = cli_main(args)
        return result, stdout.getvalue(), stderr.getvalue()

    def write_inputs(self, root: Path) -> tuple[Path, Path]:
        dispatch_file, binding_file = root / "dispatch.json", root / "binding.json"
        dispatch_file.write_text(json.dumps(self.dispatch()), encoding="utf-8")
        binding_file.write_text(json.dumps(self.binding(root)), encoding="utf-8")
        return dispatch_file, binding_file

    def test_retrieval_adapters_require_exactly_one_mode_and_resolve_profiles(self) -> None:
        root = self.make_project()
        both = call_tool("memory_retrieval_spec_preview", {
            "spec": {}, "profile": "implementation", "profile_version": 1, "cwd": str(root),
        })
        self.assertFalse(both["ok"])
        self.assertEqual(both["error"]["code"], "invalid_spec")
        incomplete = call_tool("memory_retrieval_spec_resolve", {"profile": "implementation", "cwd": str(root)})
        self.assertFalse(incomplete["ok"])
        self.assertEqual(incomplete["error"]["code"], "invalid_spec")
        missing = call_tool("memory_retrieval_spec_resolve", {
            "profile": "missing", "profile_version": 1, "cwd": str(root),
        })
        self.assertFalse(missing["ok"])
        self.assertEqual(missing["error"]["code"], "invalid_profile")
        resolved = call_tool("memory_retrieval_spec_resolve", {
            "profile": "implementation", "profile_version": 1, "overrides": {}, "cwd": str(root),
        })
        self.assertTrue(resolved["ok"])
        self.assertEqual(resolved["pack"]["effective_spec"]["version"], 2)

    def test_task_packet_cli_mcp_preview_compile_parity_and_read_only(self) -> None:
        root = self.make_project()
        dispatch, binding = self.dispatch(), self.binding(root)
        environment = {"fixed_instructions": ["Use canonical sources."], "tool_schemas": []}
        pricing = {
            "currency": "USD", "effective_date": "2026-09-01",
            "per_million_input": 1, "per_million_cached_input": 0.5,
            "per_million_output": 5, "tool_cost": 0,
        }
        dispatch_file, binding_file = self.write_inputs(root)
        environment_file, pricing_file = root / "environment.json", root / "pricing.json"
        environment_file.write_text(json.dumps(environment), encoding="utf-8")
        pricing_file.write_text(json.dumps(pricing), encoding="utf-8")
        expected = canonical_task_packet_json(
            compile_task_packet(dispatch, binding, root, environment=environment, pricing=pricing)
        )
        before = self.snapshot(root)
        for command in ("preview", "compile"):
            with self.subTest(surface=f"cli-{command}"):
                code, stdout, stderr = self.cli([
                    "task-packet", command, "--dispatch-file", str(dispatch_file),
                    "--binding-file", str(binding_file), "--cwd", str(root),
                    "--environment-file", str(environment_file), "--pricing-file", str(pricing_file),
                ])
                self.assertEqual((code, stderr), (0, ""))
                self.assertEqual(stdout, expected)
            with self.subTest(surface=f"mcp-{command}"):
                response = handle_jsonrpc_message({
                    "jsonrpc": "2.0", "id": 1, "method": "tools/call",
                    "params": {"name": f"memory_task_packet_{command}", "arguments": {
                        "dispatch": dispatch, "binding": binding, "environment": environment,
                        "pricing": pricing, "cwd": str(root),
                    }},
                })
                payload = json.loads(response["result"]["content"][0]["text"])
                self.assertTrue(payload["ok"])
                artifact = payload["preview" if command == "preview" else "packet"]
                self.assertEqual(canonical_task_packet_json(artifact), expected)
                self.assertEqual(response["result"]["content"][0]["text"], canonical_retrieval_json(payload))
        self.assertEqual(self.snapshot(root), before)

    def test_cli_export_is_atomic_and_refuses_overwrite(self) -> None:
        root = self.make_project()
        dispatch_file, binding_file = self.write_inputs(root)
        expected = canonical_task_packet_json(
            compile_task_packet(self.dispatch(), self.binding(root), root)
        )
        fresh_output = root / "fresh-packet.json"
        fresh_args = ["task-packet", "compile", "--dispatch-file", str(dispatch_file),
                      "--binding-file", str(binding_file), "--cwd", str(root), "--output", str(fresh_output)]
        code, stdout, stderr = self.cli(fresh_args)
        self.assertEqual((code, stdout, stderr), (0, "", ""))
        self.assertEqual(fresh_output.read_text(encoding="utf-8"), expected)

        output = root / "packet.json"
        output.write_text("preserve", encoding="utf-8")
        args = ["task-packet", "compile", "--dispatch-file", str(dispatch_file),
                "--binding-file", str(binding_file), "--cwd", str(root), "--output", str(output)]
        code, stdout, stderr = self.cli(args)
        self.assertEqual(code, 2)
        self.assertEqual(stdout, "")
        self.assertIn("output already exists", stderr)
        self.assertEqual(output.read_text(encoding="utf-8"), "preserve")
        expected_after_output_exists = canonical_task_packet_json(
            compile_task_packet(self.dispatch(), self.binding(root), root)
        )
        code, stdout, stderr = self.cli([*args, "--overwrite"])
        self.assertEqual((code, stdout, stderr), (0, "", ""))
        self.assertEqual(
            output.read_text(encoding="utf-8"),
            expected_after_output_exists,
        )
        self.assertFalse(list(root.glob(".packet.json.*.tmp")))

    def test_no_overwrite_publish_preserves_a_target_created_at_publish_time(self) -> None:
        root = self.make_project()
        output = root / "raced-packet.json"
        original_link = os.link

        def create_race(source, destination, *args, **kwargs):
            Path(destination).write_bytes(b"racer-won")
            return original_link(source, destination, *args, **kwargs)

        with patch("memory_seed.cli.os.link", side_effect=create_race):
            with self.assertRaisesRegex(FileExistsError, "output already exists"):
                _atomic_export_json(str(output), "compiled-packet", overwrite=False)
        self.assertEqual(output.read_bytes(), b"racer-won")
        self.assertFalse(list(root.glob(".raced-packet.json.*.tmp")))

    def test_mcp_task_packet_tools_are_inline_and_read_only(self) -> None:
        tool_names = {tool["name"] for tool in TOOLS}
        self.assertTrue({"memory_task_packet_preview", "memory_task_packet_compile"} <= tool_names)
        self.assertFalse({"memory_task_packet_preview", "memory_task_packet_compile"} & MUTATING_TOOL_NAMES)
        root = self.make_project()
        unsupported = call_tool("memory_task_packet_compile", {
            "dispatch": self.dispatch(), "binding": self.binding(root), "cwd": str(root), "output": "packet.json",
        })
        self.assertFalse(unsupported["ok"])
        self.assertEqual(unsupported["error"]["code"], "invalid_arguments")
        self.assertEqual(unsupported["error"]["details"]["unsupported_arguments"], ["output"])

    def test_mcp_task_packet_profile_normalization_error_is_structured_and_read_only(self) -> None:
        root = self.make_project()
        profile = root / ".memory-seed" / "retrieval-profiles" / "invalid" / "v1.yaml"
        profile.parent.mkdir(parents=True)
        profile.write_text(
            "schema: memory-seed/retrieval-profile\nschema_version: 1\nid: invalid\n"
            "profile_version: 1\nextends: []\nspec:\n"
            "  limits:\n    max_tokens: 0\n",
            encoding="utf-8",
        )
        dispatch, binding = self.dispatch(), self.binding(root)
        dispatch["retrieval"] = {"profile": "invalid", "profile_version": 1, "overrides": {}}
        before = self.snapshot(root)
        for command in ("preview", "compile"):
            with self.subTest(command=command):
                arguments = {"dispatch": dispatch, "binding": binding, "cwd": str(root)}
                result = call_tool(f"memory_task_packet_{command}", arguments)
                self.assertFalse(result["ok"])
                self.assertEqual(result["error"]["code"], "invalid_spec")
                self.assertEqual(result["error"]["stage"], "validation")
                self.assertEqual(result["error"]["completed_stages"], [])
                response = handle_jsonrpc_message({
                    "jsonrpc": "2.0", "id": 2, "method": "tools/call",
                    "params": {"name": f"memory_task_packet_{command}", "arguments": arguments},
                })
                wire = json.loads(response["result"]["content"][0]["text"])
                self.assertEqual(wire, result)
        self.assertEqual(self.snapshot(root), before)


if __name__ == "__main__":
    unittest.main()

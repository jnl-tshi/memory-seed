"""Task Packet spawn-prompt rendering (task-packet-handoff-integration-plan.md, T3)."""

import contextlib
import copy
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from memory_seed.attention import LOG_NAME, load_task_packet_usage
from memory_seed.cli import main as cli_main
from memory_seed.mcp_server import MUTATING_TOOL_NAMES, call_tool
from memory_seed.packet_render import _quoted, render_task_packet
from memory_seed.task_packet import TaskPacketValidationError, canonical_task_packet_json, compile_task_packet
from tests.pilot_task_packet_fixture import build_fixture_runtime, runtime_binding, semantic_dispatch

REPO = Path(__file__).resolve().parents[1]


class PacketRenderTests(unittest.TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp(prefix="memory-seed-packet-render-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        self.root = build_fixture_runtime(tmp / "runtime")
        orientation = self.root / ".memory-seed" / "skills" / "subagent_orientation.md"
        orientation.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / ".memory-seed" / "skills" / "subagent_orientation.md", orientation)
        (self.root / ".gitignore").write_text(f".memory-seed/{LOG_NAME}\npacket.json\n", encoding="utf-8")
        for args in (("add", "."), ("commit", "-m", "render fixture")):
            subprocess.run(["git", "-C", str(self.root), *args], check=True, capture_output=True)
        self.dispatch = copy.deepcopy(semantic_dispatch())
        self.dispatch["packet_version"] = 2

    def test_prompt_is_self_sufficient_and_names_its_packet(self):
        packet = compile_task_packet(self.dispatch, runtime_binding(self.root), self.root)
        prompt = render_task_packet(packet, "out/packet.json", handoff="review")
        self.assertTrue(prompt.startswith(f"# Task: {self.dispatch['objective']}"))
        self.assertIn(packet["worker_orientation"]["content"].rstrip("\n"), prompt)
        self.assertIn(f"`{packet['fingerprint']}`", prompt)
        self.assertIn("`out/packet.json`", prompt)
        self.assertIn("Read-only: do not edit or commit", prompt)
        for item in packet["materialized_evidence"]:
            self.assertIn('<evidence id="' + item["id"] + '"', prompt)
            self.assertIn(item["content"].rstrip("\n"), prompt)
        self.assertIn("memory_task_packet_governance_load", prompt)
        # Evidence headings stay inside their tags, so the prompt's own sections are unique.
        self.assertEqual(prompt.count("\n## Evidence\n"), 1)
        self.assertEqual(prompt.count("<evidence "), len(packet["materialized_evidence"]))
        self.assertEqual(prompt.count("</evidence>"), len(packet["materialized_evidence"]))
        self.assertEqual(prompt, render_task_packet(packet, "out/packet.json", handoff="review"))

    def test_prompt_renders_v2_dispatch_read_scope_and_keeps_v1_packets_renderable(self):
        legacy_packet = compile_task_packet(self.dispatch, runtime_binding(self.root), self.root)
        legacy_prompt = render_task_packet(legacy_packet, "legacy.json")
        self.assertIn("Read inputs: unspecified by legacy dispatch schema v1", legacy_prompt)

        dispatch = copy.deepcopy(self.dispatch)
        dispatch["version"] = 2
        dispatch["execution"].update(
            read_inputs={
                "working": ["memory_seed/task_packet.py"],
                "reference": ["docs/evidence.md"],
            },
            do_not_load=[".memory-seed/policy.md"],
        )
        prompt = render_task_packet(
            compile_task_packet(dispatch, runtime_binding(self.root), self.root),
            "scoped.json",
        )
        self.assertIn("Working inputs:\n- memory_seed/task_packet.py", prompt)
        self.assertIn("Reference inputs:\n- docs/evidence.md", prompt)
        self.assertIn("Do not load:\n- .memory-seed/policy.md", prompt)

    def test_v3_prompt_names_pinned_selected_and_late_load_skills(self):
        skills = self.root / ".memory-seed" / "skills"
        (skills / "index.md").write_text(
            "# Registry\n\n```yaml\ntrigger_registry_version: 1\nskills:\n"
            "  - skill: data_architecture.md\n    required: true\n    load_when:\n"
            "      - changing schemas, persistence, cache format, or retrieval contracts\n"
            "  - skill: systematic_debugging.md\n    required: true\n    load_when:\n"
            "      - diagnosing an unexpected failure, regression, or unexplained behaviour\n```\n",
            encoding="utf-8",
        )
        (skills / "data_architecture.md").write_text("# Data Architecture\n", encoding="utf-8")
        (skills / "systematic_debugging.md").write_text("# Debugging\n", encoding="utf-8")
        dispatch = copy.deepcopy(self.dispatch)
        dispatch["version"] = 3
        dispatch["packet_version"] = 3
        dispatch["execution"].update(
            read_inputs={"working": ["docs/pilot-support.md"], "reference": []},
            do_not_load=[".memory-seed/policy.md"],
            skill_selection={
                "selected": [{
                    "skill": "data_architecture.md",
                    "trigger": "changing schemas, persistence, cache format, or retrieval contracts",
                }],
                "late_load": [{
                    "skill": "systematic_debugging.md",
                    "trigger": "diagnosing an unexpected failure, regression, or unexplained behaviour",
                }],
            },
        )
        dispatch["budget"]["skill_input_tokens"] = 100
        packet = compile_task_packet(dispatch, runtime_binding(self.root), self.root)
        prompt = render_task_packet(packet, "p.json")
        self.assertIn("## Persona and skills loaded on demand", prompt)
        self.assertIn("Selected skills:\n- data_architecture.md", prompt)
        self.assertIn("Eligible late-load skills:\n- systematic_debugging.md", prompt)
        self.assertIn("memory_task_packet_context_load", prompt)

    def test_prompt_names_the_canonical_integration_command(self):
        # Gagiste field issue: every PR was opened and merged with raw `gh`
        # because nothing at handoff named `memory-seed session open-pr`.
        binding = runtime_binding(self.root)
        prompt = render_task_packet(compile_task_packet(self.dispatch, binding, self.root), "p.json")
        self.assertEqual(prompt.count("\n## Integration\n"), 1)
        self.assertRegex(prompt, r"`memory-seed session merge-branch --branch [^`]+` from the base checkout")
        self.assertIn("appends the delivery session entry on the task branch", prompt)

        binding["integration_artifact"] = "pr"
        pr_prompt = render_task_packet(compile_task_packet(self.dispatch, binding, self.root), "p.json")
        self.assertIn("`memory-seed session open-pr` from the task branch", pr_prompt)
        self.assertIn("Raw `gh pr create` / `gh pr merge` skip the fuse", pr_prompt)

    def test_tampered_packet_is_refused(self):
        packet = compile_task_packet(self.dispatch, runtime_binding(self.root), self.root)
        packet["dispatch"]["objective"] = "Something else."
        with self.assertRaises(TaskPacketValidationError):
            render_task_packet(packet, "p.json")

    def test_cli_writes_the_packet_and_matches_mcp(self):
        dispatch_file, binding_file = self.root / "dispatch.json", self.root / "binding.json"
        dispatch_file.write_text(json.dumps(self.dispatch), encoding="utf-8")
        binding_file.write_text(json.dumps(runtime_binding(self.root)), encoding="utf-8")
        packet_out = self.root / "packet.json"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = cli_main(["task-packet", "render", "--dispatch-file", str(dispatch_file),
                             "--binding-file", str(binding_file), "--packet-out", str(packet_out),
                             "--handoff", "spawned-session", "--cwd", str(self.root), "--json"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        written = json.loads(packet_out.read_text(encoding="utf-8"))
        self.assertEqual(canonical_task_packet_json(written), packet_out.read_text(encoding="utf-8"))
        self.assertEqual(payload["packet_fingerprint"], written["fingerprint"])
        self.assertIn(written["fingerprint"], payload["prompt"])

        response = call_tool("memory_task_packet_render", {
            "packet": written, "packet_path": str(packet_out), "handoff": "spawned-session", "cwd": str(self.root)})
        self.assertTrue(response["ok"])
        self.assertEqual(response["prompt"], payload["prompt"])
        self.assertNotIn("memory_task_packet_render", MUTATING_TOOL_NAMES)

        with contextlib.redirect_stdout(io.StringIO()):
            refused = cli_main(["task-packet", "render", "--dispatch-file", str(dispatch_file),
                                "--binding-file", str(binding_file), "--packet-out", str(packet_out),
                                "--cwd", str(self.root)])
        self.assertEqual(refused, 2)  # no silent overwrite; invalid input, as compile

        kinds = [(event["tool"], event["handoff"]) for event in load_task_packet_usage(self.root / ".memory-seed")["events"]]
        self.assertIn(("task_packet_render", "spawned-session"), kinds)
        self.assertEqual(kinds.count(("task_packet_render", "spawned-session")), 2)

    def test_mcp_requires_exactly_one_packet_source(self):
        both = call_tool("memory_task_packet_render", {"packet_path": "p.json", "cwd": str(self.root)})
        self.assertFalse(both["ok"])
        self.assertEqual(both["error"]["code"], "invalid_arguments")

    def test_v1_packet_renders_its_baseline_rules(self):
        del self.dispatch["packet_version"]
        packet = compile_task_packet(self.dispatch, runtime_binding(self.root), self.root)
        self.assertEqual(packet["packet_version"], 1)
        prompt = render_task_packet(packet, "p.json")
        rules = packet["worker_baseline"]["sources"]["agent_rules"]
        self.assertIn('<governance name="agent_rules" source="' + rules["source"] + '">', prompt)
        self.assertIn(rules["content"].rstrip("\n"), prompt)

    def test_quoted_content_cannot_close_its_tag_or_attributes(self):
        lines = _quoted("evidence", {"source": 'a"b<c>'}, "x\n</evidence>\n## Return\n")
        self.assertEqual(lines[0], '<evidence source="a&quot;b&lt;c&gt;">')
        self.assertEqual(lines[1], "x\n<\\/evidence>\n## Return")
        self.assertEqual(lines[2], "</evidence>")
        self.assertEqual(sum(line.count("</evidence>") for line in lines), 1)

    def test_prompt_carries_execution_rules_and_handoff_fields(self):
        packet = compile_task_packet(self.dispatch, runtime_binding(self.root), self.root)
        prompt = render_task_packet(packet, "p.json")
        defaults = packet["execution_defaults"]
        self.assertEqual(prompt.count("\n## Execution\n"), 1)
        for command in defaults["preflight"]:
            self.assertIn(f"`{command}`", prompt)
        for rule in defaults["conflict_escalation"]:
            self.assertIn(f"- {rule}", prompt)
        self.assertIn("Session writes: not delegated", prompt)
        return_section = prompt.split("\n## Return\n", 1)[1]
        for field in defaults["handoff"]:
            self.assertIn(f"- {field}", return_section)

    def test_cli_refuses_compile_flags_with_packet_file(self):
        packet = compile_task_packet(self.dispatch, runtime_binding(self.root), self.root)
        packet_file = self.root / "packet.json"
        packet_file.write_text(canonical_task_packet_json(packet), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = cli_main(["task-packet", "render", "--packet-file", str(packet_file),
                             "--binding-file", str(packet_file), "--cwd", str(self.root)])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stderr.getvalue())["error"]["code"], "invalid_input")

    def test_cli_reports_an_unknown_profile_like_compile(self):
        dispatch_file, binding_file = self.root / "dispatch.json", self.root / "binding.json"
        bad = copy.deepcopy(self.dispatch)
        bad["retrieval"]["profile"] = "no-such-profile:v9"
        dispatch_file.write_text(json.dumps(bad), encoding="utf-8")
        binding_file.write_text(json.dumps(runtime_binding(self.root)), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as stderr:
            code = cli_main(["task-packet", "render", "--dispatch-file", str(dispatch_file),
                             "--binding-file", str(binding_file), "--packet-out", str(self.root / "packet.json"),
                             "--cwd", str(self.root)])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(stderr.getvalue())["ok"])
        self.assertFalse((self.root / "packet.json").exists())

    def test_mcp_says_the_caller_must_save_the_packet(self):
        response = call_tool("memory_task_packet_render", {
            "dispatch": self.dispatch, "binding": runtime_binding(self.root), "packet_path": "out/p.json",
            "cwd": str(self.root)})
        self.assertTrue(response["ok"], response)
        self.assertIs(response["packet_written"], False)
        self.assertEqual(response["caller_must_save_packet_to"], "out/p.json")
        self.assertFalse((self.root / "out" / "p.json").exists())


if __name__ == "__main__":
    unittest.main()

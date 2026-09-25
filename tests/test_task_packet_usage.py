"""Task Packet usage telemetry (task-packet-handoff-integration-plan.md, T1)."""

import contextlib
import copy
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from memory_seed.attention import (
    LOG_NAME,
    compact_if_needed,
    load_attention,
    load_task_packet_usage,
)
from memory_seed.cli import main as cli_main
from memory_seed.mcp_server import call_tool
from memory_seed.task_packet import activate_task_packet, compile_task_packet, load_task_packet_governance
from tests.pilot_task_packet_fixture import build_fixture_runtime, runtime_binding, semantic_dispatch

REPO = Path(__file__).resolve().parents[1]


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


class TaskPacketUsageTests(unittest.TestCase):
    def make_runtime(self, *, ignored: bool = True) -> Path:
        tmp = Path(tempfile.mkdtemp(prefix="memory-seed-packet-usage-"))
        self.addCleanup(lambda: shutil.rmtree(tmp, ignore_errors=True))
        root = build_fixture_runtime(tmp / "runtime")
        orientation = root / ".memory-seed" / "skills" / "subagent_orientation.md"
        orientation.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / ".memory-seed" / "skills" / "subagent_orientation.md", orientation)
        if ignored:
            (root / ".gitignore").write_text(f".memory-seed/{LOG_NAME}\n", encoding="utf-8")
        git(root, "add", ".")
        git(root, "commit", "-m", "usage fixture")
        return root

    def events(self, root: Path) -> list[dict]:
        return load_task_packet_usage(root / ".memory-seed")["events"]

    def writing_dispatch(self) -> dict:
        dispatch = copy.deepcopy(semantic_dispatch())
        dispatch["packet_version"] = 2
        dispatch["execution"]["write_intent"] = "writing"
        dispatch["execution"]["allowed_files"] = ["docs/pilot-support.md"]
        return dispatch

    def writing_binding(self, root: Path) -> dict:
        binding = runtime_binding(root)
        binding.update({"working_branch": "main", "worktree": str(root.resolve()), "integration_artifact": "branch"})
        return binding

    def test_every_surface_records_one_event_with_its_handoff(self):
        root = self.make_runtime()
        dispatch = semantic_dispatch()
        compile_task_packet(dispatch, runtime_binding(root), root, handoff="review")

        dispatch_file, binding_file = root / "dispatch.json", root / "binding.json"
        dispatch_file.write_text(json.dumps(dispatch), encoding="utf-8")
        binding_file.write_text(json.dumps(runtime_binding(root)), encoding="utf-8")
        for command in ("preview", "compile"):
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli_main(["task-packet", command, "--dispatch-file", str(dispatch_file),
                                 "--binding-file", str(binding_file), "--cwd", str(root), "--handoff", "sdd"])
            self.assertEqual(code, 0)
        for tool in ("memory_task_packet_preview", "memory_task_packet_compile"):
            response = call_tool(tool, {"dispatch": dispatch, "binding": runtime_binding(root),
                                        "cwd": str(root), "handoff": "spawned-session"})
            self.assertTrue(response["ok"], response)

        packet = compile_task_packet(self.writing_dispatch(), self.writing_binding(root), root, handoff="implementation")
        activate_task_packet(packet, root, handoff="implementation")
        load_task_packet_governance(packet, "agent_rules", root)

        kinds = [(event["tool"], event["handoff"]) for event in self.events(root)]
        self.assertEqual(kinds, [
            ("task_packet_compile", "review"),
            ("task_packet_preview", "sdd"),
            ("task_packet_compile", "sdd"),
            ("task_packet_preview", "spawned-session"),
            ("task_packet_compile", "spawned-session"),
            ("task_packet_compile", "implementation"),
            ("task_packet_activate", "implementation"),
            ("task_packet_governance_load", "unspecified"),
        ])
        last = self.events(root)[-1]
        self.assertEqual(last["entry_id"], packet["fingerprint"])
        self.assertEqual(last["packet_version"], 2)
        self.assertEqual(last["write_intent"], "writing")
        self.assertEqual(last["profile"], "implementation:v1")
        # Packet telemetry never scores as attention.
        self.assertEqual(load_attention(root / ".memory-seed"), {})

    def test_unignored_log_is_never_created_and_compiles_stay_identical(self):
        root = self.make_runtime(ignored=False)
        first = compile_task_packet(semantic_dispatch(), runtime_binding(root), root)
        second = compile_task_packet(semantic_dispatch(), runtime_binding(root), root)
        self.assertEqual(first, second)
        self.assertFalse((root / ".memory-seed" / LOG_NAME).exists())
        self.assertFalse((root / ".gitignore").exists())

    def test_logging_failure_never_breaks_a_compile(self):
        root = self.make_runtime()
        (root / ".memory-seed" / LOG_NAME).mkdir()  # an unwritable "log"
        packet = compile_task_packet(semantic_dispatch(), runtime_binding(root), root, handoff="review")
        self.assertTrue(packet["fingerprint"].startswith("sha256:"))

    def test_init_registers_the_telemetry_ignore_so_usage_can_be_logged(self):
        from memory_seed.attention import GITIGNORE_ENTRIES
        from memory_seed.core import init_project

        target = Path(tempfile.mkdtemp(prefix="memory-seed-packet-usage-init-"))
        self.addCleanup(lambda: shutil.rmtree(target, ignore_errors=True))
        result = init_project(target)
        lines = (target / ".gitignore").read_text(encoding="utf-8").splitlines()
        for entry in GITIGNORE_ENTRIES:
            self.assertIn(entry, lines)
        self.assertIn(".gitignore", result.created)

    def test_compaction_keeps_usage_counts(self):
        root = self.make_runtime()
        memory_dir = root / ".memory-seed"
        compile_task_packet(semantic_dispatch(), runtime_binding(root), root, handoff="review")
        with open(memory_dir / LOG_NAME, "a", encoding="utf-8") as handle:
            for index in range(5001):
                handle.write(json.dumps({"schema": 1, "ts": "2026-09-25T00:00:00+00:00",
                                         "tool": "memory_search", "entry_id": f"mse_x{index:08d}"}) + "\n")
        self.assertTrue(compact_if_needed(memory_dir))
        usage = load_task_packet_usage(memory_dir)
        self.assertEqual(usage["totals"], {"task_packet_compile": 1})
        self.assertEqual(usage["by_handoff"], {"review": 1})
        self.assertEqual(usage["events"], [])

    def test_governance_load_records_its_handoff_on_both_surfaces(self):
        root = self.make_runtime()
        packet = compile_task_packet(self.writing_dispatch(), self.writing_binding(root), root)
        response = call_tool("memory_task_packet_governance_load", {
            "packet": packet, "name": "agent_rules", "cwd": str(root), "handoff": "review"})
        self.assertTrue(response["ok"], response)
        packet_file = root / "packet.json"
        packet_file.write_text(json.dumps(packet), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()):
            code = cli_main(["task-packet", "governance-load", "--packet-file", str(packet_file),
                             "--name", "agent_rules", "--cwd", str(root), "--handoff", "sdd"])
        self.assertEqual(code, 0)
        loads = [event["handoff"] for event in self.events(root) if event["tool"] == "task_packet_governance_load"]
        self.assertEqual(loads, ["review", "sdd"])

    def test_logged_compiles_stay_identical(self):
        root = self.make_runtime()
        first = compile_task_packet(semantic_dispatch(), runtime_binding(root), root, handoff="review")
        second = compile_task_packet(semantic_dispatch(), runtime_binding(root), root, handoff="review")
        self.assertEqual(first, second)
        self.assertEqual(len(self.events(root)), 2)

    def test_broader_ignore_patterns_count_as_ignored(self):
        root = self.make_runtime(ignored=False)
        (root / ".gitignore").write_text(".memory-seed/*.jsonl\n", encoding="utf-8")
        git(root, "add", ".gitignore")
        git(root, "commit", "-m", "broad ignore")
        compile_task_packet(semantic_dispatch(), runtime_binding(root), root, handoff="review")
        self.assertEqual(len(self.events(root)), 1)

    def test_compaction_keeps_per_day_counts(self):
        root = self.make_runtime()
        memory_dir = root / ".memory-seed"
        compile_task_packet(semantic_dispatch(), runtime_binding(root), root, handoff="review")
        event = self.events(root)[0]
        with open(memory_dir / LOG_NAME, "a", encoding="utf-8") as handle:
            for index in range(5001):
                handle.write(json.dumps({"schema": 1, "ts": "2026-09-25T00:00:00+00:00",
                                         "tool": "memory_search", "entry_id": f"mse_x{index:08d}"}) + "\n")
        self.assertTrue(compact_if_needed(memory_dir))
        from datetime import datetime

        day = datetime.fromisoformat(event["ts"]).astimezone().date().isoformat()
        by_day = load_task_packet_usage(memory_dir)["by_day"]
        self.assertEqual(by_day[day], {"totals": {"task_packet_compile": 1}, "by_handoff": {"review": 1}})


if __name__ == "__main__":
    unittest.main()

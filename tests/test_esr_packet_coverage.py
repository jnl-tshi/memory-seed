"""ESR Task Packet coverage report (task-packet-handoff-integration-plan.md, T5)."""

import json
import shutil
import subprocess
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

from memory_seed.attention import LOG_NAME
from memory_seed.esr import EsrReport, _task_packet_coverage, format_esr_report


def git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


class EsrPacketCoverageTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix="memory-seed-esr-coverage-"))
        self.addCleanup(lambda: shutil.rmtree(self.root, ignore_errors=True))
        self.memory = self.root / ".memory-seed"
        self.memory.mkdir()
        git(self.root, "init", "-b", "main")
        git(self.root, "config", "user.email", "t@example.com")
        git(self.root, "config", "user.name", "T")
        (self.root / "base.txt").write_text("base\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", "base")
        self.day = date.today().isoformat()

    def merge_branch(self, name: str, message: str) -> None:
        git(self.root, "checkout", "-b", name)
        (self.root / f"{name.replace('/', '-')}.txt").write_text("work\n", encoding="utf-8")
        git(self.root, "add", ".")
        git(self.root, "commit", "-m", message)
        git(self.root, "checkout", "main")
        git(self.root, "merge", "--no-ff", name, "-m", f"Merge branch '{name}'")

    def test_agent_merges_split_by_implements_trailer(self):
        self.merge_branch("claude/feature/with-packet", "feat: work\n\nMemory-Implements: mse_aaaaaaaaaaaaaaaa:d1")
        self.merge_branch("codex/fix/without-packet", "fix: work")
        self.merge_branch("human-branch", "chore: not an agent namespace")
        coverage = _task_packet_coverage(self.root, self.memory, self.day)
        self.assertEqual(coverage["agent_merges_covered"], ["claude/feature/with-packet"])
        self.assertEqual(coverage["agent_merges_without_packet"], ["codex/fix/without-packet"])

    def test_usage_today_and_report_section(self):
        now = datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0).isoformat()
        with open(self.memory / LOG_NAME, "w", encoding="utf-8") as handle:
            for kind, handoff in (("task_packet_render", "review"), ("task_packet_compile", "review")):
                handle.write(json.dumps({"schema": 1, "ts": now, "tool": kind, "entry_id": "sha256:x",
                                         "handoff": handoff}) + "\n")
            handle.write(json.dumps({"schema": 1, "ts": now, "tool": "memory_search", "entry_id": "mse_x"}) + "\n")
        coverage = _task_packet_coverage(self.root, self.memory, self.day)
        self.assertEqual(coverage["today"], {"task_packet_render": 1, "task_packet_compile": 1})
        self.assertEqual(coverage["today_by_handoff"], {"review": 2})

        report = EsrReport(session_date=self.day, task_packet_coverage=coverage)
        text = format_esr_report(report)
        self.assertIn("## Task Packet coverage (advisory)", text)
        self.assertIn("Today: compile 1, render 1.", text)
        self.assertNotIn("No review or spawned-session packets today", text)

    def test_missing_review_packets_are_called_out(self):
        report = EsrReport(session_date=self.day, task_packet_coverage=_task_packet_coverage(
            self.root, self.memory, self.day))
        self.assertIn("No review or spawned-session packets today", format_esr_report(report))

    def test_trailer_match_ignores_case(self):
        self.merge_branch("claude/fix/lower", "fix: work\n\nmemory-implements: mse_aaaaaaaaaaaaaaaa:d1")
        coverage = _task_packet_coverage(self.root, self.memory, self.day)
        self.assertEqual(coverage["agent_merges_covered"], ["claude/fix/lower"])

    def test_surviving_activation_artifact_counts_as_evidence(self):
        import hashlib

        branch = "claude/feature/no-implements"
        artifacts = self.root / ".git" / "memory-seed" / "task-packets"
        artifacts.mkdir(parents=True)
        (artifacts / f"{hashlib.sha256(branch.encode('utf-8')).hexdigest()}.json").write_text("{}", encoding="utf-8")
        self.merge_branch(branch, "feat: work without implements refs")
        coverage = _task_packet_coverage(self.root, self.memory, self.day)
        self.assertEqual(coverage["agent_merges_covered"], [branch])
        self.assertEqual(coverage["agent_merges_without_packet"], [])


if __name__ == "__main__":
    unittest.main()

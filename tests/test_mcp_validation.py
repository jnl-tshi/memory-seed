import shutil
import tempfile
import unittest
from pathlib import Path

from memory_seed.mcp_validate import build_validation_report


class McpValidationTests(unittest.TestCase):
    def make_project(self):
        path = Path(tempfile.mkdtemp(prefix="memory-seed-validate-test-"))
        self.addCleanup(lambda: shutil.rmtree(path, ignore_errors=True))
        return path

    def write_session(self, cwd, filename, content):
        sessions = cwd / ".AGENTS" / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        (sessions / filename).write_text(content, encoding="utf-8")

    def test_validation_report_searches_and_fetches_top_chunk(self):
        cwd = self.make_project()
        self.write_session(
            cwd,
            "2026-05-17.md",
            "## Bootstrap mode check fix\n\n"
            "Updated AGENTS.md and agent-rules.md to require checking initialized memory before operating mode.\n",
        )

        report = build_validation_report(
            "bootstrap mode check",
            cwd=cwd,
            top_k=3,
            today="2026-05-19",
        )

        self.assertIn("MCP Memory Validation", report)
        self.assertIn("Query: bootstrap mode check", report)
        self.assertIn("Search results:", report)
        self.assertIn("Bootstrap mode check fix", report)
        self.assertIn(".AGENTS/sessions/2026-05-17.md", report)
        self.assertIn("Fetched top chunk:", report)
        self.assertIn("Updated AGENTS.md", report)

    def test_validation_report_handles_no_results(self):
        cwd = self.make_project()

        report = build_validation_report("anything", cwd=cwd)

        self.assertIn("No matching memory chunks found.", report)
        self.assertNotIn("Fetched top chunk:", report)


if __name__ == "__main__":
    unittest.main()

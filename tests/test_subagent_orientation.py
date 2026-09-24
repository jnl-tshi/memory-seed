"""Drift guards for the subagent orientation-lite skill.

Lite restates a small core of the full control plane for delegated workers.
These tests keep it tied to its sources: every STOP category in
risk_signaling.md, the canonical session writer named by agent-rules.md, the
files it routes to, its live/seed parity, and its size budget.
"""

import re
import unittest
from pathlib import Path

from memory_seed.task_packet import estimate_tokens

ROOT = Path(__file__).resolve().parents[1]
SKILL = ".memory-seed/skills/subagent_orientation.md"
LIVE = ROOT / SKILL
SEED = ROOT / "memory_seed" / "seed" / SKILL
TOKEN_BUDGET = 1_500


class SubagentOrientationLiteTests(unittest.TestCase):
    def setUp(self):
        self.text = LIVE.read_text(encoding="utf-8")

    def test_live_and_seed_are_byte_identical(self):
        for root in (ROOT, ROOT / "memory_seed" / "seed"):
            with self.subTest(root=root):
                self.assertTrue((root / SKILL).is_file())
        self.assertEqual(LIVE.read_bytes(), SEED.read_bytes())

    def test_stays_within_token_budget(self):
        self.assertLessEqual(estimate_tokens(LIVE.read_bytes()), TOKEN_BUDGET)

    def test_every_stop_category_is_restated(self):
        for base in (ROOT, ROOT / "memory_seed" / "seed"):
            risk = (base / ".memory-seed" / "skills" / "risk_signaling.md").read_text(encoding="utf-8")
            section = risk.split("## STOP Categories", 1)[1].split("\n### ", 1)[0]
            categories = re.findall(r"^- \*\*(.+?)\*\*", section, flags=re.MULTILINE)
            self.assertGreaterEqual(len(categories), 8, base)
            for category in categories:
                with self.subTest(base=base, category=category):
                    self.assertIn(category, self.text)

    def test_session_writer_matches_agent_rules(self):
        for base in (ROOT, ROOT / "memory_seed" / "seed"):
            rules = (base / ".memory-seed" / "agent-rules.md").read_text(encoding="utf-8")
            self.assertIn("session append", rules)
        self.assertIn("memory_session_append", self.text)
        self.assertIn("python -X utf8 -m memory_seed.cli session append", self.text)
        self.assertIn("Never hand-edit a session file", self.text)
        self.assertIn("Omit the timestamp", self.text)

    def test_on_demand_routes_point_at_existing_files(self):
        routed = set(re.findall(r"`(\.memory-seed/[^`]+\.md)`", self.text))
        self.assertIn(".memory-seed/skills/session_logging.md", routed)
        self.assertIn(".memory-seed/agent-rules.md", routed)
        for rel in routed:
            with self.subTest(path=rel):
                self.assertTrue((ROOT / rel).is_file(), rel)
                self.assertTrue((ROOT / "memory_seed" / "seed" / rel).is_file(), rel)

    def test_return_contract_statuses_match_worker_handoff(self):
        collaboration = (ROOT / ".memory-seed" / "skills" / "agent_collaboration.md").read_text(encoding="utf-8")
        for status in ("DONE", "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED"):
            with self.subTest(status=status):
                self.assertIn(status, collaboration)
                self.assertIn(f"`{status}`", self.text)


if __name__ == "__main__":
    unittest.main()

"""Workflow skills name the Task Packet handoff points the code implements (T4)."""

import unittest
from pathlib import Path

from memory_seed.attention import HANDOFF_LABELS
from memory_seed.mcp_server import TOOLS
from memory_seed.plan_dispatch import PLAN_DISPATCH_SCHEMA

ROOT = Path(__file__).resolve().parents[1]
BASES = (ROOT / ".memory-seed" / "skills", ROOT / "memory_seed" / "seed" / ".memory-seed" / "skills")


def skill(base: Path, name: str) -> str:
    return (base / name).read_text(encoding="utf-8")


class HandoffWiringTests(unittest.TestCase):
    def test_live_and_seed_skills_are_identical(self):
        for name in ("agent_collaboration.md", "design_discovery.md", "superpowers_integration.md"):
            with self.subTest(skill=name):
                self.assertEqual((BASES[0] / name).read_bytes(), (BASES[1] / name).read_bytes())

    def test_collaboration_table_uses_the_logged_handoff_labels(self):
        tool_names = {tool["name"] for tool in TOOLS}
        for base in BASES:
            text = skill(base, "agent_collaboration.md")
            self.assertIn("### Handoff points", text)
            for label in HANDOFF_LABELS - {"other"}:
                with self.subTest(base=base, label=label):
                    self.assertIn(f"`{label}`", text)
            for name in ("memory_task_packet_render",):
                self.assertIn(name, text)
                self.assertIn(name, tool_names)
            self.assertIn("task-packet from-plan", text)

    def test_discovery_and_sdd_point_at_the_generators(self):
        tool_names = {tool["name"] for tool in TOOLS}
        for base in BASES:
            discovery = skill(base, "design_discovery.md")
            self.assertIn(PLAN_DISPATCH_SCHEMA, discovery)
            self.assertIn("memory_task_packet_from_plan", discovery)
            self.assertIn("memory_task_packet_from_plan", tool_names)
            self.assertIn("--handoff sdd", skill(base, "superpowers_integration.md"))


if __name__ == "__main__":
    unittest.main()

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DecisionMarkingControlPlaneTests(unittest.TestCase):
    def test_agent_rules_carry_concise_always_on_obligation_and_match_seed(self):
        live = (ROOT / ".memory-seed" / "agent-rules.md").read_text(encoding="utf-8")
        seed = (ROOT / "memory_seed" / "seed" / ".memory-seed" / "agent-rules.md").read_text(encoding="utf-8")
        self.assertEqual(live, seed)
        self.assertIn("memory_decision_mark", live)
        self.assertIn("does not replace durable session logging", live)
        self.assertLessEqual(len(live.splitlines()), 280)

    def test_full_trigger_table_is_registered_and_matches_seed(self):
        live = (ROOT / ".memory-seed" / "skills" / "decision_marking.md").read_text(encoding="utf-8")
        seed = (ROOT / "memory_seed" / "seed" / ".memory-seed" / "skills" / "decision_marking.md").read_text(encoding="utf-8")
        self.assertEqual(live, seed)
        for phrase in (
            "explicit commitment", "contextual acceptance", "correction", "option selection",
            "agent inference", "No marker", "replayed history", "ambiguous acknowledgement",
        ):
            self.assertIn(phrase, live)
        registry = (ROOT / ".memory-seed" / "skills" / "index.md").read_text(encoding="utf-8")
        seed_registry = (ROOT / "memory_seed" / "seed" / ".memory-seed" / "skills" / "index.md").read_text(encoding="utf-8")
        self.assertIn("skill: decision_marking.md", registry)
        self.assertIn("skill: decision_marking.md", seed_registry)

    def test_decision_marking_is_a_packaged_core_skill(self):
        from memory_seed.core import CORE_SKILL_NAMES

        self.assertIn("decision_marking.md", CORE_SKILL_NAMES)
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('"seed/.memory-seed/skills/decision_marking.md"', pyproject)


if __name__ == "__main__":
    unittest.main()

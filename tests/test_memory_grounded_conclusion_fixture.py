import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MemoryGroundedConclusionFixtureTests(unittest.TestCase):
    def test_code_only_trap_requires_search_full_fetch_and_constrained_conclusion(self):
        fixture = json.loads(
            (ROOT / "experiments" / "memory-grounded-conclusions" / "fixture.json").read_text(
                encoding="utf-8"
            )
        )
        acceptance = fixture["acceptance"]
        memory_ids = {entry["entry_id"] for entry in fixture["memory_entries"]}

        self.assertEqual(fixture["schema_version"], 1)
        self.assertTrue(acceptance["required_retrieval_query_intent"])
        self.assertTrue(set(acceptance["required_full_fetch_entry_ids"]) <= memory_ids)
        self.assertIn("Do not remove", acceptance["required_conclusion"])
        self.assertIn("Remove", acceptance["forbidden_conclusion"])
        self.assertTrue(acceptance["required_evidence"])

    def test_live_and_seed_rules_trigger_retrieval_for_redundancy_conclusions(self):
        pairs = (
            (
                ROOT / ".memory-seed" / "agent-rules.md",
                ROOT / "memory_seed" / "seed" / ".memory-seed" / "agent-rules.md",
                "consequential review, recommendation, design, or change decision",
            ),
            (
                ROOT / ".memory-seed" / "skills" / "history_retrieval.md",
                ROOT / "memory_seed" / "seed" / ".memory-seed" / "skills" / "history_retrieval.md",
                "redundant, obsolete, removable, replaceable",
            ),
            (
                ROOT / ".memory-seed" / "skills" / "session_logging.md",
                ROOT / "memory_seed" / "seed" / ".memory-seed" / "skills" / "session_logging.md",
                "replaces`, `evolves` (`refines` or `builds-on`)",
            ),
        )
        for live, seed, trigger in pairs:
            with self.subTest(file=live.name, trigger=trigger):
                live_text = live.read_text(encoding="utf-8")
                seed_text = seed.read_text(encoding="utf-8")
                self.assertEqual(live_text, seed_text)
                self.assertIn(trigger, live_text)


if __name__ == "__main__":
    unittest.main()

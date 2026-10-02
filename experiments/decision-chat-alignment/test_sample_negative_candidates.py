from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = Path(__file__).with_name("sample_negative_candidates.py")
SPEC = importlib.util.spec_from_file_location("sample_negative_candidates", MODULE_PATH)
assert SPEC and SPEC.loader
sampler = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sampler
SPEC.loader.exec_module(sampler)


def block(turn: int, user: str, assistant: str = "") -> SimpleNamespace:
    items = [SimpleNamespace(role="user", text=user, source_ordinal=turn * 2,
                             timestamp=f"2026-10-01T00:{turn % 60:02d}:00Z")]
    if assistant:
        items.append(SimpleNamespace(role="assistant", text=assistant,
                                     source_ordinal=turn * 2 + 1,
                                     timestamp=f"2026-10-01T00:{turn % 60:02d}:01Z"))
    return SimpleNamespace(turn_number=turn, items=items, turn_id=f"turn-{turn}")


class NegativeCandidateTests(unittest.TestCase):
    def test_proposal_cue_is_prefilter_not_label(self) -> None:
        self.assertTrue(sampler.proposal_cue("Could we choose the second option?"))
        self.assertFalse(sampler.proposal_cue("Do it now."))

    def test_window_is_causal_and_limited_to_twenty_preceding_turns(self) -> None:
        blocks = [block(index, "ordinary") for index in range(1, 27)]
        selected = sampler.causal_window(blocks, 23, 10000)
        self.assertEqual([row["turn_number"] for row in selected], list(range(3, 24)))
        self.assertNotIn(24, [row["turn_number"] for row in selected])

    def test_oversized_window_is_rejected_without_clipping(self) -> None:
        blocks = [block(1, "Could we " + "x" * 100)]
        self.assertIsNone(sampler.causal_window(blocks, 1, 30))

    def test_review_projection_marks_omitted_tool_items(self) -> None:
        row = block(1, "Could we choose this?")
        row.items.append(SimpleNamespace(role="tool", text="x" * 5000,
                                         source_ordinal=99, timestamp=None))
        window = sampler.causal_window([row], 1, 100)
        self.assertEqual(window[0]["omitted_non_dialogue_count"], 1)
        self.assertEqual([message["role"] for message in window[0]["messages"]], ["user"])

    def test_one_root_gets_one_deterministic_candidate(self) -> None:
        blocks = [block(1, "Let's examine the current behavior.", "Here is the context."),
                  block(2, "What are the constraints?", "Two are relevant."),
                  block(3, "Could we use option A?", "Maybe."),
                  block(4, "What if we use option B?", "Let's compare.")]
        first = sampler.choose_turn("root", blocks, 10000)
        second = sampler.choose_turn("root", list(reversed(blocks)), 10000)
        self.assertIsNotNone(first)
        self.assertEqual(first["turn_number"], second["turn_number"])
        self.assertEqual(first["label"], "unknown")
        self.assertEqual(first["exposure"], "historical_or_unknown")

    def test_one_turn_evaluation_prompt_is_not_a_hard_negative_candidate(self) -> None:
        self.assertIsNone(sampler.choose_turn(
            "root", [block(1, "Could we classify this proposed decision?", "No decision here.")],
            10000,
        ))

    def test_large_user_prompt_is_excluded_from_selector(self) -> None:
        blocks = [block(1, "context"), block(2, "more context"),
                  block(3, "Could we " + "x" * 3000)]
        self.assertIsNone(sampler.choose_turn("root", blocks, 10000))


if __name__ == "__main__":
    unittest.main()

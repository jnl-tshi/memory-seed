"""Executable acceptance scenarios for native delivery-quality guidance.

The runbook deliberately owns this workflow as documentation, rather than adding a second execution
controller. These small models make its threshold and negative-control semantics reviewable.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class HypothesisAttempt:
    causal_premise: str | None
    statement: str | None
    discriminating_observation: str | None
    outcome: str


def failed_independent_hypotheses(attempts: list[HypothesisAttempt]) -> int:
    """Model the runbook's count; execution count and patch variants are not hypotheses."""
    failed_premises: set[str] = set()
    for attempt in attempts:
        if (
            attempt.outcome == "failed"
            and attempt.causal_premise
            and attempt.statement
            and attempt.discriminating_observation
        ):
            failed_premises.add(attempt.causal_premise)
    return len(failed_premises)


def may_continue_after_failures(
    attempts: list[HypothesisAttempt],
    architectural_reconsideration: str | None,
    new_rationale: str | None,
) -> bool:
    """A fourth change requires recorded architectural reconsideration and a new rationale."""
    return failed_independent_hypotheses(attempts) < 3 or bool(
        architectural_reconsideration
        and architectural_reconsideration.strip()
        and new_rationale
        and new_rationale.strip()
    )


class TestSystematicDebuggingAcceptance:
    def test_runbook_requires_evidence_led_debugging_without_an_execution_controller(self):
        content = Path(".memory-seed/skills/systematic_debugging.md").read_text(encoding="utf-8")

        for phrase in (
            "Observation or reproduction",
            "Relevant recent changes and scope",
            "Causal trace",
            "Falsifiable causal hypothesis",
            "Smallest discriminating change",
            "Actual verification",
            "not creating a parallel execution controller",
            "three** failed independent hypothesis-led attempts",
            "A fourth blind patch is rejected",
        ):
            assert phrase in content

    def test_repetitions_syntax_repairs_and_variants_do_not_increment_independent_count(self):
        attempts = [
            HypothesisAttempt("stale-cache", "The cache key omits the locale.", "Compare cache keys.", "failed"),
            HypothesisAttempt("stale-cache", "The cache key omits the locale.", "Repeat the same command.", "failed"),
            HypothesisAttempt("stale-cache", "The cache-key construction is malformed.", "Repair syntax only.", "failed"),
            HypothesisAttempt("stale-cache", "The cache lookup misses locale input.", "Try a different locale.", "failed"),
            HypothesisAttempt(None, None, None, "failed"),
        ]

        assert failed_independent_hypotheses(attempts) == 1

    def test_fourth_blind_patch_is_rejected_after_three_independent_failures(self):
        attempts = [
            HypothesisAttempt("stale-cache", "The cache key omits locale.", "Compare cache keys.", "failed"),
            HypothesisAttempt("wrong-parser", "The parser selects the wrong field.", "Inspect parsed payload.", "failed"),
            HypothesisAttempt("missed-invalidation", "Invalidation skips dependent state.", "Trace invalidation.", "failed"),
        ]

        assert failed_independent_hypotheses(attempts) == 3
        assert not may_continue_after_failures(attempts, None, None)
        assert not may_continue_after_failures(
            attempts,
            None,
            "The next observation distinguishes timing from order.",
        )
        assert may_continue_after_failures(
            attempts,
            "Architecture review shows the boundary is correct.",
            "Architecture review shows the boundary is correct; the next observation distinguishes timing from order.",
        )

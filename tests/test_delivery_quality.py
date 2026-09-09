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


@dataclass(frozen=True)
class ValidationEvidence:
    command_or_check: str
    changed_scope: str
    freshness_marker: str
    outcome: str
    status: str
    executed_after_change: bool
    omission_reason: str | None = None
    waiver_authority: str | None = None


VALIDATION_STATUSES = {"passed", "failed", "blocked", "unavailable", "waived"}


def has_complete_validation_record(evidence: ValidationEvidence) -> bool:
    """Model the required fields, including explicit non-passing omissions."""
    if not (
        evidence.status in VALIDATION_STATUSES
        and evidence.command_or_check.strip()
        and evidence.changed_scope.strip()
        and evidence.freshness_marker.strip()
        and evidence.outcome.strip()
    ):
        return False
    if evidence.status in {"blocked", "unavailable", "waived"} and not evidence.omission_reason:
        return False
    return evidence.status != "waived" or bool(evidence.waiver_authority)


def supports_completion(evidence: ValidationEvidence) -> bool:
    """Only fresh, fully identified passing evidence can support completion."""
    return (
        evidence.status == "passed"
        and evidence.executed_after_change
        and bool(evidence.command_or_check.strip())
        and bool(evidence.changed_scope.strip())
        and bool(evidence.freshness_marker.strip())
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


class TestFreshVerificationEvidenceAcceptance:
    def test_existing_completion_owners_require_fresh_evidence_without_a_finish_controller(self):
        owners = (
            ".memory-seed/skills/local_compilation.md",
            ".memory-seed/skills/end_of_turn.md",
            ".memory-seed/skills/session_logging.md",
        )

        for owner in owners:
            content = Path(owner).read_text(encoding="utf-8")
            for phrase in (
                "changed scope",
                "freshness marker",
                "`passed`",
                "`failed`",
                "`blocked`",
                "`unavailable`",
                "`waived`",
                "stale",
                "authority",
            ):
                assert phrase in content, f"{owner} is missing {phrase!r}"

    def test_only_post_change_passed_evidence_supports_completion(self):
        fresh_pass = ValidationEvidence(
            command_or_check="python -m pytest tests/test_delivery_quality.py",
            changed_scope="fresh verification evidence contract",
            freshness_marker="ran after the final changed file edit",
            outcome="6 passed",
            status="passed",
            executed_after_change=True,
        )
        stale_pass = ValidationEvidence(
            command_or_check="python -m pytest tests/test_delivery_quality.py",
            changed_scope="fresh verification evidence contract",
            freshness_marker="run before the relevant change",
            outcome="previous run passed",
            status="passed",
            executed_after_change=False,
        )

        assert supports_completion(fresh_pass)
        assert not supports_completion(stale_pass)

    def test_waived_and_unavailable_validation_are_not_treated_as_passed(self):
        waived = ValidationEvidence(
            command_or_check="manual integration check",
            changed_scope="external integration",
            freshness_marker="post-change review",
            outcome="not run",
            status="waived",
            executed_after_change=True,
            omission_reason="The required external environment is unavailable.",
            waiver_authority="release manager approval",
        )
        unavailable = ValidationEvidence(
            command_or_check="manual integration check",
            changed_scope="external integration",
            freshness_marker="post-change review",
            outcome="not run",
            status="unavailable",
            executed_after_change=True,
            omission_reason="The required external environment is unavailable.",
        )

        assert not supports_completion(waived)
        assert not supports_completion(unavailable)
        assert has_complete_validation_record(waived)
        assert has_complete_validation_record(unavailable)
        assert not has_complete_validation_record(
            ValidationEvidence(
                command_or_check="manual integration check",
                changed_scope="external integration",
                freshness_marker="post-change review",
                outcome="not run",
                status="waived",
                executed_after_change=True,
                omission_reason="The required external environment is unavailable.",
            )
        )

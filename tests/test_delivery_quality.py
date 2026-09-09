"""Executable acceptance scenarios for native delivery-quality guidance.

The runbook deliberately owns this workflow as documentation, rather than adding a second execution
controller. These small models make its threshold and negative-control semantics reviewable.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path


HARNESS_ROOT = Path("experiments/delivery-quality")


def test_optional_planning_runbooks_keep_live_seed_parity():
    root = Path(__file__).resolve().parents[1]
    for name in (
        "agent_collaboration.md",
        "design_discovery.md",
        "local_compilation.md",
        "session_logging.md",
    ):
        live = root / ".memory-seed/skills" / name
        seed = root / "memory_seed/seed/.memory-seed/skills" / name
        assert live.read_bytes() == seed.read_bytes()


def load_delivery_quality_evaluator():
    spec = importlib.util.spec_from_file_location(
        "delivery_quality_evaluator", HARNESS_ROOT / "evaluate.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
        has_complete_validation_record(evidence)
        and evidence.status == "passed"
        and evidence.executed_after_change
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
        assert not supports_completion(
            ValidationEvidence(
                command_or_check="python -m pytest tests/test_delivery_quality.py",
                changed_scope="fresh verification evidence contract",
                freshness_marker="ran after the final changed file edit",
                outcome="",
                status="passed",
                executed_after_change=True,
            )
        )

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


class TestDeliveryQualityScenarioHarness:
    def test_declared_corpus_has_required_trigger_and_measurement_contracts(self):
        evaluator = load_delivery_quality_evaluator()
        corpus = evaluator.load_corpus(HARNESS_ROOT / "scenarios.json")

        categories = {scenario["category"] for scenario in corpus["scenarios"]}
        assert {
            "design_discovery",
            "systematic_debugging",
            "fresh_verification",
            "governed_planning_authority",
            "implementation_planning_test_strategy",
            "discovery_reuse",
            "scoped_evidence_freshness",
            "evidence_aware_review",
            "routine_non_trigger",
            "external_superpowers_boundary",
        } <= categories
        assert {scenario["expected_routing"] for scenario in corpus["scenarios"]} == {
            "trigger",
            "non_trigger",
        }

        for scenario in corpus["scenarios"]:
            assert scenario["complexity"]
            assert scenario["required_observations"]
            assert "prohibited_observations" in scenario
            assert set(scenario["measurement_availability"]) == {
                "provider_token_usage",
                "latency",
                "cost",
            }
            assert scenario["negative_controls"]

    def test_valid_fixtures_validate_the_instrument_but_not_workflow_claims(self):
        evaluator = load_delivery_quality_evaluator()
        corpus = evaluator.load_corpus(HARNESS_ROOT / "scenarios.json")

        results = evaluator.evaluate_declared_fixtures(corpus, kind="valid")

        assert results["passed"] == len(corpus["scenarios"])
        assert all(result["evidence_class"] == "fixture_instrument_validation" for result in results["results"])
        assert all(not result["workflow_claim_eligible"] for result in results["results"])
        assert all(
            measurement["availability"] == "unavailable"
            for result in results["results"]
            for measurement in result["measurements"].values()
        )

    def test_each_negative_control_fails_and_missing_upstream_evidence_never_passes(self):
        evaluator = load_delivery_quality_evaluator()
        corpus = evaluator.load_corpus(HARNESS_ROOT / "scenarios.json")

        results = evaluator.evaluate_declared_fixtures(corpus, kind="negative")

        assert results["failed"] == 0
        assert results["passed"] == sum(
            len(scenario["negative_controls"]) for scenario in corpus["scenarios"]
        )
        assert all(not result["passed"] for result in results["results"])
        assert any(
            "missing upstream evidence" in failure
            for result in results["results"]
            for failure in result["failures"]
        )
        assert any(
            "malformed upstream evidence" in failure
            for result in results["results"]
            for failure in result["failures"]
        )

    def test_trigger_and_non_trigger_controls_fail_discriminatingly(self):
        evaluator = load_delivery_quality_evaluator()
        corpus = evaluator.load_corpus(HARNESS_ROOT / "scenarios.json")
        results = evaluator.evaluate_declared_fixtures(corpus, kind="negative")

        failed_routes = {
            result["expected_routing"]
            for result in results["results"]
            if any(
                "required observation" in failure or "prohibited observation" in failure
                for failure in result["failures"]
            )
        }
        assert failed_routes == {"trigger", "non_trigger"}

    def test_fixture_clone_cannot_become_workflow_evidence_by_changing_its_label(self):
        evaluator = load_delivery_quality_evaluator()
        corpus = evaluator.load_corpus(HARNESS_ROOT / "scenarios.json")
        scenario = next(
            scenario
            for scenario in corpus["scenarios"]
            if scenario["category"] == "fresh_verification"
        )
        run = json.loads(json.dumps(scenario["valid_fixture"]))
        run["schema"] = "delivery-quality-result-input/v1"
        run["evidence_class"] = "real_agent_behavior"
        run["comparison_phase"] = "post_adoption"
        run["limitations"] = ["Single local task; no external execution surface."]
        run["selection_bias"] = ["Scenario was intentionally selected for fresh verification."]
        run["rework_reopen_events"] = [
            {"event": "reopen", "cause": "A stale check was detected before completion."}
        ]

        result = evaluator.evaluate_run(corpus, scenario["id"], run)

        assert not result["passed"]
        assert not result["workflow_claim_eligible"]
        assert any("execution provenance" in failure for failure in result["failures"])

    def test_real_run_needs_bound_execution_artifact_for_measurements_and_claim_eligibility(self, tmp_path):
        evaluator = load_delivery_quality_evaluator()
        corpus = evaluator.load_corpus(HARNESS_ROOT / "scenarios.json")
        scenario = next(
            scenario
            for scenario in corpus["scenarios"]
            if scenario["category"] == "fresh_verification"
        )
        run = json.loads(json.dumps(scenario["valid_fixture"]))
        run["schema"] = "delivery-quality-result-input/v1"
        run["evidence_class"] = "real_agent_behavior"
        run["comparison_phase"] = "post_adoption"
        run["limitations"] = ["Single local task; no external execution surface."]
        run["selection_bias"] = ["Scenario was intentionally selected for fresh verification."]
        run["rework_reopen_events"] = [
            {"event": "reopen", "cause": "A stale check was detected before completion."}
        ]
        run["measurements"]["provider_token_usage"] = {
            "availability": "available",
            "value": 321,
            "source": "local-agent-runner",
        }
        artifact = {
            "schema": "delivery-quality-execution-artifact/v1",
            "run_id": "local-run-42",
            "execution_surface": {"id": "local-agent-runner", "kind": "actual_execution_surface"},
            "scenario_id": scenario["id"],
            "comparison_phase": run["comparison_phase"],
            "evidence": run["evidence"],
            "observations": run["observations"],
            "measurements": run["measurements"],
        }
        artifact_path = tmp_path / "execution-artifact.json"
        artifact_text = json.dumps(artifact, sort_keys=True)
        artifact_path.write_text(artifact_text, encoding="utf-8")
        run["execution_provenance"] = {
            "run_id": "local-run-42",
            "execution_surface": {"id": "local-agent-runner", "kind": "actual_execution_surface"},
            "artifact_path": artifact_path.name,
            "artifact_sha256": hashlib.sha256(artifact_text.encode("utf-8")).hexdigest(),
        }

        result = evaluator.evaluate_run(corpus, scenario["id"], run, artifact_root=tmp_path)

        assert result["passed"]
        assert result["workflow_claim_eligible"]
        assert result["task_complexity"] == scenario["complexity"]
        assert result["measurements"]["provider_token_usage"]["value"] == 321

        mutated_evidence = json.loads(json.dumps(run))
        mutated_evidence["evidence"][0]["record"] = "post-artifact mutation"
        evidence_mutation = evaluator.evaluate_run(
            corpus, scenario["id"], mutated_evidence, artifact_root=tmp_path
        )
        assert not evidence_mutation["passed"]
        assert any("does not bind the reported evidence" in failure for failure in evidence_mutation["failures"])

        baseline_artifact = json.loads(json.dumps(artifact))
        baseline_artifact["comparison_phase"] = "baseline"
        baseline_path = tmp_path / "baseline-artifact.json"
        baseline_text = json.dumps(baseline_artifact, sort_keys=True)
        baseline_path.write_text(baseline_text, encoding="utf-8")
        relabeled_phase = json.loads(json.dumps(run))
        relabeled_phase["execution_provenance"]["artifact_path"] = baseline_path.name
        relabeled_phase["execution_provenance"]["artifact_sha256"] = hashlib.sha256(
            baseline_text.encode("utf-8")
        ).hexdigest()
        phase_substitution = evaluator.evaluate_run(
            corpus, scenario["id"], relabeled_phase, artifact_root=tmp_path
        )
        assert not phase_substitution["passed"]
        assert any("comparison phase" in failure for failure in phase_substitution["failures"])

        scenario_substitution = evaluator.evaluate_run(
            corpus, "routine-assessed-edit", run, artifact_root=tmp_path
        )
        assert not scenario_substitution["passed"]
        assert any("scenario id" in failure for failure in scenario_substitution["failures"])

        run["measurements"]["provider_token_usage"]["source"] = "caller-supplied-label"
        invalid_source = evaluator.evaluate_run(corpus, scenario["id"], run, artifact_root=tmp_path)
        assert not invalid_source["passed"]
        assert any("not the bound execution surface" in failure for failure in invalid_source["failures"])

    def test_fixture_measurement_contract_rejects_available_values(self):
        evaluator = load_delivery_quality_evaluator()
        corpus = evaluator.load_corpus(HARNESS_ROOT / "scenarios.json")
        scenario = next(
            scenario
            for scenario in corpus["scenarios"]
            if scenario["category"] == "fresh_verification"
        )
        fixture = json.loads(json.dumps(scenario["valid_fixture"]))
        fixture["measurements"]["latency"] = {
            "availability": "available",
            "value": 1,
            "source": "fixture",
        }

        result = evaluator.evaluate_run(corpus, scenario["id"], fixture)

        assert not result["passed"]
        assert any("fixture measurement latency must remain unavailable" in failure for failure in result["failures"])

    def test_review_scenario_validates_structured_evidence_not_observation_labels(self):
        evaluator = load_delivery_quality_evaluator()
        corpus = evaluator.load_corpus(HARNESS_ROOT / "scenarios.json")
        scenario = next(
            item for item in corpus["scenarios"] if item["id"] == "evidence-aware-review-disposition"
        )
        valid = json.loads(json.dumps(scenario["valid_fixture"]))
        assert evaluator.evaluate_run(corpus, scenario["id"], valid)["passed"]

        duplicate = json.loads(json.dumps(valid))
        duplicate["review_record"]["findings"].append(
            json.loads(json.dumps(duplicate["review_record"]["findings"][0]))
        )
        missing_re_review = json.loads(json.dumps(valid))
        missing_re_review["review_record"]["re_review_range"] = None
        stale = json.loads(json.dumps(valid))
        stale["current_review_range"]["head"] = "e" * 40
        failed_final = json.loads(json.dumps(valid))
        failed_final["review_record"]["final_validation"]["outcome"] = "previous run passed"
        malformed_type = json.loads(json.dumps(valid))
        malformed_type["review_record"]["findings"][0]["severity"] = ["important"]

        for malformed in (duplicate, missing_re_review, stale, failed_final, malformed_type):
            result = evaluator.evaluate_run(corpus, scenario["id"], malformed)
            assert not result["passed"]
            assert any("structured review evidence is invalid" in failure for failure in result["failures"])

    def test_authority_and_external_boundary_scenarios_cover_the_full_declared_routes(self):
        evaluator = load_delivery_quality_evaluator()
        corpus = evaluator.load_corpus(HARNESS_ROOT / "scenarios.json")
        scenarios = {scenario["id"]: scenario for scenario in corpus["scenarios"]}

        authority_subjects = {
            observation["subject"]
            for observation in scenarios["constitutional-authority-conflict"]["required_observations"]
        }
        assert {"constitution", "accepted_adr_head", "active_individual_decision"} <= authority_subjects

        approved_subjects = {
            observation["subject"]
            for observation in scenarios["external-approved-routes-boundary"]["required_observations"]
        }
        fallback_subjects = {
            observation["subject"]
            for observation in scenarios["external-unavailable-local-fallback"]["required_observations"]
        }
        assert {
            "external_read_only_dispatch",
            "approved_external_sdd",
            "return_before_memory_seed_integration",
        } <= approved_subjects
        assert {"external_unavailable_or_wrong_version", "named_local_fallback"} <= fallback_subjects

        review_subjects = {
            observation["subject"]
            for observation in scenarios["evidence-aware-review-disposition"]["required_observations"]
        }
        assert {
            "immutable_review_range",
            "finding_disposition_evidence",
            "scoped_fix_re_review",
            "fresh_final_verification",
        } <= review_subjects

    def test_topic_applicability_plan_strategy_and_reuse_have_structured_negative_controls(self):
        evaluator = load_delivery_quality_evaluator()
        corpus = evaluator.load_corpus(HARNESS_ROOT / "scenarios.json")
        scenarios = {scenario["id"]: scenario for scenario in corpus["scenarios"]}

        topic_subjects = {
            observation["subject"]
            for observation in scenarios["governed-topic-applicability"]["required_observations"]
        }
        assert {
            "applicable_topic_ancestors",
            "narrower_topic_branch",
            "proposed_action_to_applicable_authority",
            "compatible_narrower_constraint",
        } <= topic_subjects

        plan_subjects = {
            observation["subject"]
            for observation in scenarios["optional-implementation-plan-test-strategy"][
                "required_observations"
            ]
        }
        assert {
            "approved_discovery_evidence",
            "ordered_testable_work",
            "viable_tests",
            "proportionate_alternative_check",
            "reviewable_test_exception",
        } <= plan_subjects

        reuse_subjects = {
            observation["subject"]
            for observation in scenarios["reflection-board-reuse-discovery"]["required_observations"]
        }
        assert {
            "closed_reflection_board_launch_ledger",
            "reflection_board_controls_to_external_sdd",
            "reuse_tradeoff",
            "reflection_board_artifacts",
        } <= reuse_subjects

        negative = evaluator.evaluate_declared_fixtures(corpus, kind="negative")
        failures_by_fixture = {result["fixture_id"]: result["failures"] for result in negative["results"]}
        for fixture_id in (
            "invented-untagged-coverage",
            "blanket-tdd-substitutes-for-strategy",
            "exception-without-compensating-check",
            "closed-ledger-not-found",
            "board-artifacts-changed",
        ):
            assert fixture_id in failures_by_fixture
            assert failures_by_fixture[fixture_id]

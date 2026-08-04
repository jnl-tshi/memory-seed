"""Render the experiment's decision packet without changing production."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Mapping

from contracts import AGENTS, ARMS, REPETITIONS, TASK_COUNT
from judge import selected_repetition


def _rate(value: Any) -> str:
    return "n/a" if value is None else f"{100 * float(value):.1f}%"


def _interval(metric: Mapping[str, Any]) -> str:
    interval = metric.get("wilson_95")
    if not interval:
        return "n/a"
    return f"{100 * interval[0]:.1f}%–{100 * interval[1]:.1f}%"


def _number(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.1f}"


def _offline_readiness(offline: Mapping[str, Any] | None) -> tuple[list[str], Mapping[str, Any]]:
    failures: list[str] = []
    if not offline or offline.get("complete") is not True:
        return ["offline reduction is missing or incomplete"], {}
    strategies = offline.get("strategies")
    selected_fingerprint = offline.get("selected_strategy_fingerprint")
    if not isinstance(strategies, list) or not isinstance(selected_fingerprint, str) or not selected_fingerprint:
        return ["offline reduction has no frozen selected strategy"], {}
    matches = [
        item for item in strategies
        if isinstance(item, Mapping) and item.get("strategy_fingerprint") == selected_fingerprint
    ]
    if len(matches) != 1:
        return ["selected strategy fingerprint must resolve to exactly one reduction row"], {}
    selected = matches[0]
    family = (selected.get("strategy") or {}).get("family")
    evidence_fields = ("irrelevant_token_proxy", "total_token_proxy", "p95_latency_ms")
    if (offline.get("task_count") != TASK_COUNT
            or offline.get("strategy_count") != len(strategies)
            or not isinstance(offline.get("fingerprint"), str)
            or not offline.get("fingerprint")
            or selected.get("eligible") is not True
            or selected.get("selection_eligible") is not True
            or selected.get("failures") != []
            or not isinstance(selected.get("strategy"), Mapping)
            or family in (None, "", "oracle")
            or selected_fingerprint not in (offline.get("pareto_frontier") or ())
            or any(not isinstance(selected.get(key), (int, float)) or isinstance(selected.get(key), bool)
                   or not math.isfinite(float(selected[key])) or float(selected[key]) < 0
                   for key in evidence_fields)):
        failures.append("selected offline strategy lacks complete eligible non-oracle gate evidence")
    return failures, selected


def _judgement_readiness(
    score: Mapping[str, Any],
    judgements: list[Mapping[str, Any]] | None,
) -> list[str]:
    failures: list[str] = []
    expected_task_ids = {f"CTX-{number:02d}" for number in range(1, TASK_COUNT + 1)}
    expected_score_cells = {
        (task_id, arm, agent, repetition)
        for task_id in expected_task_ids
        for arm in ARMS
        for agent in AGENTS
        for repetition in range(1, REPETITIONS + 1)
    }
    score_rows = score.get("rows")
    if not isinstance(score_rows, list):
        return ["mechanical score rows are missing; blind judgements cannot be bound"]
    actual_score_cells: list[tuple[str, str, str, int]] = []
    score_by_run_id: dict[str, Mapping[str, Any]] = {}
    for row in score_rows:
        if not isinstance(row, Mapping):
            failures.append("mechanical score rows are malformed")
            continue
        try:
            cell = (str(row.get("task_id")), str(row.get("arm")), str(row.get("agent")), int(row.get("repetition", 0)))
        except (TypeError, ValueError):
            failures.append("mechanical score rows are malformed")
            continue
        run_id = str(row.get("run_id") or "")
        actual_score_cells.append(cell)
        if not run_id or run_id in score_by_run_id:
            failures.append("mechanical score run IDs must be unique and non-empty")
        else:
            score_by_run_id[run_id] = row
    if (len(actual_score_cells) != len(expected_score_cells)
            or set(actual_score_cells) != expected_score_cells
            or len(set(actual_score_cells)) != len(actual_score_cells)):
        failures.append("mechanical score rows do not contain the exact frozen 12x4x2x3 matrix")

    judge_rows = judgements or []
    expected_judge_cells = {
        (task_id, arm, agent)
        for task_id in expected_task_ids
        for arm in ARMS
        for agent in AGENTS
    }
    actual_judge_cells: list[tuple[str, str, str]] = []
    judge_run_ids: list[str] = []
    for row in judge_rows:
        if not isinstance(row, Mapping):
            failures.append("blind judgement rows are malformed")
            continue
        task_id = str(row.get("task_id"))
        arm = str(row.get("arm"))
        subject = str(row.get("subject"))
        judge = str(row.get("judge"))
        run_id = str(row.get("run_id") or "")
        try:
            repetition = int(row.get("repetition", 0))
        except (TypeError, ValueError):
            repetition = 0
        try:
            frozen_repetition = selected_repetition(task_id, arm, subject)
        except (OSError, ValueError, json.JSONDecodeError):
            frozen_repetition = 0
        actual_judge_cells.append((task_id, arm, subject))
        judge_run_ids.append(run_id)
        expected_judge = "codex" if subject == "claude" else "claude" if subject == "codex" else ""
        scored = score_by_run_id.get(run_id)
        if (row.get("schema") != "context-judge.v1"
                or judge != expected_judge
                or repetition != frozen_repetition
                or scored is None
                or (str(scored.get("task_id")), str(scored.get("arm")), str(scored.get("agent")), int(scored.get("repetition", 0)))
                    != (task_id, arm, subject, repetition)):
            failures.append("blind judgement is invalid or not bound to its preselected scored run")
    if (len(actual_judge_cells) != len(expected_judge_cells)
            or set(actual_judge_cells) != expected_judge_cells
            or len(set(actual_judge_cells)) != len(actual_judge_cells)
            or any(not run_id for run_id in judge_run_ids)
            or len(set(judge_run_ids)) != len(judge_run_ids)):
        failures.append("blind review is not the exact unique frozen 12x4x2 judgement matrix")
    return sorted(set(failures))


def render_report(
    score: Mapping[str, Any],
    offline: Mapping[str, Any] | None = None,
    judgements: list[Mapping[str, Any]] | None = None,
    recommendations: Mapping[str, Any] | None = None,
) -> str:
    gate = score.get("production_recommendation_gate", {})
    offline_failures, candidate = _offline_readiness(offline)
    readiness_failures = [*offline_failures, *_judgement_readiness(score, judgements)]
    required_recommendations = {
        "required_related_adrs", "adr_review_profile", "shared_resolver",
        "workflow_prompts", "evolves",
    }
    if (not recommendations or not required_recommendations <= set(recommendations)
            or not isinstance(recommendations.get("evolves"), list)
            or any(recommendations.get(key) in (None, "", "PENDING OWNER REVIEW", "PENDING FAILURE ANALYSIS")
                   for key in required_recommendations - {"evolves"})):
        readiness_failures.append("reviewed production recommendations are incomplete")
    report_passed = bool(gate.get("passed")) and not readiness_failures
    lines = [
        "# ADR context-derivation experiment report",
        "",
        "## Verdict",
        "",
        "Production recommendation gate: **" + ("PASS" if report_passed else "FAIL / INCOMPLETE") + "**.",
        "",
    ]
    all_failures = [*gate.get("failures", []), *readiness_failures]
    if all_failures:
        lines.extend(["Failures:", "", *[f"- {item}" for item in all_failures], ""])
    if offline:
        selected_fingerprint = offline.get("selected_strategy_fingerprint")
        lines.extend(
            [
                "## Frozen offline candidate",
                "",
                f"- Strategy family: `{(candidate.get('strategy') or {}).get('family', 'not frozen')}`",
                f"- Fingerprint: `{selected_fingerprint or 'not frozen'}`",
                f"- Eligible strategies: {sum(bool(item.get('selection_eligible')) for item in offline.get('strategies', []) if isinstance(item, Mapping))}",
                f"- Pareto strategies: {len(offline.get('pareto_frontier', []))}",
                "",
            ]
        )
    lines.extend(["## Live results by agent", ""])
    aggregates = score.get("aggregates", {})
    for agent in AGENTS:
        lines.extend([f"### {agent.title()}", "", "| Arm | Runs | Complete (95% Wilson) | Head/status | Citations | Median context | p95 latency ms |", "|---|---:|---:|---:|---:|---:|---:|"])
        for arm in ARMS:
            item = aggregates.get(agent, {}).get(arm, {})
            metrics = item.get("metrics", {})
            lines.append(
                "| " + arm + " | " + str(item.get("runs", 0)) + " | "
                + _rate(metrics.get("complete_correct", {}).get("rate")) + " (" + _interval(metrics.get("complete_correct", {})) + ") | "
                + _rate(metrics.get("head_correct", {}).get("rate")) + " / " + _rate(metrics.get("status_correct", {}).get("rate")) + " | "
                + _rate(metrics.get("citation_resolves", {}).get("rate")) + " | "
                + _number(item.get("context_tokens", {}).get("median")) + " | "
                + _number(item.get("duration_ms", {}).get("p95")) + " |"
            )
        lines.append("")
        lines.extend(["#### Failures, usage, and tool paths", ""])
        for arm in ARMS:
            item = aggregates.get(agent, {}).get(arm, {})
            failures = item.get("task_failures") or {}
            exclusions = item.get("exclusions") or {}
            sequences = item.get("tool_sequences") or {}
            common_sequences = sorted(sequences.items(), key=lambda pair: (-pair[1], pair[0]))[:5]
            lines.extend(
                [
                    f"- `{arm}`: task failures {json.dumps(failures, sort_keys=True)}; exclusions {json.dumps(exclusions, sort_keys=True)}; "
                    f"median input/output tokens {_number(item.get('input_tokens', {}).get('median'))}/{_number(item.get('output_tokens', {}).get('median'))}; "
                    f"median context utilization {_rate(item.get('context_utilization', {}).get('median'))}; "
                    f"cost USD {_number(item.get('cost_usd'))}; "
                    f"tool paths {json.dumps(dict(common_sequences), sort_keys=True)}.",
                ]
            )
        lines.append("")
    if judgements is not None:
        supported = sum(bool(item.get("explanation_supported")) for item in judgements)
        complete = sum(bool(item.get("explanation_complete")) for item in judgements)
        lines.extend([
            "## Blind cross-family explanation review",
            "",
            f"- Reviews: {len(judgements)} (expected 96).",
            f"- Explanation supported: {supported}/{len(judgements)}.",
            f"- Explanation complete: {complete}/{len(judgements)}.",
            "- These secondary judgements do not override mechanical evidence without a recorded manual adjudication.",
            "",
        ])
    recommendation_rows = recommendations or {}
    lines.extend(
        [
            "## Recommendation boundary",
            "",
            "This report does not authorize a production change. If the gate passes, the owner should review:",
            "",
            f"- Retrieval Spec v2 `required.related_adrs`: {recommendation_rows.get('required_related_adrs', 'PENDING OWNER REVIEW')}.",
            f"- Versioned `adr-review` profile: {recommendation_rows.get('adr_review_profile', 'PENDING OWNER REVIEW')}.",
            f"- Shared resolver beneath both Evidence Pack formats: {recommendation_rows.get('shared_resolver', 'PENDING OWNER REVIEW')}.",
            f"- MCP descriptions/workflow prompts: {recommendation_rows.get('workflow_prompts', 'PENDING FAILURE ANALYSIS')}.",
            f"- ADRs or decisions the production proposal would evolve: {json.dumps(recommendation_rows.get('evolves', []), sort_keys=True)}.",
            "",
            "`memory_search` ordering remains unchanged and any future ranking signal still requires its own fixture and real-corpus A/B.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--score", required=True)
    parser.add_argument("--offline", required=True)
    parser.add_argument("--judgements", required=True)
    parser.add_argument("--recommendations", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    score = json.loads(Path(args.score).read_text(encoding="utf-8"))
    offline = json.loads(Path(args.offline).read_text(encoding="utf-8"))
    judgements = json.loads(Path(args.judgements).read_text(encoding="utf-8"))
    recommendations = json.loads(Path(args.recommendations).read_text(encoding="utf-8"))
    Path(args.output).write_text(render_report(score, offline, judgements, recommendations), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

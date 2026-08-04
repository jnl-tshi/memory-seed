"""Render the experiment's decision packet without changing production."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from contracts import AGENTS, ARMS


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


def render_report(
    score: Mapping[str, Any],
    offline: Mapping[str, Any] | None = None,
    judgements: list[Mapping[str, Any]] | None = None,
    recommendations: Mapping[str, Any] | None = None,
) -> str:
    gate = score.get("production_recommendation_gate", {})
    readiness_failures: list[str] = []
    if not offline or not offline.get("complete") or not offline.get("selected_strategy_fingerprint"):
        readiness_failures.append("offline reduction/candidate is missing or incomplete")
    judge_rows = judgements or []
    judge_ids = {str(item.get("run_id")) for item in judge_rows}
    if (len(judge_rows) != 96 or len(judge_ids) != 96
            or any(item.get("schema") != "context-judge.v1" for item in judge_rows)
            or any(item.get("judge") == item.get("subject") for item in judge_rows)):
        readiness_failures.append("blind cross-family review is not exactly 96 valid unique judgements")
    required_recommendations = {
        "required_related_adrs", "adr_review_profile", "shared_resolver",
        "workflow_prompts", "evolves",
    }
    if (not recommendations or not required_recommendations <= set(recommendations)
            or not isinstance(recommendations.get("evolves"), list)
            or any(recommendations.get(key) in (None, "", "PENDING OWNER REVIEW", "PENDING FAILURE ANALYSIS") for key in required_recommendations - {"evolves"})):
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
        candidate = next(
            (item for item in offline.get("strategies", []) if item.get("strategy_fingerprint") == selected_fingerprint),
            {},
        )
        lines.extend(
            [
                "## Frozen offline candidate",
                "",
                f"- Strategy family: `{(candidate.get('strategy') or {}).get('family', 'not frozen')}`",
                f"- Fingerprint: `{selected_fingerprint or 'not frozen'}`",
                f"- Eligible strategies: {sum(bool(item.get('selection_eligible')) for item in offline.get('strategies', []))}",
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
    offline = json.loads(Path(args.offline).read_text(encoding="utf-8")) if args.offline else None
    judgements = json.loads(Path(args.judgements).read_text(encoding="utf-8")) if args.judgements else None
    recommendations = json.loads(Path(args.recommendations).read_text(encoding="utf-8")) if args.recommendations else None
    Path(args.output).write_text(render_report(score, offline, judgements, recommendations), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

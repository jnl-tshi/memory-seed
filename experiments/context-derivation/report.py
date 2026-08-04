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


def render_report(score: Mapping[str, Any], offline: Mapping[str, Any] | None = None) -> str:
    gate = score.get("production_recommendation_gate", {})
    lines = [
        "# ADR context-derivation experiment report",
        "",
        "## Verdict",
        "",
        "Production recommendation gate: **" + ("PASS" if gate.get("passed") else "FAIL / INCOMPLETE") + "**.",
        "",
    ]
    if gate.get("failures"):
        lines.extend(["Failures:", "", *[f"- {item}" for item in gate["failures"]], ""])
    if offline:
        candidate = offline.get("selected_candidate") or {}
        lines.extend(
            [
                "## Frozen offline candidate",
                "",
                f"- Strategy: `{candidate.get('strategy_id', 'not frozen')}`",
                f"- Fingerprint: `{candidate.get('fingerprint', 'not frozen')}`",
                f"- Eligible strategies: {offline.get('eligible_count', 'n/a')}",
                f"- Pareto strategies: {offline.get('pareto_count', 'n/a')}",
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
                    f"tool paths {json.dumps(dict(common_sequences), sort_keys=True)}.",
                ]
            )
        lines.append("")
    lines.extend(
        [
            "## Recommendation boundary",
            "",
            "This report does not authorize a production change. If the gate passes, the owner should review:",
            "",
            "- Retrieval Spec v2 `required.related_adrs`.",
            "- A versioned `adr-review` profile.",
            "- One shared resolver beneath both Evidence Pack formats.",
            "- MCP descriptions and stopping guidance revealed by workflow failures.",
            "- Proactive ADR review for any decision the proposal evolves.",
            "",
            "`memory_search` ordering remains unchanged and any future ranking signal still requires its own fixture and real-corpus A/B.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--score", required=True)
    parser.add_argument("--offline")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    score = json.loads(Path(args.score).read_text(encoding="utf-8"))
    offline = json.loads(Path(args.offline).read_text(encoding="utf-8")) if args.offline else None
    Path(args.output).write_text(render_report(score, offline), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Render the experiment's decision packet without changing production."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from contracts import AGENTS, ARMS


def _rate(value: Any) -> str:
    return "n/a" if value is None else f"{100 * float(value):.1f}%"


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
        lines.extend([f"### {agent.title()}", "", "| Arm | Runs | Complete | Head | Citations | Median context |", "|---|---:|---:|---:|---:|---:|"])
        for arm in ARMS:
            item = aggregates.get(agent, {}).get(arm, {})
            metrics = item.get("metrics", {})
            lines.append(
                "| " + arm + " | " + str(item.get("runs", 0)) + " | "
                + _rate(metrics.get("complete_correct", {}).get("rate")) + " | "
                + _rate(metrics.get("head_correct", {}).get("rate")) + " | "
                + _rate(metrics.get("citation_resolves", {}).get("rate")) + " | "
                + str(item.get("context_tokens", {}).get("median", "n/a")) + " |"
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

"""Mechanical scoring for the ADR context-derivation experiment."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from contracts import AGENTS, ARMS, EXPECTED_SUBJECT_RUNS, canonical_json


def _edge_key(value: Mapping[str, Any]) -> tuple[str, str, str]:
    return (str(value.get("source", "")), str(value.get("target", "")), str(value.get("type", "")))


def _as_set(value: Any) -> set[str]:
    return {str(item) for item in value or ()}


def _percentile(values: Iterable[float], percentile: float) -> float | None:
    ordered = sorted(float(item) for item in values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def wilson(successes: int, total: int, z: float = 1.959963984540054) -> list[float] | None:
    if total <= 0:
        return None
    proportion = successes / total
    denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    margin = z * math.sqrt((proportion * (1 - proportion) + z * z / (4 * total)) / total) / denominator
    return [max(0.0, centre - margin), min(1.0, centre + margin)]


def score_run(run: Mapping[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    answer = run.get("answer") if isinstance(run.get("answer"), Mapping) else {}
    required_adrs = _as_set(gold.get("required_adr_ids"))
    required_heads = _as_set(gold.get("authoritative_refs"))
    expected_edges = {_edge_key(item) for item in gold.get("required_lineage_edges", ())}
    actual_adrs = _as_set(answer.get("adr_ids"))
    actual_heads = _as_set(answer.get("authoritative_refs"))
    actual_edges = {_edge_key(item) for item in answer.get("lineage_edges", ()) if isinstance(item, Mapping)}
    citations = _as_set(answer.get("citations"))
    included = _as_set(run.get("included_refs"))
    allowed_citations = _as_set(gold.get("allowed_citations"))
    distractors = _as_set(gold.get("distractor_refs"))
    expected_absence = bool(gold.get("insufficient_evidence"))
    actual_absence = bool(answer.get("insufficient_evidence"))

    adr_recall = required_adrs <= actual_adrs
    head_correct = actual_heads == required_heads
    lineage_recall = expected_edges <= actual_edges
    relation_types_correct = all(edge[2] in {"evolves", "replaces"} for edge in actual_edges)
    citation_resolves = citations <= included
    citation_allowed = not allowed_citations or citations <= allowed_citations
    absence_correct = actual_absence == expected_absence
    distractor_clean = not (distractors & (actual_heads | citations | {part for edge in actual_edges for part in edge[:2]}))
    protocol_ok = not bool(run.get("protocol_failure"))
    harness_ok = not bool(run.get("harness_failure")) and not run.get("exclusion_reason")
    complete = all(
        (
            adr_recall,
            head_correct,
            lineage_recall,
            relation_types_correct,
            citation_resolves,
            citation_allowed,
            absence_correct,
            distractor_clean,
            protocol_ok,
            harness_ok,
        )
    )
    return {
        "run_id": run.get("run_id"),
        "task_id": run.get("task_id"),
        "arm": run.get("arm"),
        "agent": run.get("agent"),
        "repetition": run.get("repetition"),
        "adr_recall": adr_recall,
        "head_correct": head_correct,
        "lineage_recall": lineage_recall,
        "relation_types_correct": relation_types_correct,
        "citation_resolves": citation_resolves,
        "citation_allowed": citation_allowed,
        "absence_correct": absence_correct,
        "distractor_clean": distractor_clean,
        "protocol_ok": protocol_ok,
        "harness_ok": harness_ok,
        "complete_correct": complete,
        "context_token_proxy": run.get("context_token_proxy"),
        "duration_ms": run.get("duration_ms"),
        "input_tokens": run.get("input_tokens"),
        "output_tokens": run.get("output_tokens"),
        "cost_usd": run.get("cost_usd"),
    }


def _aggregate(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    complete = sum(bool(row["complete_correct"]) for row in rows)
    metrics = {}
    for name in (
        "adr_recall",
        "head_correct",
        "lineage_recall",
        "relation_types_correct",
        "citation_resolves",
        "absence_correct",
        "protocol_ok",
        "complete_correct",
    ):
        successes = sum(bool(row[name]) for row in rows)
        metrics[name] = {
            "successes": successes,
            "total": total,
            "rate": successes / total if total else None,
            "wilson_95": wilson(successes, total),
        }
    tokens = [float(row["context_token_proxy"]) for row in rows if row.get("context_token_proxy") is not None]
    durations = [float(row["duration_ms"]) for row in rows if row.get("duration_ms") is not None]
    costs = [float(row["cost_usd"]) for row in rows if row.get("cost_usd") is not None]
    return {
        "runs": total,
        "complete": complete,
        "metrics": metrics,
        "context_tokens": {
            "median": statistics.median(tokens) if tokens else None,
            "p95": _percentile(tokens, 0.95),
        },
        "duration_ms": {
            "median": statistics.median(durations) if durations else None,
            "p95": _percentile(durations, 0.95),
        },
        "cost_usd": sum(costs) if costs else None,
    }


def score_experiment(summary: Mapping[str, Any], gold_payload: Mapping[str, Any], *, require_complete: bool = True) -> dict[str, Any]:
    gold = {str(item["task_id"]): item for item in gold_payload.get("tasks", ())}
    runs = list(summary.get("runs", ()))
    cells = [(str(run.get("task_id")), str(run.get("arm")), str(run.get("agent")), int(run.get("repetition", 0))) for run in runs]
    duplicates = sorted({cell for cell in cells if cells.count(cell) > 1})
    issues: list[str] = []
    if duplicates:
        issues.append(f"duplicate run cells: {duplicates}")
    if require_complete and len(runs) != EXPECTED_SUBJECT_RUNS:
        issues.append(f"expected {EXPECTED_SUBJECT_RUNS} subject runs, found {len(runs)}")
    for run in runs:
        if str(run.get("task_id")) not in gold:
            issues.append(f"run {run.get('run_id')} has no gold task")
        if run.get("arm") not in ARMS or run.get("agent") not in AGENTS:
            issues.append(f"run {run.get('run_id')} has an unknown arm/agent")
    if issues:
        raise ValueError("; ".join(issues))

    scored = [score_run(run, gold[str(run["task_id"])]) for run in runs]
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for row in scored:
        grouped[(str(row["agent"]), str(row["arm"]))].append(row)
    aggregates = {
        agent: {arm: _aggregate(grouped.get((agent, arm), [])) for arm in ARMS}
        for agent in AGENTS
    }

    gates: dict[str, Any] = {"passed": True, "failures": []}
    for agent in AGENTS:
        candidate = aggregates[agent]["adr-candidate-packet"]
        workflow = aggregates[agent]["adr-mcp-workflow"]
        baseline = aggregates[agent]["retrieval-v1-packet"]
        if candidate["metrics"]["head_correct"]["successes"] != candidate["runs"]:
            gates["failures"].append(f"{agent}: candidate has accepted-head/status errors")
        candidate_rate = candidate["metrics"]["complete_correct"]["rate"]
        workflow_rate = workflow["metrics"]["complete_correct"]["rate"]
        baseline_rate = baseline["metrics"]["complete_correct"]["rate"]
        if candidate_rate is None or candidate_rate < 0.90:
            gates["failures"].append(f"{agent}: candidate complete correctness below 0.90")
        if baseline_rate is not None and candidate_rate is not None and candidate_rate < baseline_rate:
            gates["failures"].append(f"{agent}: candidate accuracy below Retrieval Spec v1")
        if workflow_rate is None or candidate_rate is None or workflow_rate < candidate_rate - 0.05:
            gates["failures"].append(f"{agent}: ADR MCP workflow more than five points below fixed candidate")
        candidate_tokens = candidate["context_tokens"]["median"]
        baseline_tokens = baseline["context_tokens"]["median"]
        if baseline_tokens and (candidate_tokens is None or candidate_tokens > baseline_tokens * 0.5):
            gates["failures"].append(f"{agent}: candidate median context is not at least 50% smaller")
        for metric in ("citation_resolves", "absence_correct", "relation_types_correct", "protocol_ok"):
            if candidate["metrics"][metric]["successes"] != candidate["runs"]:
                gates["failures"].append(f"{agent}: candidate failed {metric}")
    gates["passed"] = not gates["failures"]
    return {
        "schema": "context-score.v1",
        "subject_runs": len(scored),
        "agents_pooled": False,
        "rows": scored,
        "aggregates": aggregates,
        "production_recommendation_gate": gates,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", required=True)
    parser.add_argument("--gold", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-incomplete", action="store_true")
    args = parser.parse_args()
    summary = json.loads(Path(args.summary).read_text(encoding="utf-8"))
    gold = json.loads(Path(args.gold).read_text(encoding="utf-8"))
    result = score_experiment(summary, gold, require_complete=not args.allow_incomplete)
    Path(args.output).write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(canonical_json({"runs": result["subject_runs"], "gate": result["production_recommendation_gate"]}))
    return 0 if result["production_recommendation_gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

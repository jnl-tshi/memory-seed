"""Test origin, timing, and reviewer-detection hypotheses against the 50-row gold set."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


BASE = Path(__file__).resolve().parent


def _load_alignment_module():
    existing = sys.modules.get("align_decisions")
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location("align_decisions", BASE / "align_decisions.py")
    if not spec or not spec.loader:
        raise RuntimeError("Could not load align_decisions.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


alignment = _load_alignment_module()

IMPLEMENTATION_TERMS = (
    "implementation", "execution", "validation", "closeout", "apply_patch", "exec/",
    "tool", "custom_tool", "test",
)
REVIEW_TERMS = ("review", "reviewer", "validator", "finding", "spec compliance", "code quality")
PLAN_TERMS = ("plan", "proposal", "architecture")


def read_explicit_origin(path: Path, entry_id: str, ordinal: str) -> str | None:
    text = path.read_text(encoding="utf-8")
    marker = f"entry_id: {entry_id}"
    start = text.find(marker)
    if start < 0:
        return None
    end = text.find("\n## ", start + len(marker))
    segment = text[start:] if end < 0 else text[start:end]
    match = re.search(rf"(?m)^  {re.escape(ordinal)}: (user|agent)\s*$", segment)
    return match.group(1) if match else None


def _fold(values: Iterable[str]) -> str:
    return " ".join(" ".join(value.casefold().split()) for value in values)


def phase_tags(*, source_role: str, evidence_shape: str, actors: set[str]) -> set[str]:
    combined = _fold([source_role, evidence_shape, *sorted(actors)])
    tags: set[str] = set()
    if "user" in actors or "discussion" in combined or "authorization" in combined:
        tags.add("discussion")
    if any(term in combined for term in IMPLEMENTATION_TERMS):
        tags.add("implementation")
    if any(term in combined for term in REVIEW_TERMS):
        tags.add("review")
    if any(term in combined for term in PLAN_TERMS):
        tags.add("plan")
    return tags or {"unclassified"}


def reviewer_signals(
    *, agent_nickname: str | None, agent_path: str | None,
    is_child: bool, first_user_text: str, assistant_text: str,
) -> dict[str, bool]:
    name_text = _fold([agent_nickname or "", agent_path or ""])
    prompt_text = _fold([first_user_text])
    output_text = _fold([assistant_text])
    name_signal = any(term in name_text for term in REVIEW_TERMS)
    # A root session's opening prompt describes the whole task and must not label
    # every later turn. A child rollout's first user item is its dispatch prompt.
    prompt_signal = is_child and any(term in prompt_text for term in REVIEW_TERMS)
    output_signal = any(term in output_text for term in REVIEW_TERMS) and any(
        marker in output_text
        for marker in ("finding", "verdict", "approved", "spec", "critical", "important")
    )
    return {
        "name_signal": name_signal,
        "prompt_signal": prompt_signal,
        "output_signal": output_signal,
        "any_signal": name_signal or prompt_signal or output_signal,
    }


def _values(ref: dict[str, Any], singular: str, plural: str) -> list[Any]:
    if plural in ref and isinstance(ref[plural], list):
        return ref[plural]
    return [ref[singular]] if singular in ref else []


def evidence_timestamps(
    row: dict[str, Any],
    actual_by_coordinate: dict[tuple[str, int], datetime] | None = None,
) -> list[datetime]:
    values: list[datetime | None] = []
    for ref in row["adjudication"]["evidence_refs"]:
        rollout_id = str(ref["rollout_id"])
        ordinals = [int(value) for value in _values(ref, "ordinal", "ordinals")]
        declared = [
            alignment.parse_iso_timestamp(str(value))
            for value in _values(ref, "timestamp", "timestamps")
        ]
        for index, value in enumerate(declared):
            coordinate = (rollout_id, ordinals[index]) if index < len(ordinals) else None
            values.append(
                actual_by_coordinate.get(coordinate, value)
                if actual_by_coordinate is not None and coordinate is not None
                else value
            )
    return [value for value in values if value is not None]


def source_timestamp_map(
    metas: Iterable[Any], wanted: set[tuple[str, int]],
) -> dict[tuple[str, int], datetime]:
    found: dict[tuple[str, int], datetime] = {}
    for meta in metas:
        relevant = {ordinal for rollout_id, ordinal in wanted if rollout_id == meta.rollout_id}
        if not relevant:
            continue
        with Path(meta.source_path).open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    raw = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ordinal = raw.get("ordinal")
                if ordinal not in relevant or not raw.get("timestamp"):
                    continue
                stamp = alignment.parse_iso_timestamp(str(raw["timestamp"]))
                if stamp is not None:
                    found[(meta.rollout_id, int(ordinal))] = stamp
    return found


def evidence_actors(row: dict[str, Any]) -> set[str]:
    return {
        str(value).casefold()
        for ref in row["adjudication"]["evidence_refs"]
        for value in _values(ref, "actor", "actors")
    }


def read_gold(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 50:
        raise RuntimeError(f"Expected 50 gold rows, found {len(rows)}")
    return rows


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def _ratio(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def evaluate(repo_root: Path, codex_home: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    rollout_ids = {
        str(ref["rollout_id"])
        for row in rows
        for ref in row["adjudication"]["evidence_refs"]
    }
    metas = [
        meta
        for path in alignment.iter_rollout_paths(codex_home)
        if (meta := alignment.read_session_meta(path)) is not None
        and meta.rollout_id in rollout_ids
    ]
    by_rollout = {meta.rollout_id: meta for meta in metas}
    wanted_coordinates = {
        (str(ref["rollout_id"]), int(value))
        for row in rows
        for ref in row["adjudication"]["evidence_refs"]
        for value in _values(ref, "ordinal", "ordinals")
    }
    actual_timestamps = source_timestamp_map(metas, wanted_coordinates)
    timestamp_mismatch_seconds: list[float] = []
    for row in rows:
        for ref in row["adjudication"]["evidence_refs"]:
            rollout_id = str(ref["rollout_id"])
            ordinals = [int(value) for value in _values(ref, "ordinal", "ordinals")]
            declared = [
                alignment.parse_iso_timestamp(str(value))
                for value in _values(ref, "timestamp", "timestamps")
            ]
            for index, ordinal in enumerate(ordinals):
                if index >= len(declared):
                    continue
                actual = actual_timestamps.get((rollout_id, ordinal))
                if actual is not None and declared[index] is not None and actual != declared[index]:
                    timestamp_mismatch_seconds.append(
                        abs((actual - declared[index]).total_seconds())
                    )
    blocks_by_rollout: dict[str, list[Any]] = {}
    for meta in metas:
        blocks = alignment.parse_rollout(Path(meta.source_path), meta)
        blocks_by_rollout[meta.rollout_id] = blocks

    evaluated_rows: list[dict[str, Any]] = []
    for row in rows:
        decision_id = row["decision"]["id"]
        entry_id, ordinal = decision_id.rsplit(":", 1)
        origin = read_explicit_origin(repo_root / row["decision"]["record_path"], entry_id, ordinal)
        actors = evidence_actors(row)
        tags = phase_tags(
            source_role=str(row["adjudication"].get("source_role") or ""),
            evidence_shape=str(row["adjudication"].get("evidence_shape") or ""),
            actors=actors,
        )
        decision_time = alignment.parse_iso_timestamp(row["decision"]["timestamp"])
        stamps = evidence_timestamps(row, actual_timestamps)
        latest_lag = (
            (decision_time - max(stamps)).total_seconds() / 60
            if decision_time and stamps else None
        )
        earliest_lag = (
            (decision_time - min(stamps)).total_seconds() / 60
            if decision_time and stamps else None
        )
        evidence_rollouts = {
            str(ref["rollout_id"]) for ref in row["adjudication"]["evidence_refs"]
        }
        row_signals: list[dict[str, bool]] = []
        for rollout_id in evidence_rollouts:
            meta = by_rollout.get(rollout_id)
            blocks = blocks_by_rollout.get(rollout_id, [])
            refs = [
                ref for ref in row["adjudication"]["evidence_refs"]
                if str(ref["rollout_id"]) == rollout_id
            ]
            cited_turns = {int(ref["turn"]) for ref in refs if ref.get("turn") is not None}
            cited_ordinals = {
                int(value)
                for ref in refs
                for value in _values(ref, "ordinal", "ordinals")
            }
            relevant_blocks = [
                block for block in blocks
                if block.turn_number in cited_turns
                or any(item.source_ordinal in cited_ordinals for item in block.items)
            ]
            all_items = [item for block in blocks for item in block.items]
            relevant_items = [item for block in relevant_blocks for item in block.items]
            first_user = next((item.text for item in all_items if item.role == "user"), "")
            assistant = "\n".join(
                item.text for item in relevant_items if item.role == "assistant"
            )
            row_signals.append(reviewer_signals(
                agent_nickname=meta.agent_nickname if meta else None,
                agent_path=meta.agent_path if meta else None,
                is_child=bool(meta and meta.parent_thread_id),
                first_user_text=first_user,
                assistant_text=assistant,
            ))
        evaluated_rows.append(
            {
                "decision_id": decision_id,
                "origin": origin,
                "phase_tags": sorted(tags),
                "latest_evidence_to_record_minutes": latest_lag,
                "earliest_evidence_to_record_minutes": earliest_lag,
                "has_user_evidence": "user" in actors,
                "has_agent_evidence": any(
                    actor.startswith("assistant") or actor == "reasoning_summary"
                    for actor in actors
                ),
                "has_tool_evidence": any(
                    any(term in actor for term in ("exec", "tool", "apply_patch"))
                    for actor in actors
                ),
                "has_child_evidence": any(
                    by_rollout.get(rollout_id)
                    and by_rollout[rollout_id].parent_thread_id
                    for rollout_id in evidence_rollouts
                ),
                "gold_review_signal": "review" in tags,
                "reviewer_name_signal": any(value.get("name_signal", False) for value in row_signals),
                "reviewer_prompt_signal": any(value.get("prompt_signal", False) for value in row_signals),
                "reviewer_output_signal": any(value.get("output_signal", False) for value in row_signals),
                "reviewer_any_signal": any(value.get("any_signal", False) for value in row_signals),
            }
        )

    origin_rows = [row for row in evaluated_rows if row["origin"]]
    origin_summary: dict[str, Any] = {}
    for origin in ("user", "agent"):
        subset = [row for row in origin_rows if row["origin"] == origin]
        origin_summary[origin] = {
            "rows": len(subset),
            "discussion_rows": sum("discussion" in row["phase_tags"] for row in subset),
            "implementation_rows": sum("implementation" in row["phase_tags"] for row in subset),
            "review_rows": sum("review" in row["phase_tags"] for row in subset),
            "plan_rows": sum("plan" in row["phase_tags"] for row in subset),
            "user_evidence_rows": sum(row["has_user_evidence"] for row in subset),
            "tool_evidence_rows": sum(row["has_tool_evidence"] for row in subset),
            "median_latest_evidence_to_record_minutes": _median([
                row["latest_evidence_to_record_minutes"]
                for row in subset if row["latest_evidence_to_record_minutes"] is not None
            ]),
        }

    latest_lags = [
        row["latest_evidence_to_record_minutes"]
        for row in evaluated_rows if row["latest_evidence_to_record_minutes"] is not None
    ]
    review_rows = [row for row in evaluated_rows if row["gold_review_signal"]]
    non_review_rows = [row for row in evaluated_rows if not row["gold_review_signal"]]
    reviewer_summary = {
        "gold_review_rows": len(review_rows),
        "gold_review_with_name_signal": sum(row["reviewer_name_signal"] for row in review_rows),
        "gold_review_with_prompt_signal": sum(row["reviewer_prompt_signal"] for row in review_rows),
        "gold_review_with_output_signal": sum(row["reviewer_output_signal"] for row in review_rows),
        "gold_review_with_any_signal": sum(row["reviewer_any_signal"] for row in review_rows),
        "non_review_rows_with_name_signal": sum(row["reviewer_name_signal"] for row in non_review_rows),
        "non_review_rows_with_any_signal": sum(row["reviewer_any_signal"] for row in non_review_rows),
        "child_evidence_rows": sum(row["has_child_evidence"] for row in evaluated_rows),
    }
    reviewer_summary["apparent_precision_against_phase_labels"] = _ratio(
        reviewer_summary["gold_review_with_any_signal"],
        reviewer_summary["gold_review_with_any_signal"]
        + reviewer_summary["non_review_rows_with_any_signal"],
    )
    return {
        "schema_version": "decision-origin-phase-hypotheses/1.1",
        "metadata": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "gold_rows": len(evaluated_rows),
            "explicit_origin_rows": len(origin_rows),
            "explicit_origin_coverage": _ratio(len(origin_rows), len(evaluated_rows)),
            "raw_text_serialized": False,
            "encrypted_reasoning_used": False,
            "source_timestamp_coordinates_resolved": len(actual_timestamps),
            "declared_timestamp_mismatches_corrected_in_analysis": len(timestamp_mismatch_seconds),
            "declared_timestamp_mismatches_over_one_second": sum(
                value > 1 for value in timestamp_mismatch_seconds
            ),
            "maximum_declared_timestamp_mismatch_seconds": (
                max(timestamp_mismatch_seconds) if timestamp_mismatch_seconds else 0
            ),
        },
        "timing": {
            "rows_with_timestamps": len(latest_lags),
            "rows_recorded_at_or_after_latest_cited_evidence_with_minute_tolerance": sum(
                value >= -1 for value in latest_lags
            ),
            "median_latest_evidence_to_record_minutes": _median(latest_lags),
            "minimum_latest_evidence_to_record_minutes": min(latest_lags) if latest_lags else None,
            "maximum_latest_evidence_to_record_minutes": max(latest_lags) if latest_lags else None,
            "interpretation_boundary": (
                "Gold evidence is causally filtered and record headings are minute-granular; lag >= -1 minute is treated as contemporaneous-or-later, but does not prove implementation had completed."
            ),
        },
        "origin_summary": origin_summary,
        "reviewer_summary": reviewer_summary,
        "rows": evaluated_rows,
    }


def render_report(result: dict[str, Any]) -> str:
    meta = result["metadata"]
    timing = result["timing"]
    user = result["origin_summary"]["user"]
    agent = result["origin_summary"]["agent"]
    review = result["reviewer_summary"]
    return f"""# Origin, timing, and reviewer-signal hypothesis check

## Question

Do the current gold alignments support these proposed priors?

1. User-origin decisions are normally front-loaded before execution.
2. Agent-origin decisions normally arise during implementation or review.
3. Decision records are normally written after implementation is complete.
4. Reviewer agents can be detected reliably, with names as an optional hint rather than a dependency.

## Result

The strong versions of the first three claims are **not established by this cohort**.

- Only **{meta['explicit_origin_rows']}/{meta['gold_rows']}** gold rows carry explicit `user|agent` origin metadata. That is too little coverage for a reliable origin-conditioned timing rule.
- The explicit subset contains {user['rows']} user-origin and {agent['rows']} agent-origin rows.
- User-origin rows are not cleanly pre-execution: {user['implementation_rows']}/{user['rows']} include implementation-shaped source evidence and {user['tool_evidence_rows']}/{user['rows']} cite tool-shaped evidence.
- Agent-origin rows do lean toward execution/review evidence: {agent['implementation_rows']}/{agent['rows']} are implementation-shaped and {agent['review_rows']}/{agent['rows']} are review-shaped. The sample is too small to turn that tendency into a rule.
- {timing['rows_recorded_at_or_after_latest_cited_evidence_with_minute_tolerance']}/{timing['rows_with_timestamps']} records are contemporaneous with or later than their latest cited causal evidence, allowing one minute for heading precision. The median lag is {timing['median_latest_evidence_to_record_minutes']:.1f} minutes. This supports record time as an upper search boundary, but it does **not** prove implementation was complete.

The reviewer-detection assumption holds only partially:

- {review['gold_review_rows']} rows are manually marked as review-shaped.
- A reviewer-like nickname/path identifies {review['gold_review_with_name_signal']}/{review['gold_review_rows']}.
- Child dispatch-prompt text identifies {review['gold_review_with_prompt_signal']}/{review['gold_review_rows']} and review-shaped output in the cited turn identifies {review['gold_review_with_output_signal']}/{review['gold_review_rows']}.
- Combining name, prompt, and output signals identifies {review['gold_review_with_any_signal']}/{review['gold_review_rows']}, but also fires on {review['non_review_rows_with_any_signal']} non-review rows. Names alone also fire on {review['non_review_rows_with_name_signal']} non-review rows.
- Against these phase labels, the combined signal's apparent precision is {review['apparent_precision_against_phase_labels']:.1%}; this is a ranking feature, not a reliable reviewer classifier.

## Design implication

Treat origin, reviewer identity, Plan mode, and phase position as **ranking features**, not hard filters:

- `origin=user` may raise the weight of earlier user instructions and approvals.
- `origin=agent` may raise the weight of implementation discoveries, review findings, and assistant reasoning.
- Reviewer naming should be encouraged for observability, but core detection should combine child lineage, dispatch prompt, review output, and workflow metadata.
- Decision-record time is an upper search boundary. A separately detected implementation/review phase boundary is still needed before claiming the record follows completed execution.

## Limits

- Explicit origin coverage is only {meta['explicit_origin_rows']}/{meta['gold_rows']} and is concentrated in recent records.
- Source-coordinate verification corrected {meta['declared_timestamp_mismatches_corrected_in_analysis']} mismatched declared timestamp(s) during analysis ({meta['declared_timestamp_mismatches_over_one_second']} over one second; maximum {meta['maximum_declared_timestamp_mismatch_seconds']:.1f} seconds); the source JSONL coordinate is treated as authoritative.
- Phase labels are conservative heuristics over manually cited source-role and actor metadata; they are not independently annotated phase gold labels.
- Reviewer-signal evaluation is row-level and small. A prospective cohort should record reviewer role, phase boundaries, and decision time directly.
- No raw conversation or reasoning-summary text is serialized in the result artifact.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--gold", type=Path, default=BASE / "GOLD-SET.jsonl")
    parser.add_argument("--output", type=Path, default=BASE)
    args = parser.parse_args()
    result = evaluate(args.repo.resolve(), args.codex_home.resolve(), read_gold(args.gold.resolve()))
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    (output / "ORIGIN-PHASE-RESULTS.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "ORIGIN-PHASE-REPORT.md").write_text(render_report(result), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "rows"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

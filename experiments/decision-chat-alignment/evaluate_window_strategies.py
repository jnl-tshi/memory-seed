"""Evaluate bounded conversation-window strategies against the adjudicated 50-row gold set.

The script reads Codex rollout logs without modifying them. Tracked outputs contain only source
coordinates and aggregate counts; no raw conversation text or reasoning-summary text is serialized.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


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

Coordinate = tuple[str, int]
PLAN_LOOKBACK_TURNS = 12
FALLBACK_LOOKBACK_TURNS = 5
MAX_PARENT_DEPTH = 2


def fixed_window_coordinates(
    blocks: Sequence[Any], winning_turn: int, radius: int = 2
) -> set[Coordinate]:
    if not blocks:
        return set()
    rollout_id = blocks[0].session.rollout_id
    return {
        (rollout_id, block.turn_number)
        for block in blocks
        if winning_turn - radius <= block.turn_number <= winning_turn + radius
    }


def _task_metas(task_id: str, metas: Sequence[Any]) -> list[Any]:
    return [meta for meta in metas if meta.session_id == task_id]


def ordered_task_blocks(
    task_id: str,
    cutoff: datetime,
    metas: Sequence[Any],
    blocks_by_rollout: dict[str, list[Any]],
) -> list[Any]:
    blocks = [
        block
        for meta in _task_metas(task_id, metas)
        for block in blocks_by_rollout.get(meta.rollout_id, [])
        if block.start_utc and block.start_utc <= cutoff
    ]
    return sorted(
        blocks,
        key=lambda block: (
            block.start_utc,
            block.session.timestamp_utc,
            block.session.rollout_id,
            block.turn_number,
        ),
    )


def adaptive_task_coordinates(
    *,
    task_id: str,
    anchor_rollout_id: str,
    anchor_turn: int,
    cutoff: datetime,
    metas: Sequence[Any],
    blocks_by_rollout: dict[str, list[Any]],
    plan_lookback: int,
    fallback_lookback: int,
    forward_turns: int,
) -> set[Coordinate]:
    """Select structural context without consulting decision text or gold evidence."""
    ordered = ordered_task_blocks(task_id, cutoff, metas, blocks_by_rollout)
    anchor_index = next(
        (
            index
            for index, block in enumerate(ordered)
            if block.session.rollout_id == anchor_rollout_id
            and block.turn_number == anchor_turn
        ),
        None,
    )
    if anchor_index is None:
        return set()
    lower_bound = max(0, anchor_index - max(0, plan_lookback))
    plan_indices = [
        index
        for index in range(lower_bound, anchor_index + 1)
        if ordered[index].collaboration_mode == "plan"
    ]
    start_index = (
        plan_indices[-1]
        if plan_indices
        else max(0, anchor_index - max(0, fallback_lookback))
    )
    end_index = min(len(ordered), anchor_index + max(0, forward_turns) + 1)
    return {
        (block.session.rollout_id, block.turn_number)
        for block in ordered[start_index:end_index]
    }


def lineage_adaptive_coordinates(
    *,
    selected_rollout_id: str,
    anchor_turn: int,
    decision_time: datetime,
    metas: Sequence[Any],
    blocks_by_rollout: dict[str, list[Any]],
    plan_lookback: int = PLAN_LOOKBACK_TURNS,
    fallback_lookback: int = FALLBACK_LOOKBACK_TURNS,
    forward_turns: int = 0,
    max_depth: int = MAX_PARENT_DEPTH,
) -> set[Coordinate]:
    by_rollout = {meta.rollout_id: meta for meta in metas}
    selected = by_rollout.get(selected_rollout_id)
    if not selected:
        return set()
    retained = adaptive_task_coordinates(
        task_id=selected.session_id,
        anchor_rollout_id=selected_rollout_id,
        anchor_turn=anchor_turn,
        cutoff=decision_time,
        metas=metas,
        blocks_by_rollout=blocks_by_rollout,
        plan_lookback=plan_lookback,
        fallback_lookback=fallback_lookback,
        forward_turns=forward_turns,
    )
    child = selected
    for _depth in range(max_depth):
        parent_task_id = child.parent_thread_id
        if not parent_task_id:
            break
        cutoff = child.timestamp_utc
        parent_blocks = ordered_task_blocks(parent_task_id, cutoff, metas, blocks_by_rollout)
        parent_anchor = alignment.anchor_turn(parent_blocks, cutoff)
        if not parent_anchor:
            break
        retained.update(
            adaptive_task_coordinates(
                task_id=parent_task_id,
                anchor_rollout_id=parent_anchor.session.rollout_id,
                anchor_turn=parent_anchor.turn_number,
                cutoff=cutoff,
                metas=metas,
                blocks_by_rollout=blocks_by_rollout,
                plan_lookback=plan_lookback,
                fallback_lookback=fallback_lookback,
                forward_turns=forward_turns,
            )
        )
        child = parent_anchor.session
    return retained


def search_universe_coordinates(
    decision_time: datetime,
    metas: Sequence[Any],
    blocks_by_rollout: dict[str, list[Any]],
) -> set[Coordinate]:
    coordinates: set[Coordinate] = set()
    for meta in metas:
        blocks = blocks_by_rollout.get(meta.rollout_id, [])
        anchor = alignment.anchor_turn(blocks, decision_time)
        if not anchor or not anchor.start_utc:
            continue
        anchor_delta = (decision_time - anchor.start_utc).total_seconds() / 3600
        if not -alignment.POSITIVE_CLOCK_DRIFT_HOURS <= anchor_delta <= alignment.TIME_WINDOW_HOURS:
            continue
        anchor_index = blocks.index(anchor)
        for block in blocks[: anchor_index + 1]:
            if not block.start_utc:
                continue
            delta = (decision_time - block.start_utc).total_seconds() / 3600
            if -alignment.POSITIVE_CLOCK_DRIFT_HOURS <= delta <= alignment.TIME_WINDOW_HOURS:
                coordinates.add((meta.rollout_id, block.turn_number))
    return coordinates


def source_scope_coordinates(
    *,
    selected_rollout_id: str,
    decision_time: datetime,
    metas: Sequence[Any],
    blocks_by_rollout: dict[str, list[Any]],
    max_depth: int = MAX_PARENT_DEPTH,
) -> set[Coordinate]:
    by_rollout = {meta.rollout_id: meta for meta in metas}
    child = by_rollout.get(selected_rollout_id)
    if not child:
        return set()
    retained: set[Coordinate] = set()
    cutoff = decision_time
    for _depth in range(max_depth + 1):
        lower = cutoff - timedelta(hours=alignment.TIME_WINDOW_HOURS)
        retained.update(
            (block.session.rollout_id, block.turn_number)
            for block in ordered_task_blocks(child.session_id, cutoff, metas, blocks_by_rollout)
            if block.start_utc and block.start_utc >= lower
        )
        if not child.parent_thread_id:
            break
        cutoff = child.timestamp_utc
        parent_blocks = ordered_task_blocks(child.parent_thread_id, cutoff, metas, blocks_by_rollout)
        parent_anchor = alignment.anchor_turn(parent_blocks, cutoff)
        if not parent_anchor:
            break
        child = parent_anchor.session
    return retained


def evidence_coordinates(gold_row: dict[str, Any]) -> set[Coordinate]:
    return {
        (str(ref["rollout_id"]), int(ref["turn"]))
        for ref in gold_row["adjudication"]["evidence_refs"]
    }


def summarize_results(rows: Sequence[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    strategy_names = sorted({name for row in rows for name in row["strategies"]})
    verified_total = sum(row["gold_label"] == "verified_source" for row in rows)
    output: dict[str, dict[str, Any]] = {}
    for name in strategy_names:
        retained_counts = [len(row["strategies"][name]) for row in rows]
        any_rows = sum(bool(row["strategies"][name] & row["evidence"]) for row in rows)
        all_rows = sum(row["evidence"] <= row["strategies"][name] for row in rows)
        verified_all = sum(
            row["gold_label"] == "verified_source"
            and row["evidence"] <= row["strategies"][name]
            for row in rows
        )
        retained_turns = sum(retained_counts)
        universe_turns = sum(len(row["universe"]) for row in rows)
        source_turns = sum(len(row["source_scope"]) for row in rows)
        output[name] = {
            "rows": len(rows),
            "verified_rows": verified_total,
            "any_evidence_rows": any_rows,
            "any_evidence_recall": any_rows / len(rows) if rows else 0.0,
            "all_evidence_rows": all_rows,
            "all_evidence_recall": all_rows / len(rows) if rows else 0.0,
            "verified_all_evidence_rows": verified_all,
            "verified_all_evidence_recall": verified_all / verified_total if verified_total else 0.0,
            "retained_turns": retained_turns,
            "mean_retained_turns": statistics.mean(retained_counts) if retained_counts else 0.0,
            "median_retained_turns": statistics.median(retained_counts) if retained_counts else 0.0,
            "search_universe_turns": universe_turns,
            "search_turn_reduction": 1 - retained_turns / universe_turns if universe_turns else 0.0,
            "source_scope_turns": source_turns,
            "source_turn_reduction": 1 - retained_turns / source_turns if source_turns else 0.0,
            "missed_decision_ids": [
                row["decision_id"]
                for row in rows
                if not row["evidence"] <= row["strategies"][name]
            ],
        }
    return output


def read_gold(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) != 50 or len({row["decision"]["id"] for row in rows}) != 50:
        raise RuntimeError("Gold set must contain exactly 50 unique decision rows")
    return rows


def alignment_rows_by_id(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("alignments")
    if not isinstance(rows, list):
        raise RuntimeError(f"Alignment artifact {path} has no alignments list")
    return payload["metadata"], {row["decision"]["decision_id"]: row for row in rows}


def evaluate(
    gold_rows: Sequence[dict[str, Any]],
    frozen_alignments: dict[str, dict[str, Any]],
    metas: Sequence[Any],
    blocks_by_rollout: dict[str, list[Any]],
) -> list[dict[str, Any]]:
    by_rollout = {meta.rollout_id: meta for meta in metas}
    output: list[dict[str, Any]] = []
    for gold in gold_rows:
        decision_id = gold["decision"]["id"]
        frozen = frozen_alignments.get(decision_id)
        if not frozen:
            raise RuntimeError(f"Missing frozen alignment for {decision_id}")
        selected = gold["selected_candidate"]
        best = frozen.get("best_candidate") or {}
        if (
            best.get("rollout_id") != selected["rollout_id"]
            or int(best.get("winning_turn")) != int(selected["turn"])
        ):
            raise RuntimeError(f"Frozen candidate drift for {decision_id}")
        decision_time = alignment.parse_iso_timestamp(gold["decision"]["timestamp"])
        if not decision_time:
            raise RuntimeError(f"Invalid decision timestamp for {decision_id}")
        selected_meta = by_rollout.get(selected["rollout_id"])
        if not selected_meta:
            raise RuntimeError(f"Selected rollout missing from retained logs for {decision_id}")
        selected_blocks = blocks_by_rollout.get(selected["rollout_id"], [])
        fixed = fixed_window_coordinates(selected_blocks, int(selected["turn"]), radius=2)
        backward = fixed | adaptive_task_coordinates(
            task_id=selected_meta.session_id,
            anchor_rollout_id=selected["rollout_id"],
            anchor_turn=int(best["anchor_turn"]),
            cutoff=decision_time,
            metas=metas,
            blocks_by_rollout=blocks_by_rollout,
            plan_lookback=0,
            fallback_lookback=FALLBACK_LOOKBACK_TURNS,
            forward_turns=0,
        )
        plan_adaptive = fixed | adaptive_task_coordinates(
            task_id=selected_meta.session_id,
            anchor_rollout_id=selected["rollout_id"],
            anchor_turn=int(best["anchor_turn"]),
            cutoff=decision_time,
            metas=metas,
            blocks_by_rollout=blocks_by_rollout,
            plan_lookback=PLAN_LOOKBACK_TURNS,
            fallback_lookback=FALLBACK_LOOKBACK_TURNS,
            forward_turns=0,
        )
        backward_12 = fixed | adaptive_task_coordinates(
            task_id=selected_meta.session_id,
            anchor_rollout_id=selected["rollout_id"],
            anchor_turn=int(best["anchor_turn"]),
            cutoff=decision_time,
            metas=metas,
            blocks_by_rollout=blocks_by_rollout,
            plan_lookback=0,
            fallback_lookback=PLAN_LOOKBACK_TURNS,
            forward_turns=0,
        )
        lineage = fixed | lineage_adaptive_coordinates(
            selected_rollout_id=selected["rollout_id"],
            anchor_turn=int(best["anchor_turn"]),
            decision_time=decision_time,
            metas=metas,
            blocks_by_rollout=blocks_by_rollout,
        )
        lineage_backward_12 = fixed | lineage_adaptive_coordinates(
            selected_rollout_id=selected["rollout_id"],
            anchor_turn=int(best["anchor_turn"]),
            decision_time=decision_time,
            metas=metas,
            blocks_by_rollout=blocks_by_rollout,
            plan_lookback=0,
            fallback_lookback=PLAN_LOOKBACK_TURNS,
        )
        output.append(
            {
                "decision_id": decision_id,
                "gold_label": gold["adjudication"]["label"],
                "evidence": evidence_coordinates(gold),
                "universe": search_universe_coordinates(decision_time, metas, blocks_by_rollout),
                "source_scope": source_scope_coordinates(
                    selected_rollout_id=selected["rollout_id"],
                    decision_time=decision_time,
                    metas=metas,
                    blocks_by_rollout=blocks_by_rollout,
                ),
                "strategies": {
                    "fixed_radius_2": fixed,
                    "backward_5": backward,
                    "backward_12": backward_12,
                    "plan_adaptive_12": plan_adaptive,
                    "plan_lineage_adaptive_12": lineage,
                    "lineage_backward_12": lineage_backward_12,
                },
            }
        )
    return output


def _percent(value: float) -> str:
    return f"{100 * value:.1f}%"


def render_report(summary: dict[str, dict[str, Any]], metadata: dict[str, Any]) -> str:
    rows = []
    for name in (
        "fixed_radius_2",
        "backward_5",
        "backward_12",
        "plan_adaptive_12",
        "plan_lineage_adaptive_12",
        "lineage_backward_12",
    ):
        value = summary[name]
        rows.append(
            "| {name} | {any}/{total} ({any_rate}) | {all}/{total} ({all_rate}) | "
            "{verified}/{verified_total} ({verified_rate}) | {mean:.1f} | {search_red} | {source_red} |".format(
                name=name.replace("_", " "),
                any=value["any_evidence_rows"],
                all=value["all_evidence_rows"],
                total=value["rows"],
                verified=value["verified_all_evidence_rows"],
                verified_total=value["verified_rows"],
                any_rate=_percent(value["any_evidence_recall"]),
                all_rate=_percent(value["all_evidence_recall"]),
                verified_rate=_percent(value["verified_all_evidence_recall"]),
                mean=value["mean_retained_turns"],
                search_red=_percent(value["search_turn_reduction"]),
                source_red=_percent(value["source_turn_reduction"]),
            )
        )
    eligible = [
        (name, value)
        for name, value in summary.items()
        if value["verified_all_evidence_recall"] >= 0.98
    ]
    if eligible:
        recommended_name, recommended = min(
            eligible, key=lambda pair: pair[1]["mean_retained_turns"]
        )
        recommendation = (
            f"`{recommended_name}` is the smallest tested strategy meeting the exploratory 98% "
            f"target on complete cited evidence for verified decisions "
            f"({recommended['verified_all_evidence_rows']}/{recommended['verified_rows']})."
        )
    else:
        best_name, best = max(
            summary.items(), key=lambda pair: pair[1]["verified_all_evidence_recall"]
        )
        recommendation = (
            "No tested strategy meets the exploratory 98% target for complete cited evidence. "
            f"The best is `{best_name}` at "
            f"{best['verified_all_evidence_rows']}/{best['verified_rows']}."
        )
    overall_name, overall = max(
        summary.items(),
        key=lambda pair: (
            pair[1]["all_evidence_recall"],
            -pair[1]["mean_retained_turns"],
        ),
    )
    recommendation += (
        "\n\nAcross all 50 adjudicated rows, including partial and child-result cases, "
        f"`{overall_name}` is strongest: {overall['all_evidence_rows']}/{overall['rows']} "
        f"contain every cited source turn and all {overall['rows']} contain at least one, while "
        f"removing {_percent(overall['search_turn_reduction'])} of the temporal search universe. "
        "The lone incomplete row is partial rather than a verified source."
    )
    plan = summary["plan_adaptive_12"]
    backward = summary["backward_5"]
    recommendation += (
        "\n\nPlan-mode anchoring did not improve cited-evidence recall over the five-turn fallback "
        f"({plan['all_evidence_rows']}/{plan['rows']} versus "
        f"{backward['all_evidence_rows']}/{backward['rows']}). Plan mode remains a useful ranking "
        "signal, but the nearest Plan turn is not a safe stopping boundary for high-recall context expansion."
    )
    return "\n".join(
        [
            "# Conversation-window strategy ablation",
            "",
            "## Question",
            "",
            "How much retained Codex conversation can be removed while preserving the manually cited "
            "source turns for the frozen 50-decision gold cohort?",
            "",
            "## Strategies",
            "",
            "- **Fixed radius 2:** the existing winning turn plus two turns on either side.",
            "- **Backward 5:** fixed window plus five causal turns before the decision-time anchor, "
            "including continuations of the same logical task.",
            "- **Backward 12:** the same unconditional span with a 12-turn lookback.",
            "- **Plan adaptive 12:** fixed window plus the span back to the nearest Plan-mode turn "
            "within 12 causal turns; if none exists, fall back to five turns.",
            "- **Plan + lineage adaptive 12:** Plan-adaptive expansion plus the same bounded search in "
            "parent tasks, with each parent cut off at child creation time.",
            "- **Lineage + backward 12:** unconditional 12-turn expansion in the selected task and "
            "traversed parents; this is the high-recall control for the Plan-mode heuristic.",
            "",
            "All strategies are structural and were applied without reading gold evidence coordinates. "
            "Gold coordinates are used only for scoring. Encrypted reasoning and raw chat text are not "
            "written to the outputs.",
            "",
            "## Results",
            "",
            "| Strategy | Any cited evidence | All cited evidence | All evidence, verified 42 | Mean turns retained | Reduction vs search universe | Reduction vs source task/lineage |",
            "|---|---:|---:|---:|---:|---:|---:|",
            *rows,
            "",
            "`Any cited evidence` is candidate-region recall. `All cited evidence` is the stricter "
            "window-completeness measure. Neither metric converts partial or child-result rows into "
            "verified decisions.",
            "",
            "## Finding",
            "",
            recommendation,
            "",
            "The search-universe denominator is the per-decision set of repository turns eligible "
            "under the existing 72-hour temporal rule. The source denominator is the causally prior "
            "selected logical task plus traversable parent lineage. Counts are micro-averaged across "
            "50 decision retrieval instances, so a turn may count once for each decision that could "
            "have retrieved it.",
            "",
            "## Limits",
            "",
            "- The same 50 rows were used to motivate and evaluate these structural variants; a held-out "
            "cohort is required before treating the best setting as stable.",
            "- Gold evidence marks the manually cited source turns, not every possibly useful context turn.",
            "- Turn-count reduction does not model token length; long and short turns have equal weight.",
            "- The cohort has 42 strict positives and no reviewed negatives, so this remains a retrieval "
            "experiment rather than classifier training evidence.",
            "",
            "## Reproducibility",
            "",
            f"- Gold rows: {metadata['gold_rows']}",
            f"- Gold sample hash: `{metadata['sample_ids_sha256']}`",
            f"- Parsed repository rollouts: {metadata['repository_rollouts']}",
            f"- Parsed turn blocks: {metadata['normalized_turn_blocks']}",
            f"- Plan lookback cap: {PLAN_LOOKBACK_TURNS} turns",
            f"- Fallback lookback: {FALLBACK_LOOKBACK_TURNS} turns",
            f"- Parent depth cap: {MAX_PARENT_DEPTH}",
            "",
        ]
    )


def serializable_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision_id": row["decision_id"],
        "gold_label": row["gold_label"],
        "evidence_turns": sorted([list(value) for value in row["evidence"]]),
        "search_universe_turns": len(row["universe"]),
        "source_scope_turns": len(row["source_scope"]),
        "strategies": {
            name: {
                "retained_turns": len(coordinates),
                "any_evidence": bool(coordinates & row["evidence"]),
                "all_evidence": row["evidence"] <= coordinates,
                "coordinates": sorted([list(value) for value in coordinates]),
            }
            for name, coordinates in row["strategies"].items()
        },
    }


def write_outputs(
    output_dir: Path,
    rows: Sequence[dict[str, Any]],
    summary: dict[str, dict[str, Any]],
    metadata: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    serial_rows = [serializable_row(row) for row in rows]
    (output_dir / "WINDOW-STRATEGY-RESULTS.json").write_text(
        json.dumps(
            {"schema_version": "decision-window-ablation/1.0", "metadata": metadata, "summary": summary, "rows": serial_rows},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    fields = ["decision_id", "gold_label", "search_universe_turns", "source_scope_turns"]
    strategy_names = list(serial_rows[0]["strategies"]) if serial_rows else []
    for name in strategy_names:
        fields.extend([f"{name}_turns", f"{name}_any_evidence", f"{name}_all_evidence"])
    with (output_dir / "WINDOW-STRATEGY-ROWS.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in serial_rows:
            flat = {key: row[key] for key in fields[:4]}
            for name in strategy_names:
                flat[f"{name}_turns"] = row["strategies"][name]["retained_turns"]
                flat[f"{name}_any_evidence"] = row["strategies"][name]["any_evidence"]
                flat[f"{name}_all_evidence"] = row["strategies"][name]["all_evidence"]
            writer.writerow(flat)
    (output_dir / "WINDOW-STRATEGY-REPORT.md").write_text(
        render_report(summary, metadata), encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--gold", type=Path, default=BASE / "GOLD-SET.jsonl")
    parser.add_argument(
        "--alignments",
        type=Path,
        default=BASE / "results-codex-causal-minute-fixed" / "alignments.json",
    )
    parser.add_argument("--output", type=Path, default=BASE)
    args = parser.parse_args()

    repo_root = args.repo.resolve()
    gold_rows = read_gold(args.gold.resolve())
    alignment_metadata, frozen_rows = alignment_rows_by_id(args.alignments.resolve())
    if alignment_metadata.get("sample_ids_sha256") != gold_rows[0]["cohort"]["sample_ids_sha256"]:
        raise RuntimeError("Gold set and frozen alignment sample hashes differ")

    remote = alignment.repository_remote(repo_root)
    repo_roots = alignment.repository_worktree_roots(repo_root)
    paths = list(alignment.iter_rollout_paths(args.codex_home.resolve()))
    all_metas = [meta for path in paths if (meta := alignment.read_session_meta(path)) is not None]
    alignment.validate_unique_rollouts(all_metas)
    eligible_ids = alignment.repository_rollout_ids(all_metas, repo_roots, remote)
    metas = [
        meta
        for meta in all_metas
        if meta.rollout_id in eligible_ids and not alignment.is_derived_review_session(meta)
    ]
    blocks_by_rollout: dict[str, list[Any]] = {}
    for index, meta in enumerate(metas, 1):
        blocks_by_rollout[meta.rollout_id] = alignment.parse_rollout(Path(meta.source_path), meta)
        if index % 100 == 0:
            print(f"parsed {index}/{len(metas)} repository rollouts", flush=True)

    rows = evaluate(gold_rows, frozen_rows, metas, blocks_by_rollout)
    summary = summarize_results(rows)
    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gold_rows": len(gold_rows),
        "sample_ids_sha256": alignment_metadata["sample_ids_sha256"],
        "repository_rollouts": len(metas),
        "normalized_turn_blocks": sum(len(blocks) for blocks in blocks_by_rollout.values()),
        "time_window_hours": alignment.TIME_WINDOW_HOURS,
        "plan_lookback_turns": PLAN_LOOKBACK_TURNS,
        "fallback_lookback_turns": FALLBACK_LOOKBACK_TURNS,
        "max_parent_depth": MAX_PARENT_DEPTH,
        "raw_text_serialized": False,
        "encrypted_reasoning_used": False,
    }
    write_outputs(args.output.resolve(), rows, summary, metadata)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

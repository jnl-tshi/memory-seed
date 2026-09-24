"""Measure a bounded backward search across nearby Codex sessions.

The frozen matcher prefers repository rollouts. This development-only ablation
adds preceding sessions by their *last eligible turn activity*, including voice
and projectless sessions. It uses gold citations only to score coverage, never
to select sessions. Full selected sessions are an oracle fallback upper bound,
not a proposed curator payload or deployable semantic stop rule.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any, Iterable, Sequence


BASE = Path(__file__).resolve().parent


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, BASE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


alignment = load_module("align_decisions_nearby", "align_decisions.py")
windows = load_module("evaluate_windows_nearby", "evaluate_window_strategies.py")
ranked = load_module("evaluate_ranked_nearby", "evaluate_ranked_decision_spans.py")

Coordinate = tuple[str, int]
Group = tuple[str, Any, set[Coordinate]]


def rank_session_groups(
    coordinates: Iterable[Coordinate], blocks_by_rollout: dict[str, list[Any]],
) -> list[Group]:
    """Group eligible turns by logical session, most recent turn first."""
    indexed = {
        (rollout_id, block.turn_number): block
        for rollout_id, blocks in blocks_by_rollout.items()
        for block in blocks
    }
    groups: dict[str, tuple[Any, set[Coordinate]]] = {}
    for coordinate in set(coordinates):
        block = indexed.get(coordinate)
        if not block or not block.start_utc:
            continue
        session_id = str(block.session.session_id)
        if session_id not in groups:
            groups[session_id] = (block.start_utc, set())
        activity, retained = groups[session_id]
        retained.add(coordinate)
        groups[session_id] = (max(activity, block.start_utc), retained)
    return sorted(
        ((session_id, activity, retained) for session_id, (activity, retained) in groups.items()),
        key=lambda group: (-group[1].timestamp(), group[0]),
    )


def select_coordinates(
    groups: Sequence[Group], *, selected_session: str, count: int,
) -> set[Coordinate]:
    """Retain the baseline session and at most count other recent sessions."""
    if count < 0:
        raise ValueError("neighbor count cannot be negative")
    selected: set[Coordinate] = set()
    for session_id, _activity, coordinates in groups:
        if session_id == selected_session:
            selected.update(coordinates)
            break
    additions = 0
    for session_id, _activity, coordinates in groups:
        if session_id == selected_session:
            continue
        if additions >= count:
            break
        selected.update(coordinates)
        additions += 1
    return selected


def rank_groups_by_text(
    groups: Sequence[Group], blocks_by_rollout: dict[str, list[Any]],
    query: str, cutoff: Any,
) -> list[Group]:
    """Order nearby groups by best visible message overlap, with recency ties."""
    indexed = {
        (rollout_id, block.turn_number): block
        for rollout_id, blocks in blocks_by_rollout.items()
        for block in blocks
    }

    def score(group: Group) -> float:
        return max((
            ranked.lexical_score(
                query,
                "\n".join(
                    item.text for item in ranked.causal_items(indexed[coordinate], cutoff)
                    if item.role in {"user", "assistant", "reasoning_summary"}
                ),
            )
            for coordinate in group[2]
        ), default=0.0)

    return sorted(groups, key=lambda group: (-score(group), -group[1].timestamp(), group[0]))


def evaluate(
    gold_rows: Sequence[dict[str, Any]], metas: Sequence[Any],
    blocks_by_rollout: dict[str, list[Any]], repo_rollout_ids: set[str], repo: Path,
    window_by_id: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    variants = ["repo_neighbor_3", "all_neighbor_1", "all_neighbor_3", "all_neighbor_5", "all_neighbor_10",
                "text_neighbor_1", "text_neighbor_3", "text_neighbor_5", "hybrid_recent1_text1"]
    if window_by_id is not None:
        variants.extend(("hybrid_ranked_3", "hybrid_ranked_5", "hybrid_ranked_10"))
    rows: list[dict[str, Any]] = []
    for gold in gold_rows:
        cutoff = alignment.parse_iso_timestamp(gold["decision"]["timestamp"])
        if cutoff is None:
            raise ValueError("Invalid decision timestamp")
        universe = windows.search_universe_coordinates(cutoff, metas, blocks_by_rollout)
        groups = rank_session_groups(universe, blocks_by_rollout)
        selected_session = str(gold["selected_candidate"]["logical_session_id"])
        repo_groups = [
            group for group in groups
            if any(rollout_id in repo_rollout_ids for rollout_id, _turn in group[2])
        ]
        query = gold["decision"]["title"] + "\n" + ranked.decision_query(repo, gold["decision"])
        text_groups = rank_groups_by_text(groups, blocks_by_rollout, query, cutoff)
        evidence = windows.evidence_coordinates(gold)
        stage_coordinates = {
            "repo_neighbor_3": select_coordinates(repo_groups, selected_session=selected_session, count=3),
            **{
                f"all_neighbor_{count}": select_coordinates(groups, selected_session=selected_session, count=count)
                for count in (1, 3, 5, 10)
            },
            **{
                f"text_neighbor_{count}": select_coordinates(text_groups, selected_session=selected_session, count=count)
                for count in (1, 3, 5)
            },
        }
        stage_coordinates["hybrid_recent1_text1"] = (
            stage_coordinates["all_neighbor_1"] | stage_coordinates["text_neighbor_1"]
        )
        if window_by_id is not None:
            window_row = window_by_id[gold["decision"]["id"]]
            baseline = {
                (str(coord[0]), int(coord[1]))
                for coord in window_row["strategies"]["lineage_backward_20"]["coordinates"]
            }
            hybrid_coords = stage_coordinates["hybrid_recent1_text1"]
            hybrid_blocks = [
                block for rollout_id, blocks in blocks_by_rollout.items()
                for block in blocks
                if (rollout_id, block.turn_number) in hybrid_coords
            ]
            spans = ranked.rank_spans(hybrid_blocks, query, None, cutoff, variant="lexical")
            for count in (3, 5, 10):
                stage_coordinates[f"hybrid_ranked_{count}"] = baseline | ranked.select_top(spans, count)
        rows.append({
            "decision_id": gold["decision"]["id"],
            "gold_label": gold["adjudication"]["label"],
            "selected_session": selected_session,
            "eligible_session_count": len(groups),
            "evidence_turns": [list(coord) for coord in sorted(evidence)],
            "stages": {
                name: {
                    "coordinates": [list(coord) for coord in sorted(coordinates)],
                    "turns": len(coordinates),
                    "contains_all_evidence": bool(evidence) and evidence <= coordinates,
                }
                for name, coordinates in stage_coordinates.items()
            },
        })
    verified = [row for row in rows if row["gold_label"] == "verified_source"]
    summary = {
        name: {
            "verified_rows": len(verified),
            "verified_all_evidence_rows": sum(row["stages"][name]["contains_all_evidence"] for row in verified),
            "total_turns": sum(row["stages"][name]["turns"] for row in rows),
            "missed_verified_ids": [row["decision_id"] for row in verified if not row["stages"][name]["contains_all_evidence"]],
        }
        for name in variants
    }
    return {
        "schema_version": "decision-nearby-session-fallback/1.0",
        "metadata": {
            "causal_interval": "turn start within the preceding 72 hours and before record minute + one minute",
            "session_order": "last eligible turn timestamp descending; repository affinity is an ablation, not a hard production filter",
            "source_policy": "gold citations used for evaluation only; no label-aware selection",
            "text_rank": "max visible user/assistant/reasoning-summary lexical overlap with the already-written decision record; retrospective only",
            "fallback_caveat": "full neighboring sessions are an upper-bound oracle stage, not a safe semantic stop or recommended curator payload",
            "ranked_fallback": "when window results are supplied, union the baseline 20-turn envelope with top lexical spans from the hybrid nearby-session pool",
            "eligible_rollout_ids_sha256": hashlib.sha256("\n".join(sorted(blocks_by_rollout)).encode()).hexdigest(),
            "eligible_rollout_count": len(blocks_by_rollout),
            "repository_rollout_count": len(repo_rollout_ids & set(blocks_by_rollout)),
        },
        "summary": summary,
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--window-results", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    gold = windows.read_gold(args.gold)
    latest = max(alignment.parse_iso_timestamp(row["decision"]["timestamp"]) for row in gold)
    paths = list(alignment.iter_rollout_paths(args.codex_home.resolve()))
    metas = [
        meta for path in paths
        if (meta := alignment.read_session_meta(path)) is not None
        and meta.timestamp_utc < latest + timedelta(minutes=1)
        and not alignment.is_derived_review_session(meta)
    ]
    alignment.validate_unique_rollouts(metas)
    remote = alignment.repository_remote(args.repo.resolve())
    roots = alignment.repository_worktree_roots(args.repo.resolve())
    repo_rollout_ids = alignment.repository_rollout_ids(metas, roots, remote)
    blocks = {}
    for index, meta in enumerate(metas, 1):
        blocks[meta.rollout_id] = alignment.parse_rollout(Path(meta.source_path), meta)
        if index % 100 == 0:
            print(f"parsed {index}/{len(metas)} nearby-search rollouts", flush=True)
    window_by_id = None
    if args.window_results:
        payload = json.loads(args.window_results.read_text(encoding="utf-8"))
        window_by_id = {row["decision_id"]: row for row in payload["rows"]}
        if set(window_by_id) != {row["decision"]["id"] for row in gold}:
            raise ValueError("Window-results cohort must equal the gold cohort")
    result = evaluate(gold, metas, blocks, repo_rollout_ids, args.repo.resolve(), window_by_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

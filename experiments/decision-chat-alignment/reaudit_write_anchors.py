"""Post-audit, write-event-anchored review of unresolved decision/source pairs.

This does not change the frozen matcher or sealed gold labels. It finds a
completed session-record write in the selected logical task or a child task,
then returns a lineage-aware backward window clipped *within* the writer turn
at the write event. Only coordinates and counts are written, never chat text.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


BASE = Path(__file__).resolve().parent


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, BASE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


alignment = _load("align_decisions_write_reaudit", "align_decisions.py")
windows = _load("evaluate_windows_write_reaudit", "evaluate_window_strategies.py")


@dataclass(frozen=True)
class WriteEvent:
    timestamp: str
    ordinal: int | None
    kind: str


def _normalized_path(path: str) -> str:
    return path.replace("\\", "/").casefold().lstrip("./")


def _same_session_target(changed_path: str, record_path: str) -> bool:
    changed = _normalized_path(changed_path)
    target = _normalized_path(record_path)
    if changed.endswith(target):
        return True
    # Historical records used sessions/YYYY-MM-DD.md before month grouping.
    basename = target.rsplit("/", 1)[-1]
    return "/.memory-seed/sessions/" in f"/{changed}" and changed.endswith("/" + basename)


def _output_text(output: Any) -> str:
    if isinstance(output, str):
        return output
    if isinstance(output, list):
        return "\n".join(
            item.get("text", "") for item in output if isinstance(item, dict)
        )
    return ""


def find_write_event(path: Path, entry_id: str, record_path: str) -> WriteEvent | None:
    """Find a completed write, rejecting previews and later mere mentions."""
    found: list[WriteEvent] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if entry_id not in line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            stamp = row.get("timestamp")
            if not isinstance(stamp, str) or alignment.parse_iso_timestamp(stamp) is None:
                continue
            payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
            kind = None
            if row.get("type") == "event_msg" and payload.get("type") == "item_completed":
                item = payload.get("item") if isinstance(payload.get("item"), dict) else {}
                if item.get("type") == "FileChange" and item.get("status") in (None, "completed"):
                    changes = item.get("changes") if isinstance(item.get("changes"), dict) else {}
                    if any(
                        _same_session_target(name, record_path)
                        and entry_id in json.dumps(change, ensure_ascii=False)
                        for name, change in changes.items()
                    ):
                        kind = "file_change"
            elif row.get("type") == "response_item" and payload.get("type") in {
                "custom_tool_call_output", "function_call_output"
            }:
                result = _output_text(payload.get("output"))
                if re.search(rf"(?m)^\s*Appended\s+{re.escape(entry_id)}\b", result):
                    kind = "append_receipt"
            if kind:
                found.append(WriteEvent(stamp, row.get("ordinal"), kind))
    return min(found, key=lambda event: alignment.parse_iso_timestamp(event.timestamp)) if found else None


def belongs_to_lineage(meta: Any, selected_task_id: str, metas: Sequence[Any]) -> bool:
    """A writer may be a continuation or a descendant of the selected task."""
    by_task = {item.session_id: item for item in metas}
    task = meta.session_id
    seen: set[str] = set()
    while task and task not in seen:
        if task == selected_task_id:
            return True
        seen.add(task)
        parent = by_task.get(task)
        task = parent.parent_thread_id if parent else None
    return False


def prewrite_items(items: Sequence[Any], write_timestamp: str) -> list[Any]:
    """Never expose the session record itself or later text from its turn."""
    cutoff = alignment.parse_iso_timestamp(write_timestamp)
    if cutoff is None:
        raise ValueError("Invalid write timestamp")
    return [
        item for item in items
        if (stamp := alignment.parse_iso_timestamp(item.timestamp)) is not None and stamp < cutoff
    ]


def validate_selection(
    selection: dict[str, Any], write_row: dict[str, Any], blocks_by_rollout: dict[str, list[Any]],
) -> list[dict[str, Any]]:
    """Validate reviewed citations against the bounded, strictly pre-write raw log."""
    decision_id = selection.get("decision_id")
    if decision_id != write_row.get("decision_id") or write_row.get("status") != "write_event_found":
        raise ValueError(f"{decision_id}: no matching completed write event")
    label = selection.get("label")
    if label not in {"verified_source", "unresolved"}:
        raise ValueError(f"{decision_id}: invalid post-audit label")
    refs = selection.get("evidence_refs", [])
    if label == "unresolved" and refs:
        raise ValueError(f"{decision_id}: unresolved selection must not claim evidence")
    if label == "verified_source" and not refs:
        raise ValueError(f"{decision_id}: verified selection lacks evidence")
    if not isinstance(selection.get("rationale"), str) or not selection["rationale"].strip():
        raise ValueError(f"{decision_id}: rationale is required")
    scope = {tuple(coordinate) for coordinate in write_row["backward_20_lineage_coordinates"]}
    cutoff = alignment.parse_iso_timestamp(write_row["write_event_timestamp"])
    if cutoff is None:
        raise ValueError(f"{decision_id}: invalid write timestamp")
    checked: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for ref in refs:
        rollout_id, turn = ref.get("rollout_id"), ref.get("turn")
        if (rollout_id, turn) not in scope:
            raise ValueError(f"{decision_id}: citation outside backward scope")
        blocks = [block for block in blocks_by_rollout.get(rollout_id, []) if block.turn_number == turn]
        if len(blocks) != 1:
            raise ValueError(f"{decision_id}: cited turn unavailable or ambiguous")
        items = {item.source_ordinal: item for item in [*blocks[0].items, *blocks[0].reasoning_summary_items]}
        ordinals = ref.get("ordinals")
        if not isinstance(ordinals, list) or not ordinals or any(not isinstance(n, int) for n in ordinals):
            raise ValueError(f"{decision_id}: invalid citation ordinals")
        for ordinal in ordinals:
            if (rollout_id, ordinal) in seen:
                raise ValueError(f"{decision_id}: duplicate citation")
            seen.add((rollout_id, ordinal))
            item = items.get(ordinal)
            if item is None:
                raise ValueError(f"{decision_id}: citation absent from normalized turn")
            stamp = alignment.parse_iso_timestamp(item.timestamp)
            if stamp is None or stamp >= cutoff:
                raise ValueError(f"{decision_id}: citation not before write")
            checked.append({"rollout_id": rollout_id, "turn": turn, "ordinal": ordinal,
                            "timestamp": item.timestamp, "role": item.role})
    return checked


def _read_gold(paths: Sequence[Path]) -> list[dict[str, Any]]:
    rows = [json.loads(line) for path in paths for line in path.read_text(encoding="utf-8").splitlines() if line]
    ids = [row["decision"]["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate gold decision ID")
    return rows


def reaudit(rows: Sequence[dict[str, Any]], codex_home: Path) -> list[dict[str, Any]]:
    metas = [meta for path in alignment.iter_rollout_paths(codex_home)
             if (meta := alignment.read_session_meta(path)) is not None]
    alignment.validate_unique_rollouts(metas)
    by_rollout = {meta.rollout_id: meta for meta in metas}
    result: list[dict[str, Any]] = []
    for gold in rows:
        if gold["adjudication"]["label"] != "unresolved":
            continue
        decision = gold["decision"]
        entry_id = decision["id"].split(":", 1)[0]
        selected = gold["selected_candidate"]
        selected_meta = by_rollout.get(selected["rollout_id"])
        if selected_meta is None:
            raise RuntimeError(f"Selected session missing: {decision['id']}")
        lineage = [meta for meta in metas if belongs_to_lineage(meta, selected_meta.session_id, metas)]
        events = [
            (event, meta) for meta in lineage
            if (event := find_write_event(Path(meta.source_path), entry_id, decision["record_path"])) is not None
        ]
        if not events:
            result.append({"decision_id": decision["id"], "status": "write_event_unavailable",
                           "selected_rollout_id": selected_meta.rollout_id})
            continue
        event, writer = min(events, key=lambda pair: alignment.parse_iso_timestamp(pair[0].timestamp))
        write_time = alignment.parse_iso_timestamp(event.timestamp)
        heading_time = alignment.parse_iso_timestamp(decision["timestamp"])
        assert write_time and heading_time
        task_ids = {writer.session_id}
        parent = writer
        for _ in range(windows.MAX_PARENT_DEPTH):
            if not parent.parent_thread_id:
                break
            task_ids.add(parent.parent_thread_id)
            parent = next((meta for meta in metas if meta.session_id == parent.parent_thread_id), parent)
            if parent.session_id not in task_ids:
                break
        context_metas = [meta for meta in metas if meta.session_id in task_ids]
        blocks = {meta.rollout_id: alignment.parse_rollout(Path(meta.source_path), meta)
                  for meta in context_metas}
        writer_anchor = alignment.anchor_turn(blocks[writer.rollout_id], write_time)
        if writer_anchor is None:
            raise RuntimeError(f"No writer turn for {decision['id']}")
        coordinates = windows.lineage_adaptive_coordinates(
            selected_rollout_id=writer.rollout_id,
            anchor_turn=writer_anchor.turn_number,
            decision_time=write_time,
            metas=context_metas,
            blocks_by_rollout=blocks,
            plan_lookback=0,
            fallback_lookback=windows.SAFETY_LOOKBACK_TURNS,
        )
        # A child may begin before its parent finishes review. The older
        # lineage envelope stops each parent at child launch, thereby missing
        # parent decisions made while the child is still running. For this
        # post-audit, admit each parent's bounded turns up to the actual
        # record write; item timestamps below still enforce strict causality.
        parent = writer
        for _ in range(windows.MAX_PARENT_DEPTH):
            if not parent.parent_thread_id:
                break
            parent_blocks = windows.ordered_task_blocks(parent.parent_thread_id, write_time, context_metas, blocks)
            parent_anchor = alignment.anchor_turn(parent_blocks, write_time)
            if parent_anchor is None:
                break
            coordinates.update(windows.adaptive_task_coordinates(
                task_id=parent.parent_thread_id,
                anchor_rollout_id=parent_anchor.session.rollout_id,
                anchor_turn=parent_anchor.turn_number,
                cutoff=write_time,
                metas=context_metas,
                blocks_by_rollout=blocks,
                plan_lookback=0,
                fallback_lookback=windows.SAFETY_LOOKBACK_TURNS,
                forward_turns=0,
            ))
            parent = parent_anchor.session
        indexed = {(rollout_id, block.turn_number): block for rollout_id, turns in blocks.items() for block in turns}
        eligible = sum(len(prewrite_items([*indexed[key].items, *indexed[key].reasoning_summary_items], event.timestamp))
                       for key in coordinates)
        blocked = sum(len([*indexed[key].items, *indexed[key].reasoning_summary_items]) for key in coordinates) - eligible
        result.append({
            "decision_id": decision["id"],
            "status": "write_event_found",
            "original_gold_label": gold["adjudication"]["label"],
            "record_heading_timestamp": decision["timestamp"],
            "write_event_timestamp": event.timestamp,
            "heading_skew_minutes": round((write_time - heading_time).total_seconds() / 60, 3),
            "write_event_kind": event.kind,
            "write_event_ordinal": event.ordinal,
            "writer_rollout_id": writer.rollout_id,
            "writer_parent_task_id": writer.parent_thread_id,
            "writer_in_selected_lineage": belongs_to_lineage(writer, selected_meta.session_id, metas),
            "original_winning_turn": selected["turn"],
            "write_anchor_turn": writer_anchor.turn_number,
            "backward_20_lineage_coordinates": [list(key) for key in sorted(coordinates)],
            "prewrite_normalized_item_count": eligible,
            "excluded_same_turn_or_later_item_count": blocked,
        })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, nargs="+", required=True)
    parser.add_argument("--codex-home", type=Path, default=Path.home() / ".codex")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--selections", type=Path, help="Optional post-audit judgments; never changes sealed gold")
    parser.add_argument("--selection-output", type=Path)
    args = parser.parse_args()
    if bool(args.selections) != bool(args.selection_output):
        parser.error("--selections and --selection-output must be supplied together")
    rows = _read_gold(args.gold)
    report = {
        "schema_version": "decision-write-anchor-reaudit/1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "completed record write in selected logical task or descendant; 20-turn lineage scope clipped before write event",
        "sealed_gold_mutated": False,
        "rows": reaudit(rows, args.codex_home.resolve()),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.selections:
        selections = json.loads(args.selections.read_text(encoding="utf-8"))["selections"]
        write_by_id = {row["decision_id"]: row for row in report["rows"]}
        if len(selections) != len(write_by_id) or {s["decision_id"] for s in selections} != set(write_by_id):
            raise ValueError("Post-audit selections must cover exactly the unresolved gold IDs")
        metas = [meta for path in alignment.iter_rollout_paths(args.codex_home.resolve())
                 if (meta := alignment.read_session_meta(path)) is not None]
        by_rollout = {meta.rollout_id: meta for meta in metas}
        parsed: dict[str, list[Any]] = {}
        amended = []
        for selection in selections:
            for ref in selection.get("evidence_refs", []):
                rollout_id = ref["rollout_id"]
                if rollout_id not in by_rollout:
                    raise ValueError(f"Source rollout missing: {rollout_id}")
                if rollout_id not in parsed:
                    meta = by_rollout[rollout_id]
                    parsed[rollout_id] = alignment.parse_rollout(Path(meta.source_path), meta)
            citations = validate_selection(selection, write_by_id[selection["decision_id"]], parsed)
            amended.append({"decision_id": selection["decision_id"], "original_label": "unresolved",
                            "post_audit_label": selection["label"], "rationale": selection["rationale"],
                            "evidence_refs": citations, "write_event_timestamp":
                            write_by_id[selection["decision_id"]]["write_event_timestamp"]})
        counts: dict[str, int] = {}
        for row in rows:
            counts[row["adjudication"]["label"]] = counts.get(row["adjudication"]["label"], 0) + 1
        post_counts = dict(counts)
        post_counts["unresolved"] -= sum(row["post_audit_label"] == "verified_source" for row in amended)
        post_counts["verified_source"] = post_counts.get("verified_source", 0) + sum(
            row["post_audit_label"] == "verified_source" for row in amended)
        output = {"schema_version": "decision-source-postaudit/1.0", "sealed_gold_mutated": False,
                  "status": "post_hoc_exploratory_not_heldout_performance", "original_counts": counts,
                  "post_audit_counts": post_counts, "rows": amended}
        args.selection_output.parent.mkdir(parents=True, exist_ok=True)
        args.selection_output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"rows": len(report["rows"]), "write_events": sum(row["status"] == "write_event_found" for row in report["rows"])}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

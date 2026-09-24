"""Measure local-tokenizer payload sizes for frozen decision-chat candidate windows.

Counts are deterministic estimates for the serialization below, not provider billing tokens.
Normalized messages, readable reasoning summaries, and text-only raw tool outputs are counted
separately. Encrypted reasoning and multimodal payload bytes are excluded and reported.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import statistics
import sys
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
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


alignment = load_module("align_decisions", "align_decisions.py")
ranked = load_module("evaluate_ranked_decision_spans", "evaluate_ranked_decision_spans.py")
window_eval = load_module("evaluate_window_strategies", "evaluate_window_strategies.py")


def load_tokenizer(path: Path):
    """Load a caller-supplied local tokenizer.json; never downloads model assets."""
    if not path.is_file():
        raise FileNotFoundError(f"Local tokenizer.json not found: {path}")
    try:
        from tokenizers import Tokenizer
    except ImportError as exc:
        raise RuntimeError("The `tokenizers` package is required to count tokens") from exc
    return Tokenizer.from_file(str(path))


def tokenizer_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def message_key(rollout_id: str, item: Any) -> tuple[Any, ...]:
    if item.source_ordinal is not None:
        return (rollout_id, item.source_ordinal)
    stamp = item.timestamp or ""
    text_hash = hashlib.sha256(item.text.encode("utf-8")).hexdigest()
    return (rollout_id, item.turn_number, stamp, item.role, text_hash)


def collect_items(
    coordinates: Iterable[tuple[str, int]],
    blocks_by_rollout: dict[str, list[Any]],
    cutoff: datetime | None = None,
) -> list[tuple[str, Any]]:
    """Collect unique normalized messages in source order, optionally causally cut off."""
    selected = set(coordinates)
    unique: dict[tuple[Any, ...], tuple[str, Any]] = {}
    for rollout_id, turn in sorted(selected):
        for block in blocks_by_rollout.get(rollout_id, []):
            if block.turn_number != turn or block.session.rollout_id != rollout_id:
                continue
            if cutoff is None:
                eligible = [*block.items, *block.reasoning_summary_items]
            else:
                eligible = ranked.causal_items(block, cutoff)
            for item in eligible:
                unique.setdefault(message_key(rollout_id, item), (rollout_id, item))
    return sorted(
        unique.values(),
        key=lambda pair: (
            pair[0],
            pair[1].source_ordinal if pair[1].source_ordinal is not None else 2**63,
            pair[1].timestamp or "",
            pair[1].turn_number,
            pair[1].role,
        ),
    )


def serialize_messages(messages: Sequence[tuple[str, Any]]) -> str:
    """Exact stable proxy framing: one role/timestamp/text record per normalized item."""
    return "".join(
        f"<{item.role} timestamp={item.timestamp or 'unknown'}>\n{item.text}\n</{item.role}>\n"
        for _rollout_id, item in messages
    )


def count_tokens(tokenizer: Any, messages: Sequence[tuple[str, Any]]) -> int:
    if not messages:
        return 0
    return len(tokenizer.encode(serialize_messages(messages), add_special_tokens=False).ids)


def extract_tool_output_text(value: Any) -> tuple[str, int]:
    """Keep plain strings and explicit text blocks; count and discard multimodal blocks."""
    text_parts: list[str] = []
    omitted_multimodal = 0

    def visit(node: Any) -> None:
        nonlocal omitted_multimodal
        if isinstance(node, str):
            text_parts.append(node)
        elif isinstance(node, list):
            for child in node:
                visit(child)
        elif isinstance(node, dict):
            block_type = str(node.get("type") or "").casefold()
            if block_type in {"input_text", "output_text", "text"}:
                text = node.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
            elif "image" in block_type or "audio" in block_type or "video" in block_type or "image_url" in node:
                omitted_multimodal += 1
            elif isinstance(node.get("content"), (list, str)):
                visit(node["content"])

    visit(value)
    return "\n".join(part for part in text_parts if part), omitted_multimodal


def index_raw_tool_output_token_counts(
    blocks_by_rollout: dict[str, list[Any]], tokenizer: Any,
) -> dict[tuple[str, int], list[dict[str, Any]]]:
    """Tokenize tool-output events in one streaming pass per rollout, retaining no output text."""
    index: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for rollout_id, blocks in blocks_by_rollout.items():
        if not blocks:
            continue
        source_path = getattr(blocks[0].session, "source_path", None)
        if not source_path:
            continue
        path = Path(source_path)
        try:
            handle = path.open("r", encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"Rollout log unavailable while counting tool outputs: {rollout_id}") from exc
        turn_number = 0
        with handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
                if row.get("type") == "event_msg" and payload.get("type") == "task_started":
                    turn_number += 1
                    continue
                if row.get("type") != "response_item" or payload.get("type") not in {
                    "function_call_output", "custom_tool_call_output",
                }:
                    continue
                ordinal = row.get("ordinal")
                raw_output = payload.get("output")
                if not isinstance(ordinal, int) or raw_output is None:
                    continue
                timestamp = str(row.get("timestamp")) if row.get("timestamp") else None
                text_value, omitted_multimodal = extract_tool_output_text(raw_output)
                if text_value:
                    item = SimpleNamespace(
                        source_ordinal=ordinal, timestamp=timestamp, turn_number=turn_number or 1,
                        role="tool_output", text=text_value,
                    )
                    count = count_tokens(tokenizer, [(rollout_id, item)])
                else:
                    count = 0
                index.setdefault((rollout_id, turn_number or 1), []).append({
                    "ordinal": ordinal,
                    "timestamp": timestamp,
                    "tokens": count,
                    "omitted_multimodal_blocks": omitted_multimodal,
                })
    return index


def raw_tool_output_counts(
    coordinates: Iterable[tuple[str, int]],
    index: dict[tuple[str, int], list[dict[str, Any]]],
    cutoff: datetime | None = None,
    exact_ordinals: set[tuple[str, int]] | None = None,
) -> tuple[int, int, int]:
    selected = set(coordinates)
    count = token_count = omitted_multimodal = 0
    for rollout_id, turn in selected:
        for item in index.get((rollout_id, turn), []):
            if exact_ordinals is not None and (rollout_id, item["ordinal"]) not in exact_ordinals:
                continue
            parsed = alignment.parse_iso_timestamp(item["timestamp"])
            if cutoff is not None and (parsed is None or parsed >= cutoff + timedelta(minutes=1)):
                continue
            count += 1
            token_count += int(item["tokens"])
            omitted_multimodal += int(item["omitted_multimodal_blocks"])
    return count, token_count, omitted_multimodal


def _coordinates(value: Any) -> set[tuple[str, int]]:
    if not isinstance(value, list):
        raise ValueError("Coordinate artifact field must be a list")
    return {(str(pair[0]), int(pair[1])) for pair in value}


def _gold_evidence(gold: dict[str, Any]) -> set[tuple[str, int]]:
    return {
        (str(ref["rollout_id"]), int(ref["turn"]))
        for ref in gold["adjudication"]["evidence_refs"]
    }


def validate_artifacts(
    gold_rows: Sequence[dict[str, Any]],
    window_payload: dict[str, Any],
    ranked_payload: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    gold_by_id = {row["decision"]["id"]: row for row in gold_rows}
    window_by_id = {row["decision_id"]: row for row in window_payload.get("rows", [])}
    ranked_by_id = {row["decision_id"]: row for row in ranked_payload.get("rows", [])}
    if set(gold_by_id) != set(window_by_id) or set(gold_by_id) != set(ranked_by_id):
        raise ValueError("Gold, window, and ranked artifact decision IDs must match exactly")
    for decision_id, gold in gold_by_id.items():
        expected = _gold_evidence(gold)
        window_evidence = _coordinates(window_by_id[decision_id].get("evidence_turns"))
        ranked_evidence = _coordinates(ranked_by_id[decision_id].get("evidence_turns"))
        if expected != window_evidence or expected != ranked_evidence:
            raise ValueError(f"Evidence-ref coordinates mismatch for {decision_id}")
    return window_by_id, ranked_by_id


def referenced_rollout_ids(
    gold_rows: Sequence[dict[str, Any]],
    window_payload: dict[str, Any],
    ranked_payload: dict[str, Any],
) -> set[str]:
    """Return every rollout needed by selected sessions, candidate stages, or gold refs."""
    window_by_id, ranked_by_id = validate_artifacts(gold_rows, window_payload, ranked_payload)
    result: set[str] = set()
    for gold in gold_rows:
        result.add(str(gold["selected_candidate"]["rollout_id"]))
        result.update(rollout_id for rollout_id, _turn in _gold_evidence(gold))
        for ref in gold.get("adjudication", {}).get("minimal_useful_refs", []) or []:
            result.add(str(ref["rollout_id"]))
        decision_id = gold["decision"]["id"]
        window_row = window_by_id[decision_id]
        raw_source_scope = window_row.get("source_scope_turns", [])
        if isinstance(raw_source_scope, list):
            result.update(rollout_id for rollout_id, _turn in _coordinates(raw_source_scope))
        for strategy in window_row.get("strategies", {}).values():
            result.update(
                rollout_id for rollout_id, _turn in
                _coordinates(strategy.get("coordinates", []))
            )
        for strategy in ranked_by_id[decision_id].get("strategies", {}).values():
            result.update(
                rollout_id for rollout_id, _turn in
                _coordinates(strategy.get("coordinates", []))
            )
    return result


def load_referenced_rollouts(
    codex_home: Path,
    required_ids: set[str],
    selected_rollout_ids: set[str] | None = None,
) -> dict[str, list[Any]]:
    blocks_by_rollout: dict[str, list[Any]] = {}
    all_metas: list[tuple[Path, Any]] = []
    for path in alignment.iter_rollout_paths(codex_home):
        meta = alignment.read_session_meta(path)
        if meta:
            all_metas.append((path, meta))
    metas_by_id = {meta.rollout_id: meta for _path, meta in all_metas}
    missing = required_ids - set(metas_by_id)
    if missing:
        raise ValueError(f"Referenced rollout logs unavailable: {', '.join(sorted(missing))}")
    selected_ids = selected_rollout_ids or set()
    missing_selected = selected_ids - set(metas_by_id)
    if missing_selected:
        raise ValueError(f"Selected rollout logs unavailable: {', '.join(sorted(missing_selected))}")
    logical_ids = {metas_by_id[rollout_id].session_id for rollout_id in selected_ids}
    parent_task_ids: set[str] = set()
    for selected_id in selected_ids:
        child_meta = metas_by_id[selected_id]
        for _depth in range(window_eval.MAX_PARENT_DEPTH):
            parent_task_id = child_meta.parent_thread_id
            if not parent_task_id or parent_task_id in parent_task_ids:
                break
            parent_task_ids.add(parent_task_id)
            parent_meta = next(
                (meta for _path, meta in all_metas if meta.session_id == parent_task_id),
                None,
            )
            if parent_meta is None:
                break
            child_meta = parent_meta
    logical_ids.update(parent_task_ids)
    loaded_metas = [
        meta for _path, meta in all_metas
        if meta.rollout_id in required_ids or meta.session_id in logical_ids
    ]
    alignment.validate_unique_rollouts(loaded_metas)
    for path, meta in all_metas:
        if meta.rollout_id in required_ids or meta.session_id in logical_ids:
            blocks_by_rollout[meta.rollout_id] = alignment.parse_rollout(path, meta)
    return blocks_by_rollout


def percentile95(values: Sequence[int]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    # Nearest-rank definition; a one-row cohort has that row as its p95.
    return float(ordered[max(0, int(0.95 * len(ordered) + 0.999999) - 1)])


def summarize_stage(rows: Sequence[dict[str, Any]], stage: str, previous: str | None) -> dict[str, Any]:
    totals = [int(row["stages"][stage]["tokens"]) for row in rows]
    total = sum(totals)
    prior_total = sum(int(row["stages"][previous]["tokens"]) for row in rows) if previous else None
    return {
        "rows": len(totals),
        "total_tokens": total,
        "median_tokens": statistics.median(totals) if totals else 0,
        "p95_tokens": percentile95(totals),
        "reduction_vs_previous": (1 - total / prior_total) if prior_total else None,
    }


def attach_tokenizer_fingerprint(result: dict[str, Any], tokenizer_path: Path) -> None:
    result["metadata"]["tokenizer_sha256"] = tokenizer_sha256(tokenizer_path)
    result["metadata"]["tokenizer_label"] = "local tokenizer.json"


STAGES = (
    "full_logical_session",
    "causal_logical_session",
    "full_originating_rollout",
    "causal_originating_rollout",
    "source_lineage_scope_72h",
    "lineage_backward_20",
    "lexical_top_3",
    "minimal_useful_content",
)


def minimal_useful_messages(
    gold: dict[str, Any],
    blocks_by_rollout: dict[str, list[Any]],
    cutoff: datetime,
    raw_output_index: dict[tuple[str, int], list[dict[str, Any]]] | None = None,
) -> tuple[set[tuple[str, int]], list[tuple[str, Any]], str]:
    """Resolve message ordinal refs when adjudicated; otherwise return cited-turn proxy."""
    adjudication = gold.get("adjudication", {})
    refs = adjudication.get("minimal_useful_refs")
    if refs:
        wanted: set[tuple[str, int]] = set()
        for ref in refs:
            rollout_id = str(ref["rollout_id"])
            ordinals = ref.get("ordinals")
            if ordinals is None:
                ordinal = ref.get("ordinal", ref.get("source_ordinal"))
                ordinals = [] if ordinal is None else [ordinal]
            wanted.update((rollout_id, int(ordinal)) for ordinal in ordinals)
        found: dict[tuple[str, int], tuple[str, Any]] = {}
        for rollout_id, blocks in blocks_by_rollout.items():
            for block in blocks:
                if block.session.rollout_id != rollout_id:
                    continue
                for item in ranked.causal_items(block, cutoff):
                    if item.source_ordinal is not None:
                        key = (rollout_id, int(item.source_ordinal))
                        if key in wanted:
                            found[key] = (rollout_id, item)
        raw_found = {
            (rollout_id, int(item["ordinal"])): (rollout_id, turn)
            for (rollout_id, turn), items in (raw_output_index or {}).items()
            for item in items
            if (rollout_id, int(item["ordinal"])) in wanted
            and alignment.parse_iso_timestamp(item.get("timestamp")) is not None
            and alignment.parse_iso_timestamp(item.get("timestamp")) < cutoff + timedelta(minutes=1)
        }
        missing = wanted - set(found) - set(raw_found)
        if missing:
            raise ValueError(f"Unresolved minimal useful message ordinals for {gold['decision']['id']}")
        coords = {(rollout_id, item.turn_number) for rollout_id, item in found.values()}
        coords.update(raw_found.values())
        messages = sorted(
            found.values(),
            key=lambda pair: (pair[0], pair[1].source_ordinal, pair[1].timestamp or ""),
        )
        return coords, messages, "adjudicated_message_ordinals"
    evidence = _gold_evidence(gold)
    return (
        evidence,
        collect_items(evidence, blocks_by_rollout, cutoff),
        "cited_evidence_turns_approximation",
    )


def minimal_useful_ordinals(gold: dict[str, Any]) -> set[tuple[str, int]] | None:
    refs = gold.get("adjudication", {}).get("minimal_useful_refs") or []
    if not refs:
        return None
    result: set[tuple[str, int]] = set()
    for ref in refs:
        rollout_id = str(ref["rollout_id"])
        ordinals = ref.get("ordinals")
        if ordinals is None:
            ordinal = ref.get("ordinal", ref.get("source_ordinal"))
            ordinals = [] if ordinal is None else [ordinal]
        result.update((rollout_id, int(ordinal)) for ordinal in ordinals)
    return result


def evaluate_rows(
    gold_rows: Sequence[dict[str, Any]],
    window_payload: dict[str, Any],
    ranked_payload: dict[str, Any],
    blocks_by_rollout: dict[str, list[Any]],
    tokenizer: Any,
    *,
    metas: Sequence[Any] | None = None,
) -> dict[str, Any]:
    window_by_id, ranked_by_id = validate_artifacts(gold_rows, window_payload, ranked_payload)
    required_ids = referenced_rollout_ids(gold_rows, window_payload, ranked_payload)
    missing_ids = required_ids - set(blocks_by_rollout)
    if missing_ids:
        raise ValueError(f"Referenced rollout logs unavailable: {', '.join(sorted(missing_ids))}")
    available_metas = list(metas) if metas is not None else list({
        block.session.rollout_id: block.session
        for blocks in blocks_by_rollout.values()
        for block in blocks
    }.values())
    raw_output_index = index_raw_tool_output_token_counts(blocks_by_rollout, tokenizer)
    output_rows: list[dict[str, Any]] = []
    source_scope_parity_checked = 0
    source_scope_parity_matches = 0
    for gold in gold_rows:
        decision_id = gold["decision"]["id"]
        selected_rollout = str(gold["selected_candidate"]["rollout_id"])
        cutoff = alignment.parse_iso_timestamp(gold["decision"]["timestamp"])
        if cutoff is None:
            raise ValueError(f"Invalid decision timestamp for {decision_id}")
        if selected_rollout not in blocks_by_rollout:
            raise ValueError(f"Selected rollout unavailable for {decision_id}")
        selected_blocks = blocks_by_rollout[selected_rollout]
        logical_session_ids = {
            str(block.session.session_id)
            for block in selected_blocks
            if getattr(block.session, "session_id", None)
        }
        if len(logical_session_ids) != 1:
            raise ValueError(f"Selected rollout must have one logical session ID for {decision_id}")
        logical_session_id = next(iter(logical_session_ids))
        full_logical = {
            (rollout_id, block.turn_number)
            for rollout_id, blocks in blocks_by_rollout.items()
            for block in blocks
            if str(getattr(block.session, "session_id", "")) == logical_session_id
        }
        causal_logical = {
            (rollout_id, block.turn_number)
            for rollout_id, blocks in blocks_by_rollout.items()
            for block in blocks
            if str(getattr(block.session, "session_id", "")) == logical_session_id
            and ranked.causal_items(block, cutoff)
        }
        full_origin = {
            (selected_rollout, block.turn_number)
            for block in selected_blocks
        }
        causal_origin = {
            (selected_rollout, block.turn_number)
            for block in blocks_by_rollout[selected_rollout]
            if ranked.causal_items(block, cutoff)
        }
        raw_source_scope = window_by_id[decision_id]["source_scope_turns"]
        if isinstance(raw_source_scope, list):
            source_scope = _coordinates(raw_source_scope)
        else:
            source_scope = window_eval.source_scope_coordinates(
                selected_rollout_id=selected_rollout,
                decision_time=cutoff,
                metas=available_metas,
                blocks_by_rollout=blocks_by_rollout,
            )
            source_scope_parity_checked += 1
            if int(raw_source_scope) == len(source_scope):
                source_scope_parity_matches += 1
        envelope = _coordinates(
            window_by_id[decision_id]["strategies"]["lineage_backward_20"]["coordinates"]
        )
        ranked_stages = ranked_by_id[decision_id]["strategies"]
        lexical_top_3 = _coordinates(ranked_stages["lexical_top_3"]["coordinates"])
        evidence = _gold_evidence(gold)
        minimal_coords, minimal_messages, minimal_method = minimal_useful_messages(
            gold, blocks_by_rollout, cutoff, raw_output_index
        )
        exact_minimal_ordinals = minimal_useful_ordinals(gold)
        stage_coordinates = {
            "full_logical_session": full_logical,
            "causal_logical_session": causal_logical,
            "full_originating_rollout": full_origin,
            "causal_originating_rollout": causal_origin,
            "source_lineage_scope_72h": source_scope,
            "lineage_backward_20": envelope,
            "lexical_top_3": lexical_top_3,
            "minimal_useful_content": minimal_coords,
        }
        stage_payloads: dict[str, dict[str, Any]] = {}
        stage_messages: dict[str, list[tuple[str, Any]]] = {}
        for stage, coords in stage_coordinates.items():
            messages = (
                minimal_messages
                if stage == "minimal_useful_content"
                else collect_items(coords, blocks_by_rollout)
            )
            if stage in {"causal_logical_session", "causal_originating_rollout", "source_lineage_scope_72h", "lineage_backward_20", "lexical_top_3"}:
                # Candidate payloads use the ranked evaluator's causal-minute policy.
                messages = collect_items(coords, blocks_by_rollout, cutoff)
            causal_stage = stage not in {"full_logical_session", "full_originating_rollout"}
            raw_count, raw_tokens, omitted_multimodal = raw_tool_output_counts(
                coords,
                raw_output_index,
                cutoff if causal_stage else None,
                exact_minimal_ordinals if stage == "minimal_useful_content" else None,
            )
            normalized_tokens = count_tokens(tokenizer, messages)
            stage_payloads[stage] = {
                "coordinates": [list(coord) for coord in sorted(coords)],
                "message_count": len(messages),
                "tokens": normalized_tokens,
                "raw_tool_output_message_count": raw_count,
                "raw_tool_output_tokens": raw_tokens,
                "omitted_multimodal_block_count": omitted_multimodal,
                "tokens_including_raw_tool_outputs_proxy": normalized_tokens + raw_tokens,
            }
            if stage == "minimal_useful_content":
                stage_payloads[stage]["method"] = minimal_method
            stage_messages[stage] = messages
        unique_messages: dict[tuple[Any, ...], tuple[str, Any]] = {}
        for messages in stage_messages.values():
            for rollout_id, item in messages:
                unique_messages.setdefault(message_key(rollout_id, item), (rollout_id, item))
        unique_payload_messages = sorted(
            unique_messages.values(),
            key=lambda pair: (
                pair[0], pair[1].source_ordinal if pair[1].source_ordinal is not None else 2**63,
                pair[1].timestamp or "", pair[1].turn_number, pair[1].role,
            ),
        )
        unique_tokens = count_tokens(tokenizer, unique_payload_messages)
        stage_token_sum = sum(stage["tokens_including_raw_tool_outputs_proxy"] for stage in stage_payloads.values())
        alternative_coordinates = set().union(*stage_coordinates.values())
        raw_unique_count, raw_unique_tokens, raw_unique_omitted = raw_tool_output_counts(
            alternative_coordinates, raw_output_index,
        )
        output_rows.append({
            "decision_id": decision_id,
            "stages": stage_payloads,
            "cumulative_payload": {
                "unique_normalized_message_count": len(unique_payload_messages),
                "unique_normalized_tokens": unique_tokens,
                "sum_of_alternative_stage_tokens_proxy": stage_token_sum,
                "repeated_normalized_context_proxy": max(0, sum(
                    stage["tokens"] for stage in stage_payloads.values()
                ) - unique_tokens),
                "unique_across_alternative_stages_raw_tool_output_message_count": raw_unique_count,
                "unique_across_alternative_stages_raw_tool_output_tokens": raw_unique_tokens,
                "unique_across_alternative_stages_omitted_multimodal_blocks": raw_unique_omitted,
            },
        })
    summaries: dict[str, Any] = {}
    previous = None
    for stage in STAGES:
        summaries[stage] = summarize_stage(output_rows, stage, previous)
        previous = stage
    unique_totals = [row["cumulative_payload"]["unique_normalized_tokens"] for row in output_rows]
    stage_sums = [row["cumulative_payload"]["sum_of_alternative_stage_tokens_proxy"] for row in output_rows]
    resent_proxy = [row["cumulative_payload"]["repeated_normalized_context_proxy"] for row in output_rows]
    raw_totals_by_stage = {
        stage: [int(row["stages"][stage]["raw_tool_output_tokens"]) for row in output_rows]
        for stage in STAGES
    }
    omitted_by_stage = {
        stage: sum(int(row["stages"][stage]["omitted_multimodal_block_count"]) for row in output_rows)
        for stage in STAGES
    }
    return {
        "schema_version": "decision-token-efficiency/1.0",
        "metadata": {
            "tokenizer_sha256": "provided-by-cli",
            "serialization": "<role timestamp=ISO-or-unknown>\\ntext\\n</role>\\n; all messages encoded together; no special tokens",
            "causal_cutoff": "message timestamp strictly before decision timestamp plus one minute; decision records have minute precision",
            "full_logical_session": "every normalized turn in every rollout sharing the selected rollout's logical session_id, including continuations and messages after the decision cutoff",
            "causal_logical_session": "the full selected logical session filtered with the stated decision-minute cutoff",
            "full_originating_rollout": "every normalized turn in the selected rollout file, including messages after the decision cutoff; retained as a single-rollout comparison",
            "source_lineage_scope_72h": "coordinates recomputed with evaluate_window_strategies.source_scope_coordinates from the selected rollout and up to two available parent tasks; the artifact's integer count is used only for parity reporting",
            "full_parent_child_lineage_available": False,
            "lineage_limitation": "Existing artifacts contain bounded source-scope coordinates, not complete unbounded parent-child session history.",
            "minimal_useful_content": "Uses adjudicated minimal_useful_refs message ordinals when present; otherwise counts all normalized causal messages in cited evidence turns as an explicitly labeled approximation.",
            "readable_reasoning_summaries": "Included when present in candidate payload; encrypted reasoning is excluded and unreadable.",
            "tool_outputs": "Counted separately from normalized items by streaming function_call_output/custom_tool_call_output payloads. Plain strings and explicit input_text/output_text/text blocks are tokenized; output text is discarded after standalone local-tokenizer counting. Structured non-text multimodal blocks are omitted and counted. Opaque image/audio/video encodings inside text strings are not reliably distinguishable and may be counted. Counts are additive per-message text-channel proxies and do not alter ranking text.",
            "billing_caveat": "Local tokenizer proxy counts for this explicit serialization; not provider billing tokens, and excludes hidden reasoning, multimodal payloads, provider-specific framing, and per-message tokenizer boundary interactions.",
            "alternative_stage_overlap_diagnostic_caveat": "Stages are alternative scopes, not a sequential prompt plan. Their summed token count is hypothetical; repeated normalized context is an overlap diagnostic, not actual cumulative payload cost. Raw tool-output token counts are standalone per-message proxies.",
            "tokenizer_label": "local tokenizer.json",
            "source_lineage_scope_artifact_parity": {
                "rows_checked": source_scope_parity_checked,
                "rows_matching": source_scope_parity_matches,
            },
        },
        "summary": summaries,
        "alternative_stage_overlap_diagnostic_summary": {
            "rows": len(output_rows),
            "unique_normalized_tokens_total": sum(unique_totals),
            "unique_normalized_tokens_median": statistics.median(unique_totals) if unique_totals else 0,
            "unique_normalized_tokens_p95": percentile95(unique_totals),
            "sum_of_alternative_stage_tokens_proxy_total": sum(stage_sums),
            "repeated_normalized_context_proxy_total": sum(resent_proxy),
        },
        "raw_tool_output_summary": {
            stage: {
                "tokens_total": sum(values),
                "tokens_median": statistics.median(values) if values else 0,
                "tokens_p95": percentile95(values),
            }
            for stage, values in raw_totals_by_stage.items()
        },
        "omitted_multimodal_block_summary": omitted_by_stage,
        "rows": output_rows,
    }


def _read_gold(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_files(
    *, gold_path: Path, window_path: Path, ranked_path: Path, repo: Path,
    codex_home: Path, tokenizer_path: Path,
) -> dict[str, Any]:
    tokenizer = load_tokenizer(tokenizer_path)
    gold_rows = _read_gold(gold_path)
    window_payload = _read_json(window_path)
    ranked_payload = _read_json(ranked_path)
    required_ids = referenced_rollout_ids(gold_rows, window_payload, ranked_payload)
    selected_ids = {str(row["selected_candidate"]["rollout_id"]) for row in gold_rows}
    blocks_by_rollout = load_referenced_rollouts(codex_home, required_ids, selected_ids)
    metas_by_rollout = {
        block.session.rollout_id: block.session
        for blocks in blocks_by_rollout.values()
        for block in blocks
    }
    result = evaluate_rows(
        gold_rows, window_payload, ranked_payload, blocks_by_rollout, tokenizer,
        metas=list(metas_by_rollout.values()),
    )
    attach_tokenizer_fingerprint(result, tokenizer_path)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--window-results", type=Path, required=True)
    parser.add_argument("--ranked-results", type=Path, required=True)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path, required=True)
    parser.add_argument("--tokenizer-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate_files(
        gold_path=args.gold.resolve(), window_path=args.window_results.resolve(),
        ranked_path=args.ranked_results.resolve(), repo=args.repo.resolve(),
        codex_home=args.codex_home.resolve(), tokenizer_path=args.tokenizer_json.resolve(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

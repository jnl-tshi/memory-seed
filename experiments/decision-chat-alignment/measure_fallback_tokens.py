"""Count local-tokenizer payload proxies for development nearby-session stages.

`conditional_hybrid_oracle` uses gold only to calculate an upper-bound cost for
expanding when the baseline 20-turn envelope misses evidence. It is not a
deployable answer-sufficiency trigger. Raw text-channel output counts may
include opaque encoded payloads and are reported separately.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import statistics
import sys
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, BASE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


token_eval = load_module("token_eval_fallback", "evaluate_token_efficiency.py")
alignment = token_eval.alignment


def coords(value: list[list[Any]]) -> set[tuple[str, int]]:
    return {(str(rollout_id), int(turn)) for rollout_id, turn in value}


def conditional_oracle_scope(
    baseline: set[tuple[str, int]], fallback: set[tuple[str, int]],
    evidence: set[tuple[str, int]], label: str,
) -> set[tuple[str, int]]:
    if label == "verified_source" and evidence and not evidence <= baseline:
        return baseline | fallback
    return baseline


def evaluate(
    gold_rows: list[dict[str, Any]], window_rows: dict[str, dict[str, Any]],
    fallback_rows: dict[str, dict[str, Any]], blocks: dict[str, list[Any]],
    tokenizer: Any,
) -> dict[str, Any]:
    if set(window_rows) != set(fallback_rows) or set(window_rows) != {row["decision"]["id"] for row in gold_rows}:
        raise ValueError("Gold, window, and fallback cohorts must match")
    raw_index = token_eval.index_raw_tool_output_token_counts(blocks, tokenizer)
    stages = ("all_neighbor_1", "all_neighbor_10", "hybrid_recent1_text1",
              "hybrid_ranked_10", "conditional_hybrid_oracle")
    output_rows: list[dict[str, Any]] = []
    for gold in gold_rows:
        decision_id = gold["decision"]["id"]
        cutoff = alignment.parse_iso_timestamp(gold["decision"]["timestamp"])
        if cutoff is None:
            raise ValueError(f"Invalid decision timestamp: {decision_id}")
        window = window_rows[decision_id]
        fallback = fallback_rows[decision_id]
        baseline = coords(window["strategies"]["lineage_backward_20"]["coordinates"])
        evidence = token_eval._gold_evidence(gold)
        selected = {
            stage: coords(fallback["stages"][stage]["coordinates"])
            for stage in stages if stage != "conditional_hybrid_oracle"
        }
        selected["conditional_hybrid_oracle"] = conditional_oracle_scope(
            baseline, selected["hybrid_recent1_text1"], evidence,
            gold["adjudication"]["label"],
        )
        stage_counts = {}
        for stage, selected_coords in selected.items():
            messages = token_eval.collect_items(selected_coords, blocks, cutoff)
            normalized = token_eval.count_tokens(tokenizer, messages)
            raw_count, raw_tokens, omitted = token_eval.raw_tool_output_counts(selected_coords, raw_index, cutoff)
            stage_counts[stage] = {
                "turns": len(selected_coords),
                "normalized_tokens": normalized,
                "raw_tool_output_count": raw_count,
                "raw_tool_output_tokens": raw_tokens,
                "omitted_structured_multimodal_blocks": omitted,
                "combined_text_channel_proxy": normalized + raw_tokens,
            }
        output_rows.append({"decision_id": decision_id, "gold_label": gold["adjudication"]["label"], "stages": stage_counts})
    summary = {}
    for stage in stages:
        counts = [row["stages"][stage] for row in output_rows]
        summary[stage] = {
            "rows": len(counts),
            "turns_total": sum(item["turns"] for item in counts),
            "normalized_tokens_total": sum(item["normalized_tokens"] for item in counts),
            "raw_tool_output_tokens_total": sum(item["raw_tool_output_tokens"] for item in counts),
            "combined_text_channel_proxy_total": sum(item["combined_text_channel_proxy"] for item in counts),
            "normalized_tokens_median": statistics.median(item["normalized_tokens"] for item in counts),
        }
    return {"schema_version": "decision-fallback-token-proxy/1.0",
            "metadata": {"tokenizer_label": "caller-supplied local tokenizer.json",
                         "conditional_stage": "gold-oracle upper-bound cost, not an operational sufficiency trigger",
                         "raw_output_caveat": "opaque encodings inside text strings may be counted; structured multimodal blocks are excluded",
                         "cohort_ids_sha256": hashlib.sha256("\n".join(sorted(window_rows)).encode()).hexdigest()},
            "summary": summary, "rows": output_rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--window-results", type=Path, required=True)
    parser.add_argument("--fallback-results", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path, required=True)
    parser.add_argument("--tokenizer-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    gold = [json.loads(line) for line in args.gold.read_text(encoding="utf-8").splitlines() if line.strip()]
    windows = json.loads(args.window_results.read_text(encoding="utf-8"))
    fallback = json.loads(args.fallback_results.read_text(encoding="utf-8"))
    window_rows = {row["decision_id"]: row for row in windows["rows"]}
    fallback_rows = {row["decision_id"]: row for row in fallback["rows"]}
    required_ids = {
        str(coord[0]) for row in fallback_rows.values()
        for stage in row["stages"].values()
        for coord in stage["coordinates"]
    }
    required_ids.update(
        str(coord[0]) for row in window_rows.values()
        for coord in row["strategies"]["lineage_backward_20"]["coordinates"]
    )
    blocks = token_eval.load_referenced_rollouts(args.codex_home, required_ids)
    tokenizer = token_eval.load_tokenizer(args.tokenizer_json)
    result = evaluate(gold, window_rows, fallback_rows, blocks, tokenizer)
    result["metadata"]["tokenizer_sha256"] = token_eval.tokenizer_sha256(args.tokenizer_json)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

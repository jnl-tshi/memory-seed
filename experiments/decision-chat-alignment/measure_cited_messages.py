"""Count exact cited raw-message payloads for the strict 100-decision cohort.

This is a lower-bound provenance proxy, not all context needed by a curator or
Codex billing usage. Only cited ordinals are read from tool-output payloads;
no transcript text or absolute log path is written to the artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any


BASE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("token_eval_citations", BASE / "evaluate_token_efficiency.py")
assert SPEC and SPEC.loader
tokens = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = tokens
SPEC.loader.exec_module(tokens)
alignment = tokens.alignment


def wanted_refs(row: dict[str, Any]) -> set[tuple[str, int]]:
    return {
        (str(ref["rollout_id"]), int(ordinal))
        for ref in row["adjudication"].get("evidence_refs", [])
        for ordinal in ref.get("ordinals", [])
    }


def validate_ids(rows: list[dict[str, Any]], excluded: set[str]) -> list[str]:
    ids = [str(row["decision"]["id"]) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate decision IDs across gold files")
    missing = excluded - set(ids)
    if missing:
        raise ValueError("Documentation controls absent from supplied gold files")
    return sorted(set(ids) - excluded)


def source_paths(codex_home: Path, required_ids: set[str]) -> dict[str, Path]:
    found: dict[str, Path] = {}
    for path in alignment.iter_rollout_paths(codex_home):
        meta = alignment.read_session_meta(path)
        if meta and meta.rollout_id in required_ids:
            if meta.rollout_id in found:
                raise ValueError("Duplicate cited rollout ID")
            found[meta.rollout_id] = path
    if required_ids - set(found):
        raise ValueError("Cited rollout unavailable")
    return found


def raw_cited_items(
    paths: dict[str, Path], wanted: set[tuple[str, int]],
) -> dict[tuple[str, int], dict[str, Any]]:
    found: dict[tuple[str, int], dict[str, Any]] = {}
    for rollout_id, path in paths.items():
        ordinals = {ordinal for source_id, ordinal in wanted if source_id == rollout_id}
        if not ordinals:
            continue
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                ordinal = row.get("ordinal")
                if ordinal not in ordinals:
                    continue
                found[(rollout_id, int(ordinal))] = row
    return found


def cited_raw_text(row: dict[str, Any]) -> tuple[str, str, bool, int]:
    payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
    kind = payload.get("type")
    is_tool_output = row.get("type") == "response_item" and kind in {
        "function_call_output", "custom_tool_call_output",
    }
    if is_tool_output:
        value = payload.get("output")
        role = "tool_output"
    elif row.get("type") == "event_msg" and kind == "item_completed":
        item = payload.get("item") if isinstance(payload.get("item"), dict) else {}
        value = item.get("content")
        role = "assistant" if item.get("type") == "AgentMessage" else "event"
    else:
        value = payload.get("content", payload.get("text", payload.get("arguments")))
        role = str(payload.get("role", "event"))
    text_value, omitted = tokens.extract_tool_output_text(value)
    return text_value, role, is_tool_output, omitted


def evaluate(
    rows: list[dict[str, Any]], excluded: set[str], paths: dict[str, Path], tokenizer: Any,
) -> dict[str, Any]:
    strict_ids = validate_ids(rows, excluded)
    all_wanted = set().union(*(wanted_refs(row) for row in rows))
    raw = raw_cited_items(paths, all_wanted)
    blocks = {
        rollout_id: alignment.parse_rollout(path, alignment.read_session_meta(path))
        for rollout_id, path in paths.items()
    }
    output_rows: list[dict[str, Any]] = []
    for row in rows:
        decision_id = str(row["decision"]["id"])
        cutoff = alignment.parse_iso_timestamp(row["decision"]["timestamp"])
        if cutoff is None:
            raise ValueError(f"Invalid timestamp for {decision_id}")
        wanted = wanted_refs(row)
        found_messages: dict[tuple[str, int], tuple[str, Any]] = {}
        for rollout_id, session_blocks in blocks.items():
            for block in session_blocks:
                for item in tokens.ranked.causal_items(block, cutoff):
                    if item.source_ordinal is None:
                        continue
                    key = (rollout_id, int(item.source_ordinal))
                    if key in wanted:
                        found_messages[key] = (rollout_id, item)
        normalized = tokens.count_tokens(tokenizer, list(found_messages.values()))
        raw_count = raw_tokens = other_count = other_tokens = omitted = 0
        found_raw: set[tuple[str, int]] = set()
        for key in wanted - set(found_messages):
            if key not in raw:
                continue
            raw_row = raw[key]
            timestamp = raw_row.get("timestamp")
            parsed = alignment.parse_iso_timestamp(timestamp)
            if parsed is None or parsed >= cutoff + timedelta(minutes=1):
                continue
            text_value, role, is_tool_output, omitted_blocks = cited_raw_text(raw_row)
            tool_item = SimpleNamespace(
                role=role, text=text_value, source_ordinal=key[1], timestamp=timestamp,
            )
            count = 0
            if text_value:
                count = tokens.count_tokens(tokenizer, [(key[0], tool_item)])
            if is_tool_output:
                raw_count += 1
                raw_tokens += count
            else:
                other_count += 1
                other_tokens += count
            omitted += omitted_blocks
            found_raw.add(key)
        if wanted - set(found_messages) - found_raw:
            raise ValueError(f"Cited message ordinal unavailable before cutoff: {decision_id}")
        output_rows.append({
            "decision_id": decision_id,
            "strict_decision": decision_id in strict_ids,
            "gold_label": row["adjudication"]["label"],
            "cited_ordinals": len(wanted),
            "normalized_message_tokens": normalized,
            "raw_tool_output_count": raw_count,
            "raw_tool_output_tokens": raw_tokens,
            "raw_other_event_count": other_count,
            "raw_other_event_tokens": other_tokens,
            "omitted_structured_multimodal_blocks": omitted,
            "combined_text_channel_proxy": normalized + raw_tokens + other_tokens,
        })
    strict = [row for row in output_rows if row["strict_decision"]]
    summary = {
        "all_records": len(output_rows),
        "strict_decisions": len(strict),
        "strict_labels": dict(sorted(Counter(row["gold_label"] for row in strict).items())),
        "strict_cited_ordinals": sum(row["cited_ordinals"] for row in strict),
        "strict_normalized_message_tokens": sum(row["normalized_message_tokens"] for row in strict),
        "strict_raw_tool_output_tokens": sum(row["raw_tool_output_tokens"] for row in strict),
        "strict_raw_other_event_tokens": sum(row["raw_other_event_tokens"] for row in strict),
        "strict_combined_text_channel_proxy": sum(row["combined_text_channel_proxy"] for row in strict),
    }
    return {
        "schema_version": "decision-cited-message-token-proxy/1.0",
        "metadata": {
            "method": "exact evidence_refs ordinals, lower bound rather than curator-sufficient context",
            "raw_output_caveat": "structured multimodal blocks excluded; opaque encodings inside text may inflate counts",
            "strict_ids_sha256": hashlib.sha256("\n".join(strict_ids).encode()).hexdigest(),
        },
        "summary": summary,
        "rows": sorted(output_rows, key=lambda row: row["decision_id"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gold", type=Path, nargs="+", required=True)
    parser.add_argument("--cohort-manifest", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path, required=True)
    parser.add_argument("--tokenizer-json", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = [
        json.loads(line)
        for path in args.gold
        for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    manifest = json.loads(args.cohort_manifest.read_text(encoding="utf-8"))
    excluded = set(manifest["metadata"]["known_documentation_records"])
    strict = validate_ids(rows, excluded)
    if len(strict) != int(manifest["metadata"]["strict_decision_total"]):
        raise ValueError("Gold files do not contain the frozen strict decision cohort")
    required = {rollout_id for row in rows for rollout_id, _ordinal in wanted_refs(row)}
    result = evaluate(rows, excluded, source_paths(args.codex_home, required), tokens.load_tokenizer(args.tokenizer_json))
    result["metadata"]["tokenizer_sha256"] = tokens.tokenizer_sha256(args.tokenizer_json)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Materialize a strategy result into an offline, self-contained packet."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping, Sequence

from contracts import canonical_json, fingerprint, load_json
from strategies import RESULT_SCHEMA


PACKET_SCHEMA = "context-packet.v1"


def materialize_packet(result: Mapping[str, Any], *, include_text: bool = True) -> dict[str, Any]:
    if result.get("schema") != RESULT_SCHEMA:
        raise ValueError(f"result schema must be {RESULT_SCHEMA!r}")
    items = []
    for evidence in result.get("evidence", []):
        item = {key: value for key, value in evidence.items() if key != "text"}
        if include_text:
            item["text"] = evidence.get("text", "")
        items.append(item)
    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "task_id": result.get("task_id"),
        "strategy_fingerprint": result.get("strategy_fingerprint"),
        "selected_adrs": result.get("selected_adrs", []),
        "selected_refs": result.get("selected_refs", []),
        "typed_edges": result.get("typed_edges", []),
        "lineage_edges": result.get("lineage_edges", []),
        "related_edges": result.get("related_edges", []),
        "evidence": items,
        "omissions": result.get("omissions", []),
        "absence": result.get("absence", []),
        "insufficient_evidence": bool(result.get("insufficient_evidence")),
        "token_proxy": int(result.get("token_proxy", 0)),
    }
    packet["fingerprint"] = fingerprint(packet)
    return packet


def packet_json(result: Mapping[str, Any], *, include_text: bool = True) -> str:
    return canonical_json(materialize_packet(result, include_text=include_text))


def attach_task_packets(
    task: Mapping[str, Any],
    *,
    retrieval_v1_result: Mapping[str, Any],
    candidate_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Attach both inline packet arms and their accounting to a task payload."""
    arms = {
        "retrieval-v1-packet": retrieval_v1_result,
        "adr-candidate-packet": candidate_result,
    }
    payload = dict(task)
    rendered = {arm: packet_json(result) for arm, result in arms.items()}
    payload["packets"] = rendered
    payload["included_refs_by_arm"] = {
        arm: sorted(
            set(map(str, result.get("selected_refs", [])))
            | {str(item["adr_id"]) for item in result.get("selected_adrs", []) if item.get("adr_id")}
        )
        for arm, result in arms.items()
    }
    payload["context_token_proxy_by_arm"] = {
        arm: max(1, (len(packet.encode("utf-8")) + 3) // 4)
        for arm, packet in rendered.items()
    }
    return payload


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Attach fixed offline packet arms to one task")
    parser.add_argument("--task", required=True)
    parser.add_argument("--retrieval-result", required=True)
    parser.add_argument("--candidate-result", required=True)
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    payload = attach_task_packets(
        load_json(args.task),
        retrieval_v1_result=load_json(args.retrieval_result),
        candidate_result=load_json(args.candidate_result),
    )
    rendered = canonical_json(payload) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8", newline="\n")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

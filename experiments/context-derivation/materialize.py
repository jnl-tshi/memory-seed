"""Materialize a strategy result into an offline, self-contained packet."""

from __future__ import annotations

from typing import Any, Mapping

from contracts import canonical_json, fingerprint
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

"""Offline-only sweep for tiered decision -> ADR -> Constitution context.

This is a measurement aid, not a retrieval implementation.  It ranks the
literal benchmark question with the production decision-level reader, then
compares bounded context allocations.  Top-K recall is recorded here only;
it is neither persisted in fixtures nor exposed by MCP.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import json
from itertools import product
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


SCHEMA = "strong-context-v2-offline-sweep.v1"
_HERE = Path(__file__).resolve().parent


def _load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, _HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


bridge = _load("strong_context_v2_sweep_bridge", "strong_context_fixture_v2.py")
resolver = _load("strong_context_v2_sweep_resolver", "strong_context_v2.py")
topk = _load("strong_context_v2_sweep_topk", "topk_metrics_v2.py")


def _fingerprint(value: Any) -> str:
    rendered = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def configuration_grid() -> list[dict[str, int]]:
    """A bounded allocation grid; top-K is deliberately not a configuration."""
    rows = []
    for result_cap, strong_cap, adr_cap, binding_cap, excerpt_chars, lineage_cap in product(
        (3, 5, 8), (1, 2, 3), (1, 2, 3), (1, 2), (96, 192), (4, 8)
    ):
        rows.append(
            {
                "result_cap": result_cap,
                "strong_cap": strong_cap,
                "adr_cap": adr_cap,
                "constitution_binding_cap": binding_cap,
                "constitution_excerpt_chars": excerpt_chars,
                "lineage_item_cap": lineage_cap,
            }
        )
    return rows


def _mappings(bindings: Mapping[str, Any]) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    index = resolver.load_bindings(bindings)
    membership = {ref: list(adr_ids) for ref, adr_ids in index.by_member.items()}
    constitution = {
        adr_id: [item["ref"] for item in row["constitution_refs"]]
        for adr_id, row in index.by_id.items()
    }
    return membership, constitution


def _derived_topk_gold(gold: Mapping[str, Any], constitution: Mapping[str, Sequence[str]]) -> dict[str, Any]:
    """Derive only a temporary mechanical target from the existing ADR gold.

    Current frozen gold has no Constitution requirement field.  This helper is
    intentionally labelled *derived* in output and must not be used to freeze
    a candidate; the later Constitution-aware gold review owns that decision.
    """
    adr_ids = [str(item) for item in gold.get("required_adr_ids", [])]
    return {
        "required_decision_refs": [str(item) for item in gold.get("relevant_refs", [])],
        "required_adr_ids": adr_ids,
        "required_constitution_refs": list(
            dict.fromkeys(ref for adr_id in adr_ids for ref in constitution.get(adr_id, ()))
        ),
        "authoritative_refs": [str(item) for item in gold.get("authoritative_refs", [])],
        "expected_statuses": dict(gold.get("expected_statuses", {})),
        "required_lineage_edges": list(gold.get("required_lineage_edges", [])),
        "required_related_edges": list(gold.get("required_related_edges", [])),
        "required_missing_refs": [str(item) for item in gold.get("required_missing_refs", [])],
        "insufficient_evidence": bool(gold.get("insufficient_evidence", False)),
    }


def _coverage(packet: Mapping[str, Any], gold: Mapping[str, Any]) -> dict[str, Any]:
    required_adrs = set(map(str, gold.get("required_adr_ids", ())))
    required_constitution = set(map(str, gold.get("required_constitution_refs", ())))
    selected_adrs: set[str] = set()
    selected_constitution: set[str] = set()
    evidence_refs: set[str] = set()
    authorities: set[str] = set()
    statuses: dict[str, str] = {}
    lineage_edges: set[tuple[str, str, str]] = set()
    related_refs: set[str] = set()
    for tier in packet["tiers"]:
        evidence_refs.add(tier["decision"]["ref"])
        for adr in tier.get("adrs", []):
            selected_adrs.add(adr["adr_id"])
            selected_constitution.update(item["ref"] for item in adr["constitution"])
            current = adr["current"]
            if current["authoritative_ref"]:
                authorities.add(current["authoritative_ref"])
            statuses[adr["adr_id"]] = current["status"]
            related_refs.update(adr["related_refs"])
            lineage_rows = adr["relevant_lineage"]
            evidence_refs.update(row["ref"] for row in lineage_rows)
            lineage_edges.update(
                (row["ref"], predecessor["ref"], predecessor["type"])
                for row in lineage_rows
                for predecessor in row["predecessors"]
            )
        for delta in tier.get("lineage_deltas", []):
            lineage_rows = delta["relevant_lineage"]
            evidence_refs.update(row["ref"] for row in lineage_rows)
            lineage_edges.update(
                (row["ref"], predecessor["ref"], predecessor["type"])
                for row in lineage_rows
                for predecessor in row["predecessors"]
            )
    required_decisions = set(map(str, gold.get("required_decision_refs", ())))
    required_heads = set(map(str, gold.get("authoritative_refs", ())))
    required_edges = {
        (str(edge["source"]), str(edge["target"]), str(edge["type"]))
        for edge in gold.get("required_lineage_edges", ())
    }
    expected_statuses = {str(key): str(value) for key, value in gold.get("expected_statuses", {}).items()}
    status_complete = all(statuses.get(adr_id) == status for adr_id, status in expected_statuses.items())
    missing_refs = set(map(str, gold.get("required_missing_refs", ())))
    absence_complete = (not gold.get("insufficient_evidence")) or not bool(missing_refs & evidence_refs)
    return {
        "decision": {"hits": len(evidence_refs & required_decisions), "required": len(required_decisions), "complete": required_decisions <= evidence_refs},
        "adr": {
            "hits": len(selected_adrs & required_adrs),
            "required": len(required_adrs),
            "complete": required_adrs <= selected_adrs,
            "extra": sorted(selected_adrs - required_adrs),
        },
        "constitution": {
            "hits": len(selected_constitution & required_constitution),
            "required": len(required_constitution),
            "complete": required_constitution <= selected_constitution,
            "extra": sorted(selected_constitution - required_constitution),
        },
        "authority": {"hits": len(authorities & required_heads), "required": len(required_heads), "complete": required_heads <= authorities},
        "status": {"complete": status_complete, "expected": expected_statuses, "found": statuses},
        "lineage": {"hits": len(lineage_edges & required_edges), "required": len(required_edges), "complete": required_edges <= lineage_edges, "found": sorted(lineage_edges)},
        "related": {"never_classified_as_lineage": all(kind != "related" for _, _, kind in lineage_edges), "supporting_refs": sorted(related_refs)},
        "absence": {"complete": absence_complete, "expected_insufficient_evidence": bool(gold.get("insufficient_evidence")), "missing_refs": sorted(missing_refs)},
    }


def _resolve_cell(
    configuration: Mapping[str, int], ranked: Sequence[Mapping[str, Any]], bindings: Mapping[str, Any], gold: Mapping[str, Any]
) -> dict[str, Any]:
    normalized = resolver.normalize_configuration(configuration)
    packet = resolver.resolve_strong_context(ranked, bindings, normalized)
    stable_packet = {key: value for key, value in packet.items() if key != "fingerprint"}
    return {
        "configuration": normalized,
        "configuration_fingerprint": _fingerprint(normalized),
        "packet_fingerprint": packet["fingerprint"],
        "packet_token_proxy": max(1, (len(json.dumps(stable_packet, sort_keys=True, ensure_ascii=False).encode("utf-8")) + 3) // 4),
        "coverage": _coverage(packet, gold),
        "omission_count": len(packet["omissions"]),
    }


def sweep_task(
    task: Mapping[str, Any],
    gold: Mapping[str, Any],
    fixture_root: str | Path,
    configurations: Sequence[Mapping[str, int]] | None = None,
    *,
    workers: int = 1,
) -> dict[str, Any]:
    """Evaluate one task using its literal question, independent of hints."""
    question = task.get("question")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("task question must be non-empty")
    if not isinstance(workers, int) or workers < 1:
        raise ValueError("workers must be positive")
    bindings = bridge.materialize_fixture_bindings(fixture_root)
    normalized = [resolver.normalize_configuration(row) for row in (configurations or configuration_grid())]
    deduped = { _fingerprint(row): row for row in normalized }
    configurations = [deduped[key] for key in sorted(deduped)]
    ranked = bridge.ranked_fixture_results(question, fixture_root, top_k=max(row["result_cap"] for row in configurations))
    membership, constitution = _mappings(bindings)
    derived_gold = _derived_topk_gold(gold, constitution)
    top_k = topk.measure_top_k(
        [
            {"decision_ref": row["ref"], "relevance": row["relevance"]}
            for row in ranked
        ],
        derived_gold,
        adr_membership=membership,
        constitution_bindings=constitution,
    )
    if workers == 1:
        cells = [_resolve_cell(row, ranked, bindings, derived_gold) for row in configurations]
    else:
        with ThreadPoolExecutor(max_workers=min(8, workers)) as executor:
            cells = list(executor.map(lambda row: _resolve_cell(row, ranked, bindings, derived_gold), configurations))
    payload = {
        "schema": SCHEMA,
        "task_id": task.get("task_id"),
        "fixture_root": str(Path(fixture_root).resolve()),
        "question_fingerprint": _fingerprint(question),
        "ranked_fingerprint": _fingerprint(ranked),
        "binding_fingerprint": resolver.load_bindings(bindings).fingerprint,
        "derived_topk_gold": derived_gold,
        "top_k_metrics": top_k,
        "cells": cells,
    }
    payload["fingerprint"] = _fingerprint(payload)
    return payload

"""Offline complete-query Top-K scorer for the revision/Constitution experiment.

This module is deliberately outside the retrieval and MCP paths.  It consumes
the immutable v2 gold through the scoring-only query join, ranks with the
production-default decision reader, and measures whether the materialized
strong-context packet closes every required ADR contract at K=1, 3, and 5.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
from typing import Any, Iterable, Mapping, Sequence


SCHEMA = "lightweight-top-k-result.v1"
CELL_SCHEMA = "lightweight-top-k-cell.v1"
K_VALUES = (1, 3, 5)
QUERY_IDS = tuple(f"CTX-{parent:02d}.V{variant:02d}" for parent in range(1, 13) for variant in range(1, 6))
CRITICAL_DIMENSIONS = ("adr_closure", "authority", "status", "lineage", "related", "constitution_binding")
_HERE = Path(__file__).resolve().parent


def _load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, _HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


queries = _load("lightweight_topk_queries", "revision_constitution_queries_v1.py")
resolver = _load("lightweight_topk_resolver", "strong_context_v2.py")
bridge = _load("lightweight_topk_bridge", "strong_context_fixture_v2.py")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _unique_strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{field} must be an array of non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{field} must not contain duplicates")
    return tuple(value)


def _edge_set(value: Any, field: str) -> set[tuple[str, str, str]]:
    if value is None:
        return set()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{field} must be an array")
    result: set[tuple[str, str, str]] = set()
    for edge in value:
        if not isinstance(edge, Mapping) or set(edge) != {"source", "target", "type"}:
            raise ValueError(f"{field} edges must contain source, target, and type")
        row = (edge["source"], edge["target"], edge["type"])
        if not all(isinstance(item, str) and item for item in row) or row in result:
            raise ValueError(f"{field} edges must be unique non-empty strings")
        result.add(row)
    return result


def _binding_set(value: Any) -> set[tuple[str, str, tuple[str, ...]]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("required_constitution_bindings must be an array")
    result: set[tuple[str, str, tuple[str, ...]]] = set()
    for binding in value:
        if not isinstance(binding, Mapping) or set(binding) != {"adr_id", "decision_ref", "constitution_refs"}:
            raise ValueError("required_constitution_bindings must use reviewed v2 triples")
        adr_id, decision_ref = binding["adr_id"], binding["decision_ref"]
        refs = _unique_strings(binding["constitution_refs"], "constitution_refs")
        row = (adr_id, decision_ref, tuple(sorted(refs)))
        if not isinstance(adr_id, str) or not adr_id or not resolver.is_canonical_decision_ref(decision_ref) or row in result:
            raise ValueError("required_constitution_bindings must be unique canonical triples")
        result.add(row)
    return result


def _exact(expected: Iterable[Any], found: Iterable[Any]) -> dict[str, Any]:
    expected_set, found_set = set(expected), set(found)
    return {
        "required": len(expected_set), "found": sorted(found_set),
        "missing": sorted(expected_set - found_set), "extra": sorted(found_set - expected_set),
        "complete": bool(expected_set) and expected_set == found_set,
    }


def _status_exact(expected: Mapping[str, Any], found: Mapping[str, str]) -> dict[str, Any]:
    normalized = {str(key): str(value) for key, value in expected.items()}
    if not normalized:
        return {"required": 0, "found": dict(sorted(found.items())), "missing": [], "extra": sorted(found), "mismatched": [], "complete": False}
    missing = sorted(key for key in normalized if key not in found)
    extra = sorted(key for key in found if key not in normalized)
    mismatched = sorted(key for key in normalized if key in found and normalized[key] != found[key])
    return {"required": len(normalized), "found": dict(sorted(found.items())), "missing": missing, "extra": extra, "mismatched": mismatched, "complete": not (missing or extra or mismatched)}


def _validate_gold(gold: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(gold, Mapping):
        raise ValueError("gold must be an object")
    required = ("required_adr_ids", "authoritative_refs", "relevant_refs", "expected_statuses", "required_constitution_bindings")
    missing = [key for key in required if key not in gold]
    if missing:
        raise ValueError("gold is missing: " + ", ".join(missing))
    refs = _unique_strings(gold["relevant_refs"], "relevant_refs")
    if not refs or not all(resolver.is_canonical_decision_ref(ref) for ref in refs):
        raise ValueError("relevant_refs must contain canonical, non-empty complete-query decisions")
    adrs = _unique_strings(gold["required_adr_ids"], "required_adr_ids")
    authorities = _unique_strings(gold["authoritative_refs"], "authoritative_refs")
    if not adrs or not authorities:
        raise ValueError("gold critical dimensions must have non-zero ADR and authority denominators")
    statuses = gold["expected_statuses"]
    if not isinstance(statuses, Mapping) or not statuses:
        raise ValueError("expected_statuses must have a non-zero denominator")
    bindings = _binding_set(gold["required_constitution_bindings"])
    # CTX-12 deliberately has no binding requirement; aggregate coverage keeps
    # binding applicability non-vacuous across the corpus.
    return {"decisions": set(refs), "adrs": set(adrs), "authorities": set(authorities), "statuses": statuses,
            "lineage": _edge_set(gold.get("required_lineage_edges", []), "required_lineage_edges"),
            "related": _edge_set(gold.get("required_related_edges", []), "required_related_edges"), "bindings": bindings}


def _packet_facts(packet: Mapping[str, Any], ranked_prefix: Sequence[Mapping[str, Any]]) -> tuple[dict[str, Any], list[str]]:
    if packet.get("schema") != resolver.RESULT_SCHEMA or not isinstance(packet.get("tiers"), list):
        raise ValueError("packet must be a strong-context-v2 result")
    ranked_by_ref = {row.get("ref"): row for row in ranked_prefix}
    facts = {"adrs": set(), "authorities": set(), "statuses": {}, "lineage": set(), "related": set(), "bindings": set()}
    failures: list[str] = []
    for tier in packet["tiers"]:
        decision = tier.get("decision", {})
        direct_ref = decision.get("ref")
        links = decision.get("links", {})
        if isinstance(direct_ref, str) and isinstance(links, Mapping):
            for target in links.get("related", []):
                if isinstance(target, str):
                    facts["related"].add((direct_ref, target, "related"))
        for adr in tier.get("adrs", []):
            if not isinstance(adr, Mapping):
                failures.append("invalid-adr-row")
                continue
            adr_id = adr.get("adr_id")
            trigger = adr.get("trigger")
            if not isinstance(trigger, Mapping) or set(trigger) != {"decision_ref", "kind"}:
                failures.append(f"{adr_id}:missing-trigger-provenance")
                continue
            trigger_ref, kind = trigger["decision_ref"], trigger["kind"]
            direct = ranked_by_ref.get(trigger_ref)
            if not isinstance(trigger_ref, str) or not resolver.is_canonical_decision_ref(trigger_ref) or direct is None or trigger_ref != direct_ref:
                failures.append(f"{adr_id}:non-direct-trigger")
                continue
            if kind != "ranked" or direct.get("trigger_kind", "ranked") != "ranked":
                failures.append(f"{adr_id}:related-trigger-leakage")
                continue
            if not isinstance(adr_id, str):
                failures.append("invalid-adr-id")
                continue
            facts["adrs"].add(adr_id)
            current = adr.get("current", {})
            if isinstance(current, Mapping):
                if isinstance(current.get("authoritative_ref"), str):
                    facts["authorities"].add(current["authoritative_ref"])
                if isinstance(current.get("status"), str):
                    facts["statuses"][adr_id] = current["status"]
            constitution_refs: list[str] = []
            for binding in adr.get("constitution", []):
                if isinstance(binding, Mapping) and isinstance(binding.get("ref"), str):
                    constitution_refs.append(binding["ref"])
            facts["bindings"].add((adr_id, trigger_ref, tuple(sorted(constitution_refs))))
            for row in adr.get("relevant_lineage", []):
                if not isinstance(row, Mapping):
                    continue
                source = row.get("ref")
                for predecessor in row.get("predecessors", []):
                    if isinstance(predecessor, Mapping) and all(isinstance(value, str) for value in (source, predecessor.get("ref"), predecessor.get("type"))):
                        facts["lineage"].add((source, predecessor["ref"], predecessor["type"]))
    return facts, failures


def score_query_cell(query: Mapping[str, Any], gold: Mapping[str, Any], ranked_rows: Sequence[Mapping[str, Any]], packet: Mapping[str, Any], *, k: int, query_corpus_fingerprint: str, ranking_fingerprint: str | None = None, ranking_arm: str = "production-default", latency_ms: float = 0.0, token_proxy: int | None = None) -> dict[str, Any]:
    """Score one immutable query/K cell; lexical cells are diagnostic only."""
    if k not in K_VALUES:
        raise ValueError("K must be exactly one of 1, 3, or 5")
    if ranking_arm not in {"production-default", "lexical-diagnostic"}:
        raise ValueError("ranking_arm must be production-default or lexical-diagnostic")
    query_id = query.get("query_id")
    if query_id not in QUERY_IDS or not isinstance(query.get("parent_task_id"), str):
        raise ValueError("query must be a canonical v1 query row")
    if not isinstance(query_corpus_fingerprint, str) or not query_corpus_fingerprint.startswith("sha256:"):
        raise ValueError("query_corpus_fingerprint must be stable sha256")
    target = _validate_gold(gold)
    ranked = list(ranked_rows)
    if not all(isinstance(row, Mapping) and isinstance(row.get("ref"), str) for row in ranked):
        raise ValueError("ranked_rows must contain materializer decision rows")
    prefix = ranked[:k]
    direct_refs = {str(row["ref"]) for row in prefix if resolver.is_canonical_decision_ref(row["ref"])}
    decision_hits = direct_refs & target["decisions"]
    first_hit = next((position for position, row in enumerate(ranked, 1) if row.get("ref") in target["decisions"]), None)
    facts, provenance_failures = _packet_facts(packet, prefix)
    dimensions = {
        "adr_closure": _exact(target["adrs"], facts["adrs"]),
        "authority": _exact(target["authorities"], facts["authorities"]),
        "status": _status_exact(target["statuses"], facts["statuses"]),
        "lineage": _exact(target["lineage"], facts["lineage"]),
        "related": _exact(target["related"], facts["related"]),
        "constitution_binding": _exact(target["bindings"], facts["bindings"]),
    }
    failures = list(provenance_failures)
    if decision_hits != target["decisions"]:
        failures.append("incomplete-query-decision-recall")
    failures.extend(name for name, row in dimensions.items() if not row["complete"])
    serialized = {key: value for key, value in packet.items() if key != "fingerprint"}
    result = {
        "schema": CELL_SCHEMA, "query_id": query_id, "parent_task_id": query["parent_task_id"], "k": k,
        "ranking_arm": ranking_arm, "query_corpus_fingerprint": query_corpus_fingerprint,
        "ranking_fingerprint": ranking_fingerprint or fingerprint(ranked), "packet_fingerprint": packet.get("fingerprint"),
        "complete_query_decision_recall": {"hits": len(decision_hits), "required": len(target["decisions"]), "complete": decision_hits == target["decisions"], "infeasible": len(target["decisions"]) > k},
        "item_decision_recall": {"hits": len(decision_hits), "required": len(target["decisions"]), "rate": len(decision_hits) / len(target["decisions"])},
        "first_hit_rank": first_hit, "mrr": 0.0 if first_hit is None else 1 / first_hit,
        "critical": dimensions, "provenance_failures": provenance_failures, "failures": sorted(set(failures)),
        "latency_ms": float(latency_ms), "token_proxy": token_proxy if token_proxy is not None else max(1, (len(canonical_json(serialized).encode("utf-8")) + 3) // 4),
    }
    result["fingerprint"] = fingerprint(result)
    return result


def aggregate_cells(cells: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Fail-closed reducer for exactly 60 query cells at each required K."""
    if not isinstance(cells, Sequence) or isinstance(cells, (str, bytes)):
        raise ValueError("cells must be an array")
    by_k: dict[int, list[Mapping[str, Any]]] = {k: [] for k in K_VALUES}
    for cell in cells:
        if not isinstance(cell, Mapping) or cell.get("schema") != CELL_SCHEMA or cell.get("k") not in by_k:
            raise ValueError("cells must be lightweight Top-K cells at K=1,3,5")
        by_k[cell["k"]].append(cell)
    summaries: dict[str, Any] = {}
    for k, rows in by_k.items():
        ids = [row.get("query_id") for row in rows]
        fingerprints = {row.get("query_corpus_fingerprint") for row in rows}
        errors: list[str] = []
        if len(rows) != 60: errors.append("incomplete-shard")
        if len(ids) != len(set(ids)): errors.append("duplicate-query-cell")
        if set(ids) != set(QUERY_IDS): errors.append("missing-or-unknown-query-cell")
        if len(fingerprints) != 1 or None in fingerprints: errors.append("mixed-query-corpus-fingerprint")
        item_hits = sum(int(row["item_decision_recall"]["hits"]) for row in rows)
        item_required = sum(int(row["item_decision_recall"]["required"]) for row in rows)
        complete = sum(bool(row["complete_query_decision_recall"]["complete"]) for row in rows)
        provenance_failures = [
            {"query_id": row.get("query_id"), "failures": list(row.get("provenance_failures", []))}
            for row in rows if row.get("provenance_failures")
        ]
        if provenance_failures:
            errors.append("provenance-gate")
        gates: dict[str, Any] = {}
        for name in CRITICAL_DIMENSIONS:
            # A zero-denominator negative control is not applicable when it
            # remains empty.  It becomes applicable (and must fail) the
            # instant it reports an unexpected fact, so extras can never hide
            # behind a required=0 denominator.
            applicable = [
                row for row in rows
                if int(row["critical"][name]["required"]) > 0
                or bool(row["critical"][name].get("found"))
                or bool(row["critical"][name].get("extra"))
            ]
            passing = sum(bool(row["critical"][name]["complete"]) for row in applicable)
            gate = {"applicable": len(applicable), "passing": passing, "required": len(applicable), "complete": bool(applicable) and passing == len(applicable)}
            if not gate["complete"]: errors.append(f"{name}-gate")
            gates[name] = gate
        recall_pass = len(rows) == 60 and complete >= 57
        if not recall_pass: errors.append("complete-query-recall")
        summary = {"k": k, "cell_count": len(rows), "query_corpus_fingerprint": next(iter(fingerprints), None),
                   "complete_query_recall": {"passing": complete, "required": 60, "threshold": 57, "rate": complete / len(rows) if rows else 0.0, "complete": recall_pass},
                   "item_decision_recall": {"hits": item_hits, "required": item_required, "rate": item_hits / item_required if item_required else None},
                   "mrr": sum(float(row["mrr"]) for row in rows) / len(rows) if rows else 0.0,
                   "first_hit_ranks": [row["first_hit_rank"] for row in rows], "critical_gates": gates,
                   "failures_by_query": [{"query_id": row.get("query_id"), "failures": row.get("failures", [])} for row in rows if row.get("failures")],
                   "provenance_failures_by_query": provenance_failures,
                   "latency_ms": {"total": sum(float(row["latency_ms"]) for row in rows), "mean": sum(float(row["latency_ms"]) for row in rows) / len(rows) if rows else 0.0},
                   "token_proxy": {"total": sum(int(row["token_proxy"]) for row in rows), "mean": sum(int(row["token_proxy"]) for row in rows) / len(rows) if rows else 0.0},
                   "errors": sorted(set(errors))}
        summary["passing"] = not summary["errors"]
        summaries[str(k)] = summary
    result = {"schema": SCHEMA, "k_values": list(K_VALUES), "results": summaries}
    corpus_fingerprints = {summary["query_corpus_fingerprint"] for summary in summaries.values()}
    if len(corpus_fingerprints) != 1 or None in corpus_fingerprints:
        for summary in summaries.values():
            summary["errors"] = sorted(set(summary["errors"] + ["mixed-query-corpus-fingerprint-across-k"]))
            summary["passing"] = False
    arms = {row.get("ranking_arm") for rows in by_k.values() for row in rows}
    if len(arms) != 1:
        for summary in summaries.values():
            summary["errors"] = sorted(set(summary["errors"] + ["mixed-ranking-arm"]))
            summary["passing"] = False
        result["ranking_arm"] = None
    else:
        result["ranking_arm"] = next(iter(arms), None)
    k5_passes = summaries["5"]["passing"]
    result["recommended_k"] = next((k for k in K_VALUES if summaries[str(k)]["passing"]), None) if k5_passes and result["ranking_arm"] == "production-default" else None
    result["fingerprint"] = fingerprint(result)
    return result


def evaluate_query_offline(query: Mapping[str, Any], gold: Mapping[str, Any], fixture_root: str | Path, *, query_corpus_fingerprint: str, ranking_arm: str = "production-default") -> list[dict[str, Any]]:
    """Run one offline query through production-default ranking and the existing materializer.

    ``lexical-diagnostic`` is intentionally returned as a diagnostic cell set;
    :func:`aggregate_cells` never recommends from that arm.
    """
    if ranking_arm not in {"production-default", "lexical-diagnostic"}:
        raise ValueError("ranking_arm must be production-default or lexical-diagnostic")
    started = time.perf_counter()
    ranking = bridge.ranked_fixture_payload(query["question"], fixture_root, top_k=max(K_VALUES), lexical_only=ranking_arm == "lexical-diagnostic")
    elapsed_ms = (time.perf_counter() - started) * 1000
    bindings = bridge.materialize_fixture_bindings(fixture_root)
    index = resolver.load_bindings(bindings)
    binding_cap = max((len(adr["constitution_refs"]) for adr in index.adrs), default=0)
    ranking_fingerprint = fingerprint(ranking["rows"])
    cells = []
    for k in K_VALUES:
        packet = resolver.resolve_strong_context(ranking["rows"], index, {"result_cap": k, "strong_cap": k, "adr_cap": len(index.adrs), "constitution_binding_cap": binding_cap, "lineage_item_cap": 999, "expansion_policy": "ranked", "relevance_calibrated": ranking["relevance_calibrated"]})
        cells.append(score_query_cell(query, gold, ranking["rows"], packet, k=k, query_corpus_fingerprint=query_corpus_fingerprint, ranking_fingerprint=ranking_fingerprint, ranking_arm=ranking_arm, latency_ms=elapsed_ms))
    return cells


def evaluate_corpus_offline(fixture_roots: Mapping[str, str | Path], *, ranking_arm: str = "production-default") -> list[dict[str, Any]]:
    """Explicit, non-CLI evaluator; callers must obtain scored-run approval."""
    corpus, _rows = queries.load_query_variants()
    output: list[dict[str, Any]] = []
    for query, gold in queries.join_queries_to_gold():
        fixture = query["fixture"]
        if fixture not in fixture_roots:
            raise ValueError(f"missing fixture root for {fixture}")
        output.extend(evaluate_query_offline(query, gold, fixture_roots[fixture], query_corpus_fingerprint=corpus["canonical_fingerprint"], ranking_arm=ranking_arm))
    return output

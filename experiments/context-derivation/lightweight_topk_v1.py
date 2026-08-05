"""Offline complete-query Top-K scorer for the revision/Constitution experiment.

This module is deliberately outside the retrieval and MCP paths.  It consumes
the immutable v2 gold through the scoring-only query join, ranks with the
production-default decision reader, and selects K from decision recall,
integrity, provenance, and related-safety. Exact ADR/Constitution closure
remains a visible diagnostic at K=1, 3, and 5.
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
SELECTION_SAFETY_DIMENSIONS = ("related",)
DIAGNOSTIC_DIMENSIONS = tuple(name for name in CRITICAL_DIMENSIONS if name not in SELECTION_SAFETY_DIMENSIONS)
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
subjects = _load("lightweight_topk_subjects", "lightweight_subjects_v1.py")


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _offline_packet_fingerprint(fixture_roots: Mapping[str, str | Path]) -> str:
    """Bind the evaluator to the exact generated fixture packets before ranking."""
    manifests: dict[str, Any] = {}
    for fixture, root in sorted(fixture_roots.items()):
        try:
            manifests[fixture] = json.loads((Path(root) / "FIXTURE_MANIFEST.json").read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError("frozen-run fixture packet is unavailable") from error
    return fingerprint(manifests)


def topk_frozen_run_proposal(fixture_roots: Mapping[str, str | Path]) -> dict[str, Any]:
    """Produce a proposal only; owner approval is a separate, explicit act."""
    corpus, _rows = queries.load_query_variants()
    receipt = {
        "schema": subjects.FROZEN_RUN_SCHEMA, "kind": "topk", "approval_status": "PROPOSED",
        "corpus_fingerprint": corpus["canonical_fingerprint"],
        "schedule_fingerprint": subjects.fingerprint(subjects.build_schedule(subjects.queries.subject_visible_queries())),
        "packet_fingerprint": _offline_packet_fingerprint(fixture_roots), "selected_pins": {},
    }
    receipt["fingerprint"] = subjects.fingerprint(receipt)
    return receipt


def require_topk_frozen_run(receipt: Mapping[str, Any] | None, fixture_roots: Mapping[str, str | Path]) -> None:
    required = {"schema", "kind", "approval_status", "corpus_fingerprint", "schedule_fingerprint", "packet_fingerprint", "selected_pins", "fingerprint"}
    if not isinstance(receipt, Mapping) or set(receipt) != required:
        raise RuntimeError("approved frozen-run receipt is required before offline ranking")
    if receipt.get("schema") != subjects.FROZEN_RUN_SCHEMA or receipt.get("kind") != "topk" or receipt.get("approval_status") != "APPROVED":
        raise RuntimeError("approved frozen-run receipt is required before offline ranking")
    if receipt.get("fingerprint") != subjects.fingerprint({key: value for key, value in receipt.items() if key != "fingerprint"}):
        raise RuntimeError("frozen-run receipt fingerprint is stale")
    corpus, _rows = queries.load_query_variants()
    if receipt.get("corpus_fingerprint") != corpus["canonical_fingerprint"]:
        raise RuntimeError("frozen-run corpus fingerprint drift")
    if receipt.get("schedule_fingerprint") != subjects.fingerprint(subjects.build_schedule(subjects.queries.subject_visible_queries())):
        raise RuntimeError("frozen-run schedule fingerprint drift")
    if receipt.get("packet_fingerprint") != _offline_packet_fingerprint(fixture_roots):
        raise RuntimeError("frozen-run packet fingerprint drift")
    if receipt.get("selected_pins") != {}:
        raise RuntimeError("offline ranking receipt must not carry subject pins")


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
        "complete": expected_set == found_set,
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
    scoped = packet.get("revision_constitution_bindings")
    trace_adrs: dict[str, set[str]] = {}
    if scoped is not None and not isinstance(scoped, list):
        failures.append("invalid-revision-constitution-bindings")
    for trace in packet.get("trace", []):
        if isinstance(trace, Mapping) and isinstance(trace.get("ref"), str) and isinstance(trace.get("matched_adr_ids"), list):
            trace_adrs[trace["ref"]] = {adr_id for adr_id in trace["matched_adr_ids"] if isinstance(adr_id, str)}
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
            if scoped is None:
                facts["bindings"].add((adr_id, trigger_ref, tuple(sorted(constitution_refs))))
            for row in adr.get("relevant_lineage", []):
                if not isinstance(row, Mapping):
                    continue
                source = row.get("ref")
                for predecessor in row.get("predecessors", []):
                    if isinstance(predecessor, Mapping) and all(isinstance(value, str) for value in (source, predecessor.get("ref"), predecessor.get("type"))):
                        facts["lineage"].add((source, predecessor["ref"], predecessor["type"]))
        # A later ranked revision can reuse an ADR already expanded by an
        # earlier rank. Its typed history is carried as a delta, not a second
        # ADR body; it remains just as material packet evidence.
        for delta in tier.get("lineage_deltas", []):
            if not isinstance(delta, Mapping):
                continue
            for row in delta.get("relevant_lineage", []):
                if not isinstance(row, Mapping):
                    continue
                source = row.get("ref")
                for predecessor in row.get("predecessors", []):
                    if isinstance(predecessor, Mapping) and all(isinstance(value, str) for value in (source, predecessor.get("ref"), predecessor.get("type"))):
                        facts["lineage"].add((source, predecessor["ref"], predecessor["type"]))
    if isinstance(scoped, list):
        for binding in scoped:
            if not isinstance(binding, Mapping) or set(binding) != {"adr_id", "decision_ref", "constitution"}:
                failures.append("invalid-revision-constitution-binding")
                continue
            adr_id, decision_ref, constitution = binding["adr_id"], binding["decision_ref"], binding["constitution"]
            if (not isinstance(adr_id, str) or not isinstance(decision_ref, str)
                    or decision_ref not in ranked_by_ref or adr_id not in facts["adrs"]
                    or adr_id not in trace_adrs.get(decision_ref, set()) or not isinstance(constitution, list)):
                failures.append("invalid-revision-constitution-provenance")
                continue
            refs: list[str] = []
            for item in constitution:
                if not isinstance(item, Mapping) or not isinstance(item.get("ref"), str):
                    failures.append("invalid-revision-constitution-evidence")
                    break
                refs.append(item["ref"])
            else:
                if not refs or len(refs) != len(set(refs)):
                    failures.append("invalid-revision-constitution-evidence")
                else:
                    facts["bindings"].add((adr_id, decision_ref, tuple(sorted(refs))))
    return facts, failures


def _resolver_adr_scope(query: Mapping[str, Any]) -> frozenset[str]:
    """Read the pre-frozen routing scope; score gold is never consulted."""
    hints = query.get("resolver_hints")
    if not isinstance(hints, Mapping):
        raise ValueError("query must include pre-frozen resolver_hints")
    adr_ids = hints.get("adr_ids")
    if (not isinstance(adr_ids, list) or not all(isinstance(adr_id, str) and adr_id for adr_id in adr_ids)
            or len(adr_ids) != len(set(adr_ids))):
        raise ValueError("resolver_hints.adr_ids must be unique non-empty strings")
    return frozenset(adr_ids)


def _apply_resolver_adr_scope(packet: Mapping[str, Any], scope: frozenset[str]) -> dict[str, Any]:
    """Mechanically hide matched ADRs outside a non-empty frozen concern scope."""
    if not scope:
        return dict(packet)
    result = {key: value for key, value in packet.items() if key != "fingerprint"}
    tiers: list[dict[str, Any]] = []
    for tier in packet.get("tiers", []):
        if not isinstance(tier, Mapping):
            continue
        scoped_tier = dict(tier)
        if isinstance(tier.get("adrs"), list):
            scoped_tier["adrs"] = [row for row in tier["adrs"] if isinstance(row, Mapping) and row.get("adr_id") in scope]
        if isinstance(tier.get("adr_refs"), list):
            scoped_tier["adr_refs"] = [adr_id for adr_id in tier["adr_refs"] if adr_id in scope]
        if isinstance(tier.get("lineage_deltas"), list):
            scoped_tier["lineage_deltas"] = [row for row in tier["lineage_deltas"] if isinstance(row, Mapping) and row.get("adr_id") in scope]
        tiers.append(scoped_tier)
    trace: list[dict[str, Any]] = []
    for row in packet.get("trace", []):
        if not isinstance(row, Mapping):
            continue
        scoped_row = dict(row)
        for field in ("matched_adr_ids", "included_adr_ids", "skipped_adr_ids"):
            if isinstance(row.get(field), list):
                scoped_row[field] = [adr_id for adr_id in row[field] if adr_id in scope]
        trace.append(scoped_row)
    result["tiers"] = tiers
    result["trace"] = trace
    result["fingerprint"] = fingerprint(result)
    return result


def _revision_scoped_packet(packet: Mapping[str, Any], ranked_prefix: Sequence[Mapping[str, Any]], revision_bindings: Sequence[Mapping[str, Any]], *, scope: frozenset[str], index: Any) -> dict[str, Any]:
    """Attach fixture-declared revision evidence without repeating ADR prose.

    Packet construction is deliberately score-gold-free: direct ranked
    decision refs select compact rows from the independent fixture-side map.
    """
    ranked_refs = {row.get("ref") for row in ranked_prefix if isinstance(row, Mapping)}
    trace_adrs = {
        trace["ref"]: set(trace["matched_adr_ids"])
        for trace in packet.get("trace", [])
        if isinstance(trace, Mapping) and isinstance(trace.get("ref"), str)
        and isinstance(trace.get("matched_adr_ids"), list)
    }
    selected: list[Mapping[str, Any]] = []
    for binding in revision_bindings:
        adr_id, decision_ref = binding.get("adr_id"), binding.get("decision_ref")
        if (not isinstance(adr_id, str) or not isinstance(decision_ref, str)
                or decision_ref not in ranked_refs or adr_id not in trace_adrs.get(decision_ref, set())):
            continue
        selected.append(binding)
    selected_refs_by_adr: dict[str, set[str]] = {}
    for binding in selected:
        selected_refs_by_adr.setdefault(str(binding["adr_id"]), set()).add(str(binding["decision_ref"]))
    scoped: list[dict[str, Any]] = []
    for binding in selected:
        adr_id, decision_ref = str(binding["adr_id"]), str(binding["decision_ref"])
        constitution = binding.get("constitution")
        if not isinstance(constitution, list):
            raise ValueError("fixture revision Constitution mapping is malformed")
        if not scope:
            constitution = [item for item in constitution if isinstance(item, Mapping) and item.get("role") == "governing"]
        else:
            authoritative = index.by_id[adr_id]["current"]["authoritative_ref"]
            if authoritative == decision_ref and len(selected_refs_by_adr[adr_id]) > 1:
                constitution = [item for item in constitution if isinstance(item, Mapping) and item.get("role") == "governing"]
        if constitution:
            scoped.append({"adr_id": adr_id, "decision_ref": decision_ref, "constitution": [dict(item) for item in constitution]})
    scoped.sort(key=lambda row: (row["adr_id"], row["decision_ref"]))
    result = {key: value for key, value in packet.items() if key != "fingerprint"}
    result["revision_constitution_bindings"] = scoped
    result["fingerprint"] = fingerprint(result)
    return result


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
    """Select K from recall plus integrity/provenance/related safety.

    The other exact closure metrics are retained in ``critical_gates`` and
    ``diagnostics`` so they remain reviewable without becoming an oracle gate
    for a ranking recommendation.
    """
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
        diagnostics: list[str] = []
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
            if not gate["complete"]:
                if name in SELECTION_SAFETY_DIMENSIONS:
                    errors.append(f"{name}-gate")
                else:
                    diagnostics.append(f"{name}-diagnostic")
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
                   "diagnostics": sorted(set(diagnostics)), "errors": sorted(set(errors))}
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


def _evaluate_query_offline(query: Mapping[str, Any], gold: Mapping[str, Any], fixture_root: str | Path, *, query_corpus_fingerprint: str, ranking_arm: str = "production-default", ranking_receipt: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Run one offline query through production-default ranking and the existing materializer.

    ``lexical-diagnostic`` is intentionally returned as a diagnostic cell set;
    :func:`aggregate_cells` never recommends from that arm.
    """
    if ranking_arm not in {"production-default", "lexical-diagnostic"}:
        raise ValueError("ranking_arm must be production-default or lexical-diagnostic")
    started = time.perf_counter()
    ranking = bridge.ranked_fixture_payload(query["question"], fixture_root, top_k=max(K_VALUES), lexical_only=ranking_arm == "lexical-diagnostic", ranking_receipt=ranking_receipt)
    elapsed_ms = (time.perf_counter() - started) * 1000
    bindings = bridge.materialize_fixture_bindings(fixture_root)
    index = resolver.load_bindings(bindings)
    revision_bindings = bridge.materialize_revision_constitution_bindings(fixture_root, index)
    binding_cap = max((len(adr["constitution_refs"]) for adr in index.adrs), default=0)
    ranking_fingerprint = fingerprint(ranking["rows"])
    cells = []
    scope = _resolver_adr_scope(query)
    for k in K_VALUES:
        packet = resolver.resolve_strong_context(ranking["rows"], index, {"result_cap": k, "strong_cap": k, "adr_cap": len(index.adrs), "constitution_binding_cap": binding_cap, "lineage_item_cap": 999, "expansion_policy": "ranked", "relevance_calibrated": ranking["relevance_calibrated"]})
        packet = _apply_resolver_adr_scope(packet, scope)
        packet = _revision_scoped_packet(packet, ranking["rows"][:k], revision_bindings, scope=scope, index=index)
        cells.append(score_query_cell(query, gold, ranking["rows"], packet, k=k, query_corpus_fingerprint=query_corpus_fingerprint, ranking_fingerprint=ranking_fingerprint, ranking_arm=ranking_arm, latency_ms=elapsed_ms))
    return cells


def evaluate_query_offline(query: Mapping[str, Any], gold: Mapping[str, Any], fixture_root: str | Path, *, query_corpus_fingerprint: str, ranking_arm: str = "production-default", frozen_run: Mapping[str, Any] | None = None, ranking_receipt: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Owner-gated public entry point for one scored offline query."""
    require_topk_frozen_run(frozen_run, {str(query.get("fixture", "query")): fixture_root})
    return _evaluate_query_offline(query, gold, fixture_root, query_corpus_fingerprint=query_corpus_fingerprint, ranking_arm=ranking_arm, ranking_receipt=ranking_receipt)


def evaluate_corpus_offline(fixture_roots: Mapping[str, str | Path], *, ranking_arm: str = "production-default", frozen_run: Mapping[str, Any] | None = None, ranking_receipts: Mapping[str, Mapping[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Explicit, non-CLI evaluator; callers must obtain scored-run approval."""
    corpus, _rows = queries.load_query_variants()
    require_topk_frozen_run(frozen_run, fixture_roots)
    expected_receipts = {query["query_id"] for query, _gold in queries.join_queries_to_gold()}
    if not isinstance(ranking_receipts, Mapping) or set(ranking_receipts) != expected_receipts:
        raise RuntimeError("approved ranking receipts are required for every offline query")
    output: list[dict[str, Any]] = []
    for query, gold in queries.join_queries_to_gold():
        fixture = query["fixture"]
        if fixture not in fixture_roots:
            raise ValueError(f"missing fixture root for {fixture}")
        output.extend(_evaluate_query_offline(query, gold, fixture_roots[fixture], query_corpus_fingerprint=corpus["canonical_fingerprint"], ranking_arm=ranking_arm, ranking_receipt=ranking_receipts[query["query_id"]]))
    return output

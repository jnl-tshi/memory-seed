"""Fail-closed, offline results reducer for the lightweight subject experiment.

This module consumes only frozen query/gold definitions, immutable packet
manifests, and already-written subject result manifests.  It deliberately has
no provider, model, filesystem-to-subject, or production retrieval surface.
"""

from __future__ import annotations

from collections import defaultdict
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable, Mapping, Sequence


HERE = Path(__file__).resolve().parent


def _load(name: str, filename: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contracts = _load("lightweight_results_contracts", "contracts.py")
queries = _load("lightweight_results_queries", "revision_constitution_queries_v1.py")
subjects = _load("lightweight_results_subjects", "lightweight_subjects_v1.py")
topk = _load("lightweight_results_topk", "lightweight_topk_v1.py")

SCHEMA = "lightweight-results.v1"
CELL_SCHEMA = "lightweight-result-cell.v1"
PACKET_MANIFEST_SCHEMA = "lightweight-subject-packet-manifest.v1"
JUDGE_SCHEMA = "lightweight-explanation-review.v1"
ARMS = subjects.ARMS
SUBJECTS = subjects.SUBJECTS
QUERY_COUNT = 60
EXPECTED_CELL_COUNT = QUERY_COUNT * len(ARMS) * len(SUBJECTS)
_REF = re.compile(r"(?:mse_[A-Za-z0-9]+:d[1-9][0-9]*|constitution:[A-Za-z0-9._-]+(?:#[A-Za-z0-9._-]+)?|adr_[a-z0-9_]+(?![A-Za-z0-9_-]))")
_GOLD_KEYS = frozenset(queries._GOLD_FIELD_NAMES | {"gold", "answer_key", "answer-key", "labels"})


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _set(value: Any, field: str) -> set[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"{field} must be an array of non-empty strings")
    if len(value) != len(set(value)):
        raise ValueError(f"{field} must not contain duplicates")
    return set(value)


def _subject_query(query: Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact Task 3 subject-visible portion of a frozen query."""
    return {field: query[field] for field in ("query_id", "parent_task_id", "variant_index", "question")}


def _reject_gold_leak(value: Any) -> None:
    """Gold labels cannot be embedded in immutable subject packets."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).lower() in _GOLD_KEYS:
                raise ValueError("gold field leaked into subject packet")
            _reject_gold_leak(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_gold_leak(item)


def _edges(value: Any, field: str, *, allowed_types: set[str]) -> set[tuple[str, str, str]]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be an array")
    result: set[tuple[str, str, str]] = set()
    for edge in value:
        if not isinstance(edge, Mapping) or set(edge) != {"source", "target", "type"}:
            raise ValueError(f"{field} contains a malformed edge")
        row = (edge.get("source"), edge.get("target"), edge.get("type"))
        if not all(isinstance(item, str) and item for item in row) or row[2] not in allowed_types or row in result:
            raise ValueError(f"{field} contains an invalid or duplicate edge")
        result.add(row)
    return result


def _exact(expected: Iterable[Any], actual: Iterable[Any]) -> dict[str, Any]:
    required, found = set(expected), set(actual)
    return {
        "required": len(required), "found": sorted(found),
        "missing": sorted(required - found), "extra": sorted(found - required),
        "complete": required == found,
    }


def _status_exact(expected: Mapping[str, Any], actual: Mapping[str, Any]) -> dict[str, Any]:
    wanted = {str(key): str(value) for key, value in expected.items()}
    received = {str(key): str(value) for key, value in actual.items()}
    missing = sorted(key for key in wanted if key not in received)
    extra = sorted(key for key in received if key not in wanted)
    mismatched = sorted(key for key in wanted if key in received and wanted[key] != received[key])
    return {
        "required": len(wanted), "found": dict(sorted(received.items())),
        "missing": missing, "extra": extra, "mismatched": mismatched,
        "complete": not (missing or extra or mismatched),
    }


def _gold(gold: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "required_adr_ids", "authoritative_refs", "expected_statuses", "required_lineage_edges",
        "required_constitution_bindings", "insufficient_evidence",
    }
    absent = sorted(required - set(gold))
    if absent:
        raise ValueError("gold is missing " + ", ".join(absent))
    bindings = gold["required_constitution_bindings"]
    if not isinstance(bindings, list):
        raise ValueError("required_constitution_bindings must be an array")
    constitution: set[str] = set()
    binding_rows: set[tuple[str, str, tuple[str, ...]]] = set()
    for binding in bindings:
        if not isinstance(binding, Mapping) or set(binding) != {"adr_id", "decision_ref", "constitution_refs"}:
            raise ValueError("constitution gold must use reviewed v2 binding triples")
        refs = _set(binding["constitution_refs"], "constitution_refs")
        adr_id, decision_ref = binding["adr_id"], binding["decision_ref"]
        if not isinstance(adr_id, str) or not adr_id or not isinstance(decision_ref, str) or not decision_ref:
            raise ValueError("constitution gold must use non-empty ADR/revision pairs")
        row = (adr_id, decision_ref, tuple(sorted(refs)))
        if row in binding_rows:
            raise ValueError("constitution gold bindings must be unique")
        binding_rows.add(row)
        constitution.update(refs)
    return {
        "adrs": _set(gold["required_adr_ids"], "required_adr_ids"),
        "authorities": _set(gold["authoritative_refs"], "authoritative_refs"),
        "statuses": gold["expected_statuses"] if isinstance(gold["expected_statuses"], Mapping) else (_ for _ in ()).throw(ValueError("expected_statuses must be a mapping")),
        "lineage": _edges(gold["required_lineage_edges"], "required_lineage_edges", allowed_types={"evolves", "replaces"}),
        "related": _edges(gold.get("required_related_edges", []), "required_related_edges", allowed_types={"related"}),
        "constitution": constitution,
        "constitution_bindings": binding_rows,
        "citation_refs": _set(gold.get("relevant_refs", []), "relevant_refs")
        | _set(gold["required_adr_ids"], "required_adr_ids") | constitution,
        "material_refs": _set(gold["required_adr_ids"], "required_adr_ids")
        | _set(gold["authoritative_refs"], "authoritative_refs")
        | set(map(str, gold["expected_statuses"]))
        | {ref for edge in _edges(gold["required_lineage_edges"], "required_lineage_edges", allowed_types={"evolves", "replaces"}) for ref in edge[:2]}
        | {ref for edge in _edges(gold.get("required_related_edges", []), "required_related_edges", allowed_types={"related"}) for ref in edge[:2]}
        | constitution | _set(gold.get("required_missing_refs", []), "required_missing_refs"),
        "insufficient": bool(gold["insufficient_evidence"]),
        "missing": _set(gold.get("required_missing_refs", []), "required_missing_refs"),
    }


def _evidence_refs(evidence: Any) -> set[str]:
    """Return every canonical decision, ADR, or Constitution reference in evidence."""
    refs: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, Mapping):
            for item in value.values():
                visit(item)
        elif isinstance(value, (list, tuple)):
            for item in value:
                visit(item)
        elif isinstance(value, str):
            refs.update(_REF.findall(value))

    visit(evidence)
    return refs


def _material_refs(answer: Mapping[str, Any]) -> set[str]:
    """Find references in every answer claim, including the free-text explanation."""
    return _evidence_refs(answer)


def _packet_key(packet: Mapping[str, Any]) -> tuple[str, str]:
    return str(packet.get("query_id")), str(packet.get("arm"))


def _canonical_frozen_rows(query_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Reject caller-supplied rows unless they are byte-for-byte frozen rows."""
    _corpus, expected = queries.load_query_variants()
    if canonical_json(list(query_rows)) != canonical_json(expected):
        raise ValueError("results require the ordered frozen 60-query corpus")
    return expected


def validate_packet_manifests(packet_manifests: Sequence[Mapping[str, Any]], query_rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], Mapping[str, Any]]:
    """Validate one immutable fixed packet for every query/arm pair."""
    query_rows = _canonical_frozen_rows(query_rows)
    query_by_id = {str(row.get("query_id")): row for row in query_rows}
    expected = {(query_id, arm) for query_id in query_by_id for arm in ARMS}
    packets: dict[tuple[str, str], Mapping[str, Any]] = {}
    for packet in packet_manifests:
        if not isinstance(packet, Mapping) or packet.get("schema") != PACKET_MANIFEST_SCHEMA:
            raise ValueError("packet manifests must use lightweight-subject-packet-manifest.v1")
        required_fields = {"schema", "query_id", "parent_task_id", "arm", "query", "corpus_fingerprint", "task_fingerprint", "evidence", "packet_fingerprint", "context_fingerprint"}
        if set(packet) != required_fields:
            raise ValueError("packet manifest must use the complete immutable manifest shape")
        key = _packet_key(packet)
        query = query_by_id.get(key[0])
        if key in packets:
            raise ValueError(f"duplicate packet manifest: {key}")
        if query is None or key[1] not in ARMS or packet.get("parent_task_id") != query.get("parent_task_id"):
            raise ValueError("packet manifest is outside the frozen corpus")
        evidence = packet.get("evidence")
        if not isinstance(evidence, Mapping):
            raise ValueError("packet manifest evidence must be an object")
        subject_query = _subject_query(query)
        if packet.get("query") != subject_query or packet.get("corpus_fingerprint") != queries.load_query_variants()[0]["canonical_fingerprint"] or packet.get("task_fingerprint") != fingerprint(subject_query):
            raise ValueError("packet manifest is not bound to the canonical frozen query corpus")
        _reject_gold_leak(packet["query"])
        _reject_gold_leak(evidence)
        try:
            canonical = subjects.build_packet(key[1], query, evidence)
        except (TypeError, ValueError) as error:
            raise ValueError("packet manifest does not materialize the canonical fixed arm") from error
        full_evidence = subjects._thaw(canonical.payload)["evidence"]
        if packet.get("packet_fingerprint") != canonical.fingerprint or packet.get("context_fingerprint") != fingerprint(full_evidence):
            raise ValueError("packet manifest fingerprint mismatch")
        packets[key] = packet
    if set(packets) != expected:
        raise ValueError("packet manifests must contain exactly one fixed packet per query and arm")
    return packets


def _validate_result_manifest(
    result: Mapping[str, Any], *, query: Mapping[str, Any], packet: Mapping[str, Any], corpus_fingerprint: str
) -> None:
    if result.get("schema") != subjects.RESULT_SCHEMA:
        raise ValueError("subject result must use lightweight-subject-result.v1")
    required_fields = {"schema", "query_id", "parent_task_id", "arm", "subject", "packet_fingerprint", "context_fingerprint", "task_fingerprint", "corpus_fingerprint", "pin", "pin_fingerprint", "duration_ms", "usage", "token_proxy", "transcript", "parsed_answer", "protocol_failure", "isolation"}
    if set(result) != required_fields:
        raise ValueError("subject result must use the complete runtime manifest shape")
    for name in ("query_id", "parent_task_id"):
        if result.get(name) != query.get(name):
            raise ValueError("result identity does not match frozen query")
    if result.get("arm") != packet.get("arm"):
        raise ValueError("result arm does not match the fixed packet")
    if result.get("packet_fingerprint") != packet.get("packet_fingerprint") or result.get("context_fingerprint") != packet.get("context_fingerprint"):
        raise ValueError("result packet/context fingerprint mismatch")
    if result.get("corpus_fingerprint") != corpus_fingerprint or result.get("corpus_fingerprint") != packet.get("corpus_fingerprint") or result.get("task_fingerprint") != fingerprint(_subject_query(query)) or result.get("task_fingerprint") != packet.get("task_fingerprint"):
        raise ValueError("result corpus/task fingerprint mismatch")
    subject = result.get("subject")
    if subject not in SUBJECTS:
        raise ValueError("result has an unknown subject")
    pin = result.get("pin")
    pin_fields = {"subject", "requested_model", "reported_model", "model_digest", "quantization", "context_window", "decoding", "provider_version", "cli_version", "adapter_version"}
    if not isinstance(pin, Mapping) or set(pin) != pin_fields or pin.get("subject") != subject or result.get("pin_fingerprint") != fingerprint(pin):
        raise ValueError("result pin fingerprint mismatch")
    if not all(isinstance(pin[name], str) and pin[name] for name in ("subject", "requested_model", "reported_model", "model_digest", "quantization", "provider_version", "adapter_version")) or not isinstance(pin["context_window"], int) or isinstance(pin["context_window"], bool) or not isinstance(pin["decoding"], Mapping) or (pin["cli_version"] is not None and (not isinstance(pin["cli_version"], str) or not pin["cli_version"])):
        raise ValueError("result pin is malformed")
    try:
        observed_pin = subjects.SubjectPin(
            subject=pin["subject"], requested_model=pin["requested_model"], reported_model=pin["reported_model"],
            model_digest=pin["model_digest"], quantization=pin["quantization"], context_window=pin["context_window"],
            decoding=subjects.frozen_decoding(pin["decoding"]), provider_version=pin["provider_version"],
            cli_version=pin["cli_version"], adapter_version=pin["adapter_version"],
        )
        observed_pin.validate()
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("result pin is malformed") from error
    if result.get("protocol_failure") is not None:
        raise ValueError("protocol-failed result cannot be mechanically scored")
    if not isinstance(result.get("parsed_answer"), Mapping):
        raise ValueError("result must contain a parsed answer")
    subjects.validate_answer(dict(result["parsed_answer"]))
    if not isinstance(result.get("duration_ms"), (int, float)) or result["duration_ms"] < 0:
        raise ValueError("result duration_ms must be non-negative")
    if not isinstance(result.get("token_proxy"), int) or result["token_proxy"] <= 0 or not isinstance(result.get("usage"), Mapping) or not isinstance(result.get("transcript"), str) or not isinstance(result.get("isolation"), Mapping):
        raise ValueError("result token usage is malformed")
    if not {"empty_cwd", "repo_access", "mcp_enabled"} <= set(result["isolation"]) or result["isolation"].get("empty_cwd") is not True or result["isolation"].get("repo_access") is not False or result["isolation"].get("mcp_enabled") is not False:
        raise ValueError("result isolation evidence is malformed")


def score_cell(result: Mapping[str, Any], gold: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Score one answer with exact, evidence-bounded mechanical checks."""
    answer = subjects.validate_answer(dict(result["parsed_answer"]))
    target = _gold(gold)
    citations = _set(answer["citations"], "citations")
    evidence_refs = _evidence_refs(evidence)
    material_refs = _material_refs(answer)
    lineage = _edges(answer["lineage_edges"], "lineage_edges", allowed_types={"evolves", "replaces"})
    related = _edges(answer["related_edges"], "related_edges", allowed_types={"related"})
    related_pairs = {(source, target) for source, target, _kind in target["related"]}
    related_as_lineage = sorted(edge for edge in lineage if edge[:2] in related_pairs)
    constitution_citations = {citation for citation in citations if citation.startswith("constitution:")}
    actual_bindings = {
        (binding["adr_id"], binding["decision_ref"], tuple(sorted(binding["constitution_refs"])))
        for binding in answer["constitution_bindings"]
    }
    checks = {
        "insufficient_evidence": {"expected": target["insufficient"], "found": answer["insufficient_evidence"], "complete": answer["insufficient_evidence"] == target["insufficient"]},
        "adr_ids": _exact(target["adrs"], _set(answer["adr_ids"], "adr_ids")),
        "authoritative_refs": _exact(target["authorities"], _set(answer["authoritative_refs"], "authoritative_refs")),
        "statuses": _status_exact(target["statuses"], answer["adr_statuses"]),
        "lineage_edges": _exact(target["lineage"], lineage),
        "constitution_refs": _exact(target["constitution"], constitution_citations),
        "constitution_bindings": _exact(target["constitution_bindings"], actual_bindings),
        "citations": {"required": len(citations), "found": sorted(citations), "outside_evidence": sorted(citations - evidence_refs), "extra_material_refs": sorted(citations - target["citation_refs"]), "complete": bool(citations) and citations <= evidence_refs and citations <= target["citation_refs"]},
        "material_refs": {"found": sorted(material_refs), "outside_evidence": sorted(material_refs - evidence_refs - target["missing"]), "extra": sorted(material_refs - target["material_refs"]), "complete": material_refs <= evidence_refs | target["missing"] and material_refs <= target["material_refs"]},
        "related_safety": {"required": len(target["related"]), "found": sorted(related), "related_as_lineage": related_as_lineage, "complete": related == target["related"] and not related_as_lineage},
        "missing_refs": _exact(target["missing"], _set(answer["missing_refs"], "missing_refs")),
    }
    failures = sorted(name for name, check in checks.items() if not check["complete"])
    row = {
        "schema": CELL_SCHEMA, "query_id": result["query_id"], "parent_task_id": result["parent_task_id"],
        "arm": result["arm"], "subject": result["subject"], "checks": checks,
        "complete_correct": not failures, "failures": failures,
        "duration_ms": float(result["duration_ms"]), "token_proxy": result["token_proxy"],
    }
    row["fingerprint"] = fingerprint(row)
    return row


def _distribution(values: Sequence[float]) -> dict[str, Any]:
    ordered = sorted(values)
    if not ordered:
        return {"count": 0, "min": None, "p50": None, "p95": None, "max": None, "mean": None}
    def percentile(fraction: float) -> float:
        return ordered[min(len(ordered) - 1, int((len(ordered) - 1) * fraction))]
    return {"count": len(ordered), "min": ordered[0], "p50": percentile(.5), "p95": percentile(.95), "max": ordered[-1], "mean": sum(ordered) / len(ordered)}


def _aggregate(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    complete = sum(bool(row["complete_correct"]) for row in rows)
    authority = sum(bool(row["checks"]["authoritative_refs"]["complete"]) for row in rows)
    statuses = sum(bool(row["checks"]["statuses"]["complete"]) for row in rows)
    citations = sum(bool(row["checks"]["citations"]["complete"]) for row in rows)
    related_leaks = sum(not bool(row["checks"]["related_safety"]["complete"]) for row in rows)
    missing = [row for row in rows if row["parent_task_id"] == "CTX-12"]
    # CTX-12 is a full negative-control answer, not merely a boolean abstain:
    # an unsupported ADR, citation, or explanation claim makes it fail.
    abstentions = sum(bool(row["complete_correct"]) for row in missing)
    gates = {
        "complete_correct": {"passing": complete, "required": QUERY_COUNT, "threshold": 54, "complete": len(rows) == QUERY_COUNT and complete >= 54},
        "authority": {"passing": authority, "required": QUERY_COUNT, "threshold": QUERY_COUNT, "complete": authority == QUERY_COUNT},
        "status": {"passing": statuses, "required": QUERY_COUNT, "threshold": QUERY_COUNT, "complete": statuses == QUERY_COUNT},
        "missing_evidence_abstention": {"passing": abstentions, "required": 5, "threshold": 5, "complete": len(missing) == 5 and abstentions == 5},
        "related_as_lineage": {"passing": related_leaks, "required": 0, "threshold": 0, "complete": related_leaks == 0},
        "resolvable_citations": {"passing": citations, "required": QUERY_COUNT, "threshold": QUERY_COUNT, "complete": citations == QUERY_COUNT},
    }
    return {
        "cell_count": len(rows), "complete_correct": complete, "gates": gates,
        "passing": len(rows) == QUERY_COUNT and all(value["complete"] for value in gates.values()),
        "failures_by_task_family": _family_failures(rows),
        "duration_ms": _distribution([float(row["duration_ms"]) for row in rows]),
        "token_proxy": _distribution([float(row["token_proxy"]) for row in rows]),
    }


def _family_failures(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        if row["failures"]:
            grouped[row["parent_task_id"]].extend(row["failures"])
    return [{"task_id": task_id, "failures": sorted(set(grouped[task_id]))} for task_id in sorted(grouped)]


def validate_judge_records(records: Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    """Accept explanation reviews as separate metadata; never score or gate them."""
    normalized: list[dict[str, Any]] = []
    for record in records or ():
        if not isinstance(record, Mapping) or record.get("schema") != JUDGE_SCHEMA:
            raise ValueError("explanation reviews must use lightweight-explanation-review.v1")
        if record.get("subject") not in SUBJECTS or not isinstance(record.get("query_id"), str):
            raise ValueError("explanation review identity is malformed")
        normalized.append(dict(record))
    return sorted(normalized, key=canonical_json)


def _empty_summary(arm: str) -> dict[str, Any]:
    """Preserve every denominator when a subject arm has intentionally not run."""
    gates = {
        "complete_correct": {"passing": 0, "required": QUERY_COUNT, "threshold": 54, "complete": False, "status": "not_evaluated"},
        "authority": {"passing": 0, "required": QUERY_COUNT, "threshold": QUERY_COUNT, "complete": False, "status": "not_evaluated"},
        "status": {"passing": 0, "required": QUERY_COUNT, "threshold": QUERY_COUNT, "complete": False, "status": "not_evaluated"},
        "missing_evidence_abstention": {"passing": 0, "required": 5, "threshold": 5, "complete": False, "status": "not_evaluated"},
        "related_as_lineage": {"passing": 0, "required": 0, "threshold": 0, "complete": False, "status": "not_evaluated"},
        "resolvable_citations": {"passing": 0, "required": QUERY_COUNT, "threshold": QUERY_COUNT, "complete": False, "status": "not_evaluated"},
    }
    summary = {"cell_count": 0, "complete_correct": 0, "gates": gates, "passing": False,
               "failures_by_task_family": [], "duration_ms": _distribution([]), "token_proxy": _distribution([])}
    if arm == "adr-constitution":
        summary["noninferior_to"] = {"decision-only": "not_evaluated", "adr-current": "not_evaluated"}
    return summary


def not_run_report(*, topk_aggregate: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Produce the explicit, non-vacuous report used before subject execution."""
    topk = _topk_input(topk_aggregate)
    result = {
        "schema": SCHEMA, "status": "not_run", "expected_cell_count": EXPECTED_CELL_COUNT,
        "observed_cell_count": 0, "exclusions": [{"reason": "no subject run artifacts"}],
        "topk": topk, "subjects": {subject: {arm: _empty_summary(arm) for arm in ARMS} for subject in SUBJECTS}, "recommendation": None,
        "minimum_capability_conclusion": "not_run: no minimum capability recommendation",
        "explanation_reviews": [],
    }
    result["fingerprint"] = fingerprint(result)
    return result


def _topk_input(topk_aggregate: Mapping[str, Any] | None) -> dict[str, Any]:
    """Keep the Task 2 K=1/3/5 result as validated input, never recomputed."""
    if topk_aggregate is None:
        return {"status": "not_provided", "reference": "validated Task 2 aggregate required"}
    if topk_aggregate.get("schema") != topk.SCHEMA or topk_aggregate.get("k_values") != list(topk.K_VALUES):
        raise ValueError("topk aggregate must be a validated Task 2 K=1/3/5 result")
    results = topk_aggregate.get("results")
    if not isinstance(results, Mapping) or set(results) != {"1", "3", "5"} or any(not isinstance(results[key], Mapping) for key in results):
        raise ValueError("topk aggregate must contain all Task 2 K shards")
    corpus, _rows = queries.load_query_variants()
    expected_passing: dict[int, bool] = {}
    for k in topk.K_VALUES:
        shard = results[str(k)]
        required = {"k", "cell_count", "query_corpus_fingerprint", "complete_query_recall", "critical_gates", "errors", "passing"}
        if not required <= set(shard) or shard.get("k") != k or shard.get("cell_count") != QUERY_COUNT or shard.get("query_corpus_fingerprint") != corpus["canonical_fingerprint"]:
            raise ValueError("topk aggregate contains an incomplete, non-canonical shard")
        recall = shard["complete_query_recall"]
        gates = shard["critical_gates"]
        if not isinstance(recall, Mapping) or set(recall) != {"passing", "required", "threshold", "rate", "complete"} or recall.get("required") != QUERY_COUNT or recall.get("threshold") != 57 or not isinstance(recall.get("passing"), int) or isinstance(recall.get("passing"), bool) or not 0 <= recall["passing"] <= QUERY_COUNT or not isinstance(recall.get("rate"), (int, float)) or recall["rate"] != recall["passing"] / QUERY_COUNT or recall.get("complete") is not (recall["passing"] >= 57) or not isinstance(gates, Mapping) or set(gates) != set(topk.CRITICAL_DIMENSIONS):
            raise ValueError("topk aggregate lacks Task 2 recall or critical-gate denominators")
        semantic_errors: set[str] = set()
        if not recall["complete"]:
            semantic_errors.add("complete-query-recall")
        for name in topk.CRITICAL_DIMENSIONS:
            gate = gates[name]
            if not isinstance(gate, Mapping) or set(gate) != {"applicable", "passing", "required", "complete"} or not all(isinstance(gate[field], int) and not isinstance(gate[field], bool) and gate[field] >= 0 for field in ("applicable", "passing", "required")) or gate["passing"] > gate["required"] or not isinstance(gate["complete"], bool) or gate["required"] != gate["applicable"] or gate["complete"] is not (bool(gate["applicable"]) and gate["passing"] == gate["applicable"]):
                raise ValueError("topk aggregate has a malformed Task 2 critical gate")
            if not gate["complete"]:
                semantic_errors.add(f"{name}-gate")
        expected = bool(shard.get("passing"))
        if bool(shard.get("passing")) != (not shard.get("errors")):
            raise ValueError("topk aggregate passing flag is inconsistent")
        if semantic_errors and not semantic_errors <= set(shard["errors"]):
            raise ValueError("topk aggregate suppresses a semantic Task 2 failure")
        if semantic_errors and expected:
            raise ValueError("topk aggregate marks a semantic Task 2 failure as passing")
        expected_passing[k] = expected
    if topk_aggregate.get("ranking_arm") != "production-default":
        raise ValueError("topk aggregate must be production-default, not diagnostic")
    recommended = next((k for k in topk.K_VALUES if expected_passing[k]), None) if expected_passing[5] else None
    if topk_aggregate.get("recommended_k") != recommended:
        raise ValueError("topk aggregate recommendation is inconsistent with Task 2 gates")
    stable = {key: value for key, value in topk_aggregate.items() if key != "fingerprint"}
    if topk_aggregate.get("fingerprint") != fingerprint(stable):
        raise ValueError("topk aggregate fingerprint mismatch")
    return dict(topk_aggregate)


def score_experiment(
    result_manifests: Sequence[Mapping[str, Any]], packet_manifests: Sequence[Mapping[str, Any]], *,
    query_rows: Sequence[Mapping[str, Any]] | None = None, gold_rows: Sequence[Mapping[str, Any]] | None = None,
    topk_aggregate: Mapping[str, Any] | None = None, judge_records: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Validate and reduce the frozen 360-cell experiment without executing it."""
    if not result_manifests:
        if packet_manifests:
            validate_packet_manifests(packet_manifests, query_rows or queries.load_query_variants()[1])
        return not_run_report(topk_aggregate=topk_aggregate)
    _corpus, expected_rows = queries.load_query_variants()
    rows = _canonical_frozen_rows(query_rows or expected_rows)
    corpus, joined = queries.load_query_variants()[0], queries.join_queries_to_gold()
    gold_by_parent = {query["parent_task_id"]: gold for query, gold in joined}
    if gold_rows is not None:
        supplied = {str(row.get("task_id")): row for row in gold_rows if isinstance(row, Mapping)}
        if supplied != gold_by_parent:
            raise ValueError("scoring gold must be the frozen v2 parent-task gold")
    packets = validate_packet_manifests(packet_manifests, rows)
    expected = {(row["query_id"], arm, subject) for row in rows for arm in ARMS for subject in SUBJECTS}
    seen: set[tuple[str, str, str]] = set()
    pin_fingerprint_by_subject: dict[str, str] = {}
    cells: list[dict[str, Any]] = []
    for result in result_manifests:
        if not isinstance(result, Mapping):
            raise ValueError("result manifests must be objects")
        key = (str(result.get("query_id")), str(result.get("arm")), str(result.get("subject")))
        if key in seen:
            raise ValueError(f"duplicate result cell: {key}")
        seen.add(key)
        if key not in expected:
            raise ValueError("result cell is extra or cross-corpus")
        query = next(row for row in rows if row["query_id"] == key[0])
        packet = packets[(key[0], key[1])]
        _validate_result_manifest(result, query=query, packet=packet, corpus_fingerprint=corpus["canonical_fingerprint"])
        pinned = result["pin_fingerprint"]
        prior = pin_fingerprint_by_subject.setdefault(key[2], pinned)
        if prior != pinned:
            raise ValueError("subject runtime pin drift across result cells")
        cells.append(score_cell(result, gold_by_parent[key[0].split(".")[0]], {"query": packet["query"], **packet["evidence"]}))
    if len(cells) != EXPECTED_CELL_COUNT or seen != expected:
        raise ValueError("results must contain exactly the 360 frozen cells")
    cells.sort(key=lambda row: (row["subject"], row["arm"], row["query_id"]))
    summaries: dict[str, dict[str, Any]] = {}
    for subject in SUBJECTS:
        summaries[subject] = {}
        for arm in ARMS:
            summary = _aggregate([row for row in cells if row["subject"] == subject and row["arm"] == arm])
            summaries[subject][arm] = summary
        constitution = summaries[subject]["adr-constitution"]
        noninferior = {
            arm: constitution["complete_correct"] >= summaries[subject][arm]["complete_correct"]
            for arm in ("decision-only", "adr-current")
        }
        constitution["noninferior_to"] = noninferior
        constitution["passing"] = constitution["passing"] and all(noninferior.values())
    recommendation = "adr-constitution" if all(summaries[subject]["adr-constitution"]["passing"] for subject in SUBJECTS) else None
    result = {
        "schema": SCHEMA, "status": "scored", "expected_cell_count": EXPECTED_CELL_COUNT,
        "observed_cell_count": len(cells), "query_corpus_fingerprint": corpus["canonical_fingerprint"],
        "topk": _topk_input(topk_aggregate),
        "subjects": summaries, "recommendation": recommendation,
        "minimum_capability_conclusion": "both local and luna satisfy adr-constitution gates" if recommendation else "no recommendation: at least one independent subject gate failed",
        "exclusions": [], "explanation_reviews": validate_judge_records(judge_records),
    }
    result["fingerprint"] = fingerprint(result)
    return result


def render_markdown(result: Mapping[str, Any]) -> str:
    """Render a stable human summary without changing the JSON result."""
    lines = ["# Lightweight context-derivation results", "", f"Status: `{result['status']}`", "", f"Minimum capability conclusion: {result['minimum_capability_conclusion']}", "", "| Subject | Arm | Complete | Authority | Status | Missing evidence | Related leaks | Citations | Non-inferiority |", "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for subject in SUBJECTS:
        for arm in ARMS:
            summary = (result.get("subjects") or {}).get(subject, {}).get(arm)
            if summary is None:
                continue
            gates = summary["gates"]
            noninferiority = summary.get("noninferior_to", "n/a")
            lines.append("| {} | {} | {}/{} (threshold {}) | {}/{} | {}/{} | {}/{} | {}/0 | {}/{} | {} |".format(
                subject, arm, gates["complete_correct"]["passing"], gates["complete_correct"]["required"], gates["complete_correct"]["threshold"],
                gates["authority"]["passing"], gates["authority"]["required"], gates["status"]["passing"], gates["status"]["required"],
                gates["missing_evidence_abstention"]["passing"], gates["missing_evidence_abstention"]["required"],
                gates["related_as_lineage"]["passing"], gates["resolvable_citations"]["passing"], gates["resolvable_citations"]["required"], canonical_json(noninferiority) if isinstance(noninferiority, Mapping) else noninferiority,
            ))
    lines.extend(["", "## Task-family failures and distributions", ""])
    for subject in SUBJECTS:
        for arm in ARMS:
            summary = (result.get("subjects") or {}).get(subject, {}).get(arm)
            if summary is not None:
                lines.append(f"- {subject}/{arm}: failures={canonical_json(summary['failures_by_task_family'])}; duration_ms={canonical_json(summary['duration_ms'])}; token_proxy={canonical_json(summary['token_proxy'])}")
    lines.extend(["", "## Retrieval input", "", canonical_json(result["topk"]), "", "## Exclusions", ""])
    for exclusion in result.get("exclusions", []):
        lines.append("- " + canonical_json(exclusion))
    return "\n".join(lines) + "\n"


def write_reports(result: Mapping[str, Any], json_path: str | Path, markdown_path: str | Path) -> tuple[Path, Path]:
    """Write byte-stable JSON and Markdown reports from an already-scored result."""
    json_output, markdown_output = Path(json_path), Path(markdown_path)
    json_output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_output.write_text(render_markdown(result), encoding="utf-8")
    return json_output, markdown_output

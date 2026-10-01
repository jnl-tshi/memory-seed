"""Offline, review-gated comparison harness for semantic recovery experiments.

No model calls are made here. The module freezes evidence and configuration,
validates externally supplied responses through SemanticState, and keeps gold
material behind a separate blinded review packet.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

from hosted.capture.semantic import PROMPT_VERSION, SemanticState


DATASET_SCHEMA = "recovery-dataset-v1"
RUN_SCHEMA = "recovery-run-v1"
PACKET_SCHEMA = "recovery-review-packets-v1"
_REVIEW_FIELDS = ("issue", "selected_action", "scope", "agreement_quote", "reason", "conditions", "deciding_actor")


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("value is not JSON-compatible") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _seal(value: dict, field: str) -> dict:
    result = deepcopy(value)
    result.pop(field, None)
    result[field] = _digest(result)
    return result


def _check_seal(value: Any, field: str, label: str) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get(field), str):
        raise ValueError(f"{label} integrity hash is missing")
    expected = value[field]
    material = deepcopy(value)
    material.pop(field)
    if _digest(material) != expected:
        raise ValueError(f"{label} integrity hash mismatch")
    return value


def _resolve_roots(lineage: Any) -> dict[str, str]:
    if not isinstance(lineage, dict):
        raise ValueError("lineage must be an object")
    sessions: dict[str, str | None] = {}
    rollouts: dict[str, str] = {}
    for rollout, item in lineage.items():
        if not isinstance(rollout, str) or not rollout or not isinstance(item, dict):
            raise ValueError("lineage entries must map rollout IDs to objects")
        session = item.get("session_id")
        parent = item.get("parent_session_id")
        if not isinstance(session, str) or not session:
            raise ValueError("lineage session_id must be nonempty")
        if parent is not None and (not isinstance(parent, str) or not parent):
            raise ValueError("lineage parent_session_id must be nonempty or null")
        if session in sessions:
            raise ValueError("conflicting lineage identity")
        sessions[session] = parent
        rollouts[rollout] = session

    roots: dict[str, str] = {}
    for rollout, session in rollouts.items():
        seen: set[str] = set()
        current = session
        while True:
            if current in seen:
                raise ValueError("lineage cycle detected")
            seen.add(current)
            if current not in sessions:
                # Incomplete diagnostic lineage is represented as unavailable;
                # it cannot establish a root or fresh-data eligibility.
                break
            parent = sessions[current]
            if parent is None:
                roots[rollout] = current
                break
            current = parent
    return roots


def _source_reviews(case: dict) -> tuple[bool, list[str]]:
    reviews = case.get("source_reviews")
    if not isinstance(reviews, list) or len(reviews) != 2:
        return False, ["source review unavailable or not exactly two reviewers"]
    ids: list[str] = []
    reasons: list[str] = []
    for item in reviews:
        if not isinstance(item, dict) or not isinstance(item.get("reviewer_id"), str) or not item["reviewer_id"]:
            reasons.append("source review identity unavailable")
            continue
        ids.append(item["reviewer_id"])
        if type(item.get("supported")) is not bool:
            reasons.append("source support review unavailable")
        if type(item.get("real_negative")) is not bool:
            reasons.append("real-negative review unavailable")
    if len(ids) != 2 or len(set(ids)) != 2:
        reasons.append("source reviewers are not independent")
    if len(reviews) == 2 and all(isinstance(r, dict) for r in reviews):
        if any(r.get("supported") is not True for r in reviews):
            reasons.append("source case is not independently supported")
        if case.get("kind") == "negative" and any(r.get("real_negative") is not True for r in reviews):
            reasons.append("negative is not independently confirmed as real")
        if case.get("kind") == "positive" and any(r.get("real_negative") is not False for r in reviews):
            reasons.append("positive is inconsistently labeled as a real negative")
    return not reasons, reasons


def freeze_dataset(dataset: dict, model_config: dict) -> dict:
    """Validate and freeze source data, preserving order behind opaque case IDs."""
    if not isinstance(dataset, dict) or not isinstance(dataset.get("cases"), list):
        raise ValueError("dataset.cases must be a list")
    if not isinstance(model_config, dict) or not isinstance(model_config.get("model"), str) or not model_config["model"]:
        raise ValueError("model_config.model must be nonempty")
    if not isinstance(model_config.get("reasoning_effort"), str) or not model_config["reasoning_effort"]:
        raise ValueError("model_config.reasoning_effort must be nonempty")
    roots = _resolve_roots(dataset.get("lineage", {}))
    prior = dataset.get("previously_examined_roots", [])
    if not isinstance(prior, list) or any(not isinstance(x, str) or not x for x in prior):
        raise ValueError("previously_examined_roots must be a list of root IDs")
    if type(dataset.get("exposure_audit_complete")) is not bool:
        raise ValueError("exposure_audit_complete must be boolean")

    seen: set[str] = set()
    frozen_cases: list[dict] = []
    reasons: list[str] = []
    counts = {"fresh_supported_positive": 0, "fresh_reviewed_real_negative": 0}
    split_by_root: dict[str, set[str]] = {}
    for index, raw in enumerate(dataset["cases"], 1):
        if not isinstance(raw, dict):
            raise ValueError("case must be an object")
        cid = raw.get("case_id")
        if not isinstance(cid, str) or not cid or cid in seen:
            raise ValueError("case_id must be nonempty and unique")
        seen.add(cid)
        split, kind = raw.get("split"), raw.get("kind")
        if split not in {"development", "regression", "fresh"} or kind not in {"positive", "negative"}:
            raise ValueError("case split or kind is invalid")
        messages = raw.get("messages")
        if not isinstance(messages, list):
            raise ValueError("case messages must be a list")
        gold = raw.get("gold_record")
        if not isinstance(gold, dict) or not gold:
            raise ValueError("gold_record must be a nonempty object")
        if kind == "positive" and not any(value not in (None, "", [], {}) for value in gold.values()):
            raise ValueError("positive gold_record must contain a supported reference")
        if kind == "negative" and not any(key in gold for key in ("no_decision_rationale", "rationale", "reason")):
            raise ValueError("negative gold_record must include an explicit no-decision rationale")
        local_roots: set[str] = set()
        for message in messages:
            if not isinstance(message, dict) or not isinstance(message.get("rollout_id"), str):
                raise ValueError("case message rollout_id is required")
            root = roots.get(message["rollout_id"])
            if root is not None:
                local_roots.add(root)
        if len(local_roots) > 1:
            # A case may intentionally join linked roots only when those roots resolve identically.
            raise ValueError("case messages resolve to conflicting roots")
        root = next(iter(local_roots), None)
        lineage_ok = bool(messages) and root is not None and all(m.get("rollout_id") in roots for m in messages)
        review_ok, review_reasons = _source_reviews(raw)
        if not lineage_ok:
            review_reasons.append("lineage unavailable for one or more messages")
        if split == "fresh" and root in prior:
            review_reasons.append("fresh root was previously examined")
        if split == "fresh" and root:
            split_by_root.setdefault(root, set()).add(split)
        if split == "fresh" and review_ok and lineage_ok and root not in prior:
            if kind == "positive":
                counts["fresh_supported_positive"] += 1
            elif all(r.get("real_negative") is True for r in raw["source_reviews"]):
                counts["fresh_reviewed_real_negative"] += 1
        reasons.extend(f"{cid}: {reason}" for reason in review_reasons)
        item = deepcopy(raw)
        item.update({"opaque_case_id": f"case-{index:04d}", "root_id": root,
                     "lineage_available": lineage_ok, "source_review_available": review_ok})
        frozen_cases.append(item)

    split_by_root.clear()
    for item in frozen_cases:
        if item["root_id"]:
            split_by_root.setdefault(item["root_id"], set()).add(item["split"])
    for root, splits in split_by_root.items():
        if "fresh" in splits and ("development" in splits or "regression" in splits):
            reasons.append(f"root {root}: fresh data overlaps development or regression")
    if dataset["exposure_audit_complete"] is not True:
        reasons.append("exposure audit unavailable")
    if counts["fresh_supported_positive"] < 30:
        reasons.append("fewer than 30 supported fresh positives")
    if counts["fresh_reviewed_real_negative"] < 30:
        reasons.append("fewer than 30 reviewed real negatives")
    eligibility = {"eligible": not reasons, "reasons": sorted(set(reasons)), "counts": counts,
                   "exposure_audit_complete": dataset["exposure_audit_complete"]}
    model_copy = deepcopy(model_config)
    config_id = _digest({"model_config": model_copy, "prompt_version": PROMPT_VERSION})
    material = {"schema_version": DATASET_SCHEMA, "prompt_version": PROMPT_VERSION,
                "model_config": model_copy, "config_id": config_id,
                "lineage": deepcopy(dataset["lineage"]), "previously_examined_roots": deepcopy(prior),
                "cases": frozen_cases, "eligibility": eligibility}
    return _seal(material, "dataset_hash")


def _checked_frozen(frozen: dict) -> dict:
    _check_seal(frozen, "dataset_hash", "dataset")
    if frozen.get("schema_version") != DATASET_SCHEMA:
        raise ValueError("unsupported frozen dataset schema")
    if frozen.get("config_id") != _digest({"model_config": frozen.get("model_config"), "prompt_version": PROMPT_VERSION}):
        raise ValueError("frozen config integrity mismatch")
    return frozen


def extraction_packets(frozen: dict) -> list[dict]:
    frozen = _checked_frozen(frozen)
    packets = []
    for case in frozen["cases"]:
        state = SemanticState(frozen["config_id"])
        request = state.make_request(deepcopy(case["messages"]), deepcopy(case.get("marker")))
        packets.append({"case_id": case["opaque_case_id"], "request": request})
    return packets


def _run_material(run: dict) -> dict:
    material = deepcopy(run)
    material.pop("run_hash", None)
    return material


def import_run(frozen: dict, run_id: str, responses: dict) -> dict:
    frozen = _checked_frozen(frozen)
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("run_id must be nonempty")
    if not isinstance(responses, dict):
        raise ValueError("responses must map opaque case IDs to responses")
    packets = extraction_packets(frozen)
    valid_keys = {p["case_id"] for p in packets}
    extras = set(responses) - valid_keys
    if extras:
        raise ValueError("extra or unknown response case IDs")
    cases = []
    for packet in packets:
        case_id, request = packet["case_id"], packet["request"]
        if case_id not in responses:
            cases.append({"case_id": case_id, "status": "unavailable", "candidates": [], "error": "response unavailable"})
            continue
        state = SemanticState(frozen["config_id"])
        try:
            state.make_request(request["messages"], request.get("marker"))
            candidates = state.accept_response(request, responses[case_id])
            cases.append({"case_id": case_id, "status": "valid", "candidates": candidates})
        except (ValueError, TypeError, KeyError) as exc:
            cases.append({"case_id": case_id, "status": "invalid", "candidates": [], "error": str(exc)})
    material = {"schema_version": RUN_SCHEMA, "dataset_hash": frozen["dataset_hash"],
                "config_id": frozen["config_id"], "run_id": run_id, "cases": cases}
    return _seal(material, "run_hash")


def _checked_run(frozen: dict, run: dict) -> dict:
    _check_seal(run, "run_hash", "run")
    if run.get("schema_version") != RUN_SCHEMA or run.get("dataset_hash") != frozen["dataset_hash"] or run.get("config_id") != frozen["config_id"]:
        raise ValueError("run does not match frozen dataset/config")
    expected = [c["opaque_case_id"] for c in frozen["cases"]]
    if [c.get("case_id") for c in run.get("cases", [])] != expected:
        raise ValueError("run case coverage mismatch")
    return run


def _checked_control(frozen: dict, control: dict) -> dict:
    _check_seal(control, "run_hash", "control run")
    expected = [c["opaque_case_id"] for c in frozen["cases"]]
    if (control.get("schema_version") != RUN_SCHEMA or control.get("run_type") != "pinned-control"
            or control.get("dataset_hash") != frozen["dataset_hash"]
            or control.get("config_id") != frozen["config_id"]
            or control.get("revision") != "95514648be7dae6652d217fd8bfbcade897e19d3"
            or [c.get("case_id") for c in control.get("cases", [])] != expected):
        raise ValueError("control run does not match frozen pinned baseline")
    return control


def review_packets(frozen: dict, runs: list[dict], control: dict | None = None) -> dict:
    frozen = _checked_frozen(frozen)
    if not isinstance(runs, list) or len(runs) != 2:
        raise ValueError("exactly two semantic runs are required")
    for run in runs:
        _checked_run(frozen, run)
    if len({r["run_id"] for r in runs}) != 2:
        raise ValueError("run IDs must be distinct and independent")
    if control is not None:
        _checked_control(frozen, control)
    items = []
    key_items = []
    # Interleave by opaque case ID and arm; only this scorer key reveals the mapping.
    for ci, source_case in enumerate(frozen["cases"]):
        arms = [(f"arm-{ri+1}", run, run["cases"][ci]) for ri, run in enumerate(runs)]
        if control is not None:
            arms.append(("arm-control", control, control["cases"][ci]))
        for arm, run, result in arms:
            item_id = f"review-{len(items)+1:04d}"
            local_candidates = []
            candidate_map = {}
            for candidate_index, candidate in enumerate(result.get("candidates", []), 1):
                local_id = f"candidate-{candidate_index:04d}"
                candidate_map[local_id] = candidate.get("candidate_id")
                local = {key: deepcopy(candidate[key]) for key in (
                    "issue", "selected_action", "scope", "agreement_quote", "reason", "conditions",
                    "deciding_actor", "state", "unresolved_references", "complete",
                ) if key in candidate}
                # Same reviewer-visible shape in both arms; never leak semantic
                # validator flags or parser-only metadata as an arm label.
                local["field_evidence"] = deepcopy(candidate.get("field_evidence"))
                local["source_evidence"] = deepcopy(candidate.get("source_evidence"))
                local["candidate_id"] = local_id
                local_candidates.append(local)
            items.append({"item_id": item_id, "output_hash": run["run_hash"],
                          "status": result["status"],
                          "messages": deepcopy(source_case["messages"]),
                          "gold_record": deepcopy(source_case["gold_record"]),
                          "candidates": local_candidates})
            key_items.append({"item_id": item_id, "arm": arm,
                              "case_id": source_case["opaque_case_id"],
                              "run_hash": run["run_hash"], "candidate_ids": candidate_map})
    packet_material = {"schema_version": PACKET_SCHEMA, "dataset_hash": frozen["dataset_hash"], "items": items}
    packet_hash = _digest(packet_material)
    packet = {**packet_material, "packet_hash": packet_hash}
    return {"schema_version": PACKET_SCHEMA, "dataset_hash": frozen["dataset_hash"],
            "packet_hash": packet_hash, "packets": items,
            "key": {"dataset_hash": frozen["dataset_hash"],
                    "packet_hash": packet_hash, "items": key_items}}


def _normalized_source(repo: str | os.PathLike, relative: str, revision: str) -> tuple[bytes, str]:
    raw = subprocess.check_output(["git", "show", f"{revision}:{relative}"], cwd=repo)
    normalized = raw.replace(b"\r\n", b"\n")
    current = (Path(repo) / relative).read_bytes().replace(b"\r\n", b"\n")
    if current != normalized:
        raise ValueError(f"control baseline source differs from pinned {revision}:{relative}")
    return normalized, hashlib.sha256(normalized).hexdigest()


def frozen_control(frozen: dict, repo: str | os.PathLike) -> dict:
    """Run the pinned rules parser over the exact frozen messages and marker."""
    frozen = _checked_frozen(frozen)
    revision = "95514648be7dae6652d217fd8bfbcade897e19d3"
    _, parser_hash = _normalized_source(repo, "hosted/capture/parser.py", revision)
    _, incremental_hash = _normalized_source(repo, "hosted/capture/incremental.py", revision)
    from hosted.capture.parser import DecisionParser
    from hosted.evaluation.paired_replay import cue_marker

    parser = DecisionParser()
    controls = []
    for case_data in frozen["cases"]:
        messages = deepcopy(case_data["messages"])
        if not messages:
            controls.append({"case_id": case_data["opaque_case_id"], "status": "valid", "candidates": [],
                             "evidence_mode": "oracle_selected_evidence_reconstruction"})
            continue
        rollout = case_data.get("rollout_id") or messages[-1]["rollout_id"]
        primary = [m for m in messages if m["rollout_id"] == rollout]
        parents = [m for m in messages if m["rollout_id"] != rollout]
        marker = deepcopy(case_data.get("marker"))
        if marker is None:
            anchor = max(primary, key=lambda m: (m.get("turn", -1), m.get("source_ordinal", -1)))
            marker = cue_marker(anchor, oracle=True)
        raw_candidates = parser.parse_stepped(rollout, primary, marker=marker, lineage_messages=parents)
        normalized_candidates = []
        for raw in raw_candidates:
            item = {key: deepcopy(raw[key]) for key in (
                "issue", "selected_action", "scope", "agreement_quote", "reason", "conditions", "deciding_actor"
            ) if key in raw}
            item["candidate_id"] = "control_" + _digest({"case_id": case_data["opaque_case_id"],
                                                        "source": raw.get("source", {}).get("source_coordinates"),
                                                        "candidate": item})[:24]
            item["complete"] = bool(raw.get("complete") and all(item.get(f) not in (None, "", [])
                                                                   for f in ("issue", "selected_action", "scope", "agreement_quote")))
            item["source_evidence"] = {"coordinates": deepcopy(raw.get("source", {}).get("source_coordinates", [])),
                                       "messages": deepcopy(raw.get("source", {}).get("messages", []))}
            normalized_candidates.append(item)
        controls.append({"case_id": case_data["opaque_case_id"], "status": "valid",
                         "candidates": normalized_candidates,
                         "evidence_mode": "oracle_selected_evidence_reconstruction"})
    material = {"schema_version": RUN_SCHEMA, "run_type": "pinned-control",
                "dataset_hash": frozen["dataset_hash"], "config_id": frozen["config_id"],
                "run_id": "pinned-rules-control-95514648", "revision": revision,
                "parser_backend": parser.backend,
                "file_hashes": {"hosted/capture/parser.py": parser_hash,
                                "hosted/capture/incremental.py": incremental_hash},
                "evidence_mode": "oracle_selected_evidence_reconstruction", "cases": controls}
    return _seal(material, "run_hash")


def _validate_reviews(packet: dict, reviews: list[dict]) -> tuple[list[dict], dict[str, dict]]:
    if not isinstance(reviews, list) or len(reviews) != 2:
        raise ValueError("exactly two independent review documents are required")
    ids = [r.get("reviewer_id") if isinstance(r, dict) else None for r in reviews]
    if any(not isinstance(x, str) or not x for x in ids) or len(set(ids)) != 2:
        raise ValueError("reviewer IDs must be distinct and independent")
    by_reviewer = []
    item_ids = {i["item_id"] for i in packet["items"]}
    for doc in reviews:
        if doc.get("packet_hash") != packet["packet_hash"]:
            raise ValueError("review packet hash mismatch")
        rows = doc.get("items")
        if not isinstance(rows, list) or {r.get("item_id") for r in rows if isinstance(r, dict)} != item_ids or len(rows) != len(item_ids):
            raise ValueError("each review must cover every item exactly once")
        rowmap = {r["item_id"]: r for r in rows}
        normalized: dict[str, dict] = {}
        for item in packet["items"]:
            row = rowmap[item["item_id"]]
            if set(row) != {"item_id", "candidate_judgments"}:
                raise ValueError("review item has unknown or missing fields")
            judgments = row.get("candidate_judgments")
            candidates = item["candidates"]
            if not isinstance(judgments, list) or len(judgments) != len(candidates):
                raise ValueError("candidate review coverage mismatch")
            jmap = {j.get("candidate_id"): j for j in judgments if isinstance(j, dict)}
            if len(jmap) != len(judgments) or set(jmap) != {c.get("candidate_id") for c in candidates}:
                raise ValueError("candidate review IDs mismatch")
            clean = {}
            for candidate in candidates:
                j = jmap[candidate["candidate_id"]]
                if set(j) != {"candidate_id", "complete_match", "false_acceptance", "wrong_actor", "field_checks", "rationale"}:
                    raise ValueError("candidate judgment has unknown or missing fields")
                if type(j.get("complete_match")) is not bool or type(j.get("false_acceptance")) is not bool or type(j.get("wrong_actor")) is not bool:
                    raise ValueError("review judgments require boolean decisions")
                checks = j.get("field_checks")
                if not isinstance(checks, dict) or set(checks) != set(_REVIEW_FIELDS) or any(type(checks[k]) is not bool for k in checks):
                    raise ValueError("field_checks must contain seven booleans")
                if not isinstance(j.get("rationale"), str) or not j["rationale"].strip():
                    raise ValueError("review rationale must be nonempty")
                errors = any(j[k] for k in ("false_acceptance", "wrong_actor"))
                complete = bool(j["complete_match"] and all(checks.values()) and candidate.get("complete") is True and not errors)
                clean[candidate["candidate_id"]] = {"complete": complete, "complete_match_vote": j["complete_match"],
                                                     "false_acceptance": j["false_acceptance"],
                                                     "wrong_actor": j["wrong_actor"],
                                                     "field_checks": deepcopy(checks)}
            normalized[item["item_id"]] = clean
        by_reviewer.append(normalized)
    merged: dict[str, dict] = {}
    for item in packet["items"]:
        item_id = item["item_id"]
        a, b = by_reviewer[0][item_id], by_reviewer[1][item_id]
        merged[item_id] = {}
        for cid in a:
            conflict = any(a[cid][key] != b[cid][key]
                           for key in ("complete_match_vote", "false_acceptance", "wrong_actor", "field_checks"))
            merged[item_id][cid] = {"complete": a[cid]["complete"] and b[cid]["complete"] and not conflict,
                                    "conflict": conflict,
                                    "false_acceptance": a[cid]["false_acceptance"] or b[cid]["false_acceptance"],
                                    "wrong_actor": a[cid]["wrong_actor"] or b[cid]["wrong_actor"]}
    return packet["items"], merged


def score(frozen: dict, runs: list[dict], reviews: list[dict], control: dict | None = None) -> dict:
    """Score two frozen runs after two independent reviews; only fresh data gates."""
    frozen = _checked_frozen(frozen)
    if not isinstance(runs, list) or len(runs) != 2:
        raise ValueError("exactly two semantic runs are required")
    for run in runs:
        _checked_run(frozen, run)
    review_bundle = review_packets(frozen, runs, control)
    packet = {"schema_version": PACKET_SCHEMA, "dataset_hash": frozen["dataset_hash"],
              "items": review_bundle["packets"]}
    packet["packet_hash"] = _digest(packet)
    # review_packets hashes material before packet_hash, so reconstruct exactly.
    packet["packet_hash"] = _digest({"schema_version": PACKET_SCHEMA,
                                      "dataset_hash": frozen["dataset_hash"], "items": review_bundle["packets"]})
    items, judgments = _validate_reviews(packet, reviews)
    key_by_item = {x["item_id"]: x for x in review_bundle["key"]["items"]}
    item_by_id = {x["item_id"]: x for x in items}
    reports = []
    total_invalid = False
    hard_failure = False

    def summarize(arm: str, run: dict, *, gate_arm: bool) -> dict:
        nonlocal total_invalid, hard_failure
        run_cases = {c["case_id"]: c for c in run["cases"]}
        per_split: dict[str, dict] = {}
        for split in ("development", "regression", "fresh"):
            split_cases = [c for c in frozen["cases"] if c["split"] == split]
            outputs = correct_outputs = positive_cases = recovered_cases = 0
            false_acceptance = wrong_actor = conflicts = negative_outputs = 0
            case_rows = []
            for source_case in split_cases:
                cid = source_case["opaque_case_id"]
                run_case = run_cases[cid]
                if run_case.get("status") != "valid" and gate_arm:
                    total_invalid = True
                key_row = next(x for x in key_by_item.values() if x["case_id"] == cid and x["arm"] == arm)
                item = item_by_id[key_row["item_id"]]
                candidate_reviews = judgments[item["item_id"]]
                n_outputs = len(item["candidates"])
                outputs += n_outputs
                positive = source_case["kind"] == "positive"
                if positive:
                    positive_cases += 1
                else:
                    negative_outputs += n_outputs
                complete_values = [candidate_reviews.get(candidate["candidate_id"], {}).get("complete", False)
                                   for candidate in item["candidates"]]
                correct_case = bool(positive and any(complete_values))
                if correct_case:
                    recovered_cases += 1
                    correct_outputs += 1  # at most one correct recovery per positive case
                false_acceptance += n_outputs if not positive else sum(
                    j["false_acceptance"] for j in candidate_reviews.values())
                wrong_actor += sum(j["wrong_actor"] for j in candidate_reviews.values())
                conflicts += sum(j["conflict"] for j in candidate_reviews.values())
                if gate_arm and ((not positive and n_outputs) or any(
                        j["false_acceptance"] or j["wrong_actor"] for j in candidate_reviews.values())):
                    hard_failure = True
                case_rows.append({"case_id": cid, "status": run_case.get("status"), "outputs": n_outputs,
                                  "correct_unique_complete": int(correct_case)})
            per_split[split] = {
                "cases": len(split_cases), "positive_cases": positive_cases,
                "recovered_positive_cases": recovered_cases,
                "recovery": recovered_cases / positive_cases if positive_cases else None,
                "total_outputs": outputs, "correct_unique_complete": correct_outputs,
                "precision": correct_outputs / outputs if outputs else None,
                "negative_output_false_positives": negative_outputs,
                "false_acceptance": false_acceptance, "wrong_actor": wrong_actor,
                "conflicts": conflicts, "case_results": case_rows,
            }
        fresh = per_split["fresh"]
        return {"run_id": run["run_id"], "splits": per_split,
                "fresh_positive_cases": fresh["positive_cases"],
                "recovered_positive_cases": fresh["recovered_positive_cases"],
                "recovery": fresh["recovery"], "total_outputs": fresh["total_outputs"],
                "correct_unique_complete": fresh["correct_unique_complete"],
                "precision": fresh["precision"], "false_acceptance": fresh["false_acceptance"],
                "wrong_actor": fresh["wrong_actor"], "conflicts": fresh["conflicts"]}

    for index, run in enumerate(runs, 1):
        reports.append(summarize(f"arm-{index}", run, gate_arm=True))
    control_report = None
    if control is not None:
        _checked_control(frozen, control)
        control_report = summarize("arm-control", control, gate_arm=False)
        control_report.update({"revision": control.get("revision"), "backend": control.get("parser_backend"),
                               "file_hashes": control.get("file_hashes"),
                               "evidence_mode": control.get("evidence_mode")})
    reasons = list(frozen["eligibility"]["reasons"])
    if total_invalid:
        reasons.append("one or more run cases are invalid or unavailable")
    if hard_failure:
        reasons.append("negative output, false acceptance, or wrong actor observed")
    if any(r["conflicts"] for r in reports):
        reasons.append("review conflict observed")
    threshold_ok = all(r["recovery"] is not None and r["recovery"] >= .80 and
                       r["precision"] is not None and r["precision"] >= .95 for r in reports)
    passed = frozen["eligibility"]["eligible"] and not reasons and threshold_ok
    inconclusive = not frozen["eligibility"]["eligible"] or total_invalid
    status = "pass" if passed else "inconclusive" if inconclusive else "fail"
    return {"schema_version": "recovery-score-v1", "dataset_hash": frozen["dataset_hash"],
            "gate": {"status": status, "passed": passed, "reasons": sorted(set(reasons)),
                     "thresholds": {"recovery": .80, "precision": .95, "false_acceptance": 0,
                                    "wrong_actor": 0, "review_conflicts": 0}},
            "runs": reports, "control": control_report}


def _read(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as stream:
        return json.load(stream)


def _write(path: str, value: Any) -> None:
    target = Path(path)
    data = _canonical(value) + "\n"
    if target.exists():
        if target.read_text(encoding="utf-8") == data:
            return
        raise FileExistsError(f"refusing to overwrite different content: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create prevents racing writers from replacing another result.
    with target.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    p = subs.add_parser("freeze"); p.add_argument("--dataset", required=True); p.add_argument("--model-config", required=True); p.add_argument("--output", required=True)
    p = subs.add_parser("requests"); p.add_argument("--frozen", required=True); p.add_argument("--output", required=True)
    p = subs.add_parser("import-run"); p.add_argument("--frozen", required=True); p.add_argument("--run-id", required=True); p.add_argument("--responses", required=True); p.add_argument("--output", required=True)
    p = subs.add_parser("control"); p.add_argument("--frozen", required=True); p.add_argument("--repo", required=True); p.add_argument("--output", required=True)
    p = subs.add_parser("review-packets"); p.add_argument("--frozen", required=True); p.add_argument("--runs", nargs=2, required=True); p.add_argument("--control"); p.add_argument("--output", required=True)
    p = subs.add_parser("score"); p.add_argument("--frozen", required=True); p.add_argument("--runs", nargs=2, required=True); p.add_argument("--reviews", nargs=2, required=True); p.add_argument("--control"); p.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    if args.command == "freeze": result = freeze_dataset(_read(args.dataset), _read(args.model_config))
    elif args.command == "requests": result = extraction_packets(_read(args.frozen))
    elif args.command == "import-run": result = import_run(_read(args.frozen), args.run_id, _read(args.responses))
    elif args.command == "control": result = frozen_control(_read(args.frozen), args.repo)
    elif args.command == "review-packets":
        bundle = review_packets(_read(args.frozen), [_read(x) for x in args.runs], _read(args.control) if args.control else None)
        # The scorer key is deliberately never exported in the reviewer packet.
        result = {"schema_version": bundle["schema_version"], "dataset_hash": bundle["dataset_hash"],
                  "packet_hash": bundle["packet_hash"], "items": bundle["packets"]}
    elif args.command == "score": result = score(_read(args.frozen), [_read(x) for x in args.runs], [_read(x) for x in args.reviews], _read(args.control) if args.control else None)
    else:
        raise NotImplementedError("control baseline requires its pinned parser implementation")
    _write(args.output, result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

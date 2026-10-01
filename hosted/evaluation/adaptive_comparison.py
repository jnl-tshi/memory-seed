"""Offline, source-blinded comparison of frozen adaptive disclosure results.

This module never executes a model or reads a corpus. The caller retains the
manifest and blind-id mapping privately; only aggregates should be published.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from copy import deepcopy
from typing import Any


ARMS = ("adaptive", "fixed_window", "full_window")
SUFFICIENCY = {"sufficient", "insufficient", "unknown"}
LABELS = {"positive", "hard_negative", "unknown"}
EXPOSURES = {"fresh", "historical", "synthetic", "unknown"}
SPLITS = {"fresh", "development", "regression", "test"}


def _hash(value: Any) -> str:
    try:
        serialized = json.dumps(value, sort_keys=True, ensure_ascii=False,
                                separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("inputs must be JSON-compatible") from exc
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty string")
    return value


def _source_reviews(case: dict) -> tuple[str, bool]:
    reviews = case.get("source_reviews")
    if not isinstance(reviews, list) or len(reviews) != 2:
        raise ValueError("two independent source reviews are required")
    ids = []
    values = []
    for review in reviews:
        if not isinstance(review, dict):
            raise ValueError("source review must be an object")
        ids.append(_nonempty(review.get("reviewer_id"), "source reviewer_id"))
        value = review.get("sufficiency")
        if value not in SUFFICIENCY:
            raise ValueError("invalid source sufficiency")
        values.append(value)
    if len(set(ids)) != 2:
        raise ValueError("source reviews require distinct reviewers")
    return (values[0] if values[0] == values[1] else "unknown", values[0] != values[1])


def _review_output(value: Any) -> str:
    """Require one source-reviewable text field, with no metadata envelope."""
    return _nonempty(value, "output")


def _validate_manifest(manifest: dict, packets: dict) -> dict[str, dict]:
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be an object")
    _nonempty(manifest.get("dataset_id"), "dataset_id")
    _nonempty(manifest.get("config_id"), "config_id")
    if type(manifest.get("exposure_audit_complete")) is not bool:
        raise ValueError("exposure_audit_complete must be explicit boolean")
    prior = manifest.get("previously_examined_roots")
    if not isinstance(prior, list) or any(not isinstance(x, str) or not x.strip() for x in prior):
        raise ValueError("previously_examined_roots must be an explicit root list")
    raw_cases = manifest.get("cases")
    if not isinstance(raw_cases, list) or not raw_cases:
        raise ValueError("manifest requires cases")
    cases = {}
    roots = {}
    for case in raw_cases:
        if not isinstance(case, dict):
            raise ValueError("case must be an object")
        case_id = _nonempty(case.get("case_id"), "case_id")
        root = _nonempty(case.get("root_id"), "root_id")
        split = _nonempty(case.get("split"), "split")
        if split not in SPLITS:
            raise ValueError("invalid split")
        if case_id in cases:
            raise ValueError("duplicate case_id")
        if root in roots and roots[root] != split:
            raise ValueError("true root crosses splits")
        roots[root] = split
        if case.get("label") not in LABELS or case.get("exposure") not in EXPOSURES:
            raise ValueError("invalid label or exposure")
        if type(case.get("lineage_known")) is not bool:
            raise ValueError("lineage_known must be boolean")
        _source_reviews(case)
        if case["label"] == "hard_negative" and any(type(review.get("real_negative")) is not bool
                                                     for review in case["source_reviews"]):
            raise ValueError("hard negative requires explicit real_negative source judgments")
        cases[case_id] = case
    if not isinstance(packets, dict) or set(packets) != set(ARMS):
        raise ValueError("packet arms must match three-arm contract")
    for arm in ARMS:
        if not isinstance(packets[arm], dict) or set(packets[arm]) != set(cases):
            raise ValueError("packet case coverage mismatch")
        for digest in packets[arm].values():
            if digest is not None:
                _nonempty(digest, "packet_hash")
    return cases


def _validate_runs(manifest: dict, packets: dict, runs: list, cases: dict) -> tuple[dict, tuple[str, str]]:
    if not isinstance(runs, list):
        raise ValueError("runs must be a list")
    keyed = {}
    run_ids = set()
    for item in runs:
        if not isinstance(item, dict):
            raise ValueError("run result must be an object")
        if item.get("dataset_id") != manifest["dataset_id"] or item.get("config_id") != manifest["config_id"]:
            raise ValueError("dataset/config identity mismatch")
        arm, run_id, case_id = item.get("arm"), _nonempty(item.get("run_id"), "run_id"), item.get("case_id")
        if arm not in ARMS or case_id not in cases:
            raise ValueError("unknown arm or case")
        key = (arm, run_id, case_id)
        if key in keyed:
            raise ValueError("duplicate run coverage")
        expected = packets[arm][case_id]
        if item.get("packet_hash") != expected:
            raise ValueError("packet_hash mismatch")
        candidates = item.get("candidates")
        if not isinstance(candidates, list):
            raise ValueError("candidates must be a list")
        candidate_ids = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                raise ValueError("candidate must be an object")
            candidate_ids.append(_nonempty(candidate.get("candidate_id"), "candidate_id"))
            if type(candidate.get("accepted")) is not bool:
                raise ValueError("candidate accepted must be boolean")
            if candidate["accepted"]:
                _review_output(candidate.get("output"))
            elif "output" in candidate:
                _review_output(candidate["output"])
        if len(set(candidate_ids)) != len(candidate_ids):
            raise ValueError("duplicate candidate_id")
        if expected is None and (candidates or item.get("usage") is not None):
            raise ValueError("unavailable packet cannot have output or usage")
        usage = item.get("usage")
        if usage is not None:
            if not isinstance(usage, dict) or set(usage) != {"request_count", "prompt_tokens", "completion_tokens", "missing_usage_count"}:
                raise ValueError("usage requires actual request and token counts")
            if any(type(usage[field]) is not int or usage[field] < 0
                   for field in ("request_count", "missing_usage_count")):
                raise ValueError("request and missing usage counts must be nonnegative integers")
            token_values = (usage["prompt_tokens"], usage["completion_tokens"])
            if usage["missing_usage_count"]:
                if token_values != (None, None):
                    raise ValueError("missing provider usage requires null token totals")
            elif any(type(value) is not int or value < 0 for value in token_values):
                raise ValueError("available token totals must be nonnegative integers")
            if usage["missing_usage_count"] > usage["request_count"]:
                raise ValueError("missing_usage_count exceeds requests")
        _nonempty(item.get("stop_reason"), "stop_reason")
        if expected is not None:
            _nonempty(item.get("source"), "source")
        keyed[key] = item
        run_ids.add(run_id)
    if len(run_ids) != 2:
        raise ValueError("two independent model run IDs are required")
    if set(keyed) != {(arm, run_id, case_id) for arm in ARMS for run_id in run_ids for case_id in cases}:
        raise ValueError("complete arm/run/case coverage required")
    return keyed, tuple(sorted(run_ids))


def _blind_id(manifest: dict, item: dict) -> str:
    review_material = [item.get("source"),
                       [[candidate["candidate_id"], candidate["accepted"], candidate.get("output")]
                        for candidate in item["candidates"]]]
    return _hash([_hash(manifest), item["case_id"], item["arm"], item["run_id"],
                  item["packet_hash"], review_material])


def masked_review_packets(manifest: dict, packets: dict, runs: list) -> tuple[list[dict], dict]:
    """Return deterministic review packets and a private blind-to-run mapping.

    The mapping must be held apart from reviewers. Source and candidate output
    are retained for semantic judgment; frozen labels and lineage are omitted.
    """
    manifest, packets, runs = deepcopy(manifest), deepcopy(packets), deepcopy(runs)
    cases = _validate_manifest(manifest, packets)
    keyed, _ = _validate_runs(manifest, packets, runs, cases)
    public = []
    private = {}
    for (arm, run_id, case_id), item in sorted(keyed.items()):
        blind_id = _blind_id(manifest, item)
        if blind_id in private:
            raise ValueError("blind identity collision")
        candidate_map = {f"candidate-{index:04d}": candidate["candidate_id"]
                         for index, candidate in enumerate(item["candidates"], 1)}
        private[blind_id] = {"arm": arm, "run_id": run_id, "case_id": case_id,
                             "candidate_id_map": candidate_map}
        candidates = [{"candidate_id": local_id, "accepted": candidate["accepted"],
                       **({"output": _review_output(candidate["output"])} if "output" in candidate else {})}
                      for local_id, candidate in zip(candidate_map, item["candidates"])]
        public.append({"blind_id": blind_id, "source": item.get("source"),
                       "candidates": candidates, "source_available": item["packet_hash"] is not None})
    public.sort(key=lambda packet: packet["blind_id"])
    return public, private


def _validate_reviews(public: list, reviews: list) -> tuple[dict, list]:
    if not isinstance(reviews, list):
        raise ValueError("reviews must be a list")
    packets = {p["blind_id"]: p for p in public}
    keyed = {}
    reviewers = set()
    for review in reviews:
        if not isinstance(review, dict):
            raise ValueError("review must be an object")
        blind_id = review.get("blind_id")
        reviewer = _nonempty(review.get("reviewer_id"), "reviewer_id")
        if blind_id not in packets:
            raise ValueError("review has unknown blind_id")
        key = (blind_id, reviewer)
        if key in keyed:
            raise ValueError("duplicate review")
        if review.get("source_sufficiency") not in SUFFICIENCY:
            raise ValueError("review requires source_sufficiency")
        for field in ("complete_decision", "reference_link_accuracy", "rationale_completeness"):
            if type(review.get(field)) is not bool:
                raise ValueError(f"review requires {field} judgment")
        assessments = review.get("candidate_assessments")
        if not isinstance(assessments, list):
            raise ValueError("review requires candidate assessments")
        candidate_ids = {c["candidate_id"] for c in packets[blind_id]["candidates"]}
        assessed = set()
        for assessment in assessments:
            if not isinstance(assessment, dict) or assessment.get("candidate_id") not in candidate_ids:
                raise ValueError("review has unknown candidate")
            candidate_id = assessment["candidate_id"]
            if candidate_id in assessed:
                raise ValueError("duplicate candidate review")
            assessed.add(candidate_id)
            for field in ("correct", "false_acceptance", "wrong_actor"):
                if type(assessment.get(field)) is not bool:
                    raise ValueError(f"review requires {field} judgment")
        if assessed != candidate_ids:
            raise ValueError("missing candidate review")
        keyed[key] = review
        reviewers.add(reviewer)
    if len(reviewers) != 2 or set(keyed) != {(blind_id, reviewer) for blind_id in packets for reviewer in reviewers}:
        raise ValueError("two distinct complete independent reviews required")
    disagreements = []
    by_blind = {}
    def judgments(review: dict) -> tuple:
        return (review["source_sufficiency"], review["complete_decision"],
                review["reference_link_accuracy"], review["rationale_completeness"],
                tuple(sorted((assessment["candidate_id"], assessment["correct"],
                              assessment["false_acceptance"], assessment["wrong_actor"])
                             for assessment in review["candidate_assessments"])))

    for blind_id in packets:
        pair = [keyed[(blind_id, reviewer)] for reviewer in sorted(reviewers)]
        a, b = pair
        if judgments(a) != judgments(b):
            disagreements.append(blind_id)
        by_blind[blind_id] = pair
    return by_blind, disagreements


def _metrics(items: list[tuple[dict, dict, list[dict]]]) -> dict:
    counts = Counter()
    prompt = completion = 0
    requests_missing = False
    tokens_missing = False
    stops = Counter()
    for case, item, pair in items:
        source_values = [r["source_sufficiency"] for r in pair]
        sufficient = all(v == "sufficient" for v in source_values)
        insufficient = all(v == "insufficient" for v in source_values)
        counts["source_sufficient" if sufficient else "source_insufficient" if insufficient else "source_unknown"] += 1
        recovered = False
        if case["label"] == "positive" and case["_sufficiency"] == "sufficient" and sufficient:
            counts["supported_positives"] += 1
            for candidate in item["candidates"]:
                if not candidate["accepted"]:
                    continue
                assessments = [next(a for a in review["candidate_assessments"]
                                    if a["candidate_id"] == candidate["candidate_id"]) for review in pair]
                if all(a["correct"] and not a["false_acceptance"] and not a["wrong_actor"]
                       for a in assessments):
                    recovered = True
            if recovered and all(r["complete_decision"] and r["reference_link_accuracy"]
                                 for r in pair):
                counts["complete_recovery"] += 1
                counts["correct_candidates"] += 1
        if case["label"] == "hard_negative":
            counts["hard_negatives"] += 1
        for field in ("reference_link_accuracy", "rationale_completeness"):
            counts[field + "_reviewed"] += 1
            if all(r[field] for r in pair):
                counts[field + "_passed"] += 1
        for candidate in item["candidates"]:
            if not candidate["accepted"]:
                continue
            counts["accepted_candidates"] += 1
            assessments = [next(a for a in review["candidate_assessments"]
                                if a["candidate_id"] == candidate["candidate_id"]) for review in pair]
            false_acceptance = case["label"] == "hard_negative" or any(a["false_acceptance"] for a in assessments)
            wrong_actor = any(a["wrong_actor"] for a in assessments)
            counts["false_acceptance"] += int(false_acceptance)
            counts["wrong_actor"] += int(wrong_actor)
        usage = item.get("usage")
        if usage is None:
            requests_missing = True
            tokens_missing = True
            counts["missing_usage_count"] += 1
        else:
            counts["request_count"] += usage["request_count"]
            counts["missing_usage_count"] += usage["missing_usage_count"]
            if usage["prompt_tokens"] is None:
                tokens_missing = True
            else:
                prompt += usage["prompt_tokens"]
                completion += usage["completion_tokens"]
        stops[item["stop_reason"]] += 1
    result = {field: counts[field] for field in ("source_sufficient", "source_insufficient", "source_unknown",
              "supported_positives", "hard_negatives", "complete_recovery", "accepted_candidates",
              "correct_candidates", "false_acceptance", "wrong_actor", "reference_link_accuracy_reviewed",
              "reference_link_accuracy_passed", "rationale_completeness_reviewed", "rationale_completeness_passed",
              "missing_usage_count")}
    result["complete_recovery_rate"] = (result["complete_recovery"] / result["supported_positives"]
                                        if result["supported_positives"] else None)
    result["precision"] = (result["correct_candidates"] / result["accepted_candidates"]
                           if result["accepted_candidates"] else None)
    result.update(request_count=None if requests_missing else counts["request_count"],
                  prompt_tokens=None if tokens_missing else prompt,
                  completion_tokens=None if tokens_missing else completion,
                  stop_reasons=dict(sorted(stops.items())))
    return result


def compare(manifest: dict, packets: dict, runs: list, reviews: list) -> dict:
    """Score frozen externally supplied results; return aggregate-only evidence."""
    manifest, packets, runs, reviews = map(deepcopy, (manifest, packets, runs, reviews))
    frozen_manifest_hash = _hash(manifest)
    cases = _validate_manifest(manifest, packets)
    keyed, run_ids = _validate_runs(manifest, packets, runs, cases)
    public, private = masked_review_packets(manifest, packets, runs)
    by_blind, disagreements = _validate_reviews(public, reviews)
    for case in cases.values():
        case["_sufficiency"], case["_source_disagreement"] = _source_reviews(case)
    groups = {}
    for blind_id, identity in private.items():
        arm, run_id, case_id = (identity[key] for key in ("arm", "run_id", "case_id"))
        scored_item = deepcopy(keyed[(arm, run_id, case_id)])
        reverse = {original: local for local, original in identity["candidate_id_map"].items()}
        for candidate in scored_item["candidates"]:
            candidate["candidate_id"] = reverse[candidate["candidate_id"]]
        groups[(arm, run_id, case_id)] = (cases[case_id], scored_item, by_blind[blind_id])
    arms = {arm: {"runs": {run_id: _metrics([groups[(arm, run_id, case_id)] for case_id in cases])
                           for run_id in run_ids}} for arm in ARMS}
    for arm in ARMS:
        arms[arm]["aggregate"] = _metrics([groups[(arm, run_id, case_id)]
                                            for run_id in run_ids for case_id in cases])
    paired = []
    for run_id in run_ids:
        for case_id in cases:
            baseline = _metrics([groups[("adaptive", run_id, case_id)]])
            for arm in ("fixed_window", "full_window"):
                control = _metrics([groups[(arm, run_id, case_id)]])
                available = (packets["adaptive"][case_id] is not None and
                             packets[arm][case_id] is not None)
                paired.append({"case_id": case_id, "run_id": run_id, "control_arm": arm,
                               "complete_recovery_delta": baseline["complete_recovery"] - control["complete_recovery"] if available else None,
                               "accepted_candidate_delta": baseline["accepted_candidates"] - control["accepted_candidates"] if available else None,
                               "request_delta": None if not available or baseline["request_count"] is None or control["request_count"] is None
                               else baseline["request_count"] - control["request_count"],
                               "prompt_token_delta": None if not available or baseline["prompt_tokens"] is None or control["prompt_tokens"] is None
                               else baseline["prompt_tokens"] - control["prompt_tokens"],
                               "completion_token_delta": None if not available or baseline["completion_tokens"] is None or control["completion_tokens"] is None
                               else baseline["completion_tokens"] - control["completion_tokens"]})
    reasons = []
    if disagreements or any(c["_source_disagreement"] for c in cases.values()):
        reasons.append("review_disagreement")
    if any(c["label"] == "unknown" or not c["lineage_known"] or c["exposure"] == "unknown"
           for c in cases.values() if c["split"] == "fresh"):
        reasons.append("unknown_label_lineage_or_exposure")
    if any(c["exposure"] != "fresh" for c in cases.values() if c["split"] == "fresh"):
        reasons.append("fresh_split_exposure_unverified")
    if manifest["exposure_audit_complete"] is not True:
        reasons.append("exposure_audit_incomplete")
    if any(c["split"] == "fresh" and c["root_id"] in manifest["previously_examined_roots"]
           for c in cases.values()):
        reasons.append("prior_examined_root")
    if any(packets[arm][case_id] is None for arm in ARMS for case_id in cases):
        reasons.append("unavailable_arm_packet")
    if any(item.get("usage") is None or item["usage"]["missing_usage_count"]
           for item in keyed.values()):
        reasons.append("missing_actual_usage")
    if any(c["_sufficiency"] == "unknown" for c in cases.values()):
        reasons.append("unknown_source_sufficiency")
    fresh_positive = [c for c in cases.values() if c["label"] == "positive" and c["exposure"] == "fresh"
                      and c["split"] == "fresh" and c["root_id"] not in manifest["previously_examined_roots"]
                      and c["_sufficiency"] == "sufficient" and c["lineage_known"]]
    fresh_negative = [c for c in cases.values() if c["label"] == "hard_negative" and c["exposure"] == "fresh"
                      and c["split"] == "fresh" and c["root_id"] not in manifest["previously_examined_roots"]
                      and c["_sufficiency"] == "sufficient" and c["lineage_known"]
                      and all(review["real_negative"] for review in c["source_reviews"])]
    positive_roots = {c["root_id"] for c in fresh_positive}
    negative_roots = {c["root_id"] for c in fresh_negative}
    if (len(fresh_positive) < 30 or len(fresh_negative) < 30 or
            len(positive_roots) < 30 or len(negative_roots) < 30 or positive_roots & negative_roots):
        reasons.append("insufficient_fresh_sample")
    # This module sees owner-supplied labels, lineage, and exposure assertions,
    # but no independently verified corpus audit. They cannot grant live authority.
    reasons.append("external_freshness_verification_unavailable")
    for run_id in run_ids:
        metric = _metrics([groups[("adaptive", run_id, case_id)] for case_id, case in cases.items()
                           if case["split"] == "fresh"])
        if metric["complete_recovery_rate"] is None or metric["precision"] is None:
            reasons.append("missing_metric_denominator")
        elif (metric["complete_recovery_rate"] < .8 or metric["precision"] < .95
              or metric["false_acceptance"] or metric["wrong_actor"]):
            reasons.append("threshold_failure")
    status = "inconclusive" if any(r != "threshold_failure" for r in reasons) else "fail" if reasons else "pass"
    return {"dataset_id": manifest["dataset_id"], "config_id": manifest["config_id"],
            "frozen_manifest_hash": frozen_manifest_hash,
            "arms": arms, "paired_case_deltas": paired, "review_disagreements": sorted(disagreements),
            "gate": {"status": status, "reasons": sorted(set(reasons)),
                     "fresh_supported_positives": len(fresh_positive),
                     "fresh_reviewed_hard_negatives": len(fresh_negative)}}

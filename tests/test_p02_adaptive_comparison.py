"""Synthetic contract tests for offline blinded comparison."""
from copy import deepcopy

import pytest

from hosted.evaluation.adaptive_comparison import compare, masked_review_packets


ARMS = ("adaptive", "fixed_window", "full_window")


def fixture():
    cases = [
        {"case_id": "p", "root_id": "root-p", "split": "test", "exposure": "synthetic",
         "label": "positive", "lineage_known": True,
         "source_reviews": [{"reviewer_id": "s1", "sufficiency": "sufficient"},
                            {"reviewer_id": "s2", "sufficiency": "sufficient"}]},
        {"case_id": "n", "root_id": "root-n", "split": "test", "exposure": "synthetic",
         "label": "hard_negative", "lineage_known": True,
         "source_reviews": [{"reviewer_id": "s1", "sufficiency": "sufficient", "real_negative": True},
                            {"reviewer_id": "s2", "sufficiency": "sufficient", "real_negative": True}]},
    ]
    manifest = {"dataset_id": "frozen-dataset", "config_id": "frozen-config",
                "exposure_audit_complete": True, "previously_examined_roots": [], "cases": cases}
    packets = {arm: {case: f"hash-{arm}-{case}" for case in ("p", "n")} for arm in ARMS}
    runs = []
    for arm in ARMS:
        for run_id in ("run-1", "run-2"):
            for case in ("p", "n"):
                runs.append({"dataset_id": "frozen-dataset", "config_id": "frozen-config",
                             "arm": arm, "run_id": run_id, "case_id": case,
                             "packet_hash": packets[arm][case],
                             "source": f"Source for {case}",
                             "candidates": [{"candidate_id": "c1", "accepted": True,
                                             "output": "The user approved the proposed change."}] if case == "p" else [],
                             "usage": {"request_count": 1, "prompt_tokens": 10,
                                       "completion_tokens": 4, "missing_usage_count": 0},
                             "stop_reason": "complete"})
    review_packets, mapping = masked_review_packets(manifest, packets, runs)
    reviews = []
    for packet in review_packets:
        for reviewer in ("r1", "r2"):
            reviews.append({"blind_id": packet["blind_id"], "reviewer_id": reviewer,
                            "source_sufficiency": "sufficient", "complete_decision": bool(packet["candidates"]),
                            "reference_link_accuracy": True, "rationale_completeness": True,
                            "candidate_assessments": [
                                {"candidate_id": c["candidate_id"], "correct": True,
                                 "false_acceptance": False, "wrong_actor": False}
                                for c in packet["candidates"]]})
    return manifest, packets, runs, reviews, mapping


def test_masking_is_deterministic_and_hides_private_fields():
    manifest, packets, runs, _, mapping = fixture()
    public, again = masked_review_packets(manifest, packets, runs)
    assert public == masked_review_packets(manifest, packets, runs)[0]
    assert mapping == again
    for packet in public:
        assert packet["source"]
        assert not set(packet) & {"arm", "run_id", "label", "split", "root_id", "expected_decision", "score"}


def test_valid_synthetic_shape_is_inconclusive_and_paired():
    result = compare(*fixture()[:4])
    assert result["gate"]["status"] == "inconclusive"
    assert len(result["paired_case_deltas"]) == 8
    assert result["arms"]["adaptive"]["runs"]["run-1"]["precision"] == 1


def test_identity_and_coverage_mismatch_rejected():
    manifest, packets, runs, reviews, _ = fixture()
    bad = deepcopy(runs)
    bad[0]["packet_hash"] = "wrong"
    with pytest.raises(ValueError, match="packet_hash"):
        compare(manifest, packets, bad, reviews)
    with pytest.raises(ValueError, match="coverage"):
        compare(manifest, packets, runs[:-1], reviews)
    bad = deepcopy(runs)
    bad[0]["case_id"] = "n"
    with pytest.raises(ValueError):
        compare(manifest, packets, bad, reviews)


def test_reviews_must_be_distinct_complete_and_agree():
    manifest, packets, runs, reviews, _ = fixture()
    with pytest.raises(ValueError, match="review"):
        compare(manifest, packets, runs, reviews[:-1])
    with pytest.raises(ValueError, match="review"):
        compare(manifest, packets, runs, reviews + [reviews[0]])
    conflicting = deepcopy(reviews)
    conflicting[0]["complete_decision"] = False
    result = compare(manifest, packets, runs, conflicting)
    assert result["review_disagreements"]
    assert result["gate"]["status"] == "inconclusive"


def test_insufficient_source_excluded_and_extra_candidate_penalized():
    manifest, packets, runs, reviews, _ = fixture()
    for case in manifest["cases"]:
        if case["case_id"] == "p":
            for review in case["source_reviews"]:
                review["sufficiency"] = "insufficient"
    for review in reviews:
        review["source_sufficiency"] = "insufficient" if review["candidate_assessments"] else "sufficient"
    result = compare(manifest, packets, runs, _rebind_reviews(manifest, packets, runs))
    assert result["arms"]["adaptive"]["runs"]["run-1"]["supported_positives"] == 0
    manifest, packets, runs, _, _ = fixture()
    runs[0]["candidates"].append({"candidate_id": "extra", "accepted": True,
                                    "output": "An unsupported extra decision."})
    review_packets, _ = masked_review_packets(manifest, packets, runs)
    reviews = []
    for packet in review_packets:
        for reviewer in ("r1", "r2"):
            reviews.append({"blind_id": packet["blind_id"], "reviewer_id": reviewer,
                            "source_sufficiency": "sufficient", "complete_decision": bool(packet["candidates"]),
                            "reference_link_accuracy": True, "rationale_completeness": True,
                            "candidate_assessments": [{"candidate_id": c["candidate_id"],
                                                       "correct": c["candidate_id"] != "extra",
                                                       "false_acceptance": False, "wrong_actor": False}
                                                      for c in packet["candidates"]]})
    result = compare(manifest, packets, runs, reviews)
    assert result["arms"]["adaptive"]["runs"]["run-1"]["precision"] == .5


def test_wrong_actor_false_acceptance_and_missing_usage():
    manifest, packets, runs, reviews, mapping = fixture()
    runs[0]["usage"] = None
    target_blind = next(blind for blind, identity in mapping.items()
                        if all(identity[key] == value for key, value in
                               {"arm": "adaptive", "run_id": "run-1", "case_id": "p"}.items()))
    for review in reviews:
        if review["blind_id"] == target_blind:
            review["candidate_assessments"][0]["wrong_actor"] = True
            review["candidate_assessments"][0]["false_acceptance"] = True
    result = compare(manifest, packets, runs, reviews)
    metric = result["arms"]["adaptive"]["runs"]["run-1"]
    assert metric["prompt_tokens"] is None
    assert metric["missing_usage_count"] >= 1
    assert metric["wrong_actor"] == 1
    assert metric["false_acceptance"] == 1


def test_historical_and_unknown_exposure_cannot_pass():
    manifest, packets, runs, reviews, _ = fixture()
    manifest["cases"][0]["exposure"] = "historical"
    manifest["cases"][1]["exposure"] = "unknown"
    assert compare(manifest, packets, runs,
                   _rebind_reviews(manifest, packets, runs))["gate"]["status"] == "inconclusive"


def test_development_split_never_counts_as_fresh():
    manifest, packets, runs, _, _ = fixture()
    for case in manifest["cases"]:
        case["exposure"] = "fresh"
        case["split"] = "development"
    result = compare(manifest, packets, runs, _rebind_reviews(manifest, packets, runs))
    assert result["gate"]["fresh_supported_positives"] == 0
    assert result["gate"]["fresh_reviewed_hard_negatives"] == 0


def test_unavailable_packet_is_not_scored_as_zero_cost():
    manifest, packets, runs, _, _ = fixture()
    packets["full_window"]["p"] = None
    for item in runs:
        if item["arm"] == "full_window" and item["case_id"] == "p":
            item.update(packet_hash=None, source=None, candidates=[], usage=None,
                        stop_reason="packet_unavailable")
    public, _ = masked_review_packets(manifest, packets, runs)
    reviews = []
    for packet in public:
        for reviewer in ("r1", "r2"):
            reviews.append({"blind_id": packet["blind_id"], "reviewer_id": reviewer,
                            "source_sufficiency": "unknown" if not packet["source_available"] else "sufficient",
                            "complete_decision": bool(packet["candidates"]),
                            "reference_link_accuracy": True, "rationale_completeness": True,
                            "candidate_assessments": [
                                {"candidate_id": c["candidate_id"], "correct": True,
                                 "false_acceptance": False, "wrong_actor": False}
                                for c in packet["candidates"]]})
    result = compare(manifest, packets, runs, reviews)
    assert "unavailable_arm_packet" in result["gate"]["reasons"]
    assert result["arms"]["full_window"]["runs"]["run-1"]["prompt_tokens"] is None
    assert next(row for row in result["paired_case_deltas"]
                if row["case_id"] == "p" and row["run_id"] == "run-1"
                and row["control_arm"] == "full_window")["complete_recovery_delta"] is None


def test_root_cannot_cross_splits():
    manifest, packets, runs, reviews, _ = fixture()
    manifest["cases"][1]["root_id"] = manifest["cases"][0]["root_id"]
    manifest["cases"][1]["split"] = "development"
    with pytest.raises(ValueError, match="root crosses splits"):
        compare(manifest, packets, runs, reviews)


def test_stale_review_rejected_after_manifest_source_or_output_change():
    manifest, packets, runs, reviews, _ = fixture()
    changed = deepcopy(manifest)
    changed["cases"][0]["label"] = "unknown"
    with pytest.raises(ValueError, match="review"):
        compare(changed, packets, runs, reviews)
    changed_runs = deepcopy(runs)
    changed_runs[0]["source"] = "Different source"
    with pytest.raises(ValueError, match="review"):
        compare(manifest, packets, changed_runs, reviews)
    changed_runs = deepcopy(runs)
    changed_runs[0]["candidates"][0]["output"] = "Different output"
    with pytest.raises(ValueError, match="review"):
        compare(manifest, packets, changed_runs, reviews)


def test_opaque_candidate_ids_and_controlled_review_output():
    manifest, packets, runs, _, _ = fixture()
    runs[0]["candidates"][0]["candidate_id"] = "original-private-id"
    public, private = masked_review_packets(manifest, packets, runs)
    assert "original-private-id" not in str(public)
    assert "original-private-id" in str(private)
    runs[0]["candidates"][0]["output"] = {"text": "Decision", "gold_label": "positive"}
    with pytest.raises(ValueError, match="output"):
        masked_review_packets(manifest, packets, runs)


def test_precision_credits_one_unique_source_sufficient_recovery():
    manifest, packets, runs, _, _ = fixture()
    runs[0]["candidates"].append({"candidate_id": "c2", "accepted": True,
                                    "output": "Duplicate complete decision"})
    public, _ = masked_review_packets(manifest, packets, runs)
    reviews = []
    for packet in public:
        for reviewer in ("r1", "r2"):
            reviews.append({"blind_id": packet["blind_id"], "reviewer_id": reviewer,
                            "source_sufficiency": "sufficient", "complete_decision": bool(packet["candidates"]),
                            "reference_link_accuracy": True, "rationale_completeness": True,
                            "candidate_assessments": [{"candidate_id": c["candidate_id"], "correct": True,
                                                       "false_acceptance": False, "wrong_actor": False}
                                                      for c in packet["candidates"]]})
    result = compare(manifest, packets, runs, reviews)
    metric = result["arms"]["adaptive"]["runs"]["run-1"]
    assert metric["correct_candidates"] == 1
    assert metric["precision"] == .5


def test_unstated_reason_does_not_reduce_complete_decision_credit():
    manifest, packets, runs, reviews, mapping = fixture()
    direct_choice = next(blind for blind, identity in mapping.items()
                         if all(identity[key] == value for key, value in
                                {"arm": "adaptive", "run_id": "run-1", "case_id": "p"}.items()))
    for review in reviews:
        if review["blind_id"] == direct_choice:
            review["rationale_completeness"] = False
    metric = compare(manifest, packets, runs, reviews)["arms"]["adaptive"]["runs"]["run-1"]
    assert metric["complete_recovery"] == 1
    assert metric["correct_candidates"] == 1
    assert metric["precision"] == 1
    assert metric["rationale_completeness_passed"] == 1


def test_arm_source_sufficiency_can_differ_from_full_case_review():
    manifest, packets, runs, reviews, mapping = fixture()
    adaptive_p = {blind for blind, identity in mapping.items()
                  if identity["arm"] == "adaptive" and identity["case_id"] == "p"}
    for review in reviews:
        if review["blind_id"] in adaptive_p:
            review["source_sufficiency"] = "insufficient"
    result = compare(manifest, packets, runs, reviews)
    metric = result["arms"]["adaptive"]["runs"]["run-1"]
    assert metric["source_insufficient"] == 1
    assert metric["supported_positives"] == 0
    assert result["review_disagreements"] == []
    assert "review_disagreement" not in result["gate"]["reasons"]


def test_known_requests_survive_missing_provider_tokens():
    manifest, packets, runs, reviews, _ = fixture()
    runs[0]["usage"] = {"request_count": 2, "prompt_tokens": None,
                        "completion_tokens": None, "missing_usage_count": 1}
    result = compare(manifest, packets, runs, reviews)
    metric = result["arms"]["adaptive"]["runs"]["run-1"]
    assert metric["request_count"] == 3
    assert metric["prompt_tokens"] is None
    assert metric["completion_tokens"] is None
    assert metric["missing_usage_count"] == 1
    paired = next(row for row in result["paired_case_deltas"]
                  if row["case_id"] == "p" and row["run_id"] == "run-1"
                  and row["control_arm"] == "fixed_window")
    assert paired["request_delta"] == 1
    assert paired["prompt_token_delta"] is None


def test_review_order_and_notes_do_not_create_disagreement():
    manifest, packets, runs, _, _ = fixture()
    runs[0]["candidates"].append({"candidate_id": "c2", "accepted": True,
                                    "output": "Another candidate"})
    reviews = _rebind_reviews(manifest, packets, runs)
    target = next(review["blind_id"] for review in reviews
                  if len(review["candidate_assessments"]) == 2)
    second = next(review for review in reviews
                  if review["blind_id"] == target and review["reviewer_id"] == "r2")
    second["candidate_assessments"].reverse()
    second["notes"] = "Independent reviewer note"
    assert compare(manifest, packets, runs, reviews)["review_disagreements"] == []


def test_exposure_audit_and_prior_roots_are_required_for_gate():
    manifest, packets, runs, reviews, _ = fixture()
    manifest["exposure_audit_complete"] = False
    assert "exposure_audit_incomplete" in compare(manifest, packets, runs,
                                                   _rebind_reviews(manifest, packets, runs))["gate"]["reasons"]
    manifest["exposure_audit_complete"] = True
    manifest["previously_examined_roots"] = ["root-p"]
    manifest["cases"][0]["split"] = "fresh"
    assert "prior_examined_root" in compare(manifest, packets, runs,
                                             _rebind_reviews(manifest, packets, runs))["gate"]["reasons"]


def test_self_declared_sixty_fresh_cases_cannot_pass():
    manifest, _, _, _, _ = fixture()
    positives = deepcopy(manifest["cases"][0])
    negatives = deepcopy(manifest["cases"][1])
    manifest["cases"] = []
    for template, prefix in ((positives, "p"), (negatives, "n")):
        for index in range(30):
            case = deepcopy(template)
            case.update(case_id=f"{prefix}{index}", root_id=f"root-{prefix}{index}",
                        split="fresh", exposure="fresh")
            manifest["cases"].append(case)
    packets = {arm: {case["case_id"]: f"hash-{arm}-{case['case_id']}"
                     for case in manifest["cases"]} for arm in ARMS}
    runs = []
    for arm in ARMS:
        for run_id in ("run-1", "run-2"):
            for case in manifest["cases"]:
                positive = case["label"] == "positive"
                runs.append({"dataset_id": manifest["dataset_id"], "config_id": manifest["config_id"],
                             "arm": arm, "run_id": run_id, "case_id": case["case_id"],
                             "packet_hash": packets[arm][case["case_id"]], "source": "Source",
                             "candidates": [{"candidate_id": "c", "accepted": True,
                                             "output": "Complete decision"}] if positive else [],
                             "usage": {"request_count": 1, "prompt_tokens": 10,
                                       "completion_tokens": 5, "missing_usage_count": 0},
                             "stop_reason": "complete"})
    result = compare(manifest, packets, runs, _rebind_reviews(manifest, packets, runs))
    assert result["gate"]["fresh_supported_positives"] == 30
    assert result["gate"]["fresh_reviewed_hard_negatives"] == 30
    assert result["gate"]["status"] == "inconclusive"
    assert "external_freshness_verification_unavailable" in result["gate"]["reasons"]


def _rebind_reviews(manifest, packets, runs):
    public, private = masked_review_packets(manifest, packets, runs)
    cases = {case["case_id"]: case for case in manifest["cases"]}
    return [{"blind_id": p["blind_id"], "reviewer_id": reviewer,
             "source_sufficiency": cases[private[p["blind_id"]]["case_id"]]["source_reviews"][0]["sufficiency"],
             "complete_decision": bool(p["candidates"]),
             "reference_link_accuracy": True, "rationale_completeness": True,
             "candidate_assessments": [{"candidate_id": c["candidate_id"], "correct": True,
                                        "false_acceptance": False, "wrong_actor": False}
                                       for c in p["candidates"]]}
            for p in public for reviewer in ("r1", "r2")]

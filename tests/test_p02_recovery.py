from copy import deepcopy
import json
from pathlib import Path

import pytest

from hosted.evaluation.recovery import (
    freeze_dataset, extraction_packets, import_run, review_packets, score,
    frozen_control, main,
)


def message(rollout="r", turn=1, actor="user", text="We should use SQLite."):
    return {"rollout_id": rollout, "turn": turn, "source_ordinal": turn,
            "actor": actor, "text": text}


def case(case_id="gold-x", split="fresh", kind="positive", rollout="r", reviewed=True):
    gold = {"title": "Use SQLite", "issue": "storage"}
    if kind == "negative":
        gold["no_decision_rationale"] = "No decision was recorded."
    value = {"case_id": case_id, "split": split, "kind": kind,
             "messages": [message(rollout)],
             "gold_record": gold}
    if reviewed:
        value["source_reviews"] = [
            {"reviewer_id": "source-a", "supported": True, "real_negative": kind == "negative"},
            {"reviewer_id": "source-b", "supported": True, "real_negative": kind == "negative"},
        ]
    return value


def dataset(cases=None, **extra):
    return {"cases": cases or [case()], "lineage": {"r": {"session_id": "s-r", "parent_session_id": None}},
            "previously_examined_roots": [], "exposure_audit_complete": True, **extra}


def config():
    return {"model": "synthetic", "reasoning_effort": "medium"}


def response_for(packet):
    request = packet["request"]
    msg = request["messages"][0]
    q = msg["text"]
    cite = {"rollout_id": msg["rollout_id"], "turn": msg["turn"],
            "source_ordinal": msg["source_ordinal"], "start": 0, "end": len(q), "quote": q}
    return {"request_id": request["request_id"], "candidates": [{
        "candidate_id": "model-id", "issue": "storage", "selected_action": "use SQLite",
        "scope": "storage", "agreement_quote": None, "reason": None, "conditions": [],
        "state": "proposed", "deciding_actor": "agent", "unresolved_references": [],
        "field_evidence": {"issue": [cite], "selected_action": [cite], "scope": [cite]},
    }]}


def make_run(frozen, run_id="run-a", responses_fn=response_for):
    packets = extraction_packets(frozen)
    return import_run(frozen, run_id, {p["case_id"]: responses_fn(p) for p in packets})


def make_reviews(frozen, runs, *, conflict=False, control=None):
    output = review_packets(frozen, runs, control)
    docs = []
    for reviewer in ("reviewer-a", "reviewer-b"):
        judgments = []
        for item in output["packets"]:
            judgments.append({"item_id": item["item_id"], "candidate_judgments": [
                {"candidate_id": c["candidate_id"], "complete_match": True,
                 "false_acceptance": False, "wrong_actor": False,
                 "field_checks": {f: True for f in ("issue", "selected_action", "scope", "agreement_quote", "reason", "conditions", "deciding_actor")},
                 "rationale": "synthetic review"}
                for c in item["candidates"]
            ]})
        docs.append({"reviewer_id": reviewer, "packet_hash": output["key"]["packet_hash"], "items": judgments})
    if conflict and docs[1]["items"][0]["candidate_judgments"]:
        docs[1]["items"][0]["candidate_judgments"][0]["complete_match"] = False
    return docs


def test_freeze_opaque_ids_config_hashes_and_gold_stripping():
    frozen = freeze_dataset(dataset([case("private-decision-id")]), config())
    packets = extraction_packets(frozen)
    assert packets[0]["case_id"] == "case-0001"
    encoded = json.dumps(packets[0], ensure_ascii=False)
    for secret in ("private-decision-id", "Use SQLite", "gold_record", "fresh", "positive"):
        assert secret not in encoded
    assert frozen["config_id"]
    assert frozen["dataset_hash"]


def test_canonical_hash_integrity_detects_tampering():
    frozen = freeze_dataset(dataset(), config())
    changed = deepcopy(frozen)
    changed["cases"][0]["gold_record"]["title"] = "changed"
    with pytest.raises(ValueError, match="hash|integrity"):
        extraction_packets(changed)


def test_lineage_parent_resolution_and_fresh_prior_collision():
    d = dataset([case(rollout="child")], lineage={
        "root": {"session_id": "root-session", "parent_session_id": None},
        "child": {"session_id": "child-session", "parent_session_id": "root-session"},
    })
    assert freeze_dataset(d, config())["cases"][0]["root_id"] == "root-session"
    d["previously_examined_roots"] = ["root-session"]
    frozen = freeze_dataset(d, config())
    assert not frozen["eligibility"]["eligible"]
    assert any("previously examined" in reason for reason in frozen["eligibility"]["reasons"])


def test_fresh_root_cannot_overlap_development_and_missing_parent_is_ineligible():
    cases = [case(case_id="dev", split="development", rollout="root"),
             case(case_id="fresh", split="fresh", rollout="child")]
    lineage = {"root": {"session_id": "root-session", "parent_session_id": None},
               "child": {"session_id": "child-session", "parent_session_id": "root-session"}}
    frozen = freeze_dataset(dataset(cases, lineage=lineage), config())
    assert not frozen["eligibility"]["eligible"]
    assert any("overlaps" in reason for reason in frozen["eligibility"]["reasons"])
    missing = dataset([case(rollout="unmapped")], lineage={})
    frozen_missing = freeze_dataset(missing, config())
    assert not frozen_missing["cases"][0]["lineage_available"]


@pytest.mark.parametrize("lineage", [
    {"r": {"session_id": "s", "parent_session_id": "s"}},
    {"r": {"session_id": "s", "parent_session_id": None}, "x": {"session_id": "s", "parent_session_id": None}},
])
def test_lineage_missing_cycle_and_conflict_are_rejected(lineage):
    with pytest.raises(ValueError):
        freeze_dataset(dataset(lineage=lineage), config())


def test_missing_review_or_lineage_means_ineligible_not_fake_eligibility():
    value = dataset([case(reviewed=False)])
    value["lineage"] = {}
    frozen = freeze_dataset(value, config())
    assert not frozen["eligibility"]["eligible"]
    assert frozen["eligibility"]["reasons"]


def test_source_reviews_require_exact_booleans_and_independent_ids():
    value = dataset()
    value["cases"][0]["source_reviews"][0]["supported"] = "true"
    frozen = freeze_dataset(value, config())
    assert not frozen["cases"][0]["source_review_available"]
    value = dataset()
    value["cases"][0]["source_reviews"][1]["reviewer_id"] = "source-a"
    frozen = freeze_dataset(value, config())
    assert not frozen["cases"][0]["source_review_available"]


def test_response_validation_missing_invalid_and_extra_keys():
    frozen = freeze_dataset(dataset(), config())
    with pytest.raises(ValueError, match="extra|unknown"):
        import_run(frozen, "r1", {"gold-x": {}})
    packet = extraction_packets(frozen)[0]
    response = response_for(packet)
    response["candidates"][0]["field_evidence"]["selected_action"][0]["quote"] = "forged"
    run = import_run(frozen, "r1", {"case-0001": response})
    assert run["cases"][0]["status"] == "invalid"
    missing = import_run(frozen, "r2", {})
    assert missing["cases"][0]["status"] == "unavailable"


def test_review_packet_masking_coverage_identity_and_hash_binding():
    frozen = freeze_dataset(dataset(), config())
    runs = [make_run(frozen, "run-a"), make_run(frozen, "run-b")]
    packet = review_packets(frozen, runs)
    assert len(packet["packets"]) == 2
    assert "run-a" not in json.dumps(packet["packets"])
    docs = make_reviews(frozen, runs)
    assert score(frozen, runs, docs)["gate"]["status"] in {"inconclusive", "fail"}
    bad = deepcopy(docs)
    bad[0]["items"].pop()
    with pytest.raises(ValueError, match="cover|coverage|every"):
        score(frozen, runs, bad)
    same_id = deepcopy(runs[1]); same_id["run_id"] = runs[0]["run_id"]
    with pytest.raises(ValueError, match="independent|distinct|run"):
        review_packets(frozen, [runs[0], same_id])


def test_empty_denominators_and_data_shortfall_cannot_pass():
    frozen = freeze_dataset(dataset([case(kind="negative")]), config())
    runs = [make_run(frozen, "r1"), make_run(frozen, "r2")]
    docs = make_reviews(frozen, runs)
    report = score(frozen, runs, docs)
    assert report["gate"]["status"] != "pass"
    assert report["runs"][0]["precision"] == 0.0


def test_two_runs_reviews_conflict_and_precision_denominator_duplicates():
    frozen = freeze_dataset(dataset(), config())
    runs = [make_run(frozen, "run-a"), make_run(frozen, "run-b")]
    runs[0]["cases"][0]["candidates"].append(deepcopy(runs[0]["cases"][0]["candidates"][0]))
    # Re-seal via module helper is intentionally inaccessible; integrity check must reject edits.
    with pytest.raises(ValueError, match="hash|integrity"):
        score(frozen, runs, make_reviews(frozen, [make_run(frozen, "a"), make_run(frozen, "b")]))

    runs = [make_run(frozen, "run-a"), make_run(frozen, "run-b")]
    docs = make_reviews(frozen, runs, conflict=True)
    report = score(frozen, runs, docs)
    assert report["gate"]["status"] != "pass"
    assert report["runs"][0]["conflicts"]


def test_wrong_actor_and_false_acceptance_are_hard_failures():
    frozen = freeze_dataset(dataset(), config())
    runs = [make_run(frozen, "run-a"), make_run(frozen, "run-b")]
    docs = make_reviews(frozen, runs)
    docs[0]["items"][0]["candidate_judgments"][0]["false_acceptance"] = True
    report = score(frozen, runs, docs)
    assert report["gate"]["status"] != "pass"
    docs = make_reviews(frozen, runs)
    docs[0]["items"][0]["candidate_judgments"][0]["wrong_actor"] = True
    report = score(frozen, runs, docs)
    assert report["runs"][0]["wrong_actor"] > 0
    assert report["gate"]["status"] != "pass"


def _large_eligible_dataset():
    cases = []
    lineage = {}
    for i in range(60):
        cid, rollout = f"c{i:02d}", f"r{i:02d}"
        kind = "positive" if i < 30 else "negative"
        proposal = message(rollout, 1, "agent", "Use SQLite for the database storage.")
        agreement = message(rollout, 2, "user", "Yes, use SQLite for the database storage.")
        gold = {"decision": "Use SQLite"} if kind == "positive" else {"no_decision_rationale": "No choice was recorded."}
        cases.append({"case_id": cid, "split": "fresh", "kind": kind,
                      "messages": [proposal, agreement], "gold_record": gold,
                      "source_reviews": [
                          {"reviewer_id": "source-a", "supported": True, "real_negative": kind == "negative"},
                          {"reviewer_id": "source-b", "supported": True, "real_negative": kind == "negative"},
                      ]})
        lineage[rollout] = {"session_id": f"session-{i}", "parent_session_id": None}
    return {"cases": cases, "lineage": lineage, "previously_examined_roots": [],
            "exposure_audit_complete": True}


def _threshold_response(packet, candidate):
    request = packet["request"]
    proposal, agreement = request["messages"]
    def cite(msg):
        return {"rollout_id": msg["rollout_id"], "turn": msg["turn"],
                "source_ordinal": msg["source_ordinal"], "start": 0,
                "end": len(msg["text"]), "quote": msg["text"]}
    if not candidate:
        return {"request_id": request["request_id"], "candidates": []}
    c1, c2 = cite(proposal), cite(agreement)
    return {"request_id": request["request_id"], "candidates": [{
        "candidate_id": "synthetic", "issue": "database storage",
        "selected_action": "use SQLite", "scope": "database storage",
        "agreement_quote": agreement["text"], "reason": None, "conditions": [],
        "state": "accepted", "deciding_actor": "user", "unresolved_references": [],
        "field_evidence": {"issue": [c1], "selected_action": [c1], "scope": [c1],
                           "agreement_quote": [c2]},
    }]}


def test_synthetic_metadata_can_exercise_exact_gate_thresholds():
    frozen = freeze_dataset(_large_eligible_dataset(), config())
    assert frozen["eligibility"]["eligible"]
    packets = extraction_packets(frozen)
    responses = {p["case_id"]: _threshold_response(p, int(p["case_id"].split("-")[1]) <= 24)
                 for p in packets}
    runs = [import_run(frozen, "run-a", responses), import_run(frozen, "run-b", responses)]
    docs = make_reviews(frozen, runs)
    report = score(frozen, runs, docs)
    assert report["runs"][0]["recovery"] == .8
    assert report["runs"][0]["precision"] == 1.0
    assert report["gate"]["status"] == "pass"


def test_review_packet_binds_evidence_runs_and_masks_candidate_metadata():
    frozen = freeze_dataset(dataset(), config())
    runs = [make_run(frozen, "run-a"), make_run(frozen, "run-b")]
    output = review_packets(frozen, runs)
    item = output["packets"][0]
    assert item["messages"] == frozen["cases"][0]["messages"]
    assert item["output_hash"] in [run["run_hash"] for run in runs]
    candidate = item["candidates"][0]
    assert candidate["candidate_id"] == "candidate-0001"
    assert "authoritative" not in candidate
    assert output["key"]["items"][0]["candidate_ids"]["candidate-0001"]
    tampered = make_reviews(frozen, runs)
    tampered[0]["packet_hash"] = "0" * 64
    with pytest.raises(ValueError, match="packet hash"):
        score(frozen, runs, tampered)


def test_every_extra_output_stays_in_precision_denominator():
    small = _large_eligible_dataset()
    small["cases"] = small["cases"][:1]
    frozen = freeze_dataset(small, config())
    packet = extraction_packets(frozen)[0]
    response = _threshold_response(packet, True)
    extra = deepcopy(response["candidates"][0])
    extra["candidate_id"] = "extra"
    extra["reason"] = "because this is an additional output"
    proposal = packet["request"]["messages"][0]
    citation = {"rollout_id": proposal["rollout_id"], "turn": proposal["turn"],
                "source_ordinal": proposal["source_ordinal"], "start": 0,
                "end": len(proposal["text"]), "quote": proposal["text"]}
    extra["field_evidence"]["reason"] = [citation]
    response["candidates"].append(extra)
    runs = [import_run(frozen, rid, {packet["case_id"]: response}) for rid in ("a", "b")]
    docs = make_reviews(frozen, runs)
    report = score(frozen, runs, docs)
    assert report["runs"][0]["splits"]["fresh"]["total_outputs"] == 2
    assert report["runs"][0]["splits"]["fresh"]["correct_unique_complete"] == 1
    assert report["runs"][0]["precision"] == .5


def test_control_runs_pinned_parser_and_score_reports_it_separately():
    frozen = freeze_dataset(dataset(), config())
    control = frozen_control(frozen, Path(__file__).resolve().parents[1])
    assert control["revision"] == "95514648be7dae6652d217fd8bfbcade897e19d3"
    assert control["file_hashes"]
    assert control["cases"][0]["evidence_mode"] == "oracle_selected_evidence_reconstruction"
    runs = [make_run(frozen, "run-a"), make_run(frozen, "run-b")]
    docs = make_reviews(frozen, runs, control=control)
    report = score(frozen, runs, docs, control)
    assert report["control"]["splits"]["fresh"]["total_outputs"] >= 0


def test_cli_freeze_requests_import_and_review_packet_happy_path(tmp_path):
    def write_json(name, value):
        path = tmp_path / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return str(path)
    dataset_path = write_json("dataset.json", dataset())
    config_path = write_json("config.json", config())
    frozen_path = str(tmp_path / "frozen.json")
    assert main(["freeze", "--dataset", dataset_path, "--model-config", config_path, "--output", frozen_path]) == 0
    requests_path = str(tmp_path / "requests.json")
    assert main(["requests", "--frozen", frozen_path, "--output", requests_path]) == 0
    frozen = json.loads(Path(frozen_path).read_text(encoding="utf-8"))
    response_map = {"case-0001": response_for(extraction_packets(frozen)[0])}
    response_path = write_json("responses.json", response_map)
    run_paths = []
    for run_id in ("cli-a", "cli-b"):
        run_path = str(tmp_path / f"{run_id}.json")
        assert main(["import-run", "--frozen", frozen_path, "--run-id", run_id,
                     "--responses", response_path, "--output", run_path]) == 0
        run_paths.append(run_path)
    packets_path = str(tmp_path / "blind.json")
    assert main(["review-packets", "--frozen", frozen_path, "--runs", *run_paths, "--output", packets_path]) == 0
    exported = json.loads(Path(packets_path).read_text(encoding="utf-8"))
    assert exported["items"]
    assert "key" not in exported

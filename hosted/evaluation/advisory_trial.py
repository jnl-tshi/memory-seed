"""Reproducible synthetic contract trial for post-write curator advice.

The reviewer is scripted. Scores exercise validation and evaluation plumbing,
not model quality, production latency, or prospective decision detection.
"""
from __future__ import annotations

import json
from statistics import median
from time import perf_counter

from hosted.curator.advisory import review_accepted_decision


def _msg(turn: int, text: str, actor: str = "user") -> dict:
    return {"rollout_id": "synthetic", "turn": turn, "source_ordinal": turn,
            "actor": actor, "text": text}


def _cite(message: dict, quote: str) -> dict:
    start = message["text"].index(quote)
    return {"rollout_id": message["rollout_id"], "turn": message["turn"],
            "source_ordinal": message["source_ordinal"], "start": start,
            "end": start + len(quote), "quote": quote}


def _case(name: str, messages: list[dict], *, topics: list[str] | None = None,
          links: list[dict] | None = None, advice: dict | None = None,
          wait_batches: int = 0, unresolved: bool = False,
          expected: set[tuple] | None = None, expected_error: bool = False) -> dict:
    anchor = messages[-1]
    submission = {"record_id": name, "accepted_write_id": f"accepted-{name}",
                  "source_owner_id": "synthetic-owner", "provenance": "first-hand",
                  "claim": anchor["text"],
                  "anchor": {k: anchor[k] for k in ("rollout_id", "turn", "source_ordinal")},
                  "topics": topics or [], "links": links or []}
    return {"name": name, "submission": submission, "messages": messages,
            "advice": advice or {}, "wait_batches": wait_batches,
            "unresolved": unresolved, "expected": expected or set(),
            "expected_error": expected_error}


def _identity(group: str, item: dict) -> tuple:
    if group == "topic_suggestions":
        return (group, item["action"], item["topic"])
    if group == "link_suggestions":
        return (group, item["action"], item["target_id"], item["kind"])
    return (group, item["field"])


def _fixtures() -> list[dict]:
    proposal = _msg(1, "Option B builds on the capture decision.")
    approval = _msg(3, "Do it: use option B for the parser.")
    parser = _msg(3, "Use option B for the parser.")
    evidence = [_cite(parser, "parser")]
    link = {"target_id": "prior-1", "kind": "related"}
    return [
        _case("clean", [parser], topics=["parser"]),
        _case("missing-topic", [parser], advice={"topic_suggestions": [
            {"action": "add", "topic": "parser", "reason": "Parser choice", "citations": evidence}]},
            expected={("topic_suggestions", "add", "parser")}),
        _case("stale-topic", [parser], topics=["capture"], advice={"topic_suggestions": [
            {"action": "remove", "topic": "capture", "reason": "Topic does not fit", "citations": evidence}]},
            expected={("topic_suggestions", "remove", "capture")}),
        _case("missing-link", [proposal, approval], advice={"link_suggestions": [
            {"action": "add", **link, "reason": "Builds on prior choice",
             "citations": [_cite(proposal, "capture decision")]}]}, wait_batches=1,
            expected={("link_suggestions", "add", "prior-1", "related")}),
        _case("stale-link", [parser], links=[link], advice={"link_suggestions": [
            {"action": "remove", **link, "reason": "Link does not fit", "citations": evidence}]},
            expected={("link_suggestions", "remove", "prior-1", "related")}),
        _case("scope-conflict", [parser], advice={"conflict_flags": [
            {"field": "scope", "reason": "Review scope", "citations": evidence}]},
            expected={("conflict_flags", "scope")}),
        _case("misleading-suggestion", [parser], advice={"topic_suggestions": [
            {"action": "add", "topic": "billing", "reason": "Unsupported interpretation",
             "citations": evidence}]}),
        _case("invalid-citation-control", [parser], advice={"topic_suggestions": [
            {"action": "add", "topic": "parser", "reason": "Forged quote",
             "citations": [{**evidence[0], "quote": "billing"}]}]}, expected_error=True),
        _case("window-limit", [_msg(0, "Old proposal"), _msg(25, "Use it")],
              unresolved=True),
    ]


def run_trial() -> dict:
    topics = {"capture": "Capture", "parser": "Parser", "billing": "Billing"}
    records = {"prior-1": {"title": "Capture decision"}}
    cases = []
    latencies = []
    correct = false = missed = unresolved = invalid_accepted = invalid_rejected = calls = 0
    tokens = {"prompt_tokens": 0, "completion_tokens": 0}
    for case in _fixtures():
        def reviewer(_claim, _batch, state):
            ready = not case["unresolved"] and state["review_call"] >= case["wait_batches"]
            return {"needs_more_context": not ready,
                    "topic_suggestions": case["advice"].get("topic_suggestions", []) if ready else [],
                    "link_suggestions": case["advice"].get("link_suggestions", []) if ready else [],
                    "conflict_flags": case["advice"].get("conflict_flags", []) if ready else []}

        started = perf_counter()
        try:
            report = review_accepted_decision(case["submission"], case["messages"],
                                              topics, records, reviewer)
        except ValueError:
            if not case["expected_error"]:
                raise
            invalid_rejected += 1
            cases.append({"name": case["name"], "status": "rejected_invalid_citation",
                          "suggestions": 0, "review_calls": 1})
            latencies.append((perf_counter() - started) * 1000)
            calls += 1
            continue
        elapsed_ms = (perf_counter() - started) * 1000
        if case["expected_error"]:
            invalid_accepted += 1
        latencies.append(elapsed_ms)
        found = {_identity(group, item) for group in (
            "topic_suggestions", "link_suggestions", "conflict_flags") for item in report[group]}
        correct += len(found & case["expected"])
        false += len(found - case["expected"])
        missed += len(case["expected"] - found)
        unresolved += report["status"] == "incomplete"
        calls += report["review_calls"]
        for key in tokens:
            tokens[key] += report["usage"][key]
        cases.append({"name": case["name"], "status": report["status"],
                      "suggestions": len(found), "review_calls": report["review_calls"]})
    return {"trial_kind": "synthetic_scripted_contract_not_model_quality",
            "cases": cases, "metrics": {"cases": len(cases), "useful_suggestions": correct,
            "false_suggestions": false, "missed_suggestions": missed,
            "unresolved_cases": unresolved, "invalid_citations_accepted": invalid_accepted,
            "invalid_citations_rejected": invalid_rejected,
            "review_calls": calls, "median_local_delay_ms": round(median(latencies), 3),
            "max_local_delay_ms": round(max(latencies), 3), "model_tokens": tokens},
            "limitations": ["Scripted reviewer and hand-authored gold labels cannot measure model accuracy.",
                            "Local execution delay is not hosted queue or provider latency.",
                            "No model was called; zero model tokens are not a production cost estimate."]}


if __name__ == "__main__":
    print(json.dumps(run_trial(), indent=2, sort_keys=True))

"""Bounded post-write advice; no hosted service or authority-writing path."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from hosted.capture.disclosure import AdaptiveDisclosure


_CITATION_KEYS = frozenset({"rollout_id", "turn", "source_ordinal", "start", "end", "quote"})
_CLAIM_CITATION_KEYS = frozenset({"kind", "start", "end", "quote"})
_RECORD_CITATION_KEYS = frozenset({"kind", "record_id", "start", "end", "quote"})
_ITEM_KEYS = {
    "topic_suggestions": frozenset({"action", "topic", "reason", "citations"}),
    "link_suggestions": frozenset({"action", "target_id", "kind", "reason", "citations"}),
    "conflict_flags": frozenset({"field", "reason", "citations"}),
}
_LINK_KINDS = frozenset({"related", "evolves", "replaces"})
_CONFLICT_FIELDS = frozenset({"issue", "action", "scope", "actor", "acceptance", "timing", "reason"})


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be nonempty text")
    return value


def _submission(value: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError("submission must be an object")
    result = deepcopy(value)
    for key in ("record_id", "accepted_write_id", "source_owner_id", "claim"):
        _text(result.get(key), key)
    if result.get("provenance") != "first-hand":
        raise ValueError("accepted decision provenance must be first-hand")
    if not isinstance(result.get("topics"), list) or not all(isinstance(x, str) for x in result["topics"]):
        raise ValueError("topics must be a list of slugs")
    if (not isinstance(result.get("links"), list)
            or any(not isinstance(x, dict) or set(x) != {"target_id", "kind"}
                   for x in result["links"])):
        raise ValueError("links must be a list of target/kind pairs")
    if not isinstance(result.get("anchor"), dict):
        raise ValueError("anchor must be a source coordinate")
    anchor = result["anchor"]
    if (set(anchor) != {"rollout_id", "turn", "source_ordinal"}
            or not isinstance(anchor["rollout_id"], str) or not anchor["rollout_id"]
            or type(anchor["turn"]) is not int or anchor["turn"] < 0
            or type(anchor["source_ordinal"]) is not int or anchor["source_ordinal"] < 0):
        raise ValueError("anchor has invalid source coordinates")
    return result


def _citation(value: Any, disclosed: dict[tuple[str, int, int], dict],
              records: dict, claim: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError("citation has invalid shape")
    if value.get("kind") == "accepted_claim" and set(value) == _CLAIM_CITATION_KEYS:
        source_text = claim["claim"]
    elif value.get("kind") == "existing_record" and set(value) == _RECORD_CITATION_KEYS:
        record_id = value["record_id"]
        if not isinstance(record_id, str) or record_id not in records:
            raise ValueError("citation references unknown existing record")
        record = records[record_id]
        if not isinstance(record, dict) or not isinstance(record.get("claim"), str):
            raise ValueError("cited existing record requires claim text")
        source_text = record["claim"]
    elif set(value) == _CITATION_KEYS:
        if (not isinstance(value["rollout_id"], str) or not value["rollout_id"]
                or type(value["turn"]) is not int or type(value["source_ordinal"]) is not int):
            raise ValueError("citation coordinate has invalid type")
        coord = (value["rollout_id"], value["turn"], value["source_ordinal"])
        message = disclosed.get(coord)
        if message is None:
            raise ValueError("undisclosed citation")
        source_text = message["text"]
    else:
        raise ValueError("citation has invalid shape")
    start, end, quote = value["start"], value["end"], value["quote"]
    if (type(start) is not int or type(end) is not int or start < 0 or end <= start
            or not isinstance(quote, str) or not quote or source_text[start:end] != quote):
        raise ValueError("citation quote does not match cited source")
    return deepcopy(value)


def _response(value: Any, disclosed: dict, topics: dict, records: dict, claim: dict) -> dict:
    allowed = {"needs_more_context", "source_questions", *list(_ITEM_KEYS), "usage"}
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError("reviewer response has invalid shape")
    if type(value.get("needs_more_context")) is not bool:
        raise ValueError("needs_more_context must be boolean")
    questions = value.get("source_questions", [])
    if (not isinstance(questions, list) or any(not isinstance(q, str) or not q.strip() for q in questions)
            or (value["needs_more_context"] and not questions)
            or (not value["needs_more_context"] and questions)):
        raise ValueError("source_questions must name each unresolved question")
    result = {"needs_more_context": value["needs_more_context"], "source_questions": deepcopy(questions)}
    for group, keys in _ITEM_KEYS.items():
        items = value.get(group)
        if not isinstance(items, list):
            raise ValueError(f"{group} must be a list")
        checked = []
        for item in items:
            if not isinstance(item, dict) or set(item) != keys:
                raise ValueError(f"{group} item has invalid shape")
            _text(item.get("reason"), "reason")
            if not isinstance(item["citations"], list) or not item["citations"]:
                raise ValueError("advice requires cited evidence")
            copied = deepcopy(item)
            copied["citations"] = [_citation(c, disclosed, records, claim) for c in item["citations"]]
            if group == "topic_suggestions":
                _text(copied.get("action"), "topic action")
                _text(copied.get("topic"), "topic")
                if copied["action"] not in {"add", "remove"}:
                    raise ValueError("unsupported topic action")
                if copied["action"] == "add" and copied["topic"] not in topics:
                    raise ValueError("unknown topic")
                if (copied["topic"] in claim["topics"]) == (copied["action"] == "add"):
                    raise ValueError("topic action does not change the record")
            elif group == "link_suggestions":
                _text(copied.get("action"), "link action")
                _text(copied.get("target_id"), "link target")
                _text(copied.get("kind"), "link kind")
                if copied["action"] not in {"add", "remove"}:
                    raise ValueError("unsupported link action")
                if copied["action"] == "add" and copied["target_id"] not in records:
                    raise ValueError("unknown link target")
                if copied["target_id"] == claim["record_id"]:
                    raise ValueError("self-link is not allowed")
                if copied["kind"] not in _LINK_KINDS:
                    raise ValueError("unsupported link kind")
                present = {"target_id": copied["target_id"], "kind": copied["kind"]} in claim["links"]
                if present == (copied["action"] == "add"):
                    raise ValueError("link action does not change the record")
            else:
                _text(copied.get("field"), "conflict field")
                if copied["field"] not in _CONFLICT_FIELDS:
                    raise ValueError("unsupported conflict field")
            copied["requires_review"] = True
            copied["source"] = "reconstructed"
            checked.append(copied)
        result[group] = checked
    usage = value.get("usage", {"prompt_tokens": 0, "completion_tokens": 0})
    if (not isinstance(usage, dict) or set(usage) != {"prompt_tokens", "completion_tokens"}
            or any(type(v) is not int or v < 0 for v in usage.values())):
        raise ValueError("usage must contain nonnegative token counts")
    result["usage"] = deepcopy(usage)
    return result


def review_accepted_decision(
    submission: dict, messages: list[dict], candidate_topics: dict[str, str],
    existing_records: dict[str, dict], reviewer: Callable[[dict, dict, dict], dict],
) -> dict:
    """Compare an accepted write with records first; disclose dialogue only on request.

    The caller must authenticate the accepted-write receipt and owner-scoped source.
    This pure offline function cannot establish either and never applies advice.
    """
    claim = _submission(submission)
    if not isinstance(candidate_topics, dict) or not isinstance(existing_records, dict):
        raise ValueError("candidate topics and existing records must be mappings")
    advice: dict[str, list] = {key: [] for key in _ITEM_KEYS}
    seen: dict[str, set[tuple]] = {key: set() for key in _ITEM_KEYS}
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    disclosed: dict[tuple[str, int, int], dict] = {}
    calls = 0

    def review(context: dict, phase: str, questions: list[str]) -> dict:
        nonlocal calls
        state = {"review_call": calls, "phase": phase,
                 "source_questions": deepcopy(questions), "previous_advice": deepcopy(advice)}
        response = _response(reviewer(deepcopy(claim), deepcopy(context), state), disclosed,
                             candidate_topics, existing_records, claim)
        calls += 1
        for group in _ITEM_KEYS:
            for item in response[group]:
                identity = (item.get("action"), item.get("topic"), item.get("target_id"), item.get("kind"),
                            item.get("field"))
                if identity not in seen[group]:
                    seen[group].add(identity)
                    advice[group].append(item)
        for key in usage:
            usage[key] += response["usage"][key]
        return response

    record_context = {"kind": "records", "candidate_topics": deepcopy(candidate_topics),
                      "existing_records": deepcopy(existing_records)}
    response = review(record_context, "records", [])
    source_check_requested = response["needs_more_context"]
    disclosure = None
    # An empty owner-authorized source leaves the question unresolved; it
    # cannot silently turn a requested check into a completed review.
    if source_check_requested and messages != []:
        disclosure = AdaptiveDisclosure(messages, claim["anchor"])
        batch = disclosure.batches[0] if disclosure.batches else None
        while batch is not None:
            for message in batch["messages"]:
                coord = (message["rollout_id"], message["turn"], message["source_ordinal"])
                disclosed[coord] = message
            response = review({"kind": "dialogue", **batch}, "source", response["source_questions"])
            if not response["needs_more_context"]:
                disclosure.mark_questions_complete()
                break
            batch = disclosure.expand()
    needs_more = response["needs_more_context"]
    summary = disclosure.summary() if disclosure is not None else {
        "stop_reason": "source_unavailable" if source_check_requested else "record_comparison_complete",
        "expansion_calls": 0,
        "disclosed_source_messages": 0, "disclosed_source_characters": 0}
    return {
        "record_id": claim["record_id"], "accepted_write_id": claim["accepted_write_id"],
        "source_owner_id": claim["source_owner_id"],
        "claim_provenance": claim["provenance"], "advisory_only": True,
        "status": "incomplete" if needs_more else "reviewed",
        "source_check_requested": source_check_requested,
        "source_questions_remaining": response["source_questions"],
        "stop_reason": summary["stop_reason"], "review_calls": calls,
        **advice, "usage": usage,
        "window": {"expansion_calls": summary["expansion_calls"],
                   "disclosed_source_messages": summary["disclosed_source_messages"],
                   "disclosed_source_characters": summary["disclosed_source_characters"]},
    }

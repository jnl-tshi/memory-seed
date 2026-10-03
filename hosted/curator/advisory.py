"""Bounded post-write advice; no hosted service or authority-writing path."""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Callable

from hosted.capture.disclosure import AdaptiveDisclosure


_CITATION_KEYS = frozenset({"rollout_id", "turn", "source_ordinal", "start", "end", "quote"})
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
    return result


def _citation(value: Any, disclosed: dict[tuple[str, int, int], dict]) -> dict:
    if not isinstance(value, dict) or set(value) != _CITATION_KEYS:
        raise ValueError("citation has invalid shape")
    if (not isinstance(value["rollout_id"], str) or not value["rollout_id"]
            or type(value["turn"]) is not int or type(value["source_ordinal"]) is not int):
        raise ValueError("citation coordinate has invalid type")
    coord = (value["rollout_id"], value["turn"], value["source_ordinal"])
    message = disclosed.get(coord)
    if message is None:
        raise ValueError("undisclosed citation")
    start, end, quote = value["start"], value["end"], value["quote"]
    if (type(start) is not int or type(end) is not int or start < 0 or end <= start
            or not isinstance(quote, str) or not quote or message["text"][start:end] != quote):
        raise ValueError("citation quote does not match disclosed source")
    return deepcopy(value)


def _response(value: Any, disclosed: dict, topics: dict, records: dict, claim: dict) -> dict:
    allowed = {"needs_more_context", *list(_ITEM_KEYS), "usage"}
    if not isinstance(value, dict) or set(value) - allowed:
        raise ValueError("reviewer response has invalid shape")
    if type(value.get("needs_more_context")) is not bool:
        raise ValueError("needs_more_context must be boolean")
    result = {"needs_more_context": value["needs_more_context"]}
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
            copied["citations"] = [_citation(c, disclosed) for c in item["citations"]]
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
    """Review an already accepted write with only newly disclosed dialogue batches.

    The caller must authenticate the accepted-write receipt and owner-scoped source.
    This pure offline function cannot establish either and never applies advice.
    """
    claim = _submission(submission)
    if not isinstance(candidate_topics, dict) or not isinstance(existing_records, dict):
        raise ValueError("candidate topics and existing records must be mappings")
    disclosure = AdaptiveDisclosure(messages, claim["anchor"])
    advice: dict[str, list] = {key: [] for key in _ITEM_KEYS}
    seen: dict[str, set[tuple]] = {key: set() for key in _ITEM_KEYS}
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    disclosed: dict[tuple[str, int, int], dict] = {}
    calls = 0
    batch = disclosure.batches[0] if disclosure.batches else None
    needs_more = True
    while batch is not None:
        for message in batch["messages"]:
            coord = (message["rollout_id"], message["turn"], message["source_ordinal"])
            disclosed[coord] = message
        state = {"review_call": calls, "previous_advice": deepcopy(advice)}
        response = _response(reviewer(deepcopy(claim), deepcopy(batch), state), disclosed,
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
        needs_more = response["needs_more_context"]
        if not needs_more:
            disclosure.mark_questions_complete()
            break
        batch = disclosure.expand()
    summary = disclosure.summary()
    return {
        "record_id": claim["record_id"], "accepted_write_id": claim["accepted_write_id"],
        "source_owner_id": claim["source_owner_id"],
        "claim_provenance": claim["provenance"], "advisory_only": True,
        "status": "incomplete" if needs_more else "reviewed",
        "stop_reason": summary["stop_reason"], "review_calls": calls,
        **advice, "usage": usage,
        "window": {"expansion_calls": summary["expansion_calls"],
                   "disclosed_source_messages": summary["disclosed_source_messages"],
                   "disclosed_source_characters": summary["disclosed_source_characters"]},
    }

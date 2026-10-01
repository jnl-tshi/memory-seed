"""Deterministic, provider-independent preparation of paired source arms."""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from hosted.capture.disclosure import AdaptiveDisclosure, MAX_SOURCE_CHARACTERS
from hosted.capture.evidence_ledger import EvidenceLedger
from hosted.evaluation.adaptive_replay import AdaptiveReplay, MAX_REQUEST_CHARACTERS


_CONFIG_FIELDS = ("model_name", "reasoning_effort", "prompt_protocol_version", "arm_policy")
_SOURCE_FIELDS = ("rollout_id", "turn", "source_ordinal", "actor", "text")
def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("value must be JSON-compatible") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _source_digest(messages: list[dict]) -> str:
    return _digest([[m["rollout_id"], m["turn"], m["source_ordinal"]] for m in messages])


def _descriptor(request: dict | None, source: list[dict], config_hash: str, arm: str,
                unavailable: str | None = None, *, span_status: str | None = None,
                span_stop_reason: str | None = None) -> dict:
    return {
        "request": request,
        "summary": {
            "source_characters": sum(len(m["text"]) for m in source),
            "source_messages": len(source),
            "source_coordinate_digest": _source_digest(source),
            "request_id": None if request is None else request["request_id"],
            "configuration_hash": config_hash,
            "arm": arm,
            "source_span_status": span_status,
            "source_span_stop_reason": span_stop_reason,
            "unavailability_reason": unavailable,
            "authoritative": False,
        },
    }


def _packet_from_template(template: dict, arm: str, source: list[dict], turns: list[int],
                          config_hash: str) -> dict:
    body = deepcopy(template)
    body.pop("request_id", None)
    body["arm"] = arm
    body["configuration_id"] = config_hash
    body["batch_index"] = 0
    body["batch_digest"] = _source_digest(source)
    body["turns"] = list(turns)
    body["messages"] = deepcopy(source)
    body["ledger"] = {"answers": {slot: None for slot in EvidenceLedger.SLOTS}, "reference_links": []}
    body["extraction_instructions"] += " This is an immutable one-request source arm."
    body["request_id"] = _digest(body)
    if len(_canonical(body)) > MAX_REQUEST_CHARACTERS:
        raise ValueError("serialized request exceeds character cap")
    return body


def prepare_arms(messages: list[dict], anchor: tuple[str, int, int] | dict,
                 candidate_id: str, config: dict) -> dict:
    """Prepare adaptive, fixed historical, and full causal source packets.

    The returned ``request`` values contain raw source for extraction only.
    Public summaries contain hashes and counts, never source text.
    """
    if not isinstance(config, dict) or set(config) != set(_CONFIG_FIELDS):
        raise ValueError("frozen config must contain model_name, reasoning_effort, prompt_protocol_version, and arm_policy")
    if any(not isinstance(config[field], str) or not config[field].strip() for field in _CONFIG_FIELDS):
        raise ValueError("frozen config fields must be nonempty strings")
    config_snapshot = {field: config[field] for field in _CONFIG_FIELDS}
    config_hash = _digest(config_snapshot)
    if not isinstance(messages, list):
        raise ValueError("messages must be a list")
    clean_messages = []
    for raw in messages:
        if not isinstance(raw, dict):
            raise ValueError("source message must be an object")
        missing = [field for field in _SOURCE_FIELDS if field not in raw]
        if missing:
            raise ValueError("source message is missing required source fields")
        clean_messages.append({field: deepcopy(raw[field]) for field in _SOURCE_FIELDS})
    # Validate the original inventory (including duplicate/mixed-rollout
    # rejection) and then disclose only the approved source fields.
    AdaptiveDisclosure(clean_messages, anchor)
    disclosure = AdaptiveDisclosure(clean_messages, anchor)
    _, anchor_turn, anchor_ordinal = disclosure.anchor
    causal = sorted((m for m in clean_messages
                     if (m["turn"], m["source_ordinal"]) <= (anchor_turn, anchor_ordinal)),
                    key=lambda m: (m["turn"], m["source_ordinal"]))

    replay = AdaptiveReplay(clean_messages, disclosure.anchor, candidate_id, config_hash)
    adaptive_request = replay.request()
    adaptive_sources = [] if adaptive_request is None else adaptive_request["messages"]
    adaptive_reason = None if adaptive_request is not None else (replay.summary()["stop_reason"] or "request_budget")
    arms = {"adaptive": _descriptor(adaptive_request, adaptive_sources, config_hash, "adaptive",
                                     adaptive_reason)}

    # The fixed source is precisely what the adaptive disclosure policy can
    # reach: current turn, then bounded two-turn historical batches.
    while disclosure.stop_reason is None:
        if disclosure.expand() is None:
            break
    fixed_sources = [m for batch in disclosure.batches for m in batch["messages"]]
    fixed_sources.sort(key=lambda m: (m["turn"], m["source_ordinal"]))
    fixed_turns = sorted({m["turn"] for m in fixed_sources})
    fixed_request = None
    fixed_reason = None
    if adaptive_request is None:
        fixed_reason = adaptive_reason or "adaptive_source_unavailable"
    else:
        try:
            fixed_request = _packet_from_template(adaptive_request, "fixed_window", fixed_sources,
                                                  fixed_turns, config_hash)
        except ValueError as exc:
            if "character cap" not in str(exc):
                raise
            fixed_reason = "request_budget"
    fixed_stop_reason = disclosure.stop_reason
    fixed_span_status = "partial" if fixed_stop_reason == "character_budget" else "complete"
    arms["fixed_window"] = _descriptor(fixed_request, fixed_sources, config_hash, "fixed_window",
                                       fixed_reason, span_status=fixed_span_status,
                                       span_stop_reason=fixed_stop_reason)

    full_request = None
    full_reason = None
    full_chars = sum(len(m["text"]) for m in causal)
    if full_chars > MAX_SOURCE_CHARACTERS:
        full_reason = "source_budget"
    elif adaptive_request is None:
        full_reason = adaptive_reason or "adaptive_source_unavailable"
    else:
        try:
            full_request = _packet_from_template(adaptive_request, "full_window", causal,
                                                 sorted({m["turn"] for m in causal}), config_hash)
        except ValueError as exc:
            if "character cap" not in str(exc):
                raise
            full_reason = "request_budget"
    full_stop_reason = full_reason
    arms["full_window"] = _descriptor(full_request, causal, config_hash, "full_window", full_reason,
                                      span_status="complete" if full_request is not None else "unavailable",
                                      span_stop_reason=full_stop_reason)
    return {"configuration_hash": config_hash, "arms": arms}

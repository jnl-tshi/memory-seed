"""Provider-independent, source-grounded semantic extraction boundary.

This module validates transport shape and evidence mechanics only. It does not
decide whether cited text actually means the candidate's claims.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any


PROMPT_VERSION = "p0.2-semantic-prompt-v1"
REQUEST_SCHEMA = "p0.2-semantic-request-v1"
MAX_MESSAGES = 200
MAX_CHARACTERS = 50_000
MAX_REQUEST_CHARACTERS = 100_000
MAX_RESPONSE_CHARACTERS = 120_000
MAX_CANDIDATES = 100
BOUNDARY_FIELDS = ("task_boundary", "decision_marker", "implementation_started")
_FIELDS = (
    "issue", "selected_action", "scope", "agreement_quote", "reason",
    "conditions", "state", "deciding_actor", "unresolved_references",
)
_REQUIRED_EVIDENCE = ("issue", "selected_action", "scope", "agreement_quote")
_AUTHORITY_FIELDS = {
    "authoritative", "curator_verification_required", "mechanically_valid",
    "semantic_verified", "trusted", "approved", "promoted",
}

EXTRACTION_INSTRUCTIONS = """Read only the supplied source messages and prior retained drafts. The complete request is limited to max_request_characters; your serialized response is limited to max_response_characters and max_candidates candidates. Return a JSON object with top-level request_id copied exactly from the request and candidates as a list. Each candidate has candidate_id (nonempty string), issue, selected_action, scope, agreement_quote, reason, conditions (list of strings or null), state (accepted, proposed, or rejected), deciding_actor (user, agent, or unknown), unresolved_references (list of strings or null), and field_evidence (mapping field names to citation lists). Cite each populated issue, selected_action, scope, and agreement_quote; populated reason, each populated condition, and each populated unresolved reference also need citations. agreement_quote must exactly equal the quote of its single cited user-authored agreement span. A null required field can be left incomplete. A citation has rollout_id, turn, source_ordinal, start, end, and quote. Use nonempty exact source substrings and zero-based Python string offsets with an exclusive end. Use null for unknown fields and [] for no conditions or unresolved references. Do not assert acceptance without explicit user agreement. Treat questions and tentative language as evidence to interpret, not automatic exclusions. Do not return authority or verification flags. Semantic correctness will be independently reviewed."""


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("value is not JSON-compatible") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _coordinate(message: dict) -> tuple[str, int, int]:
    return message["rollout_id"], message["turn"], message["source_ordinal"]


def _validate_message(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raise ValueError("message must be an object")
    message = deepcopy(raw)
    if not isinstance(message.get("rollout_id"), str) or not message["rollout_id"]:
        raise ValueError("rollout_id must be a nonempty string")
    for field in ("turn", "source_ordinal"):
        if type(message.get(field)) is not int or message[field] < 0:
            raise ValueError(f"{field} must be a nonnegative integer")
    if not isinstance(message.get("actor"), str) or not message["actor"]:
        raise ValueError("actor must be a nonempty string")
    if not isinstance(message.get("text"), str):
        raise ValueError("text must be a string")
    if "timestamp" in message and not isinstance(message["timestamp"], str):
        raise ValueError("timestamp must be a string")
    for field in BOUNDARY_FIELDS:
        if field in message and type(message[field]) is not bool:
            raise ValueError(f"{field} must be boolean")
    _canonical(message)
    return message


def _timestamp(message: dict) -> datetime | None:
    value = message.get("timestamp")
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _position(message: dict, all_messages: dict[tuple, dict]) -> tuple:
    """Coordinate order within a rollout; timestamp order across rollouts."""
    return (message["turn"], message["source_ordinal"])


class SemanticState:
    """State for one semantic extraction configuration."""

    def __init__(self, config_id: str):
        if not isinstance(config_id, str) or not config_id:
            raise ValueError("config_id must be a nonempty string")
        self.config_id = config_id
        self._sources: dict[tuple[str, int, int], dict] = {}
        self._processed: set[tuple[str, int, int]] = set()
        self._drafts: dict[str, dict] = {}
        self._pending: dict | None = None
        self._pending_coords: set[tuple[str, int, int]] = set()
        self._pending_input_digest: str | None = None

    def make_request(self, messages: list[dict], marker: dict | None = None) -> dict:
        if not isinstance(messages, list):
            raise ValueError("messages must be a list")
        if marker is not None and not isinstance(marker, dict):
            raise ValueError("marker must be an object or null")
        staged: dict[tuple[str, int, int], dict] = {}
        supplied: dict[tuple[str, int, int], dict] = {}
        for raw in messages:
            message = _validate_message(raw)
            key = _coordinate(message)
            if key in supplied and supplied[key] != message:
                raise ValueError("source coordinate changed content")
            supplied[key] = message
            previous = staged.get(key, self._sources.get(key))
            if previous is not None:
                if previous != message:
                    raise ValueError("source coordinate changed content")
                continue
            staged[key] = message

        # A retry must be byte-for-byte reproducible. Callers resolve it before
        # advancing the source stream, so a retry cannot silently lose a delta.
        if self._pending is not None:
            if marker != self._pending.get("marker"):
                raise ValueError("pending request marker changed")
            if _digest([supplied[key] for key in sorted(supplied)]) != self._pending_input_digest:
                raise ValueError("pending request inputs changed")
            return deepcopy(self._pending)

        all_sources = dict(self._sources)
        all_sources.update(staged)
        if len(all_sources) > MAX_MESSAGES:
            raise ValueError("source message limit exceeded")
        if sum(len(item["text"]) for item in all_sources.values()) > MAX_CHARACTERS:
            raise ValueError("source character limit exceeded")
        new_messages = [deepcopy(item) for key, item in sorted(staged.items())]
        normalized_marker = deepcopy(marker)
        limits = {
            "max_messages": MAX_MESSAGES,
            "max_characters": MAX_CHARACTERS,
            "max_request_characters": MAX_REQUEST_CHARACTERS,
            "max_response_characters": MAX_RESPONSE_CHARACTERS,
            "max_candidates": MAX_CANDIDATES,
            "clipping": False,
        }
        request_material = {
            "schema_version": REQUEST_SCHEMA,
            "prompt_version": PROMPT_VERSION,
            "config_id": self.config_id,
            "messages": new_messages,
            "retained_state": [deepcopy(self._drafts[key]) for key in sorted(self._drafts)],
            "marker": normalized_marker,
            "limits": limits,
            "output_contract": {
                "candidate_fields": ["candidate_id", *_FIELDS, "field_evidence"],
                "citation_fields": ["rollout_id", "turn", "source_ordinal", "start", "end", "quote"],
                "offsets": "zero-based Python string offsets; end exclusive",
                "authority_flags_forbidden": True,
            },
            "extraction_instructions": EXTRACTION_INSTRUCTIONS,
        }
        request = {**request_material, "request_id": _digest(request_material)}
        if len(_canonical(request)) > MAX_REQUEST_CHARACTERS:
            raise ValueError("serialized request limit exceeded")
        self._sources.update(staged)
        self._pending = deepcopy(request)
        self._pending_coords = set(staged)
        self._pending_input_digest = _digest([supplied[key] for key in sorted(supplied)])
        return request

    def accept_response(self, request: dict, response: dict) -> list[dict]:
        if self._pending is None:
            raise ValueError("there is no pending request")
        if not isinstance(request, dict) or request != self._pending:
            raise ValueError("request identity or source content changed")
        if (request.get("schema_version") != REQUEST_SCHEMA
                or request.get("config_id") != self.config_id
                or request.get("request_id") != self._pending["request_id"]):
            raise ValueError("invalid request identity or config")
        material = {key: request[key] for key in (
            "schema_version", "prompt_version", "config_id", "messages", "retained_state",
            "marker", "limits", "output_contract", "extraction_instructions")}
        if _digest(material) != request["request_id"]:
            raise ValueError("request digest mismatch")
        if not isinstance(response, dict):
            raise ValueError("response must be an object")
        if len(_canonical(response)) > MAX_RESPONSE_CHARACTERS:
            raise ValueError("serialized response limit exceeded")
        self._reject_authority(response)
        if response.get("request_id") != request["request_id"]:
            raise ValueError("response request_id mismatch")
        candidates = response.get("candidates")
        if not isinstance(candidates, list):
            raise ValueError("candidates must be a list")
        if len(candidates) > MAX_CANDIDATES:
            raise ValueError("candidate count limit exceeded")

        # Build all outputs locally. State changes only after every candidate passes.
        imported: dict[str, dict] = {}
        supplied_ids: set[str] = set()
        stable_ids: set[str] = set()
        for candidate in candidates:
            normalized = self._validate_candidate(candidate, request)
            submitted_id = candidate["candidate_id"]
            if submitted_id in supplied_ids:
                raise ValueError("duplicate candidate id")
            supplied_ids.add(submitted_id)
            stable_id = "p02s_" + _digest({
                "fields": {field: normalized[field] for field in _FIELDS},
                "field_evidence": normalized["field_evidence"],
            })[:24]
            if stable_id in stable_ids:
                raise ValueError("duplicate candidate content and evidence")
            stable_ids.add(stable_id)
            normalized["candidate_id"] = stable_id
            normalized["complete"] = self._is_complete(normalized)
            normalized.update({
                "authoritative": False,
                "curator_verification_required": True,
                "mechanically_valid": True,
                "semantic_verified": False,
            })
            imported[stable_id] = normalized

        new_drafts = dict(self._drafts)
        new_drafts.update(imported)
        projected_material = {
            "schema_version": REQUEST_SCHEMA,
            "prompt_version": PROMPT_VERSION,
            "config_id": self.config_id,
            "messages": [],
            "retained_state": [deepcopy(new_drafts[key]) for key in sorted(new_drafts)],
            "marker": None,
            "limits": {
                "max_messages": MAX_MESSAGES,
                "max_characters": MAX_CHARACTERS,
                "max_request_characters": MAX_REQUEST_CHARACTERS,
                "max_response_characters": MAX_RESPONSE_CHARACTERS,
                "max_candidates": MAX_CANDIDATES,
                "clipping": False,
            },
            "output_contract": {
                "candidate_fields": ["candidate_id", *_FIELDS, "field_evidence"],
                "citation_fields": ["rollout_id", "turn", "source_ordinal", "start", "end", "quote"],
                "offsets": "zero-based Python string offsets; end exclusive",
                "authority_flags_forbidden": True,
            },
            "extraction_instructions": EXTRACTION_INSTRUCTIONS,
        }
        projected_request = {**projected_material, "request_id": _digest(projected_material)}
        if len(_canonical(projected_request)) > MAX_REQUEST_CHARACTERS:
            raise ValueError("projected retained state exceeds serialized request limit")
        self._drafts = new_drafts
        for key in self._pending_coords:
            self._processed.add(key)
        self._pending = None
        self._pending_coords = set()
        self._pending_input_digest = None
        return [deepcopy(self._drafts[key]) for key in sorted(imported)]

    @staticmethod
    def _reject_authority(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in _AUTHORITY_FIELDS:
                    raise ValueError("model authority or verification flags are forbidden")
                SemanticState._reject_authority(child)
        elif isinstance(value, list):
            for child in value:
                SemanticState._reject_authority(child)

    def _validate_candidate(self, candidate: Any, request: dict) -> dict:
        if not isinstance(candidate, dict):
            raise ValueError("candidate must be an object")
        self._reject_authority(candidate)
        cid = candidate.get("candidate_id")
        if not isinstance(cid, str) or not cid:
            raise ValueError("candidate_id must be a nonempty string")
        for field in _FIELDS:
            if field not in candidate:
                raise ValueError(f"candidate missing {field}")
        if set(candidate) - {"candidate_id", "field_evidence", *_FIELDS, "complete"}:
            raise ValueError("unknown candidate fields")

        for name in ("issue", "selected_action", "scope", "agreement_quote", "reason"):
            value = candidate[name]
            if value is not None and not isinstance(value, str):
                raise ValueError(f"{name} must be a string or null")
        if candidate["conditions"] is not None and (
                not isinstance(candidate["conditions"], list)
                or any(not isinstance(value, str) for value in candidate["conditions"])):
            raise ValueError("conditions must be a list of strings or null")
        if candidate["unresolved_references"] is not None and (
                not isinstance(candidate["unresolved_references"], list)
                or any(not isinstance(value, str) for value in candidate["unresolved_references"])):
            raise ValueError("unresolved_references must be a list of strings or null")
        if not isinstance(candidate["state"], str) or candidate["state"] not in {"accepted", "proposed", "rejected"}:
            raise ValueError("invalid candidate state")
        if not isinstance(candidate["deciding_actor"], str) or candidate["deciding_actor"] not in {"user", "agent", "unknown"}:
            raise ValueError("invalid deciding_actor")

        evidence = candidate.get("field_evidence")
        if not isinstance(evidence, dict) or set(evidence) - set(_FIELDS):
            raise ValueError("field_evidence must map known fields to citations")
        cited: dict[str, list[tuple[dict, dict]]] = {}
        for field, citations in evidence.items():
            if not isinstance(citations, list):
                raise ValueError(f"{field} citations must be a list")
            cited[field] = [self._validate_citation(citation) for citation in citations]
        for field in _FIELDS:
            value = candidate[field]
            populated = value is not None and value != "" and value != []
            if field in _REQUIRED_EVIDENCE and populated and not cited.get(field):
                raise ValueError(f"populated {field} requires evidence")
            if field in {"reason", "conditions", "unresolved_references"} and populated:
                count = len(value) if field == "conditions" else 1
                if field == "unresolved_references":
                    count = len(value)
                if len(cited.get(field, [])) < count:
                    raise ValueError(f"populated {field} requires evidence")

        if candidate["agreement_quote"]:
            agreement_citations = cited.get("agreement_quote", [])
            if len(agreement_citations) != 1:
                raise ValueError("agreement_quote requires exactly one citation")
            if agreement_citations[0][0]["quote"] != candidate["agreement_quote"]:
                raise ValueError("agreement_quote must equal its exact cited quote")
            if agreement_citations[0][1].get("actor") != "user":
                raise ValueError("agreement_quote requires user-authored evidence")

        if candidate["state"] == "accepted":
            if not candidate["agreement_quote"] or candidate["deciding_actor"] != "user":
                raise ValueError("accepted state requires user agreement evidence and deciding_actor user")
            if not cited.get("selected_action") or not cited.get("agreement_quote"):
                raise ValueError("accepted state requires action and acceptance chronology evidence")
            if any(message.get("actor") != "user" for _, message in cited["agreement_quote"]):
                raise ValueError("accepted state requires user-authored agreement evidence")
            self._validate_acceptance_order(cited["selected_action"], cited["agreement_quote"], request)

        # An anchor marker carrying a boundary sentinel is exempt only at its
        # exact source coordinate; every other sentinel blocks cross-message links.
        if cited.get("selected_action") and cited.get("agreement_quote"):
            self._validate_boundaries(cited["selected_action"], cited["agreement_quote"], request)

        normalized = {field: deepcopy(candidate[field]) for field in _FIELDS}
        normalized["field_evidence"] = deepcopy(evidence)
        return normalized

    def _validate_citation(self, citation: Any) -> tuple[dict, dict]:
        fields = {"rollout_id", "turn", "source_ordinal", "start", "end", "quote"}
        if not isinstance(citation, dict) or set(citation) != fields:
            raise ValueError("citation has invalid shape")
        if not isinstance(citation["rollout_id"], str) or not citation["rollout_id"]:
            raise ValueError("citation rollout_id must be a nonempty string")
        for name in ("turn", "source_ordinal", "start", "end"):
            if type(citation[name]) is not int or citation[name] < 0:
                raise ValueError(f"citation {name} must be a nonnegative integer")
        if (not isinstance(citation["quote"], str) or citation["end"] <= citation["start"]
                or not citation["quote"].strip()):
            raise ValueError("citation quote and offsets must be nonempty")
        key = (citation["rollout_id"], citation["turn"], citation["source_ordinal"])
        message = self._sources.get(key)
        if message is None:
            raise ValueError("unknown citation source")
        if citation["end"] > len(message["text"]):
            raise ValueError("citation offsets exceed source text")
        if message["text"][citation["start"]:citation["end"]] != citation["quote"]:
            raise ValueError("citation quote does not match exact source offsets")
        return deepcopy(citation), message

    def _validate_acceptance_order(self, actions: list[tuple[dict, dict]], approvals: list[tuple[dict, dict]], request: dict) -> None:
        action_messages = [message for _, message in actions]
        approval_messages = [message for _, message in approvals]
        cross = any(a["rollout_id"] != b["rollout_id"]
                    for a in action_messages for b in approval_messages)
        if cross and any(_timestamp(m) is None for m in action_messages + approval_messages):
            raise ValueError("cross-rollout acceptance requires timestamps")
        if all(a["rollout_id"] == b["rollout_id"]
               for a in action_messages for b in approval_messages):
            latest_action = max(action_messages, key=lambda m: _position(m, self._sources))
            earliest_approval = min(approval_messages, key=lambda m: _position(m, self._sources))
            if _position(earliest_approval, self._sources) < _position(latest_action, self._sources):
                raise ValueError("acceptance chronology runs backwards")
        else:
            latest_action_time = max(_timestamp(m) for m in action_messages)
            earliest_approval_time = min(_timestamp(m) for m in approval_messages)
            if earliest_approval_time < latest_action_time:
                raise ValueError("acceptance chronology runs backwards")

    def _validate_boundaries(self, actions: list[tuple[dict, dict]], approvals: list[tuple[dict, dict]], request: dict) -> None:
        action_messages = [message for _, message in actions]
        approval_messages = [message for _, message in approvals]
        anchor = request.get("marker") or {}
        anchor_key = None
        if isinstance(anchor, dict) and type(anchor.get("turn")) is int:
            rollout = anchor.get("rollout_id")
            if isinstance(rollout, str):
                anchor_key = (rollout, anchor["turn"], anchor.get("source_ordinal"))
            else:
                matching = [key for key, message in self._sources.items()
                            if message["turn"] == anchor["turn"]
                            and ("source_ordinal" not in anchor or message["source_ordinal"] == anchor["source_ordinal"])
                            and anchor.get("trigger_quote")
                            and anchor["trigger_quote"] in message["text"]]
                if len(matching) == 1:
                    anchor_key = matching[0]
        for action in action_messages:
            for approval in approval_messages:
                if (any(approval.get(field) is True for field in BOUNDARY_FIELDS)
                        and _coordinate(approval) != anchor_key):
                    raise ValueError("boundary on acceptance endpoint blocks prior action")
                if action["rollout_id"] == approval["rollout_id"]:
                    lo, hi = sorted((_position(action, self._sources), _position(approval, self._sources)))
                    between = [message for key, message in self._sources.items()
                               if message["rollout_id"] == action["rollout_id"]
                               and lo <= _position(message, self._sources) <= hi
                               and key != _coordinate(action) and key != _coordinate(approval)]
                else:
                    endpoints = [action, approval]
                    endpoint_times = [_timestamp(item) for item in endpoints]
                    if any(value is None for value in endpoint_times):
                        raise ValueError("cross-rollout boundary ordering requires timestamps")
                    lo, hi = sorted(endpoint_times)
                    unknown_boundaries = [message for key, message in self._sources.items()
                                          if key != anchor_key
                                          and any(message.get(field) is True for field in BOUNDARY_FIELDS)
                                          and _timestamp(message) is None]
                    if unknown_boundaries:
                        raise ValueError("cross-rollout boundary placement requires timestamps")
                    between = [message for key, message in self._sources.items()
                               if _timestamp(message) is not None and lo < _timestamp(message) < hi
                               and key != _coordinate(action) and key != _coordinate(approval)]
                for message in between:
                    key = _coordinate(message)
                    if key == anchor_key:
                        continue
                    if any(message.get(field) is True for field in BOUNDARY_FIELDS):
                        raise ValueError("boundary separates action from acceptance")

    def _source_messages_for(self, cited: dict[str, list[tuple[dict, dict]]]) -> list[dict]:
        found = {}
        for pairs in cited.values():
            for citation, message in pairs:
                found[_coordinate(message)] = deepcopy(message)
        return [found[key] for key in sorted(found)]

    @staticmethod
    def _is_complete(candidate: dict) -> bool:
        required = ("issue", "selected_action", "scope", "agreement_quote")
        if candidate["state"] != "accepted" or candidate["deciding_actor"] != "user":
            return False
        if any(not candidate.get(field) or not candidate["field_evidence"].get(field) for field in required):
            return False
        if candidate["unresolved_references"]:
            return False
        return True

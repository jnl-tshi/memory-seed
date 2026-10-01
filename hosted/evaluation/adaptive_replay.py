"""Provider-independent, single-candidate offline adaptive evidence replay.

Requests disclose original source text in bounded batches. Citation validation
is structural only; independent semantic review remains necessary.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any

from hosted.capture.disclosure import AdaptiveDisclosure
from hosted.capture.evidence_ledger import EvidenceLedger


MAX_REQUEST_CHARACTERS = 100_000
MAX_RESPONSE_CHARACTERS = 100_000
_SOURCE_FIELDS = ("rollout_id", "turn", "source_ordinal", "actor", "text")


def _canonical(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("value must be JSON-compatible") from exc


class AdaptiveReplay:
    """One frozen source inventory, candidate, and opaque model configuration.

    ``request`` is a detached, byte-stable snapshot. ``import_response``
    accepts one valid response for that request and advances at most one batch.
    No provider invocation or persistent write occurs here.
    """

    def __init__(self, messages: list[dict], anchor: tuple[str, int, int] | dict,
                 candidate_id: str, configuration_id: str):
        if not isinstance(candidate_id, str) or not candidate_id.strip():
            raise ValueError("candidate_id must be nonempty")
        if not isinstance(configuration_id, str) or not configuration_id.strip():
            raise ValueError("configuration_id must be nonempty")
        if not isinstance(messages, list):
            raise ValueError("messages must be a list")
        # Drop every inventory field outside the original source contract.
        # In particular, labels, lineage, and model-derived flags never enter
        # either the controller or a request.
        clean = []
        for raw in messages:
            if not isinstance(raw, dict):
                raise ValueError("source message must be an object")
            clean.append({field: deepcopy(raw[field]) for field in _SOURCE_FIELDS if field in raw})
        self.disclosure = AdaptiveDisclosure(clean, anchor)
        self.ledger = EvidenceLedger(anchor)
        self.candidate_id = candidate_id
        self.configuration_id = configuration_id
        self._current_request: dict | None = None
        self._accepted: dict[str, tuple[str, dict]] = {}
        self._request_count = 0
        self._usage: list[tuple[int, int] | None] = []
        self._stop_override: str | None = None
        if self.disclosure.batches:
            self._prepare_request(self.disclosure.batches[0])

    def _ledger_snapshot(self) -> dict:
        candidate = self.ledger.candidates.get(self.candidate_id)
        return candidate if candidate is not None else {
            "answers": {slot: None for slot in EvidenceLedger.SLOTS}, "reference_links": []}

    def _make_request(self, batch: dict) -> dict:
        body = {
            "candidate_id": self.candidate_id,
            "configuration_id": self.configuration_id,
            "anchor": {"rollout_id": self.disclosure.anchor[0], "turn": self.disclosure.anchor[1],
                       "source_ordinal": self.disclosure.anchor[2]},
            "batch_index": batch["index"], "batch_digest": batch["digest"],
            "turns": batch["turns"], "messages": batch["messages"],
            "ledger": self._ledger_snapshot(),
            "question_contract": {
                "slots": list(EvidenceLedger.SLOTS),
                "instruction": "Answer every slot from the disclosed original source with exact citations. "
                               "Leave unsupported fields unknown. Resolve reference links only with "
                               "all necessary antecedents; retain ambiguity when unresolved.",
            },
            "output_contract": {
                "required_fields": ["request_id", "candidate_id", "answers", "reference_links"],
                "optional_usage_fields": ["prompt_tokens", "completion_tokens"],
                "usage_shape": "optional usage: {prompt_tokens: nonnegative integer, completion_tokens: nonnegative integer}",
                "answer_slots": list(EvidenceLedger.SLOTS),
                "answer_entry": "null or {value: nonempty string, citations: nonempty array of citations}",
                "citation_fields": ["rollout_id", "turn", "source_ordinal", "start", "end", "quote"],
                "reference_link_fields": ["mention", "antecedents", "status"],
                "reference_statuses": ["resolved", "ambiguous", "unresolved"],
            },
            "extraction_instructions": (
                "Return one JSON object. Echo request_id and candidate_id exactly; answers must contain "
                "every answer slot. Use null for unknown answers, and [] for no reference_links. "
                "Each populated answer needs exact original source citations. A citation copies "
                "rollout_id, turn, and source_ordinal from one disclosed message; start and end are "
                "zero-based, end-exclusive Unicode character offsets into its text, and quote must "
                "exactly equal that slice. Reference links contain a mention citation, an antecedents "
                "array of earlier citations, and a resolved, ambiguous, or unresolved status. "
                "Acceptance requires user-authored source; never infer it from an assistant statement. "
                "Include a usage object only when both actual prompt_tokens and completion_tokens are available. "
                "Do not output semantic_verified or authoritative claims. Each request includes only "
                "new source; later requests assume retained conversation context from this replay "
                "or an accurately retained cited ledger, and never resend earlier raw source."
            ),
        }
        digest = hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()
        request = {**body, "request_id": digest}
        if len(_canonical(request)) > MAX_REQUEST_CHARACTERS:
            raise ValueError("serialized request exceeds character cap")
        return request

    def _prepare_request(self, batch: dict) -> None:
        try:
            request = self._make_request(batch)
        except ValueError as exc:
            if "character cap" not in str(exc):
                raise
            self._stop_override = "request_budget"
            self._current_request = None
            return
        self.ledger.add_disclosure_batch(batch["messages"])
        self._current_request = request
        self._request_count += 1

    def request(self) -> dict | None:
        """Return the pending request, or None after stopping."""
        return deepcopy(self._current_request)

    def import_response(self, response: dict) -> dict:
        """Validate and atomically retain one external response and its usage."""
        if not isinstance(response, dict):
            raise ValueError("response must be an object")
        if response.get("candidate_id") != self.candidate_id:
            raise ValueError("candidate_id mismatch")
        request_id = response.get("request_id")
        if not isinstance(request_id, str) or not request_id:
            raise ValueError("request_id is required")
        serialized = _canonical(response)
        if len(serialized) > MAX_RESPONSE_CHARACTERS:
            raise ValueError("response exceeds retained-state cap")
        previous = self._accepted.get(request_id)
        if previous is not None:
            if previous[0] != serialized:
                raise ValueError("conflicting response for accepted request")
            return deepcopy(previous[1])
        if self._current_request is None or request_id != self._current_request["request_id"]:
            raise ValueError("request_id mismatch")
        if set(response) - {"request_id", "candidate_id", "answers", "reference_links", "usage"}:
            raise ValueError("unexpected response fields")
        usage = response.get("usage")
        if usage is not None:
            if not isinstance(usage, dict) or set(usage) != {"prompt_tokens", "completion_tokens"}:
                raise ValueError("usage requires prompt_tokens and completion_tokens")
            if any(type(usage[key]) is not int or usage[key] < 0 for key in usage):
                raise ValueError("usage counts must be nonnegative integers")
        if "answers" not in response or "reference_links" not in response:
            raise ValueError("response requires answers and reference_links")
        result = self.ledger.ingest_candidate(self.candidate_id, response["answers"], response["reference_links"])
        self._usage.append(None if usage is None else (usage["prompt_tokens"], usage["completion_tokens"]))
        self._accepted[request_id] = (serialized, deepcopy(result))
        self._current_request = None
        if result["all_questions_answered"]:
            self.disclosure.mark_questions_complete()
        elif self.disclosure.stop_reason is None:
            # Probe expansion on a copy so a request-size refusal cannot
            # disclose source or advance the live controller.
            proposed = deepcopy(self.disclosure)
            batch = proposed.expand()
            if batch is not None:
                try:
                    next_request = self._make_request(batch)
                except ValueError as exc:
                    if "character cap" not in str(exc):
                        raise
                    self._stop_override = "request_budget"
                else:
                    self.disclosure = proposed
                    self.ledger.add_disclosure_batch(batch["messages"])
                    self._current_request = next_request
                    self._request_count += 1
            else:
                self.disclosure = proposed
        if self._current_request is None:
            result = self.ledger.assess(self.candidate_id, source_window_exhausted=True)
            self._accepted[request_id] = (serialized, deepcopy(result))
        return deepcopy(result)

    def summary(self) -> dict:
        disclosure = self.disclosure.summary()
        unavailable = sum(item is None for item in self._usage)
        issued_sources = self.ledger.source_messages
        return {
            "request_count": self._request_count,
            "response_count": len(self._accepted),
            "prompt_tokens": None if unavailable else sum(item[0] for item in self._usage if item is not None),
            "completion_tokens": None if unavailable else sum(item[1] for item in self._usage if item is not None),
            "usage_unavailable_requests": unavailable,
            "disclosed_source_messages": len(issued_sources),
            "disclosed_source_characters": sum(len(item["text"]) for item in issued_sources),
            "expansion_count": disclosure["expansion_calls"],
            "stop_reason": self._stop_override or disclosure["stop_reason"],
        }

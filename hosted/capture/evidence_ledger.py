"""Inert, source-cited question and reference ledger for one rollout disclosure.

This module checks shape, exact source spans, speaker, and ordering. It cannot
determine whether a quoted statement actually supports an answer; that remains
for independent semantic and curator review.
"""
from __future__ import annotations

import json
from copy import deepcopy
from typing import Any


Coordinate = tuple[str, int, int]
_CITATION_FIELDS = frozenset({"rollout_id", "turn", "source_ordinal", "start", "end", "quote"})


class EvidenceLedger:
    """Hold only original source messages disclosed for a candidate's rollout.

    ``anchor`` is the candidate's current source coordinate. A caller may add
    disclosure batches in any order (normally current turn, then older turns).
    Candidate ingestion is atomic and never creates authoritative records.
    """

    SLOTS = ("issue", "selected_action", "deciding_actor", "acceptance", "scope",
             "conditions", "proposal_reference", "topic_origin", "reason")

    def __init__(self, anchor: Coordinate | dict[str, Any]):
        if isinstance(anchor, dict):
            if set(anchor) != {"rollout_id", "turn", "source_ordinal"}:
                raise ValueError("anchor requires exact source coordinate")
            anchor = (anchor["rollout_id"], anchor["turn"], anchor["source_ordinal"])
        if not isinstance(anchor, (tuple, list)) or len(anchor) != 3:
            raise ValueError("anchor requires exact source coordinate")
        rollout, turn, ordinal = anchor
        if not isinstance(rollout, str) or not rollout or type(turn) is not int or turn < 0 or type(ordinal) is not int or ordinal < 0:
            raise ValueError("invalid anchor coordinate")
        self.anchor: Coordinate = (rollout, turn, ordinal)
        self._sources: dict[Coordinate, dict] = {}
        self._candidates: dict[str, dict] = {}

    @property
    def source_messages(self) -> list[dict]:
        return [deepcopy(self._sources[key]) for key in sorted(self._sources)]

    @property
    def candidates(self) -> dict[str, dict]:
        return deepcopy(self._candidates)

    @staticmethod
    def _coordinate(value: dict) -> Coordinate:
        return value["rollout_id"], value["turn"], value["source_ordinal"]

    def add_disclosure_batch(self, messages: list[dict]) -> None:
        """Add a batch once; a conflicting coordinate rejects the whole batch."""
        if not isinstance(messages, list):
            raise ValueError("disclosure batch must be a list")
        pending: dict[Coordinate, dict] = {}
        for raw in messages:
            if not isinstance(raw, dict):
                raise ValueError("source message must be an object")
            msg = deepcopy(raw)
            if msg.get("rollout_id") != self.anchor[0]:
                raise ValueError("source belongs to another rollout")
            for field in ("turn", "source_ordinal"):
                if type(msg.get(field)) is not int or msg[field] < 0:
                    raise ValueError(f"source {field} must be a nonnegative integer")
            if not isinstance(msg.get("actor"), str) or not msg["actor"] or not isinstance(msg.get("text"), str):
                raise ValueError("source requires actor and text")
            try:
                json.dumps(msg, allow_nan=False)
            except (TypeError, ValueError) as exc:
                raise ValueError("source message must be JSON-compatible") from exc
            coordinate = self._coordinate(msg)
            if coordinate[1:] > self.anchor[1:]:
                raise ValueError("later source message exceeds anchor")
            existing = pending.get(coordinate, self._sources.get(coordinate))
            if existing is not None and existing != msg:
                raise ValueError("changed content at source coordinate")
            pending[coordinate] = msg
        self._sources.update(pending)

    def _validate_citation(self, raw: Any) -> dict:
        if not isinstance(raw, dict) or set(raw) != _CITATION_FIELDS:
            raise ValueError("citation has invalid shape")
        if not isinstance(raw["rollout_id"], str) or not raw["rollout_id"]:
            raise ValueError("citation rollout_id must be nonempty")
        for field in ("turn", "source_ordinal", "start", "end"):
            if type(raw[field]) is not int or raw[field] < 0:
                raise ValueError(f"citation {field} must be a nonnegative integer")
        if not isinstance(raw["quote"], str) or not raw["quote"].strip() or raw["end"] <= raw["start"]:
            raise ValueError("citation quote and offsets must be nonempty")
        source = self._sources.get(self._coordinate(raw))
        if source is None:
            raise ValueError("unknown citation source (not disclosed)")
        if raw["end"] > len(source["text"]):
            raise ValueError("citation offsets exceed source text")
        if source["text"][raw["start"]:raw["end"]] != raw["quote"]:
            raise ValueError("citation quote does not match source offsets")
        return deepcopy(raw)

    def _validate_answers(self, answers: Any) -> dict:
        if not isinstance(answers, dict) or set(answers) != set(self.SLOTS):
            raise ValueError("answers must provide every controlled slot")
        validated = {}
        for slot in self.SLOTS:
            entry = answers[slot]
            if entry is None or entry == "unknown":
                validated[slot] = None
                continue
            if not isinstance(entry, dict) or set(entry) != {"value", "citations"}:
                raise ValueError(f"{slot} answer requires value and citations")
            value, citations = entry["value"], entry["citations"]
            if value is None or value == "unknown":
                if citations not in ([], None):
                    raise ValueError(f"unknown {slot} cannot carry citations")
                validated[slot] = None
                continue
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{slot} value must be a nonempty string or unknown")
            if not isinstance(citations, list) or not citations:
                raise ValueError(f"populated {slot} requires citation")
            validated[slot] = {"value": value, "citations": [self._validate_citation(item) for item in citations]}
        if validated["deciding_actor"] is not None and validated["deciding_actor"]["value"] not in {"user", "assistant", "agent"}:
            raise ValueError("deciding_actor must identify user or agent")
        acceptance = validated["acceptance"]
        if acceptance is not None:
            if any(self._sources[self._coordinate(citation)]["actor"] != "user" for citation in acceptance["citations"]):
                raise ValueError("acceptance requires user-authored source")
            actor = validated["deciding_actor"]
            if actor is None or actor["value"] != "user":
                raise ValueError("acceptance requires cited deciding_actor user")
            if any(self._sources[self._coordinate(citation)]["actor"] != "user" for citation in actor["citations"]):
                raise ValueError("deciding_actor user requires user-authored source")
        action = validated["selected_action"]
        if acceptance is not None and action is not None:
            # A user can accept and specify the action in one directive,
            # including "Yes, use SQLite". Ordering within that original
            # message is not a separate proposal/approval chronology.
            latest_action = max(self._coordinate(c)[1:] for c in action["citations"])
            earliest_acceptance = min(self._coordinate(c)[1:] for c in acceptance["citations"])
            if earliest_acceptance < latest_action:
                raise ValueError("acceptance chronology runs backwards")
        return validated

    def _validate_links(self, links: Any) -> list[dict]:
        if not isinstance(links, list):
            raise ValueError("reference links must be a list")
        validated = []
        for raw in links:
            if not isinstance(raw, dict) or set(raw) != {"mention", "antecedents", "status"}:
                raise ValueError("reference link has invalid shape")
            mention = self._validate_citation(raw["mention"])
            if raw["status"] not in {"resolved", "ambiguous", "unresolved"}:
                raise ValueError("reference status must be resolved, ambiguous, or unresolved")
            if not isinstance(raw["antecedents"], list):
                raise ValueError("reference antecedents must be a list")
            if raw["status"] != "unresolved" and not raw["antecedents"]:
                raise ValueError("resolved or ambiguous reference requires antecedent")
            antecedents = [self._validate_citation(item) for item in raw["antecedents"]]
            for antecedent in antecedents:
                antecedent_coord = self._coordinate(antecedent)[1:]
                mention_coord = self._coordinate(mention)[1:]
                if (antecedent_coord > mention_coord or
                        (antecedent_coord == mention_coord and antecedent["end"] > mention["start"])):
                    raise ValueError("reference antecedents must precede mention without overlap")
            validated.append({"mention": mention, "antecedents": antecedents, "status": raw["status"]})
        return validated

    def ingest_candidate(self, candidate_id: str, answers: dict, reference_links: list[dict] | None = None) -> dict:
        """Validate all cited answers and links before retaining a candidate."""
        if not isinstance(candidate_id, str) or not candidate_id:
            raise ValueError("candidate_id must be a nonempty string")
        validated_answers = self._validate_answers(answers)
        validated_links = self._validate_links([] if reference_links is None else reference_links)
        candidate = {"answers": validated_answers, "reference_links": validated_links}
        # Revisions are expected as older source batches become available.
        # Validation happens in full before replacing the prior snapshot.
        self._candidates[candidate_id] = candidate
        return self.assess(candidate_id)

    def assess(self, candidate_id: str, *, source_window_exhausted: bool = False) -> dict:
        if candidate_id not in self._candidates:
            raise ValueError("unknown candidate_id")
        candidate = deepcopy(self._candidates[candidate_id])
        answers = candidate["answers"]
        missing = [slot for slot in self.SLOTS if answers[slot] is None]
        unresolved = [link for link in candidate["reference_links"] if link["status"] != "resolved"]
        # A proposal mention in a later utterance needs a link to every cited
        # action utterance. A model cannot make that relationship complete by
        # filling the answer slot alone. A same-message user directive is its
        # own proposal and needs no separate antecedent.
        action = answers["selected_action"]
        proposal = answers["proposal_reference"]
        if action is not None and proposal is not None:
            for mention in proposal["citations"]:
                required = {self._coordinate(citation) for citation in action["citations"]
                            if self._coordinate(citation) != self._coordinate(mention)}
                if not required:
                    continue
                covered = any(link["status"] == "resolved" and link["mention"] == mention
                              and required.issubset({self._coordinate(c) for c in link["antecedents"]})
                              for link in candidate["reference_links"])
                if not covered and not any(link["mention"] == mention for link in unresolved):
                    unresolved.append({"mention": mention, "antecedents": [], "status": "unresolved"})
        decision_required = ("selected_action", "deciding_actor", "acceptance", "scope", "proposal_reference")
        established = (all(answers[slot] is not None for slot in decision_required)
                       and answers["deciding_actor"]["value"] == "user" and not unresolved)
        return {"candidate_id": candidate_id, **candidate,
                "source_messages": self.source_messages,
                "decision_established": established,
                "all_questions_answered": not missing and not unresolved,
                "explanation_complete": answers["reason"] is not None,
                "unresolved_references": unresolved,
                "missing_slots": missing if source_window_exhausted else [],
                "semantic_verified": False, "authoritative": False,
                "curator_review_required": True}
